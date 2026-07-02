/* ============================================================================
 * Pre-render committed .mmd diagram sources to SVG, themed Warm Human.
 *
 * Run:  cd triage-dashboard && node ../docs/slides/render-diagrams.mjs
 *
 * Uses the mermaid npm bundle inside the Playwright chromium already installed
 * for capture.mjs — no extra browser download (vs. mermaid-cli/puppeteer).
 * Theme variables mirror triage-dashboard/app/globals.css tokens.
 * ==========================================================================*/

import { mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(join(process.cwd(), "package.json"));
const { chromium } = require("playwright");
const mermaidJs = require.resolve("mermaid/dist/mermaid.min.js");

const HERE = dirname(fileURLToPath(import.meta.url));
const SRC = join(HERE, "diagrams");
const OUT = join(HERE, "assets");
mkdirSync(OUT, { recursive: true });

// Warm Human tokens (app/globals.css) → mermaid theme variables
const THEME = {
  theme: "base",
  themeVariables: {
    fontFamily: '"Segoe UI", Roboto, Helvetica, Arial, sans-serif',
    fontSize: "16px",
    primaryColor: "#fffdfb",        // node fill = panel
    primaryTextColor: "#33291f",    // ink
    primaryBorderColor: "#c65d3b",  // terracotta
    lineColor: "#8a7c6d",           // muted
    clusterBkg: "#faf5ee",          // panel-soft
    clusterBorder: "#efe6da",       // line
    edgeLabelBackground: "#fbf7f2", // bg
  },
  // htmlLabels MUST stay false: foreignObject labels don't render when the
  // SVG is loaded via <img> (as Marp does) — pure <text> labels always do.
  flowchart: { curve: "basis", htmlLabels: false },
  htmlLabels: false,
};

const browser = await chromium.launch();
const page = await browser.newPage();
await page.setContent("<html><body></body></html>");
await page.addScriptTag({ path: mermaidJs });

for (const file of readdirSync(SRC).filter((f) => f.endsWith(".mmd"))) {
  const source = readFileSync(join(SRC, file), "utf8");
  const svg = await page.evaluate(
    async ({ source, theme }) => {
      window.mermaid.initialize({ startOnLoad: false, ...theme });
      const { svg } = await window.mermaid.render("d" + Date.now(), source);
      return svg;
    },
    { source, theme: THEME }
  );
  const out = join(OUT, file.replace(/\.mmd$/, ".svg"));
  writeFileSync(out, svg, "utf8");
  console.log(`rendered ${file} -> ${out}`);
}

await browser.close();
