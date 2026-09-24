"use client";
// The conversation. Typed turns go through AG-UI (POST /agent on the native server) and render as they stream:
// text, the tool in use, cards, approvals. Spoken turns arrive through the voice log (/transcript) and the live
// reply through /state.partial, as the native console shows them. The record comes back from /history on open.
// Files travel as @ mentions: "@" in the composer picks a file on the Mac (the file roots), and a file attached,
// dropped or pasted is uploaded to data/blobs/uploads and mentioned the same way; the agent reads what it is pointed at.
// On a phone the composer is a messenger's: the field grows with the lines, the microphone stands where the send
// button will be until there are words, and a voice note goes to the agent's own ears (POST /voice) and comes back
// as the line it heard.
import { useEffect, useMemo, useRef, useState, type ChangeEvent, type KeyboardEvent as RKeyboardEvent, type ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { HttpAgent } from "@ag-ui/client";
import { Columns2, FileText, Folder, Mic, Paperclip, PictureInPicture2, Send, Square, X } from "lucide-react";
import { Button } from "./ui/button";
import { HeadlinesCard, PicturesGrid } from "./cards";
import { UiBlock } from "./render";
import { rise } from "@/lib/motion";
import { edgeUrl, eget, epost, img, setTalkShape, talkShape, type Card, type Row, type State } from "@/lib/edge";
import { useMobile } from "@/lib/mobile";
import { cn } from "@/lib/utils";

type Msg = { id: string; role: "user" | "assistant" | "note" | "ignored" | "headlines" | "pictures" | "ui"; text: string; t?: string; live?: boolean; data?: any };
type Found = { name: string; path: string; kind: "dir" | "file"; ext: string };
type Attached = { name: string; path: string };
type Rec = { start: number; media: MediaRecorder; chunks: Blob[]; stream: MediaStream };
const nid = () => Math.random().toString(36).slice(2) + Date.now().toString(36);
const NOTE: Record<string, string> = { Bash: "running a command", Read: "reading a file", Write: "writing a file", Edit: "editing a file", Glob: "looking through files", Grep: "searching files", WebSearch: "searching the web", WebFetch: "reading a page", Task: "delegating", Agent: "delegating", ToolSearch: "" };
const note = (tool: string) => tool in NOTE ? NOTE[tool] : tool.startsWith("mcp__playwright") ? "in the browser" : "using " + tool.replace(/^mcp__/, "").replace(/__/g, " ");
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
export const globeState = (s: string) => (s === "thinking" || s === "working" ? "thinking" : s === "speaking" ? "speaking" : s === "listening" ? "listening" : "idle") as "idle" | "thinking" | "speaking" | "listening";

// a file mention in a line: @/path, or @"/a path with spaces"
const MENTION = /@"([^"]+)"|@(\/[^\s"]+)/g;
const mention = (p: string) => "@" + (/\s/.test(p) ? `"${p}"` : p);
const short = (p: string) => p.replace(/^\/Users\/[^/]+/, "~");
const base = (p: string) => p.replace(/\/+$/, "").split("/").pop() || p;
const mmss = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
function WithMentions({ text }: { text: string }) {          // a line as written, its @ mentions shown as small file chips
  const parts: ReactNode[] = []; const re = new RegExp(MENTION.source, "g"); let last = 0; let m: RegExpExecArray | null;
  while ((m = re.exec(text))) {
    const p = m[1] || m[2]; parts.push(text.slice(last, m.index));
    parts.push(<span key={m.index} title={p} className="mx-0.5 inline-flex max-w-full items-center gap-1 rounded-full border border-border/60 bg-background/40 px-1.5 py-0.5 align-middle text-xs"><FileText className="h-3 w-3 shrink-0" /><span className="truncate">{base(p)}</span></span>);
    last = m.index + m[0].length;
  }
  parts.push(text.slice(last));
  return <>{parts}</>;
}

