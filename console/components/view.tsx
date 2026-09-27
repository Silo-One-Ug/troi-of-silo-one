"use client";
// The surfaces that are canvases of their own (the galaxies, the vault wall, the hands board, the face): embedded
// whole, filling the window edge to edge; the bar floats over them. They keep every gesture they have.
import { useEffect, useState } from "react";
import { Lock } from "lucide-react";
import { cn } from "@/lib/utils";
import { edgeUrl, eget, emit, epost, on, unlockToken, type Config } from "@/lib/edge";
import { agentName } from "@/lib/name";
import { isMobile } from "@/lib/mobile";
import { UnlockBox } from "./approvals";

export function View({ kind }: { kind: "face" | "hands" | "files" | "apps" | "vault" }) {
  const [c, setC] = useState<Config | null>(null); const [ready, setReady] = useState(false); const [path, setPath] = useState(""); const [mobile, setMobile] = useState<boolean | null>(null);
  useEffect(() => { setMobile(isMobile()); eget("/config").then(setC).catch(() => {}); try { setPath(new URLSearchParams(location.search).get("path") || ""); } catch {} }, []);   // the frame waits for this: known once, loaded once (and nothing is rendered on the server that the browser would redo)
  const galaxy = kind === "files" || kind === "apps" || kind === "vault";
  const [tok, setTok] = useState("");                             // the console's unlock token, followed: set by the PIN box, gone when its fifteen minutes end
  useEffect(() => {
    if (kind !== "vault") return;
    const check = () => setTok(unlockToken()); check();
    const t = setInterval(check, 5000); addEventListener("silo:unlock", check);
    return () => { clearInterval(t); removeEventListener("silo:unlock", check); };
  }, [kind]);
  useEffect(() => {                                               // the galaxy's "Ask Troi about it" (only from the galaxy's own origin)
    const h = (e: MessageEvent) => {
      let from = ""; try { from = new URL(edgeUrl()).origin; } catch {}
      const m = e.data || {};
      if (e.origin === from && m.troi === "ask" && typeof m.text === "string" && m.text) { epost("/say", { text: m.text }); epost("/ui", { hint: `Asked ${c?.name || agentName()} to look at it.` }); }
      if (m.troi === "hands" && typeof m.on === "boolean") { try { localStorage.setItem("silo.hands", m.on ? "1" : "0"); } catch {} emit("hands", m.on); }   // the board's own Hands button: the console's switch follows
    };
    addEventListener("message", h); return () => removeEventListener("message", h);
  }, [c]);
  useEffect(() => {                                               // the board follows the console's theme, light or dark
    if (kind !== "hands" || !ready) return;
    const post = () => { const f = document.querySelector("iframe[data-view]") as HTMLIFrameElement | null; f?.contentWindow?.postMessage({ theme: document.documentElement.classList.contains("dark") ? "dark" : "light" }, "*"); };
    const t = setTimeout(post, 400); const mo = new MutationObserver(post); mo.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => { clearTimeout(t); mo.disconnect(); };
  }, [kind, ready]);
  useEffect(() => on("hands", (v: boolean) => {                  // the hands switch, live: the galaxies' hand tracking (the board has no camera)
    const f = document.querySelector("iframe[data-view]") as HTMLIFrameElement | null;
    f?.contentWindow?.postMessage({ hands: !!v }, "*"); f?.contentWindow?.postMessage({ boardCamera: v ? "on" : "off" }, "*");
  }), []);
  // the face and the board are served by the Mac: from a phone, the Mac is the host the page came from, not 127.0.0.1, over the
  // page's own scheme (https through Tailscale's serve rules for 8790 and 8794: a browser blocks a plain-http frame inside an https page)
  const onMac = (u?: string) => { if (!u) return u; try { const h = location.hostname; return h === "localhost" || h === "127.0.0.1" ? u : u.replace(/^https?:\/\/(127\.0\.0\.1|localhost)(?=[:/])/, location.protocol + "//" + h); } catch { return u; } };
  // the board is told the theme in its address, so its first frame is already the right one (live changes follow by message)
  const boardTheme = typeof document !== "undefined" && document.documentElement.classList.contains("dark") ? "dark" : "light";
  const withTheme = (u?: string) => u ? u + (u.includes("?") ? "&" : "?") + "theme=" + boardTheme : u;
  const src = kind === "face" ? onMac(c?.face) : kind === "hands" ? withTheme(onMac(c?.hands)) : `${edgeUrl()}/galaxy.html?safe=0&mode=${kind}${kind !== "vault" ? "&bg=deep" : ""}${mobile ? "&mobile=1" : ""}${kind === "vault" && c?.vault ? "&vault=" + encodeURIComponent(c.vault) : ""}${kind === "files" && path ? "&path=" + encodeURIComponent(path) : ""}`;
  if (!src || mobile === null) return <div className="grid h-full place-items-center bg-black text-sm text-muted-foreground">…</div>;
  // the vault is the owner's: with a PIN set, its wall stays blurred and untouchable until the console is unlocked (the token
  // the bar's PIN box keeps, for fifteen minutes); the box sits on the blur itself. Until the settings are known, blurred too.
  const locked = kind === "vault" && (c === null || !!c.guarded) && !tok;
  // the frame fades in once it has painted: no blank frame between pages
  // data-galaxy / data-ready: Troi's commands (focus, refresh, hands) are posted into the galaxy once it has loaded
  const frame = <iframe key={src} src={src} title={kind} data-view={kind} data-galaxy={galaxy ? "1" : undefined} data-ready={ready ? "1" : undefined} allow="camera; microphone; autoplay; fullscreen" onLoad={e => { setReady(true); try { if (localStorage.getItem("silo.hands") === "1") setTimeout(() => { (e.target as HTMLIFrameElement).contentWindow?.postMessage({ hands: true }, "*"); (e.target as HTMLIFrameElement).contentWindow?.postMessage({ boardCamera: "on" }, "*"); }, 1500); } catch {} }} className={cn("block h-full w-full border-0 bg-black transition-[opacity,filter,transform] duration-500 ease-out", ready ? "opacity-100" : "opacity-0", locked && "pointer-events-none scale-[1.04] blur-2xl saturate-50")} />;
  if (kind !== "vault") return frame;
  return (
    <div className="relative h-full w-full overflow-hidden bg-black">
      {frame}
      {locked && (
        <div className="absolute inset-0 z-10 grid place-items-center bg-black/35 p-6" aria-live="polite">
          <div className="glass w-[min(92vw,380px)] rounded-2xl border border-border p-6 text-center shadow-2xl">
            <Lock className="mx-auto mb-3 h-6 w-6 text-muted-foreground" aria-hidden />
            <div className="text-base font-semibold">The vault is yours</div>
            <p className="mb-4 mt-1 text-sm text-muted-foreground">Your notes stay blurred until the console is unlocked. Your PIN, or your face on the Eyes page.</p>
            <UnlockBox big onDone={() => setTok(unlockToken())} />
          </div>
        </div>)}
    </div>);
}
