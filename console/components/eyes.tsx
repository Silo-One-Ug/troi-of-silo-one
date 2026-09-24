"use client";
// Eyes: what the agent sees right now. The live frame while its eyes are on, a look or a screenshot on demand, the eyes
// modes, the hands switch (the board's camera and the galaxies' hand tracking), and face ID (learn, check = unlock).
import { useEffect, useState } from "react";
import { Camera, Hand, Monitor, ScanFace } from "lucide-react";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { eget, emit, epost, img, rememberUnlock, type Config, type State } from "@/lib/edge";
import { cn } from "@/lib/utils";

const MODES = [["off", "Off", "The camera stays off"], ["every", "Every reply", "A fresh frame with every reply"], ["watch", "Watch", "Looks when the view changes"], ["screen", "Screen", "A screenshot with every request"]] as const;

export function Eyes() {
  const [c, setC] = useState<Config | null>(null); const [st, setSt] = useState<State | null>(null); const [shot, setShot] = useState(""); const [msg, setMsg] = useState(""); const [busy, setBusy] = useState(""); const [hands, setHands] = useState(false); const [tick, setTick] = useState(0);
  useEffect(() => { try { setHands(localStorage.getItem("silo.hands") === "1"); } catch {} eget("/config").then(setC).catch(() => setMsg("The agent is not answering.")); }, []);
  useEffect(() => { let stop = false; const t = async () => { if (stop) return; try { setSt(await eget("/state")); setTick(x => x + 1); } catch {} setTimeout(t, 900); }; t(); return () => { stop = true; }; }, []);
  const look = async (what: "camera" | "screen") => { setBusy(what); setMsg(what === "camera" ? "Looking…" : "Taking the screen…"); try { const d = await epost("/look", { what }); if (d.ok) { setShot(d.path); setMsg(""); } else setMsg(d.error || "Nothing came back."); } finally { setBusy(""); } };
  const eyes = async (v: string) => { const d = await epost("/settings", { eyes: v }); if (d.pending) setMsg("Protected: waiting for your approval (Telegram, or unlock with your PIN in the bar)."); else if (d.ok) { setC(x => x ? { ...x, eyes: v } : x); setMsg(v === "off" ? "Camera off." : "Eyes: " + v + "."); } };
  const toggleHands = () => { const v = !hands; setHands(v); try { localStorage.setItem("silo.hands", v ? "1" : "0"); } catch {} emit("hands", v); setMsg(v ? "Hands on: the board's camera and the galaxies track your hands." : "Hands off."); };
  const faceLearn = async () => { const d = await epost("/settings", { face_id: "learn" }); setMsg(d.pending ? "Protected: approve it first (PIN in the bar, or Telegram)." : d.ok ? "Look at the camera: five shots, about ten seconds." : d.error || "Not started."); };
  const faceCheck = async () => { setMsg("Look at the camera…"); const d = await epost("/face-verify", {}); if (d.ok) { rememberUnlock(d.token, d.until); setMsg(`It's you (${d.sim}). Unlocked for fifteen minutes.`); } else setMsg((d.error || "Not a match") + (d.sim !== undefined ? ` (${d.sim})` : "")); };
  const live = st?.live ? img(st.live) + "&t=" + tick : "";
  const frame = live || (shot ? img(shot) : "");
  return (
    <div className="grid max-w-6xl gap-4 lg:grid-cols-[1fr_320px]">
      <div className="hairline overflow-hidden">
        <div className="flex items-center gap-2 border-b border-border px-3 py-2 text-sm"><span className="font-medium">What {c?.name || "Troi"} sees</span>{live ? <Badge tone="ok">live</Badge> : shot ? <Badge tone="note">a look</Badge> : <Badge tone="warn">eyes closed</Badge>}</div>
        <div className="grid aspect-video place-items-center bg-black">{frame ? <img src={frame} alt="" className="h-full w-full object-contain" /> : <div className="px-6 text-center text-sm text-muted-foreground">The camera is off. Take a look, or switch the eyes on.</div>}</div>
        <div className="flex flex-wrap gap-2 p-3"><Button size="sm" variant="outline" disabled={!!busy} onClick={() => look("camera")}><Camera className="h-4 w-4" />Look now</Button><Button size="sm" variant="outline" disabled={!!busy} onClick={() => look("screen")}><Monitor className="h-4 w-4" />Screen now</Button></div>
      </div>
      <div className="grid content-start gap-4">
        <div className="hairline grid gap-2 p-4"><div className="label">Eyes</div><div className="flex flex-wrap gap-1.5">{MODES.map(([v, l, t]) => <button key={v} title={t} onClick={() => eyes(v)} className={cn("pill border px-3 py-1", (c?.eyes || "off") === v ? "pill-note border-transparent" : "border-border text-muted-foreground hover:text-foreground")}>{l}</button>)}</div><div className="text-xs text-muted-foreground">Turning the camera on is protected: it needs your proof.</div></div>
        <div className="hairline grid gap-2 p-4"><div className="label">Hands</div><Button size="sm" variant={hands ? "default" : "outline"} onClick={toggleHands}><Hand className="h-4 w-4" />{hands ? "Hands on" : "Hands off"}</Button><div className="text-xs text-muted-foreground">One switch for the board&apos;s camera and the galaxies&apos; hand tracking. Off saves the battery.</div></div>
        <div className="hairline grid gap-2 p-4"><div className="label">Face ID</div><div className="flex items-center gap-2"><Badge tone={c?.face_print ? "ok" : "warn"}>{c?.face_env === false ? "not installed" : c?.face_print ? "known" : "not learnt"}</Badge></div><div className="flex gap-2"><Button size="sm" variant="outline" onClick={faceLearn}><ScanFace className="h-4 w-4" />Learn my face</Button><Button size="sm" variant="outline" onClick={faceCheck}>Check it&apos;s me</Button></div></div>
        {msg && <div className="text-xs text-muted-foreground">{msg}</div>}
      </div>
    </div>
  );
}
