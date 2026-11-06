"""The neutral dummy creature: an original round biped with two ears and a stub tail.

Drawn from ellipses and triangles each frame so it can squash, stretch, lean and blink. It is
grey on purpose so every element's colours read on top of it.
"""
from .core import Canvas
from .palettes import ramp

GREY = ramp("creature")


def draw_creature(cv, x, feet_y, sx=1.0, sy=1.0, lean=0, flip=False, pal=None, flash=None,
                  eye=True, mono=None):
    """Draw the dummy with its feet centred on (x, feet_y).

    sx/sy squash-stretch, lean shifts the head sideways in px, flip faces left, flash replaces
    every body colour with one colour (hit blink), mono draws a flat silhouette.
    """
    p = pal or GREY
    W, H = 40, 40
    t = Canvas(W, H)
    cx, fy = 20, 34
    rx, ry = 9 * sx, 8 * sy
    by = fy - 2 - ry  # body centre
    hx = cx + lean
    # tail (behind)
    t.line(cx - rx + 1, by + 3, cx - rx - 3, by - 1, p[2], w=2)
    t.px(cx - rx - 4, by - 2, p[3])
    # feet
    t.ellipse(cx - 4 * sx, fy - 1, 2.5 * sx, 1.6, p[1])
    t.ellipse(cx + 4 * sx, fy - 1, 2.5 * sx, 1.6, p[1])
    # body
    t.ellipse(hx * 0.5 + cx * 0.5, by, rx, ry, p[2])
    t.ellipse(hx * 0.5 + cx * 0.5 + 1, by + 2, rx * 0.65, ry * 0.6, p[3])  # belly
    t.ellipse(hx * 0.5 + cx * 0.5 - 3 * sx, by - 4 * sy, 2.4 * sx, 1.6 * sy, p[4])  # top-left highlight
    # ears
    ex = hx * 0.5 + cx * 0.5
    top = by - ry + 1
    t.poly([(ex - 6 * sx, top + 2), (ex - 3 * sx, top - 6 * sy), (ex - 1 * sx, top + 1)], p[2])
    t.poly([(ex + 2 * sx, top + 1), (ex + 5 * sx, top - 6 * sy), (ex + 7 * sx, top + 3)], p[2])
    t.px(ex - 3 * sx, top - 3 * sy, p[4])
    t.px(ex + 5 * sx, top - 3 * sy, p[4])
    # eye + cheek, looking right
    if eye:
        t.rect(ex + rx * 0.45, by - 3 * sy, ex + rx * 0.45 + 1, by - 1 * sy, p[0])
        t.px(ex + rx * 0.45, by - 3 * sy, p[5])
    t.outline(p[0])
    if flash or mono:
        col = flash or mono
        for yy in range(H):
            for xx in range(W):
                if t.pa[xx, yy][3]:
                    t.pa[xx, yy] = col
    img = t.img
    if flip:
        from PIL import ImageOps
        img = ImageOps.mirror(img)
    cv.paste(img, x - cx, feet_y - fy)
