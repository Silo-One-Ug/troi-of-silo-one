"use client";
// Modes: permissions, microphone, model and effort go in as the voice-console phrases the agent understands (/say);
// wake word, eyes, voice ID, face ID and the voice itself are settings (/settings), guarded like the native console.
// Every change shows at once: the chip spins until the agent confirms it (the config changes), and a note says what
// happened, including when the voice line is not running or a protected change needs the PIN.
import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, Info, Loader2, Lock, RefreshCw, TriangleAlert } from "lucide-react";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Combobox } from "./ui/combobox";
import { eget, epost, unlockToken, type Config } from "@/lib/edge";
import { cn } from "@/lib/utils";

type Tone = "ok" | "info" | "warn";
type Opt = { v: string; l: string; title?: string; locked?: boolean };

function Seg({ label, value, options, onPick, hint, busy }: { label: string; value: string; options: Opt[]; onPick: (v: string) => void; hint?: string; busy?: string | null }) {
  return (
    <div className="grid min-w-0 gap-1.5">
      <div className="label">{label}</div>
      <div className="flex flex-wrap gap-1.5" role="radiogroup" aria-label={label}>{options.map(o => { const on = value === o.v, spin = busy === o.v; return (
        <button key={o.v} type="button" role="radio" aria-checked={on} title={o.title} disabled={!!busy} onClick={() => !on && onPick(o.v)}
          className={cn("pill h-8 gap-1.5 border px-3 transition-colors disabled:cursor-wait", on ? "pill-note border-transparent" : "border-border text-muted-foreground hover:border-primary/40 hover:text-foreground", spin && "border-primary/50 text-foreground")}>
          {spin ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : o.locked && !on ? <Lock className="h-3 w-3" /> : null}{o.l}
        </button>); })}</div>
      {hint && <div className="text-xs text-muted-foreground">{hint}</div>}
    </div>
  );
}

const Panel = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <section className="hairline grid min-w-0 content-start gap-5 p-4 sm:p-5"><h2 className="text-sm font-semibold">{title}</h2>{children}</section>
);

