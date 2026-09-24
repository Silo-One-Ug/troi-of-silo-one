// mouse.js — cursor control for the barehands board (Silo One's addition, not part
// of the upstream repo). The board only understands hands, so the mouse becomes one:
// a synthetic 21-point hand is added to the tracker's results at the pointer.
//   move            the hand follows the pointer (open hand)
//   hold the button OK-sign pinch: drag to move, quick click = tap (open/close)
//   release         let go
// Real hands keep working alongside. The hand vanishes after 3 s without mouse motion.
(function () {
  if (new URLSearchParams(location.search).get("role") === "render") return;
  let mx = null, my = null, down = false, lastMove = 0;
  addEventListener("mousemove", e => { mx = e.clientX; my = e.clientY; lastMove = performance.now(); });
  addEventListener("mousedown", e => { if (e.button === 0) { down = true; lastMove = performance.now(); } });
  addEventListener("mouseup", () => { down = false; lastMove = performance.now(); });
  addEventListener("mouseleave", () => { mx = null; });
  document.addEventListener("mouseleave", () => { mx = null; });

  // screen -> normalized video coords (the inverse of the page's toScreen)
  function toVideo(sx, sy) {
    const vw = cam.videoWidth || 1280, vh = cam.videoHeight || 720;
    const scale = Math.max(innerWidth / vw, innerHeight / vh);
    const dw = vw * scale, dh = vh * scale;
    const ox = (innerWidth - dw) / 2, oy = (innerHeight - dh) / 2;
    return { x: 1 - (sx - ox) / dw, y: (sy - oy) / dh };
  }

  // a hand in normalized units, fingers up; (0,0) is the pinch point
  function hand(cx, cy, pinched) {
    const P = (x, y) => ({ x: cx + x, y: cy + y, z: 0 });
    const tip8 = pinched ? [-0.065, 0.0] : [-0.05, -0.08];
    const tip4 = pinched ? tip8 : [-0.10, 0.05];
    const mid = [(tip8[0] + tip4[0]) / 2, (tip8[1] + tip4[1]) / 2];
    cx -= mid[0]; cy -= mid[1];              // the cursor (tip/thumb midpoint) lands on the pointer
    const idx = pinched ? [[-0.05, 0.045], [-0.06, 0.02]] : [[-0.04, 0.02], [-0.045, -0.03]];
    return [
      P(0, 0.22),                                                     // 0 wrist
      P(-0.03, 0.19), P(-0.06, 0.14), P(-0.075, 0.09), P(tip4[0], tip4[1]),   // thumb
      P(-0.035, 0.08), P(idx[0][0], idx[0][1]), P(idx[1][0], idx[1][1]), P(tip8[0], tip8[1]),  // index
      P(-0.012, 0.07), P(-0.013, 0.01), P(-0.014, -0.04), P(-0.015, -0.09),   // middle
      P(0.012, 0.075), P(0.013, 0.02), P(0.014, -0.03), P(0.015, -0.08),      // ring
      P(0.036, 0.085), P(0.039, 0.04), P(0.042, 0.0), P(0.045, -0.05),        // pinky
    ];
  }

  function install() {
    const lm = window.__landmarker;
    if (!lm || !lm.detectForVideo) { setTimeout(install, 500); return; }
    if (lm.__mouse) return;
    const real = lm.detectForVideo.bind(lm);
    lm.detectForVideo = function (video, now) {
      let res = { landmarks: [], worldLandmarks: [], handedness: [] };
      if (video && video.srcObject && video.readyState >= 2) { try { res = real(video, now); } catch (e) {} }   // no camera: only the mouse hand
      const fresh = mx !== null && performance.now() - lastMove < 3000;
      if (fresh) {
        const v = toVideo(mx, my);
        const h = hand(v.x, v.y, down);
        res.landmarks = (res.landmarks || []).concat([h]);
        if (res.worldLandmarks) res.worldLandmarks = res.worldLandmarks.concat([h]);
        if (res.handedness) res.handedness = res.handedness.concat([[{ categoryName: "Right", score: 1, index: 1, displayName: "Right" }]]);
      }
      return res;
    };
    lm.__mouse = true;
    console.log("[mouse.js] cursor control on: move = hand, hold = pinch, click = tap");
  }
  install();
})();
