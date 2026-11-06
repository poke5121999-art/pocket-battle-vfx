"""Pixel canvas, easing and small drawing primitives.

Every primitive snaps to whole pixels (no sub-pixel drawing, no anti-aliasing) and writes
fully opaque colours: alpha is either 0 or 255, so sheets stay crisp at any integer scale and
GIF previews need no matte.
"""
import math
import random

from PIL import Image

TAU = math.pi * 2


# ---------------------------------------------------------------- easing
def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def seg(t, a, b):
    """Progress of t through the window [a, b], clamped to 0..1."""
    if b <= a:
        return 1.0 if t >= b else 0.0
    return clamp((t - a) / (b - a))


def out_quad(t):
    return 1 - (1 - t) * (1 - t)


def in_quad(t):
    return t * t


def out_cubic(t):
    return 1 - (1 - t) ** 3


def in_cubic(t):
    return t * t * t


def out_expo(t):
    return 1.0 if t >= 1 else 1 - 2 ** (-10 * t)


def out_back(t, s=1.7):
    t -= 1
    return 1 + (s + 1) * t ** 3 + s * t ** 2


def in_out(t):
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- colour
def hexrgb(h):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)


def ramp_pick(pal, v):
    """pal is a dark->bright list of RGBA; v in 0..1 picks a step (no blending)."""
    i = int(round(clamp(v) * (len(pal) - 1)))
    return pal[i]


