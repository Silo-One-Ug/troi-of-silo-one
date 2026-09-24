"use client";
import { useEffect, useState } from "react";
import { Monitor, Moon, Sun } from "lucide-react";
import { getTheme, setTheme, applyTheme, type Theme } from "@/lib/theme";
const NEXT: Record<Theme, Theme> = { system: "light", light: "dark", dark: "system" };
export function ThemeToggle() {
  const [t, setT] = useState<Theme>("system");
  useEffect(() => { setT(getTheme()); const mq = window.matchMedia("(prefers-color-scheme: dark)"); const on = () => applyTheme(getTheme()); mq.addEventListener("change", on); return () => mq.removeEventListener("change", on); }, []);
  const Icon = t === "dark" ? Moon : t === "light" ? Sun : Monitor;
  return <button onClick={() => { const n = NEXT[t]; setTheme(n); setT(n); }} title={`Theme: ${t} (click to change)`} className="text-muted-foreground hover:text-foreground"><Icon className="h-4 w-4" /></button>;
}
