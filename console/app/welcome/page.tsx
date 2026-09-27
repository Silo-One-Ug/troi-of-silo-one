"use client";
// The welcome: first the story (who Troi is, in seven scenes over the planet), then the setup, one step at a time.
// Everything it asks for is written where it belongs: names and choices to the settings, secrets to the Keychain,
// the vault to the folder you pick. Every optional step can be skipped and done later from the console.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import gsap from "gsap";
import { ArrowRight, Check, ChevronLeft, ChevronRight, Eye, FolderOpen, KeyRound, Loader2, Mic, MonitorSmartphone, Send, ShieldCheck, Sparkles, Volume2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Combobox } from "@/components/ui/combobox";
import { Input } from "@/components/ui/input";
import { compatibility, machine, type Check as Chk, type Machine } from "@/lib/detect";
import { eget, epost, rememberUnlock, unlockToken } from "@/lib/edge";
import { agentName, useAgentName } from "@/lib/name";
import { cn } from "@/lib/utils";

const Space = dynamic(() => import("@/components/space").then(m => m.Space), { ssr: false });
const ease = [0.22, 1, 0.36, 1] as const;

// ---------------------------------------------------------------------------------------------------------- the story
type Scene = { view: string; kicker: string; title: string; body: string; visual?: "wave" | "eyes" | "work" | "memory" | "guard" };
const SCENES: Scene[] = [
  { view: "w-intro", kicker: "", title: "", body: "" },
  { view: "w-listen", kicker: "It listens", title: "Talk to it like a person.", body: "Hold a key and speak, or say its name when it listens hands-free. It answers out loud, in a voice you choose, and only to your voice when you ask it to.", visual: "wave" },
  { view: "w-see", kicker: "It sees, when you ask", title: "Eyes that stay shut until you open them.", body: "It takes a look through the camera or reads your screen when you ask. The camera stays off until you switch it on, and nothing it sees leaves this Mac.", visual: "eyes" },
  { view: "w-work", kicker: "It works", title: "Not advice. Finished work.", body: "It organises your files, opens and quits apps, drives its own browser, keeps your calendar, records meetings, reviews code, watches your servers, and draws its answers as charts and cards.", visual: "work" },
  { view: "w-remember", kicker: "It remembers", title: "A memory without a ceiling.", body: "Your notes live in a vault you own. Everything it does is kept in one record on this Mac. Nothing leaves unless you send it.", visual: "memory" },
  { view: "w-ask", kicker: "It asks first", title: "It never deletes anything.", body: "Anything that cannot be undone waits for you: your PIN, your face, your voice, or a tap on your phone. Nobody else can change how it behaves.", visual: "guard" },
  { view: "w-setup", kicker: "Five minutes", title: "Let's set it up.", body: "Your name, your Mac, a memory, a voice, your phone, a PIN. Everything can be changed later.", },
];

function Letters({ text, className }: { text: string; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => { if (!ref.current) return; const els = ref.current.querySelectorAll("span"); gsap.fromTo(els, { yPercent: 110, opacity: 0, rotateX: -60 }, { yPercent: 0, opacity: 1, rotateX: 0, duration: 1.4, ease: "expo.out", stagger: 0.09, delay: 0.25 }); }, [text]);
  return <span ref={ref} className={cn("inline-flex overflow-hidden [perspective:600px]", className)}>{text.split("").map((c, i) => <span key={i} className="inline-block will-change-transform">{c}</span>)}</span>;
}

function Wave() {
  return <div className="flex h-16 items-center gap-1.5">{Array.from({ length: 28 }).map((_, i) => <motion.span key={i} className="w-1.5 rounded-full bg-gradient-to-t from-indigo-400 to-sky-300" animate={{ height: [8, 14 + ((i * 37) % 44), 8] }} transition={{ duration: 1.1 + (i % 5) * 0.12, repeat: Infinity, ease: "easeInOut", delay: i * 0.04 }} />)}</div>;
}
const WORK = ["Files", "Apps", "Browser", "Pointer & keys", "Calendar", "Meetings", "Music", "Code reviews", "Servers", "Reminders", "Reports", "News", "Pictures", "Telegram", "Calls"];
function Visual({ kind }: { kind?: Scene["visual"] }) {
  if (kind === "wave") return <Wave />;
  if (kind === "eyes") return <div className="flex items-center gap-4"><motion.div className="grid h-16 w-16 place-items-center rounded-full border border-white/20 bg-white/5" animate={{ scaleY: [1, 1, 0.08, 1] }} transition={{ duration: 3.6, repeat: Infinity, times: [0, 0.82, 0.88, 1] }}><Eye className="h-7 w-7 text-sky-200" /></motion.div><span className="text-sm text-white/60">off until you say so</span></div>;
  if (kind === "work") return <div className="flex max-w-xl flex-wrap gap-2">{WORK.map((w, i) => <motion.span key={w} initial={{ opacity: 0, y: 10, filter: "blur(6px)" }} animate={{ opacity: 1, y: 0, filter: "blur(0px)" }} transition={{ delay: 0.35 + i * 0.06, duration: 0.6, ease }} className="rounded-full border border-white/15 bg-white/[0.06] px-3 py-1 text-sm text-white/80 backdrop-blur">{w}</motion.span>)}</div>;
  if (kind === "memory") return <div className="relative h-24 w-56">{[0, 1, 2, 3].map(i => <motion.div key={i} className="absolute h-20 w-36 rounded-lg border border-white/15 bg-white/[0.05] backdrop-blur" style={{ left: i * 18, top: i * 6 }} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1 - i * 0.18, x: 0 }} transition={{ delay: 0.3 + i * 0.12, duration: 0.7, ease }}><div className="m-3 h-1.5 w-16 rounded bg-white/30" /><div className="mx-3 h-1.5 w-24 rounded bg-white/15" /><div className="mx-3 mt-1.5 h-1.5 w-20 rounded bg-white/15" /></motion.div>)}</div>;
  if (kind === "guard") return <div className="flex flex-wrap gap-2">{["PIN", "Face", "Voice", "Telegram"].map((w, i) => <motion.span key={w} initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.3 + i * 0.1, duration: 0.5, ease }} className="flex items-center gap-1.5 rounded-full border border-emerald-300/25 bg-emerald-300/10 px-3 py-1 text-sm text-emerald-100"><ShieldCheck className="h-3.5 w-3.5" />{w}</motion.span>)}</div>;
  return null;
}

