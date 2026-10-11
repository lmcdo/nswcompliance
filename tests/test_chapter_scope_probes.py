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
    assert len(keys) == 235
    assert all("__" in k for k in keys)


def test_dq143_has_part_of_council_chapters():
    keys = p.PROBES["DQ-143"][2][0]
    assert len(keys) >= 100
    assert "leichhardt__amendment-1-george-upward-streets" in keys


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


def test_machine_whole_council_needs_the_label_and_the_words():
    words = "This DCP applies to all land in the City."
    assert p._machine_whole_council({"applies_to": "whole_council", "quote": words})
    assert not p._machine_whole_council({"applies_to": "place", "quote": words})
    assert not p._machine_whole_council({"applies_to": "whole_council", "quote": None})
