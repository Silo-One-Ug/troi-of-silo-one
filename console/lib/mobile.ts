"use client";
// One rule decides the phone layout: narrower than 768 px, or a touch screen shorter than 600 px (a phone held
// sideways), and the console is a native-style app (a bar at the top, tabs at the bottom, one column, full-screen
// views); otherwise it is the desktop console with its floating bar. CSS does the styling with md: (the same rule,
// inverted, in tailwind.config.ts); this hook is for the few things that must not render at all on the other side
// (polling, the floating conversation, the galaxy's mobile mode).
import { useEffect, useState } from "react";
export const MOBILE = "(max-width: 767px), ((pointer: coarse) and (max-height: 600px))";
export const isMobile = () => { try { return matchMedia(MOBILE).matches; } catch { return false; } };
export function useMobile(): boolean {
  const [m, setM] = useState(false);
  useEffect(() => { const q = matchMedia(MOBILE); const on = () => setM(q.matches); on(); q.addEventListener("change", on); return () => q.removeEventListener("change", on); }, []);
  return m;
}
