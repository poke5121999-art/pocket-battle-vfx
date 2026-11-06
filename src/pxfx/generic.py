"""Generic battle effects (hit spark, crit, status loops, level up ...) and unit animations."""
import math

from .core import TAU, Particle, clamp, in_quad, out_back, out_cubic, out_quad, seg, step
from .creature import draw_creature
from .core import bayer
from .fxlib import arrow, burst, glow_disc, heart, puff, shard, zigzag, bolt_path, flame_tongue, spray, particles_draw
from .palettes import ramp


# ------------------------------------------------------------------ hits
def hit_spark(S):
    burst(S, rays=6, ring=True, sparks=10, star=True, core_r=6)


def crit_hit(S):
    """Two-beat crit: the big burst, then a second smaller star pops off-centre with fresh sparks."""
    burst(S, rays=12, ring=True, sparks=20, star=True, core_r=S.w * 0.2, gravity=0.04)
    cx, cy = S.w / 2 + 9, S.h / 2 - 8
    extra = spray(S.rng, 10, cx, cy, (1.5, 3.2), (4, 7), size=(1, 2))
    for i, cv in enumerate(S.frames):
        if 5 <= i <= 8:
            k = i - 5
            cv.glow(cx, cy, 2, 12 - k * 2, S.pal[3], density=0.6)
            cv.star(cx, cy, 11 - k * 2.5, 0.3, 4, S.pal, lo=2, rot=0.3)
        if i >= 5:
            particles_draw(cv, extra, S.pal, "spark")
            from .core import step as _st
            _st(extra, gravity=0.1, drag=0.88)


def cutin_lines(S):
    """Full-screen crit/finisher cut-in plate: white flash with radial streaks, then a dark plate with a
    dithered vignette and white speed lines rushing inward, dithering out at the end. Opaque on purpose."""
    cx, cy = S.w / 2, S.h / 2
    lines = [(S.rng.uniform(0, TAU), S.rng.uniform(0.25, 0.55), S.rng.randint(1, 3)) for _ in range(48)]
    R = math.hypot(S.w, S.h) / 2 + 4
    for i, cv in enumerate(S.frames):
        if i == 0:
            cv.rect(0, 0, S.w - 1, S.h - 1, S.pal[5])
            for (a, inner, w) in lines[::3]:
                cv.line(cx + math.cos(a) * R * 0.3, cy + math.sin(a) * R * 0.22, cx + math.cos(a) * R,
                        cy + math.sin(a) * R * 0.75, S.pal[4 if w < 2 else 3 if w < 3 else 2], w=2)
            for y in range(S.h):
                for x in range(S.w):
                    d = math.hypot((x - cx) / (S.w / 2), (y - cy) / (S.h / 2))
                    if d > 0.85 and bayer(x, y) < (d - 0.85) * 2:
                        cv.px(x, y, S.pal[3])
            continue
        cv.rect(0, 0, S.w - 1, S.h - 1, S.pal[0])
        for y in range(S.h):
            for x in range(S.w):
                d = math.hypot((x - cx) / (S.w / 2), (y - cy) / (S.h / 2))
                if d < 0.55 and bayer(x, y) < (0.55 - d) * 0.9:
                    cv.px(x, y, S.pal[1])
        for (a, inner, w) in lines:
            a2 = a + i * 0.04
            r0 = R * (inner + 0.06 * ((i * 3 + int(a * 10)) % 3))
            col = S.pal[5] if w == 1 else S.pal[4] if w == 2 else S.pal[3]
            cv.line(cx + math.cos(a2) * r0, cy + math.sin(a2) * r0 * 0.75, cx + math.cos(a2) * R,
                    cy + math.sin(a2) * R * 0.75, col, w=1 if w == 1 else 2)
        if i >= S.n - 2:
            cv.dissolve(0.35 + 0.3 * (i - (S.n - 2)), seed=i)


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
    """Loop: soft green column glow, outlined shaded plus signs and sparkles rising, ground band pulse."""
    cx, fy = S.w / 2, S.feet
    seeds = [(S.rng.random(), S.rng.uniform(-1, 1), S.rng.random()) for _ in range(9)]
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        for y in range(int(fy - 44), int(fy)):
            k = (fy - y) / 44
            for x in range(int(cx - 14), int(cx + 15)):
                d = abs(x - cx) / 14
                if bayer(x, y) < (1 - d) * (1 - k) * 0.45:
                    cv.px(x, y, S.pal[2])
        pr = (ph * 2) % 1.0
        cv.band(cx, fy, 8 + pr * 16, 3 * (1 - pr) + 1, S.pal, squash=0.35, lo=2, hi=5, front_lit=True)
        for (u, side, s) in seeds:
            p = (ph + u) % 1.0
            x = cx + side * 13
            y = fy - 4 - p * (S.h - 16)
            if s > 0.4:
                a = 3 if p < 0.7 else 2
                cv.rect(x - a - 1, y - 2, x + a + 1, y + 2, S.pal[0])
                cv.rect(x - 2, y - a - 1, x + 2, y + a + 1, S.pal[0])
                cv.rect(x - a, y - 1, x + a, y + 1, S.pal[3])
                cv.rect(x - 1, y - a, x + 1, y + a, S.pal[3])
                cv.rect(x - a, y - 1, x, y, S.pal[4])
                cv.rect(x - 1, y - a, x, y, S.pal[4])
                cv.px(x, y, S.pal[5])
            else:
                cv.star(x, y, 2.5 if p < 0.5 else 1.5, 0.3, 4, S.pal, lo=3)


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
    """Loop: shaded flame tongues lick up the body, ember specks, warm floor glow."""
    cx, fy = S.w / 2, S.feet
    flames = [(-9, 0.0), (7, 0.33), (-1, 0.66), (11, 0.5), (-5, 0.85)]
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        cv.glow(cx, fy, 6, 18, S.pal[2], density=0.45, squash=0.35)
        for (dx, u) in sorted(flames, key=lambda f: -((ph + f[1]) % 1.0)):
            p = (ph + u) % 1.0
            y = fy - 6 - p * 24
            r = 4.6 * (1 - p) + 1.2
            flame_tongue(cv, cx + dx + math.sin(p * 9) * 1.2, y, r, r * 2.4, S.pal, 1.1 - p)
        for k in range(3):
            p = (ph * 2 + k / 3) % 1.0
            cv.px(cx - 6 + k * 6, fy - 26 - p * 12, S.pal[4 if p < 0.5 else 3])


