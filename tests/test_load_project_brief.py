"""The brief loader reads a JSONL file and rejects anything the table's constraints would reject.

prior-art-checked: new module under test; the database half is exercised by the dry run documented in the loader, which is read-only.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import load_project_brief as lpb  # noqa: E402


def row(**over):
    r = dict(council="campbelltown", zone_group="R2", dev_type="dwelling_house", row_type="front_setback", rank=1,
             provision_id=253257, verdict="APPLIES", reason="no condition fails")
    r.update(over)
    return r


def write(tmp_path, rows, extra=""):
    p = tmp_path / "briefs.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in rows) + extra, encoding="utf-8")
    return str(p)


def test_a_valid_row_is_read(tmp_path):
    rows, bad = lpb.read_rows(write(tmp_path, [row()]))
    assert len(rows) == 1 and bad == []


def test_rank_outside_one_to_five_is_rejected(tmp_path):
    rows, bad = lpb.read_rows(write(tmp_path, [row(rank=6), row(rank=0), row(rank=5)]))
    assert [r["rank"] for r in rows] == [5]
    assert bad == [1, 2]


def test_unknown_zone_group_dev_type_or_row_type_is_rejected(tmp_path):
    rows, bad = lpb.read_rows(write(tmp_path, [row(zone_group="R9"), row(dev_type="shed"), row(row_type="colour")]))
    assert rows == [] and bad == [1, 2, 3]


def test_a_verdict_other_than_applies_or_might_is_rejected(tmp_path):
    rows, bad = lpb.read_rows(write(tmp_path, [row(verdict="NOT"), row(verdict="MIGHT")]))
    assert [r["verdict"] for r in rows] == ["MIGHT"] and bad == [1]


def test_a_zero_provision_id_or_blank_council_is_rejected(tmp_path):
    rows, bad = lpb.read_rows(write(tmp_path, [row(provision_id=0), row(council="")]))
    assert rows == [] and bad == [1, 2]


def test_blank_lines_are_skipped_and_broken_json_is_reported(tmp_path):
    rows, bad = lpb.read_rows(write(tmp_path, [row()], extra="\n{not json\n"))
    assert len(rows) == 1 and bad == [3]


def test_apply_without_the_confirm_flag_writes_nothing_and_exits():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "load_project_brief.py"), "x.jsonl", "--apply"],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode != 0
    assert "--confirm-production-write" in (r.stdout + r.stderr)


# --- real layer: the dry run against the live database, read-only -----------------------------------------------
import os  # noqa: E402

import pytest  # noqa: E402


@pytest.mark.database
@pytest.mark.skipif(not (os.environ.get("PYTEST_REAL_DB") and os.environ.get("DATABASE_URL")),
                    reason="needs PYTEST_REAL_DB=1 and DATABASE_URL; the dry run opens a read-only session")
def test_dry_run_reads_the_database_and_writes_nothing(tmp_path):
    f = write(tmp_path, [row()])
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "load_project_brief.py"), f],
                       capture_output=True, text=True, timeout=120, env=dict(os.environ))
    out = r.stdout + r.stderr
    assert "mode: dry run (read-only)" in out
    assert "Nothing written" in out or "does not exist" in out
