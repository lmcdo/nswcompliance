"""DQ-143/DQ-144 read their chapter list from data/chapter_scope/. If that file went missing
the key lists would be empty and DQ-143 would read 0 -- a silent pass. These tests fail
first instead.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import dq_probe_live as p  # noqa: E402


def test_scope_file_loads_every_chapter():
    keys = p._chapter_scope_keys()
    assert len(keys) == 265  # 2026-10-16: +1 wollongong a1; +27 waverley Parts; +2 plan introductions (ku-ring-gai, ashfield)
    assert all("__" in k for k in keys)


def test_dq143_has_part_of_council_chapters_with_their_gate_kind():
    keys, kinds = p.PROBES["DQ-143"][2]
    assert len(keys) == len(kinds) >= 100
    gate = dict(zip(keys, kinds))
    assert gate["leichhardt__amendment-1-george-upward-streets"] == "place"
    assert "heritage" in kinds and "zone" in kinds


def test_heritage_area_chapter_needs_its_own_area_not_a_generic_tag():
    sql = p._GATED_FOR_ITS_CHAPTER
    assert "cs.kind = 'heritage' AND rp.v2_heritage_hca IS NOT NULL" in sql
    # A generic heritage tag reaches every heritage house, so it gates ONLY a chapter whose own
    # sentence covers every heritage item/area (heritage_general), never a named-area chapter.
    generic = sql.split("cs.kind = 'heritage_general'")
    assert len(generic) == 2 and "v2_marker" not in generic[0] and "v2_marker" in generic[1]


def test_missing_scope_file_raises_not_zero(monkeypatch, tmp_path):
    monkeypatch.setattr(p, "Path", lambda *_a, **_k: tmp_path / "x" / "y" / "z.py")
    try:
        p._load_chapter_scope()
    except (OSError, ValueError):
        return
    raise AssertionError("an absent chapter-scope file must raise, never yield []")


def test_dq144_excludes_only_decided_chapters():
    excluded = set(p.PROBES["DQ-144"][2][0])
    part = set(p._chapter_scope_keys(part_of_council=True))
    assert part <= excluded
    # AI-labelled whole-council chapters NOT confirmed by the fixed pattern stay counted.
    assert "canterbury_bankstown__chapter-4-4-vicinity-of-places-of-heritage-significance" not in excluded


def test_council_wide_pattern_confirms_only_land_wording():
    yes = p._COUNCIL_WIDE.search
    assert yes("This Part applies to all land within the Ashfield local government area.")
    assert yes("applies to the land to which Canterbury-Bankstown LEP 2023 applies")
    assert not yes("any works that take place on land in the vicinity of a place of heritage significance")
    assert not yes("To regulate the effective and orderly development of child care facilities")
    assert not yes("This chapter applies to the whole of the site")


def test_mapped_wording_is_never_council_wide():
    for quote in ("This chapter applies to all land within the City shown on Map 1",
                  "applies to all land in the LGA identified in Figure 3"):
        assert not p._machine_whole_council({"applies_to": "whole_council", "quote": quote})


def test_machine_whole_council_needs_the_label_and_the_words():
    words = "This DCP applies to all land in the City."
    assert p._machine_whole_council({"applies_to": "whole_council", "quote": words})
    assert not p._machine_whole_council({"applies_to": "place", "quote": words})
    assert not p._machine_whole_council({"applies_to": "whole_council", "quote": None})


# 2026-10-16: wider wording, accepted with the user's OK, tested on known-wrong sentences first.
import pytest  # noqa: E402

_NEW_CASES = [
    ("use_type", "This chapter applies to development in the vicinity of places of heritage significance", False),
    ("use_type", "This Part applies to development within the Lindfield local centre", False),
    ("use_type", "This Part applies to residential development in the R2 zone", False),
    ("use_type", "This Part applies to development on land in the Turramurra area", False),
    ("whole_council", "This Part applies to land shown on Map 1", False),
    ("whole_council", "Council has consolidated all of its DCPs that apply to the Parramatta Local Government "
                      "Area (LGA) into one plan", False),
    ("use_type", "This Part applies to development for dual occupancy dwellings", True),
    ("use_type", "This Part applies to all development types whether or not it is individually specified in "
                 "Section A of this DCP.", True),
    ("use_type", "The provisions in this section apply to all development to which this DCP applies, except "
                 "where it is clear that they are not relevant to a particular development type or use.", True),
    ("whole_council", "This DCP applies to land within the Canterbury-Bankstown Local Government Area.", True),
    ("use_type", "This part contains objectives and design controls for the protection of the environment and "
                 "applies to all forms of development.", True),
    ("use_type", "This DCP Chapter applies to any development requiring development consent under Part 4 or "
                 "approval under Part 5 of the Environmental Planning and Assessment Act 1979", True),
    ("use_type", "This part contains controls for the Hurstville City Centre and applies to all development", False),
    ("use_type", "This DCP Chapter applies to any development requiring development consent under Part 4 in the "
                 "Wollongong Local Government Area.", True),
    ("use_type", "This Part applies to development in the Wollongong City Centre", False),
    ("whole_council", "This Chapter of the DCP applies to all lands within the City of Wollongong Local "
                      "Government Area.", True),
]


@pytest.mark.parametrize("applies_to,quote,want", _NEW_CASES)
def test_wider_wording_accepts_only_unlimited_land(applies_to, quote, want):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    import dq_probe_live as d
    assert d._machine_whole_council({"applies_to": applies_to, "quote": quote}) is want


def test_waverley_place_and_condition_parts_are_never_listed_as_whole_council():
    """B4 Coastal Risk, B8 Heritage and E1-E4 (Bondi Junction, Bondi Beachfront, village centres, special  # noqa: zone-codes (Waverley DCP Part numbers, not zones)
    character areas) are land limits. Listing any of them as inheriting the plan's land would serve their
    rules to every house in Waverley."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    import dq_probe_live as d
    keys = set(d._chapter_scope_keys(machine_whole_council=True))
    for part in ("B4", "B8", "E", "E1", "E2", "E3", "E4"):  # noqa: zone-codes (Waverley DCP Part numbers, not zones)
        assert f"waverley__waverley-dcp-2022#{part}" not in keys
    assert "waverley__waverley-dcp-2022#C1" in keys          # Low Density Residential inherits the plan's land
    assert "waverley__waverley-dcp-2022" not in keys          # the whole document stays mixed_parts


def test_a_chapter_recorded_mixed_is_not_overridden_by_inheritance():
    """City of Sydney Schedules mixes general schedules with area ones (Schedule 6 Signage in The Rocks, Green
    Square). A scan of its first pages found no land wording, but that does not make it whole-council."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    import dq_probe_live as d
    assert "city_of_sydney__schedules" not in set(d._chapter_scope_keys(machine_whole_council=True))
