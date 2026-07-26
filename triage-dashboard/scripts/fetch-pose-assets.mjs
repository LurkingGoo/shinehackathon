/**
 * Vendor the MediaPipe pose assets into public/mediapipe/ (ADR 0010) so /watch
 * demos fully offline. Gitignored; safe to re-run (skips files already there).
 *
 *   npm run fetch-pose-assets
 *
 * Without this step /watch still works online — the engine falls back to the
 * official CDN URLs.
 */
import { createRequire } from "node:module";
import { copyFile, mkdir, readdir, stat, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);
const MODEL_URL =
  "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task";

const root = path.join(import.meta.dirname, "..");
const outDir = path.join(root, "public", "mediapipe");
const wasmOut = path.join(outDir, "wasm");
const modelOut = path.join(outDir, "pose_landmarker_lite.task");

await mkdir(wasmOut, { recursive: true });

// 1. wasm bundle — copied from the installed package so versions always agree.
// (package.json is not export-mapped, so resolve the main entry instead)
const wasmSrc = path.join(
  path.dirname(require.resolve("@mediapipe/tasks-vision")),
  "wasm",
);
for (const f of await readdir(wasmSrc)) {
  const dest = path.join(wasmOut, f);
  if (!existsSync(dest)) {
    await copyFile(path.join(wasmSrc, f), dest);
    console.log(`copied  wasm/${f}`);
  }
}

// 2. face-identity models (ADR 0011) — they SHIP inside @vladmandic/face-api,
// so this is a pure copy: tiny detector + 68-landmark + recognition net.
const faceOut = path.join(outDir, "face");
await mkdir(faceOut, { recursive: true });
const faceSrc = path.join(
  path.dirname(require.resolve("@vladmandic/face-api")),
  "..",
  "model",
);
const FACE_MODELS = [
  "tiny_face_detector_model",
  "face_landmark_68_model",
  "face_recognition_model",
];
for (const m of FACE_MODELS) {
  for (const suffix of ["-weights_manifest.json", ".bin"]) {
    const f = `${m}${suffix}`;
    const dest = path.join(faceOut, f);
    if (!existsSync(dest)) {
      await copyFile(path.join(faceSrc, f), dest);
      console.log(`copied  face/${f}`);
    }
  }
}

// 3. pose model — downloaded once from Google's published model URL.
if (existsSync(modelOut) && (await stat(modelOut)).size > 1_000_000) {
  console.log("model already present — skipping download");
} else {
  console.log(`downloading ${MODEL_URL} ...`);
  const res = await fetch(MODEL_URL);
  if (!res.ok) throw new Error(`model download failed: HTTP ${res.status}`);
  await writeFile(modelOut, Buffer.from(await res.arrayBuffer()));
  console.log(`saved   pose_landmarker_lite.task (${(await stat(modelOut)).size} bytes)`);
}

console.log("pose assets ready — /watch now runs offline.");
