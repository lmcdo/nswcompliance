"""A citation read off the page is offered only if it proves, and only if it is the only answer.

Each case is a shape met in the 2026-09-24 sizing run over the 5,167 unproven
served rules, paired with the confusable case that must NOT produce a fix.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import citation_derive as cd  # noqa: E402
import citation_proof as cp  # noqa: E402

BODY = "the quick council wording of this particular rule sits right here on the page"


def readings(*pages):
    raw = []
    for pno, lines in enumerate(pages, 1):
        raw.append(cp.Line(pno, 10.0, 70.0, f"header of page {pno}"))
        for n, t in enumerate(lines):
            raw.append(cp.Line(pno, 100.0 + 20 * n, 70.0, t.lower()))
        raw.append(cp.Line(pno, 800.0, 300.0, str(pno)))
    return cp.both_orders(raw, 595.0)


def derive(ref, rd, text=BODY):
    return cd.derive_citation(f"Doc__chap__{ref}", f"# code title\n\n{text}", rd)


def test_prompt_example_is_replaced_by_the_printed_heading():
    rd = readings(["e2.4 flood planning", "c5 " + BODY])
    r = derive("C4_9 C5", rd)
    assert (r["status"], r["code"]) == ("derived", "E2.4 C5")


def test_an_objective_label_is_never_taken_for_the_section():
    # The sizing prototype offered "O2 C1": O2 sat at a line start above the rule.
    labels = [f"o{n} to protect the amenity of neighbours" for n in range(1, 6)] + [f"c{n} buildings are to be articulated" for n in range(1, 5)]
    rd = readings(["g6.14 building materials"] + labels + ["c5 " + BODY])
    r = derive("G8_6_4 C5", rd)
    assert (r["status"], r["code"]) == ("derived", "G6.14 C5")


def test_wording_printed_under_two_sections_is_not_decided_by_code():
    rd = readings(["1.7 first", "o1 " + BODY], ["1.8 second", "o1 " + BODY])
    assert derive("E1_8 O1", rd)["status"] == "ambiguous"


def test_a_label_is_never_traded_for_a_coarser_citation():
    rd = readings(["4.2 site planning", BODY])            # page prints no label
    assert derive("C4_2 C3", rd)["status"] == "not_derivable"


def test_a_row_that_never_had_a_label_gets_the_section_alone():
    rd = readings(["4.2 site planning", BODY])
    r = derive("C4_2", rd)
    assert (r["status"], r["code"]) == ("derived", "4.2")


def test_councils_own_label_style_is_deferred_not_guessed():
    rd = readings(["e7 open space", "7. " + BODY])
    assert derive("E7 C7", rd)["status"] == "deferred"


def test_nothing_is_offered_when_no_heading_proves():
    rd = readings(["some words with no code at all", BODY])
    assert derive("C4_9", rd)["status"] == "not_derivable"


class TestRewriteHeading:
    """Only the stored code at the start of the first line changes; nothing else."""

    @staticmethod
    def rw(*a):
        import dcp_restore_citations as r
        return r.rewrite_heading(*a)

    def test_code_swapped_title_and_body_untouched(self):
        text = "# C4.9 C5 Special consideration\n\nAll FPLs and EPLs represent the minimum"
        assert self.rw(text, "C4_9 C5", "E2.4 C5") == \
            "# E2.4 C5 Special consideration\n\nAll FPLs and EPLs represent the minimum"

    def test_underscore_dot_and_space_are_the_same_code(self):
        assert self.rw("# 8.2.4.7 controls C57 x\n\nbody", "8_2_4_7_controls_C57", "8.2.4.7 C57") \
            == "# 8.2.4.7 C57 x\n\nbody"

    def test_code_is_matched_whole_not_as_a_prefix_of_a_longer_one(self):
        # "C4.1" must not be read as the start of "C4.12".
        assert self.rw("# C4.12 C1 title\n\nbody", "C4_1 C1", "X1") is None  # noqa: zone-codes -- DCP section keys, not zones

    def test_a_first_line_that_does_not_start_with_the_code_is_refused(self):
        assert self.rw("# Special consideration\n\nbody", "C4_9 C5", "E2.4 C5") is None
        assert self.rw("no heading line at all", "C4_9 C5", "E2.4 C5") is None


def test_an_unlabelled_rule_that_starts_mid_section_is_not_fixed():
    # Woollahra B1.1.5: the stored text opens with B1.1.4's closing lines, so the
    # heading above its start is the wrong rule's. Re-read, never "correct" it.
    filler = [f"line {w} of the earlier clause text" for w in ("one", "two", "three", "four", "five")]
    rd = readings(["b1.1.4 relationship to other parts"] + filler + [BODY])
    assert derive("B1_1_5", rd)["status"] == "not_derivable"


def test_a_fix_never_leaves_the_rules_own_chapter():
    rd = readings(["e1 heritage", "c3 " + BODY])
    assert cd.derive_citation("Doc__B3_7 C3", "# t\n\n" + BODY, rd, chapter_lead="b3")["status"] \
        == "not_derivable"
    assert cd.chapter_leading(["B3.1", "B3.2.1", "B3.7", "E1"]) == "b3"  # noqa: zone-codes -- DCP section keys, not zones
    assert cd.chapter_leading(["B3.1", "E1.2"]) is None  # noqa: zone-codes -- no majority, no constraint


def test_a_label_is_never_added_to_a_citation_that_had_none():
    # Woollahra C1.3.9: the stored text opens with C1.3.8's last control, C22.
    rd = readings(["c1.3.8 earlier section", "c22 " + BODY])
    assert derive("C1_3_9", rd)["status"] == "not_derivable"


class TestRepairRefusesUnsafeRuns:
    """Cross-review 2026-09-24: the unsafe invocations are refused before any connection."""

    @staticmethod
    def main_with(monkeypatch, *argv):
        import pytest
        import dcp_restore_citations as r
        monkeypatch.setattr(sys, "argv", ["dcp_restore_citations.py", *argv])
        with pytest.raises(SystemExit) as e:
            r.main()
        return e.value.code

    def test_apply_needs_a_council(self, monkeypatch):
        assert self.main_with(monkeypatch, "--apply") == 2

    def test_audit_share_is_bounded(self, monkeypatch):
        assert self.main_with(monkeypatch, "--audit-share", "2") == 2
        assert self.main_with(monkeypatch, "--audit-share", "0") == 2


# --- Exceptions met in the whole-fixer test of 2026-09-25 (broken labels on
# proven rules, plus the real dry run). Each pairs with the case that must still fix.

def test_a_labelled_copy_elsewhere_does_not_place_an_unlabelled_rule():
    # Warringah: the rule on p119 has bullets; a summary table on p164 repeats it beside "O15".
    rd = readings(["b9 rear building setback", "objectives", "• " + BODY],
                  ["filler"] * 3, ["r14.2 buildings are oriented", "o15 " + BODY])
    assert derive("G3_9 O1", rd)["status"] != "derived"


def test_a_printed_stored_section_is_not_swapped_for_another_section():
    # Marrickville 9.40.4.2 -> "B2" (a zone name), Canterbury-Bankstown 11.12 ->
    # "section 3.3 for ..." (a cross-reference): the stored section was printed and right.
    rd = readings(["e2.3 other matters", "c1 some other words"], ["e2.4 flood planning", "c5 " + BODY])
    assert derive("E2_3 C5", rd)["status"] != "derived"
    assert derive("E2_4_1 C5", rd)["code"] == "E2.4 C5"      # stored section not printed: fixed


def test_a_printed_stored_label_beside_the_rule_is_kept(monkeypatch):
    # Canterbury-Bankstown 2.2.5: two columns put "p1." beside "p4.", and P1 proved.
    rd = readings(["e2.4 flood planning", "c4", "c1 " + BODY])
    assert cd.stored_label_beside("Doc__E2_4 C4", BODY, rd, None) == "c4"
    assert cd.stored_label_beside("Doc__E2_4 C9", BODY, rd, None) is None
    rd = readings(["e2.4 flood planning", "c5 " + BODY])
    assert derive("E2_4 C7", rd)["code"] == "E2.4 C5"         # stored label not printed: fixed
    monkeypatch.setattr(cd, "stored_label_beside", lambda *a: "c7")
    assert derive("E2_4 C7", rd)["status"] != "derived"       # printed beside: kept


def test_a_cross_reference_ending_in_a_bracket_is_not_a_heading():
    # Leichhardt: "...(see C1.11.7 Recognised shopping streets)" proved C1.11.7.
    assert not cp._heading_like(cp.Line(1, 100.0, 70.0, "c1.11.7 recognised shopping streets)"), 595.0)
    assert cp._heading_like(cp.Line(1, 100.0, 70.0, "c1.11.7 recognised shopping streets"), 595.0)


def test_the_second_reading_agrees_only_with_the_nearest_heading_and_the_label_beside():
    rd = readings(["e2.3 other matters", "c1 some other words", "e2.4 flood planning", "c5 " + BODY])
    text = "# x\n\n" + BODY
    assert cd.page_agrees("Doc__E2_4 C5", text, rd)
    assert not cd.page_agrees("Doc__E2_3 C5", text, rd)      # a heading further up
    assert not cd.page_agrees("Doc__E2_4 C6", text, rd)      # label not the one printed
    assert not cd.page_agrees("Doc__C5", text, rd)           # no section at all


def test_a_bare_item_label_is_not_a_citation():
    # The cheap reader returned "C12" for "C2.2.2.3 C12"; the label's own line made it pass.
    labels = [f"c{n} buildings are to be articulated" for n in range(1, 6)]
    rd = readings(["e2.4 flood planning"] + labels + ["c6", BODY])
    assert cd.page_agrees("Doc__E2_4 C6", "# x\n\n" + BODY, rd)
    assert not cd.page_agrees("Doc__C6", "# x\n\n" + BODY, rd)


def test_a_bare_stored_label_gets_its_section_added():
    # Marrickville stored "C38": the section was lost, the label was right.
    labels = [f"c{n} buildings are to be articulated" for n in range(1, 6)]
    rd = readings(["e2.4 flood planning"] + labels + ["c6", BODY])
    assert derive("C6", rd)["code"] == "E2.4 C6"


def test_an_invented_preamble_heading_is_replaced_whole():
    import dcp_restore_citations as R
    t = "# preamble Document Information — Objectives — O17 To Ensure\n\nbody"
    assert R.rewrite_heading(t, "preamble_objectives_O17", "2.3 O17") == "# 2.3 O17 To Ensure\n\nbody"
    assert R.rewrite_heading("# preamble Document Information — C4 x\n\nb", "preamble_O3", "2.3 O3") is None
