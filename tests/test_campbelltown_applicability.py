"""268 Campbelltown provisions applied to every development type by default.

Every served row of the council did, because Campbelltown had no config file at
all: `_get_config_driven` found no matching key in COUNCIL_CONFIGS, returned
None, and each row fell through to ALL/ALL with source `no_config` -- ALL because
nothing matched, not because anything decided so.

WHAT THIS FILE IS GUARDING
--------------------------
Both applicability columns are HARD FILTERS on the served answer
(`frontend-nextjs/app/api/provisions/for-property/route.ts` lines 1012 and 1222,
`app/api/permissibility/check/route.ts` line 207): a row survives only if the
column is NULL, holds 'ALL', or overlaps the query. So naming a value here does
not make that value's answer better -- it deletes the row from every other
answer. The two ways to get this wrong are therefore not symmetric:

  asserting ALL where the chapter says otherwise  -> a false claim of universality
  naming a partial list                           -> a binding control disappears

The config takes the first horn only where the chapter's own Application section
supports it, and refuses the second by OMITTING the key -- `config_silent`,
"matched, nobody decided", which is true, auditable, and not `no_config`.

Both scopes asserted below are quoted from the chapter PDFs the registry points
at, read 2026-09-23.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from enrichment.config import COUNCIL_CONFIGS  # noqa: E402
from enrichment.config.campbelltown_config import CAMPBELLTOWN_CONFIG  # noqa: E402
from enrichment.extractors.applicability_tagger import ApplicabilityTagger  # noqa: E402

#: The real production shape, parentheses and all.
DOC = "Campbelltown_(Sustainable_City)_DCP_2015__{}"

PART3 = "campbelltown_dcp_part3_low_medium"
PART4 = "part_4_rfb_mixed_use"

#: Retired under the 2022 employment-zone reform and absent from
#: `lep_zone_coverage` for this LGA. Part 4's own text still names four of them.
RETIRED_ZONES = {"B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "IN1", "IN2",  # noqa: zone-codes (the retired codes this test exists to REFUSE; importing the live taxonomy would defeat it, since these are gone from it)
                 "IN3", "IN4", "B"}  # noqa: zone-codes


@pytest.fixture(scope="module")
def tagger():
    return ApplicabilityTagger()


def resolve(tagger, slug):
    return tagger._get_config_driven(DOC.format(slug), "")


class TestTheCouncilIsReachableAtAll:
    def test_the_registry_key_matches_the_real_document_id(self, tagger):
        """A config nothing can reach is indistinguishable from no config: the
        rows stay `no_config` while the file sits there looking correct."""
        assert "campbelltown" in COUNCIL_CONFIGS
        assert resolve(tagger, PART3) is not None
        assert resolve(tagger, PART4) is not None

    def test_both_registered_chapters_are_covered(self, tagger):
        """`dcp_chapter_registry` holds exactly two chapters for this council. If
        a third is onboarded, its rows go straight back to `no_config` -- so the
        count of entries is itself the thing to notice."""
        assert set(CAMPBELLTOWN_CONFIG["chapter_topics"]) == {PART3, PART4}


class TestPart3IsScopedByZone:
    def test_the_zones_are_the_four_the_chapter_names(self, tagger):
        """Section 3.1 Application: "General Requirements for all Types of
        Residential Development in areas zoned R2, R3, R4 and R5", and the same  # noqa: zone-codes (verbatim chapter text)
        four zones on every one of its sub-lists."""
        got = resolve(tagger, PART3)
        assert got["applicable_zones"] == ["R2", "R3", "R4", "R5"]  # noqa: zone-codes (quoted from section 3.1 Application)
        assert got["zone_source"] == "config_specific"

    def test_development_types_are_left_UNDECIDED_not_enumerated(self, tagger):
        """The chapter binds "all Types of Residential Development" PLUS its
        ancillary structures (fencing, outbuildings, swimming pools/spas) PLUS
        section 3.8 residential subdivision. No enumeration survives the hard
        filter intact: semi-detached and attached dwellings have no term in
        DEV_TYPE_PATTERNS at all, and a residential-only list would delete
        section 3.3 from a `fence` DA, 3.5 from an `outbuilding` DA, the pool
        controls from a `pool` DA and 3.8 from a `subdivision` DA -- every one of
        those selectable in frontend-nextjs/lib/see/ancillaryWorks.ts.
        """
        got = resolve(tagger, PART3)
        assert got["dev_type_source"] == "config_silent", (
            "Part 3 now names development types. Before doing that, check every "
            "ancillary and subdivision type in devTypeHierarchy.ts against the "
            "chapter's section list -- anything left out disappears from that "
            "type's answer")

    def test_it_is_not_asserted_as_universal(self, tagger):
        """config_all would claim the chapter binds every zone. It says R2-R5."""  # noqa: zone-codes (verbatim chapter text)
        assert resolve(tagger, PART3)["zone_source"] != "config_all"


class TestPart4IsScopedByDevelopmentType:
    def test_the_types_come_from_the_chapters_own_definition(self, tagger):
        """Section 5.1 Application covers "residential flat buildings in areas
        zoned R4" and mixed use development, defined there as development "which
        includes residential uses (such as shop top housing where relevant) in
        conjunction with one or more uses such as, business premises, commercial
        offices, retail shops, community facilities and medical centres"."""
        got = resolve(tagger, PART4)
        assert set(got["applicable_dev_types"]) == {
            "residential_flat_building", "shop_top_housing",
            "commercial_premises", "office_premises", "retail_premises"}
        assert got["dev_type_source"] == "config_specific"

    def test_a_low_density_type_is_excluded(self, tagger):
        """The separation from Part 3 is the whole point of the two entries."""
        assert "dwelling_house" not in resolve(tagger, PART4)["applicable_dev_types"]

    def test_zones_are_left_UNDECIDED_because_the_chapter_names_retired_codes(self, tagger):
        """Four of the six zones section 5.1 names -- B1, B2, B3, B4 -- were  # noqa: zone-codes (verbatim chapter text, and the point of the test)
        retired by the 2022 employment-zone reform and none appears in
        `lep_zone_coverage` for this LGA. Declaring ["R4", "RU5"] alone would  # noqa: zone-codes (verbatim chapter text)
        hide every mixed-use control from the centres the chapter was written
        for; mapping B3/B4 onto E2/MU1 here would be interpreting the instrument  # noqa: zone-codes (the successor mapping this config deliberately does NOT make)
        inside a config file. Undecided is the honest state until the successor
        mapping lands with its own citation.
        """
        assert resolve(tagger, PART4)["zone_source"] == "config_silent"


