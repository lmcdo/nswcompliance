"""scripts/dcp_extract_changed.py's run_fidelity_gate() -- the --review
post-enqueue grading pass -- verified against the REAL production database
and REAL R2-hosted PDF, not conftest_mocks.py's MagicMock stub.

Why this needs the real thing and not a mock, for gate_chapter() itself:
the bug this file guards against was a tuple-unpacking arity mismatch
(`g, f = gate_chapter(...)` against a function that returns 3 values, not
2) that a mock-based test cannot catch by construction -- a MagicMock call
happily returns whatever you tell it to, so a test built around a fake
gate_chapter() would just encode the same wrong arity as the buggy call
site and pass. The only way to prove gate_chapter() actually returns 3
values, for real, is to call the real function.

Sol cross-review (2026-09-09, on the push that first added this file)
caught two real problems in that first version, both fixed here:
  1. [HIGH] It called conn.commit() as a side effect of running the test,
     irreversibly mutating production dcp_review_queue rows every time
     someone runs the opt-in suite. Fixed: conn.rollback() in finally,
     never commit -- this test measures, it does not repair (same
     discipline as scripts/dq_db.py's own read-only guarantee).
  2. [MEDIUM] It called gate_chapter() directly rather than the actual
     integration call site in main(), so it could not catch a SECOND
     unpacking regression there. Fixed: run_fidelity_gate() was extracted
     out of main() into an importable, stubbable function (this file's
     other test class exercises THAT, with gate_chapter faked to return a
     literal 3-tuple -- catches the call site regressing even if
     gate_chapter's own signature never changes again).
  3. [MEDIUM] The registry SELECT was missing is_active = TRUE (this
     project's own pre-pr-review rule #1) -- fixed in run_fidelity_gate()
     itself, inherited here for free.

Opt-in via PYTEST_REAL_DB=1, @pytest.mark.database (deselected by default
per pytest.ini), following the exact convention tests/test_drawdown_verify_
real_db.py and tests/test_dcp_fidelity_gate_real_db.py already established.

Run it:
    PYTEST_REAL_DB=1 DATABASE_URL=<supabase pooler url> pytest -m database \
        tests/test_dcp_extract_changed_real_db.py -v
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

import dcp_fidelity_gate as gate  # noqa: E402  (after dotenv/marker setup)
import dcp_extract_changed as dx  # noqa: E402


def _skip_if_no_real_db():
    if not _REAL_DB_REQUESTED:
        pytest.skip(
            "Real-DB test. Run with: PYTEST_REAL_DB=1 DATABASE_URL=... "
            "pytest -m database tests/test_dcp_extract_changed_real_db.py"
        )
    if not os.environ.get("DATABASE_URL") and not os.environ.get("SUPABASE_DB_URL"):
        pytest.skip("PYTEST_REAL_DB=1 set but no DATABASE_URL/SUPABASE_DB_URL available.")
    required = ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME")
    if any(not os.environ.get(k) for k in required):
        pytest.skip("PYTEST_REAL_DB=1 set but R2 credentials are not available.")


def _real_s3_client():
    import boto3
    return boto3.client(
        "s3",
        endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def _real_conn():
    import psycopg2
    return psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL"))


class TestGateChapterReturnShapeAgainstRealData:
    def test_gate_chapter_return_value_unpacks_as_three_values_not_two(self):
        """The original regression: gate_chapter() must return a 3-tuple.
        NEVER COMMITS -- reads the current pending rows, grades them
        in-memory via gate_chapter()'s own UPDATE, then rolls back so this
        test has zero persistent effect on production data, however many
        times or by however many people it gets run (Sol HIGH 0.99)."""
        _skip_if_no_real_db()
        conn = _real_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT r2_current_path FROM dcp_chapter_registry "
                "WHERE council=%s AND chapter_key=%s AND r2_current_path IS NOT NULL "
                "AND is_active = TRUE",
                ("ashfield", "chapter-d-precinct-guidelines"),
            )
            row = cur.fetchone()
            assert row is not None, "fixture chapter must have a registered, active r2_current_path"

            result = gate.gate_chapter(cur, _real_s3_client(), "ashfield",
                                        "chapter-d-precinct-guidelines", row[0])

            # The regression IS the unpack -- this line is the actual test.
            # A pre-fix caller doing `g, f = result` raises ValueError here.
            grounded, flagged, skipped = result
            assert isinstance(grounded, int) and grounded >= 0
            assert isinstance(flagged, int) and flagged >= 0
            assert isinstance(skipped, int) and skipped >= 0
        finally:
            conn.rollback()  # never commit -- this test measures, it does not repair
            conn.close()


class TestRunFidelityGateCallSite:
    """Exercises the ACTUAL integration call site (run_fidelity_gate, the
    function main() calls), not just gate_chapter() in isolation -- Sol
    MEDIUM 0.99: the original version of this file could not have caught a
    second arity regression here even though this exact call site is where
    the original bug lived. gate_chapter is stubbed (a literal 3-tuple),
    so this class needs no real R2/PDF access -- only a real DB connection
    for the registry lookup, and it never writes (the stub never touches
    dcp_review_queue)."""

    def test_run_fidelity_gate_unpacks_and_sums_a_stubbed_three_tuple(self):
        _skip_if_no_real_db()

        class _StubGate:
            calls = []

            @staticmethod
            def gate_chapter(cur, s3, council, chapter_key, r2_path):
                _StubGate.calls.append((council, chapter_key, r2_path))
                return (5, 2, 1)  # grounded, flagged, skipped -- literal, not gate_chapter's real logic

        conn = _real_conn()
        try:
            review_chapters = [{"council": "ashfield", "chapter_key": "chapter-d-precinct-guidelines"}]
            g, f, s = dx.run_fidelity_gate(conn, s3=None, review_chapters=review_chapters,
                                            gate_module=_StubGate)
            assert (g, f, s) == (5, 2, 1)
            assert len(_StubGate.calls) == 1
            called_council, called_chapter, called_r2_path = _StubGate.calls[0]
            assert (called_council, called_chapter) == ("ashfield", "chapter-d-precinct-guidelines")
            assert called_r2_path, "r2_current_path must be non-empty for the active fixture row"
        finally:
            conn.rollback()
            conn.close()

    def test_run_fidelity_gate_skips_a_chapter_with_no_active_registry_row(self):
        """is_active = TRUE (Sol MEDIUM 0.9, this project's own pre-pr-review
        rule #1) -- a chapter with no matching ACTIVE row must be silently
        skipped (continue), not crash, and gate_chapter must never be called
        for it."""
        _skip_if_no_real_db()

        class _StubGate:
            calls = []

            @staticmethod
            def gate_chapter(*a, **k):
                _StubGate.calls.append((a, k))
                return (0, 0, 0)

        conn = _real_conn()
        try:
            review_chapters = [{
                "council": "ashfield",
                "chapter_key": "this-chapter-key-has-never-existed-in-either-table",
            }]
            g, f, s = dx.run_fidelity_gate(conn, s3=None, review_chapters=review_chapters,
                                            gate_module=_StubGate)
            assert (g, f, s) == (0, 0, 0)
            assert _StubGate.calls == [], "gate_chapter must not be called for an unregistered chapter"
        finally:
            conn.rollback()
            conn.close()
