import { describe, expect, it } from "vitest";
import {
  MAX_RESPEAKS,
  buildAckAnnouncement,
  buildFallAnnouncement,
  buildStillDownAnnouncement,
  heartbeatFresh,
  respeakDecision,
} from "./alerts";

describe("buildFallAnnouncement", () => {
  it("speaks name and zone inline, twice", () => {
    expect(buildFallAnnouncement("Rajoo Subramaniam", "Bedroom")).toBe(
      "Patient Rajoo Subramaniam has fallen at Bedroom! " +
        "Patient Rajoo Subramaniam has fallen at Bedroom!",
    );
  });

  it("degrades to the bare phrase, still twice, when identity is unknown", () => {
    const text = buildFallAnnouncement();
    expect(text.match(/Patient has fallen!/g)).toHaveLength(2);
    expect(text).toBe("Patient has fallen! Patient has fallen!");
  });

  it("speaks the name alone when no zone is known", () => {
    expect(buildFallAnnouncement("Rajoo Subramaniam")).toBe(
      "Patient Rajoo Subramaniam has fallen! Patient Rajoo Subramaniam has fallen!",
    );
  });

  it("speaks the zone even without a name", () => {
    expect(buildFallAnnouncement(null, "Bedroom")).toBe(
      "Patient has fallen at Bedroom! Patient has fallen at Bedroom!",
    );
  });
});

describe("respeakDecision", () => {
  const live = { acknowledged: false, acuteActive: true, repeats: 0 };

  it("keeps speaking while the alert is live and unacknowledged", () => {
    expect(respeakDecision(live)).toBe("speak");
    expect(respeakDecision({ ...live, repeats: MAX_RESPEAKS - 1 })).toBe("speak");
  });

  it("announces the ack exactly when it lands — even past the cap", () => {
    expect(respeakDecision({ ...live, acknowledged: true })).toBe("announce-ack");
    expect(
      respeakDecision({ acknowledged: true, acuteActive: false, repeats: 99 }),
    ).toBe("announce-ack");
  });

  it("stops silently when the incident clears (Reset demo / TTL)", () => {
    expect(respeakDecision({ ...live, acuteActive: false })).toBe("stop");
  });

  it("stops silently at the repeat cap", () => {
    expect(respeakDecision({ ...live, repeats: MAX_RESPEAKS })).toBe("stop");
  });
});

describe("heartbeatFresh", () => {
  it("is fresh strictly within the TTL window", () => {
    expect(heartbeatFresh("1000", 1000, 3000)).toBe(true);
    expect(heartbeatFresh("1000", 3999, 3000)).toBe(true);
    expect(heartbeatFresh("1000", 4000, 3000)).toBe(false);
  });

  it("rejects missing, garbage, and future values", () => {
    expect(heartbeatFresh(null, 1000)).toBe(false);
    expect(heartbeatFresh("not-a-number", 1000)).toBe(false);
    expect(heartbeatFresh("2000", 1000)).toBe(false); // clock went backwards
  });
});

describe("buildAckAnnouncement", () => {
  it("names the responder", () => {
    expect(buildAckAnnouncement("Dashboard")).toBe(
      "Alert acknowledged. Dashboard is responding.",
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
