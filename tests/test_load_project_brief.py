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


# --- --replace-cells: the file is the whole answer for every cell it names ---------------------------------------
def cell(**over):
    c = dict(council="hornsby", zone_group="R2", dev_type="dwelling_house", row_type="front_setback", empty=True)
    c.update(over)
    return c


def test_read_cells_reads_picks_and_empty_cell_lines(tmp_path):
    picks, empties, bad = lpb.read_cells(write(tmp_path, [row(rank=1), row(rank=2, provision_id=253258), cell(row_type="deep_soil_min")]))
    assert [p["rank"] for p in picks] == [1, 2]
    assert [e["row_type"] for e in empties] == ["deep_soil_min"] and bad == []


def test_read_cells_rejects_an_empty_line_with_an_unknown_row_type_or_blank_council(tmp_path):
    picks, empties, bad = lpb.read_cells(write(tmp_path, [cell(row_type="colour"), cell(council=""), cell(zone_group="R9")]))
    assert picks == [] and empties == [] and bad == [1, 2, 3]


def test_read_cells_still_applies_the_pick_rules(tmp_path):
    picks, empties, bad = lpb.read_cells(write(tmp_path, [row(rank=6), row(verdict="NOT"), row(provision_id=0)]))
    assert picks == [] and bad == [1, 2, 3]


def test_a_flag_that_is_not_true_is_not_an_empty_marker(tmp_path):
    picks, empties, bad = lpb.read_cells(write(tmp_path, [cell(empty=False)]))
    assert empties == [] and bad == [1]          # it has no rank or provision_id, so it is not a valid pick either


def test_replace_problems_accepts_ranks_one_to_n_and_a_separate_empty_cell():
    assert lpb.replace_problems([row(rank=1), row(rank=2, provision_id=253258)], [cell(row_type="deep_soil_min")]) == []


def test_replace_problems_rejects_a_gap_or_a_repeat_in_the_ranks():
    assert lpb.replace_problems([row(rank=1), row(rank=3)], [])
    assert lpb.replace_problems([row(rank=1), row(rank=1)], [])
    assert lpb.replace_problems([row(rank=2)], [])


def test_replace_problems_rejects_a_cell_that_is_both_picked_and_empty():
    assert lpb.replace_problems([row(rank=1)], [cell(row_type="front_setback", council="campbelltown")])


def test_replace_problems_rejects_the_same_empty_cell_named_twice():
    assert lpb.replace_problems([], [cell(), cell()])


def test_replace_problems_judges_each_cell_on_its_own():
    # two different cells, each rank 1..n: fine; ranks are never pooled across cells
    assert lpb.replace_problems([row(rank=1), row(rank=1, row_type="side_setback")], []) == []


def _run(args, tmp_path, rows):
    f = write(tmp_path, rows)
    return subprocess.run([sys.executable, str(ROOT / "scripts" / "load_project_brief.py"), f, *args],
                          capture_output=True, text=True, timeout=60)


def test_replace_apply_without_a_backup_path_writes_nothing_and_exits(tmp_path):
    r = _run(["--replace-cells", "--apply", "--confirm-production-write"], tmp_path, [row()])
    assert r.returncode != 0
    assert "--backup-to" in (r.stdout + r.stderr) and "Nothing written" in (r.stdout + r.stderr)


def test_replace_cells_cannot_be_combined_with_remove_build(tmp_path):
    r = _run(["--replace-cells", "--remove-build", "applies-when-x"], tmp_path, [row()])
    assert r.returncode != 0 and "separate operations" in (r.stdout + r.stderr)


def test_the_committed_picks_file_is_valid_and_every_cell_runs_one_to_n():
    picks, empties, bad = lpb.read_cells(str(ROOT / "data" / "plan_brief_picks_2026-11-10.jsonl"))
    assert bad == [] and picks and empties
    assert lpb.replace_problems(picks, empties) == []
    assert {p["zone_group"] for p in picks} == {"R2"} and {p["dev_type"] for p in picks} == {"dwelling_house"}
    assert len({lpb.cell_key(p) for p in picks} | {lpb.cell_key(e) for e in empties}) == 100   # 10 councils x 10 topics