class TestItRefusesTheEasyWaysToGoGreen:
    def test_no_entry_asserts_universality_on_either_key(self, tagger):
        """Declaring ['ALL'] everywhere clears `no_config` in one line and
        changes nothing about what is served. `config_all` is documented in
        `ApplicabilityTagger._resolve` as "a real assertion of universality;
        trust it" -- so it has to be earned by the chapter's own words, and
        neither of these two chapters says it."""
        for slug in CAMPBELLTOWN_CONFIG["chapter_topics"]:
            got = resolve(tagger, slug)
            assert got["zone_source"] != "config_all", slug
            assert got["dev_type_source"] != "config_all", slug

    def test_no_retired_zone_code_is_declared(self):
        """OC-17 fails on "served rows that apply to a retired zone code but not
        to its successor". A config is the easiest place to reintroduce one,
        because the chapter text still prints them."""
        for slug, entry in CAMPBELLTOWN_CONFIG["chapter_topics"].items():
            for z in entry.get("applicable_zones", []):
                assert z not in RETIRED_ZONES, f"{slug} declares retired zone {z!r}"

    def test_every_declared_dev_type_exists_in_the_vocabulary(self):
        """A typo narrows a chapter to a type that matches nothing, which hides
        every control in it -- silently, and in the harmful direction."""
        known = set(ApplicabilityTagger.DEV_TYPE_PATTERNS)
        for slug, entry in CAMPBELLTOWN_CONFIG["chapter_topics"].items():
            for dt in entry.get("applicable_dev_types", []):
                assert dt == "ALL" or dt in known, f"{slug} names unknown type {dt!r}"

    def test_an_unknown_chapter_stays_unresolved(self, tagger):
        """`_get_config_driven` must not bless a document by resemblance: an
        unrecognised chapter has to stay `no_config` so DQ-33 still counts it."""
        assert resolve(tagger, "part_9_invented_chapter") is None


class TestTheWholeRowComesOutRight:
    """`_get_config_driven` is the unit; `tag_with_provenance` is what actually
    writes the columns, and it has its own combine step that can undo either."""

    def test_part3_row_keeps_its_zones_and_stays_undecided_on_types(self, tagger):
        zones, devs, prov = tagger.tag_with_provenance(
            "The minimum front setback for a dwelling house is 4.5m.",
            DOC.format(PART3))
        assert zones == ["R2", "R3", "R4", "R5"]  # noqa: zone-codes (quoted from section 3.1 Application)
        assert devs == ["ALL"]
        assert prov == {"zone_source": "config_specific",
                        "dev_type_source": "config_silent"}

    def test_part4_row_keeps_its_types_and_stays_undecided_on_zones(self, tagger):
        zones, devs, prov = tagger.tag_with_provenance(
            "Building separation for a residential flat building is 12m.",
            DOC.format(PART4))
        assert zones == ["ALL"]
        assert "residential_flat_building" in devs
        assert prov == {"zone_source": "config_silent",
                        "dev_type_source": "config_specific"}

    def test_neither_row_can_come_back_as_no_config(self, tagger):
        """The defect this config was written for. `no_config` means nothing
        matched; if it reappears the council is unreachable again."""
        for slug in (PART3, PART4):
            _z, _d, prov = tagger.tag_with_provenance("Any control text.",
                                                      DOC.format(slug))
            assert "no_config" not in prov.values(), slug
