"use client";
// Troi steers the console with console.sh; each command is a directive in the server's numbered feed (/ui?since=N).
// This follows the feed and acts on every one of them, on whichever page is open: views and places change the page,
// galaxy commands go into the embedded galaxy, the conversation changes shape or hides, hints and tidy and movie
// mode show here. Nothing is consumed on the server, so several open consoles all obey.
import { useEffect, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { eget, emit, setTalkShape } from "@/lib/edge";
import { isMobile } from "@/lib/mobile";

const PLACES = ["conversation", "library", "modes", "routines", "reports", "approvals", "eyes", "browser", "face", "hands", "files", "apps", "vault"];
type D = Record<string, any> & { seq: number };

function toGalaxy(msg: any, tries = 8) {                       // the galaxy frame may still be loading after a page change
  const f = document.querySelector("iframe[data-galaxy]") as HTMLIFrameElement | null;
  if (f?.contentWindow && f.dataset.ready === "1") { f.contentWindow.postMessage(msg, "*"); return; }
  if (tries > 0) setTimeout(() => toGalaxy(msg, tries - 1), 600);
}

export function Directives() {
  const router = useRouter(); const path = usePathname(); const seq = useRef<number | null>(null); const [hint, setHint] = useState(""); const [dim, setDim] = useState(false);
  const go = (p: string) => { if (!path.startsWith("/" + p)) router.push("/" + p); };
  useEffect(() => {
    let stop = false, t: any = null;
    const apply = (d: D) => {
      if (d.go && PLACES.includes(d.go)) go(d.go);
      if (d.view && ["face", "hands", "files", "apps", "vault"].includes(d.view)) go(d.view);
      if (d.vault === "show") go("vault"); if (d.vault === "clear") go("face");
      if (d.files) { if (path.startsWith("/files")) toGalaxy({ files: d.files }); else router.push("/files?path=" + encodeURIComponent(d.files)); }
      if (d.focus) { const inVault = false; if (!path.startsWith("/files") && !path.startsWith("/vault")) go(inVault ? "vault" : "files"); toGalaxy({ focus: d.focus }); }
      if (d.refresh) toGalaxy({ refresh: d.refresh });
      if (d.gestures !== undefined) { try { localStorage.setItem("silo.hands", d.gestures ? "1" : "0"); } catch {} emit("hands", !!d.gestures); }   // the open view passes it on
      if (d.apps === "open") go("apps");
      if (d.images === "open") go("library"); if (d.images === "close" && path.startsWith("/library")) go("conversation");
      for (const k of ["modes", "routines", "approvals", "reports"]) { if (d[k] === "open" || d[k] === "toggle") go(k); if (d[k] === "close" && path.startsWith("/" + k)) go("conversation"); }
      if (d.camera === "open") go("eyes"); if (d.camera === "close" && path.startsWith("/eyes")) go("conversation");
      if (d.browser === "open") go("browser"); if (d.browser === "close" && path.startsWith("/browser")) go("conversation");
      if (d.talk === "column" || d.talk === "floating") { if (isMobile()) go("conversation"); else { setTalkShape(d.talk); if (d.talk === "column") go("conversation"); } }   // a phone has no floating pane: the conversation is its own tab
      if (d.panel === "hide") emit("panel", false); if (d.panel === "show") { emit("panel", true); }
      if (d.tidy) { emit("tidy", true); emit("panel", true); }
      if (d.hint) { setHint(String(d.hint)); clearTimeout(t); t = setTimeout(() => setHint(""), 9000); }
      if (d.dim !== undefined) setDim(!!d.dim);
    };
    const poll = async () => {
      if (stop) return;
      try {
        const f = await eget(`/ui?since=${seq.current ?? -1}`);
        if (seq.current === null) seq.current = f.seq;                         // start from now: old commands are history
        else { (f.items as D[]).forEach(apply); seq.current = f.seq; }
      } catch {}
      setTimeout(poll, 500);
    };
    poll();
    return () => { stop = true; };
  }, [path]);   // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <>
      <AnimatePresence>{hint && <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 8 }} className="glass fixed bottom-24 left-1/2 z-40 max-w-[70vw] -translate-x-1/2 rounded-full px-4 py-2 text-sm">{hint}</motion.div>}</AnimatePresence>
      <AnimatePresence>{dim && <motion.div initial={{ opacity: 0 }} animate={{ opacity: 0.82 }} exit={{ opacity: 0 }} className="pointer-events-none fixed inset-0 z-20 bg-black" />}</AnimatePresence>
    </>
  );
}
