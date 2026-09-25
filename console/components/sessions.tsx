"use client";
// Sessions: the record's sessions, one conversation each, with the first line as the title, when it began, when it
// last spoke and how many lines it holds; the current one is marked. Open one to read it as it was said. A new
// session is the owner's call and nobody else's: the button asks first, then sends the very "clear the session" the
// voice line takes from the owner's mouth. The agent never starts one on its own; it has no tool that could.
import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ChevronLeft, ChevronRight, History, Plus } from "lucide-react";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { join } from "./chat";
import { eget, epost } from "@/lib/edge";
import { useMobile } from "@/lib/mobile";
import { cn } from "@/lib/utils";

type Session = { id: string; title: string; started: number; last: number; n: number };
type Line = { id: number; role: string; text: string; t: string; meta: any; at: number };
const STAGE = /<<[^>]*>>|\s*<directions:[^>]*>/g;
const clean = (t: string) => t.replace(STAGE, "").trim();
const day = (t: number) => { const d = new Date(t * 1000), now = new Date(); const y = new Date(now); y.setDate(now.getDate() - 1); return d.toDateString() === now.toDateString() ? "Today" : d.toDateString() === y.toDateString() ? "Yesterday" : d.toLocaleDateString([], { day: "numeric", month: "short" }); };
const clock = (t: number) => new Date(t * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
const ago = (t: number) => { const s = Math.max(0, Date.now() / 1000 - t); return s < 60 ? "just now" : s < 3600 ? `${Math.floor(s / 60)} min ago` : s < 86400 ? `${Math.floor(s / 3600)} h ago` : `${Math.floor(s / 86400)} d ago`; };
const title = (s: Session) => clean(s.title || "").replace(/^\(session start:.*$/s, "") || "A session";

export function Sessions() {
  const [list, setList] = useState<Session[]>([]); const [current, setCurrent] = useState(""); const [live, setLive] = useState(true); const [err, setErr] = useState("");
  const [open, setOpen] = useState<string | null>(null); const [lines, setLines] = useState<Line[] | null>(null); const [asking, setAsking] = useState(false); const [note, setNote] = useState("");
  const mobile = useMobile();
  useEffect(() => {
    let stop = false;
    const tick = async () => {
      if (stop) return;
      try { const d = await eget("/sessions"); setList(d.sessions || []); setCurrent(d.current || ""); setErr(""); } catch { setErr("Troi's server is not answering: start Troi from the Desktop."); }
      try { const s = await eget("/session"); setLive(!!s.live); } catch {}
      setTimeout(tick, 5000);
    };
    tick(); return () => { stop = true; };
  }, []);
  useEffect(() => {                                                  // the opened session, as it was said
    if (!open) { setLines(null); return; } let gone = false; setLines(null);
    eget(`/history?session=${encodeURIComponent(open)}&limit=600`).then(d => {                    // a reply's sentences, one reply (as the conversation shows them)
      if (gone) return;
      const out: Line[] = [];
      for (const l of (d.items || []) as Line[]) { if (l.role === "ctl") continue; const last = out[out.length - 1]; if (l.role === "agent" && last && last.role === "agent" && last.t === l.t) last.text = join(last.text, l.text); else out.push({ ...l }); }
      setLines(out);
    }).catch(() => { if (!gone) setLines([]); });
    return () => { gone = true; };
  }, [open]);
  const fresh = async () => {                                        // the owner's word, and only theirs: the same phrase the voice line takes
    setAsking(false);
    try { const r = await epost("/say", { text: "clear the session" }); setNote(r.ok === false ? (r.error || "Troi did not take the line.") : "Asked. Troi says \"Cleared. Fresh slate.\" when it is done; the new session appears here with its first line."); }
    catch { setNote("Troi's server is not answering."); }
    setTimeout(() => setNote(""), 12000);
  };
  const sel = list.find(s => s.id === open) || null;
  const List = (
    <div className="hairline flex min-h-0 flex-col">
      <div className="flex items-center gap-2 border-b border-border px-4 py-3 text-sm"><History className="h-4 w-4 text-muted-foreground" /><span className="font-semibold">Sessions</span><span className="text-xs text-muted-foreground">{list.length ? `· ${list.length}` : ""}</span>
        <Button size="sm" className="ml-auto" onClick={() => setAsking(v => !v)} disabled={!live} title={live ? "A fresh conversation for Troi; the record and the vault stay" : "Troi is not running"}><Plus className="h-3.5 w-3.5" />New session</Button></div>
      {asking && (
        <div className="border-b border-border bg-accent/30 px-4 py-3 text-sm">
          <div className="font-medium">Start a new session?</div>
          <div className="mt-0.5 text-xs text-muted-foreground">Troi forgets the thread of this conversation and starts clean; the record below and the vault keep everything. This is your call alone: Troi never starts one by itself.</div>
          <div className="mt-2.5 flex gap-2"><Button size="sm" onClick={fresh}>Start a new session</Button><Button size="sm" variant="ghost" onClick={() => setAsking(false)}>Keep this one</Button></div>
        </div>)}
      {note && <div className="border-b border-border px-4 py-2 text-xs text-muted-foreground">{note}</div>}
      <div className="min-h-0 flex-1 overflow-y-auto">
        {list.length === 0 && <div className="px-4 py-8 text-center text-sm text-muted-foreground">{err || "No sessions in the record yet."}</div>}
        {list.map(s => (
          <button key={s.id} type="button" onClick={() => setOpen(s.id)} aria-pressed={open === s.id} className={cn("flex w-full items-start gap-3 border-b border-border/60 px-4 py-3 text-left transition-colors last:border-b-0 hover:bg-accent/40", open === s.id && "bg-accent/50")}>
            <span className="min-w-0 flex-1">
              <span className="flex items-center gap-2"><span className="truncate text-[15px] font-medium md:text-sm">{title(s)}</span>{s.id === current && <Badge tone="ok" className="h-5 px-1.5 text-[10px]">Current</Badge>}</span>
              <span className="mt-0.5 block text-xs text-muted-foreground">{day(s.started)} {clock(s.started)} · last {ago(s.last)} · {s.n} lines</span>
            </span>
            <ChevronRight className="mt-1 h-4 w-4 shrink-0 text-muted-foreground" />
          </button>))}
      </div>
    </div>);
  const Detail = sel && (
    <div className="hairline flex min-h-0 flex-col">
      <div className="flex items-center gap-2 border-b border-border px-4 py-3 text-sm">
        {mobile && <button type="button" onClick={() => setOpen(null)} aria-label="Back to the sessions" className="-ml-1 grid h-8 w-8 place-items-center rounded-full text-muted-foreground"><ChevronLeft className="h-5 w-5" /></button>}
        <span className="min-w-0 flex-1"><span className="block truncate font-semibold">{title(sel)}</span><span className="block text-xs text-muted-foreground">{day(sel.started)} {clock(sel.started)} · {sel.n} lines{sel.id === current ? " · the session Troi is in now" : ""}</span></span>
      </div>
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {lines === null && <div className="text-sm text-muted-foreground">Reading…</div>}
        {lines && lines.length === 0 && <div className="text-sm text-muted-foreground">Nothing said in this session.</div>}
        {lines && lines.map(l => l.role === "you" ? (
          <div key={l.id} className="flex justify-end"><div className="max-w-[82%] rounded-2xl rounded-br-md bg-accent px-3.5 py-2 text-[15px] md:max-w-[72%] md:text-sm"><span className="whitespace-pre-wrap">{l.text}</span>{l.t && <span className="float-right ml-2.5 mt-2 text-[10px] leading-none text-muted-foreground/80">{l.t}</span>}</div></div>
        ) : l.role === "agent" ? (
          <div key={l.id} className="min-w-0 text-[15px] leading-6 md:text-sm"><div className="chat-md"><ReactMarkdown remarkPlugins={[remarkGfm]}>{clean(l.text)}</ReactMarkdown></div>{l.t && <div className="mt-0.5 text-[10px] text-muted-foreground">{l.t}</div>}</div>
        ) : l.role === "card" ? (
          <div key={l.id} className="px-1 text-xs italic text-muted-foreground">a card: {String(l.text || "").replace(/^silo\./, "")}</div>
        ) : <div key={l.id} className="px-1 text-xs italic text-muted-foreground">{l.text}</div>)}
      </div>
    </div>);
  const h = "md:h-[calc(100vh-7.5rem)]";
  if (mobile) return <div className="fill-page">{open && sel ? <div className="flex h-full min-h-0 flex-col">{Detail}</div> : <div className="flex h-full min-h-0 flex-col">{List}</div>}</div>;
  return (
    <div className={cn("mx-auto grid w-full max-w-6xl gap-4", h, open ? "md:grid-cols-[minmax(280px,360px)_1fr]" : "md:grid-cols-[minmax(320px,520px)]")}>
      {List}
      {Detail}
    </div>
  );
}
