"""A citation must either resolve, or say that it does not.

WHY
---
`fetch_dcp_setbacks` puts `section_ref` straight into a field called `clause`,
which a conveyancer reads as the citation. Measured on production 2026-08-17,
of 967 served control rows:

    'LEP'  18 rows across 9 councils
    'ADG'  12 rows across 6 councils

Those name a whole instrument. A planner reading "ADG" opens the Apartment
Design Guide and does not find the control — the citation looks resolvable and
is not, which is worse than a blank.

The clause is NOT invented here. It lives in each council's LEP and in the ADG,
and choosing one would be the banned direction: removing a false claim cannot
create one, choosing a value can. So the value stops pretending.

THE PAIRS ARE THE POINT. A rule that rewrites everything is as wrong as one
that rewrites nothing, so both sides are pinned on real refs from the table.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))

from conveyancing_db import cite_clause  # noqa: E402


class TestABareInstrumentIsNotACitation:
    @pytest.mark.parametrize("ref,expected_name", [
        ("LEP", "Local Environmental Plan"),
        ("ADG", "Apartment Design Guide"),
        ("SEPP", "State Environmental Planning Policy"),
        ("DCP", "Development Control Plan"),
    ])
    def test_it_is_named_and_marked_unrecorded(self, ref, expected_name):
        out = cite_clause(ref)
        assert expected_name in out
        assert "no clause recorded" in out

    def test_the_acronym_alone_no_longer_stands_as_the_whole_citation(self):
        """The defect: 'ADG' rendered as if it located something."""
        assert cite_clause("ADG") != "ADG"

    def test_lower_case_is_treated_the_same(self):
        assert "no clause recorded" in cite_clause("adg")


class TestAnythingWithStructureIsLeftALONE:
    """These carry a locator. Imperfect ones still tell a reader where to look,
    and rewriting them would be a judgement per reference — out of scope."""

    @pytest.mark.parametrize("ref", [
        "part-c-table-cb",          # 19 served rows, canada_bay
        "part-L-definitions",
        "f-dwelling-houses",
        "c-open-space-landscape",
        "chapter-F",
        "C1.1",
        "3.6.2.2",
        "s3-7-2-5",
        "burwood-part4-residential.pdf#dwelling_house",
    ])
    def test_returned_unchanged(self, ref):
        assert cite_clause(ref) == ref

    def test_an_acronym_inside_a_longer_ref_is_not_rewritten(self):
        """'LEP Schedule 1' locates something; bare 'LEP' does not."""
        assert cite_clause("LEP Schedule 1") == "LEP Schedule 1"
        assert cite_clause("lep-schedule-solar") == "lep-schedule-solar"


class TestAbsenceStaysAbsence:
    @pytest.mark.parametrize("ref", [None, "", "   "])
    def test_no_ref_yields_no_citation_not_a_sentence(self, ref):
        """An empty ref must stay empty. Turning it into prose would invent a
        claim about an instrument nobody named."""
        assert cite_clause(ref) == ""


def test_the_rule_can_say_yes_and_no():
    """Control case.

    A stub returning its input unchanged passes every test in
    TestAnythingWithStructureIsLeftALONE, and a stub rewriting everything
    passes TestABareInstrumentIsNotACitation. Only pinning both on one line
    kills both mutants.
    """
    assert cite_clause("ADG") != "ADG"
    assert cite_clause("part-c-table-cb") == "part-c-table-cb"
