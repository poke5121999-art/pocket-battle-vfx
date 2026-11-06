"""Generic battle effects (hit spark, crit, status loops, level up ...) and unit animations."""
import math

from .core import TAU, Particle, clamp, in_quad, out_back, out_cubic, out_quad, seg, step
from .creature import draw_creature
from .fxlib import arrow, burst, glow_disc, heart, puff, shard, zigzag, bolt_path


# ------------------------------------------------------------------ hits
def hit_spark(S):
    burst(S, rays=6, ring=False, sparks=8, star=True)


def crit_hit(S):
    """Bigger, two-beat impact: white frame-0 block, jagged starburst overshoot, broken ring,
    long rays and a second smaller pop."""
    cx, cy = S.w / 2, S.h / 2
    R = S.w / 2 - 3
    parts = [Particle(cx, cy, math.cos(a) * s, math.sin(a) * s, S.rng.randint(8, S.n))
             for a, s in [(S.rng.uniform(0, TAU), S.rng.uniform(2.5, 4.5)) for _ in range(16)]]
    for i, cv in enumerate(S.frames):
        t = i / (S.n - 1)
        if i == 0:
            cv.disc(cx, cy, R * 0.55, S.pal[5])
            continue
        if i <= 5:
            s = R * (0.95 if i == 1 else 0.8 if i == 2 else 0.6 * (6 - i) / 3)
            pts = []
            for k in range(14):
                a = k * TAU / 14
                rr = s * (1.0 if k % 2 == 0 else 0.45) * (1.1 if k % 4 == 0 else 1)
                pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
            cv.poly(pts, S.pal[3] if i > 2 else S.pal[4])
            cv.disc(cx, cy, s * 0.4, S.pal[5])
        if 2 <= i <= 9:
            rt = seg(i, 2, 9)
            cv.ring(cx, cy, R * 0.5 + rt * R * 0.5, 2 if rt < 0.5 else 1, S.pal[4], gaps=6, phase=rt * 0.3)
        if 1 <= i <= 5:
            for k in range(12):
                a = k * TAU / 12 + 0.13
                r0 = R * (0.35 + i * 0.1)
                cv.line(cx + math.cos(a) * r0, cy + math.sin(a) * r0, cx + math.cos(a) * (r0 + R * 0.35),
                        cy + math.sin(a) * (r0 + R * 0.35), S.pal[5])
        if 6 <= i <= 8:
            cv.sparkle(cx + 7, cy - 6, 9 - i, S.pal[5])
        for p in parts:
            if p.alive and i > 1:
                c = S.pal[5] if p.t < 0.3 else S.pal[4] if p.t < 0.6 else S.pal[3]
                cv.line(p.x, p.y, p.x - p.vx, p.y - p.vy, c)
        if i > 1:
            step(parts, drag=0.85)


def cutin_lines(S):
    """Full-screen crit/finisher cut-in: dark plate, white radial speed lines rushing inwards,
    one white flash frame. Opaque on purpose (it replaces the screen for a few frames)."""
    cx, cy = S.w / 2, S.h / 2
    lines = [(S.rng.uniform(0, TAU), S.rng.uniform(0.25, 0.55), S.rng.randint(1, 2)) for _ in range(48)]
    R = math.hypot(S.w, S.h) / 2 + 4
    for i, cv in enumerate(S.frames):
        t = i / (S.n - 1)
        if i == 0:
            cv.rect(0, 0, S.w - 1, S.h - 1, S.pal[5])
            continue
        cv.rect(0, 0, S.w - 1, S.h - 1, S.pal[0])
        for (a, inner, w) in lines:
            a2 = a + i * 0.04
            r0 = R * (inner + 0.06 * ((i * 3 + int(a * 10)) % 3))
            cv.line(cx + math.cos(a2) * r0, cy + math.sin(a2) * r0 * 0.75, cx + math.cos(a2) * R,
                    cy + math.sin(a2) * R * 0.75, S.pal[5] if w == 1 else S.pal[3], w=w)
        if i >= S.n - 2:
            cv.rect(0, 0, S.w - 1, S.h - 1, S.pal[5], dither=True)


