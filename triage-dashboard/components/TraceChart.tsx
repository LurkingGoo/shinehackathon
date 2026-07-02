"use client";

import { useEffect, useState } from "react";
import type { IncidentTrace } from "@/lib/types";
import { dataClient } from "@/lib/data/client";
import styles from "./dashboard.module.css";

/**
 * The signal behind the incident — the drilldown's "what the sensor saw"
 * panel. Renders the replayed accelerometer window with the three detected
 * phases banded, so the ordered fall signature (dip → spike → stillness) is
 * visible instead of asserted. Only mounted for acute drilldowns; renders
 * nothing while the caseload is calm (the endpoint 404s).
 */
export function TraceChart() {
  const [trace, setTrace] = useState<IncidentTrace | null>(null);

  useEffect(() => {
    let alive = true;
    dataClient
      .getIncidentTrace()
      .then((t) => {
        if (alive) setTrace(t);
      })
      .catch(() => {}); // missing trace must never break the drilldown
    return () => {
      alive = false;
    };
  }, []);

  if (!trace || trace.samples.length < 2) return null;

  const W = 320;
  const H = 110;
  const PAD = 8;
  const duration = trace.samples.length * trace.dtS;
  const gMax = Math.max(trace.peakG * 1.12, 3);
  const x = (t: number) => PAD + (t / duration) * (W - 2 * PAD);
  const y = (g: number) => H - PAD - (Math.min(g, gMax) / gMax) * (H - 2 * PAD);

  const points = trace.samples
    .map((g, i) => `${x(i * trace.dtS).toFixed(1)},${y(g).toFixed(1)}`)
    .join(" ");
  const [ffStart, ffEnd] = trace.phases.freefall;

  return (
    <>
      <h4 className={styles.sec}>What the sensor saw</h4>
      <div className={styles.trace}>
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className={styles.traceSvg}
          role="img"
          aria-label={`Accelerometer trace: free-fall dip, ${trace.peakG.toFixed(1)} g impact, then stillness`}
        >
          {/* phase bands — the ordered signature, visible */}
          <rect x={x(ffStart)} y={PAD} width={Math.max(3, x(ffEnd) - x(ffStart))}
                height={H - 2 * PAD} fill="var(--sun-soft)" />
          <rect x={x(trace.phases.stillFromS)} y={PAD}
                width={W - PAD - x(trace.phases.stillFromS)} height={H - 2 * PAD}
                fill="var(--sage-soft)" />
          <line x1={x(trace.phases.impactS)} y1={PAD} x2={x(trace.phases.impactS)}
                y2={H - PAD} stroke="var(--red)" strokeWidth="1" strokeDasharray="3 2" />

          {/* rest reference at 1 g */}
          <line x1={PAD} y1={y(1)} x2={W - PAD} y2={y(1)}
                stroke="var(--line)" strokeWidth="1" />

          <polyline points={points} fill="none" stroke="var(--red)"
                    strokeWidth="1.6" strokeLinejoin="round" />

          {/* labels ride the top of their bands — the trace hugs the bottom
              because the impact peak sets the y-scale */}
          <text x={x(ffStart) - 4} y={PAD + 10} textAnchor="end"
                className={styles.traceLabel} fill="var(--sun)">free-fall</text>
          <text x={x(trace.phases.impactS) + 6} y={y(trace.peakG) + 10}
                className={styles.traceLabel} fill="var(--red)">
            impact {trace.peakG.toFixed(1)} g
          </text>
          <text x={x(trace.phases.stillFromS) + (W - PAD - x(trace.phases.stillFromS)) / 2}
                y={PAD + 10} textAnchor="middle" className={styles.traceLabel}
                fill="var(--sage)">no movement</text>
        </svg>
        <div className={styles.traceCaption}>
          Replayed real recording · the detector requires this exact order —
          free-fall, impact, stillness
        </div>
      </div>
    </>
  );
}
