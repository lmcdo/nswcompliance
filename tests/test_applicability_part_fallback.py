"""A whole-plan document read by the section reader heads its rules with section numbers ("16.2") while the
council config is keyed by Part letter ("B"): the row's own Part (v2_dcp_part) is the fallback (OC-17, 2026-10-15:
448 Waverley rows had fallen to no_config)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enrichment.extractors.applicability_tagger import ApplicabilityTagger  # noqa: E402

DOC = "Waverley_DCP_2022__waverley_dcp_2022"
TEXT = "# 16.2\n\nWaste storage areas are to be screened from the street."


def test_a_numeric_heading_falls_to_no_config_without_a_part():
    _z, _d, src = ApplicabilityTagger().tag_with_provenance(TEXT, DOC)
    assert src["dev_type_source"] == "no_config"


def test_the_rows_part_is_used_when_the_heading_matches_nothing():
    _z, _d, src = ApplicabilityTagger().tag_with_provenance(TEXT, DOC, part="B12")
    assert src["dev_type_source"] != "no_config"


def test_a_part_the_config_does_not_have_stays_undecided():
    _z, _d, src = ApplicabilityTagger().tag_with_provenance(TEXT, DOC, part="Z9")
    assert src["dev_type_source"] == "no_config"


def test_a_heading_code_that_matches_still_wins_over_the_part():
    a = ApplicabilityTagger().tag_with_provenance("# C1\n\nThe dwelling is setback 6m.", DOC, part="E1")  # noqa: zone-codes (Waverley DCP Part keys, not zones)
    b = ApplicabilityTagger().tag_with_provenance("# C1\n\nThe dwelling is setback 6m.", DOC)
    assert a == b
