"use client";

import { useCallback, useState } from "react";
import { dataClient } from "@/lib/data/client";
import styles from "./hardware.module.css";

/**
 * Hardware companion page (B1). A presentation surface only: it shows the
 * reference wearable and calls the SAME simulate endpoint the dashboard's
 * Simulate button uses, via the same data seam. Nothing parallel is built;
 * the incident pins on the dashboard through the production SSE path.
 */
export function HardwarePanel() {
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");

  const stream = useCallback(async () => {
    setStatus("sending");
    try {
      // Same code path as the dashboard's Simulate button: dataClient.simulateIncident().
      await dataClient.simulateIncident();
      setStatus("sent");
    } catch {
      setStatus("error");
    }
  }, []);

  return (
    <div className={styles.app}>
      <header className={styles.top}>
        <div>
          <h1 className={styles.brandTitle}>The wrist end of the pipeline</h1>
          <p className={styles.brandSub}>
            Bangle.js 2, the open source wearable our sense layer is built on.
          </p>
        </div>
        <a className={styles.backLink} href="/">
          Open the triage dashboard &rarr;
        </a>
      </header>

      <section className={styles.renderPanel} aria-label="Bangle.js 2 to dashboard pipeline">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          className={styles.renderImg}
          src="/bangle-render.svg"
          alt="Bangle.js 2 wearable streaming accelerometer readings over Bluetooth LE to the fall detector, which pins an acute incident to the top of the triage dashboard"
        />
      </section>

      <section className={styles.card}>
        <h2 className={styles.cardTitle}>What we change on the stock Bangle.js 2</h2>
        <ul className={styles.adaptList}>
          <li className={styles.adaptItem}>
            <b>Sample rate.</b>
            <span>
              Raised from the shipped slow poll to the rate the detector needs. The chip
              supports up to 1600 Hz; we calibrate the exact rate at the pilot.
            </span>
          </li>
          <li className={styles.adaptItem}>
            <b>Ring buffer.</b>
            <span>
              A ring buffer on the wrist, so a Bluetooth dropout does not lose the fall.
            </span>
          </li>
          <li className={styles.adaptItem}>
            <b>Battery budget.</b>
            <span>
              Streaming costs battery: weeks of standby become days. We state that honestly
              and budget for it.
            </span>
          </li>
          <li className={styles.adaptItem}>
            <b>Shared format.</b>
            <span>
              The stream speaks the same reading format the Simulate button feeds, so
              everything downstream is unchanged by design.
            </span>
          </li>
        </ul>
      </section>

      <section className={styles.beat}>
        <div className={styles.beatText}>
          <b>The link beat.</b> This button sends a recorded fall through the same simulate
          endpoint the dashboard uses. The dashboard, open in another tab, pins the incident
          through the production path: same detector, same SSE stream.
          {status === "sent" && (
            <div className={styles.beatStatus}>
              Fall streamed. Watch the dashboard tab: the incident pins to the top.
            </div>
          )}
          {status === "error" && (
            <div className={`${styles.beatStatus} ${styles.beatError}`}>
              Could not reach the scoring service. Is the backend running?
            </div>
          )}
        </div>
        <button className={styles.btn} onClick={stream} disabled={status === "sending"}>
          {status === "sending" ? "Streaming..." : "Stream a recorded fall from this device"}
        </button>
      </section>

      <p className={styles.note}>
        Honesty note: the wearable link is simulated today, and it is the one simulated link
        in this demo. The detector, the scoring, and the dashboard pin are all live.
      </p>
    </div>
  );
}