function Story({ onDone }: { onDone: () => void }) {
  const agent = useAgentName();
  const [i, setI] = useState(0); const lock = useRef(0);
  const go = useCallback((d: number) => { const now = Date.now(); if (now - lock.current < 700) return; lock.current = now; setI(x => { const n = x + d; if (n >= SCENES.length) { onDone(); return x; } return Math.max(0, n); }); }, [onDone]);
  useEffect(() => {
    const key = (e: KeyboardEvent) => { if (["ArrowRight", "ArrowDown", "Enter", " ", "PageDown"].includes(e.key)) { e.preventDefault(); go(1); } if (["ArrowLeft", "ArrowUp", "PageUp"].includes(e.key)) { e.preventDefault(); go(-1); } };
    const wheel = (e: WheelEvent) => { if (Math.abs(e.deltaY) > 24) go(e.deltaY > 0 ? 1 : -1); };
    addEventListener("keydown", key); addEventListener("wheel", wheel, { passive: true });
    return () => { removeEventListener("keydown", key); removeEventListener("wheel", wheel); };
  }, [go]);
  const s = SCENES[i];
  return (
    <>
      <Space state={i === 1 ? "listening" : i === 3 ? "working" : "idle"} view={s.view} />
      <div className="pointer-events-none fixed inset-0 bg-gradient-to-r from-black/80 via-black/35 to-transparent" />
      <div className="relative z-10 flex min-h-screen flex-col">
        <header className="flex items-center justify-between px-6 py-5 sm:px-10">
          <div className="flex items-center gap-2.5 text-xs font-medium uppercase tracking-[0.3em] text-white/60"><img src="/brand/mark.svg" alt="" className="h-6 w-6" />Troi of Silo One</div>
          <button onClick={onDone} className="text-sm text-white/60 transition hover:text-white">Skip to setup</button>
        </header>
        <main className="flex flex-1 items-center px-6 sm:px-10 lg:px-20">
          <AnimatePresence mode="wait">
            <motion.section key={i} initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -16 }} transition={{ duration: 0.8, ease }} className="max-w-2xl">
              {i === 0 ? (
                <div className="grid gap-6">
                  <motion.img src="/brand/mark.svg" alt="" initial={{ opacity: 0, scale: 0.7, rotate: -12 }} animate={{ opacity: 1, scale: 1, rotate: 0, y: [0, -6, 0] }} transition={{ opacity: { duration: 1.2, ease }, scale: { duration: 1.4, ease }, rotate: { duration: 1.6, ease }, y: { duration: 6, repeat: Infinity, ease: "easeInOut", delay: 1.6 } }} className="h-24 w-24 drop-shadow-[0_0_28px_rgba(140,149,247,0.35)] sm:h-28 sm:w-28" />
                  <h1 className="font-semibold leading-[0.9] tracking-tight text-white"><Letters key={agent} text={agent} className="text-[clamp(5rem,16vw,12rem)]" /></h1>
                  <motion.div initial={{ opacity: 0, letterSpacing: "0.1em" }} animate={{ opacity: 1, letterSpacing: "0.6em" }} transition={{ delay: 0.9, duration: 1.6, ease }} className="text-sm font-medium uppercase text-sky-200/80">of Silo One</motion.div>
                  <motion.p initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 1.4, duration: 0.9, ease }} className="max-w-md text-xl text-white/75">A chief of staff that lives on your Mac.</motion.p>
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 2, duration: 0.8 }}><Button size="lg" onClick={() => go(1)} className="group mt-2 rounded-full bg-white px-7 text-black hover:bg-white/90">Meet {agent}<ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" /></Button></motion.div>
                </div>
              ) : (
                <div className="grid gap-6">
                  <div className="text-xs font-medium uppercase tracking-[0.35em] text-sky-200/80">{s.kicker}</div>
                  <h2 className="text-[clamp(2.2rem,5vw,4rem)] font-semibold leading-[1.05] tracking-tight text-white">{s.title}</h2>
                  <p className="max-w-xl text-lg leading-relaxed text-white/70">{s.body}</p>
                  <Visual kind={s.visual} />
                  {i === SCENES.length - 1 && <div><Button size="lg" onClick={onDone} className="group mt-2 rounded-full bg-white px-7 text-black hover:bg-white/90">Begin setup<ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" /></Button></div>}
                </div>
              )}
            </motion.section>
          </AnimatePresence>
        </main>
        <footer className="flex items-center justify-between px-6 py-6 sm:px-10">
          <div className="flex gap-2">{SCENES.map((_, k) => <button key={k} aria-label={`scene ${k + 1}`} onClick={() => setI(k)} className={cn("h-1.5 rounded-full transition-all duration-500", k === i ? "w-8 bg-white" : "w-1.5 bg-white/30 hover:bg-white/60")} />)}</div>
          <div className="flex items-center gap-2 text-white/60">{i > 0 && <button onClick={() => go(-1)} className="rounded-full p-2 hover:bg-white/10" aria-label="back"><ChevronLeft className="h-5 w-5" /></button>}<button onClick={() => go(1)} className="rounded-full p-2 hover:bg-white/10" aria-label="next"><ChevronRight className="h-5 w-5" /></button></div>
        </footer>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------------------------------------- setup
