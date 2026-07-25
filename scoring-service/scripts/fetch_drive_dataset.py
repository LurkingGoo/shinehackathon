"""Google Drive -> Tier-1 raw dataset bridge (dev machine only, run once).

The loaders expect local layouts (data/sisfall/<SUBJECT>/F*.txt,
data/casas/*.txt); nothing else in the repo speaks Google Drive. This script
closes that gap for the organiser's shared folder:

  1. download the folder into data/_drive_raw/ (gdown handles folder recursion)
  2. extract any zip/tar archives found (SisFall ships zipped)
  3. SNIFF each file's format and place it:
       - SisFall: 9 comma-separated ints, ';'-terminated -> data/sisfall/<SUBJECT>/
         (validated with the REAL parser first — truncated files are rejected)
       - CASAS:   'DATE TIME SENSOR STATE' lines         -> data/casas/
       - pose annotations (json/csv named bbox/keypoint/pose) -> data/pose/
         (no runtime consumer yet; staged for the CV phase)
  4. upsert provenance (aggregate sha256 + fetched date) into
     data/datasets.lock.json — calibrate.py --json-out embeds this in
     metrics.json so every judge-facing number traces to a dataset hash.

Everything lands under git-ignored data/ subdirs: the committed Tier-2 curated
artifacts (ADR 0008) and the zero-dataset synthetic fallback are untouched.

Usage (from scoring-service/):
    C:\\Users\\lucas\\anaconda3\\python.exe -m pip install gdown        # once
    C:\\Users\\lucas\\anaconda3\\python.exe scripts/fetch_drive_dataset.py \
        --url https://drive.google.com/drive/folders/<FOLDER_ID>
    # then: scripts/calibrate.py             (counts + operating point)
    #       scripts/calibrate.py --json-out  (refresh metrics.json)
    #       scripts/curate.py                (rebake Tier-2 curated artifacts)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tarfile
import zipfile
from datetime import date
from pathlib import Path

_SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVICE_ROOT))

from app.data.loaders import DATA_DIR, load_sisfall_trace  # noqa: E402

RAW_DIR = DATA_DIR / "_drive_raw"  # staging area; under git-ignored data/
SISFALL_DIR = DATA_DIR / "sisfall"
CASAS_DIR = DATA_DIR / "casas"
POSE_DIR = DATA_DIR / "pose"
LOCK_PATH = DATA_DIR / "datasets.lock.json"

_SUBJECT = re.compile(r"S[AE]\d{2}", re.IGNORECASE)
_CASAS_LINE = re.compile(
    r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(\.\d+)?\s+\S+\s+\S+")
_POSE_NAME = re.compile(r"bbox|keypoint|pose", re.IGNORECASE)


def download(url: str) -> None:
    """Pull the shared folder into the staging dir via gdown (dev-only dep)."""
    try:
        import gdown
    except ImportError:
        raise SystemExit("gdown not installed — run: <python> -m pip install gdown")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    gdown.download_folder(url=url, output=str(RAW_DIR), quiet=False,
                          use_cookies=False)


def extract_archives(root: Path) -> int:
    """Unpack every zip/tar found (SisFall ships zipped); returns count."""
    n = 0
    for p in sorted(root.rglob("*")):
        if p.suffix.lower() == ".zip" and zipfile.is_zipfile(p):
            zipfile.ZipFile(p).extractall(p.parent / p.stem)
            n += 1
        elif p.suffix.lower() in (".gz", ".tgz", ".tar") and tarfile.is_tarfile(p):
            tarfile.open(p).extractall(p.parent / p.stem)
            n += 1
    return n


def sniff(path: Path) -> str | None:
    """Classify one file: 'sisfall' | 'casas' | 'pose' | None (skip)."""
    suffix = path.suffix.lower()
    if suffix == ".txt":
        try:
            head = path.read_text(errors="ignore")[:4096].splitlines()
        except OSError:
            return None
        head = [ln for ln in head if ln.strip()][:5]
        if not head:
            return None
        if all(len([f for f in ln.strip().rstrip(";").split(",") if f.strip()]) == 9
               for ln in head):
            return "sisfall"
        if all(_CASAS_LINE.match(ln) for ln in head):
            return "casas"
        return None
    if suffix in (".json", ".csv") and _POSE_NAME.search(path.name):
        return "pose"
    return None


def place_sisfall(src: Path) -> Path:
    """Validate with the REAL parser, then place under data/sisfall/<SUBJECT>/.

    Raises ValueError (from load_sisfall_trace) on truncation/format drift —
    nothing lands in the dataset dir unless calibrate.py could parse it."""
    load_sisfall_trace(src)
    m = _SUBJECT.search(src.name) or _SUBJECT.search(src.parent.name)
    subject = m.group(0).upper() if m else "UNKNOWN"
    dest = SISFALL_DIR / subject / src.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return dest


def place_flat(src: Path, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    shutil.copy2(src, dest)
    return dest


def aggregate_sha256(paths: list[Path]) -> str:
    """Deterministic dataset-level hash: sha256 over sorted per-file digests."""
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(hashlib.sha256(p.read_bytes()).hexdigest().encode())
        h.update(p.name.encode())
    return h.hexdigest()


def update_lock(key: str, files: list[Path], url: str, citation: str) -> None:
    """Upsert one dataset's provenance; other datasets' entries are preserved."""
    doc: dict = {}
    if LOCK_PATH.is_file():
        try:
            doc = json.loads(LOCK_PATH.read_text())
        except ValueError:
            doc = {}
    doc[key] = {"sha256": aggregate_sha256(files), "files": len(files),
                "fetched": date.today().isoformat(), "source_url": url,
                "citation": citation}
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOCK_PATH.write_text(json.dumps(doc, indent=2) + "\n")


def normalize() -> dict[str, list[Path]]:
    """Sniff + place everything staged under RAW_DIR; returns placements."""
    placed: dict[str, list[Path]] = {"sisfall": [], "casas": [], "pose": []}
    rejected = 0
    for p in sorted(RAW_DIR.rglob("*")):
        if not p.is_file():
            continue
        kind = sniff(p)
        if kind == "sisfall":
            try:
                placed["sisfall"].append(place_sisfall(p))
            except ValueError as e:
                rejected += 1
                print(f"  REJECTED (unparsable sisfall): {e}")
        elif kind == "casas":
            placed["casas"].append(place_flat(p, CASAS_DIR))
        elif kind == "pose":
            placed["pose"].append(place_flat(p, POSE_DIR))
    placed["_rejected"] = rejected  # type: ignore[assignment]
    return placed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", required=True, help="Google Drive folder URL")
    ap.add_argument("--skip-download", action="store_true",
                    help="normalize an already-populated data/_drive_raw/")
    args = ap.parse_args(argv)

    if not args.skip_download:
        download(args.url)
    if not RAW_DIR.is_dir():
        print(f"nothing staged at {RAW_DIR}")
        return 1
    n_arch = extract_archives(RAW_DIR)
    placed = normalize()
    rejected = placed.pop("_rejected")

    print(f"\narchives extracted: {n_arch}   rejected sisfall files: {rejected}")
    for kind, files in placed.items():
        print(f"  {kind}: {len(files)} files -> data/{'sisfall' if kind == 'sisfall' else kind}/")
    if placed["sisfall"]:
        update_lock("sisfall", placed["sisfall"], args.url,
                    "Sucerquia et al., 2017 — SisFall: A Fall and Movement Dataset")
    if placed["casas"]:
        update_lock("casas", placed["casas"], args.url, "WSU CASAS smart-home datasets")
    if placed["pose"]:
        print("  NOTE: pose annotations staged at data/pose/ — no runtime "
              "consumer yet (the CV track is the browser heuristic by design).")

    print("\nnext: scripts/calibrate.py             # counts + operating point"
          "\n      scripts/calibrate.py --json-out  # refresh metrics.json"
          "\n      scripts/curate.py                # rebake Tier-2 curated artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
