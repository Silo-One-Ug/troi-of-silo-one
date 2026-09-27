"use client";
// The bar: the one floating control of the console, as on the native page. Who is speaking and in what state, the
// ground behind everything (face, hands, files, apps, vault), the panes, the bell, the lock. Nothing sits behind it.
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Bell, Clock, Eye, FileText, FolderOpen, Globe, Hand, History, Image as ImageIcon, LayoutGrid, MessageSquare, Network, Orbit, ShieldCheck, SlidersHorizontal, Smile } from "lucide-react";
import { UnlockBox } from "./approvals";
import { notifyOn, notifyWanted, setNotify } from "./alerts";
import { LockButton } from "./mobile/bars";
import { ThemeToggle } from "./theme-toggle";
import { epost, subscribeState, type State } from "@/lib/edge";
import { agentName } from "@/lib/name";
import { useMobile } from "@/lib/mobile";
import { cn } from "@/lib/utils";

const GROUND = [["/face", "Face", Smile], ["/hands", "Hands board", Hand], ["/files", "Files galaxy", FolderOpen], ["/apps", "Apps galaxy", LayoutGrid], ["/vault", "Vault", Orbit]] as const;
const PANES = [["/conversation", "Conversation", MessageSquare], ["/library", "Library", ImageIcon], ["/modes", "Modes", SlidersHorizontal], ["/routines", "Routines", Clock], ["/reports", "Reports", FileText], ["/approvals", "Approvals", ShieldCheck], ["/eyes", "Eyes", Eye], ["/browser", "Browser", Globe], ["/agents", "Agents", Network], ["/sessions", "Sessions", History]] as const;

function Wave({ samples, state }: { samples: number[]; state: string }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => { const c = ref.current; if (!c) return; const x = c.getContext("2d")!; x.clearRect(0, 0, c.width, c.height); const n = 32; const s = samples.length ? samples : Array.from({ length: n }, (_, i) => state === "listening" ? 0.15 + 0.1 * Math.sin(i / 2 + Date.now() / 200) : 0.06); x.fillStyle = state === "speaking" ? "hsl(240 60% 60%)" : state === "listening" ? "hsl(142 60% 45%)" : "hsl(215 16% 60%)"; const w = c.width / n; s.slice(0, n).forEach((v, i) => { const h = Math.max(2, Math.min(1, v * 3) * c.height); x.fillRect(i * w + 1, (c.height - h) / 2, w - 2, h); }); }, [samples, state]);
  return <canvas ref={ref} width={128} height={44} className="h-[22px] w-16" />;
}

