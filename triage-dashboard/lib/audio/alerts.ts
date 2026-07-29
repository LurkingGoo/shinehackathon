/**
 * On-device audio alerts (ADR 0015). Web Speech API voices + a WebAudio
 * attention chime — no network, no audio assets, no dependency: the call-out
 * must work on the offline demo laptop. It speaks at the watch station (the
 * machine that saw the fall), which is also where anyone in earshot is.
 */

const PHRASE = "Patient has fallen!";

/** The mandated call-out, twice, then whatever identity + zone the Telegram
 * alert carries — a bystander hears the same facts the caregiver is pinged. */
export function buildFallAnnouncement(
  name?: string | null,
  zone?: string | null,
): string {
  const context = name ? ` ${name}${zone ? `, ${zone}` : ""}.` : "";
  return `${PHRASE} ${PHRASE}${context}`;
}

/** Long-lie escalation (ADR 0012) gets a sharper spoken line. */
export function buildStillDownAnnouncement(name?: string | null): string {
  return `${name ?? "The patient"} is still down! Please respond now.`;
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
