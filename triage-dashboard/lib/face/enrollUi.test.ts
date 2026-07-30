import { describe, expect, it } from "vitest";
import {
  MAX_ANGLES,
  captureGate,
  registrationNudge,
  type CaptureGateInput,
} from "./enrollUi";

const ready: CaptureGateInput = {
  engineRunning: true,
  faceStatus: "on",
  enrollTarget: "r-rajoo",
  faceSeen: true,
  angles: 0,
  busy: false,
};

describe("captureGate", () => {
  it("enables only when camera + models + target + face are all present", () => {
    expect(captureGate(ready).disabled).toBe(false);
  });

  it("walks the precondition ladder in priority order", () => {
    expect(captureGate({ ...ready, engineRunning: false }).label).toBe(
      "Start the camera to enroll",
    );
    expect(captureGate({ ...ready, faceStatus: "loading" }).label).toBe(
      "Face models loading…",
    );
    expect(captureGate({ ...ready, faceStatus: "error" }).label).toBe(
      "Face identity unavailable",
    );
    expect(captureGate({ ...ready, enrollTarget: "" }).label).toBe(
      "Choose who to enroll first",
    );
    expect(captureGate({ ...ready, faceSeen: false }).label).toBe(
      "No face in view — face the camera",
    );
  });

  it("disables while a capture is in flight (rapid-click race guard)", () => {
    const g = captureGate({ ...ready, busy: true });
    expect(g).toEqual({ disabled: true, label: "Capturing…" });
  });

  it("counts progress toward the matching-activation minimum", () => {
    expect(captureGate({ ...ready, angles: 1 }).label).toContain("1/2");
    const activated = captureGate({ ...ready, angles: 2 });
    expect(activated.disabled).toBe(false);
    expect(activated.label).toContain("2 enrolled");
  });

  it("caps at MAX_ANGLES", () => {
    const g = captureGate({ ...ready, angles: MAX_ANGLES });
    expect(g.disabled).toBe(true);
    expect(g.label).toContain(String(MAX_ANGLES));
  });

  it("busy outranks the angle cap, cap outranks face visibility", () => {
    expect(captureGate({ ...ready, busy: true, angles: MAX_ANGLES }).label).toBe(
      "Capturing…",
    );
    expect(
      captureGate({ ...ready, faceSeen: false, angles: MAX_ANGLES }).label,
    ).toContain("Enough angles");
  });
});

describe("registrationNudge", () => {
  const raju = { residentId: "r-raju", name: "Raju" };

  it("is silent when nobody was just registered", () => {
    expect(registrationNudge(null, 0)).toBeNull();
  });

  it("warns by name until the matcher minimum is reached", () => {
    const msg = registrationNudge(raju, 0);
    expect(msg).toContain("Raju");
    expect(msg).toContain("NOT recognizable");
    expect(msg).toContain("Unidentified person");
    expect(msg).toContain("2 more face angles");
  });

  it("counts down and pluralizes the remaining angles", () => {
    expect(registrationNudge(raju, 1)).toContain("1 more face angle below");
  });

  it("clears itself once the person is matchable", () => {
    expect(registrationNudge(raju, 2)).toBeNull();
    expect(registrationNudge(raju, 5)).toBeNull();
  });
});
