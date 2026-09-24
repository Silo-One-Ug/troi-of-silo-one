"use client";
// Approvals: what the agent asked for and may not do alone. A settings change needs the PIN; unlock once and the
// token rides along for fifteen minutes, exactly as the native console's lock works.
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Lock, Unlock } from "lucide-react";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { rise } from "@/lib/motion";
import { eget, epost, rememberUnlock, unlockToken, type Pending } from "@/lib/edge";
const LABEL: Record<string, string> = { trash: "Move to the Trash", kill: "Force-quit", click: "A risky click", setting: "Change a protected setting" };

export function UnlockBox() {
  const [pin, setPin] = useState(""); const [msg, setMsg] = useState(""); const [on, setOn] = useState(false);
  useEffect(() => { setOn(!!unlockToken()); const t = setInterval(() => setOn(!!unlockToken()), 5000); return () => clearInterval(t); }, []);
  const go = async () => { const d = await epost("/unlock", { pin }); if (d.ok) { rememberUnlock(d.token, d.until); setPin(""); setOn(true); setMsg(""); } else setMsg(d.error || "Wrong PIN."); };
  return (<div className="flex items-center gap-2 text-sm">{on ? <Badge tone="ok" className="gap-1"><Unlock className="h-3 w-3" />unlocked</Badge> : <><Lock className="h-4 w-4 text-muted-foreground" /><Input className="h-8 w-24" type="password" inputMode="numeric" placeholder="PIN" value={pin} onChange={e => setPin(e.target.value)} onKeyDown={e => e.key === "Enter" && go()} /><Button size="sm" variant="outline" onClick={go} disabled={!pin}>Unlock</Button></>}{msg && <span className="text-xs text-muted-foreground">{msg}</span>}</div>);
}

export function Approvals() {
  const [rows, setRows] = useState<Pending[]>([]); const [msg, setMsg] = useState(""); const [history, setHistory] = useState<any[]>([]);
  const load = async () => { try { const s = await eget("/state"); setRows(s.pending || []); } catch {} };
  const older = () => eget("/approvals").then(d => setHistory(d.approvals || [])).catch(() => {});
  useEffect(() => { load(); older(); const t = setInterval(load, 2000); return () => clearInterval(t); }, []);
  const decide = async (p: Pending, ok: boolean) => { const d = await epost("/approve", { id: p.id, ok }); setMsg(d.ok ? (d.done || (ok ? "approved" : "rejected")) : d.error || "not done"); load(); older(); };
  return (
    <div className="grid max-w-3xl gap-4">
      <div className="flex items-center justify-between"><h2 className="text-sm font-semibold">Waiting for you · {rows.length}</h2><UnlockBox /></div>
      {rows.length === 0 && <div className="hairline p-8 text-center text-sm text-muted-foreground">Nothing waiting. The agent files anything it may not do alone here.</div>}
      <AnimatePresence>{rows.map(p => (
        <motion.div key={p.id} {...rise} className="note-warn rounded-md border p-3 text-sm">
          <div className="flex items-center gap-2"><Badge tone="warn">{p.kind || "trash"}</Badge><b>{LABEL[p.kind || "trash"] || p.kind}</b><span className="ml-auto text-xs text-muted-foreground">{new Date(p.at * 1000).toLocaleTimeString()}</span></div>
          <div className="mt-1 break-all font-mono text-xs">{p.src}</div>{p.why && <div className="mt-1 text-xs text-muted-foreground">{p.why}</div>}
          <div className="mt-2 flex gap-2"><Button size="sm" onClick={() => decide(p, true)}>Approve</Button><Button size="sm" variant="outline" onClick={() => decide(p, false)}>Reject</Button></div>
        </motion.div>))}
      </AnimatePresence>
      {msg && <div className="text-xs text-muted-foreground">{msg}</div>}
      {history.length > 0 && <div className="hairline divide-y divide-border"><div className="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Earlier</div>{history.slice(0, 40).map(a => <div key={a.id} className="flex items-center gap-3 px-3 py-2 text-sm"><Badge tone={a.status === "approved" ? "ok" : a.status === "open" ? "warn" : "note"}>{a.status}</Badge><span className="text-xs text-muted-foreground">{a.kind}</span><span className="truncate font-mono text-xs">{a.src}</span><span className="ml-auto shrink-0 text-xs text-muted-foreground">{new Date(a.at * 1000).toLocaleString()}</span></div>)}</div>}
    </div>
  );
}
