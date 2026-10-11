"""Single-site proofs against the REAL cadastre, read-only (DQ-143)."""
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

pytestmark = pytest.mark.database
_REAL = os.environ.get("PYTEST_REAL_DB") == "1"
SITES = {s["precinct_id"]: s for s in json.loads(
    (Path(__file__).resolve().parents[1] / "data" / "site_chapters" / "lot_sites.json").read_text(encoding="utf-8"))["sites"]}


@pytest.fixture
def ro_cursor():
    if not _REAL:
        pytest.skip("Real-DB test. Run with: PYTEST_REAL_DB=1 pytest -m database -o addopts= <file>")
    import dq_db
    conn = dq_db.connect()
    try:
        yield conn.cursor()
    finally:
        conn.close()


def test_445_canterbury_road_lots_match_the_stated_area(ro_cursor):
    import build_site_boundaries as b
    r = b.prove(ro_cursor, SITES["11.12"])
    assert r["ok"] and r["lots_listed"] == 9 and abs(r["area_m2"] - 4414) < 50


def test_leichhardt_is_held_because_its_lots_no_longer_exist(ro_cursor):
    import build_site_boundaries as b
    r = b.prove(ro_cursor, SITES["Leichhardt Amendment 1"])
    assert not r["ok"] and r["checks"]["2_lots"] is False
