"use client";
// Sessions: the record's sessions, one conversation each, with a title (written for it by a small model once it has a
// few lines, or the owner's first real line until then), when it began, when it last spoke and how many lines it holds;
// the current one is marked. Open one to read it as it was said, rename it with the pencil. A new session is the owner's
// call and nobody else's: the button asks first, then sends the very "clear the session" the voice line takes from the
// owner's mouth. Deleting one is the owner's act too (an unlocked console, as an approval needs), or their yes to the
// agent's request on the Approvals page; a deleted session leaves the list with its lines kept, and Restore brings it
// back. The agent never starts or deletes a session on its own; it has no tool that could.
import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { GFM } from "@/lib/compat";
import { Check, ChevronLeft, ChevronRight, History, Pencil, Plus, RotateCcw, Trash2, X } from "lucide-react";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { join } from "./chat";
import { eget, epost } from "@/lib/edge";
import { agentName, useAgentName } from "@/lib/name";
import { useMobile } from "@/lib/mobile";
import { cn } from "@/lib/utils";

type Session = { id: string; title: string; summary?: string; first?: string; deleted?: number; started: number; last: number; n: number };
type Line = { id: number; role: string; text: string; t: string; meta: any; at: number };
const STAGE = /<<[^>]*>>|\s*<directions:[^>]*>/g;
const clean = (t: string) => t.replace(STAGE, "").trim();
const day = (t: number) => { const d = new Date(t * 1000), now = new Date(); const y = new Date(now); y.setDate(now.getDate() - 1); return d.toDateString() === now.toDateString() ? "Today" : d.toDateString() === y.toDateString() ? "Yesterday" : d.toLocaleDateString([], { day: "numeric", month: "short" }); };
const clock = (t: number) => new Date(t * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
const ago = (t: number) => { const s = Math.max(0, Date.now() / 1000 - t); return s < 60 ? "just now" : s < 3600 ? `${Math.floor(s / 60)} min ago` : s < 86400 ? `${Math.floor(s / 3600)} h ago` : `${Math.floor(s / 86400)} d ago`; };
const title = (s: Session) => clean(s.title || "").replace(/^\(session start:.*$/s, "") || "A session";

export function Sessions() {
  const agent = useAgentName();
  const [list, setList] = useState<Session[]>([]); const [gone, setGone] = useState<Session[]>([]); const [current, setCurrent] = useState(""); const [live, setLive] = useState(true); const [err, setErr] = useState("");
  const [open, setOpen] = useState<string | null>(null); const [lines, setLines] = useState<Line[] | null>(null); const [asking, setAsking] = useState(false); const [note, setNote] = useState("");
  const [showGone, setShowGone] = useState(false); const [confirmDel, setConfirmDel] = useState<string | null>(null); const [renaming, setRenaming] = useState(false); const [draft, setDraft] = useState("");
  const mobile = useMobile();
  const load = async () => {
    try { const d = await eget("/sessions?deleted=1"); setList(d.sessions || []); setGone(d.deleted || []); setCurrent(d.current || ""); setErr(""); } catch { setErr(`${agentName()}'s server is not answering: start ${agentName()} from the Desktop.`); }
    try { const s = await eget("/session"); setLive(!!s.live); } catch {}
  };
  useEffect(() => { let stop = false; const tick = async () => { if (stop) return; await load(); setTimeout(tick, 5000); }; tick(); return () => { stop = true; }; }, []);
  useEffect(() => {                                                  // the opened session, as it was said
    if (!open) { setLines(null); return; } let gone = false; setLines(null); setRenaming(false);
    eget(`/history?session=${encodeURIComponent(open)}&limit=600`).then(d => {                    // a reply's sentences, one reply (as the conversation shows them)
      if (gone) return;
      const out: Line[] = [];
      for (const l of (d.items || []) as Line[]) { if (l.role === "ctl") continue; const last = out[out.length - 1]; if (l.role === "agent" && last && last.role === "agent" && last.t === l.t) last.text = join(last.text, l.text); else out.push({ ...l }); }
      setLines(out);
    }).catch(() => { if (!gone) setLines([]); });
    return () => { gone = true; };
  }, [open]);
  const say = (s: string, ms = 12000) => { setNote(s); setTimeout(() => setNote(n => (n === s ? "" : n)), ms); };
  const fresh = async () => {                                        // the owner's word, and only theirs: the same phrase the voice line takes
    setAsking(false);
    try { const r = await epost("/say", { text: "clear the session" }); say(r.ok === false ? (r.error || `${agentName()} did not take the line.`) : `Asked. ${agentName()} says "Cleared. Fresh slate." when it is done; the new session appears here with its first line.`); }
    catch { say(`${agentName()}'s server is not answering.`); }
  };
  const act = async (body: any, done: string) => {                   // delete, restore, rename: the owner's own hand
    try {
      const r = await epost("/sessions", body);
      if (r.needs_unlock) say("That needs you: unlock with your PIN (the lock in the bar) and try again.");
      else if (!r.ok) say(r.error || `${agentName()}'s server said no.`);
      else { say(done, 5000); await load(); }
      return !!r.ok;
    } catch { say(`${agentName()}'s server is not answering.`); return false; }
  };
  const remove = async (id: string) => { setConfirmDel(null); if (await act({ delete: id }, "Off the list; its lines stay in the record, and Restore brings it back.") && open === id) setOpen(null); };
  const restore = (id: string) => act({ restore: id }, "Back on the list.");
  const rename = async () => { if (!open) return; const t = draft.trim(); if (!t) { setRenaming(false); return; } if (await act({ title: open, text: t }, "Renamed.")) setRenaming(false); };
  const all = [...list, ...(showGone ? gone : [])]; const sel = all.find(s => s.id === open) || null;
  const Row = (s: Session, deleted: boolean) => (
    <div key={s.id} className={cn("border-b border-border/60 last:border-b-0", open === s.id && "bg-accent/50")}>
      <div className="flex items-start gap-2 px-4 py-3">
        <button type="button" onClick={() => setOpen(s.id)} aria-pressed={open === s.id} className="min-w-0 flex-1 text-left">
          <span className="flex items-center gap-2"><span className={cn("truncate text-[15px] font-medium md:text-sm", deleted && "text-muted-foreground line-through")}>{title(s)}</span>{s.id === current && <Badge tone="ok" className="h-5 px-1.5 text-[10px]">Current</Badge>}</span>
          <span className="mt-0.5 block text-xs text-muted-foreground">{day(s.started)} {clock(s.started)} · last {ago(s.last)} · {s.n} lines{deleted && s.deleted ? ` · deleted ${ago(s.deleted)}` : ""}</span>
        </button>
        {deleted ? <button type="button" onClick={() => restore(s.id)} title="Back on the list" aria-label={`Restore ${title(s)}`} className="grid h-8 w-8 shrink-0 place-items-center rounded-full text-muted-foreground hover:bg-accent/60 hover:text-foreground"><RotateCcw className="h-4 w-4" /></button>
          : s.id !== current && <button type="button" onClick={() => setConfirmDel(confirmDel === s.id ? null : s.id)} title="Delete: off the list; its lines stay in the record" aria-label={`Delete ${title(s)}`} className="grid h-8 w-8 shrink-0 place-items-center rounded-full text-muted-foreground hover:bg-accent/60 hover:text-foreground"><Trash2 className="h-4 w-4" /></button>}
        <button type="button" onClick={() => setOpen(s.id)} aria-label={`Open ${title(s)}`} className="grid h-8 w-8 shrink-0 place-items-center text-muted-foreground"><ChevronRight className="h-4 w-4" /></button>
      </div>
      {confirmDel === s.id && (
        <div className="flex flex-wrap items-center gap-2 bg-accent/30 px-4 py-2.5 text-xs">
          <span className="text-muted-foreground">Delete this session? It leaves the list; its lines stay in the record, and Restore brings it back.</span>
          <span className="ml-auto flex gap-2"><Button size="sm" onClick={() => remove(s.id)}>Delete</Button><Button size="sm" variant="ghost" onClick={() => setConfirmDel(null)}>Keep</Button></span>
        </div>)}
    </div>);
  const List = (
    <div className="hairline flex min-h-0 flex-col">
      <div className="flex items-center gap-2 border-b border-border px-4 py-3 text-sm"><History className="h-4 w-4 text-muted-foreground" /><span className="font-semibold">Sessions</span><span className="text-xs text-muted-foreground">{list.length ? `· ${list.length}` : ""}</span>
        <Button size="sm" className="ml-auto" onClick={() => setAsking(v => !v)} disabled={!live} title={live ? `A fresh conversation for ${agent}; the record and the vault stay` : `${agent} is not running`}><Plus className="h-3.5 w-3.5" />New session</Button></div>
      {asking && (
        <div className="border-b border-border bg-accent/30 px-4 py-3 text-sm">
          <div className="font-medium">Start a new session?</div>
          <div className="mt-0.5 text-xs text-muted-foreground">{agent} forgets the thread of this conversation and starts clean; the record below and the vault keep everything. This is your call alone: {agent} never starts one by itself.</div>
          <div className="mt-2.5 flex gap-2"><Button size="sm" onClick={fresh}>Start a new session</Button><Button size="sm" variant="ghost" onClick={() => setAsking(false)}>Keep this one</Button></div>
        </div>)}
      {note && <div className="border-b border-border px-4 py-2 text-xs text-muted-foreground">{note}</div>}
      <div className="min-h-0 flex-1 overflow-y-auto">
        {list.length === 0 && <div className="px-4 py-8 text-center text-sm text-muted-foreground">{err || "No sessions in the record yet."}</div>}
        {list.map(s => Row(s, false))}
        {gone.length > 0 && <button type="button" onClick={() => setShowGone(v => !v)} className="w-full px-4 py-2.5 text-left text-xs text-muted-foreground hover:text-foreground">{showGone ? "Hide the deleted" : `Show the deleted (${gone.length})`}</button>}
        {showGone && gone.map(s => Row(s, true))}
      </div>
      <div className="border-t border-border px-4 py-2 text-[11px] text-muted-foreground">Titles are written for a session once it has a few lines; the pencil renames one. {agent} can ask for a session to be deleted; that lands on Approvals for your yes.</div>
    </div>);
  const Detail = sel && (
    <div className="hairline flex min-h-0 flex-col">
      <div className="flex items-center gap-2 border-b border-border px-4 py-3 text-sm">
        {mobile && <button type="button" onClick={() => setOpen(null)} aria-label="Back to the sessions" className="-ml-1 grid h-8 w-8 place-items-center rounded-full text-muted-foreground"><ChevronLeft className="h-5 w-5" /></button>}
        {renaming ? (
          <form className="flex min-w-0 flex-1 items-center gap-2" onSubmit={e => { e.preventDefault(); rename(); }}>
            <input autoFocus value={draft} onChange={e => setDraft(e.target.value)} onKeyDown={e => { if (e.key === "Escape") setRenaming(false); }} aria-label="The session's title" className="h-8 min-w-0 flex-1 rounded-sm border border-border bg-background px-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30" />
            <button type="submit" aria-label="Save the title" className="grid h-8 w-8 place-items-center rounded-full text-muted-foreground hover:text-foreground"><Check className="h-4 w-4" /></button>
            <button type="button" onClick={() => setRenaming(false)} aria-label="Keep the title" className="grid h-8 w-8 place-items-center rounded-full text-muted-foreground hover:text-foreground"><X className="h-4 w-4" /></button>
          </form>
        ) : (<>
          <span className="min-w-0 flex-1"><span className="block truncate font-semibold">{title(sel)}</span><span className="block text-xs text-muted-foreground">{day(sel.started)} {clock(sel.started)} · {sel.n} lines{sel.id === current ? ` · the session ${agent} is in now` : sel.deleted ? " · deleted" : ""}</span></span>
          <button type="button" onClick={() => { setDraft(title(sel)); setRenaming(true); }} title="Rename" aria-label="Rename the session" className="grid h-8 w-8 shrink-0 place-items-center rounded-full text-muted-foreground hover:bg-accent/60 hover:text-foreground"><Pencil className="h-4 w-4" /></button>
        </>)}
      </div>
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {lines === null && <div className="text-sm text-muted-foreground">Reading…</div>}
        {lines && lines.length === 0 && <div className="text-sm text-muted-foreground">Nothing said in this session.</div>}
        {lines && lines.map(l => l.role === "you" ? (
          <div key={l.id} className="flex justify-end"><div className="max-w-[82%] rounded-2xl rounded-br-md bg-accent px-3.5 py-2 text-[15px] md:max-w-[72%] md:text-sm"><span className="whitespace-pre-wrap">{l.text}</span>{l.t && <span className="float-right ml-2.5 mt-2 text-[10px] leading-none text-muted-foreground/80">{l.t}</span>}</div></div>
        ) : l.role === "agent" ? (
          <div key={l.id} className="min-w-0 text-[15px] leading-6 md:text-sm"><div className="chat-md"><ReactMarkdown remarkPlugins={GFM}>{clean(l.text)}</ReactMarkdown></div>{l.t && <div className="mt-0.5 text-[10px] text-muted-foreground">{l.t}</div>}</div>
        ) : l.role === "card" ? (
          <div key={l.id} className="px-1 text-xs italic text-muted-foreground">a card: {String(l.text || "").replace(/^silo\./, "")}</div>
        ) : <div key={l.id} className="px-1 text-xs italic text-muted-foreground">{l.text}</div>)}
      </div>
    </div>);
  const h = "md:h-[calc(100vh-7.5rem)]";
  if (mobile) return <div className="fill-page">{open && sel ? <div className="flex h-full min-h-0 flex-col">{Detail}</div> : <div className="flex h-full min-h-0 flex-col">{List}</div>}</div>;
  return (
    <div className={cn("mx-auto grid w-full max-w-6xl gap-4", h, open && sel ? "md:grid-cols-[minmax(300px,380px)_1fr]" : "md:grid-cols-[minmax(320px,560px)]")}>
      {List}
      {Detail}
    </div>
  );
}
