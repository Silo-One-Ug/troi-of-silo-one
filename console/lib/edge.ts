// The console talks to the agent's server on this Mac (troi-console/server.py, http://127.0.0.1:8796) and the parts it
// fronts; localStorage "silo.edge" (or NEXT_PUBLIC_EDGE_URL at build time) points it at another one, for tests.
"use client";
export function edgeUrl(): string {
  try { const u = typeof window !== "undefined" ? localStorage.getItem("silo.edge") : null; if (u) return u; } catch {}
  if (process.env.NEXT_PUBLIC_EDGE_URL) return process.env.NEXT_PUBLIC_EDGE_URL;
  // opened from another device (a phone on the same network): the agent is on the host the page came from, not on the phone
  try { const h = typeof window !== "undefined" ? location.hostname : ""; if (h && h !== "localhost" && h !== "127.0.0.1") return `${location.protocol}//${h}:8796`; } catch {}
  return "http://127.0.0.1:8796";
}
export const unlockToken = () => { try { const j = JSON.parse(localStorage.getItem("silo.unlock") || "null"); return j && j.until * 1000 > Date.now() ? j.token : ""; } catch { return ""; } };
export const rememberUnlock = (token: string, until: number) => { try { localStorage.setItem("silo.unlock", JSON.stringify({ token, until })); } catch {} };
export async function eget<T = any>(path: string): Promise<T> { const r = await fetch(edgeUrl() + path, { cache: "no-store" }); if (!r.ok) throw new Error(`${path}: ${r.status}`); return r.json(); }

// ONE poll of /state for the whole page. The layout, the dock, the conversation and the eyes page each used to poll it on their own,
// every half second or so, whatever was happening: four requests a second from one tab, all day. Now one loop feeds them all, and
// its pace follows the moment: fast while the agent works or speaks, slow when idle, slower still when the tab is hidden, and a
// little slower again in the saver power mode (lib/power sets window.__onBattery; the mode itself is in localStorage). A tab coming
// back from hiding polls at once.
type StateListener = (d: State | null) => void;
const feed = { subs: new Set<StateListener>(), last: null as State | null, timer: 0 as any, on: false, inflight: false, wake: false };
export function statePace(d: State | null): number {
  const hidden = typeof document !== "undefined" && document.visibilityState === "hidden";
  let saver = false; try { const m = localStorage.getItem("silo.power"); saver = m === "saver" || (m !== "full" && (window as any).__onBattery === true); } catch {}
  const busy = !!d && d.voice && d.state !== "idle" && d.state !== "off";
  return hidden ? 4000 : busy ? (saver ? 700 : 500) : (saver ? 2500 : 1500);
}
async function pump() {
  if (!feed.on || feed.inflight) { feed.wake = feed.wake || feed.inflight; return; }
  feed.inflight = true; let d: State | null = null;
  try { d = await eget("/state"); } catch { d = null; }
  feed.inflight = false; feed.last = d;
  feed.subs.forEach(fn => { try { fn(d); } catch {} });
  if (!feed.on) return;
  const delay = feed.wake ? 0 : statePace(d); feed.wake = false;
  clearTimeout(feed.timer); feed.timer = setTimeout(pump, delay);
}
export function subscribeState(fn: StateListener): () => void {
  feed.subs.add(fn); if (feed.last) fn(feed.last);
  if (!feed.on) { feed.on = true; pump(); }
  return () => { feed.subs.delete(fn); if (feed.subs.size === 0) { clearTimeout(feed.timer); feed.on = false; } };
}
export const lastState = (): State | null => feed.last;
if (typeof document !== "undefined") document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible" && feed.on) { clearTimeout(feed.timer); pump(); } });
export async function epost<T = any>(path: string, body: any = {}): Promise<T> {
  const tok = unlockToken(); const r = await fetch(edgeUrl() + path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(tok ? { ...body, unlock: tok } : body) });
  const j = await r.json().catch(() => ({})); return { ...j, _status: r.status } as T;
}
export const img = (p: string) => p.startsWith("/img?") ? edgeUrl() + p : edgeUrl() + "/img?p=" + encodeURIComponent(p);
export type Config = { name: string; key: string; mic_mode: string; permission_mode: string; model: string; deep_model: string; models?: Record<string, string>; session_model?: string; effort: string; wake_word: boolean; eyes: string; voice_id: string; voice_print: boolean; voice_id_threshold: number; pin_set: boolean; guard: boolean; guarded: boolean; face_env: boolean; face_print: boolean; face_id_threshold: number; vault: string; brief_time: string; wake_names: string[]; face: string; hands: string; tts: string; elevenlabs_voice: string; elevenlabs_voice_name?: string; elevenlabs_key: boolean; kokoro_voice: string; welcomed: boolean; owner: string; lan?: boolean | "tailscale"; tailscale?: { name: string; ip: string; https?: boolean } | null };
export type State = { state: string; voice: boolean; ui: any[]; settings: any; pending: Pending[]; partial: string; wave: number[]; live: string; agents?: number; tool?: { name: string; detail: string } | null };
export type Pending = { id: string; kind?: string; src: string; why: string; at: number };
export type Row = { role: string; text: string; t?: string; why?: string; meta?: any };
export type Card = { name: string; value: any; t?: number };
export const talkShape = (): "column" | "floating" => { try { return localStorage.getItem("silo.talkShape") === "floating" ? "floating" : "column"; } catch { return "column"; } };
export const setTalkShape = (s: "column" | "floating") => { try { localStorage.setItem("silo.talkShape", s); } catch {} window.dispatchEvent(new Event("silo:shape")); };

/** The console's own events between components (the directive follower and the pages it steers). */
export const emit = (name: string, detail?: any) => { try { window.dispatchEvent(new CustomEvent("silo:" + name, { detail })); } catch {} };
export const on = (name: string, fn: (d: any) => void) => { const h = (e: Event) => fn((e as CustomEvent).detail); window.addEventListener("silo:" + name, h); return () => window.removeEventListener("silo:" + name, h); };
