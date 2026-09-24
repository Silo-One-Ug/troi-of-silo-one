// panes.js — a small window manager shared by the console page and the galaxies.
// A pane is any element with a <header class="ph">: it can be dragged by that header,
// resized from its bottom-right corner, minimised into a chip on the dock, and it
// remembers its place (localStorage). Nothing here knows what a pane contains.
//
//   Panes.make(el, { id, title, dock, at: { left|right, top|bottom, w, h }, min: [w, h], open: true|false, onShow, onHide })
//   Panes.show(id) / hide(id) / toggle(id) / isOpen(id) / tidy() / raise(id)
window.Panes = (function () {
  const store = { get: k => { try { return JSON.parse(localStorage.getItem("pane:" + k) || "null"); } catch (e) { return null; } },
                  set: (k, v) => { try { localStorage.setItem("pane:" + k, JSON.stringify(v)); } catch (e) {} } };
  const panes = new Map(); let z = 20; const SNAP = 16;
  const css = document.createElement("style");
  css.textContent = `
    .pane { position: fixed; display: flex; flex-direction: column; min-width: 240px; min-height: 120px; overflow: hidden; }
    .pane.pane-hidden { display: none !important; }
    .pane > .ph { display: flex; align-items: center; gap: 8px; cursor: grab; user-select: none; -webkit-user-select: none; touch-action: none; }
    .pane > .ph:active { cursor: grabbing; }
    .pane > .ph .pt { font-weight: 650; letter-spacing: .12em; font-size: 11.5px; text-transform: uppercase; }
    .pane > .ph .psp { flex: 1; }
    .pane > .ph .pbtn { all: unset; cursor: pointer; width: 26px; height: 26px; display: grid; place-items: center; border-radius: 8px; opacity: .75; }
    .pane > .ph .pbtn:hover { opacity: 1; background: rgba(255,255,255,.08); }
    .pane > .ph .pbtn svg { width: 14px; height: 14px; }
    .pane .pgrow { position: absolute; right: 0; bottom: 0; width: 20px; height: 20px; cursor: nwse-resize; opacity: .5; z-index: 2;
                   background: linear-gradient(135deg, transparent 55%, rgba(140,220,255,.5) 55%, rgba(140,220,255,.5) 63%, transparent 63%, transparent 76%, rgba(140,220,255,.5) 76%, rgba(140,220,255,.5) 84%, transparent 84%); }
    .pane .pgrow:hover { opacity: .9; }
    .pchip { all: unset; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; padding: 5px 11px; border-radius: 999px; font-size: 11.5px;
             border: 1px solid rgba(140,220,255,.3); background: rgba(140,220,255,.08); color: inherit; white-space: nowrap; }
    .pchip:hover { background: rgba(140,220,255,.18); }
    .pchip i { width: 7px; height: 7px; border-radius: 50%; background: rgba(140,220,255,.8); }
    .pchip.alert i { background: #ff9b8a; box-shadow: 0 0 8px #ff9b8a; }`;
  document.head.appendChild(css);

  const svg = { min: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M5 12h14"/></svg>' };
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

  function place(p, x, y) {
    const el = p.el, w = el.offsetWidth, h = el.offsetHeight;
    x = clamp(x, 0, Math.max(0, innerWidth - w)); y = clamp(y, 0, Math.max(0, innerHeight - Math.min(h, 60)));
    if (x < SNAP) x = 0; if (y < SNAP) y = 0;
    if (innerWidth - (x + w) < SNAP) x = innerWidth - w; if (innerHeight - (y + h) < SNAP + (p.opts.margin || 0)) y = innerHeight - h - (p.opts.margin || 0);
    el.style.left = Math.round(x) + "px"; el.style.top = Math.round(y) + "px"; el.style.right = "auto"; el.style.bottom = "auto";
  }
  function size(p, w, h) {
    const [mw, mh] = p.opts.min || [260, 140];
    p.el.style.width = clamp(w, mw, innerWidth) + "px"; p.el.style.height = clamp(h, mh, innerHeight) + "px"; p.el.style.maxHeight = "none";
  }
  function save(p) { store.set(p.id, { x: p.el.offsetLeft, y: p.el.offsetTop, w: p.el.offsetWidth, h: p.el.offsetHeight, open: !p.el.classList.contains("pane-hidden") }); }
  function applyDefault(p) {
    const a = p.opts.at || {}; const el = p.el;
    el.style.left = el.style.right = el.style.top = el.style.bottom = "";
    if (a.w) el.style.width = (typeof a.w === "number" ? a.w + "px" : a.w); if (a.h) { el.style.height = (typeof a.h === "number" ? a.h + "px" : a.h); el.style.maxHeight = "none"; }
    // resolve to left/top so dragging and clamping work the same afterwards
    const w = el.offsetWidth, h = el.offsetHeight;
    const x = a.left !== undefined ? a.left : a.right !== undefined ? innerWidth - w - a.right : (innerWidth - w) / 2;
    const y = a.top !== undefined ? a.top : a.bottom !== undefined ? innerHeight - h - a.bottom : (innerHeight - h) / 2;
    el.style.left = Math.round(clamp(x, 0, Math.max(0, innerWidth - w))) + "px"; el.style.top = Math.round(clamp(y, 0, Math.max(0, innerHeight - h))) + "px"; el.style.right = "auto"; el.style.bottom = "auto";
  }
  function chip(p) {
    if (!p.opts.dock) return;
    let c = p.opts.dock.querySelector(`[data-chip="${p.id}"]`);
    if (!p.el.classList.contains("pane-hidden") || (!p.minimised && !p.alert)) { if (c) c.remove(); return; }
    if (!c) { c = document.createElement("button"); c.className = "pchip"; c.dataset.chip = p.id; c.innerHTML = "<i></i><span></span>"; c.title = "Bring back " + p.opts.title; c.onclick = () => show(p.id); p.opts.dock.appendChild(c); }
    c.querySelector("span").textContent = p.opts.chipLabel || p.opts.title; c.classList.toggle("alert", !!p.alert);
  }
  function raise(id) { const p = panes.get(id); if (p) p.el.style.zIndex = ++z; }
  function show(id) { const p = panes.get(id); if (!p) return; p.el.classList.remove("pane-hidden"); raise(id); chip(p); save(p); if (p.opts.onShow) p.opts.onShow(); }
  function hide(id, quiet) { const p = panes.get(id); if (!p) return; if (!quiet) p.minimised = true; p.el.classList.add("pane-hidden"); chip(p); save(p); if (p.opts.onHide) p.opts.onHide(); }
  function toggle(id) { isOpen(id) ? hide(id) : show(id); }
  function isOpen(id) { const p = panes.get(id); return !!p && !p.el.classList.contains("pane-hidden"); }
  function alert(id, on) { const p = panes.get(id); if (!p) return; p.alert = on; chip(p); }
  function tidy() { panes.forEach(p => { applyDefault(p); p.minimised = false; if (p.opts.open === false) p.el.classList.add("pane-hidden"); else p.el.classList.remove("pane-hidden"); chip(p); save(p); }); }

  function make(el, opts) {
    const id = opts.id || el.id; const p = { id, el, opts };
    panes.set(id, p); el.classList.add("pane"); el.dataset.pane = id;
    let h = el.querySelector(":scope > header.ph");
    if (!h) { h = document.createElement("header"); h.className = "ph"; h.innerHTML = `<span class="pt"></span>`; el.prepend(h); }
    if (opts.title && h.querySelector(".pt") && !h.querySelector(".pt").textContent) h.querySelector(".pt").textContent = opts.title;
    if (!h.querySelector(".psp")) { const sp = document.createElement("span"); sp.className = "psp"; h.appendChild(sp); }
    const mb = document.createElement("button"); mb.className = "pbtn pmin"; mb.type = "button"; mb.title = "Minimise to the dock"; mb.setAttribute("aria-label", "Minimise"); mb.innerHTML = svg.min;
    mb.onclick = e => { e.stopPropagation(); hide(id); }; h.appendChild(mb);
    const g = document.createElement("div"); g.className = "pgrow"; g.title = "Drag to resize"; el.appendChild(g);
    // z-order: whatever you touch comes to the front
    el.addEventListener("pointerdown", () => raise(id), true);
    // drag by the header
    let drag = null;
    h.addEventListener("pointerdown", e => { if (e.target.closest("button, input, select, textarea, a, label")) return; drag = { dx: e.clientX - el.offsetLeft, dy: e.clientY - el.offsetTop }; h.setPointerCapture(e.pointerId); e.preventDefault(); });
    h.addEventListener("pointermove", e => { if (!drag) return; el.style.left = (e.clientX - drag.dx) + "px"; el.style.top = (e.clientY - drag.dy) + "px"; el.style.right = "auto"; el.style.bottom = "auto"; });
    h.addEventListener("pointerup", e => { if (!drag) return; drag = null; place(p, el.offsetLeft, el.offsetTop); save(p); });
    h.addEventListener("dblclick", e => { if (e.target.closest("button, input")) return; applyDefault(p); save(p); });
    // resize from the corner
    let rs = null;
    g.addEventListener("pointerdown", e => { rs = { x: e.clientX, y: e.clientY, w: el.offsetWidth, h: el.offsetHeight }; g.setPointerCapture(e.pointerId); e.preventDefault(); e.stopPropagation(); });
    g.addEventListener("pointermove", e => { if (rs) size(p, rs.w + e.clientX - rs.x, rs.h + e.clientY - rs.y); });
    g.addEventListener("pointerup", () => { if (rs) { rs = null; place(p, el.offsetLeft, el.offsetTop); save(p); } });
    // where it was last time, or the default spot
    const s = store.get(id);
    if (s && s.w) { size(p, s.w, s.h); el.style.right = "auto"; el.style.bottom = "auto"; el.style.left = s.x + "px"; el.style.top = s.y + "px"; place(p, s.x, s.y); }
    else applyDefault(p);
    const open = s && typeof s.open === "boolean" ? s.open : opts.open !== false;
    if (!open) el.classList.add("pane-hidden");
    el.style.zIndex = ++z; chip(p);
    return p;
  }
  addEventListener("resize", () => panes.forEach(p => { if (p.el.style.left) place(p, p.el.offsetLeft, p.el.offsetTop); }));
  return { make, show, hide, toggle, isOpen, tidy, raise, alert, place: (id, x, y) => { const p = panes.get(id); if (p) place(p, x, y); } };
})();
