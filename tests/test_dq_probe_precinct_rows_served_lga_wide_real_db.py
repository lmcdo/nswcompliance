"""The DQ-99 probe, against the real database and the real serve path.

WHAT CAN GO WRONG HERE, AND WHY IT NEEDS A REAL LAYER
-----------------------------------------------------
The probe's only job is to count rows a USER can see whose scope says they apply
somewhere smaller than the council. To do that it copies the guard clause from
`scripts/conveyancing_db.fetch_dcp_setbacks` -- the single read every surface
proxies.

A copied guard rots. When it does, the probe goes on returning a number and the
number stops describing anything anyone is shown. That is not hypothetical in
this repo: DQ-97's probe fell to zero on 2026-09-10 because its population was
drained by an operator approving rows, not because the defect was repaired, and
it read as green for a day.

So these tests check the two things a unit test cannot:

1. the probe's guard still matches the serve path's guard, in source;
2. `precinct_specific` is still a value the live CHECK constraint allows, so the
   probe is not querying for something that can no longer exist.

Run:

    PYTEST_REAL_DB=1 DATABASE_URL=<pooler url> python -m pytest -m database \\
        tests/test_dq_probe_precinct_rows_served_lga_wide_real_db.py -o addopts=

The opt-in is required because conftest_mocks stubs psycopg2 by default, so
without it this would assert against a MagicMock and pass for the wrong reason.
"""
from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys

import pytest

_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

pytestmark = pytest.mark.database

_PROBE = _ROOT / "scripts" / "dq_probe_precinct_rows_served_lga_wide.py"
_SERVE_PATH = _ROOT / "scripts" / "conveyancing_db.py"


def _database_url() -> str:
    from scripts.check_council_completeness import _load_env
    _load_env()
    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not url:
        pytest.skip("no DATABASE_URL")
    return url


def _norm(sql: str) -> str:
    return re.sub(r"\s+", " ", sql).strip().lower()


def test_the_probes_guard_still_matches_the_serve_paths_guard():
    """The rot check. If fetch_dcp_setbacks changes what it considers served and
    this probe does not, the probe measures a population no user sees."""
    serve = _norm(_SERVE_PATH.read_text(encoding="utf-8"))
    assert "from dcp_setback_controls" in serve, (
        "fetch_dcp_setbacks no longer reads dcp_setback_controls -- the probe's "
        "premise is gone, not just its guard")
    for clause in ("is_current = true",
                   "(needs_review is null or needs_review = false)"):
        assert clause in serve, (
            "the serve path no longer applies `" + clause + "`. The DQ-99 probe "
            "copies this guard; update scripts/dq_probe_precinct_rows_served_"
            "lga_wide.py to match, or its count stops describing what a user "
            "is shown.")
    probe = _norm(_PROBE.read_text(encoding="utf-8"))
    for clause in ("is_current = true",
                   "(needs_review is null or needs_review = false)"):
        assert clause in probe, "the probe has lost the serve path's guard: " + clause


def test_precinct_specific_is_still_an_allowed_applicability_value():
    """If the constraint stops allowing it, the probe would count zero forever
    and read as fixed."""
    import psycopg2
    conn = psycopg2.connect(_database_url(), connect_timeout=20)
    try:
        cur = conn.cursor()
        cur.execute("SET statement_timeout='30s'")
        cur.execute(
            "SELECT pg_get_constraintdef(con.oid) FROM pg_constraint con "
            "JOIN pg_class c ON c.oid = con.conrelid "
            "WHERE c.relname = 'dcp_setback_controls' "
            "  AND con.conname = 'dcp_setback_controls_applicability_check'")
        row = cur.fetchone()
    finally:
        conn.close()
    assert row, "the applicability CHECK constraint is gone"
    assert "'precinct_specific'" in row[0], (
        "precinct_specific is no longer an allowed applicability value, so the "
        "DQ-99 probe would report 0 forever regardless of what is served")


def test_the_probe_runs_and_its_exit_code_agrees_with_its_own_count():
    """Three states, not two: a clean run exits 0 and says PASSED; a run that
    finds rows exits 1 and lists every one of them. A run that exits 1 while
    printing nothing would be the worst outcome -- red with no evidence."""
    env = dict(os.environ)
    env["DATABASE_URL"] = _database_url()
    proc = subprocess.run([sys.executable, str(_PROBE)], capture_output=True,
                          text=True, timeout=120, env=env, cwd=str(_ROOT))
    out = proc.stdout
    assert proc.returncode in (0, 1), (
        "probe exited " + str(proc.returncode) + " -- neither clean nor a "
        "finding, so nothing was measured:\n" + proc.stderr[:600])
    if proc.returncode == 0:
        assert "PASSED" in out
        return
    m = re.search(r"^(\d+) scope-limited row", out, re.M)
    assert m, "probe exited 1 without stating how many rows it found:\n" + out[:600]
    claimed = int(m.group(1))
    assert claimed > 0
    # Every row it counted must also be printed, or the count is unauditable.
    assert out.count("      scope: ") == claimed, (
        "probe claims " + str(claimed) + " rows but printed " +
        str(out.count("      scope: ")) + " of them")
