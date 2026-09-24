#!/bin/bash
# Adds cursor control (mouse.js) to the hands board: one script tag before </body>,
# and one line that exposes the hand tracker to it (the page is a module, so its
# variables are private otherwise). Idempotent; re-run after any barehands update.
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/paths.sh"; S="$ROOT/barehands/stage.html"
M="$C/barehands/mouse.js"; [ -f "$M" ] && cp "$M" "$ROOT/barehands/mouse.js"
B="$C/barehands/board.css"; [ -f "$B" ] && cp "$B" "$ROOT/barehands/board.css"
J="$C/barehands/board.js"; [ -f "$J" ] && cp "$J" "$ROOT/barehands/board.js"
python3 - "$S" <<'PY'
import sys; p = sys.argv[1]; s = open(p).read(); changed = []
if 'src="mouse.js"' not in s:
    i = s.rfind("</body>"); s = s[:i] + '<script src="mouse.js"></script>\n' + s[i:]; changed.append("script tag")
if 'src="board.js"' not in s:
    i = s.rfind("</body>"); s = s[:i] + '<script src="board.js"></script>\n' + s[i:]; changed.append("board script")
ring = "function drawRing(sc) {"
if "window.__RING" not in s and ring in s:   # the ring's look comes from board.js: what it needs, by getter (the module's own bindings stay live)
    s = s.replace(ring, 'for (const [k, g] of [["__RING", () => RING], ["__ringAmp", () => ringAmp], ["__ensureRingRes", () => ensureRingRes], ["__CFG", () => CFG]]) Object.defineProperty(window, k, { get: g, configurable: true });   // troi-console/board.js\n' + ring, 1); changed.append("ring hooks")
if "(window.__ringDraw || drawRing)(sc)" not in s and "    drawRing(sc);" in s:
    s = s.replace("    drawRing(sc);", "    (window.__ringDraw || drawRing)(sc);", 1); changed.append("ring draw")
if 'href="board.css"' not in s:
    i = s.find("</head>"); s = s[:i] + '<link rel="stylesheet" href="board.css">\n' + s[i:]; changed.append("stylesheet")
hook = 'document.getElementById("boot").remove();'
if "window.__landmarker" not in s and hook in s:
    s = s.replace(hook, hook + "\n  window.__landmarker = landmarker;   // troi-console/mouse.js: cursor control", 1); changed.append("tracker hook")
# images honour x/y (0..1 of the viewport) and w/h (fractions of the viewport) like cards do; present accepts unfocus
img_old = 'else { it.anim = { k: "in", t: 0 }; it.el.style.opacity = "0.05"; }\n      items.push(it);\n    } else if (c.a === "add_card" && c.title) {'
img_new = ('else { it.anim = { k: "in", t: 0 }; it.el.style.opacity = "0.05";\n'
           '        if (typeof c.x === "number") it.x = Math.min(0.92, Math.max(0.08, c.x)) * innerWidth;   // troi-console: placed pictures\n'
           '        if (typeof c.y === "number") it.y = Math.min(0.92, Math.max(0.08, c.y)) * innerHeight;\n'
           '        const im = it.el.querySelector("img,video"); if (im && typeof c.w === "number") im.style.maxWidth = (c.w * 100) + "vw"; if (im && typeof c.h === "number") im.style.maxHeight = (c.h * 100) + "vh"; }\n'
           '      items.push(it);\n    } else if (c.a === "add_card" && c.title) {')
if "troi-console: placed pictures" not in s and img_old in s:
    s = s.replace(img_old, img_new, 1); changed.append("placed pictures")
pr_old = '    } else if (c.a === "present") {\n      // THE PRESENT verb'
pr_new = '    } else if (c.a === "present" && c.unfocus) {\n      endPresent();                                   // troi-console: unfocus\n    } else if (c.a === "present") {\n      // THE PRESENT verb'
if "troi-console: unfocus" not in s and pr_old in s:
    s = s.replace(pr_old, pr_new, 1); changed.append("unfocus")
# the camera stays OFF until asked (battery): the console's Eyes pane or the agent turn it on by message
cam_old = "async function boot() {\n  await pickInitialCam();"
cam_new = ("async function boot() {\n"
           "  window.__camOn = async () => { if (!cam.srcObject) { await pickInitialCam(); toast(\"hand tracking camera on\", 1500); } };   // troi-console: camera by request\n"
           "  window.__camOff = () => { if (cam.srcObject) { cam.srcObject.getTracks().forEach(t => t.stop()); cam.srcObject = null; toast(\"hand tracking camera off\", 1500); } };\n"
           "  addEventListener(\"message\", e => { const m = e.data || {}; if (m.boardCamera === \"on\") window.__camOn(); if (m.boardCamera === \"off\") window.__camOff(); });\n"
           "  if (new URLSearchParams(location.search).get(\"cam\") === \"1\") await pickInitialCam();")
if "troi-console: camera by request" not in s and cam_old in s:
    s = s.replace(cam_old, cam_new, 1); changed.append("camera by request")
loop_old = "    if (cam.currentTime !== lastVideoTs) {\n      lastVideoTs = cam.currentTime;"
loop_new = "    if (cam.srcObject ? cam.currentTime !== lastVideoTs : (now - (window.__mouseTick || 0) > 33)) {   // troi-console: no camera, the mouse hand still runs\n      lastVideoTs = cam.currentTime; window.__mouseTick = now;"
if "troi-console: no camera" not in s and loop_old in s:
    s = s.replace(loop_old, loop_new, 1); changed.append("loop without camera")
ts_old = "function toScreen(lm) {\n  const vw = cam.videoWidth, vh = cam.videoHeight;"
ts_new = "function toScreen(lm) {\n  const vw = cam.videoWidth || 1280, vh = cam.videoHeight || 720;   // troi-console: sane mapping with the camera off"
if "troi-console: sane mapping" not in s and ts_old in s:
    s = s.replace(ts_old, ts_new, 1); changed.append("mapping without camera")
det_old = "      const res = landmarker.detectForVideo(cam, now);"
det_new = "      let res; try { res = landmarker.detectForVideo(cam, now); } catch (e) { res = { landmarks: [] }; }   // troi-console: an empty video must not stop the loop"
if "troi-console: an empty video" not in s and det_old in s:
    s = s.replace(det_old, det_new, 1); changed.append("detect guard")
if changed: open(p, "w").write(s); print("board: patched", ", ".join(changed))
else: print("board: cursor control already patched")
PY
