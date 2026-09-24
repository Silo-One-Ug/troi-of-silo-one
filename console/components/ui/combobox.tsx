"use client";
// The one picker of the console: a button that opens a searchable list. Type to filter, arrows to move, Enter to pick,
// Escape to close. No native <select> anywhere.
import * as React from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Check, ChevronsUpDown, Loader2, Search } from "lucide-react";
import { cn } from "@/lib/utils";

export type ComboOption = { value: string; label: string; hint?: string };

export function Combobox({ value, options, onChange, placeholder = "Choose…", empty = "Nothing matches.", loading, onOpen, className, disabled }: {
  value: string; options: ComboOption[]; onChange: (v: string) => void; placeholder?: string; empty?: string; loading?: boolean; onOpen?: () => void; className?: string; disabled?: boolean;
}) {
  const [open, setOpen] = React.useState(false); const [q, setQ] = React.useState(""); const [at, setAt] = React.useState(0);
  const root = React.useRef<HTMLDivElement>(null); const list = React.useRef<HTMLDivElement>(null); const input = React.useRef<HTMLInputElement>(null);
  const cur = options.find(o => o.value === value);
  const shown = React.useMemo(() => { const t = q.trim().toLowerCase(); return t ? options.filter(o => (o.label + " " + (o.hint || "")).toLowerCase().includes(t)) : options; }, [q, options]);
  const show = () => { if (disabled) return; setOpen(true); setQ(""); setAt(Math.max(0, options.findIndex(o => o.value === value))); onOpen?.(); };
  const pick = (o?: ComboOption) => { if (!o) return; onChange(o.value); setOpen(false); };
  React.useEffect(() => { if (!open) return; input.current?.focus(); const out = (e: PointerEvent) => { if (!root.current?.contains(e.target as Node)) setOpen(false); }; addEventListener("pointerdown", out); return () => removeEventListener("pointerdown", out); }, [open]);
  React.useEffect(() => { setAt(a => Math.min(a, Math.max(0, shown.length - 1))); }, [shown.length]);
  React.useEffect(() => { list.current?.querySelector<HTMLElement>(`[data-i="${at}"]`)?.scrollIntoView({ block: "nearest" }); }, [at, open]);
  const key = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setAt(a => Math.min(shown.length - 1, a + 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setAt(a => Math.max(0, a - 1)); }
    else if (e.key === "Enter") { e.preventDefault(); pick(shown[at]); }
    else if (e.key === "Escape" || e.key === "Tab") setOpen(false);
  };
  return (
    <div ref={root} className={cn("relative min-w-0", className)}>
      <button type="button" disabled={disabled} aria-haspopup="listbox" aria-expanded={open} onClick={() => (open ? setOpen(false) : show())} onKeyDown={e => { if (!open && (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ")) { e.preventDefault(); show(); } }}
        className="flex h-9 w-full min-w-0 items-center gap-2 rounded-sm border border-border bg-background px-3 text-left text-sm transition-colors hover:bg-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 disabled:opacity-50">
        <span className={cn("min-w-0 flex-1 truncate", !cur && "text-muted-foreground")}>{cur ? cur.label : placeholder}{cur?.hint && <span className="text-muted-foreground"> · {cur.hint}</span>}</span>
        {loading ? <Loader2 className="h-4 w-4 shrink-0 animate-spin text-muted-foreground" /> : <ChevronsUpDown className="h-4 w-4 shrink-0 text-muted-foreground" />}
      </button>
      <AnimatePresence>{open && (
        <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }} transition={{ duration: 0.14 }} className="absolute left-0 right-0 top-full z-50 mt-1 overflow-hidden rounded-md border border-border bg-background shadow-2xl">
          <div className="flex items-center gap-2 border-b border-border px-3"><Search className="h-4 w-4 shrink-0 text-muted-foreground" />
            <input ref={input} value={q} onChange={e => { setQ(e.target.value); setAt(0); }} onKeyDown={key} placeholder="Search…" role="combobox" aria-expanded aria-controls="combo-list" aria-activedescendant={shown[at] ? `combo-${at}` : undefined} className="h-9 w-full min-w-0 bg-transparent text-sm outline-none placeholder:text-muted-foreground" /></div>
          <div ref={list} id="combo-list" role="listbox" className="max-h-64 overflow-y-auto p-1">
            {loading && !options.length ? <div className="flex items-center gap-2 px-2 py-3 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" />Loading…</div>
              : shown.length === 0 ? <div className="px-2 py-3 text-sm text-muted-foreground">{empty}</div>
              : shown.map((o, i) => (
                <div key={o.value} id={`combo-${i}`} data-i={i} role="option" aria-selected={o.value === value} onPointerMove={() => setAt(i)} onClick={() => pick(o)}
                  className={cn("flex cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 text-sm", i === at && "bg-accent text-accent-foreground")}>
                  <Check className={cn("h-4 w-4 shrink-0", o.value === value ? "opacity-100" : "opacity-0")} />
                  <span className="min-w-0 flex-1 truncate">{o.label}</span>{o.hint && <span className="shrink-0 truncate text-xs text-muted-foreground max-w-[45%]">{o.hint}</span>}
                </div>))}
          </div>
        </motion.div>)}
      </AnimatePresence>
    </div>
  );
}
