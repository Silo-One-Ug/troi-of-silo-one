"use client";
// The conversation. Typed turns go through AG-UI (POST /agent on the native server) and render as they stream:
// text, the tool in use, cards, approvals. Spoken turns arrive through the voice log (/transcript) and the live
// reply through /state.partial, as the native console shows them. The record comes back from /history on open.
// The owner's lines are bubbles on the right, with initials and the time in the corner; the agent's replies sit
// straight on the page, Markdown rendered, with a copy button and the time under each. While the agent works, one
// line shows the tool in its hands and what it is on (the command, the file, the search, the page); each step takes
// the last one's place, and when the reply comes the line settles into a count of the steps, opened with a click.
// The composer is one card: what is attached shows above the words (a photo as its thumbnail, a file as a small card),
// the + opens a menu (files or photos, a screenshot of the Mac, a file pointed at with @), and on the right stand the
// microphone and the send arrow, which becomes Stop while a reply is under way. The eraser in the header (the top bar on
// a phone) clears the page and remembers where it stood, so a reload stays clear; the record and the session stay. Files
// travel as @ mentions: "@" picks a file on the Mac (the file roots); a file attached, dropped or pasted is uploaded
// to data/blobs/uploads and mentioned the same way; the agent reads what it is pointed at. On a phone the composer is
// a messenger's: the field grows with the lines, the microphone stands where the send button will be until there are
// words, and a voice note goes to the agent's own ears (POST /voice) and comes back as the line it heard.
import { useEffect, useMemo, useRef, useState, type ChangeEvent, type KeyboardEvent as RKeyboardEvent, type ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { HttpAgent } from "@ag-ui/client";
import ReactMarkdown from "react-markdown";
import { GFM } from "@/lib/compat";                       // GFM markdown where the browser can read it (an iOS 15 phone cannot)
import { AppWindow, ArrowDown, ArrowUp, AtSign, Bot, CalendarDays, Check, ChevronDown, ChevronRight, Columns2, Copy, Eraser, FilePen, FilePlus, FileSpreadsheet, FileText, Folder, FolderSearch, Globe, Hand, HardDrive, Link2, ListChecks, Loader2, Mail, Mic, Monitor, Paperclip, PictureInPicture2, Plug, Plus, Send, Square, Terminal, TextSearch, User, Users, Wrench, X } from "lucide-react";
import { Button } from "./ui/button";
import { HeadlinesCard, PicturesGrid } from "./cards";
import { UiBlock } from "./render";
import { rise } from "@/lib/motion";
import { edgeUrl, eget, epost, img, on, setTalkShape, talkShape, type Card, type Row, type State } from "@/lib/edge";
import { useMobile } from "@/lib/mobile";
import { cn } from "@/lib/utils";

type Step = { id: string; tool: string; label: string; detail?: string };
type Msg = { id: string; role: "user" | "assistant" | "note" | "ignored" | "headlines" | "pictures" | "ui" | "steps"; text: string; t?: string; live?: boolean; data?: any; steps?: Step[]; open?: boolean };
type Found = { name: string; path: string; kind: "dir" | "file"; ext: string };
type Attached = { id: string; name: string; path: string; kind: "image" | "file"; url?: string; size?: number; uploading?: boolean };
type Rec = { start: number; media: MediaRecorder; chunks: Blob[]; stream: MediaStream };
const nid = () => Math.random().toString(36).slice(2) + Date.now().toString(36);
const stamp = () => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });

// ---- the tools, each with a few words and a small icon
const NOTE: Record<string, string> = { Bash: "running a command", Read: "reading a file", Write: "writing a file", Edit: "editing a file", MultiEdit: "editing a file", NotebookEdit: "editing a notebook", Glob: "looking through files", Grep: "searching files", WebSearch: "searching the web", WebFetch: "reading a page", Task: "delegating", Agent: "delegating", ToolSearch: "" };
const TOOL_ICON: Record<string, any> = { Bash: Terminal, Read: FileText, Write: FilePlus, Edit: FilePen, MultiEdit: FilePen, NotebookEdit: FilePen, Glob: FolderSearch, Grep: TextSearch, WebSearch: Globe, WebFetch: Link2, Task: Bot, Agent: Bot };
const GOOGLE: [RegExp, string, any][] = [[/calendar|event/, "in Google Calendar", CalendarDays], [/gmail|mail|message|draft|label|thread/, "in Gmail", Mail], [/task/, "in Google Tasks", ListChecks], [/contact|people/, "in Google Contacts", Users], [/drive|doc|sheet|form|slide|file|folder/, "in Google Drive", HardDrive]];
function kind(tool: string): { label: string; Icon: any } {
  if (tool in NOTE) return { label: NOTE[tool], Icon: TOOL_ICON[tool] || Wrench };
  if (!tool.startsWith("mcp__")) return { label: "using " + tool, Icon: Wrench };
  const [, server = "", ...rest] = tool.split("__"); const fn = rest.join(" ").replace(/_/g, " ");
  if (server === "google") { const g = GOOGLE.find(([re]) => re.test(fn)); return g ? { label: g[1], Icon: g[2] } : { label: "in Google", Icon: Plug }; }
  if (/playwright|browser|chrome/.test(server)) return { label: "in the browser", Icon: AppWindow };
  if (/hands/.test(server)) return { label: "using the hands", Icon: Hand };
  return { label: "using " + server.replace(/[-_]/g, " "), Icon: Plug };
}
const fixPics = (v: any) => !v || !Array.isArray(v.items) ? v : { ...v, items: v.items.map((i: any) => ({ ...i, url: i.url && i.url.startsWith("/img?") ? img(i.url) : i.url })) };
function fromCard(c: Card): Msg | null {
  if (c.name === "silo.pictures") return { id: nid(), role: "pictures", text: "", data: fixPics(c.value) };
  if (c.name === "silo.headlines") return { id: nid(), role: "headlines", text: "", data: c.value };
  if (c.name === "silo.ui") return { id: nid(), role: "ui", text: "", data: c.value };
  return null;
}
function fromRow(r: Row): Msg | null {
  if (r.role === "you") return { id: nid(), role: "user", text: r.text, t: r.t };
  if (r.role === "agent") return { id: nid(), role: "assistant", text: r.text, t: r.t };
  if (r.role === "note") return { id: nid(), role: "note", text: r.text };
  if (r.role === "ignored") return { id: nid(), role: "ignored", text: (r.why ? r.why + " · " : "") + r.text };
  if (r.role === "card" && r.meta) return fromCard(r.meta);
  return null;
}
const STAGE = /<<[^>]*>>|\s*<directions:[^>]*>/g;                 // stage directions are for the face, never for the page
const clean = (t: string) => t.replace(STAGE, "").replace(/[ \t]+\n/g, "\n").trim();
/** Consecutive replies of one turn are one reply: it arrives from the record a line at a time, the same minute.
 *  The record keeps a reply's lines but not its blank lines, so a block (a table, a heading, a fence, a list after
 *  prose) gets the blank line Markdown needs; sentences of prose join as one paragraph. */