type Status = { owner?: string; owner_full?: string; address?: string; call?: string; vault?: string; vault_ready?: boolean; vault_candidates?: string[]; folder_candidates?: string[]; file_roots?: string[]; secrets?: Record<string, boolean>; screen?: boolean; accessibility?: boolean; gh?: boolean; backup_repo?: string; github_org?: string; github_account?: string; backup_org?: string; telegram?: { token: boolean; bot: string; paired: boolean; code: string }; face_env?: boolean; voice_env?: boolean };
const STEPS = [
  { key: "you", title: "You", icon: Sparkles },
  { key: "mac", title: "This Mac", icon: MonitorSmartphone },
  { key: "memory", title: "Memory", icon: FolderOpen },
  { key: "voice", title: "Voice", icon: Volume2 },
  { key: "phone", title: "Your phone", icon: Send },
  { key: "security", title: "Security", icon: ShieldCheck },
  { key: "extras", title: "Extras", icon: KeyRound },
  { key: "ready", title: "Ready", icon: Check },
] as const;

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return <label className="grid gap-1.5"><span className="text-xs font-medium uppercase tracking-[0.2em] text-white/55">{label}</span>{children}{hint && <span className="text-xs text-white/45">{hint}</span>}</label>;
}
const input = "h-11 border-white/15 bg-white/[0.06] text-white placeholder:text-white/35 focus-visible:ring-sky-300/40";
function Row({ ok, title, note, action }: { ok: boolean | null; title: string; note?: string; action?: React.ReactNode }) {
  return <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3"><span className={cn("grid h-6 w-6 shrink-0 place-items-center rounded-full", ok === null ? "bg-white/10" : ok ? "bg-emerald-400/20 text-emerald-300" : "bg-amber-400/15 text-amber-200")}>{ok === null ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : ok ? <Check className="h-3.5 w-3.5" /> : "!"}</span><div className="min-w-0 flex-1"><div className="text-sm text-white">{title}</div>{note && <div className="text-xs text-white/50">{note}</div>}</div>{action}</div>;
}
function Note({ tone = "info", children }: { tone?: "info" | "ok" | "warn"; children: React.ReactNode }) {
  return <div className={cn("rounded-xl border px-4 py-3 text-sm", tone === "ok" ? "border-emerald-300/25 bg-emerald-300/10 text-emerald-100" : tone === "warn" ? "border-amber-300/25 bg-amber-300/10 text-amber-100" : "border-white/10 bg-white/[0.04] text-white/70")}>{children}</div>;
}

