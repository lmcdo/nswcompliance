"""scripts/refresh_bushfire_new_areas.py: additive only. Opt-in real database run: PYTEST_REAL_DB=1 PYTEST_REAL_HTTP=1 DATABASE_URL=... pytest -o addopts= -m database"""
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import refresh_bushfire_new_areas as rb  # noqa: E402

POLY = {"type": "Polygon", "coordinates": [[[151.0, -33.0], [151.1, -33.0], [151.1, -33.1], [151.0, -33.0]]]}


def test_rows_are_built_exactly_like_the_loader_and_unusable_features_are_skipped():
    feats = [{"properties": {"OBJECTID": 5, "d_Category": 1.0}, "geometry": POLY},
             {"properties": {"OBJECTID": 6, "d_Category": None}, "geometry": POLY},
             {"properties": {"OBJECTID": 7}, "geometry": None},
             {"properties": {"d_Category": 1}, "geometry": POLY}]
    rows = rb.build_rows(feats)
    assert [r[6] for r in rows] == [5, 6]
    assert rows[0][:6] == ("unknown", None, "bushfire", "1.0", None, None) and rows[1][3] is None and rows[0][7].startswith("MULTIPOLYGON")


class _Cur:
    def __init__(self):
        self.sql = []

    def execute(self, sql, args=None):
        self.sql.append(sql)


class _Conn:
    def __init__(self):
        self.cur, self.closed = _Cur(), False

    def cursor(self):
        return self.cur

    def commit(self):
        pass

    def close(self):
        self.closed = True


def test_a_dry_run_writes_nothing_and_the_connection_is_closed(monkeypatch, capsys):
    conn = _Conn()
    monkeypatch.setenv("DATABASE_URL", "x")
    monkeypatch.setattr(rb.psycopg2, "connect", lambda *a, **k: conn)
    monkeypatch.setattr(rb, "MIN_LIVE_AREAS", 3)
    monkeypatch.setattr(rb, "live_ids", lambda: {1, 2, 3, 4})
    monkeypatch.setattr(rb, "held_ids", lambda cur: {1, 2, 9})
    assert rb.main([]) == 0
    out = capsys.readouterr().out
    assert "NEW (to add) 2" in out and "gone from live (NOT touched) 1" in out and "DRY RUN" in out
    assert not any("INSERT" in q.upper() or "DELETE" in q.upper() for q in conn.cur.sql) and conn.closed


def test_an_empty_or_short_live_id_list_stops_the_run_with_failure_and_writes_nothing(monkeypatch, capsys):
    """Review case: the service replies with an error, live_ids() is empty, and a run would report every held area as gone and exit 0."""
    conn = _Conn()
    monkeypatch.setenv("DATABASE_URL", "x")
    monkeypatch.setattr(rb.psycopg2, "connect", lambda *a, **k: conn)
    monkeypatch.setattr(rb, "held_ids", lambda cur: {1, 2, 9})
    for live in (set(), {1, 2, 3}):
        monkeypatch.setattr(rb, "live_ids", lambda live=live: live)
        assert rb.main(["--apply"]) == 1
        assert "STOPPED" in capsys.readouterr().out
    assert not any("INSERT" in q.upper() for q in conn.cur.sql) and conn.closed


def test_the_only_write_the_script_can_make_is_an_insert_that_ignores_existing_rows():
    src = (REPO / "scripts" / "refresh_bushfire_new_areas.py").read_text(encoding="utf-8")
    assert "ON CONFLICT (instrument_key, layer_type, source_oid) DO NOTHING" in src
    code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith(("#", '"""')))
    assert "DELETE FROM" not in code.upper().replace("DELETES NOTHING", "") and "UPDATE spatial_overlays" not in code


@pytest.mark.database
@pytest.mark.integration
def test_the_real_dry_run_counts_against_the_live_map_and_the_table():
    if os.environ.get("PYTEST_REAL_DB") != "1" or os.environ.get("PYTEST_REAL_HTTP") != "1" or not os.environ.get("DATABASE_URL"):
        pytest.skip("needs PYTEST_REAL_DB=1, PYTEST_REAL_HTTP=1 and DATABASE_URL; not a pass")
    import psycopg2

    live = rb.live_ids()
    if len(live) < 100000:
        pytest.skip("the live service did not return its id list; not a pass")
    conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=20)
    try:
        conn.set_session(readonly=True, autocommit=True)
        held = rb.held_ids(conn.cursor())
    finally:
        conn.close()
    assert len(held) > 200000 and len(live - held) < 20000
