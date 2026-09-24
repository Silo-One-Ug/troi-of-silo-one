"use client";
// The theme switch in the bar: what you see is what it shows (a moon on the dark console, a sun on the light one),
// and a click goes to the other. "System" stays a choice on the phone's More page and is honoured at boot; from here
// it is simply the theme it resolves to, so a click always changes something you can see.
import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
import { getTheme, setTheme, applyTheme, isDark } from "@/lib/theme";
export function ThemeToggle() {
  const [dark, setDark] = useState(true);
  useEffect(() => {
    setDark(isDark(getTheme()));
    const mq = window.matchMedia("(prefers-color-scheme: dark)"); const on = () => { applyTheme(getTheme()); setDark(isDark(getTheme())); };
    mq.addEventListener("change", on); return () => mq.removeEventListener("change", on);
  }, []);
  const Icon = dark ? Moon : Sun;
  return <button onClick={() => { const n = dark ? "light" : "dark"; setTheme(n); setDark(n === "dark"); }} title={dark ? "Dark. Click for light" : "Light. Click for dark"} aria-label={dark ? "Switch to the light theme" : "Switch to the dark theme"} className="text-muted-foreground hover:text-foreground"><Icon className="h-4 w-4" /></button>;
}
