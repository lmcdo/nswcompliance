"""The pipeline already knew which rows were broken, and queued them for a human anyway.

`check_provision()` grades EVERY extracted provision for serious artifacts. Its result was
then collapsed to a per-chapter COUNT (`serious_flagged` -> `is_schema_fail`) and the row
identity discarded. So a chapter could report

    schema_fail (12/49 provisions with serious artifacts)

while all 49 rows were enqueued `pending`, and `dcp_fidelity_gate` — which scores only
words of four or more letters — then re-judged them and returned

    39 grounded, 3 ok, 3 flagged

Both numbers are from the same run, canterbury_bankstown/chapter-7-5, 2026-09-22. Two
detectors in one pipeline disagreeing, and the one that gates approval is the blind one.

A row whose OWN TEXT is machine-detectably broken is not a judgement call and must not wait
on a human, because the human never comes: DQ-29 sat "P1, 22 rows remain for re-extraction"
for ten weeks, and on 2026-09-09 a backlog of 8,875 rows was cleared in a single night,
pushing 578 bad rows into production.

Measured over 2,416 live pending rows before this shipped: 16 carry a serious artifact
(0.7%), and ELEVEN of those are currently graded `grounded` — approvable today.

DIRECTION: this can only move a row pending -> rejected. A rejected row leaves the existing
provision current (no silent drop), so a false positive costs a stale chapter, which is
visible, never wrong text served, which is silent.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

dx = pytest.importorskip("scripts.dcp_extract_changed")


class TestItNamesTheBrokenRows:
    """The per-row verdict must survive, not be collapsed into a count."""

    def test_a_two_column_interleave_row_is_named(self):
        """Canterbury-Bankstown's shape: the Objectives/Controls columns merged."""
        text = ("Objectives Controls\n"
                "O1 Provide deep soil area C1 A minimum of 15% of the site area\n"
                "O2 Retain existing trees C2 No removal of trees over 5m")
        assert "two_col_interleave" in dx._serious_artifacts(text)

    def test_a_clean_control_is_not_named(self):
        text = ("a) The height of development must not exceed 9.5 metres above "
                "existing ground level.\n"
                "b) A minimum front setback of 6 metres applies.")
        assert dx._serious_artifacts(text) == []

    @pytest.mark.parametrize("text", ["", None, "   "])
    def test_empty_text_is_not_an_artifact(self, text):
        """A removed row carries new_text=None and must not be rejected for it."""
        assert dx._serious_artifacts(text) == []

    def test_only_SERIOUS_labels_count(self):
        """check_provision also returns advisory labels such as short_provision. Those
        must NOT reject a row -- a genuinely short rule ('No fences forward of the
        building line.') is a real control, not a defect."""
        got = dx._serious_artifacts("No fences forward of the building line.")
        assert got == [], f"an advisory label leaked into the rejecting set: {got}"


class TestTheRejectionIsWiredIntoTheEnqueuePath:
    """Source-level, because enqueue_review_changes needs a live connection. The
    behavioural half is covered by tests/test_dcp_review_enqueue.py, which stubs this
    same seam."""

    @staticmethod
    def _enqueue_src() -> str:
        src = (ROOT / "scripts" / "dcp_extract_changed.py").read_text(encoding="utf-8")
        start = src.index("def enqueue_review_changes")
        return src[start:src.index("\ndef ", start + 10)]

    def test_the_enqueue_path_asks_for_the_row_s_own_artifacts(self):
        assert "_serious_artifacts(new_t)" in self._enqueue_src(), (
            "the enqueue path no longer checks the row's own text, so a row the "
            "extractor already identified as broken is queued for a human again")

    def test_an_artifact_row_cannot_be_pending(self):
        block = self._enqueue_src()
        assert 'row_status = "rejected" if (auto_reject or artifact_labels) else "pending"' in block, (
            "a serious artifact must force 'rejected'; leaving it 'pending' is the "
            "exact regression this test exists for")

    def test_the_reason_records_which_artifacts(self):
        """'rejected' with no reason is unactionable -- the next person cannot tell a
        real defect from an over-eager guard."""
        block = self._enqueue_src()
        assert "artifact_note" in block and "artifacts: " in block

    def test_the_serious_set_is_not_silently_narrowed(self):
        """Dropping a label here would re-open the hole without any test failing
        elsewhere. latex_tokens is DQ-76; two_col_interleave is DQ-78."""
        for label in ("latex_tokens", "two_col_interleave", "two_col_numeric",
                      "word_cross_references", "toc_dotted_leaders"):
            assert label in dx.SERIOUS_ARTIFACT_LABELS, f"{label} was removed"
