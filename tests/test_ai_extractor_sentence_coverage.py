"""The reader keeps council sentences that have no number (scripts/ai_extractor.py, sentence coverage).

2026-10-18 doubled-text re-reads: 3 of 8 chapters lost council sentences on pages that page coverage passed --
Ku-ring-gai 14I "The Killara Golf Clubhouse ... is a locally listed Heritage Item", 14G's introductions, Campbelltown
Part 4 "This section sets out controls relating to residential flat buildings in areas zoned R4".
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import ai_extractor as ax  # noqa: E402

KILLARA = ("The Killara Golf Clubhouse and its curtilage area (encompassing the putting green) is a locally listed "
           "Heritage Item.")
RULE = "1 All buildings within Area A1, Area A2 and Area B are to demonstrate consideration of the Clubhouse."


def test_the_prompt_asks_for_unnumbered_paragraphs_and_names_no_code():
    assert "EVERY paragraph of council text printed under a heading" in ax.PROMPT
    assert "This section applies to" in ax.PROMPT
    assert "R4" not in ax.PROMPT          # no zone or section code as an example (the model copies examples)


def test_a_dropped_unnumbered_sentence_is_found_and_a_copied_rule_is_not():
    page = f"14I.5 HERITAGE (continued)\n{KILLARA} {RULE}\n"
    miss = ax.missing_sentences({13: page}, [RULE])
    assert list(miss) == [13] and len(miss[13]) == 1
    assert "locally listed heritage item" in miss[13][0]


def test_nothing_is_missing_when_every_sentence_was_copied():
    page = f"14I.5 HERITAGE (continued)\n{KILLARA} {RULE}\n"
    assert ax.missing_sentences({13: page}, [KILLARA, RULE]) == {}


def test_a_heading_run_into_a_sentence_does_not_make_it_missing():
    """'p 14 245 14G.1 URBAN PRECINCT (continued) 1 To create ...' -- the reader rightly leaves the heading out."""
    body = "To create a vibrant precinct capable of attracting commercial investment and quality tenants."
    page = f"p 14-245 14G.1 URBAN PRECINCT PYMBLE BUSINESS PARK (continued)\n{body}"
    assert ax.missing_sentences({3: page}, [body]) == {}


def test_a_sentence_with_a_middle_part_missing_is_found():
    full = ("The new east west and north south road corridors are to have a width of 16m and both streets should "
            "accommodate two way traffic and one lane of on street parking.")
    cut = "The new east west and north south road corridors are to have a width of 16m."
    assert ax.missing_sentences({5: full}, [cut])


def test_captions_legends_map_numbers_and_headings_are_never_asked_for():
    page = ("Figure 14I.2-1: Internal road footpaths, verges and tree planting.\n"
            "Precinct G1 Figure 14D.7-2 Public domain and pedestrian access plan.\n"
            "42a 58 55 53 55a 55 52 50 51 59 56 54 20 22 52 54 43 15 17 53 lots.\n"
            "e x i s t i n g t r e e s site access points.\n"
            "14I.5 HERITAGE")
    assert ax.page_sentences(page) == []


def test_a_rule_that_cites_a_figure_is_still_asked_for():
    rule = "Building setbacks are to be in accordance with Figure 14D.8-4 and all buildings are to be set back."
    assert ax.page_sentences(rule)


def test_only_reread_provisions_that_bring_a_missing_sentence_back_are_kept():
    named = [" ".join(ax._WORDS_RE.findall(KILLARA.lower()))]
    found = [{"code": "14I.5", "text": KILLARA}, {"code": "14I.5 1", "text": RULE}]
    assert ax.keep_bringing_back(found, named) == [found[0]]


def test_the_chapter_reader_runs_the_sentence_check_after_page_coverage():
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "scripts" / "ai_extractor.py").read_text(encoding="utf-8")
    pages_at = src.index("        _reread_skipped_pages(pdf_path, reader, model, collected)\n")
    assert src.index("        _reread_missing_sentences(pdf_path, reader, model, collected)\n") > pages_at


def test_the_top_of_a_page_continuing_a_clause_is_its_own_sentence():
    """Campbelltown Part 4 5.4.8.2 b runs over a page break: page 13 opens 'or living rooms unless they are outside the
    sound transmission barrier surrounding each unit.' then 'ii) Not open ...'. Glued to the copied items it passed."""
    page = ("or living rooms unless they are outside the sound transmission barrier surrounding each unit. "
            "ii) Not open into any habitable or public space and doors must have an effective self-sealing system; "
            "iii) Feed into appropriately sized bins located in the bin storage room.")
    copied = ["ii) Not open into any habitable or public space and doors must have an effective self-sealing system; "
              "iii) Feed into appropriately sized bins located in the bin storage room."]
    miss = ax.missing_sentences({13: page}, copied)
    assert miss and "living rooms unless" in miss[13][0]


def test_a_late_stray_match_does_not_excuse_a_whole_sentence():
    """'Note: Refer to Section 4.1C of the CLEP for the minimum qualifying site area for residential flat buildings.'
    matched only its last words, elsewhere in the output."""
    page = "Note: Refer to Section 4.1C of the CLEP for the minimum qualifying site area for residential flat buildings."
    other = ["This section sets out controls for residential flat buildings in areas zoned for them."]
    assert ax.missing_sentences({20: page}, other)
