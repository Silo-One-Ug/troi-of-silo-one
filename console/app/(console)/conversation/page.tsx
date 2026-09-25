"use client";
// The conversation as the page: the window takes the console's full width, the planet and the rocket behind it; inside,
// the words keep a reading column.
import { useEffect, useState } from "react";
import { Chat } from "@/components/chat";
import { eget } from "@/lib/edge";
export default function Conversation() {
  const [name, setName] = useState("Troi");
  useEffect(() => { eget("/config").then(c => setName(c.name)).catch(() => {}); }, []);
  return <div className="fill-page w-full md:h-[calc(100vh-7.5rem)]"><Chat name={name} /></div>;   // on a phone it fills the screen between the bars
}
