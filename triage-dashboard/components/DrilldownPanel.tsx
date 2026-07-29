import type { ResidentDetail } from "@/lib/types";
import { avatarColor, initials, pct, riskColor } from "@/lib/ui";
import { ReplayPlayer } from "./ReplayPlayer";
import { TraceChart } from "./TraceChart";
import styles from "./dashboard.module.css";

export function DrilldownPanel({ detail }: { detail: ResidentDetail | null }) {
  if (!detail) {
    return (
      <div className={styles.panel}>
        <div className={styles.empty}>
          <span className={styles.emptyEm}>👋</span>
          Tap a resident to see how they&apos;re doing and what to do next.
        </div>
      </div>
    );
  }

  const { score } = detail;
  const acute = score.track === "acute";
  const color = riskColor(score.risk, score.track);

  return (
    <div className={styles.panel}>
      <div className={styles.ph}>
        <div
          className={styles.avatar}
          style={{ background: avatarColor(detail.id, score.track) }}
        >
          {initials(detail.name)}
        </div>
        <div>
          <h3 className={styles.panelTitle}>
            {detail.name}, {detail.age}
          </h3>
          <div className={styles.panelSub}>
            {detail.unit} · {detail.zone ? `${detail.zone} · ` : ""}
            {score.recency}
          </div>
        </div>
      </div>

      <div className={styles.kpis}>
        <div className={styles.kpi}>
          <div className={styles.kpiV} style={{ color }}>
            {pct(score.risk)}
          </div>
          <div className={styles.kpiL}>{acute ? "Acute" : "Chronic"} risk</div>
        </div>
        <div className={styles.kpi}>
          <div className={styles.kpiV}>{pct(score.confidence)}%</div>
          <div className={styles.kpiL}>Confidence</div>
        </div>
        <div className={styles.kpi}>
          <div className={styles.kpiV} style={{ fontSize: 14, paddingTop: 4 }}>
            {score.sensor}
          </div>
          <div className={styles.kpiL}>Source</div>
        </div>
      </div>

      {/* Each sensor drills into its own raw signal: the accelerometer's
          waveform, or the camera's skeleton replay (ADR 0017). Both are
          self-hiding (404 → null); keyed so switching drilldowns refetches
          instead of showing a stale panel for the wrong resident. */}
      {acute && <TraceChart key={`trace-${detail.id}`} />}
      {acute && <ReplayPlayer key={`replay-${detail.id}`} />}

      <h4 className={styles.sec}>Why she&apos;s ranked here</h4>
      {detail.features.map((f, i) => (
        <div className={styles.featRow} key={i}>
          <div className={styles.featTop}>
            <span>{f.label}</span>
            <b>{f.value}</b>
          </div>
          {f.baseline && <div className={styles.featBase}>{f.baseline}</div>}
          <div className={styles.bar}>
            <i
              className={`${styles.barFill} ${acute ? styles.barFillAcute : ""}`}
              style={{ width: `${Math.round(f.weight * 100)}%` }}
            />
          </div>
        </div>
      ))}

      <div className={styles.action}>
        <div className={styles.actionK}>What to do next</div>
        {detail.recommendedAction}
      </div>

      <div className={styles.brief}>
        <div className={styles.briefK}>✎ Briefing (LLM wording · facts fixed)</div>
        <p className={styles.briefP}>{detail.briefing}</p>
      </div>
    </div>
  );
}
