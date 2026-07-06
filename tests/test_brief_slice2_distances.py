"""Slice 2 tests — nearest-feature distances, env detail fields, ANEF honesty.

Break-it scenarios covered (silent wrong results, not crashes):
  1. Mine/contaminated/drinking fetch FAILURE previously rendered a confident
     "No" (False@AUTHORITATIVE) — the WO-2 class. Failure must be NOT_AVAILABLE.
  2. A checked-none ANEF claim was made even when the lookup errored — a
     "no contour" claim off a failed check. Must be NOT_AVAILABLE. (Since
     2026-07-07 the only value source is the live LEP/SEPP-mapped layer;
     anef_zones is quarantined, #686.)
  3. A junk (non-numeric) proximity value must be dropped, never rendered as a
     distance.
  4. contaminated raw = None means genuinely no sites within 500 m — kept
     distinct from a failed register lookup.
"""
from unittest.mock import patch

import services.intelligence_brief as ib
from services.intelligence_brief import ConfidenceLevel, _build_environmental

NA = ConfidenceLevel.NOT_AVAILABLE
AUTH = ConfidenceLevel.AUTHORITATIVE

_CONTROLS = {"zone": "R3", "flood_epi": False}


def _overlays(proximity=None, covered=None, overlays=None):
    return {
        "overlays": overlays or [],
        "covered_layers": covered or ["flood", "biodiversity"],
        "proximity_m": proximity or {},
    }


def _env(**kwargs):
    """_build_environmental with the live ANEF fallbacks failed (deterministic)."""
    def boom(*a, **k):
        raise RuntimeError("down")
    with patch.object(ib, "fetch_anef_zone", boom):
        import services.portal_constraints as pc
        with patch.object(pc, "fetch_anef", boom):
            return _build_environmental(
                kwargs.pop("controls", _CONTROLS),
                kwargs.pop("overlays_data", _overlays()),
                kwargs.pop("heritage_postgis", None),
                lat=-33.86, lng=151.10,
                **kwargs,
            )


# ── nearest-feature distances ────────────────────────────────────────────────

def test_measured_distance_surfaces_on_the_no_row_map():
    env = _env(overlays_data=_overlays(proximity={"flood": 830.4, "biodiversity": 1520}))
    assert env.nearest_features.confidence == AUTH
    assert env.nearest_features.value == {"flood": 830, "biodiversity": 1520}
    assert env.flood_epi.value is False  # the row this decorates


def test_junk_proximity_value_is_dropped_not_rendered_as_distance():
    env = _env(overlays_data=_overlays(proximity={"flood": "nearish", "wetlands": 210.0}))
    assert env.nearest_features.value == {"wetlands": 210}


def test_no_proximity_is_legit_empty_not_failure():
    # Overlays succeeded, nothing to measure: value None + reason None at
    # AUTHORITATIVE (the documented queried-and-empty state — a reason here
    # would mark it as a FAILED fetch and the S1 validator would coerce it).
    env = _env()
    assert env.nearest_features.value is None
    assert env.nearest_features.confidence == AUTH
    assert env.nearest_features.reason is None


def test_overlays_failure_makes_distances_not_available():
    env = _env(overlays_data=_overlays(), overlays_failed=True)
    assert env.nearest_features.confidence == NA


# ── mine / contaminated / drinking: failure is never a confident No ─────────

def test_mine_fetch_failure_is_not_available_never_false():
    env = _env(mine_subsidence_raw=None, mine_failed=True)
    assert env.mine_subsidence.confidence == NA
    assert env.mine_subsidence.value is None
    assert env.mine_subsidence_district.confidence == NA


def test_mine_genuinely_outside_district_is_false_authoritative():
    env = _env(mine_subsidence_raw=None, mine_failed=False)
    assert env.mine_subsidence.confidence == AUTH
    assert env.mine_subsidence.value is False


def test_mine_in_district_carries_the_district_name():
    env = _env(mine_subsidence_raw={"in_district": True, "district_name": "Newcastle", "last_update": None})
    assert env.mine_subsidence.value is True
    assert env.mine_subsidence_district.value == "Newcastle"
    assert env.mine_subsidence_district.confidence == AUTH


def test_contaminated_failure_vs_genuinely_none_are_distinct():
    failed = _env(contaminated_land_raw=None, contam_failed=True)
    assert failed.contaminated_land.confidence == NA
    assert failed.contaminated_land.value is None
    assert failed.contaminated_detail.confidence == NA

    none = _env(contaminated_land_raw=None, contam_failed=False)
    assert none.contaminated_land.confidence == AUTH
    assert none.contaminated_land.value is False
    # Genuinely none: legit-empty (no reason — a reason would mark it failed).
    assert none.contaminated_detail.value is None
    assert none.contaminated_detail.confidence == AUTH
    assert none.contaminated_detail.reason is None


