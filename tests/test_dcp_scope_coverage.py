"""Default-scope coverage: which of the six a council has, and what blocks the rest.

The blocker split is the load-bearing part. Measured 2026-09-12, 33 of 37 missing
chapters have no mirrored PDF and only 4 have a PDF that was never extracted --
so a check that conflates those two sends the next session to fix the wrong
thing, which is exactly what happened before this existed.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.dcp_scope_coverage import (  # noqa: E402
    BUCKETS, HAVE_PAGE, HAVE_URL, HAZARD_BUCKETS, LGA_OVERRIDES, NO_URL,
    bucket_for, chapter_state, council_lga, required_buckets,
)


class TestBucketing:
    def test_real_chapter_keys_land_in_the_right_bucket(self):
        cases = [
            ("part-2-residential", "", "residential"),
            ("chapter-5-dwelling-houses", "", "residential"),
            ("part-1-car-parking-access", "", "parking"),
            ("s4-landscaping", "", "landscape"),
            ("chapter-e1-heritage", "", "heritage"),
            ("part1-statutory-info", "", "general"),
            ("section-a-part-7-residential-flat", "", "rfb_mixed"),
        ]
        for key, label, expected in cases:
            assert bucket_for(key, label) == expected, key

    def test_residential_flat_is_not_swallowed_by_residential(self):
        # 'residential' must not claim 'residential flat buildings': they are two
        # different default-scope chapters and conflating them would report a
        # council as having a chapter it does not.
        assert bucket_for("residential-flat-buildings", "") == "rfb_mixed"

    def test_the_label_is_used_when_the_key_says_nothing(self):
        assert bucket_for("part-c-s1", "Parking and Access") == "parking"

    def test_an_out_of_scope_chapter_matches_no_bucket(self):
        # signage, industrial, sex services etc are explicitly out of first-pass
        # scope. None must be reported and never guessed into a bucket.
        for key in ("chapter-3-6-signs", "part6-industrial",
                    "part7-s3-sex-industry", "chapter-f4-telecommunications"):
            assert bucket_for(key, "") is None, key

    def test_every_bucket_name_is_unique(self):
        names = [n for n, _ in BUCKETS] + [n for n, _, _ in HAZARD_BUCKETS]
        assert len(names) == len(set(names))

    def test_hazard_chapters_get_their_own_bucket(self):
        for key, expected in [("part2-s22-flood-management", "flood"),
                              ("chapter-e2-stormwater-flood", "flood"),
                              ("part2-s23-acid-sulfate", "acid_sulfate"),
                              ("section-b-part-16-bushfire", "bushfire"),
                              ("chapter-e1-heritage", "heritage")]:
            assert bucket_for(key, "") == expected, key

    def test_a_TREES_chapter_is_landscaping_not_biodiversity(self):
        # An earlier pattern matched 'vegetation|tree' for biodiversity, which
        # claimed ku_ring_gai's "Part 13 Trees" -- reporting landscaping MISSING
        # and biodiversity held, both wrong, from one over-broad pattern.
        assert bucket_for("section-a-part-13-trees", "") == "landscape"
        assert bucket_for("chapter-e3-tree-management", "") == "landscape"
        assert bucket_for("part-b-biodiversity-corridors", "") == "biodiversity"


class TestPerCouncilTarget:
    def test_a_council_only_needs_hazards_its_properties_carry(self):
        # The whole point: the target is derived, not templated.
        coastal = required_buckets({"heritage", "flood", "acid_sulfate"})
        inland = required_buckets({"heritage"})
        assert "flood" in coastal and "acid_sulfate" in coastal
        assert "flood" not in inland and "acid_sulfate" not in inland

    def test_the_five_universal_buckets_are_ALWAYS_required(self):
        for name, _ in BUCKETS:
            assert name in required_buckets(set())

    def test_no_overlays_means_no_hazard_chapters_required(self):
        assert required_buckets(set()) == [n for n, _ in BUCKETS]

    def test_riparian_is_triggered_by_either_layer(self):
        assert "riparian" in required_buckets({"riparian"})
        assert "riparian" in required_buckets({"foreshore_building_line"})


class TestCouncilToLgaJoin:
    LGAS = {"INNER WEST", "SYDNEY", "CITY OF PARRAMATTA", "BAYSIDE",
            "CANTERBURY-BANKSTOWN", "KU-RING-GAI"}

    def test_a_merged_council_maps_to_its_MERGED_lga(self):
        # ashfield/leichhardt/marrickville DCPs are separate documents, but their
        # PROPERTIES are Inner West's. Getting this wrong hands the council an
        # empty overlay profile and marks it complete with no hazard chapters.
        for council in ("ashfield", "leichhardt", "marrickville"):
            assert council_lga(council, self.LGAS) == "INNER WEST", council

    def test_plain_names_match_without_an_override(self):
        assert council_lga("bayside", self.LGAS) == "BAYSIDE"
        assert council_lga("canterbury_bankstown", self.LGAS) == "CANTERBURY-BANKSTOWN"

    def test_statewide_is_not_a_council(self):
        assert council_lga("state", self.LGAS) is None

    def test_an_unknown_council_returns_None_rather_than_a_wrong_lga(self):
        assert council_lga("nowhere_shire", self.LGAS) is None

    def test_every_override_points_at_a_real_lga_name_shape(self):
        for slug, lga in LGA_OVERRIDES.items():
            assert lga == lga.upper(), slug


class TestBlockerSplit:
    def test_serving_beats_everything(self):
        assert chapter_state("r2/x.pdf", "http://u", "http://p", True) == "SERVING"

    def test_a_mirrored_pdf_that_never_extracted_is_its_own_state(self):
        # 4 chapters. Cheapest real coverage available -- the file is already there.
        assert chapter_state("r2/x.pdf", None, None, False) == "NOT_EXTRACTED"

    def test_a_direct_url_means_r2_monitor_can_fetch_it_now(self):
        assert chapter_state(None, "http://council/doc.pdf", None, False) == HAVE_URL

    def test_a_PAGE_url_is_NOT_the_same_as_a_pdf_url(self):
        # THE DISTINCTION THAT MATTERS. r2_monitor selects on
        # council_url IS NOT NULL, so a chapter with only a page url is not
        # failing to mirror -- it is never attempted. 24 chapters sit here.
        assert chapter_state(None, None, "http://council/page", False) == HAVE_PAGE

    def test_nothing_at_all_needs_a_person(self):
        assert chapter_state(None, None, None, False) == NO_URL

    def test_the_state_is_not_constant(self):
        seen = {
            chapter_state("p", None, None, True),
            chapter_state("p", None, None, False),
            chapter_state(None, "u", None, False),
            chapter_state(None, None, "g", False),
            chapter_state(None, None, None, False),
        }
        assert len(seen) == 5
