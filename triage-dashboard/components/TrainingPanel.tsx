"use client";

import { useEffect, useMemo, useState } from "react";
import type { TrainingStats } from "@/lib/types";
import { dataClient } from "@/lib/data/client";
import styles from "./training.module.css";

/**
 * The judge-metrics page: how the illustrative classifier was trained, shown
 * with REAL numbers only. Every chart reads the deterministic payload from
 * /api/training-stats — the recorded gradient-descent run, real re-fits at
 * three train/test splits, real held-out confusion matrices. The page's whole
 * argument: magnitude features cap near 80%, which is WHY the shipped detector
 * encodes the temporal fall signature instead (96.2%, calibrate.py).
 */

/** Shipped-detector headline (data/metrics.json via scripts/calibrate.py). */
const DETECTOR_PCT = 96.2;

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

/* ---------------------------------------------------------------- charts -- */

interface Pt {
  x: number;
  y: number;
  label: string;
}

/** One thin-line chart with a nearest-point hover tooltip. Single series —
 * the title names it, so no legend box (identity is never color-alone). */
function LineChart({
  points,
  color,
  yFmt,
  xTitle,
  ariaLabel,
  yDomain,
}: {
  points: Pt[];
  color: string;
  yFmt: (v: number) => string;
  xTitle: string;
  ariaLabel: string;
  /** Explicit y-range. Without it the axis hugs the data — fine for a loss
   * curve, but a near-flat series would have its noise zoom-exaggerated. */
  yDomain?: [number, number];
}) {
  const [hover, setHover] = useState<number | null>(null);
  const W = 340;
  const H = 150;
  const PAD = { l: 44, r: 10, t: 10, b: 26 };

  const xs = points.map((p) => p.x);
  const ys = points.map((p) => p.y);
  const x0 = Math.min(...xs);
  const x1 = Math.max(...xs);
  const yMin = yDomain ? yDomain[0] : Math.min(...ys);
  const yMax = yDomain ? yDomain[1] : Math.max(...ys);
  const yPad = yDomain ? 0 : (yMax - yMin || 1) * 0.08;
  const y0 = yMin - yPad;
  const y1 = yMax + yPad;

  const X = (v: number) => PAD.l + ((v - x0) / (x1 - x0 || 1)) * (W - PAD.l - PAD.r);
  const Y = (v: number) => H - PAD.b - ((v - y0) / (y1 - y0)) * (H - PAD.t - PAD.b);

  const path = points.map((p, i) => `${i ? "L" : "M"}${X(p.x).toFixed(1)},${Y(p.y).toFixed(1)}`).join(" ");
  const gridY = [y0 + (y1 - y0) * 0.25, y0 + (y1 - y0) * 0.5, y0 + (y1 - y0) * 0.75];

  const onMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const mx = ((e.clientX - rect.left) / rect.width) * W;
    let best = 0;
    let bestD = Infinity;
    points.forEach((p, i) => {
      const d = Math.abs(X(p.x) - mx);
      if (d < bestD) {
        bestD = d;
        best = i;
      }
    });
    setHover(best);
  };

  const h = hover === null ? null : points[hover];

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className={styles.chartSvg}
      role="img"
      aria-label={ariaLabel}
      onMouseMove={onMove}
      onMouseLeave={() => setHover(null)}
    >
      {gridY.map((g) => (
        <line key={g} x1={PAD.l} y1={Y(g)} x2={W - PAD.r} y2={Y(g)} className={styles.grid} />
      ))}
      {/* y-axis value labels: min + max only (recessive axes) */}
      <text x={PAD.l - 6} y={Y(yMax) + 4} textAnchor="end" className={styles.axisText}>
        {yFmt(yMax)}
      </text>
      <text x={PAD.l - 6} y={Y(yMin) + 4} textAnchor="end" className={styles.axisText}>
        {yFmt(yMin)}
      </text>
      <text x={(PAD.l + W - PAD.r) / 2} y={H - 6} textAnchor="middle" className={styles.axisText}>
        {xTitle}
      </text>
      <path d={path} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
      {/* end-of-line direct label (selective, not every point) */}
      <circle cx={X(points[points.length - 1].x)} cy={Y(points[points.length - 1].y)} r="3.5" fill={color} />
      {h && (
        <g>
          <line x1={X(h.x)} y1={PAD.t} x2={X(h.x)} y2={H - PAD.b} className={styles.crosshair} />
          <circle cx={X(h.x)} cy={Y(h.y)} r="4.5" fill={color} stroke="var(--panel)" strokeWidth="2" />
          <g transform={`translate(${Math.min(X(h.x) + 8, W - 120)}, ${PAD.t + 2})`}>
            <rect width="112" height="34" rx="8" className={styles.tipBox} />
            <text x="8" y="14" className={styles.tipTitle}>{h.label}</text>
            <text x="8" y="28" className={styles.tipValue}>{yFmt(h.y)}</text>
          </g>
        </g>
      )}
    </svg>
  );
}

