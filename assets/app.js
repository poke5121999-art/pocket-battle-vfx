/* Pocket Battle VFX gallery: grid, filters, detail view and combo preview.
   Plain browser JS, no build step. Every effect is a pre-rendered sprite sheet listed in fx.json. */
(() => {
  "use strict";
  const $ = (s, el = document) => el.querySelector(s);
  const el = (tag, props = {}, kids = []) => {
    const n = Object.assign(document.createElement(tag), props);
    for (const k of kids) n.append(k);
    return n;
  };
  const imgCache = new Map();
  const loadImg = (src) => {
    if (!imgCache.has(src)) {
      imgCache.set(src, new Promise((res, rej) => {
        const i = new Image();
        i.onload = () => res(i);
        i.onerror = () => rej(new Error("image not loaded: " + src));
        i.src = src;
      }));
    }
    return imgCache.get(src);
  };

  // effects that already draw the creature themselves, or where it must be absent
  const NO_DUMMY = new Set(["evolve-glow", "recall-beam", "faint-vanish", "send-out", "miss", "crit-cutin", "charge-up"]);
  const DUMMY_KINDS = new Set(["aura", "status", "buff", "debuff", "impact", "system"]);
  const ELEMENT_ORDER = ["normal", "fire", "water", "grass", "electric", "ice", "fighting", "poison", "ground", "flying",
    "psychic", "bug", "rock", "ghost", "dragon", "dark", "steel", "fairy"];
  const KIND_ORDER = ["projectile", "beam", "impact", "area", "aura", "buff", "debuff", "status", "system", "unit"];

  let FX = [], BYID = {}, backdrop = null, dummy = null, dummyFlip = null;
  const state = { el: "all", kind: "all", q: "" };

  // ------------------------------------------------------------------ drawing
  function frameRect(d, i) {
    const c = d.sheet.columns;
    return [(i % c) * d.frameW, Math.floor(i / c) * d.frameH, d.frameW, d.frameH];
  }
  function drawFrame(ctx, d, img, i, x, y, flip = false) {
    const [sx, sy, w, h] = frameRect(d, i);
    if (!flip) { ctx.drawImage(img, sx, sy, w, h, Math.round(x), Math.round(y), w, h); return; }
    ctx.save();
    ctx.translate(Math.round(x) + w, Math.round(y));
    ctx.scale(-1, 1);
    ctx.drawImage(img, sx, sy, w, h, 0, 0, w, h);
    ctx.restore();
  }
  function fillBackdrop(ctx, w, h, ox = 0, oy = 0) {
    if (!backdrop) { ctx.fillStyle = "#2c3b3a"; ctx.fillRect(0, 0, w, h); return; }
    for (let y = -oy; y < h; y += backdrop.height)
      for (let x = -ox; x < w; x += backdrop.width) ctx.drawImage(backdrop, x, y);
  }
  function wantsDummy(d) {
    return DUMMY_KINDS.has(d.kind) && d.layer !== "screen" && !NO_DUMMY.has(d.id);
  }
  // where the dummy's feet go inside the effect frame
  function dummyFeet(d) {
    if (d.kind === "impact") return [d.anchor[0], Math.min(d.frameH - 4, d.anchor[1] + 16)];
    return [d.anchor[0], d.anchor[1]];
  }
  function drawDummy(ctx, fx, fy, flip) {
    const im = flip ? dummyFlip : dummy;
    if (im) ctx.drawImage(im, Math.round(fx - 32), Math.round(fy - 56));
  }
  function mirrorImage(img) {
    const c = el("canvas", { width: img.width, height: img.height });
    const x = c.getContext("2d");
    x.translate(img.width, 0); x.scale(-1, 1); x.drawImage(img, 0, 0);
    return c;
  }

  // A player renders one effect into a canvas at native resolution (CSS scales it, pixelated).
  class Player {
    constructor(canvas, d, opts = {}) {
      this.cv = canvas; this.d = d;
      this.ctx = canvas.getContext("2d");
      this.fps = d.fps; this.loop = d.loop; this.playing = true;
      this.showBg = opts.bg !== false; this.showDummy = opts.dummy !== false;
      this.t = 0; this.hold = 0; this.forced = null;
      this.travel = d.kind === "projectile";
      // normalise the stage: wide things 2:1, everything else square, so grid rows line up
      if (this.travel || d.frameW >= 128) { this.w = Math.max(128, d.frameW); this.h = Math.max(this.w / 2, d.frameH); }
      else { this.w = this.h = Math.max(d.frameW, d.frameH); }
      this.ox = Math.round((this.w - d.frameW) / 2);
      this.oy = d.kind === "impact" ? Math.round((this.h - d.frameH) / 2) : this.h - d.frameH;
      canvas.width = this.w; canvas.height = this.h;
      this.img = null;
      loadImg(d.sheet.image).then((i) => { this.img = i; this.draw(); });
    }
    get frame() {
      if (this.forced !== null) return this.forced;
      const n = this.d.frames, f = Math.floor(this.t * this.fps);
      return this.loop ? f % n : Math.min(n - 1, f);
    }
    restart() { this.t = 0; this.hold = 0; this.forced = null; }
    tick(dt) {
      if (!this.playing) return;
      this.forced = null;
      this.t += dt;
      const dur = this.d.frames / this.fps;
      if (!this.loop && this.t >= dur) {
        this.hold += dt;
        if (this.hold > 0.7) this.restart();
      }
      if (this.travel && this.t > 1e6) this.t = 0;
      this.draw();
    }
    draw() {
      const { ctx, d } = this;
      ctx.clearRect(0, 0, this.w, this.h);
      if (this.showBg) fillBackdrop(ctx, this.w, this.h);
      if (!this.img) return;
      if (this.travel) {
        const speed = 90; // px per second across the card
        const span = this.w + d.frameW;
        const x = ((this.t * speed) % span) - d.frameW + (this.forced !== null ? span / 2 : 0);
        drawFrame(ctx, d, this.img, this.frame, x, Math.round(this.h / 2 - d.anchor[1]));
        return;
      }
      const dm = this.showDummy && wantsDummy(d);
      const [fx, fy] = dummyFeet(d);
      const flip = d.kind === "impact";
      const ox = this.ox, oy = this.oy;
      if (dm && d.layer !== "ground") drawDummy(ctx, fx + ox, fy + oy, flip);
      drawFrame(ctx, d, this.img, this.frame, ox, oy);
      if (dm && d.layer === "ground") drawDummy(ctx, fx + ox, fy + oy, flip);
    }
  }

  // ------------------------------------------------------------------ grid
  const cards = [];
  function elementColor(e) {
    const d = FX.find((x) => x.element === e);
    return d ? d.palette[3] : "#888";
  }
  function buildChips() {
    const mk = (box, key, val, label, count, color) => {
      const b = el("button", { className: "chip", type: "button" });
      if (color) b.append(el("i", { style: `background:${color}` }));
      b.append(label, " ", el("span", { textContent: count }));
      b.dataset.v = val;
      b.addEventListener("click", () => {
        state[key] = val; syncChips(); filter(); writeHash();
        const g = $("#grid").getBoundingClientRect();
        if (g.top > window.innerHeight * 0.6) $("#grid").scrollIntoView({ behavior: "smooth" });
      });
      box.append(b);
    };
    const E = $("#elements"), K = $("#kinds");
    mk(E, "el", "all", "all", FX.length);
    for (const e of ELEMENT_ORDER) {
      const n = FX.filter((d) => d.element === e).length;
      if (n) mk(E, "el", e, e, n, elementColor(e));
    }
    mk(K, "kind", "all", "all", FX.length);
    for (const k of KIND_ORDER) {
      const n = FX.filter((d) => d.kind === k).length;
      if (n) mk(K, "kind", k, k, n);
    }
  }
  function syncChips() {
    for (const b of document.querySelectorAll("#elements .chip")) b.setAttribute("aria-pressed", String(b.dataset.v === state.el));
    for (const b of document.querySelectorAll("#kinds .chip")) b.setAttribute("aria-pressed", String(b.dataset.v === state.kind));
  }
  function writeHash() {
    const parts = [];
    if (state.el !== "all") parts.push(state.el);
    if (state.kind !== "all") parts.push(state.kind);
    history.replaceState(null, "", parts.length ? "#" + parts.join("/") : location.pathname);
  }
  function readHash() {
    const h = decodeURIComponent(location.hash.slice(1));
    if (!h || h === "combo") return;
    for (const p of h.split("/")) {
      if (ELEMENT_ORDER.includes(p)) state.el = p;
      if (KIND_ORDER.includes(p)) state.kind = p;
      if (p.startsWith("fx=")) setTimeout(() => openDetail(BYID[p.slice(3)]), 0);
    }
  }
  function buildGrid() {
    const grid = $("#grid");
    const io = "IntersectionObserver" in window ? new IntersectionObserver((ents) => {
      for (const en of ents) en.target._card.visible = en.isIntersecting;
    }, { rootMargin: "100px" }) : null;
    for (const d of FX) {
      const cv = el("canvas", { "aria-label": d.name + " preview" });
      const dur = d.loop ? "loop" : (d.durationMs / 1000).toFixed(2) + " s";
      const fig = el("figure", { className: "card", tabIndex: 0 }, [cv, el("figcaption", {}, [
        el("b", {}, [el("i", { className: "tag", style: `background:${d.palette[3]}` }), d.name]),
        el("span", { textContent: `${d.frames}f · ${dur}` })])]);
      if (d.frameW >= 128 || d.kind === "projectile") fig.classList.add("wide");
      fig.addEventListener("click", () => openDetail(d));
      fig.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openDetail(d); } });
      grid.append(fig);
      const card = { d, fig, player: new Player(cv, d), visible: !io };
      fig._card = card;
      if (io) io.observe(fig);
      cards.push(card);
    }
  }
  function filter() {
    const q = state.q.trim().toLowerCase();
    let shown = 0;
    for (const c of cards) {
      const d = c.d;
      const hay = [d.id, d.name, d.element, d.kind, d.notes, d.loop ? "loop" : "one-shot", d.layer].join(" ").toLowerCase();
      const ok = (state.el === "all" || d.element === state.el) && (state.kind === "all" || d.kind === state.kind) &&
        (!q || q.split(/\s+/).every((w) => hay.includes(w)));
      c.fig.hidden = !ok;
      shown += ok;
    }
    $("#none").hidden = shown > 0;
    $("#shown").textContent = `${shown} / ${FX.length}`;
  }

  // ------------------------------------------------------------------ detail
  let detail = null; // { d, player, scale }
  function openDetail(d) {
    if (!d) return;
    const dlg = $("#detail");
    const cv = $("#d-cv");
    const p = new Player(cv, d, { bg: true, dummy: true });
    detail = { d, player: p, scale: d.frameW >= 128 || p.w >= 128 ? 3 : 4 };
    $("#d-name").textContent = d.name;
    $("#d-id").textContent = `fx/${d.id} · ${d.element} · ${d.kind}`;
    $("#d-notes").textContent = d.notes;
    const facts = [
      ["frames", `${d.frames} × ${d.frameW}×${d.frameH} px`],
      ["timing", `${d.fps} fps · ${d.durationMs} ms · ${d.loop ? "loops" : "plays once"}`],
      ["anchor", `[${d.anchor.join(", ")}] (px in frame)`],
      ["layer", d.layer],
      ["sheet", `${d.sheet.columns} × ${d.sheet.rows} grid, ${d.sheet.width}×${d.sheet.height} px`],
    ];
    if (d.battle) {
      const b = d.battle, parts = [];
      if (b.hitFrame !== undefined) parts.push(`hit on frame ${b.hitFrame}`);
      if (b.hitStopMs) parts.push(`${b.hitStopMs} ms hit-stop`);
      if (b.shakePx) parts.push(`${b.shakePx} px shake`);
      facts.push(["battle", parts.join(" · ")]);
    }
    const dl = $("#d-facts");
    dl.replaceChildren();
    for (const [k, v] of facts) dl.append(el("dt", { textContent: k }), el("dd", { textContent: v }));
    const sw = el("dd", { className: "swatches" });
    for (const c of d.palette) sw.append(el("i", { title: c, style: `background:${c}` }));
    dl.append(el("dt", { textContent: "palette" }), sw);
    $("#d-fps").value = d.fps; $("#d-fps-o").textContent = d.fps + " fps";
    setPressed("#d-loop", p.loop); setPressed("#d-play", true); $("#d-play").textContent = "pause";
    setPressed("#d-bg", true); setPressed("#d-dummy", wantsDummy(d));
    $("#d-dummy").disabled = !wantsDummy(d);
    const sc = $("#d-scale");
    sc.replaceChildren(el("span", { className: "k", textContent: "scale" }));
    for (const s of [1, 2, 3, 4]) {
      const b = el("button", { className: "btn", type: "button", textContent: "×" + s });
      b.addEventListener("click", () => { detail.scale = s; applyScale(); });
      b.dataset.s = s;
      sc.append(b);
    }
    applyScale();
    $("#d-png").href = d.sheet.image; $("#d-png").download = d.id + ".png";
    $("#d-json").href = `fx/${d.id}.json`; $("#d-json").download = d.id + ".json";
    $("#d-gif").href = d.gif; $("#d-gif").download = d.id + ".gif";
    buildStrip(d);
    history.replaceState(null, "", "#fx=" + d.id);
    if (!dlg.open) dlg.showModal();
    applyScale();
  }
  function applyScale() {
    const { player, scale } = detail;
    const cv = player.cv;
    // never overflow the view: fall back to the largest whole scale that fits
    const box = $(".dview");
    const availW = Math.max(64, box.clientWidth - 32), availH = Math.max(64, window.innerHeight * 0.62);
    const fit = Math.max(1, Math.min(scale, Math.floor(availW / player.w), Math.floor(availH / player.h)));
    cv.style.width = player.w * fit + "px";
    cv.style.height = player.h * fit + "px";
    cv.title = fit < scale ? `shown at ×${fit} (×${scale} does not fit this screen)` : "";
    for (const b of document.querySelectorAll("#d-scale .btn")) setPressed(b, +b.dataset.s === scale);
  }
  async function buildStrip(d) {
    const box = $("#d-frames");
    box.replaceChildren();
    $("#d-cap").textContent = `frame strip — ${d.frames} frames, click one to hold it`;
    const img = await loadImg(d.sheet.image);
    const s = d.frameH > 64 ? 1 : 2;
    for (let i = 0; i < d.frames; i++) {
      const c = el("canvas", { width: d.frameW, height: d.frameH, title: "frame " + i });
      c.style.width = d.frameW * s + "px"; c.style.height = d.frameH * s + "px";
      const x = c.getContext("2d");
      drawFrame(x, d, img, i, 0, 0);
      c.addEventListener("click", () => {
        detail.player.playing = false; detail.player.forced = i; detail.player.draw();
        setPressed("#d-play", false); $("#d-play").textContent = "play";
        markStrip(i);
      });
      box.append(c);
    }
  }
  function markStrip(i) {
    const cs = $("#d-frames").children;
    for (let k = 0; k < cs.length; k++) cs[k].classList.toggle("on", k === i);
  }
  function setPressed(sel, v) {
    const b = typeof sel === "string" ? $(sel) : sel;
    b.setAttribute("aria-pressed", String(!!v));
  }
  function wireDetail() {
    const dlg = $("#detail");
    $("#d-close").addEventListener("click", () => dlg.close());
    dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });
    dlg.addEventListener("close", () => { detail = null; writeHash(); });
    $("#d-play").addEventListener("click", (e) => {
      const p = detail.player; p.playing = !p.playing;
      if (p.playing) p.forced = null;
      e.target.textContent = p.playing ? "pause" : "play"; setPressed(e.target, p.playing);
    });
    $("#d-again").addEventListener("click", () => { const p = detail.player; p.restart(); p.playing = true; $("#d-play").textContent = "pause"; setPressed("#d-play", true); });
    $("#d-loop").addEventListener("click", (e) => { const p = detail.player; p.loop = !p.loop; setPressed(e.target, p.loop); p.restart(); });
    $("#d-fps").addEventListener("input", (e) => { detail.player.fps = +e.target.value; $("#d-fps-o").textContent = e.target.value + " fps"; });
    $("#d-bg").addEventListener("click", (e) => { const p = detail.player; p.showBg = !p.showBg; setPressed(e.target, p.showBg); p.draw(); });
    $("#d-dummy").addEventListener("click", (e) => { const p = detail.player; p.showDummy = !p.showDummy; setPressed(e.target, p.showDummy); p.draw(); });
  }

  // ------------------------------------------------------------------ combo preview
  const combo = { running: false, clock: 0, freeze: 0, actors: [], events: [], shake: 0, flash: 0, dmg: null, slow: false, crit: false };
  const CASTER = [80, 132], TARGET = [240, 112];
  function fillSelect(sel, list, def, none) {
    const s = $(sel);
    if (none) s.append(el("option", { value: "", textContent: "— none —" }));
    for (const d of list) s.append(el("option", { value: d.id, textContent: `${d.name} (${d.element})` }));
    s.value = def;
  }
  function addActor(id, x, y, opts = {}) {
    const d = BYID[id];
    if (!d) return null;
    const a = Object.assign({ d, x, y, start: combo.clock, loop: d.loop, flip: false, until: Infinity, img: null }, opts);
    loadImg(d.sheet.image).then((i) => (a.img = i));
    combo.actors.push(a);
    return a;
  }
  function at(t, fn) { combo.events.push({ t, fn }); }
  function step(name) {
    for (const li of document.querySelectorAll("#c-steps li")) li.classList.toggle("on", li.dataset.s === name);
  }
  function playCombo() {
    const atk = BYID[$("#c-attack").value], imp = BYID[$("#c-impact").value], st = BYID[$("#c-status").value];
    Object.assign(combo, { clock: 0, freeze: 0, actors: [], events: [], shake: 0, flash: 0, dmg: null, running: true });
    const casterIdle = addActor("unit-idle", CASTER[0] - 32, CASTER[1] - 56, { until: 0 });
    const targetIdle = addActor("unit-idle", TARGET[0] - 32, TARGET[1] - 56, { flip: true });
    const lungeD = BYID["unit-lunge"];
    // 1. caster wind-up + lunge
    step("lunge");
    const lunge = addActor("unit-lunge", CASTER[0] - lungeD.anchor[0] - 6, CASTER[1] - 56);
    lunge.until = lungeD.frames / lungeD.fps;
    at(lunge.until, () => addActor("unit-idle", CASTER[0] - 32, CASTER[1] - 56));
    const release = 4 / lungeD.fps; // dash frame
    const sx = CASTER[0] + 14, sy = CASTER[1] - 18, tx = TARGET[0] - 4, ty = TARGET[1] - 18;
    const dist = Math.hypot(tx - sx, ty - sy), ang = Math.atan2(ty - sy, tx - sx);
    let hitAt;
    at(release, () => step("attack"));
    if (atk.kind === "beam") {
      const hf = (atk.battle && atk.battle.hitFrame) || 9;
      hitAt = release + hf / atk.fps;
      const reach = atk.frameW - atk.anchor[0];
      at(release, () => addActor(atk.id, sx, sy, { beam: { ang, sx: (dist + 6) / reach }, until: atk.frames / atk.fps }));
    } else {
      const speed = 200; // px/s
      const travel = dist / speed;
      hitAt = release + travel;
      at(release, () => addActor(atk.id, sx, sy, { path: { sx, sy, tx, ty, dur: travel }, until: travel }));
    }
    const stop = ((imp.battle && imp.battle.hitStopMs) || 60) / 1000 + (combo.crit ? 0.12 : 0);
    const shake = ((imp.battle && imp.battle.shakePx) || 2) + (combo.crit ? 2 : 0);
    // 2. contact: crit cut-in plate, freeze, shake, flash
    at(hitAt, () => {
      step("hit");
      if (combo.crit) addActor("crit-cutin", 0, 0, { screen: true, fps: 24, until: 0.24 });
      combo.freeze = stop; combo.shake = shake; combo.flash = 2;
      const iy = imp.kind === "impact" ? TARGET[1] - 16 - imp.anchor[1] : TARGET[1] - imp.anchor[1];
      const impD = combo.crit ? BYID["crit-hit"] : imp;
      const imp2 = addActor(imp.id, TARGET[0] - imp.anchor[0], iy, { until: imp.frames / imp.fps, delay: true });
      if (combo.crit) addActor(impD.id, TARGET[0] - impD.anchor[0], TARGET[1] - 16 - impD.anchor[1], { until: impD.frames / impD.fps });
      targetIdle.until = combo.clock;
      const rec = BYID["unit-recoil"];
      addActor("unit-recoil", TARGET[0] - 32, TARGET[1] - 56, { flip: true, until: rec.frames / rec.fps });
      at(combo.clock + rec.frames / rec.fps, () => addActor("unit-idle", TARGET[0] - 32, TARGET[1] - 56, { flip: true }));
      combo.dmg = { v: combo.crit ? 87 : 42, t: combo.clock, x: TARGET[0], y: TARGET[1] - 40, crit: combo.crit };
      at(combo.clock + 0.15, () => step("impact"));
      if (st) {
        at(combo.clock + 0.6, () => {
          step("status");
          const sy2 = st.layer === "ground" ? TARGET[1] - st.anchor[1] : TARGET[1] - st.anchor[1];
          addActor(st.id, TARGET[0] - st.anchor[0], sy2, { until: 2.6, front: st.layer !== "ground" });
        });
      }
      at(combo.clock + 3.4, () => { combo.running = false; step(""); });
    });
    casterIdle.until = 0;
  }
  function comboTick(dt) {
    const cv = $("#combo-cv"), ctx = cv.getContext("2d");
    if (combo.slow) dt *= 0.25;
    if (combo.running) {
      if (combo.freeze > 0) combo.freeze -= dt; // hit-stop: the clock stands still
      else {
        combo.clock += dt;
        combo.events.sort((a, b) => a.t - b.t);
        while (combo.events.length && combo.events[0].t <= combo.clock) combo.events.shift().fn();
      }
    }
    // shake: whole-pixel offsets, alternating, decaying
    let ox = 0, oy = 0;
    if (combo.shake > 0.5) {
      const s = Math.round(combo.shake);
      ox = (Math.floor(performance.now() / 40) % 2 ? s : -s); oy = (Math.floor(performance.now() / 55) % 2 ? 1 : -1) * Math.floor(s / 2);
      combo.shake *= Math.pow(0.02, dt);
    }
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.imageSmoothingEnabled = false;
    ctx.fillStyle = "#000"; ctx.fillRect(0, 0, cv.width, cv.height);
    ctx.setTransform(1, 0, 0, 1, ox, oy);
    if (backdrop) ctx.drawImage(backdropFull || backdrop, 0, 0);
    combo.actors = combo.actors.filter((a) => combo.clock - a.start <= a.until || !combo.running && a.until === Infinity);
    const layer = (a) => (a.screen ? 3 : a.d.layer === "ground" ? 0 : a.d.kind === "unit" ? 1 : 2);
    const sorted = [...combo.actors].sort((a, b) => layer(a) - layer(b));
    for (const a of sorted) {
      if (!a.img) continue;
      const d = a.d, t = Math.max(0, combo.clock - a.start);
      const n = d.frames;
      let f = Math.floor(t * (a.fps || d.fps));
      f = a.loop ? f % n : Math.min(n - 1, f);
      if (a.screen) {
        ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0);
        const [sx0, sy0, w, h] = frameRect(d, f);
        ctx.drawImage(a.img, sx0, sy0, w, h, 0, 0, cv.width, cv.height);
        ctx.restore();
        continue;
      }
      if (a.beam) {
        ctx.save();
        ctx.translate(Math.round(a.x), Math.round(a.y));
        ctx.rotate(a.beam.ang);
        ctx.scale(a.beam.sx, 1);
        const [sx0, sy0, w, h] = frameRect(d, f);
        ctx.drawImage(a.img, sx0, sy0, w, h, -d.anchor[0], -d.anchor[1], w, h);
        ctx.restore();
        continue;
      }
      if (a.path) {
        const u = Math.min(1, t / a.path.dur);
        const x = a.path.sx + (a.path.tx - a.path.sx) * u, y = a.path.sy + (a.path.ty - a.path.sy) * u;
        drawFrame(ctx, d, a.img, f, x - d.anchor[0], y - d.anchor[1]);
        continue;
      }
      drawFrame(ctx, d, a.img, f, a.x, a.y, a.flip);
    }
    // damage number: pops up with an overshoot, holds, drifts
    if (combo.dmg) {
      const t = combo.clock - combo.dmg.t;
      if (t < 1.4) {
        const pop = t < 0.12 ? t / 0.12 * 10 : t < 0.2 ? 10 - (t - 0.12) / 0.08 * 4 : 6 + (t - 0.2) * 4;
        ctx.font = (combo.dmg.crit ? "700 12px" : "700 10px") + " Silkscreen, monospace";
        ctx.textAlign = "center";
        const y = Math.round(combo.dmg.y - pop), x = combo.dmg.x;
        ctx.fillStyle = "#14121a";
        for (const [dx, dy] of [[-1, 0], [1, 0], [0, -1], [0, 1], [1, 1]]) ctx.fillText("-" + combo.dmg.v, x + dx, y + dy);
        ctx.fillStyle = combo.dmg.crit ? "#ffd040" : "#ffffff";
        ctx.fillText("-" + combo.dmg.v, x, y);
      }
    }
    if (combo.flash > 0) {
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.fillStyle = "rgba(255,255,255,0.55)";
      ctx.fillRect(0, 0, cv.width, cv.height);
      combo.flash -= 1;
    }
    if (!combo.running && !combo.actors.length) {
      // idle stage
      combo.actors = [];
      addActor("unit-idle", CASTER[0] - 32, CASTER[1] - 56);
      addActor("unit-idle", TARGET[0] - 32, TARGET[1] - 56, { flip: true });
    }
    if (!combo.running) combo.clock += dt;
  }
  let backdropFull = null;
  function wireCombo() {
    const atk = FX.filter((d) => d.kind === "projectile" || d.kind === "beam");
    const imp = FX.filter((d) => d.kind === "impact");
    const st = FX.filter((d) => ["status", "debuff", "buff"].includes(d.kind) || (d.kind === "aura" && d.loop));
    fillSelect("#c-attack", atk, "fire-fireball");
    fillSelect("#c-impact", imp, "fire-burst");
    fillSelect("#c-status", st, "status-burn", true);
    $("#c-play").addEventListener("click", playCombo);
    $("#c-crit").addEventListener("click", (e) => { combo.crit = !combo.crit; setPressed(e.target, combo.crit); });
    $("#c-slow").addEventListener("click", (e) => { combo.slow = !combo.slow; setPressed(e.target, combo.slow); });
    // keep impact element in step with the attack element, unless the user picked one
    $("#c-attack").addEventListener("change", (e) => {
      const d = BYID[e.target.value];
      const m = imp.find((x) => x.element === d.element);
      if (m) $("#c-impact").value = m.id;
    });
  }

  // ------------------------------------------------------------------ logo
  function drawLogo() {
    const c = $("#logo").getContext("2d");
    const px = (x, y, col) => { c.fillStyle = col; c.fillRect(x, y, 1, 1); };
    const rows = ["......XX........", ".....XooX.......", "....XooooX..X...", "...XooYYooX.XX..", "..XooYWWYooXoX..",
      ".XooYWWWWYooX...", "XooYWWWWWWYooX..", ".XooYWWWWYooX...", "..XooYWWYooX....", "...XooYYooX.....",
      "....XooooX......", ".....XooX..X....", "......XX..XoX...", "..........XooX..", "...........XX...", "................"];
    const map = { X: "#4a1310", o: "#e8571c", Y: "#ffd65c", W: "#fff6c9" };
    rows.forEach((r, y) => [...r].forEach((ch, x) => { if (map[ch]) px(x, y, map[ch]); }));
  }

  // ------------------------------------------------------------------ main loop
  let last = performance.now();
  function frame(now) {
    const dt = Math.min(0.1, (now - last) / 1000);
    last = now;
    if (detail) {
      detail.player.tick(dt);
      if (!detail.player.playing && detail.player.forced === null) { /* paused */ }
      else if (detail.player.playing) markStrip(detail.player.frame);
    } else {
      for (const c of cards) if (c.visible && !c.fig.hidden) c.player.tick(dt);
    }
    comboTick(dt);
    requestAnimationFrame(frame);
  }

  async function main() {
    drawLogo();
    const data = await (await fetch("fx.json")).json();
    FX = data.effects;
    for (const d of FX) BYID[d.id] = d;
    $("#total").textContent = FX.length;
    try {
      backdropFull = await loadImg("img/backdrop.png");
      // a 64x64 tile cut from the arena for cards
      const t = el("canvas", { width: 64, height: 64 });
      t.getContext("2d").drawImage(backdropFull, -128, -8);
      backdrop = t;
      dummy = await loadImg("img/dummy.png");
      dummyFlip = mirrorImage(dummy);
    } catch (e) { console.warn(e.message); }
    buildChips();
    readHash();
    syncChips();
    buildGrid();
    filter();
    wireDetail();
    wireCombo();
    $("#q").addEventListener("input", (e) => { state.q = e.target.value; filter(); });
    requestAnimationFrame(frame);
    setTimeout(playCombo, 600);
  }
  main().catch((e) => {
    document.body.prepend(el("p", { className: "wrap empty", textContent: "fx.json not loaded: " + e.message + " (serve the folder over http)" }));
  });
})();
