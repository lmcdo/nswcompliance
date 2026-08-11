"""DQ-33 — the matchers must read the document_id convention that actually exists.

The Marrickville / Ashfield / Leichhardt matchers were written for a verbose
convention ("Chapter E1", "4.1", "_4_1_"). Production uses a slug
("chapter_e1_heritage", "part4_s1_low_density"). The council matched, the PART
never did, and 9,854 served rows fell through to ALL/ALL.

THE SAFETY PROPERTY THESE TESTS EXIST FOR
-----------------------------------------
This fix NARROWS what a property is shown. Showing an irrelevant control is
noise; hiding a binding one is the liability. So the resolvers must only ever
return a key the council's config already declares — no key is invented and no
part is guessed to improve the numbers. Anything unrecognised stays ALL with
source `no_config`, which is a missed improvement rather than a hidden control.

Mutation note: a resolver that returns a key without checking the config fails
the "never invents" tests; one that returns None unconditionally fails the
"resolves the real slug" tests. Neither direction passes.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from enrichment.config.ashfield_config import ASHFIELD_CONFIG  # noqa: E402
from enrichment.config.leichhardt_config import LEICHHARDT_CONFIG  # noqa: E402
from enrichment.config.marrickville_config import MARRICKVILLE_CONFIG  # noqa: E402
from enrichment.extractors.applicability_tagger import (  # noqa: E402
    TRUSTED_ALL_SOURCES,
    ApplicabilityTagger,
)


@pytest.fixture(scope="module")
def tagger():
    return ApplicabilityTagger()


class TestResolvesTheRealSlugConvention:
    """Every one of these is a real production document_id."""

    @pytest.mark.parametrize("doc,expected", [
        ("Marrickville_DCP_2011__part4_s1_low_density", ("part", "4.1")),
        ("Marrickville_DCP_2011__part4_s2_multi_dwelling", ("part", "4.2")),
        ("Marrickville_DCP_2011__part5_commercial_mixed_use", ("part", "5")),
        ("Marrickville_DCP_2011__part6_industrial", ("part", "6")),
        ("Marrickville_DCP_2011__part8_heritage", ("part", "8")),
        ("Marrickville_DCP_2011__part2_s03_site_context_analysis", ("part", "2_3")),
        ("Marrickville_DCP_2011__part9_p47_victoria_road", ("precinct", "9_47")),
        ("Marrickville_DCP_2011__part9_p08_enmore_north", ("precinct", "9_8")),
    ])
    def test_marrickville(self, tagger, doc, expected):
        assert tagger._marrickville_slug_key(doc) == expected

    @pytest.mark.parametrize("doc,expected", [
        ("Inner_West_Ashfield_DCP_2016__chapter_e1_heritage", ("chapter", "Chapter E1")),
        ("Inner_West_Ashfield_DCP_2016__chapter_a_miscellaneous", ("chapter", "Chapter A")),
        ("Inner_West_Ashfield_DCP_2016__chapter_f_dev_category", ("chapter", "Chapter F")),
        ("Inner_West_Ashfield_DCP_2016__chapter_d_precinct_guidelines", ("chapter", "Chapter D")),
    ])
    def test_ashfield(self, tagger, doc, expected):
        assert tagger._ashfield_slug_key(doc) == expected

    @pytest.mark.parametrize("doc,expected", [
        ("Leichhardt_DCP_2013__part_c_s1_general", ("part", "Part C Section 1")),
        ("Leichhardt_DCP_2013__part_c_s2_urban_character", ("part", "Part C Section 2")),
        ("Leichhardt_DCP_2013__part_g_s1_site_specific", ("part", "Part G")),
        ("Leichhardt_DCP_2013__part_f_food", ("part", "Part F")),
    ])
    def test_leichhardt(self, tagger, doc, expected):
        assert tagger._leichhardt_slug_key(doc) == expected


class TestNeverInventsAKeyTheConfigLacks:
    """The whole safety property. A guessed part is a hidden control."""

    def test_ashfield_chapter_e2_does_not_resolve(self, tagger):
        # 118 served rows. ASHFIELD_CONFIG declares no 'Chapter E2', and inventing
        # one to cover them is exactly the guess this rule forbids.
        assert "Chapter E2" not in (ASHFIELD_CONFIG.get("chapters") or {})
        assert tagger._ashfield_slug_key(
            "Inner_West_Ashfield_DCP_2016__chapter_e2_haberfield") is None

    def test_a_part_2_subsection_the_config_omits_does_not_resolve(self, tagger):
        """131 served rows, and the right answer is still None.

        MARRICKVILLE_CONFIG enumerates 2_1..2_25 selectively and has no '2_21';
        the fallback candidate '2' is not a declared part either. Resolving it to
        the nearest neighbour would be a guess, so it stays ALL / no_config.
        """
        parts = MARRICKVILLE_CONFIG.get("parts") or {}
        assert "2_21" not in parts and "2" not in parts
        assert tagger._marrickville_slug_key(
            "Marrickville_DCP_2011__part2_s21_site_facilities_waste") is None

    def test_marrickville_unknown_part_does_not_resolve(self, tagger):
        assert "99" not in (MARRICKVILLE_CONFIG.get("parts") or {})
        assert tagger._marrickville_slug_key(
            "Marrickville_DCP_2011__part99_invented") is None

    def test_marrickville_unknown_precinct_does_not_resolve(self, tagger):
        assert "9_999" not in (MARRICKVILLE_CONFIG.get("precincts") or {})
        assert tagger._marrickville_slug_key(
            "Marrickville_DCP_2011__part9_p999_nowhere") is None

    def test_leichhardt_unknown_part_does_not_resolve(self, tagger):
        assert "Part Z" not in (LEICHHARDT_CONFIG.get("parts") or {})
        assert tagger._leichhardt_slug_key("Leichhardt_DCP_2013__part_z_invented") is None

    @pytest.mark.parametrize("doc", [
        "Marrickville_DCP_2011__da_guidelines",
        "Marrickville_DCP_2011__part10_definitions",
        "Leichhardt_DCP_2013__tree_management_technical_manual",
        "Leichhardt_DCP_2013__appendix_b_building_typologies",
    ])
    def test_non_part_documents_stay_unresolved(self, tagger, doc):
        """Guidelines, definitions, manuals and appendices are not parts."""
        assert (tagger._marrickville_slug_key(doc) is None
                and tagger._leichhardt_slug_key(doc) is None)


class TestEndToEndThroughTag:
    def test_low_density_now_resolves_to_r2_with_an_attributable_source(self, tagger):
        zones, devs, prov = tagger.tag_with_provenance(
            "# 4.1.6.3 O16 site coverage", "Marrickville_DCP_2011__part4_s1_low_density")
        assert zones == ["R2"]
        assert prov["zone_source"] == "config_specific"
        assert prov["zone_source"] in TRUSTED_ALL_SOURCES

    def test_industrial_resolves_to_the_current_employment_zone(self, tagger):
        zones, _devs, prov = tagger.tag_with_provenance(
            "# 6.1.3 O27 site facilities", "Marrickville_DCP_2011__part6_industrial")
        # E4, not the retired IN1/IN2 — DQ-30's taxonomy fix must survive this.
        assert zones == ["E4"] and prov["zone_source"] == "config_specific"

    def test_an_unresolved_document_keeps_all_and_says_no_config(self, tagger):
        zones, devs, prov = tagger.tag_with_provenance(
            "Heritage conservation area controls.",
            "Inner_West_Ashfield_DCP_2016__chapter_e2_haberfield")
        assert zones == ["ALL"] and devs == ["ALL"]
        assert prov["zone_source"] == "no_config"
        assert prov["zone_source"] not in TRUSTED_ALL_SOURCES

    def test_a_precinct_document_resolves_and_is_marked_precinct_specific(self, tagger):
        cfg = tagger._get_marrickville_config(
            "Marrickville_DCP_2011__part9_p47_victoria_road")
        assert cfg.get("is_precinct_specific") is True
        assert cfg.get("precinct_id") == "9_47"