/* ----------------------------------------------------------------- panel -- */

export function TrainingPanel() {
  const [stats, setStats] = useState<TrainingStats | null>(null);
  const [error, setError] = useState(false);
  const [splitIdx, setSplitIdx] = useState(1); // default 70/30, the middle control

  useEffect(() => {
    dataClient.getTrainingStats().then(setStats).catch(() => setError(true));
  }, []);

  const maxCoef = useMemo(
    () => (stats ? Math.max(...stats.coefficients.map(Math.abs), 1e-9) : 1),
    [stats],
  );

  if (error) {
    return (
      <main className={styles.page}>
        <p className={styles.loading}>Training metrics unavailable — is the scoring service up?</p>
      </main>
    );
  }
  if (!stats) {
    return (
      <main className={styles.page}>
        <p className={styles.loading}>Loading training metrics…</p>
      </main>
    );
  }

  const split = stats.splitSensitivity[splitIdx] ?? stats.splitSensitivity[0];
  const cm = split.confusionMatrix;
  const gap = DETECTOR_PCT - stats.accuracy * 100;

  return (
    <main className={styles.page}>
      <header className={styles.head}>
        <a className={styles.back} href="/">
          <span aria-hidden>←</span> Back to dashboard
        </a>
        <h1 className={styles.title}>How the model was trained</h1>
        <p className={styles.sub}>
          We trained a small logistic regression on {stats.counts.total} real SisFall
          recordings, using four magnitude features: peak impact, free-fall depth,
          impact energy, and post-impact stillness. Everything below is measured from
          that run. It converges near {pct(stats.accuracy)}, and that ceiling is the
          reason the shipped detector reads the temporal fall signature instead.
        </p>
      </header>

      {/* headline tiles — the gap IS the story */}
      <section className={styles.tiles} aria-label="Headline comparison">
        <div className={styles.tile}>
          <div className={styles.tileValue}>{pct(stats.accuracy)}</div>
          <div className={styles.tileLabel}>magnitude-only classifier, held-out test accuracy</div>
        </div>
        <div className={styles.tile}>
          <div className={styles.tileValue}>{DETECTOR_PCT}%</div>
          <div className={styles.tileLabel}>shipped ordered-signature detector, fall detection</div>
        </div>
        <div className={`${styles.tile} ${styles.tileBrand}`}>
          <div className={styles.tileValue}>+{gap.toFixed(1)} pts</div>
          <div className={styles.tileLabel}>
            what encoding free-fall → impact → stillness ORDER adds over magnitudes
          </div>
        </div>
      </section>

      <p className={styles.note}>{stats.$note}</p>

      {/* real GD convergence — two measures, two charts (never a dual axis) */}
      <section className={styles.card}>
        <h2 className={styles.sec}>The training run, as recorded</h2>
        <p className={styles.secSub}>
          Log-loss and held-out accuracy sampled every 100 iterations of the actual
          gradient-descent run. The accuracy curve flattens near {pct(stats.accuracy)}:
          more training does not break the magnitude ceiling.
        </p>
        <div className={styles.chartRow}>
          <figure className={styles.fig}>
            <figcaption className={styles.figCap}>Training loss (log-loss)</figcaption>
            <LineChart
              points={stats.convergence.map((c) => ({ x: c.iter, y: c.loss, label: `iteration ${c.iter}` }))}
              color="var(--brand)"
              yFmt={(v) => v.toFixed(3)}
              xTitle="gradient-descent iteration"
              ariaLabel="Training log-loss decreasing over gradient-descent iterations"
            />
          </figure>
          <figure className={styles.fig}>
            <figcaption className={styles.figCap}>Held-out test accuracy</figcaption>
            <LineChart
              points={stats.convergence.map((c) => ({ x: c.iter, y: c.testAccuracy, label: `iteration ${c.iter}` }))}
              color="var(--chart-teal)"
              yFmt={pct}
              xTitle="gradient-descent iteration"
              ariaLabel="Held-out accuracy converging to the magnitude ceiling"
            />
          </figure>
        </div>
      </section>

      {/* split controls — three REAL re-fits */}
      <section className={styles.card}>
        <h2 className={styles.sec}>Does the split change the story?</h2>
        <p className={styles.secSub}>
          Each control re-fits the model at that train/test split (same deterministic
          ordering, real held-out confusion matrix). The ceiling holds at every split.
        </p>
        <div className={styles.splitRow} role="tablist" aria-label="Train/test split">
          {stats.splitSensitivity.map((s, i) => (
            <button
              key={s.split}
              role="tab"
              aria-selected={i === splitIdx}
              className={i === splitIdx ? styles.splitBtnOn : styles.splitBtn}
              onClick={() => setSplitIdx(i)}
            >
              {s.split}
              <span className={styles.splitBtnSub}>{pct(s.accuracy)}</span>
            </button>
          ))}
        </div>
        <div className={styles.splitBody}>
          <div className={styles.matrix} role="table" aria-label={`Confusion matrix, ${split.split} split`}>
            <div className={styles.mCorner} />
            <div className={styles.mHead}>predicted fall</div>
            <div className={styles.mHead}>predicted ADL</div>
            <div className={styles.mHead}>actual fall</div>
            <div className={`${styles.mCell} ${styles.mGood}`}>
              <b>{cm.tp}</b> caught
            </div>
            <div className={`${styles.mCell} ${styles.mBad}`}>
              <b>{cm.fn}</b> missed
            </div>
            <div className={styles.mHead}>actual ADL</div>
            <div className={`${styles.mCell} ${styles.mBad}`}>
              <b>{cm.fp}</b> false alarm
            </div>
            <div className={`${styles.mCell} ${styles.mGood}`}>
              <b>{cm.tn}</b> correct calm
            </div>
          </div>
          <dl className={styles.splitStats}>
            <div>
              <dt>Accuracy</dt>
              <dd>{pct(split.accuracy)}</dd>
            </div>
            <div>
              <dt>Recall (sensitivity)</dt>
              <dd>{pct(split.recall)}</dd>
            </div>
            <div>
              <dt>Precision</dt>
              <dd>{pct(split.precision)}</dd>
            </div>
            <div>
              <dt>Train / test</dt>
              <dd>
                {split.counts.train} / {split.counts.test}
              </dd>
            </div>
          </dl>
        </div>
      </section>

      {/* learning curve */}
      <section className={styles.card}>
        <h2 className={styles.sec}>More data does not fix it</h2>
        <p className={styles.secSub}>
          Test accuracy as the training set grows (real re-fits on growing prefixes).
          The curve saturates: the limit is the features, not the data volume.
        </p>
        <figure className={styles.fig}>
          <figcaption className={styles.figCap}>Held-out accuracy vs training size</figcaption>
          <LineChart
            points={stats.learningCurve.map((p) => ({ x: p.trainSize, y: p.accuracy, label: `${p.trainSize} samples` }))}
            color="var(--chart-teal)"
            yFmt={pct}
            xTitle="training samples"
            ariaLabel="Learning curve saturating as training size grows"
            yDomain={[0.5, 0.9]}
          />
        </figure>
      </section>

      {/* coefficients — diverging bars around zero */}
      <section className={styles.card}>
        <h2 className={styles.sec}>What the model learned to weigh</h2>
        <p className={styles.secSub}>
          Standardised coefficients: bars to the right push a recording toward
          &ldquo;fall&rdquo;, bars to the left toward &ldquo;normal activity&rdquo;. The words carry
          the direction, so the colors are reinforcement, not the only signal.
        </p>
        <div className={styles.coefs}>
          {stats.featureNames.map((name, i) => {
            const c = stats.coefficients[i];
            const w = (Math.abs(c) / maxCoef) * 50; // % of half-track
            return (
              <div key={name} className={styles.coefRow} title={`${name}: ${c.toFixed(3)}`}>
                <span className={styles.coefName}>{name}</span>
                <div className={styles.coefTrack}>
                  <span className={styles.coefZero} />
                  <span
                    className={c >= 0 ? styles.coefPos : styles.coefNeg}
                    style={c >= 0 ? { left: "50%", width: `${w}%` } : { right: "50%", width: `${w}%` }}
                  />
                </div>
                <span className={styles.coefVal}>
                  {c >= 0 ? "→ fall " : "→ ADL "}
                  {c.toFixed(2)}
                </span>
              </div>
            );
          })}
        </div>
      </section>

      {/* accessibility: the same numbers as a table */}
      <details className={styles.tableWrap}>
        <summary>View the recorded run as a table</summary>
        <table className={styles.table}>
          <thead>
            <tr>
              <th scope="col">Iteration</th>
              <th scope="col">Log-loss</th>
              <th scope="col">Test accuracy</th>
            </tr>
          </thead>
          <tbody>
            {stats.convergence.map((c) => (
              <tr key={c.iter}>
                <td>{c.iter}</td>
                <td>{c.loss.toFixed(4)}</td>
                <td>{pct(c.testAccuracy)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </main>
  );
}
