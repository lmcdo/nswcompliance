"""Standards rows an ALREADY-flagged amendment should have staled get their notice (DQ-96).

prior-art-checked: extends the W3 auto-stale tests (tests/test_sepp_auto_stale.py pins the fresh-transition
path, mark_dependent_standards_stale); nothing covered an instrument flagged before that path existed, and
nothing ran either path's SQL through a real driver.

mark_dependent_standards_stale fires only on a fresh needs_review transition. sepp_housing_2021 was flagged
on 2026-05-15, before that mechanism shipped (#839, 2026-07-29), so on 2026-09-14 its 33 standards rows
stored before the change still read stale_since IS NULL, as did 2 rows tied to the E&C Codes SEPP (flagged
2026-06-08): 35 standards serving with no notice that the law had changed.

Unit tests drive the functions, exec-extracted from the monitor's source, with a recording cursor. The
database tests run both functions for real against TEMPORARY fixture tables: Postgres searches the session's
temporary schema first, so the unqualified names resolve to the fixtures and no real table is read or
written. Opt in with PYTEST_REAL_DB=1 and DATABASE_URL.
"""
import datetime
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MON_SRC = (ROOT / "scripts" / "legislation_monitor.py").read_text(encoding="utf-8")


def _load():
    ns: dict = {}
    start = MON_SRC.index("STANDARDS_TABLES_BY_INSTRUMENT = {")
    end = MON_SRC.index("def send_telegram")
    exec(MON_SRC[start:end], ns)
    return ns


NS = _load()
backfill = NS["backfill_stale_for_flagged_instruments"]
mark_fresh = NS["mark_dependent_standards_stale"]

HOUSING_CHANGED = datetime.datetime(2026, 5, 15, 10, 54, tzinfo=datetime.timezone.utc)
EC_CHANGED = datetime.datetime(2026, 6, 8, 5, 31, tzinfo=datetime.timezone.utc)


# ── unit: the statements the sweep builds ──────────────────────────────────────────────────────────

class _Cursor:
    """fetchone answers the instrument_registry lookup from `flagged`; UPDATEs are recorded."""

    def __init__(self, flagged):
        self.flagged = flagged
        self.executed = []
        self.rowcount = 0
        self._last_key = None

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        if sql.lstrip().startswith("SELECT"):
            self._last_key = params[0]
        self.rowcount = 2

    def fetchone(self):
        return self.flagged.get(self._last_key)

    def close(self):
        pass


class _Conn:
    def __init__(self, flagged):
        self.cur = _Cursor(flagged)

    def cursor(self):
        return self.cur


def _updates(conn):
    return [(s, p) for s, p in conn.cur.executed if s.lstrip().startswith("UPDATE")]


def test_no_flagged_instrument_means_no_update():
    conn = _Conn({})
    assert backfill(conn) == [] and _updates(conn) == []


def test_the_notice_is_dated_from_the_detected_change_and_only_reaches_older_rows():
    conn = _Conn({"sepp_housing_2021": ("SEPP (Housing) 2021", "24 April 2026", HOUSING_CHANGED)})
    notes = backfill(conn)
    (sql, params), = _updates(conn)
    assert "housing_sepp_standards" in sql
    assert "stale_since IS NULL" in sql, "an existing notice must never be overwritten"
    assert "created_at < %s" in sql, "a row stored after the change may already reflect the amended text"
    assert params[0] == HOUSING_CHANGED and params[-1] == HOUSING_CHANGED, "dated from the change, not today"
    assert "NOW()" not in sql
    assert "SEPP (Housing) 2021" in params[1] and "2026-05-15" in params[1]
    assert notes and "STALE" in notes[0]


def test_each_instrument_stamps_only_its_own_rows():
    conn = _Conn({"sepp_exempt_complying_2008": ("E&C Codes SEPP", "15 May 2026", EC_CHANGED)})
    backfill(conn)
    sqls = [s for s, _ in _updates(conn)]
    housing = next(s for s in sqls if "housing_sepp_standards" in s)
    cdc = next(s for s in sqls if "cdc_eligibility_standards" in s)
    assert "exempt" in housing and "housing%" not in housing
    assert "ILIKE" not in cdc
    assert not any("source_document ILIKE '%%housing%%'" in s for s in sqls)


def test_the_monitor_runs_the_sweep_on_every_run():
    """Source pin: a sweep nothing calls would leave DQ-96 to recur for the next instrument."""
    main_src = MON_SRC[MON_SRC.index("def main():"):]
    assert "backfill_stale_for_flagged_instruments(conn)" in main_src
    assert main_src.index("backfill_stale_for_flagged_instruments(conn)") < main_src.index("conn.close()\n\n    changed")


# ── database: both paths through a real driver, on temporary fixture tables ─────────────────────────

