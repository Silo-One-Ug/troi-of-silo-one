"use client";
// Agents: who the brain has put on a task, from Claude Code's own record of the session (the Agent tool's calls and
// each subagent's transcript). The brain sits at the top; its delegations hang below it, the live ones ringed. A tap
// opens the agent's card: the role and the task, what it is doing now, its steps, its latest words and, once it is
// done, its report, with the brief it was given folded underneath. Nothing here is a control: the brain decides whom
// to send, and names each one for the job ("Role: the task").
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Archive, BookOpen, Bot, Check, ChevronDown, ChevronRight, ClipboardCheck, Compass, Copy, FlaskConical, Map as MapIcon, Orbit, PenLine, Search, Wrench, X } from "lucide-react";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { GFM } from "@/lib/compat";
import { eget, epost } from "@/lib/edge";
import { agentName, useAgentName } from "@/lib/name";
import { useMobile } from "@/lib/mobile";
import { describe } from "@/lib/tools";
import { cn } from "@/lib/utils";

type StepT = { t: number; tool: string; detail?: string };
type A = { id: string; name: string; type: string; prompt: string; started: number; ended: number; status: "active" | "done" | "failed" | "quiet"; agent_id: string; result: string; archived?: boolean; doing?: string; detail?: string; said?: string; turns?: number; seen?: number; model?: string; steps?: StepT[] };
type D = { brain: { name: string; state: string; doing: string; detail?: string }; agents: A[]; session: string; record: boolean; archived?: number };
const ICON: Record<string, any> = { Explore: Search, Plan: MapIcon, "claude-code-guide": BookOpen, "general-purpose": Compass };
const KIND: Record<string, string> = { Explore: "scout", Plan: "planner", "claude-code-guide": "guide", "general-purpose": "hand" };
const STATUS: Record<A["status"], string> = { active: "at work", done: "finished", failed: "failed", quiet: "quiet" };
// the brain names an agent "Role: the task"; the role picks the icon, the task is the title
const ROLES: [RegExp, any][] = [
  [/fix|repair|patch|build|implement|engineer|coder|developer|mechanic/i, Wrench], [/investigat|scout|explor|finder|hunter|detective|searcher/i, Search],
  [/review|audit|inspector|checker|verif/i, ClipboardCheck], [/research|reader|librarian|analyst|historian|summar/i, BookOpen],
  [/test|qa\b|prober|bench/i, FlaskConical], [/writ|draft|editor|scribe|author|reporter/i, PenLine], [/plan|architect|designer/i, MapIcon]];