def test_contaminated_detail_carries_the_real_register_shape():
    # The exact shape portal_constraints.fetch_contaminated_land emits.
    raw = {
        "has_notified_sites": True,
        "site_count": 2,
        "nearest_site": {
            "name": "Former Gasworks", "street": "1 Example St", "suburb": "Concord",
            "management_class": "Regulation under the CLM Act", "activity_type": "Gasworks",
            "distance_m": 430,
        },
    }
    env = _env(contaminated_land_raw=raw)
    assert env.contaminated_land.value is True
    d = env.contaminated_detail.value
    assert d["site_count"] == 2
    assert d["nearest_site"]["name"] == "Former Gasworks"
    assert d["nearest_site"]["distance_m"] == 430


def test_drinking_failure_is_not_available():
    env = _env(drinking_water_raw=None, drinking_failed=True)
    assert env.drinking_water_catchment.confidence == NA
    assert env.drinking_water_catchment.value is None


# ── ANEF: numeric level + no claimed "none" off a failed check ───────────────

def test_anef_lookup_failures_are_not_available_not_no_contour():
    env = _env()  # both live ANEF lookups raise in the harness
    assert env.anef.confidence == NA
    assert env.anef.value is None
    assert "did not complete" in env.anef.reason
    assert env.anef_level.confidence == NA


def test_anef_genuinely_checked_none_stays_authoritative():
    import services.portal_constraints as pc
    with patch.object(pc, "fetch_anef", lambda lat, lng: None):
        env = _build_environmental(_CONTROLS, _overlays(), None, lat=-33.86, lng=151.10)
    assert env.anef.confidence == AUTH
    assert "No ANEF contour in the mapped planning layers" in env.anef.value
    assert env.anef_level.value is None
    assert env.anef_level.confidence == AUTH


def test_anef_zones_quarantined_from_brief_field():
    # Data-quality quarantine (#686): the coarse anef_zones digitisations must
    # never feed the brief's ANEF field. Mutation check: re-adding the
    # fetch_anef_zone step to _anef_fields fails this.
    import services.portal_constraints as pc
    def _boom(lat, lng):
        raise AssertionError("anef_zones consulted by the brief's ANEF field")
    with patch.object(ib, "fetch_anef_zone", _boom):
        with patch.object(pc, "fetch_anef", lambda lat, lng: None):
            env = _build_environmental(_CONTROLS, _overlays(), None, lat=-33.94, lng=151.17)
    assert env.anef.source != "anef_zones"


def test_anef_range_string_parses_leading_number_only():
    import services.portal_constraints as pc
    with patch.object(ib, "fetch_anef_zone", lambda lat, lng: None):
        with patch.object(pc, "fetch_anef", lambda lat, lng: {"anef_code": "20-25"}):
            env = _build_environmental(_CONTROLS, _overlays(), None, lat=-33.94, lng=151.17)
    assert env.anef.value == "ANEF contour 20-25"
    assert env.anef_level.value == 20.0


def test_anef_covered_overlay_value_short_circuits():
    ov = _overlays(covered=["anef"], overlays=[{"layer_type": "anef", "value": "30"}])
    env = _build_environmental(_CONTROLS, ov, None, lat=-33.94, lng=151.17)
    assert env.anef.value == "30"
    assert env.anef_level.value == 30.0


# ── golden fixture: the REAL Concord overlay capture round-trips ─────────────

def test_real_concord_overlays_fixture_builds_honestly():
    import json
    from pathlib import Path

    raw = json.load(open(Path(__file__).parent / "fixtures" / "brief_golden" / "env_overlays.json",
                         encoding="utf-8"))["output"]
    env = _env(overlays_data={
        "overlays": raw["overlays"],
        "covered_layers": raw["covered_layers"],
        "proximity_m": raw["proximity_m"],
    })
    # Canada Bay's real coverage: acid sulfate hits; the eco layers aren't
    # ingested, so there is genuinely nothing to measure — None + reason, never
    # a fabricated distance or an empty {} that reads as data.
    assert any(o.layer_type == "acid_sulfate" for o in env.overlays.value)
    assert env.nearest_features.value is None
    assert env.nearest_features.confidence == AUTH  # legit-empty, not a failure
