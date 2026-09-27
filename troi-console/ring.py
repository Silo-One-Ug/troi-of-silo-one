#!/usr/bin/env python3
"""The agent's globe, everywhere: a small floating window that follows you across every
Space and over full-screen apps, breathing with the agent's state (idle, listening,
thinking, speaking) from the voice line's signal files.

  double-click        open the console (http://localhost:3100) in the browser
  click and drag      move it (the spot is remembered in data/console.json)
  menu bar "T"        show / hide the ring, open the console, quit

Runs as a login service (com.troi-of-silo-one.ring). Needs only the voice line's state files;
when the agent is not running the ring dims to "off".
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
import sys as _sys; _sys.path.insert(0, str(Path(__file__).resolve().parent)); import paths as P  # noqa: E402
import db as _DB  # noqa: E402  (small documents live in troi.db)

import objc
from AppKit import (NSView, NSApplication, NSApplicationActivationPolicyAccessory, NSBackingStoreBuffered, NSColor, NSMakeRect, NSMenu,
                    NSMenuItem, NSPanel, NSScreen, NSStatusBar, NSVariableStatusItemLength, NSWindowCollectionBehaviorCanJoinAllSpaces,
                    NSWindowCollectionBehaviorFullScreenAuxiliary, NSWindowCollectionBehaviorStationary, NSWindowStyleMaskBorderless,
                    NSWindowStyleMaskNonactivatingPanel, NSStatusWindowLevel, NSWorkspace,
                    NSWindowStyleMaskResizable, NSFloatingWindowLevel, NSVisualEffectView, NSVisualEffectMaterialHUDWindow,
                    NSVisualEffectBlendingModeBehindWindow, NSVisualEffectStateActive, NSViewWidthSizable, NSViewHeightSizable, NSViewMinYMargin,
                    NSViewMinXMargin, NSViewMaxYMargin, NSButton, NSImage, NSImageView, NSImageOnly, NSOpenPanel,
                    NSAppearance, NSAppearanceNameAqua, NSAppearanceNameDarkAqua, NSVisualEffectMaterialPopover)
from Foundation import NSObject, NSTimer, NSURL
from WebKit import WKWebView, WKWebViewConfiguration, WKUserContentController

HERE = Path(__file__).resolve().parent
HOME = HERE.parent
SETTINGS = P.CONFIG
STATE = HOME / "backtalk" / ".voice_state"
WAVE = HOME / "backtalk" / ".voice_waveform"
FIFO = HERE / ".typed"
SIZE = 132

def _agent_name():
    import json as _j, os as _o
    try: n = _j.load(open(str(P.BACKTALK / "backtalk.json"))).get("name", "AGENT")
    except Exception: n = "AGENT"
    return ".".join(n.upper()[:6])
HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
  html,body{margin:0;background:transparent;overflow:hidden;-webkit-user-select:none;cursor:default}
  #w{position:fixed;inset:0;display:grid;place-items:center}
  canvas{position:absolute;inset:0}
  #n{position:absolute;inset:0;display:grid;place-items:center;font:700 11px/1 -apple-system,ui-sans-serif;letter-spacing:.32em;color:#fff2cc;text-shadow:0 0 10px rgba(255,200,90,.95),0 0 2px #000;pointer-events:none}
  #b{position:absolute;right:14px;top:14px;min-width:18px;height:18px;padding:0 5px;border-radius:9px;background:#ff5f57;color:#fff;font:700 11px/18px -apple-system,ui-sans-serif;text-align:center;box-shadow:0 0 10px rgba(255,95,87,.8);display:none;pointer-events:none}
  #s{position:absolute;left:0;right:0;bottom:12px;text-align:center;font:500 8px/1 -apple-system,ui-sans-serif;letter-spacing:.22em;color:rgba(255,225,170,.85);text-transform:uppercase;pointer-events:none;text-shadow:0 0 6px rgba(0,0,0,.8)}
</style></head><body><div id="w"><canvas id="c"></canvas><div id="n">__NAME__</div><div id="s">off</div><div id="b"></div></div>
<script>
// A gold globe in three dimensions: a wireframe sphere on a tilted axis, an orbit ring around
// it, two satellites on the ring. Everything is projected by hand on a 2D canvas (no libraries,
// works offline, one file). The state changes the speed, the size and the accents.
const cv=document.getElementById("c"),ctx=cv.getContext("2d");let S=132,D=devicePixelRatio||2;cv.width=S*D;cv.height=S*D;cv.style.width=S+"px";cv.style.height=S+"px";
let state="off",level=0,t0=performance.now(),spin=0,ringSpin=0,lastT=t0;
const GOLD=[255,200,90], PALE=[255,240,196], DEEP=[188,130,26];
const ACC={off:[140,120,90],idle:[255,200,90],listening:[255,160,80],thinking:[255,225,140],working:[255,190,110],speaking:[170,255,190]};
function setState(s,l){state=s in ACC?s:"idle";level=l||0;document.getElementById("s").textContent=state}
var power="full", lastDraw=0;                          // the frames follow the state and the power source: a globe breathing at idle needs no sixty a second
function setPower(p){power=p==="saver"?"saver":"full"}
function fpsNow(){const busy=state==="speaking"||state==="listening"||state==="thinking"||state==="working";return power==="saver"?(busy?24:state==="off"?2:8):(busy?60:state==="off"?4:20)}
function setBadge(n){const b=document.getElementById("b");b.style.display=n>0?"block":"none";b.textContent=n}
const rgba=(c,a)=>`rgba(${c[0]},${c[1]},${c[2]},${a})`, mix=(a,b,t)=>[0,1,2].map(i=>Math.round(a[i]+(b[i]-a[i])*t));
const AX=23.4*Math.PI/180;            // the axis leans like the Earth's
const VIEW=-0.42;                     // and the whole globe tips toward you a little
// a point on the unit sphere (lat, lon) → screen (x, y) and depth (z toward the viewer)
function P(lat,lon,R,cx,cy){
  let x=Math.cos(lat)*Math.cos(lon), y=Math.sin(lat), z=Math.cos(lat)*Math.sin(lon);
  let y1=y*Math.cos(AX)-x*Math.sin(AX), x1=y*Math.sin(AX)+x*Math.cos(AX);  // lean the axis (rotate about z)
  let y2=y1*Math.cos(VIEW)-z*Math.sin(VIEW), z2=y1*Math.sin(VIEW)+z*Math.cos(VIEW);   // tip toward the viewer (about x)
  return {x:cx+x1*R, y:cy-y2*R, z:z2};
}
function wire(R,cx,cy,front,col,lw){
  // meridians and parallels; only the requested side (front or back) is stroked
  ctx.lineWidth=lw; ctx.strokeStyle=col;
  const curves=[];
  for(let m=0;m<12;m++){ const lon=m*Math.PI/6+spin; const pts=[]; for(let i=0;i<=40;i++){ pts.push(P(-Math.PI/2+i*Math.PI/40,lon,R,cx,cy)); } curves.push(pts); }
  for(let k=-2;k<=2;k++){ const lat=k*Math.PI/6; const pts=[]; for(let i=0;i<=72;i++){ pts.push(P(lat,i*Math.PI/36+spin,R,cx,cy)); } curves.push(pts); }
  curves.forEach(pts=>{ ctx.beginPath(); let pen=false;
    pts.forEach(p=>{ const ok=front?p.z>=-0.02:p.z<0.02; if(ok){ pen?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y); pen=true; } else pen=false; });
    ctx.stroke(); });
}
function orbit(Rr,cx,cy,front,pulse,off){
  // the orbit ring: a circle in a plane tilted 68° from the screen, turning slowly; drawn as short
  // segments whose colour follows a sheen, so it reads as turned metal
  const TILT=68*Math.PI/180, N=72; let prev=null;
  for(let i=0;i<=N;i++){ const a=i/N*6.283+ringSpin; const x=Math.cos(a)*Rr, y0=Math.sin(a)*Rr; const y=y0*Math.cos(TILT), z=y0*Math.sin(TILT);
    const ex=Math.cos(0.35), sx=Math.sin(0.35); const px=cx+x*ex-y*sx, py=cy+x*sx+y*ex;      // the ring leans 20° in the screen plane too
    const p={x:px,y:py,z:z}; if(prev){ const ok=front?(p.z+prev.z)/2>=0:(p.z+prev.z)/2<0; if(ok){ const sh=.5+.5*Math.cos(a*3-ringSpin*4); ctx.strokeStyle=rgba(mix(DEEP,PALE,sh),off?.3:(front?.95:.35)); ctx.lineWidth=front?3.2+pulse*1.2:2; ctx.beginPath(); ctx.moveTo(prev.x,prev.y); ctx.lineTo(p.x,p.y); ctx.stroke(); } }
    prev=p; }
  // two satellites ride the ring
  for(let k=0;k<2;k++){ const a=ringSpin*1.6+k*Math.PI; const x=Math.cos(a)*Rr, y0=Math.sin(a)*Rr; const y=y0*Math.cos(TILT), z=y0*Math.sin(TILT); const ex=Math.cos(0.35), sx=Math.sin(0.35); const px=cx+x*ex-y*sx, py=cy+x*sx+y*ex;
    if((z>=0)===front){ const r=front?4.5:3; const g=ctx.createRadialGradient(px,py,0,px,py,r); g.addColorStop(0,rgba(PALE,off?.3:1)); g.addColorStop(.5,rgba(GOLD,off?.2:.8)); g.addColorStop(1,rgba(GOLD,0)); ctx.fillStyle=g; ctx.beginPath(); ctx.arc(px,py,r,0,7); ctx.fill(); } }
}
function frame(t){
  requestAnimationFrame(frame);
  if(t-lastDraw<1000/fpsNow()-1) return; lastDraw=t;
  ctx.setTransform(D,0,0,D,0,0); ctx.clearRect(0,0,S,S);
  const c=ACC[state], cx=S/2, cy=S/2-3, ph=(t-t0)/1000, dt=Math.min(.3,(t-lastT)/1000); lastT=t;
  const off=state==="off";
  const breath=state==="idle"?.5+.5*Math.sin(ph*1.6):off?.15:1;
  const pulse=state==="speaking"?Math.min(1,level*3):state==="listening"?.6+.4*Math.sin(ph*6):state==="thinking"?.5+.5*Math.sin(ph*3):0;
  spin+=dt*(state==="thinking"||state==="working"?1.5:state==="speaking"?.8:off?.05:.32); ringSpin+=dt*(state==="thinking"||state==="working"?1.1:off?.03:.28);
  const R=34+pulse*2.5, Rr=R*1.52;
  // warm halo
  const g=ctx.createRadialGradient(cx,cy,R*.5,cx,cy,R*1.9); g.addColorStop(0,rgba(GOLD,(.20*breath+.30*pulse)*(off?.3:1))); g.addColorStop(1,rgba(GOLD,0)); ctx.fillStyle=g; ctx.beginPath(); ctx.arc(cx,cy,R*1.9,0,7); ctx.fill();
  // the far side of the orbit ring, then the far side of the wire
  orbit(Rr,cx,cy,false,pulse,off);
  wire(R,cx,cy,false,rgba(GOLD,off?.08:.16),.8);
  // the globe body: dark glass with a gold rim and a highlight up-left
  const body=ctx.createRadialGradient(cx-R*.35,cy-R*.4,R*.1,cx,cy,R); body.addColorStop(0,rgba(GOLD,off?.08:.22)); body.addColorStop(.55,"rgba(40,28,10,.62)"); body.addColorStop(1,rgba(DEEP,.55));
  ctx.fillStyle=body; ctx.beginPath(); ctx.arc(cx,cy,R,0,7); ctx.fill();
  ctx.lineWidth=1.2; ctx.strokeStyle=rgba(GOLD,off?.25:.7); ctx.shadowColor=rgba(GOLD,.9); ctx.shadowBlur=(8+pulse*14)*(off?.3:1); ctx.beginPath(); ctx.arc(cx,cy,R,0,7); ctx.stroke(); ctx.shadowBlur=0;
  // the near side of the wire, brighter, then the near side of the ring
  wire(R,cx,cy,true,rgba(mix(GOLD,PALE,.35),off?.25:.78),1);
  // the equator carries the state colour
  ctx.lineWidth=1.6; ctx.strokeStyle=rgba(c,off?.2:.75); ctx.beginPath(); let pen=false; for(let i=0;i<=72;i++){ const p=P(0,i*Math.PI/36+spin,R,cx,cy); if(p.z>=0){ pen?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y); pen=true; } else pen=false; } ctx.stroke();
  // a specular glint
  const sp=ctx.createRadialGradient(cx-R*.42,cy-R*.45,0,cx-R*.42,cy-R*.45,R*.5); sp.addColorStop(0,"rgba(255,255,255,"+(off?.05:.22)+")"); sp.addColorStop(1,"rgba(255,255,255,0)"); ctx.fillStyle=sp; ctx.beginPath(); ctx.arc(cx,cy,R,0,7); ctx.fill();
  ctx.shadowColor=rgba(GOLD,.85); ctx.shadowBlur=off?2:8; orbit(Rr,cx,cy,true,pulse,off); ctx.shadowBlur=0;
  // state flourishes
  if(state==="thinking"||state==="working"){ const sw=ctx.createConicGradient(ph*2.4,cx,cy); sw.addColorStop(0,rgba(c,0)); sw.addColorStop(.22,rgba(c,.28)); sw.addColorStop(.23,rgba(c,0)); ctx.fillStyle=sw; ctx.beginPath(); ctx.arc(cx,cy,R*1.25,0,7); ctx.arc(cx,cy,R*1.05,0,7,true); ctx.fill(); }
  if(state==="listening"){ ctx.strokeStyle=rgba(c,.85); ctx.lineWidth=1.5; ctx.setLineDash([3,5]); ctx.beginPath(); ctx.arc(cx,cy,R*1.22+Math.sin(ph*6)*2,0,7); ctx.stroke(); ctx.setLineDash([]); }
  if(state==="speaking"){ ctx.strokeStyle=rgba(c,.45+.5*pulse); ctx.lineWidth=2; ctx.beginPath(); ctx.arc(cx,cy,R*1.15+pulse*5,0,7); ctx.stroke(); }
}
requestAnimationFrame(frame);
</script></body></html>"""


