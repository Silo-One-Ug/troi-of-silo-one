"use client";
// The agent's interface: a component tree from the `show` tool (silo.ui) rendered with the console's own
// components. Data in, shadcn-style UI out; nothing here evaluates markup or code from the agent. The vocabulary is the
// one the board draws (troi-console/barehands/board-render.js): one tree, two surfaces.
import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronRight, ExternalLink, X } from "lucide-react";
import Autoplay from "embla-carousel-autoplay";
import { Carousel, CarouselContent, CarouselItem, CarouselNext, CarouselPrevious, type CarouselApi } from "./ui/carousel";
import ReactMarkdown from "react-markdown";
import { GFM } from "@/lib/compat";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from "recharts";
import { Badge } from "./ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Progress } from "./ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { cn } from "@/lib/utils";
import { rise } from "@/lib/motion";
import { epost } from "@/lib/edge";
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

const ratio = (a: any): string | undefined => { if (a == null || a === "") return undefined; if (typeof a === "number") return a > 0 ? String(a) : undefined; const m = String(a).match(/^\s*(\d+(?:\.\d+)?)\s*[:/xX]\s*(\d+(?:\.\d+)?)\s*$/); return m && +m[2] > 0 ? `${m[1]} / ${m[2]}` : undefined; };
const num = (v: any, d: number) => { const n = Number(v); return Number.isFinite(n) ? n : d; };
const fmt = (v: any) => { if (typeof v !== "number" || !Number.isFinite(v)) return String(v ?? ""); const a = Math.abs(v); if (a >= 1e9) return (v / 1e9).toFixed(1) + "B"; if (a >= 1e6) return (v / 1e6).toFixed(1) + "M"; if (a >= 1e4) return (v / 1e3).toFixed(1) + "k"; return Number.isInteger(v) ? String(v) : String(+v.toFixed(2)); };

function Frame({ src, kind, title, height, ratio: r }: { src: string; kind: string; title?: string; height?: number; ratio?: string }) {
  const h = Math.min(720, Math.max(160, Number(height) || (kind === "map" ? 320 : 360)));
  const style = r ? { aspectRatio: r.replace("/", " / "), width: "100%" } : { height: h, width: "100%" };
  const allow = kind === "youtube" || kind === "vimeo" ? "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; fullscreen" : "fullscreen";
  return <iframe src={src} title={title || kind} style={style} className="block rounded-sm border border-border bg-surface" sandbox="allow-scripts allow-same-origin allow-popups allow-presentation allow-forms" referrerPolicy="strict-origin-when-cross-origin" allow={allow} loading="lazy" />;
}

function Embed({ s }: { s: Spec }) {
  const e = embedSrc(s.url); if (!e) return <div className="text-xs text-muted-foreground">That link cannot be embedded.</div>;
  const caption = (s.title || s.caption) && <div className="text-xs text-muted-foreground">{s.caption || s.title}{e.kind !== "page" && <a href={s.url} target="_blank" rel="noreferrer" className="ml-1 underline">open</a>}</div>;
  if (e.kind === "video") return <div className="grid gap-1"><video src={e.src} controls playsInline preload="metadata" className="w-full rounded-sm border border-border bg-foreground/90" style={{ aspectRatio: ratio(s.aspect) || "16 / 9" }} />{caption}</div>;
  if (e.kind === "audio") return <div className="grid gap-1"><audio src={e.src} controls preload="metadata" className="w-full" />{caption}</div>;
  if (e.kind === "point") return <MapView lat={e.lat} lon={e.lon} zoom={e.zoom} query={e.query} label={s.title} height={s.height} />;
  return <div className="grid gap-1"><Frame src={e.src} kind={e.kind} title={s.title} height={s.height} ratio={ratio(s.aspect) || e.ratio} />{caption}</div>;
}
const PALETTE = ["#4f46e5", "#0ea5e9", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#14b8a6"];
const tone = (t?: string) => (t === "ok" || t === "warn" ? t : "note") as "ok" | "warn" | "note";
const toneClass = (t?: string) => t === "ok" ? "text-emerald-600" : t === "warn" ? "text-amber-600" : t === "bad" ? "text-red-600" : t === "muted" ? "text-muted-foreground" : "text-primary";

function Inline({ text }: { text: string }) {
  const parts = String(text ?? "").split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]+\]\(https?:\/\/[^)\s]+\))/g);
  return <>{parts.map((p, i) => p.startsWith("**") ? <b key={i}>{p.slice(2, -2)}</b> : p.startsWith("`") ? <code key={i} className="rounded bg-surface px-1 text-[0.92em]">{p.slice(1, -1)}</code> : p.startsWith("[") ? <a key={i} href={p.slice(p.indexOf("](") + 2, -1)} target="_blank" rel="noreferrer" className="underline">{p.slice(1, p.indexOf("]("))}</a> : p.startsWith("*") ? <i key={i}>{p.slice(1, -1)}</i> : p)}</>;
}

