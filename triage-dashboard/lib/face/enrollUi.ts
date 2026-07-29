/**
 * Capture-button gating for face enrollment — pure, so every state the button
 * can be in is unit-testable without a camera. The component just renders the
 * returned {disabled, label}; no boolean soup in JSX.
 */

import { DEFAULT_MATCH_CONFIG } from "./matcher";

/** Soft cap per person: past this, more angles add noise, not recall. */
export const MAX_ANGLES = 5;

/** A positive face embed this recent counts as "face in view" — the window
 * absorbs the tick cadence (~700 ms) plus brief detection flicker during
 * head movement, so the button doesn't strobe. */
export const FACE_SEEN_FRESH_MS = 2000;

export type FaceStatus = "off" | "loading" | "on" | "error";

export interface CaptureGateInput {
  engineRunning: boolean;
  faceStatus: FaceStatus;
  /** Selected resident id ("" = none chosen). */
  enrollTarget: string;
  /** A face embed succeeded within FACE_SEEN_FRESH_MS. */
  faceSeen: boolean;
  /** Angles already captured for the target. */
  angles: number;
  /** A capture is in flight (serializes rapid clicks). */
  busy: boolean;
}

export interface CaptureGate {
  disabled: boolean;
  label: string;
}

export function captureGate(s: CaptureGateInput): CaptureGate {
  if (!s.engineRunning) return { disabled: true, label: "Start the camera to enroll" };
  if (s.faceStatus === "loading") return { disabled: true, label: "Face models loading…" };
  if (s.faceStatus !== "on") return { disabled: true, label: "Face identity unavailable" };
  if (!s.enrollTarget) return { disabled: true, label: "Choose who to enroll first" };
  if (s.busy) return { disabled: true, label: "Capturing…" };
  if (s.angles >= MAX_ANGLES)
    return { disabled: true, label: `Enough angles captured (${MAX_ANGLES})` };
  if (!s.faceSeen)
    return { disabled: true, label: "No face in view — face the camera" };
  const min = DEFAULT_MATCH_CONFIG.minAngles;
  return {
    disabled: false,
    label:
      s.angles < min
        ? `Capture this angle (${s.angles}/${min} to activate)`
        : `Capture another angle (${s.angles} enrolled)`,
  };
}
