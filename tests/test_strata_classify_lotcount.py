"""Bug 4 Stage 1: strata classifier sharpened with the StrataHub lot count.

classify_strata now prefers the strata-plan lot count (authoritative) over the
weak lot-area heuristic, which shrinks the AMBIGUOUS band — the root cause of
both Bug 4 symptoms (silent blank for apartments + wrong house-yield default).

These tests lock:
  * lot count maps to the right four-state class,
  * the count OVERRIDES the lot-area heuristic (fixes the spike case: a
    townhouse complex on a large lot was being called APARTMENT),
  * the area fallback is unchanged when no count is present,
  * _fetch_strata enriches the cadastre dict with the StrataHub count, and never
    fails the brief if StrataHub is unavailable.
"""

import pytest

from services.intelligence_brief import (
    StrataType,
    classify_strata,
    _fetch_strata,
)
from services.strata_lookup import StrataInfo


def _strata(**kw):
    base = {"is_strata": True}
    base.update(kw)
    return base


# --- lot count → four-state class -----------------------------------------

@pytest.mark.parametrize("lot_total,expected", [
    (1, StrataType.DEVELOPMENT),   # single strata lot
    (2, StrataType.DEVELOPMENT),   # duplex
    (3, StrataType.DEVELOPMENT),   # townhouse
    (4, StrataType.DEVELOPMENT),   # townhouse (upper boundary)
    (5, StrataType.APARTMENT),     # small apartment (lower boundary)
    (8, StrataType.APARTMENT),     # small apartment
    (9, StrataType.APARTMENT),     # apartment
    (474, StrataType.APARTMENT),   # large apartment building
])
def test_lot_count_maps_to_class(lot_total, expected):
    assert classify_strata(_strata(lot_total=lot_total), lot_area_m2=None) == expected


# --- lot count OVERRIDES the lot-area heuristic ---------------------------

def test_count_overrides_area_townhouse_on_large_lot():
    """The spike bug: a 3-lot townhouse complex on a 3000m² parent lot was
    classified APARTMENT by the area heuristic. The lot count fixes it."""
    assert classify_strata(
        _strata(lot_total=3), lot_area_m2=3000.0
    ) == StrataType.DEVELOPMENT


def test_count_overrides_area_apartment_on_small_footprint():
    """A 20-lot apartment block on a small parcel would be DEVELOPMENT under the
    <400m² area rule; the count correctly calls it APARTMENT."""
    assert classify_strata(
        _strata(lot_total=20), lot_area_m2=300.0
    ) == StrataType.APARTMENT


# --- area fallback unchanged when no count -------------------------------

@pytest.mark.parametrize("area,expected", [
    (3000.0, StrataType.APARTMENT),
    (350.0, StrataType.DEVELOPMENT),
    (600.0, StrataType.AMBIGUOUS),
])
def test_area_fallback_when_no_lot_count(area, expected):
    assert classify_strata(_strata(), area) == expected


def test_ambiguous_when_no_count_and_no_area():
    assert classify_strata(_strata(), None) == StrataType.AMBIGUOUS


# --- precedence + guards --------------------------------------------------

def test_not_strata_short_circuits():
    assert classify_strata({"is_strata": False}, 600.0) == StrataType.NOT_STRATA


def test_community_title_beats_lot_count():
    """plan_type is a definitive signal checked before the count."""
    assert classify_strata(
        _strata(plan_type="Community", lot_total=50), 2000.0
    ) == StrataType.DEVELOPMENT


@pytest.mark.parametrize("bad", [0, None, True, 1.5, "6"])
def test_invalid_lot_count_falls_through_to_area(bad):
    """0/None/bool/float/str lot counts must not be trusted as a count — fall
    back to the area heuristic (here mid-range → AMBIGUOUS)."""
    assert classify_strata(_strata(lot_total=bad), 600.0) == StrataType.AMBIGUOUS


# --- _fetch_strata enrichment --------------------------------------------

def _strata_info(lot_total):
    return StrataInfo(
        plan_number=1, plan_label="SP1", address="x", suburb="y", lga="z",
        lot_total=lot_total, area_m2=1000.0,
        dwelling_type="apartment" if lot_total > 8 else "townhouse",
    )


def test_fetch_strata_enriches_with_lot_count(monkeypatch):
    import services.intelligence_brief as ib
    import services.strata_lookup as sl
    monkeypatch.setattr(ib, "detect_strata", lambda *a, **k: {"is_strata": True})
    monkeypatch.setattr(sl, "query_strata_at_point", lambda lng, lat: _strata_info(12))
    result = _fetch_strata("1/2 X St", -33.8, 151.1)
    assert result["lot_total"] == 12
    assert result["dwelling_type"] == "apartment"


def test_fetch_strata_skips_strata_hub_when_not_strata(monkeypatch):
    import services.intelligence_brief as ib
    import services.strata_lookup as sl
    monkeypatch.setattr(ib, "detect_strata", lambda *a, **k: {"is_strata": False, "parent_has_strata": False})
    called = {"n": 0}
    def _boom(lng, lat):
        called["n"] += 1
        return _strata_info(99)
    monkeypatch.setattr(sl, "query_strata_at_point", _boom)
    result = _fetch_strata("10 X St", -33.8, 151.1)
    assert "lot_total" not in result
    assert called["n"] == 0


def test_fetch_strata_swallows_strata_hub_failure(monkeypatch):
    import services.intelligence_brief as ib
    import services.strata_lookup as sl
    monkeypatch.setattr(ib, "detect_strata", lambda *a, **k: {"is_strata": True})
    def _raise(lng, lat):
        raise RuntimeError("StrataHub down")
    monkeypatch.setattr(sl, "query_strata_at_point", _raise)
    result = _fetch_strata("1/2 X St", -33.8, 151.1)  # must not raise
    assert result == {"is_strata": True}
