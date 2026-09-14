"""The outreach gate's plan-in-force, retired-zone and claim-12 sub-checks can fail.

prior-art-checked: tests for sub-checks added to scripts/outreach_claim_checks.py; tests/test_dq_check_outreach.py
covers the runner (declared states, exit codes), not any composite sub-check.

The two SQL sub-checks are run for real, against fixture rows in TEMPORARY tables. Postgres searches the
session's temporary schema before public, so the unqualified table names in the checks resolve to the
fixtures and no real table is read or written; the tables vanish when the connection closes. Opt in with
PYTEST_REAL_DB=1 and DATABASE_URL, like the other database tests.

The zone guard is run with the real serve filter (conveyancing_db.zone_row_applies) and the repo's own
translation table, against rows handed to it by a fake connection.
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import outreach_claim_checks as occ  # noqa: E402

_REAL_DB_REQUESTED = os.environ.get("PYTEST_REAL_DB") == "1"


# ── zone guard (no database) ──────────────────────────────────────────────────────────────────────────

class _Cursor:
    def __init__(self, rows):
        self._rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        pass

    def fetchall(self):
        return self._rows


class _Conn:
    def __init__(self, rows):
        self._rows = rows

    def cursor(self):
        return _Cursor(self._rows)

    def close(self):
        pass


def _zone_guard(monkeypatch, rows):
    monkeypatch.setattr(occ, "_connect", lambda: _Conn(rows))
    return occ.no_site_loses_a_rule_to_a_retired_zone_code()


# The zone codes below are TEST INPUT: fixture rows quoting a council's condition text and a stored scope
# verbatim, as production held them. The guard under test takes its codes from shared/zone-taxonomy.json;
# nothing here is a lookup table, hence the per-line zone-codes lint exemptions.

def test_a_rule_scoped_only_by_retired_codes_fails(monkeypatch):
    """The 2026-09-14 case: ashfield 504 named only retired business-zone codes and had no stored scope,
    so sites in the zones that replaced them lost it."""
    verdict, detail = _zone_guard(monkeypatch, [
        (504, "ashfield", "zone_specific", "B1, B2, B4 zones", None, None)])  # noqa: zone-codes
    assert verdict == occ.FAIL and "ashfield/504" in detail


def test_the_same_rule_with_a_stored_scope_passes(monkeypatch):
    verdict, _ = _zone_guard(monkeypatch, [
        (504, "ashfield", "zone_specific", "B1, B2, B4 zones",  # noqa: zone-codes
         ["B1", "E1", "B2", "B4", "MU1"], None)])  # noqa: zone-codes
    assert verdict == occ.PASS


def test_a_rule_for_every_zone_that_mentions_a_retired_code_passes(monkeypatch):
    """Confusable negative: canada_bay 816 names two retired codes as a distance, not as the site's zone."""
    verdict, _ = _zone_guard(monkeypatch, [
        (816, "canada_bay", "universal_residential",
         "2 bedrooms, within 800m station or 400m B3/B4", None, None)])  # noqa: zone-codes
    assert verdict == occ.PASS


def test_a_rule_scoped_by_current_codes_passes(monkeypatch):
    verdict, _ = _zone_guard(monkeypatch, [
        (1, "x", "zone_specific", "E1 and MU1 zones", None, None)])  # noqa: zone-codes
    assert verdict == occ.PASS


def test_an_unreachable_database_is_not_a_pass(monkeypatch):
    monkeypatch.setattr(occ, "_connect", lambda: None)
    verdict, _ = occ.no_site_loses_a_rule_to_a_retired_zone_code()
    assert verdict == occ.UNKNOWN


# ── plan in force and claim 12 (fixture tables in a real session) ─────────────────────────────────────

@pytest.fixture()
def fixture_db():
    if not _REAL_DB_REQUESTED:
        pytest.skip("Real-DB test. Run with: PYTEST_REAL_DB=1 DATABASE_URL=... pytest -m database "
                    "tests/test_outreach_claim_checks_plan_and_zone.py -o addopts=")
    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not url:
        pytest.skip("PYTEST_REAL_DB=1 set but no DATABASE_URL/SUPABASE_DB_URL available.")
    import psycopg2

    conn = psycopg2.connect(url, connect_timeout=20)
    conn.autocommit = False
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '30s'")
    cur.execute("""
        CREATE TEMPORARY TABLE dcp_setback_controls (
            id int, lga text, source_chapter_key text, is_current boolean, needs_review boolean,
            applicability text, condition text, zones_include text[], zones_exclude text[]) ON COMMIT DROP;
        CREATE TEMPORARY TABLE dcp_chapter_registry (
            id int, council text, chapter_key text, dcp_name text, is_active boolean,
            council_url text, council_page_url text) ON COMMIT DROP;
        CREATE TEMPORARY TABLE dcp_plan_as_at (
            lga text, currency_confirmed_at timestamptz, currency_confirmed_plan text) ON COMMIT DROP;
        CREATE TEMPORARY TABLE regulatory_provisions (
            id int, is_current boolean, v2_is_actionable boolean,
            source_council text, source_chapter_key text) ON COMMIT DROP;
    """)
    cur.execute("SELECT count(*) FROM pg_class WHERE relname = 'dcp_plan_as_at' AND relpersistence = 't'")
    assert cur.fetchone()[0] == 1, "fixture tables are not temporary; refusing to go on"
    try:
        yield cur
    finally:
        conn.rollback()
        conn.close()


