#!/usr/bin/env python3
"""Rebuild every effect: colour sprite sheet, additive light sheet, animated GIF preview, per-effect JSON and
fx.json.

    python3 src/build.py            # all effects
    python3 src/build.py fire       # only ids containing "fire" (fx.json is still rewritten in full)

Needs Python 3.8+ and Pillow. Deterministic: the same code gives byte-identical sheets.
Output (relative to the site root): fx/<id>.png (colour, transparent), fx/<id>.light.png (light, premultiplied:
rgb = light, alpha = max channel - draw it with additive blending), fx/<id>.gif, fx/<id>.json, fx.json,
img/backdrop.png, img/dummy.png.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from PIL import Image  # noqa: E402

from pxfx.backdrop import make_stage  # noqa: E402
from pxfx.catalog import EFFECTS  # noqa: E402
from pxfx.core import Canvas, make_rng  # noqa: E402
from pxfx.creature import draw_creature  # noqa: E402
from pxfx.palettes import ramp, ramp_hex  # noqa: E402
from pxfx.sim import Light  # noqa: E402

ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "fx")
MAX_SHEET_W = 1024
GIF_SCALE = 2
REFS = json.load(open(os.path.join(HERE, "refs.json"), encoding="utf8"))
DUMMY_KINDS = ("aura", "status", "buff", "debuff", "impact")
NO_DUMMY = {"evolve-glow", "recall-beam", "faint-vanish", "send-out", "miss", "crit-cutin", "charge-up", "hit-spark"}


class State:
    def __init__(self, e):
        self.w, self.h, self.n, self.fps = e["frameW"], e["frameH"], e["frames"], e["fps"]
        self.pal = ramp(e["ramp"])
        self.rng = make_rng(e["id"])
        self.ground = e["ground"]
        self.feet = e["ground"]
        self.anchor = tuple(e["anchor"])
        self.frames = [Canvas(self.w, self.h) for _ in range(self.n)]
        self.material = e["material"] == "material"
        self.lights = [Light(self.w, self.h, material=self.material) for _ in range(self.n)]


def sheet_layout(e):
    cols = max(1, min(e["frames"], MAX_SHEET_W // e["frameW"]))
    rows = (e["frames"] + cols - 1) // cols
    return cols, rows


def render(e):
    S = State(e)
    e["render"](S)
    colour = [c.img for c in S.frames]
    light = [L.image() for L in S.lights]
    # thumbnail frame: most colour pixels, discounted where light dominates (so the colour layer reads)
    score = []
    for f, L in zip(colour, light):
        n = f.width * f.height
        cov = n - f.getchannel("A").histogram()[0]
        hist = L.getchannel("A").histogram()
        lmean = sum(v * c for v, c in enumerate(hist)) / (255.0 * n)
        score.append(cov * (1 - min(0.9, max(0.0, 2.5 * (lmean - 0.06)))))
    e["peakFrame"] = score.index(max(score))
    return colour, light


def write_sheet(e, frames, suffix=""):
    cols, rows = sheet_layout(e)
    sheet = Image.new("RGBA", (cols * e["frameW"], rows * e["frameH"]), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        sheet.paste(f, ((i % cols) * e["frameW"], (i // cols) * e["frameH"]))
    sheet.save(os.path.join(OUT, e["id"] + suffix + ".png"), optimize=True)
    return cols, rows


def add_light(base_rgb, light_rgba):
    """Additive composite of a premultiplied light frame onto an RGB image (clamped)."""
    from PIL import ImageChops
    return ImageChops.add(base_rgb, light_rgba.convert("RGB"))


def wants_dummy(e):
    return e["kind"] in DUMMY_KINDS and e["layer"] != "screen" and e["id"] not in NO_DUMMY


def write_gif(e, colour, light):
    """Preview on the dark stage: dummy where a unit belongs, colour layer, then light added on top."""
    w, h = e["frameW"], e["frameH"]
    stage = make_stage(w, h, e["ground"])
    out = []
    for f, L in zip(colour, light):
        bg = stage.copy()
        if wants_dummy(e):
            cv = Canvas(w, h)
            draw_creature(cv, e["anchor"][0], e["ground"], flip=e["kind"] == "impact")
            if e["layer"] == "ground":
                bg.alpha_composite(f)
                bg.alpha_composite(cv.img)
            else:
                bg.alpha_composite(cv.img)
                bg.alpha_composite(f)
        else:
            bg.alpha_composite(f)
        rgb = add_light(bg.convert("RGB"), L)
        out.append(rgb.resize((w * GIF_SCALE, h * GIF_SCALE), Image.NEAREST)
                   .quantize(colors=200, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE))
    dur = int(round(1000 / e["fps"]))
    hold = [dur] * len(out)
    if not e["loop"]:
        hold[-1] = dur + 400
    out[0].save(os.path.join(OUT, e["id"] + ".gif"), save_all=True, append_images=out[1:], duration=hold,
                loop=0, optimize=False, disposal=1)


def entry_json(e, cols, rows):
    d = {k: e[k] for k in ("id", "name", "element", "kind", "frameW", "frameH", "frames", "fps", "loop",
                           "anchor", "layer", "notes")}
    d["ground"] = e["ground"]
    d["material"] = e["material"]
    d["palette"] = ramp_hex(e["ramp"])
    d["refs"] = REFS.get(e["id"], [])
    d["sheet"] = {"image": "fx/%s.png" % e["id"], "columns": cols, "rows": rows,
                  "width": cols * e["frameW"], "height": rows * e["frameH"]}
    d["light"] = {"image": "fx/%s.light.png" % e["id"], "blend": "additive", "premultiplied": True,
                  "columns": cols, "rows": rows}
    d["gif"] = "fx/%s.gif" % e["id"]
    d["durationMs"] = int(round(e["frames"] * 1000 / e["fps"]))
    d["peakFrame"] = e.get("peakFrame", 0)
    battle = {}
    if e["hit"] is not None:
        battle["hitFrame"] = e["hit"]
    if e["hitstopMs"]:
        battle["hitStopMs"] = e["hitstopMs"]
    if e["shake"]:
        battle["shakePx"] = e["shake"]
    if battle:
        d["battle"] = battle
    return d


def main():
    flt = sys.argv[1] if len(sys.argv) > 1 else ""
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.join(ROOT, "img"), exist_ok=True)
    make_stage(320, 180, 150).save(os.path.join(ROOT, "img", "backdrop.png"), optimize=True)
    dummy = Canvas(64, 64)
    draw_creature(dummy, 32, 56)
    dummy.img.save(os.path.join(ROOT, "img", "dummy.png"), optimize=True)
    seen, entries = set(), []
    t0 = time.time()
    for e in EFFECTS:
        assert e["id"] not in seen, "duplicate id " + e["id"]
        seen.add(e["id"])
        assert e["frameW"] % 16 == 0 and e["frameH"] % 16 == 0, e["id"] + " frame size not a multiple of 16"
        jpath = os.path.join(OUT, e["id"] + ".json")
        if flt and flt not in e["id"]:
            cols, rows = sheet_layout(e)
            if os.path.exists(jpath):
                e["peakFrame"] = json.load(open(jpath)).get("peakFrame", 0)
        else:
            colour, light = render(e)
            cols, rows = write_sheet(e, colour)
            write_sheet(e, light, ".light")
            write_gif(e, colour, light)
        d = entry_json(e, cols, rows)
        with open(jpath, "w", encoding="utf8") as f:
            json.dump(d, f, indent=1)
        entries.append(d)
    meta = {"name": "Pocket Battle VFX", "license": "CC0-1.0", "count": len(entries), "fps": 30,
            "elements": sorted({d["element"] for d in entries}), "effects": entries}
    with open(os.path.join(ROOT, "fx.json"), "w", encoding="utf8") as f:
        json.dump(meta, f, indent=1)
    print("built %d effects in %.1fs -> %s" % (len(entries), time.time() - t0, OUT))


if __name__ == "__main__":
    main()
