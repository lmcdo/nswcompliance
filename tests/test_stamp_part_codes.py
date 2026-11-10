"""AI/section-read headings get the Part code from the page map (Waverley lost its area links without it).

Waverley DCP 2022 Amendment 6 queue, 2026-11-11: 1,309 rows on Part E pages, 20 headed with a Part code; the
precinct rule copies v2_dcp_part only when it is exactly E1..E7, so 1,289 lost their area link.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from enrichment.config import COUNCIL_CONFIGS  # noqa: E402
from enrichment.extractors.layer_topic_tagger import LayerTopicTagger  # noqa: E402
from scripts.dcp_extract_changed import build_provision_text, stamp_part_codes  # noqa: E402

RANGES = [("B1", "Waste", 12, 23), ("E1", "Bondi Junction", 264, 318), ("E3", "Local Village Centres", 342, 376)]  # noqa: zone-codes  (DCP Part keys, not zones)
PARTS = COUNCIL_CONFIGS["waverley"]["parts"]
DOC = "Waverley_DCP_2022__waverley_dcp_2022"


def _sec(number, title, page):
    return {"section_number": number, "section_title": title, "content": "x", "tables": [], "page_start": page}


def _part(sec):
    return LayerTopicTagger().tag(DOC, build_provision_text(sec))[1]


def test_a_numeric_heading_on_a_part_e_page_gets_the_part_and_matches_the_precinct_rule():
    s = _sec("1.2 (e)", "URBAN FORM CONTROLS", 265)
    assert stamp_part_codes([s], RANGES, PARTS) == 1
    assert build_provision_text(s).startswith("# E1 1.2 (e) URBAN FORM CONTROLS")
    assert _part(s) == "E1"                       # ^E[0-9]$ -> waverley_part_e copies it


def test_without_the_stamp_the_same_rule_has_no_part_E():
    assert not _part(_sec("1.2 (e)", "URBAN FORM CONTROLS", 265)).startswith("E")


def test_the_part_comes_from_the_page_not_the_text():
    s = _sec("2.1", "Setbacks", 350)
    stamp_part_codes([s], RANGES, PARTS)
    assert _part(s) == "E3"


def test_a_page_outside_every_part_is_left_alone():
    s = _sec("2.1", "x", 200)
    assert stamp_part_codes([s], RANGES, PARTS) == 0 and "text_heading" not in s


def test_a_heading_that_already_starts_with_a_letter_code_is_left_as_read():
    s = _sec("E3.2", "Setbacks", 350)
    assert stamp_part_codes([s], RANGES, PARTS) == 0 and "text_heading" not in s


def test_an_existing_text_heading_is_not_overwritten():
    s = _sec("1.2", "x", 265)
    s["text_heading"] = "E1 already"
    assert stamp_part_codes([s], RANGES, PARTS) == 0 and s["text_heading"] == "E1 already"


def test_a_council_whose_config_cannot_resolve_the_part_is_not_stamped():
    s = _sec("1.2", "x", 265)
    assert stamp_part_codes([s], RANGES, {}) == 0 and stamp_part_codes([s], RANGES, None) == 0


def test_the_ref_number_source_is_unchanged_and_preamble_is_skipped():
    s = _sec("1.2 (e)", "x", 265)
    stamp_part_codes([s], RANGES, PARTS)
    assert s["section_number"] == "1.2 (e)"
    p = _sec("preamble", "", 265)
    assert stamp_part_codes([p], RANGES, PARTS) == 0


def test_a_section_with_no_integer_page_is_skipped():
    s = _sec("1.2", "x", None)
    assert stamp_part_codes([s], RANGES, PARTS) == 0


def test_the_extractor_stamps_both_ai_readers_and_not_the_regex_reader():
    src = open(os.path.join(os.path.dirname(__file__), "..", "scripts", "dcp_extract_changed.py"),
               encoding="utf-8").read()
    assert "return self._stamp_parts(sr.to_sections(out[\"rules\"]))" in src
    assert "return self._stamp_parts(\n                    ai_extract_chapter(" in src
