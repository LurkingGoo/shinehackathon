"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { AlertStatus, CaseloadEntry, ResidentDetail } from "@/lib/types";
import { dataClient } from "@/lib/data/client";
import {
  buildAckAnnouncement,
  buildFallAnnouncement,
  loadAudioEnabled,
  saveAudioEnabled,
  sirenElsewhere,
  speakAlert,
} from "@/lib/audio/alerts";
import { useRespeak } from "@/lib/audio/useRespeak";
import { CaseloadCard } from "./CaseloadCard";
import { DrilldownPanel } from "./DrilldownPanel";
import styles from "./dashboard.module.css";

/** Defensive re-sort: acute first, then chronic by risk desc. Never trust order blind. */
function rank(entries: CaseloadEntry[]): CaseloadEntry[] {
  const acute = entries.filter((e) => e.score.track === "acute");
  const chronic = entries
    .filter((e) => e.score.track !== "acute")
    .sort((a, b) => b.score.risk - a.score.risk);
  return [...acute, ...chronic].map((e, i) => ({ ...e, rank: i + 1 }));
}

export function Dashboard() {
  const [entries, setEntries] = useState<CaseloadEntry[]>([]);
  const [detail, setDetail] = useState<ResidentDetail | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [flashId, setFlashId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [nearMiss, setNearMiss] = useState<string | null>(null);
  const [alerts, setAlerts] = useState<AlertStatus | null>(null);
  const acuteRef = useRef<HTMLDivElement>(null);
  const nearMissTimer = useRef<ReturnType<typeof setTimeout>>();

  // Voice alerts (ADR 0015/0016) on the dashboard too — a Simulate incident
  // arrives over SSE, not through /watch, and must still sound. Same
  // persisted toggle as the watch station. Siren ownership: a live /watch
  // page heartbeats and owns the voice (its speakers are this machine's, even
  // from a hidden tab) — this page speaks only when no station is alive AND
  // its own tab is visible, so the two surfaces never talk over each other.
  const [audioOn, setAudioOn] = useState(true);
  const audioOnRef = useRef(audioOn);
  audioOnRef.current = audioOn;
  useEffect(() => setAudioOn(loadAudioEnabled()), []);
  const speakIfVisible = useCallback((text: string) => {
    if (audioOnRef.current && !document.hidden && !sirenElsewhere())
      speakAlert(text);
  }, []);
  const { startRespeak, stopRespeak } = useRespeak(speakIfVisible, setAlerts);

  // initial load — ALL data via dataClient, never fixtures/api directly
  useEffect(() => {
    dataClient
      .getRankedCaseload()
      .then((c) => setEntries(rank(c.entries)))
      .finally(() => setLoading(false));
    dataClient.getAlertStatus().then(setAlerts).catch(() => setAlerts(null));
  }, []);

  // Refresh the alert-leg outcome shortly after an incident arrives — the
  // Telegram dispatch resolves on a backend thread a beat behind the SSE event.
  const refreshAlerts = useCallback(() => {
    setTimeout(() => {
      dataClient.getAlertStatus().then(setAlerts).catch(() => undefined);
    }, 1500);
  }, []);

  // Acknowledgement arrives out-of-band (a caregiver taps the Telegram
  // button, ADR 0012) — poll so the badge reflects it within seconds.
  useEffect(() => {
    const id = setInterval(() => {
      dataClient.getAlertStatus().then(setAlerts).catch(() => undefined);
    }, 5000);
    return () => clearInterval(id);
  }, []);

  // Belt-and-braces resync (gap check 2026-07-29): the SSE stream has no
  // replay — an incident fired during a sleep/Wi-Fi blip is missed until
  // refresh. A periodic caseload refetch realigns within 30 s; idempotent,
  // rank() just recomputes from server truth.
  useEffect(() => {
    const id = setInterval(() => {
      dataClient
        .getRankedCaseload()
        .then((c) => setEntries(rank(c.entries)))
        .catch(() => undefined);
    }, 30_000);
    return () => clearInterval(id);
  }, []);

  // live incident channel (mock pub/sub now; SSE/WS later — same handler)
  useEffect(() => {
    return dataClient.subscribeToIncidents((event) => {
      setEntries((prev) => rank([event.entry, ...prev.filter((e) => e.id !== event.entry.id)]));
      setDetail(event.detail);
      setSelectedId(event.entry.id);
      setFlashId(event.entry.id);
      setTimeout(() => setFlashId(null), 1100);
      refreshAlerts();
      // Sound the alert here too (ADR 0016): the fix for Simulate incidents,
      // which never pass through /watch. Named from the event itself.
      const announcement = buildFallAnnouncement(event.entry.name, event.entry.zone);
      speakIfVisible(announcement);
      startRespeak(announcement);
      requestAnimationFrame(() =>
        acuteRef.current?.scrollIntoView({ behavior: "smooth", block: "center" })
      );
    });
  }, [refreshAlerts, speakIfVisible, startRespeak]);

  const select = useCallback(async (id: string) => {
    setSelectedId(id);
    setDetail(await dataClient.getResidentDetail(id));
  }, []);

  const simulate = useCallback(() => {
    void dataClient.simulateIncident();
  }, []);

  // Specificity demo: a dropped-phone impact that the detector correctly
  // ignores. No incident is marked — just a transient, non-alarming note.
  const simulateNearMiss = useCallback(async () => {
    const r = await dataClient.simulateNearMiss();
    setNearMiss(
      `✓ Checked — dropped phone, not a fall. Detector stayed silent (peak ${r.peakG}g).`,
    );
    clearTimeout(nearMissTimer.current);
    nearMissTimer.current = setTimeout(() => setNearMiss(null), 4000);
  }, []);

  useEffect(() => () => clearTimeout(nearMissTimer.current), []);

  // Demo reset: clear the incident server-side (it persists in /caseload with
  // a TTL), then re-pull the calm ranking so the beat can be re-run.
  const reset = useCallback(async () => {
    stopRespeak(); // the demo beat is over — no lingering voice loop
    await dataClient.clearIncident();
    const c = await dataClient.getRankedCaseload();
    setEntries(rank(c.entries));
    setDetail(null);
    setSelectedId(null);
  }, [stopRespeak]);

  // Stop alert (ADR 0016): the dashboard's own "I am responding". Acks the
  // active alert (first responder wins — a Telegram tap that landed first
  // keeps ownership) which also stops the watch station's voice loop. It
  // never touches the incident itself, so Simulate / Reset demo are unaffected.
  const ackAlert = useCallback(async () => {
    try {
      const ack = await dataClient.acknowledgeAlert("Dashboard");
      stopRespeak(); // silence immediately — do not wait for the next tick
      speakIfVisible(buildAckAnnouncement(ack.by));
    } catch {
      /* 404 = the incident just cleared under us — the poll realigns */
    }
    dataClient.getAlertStatus().then(setAlerts).catch(() => undefined);
  }, [stopRespeak, speakIfVisible]);

  // Alert-leg badge: configuration state, upgraded by the latest dispatch
  // outcome so the caregiver-ping leg is never silently unverifiable.
  const tgBadge = (() => {
    if (!alerts) return null;
    if (!alerts.telegram.configured)
      return { cls: styles.tgOff, label: "Telegram: not configured" };
    if (alerts.lastDispatch?.outcome === "failed")
      return { cls: styles.tgFail, label: "Telegram: send failed" };
    if (alerts.lastDispatch?.outcome === "sent")
      return { cls: styles.tgOn, label: "Telegram: alert sent" };
    return { cls: styles.tgOn, label: "Telegram: connected" };
  })();

  const acute = entries.filter((e) => e.score.track === "acute");
  const chronic = entries.filter((e) => e.score.track !== "acute");
  const needAttention = acute.length + chronic.filter((e) => e.score.risk >= 0.55).length;
  const hasAcute = acute.length > 0;

  return (
    <div className={styles.app}>
      <header className={styles.top}>
        <div>
          <h1 className={styles.brandTitle}>Good morning, Siti 🌤</h1>
          <p className={styles.brandSub}>
            Here&apos;s your caseload for today — the people who may need you first are at the top.
          </p>
        </div>
        <div className={styles.greet}>
          <div className={styles.greetHi}>Ang Mo Kio cluster</div>
          <div className={styles.greetSm}>Wed 1 Jul · 08:00</div>
          <nav className={styles.docNav}>
            <a className={styles.docLink} href="/judge-brief.html">
              Judge brief <span aria-hidden>→</span>
            </a>
            <a className={styles.docLink} href="/training">
              Model metrics <span aria-hidden>→</span>
            </a>
            <a className={styles.docLink} href="/watch">
              Camera watch <span aria-hidden>→</span>
            </a>
            <a className={styles.docLink} href="/slides.pdf" target="_blank" rel="noopener">
              Slides <span aria-hidden>↗</span>
            </a>
          </nav>
        </div>
      </header>

      <div className={styles.toolbar}>
        <div className={styles.toolbarMsg}>
          <b>{needAttention}</b> of <b>{entries.length}</b> residents could use a check today.
        </div>
        <div className={styles.toolbarRight}>
          {tgBadge && (
            <span
              className={`${styles.tgBadge} ${tgBadge.cls}`}
              title={
                alerts?.lastDispatch
                  ? `last dispatch: ${alerts.lastDispatch.outcome} · ${alerts.lastDispatch.at}`
                  : "no dispatch attempted yet"
              }
            >
              {tgBadge.label}
            </span>
          )}
          {alerts?.acknowledged && (
            <span
              className={`${styles.tgBadge} ${styles.tgOn}`}
              title={`acknowledged at ${alerts.acknowledged.at}`}
            >
              ✓ {alerts.acknowledged.by} responding
            </span>
          )}
          <span className={styles.live}>
            <span className={styles.pulse} />
            Live · replaying data
          </span>
          <button
            className={`${styles.btn} ${styles.btnCalm}`}
            onClick={() => {
              setAudioOn((on) => {
                saveAudioEnabled(!on);
                return !on;
              });
            }}
            aria-pressed={audioOn}
            title="Voice alerts on this screen (shared with the camera watch page)"
          >
            {audioOn ? "🔊" : "🔇"}
          </button>
          {hasAcute && alerts && !alerts.acknowledged && (
            <button className={`${styles.btn} ${styles.btnCalm}`} onClick={() => void ackAlert()}>
              🔕 I am responding — stop alert
            </button>
          )}
          {!hasAcute && (
            <button className={`${styles.btn} ${styles.btnCalm}`} onClick={simulateNearMiss}>
              Simulate near-miss
            </button>
          )}
          <button className={styles.btn} onClick={hasAcute ? reset : simulate}>
            {hasAcute ? "Reset demo" : "Simulate incident"}
          </button>
        </div>
      </div>

      {nearMiss && (
        <div className={styles.calmBanner} role="status">
          {nearMiss}
        </div>
      )}

      <div className={styles.grid}>
        <div>
          {hasAcute && (
            <div className={`${styles.band} ${styles.bandAcute}`}>
              🚨 Someone needs help right now
            </div>
          )}
          <div ref={acuteRef}>
            {acute.map((e) => (
              <CaseloadCard
                key={e.id}
                entry={e}
                selected={selectedId === e.id}
                flash={flashId === e.id}
                onSelect={select}
              />
            ))}
          </div>

          <div className={styles.band}>Today&apos;s caseload · most concern first</div>
          {loading ? (
            <div className={styles.empty}>Loading caseload…</div>
          ) : (
            chronic.map((e) => (
              <CaseloadCard
                key={e.id}
                entry={e}
                selected={selectedId === e.id}
                onSelect={select}
              />
            ))
          )}

          <div className={styles.foot}>
            Every reason shown is drawn straight from the sensors — plain words, no guesswork.
          </div>
        </div>

        <aside>
          <DrilldownPanel detail={detail} />
        </aside>
      </div>
    </div>
  );
}