const block = (l: string) => /^(\||#{1,6}\s|```|>|[-*+]\s|\d+[.)]\s)/.test(l.trim());
const item = (l: string) => /^([-*+]\s|\d+[.)]\s)/.test(l.trim());
export function join(a: string, b: string): string {
  const al = a.split("\n").pop() || "", bl = b.split("\n")[0] || "";
  const gap = (block(al) || block(bl)) && !(item(al) && item(bl));
  return a + (gap ? "\n\n" : "\n") + b;
}
const joinAll = (lines: string[]) => lines.slice(1).reduce((a, b) => join(a, b), lines[0] || "");   // a reply from its lines, as the record gives them
const norm = (s: string) => s.replace(/\s+/g, " ").trim();
function append(ms: Msg[], m: Msg): Msg[] {
  const last = ms[ms.length - 1];
  if (m.role === "assistant" && last && last.role === "assistant" && !last.live && (last.t || "") === (m.t || "")) return [...ms.slice(0, -1), { ...last, text: join(last.text, m.text) }];
  return [...ms, m];
}
const group = (rows: Msg[]) => rows.reduce<Msg[]>((acc, m) => append(acc, m), []);
/** The steps of a turn are one line: a new step joins the live group at the end, or opens one. */
function addStep(ms: Msg[], s: Step): Msg[] {
  const last = ms[ms.length - 1];
  if (last && last.role === "steps" && last.live) return [...ms.slice(0, -1), { ...last, steps: [...(last.steps || []), s] }];
  return [...ms, { id: nid(), role: "steps", text: "", live: true, steps: [s] }];
}
const withDetail = (ms: Msg[], id: string, detail: string) => ms.map(m => m.role === "steps" && m.steps?.some(s => s.id === id) ? { ...m, steps: m.steps!.map(s => s.id === id ? { ...s, detail } : s) } : m);
const settle = (ms: Msg[]) => ms.some(m => m.role === "steps" && m.live) ? ms.map(m => m.role === "steps" && m.live ? { ...m, live: false } : m) : ms;   // the turn's steps are done: the line becomes their count
const Md = ({ text }: { text: string }) => <div className="chat-md"><ReactMarkdown remarkPlugins={GFM}>{text}</ReactMarkdown></div>;
export const globeState = (s: string) => (s === "thinking" || s === "working" ? "thinking" : s === "speaking" ? "speaking" : s === "listening" ? "listening" : "idle") as "idle" | "thinking" | "speaking" | "listening";

// a file mention in a line: @/path, or @"/a path with spaces"
const MENTION = /@"([^"]+)"|@(\/[^\s"]+)/g;
const mention = (p: string) => "@" + (/\s/.test(p) ? `"${p}"` : p);
const short = (p: string) => p.replace(/^\/Users\/[^/]+/, "~");
const base = (p: string) => p.replace(/\/+$/, "").split("/").pop() || p;
const mmss = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
const initials = (n: string) => n.trim().split(/\s+/).filter(Boolean).slice(0, 2).map(w => w[0].toUpperCase()).join("");
const IMAGE = /\.(png|jpe?g|gif|webp|heic|heif|bmp|tiff?|avif|svg)$/i;
const SHEET = /\.(xlsx?|xlsm|csv|numbers|tsv)$/i;
const kb = (n?: number) => !n ? "" : n < 1024 * 1024 ? `${Math.max(1, Math.round(n / 1024))} KB` : `${(n / 1024 / 1024).toFixed(1)} MB`;
function WithMentions({ text }: { text: string }) {          // a line as written, its @ mentions shown as small file chips
  const parts: ReactNode[] = []; const re = new RegExp(MENTION.source, "g"); let last = 0; let m: RegExpExecArray | null;
  while ((m = re.exec(text))) {
    const p = m[1] || m[2]; parts.push(text.slice(last, m.index));
    const nm = base(p).replace(/^\d{4}-\d{2}-\d{2}-\d{6}-/, "");             // an upload's name, without the stamp the Mac keeps it under
    parts.push(<span key={m.index} title={p} className="mx-0.5 inline-flex max-w-full items-center gap-1.5 rounded-lg border border-border/60 bg-background/40 px-1.5 py-0.5 align-middle text-xs">
      {IMAGE.test(p) ? <img src={img(p)} alt="" className="h-8 w-8 shrink-0 rounded-md object-cover" onError={e => { e.currentTarget.style.display = "none"; }} /> : <FileText className="h-3 w-3 shrink-0" />}<span className="truncate">{nm}</span></span>);
    last = m.index + m[0].length;
  }
  parts.push(text.slice(last));
  return <>{parts}</>;
}
async function copyText(t: string) {                          // the clipboard, or the old way over plain http (a phone on the network)
  try { if (navigator.clipboard && window.isSecureContext) { await navigator.clipboard.writeText(t); return true; } } catch {}
  try { const ta = document.createElement("textarea"); ta.value = t; ta.setAttribute("readonly", ""); ta.style.position = "fixed"; ta.style.opacity = "0"; document.body.appendChild(ta); ta.select(); const ok = document.execCommand("copy"); ta.remove(); return ok; } catch { return false; }
}
function CopyButton({ text }: { text: string }) {
  const [ok, setOk] = useState(false);
  return <button type="button" onClick={async () => { if (await copyText(text)) { setOk(true); setTimeout(() => setOk(false), 1500); } }} aria-label="Copy the reply" title={ok ? "Copied" : "Copy"}
    className="grid h-7 w-7 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-accent/60 hover:text-foreground">{ok ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}</button>;
}
function Avatar({ name }: { name: string }) {                // the owner's initials by their lines
  const i = initials(name);
  return <span title={name || undefined} aria-hidden className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-primary/15 text-[11px] font-semibold text-primary ring-1 ring-primary/30">{i || <User className="h-3.5 w-3.5" />}</span>;
}
const Detail = ({ d }: { d?: string }) => d ? <code className="min-w-0 truncate font-mono text-[11px] text-muted-foreground/75" title={d}>{d}</code> : null;
/** The steps of a turn: while it runs, the step under way (shimmering, with what it is on), each replacing the last;
 *  done, the count of steps per kind, opened with a click to the list. */
