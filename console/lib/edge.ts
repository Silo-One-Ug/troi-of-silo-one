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
export async function epost<T = any>(path: string, body: any = {}): Promise<T> {
  const tok = unlockToken(); const r = await fetch(edgeUrl() + path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(tok ? { ...body, unlock: tok } : body) });
  const j = await r.json().catch(() => ({})); return { ...j, _status: r.status } as T;
}
export const img = (p: string) => p.startsWith("/img?") ? edgeUrl() + p : edgeUrl() + "/img?p=" + encodeURIComponent(p);
export type Config = { name: string; key: string; mic_mode: string; permission_mode: string; model: string; deep_model: string; effort: string; wake_word: boolean; eyes: string; voice_id: string; voice_print: boolean; voice_id_threshold: number; pin_set: boolean; guard: boolean; guarded: boolean; face_env: boolean; face_print: boolean; face_id_threshold: number; vault: string; brief_time: string; wake_names: string[]; face: string; hands: string; tts: string; elevenlabs_voice: string; elevenlabs_voice_name?: string; elevenlabs_key: boolean; kokoro_voice: string; welcomed: boolean; owner: string; lan?: boolean | "tailscale"; tailscale?: { name: string; ip: string; https?: boolean } | null };
export type State = { state: string; voice: boolean; ui: any[]; settings: any; pending: Pending[]; partial: string; wave: number[]; live: string; agents?: number };
export type Pending = { id: string; kind?: string; src: string; why: string; at: number };
export type Row = { role: string; text: string; t?: string; why?: string; meta?: any };
export type Card = { name: string; value: any; t?: number };
export const talkShape = (): "column" | "floating" => { try { return localStorage.getItem("silo.talkShape") === "floating" ? "floating" : "column"; } catch { return "column"; } };
export const setTalkShape = (s: "column" | "floating") => { try { localStorage.setItem("silo.talkShape", s); } catch {} window.dispatchEvent(new Event("silo:shape")); };

/** The console's own events between components (the directive follower and the pages it steers). */
export const emit = (name: string, detail?: any) => { try { window.dispatchEvent(new CustomEvent("silo:" + name, { detail })); } catch {} };
export const on = (name: string, fn: (d: any) => void) => { const h = (e: Event) => fn((e as CustomEvent).detail); window.addEventListener("silo:" + name, h); return () => window.removeEventListener("silo:" + name, h); };
