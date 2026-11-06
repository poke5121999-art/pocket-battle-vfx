"""Effect archetypes (v2, polished). Each takes S (render state: S.n frames of S.w x S.h, S.pal 6-step
ramp, S.rng seeded random, S.frames list of Canvas, S.feet) plus options and paints every frame.

Shared rules (research/style-guide.md + polish round):
- every main shape is volumetric: dithered glow behind -> dark rim -> body -> lit side -> hot core;
- impacts: 1 flash frame, burst at full size by frame 2, ease-out tail, lingering particles, floor flash/decal;
- fades use ordered (Bayer) dissolve, never alpha; smoke cools into the shared grey-violet smoke ramp;
- secondary particles (sparks, embers, droplets, chips, dust) run on gravity + drag;
- loops are periodic in i/n; directional effects face right.
"""
import math

from .core import (TAU, Particle, bayer, clamp, in_quad, out_back, out_cubic, out_expo, out_quad, seg, step)
from .palettes import ramp

SMOKE = ramp("smoke")
SCORCH = ramp("scorch")
DUST = ramp("dust")


# ------------------------------------------------------------------ small shared shapes
def glow_disc(cv, x, y, r, pal, core=True, halo=3):
    """Shaded orb with a dithered glow (kept for callers in generic.py)."""
    if r <= 0:
        return
    cv.glow(x, y, r, r + halo + r * 0.4, pal[2], density=0.7)
    cv.shaded(x, y, r, r, pal, lo=1, hi=5 if core else 4)


def puff(cv, x, y, r, pal, heat, smoke=None):
    """Flame/smoke puff. heat 1 = white-hot, 0 = cold. Below heat 0.3 it switches to the smoke ramp."""
    heat = clamp(heat)
    if r < 0.8:
        cv.px(x, y, pal[max(1, int(heat * 5))])
        return
    if heat < 0.3 and smoke is not False:
        sp = smoke or SMOKE
        top = 2 + int(heat / 0.3 * 2)
        cv.shaded(x, y, r, r * 0.92, sp, lo=1, hi=top + 1, rim=True)
        return
    hi = 2 + int(round(heat * 3))
    lo = max(0, hi - 3)
    cv.shaded(x, y, r, r * 0.95, pal, lo=lo, hi=min(5, hi), light=(-0.2, -0.7), rim=r > 4)


def leaf(cv, x, y, ang, size, pal):
    """Two-tone leaf/petal with a dark edge and a bright vein."""
    ca, sa = math.cos(ang), math.sin(ang)
    for k in range(-size, size + 1):
        half = int(round((1 - (k / (size + 0.5)) ** 2) * size * 0.55))
        for j in range(-half - 1, half + 2):
            if abs(j) == half + 1:
                c = pal[1]
            elif j <= 0:
                c = pal[3] if k < size * 0.4 else pal[4]
            else:
                c = pal[2]
            cv.px(x + ca * k - sa * j, y + sa * k + ca * j, c)
    for k in range(-size + 1, size):
        cv.px(x + ca * k, y + sa * k, pal[4])
    cv.px(x + ca * size, y + sa * size, pal[5])


def shard(cv, x, y, ang, length, width, pal, outline=True):
    """Faceted crystal: dark facet, light facet, bright ridge, hot tip, optional outline."""
    ca, sa = math.cos(ang), math.sin(ang)
    tip = (x + ca * length * 0.6, y + sa * length * 0.6)
    tail = (x - ca * length * 0.4, y - sa * length * 0.4)
    nx, ny = -sa * width, ca * width
    if outline:
        o = 1.0
        cv.poly([(tip[0] + ca * o, tip[1] + sa * o), (x + nx * 1.35, y + ny * 1.35),
                 (tail[0] - ca * o, tail[1] - sa * o), (x - nx * 1.35, y - ny * 1.35)], pal[0])
    cv.poly([tip, (x + nx, y + ny), tail, (x - nx, y - ny)], pal[2])
    cv.poly([tip, (x - nx, y - ny), tail], pal[3])
    cv.poly([tip, (x - nx * 0.4, y - ny * 0.4), (x, y)], pal[4])
    cv.line(tip[0], tip[1], x - ca * length * 0.15, y - sa * length * 0.15, pal[4])
    cv.px(tip[0], tip[1], pal[5])


def zigzag(rng, x0, y0, x1, y1, segs, amp):
    pts = [(x0, y0)]
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy) or 1
    nx, ny = -dy / L, dx / L
    for k in range(1, segs):
        t = k / segs
        o = rng.uniform(-amp, amp)
        pts.append((x0 + dx * t + nx * o, y0 + dy * t + ny * o))
    pts.append((x1, y1))
    return pts


def bolt_path(cv, pts, pal, w=2):
    cv.stroke(pts, w, pal, lo=2, hi=5)


def arrow(cv, x, y, up, pal, size=4):
    """Stat arrow with its tip at (x, y): outlined, shaded chevron head + stem behind it."""
    b = 1 if up else -1                      # direction from the tip toward the base
    hb = y + b * (size + 1)                  # head base line
    s0, s1 = sorted((hb, hb + b * (size + 2)))
    cv.poly([(x, y - b * 1.5), (x - size - 2.5, hb + b * 0.8), (x + size + 2.5, hb + b * 0.8)], pal[0])
    cv.rect(x - size * 0.45 - 1, s0 - 1, x + size * 0.45 + 1, s1 + 1, pal[0])
    cv.poly([(x, y), (x - size - 1, hb), (x + size + 1, hb)], pal[3])
    cv.poly([(x, y), (x - size - 1, hb), (x, hb)], pal[4])
    cv.rect(x - size * 0.45, s0, x + size * 0.45, s1, pal[2])
    cv.rect(x - size * 0.45, s0, x, s1, pal[3])
    cv.px(x, y + b, pal[5])