function Steps({ m, onToggle }: { m: Msg; onToggle: () => void }) {
  const steps = m.steps || []; const cur = steps[steps.length - 1]; if (!cur) return null;
  if (m.live || steps.length === 1) {
    const { Icon } = kind(cur.tool);
    return <div className="flex min-w-0 items-center gap-2 px-1 text-xs text-muted-foreground"><Icon className="h-3.5 w-3.5 shrink-0" /><span className={cn("shrink-0", m.live && "shimmer")}>{cur.label}</span><Detail d={cur.detail} /></div>;
  }
  const counts: [string, number][] = []; for (const s of steps) { const c = counts.find(x => x[0] === s.tool); if (c) c[1]++; else counts.push([s.tool, 1]); }
  return (
    <div className="min-w-0 px-1 text-xs text-muted-foreground">
      <button type="button" onClick={onToggle} aria-expanded={!!m.open} title={m.open ? "Fold the steps away" : "What it did, step by step"} className="flex items-center gap-2.5 rounded-md py-0.5 transition-colors hover:text-foreground">
        {m.open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        {counts.map(([tool, n]) => { const { Icon, label } = kind(tool); return <span key={tool} title={label} className="inline-flex items-center gap-1"><Icon className="h-3.5 w-3.5" />{n}</span>; })}
        <span className="text-muted-foreground/70">{steps.length} steps</span>
      </button>
      {m.open && <ul className="mt-1 space-y-0.5 border-l border-border pl-3">{steps.map(s => { const { Icon } = kind(s.tool); return <li key={s.id} className="flex min-w-0 items-center gap-2"><Icon className="h-3.5 w-3.5 shrink-0" /><span className="shrink-0">{s.label}</span><Detail d={s.detail} /></li>; })}</ul>}
    </div>);
}
/** What is attached, before it is sent: a photo as its thumbnail, anything else as a small card; × leaves it out. */
function Attachment({ f, onRemove }: { f: Attached; onRemove: () => void }) {
  const [broken, setBroken] = useState(false);
  const Icon = SHEET.test(f.name) ? FileSpreadsheet : FileText;
  const pic = f.kind === "image" && f.url && !broken;
  return (
    <div title={f.name} className={cn("relative shrink-0", pic ? "h-[72px] w-[72px]" : "flex max-w-[240px] items-center gap-2.5 rounded-xl border border-border bg-surface/80 py-2 pl-2.5 pr-3")}>
      {pic ? <img src={f.url} alt={f.name} onError={() => setBroken(true)} className="h-full w-full rounded-xl border border-border object-cover" />
        : <><span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-accent/60 text-accent-foreground"><Icon className="h-4 w-4" /></span>
          <span className="min-w-0"><span className="block truncate text-xs font-medium">{f.name}</span><span className="block text-[10px] text-muted-foreground">{f.uploading ? "uploading…" : [f.name.split(".").pop()?.toUpperCase(), kb(f.size)].filter(Boolean).join(" · ")}</span></span></>}
      {f.uploading && pic && <span className="absolute inset-0 grid place-items-center rounded-xl bg-background/50"><Loader2 className="h-4 w-4 animate-spin" /></span>}
      <button type="button" aria-label={`Leave ${f.name} out`} onClick={onRemove} className="absolute -right-1.5 -top-1.5 grid h-5 w-5 place-items-center rounded-full border border-border bg-background text-muted-foreground shadow-sm transition-colors hover:text-foreground"><X className="h-3 w-3" /></button>
    </div>);
}

export function Chat({ name, embedded = false, onState }: { name: string; embedded?: boolean; onState?: (s: string) => void }) {
  const agent = useMemo(() => new HttpAgent({ url: edgeUrl() + "/agent", threadId: "console" }), []);
  const [msgs, setMsgs] = useState<Msg[]>([]); const [text, setText] = useState(""); const [busy, setBusy] = useState(false); const [state, setState] = useState("off"); const [hint, setHint] = useState("");
  const [owner, setOwner] = useState(""); const [cleared, setCleared] = useState(false); const since = useRef<{ pos: number; cpos: number } | null>(null);   // where the chat was cleared: the page shows the record from there
  const [files, setFiles] = useState<Attached[]>([]); const [drag, setDrag] = useState(false); const [menu, setMenu] = useState(false); const [shooting, setShooting] = useState(false);
  const [pick, setPick] = useState<{ start: number; q: string; items: Found[]; i: number; loading: boolean } | null>(null);   // the @ picker: where the mention starts, what is typed so far, what was found
  const [rec, setRec] = useState<Rec | null>(null); const [recT, setRecT] = useState(0); const [hearing, setHearing] = useState(false);
  const [below, setBelow] = useState(0); const [tail, setTail] = useState(true);        // at the end of the conversation, or reading above; lines that arrived meanwhile
  const scroller = useRef<HTMLDivElement>(null); const atBottom = useRef(true); const seen = useRef(0);
  const pos = useRef(0), cpos = useRef(0), skip = useRef<Set<string>>(new Set()), end = useRef<HTMLDivElement>(null), busyRef = useRef(false);
  // a spoken reply on the page: `live` while the brain writes it (the words from the partial; the record's lines kept aside), `settled` for a minute after,
  // so lines of it that the log delivers late still land in the same bubble instead of a second one; `typed` remembers the last typed replies, which come
  // through the voice log again as spoken chunks and must not show twice
  const live = useRef<{ id: string; final: string[]; t?: string } | null>(null), settled = useRef<{ id: string; final: string[]; at: number } | null>(null), typed = useRef<string[]>([]);
  const liveStep = useRef<{ id: string; name: string; detail: string } | null>(null), args = useRef<Record<string, string>>({});   // the step under way in a spoken turn; a typed turn's tool inputs as they stream
  const input = useRef<HTMLTextAreaElement>(null), fileIn = useRef<HTMLInputElement>(null), findT = useRef<any>(0), findN = useRef(0), menuRef = useRef<HTMLDivElement>(null);
  const upsert = (id: string, f: (m: Msg) => Msg) => setMsgs(ms => ms.map(m => m.id === id ? f(m) : m));
  const quiet = (m: Msg) => m.role === "note" || m.role === "ignored" || m.role === "steps";
  useEffect(() => {                                              // follow the conversation only while the owner is at its end
    if (atBottom.current) { end.current?.scrollIntoView({ behavior: "smooth" }); seen.current = msgs.length; setBelow(0); }
    else setBelow(Math.max(0, msgs.filter(m => !quiet(m)).length - seen.current));
  }, [msgs]);
  const onScroll = () => { const el = scroller.current; if (!el) return; const near = el.scrollHeight - el.scrollTop - el.clientHeight < 48; atBottom.current = near; setTail(near); if (near) { seen.current = msgs.length; setBelow(0); } };
  const toBottom = () => { atBottom.current = true; setTail(true); end.current?.scrollIntoView({ behavior: "smooth" }); seen.current = msgs.length; setBelow(0); };
  useEffect(() => { onState?.(state); }, [state, onState]);
  useEffect(() => { const el = input.current; if (!el) return; if (!text) { el.style.height = ""; return; } el.style.height = "auto"; el.style.height = Math.min(el.scrollHeight + (el.offsetHeight - el.clientHeight), 200) + "px"; }, [text]);   // the field grows with the lines, up to seven or so; empty, it is the one line the styles give it
  useEffect(() => { if (!rec) { setRecT(0); return; } const t = setInterval(() => setRecT(Math.floor((Date.now() - rec.start) / 1000)), 500); return () => clearInterval(t); }, [rec]);
  useEffect(() => {                                               // Esc cuts a reply off, as the Stop button does; it also closes the + menu
    const k = (e: KeyboardEvent) => { if (e.key !== "Escape" || e.defaultPrevented) return; if (menu) { setMenu(false); return; } if (state && state !== "idle" && state !== "off") epost("/say", { text: "stop" }); };
    addEventListener("keydown", k); return () => removeEventListener("keydown", k);
  }, [state, menu]);
  const clear = () => {                                           // the page empties and remembers where it stood; the record and the session stay
    since.current = { pos: pos.current, cpos: cpos.current }; try { localStorage.setItem("silo.chatSince", JSON.stringify(since.current)); } catch {}
    live.current = null; liveStep.current = null; setMsgs([]); setCleared(true); setHint(""); setMenu(false);
  };
  const unclear = async () => {                                   // what came before, back on the page
    since.current = null; try { localStorage.removeItem("silo.chatSince"); } catch {} setCleared(false);
    try { const h = await eget("/history?limit=120"); setMsgs(group(h.items.map(fromRow).filter(Boolean) as Msg[])); pos.current = h.pos || 0; cpos.current = h.cpos || 0; } catch {}
  };
  useEffect(() => on("chat-clear", clear), []);                   // the phone's top bar asks the same   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {                                               // the + menu closes on a click anywhere else
    if (!menu) return; const h = (e: MouseEvent) => { if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenu(false); };
    addEventListener("mousedown", h); return () => removeEventListener("mousedown", h);
  }, [menu]);
  useEffect(() => {
    let stop = false;
    (async () => {
      eget("/config").then(c => setOwner(c.owner || "")).catch(() => {});
      try { since.current = JSON.parse(localStorage.getItem("silo.chatSince") || "null"); } catch {}
      try {
        const h = await eget("/history?limit=120"); let rows = h.items as Row[]; pos.current = h.pos || 0; cpos.current = h.cpos || 0;
        const sc = since.current;
        if (sc && sc.pos <= pos.current) {                                              // cleared earlier: only what came after
          try { const d = await eget(`/transcript?pos=${sc.pos}&cpos=${sc.cpos}`); rows = (d.items as Row[]).filter(r => r.role !== "ctl").slice(-120); pos.current = d.pos; if (d.cpos !== undefined) cpos.current = d.cpos; setCleared(true); } catch {}
        } else if (sc) { since.current = null; try { localStorage.removeItem("silo.chatSince"); } catch {} }   // the record started over since then
        setMsgs(group(rows.map(fromRow).filter(Boolean) as Msg[]));
      } catch { setHint("Troi's server is not answering: start Troi from the Desktop."); }
      const poll = async () => {
        if (stop) return;
        try {
          const d = await eget(`/transcript?pos=${pos.current}&cpos=${cpos.current}`); pos.current = d.pos; if (d.cpos !== undefined) cpos.current = d.cpos;
          for (const it of d.items as Row[]) {
            if (it.role === "ctl") continue;
            const key = it.role + "|" + it.text.slice(0, 60); if (skip.current.has(key)) { skip.current.delete(key); continue; }
            if (it.role === "agent") {
              const n = norm(it.text);
              if (n.length >= 8 && typed.current.some(s => s.includes(n))) continue;      // a typed turn's reply, already on the page from its own stream
              if (live.current) { const l = live.current; l.final.push(it.text); l.t = l.t || it.t; continue; }   // the reply under way: the record's lines wait for its end
              if (busyRef.current) continue;                                             // the same reply is streaming into its own place
              const s = settled.current;
              if (s && Date.now() - s.at < 60000) { s.final.push(it.text); upsert(s.id, m => ({ ...m, text: joinAll(s.final), t: m.t || it.t })); continue; }   // a late line of the reply just settled: the whole reply again, as the record has it
            } else settled.current = null;                                                 // the turn moved on: the next reply is a new one
            const m = fromRow(it); if (m) setMsgs(ms => append(m.role === "assistant" ? settle(ms) : ms, m));
          }
          for (const c of (d.cards || []) as Card[]) { const m = fromCard(c); if (m) setMsgs(ms => [...ms, m]); }
        } catch {}
        setTimeout(poll, 700);
      };
      const pollState = async () => {
        if (stop) return;
        try {
          const d: State = await eget("/state"); setState(d.voice ? d.state : "off");
          const part = clean(d.partial || "");
          if (!busyRef.current) {                                    // a spoken turn (or one typed elsewhere): the tool in the brain's hands, from the state
            const tl = d.tool && d.tool.name ? d.tool : null, cur = liveStep.current;
            if (tl && (!cur || cur.name !== tl.name || (tl.detail && cur.detail && tl.detail !== cur.detail))) {
              const id = nid(); liveStep.current = { id, name: tl.name, detail: tl.detail || "" }; const { label } = kind(tl.name);
              if (label) setMsgs(ms => addStep(ms, { id, tool: tl.name, label, detail: tl.detail || undefined }));
            } else if (tl && cur && tl.detail && !cur.detail) { cur.detail = tl.detail; setMsgs(ms => withDetail(ms, cur.id, tl.detail)); }
            else if (!tl && cur) liveStep.current = null;
            if (!tl && !part && (d.state === "idle" || !d.voice)) setMsgs(settle);
          }
          if (part && !busyRef.current) {
            if (!live.current) { const id = nid(); live.current = { id, final: [] }; settled.current = null; setMsgs(ms => [...settle(ms), { id, role: "assistant", text: part, live: true }]); }
            else upsert(live.current.id, m => ({ ...m, text: part }));
          } else if (!part && live.current && !(d.voice && (d.state === "thinking" || (d.tool && d.tool.name)))) {   // the turn is over: a tool still in the brain's hands keeps the reply live, whatever the partial says
            // the reply settles to what the record has of it, whole and in order, so the page reads as it will after a reload; the words as written stand only until a line has arrived
            const l = live.current; live.current = null; settled.current = { id: l.id, final: l.final, at: Date.now() };
            upsert(l.id, m => ({ ...m, live: false, t: m.t || l.t || stamp(), text: l.final.length ? joinAll(l.final) : clean(m.text) }));
          }
        } catch { setState("off"); }
        setTimeout(pollState, 500);
      };
      poll(); pollState();
    })();
    return () => { stop = true; };
  }, []);   // eslint-disable-line react-hooks/exhaustive-deps

  // ---- files: the @ picker over the file roots, and uploads (the clip, a drop, a paste, a screenshot) into data/blobs/uploads
  const search = (start: number, q: string) => {                  // the picker: what is typed after the @, looked up on the Mac
    setPick(p => ({ start, q, items: p?.items || [], i: 0, loading: true }));
    clearTimeout(findT.current); const n = ++findN.current;
    findT.current = setTimeout(async () => {
      let items: Found[] = []; try { items = (await eget(`/find?q=${encodeURIComponent(q)}`)).items || []; } catch {}
      if (n === findN.current) setPick(p => p ? (items.length ? { ...p, items, i: 0, loading: false } : null) : p);   // nothing found: the @ stays as typed, Enter sends
    }, 120);
  };
  const onChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    const v = e.target.value; setText(v);
    const caret = e.target.selectionStart ?? v.length; let start = -1;
    if (pick && v[pick.start] === "@" && caret > pick.start && !v.slice(pick.start + 1, caret).includes("@")) start = pick.start;   // the picker is open: everything since the @ is the search, spaces included
    else { const m = /(^|\s)@([^\s@"]*)$/.exec(v.slice(0, caret)); if (m) start = caret - m[2].length - 1; }
    if (start < 0) { setPick(null); return; }
    search(start, v.slice(start + 1, caret));
  };
  const pointAt = () => {                                          // the menu's "@": an @ at the end of the words, the picker open on the file roots
    const el = input.current; const v = text.length && !/\s$/.test(text) ? text + " @" : text + "@"; setText(v); setMenu(false);
    requestAnimationFrame(() => { if (el) { el.focus(); el.setSelectionRange(v.length, v.length); } }); search(v.length - 1, "");
  };
  const choose = (it: Found) => {
    if (!pick) return;
    const caret = input.current?.selectionStart ?? text.length, before = text.slice(0, pick.start), after = text.slice(caret);
    const ins = mention(it.path + (it.kind === "dir" ? "/" : "")) + " "; setText(before + ins + after); setPick(null);
    requestAnimationFrame(() => { const el = input.current; if (el) { el.focus(); const at = before.length + ins.length; el.setSelectionRange(at, at); } });
  };
  const onKey = (e: RKeyboardEvent<HTMLTextAreaElement>) => {
    if (pick) {
      if (e.key === "ArrowDown") { e.preventDefault(); setPick(p => p ? { ...p, i: Math.min(p.i + 1, Math.max(p.items.length - 1, 0)) } : p); return; }
      if (e.key === "ArrowUp") { e.preventDefault(); setPick(p => p ? { ...p, i: Math.max(p.i - 1, 0) } : p); return; }
      if ((e.key === "Enter" || e.key === "Tab") && pick.items.length) { e.preventDefault(); choose(pick.items[pick.i]); return; }
      if (e.key === "Enter" && pick.loading) { e.preventDefault(); return; }                 // the search is still out: not a send
      if (e.key === "Escape") { e.preventDefault(); setPick(null); return; }
    }
    if (e.key === "Enter" && !e.shiftKey && !mobile) { e.preventDefault(); send(text); }   // on a phone Return makes a new line, as in a messenger; the plane sends
  };
  const drop = (id: string) => setFiles(fs => { const f = fs.find(x => x.id === id); if (f?.url && f.url.startsWith("blob:")) URL.revokeObjectURL(f.url); return fs.filter(x => x.id !== id); });
  const upload = async (list: FileList | File[] | null) => {
    const arr = Array.from(list || []); if (!arr.length) return; setMenu(false);
    for (const f of arr) {
      if (f.size > 60_000_000) { setHint(`${f.name} is over 60 MB.`); continue; }
      const id = nid(); const isPic = f.type.startsWith("image/") || IMAGE.test(f.name);
      setFiles(fs => [...fs, { id, name: f.name, path: "", kind: isPic ? "image" : "file", url: isPic ? URL.createObjectURL(f) : undefined, size: f.size, uploading: true }]);   // shown at once, as it goes up
      try {
        const r = await fetch(edgeUrl() + "/upload", { method: "POST", headers: { "X-Filename": f.name.normalize("NFKD").replace(/[^\x20-\x7E]/g, "_"), "X-Kind": "uploads", "Content-Type": "application/octet-stream" }, body: f });
        const d = await r.json().catch(() => ({}));
        if (d.ok && d.path) { setFiles(fs => fs.map(x => x.id === id ? { ...x, path: d.path, uploading: false } : x)); setHint(""); }
        else { drop(id); setHint(d.error ? `${f.name}: ${d.error}.` : `${f.name} did not upload.`); }
      } catch { drop(id); setHint(`${f.name} did not upload: Troi's server is not answering.`); }
    }
  };
  const screenshot = async () => {                                 // the Mac's screen, captured by the agent's own eyes and attached
    setMenu(false); setShooting(true);
    try {
      const d = await epost("/look", { what: "screen" });
      if (d.ok && d.path) { setFiles(fs => [...fs, { id: nid(), name: base(d.path), path: d.path, kind: "image", url: img(d.path) }]); setHint(""); }
      else setHint(d.error ? `No screenshot: ${d.error}` : "No screenshot.");
    } catch { setHint("No screenshot: Troi's server is not answering."); }
    finally { setShooting(false); }
  };

  // ---- a voice note: the microphone, the agent's own ears, the words sent as the line
  const canMic = typeof navigator !== "undefined" && !!navigator.mediaDevices?.getUserMedia && typeof MediaRecorder !== "undefined";
  const startRec = async () => {
    if (!canMic) { setHint(typeof window !== "undefined" && !window.isSecureContext ? "The microphone needs an https address on a phone: see On your phone in the docs, or send a voice note on Telegram." : "This browser cannot record."); return; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const type = ["audio/mp4", "audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus"].find(t => MediaRecorder.isTypeSupported(t)) || "";
      const media = new MediaRecorder(stream, type ? { mimeType: type } : undefined); const chunks: Blob[] = [];
      media.ondataavailable = e => { if (e.data.size) chunks.push(e.data); };
      media.start(250); setRec({ start: Date.now(), media, chunks, stream }); setHint("");
    } catch { setHint("The microphone was not allowed."); }
  };
  const stopRec = (keep: boolean) => {
    const r = rec; if (!r) return; setRec(null);
    r.media.onstop = () => { r.stream.getTracks().forEach(t => t.stop()); if (keep) sendVoice(new Blob(r.chunks, { type: r.media.mimeType || "audio/webm" })); };
    try { r.media.stop(); } catch { r.stream.getTracks().forEach(t => t.stop()); }
  };
  const sendVoice = async (blob: Blob) => {
    if (blob.size < 2000) { setHint("Too short to hear."); return; }
    setHearing(true); setHint("Listening…");
    try {
      const ext = blob.type.includes("mp4") ? "m4a" : blob.type.includes("ogg") ? "ogg" : "webm";
      const r = await fetch(edgeUrl() + "/voice", { method: "POST", headers: { "X-Filename": `note.${ext}`, "Content-Type": blob.type || "application/octet-stream" }, body: blob });
      const d = await r.json().catch(() => ({}));
      if (d.ok && d.text) { setHint(""); await send(d.text); } else setHint(d.error ? String(d.error) : "I could not make out any words.");
    } catch { setHint("Troi's server is not answering."); }
    finally { setHearing(false); }
  };

  async function send(t: string) {
    const ready = files.filter(f => f.path && !f.uploading);
    const full = [t.trim(), ...ready.map(f => mention(f.path))].filter(Boolean).join(" ");   // attached files go as @ mentions, after the words
    if (!full || busy) return;
    if (busyRef.current) { try { agent.abortRun(); } catch {} }                            // a reply still streaming: let it go; its sentences come through the record
    for (const f of ready) if (f.url && f.url.startsWith("blob:")) URL.revokeObjectURL(f.url);
    setBusy(true); busyRef.current = true; setText(""); setFiles(fs => fs.filter(f => f.uploading)); setPick(null); setMenu(false); setMsgs(ms => [...settle(ms), { id: nid(), role: "user", text: full, t: stamp() }]); skip.current.add("you|" + full.slice(0, 60));
    agent.messages = [{ id: nid(), role: "user", content: full }];
    const said: string[] = []; const free = setTimeout(() => setBusy(false), 6000);          // the field is free once the run has started, or after six seconds whatever happens
    try {
      await agent.runAgent({}, {
        onRunStartedEvent: () => { clearTimeout(free); setBusy(false); },
        onTextMessageStartEvent: ({ event }) => setMsgs(ms => [...settle(ms), { id: event.messageId, role: "assistant", text: "", live: true }]),
        onTextMessageContentEvent: ({ event }) => upsert(event.messageId, m => ({ ...m, text: m.text + event.delta })),
        onTextMessageEndEvent: ({ event }) => setMsgs(ms => ms.flatMap(m => { if (m.id !== event.messageId) return [m]; const txt = clean(m.text); if (!txt) return []; said.push(m.text); return [{ ...m, live: false, t: stamp(), text: txt }]; })),
        onToolCallStartEvent: ({ event }) => { const { label } = kind(event.toolCallName); if (label) setMsgs(ms => addStep(ms, { id: event.toolCallId, tool: event.toolCallName, label })); },
        onToolCallArgsEvent: ({ event }) => { const buf = (args.current[event.toolCallId] = (args.current[event.toolCallId] || "") + event.delta); try { const d = JSON.parse(buf); if (d && typeof d.detail === "string" && d.detail) setMsgs(ms => withDetail(ms, event.toolCallId, d.detail)); } catch {} },   // what the tool is on, once the brain has said
        onToolCallEndEvent: ({ event }) => { delete args.current[event.toolCallId]; },
        onCustomEvent: ({ event }) => { if (event.name === "silo.state") setState(String(event.value)); const m = fromCard({ name: event.name, value: event.value }); if (m) setMsgs(ms => [...ms, m]);
          if (event.name === "silo.approval") setMsgs(ms => [...ms, { id: nid(), role: "note", text: `waiting for your approval: ${(event.value as any).kind} · ${(event.value as any).subject}` }]); },
        onRunErrorEvent: ({ event }) => setMsgs(ms => [...ms, { id: nid(), role: "note", text: event.message }]),
      });
    } catch (e: any) { if (!/abort/i.test(String(e?.name || e?.message || e))) setMsgs(ms => [...ms, { id: nid(), role: "note", text: "The line did not answer: " + (e?.message || e) }]); }
    for (const s of said) { for (const sent of s.replace(/([.!?])\s+/g, "$1\n").split("\n")) skip.current.add("agent|" + sent.slice(0, 60)); typed.current.push(norm(clean(s))); }   // the same words come back through the voice log as spoken chunks: known by their sentences and by the whole text
    typed.current.splice(0, Math.max(0, typed.current.length - 6));
    clearTimeout(free); setBusy(false); busyRef.current = false; setMsgs(settle);
  }
  const shape = talkShape(); const mobile = useMobile(); const talking = busy || (state !== "idle" && state !== "off");
  const uploading = files.some(f => f.uploading) || hearing; const something = text.trim().length > 0 || files.some(f => f.path && !f.uploading);
  const col = embedded ? "w-full" : "mx-auto w-full max-w-[880px]";                       // the window is the page's full width; the words keep a reading column
  const round = "grid h-8 w-8 shrink-0 place-items-center rounded-full transition-colors";
  const previews = files.length > 0 && <div className={cn("flex flex-wrap gap-2.5", mobile ? "pb-2" : "px-3 pt-3")}>{files.map(f => <Attachment key={f.id} f={f} onRemove={() => drop(f.id)} />)}</div>;
  const recording = rec && (
    <div className={cn("flex min-w-0 flex-1 items-center gap-2.5", mobile ? "h-11 rounded-full border border-border bg-background px-4" : "h-10 px-4")}>
      <span className="h-2.5 w-2.5 shrink-0 animate-pulse rounded-full bg-red-500" /><span className="font-mono text-sm tabular-nums">{mmss(recT)}</span><span className="truncate text-sm text-muted-foreground">Recording</span>
      <button type="button" aria-label="Throw the recording away" onClick={() => stopRec(false)} className="ml-auto grid h-8 w-8 shrink-0 place-items-center rounded-full text-muted-foreground hover:text-foreground"><X className="h-4 w-4" /></button>
    </div>);
  const menuItems = [
    { Icon: Paperclip, label: "Add files or photos", onClick: () => { setMenu(false); fileIn.current?.click(); } },
    { Icon: Monitor, label: shooting ? "Taking a screenshot…" : "Take a screenshot", onClick: screenshot, disabled: shooting },
    { Icon: AtSign, label: "Point at a file on the Mac", onClick: pointAt },
  ];
  return (
    <div className={cn("flex h-full min-h-0 flex-col", embedded ? "" : "md:hairline")}>
      {/* the header is the desktop's: on a phone the top bar already says who is speaking and in what state */}
      <div className="hidden items-center gap-2 border-b border-border px-3 py-2 text-sm md:flex"><span className="font-medium">Conversation</span><span className="text-xs text-muted-foreground">· {state}</span>
        <button type="button" onClick={clear} disabled={msgs.length === 0} aria-label="Clear the chat" title="Clear the chat: the page empties; the record and the session stay" className="ml-auto text-muted-foreground hover:text-foreground disabled:opacity-40"><Eraser className="h-4 w-4" /></button>
        <button className="text-muted-foreground hover:text-foreground" title={shape === "column" ? "Make it a floating pane" : "Make it a full column"} onClick={() => { const next = shape === "column" ? "floating" : "column"; setTalkShape(next); try { if (["localhost", "127.0.0.1"].includes(location.hostname)) fetch("http://127.0.0.1:8794/floater", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ shown: next === "floating" }), keepalive: true }).catch(() => {}); } catch {} }}>{shape === "column" ? <PictureInPicture2 className="h-4 w-4" /> : <Columns2 className="h-4 w-4" />}</button></div>
      <div ref={scroller} onScroll={onScroll} className="relative min-h-0 flex-1 overflow-y-auto overflow-x-hidden px-3 py-3 md:px-6 md:py-4">
        {msgs.length === 0 && <div className="grid h-full place-items-center px-6 text-center text-[15px] text-muted-foreground md:text-sm">{cleared ? <span>Cleared. <button type="button" onClick={unclear} className="underline underline-offset-2 hover:text-foreground">Show what came before</button></span> : mobile ? `Nothing said yet. Write to ${name} below; it answers here and out loud on the Mac.` : "Nothing said yet. Hold your talk key and speak, or type below."}</div>}
        <div className={cn(col, "space-y-3")}>
          <AnimatePresence initial={false}>
            {msgs.map(m => m.role === "headlines" ? <HeadlinesCard key={m.id} {...m.data} /> : m.role === "pictures" ? <PicturesGrid key={m.id} {...m.data} /> : m.role === "ui" ? <UiBlock key={m.id} {...m.data} />
              : m.role === "steps" ? <motion.div key={m.id} {...rise}><Steps m={m} onToggle={() => upsert(m.id, x => ({ ...x, open: !x.open }))} /></motion.div>
              : m.role === "user" ? (
                <motion.div key={m.id} {...rise} className="flex items-end justify-end gap-2">
                  <div className="min-w-0 max-w-[82%] rounded-2xl rounded-br-md bg-accent px-3.5 py-2 text-[15px] md:max-w-[72%] md:text-sm"><span className="whitespace-pre-wrap [overflow-wrap:anywhere]"><WithMentions text={m.text} /></span>{m.t && <span className="float-right ml-2.5 mt-2 text-[10px] leading-none text-muted-foreground/80">{m.t}</span>}</div>
                  <Avatar name={owner} />
                </motion.div>)
              : m.role === "assistant" ? (
                <motion.div key={m.id} {...rise} className="min-w-0 text-[15px] leading-6 md:text-sm">
                  <Md text={m.text} />{m.live && <span className="ml-0.5 animate-pulse text-primary">▍</span>}
                  {!m.live && <div className="mt-1 flex items-center gap-1.5"><CopyButton text={m.text} />{m.t && <span className="text-[10px] text-muted-foreground">{m.t}</span>}</div>}
                </motion.div>)
              : <motion.div key={m.id} {...rise} className="px-1 text-xs italic text-muted-foreground">{m.text}</motion.div>)}
          </AnimatePresence>
          <div ref={end} />
        </div>
      </div>
      {!tail && msgs.length > 0 && (
        <div className="pointer-events-none relative"><button type="button" onClick={toBottom} aria-label="Back to the latest" className="glass pointer-events-auto absolute bottom-3 left-1/2 flex h-9 -translate-x-1/2 items-center gap-1.5 rounded-full px-3.5 text-xs font-medium shadow-lg">
          <ArrowDown className="h-4 w-4" />{below > 0 ? `${below} new` : "Latest"}</button></div>)}
      {/* the composer. On the desktop, one card: what is attached, the words, then the + menu, the model, the microphone and the arrow (Stop while a reply is under way). On a phone, a messenger's row. */}
      <form className={cn("relative", mobile ? "border-t border-border p-2.5" : "px-6 pb-4 pt-1")} onSubmit={e => { e.preventDefault(); if (rec) stopRec(true); else send(text); }}
        onDragOver={e => { if (e.dataTransfer.types.includes("Files")) { e.preventDefault(); setDrag(true); } }} onDragLeave={() => setDrag(false)} onDrop={e => { e.preventDefault(); setDrag(false); upload(e.dataTransfer.files); }}>
        <div className={cn(col, "relative")}>
          {pick && pick.items.length > 0 && (
            <div role="listbox" aria-label="Files on the Mac" className="absolute bottom-full left-0 right-0 z-20 mb-2 max-h-60 overflow-y-auto rounded-xl border border-border bg-background/95 p-1 shadow-lg backdrop-blur">
              {pick.items.map((it, k) => (
                <button type="button" role="option" aria-selected={k === pick.i} key={it.path} onMouseDown={e => { e.preventDefault(); choose(it); }} onMouseEnter={() => setPick(p => p ? { ...p, i: k } : p)}
                  className={cn("flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-sm", k === pick.i ? "bg-accent text-accent-foreground" : "text-foreground")}>
                  {it.kind === "dir" ? <Folder className="h-4 w-4 shrink-0 text-muted-foreground" /> : <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />}
                  <span className="truncate">{it.name}</span><span className="ml-auto hidden max-w-[50%] truncate text-xs text-muted-foreground sm:block">{short(it.path).replace(/\/[^/]*$/, "")}</span>
                </button>))}
            </div>)}
          <input ref={fileIn} type="file" multiple className="hidden" onChange={e => { upload(e.target.files); e.target.value = ""; }} />
          {mobile ? (<>
            {previews}
            <div className="flex items-end gap-2">
              {recording || (<>
                <Button type="button" variant="outline" aria-label="Attach a file" title="Attach a file or a photo" disabled={uploading} onClick={() => fileIn.current?.click()} className="h-11 w-11 shrink-0 rounded-full p-0"><Paperclip className={cn("h-[18px] w-[18px]", uploading && "animate-pulse")} /></Button>
                <textarea ref={input} rows={1} value={text} onChange={onChange} onKeyDown={onKey} onBlur={() => setTimeout(() => setPick(null), 150)} onPaste={e => { if (e.clipboardData.files.length) { e.preventDefault(); upload(e.clipboardData.files); } }}
                  placeholder={`Message ${name}`} autoCapitalize="sentences" autoComplete="off" aria-label={`Message ${name}`}
                  className="max-h-40 min-h-11 w-full flex-1 resize-none rounded-[22px] border border-border bg-background px-4 py-2.5 text-base leading-6 placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30" />
              </>)}
              {rec ? <Button type="submit" aria-label="Send the recording" className="h-11 w-11 shrink-0 rounded-full p-0"><Send className="h-5 w-5" /></Button>
                : !something ? <Button type="button" onClick={startRec} disabled={busy || uploading} aria-label="Record a voice note" className="h-11 w-11 shrink-0 rounded-full p-0"><Mic className="h-5 w-5" /></Button>
                : <Button type="submit" disabled={busy || uploading} aria-label="Send" className="h-11 w-11 shrink-0 rounded-full p-0"><Send className="h-5 w-5" /></Button>}
              {talking && <Button type="button" variant="outline" onClick={() => epost("/say", { text: "stop" })} title="Cut the reply off" aria-label="Stop the reply" className="h-11 w-11 shrink-0 rounded-full p-0"><Square className="h-4 w-4" /></Button>}
            </div>
          </>) : (
            <div className={cn("rounded-2xl border bg-background/80 shadow-sm transition-colors focus-within:border-primary/50 focus-within:ring-2 focus-within:ring-primary/15", drag ? "border-primary bg-accent/30" : "border-border")}>
              {previews}
              {recording || <textarea ref={input} rows={1} value={text} onChange={onChange} onKeyDown={onKey} onBlur={() => setTimeout(() => setPick(null), 150)} onPaste={e => { if (e.clipboardData.files.length) { e.preventDefault(); upload(e.clipboardData.files); } }}
                placeholder={`Type to ${name} · @ points at a file`} autoCapitalize="sentences" autoComplete="off" aria-label={`Message ${name}`}
                className="block max-h-[200px] w-full resize-none bg-transparent px-4 pb-1 pt-3 text-sm leading-6 placeholder:text-muted-foreground focus:outline-none" />}
              <div className="flex items-center gap-1 px-2 pb-2 pt-1">
                <div ref={menuRef} className="relative">
                  <button type="button" onClick={() => setMenu(v => !v)} aria-label="Add" aria-haspopup="menu" aria-expanded={menu} title="Add files or photos, a screenshot, a file on the Mac" className={cn(round, "text-muted-foreground hover:bg-accent/60 hover:text-foreground", menu && "bg-accent/60 text-foreground")}><Plus className={cn("h-4 w-4 transition-transform", menu && "rotate-45")} /></button>
                  {menu && (
                    <div role="menu" className="absolute bottom-full left-0 z-30 mb-2 w-64 rounded-xl border border-border bg-background/95 p-1.5 shadow-xl backdrop-blur">
                      {menuItems.map(it => <button key={it.label} type="button" role="menuitem" disabled={it.disabled} onClick={it.onClick} className="flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-left text-sm text-foreground transition-colors hover:bg-accent/60 disabled:opacity-60"><it.Icon className="h-4 w-4 text-muted-foreground" />{it.label}</button>)}
                    </div>)}
                </div>
                <button type="button" onClick={() => fileIn.current?.click()} aria-label="Attach a file" title="Attach a file or a photo: choose one, drop it here, or paste it" className={cn(round, "text-muted-foreground hover:bg-accent/60 hover:text-foreground")}><Paperclip className={cn("h-4 w-4", uploading && "animate-pulse")} /></button>
                {!rec && <button type="button" onClick={startRec} disabled={busy || uploading} aria-label="Record a voice note" title="A voice note: speak, then send it" className={cn(round, "ml-auto text-muted-foreground hover:bg-accent/60 hover:text-foreground disabled:opacity-50")}><Mic className="h-4 w-4" /></button>}
                {rec ? <button type="submit" aria-label="Send the recording" title="Send the recording" className={cn(round, "ml-auto bg-primary text-primary-foreground hover:bg-primary/90")}><ArrowUp className="h-4 w-4" /></button>
                  : talking && !something ? <button type="button" onClick={() => epost("/say", { text: "stop" })} aria-label="Stop the reply" title="Cut the reply off (Esc)" className={cn(round, "border border-border bg-background text-foreground hover:bg-accent/60")}><Square className="h-3.5 w-3.5" /></button>
                  : <button type="submit" disabled={busy || uploading || !something} aria-label="Send" title="Send (Enter)" className={cn(round, "bg-primary text-primary-foreground hover:bg-primary/90 disabled:cursor-default disabled:bg-muted disabled:text-muted-foreground")}><ArrowUp className="h-4 w-4" /></button>}
              </div>
            </div>)}
        </div>
      </form>
      {hint && <div className={cn(col, "px-4 pb-3 text-xs text-muted-foreground md:px-10")}>{hint}</div>}
    </div>
  );
}
