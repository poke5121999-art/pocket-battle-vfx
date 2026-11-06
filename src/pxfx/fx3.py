"""v3 archetypes in the particle + light style (see sim.py).

Every effect is run() through a 120 Hz particle sim sampled at S.fps (30). Loops use periodic emission: the
random numbers of frame i come from an RNG keyed by i mod n and the turbulence field is periodic, so after a
warm-up of one loop the recorded frames wrap with no seam. Shapes are noise-broken (rag_blob, tongue,
jag_star, crescent, broken_ring, bolt); full circles appear only as tiny bubbles and as broken shockwave rings.
"""
import math
import random

from .core import TAU, clamp, out_cubic, out_quad, seg, in_quad
from .creature import draw_creature
from .palettes import ramp
from .sim import (P, Light, Sim, bolt, broken_ring, crescent, jag_star, life_col, noise2, rag_blob, streak, tongue,
                  with_alpha)

SMOKE = ramp("smoke")
DUST = ramp("dust")
SCORCH = ramp("scorch")


# ------------------------------------------------------------------ runner
def run(S, tick, draw, loop=False, ground=None, warm=None, wind=0.0):
    fps = S.fps
    _MAT["on"] = bool(getattr(S, "material", False))
    sim = Sim(S, ground=ground, wind=wind, period=(S.n / fps) if loop else None)
    base = S.rng.randrange(1 << 30)

    def R(i, salt=0):
        k = (i % S.n) if loop else i
        return random.Random(base + k * 7919 + salt * 104729)

    if loop:
        W = warm or S.n
        sim.time = -W / fps
        for i in range(-W, 0):
            tick(sim, i % S.n, (i % S.n) / fps, R(i))
            sim.advance(fps)
    for i in range(S.n):
        t = i / fps
        tick(sim, i, t, R(i))
        sim.advance(fps)
        draw(S.frames[i], S.lights[i], sim, i, t, R(i, 1))
    return sim


# ------------------------------------------------------------------ particle drawing
def draw_parts(cv, L, parts, rng, kinds=None):
    for p in parts:
        if kinds and p.kind not in kinds:
            continue
        if p.flick and rng.random() < p.flick:
            continue
        t = p.t
        kind = p.kind
        if p.smoke_at < 1 and t >= p.smoke_at:
            kind = "smoke"
        if kind == "smoke":
            st = (t - p.smoke_at) / max(0.05, 1 - p.smoke_at) if p.smoke_at < 1 else t
            col = life_col(SMOKE[1:4][::-1], st)
            r = p.size * (1 + st * 0.7)
            rag_blob(cv, p.x, p.y, r, col, p.seed, t=st, rough=0.5, holes=0.3 + st * 0.55,
                     alpha=150 if st < 0.45 else 90)
            continue
        col = life_col(p.ramp, t)
        if kind == "px":
            cv.px(p.x, p.y, col)
            if p.size > 1.6:
                cv.px(p.x + 1, p.y, col)
                cv.px(p.x, p.y + 1, col)
                cv.px(p.x + 1, p.y + 1, life_col(p.ramp, min(1, t + 0.25)))
        elif kind == "streak":
            sp = math.hypot(p.vx, p.vy)
            ln = clamp(sp * 0.045 * p.size, 1, 9)
            cols = [col] + [life_col(p.ramp, min(1, t + 0.2 * k)) for k in (1, 2, 3)]
            streak(cv, p.x, p.y, p.vx or 0.01, p.vy, ln, cols)
        elif kind == "flame":
            r = p.size * (1 - t * 0.55)
            rag_blob(cv, p.x, p.y, r, col, p.seed, t=t, rough=0.42, edge=life_col(p.ramp, min(1, t + 0.3)))
        elif kind == "chip":
            s = p.size
            pts = [(p.x + math.cos(p.rot + k * TAU / 3 + (k == 1) * 0.6) * s * (1 if k else 1.3),
                    p.y + math.sin(p.rot + k * TAU / 3 + (k == 1) * 0.6) * s) for k in range(3)]
            cv.poly(pts, p.ramp[1])
            cv.poly([pts[0], pts[1], (p.x, p.y)], p.ramp[2])
            cv.px(pts[0][0], pts[0][1], p.ramp[3])
        elif kind == "drop":
            sp = math.hypot(p.vx, p.vy)
            if sp > 40:
                streak(cv, p.x, p.y, p.vx, p.vy, min(4, sp * 0.03), [p.ramp[0], p.ramp[1], p.ramp[2]])
            else:
                cv.px(p.x, p.y, p.ramp[1])
                if p.size > 1.4:
                    cv.px(p.x, p.y + 1, p.ramp[2])
            cv.px(p.x, p.y, p.ramp[0])
        elif kind == "leaf":
            ca, sa = math.cos(p.rot), math.sin(p.rot)
            n = max(2, int(p.size + 1))
            for k in range(-n, n + 1):
                c = p.ramp[0] if k == n else p.ramp[1] if k > 0 else p.ramp[2]
                cv.px(p.x + ca * k * 0.8, p.y + sa * k * 0.8, c)
                if abs(k) < n - 1:
                    cv.px(p.x + ca * k * 0.8 - sa, p.y + sa * k * 0.8 + ca, p.ramp[2])
        elif kind == "shard":
            ca, sa = math.cos(p.rot), math.sin(p.rot)
            n = max(2, int(p.size * 1.5))
            for k in range(n + 1):
                cv.px(p.x + ca * k, p.y + sa * k, p.ramp[0] if k == n else p.ramp[1])
            cv.px(p.x - sa, p.y + ca, p.ramp[2])
        elif kind == "star":
            r = 1 if p.size < 1.6 or t > 0.7 else 2
            for k in range(1, r + 1):
                for (ax, ay) in ((k, 0), (-k, 0), (0, k), (0, -k)):
                    cv.px(p.x + ax, p.y + ay, life_col(p.ramp, min(1, t + 0.25 * k)))
            cv.px(p.x, p.y, col)
        elif kind == "snow":
            cv.px(p.x, p.y, col)
            if p.size > 1.4:
                for (ax, ay) in ((1, 1), (-1, -1), (1, -1), (-1, 1)):
                    cv.px(p.x + ax, p.y + ay, life_col(p.ramp, min(1, t + 0.3)))
        elif kind == "bubble":
            r = 1 if p.size < 1.8 else 2
            for (ax, ay) in ((r, 0), (-r, 0), (0, r), (0, -r)) + (((1, 1), (-1, 1), (1, -1), (-1, -1)) if r == 2 else ()):
                cv.px(p.x + ax, p.y + ay, col)
            cv.px(p.x - (r - 1 or 1) * 0.5, p.y - (r - 1 or 1) * 0.5, p.ramp[0])
        elif kind == "glyph":
            sc = 1 if t < 0.45 else 2
            cv.text(p.data, p.x, p.y, col, outline=p.ramp[-1], scale=sc)
        elif kind == "bug":
            cv.px(p.x, p.y, p.ramp[2])
            cv.px(p.x + 1, p.y, p.ramp[1])
            cv.px(p.x, p.y - 1, p.ramp[0] if (int(p.age * 30) % 2) else p.ramp[1])
        elif kind == "wisp":
            sp = math.hypot(p.vx, p.vy) or 1
            ux, uy = p.vx / sp, p.vy / sp
            n = int(3 + p.size * 2)
            for k in range(n):
                f = k / n
                w = (1 - f) * p.size * 0.6
                c = life_col(p.ramp, min(1, t + f * 0.6))
                x = p.x - ux * k + math.sin(k * 0.9 + p.age * 9) * 0.8
                y = p.y - uy * k
                cv.px(x, y, c)
                if w > 0.7:
                    cv.px(x + 1, y, c)
        elif kind == "heart":
            for (ax, ay) in ((-1, -1), (1, -1), (-1, 0), (0, 0), (1, 0), (0, 1)):
                cv.px(p.x + ax, p.y + ay, col if ay >= 0 else life_col(p.ramp, max(0, t - 0.2)))
        if p.light and t < 1:
            r, inten = p.light
            L.add(p.x, p.y, r * (1 - t * 0.4), p.ramp[min(1, len(p.ramp) - 1)], inten * (1 - t) ** 1.2)


# ------------------------------------------------------------------ element styles
_MAT = {"on": False}


def life_ramp(pal, hot=True):
    """Colour over life: white-hot -> highlight -> light -> mid -> dark. Material effects (water, rock, leaves)
    never start white-hot: they start at the lit tone and darken."""
    if _MAT["on"]:
        return [pal[4], pal[3], pal[2], pal[1]]
    return [pal[5], pal[4], pal[3], pal[2], pal[1]] if hot else [pal[4], pal[3], pal[2], pal[1]]


STYLE = {
    # element: (main particle, secondary, gravity, drag, turbulence, smoke?)
    "fire": ("flame", "ember", -40, 2.0, 60, True),
    "dragon": ("flame", "ember", -30, 2.0, 70, False),
    "water": ("drop", "mist", 220, 0.6, 0, False),
    "grass": ("leaf", "mote", 30, 2.5, 60, False),
    "electric": ("streak", "bolt", 40, 3.5, 0, False),
    "ice": ("shard", "snow", 60, 2.0, 20, False),
    "fighting": ("streak", "dust", 160, 3.0, 0, False),
    "poison": ("drop", "bubble", 160, 1.0, 20, True),
    "ground": ("chip", "dust", 260, 0.5, 0, False),
    "rock": ("chip", "dust", 280, 0.4, 0, False),
    "flying": ("streak", "mote", 0, 3.0, 90, False),
    "psychic": ("mote", "streak", -10, 2.5, 70, False),
    "bug": ("bug", "mote", 0, 1.5, 120, False),
    "ghost": ("wisp", "mote", -25, 1.8, 90, True),
    "dark": ("wisp", "streak", -10, 2.0, 80, True),
    "steel": ("streak", "chip", 200, 2.5, 0, False),
    "fairy": ("star", "heart", -15, 2.2, 60, False),
    "normal": ("streak", "dust", 120, 3.0, 0, False),
}


def spawn(sim, el, pal, n, x, y, ang=-math.pi / 2, spread=TAU, speed=(30, 90), rng=None, scale=1.0, secondary=False,
          light=True):
    """Spawn n element particles in a velocity cone. secondary picks the element's second particle type."""
    main, sec, g, drag, turb, smoke = STYLE[el]
    kind = sec if secondary else main
    hot = life_ramp(pal)
    sp = (speed[0] * scale, speed[1] * scale)
    common = dict(ang=ang, spread=spread, speed=sp, rng=rng)
    if kind == "flame":
        return sim.emit(n, x, y, life=(0.35, 0.75), size=(1.1 * scale, 2.5 * scale), kind="flame", ramp=hot, g=g,
                        drag=drag, turb=turb, smoke_at=0.72 if smoke else 2, light=(6 * scale, 0.12) if light else None,
                        area=2 * scale, **common)
    if kind == "ember":
        return sim.emit(n, x, y, life=(0.4, 1.0), size=(1, 1.6), kind="px", ramp=hot, g=g * 0.5, drag=1.2,
                        turb=turb * 1.5, flick=0.15, light=(3, 0.08) if light else None, **common)
    if kind == "drop":
        r = [pal[5], pal[3], pal[2], pal[1]]
        return sim.emit(n, x, y, life=(0.4, 0.9), size=(1, 2), kind="drop", ramp=r, g=g, drag=drag, bounce=0.25,
                        smoke_at=0.75 if smoke else 2, light=(4, 0.09) if light else None, **common)
    if kind == "mist":
        return sim.emit(n, x, y, life=(0.4, 0.8), size=(1, 1.5), kind="px", ramp=[pal[4], pal[3], pal[2]], g=-10,
                        drag=3, turb=40, flick=0.3, **common)
    if kind == "leaf":
        return sim.emit(n, x, y, life=(0.6, 1.2), size=(1.5, 2.6), kind="leaf", ramp=[pal[5], pal[3], pal[2]], g=g,
                        drag=drag, turb=turb, spin=8, **common)
    if kind == "mote":
        return sim.emit(n, x, y, life=(0.4, 1.0), size=(1, 1.8), kind="px", ramp=hot, g=g * 0.3, drag=2.5,
                        turb=turb, flick=0.2, light=(4, 0.13) if light else None, **common)
    if kind == "streak":
        return sim.emit(n, x, y, life=(0.2, 0.5), size=(1, 1.6), kind="streak", ramp=hot, g=g, drag=drag,
                        bounce=0.3, light=(4, 0.13) if light else None, **common)
    if kind == "bolt":
        return sim.emit(n, x, y, life=(0.1, 0.25), size=(1, 1.4), kind="streak", ramp=[pal[5], pal[4], pal[3]],
                        g=0, drag=1, light=(5, 0.20) if light else None, **common)
    if kind == "shard":
        return sim.emit(n, x, y, life=(0.4, 0.8), size=(1.5, 3), kind="shard", ramp=[pal[5], pal[3], pal[1]], g=g,
                        drag=drag, spin=6, bounce=0.2, light=(4, 0.11) if light else None, **common)
    if kind == "snow":
        return sim.emit(n, x, y, life=(0.6, 1.2), size=(1, 2), kind="snow", ramp=[pal[5], pal[4], pal[3]], g=25,
                        drag=2, turb=40, **common)
    if kind in ("chip",):
        return sim.emit(n, x, y, life=(0.6, 1.1), size=(1.2 * scale, 2.6 * scale), kind="chip",
                        ramp=[pal[0], pal[2], pal[3], pal[4]], g=g, drag=drag, spin=10, bounce=0.35, **common)
    if kind == "dust":
        return sim.emit(n, x, y, life=(0.6, 1.2), size=(1.6 * scale, 3.2 * scale), kind="smoke", ramp=DUST,
                        g=-8, drag=2.5, turb=30, grow=0.6, **common)
    if kind == "bubble":
        return sim.emit(n, x, y, life=(0.5, 1.1), size=(1, 2.2), kind="bubble", ramp=[pal[5], pal[3], pal[2]],
                        g=-30, drag=2, turb=40, **common)
    if kind == "bug":
        return sim.emit(n, x, y, life=(0.6, 1.4), size=(1, 1.5), kind="bug", ramp=[pal[5], pal[3], pal[1]], g=0,
                        drag=1.0, turb=turb, **common)
    if kind == "wisp":
        return sim.emit(n, x, y, life=(0.5, 1.0), size=(1.2, 2.2), kind="wisp", ramp=hot, g=g, drag=drag,
                        turb=turb, smoke_at=0.7 if smoke else 2, light=(6, 0.13) if light else None, **common)
    if kind == "star":
        return sim.emit(n, x, y, life=(0.4, 0.9), size=(1, 2.2), kind="star", ramp=hot, g=g, drag=drag, turb=turb,
                        light=(5, 0.15) if light else None, **common)
    if kind == "heart":
        return sim.emit(n, x, y, life=(0.5, 1.0), size=(1, 2), kind="heart", ramp=[pal[5], pal[3], pal[2]], g=-20,
                        drag=2, turb=40, **common)
    raise ValueError("unknown particle kind " + kind)


# ------------------------------------------------------------------ projectiles (loops)
def projectile(S, el, head=3.0, trail=1.0, kind=None):
    """Loop facing right: a small flickering head, a trail of shed element particles, light on the head.
    The engine moves it; particles inherit a backwards drift so the trail streams behind."""
    pal = S.pal
    hx, hy = S.w - 16, S.h / 2
    kind = kind or el
    drift = -110.0

    def tick(sim, i, t, rng):
        for p in sim.parts:
            p.x += drift / S.fps * 0.0  # trail drift is given at spawn time
        n = int(1.5 * trail) + (1 if rng.random() < 0.5 else 0)
        if kind in ("rock", "ground"):
            spawn(sim, "ground", ramp("dust") if False else pal, 1, hx - head, hy + 1, ang=math.pi, spread=0.8,
                  speed=(40, 80), rng=rng, secondary=True)
            return
        if kind == "star":
            sim.emit(2, hx - 3, hy, ang=math.pi, spread=0.9, speed=(50, 110), life=(0.3, 0.7), size=(1, 2.2),
                     kind="star", ramp=life_ramp(pal), drag=2, turb=30, rng=rng, light=(4, 0.13))
            return
        parts = spawn(sim, el, pal, n, hx - head * 0.5, hy, ang=math.pi, spread=0.7, speed=(30, 70), rng=rng)
        for p in parts:
            p.vx += drift * 0.6
            p.life *= 0.5
        if rng.random() < 0.4:
            for p in spawn(sim, el, pal, 1, hx - head, hy, ang=math.pi, spread=1.4, speed=(20, 50), rng=rng,
                           secondary=True):
                p.vx += drift * 0.4
                p.life *= 0.6

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        draw_parts(cv, L, sim.parts, rng)
        L.add(hx, hy, head * 4, pal[3], 0.3)
        L.add(hx - 10, hy, head * 4, pal[2], 0.18)
        if kind in ("rock", "ground"):
            s = head + 2
            rot = ph * TAU
            pts = [(hx + math.cos(rot + k * TAU / 6) * s * (0.8 + 0.25 * ((k * 7) % 3) / 2),
                    hy + math.sin(rot + k * TAU / 6) * s * (0.8 + 0.25 * ((k * 5) % 3) / 2)) for k in range(6)]
            cv.poly([(hx + (x - hx) * 1.25, hy + (y - hy) * 1.25) for x, y in pts], pal[0])
            cv.poly(pts, pal[2])
            cv.poly(pts[:3] + [(hx, hy)], pal[3])
            cv.px(pts[1][0], pts[1][1], pal[4])
            for k in range(3):
                streak(cv, hx - s - 2, hy - s + k * s, 1, 0, 6 + (i + k) % 3 * 3, [pal[3], pal[2], pal[1]])
            return
        if kind == "star":
            for k, (dx, dy) in enumerate(((0, 0), (-18, -6), (-30, 5))):
                r = 3 - (k > 0)
                x, y = hx + dx, hy + dy + math.sin((ph + k * 0.3) * TAU) * 1.5
                jag_star(cv, x, y, r + 2 + (i + k) % 2, 4, [pal[3], pal[4], pal[5]], rng, inner=0.3, rot=ph * 2)
                L.add(x, y, 6, pal[4], 0.18)
            return
        if kind == "electric":
            for k in range(3):
                a = rng.uniform(0, TAU)
                bolt(cv, rng, hx, hy, hx + math.cos(a) * 8, hy + math.sin(a) * 7, [pal[3], pal[5]], segs=3, amp=2.5)
            bolt(cv, rng, hx, hy, hx - 22, hy + rng.uniform(-5, 5), [pal[2], pal[4]], segs=5, amp=3)
        flick = 0.85 + 0.3 * noise2(i * 0.9, 3.3, 7)
        rag_blob(cv, hx, hy, head * 1.25 * flick, pal[3], 11 + i, t=ph * 2, rough=0.35, edge=pal[2])
        rag_blob(cv, hx + 0.5, hy - 0.3, head * 0.7, pal[4], 19 + i, t=ph * 3, rough=0.3)
        cv.px(hx + 1, hy - 1, pal[5])
        cv.px(hx + 1, hy, pal[5])
        if kind == "poison":
            cv.px(hx - 1, hy + head + 1, pal[2])
        if kind in ("ghost", "dark"):
            cv.px(hx, hy, pal[0])

    run(S, tick, draw, loop=True, warm=30)


def blade(S, el, count=1):
    """Loop: tapered air/force crescents flying right with wind streaks (never a constant-width arc)."""
    pal = S.pal
    cy = S.h / 2

    def tick(sim, i, t, rng):
        for p in spawn(sim, el, pal, 2, S.w - 20, cy + rng.uniform(-8, 8), ang=math.pi, spread=0.3, speed=(80, 160),
                       rng=rng, light=False):
            p.vx -= 60

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        draw_parts(cv, L, sim.parts, rng)
        for k in range(count):
            x = S.w - 18 - k * 22
            wob = math.sin((ph + k * 0.37) * TAU) * 1.2
            crescent(cv, x - 10, cy + wob, 12 - k * 2, -1.15, 1.15, 4.5 - k, [pal[2], pal[4], pal[5]], squash=1.0)
            L.add(x - 2, cy, 10, pal[3], 0.45)

    run(S, tick, draw, loop=True, warm=20)


def waves_v3(S, el, arcs=3):
    """Loop: tapered sound/force crescents travelling right, each thinning as it grows, with motes."""
    pal = S.pal
    cy = S.h / 2

    def tick(sim, i, t, rng):
        spawn(sim, el, pal, 1, 10, cy + rng.uniform(-10, 10), ang=0, spread=0.8, speed=(40, 90), rng=rng,
              secondary=True, light=False)

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        draw_parts(cv, L, sim.parts, rng)
        for k in range(arcs):
            p = (ph + k / arcs) % 1.0
            r = 6 + p * (S.w - 16)
            crescent(cv, 2, cy, r, -0.5 - 0.25 * (1 - p), 0.5 + 0.25 * (1 - p), 4.5 * (1 - p * 0.6),
                     [pal[1], pal[3], pal[5] if p < 0.4 else pal[4]], squash=1.05)
            L.add(2 + r - 2, cy, 8, pal[3], 0.35 * (1 - p))
        rag_blob(cv, 5, cy, 2.5, pal[4], 3 + i, t=ph, edge=pal[2])
        L.add(5, cy, 10, pal[3], 0.5)

    run(S, tick, draw, loop=True, warm=20)


