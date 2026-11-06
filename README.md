# Pocket Battle VFX

90 pixel-art battle effects for top-down monster-battle / auto-battle games: projectiles, beams, impacts, areas
and auras for 18 elements, plus hit sparks, crits, a crit cut-in, miss, shield, heal, stat up/down, six status
loops, faint, level up, evolve glow, recall beam, send-out, and four unit animations on a neutral dummy creature.

Every frame is **drawn by code** (`src/`). Nothing is traced or cropped from any game or video.

**Licence: CC0 1.0** (public domain) for the sprite sheets, GIFs, JSON, pages and generator. See `LICENSE`.

## Site

Static, relative paths, no build step. `index.html` is the gallery (filters by element and kind, search, detail
view with frame strip, play/pause, fps slider, ×1–×4 scale, loop toggle, PNG/JSON/GIF downloads) with a combo
preview (caster lunge → projectile or beam → impact with hit-stop, shake and flash → target recoil → status loop
and damage number). `how.html` explains the rules and timing and cites the reference clips by timestamp.

Run locally (fetch() needs http, not file://):

```sh
python3 -m http.server 8000   # then open http://localhost:8000/
```

## Regenerate

Needs Python 3.8+ and Pillow (`pip install pillow`). From the site root:

```sh
python3 src/build.py              # rebuild everything (~45 s, 30 fps particle sims)
python3 src/build.py fire         # re-render only ids containing "fire" (fx.json is still rewritten)
```

The build is deterministic: each effect's random numbers are seeded from its id, so the same source gives
byte-identical sheets.

## Files

```
index.html, how.html        gallery + combo, and the "how it's made" page
assets/style.css, app.js    site styling and logic (plain JS)
fx.json                     all effects in one file (the gallery reads this)
fx/<id>.png                 colour layer: transparent sprite sheet, frames left→right then top→bottom
fx/<id>.light.png           light layer, same grid: premultiplied (rgb = light, alpha = max channel); draw it
                            with additive blending (ONE, ONE) on top of everything, or skip it
fx/<id>.json                one effect's entry (same fields as in fx.json)
fx/<id>.gif                 2× preview: colour + light composited on the dark stage
img/backdrop.png            320×180 battle ground (our own), img/dummy.png the neutral creature
src/build.py                the one command
src/pxfx/core.py            pixel canvas: whole-pixel discs, rings, ellipses, lines, polygons, sparkles, 3×5 font
src/pxfx/palettes.py        6-step colour ramp per element and for generic effects
src/pxfx/sim.py             v3 core: value/curl noise, 120 Hz particle sim, half-res additive light layer,
                            noise-broken shapes (ragged blobs, flame tongues, jagged bursts, tapered crescents)
src/pxfx/fx3.py             one drawing function per move (Hydro Pump, Flamethrower, Thunder, Razor Leaf,
                            Ice Beam, Earthquake, Shadow Ball, ...) built from shared shapes (leaf, petal,
                            crystal, goo, rock chunk, dust billow, wind curl, feather, needle, glove,
                            comic star, heart, wavy ring, flame tongue) + status, generic systems, unit acting
src/pxfx/fxlib.py           v2 archetypes (kept for reference, unused): orb, boulder, volley, waves, beam, bolt, burst, splash, explosion,
                            debris, slash, aura, pillar, vortex, pulse rings, cloud, rain, cracks, spikes, swarm, shield
src/pxfx/generic.py         hit spark, crit, cut-in, miss, heal, stat arrows, status loops, faint, level up,
                            evolve, recall, send-out, charge, unit idle/lunge/recoil/faint
src/pxfx/creature.py        the dummy creature, drawn from shapes each frame
src/pxfx/catalog.py         the effect table: id, name, element, kind, size, frames, fps, archetype, timing
src/refs.json               effect id → reference-catalogue ids it was informed by
src/refs-index.json         reference id → YouTube link with timestamp (used by how.html)
```

## Effect entry (`fx.json` → `effects[]`, and `fx/<id>.json`)

| field | meaning |
|---|---|
| `id`, `name` | stable id (file name) and display name (element + shape) |
| `element` | one of the 18 elements; generic effects use the closest one |
| `kind` | projectile, beam, impact, area, aura, buff, debuff, status, system, unit |
| `frameW`, `frameH`, `frames`, `fps`, `loop` | frame size (multiples of 32), count, playback |
| `anchor` | pixel inside a frame that you place on the world point: projectile head, beam origin, impact centre, or unit feet |
| `layer` | `ground` (under units), `front` (over units), `screen` (full-screen plate) |
| `palette` | the 6-step dark→bright ramp used |
| `notes` | how it is built / when to use it |
| `refs` | ids of catalogued reference moments that informed it |
| `sheet` | `image`, `columns`, `rows`, `width`, `height` |
| `gif`, `durationMs` | preview path and length |
| `light` | light sheet: `image`, `blend` (additive), `premultiplied`, grid |
| `ground` | y of the floor line inside a frame (units stand on it, debris bounces on it) |
| `material` | `material` (water, rock, leaves, metal...: no glow, only contact glints in the light layer) or `emissive` (fire, lightning, energy) |
| `peakFrame` | the frame with the most pixels (used for thumbnails) |
| `battle` | optional `hitFrame`, `hitStopMs`, `shakePx` for wiring the hit |

Projectiles are short loops facing right: move them with your engine and rotate to the travel direction. Beams
start at `anchor` and reach the right edge; stretch them horizontally to the target. Aura/status effects use the
unit's feet as anchor (feet at y = 56 in a 64 px frame).

## Credits

Generated with code written for this pack. Presentation ideas (chips, live cards, detail dialog) were inspired by
the MIT-licensed pixelfx gallery by Patch; no code or art from it is used. Reference clips are only linked by
timestamp on `how.html` for study.
