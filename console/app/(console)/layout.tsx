"use client";
// The console: space behind everything, the conversation in its chosen shape, and the chrome for the screen it is on:
// the floating bar on a desktop, a bar and tabs on a phone (components/mobile/bars.tsx; under 768 px).
import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { motion } from "framer-motion";
import { Dock } from "@/components/dock";
import { FloatingChat } from "@/components/floating";
import { Sounds } from "@/components/sounds";
import { Directives } from "@/components/directives";
import { Alerts } from "@/components/alerts";
import { MobileChrome, TITLES } from "@/components/mobile/bars";
import { eget, on, talkShape, type Config } from "@/lib/edge";
import { useMobile } from "@/lib/mobile";
const Space = dynamic(() => import("@/components/space").then(m => m.Space), { ssr: false });
const CANVAS = ["/face", "/hands", "/files", "/apps", "/vault"];   // pages that are a canvas of their own

export default function ConsoleLayout({ children }: { children: React.ReactNode }) {
  const path = usePathname(); const router = useRouter(); const mobile = useMobile(); const [cfg, setCfg] = useState<Config | null>(null); const [panelOn, setPanelOn] = useState(true); const [shape, setShape] = useState<"column" | "floating">("column"); const [state, setState] = useState<any>("idle");
  useEffect(() => { eget("/config").then(c => { setCfg(c); document.title = c.name + " Console"; if (c.welcomed === false) router.replace("/welcome"); }).catch(() => {}); setShape(talkShape()); const on = () => setShape(talkShape()); window.addEventListener("silo:shape", on); return () => window.removeEventListener("silo:shape", on); }, []);
  // Troi's "show / hide the conversation": the floating pane appears or goes; in the column shape, showing it opens its page
  useEffect(() => on("panel", (v: boolean) => { setPanelOn(!!v); if (v && talkShape() === "column" && !location.pathname.startsWith("/conversation")) router.push("/conversation"); }), [router]);
  useEffect(() => { let stop = false; const t = async () => { if (stop) return; try { const d = await eget("/state"); setState(d.voice ? d.state : "off"); } catch { setState("off"); } setTimeout(t, 800); }; t(); return () => { stop = true; }; }, []);
  const name = cfg?.name || "Troi"; const onTalk = path.startsWith("/conversation"); const canvas = CANVAS.some(p => path.startsWith(p)); const section = path.split("/")[1] || "default";
  return (
    <div className="min-h-[100dvh] md:min-h-screen md:pb-24">{/* on a phone the page measures itself in the visible height: 100vh runs under Safari's bars and makes the page scroll */}
      <Space state={state} view={section} active={!canvas} lite={mobile} />{/* always mounted: a remount flashes and reloads the planet; paused under the canvas pages; lighter on a phone */}
      {/* enter-only, opacity-only: an exit under the app router can leave the next page stuck at opacity 0. app-page keeps clear of the phone's bars */}
      <motion.main key={path} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.35, ease: "easeOut" }} className={canvas ? "fixed inset-0 z-0 bg-black" : onTalk ? "app-page on-space mx-auto max-w-[1800px] px-0 pt-0 md:px-5 md:pt-5" : "app-page on-space mx-auto max-w-[1800px] px-3 pt-3 sm:px-5 sm:pt-5"}>{children}</motion.main>
      {shape === "floating" && !onTalk && panelOn && !mobile && <FloatingChat name={name} />}
      <Directives />
      <Alerts />
      <MobileChrome name={name} title={TITLES[section] || name} canvas={canvas} />
      <Sounds state={state} />
      <Dock name={name} />
    </div>
  );
}
