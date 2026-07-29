/**
 * On-device audio alerts (ADR 0015). Web Speech API voices + a WebAudio
 * attention chime — no network, no audio assets, no dependency: the call-out
 * must work on the offline demo laptop. It speaks at the watch station (the
 * machine that saw the fall), which is also where anyone in earshot is.
 */

/** The call-out, twice, carrying the same identity + zone facts as the
 * Telegram alert: "Patient <name> has fallen at <zone>!" — name and zone
 * degrade gracefully when unknown (fail-open, never blocks the alert). */
export function buildFallAnnouncement(
  name?: string | null,
  zone?: string | null,
): string {
  const phrase = `Patient${name ? ` ${name}` : ""} has fallen${
    zone ? ` at ${zone}` : ""
  }!`;
  return `${phrase} ${phrase}`;
}

/** Long-lie escalation (ADR 0012) gets a sharper spoken line. */
export function buildStillDownAnnouncement(name?: string | null): string {
  return `${name ?? "The patient"} is still down! Please respond now.`;
}

/** Spoken once when the re-speak loop sees the ack land (ADR 0016). */
export function buildAckAnnouncement(by: string): string {
  return `Alert acknowledged. ${by} is responding.`;
}

/* --------------------- re-speak until acknowledged ------------------------ */
export const RESPEAK_INTERVAL_MS = 20_000;
/** ≈5 minutes of repeats — anything longer is the escalation path's job. */
export const MAX_RESPEAKS = 15;

export type RespeakAction = "speak" | "announce-ack" | "stop";

/** One tick of the re-speak loop (ADR 0016), pure so every branch is
 * testable: ack wins (announce it, once), a cleared incident or the repeat
 * cap stops silently, otherwise speak again. */
export function respeakDecision(s: {
  acknowledged: boolean;
  acuteActive: boolean;
  repeats: number;
}): RespeakAction {
  if (s.acknowledged) return "announce-ack";
  if (!s.acuteActive || s.repeats >= MAX_RESPEAKS) return "stop";
  return "speak";
}

/* --------------- siren ownership: watch station vs dashboard -------------- */
// Both pages hear every incident over SSE; exactly one should voice it. The
// /watch page (the room station) heartbeats while mounted; the dashboard
// yields whenever a fresh heartbeat exists — even if the watch tab is hidden,
// its speakers are the same machine's and it will speak.
const SIREN_KEY = "watch-siren-heartbeat-v1";
export const SIREN_TTL_MS = 3000;

/** Pure freshness predicate for the heartbeat value (unit-tested). */
export function heartbeatFresh(
  raw: string | null,
  now: number,
  ttl: number = SIREN_TTL_MS,
): boolean {
  const ts = raw ? Number(raw) : NaN;
  return Number.isFinite(ts) && now - ts >= 0 && now - ts < ttl;
}

/** The watch page calls this every second while mounted. */
export function markSirenAlive(): void {
  try {
    window.localStorage.setItem(SIREN_KEY, String(Date.now()));
  } catch {
    /* storage unavailable — the dashboard will speak instead */
  }
}

/** True when a live watch station owns the siren (dashboard yields). */
export function sirenElsewhere(): boolean {
  try {
    return heartbeatFresh(window.localStorage.getItem(SIREN_KEY), Date.now());
  } catch {
    return false;
  }
}

/* ------------------------- enabled flag (persisted) ----------------------- */
const KEY = "watch-audio-alerts-v1";

export function loadAudioEnabled(): boolean {
  try {
    return window.localStorage.getItem(KEY) !== "0"; // default ON
  } catch {
    return true;
  }
}

export function saveAudioEnabled(on: boolean): void {
  try {
    window.localStorage.setItem(KEY, on ? "1" : "0");
  } catch {
    /* storage unavailable — the in-memory toggle still works */
  }
}

/* ------------------------------ playback ---------------------------------- */
let ctx: AudioContext | null = null;

/** Two rising tones before the speech — grabs attention faster than a voice
 * onset. Best-effort: any audio failure must never break the alert path. */
function chime(): void {
  try {
    const AC =
      window.AudioContext ??
      (window as unknown as { webkitAudioContext?: typeof AudioContext })
        .webkitAudioContext;
    if (!AC) return;
    ctx ??= new AC();
    void ctx.resume();
    const t = ctx.currentTime;
    for (const [freq, at] of [
      [880, 0],
      [1175, 0.18],
    ] as const) {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.frequency.value = freq;
      osc.connect(gain).connect(ctx.destination);
      gain.gain.setValueAtTime(0.0001, t + at);
      gain.gain.exponentialRampToValueAtTime(0.4, t + at + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, t + at + 0.35);
      osc.start(t + at);
      osc.stop(t + at + 0.4);
    }
  } catch {
    /* best-effort */
  }
}

/** Chime, then speak. A newer emergency supersedes anything still queued. */
export function speakAlert(text: string): void {
  if (typeof window === "undefined") return;
  chime();
  const synth = window.speechSynthesis;
  if (!synth) return;
  try {
    synth.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 1.05;
    u.volume = 1;
    synth.speak(u);
  } catch {
    /* best-effort */
  }
}
