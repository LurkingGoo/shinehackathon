/**
 * On-device enrollment gallery (ADR 0011). Embeddings + resident binding live
 * in localStorage ONLY — no face image is ever stored, nothing is uploaded.
 * Clearing browser storage forgets everyone (that is a feature, not a bug).
 */

import type { EnrolledPerson } from "./matcher";

const KEY = "watch-face-gallery-v1";

function storage(): Storage | null {
  return typeof window === "undefined" ? null : window.localStorage;
}

export function loadGallery(): EnrolledPerson[] {
  try {
    const raw = storage()?.getItem(KEY);
    return raw ? (JSON.parse(raw) as EnrolledPerson[]) : [];
  } catch {
    return [];
  }
}

function save(gallery: EnrolledPerson[]): void {
  storage()?.setItem(KEY, JSON.stringify(gallery));
}

/** Add one captured angle for a person (creates the person on first capture). */
export function addEmbedding(
  residentId: string,
  label: string,
  embedding: number[],
): EnrolledPerson[] {
  const gallery = loadGallery();
  const person = gallery.find((p) => p.residentId === residentId);
  if (person) {
    person.embeddings.push(embedding);
    person.label = label;
  } else {
    gallery.push({ residentId, label, embeddings: [embedding] });
  }
  save(gallery);
  return gallery;
}

export function removePerson(residentId: string): EnrolledPerson[] {
  const gallery = loadGallery().filter((p) => p.residentId !== residentId);
  save(gallery);
  return gallery;
}
