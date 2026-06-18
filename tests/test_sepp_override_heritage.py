"""GATE-2 — a SEPP height/FSR override must be eligible and must not fire on
heritage land.

The Low/Mid-Rise Housing reforms (the SEPP bonuses) exclude heritage items and
Heritage Conservation Areas; the engine previously applied a 7m->9.5m bonus on
the Haberfield HCA. _detect_sepp_lep_overrides now honours std.eligible and is
suppressed on heritage land.
"""
from services.intelligence_brief import _detect_sepp_lep_overrides, _is_heritage_land
from services.constraint_models import SEPPStandard


def _std(eligible=True, max_height_m=9.5, max_fsr=None, dev_type="residential_flat_building"):
    return SEPPStandard(dev_type=dev_type, eligible=eligible, max_height_m=max_height_m, max_fsr=max_fsr)


# --- override fires only when valid -----------------------------------------

def test_eligible_height_bonus_overrides_lep_when_not_heritage():
    o = _detect_sepp_lep_overrides([_std(max_height_m=9.5)], lep_height_m=7.0, lep_fsr=None, is_heritage=False)
    assert len(o) == 1
    assert o[0].control == "height" and o[0].sepp_value == 9.5 and o[0].lep_value == 7.0


def test_fsr_bonus_override_when_more_generous():
    o = _detect_sepp_lep_overrides([_std(max_height_m=None, max_fsr=1.0)], lep_height_m=None, lep_fsr=0.5)
    assert len(o) == 1 and o[0].control == "fsr"


def test_no_override_when_sepp_not_strictly_greater():
    o = _detect_sepp_lep_overrides([_std(max_height_m=7.0)], lep_height_m=7.0, lep_fsr=None)
    assert o == []


# --- GATE-2 guards ----------------------------------------------------------

def test_heritage_suppresses_override():
    """The Haberfield case: a 7m->9.5m bonus must NOT fire on HCA land."""
    o = _detect_sepp_lep_overrides([_std(max_height_m=9.5)], lep_height_m=7.0, lep_fsr=None, is_heritage=True)
    assert o == []


def test_ineligible_standard_does_not_override():
    o = _detect_sepp_lep_overrides([_std(eligible=False, max_height_m=9.5)], lep_height_m=7.0, lep_fsr=None)
    assert o == []


# --- heritage detection -----------------------------------------------------

def test_is_heritage_from_portal_items():
    assert _is_heritage_land({"heritage_items": ["Haberfield Heritage Conservation Area"]}, None) is True


def test_is_heritage_from_postgis_has_heritage():
    assert _is_heritage_land({}, {"has_heritage": True}) is True


def test_not_heritage_when_neither():
    assert _is_heritage_land({}, {"has_heritage": False}) is False
    assert _is_heritage_land({}, None) is False
    assert _is_heritage_land({"heritage_items": []}, None) is False
