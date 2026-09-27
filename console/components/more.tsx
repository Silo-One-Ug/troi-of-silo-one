"use client";
// More: everything the desktop bar shows that does not earn a tab on the phone, as grouped lists. The agent's pages
// (Modes, Routines, Reports, Eyes, Browser), this phone's own settings (notifications, appearance, the lock) and the
// way back to the welcome. Nothing the desktop can do is missing here.
import Link from "next/link";
import { useEffect, useState } from "react";
import { Bell, ChevronRight, Clock, Eye, FileText, Globe, History, Lock, Monitor, Moon, Music, Network, SlidersHorizontal, Sparkles, Sun, Unlock } from "lucide-react";
import { Switch } from "./ui/switch";
import { notifyOn, setNotify } from "./alerts";
import { setWorkSound, workSoundOn } from "./sounds";
import { LockButton, useUnlocked } from "./mobile/bars";
import { getTheme, setTheme, type Theme } from "@/lib/theme";
import { eget } from "@/lib/edge";
import { DEFAULT_NAME, agentName, rememberName } from "@/lib/name";
import { cn } from "@/lib/utils";

const PAGES = [
  { href: "/modes", title: "Modes", note: "Permissions, microphone, wake word, model, eyes, voice", Icon: SlidersHorizontal },
  { href: "/routines", title: "Routines", note: "What runs on a clock, and the reminders", Icon: Clock },
  { href: "/reports", title: "Reports", note: "The end-of-day reports", Icon: FileText },
  { href: "/eyes", title: "Eyes", note: "What it sees, the hands switch, face ID", Icon: Eye },
  { href: "/browser", title: "Browser", note: "Its browser, live; take over when a site needs you", Icon: Globe },
  { href: "/agents", title: "Agents", note: "Who it has put on a task, and how each is doing", Icon: Network },
  { href: "/sessions", title: "Sessions", note: "Every conversation in the record; a new one when you say so", Icon: History },
] as const;
const THEMES: [Theme, string, any][] = [["system", "Auto", Monitor], ["light", "Light", Sun], ["dark", "Dark", Moon]];

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="grid gap-1.5"><div className="px-4 text-[12px] font-semibold uppercase tracking-wider text-muted-foreground">{title}</div><div className="hairline divide-y divide-border overflow-hidden rounded-2xl">{children}</div></section>;
}
const Row = ({ Icon, title, note, right, onClick, href }: { Icon: any; title: string; note?: string; right?: React.ReactNode; onClick?: () => void; href?: string }) => {
  const inner = (<>
    <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-accent text-accent-foreground"><Icon className="h-[18px] w-[18px]" /></span>
    <span className="min-w-0 flex-1"><span className="block text-[16px]">{title}</span>{note && <span className="block truncate text-[13px] text-muted-foreground">{note}</span>}</span>
    {right}
  </>);
  const cls = "flex w-full items-center gap-3.5 px-4 py-3 text-left transition-colors active:bg-surface";
  return href ? <Link href={href} className={cls}>{inner}</Link> : <button type="button" onClick={onClick} className={cls}>{inner}</button>;
};

export function More() {
  const [bell, setBell] = useState(false); const [snd, setSnd] = useState(true); const [theme, setThemeState] = useState<Theme>("system"); const [name, setName] = useState(DEFAULT_NAME); const unlocked = useUnlocked();
  useEffect(() => { setBell(notifyOn()); setSnd(workSoundOn()); setThemeState(getTheme()); setName(agentName()); eget("/config").then(c => { rememberName(c.name); setName(c.name || agentName()); }).catch(() => {}); }, []);
  const toggleBell = async (on: boolean) => {
    if (!on) { setNotify(false); setBell(false); return; }
    if (!("Notification" in window)) return;
    const p = Notification.permission === "granted" ? "granted" : await Notification.requestPermission();
    if (p !== "granted") return;
    setNotify(true); setBell(true); try { new Notification(name, { body: "Notifications are on.", tag: "troi-hello", silent: true }); } catch {}
  };
  return (
    <div className="mx-auto grid w-full max-w-md gap-6">
      <Group title={name}>{PAGES.map(p => <Row key={p.href} href={p.href} Icon={p.Icon} title={p.title} note={p.note} right={<ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />} />)}</Group>
      <Group title="This phone">
        <div className="flex items-center gap-3.5 px-4 py-3"><span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-accent text-accent-foreground"><Bell className="h-[18px] w-[18px]" /></span><span className="min-w-0 flex-1"><span className="block text-[16px]">Notifications</span><span className="block text-[13px] text-muted-foreground">Approvals and reminders; replies while you are elsewhere</span></span><Switch checked={bell} onCheckedChange={toggleBell} aria-label="Notifications" /></div>
        <div className="flex items-center gap-3.5 px-4 py-3"><span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-accent text-accent-foreground"><Music className="h-[18px] w-[18px]" /></span><span className="min-w-0 flex-1"><span className="block text-[16px]">Sounds while it works</span><span className="block text-[13px] text-muted-foreground">A soft pad while {name} works, a chime when it is done</span></span><Switch checked={snd} onCheckedChange={v => { setSnd(v); setWorkSound(v); }} aria-label="Sounds while it works" /></div>
        <div className="grid gap-2 px-4 py-3"><div className="flex items-center gap-3.5"><span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-accent text-accent-foreground"><Sun className="h-[18px] w-[18px]" /></span><span className="text-[16px]">Appearance</span></div>
          <div className="grid grid-cols-3 rounded-xl bg-muted p-1 text-[14px] font-medium" role="radiogroup" aria-label="Appearance">{THEMES.map(([t, l, I]) => <button key={t} role="radio" aria-checked={theme === t} onClick={() => { setTheme(t); setThemeState(t); }} className={cn("flex h-9 items-center justify-center gap-1.5 rounded-lg transition-colors", theme === t ? "bg-background shadow-sm" : "text-muted-foreground")}><I className="h-4 w-4" />{l}</button>)}</div></div>
        <div className="flex items-center gap-3.5 px-4 py-2 pr-2"><span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-accent text-accent-foreground">{unlocked ? <Unlock className="h-[18px] w-[18px]" /> : <Lock className="h-[18px] w-[18px]" />}</span><span className="min-w-0 flex-1"><span className="block text-[16px]">{unlocked ? "Unlocked" : "Locked"}</span><span className="block text-[13px] text-muted-foreground">{unlocked ? "Protected changes go through for fifteen minutes" : "Your PIN approves protected changes"}</span></span><LockButton /></div>
      </Group>
      <Group title="Setup">
        <Row href="/welcome?step=setup" Icon={Sparkles} title="Welcome and setup" note="Your name, this Mac, memory, voice, phone, PIN" right={<ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />} />
      </Group>
      <p className="px-4 text-center text-[12px] text-muted-foreground">Troi of Silo One · the console on your phone. Everything here is the same Troi as on the Mac.</p>
    </div>
  );
}
