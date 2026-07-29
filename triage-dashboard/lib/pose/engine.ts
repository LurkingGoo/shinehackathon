/**
 * MediaPipe glue for /watch — the only module that touches @mediapipe/tasks-vision.
 *
 * Asset policy (ADR 0010): prefer the locally vendored copies under
 * /mediapipe/* (populated by `npm run fetch-pose-assets`, gitignored) so a
 * pre-fetched laptop demos fully offline; fall back to the official CDN URLs
 * so a fresh clone still works with internet. All inference is in-browser —
 * no frame ever leaves the device. (Since ADR 0017, a quantized LANDMARK
 * trace does leave, once, after a confirmed fall — coordinates, never
 * pixels; see lib/pose/replayBuffer.ts.)
 *
 * Kept free of detection logic: this module returns raw landmarks; the
 * unit-tested state machine in fallHeuristic.ts decides what they mean.
 */

import type { LandmarkPoint } from "./fallHeuristic";

// Pinned to the installed package version so local wasm and CDN wasm agree.
const TASKS_VISION_VERSION = "0.10.35";
const LOCAL_WASM = "/mediapipe/wasm";
const CDN_WASM = `https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@${TASKS_VISION_VERSION}/wasm`;
const LOCAL_MODEL = "/mediapipe/pose_landmarker_lite.task";
const CDN_MODEL =
  "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task";

export interface PoseEngine {
  /** Landmarks for the most prominent person, or undefined when none. */
  detect(video: HTMLVideoElement, timestampMs: number): LandmarkPoint[] | undefined;
  close(): void;
  /** Where the assets actually came from — surfaced in the UI. */
  source: "local" | "cdn";
}

async function localAssetAvailable(url: string): Promise<boolean> {
  try {
    const res = await fetch(url, { method: "HEAD" });
    return res.ok;
  } catch {
    return false;
  }
}

export async function createPoseEngine(): Promise<PoseEngine> {
  // Dynamic import keeps ~1 MB of MediaPipe JS out of every other page's bundle.
  const { FilesetResolver, PoseLandmarker } = await import("@mediapipe/tasks-vision");

  const useLocal =
    (await localAssetAvailable(`${LOCAL_WASM}/vision_wasm_internal.wasm`)) &&
    (await localAssetAvailable(LOCAL_MODEL));

  const fileset = await FilesetResolver.forVisionTasks(useLocal ? LOCAL_WASM : CDN_WASM);
  const landmarker = await PoseLandmarker.createFromOptions(fileset, {
    baseOptions: { modelAssetPath: useLocal ? LOCAL_MODEL : CDN_MODEL },
    runningMode: "VIDEO",
    numPoses: 1,
  });

  return {
    source: useLocal ? "local" : "cdn",
    detect(video, timestampMs) {
      const result = landmarker.detectForVideo(video, timestampMs);
      const pose = result.landmarks?.[0];
      if (!pose || pose.length === 0) return undefined;
      return pose.map((p) => ({ x: p.x, y: p.y, visibility: p.visibility }));
    },
    close() {
      landmarker.close();
    },
  };
}
