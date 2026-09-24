"use client";
// The agent's interface: a component tree from the `show` tool (silo.ui) rendered with the console's own
// components. Data in, shadcn-style UI out; nothing here evaluates markup or code from the agent.
import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ExternalLink, X } from "lucide-react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge } from "./ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Progress } from "./ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { cn } from "@/lib/utils";
import { rise } from "@/lib/motion";
import dynamic from "next/dynamic";
const MapView = dynamic(() => import("./map-view").then(m => m.MapView), { ssr: false, loading: () => <div className="h-40 animate-pulse rounded-sm bg-surface" /> });

export type Spec = { type: string; [k: string]: any };

/** Turn what people paste (a watch page, a map link) into what a frame can load. Only https providers we know, or a plain https page. */
export type EmbedInfo = { src: string; kind: "youtube" | "vimeo" | "map" | "point" | "video" | "audio" | "page"; ratio?: string; lat?: number; lon?: number; zoom?: number; query?: string };
export function embedSrc(raw: string): EmbedInfo | null {
  let u: URL; try { u = new URL(String(raw || "")); } catch { return null; }
  if (u.protocol !== "https:") return null;
  const h = u.hostname.replace(/^www\./, "");
  if (h === "youtu.be" || h.endsWith("youtube.com") || h.endsWith("youtube-nocookie.com")) {
    const id = h === "youtu.be" ? u.pathname.slice(1).split("/")[0] : u.pathname.startsWith("/embed/") ? u.pathname.split("/")[2] : u.pathname.startsWith("/shorts/") ? u.pathname.split("/")[2] : u.pathname.startsWith("/live/") ? u.pathname.split("/")[2] : u.searchParams.get("v") || "";
    if (!/^[\w-]{6,}$/.test(id)) return null;
    const t = u.searchParams.get("t") || u.searchParams.get("start"); const start = t ? parseInt(String(t).replace(/s$/, ""), 10) : 0;
    return { src: `https://www.youtube-nocookie.com/embed/${id}?rel=0${start ? `&start=${start}` : ""}`, kind: "youtube", ratio: "16/9" };
  }
  if (h === "vimeo.com" || h === "player.vimeo.com") { const id = (u.pathname.match(/(\d{5,})/) || [])[1]; return id ? { src: `https://player.vimeo.com/video/${id}`, kind: "vimeo", ratio: "16/9" } : null; }
  if (h === "google.com" || h.endsWith(".google.com") || h === "maps.app.goo.gl") {
    if (u.pathname.startsWith("/maps/embed")) return { src: u.toString(), kind: "map" };          // the share dialog's own embed link frames fine
    const at = u.pathname.match(/@(-?\d+\.\d+),(-?\d+\.\d+)(?:,(\d+\.?\d*)z)?/);
    if (at) return { src: "", kind: "point", lat: +at[1], lon: +at[2], zoom: at[3] ? Math.round(+at[3]) : 14 };
    const q = u.searchParams.get("q") || u.searchParams.get("query") || decodeURIComponent((u.pathname.match(/\/place\/([^/@]+)/) || [])[1] || "").replace(/\+/g, " ");
    const ll = q.match(/^(-?\d+\.\d+),\s*(-?\d+\.\d+)$/); if (ll) return { src: "", kind: "point", lat: +ll[1], lon: +ll[2], zoom: 14 };
    if (q) return { src: "", kind: "point", query: q };
    return null;
  }
  if (h === "openstreetmap.org" || h === "osm.org") {
    const lat = u.searchParams.get("mlat"), lon = u.searchParams.get("mlon"); const m = u.hash.match(/map=(\d+)\/(-?\d+\.?\d*)\/(-?\d+\.?\d*)/);
    if (lat && lon) return { src: "", kind: "point", lat: +lat, lon: +lon, zoom: m ? +m[1] : 14 };
    if (m) return { src: "", kind: "point", lat: +m[2], lon: +m[3], zoom: +m[1] };
    const bb = u.searchParams.get("bbox")?.split(",").map(Number); if (bb && bb.length === 4 && bb.every(isFinite)) return { src: "", kind: "point", lat: (bb[1] + bb[3]) / 2, lon: (bb[0] + bb[2]) / 2, zoom: 13 };
    return null;
  }
  if (/\.(mp4|webm|mov|m4v)(\?|$)/i.test(u.pathname + u.search)) return { src: u.toString(), kind: "video", ratio: "16/9" };
  if (/\.(mp3|m4a|wav|ogg|oga|flac)(\?|$)/i.test(u.pathname + u.search)) return { src: u.toString(), kind: "audio" };
  return { src: u.toString(), kind: "page" };
}

