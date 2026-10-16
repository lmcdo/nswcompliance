"""Warringah DCP 2011 is one whole-DCP document; its rows are headed with section numbers, not Part letters. The row's
PDF page names its Part (ranges from the PDF's own Part headings). A page with no single Part stays no_config."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enrichment.extractors.applicability_tagger import ApplicabilityTagger  # noqa: E402

DOC = "Warringah_DCP_2011__warringah_dcp_2011_full"
TEXT = "# 5.0\n\nFigure 4: Landscaping with deep soil planting zone at 6.5m setback."


def _src(page, part=None):
    return ApplicabilityTagger().tag_with_provenance(TEXT, DOC, part=part, pdf_page=page)[2]["dev_type_source"]


def test_a_numeric_heading_without_a_page_stays_no_config():
    assert _src(None) == "no_config"


def test_a_row_on_a_known_page_gets_that_pages_part():
    # PDF p175 is inside Part G (94-258); Part G is declared in the config.
    assert _src(175) != "no_config"
    # p56 is Part D, p86 Part E: the Part's own entry, not a shared one.
    z_g = ApplicabilityTagger().tag_with_provenance(TEXT, DOC, pdf_page=175)
    z_a = ApplicabilityTagger().tag_with_provenance(TEXT, DOC, part="G")
    assert z_g == z_a


def test_a_page_where_two_parts_meet_stays_unresolved():
    # Part B's heading sits mid-way down p15, so p15 holds Part A text and Part B text.
    assert _src(15) == "no_config"
    # the cover / amendment pages sit before Part A's heading
    assert _src(1) == "no_config"


def test_a_page_beyond_the_document_stays_unresolved():
    assert _src(900) == "no_config"


def test_an_unknown_part_value_does_not_block_the_page_lookup():
    assert _src(175, part="unknown") != "no_config"
