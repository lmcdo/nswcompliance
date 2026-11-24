"""Waverley rows on annexure pages and reference pages: a page that names its Part gives the row that Part; a page in no list stays unresolved."""
import json
from pathlib import Path

from enrichment.extractors.applicability_tagger import ApplicabilityTagger

DOC = "Waverley_DCP_2022__waverley_dcp_2022"
PAGES = json.loads((Path(__file__).resolve().parent.parent / "enrichment" / "config" / "waverley_part_pages.json").read_text(encoding="utf-8"))
TAGGER = ApplicabilityTagger()


def src(text, page, part="unknown"):
    return TAGGER.tag_with_provenance(text, DOC, part=part, pdf_page=page)[2]["dev_type_source"]


def test_a_contents_page_row_applies_to_all_and_says_it_was_decided():
    assert src("# 15.7 Minor Encroachments\n\n15.7 Minor Encroachments | 139", 11) == "config_all"


def test_the_general_notes_page_is_reference_and_a_plan_cross_reference_is_not_read_as_a_zone():
    zones, _devs, why = TAGGER.tag_with_provenance("# Special Character Areas\n\nRefer to Part E4 for Special Character Areas", DOC, part="unknown", pdf_page=187)
    assert why["zone_source"] == "config_all" and zones == ["ALL"]


def test_an_annexure_row_with_a_numeric_heading_takes_its_part_from_the_page():
    # '7.9' is a section number inside Part E2; without the page the row finds no Part and reads no_config.
    assert src("# 7.9 WINDOWS\n\nBuildings in the Bondi Beachfront Area have a", 421) != "no_config"
    assert src("# 7.9 WINDOWS\n\nBuildings in the Bondi Beachfront Area have a", 500) == "no_config"


def test_a_page_in_no_list_is_never_guessed():
    assert src("# 7.9 WINDOWS\n\nfoo", 500) == "no_config"
    assert src("# 7.9 WINDOWS\n\nfoo", None) == "no_config"


def test_a_row_with_no_heading_code_on_a_c1_page_takes_c1():
    assert src("# (ix)\n\nIn areas of heritage significance, the importance of", 193) != "no_config"


def test_a_row_that_already_carries_a_valid_part_keeps_it_on_a_reference_free_page():
    # B8's own entry is ALL; the row's own Part B8 must not be replaced by the page's range on p421 (E2).
    assert src("# B8.1 Heritage\n\nfoo", 421, part="B8") != "no_config"


def test_ranges_do_not_overlap_and_each_cites_a_page():
    rs = sorted(PAGES["ranges"], key=lambda r: r["first_page"])
    for a, b in zip(rs, rs[1:]):
        assert a["last_page"] < b["first_page"], (a["part"], b["part"])
    assert all(r["first_page"] <= r["last_page"] and r["evidence"].startswith("PDF p") for r in PAGES["ranges"] + PAGES["reference_pages"])


def test_a_reference_page_is_not_inside_a_part_range():
    for ref in PAGES["reference_pages"]:
        for rng in PAGES["ranges"]:
            assert not (rng["first_page"] <= ref["first_page"] <= rng["last_page"]), (ref, rng)
