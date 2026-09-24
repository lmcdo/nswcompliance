"""DQ-107 — the gate an LGA must pass before a config can be written for it.

An applicability config is keyed on a `document_id` or on a section code read
out of the provision text. Both assume the code identifies ONE thing. Where a
registered document is really several plans concatenated, the same code appears
under each of them with a different scope, and no entry can be written that is
true of all of them — whatever is declared mis-scopes the rest.

WHY THE RULE IS "DISJOINT DEVELOPMENT TYPES" and not "different text". Measured
2026-09-24 across the whole served set:

    same code, any differing heading text   1,180 pairs  ordinary provision
                                                         splitting — noise
    same code, differing scope SENTENCES       35 pairs
    ...naming DISJOINT development types        1 pair   the real defect

The 34 near-misses are the confusable negatives, and they are real rows rather
than invented ones:

  * woollahra pairs "all land within the Woollahra municipality" with
    "development that requires development consent" — a land scope and a
    development scope, both true of the same chapter at once.
  * city_of_sydney's are the boilerplate "to the extent of the inconsistency".
  * three parramatta pairs are the SAME sentence twice, once clean and once
    carrying HTML table debris from extraction.
  * parramatta 9.10.x pairs two street addresses, which name no development
    type at all.

A detector keyed on "the text differs" calls all 1,180 a defect. One keyed on
"the scope sentences differ" still calls 35. Only "these scopes cannot both be
true of one provision" isolates the case a config genuinely cannot express.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from dq_probe_unchecked_rows import probe_107, _SCOPE_SENTENCE  # noqa: E402


class FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    def execute(self, *_a, **_k):
        return None

    def fetchall(self):
        return self._rows


def _row(text, council="somewhere", doc="Some_Council_DCP__part_b"):
    return (council, doc, text)


def _count(rows):
    count, detail = probe_107(FakeCursor(rows))
    return count, detail


class TestTheRealDefect:
    def test_one_code_two_exclusive_plans_is_flagged(self):
        """Cumberland's shape, which is what this exists for: five sub-parts
        sharing a document_id, each with its own '1.1 Land to which this Part
        applies' naming a different development type."""
        count, detail = _count([
            _row("# 1.1 Land to which this Part applies This Part applies to "
                 "residential flat building development under the LEP."),
            _row("# 1.1 Land to which this Part applies This Part applies to "
                 "development of land for the purposes of a boarding house."),
        ])
        assert count == 1
        key = next(iter(detail))
        assert "section 1.1" in key[0]
        assert "boarding_house" in key[1] and "residential_flat_building" in key[1]

    def test_the_detail_says_why_no_entry_can_be_written(self):
        count, detail = _count([
            _row("# 2.4 This Part applies to boarding house development."),
            _row("# 2.4 This Part applies to residential flat building development."),
        ])
        assert count == 1
        assert "no single config entry is true of all" in next(iter(detail))[1]


class TestTheThirtyFourNearMissesStayQuiet:
    def test_a_land_scope_beside_a_development_scope_is_not_a_collision(self):
        """Woollahra. Both statements are true of the same chapter at once —
        one says WHERE, the other says WHAT KIND OF APPLICATION."""
        count, _ = _count([
            _row("# E1.1 This Chapter applies to all land within the Woollahra "
                 "municipality."),
            _row("# E1.1 This Chapter applies to development that requires "
                 "development consent."),
        ])
        assert count == 0

    def test_boilerplate_inconsistency_wording_is_not_a_collision(self):
        """City of Sydney. 'to the extent of the inconsistency' names no
        development type, so it cannot contradict anything."""
        count, _ = _count([
            _row("# 5.11 This Section applies to the extent of the inconsistency."),
            _row("# 5.11 This Section applies to the land identified in figure 5."),
        ])
        assert count == 0

    def test_the_same_sentence_read_twice_with_table_debris_counts_once(self):
        """Parramatta 8.2.3, 7.5 and 3.7. The extractor emitted the scope once
        cleanly and once with HTML table markup around it. One statement, read
        twice — not two plans."""
        count, _ = _count([
            _row("# 8.2.3 The provisions of this Section apply to development "
                 "within Granville Local Centre for dwelling houses."),
            _row("# 8.2.3 The provisions of this Section apply to development "
                 "within Granville Local Centre for dwelling houses</td> <td>."),
        ])
        assert count == 0

    def test_a_street_address_names_no_development_type(self):
        """Parramatta 9.10.x pairs two site-specific addresses."""
        count, _ = _count([
            _row("# 9.10.3.1 This Section applies to land at 2-10 Phillip Street, "
                 "Parramatta as shown in figure 9."),
            _row("# 9.10.3.1 This Section applies to 180 George Street, Parramatta "
                 "at the intersection of George and Charles streets."),
        ])
        assert count == 0

    def test_overlapping_scopes_are_not_a_collision(self):
        """A broad scope and a narrow one that share a type can both be true."""
        count, _ = _count([
            _row("# 3.1 This Part applies to dwelling house and dual occupancy "
                 "development."),
            _row("# 3.1 This Part applies to dwelling house development."),
        ])
        assert count == 0

    def test_a_single_scope_statement_is_never_a_collision(self):
        count, _ = _count([
            _row("# 3.1 This Part applies to boarding house development."),
        ])
        assert count == 0

    def test_the_same_code_in_a_DIFFERENT_document_is_not_a_collision(self):
        """Two councils, or two properly separated plans, both having a 1.1 is
        the normal case — and is exactly what splitting the document achieves."""
        count, _ = _count([
            _row("# 1.1 This Part applies to boarding house development.",
                 doc="Council_DCP__part_b_boarding_houses"),
            _row("# 1.1 This Part applies to residential flat building development.",
                 doc="Council_DCP__part_c_apartments"),
        ])
        assert count == 0, "splitting the document must clear this check"


class TestTheScopeSentencePattern:
    @pytest.mark.parametrize("text,expected", [
        ("This Part applies to boarding house development.", True),
        ("Land to which this Part applies This Part applies to dwellings.", True),
        ("The provisions of this Section apply to development in Granville.", True),
        ("This Chapter applies to all land in the municipality.", True),
        ("The council encourages boarding houses in this area.", False),
        ("Applicants should refer to Part 3.", False),
    ])
    def test_it_matches_how_councils_actually_write_scope(self, text, expected):
        """Every positive here is a phrasing taken from a council in the served
        set, not a guess at how a DCP might be worded."""
        assert bool(_SCOPE_SENTENCE.search(text)) is expected