def st_poison(S):
    """Loop: shaded toxic bubbles rise from a sickly floor puddle and pop into rings of droplets."""
    cx, fy = S.w / 2, S.feet
    bub = [(-9, 0.0, 2.6), (4, 0.25, 1.8), (10, 0.5, 2.4), (-3, 0.75, 1.6), (0, 0.4, 3.2), (-12, 0.6, 1.6)]
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        cv.glow(cx, fy, 6, 18, S.pal[2], density=0.45, squash=0.3)
        cv.ellipse(cx, fy, 12, 2.5, S.pal[1])
        cv.ellipse(cx - 2, fy - 0.5, 7, 1.2, S.pal[3])
        for (dx, u, s) in bub:
            p = (ph + u) % 1.0
            y = fy - 6 - p * 30
            if p < 0.85:
                cv.shaded(cx + dx, y, s, s, S.pal, lo=1)
            else:
                for k in range(6):
                    a = k * TAU / 6 + 0.3
                    cv.px(cx + dx + math.cos(a) * (s + 3), y + math.sin(a) * (s + 3), S.pal[4])


def st_paralysis(S):
    """Loop: thick cored sparks jump around the body with glow, yellow rim flicker; off beat every 3rd frame."""
    cx, fy = S.w / 2, S.feet
    for i, cv in enumerate(S.frames):
        if i % 3 == 2:
            cv.glow(cx, fy - 16, 0, 18, S.pal[2], density=0.2)
            continue
        cv.glow(cx, fy - 16, 0, 20, S.pal[2], density=0.18)
        for k in range(3 + (i % 2)):
            x0 = cx + S.rng.uniform(-15, 15)
            y0 = fy - S.rng.uniform(6, 32)
            pts = zigzag(S.rng, x0, y0, x0 + S.rng.uniform(-10, 10), y0 + S.rng.uniform(-10, 10), 3, 3)
            cv.glow(x0, y0, 0, 6, S.pal[3], density=0.4)
            cv.stroke(pts, 2, S.pal, lo=2, hi=5)
        cv.star(cx + S.rng.uniform(-12, 12), fy - S.rng.uniform(22, 36), 4, 0.3, 4, S.pal, lo=2)