function Chart({ s }: { s: Spec }) {
  const data: any[] = Array.isArray(s.data) ? s.data.filter((d: any) => d && typeof d === "object") : []; const x = s.x || Object.keys(data[0] || {})[0];
  const series: string[] = Array.isArray(s.series) && s.series.length ? s.series.map(String) : Object.keys(data[0] || {}).filter(k => k !== x && typeof data[0][k] === "number").slice(0, 6);
  const color = (i: number) => (Array.isArray(s.colors) && /^#[0-9a-f]{3,8}$/i.test(String(s.colors[i] || ""))) ? s.colors[i] : PALETTE[i % PALETTE.length];
  const common = { data, margin: { top: 8, right: 8, left: 0, bottom: 0 } };
  const domain: [any, any] = [s.ymin != null ? num(s.ymin, 0) : "auto", s.ymax != null ? num(s.ymax, 0) : "auto"];
  // recharts reads its direct children by type, so the axes are an array, never a fragment
  const axes = [<CartesianGrid key="g" stroke="hsl(var(--border))" vertical={false} />, <XAxis key="x" dataKey={x} type={s.kind === "scatter" ? "number" : "category"} tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={{ stroke: "hsl(var(--border))" }} tickLine={false} />, <YAxis key="y" width={36} domain={domain} tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />, <Tooltip key="t" contentStyle={{ fontSize: 12, borderRadius: 6, border: "1px solid hsl(var(--border))", background: "hsl(var(--background))", color: "hsl(var(--foreground))" }} />];
  const pie = s.kind === "pie" || s.kind === "donut";
  return (
    <div className="grid gap-2">
      {s.title && <div className="label">{s.title}</div>}
      <div className="w-full min-w-0" style={{ height: Math.min(600, Math.max(120, num(s.height, 224))) }}>
        <ResponsiveContainer width="100%" height="100%">
          {s.kind === "bar" ? <BarChart {...common}>{axes}{series.map((k, i) => <Bar key={k} dataKey={k} stackId={s.stacked ? "a" : undefined} fill={color(i)} radius={s.stacked ? 0 : [3, 3, 0, 0]} />)}</BarChart>
          : s.kind === "area" ? <AreaChart {...common}>{axes}{series.map((k, i) => <Area key={k} type="monotone" dataKey={k} stackId={s.stacked ? "a" : undefined} stroke={color(i)} fill={color(i)} fillOpacity={s.stacked ? 0.45 : 0.12} strokeWidth={2} />)}</AreaChart>
          : s.kind === "scatter" ? <ScatterChart margin={common.margin}>{axes}{series.map((k, i) => <Scatter key={k} name={k} data={data} dataKey={k} fill={color(i)} />)}</ScatterChart>
          : pie ? <PieChart><Tooltip contentStyle={{ fontSize: 12 }} /><Pie data={data} dataKey={series[0]} nameKey={x} innerRadius={s.kind === "donut" ? 52 : 0} outerRadius={84} paddingAngle={2}>{data.map((_, i) => <Cell key={i} fill={color(i)} />)}</Pie></PieChart>
          : <LineChart {...common}>{axes}{series.map((k, i) => <Line key={k} type="monotone" dataKey={k} stroke={color(i)} strokeWidth={2} dot={s.dots !== 0 && data.length <= 40} />)}</LineChart>}
        </ResponsiveContainer>
      </div>
      {pie ? <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">{data.map((d, i) => <span key={i} className="flex items-center gap-1"><i className="inline-block h-2 w-2 rounded-full" style={{ background: color(i) }} />{String(d[x])} <span className="opacity-70">{fmt(d[series[0]])}{s.unit || ""}</span></span>)}</div>
        : (series.length > 1 || s.legend) && <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">{series.map((k, i) => <span key={k} className="flex items-center gap-1"><i className="inline-block h-2 w-2 rounded-full" style={{ background: color(i) }} />{k}</span>)}</div>}
    </div>
  );
}

function Spark({ data, tone: t }: { data: any[]; tone?: string }) {
  const v = (Array.isArray(data) ? data : []).map(Number).filter(Number.isFinite).slice(-120); if (v.length < 2) return null;
  const lo = Math.min(...v), hi = Math.max(...v); const pts = v.map((y, i) => [i / (v.length - 1) * 116 + 2, hi === lo ? 15 : 27 - (y - lo) / (hi - lo) * 24]);
  return <svg viewBox="0 0 120 30" className={cn("h-7 w-28", toneClass(t))}><path d={pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ")} fill="none" stroke="currentColor" strokeWidth={1.8} /><circle cx={pts[pts.length - 1][0]} cy={pts[pts.length - 1][1]} r={2.4} fill="currentColor" /></svg>;
}

function Gauge({ s }: { s: Spec }) {
  const min = num(s.min, 0), max = num(s.max, 100), v = Math.min(Math.max(num(s.value, 0), Math.min(min, max)), Math.max(min, max)); const p = max === min ? 0 : (v - min) / (max - min);
  const arc = (from: number, to: number) => { const a0 = Math.PI * (1 - from), a1 = Math.PI * (1 - to); return `M ${100 + 80 * Math.cos(a0)} ${100 - 80 * Math.sin(a0)} A 80 80 0 0 1 ${100 + 80 * Math.cos(a1)} ${100 - 80 * Math.sin(a1)}`; };
  return <div className="grid justify-items-center gap-1"><svg viewBox="0 0 200 116" className="w-full max-w-[220px]"><path d={arc(0, 1)} fill="none" stroke="hsl(var(--border))" strokeWidth={14} strokeLinecap="round" /><path d={arc(0, Math.max(0.02, p))} fill="none" stroke="currentColor" strokeWidth={14} strokeLinecap="round" className={toneClass(s.tone || "note")} /><text x={100} y={92} textAnchor="middle" className="fill-foreground text-[28px] font-semibold">{fmt(v)}{s.unit || ""}</text></svg>{s.label && <div className="label">{s.label}</div>}</div>;
}

function Slideshow({ s, open }: { s: Spec; open: (p: any) => void }) {
  const items: any[] = (Array.isArray(s.items) ? s.items : []).map((i: any) => typeof i === "string" ? { url: i } : i).filter(Boolean).slice(0, 60);
  const [api, setApi] = useState<CarouselApi>(); const [i, setI] = useState(0);
  const every = s.autoplay === 0 || s.autoplay === false ? 0 : Math.min(600, Math.max(2, num(s.interval, 6))) * 1000;
  const plugins = useMemo(() => every && items.length > 1 ? [Autoplay({ delay: every, stopOnInteraction: false, stopOnMouseEnter: true })] : [], [every, items.length]);
  useEffect(() => { if (!api) return; const on = () => setI(api.selectedScrollSnap()); on(); api.on("select", on); return () => { api.off("select", on); }; }, [api]);
  if (!items.length) return null;
  return (
    <div className="grid gap-1.5">
      <Carousel setApi={setApi} opts={{ loop: true, startIndex: Math.min(Math.max(0, num(s.index, 0)), items.length - 1) }} plugins={plugins}>
        <CarouselContent>{items.map((it, k) => <CarouselItem key={k}><div className="relative overflow-hidden rounded-sm bg-surface" style={{ aspectRatio: ratio(s.aspect) || "16 / 9" }}>{it.type ? <div className="absolute inset-0 overflow-auto p-3"><Render s={it} open={open} /></div> : <img src={it.url || it.src} alt={it.caption || it.title || ""} draggable={false} className="absolute inset-0 h-full w-full" style={{ objectFit: it.fit === "contain" || s.fit === "contain" ? "contain" : "cover" }} onClick={() => open(it)} />}{(it.caption || (!it.type && it.title)) && <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 to-transparent px-3 pb-2 pt-6 text-xs text-white">{it.caption || it.title}</div>}</div></CarouselItem>)}</CarouselContent>
        {items.length > 1 && <><CarouselPrevious /><CarouselNext /></>}
      </Carousel>
      {items.length > 1 && <div className="flex justify-center gap-1.5">{items.map((_, k) => <button key={k} aria-label={`slide ${k + 1}`} onClick={() => api?.scrollTo(k)} className={cn("h-2 w-2 rounded-full", k === i ? "bg-primary" : "bg-border")} />)}</div>}
      {s.title && <div className="text-center text-xs text-muted-foreground">{s.title}</div>}
    </div>
  );
}

function Accordion({ s, open }: { s: Spec; open: (p: any) => void }) {
  const items: any[] = (Array.isArray(s.items) ? s.items : []).filter((i: any) => i && i.label).slice(0, 30);
  const [on, setOn] = useState<number[]>(items.map((it, k) => it.open ? k : -1).filter(k => k >= 0));
  return <div className="divide-y divide-border">{items.map((it, k) => <div key={k}><button onClick={() => setOn(o => o.includes(k) ? o.filter(x => x !== k) : s.single ? [k] : [...o, k])} className="flex w-full items-center gap-2 py-2 text-left text-sm font-medium"><ChevronRight className={cn("h-3.5 w-3.5 transition-transform", on.includes(k) && "rotate-90")} />{it.label}{it.note && <span className="ml-auto text-xs text-muted-foreground">{it.note}</span>}</button>{on.includes(k) && <div className="pb-3 pl-6">{it.child ? <Render s={it.child} open={open} /> : <p className="text-sm text-muted-foreground"><Inline text={it.text} /></p>}</div>}</div>)}</div>;
}

function Countdown({ s }: { s: Spec }) {
  const to = Date.parse(String(s.to || "")); const [now, setNow] = useState(Date.now());
  useEffect(() => { const h = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(h); }, []);
  let text = "when?"; if (Number.isFinite(to)) { let sec = Math.round((to - now) / 1000); if (sec <= 0) text = String(s.done || "now"); else { const d = Math.floor(sec / 86400); sec -= d * 86400; const h = Math.floor(sec / 3600); sec -= h * 3600; const m = Math.floor(sec / 60); sec -= m * 60; text = (d ? d + "d " : "") + String(h).padStart(2, "0") + ":" + String(m).padStart(2, "0") + ":" + String(sec).padStart(2, "0"); } }
  return <div className="grid gap-0.5">{s.label && <div className="label">{s.label}</div>}<div className="font-mono text-3xl font-semibold tabular-nums">{text}</div></div>;
}

function Clock({ s }: { s: Spec }) {
  const [now, setNow] = useState(new Date());
  useEffect(() => { const h = setInterval(() => setNow(new Date()), s.seconds ? 1000 : 10000); return () => clearInterval(h); }, [s.seconds]);
  let t = "", d = ""; try { t = new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit", second: s.seconds ? "2-digit" : undefined, hour12: !!s.h12, timeZone: s.tz || undefined }).format(now); d = new Intl.DateTimeFormat(undefined, { weekday: "long", day: "numeric", month: "long", timeZone: s.tz || undefined }).format(now); } catch { t = "unknown time zone"; }
  return <div className="grid gap-0.5">{s.label && <div className="label">{s.label}</div>}<div className="font-mono text-3xl font-semibold tabular-nums">{t}</div><div className="text-xs text-muted-foreground">{d}{s.tz ? ` · ${s.tz}` : ""}</div></div>;
}

function Calendar({ s }: { s: Spec }) {
  const m = /^(\d{4})-(\d{2})$/.exec(String(s.month || "")); const now = new Date(); const y = m ? +m[1] : now.getFullYear(), mo = m ? +m[2] - 1 : now.getMonth();
  const first = new Date(y, mo, 1), days = new Date(y, mo + 1, 0).getDate(), lead = (first.getDay() + 6) % 7;
  const marks: Record<number, any[]> = {}; (Array.isArray(s.marks) ? s.marks : []).forEach((mk: any) => { const dt = typeof mk === "string" ? mk : mk?.date; const mm = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(dt || "")); if (mm && +mm[1] === y && +mm[2] - 1 === mo) (marks[+mm[3]] = marks[+mm[3]] || []).push(typeof mk === "string" ? { label: "" } : mk); });
  const cells = [...Array(lead).fill(null), ...Array.from({ length: days }, (_, i) => i + 1)];
  return (
    <div className="grid gap-2">
      <div className="text-sm font-semibold">{s.title || first.toLocaleDateString(undefined, { month: "long", year: "numeric" })}</div>
      <div className="grid grid-cols-7 gap-0.5 text-center text-[10px] uppercase tracking-wide text-muted-foreground">{["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"].map(w => <div key={w}>{w}</div>)}</div>
      <div className="grid grid-cols-7 gap-0.5">{cells.map((d, k) => d == null ? <div key={k} /> : <div key={k} title={(marks[d] || []).map((x: any) => x.label).filter(Boolean).join(", ")} className={cn("grid aspect-square place-items-center rounded text-xs", marks[d] && "bg-primary/10", now.getFullYear() === y && now.getMonth() === mo && now.getDate() === d && "font-semibold ring-1 ring-primary")}>{d}</div>)}</div>
      {Object.keys(marks).length > 0 && <div className="grid gap-0.5 text-xs">{Object.keys(marks).map(Number).sort((a, b) => a - b).flatMap(d => marks[d].filter((x: any) => x.label).map((x: any, i: number) => <div key={d + "-" + i} className="flex items-center gap-2"><span className={cn("h-1.5 w-1.5 rounded-full bg-current", toneClass(x.tone))} /><span className="text-muted-foreground">{String(d).padStart(2, "0")}</span>{x.label}</div>))}</div>}
    </div>
  );
}

function Avatar({ it, size }: { it: any; size: number }) {
  const initials = String(it.initials || String(it.name || "").split(/\s+/).map((w: string) => w[0]).join("").slice(0, 2).toUpperCase() || "?");
  return <span className="inline-grid flex-none place-items-center overflow-hidden rounded-full border border-border bg-surface font-semibold" style={{ width: size, height: size, fontSize: Math.round(size * 0.38) }} title={it.name || ""}>{it.url ? <img src={it.url} alt={it.name || ""} className="h-full w-full object-cover" /> : initials}</span>;
}

function Pic({ url, title, caption, credit, href, fit, aspect, onOpen }: { url: string; title?: string; caption?: string; credit?: string; href?: string; fit?: string; aspect?: string; onOpen: () => void }) {
  if (!url) return null;
  return (
    <figure className="group grid gap-1">
      <button onClick={onOpen} className="overflow-hidden rounded-sm bg-surface" style={{ aspectRatio: aspect || "4 / 3" }}><img src={url} alt={caption || title || ""} loading="lazy" className="h-full w-full transition-transform group-hover:scale-[1.03]" style={{ objectFit: fit === "contain" ? "contain" : "cover" }} /></button>
      {(caption || title || credit) && <figcaption className="truncate text-[11px] text-muted-foreground">{caption || title}{credit ? ` · ${credit}` : ""}{href && <a href={href} target="_blank" rel="noreferrer" className="ml-1 underline">source</a>}</figcaption>}
    </figure>
  );
}

/** A click on a button or a choice in the conversation reaches the agent as a line, the way it does from the board. */
function answer(kind: string, label: string, title: string | undefined, action?: string, value?: string) {
  const what = kind === "choice" ? `chose "${label}"` : kind === "check" ? `${value === "undone" ? "unticked" : "ticked"} "${label}"` : `clicked "${label}"`;
  epost("/say", { text: `(console: the owner ${what}${title ? ` on "${title}"` : ""}${action && action !== label ? ` (action: ${action})` : ""}. Take it as their answer and act on it; when a word back is all it needs, one short sentence.)` }).catch(() => {});
}

function Checklist({ s, title }: { s: Spec; title?: string }) {
  const items: any[] = Array.isArray(s.items) ? s.items : [];
  const [done, setDone] = useState<Set<number>>(() => new Set(items.map((i: any, k: number) => (i && typeof i === "object" && i.done) ? k : -1).filter((k: number) => k >= 0)));
  return <ul className="grid gap-1 text-sm">{items.map((i: any, k: number) => { const o = typeof i === "object" && i ? i : { text: i }; const on = done.has(k); return <li key={k} className={cn("flex items-start gap-2", on && "text-muted-foreground")}><button aria-pressed={on} onClick={() => { setDone(d => { const nx = new Set(d); if (nx.has(k)) nx.delete(k); else nx.add(k); return nx; }); answer("check", String(o.text ?? ""), title, s.action, on ? "undone" : "done"); }} className={cn("mt-1 inline-grid h-3.5 w-3.5 flex-none place-items-center rounded-sm border border-primary text-[9px] leading-none", on && "bg-primary text-primary-foreground")}>{on && "✓"}</button><span><Inline text={o.text ?? ""} />{o.note && <div className="text-xs text-muted-foreground">{o.note}</div>}</span></li>; })}</ul>;
}

function Choice({ s, title }: { s: Spec; title?: string }) {
  const opts: any[] = (Array.isArray(s.options) ? s.options : []).map((o: any) => typeof o === "object" && o ? o : { label: String(o), value: String(o) }).slice(0, 12);
  const [sel, setSel] = useState<number>(opts.findIndex(o => s.value != null && String(o.value ?? o.label) === String(s.value)));
  if (!opts.length) return null;
  return <div className="grid gap-1.5">{s.label && <div className="label">{s.label}</div>}<div className="flex flex-wrap gap-1.5">{opts.map((o, k) => <button key={k} onClick={() => { setSel(k); answer("choice", String(o.label ?? o.value), title, s.action); }} className={cn("rounded-full border px-3 py-1 text-sm", k === sel ? "border-primary text-primary" : "border-border")}>{o.label ?? o.value}</button>)}</div></div>;
}

export function Render({ s, open, title }: { s: Spec; open: (p: any) => void; title?: string }) {
  if (!s || typeof s !== "object") return null;
  const kids = (s.children || []).map((c: Spec, i: number) => <Render key={i} s={c} open={open} title={title} />);
  switch (s.type) {
    case "stack": return <div className={cn("grid", s.gap === "lg" ? "gap-5" : s.gap === "sm" ? "gap-1.5" : "gap-3")}>{kids}</div>;
    case "row": return <div className={cn("flex items-center gap-3", s.wrap === 0 || s.wrap === false ? "flex-nowrap" : "flex-wrap", s.justify === "between" && "justify-between", s.justify === "center" && "justify-center", s.justify === "end" && "justify-end")}>{kids}</div>;
    case "grid": return <div className={cn("grid gap-3", { 1: "grid-cols-1", 2: "grid-cols-2", 3: "grid-cols-3", 4: "grid-cols-4", 5: "grid-cols-5", 6: "grid-cols-6" }[Math.min(6, Math.max(1, Number(s.cols) || Math.min(kids.length || 2, 3)))])}>{kids}</div>;
    case "columns": { const w: number[] = Array.isArray(s.weights) ? s.weights : []; return <div className="grid gap-3" style={{ gridTemplateColumns: kids.map((_: any, i: number) => `${Math.min(12, Math.max(0.2, num(w[i], 1)))}fr`).join(" ") }}>{kids}</div>; }
    case "card": return <Card><CardHeader className="pb-2"><div><CardTitle>{s.title}</CardTitle>{s.subtitle && <div className="text-xs text-muted-foreground">{s.subtitle}</div>}</div></CardHeader><CardContent className="grid gap-3">{kids}{s.footer && <div className="border-t border-border pt-2 text-xs text-muted-foreground">{s.footer}</div>}</CardContent></Card>;
    case "group": return <fieldset className="grid gap-3 rounded-md border border-border p-3">{s.title && <legend className="label px-1">{s.title}</legend>}{kids}</fieldset>;
    case "heading": { const L = (s.level === 1 ? "h2" : s.level === 3 ? "h4" : s.level === 4 ? "h5" : "h3") as any; return <L className={cn("font-semibold", s.level === 1 ? "text-xl" : s.level === 3 ? "text-sm" : s.level === 4 ? "label" : "text-base")} style={{ textAlign: s.align }}><Inline text={s.text} /></L>; }
    case "text": return <p className={cn("leading-6", s.size === "sm" ? "text-xs" : s.size === "lg" ? "text-base" : s.size === "xl" ? "text-lg" : "text-sm", s.muted && "text-muted-foreground", s.mono && "font-mono")} style={{ textAlign: s.align }}><Inline text={s.text} /></p>;
    case "md": case "markdown": return <div className="chat-md text-sm"><ReactMarkdown remarkPlugins={GFM}>{String(s.text ?? "")}</ReactMarkdown></div>;
    case "quote": return <blockquote className="border-l-2 border-amber-500 pl-3 text-sm italic">{s.text}{s.cite && <cite className="block pt-1 text-xs not-italic text-muted-foreground">{s.cite}</cite>}</blockquote>;
    case "code": return <div className="grid gap-1">{(s.title || s.lang) && <div className="label">{s.title || s.lang}</div>}<pre className="overflow-x-auto rounded-md bg-surface p-3 text-xs">{String(s.text ?? "")}</pre></div>;
    case "kbd": return <span className="inline-flex gap-1">{(Array.isArray(s.keys) ? s.keys : String(s.keys || s.text || "").split(/\s+/)).filter(Boolean).slice(0, 8).map((k: string, i: number) => <kbd key={i} className="rounded border border-border bg-surface px-1.5 text-xs">{k}</kbd>)}</span>;
    case "badge": return <span><Badge tone={tone(s.tone)}>{s.text}</Badge></span>;
    case "tags": return <div className="flex flex-wrap gap-1.5">{(Array.isArray(s.items) ? s.items : []).slice(0, 40).map((t: any, i: number) => <Badge key={i} tone={tone(typeof t === "object" ? t?.tone : s.tone)}>{typeof t === "object" ? t?.text : t}</Badge>)}</div>;
    case "link": return s.href ? <a href={s.href} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm text-primary hover:underline">{s.text || s.href}<ExternalLink className="h-3 w-3" /></a> : <span className="text-sm">{s.text}</span>;
    case "divider": return s.label ? <div className="flex items-center gap-2 text-[11px] uppercase tracking-wide text-muted-foreground"><hr className="flex-1 border-border" />{s.label}<hr className="flex-1 border-border" /></div> : <hr className="border-border" />;
    case "spacer": return <div style={{ height: Math.min(400, Math.max(0, num(s.h, 12))) }} />;
    case "aspect": return <div className="relative overflow-hidden rounded-sm" style={{ aspectRatio: ratio(s.ratio || s.aspect) || "16 / 9" }}><div className="absolute inset-0">{s.child && <Render s={s.child} open={open} title={title} />}</div></div>;
    case "hero": return <div className="relative flex min-h-[120px] items-end overflow-hidden rounded-md bg-surface bg-cover bg-center text-white" style={{ aspectRatio: ratio(s.aspect) || "16 / 7", backgroundImage: s.src || s.url ? `url("${String(s.src || s.url).replace(/"/g, "%22")}")` : undefined }}><div className="absolute inset-0 bg-gradient-to-t from-black/75 to-black/5" /><div className="relative grid gap-1 p-4">{s.kicker && <div className="text-[11px] uppercase tracking-wider opacity-80">{s.kicker}</div>}{s.title && <div className="text-2xl font-bold leading-tight">{s.title}</div>}{s.subtitle && <div className="text-sm opacity-90"><Inline text={s.subtitle} /></div>}</div></div>;
    case "image": return <Pic url={s.url || s.src} title={s.title} caption={s.caption} credit={s.credit} href={s.href} fit={s.fit} aspect={ratio(s.aspect)} onOpen={() => open({ ...s, url: s.url || s.src })} />;
    case "gallery": { const items = (s.items || []).map((i: any) => typeof i === "string" ? { url: i } : i).filter((i: any) => i?.url || i?.src); const auto = items.length <= 1 ? 1 : items.length === 2 ? 2 : items.length <= 4 ? 2 : items.length <= 9 ? 3 : 4; const cols = Math.min(6, Math.max(1, Number(s.cols) || auto)); return <div className="grid gap-2" style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}>{items.map((i: any, k: number) => <Pic key={k} url={i.url || i.src} title={s.numbered ? `#${k + 1} ${i.title || i.caption || ""}` : i.title} caption={s.numbered ? undefined : i.caption} credit={i.credit} href={i.href} fit={i.fit || s.fit} aspect={ratio(i.aspect || s.aspect)} onOpen={() => open({ ...i, url: i.url || i.src })} />)}</div>; }
    case "slideshow": case "carousel": return <Slideshow s={s} open={open} />;
    case "stat": return <div className="hairline grid gap-1 p-3"><div className="label">{s.label}</div><div className="flex items-baseline gap-2"><span className={cn("text-2xl font-semibold tracking-tight", s.tone && s.tone !== "note" && toneClass(s.tone))}>{fmt(s.value)}</span>{s.unit && <span className="text-sm text-muted-foreground">{s.unit}</span>}{s.delta != null && s.delta !== "" && <Badge tone={tone(s.tone || (String(s.delta).trim().startsWith("-") ? "warn" : "ok"))}>{s.delta}</Badge>}</div>{Array.isArray(s.spark) && <Spark data={s.spark} tone={s.tone} />}{s.note && <div className="text-xs text-muted-foreground">{s.note}</div>}</div>;
    case "progress": { const max = num(s.max, 100) || 100; const v = Math.min(Math.max(num(s.value, 0), 0), max); return <div className="grid gap-1.5"><div className="flex justify-between text-xs"><span>{s.label}</span><span className="text-muted-foreground">{s.text || (max === 100 ? Math.round(v) + "%" : `${fmt(v)} / ${fmt(max)}`)}</span></div><Progress value={v / max * 100} /></div>; }
    case "gauge": case "meter": return <Gauge s={s} />;
    case "kv": { const items = Array.isArray(s.items) ? s.items : s.items && typeof s.items === "object" ? Object.keys(s.items).map(k => ({ k, v: s.items[k] })) : []; return <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">{items.map((i: any, k: number) => <div key={k} className="contents"><dt className="text-muted-foreground">{i.k ?? i.key ?? i.label}</dt><dd><Inline text={String(i.v ?? i.value ?? "")} /></dd></div>)}</dl>; }
    case "list": { const items = Array.isArray(s.items) ? s.items : []; if (s.check || items.some((i: any) => i && typeof i === "object" && i.done != null)) return <Checklist s={s} title={title} />; const L = (s.ordered ? "ol" : "ul") as any; return <L className={cn("grid gap-1 text-sm", s.ordered ? "list-decimal pl-5" : "list-disc pl-5")}>{items.map((i: any, k: number) => { const o = typeof i === "object" && i ? i : { text: i }; return <li key={k}><Inline text={o.text ?? ""} />{o.note && <div className="text-xs text-muted-foreground">{o.note}</div>}</li>; })}</L>; }
    case "table": { const cols = (Array.isArray(s.columns) ? s.columns : []).map((c: any) => typeof c === "object" && c ? c : { label: String(c) }); const hi = new Set((Array.isArray(s.highlight) ? s.highlight : [s.highlight]).map(Number)); return <div className="hairline overflow-x-auto"><table className={cn("w-full text-sm", s.compact && "text-xs")}><thead className="bg-surface text-left text-xs uppercase tracking-wide text-muted-foreground"><tr>{cols.map((c: any, k: number) => <th key={k} className="px-3 py-2 font-medium" style={{ textAlign: c.align }}>{c.label ?? c.key}</th>)}</tr></thead><tbody className="divide-y divide-border">{(s.rows || []).map((r: any, k: number) => { const cells = Array.isArray(r) ? r : r && typeof r === "object" ? cols.map((c: any) => r[c.key ?? c.label]) : [r]; return <tr key={k} className={cn(hi.has(k) && "bg-amber-50 dark:bg-amber-950/30")}>{cells.map((c: any, j: number) => <td key={j} className={cn("px-3", s.compact ? "py-1" : "py-2")} style={{ textAlign: cols[j]?.align }}>{c && typeof c === "object" && c.type ? <Render s={c} open={open} title={title} /> : <Inline text={typeof c === "number" ? fmt(c) : String(c ?? "")} />}</td>)}</tr>; })}</tbody>{Array.isArray(s.footer) && <tfoot className="border-t border-border font-medium"><tr>{s.footer.map((c: any, j: number) => <td key={j} className="px-3 py-2" style={{ textAlign: cols[j]?.align }}>{typeof c === "number" ? fmt(c) : String(c ?? "")}</td>)}</tr></tfoot>}{s.caption && <caption className="p-2 text-left text-xs text-muted-foreground">{s.caption}</caption>}</table></div>; }
    case "chart": return <Chart s={s} />;
    case "sparkline": return <div className="grid gap-1">{s.label && <div className="label">{s.label}</div>}<Spark data={s.data} tone={s.tone} /></div>;
    case "rating": { const max = Math.min(10, Math.max(1, Math.round(num(s.max, 5)))), v = Math.min(Math.max(num(s.value, 0), 0), max); return <div className="flex items-center gap-2 text-sm">{s.label && <span className="text-muted-foreground">{s.label}</span>}<span className="relative inline-block leading-none tracking-[2px] text-lg"><span className="text-border">{"★".repeat(max)}</span><span className="absolute left-0 top-0 overflow-hidden whitespace-nowrap text-amber-500" style={{ width: `${v / max * 100}%` }}>{"★".repeat(max)}</span></span><span className="text-muted-foreground">{fmt(v)}/{max}</span></div>; }
    case "countdown": return <Countdown s={s} />;
    case "clock": return <Clock s={s} />;
    case "calendar": return <Calendar s={s} />;
    case "tabs": { const items = (s.items || []).filter((i: any) => i?.label); if (!items.length) return null; return <Tabs defaultValue={String(Math.min(Math.max(0, num(s.active, 0)), items.length - 1))}><TabsList>{items.map((i: any, k: number) => <TabsTrigger key={k} value={String(k)}>{i.label}</TabsTrigger>)}</TabsList>{items.map((i: any, k: number) => <TabsContent key={k} value={String(k)}>{i.child && <Render s={i.child} open={open} title={title} />}</TabsContent>)}</Tabs>; }
    case "accordion": return <Accordion s={s} open={open} />;
    case "steps": { const items = (Array.isArray(s.items) ? s.items : []).map((i: any) => typeof i === "string" ? { title: i } : i).filter(Boolean); const cur = s.current != null ? num(s.current, -1) : -1; return <ol className="grid gap-3">{items.map((it: any, k: number) => { const st = it.status || (cur >= 0 ? (k < cur ? "done" : k === cur ? "current" : "todo") : "todo"); return <li key={k} className="flex gap-3"><span className={cn("grid h-6 w-6 flex-none place-items-center rounded-full border text-xs font-medium", st === "done" ? "border-primary bg-primary text-primary-foreground" : st === "current" ? "border-primary text-primary" : "border-border text-muted-foreground")}>{st === "done" ? "✓" : k + 1}</span><div className="grid gap-0.5 pt-0.5"><div className={cn("text-sm font-medium", st === "todo" && "text-muted-foreground")}>{it.title || it.text}</div>{(it.body || it.note) && <div className="text-xs text-muted-foreground"><Inline text={it.body || it.note} /></div>}</div></li>; })}</ol>; }
    case "timeline": return <div className="grid">{(Array.isArray(s.items) ? s.items : []).filter(Boolean).map((it: any, k: number, arr: any[]) => <div key={k} className="grid grid-cols-[auto_12px_1fr] gap-x-3"><div className="pt-0.5 text-right font-mono text-xs text-muted-foreground">{it.time || it.when}</div><div className="relative flex justify-center"><span className={cn("mt-1.5 h-2.5 w-2.5 rounded-full bg-current", toneClass(it.tone))} />{k < arr.length - 1 && <span className="absolute top-4 h-[calc(100%-4px)] w-px bg-border" />}</div><div className="grid gap-0.5 pb-3"><div className="text-sm font-medium">{it.title}</div>{(it.body || it.text) && <div className="text-xs text-muted-foreground"><Inline text={it.body || it.text} /></div>}</div></div>)}</div>;
    case "embed": case "video": case "audio": case "web": return (s.url || s.src) ? <Embed s={{ ...s, url: s.url || s.src }} /> : null;
    case "youtube": case "vimeo": { const id = String(s.id || ""); const url = s.url || (s.type === "youtube" ? `https://www.youtube.com/watch?v=${id}` : `https://vimeo.com/${id}`); return <Embed s={{ ...s, url }} />; }
    case "map": { const lat = Number(s.lat), lon = Number(s.lon ?? s.lng); if (!isFinite(lat) || !isFinite(lon)) return s.query ? <MapView query={s.query} zoom={Number(s.zoom) || 13} label={s.label} height={s.height} /> : s.url ? <Embed s={s} /> : null; return <MapView lat={lat} lon={lon} zoom={Number(s.zoom) || 14} label={s.label || s.title} height={s.height} />; }
    case "callout": return <div className={cn("rounded-md border p-3 text-sm", s.tone === "ok" ? "note-ok" : s.tone === "warn" || s.tone === "bad" ? "note-warn" : "border-border bg-surface")}>{s.title && <b className="block">{s.title}</b>}<Inline text={s.text} /></div>;
    case "avatar": return <div className="flex items-center gap-3"><Avatar it={s} size={Math.min(160, Math.max(20, num(s.size, 40)))} />{(s.name || s.sub) && <div>{s.name && <div className="text-sm font-medium">{s.name}</div>}{s.sub && <div className="text-xs text-muted-foreground">{s.sub}</div>}</div>}</div>;
    case "avatars": { const items = (Array.isArray(s.items) ? s.items : []).map((i: any) => typeof i === "string" ? { name: i } : i).filter(Boolean); const max = Math.min(20, Math.max(1, num(s.max, 6))); const size = Math.min(120, Math.max(20, num(s.size, 32))); return <div className="flex items-center"><div className="flex">{items.slice(0, max).map((it: any, k: number) => <span key={k} className="-mr-2 rounded-full ring-2 ring-background"><Avatar it={it} size={size} /></span>)}{items.length > max && <span className="-mr-2 inline-grid place-items-center rounded-full border border-border bg-surface text-xs text-muted-foreground ring-2 ring-background" style={{ width: size, height: size }}>+{items.length - max}</span>}</div>{s.label && <span className="ml-4 text-xs text-muted-foreground">{s.label}</span>}</div>; }
    case "skeleton": return <div className="grid gap-2">{Array.from({ length: Math.min(12, Math.max(1, num(s.lines, 3))) }).map((_, i) => <div key={i} className="h-3 animate-pulse rounded bg-surface" style={{ width: `${i === 0 ? 100 : 100 - (i % 3) * 12}%` }} />)}</div>;
    case "button": return <span><button onClick={() => answer("button", String(s.label || s.text || "OK"), title, s.action)} className={cn("rounded-full border px-3 py-1 text-sm", s.primary ? "border-primary bg-primary text-primary-foreground" : "border-border hover:border-primary")}>{s.label || s.text || "OK"}</button></span>;
    case "choice": return <Choice s={s} title={title} />;
    default: return null;
  }
}

export function UiBlock({ title, spec }: { title?: string; spec: Spec }) {
  const [open, setOpen] = useState<any>(null);
  return (
    <motion.div {...rise} className="hairline w-full max-w-[90%] overflow-hidden">
      {title && <div className="border-b border-border bg-surface px-3 py-2 text-sm font-semibold">{title}</div>}
      <div className="p-3"><Render s={spec} open={setOpen} title={title} /></div>
      <AnimatePresence>{open && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-50 grid place-items-center bg-black/80 p-6" onClick={() => setOpen(null)}>
          <motion.img initial={{ scale: 0.96 }} animate={{ scale: 1 }} src={open.url} alt={open.title || open.caption || ""} className="max-h-[80vh] max-w-full rounded-md shadow-2xl" />
          <div className="mt-3 flex items-center gap-3 text-xs text-white"><span>{open.caption || open.title}</span><span className="opacity-70">{open.credit}</span><X className="h-4 w-4" /></div>
        </motion.div>)}
      </AnimatePresence>
    </motion.div>
  );
}
