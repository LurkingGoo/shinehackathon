"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { CaseloadEntry, ResidentDetail } from "@/lib/types";
import { dataClient } from "@/lib/data/client";
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
  const acuteRef = useRef<HTMLDivElement>(null);

  // initial load — ALL data via dataClient, never fixtures/api directly
  useEffect(() => {
    dataClient
      .getRankedCaseload()
      .then((c) => setEntries(rank(c.entries)))
      .finally(() => setLoading(false));
  }, []);

  // live incident channel (mock pub/sub now; SSE/WS later — same handler)
  useEffect(() => {
    return dataClient.subscribeToIncidents((event) => {
      setEntries((prev) => rank([event.entry, ...prev.filter((e) => e.id !== event.entry.id)]));
      setDetail(event.detail);
      setSelectedId(event.entry.id);
      setFlashId(event.entry.id);
      setTimeout(() => setFlashId(null), 1100);
      requestAnimationFrame(() =>
        acuteRef.current?.scrollIntoView({ behavior: "smooth", block: "center" })
      );
    });
  }, []);

  const select = useCallback(async (id: string) => {
    setSelectedId(id);
    setDetail(await dataClient.getResidentDetail(id));
  }, []);

  const simulate = useCallback(() => {
    void dataClient.simulateIncident();
  }, []);

  // Demo reset: clear the incident server-side (it persists in /caseload with
  // a TTL), then re-pull the calm ranking so the beat can be re-run.
  const reset = useCallback(async () => {
    await dataClient.clearIncident();
    const c = await dataClient.getRankedCaseload();
    setEntries(rank(c.entries));
    setDetail(null);
    setSelectedId(null);
  }, []);

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
        </div>
      </header>

      <div className={styles.toolbar}>
        <div className={styles.toolbarMsg}>
          <b>{needAttention}</b> of <b>{entries.length}</b> residents could use a check today.
        </div>
        <div className={styles.toolbarRight}>
          <span className={styles.live}>
            <span className={styles.pulse} />
            Live · replaying data
          </span>
          <button className={styles.btn} onClick={hasAcute ? reset : simulate}>
            {hasAcute ? "Reset demo" : "Simulate incident"}
          </button>
        </div>
      </div>

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
