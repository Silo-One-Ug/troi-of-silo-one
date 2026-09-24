"use client";
// Routines: the pulse's jobs with their times and switches, run now, the reminders. The CI watch's card is where the
// GitHub orgs and users it follows are set (as many as you like; the pulse reads them every round).
import { useEffect, useState } from "react";
import { Play, Plus, X } from "lucide-react";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { eget, epost } from "@/lib/edge";

const NAME = /^[A-Za-z0-9][A-Za-z0-9-]{0,38}$/;          // a GitHub org or user name

function Orgs({ orgs, busy, onSave }: { orgs: string[]; busy: boolean; onSave: (orgs: string[]) => void }) {
  const [v, setV] = useState("");
  const add = () => {
    const s = v.trim().replace(/^@/, "").replace(/^https?:\/\/github\.com\//i, "").replace(/\/.*$/, "");   // "@org", a pasted URL or "org/repo" all mean the org
    setV(""); if (s && NAME.test(s) && !orgs.includes(s)) onSave([...orgs, s]);
  };
  return (
    <div className="flex flex-wrap items-center gap-1.5 pt-1">
      {orgs.map(o => <span key={o} className="pill h-7 gap-1 border border-border pl-2.5 pr-1 text-xs"><span>{o}</span>
        <button type="button" aria-label={`Stop watching ${o}`} disabled={busy} onClick={() => onSave(orgs.filter(x => x !== o))} className="grid h-5 w-5 place-items-center rounded-full text-muted-foreground hover:bg-muted hover:text-foreground"><X className="h-3 w-3" /></button></span>)}
      <Input className="h-7 w-40 text-xs" value={v} placeholder="org or user" aria-label="GitHub org or user to watch" disabled={busy} onChange={e => setV(e.target.value)} onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); add(); } }} />
      <Button size="sm" variant="ghost" disabled={busy || !v.trim()} onClick={add}><Plus className="h-3.5 w-3.5" />Watch</Button>
    </div>
  );
}

export function Routines() {
  const [d, setD] = useState<any>(null); const [msg, setMsg] = useState(""); const [busy, setBusy] = useState("");
  const load = async () => { try { setD(await eget("/routines")); } catch { setMsg("Troi's server is not answering: start Troi from the Desktop."); } };
  useEffect(() => { load(); const t = setInterval(load, 15000); return () => clearInterval(t); }, []);
  const post = async (body: any) => { setBusy(body.id); try { const r = await epost("/routines", body); setMsg(r.done || (r.ok ? "saved" : r.error || "")); } finally { setBusy(""); load(); } };
  const saveOrgs = async (orgs: string[]) => { setBusy("orgs"); try { const r = await epost("/settings", { github_orgs: orgs }); setMsg(r.ok ? (orgs.length ? `Watching ${orgs.join(", ")}: the newest run on main of every repo, every three minutes.` : "Watching no GitHub org or user.") : r.error || "not saved"); } finally { setBusy(""); load(); } };
  if (!d) return <div className="hairline p-6 text-sm text-muted-foreground">{msg || "…"}</div>;
  return (
    <div className="grid max-w-4xl gap-5">
      <div className="hairline divide-y divide-border">
        <div className="flex items-center gap-3 px-4 py-2"><span className="text-sm font-semibold">On a clock</span><Badge tone={d.pulse ? "ok" : "warn"}>{d.pulse ? "pulse running" : "pulse not running"}</Badge></div>
        {d.jobs.map((j: any) => (
          <div key={j.id} className="grid gap-3 px-4 py-3 text-sm md:grid-cols-[1fr_auto] md:items-center md:gap-4">{/* one column on a phone: the buttons under the job */}
            <div className="grid min-w-0 gap-0.5"><div className="flex flex-wrap items-center gap-2"><span className="font-medium">{j.name}</span><Badge tone={j.enabled ? "ok" : "warn"}>{j.enabled ? "on" : "off"}</Badge>{j.editable ? <Input className="h-8 w-24 font-mono text-xs md:h-7" defaultValue={j.when} onBlur={e => e.target.value !== j.when && post({ id: j.id, when: e.target.value })} /> : <code className="text-xs text-muted-foreground">{j.when}</code>}</div>
              <div className="text-xs text-muted-foreground">{j.detail}{j.last ? ` · last: ${String(j.last).slice(0, 120)}` : ""}</div>
              {j.id === "ci" && <Orgs orgs={j.orgs || []} busy={busy === "orgs"} onSave={saveOrgs} />}</div>
            <div className="flex flex-wrap gap-2">{j.editable && <Button size="sm" variant="ghost" onClick={() => post({ id: j.id, enabled: !j.enabled })}>{j.enabled ? "Switch off" : "Switch on"}</Button>}{["report", "brief", "compact", "backup", "housekeeping", "ci"].includes(j.id) && <Button size="sm" variant="outline" disabled={busy === j.id} onClick={() => post({ id: j.id, run: true })}><Play className="h-3.5 w-3.5" />{busy === j.id ? "running…" : "Run now"}</Button>}</div>
          </div>))}
      </div>
      <div className="hairline divide-y divide-border">
        <div className="px-4 py-2 text-sm font-semibold">Reminders</div>
        {(d.reminders || []).length === 0 && <div className="px-4 py-3 text-sm text-muted-foreground">None set. Say &quot;remind me in 20 minutes to…&quot;.</div>}
        {(d.reminders || []).map((r: any) => <div key={r.at} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2 text-sm"><span className="w-full text-xs text-muted-foreground md:w-40 md:text-sm">{new Date(r.at * 1000).toLocaleString()}</span><span className="min-w-0 flex-1">{r.text}</span><Button size="sm" variant="ghost" onClick={() => post({ id: "reminder", cancel: r.at })}><X className="h-3.5 w-3.5" />Cancel</Button></div>)}
      </div>
      {msg && <div className="text-xs text-muted-foreground">{msg}</div>}
    </div>
  );
}