# 3x5 pixel font for the few words effects spell out (MISS, Z, LV UP, digits, !).
FONT = {
    "A": "010101111101101", "B": "110101110101110", "C": "011100100100011", "D": "110101101101110",
    "E": "111100110100111", "F": "111100110100100", "G": "011100101101011", "H": "101101111101101",
    "I": "111010010010111", "K": "101101110101101", "L": "100100100100111", "M": "101111111101101",
    "N": "110101101101101", "O": "010101101101010", "P": "110101110100100", "R": "110101110101101",
    "S": "011100010001110", "T": "111010010010010", "U": "101101101101111", "V": "101101101101010",
    "W": "101101111111101", "X": "101101010101101", "Y": "101101010010010", "Z": "111001010100111",
    "0": "111101101101111", "1": "010110010010111", "2": "110001010100111", "3": "110001010001110",
    "4": "101101111001001", "5": "111100110001110", "6": "011100111101111", "7": "111001010010010",
    "8": "111101111101111", "9": "111101111001110", "!": "010010010000010", "+": "000010111010000",
    "-": "000000111000000", " ": "000000000000000", "?": "110001010000010",
}


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        self.pa = self.img.load()

    # -- single pixels
    def px(self, x, y, c):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < self.w and 0 <= y < self.h and c is not None:
            self.pa[x, y] = c

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.pa[x, y]
        return (0, 0, 0, 0)

    def under(self, x, y, c):
        """Paint only where nothing is drawn yet (glow behind existing pixels)."""
        x, y = int(round(x)), int(round(y))
        if 0 <= x < self.w and 0 <= y < self.h and self.pa[x, y][3] == 0:
            self.pa[x, y] = c

    # -- filled shapes
    def disc(self, cx, cy, r, c, dither=False, under=False):
        cx, cy = int(round(cx)), int(round(cy))
        if r <= 0:
            return
        if r < 1:
            (self.under if under else self.px)(cx, cy, c)
            return
        ri = int(math.ceil(r))
        rr = r * r + r * 0.6
        for dy in range(-ri, ri + 1):
            for dx in range(-ri, ri + 1):
                if dx * dx + dy * dy <= rr:
                    if dither and (cx + dx + cy + dy) & 1:
                        continue
                    (self.under if under else self.px)(cx + dx, cy + dy, c)

    def ellipse(self, cx, cy, rx, ry, c, dither=False):
        cx, cy = int(round(cx)), int(round(cy))
        if rx < 0.5 or ry < 0.5:
            return
        ix, iy = int(math.ceil(rx)), int(math.ceil(ry))
        for dy in range(-iy, iy + 1):
            for dx in range(-ix, ix + 1):
                if (dx / (rx + 0.3)) ** 2 + (dy / (ry + 0.3)) ** 2 <= 1:
                    if dither and (cx + dx + cy + dy) & 1:
                        continue
                    self.px(cx + dx, cy + dy, c)

    def ring(self, cx, cy, r, thick, c, dither=False, squash=1.0, gaps=0, phase=0.0):
        """Circle outline of given thickness; squash < 1 flattens it (ground rings);
        gaps > 0 cuts it into that many arcs."""
        if r <= 0 or thick <= 0:
            return
        cx, cy = int(round(cx)), int(round(cy))
        ri = int(math.ceil(r)) + 1
        inner = max(0.0, r - thick)
        for dy in range(-ri, ri + 1):
            for dx in range(-ri, ri + 1):
                yy = dy / squash if squash != 1 else dy
                d = math.hypot(dx, yy)
                if inner < d <= r + 0.5:
                    if gaps:
                        a = (math.atan2(yy, dx) / TAU + phase) % 1.0
                        if (a * gaps) % 1.0 > 0.62:
                            continue
                    if dither and (cx + dx + cy + dy) & 1:
                        continue
                    self.px(cx + dx, cy + dy, c)

    def rect(self, x0, y0, x1, y1, c, dither=False):
        for y in range(int(round(y0)), int(round(y1)) + 1):
            for x in range(int(round(x0)), int(round(x1)) + 1):
                if dither and (x + y) & 1:
                    continue
                self.px(x, y, c)

    def line(self, x0, y0, x1, y1, c, w=1, dither=False):
        x0, y0, x1, y1 = (int(round(v)) for v in (x0, y0, x1, y1))
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            if not (dither and (x0 + y0) & 1):
                if w <= 1:
                    self.px(x0, y0, c)
                else:
                    self.disc(x0, y0, (w - 1) / 2.0, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def poly(self, pts, c):
        """Scanline polygon fill, pixel centres, no anti-aliasing."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for y in range(int(math.floor(min(ys))), int(math.ceil(max(ys))) + 1):
            yc = y + 0.5
            xs = []
            for i in range(len(pts)):
                (ax, ay), (bx, by) = pts[i], pts[(i + 1) % len(pts)]
                if (ay <= yc < by) or (by <= yc < ay):
                    xs.append(ax + (yc - ay) * (bx - ax) / (by - ay))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                for x in range(int(math.ceil(xs[k] - 0.5)), int(math.floor(xs[k + 1] - 0.5)) + 1):
                    self.px(x, y, c)

    # -- small sprites
    def sparkle(self, x, y, r, c, core=None):
        """4-point star: a plus with arms of length r, bright single-pixel core."""
        x, y = int(round(x)), int(round(y))
        r = int(round(r))
        for k in range(1, r + 1):
            for (ax, ay) in ((k, 0), (-k, 0), (0, k), (0, -k)):
                self.px(x + ax, y + ay, c)
        if r >= 3:
            for (ax, ay) in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
                self.px(x + ax, y + ay, c)
        self.px(x, y, core or c)

    def text(self, s, x, y, c, outline=None, scale=1):
        """Draw 3x5 pixel text centred on x, top at y."""
        width = len(s) * 4 * scale - scale
        x0 = int(round(x - width / 2))
        y = int(round(y))
        cells = []
        for i, ch in enumerate(s.upper()):
            bits = FONT.get(ch, FONT["?"])
            for b in range(15):
                if bits[b] == "1":
                    gx, gy = x0 + (i * 4 + b % 3) * scale, y + (b // 3) * scale
                    for sy in range(scale):
                        for sx in range(scale):
                            cells.append((gx + sx, gy + sy))
        if outline:
            filled = set(cells)
            for (cx, cy) in cells:
                for ox in (-1, 0, 1):
                    for oy in (-1, 0, 1):
                        if (cx + ox, cy + oy) not in filled:
                            self.under(cx + ox, cy + oy, outline)
        for (cx, cy) in cells:
            self.px(cx, cy, c)

    def outline(self, c):
        """1 px outline around everything drawn so far (4-neighbourhood)."""
        w, h, pa = self.w, self.h, self.pa
        add = []
        for y in range(h):
            for x in range(w):
                if pa[x, y][3]:
                    continue
                for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + ox, y + oy
                    if 0 <= nx < w and 0 <= ny < h and pa[nx, ny][3]:
                        add.append((x, y))
                        break
        for (x, y) in add:
            pa[x, y] = c

    def paste(self, other, ox, oy):
        """Copy opaque pixels of another canvas/image at an integer offset."""
        src = other.pa if isinstance(other, Canvas) else other.load()
        sw, sh = (other.w, other.h) if isinstance(other, Canvas) else other.size
        ox, oy = int(round(ox)), int(round(oy))
        for y in range(sh):
            for x in range(sw):
                p = src[x, y]
                if p[3]:
                    self.px(x + ox, y + oy, p)


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "age", "size", "kind", "seed", "c")

    def __init__(self, x, y, vx, vy, life, size=1.0, kind=0, seed=0.0, c=None):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life, self.age, self.size, self.kind, self.seed, self.c = life, 0, size, kind, seed, c

    @property
    def t(self):
        return self.age / max(1, self.life)

    @property
    def alive(self):
        return 0 <= self.age < self.life


def step(parts, gravity=0.0, drag=1.0):
    for p in parts:
        if p.age < 0:
            p.age += 1
            continue
        p.x += p.vx
        p.y += p.vy
        p.vy += gravity
        p.vx *= drag
        p.vy *= drag
        p.age += 1


def make_rng(seed_text):
    s = 0
    for ch in seed_text:
        s = (s * 131 + ord(ch)) & 0xFFFFFFFF
    return random.Random(s)


# ---------------------------------------------------------------- v2 helpers: ordered dither + shading
BAYER4 = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def bayer(x, y):
    """Ordered-dither threshold in (0, 1) for pixel (x, y)."""
    return (BAYER4[int(y) & 3][int(x) & 3] + 0.5) / 16.0


def _glow(self, cx, cy, r0, r1, c, density=0.75, squash=1.0, under=True):
    """Soft glow without alpha: pixels between r0 and r1 are lit by a Bayer pattern whose density falls off
    linearly to 0 at r1. Painted behind existing pixels by default."""
    if r1 <= r0:
        return
    ri = int(math.ceil(r1)) + 1
    cx, cy = int(round(cx)), int(round(cy))
    for dy in range(-ri, ri + 1):
        for dx in range(-ri, ri + 1):
            d = math.hypot(dx, dy / squash)
            if d > r1 or d < r0:
                continue
            k = density * (1 - (d - r0) / (r1 - r0))
            if bayer(cx + dx, cy + dy) < k:
                (self.under if under else self.px)(cx + dx, cy + dy, c)


def _shaded(self, cx, cy, rx, ry, pal, lo=1, hi=5, light=(-0.45, -0.55), rim=True, dither_edge=False):
    """Volumetric blob: rim (pal[lo]) -> body -> lit side -> highlight -> hot spot (pal[hi]).
    Tones are picked from a lit-sphere term so one call gives 4-5 tones."""
    if rx < 0.6 or ry < 0.6:
        self.px(cx, cy, pal[hi])
        return
    cx_i, cy_i = int(round(cx)), int(round(cy))
    ix, iy = int(math.ceil(rx)) + 1, int(math.ceil(ry)) + 1
    lx, ly = light
    span = hi - lo
    for dy in range(-iy, iy + 1):
        for dx in range(-ix, ix + 1):
            nx, ny = dx / (rx + 0.35), dy / (ry + 0.35)
            d2 = nx * nx + ny * ny
            if d2 > 1:
                continue
            nz = math.sqrt(1 - d2)
            lum = clamp(0.5 + 0.55 * (-(nx * lx + ny * ly) + nz * 0.6) - 0.15)
            if rim and d2 > 0.78:
                lum = min(lum, 0.12)
            idx = lo + int(lum * span + bayer(cx_i + dx, cy_i + dy) * 0.9 - 0.2)
            idx = max(lo, min(hi, idx))
            self.px(cx_i + dx, cy_i + dy, pal[idx])


def _dissolve(self, amount, seed=0):
    """Remove pixels with an ordered pattern (amount 0 keeps all, 1 removes all) - fades without alpha."""
    if amount <= 0:
        return
    for y in range(self.h):
        for x in range(self.w):
            if self.pa[x, y][3] and bayer(x + seed, y + seed * 3) < amount:
                self.pa[x, y] = (0, 0, 0, 0)


def _stroke(self, pts, w, pal, lo=1, hi=5, glow=0):
    """Thick polyline with a rim, body and 1 px hot core (bolts, beams, ribbons)."""
    for a, b in zip(pts, pts[1:]):
        self.line(a[0], a[1], b[0], b[1], pal[lo], w=w + 2)
    for a, b in zip(pts, pts[1:]):
        self.line(a[0], a[1], b[0], b[1], pal[max(lo, hi - 2)], w=w)
    if w >= 3:
        for a, b in zip(pts, pts[1:]):
            self.line(a[0], a[1], b[0], b[1], pal[hi - 1], w=max(1, w - 2))
    for a, b in zip(pts, pts[1:]):
        self.line(a[0], a[1], b[0], b[1], pal[hi], w=1)
    if glow:
        for a in pts[::2]:
            self.glow(a[0], a[1], w / 2 + 1, w / 2 + glow, pal[lo + 1], density=0.5)


def _tri_ray(self, cx, cy, ang, r0, r1, width, c):
    """Tapered ray (a thin triangle) from r0 to r1 along ang."""
    ca, sa = math.cos(ang), math.sin(ang)
    nx, ny = -sa * width / 2, ca * width / 2
    self.poly([(cx + ca * r0 + nx, cy + sa * r0 + ny), (cx + ca * r1, cy + sa * r1),
               (cx + ca * r0 - nx, cy + sa * r0 - ny)], c)


def _band(self, cx, cy, r, thick, pal, squash=1.0, lo=2, hi=5, front_lit=False, gaps=0, phase=0.0, dens=1.0):
    """Thick ring with a gradient across its width: outer edge dark, inner bright edge hot.
    front_lit brightens the lower (front) half - for squashed rings seen from above."""
    if r <= 0 or thick <= 0:
        return
    cx_i, cy_i = int(round(cx)), int(round(cy))
    ri = int(math.ceil(r)) + 1
    inner = max(0.0, r - thick)
    for dy in range(-ri, ri + 1):
        for dx in range(-ri, ri + 1):
            yy = dy / squash
            d = math.hypot(dx, yy)
            if not (inner < d <= r + 0.5):
                continue
            if gaps:
                a = (math.atan2(yy, dx) / TAU + phase) % 1.0
                if (a * gaps) % 1.0 > 0.66:
                    continue
            if dens < 1 and bayer(cx_i + dx, cy_i + dy) > dens:
                continue
            k = (r + 0.5 - d) / (thick + 0.5)          # 0 outer edge -> 1 inner edge
            if front_lit:
                k = k * 0.7 + (0.3 if dy > 0 else -0.1)
            idx = lo + int(clamp(k) * (hi - lo) + 0.25)
            self.px(cx_i + dx, cy_i + dy, pal[max(lo, min(hi, idx))])


def _star(self, cx, cy, r, inner, points, pal, rot=0.0, lo=2, hi=5):
    """Filled N-point star with a shaded body: outline-ish edge, mid body, bright centre."""
    pts = []
    for k in range(points * 2):
        a = rot + k * math.pi / points
        rr = r if k % 2 == 0 else r * inner
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    self.poly(pts, pal[lo])
    pts2 = [(cx + (x - cx) * 0.72, cy + (y - cy) * 0.72) for x, y in pts]
    self.poly(pts2, pal[min(hi, lo + 1)])
    pts3 = [(cx + (x - cx) * 0.45, cy + (y - cy) * 0.45) for x, y in pts]
    self.poly(pts3, pal[min(hi, lo + 2)])
    self.disc(cx, cy, max(0.6, r * 0.18), pal[hi])


Canvas.glow = _glow
Canvas.shaded = _shaded
Canvas.dissolve = _dissolve
Canvas.stroke = _stroke
Canvas.tri_ray = _tri_ray
Canvas.band = _band
Canvas.star = _star
