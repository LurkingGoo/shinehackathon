/* Presentation helpers (pure, no data access). Safe for client + server. */
import type { Track } from "@/lib/types";

/** Status color for a risk value. Acute is always red. */
export function riskColor(risk: number, track: Track): string {
  if (track === "acute") return "var(--red)";
  if (risk >= 0.55) return "var(--sun)";
  if (risk >= 0.35) return "#a9791f";
  return "var(--sage)";
}

/** Short status word paired with color (color is never the only signal). */
export function trackWord(track: Track): string {
  return track === "acute" ? "ACUTE" : "CHRONIC";
}

const AV = ["--av-0", "--av-1", "--av-2", "--av-3", "--av-4", "--av-5"];

export function avatarColor(id: string, track: Track): string {
  if (track === "acute") return "var(--red)";
  let h = 0;
  for (const ch of id) h = (h * 31 + ch.charCodeAt(0)) % AV.length;
  return `var(${AV[h]})`;
}

export function initials(name: string): string {
  return name
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("");
}

export const pct = (x: number) => Math.round(x * 100);
