"""Offline tests for the approval decision in scripts/dcp_approve_proven.py (no DB, no PDFs)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import dcp_approve_proven as ap  # noqa: E402

LONG = "Development must provide a landscaped front setback of at least 3 metres."


def test_exact_long_sentence_start_is_approved():
    assert ap.plain_approvable("exact", LONG) is True


@pytest.mark.parametrize("status", ["recovered", "unconfirmed", "not_a_control", ""])
def test_not_exact_is_not_approved(status):
    assert ap.plain_approvable(status, LONG) is False


def test_too_short_is_not_approved():
    assert ap.plain_approvable("exact", "Cool roofs") is False  # < MIN_CHARS


def test_starts_lowercase_is_not_approved():
    assert ap.plain_approvable("exact", "the rich mixture of materials and finishes is retained") is False


def test_orphan_lead_in_is_not_approved():
    assert ap.plain_approvable("exact", "The objectives of this Part of the DCP are to:") is False


def test_long_text_ending_colon_is_not_an_orphan():
    body = "Development must " + "x" * 300 + ":"
    assert ap.plain_approvable("exact", body) is True


def test_removed_row_outside_removals_not_approved():
    assert ap.removal_decision("removed", False) == "left_removed"


def test_removed_row_inside_removals_approved():
    assert ap.removal_decision("removed", True) == "approve_removal"


def test_non_removal_untouched_by_removal_rule():
    assert ap.removal_decision("added", True) is None
    assert ap.removal_decision("changed", False) is None


def test_rows_only_from_active_pdf():
    sql = " ".join(ap.CHAPTER_ROWS_SQL.split())
    assert "reg.is_active" in sql
    assert "q.source_content_hash = COALESCE(reg.staged_content_hash, reg.content_hash)" in sql
    assert "q.status = 'pending'" in sql


def test_constants_unchanged():
    assert ap.REVIEWER == "auto:council_quote"
    assert ap.REASON.startswith("printed word for word in the current PDF")
    assert ap.cq.MIN_CHARS == 25


def test_mutation_always_approve_fails_suite(monkeypatch):
    """A decision that always approves must be caught by the rejection cases above."""
    monkeypatch.setattr(ap, "plain_approvable", lambda status, body: True)
    with pytest.raises(AssertionError):
        test_not_exact_is_not_approved("unconfirmed")
    with pytest.raises(AssertionError):
        test_orphan_lead_in_is_not_approved()
    with pytest.raises(AssertionError):
        test_too_short_is_not_approved()
    with pytest.raises(AssertionError):
        test_starts_lowercase_is_not_approved()
