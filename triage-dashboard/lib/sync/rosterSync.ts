/**
 * Cross-tab roster sync (gap check 2026-07-30). A register / location save /
 * delete on /watch must reach an already-open dashboard tab NOW, not on its
 * 30 s belt-and-braces poll — a caseworker watching the screen should never
 * see a deleted resident linger. Carries NO data: it is a pure "refetch your
 * caseload" nudge, so server truth stays the single source and a lost or
 * duplicated message costs nothing (refetch is idempotent).
 *
 * BroadcastChannel reaches every same-origin tab; where it is unavailable
 * (old WebKit) the localStorage bump reaches other tabs via the storage
 * event. Both paths are fire-and-forget and safe under SSR (no window).
 */

const CHANNEL = "shine-roster-sync";
const LS_KEY = "shine-roster-sync-v1";

export function announceRosterChange(): void {
  if (typeof window === "undefined") return;
  try {
    if (typeof BroadcastChannel !== "undefined") {
      const ch = new BroadcastChannel(CHANNEL);
      ch.postMessage("changed");
      ch.close();
    }
  } catch {
    /* sync is best-effort — the 30 s poll remains the backstop */
  }
  try {
    window.localStorage.setItem(LS_KEY, String(Date.now()));
  } catch {
    /* storage full/blocked — same backstop */
  }
}

/** Subscribe to roster-change nudges from OTHER tabs. Returns unsubscribe. */
export function onRosterChange(cb: () => void): () => void {
  if (typeof window === "undefined") return () => undefined;
  let ch: BroadcastChannel | null = null;
  try {
    if (typeof BroadcastChannel !== "undefined") {
      ch = new BroadcastChannel(CHANNEL);
      ch.onmessage = () => cb();
    }
  } catch {
    ch = null;
  }
  const onStorage = (e: StorageEvent) => {
    if (e.key === LS_KEY) cb();
  };
  window.addEventListener("storage", onStorage);
  return () => {
    try {
      ch?.close();
    } catch {
      /* already closed */
    }
    window.removeEventListener("storage", onStorage);
  };
}
