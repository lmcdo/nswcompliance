"""The contents parser, against real page text and against what must NOT parse.

The positives are real pdfplumber output from named chapters (tests/fixtures/
dcp_toc_samples.py). The negatives are the load-bearing half: this parser was
widened from three formats to six, and every loosening raises the chance that
body prose reads as a contents page. A fabricated contents list produces a
fabricated "sections missing" finding, which is worse than the fail-open check
it replaces, because it looks like evidence.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.dcp_toc_parse import (  # noqa: E402
    MIN_TOTAL, NO_CONTENTS, READ, TITLES_ONLY, UNREADABLE,
    entry_strength, page_entries, parse_contents,
)
from tests.fixtures import dcp_toc_samples as S  # noqa: E402


class TestRealFormatsParse:
    """Six shapes found in the corpus on 2026-09-12. All must READ."""

    @pytest.mark.parametrize("label,text,expected", [
        (label, text, expected) for label, text, expected in S.CASES
    ])
    def test_fixture_status(self, label, text, expected):
        status, _codes, _entries = parse_contents([text])
        assert status == expected, label + " parsed as " + status

    def test_ku_ring_gai_trailing_letter_codes_are_kept_whole(self):
        # "14A.1" must not be read as "14". This single shape is 34 of the 113
        # chapters the previous parser could not read.
        _status, codes, _ = parse_contents([S.KU_RING_GAI])
        assert "14A.1" in codes
        assert "14A.7" in codes
        assert "14" not in codes

    def test_canterbury_prefix_word_is_stripped_not_parsed_as_a_code(self):
        # "Section 1 - Introduction" is code 1, not code "Section".
        _status, codes, _ = parse_contents([S.CANTERBURY_BANKSTOWN])
        assert codes == {"1", "2", "3", "4", "5", "6"}

    def test_leaders_without_a_page_number_still_parse(self):
        # canterbury_bankstown's dot leaders run off the line with no page number.
        # The old regex required a trailing \d{1,3} and matched none of these.
        _status, codes, entries = parse_contents([S.CANTERBURY_BANKSTOWN])
        assert len(codes) == 6
        assert all(page is None for _c, _t, page in entries)

    def test_trailing_dot_on_a_code_is_not_part_of_the_code(self):
        _status, codes, _ = parse_contents([S.LEICHHARDT_G13])
        assert "4.1" in codes and "4.1." not in codes
        assert "G13.1" in codes


class TestCannotReadIsNeverAPass:
    """The rule the whole module exists for."""

    def test_titles_only_is_not_read_and_yields_no_codes(self):
        # A real contents page listing titles and page numbers and NO codes.
        # Returning READ with zero codes would let compare_codes see an empty
        # listed set and call the chapter OK.
        status, codes, _ = parse_contents([S.ASHFIELD_TITLES_ONLY])
        assert status == TITLES_ONLY
        assert codes == set()

    def test_a_contents_heading_we_cannot_read_is_UNREADABLE_not_NO_CONTENTS(self):
        # The page announces itself as a contents page, and we still fail. That
        # is a defect in this parser, and must be distinguishable from a document
        # that simply has no contents page.
        garbled = "TABLE OF CONTENTS\n" + "\n".join(
            "фхц чшщ ъ" for _ in range(8))
        status, _codes, _ = parse_contents([garbled])
        assert status == UNREADABLE

    def test_a_document_with_no_contents_page_is_NO_CONTENTS(self):
        status, _codes, _ = parse_contents([S.COVER])
        assert status == NO_CONTENTS

    def test_empty_text_layer_is_NO_CONTENTS_not_a_crash(self):
        status, codes, entries = parse_contents(["", "", ""])
        assert status == NO_CONTENTS
        assert codes == set() and entries == []

    def test_below_MIN_TOTAL_codes_does_not_report_READ(self):
        # A handful of codes is not a contents page. Reporting READ here is
        # precisely coverage_gap's bug: too little to judge, reported as judged.
        thin = "CONTENTS\n1 Alpha\n2 Beta\n"
        status, codes, _ = parse_contents([thin])
        assert len(codes) < MIN_TOTAL
        assert status != READ


class TestConfusableNegatives:
    """Body prose must not read as a contents page. These are the guardrails on
    every loosening in the regex, and they are what stops a fabricated finding."""

    def test_body_prose_does_not_parse(self):
        status, _codes, _ = parse_contents([S.BODY_PROSE])
        assert status == NO_CONTENTS

    def test_numbered_controls_do_not_parse(self):
        # One control per line, dense in codes, no contents heading -- the shape
        # the widened regex is most likely to swallow.
        status, codes, _ = parse_contents([S.NUMBERED_CONTROLS])
        assert status == NO_CONTENTS, "parsed " + str(len(codes)) + " fake entries"

    def test_wrapped_controls_do_not_parse(self):
        status, _codes, _ = parse_contents([S.WRAPPED_CONTROLS])
        assert status == NO_CONTENTS

    def test_a_sentence_is_rejected_as_an_entry(self):
        assert entry_strength(
            "Development must maintain significant views to the place", None,
            "2.2 Development must maintain significant views to the place.") is None

    def test_a_long_titleless_run_of_words_is_rejected(self):
        long_title = " ".join(["word"] * 14)
        assert entry_strength(long_title, None, "2.2 " + long_title) is None

    def test_but_a_page_number_makes_an_entry_unambiguous(self):
        # A trailing page number appears on contents pages and nowhere else, so
        # the sentence test is skipped for it -- otherwise a legitimate long
        # contents title with a page number would be dropped.
        assert entry_strength("A very long but genuine contents title here now",
                              143, "B16 ... 143") == "STRONG"

    def test_dot_leaders_also_make_an_entry_unambiguous(self):
        assert entry_strength("Introduction", None,
                              "Section 1 - Introduction ......") == "STRONG"


class TestPageLevelDensityGate:
    def test_a_contents_heading_lowers_the_bar(self):
        # With a heading, three entries are enough. Without one, they are not.
        headed = "CONTENTS\n1 Alpha\n2 Beta\n3 Gamma\n4 Delta\n"
        bare = "1 Alpha\n2 Beta\n3 Gamma\n4 Delta\n"
        assert parse_contents([headed])[0] == READ
        # bare has 4 entries, below MIN_ENTRIES_BARE=5
        assert parse_contents([bare])[0] != READ

    def test_entries_buried_in_prose_do_not_reach_the_density_bar(self):
        prose = "\n".join(["This is a sentence of ordinary body text here."] * 20)
        page = "1 Alpha\n2 Beta\n3 Gamma\n4 Delta\n5 Epsilon\n" + prose
        coded, _titled, density, heading = page_entries(page)
        assert len(coded) == 5 and not heading
        assert density < 0.45
        assert parse_contents([page])[0] != READ

    def test_null_and_none_page_text_do_not_raise(self):
        assert page_entries(None) == ([], [], 0.0, False)
        assert page_entries("") == ([], [], 0.0, False)


class TestMutationResistance:
    """Would a gutted implementation still pass? These say no."""

    def test_parser_actually_returns_codes_not_an_empty_set(self):
        # `return NO_CONTENTS, set(), []` would pass every negative test above.
        _status, codes, _ = parse_contents([S.WAVERLEY])
        assert codes == {"A1", "B1", "B15", "B16", "C1", "E7", "F1", "F5"}  # noqa: zone-codes  (DCP Part codes, not NSW zone codes)

    def test_parser_does_not_simply_accept_everything(self):
        # `return READ, {...}, [...]` would pass every positive test above.
        negatives = [S.BODY_PROSE, S.NUMBERED_CONTROLS, S.WRAPPED_CONTROLS,
                     S.COVER, S.SCANNED]
        assert all(parse_contents([n])[0] != READ for n in negatives)
