"""`--phase status` must actually execute against the real schema.

WHY THIS FILE EXISTS. get_enrichment_status() counted
`v2_enriched_at IS NOT NULL`, and that column exists on no table in this database.
Every invocation raised psycopg2.errors.UndefinedColumn. The report had been dead
for as long as that was true, and two warning messages in the commit and extract
workers told operators to run it when enrichment failed -- so the instruction
given at the moment something went wrong pointed at a command that crashed.

No test could catch it without a database: the column name lives inside a SQL
string, so the type checker cannot see it and a mocked psycopg2 answers a
MagicMock to anything. The repo HAS a gate for exactly this class
(scripts/validate_schema_contract.py, "code vs live catalog", wired into CI) but
it scans only `frontend-nextjs/app/api` and `services` -- not `enrichment` or
`scripts`, which is where most of the database-writing code lives.

Opt-in, per the convention in tests/test_lga_coverage.py: conftest_mocks.py stubs
psycopg2 unless PYTEST_REAL_DB=1, so without the flag this would assert against a
mock and pass whatever the schema said.

Run it:
    PYTEST_REAL_DB=1 DATABASE_URL=<supabase pooler url> pytest -m database \\
        tests/test_pipeline_status_real_db.py -v
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
            "pytest -m database tests/test_pipeline_status_real_db.py"
        )
    if not os.environ.get("DATABASE_URL") and not os.environ.get("SUPABASE_DB_URL"):
        pytest.skip("PYTEST_REAL_DB=1 set but no DATABASE_URL/SUPABASE_DB_URL available.")


def test_the_status_report_runs_against_the_live_schema():
    """The whole point: execute the query, so a column that does not exist raises.

    This is the test that was missing. It fails loudly on the pre-fix code with
    UndefinedColumn: column "v2_enriched_at" does not exist.
    """
    _skip_if_no_real_db()
    from enrichment.pipeline import get_enrichment_status

    status = get_enrichment_status()
    assert status["total_provisions"] > 0, "the corpus cannot be empty"
    assert status["actionable"] > 0
    # Every key the CLI prints must be present, or `--phase status` KeyErrors
    # instead -- swapping one crash for another.
    for key in ("total_provisions", "actionable", "boilerplate",
                "with_numeric_values", "without_numeric_values",
                "site_condition_tagged", "heritage", "flood", "bushfire",
                "general_no_condition", "type_classified", "type_control",
                "type_objective", "type_definition", "type_note",
                "type_procedural"):
        assert key in status, f"the CLI prints status[{key!r}] and it is missing"


def test_the_removed_metrics_are_really_gone():
    """`enriched`, `pending` and `enrichment_pct` measured a column that never
    existed. They were deleted rather than repointed at a surviving column,
    because inventing a new definition of "enriched" is choosing a value where
    deleting a dead metric only removes a claim.

    Pinned so a later change cannot quietly reintroduce them against whichever
    column happens to be handy."""
    _skip_if_no_real_db()
    from enrichment.pipeline import get_enrichment_status

    status = get_enrichment_status()
    for gone in ("enriched", "pending", "enrichment_pct"):
        assert gone not in status, (
            f"{gone!r} is back. If an enrichment-coverage metric is wanted, define "
            f"it against a column that exists and say which, in the report itself."
        )
