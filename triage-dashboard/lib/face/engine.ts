/**
 * Face-embedding glue for /watch identity (ADR 0011) — the only module that
 * touches @vladmandic/face-api. Mirrors lib/pose/engine.ts: local-first
 * vendored assets (fetch-pose-assets.mjs copies them out of node_modules —
 * the models ship INSIDE the npm package, no external download), CDN
 * fallback, all inference in-browser. Returns raw 128-D descriptors; the
 * unit-tested matcher decides who they belong to.
 */

// Pinned to the installed package version so local and CDN models agree.
const FACE_API_VERSION = "1.7.15";
const LOCAL_MODELS = "/mediapipe/face";
const CDN_MODELS = `https://cdn.jsdelivr.net/npm/@vladmandic/face-api@${FACE_API_VERSION}/model`;

export interface FaceEngine {
  /** 128-D descriptor of the single most prominent face, or null. */
  embed(video: HTMLVideoElement): Promise<number[] | null>;
  source: "local" | "cdn";
}

async function localAssetAvailable(url: string): Promise<boolean> {
  try {
    return (await fetch(url, { method: "HEAD" })).ok;
  } catch {
    return false;
  }
}

export async function createFaceEngine(): Promise<FaceEngine> {
  const faceapi = await import("@vladmandic/face-api");
  // Backend warm-up when the bundled tf exposes it (types lag the runtime);
  // otherwise the first inference initializes it lazily.
  const tf = (faceapi as unknown as { tf?: { ready?: () => Promise<void> } }).tf;
  if (tf?.ready) await tf.ready();

  const useLocal = await localAssetAvailable(
    `${LOCAL_MODELS}/tiny_face_detector_model-weights_manifest.json`,
  );
  const base = useLocal ? LOCAL_MODELS : CDN_MODELS;
  await Promise.all([
    faceapi.nets.tinyFaceDetector.loadFromUri(base),
    faceapi.nets.faceLandmark68Net.loadFromUri(base),
    faceapi.nets.faceRecognitionNet.loadFromUri(base),
  ]);
  const opts = new faceapi.TinyFaceDetectorOptions({
    inputSize: 320,
    scoreThreshold: 0.5,
  });

  return {
    source: useLocal ? "local" : "cdn",
    async embed(video) {
      const det = await faceapi
        .detectSingleFace(video, opts)
        .withFaceLandmarks()
        .withFaceDescriptor();
      return det ? Array.from(det.descriptor) : null;
    },
  };
}
