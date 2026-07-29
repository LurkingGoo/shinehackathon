/**
 * Shared skeleton geometry: the bone graph the /watch overlay draws, and the
 * replay subset (ADR 0017) — the landmarks worth transmitting after a fall.
 */

// Minimal skeleton: torso box + limbs, MediaPipe pose indices.
export const BONES: Array<[number, number]> = [
  [11, 12], [11, 23], [12, 24], [23, 24], // torso
  [11, 13], [13, 15], [12, 14], [14, 16], // arms
  [23, 25], [25, 27], [24, 26], [26, 28], // legs
];

/** Replay subset: nose (head dot) + every joint BONES references. 13 points
 * instead of 33 keeps the upload ~2.5x smaller with zero visual loss. */
export const REPLAY_LANDMARKS: readonly number[] = [
  0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28,
];

const SUBSET_INDEX = new Map(REPLAY_LANDMARKS.map((m, i) => [m, i]));

/** BONES remapped onto REPLAY_LANDMARKS positions, for drawing a replay frame. */
export const REPLAY_BONES: Array<[number, number]> = BONES.map(([a, b]) => [
  SUBSET_INDEX.get(a) as number,
  SUBSET_INDEX.get(b) as number,
]);
