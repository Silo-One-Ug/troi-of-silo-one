// board-app.js — the board (Silo One): a warm white, full-width page of tiles. The agent fills it through /cmd (cards,
// pictures, notes from the vault, UI panels drawn by board-render.js, layouts); the owner moves tiles with the mouse:
// drag a title bar (a picture anywhere), scroll inside a panel, click × to put a tile away, double-click a title to
// spotlight it, Esc to end the spotlight, drag the corner grip to resize. New items flow into free space in reading order;
// `tidy` re-flows everything. What is up is reported on the /state heartbeat and saved by board-server.py, and comes back
// on load. An empty board says what it is for, with prompts that go to the agent when clicked. Opened on its own, the page
// hands over to the console's Hands view, so the console's bar is the one navigation everywhere (?bare=1 keeps it bare).
// On a phone (under 768 px) the same tiles flow as one column in reading order, full width, nothing to drag; a tap on a
// title spotlights a tile. The model keeps the glass's positions throughout, so the desktop finds everything where it was.
(function () {
  const R = () => window.__boardRender;
  const $ = s => document.querySelector(s);
  const num = (v, d) => { const n = Number(v); return Number.isFinite(n) ? n : d; };
  const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
  const str = v => v == null ? "" : String(v);
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = String(text); return e; };
  const W = () => innerWidth, H = () => innerHeight;
  const MARGIN = 24, GAP = 18, TOP = 24, BOTTOM = 24;
  // a phone: one column in reading order (the model's y, then x), laid out by the page; the model keeps the glass's geometry
  const NARROW_MQ = matchMedia("(max-width: 767px)"), narrow = () => NARROW_MQ.matches;
  const rank = t => Math.round(clamp(num(t.y, 0.45), 0, 12) * 8) * 1000 + Math.round(clamp(num(t.x, 0.5), 0, 1) * 100);
  const orderTile = t => { t.el.style.order = String(rank(t)); };
  const reorder = () => tiles.forEach(orderTile);
  const stage = $("#stage"), emptyEl = $("#empty"), toastEl = $("#toast");
  // the theme: the console's word (a message, or ?theme= in the address), remembered so the next load paints right from
  // its first frame; without a word, the system's
  const applyTheme = t => {
    if (t === "dark" || t === "light") { document.documentElement.dataset.theme = t; try { localStorage.setItem("board.theme", t); } catch (e) {} }
    else { delete document.documentElement.dataset.theme; try { localStorage.removeItem("board.theme"); } catch (e) {} }
  };
  { const q = new URLSearchParams(location.search).get("theme"); if (q === "dark" || q === "light" || q === "system") applyTheme(q); }
  addEventListener("message", e => { const m = e.data || {}; if (m.theme === "dark" || m.theme === "light" || m.theme === "system") applyTheme(m.theme); });
  let tiles = [], UID = 1, presented = null, CFG = { name: "Assistant" }, seq = 1;
  const isModel = s => /\.(glb|gltf)(\?|$)/i.test(str(s));
  const isVideo = s => /\.(webm|mp4|mov|m4v)(\?|$)/i.test(str(s));
  const newUid = () => "u" + Date.now().toString(36) + (seq++).toString(36);

  function toast(msg, ms = 2200) { toastEl.textContent = msg; toastEl.classList.add("on"); clearTimeout(toastEl._h); toastEl._h = setTimeout(() => toastEl.classList.remove("on"), ms); }

  // ---- geometry: a tile's centre and width are fractions of the window, so a resize keeps the picture
  function layoutTile(t, live) {
    const e = t.el;
    if (narrow()) {                           // the column lays it out: no inline geometry, just its place in the order
      e.style.left = e.style.top = e.style.width = e.style.height = "";
      const m = t.type === "img" ? e.querySelector("img, video") : null; if (m) { m.style.maxWidth = ""; m.style.maxHeight = ""; }
      orderTile(t); fitStage(); return;
    }
    if (t.type === "img") {
      const m = e.querySelector("img, video");
      if (m) { m.style.maxWidth = t.w != null ? Math.round(clamp(t.w, 0.08, 1) * W() - 12) + "px" : ""; m.style.maxHeight = t.h != null ? Math.round(clamp(t.h, 0.1, 0.95) * H()) + "px" : ""; }
    } else {
      e.style.width = t.w != null ? Math.round(clamp(t.w, 0.1, 1) * W() - (t.w >= 0.97 ? 2 * MARGIN : 0)) + "px" : "";
      if (t.type === "ui" && t.aspect) { const ar = ratioOf(t.aspect); e.style.height = ar ? Math.round(e.offsetWidth / ar) + "px" : ""; }
      else e.style.height = t.h != null ? Math.round(clamp(t.h, 0.1, 0.95) * H()) + "px" : "";
    }
    const p = posOf(t);
    if (live) e.classList.add("dragging");
    e.style.left = Math.round(p.left) + "px"; e.style.top = Math.round(p.top) + "px";
    fitStage();
  }
  function posOf(t) {                       // where the model puts a tile, clamped so it stays reachable (on a phone: where the column put it)
    const w = t.el.offsetWidth, h = t.el.offsetHeight;
    if (narrow()) return { left: t.el.offsetLeft, top: t.el.offsetTop, w, h };
    return { left: clamp(t.x * W() - w / 2, -w + 90, W() - 90), top: Math.max(0, t.y * H() - h / 2), w, h };
  }
  function fitStage() {                     // the page is as tall as its lowest tile: the board scrolls, nothing is lost below the fold
    if (narrow()) { stage.style.height = ""; return; }
    const b = Math.max(0, ...tiles.filter(o => o.el.isConnected && !o.pending).map(o => rectOf(o).b));
    stage.style.height = Math.max(H(), b + 48) + "px";
  }
  function reveal(t) {                      // a new tile below the fold comes into view
    const p = posOf(t), top = window.scrollY, bottom = top + H();
    if (p.top + p.h > bottom || p.top < top) t.el.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
  const ratioOf = a => { if (a == null || a === "") return 0; if (typeof a === "number") return a > 0 ? a : 0; const m = String(a).match(/^\s*(\d+(?:\.\d+)?)\s*[:/xX]\s*(\d+(?:\.\d+)?)\s*$/); return m && +m[2] > 0 ? +m[1] / +m[2] : 0; };
  const rectOf = o => { const p = posOf(o); return { l: p.left, t: p.top, r: p.left + p.w, b: p.top + p.h }; };
  function setLT(t, left, top) { const w = t.el.offsetWidth, h = t.el.offsetHeight; t.x = (left + w / 2) / W(); t.y = (top + h / 2) / H(); layoutTile(t); }
  let zTop = 1;
  function bringFront(t) { if (+t.el.style.zIndex !== zTop) t.el.style.zIndex = String(++zTop); }

  // the first free spot in reading order; below everything when nothing fits (Tidy sorts it out)
  function autoPlace(t) {
    if (narrow()) {                          // under everything, in the model too, so the glass finds it there later
      const others = tiles.filter(o => o !== t && o.el.isConnected && !o.el.classList.contains("leave"));
      t.x = 0.5; t.y = others.length ? Math.min(12, Math.max(...others.map(o => num(o.y, 0.45))) + 0.35) : 0.45; layoutTile(t); return true;
    }
    const w = t.el.offsetWidth, h = t.el.offsetHeight;
    if (!w || !h) return false;
    const others = tiles.filter(o => o !== t && o.el.isConnected && !o.el.classList.contains("leave") && !o.pending).map(rectOf);
    const right = W() - MARGIN, step = 24;
    for (let y = TOP; y < TOP + 12 * H(); y += step)
      for (let x = MARGIN; x + w <= right + 1; x += step)
        if (!others.some(o => o.l < x + w + GAP && o.r > x - GAP && o.t < y + h + GAP && o.b > y - GAP)) { setLT(t, x, y); return true; }
    const low = others.length ? Math.max(...others.map(o => o.b)) + GAP : TOP;
    setLT(t, MARGIN, low); return false;
  }

  function placeFree(t, left, top) {
    if (narrow()) { layoutTile(t); return; }
    const w = t.el.offsetWidth, h = t.el.offsetHeight; if (!w || !h) return;
    const others = tiles.filter(o => o !== t && o.el.isConnected && !o.el.classList.contains("leave") && !o.pending && o !== presented).map(rectOf);
    const free = (x, y) => x >= MARGIN - 1 && x + w <= W() - MARGIN + 1 && y >= TOP - 1 && !others.some(o => o.l < x + w + GAP && o.r > x - GAP && o.t < y + h + GAP && o.b > y - GAP);
    left = clamp(left, MARGIN, Math.max(MARGIN, W() - MARGIN - w)); top = Math.max(TOP, top);
    if (free(left, top)) { setLT(t, left, top); return; }
    const step = 24;
    for (let r = step; r <= 1200; r += step) {                      // rings outward from the wish, nearest first
      const cands = [];
      for (let dx = -r; dx <= r; dx += step) cands.push([left + dx, top - r], [left + dx, top + r]);
      for (let dy = -r + step; dy <= r - step; dy += step) cands.push([left - r, top + dy], [left + r, top + dy]);
      cands.sort((a, b) => Math.hypot(a[0] - left, a[1] - top) - Math.hypot(b[0] - left, b[1] - top));
      for (const [x, y] of cands) if (free(x, y)) { setLT(t, x, y); return; }
    }
    autoPlace(t);
  }
  function settle() {                          // after a restore or a restyle: reading order, each tile kept off the ones before it
    if (narrow()) { reorder(); dirty(); return; }
    const list = tiles.filter(o => o.el.isConnected && !o.pending).map(o => ({ o, r: rectOf(o) })).sort((a, b) => (a.r.t - b.r.t) || (a.r.l - b.r.l)).map(x => x.o);
    const done = new Set();
    for (const o of list) { const p = posOf(o); const keep = tiles; tiles = list.filter(x => done.has(x) || x === o); placeFree(o, p.left, p.top); tiles = keep; done.add(o); }
    dirty();
  }
  function tidy(quiet) {
    if (narrow()) { if (!quiet) toast("one column on a phone: nothing to tidy"); return; }
    const list = tiles.filter(o => o.el.isConnected && o !== presented).map(o => ({ o, r: rectOf(o) })).sort((a, b) => (a.r.t - b.r.t) || (a.r.l - b.r.l)).map(x => x.o);
    let x = MARGIN, y = TOP, rowH = 0; const right = W() - MARGIN;
    for (const o of list) {
      const w = o.el.offsetWidth, h = o.el.offsetHeight;
      if (x > MARGIN && x + w > right) { x = MARGIN; y += rowH + GAP; rowH = 0; }
      setLT(o, x, y); x += w + GAP; rowH = Math.max(rowH, h);
    }
    dirty(); if (!quiet && list.length) toast("tidied");
  }

  // ---- tiles
  function buildEl(t) {
    const e = el("div", "tile tile-" + (t.type === "panel" ? "note" : t.type)); e.dataset.id = t.id;
    const bar = (title) => { const b = el("div", "tilebar" + (t.hidebar ? " hidden" : "")); b.appendChild(el("h3", null, title)); const x = el("span", "tileclose", "×"); x.title = "put it away"; b.appendChild(x); return b; };
    if (t.type === "img") {
      const m = isVideo(t.src) ? el("video") : el("img");
      m.src = t.src; if (m.tagName === "VIDEO") { m.autoplay = true; m.loop = true; m.muted = true; m.playsInline = true; m.controls = true; } else { m.alt = t.title || ""; m.draggable = false; }
      m.addEventListener(m.tagName === "VIDEO" ? "loadedmetadata" : "load", () => { if (t.pending) { t.pending = false; e.style.visibility = ""; autoPlace(t); reveal(t); dirty(); } else layoutTile(t); });
      e.appendChild(m); if (t.title) e.appendChild(el("div", "tilecap", t.title));
      const x = el("span", "tileclose float", "×"); x.title = "put it away"; e.appendChild(x);
    } else if (t.type === "card") {
      e.appendChild(bar(t.title)); const b = el("div", "tilebody"); b.appendChild(el("p", null, t.body || "")); e.appendChild(b);
      if (t.file) e.classList.add("note");
    } else if (t.type === "panel") {
      e.appendChild(bar(t.title)); const b = el("div", "tilebody"); b.textContent = "…"; e.appendChild(b); t.body = b;
      fetch("/note?f=" + encodeURIComponent(t.file)).then(r => r.ok ? r.text() : "(the note could not be read)").then(txt => { b.replaceChildren(R().markdown(txt)); if (t.sy) b.scrollTop = t.sy * (b.scrollHeight - b.clientHeight); }).catch(() => { b.textContent = "(the note could not be read)"; });
    } else if (t.type === "ui") {
      e.appendChild(bar(t.title)); const b = el("div", "tilebody"); e.appendChild(b); t.body = b;
      t.state = t.state && typeof t.state === "object" ? t.state : {};
      const cx = { state: t.state, live: true, onState: st => { t.state = st; dirty(); }, onEvent: ev => sendEvent(t, ev) };
      t.root = R().render(t.spec, cx) || el("div"); b.appendChild(t.root); t.cx = cx;
      if (t.aspect || t.h != null) e.classList.add("fixed");
    } else if (t.type === "model") {
      e.appendChild(bar(t.title || "3D model")); const b = el("div", "tilebody"); b.appendChild(el("p", "uimuted", (t.src || "").split("/").pop() + " · 3D models are not shown on this board")); e.appendChild(b);
    }
    if (t.type !== "card" && t.type !== "model") { const g = el("span", "tilegrip"); g.title = "resize"; e.appendChild(g); }
    return e;
  }

  function addTile(t, opts) {
    opts = opts || {};
    t.id = UID++; t.el = buildEl(t); stage.appendChild(t.el); tiles.push(t);
    const placed = typeof t.x === "number" && typeof t.y === "number";
    if (!placed) { t.x = 0.5; t.y = 0.45; }
    if (t.type === "img" && !placed && !narrow()) { t.pending = true; t.el.style.visibility = "hidden"; layoutTile(t); }
    else { layoutTile(t); if (opts.wish) placeFree(t, opts.wish[0], opts.wish[1]); else if (!placed) autoPlace(t); reveal(t); }
    t.el.classList.add("arrive"); setTimeout(() => t.el.classList.remove("arrive"), 500);
    if (opts.hand) pulse(t);
    if (opts.present) requestAnimationFrame(() => present(t));
    dirty(); return t;
  }
  function remove(t) { if (presented === t) unpresent(); t.el.classList.add("leave"); setTimeout(() => t.el.remove(), 260); tiles = tiles.filter(o => o !== t); dirty(); }
  function pulse(t) { t.el.classList.remove("pulse"); void t.el.offsetWidth; t.el.classList.add("pulse"); setTimeout(() => t.el.classList.remove("pulse"), 1700); }
  function yank(t) { t.el.classList.add("shake"); setTimeout(() => remove(t), 380); }
  function findTile(title, types) {
    const list = tiles.filter(o => o.el.isConnected && (!types || types.includes(o.type)));
    if (title) {
      const q = str(title).toLowerCase();
      return list.find(o => str(o.title).toLowerCase() === q) || list.find(o => str(o.title).toLowerCase().includes(q) || str(o.src).toLowerCase().includes(q) || str(o.file).toLowerCase().includes(q)) || null;
    }
    return list[list.length - 1] || null;
  }

  // ---- the spotlight
  function present(t) {
    if (!t || !t.el.isConnected) return;
    if (presented === t) return;
    if (presented) unpresent(true);
    if (narrow()) {                              // on a phone: the tile comes into view whole and the others fade; no geometry changes
      presented = t; t.prev = null; document.body.classList.add("presenting");
      tiles.forEach(o => o.el.classList.toggle("dimmed", o !== t)); t.el.classList.add("presented");
      requestAnimationFrame(() => t.el.scrollIntoView({ behavior: "smooth", block: "start" })); dirty(); return;
    }
    presented = t; t.prev = { x: t.x, y: t.y, w: t.w, h: t.h, fixed: t.el.classList.contains("fixed") };
    document.body.classList.add("presenting"); document.documentElement.style.overflow = "hidden";   // the page holds still; the tile's body scrolls
    tiles.forEach(o => o.el.classList.toggle("dimmed", o !== t)); t.el.classList.add("presented"); bringFront(t);
    const natural = t.el.offsetWidth / W();
    t.w = t.type === "img" ? clamp(natural * 1.8, 0.4, 0.9) : t.type === "card" ? clamp(natural * 1.3, 0.3, 0.6) : clamp(Math.max(natural * 1.5, 0.5), 0.3, 0.92);
    if (t.type !== "img") { t.h = undefined; t.el.classList.remove("fixed"); }   // as much of it as fits
    t.el.classList.add("dragging");              // sized first, without the glide, so the height measured is the true one
    layoutTile(t);
    recenter(t, true);
    t.el.classList.remove("dragging"); void t.el.offsetWidth;
    layoutTile(t); dirty();                       // then the glide, to the centre of the screen
  }
  function recenter(t, sizing) {
    const room = H() - 24;
    let h = t.el.offsetHeight;
    if (sizing && h > room && t.type !== "img" && t.type !== "card") { t.h = room / H(); t.el.classList.add("fixed"); layoutTile(t); h = t.el.offsetHeight; }
    t.x = 0.5; t.y = (window.scrollY + Math.max(12, (H() - h) / 2) + h / 2) / H();
  }
  function unpresent(keepVeil) {
    if (!presented) return;
    const t = presented; presented = null;
    if (!keepVeil) { document.body.classList.remove("presenting"); document.documentElement.style.overflow = ""; }
    tiles.forEach(o => o.el.classList.remove("dimmed")); t.el.classList.remove("presented");
    if (t.prev) { t.x = t.prev.x; t.y = t.prev.y; t.w = t.prev.w; t.h = t.prev.h; if (!t.prev.fixed) t.el.classList.remove("fixed"); t.prev = null; }
    layoutTile(t); dirty();
  }

  // ---- the mouse: drag, resize, close, spotlight, click through to the parts
  function tileOf(node) { const e = node && node.closest && node.closest(".tile"); return e ? tiles.find(t => t.el === e) : null; }
  stage.addEventListener("mousedown", e => {
    if (e.button !== 0) return;
    const t = tileOf(e.target); if (!t) return;
    if (narrow()) return;                        // nothing to drag or resize in the column
    bringFront(t);
    if (e.target.closest(".tileclose")) return;
    if (e.target.closest(".tilegrip")) { startResize(t, e); return; }
    const onBar = !!e.target.closest(".tilebar");
    const media = e.target.closest("video, audio, iframe, [data-act], a, input, select, textarea");
    if (onBar || (t.type === "img" && !media)) startDrag(t, e);
  });
  function startDrag(t, e) {
    e.preventDefault();
    const r = t.el.getBoundingClientRect(), dx = e.clientX - r.left, dy = e.clientY - r.top; let moved = false;
    const move = ev => { moved = true; const left = ev.clientX - dx, top = ev.clientY - dy + window.scrollY; t.x = (left + r.width / 2) / W(); t.y = (top + r.height / 2) / H(); layoutTile(t, true); };
    const up = () => { removeEventListener("mousemove", move); removeEventListener("mouseup", up); t.el.classList.remove("dragging"); if (moved) { if (presented === t) { presented = null; document.body.classList.remove("presenting"); document.documentElement.style.overflow = ""; tiles.forEach(o => o.el.classList.remove("dimmed")); t.el.classList.remove("presented"); t.prev = null; } const p = posOf(t); placeFree(t, p.left, p.top); dirty(); } };
    addEventListener("mousemove", move); addEventListener("mouseup", up);
  }
  function startResize(t, e) {
    e.preventDefault(); const rr = t.el.getBoundingClientRect(), r = { left: rr.left, top: rr.top + window.scrollY, width: rr.width, height: rr.height }; t.el.classList.add("resizing");
    const fixedH = t.type === "panel" || (t.type === "ui" && (t.h != null || t.aspect));
    const move = ev => {
      const w = clamp(ev.clientX - r.left, 160, W() - r.left - 8); t.w = w / W(); const py = ev.clientY + window.scrollY;
      if (t.type === "img") { t.h = clamp(py - r.top, 80, H() * 0.95) / H(); }
      else if (fixedH) { t.h = clamp(py - r.top, 120, H() * 0.95) / H(); t.aspect = null; if (t.type === "ui") t.el.classList.add("fixed"); }
      t.x = (r.left + w / 2) / W(); const h = t.el.offsetHeight; t.y = (r.top + h / 2) / H(); layoutTile(t, true);
    };
    const up = () => { removeEventListener("mousemove", move); removeEventListener("mouseup", up); t.el.classList.remove("dragging", "resizing"); const h = t.el.offsetHeight; t.y = (r.top + h / 2) / H(); layoutTile(t); dirty(); };
    addEventListener("mousemove", move); addEventListener("mouseup", up);
  }
  stage.addEventListener("click", e => {
    const t = tileOf(e.target);
    if (!t) { if (presented && e.target === stage) unpresent(); return; }
    if (narrow() && presented && t !== presented) { unpresent(); return; }                  // a tap on a faded tile ends the spotlight
    if (e.target.closest(".tileclose")) { remove(t); return; }
    if (narrow() && e.target.closest(".tilebar")) { if (presented === t) unpresent(); else present(t); return; }   // a tap on a title: the spotlight
    if (t.type === "card" && t.file && e.target.closest(".tilebody")) { openNote(t.file, t.title, t); return; }
    const cb = e.target.closest("li.uicheck[data-line]");
    if (cb && t.type === "panel" && t.file) {
      const done = !cb.classList.contains("done"); cb.classList.toggle("done", done); cb.classList.toggle("todo", !done);
      fetch("/note", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ f: t.file, line: +cb.dataset.line, done }) })
        .then(r => r.ok ? r.json() : r.json().then(j => Promise.reject(j.error || r.status)))
        .then(() => toast(done ? "ticked, in the note too" : "unticked, in the note too", 1400))
        .catch(err => { cb.classList.toggle("done", !done); cb.classList.toggle("todo", done); toast("the note kept its mark: " + err, 2600); });
      return;
    }
    const a = e.target.closest("[data-act]");
    if (a && t.root && t.root.contains(a)) {
      const res = R().act(t.root, t.state, a.dataset.act);
      if (res.changed) dirty();
      if (res.event) sendEvent(t, res.event);
      a.classList.remove("tapped"); void a.offsetWidth; a.classList.add("tapped"); setTimeout(() => a.classList.remove("tapped"), 500);
    }
  });
  stage.addEventListener("dblclick", e => {
    const t = tileOf(e.target); if (!t) return;
    if (e.target.closest(".tilebar") || (t.type === "img" && !e.target.closest("video"))) { if (presented === t) unpresent(); else present(t); }
  });
  addEventListener("keydown", e => { if (e.key === "Escape" && presented) unpresent(); });
  addEventListener("resize", () => { if (narrow()) return; tiles.forEach(t => layoutTile(t)); if (presented) { recenter(presented); layoutTile(presented); } });
  NARROW_MQ.addEventListener("change", () => {  // across the breakpoint (a window resized, a phone turned): the other layout, from the same model
    if (presented) unpresent(); tiles.forEach(t => layoutTile(t)); if (!narrow()) settle(); buildEmpty(); dirty();
  });
  $("#tidy").addEventListener("click", () => tidy());
  const clearBtn = $("#clear");
  clearBtn.addEventListener("click", () => {
    if (!clearBtn.classList.contains("arm")) { clearBtn.classList.add("arm"); clearBtn.textContent = "Clear all?"; clearTimeout(clearBtn._h); clearBtn._h = setTimeout(() => { clearBtn.classList.remove("arm"); clearBtn.textContent = "Clear"; }, 3000); return; }
    clearBtn.classList.remove("arm"); clearBtn.textContent = "Clear"; clearAll(); toast("the board is clear");
  });
  function clearAll() { tiles.slice().forEach(remove); }

  // ---- notes from the vault
  function openNote(file, title, near) {
    const open = tiles.find(o => o.type === "panel" && o.file === file);
    if (open) { bringFront(open); pulse(open); return open; }
    const name = str(title || file.split("/").pop().replace(/\.md$/, ""));
    const t = { type: "panel", title: name, file, w: 0.36, h: 0.62 };
    if (near && narrow()) { t.x = num(near.x, 0.5); t.y = num(near.y, 0.45) + 0.001; return addTile(t); }   // right after its card in the column
    if (near) { const p = posOf(near); t.x = 0.5; t.y = 0.45; const made = addTile(t, { quiet: true, wish: [p.left + p.w + GAP, p.top] }); return made; }
    return addTile(t);
  }

  // ---- UI panels
  function addUI(c) {
    if (!c.spec || typeof c.spec !== "object") return null;
    const t = { type: "ui", title: str(c.title || "PANEL"), spec: c.spec, uid: str(c.uid) || newUid(), uv: num(c.uv, 1), state: c.state, w: clamp(num(c.w, 0.3), 0.1, 1), h: c.scroll ? clamp(num(c.h, 0.62), 0.2, 0.95) : (typeof c.h === "number" ? clamp(c.h, 0.1, 0.95) : undefined), aspect: c.aspect || undefined, hidebar: c.hidebar ? 1 : undefined, x: c.x, y: c.y };
    return addTile(t, { hand: c.hand, present: c.present });
  }
  function uiOp(c) {
    const t = c.uid ? tiles.find(o => o.type === "ui" && o.uid === c.uid) : findTile(c.title, ["ui"]);
    if (!t) { toast("no such panel on the board"); return; }
    const r = R();
    if (c.spec && typeof c.spec === "object") {
      t.spec = c.spec; t.uv = num(c.uv, t.uv + 1);
      const fresh = r.render(c.spec, t.cx) || el("div"); t.root.replaceWith(fresh); t.root = fresh; t.body.scrollTop = 0;
      layoutTile(t); const p = posOf(t); placeFree(t, p.left, p.top);
    }
    if (c.state && typeof c.state === "object") { Object.assign(t.state, c.state); r.applyState(t.root, t.state); }
    if (c.name != null) { t.title = str(c.name); const h = t.el.querySelector(".tilebar h3"); if (h) h.textContent = t.title; }
    const op = str(c.op);
    if (op === "next" || op === "prev" || op === "goto") r.step(t.root, t.state, op, c.i != null ? c.i : c.n, c.id);
    else if (["play", "pause", "toggle", "mute", "unmute", "seek"].includes(op)) r.media(t.root, op, c.t != null ? c.t : c.i, c.id);
    else if (op === "scroll") scrollBody(t, c.dir);
    else if (op === "close") remove(t);
    else if (op === "hover") pulse(t);
    else if (op === "present") present(t);
    else if (op === "unpresent") unpresent();
    if (typeof c.w === "number") t.w = clamp(c.w, 0.1, 1);
    if (typeof c.h === "number") { t.h = clamp(c.h, 0.1, 0.95); t.el.classList.add("fixed"); }
    if (typeof c.x === "number") t.x = clamp(c.x, 0.04, 0.96);
    if (typeof c.y === "number") t.y = clamp(c.y, 0.04, 12);
    layoutTile(t); bringFront(t); dirty();
  }
  function scrollBody(t, dir) {
    const b = t.body; if (!b) return; const page = b.clientHeight * 0.8; dir = str(dir || "down");
    b.scrollTo({ top: dir === "top" ? 0 : dir === "bottom" ? b.scrollHeight : b.scrollTop + (dir === "up" ? -page : page), behavior: "smooth" }); dirty();
  }

  // ---- several pieces at once, in the cells of a grid (or a row, a column), a caption under them
  function layout(c) {
    const items = Array.isArray(c.items) ? c.items.slice(0, 24) : []; if (!items.length) return;
    if (c.clear) clearAll();
    const n = items.length, kind = str(c.kind || "grid");
    const cols = kind === "row" ? n : kind === "column" ? 1 : clamp(Math.round(num(c.cols, n <= 1 ? 1 : n <= 4 ? 2 : n <= 9 ? 3 : 4)), 1, 6);
    const rows = Math.ceil(n / cols);
    const Wf = clamp(num(c.w, 0.94), 0.2, 0.98), Hf = clamp(num(c.h, c.caption ? 0.7 : 0.82), 0.2, 0.95);
    const cx0 = clamp(num(c.x, 0.5), 0.1, 0.9), cy0 = clamp(num(c.y, c.caption ? 0.43 : 0.48), 0.1, 0.9), gap = clamp(num(c.gap, 0.015), 0, 0.1);
    const cw = (Wf - gap * (cols - 1)) / cols, ch = (Hf - gap * (rows - 1)) / rows;
    items.forEach((item, i) => {
      if (!item || typeof item !== "object") return;
      const r = Math.floor(i / cols), col = i % cols, inRow = r === rows - 1 ? n - r * cols : cols;
      const x = cx0 - Wf / 2 + cw / 2 + col * (cw + gap) + (inRow < cols ? (cols - inRow) * (cw + gap) / 2 : 0);
      const y = cy0 - Hf / 2 + ch / 2 + r * (ch + gap);
      const d = { ...item, x: +x.toFixed(4), y: +y.toFixed(4) };
      if (d.a === "add_ui") { if (typeof d.w !== "number") d.w = +cw.toFixed(4); if (!d.aspect && !d.scroll && typeof d.h !== "number") d.h = +ch.toFixed(4); addUI(d); }
      else if (d.a === "add_img" && d.src) addTile({ type: isModel(d.src) ? "model" : "img", title: str(d.title), src: d.src, x: d.x, y: d.y, w: typeof d.w === "number" ? d.w : +cw.toFixed(4), h: typeof d.h === "number" ? d.h : +ch.toFixed(4) });
      else if (d.a === "add_card" && d.title) addTile({ type: "card", title: d.title, body: d.body || "", file: d.file || "", x: d.x, y: d.y, w: Math.min(cw, 480 / W()) });
    });
    if (c.caption) addTile({ type: "card", title: str(c.title || c.caption).slice(0, 60), body: c.title ? str(c.caption) : "", x: cx0, y: clamp(cy0 + Hf / 2 + 0.07, 0.1, 0.95) });
  }

  // ---- the commands (bin/board.sh, show.py, pictures.py, show-image.sh, the console)
  function applyCmds(cmds) {
    (cmds || []).forEach(c => {
      if (!c || typeof c !== "object") return;
      switch (c.a) {
        case "clear": case "reset": clearAll(); break;
        case "add_card": if (c.title) { const t = addTile({ type: "card", title: c.title, body: c.body || "", file: c.file || "", x: c.x, y: c.y }, { hand: c.hand }); if (c.open && t.file) openNote(t.file, t.title, t); } break;
        case "add_img": case "hand": case "give": if (c.src) addTile({ type: isModel(c.src) ? "model" : "img", title: str(c.title), src: c.src, x: c.x, y: c.y, w: typeof c.w === "number" ? c.w : undefined, h: typeof c.h === "number" ? c.h : undefined }, { hand: c.a !== "add_img" }); break;
        case "present": {
          if (c.unfocus) { unpresent(); break; }
          let t = c.title ? findTile(c.title) : null;
          if (!t && c.src) t = addTile({ type: isModel(c.src) ? "model" : "img", title: str(c.title), src: c.src });
          else if (!t && c.title) t = addTile({ type: "card", title: c.title, body: c.body || "", file: c.file || "" });
          if (t && c.open && t.file) t = openNote(t.file, t.title, t) || t;
          if (t) requestAnimationFrame(() => present(t));
          break;
        }
        case "yank": { const t = findTile(c.title); if (t) yank(t); break; }
        case "hover": { const t = findTile(c.title); if (t) { bringFront(t); pulse(t); } break; }
        case "scroll_note": { const t = tiles.filter(o => o.body && o.el.isConnected).pop(); if (t) scrollBody(t, c.dir); break; }
        case "add_ui": addUI(c); break;
        case "ui": uiOp(c); break;
        case "layout": layout(c); break;
        case "tidy": tidy(); break;
        default: break;                            // widget, explode, assemble: the ring and the holograms are gone
      }
    });
  }

  // ---- what is up, reported every 300 ms (the reply carries the queued commands); the server saves it
  function snapshotOf(t) {
    const b = t.body, sy = b && b.scrollHeight > b.clientHeight ? +(b.scrollTop / (b.scrollHeight - b.clientHeight)).toFixed(3) : undefined;
    const us = t.type === "ui" && t.state && Object.keys(t.state).length ? t.state : undefined;
    return { id: t.id, type: t.type, title: t.title, body: t.type === "card" ? t.body : undefined, src: t.src, file: t.file, x: +t.x.toFixed(4), y: +t.y.toFixed(4), scale: 1,
      tw: t.w != null ? +t.w.toFixed(4) : undefined, th: t.h != null ? +t.h.toFixed(4) : undefined, ui: t.type === "ui" ? 1 : undefined, uid: t.uid, uv: t.uv, us, ua: t.aspect || undefined, ub: t.hidebar,
      sy, pres: presented === t ? 1 : undefined, g: 0, op: 1 };
  }
  let dirtyFlag = true;
  function dirty() { dirtyFlag = true; emptyEl.hidden = tiles.some(t => t.el.isConnected && !t.el.classList.contains("leave")); fitStage(); }
  async function beat() {
    const items = tiles.filter(t => t.el.isConnected && !t.el.classList.contains("leave")).map(snapshotOf);
    try {
      const r = await fetch("/state", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ cursors: [], items }) });
      if (r.ok) { const cmds = await r.json(); if (Array.isArray(cmds) && cmds.length) applyCmds(cmds); }
    } catch (e) {}
  }
  let lastEv = null;
  function sendEvent(t, ev) {
    const now = Date.now();
    if (lastEv && lastEv.action === ev.action && lastEv.value === ev.value && now - lastEv.t < 1200) return;
    lastEv = { action: ev.action, value: ev.value, t: now };
    fetch("/event", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ uid: t ? t.uid : "", title: t ? t.title : "", kind: ev.kind, action: ev.action, label: ev.label, value: ev.value == null ? "" : ev.value }) }).catch(() => {});
    if (ev.kind !== "prompt") toast(`${ev.kind === "choice" ? "chose" : "sent"} "${ev.label}"`, 1400);
  }

  // ---- the saved scene, back on the board
  async function restore() {
    let sc = null;
    try { const r = await fetch("/scene", { cache: "no-store" }); if (r.ok) sc = await r.json(); } catch (e) {}
    const list = sc && Array.isArray(sc.items) ? sc.items : []; const specs = (sc && sc.ui) || {}; let pres = null, n = 0;
    for (const s of list) {
      try {
        let t = null;
        const base = { title: str(s.title), x: num(s.x, 0.5), y: num(s.y, 0.45), w: s.tw != null ? num(s.tw, undefined) : undefined, h: s.th != null ? num(s.th, undefined) : undefined };
        if (s.type === "ui") { const rec = specs[s.uid]; if (!rec || !rec.spec) continue; t = addTile({ ...base, type: "ui", spec: rec.spec, uid: s.uid, uv: num(rec.v, 1), state: s.us, aspect: s.ua || undefined, hidebar: s.ub }); }
        else if (s.type === "card") t = addTile({ ...base, type: "card", body: str(s.body), file: str(s.file) });
        else if (s.type === "img" && s.src) t = addTile({ ...base, type: "img", src: s.src });
        else if (s.type === "model" && s.src) t = addTile({ ...base, type: "model", src: s.src });
        else if (s.type === "panel" && s.file) t = addTile({ ...base, type: "panel", file: s.file, w: base.w != null ? base.w : 0.36, h: base.h != null ? base.h : 0.62, sy: num(s.sy, 0) });
        if (t) { n++; if (s.pres) pres = t; }
      } catch (e) { console.warn("[board] restore", s.type, e); }
    }
    if (n) requestAnimationFrame(() => { settle(); if (pres) present(pres); });
    if (n) toast(`the board is back: ${n} item${n > 1 ? "s" : ""}`);
    return n;
  }

  // ---- the empty board says what it is for
  function buildEmpty() {
    const card = el("div", "emptycard");
    card.appendChild(el("div", "kicker", `${str(CFG.name || "the agent")} · the board`));
    card.appendChild(el("h1", null, "Ask me for something to see. It lands here."));
    card.appendChild(el("p", null, "Pictures and research, notes from the vault, charts and tables, a plan, a video, a map. Whatever I put up stays until you clear it."));
    const how = el("p", "how");
    if (narrow()) how.append("Tap a title to spotlight a tile, tap it again to let it go; × puts a tile away.");
    else how.append("Drag a tile by its title. Scroll inside a panel. Double-click a title to spotlight it, click × to put it away. ", el("b", null, "Tidy"), " lines everything up.");
    card.appendChild(how);
    const prompts = el("div", "prompts");
    ["Show me today's headlines", "Put my active priorities on the board", "Draw this week's deploys as a chart", "Show me pictures of Kampala at night"].forEach(p => {
      const b = el("button", null, p); b.type = "button";
      b.addEventListener("click", () => { sendEvent(null, { kind: "prompt", action: "prompt", label: p, value: "" }); b.classList.add("sent"); b.textContent = "sent: " + p; setTimeout(() => { b.classList.remove("sent"); b.textContent = p; }, 4000); });
      prompts.appendChild(b);
    });
    card.appendChild(prompts);
    emptyEl.replaceChildren(card);
  }

  // ---- one bar for every interface, the console's: a board opened on its own goes to the console's Hands view, which frames
  //      it under that bar. A bench, or a console that is not up, keeps the bare page (?bare=1 asks for it outright).
  function handOver() {
    if (window.top !== window || new URLSearchParams(location.search).has("bare")) return;
    const host = location.hostname === "127.0.0.1" ? "localhost" : location.hostname;
    const console_ = location.protocol === "https:" ? `https://${host}` : `http://${host}:3100`;   // over Tailscale's https the console is on 443
    fetch(console_ + "/", { mode: "no-cors", cache: "no-store" }).then(() => location.replace(console_ + "/hands")).catch(() => {});
  }

  // ---- boot
  (async () => {
    handOver();
    try { const r = await fetch("/config"); if (r.ok) CFG = await r.json(); } catch (e) {}
    buildEmpty();
    await restore();
    dirty();
    setInterval(beat, 300); beat();
  })();

  window.__board = { tiles: () => tiles, tidy, present, unpresent, applyCmds, autoPlace, layoutTile, narrow };
})();
