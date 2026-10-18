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
    monkeypatch.setattr(g, "relinkable_count", lambda cur, c, k: g.Linked(4, 4))
    with pytest.raises(g.AreaLinkLossRefused, match="--allow-area-link-loss waverley/waverley-dcp-2022"):
        g.enforce(None, "waverley", "waverley-dcp-2022", g.Linked(89, 0))
    assert g.enforce(None, "waverley", "waverley-dcp-2022", g.Linked(89, 0),
                     frozenset({"waverley/waverley-dcp-2022"})) == g.Linked(4, 4)


def test_both_publish_paths_run_the_guard_before_they_commit():
    """PR #1285 review: the direct-to-live path (dcp_extract_changed) published without it."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "scripts"
    for name in ("dcp_commit_approved.py", "dcp_extract_changed.py"):
        src = (root / name).read_text(encoding="utf-8")
        assert "area_links.linked_count(cur, council, chapter_key)" in src, name
        guard = src.index("area_links.enforce(cur, council, chapter_key")
        assert "conn.commit()" in src[guard:guard + 400] or name == "dcp_commit_approved.py", name


class _Cur:
    """Records UPDATEs; returns the canned SELECT rows once."""

    def __init__(self, rows):
        self.rows, self.updates = rows, []

    def execute(self, sql, params=None):
        if sql.lstrip().startswith("UPDATE"):
            self.updates.append(params)

    def fetchall(self):
        out, self.rows = self.rows, []
        return out


class _Tagger:
    def tag(self, doc, text):
        return ("precinct", "E6" if "Bondi" in text else None, None)


def test_fill_parts_gives_new_rows_the_part_enrichment_would():
    """2026-10-15: inside the publish no new Waverley row had a Part yet, so the guard predicted 0 of 126 links
    while the published version carries 1,028 Part E rows. The Part is filled first, with the same tagger."""
    cur = _Cur([(1, "d", "Bondi Junction controls ..."), (2, "d", "General controls ...")])
    assert g.fill_parts(cur, "waverley", "waverley-dcp-2022", tagger=_Tagger()) == 1
    assert cur.updates == [("E6", 1)]          # a row the tagger gives no Part is left alone


def test_both_publish_paths_fill_the_part_before_the_guard():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "scripts"
    for name in ("dcp_commit_approved.py", "dcp_extract_changed.py"):
        src = (root / name).read_text(encoding="utf-8")
        fill = src.index("area_links.fill_parts(cur, council, chapter_key)")
        assert fill < src.index("area_links.enforce(cur, council, chapter_key"), name


class _ZoneTagger:
    """Stands in for ApplicabilityTagger.tag_with_provenance."""

    def tag_with_provenance(self, text, doc, part=None, pdf_page=None):
        if "config" in text:
            return ["R2", "R3"], ["ALL"], {"zone_source": "config_specific"}  # noqa: zone-codes (test fixture)
        if "prose" in text:
            return ["R4"], ["ALL"], {"zone_source": "text_regex"}
        return ["ALL"], ["ALL"], {"zone_source": "config_all"}


def test_config_zones_count_and_zones_read_from_prose_do_not():
    """Campbelltown Part 3, 2026-10-18: enrichment re-applied its zones from the chapter config to all 504 rules, but the
    guard predicted only precinct/gate links and refused. A zone read from the rule's own words is not counted."""
    cur = _Cur([(1, "d", "config row", None, 3), (2, "d", "prose row", None, 3), (3, "d", "everywhere", None, 4)])
    assert g.config_zoned_ids(cur, "campbelltown", "part3", tagger=_ZoneTagger()) == {1}


def test_zone_only_links_re_applied_by_config_pass(monkeypatch):
    monkeypatch.setattr(g, "relinkable_ids", lambda cur, c, k: set())
    monkeypatch.setattr(g, "config_zoned_ids", lambda cur, c, k: set(range(504)))
    assert g.enforce(None, "campbelltown", "part3", g.Linked(0, 193)) == g.Linked(0, 504)


def test_config_zones_cannot_hide_lost_precinct_links(monkeypatch):
    """The two kinds are judged apart: a chapter that loses its precinct links is refused even when every row will
    get config zones, so the zone count can never stand in for the precincts."""
    monkeypatch.setattr(g, "relinkable_ids", lambda cur, c, k: set(range(10)))
    monkeypatch.setattr(g, "config_zoned_ids", lambda cur, c, k: set(range(500)))
    with pytest.raises(g.AreaLinkLossRefused, match="100 rules linked to a precinct or marker"):
        g.enforce(None, "c", "k", g.Linked(100, 50))


def test_lost_zone_only_links_are_still_refused(monkeypatch):
    monkeypatch.setattr(g, "relinkable_ids", lambda cur, c, k: set())
    monkeypatch.setattr(g, "config_zoned_ids", lambda cur, c, k: set(range(20)))
    with pytest.raises(g.AreaLinkLossRefused):
        g.enforce(None, "c", "k", g.Linked(0, 193))
