"""The brief's outreach checks: the pure helpers behind the recall and page-proof numbers.

prior-art-checked: new module under test; the database-backed checks report UNKNOWN when no database is reachable, which is asserted here.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import plan_brief_checks as pbc  # noqa: E402


def test_norm_keeps_letters_digits_dots_and_percent_only():
    assert pbc._norm("A 5.5 m  Setback; 30%!") == "a5.5msetback30%"
    assert pbc._norm(None) == ""


def test_wilson_lower_bound_is_below_the_point_estimate_and_rises_with_sample_size():
    small = pbc._wilson_lower(9, 10)
    large = pbc._wilson_lower(90, 100)
    assert small < 0.9 and large < 0.9
    assert large > small


def test_wilson_lower_bound_of_all_correct_is_below_one():
    assert 0.0 < pbc._wilson_lower(50, 50) < 1.0


def test_speed_check_is_unknown_without_a_deployment_address(monkeypatch):
    monkeypatch.delenv("PLAN_BRIEF_URL", raising=False)
    monkeypatch.setattr(pbc, "ROOT", Path("no-such-folder"))
    status, why = pbc.brief_speed()
    assert status == pbc.UNKNOWN
    assert "PLAN_BRIEF_URL" in why


def test_a_header_value_that_is_none_does_not_break_the_speed_check(monkeypatch):
    monkeypatch.setenv("PLAN_BRIEF_URL", "http://127.0.0.1:9")
    monkeypatch.delenv("PLAN_BRIEF_HEADERS", raising=False)
    status, _why = pbc.brief_speed()
    assert status in (pbc.UNKNOWN, pbc.FAIL)


# --- real layer: the database-backed checks against the live catalog, read-only ---------------------------------
import os  # noqa: E402

import pytest  # noqa: E402


@pytest.mark.database
@pytest.mark.skipif(not (os.environ.get("PYTEST_REAL_DB") and os.environ.get("DATABASE_URL")),
                    reason="needs PYTEST_REAL_DB=1 and DATABASE_URL; the checks only read")
def test_page_proof_check_returns_a_status_and_a_reason():
    status, why = pbc.brief_page_proof()
    assert status in (pbc.PASS, pbc.FAIL, pbc.UNKNOWN)
    assert isinstance(why, str) and why


# ---- OC-29: the heading read (a script's read of the council's own section headings; not an owner read) ----
import json  # noqa: E402

_COUNCILS = ["wollongong", "penrith", "waverley", "campbelltown", "ashfield"]
_TOPICS = ["front_setback", "side_setback", "rear_setback", "car_parking", "landscaping_min", "private_open_space"]


def _read_rows(red_at=()):
    rows = []
    for i, (c, t) in enumerate([(c, t) for c in _COUNCILS for t in _TOPICS], start=1):
        rows.append({"n": i, "council": c, "dev_type": "dwelling_house", "zone_group": "R2", "row_type": t,
                     "first_provision_id": 1000 + i, "flag": "red" if i in red_at else "none", "section": "x"})
    return rows


def _setup(monkeypatch, tmp_path, rows, live=None):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "plan_brief_heading_read_2026-11-09.json").write_text(json.dumps({"named_councils": sorted({r["council"] for r in rows}), "rows": rows}), encoding="utf-8")
    monkeypatch.setattr(pbc, "ROOT", tmp_path)

    class _Cur:
        def __enter__(self): return self
        def __exit__(self, *a): return False

    class _Conn:
        def cursor(self): return _Cur()
        def close(self): pass

    monkeypatch.setattr(pbc, "_conn", lambda: _Conn())
    live = live if live is not None else {(r["council"], r["dev_type"], r["zone_group"], r["row_type"]): [r["first_provision_id"]] for r in rows}
    monkeypatch.setattr(pbc, "_brief_top5", lambda cur: live)


def test_heading_read_passes_with_no_flagged_rows(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, _read_rows())
    assert pbc.heading_read()[0] == pbc.PASS


def test_heading_read_passes_with_one_flagged_row_and_fails_with_two(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, _read_rows(red_at=(3,)))
    assert pbc.heading_read()[0] == pbc.PASS
    second = tmp_path / "second"
    second.mkdir()
    _setup(monkeypatch, second, _read_rows(red_at=(3, 9)))
    assert pbc.heading_read()[0] == pbc.FAIL


def test_heading_read_fails_when_a_first_clause_changed(monkeypatch, tmp_path):
    rows = _read_rows()
    live = {(r["council"], r["dev_type"], r["zone_group"], r["row_type"]): [r["first_provision_id"]] for r in rows}
    live[("wollongong", "dwelling_house", "R2", "front_setback")] = [999999]
    _setup(monkeypatch, tmp_path, rows, live)
    status, why = pbc.heading_read()
    assert status == pbc.FAIL and "STALE" in why


def test_heading_read_fails_on_duplicate_rows_bad_flags_and_missing_file(monkeypatch, tmp_path):
    rows = _read_rows()
    dup = [dict(r) for r in rows]
    dup[1]["n"] = 1                      # two rows numbered 1
    _setup(monkeypatch, tmp_path, dup)
    assert pbc.heading_read()[0] == pbc.FAIL
    bad = _read_rows()
    bad[0]["flag"] = "maybe"
    (tmp_path / "data" / "plan_brief_heading_read_2026-11-09.json").write_text(json.dumps({"named_councils": _COUNCILS, "rows": bad}), encoding="utf-8")
    assert pbc.heading_read()[0] == pbc.FAIL
    (tmp_path / "data" / "plan_brief_heading_read_2026-11-09.json").write_text("{}", encoding="utf-8")
    assert pbc.heading_read()[0] == pbc.FAIL
    (tmp_path / "data" / "plan_brief_heading_read_2026-11-09.json").unlink()
    assert pbc.heading_read()[0] == pbc.FAIL

def test_heading_read_needs_at_least_thirty_rows(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, _read_rows()[:29])
    status, why = pbc.heading_read()
    assert status == pbc.FAIL and "at least 30" in why

def test_heading_read_fails_on_wrong_types_and_on_councils_outside_the_named_list(monkeypatch, tmp_path):
    rows = _read_rows()
    rows[2]["n"] = None
    _setup(monkeypatch, tmp_path, rows)
    status, why = pbc.heading_read()
    assert status == pbc.FAIL and "wrongly typed" in why
    other = tmp_path / "other"
    other.mkdir()
    _setup(monkeypatch, other, _read_rows())
    path = other / "data" / "plan_brief_heading_read_2026-11-09.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["named_councils"] = _COUNCILS[:-1]          # a council in the rows is not in the named list
    path.write_text(json.dumps(doc), encoding="utf-8")
    status, why = pbc.heading_read()
    assert status == pbc.FAIL and "named_councils" in why

def test_recorded_speed_passes_fails_and_rejects_a_short_record(monkeypatch, tmp_path):
    monkeypatch.delenv("PLAN_BRIEF_URL", raising=False)
    (tmp_path / "data").mkdir()
    f = tmp_path / "data" / "plan_brief_speed_2026-11-09.json"
    monkeypatch.setattr(pbc, "ROOT", tmp_path)
    f.write_text(json.dumps({"calls": 72, "p95_s": 0.41, "bar_s": 2.0, "p50_s": 0.19, "measured_on": "2026-11-09"}), encoding="utf-8")
    assert pbc.brief_speed()[0] == pbc.PASS
    f.write_text(json.dumps({"calls": 72, "p95_s": 2.5, "bar_s": 2.0}), encoding="utf-8")
    assert pbc.brief_speed()[0] == pbc.FAIL
    f.write_text(json.dumps({"calls": 10, "p95_s": 0.1, "bar_s": 2.0}), encoding="utf-8")
    assert pbc.brief_speed()[0] == pbc.FAIL
    f.write_text("{}", encoding="utf-8")
    assert pbc.brief_speed()[0] == pbc.UNKNOWN