@pytest.fixture()
def fixture_db():
    if os.environ.get("PYTEST_REAL_DB") != "1":
        pytest.skip("Real-DB test. Run with: PYTEST_REAL_DB=1 DATABASE_URL=... pytest -m database "
                    "tests/test_legislation_monitor_stale_backfill.py -o addopts=")
    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not url:
        pytest.skip("PYTEST_REAL_DB=1 set but no DATABASE_URL/SUPABASE_DB_URL available.")
    import psycopg2

    conn = psycopg2.connect(url, connect_timeout=20)
    conn.autocommit = False
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '30s'")
    cur.execute("""
        CREATE TEMPORARY TABLE instrument_registry (
            instrument_key text, instrument_label text, current_version text,
            last_changed timestamptz, needs_review boolean, is_active boolean) ON COMMIT DROP;
        CREATE TEMPORARY TABLE housing_sepp_standards (
            id int, source_document text, created_at timestamptz,
            stale_since timestamptz, stale_reason text) ON COMMIT DROP;
        CREATE TEMPORARY TABLE cdc_eligibility_standards (
            id int, created_at timestamptz, stale_since timestamptz, stale_reason text) ON COMMIT DROP;
    """)
    cur.execute("SELECT count(*) FROM pg_class WHERE relname IN ('instrument_registry', "
                "'housing_sepp_standards', 'cdc_eligibility_standards') AND relpersistence = 't'")
    assert cur.fetchone()[0] == 3, "fixture tables are not temporary; refusing to go on"
    cur.close()
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()


def _seed(conn, housing_flagged=True, ec_flagged=True):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO instrument_registry VALUES "
        "('sepp_housing_2021', 'SEPP (Housing) 2021', '24 April 2026', %s, %s, TRUE), "
        "('sepp_exempt_complying_2008', 'SEPP (Exempt and Complying Development Codes) 2008', '15 May 2026', %s, %s, TRUE)",
        (HOUSING_CHANGED, housing_flagged, EC_CHANGED, ec_flagged))
    cur.execute("""
        INSERT INTO housing_sepp_standards (id, source_document, created_at, stale_since, stale_reason) VALUES
            (1,  'SEPP (Housing) 2021',                                  '2026-01-03', NULL, NULL),
            (12, 'SEPP (Housing) 2021 - LMR Amendment',                  '2026-01-03', NULL, NULL),
            (34, 'State Environmental Planning Policy (Housing) 2021',   '2026-05-31', NULL, NULL),
            (36, 'State Environmental Planning Policy (Exempt and Complying Development Codes) 2008', '2026-05-31', NULL, NULL),
            (90, 'SEPP (Housing) 2021',                                  '2026-01-03', '2026-02-01', 'an earlier notice');
        INSERT INTO cdc_eligibility_standards (id, created_at, stale_since, stale_reason) VALUES
            (1, '2026-03-01', NULL, NULL),
            (2, '2026-07-01', NULL, NULL);
    """)
    cur.close()


def _stale(conn, table):
    cur = conn.cursor()
    cur.execute(f"SELECT id, stale_since, stale_reason FROM {table} WHERE stale_since IS NOT NULL ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    return {r[0]: (r[1], r[2]) for r in rows}


@pytest.mark.database
def test_the_sweep_stamps_exactly_the_rows_stored_before_each_change(fixture_db):
    _seed(fixture_db)
    backfill(fixture_db)
    housing = _stale(fixture_db, "housing_sepp_standards")
    # 1 and 12 predate the Housing change; 36 predates the E&C change; 34 came after the Housing change;
    # 90 already carried a notice, which must be left as it was.
    assert set(housing) == {1, 12, 36, 90}
    assert housing[1][0] == HOUSING_CHANGED and housing[12][0] == HOUSING_CHANGED
    assert housing[36][0] == EC_CHANGED
    assert housing[90][1] == "an earlier notice"
    assert set(_stale(fixture_db, "cdc_eligibility_standards")) == {1}


@pytest.mark.database
def test_a_second_run_changes_nothing(fixture_db):
    _seed(fixture_db)
    backfill(fixture_db)
    before = _stale(fixture_db, "housing_sepp_standards")
    assert backfill(fixture_db) == []
    assert _stale(fixture_db, "housing_sepp_standards") == before


@pytest.mark.database
def test_an_instrument_that_is_not_flagged_is_left_alone(fixture_db):
    """Confusable negative: the same old rows, but nobody has flagged a change."""
    _seed(fixture_db, housing_flagged=False, ec_flagged=False)
    assert backfill(fixture_db) == []
    assert set(_stale(fixture_db, "housing_sepp_standards")) == {90}


@pytest.mark.database
def test_the_fresh_transition_path_runs_through_a_real_driver(fixture_db):
    """The W3 path's predicates contain ILIKE '%housing%' next to a %s parameter; through psycopg2 an
    unescaped '%h' is a malformed placeholder. This runs the statement for real."""
    _seed(fixture_db)
    notes = mark_fresh(fixture_db, "sepp_housing_2021", "SEPP (Housing) 2021", "24 April 2026", "1 Oct 2026")
    assert notes, "the fresh path stamped nothing"
    assert {1, 12, 34}.issubset(_stale(fixture_db, "housing_sepp_standards"))
    assert 36 not in _stale(fixture_db, "housing_sepp_standards"), "a Housing change staled an E&C row"
