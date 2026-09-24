"use client";
// The console: space behind everything, the bar at the bottom, the conversation in its chosen shape.
import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { motion } from "framer-motion";
import { Dock } from "@/components/dock";
import { FloatingChat } from "@/components/floating";
import { Directives } from "@/components/directives";
import { Alerts } from "@/components/alerts";
import { eget, on, talkShape, type Config } from "@/lib/edge";
const Space = dynamic(() => import("@/components/space").then(m => m.Space), { ssr: false });
const CANVAS = ["/face", "/hands", "/files", "/apps", "/vault"];   // pages that are a canvas of their own

export default function ConsoleLayout({ children }: { children: React.ReactNode }) {
  const path = usePathname(); const router = useRouter(); const [cfg, setCfg] = useState<Config | null>(null); const [panelOn, setPanelOn] = useState(true); const [shape, setShape] = useState<"column" | "floating">("column"); const [state, setState] = useState<any>("idle");
  useEffect(() => { eget("/config").then(c => { setCfg(c); document.title = c.name + " Console"; if (c.welcomed === false) router.replace("/welcome"); }).catch(() => {}); setShape(talkShape()); const on = () => setShape(talkShape()); window.addEventListener("silo:shape", on); return () => window.removeEventListener("silo:shape", on); }, []);
  // Troi's "show / hide the conversation": the floating pane appears or goes; in the column shape, showing it opens its page
  useEffect(() => on("panel", (v: boolean) => { setPanelOn(!!v); if (v && talkShape() === "column" && !location.pathname.startsWith("/conversation")) router.push("/conversation"); }), [router]);
  useEffect(() => { let stop = false; const t = async () => { if (stop) return; try { const d = await eget("/state"); setState(d.voice ? d.state : "off"); } catch { setState("off"); } setTimeout(t, 800); }; t(); return () => { stop = true; }; }, []);
  const name = cfg?.name || "Troi"; const onTalk = path.startsWith("/conversation"); const canvas = CANVAS.some(p => path.startsWith(p));
  return (
    <div className="min-h-screen pb-24">
      <Space state={state} view={path.split("/")[1] || "default"} active={!canvas} />{/* always mounted: a remount flashes and reloads the planet; paused under the canvas pages */}
      {/* enter-only, opacity-only: an exit under the app router can leave the next page stuck at opacity 0 */}
      <motion.main key={path} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.35, ease: "easeOut" }} className={canvas ? "fixed inset-0 z-0 bg-black" : "on-space mx-auto max-w-[1800px] px-3 pt-3 sm:px-5 sm:pt-5"}>{children}</motion.main>
      {shape === "floating" && !onTalk && panelOn && <FloatingChat name={name} />}
      <Directives />
      <Alerts />
      <Dock name={name} />
    </div>
  );
}
