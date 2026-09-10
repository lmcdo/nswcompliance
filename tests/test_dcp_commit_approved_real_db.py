"""The assumption the precinct re-derivation rests on, checked against production.

`dcp_commit_approved` now hands each committed council's name straight to
`derive_precinct_keys.run(council=...)`. That only works if three systems agree on
how a council is spelled:

    dcp_review_queue.council  ->  the name the commit loop sees
    derive_precinct_keys.RULES[*]["council"]  ->  the name the rule matches on
    regulatory_provisions.source_council      ->  the name the UPDATE filters on

A mismatch does not raise. run() would select zero rows, print a tidy zero total,
and the keys would stay NULL -- the exact silent shape of the bug this fixes. A
mock cannot check this: the vocabularies live in production, so the test has to.

The unit tests in tests/test_dcp_commit_rederives_precinct_keys.py pin the WIRING
(scoped not bulk, applied not dry-run, after layer tagging, survivable errors).
This file pins the DATA those tests mock away.

    PYTEST_REAL_DB=1 DATABASE_URL=<supabase pooler url> pytest -m database \
        tests/test_dcp_commit_approved_real_db.py -o addopts=""

Skipped by default: conftest_mocks stubs psycopg2 unless PYTEST_REAL_DB=1, so
without the opt-in these would interrogate a MagicMock and pass on nonsense.

Nothing here writes. The one test that exercises the derivation itself runs it
apply=False, so it reads production and reports; it cannot change a key.
"""
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

# prior-art-checked: reuse, not reinvention -- scripts/dq_db.py already solved
# "find the right .env from inside a worktree" (a naive load_dotenv('.env') falls
# through to localhost defaults from a worktree, which has no .env of its own).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from dq_db import main_checkout  # noqa: E402

# Gate the dotenv load on the flag itself, so production DATABASE_URL is never
# pulled into the process on a plain `pytest` run whose tests here are deselected
# anyway. Same reasoning as tests/test_drawdown_verify_real_db.py, which had this
# corrected in cross-review.
_REAL_DB_REQUESTED = os.environ.get("PYTEST_REAL_DB") == "1"
if _REAL_DB_REQUESTED:
    load_dotenv(main_checkout() / ".env")

pytestmark = pytest.mark.database


def _skip_if_no_real_db():
    if not _REAL_DB_REQUESTED:
        pytest.skip(
            "Real-DB test. Run with: PYTEST_REAL_DB=1 DATABASE_URL=... "
            "pytest -m database tests/test_dcp_commit_approved_real_db.py"
        )
    if not os.environ.get("DATABASE_URL") and not os.environ.get("SUPABASE_DB_URL"):
        pytest.skip("PYTEST_REAL_DB=1 set but no DATABASE_URL/SUPABASE_DB_URL available.")


def _conn():
    import psycopg2
    return psycopg2.connect(
        os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"],
        connect_timeout=10,
    )


def _rules_councils():
    """Imported late and inside a test: derive_precinct_keys reads DATABASE_URL and
    opens data/cos_precinct_page_ranges.json at MODULE level, so importing it at
    collection time would run that on every plain pytest run."""
    import derive_precinct_keys as dpk
    return {r["council"] for r in dpk.RULES}


class TestCouncilSlugVocabulary:
    def test_every_rule_council_exists_in_the_provisions_vocabulary(self):
        """A rule naming a council the provisions table spells differently is dead.

        run() filters `WHERE source_council = %(council)s`. If the RULES slug is not
        a real source_council value, the rule selects nothing, reports zero, and the
        council is never keyed -- with no error at any layer.
        """
        _skip_if_no_real_db()
        conn = _conn()
        try:
            cur = conn.cursor()
            cur.execute("SET statement_timeout = '30s'")
            cur.execute(
                "SELECT DISTINCT source_council FROM regulatory_provisions "
                "WHERE source_council IS NOT NULL"
            )
            provisions = {r[0] for r in cur.fetchall()}
        finally:
            conn.close()

        orphans = sorted(_rules_councils() - provisions)
        assert not orphans, (
            f"derive_precinct_keys has rules for councils that do not exist in "
            f"regulatory_provisions.source_council: {orphans}. Those rules can never "
            f"key anything, and they fail silently -- run() reports a zero total, not "
            f"an error."
        )

    def test_review_queue_councils_use_the_same_slug_vocabulary(self):
        """The commit loop reads a council from dcp_review_queue and hands that exact
        string to the derivation. If the queue spells a council differently from the
        provisions table, the scoped derivation silently keys nothing for it."""
        _skip_if_no_real_db()
        conn = _conn()
        try:
            cur = conn.cursor()
            cur.execute("SET statement_timeout = '30s'")
            cur.execute("SELECT DISTINCT council FROM dcp_review_queue WHERE council IS NOT NULL")
            queue = {r[0] for r in cur.fetchall()}
            cur.execute(
                "SELECT DISTINCT source_council FROM regulatory_provisions "
                "WHERE source_council IS NOT NULL"
            )
            provisions = {r[0] for r in cur.fetchall()}
        finally:
            conn.close()

        strangers = sorted(queue - provisions)
        assert not strangers, (
            f"dcp_review_queue uses council slugs absent from "
            f"regulatory_provisions.source_council: {strangers}. Committing one of "
            f"these would hand the derivation a name it cannot match."
        )


class TestDerivationStillMatchesProduction:
    def test_the_rules_still_reproduce_the_keys_production_already_has(self):
        """Read-only proof that the rules have not drifted from the data.

        `validate=True` asserts that every key a validate-rule derives equals the key
        the row already carries; run() returns 1 and prints the offenders if any
        disagree. `apply=False` means it reads and reports and writes nothing, so
        this is safe to run against production on every DB test pass.

        This is what would catch a re-paginated PDF or an amended chapter quietly
        invalidating a rule -- the case where the wiring works perfectly and still
        writes wrong keys.
        """
        _skip_if_no_real_db()
        import derive_precinct_keys as dpk

        rc = dpk.run(council=None, apply=False, validate=True)

        assert rc == 0, (
            "derive_precinct_keys --validate failed against production: at least one "
            "derived key no longer reproduces the key the row already carries, so the "
            "rules have drifted from the data. Re-run "
            "`python scripts/derive_precinct_keys.py --validate` for the offenders."
        )

    def test_the_committed_councils_set_is_wired_to_the_derivation(self):
        """Cheap structural pin, real-layer file so it travels with the checks above.

        The unit tests mock derive_precinct_keys entirely; this asserts the real
        module actually exposes the callable the commit path imports, with the
        keyword arguments it passes. A rename in derive_precinct_keys would otherwise
        only surface at 3am in the Railway log.
        """
        _skip_if_no_real_db()
        import inspect

        import derive_precinct_keys as dpk

        assert callable(dpk.run), "dcp_commit_approved imports run() from this module"
        params = inspect.signature(dpk.run).parameters
        for expected in ("council", "apply", "validate"):
            assert expected in params, (
                f"dcp_commit_approved calls run({expected}=...); the real signature is "
                f"{tuple(params)}"
            )
