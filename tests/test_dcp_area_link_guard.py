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