export function Modes() {
  const [c, setC] = useState<Config | null>(null); const [down, setDown] = useState(""); const [note, setNote] = useState<{ tone: Tone; text: string } | null>(null);
  const [busy, setBusy] = useState<Record<string, string | null>>({}); const [confirmAuto, setConfirmAuto] = useState(false);
  const [model, setModel] = useState("fast"); const [voices, setVoices] = useState<any[]>([]); const [voicesLoading, setVoicesLoading] = useState(false); const [strict, setStrict] = useState<number | null>(null);
  const noteTimer = useRef<any>(0); const cfg = useRef<Config | null>(null);
  const tell = useCallback((tone: Tone, text: string) => { setNote({ tone, text }); clearTimeout(noteTimer.current); noteTimer.current = setTimeout(() => setNote(null), tone === "warn" ? 12000 : 6000); }, []);
  const load = useCallback(async () => { try { const d = await eget<Config>("/config"); cfg.current = d; setC(d); setDown(""); return d; } catch { setDown("Troi's server is not answering: start Troi from the Desktop."); return null; } }, []);
  useEffect(() => { load(); try { setModel(localStorage.getItem("silo.model") || "fast"); } catch {} const t = setInterval(load, 5000); return () => clearInterval(t); }, [load]);

  // wait for the agent to confirm a change (the config reads back the new value); a short, quick poll
  const confirm = async (check: (d: Config) => boolean, ms = 6000) => { const end = Date.now() + ms; while (Date.now() < end) { await new Promise(r => setTimeout(r, 600)); const d = await load(); if (d && check(d)) return true; } return false; };
  const run = async (key: string, v: string, fn: () => Promise<void>) => { setBusy(b => ({ ...b, [key]: v })); try { await fn(); } finally { setBusy(b => ({ ...b, [key]: null })); } };
  const say = async (t: string) => { const d = await epost("/say", { text: t }); if (!d.ok) tell("warn", d.error ? `Not sent: ${d.error}.` : "Not sent: the voice line did not answer."); return !!d.ok; };
  const locked = () => !!c?.guarded && !unlockToken();
  const needsPin = (what: string) => tell("warn", `${what} is protected. Unlock with your PIN in the bar, then pick it again.`);
  const set = async (body: any, done: string) => {
    const d = await epost("/settings", body);
    if (d.pending) { tell("warn", `Protected (${(d.protected || []).join(", ")}): sent to Telegram for approval. Or unlock with your PIN in the bar and pick it again.`); return; }
    if (d.ok) tell("ok", done); else tell("warn", "Not saved: " + (d.error || "the console refused it") + ".");
    load();
  };
  const loadVoices = async (force = false) => { if (voicesLoading || (voices.length && !force)) return; setVoicesLoading(true); try { const d = await eget("/voices"); if (d.ok) setVoices(d.voices || []); else tell("warn", d.error || "Could not load the voices."); } catch { tell("warn", "Could not load the voices."); } setVoicesLoading(false); };
  useEffect(() => { if (c?.elevenlabs_key) loadVoices(); }, [c?.elevenlabs_key]);   // eslint-disable-line react-hooks/exhaustive-deps

  if (!c) return <div className="hairline max-w-xl p-6 text-sm text-muted-foreground">{down || <span className="inline-flex items-center gap-2"><Loader2 className="h-4 w-4 animate-spin" />Reading the agent&apos;s modes…</span>}</div>;
  const perm = c.permission_mode === "bypassPermissions" ? "auto" : "ask", mic = c.mic_mode === "open" ? "open" : "ptt";
  const voiceOpts = voices.map(v => ({ value: v.voice_id, label: v.name, hint: typeof v.labels === "string" ? v.labels : Object.values(v.labels || {}).join(" · ") }));
  if (c.elevenlabs_voice && !voiceOpts.some(o => o.value === c.elevenlabs_voice)) voiceOpts.unshift({ value: c.elevenlabs_voice, label: c.elevenlabs_voice_name || c.elevenlabs_voice, hint: "current" });
  const strictness = strict ?? c.voice_id_threshold;
  const saveStrict = () => { if (strict != null && strict !== c.voice_id_threshold) set({ voice_id_threshold: strict }, `Strictness ${strict.toFixed(2)} saved.`); };

  return (
    <div className="mx-auto grid w-full max-w-5xl gap-4">
      <AnimatePresence>{(note || down) && (
        <motion.div key={(note?.text || down)} initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} role="status"
          className={cn("flex items-start gap-2 rounded-md border px-3 py-2 text-sm", down || note?.tone === "warn" ? "note-warn" : note?.tone === "ok" ? "note-ok" : "hairline")}>
          {down || note?.tone === "warn" ? <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" /> : note?.tone === "ok" ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" /> : <Info className="mt-0.5 h-4 w-4 shrink-0" />}
          <span className="min-w-0">{down || note?.text}</span>
        </motion.div>)}
      </AnimatePresence>
      {!c.guarded || unlockToken() ? null : <div className="flex items-center gap-2 text-xs text-muted-foreground"><Lock className="h-3.5 w-3.5" />Changes marked with a lock need your PIN (unlock in the bar) or your approval on Telegram.</div>}

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="How it works">
          <Seg label="Permissions" value={perm} busy={busy.perm} hint={confirmAuto ? "Click Confirm to let it act without asking." : undefined}
            options={[{ v: "ask", l: "Ask first", title: "Asks out loud before changing anything" }, { v: "auto", l: confirmAuto ? "Confirm" : "Auto-approve", title: "Acts without asking. Needs a second click.", locked: locked() }]}
            onPick={v => run("perm", v, async () => {
              if (v === "ask") { setConfirmAuto(false); if (await say("start asking again")) tell(await confirm(d => d.permission_mode !== "bypassPermissions") ? "ok" : "info", "Asking first again."); return; }
              if (locked()) return needsPin("Auto-approve");
              if (!confirmAuto) { if (await say("stop asking for permission")) { setConfirmAuto(true); tell("info", `${c.name} will act without asking once you click Confirm.`); setTimeout(() => setConfirmAuto(false), 20000); } return; }
              setConfirmAuto(false); if (await say("confirm")) { const ok = await confirm(d => d.permission_mode === "bypassPermissions"); tell(ok ? "ok" : "info", ok ? `${c.name} acts without asking now.` : "Sent. The voice line has not confirmed it yet."); }
            })} />
          <Seg label="Microphone" value={mic} busy={busy.mic} options={[{ v: "ptt", l: "Push to talk", title: `Hold ${c.key} and speak` }, { v: "open", l: "Hands-free", title: "Always listening", locked: locked() }]}
            onPick={v => run("mic", v, async () => {
              if (v === "open" && locked()) return needsPin("Hands-free listening");
              if (!(await say(v === "ptt" ? "push to talk mode" : "go hands free"))) return;
              const ok = await confirm(d => (d.mic_mode === "open" ? "open" : "ptt") === v);
              tell(ok ? "ok" : "info", ok ? (v === "ptt" ? "Push to talk." : "Hands-free listening.") : "Sent. The voice line has not confirmed it yet.");
            })} />
          <Seg label="Wake word" value={c.wake_word === false ? "off" : "on"} busy={busy.wake} options={[{ v: "on", l: "Say the name" }, { v: "off", l: "Off" }]}
            onPick={v => run("wake", v, () => set({ wake_word: v === "on" }, v === "on" ? `Hands-free acts only when it hears "${c.name}".` : "Wake word off."))} />
          <Seg label="Model" value={model} busy={busy.model} hint={model === "deep" ? `${c.deep_model}, for this session` : c.model}
            options={[{ v: "fast", l: "Fast", title: c.model }, { v: "deep", l: "Deep", title: c.deep_model + ". This session only." }]}
            onPick={v => run("model", v, async () => { if (await say(v === "deep" ? "switch to the deep model" : "back to the fast model")) { setModel(v); try { localStorage.setItem("silo.model", v); } catch {} tell("ok", v === "deep" ? "Deep model for this session." : "Fast model."); } })} />
          <Seg label="Effort" value={c.effort || ""} busy={busy.effort} hint={c.effort ? undefined : "the model's default"} options={[{ v: "low", l: "Low" }, { v: "medium", l: "Medium" }, { v: "high", l: "High" }, { v: "max", l: "Max" }]}
            onPick={v => run("effort", v, async () => { if (!(await say(`set effort to ${v}`))) return; const ok = await confirm(d => d.effort === v); tell(ok ? "ok" : "info", ok ? `Effort ${v}, saved as the default.` : `Effort ${v} sent. The page shows it once the agent reports it.`); })} />
        </Panel>

        <Panel title="Senses and voice">
          <Seg label="Eyes" value={c.eyes || "off"} busy={busy.eyes} options={[{ v: "off", l: "Off" }, { v: "every", l: "Every reply", title: "A fresh camera frame with every reply" }, { v: "watch", l: "Watch", title: "Looks when the view changes" }, { v: "screen", l: "Screen", title: "A screenshot with every request" }]}
            onPick={v => run("eyes", v, () => set({ eyes: v }, v === "off" ? "Camera off." : v === "screen" ? "Screen sight on." : "Camera on: " + v + "."))} />
          <Seg label="Voice ID" value={c.voice_id || "off"} busy={busy.vid} hint={c.voice_print ? "your voice is known" : "no voice print yet"} options={[{ v: "off", l: "Off" }, { v: "on", l: "Only me" }, { v: "learn", l: "Learn my voice", title: "Hold the talk key and read aloud for about a minute" }]}
            onPick={v => run("vid", v, async () => { if (v === "on" && !c.voice_print) { tell("warn", `${c.name} does not know your voice yet. Learn it first.`); return; } await set({ voice_id: v }, v === "learn" ? "Read aloud until the transcript says the print is built." : v === "on" ? "Answers only your voice." : "Voice ID off."); })} />
          <div className="grid min-w-0 gap-1.5">
            <div className="label flex items-center justify-between"><span>Strictness</span><span className="tabular-nums normal-case tracking-normal text-foreground">{strictness.toFixed(2)}</span></div>
            <input type="range" min="0.6" max="0.95" step="0.01" value={strictness} aria-label="Voice ID strictness" onChange={e => setStrict(Number(e.target.value))} onPointerUp={saveStrict} onKeyUp={saveStrict} onBlur={saveStrict} className="w-full min-w-0 accent-[hsl(var(--primary))]" />
            <div className="flex justify-between text-[11px] text-muted-foreground"><span>lenient</span><span>strict</span></div>
          </div>
          <div className="grid min-w-0 gap-1.5"><div className="label">Face ID</div><div className="flex flex-wrap items-center gap-2"><Badge tone={c.face_print ? "ok" : "warn"}>{c.face_env === false ? "not installed" : c.face_print ? "known" : "not learnt"}</Badge><Button size="sm" variant="outline" disabled={!!busy.face} onClick={() => run("face", "learn", () => set({ face_id: "learn" }, "Look at the camera: five shots, about ten seconds."))}>{busy.face && <Loader2 className="h-3.5 w-3.5 animate-spin" />}Learn my face</Button></div></div>
          <Seg label="Voice" value={c.tts || "kokoro"} busy={busy.tts} options={[{ v: "kokoro", l: `Kokoro (${c.kokoro_voice})` }, { v: "elevenlabs", l: "ElevenLabs" }]} hint={c.elevenlabs_key ? undefined : "no ElevenLabs key in the Keychain yet"}
            onPick={v => run("tts", v, async () => { if (v === "elevenlabs" && !c.elevenlabs_key) { tell("warn", "ElevenLabs needs your key first (the welcome page keeps it in the Keychain)."); return; } await set({ tts: v, elevenlabs_voice: c.elevenlabs_voice || "" }, v === "elevenlabs" ? `${c.name} speaks with ElevenLabs from the next line.` : `${c.name} speaks with Kokoro.`); })} />
          {c.elevenlabs_key && (
            <div className="grid min-w-0 gap-1.5"><div className="label">ElevenLabs voice</div>
              <div className="flex min-w-0 gap-2">
                <Combobox className="flex-1" value={c.elevenlabs_voice || ""} options={voiceOpts} loading={voicesLoading} onOpen={() => loadVoices()} placeholder="Choose a voice…" empty="No voice by that name."
                  onChange={v => run("voice", v, () => set({ tts: "elevenlabs", elevenlabs_voice: v }, `Voice changed to ${voiceOpts.find(o => o.value === v)?.label || v}.`))} />
                <Button size="icon" variant="outline" title="Reload the voices" aria-label="Reload the voices" disabled={voicesLoading} onClick={() => loadVoices(true)}><RefreshCw className={cn("h-4 w-4", voicesLoading && "animate-spin")} /></Button>
              </div>
            </div>)}
        </Panel>
      </div>
    </div>
  );
}
