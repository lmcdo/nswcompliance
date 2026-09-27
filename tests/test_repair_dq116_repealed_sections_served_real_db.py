"""DQ-116's repair, verified against the REAL production database.

`find_rows()` is the half that decides which rows the repair touches, and every
other test of this work stops at a pure function: `detect_repealed_section` is
tested exhaustively in tests/test_dq116_repealed_section_served.py, but that
proves the RULE, not that the rule and the SQL pre-filter in front of it see the
same population. That seam is where this already went wrong once — a first
pre-filter used '%was repealed%' and never showed the rule nsw_statewide 3.29,
whose text reads "is repealed at the end of". A narrower filter than the rule is
invisible: nothing errors, the count is simply lower.

So this asserts the property that matters and cannot be checked with a mock:
**the repair and DQ-116's probe select the same rows.** If they ever diverge, the
check goes green over rows the repair will not touch, or the repair touches rows
nobody reviewed.

READ-ONLY. It never calls the --apply path; dq_db hands out a read-only session.

Opt-in per this repo's convention (tests/test_drawdown_verify_real_db.py,
tests/test_lga_coverage.py): conftest_mocks.py stubs psycopg2 by default, so a DB
test would otherwise get a MagicMock and fail on nonsense comparisons.

    PYTEST_REAL_DB=1 DATABASE_URL=<supabase pooler url> pytest -m database \\
        tests/test_repair_dq116_repealed_sections_served_real_db.py -v
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

pytestmark = [
    pytest.mark.database,
    pytest.mark.skipif(
        os.environ.get("PYTEST_REAL_DB") != "1",
        reason="needs the real psycopg2 driver and a live DATABASE_URL; "
               "conftest_mocks.py stubs psycopg2 by default",
    ),
]


def _repair_module():
    """Load the repair by path — its filename is not an importable module name."""
    path = ROOT / "scripts" / "repair_dq116_repealed_sections_served.py"
    spec = importlib.util.spec_from_file_location("repair_dq116", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def rows():
    import dq_db
    repair = _repair_module()
    with dq_db.session() as conn, conn.cursor() as cur:
        return repair.find_rows(cur)


def test_find_rows_runs_against_the_real_driver(rows):
    """A MagicMock cursor would return a Mock here, not a list."""
    assert isinstance(rows, list)


def test_every_selected_row_carries_the_councils_own_sentence(rows):
    """The repair must never touch a row it cannot quote a reason for — the
    evidence is what a person adjudicates, and a bare id is not reviewable."""
    for r in rows:
        assert r["evidence"], "row %s selected with no evidence" % r["id"]
        assert len(r["evidence"]) > 10


def test_the_repair_and_the_probe_select_the_same_rows(rows):
    """THE POINT OF THIS FILE. A pre-filter narrower than the rule is a silent
    miss; one wider than the rule means the repair would touch unreviewed rows.
    Both are invisible without comparing the two populations directly."""
    import dq_db
    import dq_probe_unchecked_rows as probe

    with dq_db.session() as conn, conn.cursor() as cur:
        count, detail = probe.probe_116(cur)

    assert count == len(rows), (
        "DQ-116 reads %d and the repair would select %d — the check and the "
        "repair disagree about what the defect is" % (count, len(rows))
    )
    probe_evidence = sorted(e for _, e in detail)
    repair_evidence = sorted(r["evidence"] for r in rows)
    assert probe_evidence == repair_evidence


def test_the_repair_is_idempotent_after_its_own_apply(rows):
    """It ran against production on 2026-09-27 and took DQ-116 from 2 to 0.

    This deliberately asserts ZERO rather than a number: any non-zero means a
    repealed section has entered the served set since, which is exactly the
    regression DQ-116 exists to catch — the detector is not yet wired into the
    write path, so a chapter re-extraction can put one back.
    """
    assert rows == [], (
        "%d repealed section(s) are served again: %s"
        % (len(rows), [r["ref_number"] for r in rows])
    )


def test_it_never_writes_on_the_read_path():
    """dq_db hands out a read-only session; the --apply path opens its own
    connection. If find_rows ever acquired write access this would fail."""
    import dq_db
    with dq_db.session() as conn, conn.cursor() as cur:
        with pytest.raises(Exception):
            cur.execute("UPDATE regulatory_provisions SET v2_is_actionable = "
                        "v2_is_actionable WHERE id = -1")
