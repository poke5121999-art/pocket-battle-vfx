"""The effect list. One row per effect: id, display name, element, kind, frame size, frame count,
fps, loop, anchor, layer, ramp, renderer, notes, and battle timing (hit frame, hit-stop, shake).

Names describe element + shape only. Kinds: projectile, beam, impact, aura, area, buff, debuff,
status, system, unit.
"""
from . import fxlib as F
from . import generic as G


def E(id, name, element, kind, size, frames, fps, render, loop=False, anchor=None, layer="front",
      ramp=None, notes="", hit=None, hitstop=0, shake=0, feet=None):
    w, h = size
    if anchor is None:
        if kind == "projectile":
            anchor = [w - 15, h // 2]
        elif kind == "beam":
            anchor = [10, h // 2]
        elif kind in ("aura", "status", "buff", "debuff", "unit", "system") and feet is not None:
            anchor = [w // 2, feet]
        else:
            anchor = [w // 2, h // 2]
    return dict(id=id, name=name, element=element, kind=kind, frameW=w, frameH=h, frames=frames, fps=fps,
                loop=loop, anchor=anchor, layer=layer, ramp=ramp or element, render=render, notes=notes,
                hit=hit, hitstopMs=hitstop, shake=shake, feet=feet)


FEET = 56  # feet line inside 64-tall unit-centred frames

EFFECTS = [
    # ---------------------------------------------------------------- normal
    E("normal-star-volley", "Star Volley", "normal", "projectile", (96, 32), 8, 15, lambda S: F.volley(S, "star", 3), loop=True,
      notes="Three spinning stars with dithered streaks; loop, move it with the engine."),
    E("normal-impact-burst", "Impact Burst", "normal", "impact", (64, 64), 10, 20, lambda S: F.burst(S, rays=8, sparks=10),
      notes="The default hit: white frame 0, 8-point star, ring, rays, sparks cooling.", hit=0, hitstop=60, shake=2),
    E("normal-shock-ring", "Shock Ring", "normal", "area", (96, 64), 12, 15,
      lambda S: F.pulse_rings(S, rings=3, thick=3, squash=0.4, loop=False), layer="ground",
      notes="Ground shockwave: three squashed rings leave the caster's feet (roar / stomp)."),
    # ---------------------------------------------------------------- fire
    E("fire-fireball", "Fire Ball", "fire", "projectile", (96, 32), 8, 15, lambda S: F.orb(S, r=5, trail="flame"), loop=True,
      notes="Hot white core, flame puffs that cool down the ramp along the trail."),
    E("fire-burst", "Fire Burst", "fire", "impact", (96, 96), 14, 15, lambda S: F.explosion(S, puffs=11, embers=12),
      notes="Flash, shaded fireball cluster, cools into grey-violet smoke that rises; embers fall, scorch decal.", hit=0, hitstop=80, shake=3),
    E("fire-pillar", "Flame Pillar", "fire", "area", (64, 128), 14, 15, lambda S: F.pillar(S, "flame"),
      anchor=[32, 120], notes="Column erupts from a ground glow, overshoots, holds, collapses."),
    E("fire-aura", "Flame Aura", "fire", "aura", (64, 64), 8, 12, lambda S: F.aura(S, "flame"), loop=True, feet=FEET,
      notes="Rising flame tongues around the unit; ground ring pulse."),
    # ---------------------------------------------------------------- water
    E("water-jet", "Water Jet", "water", "beam", (128, 64), 20, 15, lambda S: F.beam(S, style="wave", width=7),
      notes="Charge 6f, shoots across in 3f, wavy body holds 8f, thins out.", hit=9, hitstop=40, shake=1),
    E("water-bubble-shot", "Bubble Shot", "water", "projectile", (96, 32), 8, 15, lambda S: F.orb(S, r=4, trail="bubble"), loop=True,
      notes="Glossy orb shedding ring bubbles."),
    E("water-splash", "Water Splash", "water", "impact", (64, 64), 12, 15, lambda S: F.splash(S, drops=16),
      anchor=[32, 52], notes="Crown splash, droplets on gravity arcs, flat ripple rings.", hit=0, hitstop=50, shake=1),
    E("water-whirlpool", "Whirlpool", "water", "area", (64, 96), 10, 12, lambda S: F.vortex(S, "water", rings=6), loop=True,
      anchor=[32, 88], notes="Stacked squashed rings spiralling up with orbiting droplets."),
    # ---------------------------------------------------------------- grass
    E("grass-leaf-volley", "Leaf Volley", "grass", "projectile", (96, 32), 8, 15, lambda S: F.volley(S, "leaf", 3), loop=True,
      notes="Three tumbling two-tone leaves."),
    E("grass-petal-burst", "Petal Burst", "grass", "impact", (64, 64), 12, 15,
      lambda S: F.burst(S, rays=6, sparks=12, spark_kind="petal", gravity=0.08),
      notes="Green flash, leaves burst out and drift down.", hit=0, hitstop=50, shake=1),
    E("grass-leaf-spiral", "Leaf Spiral", "grass", "area", (64, 96), 10, 12, lambda S: F.vortex(S, "petal", rings=6), loop=True,
      anchor=[32, 88], notes="Tornado of rings with orbiting leaves (spiral-ring language from the reference clips)."),
    # ---------------------------------------------------------------- electric
    E("electric-spark-ball", "Spark Ball", "electric", "projectile", (96, 32), 8, 15,
      lambda S: F.orb(S, r=4, trail="electric", spark_tail=False), loop=True,
      notes="Yellow orb with a jittering bolt tail, redrawn every frame."),
    E("electric-thunder-strike", "Thunder Strike", "electric", "impact", (64, 128), 12, 15, lambda S: F.bolt_strike(S, 2),
      anchor=[32, 114], notes="1 pre-strike frame, bolt flickers 4 + 2 frames, ground ring.", hit=1, hitstop=80, shake=3),
    E("electric-static-aura", "Static Aura", "electric", "aura", (64, 64), 8, 12, lambda S: F.aura(S, "spark"), loop=True, feet=FEET,
      notes="Crackling sparks climbing the unit; flicker by skipping beats."),
    # ---------------------------------------------------------------- ice
    E("ice-shards", "Ice Shards", "ice", "projectile", (96, 32), 8, 15, lambda S: F.volley(S, "shard", 3), loop=True,
      notes="Three faceted shards, light side up, white tips."),
    E("ice-beam", "Ice Beam", "ice", "beam", (128, 64), 20, 15, lambda S: F.beam(S, style="ice", width=6),
      notes="Pale beam with crystals budding off both edges.", hit=9, hitstop=40, shake=1),
    E("ice-shatter", "Frost Shatter", "ice", "impact", (64, 64), 12, 15,
      lambda S: F.burst(S, rays=6, sparks=9, spark_kind="shard", gravity=0.12),
      notes="Crystal fragments fly and fall; ring breaks into arcs.", hit=0, hitstop=60, shake=2),
    E("ice-blizzard", "Blizzard Field", "ice", "area", (96, 96), 12, 12, lambda S: F.rain(S, "snow", 46, wind=0.9), loop=True,
      notes="Diagonal snow over a frosted ground ellipse with wind streaks."),
    # ---------------------------------------------------------------- fighting
    E("fighting-force-wave", "Force Wave", "fighting", "projectile", (64, 64), 8, 15, lambda S: F.waves(S, arcs=3, thick=3), loop=True,
      anchor=[6, 32], notes="Thick arcs pushed forward from the fist."),
    E("fighting-power-hit", "Power Hit", "fighting", "impact", (96, 96), 12, 20,
      lambda S: F.burst(S, rays=12, sparks=14, core_r=12), notes="Wide 8-point star, 12 rays: the heavy punch.",
      hit=0, hitstop=100, shake=4),
    E("fighting-power-aura", "Power Aura", "fighting", "aura", (64, 64), 8, 12, lambda S: F.aura(S, "line"), loop=True, feet=FEET,
      notes="Fast vertical speed-lines rising (power-up)."),
    # ---------------------------------------------------------------- poison
    E("poison-sludge-glob", "Sludge Glob", "poison", "projectile", (96, 32), 8, 15, lambda S: F.orb(S, r=5, trail="drip"), loop=True,
      notes="Heavy glob dripping blobs that fall away."),
    E("poison-toxic-splash", "Toxic Splash", "poison", "impact", (64, 64), 12, 15, lambda S: F.splash(S, drops=14),
      anchor=[32, 52], notes="The splash archetype in purple; reads as goo.", hit=0, hitstop=50, shake=1),
    E("poison-cloud", "Poison Cloud", "poison", "area", (96, 64), 10, 10, lambda S: F.cloud(S, 9), loop=True,
      notes="Lumpy dithered gas that churns; bubbles pop at the rim."),
    # ---------------------------------------------------------------- ground
    E("ground-mud-ball", "Mud Ball", "ground", "projectile", (96, 32), 8, 15, lambda S: F.orb(S, r=5, trail="dust"), loop=True,
      notes="Earth orb with a dust trail."),
    E("ground-quake", "Quake Cracks", "ground", "area", (128, 64), 14, 15, lambda S: F.cracks(S, 7), layer="ground",
      notes="Cracks race out, rocks heave, dust; ground layer under units.", hit=3, hitstop=0, shake=4),
    E("ground-dust-burst", "Dust Burst", "ground", "impact", (64, 64), 12, 15, lambda S: F.debris(S, 7),
      anchor=[32, 50], notes="Chunks bounce, dust rolls outward.", hit=0, hitstop=60, shake=2),
    # ---------------------------------------------------------------- flying
    E("flying-air-blade", "Air Blade", "flying", "projectile", (96, 32), 6, 15, lambda S: F.crescent_loop(S), loop=True,
      notes="Crescent of wind with streaks behind."),
    E("flying-gust-burst", "Gust Burst", "flying", "impact", (64, 64), 10, 15,
      lambda S: F.burst(S, rays=6, sparks=8, star=False), notes="Airy hit: no star, ring and rays only.", hit=0, hitstop=40, shake=1),
    E("flying-tornado", "Tornado", "flying", "area", (64, 96), 10, 12, lambda S: F.vortex(S, "wind", rings=7), loop=True,
      anchor=[32, 88], notes="Broken rings spiralling up with wind ticks."),
    # ---------------------------------------------------------------- psychic
    E("psychic-psy-beam", "Psy Beam", "psychic", "beam", (128, 64), 20, 15, lambda S: F.beam(S, style="rings", width=5),
      notes="Pink beam with rings travelling along it.", hit=9, hitstop=40, shake=1),
    E("psychic-psy-burst", "Psy Burst", "psychic", "impact", (96, 96), 12, 15,
      lambda S: F.pulse_rings(S, rings=4, thick=2, loop=False), notes="Concentric rings blow outwards from the target.",
      hit=0, hitstop=60, shake=2),
    E("psychic-mind-field", "Mind Field", "psychic", "aura", (64, 64), 8, 10,
      lambda S: F.pulse_rings(S, rings=3, thick=1, squash=0.35, loop=True), loop=True, feet=FEET, layer="ground",
      notes="Ground rings pulsing under the unit (status-room / mind control)."),
    # ---------------------------------------------------------------- bug
    E("bug-buzz-wave", "Buzz Wave", "bug", "projectile", (64, 64), 8, 15, lambda S: F.waves(S, arcs=4, thick=2), loop=True,
      anchor=[6, 32], notes="Thin sound arcs."),
    E("bug-sting-volley", "Sting Volley", "bug", "projectile", (96, 32), 6, 15, lambda S: F.volley(S, "needle", 3), loop=True,
      notes="Three needles in formation."),
    E("bug-sting-hit", "Sting Hit", "bug", "impact", (64, 64), 10, 20, lambda S: F.burst(S, rays=4, sparks=8, core_r=6),
      notes="Small sharp hit: 4 rays.", hit=0, hitstop=40, shake=1),
    E("bug-swarm", "Swarm", "bug", "area", (64, 64), 8, 15, lambda S: F.swarm(S, 24), loop=True,
      notes="Tiny bugs on noisy orbits with wing flicker."),
    # ---------------------------------------------------------------- rock
    E("rock-boulder", "Boulder Throw", "rock", "projectile", (96, 32), 8, 15, lambda S: F.boulder(S, r=7), loop=True,
      notes="Faceted rock tumbling in 8 steps with an outline, dust trail."),
    E("rock-smash", "Rock Smash", "rock", "impact", (64, 64), 14, 15, lambda S: F.debris(S, 10),
      anchor=[32, 54], notes="Heavy chunks bounce twice.", hit=0, hitstop=80, shake=3),
    E("rock-stone-spikes", "Stone Spikes", "rock", "area", (128, 64), 16, 15, lambda S: F.spikes(S, 6, "rock"),
      anchor=[64, 56], notes="Spikes stab up left to right, hold, sink.", hit=2, hitstop=60, shake=2),
    # ---------------------------------------------------------------- ghost
    E("ghost-shadow-orb", "Shadow Orb", "ghost", "projectile", (96, 32), 8, 15, lambda S: F.orb(S, r=6, trail="smoke"), loop=True,
      notes="Dark orb with a smoky, dithered tail."),
    E("ghost-hex-burst", "Hex Burst", "ghost", "impact", (64, 64), 12, 15,
      lambda S: F.pulse_rings(S, rings=3, thick=2, loop=False, dark_center=True),
      notes="Dark core, purple rings.", hit=0, hitstop=60, shake=1),
    E("ghost-spirit-wisps", "Spirit Wisps", "ghost", "aura", (64, 64), 10, 10, lambda S: F.aura(S, "wisp", ground=False), loop=True,
      feet=FEET, notes="Wisps with dithered tails drift up."),
    # ---------------------------------------------------------------- dragon
    E("dragon-pulse-beam", "Dragon Beam", "dragon", "beam", (128, 64), 20, 15, lambda S: F.beam(S, style="spiral", width=8),
      notes="Thick blue-teal beam with a white helix (beam language from the reference clips).", hit=9, hitstop=60, shake=2),
    E("dragon-burst", "Dragon Burst", "dragon", "impact", (96, 96), 14, 15, lambda S: F.explosion(S, puffs=10, embers=8),
      notes="The explosion archetype in cold colours: shaded cluster, smoke, embers, scorch decal.", hit=0, hitstop=80, shake=3),
    E("dragon-aura", "Dragon Aura", "dragon", "aura", (64, 64), 8, 12, lambda S: F.aura(S, "flame"), loop=True, feet=FEET,
      notes="Blue flame tongues."),
    # ---------------------------------------------------------------- dark
    E("dark-night-claw", "Night Claw", "dark", "impact", (64, 64), 10, 20, lambda S: F.slash(S, count=3, width=3, claw=True),
      ramp="dark", notes="Three diagonal rakes, white edge cools to plum.", hit=1, hitstop=60, shake=2),
    E("dark-pulse", "Dark Pulse", "dark", "area", (96, 96), 10, 12, lambda S: F.pulse_rings(S, rings=3, thick=3, loop=True, dark_center=True),
      loop=True, notes="Thick dark rings radiate from a black core."),
    E("dark-orb", "Dark Orb", "dark", "projectile", (96, 32), 8, 15, lambda S: F.orb(S, r=5, trail="smoke", ring=True), loop=True,
      notes="Black-plum orb with a tilted ring."),
    # ---------------------------------------------------------------- steel
    E("steel-beam", "Steel Beam", "steel", "beam", (128, 64), 20, 15, lambda S: F.beam(S, style="spiral", width=6),
      notes="Silver beam with a white helix.", hit=9, hitstop=60, shake=2),
    E("steel-metal-spark", "Metal Spark", "steel", "impact", (64, 64), 10, 20, lambda S: F.burst(S, rays=8, sparks=16, gravity=0.15),
      notes="Clang: many sparks that arc down.", hit=0, hitstop=60, shake=2),
    E("steel-iron-spikes", "Iron Spikes", "steel", "area", (128, 64), 16, 15, lambda S: F.spikes(S, 5, "ice"),
      anchor=[64, 56], notes="Polished spikes rise in sequence.", hit=2, hitstop=60, shake=2),
    E("steel-slash", "Steel Slash", "steel", "impact", (64, 64), 10, 20, lambda S: F.slash(S, count=1, width=7),
      notes="Single crescent sweep, two-frame whip.", hit=1, hitstop=60, shake=2),
    # ---------------------------------------------------------------- fairy
    E("fairy-moon-orb", "Moon Orb", "fairy", "projectile", (96, 32), 8, 15, lambda S: F.orb(S, r=5, trail="sparkle"), loop=True,
      notes="Pink orb leaving twinkling sparkles."),
    E("fairy-sparkle-burst", "Sparkle Burst", "fairy", "impact", (64, 64), 12, 15, G.fairy_burst,
      notes="Hearts and stars fly out of a soft star.", hit=0, hitstop=50, shake=1),
    E("fairy-ring-aura", "Fairy Ring", "fairy", "aura", (64, 64), 10, 12, lambda S: F.aura(S, "sparkle"), loop=True, feet=FEET,
      notes="Sparkles rise inside a pink ground ring."),
    # ---------------------------------------------------------------- generic
    E("hit-spark", "Hit Spark", "normal", "impact", (32, 32), 6, 20, G.hit_spark, ramp="white",
      notes="Smallest hit, 300 ms: use on every contact.", hit=0, hitstop=40, shake=1),
    E("crit-hit", "Critical Hit", "normal", "impact", (96, 96), 14, 20, G.crit_hit, ramp="gold",
      notes="Two-beat crit: white block, jagged starburst, broken ring, long rays.", hit=0, hitstop=120, shake=4),
    E("crit-cutin", "Crit Cut-in", "normal", "system", (128, 64), 6, 15, G.cutin_lines, ramp="white", layer="screen",
      notes="Opaque screen plate with radial speed lines for 4-6 frames on crits and K.O.s (reference clips)."),
    E("miss", "Miss", "normal", "system", (64, 64), 12, 15, G.miss, ramp="white", feet=FEET,
      notes="After-images slide off and MISS pops."),
    E("shield", "Shield Dome", "steel", "buff", (64, 64), 8, 10, lambda S: F.ring_shield(S), loop=True, ramp="shield", feet=FEET,
      notes="Hex-lattice dome with a sweeping highlight."),
    E("heal", "Heal", "grass", "buff", (64, 64), 10, 12, G.heal, loop=True, ramp="heal", feet=FEET,
      notes="Plus signs and sparkles rise; soft ring pulse."),
    E("stat-up", "Stat Up", "normal", "buff", (64, 64), 8, 12, lambda S: G.stat_arrows(S, True), loop=True, ramp="red", feet=FEET,
      notes="Warm arrows stream up."),
    E("stat-down", "Stat Down", "normal", "debuff", (64, 64), 8, 12, lambda S: G.stat_arrows(S, False), loop=True, ramp="blue",
      feet=FEET, notes="Cold arrows sink."),
    E("status-burn", "Burn", "fire", "status", (64, 64), 8, 12, G.st_burn, loop=True, feet=FEET, notes="Small flames lick up the body."),
    E("status-poison", "Poison", "poison", "status", (64, 64), 8, 10, G.st_poison, loop=True, feet=FEET, notes="Bubbles rise and pop."),
    E("status-paralysis", "Paralysis", "electric", "status", (64, 64), 9, 15, G.st_paralysis, loop=True, feet=FEET,
      notes="Random sparks with an off-beat every third frame."),
    E("status-sleep", "Sleep", "normal", "status", (64, 64), 12, 8, G.st_sleep, loop=True, ramp="blue", feet=FEET,
      notes="Z letters drift up and grow."),
    E("status-freeze", "Freeze", "ice", "status", (64, 64), 8, 8, G.st_freeze, loop=True, feet=FEET,
      notes="Ice crust with a glint sweeping across."),
    E("status-confusion", "Confusion", "normal", "status", (64, 64), 9, 12, G.st_confusion, loop=True, ramp="gold", feet=FEET,
      notes="Three stars orbit above the head, front ones bigger."),
    E("faint-vanish", "Faint Vanish", "normal", "system", (64, 64), 14, 15, G.faint_vanish, ramp="white", feet=FEET,
      notes="Dust ring and rising motes; play over the faint unit animation."),
    E("level-up", "Level Up", "normal", "system", (64, 64), 16, 15, G.level_up, ramp="gold", feet=FEET,
      notes="Gold column, sparkles, chevron and LV UP stamp."),
    E("evolve-glow", "Evolve Glow", "normal", "system", (64, 64), 20, 15, G.evolve_glow, ramp="white", feet=FEET,
      notes="Silhouette blinks white in quickening beats, then a flash hides the swap."),
    E("recall-beam", "Recall Beam", "normal", "system", (64, 64), 14, 15, G.recall_beam, ramp="red", feet=FEET,
      notes="Thin red beam appears at full length; unit shrinks into it."),
    E("send-out", "Send-out Burst", "normal", "system", (64, 64), 12, 15, G.send_out, ramp="white", feet=FEET,
      notes="Floor flash ring and sparkles as a unit appears."),
    E("charge-up", "Charge Up", "normal", "buff", (64, 64), 8, 15, G.charge_up, loop=True, ramp="gold",
      notes="Generic wind-up: particles stream into a pulsing core."),
    # ---------------------------------------------------------------- unit animations
    E("unit-idle", "Idle Bob", "normal", "unit", (64, 64), 6, 6, G.unit_idle, loop=True, ramp="creature", feet=FEET,
      notes="Squash/stretch bob, blink on frame 2."),
    E("unit-lunge", "Attack Lunge", "normal", "unit", (96, 64), 12, 15, G.unit_lunge, ramp="creature", feet=FEET,
      anchor=[20, FEET], notes="Lean back 3f, dash 2f with after-image, hold 2f, return."),
    E("unit-recoil", "Hit Recoil", "normal", "unit", (64, 64), 10, 15, G.unit_recoil, ramp="creature", feet=FEET,
      notes="2 white frames, knockback 7px with jitter, 2 blinks, settle."),
    E("unit-faint", "Faint", "normal", "unit", (64, 64), 14, 12, G.unit_faint, ramp="creature", feet=FEET,
      notes="Stagger, flatten, dither out."),
]
