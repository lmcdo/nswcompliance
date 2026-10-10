"""Inner West LEP 2022 rows are scoped by their CLAUSE, from the Plan's own words (DQ-140).

prior-art-checked: reuse not viable because the per-clause LEP path is new in this PR.
"""
import pytest

from enrichment.config.inner_west_lep_config import INNER_WEST_LEP_CLAUSES, clause_key
from enrichment.extractors.applicability_tagger import ApplicabilityTagger

DOC = "Inner_West_Local_Environmental_Plan_2022__NSW_Legislation"


@pytest.fixture(scope="module")
def tagger():
    return ApplicabilityTagger()


def test_clause_key_reads_clause_schedule_and_land_use_table():
    assert clause_key("6.34 Development of certain land at Alma Avenue") == "6.34"
    assert clause_key("Schedule 5 Environmental heritage") == "Schedule 5"
    assert clause_key("Land Use Table Zone R1 General Residential") == "LUT:R1"
    assert clause_key(None) is None


def test_named_zones_become_config_specific(tagger):
    zones, devs, prov = tagger.tag_with_provenance("any text", DOC, clause="6.11 Something")
    assert prov["zone_source"] == "config_specific" and set(zones) <= {"R1", "R2", "R3", "R4"}  # noqa: zone-codes - zones the config quotes from cl 6.11


def test_land_use_table_row_is_scoped_to_its_zone(tagger):
    zones, _, prov = tagger.tag_with_provenance("Permitted with consent ...", DOC,
                                                clause="Land Use Table Zone R4 High Density Residential")
    assert zones == ["R4"] and prov["zone_source"] == "config_specific"


def test_site_specific_schedule_is_a_recorded_decline_not_a_guess(tagger):
    zones, _, prov = tagger.tag_with_provenance("Lot 11, DP 499846 ... in Zone R1", DOC, clause="Schedule 1 Additional permitted uses")
    assert zones == ["ALL"] and prov["zone_source"] == "config_declined"


def test_unknown_clause_is_no_config_and_never_text_regex(tagger):
    # The row text names a zone; without a clause entry it must NOT be narrowed by regex.
    zones, _, prov = tagger.tag_with_provenance("This applies to land in Zone R2.", DOC, clause="99.99 Nothing")
    assert prov["zone_source"] == "no_config" and zones == ["ALL"]


def test_other_documents_are_unaffected(tagger):
    a = tagger.tag_with_provenance("This applies to land in Zone R2.", "Some_Other_DCP_2020__chapter_1")
    b = tagger.tag_with_provenance("This applies to land in Zone R2.", "Some_Other_DCP_2020__chapter_1", clause="6.11 X")
    assert a == b


def test_every_declared_scope_carries_its_quote():
    for key, e in INNER_WEST_LEP_CLAUSES.items():
        for field in ("applicable_zones", "applicable_dev_types"):
            if field in e or field in e.get("scope_declined", []):
                assert e["scope_evidence"].get(field), f"{key} {field} has no quote"
        assert not (set(e.get("scope_declined", [])) & {f for f in ("applicable_zones", "applicable_dev_types") if f in e}), key


def test_a_later_inner_west_lep_does_not_inherit_the_2022_scopes(tagger):
    later = "Inner_West_Local_Environmental_Plan_2025__NSW_Legislation"
    _, _, prov = tagger.tag_with_provenance("text", later, clause="6.11 Something")
    assert prov["zone_source"] != "config_specific"
