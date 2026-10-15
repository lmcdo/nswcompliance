"""The not-covered list can only name whole chapters or explicit row ids, and every entry says why."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("h", ROOT / "scripts" / "hide_unmapped_area_rules.py")
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)


def test_every_listed_entry_is_bounded_and_explained():
    for sel in h.selectors():
        sql, params = h.where_for(sel)
        assert params[:2] == [sel["council"], sel["chapter_key"]]
        assert len(sel["reason"].split()) >= 8
        assert isinstance(sel["expect"], int) and sel["expect"] > 0


def test_ids_narrow_the_match():
    sql, params = h.where_for({"council": "woollahra", "chapter_key": "x", "ids": [1, 2]})
    assert "id = ANY(%s)" in sql and params[2] == [1, 2]


def test_a_selector_without_a_chapter_is_refused():
    with pytest.raises(SystemExit):
        h.where_for({"council": "woollahra"})
