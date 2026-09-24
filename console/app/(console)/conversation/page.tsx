"use client";
// The conversation as a column: the chat on the left third of space, the planet and the rocket on the right.
import { useEffect, useState } from "react";
import { Chat } from "@/components/chat";
import { eget } from "@/lib/edge";
export default function Conversation() {
  const [name, setName] = useState("Troi");
  useEffect(() => { eget("/config").then(c => setName(c.name)).catch(() => {}); }, []);
  return <div className="h-[calc(100vh-7.5rem)] w-full max-w-[680px]"><Chat name={name} /></div>;
}
