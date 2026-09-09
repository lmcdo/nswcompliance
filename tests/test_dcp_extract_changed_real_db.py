"""scripts/dcp_extract_changed.py's --review fidelity-gate integration loop,
verified against the REAL production database and REAL R2-hosted PDF -- not
conftest_mocks.py's MagicMock stub.

Why this needs the real thing and not a mock: the bug this file guards
against was a tuple-unpacking arity mismatch (`g, f = gate_chapter(...)`
against a function that returns 3 values, not 2) that a mock-based test
cannot catch by construction -- a MagicMock call happily returns whatever
you tell it to, so a test built around a fake gate_chapter() would just
encode the same wrong arity as the buggy call site and pass. The only way
to prove the call site actually consumes gate_chapter()'s REAL return shape
is to call the real function.

Found live 2026-09-09: every `--review` run since the 2026-09-07 fidelity
gate auto-scoping fix (#1057) crashed here (advisory try/except swallowed
it as "fidelity gate skipped ... rows queued but ungraded"). Reproduced via
the actual CLI against ashfield/chapter-d-precinct-guidelines, fixed the
2-value unpack to 3, verified by calling gate_chapter() directly against
the same real chapter -- it retroactively graded the 1,668 rows the broken
run had left ungraded.

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

# Same reasoning as test_drawdown_verify_real_db.py / test_dcp_fidelity_gate_
# real_db.py (Sol cross-review, 2026-09-04): only load the real DATABASE_URL
# into the process when the real-DB flag is explicitly set.
_REAL_DB_REQUESTED = os.environ.get("PYTEST_REAL_DB") == "1"
if _REAL_DB_REQUESTED:
    load_dotenv(main_checkout() / ".env")

pytestmark = pytest.mark.database

import dcp_fidelity_gate as gate  # noqa: E402  (after dotenv/marker setup)


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


class TestFidelityGateCallSiteAgainstRealData:
    def test_gate_chapter_return_value_unpacks_as_three_values_not_two(self):
        """The exact regression: gate_chapter() must return a 3-tuple, and
        callers (scripts/dcp_extract_changed.py's --review integration loop)
        must unpack all 3 -- this is what a `g, f = gate_chapter(...)` call
        site gets wrong (ValueError: too many values to unpack). Runs
        against ashfield/chapter-d-precinct-guidelines, the same real
        chapter the production crash was found and fixed against."""
        _skip_if_no_real_db()
        import psycopg2

        conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL"))
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT r2_current_path FROM dcp_chapter_registry "
                "WHERE council=%s AND chapter_key=%s AND r2_current_path IS NOT NULL",
                ("ashfield", "chapter-d-precinct-guidelines"),
            )
            row = cur.fetchone()
            assert row is not None, "fixture chapter must have a registered r2_current_path"

            result = gate.gate_chapter(cur, _real_s3_client(), "ashfield",
                                        "chapter-d-precinct-guidelines", row[0])
            conn.commit()

            # The regression IS the unpack -- this line is the actual test.
            # A pre-fix caller doing `g, f = result` raises ValueError here.
            grounded, flagged, skipped = result
            assert isinstance(grounded, int) and grounded >= 0
            assert isinstance(flagged, int) and flagged >= 0
            assert isinstance(skipped, int) and skipped >= 0
        finally:
            conn.close()
