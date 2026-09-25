"use client";
// Sounds: a soft pad while the agent works (it fades in with the state and out when the state leaves), and a short
// chime the moment the work is done and the agent is about to answer. Made in the browser with Web Audio: no files,
// nothing fetched, a warm low fifth under a slow filter with a breath of wind. On by default; off in Modes, or in More
// on a phone. A browser plays nothing before the first click or key on a page, so the first stretch of work after a
// fresh load may be silent until you touch the page.
import { useEffect, useRef } from "react";
import { emit, on } from "@/lib/edge";

const KEY = "silo.worksound";
export const workSoundOn = () => { try { return localStorage.getItem(KEY) !== "off"; } catch { return true; } };
export const setWorkSound = (v: boolean) => { try { localStorage.setItem(KEY, v ? "on" : "off"); } catch {} emit("worksound", v); };

type Pad = { master: GainNode; sources: (OscillatorNode | AudioBufferSourceNode)[]; since: number };
class Engine {
  ctx: AudioContext | null = null; pad: Pad | null = null; chimes = 0; pads = 0;
  ensure() {
    if (!this.ctx) { try { this.ctx = new (window.AudioContext || (window as any).webkitAudioContext)(); } catch { return null; } }
    if (this.ctx.state === "suspended") this.ctx.resume().catch(() => {});
    return this.ctx;
  }
  get live() { return !!this.ctx && this.ctx.state === "running"; }
  startPad() {
    const ctx = this.ensure(); if (!ctx || this.pad) return;
    const t = ctx.currentTime, sources: Pad["sources"] = [];
    const master = ctx.createGain(); master.gain.setValueAtTime(0.0001, t); master.gain.exponentialRampToValueAtTime(0.07, t + 2.5); master.connect(ctx.destination);
    const filter = ctx.createBiquadFilter(); filter.type = "lowpass"; filter.frequency.value = 520; filter.Q.value = 0.7; filter.connect(master);
    const sweep = ctx.createOscillator(); sweep.frequency.value = 0.08; const sweepG = ctx.createGain(); sweepG.gain.value = 220; sweep.connect(sweepG); sweepG.connect(filter.frequency); sweep.start(); sources.push(sweep);   // the filter opens and closes, slowly
    const breath = ctx.createOscillator(); breath.frequency.value = 0.05; const breathG = ctx.createGain(); breathG.gain.value = 0.015; breath.connect(breathG); breathG.connect(master.gain); breath.start(); sources.push(breath);   // the whole pad breathes
    for (const [f, type, g, det] of [[110, "sine", 0.5, 0], [164.81, "sine", 0.34, 4], [220, "triangle", 0.1, -3], [329.63, "sine", 0.07, 6]] as [number, OscillatorType, number, number][]) {   // A2, E3, A3, E4: a low fifth and its shadow
      const o = ctx.createOscillator(); o.type = type; o.frequency.value = f; o.detune.value = det; const og = ctx.createGain(); og.gain.value = g; o.connect(og); og.connect(filter); o.start(); sources.push(o);
    }
    const buf = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate); const d = buf.getChannelData(0); for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;   // a breath of wind under it all
    const wind = ctx.createBufferSource(); wind.buffer = buf; wind.loop = true; const windF = ctx.createBiquadFilter(); windF.type = "lowpass"; windF.frequency.value = 260; const windG = ctx.createGain(); windG.gain.value = 0.16; wind.connect(windF); windF.connect(windG); windG.connect(master); wind.start(); sources.push(wind);
    this.pad = { master, sources, since: Date.now() }; this.pads++;
  }
  stopPad() {
    const ctx = this.ctx, pad = this.pad; if (!ctx || !pad) return; this.pad = null;
    const t = ctx.currentTime; pad.master.gain.cancelScheduledValues(t); pad.master.gain.setValueAtTime(Math.max(0.0001, pad.master.gain.value), t); pad.master.gain.exponentialRampToValueAtTime(0.0001, t + 1.2);
    setTimeout(() => { for (const s of pad.sources) { try { s.stop(); } catch {} } try { pad.master.disconnect(); } catch {} }, 1400);
  }
  chime() {                                                          // a small bell, A5 then E6, with a whisper of the octave over each
    const ctx = this.ctx; if (!ctx || ctx.state !== "running") return;
    const t = ctx.currentTime;
    const note = (f: number, at: number, g: number, len: number) => { const o = ctx.createOscillator(); o.type = "sine"; o.frequency.value = f; const og = ctx.createGain(); og.gain.setValueAtTime(0.0001, at); og.gain.exponentialRampToValueAtTime(g, at + 0.02); og.gain.exponentialRampToValueAtTime(0.0001, at + len); o.connect(og); og.connect(ctx.destination); o.start(at); o.stop(at + len + 0.05); };
    note(880, t, 0.1, 1.1); note(1760, t, 0.02, 0.7); note(1318.5, t + 0.17, 0.09, 1.4); note(2637, t + 0.17, 0.018, 0.8);
    this.chimes++;
  }
}
const engine = typeof window !== "undefined" ? new Engine() : null;

export function Sounds({ state }: { state: string }) {
  const was = useRef(false); const enabled = useRef(true);
  useEffect(() => {                                                  // the browser lets a page play only after a touch: make the context then
    enabled.current = workSoundOn(); (window as any).__siloSounds = engine;
    const wake = () => { engine?.ensure(); }; addEventListener("pointerdown", wake); addEventListener("keydown", wake);
    const off = on("worksound", (v: boolean) => { enabled.current = !!v; if (!v) engine?.stopPad(); });
    return () => { removeEventListener("pointerdown", wake); removeEventListener("keydown", wake); off(); };
  }, []);
  useEffect(() => {
    const working = state === "working" || state === "thinking";
    if (working) { if (enabled.current) engine?.startPad(); }
    else { engine?.stopPad(); if (was.current && enabled.current && (state === "idle" || state === "speaking")) engine?.chime(); }
    was.current = working;
  }, [state]);
  return null;
}
