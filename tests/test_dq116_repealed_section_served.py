"""DQ-116: a section the council has repealed, still served as a live control.

Written to be MUTATION-RESISTANT. Three wrong versions must each fail a test:

  * `return None`                      -> a detector that never fires
  * mark ANYWHERE counts               -> would flag 67 correctly-served rows,
                                          because `(a) (Repealed) (b) ...` is
                                          how NSW legislation is drafted
  * scan back for the sentence start   -> evidence begins mid-section-number

No database: `detect_repealed_section` is pure, so every case here is a real
end-to-end run of the function the ledger's probe calls.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

from dcp_extract_changed import detect_repealed_section as detect  # noqa: E402


# The real row, verbatim from production (id 127014), trimmed.
WOOLLAHRA_B33 = (
    "# B3.3 Floorplate (Repealed)\n\n"
    "Part B | General Residential B3 | General Development Controls "
    "B3.3 Floorplate (Repealed) This section was repealed by Woollahra "
    "Development Control Plan 2015 (Amendment 36) on 21 August 2026. "
    "21 August 2026 Woollahra Development Control Plan 2015 B3 pg.17"
)


class TestItFires:
    def test_the_real_row(self):
        why = detect("", WOOLLAHRA_B33)
        assert why is not None
        assert "repealed by Woollahra" in why

    def test_evidence_names_the_instrument_and_the_date(self):
        """A flag with no quote cannot be checked against the plan, which is
        the whole reason this returns a string rather than True."""
        why = detect("", WOOLLAHRA_B33)
        assert "Amendment 36" in why and "21 August 2026" in why

    def test_evidence_does_not_begin_mid_section_number(self):
        """REGRESSION. The first version scanned BACK to the previous full
        stop to find the sentence start, and the nearest '.' is the one inside
        'B3.3' - so the evidence came out as '3 Floorplate This section was
        repealed by...', starting mid-number."""
        why = detect("", WOOLLAHRA_B33)
        assert why.startswith("This section was repealed")
        assert not why.startswith("3 ")

    def test_title_marked_without_a_sentence(self):
        why = detect("", "# B3.3 Floorplate (Repealed)\n\nbody text with no sentence")
        assert why is not None and "B3.3 Floorplate (Repealed)" in why

    @pytest.mark.parametrize("word", ["Repealed", "Deleted", "Revoked"])
    def test_the_three_title_markings(self, word):
        assert detect("", "# A1.2 Something (%s)\n\nbody" % word) is not None

    @pytest.mark.parametrize("verb", ["was repealed", "has been repealed",
                                      "is repealed", "was deleted", "was revoked"])
    def test_the_sentence_forms(self, verb):
        assert detect("", "# X\n\nThis section %s by Amendment 4 on 1 May 2025." % verb)

    def test_section_header_is_used_when_the_text_has_no_heading_line(self):
        assert detect("B3.3 Floorplate (Repealed)", "body text only") is not None


class TestItDoesNotFireOnCorrectlyServedRows:
    """67 of the 68 rows carrying repeal wording are these. Flagging them would
    be worse than not checking: it would push toward deleting a paragraph the
    council deliberately left in place."""

    def test_inline_repealed_subparagraph_is_a_live_clause(self):
        assert detect("", "(a) (Repealed) (b) not have an area more than 25 m2") is None

    def test_inline_under_a_clean_title(self):
        assert detect("", "# A1.1.6 Definitions\n\nO5 (Repealed) O6 To establish a "
                          "consistent set of definitions") is None

    def test_the_live_plan_doing_the_repealing(self):
        """Leichhardt A1.2 lists the plans IT repeals. It is the current plan."""
        assert detect("", "# A1.2 PLANS REPEALED BY THIS PLAN\n\nThe following Plans "
                          "are repealed by this Development Control Plan, except to "
                          "the extent that those Plans shall continue to apply") is None

    def test_the_lighthouse(self):
        """The sentence that defeated the document-level rule's first version:
        passive voice, named agent, perfect grammar - and about a lighthouse in
        a heritage chapter's history."""
        assert detect("", "# C3 Watsons Bay HCA\n\nThis was later replaced by a "
                          "number of lighthouses including the existing Hornby "
                          "Light, and the harbour") is None

    def test_amendment_history_prose(self):
        assert detect("", "# A1 Introduction\n\nClause 4.6 was repealed by "
                          "Amendment 5 in 2019, and the current controls are below") is None

    def test_clean_control(self):
        assert detect("", "# B3.1 Site Coverage\n\nThe maximum site coverage is 60%.") is None


class TestItCannotCrashTheLedger:
    @pytest.mark.parametrize("header,text", [
        ("", ""), ("", None), (None, None), (None, ""),
        ("", "   \n\n  "), ("", "#"), ("", "# \n\n"),
    ])
    def test_empty_and_degenerate_input(self, header, text):
        assert detect(header, text) is None

    def test_evidence_is_capped(self):
        long_tail = "x" * 900
        why = detect("", "# X\n\nThis section was repealed by %s" % long_tail)
        assert why is not None and len(why) <= 200

    def test_a_row_with_no_heading_line_does_not_read_the_body_as_a_title(self):
        """A statute sub-paragraph starts straight into body text. If the body's
        first line were treated as the title, every inline `(a) (Repealed)`
        would flag."""
        assert detect("", "(1) (Repealed) (2) A public authority must not") is None


class TestRegisteredCorrectly:
    def test_the_probe_is_in_the_ledger_and_needs_a_database(self):
        import dq_probe_unchecked_rows as m
        headline, means, fn, needs_db = m.PROBES["DQ-116"]
        assert needs_db is True
        assert fn is m.probe_116
        assert headline and means

    def test_the_ledger_row_points_at_this_probe(self):
        """Pins the WIRING, not the status.

        The first version also asserted `declared == "open"`. That broke in CI
        the moment the defect was actually fixed and the row moved to "fixed" —
        a test that fails BECAUSE the problem was solved. Worse, it duplicated
        dq_check.py, whose entire job is to police declared-vs-live in both
        directions; two copies of that rule can only ever disagree, and the one
        that loses is the test somebody edits to go green.

        So: the row must exist, and it must point at this probe. Whether it
        currently reads open or fixed is the ledger's business.
        """
        import io
        import json
        d = json.load(io.open(ROOT / ".claude" / "dq_checks.json", encoding="utf-8"))
        row = d["checks"]["DQ-116"]
        assert row["check"] == ["python", "scripts/dq_probe_unchecked_rows.py",
                                "--id", "DQ-116"]
        assert row["declared"] in {"open", "fixed"}

    def test_the_document_level_guard_is_untouched(self):
        """This branch adds a sibling; it must not have altered the hard reject
        that keeps archive editions out in the first place."""
        from dcp_extract_changed import detect_repealed_stamp
        assert detect_repealed_stamp(
            ["Repealed by WDCP 2015 Amendment No. 13 on 12 October 2020"])
        assert detect_repealed_stamp(
            ["This was later replaced by a number of lighthouses"]) is None
