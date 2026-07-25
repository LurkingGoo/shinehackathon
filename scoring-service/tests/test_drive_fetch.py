"""Google Drive -> Tier-1 bridge tests (scripts/fetch_drive_dataset.py).

The download itself (gdown) is a dev-machine network step and is NOT tested;
what IS pinned is everything that decides where a byte lands: format sniffing
(SisFall 9-field vs CASAS event lines vs pose annotations), strict-parse
validation before placement (a truncated SisFall file must be REJECTED, not
placed), subject-folder routing, and the deterministic provenance hash that
feeds data/datasets.lock.json -> metrics.json.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "fetch_drive_dataset.py"
_spec = importlib.util.spec_from_file_location("fetch_drive_dataset", _SCRIPT)
fdd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fdd)

SISFALL_LINE = "  12, -34, 8123, 1, 2, 3, 4, 5, 6;\n"
CASAS_LINE = "2010-11-04 00:03:50.209589 M003 ON\n"


def _write(p: Path, text: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


class TestSniff:
    def test_sisfall_nine_field(self, tmp_path):
        p = _write(tmp_path / "F01_SA01_R01.txt", SISFALL_LINE * 5)
        assert fdd.sniff(p) == "sisfall"

    def test_casas_event_lines(self, tmp_path):
        p = _write(tmp_path / "aruba_slice.txt", CASAS_LINE * 5)
        assert fdd.sniff(p) == "casas"

    def test_casas_without_subseconds(self, tmp_path):
        p = _write(tmp_path / "hh101.txt", "2012-01-01 08:00:00 D002 OPEN\n" * 3)
        assert fdd.sniff(p) == "casas"

    def test_pose_annotations_by_name(self, tmp_path):
        assert fdd.sniff(_write(tmp_path / "pose_keypoints.json", "{}")) == "pose"
        assert fdd.sniff(_write(tmp_path / "bbox_labels.csv", "x,y\n")) == "pose"

    def test_unknown_files_skipped(self, tmp_path):
        assert fdd.sniff(_write(tmp_path / "notes.txt", "hello world\n")) is None
        assert fdd.sniff(_write(tmp_path / "readme.md", "# hi\n")) is None
        assert fdd.sniff(_write(tmp_path / "empty.txt", "")) is None


class TestPlacement:
    def test_sisfall_routed_to_subject_folder(self, tmp_path, monkeypatch):
        monkeypatch.setattr(fdd, "SISFALL_DIR", tmp_path / "sisfall")
        src = _write(tmp_path / "raw" / "F01_SE06_R02.txt", SISFALL_LINE * 10)
        dest = fdd.place_sisfall(src)
        assert dest == tmp_path / "sisfall" / "SE06" / "F01_SE06_R02.txt"
        assert dest.is_file()

    def test_subject_from_parent_dir_when_not_in_name(self, tmp_path, monkeypatch):
        monkeypatch.setattr(fdd, "SISFALL_DIR", tmp_path / "sisfall")
        src = _write(tmp_path / "raw" / "SA07" / "trial3.txt", SISFALL_LINE * 10)
        assert fdd.place_sisfall(src).parent.name == "SA07"

    def test_truncated_sisfall_rejected_not_placed(self, tmp_path, monkeypatch):
        """A file that sniffs right but fails the REAL parser must raise, and
        nothing may land in the dataset dir — calibrate.py must never see it."""
        import pytest

        monkeypatch.setattr(fdd, "SISFALL_DIR", tmp_path / "sisfall")
        bad = _write(tmp_path / "raw" / "F02_SA01_R01.txt",
                     SISFALL_LINE * 3 + "12, 34\n")  # truncated final line
        with pytest.raises(ValueError):
            fdd.place_sisfall(bad)
        assert not (tmp_path / "sisfall").exists()


class TestProvenance:
    def test_aggregate_hash_deterministic_and_content_sensitive(self, tmp_path):
        a = _write(tmp_path / "a.txt", "one")
        b = _write(tmp_path / "b.txt", "two")
        h1 = fdd.aggregate_sha256([a, b])
        h2 = fdd.aggregate_sha256([b, a])  # order-independent (sorted inside)
        assert h1 == h2 and len(h1) == 64
        b.write_text("changed")
        assert fdd.aggregate_sha256([a, b]) != h1

    def test_lock_upsert_preserves_other_datasets(self, tmp_path, monkeypatch):
        lock = tmp_path / "datasets.lock.json"
        lock.write_text(json.dumps({"sisfall": {"sha256": "keepme"}}))
        monkeypatch.setattr(fdd, "LOCK_PATH", lock)
        f = _write(tmp_path / "aruba.txt", CASAS_LINE)
        fdd.update_lock("casas", [f], "https://example.test/folder", "WSU CASAS")
        doc = json.loads(lock.read_text())
        assert doc["sisfall"]["sha256"] == "keepme"      # untouched
        assert doc["casas"]["files"] == 1
        assert doc["casas"]["source_url"] == "https://example.test/folder"
        assert len(doc["casas"]["sha256"]) == 64
