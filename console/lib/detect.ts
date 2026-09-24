// What this machine and browser can do, read from the browser alone. Nothing leaves the page unless the person saves it.
"use client";
export type Check = { key: string; label: string; ok: boolean | null; note: string };
export type Machine = { os: string; browser: string; device: string; cores: number; memory: string; gpu: string; screen: string; lang: string; tz: string; online: boolean; touch: boolean; battery?: string };

export function machine(): Machine {
  const ua = navigator.userAgent; const d: any = (navigator as any).userAgentData;
  const os = d?.platform || (/Mac/.test(ua) ? "macOS" : /Windows/.test(ua) ? "Windows" : /Android/.test(ua) ? "Android" : /iPhone|iPad/.test(ua) ? "iOS" : /Linux/.test(ua) ? "Linux" : "unknown");
  const b = d?.brands?.find((x: any) => !/Not|Chromium/.test(x.brand)) || d?.brands?.[0];
  const browser = b ? `${b.brand} ${b.version}` : /Firefox\/(\d+)/.test(ua) ? `Firefox ${RegExp.$1}` : /Version\/(\d+).*Safari/.test(ua) ? `Safari ${RegExp.$1}` : /Chrome\/(\d+)/.test(ua) ? `Chrome ${RegExp.$1}` : "unknown";
  let gpu = "unknown"; try { const c = document.createElement("canvas"); const gl: any = c.getContext("webgl2") || c.getContext("webgl"); const ext = gl?.getExtension("WEBGL_debug_renderer_info"); gpu = ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl ? "WebGL, renderer hidden" : "no WebGL"; } catch {}
  const mem = (navigator as any).deviceMemory; const mobile = d?.mobile ?? /Mobi|Android|iPhone/.test(ua);
  return { os, browser, device: mobile ? "phone or tablet" : "desktop or laptop", cores: navigator.hardwareConcurrency || 0, memory: mem ? `${mem} GB+` : "not exposed", gpu: String(gpu).replace(/ANGLE \((.*)\)/, "$1").slice(0, 60), screen: `${screen.width}×${screen.height} @${Math.round(devicePixelRatio * 10) / 10}x`, lang: navigator.language, tz: Intl.DateTimeFormat().resolvedOptions().timeZone, online: navigator.onLine, touch: navigator.maxTouchPoints > 0 };
}

export async function battery(): Promise<string | undefined> {
  try { const b = await (navigator as any).getBattery?.(); if (!b) return; return `${Math.round(b.level * 100)}%${b.charging ? ", charging" : ""}`; } catch { return; }
}

export function compatibility(): Check[] {
  const has = (ok: boolean, label: string, key: string, yes: string, no: string): Check => ({ key, label, ok, note: ok ? yes : no });
  let storage = false; try { localStorage.setItem("silo.t", "1"); localStorage.removeItem("silo.t"); storage = true; } catch {}
  let webgl = false; try { const c = document.createElement("canvas"); webgl = !!(c.getContext("webgl2") || c.getContext("webgl")); } catch {}
  return [
    has(window.isSecureContext, "Secure context", "secure", "https or localhost: the microphone and camera can be asked for", "Serve the console over https (or localhost); browsers refuse the microphone otherwise"),
    has("WebSocket" in window, "Live channels", "ws", "WebSockets for voice and devices", "No WebSocket: voice and devices cannot connect"),
    has(!!(window.AudioContext || (window as any).webkitAudioContext), "Audio", "audio", "Web Audio for the spoken replies", "No Web Audio: replies will not be spoken"),
    has(!!navigator.mediaDevices?.getUserMedia, "Microphone and camera access", "media", "The browser can ask for them", "No media devices API in this browser"),
    has(webgl, "3D", "webgl", "WebGL for the globe and the board", "No WebGL: the globe falls back to a still"),
    has(storage, "Local storage", "storage", "Your sign-in stays on this machine", "Storage is blocked: you will sign in each visit"),
    has("Notification" in window, "Notifications", "notify", "The console can tap you on the shoulder", "No notifications in this browser"),
    has(typeof ReadableStream !== "undefined" && "TextDecoder" in window, "Streaming", "stream", "Replies arrive as they are written", "No streaming: replies arrive whole"),
  ];
}
