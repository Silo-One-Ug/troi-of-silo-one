"use client";
// Reports: the end-of-day reports report.py built, shown as they are, with the PDF to download.
import { useEffect, useState } from "react";
import { Download, FileText } from "lucide-react";
import { Button } from "./ui/button";
import { edgeUrl, eget, epost } from "@/lib/edge";

export function Reports() {
  const [rows, setRows] = useState<any[]>([]); const [open, setOpen] = useState<string>(""); const [msg, setMsg] = useState("");
  const load = () => eget("/reports").then(d => setRows(d.reports || [])).catch(() => setMsg("Troi's server is not answering: start Troi from the Desktop."));
  useEffect(() => { load(); }, []);
  return (
    <div className="grid grid-cols-[260px_1fr] gap-6">
      <aside className="grid content-start gap-3">
        <Button onClick={async () => { const r = await epost("/routines", { id: "report", run: true }); setMsg(r.done || r.error || ""); setTimeout(load, 60000); }}>Build today&apos;s report</Button>
        <div className="hairline divide-y divide-border">{rows.length === 0 && <div className="p-4 text-sm text-muted-foreground">No reports yet.</div>}{rows.map(r => <button key={r.date} onClick={() => setOpen(r.date)} className={"flex w-full items-center gap-2 px-3 py-2.5 text-left text-sm hover:bg-surface " + (open === r.date ? "bg-accent" : "")}><FileText className="h-3.5 w-3.5 text-muted-foreground" /><b>{r.date}</b>{r.pdf && <Download className="ml-auto h-3.5 w-3.5 text-muted-foreground" />}</button>)}</div>
        {msg && <div className="text-xs text-muted-foreground">{msg}</div>}
      </aside>
      <section className="hairline min-h-[70vh] overflow-hidden">{open ? <><div className="flex items-center gap-3 border-b border-border px-3 py-2 text-sm"><b>{open}</b><a className="ml-auto text-xs text-primary underline" href={`${edgeUrl()}/report.pdf?d=${open}`}>Download the PDF</a></div><iframe src={`${edgeUrl()}/report?d=${open}`} className="h-[70vh] w-full" title={open} /></> : <div className="grid h-full place-items-center p-10 text-sm text-muted-foreground">Pick a day.</div>}</section>
    </div>
  );
}
