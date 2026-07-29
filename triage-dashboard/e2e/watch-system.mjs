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
 * NOTE: leaves "E2E Check" in the runtime registry (data/residents.json) —
 * clean up via reset or by removing the entry and restarting the service.
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

  console.log("\nPASS — register → generic detection → alert → dashboard all held.");
} catch (err) {
  await page.screenshot({ path: `${SHOTS}/e2e-failure.png`, fullPage: true }).catch(() => {});
  console.error("\nFAIL —", err.message);
  process.exitCode = 1;
} finally {
  await browser.close();
}
