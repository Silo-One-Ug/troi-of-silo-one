"use client";
// The phone's chrome: a bar at the top (who is speaking and in what state, the page's name, the lock) and five tabs at
// the bottom (Talk, Views, Library, Approvals, More), the way an app on the phone is laid out. On a full-screen view
// (a galaxy, the face, the board) both give way to one pill that brings you back. Everything the desktop bar offers is
// here or one tap away in More; nothing is hidden. Rendered only under 768 px (md:hidden), polled only there.
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { ChevronLeft, Eraser, Image as ImageIcon, Layers, Lock, MessageSquare, MoreHorizontal, ShieldCheck, Unlock } from "lucide-react";
import { Sheet } from "./sheet";
import { UnlockBox } from "../approvals";
import { eget, emit, unlockToken, type State } from "@/lib/edge";
import { useMobile } from "@/lib/mobile";
import { cn } from "@/lib/utils";

export const TITLES: Record<string, string> = { conversation: "Conversation", library: "Library", modes: "Modes", routines: "Routines", reports: "Reports", approvals: "Approvals", eyes: "Eyes", browser: "Browser", agents: "Agents", views: "Views", more: "More" };
const TABS = [
  { href: "/conversation", label: "Talk", Icon: MessageSquare, match: ["/conversation"] },
  { href: "/views", label: "Views", Icon: Layers, match: ["/views", "/face", "/hands", "/files", "/apps", "/vault"] },
  { href: "/library", label: "Library", Icon: ImageIcon, match: ["/library"] },
  { href: "/approvals", label: "Approvals", Icon: ShieldCheck, match: ["/approvals"] },
  { href: "/more", label: "More", Icon: MoreHorizontal, match: ["/more", "/modes", "/routines", "/reports", "/eyes", "/browser", "/agents"] },
] as const;
const STATE_WORD: Record<string, string> = { off: "not running", idle: "idle", listening: "listening", thinking: "thinking", working: "working", speaking: "speaking" };

export function useUnlocked() {
  const [on, setOn] = useState(false);
  useEffect(() => { const t = () => setOn(!!unlockToken()); t(); const i = setInterval(t, 3000); addEventListener("silo:unlock", t); return () => { clearInterval(i); removeEventListener("silo:unlock", t); }; }, []);
  return on;
}

/** The lock: the state at a glance, and the PIN in a sheet (protected changes stay unlocked for fifteen minutes). */
export function LockButton({ className }: { className?: string }) {
  const [open, setOpen] = useState(false); const unlocked = useUnlocked();
  const lockNow = () => { try { localStorage.removeItem("silo.unlock"); } catch {} dispatchEvent(new Event("silo:unlock")); setOpen(false); };
  return (<>
    <button type="button" aria-label={unlocked ? "Unlocked: protected changes go through" : "Unlock with your PIN"} onClick={() => setOpen(true)} className={cn("grid h-11 w-11 place-items-center rounded-full active:bg-surface", className)}>
      {unlocked ? <Unlock className="h-5 w-5 text-emerald-400" /> : <Lock className="h-5 w-5 text-muted-foreground" />}
    </button>
    <Sheet open={open} onClose={() => setOpen(false)} title={unlocked ? "Unlocked" : "Unlock"}>
      {unlocked ? (
        <div className="grid gap-4"><p className="text-[15px] text-muted-foreground">Protected changes go through for fifteen minutes: the Trash, the camera, auto-approve, clearing the session.</p>
          <button onClick={lockNow} className="h-11 rounded-xl border border-border text-[15px] font-medium active:bg-surface">Lock now</button></div>
      ) : (
        <div className="grid gap-4"><p className="text-[15px] text-muted-foreground">Your PIN approves anything protected. Without it, the request goes to your phone on Telegram.</p><UnlockBox big onDone={() => setOpen(false)} /></div>
      )}
    </Sheet>
  </>);
}

/** The top bar and the tabs, from one poll of the agent's state. On a canvas page, the pill back to Views instead. */
export function MobileChrome({ name, title, canvas }: { name: string; title: string; canvas: boolean }) {
  const path = usePathname(); const mobile = useMobile(); const [st, setSt] = useState<State | null>(null);
  useEffect(() => {
    if (!mobile) return; let stop = false;
    const tick = async () => { if (stop) return; try { setSt(await eget("/state")); } catch { setSt(null); } setTimeout(tick, 1000); };
    tick(); return () => { stop = true; };
  }, [mobile]);
  const state = st ? (st.voice ? st.state : "off") : "off"; const pending = (st?.pending || []).length;
  if (canvas) return (
    <Link href="/views" aria-label="Back to the views" className="glass fixed left-4 z-40 flex h-11 items-center gap-1 rounded-full pl-2 pr-4 text-[15px] font-medium shadow-lg md:hidden" style={{ bottom: "calc(env(safe-area-inset-bottom, 0px) + 16px)" }}><ChevronLeft className="h-5 w-5" />Views</Link>
  );
  return (<>
    <header className="glass fixed inset-x-0 top-0 z-40 rounded-none border-x-0 border-t-0 md:hidden" style={{ paddingTop: "env(safe-area-inset-top, 0px)" }}>
      <div className="relative flex h-12 items-center px-2">
        <div className="flex min-w-0 items-center gap-2 pl-2">
          <span className={cn("h-2 w-2 shrink-0 rounded-full", state === "off" ? "bg-muted-foreground/40" : state === "idle" ? "bg-emerald-500" : state === "listening" ? "bg-emerald-400 animate-pulse" : state === "speaking" ? "bg-primary animate-pulse" : "bg-amber-400 animate-pulse")} />
          <span className="text-[11px] font-semibold tracking-[.14em]">{name.toUpperCase()}</span>
        </div>
        <div className="pointer-events-none absolute inset-x-24 text-center"><div className="truncate text-[16px] font-semibold leading-tight">{title}</div><div className="truncate text-[11px] leading-tight text-muted-foreground">{STATE_WORD[state] || state}</div></div>
        <div className="ml-auto flex items-center gap-0.5">{path.startsWith("/conversation") && <button type="button" aria-label="Clear the chat" title="Clear the chat" onClick={() => emit("chat-clear")} className="grid h-10 w-10 place-items-center rounded-full text-muted-foreground active:text-foreground"><Eraser className="h-[18px] w-[18px]" /></button>}<LockButton /></div>
      </div>
    </header>
    <nav aria-label="Sections" className="glass fixed inset-x-0 bottom-0 z-40 rounded-none border-x-0 border-b-0 md:hidden" style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}>
      <div className="flex h-[54px] items-stretch">
        {TABS.map(({ href, label, Icon, match }) => { const on = match.some(m => path.startsWith(m)); const badge = href === "/approvals" ? pending : 0; return (
          <Link key={href} href={href} aria-current={on ? "page" : undefined} className={cn("relative flex flex-1 flex-col items-center justify-center gap-0.5 text-[10px] font-medium transition-colors", on ? "text-primary" : "text-muted-foreground")}>
            <span className="relative"><Icon className="h-[22px] w-[22px]" strokeWidth={on ? 2.2 : 1.8} />{!!badge && <span className="absolute -right-2.5 -top-1.5 grid h-4 min-w-4 place-items-center rounded-full bg-amber-500 px-1 text-[10px] font-semibold text-white">{badge}</span>}</span>
            {label}
          </Link>); })}
      </div>
    </nav>
  </>);
}