def settings():
    try:
        return json.loads(SETTINGS.read_text())
    except Exception:
        return {}


CONSOLE_URL = os.environ.get("TROI_CONSOLE_URL", "http://localhost:3100/")     # the console app; :8796 is the agent's API
FLOAT_URL = CONSOLE_URL.rstrip("/") + "/float"                    # the conversation alone, for the floater panel
FLOAT_FILE = P.DATA / "cache" / "floater.json"                       # {shown, x, y, w, h}: console.sh float and the board server write shown; the panel writes its frame



def save_pos(x, y):
    try:
        c = settings(); c["ring_pos"] = [int(x), int(y)]; SETTINGS.write_text(json.dumps(c, indent=2))
    except Exception:
        pass


class DragView(NSView):
    """A see-through layer over the ring: drag moves the window, a double-click opens the console."""
    def mouseDown_(self, event):
        if event.clickCount() >= 2:
            NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_(CONSOLE_URL))
            return
        before = self.window().frame().origin
        self.window().performWindowDragWithEvent_(event)
        after = self.window().frame().origin
        if abs(after.x - before.x) >= 1 or abs(after.y - before.y) >= 1:
            save_pos(after.x, after.y)

    def acceptsFirstMouse_(self, event):
        return True


def float_state():
    try:
        return json.loads(FLOAT_FILE.read_text())
    except Exception:
        return {}


