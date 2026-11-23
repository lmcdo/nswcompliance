"""A cross-reference to a chapter of the plan ("Part E4") is not a zone, even when its code is also a zone code."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enrichment.extractors.applicability_tagger import ApplicabilityTagger, strip_plan_references  # noqa: E402


def zones(text):
    return ApplicabilityTagger()._extract_zones_from_text(text)


def test_a_part_reference_is_not_read_as_a_zone():
    assert "E4" not in zones("# Special Character Areas\n\nRefer to Part E4 for Special Character Areas which apply to residential land.")  # noqa: zone-codes -- E4 here is a plan Part


def test_other_reference_words_are_stripped_too():
    for t in ("See Chapter B3 for trees", "as set out in Annexure B3-2", "Refer to Appendix E1", "see Section B1.2", "Figure B3-4 shows", "Table E4 lists", "Schedule B1"):  # noqa: zone-codes -- plan reference codes, the test proves they are removed
        assert not any(c in strip_plan_references(t) for c in ("B3", "E4", "E1", "B1")), t  # noqa: zone-codes -- plan reference codes, the test proves they are removed


def test_a_real_zone_mention_survives():
    assert "R2" in zones("Development in the R2 Low Density Residential zone must provide a landscaped area.")  # noqa: zone-codes -- a real zone mention
    assert "B3" in zones("Land zoned B3 Commercial Core permits shop top housing.")  # noqa: zone-codes -- a real zone mention


def test_a_zone_written_next_to_a_reference_is_still_found():
    z = zones("Refer to Part E4 for character areas. Land in zone R3 is also covered.")  # noqa: zone-codes -- E4 is a plan Part, R3 a real zone
    assert "R3" in z and "E4" not in z  # noqa: zone-codes -- as above


def test_a_zone_written_with_the_word_zone_is_not_stripped():
    assert "E4" in zones("Land in zone E4 Environmental Living must retain trees.")  # noqa: zone-codes -- a real zone mention