def test_a_rank_or_provision_id_that_is_not_a_whole_number_is_rejected_not_truncated(tmp_path):
    picks, empties, bad = lpb.read_cells(write(tmp_path, [row(rank=1.9), row(provision_id=240903.9), row(rank=True), row(rank="2")]))
    assert picks == [] and bad == [1, 2, 3, 4]


def test_an_empty_marker_that_also_carries_pick_fields_is_rejected_not_obeyed(tmp_path):
    picks, empties, bad = lpb.read_cells(write(tmp_path, [cell(rank=1, provision_id=262143, verdict="MIGHT"), cell(reason="x")]))
    assert picks == [] and empties == [] and bad == [1, 2]


def test_no_committed_pick_is_on_the_served_skip_list():
    # a pick the page then drops would leave its cell empty while the file says it is filled
    skip = set(json.loads((ROOT / "frontend-nextjs" / "shared" / "brief-scope.json").read_text(encoding="utf-8"))["excluded_provision_ids"])
    picks, _, _ = lpb.read_cells(str(ROOT / "data" / "plan_brief_picks_2026-11-10.jsonl"))
    assert [p["provision_id"] for p in picks if p["provision_id"] in skip] == []


def test_the_same_clause_picked_at_two_ranks_of_one_cell_is_a_problem():
    assert lpb.replace_problems([row(rank=1, provision_id=5), row(rank=2, provision_id=5)], [])
    assert lpb.replace_problems([row(rank=1, provision_id=5), row(rank=1, row_type="side_setback", provision_id=5)], []) == []   # different cells may share a clause


COLS = ["id", "council", "zone_group", "dev_type", "row_type", "rank", "provision_id", "verdict", "reason", "build_id", "built_at"]
KEY = ("hornsby", "R2", "dwelling_house", "front_setback")


def old_row(rank, pid):
    return (1000 + rank, "hornsby", "R2", "dwelling_house", "front_setback", rank, pid, "MIGHT", "why", "applies-when-x", "2026-11-08 07:11:29+00:00")


def test_a_backup_names_its_cells_and_keeps_every_saved_row(tmp_path):
    payload = lpb.backup_payload(COLS, [old_row(1, 5), old_row(2, 6)], [KEY, ("hornsby", "R2", "dwelling_house", "deep_soil_min")])
    f = tmp_path / "b.json"
    f.write_text(json.dumps(payload), encoding="utf-8")
    cells, rows, problems = lpb.read_backup(str(f))
    assert problems == [] and len(rows) == 2
    assert KEY in cells and ("hornsby", "R2", "dwelling_house", "deep_soil_min") in cells    # a cell that had no rows is restored empty


def test_a_backup_with_a_row_outside_its_named_cells_is_refused(tmp_path):
    payload = lpb.backup_payload(COLS, [old_row(1, 5)], [("hornsby", "R2", "dwelling_house", "side_setback")])
    f = tmp_path / "b.json"
    f.write_text(json.dumps(payload), encoding="utf-8")
    assert lpb.read_backup(str(f))[2]


def test_a_backup_that_names_no_cells_is_refused(tmp_path):
    f = tmp_path / "b.json"
    f.write_text(json.dumps({"cells": [], "rows": []}), encoding="utf-8")
    assert lpb.read_backup(str(f))[2]


def test_restore_apply_without_the_confirm_flag_writes_nothing_and_exits(tmp_path):
    f = tmp_path / "b.json"
    f.write_text(json.dumps(lpb.backup_payload(COLS, [old_row(1, 5)], [KEY])), encoding="utf-8")
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "load_project_brief.py"), "--restore-from", str(f), "--apply"],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode != 0 and "--confirm-production-write" in (r.stdout + r.stderr)