def miss(S):
    """Dodge read: the unit's after-image slides away in two ghosts and MISS pops above."""
    from .core import Canvas
    cx, fy = S.w / 2, S.feet
    for i, cv in enumerate(S.frames):
        t = i / (S.n - 1)
        if t < 0.6:
            for k, off in enumerate((-12, -6)):
                g = out_cubic(seg(t, 0, 0.4))
                ghost = Canvas(S.w, S.h)
                draw_creature(ghost, int(cx + off * g), int(fy), flip=True, mono=S.pal[2 + k])
                for yy in range(S.h):
                    for xx in range(S.w):
                        if ghost.pa[xx, yy][3] and (xx + yy + k + i) % 2 == 0:
                            cv.px(xx, yy, ghost.pa[xx, yy])
            for k in range(3):
                y = fy - 22 + k * 8
                cv.line(cx + 4, y, cx + 14 - t * 10, y, S.pal[4])
        pop = out_back(seg(t, 0.1, 0.35))
        y = fy - 34 - pop * 6 - seg(t, 0.6, 1) * 4
        if t < 0.92:
            cv.text("MISS", cx, y, S.pal[5], outline=S.pal[0])


def heal(S):
    """Loop: green plus signs and sparkles rise around the unit, a soft ground ring pulses."""
    cx, fy = S.w / 2, S.feet
    seeds = [(S.rng.random(), S.rng.uniform(-1, 1), S.rng.random()) for _ in range(10)]
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        pr = (ph * 2) % 1.0
        cv.ring(cx, fy, 6 + pr * 14, 1, S.pal[4 if pr < 0.5 else 2], squash=0.35)
        for (u, side, s) in seeds:
            p = (ph + u) % 1.0
            x = cx + side * 13
            y = fy - 4 - p * (S.h - 16)
            if s > 0.45:
                size = 2 if p < 0.7 else 1
                cv.rect(x - size, y, x + size, y, S.pal[4])
                cv.rect(x, y - size, x, y + size, S.pal[4])
                cv.px(x, y, S.pal[5])
                cv.outline if False else None
            else:
                cv.sparkle(x, y, 1 if p > 0.5 else 2, S.pal[3], S.pal[5])
        cv.disc(cx, fy - 16, 2 + (i % 2), S.pal[3], dither=True)


def stat_arrows(S, up=True):
    """Loop: chevron arrows stream up (stat up) or down (stat down) through the unit, with a
    tinted ring at the feet."""
    cx, fy = S.w / 2, S.feet
    cols = [(-10, 0.0), (0, 0.35), (10, 0.7), (-5, 0.55), (6, 0.15)]
    span = S.h - 14
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        cv.ring(cx, fy, 15, 1, S.pal[3], squash=0.35, gaps=5, phase=ph if up else -ph)
        for (dx, u) in cols:
            p = (ph + u) % 1.0
            y = fy - 6 - p * span if up else fy - span + p * span
            arrow(cv, cx + dx, y, up, S.pal, size=3 if dx % 10 else 4)
        for k in range(4):
            p = (ph * 2 + k / 4) % 1.0
            y = fy - p * span if up else fy - span + p * span
            cv.line(cx - 14 + k * 9, y, cx - 14 + k * 9, y + (4 if up else -4), S.pal[4])


# ------------------------------------------------------------------ status loops
def st_burn(S):
    cx, fy = S.w / 2, S.feet
    flames = [(-8, 0.0), (6, 0.33), (-1, 0.66), (10, 0.5)]
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        for (dx, u) in flames:
            p = (ph + u) % 1.0
            y = fy - 10 - p * 22
            r = 4.4 * (1 - p) + 0.8
            puff(cv, cx + dx + math.sin(p * 9) * 1.2, y, r, S.pal, 1.05 - p)
            if p < 0.4:
                cv.px(cx + dx, y - r - 1, S.pal[4])
        if i % 4 < 2:
            cv.px(cx - 4, fy - 30 - (i % 2), S.pal[3])


def st_poison(S):
    cx, fy = S.w / 2, S.feet
    bub = [(-9, 0.0, 2), (4, 0.25, 1), (9, 0.5, 2), (-3, 0.75, 1), (0, 0.4, 3)]
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        for (dx, u, s) in bub:
            p = (ph + u) % 1.0
            y = fy - 6 - p * 30
            if p < 0.85:
                cv.disc(cx + dx, y, s, S.pal[2])
                cv.ring(cx + dx, y, s + 0.6, 1, S.pal[3])
                cv.px(cx + dx - 1, y - 1, S.pal[5])
            else:
                for k in range(4):
                    a = k * TAU / 4 + 0.78
                    cv.px(cx + dx + math.cos(a) * (s + 2), y + math.sin(a) * (s + 2), S.pal[3])
        # sickly drip on the ground
        cv.ellipse(cx, fy, 10, 2, S.pal[1], dither=True)


