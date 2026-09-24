"use client";
// A map drawn in the console with Leaflet and OpenStreetMap tiles: a point with a marker and a label, or a place name
// looked up through Nominatim (OSM's geocoder, light use with the page as referer). No key, no account, no frame.
import { useEffect, useRef, useState } from "react";
import "leaflet/dist/leaflet.css";

export type MapProps = { lat?: number; lon?: number; zoom?: number; label?: string; query?: string; height?: number };

export function MapView({ lat, lon, zoom = 14, label, query, height }: MapProps) {
  const el = useRef<HTMLDivElement>(null); const [pt, setPt] = useState<{ lat: number; lon: number; name?: string } | null>(isFinite(Number(lat)) && isFinite(Number(lon)) ? { lat: Number(lat), lon: Number(lon) } : null);
  const [err, setErr] = useState("");
  useEffect(() => {
    if (pt || !query) return;
    fetch(`https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${encodeURIComponent(query)}`, { headers: { Accept: "application/json" } })
      .then(r => r.json()).then(j => j?.[0] ? setPt({ lat: +j[0].lat, lon: +j[0].lon, name: j[0].display_name }) : setErr(`Nothing found for “${query}”.`)).catch(() => setErr("The place lookup did not answer."));
  }, [pt, query]);
  useEffect(() => {
    if (!pt || !el.current) return;
    let map: any;
    import("leaflet").then(L => {
      if (!el.current) return;
      map = L.map(el.current, { zoomControl: true, attributionControl: true, scrollWheelZoom: false }).setView([pt.lat, pt.lon], Math.max(2, Math.min(19, Number(zoom) || 14)));
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' }).addTo(map);
      const m = L.circleMarker([pt.lat, pt.lon], { radius: 8, color: "#4f46e5", weight: 2, fillColor: "#6366f1", fillOpacity: 0.85 }).addTo(map);
      const text = label || pt.name || `${pt.lat.toFixed(4)}, ${pt.lon.toFixed(4)}`; m.bindPopup(text); m.bindTooltip(text, { permanent: !!label, direction: "top", offset: [0, -8] });
    });
    return () => { map?.remove(); };
  }, [pt, zoom, label]);
  const h = Math.min(720, Math.max(160, Number(height) || 320));
  if (err) return <div className="text-xs text-muted-foreground">{err}</div>;
  return <div className="grid gap-1">
    <div ref={el} style={{ height: h }} className="w-full overflow-hidden rounded-sm border border-border bg-surface" />
    {pt && <div className="text-xs text-muted-foreground">{label || pt.name || query} · <a href={`https://www.openstreetmap.org/?mlat=${pt.lat}&mlon=${pt.lon}#map=${zoom}/${pt.lat}/${pt.lon}`} target="_blank" rel="noreferrer" className="underline">open the map</a></div>}
    {!pt && !err && <div className="text-xs text-muted-foreground">Looking up “{query}”…</div>}
  </div>;
}
