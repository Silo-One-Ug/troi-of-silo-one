"use client";
// The Library: every picture the agent took, made, found or received, as books by where and day.
import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, Search, Star, X } from "lucide-react";
import { Badge } from "./ui/badge";
import { Input } from "./ui/input";
import { eget, epost, img } from "@/lib/edge";
import { rise } from "@/lib/motion";
import { cn } from "@/lib/utils";
type Pic = { id?: number; path: string; name: string; where: string; kind: string; t: number; starred?: boolean; credit?: string };
const day = (t: number) => { const d = new Date(t * 1000); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; };
const dayLabel = (d: string) => { const t = new Date(d + "T00:00:00"); const diff = Math.round((new Date().setHours(0, 0, 0, 0) - t.getTime()) / 86400000); return diff === 0 ? "Today" : diff === 1 ? "Yesterday" : t.toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" }); };

export function Library() {
  const [rows, setRows] = useState<Pic[]>([]); const [q, setQ] = useState(""); const [where, setWhere] = useState(""); const [book, setBook] = useState<string | null>(null); const [open, setOpen] = useState<Pic | null>(null);
  useEffect(() => { eget("/images").then(d => setRows(d.items || [])).catch(() => {}); }, []);
  const star = async (p: Pic) => { const on = !p.starred; const d = await epost("/star", { id: p.id, on }); if (d.ok) setRows(rs => rs.map(r => r.path === p.path ? { ...r, starred: on } : r)); };
  const wheres = useMemo(() => [...new Set(rows.map(r => r.where))], [rows]);
  const filtered = rows.filter(r => (!where || r.where === where) && (!q || r.name.toLowerCase().includes(q.toLowerCase()) || r.where.toLowerCase().includes(q.toLowerCase())));
  const books = useMemo(() => { const m = new Map<string, Pic[]>(); for (const r of filtered) { const k = r.where + "|" + day(r.t); m.set(k, [...(m.get(k) || []), r]); } return [...m.entries()]; }, [filtered]);
  const list = book ? (books.find(([k]) => k === book)?.[1] || []) : [];
  const at = (i: number) => { if (!open) return; const j = list.findIndex(r => r.path === open.path) + i; if (list[j]) setOpen(list[j]); };
  useEffect(() => { const k = (e: KeyboardEvent) => { if (!open) return; if (e.key === "Escape") setOpen(null); if (e.key === "ArrowRight") at(1); if (e.key === "ArrowLeft") at(-1); }; window.addEventListener("keydown", k); return () => window.removeEventListener("keydown", k); });
  return (
    <div className="grid gap-4 md:gap-5">
      {/* on a phone: the search on its own line, the places as a strip that scrolls sideways under a thumb */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative order-first w-full md:order-last md:ml-auto md:w-72"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" /><Input className="h-10 rounded-full pl-9 md:h-9 md:rounded-sm md:pl-8" type="search" placeholder="Search names and places" value={q} onChange={e => { setQ(e.target.value); setBook(null); }} /></div>
        <div className="no-scrollbar flex w-full items-center gap-2 overflow-x-auto md:w-auto md:flex-wrap md:overflow-visible">
          {book ? <button onClick={() => setBook(null)} className="flex h-8 shrink-0 items-center gap-1.5 text-[15px] text-muted-foreground hover:text-foreground md:text-sm"><ArrowLeft className="h-4 w-4" />Library</button> : <><button onClick={() => setWhere("")} className={cn("pill h-8 shrink-0 border border-border px-3 md:h-auto md:px-2.5 md:py-1", !where && "pill-note border-transparent")}>All</button>{wheres.map(w => <button key={w} onClick={() => setWhere(w)} className={cn("pill h-8 shrink-0 border border-border px-3 md:h-auto md:px-2.5 md:py-1", where === w && "pill-note border-transparent")}>{w}</button>)}</>}
        </div>
      </div>
      {rows.length === 0 && <div className="hairline p-10 text-center text-sm text-muted-foreground">No pictures yet.</div>}
      {!book && <div className="grid grid-cols-2 gap-x-4 gap-y-6 sm:grid-cols-3 md:gap-x-5 md:gap-y-7 lg:grid-cols-5">{books.map(([k, pics]) => { const [w, d] = k.split("|"); const [a, b, c] = pics; return (
        <motion.button key={k} {...rise} onClick={() => setBook(k)} className="group grid w-full min-w-0 gap-2 text-left">
          <div className="relative aspect-[4/3] w-full">{c && <div className="absolute inset-0 translate-x-3 -translate-y-3 rotate-[3deg] overflow-hidden rounded-md border border-border bg-surface opacity-60"><img src={img(c.path)} alt="" className="h-full w-full object-cover" /></div>}{b && <div className="absolute inset-0 translate-x-1.5 -translate-y-1.5 rotate-[1.5deg] overflow-hidden rounded-md border border-border bg-surface opacity-80"><img src={img(b.path)} alt="" className="h-full w-full object-cover" /></div>}<div className="absolute inset-0 overflow-hidden rounded-md border border-border bg-surface shadow-sm transition-transform duration-300 group-hover:-translate-y-1"><img src={img(a.path)} alt={a.name} loading="lazy" className="h-full w-full object-cover" /></div><span className="absolute bottom-2 right-2 rounded-sm bg-background/90 px-1.5 py-0.5 text-[11px] font-medium">{pics.length}</span></div>
          <div className="grid min-w-0 gap-0.5"><div className="flex min-w-0 items-center gap-2"><Badge tone="note" className="shrink-0">{w}</Badge><span className="min-w-0 truncate text-sm font-medium">{dayLabel(d)}</span></div></div>
        </motion.button>); })}</div>}
      {book && <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">{list.map(p => <motion.button key={p.path} {...rise} onClick={() => setOpen(p)} className="group grid w-full min-w-0 gap-1 text-left"><div className="aspect-[4/3] w-full overflow-hidden rounded-md border border-border bg-surface"><img src={img(p.path)} alt={p.name} loading="lazy" className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.03]" /></div><div className="flex min-w-0 items-center gap-1"><span className="min-w-0 flex-1 truncate text-xs">{p.name}</span>{p.id !== undefined && <span role="button" title={p.starred ? "Kept: stays past the 14 days" : "Keep it past the 14 days"} onClick={e => { e.stopPropagation(); star(p); }} className={p.starred ? "text-amber-400" : "text-muted-foreground hover:text-foreground"}><Star className="h-3.5 w-3.5" fill={p.starred ? "currentColor" : "none"} /></span>}</div>{p.credit && <div className="truncate text-[10px] text-muted-foreground">{p.credit}</div>}<div className="truncate text-[10px] text-muted-foreground">{new Date(p.t * 1000).toLocaleTimeString()}</div></motion.button>)}</div>}
      <AnimatePresence>{open && <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-50 grid place-items-center bg-black/90 p-3 md:p-6" onClick={() => setOpen(null)}>
        <button aria-label="Close" onClick={() => setOpen(null)} className="absolute right-3 z-10 grid h-11 w-11 place-items-center rounded-full bg-white/10 text-white md:right-5" style={{ top: "calc(env(safe-area-inset-top, 0px) + 12px)" }}><X className="h-5 w-5" /></button>
        <motion.img key={open.path} initial={{ scale: 0.97, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} src={img(open.path)} alt={open.name} className="max-h-[78dvh] max-w-full rounded-md shadow-2xl" />
        <div className="mt-3 flex max-w-full flex-wrap items-center justify-center gap-x-3 gap-y-1 px-2 text-center text-xs text-white"><b className="truncate">{open.name}</b><span className="opacity-70">{open.where} · {new Date(open.t * 1000).toLocaleString()}</span></div></motion.div>}</AnimatePresence>
    </div>
  );
}
