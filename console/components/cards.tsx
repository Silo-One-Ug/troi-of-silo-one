"use client";
// Generative UI: cards drawn from the console tools' data (silo.headlines, silo.pictures), never from prose.
import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ExternalLink, Newspaper, X } from "lucide-react";
import { Badge } from "./ui/badge";
import { rise } from "@/lib/motion";

export type Headline = { title: string; source: string; url: string; when: string; summary?: string };
export type Picture = { url: string; page: string; title: string; author?: string; license?: string; source: string };

export function HeadlinesCard({ scope, topic, items }: { scope: string; topic?: string; items: Headline[] }) {
  return (
    <motion.div {...rise} className="hairline max-w-[85%] overflow-hidden text-sm">
      <div className="flex items-center gap-2 border-b border-border bg-surface px-3 py-2"><Newspaper className="h-4 w-4 text-primary" /><b>{topic ? `On “${topic}”` : scope === "world" ? "World headlines" : scope === "all" ? "Headlines" : "Uganda headlines"}</b><span className="ml-auto text-xs text-muted-foreground">{items.length} from the outlets</span></div>
      {items.length === 0 && <div className="p-3 text-xs text-muted-foreground">Nothing came back from the outlets.</div>}
      <ol className="divide-y divide-border">
        {items.map((h, i) => (
          <li key={i} className="grid gap-0.5 px-3 py-2">
            <div className="flex items-center gap-2"><Badge tone="note">{h.source}</Badge><span className="text-xs text-muted-foreground">{h.when}</span></div>
            <a href={h.url} target="_blank" rel="noreferrer" className="font-medium hover:text-primary">{h.title} <ExternalLink className="inline h-3 w-3 text-muted-foreground" /></a>
            {h.summary && <div className="text-xs text-muted-foreground">{h.summary}</div>}
          </li>
        ))}
      </ol>
    </motion.div>
  );
}

export function PicturesGrid({ query, items }: { query: string; items: Picture[] }) {
  const [open, setOpen] = useState<Picture | null>(null);
  return (
    <motion.div {...rise} className="hairline max-w-[85%] overflow-hidden text-sm">
      <div className="flex items-center gap-2 border-b border-border bg-surface px-3 py-2"><b>Pictures · {query}</b><span className="ml-auto text-xs text-muted-foreground">{items.length}, credited</span></div>
      {items.length === 0 && <div className="p-3 text-xs text-muted-foreground">No free picture found.</div>}
      <div className="grid grid-cols-2 gap-2 p-2 sm:grid-cols-3">
        {items.map((p, i) => (
          <button key={i} onClick={() => setOpen(p)} className="group grid gap-1 text-left">
            <div className="aspect-[4/3] overflow-hidden rounded-sm bg-surface"><img src={p.url} alt={p.title} loading="lazy" className="h-full w-full object-cover transition-transform group-hover:scale-[1.03]" /></div>
            <div className="truncate text-xs">{p.title}</div>
            <div className="truncate text-[10px] text-muted-foreground">{p.source}{p.author ? ` · ${p.author}` : ""}{p.license ? ` · ${p.license}` : ""}</div>
          </button>
        ))}
      </div>
      <AnimatePresence>{open && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-50 grid place-items-center bg-black/80 p-6" onClick={() => setOpen(null)}>
          <motion.img initial={{ scale: 0.96 }} animate={{ scale: 1 }} src={open.url} alt={open.title} className="max-h-[80vh] max-w-full rounded-md shadow-2xl" />
          <div className="mt-3 flex items-center gap-3 text-xs text-white"><span>{open.title}</span><span className="opacity-70">{open.source}{open.author ? ` · ${open.author}` : ""}{open.license ? ` · ${open.license}` : ""}</span>{open.page && <a href={open.page} target="_blank" rel="noreferrer" className="underline" onClick={e => e.stopPropagation()}>source page</a>}<X className="h-4 w-4" /></div>
        </motion.div>)}
      </AnimatePresence>
    </motion.div>
  );
}
