"""The approve step, against the REAL queue — and proof its dry run writes nothing.

On 2026-09-09, 8,875 queued rows were approved in one night and 578 bad rows
went live. `scripts/dcp_approve_graded.py` exists to not be that, and the two
things that make it different are structural rather than intentions: every row
carries a verdict from the fidelity gate as REPAIRED on 2026-09-22, and approval
is by NAMED CLASS with the class written into `review_reason` on each row.

Under `conftest_mocks.py` psycopg2 is stubbed, so `cur.fetchall()` yields
nothing: the plan comes back empty, the script prints "to approve: 0" and exits
cleanly. That is indistinguishable from "the queue is already clear". Opt-in via
PYTEST_REAL_DB=1 + @pytest.mark.database, deselected by pytest.ini.

    PYTEST_REAL_DB=1 DATABASE_URL=<supabase pooler url> pytest -m database \
        tests/test_dcp_approve_graded_real_db.py -v

THE ASSERTION THAT MATTERS MOST is that a dry run leaves the queue byte for byte
as it found it. A tool that writes when you asked it not to is worse than one
that refuses to write at all, and this one is pointed at the table that decides
what reaches a planner.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.dcp_approve_graded import _classify, _is_control_shaped  # noqa: E402

pytestmark = [
    pytest.mark.database,
    pytest.mark.skipif(
        os.getenv("PYTEST_REAL_DB") != "1",
        reason="needs the real psycopg2 driver; a stubbed one yields an empty "
               "plan, which reads exactly like an already-clear queue",
    ),
]


@pytest.fixture(scope="module")
def cur():
    sys.path.insert(0, str(ROOT / "scripts"))
    import dq_db

    conn = dq_db.connect()
    try:
        yield conn.cursor()
    finally:
        conn.close()


def _status_counts(cur):
    cur.execute("SELECT status, count(*)::int FROM dcp_review_queue GROUP BY 1")
    return dict(cur.fetchall())


class TestTheDryRunIsReallyDry:
    def test_it_writes_nothing_without_apply(self, cur):
        """The whole safety claim. Compared as a full status census rather than
        a pending count, so a row moved between two other statuses would show."""
        before = _status_counts(cur)
        done = subprocess.run(
            [sys.executable, "scripts/dcp_approve_graded.py"],
            cwd=ROOT, capture_output=True, text=True, timeout=900,
        )
        assert done.returncode == 0, done.stderr[-2000:]
        assert "DRY RUN" in done.stdout
        cur.connection.rollback()          # drop this session's snapshot
        assert _status_counts(cur) == before

    def test_it_refuses_without_a_database_rather_than_reporting_clean(self):
        done = subprocess.run(
            [sys.executable, "scripts/dcp_approve_graded.py"],
            cwd=ROOT, capture_output=True, text=True, timeout=120,
            env={**os.environ, "DATABASE_URL": "", "SUPABASE_DB_URL": ""},
        )
        assert done.returncode == 2
        assert "not a pass" in done.stderr


class TestEveryPendingRowGetsAReasonedVerdict:
    def test_no_row_is_classified_without_a_reason(self, cur):
        """A held row must say WHY it is held, or the person meeting it has
        nothing to act on."""
        cur.execute(
            """SELECT fidelity_status, fidelity_detail, source_page_verified, new_text
                 FROM dcp_review_queue WHERE status = 'pending'"""
        )
        for fidelity, detail, page, text in cur.fetchall():
            cls, reason = _classify(fidelity, detail, page, text)
            assert reason, "a verdict with no reason"
            if cls is None:
                assert len(reason) > 20, reason

    def test_the_classes_on_the_real_queue_are_the_documented_ones(self, cur):
        """A class appearing that the script's own `--classes` default does not
        list would be approved silently on the next run."""
        documented = {"grounded", "non_actionable", "reference_numbers",
                      "objective_label", "flagged_other"}
        cur.execute(
            """SELECT fidelity_status, fidelity_detail, source_page_verified, new_text
                 FROM dcp_review_queue WHERE status = 'pending'"""
        )
        seen = set()
        for fidelity, detail, page, text in cur.fetchall():
            cls, _ = _classify(fidelity, detail, page, text)
            if cls:
                seen.add(cls)
        assert seen <= documented, f"undocumented class: {seen - documented}"

    def test_a_control_shaped_number_is_always_held(self, cur):
        """The line between "approve" and "a person looks". A one-decimal number
        in planning range is the single most likely thing to BE a control."""
        cur.execute(
            """SELECT fidelity_status, fidelity_detail, source_page_verified, new_text
                 FROM dcp_review_queue
                WHERE status = 'pending' AND fidelity_detail LIKE '%numbers not in source%'"""
        )
        for fidelity, detail, page, text in cur.fetchall():
            import re

            m = re.search(r"numbers not in source: ([^;]+)", detail or "")
            if m and any(_is_control_shaped(x.strip()) for x in m.group(1).split(",")):
                cls, _ = _classify(fidelity, detail, page, text)
                assert cls is None, "a control-shaped number was approved"


class TestTheShapeOfTheClassifier:
    @pytest.mark.parametrize("tok,expected", [
        ("3.5", True), ("7.8", True), ("0.5", True), ("100.0", True),
        ("11", False), ("2660", False), ("01", False), ("04", False),
        ("0.4", False), ("628.18852", False), ("120.5", False),
    ])
    def test_control_shaped_is_a_decimal_in_planning_range(self, tok, expected):
        """Integers are page numbers, figure numbers and document references;
        a decimal between 0.5 and 100 is a setback, a height or an FSR. `01` is
        the objective LABEL bug, not a measurement."""
        assert _is_control_shaped(tok) is expected

    def test_reversed_text_is_never_approved(self):
        """DQ-104. There is nothing for a person to decide about mirrored text
        either, but it must not be approved on that account."""
        cls, reason = _classify(
            "grounded", None, 12,
            "# 5.2 kcabtes m0.2 etis yradnuob htaptoof")
        assert cls is None
        assert "reversed" in reason