const parts = (name: string) => { const m = /^([^:]{2,28}):\s*(\S.*)$/s.exec(name || ""); return m ? { role: m[1].trim(), task: m[2].trim() } : { role: "", task: name || "an agent" }; };
const iconOf = (a: A) => { const { role } = parts(a.name); const hit = role ? ROLES.find(([re]) => re.test(role)) : undefined; return hit ? hit[1] : ICON[a.type] || Bot; };
const span = (a: A, now: number) => { const s = Math.max(0, Math.round((a.ended || now) - a.started)); return s < 60 ? `${s}s` : s < 3600 ? `${Math.floor(s / 60)}m ${s % 60}s` : `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`; };
const clock = (t: number) => new Date(t * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
const brainName = (m?: string) => m ? m.replace(/^claude-/, "").replace(/-\d{8}$/, "").replace(/(\d)-(\d)/g, "$1.$2").replace(/-/g, " ") : "";
// what the agent has in its hands right now: its last step, said the way the working line says it
const nowOf = (a: A) => { const s = a.steps && a.steps.length ? a.steps[a.steps.length - 1] : null; return s ? describe(s.tool, s.detail || a.detail) : { Icon: Wrench, label: a.doing || "", note: a.detail, raw: a.detail }; };
const Eyebrow = ({ children, className }: { children: React.ReactNode; className?: string }) => <div className={cn("flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[.12em] text-muted-foreground", className)}>{children}</div>;
const Small = ({ onClick, children }: { onClick: () => void; children: React.ReactNode }) => <button type="button" onClick={onClick} className="ml-auto inline-flex items-center gap-1 font-normal normal-case tracking-normal transition-colors hover:text-foreground">{children}</button>;

function Node({ title, sub, Icon, active, dim, badge, selected, onClick, onArchive }: { title: string; sub: string; Icon: any; active?: boolean; dim?: boolean; badge?: string; selected?: boolean; onClick?: () => void; onArchive?: () => void }) {
  return (
    <div className={cn("group relative w-full md:w-auto", onArchive && "pr-0")}>
      <button type="button" onClick={onClick} aria-pressed={onClick ? !!selected : undefined} disabled={!onClick}
        className={cn("relative flex w-full items-center gap-3 rounded-full border bg-surface/70 px-3 py-2.5 text-left transition-colors md:w-auto md:min-w-[230px] md:max-w-[320px] md:px-4",
          active ? "border-emerald-500/70 shadow-[0_0_0_1px_rgba(16,185,129,.35),0_0_28px_-8px_rgba(16,185,129,.7)]" : "border-border", selected && "bg-accent/50", dim && "opacity-60", onClick ? "hover:border-primary/40" : "cursor-default")}>
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full border border-border bg-background"><Icon className="h-[18px] w-[18px]" /></span>
        <span className="min-w-0 flex-1"><span className="block truncate text-[15px] font-semibold md:text-sm">{title}</span>
          <span className="flex items-center gap-1.5 text-xs text-muted-foreground"><span className={cn("h-1.5 w-1.5 shrink-0 rounded-full", active ? "bg-emerald-400" : "bg-amber-400")} /><span className="truncate">{sub}</span></span></span>
        {badge && <Badge tone={badge === "Active" ? "ok" : badge === "Failed" ? "warn" : "note"} className="absolute -right-1 -top-2.5 h-5 px-2 text-[11px]">{badge}</Badge>}
      </button>
      {onArchive && <button type="button" onClick={e => { e.stopPropagation(); onArchive(); }} title="Archive: off the chart (the record keeps it)" aria-label={`Archive ${title}`}
        className="absolute -right-1.5 -top-1.5 grid h-6 w-6 place-items-center rounded-full border border-border bg-background text-muted-foreground opacity-70 transition hover:text-foreground hover:opacity-100 md:opacity-0 md:group-hover:opacity-100 md:focus-visible:opacity-100"><X className="h-3 w-3" /></button>}
    </div>
  );
}

/** One agent, opened: who it is and where it stands, what it has in its hands, its steps, its words, its report, its brief. */
function AgentCard({ a, now, onArchive, onClose }: { a: A; now: number; onArchive?: () => void; onClose: () => void }) {
  const { role, task } = parts(a.name); const Icon = iconOf(a); const active = a.status === "active";
  const [brief, setBrief] = useState(true); const [allSteps, setAllSteps] = useState(false); const [copied, setCopied] = useState(false);
  useEffect(() => { setBrief(true); setAllSteps(false); setCopied(false); }, [a.id]);
  const steps = a.steps || []; const shownSteps = allSteps ? steps : steps.slice(-6);
  const words = a.prompt ? a.prompt.trim().split(/\s+/).length : 0;
  const copy = async () => { try { await navigator.clipboard.writeText(a.result); setCopied(true); setTimeout(() => setCopied(false), 1500); } catch {} };
  const n = active && a.doing ? nowOf(a) : null;
  return (
    <div className="hairline grid gap-4 p-4 text-sm sm:p-5">
      <div className="flex items-start gap-3.5">
        <span className={cn("grid h-12 w-12 shrink-0 place-items-center rounded-full border bg-background", active ? "border-emerald-500/60" : "border-border")}><Icon className="h-5 w-5" /></span>
        <div className="min-w-0 flex-1">
          {role && <div className="text-[10px] font-semibold uppercase tracking-[.14em] text-muted-foreground">{role}</div>}
          <h2 className="text-balance text-[17px] font-semibold leading-snug">{task}</h2>
          <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
            <Badge tone={active ? "ok" : a.status === "failed" ? "warn" : "note"} className="h-5 gap-1.5 px-2 text-[11px]">{active && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />}{STATUS[a.status]}</Badge>
            <span>{KIND[a.type] || a.type}{a.model ? ` on ${brainName(a.model)}` : ""}</span>
            <span>started {clock(a.started)}{a.ended ? `, finished ${clock(a.ended)}` : ""}</span>
            <span className="tabular-nums">{span(a, now)}</span>
            {a.turns ? <span>{a.turns} turns</span> : null}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          {onArchive && <Button size="sm" variant="ghost" onClick={onArchive} title="Off the chart; the record keeps it"><Archive className="h-3.5 w-3.5" />Archive</Button>}
          <button type="button" onClick={onClose} aria-label="Close" className="grid h-7 w-7 place-items-center rounded-full text-muted-foreground transition hover:bg-accent hover:text-foreground"><X className="h-3.5 w-3.5" /></button>
        </div>
      </div>
      {n && (
        <div className="flex min-w-0 items-center gap-2.5 rounded-xl border border-emerald-500/30 bg-emerald-500/[.06] px-3 py-2" title={n.raw}>
          <n.Icon className="h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" /><span className="shimmer shrink-0 font-medium">{n.label}</span>
          {n.note && <code className="min-w-0 truncate rounded bg-muted px-1.5 py-0.5 text-[11.5px]">{n.note}</code>}
        </div>)}
      {steps.length > 0 && (
        <section className="grid gap-1.5">
          <Eyebrow><span>Steps</span><span className="font-normal normal-case tracking-normal">{steps.length}</span>
            {steps.length > 6 && <Small onClick={() => setAllSteps(v => !v)}>{allSteps ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}{allSteps ? "The last six" : `All ${steps.length}`}</Small>}</Eyebrow>
          <ol className="steps-rail text-xs text-muted-foreground">{shownSteps.map((s, i) => { const k = describe(s.tool, s.detail); return <li key={`${s.t}-${i}`} title={k.raw}><k.Icon className="h-3 w-3 shrink-0 opacity-80" /><span className="shrink-0">{k.label}</span>{k.note && <code className="min-w-0 truncate rounded bg-muted px-1 text-[11px]">{k.note}</code>}</li>; })}</ol>
        </section>)}
      {a.said && (
        <section className="grid gap-1.5"><Eyebrow>{active ? "Latest words" : "Last words"}</Eyebrow>
          <blockquote className="border-l-2 border-border pl-3 text-[13px] leading-relaxed text-muted-foreground">{a.said}</blockquote></section>)}
      {a.result && (
        <section className="grid gap-1.5">
          <Eyebrow><span>{a.status === "failed" ? "What went wrong" : "Reported"}</span><Small onClick={copy}>{copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}{copied ? "Copied" : "Copy"}</Small></Eyebrow>
          <div className="rounded-xl border border-border bg-surface/60 px-4 py-3"><div className="chat-md text-[13px] leading-relaxed"><ReactMarkdown remarkPlugins={GFM}>{a.result}</ReactMarkdown></div></div>
        </section>)}
      {a.prompt && (
        <section className="grid gap-1.5">
          <button type="button" onClick={() => setBrief(v => !v)} aria-expanded={brief} title={brief ? "Fold the brief to two lines" : "The whole brief"} className="flex items-center gap-2 text-left text-[11px] font-semibold uppercase tracking-[.12em] text-muted-foreground transition-colors hover:text-foreground">
            {brief ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}<span>The task</span>{words > 0 && <span className="font-normal normal-case tracking-normal">{words} words</span>}</button>
          {brief ? <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-xl border border-border bg-muted/40 px-4 py-3 font-sans text-[12.5px] leading-relaxed text-muted-foreground">{a.prompt}</pre>
            : <p className="line-clamp-2 text-[13px] text-muted-foreground">{a.prompt}</p>}
        </section>)}
    </div>
  );
}

export function Agents() {
  const fallback = useAgentName();
  const [d, setD] = useState<D | null>(null); const [err, setErr] = useState(""); const [sel, setSel] = useState<string | null>(null); const [now, setNow] = useState(() => Date.now() / 1000);
  const mobile = useMobile(); const wrap = useRef<HTMLDivElement>(null); const brainRef = useRef<HTMLDivElement>(null); const refs = useRef<Record<string, HTMLDivElement | null>>({});
  const [lines, setLines] = useState<string[]>([]); const [box, setBox] = useState({ w: 0, h: 0 }); const [showGone, setShowGone] = useState(false);
  const archive = async (what: string) => { const r = await epost("/agents", { archive: what }); if (r.ok) { setSel(null); try { setD(await eget("/agents")); } catch {} } };
  useEffect(() => {
    let stop = false;
    const tick = async () => { if (stop) return; try { setD(await eget("/agents")); setErr(""); } catch { setErr(`${agentName()}'s server is not answering: start ${agentName()} from the Desktop.`); } setNow(Date.now() / 1000); setTimeout(tick, 2000); };
    tick(); return () => { stop = true; };
  }, []);
  const all = d?.agents || []; const agents = all.filter(a => showGone || !a.archived); const active = agents.filter(a => a.status === "active"); const finished = agents.filter(a => a.status !== "active" && !a.archived);
  const gone = all.filter(a => a.archived).length; const shown = agents.slice(0, 12);   // the newest twelve on the chart
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
  const brain = d?.brain; const name = brain?.name || fallback;
  const brainSub = !brain ? "…" : brain.state === "off" ? "not running" : brain.doing ? `${brain.state} · ${brain.doing}` : brain.state;
  const selA = agents.find(a => a.id === sel) || null;
  return (
    <div className="mx-auto grid w-full max-w-5xl gap-4">
      <div className="hairline p-4 sm:p-6">
        <div className="mb-5 flex flex-wrap items-center gap-x-3 gap-y-2 text-sm"><span className="font-semibold">At work</span>
          <span className="text-muted-foreground">{active.length ? `${active.length} on a task` : "no one on a task"}{finished.length > 0 ? ` · ${finished.length} finished this session` : ""}</span>
          <span className="ml-auto flex items-center gap-2">
            {finished.length > 0 && <Button size="sm" variant="ghost" onClick={() => archive("finished")} title="Off the chart; the record keeps them"><Archive className="h-3.5 w-3.5" />Archive finished</Button>}
            {gone > 0 && <Button size="sm" variant="ghost" onClick={() => setShowGone(v => !v)}>{showGone ? "Hide archived" : `Show archived (${gone})`}</Button>}</span></div>
        <div ref={wrap} className="relative">
          {!mobile && <svg className="pointer-events-none absolute left-0 top-0" width={box.w} height={box.h} aria-hidden>{lines.map((p, i) => <path key={i} d={p} fill="none" stroke="hsl(var(--border))" strokeWidth={1.5} />)}</svg>}
          <div className="relative flex justify-center"><div ref={brainRef} className={mobile ? "w-full max-w-[320px]" : ""}><Node title={name} sub={brainSub} Icon={Orbit} active={!!brain && !["off", "idle"].includes(brain.state)} /></div></div>
          {shown.length > 0 && (
            <div className={cn("relative flex justify-center", mobile ? "mt-5 flex-col items-center gap-y-4" : "mt-12 flex-wrap gap-x-6 gap-y-10")}>
              {shown.map(a => (
                <div key={a.id} ref={el => { refs.current[a.id] = el; }} className={mobile ? "w-full max-w-[320px]" : ""}>
                  <Node title={a.name} sub={`${KIND[a.type] || a.type}${a.status === "active" ? (a.doing ? " · " + a.doing : " · at work") : " · " + span(a, now)}${a.archived ? " · archived" : ""}`} Icon={ICON[a.type] || Bot} active={a.status === "active"} dim={a.status !== "active"}
                    badge={a.status === "active" ? "Active" : a.status === "failed" ? "Failed" : a.status === "quiet" ? "Quiet" : undefined} selected={sel === a.id} onClick={() => setSel(sel === a.id ? null : a.id)} onArchive={a.status !== "active" && !a.archived ? () => archive(a.id) : undefined} />
                </div>))}
            </div>)}
          {shown.length === 0 && <p className="mx-auto mt-8 max-w-md text-center text-sm text-muted-foreground">{err || (d && !d.record ? "No record of this session yet." : `No one is on a task right now. ${name} delegates when a job is big enough, a survey of files, a piece of research, a review, and names each one for the work. They appear here as it does.`)}</p>}
        </div>
      </div>
      {selA && <AgentCard a={selA} now={now} onClose={() => setSel(null)} onArchive={selA.status !== "active" && !selA.archived ? () => archive(selA.id) : undefined} />}
      {agents.length > shown.length && <div className="text-xs text-muted-foreground">And {agents.length - shown.length} earlier this session.</div>}
    </div>
  );
}