def _seed(cur):
    cur.execute("""
        INSERT INTO dcp_chapter_registry VALUES
            (1, 'good',   'ch1', 'Good DCP 2020', TRUE, 'https://good.example/ch1.pdf', NULL),
            (2, 'wrong',  'ch1', 'Plan A 2012',   TRUE, 'https://wrong.example/a.pdf', NULL),
            (3, 'two',    'old', 'Two DCP 2012',  TRUE, NULL, 'https://two.example/dcp'),
            (4, 'two',    'new', 'Two DCP 2022',  TRUE, NULL, 'https://two.example/dcp'),
            (5, 'stale',  'ch1', 'Stale DCP 2015', TRUE, 'https://stale.example/ch1.pdf', NULL),
            (6, 'nourl',  'ch1', 'NoUrl DCP 2019', TRUE, NULL, NULL),
            (7, 'retired','ch1', 'Retired DCP 2010', FALSE, 'https://retired.example/ch1.pdf', NULL);
        INSERT INTO dcp_setback_controls (id, lga, source_chapter_key, is_current, needs_review) VALUES
            (10, 'good',    'ch1',           TRUE, FALSE),
            (11, 'good',    '_external_lep', TRUE, FALSE),
            (20, 'wrong',   'ch1',           TRUE, FALSE),
            (30, 'two',     'old',           TRUE, NULL),
            (31, 'two',     'new',           TRUE, FALSE),
            (40, 'nullkey', NULL,            TRUE, FALSE),
            (50, 'stale',   'ch1',           TRUE, FALSE),
            (60, 'nourl',   'ch1',           TRUE, FALSE),
            (70, 'retired', 'ch1',           TRUE, FALSE),
            (80, 'hidden',  'gone',          TRUE, TRUE),
            (90, 'extonly', '_external_adg', TRUE, FALSE);
        INSERT INTO dcp_plan_as_at VALUES
            ('good',  NOW() - INTERVAL '10 days',  'Good DCP 2020'),
            ('wrong', NOW() - INTERVAL '10 days',  'Plan B 2024'),
            ('stale', NOW() - INTERVAL '100 days', 'Stale DCP 2015'),
            ('nourl', NOW() - INTERVAL '5 days',   'NoUrl DCP 2019');
    """)


@pytest.mark.database
def test_the_plan_in_force_check_names_each_way_a_council_can_fail(fixture_db):
    _seed(fixture_db)
    fixture_db.execute(occ._PLAN_IN_FORCE_SQL)
    reasons = dict(fixture_db.fetchall())
    # The cross-review case: a recent confirmation of a DIFFERENT plan must not pass.
    assert reasons.get("wrong") == "confirmation names Plan B 2024"
    assert reasons.get("two") == "2 plan names served"
    assert reasons.get("nullkey") == "1 number(s) trace to no active chapter"
    assert reasons.get("retired") == "1 number(s) trace to no active chapter"
    assert reasons.get("stale") == "confirmation older than 90 days"
    # Confusable negatives: a council confirmed for the one plan it serves passes, and so does a council
    # served only from state instruments or only from rows held back for review.
    assert "good" not in reasons and "nourl" not in reasons
    assert "extonly" not in reasons and "hidden" not in reasons


@pytest.mark.database
def test_claim_12_counts_council_material_with_no_published_source(fixture_db):
    _seed(fixture_db)
    fixture_db.execute("""
        INSERT INTO regulatory_provisions VALUES
            (1, TRUE,  TRUE,  'good',  'ch1'),
            (2, TRUE,  TRUE,  'nourl', 'ch1'),
            (3, TRUE,  FALSE, 'nourl', 'ch1'),
            (4, TRUE,  TRUE,  'state', 'adg'),
            (5, FALSE, TRUE,  'gone',  'ch9');
    """)
    fixture_db.execute(occ._UNTRACED_COUNCIL_MATERIAL_SQL)
    # numbers: nullkey 40 (no chapter), nourl 60 (no address), retired 70 (inactive chapter) = 3
    # rules: nourl provision 2 = 1; the non-actionable, state and superseded provisions are not served council rules
    assert fixture_db.fetchone()[0] == 4
