// board-render.js — the UI panels' renderer for the hands board (Silo One's addition; injected by patch-board.sh,
// the upstream files stay as they are). JSON in, glass interface out: the same component vocabulary show.py draws in
// the console's conversation, here as hand-held panels. Shared by the tracker page and the on-air mirror
// (?role=render). Nothing here evaluates markup from the agent: every string lands as text, every address is checked
// (https, or the board's own /media/ airlock), links never navigate the board away.
//
//   window.__boardRender.render(spec, state, cx) -> element      cx: { live, onState(state), onEvent(ev) }
//   window.__boardRender.applyState(root, state)                 tabs, slides, accordions, choices follow the state
//   window.__boardRender.act(root, state, "tab:KEY:2")           a tap on [data-act]; returns { changed, event }
//   window.__boardRender.step(root, state, op, i, id)            next | prev | goto on the first slideshow or tabs (or by id)
//   window.__boardRender.media(root, op, arg, id)                play | pause | toggle | mute | unmute | seek on video, audio, YouTube, Vimeo
//   window.__boardRender.count(spec)                             how many components a tree holds
(function () {
  const PALETTE = ["#8ff0e4", "#f4ae45", "#7cc7ff", "#b39cff", "#7be3a5", "#ff8fa3", "#ffd166", "#5ad1c9"];
  const TONES = ["ok", "note", "warn", "bad", "muted"];
  // the named colours of board-theme.css: any component wears one as its tone, and a chart series can be one by name
  const COLS = ["rust", "clay", "ocean", "sky", "navy", "forest", "moss", "lime", "sand", "sun", "gold", "berry", "rose", "coral", "violet", "lavender", "slate", "steel", "teal", "mint"];
  const PATTERNS = ["dots", "grid", "rays", "waves", "none"];
  const MAX_DEPTH = 10, MAX_KIDS = 200, MAX_ROWS = 600;

  // ---- small helpers: elements as text, never markup
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = String(text); return e; };
  const svgEl = (tag, attrs) => { const e = document.createElementNS("http://www.w3.org/2000/svg", tag); for (const k in attrs || {}) e.setAttribute(k, attrs[k]); return e; };
  const num = (v, d) => { const n = Number(v); return Number.isFinite(n) ? n : d; };
  const str = v => v == null ? "" : String(v);
  const tone = t => TONES.includes(t) || COLS.includes(t) ? t : "note";
  const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
  const safeUrl = u => { u = str(u).trim(); return /^https:\/\/\S+$/i.test(u) || (u.startsWith("/media/") && !u.includes("..")) ? u : ""; };
  const host = u => { try { return new URL(u).hostname.replace(/^www\./, ""); } catch (e) { return ""; } };
  // an aspect ratio in any of the usual spellings: "16:9", "16/9", "4x3", 1.5
  const aspect = a => {
    if (a == null || a === "") return "";
    if (typeof a === "number") return a > 0 ? String(a) : "";
    const m = String(a).match(/^\s*(\d+(?:\.\d+)?)\s*[:/xX]\s*(\d+(?:\.\d+)?)\s*$/);
    return m && +m[2] > 0 ? `${m[1]} / ${m[2]}` : "";
  };
  const fmt = v => {
    if (typeof v !== "number" || !Number.isFinite(v)) return str(v);
    const a = Math.abs(v);
    if (a >= 1e9) return (v / 1e9).toFixed(a >= 1e10 ? 0 : 1) + "B";
    if (a >= 1e6) return (v / 1e6).toFixed(a >= 1e7 ? 0 : 1) + "M";
    if (a >= 1e4) return (v / 1e3).toFixed(a >= 1e5 ? 0 : 1) + "k";
    return Number.isInteger(v) ? String(v) : String(+v.toFixed(2));
  };
  const keyOf = (node, path) => str(node.id || node.key || path);

  // a link on the board (Paul, 2026-09-27: "links are not clickable on the board"): an https address opens in a new tab and the
  // board stays where it is; anything else is shown as words with the address in the tooltip, never followed
  function anchor(text, href, withHost) {
    const h = safeUrl(href);
    if (!h || !/^https:/i.test(h)) { const s = el("span", "uilink", text || str(href)); s.title = str(href); return s; }
    const a = el("a", "uilink", text || h); a.href = h; a.target = "_blank"; a.rel = "noopener noreferrer"; a.title = h;
    const hs = host(h); if (withHost && hs && text) a.appendChild(el("span", "uimuted uihost", " " + hs));
    return a;
  }
  // ---- inline markdown: **bold**, *italic*, `code`, [text](https://…) (a link that opens in a new tab), line breaks
  function inline(text) {
    const frag = document.createDocumentFragment();
    const s = str(text);
    const re = /(\*\*[^*\n]+\*\*|\*[^*\n]+\*|`[^`\n]+`|\[[^\]\n]+\]\((https?:\/\/[^)\s]+)\)|\n)/g;
    let last = 0, m;
    while ((m = re.exec(s))) {
      if (m.index > last) frag.appendChild(document.createTextNode(s.slice(last, m.index)));
      const t = m[0];
      if (t === "\n") frag.appendChild(el("br"));
      else if (t.startsWith("**")) frag.appendChild(el("b", null, t.slice(2, -2)));
      else if (t.startsWith("`")) frag.appendChild(el("code", "uiinlinecode", t.slice(1, -1)));
      else if (t.startsWith("[")) { frag.appendChild(anchor(t.slice(1, t.indexOf("](")), m[2])); }
      else frag.appendChild(el("i", null, t.slice(1, -1)));
      last = m.index + t.length;
    }
    if (last < s.length) frag.appendChild(document.createTextNode(s.slice(last)));
    return frag;
  }

  // ---- block markdown for the md component: headings, bullets, numbers, quotes, fences, rules, pipe tables, paragraphs
  function markdown(text) {
    const root = el("div", "uimd");
    const lines = str(text).replace(/\r/g, "").split("\n");
    let i = 0, para = [];
    if (lines[0] === "---") { const end = lines.indexOf("---", 1); if (end > 0) i = end + 1; }   // a note's front matter is for the vault, not the reader
    const flush = () => { if (para.length) { const p = el("p"); p.appendChild(inline(para.join("\n"))); root.appendChild(p); para = []; } };
    while (i < lines.length) {
      const l = lines[i];
      if (/^```/.test(l)) { flush(); const buf = []; i++; while (i < lines.length && !/^```/.test(lines[i])) buf.push(lines[i++]); i++; root.appendChild(el("pre", "uicode", buf.join("\n"))); continue; }
      let m;
      if ((m = /^(#{1,6})\s+(.*)$/.exec(l))) { flush(); const h = el("h" + Math.min(4, m[1].length), "uih uih" + Math.min(4, m[1].length)); h.appendChild(inline(m[2])); root.appendChild(h); i++; continue; }
      if (/^\s*(-{3,}|\*{3,}|_{3,})\s*$/.test(l)) { flush(); root.appendChild(el("hr", "uidivider")); i++; continue; }
      if (/^\s*[-*+]\s+/.test(l) || /^\s*\d+[.)]\s+/.test(l)) {
        flush(); const ordered = /^\s*\d+[.)]\s+/.test(l); const list = el(ordered ? "ol" : "ul", "uilist");
        while (i < lines.length && (/^\s*[-*+]\s+/.test(lines[i]) || /^\s*\d+[.)]\s+/.test(lines[i]))) {
          const item = lines[i].replace(/^\s*([-*+]|\d+[.)])\s+/, ""); const li = el("li");
          const cb = /^\[( |x|X)\]\s+/.exec(item);
          if (cb) { li.classList.add("uicheck", cb[1] !== " " ? "done" : "todo"); li.dataset.line = String(i); li.dataset.act = "chk:md:" + i; li.appendChild(inline(item.slice(cb[0].length))); }
          else li.appendChild(inline(item));
          list.appendChild(li); i++;
        }
        root.appendChild(list); continue;
      }
      if (/^\s*>\s?/.test(l)) { flush(); const buf = []; while (i < lines.length && /^\s*>\s?/.test(lines[i])) buf.push(lines[i++].replace(/^\s*>\s?/, "")); const q = el("blockquote", "uiquote"); q.appendChild(inline(buf.join("\n"))); root.appendChild(q); continue; }
      if (/^\s*\|.*\|\s*$/.test(l) && i + 1 < lines.length && /^\s*\|?\s*:?-{2,}/.test(lines[i + 1])) {
        flush(); const cells = r => r.trim().replace(/^\||\|$/g, "").split("|").map(c => c.trim());
        const cols = cells(l); i += 2; const rows = [];
        while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) rows.push(cells(lines[i++]));
        root.appendChild(table({ columns: cols, rows }, null)); continue;
      }
      if (!l.trim()) { flush(); i++; continue; }
      para.push(l); i++;
    }
    flush();
    return root;
  }

  // ---- the renderer proper
  function kids(node, cx, path, depth) {
    const out = [];
    const list = Array.isArray(node.children) ? node.children.slice(0, MAX_KIDS) : [];
    list.forEach((c, i) => { const e = render(c, cx, `${path}.${i}`, depth + 1); if (e) out.push(e); });
    return out;
  }
  const append = (parent, list) => { for (const e of list) parent.appendChild(e); return parent; };
  const gapClass = g => g === "sm" || g === "lg" || g === "none" ? " gap-" + g : "";

  function stack(n, cx, path, depth) { return append(el("div", "uistack" + gapClass(n.gap)), kids(n, cx, path, depth)); }
  function row(n, cx, path, depth) {
    const r = el("div", "uirow" + gapClass(n.gap) + (n.wrap === 0 || n.wrap === false ? " nowrap" : ""));
    if (n.align) r.style.alignItems = { start: "flex-start", center: "center", end: "flex-end", stretch: "stretch" }[n.align] || "";
    if (n.justify) r.style.justifyContent = { start: "flex-start", center: "center", end: "flex-end", between: "space-between", around: "space-around" }[n.justify] || "";
    return append(r, kids(n, cx, path, depth));
  }
  function grid(n, cx, path, depth) {
    const list = kids(n, cx, path, depth);
    const auto = list.length <= 1 ? 1 : list.length <= 3 ? list.length : list.length === 4 ? 2 : list.length <= 6 ? 3 : 4;
    const cols = clamp(Math.round(num(n.cols, auto)), 1, 6);
    const g = el("div", "uigrid" + gapClass(n.gap)); g.style.gridTemplateColumns = `repeat(${cols}, minmax(0, 1fr))`;
    return append(g, list);
  }
  function columns(n, cx, path, depth) {
    const list = kids(n, cx, path, depth);
    const w = Array.isArray(n.weights) && n.weights.length ? n.weights : list.map(() => 1);
    const g = el("div", "uigrid uicols" + gapClass(n.gap)); g.style.gridTemplateColumns = list.map((_, i) => `${clamp(num(w[i], 1), 0.2, 12)}fr`).join(" ");
    return append(g, list);
  }
  function card(n, cx, path, depth) {
    const c = el("div", "uicard" + (n.tone ? " tone-" + tone(n.tone) : ""));
    if (n.title || n.subtitle) { const h = el("div", "uicardhead"); if (n.title) h.appendChild(el("div", "uicardtitle", n.title)); if (n.subtitle) h.appendChild(el("div", "uimuted", n.subtitle)); c.appendChild(h); }
    const body = append(el("div", "uistack"), kids(n, cx, path, depth)); if (body.childNodes.length) c.appendChild(body);
    if (n.footer) c.appendChild(el("div", "uicardfoot", n.footer));
    return c;
  }
  function group(n, cx, path, depth) {
    const f = el("fieldset", "uigroup"); if (n.title) f.appendChild(el("legend", null, n.title));
    return append(f, kids(n, cx, path, depth));
  }
  function tabs(n, cx, path, depth) {
    const items = (Array.isArray(n.items) ? n.items : []).filter(i => i && i.label).slice(0, 12);
    if (!items.length) return null;
    const key = keyOf(n, path); const root = el("div", "uitabs"); root.dataset.key = key; root.dataset.kind = "tabs"; root.dataset.n = items.length;
    const list = el("div", "uitablist");
    items.forEach((it, i) => { const t = el("span", "uitab", it.label); t.dataset.act = `tab:${key}:${i}`; list.appendChild(t); });
    root.appendChild(list);
    items.forEach((it, i) => { const p = el("div", "uipane"); const c = it.child ? render(it.child, cx, `${path}.${i}`, depth + 1) : null; if (c) p.appendChild(c); root.appendChild(p); });
    setTabs(root, num(cx.state[key], clamp(num(n.active, 0), 0, items.length - 1)));
    return root;
  }
  function setTabs(root, i) {
    const n = num(root.dataset.n, 1); i = clamp(Math.round(num(i, 0)), 0, n - 1);
    root.querySelectorAll(":scope > .uitablist > .uitab").forEach((t, k) => t.classList.toggle("on", k === i));
    root.querySelectorAll(":scope > .uipane").forEach((p, k) => p.classList.toggle("on", k === i));
    root.dataset.i = i;
  }
  function accordion(n, cx, path, depth) {
    const items = (Array.isArray(n.items) ? n.items : []).filter(i => i && i.label).slice(0, 30);
    if (!items.length) return null;
    const key = keyOf(n, path); const root = el("div", "uiacc"); root.dataset.key = key; root.dataset.kind = "acc"; if (n.single) root.dataset.single = "1";
    items.forEach((it, i) => {
      const item = el("div", "uiaccitem"); const head = el("div", "uiacchead"); head.dataset.act = `acc:${key}:${i}`;
      head.appendChild(el("span", "uiaccmark")); head.appendChild(el("span", "uiacclabel", it.label)); if (it.note) head.appendChild(el("span", "uimuted uiaccnote", it.note));
      const body = el("div", "uiaccbody"); const c = it.child ? render(it.child, cx, `${path}.${i}`, depth + 1) : (it.text ? textNode({ text: it.text }) : null); if (c) body.appendChild(c);
      item.appendChild(head); item.appendChild(body); root.appendChild(item);
    });
    const open = Array.isArray(cx.state[key]) ? cx.state[key] : items.map((it, i) => it.open ? i : -1).filter(i => i >= 0);
    setAcc(root, open);
    return root;
  }
  function setAcc(root, open) {
    const set = new Set((Array.isArray(open) ? open : []).map(Number));
    root.querySelectorAll(":scope > .uiaccitem").forEach((it, k) => it.classList.toggle("open", set.has(k)));
  }
  function chevron(dir) { const g = svgEl("svg", { viewBox: "0 0 24 24", width: 16, height: 16, fill: "none", stroke: "currentColor", "stroke-width": 2, "stroke-linecap": "round", "stroke-linejoin": "round" }); g.appendChild(svgEl("path", { d: dir < 0 ? "M15 18l-6-6 6-6" : "M9 18l6-6-6-6" })); return g; }
  function slideshow(n, cx, path, depth) {
    const raw = (Array.isArray(n.items) ? n.items : []).slice(0, 60);
    const items = raw.map(it => typeof it === "string" ? { url: it } : it).filter(it => it && typeof it === "object");
    if (!items.length) return null;
    const key = keyOf(n, path); const root = el("div", "uislides"); root.dataset.key = key; root.dataset.kind = "slides"; root.dataset.n = items.length; root.tabIndex = 0;
    const view = el("div", "uiview"); view.style.aspectRatio = aspect(n.aspect) || "16 / 9";
    const track = el("div", "uitrack");
    items.forEach((it, i) => {
      const sl = el("div", "uislide"); let c;
      if (it.type) c = render(it, cx, `${path}.${i}`, depth + 1);
      else { const u = safeUrl(it.url || it.src); if (u) { const im = el("img"); im.src = u; im.alt = str(it.title || it.caption || ""); im.loading = "lazy"; im.draggable = false; im.style.objectFit = it.fit === "contain" || n.fit === "contain" ? "contain" : "cover"; c = im; } }
      if (c) sl.appendChild(c);
      const cap = it.caption || (it.type ? "" : it.title); if (cap) sl.appendChild(el("div", "uislidecap", cap));
      track.appendChild(sl);
    });
    view.appendChild(track); root.appendChild(view);
    let drag = null;
    const go = i => { i = ((i % items.length) + items.length) % items.length; setSlide(root, i); cx.state[key] = i; cx.onState && cx.onState(cx.state); };
    if (items.length > 1) {
      const prev = el("span", "uinav prev"); prev.dataset.act = `slide:${key}:prev`; prev.appendChild(chevron(-1));
      const next = el("span", "uinav next"); next.dataset.act = `slide:${key}:next`; next.appendChild(chevron(1));
      root.appendChild(prev); root.appendChild(next);
      const dots = el("div", "uidots"); items.forEach((_, i) => { const d = el("span", "uidot"); d.dataset.act = `slide:${key}:${i}`; dots.appendChild(d); }); root.appendChild(dots);
      view.addEventListener("mousedown", e => { if (e.button !== 0 || e.target.closest("video, audio, iframe, [data-act]")) return; drag = { x: e.clientX, w: view.offsetWidth || 1 }; track.classList.add("dragging"); e.preventDefault(); });
      const onMove = e => { if (!drag) return; const dx = e.clientX - drag.x; track.style.transform = `translateX(calc(${-num(root.dataset.i, 0) * 100}% + ${dx}px))`; };
      const onUp = e => { if (!drag) return; const dx = e.clientX - drag.x; track.classList.remove("dragging"); const cur = num(root.dataset.i, 0); const to = dx < -Math.min(60, drag.w * 0.15) ? cur + 1 : dx > Math.min(60, drag.w * 0.15) ? cur - 1 : cur; drag = null; if (to !== cur && to >= 0 && to < items.length) go(to); else setSlide(root, cur); };
      addEventListener("mousemove", onMove); addEventListener("mouseup", onUp);
      root.addEventListener("keydown", e => { if (e.key === "ArrowRight") { go(num(root.dataset.i, 0) + 1); e.preventDefault(); } else if (e.key === "ArrowLeft") { go(num(root.dataset.i, 0) - 1); e.preventDefault(); } });
    }
    if (n.title) root.appendChild(el("div", "uimuted uislidetitle", n.title));
    setSlide(root, num(cx.state[key], clamp(num(n.index, 0), 0, items.length - 1)));
    const every = n.autoplay === 0 || n.autoplay === false ? 0 : clamp(num(n.interval, 6), 2, 600) * 1000;
    if (cx.live && every && items.length > 1) {
      root._timer = setInterval(() => {
        if (!root.isConnected) { clearInterval(root._timer); return; }
        if (drag || root.matches(":hover")) return;                                   // a hand on it holds it
        const pane = root.closest(".uipane"); if (pane && !pane.classList.contains("on")) return;
        go(num(root.dataset.i, 0) + 1);
      }, every);
    }
    return root;
  }
  function setSlide(root, i) {
    const n = num(root.dataset.n, 1); i = ((Math.round(num(i, 0)) % n) + n) % n;
    const track = root.querySelector(":scope > .uiview > .uitrack"); if (track) track.style.transform = `translateX(${-i * 100}%)`;
    root.querySelectorAll(":scope > .uidots > .uidot").forEach((d, k) => d.classList.toggle("on", k === i));
    root.dataset.i = i;
  }
  function steps(n, cx) {
    const items = (Array.isArray(n.items) ? n.items : []).slice(0, 40).map(it => typeof it === "string" ? { title: it } : it).filter(it => it && typeof it === "object");
    if (!items.length) return null;
    const cur = n.current != null ? num(n.current, -1) : -1;
    const root = el("ol", "uisteps");
    items.forEach((it, i) => {
      const st = it.status || (cur >= 0 ? (i < cur ? "done" : i === cur ? "current" : "todo") : "todo");
      const li = el("li", "uistep " + (["done", "current", "todo"].includes(st) ? st : "todo") + (it.tone ? " tone-" + tone(it.tone) : ""));
      const mark = el("span", "uistepmark", st === "done" ? "" : String(i + 1)); li.appendChild(mark);
      const body = el("div", "uistepbody"); body.appendChild(el("div", "uisteptitle", it.title || it.text || "")); if (it.body || it.note) { const p = el("div", "uimuted"); p.appendChild(inline(it.body || it.note)); body.appendChild(p); }
      li.appendChild(body); root.appendChild(li);
    });
    return root;
  }
  function timeline(n) {
    const items = (Array.isArray(n.items) ? n.items : []).slice(0, 60).filter(it => it && typeof it === "object");
    if (!items.length) return null;
    const root = el("div", "uitimeline");
    items.forEach(it => {
      const r = el("div", "uitl" + (it.tone ? " tone-" + tone(it.tone) : ""));
      r.appendChild(el("div", "uitltime", it.time || it.when || ""));
      const dot = el("span", "uitldot"); r.appendChild(dot);
      const b = el("div", "uitlbody"); if (it.title) b.appendChild(el("div", "uitltitle", it.title)); if (it.body || it.text) { const p = el("div", "uimuted"); p.appendChild(inline(it.body || it.text)); b.appendChild(p); }
      r.appendChild(b); root.appendChild(r);
    });
    return root;
  }
  function divider(n) { const h = el("div", "uidivider" + (n.label ? " labelled" : "")); if (n.label) h.appendChild(el("span", null, n.label)); return h; }
  function spacer(n) { const d = el("div", "uispacer"); d.style.height = clamp(num(n.h, 12), 0, 400) + "px"; return d; }
  function aspectBox(n, cx, path, depth) {
    const d = el("div", "uiaspect"); d.style.aspectRatio = aspect(n.ratio || n.aspect) || "16 / 9";
    const c = n.child ? render(n.child, cx, path + ".0", depth + 1) : null; if (c) d.appendChild(c);
    return d;
  }
  function hero(n) {
    const d = el("div", "uihero"); d.style.aspectRatio = aspect(n.aspect) || "16 / 7";
    const u = safeUrl(n.src || n.url); if (u) d.style.backgroundImage = `url("${u.replace(/"/g, "%22")}")`;
    else {   // no picture: a band in the theme's two hues (or the tone named), with a quiet pattern over it
      d.classList.add("band", "pattern-" + (PATTERNS.includes(n.pattern) ? n.pattern : "dots")); if (n.tone) d.classList.add("tone-" + tone(n.tone));
      if (!aspect(n.aspect)) d.style.aspectRatio = "16 / 5";
    }
    const t = el("div", "uiherotext"); if (n.kicker) t.appendChild(el("div", "uilabel", n.kicker)); if (n.title) t.appendChild(el("div", "uiherotitle", n.title)); if (n.subtitle) { const s = el("div", "uiherosub"); s.appendChild(inline(n.subtitle)); t.appendChild(s); }
    d.appendChild(t); return d;
  }
  function heading(n) { const lv = clamp(Math.round(num(n.level, 2)), 1, 4); const h = el("h" + lv, "uih uih" + lv); h.appendChild(inline(n.text)); if (n.align) h.style.textAlign = n.align; return h; }
  function textNode(n) {
    const p = el("p", "uitext" + (n.size ? " size-" + ({ sm: "sm", md: "md", lg: "lg", xl: "xl" }[n.size] || "md") : "") + (n.muted ? " uimuted" : "") + (n.mono ? " mono" : ""));
    p.appendChild(inline(n.text)); if (n.align) p.style.textAlign = n.align; return p;
  }
  function md(n) { return markdown(n.text); }
  function quote(n) { const q = el("blockquote", "uiquote"); q.appendChild(inline(n.text)); if (n.cite) q.appendChild(el("cite", null, n.cite)); return q; }
  function code(n) { const w = el("div", "uicodewrap"); if (n.lang || n.title) w.appendChild(el("div", "uilabel", n.title || n.lang)); w.appendChild(el("pre", "uicode", n.text)); return w; }
  function kbd(n) { const w = el("span", "uikbds"); const keys = Array.isArray(n.keys) ? n.keys : str(n.keys || n.text).split(/\s+/); keys.filter(Boolean).slice(0, 8).forEach(k => w.appendChild(el("kbd", null, k))); return w; }
  function badge(n) { return el("span", "uibadge tone-" + tone(n.tone), n.text); }
  function tags(n) { const w = el("div", "uitags"); (Array.isArray(n.items) ? n.items : []).slice(0, 40).forEach(t => w.appendChild(el("span", "uibadge tone-" + tone(typeof t === "object" ? t.tone : n.tone), typeof t === "object" ? t.text : t))); return w; }
  function callout(n) { const d = el("div", "uicallout tone-" + tone(n.tone)); if (n.title) d.appendChild(el("b", null, n.title)); const p = el("div"); p.appendChild(inline(n.text)); d.appendChild(p); return d; }
  function link(n) { return anchor(n.text, n.href, true); }
  function stat(n) {
    const d = el("div", "uistat" + (n.tone ? " tone-" + tone(n.tone) : "") + (n.boxed ? " boxed" : "")); d.title = [n.label, fmt(n.value) + str(n.unit || ""), n.delta != null && n.delta !== "" ? str(n.delta) : "", n.note].filter(Boolean).join(" · ");
    if (n.label) d.appendChild(el("div", "uilabel", n.label));
    const v = el("div", "uistatrow"); v.appendChild(el("span", "uistatvalue", fmt(n.value))); if (n.unit) v.appendChild(el("span", "uistatunit", n.unit));
    if (n.delta != null && n.delta !== "") v.appendChild(el("span", "uibadge tone-" + tone(n.tone || (String(n.delta).trim().startsWith("-") ? "bad" : "ok")), n.delta));
    d.appendChild(v);
    if (Array.isArray(n.spark) && n.spark.length > 1) d.appendChild(sparkSvg(n.spark, n.tone));
    if (n.note) d.appendChild(el("div", "uimuted", n.note));
    return d;
  }
  function progress(n) {
    const max = num(n.max, 100) || 100; const v = clamp(num(n.value, 0), 0, max);
    const d = el("div", "uiprogress" + (n.tone ? " tone-" + tone(n.tone) : ""));
    const top = el("div", "uiprogtop"); top.appendChild(el("span", null, n.label || "")); top.appendChild(el("span", "uimuted", n.text || (max === 100 ? Math.round(v) + "%" : fmt(v) + " / " + fmt(max)))); d.appendChild(top);
    const bar = el("div", "uiprog"); const fill = el("div", "uiprogfill"); fill.style.width = (v / max * 100).toFixed(1) + "%"; bar.appendChild(fill); d.appendChild(bar);
    return d;
  }
  function gauge(n) {
    const min = num(n.min, 0), max = num(n.max, 100), v = clamp(num(n.value, 0), Math.min(min, max), Math.max(min, max));
    const p = max === min ? 0 : (v - min) / (max - min);
    const d = el("div", "uigauge" + (n.tone ? " tone-" + tone(n.tone) : "")); d.title = (n.label ? n.label + ": " : "") + fmt(v) + str(n.unit || "") + (min !== 0 || max !== 100 ? " of " + fmt(max) : "");
    const svg = svgEl("svg", { viewBox: "0 0 200 116", class: "uigaugesvg" });
    const arc = (from, to, cls) => { const a0 = Math.PI * (1 - from), a1 = Math.PI * (1 - to); const x0 = 100 + 80 * Math.cos(a0), y0 = 100 - 80 * Math.sin(a0), x1 = 100 + 80 * Math.cos(a1), y1 = 100 - 80 * Math.sin(a1); return svgEl("path", { d: `M ${x0} ${y0} A 80 80 0 0 1 ${x1} ${y1}`, class: cls, fill: "none", "stroke-width": 14, "stroke-linecap": "round" }); };
    svg.appendChild(arc(0, 1, "uigaugetrack")); if (p > 0.001) svg.appendChild(arc(0, Math.max(0.02, p), "uigaugefill"));
    const t = svgEl("text", { x: 100, y: 92, "text-anchor": "middle", class: "uigaugevalue" }); t.textContent = fmt(v) + (n.unit ? n.unit : ""); svg.appendChild(t);
    d.appendChild(svg); if (n.label) d.appendChild(el("div", "uilabel center", n.label));
    return d;
  }
  function kv(n) {
    const items = Array.isArray(n.items) ? n.items : (n.items && typeof n.items === "object" ? Object.keys(n.items).map(k => ({ k, v: n.items[k] })) : []);
    const dl = el("dl", "uikv");
    items.slice(0, 80).forEach(it => { if (!it) return; const r = el("div", "uikvrow"); r.appendChild(el("dt", null, it.k ?? it.key ?? it.label ?? "")); const dd = el("dd"); dd.appendChild(inline(str(it.v ?? it.value ?? ""))); r.appendChild(dd); dl.appendChild(r); });
    return dl;
  }
  function list(n, cx, path) {
    const items = (Array.isArray(n.items) ? n.items : []).slice(0, MAX_ROWS);
    const checks = !!n.check || items.some(it => it && typeof it === "object" && it.done != null);
    const key = keyOf(n, path);
    const L = el(n.ordered ? "ol" : "ul", "uilist" + (checks ? " checks" : ""));
    if (checks) { L.dataset.key = key; L.dataset.kind = "checks"; L.dataset.action = str(n.action || key); }
    items.forEach((it, i) => {
      const li = el("li"); const o = typeof it === "object" && it ? it : { text: it };
      if (o.tone) li.classList.add("tone-" + tone(o.tone));
      if (checks) { li.classList.add("uicheck", o.done ? "done" : "todo"); li.dataset.act = `chk:${key}:${i}`; }
      li.appendChild(inline(o.text ?? "")); if (o.note) li.appendChild(el("div", "uimuted", o.note));
      L.appendChild(li);
    });
    if (checks && Array.isArray((cx || {}).state && cx.state[key])) setChecks(L, cx.state[key]);
    return L;
  }
  function setChecks(root, done) {
    const set = new Set((Array.isArray(done) ? done : []).map(Number));
    root.querySelectorAll(":scope > li.uicheck").forEach((li, k) => { li.classList.toggle("done", set.has(k)); li.classList.toggle("todo", !set.has(k)); });
  }
  // a cell that reads as a number (a count, a score, a minute, a percentage, a time) sits right-aligned in tabular figures
  const isNum = v => typeof v === "number" || (typeof v === "string" && /\d/.test(v) && /^[\s\d.,%+\-\u2013\u2212:'"\u2032\u2033x\u00d7\/]*$/.test(v.trim()));
  function table(n) {
    const cols = (Array.isArray(n.columns) ? n.columns : []).slice(0, 24).map(c => typeof c === "object" && c ? c : { label: str(c) });
    const rows = (Array.isArray(n.rows) ? n.rows : []).slice(0, MAX_ROWS);
    const hi = new Set((Array.isArray(n.highlight) ? n.highlight : [n.highlight]).map(Number).filter(Number.isFinite));
    const wrap = el("div", "uitablewrap"); const t = el("table", "uitable" + (n.zebra === 0 || n.zebra === false ? "" : " zebra") + (n.compact ? " compact" : ""));
    if (cols.length) { const thead = el("thead"); const tr = el("tr"); cols.forEach(c => { const th = el("th", null, c.label ?? c.key ?? ""); if (c.align) th.style.textAlign = c.align; tr.appendChild(th); }); thead.appendChild(tr); t.appendChild(thead); }
    const tb = el("tbody");
    rows.forEach((r, i) => {
      const tr = el("tr"); if (hi.has(i)) tr.classList.add("hi");
      const cells = Array.isArray(r) ? r : (r && typeof r === "object" ? cols.map(c => r[c.key ?? c.label]) : [r]);
      cells.slice(0, Math.max(cols.length, 24)).forEach((c, j) => { const td = el("td"); if (c && typeof c === "object" && c.type) { const e = render(c, { state: {}, live: false }, `${i}.${j}`, MAX_DEPTH - 1); if (e) td.appendChild(e); } else td.appendChild(inline(typeof c === "number" ? fmt(c) : str(c))); if (isNum(c)) td.classList.add("num"); if (cols[j] && cols[j].align) td.style.textAlign = cols[j].align; tr.appendChild(td); });
      tb.appendChild(tr);
    });
    t.appendChild(tb);
    for (let j = 0; j < Math.max(cols.length, 1); j++) {       // a column of numbers takes its header along to the right
      const tds = [...tb.querySelectorAll("tr")].map(tr => tr.children[j]).filter(Boolean), filled = tds.filter(td => td.textContent.trim());
      if (filled.length && filled.every(td => td.classList.contains("num"))) { const th = t.querySelector(`thead th:nth-child(${j + 1})`); if (th && !th.style.textAlign) th.classList.add("num"); }
    }
    if (Array.isArray(n.footer)) { const tf = el("tfoot"); const tr = el("tr"); n.footer.slice(0, 24).forEach((c, j) => { const td = el("td"); td.appendChild(inline(typeof c === "number" ? fmt(c) : str(c))); if (cols[j] && cols[j].align) td.style.textAlign = cols[j].align; tr.appendChild(td); }); tf.appendChild(tr); t.appendChild(tf); }
    if (n.caption) t.appendChild(el("caption", null, n.caption));
    wrap.appendChild(t); return wrap;
  }

  // ---- charts, as inline SVG: line, area, bar (grouped or stacked), pie, donut, scatter
  function niceTicks(lo, hi, n) {
    if (!(hi > lo)) { hi = lo + 1; }
    const span = hi - lo, step0 = span / Math.max(1, n), mag = Math.pow(10, Math.floor(Math.log10(step0)));
    const step = [1, 2, 2.5, 5, 10].map(m => m * mag).find(s => span / s <= n) || 10 * mag;
    const out = []; for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(+v.toFixed(10));
    return out;
  }
  function chart(n) {
    const data = (Array.isArray(n.data) ? n.data : []).filter(d => d && typeof d === "object").slice(0, MAX_ROWS);
    const kind = ["line", "bar", "area", "pie", "donut", "scatter"].includes(n.kind) ? n.kind : "line";
    const first = data[0] || {};
    const x = n.x || Object.keys(first)[0] || "x";
    const series = (Array.isArray(n.series) && n.series.length ? n.series : Object.keys(first).filter(k => k !== x && typeof first[k] === "number")).map(String).slice(0, 8);
    const wrap = el("div", "uichartwrap"); if (n.title) wrap.appendChild(el("div", "uilabel", n.title));
    if (!data.length || !series.length) { wrap.appendChild(el("div", "uimuted", "no data")); return wrap; }
    // a mark's colour: a hex the tree names stays inline; otherwise a class, and the theme's palette (board-theme.css) paints it:
    // the theme's own series colours, or a named colour ("rust", "sky", …) when the tree names one. PALETTE is the fallback attribute.
    const named = i => Array.isArray(n.colors) && typeof n.colors[i] === "string" ? n.colors[i].trim() : "";
    const hexOf = i => /^#[0-9a-f]{3,8}$/i.test(named(i)) ? named(i) : "";
    const colors = i => hexOf(i) || PALETTE[i % PALETTE.length];
    const paint = (e, i, kind) => { if (hexOf(i)) { if (kind === "b") e.style.background = hexOf(i); return e; } const nm = named(i); if (COLS.includes(nm)) e.classList.add("tone-" + nm, "uic" + kind + "-" + nm); else e.classList.add("uic" + kind + (i % 8 + 1)); return e; };
    const perCategory = kind === "bar" && series.length === 1 && !n.mono && data.length <= 12;   // one series of categories: a colour a bar, unless mono asks for one
    const W = 480, H = clamp(num(n.height, 220), 120, 600);
    const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, class: "uichart", role: "img" });
    // the tip: a small dark card that follows the mouse over a mark, naming the x and every series' value (Paul, 2026-09-27: "graphs should have tooltips, hovers")
    const unit = str(n.unit || ""), tip = el("div", "uitip"); wrap.classList.add("hastip"); wrap.appendChild(tip);
    const moveTip = evt => { const b = wrap.getBoundingClientRect(); tip.style.left = clamp(evt.clientX - b.left, 48, Math.max(48, b.width - 48)) + "px"; tip.style.top = Math.max(0, evt.clientY - b.top) + "px"; };
    const showTip = (evt, title, rows) => { tip.replaceChildren(); if (title) tip.appendChild(el("b", null, title)); rows.forEach(r => { const line = el("div", "uitiprow"); line.appendChild(paint(el("i"), r.i, "b")); if (r.label) line.appendChild(el("span", null, r.label)); line.appendChild(el("span", "uitipval", r.value)); tip.appendChild(line); }); moveTip(evt); tip.classList.add("on"); };
    const hideTip = () => tip.classList.remove("on");
    const bars = [];   // the bars of each column, lit together under the mouse
    if (kind === "pie" || kind === "donut") {
      const vals = data.map(d => Math.max(0, num(d[series[0]], 0))); const total = vals.reduce((a, b) => a + b, 0) || 1;
      const cx0 = H / 2, cy0 = H / 2, R = H / 2 - 8, r0 = kind === "donut" ? R * 0.58 : 0;
      let a = -Math.PI / 2;
      vals.forEach((v, i) => {
        const a1 = a + v / total * Math.PI * 2; const big = a1 - a > Math.PI ? 1 : 0;
        const p0 = [cx0 + R * Math.cos(a), cy0 + R * Math.sin(a)], p1 = [cx0 + R * Math.cos(a1), cy0 + R * Math.sin(a1)];
        let d;
        if (v / total > 0.9999) d = `M ${cx0 + R} ${cy0} A ${R} ${R} 0 1 1 ${cx0 - R} ${cy0} A ${R} ${R} 0 1 1 ${cx0 + R} ${cy0}` + (r0 ? ` M ${cx0 + r0} ${cy0} A ${r0} ${r0} 0 1 0 ${cx0 - r0} ${cy0} A ${r0} ${r0} 0 1 0 ${cx0 + r0} ${cy0}` : "");
        else if (r0) { const q0 = [cx0 + r0 * Math.cos(a1), cy0 + r0 * Math.sin(a1)], q1 = [cx0 + r0 * Math.cos(a), cy0 + r0 * Math.sin(a)]; d = `M ${p0.join(" ")} A ${R} ${R} 0 ${big} 1 ${p1.join(" ")} L ${q0.join(" ")} A ${r0} ${r0} 0 ${big} 0 ${q1.join(" ")} Z`; }
        else d = `M ${cx0} ${cy0} L ${p0.join(" ")} A ${R} ${R} 0 ${big} 1 ${p1.join(" ")} Z`;
        if (v > 0) { const sl = paint(svgEl("path", { d, fill: colors(i), "fill-rule": "evenodd", class: "uislice", stroke: "rgba(3,14,20,0.55)", "stroke-width": 1.5 }), i, "f");
          sl.addEventListener("mouseenter", evt => showTip(evt, str(data[i][x]), [{ i, label: fmt(v) + unit, value: Math.round(v / total * 100) + "%" }])); sl.addEventListener("mousemove", moveTip); sl.addEventListener("mouseleave", hideTip);
          svg.appendChild(sl); }
        a = a1;
      });
      if (r0 && n.center != null) { const t = svgEl("text", { x: cx0, y: cy0 + 6, "text-anchor": "middle", class: "uichartcenter" }); t.textContent = str(n.center); svg.appendChild(t); }
      const legend = el("div", "uilegend col");
      data.forEach((d, i) => { const li = el("div", "uilegenditem"); const sw = paint(el("i"), i, "b"); li.appendChild(sw); li.appendChild(el("span", null, str(d[x]))); li.appendChild(el("span", "uimuted", fmt(vals[i]) + (n.unit || "") + " · " + Math.round(vals[i] / total * 100) + "%")); legend.appendChild(li); });
      const rowEl = el("div", "uipierow"); svg.style.width = H + "px"; svg.style.flex = "none"; rowEl.appendChild(svg); rowEl.appendChild(legend); wrap.appendChild(rowEl);
      return wrap;
    }
    const padL = 44, padR = 12, padT = 10, padB = 28, pw = W - padL - padR, ph = H - padT - padB;
    const stacked = !!n.stacked && (kind === "bar" || kind === "area");
    const ys = data.map(d => series.map(k => num(d[k], NaN)));
    let lo = 0, hi = 0;
    if (stacked) { data.forEach((_, i) => { const pos = ys[i].filter(v => v > 0).reduce((a, b) => a + b, 0), neg = ys[i].filter(v => v < 0).reduce((a, b) => a + b, 0); hi = Math.max(hi, pos); lo = Math.min(lo, neg); }); }
    else ys.forEach(r => r.forEach(v => { if (Number.isFinite(v)) { hi = Math.max(hi, v); lo = Math.min(lo, v); } }));
    if (n.ymin != null) lo = num(n.ymin, lo); if (n.ymax != null) hi = num(n.ymax, hi);
    if (hi === lo) hi = lo + 1;
    const ticks = niceTicks(lo, hi, 4); lo = Math.min(lo, ticks[0]); hi = Math.max(hi, ticks[ticks.length - 1]);
    const sy = v => padT + ph - (v - lo) / (hi - lo) * ph;
    const isScatter = kind === "scatter";
    const xnum = isScatter ? data.map(d => num(d[x], NaN)) : null;
    const xlo = isScatter ? Math.min(...xnum.filter(Number.isFinite)) : 0, xhi = isScatter ? Math.max(...xnum.filter(Number.isFinite)) : 1;
    const sx = i => isScatter ? padL + (xhi === xlo ? 0.5 : (xnum[i] - xlo) / (xhi - xlo)) * pw : padL + (data.length === 1 ? 0.5 : (kind === "bar" ? (i + 0.5) / data.length : i / (data.length - 1))) * pw;
    ticks.forEach(t => { svg.appendChild(svgEl("line", { x1: padL, x2: W - padR, y1: sy(t), y2: sy(t), class: "uigridline" })); const tx = svgEl("text", { x: padL - 6, y: sy(t) + 3.5, "text-anchor": "end", class: "uitick" }); tx.textContent = fmt(t); svg.appendChild(tx); });
    const labelEvery = Math.ceil(data.length / (isScatter ? 6 : 8));
    if (isScatter) { niceTicks(xlo, xhi, 6).forEach(t => { const px = padL + (xhi === xlo ? 0.5 : (t - xlo) / (xhi - xlo)) * pw; const tx = svgEl("text", { x: px, y: H - 8, "text-anchor": "middle", class: "uitick" }); tx.textContent = fmt(t); svg.appendChild(tx); }); }
    else data.forEach((d, i) => { if (i % labelEvery) return; const tx = svgEl("text", { x: sx(i), y: H - 8, "text-anchor": "middle", class: "uitick" }); tx.textContent = str(d[x]).slice(0, 14); svg.appendChild(tx); });
    if (lo < 0 && hi > 0) svg.appendChild(svgEl("line", { x1: padL, x2: W - padR, y1: sy(0), y2: sy(0), class: "uizero" }));
    if (kind === "bar") {
      const band = pw / data.length, inner = band * 0.72;
      data.forEach((_, i) => {
        if (stacked) {
          let up = 0, down = 0;
          series.forEach((k, s) => { const v = ys[i][s]; if (!Number.isFinite(v) || v === 0) return; const y0 = v > 0 ? up : down, y1 = y0 + v; if (v > 0) up = y1; else down = y1; const rc = paint(svgEl("rect", { x: sx(i) - inner / 2, y: Math.min(sy(y0), sy(y1)), width: inner, height: Math.max(1, Math.abs(sy(y0) - sy(y1))), fill: colors(s), rx: 3, class: "uibar" }), s, "f"); (bars[i] = bars[i] || []).push(rc); svg.appendChild(rc); });
        } else {
          const bw = inner / series.length;
          series.forEach((k, s) => { const v = ys[i][s]; if (!Number.isFinite(v)) return; const y0 = sy(Math.max(0, Math.min(v, 0))), y1 = sy(v); const ci = perCategory ? i : s; const rc = paint(svgEl("rect", { x: sx(i) - inner / 2 + s * bw, y: Math.min(y0, y1), width: Math.max(1, bw - 2), height: Math.max(1, Math.abs(y1 - y0)), fill: colors(ci), rx: 3, class: "uibar" }), ci, "f"); (bars[i] = bars[i] || []).push(rc); svg.appendChild(rc); });
        }
      });
    } else if (isScatter) {
      series.forEach((k, s) => data.forEach((_, i) => { const v = ys[i][s]; if (!Number.isFinite(v) || !Number.isFinite(xnum[i])) return; const c = paint(svgEl("circle", { cx: sx(i), cy: sy(v), r: 4.5, fill: colors(s), class: "uidot2" }), s, "f");
        c.addEventListener("mouseenter", evt => showTip(evt, k, [{ i: s, label: str(data[i][x]), value: fmt(v) + unit }])); c.addEventListener("mousemove", moveTip); c.addEventListener("mouseleave", hideTip); svg.appendChild(c); }));
    } else {
      const base = series.map(() => data.map(() => 0));
      series.forEach((k, s) => {
        const pts = [];
        data.forEach((_, i) => { let v = ys[i][s]; if (!Number.isFinite(v)) return; let b = 0; if (stacked) { b = base[s][i]; v = b + v; if (s + 1 < series.length) base[s + 1][i] = v; } pts.push([sx(i), sy(v), sy(b)]); });
        if (pts.length < 1) return;
        const line = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
        if (kind === "area") { const back = pts.slice().reverse().map(p => "L" + p[0].toFixed(1) + " " + (stacked ? p[2] : sy(Math.max(lo, 0))).toFixed(1)).join(" "); svg.appendChild(paint(svgEl("path", { d: line + " " + back + " Z", fill: colors(s), "fill-opacity": stacked ? 0.55 : 0.18, stroke: "none" }), s, "f")); }
        svg.appendChild(paint(svgEl("path", { d: line, fill: "none", stroke: colors(s), "stroke-width": 2.2, "stroke-linejoin": "round", "stroke-linecap": "round" }), s, "s"));
        if (n.dots !== 0 && pts.length <= 40) pts.forEach(p => svg.appendChild(paint(svgEl("circle", { cx: p[0], cy: p[1], r: 3, fill: colors(s) }), s, "f")));
      });
    }
    if (!isScatter) {   // a hit band a column: a dashed guide, the column's bars lit, and the tip with the x and every series' value
      const guide = svgEl("line", { x1: 0, x2: 0, y1: padT, y2: padT + ph, class: "uiguide" }); svg.appendChild(guide);
      const cool = () => { guide.classList.remove("on"); svg.querySelectorAll(".uibar.hot").forEach(b => b.classList.remove("hot")); hideTip(); };
      data.forEach((d, i) => {
        const x0 = i === 0 ? padL : (sx(i - 1) + sx(i)) / 2, x1 = i === data.length - 1 ? W - padR : (sx(i) + sx(i + 1)) / 2;
        const hit = svgEl("rect", { x: x0, y: padT, width: Math.max(1, x1 - x0), height: ph, fill: "transparent", class: "uihit" });
        hit.addEventListener("mouseenter", evt => {
          guide.setAttribute("x1", sx(i)); guide.setAttribute("x2", sx(i)); guide.classList.add("on");
          svg.querySelectorAll(".uibar.hot").forEach(b => b.classList.remove("hot")); (bars[i] || []).forEach(b => b.classList.add("hot"));
          const rows = series.map((k, s) => [k, s]).filter(([, s]) => Number.isFinite(ys[i][s])).map(([k, s]) => ({ i: perCategory ? i : s, label: series.length > 1 ? k : "", value: fmt(ys[i][s]) + unit }));
          showTip(evt, str(d[x]), rows);
        });
        hit.addEventListener("mousemove", moveTip); hit.addEventListener("mouseleave", cool);
        svg.appendChild(hit);
      });
    }
    wrap.appendChild(svg);
    if (series.length > 1 || n.legend) { const legend = el("div", "uilegend"); series.forEach((k, s) => { const li = el("div", "uilegenditem"); const sw = paint(el("i"), s, "b"); li.appendChild(sw); li.appendChild(el("span", null, k)); legend.appendChild(li); }); wrap.appendChild(legend); }
    return wrap;
  }
  function sparkSvg(arr, tn) {
    const vals = arr.map(v => num(v, NaN)).filter(Number.isFinite).slice(-120); if (vals.length < 2) return el("span");
    const lo = Math.min(...vals), hi = Math.max(...vals), W = 120, H = 30;
    const pts = vals.map((v, i) => [i / (vals.length - 1) * (W - 4) + 2, hi === lo ? H / 2 : H - 3 - (v - lo) / (hi - lo) * (H - 6)]);
    const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, class: "uispark" + (tn ? " tone-" + tone(tn) : "") });
    svg.appendChild(svgEl("path", { d: pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" "), fill: "none", "stroke-width": 1.8, class: "uisparkline" }));
    const last = pts[pts.length - 1]; svg.appendChild(svgEl("circle", { cx: last[0], cy: last[1], r: 2.4, class: "uisparkdot" }));
    return svg;
  }
  function sparkline(n) { const w = el("div", "uisparkwrap"); if (n.label) w.appendChild(el("div", "uilabel", n.label)); w.appendChild(sparkSvg(Array.isArray(n.data) ? n.data : [], n.tone)); return w; }
  function rating(n) {
    const max = clamp(Math.round(num(n.max, 5)), 1, 10), v = clamp(num(n.value, 0), 0, max);
    const d = el("div", "uirating"); if (n.label) d.appendChild(el("span", "uimuted", n.label + " "));
    const stars = el("span", "uistars"); const back = el("span", "uistarsback", "★".repeat(max)); const fill = el("span", "uistarsfill", "★".repeat(max)); fill.style.width = (v / max * 100).toFixed(1) + "%"; stars.appendChild(back); stars.appendChild(fill); d.appendChild(stars);
    d.appendChild(el("span", "uimuted", " " + fmt(v) + "/" + max)); return d;
  }
  function countdown(n) {
    const to = Date.parse(str(n.to)); const d = el("div", "uicountdown"); if (n.label) d.appendChild(el("div", "uilabel", n.label));
    const v = el("div", "uicountvalue"); d.appendChild(v);
    if (!Number.isFinite(to)) { v.textContent = "when?"; return d; }
    const paint = () => {
      if (!d.isConnected) { clearInterval(d._timer); return; }
      let s = Math.round((to - Date.now()) / 1000); if (s <= 0) { v.textContent = str(n.done || "now"); d.classList.add("done"); return; }
      const dd = Math.floor(s / 86400); s -= dd * 86400; const hh = Math.floor(s / 3600); s -= hh * 3600; const mm = Math.floor(s / 60); s -= mm * 60;
      v.textContent = (dd ? dd + "d " : "") + String(hh).padStart(2, "0") + ":" + String(mm).padStart(2, "0") + ":" + String(s).padStart(2, "0");
    };
    paint(); d._timer = setInterval(paint, 1000); return d;
  }
  function clock(n) {
    const d = el("div", "uiclock"); if (n.label) d.appendChild(el("div", "uilabel", n.label)); const v = el("div", "uiclockvalue"); d.appendChild(v); const sub = el("div", "uimuted"); d.appendChild(sub);
    let fmtT, fmtD;
    try { fmtT = new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit", second: n.seconds ? "2-digit" : undefined, hour12: !!n.h12, timeZone: n.tz || undefined }); fmtD = new Intl.DateTimeFormat(undefined, { weekday: "long", day: "numeric", month: "long", timeZone: n.tz || undefined }); }
    catch (e) { v.textContent = "unknown time zone"; return d; }
    const paint = () => { if (!d.isConnected) { clearInterval(d._timer); return; } const now = new Date(); v.textContent = fmtT.format(now); sub.textContent = fmtD.format(now) + (n.tz ? " · " + n.tz : ""); };
    paint(); d._timer = setInterval(paint, n.seconds ? 1000 : 10000); return d;
  }
  function calendar(n) {
    const m = /^(\d{4})-(\d{2})$/.exec(str(n.month)); const now = new Date();
    const y = m ? +m[1] : now.getFullYear(), mo = m ? +m[2] - 1 : now.getMonth();
    const first = new Date(y, mo, 1), days = new Date(y, mo + 1, 0).getDate(), lead = (first.getDay() + 6) % 7;   // weeks start on Monday
    const marks = {}; (Array.isArray(n.marks) ? n.marks : []).slice(0, 200).forEach(mk => { if (!mk) return; const dt = typeof mk === "string" ? mk : mk.date; const mm = /^(\d{4})-(\d{2})-(\d{2})/.exec(str(dt)); if (mm && +mm[1] === y && +mm[2] - 1 === mo) (marks[+mm[3]] = marks[+mm[3]] || []).push(typeof mk === "string" ? { label: "" } : mk); });
    const root = el("div", "uical"); root.appendChild(el("div", "uicaltitle", n.title || first.toLocaleDateString(undefined, { month: "long", year: "numeric" })));
    const g = el("div", "uicalgrid"); ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"].forEach(w => g.appendChild(el("div", "uicaldow", w)));
    for (let i = 0; i < lead; i++) g.appendChild(el("div", "uicalday empty"));
    for (let d = 1; d <= days; d++) {
      const c = el("div", "uicalday" + (now.getFullYear() === y && now.getMonth() === mo && now.getDate() === d ? " today" : "") + (marks[d] ? " marked" : ""));
      c.appendChild(el("span", "uicalnum", d));
      if (marks[d]) { const dots = el("div", "uicaldots"); marks[d].slice(0, 3).forEach(mk => { const dot = el("i", "tone-" + tone(mk.tone)); dots.appendChild(dot); }); c.appendChild(dots); c.title = marks[d].map(mk => mk.label || "").filter(Boolean).join(", "); }
      g.appendChild(c);
    }
    root.appendChild(g);
    const labelled = Object.keys(marks).map(Number).sort((a, b) => a - b).flatMap(d => marks[d].filter(mk => mk.label).map(mk => ({ d, mk })));
    if (labelled.length) { const ul = el("div", "uicallist"); labelled.slice(0, 12).forEach(({ d, mk }) => { const r = el("div", "uicalitem"); const dot = el("i", "tone-" + tone(mk.tone)); r.appendChild(dot); r.appendChild(el("span", "uimuted", String(d).padStart(2, "0"))); r.appendChild(el("span", null, mk.label)); ul.appendChild(r); }); root.appendChild(ul); }
    return root;
  }
  function figure(it, opts) {
    const u = safeUrl(it.url || it.src); if (!u) return null;
    const f = el("figure", "uifigure"); const box = el("div", "uiimgbox"); const ar = aspect(it.aspect || (opts && opts.aspect));
    if (ar) box.style.aspectRatio = ar; else box.classList.add("natural");
    const im = el("img"); im.src = u; im.alt = str(it.title || it.caption || ""); im.loading = "lazy"; im.decoding = "async";
    im.style.objectFit = (it.fit || (opts && opts.fit)) === "contain" ? "contain" : "cover"; if (it.radius != null) box.style.borderRadius = clamp(num(it.radius, 10), 0, 60) + "px";
    box.appendChild(im);
    if (opts && opts.number) box.appendChild(el("span", "uinum", "#" + opts.number));
    f.appendChild(box);
    const cap = it.caption || it.title, credit = it.credit || (it.source ? it.source + (it.author ? " · " + it.author : "") : "");
    if (cap || credit) { const fc = el("figcaption"); if (cap) fc.appendChild(el("span", null, cap)); if (credit) fc.appendChild(el("span", "uimuted", (cap ? " · " : "") + credit)); f.appendChild(fc); }
    return f;
  }
  function image(n) { return figure(n, {}); }
  function gallery(n) {
    const items = (Array.isArray(n.items) ? n.items : []).map(it => typeof it === "string" ? { url: it } : it).filter(it => it && safeUrl(it.url || it.src)).slice(0, 60);
    if (!items.length) return null;
    const auto = items.length === 1 ? 1 : items.length === 2 ? 2 : items.length <= 4 ? 2 : items.length <= 9 ? 3 : 4;
    const cols = clamp(Math.round(num(n.cols, auto)), 1, 6);
    const g = el("div", "uigallery"); g.style.gridTemplateColumns = `repeat(${cols}, minmax(0, 1fr))`;
    items.forEach((it, i) => { const f = figure(it, { aspect: n.aspect || "4/3", fit: n.fit, number: n.numbered ? i + 1 : 0 }); if (f) g.appendChild(f); });
    return g;
  }
  function video(n) {
    const u = safeUrl(n.src || n.url); if (!u) return null;
    const box = el("div", "uimedia"); box.style.aspectRatio = aspect(n.aspect) || "16 / 9";
    const v = el("video"); v.src = u; v.playsInline = true; v.preload = "metadata";
    v.loop = n.loop !== 0 && n.loop !== false; v.muted = n.muted !== 0 && n.muted !== false; v.autoplay = n.autoplay !== 0 && n.autoplay !== false && v.muted;
    v.controls = n.controls !== 0 && n.controls !== false;   // a mouse can use them const poster = safeUrl(n.poster); if (poster) v.poster = poster; v.style.objectFit = n.fit === "contain" ? "contain" : "cover";
    if (n.id) v.dataset.media = str(n.id);
    box.appendChild(v); if (n.autoplay !== 0 && n.autoplay !== false) v.play().catch(() => {});
    return withCaption(box, n);
  }
  function withCaption(box, n) { if (!n.caption && !n.title) return box; const f = el("figure", "uifigure"); f.appendChild(box); f.appendChild(el("figcaption", null, n.caption || n.title)); return f; }
  const ytId = n => { const id = str(n.id); if (/^[\w-]{6,}$/.test(id)) return id; let u; try { u = new URL(str(n.url)); } catch (e) { return ""; } const h = u.hostname.replace(/^www\./, ""); if (!(h === "youtu.be" || h.endsWith("youtube.com") || h.endsWith("youtube-nocookie.com"))) return ""; const p = u.pathname; const v = h === "youtu.be" ? p.slice(1).split("/")[0] : /^\/(embed|shorts|live)\//.test(p) ? p.split("/")[2] : u.searchParams.get("v") || ""; return /^[\w-]{6,}$/.test(v) ? v : ""; };
  function youtube(n) {
    const id = ytId(n); if (!id) return el("div", "uimuted", "that is not a YouTube link");
    const box = el("div", "uimedia"); box.style.aspectRatio = aspect(n.aspect) || "16 / 9";
    const f = el("iframe", "uiyt"); const start = clamp(Math.round(num(n.start, 0)), 0, 86400);
    const auto = n.autoplay !== 0 && n.autoplay !== false; const mute = n.mute === 0 || n.mute === false ? 0 : 1;
    f.src = `https://www.youtube-nocookie.com/embed/${id}?rel=0&modestbranding=1&playsinline=1&enablejsapi=1&autoplay=${auto ? 1 : 0}&mute=${auto ? mute : 0}${start ? `&start=${start}` : ""}${n.loop ? `&loop=1&playlist=${id}` : ""}`;
    f.allow = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; fullscreen"; f.referrerPolicy = "strict-origin-when-cross-origin"; f.loading = "lazy"; f.title = str(n.title || "YouTube");
    if (n.name) f.dataset.media = str(n.name);
    box.appendChild(f); return withCaption(box, n);
  }
  function vimeo(n) {
    let id = str(n.id); if (!/^\d{5,}$/.test(id)) { const m = /vimeo\.com\/(?:video\/)?(\d{5,})/.exec(str(n.url)); id = m ? m[1] : ""; }
    if (!id) return el("div", "uimuted", "that is not a Vimeo link");
    const box = el("div", "uimedia"); box.style.aspectRatio = aspect(n.aspect) || "16 / 9";
    const f = el("iframe", "uivimeo"); const auto = n.autoplay !== 0 && n.autoplay !== false;
    f.src = `https://player.vimeo.com/video/${id}?autoplay=${auto ? 1 : 0}&muted=${auto ? 1 : 0}&loop=${n.loop ? 1 : 0}&title=0&byline=0&portrait=0&api=1`;
    f.allow = "autoplay; fullscreen; picture-in-picture"; f.referrerPolicy = "strict-origin-when-cross-origin"; f.loading = "lazy"; f.title = str(n.title || "Vimeo"); if (n.name) f.dataset.media = str(n.name);
    box.appendChild(f); return withCaption(box, n);
  }
  function audio(n) {
    const u = safeUrl(n.src || n.url); if (!u) return null;
    const d = el("div", "uiaudio"); if (n.title) d.appendChild(el("div", "uilabel", n.title)); const a = el("audio"); a.src = u; a.controls = true; a.preload = "metadata"; a.loop = !!n.loop; if (n.id) a.dataset.media = str(n.id); d.appendChild(a); return d;
  }
  function embed(n) {
    const u = safeUrl(n.url || n.src); if (!u || !/^https:/.test(u)) return el("div", "uimuted", "that link cannot be embedded (https only)");
    const y = ytId({ url: u }); if (y) return youtube({ ...n, url: u });
    if (/vimeo\.com\/(video\/)?\d{5,}/.test(u)) return vimeo({ ...n, url: u });
    if (/\.(mp4|webm|mov|m4v)(\?|$)/i.test(u)) return video({ ...n, src: u });
    if (/\.(mp3|m4a|wav|ogg|oga|flac)(\?|$)/i.test(u)) return audio({ ...n, src: u });
    const box = el("div", "uimedia uiembed"); const ar = aspect(n.aspect); if (ar) box.style.aspectRatio = ar; else box.style.height = clamp(num(n.height, 360), 120, 1200) + "px";
    const f = el("iframe"); f.src = u; f.setAttribute("sandbox", "allow-scripts allow-same-origin allow-popups allow-presentation allow-forms"); f.referrerPolicy = "strict-origin-when-cross-origin"; f.loading = "lazy"; f.title = str(n.title || host(u)); f.allow = "fullscreen";
    box.appendChild(f); const w = withCaption(box, n); if (w === box) { const fig = el("figure", "uifigure"); fig.appendChild(box); fig.appendChild(el("figcaption", "uimuted", host(u))); return fig; } return w;
  }
  function map(n) {
    const lat = num(n.lat, NaN), lon = num(n.lon ?? n.lng, NaN);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) { const u = safeUrl(n.url); return u ? embed({ url: u, aspect: n.aspect || "4/3", title: n.label || n.title }) : el("div", "uimuted", "a map needs lat and lon"); }
    const zoom = clamp(Math.round(num(n.zoom, 14)), 2, 19);
    const dLon = 360 / Math.pow(2, zoom) * 1.9, dLat = dLon * Math.cos(lat * Math.PI / 180) * 0.75;
    const bbox = [lon - dLon / 2, lat - dLat / 2, lon + dLon / 2, lat + dLat / 2].map(v => v.toFixed(5)).join(",");
    const box = el("div", "uimedia uimap"); box.style.aspectRatio = aspect(n.aspect) || "4 / 3";
    const f = el("iframe"); f.src = `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${lat.toFixed(5)},${lon.toFixed(5)}`; f.referrerPolicy = "strict-origin-when-cross-origin"; f.loading = "lazy"; f.title = str(n.label || n.title || "map"); f.setAttribute("sandbox", "allow-scripts allow-same-origin");
    box.appendChild(f);
    const fig = el("figure", "uifigure"); fig.appendChild(box); fig.appendChild(el("figcaption", null, (n.label || n.title || "") + (n.label || n.title ? " · " : "") + lat.toFixed(4) + ", " + lon.toFixed(4) + " · OpenStreetMap")); return fig;
  }
  function avatarEl(it, size) {
    const a = el("span", "uiavatar" + (it.tone ? " tone-" + tone(it.tone) : "")); a.style.width = a.style.height = size + "px"; a.style.fontSize = Math.round(size * 0.38) + "px";
    const u = safeUrl(it.url || it.src); if (u) { const im = el("img"); im.src = u; im.alt = str(it.name || ""); a.appendChild(im); }
    else a.textContent = str(it.initials || str(it.name).split(/\s+/).map(w => w[0]).join("").slice(0, 2).toUpperCase() || "?");
    a.title = str(it.name || ""); return a;
  }
  function avatar(n) {
    const size = clamp(num(n.size, 44), 20, 160); const d = el("div", "uiavatarrow"); d.appendChild(avatarEl(n, size));
    if (n.name || n.sub) { const t = el("div"); if (n.name) t.appendChild(el("div", "uiavatarname", n.name)); if (n.sub) t.appendChild(el("div", "uimuted", n.sub)); d.appendChild(t); }
    return d;
  }
  function avatars(n) {
    const items = (Array.isArray(n.items) ? n.items : []).map(it => typeof it === "string" ? { name: it } : it).filter(Boolean); const max = clamp(Math.round(num(n.max, 6)), 1, 20);
    const d = el("div", "uiavatars"); const size = clamp(num(n.size, 36), 20, 120);
    items.slice(0, max).forEach(it => d.appendChild(avatarEl(it, size)));
    if (items.length > max) { const more = el("span", "uiavatar more", "+" + (items.length - max)); more.style.width = more.style.height = size + "px"; more.style.fontSize = Math.round(size * 0.34) + "px"; d.appendChild(more); }
    if (n.label) d.appendChild(el("span", "uimuted", n.label)); return d;
  }
  function skeleton(n) { const d = el("div", "uiskeleton"); const lines = clamp(Math.round(num(n.lines, 3)), 1, 12); for (let i = 0; i < lines; i++) { const l = el("div", "uibone"); l.style.width = (i === lines - 1 && lines > 1 ? 60 : 100 - (i % 3) * 8) + "%"; d.appendChild(l); } return d; }
  function button(n, cx, path) {
    const key = keyOf(n, path); const b = el("span", "uibtn tone-" + tone(n.tone) + (n.primary ? " primary" : ""), n.label || n.text || "OK");
    b.dataset.act = `btn:${key}`; b.dataset.action = str(n.action || n.label || key); b.dataset.label = str(n.label || n.text || "OK"); return b;
  }
  function choice(n, cx, path) {
    const opts = (Array.isArray(n.options) ? n.options : []).map(o => typeof o === "object" && o ? o : { label: str(o), value: str(o) }).slice(0, 12);
    if (!opts.length) return null;
    const key = keyOf(n, path); const root = el("div", "uichoice"); root.dataset.key = key; root.dataset.kind = "choice"; root.dataset.action = str(n.action || key);
    if (n.label) root.appendChild(el("div", "uilabel", n.label));
    const row = el("div", "uichoicerow");
    opts.forEach((o, i) => { const c = el("span", "uichip", o.label ?? o.value); c.dataset.act = `choice:${key}:${i}`; c.dataset.value = str(o.value ?? o.label); c.dataset.label = str(o.label ?? o.value); row.appendChild(c); });
    root.appendChild(row);
    const sel = cx.state[key] != null ? num(cx.state[key], -1) : opts.findIndex(o => n.value != null && str(o.value ?? o.label) === str(n.value));
    setChoice(root, sel); return root;
  }
  function setChoice(root, i) { root.querySelectorAll(":scope > .uichoicerow > .uichip").forEach((c, k) => c.classList.toggle("on", k === i)); root.dataset.i = i; }

  const RENDER = { stack, row, grid, columns, card, group, tabs, accordion, slideshow, carousel: slideshow, steps, timeline, divider, spacer, aspect: aspectBox, hero,
    heading, text: textNode, md, markdown: md, quote, code, kbd, badge, tags, callout, link, stat, progress, gauge, meter: gauge, kv, list, table, chart, sparkline, rating,
    countdown, clock, calendar, image, gallery, video, youtube, vimeo, audio, embed, web: embed, map, avatar, avatars, skeleton, button, choice, empty: () => null };

  function render(node, cx, path, depth) {
    cx = cx || { state: {}, live: false }; if (!cx.state) cx.state = {}; path = path || "0"; depth = depth || 0;
    if (!node || typeof node !== "object" || depth > MAX_DEPTH) return null;
    const fn = RENDER[node.type];
    if (!fn) return null;
    try { const e = fn(node, cx, path, depth); if (e && node.type !== "empty") e.classList.add("ui-" + node.type); return e; }
    catch (e) { console.warn("[board-render]", node.type, e); return null; }
  }
  function count(node) { if (!node || typeof node !== "object") return 0; let n = RENDER[node.type] ? 1 : 0; (node.children || []).forEach(c => n += count(c)); if (node.child) n += count(node.child); (Array.isArray(node.items) ? node.items : []).forEach(i => { if (i && typeof i === "object" && i.child) n += count(i.child); }); return n; }

  // ---- state in, state out: the interactive components follow one flat map { key: value }
  function applyState(root, state) {
    state = state || {};
    root.querySelectorAll("[data-kind]").forEach(c => {
      const k = c.dataset.key; if (!(k in state)) return;
      if (c.dataset.kind === "tabs") setTabs(c, state[k]);
      else if (c.dataset.kind === "slides") setSlide(c, state[k]);
      else if (c.dataset.kind === "acc") setAcc(c, state[k]);
      else if (c.dataset.kind === "choice") setChoice(c, num(state[k], -1));
      else if (c.dataset.kind === "checks") setChecks(c, state[k]);
    });
  }
  function act(root, state, actStr) {
    const [kind, key, arg] = str(actStr).split(":"); state = state || {};
    const comp = key ? Array.from(root.querySelectorAll("[data-key]")).find(c => c.dataset.key === key) : null;
    if (kind === "tab" && comp) { const i = clamp(num(arg, 0), 0, num(comp.dataset.n, 1) - 1); state[key] = i; setTabs(comp, i); return { changed: true }; }
    if (kind === "slide" && comp) { const n = num(comp.dataset.n, 1), cur = num(comp.dataset.i, 0); const i = arg === "next" ? (cur + 1) % n : arg === "prev" ? (cur - 1 + n) % n : clamp(num(arg, 0), 0, n - 1); state[key] = i; setSlide(comp, i); return { changed: true }; }
    if (kind === "acc" && comp) { const i = num(arg, 0); const open = new Set(Array.from(comp.querySelectorAll(":scope > .uiaccitem")).map((it, k) => it.classList.contains("open") ? k : -1).filter(k => k >= 0)); if (open.has(i)) open.delete(i); else { if (comp.dataset.single) open.clear(); open.add(i); } state[key] = Array.from(open).sort((a, b) => a - b); setAcc(comp, state[key]); return { changed: true }; }
    if (kind === "choice" && comp) { const i = num(arg, -1); state[key] = i; setChoice(comp, i); const chip = comp.querySelectorAll(":scope > .uichoicerow > .uichip")[i]; return { changed: true, event: { kind: "choice", action: comp.dataset.action, value: chip ? chip.dataset.value : "", label: chip ? chip.dataset.label : "" } }; }
    if (kind === "chk") {
      const li = Array.from(root.querySelectorAll("li.uicheck[data-act]")).find(x => x.dataset.act === actStr); if (!li) return { changed: false };
      const done = !li.classList.contains("done"); li.classList.toggle("done", done); li.classList.toggle("todo", !done);
      if (comp && comp.dataset.kind === "checks") state[key] = Array.from(comp.querySelectorAll(":scope > li.uicheck")).map((x, k) => x.classList.contains("done") ? k : -1).filter(k => k >= 0);
      const label = Array.from(li.childNodes).filter(x => x.nodeType === 3 || (x.nodeType === 1 && !x.classList.contains("uimuted"))).map(x => x.textContent).join("").trim();
      return { changed: true, event: { kind: "check", action: comp && comp.dataset.action ? comp.dataset.action : key, label, value: done ? "done" : "undone" } };
    }
    if (kind === "btn") { const b = Array.from(root.querySelectorAll("[data-act]")).find(x => x.dataset.act === actStr); return { changed: false, event: { kind: "button", action: b ? b.dataset.action : key, label: b ? b.dataset.label : key } }; }
    return { changed: false };
  }
  function step(root, state, op, i, id) {
    const comps = Array.from(root.querySelectorAll("[data-kind]")).filter(c => c.dataset.kind === "slides" || c.dataset.kind === "tabs");
    const comp = id ? comps.find(c => c.dataset.key === str(id)) : (comps.find(c => c.dataset.kind === "slides") || comps[0]);
    if (!comp) return false;
    const n = num(comp.dataset.n, 1), cur = num(comp.dataset.i, 0);
    const to = op === "next" ? (cur + 1) % n : op === "prev" ? (cur - 1 + n) % n : clamp(num(i, 0), 0, n - 1);
    state[comp.dataset.key] = to; if (comp.dataset.kind === "slides") setSlide(comp, to); else setTabs(comp, to); return true;
  }
  function media(root, op, arg, id) {
    const all = Array.from(root.querySelectorAll("video, audio, iframe.uiyt, iframe.uivimeo"));
    const m = id ? all.find(x => x.dataset.media === str(id)) : all[0]; if (!m) return false;
    const yt = m.classList && m.classList.contains("uiyt"), vm = m.classList && m.classList.contains("uivimeo");
    const post = (msg, origin) => { try { m.contentWindow.postMessage(typeof msg === "string" ? msg : JSON.stringify(msg), origin); } catch (e) {} };
    if (yt) { const f = { play: "playVideo", pause: "pauseVideo", mute: "mute", unmute: "unMute", seek: "seekTo", toggle: "playVideo" }[op]; if (!f) return false; post({ event: "listening", id: 1 }, "https://www.youtube-nocookie.com"); post({ event: "command", func: f, args: op === "seek" ? [num(arg, 0), true] : [] }, "https://www.youtube-nocookie.com"); return true; }
    if (vm) { const f = { play: "play", pause: "pause", mute: "setMuted", unmute: "setMuted", seek: "setCurrentTime", toggle: "play" }[op]; if (!f) return false; post({ method: f, value: op === "mute" ? true : op === "unmute" ? false : op === "seek" ? num(arg, 0) : undefined }, "https://player.vimeo.com"); return true; }
    if (op === "play") { m.play().catch(() => {}); return true; }
    if (op === "pause") { m.pause(); return true; }
    if (op === "toggle") { if (m.paused) m.play().catch(() => {}); else m.pause(); return true; }
    if (op === "mute") { m.muted = true; return true; }
    if (op === "unmute") { m.muted = false; m.play().catch(() => {}); return true; }
    if (op === "seek") { m.currentTime = Math.max(0, num(arg, 0)); return true; }
    return false;
  }

  window.__boardRender = { render, applyState, act, step, media, count, inline, markdown, PALETTE, COLS, TYPES: Object.keys(RENDER) };
})();
