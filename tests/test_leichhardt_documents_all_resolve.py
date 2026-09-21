"""Nine Leichhardt documents had no applicability config, so 871 served rows applied
to every development type because nothing matched.

A planner looking at a terrace house was shown Leichhardt's vehicle repair station and
industrial parking controls. Nothing errored, nothing blanked, no number was wrong —
an unmatched document falls through to ALL, so the failure shows MORE than it should,
never less. That is why it survived: there is nothing to notice.

Three causes, and the third is the one that matters:

1. The config was written from a partial reading of the plan. Its docstring lists eight
   parts as "Structure:". The DCP has Part C Sections 3, 4 and 5 as well, plus six
   appendices, amendments and technical manuals.
2. Six of those nine matched NO regex branch in the tagger, so no config entry could
   ever have been reached however carefully it was written.
3. Nothing checks that an ingested document resolves to a config key. The only thing
   that counts it is DQ-33, which reports one aggregate — "1,986 against a floor of
   1,278" — that names no council, no document, and no cause.

Scope for each entry was read from its own provisions rather than its title, because
the titles are what made this look easy. `appendix_b_building_typologies` sounds
residential; its section headers span C4 and C6, so it is declared ALL rather than
narrowed on the strength of its name.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from enrichment.config.leichhardt_config import LEICHHARDT_CONFIG  # noqa: E402
from enrichment.extractors.applicability_tagger import ApplicabilityTagger  # noqa: E402

#: The nine that were unconfigured, with the served row count each carried.
UNCONFIGURED = {
    "part_c_s3_residential": ("Part C Section 3", 192),
    "part_c_s4_non_residential": ("Part C Section 4", 286),
    "part_c_s5_entertainment_precincts": ("Part C Section 5", 17),
    "appendix_b_building_typologies": ("Appendix B", 108),
    "appendix_d_waste_template": ("Appendix D", 27),
    "appendix_e_water_guidelines": ("Appendix E", 34),
    "tree_management_technical_manual": ("Tree Management Technical Manual", 103),
    "amendment_1_george_upward_streets": ("Amendment 1", 91),
    "amendment_7_licensed_premises": ("Amendment 7", 13),
}
#: Narrowed from their own content. Everything else stays ALL deliberately.
NARROWED = {"Part C Section 3", "Part C Section 4", "Amendment 7"}


@pytest.fixture(scope="module")
def tagger():
    return ApplicabilityTagger()


class TestEveryUnconfiguredDocumentNowResolves:
    @pytest.mark.parametrize("slug,expected", [(s, k) for s, (k, _n) in UNCONFIGURED.items()])
    def test_it_resolves_to_its_declared_key(self, tagger, slug, expected):
        got = tagger._leichhardt_slug_key(f"Leichhardt_DCP_2013__{slug}")
        assert got == ("part", expected), (
            f"{slug} resolves to {got}, so its rows stay no_config and apply to every "
            f"development type")

    @pytest.mark.parametrize("key", sorted({k for k, _n in UNCONFIGURED.values()}))
    def test_the_key_is_actually_declared(self, key):
        assert key in LEICHHARDT_CONFIG["parts"], (
            f"{key} is matched but not declared, so the lookup returns nothing")

    def test_the_six_that_had_no_branch_at_all(self, tagger):
        """Appendices, amendments and the tree manual matched neither part_x nor
        part_x_sN. No config entry could have been reached for them."""
        for slug in ("appendix_b_building_typologies", "appendix_d_waste_template",
                     "appendix_e_water_guidelines", "tree_management_technical_manual",
                     "amendment_1_george_upward_streets", "amendment_7_licensed_premises"):
            assert tagger._leichhardt_slug_key(f"Leichhardt_DCP_2013__{slug}") is not None


class TestItStillRefusesToInventAKey:
    """The module's own rule: a slug resolves ONLY to a key the config declares, and
    the count may not be improved by guessing."""

    @pytest.mark.parametrize("slug", [
        "appendix_z_does_not_exist",
        "amendment_99_nope",
        "part_c_s9_invented",
        "tree_surgery_manual_not_ours",
    ])
    def test_an_unknown_document_stays_unresolved(self, tagger, slug):
        assert tagger._leichhardt_slug_key(f"Leichhardt_DCP_2013__{slug}") is None, (
            f"{slug} was mapped to a key by resemblance rather than declaration")


class TestTheNarrowingIsEvidenceBased:
    def test_part_c_section_4_is_non_residential(self):
        """Its provisions: 'C4.19 Objectives for vehicle repair stations',
        'C4.10 Parking compliance for industrial development'."""
        types = LEICHHARDT_CONFIG["parts"]["Part C Section 4"]["applicable_dev_types"]
        assert "industrial_development" in types
        assert "dwelling_house" not in types, (
            "industrial and vehicle-repair controls would be shown against houses")

    def test_part_c_section_3_is_residential(self):
        """Its provisions: 'C3.2 Building envelope', 'C3.6 Visual engagement with the
        public realm - Retaining walls'."""
        types = LEICHHARDT_CONFIG["parts"]["Part C Section 3"]["applicable_dev_types"]
        assert "dwelling_house" in types
        assert "industrial_development" not in types

    def test_nothing_else_was_narrowed(self):
        """The asymmetry that decided every entry: showing an irrelevant control is
        noise, hiding a binding one is the liability. So a part is narrowed only where
        its own provisions and its title agree unambiguously."""
        for key, _n in UNCONFIGURED.values():
            types = LEICHHARDT_CONFIG["parts"][key]["applicable_dev_types"]
            if key in NARROWED:
                assert types != ["ALL"], f"{key} was meant to be narrowed"
            else:
                assert types == ["ALL"], (
                    f"{key} was narrowed without its content unambiguously saying so; "
                    f"that hides controls from properties they bind")

    def test_appendix_b_specifically_stays_all(self):
        """It reads residential from its name -- terraces, party walls -- but its
        section headers span C4 and C6, so it is referenced from more than one Part."""
        assert LEICHHARDT_CONFIG["parts"]["Appendix B"]["applicable_dev_types"] == ["ALL"]


class TestThePartsThatWereAlreadyThere:
    def test_the_original_eight_are_untouched(self):
        """Adding nine must not disturb the parts that were already resolving."""
        for key in ("Part A", "Part B", "Part C Section 1", "Part C Section 2",
                    "Part D", "Part E", "Part F", "Part G"):
            assert key in LEICHHARDT_CONFIG["parts"]

    def test_part_f_is_still_food_only(self, tagger):
        """The one part that was already narrowed. A regression here would widen it
        silently, which is the opposite failure and equally quiet."""
        types = LEICHHARDT_CONFIG["parts"]["Part F"]["applicable_dev_types"]
        assert "food_and_drink_premises" in types and types != ["ALL"]
