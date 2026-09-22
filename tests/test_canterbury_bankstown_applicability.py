"""883 Canterbury-Bankstown provisions applied to every development type by default.

They carried `v2_dev_type_source='no_config'`: ALL because nothing matched, not because
anything decided so. 713 of them arrived on 2026-09-22 when two re-read chapters were
published, pushing DQ-33 over its floor and flipping OC-17 from passing to CONTRADICTED.
Publishing did not create the defect -- it made an existing one big enough to trip a gate.

THE TEMPTATION THIS FILE EXISTS TO REFUSE
-----------------------------------------
Declaring every chapter `['ALL']` clears the count in one line and changes nothing about
what is served. It would also be a lie: `config_all` is documented in
`ApplicabilityTagger._resolve` as "a real assertion of universality; trust it", so
asserting it for `chapter_10_7_sex_services_premises` is worse than the `no_config` it
replaces. A number made green by a false assertion is the defect DQ-33 exists to catch.

So the config uses three different states, and each one is pinned below:
  config_all      -- place/topic chapters, which genuinely bind any development there
  config_specific -- land-use chapters the tagger's vocabulary can express
  config_silent   -- land-use chapters it CANNOT (no term exists for a school, a place of
                     public worship or a home business). "Matched; nobody decided." True,
                     and not the same claim as ALL.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from enrichment.config import COUNCIL_CONFIGS  # noqa: E402
from enrichment.config.canterbury_bankstown_config import (  # noqa: E402
    CANTERBURY_BANKSTOWN_CONFIG,
)
from enrichment.extractors.applicability_tagger import ApplicabilityTagger  # noqa: E402

DOC = "Canterbury-Bankstown_DCP_2023__{}"


@pytest.fixture(scope="module")
def tagger():
    return ApplicabilityTagger()


def resolve(tagger, slug):
    return tagger._get_config_driven(DOC.format(slug), "")


class TestTheCouncilIsReachableAtAll:
    def test_the_hyphenated_document_id_finds_the_config(self):
        """document_ids are 'Canterbury-Bankstown_...' -- HYPHENATED. Registering only
        the underscored spelling would match nothing and leave every row no_config
        while the config file sat there looking correct."""
        assert "canterbury-bankstown" in COUNCIL_CONFIGS
        assert resolve(ApplicabilityTagger(), "chapter_7_6_belmore_and_lakemba") is not None


class TestPlaceScopedChaptersAssertALL:
    @pytest.mark.parametrize("slug", [
        "chapter_7_5_canterbury_local_centre",
        "chapter_7_6_belmore_and_lakemba",
        "chapter_4_3_heritage_conservation_areas",
        "chapter_2_2_flood_risk_management",
        "chapter_11_14_riverwood_estate",
    ])
    def test_it_is_config_all_not_no_config(self, tagger, slug):
        got = resolve(tagger, slug)
        assert got["dev_type_source"] == "config_all", (
            f"{slug} resolves as {got['dev_type_source']}; these chapters are scoped by "
            f"PLACE or SUBJECT, so ALL is a decision and must be recorded as one")
        assert got["applicable_dev_types"] == ["ALL"]

    def test_the_precinct_chapters_say_they_are_precinct_specific(self, tagger):
        assert resolve(tagger, "chapter_7_6_belmore_and_lakemba")["is_precinct_specific"]


class TestLandUseChaptersAreNarrowed:
    def test_sex_services_premises_is_not_ALL(self, tagger):
        got = resolve(tagger, "chapter_10_7_sex_services_premises")
        assert got["applicable_dev_types"] == ["sex_services_premises"]
        assert got["dev_type_source"] == "config_specific"

    def test_child_care_is_not_ALL(self, tagger):
        got = resolve(tagger, "chapter_10_1_child_care_centres")
        assert got["applicable_dev_types"] == ["child_care_centre"]

    def test_industrial_requirements_exclude_houses(self, tagger):
        got = resolve(tagger, "chapter_9_1_general_requirements")
        assert "industrial_development" in got["applicable_dev_types"]
        assert "dwelling_house" not in got["applicable_dev_types"]

    @pytest.mark.parametrize("slug", [
        "chapter_10_2_schools",
        "chapter_10_3_home_businesses",
        "chapter_10_5_places_of_public_worship",
    ])
    def test_what_cannot_be_expressed_is_left_UNDECIDED_not_asserted(self, tagger, slug):
        """DEV_TYPE_PATTERNS has no term for these uses. Omitting the key yields
        config_silent -- "matched, nobody decided" -- which is true. Saying ALL would
        assert that a school control binds a warehouse.

        Adding the missing vocabulary is the real fix; this records the gap honestly
        instead of papering over it.
        """
        got = resolve(tagger, slug)
        assert got["dev_type_source"] == "config_silent", (
            f"{slug} now claims {got['dev_type_source']}. If a development type for this "
            f"use was added to the vocabulary, narrow the chapter and update this test — "
            f"do not let it become an assertion of ALL")

    def test_no_chapter_claims_config_all_from_the_land_use_family(self, tagger):
        """The 10.x family is 'specific land uses' by definition. If one of them ever
        reads config_all, someone has cleared a count by asserting universality."""
        for slug in CANTERBURY_BANKSTOWN_CONFIG["chapter_topics"]:
            if not slug.startswith("chapter_10_"):
                continue
            got = resolve(tagger, slug)
            assert got["dev_type_source"] != "config_all", (
                f"{slug} asserts ALL; a specific-land-use chapter cannot bind every "
                f"development type")


class TestItStillRefusesToInventAScope:
    @pytest.mark.parametrize("slug", [
        "chapter_99_does_not_exist",
        "chapter_12_1_invented_precinct",
    ])
    def test_an_unknown_chapter_stays_unresolved(self, tagger, slug):
        assert resolve(tagger, slug) is None, (
            f"{slug} was given a scope by resemblance; an unknown document must stay "
            f"no_config so it is COUNTED rather than silently blessed")

    def test_every_declared_chapter_uses_a_real_development_type(self, tagger):
        """A typo here narrows a chapter to a type that matches nothing, which hides
        every control in it -- the silent, harmful direction."""
        known = set(ApplicabilityTagger.DEV_TYPE_PATTERNS)
        for slug, entry in CANTERBURY_BANKSTOWN_CONFIG["chapter_topics"].items():
            for dt in entry.get("applicable_dev_types", []):
                assert dt == "ALL" or dt in known, f"{slug} names unknown dev type {dt!r}"
