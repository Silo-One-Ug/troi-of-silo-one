"use client";
// The conversation alone, for the desktop floater: the ring's second panel (troi-console/ring.py) loads this route in
// a translucent native window that floats above every app. No bar, no tabs, no planet; the page is transparent so the
// panel's own glass shows through, and the conversation fills whatever size the panel is dragged to.
import { useEffect, useState } from "react";
import { Chat } from "@/components/chat";
import { eget } from "@/lib/edge";

export default function Float() {
  const [name, setName] = useState("Troi");
  useEffect(() => { eget("/config").then(c => setName(c.name)).catch(() => {}); }, []);
  useEffect(() => { document.documentElement.classList.add("float-panel"); return () => document.documentElement.classList.remove("float-panel"); }, []);
  return (
    <>
      <style>{`html.float-panel, html.float-panel body { background: transparent !important; overflow: hidden; } html.float-panel body { font-size: 14px; }`}</style>
      <div className="glass flex h-[100dvh] w-full flex-col overflow-hidden rounded-none border-0 bg-transparent"><Chat name={name} embedded /></div>
    </>
  );
}
