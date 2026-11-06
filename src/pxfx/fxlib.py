"""Effect archetypes. Each takes S (the render state: S.n frames of S.w x S.h, S.pal ramp,
S.rng seeded random, S.frames list of Canvas) plus options, and paints every frame.

Conventions shared by all archetypes (from research/style-guide.md):
- directional effects face right; the engine mirrors/rotates them.
- frame 0 or 1 of an impact is the brightest (core colour), later frames cool down the ramp.
- layering inside a frame: glow halo (dithered, behind) -> body (mid) -> core (bright) -> sparks.
- loops are periodic in i/n so frame n wraps to frame 0 with no seam.
"""
import math

from .core import (TAU, Particle, clamp, in_quad, lerp, out_back, out_cubic, out_expo,
                   out_quad, seg, step)


# ------------------------------------------------------------------ helpers
def glow_disc(cv, x, y, r, pal, core=True, halo=2):
    """Layered orb: dithered halo, dark rim, mid body, light, hot core."""
    if r <= 0:
        return
    cv.disc(x, y, r + halo, pal[1], dither=True, under=True)
    cv.disc(x, y, r, pal[2])
    cv.disc(x - r * 0.15, y - r * 0.15, r * 0.7, pal[3])
    if core:
        cv.disc(x - r * 0.25, y - r * 0.25, max(0.6, r * 0.38), pal[5] if r < 4 else pal[4])
        if r >= 4:
            cv.disc(x - r * 0.3, y - r * 0.3, r * 0.18, pal[5])


def puff(cv, x, y, r, pal, heat):
    """A flame/smoke puff whose colours slide down the ramp as heat drops (1 hot -> 0 cold)."""
    hi = int(round(clamp(heat) * 5))
    cv.disc(x, y, r, pal[max(0, hi - 2)])
    if r > 1.2:
        cv.disc(x - r * 0.2, y - r * 0.25, r * 0.6, pal[max(0, hi - 1)])
    if r > 2.5 and hi >= 3:
        cv.disc(x - r * 0.3, y - r * 0.35, r * 0.28, pal[hi])


def leaf(cv, x, y, ang, size, pal):
    """Small two-tone leaf/petal: a pointed ellipse rotated to ang."""
    ca, sa = math.cos(ang), math.sin(ang)
    for k in range(-size, size + 1):
        half = int(round((1 - (k / (size + 0.5)) ** 2) * size * 0.5))
        for j in range(-half, half + 1):
            c = pal[3] if j <= 0 else pal[2]
            cv.px(x + ca * k - sa * j, y + sa * k + ca * j, c)
    cv.px(x + ca * size, y + sa * size, pal[4])


def shard(cv, x, y, ang, length, width, pal):
    """Pointed crystal shard: dark side, light side, bright tip."""
    ca, sa = math.cos(ang), math.sin(ang)
    tip = (x + ca * length * 0.6, y + sa * length * 0.6)
    tail = (x - ca * length * 0.4, y - sa * length * 0.4)
    nx, ny = -sa * width, ca * width
    cv.poly([tip, (x + nx, y + ny), tail, (x - nx, y - ny)], pal[2])
    cv.poly([tip, (x - nx, y - ny), tail], pal[3])
    cv.line(tip[0], tip[1], x, y, pal[4])
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
    for a, b in zip(pts, pts[1:]):
        cv.line(a[0], a[1], b[0], b[1], pal[2], w=w + 2)
    for a, b in zip(pts, pts[1:]):
        cv.line(a[0], a[1], b[0], b[1], pal[4], w=w)
    for a, b in zip(pts, pts[1:]):
        cv.line(a[0], a[1], b[0], b[1], pal[5], w=1)


def arrow(cv, x, y, up, pal, size=4):
    """Stat arrow: chevron head + stem, outlined."""
    d = -1 if up else 1
    for k in range(size + 1):
        cv.line(x - size + k, y + d * k, x + size - k, y + d * k, pal[3] if k else pal[4])
    cv.rect(x - 1, y + d * (size + 1), x + 1, y + d * (size * 2 + 1), pal[2])


