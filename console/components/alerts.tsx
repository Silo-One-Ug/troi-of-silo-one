"use client";
// Alerts: the interface sounds and system notifications the native console had. A new approval, a due reminder, and a
// Telegram message while you are elsewhere each play a short cue (troi-console/assets/cue-*.wav, served by the agent at
// /sounds/). With the bell on, approvals and reminders raise a notification, and replies and Telegram messages do too
// while the console is not the page you are looking at. "cues": false in the settings (movie mode sets it) silences the sounds.
import { useEffect, useRef } from "react";
import { edgeUrl, eget, lastState } from "@/lib/edge";
import { DEFAULT_NAME, agentName, rememberName } from "@/lib/name";

export const notifyOn = () => { try { return localStorage.getItem("silo.notify") === "1" && "Notification" in window && Notification.permission === "granted"; } catch { return false; } };
/** Wanted here, whether or not the browser has granted them yet (the bell shows the difference). */
export const notifyWanted = () => { try { return localStorage.getItem("silo.notify") === "1"; } catch { return false; } };
export const setNotify = (on: boolean) => { try { localStorage.setItem("silo.notify", on ? "1" : "0"); } catch {} };
/** One of the interface cues (approval, reminder, telegram), unless the settings say cues are off. */
export const cueSound = (kind: string) => { try { if (lastState()?.settings?.cues === false) return; const a = new Audio(edgeUrl() + "/sounds/cue-" + kind + ".wav"); a.volume = 0.6; a.play().catch(() => {}); } catch {} };
/** The agent ringing the bell itself (console.sh notify, for work you asked to be told about): a system notification when
 *  they are on, the reminder cue always; the words above the bar are the directive's own doing. */
export const ringBell = (title: string, body: string, tag = "troi-notify") => {
  cueSound("reminder");
  if (!notifyOn()) return false;
  try { const n = new Notification(title, { body: body.slice(0, 180), tag }); n.onclick = () => { window.focus(); n.close(); }; return true; } catch { return false; }
};
const LABEL: Record<string, string> = { trash: "wants to move something to the Trash", kill: "wants to force-quit an app", click: "wants to make a risky click", setting: "wants a protected setting changed" };

export function Alerts() {
  const seen = useRef<Set<string> | null>(null); const pos = useRef<number | null>(null); const cues = useRef(true); const name = useRef(DEFAULT_NAME); const cued = useRef(new Set<string>());
  useEffect(() => {
    let stop = false;
    const cue = (kind: string, tag: string) => {
      if (!cues.current || cued.current.has(tag)) return;
      cued.current.add(tag); if (cued.current.size > 400) cued.current.clear();
      try { const a = new Audio(edgeUrl() + "/sounds/cue-" + kind + ".wav"); a.volume = 0.6; a.play().catch(() => {}); } catch {}
    };
    const notify = (title: string, body: string, tag: string) => {
      if (!notifyOn()) return;
      try { const n = new Notification(title, { body: body.slice(0, 180), tag }); n.onclick = () => { window.focus(); n.close(); }; } catch {}
    };
    const tick = async () => {
      if (stop) return;
      try {
        const s = await eget("/state"); cues.current = s.settings?.cues !== false;
        const pending: any[] = s.pending || [];
        if (seen.current) for (const p of pending) if (!seen.current.has(p.id)) {
          cue("approval", "ap-" + p.id); notify(`${name.current} ${LABEL[p.kind || "trash"] || "needs you"}`, String(p.src || ""), "ap-" + p.id);
        }
        seen.current = new Set(pending.map(p => p.id));
        if (pos.current === null) pos.current = (await eget("/history?limit=1")).pos ?? 0;   // from now on: old lines are history
        else {
          const d = await eget(`/transcript?pos=${pos.current}`); pos.current = d.pos;
          for (const it of d.items || []) {
            const text = String(it.text || ""); const key = (it.t || "") + text.slice(0, 40);
            if (it.role === "note" && /^(Reminder due|Pulse: reminder)/.test(text)) { cue("reminder", "rm-" + key); notify("Reminder", text, "rm-" + key); }
            else if (it.role === "you" && text.startsWith("📱") && document.hidden) { cue("telegram", "tg-" + key); notify("Telegram", text.slice(2).trim(), "tg-" + key); }
            else if (it.role === "agent" && document.hidden) notify(name.current, text, "troi-reply");
          }
        }
      } catch {}
      setTimeout(tick, 2000);
    };
    eget("/config").then(c => { rememberName(c.name); name.current = c.name || agentName(); }).catch(() => {});
    tick();
    return () => { stop = true; };
  }, []);
  return null;
}
