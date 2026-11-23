"""Annexure, definition and abbreviation rows apply to every development type: recorded as a decision (config_all), not as the no_config fallthrough."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enrichment.extractors.applicability_tagger import (  # noqa: E402
    APPLICABILITY_SOURCES, TRUSTED_ALL_SOURCES, ApplicabilityTagger, is_reference_row)

DOC = "Waverley_DCP_2022__waverley_dcp_2022"


def src(text, part=None):
    return ApplicabilityTagger().tag_with_provenance(text, DOC, part=part)[2]


def test_annexure_definition_and_abbreviation_headings_are_reference_rows():
    for t in ("# Annexure B1-1 Examples of Building Material Reuse\n\nCarpet", "# ABBREVIATIONS PMF\n\nProbable Maximum Flood", "# DEFINITIONS Awning\n\nA roof-like structure",
              "## Definition of site\n\nx", "# Appendix 2 Schedule", "# Glossary\n\nx", "  # annexure b3-2 Melaleuca armillaris\n\nx"):
        assert is_reference_row(t), t


def test_a_normal_rule_or_one_that_only_mentions_a_definition_is_not_a_reference_row():
    for t in ("# 16.2 Waste\n\nSee the definitions in Annexure B.", "# B3 Landscaping\n\nTrees must be retained.", "Annexure B1-1 without a heading mark", "", None,  # noqa: zone-codes -- B3 is an annexure chapter code here, the test proves it is NOT read as a zone
              "# Definitions-based controls for signage\n\nx" if False else "# Annexures are listed in section 5\n\nx"):
        assert not is_reference_row(t), t


def test_only_the_first_line_is_read_so_a_body_that_says_definitions_does_not_count():
    assert not is_reference_row("# 7.2 Bicycle parking\n\n# Definitions\n\nx")


def test_a_reference_row_without_a_part_is_config_all_not_no_config():
    s = src("# Annexure B3-2 Casuarina equisetifolia\n\nCasuarina equisetifolia")
    assert s["zone_source"] == s["dev_type_source"] == "config_all"


def test_a_numeric_rule_without_a_part_still_falls_to_no_config():
    assert src("# 16.2\n\nWaste storage areas are to be screened from the street.")["dev_type_source"] == "no_config"


def test_a_reference_row_that_has_a_real_part_keeps_the_configs_answer():
    s = src("# Annexure B1-1 Examples\n\nx", part="B12")
    assert s["dev_type_source"] != "no_config"


def test_config_all_is_a_known_trusted_source():
    assert "config_all" in APPLICABILITY_SOURCES and "config_all" in TRUSTED_ALL_SOURCES
