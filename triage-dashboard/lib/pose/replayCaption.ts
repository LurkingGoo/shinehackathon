/**
 * Pure caption builder for the "How the fall happened" player (ADR 0017
 * phase 3). Extracted from ReplayPlayer so the fact enumeration is TESTED —
 * the 1.16.0 gap check found impactSeverity silently missing here while the
 * rationale and the Telegram GIF caption already stated it. Wording mirrors
 * the server's _apply_replay_facts fragments so the drilldown, the feature
 * rows and the chat never disagree about the same fall.
 */

import type { ReplayFactsPayload } from "@/lib/types";

const EMPTY = "Replayed joint positions · no pixels were recorded";

export function factsCaption(
  facts: ReplayFactsPayload | null | undefined,
): string {
  if (!facts) return EMPTY;
  const bits: string[] = [];
  if (facts.direction && facts.direction !== "unknown")
    bits.push(
      facts.direction === "toward-camera"
        ? "fell toward the camera"
        : `fell ${facts.direction === "left" ? "leftward" : "rightward"}`,
    );
  if (facts.descentDurationMs)
    bits.push(`${(facts.descentDurationMs / 1000).toFixed(1)}s descent`);
  if (facts.impactSeverity) bits.push(`${facts.impactSeverity} impact`);
  if (facts.protectiveArm === false) bits.push("no arm protection");
  if (facts.protectiveArm === true) bits.push("arms broke the fall");
  if (facts.postImpactMovement === "slight" || facts.postImpactMovement === "moving")
    bits.push(`${facts.postImpactMovement} movement after impact`);
  return bits.length ? `${bits.join(" · ")} · joint positions only, no pixels` : EMPTY;
}
