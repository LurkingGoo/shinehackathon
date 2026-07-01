import styles from "./dashboard.module.css";

/** Circular risk gauge. Risk drives the arc; color is status. */
export function RiskRing({ risk, color }: { risk: number; color: string }) {
  const r = 24;
  const c = 2 * Math.PI * r;
  const off = c * (1 - risk);
  return (
    <div className={styles.ring} aria-hidden>
      <svg width="58" height="58">
        <circle cx="29" cy="29" r={r} stroke="#eee5da" strokeWidth="6" fill="none" />
        <circle
          cx="29"
          cy="29"
          r={r}
          stroke={color}
          strokeWidth="6"
          fill="none"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={off}
        />
      </svg>
      <div className={styles.ringNum} style={{ color }}>
        {Math.round(risk * 100)}
      </div>
    </div>
  );
}
