"use client";
// Agents: who the brain has put on a task, from Claude Code's own record of the session (the Agent tool's calls and
// each subagent's transcript). The brain sits at the top; its delegations hang below it, the live ones ringed. A tap
// opens the task and what the agent is doing now. Nothing here is a control: the brain decides whom to send, and names
// each one for the job.
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { BookOpen, Bot, Compass, Map as MapIcon, Orbit, Search } from "lucide-react";
import { Badge } from "./ui/badge";
import { eget } from "@/lib/edge";
import { useMobile } from "@/lib/mobile";
import { cn } from "@/lib/utils";

type A = { id: string; name: string; type: string; prompt: string; started: number; ended: number; status: "active" | "done" | "failed" | "quiet"; agent_id: string; result: string; doing?: string; detail?: string; said?: string; turns?: number; seen?: number };
type D = { brain: { name: string; state: string; doing: string }; agents: A[]; session: string; record: boolean };
const ICON: Record<string, any> = { Explore: Search, Plan: MapIcon, "claude-code-guide": BookOpen, "general-purpose": Compass };
const KIND: Record<string, string> = { Explore: "scout", Plan: "planner", "claude-code-guide": "guide", "general-purpose": "hand" };
const span = (a: A, now: number) => { const s = Math.max(0, Math.round((a.ended || now) - a.started)); return s < 60 ? `${s}s` : s < 3600 ? `${Math.floor(s / 60)}m ${s % 60}s` : `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`; };
const clock = (t: number) => new Date(t * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

function Node({ title, sub, Icon, active, dim, badge, selected, onClick }: { title: string; sub: string; Icon: any; active?: boolean; dim?: boolean; badge?: string; selected?: boolean; onClick?: () => void }) {
  return (
    <button type="button" onClick={onClick} aria-pressed={onClick ? !!selected : undefined} disabled={!onClick}
      className={cn("relative flex w-full items-center gap-3 rounded-full border bg-surface/70 px-3 py-2.5 text-left transition-colors md:w-auto md:min-w-[230px] md:max-w-[320px] md:px-4",
        active ? "border-emerald-500/70 shadow-[0_0_0_1px_rgba(16,185,129,.35),0_0_28px_-8px_rgba(16,185,129,.7)]" : "border-border", selected && "bg-accent/50", dim && "opacity-60", onClick ? "hover:border-primary/40" : "cursor-default")}>
      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full border border-border bg-background"><Icon className="h-[18px] w-[18px]" /></span>
      <span className="min-w-0 flex-1"><span className="block truncate text-[15px] font-semibold md:text-sm">{title}</span>
        <span className="flex items-center gap-1.5 text-xs text-muted-foreground"><span className={cn("h-1.5 w-1.5 shrink-0 rounded-full", active ? "bg-emerald-400" : "bg-amber-400")} /><span className="truncate">{sub}</span></span></span>
      {badge && <Badge tone={badge === "Active" ? "ok" : badge === "Failed" ? "warn" : "note"} className="absolute -right-1 -top-2.5 h-5 px-2 text-[11px]">{badge}</Badge>}
    </button>
  );
}

export function Agents() {
  const [d, setD] = useState<D | null>(null); const [err, setErr] = useState(""); const [sel, setSel] = useState<string | null>(null); const [now, setNow] = useState(() => Date.now() / 1000);
  const mobile = useMobile(); const wrap = useRef<HTMLDivElement>(null); const brainRef = useRef<HTMLDivElement>(null); const refs = useRef<Record<string, HTMLDivElement | null>>({});
  const [lines, setLines] = useState<string[]>([]); const [box, setBox] = useState({ w: 0, h: 0 });
  useEffect(() => {
    let stop = false;
    const tick = async () => { if (stop) return; try { setD(await eget("/agents")); setErr(""); } catch { setErr("Troi's server is not answering: start Troi from the Desktop."); } setNow(Date.now() / 1000); setTimeout(tick, 2000); };
    tick(); return () => { stop = true; };
  }, []);
  const agents = d?.agents || []; const active = agents.filter(a => a.status === "active"); const shown = agents.slice(0, 12);   // the newest twelve on the chart
  // the connectors, measured, so they follow the row wherever it wraps: the brain down to a bus, the bus across, a stub down to each node on the first row
  useLayoutEffect(() => {
    if (mobile) { setLines([]); return; }
    const draw = () => {
      const w = wrap.current, b = brainRef.current; if (!w || !b) return;
      const W = w.getBoundingClientRect(), B = b.getBoundingClientRect(); const bx = B.left + B.width / 2 - W.left, by = B.bottom - W.top;
      const tops = shown.map(a => refs.current[a.id]).filter(Boolean).map(el => { const r = el!.getBoundingClientRect(); return { x: r.left + r.width / 2 - W.left, y: r.top - W.top }; });
      const out: string[] = [];
      if (tops.length) {
        const top = Math.min(...tops.map(t => t.y)); const row = tops.filter(t => t.y - top < 8); const bus = by + Math.max(12, (top - by) / 2); const xs = row.map(t => t.x);
        out.push(`M${bx},${by} V${bus}`, `M${Math.min(...xs, bx)},${bus} H${Math.max(...xs, bx)}`); for (const t of row) out.push(`M${t.x},${bus} V${t.y}`);
      }
      setLines(out); setBox({ w: W.width, h: W.height });
    };
    draw(); const ro = new ResizeObserver(draw); if (wrap.current) ro.observe(wrap.current); return () => ro.disconnect();
  }, [mobile, d]);   // eslint-disable-line react-hooks/exhaustive-deps
  const brain = d?.brain; const name = brain?.name || "Troi";
  const brainSub = !brain ? "…" : brain.state === "off" ? "not running" : brain.doing ? `${brain.state} · ${brain.doing}` : brain.state;
  const selA = agents.find(a => a.id === sel) || null;
  return (
    <div className="mx-auto grid w-full max-w-5xl gap-4">
      <div className="hairline p-4 sm:p-6">
        <div className="mb-5 flex flex-wrap items-baseline gap-x-3 gap-y-1 text-sm"><span className="font-semibold">At work</span>
          <span className="text-muted-foreground">{active.length ? `${active.length} on a task` : "no one on a task"}{agents.length - active.length > 0 ? ` · ${agents.length - active.length} finished this session` : ""}</span></div>
        <div ref={wrap} className="relative">
          {!mobile && <svg className="pointer-events-none absolute left-0 top-0" width={box.w} height={box.h} aria-hidden>{lines.map((p, i) => <path key={i} d={p} fill="none" stroke="hsl(var(--border))" strokeWidth={1.5} />)}</svg>}
          <div className="relative flex justify-center"><div ref={brainRef} className={mobile ? "w-full max-w-[320px]" : ""}><Node title={name} sub={brainSub} Icon={Orbit} active={!!brain && !["off", "idle"].includes(brain.state)} /></div></div>
          {shown.length > 0 && (
            <div className={cn("relative flex justify-center", mobile ? "mt-5 flex-col items-center gap-y-4" : "mt-12 flex-wrap gap-x-6 gap-y-10")}>
              {shown.map(a => (
                <div key={a.id} ref={el => { refs.current[a.id] = el; }} className={mobile ? "w-full max-w-[320px]" : ""}>
                  <Node title={a.name} sub={`${KIND[a.type] || a.type}${a.status === "active" ? (a.doing ? " · " + a.doing : " · at work") : " · " + span(a, now)}`} Icon={ICON[a.type] || Bot} active={a.status === "active"} dim={a.status !== "active"}
                    badge={a.status === "active" ? "Active" : a.status === "failed" ? "Failed" : a.status === "quiet" ? "Quiet" : undefined} selected={sel === a.id} onClick={() => setSel(sel === a.id ? null : a.id)} />
                </div>))}
            </div>)}
          {shown.length === 0 && <p className="mx-auto mt-8 max-w-md text-center text-sm text-muted-foreground">{err || (d && !d.record ? "No record of this session yet." : `No one is on a task right now. ${name} delegates when a job is big enough, a survey of files, a piece of research, a review, and names each one for the work. They appear here as it does.`)}</p>}
        </div>
      </div>
      {selA && (
        <div className="hairline grid gap-3 p-4 text-sm sm:p-5">
          <div className="flex flex-wrap items-center gap-2"><span className="font-semibold">{selA.name}</span><Badge tone={selA.status === "active" ? "ok" : selA.status === "failed" ? "warn" : "note"}>{selA.status}</Badge>
            <span className="text-xs text-muted-foreground">{KIND[selA.type] || selA.type} · started {clock(selA.started)}{selA.ended ? `, finished ${clock(selA.ended)}` : ""} · {span(selA, now)}{selA.turns ? ` · ${selA.turns} turns` : ""}</span></div>
          {selA.doing && <div><span className="text-muted-foreground">Now: </span>{selA.doing}{selA.detail ? <code className="ml-1 rounded bg-muted px-1 text-xs">{selA.detail}</code> : null}</div>}
          {selA.said && <div><span className="text-muted-foreground">Last words: </span>{selA.said}</div>}
          {selA.result && <div><span className="text-muted-foreground">Reported: </span>{selA.result}</div>}
          <div><span className="text-muted-foreground">The task: </span><span className="whitespace-pre-wrap">{selA.prompt}</span></div>
        </div>)}
      {agents.length > shown.length && <div className="text-xs text-muted-foreground">And {agents.length - shown.length} earlier this session.</div>}
    </div>
  );
}
