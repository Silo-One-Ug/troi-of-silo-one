// board.js — Silo One's additions to the hands board (injected by patch-board.sh; the upstream files stay as they are).
//   1. The ring, drawn Silo One's way: a gyroscope of two orbits around a breathing core, each with its satellite
//      (the brand's orbit and the one that rides it), a band of ticks that turns, the name and the state. It turns
//      with the agent's state (quicker when thinking, ripples inward when listening) and pulses on its voice.
//   2. A Hands button in the corner: the camera and hand tracking on or off, here and on the console's switch.
(function () {
  const TAU = Math.PI * 2;
  const STATUS = { idle: "IDLE", listening: "LISTENING", thinking: "THINKING", speaking: "SPEAKING" };
  const FONT = 'Sora, "SF Pro Display", -apple-system, Helvetica, sans-serif';

  window.__ringDraw = function (sc) {
    const R = window.__RING; if (!R) return;
    const d = R.data || {}, st = d.state || "idle";
    const amp = st === "speaking" ? (window.__ringAmp ? window.__ringAmp() : 0) : (R.amp *= 0.9);
    const t = Date.now() / 1000;
    const base = R.COLS[st] || R.COLS.idle, tint = R.MOODT[d.mood];
    const c = tint ? base.map((v, i) => Math.round(v * 0.35 + tint[i] * 0.65)) : base;
    const col = a => `rgba(${c[0]},${c[1]},${c[2]},${a})`;
    const gold = a => `rgba(244,174,69,${a})`;                       // the brand's orbit gold (brand/make_logo.py)
    const x = sc.ctx; if (window.__ensureRingRes) window.__ensureRingRes(sc);
    x.setTransform(sc.RES, 0, 0, sc.RES, 0, 0); x.clearRect(0, 0, 440, 440);
    x.save(); x.translate(220, 220); x.lineCap = "round";
    const tap = Math.exp(-Math.max(0, t - (sc.tapT || 0)) * 4);
    const breath = 0.5 + 0.5 * Math.sin(t * 1.15);
    const speak = st === "speaking" ? amp : 0;
    const pace = st === "thinking" ? 2.1 : st === "listening" ? 0.6 : 1;
    // 1. the band: a thin outer ring and sixty ticks that turn, slowly
    x.shadowColor = col(0.9); x.shadowBlur = 10 + speak * 22 + tap * 10;
    x.strokeStyle = col(0.8 + speak * 0.2); x.lineWidth = 1.5 + speak * 1.5;
    x.beginPath(); x.arc(0, 0, 196, 0, TAU); x.stroke(); x.shadowBlur = 0;
    const rot = t * 0.05 * pace;
    for (let i = 0; i < 60; i++) {
      const a = rot + i / 60 * TAU, big = i % 5 === 0;
      x.strokeStyle = col(big ? 0.7 : 0.26); x.lineWidth = big ? 1.8 : 1;
      x.beginPath(); x.moveTo(Math.cos(a) * (big ? 180 : 185), Math.sin(a) * (big ? 180 : 185)); x.lineTo(Math.cos(a) * 190, Math.sin(a) * 190); x.stroke();
    }
    // 2. the gyroscope: two orbits, tilting and turning, each with its satellite; the one behind the core is dimmer
    const orbit = (rx, squash, turn, phase, colour, w, sat) => {
      x.save(); x.rotate(turn);
      x.beginPath(); x.ellipse(0, 0, rx, rx * squash, 0, 0, TAU);
      x.strokeStyle = colour(0.5); x.lineWidth = w; x.shadowColor = colour(0.8); x.shadowBlur = 8; x.stroke();
      const sx = Math.cos(phase) * rx, sy = Math.sin(phase) * rx * squash, front = Math.sin(phase) > 0;
      x.shadowBlur = 16; x.fillStyle = colour(front ? 1 : 0.5);
      x.beginPath(); x.arc(sx, sy, front ? sat : sat * 0.8, 0, TAU); x.fill();
      x.restore();
    };
    const sq1 = 0.2 + 0.5 * Math.abs(Math.sin(t * 0.19)), sq2 = 0.2 + 0.5 * Math.abs(Math.cos(t * 0.15 + 1));
    orbit(160, sq1, t * 0.10 * pace, t * 0.85 * pace, gold, 1.4, 4.5);
    orbit(150, sq2, -t * 0.08 * pace + 1.2, -t * 0.65 * pace + 2, col, 1.2, 3.5);
    // 3. the state, in motion
    if (st === "listening") {                                         // ripples drawn inward: receiving
      for (let k = 0; k < 3; k++) { const p = (t * 0.7 + k / 3) % 1; x.globalAlpha = (1 - p) * p * 1.8; x.strokeStyle = col(0.9); x.lineWidth = 1.5; x.beginPath(); x.arc(0, 0, 190 - p * 70, 0, TAU); x.stroke(); }
      x.globalAlpha = 1;
    } else if (st === "thinking") {                                    // a comet running the band
      const a0 = t * 2.6;
      for (let i = 0; i < 9; i++) { x.globalAlpha = 0.6 * (1 - i / 9); x.strokeStyle = col(0.95); x.lineWidth = 5; x.shadowColor = col(0.9); x.shadowBlur = 10; x.beginPath(); x.arc(0, 0, 196, a0 - (i + 1) * 0.09, a0 - i * 0.09); x.stroke(); }
      x.globalAlpha = 1; x.shadowBlur = 0;
    }
    // 4. the core: a glow that breathes, brighter on the voice, under a thin glass rim
    const g = x.createRadialGradient(0, 0, 10, 0, 0, 118);
    g.addColorStop(0, col(0.16 + 0.10 * breath + 0.35 * speak)); g.addColorStop(0.6, col(0.05 + 0.04 * breath + 0.15 * speak)); g.addColorStop(1, col(0));
    x.fillStyle = g; x.beginPath(); x.arc(0, 0, 118, 0, TAU); x.fill();
    x.shadowColor = col(0.9); x.shadowBlur = 8 + speak * 20; x.strokeStyle = col(0.7 + speak * 0.3); x.lineWidth = 1.5 + speak * 2;
    x.beginPath(); x.arc(0, 0, 118, 0, TAU); x.stroke(); x.shadowBlur = 0;
    // 5. the name and the state
    const cfg = window.__CFG || {}; const nm = (cfg.name || "ASSISTANT").toUpperCase();
    const fpx = nm.length <= 8 ? 24 : nm.length <= 14 ? 17 : 13, gap = Math.round(fpx * 0.3);
    x.textAlign = "center"; x.textBaseline = "middle"; x.shadowColor = "rgba(2,10,10,0.85)"; x.shadowBlur = 6;
    x.fillStyle = `rgba(240,250,250,${0.92 + speak * 0.08})`; x.font = `600 ${fpx}px ${FONT}`;
    try { x.letterSpacing = gap + "px"; } catch (e) {}
    x.fillText(nm, gap / 2, -10);                                      // the spacing trails the last letter: nudge to centre
    x.font = `500 11px ${FONT}`; try { x.letterSpacing = "4px"; } catch (e) {}
    x.fillStyle = col(0.95); x.globalAlpha = 0.7 + 0.3 * breath;
    x.fillText(STATUS[st] || "IDLE", 2, 18);
    x.globalAlpha = 1; x.shadowBlur = 0; try { x.letterSpacing = "0px"; } catch (e) {}
    x.restore();
  };

  // the Hands button: the camera by request, here as on the console; the console's switch follows
  if (new URLSearchParams(location.search).get("role") === "render") return;
  // the opening screen: the agent's name from the board's own config, and a note that says what is happening
  const bootName = document.getElementById("boot-name"), bootNote = document.getElementById("boot-note");
  const note = s => { if (bootNote && bootNote.isConnected) bootNote.textContent = s; };
  if (bootName) fetch("/config").then(r => r.ok ? r.json() : null).then(c => { if (c && c.name && bootName.isConnected) bootName.textContent = String(c.name).toUpperCase(); }).catch(() => {});
  addEventListener("message", e => { if ((e.data || {}).boardCamera === "on") note("starting the camera… allow it when the browser asks"); });
  const btn = document.createElement("button"); btn.id = "troi-hands"; btn.type = "button"; btn.setAttribute("aria-pressed", "false");
  const on = () => !!(window.cam && window.cam.srcObject);
  const paint = () => { const v = on(); btn.setAttribute("aria-pressed", v ? "true" : "false"); btn.textContent = v ? "Hands on" : "Hands off";
    btn.title = v ? "Hand tracking is on. Click to switch the camera off" : "Hand tracking is off. Click to switch the camera on (the browser asks for it once)"; };
  btn.addEventListener("click", async () => {
    const want = !on();
    try { if (want) { note("starting the camera… allow it when the browser asks"); if (window.__camOn) await window.__camOn(); } else if (window.__camOff) window.__camOff(); } catch (e) {}
    paint();
    try { if (window.parent !== window) window.parent.postMessage({ troi: "hands", on: on() }, "*"); } catch (e) {}
  });
  document.body.appendChild(btn); setInterval(paint, 500); paint();
})();
