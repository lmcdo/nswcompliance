"""Map layers are checked against the whole lot, not only the address point.

The property route asked `ST_Contains(geom, address point)` for flood, riparian, wetlands and the
other hazard layers, so a lot whose back half is flood mapped read "No" when the address point sat
outside the flood polygon (code-quality review, served rules finding 0, P1).

Real lots, read-only: each was picked from production because its own point-on-surface lies outside a
flood polygon that overlaps the lot by more than 20 m2 (found by SQL, 2026-10-26, not typed in).

    PYTEST_REAL_DB=1 pytest -m database tests/test_spatial_overlays_whole_lot_real_db.py -v
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from dq_db import main_checkout  # noqa: E402

_REAL_DB_REQUESTED = os.environ.get("PYTEST_REAL_DB") == "1"
if _REAL_DB_REQUESTED:
    load_dotenv(main_checkout() / ".env")

pytestmark = pytest.mark.database

SQL_FILE = ROOT / "frontend-nextjs" / "lib" / "spatial-overlays-sql.ts"
LOTS = ["8//DP575940", "1//DP854205", "2//DP221940"]


def _route_sql() -> str:
    """The exact SQL text the route runs, with $1/$2 as psycopg placeholders."""
    m = re.search(r"SPATIAL_OVERLAYS_SQL = `(.*?)`", SQL_FILE.read_text(encoding="utf-8"), re.S)
    assert m, "SPATIAL_OVERLAYS_SQL not found"
    return m.group(1).replace("$1", "%(lon)s").replace("$2", "%(lat)s")


@pytest.fixture(scope="module")
def cur():
    if not _REAL_DB_REQUESTED:
        pytest.skip("Real-DB test. Run with: PYTEST_REAL_DB=1 pytest -m database "
                    "tests/test_spatial_overlays_whole_lot_real_db.py")
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        pytest.skip("PYTEST_REAL_DB=1 set but no DATABASE_URL/SUPABASE_DB_URL available.")
    import psycopg2

    conn = psycopg2.connect(dsn, connect_timeout=30)
    conn.set_session(readonly=True, autocommit=True)
    c = conn.cursor()
    c.execute("SET statement_timeout = '30s'")
    yield c
    conn.close()


def _point(cur, lot: str) -> tuple[float, float]:
    cur.execute("SELECT ST_X(p), ST_Y(p) FROM (SELECT ST_PointOnSurface(geom) p "
                "FROM nsw_cadastre_lots WHERE lotidstring = %s) q", (lot,))
    row = cur.fetchone()
    assert row, f"lot {lot} not in nsw_cadastre_lots"
    return row


@pytest.mark.parametrize("lot", LOTS)
def test_point_outside_flood_but_lot_overlaps_reads_flood(cur, lot):
    lon, lat = _point(cur, lot)
    cur.execute("SELECT count(*) FROM spatial_overlays WHERE layer_type = 'flood' "
                "AND ST_Contains(geom, ST_SetSRID(ST_Point(%s, %s), 4326))", (lon, lat))
    assert cur.fetchone()[0] == 0, "fixture no longer valid: the point itself is in a flood polygon"
    cur.execute(_route_sql(), {"lon": lon, "lat": lat})
    layers = [r[0] for r in cur.fetchall()]
    assert "flood" in layers, f"{lot}: flood overlaps the lot but the route query did not return it"


@pytest.mark.parametrize("lot", LOTS)
def test_value_layers_stay_at_the_point(cur, lot):
    """FSR / lot size / acid sulfate are read as one value; a neighbour's value must not join in."""
    lon, lat = _point(cur, lot)
    cur.execute("SELECT layer_type, value FROM spatial_overlays WHERE layer_type IN ('fsr','lot_size','acid_sulfate') "
                "AND ST_Contains(geom, ST_SetSRID(ST_Point(%s, %s), 4326)) ORDER BY 1, 2", (lon, lat))
    at_point = cur.fetchall()
    cur.execute(_route_sql(), {"lon": lon, "lat": lat})
    from_route = sorted(r for r in cur.fetchall() if r[0] in ("fsr", "lot_size", "acid_sulfate"))
    assert from_route == at_point


@pytest.mark.parametrize("lot", LOTS)
def test_lot_found_marker_reads_true_on_a_real_lot(cur, lot):
    lon, lat = _point(cur, lot)
    cur.execute(_route_sql(), {"lon": lon, "lat": lat})
    assert ("__lot_found", "true") in cur.fetchall()


def test_lot_found_marker_reads_false_off_the_cadastre(cur):
    """(0, 0) is in the Gulf of Guinea: no NSW lot can hold it, so the route must say not checked."""
    cur.execute(_route_sql(), {"lon": 0.0, "lat": 0.0})
    assert cur.fetchall() == [("__lot_found", "false")]
