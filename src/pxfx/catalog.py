"""The effect table (v3 art pass): id, display name, element, kind, frame size, frame count, fps, renderer,
anchor, ground line, layer, notes, battle timing. Names describe element + shape only. All effects run at
30 fps. `ground` is the y of the floor line inside the frame (units stand on it, debris bounces on it)."""
from . import fx3 as X

FPS = 30


def E(id, name, element, kind, size, frames, render, loop=False, anchor=None, ground=None, layer="front",
      ramp=None, notes="", hit=None, hitstop=0, shake=0):
    w, h = size
    g = ground if ground is not None else h - 10
    if anchor is None:
        if kind == "projectile":
            anchor = [w - 16, h // 2]
        elif kind == "beam":
            anchor = [10, h // 2]
        elif kind == "impact":
            anchor = [w // 2, g - 22]
        else:
            anchor = [w // 2, g]
    return dict(id=id, name=name, element=element, kind=kind, frameW=w, frameH=h, frames=frames, fps=FPS,
                loop=loop, anchor=anchor, ground=g, layer=layer, ramp=ramp or element, render=render, notes=notes,
                hit=hit, hitstopMs=hitstop, shake=shake,
                feet=g if kind in ("aura", "status", "buff", "debuff", "unit", "system", "impact") else None)


PRJ, BEAM, IMP, AURA = (96, 48), (192, 64), (128, 96), (64, 96)


def proj(el, **k):
    return lambda S: X.projectile(S, el, **k)


def imp(el, power=1.0, ring=False):
    return lambda S: X.impact(S, el, power=power, ring=ring)


EFFECTS = [
    # normal
    E("normal-star-volley", "Star Volley", "normal", "projectile", PRJ, 24, proj("normal", kind="star"), loop=True,
      notes="Three jagged stars bob in formation, shedding star motes."),
    E("normal-impact-burst", "Impact Burst", "normal", "impact", IMP, 26, imp("normal", 1.0),
      notes="White jagged burst, streak sparks bouncing on the floor, dust puffs, light pulse.", hit=0, hitstop=60, shake=2),
    E("normal-shock-ring", "Shock Ring", "normal", "area", IMP, 30, lambda S: X.shockwave(S, "normal"), layer="ground",
      notes="Two broken, uneven shock rings on the floor kicking up dust (a ring by design)."),
    # fire
    E("fire-fireball", "Fire Ball", "fire", "projectile", PRJ, 24, proj("fire", head=3.2, trail=1.3), loop=True,
      notes="Flickering hot head; flame blobs shed backwards cool white > yellow > red > smoke; embers."),
    E("fire-burst", "Fire Burst", "fire", "impact", IMP, 36, imp("fire", 1.25),
      notes="Flash, jagged burst, flame blobs boil up and turn to drifting smoke, embers fall.", hit=0, hitstop=80, shake=3),
    E("fire-pillar", "Flame Pillar", "fire", "area", (64, 128), 45, lambda S: X.pillar_v3(S, "fire"), ground=120,
      notes="Floor flicker, then a column of rising flame blobs and tongues, sparks at the base, smoke off the top."),
    E("fire-aura", "Flame Aura", "fire", "aura", AURA, 30, lambda S: X.aura_v3(S, "fire", rate=3), loop=True,
      notes="Flames and embers rise along the body edges."),
    # water
    E("water-jet", "Water Jet", "water", "beam", BEAM, 40, lambda S: X.beam_v3(S, "water", width=4.2),
      notes="Gather, then a jittering jet with ragged edges, spray leaving the stream, splash at the end.",
      hit=13, hitstop=40, shake=1),
    E("water-bubble-shot", "Bubble Shot", "water", "projectile", PRJ, 24, proj("water", head=3), loop=True,
      notes="Glossy head with droplets and mist shed behind."),
    E("water-splash", "Water Splash", "water", "impact", IMP, 26, imp("water", 1.2),
      notes="Droplets on gravity arcs bouncing on the floor, mist, light flash.", hit=0, hitstop=50, shake=1),
    E("water-whirlpool", "Whirlpool", "water", "area", (96, 128), 30, lambda S: X.vortex_v3(S, "water"), loop=True,
      ground=120, notes="Droplets riding a rising helix with streak tails; back half dimmer."),
    # grass
    E("grass-leaf-volley", "Leaf Volley", "grass", "projectile", PRJ, 24, proj("grass", head=2.4, trail=1.2), loop=True,
      notes="Small green core shedding tumbling leaves."),
    E("grass-petal-burst", "Petal Burst", "grass", "impact", IMP, 26, imp("grass", 1.0),
      notes="Green flash, leaves burst out and flutter down on turbulence.", hit=0, hitstop=50, shake=1),
    E("grass-leaf-spiral", "Leaf Spiral", "grass", "area", (96, 128), 30, lambda S: X.vortex_v3(S, "grass"), loop=True,
      ground=120, notes="Leaves riding a rising helix."),
    # electric
    E("electric-spark-ball", "Spark Ball", "electric", "projectile", PRJ, 24, proj("electric", head=2.8), loop=True,
      notes="Crackling core with bolts redrawn every frame and sparks."),
    E("electric-thunder-strike", "Thunder Strike", "electric", "impact", (96, 128), 30,
      lambda S: X.impact(S, "electric", 1.1), ground=118,
      notes="Bolt flicker drawn by the impact core plus sparks; see combo for the strike.", hit=0, hitstop=80, shake=3),
    E("electric-static-aura", "Static Aura", "electric", "aura", AURA, 30, lambda S: X.aura_v3(S, "electric", rate=2),
      loop=True, notes="Sparks crawl up the body edges."),
    # ice
    E("ice-shards", "Ice Shards", "ice", "projectile", PRJ, 24, proj("ice", head=2.6), loop=True,
      notes="Pale core shedding glinting shards and snow motes."),
    E("ice-beam", "Ice Beam", "ice", "beam", BEAM, 40, lambda S: X.beam_v3(S, "ice", width=3.6),
      notes="Jittering pale beam with crystals budding off the edges, shards breaking away.", hit=13, hitstop=40, shake=1),
    E("ice-shatter", "Frost Shatter", "ice", "impact", IMP, 26, imp("ice", 1.1),
      notes="Shards burst out, bounce and glint; snow drifts.", hit=0, hitstop=60, shake=2),
    E("ice-blizzard", "Blizzard Field", "ice", "area", IMP, 30, lambda S: X.weather_v3(S, "ice"), loop=True,
      notes="Diagonal snow on wind streaks over a frosted floor line."),
    # fighting
    E("fighting-force-wave", "Force Wave", "fighting", "projectile", (96, 64), 24, lambda S: X.waves_v3(S, "fighting", 3),
      loop=True, anchor=[4, 32], notes="Tapered force crescents thinning as they travel."),
    E("fighting-power-hit", "Power Hit", "fighting", "impact", IMP, 26, imp("fighting", 1.4),
      notes="Big jagged burst, long streak sparks, dust and smoke on the floor.", hit=0, hitstop=100, shake=4),
    E("fighting-power-aura", "Power Aura", "fighting", "aura", AURA, 30,
      lambda S: X.aura_v3(S, "fighting", rate=2, kind="line"), loop=True, notes="Fast rising streaks (power-up)."),
    # poison
    E("poison-sludge-glob", "Sludge Glob", "poison", "projectile", PRJ, 24, proj("poison", head=3.2), loop=True,
      notes="Heavy glob shedding drips that fall away, bubbles."),
    E("poison-toxic-splash", "Toxic Splash", "poison", "impact", IMP, 26, imp("poison", 1.1),
      notes="Goo drops bounce, bubbles rise, gas puffs.", hit=0, hitstop=50, shake=1),
    E("poison-cloud", "Poison Cloud", "poison", "area", IMP, 30, lambda S: X.cloud_v3(S, "poison"), loop=True,
      notes="Translucent gas puffs drift and break apart; bubbles pop."),
    # ground
    E("ground-mud-ball", "Mud Ball", "ground", "projectile", PRJ, 24, proj("ground", head=3.6, kind="ground"), loop=True,
      notes="Tumbling clod with a dust trail."),
    E("ground-quake", "Quake Cracks", "ground", "area", (160, 96), 36, lambda S: X.quake_v3(S, "ground"), layer="ground",
      notes="Forked cracks race out glowing then cool; chunks pop and bounce; dust.", hit=3, hitstop=0, shake=4),
    E("ground-dust-burst", "Dust Burst", "ground", "impact", IMP, 26, imp("ground", 1.2),
      notes="Chunks bounce on the floor, dust rolls out and thins.", hit=0, hitstop=60, shake=2),
    # flying
    E("flying-air-blade", "Air Blade", "flying", "projectile", PRJ, 18, lambda S: X.blade(S, "flying", 1), loop=True,
      notes="Tapered crescent of wind with streaks."),
    E("flying-gust-burst", "Gust Burst", "flying", "impact", IMP, 24, imp("flying", 1.0),
      notes="Airy jagged burst with long wind streaks.", hit=0, hitstop=40, shake=1),
    E("flying-tornado", "Tornado", "flying", "area", (96, 128), 30, lambda S: X.vortex_v3(S, "flying"), loop=True,
      ground=120, notes="Wind streaks riding a rising helix, dust at the base."),
    # psychic
    E("psychic-psy-beam", "Psy Beam", "psychic", "beam", BEAM, 40, lambda S: X.beam_v3(S, "psychic", width=3.4),
      notes="Pink jittering beam shedding motes.", hit=13, hitstop=40, shake=1),
    E("psychic-psy-burst", "Psy Burst", "psychic", "impact", IMP, 26, imp("psychic", 1.1, ring=True),
      notes="Jagged pink burst, swirling motes, broken shock ring on the floor.", hit=0, hitstop=60, shake=2),
    E("psychic-mind-field", "Mind Field", "psychic", "aura", AURA, 30, lambda S: X.aura_v3(S, "psychic", rate=2),
      loop=True, notes="Motes float up and swirl around the unit."),
    # bug
    E("bug-buzz-wave", "Buzz Wave", "bug", "projectile", (96, 64), 24, lambda S: X.waves_v3(S, "bug", 4), loop=True,
      anchor=[4, 32], notes="Thin tapered sound crescents with buzzing motes."),
    E("bug-sting-volley", "Sting Volley", "bug", "projectile", PRJ, 24, proj("bug", head=2.2), loop=True,
      notes="Sharp green core with tiny bugs shed behind."),
    E("bug-sting-hit", "Sting Hit", "bug", "impact", IMP, 24, imp("bug", 0.8),
      notes="Small sharp burst, bugs scatter.", hit=0, hitstop=40, shake=1),
    E("bug-swarm", "Swarm", "bug", "area", (96, 96), 30, lambda S: X.swarm_v3(S, "bug"), loop=True,
      notes="Bugs ride a curl-noise flow around the centre."),
    # rock
    E("rock-boulder", "Boulder Throw", "rock", "projectile", PRJ, 24, proj("rock", head=4.5, kind="rock"), loop=True,
      notes="Faceted rock tumbling, outlined, dust trail and speed streaks."),
    E("rock-smash", "Rock Smash", "rock", "impact", IMP, 36, imp("rock", 1.3),
      notes="Heavy chips bounce twice, dust and smoke roll.", hit=0, hitstop=80, shake=3),
    E("rock-stone-spikes", "Stone Spikes", "rock", "area", (160, 96), 45, lambda S: X.spikes_v3(S, "rock"),
      notes="Noise-edged stone shards stab up in sequence, chips and dust, crumble back.", hit=2, hitstop=60, shake=2),
    # ghost
    E("ghost-shadow-orb", "Shadow Orb", "ghost", "projectile", PRJ, 24, proj("ghost", head=3.2), loop=True,
      notes="Dark-cored orb trailing wisps that smoke out."),
    E("ghost-hex-burst", "Hex Burst", "ghost", "impact", IMP, 26, imp("ghost", 1.1),
      notes="Purple burst, wisps writhe up and smoke away.", hit=0, hitstop=60, shake=1),
    E("ghost-spirit-wisps", "Spirit Wisps", "ghost", "aura", AURA, 30, lambda S: X.aura_v3(S, "ghost", rate=2),
      loop=True, notes="Wisps writhe up and fade to smoke."),
    # dragon
    E("dragon-pulse-beam", "Dragon Beam", "dragon", "beam", BEAM, 40, lambda S: X.beam_v3(S, "dragon", width=4.6),
      notes="Thick blue-teal jittering beam shedding cold flames.", hit=13, hitstop=60, shake=2),
    E("dragon-burst", "Dragon Burst", "dragon", "impact", IMP, 36, imp("dragon", 1.25),
      notes="Cold-flame burst boiling up, embers.", hit=0, hitstop=80, shake=3),
    E("dragon-aura", "Dragon Aura", "dragon", "aura", AURA, 30, lambda S: X.aura_v3(S, "dragon", rate=3), loop=True,
      notes="Blue flames rise along the body."),
    # dark
    E("dark-night-claw", "Night Claw", "dark", "impact", IMP, 24, lambda S: X.slash_v3(S, "dark", count=3, claw=True),
      notes="Three tapered rakes, hot edge cooling to plum, sparks.", hit=2, hitstop=60, shake=2),
    E("dark-pulse", "Dark Pulse", "dark", "area", IMP, 30, lambda S: X.shockwave(S, "dark", dark=True), layer="ground",
      notes="Dark broken rings spread from a black core with wisps (a ring by design)."),
    E("dark-orb", "Dark Orb", "dark", "projectile", PRJ, 24, proj("dark", head=3), loop=True,
      notes="Black-plum orb trailing writhing wisps."),
    # steel
    E("steel-beam", "Steel Beam", "steel", "beam", BEAM, 40, lambda S: X.beam_v3(S, "steel", width=4.0),
      notes="Silver jittering beam throwing metal sparks.", hit=13, hitstop=60, shake=2),
    E("steel-metal-spark", "Metal Spark", "steel", "impact", IMP, 26, imp("steel", 1.1),
      notes="Clang: many streak sparks arc down and bounce.", hit=0, hitstop=60, shake=2),
    E("steel-iron-spikes", "Iron Spikes", "steel", "area", (160, 96), 45, lambda S: X.spikes_v3(S, "steel"),
      notes="Polished noise-edged spikes rise in sequence.", hit=2, hitstop=60, shake=2),
    E("steel-slash", "Steel Slash", "steel", "impact", IMP, 24, lambda S: X.slash_v3(S, "steel", count=1),
      notes="Tapered crescent sweep, hot edge, sparks off the tip.", hit=1, hitstop=60, shake=2),
    # fairy
    E("fairy-moon-orb", "Moon Orb", "fairy", "projectile", PRJ, 24, proj("fairy", head=3), loop=True,
      notes="Pink orb leaving twinkling stars."),
    E("fairy-sparkle-burst", "Sparkle Burst", "fairy", "impact", IMP, 26, imp("fairy", 1.0),
      notes="Soft jagged burst, stars and hearts drift.", hit=0, hitstop=50, shake=1),
    E("fairy-ring-aura", "Fairy Ring", "fairy", "aura", AURA, 30, lambda S: X.aura_v3(S, "fairy", rate=2), loop=True,
      notes="Stars and hearts rise around the unit."),
    # generic
    E("hit-spark", "Hit Spark", "normal", "impact", (64, 64), 12, lambda S: X.burst_generic(S, 0.7), ramp="white",
      anchor=[32, 32], ground=56, notes="Smallest hit, 400 ms: jagged spark + streaks + light.", hit=0, hitstop=40, shake=1),
    E("crit-hit", "Critical Hit", "normal", "impact", IMP, 24, lambda S: X.burst_generic(S, 1.4, second=True),
      ramp="gold", notes="Two-beat crit: big jagged burst, then a second pop.", hit=0, hitstop=120, shake=4),
    E("crit-cutin", "Crit Cut-in", "normal", "system", (160, 96), 8, X.cutin_v3, ramp="white", layer="screen",
      anchor=[0, 0], notes="Opaque screen plate with tapered speed lines for a few frames on crits and K.O.s."),
    E("miss", "Miss", "normal", "system", AURA, 24, X.miss_v3, ramp="white", notes="After-images slide off, dust, MISS pops."),
    E("shield", "Shield Dome", "steel", "buff", (96, 96), 30, X.shield_v3, loop=True, ramp="shield",
      notes="Broken shimmering barrier edge, hex glints, motes sliding along it."),
    E("heal", "Heal", "grass", "buff", AURA, 30, X.heal_v3, loop=True, ramp="heal", notes="Plus glyphs and sparkles rise."),
    E("stat-up", "Stat Up", "normal", "buff", AURA, 30, lambda S: X.stat_v3(S, True), loop=True, ramp="red",
      notes="Chevrons and streaks flow up."),
    E("stat-down", "Stat Down", "normal", "debuff", AURA, 30, lambda S: X.stat_v3(S, False), loop=True, ramp="blue",
      notes="Chevrons and streaks sink."),
    E("status-burn", "Burn", "fire", "status", AURA, 30, lambda S: X.status_v3(S, "burn"), loop=True,
      notes="Small flames and embers on the body."),
    E("status-poison", "Poison", "poison", "status", AURA, 30, lambda S: X.status_v3(S, "poison"), loop=True,
      notes="Tiny bubbles rise, drips fall."),
    E("status-paralysis", "Paralysis", "electric", "status", AURA, 30, lambda S: X.status_v3(S, "paralysis"), loop=True,
      notes="Tiny bolts and sparks, off-beat every third frame."),
    E("status-sleep", "Sleep", "normal", "status", AURA, 28, lambda S: X.status_v3(S, "sleep"), loop=True, ramp="blue",
      notes="Z glyphs drift up and grow."),
    E("status-freeze", "Freeze", "ice", "status", AURA, 30, lambda S: X.status_v3(S, "freeze"), loop=True,
      notes="Ice crust at the feet, falling frost motes, a glint sweeping across."),
    E("status-confusion", "Confusion", "normal", "status", AURA, 30, lambda S: X.status_v3(S, "confusion"), loop=True,
      ramp="gold", notes="Three tiny stars circle above the head with trails."),
    E("faint-vanish", "Faint Vanish", "normal", "system", AURA, 36, X.faint_v3, ramp="white",
      notes="Dust puff and rising motes; play over the faint animation."),
    E("level-up", "Level Up", "normal", "system", AURA, 45, lambda S: X.sparkle_burst(S, text="LV UP", rise=True),
      ramp="gold", notes="Light flash, rising streaks and stars, LV UP stamp."),
    E("evolve-glow", "Evolve Glow", "normal", "system", AURA, 60, X.evolve_v3, ramp="white",
      notes="Silhouette beats white faster and faster in rising light, ends in a flash."),
    E("recall-beam", "Recall Beam", "normal", "system", AURA, 36, X.recall_v3, ramp="red",
      notes="Jittering red beam; unit turns red, shrinks and lifts away in motes."),
    E("send-out", "Send-out Burst", "normal", "system", AURA, 30, lambda S: X.sparkle_burst(S), ramp="white",
      notes="Light flash and stars bursting as a unit appears."),
    E("charge-up", "Charge Up", "normal", "buff", (64, 64), 24, lambda S: X.converge(S), loop=True, ramp="gold",
      anchor=[32, 32], ground=56, notes="Streaks spiral into a flickering core with growing light."),
    # unit animations
    E("unit-idle", "Idle Bob", "normal", "unit", (64, 64), 24, lambda S: X.unit_v3(S, "idle"), loop=True,
      ramp="creature", ground=56, notes="Breathing squash/stretch, blink."),
    E("unit-lunge", "Attack Lunge", "normal", "unit", (96, 64), 30, lambda S: X.unit_v3(S, "lunge"), ramp="creature",
      ground=56, anchor=[22, 56], notes="Crouch wind-up held 7f, dash 2f with smear ghosts, contact freeze 4f, recover.",
      hit=9),
    E("unit-recoil", "Hit Recoil", "normal", "unit", (64, 64), 24, lambda S: X.unit_v3(S, "recoil"), ramp="creature",
      ground=56, notes="3 white frames, 3 frozen frames, knockback with shake, blinks, settle.", hit=0),
    E("unit-faint", "Faint", "normal", "unit", (64, 64), 36, lambda S: X.unit_v3(S, "faint"), ramp="creature",
      ground=56, notes="Wobble, flatten, dissolve."),
]