function Frame({ src, kind, title, height, ratio }: { src: string; kind: string; title?: string; height?: number; ratio?: string }) {
  const h = Math.min(720, Math.max(160, Number(height) || (kind === "map" ? 320 : 360)));
  const style = ratio ? { aspectRatio: ratio.replace("/", " / "), width: "100%" } : { height: h, width: "100%" };
  const allow = kind === "youtube" || kind === "vimeo" ? "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; fullscreen" : "fullscreen";
  return <iframe src={src} title={title || kind} style={style} className="block rounded-sm border border-border bg-surface" sandbox="allow-scripts allow-same-origin allow-popups allow-presentation allow-forms" referrerPolicy="strict-origin-when-cross-origin" allow={allow} loading="lazy" />;
}

function Embed({ s }: { s: Spec }) {
  const e = embedSrc(s.url); if (!e) return <div className="text-xs text-muted-foreground">That link cannot be embedded.</div>;
  const caption = s.title && <div className="text-xs text-muted-foreground">{s.title}{e.kind !== "page" && <a href={s.url} target="_blank" rel="noreferrer" className="ml-1 underline">open</a>}</div>;
  if (e.kind === "video") return <div className="grid gap-1"><video src={e.src} controls playsInline preload="metadata" className="w-full rounded-sm border border-border bg-foreground/90" style={{ aspectRatio: "16 / 9" }} />{caption}</div>;
  if (e.kind === "audio") return <div className="grid gap-1"><audio src={e.src} controls preload="metadata" className="w-full" />{caption}</div>;
  if (e.kind === "point") return <MapView lat={e.lat} lon={e.lon} zoom={e.zoom} query={e.query} label={s.title} height={s.height} />;
  return <div className="grid gap-1"><Frame src={e.src} kind={e.kind} title={s.title} height={s.height} ratio={e.ratio} />{caption}</div>;
}
const PALETTE = ["#4f46e5", "#0ea5e9", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#14b8a6"];
const tone = (t?: string) => (t === "ok" || t === "warn" ? t : "note") as "ok" | "warn" | "note";

function Inline({ text }: { text: string }) {
  const parts = String(text ?? "").split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g);
  return <>{parts.map((p, i) => p.startsWith("**") ? <b key={i}>{p.slice(2, -2)}</b> : p.startsWith("*") ? <i key={i}>{p.slice(1, -1)}</i> : p)}</>;
}