def heart(cv, x, y, pal, s=1):
    rows = ["0110110", "1233321", "1234321", "0123210", "0012100", "0001000"] if s else \
        ["01010", "12321", "01210", "00100"]
    for j, r in enumerate(rows):
        for i, b in enumerate(r):
            if b != "0":
                cv.px(x - len(r) // 2 + i, y - len(rows) // 2 + j, pal[{"1": 1, "2": 3, "3": 4, "4": 5}[b]])


def floor_flash(cv, x, y, r, pal, t, decal=None):
    """Ground contact: bright squashed flash on contact frames, then a darker decal that dissolves."""
    if t < 0.18:
        k = 1 - t / 0.18
        cv.glow(x, y, r * 0.5, r * 1.25, pal[3], density=0.8 * k + 0.2, squash=0.35)
        cv.ellipse(x, y, r * (0.6 + 0.4 * k), r * 0.22 * (0.6 + 0.4 * k), pal[4])
        cv.ellipse(x, y, r * 0.35, r * 0.1 + 0.6, pal[5])
    elif decal:
        dt = (t - 0.18) / 0.82
        for yy in range(int(-r * 0.3), int(r * 0.3) + 1):
            for xx in range(int(-r), int(r) + 1):
                d = (xx / r) ** 2 + (yy / (r * 0.3)) ** 2
                if d <= 1 and bayer(x + xx, y + yy) > dt * 0.9 + d * 0.35:
                    cv.under(x + xx, y + yy, decal[1] if d < 0.45 else decal[0])


def particles_draw(cv, parts, pal, kind="spark"):
    for p in parts:
        if not p.alive:
            continue
        t = p.t
        c = pal[5] if t < 0.2 else pal[4] if t < 0.45 else pal[3] if t < 0.7 else pal[2]
        if kind == "spark":
            L = 1.6 if t < 0.5 else 0.8
            cv.line(p.x, p.y, p.x - p.vx * L, p.y - p.vy * L, c, w=2 if p.size > 1.5 and t < 0.4 else 1)
            cv.px(p.x, p.y, pal[5] if t < 0.5 else pal[4])
        elif kind == "ember":
            cv.disc(p.x, p.y, 1 if p.size > 1.4 and t < 0.6 else 0.5, c)
        elif kind == "chip":
            s = p.size * (1 - t * 0.3)
            ang = p.age * 0.7 + p.kind
            pts = [(p.x + math.cos(ang + k * TAU / 4) * s, p.y + math.sin(ang + k * TAU / 4) * s * 0.8) for k in range(4)]
            cv.poly(pts, pal[1])
            cv.poly(pts[:3], pal[2])
            cv.px(pts[0][0], pts[0][1], pal[4])
        elif kind == "drop":
            cv.disc(p.x, p.y, p.size * (1 - t * 0.4), pal[2])
            cv.disc(p.x - 0.4, p.y - 0.4, p.size * 0.55 * (1 - t * 0.4), pal[3])
            cv.px(p.x - 0.6, p.y - 0.8, pal[5])
        elif kind == "petal":
            leaf(cv, p.x, p.y, p.age * 0.6 + p.kind, 3, pal)
        elif kind == "shard":
            shard(cv, p.x, p.y, math.atan2(p.vy, p.vx) + p.age * 0.2, 7, 1.8, pal)
        elif kind == "star":
            cv.star(p.x, p.y, 3 if t < 0.6 else 2, 0.35, 4, pal, lo=2)
        elif kind == "heart":
            heart(cv, p.x, p.y, pal, s=p.kind % 2)
        elif kind == "bubble":
            r = 1.2 + p.kind * 0.6
            cv.ring(p.x, p.y, r + 0.5, 1, pal[3])
            cv.px(p.x - 0.6, p.y - 0.8, pal[5])


def spray(rng, n, x, y, speed, life, up=0.0, spread=TAU, base=0.0, size=(1.0, 2.0)):
    out = []
    for _ in range(n):
        a = base + rng.uniform(-spread / 2, spread / 2)
        s = rng.uniform(*speed)
        out.append(Particle(x, y, math.cos(a) * s, math.sin(a) * s - up, rng.randint(*life),
                            size=rng.uniform(*size), kind=rng.randint(0, 3)))
    return out


def comet_tail(cv, hx, hy, r, length, pal, ph, wob=0.15, lo=1, dither_end=True):
    """Tapered comet body behind a head: rim / body / light / core columns with a wobbling edge."""
    L = int(length)
    for k in range(L):
        u = k / max(1, L - 1)
        x = hx - k
        half = r * (1 - u) ** 0.75 * (1 + wob * math.sin(u * 14 - ph * TAU * 2))
        yc = hy + math.sin(u * 7 - ph * TAU) * u * 1.5
        if half < 0.4:
            continue
        for y in range(int(math.floor(yc - half - 0.5)), int(math.ceil(yc + half + 0.5)) + 1):
            d = abs(y - yc) / (half + 0.5)
            if d > 1:
                continue
            if dither_end and u > 0.55 and bayer(x, y) < (u - 0.55) * 2.0:
                continue
            idx = lo if d > 0.78 else lo + 1 if d > 0.5 else lo + 2 if (d > 0.22 or u > 0.45) else lo + 3
            if u < 0.18 and d < 0.4:
                idx = lo + 4
            cv.px(x, y, pal[min(5, idx)])


# ------------------------------------------------------------------ projectiles (loops)
def orb(S, r=5, trail="flame", ring=False, spark_tail=True):
    """Looping projectile flying right: shaded head, comet body, element particles, glow."""
    r = r + 2
    hx, hy = S.w - r - 9, S.h // 2
    K = 18
    seeds = [(S.rng.random(), S.rng.uniform(-1, 1), S.rng.random()) for _ in range(K)]
    tail_len = S.w * (0.62 if trail in ("flame", "smoke", "dust", "drip") else 0.45)
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        cv.glow(hx, hy, r, r + 7, S.pal[2], density=0.55)
        if trail in ("flame", "smoke", "dust", "drip", "electric", "sparkle"):
            comet_tail(cv, hx - 1, hy, r * (0.95 if trail != "sparkle" else 0.6), tail_len, S.pal, ph,
                       lo=0 if trail == "dust" else 2 if trail == "electric" else 1)
        for (u, oy, sz) in seeds:
            p = (ph * 2 + u) % 1.0
            x = hx - r - p * (S.w - r - 14)
            y = hy + oy * (2 + p * r * 0.9) + math.sin((p + u) * TAU) * 1.2
            if trail == "flame":
                if sz > 0.5:
                    puff(cv, x, y - p * 3, (1 - p) * r * 0.55 + 0.6, S.pal, 1 - p * 1.25)
                else:
                    cv.px(x, y - p * 5, S.pal[4 if p < 0.5 else 3])
            elif trail == "smoke":
                puff(cv, x, y, (1 - p) * r * 0.6 + 0.6, S.pal, 0.55 - p * 0.5, smoke=S.pal)
            elif trail == "bubble":
                rr = 1.2 + sz * 2.4 * (1 - p * 0.5)
                cv.ring(x, y, rr + 0.5, 1, S.pal[3])
                cv.px(x - rr * 0.4, y - rr * 0.4, S.pal[5])
            elif trail == "sparkle":
                if (int(p * 8) + int(u * 5)) % 2 == 0:
                    cv.star(x, y, 1.5 + (1 - p) * 2.2, 0.3, 4, S.pal, lo=3)
            elif trail == "drip":
                cv.shaded(x, y + p * 6, (1 - p) * 2.2 + 0.6, (1 - p) * 2.6 + 0.6, S.pal, lo=1, hi=4)
            elif trail == "dust":
                cv.shaded(x, y + p * 2, (1 - p) * 2.4 + 0.6, (1 - p) * 2.0 + 0.6, DUST, lo=1, hi=4)
            elif trail == "electric" and sz > 0.6:
                cv.px(x, y, S.pal[4])
        if spark_tail:
            for k in range(3):
                yy = hy - r * 0.6 + k * r * 0.6
                L = 6 + ((i + k * 3) % 4) * 3
                cv.line(hx - r - 2, yy, hx - r - 2 - L, yy, S.pal[4 if k == 1 else 3])
        cv.shaded(hx, hy, r * 1.12, r * (0.95 + 0.05 * (i % 2)), S.pal, lo=1, hi=5, light=(0.5, -0.5))
        cv.disc(hx + r * 0.25, hy - r * 0.2, max(1, r * 0.3), S.pal[5])
        if ring:
            a = ph * TAU * 2
            cv.band(hx, hy, r + 4, 2, S.pal, squash=abs(math.cos(a)) * 0.7 + 0.25, lo=2, hi=5, gaps=2, phase=ph)
        if trail == "electric":
            for k in range(2):
                pts = zigzag(S.rng, hx - r, hy + (k - 0.5) * 3, hx - r - 18 - k * 6, hy + S.rng.uniform(-6, 6), 4, 3)
                cv.stroke(pts, 1, S.pal, lo=2, hi=5)
            for k in range(3):
                a = S.rng.uniform(0, TAU)
                pts = zigzag(S.rng, hx + math.cos(a) * r, hy + math.sin(a) * r,
                             hx + math.cos(a) * (r + 6), hy + math.sin(a) * (r + 6), 2, 1.5)
                cv.stroke(pts, 1, S.pal, lo=3, hi=5)


def boulder(S, r=6, dust=True):
    """Tumbling faceted rock: four facet tones + outline, dust comet and puffs, speed lines."""
    r = r + 2
    hx, hy = S.w - r - 8, S.h // 2
    seeds = [(S.rng.random(), S.rng.uniform(-1, 1)) for _ in range(12)]
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        if dust:
            comet_tail(cv, hx - r + 2, hy + 1, r * 0.8, S.w * 0.5, DUST, ph, lo=0)
            for (u, oy) in seeds:
                p = (ph * 2 + u) % 1.0
                cv.shaded(hx - r - p * 40, hy + oy * 4 + p * 4, (1 - p) * 2.4 + 0.6, (1 - p) * 2.0 + 0.6, DUST, lo=1, hi=4)
        for k in range(3):
            yy = hy - r + 2 + k * (r - 1)
            cv.line(hx - r - 3, yy, hx - r - 10 - ((i + k) % 3) * 4, yy, DUST[4])
        a = ph * TAU
        pts = []
        for k in range(8):
            ang = a + k * TAU / 8
            rr = r * (0.82 + 0.18 * ((k * 37) % 5) / 4)
            pts.append((hx + math.cos(ang) * rr, hy + math.sin(ang) * rr))
        out = [(hx + (x - hx) * 1.18, hy + (y - hy) * 1.18) for x, y in pts]
        cv.poly(out, S.pal[0])
        cv.poly(pts, S.pal[2])
        for k in range(8):
            f = [pts[k], pts[(k + 1) % 8], (hx, hy)]
            mid = (pts[k][0] + pts[(k + 1) % 8][0]) / 2 - hx, (pts[k][1] + pts[(k + 1) % 8][1]) / 2 - hy
            lit = -(mid[0] * 0.6 + mid[1] * 0.8) / r
            cv.poly(f, S.pal[1] if lit < -0.4 else S.pal[2] if lit < 0.15 else S.pal[3] if lit < 0.6 else S.pal[4])
        cv.px(hx - r * 0.35, hy - r * 0.45, S.pal[5])
        cv.line(hx - 2, hy + 1, hx + 2, hy - 2, S.pal[1])


def volley(S, kind="shard", count=3):
    """Loop: a formation of shards/leaves/stars/needles flying right, each with a trail and glints."""
    cy = S.h / 2
    gap = (S.w - 24) / max(1, count)
    slots = [(S.w - 12 - k * gap, cy + ((-1) ** k) * (4 + k * 2), S.rng.random()) for k in range(count)]
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        for (x, y, u) in slots:
            yy = y + math.sin((ph + u) * TAU) * 1.5
            tl = 14 + ((i + int(u * 4)) % 3) * 2
            cv.tri_ray(x - 4, yy, math.pi, 0, tl, 3.5, S.pal[1])
            cv.tri_ray(x - 4, yy, math.pi, 0, tl * 0.6, 1.6, S.pal[3])
            if kind == "shard":
                cv.glow(x, yy, 3, 8, S.pal[2], density=0.45)
                shard(cv, x, yy, 0.0, 16, 3.4, S.pal)
            elif kind == "leaf":
                leaf(cv, x, yy, (ph + u) * TAU * 2, 6, S.pal)
                cv.px(x - 8, yy + 2, S.pal[3])
            elif kind == "star":
                cv.glow(x, yy, 3, 9, S.pal[2], density=0.55)
                cv.star(x, yy, 7 + (i + int(u * 4)) % 2, 0.38, 4, S.pal, rot=(ph + u) * TAU / 4, lo=1)
            elif kind == "needle":
                cv.glow(x, yy, 2, 6, S.pal[2], density=0.4)
                cv.tri_ray(x - 8, yy, 0, 0, 16, 4.5, S.pal[0])
                cv.tri_ray(x - 8, yy, 0, 0, 15, 3, S.pal[3])
                cv.line(x - 7, yy - 1, x + 5, yy - 1, S.pal[4])
                cv.px(x + 7, yy, S.pal[5])
            elif kind == "crescent":
                cv.band(x - 3, yy, 8, 3, S.pal, lo=2, hi=5, gaps=1, phase=0.69)


def waves(S, arcs=3, thick=2):
    """Loop: thick shaded arcs travelling right (sound / force / buzz) with glow and motes."""
    cx, cy = 4, S.h / 2
    thick = thick * 2
    motes = [(S.rng.random(), S.rng.uniform(-1, 1)) for _ in range(10)]
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        for k in range(arcs):
            p = (ph + k / arcs) % 1.0
            r = 8 + p * (S.w - 14)
            span = (0.13 + 0.06 * (1 - p)) * TAU
            th = max(2, thick * (1.1 - p * 0.5))
            hi = 5 if p < 0.35 else 4
            for a_i in range(-90, 91):
                a = a_i / 90 * span
                edge = 1 - abs(a_i) / 90
                for tt in range(int(th * (0.5 + 0.5 * edge)) + 1):
                    rr = r - tt
                    kk = tt / max(1, th)
                    idx = hi if kk < 0.2 else hi - 1 if kk < 0.5 else 2 if kk < 0.8 else 1
                    cv.px(cx + math.cos(a) * rr, cy + math.sin(a) * rr * 1.1, S.pal[idx])
                if a_i % 3 == 0:
                    cv.glow(cx + math.cos(a) * (r + 2), cy + math.sin(a) * (r + 2) * 1.1, 0, 2.5, S.pal[2], density=0.4)
        for (u, oy) in motes:
            p = (ph + u) % 1.0
            cv.px(cx + 10 + p * (S.w - 18), cy + oy * (6 + p * S.h * 0.35), S.pal[4 if p < 0.5 else 3])
        cv.shaded(cx + 3, cy, 4, 5, S.pal, lo=2)


def crescent_loop(S):
    """Loop: a thick shaded air blade (filled crescent) with wind ribbons."""
    cx, cy = S.w - 18, S.h / 2
    R = S.h / 2 - 2
    for i, cv in enumerate(S.frames):
        wob = (i % 2)
        for k in range(5):
            y = cy - R * 0.7 + k * R * 0.35 + ((i + k) % 2)
            x1 = cx - 10 - (k * 5 + i * 4) % 9
            x0 = x1 - 14 - (k * 7 + i * 3) % 12
            cv.line(x0, y, x1, y, S.pal[2], w=2)
            cv.line(x0 + 4, y, x1, y, S.pal[3])
        for y in range(int(cy - R), int(cy + R) + 1):
            for x in range(int(cx - R), int(cx + R * 0.7) + 1):
                d1 = math.hypot((x - cx) / 0.62, y - cy)
                d2 = math.hypot((x - cx + 6 + wob) / 0.62, y - cy)
                if d1 <= R and d2 > R:
                    k = (R - d1) / 5.0
                    idx = 5 if k < 0.18 else 4 if k < 0.4 else 3 if k < 0.65 else 2
                    cv.px(x + wob, y, S.pal[idx])
        cv.glow(cx, cy, R * 0.6, R + 4, S.pal[2], density=0.35)


# ------------------------------------------------------------------ beams (one-shot)
def beam(S, style="spiral", charge=6, extend=3, hold=8, width=6):
    """Anticipation gather -> smear frame -> thick beam with core line and element edges -> thins out.
    style: spiral | wave | rings | ice | plain"""
    ox, oy = 12, S.h / 2
    width = width * 1.6
    fade = S.n - charge - extend - hold
    gather = [(S.rng.uniform(0, TAU), S.rng.uniform(12, 24)) for _ in range(14)]
    spray_p = []
    for i, cv in enumerate(S.frames):
        if i < charge:
            t = (i + 1) / charge
            for (a, d) in gather:
                dd = d * (1 - out_quad(t)) + 2
                cv.line(ox + math.cos(a) * dd, oy + math.sin(a) * dd,
                        ox + math.cos(a) * (dd + 4), oy + math.sin(a) * (dd + 4), S.pal[4 if t > 0.5 else 3])
            glow_disc(cv, ox, oy, 2 + t * width * 0.45, S.pal)
            if i >= charge - 2:
                cv.band(ox, oy, width * 0.9 + 4, 2, S.pal, lo=3, hi=5)
            continue
        k = i - charge
        if k == 0:
            cv.line(ox, oy, S.w, oy, S.pal[5], w=3)
            cv.line(ox, oy - 2, S.w, oy - 2, S.pal[4])
            cv.line(ox, oy + 2, S.w, oy + 2, S.pal[4])
            glow_disc(cv, ox, oy, width * 0.6, S.pal)
            continue
        if k < extend:
            head = ox + (S.w - ox) * out_quad((k + 1) / extend)
            wfac = 0.75 + 0.25 * (k + 1) / extend
        elif k < extend + hold:
            head = S.w + 4
            wfac = 1.0 + (0.1 if (k % 2) else 0)
        else:
            head = S.w + 4
            wfac = max(0.0, 1 - (k - extend - hold + 1) / (fade + 1))
        half = width * wfac / 2
        if half < 0.6:
            cv.line(ox, oy, S.w, oy, S.pal[3], dither=True)
            continue
        for x in range(int(ox), int(min(head, S.w + 2))):
            yo = math.sin(x * 0.22 - i * 1.4) * 2.0 if style == "wave" else 0
            yc = oy + yo
            edge = half
            if style == "wave":
                edge = half + 1.4 * max(0, math.sin(x * 0.9 - i * 2.1)) + (1 if (x * 7 + i) % 5 == 0 else 0)
            elif style in ("plain", "spiral"):
                edge = half + 0.6 * math.sin(x * 0.5 - i * 1.7)
            for y in range(int(yc - edge - 4), int(yc + edge + 5)):
                d = abs(y - yc)
                if d > edge:
                    if d < edge + 3.5 and bayer(x, y) < 0.55 * (1 - (d - edge) / 3.5):
                        cv.under(x, y, S.pal[2])
                    continue
                kk = d / max(0.6, edge)
                idx = 1 if kk > 0.85 else 2 if kk > 0.62 else 3 if kk > 0.38 else 4 if kk > 0.14 else 5
                cv.px(x, y, S.pal[idx])
            if style == "spiral":
                a = x * 0.4 - i * 1.1
                sy = yc + math.sin(a) * (half + 1.5)
                if math.cos(a) > -0.1:
                    cv.px(x, sy, S.pal[5])
                    cv.px(x, sy + 1, S.pal[5])
                else:
                    cv.px(x, sy, S.pal[1])
            elif style == "rings" and (x - i * 3) % 11 == 0:
                cv.band(x, yc, half + 4, 2, S.pal, squash=1.0, lo=3, hi=5)
            elif style == "ice" and (x * 7 + i) % 9 == 0:
                side = -1 if (x // 9) % 2 else 1
                shard(cv, x, yc + side * (half + 2), -side * 1.4, 9, 2, S.pal)
            elif style == "wave" and (x * 13 + i * 7) % 17 == 0 and len(spray_p) < 40:
                spray_p.append(Particle(x, yc - edge * (1 if x % 2 else -1), S.rng.uniform(-0.3, 0.6),
                                        S.rng.uniform(-1.6, 1.6), S.rng.randint(4, 8), size=S.rng.uniform(0.8, 1.6)))
        particles_draw(cv, spray_p, S.pal, "drop")
        step(spray_p, gravity=0.25)
        glow_disc(cv, ox, oy, half * 1.1 + 1.5, S.pal)
        if head < S.w:
            glow_disc(cv, head, oy, half + 1.5, S.pal)
        elif k < extend + hold:
            cv.shaded(S.w - 3, oy, half + 3, half + 4, S.pal, lo=2)


def bolt_strike(S, branches=2):
    """Lightning: dim pre-strike + ground sparks (2 f), fat cored bolt with branches flickering, ground
    flash, shock band, debris sparks, scorch decal."""
    tx, ty = S.w / 2, S.h - 14
    sparks = []
    for i, cv in enumerate(S.frames):
        if i < 2:
            cv.line(tx, 0, tx, ty, S.pal[2], dither=True)
            cv.glow(tx, ty, 2, 8 + i * 4, S.pal[3], density=0.5, squash=0.4)
            for k in range(2 + i * 2):
                a = S.rng.uniform(math.pi, TAU)
                pts = zigzag(S.rng, tx, ty, tx + math.cos(a) * 8, ty + math.sin(a) * 5, 2, 1.5)
                cv.stroke(pts, 1, S.pal, lo=3, hi=5)
            continue
        j = i - 2
        floor_flash(cv, tx, ty + 2, 22, S.pal, seg(j, 0, 9), decal=SCORCH)
        if j <= 4 or (j <= 7 and j % 2 == 1):
            pts = zigzag(S.rng, tx + S.rng.uniform(-8, 8), -2, tx, ty, 8, 7)
            for p in pts[::2]:
                cv.glow(p[0], p[1], 2, 9, S.pal[2], density=0.5)
            cv.stroke(pts, 4 if j < 3 else 3, S.pal, lo=2, hi=5)
            for b in range(branches + (1 if j < 2 else 0)):
                jj = S.rng.randint(1, len(pts) - 3)
                bx, by = pts[jj]
                ex = bx + S.rng.choice((-1, 1)) * S.rng.uniform(10, 20)
                bp = zigzag(S.rng, bx, by, ex, by + S.rng.uniform(8, 20), 3, 3)
                cv.stroke(bp, 1, S.pal, lo=2, hi=5)
            if j == 0:
                sparks += spray(S.rng, 14, tx, ty - 2, (1.5, 3.4), (5, 9), up=1.5, spread=math.pi, base=-math.pi / 2)
        if j >= 6:
            for k in range(3):
                sx = tx + S.rng.uniform(-12, 12)
                sy = ty + S.rng.uniform(-3, 3)
                pts = zigzag(S.rng, sx, sy, sx + S.rng.uniform(-6, 6), sy - S.rng.uniform(3, 8), 2, 2)
                cv.stroke(pts, 1, S.pal, lo=2, hi=5 if j < 8 else 4)
            cv.glow(tx, ty + 2, 3, 12, S.pal[2], density=0.35 if j < 8 else 0.2, squash=0.4)
        if j < 3:
            cv.shaded(tx, ty - 1, 9 - j * 2, 6 - j, S.pal, lo=3)
        if 0 <= j < 8:
            cv.band(tx, ty + 2, 6 + out_cubic(seg(j, 0, 7)) * 22, 3 if j < 3 else 2, S.pal, squash=0.38, lo=2, hi=5,
                    front_lit=True)
        particles_draw(cv, sparks, S.pal, "spark")
        step(sparks, gravity=0.35, drag=0.92)


# ------------------------------------------------------------------ impacts (one-shot)
def burst(S, rays=8, ring=True, sparks=12, star=True, gravity=0.0, spark_kind="dot", core_r=None):
    """Flash -> shaded star at full size by frame 1-2 -> thick ring + tapered rays -> sparks/debris with
    gravity linger -> dissolve. Floor flash under the target."""
    cx, cy = S.w / 2, S.h / 2
    R = min(S.w, S.h) / 2 - 2
    core_r = core_r or R * 0.42
    kind = {"dot": "spark"}.get(spark_kind, spark_kind)
    parts = spray(S.rng, sparks + 4, cx, cy, (R / 16, R / 8), (int(S.n * 0.6), S.n + 2), up=gravity * 4,
                  size=(1.0, 2.2))
    motes = spray(S.rng, 8, cx, cy, (R / 40, R / 22), (S.n - 3, S.n + 4), size=(0.8, 1.6))
    ray_a = [k * TAU / rays + (0.18 if k % 2 else 0) for k in range(rays)]
    fy = min(S.h - 3, cy + R * 0.62)
    for i, cv in enumerate(S.frames):
        t = i / max(1, S.n - 1)
        floor_flash(cv, cx, fy, R * 0.75, S.pal, t)
        if i == 0:
            cv.glow(cx, cy, core_r, core_r * 2.1, S.pal[3], density=0.9)
            cv.band(cx, cy, core_r * 1.6, 2, S.pal, lo=2, hi=4)
            cv.disc(cx, cy, core_r * 1.25, S.pal[4])
            cv.disc(cx, cy, core_r * 0.95, S.pal[5])
            continue
        if star and i <= 4:
            s = core_r * (2.0 if i == 1 else 1.75 if i == 2 else 1.3 if i == 3 else 0.9)
            cv.glow(cx, cy, s * 0.5, s * 1.3, S.pal[2], density=0.6)
            cv.star(cx, cy, s, 0.36, 4, S.pal, rot=-0.15, lo=2)
            cv.star(cx, cy, s * 0.6, 0.4, 4, S.pal, rot=math.pi / 4 - 0.15, lo=3)
        if ring and 1 <= i <= S.n * 0.7:
            rt = seg(t, 0.04, 0.7)
            rr = core_r + out_cubic(rt) * (R - core_r)
            cv.band(cx, cy, rr, max(1.5, 5 * (1 - rt)), S.pal, lo=1 if rt > 0.5 else 2, hi=5 if rt < 0.4 else 4,
                    gaps=0 if rt < 0.45 else 6, phase=0.1, dens=1.0 if rt < 0.6 else 0.6)
        if 1 <= i <= S.n * 0.5:
            rt = seg(t, 0.04, 0.5)
            for k, a in enumerate(ray_a):
                r0 = core_r * 0.7 + out_expo(rt) * R * 0.45
                r1 = r0 + (1 - rt) * R * (0.6 if k % 2 == 0 else 0.35)
                cv.tri_ray(cx, cy, a, r0, r1, 3.2 * (1 - rt) + 1, S.pal[4 if rt < 0.4 else 3])
                cv.line(cx + math.cos(a) * r0, cy + math.sin(a) * r0, cx + math.cos(a) * (r0 + (r1 - r0) * 0.6),
                        cy + math.sin(a) * (r0 + (r1 - r0) * 0.6), S.pal[5])
        if i >= 1:
            particles_draw(cv, parts, S.pal, kind)
            for m in motes:
                if m.alive and m.age > 2:
                    cv.disc(m.x, m.y - m.age * 0.4, m.size, S.pal[3 if m.t < 0.6 else 2])
                    cv.px(m.x, m.y - m.age * 0.4, S.pal[5 if m.t < 0.4 else 4])
            step(parts, gravity=gravity + 0.05, drag=0.88)
            step(motes, drag=0.9)
        if t > 0.7:
            cv.dissolve((t - 0.7) / 0.3 * 0.7, seed=i)


def splash(S, drops=16):
    """Liquid hit: flash blob, shaded crown spikes, highlighted droplets on gravity, foam band, puddle
    decal dissolving."""
    cx, gy = S.w / 2, S.h - 12
    parts = []
    for k in range(drops + 6):
        a = S.rng.uniform(math.pi * 1.08, math.pi * 1.92)
        sp = S.rng.uniform(1.8, 4.2)
        parts.append(Particle(cx + S.rng.uniform(-4, 4), gy - 8, math.cos(a) * sp, math.sin(a) * sp,
                              S.n, size=S.rng.uniform(1.2, 2.6)))
    for i, cv in enumerate(S.frames):
        t = i / (S.n - 1)
        floor_flash(cv, cx, gy + 1, S.w * 0.42, S.pal, t, decal=[S.pal[1], S.pal[2]])
        for k in range(2):
            rt = seg(t, 0.08 + k * 0.22, 0.75 + k * 0.2)
            if 0 < rt < 1:
                cv.band(cx, gy, 8 + rt * (S.w / 2 - 6), 3 * (1 - rt) + 1, S.pal, squash=0.33, lo=2, hi=5,
                        front_lit=True, dens=1 if rt < 0.6 else 0.6)
        if i < 2:
            cv.glow(cx, gy - 8, 5, 14, S.pal[3], density=0.8)
            cv.shaded(cx, gy - 8, 9 - i * 2, 8 - i * 2, S.pal, lo=3)
        if 1 <= i < S.n * 0.6:
            ct = seg(t, 0.05, 0.6)
            h = math.sin(ct * math.pi) * 22
            for k in range(-4, 5):
                x = cx + k * (3 + ct * 3)
                top = gy - 4 - h * (1 - abs(k) / 5)
                cv.poly([(x - 2.2, gy - 2), (x + k * 0.6, top), (x + 2.2, gy - 2)], S.pal[2])
                cv.poly([(x - 1, gy - 3), (x + k * 0.6, top), (x + 0.5, gy - 3)], S.pal[3])
                cv.disc(x + k * 0.6, top - 1, 1.3, S.pal[4])
                cv.px(x + k * 0.6, top - 1, S.pal[5])
            cv.ellipse(cx, gy - 2, 7 + ct * 8, 3.5, S.pal[2])
            cv.ellipse(cx, gy - 3, 5 + ct * 6, 2, S.pal[4])
        live = [p for p in parts if p.y < gy + 1]
        particles_draw(cv, live, S.pal, "drop")
        step(parts, gravity=0.42)


def explosion(S, puffs=10, smoke=True, embers=10):
    """Fire burst: flash, shaded fireball cluster at full size by frame 2, shock band, cooling into
    grey-violet smoke that rises and dissolves, embers on gravity, scorch decal."""
    cx, cy = S.w / 2, S.h / 2 + 4
    R = min(S.w, S.h) / 2 - 3
    blobs = [(S.rng.uniform(0, TAU), S.rng.uniform(0.2, 1.0), S.rng.uniform(0.55, 1.0)) for _ in range(puffs + 4)]
    emb = spray(S.rng, embers + 8, cx, cy, (1.8, 4.0), (S.n // 2, S.n), up=1.6, size=(1, 2))
    fy = min(S.h - 4, cy + R * 0.6)
    for i, cv in enumerate(S.frames):
        t = i / (S.n - 1)
        floor_flash(cv, cx, fy, R * 0.9, S.pal, t, decal=SCORCH)
        if i == 0:
            cv.glow(cx, cy, R * 0.3, R * 0.85, S.pal[4], density=0.9)
            cv.disc(cx, cy, R * 0.45, S.pal[5])
            continue
        ex = out_cubic(seg(t, 0, 0.3))
        heat = 1 - seg(t, 0.08, 0.75)
        if i < 5:
            cv.band(cx, cy, R * (0.55 + i * 0.12), 3, S.pal, lo=3, hi=5, dens=1 - i * 0.18)
        if heat > 0.3:
            cv.glow(cx, cy, R * 0.4 * ex, R * 0.95 * ex + 2, S.pal[2], density=0.5 * heat + 0.2)
        for (a, d, s) in sorted(blobs, key=lambda b: -b[1]):
            dist = d * R * 0.55 * ex
            rise = seg(t, 0.35, 1) * R * 0.55 * s if smoke else 0
            r = (R * 0.4 * s) * (0.55 + 0.6 * ex) * (1 - 0.35 * seg(t, 0.6, 1))
            puff(cv, cx + math.cos(a) * dist, cy + math.sin(a) * dist * 0.75 - rise, r, S.pal,
                 heat * (1.15 - d * 0.35))
        particles_draw(cv, emb, S.pal, "ember")
        step(emb, gravity=0.2, drag=0.93)
        if t > 0.72:
            cv.dissolve((t - 0.72) / 0.28 * 0.8, seed=i)


def debris(S, chunks=9, dust=True):
    """Rock/ground hit: flash star, shaded outlined chunks that bounce, rolling dust puffs, decal."""
    cx, gy = S.w / 2, S.h - 10
    parts = [Particle(cx + S.rng.uniform(-5, 5), gy - 8, S.rng.uniform(-2.8, 2.8), S.rng.uniform(-4.6, -2.2),
                      S.n, size=S.rng.uniform(2.0, 4.2), kind=S.rng.randint(0, 3)) for _ in range(chunks + 3)]
    dusts = [(S.rng.choice((-1, 1)) * S.rng.uniform(0.2, 1), S.rng.uniform(0.6, 1), S.rng.random()) for _ in range(10)]
    for i, cv in enumerate(S.frames):
        t = i / (S.n - 1)
        floor_flash(cv, cx, gy + 1, S.w * 0.4, S.pal, t, decal=SCORCH)
        if i < 3:
            cv.glow(cx, gy - 8, 4, 16 - i * 3, S.pal[4], density=0.8)
            cv.star(cx, gy - 8, 14 - i * 3, 0.35, 4, S.pal, lo=2)
        if dust:
            for (d, s, u) in dusts:
                dt = out_quad(seg(t, 0.05 + u * 0.1, 1))
                if dt <= 0:
                    continue
                x = cx + d * dt * S.w * 0.42
                r = (2.5 + s * 5) * (0.4 + dt) * (1 - seg(t, 0.75, 1) * 0.5)
                cv.shaded(x, gy - r * 0.55 - dt * 4, r, r * 0.85, DUST, lo=1, hi=4)
        for p in parts:
            s = p.size
            ang = p.age * 0.5 + p.kind
            pts = [(p.x + math.cos(ang + k * TAU / 5) * s, p.y + math.sin(ang + k * TAU / 5) * s) for k in range(5)]
            out = [(p.x + (x - p.x) * 1.3, p.y + (y - p.y) * 1.3) for x, y in pts]
            cv.poly(out, S.pal[0])
            cv.poly(pts, S.pal[2])
            cv.poly([pts[0], pts[1], (p.x, p.y)], S.pal[4])
            cv.poly([pts[3], pts[4], (p.x, p.y)], S.pal[1])
        step(parts, gravity=0.4)
        for p in parts:
            if p.y > gy:
                p.y = gy
                p.vy *= -0.35
                p.vx *= 0.6
        if t > 0.75:
            cv.dissolve((t - 0.75) / 0.25 * 0.7, seed=i)


def slash(S, count=1, width=3, claw=False):
    """Thick crescent slash(es): fast sweep, hot leading edge, cooling tail, glint and sparks."""
    cx, cy = S.w / 2, S.h / 2
    R = min(S.w, S.h) / 2 - 3
    width = width + 2
    sparks = []
    for i, cv in enumerate(S.frames):
        t = i / (S.n - 1)
        for c in range(count):
            off = (c - (count - 1) / 2) * 11
            delay = c * (0.04 if claw else 0.08)
            lt = seg(t, delay, delay + 0.8)
            if lt <= 0 or lt >= 1:
                continue
            sweep = out_expo(seg(lt, 0, 0.22))
            thin = 1 - seg(lt, 0.35, 1) ** 1.3
            steps = 90
            if claw:
                x0, y0 = cx - R * 0.75 + off, cy - R * 0.85 - off * 0.25
                x1, y1 = cx + R * 0.65 + off, cy + R * 0.85 - off * 0.25
                tail0 = seg(lt, 0.25, 1.0)
                for k in range(steps + 1):
                    f = k / steps
                    if f > sweep or f < tail0:
                        continue
                    x = x0 + (x1 - x0) * f + math.sin(f * math.pi) * -4
                    y = y0 + (y1 - y0) * f
                    wk = width * thin * math.sin(clamp((f - tail0) / max(0.05, sweep - tail0)) * math.pi) + 0.5
                    for tt in range(int(math.ceil(wk)) + 1):
                        kk = tt / max(1, wk)
                        col = S.pal[5] if kk < 0.25 else S.pal[4] if kk < 0.5 else S.pal[3] if kk < 0.8 else S.pal[2]
                        cv.px(x + tt * 0.7, y - tt * 0.7, col)
                    cv.glow(x, y, wk, wk + 3, S.pal[2], density=0.3)
                continue
            a0, a1 = -2.4, -2.4 + 2.9 * sweep
            tail = a0 + (a1 - a0) * seg(lt, 0.25, 1.0) ** 1.5
            for k in range(steps + 1):
                a = tail + (a1 - tail) * k / steps
                frac = k / steps
                wk = max(0.0, width * thin * math.sin(frac * math.pi * 0.95 + 0.1) * 1.5)
                for tt in range(int(math.ceil(wk)) + 1):
                    rr = R - tt + off
                    x = cx + math.cos(a) * rr
                    y = cy + math.sin(a) * rr * 0.78
                    kk = tt / max(1, wk)
                    col = S.pal[5] if kk < 0.22 else S.pal[4] if kk < 0.45 else S.pal[3] if kk < 0.7 else S.pal[2]
                    cv.px(x, y, col)
                if k % 6 == 0:
                    cv.glow(cx + math.cos(a) * (R - wk / 2 + off), cy + math.sin(a) * (R - wk / 2 + off) * 0.78, 0,
                            wk / 2 + 4, S.pal[2], density=0.5)
        if i == 2:
            ex, ey = (cx + R * 0.6, cy + R * 0.8) if claw else (cx + math.cos(0.5) * R, cy + math.sin(0.5) * R * 0.78)
            sparks += spray(S.rng, 10, ex, ey, (1.2, 3.0), (4, 8), up=0.5, size=(1, 2))
        if 2 <= i <= 4:
            gx, gy = (cx + R * 0.65, cy + R * 0.8) if claw else (cx + math.cos(0.5) * R, cy + math.sin(0.5) * R * 0.78)
            cv.star(gx, gy, 7 - (i - 2) * 2, 0.3, 4, S.pal, lo=3)
        particles_draw(cv, sparks, S.pal, "spark")
        step(sparks, gravity=0.2, drag=0.88)


# ------------------------------------------------------------------ areas and auras
def flame_tongue(cv, x, y, r, h, pal, heat, lean=0.0):
    """Teardrop flame: shaded round base + tapered tip, coloured by heat."""
    hi = 2 + int(round(clamp(heat) * 3))
    lo = max(0, hi - 3)
    cv.poly([(x - r * 0.9, y), (x + lean, y - h), (x + r * 0.9, y)], pal[lo + 1])
    cv.poly([(x - r * 0.4, y), (x + lean * 0.7, y - h * 0.7), (x + r * 0.4, y)], pal[min(5, lo + 2)])
    cv.shaded(x, y, r, r * 0.9, pal, lo=lo, hi=min(5, hi), light=(0, -0.8))


def aura(S, kind="flame", ground=True):
    """Loop around a standing unit (feet at S.feet): ground band + glow, element bodies rising along the
    silhouette edge, small motes."""
    cx, fy = S.w / 2, S.feet
    K = 16
    seeds = [(S.rng.random(), S.rng.choice((-1, 1)) * S.rng.uniform(0.5, 1), S.rng.random()) for _ in range(K)]
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        if ground:
            cv.glow(cx, fy, 8, 24, S.pal[2], density=0.55, squash=0.35)
            pr = (ph * 2) % 1.0
            cv.band(cx, fy, 10 + pr * 14, 3 * (1 - pr) + 1, S.pal, squash=0.35, lo=2, hi=5, front_lit=True)
            cv.band(cx, fy, 16, 2, S.pal, squash=0.35, lo=1, hi=4, gaps=6, phase=ph, front_lit=True)
        order = sorted(seeds, key=lambda s: (ph + s[0]) % 1.0, reverse=True)
        for (u, side, sz) in order:
            p = (ph + u) % 1.0
            x = cx + side * (13 - p * 5) + math.sin((p * 2 + u) * TAU) * 1.5
            y = fy - 1 - (p ** 1.2) * (S.h * 0.72)
            if kind == "flame":
                r = (1 - p) * 4.2 * (0.6 + sz * 0.6) + 1
                flame_tongue(cv, x, y, r, r * 2.6, S.pal, 1.1 - p, lean=-side * 1.5)
            elif kind == "spark":
                if (i + int(u * 7)) % 3 != 0:
                    pts = zigzag(S.rng, x, y, x + S.rng.uniform(-5, 5), y - 8, 3, 2.5)
                    cv.stroke(pts, 1, S.pal, lo=2, hi=5)
                    cv.glow(x, y - 4, 1, 5, S.pal[2], density=0.4)
            elif kind == "wisp":
                r = (1 - p) * 3.2 + 1
                for k in range(4):
                    cv.disc(x - side * k * 0.6, y + r + k * 2, r * (1 - k * 0.22), S.pal[2], dither=k > 1)
                cv.glow(x, y, r, r + 4, S.pal[2], density=0.4)
                cv.shaded(x, y, r, r, S.pal, lo=1)
            elif kind == "sparkle":
                if (int(p * 6) + int(u * 3)) % 3 != 0:
                    cv.glow(x, y, 1, 5, S.pal[2], density=0.45)
                    cv.star(x, y, 2 + (1 - p) * 3, 0.32, 4, S.pal, lo=2)
            elif kind == "bubble":
                cv.ring(x, y, 1.5 + sz * 1.5 * (1 - p * 0.3), 1, S.pal[3])
                cv.px(x - 1, y - 1, S.pal[5])
            elif kind == "leaf":
                leaf(cv, x, y, (p + u) * TAU, 4, S.pal)
            elif kind == "line":
                L = 7 + sz * 8
                cv.line(x, y, x, y + L, S.pal[2], w=3)
                cv.line(x, y, x, y + L * 0.7, S.pal[4], w=1)
                cv.px(x, y - 1, S.pal[5])
                cv.glow(x, y + L / 2, 1, 4, S.pal[2], density=0.35)
        if kind == "line":
            for k in range(6):
                p = (ph * 2 + k / 6) % 1.0
                cv.px(cx + (k - 2.5) * 5, fy - 4 - p * 30, S.pal[4])


def pillar(S, kind="flame"):
    """Column bursting from a ground glow: 2 f anticipation, overshoot rise, shaded flickering column,
    crown puffs, base embers, collapse, scorch decal."""
    cx, gy = S.w / 2, S.h - 8
    Hmax = S.h - 16
    emb = []
    for i, cv in enumerate(S.frames):
        t = i / (S.n - 1)
        floor_flash(cv, cx, gy, 20, S.pal, seg(t, 0.12, 1), decal=SCORCH)
        if i < 2:
            cv.glow(cx, gy, 3, 12 + i * 5, S.pal[3], density=0.7, squash=0.35)
            cv.band(cx, gy, 8 + i * 4, 2, S.pal, squash=0.35, lo=3, hi=5)
            continue
        rise = out_back(seg(t, 0.12, 0.35))
        fall = seg(t, 0.65, 1.0)
        height = Hmax * clamp(rise) * (1 - in_quad(fall))
        w = 11 * (1 - fall * 0.6)
        if i == 2:
            emb += spray(S.rng, 16, cx, gy - 4, (1.5, 3.5), (6, 12), up=2.5, spread=math.pi * 0.9, base=-math.pi / 2)
        for y in range(int(gy - height), int(gy)):
            k = (gy - y) / max(1, height)
            jag = math.sin(y * 0.7 + i * 1.9) * 1.8 + math.sin(y * 0.23 - i) * 1.2
            hw = w * (1 - k * 0.3) + jag * 0.6
            for x in range(int(cx - hw - 5), int(cx + hw + 6)):
                d = abs(x - cx - jag * 0.4) / max(1, hw)
                if d > 1:
                    if d < 1 + 5 / max(1, hw) and bayer(x, y) < 0.5 * (1 - (d - 1) * hw / 5):
                        cv.under(x, y, S.pal[2])
                    continue
                kk = d + (bayer(x, y) - 0.5) * 0.2
                idx = 1 if kk > 0.82 else 2 if kk > 0.6 else 3 if kk > 0.36 else 4 if kk > 0.14 else 5
                if t > 0.6 and idx == 5:
                    idx = 4
                cv.px(x, y, S.pal[idx])
        top = gy - height
        if height > 6:
            for k in range(5):
                a = -math.pi / 2 + (k - 2) * 0.5
                d = 6 + (i % 3) * 2
                if kind == "flame":
                    puff(cv, cx + math.cos(a) * d, top + math.sin(a) * d, 3.5, S.pal, 0.85 - fall)
                else:
                    cv.shaded(cx + math.cos(a) * d, top + math.sin(a) * d, 2.5, 2.5, S.pal, lo=1)
            cv.shaded(cx, top, w * 0.8, 4, S.pal, lo=2)
        cv.band(cx, gy, 12 + rise * 6, 3, S.pal, squash=0.33, lo=2, hi=5, front_lit=True)
        particles_draw(cv, emb, S.pal, "ember" if kind == "flame" else "drop")
        step(emb, gravity=0.18, drag=0.95)


def vortex(S, kind="petal", rings=6):
    """Loop tornado: funnel glow, stacked thick squashed bands lit on the front, orbiting pieces in front
    and behind, ground swirl band."""
    cx, gy = S.w / 2, S.h - 8
    Ht = S.h - 14
    seeds = [(S.rng.random(), S.rng.random()) for _ in range(16)]
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        for k in range(8):
            f = k / 8
            cv.glow(cx, gy - f * Ht, 0, 5 + f * (S.w / 2 - 6), S.pal[1], density=0.5,
                    squash=0.35)
        cv.band(cx, gy + 1, S.w / 2 - 6, 3, S.pal, squash=0.25, lo=1, hi=4, gaps=4, phase=ph, front_lit=True)
        back, front = [], []
        for (u, v) in seeds:
            f = (u + ph * 0.5) % 1.0
            a = (v + ph * 2) * TAU
            r = 4 + f * (S.w / 2 - 9)
            item = (cx + math.cos(a) * r, gy - f * Ht + math.sin(a) * r * 0.3, a)
            (front if math.sin(a) > 0 else back).append(item)
        for (x, y, a) in back:
            cv.disc(x, y, 1, S.pal[2])
        for k in range(rings):
            f = (k + ph) / rings
            y = gy - f * Ht
            r = 4 + f * (S.w / 2 - 9)
            sway = math.sin((f * 2 + ph) * TAU) * 2
            cv.band(cx + sway, y, r, 3 + f * 3, S.pal, squash=0.3, lo=1, hi=5 if k % 2 == 0 else 4, front_lit=True,
                    gaps=2 if kind == "wind" else 0, phase=ph * 2 + f)
        for (x, y, a) in front:
            if kind == "petal":
                leaf(cv, x, y, a * 2, 3, S.pal)
            elif kind == "water":
                cv.shaded(x, y, 1.6, 1.8, S.pal, lo=2)
            elif kind == "wind":
                cv.line(x, y, x - math.sin(a) * 6, y + math.cos(a) * 1.5, S.pal[5], w=1)
                cv.line(x - math.sin(a) * 2, y, x - math.sin(a) * 8, y + math.cos(a) * 2, S.pal[3])
            else:
                cv.star(x, y, 2, 0.3, 4, S.pal, lo=3)


def pulse_rings(S, rings=3, thick=2, squash=1.0, loop=True, dark_center=False):
    """Thick gradient rings growing outward with a dithered field between them and a shaded core.
    One-shot version adds a flash frame, outward particles and a dissolve."""
    ground = squash != 1.0
    cx, cy = S.w / 2, (S.h / 2 if not ground else S.h - 14)
    R = min(S.w / 2, (S.h / 2 if not ground else S.h - 16) / squash) - 2
    th = thick * 2 + 1 + (thick + 1 if ground else 0)
    sp = spray(S.rng, 14, cx, cy, (R / 18, R / 9), (S.n // 2, S.n), size=(1, 2)) if not loop else []
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        t = i / max(1, S.n - 1)
        if not loop and i == 0:
            cv.glow(cx, cy, 4, R * 0.55, S.pal[3], density=0.9, squash=squash)
            cv.shaded(cx, cy, R * 0.3, R * 0.3 * squash, S.pal, lo=2)
            continue
        cv.glow(cx, cy, 0, R * (0.9 if loop else 0.4 + out_quad(t) * 0.6), S.pal[1], density=0.45 if ground else 0.32,
                squash=squash)
        for k in range(rings):
            p = (ph + k / rings) % 1.0 if loop else clamp(t * 1.4 - k * 0.15)
            if not loop and (p <= 0 or p >= 1):
                continue
            r = 5 + out_quad(p) * (R - 5)
            w = max(1.5, th * (1 - p * 0.55))
            cv.band(cx, cy, r, w, S.pal, squash=squash, lo=1 if p > 0.6 else 2, hi=5 if p < 0.3 else 4,
                    front_lit=ground, dens=1.0 if p < 0.7 else 0.65)
        if loop or t < 0.6:
            if dark_center:
                cv.glow(cx, cy, 4, 9, S.pal[3], density=0.6, squash=squash)
                cv.ellipse(cx, cy, 5 + (i % 2), (5 + (i % 2)) * squash, S.pal[0])
                cv.band(cx, cy, 6 + (i % 2), 2, S.pal, squash=squash, lo=3, hi=5)
            else:
                cv.shaded(cx, cy, 3 + (i % 2), (3 + (i % 2)) * max(squash, 0.6), S.pal, lo=2)
        if sp:
            particles_draw(cv, sp, S.pal, "star" if not dark_center else "ember")
            step(sp, drag=0.9)
        if not loop and t > 0.7:
            cv.dissolve((t - 0.7) / 0.3 * 0.75, seed=i)


def cloud(S, puffs=9):
    """Gas cloud loop: lit-from-above shaded lumps with dithered rim glow, churning; bubbles rise and pop."""
    cx, cy = S.w / 2, S.h / 2 + 6
    blobs = [(S.rng.uniform(-1, 1), S.rng.uniform(-0.6, 0.6), S.rng.uniform(6, 11), S.rng.random()) for _ in range(puffs + 2)]
    bub = [(S.rng.uniform(-1, 1), S.rng.random(), S.rng.uniform(1.2, 2.4)) for _ in range(8)]
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        cv.glow(cx, cy + 4, 10, S.w / 2, S.pal[1], density=0.4, squash=0.55)
        for (bx, by, r, u) in sorted(blobs, key=lambda b: b[1]):
            wob = math.sin((ph + u) * TAU)
            x = cx + bx * (S.w / 2 - 14) + wob * 2
            y = cy + by * (S.h / 2 - 14) + math.cos((ph + u) * TAU) * 1.5
            rr = r + wob * 1.2
            cv.glow(x, y, rr, rr + 3, S.pal[2], density=0.5)
            cv.shaded(x, y, rr, rr * 0.85, S.pal, lo=1, hi=4, light=(-0.2, -0.9))
        for (bx, u, s) in bub:
            p = (ph + u) % 1.0
            x = cx + bx * (S.w / 2 - 12)
            y = cy + 2 - p * (S.h / 2 + 4)
            if p < 0.8:
                cv.shaded(x, y, s + p * 1.5, s + p * 1.5, S.pal, lo=2)
            else:
                for k in range(6):
                    a = k * TAU / 6
                    cv.px(x + math.cos(a) * (s + 3), y + math.sin(a) * (s + 3), S.pal[4])


def rain(S, kind="snow", density=26, wind=0.6):
    """Weather area loop: frosted ground decal, wind ribbons, big shaded flakes/hail/drops falling."""
    cx, gy = S.w / 2, S.h - 10
    seeds = [(S.rng.random(), S.rng.random(), S.rng.random()) for _ in range(density)]
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        cv.glow(cx, gy, S.w / 2 - 16, S.w / 2 - 2, S.pal[2], density=0.5, squash=0.2)
        cv.ellipse(cx, gy, S.w / 2 - 14, 5, S.pal[2])
        cv.ellipse(cx, gy - 1, S.w / 2 - 20, 3, S.pal[3])
        for k in range(5):
            x = cx - S.w / 2 + 16 + k * (S.w - 32) / 4 + (k % 2) * 3
            cv.star(x, gy - 1 - (k % 2), 2 + ((i + k) % 3 == 0), 0.3, 4, S.pal, lo=3)
        for k in range(3):
            p = (ph + k / 3) % 1.0
            y = 12 + k * (S.h / 4)
            x0 = p * (S.w + 30) - 30
            pts = [(x0 + j * 5, y + math.sin(j * 0.9 + p * 6) * 2 + j * wind * 1.2) for j in range(7)]
            cv.stroke(pts, 2, S.pal, lo=2, hi=4)
        for (u, v, s) in seeds:
            p = (ph + v) % 1.0
            x = (u * (S.w + 20) - 10 + p * wind * 30) % S.w
            y = p * (gy + 4) - 4
            if kind == "snow":
                if s > 0.55:
                    cv.glow(x, y, 1, 4, S.pal[2], density=0.4)
                    cv.star(x, y, 3, 0.3, 4, S.pal, rot=p * 3, lo=2)
                else:
                    cv.disc(x, y, 1, S.pal[4])
                    cv.px(x, y, S.pal[5])
            elif kind == "rain":
                cv.line(x, y, x - wind * 3, y - 6, S.pal[3], w=2)
            elif kind == "hail":
                shard(cv, x, y, 1.2, 6, 1.5, S.pal)


def cracks(S, n_cracks=6):
    """Ground layer: floor flash, glowing cracks race out and cool, outlined slabs heave, dust rolls,
    everything settles into a dissolving decal."""
    cx, cy = S.w / 2, S.h / 2 + 8
    paths = []
    for k in range(n_cracks):
        a = k * TAU / n_cracks + S.rng.uniform(-0.3, 0.3)
        L = S.rng.uniform(0.7, 1.0) * (S.w / 2 - 4)
        pts = [(cx, cy)]
        for j in range(1, 7):
            d = L * j / 6
            pts.append((cx + math.cos(a) * d + S.rng.uniform(-2.5, 2.5), cy + math.sin(a) * d * 0.45 + S.rng.uniform(-1, 1)))
        paths.append(pts)
    rocks = [Particle(cx + S.rng.uniform(-S.w / 3, S.w / 3), cy + S.rng.uniform(-8, 6), S.rng.uniform(-0.4, 0.4),
                      S.rng.uniform(-3.0, -1.4), S.n, size=S.rng.uniform(2.2, 4.0), kind=k) for k in range(9)]
    dust = [(S.rng.uniform(-1, 1), S.rng.uniform(-0.5, 0.5), S.rng.uniform(3, 6)) for _ in range(10)]
    for i, cv in enumerate(S.frames):
        t = i / (S.n - 1)
        grow = out_cubic(seg(t, 0, 0.35))
        heat = 1 - seg(t, 0.15, 0.6)
        floor_flash(cv, cx, cy, S.w * 0.45, S.pal, t)
        for pts in paths:
            m = max(1, int(round(grow * (len(pts) - 1))))
            sub = pts[:m + 1]
            for a, b in zip(sub, sub[1:]):
                cv.line(a[0], a[1] + 1, b[0], b[1] + 1, SCORCH[0], w=3)
                cv.line(a[0], a[1], b[0], b[1], SCORCH[1], w=3)
                cv.line(a[0], a[1], b[0], b[1], S.pal[5 if heat > 0.7 else 4] if heat > 0.25 else SCORCH[2], w=1)
        if 0 < t < 0.7:
            cv.band(cx, cy, 6 + grow * (S.w / 2 - 6), 3, S.pal, squash=0.45, lo=2, hi=4, front_lit=True,
                    dens=1 - seg(t, 0.3, 0.7) * 0.6)
        for (dx, dy, r) in dust:
            dt = out_quad(seg(t, 0.1, 1))
            if dt > 0:
                rr = r * (0.5 + dt) * (1 - seg(t, 0.8, 1) * 0.5)
                cv.shaded(cx + dx * (S.w / 2 - 10) * (0.5 + dt * 0.5), cy + dy * 14 - dt * 6, rr, rr * 0.8, DUST, lo=1, hi=4)
        for p in rocks:
            if i >= 2 and (p.y < cy + 10 or p.vy < 0):
                s = p.size
                pts = [(p.x + math.cos(p.kind + k * TAU / 5 + p.age * 0.35) * s,
                        p.y + math.sin(p.kind + k * TAU / 5 + p.age * 0.35) * s) for k in range(5)]
                cv.poly([(p.x + (x - p.x) * 1.3, p.y + (y - p.y) * 1.3) for x, y in pts], S.pal[0])
                cv.poly(pts, S.pal[2])
                cv.poly([pts[0], pts[1], (p.x, p.y)], S.pal[4])
                cv.poly([pts[3], pts[4], (p.x, p.y)], S.pal[1])
        if i >= 2:
            step(rocks, gravity=0.32)
        if t > 0.8:
            cv.dissolve((t - 0.8) / 0.2 * 0.6, seed=i)


def spikes(S, count=5, kind="rock"):
    """Floor telegraph glow, spikes stab up in sequence (shaded faces + outline + ridge), chips fly,
    dust at the base, hold, sink."""
    gy = S.h - 8
    xs = [12 + k * (S.w - 24) / max(1, count - 1) for k in range(count)]
    hs = [S.rng.uniform(0.7, 1.0) * (S.h - 16) for _ in range(count)]
    chips = []
    started = set()
    for i, cv in enumerate(S.frames):
        t = i / (S.n - 1)
        for k, (x, h) in enumerate(zip(xs, hs)):
            st = seg(t, 0.06 + k * 0.06, 0.06 + k * 0.06 + 0.12)
            sink = seg(t, 0.72, 1.0)
            w = 5 + h / 9
            if st <= 0:
                cv.glow(x, gy, 2, w + 5, S.pal[3], density=0.6, squash=0.35)
                cv.ellipse(x, gy, w + 2, 2, S.pal[2], dither=True)
                continue
            if k not in started:
                started.add(k)
                chips += spray(S.rng, 5, x, gy - 3, (1.2, 2.6), (6, 10), up=2.2, spread=math.pi * 0.8,
                               base=-math.pi / 2, size=(1.2, 2.2))
            hh = h * out_back(st) * (1 - in_quad(sink))
            cv.ellipse(x, gy, w + 4, 2.5, DUST[1])
            if hh < 1:
                continue
            top = gy - hh
            lean = (k % 3 - 1) * 2
            cv.poly([(x - w - 1.2, gy + 1), (x + lean, top - 1.5), (x + w + 1.2, gy + 1)], S.pal[0])
            cv.poly([(x - w, gy), (x + lean, top), (x + w, gy)], S.pal[2])
            cv.poly([(x + lean * 0.3 - w * 0.1, gy), (x + lean, top), (x + w, gy)],
                    S.pal[3] if kind != "ice" else S.pal[4])
            cv.poly([(x - w, gy), (x + lean, top), (x - w * 0.55, gy)], S.pal[1])
            cv.line(x + lean, top, x + lean * 0.3 - w * 0.1, gy - 2, S.pal[4] if kind != "ice" else S.pal[5])
            cv.px(x + lean, top, S.pal[5])
            if 0 < st < 1:
                cv.shaded(x - w - 2, gy - 2, 3, 2.5, DUST, lo=1, hi=4)
                cv.shaded(x + w + 2, gy - 2, 3, 2.5, DUST, lo=1, hi=4)
        particles_draw(cv, chips, S.pal, "chip")
        step(chips, gravity=0.35)


def swarm(S, count=16):
    """Loop: outlined bugs with flickering wings on noisy orbits inside a faint buzz haze."""
    cx, cy = S.w / 2, S.h / 2
    seeds = [(S.rng.random(), S.rng.uniform(8, S.w / 2 - 5), S.rng.uniform(0.4, 0.9), S.rng.choice((1, 2))) for _ in range(count)]
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        cv.glow(cx, cy, 0, S.w / 2 - 2, S.pal[1], density=0.45, squash=0.7)
        for (u, r, sq, sp) in sorted(seeds, key=lambda s: math.sin((s[0] + ph * s[3]) * TAU)):
            a = (u + ph * sp) * TAU
            x = cx + math.cos(a) * r
            y = cy + math.sin(a) * r * sq + math.sin(a * 3) * 2
            for k in range(1, 4):
                cv.px(cx + math.cos(a - 0.12 * k) * r, cy + math.sin(a - 0.12 * k) * r * sq, S.pal[2 if k < 2 else 1])
            cv.rect(x - 2, y - 1, x + 2, y + 1, S.pal[0])
            cv.rect(x - 1, y - 1, x + 1, y, S.pal[2])
            cv.px(x + 1, y, S.pal[3])
            wing = S.pal[5] if (i + int(u * 9)) % 2 else S.pal[4]
            cv.px(x - 1, y - 2, wing)
            cv.px(x, y - 2, wing)
            cv.px(x + 1, y - 3 + (i % 2), wing)


def ring_shield(S, hexes=True):
    """Loop: dome with a thick gradient rim, faint dithered fill, hex points and a sweeping highlight."""
    cx, fy = S.w / 2, S.feet
    R = S.w / 2 - 4
    cy = fy - R * 0.55
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        cv.ellipse(cx, fy, R, R * 0.3, S.pal[1], dither=True)
        cv.band(cx, fy, R, 2, S.pal, squash=0.3, lo=2, hi=4, front_lit=True)
        for y in range(int(cy - R), int(fy) + 1):
            for x in range(int(cx - R), int(cx + R) + 1):
                d = math.hypot((x - cx) / R, (y - cy) / (R * 0.95))
                if d > 1.0:
                    continue
                if d > 0.86:
                    k = (d - 0.86) / 0.14
                    cv.px(x, y, S.pal[5] if k < 0.3 else S.pal[4] if k < 0.6 else S.pal[3])
                    continue
                diag = ((x - cx) + (y - cy) * 0.8) / (2 * R) + 0.5
                sweep = (ph * 1.6) % 1.6 - 0.3
                if abs(diag - sweep) < 0.07:
                    cv.px(x, y, S.pal[4] if abs(diag - sweep) < 0.035 else S.pal[3])
                elif hexes and d > 0.45 and x % 4 == (y // 4 % 2) * 2 and y % 4 == 0:
                    cv.px(x, y, S.pal[3])
                elif bayer(x, y) < 0.12 + d * 0.18:
                    cv.px(x, y, S.pal[2])
        cv.star(cx - R * 0.45, cy - R * 0.5, 3 + (i % 2), 0.3, 4, S.pal, lo=3)
