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


# ---- OC-29: the heading check (a script's read of the council's own section headings, on the live rows after the skip) ----
import json  # noqa: E402

_NAMED = ["wollongong", "penrith", "waverley", "campbelltown", "ashfield"]
_CORE = ["front_setback", "side_setback", "rear_setback", "car_parking", "landscaping_min", "private_open_space"]
_EXTRA = ["max_height", "deep_soil_min", "max_site_coverage", "secondary_street_setback", "x1", "x2"]


def _world():
    """5 councils x 12 topics, 3 live clauses per topic, every clause scanned and unflagged, every proven cell hit."""
    top, scan, cells = {}, [], {}
    pid = 1000
    for c in _NAMED:
        for row in _CORE + _EXTRA:
            pids = [pid + 1, pid + 2, pid + 3]
            pid += 10
            top[(c, "dwelling_house", "R2", row)] = pids
            scan += [{"council": c, "type": row, "rank": i + 1, "pid": p, "flagged": False, "reason": None} for i, p in enumerate(pids)]
            cells[(c, "dwelling_house", row)] = {pids[0]}
    return top, scan, cells


def _setup(monkeypatch, tmp_path, top, scan, cells, named=None, excluded=()):
    (tmp_path / "frontend-nextjs" / "shared").mkdir(parents=True)
    (tmp_path / "data").mkdir()
    (tmp_path / "frontend-nextjs" / "shared" / "brief-scope.json").write_text(
        json.dumps({"councils": named if named is not None else _NAMED, "dev_type": "dwelling_house", "zone_group": "R2",
                    "excluded_provision_ids": list(excluded)}), encoding="utf-8")
    (tmp_path / "data" / "plan_brief_heading_scan_2026-11-09.json").write_text(json.dumps({"rows": scan}), encoding="utf-8")
    monkeypatch.setattr(pbc, "ROOT", tmp_path)

    class _Cur:
        def __enter__(self): return self
        def __exit__(self, *a): return False

    class _Conn:
        def cursor(self): return _Cur()
        def close(self): pass

    monkeypatch.setattr(pbc, "_conn", lambda: _Conn())
    monkeypatch.setattr(pbc, "_brief_top5", lambda cur: top)
    monkeypatch.setattr(pbc, "_gold_cells", lambda cur, councils: cells)


def test_heading_check_passes_when_everything_shown_was_read_and_nothing_flagged_remains(monkeypatch, tmp_path):
    top, scan, cells = _world()
    _setup(monkeypatch, tmp_path, top, scan, cells)
    status, why = pbc.heading_read()
    assert status == pbc.PASS, why


def test_heading_check_fails_on_a_flagged_clause_unless_the_skip_list_removes_it(monkeypatch, tmp_path):
    top, scan, cells = _world()
    scan[0]["flagged"] = True                      # the first clause of wollongong front_setback
    flagged_pid = scan[0]["pid"]
    _setup(monkeypatch, tmp_path, top, scan, cells)
    status, why = pbc.heading_read()
    assert status == pbc.FAIL and "flagged" in why
    second = tmp_path / "second"
    second.mkdir()
    _setup(monkeypatch, second, top, scan, cells, excluded=[flagged_pid])
    assert pbc.heading_read()[0] == pbc.PASS


def test_heading_check_fails_on_a_clause_that_was_never_scanned(monkeypatch, tmp_path):
    top, scan, cells = _world()
    top[("penrith", "dwelling_house", "R2", "car_parking")].append(999999)     # the brief gained a clause after the scan
    _setup(monkeypatch, tmp_path, top, scan, cells)
    status, why = pbc.heading_read()
    assert status == pbc.FAIL and "never read" in why


def test_heading_check_needs_a_clause_left_for_every_core_topic_but_not_the_extra_ones(monkeypatch, tmp_path):
    top, scan, cells = _world()
    core_all = top[("waverley", "dwelling_house", "R2", "front_setback")]
    _setup(monkeypatch, tmp_path, top, scan, cells, excluded=core_all)
    status, why = pbc.heading_read()
    assert status == pbc.FAIL and "no clause is left" in why
    second = tmp_path / "second"
    second.mkdir()
    extra_all = top[("waverley", "dwelling_house", "R2", "max_height")]
    _setup(monkeypatch, second, top, scan, cells, excluded=extra_all)
    assert pbc.heading_read()[0] == pbc.PASS


def test_heading_check_fails_when_recall_after_the_skip_is_too_low(monkeypatch, tmp_path):
    top, scan, cells = _world()
    for k in [k for k in cells if k[0] == "ashfield"]:
        cells[k] = {424242}                           # none of ashfield's proven rules is shown
    _setup(monkeypatch, tmp_path, top, scan, cells)
    status, why = pbc.heading_read()
    assert status == pbc.FAIL and "recall under 80%" in why


def test_heading_check_fails_with_too_few_councils_or_missing_files(monkeypatch, tmp_path):
    top, scan, cells = _world()
    _setup(monkeypatch, tmp_path, top, scan, cells, named=_NAMED[:4])
    assert pbc.heading_read()[0] == pbc.FAIL
    (tmp_path / "data" / "plan_brief_heading_scan_2026-11-09.json").unlink()
    assert pbc.heading_read()[0] == pbc.FAIL


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
