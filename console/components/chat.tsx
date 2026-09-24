"use client";
// The conversation. Typed turns go through AG-UI (POST /agent on the native server) and render as they stream:
// text, the tool in use, cards, approvals. Spoken turns arrive through the voice log (/transcript) and the live
// reply through /state.partial, as the native console shows them. The record comes back from /history on open.
import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { HttpAgent } from "@ag-ui/client";
import { Columns2, PictureInPicture2, Send, Square } from "lucide-react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { HeadlinesCard, PicturesGrid } from "./cards";
import { UiBlock } from "./render";
import { rise } from "@/lib/motion";
import { edgeUrl, eget, epost, img, setTalkShape, talkShape, type Card, type Row, type State } from "@/lib/edge";
import { cn } from "@/lib/utils";

type Msg = { id: string; role: "user" | "assistant" | "note" | "ignored" | "headlines" | "pictures" | "ui"; text: string; t?: string; live?: boolean; data?: any };
const nid = () => Math.random().toString(36).slice(2) + Date.now().toString(36);
const NOTE: Record<string, string> = { Bash: "running a command", Read: "reading a file", Write: "writing a file", Edit: "editing a file", Glob: "looking through files", Grep: "searching files", WebSearch: "searching the web", WebFetch: "reading a page", Task: "working on it", ToolSearch: "" };
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

export function Chat({ name, embedded = false, onState }: { name: string; embedded?: boolean; onState?: (s: string) => void }) {
  const agent = useMemo(() => new HttpAgent({ url: edgeUrl() + "/agent", threadId: "console" }), []);
  const [msgs, setMsgs] = useState<Msg[]>([]); const [text, setText] = useState(""); const [busy, setBusy] = useState(false); const [state, setState] = useState("off"); const [hint, setHint] = useState("");
  const pos = useRef(0), cpos = useRef(0), live = useRef<{ id: string; final: string[] } | null>(null), skip = useRef<Set<string>>(new Set()), end = useRef<HTMLDivElement>(null), busyRef = useRef(false);
  const upsert = (id: string, f: (m: Msg) => Msg) => setMsgs(ms => ms.map(m => m.id === id ? f(m) : m));
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs]);
  useEffect(() => { onState?.(state); }, [state, onState]);
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

  async function send(t: string) {
    if (!t.trim() || busy) return;
    setBusy(true); busyRef.current = true; setText(""); setMsgs(ms => [...ms, { id: nid(), role: "user", text: t }]); skip.current.add("you|" + t.slice(0, 60));
    agent.messages = [{ id: nid(), role: "user", content: t }];
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
  const shape = talkShape();
  return (
    <div className={cn("flex h-full min-h-0 flex-col", embedded ? "" : "hairline")}>
      <div className="flex items-center gap-2 border-b border-border px-3 py-2 text-sm"><span className="font-medium">Conversation</span><span className="text-xs text-muted-foreground">· {state}</span>
        <button className="ml-auto text-muted-foreground hover:text-foreground" title={shape === "column" ? "Make it a floating pane" : "Make it a full column"} onClick={() => setTalkShape(shape === "column" ? "floating" : "column")}>{shape === "column" ? <PictureInPicture2 className="h-4 w-4" /> : <Columns2 className="h-4 w-4" />}</button></div>
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
        {msgs.length === 0 && <div className="grid h-full place-items-center text-sm text-muted-foreground">Nothing said yet. Hold your talk key and speak, or type below.</div>}
        <AnimatePresence initial={false}>
          {msgs.map(m => m.role === "headlines" ? <HeadlinesCard key={m.id} {...m.data} /> : m.role === "pictures" ? <PicturesGrid key={m.id} {...m.data} /> : m.role === "ui" ? <UiBlock key={m.id} {...m.data} /> : (
            <motion.div key={m.id} {...rise} className={m.role === "user" ? "ml-auto max-w-[75%] rounded-md bg-accent px-3 py-2 text-sm" : m.role === "note" || m.role === "ignored" ? "text-xs italic text-muted-foreground" : cn("max-w-[85%] whitespace-pre-wrap rounded-md border border-border px-3 py-2 text-sm leading-6", m.live && "border-dashed")}>
              {m.text}{m.live && <span className="ml-0.5 animate-pulse text-primary">▍</span>}{m.t && !m.live && m.role !== "note" && <span className="ml-2 text-[10px] text-muted-foreground">{m.t}</span>}
            </motion.div>))}
        </AnimatePresence>
        <div ref={end} />
      </div>
      <form className="flex gap-2 border-t border-border p-3" onSubmit={e => { e.preventDefault(); send(text); }}>
        <Input value={text} onChange={e => setText(e.target.value)} placeholder={`Type to ${name} and press Enter`} />
        <Button type="submit" disabled={busy}><Send className="h-4 w-4" />Send</Button>
        <Button type="button" variant="outline" onClick={() => epost("/say", { text: "stop" })} title="Cut the reply off (Esc)"><Square className="h-4 w-4" /></Button>
      </form>
      {hint && <div className="px-4 pb-3 text-xs text-muted-foreground">{hint}</div>}
    </div>
  );
}
