import { afterEach, describe, expect, it, vi } from "vitest";
import { announceRosterChange, onRosterChange } from "./rosterSync";

/* Node has no window/BroadcastChannel — stub the browser surface the module
 * touches. FakeBroadcastChannel delivers to OTHER instances on the same
 * name, like the real thing (a tab never hears its own post). */

class FakeBroadcastChannel {
  static instances: FakeBroadcastChannel[] = [];
  onmessage: ((e: { data: unknown }) => void) | null = null;
  closed = false;
  constructor(public name: string) {
    FakeBroadcastChannel.instances.push(this);
  }
  postMessage(data: unknown) {
    for (const ch of FakeBroadcastChannel.instances)
      if (ch !== this && !ch.closed && ch.name === this.name)
        ch.onmessage?.({ data });
  }
  close() {
    this.closed = true;
  }
}

type StorageListener = (e: { key: string | null }) => void;

function stubWindow() {
  const listeners = new Set<StorageListener>();
  const store = new Map<string, string>();
  const win = {
    addEventListener: (type: string, fn: StorageListener) => {
      if (type === "storage") listeners.add(fn);
    },
    removeEventListener: (_: string, fn: StorageListener) => {
      listeners.delete(fn);
    },
    localStorage: {
      setItem: (k: string, v: string) => void store.set(k, v),
      getItem: (k: string) => store.get(k) ?? null,
    },
  };
  vi.stubGlobal("window", win);
  return {
    fireStorage: (key: string) => listeners.forEach((fn) => fn({ key })),
    listeners,
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
  FakeBroadcastChannel.instances = [];
});

describe("rosterSync", () => {
  it("is a safe no-op without a window (SSR)", () => {
    expect(() => announceRosterChange()).not.toThrow();
    expect(onRosterChange(() => undefined)).toBeTypeOf("function");
  });

  it("delivers an announce to another tab's subscriber via BroadcastChannel", () => {
    stubWindow();
    vi.stubGlobal("BroadcastChannel", FakeBroadcastChannel);
    const cb = vi.fn();
    const off = onRosterChange(cb);
    announceRosterChange();
    expect(cb).toHaveBeenCalledTimes(1);
    off();
    announceRosterChange();
    expect(cb).toHaveBeenCalledTimes(1); // closed channel hears nothing
  });

  it("falls back to the storage event when BroadcastChannel is absent", () => {
    const { fireStorage } = stubWindow();
    const cb = vi.fn();
    onRosterChange(cb);
    announceRosterChange(); // writes the localStorage bump
    fireStorage("shine-roster-sync-v1"); // the OTHER tab's storage event
    expect(cb).toHaveBeenCalledTimes(1);
    fireStorage("unrelated-key");
    expect(cb).toHaveBeenCalledTimes(1);
  });

  it("unsubscribe removes the storage listener", () => {
    const { fireStorage, listeners } = stubWindow();
    const cb = vi.fn();
    const off = onRosterChange(cb);
    expect(listeners.size).toBe(1);
    off();
    expect(listeners.size).toBe(0);
    fireStorage("shine-roster-sync-v1");
    expect(cb).not.toHaveBeenCalled();
  });
});
