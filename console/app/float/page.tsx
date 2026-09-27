"use client";
// The conversation alone, for the desktop floater: the ring's second panel (troi-console/ring.py) loads this route in
// a translucent native window that floats above every app. No bar, no tabs, no planet; the page is transparent so the
// panel's own glass shows through, and the conversation fills whatever size the panel is dragged to. The theme comes
// from the settings (`theme`, kept there by the console's own switch), since this web view shares no storage with the
// console's browser: a light console gives a light floater (Paul, 2026-09-27).
import { useEffect, useState } from "react";
import { Chat } from "@/components/chat";
import { eget, subscribeState } from "@/lib/edge";
import { DEFAULT_NAME, agentName, rememberName } from "@/lib/name";
import { applyTheme, isTheme } from "@/lib/theme";

export default function Float() {
  const [name, setName] = useState(DEFAULT_NAME);
  useEffect(() => { setName(agentName()); eget("/config").then(c => { rememberName(c.name); setName(c.name || agentName()); }).catch(() => {}); }, []);
  useEffect(() => { document.documentElement.classList.add("float-panel"); return () => document.documentElement.classList.remove("float-panel"); }, []);
  useEffect(() => subscribeState(d => { const t = d?.settings?.theme; applyTheme(isTheme(t) ? t : "system"); }), []);
  return (
    <>
      <style>{`html.float-panel, html.float-panel body { background: transparent !important; overflow: hidden; } html.float-panel body { font-size: 14px; }`}</style>
      <div className="glass flex h-[100dvh] w-full flex-col overflow-hidden rounded-none border-0 bg-transparent"><Chat name={name} embedded /></div>
    </>
  );
}
