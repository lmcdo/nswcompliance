"""fetch_dcp_setbacks against the real database: scope and unit, as a user receives them.

prior-art-checked: tests/test_conveyancing_db.py covers the same rules with fixture rows; the DQ-99 probe's real-db
test checks the probe runs. Neither calls the serve path against production rows, which is where a stored unit
or an applicability value the fixtures never imagined would show up.

WHAT CAN GO WRONG HERE
----------------------
1. A precinct-only rule is returned for a whole council: the skip matches a literal, and a renamed or re-cased
   applicability value would walk straight past it. So this asks the serve path, for every council that holds a
   current precinct_specific row, and requires none to come back.
2. A number prints in the wrong unit: the wording helper formats from the row's unit, and only real rows show the
   units actually stored (spaces/dwelling, %, m2, hours). So every served number from councils storing a unit
   other than metres must carry that unit in its requirement text.

Run:

    PYTEST_REAL_DB=1 python -m pytest -m database tests/test_conveyancing_db_served_scope_real_db.py -o addopts=

The opt-in is required because conftest_mocks stubs psycopg2 by default.
"""
from __future__ import annotations

import os
import pathlib
import sys

import pytest

_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "scripts"))

pytestmark = pytest.mark.database

_SERVED = "is_current = TRUE AND (needs_review IS NULL OR needs_review = FALSE)"


def _connect():
    from scripts.check_council_completeness import _load_env
    _load_env()
    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not url:
        pytest.skip("no DATABASE_URL")
    import psycopg2
    conn = psycopg2.connect(url, connect_timeout=20)
    with conn.cursor() as cur:
        cur.execute("SET statement_timeout = '30s'")
    return conn


def _served(conn, lga: str) -> list[dict]:
    import conveyancing_db as cdb
    res = cdb.fetch_dcp_setbacks(conn, lga, raise_on_error=True) or {}
    return (res.get("setbacks") or []) + (res.get("sd_setbacks") or [])


def test_no_council_is_served_a_precinct_only_rule():
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT DISTINCT lga FROM dcp_setback_controls "
                        f"WHERE applicability = 'precinct_specific' AND {_SERVED} ORDER BY lga")
            lgas = [r[0] for r in cur.fetchall()]
        if not lgas:
            pytest.skip("no current precinct_specific rows exist, so there is nothing for the skip to act on")
        leaked = [(lga, e.get("semantic_type")) for lga in lgas for e in _served(conn, lga)
                  if (e.get("applicability") or "").strip().lower() == "precinct_specific"]
    finally:
        conn.close()
    assert not leaked, f"precinct-only rules served council-wide: {leaked}"


def test_every_served_number_prints_in_its_stored_unit():
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT DISTINCT lga FROM dcp_setback_controls "
                        f"WHERE {_SERVED} AND COALESCE(TRIM(unit), '') NOT IN ('', 'm') "
                        f"AND (value_min IS NOT NULL OR value_max IS NOT NULL) ORDER BY lga")
            lgas = [r[0] for r in cur.fetchall()]
        assert lgas, "no served number carries a unit other than metres, so this test would prove nothing"
        checked, wrong = 0, []
        for lga in lgas:
            for e in _served(conn, lga):
                unit = (e.get("unit") or "").strip()
                if not unit or (e.get("value_min") is None and e.get("value_max") is None):
                    continue
                checked += 1
                if unit not in (e.get("requirement") or ""):
                    wrong.append((lga, e.get("semantic_type"), unit, e.get("requirement")))
    finally:
        conn.close()
    assert checked, "the serve path returned no numbers for councils that store non-metre units"
    assert not wrong, f"{len(wrong)} of {checked} served numbers print without their unit: {wrong[:5]}"