def heart(cv, x, y, pal, s=1):
    rows = ["01010", "11111", "11111", "01110", "00100"] if s else ["101", "111", "010"]
    for j, r in enumerate(rows):
        for i, b in enumerate(r):
            if b == "1":
                cv.px(x - len(r) // 2 + i, y - len(rows) // 2 + j, pal[4] if (i + j) < 2 else pal[3])


# ------------------------------------------------------------------ projectiles (loops)
def orb(S, r=5, trail="flame", ring=False, spark_tail=True):
    """Looping projectile flying right. Head at (S.w - r - 6, S.h/2); trail fills the left."""
    hx, hy = S.w - r - 6, S.h // 2
    K = 22 if trail == "flame" else 14
    seeds = [(S.rng.random(), S.rng.uniform(-1, 1), S.rng.random()) for _ in range(K)]
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        # trail particles, periodic in ph
        for (u, oy, sz) in seeds:
            p = (ph * 2 + u) % 1.0
            x = hx - 2 - p * (S.w - r - 14)
            y = hy + oy * (2 + p * r * 0.9) + math.sin((p + u) * TAU) * 1.2
            if trail == "flame":
                x = hx - 2 - (p ** 1.3) * (S.w - r - 14)
                puff(cv, x, y, (1 - p) * r * (0.75 + sz * 0.45) + 0.5, S.pal, 1 - p * 1.05)
            elif trail == "smoke":
                cv.disc(x, y, (1 - p) * r * 0.7 + 0.5, S.pal[1 if p > 0.4 else 2], dither=p > 0.6)
            elif trail == "bubble":
                rr = 1 + sz * 2.2 * (1 - p)
                cv.ring(x, y, rr, 1, S.pal[3])
                cv.px(x - rr * 0.4, y - rr * 0.4, S.pal[5])
            elif trail == "sparkle":
                if (int(p * 8) + int(u * 5)) % 2 == 0:
                    cv.sparkle(x, y, 1 + (1 - p) * 2, S.pal[3 if p > 0.3 else 4], S.pal[5])
            elif trail == "dots":
                cv.disc(x, y, (1 - p) * 1.6, S.pal[2 + int((1 - p) * 2)])
            elif trail == "drip":
                cv.disc(x, y + p * 5, (1 - p) * 1.8 + 0.3, S.pal[2 if p > 0.5 else 3])
            elif trail == "dust":
                cv.disc(x, y + p * 2, (1 - p) * 1.6 + 0.4, S.pal[1 + (int(u * 3) % 2)], dither=p > 0.5)
        if spark_tail:
            # a long thin streak right behind the head sells speed
            cv.line(hx - r - 1, hy, hx - r - 4 - (i % 2) * 3, hy, S.pal[4])
        pulse = r + (1 if i % 4 in (1, 2) else 0) * 0.6
        glow_disc(cv, hx, hy, pulse, S.pal)
        if ring:
            a = ph * TAU * 2
            cv.ring(hx, hy, r + 3, 1, S.pal[4], squash=abs(math.cos(a)) * 0.8 + 0.2, gaps=2, phase=ph)
        if trail == "electric":
            pts = zigzag(S.rng, hx - r, hy, hx - r - 14, hy + S.rng.uniform(-4, 4), 4, 2.5)
            bolt_path(cv, pts, S.pal, w=1)
            pts = zigzag(S.rng, hx, hy, hx + S.rng.uniform(-3, 3), hy + S.rng.choice((-1, 1)) * (r + 4), 3, 1.5)
            for a, b in zip(pts, pts[1:]):
                cv.line(a[0], a[1], b[0], b[1], S.pal[4])


def boulder(S, r=6, dust=True):
    """Tumbling rock projectile, loop: faceted body rotating in 4 steps, dust trail."""
    hx, hy = S.w - r - 6, S.h // 2
    K = 10
    seeds = [(S.rng.random(), S.rng.uniform(-1, 1)) for _ in range(K)]
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        if dust:
            for (u, oy) in seeds:
                p = (ph * 2 + u) % 1.0
                cv.disc(hx - r - p * 30, hy + oy * 3 + p * 3, (1 - p) * 2.2 + 0.3, S.pal[2 if p < 0.4 else 1],
                        dither=p > 0.5)
        a = ph * TAU
        pts = []
        for k in range(7):
            ang = a + k * TAU / 7
            rr = r * (0.85 + 0.15 * ((k * 37) % 5) / 4)
            pts.append((hx + math.cos(ang) * rr, hy + math.sin(ang) * rr))
        cv.poly(pts, S.pal[2])
        cv.poly([pts[0], pts[1], pts[2], (hx, hy)], S.pal[3])
        cv.poly([pts[4], pts[5], (hx, hy)], S.pal[1])
        cv.px(pts[1][0], pts[1][1], S.pal[4])
        cv.outline(S.pal[0])


def volley(S, kind="shard", count=3):
    """Loop: a small formation of shards/leaves/stars flying right, each bobbing on its own phase."""
    cy = S.h / 2
    slots = [(S.w - 10 - k * 15, cy + ((-1) ** k) * (5 + k * 2), S.rng.random()) for k in range(count)]
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        for (x, y, u) in slots:
            yy = y + math.sin((ph + u) * TAU) * 1.5
            # streak behind each
            cv.line(x - 6, yy, x - 12 - (i + int(u * 4)) % 3 * 2, yy, S.pal[2], dither=True)
            if kind == "shard":
                shard(cv, x, yy, 0.0, 11, 2.4, S.pal)
            elif kind == "leaf":
                leaf(cv, x, yy, (ph + u) * TAU * 2, 4, S.pal)
            elif kind == "star":
                rr = 3 + (i + int(u * 4)) % 2
                cv.sparkle(x, yy, rr, S.pal[4], S.pal[5])
                cv.disc(x, yy, 1, S.pal[5])
            elif kind == "needle":
                cv.line(x - 6, yy, x + 4, yy, S.pal[3])
                cv.line(x - 2, yy - 1, x + 3, yy - 1, S.pal[4])
                cv.px(x + 5, yy, S.pal[5])
            elif kind == "crescent":
                cv.ring(x - 3, yy, 7, 2, S.pal[3], gaps=1, phase=0.69)
                cv.ring(x - 3, yy, 7, 1, S.pal[5], gaps=1, phase=0.69)


def waves(S, arcs=3, thick=2):
    """Loop: concentric arcs travelling right (sound / force / buzz)."""
    cx, cy = 6, S.h / 2
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        for k in range(arcs):
            p = (ph + k / arcs) % 1.0
            r = 6 + p * (S.w - 14)
            col = S.pal[4] if p < 0.4 else S.pal[3] if p < 0.75 else S.pal[2]
            span = 0.11 + 0.05 * (1 - p)
            for a_i in range(-60, 61):
                a = a_i / 60 * span * TAU
                for tt in range(thick):
                    cv.px(cx + math.cos(a) * (r - tt), cy + math.sin(a) * (r - tt) * 1.1, col)
        cv.disc(cx + 2, cy, 2, S.pal[4])


def crescent_loop(S):
    """Loop: a spinning-free air blade (crescent) with wind streaks, facing right."""
    cx, cy = S.w - 16, S.h / 2
    for i, cv in enumerate(S.frames):
        wob = math.sin(i / S.n * TAU) * 1
        for k in range(5):
            y = cy - 8 + k * 4 + ((i + k) % 2)
            cv.line(cx - 18 - (k * 7 + i * 3) % 14, y, cx - 8 - (k * 5 + i * 3) % 9, y, S.pal[2], dither=k % 2 == 0)
        for t in range(4):
            r = 14 - t
            for a_i in range(-60, 61):
                a = a_i / 60 * 1.3
                taper = 1 - abs(a_i) / 60
                if t >= 2 and taper < 0.25 * (t - 1):
                    continue
                x = cx + math.cos(a) * r * 0.6 + wob
                y = cy + math.sin(a) * r
                cv.px(x, y, S.pal[2 + t] if t < 3 else S.pal[5])


# ------------------------------------------------------------------ beams (one-shot)
def beam(S, style="spiral", charge=6, extend=3, hold=8, width=6):
    """Charge at the left, beam shoots right across the frame, holds, thins out.
    style: spiral | wave | rings | ice | plain"""
    ox, oy = 10, S.h / 2
    fade = S.n - charge - extend - hold
    gather = [(S.rng.uniform(0, TAU), S.rng.uniform(10, 20)) for _ in range(10)]
    for i, cv in enumerate(S.frames):
        if i < charge:
            t = (i + 1) / charge
            for (a, d) in gather:
                dd = d * (1 - out_quad(t))
                cv.line(ox + math.cos(a) * dd, oy + math.sin(a) * dd,
                        ox + math.cos(a) * (dd + 3), oy + math.sin(a) * (dd + 3), S.pal[4])
            glow_disc(cv, ox, oy, 1 + t * (width * 0.6), S.pal)
            if i == charge - 1:
                cv.ring(ox, oy, width + 3, 1, S.pal[5])
            continue
        k = i - charge
        if k < extend:
            head = ox + (S.w - ox) * out_quad((k + 1) / extend)
            wfac = 0.7 + 0.3 * (k + 1) / extend
        elif k < extend + hold:
            head = S.w + 4
            wfac = 1.0 + (0.12 if (k % 2) else 0)
        else:
            head = S.w + 4
            wfac = max(0.0, 1 - (k - extend - hold + 1) / (fade + 1))
        w = width * wfac
        if w < 0.5:
            continue
        for x in range(int(ox), int(min(head, S.w + 2))):
            if style == "wave":
                yo = math.sin((x * 0.25) - i * 1.4) * 1.6
            else:
                yo = 0
            half = w / 2
            for y in range(int(oy - half - 2), int(oy + half + 3)):
                d = abs(y - (oy + yo))
                if d <= half + 1.5 and (x + y) % 2 == 0:
                    cv.under(x, y, S.pal[1])
                if d <= half:
                    cv.px(x, y, S.pal[2])
                if d <= half * 0.62:
                    cv.px(x, y, S.pal[3])
                if d <= half * 0.28:
                    cv.px(x, y, S.pal[5])
            if style == "spiral":
                a = x * 0.42 - i * 1.1
                sy = oy + math.sin(a) * (half + 1.5)
                if math.cos(a) > -0.2:
                    cv.px(x, sy, S.pal[5])
                    cv.px(x, sy + 1, S.pal[4])
            elif style == "rings" and (x - i * 3) % 12 == 0:
                cv.ring(x, oy, half + 3, 1, S.pal[4], squash=1.0)
            elif style == "ice" and (x * 7 + i) % 11 == 0:
                shard(cv, x, oy + ((x * 13) % 3 - 1) * (half + 2), -1.57 if x % 2 else 1.57, 6, 1.5, S.pal)
        # muzzle flare at origin
        glow_disc(cv, ox, oy, w * 0.75 + 1, S.pal)
        if head < S.w:
            glow_disc(cv, head, oy, w * 0.65 + 1, S.pal)
        elif k < extend + hold:
            cv.disc(S.w - 2, oy, w * 0.7, S.pal[4])


def bolt_strike(S, branches=2):
    """Lightning from the top edge into a point near the bottom; flicker regenerates the path."""
    tx, ty = S.w / 2, S.h - 14
    for i, cv in enumerate(S.frames):
        t = i / (S.n - 1)
        if i == 0:
            # anticipation: a thin pre-strike line
            cv.line(tx, 0, tx, ty, S.pal[2], dither=True)
            continue
        if i >= 8:
            # residue: scorched spot and crawling sparks
            cv.ellipse(tx, ty + 2, 8, 2, S.pal[0], dither=i > 9)
            for k in range(3):
                sx = tx + S.rng.uniform(-10, 10)
                sy = ty + S.rng.uniform(-3, 2)
                pts = zigzag(S.rng, sx, sy, sx + S.rng.uniform(-5, 5), sy - S.rng.uniform(2, 6), 2, 1.5)
                for a, b in zip(pts, pts[1:]):
                    cv.line(a[0], a[1], b[0], b[1], S.pal[4 if i < 10 else 3])
        if i <= 4 or (i <= 7 and i % 2 == 1):
            pts = zigzag(S.rng, tx + S.rng.uniform(-6, 6), -2, tx, ty, 7, 6)
            bolt_path(cv, pts, S.pal, w=4 if i < 3 else 3)
            for b in range(branches):
                j = S.rng.randint(1, len(pts) - 3)
                bx, by = pts[j]
                ex = bx + S.rng.choice((-1, 1)) * S.rng.uniform(8, 16)
                bp = zigzag(S.rng, bx, by, ex, by + S.rng.uniform(8, 18), 3, 3)
                for a, b2 in zip(bp, bp[1:]):
                    cv.line(a[0], a[1], b2[0], b2[1], S.pal[4])
        # ground impact
        if 1 <= i:
            r = 3 + out_cubic(seg(i, 1, 7)) * 16
            if i < 9:
                cv.ring(tx, ty + 2, r, 1 if i > 3 else 2, S.pal[4 if i < 5 else 3], squash=0.4)
            if i < 4:
                cv.disc(tx, ty, 7 - i, S.pal[5])
            for k in range(6):
                if i < 9:
                    a = k * TAU / 6 + 0.3
                    rr = 4 + i * 2.5
                    cv.px(tx + math.cos(a) * rr, ty - abs(math.sin(a)) * rr * 0.6, S.pal[4])


# ------------------------------------------------------------------ impacts (one-shot)
def burst(S, rays=8, ring=True, sparks=12, star=True, gravity=0.0, spark_kind="dot", core_r=None):
    """The core impact: flash -> star -> expanding ring + rays -> sparks cool and fall."""
    cx, cy = S.w / 2, S.h / 2
    R = min(S.w, S.h) / 2 - 2
    core_r = core_r or R * 0.32
    parts = []
    for k in range(sparks):
        a = S.rng.uniform(0, TAU)
        sp = S.rng.uniform(1.6, 3.4) * R / 30
        parts.append(Particle(cx, cy, math.cos(a) * sp, math.sin(a) * sp - gravity * 3,
                              S.rng.randint(int(S.n * 0.7), S.n + 2), kind=S.rng.randint(0, 2)))
    big = R > 36
    ray_a = [S.rng.uniform(0, TAU) if k % 2 else k * TAU / rays for k in range(rays)]
    for i, cv in enumerate(S.frames):
        t = i / max(1, S.n - 1)
        if i == 0:
            cv.disc(cx, cy, core_r * 0.8, S.pal[5])
            cv.disc(cx, cy, core_r * 1.3, S.pal[4], dither=True, under=True)
        else:
            if star and i <= 3:
                s = core_r * (1.9 if i == 1 else 1.45 if i == 2 else 0.9)
                pts = []
                for k in range(8):
                    a = k * TAU / 8 + 0.2
                    rr = s * (1.0 if k % 2 == 0 else 0.4)
                    pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
                cv.poly(pts, S.pal[4] if i < 3 else S.pal[3])
                cv.disc(cx, cy, s * 0.35, S.pal[5])
            if ring and i <= S.n * 0.6:
                rt = seg(t, 0.05, 0.6)
                rr = core_r + out_cubic(rt) * (R - core_r)
                cv.ring(cx, cy, rr, 2 if rt < 0.5 else 1, S.pal[4] if rt < 0.35 else S.pal[3], gaps=0 if rt < 0.5 else 5,
                        phase=0.1)
            if i <= S.n * 0.45:
                rt = seg(t, 0.05, 0.45)
                for a in ray_a:
                    r0 = core_r * 0.8 + out_expo(rt) * R * 0.55
                    r1 = r0 + (1 - rt) * R * 0.45
                    cv.line(cx + math.cos(a) * r0, cy + math.sin(a) * r0,
                            cx + math.cos(a) * r1, cy + math.sin(a) * r1, S.pal[5 if rt < 0.3 else 4])
        for p in parts:
            if p.alive and i > 0:
                c = S.pal[5] if p.t < 0.25 else S.pal[4] if p.t < 0.55 else S.pal[3] if p.t < 0.8 else S.pal[2]
                if spark_kind == "dot":
                    if p.t < 0.45:
                        cv.line(p.x, p.y, p.x - p.vx * 1.8, p.y - p.vy * 1.8, c, w=2 if big else 1)
                    elif big or p.t < 0.75:
                        cv.disc(p.x, p.y, 1 if big else 0.5, c) if big else cv.line(p.x, p.y, p.x - p.vx, p.y - p.vy, c)
                    else:
                        cv.px(p.x, p.y, c)
                elif spark_kind == "petal":
                    leaf(cv, p.x, p.y, p.age * 0.7 + p.kind, 3, S.pal)
                elif spark_kind == "star":
                    cv.sparkle(p.x, p.y, 2 if p.t < 0.6 else 1, c, S.pal[5])
                elif spark_kind == "heart":
                    heart(cv, p.x, p.y, S.pal, s=p.kind % 2)
                elif spark_kind == "shard":
                    shard(cv, p.x, p.y, math.atan2(p.vy, p.vx), 6, 1.4, S.pal)
                elif spark_kind == "bubble":
                    cv.ring(p.x, p.y, 1 + p.kind * 0.7, 1, S.pal[3])
        step(parts, gravity=gravity + 0.03, drag=0.9)


def splash(S, drops=16):
    """Liquid hit: crown splash, droplets on gravity arcs, ground ripple ring."""
    cx, gy = S.w / 2, S.h - 12
    parts = []
    for k in range(drops):
        a = S.rng.uniform(math.pi * 1.1, math.pi * 1.9)
        sp = S.rng.uniform(1.6, 3.6)
        parts.append(Particle(cx + S.rng.uniform(-3, 3), gy - 6, math.cos(a) * sp, math.sin(a) * sp,
                              S.n, size=S.rng.uniform(1, 2.2)))
    for i, cv in enumerate(S.frames):
        t = i / (S.n - 1)
        # ground ripples
        for k in range(2):
            rt = seg(t, 0.1 + k * 0.2, 0.8 + k * 0.2)
            if 0 < rt < 1:
                cv.ring(cx, gy, 6 + rt * (S.w / 2 - 8), 1, S.pal[4 if rt < 0.5 else 3], squash=0.35)
        # crown
        if i < S.n * 0.55:
            ct = seg(t, 0, 0.55)
            h = math.sin(ct * math.pi) * 16
            for k in range(-3, 4):
                x = cx + k * (3 + ct * 3)
                top = gy - 4 - h * (1 - abs(k) / 4)
                cv.line(x, gy - 2, x + k * 0.7, top, S.pal[3], w=2)
                cv.px(x + k * 0.7, top - 1, S.pal[5])
            cv.ellipse(cx, gy - 2, 6 + ct * 6, 3, S.pal[2])
            if i < 2:
                cv.disc(cx, gy - 6, 6, S.pal[5])
        for p in parts:
            if p.alive and p.y < gy + 1:
                cv.disc(p.x, p.y, p.size * (1 - p.t * 0.5), S.pal[3 if p.t < 0.6 else 2])
                cv.px(p.x - 0.5, p.y - 0.5, S.pal[5])
        step(parts, gravity=0.42)


def explosion(S, puffs=10, smoke=True, embers=10):
    """Fire burst: white flash, expanding hot puffs, cool to smoke that rises, embers fall."""
    cx, cy = S.w / 2, S.h / 2 + 4
    R = min(S.w, S.h) / 2 - 4
    blobs = [(S.rng.uniform(0, TAU), S.rng.uniform(0.3, 1.0), S.rng.uniform(0.5, 1.0)) for _ in range(puffs)]
    emb = [Particle(cx, cy, math.cos(a) * s, math.sin(a) * s - 1.2, S.rng.randint(S.n // 2, S.n))
           for a, s in [(S.rng.uniform(0, TAU), S.rng.uniform(1.5, 3.2)) for _ in range(embers)]]
    for i, cv in enumerate(S.frames):
        t = i / (S.n - 1)
        if i == 0:
            cv.disc(cx, cy, R * 0.35, S.pal[5])
            cv.ring(cx, cy, R * 0.55, 1, S.pal[4])
            continue
        ex = out_cubic(seg(t, 0, 0.45))
        heat = 1 - seg(t, 0.1, 0.9)
        for (a, d, s) in sorted(blobs, key=lambda b: -b[1]):
            dist = d * R * 0.6 * ex
            rise = seg(t, 0.4, 1) * R * 0.5 * s if smoke else 0
            r = (R * 0.42 * s) * (0.5 + 0.6 * ex) * (1 - 0.5 * seg(t, 0.6, 1))
            puff(cv, cx + math.cos(a) * dist, cy + math.sin(a) * dist * 0.8 - rise, r, S.pal, heat * (1.1 - d * 0.3))
        if i < 4:
            cv.ring(cx, cy, R * (0.6 + i * 0.15), 1, S.pal[5 - i // 2])
        for p in emb:
            if p.alive:
                cv.px(p.x, p.y, S.pal[4 if p.t < 0.5 else 3])
        step(emb, gravity=0.18, drag=0.92)


def debris(S, chunks=9, dust=True):
    """Rock/ground hit: chunks fly up and bounce on the floor, dust puffs roll out."""
    cx, gy = S.w / 2, S.h - 10
    parts = [Particle(cx + S.rng.uniform(-4, 4), gy - 8, S.rng.uniform(-2.6, 2.6), S.rng.uniform(-4.2, -2),
                      S.n, size=S.rng.uniform(1.5, 3.2), kind=S.rng.randint(0, 3)) for _ in range(chunks)]
    dusts = [(S.rng.choice((-1, 1)) * S.rng.uniform(0.3, 1), S.rng.uniform(0.6, 1)) for _ in range(8)]
    for i, cv in enumerate(S.frames):
        t = i / (S.n - 1)
        if i < 3:
            cv.disc(cx, gy - 8, 7 - i * 2, S.pal[5 - i])
            for k in range(6):
                a = k * TAU / 6 + 0.4
                cv.line(cx + math.cos(a) * 5, gy - 8 + math.sin(a) * 5, cx + math.cos(a) * (10 + i * 4),
                        gy - 8 + math.sin(a) * (10 + i * 4), S.pal[4])
        if dust:
            for (d, s) in dusts:
                dt = out_quad(seg(t, 0.05, 1))
                x = cx + d * dt * S.w * 0.4
                r = (2 + s * 4) * (0.4 + dt) * (1 - seg(t, 0.7, 1) * 0.6)
                cv.disc(x, gy - r * 0.6 - dt * 3, r, S.pal[1 if t > 0.6 else 2], dither=t > 0.7)
        for p in parts:
            if p.age < p.life:
                s = p.size
                ang = p.age * 0.6 + p.kind
                pts = [(p.x + math.cos(ang + k * TAU / 4) * s, p.y + math.sin(ang + k * TAU / 4) * s) for k in range(4)]
                cv.poly(pts, S.pal[2])
                cv.px(pts[0][0], pts[0][1], S.pal[4])
                cv.px(p.x, p.y, S.pal[3])
        step(parts, gravity=0.38)
        for p in parts:
            if p.y > gy:
                p.y = gy
                p.vy *= -0.35
                p.vx *= 0.6


def slash(S, count=1, width=3, claw=False):
    """Crescent slash(es): whip across in 2 frames, white edge cools to the ramp, thins out."""
    cx, cy = S.w / 2, S.h / 2
    R = min(S.w, S.h) / 2 - 3
    for i, cv in enumerate(S.frames):
        t = i / (S.n - 1)
        for c in range(count):
            off = (c - (count - 1) / 2) * 9
            delay = c * 0.08 if not claw else c * 0.04
            lt = seg(t, delay, delay + 0.75)
            if lt <= 0 or lt >= 1:
                continue
            sweep = out_expo(seg(lt, 0, 0.25))
            thin = 1 - seg(lt, 0.3, 1)
            a0, a1 = -2.3, -2.3 + 2.6 * sweep
            tail = a0 + (a1 - a0) * seg(lt, 0.3, 1.0) ** 2
            steps = 70
            for k in range(steps + 1):
                a = tail + (a1 - tail) * k / steps
                frac = k / steps
                wk = max(0.0, width * thin * math.sin(frac * math.pi) * 1.4)
                for tt in range(int(math.ceil(wk)) + 1):
                    if claw:
                        x = cx + off + math.cos(a) * 3 * R / R + (frac - 0.5) * R * 1.6 * 0.9
                        y = cy + (frac - 0.5) * R * 1.6 + tt - off * 0.3
                    else:
                        rr = R - tt + off
                        x = cx + math.cos(a) * rr
                        y = cy + math.sin(a) * rr * 0.75
                    col = S.pal[5] if (tt == 0 and lt < 0.5) else S.pal[4] if tt <= 1 else S.pal[3] if tt <= 2 else S.pal[2]
                    cv.px(x, y, col)
        if 2 <= i <= 4:
            # glint and a couple of chips at the end of the stroke
            gx, gy = cx + math.cos(0.3) * R, cy + math.sin(0.3) * R * 0.75
            if claw:
                gx, gy = cx + R * 0.7, cy + R * 0.8
            cv.sparkle(gx, gy, 4 - (i - 2), S.pal[5])


# ------------------------------------------------------------------ areas and auras
def aura(S, kind="flame", ground=True):
    """Loop around a standing unit (feet at S.feet). Particles rise along the silhouette edge."""
    cx, fy = S.w / 2, S.feet
    K = 18
    seeds = [(S.rng.random(), S.rng.uniform(-1, 1), S.rng.random()) for _ in range(K)]
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        if ground:
            pr = (ph * 2) % 1.0
            cv.ring(cx, fy, 8 + pr * 16, 1, S.pal[4 if pr < 0.5 else 2], squash=0.35)
            cv.ring(cx, fy, 14, 1, S.pal[2], squash=0.35, gaps=6, phase=ph)
        for (u, side, sz) in seeds:
            p = (ph + u) % 1.0
            x = cx + side * (11 - p * 4) + math.sin((p * 2 + u) * TAU) * 1.5
            y = fy - 2 - p * (S.h * 0.75)
            if kind == "flame":
                y = fy - 2 - (p ** 1.4) * (S.h * 0.7)
                r = (1 - p) * 4.6 * (0.6 + sz * 0.6) + 0.5
                puff(cv, x, y, r, S.pal, 1.05 - p)
                if p < 0.5:
                    cv.px(x, y - r - 1, S.pal[4])
            elif kind == "spark":
                if (i + int(u * 7)) % 3 != 0:
                    pts = zigzag(S.rng, x, y, x + S.rng.uniform(-4, 4), y - 6, 3, 2)
                    for a, b in zip(pts, pts[1:]):
                        cv.line(a[0], a[1], b[0], b[1], S.pal[4 if p < 0.5 else 3])
            elif kind == "wisp":
                r = (1 - p) * 2.4 + 0.5
                cv.disc(x, y, r, S.pal[3])
                cv.disc(x, y + r + 1, r * 0.6, S.pal[2], dither=True)
                cv.px(x, y, S.pal[5])
            elif kind == "sparkle":
                if (int(p * 6) + int(u * 3)) % 2 == 0:
                    cv.sparkle(x, y, 1 + (1 - p) * 2, S.pal[4], S.pal[5])
            elif kind == "bubble":
                cv.ring(x, y, 1 + sz * 1.5 * (1 - p * 0.3), 1, S.pal[3])
                cv.px(x - 1, y - 1, S.pal[5])
            elif kind == "leaf":
                leaf(cv, x, y, (p + u) * TAU, 3, S.pal)
            elif kind == "line":
                cv.line(x, y, x, y + 5 + sz * 5, S.pal[4 if p < 0.4 else 3])
            elif kind == "hex":
                pass


def pillar(S, kind="flame"):
    """Column bursting up from the ground: base splash, jagged column, crown, then it collapses."""
    cx, gy = S.w / 2, S.h - 8
    Hmax = S.h - 18
    for i, cv in enumerate(S.frames):
        t = i / (S.n - 1)
        rise = out_back(seg(t, 0.05, 0.35)) if t < 0.35 else 1.0
        fall = seg(t, 0.65, 1.0)
        height = Hmax * clamp(rise) * (1 - in_quad(fall))
        w = 9 * (1 - fall * 0.7)
        cv.ellipse(cx, gy, 14 + rise * 4, 4, S.pal[1], dither=True)
        cv.ellipse(cx, gy, 10, 3, S.pal[2])
        if i == 0:
            cv.ring(cx, gy, 8, 1, S.pal[4], squash=0.35)
            continue
        for y in range(int(gy - height), int(gy)):
            k = (gy - y) / max(1, height)
            jag = math.sin(y * 0.7 + i * 1.9) * 1.6 + math.sin(y * 0.23 - i) * 1.2
            hw = w * (1 - k * 0.35) + jag * 0.6
            cv.line(cx - hw - 1, y, cx + hw + 1, y, S.pal[1], dither=True)
            cv.line(cx - hw, y, cx + hw, y, S.pal[2])
            cv.line(cx - hw * 0.6 + jag * 0.4, y, cx + hw * 0.5 + jag * 0.4, y, S.pal[3])
            cv.line(cx - hw * 0.2 + jag * 0.3, y, cx + hw * 0.15 + jag * 0.3, y, S.pal[5] if t < 0.6 else S.pal[4])
        top = gy - height
        if height > 4:
            for k in range(5):
                a = -math.pi / 2 + (k - 2) * 0.45
                d = 5 + (i % 3) * 2
                if kind == "flame":
                    puff(cv, cx + math.cos(a) * d, top + math.sin(a) * d, 3, S.pal, 0.8 - fall)
                else:
                    cv.disc(cx + math.cos(a) * d, top + math.sin(a) * d, 2, S.pal[3])
                    cv.px(cx + math.cos(a) * (d + 3), top + math.sin(a) * (d + 3), S.pal[4])
        if 1 <= i <= 4:
            cv.ring(cx, gy, 10 + i * 5, 1, S.pal[4], squash=0.35)


def vortex(S, kind="petal", rings=6):
    """Spiral of stacked squashed rings (a cheap 3D tornado) with orbiting pieces. Loop."""
    cx, gy = S.w / 2, S.h - 8
    Ht = S.h - 16
    K = 12
    seeds = [(S.rng.random(), S.rng.random()) for _ in range(K)]
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        for k in range(rings):
            f = (k + ph) / rings
            y = gy - f * Ht
            r = 4 + f * (S.w / 2 - 8)
            sway = math.sin((f * 2 + ph) * TAU) * 2
            col = S.pal[4] if k % 2 == 0 else S.pal[3]
            cv.ring(cx + sway, y, r, 1, col, squash=0.28, gaps=2 if kind == "wind" else 0, phase=ph * 2 + f)
        for (u, v) in seeds:
            f = (u + ph * 0.5) % 1.0
            a = (v + ph * 2) * TAU
            r = 4 + f * (S.w / 2 - 8)
            x = cx + math.cos(a) * r
            y = gy - f * Ht + math.sin(a) * r * 0.28
            if kind == "petal":
                leaf(cv, x, y, a * 2, 2, S.pal)
            elif kind == "water":
                cv.disc(x, y, 1.4, S.pal[4])
            elif kind == "wind":
                cv.line(x, y, x - math.sin(a) * 4, y + math.cos(a) * 1, S.pal[4])
            elif kind == "snow":
                cv.sparkle(x, y, 1, S.pal[4], S.pal[5])


def pulse_rings(S, rings=3, thick=2, squash=1.0, loop=True, dark_center=False):
    """Concentric rings growing outwards (psychic/dark pulse/roar). Loop or one-shot."""
    cx, cy = S.w / 2, S.h / 2 if squash == 1.0 else S.h - 14
    R = min(S.w / 2, S.h / 2 / squash) - 2
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        if not loop:
            ph = i / (S.n - 1) * 0.999
        for k in range(rings):
            p = (ph + k / rings) % 1.0 if loop else clamp(ph * 1.5 - k * 0.18)
            if not loop and (p <= 0 or p >= 1):
                continue
            r = 4 + out_quad(p) * (R - 4)
            col = S.pal[5] if p < 0.15 else S.pal[4] if p < 0.45 else S.pal[3] if p < 0.75 else S.pal[2]
            cv.ring(cx, cy, r, thick if p < 0.6 else 1, col, squash=squash, dither=p > 0.85)
        if not loop and i > S.n * 0.6:
            continue
        if dark_center:
            cv.disc(cx, cy, 3 + (i % 2), S.pal[0])
            cv.ring(cx, cy, 5, 1, S.pal[3])
        else:
            cv.disc(cx, cy, 2 + (i % 2), S.pal[4])


def cloud(S, puffs=9):
    """Poison/gas cloud area loop: lumpy dithered puffs that churn, bubbles pop at the rim."""
    cx, cy = S.w / 2, S.h / 2 + 6
    blobs = [(S.rng.uniform(-1, 1), S.rng.uniform(-0.6, 0.6), S.rng.uniform(5, 10), S.rng.random()) for _ in range(puffs)]
    bub = [(S.rng.uniform(-1, 1), S.rng.random()) for _ in range(7)]
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        for (bx, by, r, u) in blobs:
            wob = math.sin((ph + u) * TAU)
            x = cx + bx * (S.w / 2 - 14) + wob * 2
            y = cy + by * (S.h / 2 - 14) + math.cos((ph + u) * TAU) * 1.5
            rr = r + wob * 1.2
            cv.disc(x, y, rr + 2, S.pal[1], dither=True, under=True)
            cv.disc(x, y, rr, S.pal[2])
            cv.disc(x - rr * 0.25, y - rr * 0.3, rr * 0.55, S.pal[3])
        for (bx, u) in bub:
            p = (ph + u) % 1.0
            x = cx + bx * (S.w / 2 - 12)
            y = cy + 4 - p * (S.h / 2)
            if p < 0.8:
                cv.ring(x, y, 1 + p * 2.5, 1, S.pal[4])
            else:
                for k in range(4):
                    a = k * TAU / 4 + 0.78
                    cv.px(x + math.cos(a) * 4, y + math.sin(a) * 4, S.pal[4])


def rain(S, kind="snow", density=26, wind=0.6):
    """Area weather loop: snow/hail/rain/leaves falling diagonally over a ground ellipse."""
    cx, gy = S.w / 2, S.h - 10
    seeds = [(S.rng.random(), S.rng.random(), S.rng.random()) for _ in range(density)]
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        cv.ellipse(cx, gy, S.w / 2 - 6, 6, S.pal[1], dither=True)
        cv.ring(cx, gy, S.w / 2 - 6, 1, S.pal[3], squash=6 / (S.w / 2 - 6), gaps=8, phase=ph)
        for (u, v, s) in seeds:
            p = (ph + v) % 1.0
            x = (u * (S.w + 20) - 10 + p * wind * 30) % S.w
            y = p * (gy + 4) - 4
            if kind == "snow":
                if s > 0.6:
                    cv.sparkle(x, y, 1, S.pal[4], S.pal[5])
                else:
                    cv.px(x, y, S.pal[5 if s > 0.3 else 3])
            elif kind == "rain":
                cv.line(x, y, x - wind * 3, y - 5, S.pal[3])
            elif kind == "hail":
                shard(cv, x, y, 1.2, 5, 1.2, S.pal)
            elif kind == "sand":
                cv.line(x, y, x - 4, y - 1, S.pal[3 if s > 0.5 else 2])
        # wind streaks
        for k in range(3):
            p = (ph + k / 3) % 1.0
            y = 10 + k * (S.h / 4)
            cv.line(p * S.w - 14, y, p * S.w, y + 3, S.pal[4], dither=True)


def cracks(S, n_cracks=6):
    """Ground layer: cracks race out from the centre, chunks heave, dust rises, then settle."""
    cx, cy = S.w / 2, S.h / 2 + 6
    paths = []
    for k in range(n_cracks):
        a = k * TAU / n_cracks + S.rng.uniform(-0.3, 0.3)
        L = S.rng.uniform(0.6, 1.0) * (S.w / 2 - 6)
        pts = [(cx, cy)]
        for j in range(1, 6):
            d = L * j / 5
            pts.append((cx + math.cos(a) * d + S.rng.uniform(-2, 2), cy + math.sin(a) * d * 0.45 + S.rng.uniform(-1, 1)))
        paths.append(pts)
    rocks = [Particle(cx + S.rng.uniform(-S.w / 3, S.w / 3), cy + S.rng.uniform(-6, 6), 0, S.rng.uniform(-2.6, -1.2),
                      S.n, size=S.rng.uniform(1.5, 2.8), kind=k) for k in range(7)]
    for i, cv in enumerate(S.frames):
        t = i / (S.n - 1)
        grow = out_cubic(seg(t, 0, 0.4))
        fade = seg(t, 0.75, 1)
        for pts in paths:
            m = int(round(grow * (len(pts) - 1)))
            for a, b in zip(pts[:m], pts[1:m + 1]):
                cv.line(a[0], a[1] + 1, b[0], b[1] + 1, S.pal[1])
                cv.line(a[0], a[1], b[0], b[1], S.pal[0] if fade < 0.5 else S.pal[1], w=2)
                if t < 0.5:
                    cv.px((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 - 1, S.pal[4])
        if t < 0.6:
            cv.ring(cx, cy, 4 + grow * (S.w / 2 - 6), 1, S.pal[3], squash=0.45, dither=t > 0.3)
        for p in rocks:
            if i >= 2:
                if p.y < cy + 8 or p.vy < 0:
                    pts = [(p.x + math.cos(p.kind + k * TAU / 4 + p.age * 0.4) * p.size,
                            p.y + math.sin(p.kind + k * TAU / 4 + p.age * 0.4) * p.size) for k in range(4)]
                    cv.poly(pts, S.pal[2])
                    cv.px(p.x, p.y - 1, S.pal[4])
                cv.disc(p.x, p.y + 2, p.size + 1 - fade * 2, S.pal[2], dither=True, under=True)
        if i >= 2:
            step(rocks, gravity=0.3)


def spikes(S, count=5, kind="rock"):
    """Spikes stab up from the ground one after another left->right, hold, then sink."""
    gy = S.h - 8
    xs = [12 + k * (S.w - 24) / max(1, count - 1) for k in range(count)]
    hs = [S.rng.uniform(0.6, 1.0) * (S.h - 22) for _ in range(count)]
    for i, cv in enumerate(S.frames):
        t = i / (S.n - 1)
        for k, (x, h) in enumerate(zip(xs, hs)):
            st = seg(t, k * 0.07, k * 0.07 + 0.15)
            sink = seg(t, 0.7, 1.0)
            hh = h * out_back(st) * (1 - in_quad(sink)) if st > 0 else 0
            w = 4 + h / 10
            cv.ellipse(x, gy, w + 4, 2, S.pal[1], dither=True)
            if hh < 1:
                continue
            top = gy - hh
            cv.poly([(x - w, gy), (x, top), (x + w, gy)], S.pal[2])
            cv.poly([(x - w * 0.15, gy), (x, top), (x + w, gy)], S.pal[3] if kind != "ice" else S.pal[4])
            cv.line(x, top, x - w * 0.3, gy - 2, S.pal[4] if kind != "ice" else S.pal[5])
            cv.px(x, top, S.pal[5])
            if 0 < st < 1:
                for j in range(3):
                    cv.px(x + (j - 1) * (w + 2), gy - 3 - j % 2 * 2, S.pal[3])


def swarm(S, count=16):
    """Loop: tiny buzzing dots orbiting a centre on noisy ellipses."""
    cx, cy = S.w / 2, S.h / 2
    seeds = [(S.rng.random(), S.rng.uniform(8, S.w / 2 - 4), S.rng.uniform(0.4, 0.9), S.rng.choice((1, 2))) for _ in range(count)]
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        for (u, r, sq, sp) in seeds:
            a = (u + ph * sp) * TAU
            x = cx + math.cos(a) * r
            y = cy + math.sin(a) * r * sq + math.sin(a * 3) * 2
            x2 = cx + math.cos(a - 0.25) * r
            y2 = cy + math.sin(a - 0.25) * r * sq
            cv.line(x2, y2, x, y, S.pal[2], dither=True)
            cv.px(x, y, S.pal[1])
            cv.px(x + 1, y, S.pal[3])
            cv.px(x, y - 1, S.pal[5] if (i + int(u * 9)) % 2 else S.pal[4])  # wing flicker


def ring_shield(S, hexes=True):
    """Loop: dome bubble over the unit with a hex lattice shimmer and a sweeping highlight."""
    cx, fy = S.w / 2, S.feet
    R = S.w / 2 - 4
    cy = fy - R * 0.55
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        cv.ellipse(cx, fy, R, R * 0.3, S.pal[1], dither=True)
        for y in range(int(cy - R), int(fy) + 1):
            for x in range(int(cx - R), int(cx + R) + 1):
                d = math.hypot((x - cx) / R, (y - cy) / (R * 0.95))
                if 0.9 < d <= 1.0:
                    cv.px(x, y, S.pal[3])
                elif hexes and d <= 0.9:
                    diag = ((x - cx) + (y - cy) * 0.8) / (2 * R) + 0.5  # 0..1 across the dome
                    sweep = (ph * 1.6) % 1.6 - 0.3
                    if abs(diag - sweep) < 0.06 and (x + y) % 2 == 0:
                        cv.px(x, y, S.pal[4])
                    elif d > 0.45 and x % 4 == (y // 4 % 2) * 2 and y % 4 == 0:
                        cv.px(x, y, S.pal[2])
        a = ph * TAU
        cv.ring(cx, cy, R - 3, 1, S.pal[5], gaps=1, phase=ph)
        cv.sparkle(cx - R * 0.5, cy - R * 0.5, 2 + (i % 2), S.pal[5])
