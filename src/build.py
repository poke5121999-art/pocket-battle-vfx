#!/usr/bin/env python3
"""Rebuild every effect: sprite sheet PNG, animated GIF preview, per-effect JSON and fx.json.

    python3 src/build.py            # all effects
    python3 src/build.py fire-burst # only ids containing this text (fx.json is still rewritten in full)

Needs Python 3.8+ and Pillow. Deterministic: the same code gives byte-identical sheets.
Output (relative to the site root): fx/<id>.png, fx/<id>.gif, fx/<id>.json, fx.json,
img/backdrop.png, img/dummy.png.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from PIL import Image  # noqa: E402

from pxfx.backdrop import make_backdrop, make_tile  # noqa: E402
from pxfx.catalog import EFFECTS  # noqa: E402
from pxfx.core import Canvas, make_rng  # noqa: E402
from pxfx.creature import draw_creature  # noqa: E402
from pxfx.palettes import RAMPS, ramp  # noqa: E402

ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "fx")
MAX_SHEET_W = 1024
GIF_SCALE = 2
REFS = json.load(open(os.path.join(HERE, "refs.json"), encoding="utf8"))


class State:
    def __init__(self, e):
        self.w, self.h, self.n = e["frameW"], e["frameH"], e["frames"]
        self.pal = ramp(e["ramp"])
        self.rng = make_rng(e["id"])
        self.feet = e["feet"] or (self.h - 8)
        self.frames = [Canvas(self.w, self.h) for _ in range(self.n)]


def sheet_layout(e):
    cols = max(1, min(e["frames"], MAX_SHEET_W // e["frameW"]))
    rows = (e["frames"] + cols - 1) // cols
    return cols, rows


def render(e):
    S = State(e)
    e["render"](S)
    return [c.img for c in S.frames]


def write_sheet(e, frames):
    cols, rows = sheet_layout(e)
    sheet = Image.new("RGBA", (cols * e["frameW"], rows * e["frameH"]), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        sheet.paste(f, ((i % cols) * e["frameW"], (i // cols) * e["frameH"]))
    sheet.save(os.path.join(OUT, e["id"] + ".png"), optimize=True)
    return cols, rows


def write_gif(e, frames):
    """Preview: effect over our battle tile, dummy creature placed where the effect expects a unit."""
    w, h = e["frameW"], e["frameH"]
    tile = make_tile(w, h)
    dummy_kinds = ("aura", "status", "buff", "debuff", "impact")
    out = []
    for f in frames:
        bg = tile.copy()
        if e["kind"] in dummy_kinds and e["layer"] != "screen" and e["kind"] != "unit":
            cv = Canvas(w, h)
            fy = e["feet"] or min(h - 6, h // 2 + 18)
            if e["kind"] == "impact":
                fy = min(h - 4, e["anchor"][1] + 16)
            draw_creature(cv, w // 2, fy, flip=True)
            if e["layer"] == "ground":
                bg.alpha_composite(f)
                bg.alpha_composite(cv.img)
            else:
                bg.alpha_composite(cv.img)
                bg.alpha_composite(f)
        else:
            bg.alpha_composite(f)
        out.append(bg.convert("RGB").resize((w * GIF_SCALE, h * GIF_SCALE), Image.NEAREST)
                   .quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE))
    dur = int(round(1000 / e["fps"]))
    hold = [dur] * len(out)
    if not e["loop"]:
        hold[-1] = dur + 500  # pause on the last frame of one-shots so the preview breathes
    out[0].save(os.path.join(OUT, e["id"] + ".gif"), save_all=True, append_images=out[1:], duration=hold,
                loop=0, optimize=False, disposal=1)


def entry_json(e, cols, rows):
    d = {k: e[k] for k in ("id", "name", "element", "kind", "frameW", "frameH", "frames", "fps", "loop",
                           "anchor", "layer", "notes")}
    d["palette"] = RAMPS[e["ramp"]]
    d["refs"] = REFS.get(e["id"], [])
    d["sheet"] = {"image": "fx/%s.png" % e["id"], "columns": cols, "rows": rows,
                  "width": cols * e["frameW"], "height": rows * e["frameH"]}
    d["gif"] = "fx/%s.gif" % e["id"]
    d["durationMs"] = int(round(e["frames"] * 1000 / e["fps"]))
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
    make_backdrop().save(os.path.join(ROOT, "img", "backdrop.png"), optimize=True)
    dummy = Canvas(64, 64)
    draw_creature(dummy, 32, 56)
    dummy.img.save(os.path.join(ROOT, "img", "dummy.png"), optimize=True)
    seen, entries = set(), []
    t0 = time.time()
    for e in EFFECTS:
        assert e["id"] not in seen, "duplicate id " + e["id"]
        seen.add(e["id"])
        assert e["frameW"] % 32 == 0 and e["frameH"] % 32 == 0, e["id"] + " frame size not a multiple of 32"
        if flt and flt not in e["id"]:
            cols, rows = sheet_layout(e)
        else:
            frames = render(e)
            cols, rows = write_sheet(e, frames)
            write_gif(e, frames)
        d = entry_json(e, cols, rows)
        with open(os.path.join(OUT, e["id"] + ".json"), "w", encoding="utf8") as f:
            json.dump(d, f, indent=1)
        entries.append(d)
    meta = {"name": "Pocket Battle VFX", "license": "CC0-1.0", "count": len(entries),
            "elements": sorted({d["element"] for d in entries}), "effects": entries}
    with open(os.path.join(ROOT, "fx.json"), "w", encoding="utf8") as f:
        json.dump(meta, f, indent=1)
    print("built %d effects in %.1fs -> %s" % (len(entries), time.time() - t0, OUT))


if __name__ == "__main__":
    main()
