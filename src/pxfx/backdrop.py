"""Our own simple battle ground: a muted top-down field with speckle texture, grass tufts and two
oval stand pads. Dark-mid value so both bright and dark effects read on it."""
from .core import Canvas, hexrgb, make_rng

BASE = hexrgb("#2c3b3a")
DARK = hexrgb("#243130")
LIGHT = hexrgb("#354746")
TUFT = hexrgb("#3f5a4a")
TUFT_HI = hexrgb("#55745c")
PAD = hexrgb("#3a4c4a")
PAD_RIM = hexrgb("#4f6562")
PAD_SH = hexrgb("#222e2d")


def _field(w, h, seed):
    rng = make_rng(seed)
    cv = Canvas(w, h)
    cv.rect(0, 0, w - 1, h - 1, BASE)
    for _ in range(w * h // 18):
        x, y = rng.randrange(w), rng.randrange(h)
        cv.px(x, y, DARK if rng.random() < 0.55 else LIGHT)
    for _ in range(max(2, w * h // 900)):
        x, y = rng.randrange(w), rng.randrange(h)
        cv.px(x, y, TUFT)
        cv.px(x - 1, y + 1, TUFT)
        cv.px(x + 1, y + 1, TUFT)
        cv.px(x, y - 1, TUFT_HI)
    return cv


def _pad(cv, cx, cy, rx, ry):
    cv.ellipse(cx, cy + 1, rx, ry, PAD_SH)
    cv.ellipse(cx, cy, rx, ry, PAD)
    cv.ring(cx, cy, rx, 1, PAD_RIM, squash=ry / rx)


def make_tile(w, h):
    cv = _field(w, h, "tile%dx%d" % (w, h))
    return cv.img


def make_backdrop(w=320, h=180):
    cv = _field(w, h, "arena")
    _pad(cv, 80, 132, 30, 9)
    _pad(cv, 240, 112, 30, 9)
    return cv.img