def float_write(**kv):
    """Merge keys into the floater's state file (shown, x, y, w, h); atomic, tolerant."""
    try:
        d = float_state(); d.update(kv)
        FLOAT_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = FLOAT_FILE.with_suffix(".json.tmp"); tmp.write_text(json.dumps(d)); os.replace(tmp, FLOAT_FILE)
    except Exception:
        pass


class FloatDrag(NSView):
    """The strip at the top of the conversation panel: drag moves it, a double-click puts it back to its default place."""
    def mouseDown_(self, event):
        if event.clickCount() >= 2:
            APP.float_default(); return
        self.window().performWindowDragWithEvent_(event)
        APP.float_remember()

    def acceptsFirstMouse_(self, event):
        return True


class FloatPanel(NSPanel):
    """A borderless panel says no to becoming the key window, which is why nothing typed reached the conversation; this one
    says yes (and only when needed, so the app the owner is in keeps the front until they click into the pane)."""
    def canBecomeKeyWindow(self):
        return True

    def canBecomeMainWindow(self):
        return False


# WebKit hands these two delegate methods a completion block that reaches Python without a signature ("cannot call block without a
# signature", whatever metadata is registered), so the ring cannot answer them from Python: it crashed inside WebKit's callback and
# launchd brought it back, the pane vanishing and returning at every paperclip. The real delegate is therefore native: TroiWebUI,
# forty lines of Objective-C compiled into the ring's bundle (WEBUI_M, built beside the launcher) and loaded here. This Python one
# is the fallback when there is no compiler: the picker still opens, the chosen file does not reach the page.
class WebUI(NSObject, protocols=[objc.protocolNamed("WKUIDelegate")]):
    """What the web view asks the host for: a file picker for the paperclip (a plain web view has none and the click does
    nothing), and the microphone for the recorder (granted here; the Mac asks once more for the ring's own permission)."""
    def webView_runOpenPanelWithParameters_initiatedByFrame_completionHandler_(self, web, params, frame, handler):
        # the picker runs beside the page, never as a modal loop inside WebKit's own callback: that stalled the web process (the
        # pane went blank and came back) and the chosen file never reached the page
        panel = NSOpenPanel.openPanel()
        panel.setCanChooseFiles_(True); panel.setCanChooseDirectories_(False)
        try:
            panel.setAllowsMultipleSelection_(bool(params.allowsMultipleSelection()))
        except Exception:
            panel.setAllowsMultipleSelection_(True)
        panel.setTitle_("A file or a photo for the conversation"); panel.setPrompt_("Attach")
        panel.setLevel_(NSFloatingWindowLevel + 1)
        self._panel = panel                                            # kept until it answers

        def done(res):
            try:
                handler(panel.URLs() if res == 1 else None)
            except Exception as e:
                print("[ring] file picker:", e, file=sys.stderr)
            self._panel = None
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        panel.beginWithCompletionHandler_(done)
        panel.makeKeyAndOrderFront_(None)

    def webView_requestMediaCapturePermissionForOrigin_initiatedByFrame_type_decisionHandler_(self, web, origin, frame, kind, handler):
        handler(1)                                                     # WKPermissionDecisionGrant: the console asked for the microphone