# ------------------------------------------------------------------ beams (one-shot)
def beam_v3(S, el, width=4.0, charge=0.4, hold=0.6):
    """Gather (particles converge, light grows) -> beam snaps across with a jittering core, ragged edges,
    edge crackle shedding particles, splash at the end -> beam thins and breaks into particles."""
    pal = S.pal
    ox, oy = 10, S.h / 2
    fire_t, end_t = charge, charge + hold
    total = S.n / S.fps

    def width_at(t):
        if t < fire_t:
            return 0
        if t < fire_t + 0.07:
            return width * 0.4
        if t < end_t:
            return width * (1 + 0.15 * math.sin(t * 40))
        return width * max(0, 1 - (t - end_t) / max(0.05, total - end_t - 0.1))

    def tick(sim, i, t, rng):
        if t < fire_t:
            for _ in range(3):
                a = rng.uniform(0, TAU)
                d = rng.uniform(14, 26)
                sim.emit(1, ox + math.cos(a) * d, oy + math.sin(a) * d, ang=a + math.pi, spread=0.2,
                         speed=(d * 2.5, d * 3.2), life=(0.25, 0.4), size=(1, 1.4), kind="streak",
                         ramp=life_ramp(pal), drag=0, rng=rng, light=(3, 0.13))
        w = width_at(t)
        if w > 0.5:
            for _ in range(3):
                x = rng.uniform(ox + 6, S.w - 4)
                side = rng.choice((-1, 1))
                spawn(sim, el, pal, 1, x, oy + side * w, ang=side * math.pi / 2 + rng.uniform(-0.6, 0.6),
                      spread=0.5, speed=(20, 60), rng=rng, light=False)
            spawn(sim, el, pal, 2, S.w - 4, oy, ang=math.pi, spread=2.2, speed=(30, 90), rng=rng)
        if end_t <= t < end_t + 0.1:
            for _ in range(6):
                x = rng.uniform(ox, S.w)
                spawn(sim, el, pal, 1, x, oy, ang=-math.pi / 2, spread=TAU, speed=(10, 40), rng=rng, secondary=True)

    def draw(cv, L, sim, i, t, rng):
        w = width_at(t)
        if t < fire_t:
            k = t / fire_t
            rag_blob(cv, ox, oy, 1 + k * 3.5, pal[4], i, t=t, rough=0.4, edge=pal[3])
            cv.px(ox, oy, pal[5])
            L.add(ox, oy, 6 + k * 14, pal[3], 0.4 + k * 0.6)
        if w > 0.4:
            seed = int(t * 30)
            for x in range(ox, S.w):
                jy = noise2(x * 0.18, t * 9, 3) * (1.2 + w * 0.25)
                edge_n = noise2(x * 0.35, t * 12, 9)
                half = w * (0.8 + 0.35 * edge_n)
                yc = oy + jy
                for y in range(int(yc - half - 1), int(yc + half + 2)):
                    d = abs(y + 0.5 - yc) / max(0.5, half)
                    if d > 1.0:
                        continue
                    c = pal[5] if d < 0.18 else pal[4] if d < 0.45 else pal[3] if d < 0.75 else pal[2]
                    cv.px(x, y, c)
                if (x + seed) % 9 == 0:
                    L.add(x, yc, w * 2 + 4, pal[2], 0.13)
                if el == "electric" and (x * 13 + seed * 7) % 23 == 0:
                    bolt(cv, rng, x, yc, x + rng.uniform(-6, 6), yc + rng.choice((-1, 1)) * (w + 6), [pal[3], pal[5]],
                         segs=3, amp=2)
                if el == "ice" and (x * 7 + seed) % 13 == 0:
                    side = 1 if (x // 13) % 2 else -1
                    for k in range(4):
                        cv.px(x + k * 0.4, yc + side * (half + 1 + k), pal[5 - (k > 1)])
            rag_blob(cv, ox, oy, w * 1.1 + 1, pal[4], 5, t=t, rough=0.35, edge=pal[3])
            L.add(ox, oy, w * 4 + 6, pal[3], 0.5)
            L.add(S.w - 4, oy, w * 3 + 6, pal[3], 0.35)
            jag_star(cv, S.w - 3, oy, w * 1.8 + 3, 6, [pal[3], pal[4], pal[5]], rng, inner=0.35)
        draw_parts(cv, L, sim.parts, rng)

    run(S, tick, draw)


# ------------------------------------------------------------------ impacts (one-shot)
def impact(S, el, power=1.0, ring=False):
    """Hit at (cx, cy) above the ground line: 1-2 flash frames (light + small jagged white), jagged asymmetric
    burst, element debris with gravity bouncing on the ground, smoke/dust drifting and thinning, light pulse."""
    pal = S.pal
    cx, cy = S.anchor
    gy = S.ground
    rs = random.Random(S.rng.randrange(1 << 30))

    def tick(sim, i, t, rng):
        if i == 0:
            wy, wsp = (gy - 2, 1.7) if el == "water" else (cy, TAU * 0.9)  # water sprays up off the floor
            for p in spawn(sim, el, pal, int(24 * power), cx, wy, ang=-math.pi / 2, spread=wsp, speed=(50, 160),
                           rng=rng, scale=power * 1.15):
                p.life *= 1.6
                p.bounce = max(p.bounce, 0.3)
            for p in spawn(sim, el, pal, int(10 * power), cx, cy, ang=-math.pi / 2, spread=TAU, speed=(25, 80), rng=rng,
                           secondary=True, scale=power):
                p.life *= 1.7
            # slow lingering motes that hang in the air and settle (pixelfx "blunt hit" tail)
            sim.emit(int(8 * power), cx, cy, ang=-math.pi / 2, spread=TAU, speed=(8, 30), life=(0.9, 1.4),
                     size=(1, 1.4), kind="px", ramp=life_ramp(pal), g=25, drag=2.2, turb=25, flick=0.15,
                     bounce=0.2, rng=rng, light=(2, 0.05))
            if el != "water":
                sim.emit(int(10 * power), cx, cy, ang=-math.pi / 2, spread=TAU, speed=(90, 220), life=(0.15, 0.35),
                     size=(1, 1.6), kind="streak", ramp=life_ramp(pal), drag=4, g=120, rng=rng, light=(3, 0.13))
        if i == 2 and el in ("fire", "dragon", "normal", "fighting", "rock", "ground", "steel", "poison", "dark",
                             "ghost"):
            nsm = 10 if el in ("fire", "dragon") else 6
            sim.emit(int(nsm * power), cx + rng.uniform(-6, 6), cy + 4, ang=-math.pi / 2, spread=1.6, speed=(14, 40),
                     life=(1.3, 1.9), size=(2.0 * power, 3.4 * power), kind="smoke", ramp=SMOKE, g=-18, drag=1.2,
                     turb=35, grow=0.4, rng=rng)
        if i == 1 and el in ("water", "poison"):
            r = [pal[5], pal[3], pal[2], pal[1]]
            sim.emit(int(18 * power), cx, gy - 1, ang=-math.pi / 2, spread=1.3, speed=(70, 150), life=(0.5, 0.9),
                     size=(1, 2), kind="drop", ramp=r, g=300, drag=0.4, bounce=0.2, rng=rng, area=4, area_y=0)
        if el == "electric" and S.h >= 128 and 6 <= i < 36 and i % 5 == 0:
            # residual sparks hopping off the scorch
            sim.emit(2, cx + rng.uniform(-10, 10), gy - 1, ang=-math.pi / 2, spread=1.4, speed=(30, 70),
                     life=(0.2, 0.4), size=(1, 1.3), kind="streak", ramp=life_ramp(pal), g=260, drag=1, bounce=0.3,
                     rng=rng, light=(3, 0.06))
        if ring and i % 2 == 0 and i < S.n * 0.7:
            for p in spawn(sim, el, pal, 3, cx + rng.uniform(-14, 14), cy + rng.uniform(-10, 8), ang=-math.pi / 2,
                           spread=TAU, speed=(6, 22), rng=rng, light=False):
                p.life *= 1.5
        if 0 < i < 8 and el in ("fire", "dragon"):
            spawn(sim, el, pal, 2, cx + rng.uniform(-6, 6), cy + rng.uniform(-4, 4), rng=rng, speed=(10, 40),
                  scale=power)

    def draw(cv, L, sim, i, t, rng):
        # light pulse: very bright on contact, decays fast
        k = math.exp(-t * 7)
        k2 = math.exp(-t * 2.2)
        L.add(cx, cy, 26 * power, pal[3], 0.7 * k + 0.08 * k2, glint=i < 2)
        L.add(cx, gy, 24 * power, pal[2], 0.3 * k + 0.08 * k2)
        mat = getattr(S, "material", False)
        if el == "water":
            # splash crown on the floor instead of a burst: translucent sheet spikes with foam tips
            if 1 <= i <= 14:
                f = i / 14
                hgt = math.sin(f * math.pi) * 22 * power
                for k in range(-5, 6):
                    x = cx + k * (2.4 + f * 3)
                    top = gy - 2 - hgt * (1 - abs(k) / 6) * (0.7 + 0.3 * abs(noise2(k, 3, 1)))
                    for y in range(int(top), int(gy)):
                        fr = (y - top) / max(1, gy - top)
                        cv.px(x + k * 0.15 * (gy - y) * 0.1, y, _wcol(pal[2] if fr > 0.6 else pal[3], 190))
                    cv.px(x, top, pal[5])
                    cv.px(x, top - 1, pal[5])
        elif i == 0:
            jag_star(cv, cx, cy, 10 * power, 8, [pal[2], pal[3], pal[4]] if mat else [pal[3], pal[4], pal[5]], rs,
                     inner=0.32)
        elif i <= 4:
            r = (16 - i * 2.5) * power
            if not mat:
                rag_blob(cv, cx, cy, (7 - i * 1.4) * power, pal[3], 77 + i, t=i * 0.1, rough=0.5, edge=pal[2],
                         holes=0.1 * i)
            jag_star(cv, cx, cy, r, 9, [pal[1], pal[2], pal[3], pal[4]] if mat else [pal[2], pal[3], pal[4], pal[5]],
                     rs, inner=0.22, rot=i * 0.4)
        if el == "electric" and S.h >= 128:
            ft = i / S.fps
            # scorch: noisy dark patch on the floor, shrinking
            sc = clamp(1 - ft / 1.6)
            if i >= 1 and sc > 0:
                hw = 14 * (0.5 + 0.5 * sc)
                for x in range(int(cx - hw), int(cx + hw) + 1):
                    if noise2(x * 0.5, 3.3, 41) > -0.2 - sc * 0.5:
                        cv.under(x, gy, SCORCH[1])
                        if abs(x - cx) < hw * 0.5:
                            cv.under(x, gy - 1, SCORCH[2])
            # ground crackle crawling outwards for ~1 s
            if 3 <= i and ft < 1.2 and i % 2 == 0:
                for side in (-1, 1):
                    d0 = 4 + ft * 18 + rng.uniform(-3, 3)
                    x0 = cx + side * d0
                    bolt(cv, rng, x0, gy - 1, x0 + side * rng.uniform(4, 9), gy - rng.uniform(1, 5),
                         [pal[3], pal[5]], segs=3, amp=1.5)
                L.add(cx, gy - 2, 18, pal[3], 0.18 * sc)
        if el == "electric" and S.h >= 128 and (i <= 4 or i in (6, 8)):
            for _ in range(2 if i < 3 else 1):
                bolt(cv, rng, cx + rng.uniform(-10, 10), -2, cx, cy, [pal[3], pal[5]], segs=9, amp=7,
                     width=3 if i < 3 else 2, light=L, lcol=pal[4])
        if el in ("water", "poison") and i >= 1:
            k = clamp(1 - i / (S.n * 0.9))
            half = (10 + i * 1.6) * power * (0.4 + 0.6 * k)
            for x in range(int(cx - half), int(cx + half) + 1):
                if noise2(x * 0.4, i * 0.15, 13) > -0.3 + (1 - k) * 0.9:
                    cv.px(x, gy, pal[2] if abs(x - cx) > half * 0.6 else pal[3])
                    if abs(x - cx) < half * 0.4 and noise2(x * 0.9, i * 0.3, 2) > 0.4:
                        cv.px(x, gy - 1, pal[4])
        if ring and 1 <= i <= 12:
            f = out_cubic(i / 12)
            broken_ring(cv, cx, gy, 6 + f * 40 * power, 3 * (1 - f) + 1, [pal[2], pal[3], pal[4]], 21, t,
                        squash=0.3)
        if ring and 2 <= i <= S.n - 4:
            # floor sigil: four tapered arcs on a slowly turning squashed circle, rune ticks between, fading
            fa = clamp(1 - (i - 2) / (S.n - 6))
            rr = 20 * power
            rot = t * 1.6
            for q in range(4):
                a0 = rot + q * TAU / 4 + 0.25
                crescent(cv, cx, gy - 1, rr, a0, a0 + 1.0, 2.6 * fa + 0.6, [pal[1], pal[3], pal[4]], squash=0.32,
                         taper=0.8)
                ta = a0 + 1.28
                for j in range(3):
                    cv.px(cx + math.cos(ta) * (rr - 2 + j), gy - 1 + math.sin(ta) * (rr - 2 + j) * 0.32, pal[4])
            L.add(cx, gy - 1, rr, pal[2], 0.18 * fa)
        if i in (1, 2):
            for a in range(6):
                ang = rs.uniform(0, TAU)
                r0, r1 = 6 * power, (18 + i * 6) * power
                streak(cv, cx + math.cos(ang) * r1, cy + math.sin(ang) * r1, math.cos(ang), math.sin(ang),
                       r1 - r0, [pal[5], pal[4], pal[3]])
        draw_parts(cv, L, sim.parts, rng)

    run(S, tick, draw, ground=gy)


def slash_v3(S, el, count=1, claw=False):
    """Tapered crescent slash(es): 1 smear frame, the arc thick in the middle and thin at the ends, the hot edge
    cools, sparks fly off the tip, light follows the blade."""
    pal = S.pal
    cx, cy = S.anchor
    R = min(S.w, S.h) * 0.36
    dur = 0.3

    def tick(sim, i, t, rng):
        if i == 2:
            tipx, tipy = (cx + R * 0.7, cy + R * 0.6)
            sim.emit(12, tipx, tipy, ang=0.6, spread=1.6, speed=(60, 160), life=(0.15, 0.4), size=(1, 1.6),
                     kind="streak", ramp=life_ramp(pal), drag=3, g=180, rng=rng, light=(3, 0.13))
            spawn(sim, el, pal, 5, cx, cy, rng=rng, secondary=True, speed=(10, 40))

    def draw(cv, L, sim, i, t, rng):
        for c in range(count):
            lt = (t - c * 0.035) / dur
            if not (0 < lt < 1.4):
                continue
            off = (c - (count - 1) / 2) * 7
            if claw:
                a0, a1 = -2.2, -2.2 + 1.5 * min(1, out_quad(min(1, lt * 2.2)))
                rr = R + off
                ccx, ccy = cx - R * 0.55 + off, cy + R * 0.2
            else:
                a0, a1 = -2.5, -2.5 + 2.6 * min(1, out_quad(min(1, lt * 2.2)))
                rr = R + off
                ccx, ccy = cx, cy
            tail = a0 + (a1 - a0) * clamp((lt - 0.25) / 0.9) ** 1.4
            w = 6 * (1 - clamp((lt - 0.4) / 0.9)) + 0.6
            if a1 - tail > 0.05:
                crescent(cv, ccx, ccy, rr, tail, a1, w, [pal[2], pal[4], pal[5]], squash=0.8 if not claw else 1.0,
                         taper=0.7)
                mid = (tail + a1) / 2
                L.add(ccx + math.cos(mid) * rr, ccy + math.sin(mid) * rr * 0.8, 14, pal[3], 0.55 * (1.2 - lt))
            if i == 1 and c == 0:
                crescent(cv, ccx, ccy, rr + 2, a0, a0 + 2.6, 1.2, [pal[3], pal[4], pal[4]], squash=0.8, taper=0.5)
        draw_parts(cv, L, sim.parts, rng)

    run(S, tick, draw, ground=S.ground)


# ------------------------------------------------------------------ areas
def pillar_v3(S, el):
    """Ground telegraph flicker, then a column of rising element particles + core tongues, sparks at the
    base, smoke/mist off the top, light along the column; dies down."""
    pal = S.pal
    cx, gy = S.w / 2, S.ground
    t_on, t_off = 0.2, 1.1

    def tick(sim, i, t, rng):
        if t < t_on:
            sim.emit(2, cx + rng.uniform(-8, 8), gy, ang=-math.pi / 2, spread=0.4, speed=(10, 30),
                     life=(0.2, 0.4), size=(1, 1.4), kind="px", ramp=life_ramp(pal), rng=rng, light=(4, 0.13))
        elif t < t_off:
            k = 1 - (t - t_on) / (t_off - t_on) * 0.5
            for p in spawn(sim, el, pal, int(7 * k), cx, gy - 2, ang=-math.pi / 2, spread=0.35, speed=(120, 200),
                           rng=rng, scale=1.1):
                p.life *= 0.9
            spawn(sim, el, pal, 2, cx, gy - 1, ang=-math.pi / 2, spread=2.6, speed=(30, 90), rng=rng, secondary=True)
            if t < t_on + 0.06:
                sim.emit(14, cx, gy - 1, ang=-math.pi / 2, spread=2.8, speed=(60, 160), life=(0.2, 0.5),
                         size=(1, 1.5), kind="streak", ramp=life_ramp(pal), g=250, drag=2, bounce=0.3, rng=rng)

    def draw(cv, L, sim, i, t, rng):
        if t < t_on:
            L.add(cx, gy, 10 + t * 40, pal[3], 0.3 + t * 2)
        elif t < t_off + 0.3:
            k = clamp(1 - (t - t_off) / 0.3) if t > t_off else 1
            hgt = (gy - 8) * min(1, (t - t_on) / 0.12) * k
            for j in range(3):
                y = gy - (j + 0.5) * hgt * 0.7 / 3
                L.add(cx, y, 12, pal[3], 0.22 * k)
            if k > 0.2:
                for j in range(3):
                    tongue(cv, cx + (j - 1) * 3, gy, 4 - abs(j - 1), hgt * (0.55 + 0.2 * (j == 1)) * k,
                           [pal[2], pal[4], pal[5]], 40 + j, t, lean=noise2(t * 3, j, 4) * 0.08)
        draw_parts(cv, L, sim.parts, rng)
        if t >= t_on:
            L.add(cx, gy, 20, pal[3], 0.5 * math.exp(-(t - t_on) * 2))

    run(S, tick, draw, ground=gy)


def vortex_v3(S, el):
    """Loop: particles riding a rising helix (tornado/whirlpool/leaf storm) with streak tails, dust at the
    base, light on the column. Depth: back half dimmer."""
    pal = S.pal
    cx, gy = S.w / 2, S.ground
    Ht = gy - 8

    def tick(sim, i, t, rng):
        for _ in range(5):
            p = P(x=cx, y=gy, life=rng.uniform(0.8, 1.4), size=rng.uniform(1, 2.2), ramp=life_ramp(pal),
                  seed=rng.randrange(9999), rot=rng.uniform(0, TAU), kind="hel")
            p.data = (rng.uniform(0, TAU), rng.uniform(0.7, 1.1), rng.choice((0, 1, 1)))
            sim.parts.append(p)
        if rng.random() < 0.7:
            spawn(sim, el, pal, 1, cx + rng.uniform(-12, 12), gy, ang=-math.pi / 2, spread=1.2, speed=(10, 30),
                  rng=rng, secondary=True, light=False)

    def draw(cv, L, sim, i, t, rng):
        hel = [p for p in sim.parts if p.kind == "hel"]
        other = [p for p in sim.parts if p.kind != "hel"]
        draw_parts(cv, L, other, rng)
        items = []
        for p in hel:
            a0, sp, kind = p.data
            f = p.t
            a = a0 + p.age * 9 * sp
            r = 3 + f * (S.w / 2 - 8)
            x = cx + math.cos(a) * r
            y = gy - f * Ht + math.sin(a) * r * 0.28
            items.append((math.sin(a), x, y, a, r, p, kind))
        for (z, x, y, a, r, p, kind) in sorted(items):
            front = z > 0
            c = life_col(p.ramp, p.t * 0.6 + (0 if front else 0.35))
            tx, ty = -math.sin(a) * r, math.cos(a) * r * 0.28
            n = math.hypot(tx, ty) or 1
            if kind == 0 and el in ("grass", "fairy", "flying"):
                p.x, p.y, p.rot = x, y, a * 2
                if el == "grass":
                    p.kind = "leaf"
                    p.ramp = [pal[5], pal[3], pal[2]] if front else [pal[3], pal[2], pal[1]]
                    draw_parts(cv, L, [p], rng)
                    p.kind = "hel"
                    p.ramp = life_ramp(pal)
                    continue
            streak(cv, x, y, tx / n, ty / n, 3 + p.size * 2 + (3 if front else 0),
                   [c, life_col(p.ramp, min(1, p.t + 0.3)), life_col(p.ramp, min(1, p.t + 0.5))])
        for j in range(4):
            L.add(cx, gy - (j + 0.5) * Ht / 4, 12 + j * 4, pal[3], 0.3)

    run(S, tick, draw, loop=True, ground=gy, warm=44)


def cloud_v3(S, el):
    """Loop: translucent gas puffs drifting and breaking apart, bubbles rising and popping, faint light."""
    pal = S.pal
    cx, gy = S.w / 2, S.ground

    def tick(sim, i, t, rng):
        if rng.random() < 0.8:
            sim.emit(1, cx + rng.uniform(-S.w * 0.32, S.w * 0.32), gy - rng.uniform(2, 14), ang=-math.pi / 2,
                     spread=1.5, speed=(4, 14), life=(1.0, 1.6), size=(3, 5.5), kind="gas",
                     ramp=[pal[4], pal[3], pal[2], pal[1]], turb=25, grow=0.25, drag=1, rng=rng)
        spawn(sim, el, pal, 1, cx + rng.uniform(-S.w * 0.3, S.w * 0.3), gy - 2, ang=-math.pi / 2, spread=0.6,
              speed=(10, 30), rng=rng, secondary=True)

    def draw(cv, L, sim, i, t, rng):
        for p in sim.parts:
            if p.kind == "gas":
                f = p.t
                a = 176 if 0.15 < f < 0.7 else 96
                rag_blob(cv, p.x, p.y, p.size, life_col(p.ramp, f), p.seed, t=f, rough=0.5, holes=0.12 + f * 0.5,
                         alpha=a)
                L.add(p.x, p.y, p.size * 2.5, pal[2], 0.12 * (1 - f))
        draw_parts(cv, L, [p for p in sim.parts if p.kind != "gas"], rng)

    run(S, tick, draw, loop=True, ground=gy, warm=50)


def weather_v3(S, el, kind="snow"):
    """Loop: diagonal snow/hail on wind streaks, frost motes settling on the ground line."""
    pal = S.pal
    gy = S.ground

    def tick(sim, i, t, rng):
        for _ in range(2):
            sim.emit(1, rng.uniform(-20, S.w), -2, ang=1.15, spread=0.25, speed=(60, 100), life=(0.9, 1.3),
                     size=(0.8, 2.0), kind="snow", ramp=[pal[5], pal[4], pal[3]], turb=35, rng=rng)
        if rng.random() < 0.5:
            sim.emit(1, rng.uniform(-30, S.w * 0.6), rng.uniform(10, gy - 10), ang=0.25, spread=0.1,
                     speed=(150, 220), life=(0.2, 0.35), size=(1.5, 2), kind="streak", ramp=[pal[4], pal[3], pal[2]],
                     rng=rng)

    def draw(cv, L, sim, i, t, rng):
        for k in range(int(S.w / 6)):
            x = k * 6 + (k * 7) % 4
            if noise2(k * 0.7, 0.5, 9) > -0.2:
                cv.px(x, gy, pal[3])
                if k % 3 == 0:
                    cv.px(x + 1, gy - 1, pal[4])
        draw_parts(cv, L, [p for p in sim.parts if p.y < gy], rng)
        L.add(S.w / 2, gy, S.w / 2, pal[2], 0.2)

    run(S, tick, draw, loop=True, ground=gy, warm=40)


def quake_v3(S, el):
    """Ground layer: forked cracks race out along the ground plane (jagged polylines, glowing then cooling),
    chunks pop up and bounce, dust rolls and thins."""
    pal = S.pal
    cx, gy = S.w / 2, S.ground - 6
    rs = random.Random(S.rng.randrange(1 << 30))
    cracks = []
    for k in range(7):
        a = k * TAU / 7 + rs.uniform(-0.3, 0.3)
        L_ = rs.uniform(0.6, 1.0) * (S.w / 2 - 6)
        pts = [(cx, gy)]
        for j in range(1, 8):
            d = L_ * j / 7
            pts.append((cx + math.cos(a) * d + rs.uniform(-3, 3), gy + math.sin(a) * d * 0.3 + rs.uniform(-1.5, 1.5)))
        cracks.append(pts)

    def tick(sim, i, t, rng):
        if i in (2, 5, 8):
            for pts in cracks:
                j = min(len(pts) - 1, i)
                spawn(sim, el, pal, 1, pts[j][0], pts[j][1], ang=-math.pi / 2, spread=1.0, speed=(60, 130), rng=rng)
                spawn(sim, el, pal, 1, pts[j][0], pts[j][1], ang=-math.pi / 2, spread=1.4, speed=(5, 20), rng=rng,
                      secondary=True)

    def draw(cv, L, sim, i, t, rng):
        grow = out_cubic(clamp(t / 0.4))
        heat = clamp(1 - t / 0.8)
        for pts in cracks:
            m = max(1, int(round(grow * (len(pts) - 1))))
            for j, (a, b) in enumerate(zip(pts[:m], pts[1:m + 1])):
                w = 2 if j < 3 else 1
                cv.line(a[0], a[1] + 1, b[0], b[1] + 1, SCORCH[0], w=w + 1)
                cv.line(a[0], a[1], b[0], b[1], pal[4] if heat > 0.5 else pal[2] if heat > 0.15 else SCORCH[2], w=w)
                if heat > 0.2 and j % 2 == 0:
                    L.add(b[0], b[1], 8, pal[3], 0.4 * heat)
        L.add(cx, gy, 40, pal[3], 1.0 * math.exp(-t * 6))
        draw_parts(cv, L, sim.parts, rng)

    run(S, tick, draw, ground=S.ground)


def spikes_v3(S, el):
    """Spikes stab out of the ground in sequence: noise-edged faceted shards (not triangles), chips spray and
    bounce, dust rolls; they crumble back down."""
    pal = S.pal
    gy = S.ground
    rs = random.Random(S.rng.randrange(1 << 30))
    xs = [14 + k * (S.w - 28) / 4 for k in range(5)]
    hs = [rs.uniform(0.55, 1.0) * (gy - 12) for _ in xs]
    leans = [rs.uniform(-0.25, 0.25) for _ in xs]

    def tick(sim, i, t, rng):
        for k, x in enumerate(xs):
            if i == 2 + k * 2:
                spawn(sim, "rock" if el != "steel" else "steel", pal, 6, x, gy - 2, ang=-math.pi / 2, spread=2.2,
                      speed=(50, 120), rng=rng)
                sim.emit(3, x, gy - 1, ang=-math.pi / 2, spread=2.4, speed=(8, 24), life=(0.6, 1.1),
                         size=(2, 3.4), kind="smoke", ramp=DUST, g=-6, drag=2, turb=25, grow=0.5, rng=rng)

    def draw(cv, L, sim, i, t, rng):
        for k, (x, h, ln) in enumerate(zip(xs, hs, leans)):
            st = clamp((i - 2 - k * 2) / 3)
            sink = clamp((t - 0.85) / 0.35)
            hh = h * out_quad(st) * (1 - in_quad(sink))
            if st <= 0:
                if i >= k * 2 - 2:
                    L.add(x, gy, 8, pal[3], 0.3)
                continue
            if hh < 1:
                continue
            w = 3.5 + h / 12
            top = (x + ln * hh, gy - hh)
            for y in range(int(top[1]), int(gy) + 1):
                f = min(1.0, (gy - y) / hh)
                cxl = x + ln * (gy - y)
                half = w * (1 - f) ** 0.85 + 0.4
                nl = noise2(y * 0.5, k * 3.1, 17) * 0.9
                nr = noise2(y * 0.5, k * 3.1 + 9, 17) * 0.9
                for xx in range(int(cxl - half + nl - 1), int(cxl + half + nr + 2)):
                    if xx < cxl - half + nl - 1 or xx > cxl + half + nr + 1:
                        continue
                    if xx <= cxl - half + nl or xx >= cxl + half + nr:
                        c = pal[0]
                    elif xx < cxl - half * 0.2:
                        c = pal[2] if xx > cxl - half * 0.7 else pal[1]
                    else:
                        c = pal[3] if xx > cxl + half * 0.25 else pal[4]
                    cv.px(xx, y, c)
            cv.px(top[0], top[1], pal[5])
            if st < 1:
                L.add(x, gy - hh / 2, 10, pal[3], 0.4)
        draw_parts(cv, L, sim.parts, rng)

    run(S, tick, draw, ground=gy)


def shockwave(S, el, dark=False):
    """Ground shockwave: two broken, uneven, tapering rings squashed onto the floor, dust kicked up along the
    front, a light flash. (A ring by design - the move is literally a ring.)"""
    pal = S.pal
    cx, gy = S.w / 2, S.ground - 4

    def tick(sim, i, t, rng):
        for k in range(2):
            r = 6 + out_cubic(clamp((t - k * 0.12) / 0.6)) * (S.w / 2 - 8)
            if 0.02 < t - k * 0.12 < 0.55:
                a = rng.uniform(0, TAU)
                spawn(sim, el, pal, 1, cx + math.cos(a) * r, gy + math.sin(a) * r * 0.3, ang=-math.pi / 2,
                      spread=1.0, speed=(10, 30), rng=rng, secondary=True, light=False)

    def draw(cv, L, sim, i, t, rng):
        for k in range(2):
            f = clamp((t - k * 0.12) / 0.6)
            if 0 < f < 1:
                r = 6 + out_cubic(f) * (S.w / 2 - 8)
                cols = [pal[0], pal[2], pal[4]] if dark else [pal[2], pal[3], pal[5] if f < 0.3 else pal[4]]
                broken_ring(cv, cx, gy, r, 4 * (1 - f) + 1, cols, 7 + k, t, squash=0.32, keep=0.7 - f * 0.25)
                L.add(cx, gy, r * 0.6, pal[3], 0.2 * (1 - f))
        if dark:
            rag_blob(cv, cx, gy - 1, 4 * clamp(1 - t * 1.5), pal[0], 3, t=t, edge=pal[3])
        L.add(cx, gy, 16, pal[4], 0.6 * math.exp(-t * 8))
        draw_parts(cv, L, sim.parts, rng)

    run(S, tick, draw, ground=S.ground)


def swarm_v3(S, el):
    """Loop: bugs riding a curl-noise flow around a centre, wing flicker, faint light."""
    pal = S.pal
    cx, cy = S.w / 2, S.h / 2

    def tick(sim, i, t, rng):
        for p in spawn(sim, el, pal, 2, cx + rng.uniform(-14, 14), cy + rng.uniform(-8, 8), rng=rng,
                       speed=(20, 50)):
            p.life = rng.uniform(1.0, 1.6)
        for p in sim.parts:
            p.vx += (cx - p.x) * 0.06
            p.vy += (cy - p.y) * 0.1

    def draw(cv, L, sim, i, t, rng):
        draw_parts(cv, L, sim.parts, rng)
        L.add(cx, cy, 24, pal[2], 0.25)

    run(S, tick, draw, loop=True, warm=50)


# ------------------------------------------------------------------ auras and status (loops, unit-scale)
def aura_v3(S, el, rate=3, spread_x=11, lift=(25, 55), kind=None):
    """Loop around a standing unit: element particles rise along the silhouette edges, a flicker of light at
    the feet. No rings."""
    pal = S.pal
    cx, fy = S.w / 2, S.ground

    def tick(sim, i, t, rng):
        for _ in range(rate):
            side = rng.choice((-1, 1))
            x = cx + side * rng.uniform(spread_x * 0.4, spread_x)
            y = fy - rng.uniform(0, 14)
            if kind == "line":
                sim.emit(1, x, y, ang=-math.pi / 2, spread=0.05, speed=(80, 140), life=(0.25, 0.45), size=(1.4, 2),
                         kind="streak", ramp=life_ramp(pal), rng=rng, light=(4, 0.11))
                continue
            for p in spawn(sim, el, pal, 1, x, y, ang=-math.pi / 2, spread=0.5, speed=lift, rng=rng, scale=0.8):
                p.vx += -side * 6
        if rng.random() < 0.6:
            spawn(sim, el, pal, 1, cx + rng.uniform(-spread_x, spread_x), fy - rng.uniform(4, 26),
                  ang=-math.pi / 2, spread=0.8, speed=(10, 25), rng=rng, secondary=True)

    def draw(cv, L, sim, i, t, rng):
        if el == "electric" and i % 3 != 2:
            for k in range(2):
                side = rng.choice((-1, 1))
                x0 = cx + side * rng.uniform(6, spread_x)
                y0 = fy - rng.uniform(4, 30)
                bolt(cv, rng, x0, y0, x0 + side * rng.uniform(2, 7), y0 - rng.uniform(5, 10), [pal[3], pal[5]],
                     segs=3, amp=2, light=L, lcol=pal[3])
        draw_parts(cv, L, sim.parts, rng)
        L.add(cx, fy - 2, 16, pal[2], 0.25 + 0.1 * noise2(i * 0.7, 1, 5))
        for k in range(int(spread_x * 1.4)):
            x = cx - spread_x * 0.7 + k
            if noise2(k * 0.6, t * 6, 3) > 0.15:
                cv.px(x, fy, pal[3])

    run(S, tick, draw, loop=True, ground=fy, warm=40)


def status_v3(S, what):
    """Character-scale status loops sized for the 32 px dummy (feet at S.ground, body centre ~10 px up, head top
    ~25 px up). Each reads at 1x on its own: burn = tongues licking the body + embers + flicker; poison = bubbles
    that rise and pop + drips; sleep = 2-3 Z letters drifting up and growing; paralysis = sparks crawling on the
    body + a twitch flash every 2/3 s; freeze = ice crust shards on the body + frost motes + glint; confusion =
    stars and a bird orbiting the head on a tilted ellipse made of separate motes."""
    pal = S.pal
    cx, fy = S.w / 2, S.ground
    body_y = fy - 10
    head = fy - 27
    # points on the dummy silhouette (body ellipse rx 9 ry 8 + ears), used to anchor crawling effects
    sil = [(cx + math.cos(a) * 9.5, body_y + math.sin(a) * 8.5) for a in [k * TAU / 20 for k in range(20)]]
    sil += [(cx - 4, fy - 23), (cx - 3, fy - 25), (cx + 4, fy - 24), (cx + 5, fy - 26)]
    upper = [p for p in sil if p[1] < body_y + 3]

    def tick(sim, i, t, rng):
        if what == "burn":
            if rng.random() < 0.8:
                sim.emit(1, cx + rng.uniform(-8, 8), body_y - rng.uniform(0, 8), ang=-math.pi / 2, spread=0.6,
                         speed=(18, 40), life=(0.5, 0.9), size=(1, 1.6), kind="px", ramp=life_ramp(pal), g=-25,
                         drag=1.2, turb=50, flick=0.2, rng=rng, light=(3, 0.08))
            if rng.random() < 0.25:
                sim.emit(1, cx + rng.uniform(-5, 5), head + 2, ang=-math.pi / 2, spread=0.4, speed=(8, 16),
                         life=(0.7, 1.1), size=(1.2, 2.0), kind="smoke", ramp=SMOKE, g=-10, drag=1, turb=30,
                         grow=0.3, rng=rng)
        elif what == "poison":
            if i % 4 == 0:
                x, y = rng.choice(upper)
                p = sim.emit(1, x + rng.uniform(-2, 2), y, ang=-math.pi / 2, spread=0.5, speed=(10, 20),
                             life=(0.7, 1.0), size=(1.6, 2.6), kind="pbubble", ramp=[pal[5], pal[4], pal[3], pal[2]],
                             turb=25, drag=1, rng=rng)
            if i % 6 == 3:
                sim.emit(1, cx + rng.uniform(-7, 7), body_y + 6, ang=math.pi / 2, spread=0.1, speed=(2, 6),
                         life=(0.5, 0.7), size=(1, 1.6), kind="drop", ramp=[pal[4], pal[3], pal[2], pal[1]], g=160,
                         rng=rng)
            if rng.random() < 0.4:
                sim.emit(1, cx + rng.uniform(-10, 10), body_y + rng.uniform(-8, 6), ang=-math.pi / 2, spread=1,
                         speed=(4, 10), life=(0.4, 0.7), size=(1, 1), kind="px", ramp=[pal[4], pal[3], pal[2]],
                         turb=20, flick=0.3, rng=rng)
        elif what == "sleep":
            if i % 10 == 0:
                sim.emit(1, cx + 6, head + 2, ang=-1.0, spread=0.05, speed=(13, 13), life=(1.6, 1.6), size=(1, 1),
                         kind="z", ramp=[pal[5], pal[4], pal[3]], drag=0.2, rng=rng)
        elif what == "paralysis":
            if i % 2 == 0:
                x, y = rng.choice(sil)
                sim.emit(2, x, y, ang=rng.uniform(0, TAU), spread=1.2, speed=(30, 70), life=(0.12, 0.25),
                         size=(1, 1.3), kind="streak", ramp=[pal[5], pal[4], pal[3]], drag=3, g=120, rng=rng,
                         light=(3, 0.08))
        elif what == "freeze":
            if rng.random() < 0.45:
                sim.emit(1, cx + rng.uniform(-14, 14), head - rng.uniform(0, 10), ang=math.pi / 2, spread=0.6,
                         speed=(4, 12), life=(0.8, 1.2), size=(1, 2), kind="snow", ramp=[pal[5], pal[4], pal[3]],
                         turb=20, rng=rng)

    rs = random.Random(9)
    crust = []  # ice shards hugging the lower body and sides, plus two on the head
    for k in range(9):
        a = math.pi * (0.05 + 0.9 * k / 8)
        x, y = cx + math.cos(a) * 9.5, body_y + math.sin(a) * 8.0
        crust.append((x, y + 1, -math.pi / 2 + (x - cx) * 0.06 + rs.uniform(-0.25, 0.25), rs.uniform(4, 8)))
    for (x, y) in ((cx - 9, body_y - 3), (cx + 9, body_y - 2), (cx - 3, fy - 23), (cx + 4, fy - 24)):
        crust.append((x, y, -math.pi / 2 + (x - cx) * 0.08, rs.uniform(3, 5)))

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        if what == "burn":
            tongues = [(-7, 0.0, 7), (-2, 0.4, 10), (4, 0.15, 9), (8, 0.65, 6), (1, 0.8, 7)]
            for k, (dx, p0, hmax) in enumerate(tongues):
                f = (ph * 2 + p0) % 1.0
                h = hmax * math.sin(f * math.pi) ** 0.7 + 1
                base = body_y + 2 - abs(dx) * 0.2 - f * 6
                tongue(cv, cx + dx, base, 2.4 - f, h, [pal[2], pal[4], pal[5]], 30 + k, t,
                       lean=noise2(t * 5, k, 9) * 0.25)
            L.add(cx, body_y - 4, 14, pal[3], 0.22 + 0.12 * max(0, noise2(i * 0.9, 2, 3)))
        if what == "paralysis":
            for k in range(2 + (i % 2)):
                a, b = rng.choice(sil), rng.choice(sil)
                if math.hypot(a[0] - b[0], a[1] - b[1]) > 12:
                    b = (a[0] + rng.uniform(-6, 6), a[1] + rng.uniform(-6, 6))
                bolt(cv, rng, a[0], a[1], b[0], b[1], [pal[3], pal[5]], segs=4, amp=2.5)
            L.add(cx, body_y - 3, 12, pal[3], 0.12)
            if i % 20 in (0, 1):  # twitch flash: the silhouette edge lights up
                for (x, y) in sil:
                    cv.px(x, y, pal[5])
                    cv.px(x + rng.choice((-1, 1)), y, pal[4])
                L.add(cx, body_y - 4, 16, pal[4], 0.22)
        if what == "freeze":
            for (x, y, a, ln) in crust:
                ca, sa = math.cos(a), math.sin(a)
                for j in range(int(ln) + 1):
                    w = (1 - j / (ln + 1)) * 1.6
                    for o in range(-int(w), int(w) + 1):
                        c = pal[4] if o <= 0 else pal[2]
                        if j == int(ln):
                            c = pal[5]
                        cv.px(x + ca * j - sa * o, y + sa * j + ca * o, c)
                cv.px(x - sa * 2, y + ca * 2, pal[1])
            g = (ph * 1.4) % 1.4
            if g < 1:
                gx = cx - 12 + g * 24
                for j in range(6):
                    cv.px(gx + j * 0.5, body_y + 4 - j, pal[5])
                L.add(gx, body_y, 6, pal[5], 0.35)
            L.add(cx, body_y, 16, pal[3], 0.15)
        if what == "confusion":
            tilt = 0.25
            items = []
            for k in range(4):
                a = (ph + k / 4) * TAU
                for j in range(1, 7):  # dotted trail of separate motes
                    aa = a - j * 0.13
                    x = cx + math.cos(aa) * 13
                    y = head - 3 + math.sin(aa) * 4 + math.cos(aa) * 13 * tilt
                    if j % 2 == 0:
                        cv.px(x, y, pal[2] if j < 4 else pal[1])
                x = cx + math.cos(a) * 13
                y = head - 3 + math.sin(a) * 4 + math.cos(a) * 13 * tilt
                items.append((math.sin(a), x, y, k))
            for (z, x, y, k) in sorted(items):
                front = z > 0
                if k == 3:  # a little bird
                    c = pal[4] if front else pal[3]
                    for (ax, ay) in ((-2, -1), (-1, 0), (0, 0), (1, 0), (2, -1)):
                        cv.px(x + ax, y + ay - (i % 4 < 2), c)
                    cv.px(x, y + 1, pal[2])
                else:
                    r = 2 if front else 1
                    for kk in range(1, r + 1):
                        for (ax, ay) in ((kk, 0), (-kk, 0), (0, kk), (0, -kk)):
                            cv.px(x + ax, y + ay, pal[4] if front else pal[3])
                    cv.px(x, y, pal[5])
                L.add(x, y, 5, pal[4], 0.25 if front else 0.1)
        for p in sim.parts:
            if p.kind == "pbubble":
                if p.t < 0.8:
                    r = 1 if p.size < 2 else 2
                    for (ax, ay) in ((r, 0), (-r, 0), (0, r), (0, -r)) + (((1, 1), (-1, 1), (1, -1), (-1, -1)) if r == 2 else ()):
                        cv.px(p.x + ax, p.y + ay, pal[3])
                    if r == 2:
                        cv.px(p.x, p.y, pal[1])
                    cv.px(p.x - 1, p.y - 1, pal[5])
                else:  # pop: four specks fly out
                    k = (p.t - 0.8) / 0.2 * 3 + 2
                    for (ax, ay) in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
                        cv.px(p.x + ax * k, p.y + ay * k, pal[4])
            elif p.kind == "z":
                sc = 1 if p.t < 0.4 else 2
                y = p.y - (p.t * 4)
                x = p.x + math.sin(p.age * 4) * 1.5
                cv.text("Z", x, y, life_col(p.ramp, p.t), outline=pal[0], scale=sc)
                L.add(x, y + 3 * sc, 5 * sc, pal[3], 0.2 * (1 - p.t))
        draw_parts(cv, L, [p for p in sim.parts if p.kind not in ("pbubble", "z")], rng)
        if what == "poison":
            L.add(cx, body_y, 14, pal[3], 0.15)

    run(S, tick, draw, loop=True, ground=fy, warm=50)

# ------------------------------------------------------------------ generic systems
def heal_v3(S):
    pal = S.pal
    cx, fy = S.w / 2, S.ground

    def tick(sim, i, t, rng):
        if rng.random() < 0.7:
            sim.emit(1, cx + rng.uniform(-12, 12), fy - rng.uniform(0, 10), ang=-math.pi / 2, spread=0.2,
                     speed=(20, 34), life=(0.8, 1.2), size=(1, 1), kind="glyph", data="+",
                     ramp=[pal[5], pal[4], pal[3], pal[0]], turb=10, rng=rng)
        spawn(sim, "fairy", pal, 1, cx + rng.uniform(-12, 12), fy - rng.uniform(0, 20), rng=rng, speed=(10, 30))

    def draw(cv, L, sim, i, t, rng):
        draw_parts(cv, L, sim.parts, rng)
        L.add(cx, fy - 14, 22, pal[3], 0.4 + 0.15 * math.sin(i / S.n * TAU))

    run(S, tick, draw, loop=True, ground=fy, warm=40)


def stat_v3(S, up=True):
    """Loop: arrow chevrons and streak particles flowing up (stat up) or down (stat down) through the unit."""
    pal = S.pal
    cx, fy = S.w / 2, S.ground
    d = -1 if up else 1

    def tick(sim, i, t, rng):
        if i % 5 == 0:
            y0 = fy - 4 if up else fy - 40
            sim.emit(1, cx + rng.choice((-9, 0, 9)) + rng.uniform(-2, 2), y0, ang=d * math.pi / 2, spread=0,
                     speed=(40, 40), life=(0.8, 0.8), size=(1, 1), kind="arrow", ramp=[pal[5], pal[4], pal[3], pal[0]],
                     rng=rng)
        sim.emit(1, cx + rng.uniform(-13, 13), fy - (4 if up else 40), ang=d * math.pi / 2, spread=0.05,
                 speed=(60, 100), life=(0.3, 0.5), size=(1, 1.4), kind="streak", ramp=life_ramp(pal), rng=rng,
                 light=(3, 0.09))

    def draw(cv, L, sim, i, t, rng):
        for p in sim.parts:
            if p.kind == "arrow":
                x, y = p.x, p.y
                c = life_col(p.ramp, p.t * 0.8)
                # tip at (x, y + d*3): rows narrow toward the direction of travel, stem trails behind
                for k in range(4):
                    cv.line(x - 3 + k, y + d * k, x + 3 - k, y + d * k, c if k < 3 else p.ramp[0])
                    cv.px(x - 4 + k, y + d * k, p.ramp[-1])
                    cv.px(x + 4 - k, y + d * k, p.ramp[-1])
                y0, y1 = sorted((y - d * 1, y - d * 4))
                cv.rect(x - 1, y0, x + 1, y1, life_col(p.ramp, p.t * 0.8 + 0.2))
                L.add(x, y, 7, pal[3], 0.4 * (1 - p.t))
        draw_parts(cv, L, [p for p in sim.parts if p.kind != "arrow"], rng)
        L.add(cx, fy - 16, 20, pal[3], 0.3)

    run(S, tick, draw, loop=True, ground=fy, warm=30)


def burst_generic(S, power=1.0, kind="spark", second=False):
    """Hit spark / crit: jagged white-hot burst, streak sparks with gravity, light flash; crit adds a second
    pop off-centre."""
    pal = S.pal
    cx, cy = S.anchor
    rs = random.Random(S.rng.randrange(1 << 30))

    def tick(sim, i, t, rng):
        if i == 0 or (second and i == 7):
            ox, oy = (0, 0) if i == 0 else (9 * power, -7 * power)
            sim.emit(int(14 * power), cx + ox, cy + oy, ang=0, spread=TAU, speed=(70 * power, 200 * power),
                     life=(0.25, 0.6), size=(1, 1.8), kind="streak", ramp=life_ramp(pal), drag=4, g=150,
                     bounce=0.3, rng=rng, light=(4, 0.13))
            # lingering motes: hang, drift and settle on the floor for ~1 s
            sim.emit(int(10 * power), cx + ox, cy + oy, ang=-math.pi / 2, spread=TAU, speed=(10, 45),
                     life=(0.7, 1.2), size=(1, 1.4), kind="px", ramp=life_ramp(pal), drag=2.2, g=30, flick=0.15,
                     bounce=0.2, turb=20, rng=rng)

    def draw(cv, L, sim, i, t, rng):
        for (t0, ox, oy, pw) in ((0, 0, 0, power), (7, 9 * power, -7 * power, power * 0.6)):
            if not second and t0:
                continue
            j = i - t0
            if 0 <= j <= 3:
                r = (9 - j * 2) * pw + (2 if j == 1 else 0)
                jag_star(cv, cx + ox, cy + oy, r, 8, [pal[2], pal[3], pal[4], pal[5]][j // 2:], rs, inner=0.25,
                         rot=j * 0.3)
            if j >= 0:
                L.add(cx + ox, cy + oy, 22 * pw, pal[4], 1.4 * math.exp(-j / S.fps * 9))
        draw_parts(cv, L, sim.parts, rng)

    run(S, tick, draw, ground=S.ground)


def converge(S, kind="charge"):
    """Loop: particles stream inwards on curved paths to a flickering core with growing light."""
    pal = S.pal
    cx, cy = S.anchor

    def tick(sim, i, t, rng):
        for _ in range(3):
            a = rng.uniform(0, TAU)
            d = rng.uniform(16, 26)
            sim.emit(1, cx + math.cos(a) * d, cy + math.sin(a) * d, ang=a + math.pi + 0.5, spread=0.2,
                     speed=(d * 2.4, d * 3.0), life=(0.32, 0.4), size=(1, 1.5), kind="streak", ramp=life_ramp(pal)[::-1],
                     drag=0, rng=rng, light=(3, 0.11))
        for p in sim.parts:
            p.vx += (cx - p.x) * 0.9
            p.vy += (cy - p.y) * 0.9

    def draw(cv, L, sim, i, t, rng):
        draw_parts(cv, L, sim.parts, rng)
        f = 0.8 + 0.3 * noise2(i * 0.8, 1, 2)
        rag_blob(cv, cx, cy, 2.5 * f, pal[4], i, t=i / S.n, edge=pal[3])
        cv.px(cx, cy, pal[5])
        L.add(cx, cy, 16 * f, pal[4], 0.8)

    run(S, tick, draw, loop=True, warm=20)


def sparkle_burst(S, text=None, rise=False, flash=True):
    """Send-out / level-up style: light flash, star motes bursting outwards (or rising), optional text stamp."""
    pal = S.pal
    cx, fy = S.w / 2, S.ground

    def tick(sim, i, t, rng):
        if i == 0:
            sim.emit(18, cx, fy - 14, ang=-math.pi / 2, spread=TAU, speed=(30, 90), life=(0.5, 1.0),
                     size=(1, 2.2), kind="star", ramp=life_ramp(pal), drag=2.5, g=-10 if rise else 30, rng=rng,
                     light=(5, 0.18))
        if rise and t < 0.8:
            sim.emit(2, cx + rng.uniform(-12, 12), fy, ang=-math.pi / 2, spread=0.1, speed=(50, 90),
                     life=(0.5, 0.8), size=(1, 1.6), kind="streak", ramp=life_ramp(pal), rng=rng, light=(3, 0.09))

    def draw(cv, L, sim, i, t, rng):
        if flash and t < 0.25:
            k = 1 - t / 0.25
            for y in range(0, int(fy)):
                if noise2(y * 0.3, t * 20, 4) > 1 - k * 1.5:
                    cv.px(cx + noise2(y * 0.2, t * 9, 8) * 2, y, pal[5])
            jag_star(cv, cx, fy - 14, 10 * k + 2, 6, [pal[3], pal[4], pal[5]], random.Random(i), inner=0.3)
        L.add(cx, fy - 14, 30, pal[4], 1.2 * math.exp(-t * 4))
        L.add(cx, fy, 26, pal[3], 0.5 * math.exp(-t * 3))
        draw_parts(cv, L, sim.parts, rng)
        if text and 0.15 < t < S.n / S.fps - 0.1:
            pop = min(1, (t - 0.15) / 0.12)
            cv.text(text, cx, 6 + (1 - pop) * 4, pal[5], outline=pal[0])
            L.add(cx, 9, 14, pal[4], 0.4)

    run(S, tick, draw, ground=fy)


def faint_v3(S):
    pal = S.pal
    cx, fy = S.w / 2, S.ground

    def tick(sim, i, t, rng):
        if i == 0:
            sim.emit(8, cx, fy - 1, ang=-math.pi / 2, spread=2.8, speed=(10, 30), life=(0.8, 1.3), size=(2, 3.4),
                     kind="smoke", ramp=DUST, g=-6, drag=2, turb=30, grow=0.5, rng=rng)
        if t < 0.6:
            sim.emit(3, cx + rng.uniform(-10, 10), fy - rng.uniform(2, 24), ang=-math.pi / 2, spread=0.6,
                     speed=(10, 30), life=(0.5, 0.9), size=(1, 1.6), kind="px", ramp=life_ramp(pal), turb=40,
                     drag=1.5, flick=0.2, rng=rng, light=(3, 0.11))

    def draw(cv, L, sim, i, t, rng):
        draw_parts(cv, L, sim.parts, rng)
        L.add(cx, fy - 12, 18, pal[3], 0.4 * math.exp(-t * 2))

    run(S, tick, draw, ground=fy)


def miss_v3(S):
    pal = S.pal
    cx, fy = S.w / 2, S.ground

    def tick(sim, i, t, rng):
        if i == 0:
            sim.emit(5, cx - 4, fy - 1, ang=math.pi, spread=1.2, speed=(10, 40), life=(0.5, 0.9), size=(1.5, 2.6),
                     kind="smoke", ramp=DUST, g=-6, drag=3, grow=0.4, rng=rng)
        if i < 6:
            sim.emit(2, cx, fy - rng.uniform(6, 24), ang=math.pi, spread=0.1, speed=(120, 160), life=(0.15, 0.25),
                     size=(1.2, 1.6), kind="streak", ramp=[pal[5], pal[4], pal[3]], rng=rng)

    def draw(cv, L, sim, i, t, rng):
        if t < 0.35:
            g = out_cubic(clamp(t / 0.3))
            for k, off in enumerate((-14, -7)):
                ghost = __import__("pxfx.core", fromlist=["Canvas"]).Canvas(S.w, S.h)
                draw_creature(ghost, int(cx + off * g), int(fy), flip=True, mono=pal[2 + k])
                for yy in range(S.h):
                    for xx in range(S.w):
                        if ghost.pa[xx, yy][3] and (xx + yy + k + i) % (2 + k) == 0:
                            cv.px(xx, yy, ghost.pa[xx, yy])
        draw_parts(cv, L, sim.parts, rng)
        pop = out_cubic(clamp((t - 0.05) / 0.15))
        if t < S.n / S.fps - 0.15:
            cv.text("MISS", cx, fy - 40 - pop * 5 - t * 6, pal[5], outline=pal[0])

    run(S, tick, draw, ground=fy)


def evolve_v3(S):
    """Quickening white silhouette beats inside rising light motes; ends in a big light flash."""
    pal = S.pal
    cx, fy = S.w / 2, S.ground
    total = S.n / S.fps

    def tick(sim, i, t, rng):
        sim.emit(2, cx + rng.uniform(-16, 16), fy - rng.uniform(0, 10), ang=-math.pi / 2, spread=0.15,
                 speed=(30, 60), life=(0.6, 1.0), size=(1, 2), kind="star", ramp=life_ramp(pal), rng=rng,
                 light=(4, 0.13))

    def draw(cv, L, sim, i, t, rng):
        f = t / total
        beat = math.sin(f * f * 12 * math.pi)
        white = beat > 0.2 or f > 0.85
        draw_creature(cv, int(cx), int(fy), mono=pal[5] if white else None, pal=ramp("white") if not white else None)
        L.add(cx, fy - 14, 24 + 10 * max(0, beat), pal[4], 0.5 + 0.6 * max(0, beat) + (2.0 if f > 0.85 else 0))
        draw_parts(cv, L, sim.parts, rng)

    run(S, tick, draw, ground=fy)


def recall_v3(S):
    """Red recall: a jittering thin beam appears at full length, the unit turns red, shrinks and is pulled up
    as red motes, light on the beam."""
    pal = S.pal
    cx, fy = S.w / 2, S.ground
    total = S.n / S.fps

    def tick(sim, i, t, rng):
        f = t / total
        if 0.25 < f < 0.75:
            sim.emit(3, cx + rng.uniform(-8, 8), fy - rng.uniform(4, 22), ang=-math.pi / 2, spread=0.3,
                     speed=(40, 90), life=(0.3, 0.6), size=(1, 1.6), kind="streak", ramp=life_ramp(pal), rng=rng,
                     light=(3, 0.11))

    def draw(cv, L, sim, i, t, rng):
        f = t / total
        if f < 0.9:
            for y in range(0, int(fy - 14)):
                j = noise2(y * 0.2, t * 15, 4) * 0.8
                cv.px(cx + j, y, pal[5])
                if y % 3 == 0:
                    cv.px(cx + j + 1, y, pal[3])
            for j in range(0, int(fy), 8):
                L.add(cx, j, 8, pal[3], 0.4)
        sh = 1 - in_quad(clamp((f - 0.2) / 0.55))
        if sh > 0.1:
            lift = clamp((f - 0.4) / 0.4) * 18
            draw_creature(cv, int(cx), int(fy - lift), sx=sh, sy=sh, pal=pal if f > 0.15 else None)
            if f > 0.15:
                L.add(cx, fy - lift - 12 * sh, 16 * sh + 4, pal[3], 0.6)
        draw_parts(cv, L, sim.parts, rng)

    run(S, tick, draw, ground=fy)


def shield_v3(S):
    """Loop: a shimmering barrier: a broken, tapering dome edge drawn by noise (not a clean circle), hex
    glints drifting over it, motes sliding along the edge, soft light."""
    pal = S.pal
    cx, fy = S.w / 2, S.ground
    R = S.w / 2 - 6
    cy = fy - R * 0.55

    def tick(sim, i, t, rng):
        a = rng.uniform(math.pi * 1.05, math.pi * 1.95)
        sim.emit(1, cx + math.cos(a) * R, cy + math.sin(a) * R * 0.95, ang=a + math.pi / 2, spread=0.2,
                 speed=(20, 40), life=(0.4, 0.7), size=(1, 1.4), kind="px", ramp=life_ramp(pal), drag=1, rng=rng,
                 light=(3, 0.11))

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        steps = 120
        for k in range(steps):
            a = math.pi + k / (steps - 1) * math.pi
            n = noise2(k * 0.12, ph * 6, 3)
            if n > 0.45:
                continue
            w = 1 + (n < -0.2) + (n < -0.55)
            for j in range(w):
                c = pal[5] if j == 0 and n < -0.4 else pal[4] if j == 0 else pal[3]
                cv.px(cx + math.cos(a) * (R - j), cy + math.sin(a) * (R - j) * 0.95, c)
        for k in range(10):
            gx = cx + noise2(k * 1.7, ph * 2, 6) * R * 0.7
            gy = cy + noise2(k * 1.3 + 5, ph * 2, 6) * R * 0.5
            if (k + i) % 4 < 2:
                for (ax, ay) in ((0, 0), (1, 0), (-1, 1), (2, 1), (0, 2), (1, 2)):
                    cv.px(gx + ax, gy + ay, pal[3])
        for k in range(int(R * 1.6)):
            x = cx - R * 0.8 + k
            if noise2(k * 0.5, ph * 5, 1) > -0.1:
                cv.px(x, fy, pal[3])
        draw_parts(cv, L, sim.parts, rng)
        L.add(cx, cy + 4, R * 1.2, pal[2], 0.35)

    run(S, tick, draw, loop=True, ground=fy, warm=24)


def cutin_v3(S):
    """Full-screen crit cut-in plate: white flash, then dark plate with tapered speed lines rushing inwards
    (each line a streak, varied weight), dithering out. Opaque by design."""
    from .core import bayer
    pal = S.pal
    cx, cy = S.w / 2, S.h / 2
    rs = random.Random(S.rng.randrange(1 << 30))
    lines = [(rs.uniform(0, TAU), rs.uniform(0.3, 0.6), rs.randint(1, 3)) for _ in range(54)]
    R = math.hypot(S.w, S.h) / 2 + 4
    for i, cv in enumerate(S.frames):
        L = S.lights[i]
        if i == 0:
            cv.rect(0, 0, S.w - 1, S.h - 1, pal[5])
            for y in range(S.h):
                for x in range(S.w):
                    d = math.hypot((x - cx) / (S.w / 2), (y - cy) / (S.h / 2))
                    if d > 0.8 and bayer(x, y) < (d - 0.8) * 2:
                        cv.px(x, y, pal[3])
            L.add(cx, cy, S.w * 0.6, pal[5], 1.0)
            continue
        cv.rect(0, 0, S.w - 1, S.h - 1, pal[0])
        for (a, inner, w) in lines:
            a2 = a + i * 0.03
            r0 = R * (inner + 0.08 * ((i * 3 + int(a * 10)) % 3))
            x1, y1 = cx + math.cos(a2) * R, cy + math.sin(a2) * R * 0.75
            L_ = R - r0
            for k in range(int(L_)):
                f = k / L_
                x = x1 - math.cos(a2) * k
                y = y1 - math.sin(a2) * k * 0.75
                c = pal[5] if f < 0.4 else pal[4] if f < 0.75 else pal[2]
                cv.px(x, y, c)
                if w == 3 and f < 0.5:
                    cv.px(x + 1, y, pal[4])
        if i >= S.n - 2:
            cv.dissolve(0.35 + 0.3 * (i - (S.n - 2)), seed=i)


# ------------------------------------------------------------------ unit acting
def unit_v3(S, act):
    """Unit animations with acting (frame-exact, no particles except dust): idle, lunge (wind-up hold, dash
    smear, contact freeze, recover), recoil (white flash, freeze, knockback + shake, blink, settle), faint."""
    fy = S.ground
    n = S.n
    for i, cv in enumerate(S.frames):
        L = S.lights[i]
        t = i / (n - 1)
        if act == "idle":
            b = math.sin(i / n * TAU)
            draw_creature(cv, S.w // 2, fy, sx=1 + 0.05 * b, sy=1 - 0.06 * b, eye=(i not in (8, 9)))
        elif act == "lunge":
            # 0-0.22 crouch back (anticipation, held), 0.22-0.3 dash (smear), 0.3-0.45 contact freeze,
            # 0.45-1 recover back home
            x0 = 22
            if t < 0.22:
                u = out_quad(t / 0.22)
                x, sx, sy, lean = -5 * u, 1 + 0.14 * u, 1 - 0.14 * u, -2 * u
            elif t < 0.3:
                u = (t - 0.22) / 0.08
                x, sx, sy, lean = -5 + 37 * out_cubic(u), 0.86, 1.12, 3
                for k in range(3):
                    gx = x0 + int(-5 + 37 * out_cubic(u) - (k + 1) * 7)
                    ghost = draw_creature
                    ghost(cv, gx, fy, sx=0.86, sy=1.12, mono=(110 - k * 20, 108 - k * 20, 130 - k * 20, 255))
            elif t < 0.45:
                x, sx, sy, lean = 32, 1.06, 0.95, 2
            else:
                u = in_quad((t - 0.45) / 0.55) if t < 0.8 else 1.0
                u = min(1.0, (t - 0.45) / 0.4)
                x, sx, sy, lean = 32 * (1 - out_quad(u)), 1.0, 1.0, 0
            draw_creature(cv, x0 + int(round(x)), fy, sx=sx, sy=sy, lean=int(lean))
            if 0.3 <= t < 0.45:
                L.add(x0 + 32 + 12, fy - 14, 12, (255, 240, 200, 255), 0.6)
        elif act == "recoil":
            fl = (255, 255, 255, 255) if i < 3 else None
            if 3 <= i < 6:
                kb, sh = 0, 0  # freeze on contact
                fl = (255, 236, 236, 255) if i == 3 else None
            else:
                u = clamp((i - 6) / 10)
                kb = 8 * out_quad(min(1, u * 2)) * (1 - u)
                sh = (2 if i % 2 else -2) if 6 <= i < 10 else 0
            if i in (16, 18, 20):
                continue
            draw_creature(cv, S.w // 2 + int(kb) + sh, fy, sx=0.92 if i < 8 else 1.0, sy=1.06 if i < 8 else 1.0,
                          lean=-2 if i < 12 else 0, flash=fl)
            if i < 3:
                L.add(S.w // 2, fy - 14, 18, (255, 255, 255, 255), 0.6)
        elif act == "faint":
            sy = 1 - out_quad(clamp((t - 0.25) / 0.3)) * 0.55
            sx = 1 + clamp((t - 0.25) / 0.3) * 0.28
            wob = int(math.sin(t * 30) * 2 * (1 - clamp(t / 0.25))) if t < 0.25 else 0
            if t < 0.88:
                draw_creature(cv, S.w // 2 - int(clamp(t / 0.25) * 3) + wob, fy, sx=sx, sy=sy, eye=t < 0.2)
            fade = clamp((t - 0.6) / 0.35)
            if fade > 0:
                cv.dissolve(fade, seed=3)


# ------------------------------------------------------------------ water (material: no glow)
def _wcol(c, a):
    return (c[0], c[1], c[2], a)


def water_jet(S):
    """Pressurised stream (material): pressure build at the mouth, a translucent blue body 8-14 px thick that
    flares toward the target, darker underside, white foam ripples running forward along the top edge, bulges,
    droplets peeling off on gravity arcs, mist, a splash crown + spray fan at the target and water running
    down to the floor; at the end the stream breaks into falling drops. No light except a glint at contact."""
    pal = S.pal
    ox, oy = S.anchor[0], S.anchor[1]
    gy = S.ground
    total = S.n / S.fps
    t_on, t_off = 0.3, 1.0
    tx = S.w - 6
    drops = [pal[5], pal[3], pal[2], pal[1]]

    def thick(x, t):
        f = (x - ox) / (tx - ox)
        base = 4 + 3 * f  # half-thickness: 8 px at the mouth -> 14 px at the target
        bulge = 1.6 * noise2(x * 0.12 - t * 9, 1.7, 5)
        return max(1.5, base + bulge)

    def head_at(t):
        if t < t_on:
            return ox
        return ox + (tx - ox) * min(1, (t - t_on) / 0.12)

    def tail_at(t):
        if t < t_off:
            return ox
        return ox + (tx - ox) * min(1, (t - t_off) / 0.35)

    def tick(sim, i, t, rng):
        h, tl = head_at(t), tail_at(t)
        if t < t_on:
            if rng.random() < 0.5:
                sim.emit(1, ox + 3, oy + rng.uniform(-3, 3), ang=math.pi / 2, spread=0.6, speed=(5, 15),
                         life=(0.4, 0.6), size=(1, 1.5), kind="drop", ramp=drops, g=200, rng=rng)
            return
        if h > tl + 4:
            for _ in range(3):  # droplets peeling off the edges
                x = rng.uniform(max(tl, ox + 10), h)
                top = rng.random() < 0.6
                y = oy + (-1 if top else 1) * thick(x, t)
                sim.emit(1, x, y, ang=(-0.9 if top else 0.6), spread=0.6, speed=(30, 80), life=(0.5, 0.9),
                         size=(1, 2), kind="drop", ramp=drops, g=260, drag=0.3, bounce=0.2, rng=rng)
            if h >= tx - 1 and t < t_off + 0.1:
                # splash crown + spray fan back from the target, water running down
                sim.emit(4, tx, oy, ang=math.pi + 0.0, spread=2.4, speed=(60, 150), life=(0.4, 0.8), size=(1, 2.2),
                         kind="drop", ramp=drops, g=300, drag=0.4, bounce=0.2, rng=rng)
                sim.emit(2, tx - 2, oy + 6, ang=math.pi / 2, spread=0.3, speed=(20, 50), life=(0.5, 0.8),
                         size=(1.2, 2), kind="drop", ramp=drops, g=320, bounce=0.1, rng=rng)
                if rng.random() < 0.5:
                    sim.emit(1, tx - 6, oy + rng.uniform(-8, 8), ang=math.pi, spread=1.6, speed=(6, 18),
                             life=(0.6, 1.0), size=(2, 3.4), kind="mistpuff", ramp=[pal[4], pal[3]], g=-6, drag=1.5,
                             turb=20, grow=0.4, rng=rng)
        if t_off <= t < t_off + 0.4:  # the stream breaks into drops that fall
            for _ in range(5):
                x = rng.uniform(tl, max(tl + 1, h))
                sim.emit(1, x, oy + rng.uniform(-4, 4), ang=0.2, spread=0.6, speed=(20, 60), life=(0.6, 1.0),
                         size=(1.2, 2.4), kind="drop", ramp=drops, g=300, bounce=0.2, rng=rng)

    def draw(cv, L, sim, i, t, rng):
        h, tl = head_at(t), tail_at(t)
        if t < t_on:  # pressure build: bulging blob at the mouth
            k = t / t_on
            r = 2 + k * 4 + math.sin(t * 40) * 0.6
            for dy in range(-int(r) - 1, int(r) + 2):
                for dx in range(-int(r) - 1, int(r) + 2):
                    d = math.hypot(dx / 1.2, dy)
                    if d <= r:
                        c = pal[4] if (dx < -1 and dy < -1) else pal[3] if dy < 1 else pal[2]
                        cv.px(ox + dx, oy + dy, _wcol(c, 200))
        if h > tl + 1:
            for x in range(int(tl), int(min(h, tx)) + 1):
                th = thick(x, t)
                if x < ox + 4:
                    th *= 0.7
                yc = oy + noise2(x * 0.08 - t * 6, 4.4, 2) * 1.2
                top, bot = yc - th, yc + th
                for y in range(int(top), int(bot) + 1):
                    f = (y - top) / max(1, bot - top)  # 0 top -> 1 bottom
                    if f < 0.14:
                        c, a = pal[4], 255
                    elif f < 0.45:
                        c, a = pal[3], 190
                    elif f < 0.8:
                        c, a = pal[2], 175
                    else:
                        c, a = pal[1], 215
                    cv.px(x, y, _wcol(c, a))
                # foam ripples running forward along the top edge
                if noise2(x * 0.25 - t * 14, 7.1, 9) > 0.15:
                    cv.px(x, top, pal[5])
                    if noise2(x * 0.5 - t * 14, 2.2, 3) > 0.35:
                        cv.px(x, top - 1, pal[5])
                        cv.px(x, top + 1, pal[5])
                if noise2(x * 0.3 - t * 10, 9.9, 4) > 0.55:
                    cv.px(x, yc - th * 0.35, pal[5])
            if h >= tx - 1 and t < t_off + 0.2:
                # crown at the target: foam spikes and a sheet of water folding back
                for k in range(7):
                    a = math.pi * (0.55 + k * 0.15)
                    ln = 5 + 6 * abs(noise2(k * 1.3, t * 6, 11))
                    for j in range(int(ln)):
                        cv.px(tx + math.cos(a) * j, oy + math.sin(a) * j * 1.3, pal[5] if j > ln - 2 else _wcol(pal[3], 210))
                # water running down from the hit point to the floor, puddle on the ground
                for y in range(int(oy + 8), int(gy)):
                    w = noise2(y * 0.4, t * 8, 6)
                    cv.px(tx - 2 + w, y, _wcol(pal[3], 200))
                    if (y + i) % 5 == 0:
                        cv.px(tx - 2 + w, y, pal[5])
                L.add(tx, oy, 6, pal[5], 0.25, glint=True)
        if t >= t_on:
            ph = min(1.0, (t - t_on) / (total - t_on))
            pw = 6 + ph * 18
            for x in range(int(tx - pw), int(tx + 4)):
                if noise2(x * 0.5, 1.3, 8) > -0.4:
                    cv.px(x, gy, _wcol(pal[2], 210))
                    if noise2(x * 0.9, 2.1, 1) > 0.5:
                        cv.px(x, gy - 1, pal[4])
        for p in sim.parts:
            if p.kind == "mistpuff":
                rag_blob(cv, p.x, p.y, p.size, life_col(p.ramp, p.t), p.seed, t=p.t, rough=0.5,
                         holes=0.35 + p.t * 0.5, alpha=110 if p.t < 0.5 else 70)
        draw_parts(cv, L, [p for p in sim.parts if p.kind != "mistpuff"], rng)

    run(S, tick, draw, ground=gy)


def _bubble(cv, x, y, r, pal):
    """One bubble: thin outline, empty inside with a faint inner rim tint, 1-2 px white highlight top-left,
    a small reflection bottom-right. Round on purpose - a bubble is round."""
    xi, yi = int(round(x)), int(round(y))
    ri = int(math.ceil(r)) + 1
    for dy in range(-ri, ri + 1):
        for dx in range(-ri, ri + 1):
            d = math.hypot(dx, dy)
            if r - 0.55 < d <= r + 0.45:
                cv.px(xi + dx, yi + dy, pal[3] if dy < 0 else pal[2])
            elif r >= 2.5 and r - 1.5 < d <= r - 0.55:
                cv.px(xi + dx, yi + dy, _wcol(pal[3], 90))
            elif d <= r - 1.5:
                cv.px(xi + dx, yi + dy, _wcol(pal[4], 45))
    hx, hy = xi - int(r * 0.45), yi - int(r * 0.45)
    cv.px(hx, hy, pal[5])
    if r >= 2.5:
        cv.px(hx + 1, hy, pal[5])
        cv.px(hx, hy + 1, pal[5])
    if r >= 3.5:
        cv.px(xi + int(r * 0.5), yi + int(r * 0.5), pal[4])


def bubble_shot(S):
    """Loop: a cluster of 7 bubbles (3-10 px) wobbling and drifting forward at slightly different speeds; the
    small ones trail behind; a few micro-bubbles. The engine moves the cluster."""
    pal = S.pal
    rs = random.Random(31)
    hx, hy = S.w - 18, S.h / 2
    bubs = []
    for k in range(7):
        r = [5.6, 4.6, 3.8, 3.0, 2.4, 2.0, 1.6][k]
        bubs.append((r, hx - k * 8 - rs.uniform(0, 4), hy + rs.uniform(-7, 7), rs.random(), rs.choice((1, 2))))
    micro = [(rs.uniform(0, 1), rs.uniform(-1, 1)) for _ in range(8)]
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        for (u, oy) in micro:
            p = (ph + u) % 1.0
            cv.px(hx - 20 - p * 40, hy + oy * 8 - p * 3, pal[3] if p < 0.6 else pal[2])
        for (r, x, y, p0, m) in sorted(bubs, key=lambda b: b[0]):
            # wobble: drift forward/back at its own rate (periodic), bob vertically, squash a little
            dx = math.sin((ph * m + p0) * TAU) * 2.5
            dy = math.sin((ph * 2 + p0) * TAU) * 1.5
            _bubble(cv, x + dx, y + dy, r + 0.25 * math.sin((ph * 3 + p0) * TAU), pal)


def bubble_pop(S):
    """Impact for bubble shots: bubbles arrive and pop one after another - each leaves a broken ring flash and
    3-5 droplets that fall; a tiny glint on each pop."""
    pal = S.pal
    cx, cy = S.anchor
    rs = random.Random(7)
    pops = [(cx + rs.uniform(-12, 12), cy + rs.uniform(-10, 8), rs.uniform(2, 4.5), 2 + k * 3) for k in range(6)]
    drops = [pal[5], pal[3], pal[2], pal[1]]

    def tick(sim, i, t, rng):
        for (x, y, r, f) in pops:
            if i == f:
                sim.emit(rng.randint(3, 5), x, y, ang=-math.pi / 2, spread=2.6, speed=(30, 70), life=(0.4, 0.8),
                         size=(1, 1.6), kind="drop", ramp=drops, g=260, bounce=0.2, rng=rng)

    def draw(cv, L, sim, i, t, rng):
        for (x, y, r, f) in pops:
            if i < f:
                _bubble(cv, x - (f - i) * 2.5, y, r, pal)
            elif i < f + 3:
                k = i - f
                rr = r + 1 + k * 1.5
                for a in range(12):
                    if (a + k) % 3 == 0:
                        continue
                    aa = a * TAU / 12
                    cv.px(x + math.cos(aa) * rr, y + math.sin(aa) * rr, pal[5] if k == 0 else pal[3])
                if k == 0:
                    L.add(x, y, 5, pal[5], 0.3, glint=True)
        draw_parts(cv, L, sim.parts, rng)

    run(S, tick, draw, ground=S.ground)


def whirlpool(S):
    """Loop (material): a water vortex lying on the floor around the target - translucent spiral arms squashed
    onto the ground plane, darker toward the eye, white foam on the arm crests, a low churning wall of water at
    the rim with spray, drops flung outward."""
    pal = S.pal
    cx, gy = S.w / 2, S.ground - 4
    R = S.w / 2 - 14
    sq = 0.36
    drops = [pal[5], pal[3], pal[2], pal[1]]

    def tick(sim, i, t, rng):
        if rng.random() < 0.7:
            a = rng.uniform(0, TAU)
            sim.emit(1, cx + math.cos(a) * R, gy + math.sin(a) * R * sq, ang=-math.pi / 2 + math.cos(a) * 0.6,
                     spread=0.4, speed=(30, 70), life=(0.4, 0.7), size=(1, 1.8), kind="drop", ramp=drops, g=260,
                     rng=rng)

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        back, front = [], []
        # translucent water body: the bowl, darker toward the eye
        for y in range(int(gy - R * sq) - 1, int(gy + R * sq) + 2):
            for x in range(int(cx - R) - 1, int(cx + R) + 2):
                d = math.hypot((x - cx) / R, (y - gy) / (R * sq))
                if d > 1:
                    continue
                a = math.atan2((y - gy) / sq, x - cx)
                # 3 spiral arms rotating inward, broken up by noise so they churn instead of reading as a logo
                arm = math.sin(a * 3 + d * 9 - ph * TAU * 3 + noise2(x * 0.15, y * 0.3, 7) * 1.4)
                c = pal[1] if d < 0.22 else pal[2] if arm < 0.1 else pal[3]
                if arm > 0.9 and d > 0.3 and noise2(x * 0.5, y * 0.8 + ph * 8, 3) > -0.3:
                    c = pal[5] if d > 0.55 else pal[4]
                cv.px(x, y, _wcol(c, 255 if c in (pal[5], pal[4]) else 185 if d > 0.25 else 220))
        # ribbons of water winding around the target on tilted ellipses, tightening as they rise
        for k, (hgt, rr, sp) in enumerate(((6, R * 0.8, 1.0), (13, R * 0.62, 1.3), (20, R * 0.45, 1.7))):
            a0 = ph * TAU * sp + k * 2.1
            for half in (0, 1):  # back half first, front half after the bowl so it wraps around the body
                aa = a0 + half * math.pi
                crescent(cv, cx, gy - hgt, rr, aa, aa + 2.2, 2.4 - k * 0.4,
                         [_wcol(pal[2], 200), _wcol(pal[3], 210), pal[5]], squash=0.34, taper=0.8)
            bx = cx + math.cos(a0 + 1.1) * rr
            by = gy - hgt + math.sin(a0 + 1.1) * rr * 0.34 - 2
            _bubble(cv, bx, by, 1.6 + k * 0.4, pal)
        # churning wall at the rim: short rising curtains, front half drawn over the bowl
        for k in range(28):
            a = k / 28 * TAU + ph * TAU
            x = cx + math.cos(a) * R
            y = gy + math.sin(a) * R * sq
            hgt = 3 + 3 * (0.5 + 0.5 * noise2(k * 0.7, ph * 4, 5))
            col = pal[3] if math.sin(a) > 0 else pal[2]
            for j in range(int(hgt)):
                cv.px(x, y - j, _wcol(col, 210))
            cv.px(x, y - int(hgt), pal[5])
        draw_parts(cv, L, sim.parts, rng)

    run(S, tick, draw, loop=True, ground=S.ground, warm=24)


def water_gun(S):
    """Water Gun (material): the SMALL water move - a narrow 3-5 px stream made of droplets and dots, bright
    cyan/white core on a mid-blue edge, specks shed off it, quick (~0.4 s travel), ends in a small splash."""
    pal = S.pal
    ox, oy = S.anchor
    tx = S.w - 6
    gy = S.ground
    t_on, t_off = 0.1, 0.55
    drops = [pal[5], pal[3], pal[2], pal[1]]

    def head(t):
        return ox + (tx - ox) * clamp((t - t_on) / 0.18)

    def tail(t):
        return ox + (tx - ox) * clamp((t - t_off) / 0.18)

    def tick(sim, i, t, rng):
        h, tl = head(t), tail(t)
        if h > tl + 2 and rng.random() < 0.8:
            x = rng.uniform(tl, h)
            sim.emit(1, x, oy + rng.uniform(-2, 2), ang=rng.choice((-1.0, 0.7)), spread=0.6, speed=(15, 45),
                     life=(0.3, 0.6), size=(1, 1.4), kind="drop", ramp=drops, g=240, rng=rng)
        if h >= tx - 1 and t < t_off + 0.15:
            sim.emit(3, tx, oy, ang=math.pi, spread=2.2, speed=(30, 90), life=(0.3, 0.6), size=(1, 1.8),
                     kind="drop", ramp=drops, g=280, bounce=0.2, rng=rng)

    def draw(cv, L, sim, i, t, rng):
        h, tl = head(t), tail(t)
        for x in range(int(tl), int(h) + 1):
            y = oy + noise2(x * 0.15 - t * 20, 2, 3) * 0.8
            if (x * 3 + i) % 7 < 5:  # dotted: the stream is made of drops, with gaps
                cv.px(x, y - 1, _wcol(pal[3], 210))
                cv.px(x, y, pal[4] if (x + i) % 3 else pal[5])
                cv.px(x, y + 1, _wcol(pal[2], 220))
            elif (x + i) % 2:
                cv.px(x, y, pal[3])
        if t < t_on + 0.05:
            cv.px(ox + 1, oy, pal[5])
            cv.px(ox, oy - 1, pal[4])
        draw_parts(cv, L, sim.parts, rng)
        if h >= tx - 1 and t < t_off + 0.1:
            L.add(tx, oy, 5, pal[5], 0.3, glint=True)
            for k in range(5):
                a = math.pi * (0.6 + k * 0.2)
                cv.px(tx + math.cos(a) * 3, oy + math.sin(a) * 3, pal[5])

    run(S, tick, draw, ground=gy)


def surf_wave(S):
    """Surf (material): a wave arrives from the attacker side (~0.45 s) - curved crest leaning forward, white
    foam along the top, dark-to-light blue translucent body - then crashes over the target (~0.45 s): the crest
    collapses into foam spray and drops flying up and forward, the body drains away leaving a puddle."""
    pal = S.pal
    cx, gy = S.anchor[0], S.ground
    W = S.w
    drops = [pal[5], pal[3], pal[2], pal[1]]
    t_arrive, t_crash = 0.45, 0.9

    def front_x(t):
        return -10 + (cx + 14 + 10) * out_quad(clamp(t / t_arrive))

    def height_at(x, t):
        fx = front_x(t)
        if x > fx + 2:
            return 0
        d = fx - x  # distance behind the front
        crest = 30 * (1 - clamp((t - t_arrive) / (t_crash - t_arrive)) * 0.85)
        h = crest * math.exp(-d / 26) * (1 - math.exp(-(d + 3) / 4))
        h *= 1 - clamp((t - t_crash) / 0.5)
        return max(0, h + noise2(x * 0.2, t * 6, 3) * 1.5)

    def tick(sim, i, t, rng):
        fx = front_x(t)
        if t_arrive - 0.05 < t < t_crash:
            for _ in range(4):
                sim.emit(1, fx - rng.uniform(0, 8), gy - height_at(fx - 4, t), ang=-0.9, spread=1.2,
                         speed=(60, 140), life=(0.4, 0.8), size=(1, 2), kind="drop", ramp=drops, g=300, drag=0.3,
                         bounce=0.2, rng=rng)
        elif t < t_arrive and rng.random() < 0.6:
            sim.emit(1, fx, gy - height_at(fx - 3, t), ang=-0.6, spread=0.8, speed=(30, 70), life=(0.3, 0.5),
                     size=(1, 1.5), kind="drop", ramp=drops, g=280, rng=rng)

    def draw(cv, L, sim, i, t, rng):
        for x in range(0, W):
            h = height_at(x, t)
            if h < 0.6:
                continue
            top = gy - h
            # the crest leans forward: the top few px shift toward the front
            for y in range(int(top), int(gy) + 1):
                f = (y - top) / max(1, h)
                c, a = (pal[3], 200) if f < 0.3 else (pal[2], 190) if f < 0.7 else (pal[1], 215)
                lean = int((1 - f) * 3) if t < t_crash else 0
                cv.px(x + lean, y, _wcol(c, a))
            # foam on the crest: broken white sawtooth
            if noise2(x * 0.35, t * 10, 9) > -0.2:
                cv.px(x + 3, top, pal[5])
                cv.px(x + 3, top - 1, pal[5] if (x + i) % 3 else pal[4])
            if noise2(x * 0.5, t * 8, 4) > 0.45:
                cv.px(x + 2, top + 3, pal[5])
        if t > t_crash:  # puddle draining
            k = clamp(1 - (t - t_crash) / 0.6)
            for x in range(int(cx - 30 * k - 6), int(cx + 30 * k + 6)):
                if noise2(x * 0.4, 7, 2) > -0.3 + (1 - k):
                    cv.px(x, gy, _wcol(pal[2], 200))
        if t_arrive - 0.05 < t < t_arrive + 0.1:
            L.add(front_x(t), gy - 20, 7, pal[5], 0.3, glint=True)
        draw_parts(cv, L, sim.parts, rng)

    run(S, tick, draw, ground=gy)


# ------------------------------------------------------------------ fire (emissive), designed per move
def tongue_dir(cv, x, y, ang, w, length, cols, seed, t, bend=2.0):
    """Flame tongue along any direction: wide flickering base at (x, y) tapering to a bent tip.
    cols = [edge (dark red), body (orange), core (yellow/white)]."""
    ca, sa = math.cos(ang), math.sin(ang)
    L = max(2, int(length))
    for k in range(L):
        f = k / L
        half = w * (1 - f) ** 0.85 * (0.75 + 0.4 * noise2(f * 3 + seed % 31, t * 8, seed))
        off = noise2(f * 2.5, t * 6 + seed % 17, seed + 3) * f * bend
        bx, by = x + ca * k - sa * off, y + sa * k + ca * off
        n = int(math.ceil(half))
        for j in range(-n, n + 1):
            d = abs(j) / max(0.6, half)
            if d > 1:
                continue
            c = cols[0] if d > 0.66 else cols[1] if (d > 0.28 or f > 0.55) else cols[2]
            cv.px(bx - sa * j, by + ca * j, c)


def _fcols(pal, heat=1.0):
    return [pal[1], pal[3], pal[5] if heat > 0.6 else pal[4]]


def fireball(S):
    """Loop: a fireball with a real flame body - hot round-ish core, flame tongues streaming backwards and
    flickering, a dark red edge, embers and a little smoke shed behind; light on the head."""
    pal = S.pal
    hx, hy = S.anchor

    def tick(sim, i, t, rng):
        for p in spawn(sim, "fire", pal, 1, hx - 6, hy + rng.uniform(-3, 3), ang=math.pi, spread=0.6,
                       speed=(30, 70), rng=rng, scale=0.8):
            p.vx -= 40
            p.life *= 0.6
        if rng.random() < 0.6:
            for p in spawn(sim, "fire", pal, 1, hx - 8, hy, ang=math.pi, spread=1.4, speed=(20, 50), rng=rng,
                           secondary=True):
                p.vx -= 50

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        draw_parts(cv, L, sim.parts, rng)
        for k, (dy, ln, w) in enumerate(((0, 26, 5.5), (-4, 18, 3.4), (4, 17, 3.2), (-2, 22, 2.6), (3, 12, 2.4))):
            ln2 = ln * (0.85 + 0.25 * noise2(ph * 6 + k, 1.3, 7))
            tongue_dir(cv, hx + 2, hy + dy * 0.8, math.pi + dy * 0.03, w, ln2, _fcols(pal), 50 + k, t, bend=3)
        rag_blob(cv, hx + 1, hy, 4.6, pal[4], 9 + i, t=ph * 3, rough=0.25, edge=pal[3])
        rag_blob(cv, hx + 2, hy - 0.5, 2.4, pal[5], 13 + i, t=ph * 4, rough=0.25)
        L.add(hx, hy, 16, pal[3], 0.55)
        L.add(hx - 12, hy, 12, pal[2], 0.25)

    run(S, tick, draw, loop=True, warm=24)


def embers_shot(S):
    """Loop: Ember - four small separate fireballs in a loose low formation, orange with yellow tips, each
    with a short flickering tail; clearly smaller than the fireball."""
    pal = S.pal
    hx, hy = S.anchor
    slots = [(hx, hy, 0.0), (hx - 18, hy - 7, 0.3), (hx - 34, hy + 4, 0.6), (hx - 50, hy - 3, 0.15)]

    def tick(sim, i, t, rng):
        for (x, y, u) in slots:
            if rng.random() < 0.5:
                for p in spawn(sim, "fire", pal, 1, x - 3, y, ang=math.pi, spread=1.2, speed=(15, 40), rng=rng,
                               secondary=True):
                    p.vx -= 40

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        draw_parts(cv, L, sim.parts, rng)
        for k, (x, y, u) in enumerate(slots):
            yy = y + math.sin((ph + u) * TAU) * 1.5
            tongue_dir(cv, x + 1, yy, math.pi, 2.6, 9 + 3 * noise2(ph * 5, k, 2), _fcols(pal), 70 + k, t)
            rag_blob(cv, x + 1, yy, 2.2, pal[4], 30 + k + i, t=ph * 3, rough=0.3, edge=pal[3])
            cv.px(x + 1, yy - 1, pal[5])
            L.add(x, yy, 8, pal[3], 0.3)

    run(S, tick, draw, loop=True, warm=24)


def flamethrower(S):
    """Flamethrower: a continuous jet shaped as a wedge (narrow at the mouth, wide at the target) with wavy
    flickering edges, dark red rim, orange body and a yellow-white core line, sparks shed along it; ~0.9 s of
    flow, then the target is engulfed in a burst and embers."""
    pal = S.pal
    ox, oy = S.anchor
    tx = S.w - 8
    t_on, t_off = 0.15, 1.05

    def head(t):
        return ox + (tx - ox) * clamp((t - t_on) / 0.2)

    def tail(t):
        return ox + (tx - ox) * clamp((t - t_off) / 0.25)

    def tick(sim, i, t, rng):
        h, tl = head(t), tail(t)
        if h > tl + 4:
            for _ in range(3):
                x = rng.uniform(tl, h)
                f = (x - ox) / (tx - ox)
                spawn(sim, "fire", pal, 1, x, oy + rng.uniform(-1, 1) * (2 + f * 9), ang=-math.pi / 2, spread=1.4,
                      speed=(10, 40), rng=rng, scale=0.7)
            if h >= tx - 1:
                spawn(sim, "fire", pal, 3, tx, oy, ang=math.pi, spread=2.6, speed=(30, 90), rng=rng, scale=1.1)
                spawn(sim, "fire", pal, 2, tx, oy, rng=rng, secondary=True, speed=(30, 90))

    def draw(cv, L, sim, i, t, rng):
        h, tl = head(t), tail(t)
        for x in range(int(tl), int(h) + 1):
            f = (x - ox) / (tx - ox)
            half = 1.5 + f * 10 + 1.8 * noise2(x * 0.18 - t * 16, 3, 4)
            yc = oy + noise2(x * 0.09 - t * 10, 8, 2) * (1 + f * 3)
            for y in range(int(yc - half), int(yc + half) + 1):
                d = abs(y - yc) / max(0.6, half)
                edge = noise2(x * 0.5 - t * 20, y * 0.5, 6) * 0.25
                if d > 1 + edge:
                    continue
                c = pal[1] if d > 0.78 else pal[3] if d > 0.42 else pal[4] if d > 0.16 else pal[5]
                cv.px(x, y, c)
            if x % 8 == 0:
                L.add(x, yc, 6 + f * 12, pal[3], 0.3)
        if h >= tx - 1 and t < t_off + 0.3:
            for k in range(5):
                a = math.pi + (k - 2) * 0.55
                tongue_dir(cv, tx, oy, a, 3.5, 10 + 4 * noise2(t * 8, k, 5), _fcols(pal), 90 + k, t)
            L.add(tx, oy, 22, pal[4], 0.7)
        draw_parts(cv, L, sim.parts, rng)

    run(S, tick, draw, ground=S.ground)


def fire_blast(S):
    """Fire Blast: a five-armed star of flame (the big 'big-character' shape) bursts out of a white-hot core in
    ~0.2 s, washes the target with a 2-3 frame flash, then flickers and shrinks over ~0.6 s, shedding embers
    and smoke."""
    pal = S.pal
    cx, cy = S.anchor
    gy = S.ground
    arms = [(-math.pi / 2 + k * TAU / 5) for k in range(5)]

    def tick(sim, i, t, rng):
        if i == 0:
            spawn(sim, "fire", pal, 18, cx, cy, ang=-math.pi / 2, spread=TAU, speed=(60, 150), rng=rng, scale=1.2)
            spawn(sim, "fire", pal, 14, cx, cy, rng=rng, secondary=True, speed=(50, 140))
        if 6 <= i <= 22 and i % 3 == 0:
            a = rng.choice(arms)
            spawn(sim, "fire", pal, 2, cx + math.cos(a) * 16, cy + math.sin(a) * 16, ang=a, spread=0.6,
                  speed=(20, 50), rng=rng)

    def draw(cv, L, sim, i, t, rng):
        grow = out_cubic(clamp(t / 0.2))
        fade = clamp((t - 0.35) / 0.6)
        if fade < 1:
            for k, a in enumerate(arms):
                ln = (22 + 4 * noise2(t * 6, k, 3)) * grow * (1 - fade * 0.8)
                w = 6.5 * (1 - fade * 0.6)
                heat = 1 - fade
                tongue_dir(cv, cx, cy, a, w, ln, _fcols(pal, heat), 110 + k, t, bend=2.5)
            rag_blob(cv, cx, cy, 7 * (1 - fade * 0.7) + 1, pal[4], 5 + i, t=t, rough=0.3, edge=pal[3])
            rag_blob(cv, cx, cy, 4 * (1 - fade), pal[5], 7 + i, t=t, rough=0.3)
        if i < 3:
            L.add(cx, cy, 40, pal[5], 1.0)
        L.add(cx, cy, 30 * (1 - fade * 0.5), pal[3], 0.8 * (1 - fade) + 0.1)
        L.add(cx, gy, 24, pal[2], 0.4 * (1 - fade))
        draw_parts(cv, L, sim.parts, rng)

    run(S, tick, draw, ground=gy)


def fire_spin(S):
    """Loop: Fire Spin - a vortex of flame tongues circling the target on a tilted ellipse and rising, back half
    drawn behind (dimmer), front half over the body, tongues leaning with the rotation, a flame ribbon swirling
    up through them; embers spiral up."""
    pal = S.pal
    cx, gy = S.anchor[0], S.ground

    def tick(sim, i, t, rng):
        a = rng.uniform(0, TAU)
        spawn(sim, "fire", pal, 1, cx + math.cos(a) * 18, gy - 6 + math.sin(a) * 5, ang=-math.pi / 2, spread=0.5,
              speed=(30, 70), rng=rng, secondary=True)

    def ribbon(cv, ph, front):
        for k in range(260):
            u = k / 260
            a = (ph * 1.5 + u * 1.6) * TAU
            if (math.sin(a) > 0) != front:
                continue
            r = 20 - u * 8
            x = cx + math.cos(a) * r
            y = gy - 4 - u * 30 + math.sin(a) * r * 0.3
            w = 2.5 * math.sin(u * math.pi) + 0.5
            for j in range(-int(w), int(w) + 1):
                cv.px(x, y + j, (pal[4] if abs(j) < w * 0.4 else pal[3]) if front else pal[2])

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        items = []
        for k in range(16):
            a = (k / 16 + ph) * TAU
            lvl = (k % 2) / 2
            r = 19 - lvl * 5
            y = gy - 1 - lvl * 8 + math.sin(a) * r * 0.3
            x = cx + math.cos(a) * r
            items.append((math.sin(a), x, y, a, k, lvl))
        ribbon(cv, ph, False)
        for (z, x, y, a, k, lvl) in sorted(items):
            front = z > 0
            cols = [pal[1], pal[3], pal[4]] if front else [pal[0], pal[1], pal[2]]
            lean = -math.cos(a) * 0.45
            h = (16 - lvl * 4) * (0.8 + 0.4 * noise2(ph * 6, k, 2)) * (1.0 if front else 0.8)
            tongue_dir(cv, x, y, -math.pi / 2 + lean, 3.6 if front else 2.6, h, cols, 130 + k, t, bend=2.5)
        ribbon(cv, ph, True)
        draw_parts(cv, L, sim.parts, rng)
        L.add(cx, gy - 12, 26, pal[3], 0.5 + 0.1 * noise2(i, 1, 3))

    run(S, tick, draw, loop=True, ground=gy, warm=30)


def flame_wheel(S):
    """Loop: Flame Wheel / Fire Punch charge - the unit is wrapped in a spinning wheel of fire: flame tongues set
    on a circle around the body, each trailing against the spin, so the ring reads as rolling; embers fly off the
    rim. Different silhouette from Fire Spin (that one is a ground vortex around the target)."""
    pal = S.pal
    cx, fy = S.w / 2, S.ground
    cy = fy - 15
    R = 19

    def tick(sim, i, t, rng):
        a = rng.uniform(0, TAU)
        spawn(sim, "fire", pal, 1, cx + math.cos(a) * R, cy + math.sin(a) * R, ang=a, spread=0.4, speed=(20, 50),
              rng=rng, secondary=True)

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        for k in range(12):
            a = (k / 12 + ph / 3) * TAU
            x, y = cx + math.cos(a) * R * 0.85, cy + math.sin(a) * R
            tang = a - math.pi / 2          # trail against a clockwise spin
            ln = 11 + 4 * noise2(ph * 6, k, 3)
            tongue_dir(cv, x, y, tang, 3.2, ln, _fcols(pal), 150 + k, t, bend=2)
        draw_parts(cv, L, sim.parts, rng)
        L.add(cx, cy, 24, pal[3], 0.45 + 0.1 * noise2(i, 2, 5))

    run(S, tick, draw, loop=True, ground=fy, warm=24)


# ------------------------------------------------------------------ electric (emissive), designed per move
def _arc(cv, rng, x0, y0, x1, y1, pal, segs=4, amp=3.0, width=1, L=None):
    return bolt(cv, rng, x0, y0, x1, y1, [pal[3], pal[5]] if width > 1 else [pal[5]], segs=segs, amp=amp,
                width=width, light=L, lcol=pal[4])


def spark_ball(S):
    """Loop: Thunder Shock as a projectile - a small round crackling ball (white core, yellow body, dark rim) with
    4-5 short jagged arcs leaping off its surface, redrawn every frame, and loose sparks hopping behind. No comet
    tail: the ball jitters instead."""
    pal = S.pal
    hx, hy = S.anchor

    def tick(sim, i, t, rng):
        if rng.random() < 0.7:
            spawn(sim, "electric", pal, 1, hx - 4, hy, ang=math.pi, spread=1.6, speed=(30, 80), rng=rng,
                  secondary=True)

    def draw(cv, L, sim, i, t, rng):
        jx, jy = rng.choice((-1, 0, 0, 1)), rng.choice((-1, 0, 0, 1))
        x, y = hx - 3 + jx, hy + jy
        draw_parts(cv, L, sim.parts, rng)
        for k in range(rng.randint(4, 5)):
            a = rng.uniform(0, TAU)
            r0, r1 = 4.5, rng.uniform(9, 15)
            _arc(cv, rng, x + math.cos(a) * r0, y + math.sin(a) * r0, x + math.cos(a + rng.uniform(-0.6, 0.6)) * r1,
                 y + math.sin(a) * r1 * 0.8, pal, segs=3, amp=3)
        cv.disc(x, y, 5, pal[2])
        cv.disc(x, y, 4, pal[4])
        cv.disc(x - 0.5, y - 0.5, 2, pal[5])
        L.add(x, y, 14, pal[4], 0.55 + 0.25 * rng.random())

    run(S, tick, draw, loop=True, warm=10)


def thunder(S):
    """Thunder: a storm cloud darkens the top of the frame (pre-beat), then a thick branching bolt falls from above
    onto the target with a white flash, re-strikes twice, a disc of yellow light and crawling ground arcs spread at
    the feet, sparks hop; ~1.3 s."""
    pal = S.pal
    cx, gy = S.anchor[0], S.ground
    top = 4
    strikes = (8, 14, 19)

    def tick(sim, i, t, rng):
        if i in strikes:
            spawn(sim, "electric", pal, 10, cx, gy - 4, ang=-math.pi / 2, spread=2.6, speed=(50, 140), rng=rng,
                  secondary=True)

    def draw(cv, L, sim, i, t, rng):
        # storm cloud: dark ragged blob band at the top, flickering lighter on strikes
        if i < 34:
            lit = any(0 <= i - s < 2 for s in strikes)
            k = clamp(i / 6) * (1 - clamp((i - 26) / 8))
            for j in range(5):
                bx = cx + (j - 2) * 15 + 3 * noise2(j, i * 0.1, 3)
                rag_blob(cv, bx, top + 6 + (j % 2) * 3, (9 + (j % 3) * 2) * k, (96, 96, 128) if lit else (40, 38, 58),
                         20 + j, t=t * 0.5, rough=0.35, edge=(62, 60, 86) if lit else (28, 26, 40))
        for s in strikes:
            d = i - s
            if 0 <= d < 3:
                w = 3 if (d == 0 and s == strikes[0]) else 2
                pts = _arc(cv, rng, cx + rng.uniform(-8, 8), top + 10, cx, gy - 2, pal, segs=9, amp=9, width=w, L=L)
                for _ in range(2):
                    p0 = pts[rng.randint(2, 5)]
                    _arc(cv, rng, p0[0], p0[1], p0[0] + rng.uniform(-22, 22), p0[1] + rng.uniform(10, 30), pal,
                         segs=4, amp=4)
                if d == 0:
                    L.add(cx, gy - 20, 60, pal[5], 1.0)
                    cv.ellipse(cx, gy - 1, 16, 4, pal[5])
        if i >= strikes[0]:
            u = clamp((i - strikes[0]) / 22)
            rx = 6 + u * 34
            fade = 1 - u
            if fade > 0.05:
                for k in range(int(rx * 4)):
                    a = k / (rx * 4) * TAU
                    x, y = cx + math.cos(a) * rx, gy - 1 + math.sin(a) * rx * 0.22
                    if noise2(a * 3, i * 0.3, 9) > -0.3 + u * 0.6:
                        cv.px(x, y, pal[4] if fade > 0.5 else pal[2])
                L.add(cx, gy, rx + 8, pal[3], 0.5 * fade)
            if i < 36 and i % 2 == 0:
                for _ in range(2):
                    a = rng.choice((-1, 1))
                    x0 = cx + a * rng.uniform(2, 8)
                    _arc(cv, rng, x0, gy - 1, x0 + a * rng.uniform(8, 20), gy - rng.uniform(0, 3), pal, segs=4, amp=2)
        draw_parts(cv, L, sim.parts, rng)

    run(S, tick, draw, ground=gy)


def thunderbolt(S):
    """Thunderbolt: thin jagged bolts with 2-4 sharp kinks are thrown at the target from the upper left, three
    quick strikes ~0.1 s apart, each with a white flash on the target and a few side branches, then 0.3 s of small
    crackling arcs jumping over the body; ~0.8 s."""
    pal = S.pal
    cx, cy = S.anchor
    strikes = (2, 6, 10)

    def tick(sim, i, t, rng):
        if i in strikes:
            spawn(sim, "electric", pal, 6, cx, cy, rng=rng, secondary=True, speed=(40, 120))

    def draw(cv, L, sim, i, t, rng):
        for n, s in enumerate(strikes):
            d = i - s
            if 0 <= d < 2:
                sx = 4 + n * 10
                pts = _arc(cv, rng, sx, 4 + n * 6, cx, cy, pal, segs=5, amp=10, width=2, L=L)
                p0 = pts[rng.randint(1, 3)]
                _arc(cv, rng, p0[0], p0[1], p0[0] + rng.uniform(4, 16), p0[1] + rng.uniform(6, 16), pal, segs=3, amp=3)
                if d == 0:
                    cv.disc(cx, cy, 7, pal[5])
                    L.add(cx, cy, 30, pal[5], 0.9)
        if strikes[-1] <= i < strikes[-1] + 12:
            for _ in range(3):
                a = rng.uniform(0, TAU)
                x0, y0 = cx + math.cos(a) * 9, cy + math.sin(a) * 9
                _arc(cv, rng, x0, y0, x0 + rng.uniform(-8, 8), y0 + rng.uniform(-8, 8), pal, segs=3, amp=2)
            L.add(cx, cy, 16, pal[4], 0.3)
        draw_parts(cv, L, sim.parts, rng)

    run(S, tick, draw, ground=S.ground)


def thunder_wave(S):
    """Loop: Thunder Wave / static field - a jagged electric ring circles the unit's middle and squeezes in, with
    arcs jumping from the ring to the body; reads as 'held by a ring of electricity', not as rising sparks."""
    pal = S.pal
    cx, fy = S.w / 2, S.ground
    cy = fy - 13

    def tick(sim, i, t, rng):
        pass

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        for ring in range(2):
            u = (ph + ring * 0.5) % 1
            rx = 19 - u * 8
            yy = cy - 7 + u * 14
            pts = []
            for k in range(41):
                a = k / 40 * TAU
                j = rng.uniform(-2.5, 2.5) if k % 2 else 0
                pts.append((cx + math.cos(a) * (rx + j), yy + math.sin(a) * (rx * 0.3) + j * 0.8, math.sin(a)))
            for a, b in zip(pts, pts[1:]):
                if rng.random() < 0.12:
                    continue
                front = a[2] > 0
                col = (pal[5] if u < 0.5 else pal[4]) if front else pal[2]
                cv.line(a[0], a[1], b[0], b[1], col)
            L.add(cx, yy, rx, pal[4], 0.25 * (1 - u))
        if i % 3 != 2:
            a = rng.uniform(0, TAU)
            _arc(cv, rng, cx + math.cos(a) * 18, cy + math.sin(a) * 5, cx + math.cos(a) * 7,
                 cy + rng.uniform(-8, 6), pal, segs=3, amp=2)

    run(S, tick, draw, loop=True, ground=fy, warm=0)


# ------------------------------------------------------------------ grass (material), designed per move
PETAL = [(110, 34, 72), (196, 84, 138), (240, 150, 196), (255, 214, 234), (255, 246, 250)]


def leaf_shape(cv, x, y, ang, L, W, cols, vein=True, tip=0.8):
    """Pointed-oval leaf (lens) along ang: dark outline, body, highlight on the side facing the top-left light,
    centre vein. cols = [edge, body, light, vein]. W can be foreshortened (tumbling)."""
    x, y = int(math.floor(x + 0.5)), int(math.floor(y + 0.5))
    ca, sa = math.cos(ang), math.sin(ang)
    hl, hw = L / 2, max(0.5, W / 2)
    lit_plus = (-sa) * -0.7 + ca * -0.7 > 0          # +v side normal (-sa, ca) faces the top-left light?
    R = int(hl + 2)
    for dy in range(-R, R + 1):
        for dx in range(-R, R + 1):
            u = dx * ca + dy * sa
            v = -dx * sa + dy * ca
            if abs(u) > hl:
                continue
            f = abs(u) / hl
            w = hw * (1 - f ** 2) ** tip
            if abs(v) > w + 0.35:
                continue
            if abs(v) > w - 0.75 or f > 0.86:
                c = cols[0]
            elif vein and abs(v) < 0.5 and W > 2.5:
                c = cols[3]
            elif (v > 0) == lit_plus:
                c = cols[2]
            else:
                c = cols[1]
            cv.px(x + dx, y + dy, c)


def _lcols(pal):
    return [pal[0], pal[2], pal[3], pal[1]]


def petal_shape(cv, x, y, ang, s, flat):
    """Pink petal: rounded teardrop with a notch-free tip, lit edge, foreshortened by flat (0..1)."""
    leaf_shape(cv, x, y, ang, s, max(1.2, s * 0.8 * flat), [PETAL[1], PETAL[2], PETAL[3], PETAL[2]], vein=False,
               tip=0.45)


def razor_leaf(S):
    """Loop: Razor Leaf - five distinct leaf shapes (pointed oval, centre vein, dark edge, lit side) flying in a
    staggered loose arc, each spinning flat-to-edge as it tumbles; sharp, no glow, no core."""
    pal = S.pal
    hx, hy = S.anchor
    rr = random.Random(7)
    leaves = [(hx - 4 - k * 15 + rr.uniform(-3, 3), hy + math.sin(k * 1.7) * 7, rr.uniform(0, 1), rr.choice((1, 2)))
              for k in range(5)]

    def tick(sim, i, t, rng):
        pass

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        for k, (x, y, u, spins) in enumerate(leaves):
            a = (ph * spins + u) * TAU
            yy = y + math.sin((ph + u) * TAU) * 1.5
            W = 4.6 * abs(math.cos(a)) + 0.8
            leaf_shape(cv, x, yy, -0.25 + math.sin(a) * 0.5, 12, W * 1.1, _lcols(pal))
            if k == 0:
                for j in range(3):
                    cv.px(x - 7 - j * 3, yy + (j % 2), pal[3] if j == 0 else pal[2])

    run(S, tick, draw, loop=True, warm=0)


def _flutter(rr, n, cx, cy, spd, up):
    out = []
    for k in range(n):
        a = rr.uniform(0, TAU)
        sp = rr.uniform(*spd)
        out.append(dict(vx=math.cos(a) * sp, vy=math.sin(a) * sp * 0.8 - up * rr.uniform(0.5, 1), ph=rr.uniform(0, TAU),
                        w=rr.uniform(5, 9), sway=rr.uniform(3, 7), s=rr.uniform(5, 8), fall=rr.uniform(14, 24),
                        spin=rr.uniform(0.8, 1.6) * rr.choice((-1, 1)), delay=rr.uniform(0, 0.15)))
    return out


def _flutter_pos(p, t, cx, cy, gy, drag=4.0):
    t = max(0.0, t - p["delay"])
    k = (1 - math.exp(-drag * t)) / drag
    x = cx + p["vx"] * k + p["sway"] * math.sin(p["w"] * t + p["ph"]) * min(1, t * 3)
    y = cy + p["vy"] * k + p["fall"] * t
    return x, min(y, gy - 1), t


def petal_dance(S):
    """Petal Dance hit: pink and white petals burst out of the target in a swirl, then flutter down, each swaying
    side to side and turning flat-to-edge (the falling-petal read); a few green leaves mixed in. No flash: grass is
    a material."""
    pal = S.pal
    cx, cy = S.anchor
    gy = S.ground
    rr = random.Random(11)
    petals = _flutter(rr, 26, cx, cy, (110, 200), 40)
    leaves = _flutter(rr, 5, cx, cy, (100, 170), 40)

    def tick(sim, i, t, rng):
        pass

    def draw(cv, L, sim, i, t, rng):
        for grp, isleaf in ((leaves, True), (petals, False)):
            for k, p in enumerate(grp):
                x, y, tt = _flutter_pos(p, t, cx, cy, gy, drag=3.0)
                if tt <= 0:
                    continue
                if t > 1.0 and (k * 7 + i) % 40 < (t - 1.0) * 40:
                    continue
                a = p["spin"] * tt * 4 + p["ph"]
                flat = abs(math.cos(p["w"] * tt * 0.7 + p["ph"]))
                if isleaf:
                    leaf_shape(cv, x, y, a, 8, 3.6 * flat + 0.8, _lcols(pal))
                else:
                    petal_shape(cv, x, y, a, p["s"], flat)
        if i < 3:
            for k in range(10):
                a = k / 10 * TAU + i * 0.3
                r = 5 + i * 5
                petal_shape(cv, cx + math.cos(a) * r, cy + math.sin(a) * r * 0.8, a + 1.2, 6, 0.8)

    run(S, tick, draw, ground=gy)


def sleep_powder(S):
    """Sleep Powder / Stun Spore: a soft cloud of many tiny powder grains sprinkled from above, drifting down and
    outward over the target, pale green with brighter specks twinkling; slow (~1.3 s). No glow (powder)."""
    pal = S.pal
    cx, cy = S.anchor
    gy = S.ground
    rr = random.Random(5)
    grains = [dict(x=cx + rr.gauss(0, 9), y=cy - 34 + rr.gauss(0, 5), vx=rr.gauss(0, 7), fall=rr.uniform(12, 26),
                   ph=rr.uniform(0, TAU), d=rr.uniform(0, 0.45), tw=rr.random() < 0.18) for _ in range(150)]
    POW = [(120, 150, 90), (170, 200, 120), (214, 236, 160), (250, 255, 220)]

    def tick(sim, i, t, rng):
        pass

    def draw(cv, L, sim, i, t, rng):
        for k, g in enumerate(grains):
            tt = t - g["d"]
            if tt <= 0:
                continue
            x = g["x"] + g["vx"] * tt + 2 * math.sin(tt * 3 + g["ph"])
            y = g["y"] + g["fall"] * tt + 8 * (1 - math.exp(-tt * 2))
            if y >= gy - 1:
                continue
            life = clamp(1 - (t - 0.9) / 0.6)
            if (k % 10) / 10 > life:
                continue
            if g["tw"] and (i + k) % 4 == 0:
                cv.px(x, y, POW[3])
                cv.px(x + 1, y, POW[2]); cv.px(x - 1, y, POW[2]); cv.px(x, y + 1, POW[2]); cv.px(x, y - 1, POW[2])
            else:
                cv.px(x, y, POW[1] if (k + i // 3) % 3 else POW[2])
        # thin haze: dither of the darkest powder tone inside the cloud core
        if t < 1.3:
            yc = cy - 30 + 22 * clamp(t / 0.9)
            for y in range(int(yc - 8), int(yc + 9)):
                for x in range(int(cx - 14), int(cx + 15)):
                    if noise2(x * 0.7, y * 0.7 + i * 0.2, 4) > 0.35 and ((x - cx) / 14) ** 2 + ((y - yc) / 8) ** 2 < 1 - clamp((t - 0.8) / 0.5):
                        cv.px(x, y, POW[0])

    run(S, tick, draw, ground=gy)


def leaf_tornado(S):
    """Loop: Petal Dance / leaf storm around the target - 20 real leaf shapes riding a rising helix around the
    target, back ones darker and smaller, front ones bigger, each tumbling; a few petals mixed in; a faint ground
    swirl of grass bits. Leaves, not wind lines."""
    pal = S.pal
    cx, gy = S.anchor[0], S.ground
    rr = random.Random(3)
    items = [(rr.uniform(0, 1), rr.uniform(0, 1), rr.uniform(0, TAU), rr.random() < 0.2) for _ in range(30)]

    def tick(sim, i, t, rng):
        pass

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        lst = []
        for k, (h0, a0, sp, pet) in enumerate(items):
            h = (h0 + ph) % 1
            a = a0 * TAU + ph * TAU * 2 + h * 3
            r = 12 + h * 24
            x = cx + math.cos(a) * r
            y = gy - 4 - h * 92 + math.sin(a) * r * 0.25
            lst.append((math.sin(a), x, y, a, k, pet, h))
        for (z, x, y, a, k, pet, h) in sorted(lst):
            front = z > 0
            spin = a * 1.3 + items[k][2]
            flat = abs(math.cos(spin))
            if pet:
                petal_shape(cv, x, y, spin, 7 if front else 5, flat)
            else:
                cols = _lcols(pal) if front else [pal[0], pal[1], pal[2], pal[0]]
                leaf_shape(cv, x, y, a + math.pi / 2 + 0.4 * math.sin(spin), 14 if front else 10,
                           (6.0 if front else 4.2) * flat + 1.0, cols)
        for k in range(24):
            a = k / 24 * TAU + ph * TAU * 2
            if k % 3:
                cv.px(cx + math.cos(a) * 16, gy - 1 + math.sin(a) * 3, pal[1])

    run(S, tick, draw, loop=True, ground=gy, warm=0)


# ------------------------------------------------------------------ ice, designed per move
def crystal(cv, x, y, ang, L, W, pal, lit=True):
    """Faceted ice crystal (elongated kite) along ang: two facets split by a ridge, the facet facing the top-left
    light is pale, the other mid-blue, white ridge highlight, dark-blue outline. W may be foreshortened."""
    x, y = int(math.floor(x + 0.5)), int(math.floor(y + 0.5))
    ca, sa = math.cos(ang), math.sin(ang)
    hl, hw = L / 2, max(0.6, W / 2)
    lit_plus = (-sa) * -0.7 + ca * -0.7 > 0
    R = int(hl + 2)
    for dy in range(-R, R + 1):
        for dx in range(-R, R + 1):
            u = dx * ca + dy * sa
            v = -dx * sa + dy * ca
            if u > hl or u < -hl * 0.55:
                continue
            w = hw * ((hl - u) / (hl * 0.75) if u > hl * 0.25 else (u + hl * 0.55) / (hl * 0.8))
            w = min(w, hw)
            if abs(v) > w + 0.3:
                continue
            if abs(v) > w - 0.8:
                c = pal[1] if (v > 0) != lit_plus else pal[2]
            elif abs(v) < 0.5:
                c = pal[5]
            elif (v > 0) == lit_plus:
                c = pal[4] if lit else pal[3]
            else:
                c = pal[3] if lit else pal[2]
            cv.px(x + dx, y + dy, c)


def snowflake(cv, x, y, s, c, c2=None):
    if s <= 1:
        cv.px(x, y, c)
        return
    for k in range(-s, s + 1):
        cv.px(x + k, y, c if abs(k) < s else (c2 or c))
        cv.px(x, y + k, c if abs(k) < s else (c2 or c))
    if s >= 2:
        for k in (-1, 1):
            cv.px(x + k, y + k, c2 or c); cv.px(x + k, y - k, c2 or c)


def ice_shards(S):
    """Loop: Icy Wind / ice shards - four faceted crystals flying in a loose wedge, each spinning (the facets swap
    light and dark as it turns), a few snow specks peel off behind. No glow, no core."""
    pal = S.pal
    hx, hy = S.anchor
    rr = random.Random(9)
    shards = [(hx - 4, hy, 0.0, 19, 8), (hx - 24, hy - 10, 0.3, 15, 6.5), (hx - 26, hy + 10, 0.6, 15, 6.5),
              (hx - 44, hy + 1, 0.15, 12, 5)]
    specks = [(rr.uniform(-60, 0), rr.uniform(-10, 10), rr.uniform(0, 1)) for _ in range(14)]

    def tick(sim, i, t, rng):
        pass

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        for (sx, sy, u) in specks:
            x = hx + ((sx - ph * 60 * 2) % -60) - 6
            if x < hx - 58:
                continue
            cv.px(x, hy + sy + math.sin((ph + u) * TAU) * 2, pal[4] if u > 0.6 else pal[3])
        for k, (x, y, u, Ls, Ws) in enumerate(shards):
            a = (ph * 2 + u) * TAU
            crystal(cv, x, y + math.sin((ph + u) * TAU), math.sin(a) * 0.35, Ls, Ws * (0.35 + 0.65 * abs(math.cos(a))),
                    pal, lit=math.cos(a) > 0)
        if (i % 8) < 2:
            L.add(hx - 2, hy - 2, 4, pal[5], 0.5, glint=True)

    run(S, tick, draw, loop=True, warm=0)


def ice_beam(S):
    """Ice Beam: a crisp straight beam (hard parallel edges, pale cyan body, white core), 4-point star glints
    running along it, and ice crystals growing on its path as it passes - they stay after the beam cuts off, then
    crack and fall; at the target a burst of faceted shards and snowflakes."""
    pal = S.pal
    ox, oy = S.anchor
    tx = S.w - 6
    t_on, t_off = 0.2, 0.95
    rr = random.Random(13)
    buds = [(ox + 16 + k * ((tx - ox - 24) / 7) + rr.uniform(-4, 4), rr.choice((-1, 1)), rr.uniform(11, 17),
             rr.uniform(-0.5, 0.5)) for k in range(8)]
    pieces = [dict(vx=rr.uniform(-40, 70), vy=rr.uniform(-90, -20), a=rr.uniform(0, TAU), s=rr.uniform(7, 12),
                   w=rr.uniform(-8, 8)) for _ in range(10)]

    def head(t):
        return ox + (tx - ox) * clamp((t - t_on) / 0.15)

    def draw(cv, L, sim, i, t, rng):
        h = head(t)
        on = t_on <= t < t_off
        if t < t_on:
            g = clamp(t / t_on)
            snowflake(cv, ox, oy, int(1 + g * 3), pal[5], pal[3])
            L.add(ox, oy, 8 + g * 8, pal[3], 0.6 * g)
        if on:
            thin = 1 - clamp((t - (t_off - 0.15)) / 0.15)
            hw = 3.5 * thin + 0.5
            for x in range(int(ox), int(h) + 1):
                for y in range(int(oy - hw), int(oy + hw) + 1):
                    d = abs(y - oy) / max(hw, 0.5)
                    cv.px(x, y, pal[1] if d > 0.85 else pal[3] if d > 0.3 else pal[5])
                if x % 10 == 0:
                    L.add(x, oy, 7, pal[2], 0.22 * thin)
            for k in range(4):
                gx = ox + ((t * 300 + k * 40) % max(1, h - ox))
                snowflake(cv, gx, oy + (k % 2 * 2 - 1) * (hw + 2), 2, pal[5], pal[3])
            if h >= tx - 1:
                L.add(tx, oy, 20, pal[5], 0.7 * thin)
        # crystals budding on the path once the head has passed, staying after the beam stops, then falling
        for k, (bx, side, bl, ba) in enumerate(buds):
            t0 = t_on + 0.15 * (bx - ox) / (tx - ox)
            if t < t0:
                continue
            g = clamp((t - t0) / 0.2)
            fall = max(0.0, t - (t_off + 0.03 + k * 0.025))
            yy = oy + side * 2 + 260 * fall * fall
            if yy > S.h:
                continue
            crystal(cv, bx, yy + side * bl * g * 0.45, -side * math.pi / 2 + ba + fall * 4, bl * g, 6.5 * g, pal)
            if g < 1 or fall == 0 and (i + k) % 9 == 0:
                L.add(bx, yy, 4, pal[5], 0.5, glint=True)
        # target burst of faceted pieces once the beam lands
        tl = t - (t_on + 0.15)
        if tl > 0:
            for k, p in enumerate(pieces):
                x = tx - 4 + p["vx"] * tl * 0.6
                y = oy + p["vy"] * tl * 0.6 + 140 * tl * tl
                if y > S.h:
                    continue
                if tl < 0.9:
                    crystal(cv, x, y, p["a"] + p["w"] * tl, p["s"], p["s"] * 0.5, pal)
        if 0 < tl < 0.8:
            for k in range(3):
                snowflake(cv, tx - 6 + k * 3 - (i % 3), oy - 8 + k * 7, 2, pal[5], pal[3])

    run(S, lambda *a: None, draw, ground=S.ground)


def ice_break(S):
    """Ice shatter: the target is sealed in a faceted ice block (pale facets, white edges) for a beat, cracks run
    over it, then it bursts into faceted crystal chunks that fly, spin, bounce on the floor and glint; snow bits
    drift. No glow, only glints on the breaking edges."""
    pal = S.pal
    cx, cy = S.anchor
    gy = S.ground
    rr = random.Random(21)
    chunks = [dict(vx=rr.uniform(-110, 110), vy=rr.uniform(-150, -40), a=rr.uniform(0, TAU), w=rr.uniform(-9, 9),
                   s=rr.uniform(8, 15)) for _ in range(14)]
    T_CRACK, T_BREAK = 0.12, 0.3
    top, bot = cy - 18, gy

    def block(cv, i, crack):
        xs = (cx - 15, cx + 15)
        poly = [(cx - 12, top), (cx + 9, top - 3), (cx + 16, top + 8), (cx + 14, bot), (cx - 15, bot), (cx - 17, top + 9)]
        for y in range(int(top - 3), int(bot) + 1):
            for x in range(int(xs[0]) - 3, int(xs[1]) + 3):
                if not _inpoly(x + 0.5, y + 0.5, poly):
                    continue
                f = (x - cx) + (y - top) * 0.6
                c = pal[4] if f < -6 else pal[3] if f < 10 else pal[2]
                if (x + y) % 2 == 0 and c == pal[2]:
                    continue
                cv.px(x, y, c)
        for a, b in zip(poly, poly[1:] + poly[:1]):
            cv.line(a[0], a[1], b[0], b[1], pal[5] if a[1] < cy else pal[1])
        cv.line(cx - 12, top, cx - 4, bot, pal[5])
        if crack:
            r2 = random.Random(4)
            for k in range(4):
                x0, y0 = cx + r2.uniform(-4, 4), cy + r2.uniform(-4, 4)
                for _ in range(3):
                    x1, y1 = x0 + r2.uniform(-7, 7), y0 + r2.uniform(-7, 7)
                    cv.line(x0, y0, x1, y1, pal[0])
                    x0, y0 = x1, y1

    def draw(cv, L, sim, i, t, rng):
        if t < T_BREAK:
            block(cv, i, t > T_CRACK)
            if t > T_CRACK and i % 2 == 0:
                L.add(cx - 6, cy - 6, 5, pal[5], 0.6, glint=True)
            return
        tl = t - T_BREAK
        for k, p in enumerate(chunks):
            x = cx + p["vx"] * tl
            y = cy + p["vy"] * tl + 260 * tl * tl
            if y > gy - 2:
                tb = (-p["vy"] + math.sqrt(p["vy"] ** 2 + 4 * 260 * (gy - 2 - cy))) / (2 * 260)
                y = gy - 2 - max(0.0, 40 * (tl - tb) - 200 * (tl - tb) ** 2)
                x = cx + p["vx"] * (tb + (tl - tb) * 0.3)
            if tl > 0.7 and (k * 5) % 16 < (tl - 0.7) * 30:
                continue
            spin = p["a"] + p["w"] * min(tl, 0.6)
            crystal(cv, x, y, spin, p["s"], p["s"] * 0.55, pal, lit=math.cos(spin * 2) > 0)
            if (i + k) % 11 == 0:
                L.add(x, y, 3, pal[5], 0.5, glint=True)
        for k in range(10):
            x = cx + (k - 5) * 7 + math.sin(t * 3 + k) * 3
            y = cy - 20 + tl * 30 + k * 3
            if y < gy - 1 and tl < 1.0:
                cv.px(x, y, pal[5] if k % 3 == 0 else pal[4])

    run(S, lambda *a: None, draw, ground=gy)


def _inpoly(x, y, poly):
    inside = False
    j = len(poly) - 1
    for k in range(len(poly)):
        xi, yi = poly[k]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-9) + xi:
            inside = not inside
        j = k
    return inside


def blizzard(S):
    """Loop: Blizzard - driving snow on a hard diagonal wind: three depth layers (far = 1 px slow, near = cross
    flakes fast), long wind streaks sweeping across, gust bands where the snow thickens, frost building on the
    floor line and rime on the left of the ground. Fills the frame."""
    pal = S.pal
    W, Hh, gy = S.w, S.h, S.ground
    rr = random.Random(17)
    n = S.n
    layers = []
    for depth, count, spd, size in ((0, 130, 1, 0), (1, 60, 2, 1), (2, 18, 3, 2)):
        for _ in range(count):
            layers.append((depth, rr.uniform(0, W + 60), rr.uniform(0, Hh), spd, size, rr.uniform(0, TAU)))
    streaks = [(rr.uniform(0, 1), rr.uniform(4, gy - 6), rr.uniform(14, 30)) for _ in range(8)]

    def draw(cv, L, sim, i, t, rng):
        ph = i / n
        # frost on the floor: dithered white line with icicle ticks
        for x in range(0, W):
            if noise2(x * 0.3, 1, 3) > -0.3:
                cv.px(x, gy - 1, pal[4] if x % 3 else pal[5])
            if noise2(x * 0.5, 2, 5) > 0.45:
                cv.px(x, gy - 2, pal[3])
        for (u, y, ln) in streaks:
            x = ((u + ph * 2) % 1) * (W + 60) - 30
            for k in range(int(ln)):
                if k % 4 != 3:
                    cv.px(x - k, y + k * 0.25, pal[2] if k > ln * 0.5 else pal[3])
        for (depth, x0, y0, spd, size, p) in layers:
            # each layer moves an integer number of frame-widths per loop so the loop is seamless
            dx = ph * (W + 60) * spd
            dy = ph * Hh * spd
            x = (x0 + dx) % (W + 60) - 30
            y = (y0 + dy * 0.6 + 3 * math.sin(ph * TAU * 2 + p)) % Hh
            if y > gy - 2:
                continue
            gust = noise2(x * 0.02 - ph * 4, y * 0.02, 8)
            if depth == 0 and gust < -0.2:
                continue
            c = (pal[2], pal[4], pal[5])[depth]
            if size == 0:
                cv.px(x, y, c)
            elif size == 1:
                cv.px(x, y, c); cv.px(x - 1, y - 0.5, pal[3])
            else:
                snowflake(cv, x, y, 2, pal[5], pal[3])
                cv.px(x - 3, y - 1.5, pal[3]); cv.px(x - 4, y - 2, pal[2])

    run(S, lambda *a: None, draw, loop=True, ground=gy, warm=0)


# ------------------------------------------------------------------ fighting, designed per move
def shaded_shape(cv, x, y, inside, R, cols):
    """Fill a shape given by inside(dx, dy) -> bool around (x, y): 1 px outline cols[0], body lit from the
    top-left (cols[1] shade, cols[2] body, cols[3] light)."""
    x, y = int(math.floor(x + 0.5)), int(math.floor(y + 0.5))
    pts = set()
    for dy in range(-R, R + 1):
        for dx in range(-R, R + 1):
            if inside(dx, dy):
                pts.add((dx, dy))
    for (dx, dy) in pts:
        if any((dx + a, dy + b) not in pts for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            c = cols[0]
        else:
            lit = (-dx - dy) / (R * 1.2)
            c = cols[3] if lit > 0.45 else cols[2] if lit > -0.35 else cols[1]
        cv.px(x + dx, y + dy, c)


def glove(cv, x, y, s, pal, cuff=(232, 226, 214)):
    """A boxing glove facing right (our own drawing): round fist, thumb over the top, white cuff; s = scale."""
    def inside(dx, dy):
        u, v = dx / s, dy / s
        fist = (u / 7.5) ** 2 + (v / 6.2) ** 2 <= 1
        thumb = ((u + 0.5) / 4.5) ** 2 + ((v + 4.6) / 2.4) ** 2 <= 1
        return fist or thumb
    shaded_shape(cv, x, y, inside, int(9 * s), [pal[0], pal[1], pal[2], pal[4]])
    for k in range(int(-2 * s), int(2 * s) + 1):
        cv.px(x - 5 * s + k * 0.3, y - 2.6 * s + k, pal[0])          # thumb crease
    for dy in range(int(-4.5 * s), int(4.5 * s) + 1):
        for dx in range(int(-10 * s), int(-6.8 * s)):
            cv.px(x + dx, y + dy, pal[0] if dx == int(-10 * s) or abs(dy) >= int(4.5 * s) else cuff)


def pow_star(cv, x, y, r, pal, rot=0.0, n=8, white=(255, 255, 255)):
    """Comic contact star: n uneven points, white fill, warm inner ring, dark outline - drawn, not light."""
    x, y = int(math.floor(x + 0.5)), int(math.floor(y + 0.5))
    rr = random.Random(int(r * 10) + n)
    pts = []
    for k in range(n * 2):
        a = rot + k * math.pi / n
        rad = r * (rr.uniform(0.85, 1.1) if k % 2 == 0 else 0.42)
        pts.append((x + math.cos(a) * rad, y + math.sin(a) * rad))
    R = int(r + 2)
    inn = set()
    for dy in range(-R, R + 1):
        for dx in range(-R, R + 1):
            if _inpoly(x + dx + 0.5013, y + dy + 0.4987, pts):
                inn.add((dx, dy))
    for (dx, dy) in inn:
        edge = any((dx + a, dy + b) not in inn for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        d = math.hypot(dx, dy) / r
        cv.px(x + dx, y + dy, pal[1] if edge else pal[4] if d > 0.5 else white)


def mega_punch(S):
    """Mega Punch / power hit: a big glove drives in from the left with speed lines (wind-up 4 frames), lands with
    a white comic contact star, hit-lines and a 2-frame squash, then pulls back; dust kicks up at the feet. Reads
    as 'punched', no glow (fighting is physical)."""
    pal = S.pal
    cx, cy = S.anchor
    gy = S.ground
    HIT = 5

    def draw(cv, L, sim, i, t, rng):
        if i <= HIT:
            u = out_cubic(i / HIT)
            gx = 6 + (cx - 18 - 6) * u
            for k in range(6):
                yy = cy - 9 + k * 3.6
                ln = 10 + (k * 7) % 13
                for d in range(int(ln)):
                    if d % 5 != 4:
                        cv.px(gx - 18 - d - (k * 5) % 9, yy, pal[3] if d < ln * 0.4 else pal[2])
            glove(cv, gx, cy, 1.7, pal)
        else:
            d = i - HIT
            back = clamp((d - 3) / 6)
            gx = cx - 18 - 22 * out_cubic(back)
            if back < 1:
                glove(cv, gx, cy + 1, 1.7 * (1.08 if d < 2 else 1.0), pal)
            if d < 9:
                r = (17 if d < 2 else 14) * (1 - clamp((d - 3) / 6) * 0.6)
                pow_star(cv, cx + 2, cy - 1, r, pal, rot=0.2 + d * 0.05, n=8)
                if d < 2:
                    L.add(cx, cy, 6, pal[5], 0.7, glint=True)
            if d < 7:
                for k in range(5):
                    a = -0.9 + k * 0.45
                    r0 = 18 + d * 3
                    cv.line(cx + 2 + math.cos(a) * r0, cy + math.sin(a) * r0, cx + 2 + math.cos(a) * (r0 + 6),
                            cy + math.sin(a) * (r0 + 6), pal[4] if d < 3 else pal[2])
            if d < 22:
                for k in range(6):
                    sx = cx + (k - 2.5) * (6 + d * 1.6)
                    rag_blob(cv, sx, gy - 3 - d * 0.3, 3.5 * (1 - d / 22) + 0.5, (122, 112, 104), 40 + k, t=t,
                             rough=0.4, edge=(84, 76, 72))

    run(S, lambda *a: None, draw, ground=gy)


def karate_chop(S):
    """Karate Chop: a fast downward swoosh arc sweeps across the target and leaves a sharp curved white slash line
    for 2 frames, then a small contact star and short hit lines; quick and sharp."""
    pal = S.pal
    cx, cy = S.anchor
    HIT = 4

    def draw(cv, L, sim, i, t, rng):
        # the chop itself is a fast sweep: a widening swoosh arc, then the sharp slash line across the body
        if i < HIT:
            u = (i + 1) / HIT
            crescent(cv, cx - 24, cy + 30, 46, -1.55, -1.55 + 1.4 * u, 2.0 + 2.5 * u, [pal[2], pal[3], pal[4]],
                     squash=1.0)
        if HIT <= i <= HIT + 1:
            crescent(cv, cx - 24, cy + 30, 46, -1.6, -0.1, 4.5, [pal[3], pal[5], (255, 255, 255)], squash=1.0)
        if HIT <= i < HIT + 10:
            d = i - HIT
            pow_star(cv, cx, cy, (11 if d < 2 else 9) * (1 - d / 14), pal, rot=0.4, n=6)
            if d < 2:
                L.add(cx, cy, 6, pal[5], 0.7, glint=True)
            if d < 6:
                for k in (-1, 1):
                    cv.line(cx + k * (12 + d), cy - 10 - d, cx + k * (16 + d * 2), cy - 14 - d * 2, pal[4])

    run(S, lambda *a: None, draw, ground=S.ground)


def force_wave(S):
    """Loop: a fighting force wave (Submission / chop shockwave) - a punch of compressed air: a cone of three
    edge-on pressure rings (tall thin ellipses) that grow as they travel, parallel speed lines between them and
    dust puffs shed below. Unlike the bug buzz (wobbly sound rings) these are rigid rings with a hard front."""
    pal = S.pal
    ox, oy = S.anchor
    n = S.n

    def draw(cv, L, sim, i, t, rng):
        ph = i / n
        for k in range(3):
            u = (ph + k / 3) % 1
            x = ox + 8 + u * (S.w - 24)
            ry = 6 + u * 18
            rx = 2 + u * 2.5
            for j in range(int(ry * 8)):
                a = j / (ry * 8) * TAU
                px_, py_ = x + math.cos(a) * rx, oy + math.sin(a) * ry
                front = math.cos(a) > 0
                cv.px(px_, py_, (pal[5] if u < 0.5 else pal[4]) if front else pal[2])
                if front and abs(math.sin(a)) < 0.7:
                    cv.px(px_ + 1, py_, pal[3])
        for k in range(5):
            yy = oy + (k - 2) * 5
            x0 = ox + 4 + ((ph * 2 + k * 0.37) % 1) * (S.w - 30)
            for d in range(10):
                if d % 4 != 3:
                    cv.px(x0 - d, yy, pal[3] if d < 4 else pal[2])
        for k in range(4):
            u = (ph + k / 4) % 1
            rag_blob(cv, ox + 10 + u * (S.w - 30), oy + 20 + u * 4, 1.5 + u * 2.5, (118, 108, 100), 60 + k, t=u,
                     rough=0.4)

    run(S, lambda *a: None, draw, loop=True, warm=0)


def focus_energy(S):
    """Loop: Focus Energy / getting pumped - an upward flame-shaped energy shell hugging the body (all tongues
    point up, like a battle aura), short inward lines rushing to the body in pulses, and a ring pulsing at the
    feet. Emissive (energy)."""
    pal = S.pal
    cx, fy = S.w / 2, S.ground
    cy = fy - 13

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        pulse = 0.5 + 0.5 * math.sin(ph * TAU * 2)
        for k in range(18):
            a = k / 18 * TAU
            x = cx + math.cos(a) * 14
            y = cy + math.sin(a) * 15
            if math.sin(a) > 0.75:
                continue
            ln = (8 + 6 * (0.5 - math.sin(a) * 0.5)) * (0.7 + 0.5 * noise2(ph * 8, k, 3)) * (0.8 + 0.3 * pulse)
            tongue_dir(cv, x, y, -math.pi / 2 + math.cos(a) * 0.25, 2.8, ln, [pal[1], pal[3], pal[4]], 170 + k, t)
        if i % 10 < 4:
            for k in range(8):
                a = k / 8 * TAU + 0.2
                r0 = 30 - (i % 10) * 4
                cv.line(cx + math.cos(a) * r0, cy + math.sin(a) * r0, cx + math.cos(a) * (r0 - 5),
                        cy + math.sin(a) * (r0 - 5), pal[5])
        rx = 12 + pulse * 6
        for j in range(int(rx * 5)):
            a = j / (rx * 5) * TAU
            cv.px(cx + math.cos(a) * rx, fy - 1 + math.sin(a) * rx * 0.25, pal[4] if math.sin(a) > 0 else pal[2])
        L.add(cx, cy, 22, pal[3], 0.35 + 0.2 * pulse)

    run(S, lambda *a: None, draw, loop=True, ground=fy, warm=0)


# ------------------------------------------------------------------ poison (material), designed per move
def goo(cv, x, y, rx, ry, pal, seed, t, spec=True, rough=0.12):
    """Glossy goo blob: wobbly noisy edge, dark outline, body shaded from the top-left, white specular dot."""
    def inside(dx, dy):
        a = math.atan2(dy, dx)
        k = 1 + rough * noise2(math.cos(a) * 1.5 + seed, math.sin(a) * 1.5 + t * 3, seed)
        return (dx / (rx * k)) ** 2 + (dy / (ry * k)) ** 2 <= 1
    R = int(max(rx, ry) * 1.2 + 1)
    shaded_shape(cv, x, y, inside, R, [pal[0], pal[1], pal[2], pal[3]])
    if spec and rx >= 2.5:
        sx, sy = x - rx * 0.4, y - ry * 0.45
        cv.px(sx, sy, pal[5])
        if rx >= 4:
            cv.px(sx + 1, sy, pal[4]); cv.px(sx, sy + 1, pal[4])


def sludge_glob(S):
    """Loop: Sludge - three glossy purple globs thrown in a heavy arc, each wobbling (squash and stretch out of
    phase), a sticky strand between the lead glob and the next, drips beading off the bottom and falling.
    Viscous, not a spark; no glow."""
    pal = S.pal
    hx, hy = S.anchor
    globs = [(hx - 8, hy, 8.5, 0.0), (hx - 38, hy + 6, 4.6, 0.33), (hx - 54, hy + 10, 3.2, 0.66)]
    rr = random.Random(23)
    drips = [(rr.choice((0, 1)), rr.uniform(0, 1), rr.uniform(-3, 3)) for _ in range(5)]

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        # viscous tail: the lead glob drags a tapering, sagging tail of goo behind it
        x0, y0, r0, _ = globs[0]
        for k in range(14, 0, -1):
            f = k / 14
            x = x0 - f * 20
            y = y0 + f * f * 4 + math.sin((ph * 2 - f) * TAU) * f * 1.5
            r = r0 * (1 - f) * 0.9 + 0.8
            cv.disc(x, y + 0.5, r + 0.6, pal[0])
        for k in range(14, 0, -1):
            f = k / 14
            x = x0 - f * 20
            y = y0 + f * f * 4 + math.sin((ph * 2 - f) * TAU) * f * 1.5
            r = r0 * (1 - f) * 0.9 + 0.8
            cv.disc(x, y, r, pal[2])
            cv.px(x, y - r + 1, pal[3])
        for (g, u, ox) in drips:
            gx, gy0, gr, _ = globs[g]
            f = (ph + u) % 1
            y = gy0 + gr * 0.8 + f * 22 + 30 * f * f
            x = gx + ox - f * 10
            ln = 1 + int(3 * (1 - f))
            for k in range(ln):
                cv.px(x, y - k, pal[2] if k else pal[3])
            cv.px(x, y + 1, pal[0])
        for k, (x, y, r, u) in enumerate(globs):
            w = math.sin((ph * 2 + u) * TAU)
            goo(cv, x, y + math.sin((ph + u) * TAU) * 1.2, r * (1.1 + 0.12 * w), r * (0.9 - 0.12 * w), pal, 30 + k, ph)

    run(S, lambda *a: None, draw, loop=True, warm=0)


def toxic_splat(S):
    """Acid / Sludge hit: a goo blob slaps the target and flattens into a splat over it, droplets fly out on heavy
    arcs and land as small puddles, strings drip from the splat, a puddle spreads at the feet and bubbles rise in
    it and pop (broken ring). Purple liquid, no flash."""
    pal = S.pal
    cx, cy = S.anchor
    gy = S.ground
    rr = random.Random(31)
    drops = [dict(vx=rr.uniform(-120, 120), vy=rr.uniform(-150, -30), r=rr.uniform(1.6, 3.2)) for _ in range(14)]
    bubbles = [(rr.uniform(-16, 16), rr.uniform(0.3, 1.1), rr.uniform(1.5, 3.2)) for _ in range(7)]
    G = 380

    def draw(cv, L, sim, i, t, rng):
        # puddle at the feet grows from 0.2 s
        pu = clamp((t - 0.15) / 0.5)
        fade = clamp((t - 1.0) / 0.35)
        if pu > 0:
            rx = 6 + 18 * pu * (1 - fade * 0.4)
            for x in range(int(cx - rx), int(cx + rx) + 1):
                d = abs(x - cx) / rx
                h = 1 + (2.5 * (1 - d * d)) * (1 - fade)
                for y in range(int(gy - h), gy):
                    cv.px(x, y, pal[1] if y < gy - h + 1 else pal[2] if d < 0.7 else pal[1])
                if d < 0.6 and (x + i // 2) % 7 == 0:
                    cv.px(x, gy - h - 0.5, pal[3])
        # splat on the target: blob arrives (frames 0-2), flattens, then slides and drips
        if t < 1.1:
            sq = clamp(t / 0.08)
            rx = 8 + 8 * sq
            ry = 8 - 3 * sq
            slide = max(0.0, t - 0.25) * 8
            goo(cv, cx, cy + 3 + slide, rx * (1 - fade), ry * (1 - fade) + 0.5, pal, 41, t * 0.5, rough=0.4)
            if t > 0.2:
                for k in range(4):
                    sx = cx - 9 + k * 6
                    ln = clamp((t - 0.2 - k * 0.07) / 0.5) * (8 + (k * 5) % 7)
                    for d in range(int(ln)):
                        cv.px(sx, cy + ry + slide + d, pal[2] if d < ln - 1 else pal[3])
                    if ln > 2:
                        cv.px(sx, cy + ry + slide + ln, pal[0])
        # flying droplets on heavy arcs; once they land they stay as tiny puddles until fade
        for k, p in enumerate(drops):
            tt = t - 0.04
            if tt <= 0:
                continue
            x = cx + p["vx"] * tt
            y = cy + p["vy"] * tt + 0.5 * G * tt * tt
            if y >= gy - 1:
                tl = (-p["vy"] + math.sqrt(p["vy"] ** 2 + 2 * G * (gy - 1 - cy))) / G
                x = cx + p["vx"] * tl
                if fade < 1:
                    cv.line(x - p["r"], gy - 1, x + p["r"], gy - 1, pal[2])
                continue
            vyn = p["vy"] + G * tt
            goo(cv, x, y, p["r"], p["r"] * (1 + min(0.6, abs(vyn) / 400)), pal, 50 + k, t, spec=p["r"] > 2.5)
        # bubbles in the puddle rise and pop
        for (bx, t0, br) in bubbles:
            u = (t - t0) / 0.35
            if 0 <= u < 1 and pu > 0.3:
                x, y = cx + bx, gy - 2 - u * 3
                if u < 0.8:
                    cv.ring(x, y, br, 1, pal[3])
                    cv.px(x - br * 0.4, y - br * 0.4, pal[5])
                else:
                    for a in range(6):
                        aa = a / 6 * TAU
                        cv.px(x + math.cos(aa) * (br + 1.5), y + math.sin(aa) * (br + 1.5), pal[4])

    run(S, lambda *a: None, draw, ground=gy)


def poison_gas(S):
    """Loop: Poison Gas / Smog - a billowing cloud of round lobes over the target that roll and swell in turn,
    dithered (see-through) purple with a sickly green tinge, lit rims on top, darker core below, wisps curling
    off the top. A cloud with a shape, not floor puffs."""
    pal = S.pal
    cx, cy = S.anchor[0], S.ground - 20
    rr = random.Random(37)
    GREEN = [(54, 70, 40), (96, 124, 60), (146, 176, 84)]
    lobes = [(rr.uniform(-22, 22), rr.uniform(-10, 6), rr.uniform(10, 15), rr.uniform(0, 1), rr.random() < 0.3)
             for _ in range(9)]

    def field(px, py, cur):
        best, bk = -1.0, 0
        for k, (x, y, r) in enumerate(cur):
            v = 1 - math.hypot(px - x, py - y) / r
            if v > best:
                best, bk = v, k
        return best, bk

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        cur = []
        for k, (lx, ly, lr, u, green) in enumerate(lobes):
            sw = math.sin((ph + u) * TAU)
            cur.append((cx + lx + 3 * math.sin((ph + u) * TAU), cy + ly - 2 * sw, lr * (0.85 + 0.15 * sw)))
        x0, x1 = int(min(c[0] - c[2] for c in cur)) - 2, int(max(c[0] + c[2] for c in cur)) + 2
        y0, y1 = int(min(c[1] - c[2] for c in cur)) - 2, int(max(c[1] + c[2] for c in cur)) + 2
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                v, k = field(x, y, cur)
                v += 0.08 * noise2(x * 0.25, y * 0.25 + ph * 3, 7)
                if v <= 0:
                    continue
                green = lobes[k][4]
                cols = GREEN if green else [pal[0], pal[1], pal[2]]
                above = field(x, y - 2, cur)[0] + 0.08 * noise2(x * 0.25, (y - 2) * 0.25 + ph * 3, 7)
                if above <= 0:
                    cv.px(x, y, GREEN[2] if green else pal[3])
                elif v < 0.12 and y > cur[k][1]:
                    cv.px(x, y, cols[0])
                elif (x + y + i // 3) % 2 == 0 or (v > 0.55 and (x + i // 3) % 2 == 0):
                    cv.px(x, y, cols[1] if y < cur[k][1] else cols[0])
        for k in range(3):
            u = (ph + k / 3) % 1
            x0 = cx - 14 + k * 14
            for j in range(12):
                f = j / 12
                y = cy - 18 - u * 26 - f * 8
                x = x0 + math.sin(f * 5 + u * 6 + k) * 3
                if (1 - u) * 12 > j:
                    cv.px(x, y, pal[2] if j < 6 else pal[1])

    run(S, lambda *a: None, draw, loop=True, ground=S.ground, warm=0)


# ------------------------------------------------------------------ ground / rock shared shapes
DUST = [(58, 44, 34), (96, 78, 60), (138, 116, 90), (182, 160, 128), (214, 196, 164)]


def rock_chunk(cv, x, y, r, ang, cols, seed=0):
    """Faceted rock chunk: irregular 5-7 sided polygon, facet facing the top-left light is pale, the rest mid or
    dark, 1 px dark outline. cols = [outline, dark, mid, light]."""
    x, y = int(math.floor(x + 0.5)), int(math.floor(y + 0.5))
    rr = random.Random(seed * 7919 + 13)
    n = rr.randint(5, 7)
    pts = []
    for k in range(n):
        a = ang + k * TAU / n + rr.uniform(-0.3, 0.3)
        rad = r * rr.uniform(0.75, 1.1)
        pts.append((x + math.cos(a) * rad, y + math.sin(a) * rad))
    R = int(r * 1.2 + 2)
    inn = set()
    for dy in range(-R, R + 1):
        for dx in range(-R, R + 1):
            if _inpoly(x + dx + 0.5, y + dy + 0.5, pts):
                inn.add((dx, dy))
    # facet split: a ridge from the top-left vertex region through the centre
    ra = ang + 0.7
    for (dx, dy) in inn:
        edge = any((dx + a, dy + b) not in inn for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        if edge:
            c = cols[0]
        else:
            side = dx * math.sin(ra) - dy * math.cos(ra)
            lit = -dx - dy
            c = cols[3] if (lit > r * 0.3) else cols[2] if side > 0 else cols[1]
        cv.px(x + dx, y + dy, c)


def billow(cv, puffs, cols, i, solid=True, ph=0.0):
    """One dust cloud with form from several round puffs [(x, y, r)]: a single merged mass, lit rim on top,
    shadowed underside, ragged dithered edge. cols = [shadow, body, light, rim]."""
    if not puffs:
        return
    x0, x1 = int(min(p[0] - p[2] for p in puffs)) - 2, int(max(p[0] + p[2] for p in puffs)) + 2
    y0, y1 = int(min(p[1] - p[2] for p in puffs)) - 2, int(max(p[1] + p[2] for p in puffs)) + 2

    def f(px, py):
        best, by = -1.0, 0.0
        for (x, y, r) in puffs:
            if r <= 0.5:
                continue
            v = 1 - math.hypot(px - x, py - y) / r
            if v > best:
                best, by = v, y
        return best + 0.1 * noise2(px * 0.3, py * 0.3 + ph, 11), by

    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            v, cy = f(x, y)
            if v <= 0:
                continue
            if v < 0.12 and (x + y) % 2:
                continue
            up = f(x - 1, y - 2)[0]
            if up <= 0:
                c = cols[3]
            elif y > cy + 2:
                c = cols[0]
            elif f(x - 2, y - 3)[0] <= 0.15:
                c = cols[2]
            else:
                c = cols[1]
            if not solid and v > 0.3 and (x + y + i) % 2 == 0 and c == cols[1]:
                continue
            cv.px(x, y, c)


def _rcols(pal):
    return [pal[0], pal[1], pal[2], pal[3]]


# ------------------------------------------------------------------ ground (material), designed per move
def mud_ball(S):
    """Loop: Mud-Slap / thrown clod - a lumpy brown clump (ragged outline, darker wet spots, pebbles stuck in it)
    tumbling end over end, shedding crumbs of dirt that drop away behind it, a thin dust smear. No glow."""
    pal = S.pal
    hx, hy = S.anchor
    rr = random.Random(43)
    crumbs = [(rr.uniform(0, 1), rr.uniform(-3, 3), rr.uniform(1, 2.2)) for _ in range(9)]

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        for (u, oy, r) in crumbs:
            f = (ph * 2 + u) % 1
            x = hx - 8 - f * 50
            y = hy + oy + 3 + 40 * f * f
            if r > 1.6:
                rock_chunk(cv, x, y, r, f * 6, [pal[0], pal[1], pal[2], pal[3]], seed=int(u * 100))
            else:
                cv.px(x, y, pal[2]); cv.px(x + 1, y, pal[1])
        for k in range(10):
            f = k / 10
            if (k + i) % 3:
                cv.px(hx - 10 - f * 22, hy + math.sin(f * 7 + ph * TAU) * 1.5, DUST[1])
        rot = ph * TAU
        goo(cv, hx - 2, hy, 8.5, 7.5, [pal[0], pal[1], pal[2], pal[2], pal[3], pal[3]], 61, ph, spec=False, rough=0.32)
        for k in range(4):
            a = rot + k * 1.7
            px_, py_ = hx - 2 + math.cos(a) * 4.5, hy + math.sin(a) * 4
            if k % 2:
                cv.px(px_, py_, pal[0]); cv.px(px_ + 1, py_, pal[1])
            else:
                rock_chunk(cv, px_, py_, 1.8, a, [pal[0], DUST[1], DUST[2], DUST[3]], seed=k)

    run(S, lambda *a: None, draw, loop=True, warm=0)


def _crack_tree(rr, cx, gy, n, length, squash=0.32):
    segs = []
    for k in range(n):
        a = k / n * TAU + rr.uniform(-0.3, 0.3)
        x, y = cx, gy
        L = length * rr.uniform(0.6, 1.0)
        steps = 6
        prev = (x, y)
        for s in range(steps):
            a += rr.uniform(-0.5, 0.5)
            d = L / steps
            x, y = x + math.cos(a) * d, y + math.sin(a) * d * squash
            segs.append((prev, (x, y), (s + 1) / steps, k))
            if rr.random() < 0.3 and s > 1:
                b = a + rr.choice((-1, 1)) * rr.uniform(0.6, 1.0)
                bx, by = x + math.cos(b) * d * 1.4, y + math.sin(b) * d * 1.4 * squash
                segs.append(((x, y), (bx, by), (s + 1.5) / steps, k))
            prev = (x, y)
    return segs


def earthquake(S):
    """Earthquake: the ground cracks in three jolts - each jolt extends a web of dark fissures (light lower lip)
    out from under the target, pops rock chips up along the new crack ends and throws rolling dust billows along
    the floor; then dust settles and the cracks stay. Comes from below, no projectile, no glow."""
    pal = S.pal
    cx, gy = S.anchor[0], S.ground - 6
    rr = random.Random(47)
    segs = _crack_tree(rr, cx, gy, 7, 70)
    jolts = (0, 8, 16)
    chips = [dict(x=cx + rr.uniform(-60, 60), j=rr.randrange(3), vy=rr.uniform(-110, -60), vx=rr.uniform(-25, 25),
                  r=rr.uniform(1.6, 3.4), a=rr.uniform(0, TAU)) for _ in range(18)]

    def draw(cv, L, sim, i, t, rng):
        reach = 0.0
        for k, j in enumerate(jolts):
            if i >= j:
                reach = (k + clamp((i - j) / 3)) / 3
        if i >= 0:
            g = clamp((i + 1) / 4)
            for y in range(int(gy - 14 * g), int(gy + 14 * g) + 1):
                for x in range(int(cx - 74 * g), int(cx + 74 * g) + 1):
                    d = ((x - cx) / (74 * g)) ** 2 + ((y - gy) / (14 * g)) ** 2
                    if d < 1 and (d < 0.55 or (x + y) % 2 == 0) and noise2(x * 0.1, y * 0.2, 3) > -0.4 + d * 0.6:
                        cv.px(x, y, pal[1] if d > 0.3 else pal[2])
        for (a, b, f, k) in segs:
            if f > reach:
                continue
            cv.line(a[0], a[1] + 1, b[0], b[1] + 1, pal[2])
            cv.line(a[0], a[1], b[0], b[1], pal[0], w=2 if f < 0.5 else 1)
        # dust billows rolling along the floor after each jolt
        for k, j in enumerate(jolts):
            d = (i - j) / 30
            if 0 <= d < 1:
                puffs = []
                for s in (-1, 1):
                    for m in range(3):
                        x = cx + s * (12 + k * 14 + m * 9 + d * 26)
                        r = (4 + m * 1.5) * math.sin(math.pi * min(1, d * 1.3)) + 0.5
                        puffs.append((x, gy - r * 0.6 + 2, r))
                billow(cv, puffs, [DUST[0], DUST[1], DUST[2], DUST[3]], i, ph=d)
        for k, c in enumerate(chips):
            tt = (i - jolts[c["j"]]) / 30
            if tt < 0:
                continue
            y = gy + c["vy"] * tt + 0.5 * 420 * tt * tt
            if y > gy + 2:
                continue
            rock_chunk(cv, c["x"] + c["vx"] * tt, y, c["r"], c["a"] + tt * 8, _rcols(pal), seed=k)

    run(S, lambda *a: None, draw, ground=S.ground)


def dig_burst(S):
    """Dig (emerging) / Sand-Attack: the floor bursts open under the target - a dark hole with a raised dirt rim,
    a fountain of clods and rock chunks thrown up and falling back, and a dust cloud with real form rolling out
    to both sides and rising, then settling. Material: no flash."""
    pal = S.pal
    cx, gy = S.anchor[0], S.ground
    rr = random.Random(53)
    clods = [dict(vx=rr.uniform(-80, 80), vy=rr.uniform(-210, -90), r=rr.uniform(2, 4.5), a=rr.uniform(0, TAU),
                  d=rr.uniform(0, 0.1)) for _ in range(16)]
    G = 480

    def draw(cv, L, sim, i, t, rng):
        hole = clamp(t / 0.1) * (1 - clamp((t - 1.0) / 0.3))
        if hole > 0:
            cv.ellipse(cx, gy - 1, 16 * hole, 3.5 * hole, pal[0])
            for k in range(12):
                a = math.pi + k / 11 * math.pi
                rock_chunk(cv, cx + math.cos(a) * 17 * hole, gy - 1 + math.sin(a) * 4 * hole, 2.4 * hole + 0.5,
                           k * 0.8, _rcols(pal), seed=k)
        # dust cloud: puffs roll outwards and up
        u = clamp(t / 1.2)
        if t < 1.4:
            puffs = []
            for s in (-1, 1):
                for m in range(4):
                    x = cx + s * (5 + m * 6 + 14 * out_cubic(u) * (0.5 + m * 0.25))
                    y = gy - 4 - (3 - m) * 4 - 22 * u * (1 - m * 0.2)
                    r = (8 - m * 1.2) * (0.3 + 1.1 * out_cubic(clamp(t / 0.35))) * (1 - clamp((t - 0.8) / 0.5))
                    if r < 2:
                        continue
                    puffs.append((x, y, r))
            rc = 10 * out_cubic(clamp(t / 0.3)) * (1 - clamp((t - 0.8) / 0.5))
            if rc >= 2:
                puffs.append((cx, gy - 14 - 24 * u, rc))
            billow(cv, puffs, [DUST[1], DUST[2], DUST[3], DUST[4]], i, ph=t)
        for k, c in enumerate(clods):
            tt = t - c["d"]
            if tt <= 0:
                continue
            y = gy - 4 + c["vy"] * tt + 0.5 * G * tt * tt
            if y > gy - 1:
                continue
            rock_chunk(cv, cx + c["vx"] * tt, y, c["r"], c["a"] + tt * 6, _rcols(pal), seed=k + 20)

    run(S, lambda *a: None, draw, ground=gy)


# ------------------------------------------------------------------ rock (material), designed per move
def boulder_throw(S):
    """Loop: Rock Throw - one big faceted boulder (angular, lit top-left facet, dark bottom, cracks) tumbling as it
    flies, short speed lines behind, pebbles and a small dust puff peeling off. Heavy and solid; no glow."""
    pal = S.pal
    hx, hy = S.anchor
    rr = random.Random(59)
    peb = [(rr.uniform(0, 1), rr.uniform(-6, 6), rr.uniform(1.2, 2.4)) for _ in range(6)]

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        for k in range(4):
            yy = hy - 8 + k * 5
            ln = 10 + (k * 7) % 9
            x0 = hx - 18 - ((ph * 3 + k * 0.3) % 1) * 10
            for d in range(int(ln)):
                if d % 4 != 3:
                    cv.px(x0 - d, yy, DUST[2] if d < 4 else DUST[1])
        for (u, oy, r) in peb:
            f = (ph * 2 + u) % 1
            rock_chunk(cv, hx - 14 - f * 40, hy + oy + 22 * f * f, r, f * 9, _rcols(pal), seed=int(u * 50))
        puffs = [(hx - 16 - ((ph * 2) % 1) * 18, hy + 8, 4 * (1 - (ph * 2) % 1) + 0.5)]
        billow(cv, puffs, [DUST[0], DUST[1], DUST[2], DUST[3]], i)
        rot = -ph * TAU
        rock_chunk(cv, hx - 4, hy, 13, rot, _rcols(pal), seed=3)
        for k in range(2):
            a = rot + k * 2.2
            x0, y0 = hx - 4 + math.cos(a) * 3, hy + math.sin(a) * 3
            cv.line(x0, y0, x0 + math.cos(a + 0.5) * 6, y0 + math.sin(a + 0.5) * 6, pal[1])

    run(S, lambda *a: None, draw, loop=True, warm=0)


def rock_slide(S):
    """Rock Slide hit: four angular boulders fall from above the frame onto the target one after another,
    accelerating, each lands with a small bounce, a dust billow and chips flying; the last ones pile, then the
    pile crumbles into chunks and the dust settles. Heavy, no glow."""
    pal = S.pal
    cx, gy = S.anchor[0], S.ground
    rr = random.Random(61)
    rocks = [dict(x=cx + dx, t0=t0, r=r, a=rr.uniform(0, TAU), land=gy - r * 0.8 - lift)
             for (dx, t0, r, lift) in ((-8, 0.0, 10, 0), (10, 0.12, 9, 0), (0, 0.24, 11, 14), (-14, 0.36, 7, 0))]
    G = 900
    chips = [dict(k=rr.randrange(4), vx=rr.uniform(-90, 90), vy=rr.uniform(-140, -40), r=rr.uniform(1.4, 3))
             for _ in range(20)]

    def land_t(rk):
        return rk["t0"] + math.sqrt(2 * (rk["land"] + 20) / G)

    def draw(cv, L, sim, i, t, rng):
        crumble = clamp((t - 1.05) / 0.4)
        for k, rk in enumerate(rocks):
            if t < rk["t0"]:
                continue
            tl = land_t(rk)
            if t < tl:
                tt = t - rk["t0"]
                y = -20 + 0.5 * G * tt * tt
                ang = rk["a"] + tt * 3
            else:
                d = t - tl
                y = rk["land"] - max(0.0, 26 * d - 260 * d * d)
                ang = rk["a"] + (tl - rk["t0"]) * 3
                if d < 0.6:
                    puffs = [(rk["x"] + s * (4 + d * 30), gy - 3 - d * 10, (6 - d * 6) * min(1, d * 10) + 0.3)
                             for s in (-1, 1)]
                    billow(cv, puffs, [DUST[0], DUST[1], DUST[2], DUST[3]], i, ph=d)
            if crumble > 0:
                if (k * 3 + int(crumble * 10)) % 4 < crumble * 4:
                    continue
            rock_chunk(cv, rk["x"], y, rk["r"] * (1 - crumble * 0.3), ang, _rcols(pal), seed=k + 7)
        for c in chips:
            rk = rocks[c["k"]]
            tt = t - land_t(rk)
            if tt <= 0:
                continue
            y = gy - 4 + c["vy"] * tt + 0.5 * 600 * tt * tt
            if y > gy - 1:
                continue
            rock_chunk(cv, rk["x"] + c["vx"] * tt, y, c["r"], tt * 7, _rcols(pal), seed=c["k"] + 30)
        if crumble > 0:
            for k in range(8):
                rock_chunk(cv, cx - 18 + k * 5, gy - 2 - (k % 2) * 2, 2.5 + (k % 3), k, _rcols(pal), seed=k + 40)

    run(S, lambda *a: None, draw, ground=gy)


def stone_edge(S):
    """Stone Edge / Rock Tomb: angular stone blades burst up from the floor around the target one after another
    (each a 3-facet shard with a hard outline and a chipped tip), kicking chips and a dust skirt at the base,
    hold, then crack and crumble into chunks that drop."""
    pal = S.pal
    cx, gy = S.anchor[0], S.ground
    rr = random.Random(67)
    spikes = []
    for k in range(5):
        x = cx + (k - 2) * 26 + rr.uniform(-4, 4)
        spikes.append(dict(x=x, h=rr.uniform(44, 66), w=rr.uniform(9, 13), lean=rr.uniform(-8, 8), t0=k * 0.05,
                           chip=rr.uniform(0.2, 0.5)))

    def shard(cv, sp, g, crack):
        x, w, h = sp["x"], sp["w"], sp["h"] * g
        tip = (x + sp["lean"] * g, gy - h)
        bl, br = (x - w, gy), (x + w, gy)
        mid = (x + w * 0.15, gy)
        ls = (x - w * 0.95 + sp["lean"] * 0.45 * g, gy - h * 0.42)
        rs = (x + w * 0.45 + sp["lean"] * 0.6 * g, gy - h * 0.62)
        ridge = (x + w * 0.05 + sp["lean"] * 0.5 * g, gy - h * 0.5)
        left = [bl, mid, ridge, tip, ls]
        right = [mid, br, rs, tip, ridge]
        for poly, c in ((left, pal[3]), (right, pal[1])):
            xs = [p[0] for p in poly]
            ys = [p[1] for p in poly]
            for yy in range(int(min(ys)), int(max(ys)) + 1):
                for xx in range(int(min(xs)) - 1, int(max(xs)) + 2):
                    if _inpoly(xx + 0.5, yy + 0.5, poly):
                        cv.px(xx, yy, c if (yy - tip[1]) > 3 or c != pal[1] else pal[2])
        for a_, b_ in ((bl, ls), (ls, tip), (br, rs), (rs, tip)):
            cv.line(a_[0], a_[1], b_[0], b_[1], pal[0])
        cv.line(mid[0], mid[1], ridge[0], ridge[1], pal[4])
        cv.line(ridge[0], ridge[1], tip[0], tip[1], pal[4])
        cv.line(tip[0] - 2, tip[1] + 6, tip[0] + 3, tip[1] + 9, pal[0])
        if crack:
            cv.line(x - w * 0.4, gy - h * 0.4, x + w * 0.3, gy - h * 0.55, pal[0])
            cv.line(x + w * 0.3, gy - h * 0.55, x - w * 0.1, gy - h * 0.7, pal[0])

    def draw(cv, L, sim, i, t, rng):
        for k, sp in enumerate(spikes):
            tt = t - sp["t0"]
            if tt <= 0:
                continue
            g = out_cubic(clamp(tt / 0.12))
            end = clamp((t - 1.0) / 0.35)
            if end < 0.5:
                shard(cv, sp, g, t > 0.85)
            else:
                for j in range(5):
                    yy = gy - sp["h"] * (0.2 + j * 0.15) + (end - 0.5) * 2 * 60 * (1 + j * 0.2)
                    if yy < gy - 2:
                        rock_chunk(cv, sp["x"] + (j - 2) * 3, yy, 4 - j * 0.4, j + k, _rcols(pal), seed=k * 5 + j)
            if tt < 0.5:
                d = tt / 0.5
                puffs = [(sp["x"] + s * (sp["w"] + d * 16), gy - 3 - d * 4, 5 * math.sin(math.pi * d) + 0.3)
                         for s in (-1, 1)]
                billow(cv, puffs, [DUST[0], DUST[1], DUST[2], DUST[3]], i, ph=d)
                for j in range(3):
                    a = -math.pi / 2 + (j - 1) * 0.9
                    rr_ = 6 + tt * 90
                    yy = gy - 6 + math.sin(a) * rr_ + 300 * tt * tt
                    if yy < gy - 1:
                        rock_chunk(cv, sp["x"] + math.cos(a) * rr_, yy, 1.8, tt * 9, _rcols(pal), seed=k * 3 + j)

    run(S, lambda *a: None, draw, ground=gy)


# ------------------------------------------------------------------ flying (material: air), designed per move
AIR = [(70, 84, 120), (130, 150, 196), (196, 212, 240), (244, 248, 255)]


def wind_curl(cv, x, y, r, a0, turns, cols, tail=0, sx=1.0):
    """Wind curl: a thin spiral hook (radius shrinking to the centre) with a straight tail leading into it."""
    steps = int(r * turns * 8) + 4
    for k in range(steps):
        f = k / steps
        a = a0 + f * turns * TAU
        rad = r * (1 - f * 0.8)
        c = cols[min(len(cols) - 1, int((1 - f) * len(cols)))] if f > 0.15 else cols[-1]
        cv.px(x + math.cos(a) * rad * sx, y + math.sin(a) * rad, c)
    if tail:
        tx, ty = x + math.cos(a0) * r * sx, y + math.sin(a0) * r
        ta = a0 - math.pi / 2 * (1 if sx > 0 else -1)
        for k in range(int(tail)):
            if k % 6 != 5:
                cv.px(tx + math.cos(ta) * k, ty + math.sin(ta) * k * 0.15, cols[-1] if k < tail * 0.4 else cols[0])


def feather(cv, x, y, ang, s, flat=1.0):
    leaf_shape(cv, x, y, ang, s, max(1.2, s * 0.42 * flat), [AIR[1], AIR[2], AIR[3], AIR[1]], vein=True, tip=0.55)


def air_blade(S):
    """Loop: Wing Attack / Razor Wind - two pale crescent air blades (a big one and a small echo) flying edge-first,
    thin wind lines curling off their tips, a loose feather tumbling behind. Air is a material: no glow."""
    pal = S.pal
    hx, hy = S.anchor

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        for k in range(3):
            u = (ph * 2 + k / 3) % 1
            yy = hy - 9 + k * 9
            wind_curl(cv, hx - 10 - u * 40, yy, 3 + k, -math.pi / 2 + u * 2, 0.8, [AIR[0], AIR[1], AIR[2]],
                      tail=10 + k * 4)
        crescent(cv, hx - 22, hy + 1, 9, -1.2, 1.2, 2.5, [AIR[1], AIR[2], AIR[3]], squash=1.0)
        crescent(cv, hx - 4, hy, 14, -1.3, 1.3, 3.6, [AIR[1], AIR[2], AIR[3]], squash=1.0)
        f = ph
        feather(cv, hx - 30 - f * 20, hy + 8 + math.sin(f * TAU) * 3, f * TAU, 9, abs(math.cos(f * TAU * 2)))

    run(S, lambda *a: None, draw, loop=True, warm=0)


def gust(S):
    """Gust: wind curls sweep in from the attacker side and wrap around the target (spiral hooks with long tails,
    pale and thin), carrying leaves and dust bits; dust kicks up at the base; ~1 s. Not a radial burst."""
    pal = S.pal
    cx, cy = S.anchor
    gy = S.ground
    rr = random.Random(71)
    curls = [dict(t0=k * 0.07, y=cy - 14 + k * 7 + rr.uniform(-2, 2), r=rr.uniform(5, 9), sx=rr.choice((1, -1)))
             for k in range(5)]
    bits = [dict(u=rr.uniform(0, 1), r=rr.uniform(8, 22), y=rr.uniform(-18, 10), leaf=rr.random() < 0.5,
                 sp=rr.uniform(2, 3.5)) for _ in range(10)]

    def draw(cv, L, sim, i, t, rng):
        for c in curls:
            tt = t - c["t0"]
            if tt <= 0 or tt > 0.8:
                continue
            arrive = out_cubic(clamp(tt / 0.3))
            x = 4 + (cx - 4) * arrive
            fade = clamp((tt - 0.55) / 0.25)
            cols = [AIR[0], AIR[1], AIR[2]] if fade < 0.5 else [AIR[0], AIR[0], AIR[1]]
            wind_curl(cv, x + (tt - 0.3) * 30 * (tt > 0.3), c["y"], c["r"] * (1 + fade * 0.6), math.pi / 2 + tt * 8,
                      0.9, cols, tail=int(30 * (1 - arrive) + 8))
        for k, b in enumerate(bits):
            tt = t - 0.15
            if tt <= 0 or tt > 0.9:
                continue
            a = b["u"] * TAU + tt * b["sp"] * TAU
            x = cx + math.cos(a) * b["r"] * (1 + tt)
            y = cy + b["y"] + math.sin(a) * b["r"] * 0.35 - tt * 10
            if b["leaf"]:
                leaf_shape(cv, x, y, a * 2, 6, 2.6 * abs(math.cos(a * 3)) + 0.8,
                           [(36, 80, 40), (76, 140, 60), (140, 196, 90), (36, 80, 40)])
            else:
                cv.px(x, y, DUST[3]); cv.px(x + 1, y, DUST[2])
        if 0.1 < t < 1.0:
            d = (t - 0.1) / 0.9
            puffs = [(cx + s * (8 + d * 26), gy - 3 - d * 5, 5 * math.sin(math.pi * d) + 0.3) for s in (-1, 1)]
            billow(cv, puffs, [DUST[0], DUST[1], DUST[2], DUST[3]], i, ph=d)

    run(S, lambda *a: None, draw, ground=gy)


def whirlwind(S):
    """Loop: Whirlwind / tornado - a funnel of thin broken wind lines (tilted ellipse arcs widening upward, front
    arcs bright, back arcs dim), a spiral line climbing it, rock bits, leaves and dust caught and orbiting, a dust
    cloud churning at the base. Wind + debris, unlike the leaf storm (leaves only) and whirlpool (water)."""
    pal = S.pal
    cx, gy = S.anchor[0], S.ground
    rr = random.Random(73)
    debris = [(rr.uniform(0, 1), rr.uniform(0, 1), rr.choice(("rock", "rock", "leaf", "dust"))) for _ in range(14)]

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        H = 100
        billow(cv, [(cx + s * 12 + math.sin(ph * TAU + s) * 3, gy - 4, 7) for s in (-1, 0, 1)] +
               [(cx + s * 22, gy - 2, 4) for s in (-1, 1)], [DUST[0], DUST[1], DUST[2], DUST[3]], i, ph=ph * 3)
        for layer in (0, 1):
            for k in range(12):
                h = k / 12
                y = gy - 8 - h * H
                rx = 6 + h * h * 30 + h * 6
                off = math.sin(h * 5 + ph * TAU) * 4 * h
                for j in range(int(rx * 7)):
                    a = j / (rx * 7) * TAU + ph * TAU * 2 + k
                    front = math.sin(a) > 0
                    if front != bool(layer):
                        continue
                    if noise2(a * 1.5 + k, ph * 4 + h * 3, 5) < -0.05:
                        continue
                    cv.px(cx + off + math.cos(a) * rx, y + math.sin(a) * rx * 0.22,
                          (AIR[3] if h < 0.6 else AIR[2]) if front else AIR[0])
            if layer == 0:
                for (u, v, kind) in debris:
                    h = (u + ph) % 1
                    a = v * TAU + ph * TAU * 3
                    rx = 6 + h * h * 30 + h * 6 + 3
                    x = cx + math.sin(h * 5 + ph * TAU) * 4 * h + math.cos(a) * rx
                    y = gy - 8 - h * H + math.sin(a) * rx * 0.22
                    if kind == "rock":
                        rock_chunk(cv, x, y, 3.2, a, [DUST[0], DUST[1], DUST[2], DUST[3]], seed=int(v * 99))
                    elif kind == "leaf":
                        leaf_shape(cv, x, y, a, 9, 3.6 * abs(math.cos(a)) + 0.8,
                                   [(36, 80, 40), (76, 140, 60), (140, 196, 90), (36, 80, 40)])
                    else:
                        cv.px(x, y, DUST[3]); cv.px(x + 1, y, DUST[2]); cv.px(x, y + 1, DUST[2])

    run(S, lambda *a: None, draw, loop=True, ground=gy, warm=0)


# ------------------------------------------------------------------ psychic (emissive), designed per move
PSY_BAND = [(255, 120, 200), (200, 110, 255), (120, 170, 255), (255, 200, 120)]


def wavy_ring(cv, x, y, r, waves, amp, phase, col, squash=1.0, col_back=None, steps=None):
    steps = steps or max(24, int(r * 8))
    for k in range(steps):
        a = k / steps * TAU
        rr_ = r + amp * math.sin(a * waves + phase)
        c = col if (col_back is None or math.sin(a) > 0) else col_back
        cv.px(x + math.cos(a) * rr_, y + math.sin(a) * rr_ * squash, c)


def psybeam(S):
    """Psybeam: a band of rings travelling down a sine-wave path - each ring a tall thin ellipse, colours cycling
    pink / violet / blue / gold (the psychedelic band), rings pulsing in size; at the target the rings collapse
    into concentric ripples. Emissive, soft light."""
    pal = S.pal
    ox, oy = S.anchor
    tx = S.w - 8
    t_on, t_off = 0.15, 1.0

    def draw(cv, L, sim, i, t, rng):
        h = ox + (tx - ox) * clamp((t - t_on) / 0.25)
        tail = ox + (tx - ox) * clamp((t - t_off) / 0.2)
        if t < t_on:
            wavy_ring(cv, ox, oy, 2 + t / t_on * 4, 3, 1, t * 20, pal[4])
            L.add(ox, oy, 10, pal[3], 0.5)
        if h > tail + 2:
            for x in range(int(tail), int(h)):
                y = oy + math.sin((x - ox) * 0.12 - t * 14) * 3
                cv.px(x, y, pal[5] if x % 2 else pal[4])
            k0 = int((t * 90) // 7)
            x = ox + ((t * 90) % 7)
            k = 0
            while x < h:
                if x > tail:
                    y = oy + math.sin((x - ox) * 0.12 - t * 14) * 3
                    col = PSY_BAND[(k - k0) % 4]
                    ry = 5 + 3 * math.sin((x - ox) * 0.2 - t * 18)
                    for j in range(int(ry * 6)):
                        a = j / (ry * 6) * TAU
                        cv.px(x + math.cos(a) * 2.2, y + math.sin(a) * ry, col)
                    if k % 2 == 0:
                        L.add(x, y, 9, col, 0.25)
                x += 7
                k += 1
        tl = t - (t_on + 0.25)
        if 0 < tl < 0.9:
            for k in range(3):
                u = ((tl * 1.8) + k / 3) % 1
                wavy_ring(cv, tx, oy, 3 + u * 14, 5, 1.5, t * 10, PSY_BAND[k % 4] if u < 0.7 else pal[2], squash=1.0)
            L.add(tx, oy, 18, pal[3], 0.5)

    run(S, lambda *a: None, draw, ground=S.ground)


def psychic_wave(S):
    """Psychic / Confusion hit: wavy concentric ripples centred on the target pulse out in three beats (pull in,
    push out), the air over the target bends (horizontal sine-wave distortion bands drawn across it), pink motes
    drift and a few white star glints; soft glow, no hard spark edges."""
    pal = S.pal
    cx, cy = S.anchor
    beats = (0.0, 0.3, 0.6)
    rr = random.Random(79)
    motes = [(rr.uniform(0, TAU), rr.uniform(10, 34), rr.uniform(0, 1)) for _ in range(18)]

    def draw(cv, L, sim, i, t, rng):
        for b in beats:
            u = (t - b) / 0.55
            if 0 <= u < 1:
                pull = 1 - 0.25 * math.sin(math.pi * min(1, u * 4)) if u < 0.25 else 1
                r = (6 + 38 * out_cubic(u)) * pull
                col = pal[5] if u < 0.2 else pal[4] if u < 0.5 else pal[3] if u < 0.8 else pal[2]
                wavy_ring(cv, cx, cy, r, 7, 1.6 + u * 2, t * 12 + b * 9, col, squash=0.8)
                if u < 0.6:
                    wavy_ring(cv, cx, cy, r * 0.7, 5, 1.2, -t * 10, pal[3], squash=0.8)
                L.add(cx, cy, r * 0.8, pal[3], 0.35 * (1 - u))
        if t < 1.0:
            for k in range(7):
                y = cy - 15 + k * 5
                for x in range(int(cx - 18), int(cx + 19)):
                    if (x + k) % 2:
                        continue
                    dy = math.sin(x * 0.35 + t * 18 + k) * 1.5
                    if abs(x - cx) < 18 - abs(k - 3) * 2:
                        cv.px(x, y + dy, pal[2] if (x // 3 + k) % 3 else pal[3])
        for (a, r, u) in motes:
            tt = (t * 0.8 + u) % 1
            x = cx + math.cos(a + tt * 2) * r
            y = cy + math.sin(a + tt * 2) * r * 0.7 - tt * 10
            if t < 1.2:
                cv.px(x, y, pal[4] if tt < 0.5 else pal[3])
        for k in range(3):
            if (i + k * 5) % 9 < 2 and t < 1.1:
                a = k * 2.1 + 0.4
                snowflake(cv, cx + math.cos(a) * 20, cy + math.sin(a) * 14, 2, (255, 255, 255), pal[4])

    run(S, lambda *a: None, draw, ground=S.ground)


def mind_field(S):
    """Loop: Psychic field - two wavy rings counter-rotate around the unit at hip and head height (back half dim,
    front half bright), the space inside shimmers with thin vertical sine lines rising, motes drift up; a held
    telekinetic grip rather than a hit."""
    pal = S.pal
    cx, fy = S.w / 2, S.ground
    rr = random.Random(83)
    motes = [(rr.uniform(-16, 16), rr.uniform(0, 1)) for _ in range(10)]

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        for (yy, r, dirn, w) in ((fy - 6, 17, 1, 6), (fy - 22, 13, -1, 5)):
            wavy_ring(cv, cx, yy, r, w, 1.4, dirn * ph * TAU * 2, pal[4], squash=0.3, col_back=pal[2])
            L.add(cx, yy, r, pal[3], 0.25)
        for k in range(4):
            x0 = cx - 9 + k * 6
            u = (ph + k * 0.25) % 1
            for j in range(10):
                y = fy - 4 - u * 30 - j
                if fy - 34 < y < fy - 2:
                    cv.px(x0 + math.sin(j * 0.8 + ph * TAU * 2) * 1.5, y, pal[3] if j < 5 else pal[2])
        for (dx, u) in motes:
            f = (ph + u) % 1
            cv.px(cx + dx + math.sin(f * 9) * 2, fy - 4 - f * 40, pal[5] if f < 0.3 else pal[4])

    run(S, lambda *a: None, draw, loop=True, ground=fy, warm=0)


# ------------------------------------------------------------------ bug (material), designed per move
def needle(cv, x, y, ang, L, pal, shaft=(236, 236, 214)):
    """Thin needle: pale shaft, dark green pointed tip at (x, y), a 2 px fletch at the back."""
    ca, sa = math.cos(ang), math.sin(ang)
    for k in range(int(L)):
        px_, py_ = x - ca * k, y - sa * k
        c = (150, 150, 120) if k < 3 else shaft if k < L - 2 else pal[3]
        cv.px(px_, py_, c)
        if 3 <= k < L - 3 and k % 2 == 0:
            cv.px(px_ - sa, py_ + ca, (176, 176, 160))
    bx, by = x - ca * (L - 1), y - sa * (L - 1)
    cv.px(bx - sa * 1.5, by + ca * 1.5, pal[3]); cv.px(bx + sa * 1.5, by - ca * 1.5, pal[3])


def pin_missile(S):
    """Loop: Pin Missile - five thin needles (pale shaft, dark tip, green fletch) fly straight and fast in a
    staggered rapid burst, each with a short speed line; no glowing core."""
    pal = S.pal
    hx, hy = S.anchor
    rr = random.Random(89)
    pins = [(rr.uniform(0, 1), rr.uniform(-12, 12)) for _ in range(5)]

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        for k, (u, oy) in enumerate(pins):
            f = (ph * 2 + u) % 1
            x = hx + 4 - (1 - f) * 70
            if x < 14:
                continue
            needle(cv, x, hy + oy, 0.0, 13, pal)
            for d in range(8):
                if d % 3 != 2:
                    cv.px(x - 15 - d, hy + oy, pal[2] if d < 4 else pal[1])

    run(S, lambda *a: None, draw, loop=True, warm=0)


def twineedle_hit(S):
    """Poison Sting / Twineedle hit: two needles jab into the target one after the other (each stops dead and
    quivers), a small white contact puff at each tip, then a little purple poison puff bubbles up from the wound;
    the needles drop out and fall. Small and sharp, no radial burst."""
    pal = S.pal
    cx, cy = S.anchor
    gy = S.ground
    PURP = [(42, 18, 56), (92, 35, 120), (148, 64, 184), (196, 110, 224)]
    jabs = [(0.0, cx - 4, cy + 4, 0.25), (0.17, cx + 1, cy + 11, -0.15)]

    def draw(cv, L, sim, i, t, rng):
        for k, (t0, x, y, a) in enumerate(jabs):
            tt = t - t0
            if tt < 0:
                continue
            ca, sa = math.cos(a), math.sin(a)
            if tt < 0.06:
                u = tt / 0.06
                needle(cv, x - ca * 30 * (1 - u), y - sa * 30 * (1 - u), a, 14, pal)
            elif tt < 0.6:
                q = math.sin(tt * 90) * max(0.0, 1 - (tt - 0.06) * 8)
                needle(cv, x + 3 * ca, y + 3 * sa + q, a, 14, pal)
            else:
                d = tt - 0.6
                yy = y + 200 * d * d
                if yy < gy - 1:
                    needle(cv, x - 4 - d * 20, yy, a + d * 6, 14, pal)
            if 0.06 <= tt < 0.2:
                pow_star(cv, x + 3 * ca, y + 3 * sa, 6 - (tt - 0.06) * 25, [None, (150, 150, 150), None, None,
                         (230, 230, 230)], n=5, white=(255, 255, 255))
            if 0.22 <= tt < 1.1:
                d = (tt - 0.22) / 0.88
                for j in range(3):
                    u = d * 1.3 - j * 0.18
                    if 0 < u < 1:
                        r = 1.5 + j * 0.5 + u * 1.5
                        goo(cv, x + 4 + j * 3 + math.sin(u * 6 + j) * 2, y - 2 - u * 18 - j * 2, r, r, PURP + [(220, 160, 240), (250, 225, 255)],
                            70 + j, u, spec=r > 2.4)
                if d < 0.6:
                    billow(cv, [(x + 5, y - 2, 4 * math.sin(math.pi * d / 0.6) + 0.3)], PURP, i, solid=False)

    run(S, lambda *a: None, draw, ground=gy)


def bug_buzz(S):
    """Loop: Bug Buzz / Supersonic - vibrating sound arcs: each arc is a ')' whose edge zig-zags at high frequency
    (it trembles every frame), expanding and thinning as it travels, with little 'buzz' tick marks between them.
    Unlike the fighting force wave (rigid pressure rings with a hard front)."""
    pal = S.pal
    ox, oy = S.anchor
    n = S.n

    def draw(cv, L, sim, i, t, rng):
        ph = i / n
        for k in range(4):
            u = (ph + k / 4) % 1
            r = 6 + u * (S.w - 20)
            span = 0.5 + 0.2 * (1 - u)
            steps = int(r * span * 4) + 6
            for j in range(steps):
                a = -span + 2 * span * j / steps
                z = (1.6 if (j + i) % 2 else -1.6) * (1 - u * 0.5)
                rad = r + z
                c = pal[4] if u < 0.4 else pal[3] if u < 0.75 else pal[2]
                cv.px(ox + math.cos(a) * rad, oy + math.sin(a) * rad * 1.1, c)
                if u < 0.5 and j % 2:
                    cv.px(ox + math.cos(a) * (rad - 1), oy + math.sin(a) * (rad - 1) * 1.1, pal[2])
        for k in range(5):
            u = (ph * 2 + k / 5) % 1
            x = ox + 10 + u * (S.w - 30)
            y = oy + (k - 2) * 7 + (1 if (i + k) % 2 else -1)
            cv.line(x, y, x + 2, y - 2, pal[3]); cv.line(x + 2, y - 2, x + 4, y, pal[3])

    run(S, lambda *a: None, draw, loop=True, warm=0)


def bug_swarm(S):
    """Loop: a swarm of real little insects (dark body, pale wings flicking open and shut every other frame)
    circling the target on looping paths, some passing in front, some behind; a faint buzzing tick here and
    there. Bugs, not dots."""
    pal = S.pal
    cx, cy = S.anchor[0], S.ground - 24
    rr = random.Random(97)
    bugs = [(rr.uniform(0, 1), rr.uniform(12, 30), rr.uniform(0.5, 0.9), rr.choice((1, 2)) * rr.choice((-1, 1)),
             rr.uniform(0, TAU)) for _ in range(16)]

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        for k, (u, r, sq, sp, p) in enumerate(bugs):
            a = (u + ph * sp) * TAU
            x = cx + math.cos(a) * r + 3 * math.sin(ph * TAU * 3 + p)
            y = cy + math.sin(a) * r * sq * 0.6 + 4 * math.sin(a * 2 + p)
            back = math.sin(a) < 0
            body = (34, 44, 16) if not back else (60, 74, 30)
            dx = -1 if math.cos(a + math.pi / 2 * (1 if sp > 0 else -1)) < 0 else 1
            for j in (-1, 0, 1):
                cv.px(x + j * dx, y, body)
                cv.px(x + j * dx, y + 1, body if j else pal[1])
            cv.px(x + dx * 2, y, pal[3] if not back else pal[2])
            wc = (236, 244, 226) if not back else (140, 150, 140)
            if (i + k) % 2:
                cv.px(x - dx, y - 1, wc); cv.px(x, y - 2, wc); cv.px(x - dx, y - 2, wc); cv.px(x + 1 - dx, y - 3, wc)
            else:
                cv.px(x - dx, y - 1, wc); cv.px(x - 2 * dx, y - 1, wc); cv.px(x - dx, y + 2, wc)

    run(S, lambda *a: None, draw, loop=True, warm=0)


# ------------------------------------------------------------------ ghost (emissive), designed per move
GHOST_PINK = (236, 120, 220)


def ghost_eyes(cv, x, y, s, open_):
    """A pair of slanted ghost eyes (our own drawing): white slits with a dark pupil; open_ 0..1."""
    h = max(0, int(round(2 * open_)))
    for side in (-1, 1):
        ex = x + side * (3 + s)
        for k in range(-2 - s, 3 + s):
            yy = y + (k * side) * 0.25
            for j in range(-h // 2, h - h // 2 + (1 if h else 0)):
                cv.px(ex + k, yy + j, (255, 255, 255))
        if h:
            cv.px(ex + side, y, (40, 10, 50))


def shadow_ball(S):
    """Loop: Shadow Ball - a dark swirling orb: near-black core, purple swirl arms turning inside it, a thin
    magenta-pink rim that is the only bright part (light only at the rim), dark smoke wisps trailing and curling.
    Dark core, not a bright head."""
    pal = S.pal
    hx, hy = S.anchor
    R = 9

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        for k in range(5):
            u = (ph * 2 + k / 5) % 1
            billow(cv, [(hx - 8 - u * 34, hy + math.sin(u * 7 + k) * 4, 4.5 * (1 - u) + 0.6)],
                   [pal[0], pal[1], pal[1], pal[2]], i, solid=False, ph=u)
        x, y = hx - 4, hy
        cv.disc(x, y, R, pal[0])
        for arm in range(3):
            for k in range(26):
                f = k / 26
                a = ph * TAU * 2 + arm * TAU / 3 + f * 4
                r = f * (R - 1.5)
                cv.px(x + math.cos(a) * r, y + math.sin(a) * r, pal[2] if f > 0.4 else pal[1])
        for k in range(int(R * 7)):
            a = k / (R * 7) * TAU
            wob = 0.6 * math.sin(a * 5 + ph * TAU * 3)
            c = GHOST_PINK if (k + i) % 5 else pal[4]
            cv.px(x + math.cos(a) * (R + wob), y + math.sin(a) * (R + wob), c)
            if k % 9 == 0:
                L.add(x + math.cos(a) * R, y + math.sin(a) * R, 5, GHOST_PINK, 0.22)

    run(S, lambda *a: None, draw, loop=True, warm=0)


def hex_haunt(S):
    """Night Shade / Hex / Lick hit: purple fog creeps over the floor, the target is overlaid by a dark violet
    silhouette (the 'hexed' tint), ghostly purple flames rise around it, a pair of slanted eyes opens above it and
    stares, then a pink-magenta orb flash ends it. Atmosphere, not a spark burst."""
    pal = S.pal
    cx, cy = S.anchor
    gy = S.ground
    rr = random.Random(101)
    flames = [(rr.uniform(-22, 22), rr.uniform(0, 0.3), rr.uniform(10, 18)) for _ in range(7)]

    def draw(cv, L, sim, i, t, rng):
        fog = clamp(t / 0.3) * (1 - clamp((t - 1.0) / 0.3))
        if fog > 0:
            for y in range(int(gy - 10 * fog), gy):
                for x in range(int(cx - 60 * fog), int(cx + 60 * fog)):
                    v = noise2(x * 0.08 + t * 2, y * 0.2, 13)
                    if v > 0.1 - fog * 0.3 and (x + y + i // 2) % 2 == 0:
                        cv.px(x, y, pal[1] if v < 0.4 else pal[2])
        tint = clamp((t - 0.1) / 0.15) * (1 - clamp((t - 0.9) / 0.2))
        if tint > 0:
            for y in range(int(cy - 10), int(gy)):
                for x in range(int(cx - 13), int(cx + 14)):
                    if ((x - cx) / 13) ** 2 + ((y - (gy - 13)) / 14) ** 2 < 1 and (x + y) % 2 == 0:
                        cv.px(x, y, pal[0] if tint > 0.5 else pal[1])
        for k, (dx, t0, h) in enumerate(flames):
            tt = t - 0.15 - t0
            if 0 < tt < 0.85:
                g = math.sin(math.pi * tt / 0.85)
                tongue_dir(cv, cx + dx, gy - 1, -math.pi / 2 + 0.2 * math.sin(tt * 9 + k), 3.0, h * g,
                           [pal[1], pal[3], GHOST_PINK], 190 + k, t, bend=4)
                L.add(cx + dx, gy - 6, 7, pal[3], 0.25 * g)
        if 0.3 < t < 1.05:
            op = clamp((t - 0.3) / 0.1) * (1 - clamp((t - 0.95) / 0.1))
            ghost_eyes(cv, cx, cy - 22, 2, op)
            L.add(cx, cy - 22, 12, GHOST_PINK, 0.4 * op)
        if 1.0 <= t < 1.2:
            r = 4 + (t - 1.0) * 60
            cv.disc(cx, cy, r * 0.5, GHOST_PINK)
            cv.ring(cx, cy, r, 1, pal[4])
            L.add(cx, cy, 26, GHOST_PINK, 0.9 * (1 - (t - 1.0) / 0.2))

    run(S, lambda *a: None, draw, ground=gy)


def will_o_wisps(S):
    """Loop: Confuse Ray / spirit wisps - three soft will-o'-wisps (glowing orb, pale core, pink-violet rim) drift
    around the unit on slow wandering paths, each trailing a tapering curled tail of its own; drifting, not shooting."""
    pal = S.pal
    cx, fy = S.w / 2, S.ground
    cy = fy - 16

    def pos(ph, k):
        a = ph * TAU + k * TAU / 3
        return (cx + math.cos(a) * 17 + 3 * math.sin(ph * TAU * 2 + k),
                cy + math.sin(a) * 8 - 6 * math.sin(ph * TAU + k * 2))

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        for k in range(3):
            for j in range(16, 0, -1):
                x, y = pos(ph - j * 0.012, k)
                r = 2.4 * (1 - j / 16) + 0.4
                cv.disc(x, y - j * 0.3, r, pal[2] if j > 8 else pal[3])
            x, y = pos(ph, k)
            cv.disc(x, y, 3.6, GHOST_PINK)
            cv.disc(x, y, 2.4, pal[4])
            cv.px(x - 1, y - 1, pal[5])
            L.add(x, y, 10, pal[3], 0.45)

    run(S, lambda *a: None, draw, loop=True, ground=fy, warm=0)


# ------------------------------------------------------------------ dark (emissive, black energy), designed per move
def night_slash(S):
    """Night Slash / Feint Attack: the instant cut - a dark band flicks across the target for one frame, then three
    claw gashes rake across it: black slashes with a pale lilac rim on the outside, staying as torn black marks
    that shrink away; a few dark shreds fly off."""
    pal = S.pal
    cx, cy = S.anchor
    rr = random.Random(103)
    shreds = [dict(vx=rr.uniform(20, 90), vy=rr.uniform(-80, 20)) for _ in range(8)]

    def draw(cv, L, sim, i, t, rng):
        if i == 1:
            for y in range(int(cy - 3), int(cy + 4)):
                for x in range(0, S.w):
                    if (x + y) % 2 == 0:
                        cv.px(x, y, pal[0])
        for k in range(3):
            t0 = 2 + k
            d = i - t0
            if d < 0:
                continue
            g = clamp((d + 1) / 2)
            shrink = clamp((d - 6) / 10)
            if shrink >= 1:
                continue
            ox = (k - 1) * 8
            a0, a1 = -2.3, -2.3 + 1.7 * g
            a0, a1 = -1.65, -1.65 + 1.45 * g
            crescent(cv, cx + ox - 20, cy + 34, 40 - shrink * 4, a0, a1, 5 * (1 - shrink) + 0.8,
                     [pal[5], pal[2], pal[0]], squash=1.0)
            if d < 3:
                L.add(cx + ox, cy, 10, pal[4], 0.3)
        for k, s in enumerate(shreds):
            tt = (i - 3) / 30
            if 0 < tt < 0.5:
                x = cx + s["vx"] * tt
                y = cy + s["vy"] * tt + 150 * tt * tt
                cv.px(x, y, pal[0]); cv.px(x + 1, y, pal[3]); cv.px(x, y + 1, pal[0])

    run(S, lambda *a: None, draw, ground=S.ground)


def dark_pulse(S):
    """Dark Pulse: a black core swells, then rings of malice spread out: each ring is a thick black band with
    spikes along its outer edge and a pale lilac rim, uneven and pulsing, on the floor plane; dark wisps peel off
    upward. Rings by design (it is a pulse), but black with a light rim, never a bright ring."""
    pal = S.pal
    cx, gy = S.anchor[0], S.ground - 4

    def draw(cv, L, sim, i, t, rng):
        core = clamp(t / 0.15) * (1 - clamp((t - 0.5) / 0.3))
        if core > 0:
            cv.ellipse(cx, gy - 6, 8 * core, 8 * core, pal[0])
            for k in range(int(40 * core)):
                a = k / (40 * core) * TAU
                cv.px(cx + math.cos(a) * 8 * core, gy - 6 + math.sin(a) * 8 * core, pal[4])
        for b in range(3):
            u = (t - 0.12 - b * 0.18) / 0.6
            if not 0 <= u < 1:
                continue
            r = 8 + u * 54
            th = 3.5 * (1 - u) + 1
            steps = int(r * 7)
            for k in range(steps):
                a = k / steps * TAU
                spike = 3 * max(0.0, math.sin(a * 11 + b * 2 + t * 6)) ** 3
                for j in range(int(th)):
                    rr_ = r - j
                    cv.px(cx + math.cos(a) * rr_, gy + math.sin(a) * rr_ * 0.32, pal[2] if (j + k) % 2 else pal[1])
                ro = r + 1 + spike * (1 - u)
                cv.px(cx + math.cos(a) * ro, gy + math.sin(a) * ro * 0.32, pal[5] if u < 0.4 else pal[4] if u < 0.7 else pal[3])
            L.add(cx, gy, r * 0.6, pal[3], 0.2 * (1 - u))
        for k in range(5):
            u = (t * 1.3 + k / 5) % 1
            if t < 0.9:
                x = cx + (k - 2) * 12 + math.sin(u * 8 + k) * 3
                for j in range(6):
                    cv.px(x + math.sin((u + j * 0.05) * 9) * 1.5, gy - 8 - u * 30 - j, pal[2] if j < 3 else pal[1])

    run(S, lambda *a: None, draw, ground=S.ground)


def malice_orb(S):
    """Loop: a Dark Pulse orb - a spiky black ball (jagged spikes that grow and retract around it), pale lilac
    rim on the spikes, a tight pulsing ring around it, dark shreds trailing; menacing rather than ghostly (the
    ghost shadow ball is round, swirling, pink-rimmed)."""
    pal = S.pal
    hx, hy = S.anchor

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        x, y = hx - 4, hy
        for k in range(6):
            u = (ph * 2 + k / 6) % 1
            sx = x - 10 - u * 36
            sy = y + math.sin(u * 9 + k) * 5
            cv.px(sx, sy, pal[0]); cv.px(sx + 1, sy, pal[2]); cv.px(sx, sy + 1, pal[0])
        n = 9
        pts = []
        for k in range(n * 2):
            a = k * math.pi / n + ph * TAU * 0.5
            if k % 2 == 0:
                rad = 7 + 4 * (0.5 + 0.5 * math.sin(ph * TAU * 2 + k))
            else:
                rad = 5.5
            pts.append((x + math.cos(a) * rad, y + math.sin(a) * rad))
        inn = set()
        for dy in range(-13, 14):
            for dx in range(-13, 14):
                if _inpoly(x + dx + 0.5, y + dy + 0.5, pts):
                    inn.add((dx, dy))
        for (dx, dy) in inn:
            edge = any((dx + a, dy + b) not in inn for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            dd = math.hypot(dx, dy)
            cv.px(x + dx, y + dy, (pal[5] if (dx + dy) < 2 else pal[4]) if edge else pal[0] if dd < 3 else pal[1] if dd < 5 else pal[2])
        r = 13 + 2 * math.sin(ph * TAU * 2)
        for k in range(int(r * 5)):
            if k % 3:
                a = k / (r * 5) * TAU
                cv.px(x + math.cos(a) * r, y + math.sin(a) * r, pal[3])
        L.add(x, y, 12, pal[3], 0.25)

    run(S, lambda *a: None, draw, loop=True, warm=0)


# ------------------------------------------------------------------ dragon (emissive), designed per move
DRAGON_SPARK = (255, 236, 120)


def dragon_flame(cv, x, y, r, pal, seed, t):
    rag_blob(cv, x, y, r, pal[2], seed, t=t, rough=0.35, edge=pal[1])
    rag_blob(cv, x + 0.5, y - 0.5, r * 0.6, pal[3], seed + 1, t=t, rough=0.3)
    rag_blob(cv, x + 1, y - 1, r * 0.3, pal[5], seed + 2, t=t, rough=0.3)


def dragon_rage(S):
    """Dragon Rage: a straight 'string of pearls' - round blue-purple flame puffs travelling in a line, each
    flickering with a pale core, the head puff biggest and brightest, yellow sparks spitting off; at the target a
    blue-violet flame burst flickers. Not a laser."""
    pal = S.pal
    ox, oy = S.anchor
    tx = S.w - 10
    t_on, t_off = 0.12, 0.95
    rr = random.Random(107)
    sparks = [(rr.uniform(0, 1), rr.uniform(-1, 1)) for _ in range(12)]

    def draw(cv, L, sim, i, t, rng):
        h = ox + (tx - ox) * clamp((t - t_on) / 0.3)
        tail = ox + (tx - ox) * clamp((t - t_off) / 0.2)
        k = 0
        x = h
        while x > tail + 2 and x > ox:
            big = k == 0
            r = 6.5 if big else 3.6 + 1.2 * math.sin(k * 1.7 + t * 20)
            dragon_flame(cv, x, oy + math.sin(k * 1.3 + t * 10) * 1.2, r, pal, 210 + k, t)
            if k % 2 == 0:
                L.add(x, oy, 10 if big else 6, pal[3], 0.4 if big else 0.2)
            x -= 9
            k += 1
        for (u, s) in sparks:
            if h > tail + 4:
                f = (u + t * 3) % 1
                sx = tail + (h - tail) * f
                sy = oy + s * (4 + f * 6) - f * 3
                cv.px(sx, sy, DRAGON_SPARK)
        tl = t - (t_on + 0.3)
        if 0 < tl < 0.85:
            g = math.sin(math.pi * min(1, tl / 0.85))
            for j in range(6):
                a = -math.pi / 2 + (j - 2.5) * 0.5
                tongue_dir(cv, tx, oy + 4, a, 3.2, (10 + 5 * noise2(t * 8, j, 3)) * g, [pal[1], pal[2], pal[4]],
                           220 + j, t)
            L.add(tx, oy, 18, pal[3], 0.6 * g)

    run(S, lambda *a: None, draw, ground=S.ground)


def draconic_burst(S):
    """Dragon Rage hit / Outrage: a blue-violet flame burst on the target, and draconic energy shards - angular
    scale-like crystals in blue and pale cyan - fly out on spinning arcs, yellow sparks spit; flickers down."""
    pal = S.pal
    cx, cy = S.anchor
    rr = random.Random(109)
    shards = [dict(a=rr.uniform(0, TAU), sp=rr.uniform(60, 130), s=rr.uniform(6, 11), w=rr.uniform(-8, 8))
              for _ in range(9)]

    def draw(cv, L, sim, i, t, rng):
        g = out_cubic(clamp(t / 0.15)) * (1 - clamp((t - 0.45) / 0.6))
        if g > 0.02:
            for j in range(7):
                a = -math.pi / 2 + (j - 3) * 0.55
                tongue_dir(cv, cx, cy + 6, a, 4 * g + 1, (16 + 6 * noise2(t * 8, j, 9)) * g,
                           [pal[1], pal[2], pal[4]], 230 + j, t, bend=3)
            dragon_flame(cv, cx, cy + 2, 7 * g + 1, pal, 240, t)
            L.add(cx, cy, 28 * g + 6, pal[3], 0.7 * g)
        for k, s in enumerate(shards):
            tt = t - 0.05
            if 0 < tt < 0.8:
                d = s["sp"] * (1 - math.exp(-3 * tt)) / 3
                x = cx + math.cos(s["a"]) * d
                y = cy + math.sin(s["a"]) * d * 0.8 + 40 * tt * tt
                crystal(cv, x, y, s["a"] + s["w"] * tt, s["s"] * (1 - tt * 0.5), s["s"] * 0.45, pal)
        for k in range(10):
            tt = t - 0.03 * k
            if 0 < tt < 0.5:
                a = k * 2.4
                d = 10 + tt * 90
                cv.px(cx + math.cos(a) * d, cy + math.sin(a) * d * 0.8, DRAGON_SPARK)

    run(S, lambda *a: None, draw, ground=S.ground)


def dragon_dance(S):
    """Loop: Dragon Dance - a serpentine ribbon of blue-violet energy coils up around the unit like a dragon's
    body (thick in the middle, tapering head and tail, back loops dim), small flame tufts along its spine, yellow
    sparks shed; a swirling coil, not rising particles."""
    pal = S.pal
    cx, fy = S.w / 2, S.ground

    def pt(u, ph):
        a = (u * 2.2 + ph) * TAU
        return cx + math.cos(a) * 16, fy - 2 - u * 52 + math.sin(a) * 4, math.sin(a)

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        for front in (False, True):
            for k in range(160):
                u = k / 160
                x, y, z = pt(u, ph)
                if (z > 0) != front:
                    continue
                w = 3.5 * math.sin(math.pi * u) ** 0.7 + 0.5
                for j in range(-int(w), int(w) + 1):
                    d = abs(j) / max(w, 0.5)
                    if front:
                        c = pal[1] if d > 0.7 else pal[3] if d > 0.3 else pal[4]
                    else:
                        c = pal[0] if d > 0.6 else pal[1]
                    cv.px(x, y + j, c)
            if front:
                for k in range(7):
                    u = 0.15 + k * 0.11
                    x, y, z = pt(u, ph)
                    if z > 0:
                        tongue_dir(cv, x, y - 3, -math.pi / 2, 1.6, 4 + 2 * noise2(ph * 6, k, 2),
                                   [pal[1], pal[2], pal[4]], 250 + k, t)
                hx, hy, hz = pt(1.0, ph)
                cv.disc(hx, hy, 2.5, pal[4]); cv.px(hx + 1, hy - 1, DRAGON_SPARK)
        for k in range(4):
            u = (ph * 2 + k / 4) % 1
            x, y, z = pt(u, ph)
            cv.px(x + 4, y - 4 - u * 6, DRAGON_SPARK)
        L.add(cx, fy - 26, 26, pal[3], 0.35)

    run(S, lambda *a: None, draw, loop=True, ground=fy, warm=0)


# ------------------------------------------------------------------ steel, designed per move
SPARK_OR = [(160, 60, 20), (240, 130, 40), (255, 200, 90), (255, 244, 200)]


def flash_cannon(S):
    """Flash Cannon: light gathers at the mouth (silver orb, glints converging), then a wide hard-edged silver
    beam releases at once - steel-grey edge, white body, a brighter specular stripe along its top third - with
    small metal flakes shed along it and a white star flash at the target."""
    pal = S.pal
    ox, oy = S.anchor
    tx = S.w - 6
    t_on, t_off = 0.35, 1.05
    rr = random.Random(113)
    flakes = [(rr.uniform(0, 1), rr.uniform(-1, 1), rr.uniform(0, TAU)) for _ in range(10)]

    def draw(cv, L, sim, i, t, rng):
        if t < t_on + 0.05:
            g = clamp(t / t_on)
            cv.disc(ox, oy, 2 + g * 5, pal[3])
            cv.disc(ox, oy, 1 + g * 3, pal[5])
            for k in range(6):
                a = k / 6 * TAU + 0.3
                r = 22 * (1 - g) + 6
                cv.line(ox + math.cos(a) * r, oy + math.sin(a) * r, ox + math.cos(a) * (r + 4),
                        oy + math.sin(a) * (r + 4), pal[5])
            L.add(ox, oy, 8 + g * 10, pal[4], 0.6 * g)
        if t_on <= t < t_off:
            h = ox + (tx - ox) * clamp((t - t_on) / 0.08)
            thin = 1 - clamp((t - (t_off - 0.2)) / 0.2)
            hw = 6.5 * thin + 0.5
            for x in range(int(ox), int(h) + 1):
                for y in range(int(oy - hw), int(oy + hw) + 1):
                    d = (y - oy) / max(hw, 0.5)
                    if abs(d) > 0.82:
                        c = pal[2]
                    elif -0.6 < d < -0.25:
                        c = pal[5]
                    else:
                        c = pal[4] if abs(d) < 0.6 else pal[3]
                    cv.px(x, y, c)
                if x % 12 == 0:
                    L.add(x, oy, 9, pal[4], 0.3 * thin)
            for (u, s, a) in flakes:
                f = (u + (t - t_on) * 2) % 1
                fx = ox + (h - ox) * f
                fy = oy + s * (hw + 3 + f * 8)
                crystal(cv, fx, fy, a + t * 8, 5, 2.5, pal)
            if h >= tx - 1:
                pow_star(cv, tx - 2, oy, 10 * thin + 3, [None, pal[3], None, None, pal[5]], n=6)
                L.add(tx, oy, 22, pal[5], 0.8 * thin)

    run(S, lambda *a: None, draw, ground=S.ground)


def metal_clang(S):
    """Metal Claw / Iron Tail hit: a silver strike arc clangs against the target, a white star flash for two
    frames, and a shower of orange sparks off metal flies out and arcs down, bouncing on the floor; a ring of
    'clang' lines. Only the flash and sparks give light."""
    pal = S.pal
    cx, cy = S.anchor
    gy = S.ground
    rr = random.Random(127)
    sparks = [dict(vx=rr.uniform(-140, 140), vy=rr.uniform(-170, -20), L=rr.uniform(3, 6)) for _ in range(24)]
    G = 520

    def draw(cv, L, sim, i, t, rng):
        if i < 6:
            crescent(cv, cx - 10, cy + 6, 22, -1.9, -0.2, 3.5 * (1 - i / 6) + 1, [pal[2], pal[4], pal[5]])
        if i < 3:
            pow_star(cv, cx, cy, 13 - i * 2, [None, pal[3], None, None, pal[5]], n=7)
            L.add(cx, cy, 22, pal[5], 0.9)
        if 2 <= i < 8:
            r = 14 + (i - 2) * 4
            for k in range(8):
                a = k / 8 * TAU + 0.2
                cv.line(cx + math.cos(a) * r, cy + math.sin(a) * r, cx + math.cos(a) * (r + 4),
                        cy + math.sin(a) * (r + 4), pal[4])
        for k, s in enumerate(sparks):
            tt = t - 0.02
            if tt <= 0 or tt > 1.0:
                continue
            x = cx + s["vx"] * tt
            y = cy + s["vy"] * tt + 0.5 * G * tt * tt
            vy = s["vy"] + G * tt
            if y > gy - 1:
                tb = tt - 0.08
                y = gy - 1 - max(0.0, 20 * (tt - tb) - 100 * (tt - tb) ** 2)
            heat = 1 - tt
            col = SPARK_OR[3] if heat > 0.8 else SPARK_OR[2] if heat > 0.5 else SPARK_OR[1] if heat > 0.25 else SPARK_OR[0]
            sp = math.hypot(s["vx"], vy) or 1
            for d in range(int(s["L"] * heat) + 1):
                cv.px(x - s["vx"] / sp * d, y - vy / sp * d, col)
            if heat > 0.5 and k % 3 == 0:
                L.add(x, y, 3, SPARK_OR[2], 0.3, glint=True)

    run(S, lambda *a: None, draw, ground=gy)


def iron_spikes(S):
    """Iron Head / metal spikes: thin polished steel blades shoot up through the floor in sequence - narrow,
    mirror-shaded (dark edge, mid, white specular stripe), a glint runs up each blade - hold, then retract
    cleanly back into the floor (metal does not crumble, unlike Stone Edge)."""
    pal = S.pal
    cx, gy = S.anchor[0], S.ground
    rr = random.Random(131)
    blades = [dict(x=cx + (k - 3) * 19 + rr.uniform(-3, 3), h=rr.uniform(40, 64), w=rr.uniform(4, 6),
                   t0=abs(k - 3) * 0.05) for k in range(7)]

    def draw(cv, L, sim, i, t, rng):
        for k, b in enumerate(blades):
            tt = t - b["t0"]
            if tt <= 0:
                continue
            up = out_cubic(clamp(tt / 0.08))
            down = clamp((t - 1.05) / 0.15)
            h = b["h"] * up * (1 - down)
            if h < 1:
                continue
            w = b["w"]
            for y in range(int(gy - h), gy):
                f = (gy - y) / max(h, 1)
                hw = w * (1 - f) + 0.5
                for x in range(int(b["x"] - hw), int(b["x"] + hw) + 1):
                    d = (x - b["x"]) / max(hw, 0.5)
                    c = pal[1] if abs(d) > 0.8 else pal[5] if -0.45 < d < -0.1 else pal[3] if d < 0.3 else pal[2]
                    cv.px(x, y, c)
            gl = ((t - b["t0"]) * 2.5) % 1.4
            if gl < 1 and down == 0:
                gyl = gy - h * gl
                snowflake(cv, b["x"] - 1, gyl, 2, pal[5], pal[4])
                L.add(b["x"], gyl, 4, pal[5], 0.6, glint=True)
            if tt < 0.2:
                for s in (-1, 1):
                    cv.px(b["x"] + s * (w + 2 + tt * 30), gy - 2 - tt * 10, SPARK_OR[2])

    run(S, lambda *a: None, draw, ground=gy)


def iron_tail(S):
    """Iron Tail: one heavy silver arc swings down onto the target - a thick crescent shaded like polished metal
    (dark edge, steel body, white specular line) with motion smears behind it - lands with a clang star and
    orange sparks."""
    pal = S.pal
    cx, cy = S.anchor
    HIT = 4

    def draw(cv, L, sim, i, t, rng):
        if i <= HIT + 2:
            u = clamp((i + 1) / (HIT + 1))
            for k in range(3):
                uu = max(0.05, u - k * 0.18)
                crescent(cv, cx - 18, cy + 30, 44, -1.7, -1.7 + 1.5 * uu, (6 - k * 2) * (1 if i <= HIT else 0.5),
                         [pal[1], pal[3] if k == 0 else pal[2], pal[5] if k == 0 else pal[3]])
        if HIT <= i < HIT + 8:
            d = i - HIT
            pow_star(cv, cx + 4, cy + 4, 11 - d, [None, pal[3], None, None, pal[5]], n=6)
            if d < 2:
                L.add(cx, cy, 16, pal[5], 0.8)
            for k in range(6):
                a = -0.5 - k * 0.45
                r = 8 + d * 6
                cv.px(cx + 4 + math.cos(a) * r, cy + 4 + math.sin(a) * r + d * d * 0.6, SPARK_OR[2 if d < 4 else 1])

    run(S, lambda *a: None, draw, ground=S.ground)


# ------------------------------------------------------------------ fairy (emissive), designed per move
def heart(cv, x, y, s, fill, edge):
    R = int(s * 1.4) + 1
    pts = set()
    for dy in range(-R, R + 1):
        for dx in range(-R, R + 1):
            u, v = dx / s, -(dy / s) + 0.25
            if (u * u + v * v - 1) ** 3 - u * u * v ** 3 <= 0:
                pts.add((dx, dy))
    for (dx, dy) in pts:
        e = any((dx + a, dy + b) not in pts for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        cv.px(x + dx, y + dy, edge if e else fill)
    if s >= 3:
        cv.px(x - s * 0.45, y - s * 0.3, (255, 255, 255))


def star4(cv, x, y, s, c, c2):
    for k in range(-s, s + 1):
        cv.px(x + k, y, c if abs(k) < s else c2)
        cv.px(x, y + k, c if abs(k) < s else c2)


def moonblast(S):
    """Loop: Moonblast - a pale pink full-moon disc (soft craters, lit rim upper left, shaded edge lower right)
    with a soft halo, sparkles orbiting it and a twinkling sparkle trail. A moon, not a comet."""
    pal = S.pal
    hx, hy = S.anchor
    R = 8

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        x, y = hx - 4, hy
        for k in range(6):
            u = (ph * 2 + k / 6) % 1
            sx, sy = x - 12 - u * 40, y + math.sin(u * 8 + k) * 5
            if (i + k) % 3:
                star4(cv, sx, sy, 2 if u < 0.5 else 1, pal[4], pal[3])
        for dy in range(-R, R + 1):
            for dx in range(-R, R + 1):
                d = math.hypot(dx, dy)
                if d > R:
                    continue
                lit = (-dx - dy) / (R * 1.4)
                c = pal[5] if lit > 0.35 else pal[4] if lit > -0.3 else pal[3]
                if d > R - 1:
                    c = pal[3] if lit < 0 else pal[4]
                cv.px(x + dx, y + dy, c)
        for (cx_, cy_, r) in ((2, 1, 2), (-2, 3, 1.3), (3, -3, 1.2)):
            cv.disc(x + cx_, y + cy_, r, pal[3])
        for k in range(3):
            a = ph * TAU * 2 + k * TAU / 3
            star4(cv, x + math.cos(a) * 13, y + math.sin(a) * 8, 2, (255, 255, 255), pal[4])
        L.add(x, y, 13, pal[3], 0.22)

    run(S, lambda *a: None, draw, loop=True, warm=0)


def charm_burst(S):
    """Disarming Voice / Charm hit: a soft pink ring pops on the target, hearts of several sizes burst out and
    float up wobbling, 4-point sparkles twinkle on and off, small stars spin; gentle, no hard radial lines."""
    pal = S.pal
    cx, cy = S.anchor
    rr = random.Random(137)
    hearts = [dict(a=rr.uniform(-math.pi, 0), sp=rr.uniform(30, 70), s=rr.uniform(2.5, 4.5), w=rr.uniform(0, TAU))
              for _ in range(9)]
    sparks = [(rr.uniform(-34, 34), rr.uniform(-34, 14), rr.uniform(0, 1)) for _ in range(12)]

    def draw(cv, L, sim, i, t, rng):
        if t < 0.35:
            u = t / 0.35
            for k in range(int(40 + u * 60)):
                a = k / (40 + u * 60) * TAU
                r = 6 + u * 26
                cv.px(cx + math.cos(a) * r, cy + math.sin(a) * r * 0.8, pal[4] if u < 0.5 else pal[3])
            L.add(cx, cy, 20, pal[3], 0.6 * (1 - u))
        for k, h in enumerate(hearts):
            tt = t - 0.04
            if 0 < tt < 1.25:
                d = h["sp"] * (1 - math.exp(-4 * tt)) / 4
                x = cx + math.cos(h["a"]) * d * 1.5 + math.sin(tt * 6 + h["w"]) * 2
                y = cy + math.sin(h["a"]) * d - tt * 14
                s = h["s"] * (1 - clamp((tt - 0.9) / 0.35))
                if s > 1:
                    heart(cv, x, y, s, pal[3], pal[1])
        for (dx, dy, u) in sparks:
            ph = (t * 2.5 + u) % 1
            if t < 1.3 and ph < 0.4:
                star4(cv, cx + dx, cy + dy, 2 if ph < 0.2 else 1, (255, 255, 255), pal[4])
                L.add(cx + dx, cy + dy, 4, pal[4], 0.3)

    run(S, lambda *a: None, draw, ground=S.ground)


def moonlight(S):
    """Loop: Moonlight / Fairy Wind field - a small crescent moon hangs above the unit and a soft pale column of
    moonlight falls from it (dithered, see-through), sparkles circle the feet on a ring and twinkle, a few motes
    drift down through the beam."""
    pal = S.pal
    cx, fy = S.w / 2, S.ground
    my = fy - 50

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        for y in range(int(my + 5), fy):
            f = (y - my) / (fy - my)
            hw = 5 + f * 9
            for x in range(int(cx - hw), int(cx + hw) + 1):
                if (x + y + i // 4) % 3 == 0 and abs(x - cx) < hw - (1 if (x + y) % 2 else 0):
                    cv.px(x, y, pal[2] if abs(x - cx) > hw * 0.6 else pal[3])
        for dy in range(-6, 7):
            for dx in range(-6, 7):
                if dx * dx + dy * dy <= 36 and (dx - 2.5) ** 2 + (dy + 1.5) ** 2 > 20:
                    cv.px(cx + dx, my + dy, pal[5] if dx + dy < -2 else pal[4])
        L.add(cx, my, 12, pal[4], 0.5)
        L.add(cx, fy - 15, 18, pal[3], 0.25)
        for k in range(8):
            a = ph * TAU + k / 8 * TAU
            x, y = cx + math.cos(a) * 17, fy - 2 + math.sin(a) * 4
            if (i + k) % 4:
                star4(cv, x, y, 2 if math.sin(a) > 0 else 1, (255, 255, 255) if math.sin(a) > 0 else pal[4], pal[3])
        for k in range(4):
            u = (ph + k / 4) % 1
            cv.px(cx - 6 + k * 4, my + 8 + u * 40, pal[5])

    run(S, lambda *a: None, draw, loop=True, ground=fy, warm=0)


# ------------------------------------------------------------------ normal + status, designed per move
STAR_Y = [None, (176, 120, 30), None, None, (255, 226, 110)]


def swift_stars(S):
    """Loop: Swift - five five-pointed stars (yellow fill, white core, dark gold outline) in a loose spread
    formation, each spinning at its own rate, a tiny sparkle trail behind each."""
    pal = S.pal
    hx, hy = S.anchor
    stars = [(hx - 4, hy, 7, 0.0), (hx - 22, hy - 10, 5.5, 0.4), (hx - 24, hy + 10, 5.5, 0.7), (hx - 42, hy - 3, 4.5, 0.2),
             (hx - 56, hy + 7, 4, 0.55)]

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        for k, (x, y, r, u) in enumerate(stars):
            yy = y + math.sin((ph + u) * TAU) * 1.5
            for d in range(1, 4):
                if (i + d + k) % 2:
                    cv.px(x - r - d * 3, yy + (d % 2), (255, 236, 160) if d == 1 else (200, 170, 90))
            pow_star(cv, x, yy, r, STAR_Y, rot=(ph * (2 + k % 2) + u) * TAU / 5 * (1 if k % 2 else -1), n=5)
            L.add(x, yy, r + 4, (255, 226, 110), 0.3)

    run(S, lambda *a: None, draw, loop=True, warm=0)


def tackle_spark(S):
    """Hit spark (Tackle / Scratch / Pound contact): a small white-yellow contact star with 5 points for 2 frames,
    the star shrinks while 4 short flick lines shoot out, then a few specks; 0.4 s, neutral colours."""
    pal = S.pal
    cx, cy = S.anchor

    def draw(cv, L, sim, i, t, rng):
        if i < 6:
            pow_star(cv, cx, cy, 8 - i * 1.1, STAR_Y, rot=0.3 + i * 0.1, n=5)
        if i < 2:
            L.add(cx, cy, 14, (255, 240, 200), 0.8)
        if 1 <= i < 7:
            d = i - 1
            for k in range(4):
                a = 0.4 + k * TAU / 4
                r = 7 + d * 3
                cv.line(cx + math.cos(a) * r, cy + math.sin(a) * r, cx + math.cos(a) * (r + 3),
                        cy + math.sin(a) * (r + 3), (255, 236, 160) if d < 3 else (200, 170, 90))

    run(S, lambda *a: None, draw, ground=S.ground)


def body_slam(S):
    """Body Slam / Take Down impact: heavy downward speed lines fall onto the target, then a big white comic
    impact star (10 points) squashed wide, a floor shock with dust billows thrown out both sides, impact lines,
    the star shrinks while dust rolls and settles. Physical weight, no glow."""
    pal = S.pal
    cx, cy = S.anchor
    gy = S.ground
    HIT = 4

    def draw(cv, L, sim, i, t, rng):
        if i < HIT:
            for k in range(7):
                x = cx - 18 + k * 6
                y0 = cy - 40 + i * 8 + (k * 5) % 9
                cv.line(x, y0, x, y0 + 10, (200, 200, 210) if k % 2 else (140, 140, 156))
        d = i - HIT
        if 0 <= d < 10:
            r = 22 if d < 2 else 20 - (d - 2) * 2
            star = [None, (130, 110, 90), None, None, (255, 236, 170)]
            pts_sc = 1.0
            pow_star(cv, cx, cy + 4, r, star, rot=0.15, n=10)
            if d < 2:
                L.add(cx, cy, 8, (255, 255, 255), 0.7, glint=True)
            for k in range(6):
                a = -math.pi + k * math.pi / 5
                r0 = r + 3 + d * 2
                cv.line(cx + math.cos(a) * r0, cy + 4 + math.sin(a) * r0 * 0.7, cx + math.cos(a) * (r0 + 6),
                        cy + 4 + math.sin(a) * (r0 + 6) * 0.7, (240, 236, 220))
        if d >= 0 and d < 30:
            u = d / 30
            puffs = []
            for s in (-1, 1):
                for m in range(3):
                    puffs.append((cx + s * (10 + m * 7 + u * 30), gy - 3 - m, (6 - m * 1.2) * math.sin(math.pi * min(1, u * 1.5 + 0.1)) + 0.3))
            billow(cv, puffs, [DUST[0], DUST[1], DUST[2], DUST[3]], i, ph=u)

    run(S, lambda *a: None, draw, ground=gy)


def poison_bubbles(S):
    """Loop: poisoned - purple bubbles rise off the unit and pop (ring + highlight, broken ring when they pop),
    a sickly purple drip at the feet; one colour per status (movref)."""
    pal = S.pal
    cx, fy = S.w / 2, S.ground
    rr = random.Random(139)
    bubs = [(rr.uniform(-12, 12), rr.uniform(0, 1), rr.uniform(1.5, 3.2)) for _ in range(7)]

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        for (dx, u, r) in bubs:
            f = (ph + u) % 1
            x = cx + dx + math.sin(f * 7 + dx) * 2
            y = fy - 8 - f * 34
            if f < 0.82:
                cv.ring(x, y, r, 1, pal[3])
                cv.px(x - r * 0.4, y - r * 0.4, pal[5])
            elif f < 0.92:
                for a in range(6):
                    if a % 2 == 0:
                        aa = a / 6 * TAU
                        cv.px(x + math.cos(aa) * (r + 1.5), y + math.sin(aa) * (r + 1.5), pal[4])
        for k in range(3):
            f = (ph * 2 + k / 3) % 1
            x = cx - 8 + k * 8
            cv.px(x, fy - 12 + f * 10, pal[2]); cv.px(x, fy - 11 + f * 10, pal[3])
        cv.ellipse(cx, fy - 1, 9, 1.5, pal[1])

    run(S, lambda *a: None, draw, loop=True, ground=fy, warm=0)


def frozen_coat(S):
    """Loop: frozen - the unit is coated in pale ice: a faceted translucent ice shell over the lower body (lit
    facets, dithered see-through, white edges), icicles on its rim, a glint sweeping across it, frost specks."""
    pal = S.pal
    cx, fy = S.w / 2, S.ground
    top = fy - 22
    poly = [(cx - 14, fy), (cx - 15, top + 8), (cx - 8, top), (cx + 6, top - 2), (cx + 14, top + 6), (cx + 15, fy)]

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        for y in range(int(top - 3), fy):
            for x in range(int(cx - 16), int(cx + 17)):
                if not _inpoly(x + 0.5, y + 0.5, poly):
                    continue
                f = (x - cx) + (y - top) * 0.5
                c = pal[4] if f < -6 else pal[3] if f < 8 else pal[2]
                if (x + y) % 2 == 0:
                    cv.px(x, y, c)
        for a, b in zip(poly, poly[1:]):
            cv.line(a[0], a[1], b[0], b[1], pal[5] if a[1] < fy - 6 and b[1] < fy - 6 else pal[3])
        cv.line(cx - 8, top, cx - 3, fy - 2, pal[5])
        cv.line(cx + 6, top - 2, cx + 4, fy - 4, pal[4])
        g = (ph * 1.5) % 1.5
        if g < 1:
            gx = cx - 14 + g * 28
            for k in range(5):
                cv.px(gx + k * 0.5, top + 2 + k * 4, (255, 255, 255))
            L.add(gx, top + 8, 5, pal[5], 0.6, glint=True)
        for k in range(4):
            f = (ph + k / 4) % 1
            cv.px(cx - 12 + k * 8, top - 4 - f * 10, pal[5] if f < 0.5 else pal[3])

    run(S, lambda *a: None, draw, loop=True, ground=fy, warm=0)


# ------------------------------------------------------------------ rush (caster-attached contact moves), art pass 5
RUSH = dict(windupFrames=4, dashFrames=6, contactFrame=9, dashPx=120, returnFrames=8)
# Flame Wheel holds the burning wheel face-on for a beat before it rolls (movref/fire.md: ~0.5 s ring, ~0.25 s dash)
FLAME_RUSH = dict(windupFrames=10, dashFrames=6, contactFrame=15, dashPx=120, returnFrames=8)


def rush_u(i, R=RUSH):
    """How far along the dash the caster is at frame i (0 = start, 1 = touching the target). The engine moves the
    caster by dashPx * rush_u; the sheet is drawn in the caster's own frame."""
    w, d = R["windupFrames"], R["dashFrames"]
    if i < w:
        return 0.0
    if i >= w + d - 1:
        return 1.0
    return ((i - w + 1) / d) ** 1.5


def _shell(cv, x, y, rx, ry, cols, i, front_col):
    """Translucent shell around the body (dithered), with a bright rim on the leading (right) side."""
    for dy in range(-int(ry) - 1, int(ry) + 2):
        for dx in range(-int(rx) - 1, int(rx) + 2):
            d = (dx / rx) ** 2 + (dy / ry) ** 2
            if d > 1:
                continue
            if d > 0.72:
                c = front_col if dx > rx * 0.3 else cols[1] if dy < 0 else cols[0]
                cv.px(x + dx, y + dy, c)
            elif (dx + dy + i) % 3 == 0:
                cv.px(x + dx, y + dy, cols[1] if dy < 0 else cols[0])


def aqua_jet(S):
    """Aqua Jet (rush, caster-attached): water ribbons spiral up around the body (4-frame wind-up), the caster is
    wrapped in a see-through water shell with a white foam front and shoots forward, a tapering water stream and
    droplets stream behind it with speed lines; on contact a white-blue splash bursts on the target with a spray
    fan and a curved water arc, then the trail breaks into drops that fall. Material: no glow, glint at contact."""
    pal = S.pal
    ax, gy = S.anchor
    bx, by = ax, gy - 13
    R = RUSH
    C = R["contactFrame"]
    rr = random.Random(151)
    trail_drops = [(rr.uniform(0.05, 1.0), rr.uniform(-6, 6), rr.uniform(1, 2.2)) for _ in range(18)]
    spray = [dict(vx=rr.uniform(30, 150), vy=rr.uniform(-170, -30), r=rr.uniform(1, 2.6)) for _ in range(18)]
    G = 520

    def draw(cv, L, sim, i, t, rng):
        u = rush_u(i)
        off = R["dashPx"] * u                      # world distance travelled; world x = local x + off
        sx_local = bx - off                         # where the dash started, in local coords
        # trail: a tapering stream from the start point to the back of the body, while dashing
        if i >= R["windupFrames"]:
            brk = max(0.0, (i - C) / 10)           # after contact the stream breaks up and falls
            tail = sx_local + 4
            head = bx - 10
            for x in range(int(tail), int(head) + 1):
                f = (x - tail) / max(1.0, head - tail)
                seg = int(x) // 6
                if brk > 0 and ((seg * 7) % 11) / 11 < brk * 1.4 + 0.15:
                    continue
                th = 1 + f * 6 * (1 - brk)
                yc = by + 2 + math.sin(x * 0.25 - i * 1.3) * (1 - f) * 2 + brk * brk * (30 + (seg * 13) % 20)
                for yy in range(int(yc - th), int(yc + th) + 1):
                    d = (yy - yc) / max(th, 0.5)
                    c = pal[4] if d < -0.55 else pal[2] if d < 0.45 else pal[1]
                    if f < 0.3 and (x + yy) % 2:
                        continue
                    cv.px(x, yy, c)
                if (x + i) % 9 == 0 and brk == 0:
                    cv.px(x, yc - th - 1, pal[5])
            for (fu, oy, r) in trail_drops:
                wx = R["dashPx"] * fu                # world x along the path where the drop was shed
                if u < fu:
                    continue
                age = (i - (R["windupFrames"] + fu * R["dashFrames"])) / 30
                lx = sx_local + wx - age * 10
                ly = by + oy + 120 * age * age
                if ly < gy - 1:
                    cv.disc(lx, ly, r, pal[3]) if r > 1.6 else cv.px(lx, ly, pal[4])
                    if r > 1.6:
                        cv.px(lx - 0.5, ly - 0.5, pal[5])
        # speed lines while dashing
        if R["windupFrames"] <= i < C:
            for k in range(5):
                yy = by - 12 + k * 6
                x0 = bx - 18 - (k * 13 + i * 9) % 30
                cv.line(x0, yy, x0 - 10 - (k % 3) * 4, yy, (230, 244, 255) if k % 2 else pal[4])
        # wind-up: ribbons spiral up the body
        if i < R["windupFrames"] + 2:
            g = (i + 1) / R["windupFrames"]
            for k in range(3):
                a0 = i * 1.2 + k * TAU / 3
                crescent(cv, bx, by + 6 - k * 6 * min(1, g), 13, a0, a0 + 2.2, 2.2, [pal[1], pal[3], pal[5]],
                         squash=0.45)
            for k in range(4):
                cv.px(bx - 10 + k * 7, gy - 2 - g * 10 - (k % 2) * 4, pal[4])
        # the water shell around the body until contact
        if R["windupFrames"] - 1 <= i <= C:
            stretch = 1.0 + 0.35 * (R["windupFrames"] <= i < C)
            _shell(cv, bx - 2, by, 15 * stretch, 14 / stretch ** 0.5, [pal[1], pal[2]], i, pal[5])
            for k in range(3):
                a = i * 1.7 + k * 2.1
                cv.px(bx + math.cos(a) * 12, by + math.sin(a) * 10, pal[5])
        # contact: splash on the target, spray fan, curved arc
        if i >= C:
            d = i - C
            cx, cy = bx + 17, by
            if d < 3:
                rag_blob(cv, cx, cy, 9 - d * 2, (255, 255, 255), 160 + d, t=t, rough=0.4, edge=pal[4])
                L.add(cx, cy, 6, pal[5], 0.6, glint=True)
            if d < 7:
                crescent(cv, cx - 6, cy, 14 + d * 2.5, -1.2, 1.2, 3 - d * 0.35, [pal[1], pal[3], pal[5]], squash=1.0)
            tt = d / 30
            for k, s in enumerate(spray):
                x = cx + s["vx"] * tt
                y = cy + s["vy"] * tt + 0.5 * G * tt * tt
                if y > gy - 1:
                    if tt < 0.6:
                        cv.line(x - 1.5, gy - 1, x + 1.5, gy - 1, pal[3])
                    continue
                if s["r"] > 1.8:
                    cv.disc(x, y, s["r"], pal[3]); cv.px(x - 0.5, y - 0.5, pal[5])
                else:
                    cv.px(x, y, pal[4])

    run(S, lambda *a: None, draw, ground=gy)


def flame_wheel_rush(S):
    """Flame Wheel (rush, caster-attached): a wheel of flame tongues forms around the body (wind-up), the burning
    wheel spins fast as the caster charges forward leaving a trail of fire and embers, then bursts into a fan of
    flame on the target with embers falling. Emissive."""
    pal = S.pal
    ax, gy = S.anchor
    bx, by = ax, gy - 14
    R = FLAME_RUSH
    C = R["contactFrame"]
    rr = random.Random(157)
    embers = [dict(vx=rr.uniform(-20, 120), vy=rr.uniform(-150, -40)) for _ in range(16)]

    def draw(cv, L, sim, i, t, rng):
        u = rush_u(i, R)
        off = R["dashPx"] * u
        sx_local = bx - off
        if i >= R["windupFrames"]:
            fade = max(0.0, (i - C) / 8)
            for k in range(14):
                f = k / 14
                x = sx_local + (bx - 14 - sx_local) * f
                if x > bx - 12 or fade > f + 0.2:
                    continue
                h = (5 + 9 * f) * (1 - fade)
                tongue_dir(cv, x, by + 6, -math.pi / 2 - 0.5, 2.4 + f * 1.5, h, _fcols(pal), 300 + k, t, bend=2)
                if k % 3 == 0:
                    L.add(x, by + 2, 6 + f * 5, pal[3], 0.25 * (1 - fade))
        if i <= C:
            g = min(1.0, (i + 1) / R["windupFrames"])
            spin = i * (0.25 if i < R["windupFrames"] else 0.6)
            n = int(4 + 10 * g)
            for k in range(n):
                a = k / 14 * TAU + spin
                x, y = bx + math.cos(a) * 17 * 0.9, by + math.sin(a) * 17
                tongue_dir(cv, x, y, a - math.pi / 2, 3.2, 10 + 3 * noise2(t * 8, k, 3), _fcols(pal), 320 + k, t, bend=2)
            L.add(bx, by, 22, pal[3], 0.5 * g)
        if i >= C:
            d = i - C
            cx, cy = bx + 16, by
            gg = max(0.0, 1 - d / 9)
            if gg > 0:
                for j in range(6):
                    a = (j - 2.5) * 0.45
                    tongue_dir(cv, cx - 4, cy, a, 4 * gg + 1, (14 + 5 * noise2(t * 8, j, 9)) * gg, _fcols(pal),
                               340 + j, t, bend=3)
                rag_blob(cv, cx, cy, 6 * gg + 1, pal[4], 350, t=t, rough=0.3, edge=pal[3])
                if d < 2:
                    rag_blob(cv, cx, cy, 3, pal[5], 351, t=t)
                L.add(cx, cy, 18 * gg + 4, pal[4], 0.8 * gg)
            tt = d / 30
            for k, e in enumerate(embers):
                x = cx + e["vx"] * tt
                y = cy + e["vy"] * tt + 0.5 * 420 * tt * tt
                if y < gy - 1 and tt < 0.6:
                    cv.px(x, y, pal[5] if tt < 0.15 else pal[4] if tt < 0.35 else pal[2])

    run(S, lambda *a: None, draw, ground=gy)


def dark_pulse_beam(S):
    """Dark Pulse (art pass 5): the user releases rings of malice that travel FROM THE USER to the target - each
    ring a tall dark band (dithered black-plum) with a pale spiky rim on its leading edge, growing as it travels;
    a dark core pulses at the user; at the target the rings pile into a dark spiky burst."""
    pal = S.pal
    ox, oy = S.anchor
    tx = S.w - 10
    SP = 11.0                   # px per frame
    emits = [1, 4, 7, 10, 13]

    def draw(cv, L, sim, i, t, rng):
        if i < 16:
            r = 4 + 2 * math.sin(i * 0.9)
            cv.disc(ox + 2, oy, r + 1, pal[3])
            cv.disc(ox + 2, oy, r, pal[0])
        for e in emits:
            d = i - e
            if d < 0:
                continue
            x = ox + 6 + d * SP
            if x > tx:
                continue
            f = (x - ox) / (tx - ox)
            ry = 6 + f * 12
            rx = 2 + f * 2
            for j in range(int(ry * 7)):
                a = j / (ry * 7) * TAU
                px_, py_ = x + math.cos(a) * rx, oy + math.sin(a) * ry
                front = math.cos(a) > 0
                if front:
                    spike = 2.5 * max(0.0, math.sin(a * 6 + e)) ** 3
                    cv.px(px_ + 1 + spike, py_, pal[5] if f < 0.6 else pal[4])
                    cv.px(px_ + 2 + spike, py_, pal[4] if f < 0.6 else pal[3])
                    cv.px(px_, py_, pal[2])
                else:
                    if (j + i) % 2 == 0:
                        cv.px(px_, py_, pal[1])
                cv.px(px_ - 1, py_, pal[0] if front else pal[1])
            L.add(x, oy, ry * 0.6, pal[3], 0.12)
        first = (tx - ox - 6) / SP + emits[0]
        d = i - first
        if 0 <= d < 18:
            g = math.sin(math.pi * min(1.0, d / 18)) if d > 3 else d / 3
            n = 9
            pts = []
            for k in range(n * 2):
                a = k * math.pi / n + d * 0.1
                rad = (13 if k % 2 == 0 else 6) * (0.4 + g)
                pts.append((tx - 4 + math.cos(a) * rad, oy + math.sin(a) * rad))
            for yy in range(int(oy - 20), int(oy + 21)):
                for xx in range(int(tx - 26), int(tx + 18)):
                    if _inpoly(xx + 0.5013, yy + 0.4987, pts):
                        cv.px(xx, yy, pal[0] if math.hypot(xx - tx + 4, yy - oy) < 6 * (0.4 + g) else pal[1])
            for a_, b_ in zip(pts, pts[1:] + pts[:1]):
                cv.line(a_[0], a_[1], b_[0], b_[1], pal[4])
            L.add(tx - 4, oy, 14, pal[3], 0.35 * g)

    run(S, lambda *a: None, draw, ground=S.ground)


def thunder_wave_beam(S):
    """Thunder Wave (art pass 5, per movref/electric.md): a weak jolt is sent TO THE TARGET - thin gold hoops fly
    from the user with a small crackle skipping along, then jagged static rings close around the target's body and
    squeeze, with tiny arcs jumping to it: the target is held by electricity (paralysis)."""
    pal = S.pal
    ox, oy = S.anchor
    tx = S.w - 18
    ARR = 10

    def draw(cv, L, sim, i, t, rng):
        if i < ARR:
            # thin gold hoops fly from the user to the target, a crackle skipping between them
            for k in range(4):
                u = (i + 1 - k * 1.5) / ARR
                if not 0 < u <= 1:
                    continue
                hx = ox + (tx - ox) * u
                ry = 7 + 3 * u
                for j in range(int(ry * 6)):
                    a_ = j / (ry * 6) * TAU
                    cv.px(hx + math.cos(a_) * 2.2, oy + math.sin(a_) * ry, pal[5] if math.cos(a_) > 0 else pal[3])
                L.add(hx, oy, 6, pal[4], 0.25)
            lead = ox + (tx - ox) * min(1.0, (i + 1) / ARR)
            _arc(cv, rng, lead - 16, oy + rng.uniform(-3, 3), lead, oy, pal, segs=4, amp=3, width=1)
            if i < 3:
                cv.disc(ox + 2, oy, 3, pal[5])
                L.add(ox, oy, 10, pal[4], 0.5)
        else:
            d = i - ARR
            for ring in range(2):
                u = ((d / 20) + ring * 0.5) % 1
                rw = 15 - u * 7
                yc = oy - 9 + u * 18
                pts = []
                for k in range(41):
                    a = k / 40 * TAU
                    j = rng.uniform(-2.2, 2.2) if k % 2 else 0
                    pts.append((tx + math.cos(a) * (rw + j), yc + math.sin(a) * rw * 0.3 + j * 0.6, math.sin(a)))
                for a_, b_ in zip(pts, pts[1:]):
                    if rng.random() < 0.12:
                        continue
                    cv.line(a_[0], a_[1], b_[0], b_[1], (pal[5] if u < 0.5 else pal[4]) if a_[2] > 0 else pal[2])
                L.add(tx, yc, rw, pal[4], 0.2 * (1 - u))
            if d % 3 != 2:
                a = rng.uniform(0, TAU)
                _arc(cv, rng, tx + math.cos(a) * 7, oy + math.sin(a) * 16, tx + rng.uniform(-3, 3), oy + rng.uniform(-8, 8),
                     pal, segs=3, amp=2)
            if d < 3:
                cv.disc(tx, oy, 5 - d, pal[5])
                L.add(tx, oy, 14, pal[5], 0.6)

    run(S, lambda *a: None, draw, ground=S.ground)