def st_sleep(S):
    """Loop: outlined, two-tone Z letters drift up and grow, with a small bubble."""
    cx, fy = S.w / 2, S.feet
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        for k in range(3):
            p = (ph + k / 3) % 1.0
            x = cx + 6 + p * 12 + math.sin(p * TAU) * 2
            y = fy - 28 - p * 22
            sc = 1 if p < 0.4 else 2
            if p < 0.92:
                cv.glow(x, y + 2 * sc, 1, 4 + 3 * sc, S.pal[2], density=0.35)
                cv.text("Z", x + 1, y + 1, S.pal[2], scale=sc)
                cv.text("Z", x, y, S.pal[4 if p < 0.6 else 5], outline=S.pal[0], scale=sc)
        b = (ph * 2) % 1.0
        cv.shaded(cx + 4, fy - 22 - b * 3, 1.5 + b * 2.5, 1.5 + b * 2.5, S.pal, lo=2)


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
    """Loop: three shaded stars orbit above the head on a squashed glowing track; front ones bigger."""
    cx, fy = S.w / 2, S.feet
    hy = fy - 36
    for i, cv in enumerate(S.frames):
        ph = i / S.n
        cv.glow(cx, hy, 8, 18, S.pal[2], density=0.3, squash=0.35)
        cv.band(cx, hy, 15, 2, S.pal, squash=0.3, lo=1, hi=3, front_lit=True, gaps=3, phase=ph)
        items = []
        for k in range(3):
            a = (ph + k / 3) * TAU
            items.append((math.sin(a), cx + math.cos(a) * 15, hy + math.sin(a) * 4.5))
        for (z, x, y) in sorted(items):
            r = 4.5 if z > 0 else 3
            cv.star(x, y, r + 1, 0.55, 5, S.pal, lo=1, hi=5 if z > 0 else 4, rot=-math.pi / 2 + ph * 2)


