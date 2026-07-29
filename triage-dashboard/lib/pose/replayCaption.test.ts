import { describe, expect, it } from "vitest";
import type { ReplayFactsPayload } from "@/lib/types";
import { factsCaption } from "./replayCaption";

const FULL: ReplayFactsPayload = {
  descentDurationMs: 1900,
  direction: "right",
  protectiveArm: false,
  postImpactMovement: "slight",
  impactSpeed: 1.42,
  impactSeverity: "hard",
};

describe("factsCaption", () => {
  it("enumerates EVERY informative fact field — none may drift silently", () => {
    const caption = factsCaption(FULL);
    // one assertion per ReplayFactsPayload field; extend when the type grows
    expect(caption).toContain("fell rightward"); // direction
    expect(caption).toContain("1.9s descent"); // descentDurationMs
    expect(caption).toContain("hard impact"); // impactSeverity (impactSpeed's band)
    expect(caption).toContain("no arm protection"); // protectiveArm
    expect(caption).toContain("slight movement after impact"); // postImpactMovement
    expect(caption).toContain("joint positions only, no pixels");
  });

  it("keeps the server's severity wording (drilldown ↔ rationale parity)", () => {
    for (const sev of ["gentle", "moderate", "hard"] as const) {
      expect(factsCaption({ ...FULL, impactSeverity: sev })).toContain(
        `${sev} impact`,
      );
    }
  });

  it("protective arms present reads as arms broke the fall", () => {
    expect(factsCaption({ ...FULL, protectiveArm: true })).toContain(
      "arms broke the fall",
    );
  });

  it("uninformative facts fall back to the plain privacy caption", () => {
    const caption = factsCaption({
      descentDurationMs: null,
      direction: "unknown",
      protectiveArm: null,
      postImpactMovement: "unknown",
      impactSpeed: null,
      impactSeverity: null,
    });
    expect(caption).toBe("Replayed joint positions · no pixels were recorded");
    expect(factsCaption(null)).toBe(caption);
    expect(factsCaption(undefined)).toBe(caption);
  });
});
