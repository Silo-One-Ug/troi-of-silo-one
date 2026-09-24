// Theme: system, light or dark. The choice lives in this browser; the class on <html> drives the tokens (globals.css).
"use client";
export type Theme = "system" | "light" | "dark";
const KEY = "silo.theme";
export function getTheme(): Theme { try { return (localStorage.getItem(KEY) as Theme) || "dark"; } catch { return "system"; } }
/** What a choice comes to on this screen: "system" follows the Mac. */
export function isDark(t: Theme): boolean { return t === "dark" || (t === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches); }
export function applyTheme(t: Theme) {
  const dark = isDark(t);
  document.documentElement.classList.toggle("dark", dark); document.documentElement.style.colorScheme = dark ? "dark" : "light";
}
export function setTheme(t: Theme) { try { localStorage.setItem(KEY, t); } catch {} applyTheme(t); }
/** Runs before paint (inlined in the root layout) so a dark page never flashes white. */
export const THEME_BOOT = `(function(){try{var t=localStorage.getItem("silo.theme")||"dark";var d=t==="dark"||(t==="system"&&matchMedia("(prefers-color-scheme: dark)").matches);if(d){document.documentElement.classList.add("dark");document.documentElement.style.colorScheme="dark"}}catch(e){}})();`;
