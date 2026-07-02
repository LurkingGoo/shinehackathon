/* ============================================================================
 * Slide-asset capture — full screenshots + the 6 walkthrough chips.
 *
 * Run (servers must be up: scoring-service :8000, dashboard :3000):
 *   cd triage-dashboard && node ../docs/slides/capture.mjs
 *
 * Philosophy (docs/slide-plan.md): screenshots are regenerated, never edited.
 * Chips are cut from the SAME rendered state as the full shots, with crop
 * regions derived from element bounding boxes — so a product change moves the
 * chips automatically and nothing goes stale. No hand annotation, ever.
 * ==========================================================================*/

import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

// playwright lives in triage-dashboard/node_modules — resolve from the cwd
// (the script itself sits with the deck source, outside any package).
const { chromium } = createRequire(join(process.cwd(), "package.json"))(
  "playwright"
);

const BASE = process.env.DASHBOARD_URL ?? "http://localhost:3000";
const OUT = join(dirname(fileURLToPath(import.meta.url)), "assets");
mkdirSync(OUT, { recursive: true });

// Projector-friendly frame: 16:10 desktop, 2x for crisp crops.
const VIEWPORT = { width: 1600, height: 1000 };
const SCALE = 2;
const PAD = 14; // css px of breathing room around every chip crop

/** Clip a padded region around one or more elements, in the current state.
 *  padTop can be tightened when a neighbouring element sits just above. */
async function chip(page, locators, file, { padTop = PAD } = {}) {
  const boxes = [];
  for (const loc of locators) {
    const b = await loc.boundingBox();
    if (b) boxes.push(b);
  }
  if (!boxes.length) throw new Error(`chip ${file}: no visible element`);
  const x1 = Math.min(...boxes.map((b) => b.x)) - PAD;
  const y1 = Math.min(...boxes.map((b) => b.y)) - padTop;
  const x2 = Math.max(...boxes.map((b) => b.x + b.width)) + PAD;
  const y2 = Math.max(...boxes.map((b) => b.y + b.height)) + PAD;
  await page.screenshot({
    path: join(OUT, file),
    clip: {
      x: Math.max(0, x1),
      y: Math.max(0, y1),
      width: Math.min(VIEWPORT.width, x2) - Math.max(0, x1),
      height: Math.min(VIEWPORT.height, y2) - Math.max(0, y1),
    },
  });
  console.log(`  chip  ${file}`);
}

async function full(page, file) {
  await page.screenshot({ path: join(OUT, file) });
  console.log(`  full  ${file}`);
}

const run = async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({
    viewport: VIEWPORT,
    deviceScaleFactor: SCALE,
  });

  // CSS-module classes hash in dev but keep their base name: dashboard_card__x
  const sel = (name) => `[class*="_${name}__"]`;

  // -- reset to the calm state -----------------------------------------------
  const clear = await page.request.post(`${BASE}/api/incidents/clear`);
  if (!clear.ok()) throw new Error(`clear -> ${clear.status()}`);

  await page.goto(BASE);
  await page.waitForSelector(sel("card"));
  await page.waitForTimeout(400); // let avatars/rings settle

  // -- calm establishing shot + calm chips ------------------------------------
  console.log("calm state:");
  await full(page, "caseload-calm.png");
  await chip(page, [page.locator(sel("toolbar"))], "chip-simulate-button.png");
  await chip(page, [page.locator(sel("card")).first()], "chip-top-row.png", {
    padTop: 4, // section band sits directly above the first card
  });

  // -- the beat: simulate → pin + flash ---------------------------------------
  console.log("incident beat:");
  await page.click('button:has-text("Simulate incident")');
  await page.waitForSelector("text=FALL DETECTED", { timeout: 15000 });
  // flash class lives ~1.1s — capture inside that window
  await page.waitForTimeout(250);
  await full(page, "caseload-incident-pin.png");
  await chip(page, [page.locator(sel("cardAcute"))], "chip-acute-card.png", {
    padTop: 4, // "someone needs help" band sits directly above
  });

  // -- drill-down (opens automatically with the incident) ---------------------
  await page.waitForSelector("text=What to do next");
  await page.waitForTimeout(1200); // let the flash finish for the steady shot
  await full(page, "caseload-incident-drilldown.png");
  await chip(page, [page.locator(sel("action"))], "chip-recommended-action.png");
  await chip(
    page,
    [page.locator('h4:has-text("ranked here")'),
     ...(await page.locator(sel("featRow")).all())],
    "chip-feature-decomposition.png" // heading + all feature rows
  );
  await chip(page, [page.locator(sel("kpis"))], "chip-confidence-axis.png");
  await chip(
    page,
    [page.locator('h4:has-text("What the sensor saw")'), page.locator(sel("trace"))],
    "chip-sensor-waveform.png" // the ordered fall signature, from the live drilldown
  );

  // -- leave the demo calm -----------------------------------------------------
  await page.request.post(`${BASE}/api/incidents/clear`);
  await browser.close();
  console.log(`\nassets written to ${OUT}`);
};

run().catch((e) => {
  console.error(e);
  process.exit(1);
});