def _symbol(name, tip):
    img = NSImage.imageWithSystemSymbolName_accessibilityDescription_(name, tip)
    return img


class Floater:
    """The conversation as a panel of its own: translucent, resizable, above every app and on every space, showing the
    console's /float route. Shown and hidden through the state file (console.sh float, the console's pane button through
    the board server, the ring's menu); its frame is remembered in the same file. A header carries three buttons: back to
    the console, larger or smaller, put away; a grip glyph marks the corner that resizes (every edge does)."""
    W, H, MIN_W, MIN_H, STRIP, BIG_W, BIG_H = 440, 560, 360, 260, 30, 760, 880

    def __init__(self):
        scr = NSScreen.mainScreen().visibleFrame(); st = float_state()
        x = st.get("x", scr.origin.x + scr.size.width - self.W - 24); y = st.get("y", scr.origin.y + 24)
        w = max(self.MIN_W, st.get("w", self.W)); h = max(self.MIN_H, st.get("h", self.H))
        self.win = FloatPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(x, y, w, h), NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel | NSWindowStyleMaskResizable, NSBackingStoreBuffered, False)
        p = self.win
        p.setLevel_(NSFloatingWindowLevel)
        p.setCollectionBehavior_(NSWindowCollectionBehaviorCanJoinAllSpaces | NSWindowCollectionBehaviorFullScreenAuxiliary)
        p.setOpaque_(False); p.setBackgroundColor_(NSColor.clearColor()); p.setHasShadow_(True)
        p.setMovableByWindowBackground_(False); p.setHidesOnDeactivate_(False); p.setBecomesKeyOnlyIfNeeded_(True)
        p.setMinSize_((self.MIN_W, self.MIN_H))
        glass = NSVisualEffectView.alloc().initWithFrame_(NSMakeRect(0, 0, w, h))
        glass.setMaterial_(NSVisualEffectMaterialHUDWindow); glass.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow); glass.setState_(NSVisualEffectStateActive)
        glass.setWantsLayer_(True); glass.layer().setCornerRadius_(14.0); glass.layer().setMasksToBounds_(True)
        glass.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        cfg = WKWebViewConfiguration.alloc().init()
        # a web view has no navigator.mediaDevices unless its host says so (WebKit's own switch, private): the pane's microphone needs it,
        # and the console is plain http on localhost, which WebKit may not count as a secure connection for capture
        for sel, val in (("_setMediaDevicesEnabled_", True), ("_setMediaCaptureRequiresSecureConnection_", False)):
            try:
                getattr(cfg.preferences(), sel)(val)
            except Exception as e:
                print("[ring] web view preference", sel, "not available:", e, file=sys.stderr)
        self.web = WKWebView.alloc().initWithFrame_configuration_(NSMakeRect(0, 0, w, h - self.STRIP), cfg)
        self.web.setValue_forKey_(False, "drawsBackground")
        self.web.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        self.ui = native_webui() or WebUI.alloc().init(); self.web.setUIDelegate_(self.ui)
        glass.addSubview_(self.web)
        self.strip = FloatDrag.alloc().initWithFrame_(NSMakeRect(0, h - self.STRIP, w, self.STRIP))
        self.strip.setAutoresizingMask_(NSViewWidthSizable | NSViewMinYMargin)
        glass.addSubview_(self.strip)
        # the header's three buttons, right-aligned, following the right edge: back to the console, larger or smaller, put away
        app = NSApplication.sharedApplication().delegate()
        for i, (sym, tip, action) in enumerate((("macwindow", "Back to the console", "floatconsole:"),
                                                 ("arrow.up.left.and.arrow.down.right", "Larger, or back to the small pane", "floatsize:"),
                                                 ("xmark", "Put the conversation away", "floatclose:"))):
            b = NSButton.alloc().initWithFrame_(NSMakeRect(w - 28 * (3 - i) - 4, 4, 24, 22))
            b.setBordered_(False); b.setImage_(_symbol(sym, tip)); b.setImagePosition_(NSImageOnly); b.setToolTip_(tip)
            b.setContentTintColor_(NSColor.secondaryLabelColor()); b.setTarget_(app); b.setAction_(action)
            b.setAutoresizingMask_(NSViewMinXMargin)
            self.strip.addSubview_(b)
        grip = NSImageView.alloc().initWithFrame_(NSMakeRect(w - 18, 3, 14, 14))
        grip.setImage_(_symbol("arrow.up.left.and.arrow.down.right", "resize")); grip.setContentTintColor_(NSColor.tertiaryLabelColor())
        grip.setToolTip_("Drag an edge or this corner to resize"); grip.setAutoresizingMask_(NSViewMinXMargin | NSViewMaxYMargin)
        glass.addSubview_(grip)
        p.setContentView_(glass)
        self.glass = glass; self._dark = None
        self.loaded_at = 0.0; self.lastframe = None; self.moved_at = 0.0; self.shown = False

    def toggle_size(self):
        """The small pane or the large one, grown from its top-right corner and kept on the screen."""
        f = self.win.frame(); scr = NSScreen.mainScreen().visibleFrame()
        nw, nh = (self.BIG_W, self.BIG_H) if f.size.width < (self.W + self.BIG_W) / 2 else (self.W, self.H)
        nx = min(max(scr.origin.x, f.origin.x + f.size.width - nw), scr.origin.x + scr.size.width - nw)
        ny = min(max(scr.origin.y, f.origin.y + f.size.height - nh), scr.origin.y + scr.size.height - nh)
        self.win.setFrame_display_animate_(NSMakeRect(nx, ny, nw, nh), True, True)
        float_write(x=int(nx), y=int(ny), w=int(nw), h=int(nh))

    def load(self):
        self.web.loadRequest_(__import__("Foundation").NSURLRequest.requestWithURL_(NSURL.URLWithString_(FLOAT_URL)))
        self.loaded_at = time.time()

    def show(self):
        if time.time() - self.loaded_at > 60:            # fresh after a while away: the console may have been rebuilt or restarted
            self.load()
        self.win.orderFrontRegardless(); self.shown = True

    def hide(self):
        self.win.orderOut_(None); self.shown = False

    def follow_theme(self):
        """The panel's glass follows the page it shows: dark HUD glass under a dark console, light glass under a light one
        (the page takes the theme from the settings; Paul, 2026-09-27: "the floater not being light mode")."""
        def done(result, error):
            dark = True if error is not None or result is None else bool(result)
            if self._dark == dark:
                return
            self._dark = dark
            try:
                self.glass.setMaterial_(NSVisualEffectMaterialHUDWindow if dark else NSVisualEffectMaterialPopover)
                self.glass.setAppearance_(NSAppearance.appearanceNamed_(NSAppearanceNameDarkAqua if dark else NSAppearanceNameAqua))
            except Exception as e:
                print("[ring] floater theme not applied:", e, file=sys.stderr)
        try:
            self.web.evaluateJavaScript_completionHandler_("document.documentElement.classList.contains('dark')", done)
        except Exception as e:
            print("[ring] floater theme not read:", e, file=sys.stderr)

    def sync(self):
        """Follow the state file (shown), and remember the frame a second after it stops moving; the glass follows the theme."""
        want = bool(float_state().get("shown", False))
        if self.win.isVisible():
            self.follow_theme()
        if want and not self.win.isVisible(): self.show()
        elif not want and self.win.isVisible(): self.hide()
        f = self.win.frame(); fr = (int(f.origin.x), int(f.origin.y), int(f.size.width), int(f.size.height))
        if self.lastframe and fr != self.lastframe: self.moved_at = time.time()
        if self.lastframe and fr == self.lastframe and self.moved_at and time.time() - self.moved_at > 1.0:
            float_write(x=fr[0], y=fr[1], w=fr[2], h=fr[3]); self.moved_at = 0.0
        self.lastframe = fr

    def default(self):
        scr = NSScreen.mainScreen().visibleFrame()
        self.win.setFrame_display_(NSMakeRect(scr.origin.x + scr.size.width - self.W - 24, scr.origin.y + 24, self.W, self.H), True)
        float_write(x=int(scr.origin.x + scr.size.width - self.W - 24), y=int(scr.origin.y + 24), w=self.W, h=self.H)


