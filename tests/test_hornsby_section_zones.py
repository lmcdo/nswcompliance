"""Hornsby Part 3: a rule's zone comes from the section its page sits in.

prior-art-checked: extends the existing tagger's config path; no other test covers page-range sections.
"""
import pytest

from enrichment.extractors.applicability_tagger import ApplicabilityTagger

DOC = "Hornsby_DCP_2024__hornsby_dcp_2024_part3_residential"


@pytest.mark.parametrize("page,zones", [
    (7, ["R2", "R3", "R4"]), (16, ["R2", "R3", "R4"]),  # 3.1 is left on the Part's zones  # noqa: zone-codes - expected values quoted from the council's section openings
    (17, ["R3"]), (39, ["R3"]), (40, ["R3", "R4"]), (51, ["R3", "R4"]), (52, ["R4"]), (82, ["R4"]),  # noqa: zone-codes - expected values quoted from the council's section openings
    (83, ["R2", "R3", "R4"]), (101, ["R2", "R3", "R4"]),  # 3.5 unchanged until the seniors area's zone is known  # noqa: zone-codes - expected values quoted from the council's section openings
    (None, ["R2", "R3", "R4"]),  # no page: never guess a section  # noqa: zone-codes - expected values quoted from the council's section openings
])
def test_zone_follows_the_section_page(page, zones):
    got_zones, got_types, source = ApplicabilityTagger().tag_with_provenance("A rule.", DOC, pdf_page=page)
    assert sorted(got_zones) == zones
    assert got_types == ["ALL"] and source["dev_type_source"] == "config_declined"


def test_narrow_only_never_writes_a_row_that_gains_a_zone():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from retag_applicability_slug_docids import only_narrowing

    def row(i, new_z, old_z, new_d=("ALL",), old_d=("ALL",)):
        return (i, list(new_z), list(new_d), "config_specific", "config_declined", list(old_z), list(old_d))

    plan = [row(1, ["R4"], ["R2", "R3", "R4"]), row(2, ["R2", "R3", "R4"], ["R4"]),  # noqa: zone-codes - expected values quoted from the council's section openings
            row(3, ["R3"], ["R4"]), row(4, ["R4"], ["ALL"]), row(5, ["ALL"], ["R4"]),  # noqa: zone-codes - expected values quoted from the council's section openings
            row(6, ["R4"], ["R2", "R4"], ["ALL"], ["dwelling_house"])]  # noqa: zone-codes - expected values quoted from the council's section openings
    assert [r[0] for r in only_narrowing(plan)] == [1, 4]