def st_paralysis(S):
    cx, fy = S.w / 2, S.feet
    for i, cv in enumerate(S.frames):
        if i % 3 == 2:
            continue  # off beats make it flicker
        for k in range(2 + (i % 2)):
            x0 = cx + S.rng.uniform(-14, 14)
            y0 = fy - S.rng.uniform(8, 30)
            pts = zigzag(S.rng, x0, y0, x0 + S.rng.uniform(-8, 8), y0 + S.rng.uniform(-8, 8), 3, 2.5)
            bolt_path(cv, pts, S.pal, w=1)
        cv.sparkle(cx + S.rng.uniform(-12, 12), fy - S.rng.uniform(20, 34), 2, S.pal[4], S.pal[5])


def st_sleep(S):
    cx, fy = S.w / 2, S.feet
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        for k in range(3):
            p = (ph + k / 3) % 1.0
            x = cx + 6 + p * 12 + math.sin(p * TAU) * 2
            y = fy - 26 - p * 22
            sc = 1 if p < 0.55 else 2
            if p < 0.92:
                cv.text("Z", x, y, S.pal[4 if p < 0.6 else 5], outline=S.pal[0], scale=sc)


def st_freeze(S):
    """Loop: ice crust over the unit's silhouette area with glints travelling across."""
    cx, fy = S.w / 2, S.feet
    crystals = [(-11, 0, 9, 3.0), (-6, -4, 14, 2.6), (2, -2, 16, 3.0), (9, 0, 11, 2.6), (-2, 0, 8, 2.2),
                (12, -6, 8, 2.0), (-13, -8, 7, 2.0)]
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        cv.ellipse(cx, fy, 16, 3, S.pal[2])
        cv.ellipse(cx, fy - 1, 13, 2, S.pal[3])
        for (dx, dy, h, w) in crystals:
            shard(cv, cx + dx, fy - h * 0.5 + dy, -math.pi / 2 + dx * 0.02, h, w, S.pal)
        gx = cx - 16 + ((ph * 2) % 1.0) * 32
        for y in range(int(fy - 18), int(fy)):
            if 0 <= gx < S.w and cv.get(int(gx + (fy - y) * 0.4), y)[3]:
                cv.px(gx + (fy - y) * 0.4, y, S.pal[5])
        if i % 4 == 0:
            cv.sparkle(cx + 8, fy - 18, 2, S.pal[5])


def st_confusion(S):
    """Loop: three little stars orbit above the head on a squashed ellipse."""
    cx, fy = S.w / 2, S.feet
    hy = fy - 34
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        cv.ring(cx, hy, 14, 1, S.pal[2], squash=0.3, dither=True)
        for k in range(3):
            a = (ph + k / 3) * TAU
            x = cx + math.cos(a) * 14
            y = hy + math.sin(a) * 4.2
            front = math.sin(a) > 0
            cv.sparkle(x, y, 3 if front else 2, S.pal[4 if front else 3], S.pal[5])
            if front:
                cv.disc(x, y, 1, S.pal[5])