function Setup() {
  const agent = useAgentName();
  const router = useRouter();
  const [step, setStep] = useState(0); const [done, setDone] = useState<Record<string, boolean>>({}); const [st, setSt] = useState<Status>({}); const [msg, setMsg] = useState<{ tone: "info" | "ok" | "warn"; text: string } | null>(null); const [busy, setBusy] = useState(false);
  const refresh = useCallback(async () => { try { setSt(await eget("/setup/status")); } catch { setMsg({ tone: "warn", text: `The agent is not answering yet. Is ${agentName()} running? (double-click ${agentName()} on the Desktop)` }); } }, []);
  useEffect(() => { refresh(); }, [refresh]);
  const mark = (k: string) => setDone(d => ({ ...d, [k]: true }));
  const next = () => { setMsg(null); setStep(s => Math.min(STEPS.length - 1, s + 1)); };
  const say = (tone: "info" | "ok" | "warn", text: string) => setMsg({ tone, text });

  // ---- you
  // one name: the first word is what Troi greets you by, the whole of it goes on anything written for other people
  const [you, setYou] = useState({ owner_full: "", call: "sir" });
  const firstName = (you.owner_full.trim().split(/\s+/)[0] || "");
  useEffect(() => { if (st.owner !== undefined) setYou(y => ({ owner_full: y.owner_full || st.owner_full || st.owner || "", call: y.call || st.call || "sir" })); }, [st.owner, st.owner_full, st.call]);
  const saveYou = async () => { if (!firstName) { say("warn", `Your name, please: it is how ${agentName()} knows you.`); return; } setBusy(true); try { const call = you.call === "your name" ? firstName : (you.call || "sir"); const d = await epost("/setup/profile", { owner: firstName, owner_full: you.owner_full.trim(), address: firstName, call }); if (d.ok) { mark("you"); next(); } else say("warn", d.error || "Not saved."); } finally { setBusy(false); } };

  // ---- this Mac (and the folders it may organise)
  const [roots, setRoots] = useState<string[] | null>(null);
  useEffect(() => { if (roots === null && st.folder_candidates) setRoots((st.file_roots || []).filter(r => st.folder_candidates!.includes(r))); }, [st.folder_candidates, st.file_roots, roots]);
  const toggleRoot = (r: string) => setRoots(x => (x || []).includes(r) ? (x || []).filter(y => y !== r) : [...(x || []), r]);
  const saveMac = async () => { if (roots) { const d = await epost("/setup/profile", { file_roots: roots }); if (!d.ok) { say("warn", d.error || "The folders were not saved."); return; } } mark("mac"); next(); };
  const [m, setM] = useState<Machine | null>(null); const [checks, setChecks] = useState<Chk[]>([]); const [mic, setMic] = useState<"" | "ok" | "no">(""); const [cam, setCam] = useState<"" | "ok" | "no">(""); const [ptt, setPtt] = useState(false); const [heard, setHeard] = useState("");
  useEffect(() => {                                                // the talk key: listening shows it works; the words show the ears do too
    if (STEPS[step].key !== "mac") return; setM(machine()); setChecks(compatibility()); let stop = false; let pos: number | null = null;
    const t = async () => {
      if (stop) return;
      try {
        const d = await eget("/state"); if (d.state === "listening") setPtt(true);
        if (pos === null) pos = (await eget("/history?limit=1")).pos ?? 0;
        else { const tr = await eget(`/transcript?pos=${pos}`); pos = tr.pos; const you = (tr.items || []).filter((i: any) => i.role === "you" && !String(i.text).startsWith("(")).pop(); if (you) { setPtt(true); setHeard(String(you.text)); } }
      } catch {}
      setTimeout(t, 500);
    };
    t(); return () => { stop = true; };
  }, [step]);
  const testMic = async () => { try { const s = await navigator.mediaDevices.getUserMedia({ audio: true }); s.getTracks().forEach(t => t.stop()); setMic("ok"); } catch { setMic("no"); } };
  const testCam = async () => { try { const s = await navigator.mediaDevices.getUserMedia({ video: true }); s.getTracks().forEach(t => t.stop()); setCam("ok"); } catch { setCam("no"); } };

  // ---- memory
  const [vaultPath, setVaultPath] = useState("");
  const newVault = async () => { setBusy(true); try { const d = await epost("/setup/vault", { mode: "new" }); if (d.ok) { mark("memory"); await refresh(); say("ok", "A new vault, ready at " + d.vault + `. ${agentName()} will interview you to fill it in.`); } else say("warn", d.error || "Not created."); } finally { setBusy(false); } };
  const pickVault = async (p: string) => { if (!p.trim()) return; setBusy(true); try { const d = await epost("/setup/vault", { mode: "use", path: p.trim() }); if (d.ok) { mark("memory"); await refresh(); say("ok", `${agentName()} will use the vault at ` + d.vault + "."); } else say("warn", d.error || "No vault there."); } finally { setBusy(false); } };
  const [backupRepo, setBackupRepo] = useState("");

  // ---- voice
  const [elKey, setElKey] = useState(""); const [voices, setVoices] = useState<any[]>([]); const [voice, setVoice] = useState(""); const [engine, setEngine] = useState<"kokoro" | "elevenlabs">("kokoro");
  const keepKey = async (name: string, value: string, done: string) => { if (!value.trim()) return false; const d = await epost("/keychain", { service: name, value: value.trim() }); if (d.ok) { say("ok", done); await refresh(); return true; } say("warn", "Not kept: " + (d.error || "the Keychain said no")); return false; };
  const loadVoices = async () => { const d = await eget("/voices"); if (d.ok) { setVoices(d.voices); if (!voice && d.voices[0]) setVoice(d.voices.find((v: any) => v.category === "cloned")?.voice_id || d.voices[0].voice_id); } else say("warn", d.error); };
  const saveVoice = async () => { const d = await epost("/settings", { tts: engine, elevenlabs_voice: engine === "elevenlabs" ? voice : "" }); if (d.ok) { mark("voice"); say("ok", engine === "elevenlabs" ? "ElevenLabs it is." : "Kokoro it is: local and free."); } else say("warn", d.error || "Not saved."); };
  const testVoice = async () => { const d = await epost("/say", { text: "(this is a voice test from the welcome: say one short, warm sentence so the owner can hear your voice, nothing else)" }); say(d.ok ? "info" : "warn", d.ok ? `Listen: ${agentName()} is saying something.` : `The voice line is not running yet (start ${agentName()} from the Desktop).`); };

  // ---- phone (Telegram)
  const [tgToken, setTgToken] = useState(""); const tg = st.telegram;
  useEffect(() => { if (STEPS[step].key !== "phone" || !tg?.token || tg.paired) return; const t = setInterval(refresh, 2500); return () => clearInterval(t); }, [step, tg?.token, tg?.paired, refresh]);
  const saveTelegram = async () => { if (await keepKey("telegram", tgToken, "Kept. Waking the Telegram bridge…")) { setTgToken(""); await epost("/setup/services", { action: "restart", name: "telegram" }); setTimeout(refresh, 4000); } };
  useEffect(() => { if (tg?.paired) mark("phone"); }, [tg?.paired]);

  // ---- security
  const [pin, setPin] = useState(""); const [pin2, setPin2] = useState(""); const [unlocked, setUnlocked] = useState(false); const [faceMsg, setFaceMsg] = useState(""); const [voiceMsg, setVoiceMsg] = useState("");
  useEffect(() => { setUnlocked(!!unlockToken()); }, [step]);
  const savePin = async () => {
    if (!/^\d{4,12}$/.test(pin)) { say("warn", "A PIN is 4 to 12 digits."); return; } if (pin !== pin2) { say("warn", "The two PINs differ."); return; }
    if (!(await keepKey("pin", pin, "PIN kept in the Keychain."))) return;
    const u = await epost("/unlock", { pin }); if (u.ok) { rememberUnlock(u.token, u.until); setUnlocked(true); } setPin(""); setPin2(""); mark("security");
  };
  const unlock = async () => { const u = await epost("/unlock", { pin }); if (u.ok) { rememberUnlock(u.token, u.until); setUnlocked(true); setPin(""); mark("security"); } else say("warn", u.error || "Wrong PIN."); };
  const learnFace = async () => { const d = await epost("/settings", { face_id: "learn" }); if (d.pending) { setFaceMsg("Protected: unlock with your PIN first."); return; } setFaceMsg("Look at the camera: five photos, about ten seconds…"); let n = 0; const t = setInterval(async () => { n++; const c = await eget("/config").catch(() => null); if (c?.face_print) { clearInterval(t); setFaceMsg("Your face is known."); } else if (n > 20) { clearInterval(t); setFaceMsg("It did not finish. Check the camera permission, then try again."); } }, 1500); };
  const learnVoice = async () => { const d = await epost("/settings", { voice_id: "learn" }); if (d.pending) { setVoiceMsg("Protected: unlock with your PIN first."); return; } setVoiceMsg("Hold Right Option and read the passage below aloud, a few sentences at a time, until this says your voice is known."); let n = 0; const t = setInterval(async () => { n++; const c = await eget("/config").catch(() => null); if (c?.voice_print) { clearInterval(t); setVoiceMsg("Your voice is known. Voice ID is on."); } else if (n > 120) clearInterval(t); }, 1500); };

  // ---- extras
  const [ex, setEx] = useState({ openai: "", gemini: "", agoraId: "", agoraCert: "" });
  const saveExtras = async () => {
    const kept: string[] = [];
    if (ex.openai && await keepKey("openai", ex.openai, "")) kept.push("OpenAI");
    if (ex.gemini && await keepKey("gemini", ex.gemini, "")) kept.push("Gemini");
    if (ex.agoraId && await keepKey("agora-appid", ex.agoraId, "")) kept.push("Agora");
    if (ex.agoraCert && await keepKey("agora-cert", ex.agoraCert, "")) kept.push("Agora certificate");
    setEx({ openai: "", gemini: "", agoraId: "", agoraCert: "" }); mark("extras"); say("ok", kept.length ? "Kept: " + kept.join(", ") + "." : "Nothing to keep; you can add these later."); next();
  };

  // ---- ready: the voice line starts over with everything written here, and introduces itself
  const [waking, setWaking] = useState<"" | "on" | "novoice">("");
  const finish = async () => {
    setBusy(true);
    const d = await epost("/setup/finish", backupRepo.trim() ? { backup_repo: backupRepo.trim() } : {});
    if (!d.ok) { setBusy(false); say("warn", d.error || `Not finished: is ${agentName()} running?`); return; }
    setWaking(d.voice ? "on" : "novoice");
    setTimeout(() => router.replace("/conversation"), d.voice ? 3200 : 5200);
  };

  const k = STEPS[step].key;
  const readyItems = [["You", firstName || st.owner], ["Memory", st.vault_ready ? "vault ready" : ""], ["Voice", engine === "elevenlabs" ? "ElevenLabs" : "Kokoro"], ["Phone", tg?.paired ? "paired" : ""], ["PIN", st.secrets?.pin ? "set" : ""], ["Screen", st.screen ? "granted" : ""]] as const;
  const passage = `The quick brown fox jumps over the lazy dog. I am teaching ${agent} my voice so that, when I work hands-free, it answers me and nobody else. My name is ` + (firstName || st.owner || "…") + ", and this is how I sound when I speak normally, not too fast and not too slow.";
  return (
    <>
      <Space state="idle" view="w-setup" />
      <div className="pointer-events-none fixed inset-0 bg-black/55" />
      <div className="relative z-10 mx-auto grid min-h-screen max-w-6xl gap-8 px-5 py-8 md:grid-cols-[240px_1fr] md:py-14">
        <aside className="hidden md:block">
          <div className="mb-8 flex items-center gap-2.5 text-xs font-medium uppercase tracking-[0.3em] text-white/60"><img src="/brand/mark.svg" alt="" className="h-6 w-6" />{agent} · setup</div>
          <ol className="grid gap-1">{STEPS.map((s, i) => { const Icon = s.icon; const on = i === step; return (
            <li key={s.key}><button onClick={() => { setMsg(null); setStep(i); }} className={cn("flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm transition", on ? "bg-white/10 text-white" : "text-white/55 hover:bg-white/[0.05] hover:text-white")}>
              <span className={cn("grid h-7 w-7 place-items-center rounded-full border", done[s.key] ? "border-emerald-300/40 bg-emerald-300/15 text-emerald-200" : on ? "border-white/40" : "border-white/15")}>{done[s.key] ? <Check className="h-3.5 w-3.5" /> : <Icon className="h-3.5 w-3.5" />}</span>{s.title}</button></li>); })}</ol>
        </aside>
        <section className="glass min-w-0 self-start rounded-3xl p-5 sm:p-9">{/* min-w-0: the step strip below scrolls instead of widening the card past the phone */}
          {/* on a phone the steps are a strip above the card (the side list is hidden); every step stays one tap away */}
          <div className="no-scrollbar mb-4 flex w-full max-w-full gap-2 overflow-x-auto md:hidden">{STEPS.map((s, i) => { const Icon = s.icon; const on = i === step; return (
            <button key={s.key} onClick={() => { setMsg(null); setStep(i); }} aria-current={on ? "step" : undefined} className={cn("flex h-9 shrink-0 items-center gap-1.5 rounded-full border px-3 text-[13px] transition", on ? "border-white bg-white text-black" : done[s.key] ? "border-emerald-300/40 bg-emerald-300/10 text-emerald-100" : "border-white/15 text-white/60")}>{done[s.key] && !on ? <Check className="h-3.5 w-3.5" /> : <Icon className="h-3.5 w-3.5" />}{s.title}</button>); })}</div>
          <div className="mb-1 text-xs font-medium uppercase tracking-[0.3em] text-sky-200/80">Step {step + 1} of {STEPS.length}</div>
          <AnimatePresence mode="wait">
            <motion.div key={k} initial={{ opacity: 0, x: 18 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -12 }} transition={{ duration: 0.45, ease }} className="grid gap-6">
              {k === "you" && (<>
                <div><h2 className="text-3xl font-semibold tracking-tight text-white">First, who does {agent} work for?</h2><p className="mt-2 text-white/60">{agent} greets you by your first name and knows you from everyone else by it.</p></div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="Your name" hint={`Your full name; the first word is how ${agent} says hello. The whole of it goes on anything written for other people.`}><Input className={input} value={you.owner_full} onChange={e => setYou({ ...you, owner_full: e.target.value })} placeholder="Alex Morgan" autoCapitalize="words" autoFocus /></Field>
                  <Field label={`What ${agent} calls you`} hint="Mid-conversation: &ldquo;Right away, sir.&rdquo;"><div className="flex flex-wrap gap-2">{["sir", "boss", "madam", firstName || "your name"].map(c => { const on = you.call === c || (c === firstName && (you.call === firstName || you.call === "your name")); return <button key={c} onClick={() => setYou({ ...you, call: c === firstName ? "your name" : c })} className={cn("rounded-full border px-3.5 py-1.5 text-sm transition", on ? "border-white bg-white text-black" : "border-white/20 text-white/75 hover:border-white/50")}>{c}</button>; })}</div></Field>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4 text-white/80"><div className="mb-1 text-xs uppercase tracking-[0.2em] text-white/45">You will hear</div>&ldquo;Hello {firstName || "…"}.&rdquo; &nbsp;…&nbsp; &ldquo;Right away, {you.call === "your name" ? (firstName || "…") : (you.call || "sir")}.&rdquo;</div>
                <div className="flex gap-3"><Button size="lg" className="rounded-full bg-white px-6 text-black hover:bg-white/90" disabled={busy} onClick={saveYou}>Continue<ArrowRight className="h-4 w-4" /></Button></div>
              </>)}
              {k === "mac" && (<>
                <div><h2 className="text-3xl font-semibold tracking-tight text-white">This Mac</h2><p className="mt-2 text-white/60">{agent} lives here. A few permissions let it hear, see and act; each one is yours to give.</p></div>
                {m && <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">{[["System", m.os], ["Browser", m.browser], ["Processor", `${m.cores} cores`], ["Graphics", m.gpu]].map(([l, v]) => <div key={l} className="rounded-xl border border-white/10 bg-white/[0.04] p-3"><div className="text-[10px] uppercase tracking-[0.2em] text-white/45">{l}</div><div className="mt-1 truncate text-sm text-white" title={String(v)}>{v}</div></div>)}</div>}
                <div className="grid gap-2">
                  <Row ok={checks.length ? checks.every(c => c.ok) : null} title="This browser can run the console" note={checks.filter(c => !c.ok).map(c => c.label).join(", ") || "sockets, audio, 3D, storage, notifications"} />
                  <Row ok={mic === "" ? false : mic === "ok"} title="Microphone" note={mic === "ok" ? "granted" : "so you can speak from the console too"} action={<Button size="sm" variant="outline" className="border-white/20 bg-transparent text-white hover:bg-white/10" onClick={testMic}><Mic className="h-4 w-4" />Test</Button>} />
                  <Row ok={cam === "" ? false : cam === "ok"} title="Camera" note={cam === "ok" ? "granted (it stays off until you ask)" : "optional: a look when you ask"} action={<Button size="sm" variant="outline" className="border-white/20 bg-transparent text-white hover:bg-white/10" onClick={testCam}><Eye className="h-4 w-4" />Allow</Button>} />
                  <Row ok={!!st.screen} title="Screen Recording (for Terminal)" note={st.screen ? `granted: ${agent} can read your screen when asked` : "System Settings › Privacy & Security › Screen Recording › Terminal, then reopen Terminal"} action={<Button size="sm" variant="ghost" className="text-white/70 hover:bg-white/10" onClick={refresh}>Check again</Button>} />
                  <Row ok={!!st.accessibility} title="Accessibility (for Terminal)" note={st.accessibility ? "granted: the cursor guard can read buttons" : "System Settings › Privacy & Security › Accessibility › Terminal"} />
                  <Row ok={ptt} title="The talk key (Input Monitoring)" note={heard ? `${agent} heard: “${heard}” (it answers once the setup is done)` : ptt ? "the key works: now say something while you hold it" : "hold Right Option and say something; if nothing happens, allow Terminal under Input Monitoring"} />
                </div>
                <div className="grid gap-2"><div className="text-xs font-medium uppercase tracking-[0.2em] text-white/55">Folders it may organise</div><div className="text-sm text-white/50">It moves, renames and tidies only inside these (and its own vault). It never deletes: anything bound for the Trash waits for you.</div>
                  <div className="flex flex-wrap gap-2">{(st.folder_candidates || []).map(r => { const on = (roots || []).includes(r); return <button key={r} onClick={() => toggleRoot(r)} className={cn("flex items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-sm transition", on ? "border-white bg-white text-black" : "border-white/20 text-white/75 hover:border-white/50")}>{on ? <Check className="h-3.5 w-3.5" /> : <FolderOpen className="h-3.5 w-3.5" />}{r.startsWith("/Volumes/") ? r.slice(9) + " (drive)" : r.replace(/^\/Users\/[^/]+\//, "")}</button>; })}</div></div>
                <div className="flex gap-3"><Button size="lg" className="rounded-full bg-white px-6 text-black hover:bg-white/90" onClick={saveMac}>Continue<ArrowRight className="h-4 w-4" /></Button></div>
              </>)}
              {k === "memory" && (<>
                <div><h2 className="text-3xl font-semibold tracking-tight text-white">A memory of its own</h2><p className="mt-2 text-white/60">{agent} keeps what it learns about you and your work in a vault: plain notes, in folders, that you can open in any editor. It fills it in with you, one conversation at a time.</p></div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <button disabled={busy} onClick={newVault} className="group rounded-2xl border border-white/15 bg-white/[0.05] p-5 text-left transition hover:border-white/40 hover:bg-white/[0.08]"><div className="text-xs uppercase tracking-[0.2em] text-sky-200/80">Recommended</div><div className="mt-2 text-lg font-medium text-white">Start a new vault</div><div className="mt-1 text-sm text-white/55">Inside {agent}&apos;s own data folder, git-backed. {agent} interviews you to fill it in.</div></button>
                  <div className="rounded-2xl border border-white/15 bg-white/[0.05] p-5"><div className="text-lg font-medium text-white">Use one I have</div><div className="mt-2 grid gap-2">{(st.vault_candidates || []).map(c => <button key={c} onClick={() => pickVault(c)} className="truncate rounded-lg border border-white/10 px-3 py-2 text-left text-sm text-white/80 hover:border-white/40" title={c}>{c.replace(/^\/Users\/[^/]+/, "~")}</button>)}<div className="flex gap-2"><Input className={cn(input, "h-9")} value={vaultPath} onChange={e => setVaultPath(e.target.value)} placeholder="/path/to/your vault" /><Button size="sm" variant="outline" className="border-white/20 bg-transparent text-white hover:bg-white/10" onClick={() => pickVault(vaultPath)}>Use</Button></div></div></div>
                </div>
                {st.vault_ready && <Note tone="ok">Vault: {st.vault}</Note>}
                <Field label="Nightly backups" hint={st.gh ? `Two private repos${st.backup_org ? ` in ${st.backup_org}` : ""}, written as ${st.github_account || "your GitHub account"}: the record here, the vault in troi-vault. Created on the first backup.` : `Sign in to GitHub first (gh auth login in a terminal); until then the backups stay on this Mac.`}><Input className={input} value={backupRepo} onChange={e => setBackupRepo(e.target.value)} placeholder={st.backup_repo || `${st.backup_org || st.github_account || "your-account"}/troi-of-silo-one-backups (default)`} /></Field>
                <div className="flex gap-3"><Button size="lg" className="rounded-full bg-white px-6 text-black hover:bg-white/90" disabled={!st.vault_ready} onClick={next}>Continue<ArrowRight className="h-4 w-4" /></Button></div>
              </>)}
              {k === "voice" && (<>
                <div><h2 className="text-3xl font-semibold tracking-tight text-white">A voice</h2><p className="mt-2 text-white/60">Kokoro speaks from this Mac, for free. ElevenLabs sounds more human, with your key; Kokoro takes over whenever ElevenLabs cannot answer.</p></div>
                <div className="grid gap-3 sm:grid-cols-2">{(["kokoro", "elevenlabs"] as const).map(e => <button key={e} onClick={() => setEngine(e)} className={cn("rounded-2xl border p-5 text-left transition", engine === e ? "border-white bg-white/[0.1]" : "border-white/15 bg-white/[0.04] hover:border-white/40")}><div className="text-lg font-medium text-white">{e === "kokoro" ? "Kokoro" : "ElevenLabs"}</div><div className="mt-1 text-sm text-white/55">{e === "kokoro" ? "Local, free, private. A warm British voice." : "Premium voices, including your own clone."}</div></button>)}</div>
                {engine === "elevenlabs" && <div className="grid gap-3">
                  {!st.secrets?.elevenlabs ? <div className="flex gap-2"><Input type="password" className={input} value={elKey} onChange={e => setElKey(e.target.value)} placeholder="ElevenLabs API key (elevenlabs.io › Profile › API keys)" /><Button className="h-11" onClick={async () => { if (await keepKey("elevenlabs", elKey, "Key kept in the Keychain.")) { setElKey(""); loadVoices(); } }}>Keep</Button></div> : <Note tone="ok">Your ElevenLabs key is in the Keychain.</Note>}
                  {st.secrets?.elevenlabs && <div className="flex gap-2"><Combobox className="flex-1" value={voice} options={voices.map(v => ({ value: v.voice_id, label: v.name, hint: typeof v.labels === "string" ? v.labels : Object.values(v.labels || {}).join(" · ") }))} loading={!voices.length} onOpen={() => !voices.length && loadVoices()} onChange={setVoice} placeholder={voices.length ? "Choose a voice…" : "Load your voices…"} empty="No voice by that name." /><Button variant="outline" className="h-11 border-white/20 bg-transparent text-white hover:bg-white/10" onClick={loadVoices}>Voices</Button></div>}
                </div>}
                <div className="flex flex-wrap gap-3"><Button size="lg" className="rounded-full bg-white px-6 text-black hover:bg-white/90" disabled={engine === "elevenlabs" && !voice} onClick={async () => { await saveVoice(); }}>Use this voice</Button><Button size="lg" variant="outline" className="rounded-full border-white/25 bg-transparent text-white hover:bg-white/10" onClick={testVoice}><Volume2 className="h-4 w-4" />Hear it</Button><Button size="lg" variant="ghost" className="rounded-full text-white/70 hover:bg-white/10" onClick={next}>Continue<ArrowRight className="h-4 w-4" /></Button></div>
              </>)}
              {k === "phone" && (<>
                <div><h2 className="text-3xl font-semibold tracking-tight text-white">Your phone</h2><p className="mt-2 text-white/60">Talk to {agent} from anywhere on Telegram: text, photos, voice notes. Approvals arrive there too, with a tap to answer.</p></div>
                {!tg?.token ? (<div className="grid gap-3">
                  <ol className="grid gap-2 text-sm text-white/70"><li>1. In Telegram, open <b className="text-white">@BotFather</b> and send <code className="rounded bg-white/10 px-1.5">/newbot</code>. Give it a name.</li><li>2. Paste the token it gives you here. It goes to the Keychain.</li></ol>
                  <div className="flex gap-2"><Input type="password" className={input} value={tgToken} onChange={e => setTgToken(e.target.value)} placeholder="123456789:AA…" /><Button className="h-11" onClick={saveTelegram}>Keep</Button></div>
                </div>) : tg?.paired ? <Note tone="ok">Your phone is paired{tg.bot ? " with @" + tg.bot : ""}. Say hello to it.</Note> : (
                  <div className="grid gap-3"><Note>Now send this code to {tg?.bot ? <b className="text-white">@{tg.bot}</b> : "your bot"} from your own Telegram account:</Note>
                    <div className="flex flex-wrap items-center gap-4"><div className="rounded-2xl border border-white/15 bg-white/[0.06] px-5 py-3 font-mono text-3xl tracking-[0.2em] text-white sm:px-6 sm:py-4 sm:text-4xl sm:tracking-[0.3em]">{tg?.code || "······"}</div><span className="flex items-center gap-2 text-sm text-white/50"><Loader2 className="h-5 w-5 animate-spin text-white/50" />waiting for your message…</span></div></div>)}
                <div className="flex gap-3"><Button size="lg" className="rounded-full bg-white px-6 text-black hover:bg-white/90" onClick={next}>{tg?.paired ? "Continue" : "Skip for now"}<ArrowRight className="h-4 w-4" /></Button></div>
              </>)}
              {k === "security" && (<>
                <div><h2 className="text-3xl font-semibold tracking-tight text-white">Only you</h2><p className="mt-2 text-white/60">A PIN approves anything protected: moving things to the Trash, turning the camera on, auto-approve, clearing the session. Your face can stand in for it, and your phone on Telegram.</p></div>
                {st.secrets?.pin && !unlocked ? (<div className="grid gap-3 sm:grid-cols-[1fr_auto]"><Input type="password" inputMode="numeric" className={input} value={pin} onChange={e => setPin(e.target.value)} placeholder="Your PIN" onKeyDown={e => e.key === "Enter" && unlock()} /><Button className="h-11" onClick={unlock}>Unlock</Button></div>) : !st.secrets?.pin ? (<div className="grid gap-3 sm:grid-cols-[1fr_1fr_auto]"><Input type="password" inputMode="numeric" className={input} value={pin} onChange={e => setPin(e.target.value)} placeholder="A PIN, 4 to 12 digits" /><Input type="password" inputMode="numeric" className={input} value={pin2} onChange={e => setPin2(e.target.value)} placeholder="Once more" /><Button className="h-11" onClick={savePin}>Set PIN</Button></div>) : <Note tone="ok">PIN set, and the console is unlocked for fifteen minutes.</Note>}
                <div className="grid gap-2">
                  <Row ok={faceMsg.startsWith("Your face") || false} title="Your face" note={faceMsg || (st.face_env === false ? "face ID is not installed on this Mac" : `five photos; ${agent} checks it's you before a protected change`)} action={<Button size="sm" variant="outline" className="border-white/20 bg-transparent text-white hover:bg-white/10" disabled={st.face_env === false} onClick={learnFace}>Learn my face</Button>} />
                  <Row ok={voiceMsg.startsWith("Your voice") || false} title="Your voice" note={voiceMsg || "about a minute of reading aloud; hands-free then answers only you"} action={<Button size="sm" variant="outline" className="border-white/20 bg-transparent text-white hover:bg-white/10" onClick={learnVoice}>Learn my voice</Button>} />
                  {voiceMsg && !voiceMsg.startsWith("Your voice") && <div className="rounded-xl border border-white/10 bg-white/[0.04] p-4 text-base leading-relaxed text-white/85">{passage}</div>}
                </div>
                <div className="flex gap-3"><Button size="lg" className="rounded-full bg-white px-6 text-black hover:bg-white/90" onClick={next}>{st.secrets?.pin ? "Continue" : "Skip for now"}<ArrowRight className="h-4 w-4" /></Button></div>
              </>)}
              {k === "extras" && (<>
                <div><h2 className="text-3xl font-semibold tracking-tight text-white">Extras</h2><p className="mt-2 text-white/60">All optional: add any of them now or later. Each key goes to the Keychain. The GitHub builds {agent} watches are set in Routines, once you are in.</p></div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="Pictures · OpenAI key" hint={`So ${agent} can make pictures from words.`}><Input type="password" className={input} value={ex.openai} onChange={e => setEx({ ...ex, openai: e.target.value })} placeholder={st.secrets?.openai ? "kept (leave empty to keep it)" : "sk-…"} /></Field>
                  <Field label="Pictures · Gemini key" hint="An alternative to OpenAI."><Input type="password" className={input} value={ex.gemini} onChange={e => setEx({ ...ex, gemini: e.target.value })} placeholder={st.secrets?.gemini ? "kept" : "AIza…"} /></Field>
                  <Field label="Phone calls · Agora app id" hint={`So ${agent} can call you.`}><Input className={input} value={ex.agoraId} onChange={e => setEx({ ...ex, agoraId: e.target.value })} placeholder={st.secrets?.["agora-appid"] ? "kept" : "app id"} /></Field>
                  <Field label="Phone calls · Agora certificate"><Input type="password" className={input} value={ex.agoraCert} onChange={e => setEx({ ...ex, agoraCert: e.target.value })} placeholder={st.secrets?.["agora-cert"] ? "kept" : "certificate"} /></Field>
                </div>
                <div className="flex gap-3"><Button size="lg" className="rounded-full bg-white px-6 text-black hover:bg-white/90" onClick={saveExtras}>Continue<ArrowRight className="h-4 w-4" /></Button></div>
              </>)}
              {k === "ready" && (<>
                <div><h2 className="text-4xl font-semibold tracking-tight text-white">{agent} is ready{(firstName || st.owner) ? `, ${firstName || st.owner}` : ""}.</h2><p className="mt-2 text-white/60">It will introduce itself. Anything you skipped lives in the console: Modes, Approvals, and the Keychain items under troi-of-silo-one.</p></div>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">{readyItems.map(([l, v]) => <div key={l} className={cn("rounded-2xl border p-4", v ? "border-emerald-300/25 bg-emerald-300/[0.07]" : "border-white/10 bg-white/[0.03]")}><div className="text-[10px] uppercase tracking-[0.2em] text-white/45">{l}</div><div className={cn("mt-1 text-sm", v ? "text-white" : "text-white/40")}>{v || "later"}</div></div>)}</div>
                <div><Button size="lg" className="group rounded-full bg-white px-8 text-black hover:bg-white/90" disabled={busy} onClick={finish}>Meet {agent}<ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" /></Button></div>
              </>)}
              {msg && <Note tone={msg.tone}>{msg.text}</Note>}
            </motion.div>
          </AnimatePresence>
        </section>
      </div>
      <AnimatePresence>{waking && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.9, ease }} className="fixed inset-0 z-50 grid place-items-center bg-black/80 backdrop-blur-sm">
          <div className="grid justify-items-center gap-6 text-center">
            <div className="relative h-24 w-24">{[0, 1, 2].map(i => <motion.span key={i} className="absolute inset-0 rounded-full border border-sky-200/50" animate={{ scale: [0.6, 1.8], opacity: [0.9, 0] }} transition={{ duration: 2.4, repeat: Infinity, delay: i * 0.8, ease: "easeOut" }} />)}<img src="/brand/mark.svg" alt="" className="absolute inset-3" /></div>
            <div className="text-2xl font-semibold tracking-tight text-white">{waking === "on" ? `${agent} is waking up` : "All set"}</div>
            <div className="max-w-sm text-white/60">{waking === "on" ? "with your name, your memory and your voice. It will introduce itself in a moment." : `Start ${agent} from the Desktop and it will introduce itself.`}</div>
          </div>
        </motion.div>)}</AnimatePresence>
    </>
  );
}

export default function Welcome() {
  const [phase, setPhase] = useState<"story" | "setup">("story");
  useEffect(() => { document.title = `Welcome · ${agentName()}`; try { if (new URLSearchParams(location.search).get("step") === "setup") setPhase("setup"); } catch {} }, []);
  const toSetup = useMemo(() => () => setPhase("setup"), []);
  return <div className="dark relative isolate min-h-screen text-white">{phase === "story" ? <Story onDone={toSetup} /> : <Setup />}</div>;
}