APP = None


class Handler(NSObject):
    def userContentController_didReceiveScriptMessage_(self, ctl, msg):
        if str(msg.body()) == "open":
            NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_(CONSOLE_URL))


class App(NSObject):
    def applicationDidFinishLaunching_(self, note):
        scr = NSScreen.mainScreen().visibleFrame()
        pos = settings().get("ring_pos") or [scr.origin.x + scr.size.width - SIZE - 12, scr.origin.y + scr.size.height - SIZE - 8]
        global APP; APP = self
        self.ring_pos = pos
        self.win = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(pos[0], pos[1], SIZE, SIZE), NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel, NSBackingStoreBuffered, False)
        w = self.win
        w.setLevel_(NSStatusWindowLevel)
        w.setCollectionBehavior_(NSWindowCollectionBehaviorCanJoinAllSpaces | NSWindowCollectionBehaviorStationary | NSWindowCollectionBehaviorFullScreenAuxiliary)
        w.setOpaque_(False); w.setBackgroundColor_(NSColor.clearColor()); w.setHasShadow_(False)
        w.setMovableByWindowBackground_(True); w.setHidesOnDeactivate_(False); w.setIgnoresMouseEvents_(False)
        cfg = WKWebViewConfiguration.alloc().init()
        ctl = WKUserContentController.alloc().init(); self.handler = Handler.alloc().init()
        ctl.addScriptMessageHandler_name_(self.handler, "troi"); cfg.setUserContentController_(ctl)
        self.web = WKWebView.alloc().initWithFrame_configuration_(NSMakeRect(0, 0, SIZE, SIZE), cfg)
        self.web.setValue_forKey_(False, "drawsBackground")
        self.web.loadHTMLString_baseURL_(HTML.replace("__NAME__", _agent_name()), None)
        container = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, SIZE, SIZE))
        container.addSubview_(self.web)
        self.drag = DragView.alloc().initWithFrame_(NSMakeRect(0, 0, SIZE, SIZE)); container.addSubview_(self.drag)
        w.setContentView_(container); w.orderFrontRegardless()
        # the menu bar item
        self.item = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        self.item.button().setTitle_("T")
        menu = NSMenu.alloc().init()
        for title, sel in (("Show / hide the ring", "toggle:"), ("Show / hide the conversation", "togglefloat:"), ("Open the console", "open:"), ("Quit the ring", "quit:")):
            it = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, sel, ""); it.setTarget_(self); menu.addItem_(it)
        self.item.setMenu_(menu)
        self.last = None; self.lastpos = None
        try:
            self.floater = Floater()
        except Exception as e:
            self.floater = None; print("[ring] no conversation panel:", e, file=sys.stderr)
        self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(0.2, self, "tick:", None, True)

    def check_power(self):
        """On battery the globe and the pane draw fewer frames: pmset says which side of the cord we are on (asked every 30 s)."""
        import subprocess
        try:
            out = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True, timeout=5).stdout
            mode = "saver" if "Battery Power" in out else "full"
        except Exception:
            mode = "full"
        self.power = mode
        self.web.evaluateJavaScript_completionHandler_(f"setPower({json.dumps(mode)})", None)
        # the pane is a WebKit view, which has no Battery API: the ring tells its page (window.__setBattery in the console's lib/power)
        if self.floater is not None and self.floater.win.isVisible():
            try:
                self.floater.web.evaluateJavaScript_completionHandler_(f"window.__setBattery&&window.__setBattery({'true' if mode == 'saver' else 'false'})", None)
            except Exception:
                pass

    def tick_(self, timer):
        n = getattr(self, "ticks", 0) + 1; self.ticks = n
        if n % 150 == 1:
            self.check_power()
        try:
            st = STATE.read_text().strip() if FIFO.exists() else "off"
        except Exception:
            st = "off"
        try:
            b = HOME / "backtalk" / ".voice_busy"
            if st == "idle" and b.exists() and time.time() - b.stat().st_mtime < 900:
                st = "working"
        except Exception:
            pass
        level = 0.0
        if st == "speaking":
            try:
                s = json.loads(WAVE.read_text()).get("samples", [])
                level = sum(abs(x) for x in s) / max(1, len(s))
            except Exception:
                level = 0.3
        self.web.evaluateJavaScript_completionHandler_(f"setState({json.dumps(st)}, {level:.3f})", None)
        # a badge for things waiting on the owner: approvals (console) and reminders due within ten minutes
        self.badge_tick = getattr(self, "badge_tick", 0) + 1
        if self.badge_tick % 20 == 0:
            n = 0
            try:
                import urllib.request
                with urllib.request.urlopen("http://127.0.0.1:8796/pending", timeout=2) as r:
                    n += len(json.load(r).get("pending", []))
            except Exception:
                pass
            try:
                rem = json.loads(_DB.doc("reminders").read_text())
                n += sum(1 for x in rem if x.get("at", 0) - time.time() < 600)
            except Exception:
                pass
            self.web.evaluateJavaScript_completionHandler_(f"setBadge({n})", None)
        if self.floater is not None and self.badge_tick % 3 == 0:
            try:
                self.floater.sync()
            except Exception:
                pass
        # remember where the ring was dragged
        f = self.win.frame(); p = (int(f.origin.x), int(f.origin.y))
        if self.lastpos and p != self.lastpos:
            self.moved_at = time.time()
        if self.lastpos and p == self.lastpos and getattr(self, "moved_at", 0) and time.time() - self.moved_at > 1.0:
            save_pos(*p); self.moved_at = 0
        self.lastpos = p

    def toggle_(self, sender):
        self.win.orderOut_(None) if self.win.isVisible() else self.win.orderFrontRegardless()

    def togglefloat_(self, sender):
        float_write(shown=not bool(float_state().get("shown", False)))

    def float_default(self):
        if self.floater is not None: self.floater.default()

    def float_remember(self):
        if self.floater is not None: self.floater.moved_at = time.time()

    def floatclose_(self, sender):
        float_write(shown=False)

    def floatsize_(self, sender):
        if self.floater is not None: self.floater.toggle_size()

    def floatconsole_(self, sender):
        """Back to the full console: the conversation returns to its column there, the pane goes, the console's window comes
        forward (the Chrome app the owner made of it, else whichever app shows a console window, else the default browser)."""
        import subprocess
        subprocess.Popen([str(HERE / "console.sh"), "talk", "column"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        float_write(shown=False)
        name = _agent_name()
        for cand in (Path.home() / "Applications" / "Chrome Apps.localized" / f"{name}.app", Path.home() / "Applications" / f"{name}.app"):
            if cand.exists():
                subprocess.Popen(["open", "-a", str(cand)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); return
        script = ('tell application "System Events" to repeat with p in (every application process whose background only is false)\n'
                  '  try\n    if (name of window 1 of p) contains "Console" then\n      set frontmost of p to true\n      return name of p\n    end if\n  end try\n'
                  'end repeat')
        r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=8)
        if not r.stdout.strip():
            NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_(CONSOLE_URL.rstrip("/") + "/conversation"))

    def open_(self, sender):
        NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_(CONSOLE_URL))

    def quit_(self, sender):
        NSApplication.sharedApplication().terminate_(None)


