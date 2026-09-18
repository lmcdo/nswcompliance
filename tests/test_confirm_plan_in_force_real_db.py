"""The plan-in-force confirmations, against the REAL table they were written to.

The field means a person checked that the plan a council's numbers trace to is the plan in
force. Two things can rot it and neither is visible in a mock: a confirmation naming a plan
the check does not derive (fails as loudly as none, but looks done), and a confirmation
written for a council whose source moved after extraction (green on the exact condition the
check exists to catch).

Opt-in: PYTEST_REAL_DB=1 plus @pytest.mark.database, deselected by default per pytest.ini.
Read-only — nothing here writes.

    PYTEST_REAL_DB=1 DATABASE_URL=... pytest -m database \
        tests/test_confirm_plan_in_force_real_db.py -v
"""
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from dq_db import main_checkout  # noqa: E402

_REAL_DB_REQUESTED = os.environ.get("PYTEST_REAL_DB") == "1"
if _REAL_DB_REQUESTED:
    load_dotenv(main_checkout() / ".env")

pytestmark = pytest.mark.database


def _skip_if_no_real_db():
    if not _REAL_DB_REQUESTED:
        pytest.skip("Real-DB test. PYTEST_REAL_DB=1 DATABASE_URL=... pytest -m database "
                    "tests/test_confirm_plan_in_force_real_db.py")
    if not os.environ.get("DATABASE_URL") and not os.environ.get("SUPABASE_DB_URL"):
        pytest.skip("PYTEST_REAL_DB=1 set but no DATABASE_URL/SUPABASE_DB_URL available.")


def _rows():
    import confirm_plan_in_force as c

    conn = c.psycopg2.connect(c._dsn(), connect_timeout=20)
    try:
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = '30s'")
            cur.execute(c.PLAN_SQL)
            return c, cur.fetchall()
    finally:
        conn.close()


class TestEveryConfirmationNamesThePlanTheCheckDerives:
    def test_the_written_plan_equals_the_derived_plan(self):
        """The round trip that matters: what was stored must equal what the check computes,
        or OC-17 fails while the table looks confirmed."""
        _skip_if_no_real_db()
        _c, rows = _rows()
        # PLAN_SQL returns the derived name; read the stored one alongside it.
        import confirm_plan_in_force as c

        conn = c.psycopg2.connect(c._dsn(), connect_timeout=20)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT lga, currency_confirmed_plan FROM dcp_plan_as_at "
                            "WHERE currency_confirmed_plan IS NOT NULL")
                stored = dict(cur.fetchall())
        finally:
            conn.close()
        derived = {r[0]: r[3] for r in rows}
        mismatched = [(lga, derived.get(lga), name) for lga, name in stored.items()
                      if lga in derived and derived[lga] != name]
        assert not mismatched, mismatched


class TestNothingIsConfirmedThatShouldNotBe:
    def test_every_held_back_council_is_still_unconfirmed(self):
        """City of Sydney, Georges River, Ku-ring-gai and Woollahra serve numbers read out
        of documents we no longer hold; Northern Beaches monitors a URL pinned to a 2016
        file. Confirming any of them would attest to the wrong version."""
        _skip_if_no_real_db()
        c, _rows_unused = _rows()
        conn = c.psycopg2.connect(c._dsn(), connect_timeout=20)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT lga FROM dcp_plan_as_at WHERE lga = ANY(%s) "
                            "AND currency_confirmed_at IS NOT NULL",
                            (sorted(c.HELD_BACK),))
                confirmed = [lga for (lga,) in cur.fetchall()]
        finally:
            conn.close()
        assert not confirmed, f"held back but confirmed: {confirmed}"

    def test_no_confirmation_rests_on_nothing(self):
        """A confirmation with no recorded evidence is the failure this field exists to
        prevent — a record of being seen standing in for a check."""
        _skip_if_no_real_db()
        import confirm_plan_in_force as c

        conn = c.psycopg2.connect(c._dsn(), connect_timeout=20)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT lga FROM dcp_plan_as_at "
                            "WHERE currency_confirmed_at IS NOT NULL "
                            "AND (currency_evidence IS NULL OR btrim(currency_evidence) = '')")
                bare = [lga for (lga,) in cur.fetchall()]
        finally:
            conn.close()
        assert not bare, f"confirmed with no evidence: {bare}"

    def test_a_council_serving_two_plan_names_is_never_confirmed(self):
        """The condition the tracing repair cleared. If it returns, the confirmation must
        not paper over it."""
        _skip_if_no_real_db()
        _c, rows = _rows()
        import confirm_plan_in_force as c

        conn = c.psycopg2.connect(c._dsn(), connect_timeout=20)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT lga FROM dcp_plan_as_at WHERE currency_confirmed_at IS NOT NULL")
                confirmed = {lga for (lga,) in cur.fetchall()}
        finally:
            conn.close()
        bad = [(r[0], r[1], r[2]) for r in rows
               if r[0] in confirmed and (r[1] or r[2] != 1)]
        assert not bad, f"confirmed despite untraced numbers or multiple plans: {bad}"