function Chart({ s }: { s: Spec }) {
  const data: any[] = Array.isArray(s.data) ? s.data : []; const series: string[] = Array.isArray(s.series) && s.series.length ? s.series : Object.keys(data[0] || {}).filter(k => k !== s.x).slice(0, 4);
  const x = s.x || Object.keys(data[0] || {})[0];
  const common = { data, margin: { top: 8, right: 8, left: 0, bottom: 0 } };
  // recharts reads its direct children by type, so the axes are an array, never a fragment
  const axes = [<CartesianGrid key="g" stroke="hsl(var(--border))" vertical={false} />, <XAxis key="x" dataKey={x} tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={{ stroke: "hsl(var(--border))" }} tickLine={false} />, <YAxis key="y" width={36} tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />, <Tooltip key="t" contentStyle={{ fontSize: 12, borderRadius: 6, border: "1px solid hsl(var(--border))", background: "hsl(var(--background))", color: "hsl(var(--foreground))" }} />];
  return (
    <div className="grid gap-2">
      {s.title && <div className="label">{s.title}</div>}
      <div className="h-56 w-full min-w-0">
        <ResponsiveContainer width="100%" height="100%">
          {s.kind === "bar" ? <BarChart {...common}>{axes}{series.map((k, i) => <Bar key={k} dataKey={k} fill={PALETTE[i % PALETTE.length]} radius={[3, 3, 0, 0]} />)}</BarChart>
          : s.kind === "area" ? <AreaChart {...common}>{axes}{series.map((k, i) => <Area key={k} type="monotone" dataKey={k} stroke={PALETTE[i % PALETTE.length]} fill={PALETTE[i % PALETTE.length]} fillOpacity={0.12} strokeWidth={2} />)}</AreaChart>
          : s.kind === "pie" ? <PieChart><Tooltip contentStyle={{ fontSize: 12 }} /><Pie data={data} dataKey={series[0]} nameKey={x} innerRadius={48} outerRadius={84} paddingAngle={2}>{data.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}</Pie></PieChart>
          : <LineChart {...common}>{axes}{series.map((k, i) => <Line key={k} type="monotone" dataKey={k} stroke={PALETTE[i % PALETTE.length]} strokeWidth={2} dot={false} />)}</LineChart>}
        </ResponsiveContainer>
      </div>
      {series.length > 1 && <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">{series.map((k, i) => <span key={k} className="flex items-center gap-1"><i className="inline-block h-2 w-2 rounded-full" style={{ background: PALETTE[i % PALETTE.length] }} />{k}</span>)}</div>}
    </div>
  );
}

function Pic({ url, title, credit, href, onOpen }: { url: string; title?: string; credit?: string; href?: string; onOpen: () => void }) {
  if (!url) return null;
  return (
    <figure className="group grid gap-1">
      <button onClick={onOpen} className="aspect-[4/3] overflow-hidden rounded-sm bg-surface"><img src={url} alt={title || ""} loading="lazy" className="h-full w-full object-cover transition-transform group-hover:scale-[1.03]" /></button>
      {(title || credit) && <figcaption className="truncate text-[11px] text-muted-foreground">{title}{credit ? ` · ${credit}` : ""}{href && <a href={href} target="_blank" rel="noreferrer" className="ml-1 underline">source</a>}</figcaption>}
    </figure>
  );
}

export function Render({ s, open }: { s: Spec; open: (p: any) => void }) {
  if (!s || typeof s !== "object") return null;
  const kids = (s.children || []).map((c: Spec, i: number) => <Render key={i} s={c} open={open} />);
  switch (s.type) {
    case "stack": return <div className={cn("grid", s.gap === "lg" ? "gap-5" : "gap-3")}>{kids}</div>;
    case "grid": return <div className={cn("grid gap-3", { 1: "grid-cols-1", 2: "grid-cols-2", 3: "grid-cols-3", 4: "grid-cols-4" }[Math.min(4, Math.max(1, Number(s.cols) || 2))])}>{kids}</div>;
    case "card": return <Card><CardHeader className="pb-2"><div><CardTitle>{s.title}</CardTitle>{s.subtitle && <div className="text-xs text-muted-foreground">{s.subtitle}</div>}</div></CardHeader><CardContent className="grid gap-3">{kids}{s.footer && <div className="border-t border-border pt-2 text-xs text-muted-foreground">{s.footer}</div>}</CardContent></Card>;
    case "heading": { const L = (s.level === 1 ? "h2" : s.level === 3 ? "h4" : "h3") as any; return <L className={cn("font-semibold", s.level === 1 ? "text-xl" : s.level === 3 ? "text-sm" : "text-base")}>{s.text}</L>; }
    case "text": return <p className={cn("text-sm leading-6", s.muted && "text-muted-foreground")}><Inline text={s.text} /></p>;
    case "badge": return <span><Badge tone={tone(s.tone)}>{s.text}</Badge></span>;
    case "link": return s.href ? <a href={s.href} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm text-primary hover:underline">{s.text || s.href}<ExternalLink className="h-3 w-3" /></a> : <span className="text-sm">{s.text}</span>;
    case "divider": return <hr className="border-border" />;
    case "image": return <Pic url={s.url} title={s.title} credit={s.credit} href={s.href} onOpen={() => open(s)} />;
    case "gallery": { const items = (s.items || []).filter((i: any) => i?.url); const cols = items.length <= 1 ? "grid-cols-1" : items.length === 2 ? "grid-cols-2" : items.length <= 4 ? "grid-cols-2 sm:grid-cols-4" : "grid-cols-3"; return <div className={cn("grid gap-2", cols)}>{items.map((i: any, k: number) => <Pic key={k} {...i} onOpen={() => open(i)} />)}</div>; }
    case "stat": return <div className="hairline grid gap-1 p-3"><div className="label">{s.label}</div><div className="flex items-baseline gap-2"><span className="text-2xl font-semibold tracking-tight">{s.value}</span>{s.delta && <Badge tone={tone(s.tone)}>{s.delta}</Badge>}</div>{s.note && <div className="text-xs text-muted-foreground">{s.note}</div>}</div>;
    case "progress": return <div className="grid gap-1.5"><div className="flex justify-between text-xs"><span>{s.label}</span><span className="text-muted-foreground">{Math.round(Number(s.value) || 0)}%</span></div><Progress value={Number(s.value) || 0} /></div>;
    case "kv": return <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">{(s.items || []).map((i: any, k: number) => <div key={k} className="contents"><dt className="text-muted-foreground">{i.k}</dt><dd>{i.v}</dd></div>)}</dl>;
    case "list": { const L = (s.ordered ? "ol" : "ul") as any; return <L className={cn("grid gap-1 pl-5 text-sm", s.ordered ? "list-decimal" : "list-disc")}>{(s.items || []).map((i: any, k: number) => <li key={k}><Inline text={typeof i === "string" ? i : i?.text ?? ""} /></li>)}</L>; }
    case "table": return <div className="hairline overflow-x-auto"><table className="w-full text-sm"><thead className="bg-surface text-left text-xs uppercase tracking-wide text-muted-foreground"><tr>{(s.columns || []).map((c: any, k: number) => <th key={k} className="px-3 py-2 font-medium">{c}</th>)}</tr></thead><tbody className="divide-y divide-border">{(s.rows || []).map((r: any[], k: number) => <tr key={k}>{(r || []).map((c, j) => <td key={j} className="px-3 py-2">{String(c ?? "")}</td>)}</tr>)}</tbody>{s.caption && <caption className="p-2 text-left text-xs text-muted-foreground">{s.caption}</caption>}</table></div>;
    case "chart": return <Chart s={s} />;
    case "tabs": { const items = (s.items || []).filter((i: any) => i?.label); if (!items.length) return null; return <Tabs defaultValue="0"><TabsList>{items.map((i: any, k: number) => <TabsTrigger key={k} value={String(k)}>{i.label}</TabsTrigger>)}</TabsList>{items.map((i: any, k: number) => <TabsContent key={k} value={String(k)}>{i.child && <Render s={i.child} open={open} />}</TabsContent>)}</Tabs>; }
    case "embed": case "video": case "audio": return s.url ? <Embed s={s} /> : null;
    case "map": { const lat = Number(s.lat), lon = Number(s.lon); if (!isFinite(lat) || !isFinite(lon)) return s.query ? <MapView query={s.query} zoom={Number(s.zoom) || 13} label={s.label} height={s.height} /> : s.url ? <Embed s={s} /> : null; return <MapView lat={lat} lon={lon} zoom={Number(s.zoom) || 14} label={s.label || s.title} height={s.height} />; }
    case "callout": return <div className={cn("rounded-md border p-3 text-sm", s.tone === "ok" ? "note-ok" : s.tone === "warn" ? "note-warn" : "border-border bg-surface")}>{s.title && <b className="block">{s.title}</b>}<Inline text={s.text} /></div>;
    default: return null;
  }
}

export function UiBlock({ title, spec }: { title?: string; spec: Spec }) {
  const [open, setOpen] = useState<any>(null);
  return (
    <motion.div {...rise} className="hairline w-full max-w-[90%] overflow-hidden">
      {title && <div className="border-b border-border bg-surface px-3 py-2 text-sm font-semibold">{title}</div>}
      <div className="p-3"><Render s={spec} open={setOpen} /></div>
      <AnimatePresence>{open && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-50 grid place-items-center bg-black/80 p-6" onClick={() => setOpen(null)}>
          <motion.img initial={{ scale: 0.96 }} animate={{ scale: 1 }} src={open.url} alt={open.title || ""} className="max-h-[80vh] max-w-full rounded-md shadow-2xl" />
          <div className="mt-3 flex items-center gap-3 text-xs text-white"><span>{open.title}</span><span className="opacity-70">{open.credit}</span><X className="h-4 w-4" /></div>
        </motion.div>)}
      </AnimatePresence>
    </motion.div>
  );
}