# ------------------------------------------------------------------ transitions
def faint_vanish(S):
    """Dissolve puff: the silhouette area breaks into rising grey motes and a ground dust ring."""
    cx, fy = S.w / 2, S.feet
    motes = [Particle(cx + S.rng.uniform(-10, 10), fy - S.rng.uniform(2, 24), S.rng.uniform(-0.3, 0.3),
                      S.rng.uniform(-1.2, -0.4), S.rng.randint(S.n // 2, S.n), size=S.rng.uniform(0.6, 1.8),
                      kind=S.rng.randint(0, 9)) for _ in range(40)]
    for i, cv in enumerate(S.frames):
        t = i / (S.n - 1)
        rt = out_cubic(seg(t, 0, 0.6))
        if t < 0.7:
            cv.ring(cx, fy, 6 + rt * 20, 1, S.pal[3], squash=0.3, dither=t > 0.4)
        for k in range(5):
            dt = out_quad(seg(t, 0, 0.8))
            for side in (-1, 1):
                x = cx + side * (4 + dt * 18 + k * 2)
                r = (3 - k * 0.4) * (1 - seg(t, 0.5, 1))
                if r > 0.4:
                    cv.disc(x, fy - 2 - k, r, S.pal[2], dither=t > 0.5)
        for p in motes:
            if p.alive and p.age >= p.kind * 0.4:
                cv.disc(p.x, p.y, p.size * (1 - p.t), S.pal[4 if p.t < 0.3 else 3])
        step(motes)


def level_up(S):
    """Gold column of light, rising sparkles, chevrons and an LV UP stamp that bounces in."""
    cx, fy = S.w / 2, S.feet
    sp = [(S.rng.uniform(-14, 14), S.rng.random()) for _ in range(14)]
    for i, cv in enumerate(S.frames):
        t = i / (S.n - 1)
        col = out_back(seg(t, 0, 0.25)) * (1 - seg(t, 0.75, 1))
        w = 12 * clamp(col)
        if w > 0.5:
            for k, (fx, c) in enumerate(((-1.0, 2), (-0.55, 3), (0.55, 3), (1.0, 2))):
                x = cx + fx * w
                for y in range(int((i * 3 + k * 5) % 6), int(fy) - 2, 6):
                    cv.line(x, y, x, y + 3, S.pal[c])
        cv.ring(cx, fy, 6 + out_cubic(seg(t, 0, 0.5)) * 18, 1, S.pal[4], squash=0.35)
        for (dx, u) in sp:
            p = (t * 1.6 + u) % 1.0
            cv.sparkle(cx + dx, fy - p * (S.h - 10), 2 if p < 0.5 else 1, S.pal[4], S.pal[5])
        if 0.15 < t < 0.85:
            arrow(cv, cx, fy - 14 - seg(t, 0.15, 0.85) * 10, True, S.pal, size=5)
        pop = out_back(seg(t, 0.25, 0.45))
        if t > 0.25:
            cv.text("LV UP", cx, 4 + (1 - pop) * 4, S.pal[5], outline=S.pal[0])


def evolve_glow(S):
    """White silhouette pulse: the body area flashes white in quickening beats inside a ring of
    light rays, then one big flash."""
    cx, fy = S.w / 2, S.feet
    for i, cv in enumerate(S.frames):
        t = i / (S.n - 1)
        beat = math.sin((t * t * 10) * math.pi)
        for k in range(10):
            a = k * TAU / 10 + t * 2
            r0, r1 = 18, 18 + 6 + beat * 4
            cv.line(cx + math.cos(a) * r0, fy - 18 + math.sin(a) * r0, cx + math.cos(a) * r1,
                    fy - 18 + math.sin(a) * r1, S.pal[4] if beat > 0 else S.pal[3])
        if beat > 0.2 or t > 0.85:
            draw_creature(cv, int(cx), int(fy), mono=S.pal[5])
            cv.disc(cx, fy - 18, 16, S.pal[4], dither=True, under=True)
        else:
            draw_creature(cv, int(cx), int(fy), mono=S.pal[3])
        if t > 0.88:
            cv.disc(cx, fy - 18, 26, S.pal[5], dither=(i % 2 == 0))


def recall_beam(S):
    """Red capture/recall beam: thin line appears full length in one frame, the unit shrinks into
    a red silhouette and is pulled up the beam, a ring closes."""
    cx, fy = S.w / 2, S.feet
    for i, cv in enumerate(S.frames):
        t = i / (S.n - 1)
        bw = 1 + (1 if 0.1 < t < 0.8 else 0)
        if t < 0.9:
            cv.line(cx, 0, cx, fy - 16, S.pal[3], w=bw + 2, dither=True)
            cv.line(cx, 0, cx, fy - 16, S.pal[4], w=bw)
            cv.line(cx, 0, cx, fy - 16, S.pal[5])
        sh = 1 - in_quad(seg(t, 0.2, 0.75))
        if sh > 0.1:
            lift = seg(t, 0.4, 0.8) * 20
            draw_creature(cv, int(cx), int(fy - lift), sx=sh, sy=sh, mono=S.pal[3] if t > 0.15 else None)
        rt = seg(t, 0.6, 1)
        if 0 < rt < 1:
            cv.ring(cx, fy - 22, 14 * (1 - rt) + 1, 1, S.pal[5])
        if 0.7 < t < 0.95:
            cv.sparkle(cx, fy - 30, 3, S.pal[5])


def send_out(S):
    """Send-out burst: white flash ring on the floor, sparkles, the unit pops in with a stretch."""
    cx, fy = S.w / 2, S.feet
    for i, cv in enumerate(S.frames):
        t = i / (S.n - 1)
        rt = out_cubic(seg(t, 0, 0.5))
        cv.ring(cx, fy, 4 + rt * 22, 2 if rt < 0.5 else 1, S.pal[5 if rt < 0.3 else 4], squash=0.35)
        if t < 0.3:
            cv.disc(cx, fy - 14, 10 * (1 - t * 2.5), S.pal[5])
        for k in range(8):
            a = k * TAU / 8 + 0.4
            d = 6 + rt * 20
            if t < 0.7:
                cv.sparkle(cx + math.cos(a) * d, fy - 14 + math.sin(a) * d * 0.8, 2 if t < 0.4 else 1, S.pal[4], S.pal[5])


def charge_up(S):
    """Loop: generic wind-up gather; particles stream inwards to a pulsing core above the unit."""
    cx, cy = S.w / 2, S.h / 2
    seeds = [(S.rng.uniform(0, TAU), S.rng.random()) for _ in range(14)]
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        for (a, u) in seeds:
            p = (ph + u) % 1.0
            d = (1 - out_quad(p)) * (S.w / 2 - 4) + 3
            x, y = cx + math.cos(a) * d, cy + math.sin(a) * d
            cv.line(x, y, x + math.cos(a) * 3, y + math.sin(a) * 3, S.pal[4 if p > 0.5 else 3])
        glow_disc(cv, cx, cy, 3 + (i % 2), S.pal)
        cv.ring(cx, cy, 9 - (i % 4) * 2 + 4, 1, S.pal[4], dither=True)


def fairy_burst(S):
    burst(S, rays=6, ring=True, sparks=10, star=True, spark_kind="heart", gravity=0.05)


# ------------------------------------------------------------------ unit animations
def unit_idle(S):
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        b = math.sin(ph * TAU)
        draw_creature(cv, S.w // 2, S.feet, sx=1 + 0.05 * b, sy=1 - 0.06 * b, eye=(i != 2))


def unit_lunge(S):
    """Anticipation lean back (squash) -> dash forward (stretch, after-image) -> hold -> return."""
    x0 = 20
    keys = [(0.0, 0, 1.0, 1.0), (0.25, -5, 1.15, 0.85), (0.38, 26, 0.85, 1.12), (0.5, 30, 1.05, 0.95),
            (0.66, 30, 1.0, 1.0), (1.0, 0, 1.0, 1.0)]
    for i, cv in enumerate(S.frames):
        t = i / (S.n - 1)
        for (ta, xa, sxa, sya), (tb, xb, sxb, syb) in zip(keys, keys[1:]):
            if ta <= t <= tb:
                u = (t - ta) / (tb - ta)
                u = out_cubic(u) if xb > xa else u
                x, sx, sy = xa + (xb - xa) * u, sxa + (sxb - sxa) * u, sya + (syb - sya) * u
                break
        if 0.3 < t < 0.5:
            draw_creature(cv, x0 + int(x) - 10, S.feet, sx=sx, sy=sy, mono=(150, 148, 170, 255))
        draw_creature(cv, x0 + int(x), S.feet, sx=sx, sy=sy, lean=2 if x > 10 else 0)


def unit_recoil(S):
    """Hit: white flash frames, knockback with hit-stop hold, blink, settle."""
    cx = S.w // 2
    for i, cv in enumerate(S.frames):
        t = i / (S.n - 1)
        kb = out_quad(seg(t, 0.12, 0.35)) * 7 * (1 - seg(t, 0.5, 1))
        shake = (2 if i % 2 else -2) if 1 <= i <= 3 else 0
        flash = (255, 255, 255, 255) if i in (0, 1) else None
        if i in (5, 7):
            continue  # blink
        draw_creature(cv, cx + int(kb) + shake, S.feet, sx=0.92 if i < 3 else 1.0, sy=1.06 if i < 3 else 1.0,
                      lean=-2 if i < 5 else 0, flash=flash)


def unit_faint(S):
    """Faint: stagger, tip and drop flat, then dither out."""
    cx = S.w // 2
    for i, cv in enumerate(S.frames):
        t = i / (S.n - 1)
        sy = 1 - out_quad(seg(t, 0.2, 0.55)) * 0.55
        sx = 1 + seg(t, 0.2, 0.55) * 0.25
        drop = 0
        if t < 0.2:
            drop = 0
        tmp_feet = S.feet + drop
        if t < 0.85:
            draw_creature(cv, cx - int(seg(t, 0, 0.2) * 3), tmp_feet, sx=sx, sy=sy, eye=t < 0.2)
        fade = seg(t, 0.6, 1.0)
        if fade > 0:
            for y in range(S.h):
                for x in range(S.w):
                    if cv.get(x, y)[3] and ((x * 7 + y * 13) % 10) / 10 < fade:
                        cv.pa[x, y] = (0, 0, 0, 0)
        if 0.25 < t < 0.6:
            cv.ellipse(cx, S.feet, 12, 2, (120, 116, 132, 255), dither=True)