LAUNCHER_C = r'''
// the ring's launcher: a real application bundle around the same Python, so the Mac can ask the owner for the microphone
// (a usage description lives only in a bundle's Info.plist) and names the ring in its prompts. It loads the interpreter's
// library and runs ring.py; nothing else.
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
int main(int argc, char **argv) {
  const char *lib = getenv("TROI_LIBPYTHON");
  if (!lib) { fprintf(stderr, "ring: TROI_LIBPYTHON is not set\n"); return 2; }
  void *h = dlopen(lib, RTLD_NOW | RTLD_GLOBAL);
  if (!h) { fprintf(stderr, "ring: %s\n", dlerror()); return 2; }
  int (*pymain)(int, char **) = (int (*)(int, char **)) dlsym(h, "Py_BytesMain");
  if (!pymain) { fprintf(stderr, "ring: no Py_BytesMain in %s\n", lib); return 2; }
  return pymain(argc, argv);
}
'''


WEBUI_M = r'''
// TroiWebUI: what the conversation pane's web view asks its host for, answered natively. The paperclip's file picker (the Mac's
// own, beside the page, never a modal loop inside WebKit's callback) and the microphone (granted; the Mac then asks the owner
// once, in the ring's name). Built into the ring's bundle by ring.py and loaded from there.
#import <AppKit/AppKit.h>
#import <WebKit/WebKit.h>
@interface TroiWebUI : NSObject <WKUIDelegate>
@end
@implementation TroiWebUI
- (void)webView:(WKWebView *)webView runOpenPanelWithParameters:(WKOpenPanelParameters *)parameters initiatedByFrame:(WKFrameInfo *)frame
      completionHandler:(void (^)(NSArray<NSURL *> *URLs))completionHandler {
  NSOpenPanel *panel = [NSOpenPanel openPanel];
  panel.canChooseFiles = YES; panel.canChooseDirectories = NO;
  panel.allowsMultipleSelection = parameters.allowsMultipleSelection;
  panel.title = @"A file or a photo for the conversation"; panel.prompt = @"Attach";
  panel.level = NSFloatingWindowLevel + 1;
  [NSApp activateIgnoringOtherApps:YES];
  [panel beginWithCompletionHandler:^(NSModalResponse result) { completionHandler(result == NSModalResponseOK ? panel.URLs : nil); }];
  [panel makeKeyAndOrderFront:nil];
}
- (void)webView:(WKWebView *)webView requestMediaCapturePermissionForOrigin:(WKSecurityOrigin *)origin initiatedByFrame:(WKFrameInfo *)frame
      type:(WKMediaCaptureType)type decisionHandler:(void (^)(WKPermissionDecision decision))decisionHandler {
  decisionHandler(WKPermissionDecisionGrant);
}
@end
'''


