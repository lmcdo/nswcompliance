"""Cumberland DCP Part B is five sub-Parts in one document with colliding section codes. The row's PDF page names its
sub-Part (divider pages read from the PDF). A divider/cover page stays no_config."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enrichment.extractors.applicability_tagger import ApplicabilityTagger  # noqa: E402

DOC = "Cumberland_DCP_Part_B_–_Residential_Zones_2021__cumberland_dcp_part_b_residential"
TEXT = "# 1.1\n\nSetbacks shall be provided in accordance with Table 1."


def _tag(page):
    z, d, src = ApplicabilityTagger().tag_with_provenance(TEXT, DOC, part="unknown", pdf_page=page)
    return z, d, src["dev_type_source"]


def test_each_known_page_gets_its_sub_parts_types():
    # noqa: zone-codes - Cumberland residential zones asserted as stored
    assert _tag(8) == (["R2", "R3", "R4"], ["dwelling_house", "secondary_dwelling"], "config_specific")  # noqa: zone-codes
    assert _tag(31)[1] == ["dual_occupancy"]
    assert _tag(39)[1] == ["residential_flat_building"]
    assert _tag(45)[1] == ["boarding_house"]


def test_b5_excludes_single_dwellings():
    _, devs, src = _tag(53)
    assert src == "config_specific" and "dwelling_house" not in devs and "residential_flat_building" in devs


def test_same_section_code_resolves_differently_per_page():
    assert _tag(8)[1] != _tag(45)[1]


def test_divider_cover_and_out_of_range_pages_stay_unresolved():
    for page in (1, 3, 6, 29, 37, 43, 51, 900, None):
        assert _tag(page)[2] == "no_config", page
