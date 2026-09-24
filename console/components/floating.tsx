"use client";
// The floating conversation: a pane that stays inside the window and above the bar. Drag it by its header, resize it
// from the corner; its place and size are remembered. Double-click the grip to put it back.
import { useCallback, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { GripHorizontal } from "lucide-react";
import { Chat } from "./chat";
import { on } from "@/lib/edge";

const BAR = 88, GAP = 16, MIN_W = 360, MIN_H = 260;
type Box = { x: number; y: number; w: number; h: number };
const fallback = (): Box => { const w = Math.min(520, innerWidth - 2 * GAP), h = Math.min(Math.round(innerHeight * 0.5), innerHeight - BAR - 2 * GAP); return { x: innerWidth - w - GAP, y: innerHeight - BAR - h - GAP, w, h }; };
const clampBox = (b: Box): Box => { const w = Math.max(MIN_W, Math.min(b.w, innerWidth - 2 * GAP)), h = Math.max(MIN_H, Math.min(b.h, innerHeight - BAR - 2 * GAP)); return { w, h, x: Math.max(GAP, Math.min(b.x, innerWidth - w - GAP)), y: Math.max(GAP, Math.min(b.y, innerHeight - BAR - h - GAP)) }; };

export function FloatingChat({ name }: { name: string }) {
  const [box, setBox] = useState<Box | null>(null); const drag = useRef<{ kind: "move" | "size"; sx: number; sy: number; b: Box } | null>(null);
  useEffect(() => { let b: Box | null = null; try { b = JSON.parse(localStorage.getItem("silo.floatBox") || "null"); } catch {} setBox(clampBox(b || fallback())); const on = () => setBox(x => x && clampBox(x)); addEventListener("resize", on); return () => removeEventListener("resize", on); }, []);
  const save = (b: Box) => { try { localStorage.setItem("silo.floatBox", JSON.stringify(b)); } catch {} };
  useEffect(() => on("tidy", () => { const b = clampBox(fallback()); setBox(b); save(b); }), []);   // "tidy the panes"
  const move = useCallback((e: PointerEvent) => { const d = drag.current; if (!d) return; const dx = e.clientX - d.sx, dy = e.clientY - d.sy; setBox(clampBox(d.kind === "move" ? { ...d.b, x: d.b.x + dx, y: d.b.y + dy } : { ...d.b, w: d.b.w + dx, h: d.b.h + dy })); }, []);
  const up = useCallback(() => { drag.current = null; removeEventListener("pointermove", move); setBox(b => { if (b) save(b); return b; }); }, [move]);
  const start = (kind: "move" | "size") => (e: React.PointerEvent) => { if (!box) return; e.preventDefault(); drag.current = { kind, sx: e.clientX, sy: e.clientY, b: box }; addEventListener("pointermove", move); addEventListener("pointerup", up, { once: true }); };
  if (!box) return null;
  return (
    <motion.div initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} style={{ left: box.x, top: box.y, width: box.w, height: box.h }} className="glass fixed z-30 flex flex-col overflow-hidden rounded-xl shadow-2xl">
      <div onPointerDown={start("move")} onDoubleClick={() => { const b = clampBox(fallback()); setBox(b); save(b); }} className="flex h-5 shrink-0 cursor-grab items-center justify-center text-muted-foreground active:cursor-grabbing" title="Drag; double-click to put it back"><GripHorizontal className="h-4 w-4" /></div>
      <div className="min-h-0 flex-1"><Chat name={name} embedded /></div>
      <div onPointerDown={start("size")} className="absolute bottom-0 right-0 h-4 w-4 cursor-nwse-resize" title="Resize" style={{ background: "linear-gradient(135deg, transparent 50%, hsl(var(--border)) 50%)" }} />
    </motion.div>
  );
}
