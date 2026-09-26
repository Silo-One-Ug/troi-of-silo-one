"use client";
// The conversation as the page: the window takes the console's full width, the planet and the rocket behind it; inside,
// the words keep a reading column.
import { useEffect, useState } from "react";
import { Chat } from "@/components/chat";
import { eget } from "@/lib/edge";
import { useMobile } from "@/lib/mobile";
export default function Conversation() {
  const [name, setName] = useState("Troi"); const mobile = useMobile();
  useEffect(() => { eget("/config").then(c => setName(c.name)).catch(() => {}); }, []);
  // on a phone the page itself does not scroll while the conversation is open: the message list scrolls, the composer stays above the tabs
  useEffect(() => { if (!mobile) return; document.documentElement.classList.add("talk-lock"); return () => document.documentElement.classList.remove("talk-lock"); }, [mobile]);
  return <div className="fill-page w-full md:h-[calc(100vh-7.5rem)]"><Chat name={name} /></div>;   // on a phone it fills the screen between the bars
}
