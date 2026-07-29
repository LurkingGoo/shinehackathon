"use client";

/**
 * Shared re-speak loop (ADR 0016) — used by BOTH alert surfaces: the /watch
 * station and the dashboard (a Simulate incident arrives over SSE and must
 * sound there too). Each page supplies its own `speak` so it owns its muting
 * rules (watch: the sound toggle; dashboard: toggle + only while visible).
 */

import { useCallback, useEffect, useRef } from "react";
import type { AlertStatus } from "@/lib/types";
import { dataClient } from "@/lib/data/client";
import {
  RESPEAK_INTERVAL_MS,
  buildAckAnnouncement,
  respeakDecision,
} from "./alerts";

export function useRespeak(
  speak: (text: string) => void,
  onAck?: (status: AlertStatus) => void,
) {
  const timerRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined);
  const countRef = useRef(0);

  const stopRespeak = useCallback(() => {
    clearInterval(timerRef.current);
    timerRef.current = undefined;
  }, []);

  const startRespeak = useCallback(
    (announcement: string) => {
      stopRespeak();
      countRef.current = 0;
      timerRef.current = setInterval(async () => {
        const status = await dataClient.getAlertStatus().catch(() => null);
        if (!status) return; // service unreachable — try again next tick
        let acuteActive = true;
        if (!status.acknowledged) {
          const caseload = await dataClient.getRankedCaseload().catch(() => null);
          if (caseload)
            acuteActive = caseload.entries.some((e) => e.score.track === "acute");
        }
        const action = respeakDecision({
          acknowledged: Boolean(status.acknowledged),
          acuteActive,
          repeats: countRef.current,
        });
        if (action === "announce-ack") {
          stopRespeak();
          if (status.acknowledged) {
            speak(buildAckAnnouncement(status.acknowledged.by));
            onAck?.(status);
          }
        } else if (action === "stop") {
          stopRespeak();
        } else {
          countRef.current += 1;
          speak(announcement);
        }
      }, RESPEAK_INTERVAL_MS);
    },
    [speak, onAck, stopRespeak],
  );

  useEffect(() => () => stopRespeak(), [stopRespeak]);
  return { startRespeak, stopRespeak };
}