export function Chat({ name, embedded = false, onState }: { name: string; embedded?: boolean; onState?: (s: string) => void }) {
  const agent = useMemo(() => new HttpAgent({ url: edgeUrl() + "/agent", threadId: "console" }), []);
  const [msgs, setMsgs] = useState<Msg[]>([]); const [text, setText] = useState(""); const [busy, setBusy] = useState(false); const [state, setState] = useState("off"); const [hint, setHint] = useState("");
  const [files, setFiles] = useState<Attached[]>([]); const [uploading, setUploading] = useState(0); const [drag, setDrag] = useState(false);
  const [pick, setPick] = useState<{ start: number; q: string; items: Found[]; i: number; loading: boolean } | null>(null);   // the @ picker: where the mention starts, what is typed so far, what was found
  const [rec, setRec] = useState<Rec | null>(null); const [recT, setRecT] = useState(0);
  const pos = useRef(0), cpos = useRef(0), live = useRef<{ id: string; final: string[] } | null>(null), skip = useRef<Set<string>>(new Set()), end = useRef<HTMLDivElement>(null), busyRef = useRef(false);
  const input = useRef<HTMLTextAreaElement>(null), fileIn = useRef<HTMLInputElement>(null), findT = useRef<any>(0), findN = useRef(0);
  const upsert = (id: string, f: (m: Msg) => Msg) => setMsgs(ms => ms.map(m => m.id === id ? f(m) : m));
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs]);
  useEffect(() => { onState?.(state); }, [state, onState]);
  useEffect(() => { const el = input.current; if (!el) return; if (!text) { el.style.height = ""; return; } el.style.height = "auto"; el.style.height = Math.min(el.scrollHeight + (el.offsetHeight - el.clientHeight), 160) + "px"; }, [text]);   // the field grows with the lines, up to five or so; empty, it is the one line the styles give it
  useEffect(() => { if (!rec) { setRecT(0); return; } const t = setInterval(() => setRecT(Math.floor((Date.now() - rec.start) / 1000)), 500); return () => clearInterval(t); }, [rec]);
  useEffect(() => {                                               // Esc cuts a reply off, as the Stop button does
    const k = (e: KeyboardEvent) => { if (e.key === "Escape" && !e.defaultPrevented && state && state !== "idle" && state !== "off") epost("/say", { text: "stop" }); };
    addEventListener("keydown", k); return () => removeEventListener("keydown", k);
  }, [state]);
  useEffect(() => {
    let stop = false;
    (async () => {
      try { const h = await eget("/history?limit=120"); setMsgs(h.items.map(fromRow).filter(Boolean) as Msg[]); pos.current = h.pos || 0; cpos.current = h.cpos || 0; } catch { setHint("Troi's server is not answering: start Troi from the Desktop."); }
      const poll = async () => {
        if (stop) return;
        try {
          const d = await eget(`/transcript?pos=${pos.current}&cpos=${cpos.current}`); pos.current = d.pos; if (d.cpos !== undefined) cpos.current = d.cpos;
          for (const it of d.items as Row[]) {
            if (it.role === "ctl") continue;
            const key = it.role + "|" + it.text.slice(0, 60); if (skip.current.has(key)) { skip.current.delete(key); continue; }
            if (it.role === "agent" && live.current) { live.current.final.push(it.text); continue; }
            const m = fromRow(it); if (m) setMsgs(ms => [...ms, m]);
          }
          for (const c of (d.cards || []) as Card[]) { const m = fromCard(c); if (m) setMsgs(ms => [...ms, m]); }
        } catch {}
        setTimeout(poll, 700);
      };
      const pollState = async () => {
        if (stop) return;
        try {
          const d: State = await eget("/state"); setState(d.voice ? d.state : "off");
          const part = (d.partial || "").replace(/\s*<directions:[^>]*>/g, "");
          if (part && !busyRef.current) {
            if (!live.current) { const id = nid(); live.current = { id, final: [] }; setMsgs(ms => [...ms, { id, role: "assistant", text: part, live: true }]); }
            else upsert(live.current.id, m => ({ ...m, text: part }));
          } else if (!part && live.current) { const l = live.current; live.current = null; upsert(l.id, m => ({ ...m, live: false, text: l.final.length ? l.final.join(" ") : m.text })); }
        } catch { setState("off"); }
        setTimeout(pollState, 500);
      };
      poll(); pollState();
    })();
    return () => { stop = true; };
  }, []);   // eslint-disable-line react-hooks/exhaustive-deps

  // ---- files: the @ picker over the file roots, and uploads (the clip, a drop, a paste) into data/blobs/uploads
  const onChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    const v = e.target.value; setText(v);
    const caret = e.target.selectionStart ?? v.length; let start = -1;
    if (pick && v[pick.start] === "@" && caret > pick.start && !v.slice(pick.start + 1, caret).includes("@")) start = pick.start;   // the picker is open: everything since the @ is the search, spaces included
    else { const m = /(^|\s)@([^\s@"]*)$/.exec(v.slice(0, caret)); if (m) start = caret - m[2].length - 1; }
    if (start < 0) { setPick(null); return; }
    const q = v.slice(start + 1, caret);
    setPick(p => ({ start, q, items: p?.items || [], i: 0, loading: true }));
    clearTimeout(findT.current); const n = ++findN.current;
    findT.current = setTimeout(async () => {
      let items: Found[] = []; try { items = (await eget(`/find?q=${encodeURIComponent(q)}`)).items || []; } catch {}
      if (n === findN.current) setPick(p => p ? (items.length ? { ...p, items, i: 0, loading: false } : null) : p);   // nothing found: the @ stays as typed, Enter sends
    }, 120);
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
  const upload = async (list: FileList | File[] | null) => {
    const arr = Array.from(list || []); if (!arr.length) return;
    for (const f of arr) {
      if (f.size > 60_000_000) { setHint(`${f.name} is over 60 MB.`); continue; }
      setUploading(n => n + 1);
      try {
        const r = await fetch(edgeUrl() + "/upload", { method: "POST", headers: { "X-Filename": f.name.normalize("NFKD").replace(/[^\x20-\x7E]/g, "_"), "X-Kind": "uploads", "Content-Type": "application/octet-stream" }, body: f });
        const d = await r.json().catch(() => ({}));
        if (d.ok && d.path) { setFiles(fs => fs.some(x => x.path === d.path) ? fs : [...fs, { name: f.name, path: d.path }]); setHint(""); }
        else setHint(d.error ? `${f.name}: ${d.error}.` : `${f.name} did not upload.`);
      } catch { setHint(`${f.name} did not upload: Troi's server is not answering.`); }
      finally { setUploading(n => n - 1); }
    }
  };

  // ---- a voice note: the phone's microphone, the agent's own ears, the words sent as the line
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
    setUploading(n => n + 1); setHint("Listening…");
    try {
      const ext = blob.type.includes("mp4") ? "m4a" : blob.type.includes("ogg") ? "ogg" : "webm";
      const r = await fetch(edgeUrl() + "/voice", { method: "POST", headers: { "X-Filename": `note.${ext}`, "Content-Type": blob.type || "application/octet-stream" }, body: blob });
      const d = await r.json().catch(() => ({}));
      if (d.ok && d.text) { setHint(""); await send(d.text); } else setHint(d.error ? String(d.error) : "I could not make out any words.");
    } catch { setHint("Troi's server is not answering."); }
    finally { setUploading(n => n - 1); }
  };

  async function send(t: string) {
    const full = [t.trim(), ...files.map(f => mention(f.path))].filter(Boolean).join(" ");   // attached files go as @ mentions, after the words
    if (!full || busy) return;
    setBusy(true); busyRef.current = true; setText(""); setFiles([]); setPick(null); setMsgs(ms => [...ms, { id: nid(), role: "user", text: full }]); skip.current.add("you|" + full.slice(0, 60));
    agent.messages = [{ id: nid(), role: "user", content: full }];
    const said: string[] = [];
    try {
      await agent.runAgent({}, {
        onTextMessageStartEvent: ({ event }) => setMsgs(ms => [...ms, { id: event.messageId, role: "assistant", text: "", live: true }]),
        onTextMessageContentEvent: ({ event }) => upsert(event.messageId, m => ({ ...m, text: m.text + event.delta })),
        onTextMessageEndEvent: ({ event }) => setMsgs(ms => ms.map(m => { if (m.id === event.messageId) { said.push(m.text); return { ...m, live: false }; } return m; })),
        onToolCallStartEvent: ({ event }) => { const n = note(event.toolCallName); if (n) setMsgs(ms => [...ms, { id: nid(), role: "note", text: n }]); },
        onCustomEvent: ({ event }) => { if (event.name === "silo.state") setState(String(event.value)); const m = fromCard({ name: event.name, value: event.value }); if (m) setMsgs(ms => [...ms, m]);
          if (event.name === "silo.approval") setMsgs(ms => [...ms, { id: nid(), role: "note", text: `waiting for your approval: ${(event.value as any).kind} · ${(event.value as any).subject}` }]); },
        onRunErrorEvent: ({ event }) => setMsgs(ms => [...ms, { id: nid(), role: "note", text: event.message }]),
      });
    } catch (e: any) { setMsgs(ms => [...ms, { id: nid(), role: "note", text: "The line did not answer: " + (e?.message || e) }]); }
    for (const s of said) for (const sent of s.split(/(?<=[.!?])\s+/)) skip.current.add("agent|" + sent.slice(0, 60));   // the same sentences come through the voice log
    setBusy(false); busyRef.current = false;
  }
  const shape = talkShape(); const mobile = useMobile(); const talking = busy || (state !== "idle" && state !== "off"); const something = text.trim().length > 0 || files.length > 0;
  const field = "w-full border border-border bg-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30";
  return (
    <div className={cn("flex h-full min-h-0 flex-col", embedded ? "" : "md:hairline")}>
      {/* the header is the desktop's: on a phone the top bar already says who is speaking and in what state */}
      <div className="hidden items-center gap-2 border-b border-border px-3 py-2 text-sm md:flex"><span className="font-medium">Conversation</span><span className="text-xs text-muted-foreground">· {state}</span>
        <button className="ml-auto text-muted-foreground hover:text-foreground" title={shape === "column" ? "Make it a floating pane" : "Make it a full column"} onClick={() => setTalkShape(shape === "column" ? "floating" : "column")}>{shape === "column" ? <PictureInPicture2 className="h-4 w-4" /> : <Columns2 className="h-4 w-4" />}</button></div>
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-3 py-3 md:p-4">
        {msgs.length === 0 && <div className="grid h-full place-items-center px-6 text-center text-[15px] text-muted-foreground md:text-sm">{mobile ? `Nothing said yet. Write to ${name} below; it answers here and out loud on the Mac.` : "Nothing said yet. Hold your talk key and speak, or type below."}</div>}
        <AnimatePresence initial={false}>
          {msgs.map(m => m.role === "headlines" ? <HeadlinesCard key={m.id} {...m.data} /> : m.role === "pictures" ? <PicturesGrid key={m.id} {...m.data} /> : m.role === "ui" ? <UiBlock key={m.id} {...m.data} /> : (
            <motion.div key={m.id} {...rise} className={m.role === "user" ? "ml-auto max-w-[80%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-accent px-3.5 py-2 text-[15px] md:max-w-[75%] md:rounded-md md:text-sm" : m.role === "note" || m.role === "ignored" ? "px-1 text-xs italic text-muted-foreground" : cn("max-w-[88%] whitespace-pre-wrap rounded-2xl rounded-bl-md border border-border bg-surface/85 px-3.5 py-2 text-[15px] leading-6 md:max-w-[85%] md:rounded-md md:bg-transparent md:text-sm", m.live && "border-dashed")}>
              {m.role === "user" ? <WithMentions text={m.text} /> : m.text}{m.live && <span className="ml-0.5 animate-pulse text-primary">▍</span>}{m.t && !m.live && m.role !== "note" && <span className="ml-2 text-[10px] text-muted-foreground">{m.t}</span>}
            </motion.div>))}
        </AnimatePresence>
        <div ref={end} />
      </div>
      {/* the composer: the clip, the field (with the @ picker above it), then the plane, or the microphone while the field is empty on a phone; Stop shows while a reply is under way */}
      <form className={cn("relative border-t border-border p-2.5 md:p-3", drag && "bg-accent/40")} onSubmit={e => { e.preventDefault(); send(text); }}
        onDragOver={e => { if (e.dataTransfer.types.includes("Files")) { e.preventDefault(); setDrag(true); } }} onDragLeave={() => setDrag(false)} onDrop={e => { e.preventDefault(); setDrag(false); upload(e.dataTransfer.files); }}>
        {pick && pick.items.length > 0 && (
          <div role="listbox" aria-label="Files on the Mac" className="absolute bottom-full left-2.5 right-2.5 z-20 mb-1 max-h-60 overflow-y-auto rounded-md border border-border bg-background/95 p-1 shadow-lg backdrop-blur md:left-3 md:right-3">
            {pick.items.map((it, k) => (
              <button type="button" role="option" aria-selected={k === pick.i} key={it.path} onMouseDown={e => { e.preventDefault(); choose(it); }} onMouseEnter={() => setPick(p => p ? { ...p, i: k } : p)}
                className={cn("flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm", k === pick.i ? "bg-accent text-accent-foreground" : "text-foreground")}>
                {it.kind === "dir" ? <Folder className="h-4 w-4 shrink-0 text-muted-foreground" /> : <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />}
                <span className="truncate">{it.name}</span><span className="ml-auto hidden max-w-[50%] truncate text-xs text-muted-foreground sm:block">{short(it.path).replace(/\/[^/]*$/, "")}</span>
              </button>))}
          </div>)}
        <div className="flex items-end gap-2">
          <input ref={fileIn} type="file" multiple className="hidden" onChange={e => { upload(e.target.files); e.target.value = ""; }} />
          {rec ? (
            <div className="flex h-11 min-w-0 flex-1 items-center gap-2.5 rounded-full border border-border bg-background px-4 md:h-9 md:rounded-sm">
              <span className="h-2.5 w-2.5 shrink-0 animate-pulse rounded-full bg-red-500" /><span className="font-mono text-sm tabular-nums">{mmss(recT)}</span><span className="truncate text-sm text-muted-foreground">Recording</span>
              <button type="button" aria-label="Throw the recording away" onClick={() => stopRec(false)} className="ml-auto grid h-8 w-8 shrink-0 place-items-center rounded-full text-muted-foreground hover:text-foreground"><X className="h-4 w-4" /></button>
            </div>
          ) : (<>
            <Button type="button" variant="outline" aria-label="Attach a file" title="Attach a file: choose one, drop it here, or paste it. Type @ to point at a file on the Mac." disabled={uploading > 0} onClick={() => fileIn.current?.click()} className="h-11 w-11 shrink-0 rounded-full p-0 md:h-9 md:w-9 md:rounded-sm"><Paperclip className={cn("h-[18px] w-[18px] md:h-4 md:w-4", uploading > 0 && "animate-pulse")} /></Button>
            <textarea ref={input} rows={1} value={text} onChange={onChange} onKeyDown={onKey} onBlur={() => setTimeout(() => setPick(null), 150)} onPaste={e => { if (e.clipboardData.files.length) { e.preventDefault(); upload(e.clipboardData.files); } }}
              placeholder={mobile ? `Message ${name}` : `Type to ${name} and press Enter · @ points at a file`} autoCapitalize="sentences" autoComplete="off" aria-label={`Message ${name}`}
              className={cn(field, "max-h-40 min-h-11 flex-1 resize-none rounded-[22px] px-4 py-2.5 text-base leading-6 md:min-h-9 md:rounded-sm md:px-3 md:py-1.5 md:text-sm")} />
          </>)}
          {rec ? <Button type="button" onClick={() => stopRec(true)} aria-label="Send the recording" className="h-11 w-11 shrink-0 rounded-full p-0 md:h-9 md:w-auto md:rounded-sm md:px-4"><Send className="h-5 w-5 md:h-4 md:w-4" /><span className="hidden md:inline">Send</span></Button>
            : mobile && !something ? <Button type="button" onClick={startRec} disabled={busy || uploading > 0} aria-label="Record a voice note" className="h-11 w-11 shrink-0 rounded-full p-0"><Mic className="h-5 w-5" /></Button>
            : <Button type="submit" disabled={busy || uploading > 0 || !something} aria-label="Send" className="h-11 w-11 shrink-0 rounded-full p-0 md:h-9 md:w-auto md:rounded-sm md:px-4"><Send className="h-5 w-5 md:h-4 md:w-4" /><span className="hidden md:inline">Send</span></Button>}
          <Button type="button" variant="outline" onClick={() => epost("/say", { text: "stop" })} title="Cut the reply off (Esc)" aria-label="Stop the reply" className={cn("h-11 w-11 shrink-0 rounded-full p-0 md:inline-flex md:h-9 md:w-auto md:rounded-sm md:px-3", talking ? "inline-flex" : "hidden")}><Square className="h-4 w-4" /></Button>
        </div>
        {files.length > 0 && <div className="flex flex-wrap gap-1.5 pt-2">{files.map(f => (
          <span key={f.path} title={f.path} className="inline-flex max-w-full items-center gap-1 rounded-full border border-border px-2 py-0.5 text-xs"><FileText className="h-3 w-3 shrink-0" /><span className="truncate">{f.name}</span>
            <button type="button" aria-label={`Leave ${f.name} out`} onClick={() => setFiles(fs => fs.filter(x => x.path !== f.path))} className="grid h-4 w-4 place-items-center rounded-full text-muted-foreground hover:text-foreground"><X className="h-3 w-3" /></button></span>))}
        </div>}
      </form>
      {hint && <div className="px-4 pb-3 text-xs text-muted-foreground">{hint}</div>}
    </div>
  );
}
