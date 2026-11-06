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
def life_ramp(pal, hot=True):
    """Colour over life: white-hot -> highlight -> light -> mid -> dark."""
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
        L.add(hx, hy, head * 4.5, pal[3], 0.45)
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
                L.add(x, y, 8, pal[4], 0.5)
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
            spawn(sim, el, pal, int(24 * power), cx, cy, ang=-math.pi / 2, spread=TAU * 0.9, speed=(50, 160),
                  rng=rng, scale=power * 1.15)
            spawn(sim, el, pal, int(8 * power), cx, cy, ang=-math.pi / 2, spread=TAU, speed=(25, 80), rng=rng,
                  secondary=True, scale=power)
            sim.emit(int(10 * power), cx, cy, ang=-math.pi / 2, spread=TAU, speed=(90, 220), life=(0.15, 0.35),
                     size=(1, 1.6), kind="streak", ramp=life_ramp(pal), drag=4, g=120, rng=rng, light=(3, 0.13))
        if i == 2 and el in ("fire", "dragon", "normal", "fighting", "rock", "ground", "steel", "poison", "dark",
                             "ghost"):
            nsm = 10 if el in ("fire", "dragon") else 6
            sim.emit(int(nsm * power), cx + rng.uniform(-6, 6), cy + 4, ang=-math.pi / 2, spread=1.6, speed=(14, 40),
                     life=(0.9, 1.5), size=(2.0 * power, 3.4 * power), kind="smoke", ramp=SMOKE, g=-18, drag=1.2,
                     turb=35, grow=0.4, rng=rng)
        if i == 1 and el in ("water", "poison"):
            r = [pal[5], pal[3], pal[2], pal[1]]
            sim.emit(int(18 * power), cx, gy - 1, ang=-math.pi / 2, spread=1.3, speed=(70, 150), life=(0.5, 0.9),
                     size=(1, 2), kind="drop", ramp=r, g=300, drag=0.4, bounce=0.2, rng=rng, area=4, area_y=0)
        if 0 < i < 8 and el in ("fire", "dragon"):
            spawn(sim, el, pal, 2, cx + rng.uniform(-6, 6), cy + rng.uniform(-4, 4), rng=rng, speed=(10, 40),
                  scale=power)

    def draw(cv, L, sim, i, t, rng):
        # light pulse: very bright on contact, decays fast
        k = math.exp(-t * 7)
        L.add(cx, cy, 26 * power, pal[3], 0.85 * k)
        L.add(cx, gy, 24 * power, pal[2], 0.35 * k)
        if i == 0:
            jag_star(cv, cx, cy, 10 * power, 8, [pal[3], pal[4], pal[5]], rs, inner=0.32)
        elif i <= 4:
            r = (16 - i * 2.5) * power
            rag_blob(cv, cx, cy, (7 - i * 1.4) * power, pal[3], 77 + i, t=i * 0.1, rough=0.5, edge=pal[2],
                     holes=0.1 * i)
            jag_star(cv, cx, cy, r, 9, [pal[2], pal[3], pal[4], pal[5]], rs, inner=0.22, rot=i * 0.4)
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
                L.add(cx, gy, r * 0.8, pal[3], 0.4 * (1 - f))
        if dark:
            rag_blob(cv, cx, gy - 1, 4 * clamp(1 - t * 1.5), pal[0], 3, t=t, edge=pal[3])
        L.add(cx, gy, 20, pal[4], math.exp(-t * 8))
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
    """Character-scale status loops: small motes drifting near the body / above the head."""
    pal = S.pal
    cx, fy = S.w / 2, S.ground
    head = fy - 30

    def tick(sim, i, t, rng):
        if what == "burn":
            for _ in range(2):
                spawn(sim, "fire", pal, 1, cx + rng.uniform(-9, 9), fy - rng.uniform(2, 20), rng=rng,
                      speed=(15, 35), scale=0.7)
            if rng.random() < 0.5:
                spawn(sim, "fire", pal, 1, cx + rng.uniform(-8, 8), fy - 18, rng=rng, secondary=True)
        elif what == "poison":
            if rng.random() < 0.6:
                sim.emit(1, cx + rng.uniform(-10, 10), fy - rng.uniform(4, 22), ang=-math.pi / 2, spread=0.4,
                         speed=(10, 22), life=(0.6, 1.0), size=(1, 2.4), kind="bubble",
                         ramp=[pal[5], pal[3], pal[2]], turb=30, drag=1, rng=rng)
            if rng.random() < 0.3:
                sim.emit(1, cx + rng.uniform(-8, 8), fy - 16, ang=math.pi / 2, spread=0.2, speed=(5, 10),
                         life=(0.4, 0.7), size=(1, 1.4), kind="drop", ramp=[pal[4], pal[3], pal[2]], g=90, rng=rng)
        elif what == "paralysis":
            if i % 3 != 2:
                spawn(sim, "electric", pal, 2, cx + rng.uniform(-10, 10), fy - rng.uniform(4, 26), rng=rng,
                      speed=(30, 70))
        elif what == "sleep":
            if i % 14 == 0:
                sim.emit(1, cx + 7, head, ang=-1.2, spread=0.1, speed=(14, 16), life=(1.3, 1.3), size=(1, 1),
                         kind="glyph", ramp=[pal[5], pal[5], pal[4], pal[0]], data="Z", turb=0, drag=0.2, rng=rng,
                         light=(6, 0.25))
        elif what == "freeze":
            if rng.random() < 0.5:
                sim.emit(1, cx + rng.uniform(-14, 14), fy - rng.uniform(16, 36), ang=math.pi / 2, spread=0.6,
                         speed=(4, 12), life=(0.7, 1.1), size=(1, 2), kind="snow", ramp=[pal[5], pal[4], pal[3]],
                         turb=20, rng=rng)
        elif what == "confusion":
            pass

    def draw(cv, L, sim, i, t, rng):
        ph = i / S.n
        if what == "paralysis" and i % 3 != 2:
            for k in range(2):
                x0 = cx + rng.uniform(-10, 10)
                y0 = fy - rng.uniform(6, 24)
                bolt(cv, rng, x0, y0, x0 + rng.uniform(-6, 6), y0 + rng.uniform(-7, 7), [pal[3], pal[5]], segs=3,
                     amp=2.5, light=L, lcol=pal[4])
        if what == "freeze":
            rs = random.Random(5)
            for k in range(6):
                x = cx + rs.uniform(-12, 12)
                h = rs.uniform(5, 11)
                lean = rs.uniform(-0.4, 0.4)
                for j in range(int(h)):
                    f = j / h
                    hw = (1 - f) * 2
                    for xx in range(int(x + lean * j - hw), int(x + lean * j + hw) + 1):
                        cv.px(xx, fy - j, pal[4] if xx >= x + lean * j else pal[2])
                cv.px(x + lean * h, fy - h, pal[5])
            g = (ph * 1.5) % 1.5
            L.add(cx - 14 + g * 28, fy - 6, 6, pal[5], 0.6 if g < 1 else 0)
            L.add(cx, fy - 4, 18, pal[3], 0.3)
        if what == "confusion":
            for k in range(3):
                a = (ph + k / 3) * TAU
                x = cx + math.cos(a) * 12
                y = head - 4 + math.sin(a) * 3.5
                front = math.sin(a) > 0
                for j in range(1, 5):
                    aa = a - j * 0.18
                    cv.px(cx + math.cos(aa) * 12, head - 4 + math.sin(aa) * 3.5, pal[2] if j < 3 else pal[1])
                r = 2 if front else 1
                for kk in range(1, r + 1):
                    for (ax, ay) in ((kk, 0), (-kk, 0), (0, kk), (0, -kk)):
                        cv.px(x + ax, y + ay, pal[4] if front else pal[3])
                cv.px(x, y, pal[5])
                L.add(x, y, 6, pal[4], 0.45 if front else 0.2)
        if what == "burn":
            for k, (dx, ph0) in enumerate(((-7, 0.0), (5, 0.35), (-1, 0.7), (9, 0.55))):
                f = (ph + ph0) % 1.0
                hgt = (5 + 4 * math.sin(f * math.pi)) * (1.1 - f * 0.4)
                tongue(cv, cx + dx, fy - 4 - f * 12, 2.2, hgt, [pal[2], pal[4], pal[5]], 30 + k, t,
                       lean=noise2(t * 4, k, 9) * 0.15)
            L.add(cx, fy - 10, 16, pal[3], 0.25 + 0.1 * noise2(i * 0.8, 2, 3))
        if what == "poison":
            L.add(cx, fy - 8, 16, pal[3], 0.2)
        draw_parts(cv, L, sim.parts, rng)

    run(S, tick, draw, loop=True, ground=fy, warm=45)


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
                     life=(0.15, 0.4), size=(1, 1.8), kind="streak", ramp=life_ramp(pal), drag=4, g=150,
                     bounce=0.3, rng=rng, light=(4, 0.13))
            sim.emit(int(6 * power), cx + ox, cy + oy, ang=-math.pi / 2, spread=TAU, speed=(15, 50),
                     life=(0.3, 0.6), size=(1, 1.4), kind="px", ramp=life_ramp(pal), drag=3, g=40, flick=0.2,
                     rng=rng)

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
