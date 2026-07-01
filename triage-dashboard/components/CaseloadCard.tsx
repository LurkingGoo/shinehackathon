import type { CaseloadEntry } from "@/lib/types";
import { avatarColor, initials, pct, riskColor, trackWord } from "@/lib/ui";
import { RiskRing } from "./RiskRing";
import styles from "./dashboard.module.css";

export function CaseloadCard({
  entry,
  selected,
  flash,
  onSelect,
}: {
  entry: CaseloadEntry;
  selected: boolean;
  flash?: boolean;
  onSelect: (id: string) => void;
}) {
  const { score } = entry;
  const acute = score.track === "acute";
  const low = !acute && score.risk < 0.35;
  const color = riskColor(score.risk, score.track);

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onSelect(entry.id)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect(entry.id);
        }
      }}
      className={[
        styles.card,
        acute ? styles.cardAcute : "",
        flash ? styles.flash : "",
        selected ? styles.cardSel : "",
      ].join(" ")}
      aria-label={`${entry.name}, ${trackWord(score.track)} risk ${pct(score.risk)}`}
    >
      {acute && <span className={styles.badge}>FALL DETECTED</span>}

      <div
        className={styles.avatar}
        style={{ background: avatarColor(entry.id, score.track) }}
      >
        {initials(entry.name)}
      </div>

      <div className={styles.body}>
        <div className={styles.nm}>
          {entry.name} <span>· {entry.age}</span>
        </div>
        <div className={styles.meta}>
          {entry.unit} · {score.recency} · {score.sensor}
        </div>
        <div
          className={[
            styles.why,
            acute ? styles.whyAcute : low ? styles.whyLow : "",
          ].join(" ")}
        >
          <span className={styles.trackTag} style={{ color }}>
            {trackWord(score.track)}
          </span>
          <span>{score.rationale}</span>
        </div>

        {acute && (
          <div className={styles.actions}>
            {/* Design-concrete affordances. Wired to no-op here; backend/Twilio later. */}
            <button
              type="button"
              className={`${styles.actionBtn} ${styles.callNow}`}
              onClick={(e) => e.stopPropagation()}
            >
              📞 Call now
            </button>
            <button
              type="button"
              className={`${styles.actionBtn} ${styles.escalate}`}
              onClick={(e) => e.stopPropagation()}
            >
              Escalate
            </button>
          </div>
        )}
      </div>

      <div className={styles.stat}>
        <RiskRing risk={score.risk} color={color} />
        <div className={styles.conf}>
          confidence <b>{pct(score.confidence)}%</b>
        </div>
        <div className={styles.sens}>{score.sensorClass}</div>
      </div>
    </div>
  );
}
