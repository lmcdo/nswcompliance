"""Blacktown, Penrith, Hornsby and Georges River — scope read from their own PDFs.

Four councils served rules with no applicability config at all, so their rules
applied to EVERY development type by fallthrough rather than by decision
(DQ-105). Writing a config is the one onboarding step nothing can derive: it
records which zones and development types each Part binds, taken from that
Part's own scope section.

EVERY ASSERTION HERE IS A QUOTATION, and the reason is canterbury_bankstown's
chapter 9.1. That chapter was configured as industrial on the strength of its
position in the numbering; its own first page scopes it to Zone E4 while its
controls govern food premises and vehicle body repair workshops, so the guessed
config deleted a food-premises control from every food-premises application.
Titles are not scopes.

THE TWO WAYS TO GET THIS WRONG ARE NOT SYMMETRIC
------------------------------------------------
Both columns are HARD filters on the served answer. Asserting ALL where the Part
says otherwise is a false claim of universality; naming a PARTIAL list makes a
binding control disappear. So a key is declared only where the Part states it,
and omitted otherwise -- `config_silent`, "matched, nobody decided", which is
true and is NOT `no_config`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from enrichment.config import COUNCIL_CONFIGS  # noqa: E402
from enrichment.config.blacktown_config import BLACKTOWN_CONFIG  # noqa: E402
from enrichment.config.georges_river_config import GEORGES_RIVER_CONFIG  # noqa: E402
from enrichment.config.hornsby_config import HORNSBY_CONFIG  # noqa: E402
from enrichment.config.penrith_config import PENRITH_CONFIG  # noqa: E402
from enrichment.config.wollongong_config import WOLLONGONG_CONFIG  # noqa: E402
from enrichment.extractors.applicability_tagger import ApplicabilityTagger  # noqa: E402

#: The production document_ids, exactly as regulatory_provisions stores them.
DOCS = {
    "blacktown_part_c": "Blacktown_DCP_2015__blacktown_dcp_2015_part_c",
    "blacktown_parking": "Blacktown_DCP_2015__part_a_car_parking",
    "penrith_c10": "Penrith_DCP_2014__c10_transport_access_parking",
    "penrith_d2": "Penrith_DCP_2014__penrith_dcp_2014_part_d2",
    "hornsby_general": "Hornsby_DCP_2024__part_1_general",
    "hornsby_residential": "Hornsby_DCP_2024__hornsby_dcp_2024_part3_residential",
    "gr_general": "Georges_River_DCP_2021__part_3_general_planning_considerations",
    "gr_low_density": "Georges_River_DCP_2021__grdcp_part_6_1_low_density",
    "wg_intro": "Wollongong_DCP_2009__chapter_a1_introduction",
    "wg_residential": "Wollongong_DCP_2009__chapter_b1_residential",
    "wg_parking": "Wollongong_DCP_2009__chapter_e3_car_parking",
    "wg_landscaping": "Wollongong_DCP_2009__chapter_e6_landscaping",
    "wg_heritage": "Wollongong_DCP_2009__chapter_e11_heritage_conservation",
    "wg_trees": "Wollongong_DCP_2009__chapter_e17_trees_and_vegetation",
}

CONFIGS = {"blacktown": BLACKTOWN_CONFIG, "penrith": PENRITH_CONFIG,
           "hornsby": HORNSBY_CONFIG, "georges_river": GEORGES_RIVER_CONFIG,
           "wollongong": WOLLONGONG_CONFIG}


@pytest.fixture(scope="module")
def tagger():
    return ApplicabilityTagger()


def resolve(tagger, key):
    return tagger._get_config_driven(DOCS[key], "")


class TestEveryCouncilIsReachable:
    @pytest.mark.parametrize("council", sorted(CONFIGS))
    def test_registered_in_the_lookup(self, council):
        """A config nothing can reach is indistinguishable from no config: the
        rows stay `no_config` while the file sits there looking correct."""
        assert council in COUNCIL_CONFIGS

    @pytest.mark.parametrize("key", sorted(DOCS))
    def test_every_served_document_resolves(self, tagger, key):
        assert resolve(tagger, key) is not None, (
            f"{DOCS[key]} reaches no entry -- its rows stay no_config")


class TestScopesAreQuotedNotGuessed:
    def test_blacktown_part_c_is_the_residential_zones(self, tagger):
        """Section 1.1 "Land to which this Part applies": "This Part of the DCP
        applies to all land within the Blacktown Local Government Area zoned for
        residential purposes under Blacktown LEP 2015." The four R zones are the
        ones lep_zone_coverage records for this LGA -- taken from the data, not
        assumed, so a zone Blacktown does not have is never declared."""
        got = resolve(tagger, "blacktown_part_c")
        assert got["applicable_zones"] == ["R1", "R2", "R3", "R4"]  # noqa: zone-codes
        assert got["zone_source"] == "config_specific"
        assert got["dev_type_source"] == "config_silent", (
            "the Part binds ALL development in those zones, not a list of types")

    def test_blacktown_car_parking_is_the_whole_lga(self, tagger):
        """Section 1.1: "Blacktown DCP 2015 applies to all land within the
        Blacktown Local Government Area that is zoned under Blacktown Local
        Environmental Plan (LEP) 2015." ALL here is an assertion, not a
        fallthrough -- a parking Part binds anything generating parking."""
        got = resolve(tagger, "blacktown_parking")
        assert got["zone_source"] == "config_all"
        assert got["dev_type_source"] == "config_all"

    def test_penrith_c10_binds_everything_that_generates_a_trip(self, tagger):
        got = resolve(tagger, "penrith_c10")
        assert got["zone_source"] == "config_all"
        assert got["dev_type_source"] == "config_all"

    def test_penrith_d2_decides_NEITHER_key(self, tagger):
        """The trap this whole file exists for. "D2 Residential Development"
        reads like a residential-only Part and is not one: its own contents are
        2.1 Single Dwellings, 2.2 Dual Occupancies, 2.4 Multi Dwelling Housing,
        2.5 Residential Flat Buildings -- and 2.6 NON RESIDENTIAL DEVELOPMENTS.
        Declaring the residential types would delete section 2.6 from every
        non-residential application it governs."""
        got = resolve(tagger, "penrith_d2")
        assert got["zone_source"] == "config_silent"
        assert got["dev_type_source"] == "config_silent"

    def test_hornsby_general_applies_to_all_land(self, tagger):
        got = resolve(tagger, "hornsby_general")
        assert got["zone_source"] == "config_all"
        assert got["dev_type_source"] == "config_all"

    def test_hornsby_residential_is_the_residential_zones(self, tagger):
        """Introduction: "This Part of the DCP applies to residential
        development within the Residential zones of the Hornsby Local
        Government Area." Hornsby has no R1 and no R5 in lep_zone_coverage, so  # noqa: zone-codes (verbatim reasoning about this LGA's own zone list)
        neither is declared."""
        got = resolve(tagger, "hornsby_residential")
        assert got["applicable_zones"] == ["R2", "R3", "R4"]  # noqa: zone-codes
        assert got["dev_type_source"] == "config_silent"

    def test_georges_river_general_applies_to_all_forms(self, tagger):
        """Part 3, verbatim: this Part "applies to all forms of development"."""
        got = resolve(tagger, "gr_general")
        assert got["dev_type_source"] == "config_all"

    def test_georges_river_low_density_names_its_three_expressible_types(self, tagger):
        """Section 6.1.1: "This part applies to dwelling houses, dual occupancy
        development, secondary dwellings and narrow lot housing." Three of the
        four have a term. "Narrow lot housing" has none -- and, checked
        2026-09-23, neither does the SERVING taxonomy in devTypeHierarchy.ts, so
        no query can ask for it and naming the other three hides nothing. That
        check is the test: a missing term matters only when somebody can select
        it."""
        got = resolve(tagger, "gr_low_density")
        assert set(got["applicable_dev_types"]) == {
            "dwelling_house", "dual_occupancy", "secondary_dwelling"}
        assert got["zone_source"] == "config_silent", (
            "the Part names development forms, not zones")


class TestWollongong:
    def test_residential_is_the_residential_zones_and_c4_not_e4(self, tagger):
        # "E4 Environmental Living" in the 2009 text is C4 since 2023; E4 is
        # now General Industrial and must not receive dwelling controls.
        zones = WOLLONGONG_CONFIG["chapter_topics"]["chapter_b1_residential"]["applicable_zones"]
        assert set(zones) == {"R1", "R2", "R3", "R4", "R5", "C4"}  # noqa: zone-codes
        assert "E4" not in zones  # noqa: zone-codes

    def test_heritage_is_a_site_condition(self, tagger):
        e = WOLLONGONG_CONFIG["chapter_topics"]["chapter_e11_heritage_conservation"]
        assert e["layer"] == "condition" and e["site_conditions"] == ["heritage"]

    def test_landscaping_decides_neither_key(self):
        e = WOLLONGONG_CONFIG["chapter_topics"]["chapter_e6_landscaping"]
        assert e and "applicable_zones" not in e and "applicable_dev_types" not in e

    def test_every_active_wollongong_chapter_has_an_entry(self):
        keys = {d.split("__", 1)[1] for k, d in DOCS.items() if k.startswith("wg_")}
        assert keys == set(WOLLONGONG_CONFIG["chapter_topics"])


class TestItRefusesTheEasyWaysToGoGreen:
    def test_no_entry_is_an_empty_dict(self):
        """`_resolve` opens with `if not entry: return ['ALL'], 'no_config'`, so
        an entry declaring neither key is falsy and collapses straight back to
        the state these configs exist to clear -- with every value-level test
        above still green. penrith_d2 is one `layer` line away from it."""
        for council, cfg in CONFIGS.items():
            for slug, entry in cfg["chapter_topics"].items():
                assert entry, f"{council}/{slug} is an empty dict -> no_config"

    def test_no_row_can_come_back_as_no_config(self, tagger):
        for key, doc in DOCS.items():
            _z, _d, prov = tagger.tag_with_provenance("Any control text.", doc)
            assert "no_config" not in prov.values(), key

    def test_every_declared_dev_type_exists_in_the_vocabulary(self):
        """A typo narrows a Part to a type nothing matches, hiding every control
        in it -- silently, in the harmful direction."""
        known = set(ApplicabilityTagger.DEV_TYPE_PATTERNS)
        for council, cfg in CONFIGS.items():
            for slug, entry in cfg["chapter_topics"].items():
                for dt in entry.get("applicable_dev_types", []):
                    assert dt == "ALL" or dt in known, f"{council}/{slug}: {dt!r}"

    def test_no_retired_zone_code_is_declared(self):
        """OC-17 fails on served rows applying to a retired zone code. A config
        is the easiest place to reintroduce one, because DCP text still prints
        the pre-2022 business and industrial codes."""
        retired = {"B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8",  # noqa: zone-codes
                   "IN1", "IN2", "IN3", "IN4"}  # noqa: zone-codes
        for council, cfg in CONFIGS.items():
            for slug, entry in cfg["chapter_topics"].items():
                for z in entry.get("applicable_zones", []):
                    assert z not in retired, f"{council}/{slug} declares {z!r}"

    def test_an_unknown_chapter_stays_unresolved(self, tagger):
        """`_get_config_driven` must not bless a document by resemblance."""
        assert tagger._get_config_driven(
            "Blacktown_DCP_2015__part_z_invented", "") is None
