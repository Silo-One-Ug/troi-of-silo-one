// The page's power mode. "auto" follows the battery: saver while the Mac (or the phone) is discharging, full when plugged in or when
// the browser cannot say; "full" and "saver" are the owner's word for this device (localStorage, in Modes). Saver means the planet
// at a few frames a second without the glow, one pixel per point, and the page asking the agent's server less often when nothing
// is happening. Every part that cares reads effectivePower() or the usePower() hook and follows the "power" event.
import { useEffect, useState } from "react";
import { emit, on } from "@/lib/edge";

export type PowerMode = "auto" | "full" | "saver";
export const powerMode = (): PowerMode => { try { const v = localStorage.getItem("silo.power"); return v === "full" || v === "saver" ? v : "auto"; } catch { return "auto"; } };
export const setPowerMode = (m: PowerMode) => { try { localStorage.setItem("silo.power", m); } catch {} emit("power", m); };

let battery: any = null, discharging = false, asked = false;
function watchBattery() {
  if (asked || typeof navigator === "undefined" || typeof (navigator as any).getBattery !== "function") return;
  asked = true;
  (navigator as any).getBattery().then((b: any) => {
    battery = b;
    const upd = () => { const d = !b.charging; (window as any).__onBattery = d; if (d !== discharging) { discharging = d; emit("power", powerMode()); } };
    upd(); b.addEventListener("chargingchange", upd);
  }).catch(() => {});
}
// a host whose browser has no Battery API (the ring's pane is a WebKit view; Safari too) tells the page itself: window.__setBattery(true|false)
if (typeof window !== "undefined") (window as any).__setBattery = (d: boolean) => { d = !!d; (window as any).__onBattery = d; if (d !== discharging) { discharging = d; emit("power", powerMode()); } };
export const onBattery = () => { watchBattery(); return discharging; };
export const batteryLevel = (): number | null => battery ? Math.round(battery.level * 100) : null;
export const effectivePower = (): "full" | "saver" => { const m = powerMode(); return m === "auto" ? (onBattery() ? "saver" : "full") : m; };

export function usePower(): { mode: PowerMode; effective: "full" | "saver"; onBattery: boolean; level: number | null } {
  const [, tick] = useState(0);
  useEffect(() => { watchBattery(); return on("power", () => tick(x => x + 1)); }, []);
  return { mode: powerMode(), effective: effectivePower(), onBattery: onBattery(), level: batteryLevel() };
}
