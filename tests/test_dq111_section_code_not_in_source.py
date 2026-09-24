"""DQ-111: a served row's section code must be printed in its own source.

The probe's two ways of being wrong are both pinned here, each with a real case
from the 2026-09-24 corpus run:

* calling a genuine citation invented -- Waverley's refs join the headings
  above a rule (``B14_14_3_14_3_7`` = B14 > 14.3 > 14.3.7), so the joined string
  is absent while every piece of it is printed;
* calling an invented citation genuine -- Woollahra E2's ``C4.9`` is the
  extraction prompt's own example string, and it passed the first version of
  the path rule because "C4" is cross-referenced once in that chapter.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import dq_probe_section_code_not_in_source as p  # noqa: E402


def secs(tail):
    sections, item, reason = p.split_ref("Doc__chapter__" + tail)
    return [p.render(g) for g in sections], (p.render(item) if item else None), reason


class TestSplitRef:
    def test_section_and_item(self):
        assert secs("C4_9 C5") == (["C4.9"], "C5", None)

    def test_item_joined_by_underscore(self):
        assert secs("8_2_4_7_controls_C57") == (["8.2.4.7"], "C57", None)

    def test_parenthetical_subclause_is_not_part_of_the_code(self):
        assert secs("C2_2_1_2(a) C1") == (["C2.2.1.2"], "C1", None)  # noqa: zone-codes -- DCP section keys, not zones

    def test_two_section_groups_are_both_judged(self):
        assert secs("G9 G8_10_1 O2") == (["G9", "G8.10.1"], "O2", None)

    def test_bare_integer_is_declared_not_dropped(self):
        assert secs("6")[2] == "bare integer section (not discriminating)"

    def test_words_only_is_declared_not_dropped(self):
        assert secs("height_objectives")[2] == "no clause number in the ref"

    def test_part_word_is_not_a_code(self):
        # "Part 7" is a qualifier; the judged code is the design solution.
        assert secs("D-Part4_design_solution_DS5_7")[0] == ["DS5.7"]


class TestPresent:
    def test_boundary_rejects_longer_numbers(self):
        g = ("", ["4", "1"])
        assert not p.present(g, "see 14.1 and 4.12 only")
        assert p.present(g, "section 4.1 controls")

    def test_prefix_is_required(self):
        # Wollongong prints 4.2; a reader that adds "C" has changed the citation.
        assert not p.present(("C", ["4", "2"]), "4.2 site planning")


class TestPathKind:
    def test_waverley_joined_headings_are_traceable(self):
        text = "b14 advertising and signage 14.3 sign specific controls 14.3.7 murals"
        assert p.path_kind(("B", ["14", "14", "3", "14", "3", "7"]), text) == "path"

    def test_warringah_heading_number_needs_its_own_heading_words(self):
        text = "g1 dee why town centre ... 12 key sites applies to land"
        row = "# g1.12 o4 key sites to restrict vehicular access"
        assert p.path_kind(("G", ["1", "12"]), text, row) == "path_weak"

    def test_woollahra_prompt_example_is_not_rescued_by_a_cross_reference(self):
        # The confusable positive: "C4" IS printed (a cross-reference), and
        # "9" is printed everywhere. Neither makes C4.9 a heading in this chapter.
        text = "refer to chapter c4 for heritage. 9 other matters. e2.4 flood planning"
        row = "# c4.9 c5 flood planning levels habitable floors"
        assert p.path_kind(("C", ["4", "9"]), text, row) == "not_printed"

    def test_absent_part_is_not_printed(self):
        assert p.path_kind(("G", ["3", "10"]), "belrose corridor requirements", "# g3.10 o4 x y") \
            == "not_printed"


def test_heading_words_skip_the_code_tokens():
    assert p.heading_words("# g1.12 o4 key sites to restrict") == ["key", "sites"]
