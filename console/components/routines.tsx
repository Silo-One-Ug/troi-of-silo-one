"use client";
// Routines: the pulse's jobs with their times and switches, run now, the reminders.
import { useEffect, useState } from "react";
import { Play, X } from "lucide-react";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { eget, epost } from "@/lib/edge";

export function Routines() {
  const [d, setD] = useState<any>(null); const [msg, setMsg] = useState(""); const [busy, setBusy] = useState("");
  const load = async () => { try { setD(await eget("/routines")); } catch { setMsg("Troi's server is not answering: start Troi from the Desktop."); } };
  useEffect(() => { load(); const t = setInterval(load, 15000); return () => clearInterval(t); }, []);
  const post = async (body: any) => { setBusy(body.id); try { const r = await epost("/routines", body); setMsg(r.done || (r.ok ? "saved" : r.error || "")); } finally { setBusy(""); load(); } };
  if (!d) return <div className="hairline p-6 text-sm text-muted-foreground">{msg || "…"}</div>;
  return (
    <div className="grid max-w-4xl gap-5">
      <div className="hairline divide-y divide-border">
        <div className="flex items-center gap-3 px-4 py-2"><span className="text-sm font-semibold">On a clock</span><Badge tone={d.pulse ? "ok" : "warn"}>{d.pulse ? "pulse running" : "pulse not running"}</Badge></div>
        {d.jobs.map((j: any) => (
          <div key={j.id} className="grid grid-cols-[1fr_auto] items-center gap-4 px-4 py-3 text-sm">
            <div className="grid gap-0.5"><div className="flex items-center gap-2"><span className="font-medium">{j.name}</span><Badge tone={j.enabled ? "ok" : "warn"}>{j.enabled ? "on" : "off"}</Badge>{j.editable ? <Input className="h-7 w-24 font-mono text-xs" defaultValue={j.when} onBlur={e => e.target.value !== j.when && post({ id: j.id, when: e.target.value })} /> : <code className="text-xs text-muted-foreground">{j.when}</code>}</div>
              <div className="text-xs text-muted-foreground">{j.detail}{j.last ? ` · last: ${String(j.last).slice(0, 120)}` : ""}</div></div>
            <div className="flex gap-2">{j.editable && <Button size="sm" variant="ghost" onClick={() => post({ id: j.id, enabled: !j.enabled })}>{j.enabled ? "Switch off" : "Switch on"}</Button>}{["report", "brief", "compact", "backup", "housekeeping", "ci"].includes(j.id) && <Button size="sm" variant="outline" disabled={busy === j.id} onClick={() => post({ id: j.id, run: true })}><Play className="h-3.5 w-3.5" />{busy === j.id ? "running…" : "Run now"}</Button>}</div>
          </div>))}
      </div>
      <div className="hairline divide-y divide-border">
        <div className="px-4 py-2 text-sm font-semibold">Reminders</div>
        {(d.reminders || []).length === 0 && <div className="px-4 py-3 text-sm text-muted-foreground">None set. Say &quot;remind me in 20 minutes to…&quot;.</div>}
        {(d.reminders || []).map((r: any) => <div key={r.at} className="flex items-center gap-3 px-4 py-2 text-sm"><span className="w-40 text-muted-foreground">{new Date(r.at * 1000).toLocaleString()}</span><span className="flex-1">{r.text}</span><Button size="sm" variant="ghost" onClick={() => post({ id: "reminder", cancel: r.at })}><X className="h-3.5 w-3.5" />Cancel</Button></div>)}
      </div>
      {msg && <div className="text-xs text-muted-foreground">{msg}</div>}
    </div>
  );
}