export function Dock({ name }: { name: string }) {
  const path = usePathname(); const mobile = useMobile(); const [st, setSt] = useState<State | null>(null); const [pending, setPending] = useState(0); const [bell, setBell] = useState(false);
  const [wanted, setWanted] = useState(false);                        // wanted here, but this browser has not allowed them (yet): the bell says so
  const refreshBell = () => { const on = notifyOn(); setBell(on); setWanted(!on && notifyWanted()); };
  useEffect(() => {                                                  // the browser can allow or block them without a reload (the icon in the address bar): keep looking
    refreshBell(); const t = setInterval(refreshBell, 3000); window.addEventListener("focus", refreshBell);
    return () => { clearInterval(t); window.removeEventListener("focus", refreshBell); };
  }, []);
  const say = (hint: string) => { epost("/ui", { hint }).catch(() => {}); };
  const toggleBell = async () => {                                   // on: approvals and reminders always; replies and Telegram while you are elsewhere
    if (!("Notification" in window)) { say("This window cannot show notifications; turn them on in the console in your browser."); return; }
    if (bell || wanted) { setNotify(false); refreshBell(); return; }
    setNotify(true);                                                 // the wish is kept even when the browser says no now: the bell shows amber until it is allowed
    const p = Notification.permission === "granted" ? "granted" : await Notification.requestPermission();
    refreshBell();
    if (p !== "granted") { say(p === "denied" ? "Your browser has blocked notifications for the console: allow them from the icon in the address bar, and the bell turns green." : "Your browser did not show the permission prompt: click the bell or the lock icon in the address bar and allow notifications."); return; }
    try { new Notification(name || agentName(), { body: "Notifications are on.", tag: "troi-hello", silent: true }); } catch {}
  };
  useEffect(() => { if (mobile) return; return subscribeState(d => { setSt(d); setPending(((d && d.pending) || []).length); }); }, [mobile]);   // a phone has its own bars, and their own poll
  const state = st ? (st.voice ? st.state : "off") : "off";
  const item = (href: string, label: string, Icon: any, badge?: number) => { const on = path.startsWith(href); return (
    <Link key={href} href={href} title={label} aria-label={label} className={cn("relative grid h-9 w-9 shrink-0 place-items-center rounded-md transition-colors", on ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:bg-surface hover:text-foreground")}><Icon className="h-[18px] w-[18px]" />{!!badge && <span className="absolute -right-1 -top-1 grid h-4 min-w-4 place-items-center rounded-full bg-amber-500 px-1 text-[10px] font-semibold text-white">{badge}</span>}</Link>); };
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-2 z-40 hidden justify-center px-2 sm:bottom-4 md:flex">{/* centring lives on this wrapper: Framer Motion owns the bar's transform. Under 768 px the phone's bars take over */}
    <motion.nav initial={{ y: 24, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ type: "spring", stiffness: 300, damping: 30 }} className="glass no-scrollbar pointer-events-auto flex max-w-full items-center gap-2 overflow-x-auto rounded-2xl px-2 py-2 shadow-2xl sm:px-3">{/* narrow windows: the bar scrolls sideways instead of spilling off */}
      <div className="flex shrink-0 items-center gap-2 pr-1 sm:pr-2"><span className={cn("h-2.5 w-2.5 rounded-full", state === "off" ? "bg-muted-foreground/40" : state === "idle" ? "bg-emerald-500" : state === "listening" ? "bg-emerald-400 animate-pulse" : state === "speaking" ? "bg-primary animate-pulse" : "bg-amber-400 animate-pulse")} /><img src="/brand/mark.svg" alt="" className="hidden h-5 w-5 dark:block" /><img src="/brand/mark-on-light.svg" alt="" className="h-5 w-5 dark:hidden" /><b className="text-xs tracking-[.12em]">{name.toUpperCase()}</b><span className="hidden w-14 text-xs text-muted-foreground md:inline">{state}</span><span className="hidden lg:inline"><Wave samples={st?.wave || []} state={state} /></span></div>
      <span className="h-6 w-px shrink-0 bg-border" />
      <div className="flex shrink-0 items-center gap-1">{GROUND.map(([h, l, I]) => item(h, l, I))}</div>
      <span className="h-6 w-px shrink-0 bg-border" />
      <div className="flex shrink-0 items-center gap-1">{PANES.map(([h, l, I]) => item(h, l, I, h === "/approvals" ? pending : h === "/agents" ? (st?.agents || 0) : 0))}</div>
      <span className="h-6 w-px shrink-0 bg-border" />
      <div className="flex shrink-0 items-center gap-2 pl-1"><button title={bell ? "Notifications on" : wanted ? "Notifications wanted, but this browser has not allowed them: allow them from the icon in the address bar" : "Notifications off"} aria-pressed={bell} className={cn("transition-colors", bell ? "text-primary" : wanted ? "text-amber-500" : "text-muted-foreground hover:text-foreground")} onClick={toggleBell}><span className="relative inline-flex"><Bell className={cn("h-4 w-4", bell && "fill-primary/20")} />{(bell || wanted) && <span aria-hidden className={cn("absolute -right-1 -top-1 h-2 w-2 rounded-full ring-2 ring-background", bell ? "bg-emerald-500" : "bg-amber-500")} />}</span></button>
        <div className="hidden lg:block"><UnlockBox /></div><LockButton className="h-9 w-9 lg:hidden" />{/* a tablet has no room for the PIN box in the bar: the lock opens it in a sheet */}
        <ThemeToggle /></div>
    </motion.nav>
    </div>
  );
}