def native_webui():
    """The native delegate from the bundle's dylib, or None (no compiler, no bundle): then the Python fallback serves."""
    try:
        dylib = bundle_dir() / "Contents" / "MacOS" / "TroiWebUI.dylib"
        if not dylib.exists():
            return None
        import ctypes
        ctypes.CDLL(str(dylib))
        return objc.lookUpClass("TroiWebUI").alloc().init()
    except Exception as e:
        print("[ring] native web delegate not loaded:", e, file=sys.stderr)
        return None


def bundle_dir():
    return P.DATA / "ring" / ("%s Ring.app" % _agent_name())


def build_bundle():
    """The app bundle, built here when missing or older than this file: Contents/MacOS/ring (the launcher, compiled with cc)
    and an Info.plist with the microphone's usage description. Returns the launcher's path, or None when it cannot be built."""
    import plistlib, shutil, subprocess
    app = bundle_dir(); macos = app / "Contents" / "MacOS"; exe = macos / "ring"; plist = app / "Contents" / "Info.plist"
    src = Path(__file__).resolve()
    if exe.exists() and plist.exists() and exe.stat().st_mtime >= src.stat().st_mtime:
        return exe
    cc = shutil.which("cc") or shutil.which("clang")
    if not cc:
        return None
    macos.mkdir(parents=True, exist_ok=True)
    c = app / "Contents" / "launcher.c"; c.write_text(LAUNCHER_C)
    r = subprocess.run([cc, "-O2", "-o", str(exe), str(c)], capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        print("[ring] the launcher did not compile:", r.stderr[-300:], file=sys.stderr); return None
    m = app / "Contents" / "TroiWebUI.m"; m.write_text(WEBUI_M); dylib = macos / "TroiWebUI.dylib"
    r = subprocess.run([cc, "-fobjc-arc", "-dynamiclib", "-framework", "AppKit", "-framework", "WebKit", "-o", str(dylib), str(m)], capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        print("[ring] the web delegate did not compile (the Python one serves):", r.stderr[-300:], file=sys.stderr)
    else:
        subprocess.run(["codesign", "--force", "--sign", "-", str(dylib)], capture_output=True, text=True, timeout=60)
    name = _agent_name()
    plistlib.dump({"CFBundleName": "%s Ring" % name, "CFBundleDisplayName": "%s Ring" % name, "CFBundleIdentifier": "com.troi-of-silo-one.ring",
                   "CFBundleExecutable": "ring", "CFBundlePackageType": "APPL", "CFBundleVersion": "1", "CFBundleShortVersionString": "1.0",
                   "LSUIElement": True, "NSHighResolutionCapable": True,
                   "NSMicrophoneUsageDescription": "The floating conversation records your voice when you press its microphone.",
                   "NSCameraUsageDescription": "The console's pages can show the camera when you ask."}, plist.open("wb"))
    (app / "Contents" / "PkgInfo").write_text("APPL????")
    subprocess.run(["codesign", "--force", "--sign", "-", str(exe)], capture_output=True, text=True, timeout=60)   # ad hoc: what Apple silicon asks of any binary
    return exe


def bundled_exec():
    """Run again from inside the bundle (the same process id, so launchd is none the wiser). Plain Python when anything is missing."""
    if os.environ.get("TROI_RING_BUNDLED") == "1" or "--no-bundle" in sys.argv:
        return
    try:
        exe = build_bundle()
        if not exe:
            return
        py = Path(sys.executable).resolve(); prefix = py.parent.parent
        lib = prefix / "lib" / ("libpython%d.%d.dylib" % sys.version_info[:2])
        if not lib.exists():
            print("[ring] no shared Python library at", lib, "; running plain", file=sys.stderr); return
        site = [p for p in sys.path if p.endswith("site-packages")]
        env = dict(os.environ, TROI_RING_BUNDLED="1", TROI_LIBPYTHON=str(lib), PYTHONHOME=str(prefix), PYTHONPATH=":".join(site + [str(HERE)]))
        os.execve(str(exe), [str(exe), str(Path(__file__).resolve()), *[a for a in sys.argv[1:]]], env)
    except Exception as e:
        print("[ring] running plain, no bundle:", e, file=sys.stderr)


if __name__ == "__main__":
    bundled_exec()
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)     # no Dock icon
    delegate = App.alloc().init(); app.setDelegate_(delegate)
    app.run()
