"""Fetch the real datasets with pinned provenance.

    python scripts/fetch_datasets.py            # fetch anything missing, verify the rest
    python scripts/fetch_datasets.py --verify   # only verify data on disk vs the lock

Every dataset that enters the pipeline is recorded in data/datasets.lock.json:
source URL, sha256, size, fetch date, citation. The lock file is COMMITTED
(the data itself is git-ignored) — it is the provenance chain the scoring-card
Datasheet cites, and re-fetching on another machine verifies against it.
Community mirrors are used because the official hosts are dead/oversized
(docs/scoring-card.md §Datasheet); citations reference the original papers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
import zipfile
from datetime import date
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
LOCK = DATA / "datasets.lock.json"

SOURCES = {
    "sisfall": {
        "url": "https://github.com/BIng2325/SisFall/releases/download/dataset/SisFall.zip",
        "kind": "zip",
        "target": "sisfall",
        "citation": "Sucerquia, Lopez, Vargas-Bonilla — SisFall: A Fall and "
                    "Movement Dataset. Sensors 17(1):198, 2017. Mirror of the "
                    "original Universidad de Antioquia release (official host down).",
    },
    "casas-aruba": {
        "url": "https://raw.githubusercontent.com/vladbucur-8/casas-datascience/"
               "main/datasets/aruba/data",
        "kind": "file",
        "target": "casas/aruba.txt",
        "citation": "Cook et al. — CASAS Aruba testbed (WSU), single resident, "
                    "2010-11-04..2011-06-11. Mirror; official distribution moved "
                    "into the 2.7 GB Zenodo all-homes bundle (record 15708568).",
    },
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  downloading {url}")
    with urllib.request.urlopen(url) as r, dest.open("wb") as f:
        expected = int(r.headers.get("Content-Length") or 0)
        done = 0
        while chunk := r.read(1 << 20):
            f.write(chunk)
            done += len(chunk)
            if done % (20 << 20) < (1 << 20):
                print(f"    {done / (1 << 20):.0f} MiB ...")
    if expected and dest.stat().st_size != expected:
        dest.unlink()  # never leave a truncated artifact that could get locked
        raise IOError(f"truncated download: got {done} of {expected} bytes — "
                      f"retry, or fetch with curl -L into {dest}")
    print(f"    {dest.stat().st_size / (1 << 20):.1f} MiB done")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify", action="store_true", help="verify only, no downloads")
    args = ap.parse_args()

    lock = json.loads(LOCK.read_text()) if LOCK.exists() else {}
    failures = 0

    for name, src in SOURCES.items():
        print(f"[{name}]")
        raw = DATA / "_raw" / Path(src["url"]).name
        entry = lock.get(name)

        if entry and args.verify:
            target = DATA / src["target"]
            ok = target.exists()
            print(f"  lock sha256 {entry['sha256'][:16]}…  target on disk: {ok}")
            failures += 0 if ok else 1
            continue

        if not raw.exists():
            if args.verify:
                print("  raw artifact missing (ok if extracted target exists)")
            else:
                _download(src["url"], raw)

        if raw.exists():
            digest = _sha256(raw)
            if entry and entry["sha256"] != digest:
                print(f"  !! sha256 MISMATCH vs lock — refusing to use "
                      f"(lock {entry['sha256'][:16]}…, got {digest[:16]}…)")
                failures += 1
                continue
            if src["kind"] == "zip":
                out = DATA / src["target"]
                if not out.exists():
                    print(f"  extracting -> {out}")
                    with zipfile.ZipFile(raw) as z:
                        z.extractall(out)
            else:
                out = DATA / src["target"]
                if not out.exists():
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_bytes(raw.read_bytes())
            lock[name] = {
                "source_url": src["url"],
                "sha256": digest,
                "bytes": raw.stat().st_size,
                "fetched": entry["fetched"] if entry else str(date.today()),
                "citation": src["citation"],
                "target": src["target"],
            }

    if not args.verify:
        DATA.mkdir(parents=True, exist_ok=True)
        LOCK.write_text(json.dumps(lock, indent=2) + "\n")
        print(f"\nlock written -> {LOCK}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
