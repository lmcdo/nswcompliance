"""The conveyancing report's flood answer comes from services/flood_planning.py.

Before 2026-10-28 the report counted any row in the 'flood' layer (PMF lines,
'Other', 'Transitional Land') as a flood planning hit, and its summary said
"No ... flood ... overlays identified" with no check that the council's map is
held. A failed lookup must read unknown, never a clean "no".
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
gcr = pytest.importorskip("generate_conveyancing_report")


def test_a_failed_lookup_is_unknown_never_no(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("db down")
    monkeypatch.setattr(gcr.psycopg2, "connect", boom)
    got = gcr.get_flood_planning_status(-33.86, 151.10)
    assert got["value"] is None
    assert "could not be checked" in got["reason"]


def test_the_report_reads_the_one_producer(monkeypatch):
    import flood_planning
    seen = {}
    monkeypatch.setattr(flood_planning, "flood_planning_status",
                        lambda lat, lng, conn: seen.setdefault("v", {"value": False, "reason": "r"}))
    monkeypatch.setattr(gcr.psycopg2, "connect", lambda *a, **k: type("C", (), {"close": lambda self: None})())
    assert gcr.get_flood_planning_status(-28.86, 153.56)["value"] is False
    assert seen, "the report did not call services/flood_planning.py"


def test_a_lot_outline_hit_wins_over_a_point_no():
    """A big lot partly on the map, address point off it: the report must say yes."""
    got = gcr.apply_lot_flood_hit({"value": False, "reason": "not on the council's flood planning map"},
                                  [{"layer_type": "flood", "value": "Flood Planning Area"}])
    assert got["value"] is True and "lot outline" in got["reason"]


def test_an_extreme_only_lot_row_does_not_make_a_yes():
    got = gcr.apply_lot_flood_hit({"value": False, "reason": "r"}, [{"layer_type": "flood", "value": "PMF"}])
    assert got["value"] is False


def test_no_lot_rows_keeps_the_point_answer():
    assert gcr.apply_lot_flood_hit({"value": None, "reason": "r"}, [])["value"] is None
