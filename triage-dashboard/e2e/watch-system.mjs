/**
 * System test for the /watch → scoring-service → dashboard → Telegram chain.
 *
 * Run with both services up (dashboard :3000, scoring-service :8000):
 *   node e2e/watch-system.mjs
 *
 * Covers the regression where registering a new person silently rebound the
 * "Report as" selector, so a stranger's fall was reported under the last
 * registered name. Registers a throwaway resident, fires a test detection,
 * and asserts the alert stays GENERIC end to end (UI log, /alerts/status,
 * dashboard acute row). Sends one real Telegram message if configured.
 *
 * Ends by deleting "E2E Check" through the UI (ADR 0014): two-step confirm,
 * roster + registry cascade asserted — the test cleans up its own registrant.
 */
import assert from "node:assert/strict";
import { chromium } from "playwright";

const DASH = process.env.DASH_URL ?? "http://localhost:3000";
const API = process.env.API_URL ?? "http://localhost:8000";
const SHOTS = process.env.SHOT_DIR ?? ".";
const TEST_NAME = "E2E Check";

const startedAt = new Date();
const browser = await chromium.launch();
const page = await browser.newPage();
const step = (msg) => console.log(`  ✓ ${msg}`);

try {
  // — /watch loads
  await page.goto(`${DASH}/watch`, { waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: /knows a fall from a lie-down/ }).waitFor();

  // The roster options arrive via a client-side fetch after hydration —
  // waiting for them guards every interaction below against the hydration
  // race (a fill landing on the pre-React DOM is silently lost).
  const reportAs = page.getByLabel("Report as");
  await reportAs.locator("option").nth(1).waitFor({ state: "attached", timeout: 15_000 });
  step("/watch page loads, roster fetched");

  assert.equal(await reportAs.inputValue(), "", "Report as should start generic");

  // — register a new person (People & locations, ADR 0013)
  await page.getByLabel("Name").fill(TEST_NAME);
  await page.getByRole("button", { name: "Register person" }).click();
  await page.getByText(`${TEST_NAME} registered`).waitFor({ timeout: 10_000 });
  step(`registered "${TEST_NAME}" through the runtime registry`);

  // — the roster refetch must list them… (options in a closed <select> are
  // "hidden" to Playwright, so wait for attachment, not visibility)
  await reportAs
    .locator("option", { hasText: TEST_NAME })
    .first()
    .waitFor({ state: "attached", timeout: 10_000 });
  step("new person appears in the Report-as roster");

  // — …but registration must NOT hijack the selector (the fixed regression)
  assert.equal(
    await reportAs.inputValue(),
    "",
    "REGRESSION: registering a person auto-bound the Report-as selector",
  );
  step("Report-as selector stays on the generic default");

  // — fire a test detection; it must go out generic (no "as <name>")
  await page.getByRole("button", { name: "Send test detection" }).click();
  const sentLog = page.locator("li", { hasText: "Test detection" }).first();
  await sentLog.waitFor({ timeout: 10_000 });
  const sentText = (await sentLog.textContent()) ?? "";
  assert.ok(
    !sentText.includes(" as "),
    `detection was attributed to someone: "${sentText}"`,
  );
  step("test detection sent GENERIC (no name attached)");

  // — Telegram leg: the panel reports the actual dispatch outcome
  const outcomeLog = page
    .locator("li", { hasText: /Telegram alert|Telegram not configured/ })
    .first();
  await outcomeLog.waitFor({ timeout: 15_000 });
  const outcomeText = (await outcomeLog.textContent()) ?? "";
  assert.ok(
    !outcomeText.includes("FAILED"),
    `Telegram dispatch failed: "${outcomeText}"`,
  );
  step(`Telegram leg: ${outcomeText.replace(/^\d\d:\d\d:\d\d/, "").trim()}`);

  // — backend agrees: /alerts/status shows a fresh dispatch
  const status = await (await page.request.get(`${API}/alerts/status`)).json();
  if (status.telegram.configured) {
    assert.equal(status.lastDispatch?.outcome, "sent", "alert dispatch not sent");
    assert.ok(
      new Date(status.lastDispatch.at) >= new Date(startedAt.toISOString().slice(0, 19) + "Z"),
      "lastDispatch predates this test run",
    );
    step("/alerts/status confirms the dispatch went out during this run");
  } else {
    step("/alerts/status: Telegram not configured — leg skipped");
  }
  await page.screenshot({ path: `${SHOTS}/e2e-watch.png`, fullPage: true });

  // — dashboard shows the acute incident for the DEFAULT resident
  await page.goto(DASH, { waitUntil: "domcontentloaded" });
  await page.getByText("Someone needs help right now").waitFor({ timeout: 10_000 });
  await page.getByText("Tan Ah Moi").first().waitFor();
  step("dashboard shows the acute row for the generic default resident");
  await page.screenshot({ path: `${SHOTS}/e2e-dashboard.png`, fullPage: true });

  // — stop alert from the dashboard (ADR 0016): ack lands, badge appears,
  // the button retires (first responder owns the response)
  await page.getByRole("button", { name: /I am responding/ }).click();
  await page.getByText("✓ Dashboard responding").waitFor({ timeout: 10_000 });
  await page
    .getByRole("button", { name: /I am responding/ })
    .waitFor({ state: "detached", timeout: 10_000 });
  const acked = await (await page.request.get(`${API}/alerts/status`)).json();
  assert.equal(acked.acknowledged?.by, "Dashboard", "ack missing from /alerts/status");
  step("dashboard stop-alert acked the incident (badge up, button retired)");

  // — skeleton replay (ADR 0017): fire a camera incident via the API,
  // upload a synthetic landmark trace + facts, and the drilldown must show
  // the player with the enriched deterministic rationale.
  const cvRes = await page.request.post(`${API}/incidents/cv-detected`, {
    data: { stillnessS: 8 },
  });
  const iid = cvRes.headers()["x-incident-id"];
  assert.ok(iid, "cv-detected did not return X-Incident-Id");

  // LIVE ordering (gap check 2026-07-30): open the drilldown BEFORE the
  // upload lands — exactly what happens in a real fall (the SSE event beats
  // the replay POST). The player must appear via its poll, not a lucky
  // mount-time fetch.
  await page.goto(DASH, { waitUntil: "domcontentloaded" });
  await page.getByText("Someone needs help right now").waitFor({ timeout: 10_000 });
  await page.getByText("Tan Ah Moi").first().click();
  assert.equal(
    await page.getByText("How the fall happened").count(), 0,
    "player appeared before any trace existed",
  );

  const frames = Array.from({ length: 30 }, (_, i) => [i * 100, ...Array(39).fill(500)]);
  const up = await page.request.post(`${API}/incidents/replay`, {
    data: {
      incidentId: iid, fps: 10, quantScale: 1000, frames,
      facts: { descentDurationMs: 1900, direction: "right", protectiveArm: false,
               postImpactMovement: "none" },
    },
  });
  assert.equal(up.status(), 200, "replay upload failed");
  assert.equal((await page.request.get(`${API}/incidents/replay`)).status(), 200);
  step("camera incident live; trace uploaded AFTER the drilldown opened");

  await page.getByText("How the fall happened").waitFor({ timeout: 20_000 });
  await page.getByText(/fell rightward/).first().waitFor({ timeout: 5_000 });
  step("player materialized via its poll + enriched rationale shown");
  await page.screenshot({ path: `${SHOTS}/e2e-replay.png`, fullPage: true });

  // reset the beat: the replay must die with the incident
  await page.request.post(`${API}/incidents/clear`);
  assert.equal(
    (await page.request.get(`${API}/incidents/replay`)).status(), 404,
    "replay outlived the incident",
  );
  step("Reset demo dropped the replay (retention claim held)");

  // — resident lifecycle (ADR 0014): delete the registrant through the UI.
  // Capture the target id first so the 404 re-delete check hits the right row.
  const before = (await (await page.request.get(`${API}/caseload`)).json()).entries;
  const target = before.find((e) => e.name === TEST_NAME && e.registered);
  assert.ok(target, "registrant missing from /caseload before deletion");

  await page.goto(`${DASH}/watch`, { waitUntil: "domcontentloaded" });
  const who = page.getByLabel("Who");
  await who.locator("option", { hasText: TEST_NAME }).first()
    .waitFor({ state: "attached", timeout: 15_000 });
  await who.selectOption(target.id);
  await page.getByRole("button", { name: `Remove ${TEST_NAME}` }).click();
  await page.getByRole("button", { name: /Tap again to confirm/ }).click();
  await page.getByText(`${TEST_NAME} removed`).waitFor({ timeout: 10_000 });
  step(`deleted "${TEST_NAME}" via the two-step confirm`);

  // — backend cascade: out of /caseload, and a re-delete hard-404s
  const after = (await (await page.request.get(`${API}/caseload`)).json()).entries;
  assert.ok(after.every((e) => e.id !== target.id), "deleted person still in /caseload");
  assert.equal(
    (await page.request.delete(`${API}/residents/${target.id}`)).status(),
    404,
    "second delete should 404 (already gone)",
  );
  step("backend cascade held: /caseload clean, re-delete 404s");

  // — sweep litter older runs may have left, keeping the registry pristine
  for (const e of after.filter((x) => x.name === TEST_NAME && x.registered)) {
    assert.equal(
      (await page.request.delete(`${API}/residents/${e.id}`)).status(), 200,
      `litter sweep failed for ${e.id}`,
    );
  }

  // — UI agrees: reload (the API sweep bypassed the page), roster is clean
  await page.reload({ waitUntil: "domcontentloaded" });
  const reportAs2 = page.getByLabel("Report as");
  await reportAs2.locator("option").nth(1).waitFor({ state: "attached", timeout: 15_000 });
  assert.equal(
    await reportAs2.locator("option", { hasText: TEST_NAME }).count(),
    0,
    "deleted person still in the Report-as roster",
  );
  step("deleted person left the Report-as roster");

  console.log("\nPASS — register → detection → alert → ack → replay → delete all held.");
} catch (err) {
  await page.screenshot({ path: `${SHOTS}/e2e-failure.png`, fullPage: true }).catch(() => {});
  console.error("\nFAIL —", err.message);
  process.exitCode = 1;
} finally {
  await browser.close();
}
