"""Dark -> bright colour ramps, 6 steps each: [shadow, dark, mid, light, highlight, hot core].

Rules (see research/style-guide.md): every element owns one hue family; step 0 is used for the
outline/shadow pixels, step 5 only for the hottest 1-3 px cores and first-frame flashes. Values are
our own picks, chosen after sampling the reference clips' effect colours (research/catalogue.csv)
for hue and contrast only.
"""
from .core import hexrgb

RAMPS = {
    "normal":   ["#33313d", "#686676", "#a3a1b1", "#d2d0dc", "#efeef5", "#ffffff"],
    "fire":     ["#4a1310", "#a8291a", "#e8571c", "#ff9a2e", "#ffd65c", "#fff6c9"],
    "water":    ["#0f2a5c", "#1e5cb8", "#3497e6", "#6ccdfc", "#b6efff", "#ffffff"],
    "grass":    ["#12381c", "#23702c", "#47a83a", "#8dd54b", "#d2f27a", "#f8ffd8"],
    "electric": ["#4a3208", "#b07a0c", "#f2c414", "#ffe94a", "#fff7a8", "#ffffff"],
    "ice":      ["#1b3d5e", "#3a7bb0", "#6fc0e8", "#a8e8ff", "#dcfaff", "#ffffff"],
    "fighting": ["#4a1410", "#922a18", "#d24e22", "#f28c3c", "#ffc878", "#fff0d0"],
    "poison":   ["#2a1238", "#5c2378", "#9440b8", "#c46ee0", "#e8a8f8", "#fbe8ff"],
    "ground":   ["#3a2410", "#6e4a22", "#a8783c", "#d4a85c", "#f0d494", "#fff4d8"],
    "flying":   ["#2a3a6a", "#5068b0", "#84a4e8", "#b8d0ff", "#e4eeff", "#ffffff"],
    "psychic":  ["#4a1040", "#a02878", "#e8508c", "#ff8cb8", "#ffc8e0", "#fff0f8"],
    "bug":      ["#263808", "#4e6e10", "#86a81c", "#b8d43a", "#e0f07c", "#f8ffd0"],
    "rock":     ["#2e2418", "#5a4a32", "#8c7652", "#b8a07a", "#ddc9a4", "#f4ead6"],
    "ghost":    ["#1a1030", "#3c2468", "#6a44a8", "#9a78d8", "#c8b0f8", "#f0e8ff"],
    "dragon":   ["#141e4a", "#2a3c9c", "#4a64e0", "#6aa0ff", "#a8f0f0", "#ffffff"],
    "dark":     ["#0c0a12", "#241c2c", "#3e3048", "#6a4c70", "#a07890", "#e0c8d0"],
    "steel":    ["#262c38", "#4a5466", "#7a8698", "#aeb8c8", "#dce4ee", "#ffffff"],
    "fairy":    ["#4a1438", "#a83a78", "#f070b0", "#ff9cd0", "#ffd0ea", "#ffffff"],
    # generic systems
    "heal":     ["#0e3a2a", "#1c7a4a", "#3cc06a", "#7ef08c", "#c8ffc0", "#ffffff"],
    "gold":     ["#4a300a", "#9a6410", "#e0a020", "#ffd040", "#fff090", "#ffffff"],
    "red":      ["#3a0a10", "#8a1420", "#d82838", "#ff5a5a", "#ffa8a0", "#ffffff"],
    "blue":     ["#0c1a48", "#1c3a9a", "#3464e0", "#6a9cff", "#b4d0ff", "#ffffff"],
    "white":    ["#3a3a4a", "#7a7a8e", "#b4b4c4", "#dedeea", "#f4f4fa", "#ffffff"],
    "shield":   ["#0c2a48", "#1a5a8a", "#2e9ad0", "#68d8f0", "#bcf6ff", "#ffffff"],
    "smoke":    ["#1e1a26", "#38323f", "#565061", "#7a7486", "#a29cad", "#cfcad6"],
    "scorch":   ["#140f12", "#231a1c", "#33282a", "#4a3a36", "#6a5448", "#8c735e"],
    "dust":     ["#2a2018", "#4a3a2a", "#6e5a42", "#94805e", "#bba880", "#e0d2b0"],
    "creature": ["#1c1a24", "#4a4858", "#77758a", "#a7a5b8", "#d4d2e0", "#f4f3f8"],
}

ELEMENTS = ["normal", "fire", "water", "grass", "electric", "ice", "fighting", "poison", "ground",
            "flying", "psychic", "bug", "rock", "ghost", "dragon", "dark", "steel", "fairy"]


import colorsys


def _shift(rgba, i, n):
    """Hue-shift a ramp step: shadows lean toward blue-violet, highlights toward warm yellow, and dark steps
    gain a little saturation, so a ramp reads as lit material instead of one hue getting darker."""
    r, g, b, a = rgba
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    t = i / (n - 1)
    if s > 0.08:
        if t < 0.5:
            target, amt = 0.70, (0.5 - t) * 2 * 0.07   # ~25 deg toward violet at the darkest step
        else:
            target, amt = 0.15, (t - 0.5) * 2 * 0.05   # ~18 deg toward yellow at the brightest step
        d = ((target - h + 0.5) % 1.0) - 0.5
        h = (h + max(-amt, min(amt, d))) % 1.0
        if t < 0.4:
            s = min(1.0, s * 1.12)
    else:  # greys: cool shadows, warm highlights
        if t < 0.5:
            h, s = 0.69, max(s, 0.18 * (0.5 - t) * 2)
        elif t < 1:
            h, s = 0.12, max(s, 0.06 * (t - 0.5) * 2)
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(round(r * 255)), int(round(g * 255)), int(round(b * 255)), a)


def ramp(name):
    base = [hexrgb(h) for h in RAMPS[name]]
    if name in ("creature",):
        return base
    return [_shift(c, i, len(base)) for i, c in enumerate(base)]


def ramp_hex(name):
    return ["#%02x%02x%02x" % c[:3] for c in ramp(name)]
