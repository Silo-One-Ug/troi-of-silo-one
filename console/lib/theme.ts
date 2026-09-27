// Theme: system, light or dark. The choice lives in this browser (the class on <html> drives the tokens, globals.css)
// and, since 2026-09-27, in the settings too (`theme`), so the desktop floater (a web view of its own, with no shared
// storage) and a spoken order ("light mode") reach every screen of the console.
"use client";
import { epost } from "@/lib/edge";
export type Theme = "system" | "light" | "dark";
const KEY = "silo.theme";
export function getTheme(): Theme { try { return (localStorage.getItem(KEY) as Theme) || "dark"; } catch { return "system"; } }
export const isTheme = (v: unknown): v is Theme => v === "system" || v === "light" || v === "dark";
/** What a choice comes to on this screen: "system" follows the Mac. */
export function isDark(t: Theme): boolean { return t === "dark" || (t === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches); }
export function applyTheme(t: Theme) {
  const dark = isDark(t);
  document.documentElement.classList.toggle("dark", dark); document.documentElement.style.colorScheme = dark ? "dark" : "light";
}
/** A choice made on this screen: kept here, applied, and told to the settings so the other screens follow. */
export function setTheme(t: Theme) { adoptTheme(t); epost("/settings", { theme: t }).catch(() => {}); }
/** A choice made elsewhere (the settings, another screen): kept here and applied, nothing echoed back. */
export function adoptTheme(t: Theme) { try { localStorage.setItem(KEY, t); } catch {} applyTheme(t); }
/** Runs before paint (inlined in the root layout) so a dark page never flashes white. */
export const THEME_BOOT = `(function(){try{var t=localStorage.getItem("silo.theme")||"dark";var d=t==="dark"||(t==="system"&&matchMedia("(prefers-color-scheme: dark)").matches);if(d){document.documentElement.classList.add("dark");document.documentElement.style.colorScheme="dark"}else{document.documentElement.style.colorScheme="light"}}catch(e){}})();`;
