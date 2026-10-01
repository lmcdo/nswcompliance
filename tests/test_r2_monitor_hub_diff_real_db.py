"""The removed/unlisted split, checked against the REAL registry rows.

The pure-logic tests in tests/test_r2_monitor_alerting.py build their own
`stored` dicts, so they prove the classification rule and nothing about the
data it will meet. This file closes that gap: it reads canterbury_bankstown's
actual rows out of production and asserts the classification the live sweep
will produce, so a change to the data -- a counter reset, a chapter marked
inert, a URL repaired -- is visible here rather than only in a Telegram digest
a fortnight later.

Why canterbury_bankstown: it is the council the split exists for. Measured
2026-10-01, its hub page exposes 14 PDF links (six of them the same waste
document) and enumerates none of its DCP chapters, which are served from a
SharePoint/Azure api/publish endpoint. The registry holds 54 non-inert active
chapters, so every sweep reported 54 "Removed from hub" while 51 of those
chapters had been fetched and hashed successfully in that same run.

This deliberately does NOT scrape the council's hub page. That is a live HTTP
call to a third party whose WAF discriminates by IP (the repo already records
Railway's single-IP problem), so putting it in an automated test would make
the test report on the council's mood rather than on our logic. The empty
`discovered` list models exactly what the scraper returns for the chapters in
question -- none of them -- which is the condition under test.

Run it:
    PYTEST_REAL_DB=1 pytest -m database tests/test_r2_monitor_hub_diff_real_db.py -v
"""
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

# prior-art-checked: reuse, not reinvention -- scripts/dq_db.py already solved
# "find the right .env from inside a worktree", and tests/test_drawdown_verify_
# real_db.py already established this opt-in shape. Following both rather than
# inventing a third way.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from dq_db import main_checkout  # noqa: E402

# Gate the credential load on the flag itself, for the reason recorded in
# test_drawdown_verify_real_db.py: a plain `pytest` run must never pull the
# production DATABASE_URL into the process environment just by collecting a
# module whose tests are deselected anyway.
_REAL_DB_REQUESTED = os.environ.get("PYTEST_REAL_DB") == "1"
if _REAL_DB_REQUESTED:
    load_dotenv(main_checkout() / ".env")

pytestmark = pytest.mark.database

# r2_monitor reads its R2 and DB config at import time with a bare index, so the
# module cannot be imported at all without them — and a worktree carries no .env.
# These tests never make an R2 call, so placeholders are fine there.
#
# DATABASE_URL is deliberately NOT placeholdered in real-DB mode. r2_monitor reads
# `DATABASE_URL or SUPABASE_DB_URL`, and so does this file; setting a placeholder
# unconditionally would satisfy the first and silently prevent the SUPABASE_DB_URL
# fallback from ever being reached, so a run configured only with SUPABASE_DB_URL
# would try to connect to the literal string "test-database_url" instead of
# skipping or working. Caught by the pre-push cross-review, 2026-10-01.
_PLACEHOLDERS = ["R2_ACCOUNT_ID", "R2_BUCKET_NAME", "R2_ACCESS_KEY_ID",
                 "R2_SECRET_ACCESS_KEY"]
if not _REAL_DB_REQUESTED:
    _PLACEHOLDERS.append("DATABASE_URL")
for _var in _PLACEHOLDERS:
    os.environ.setdefault(_var, f"test-{_var.lower()}")

from r2_monitor import diff_urls, UNLISTED_CONFIRM_FAILURES  # noqa: E402

COUNCIL = "canterbury_bankstown"


def _skip_if_no_real_db():
    if not _REAL_DB_REQUESTED:
        pytest.skip(
            "Real-DB test. Run with: PYTEST_REAL_DB=1 pytest -m database "
            "tests/test_r2_monitor_hub_diff_real_db.py"
        )
    if not os.environ.get("DATABASE_URL") and not os.environ.get("SUPABASE_DB_URL"):
        pytest.skip("PYTEST_REAL_DB=1 set but no DATABASE_URL/SUPABASE_DB_URL available.")


def _live_rows():
    """The rows the sweep itself would hand diff_urls, read read-only."""
    import psycopg2

    dsn = os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"]
    conn = psycopg2.connect(dsn, connect_timeout=30)
    try:
        conn.set_session(readonly=True, autocommit=True)
        cur = conn.cursor()
        cur.execute("SET statement_timeout = '30s'")
        cur.execute(
            """SELECT chapter_key, council_url, check_failures
                 FROM dcp_chapter_registry
                WHERE council = %s
                  AND is_active
                  AND NOT COALESCE(is_inert, FALSE)
                  AND council_url IS NOT NULL""",
            (COUNCIL,),
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    finally:
        conn.close()


class TestAgainstTheRealRegistry:
    def test_a_live_url_absent_from_the_hub_never_alerts(self):
        """The defect itself: 51 chapters that fetch fine must not be 'removed'.

        Asserted as a rule over whatever the data currently is, not against a
        frozen count -- a count would go stale the first time a chapter is
        onboarded or repaired, and a stale assertion gets deleted rather than
        read.
        """
        _skip_if_no_real_db()
        rows = _live_rows()
        assert rows, f"no active non-inert {COUNCIL} chapters found — check the slug"

        diff = diff_urls(discovered=[], stored=rows, hub_expected_count=None)

        healthy = {r["chapter_key"] for r in rows
                   if (r["check_failures"] or 0) < UNLISTED_CONFIRM_FAILURES}
        assert healthy, "expected at least one healthy chapter to prove the point"
        assert healthy.isdisjoint(set(diff.removed)), (
            "a chapter whose own URL is still fetching was reported as removed: "
            f"{sorted(healthy & set(diff.removed))}"
        )
        assert healthy == set(diff.unlisted)

    def test_a_persistently_failing_url_does_alert(self):
        """The other direction: the split must not silence a real removal."""
        _skip_if_no_real_db()
        rows = _live_rows()
        dead = {r["chapter_key"] for r in rows
                if (r["check_failures"] or 0) >= UNLISTED_CONFIRM_FAILURES}

        diff = diff_urls(discovered=[], stored=rows, hub_expected_count=None)
        assert set(diff.removed) == dead
        if not dead:
            pytest.skip(
                "No chapter is currently at or above the threshold, so the alerting "
                "direction has no live example today. The pure-logic tests cover it."
            )

    def test_every_chapter_lands_in_exactly_one_bucket(self):
        """No silent drop: the split must partition, not filter."""
        _skip_if_no_real_db()
        rows = _live_rows()
        diff = diff_urls(discovered=[], stored=rows, hub_expected_count=None)

        removed, unlisted = set(diff.removed), set(diff.unlisted)
        assert removed.isdisjoint(unlisted)
        assert removed | unlisted == {r["chapter_key"] for r in rows}
        assert len(diff.removed) + len(diff.unlisted) == len(rows)
