"""The published-coverage verifier, run against the REAL catalog.

WHY THIS EXISTS. `scripts/verify_coverage_stats.py` is the gate standing between
the database and every number on the public site. It runs in `gates.yml`,
`data-watch.yml` and `.githooks/pre-push` — as a script step, with no test of its
own. So its eight SQL statements have never been asserted to be valid SQL by
anything except the act of running it, and a column rename would surface as a CI
step failing rather than as a named test.

That is not hypothetical in this repo. `enrichment/pipeline.py`'s status report
counted `v2_enriched_at`, a column on no table, and raised on every invocation for
months because executing it was the only way to find out (#1085, same day).

This file adds the real layer: execute every query the verifier declares, against
the live catalog, and assert each returns an integer. Opt-in via PYTEST_REAL_DB=1,
because conftest_mocks.py stubs psycopg2 otherwise and a MagicMock answers
anything.

Run it:
    PYTEST_REAL_DB=1 DATABASE_URL=<supabase pooler url> pytest -m database \\
        tests/test_verify_coverage_stats_real_db.py -v
"""
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from dq_db import main_checkout  # noqa: E402

_REAL_DB_REQUESTED = os.environ.get("PYTEST_REAL_DB") == "1"
if _REAL_DB_REQUESTED:
    load_dotenv(main_checkout() / ".env")

pytestmark = pytest.mark.database


def _skip_if_no_real_db():
    if not _REAL_DB_REQUESTED:
        pytest.skip(
            "Real-DB test. Run with: PYTEST_REAL_DB=1 DATABASE_URL=... "
            "pytest -m database tests/test_verify_coverage_stats_real_db.py"
        )
    if not os.environ.get("DATABASE_URL") and not os.environ.get("SUPABASE_DB_URL"):
        pytest.skip("PYTEST_REAL_DB=1 set but no DATABASE_URL/SUPABASE_DB_URL available.")


def test_every_declared_query_runs_against_the_live_catalog():
    """A renamed or dropped column must fail HERE, naming the stat, rather than
    as an opaque CI step failure."""
    _skip_if_no_real_db()
    import verify_coverage_stats as v
    from dq_db import connect

    conn = connect()
    try:
        cur = conn.cursor()
        for key, (label, sql) in v.QUERIES.items():
            try:
                cur.execute(sql)
            except Exception as exc:  # noqa: BLE001
                pytest.fail(f"{key} ({label}) does not run against the live schema: {exc}")
            row = cur.fetchone()
            assert row is not None and isinstance(row[0], int), (
                f"{key} ({label}) returned {row!r}, not a count"
            )
    finally:
        conn.close()


def test_the_published_figures_agree_with_the_database():
    """The verifier's own verdict, asserted as a test.

    Exit 0 = agree, 1 = drift, 2 = database unreachable. Unreachable SKIPS rather
    than fails, matching the script's own three-state handling — collapsing
    'unreachable' into 'the figures disagree' turned main red on 2026-08-12.
    """
    _skip_if_no_real_db()
    import verify_coverage_stats as v

    rc = v.main()
    if rc == 2:
        pytest.skip("database unreachable — UNKNOWN, not a disagreement")
    assert rc == 0, (
        "published coverage figures disagree with the database; the verifier "
        "printed which above. Update frontend-nextjs/lib/coverage.ts."
    )


def test_the_two_flood_counts_are_read_from_the_source_not_the_database():
    """Both flood figures come from services/flood_truth.py, so they must hold
    without a connection. Pinned because reading them from the database instead
    would silently reintroduce the defect this branch fixes: the DB knows nothing
    about which studies carry a depth band."""
    _skip_if_no_real_db()
    import verify_coverage_stats as v

    assert v.live_flood_study_count() == 4
    assert v.live_flood_depth_study_count() == 3
    assert v.live_flood_depth_study_count() <= v.live_flood_study_count()
