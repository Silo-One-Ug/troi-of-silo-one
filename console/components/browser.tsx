"use client";
// Browser: the agent's browser, live (Arc, shared with you, or a Chrome of its own: browser-mcp.sh decides). Watch it
// work, or take over: click, double-click, scroll, type, use the address bar, log in to a site for it. Frames come from
// the bridge a few times a second while this page is open; the bridge also says which app it is, for the Window button.
import { useEffect, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, AppWindow, RotateCw } from "lucide-react";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { edgeUrl, eget, epost } from "@/lib/edge";

type Info = { url?: string; title?: string; app?: string; w?: number; h?: number; up?: boolean; fresh?: boolean };
const SPECIAL: Record<string, string> = { Enter: "Enter", Backspace: "Backspace", Tab: "Tab", Escape: "Escape", ArrowUp: "ArrowUp", ArrowDown: "ArrowDown", ArrowLeft: "ArrowLeft", ArrowRight: "ArrowRight", Delete: "Delete", Home: "Home", End: "End", PageUp: "PageUp", PageDown: "PageDown" };

export function Browser() {
  const [info, setInfo] = useState<Info>({}); const [src, setSrc] = useState(""); const [url, setUrl] = useState(""); const editing = useRef(false); const imgRef = useRef<HTMLImageElement>(null); const infoRef = useRef<Info>({});
  useEffect(() => {
    let stop = false;
    const tick = async () => {
      if (stop) return;
      let d: Info = {};
      try { d = await eget("/browser"); setInfo(d); infoRef.current = d; if (!editing.current) setUrl(d.url && d.url !== "about:blank" ? d.url : ""); } catch {}
      if (d.up && d.fresh) { const next = `${edgeUrl()}/browser.jpg?t=${Date.now()}`; const im = new Image(); im.onload = () => setSrc(next); im.src = next; }
      setTimeout(tick, d.fresh ? 380 : 1500);
    };
    tick(); return () => { stop = true; };
  }, []);
  const cmd = (b: any) => epost("/browser", b);
  const point = (e: React.MouseEvent | React.WheelEvent) => { const i = infoRef.current, el = imgRef.current; if (!el || !i.w || !i.h) return null; const r = el.getBoundingClientRect(); const x = (e.clientX - r.left) / r.width * i.w, y = (e.clientY - r.top) / r.height * i.h; return x < 0 || y < 0 || x > i.w || y > i.h ? null : { x: Math.round(x), y: Math.round(y) }; };
  const go = () => { const u = url.trim(); if (!u) return; if (!info.up) cmd({ op: "open" }); setTimeout(() => cmd({ op: "goto", url: u }), info.up ? 0 : 4000); editing.current = false; };
  return (
    <div className="hairline fill-page flex flex-col overflow-hidden md:h-[calc(100vh-7.5rem)]">
      <div className="flex items-center gap-1.5 border-b border-border px-2 py-2 md:gap-2 md:px-3">{/* on a phone: icons only, the address field takes the width, the state sits in the line below */}
        <Button size="sm" variant="ghost" title="Back" aria-label="Back" className="px-2" onClick={() => cmd({ op: "back" })}><ArrowLeft className="h-4 w-4" /></Button>
        <Button size="sm" variant="ghost" title="Forward" aria-label="Forward" className="px-2" onClick={() => cmd({ op: "forward" })}><ArrowRight className="h-4 w-4" /></Button>
        <Button size="sm" variant="ghost" title="Reload" aria-label="Reload" className="hidden px-2 sm:inline-flex" onClick={() => cmd({ op: "reload" })}><RotateCw className="h-4 w-4" /></Button>
        <Input value={url} placeholder="address or search" type="url" inputMode="url" enterKeyHint="go" autoCapitalize="none" autoCorrect="off" spellCheck={false} onFocus={() => { editing.current = true; }} onBlur={() => { editing.current = false; }} onChange={e => setUrl(e.target.value)} onKeyDown={e => e.key === "Enter" && go()} />
        <Button size="sm" onClick={go}>Go</Button>
        <Button size="sm" variant="outline" title={`Bring the ${info.app || "browser"} window forward`} aria-label="Bring the browser window forward" onClick={() => epost("/app", { op: "focus", name: info.app || "Google Chrome" })}><AppWindow className="h-4 w-4" /><span className="hidden sm:inline">Window</span></Button>
        <Badge className="hidden sm:inline-flex" tone={info.up ? (info.fresh ? "ok" : "note") : "warn"}>{!info.up ? "closed" : info.fresh ? "live" : "waiting"}</Badge>
      </div>
      <div tabIndex={0} className="relative grid min-h-0 flex-1 cursor-default place-items-center overflow-hidden bg-black outline-none focus:ring-2 focus:ring-primary/40"
        onClick={e => { const p = point(e); if (p) cmd({ op: "click", ...p, count: 1 }); }}
        onDoubleClick={e => { const p = point(e); if (p) cmd({ op: "click", ...p, count: 2 }); }}
        onWheel={e => { const p = point(e); if (p) cmd({ op: "scroll", ...p, dy: Math.round(e.deltaY * 2) }); }}
        onKeyDown={e => { if (e.metaKey || e.ctrlKey) return; if (SPECIAL[e.key]) { e.preventDefault(); cmd({ op: "key", key: SPECIAL[e.key] }); } else if (e.key.length === 1) { e.preventDefault(); cmd({ op: "type", text: e.key }); } }}>
        {info.up && src ? <img ref={imgRef} src={src} alt="" draggable={false} className="max-h-full max-w-full select-none" /> : <div className="px-6 text-center text-sm text-muted-foreground">The browser is not open. Type an address and press Go, or ask the agent to open a page.</div>}
      </div>
      <div className="truncate border-t border-border px-3 py-1.5 text-xs text-muted-foreground"><span className="sm:hidden">{!info.up ? "closed" : info.fresh ? "live" : "waiting"}{(info.title || info.url) ? " · " : ""}</span>{info.title || info.url || ""}</div>
    </div>
  );
}
