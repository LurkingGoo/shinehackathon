import { describe, expect, it } from "vitest";
import { buildFallAnnouncement, buildStillDownAnnouncement } from "./alerts";

describe("buildFallAnnouncement", () => {
  it("speaks the mandated phrase exactly twice when identity is unknown", () => {
    const text = buildFallAnnouncement();
    expect(text.match(/Patient has fallen!/g)).toHaveLength(2);
    expect(text).toBe("Patient has fallen! Patient has fallen!");
  });

  it("appends name and zone when the identity is bound", () => {
    expect(buildFallAnnouncement("Rajoo Subramaniam", "Bedroom")).toBe(
      "Patient has fallen! Patient has fallen! Rajoo Subramaniam, Bedroom.",
    );
  });

  it("appends name alone when no zone is known", () => {
    expect(buildFallAnnouncement("Rajoo Subramaniam")).toBe(
      "Patient has fallen! Patient has fallen! Rajoo Subramaniam.",
    );
  });

  it("never leaks a zone without a name to anchor it", () => {
    expect(buildFallAnnouncement(null, "Bedroom")).toBe(
      "Patient has fallen! Patient has fallen!",
    );
  });
});

describe("buildStillDownAnnouncement", () => {
  it("names the person when known, stays generic otherwise", () => {
    expect(buildStillDownAnnouncement("Rajoo Subramaniam")).toBe(
      "Rajoo Subramaniam is still down! Please respond now.",
    );
    expect(buildStillDownAnnouncement()).toBe(
      "The patient is still down! Please respond now.",
    );
  });
});
