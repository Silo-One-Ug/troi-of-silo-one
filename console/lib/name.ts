// The agent's name on the page. The server says it (/config: name, from the settings' `agent`); the page remembers the
// last one it heard, so the lines that must show while the server is away ("… is not answering") still carry the right
// name. Rendered text goes through the hook (the first paint says the default, then the remembered name, then the
// server's) so the page the server sent and the page the browser draws agree; words made at the moment of an event
// (an error, a notification) take agentName() directly.
import { useEffect, useState } from "react";
import { eget } from "@/lib/edge";

export const DEFAULT_NAME = "Troi";
export function agentName(): string { try { return localStorage.getItem("silo.name") || DEFAULT_NAME; } catch { return DEFAULT_NAME; } }
export function rememberName(n: unknown) { if (typeof n !== "string" || !n.trim()) return; try { localStorage.setItem("silo.name", n.trim()); } catch {} }
export function useAgentName(): string {
  const [n, setN] = useState(DEFAULT_NAME);
  useEffect(() => { setN(agentName()); eget("/config").then(c => { if (c?.name) { rememberName(c.name); setN(c.name); } }).catch(() => {}); }, []);
  return n;
}
