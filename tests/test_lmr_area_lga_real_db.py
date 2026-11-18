"""Real-database check of the council fallback. Opt in: PYTEST_REAL_DB=1 DATABASE_URL=... pytest -o addopts= -m database

Read-only. (conftest_mocks stubs psycopg2 by default, so a database test would otherwise get a MagicMock.)
Part 2 also calls the live state boundary service; a timeout there skips that lot, it is not a failure of the fallback.
"""
import os
import random

import pytest

from services import lmr_area_inputs as inp
from services import lmr_area_lga as lga

EXCLUDED = ["BATHURST REGIONAL", "BLUE MOUNTAINS", "HAWKESBURY", "WOLLONDILLY"]


def _conn():
    if os.environ.get("PYTEST_REAL_DB") != "1" or not os.environ.get("DATABASE_URL"):
        pytest.skip("real database test: run with PYTEST_REAL_DB=1 DATABASE_URL=... pytest -o addopts= -m database")
    import psycopg2

    c = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=20)
    c.set_session(readonly=True, autocommit=True)
    cur = c.cursor()
    cur.execute("SET statement_timeout = '30000'")
    return c, cur


@pytest.mark.database
@pytest.mark.integration
def test_points_in_the_four_excluded_councils_resolve_to_that_council():
    c, cur = _conn()
    try:
        for name in EXCLUDED:
            cur.execute("SELECT ST_Y(ST_PointOnSurface(geom)), ST_X(ST_PointOnSurface(geom)) FROM lot_search_index "
                        "WHERE lga_name = %s LIMIT 400", (name,))
            pts = cur.fetchall()
            random.Random(20261118).shuffle(pts)
            got = [lga.lga_from_snapshot(lat, lng) for lat, lng in pts[:8]]
            assert len(pts) >= 8, name
            assert all(g is None or g[0] == name for g in got), (name, got)          # never the wrong council
            assert sum(g is not None for g in got) >= 6, (name, got)                  # and mostly sure (a border lot may say nothing)
    finally:
        c.close()


@pytest.mark.database
@pytest.mark.integration
def test_points_shifted_into_roads_in_the_excluded_councils_never_get_a_different_council_than_the_live_service():
    """A point 30-60 m off a lot (a road reserve, or geocode drift) is where a neighbour's lots could be the nearest: no wrong council allowed."""
    c, cur = _conn()
    try:
        pts = []
        for name in EXCLUDED:
            cur.execute("SELECT ST_Y(ST_PointOnSurface(geom)), ST_X(ST_PointOnSurface(geom)) FROM lot_search_index "
                        "WHERE lga_name = %s LIMIT 400", (name,))
            rows = cur.fetchall()
            random.Random(11).shuffle(rows)
            for lat, lng in rows[:4]:
                dlat, dlng = random.Random(lat).choice([(0.0003, 0), (-0.0003, 0), (0, 0.0004), (0, -0.0004), (0.0006, 0.0006), (-0.0006, -0.0006)])
                pts.append((lat + dlat, lng + dlng))
    finally:
        c.close()
    wrong = []
    for lat, lng in pts:
        snap = lga.lga_from_snapshot(lat, lng)
        answered, live = inp._lga_live(lat, lng)
        if snap is not None and answered and live is not None and snap[0].upper() != live.upper():
            wrong.append((snap[0], live, lat, lng))
    assert wrong == [], wrong


@pytest.mark.database
@pytest.mark.integration
def test_the_snapshot_agrees_with_the_live_service_wherever_both_answer():
    c, cur = _conn()
    try:
        cur.execute("SELECT lga_name, ST_Y(ST_PointOnSurface(geom)), ST_X(ST_PointOnSurface(geom)) FROM lot_search_index "
                    "TABLESAMPLE SYSTEM (0.02) LIMIT 200")
        rows = cur.fetchall()
    finally:
        c.close()
    random.Random(20261118).shuffle(rows)
    both = disagree = 0
    for _name, lat, lng in rows[:20]:
        answered, live = inp._lga_live(lat, lng)
        snap = lga.lga_from_snapshot(lat, lng)
        if live is None or snap is None:
            continue
        both += 1
        disagree += live.upper() != snap[0].upper()
    assert disagree == 0, f"{disagree} of {both} lots disagreed with the live service"
