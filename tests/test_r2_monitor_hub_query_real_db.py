"""The widened chapter query, checked against the REAL registry.

tests/test_hub_discovery_is_not_gated_on_change_detection.py asserts the SQL
text and exercises pick_hub_row on hand-built rows. Neither touches a database,
so together they prove the predicate was written and nothing about what it
actually admits. That gap matters here more than usual, because the whole claim
of this branch is a count of councils in production — 9 hub-scraped becomes 19 —
and a count is exactly the kind of assertion that quietly stops being true.

This file runs the real predicate against the real table and asserts the
property the branch exists to deliver: a council with a registered scraper and
a hub URL is reachable by the sweep even when not one of its chapters carries a
per-chapter `council_url`.

Asserted as a property over whatever the data currently is, not against frozen
numbers. A frozen "19" goes stale the first time a council is onboarded, and a
stale assertion gets deleted rather than read
(memory/feedback-no-new-lists-finish-against-the-benchmark.md).

Deliberately does NOT scrape any council hub page: those are live third-party
calls whose WAFs discriminate by IP, so a test built on them would report on the
councils' mood rather than on our SQL.

Run it:
    PYTEST_REAL_DB=1 pytest -m database tests/test_r2_monitor_hub_query_real_db.py -v
"""
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

# prior-art-checked: reuse, not reinvention — scripts/dq_db.py already solved
# "find the right .env from inside a worktree", and
# tests/test_drawdown_verify_real_db.py already established this opt-in shape.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from dq_db import main_checkout  # noqa: E402

# Gate the credential load on the flag itself, for the reason recorded in
# test_drawdown_verify_real_db.py: a plain `pytest` run must never pull the
# production DATABASE_URL into the process just by collecting a module whose
# tests are deselected anyway.
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

from hub_scrapers import HUB_SCRAPERS  # noqa: E402
from r2_monitor import pick_hub_row  # noqa: E402

#: The predicate this branch changed, and the one it replaced.
NEW_PREDICATE = "(council_url IS NOT NULL OR council_page_url IS NOT NULL)"
OLD_PREDICATE = "council_url IS NOT NULL"


def _skip_if_no_real_db():
    if not _REAL_DB_REQUESTED:
        pytest.skip(
            "Real-DB test. Run with: PYTEST_REAL_DB=1 pytest -m database "
            "tests/test_r2_monitor_hub_query_real_db.py"
        )
    if not os.environ.get("DATABASE_URL") and not os.environ.get("SUPABASE_DB_URL"):
        pytest.skip("PYTEST_REAL_DB=1 set but no DATABASE_URL/SUPABASE_DB_URL available.")


def _councils_admitted_by(predicate: str) -> dict[str, list[dict]]:
    """Group active chapters by council under the given predicate, read-only."""
    import psycopg2

    dsn = os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"]
    conn = psycopg2.connect(dsn, connect_timeout=30)
    try:
        conn.set_session(readonly=True, autocommit=True)
        cur = conn.cursor()
        cur.execute("SET statement_timeout = '30s'")
        cur.execute(
            f"""SELECT council, chapter_key, council_url, council_page_url, sort_order
                  FROM dcp_chapter_registry
                 WHERE is_active = TRUE AND {predicate}
                 ORDER BY council, sort_order"""
        )
        cols = [d[0] for d in cur.description]
        grouped: dict[str, list[dict]] = {}
        for row in cur.fetchall():
            r = dict(zip(cols, row))
            grouped.setdefault(r["council"], []).append(r)
        return grouped
    finally:
        conn.close()


def _hub_scrapable(grouped: dict[str, list[dict]]) -> set[str]:
    """Councils the sweep would actually hub-scrape: a scraper AND a hub URL."""
    out = set()
    for council, rows in grouped.items():
        if council not in HUB_SCRAPERS:
            continue
        if (pick_hub_row(rows).get("council_page_url") or "").strip():
            out.add(council)
    return out


class TestTheWidenedQueryAgainstProduction:
    def test_it_admits_strictly_more_councils_and_loses_none(self):
        _skip_if_no_real_db()
        old = _councils_admitted_by(OLD_PREDICATE)
        new = _councils_admitted_by(NEW_PREDICATE)

        assert set(old).issubset(set(new)), (
            "the widened predicate dropped a council the old one admitted: "
            f"{sorted(set(old) - set(new))}"
        )
        assert len(new) > len(old), (
            "the widened predicate admitted no new council, so either the fix is "
            "inert or the data no longer contains the shape it was written for"
        )

    def test_hub_scrapable_councils_strictly_increase(self):
        """The number that matters: who gets their document list re-read."""
        _skip_if_no_real_db()
        old_scrapable = _hub_scrapable(_councils_admitted_by(OLD_PREDICATE))
        new_scrapable = _hub_scrapable(_councils_admitted_by(NEW_PREDICATE))

        assert old_scrapable.issubset(new_scrapable), (
            f"a council stopped being hub-scrapable: "
            f"{sorted(old_scrapable - new_scrapable)}"
        )
        assert new_scrapable - old_scrapable, (
            "no council was recovered — the defect this branch fixes is gone from "
            "the data, or the predicate is not doing what it claims"
        )

    def test_a_council_with_only_a_hub_url_is_now_reachable(self):
        """The exact locked-out shape: a scraper, a hub URL, no per-chapter URL.

        Named as a property rather than a council list, because which councils
        are in this state changes as per-chapter URLs are filled in — and when
        none are left, that is success, not a failure, so it skips rather than
        asserting an empty set is non-empty.
        """
        _skip_if_no_real_db()
        new = _councils_admitted_by(NEW_PREDICATE)

        locked_out = {
            council for council, rows in new.items()
            if council in HUB_SCRAPERS
            and all(not (r.get("council_url") or "").strip() for r in rows)
            and (pick_hub_row(rows).get("council_page_url") or "").strip()
        }
        if not locked_out:
            pytest.skip(
                "No council is currently in the hub-URL-only shape — every scraper "
                "council now has at least one per-chapter URL. The fix is still "
                "correct; there is simply no live example to assert on today."
            )

        old = _councils_admitted_by(OLD_PREDICATE)
        assert locked_out.isdisjoint(set(old)), (
            "a hub-URL-only council was already admitted by the old predicate, "
            "which contradicts the premise of this branch"
        )

    def test_pick_hub_row_finds_a_hub_url_the_first_row_lacks(self):
        """cumberland's shape, asserted against production rather than a fixture."""
        _skip_if_no_real_db()
        new = _councils_admitted_by(NEW_PREDICATE)

        split_shape = {
            council for council, rows in new.items()
            if len(rows) > 1
            and not (rows[0].get("council_page_url") or "").strip()
            and any((r.get("council_page_url") or "").strip() for r in rows)
        }
        if not split_shape:
            pytest.skip("No council currently records its hub URL off row zero.")

        for council in split_shape:
            rows = new[council]
            assert (pick_hub_row(rows).get("council_page_url") or "").strip(), (
                f"pick_hub_row returned a row with no hub URL for {council}, so the "
                f"council would be skipped despite having one"
            )
