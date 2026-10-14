"""Publish refuses a chapter whose new version would lose its area links (scripts/dcp_area_link_guard.py).

prior-art-checked: new module; pure judge plus a fake cursor, no database.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import dcp_area_link_guard as g  # noqa: E402


def test_keeping_nine_tenths_of_the_links_passes():
    assert g.judge(100, 90) and g.judge(100, 150)


def test_losing_more_than_a_tenth_of_the_links_is_refused():
    assert not g.judge(89, 4)            # Waverley pilot: 4 of 89 Part E links
    assert not g.judge(1009, 124)        # Leichhardt C2 before the C2.2.1.4 heading fix


def test_a_chapter_with_few_links_is_not_judged():
    assert g.judge(4, 0)


def test_enforce_raises_and_the_override_lets_one_named_chapter_through(monkeypatch):
    monkeypatch.setattr(g, "relinkable_count", lambda cur, c, k: 4)
    with pytest.raises(g.AreaLinkLossRefused, match="--allow-area-link-loss waverley/waverley-dcp-2022"):
        g.enforce(None, "waverley", "waverley-dcp-2022", 89)
    assert g.enforce(None, "waverley", "waverley-dcp-2022", 89,
                     frozenset({"waverley/waverley-dcp-2022"})) == 4
