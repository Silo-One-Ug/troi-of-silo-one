"use client";
// The surfaces that are canvases of their own (the galaxies, the vault wall, the hands board, the face): embedded
// whole, filling the window edge to edge; the bar floats over them. They keep every gesture they have.
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { edgeUrl, eget, type Config } from "@/lib/edge";

export function View({ kind }: { kind: "face" | "hands" | "files" | "apps" | "vault" }) {
  const [c, setC] = useState<Config | null>(null); const [ready, setReady] = useState(false); const [path, setPath] = useState("");
  useEffect(() => { eget("/config").then(setC).catch(() => {}); try { setPath(new URLSearchParams(location.search).get("path") || ""); } catch {} }, []);
  const galaxy = kind === "files" || kind === "apps" || kind === "vault";
  const src = kind === "face" ? c?.face : kind === "hands" ? c?.hands : `${edgeUrl()}/galaxy.html?safe=0&mode=${kind}${kind !== "vault" ? "&bg=deep" : ""}${kind === "vault" && c?.vault ? "&vault=" + encodeURIComponent(c.vault) : ""}${kind === "files" && path ? "&path=" + encodeURIComponent(path) : ""}`;
  if (!src) return <div className="grid h-full place-items-center bg-black text-sm text-muted-foreground">…</div>;
  // the frame fades in once it has painted: no blank frame between pages
  // data-galaxy / data-ready: Troi's commands (focus, refresh, hands) are posted into the galaxy once it has loaded
  return <iframe key={src} src={src} title={kind} data-galaxy={galaxy ? "1" : undefined} data-ready={ready ? "1" : undefined} allow="camera; microphone; autoplay; fullscreen" onLoad={e => { setReady(true); try { if (localStorage.getItem("silo.hands") === "1") setTimeout(() => { (e.target as HTMLIFrameElement).contentWindow?.postMessage({ hands: true }, "*"); (e.target as HTMLIFrameElement).contentWindow?.postMessage({ boardCamera: "on" }, "*"); }, 1500); } catch {} }} className={cn("block h-full w-full border-0 bg-black transition-opacity duration-500 ease-out", ready ? "opacity-100" : "opacity-0")} />;
}
