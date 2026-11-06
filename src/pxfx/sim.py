"""v3 core: value noise, a seeded particle simulation stepped at 120 Hz and sampled at the frame rate, an
additive LIGHT layer, and noise-broken pixel shapes.

Two layers per frame (the pixelfx-style split):
- COLOR: crisp pixels, mostly opaque; smoke may use two translucent levels (alpha 96 / 176).
- LIGHT: soft additive light, rendered at half resolution, upscaled bilinear on export. Stored premultiplied
  (rgb = light, alpha = max channel) so an engine adds it with blend (ONE, ONE).
"""
import math

from PIL import Image

from .core import TAU, Canvas, clamp

SUB = 4  # simulation substeps per frame (30 fps x 4 = 120 Hz)


# ------------------------------------------------------------------ noise
def _hash(ix, iy, seed):
    h = (ix * 374761393 + iy * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0


def noise2(x, y, seed=0):
    """Smooth value noise in [-1, 1]."""
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = x - ix, y - iy
    sx, sy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b = _hash(ix, iy, seed), _hash(ix + 1, iy, seed)
    c, d = _hash(ix, iy + 1, seed), _hash(ix + 1, iy + 1, seed)
    return (a + (b - a) * sx + (c - a) * sy + (a - b - c + d) * sx * sy) * 2 - 1


def fbm(x, y, seed=0, oct=3):
    s, amp, tot = 0.0, 0.5, 0.0
    for o in range(oct):
        s += noise2(x, y, seed + o * 31) * amp
        tot += amp
        x, y, amp = x * 2.03, y * 2.03, amp * 0.5
    return s / tot


def curl(x, y, seed):
    """Divergence-free swirl from the noise gradient (rotated)."""
    e = 0.15
    dx = noise2(x + e, y, seed) - noise2(x - e, y, seed)
    dy = noise2(x, y + e, seed) - noise2(x, y - e, seed)
    return dy / (2 * e), -dx / (2 * e)


# ------------------------------------------------------------------ light layer
class Light:
    """Additive light at half resolution. add() splats a soft radial falloff."""

    def __init__(self, w, h, scale=2):
        self.s = scale
        self.w, self.h = (w + scale - 1) // scale, (h + scale - 1) // scale
        self.W, self.H = w, h
        self.buf = [[0.0, 0.0, 0.0] for _ in range(self.w * self.h)]

    def add(self, x, y, radius, col, intensity=1.0):
        if intensity <= 0.01 or radius <= 0:
            return
        s = self.s
        cx, cy, r = x / s, y / s, max(0.6, radius / s)
        r2 = r * r
        cr, cg, cb = col[0] / 255 * intensity, col[1] / 255 * intensity, col[2] / 255 * intensity
        x0, x1 = max(0, int(cx - r * 1.6)), min(self.w - 1, int(cx + r * 1.6) + 1)
        y0, y1 = max(0, int(cy - r * 1.6)), min(self.h - 1, int(cy + r * 1.6) + 1)
        for yy in range(y0, y1 + 1):
            dy = (yy + 0.5 - cy) ** 2
            row = yy * self.w
            for xx in range(x0, x1 + 1):
                d2 = (xx + 0.5 - cx) ** 2 + dy
                if d2 > r2 * 2.56:
                    continue
                k = math.exp(-d2 / (r2 * 0.5))
                p = self.buf[row + xx]
                p[0] += cr * k
                p[1] += cg * k
                p[2] += cb * k

    def image(self):
        """Premultiplied RGBA at full size: rgb = light, a = max(rgb)."""
        im = Image.new("RGB", (self.w, self.h))
        # soft tone curve: light adds up without clipping to flat white (keeps the hue of hot spots)
        # capped at ~60 % so light never hides the colour pixels under it
        tm = lambda v: int(255 * 0.6 * (1 - math.exp(-1.6 * v)))
        im.putdata([(tm(p[0]), tm(p[1]), tm(p[2])) for p in self.buf])
        im = im.resize((self.w * self.s, self.h * self.s), Image.BILINEAR).crop((0, 0, self.W, self.H))
        r, g, b = im.split()
        px = list(im.getdata())
        a = Image.new("L", im.size)
        a.putdata([max(p) for p in px])
        return Image.merge("RGBA", (r, g, b, a))


# ------------------------------------------------------------------ particles
class P:
    __slots__ = ("x", "y", "vx", "vy", "age", "life", "size", "ramp", "kind", "seed", "rot", "spin",
                 "light", "g", "drag", "turb", "bounce", "smoke_at", "flick", "data", "grow")

    def __init__(self, **k):
        self.x = self.y = self.vx = self.vy = 0.0
        self.age, self.life, self.size = 0.0, 1.0, 1.0
        self.ramp, self.kind, self.seed = None, "px", 0
        self.rot, self.spin = 0.0, 0.0
        self.light = None          # (radius, intensity) or None
        self.g, self.drag, self.turb, self.bounce = 0.0, 0.0, 0.0, 0.0
        self.smoke_at = 2.0        # life fraction where it turns to smoke (>1 = never)
        self.flick = 0.0           # 0..1 chance a frame skips drawing it (flicker)
        self.data = None
        self.grow = 0.0            # size change per second (relative)
        for a, v in k.items():
            setattr(self, a, v)

    @property
    def t(self):
        return self.age / self.life


class Sim:
    """Holds particles, steps them at 120 Hz, knows the ground line."""

    def __init__(self, S, ground=None, wind=0.0, period=None):
        self.S = S
        self.rng = S.rng
        self.period = period
        self.parts = []
        self.ground = ground
        self.wind = wind
        self.time = 0.0
        self.seed = S.rng.randrange(1 << 16)

    def emit(self, n, x, y, ang=0.0, spread=TAU, speed=(10, 30), life=(0.4, 0.8), size=(1, 2), area=0.0,
             area_y=None, rng=None, **kw):
        """Spawn n particles at (x, y) (+ random offset inside area/area_y), velocity in a cone."""
        rng = rng or self.rng
        out = []
        for _ in range(int(n)):
            a = ang + rng.uniform(-spread / 2, spread / 2)
            sp = rng.uniform(*speed)
            ox = rng.uniform(-area, area) if area else 0
            oy = rng.uniform(-(area_y if area_y is not None else area), (area_y if area_y is not None else area)) \
                if (area or area_y) else 0
            p = P(x=x + ox, y=y + oy, vx=math.cos(a) * sp, vy=math.sin(a) * sp, life=rng.uniform(*life),
                  size=rng.uniform(*size), seed=rng.randrange(1 << 16), rot=rng.uniform(0, TAU), **kw)
            out.append(p)
        self.parts.extend(out)
        return out

    def step(self, dt):
        self.time += dt
        g_line = self.ground
        for p in self.parts:
            p.age += dt
            if p.turb:
                if self.period:
                    ph = self.time / self.period * TAU
                    cx, cy = curl(p.x * 0.06 + math.cos(ph) * 0.8, p.y * 0.06 + math.sin(ph) * 0.8, self.seed + p.seed % 7)
                else:
                    cx, cy = curl(p.x * 0.06, p.y * 0.06 + self.time * 0.6, self.seed + p.seed % 7)
                p.vx += cx * p.turb * dt
                p.vy += cy * p.turb * dt
            p.vy += p.g * dt
            p.vx += self.wind * dt
            if p.drag:
                k = math.exp(-p.drag * dt)
                p.vx *= k
                p.vy *= k
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.rot += p.spin * dt
            if p.grow:
                p.size = max(0.2, p.size * (1 + p.grow * dt))
            if g_line is not None and p.bounce and p.y > g_line:
                p.y = g_line
                p.vy = -abs(p.vy) * p.bounce
                p.vx *= 0.6
                if abs(p.vy) < 6:
                    p.vy = 0
        self.parts = [p for p in self.parts if p.age < p.life]

    def advance(self, fps):
        dt = 1.0 / fps / SUB
        for _ in range(SUB):
            self.step(dt)


# ------------------------------------------------------------------ colour over life
def life_col(ramp, t):
    i = int(clamp(t) * (len(ramp) - 1) + 0.5)
    return ramp[min(len(ramp) - 1, i)]


def with_alpha(c, a):
    return (c[0], c[1], c[2], a)


# ------------------------------------------------------------------ noise-broken pixel shapes
def rag_blob(cv, x, y, r, col, seed, t=0.0, rough=0.38, holes=0.0, edge=None, alpha=255):
    """Irregular blob: radius modulated by angular noise, optional holes (breaking apart), darker edge."""
    if r < 0.8:
        cv.px(x, y, with_alpha(col, alpha))
        return
    ri = int(r * (1 + rough)) + 1
    xi, yi = int(round(x)), int(round(y))
    for dy in range(-ri, ri + 1):
        for dx in range(-ri, ri + 1):
            d = math.hypot(dx, dy)
            a = math.atan2(dy, dx)
            rr = r * (1 + rough * noise2(math.cos(a) * 1.6 + seed % 97, math.sin(a) * 1.6 + t * 2.5, seed))
            if d > rr:
                continue
            if holes and noise2((xi + dx) * 0.45 + seed % 13, (yi + dy) * 0.45 + t * 3, seed + 5) * 0.5 + 0.5 < holes:
                continue
            c = edge if (edge is not None and d > rr - 1.0) else col
            cv.px(xi + dx, yi + dy, with_alpha(c, alpha))


def streak(cv, x, y, vx, vy, length, cols):
    """Tapered motion streak: bright head at (x, y), tail fades through cols (head colour first)."""
    sp = math.hypot(vx, vy) or 1
    ux, uy = vx / sp, vy / sp
    L = max(1, int(length))
    for k in range(L + 1):
        c = cols[min(len(cols) - 1, int(k / (L + 1) * len(cols)))]
        cv.px(x - ux * k, y - uy * k, c)


def tongue(cv, x, y, w, h, cols, seed, t, lean=0.0):
    """Flame tongue: wide flickering base tapering to a bent tip. cols = [edge, body, core]."""
    H = max(2, int(h))
    for k in range(H):
        f = k / H
        half = w * (1 - f) ** 0.9 * (0.75 + 0.35 * noise2(f * 3 + seed % 31, t * 7, seed))
        cx = x + lean * f * f * h + noise2(f * 2.5, t * 5 + seed % 17, seed + 3) * f * 2.2
        yy = y - k
        for xx in range(int(math.floor(cx - half)), int(math.ceil(cx + half)) + 1):
            d = abs(xx - cx) / max(0.6, half)
            if d > 1:
                continue
            c = cols[0] if d > 0.66 else cols[1] if (d > 0.3 or f > 0.6) else cols[2]
            cv.px(xx, yy, c)


def jag_star(cv, x, y, r, n, cols, rng, inner=0.28, rot=0.0):
    """Asymmetric jagged burst: n spikes of random length, layered from cols[0] (outer) to cols[-1]."""
    spikes = [(rot + k * TAU / n + rng.uniform(-0.25, 0.25), rng.uniform(0.45, 1.0)) for k in range(n)]
    for li, c in enumerate(cols):
        s = 1 - li / (len(cols) + 0.4)
        pts = []
        for (a, L) in spikes:
            pts.append((x + math.cos(a) * r * L * s, y + math.sin(a) * r * L * s))
            a2 = a + TAU / n / 2
            pts.append((x + math.cos(a2) * r * inner * s, y + math.sin(a2) * r * inner * s))
        cv.poly(pts, c)


def crescent(cv, cx, cy, r, a0, a1, width, cols, squash=1.0, taper=0.9, steps=None):
    """Tapered arc (thick in the middle, thin at the ends): cols = [outer edge, body, hot inner edge]."""
    steps = steps or max(12, int(abs(a1 - a0) * r * 1.4))
    for k in range(steps + 1):
        f = k / steps
        a = a0 + (a1 - a0) * f
        w = width * (math.sin(math.pi * f) ** taper)
        if w < 0.4:
            continue
        for j in range(int(math.ceil(w)) + 1):
            rr = r - j
            kk = j / max(1, w)
            c = cols[2] if kk < 0.3 else cols[1] if kk < 0.75 else cols[0]
            cv.px(cx + math.cos(a) * rr, cy + math.sin(a) * rr * squash, c)


def broken_ring(cv, cx, cy, r, width, cols, seed, t, squash=1.0, keep=0.62):
    """Shockwave ring that is uneven and broken: noise decides gaps and width along the circle."""
    steps = max(24, int(r * 7))
    for k in range(steps):
        a = k / steps * TAU
        n = noise2(math.cos(a) * 2 + seed % 41, math.sin(a) * 2 + t * 2, seed)
        if n * 0.5 + 0.5 > keep:
            continue
        w = width * (0.35 + 0.65 * (1 - (n * 0.5 + 0.5) / keep))
        for j in range(int(math.ceil(w)) + 1):
            kk = j / max(1, w)
            c = cols[2] if kk < 0.3 else cols[1] if kk < 0.75 else cols[0]
            cv.px(cx + math.cos(a) * (r - j), cy + math.sin(a) * (r - j) * squash, c)


def bolt(cv, rng, x0, y0, x1, y1, cols, segs=8, amp=6.0, width=1, light=None, lcol=None):
    """Jagged lightning polyline, regenerated each call: rim/core colours, optional light along it."""
    pts = [(x0, y0)]
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy) or 1
    nx, ny = -dy / L, dx / L
    for k in range(1, segs):
        f = k / segs
        o = rng.uniform(-amp, amp) * math.sin(math.pi * f) ** 0.5
        pts.append((x0 + dx * f + nx * o, y0 + dy * f + ny * o))
    pts.append((x1, y1))
    for a, b in zip(pts, pts[1:]):
        if width > 1:
            cv.line(a[0], a[1], b[0], b[1], cols[0], w=width + 1)
        cv.line(a[0], a[1], b[0], b[1], cols[-1], w=max(1, width - 1) if width > 2 else 1)
        if light is not None:
            light.add((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 5 + width * 2, lcol or cols[-1], 0.14)
    return pts


def frames_light(S):
    return [Light(S.w, S.h) for _ in range(S.n)]
