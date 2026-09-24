"use client";
// A bottom sheet, as a phone expects one: it slides up over the dimmed page, has a grip, closes on the dim, the grip,
// a downward drag or Escape, and keeps clear of the home indicator.
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "framer-motion";
import { cn } from "@/lib/utils";

export function Sheet({ open, onClose, title, children, className }: { open: boolean; onClose: () => void; title?: string; children: React.ReactNode; className?: string }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);
  useEffect(() => { if (!open) return; const k = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); }; addEventListener("keydown", k); return () => removeEventListener("keydown", k); }, [open, onClose]);
  if (!mounted) return null;
  // a portal to the body: a fixed sheet inside a frosted bar would be positioned against that bar (backdrop-filter makes a containing block), not the screen
  return createPortal(
    <AnimatePresence>{open && (<>
      <motion.div key="dim" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }} className="fixed inset-0 z-50 bg-black/50" onClick={onClose} />
      <motion.div key="sheet" role="dialog" aria-modal="true" aria-label={title} initial={{ y: "100%" }} animate={{ y: 0 }} exit={{ y: "100%" }} transition={{ type: "spring", stiffness: 420, damping: 40 }}
        drag="y" dragConstraints={{ top: 0, bottom: 0 }} dragElastic={{ top: 0, bottom: 0.6 }} onDragEnd={(_, i) => { if (i.offset.y > 80 || i.velocity.y > 600) onClose(); }}
        className={cn("glass fixed inset-x-0 bottom-0 z-50 rounded-t-2xl border-b-0 px-5 pt-2 shadow-2xl", className)} style={{ paddingBottom: "calc(env(safe-area-inset-bottom, 0px) + 20px)" }}>
        <button aria-label="Close" onClick={onClose} className="mx-auto mb-3 block h-1.5 w-10 rounded-full bg-muted-foreground/40" />
        {title && <div className="mb-3 text-[17px] font-semibold">{title}</div>}
        {children}
      </motion.div>
    </>)}</AnimatePresence>,
    document.body);
}