def faint_vanish(S):
    """Dissolve puff: shaded dust puffs roll out at the feet, glowing motes rise from the body area."""
    cx, fy = S.w / 2, S.feet
    dust = ramp("dust")
    motes = [Particle(cx + S.rng.uniform(-11, 11), fy - S.rng.uniform(2, 26), S.rng.uniform(-0.3, 0.3),
                      S.rng.uniform(-1.3, -0.5), S.rng.randint(S.n // 2, S.n), size=S.rng.uniform(1.0, 2.2),
                      kind=S.rng.randint(0, 6)) for _ in range(34)]
    for i, cv in enumerate(S.frames):
        t = i / (S.n - 1)
        rt = out_cubic(seg(t, 0, 0.6))
        if t < 0.8:
            cv.band(cx, fy, 6 + rt * 22, 2, S.pal, squash=0.3, lo=1, hi=4, front_lit=True, dens=1 - t)
        for k in range(4):
            dt = out_quad(seg(t, 0, 0.8))
            for side in (-1, 1):
                x = cx + side * (4 + dt * 18 + k * 3)
                r = (4 - k * 0.6) * (1 - seg(t, 0.55, 1) * 0.8)
                if r > 0.6:
                    cv.shaded(x, fy - 2 - k * 1.5, r, r * 0.8, dust, lo=1, hi=4)
        if t < 0.25:
            cv.glow(cx, fy - 14, 4, 16, S.pal[3], density=0.6 * (1 - t * 4))
        for p in motes:
            if p.alive and p.age >= p.kind * 0.5:
                cv.glow(p.x, p.y, 0, 2.5, S.pal[2], density=0.4)
                cv.disc(p.x, p.y, p.size * (1 - p.t * 0.6), S.pal[4 if p.t < 0.3 else 3])
                cv.px(p.x, p.y, S.pal[5])
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
    """Silhouette pulse: the body flashes white in quickening beats inside a ring of tapered light rays and
    a rising sparkle column, then one big flash hides the swap."""
    cx, fy = S.w / 2, S.feet
    cy = fy - 18
    for i, cv in enumerate(S.frames):
        t = i / (S.n - 1)
        beat = math.sin((t * t * 10) * math.pi)
        cv.glow(cx, cy, 10, 26 + beat * 3, S.pal[2], density=0.35 + 0.25 * max(0, beat))
        for k in range(10):
            a = k * TAU / 10 + t * 2
            cv.tri_ray(cx, cy, a, 16, 24 + beat * 5, 3, S.pal[4] if beat > 0 else S.pal[3])
        if beat > 0.2 or t > 0.85:
            draw_creature(cv, int(cx), int(fy), mono=S.pal[5])
        else:
            draw_creature(cv, int(cx), int(fy), pal=ramp("white"))
        for k in range(5):
            y = fy - ((t * 2 + k / 5) % 1.0) * 44
            cv.star(cx + (k - 2) * 7, y, 2, 0.3, 4, S.pal, lo=3)
        if t > 0.88:
            cv.glow(cx, cy, 0, 30, S.pal[4], density=0.9)
            cv.disc(cx, cy, 20, S.pal[5])
            cv.band(cx, cy, 26, 3, S.pal, lo=2, hi=4)


def recall_beam(S):
    """Recall: a cored red beam appears at full length in one frame; the unit turns into a shaded red
    silhouette, shrinks and is pulled up; a ring closes with a glint."""
    cx, fy = S.w / 2, S.feet
    for i, cv in enumerate(S.frames):
        t = i / (S.n - 1)
        bw = 2 + (1 if 0.1 < t < 0.8 else 0)
        if t < 0.9:
            cv.glow(cx, (fy - 16) / 2, 1, 5, S.pal[2], density=0.4, squash=4)
            cv.stroke([(cx, 0), (cx, fy - 16)], bw, S.pal, lo=1, hi=5)
        sh = 1 - in_quad(seg(t, 0.2, 0.75))
        if sh > 0.1:
            lift = seg(t, 0.4, 0.8) * 20
            draw_creature(cv, int(cx), int(fy - lift), sx=sh, sy=sh, pal=S.pal if t > 0.15 else None)
            if t > 0.15:
                cv.glow(cx, fy - lift - 12 * sh, 6 * sh, 14 * sh + 2, S.pal[3], density=0.5)
        rt = seg(t, 0.6, 1)
        if 0 < rt < 1:
            cv.band(cx, fy - 22, 14 * (1 - rt) + 2, 2, S.pal, lo=2, hi=5)
        if 0.7 < t < 0.95:
            cv.star(cx, fy - 30, 5, 0.3, 4, S.pal, lo=2)


def send_out(S):
    """Send-out: shaded floor flash, thick ring, a light pillar flicker and sparkles bursting outward."""
    cx, fy = S.w / 2, S.feet
    for i, cv in enumerate(S.frames):
        t = i / (S.n - 1)
        rt = out_cubic(seg(t, 0, 0.5))
        cv.band(cx, fy, 5 + rt * 22, 4 * (1 - rt) + 1.5, S.pal, squash=0.35, lo=2, hi=5, front_lit=True,
                dens=1 - seg(t, 0.5, 1) * 0.6)
        if t < 0.35:
            k = 1 - t / 0.35
            cv.glow(cx, fy - 14, 4, 20 * k + 4, S.pal[3], density=0.8)
            cv.shaded(cx, fy - 14, 10 * k + 2, 12 * k + 2, S.pal, lo=2)
            for y in range(0, int(fy)):
                if bayer(cx, y) < k:
                    cv.line(cx - 3 * k, y, cx + 3 * k, y, S.pal[4])
        for k in range(8):
            a = k * TAU / 8 + 0.4
            d = 6 + rt * 20
            if t < 0.75:
                cv.star(cx + math.cos(a) * d, fy - 14 + math.sin(a) * d * 0.8, 3.5 if t < 0.4 else 2, 0.3, 4, S.pal, lo=2)


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
