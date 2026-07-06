"""Bug 4: get_cadastral_info must derive plan_type from classsubtype, not the
planlabel prefix alone.

A community-title lot (classsubtype=4, Community Land Development Act) can carry a
DP-style planlabel. The old prefix-only rule ("community" iff planlabel starts CP)
mislabelled such a lot "strata", so classify_strata dropped it into AMBIGUOUS and the
brief hid the capacity card on a developable lot. These tests pin the corrected
derivation and the end-to-end routing (classsubtype=4 -> community -> DEVELOPMENT),
and guard that genuine stacked strata (classsubtype=3) is unchanged and never promoted.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import generate_conveyancing_report as gcr  # noqa: E402
from services.intelligence_brief import classify_strata, StrataType  # noqa: E402


class _FakeResp:
    def __init__(self, features):
        self._features = features

    def raise_for_status(self):
        return None

    def json(self):
        return {"features": self._features}


def _patch_cadastre(monkeypatch, features):
    def _fake_get(url, params=None, timeout=None):
        return _FakeResp(features)

    monkeypatch.setattr(gcr.requests, "get", _fake_get)


def _feat(**attrs):
    return {"attributes": attrs}


def test_community_classsubtype_with_dp_label_is_community(monkeypatch):
    # the live 25 Empire St case: classsubtype 4 community lot carrying a DP label
    _patch_cadastre(monkeypatch, [_feat(planlabel="DP1252132", lotnumber="63", classsubtype=4, hasstratum=2)])
    out = gcr.get_cadastral_info(-33.88, 151.13)
    assert out["is_strata"] is True
    assert out["plan_type"] == "community"


def test_true_strata_classsubtype_3_stays_strata(monkeypatch):
    # genuine stacked strata must NOT be promoted to community/development
    _patch_cadastre(monkeypatch, [_feat(planlabel="SP1786", lotnumber="1", classsubtype=3, hasstratum=2)])
    out = gcr.get_cadastral_info(-33.88, 151.13)
    assert out["is_strata"] is True
    assert out["plan_type"] == "strata"


def test_cp_planlabel_prefix_still_community(monkeypatch):
    # the prefix path keeps working when classsubtype is absent from the dataset
    _patch_cadastre(monkeypatch, [_feat(planlabel="CP12345", lotnumber="1", classsubtype=None, hasstratum=2)])
    out = gcr.get_cadastral_info(-33.88, 151.13)
    assert out["plan_type"] == "community"


def test_sp_planlabel_prefix_is_strata(monkeypatch):
    _patch_cadastre(monkeypatch, [_feat(planlabel="SP9999", lotnumber="1", classsubtype=None, hasstratum=2)])
    out = gcr.get_cadastral_info(-33.88, 151.13)
    assert out["plan_type"] == "strata"


def test_community_lot_routes_to_development_end_to_end(monkeypatch):
    # the whole point: community classification un-hides the capacity card
    _patch_cadastre(monkeypatch, [_feat(planlabel="DP1252132", lotnumber="63", classsubtype=4, hasstratum=2)])
    out = gcr.get_cadastral_info(-33.88, 151.13)
    routed = classify_strata({"is_strata": True, "plan_type": out["plan_type"]}, lot_area_m2=600.0)
    assert routed == StrataType.DEVELOPMENT


def test_genuine_strata_without_count_stays_out_of_development(monkeypatch):
    # the failure mode: StrataHub lot count unavailable. classsubtype 3 must still
    # NOT route to DEVELOPMENT off the area heuristic alone (stays AMBIGUOUS).
    _patch_cadastre(monkeypatch, [_feat(planlabel="SP1786", lotnumber="1", classsubtype=3, hasstratum=2)])
    out = gcr.get_cadastral_info(-33.88, 151.13)
    routed = classify_strata({"is_strata": True, "plan_type": out["plan_type"]}, lot_area_m2=600.0)
    assert routed == StrataType.AMBIGUOUS


# ---------------------------------------------------------------------------
# Containment vs 20m fallback buffer (38 Park Rd Bowral regression)
#
# The always-20m buffer captured a NEIGHBOUR's strata scheme and reported an
# adjacent Torrens lot as strata. Point-in-polygon must decide; the buffer is
# a fallback for geocodes that hit no lot, and its SP hits are not authoritative.
# ---------------------------------------------------------------------------

_BOWRAL_TORRENS = _feat(planlabel="DP702113", lotnumber="12", classsubtype=1, hasstratum=1)
_NEIGHBOUR_SP = _feat(planlabel="SP105471", lotnumber=None, classsubtype=3, hasstratum=2)


def _patch_cadastre_two_stage(monkeypatch, point_features, buffer_features):
    """Point-in-polygon query has no 'distance' param; the fallback buffer does."""
    def _fake_get(url, params=None, timeout=None):
        if params and "distance" in params:
            return _FakeResp(buffer_features)
        return _FakeResp(point_features)

    monkeypatch.setattr(gcr.requests, "get", _fake_get)


def test_torrens_lot_ignores_neighbouring_sp_in_buffer(monkeypatch):
    # the live 38 Park Rd Bowral case: point is inside the DP lot; the
    # neighbour's SP only appears in the buffer query, which must not run.
    _patch_cadastre_two_stage(monkeypatch, [_BOWRAL_TORRENS], [_BOWRAL_TORRENS, _NEIGHBOUR_SP])
    out = gcr.get_cadastral_info(-34.488, 150.430)
    assert out["is_strata"] is False
    assert out["plan_label"] == "DP702113"
    assert out["containment"] is True

    strata = gcr.detect_strata("38 Park Rd, Bowral NSW 2576", -34.488, 150.430)
    assert strata["is_strata"] is False
    assert strata["strata_plan"] is None


def test_contained_sp_lot_still_confirms_strata(monkeypatch):
    # genuine strata: SP polygon contains the point — unchanged behaviour,
    # confirmed even without a unit-style address.
    _patch_cadastre_two_stage(monkeypatch, [_NEIGHBOUR_SP], [])
    strata = gcr.detect_strata("1 Example St, Hurstville NSW", -33.96, 151.10)
    assert strata["is_strata"] is True
    assert strata["strata_plan"] == "SP105471"
    assert strata["source"] == "cadastre"


def test_buffer_fallback_sp_alone_is_ambiguous_not_strata(monkeypatch):
    # geocode missed every lot; an SP within 20m without a unit-style address
    # may be the neighbour's scheme — must NOT confirm strata.
    _patch_cadastre_two_stage(monkeypatch, [], [_BOWRAL_TORRENS, _NEIGHBOUR_SP])
    strata = gcr.detect_strata("38 Park Rd, Bowral NSW 2576", -34.488, 150.430)
    assert strata["is_strata"] is False
    assert strata["parent_has_strata"] is True


def test_buffer_fallback_sp_plus_unit_address_confirms(monkeypatch):
    # geocode missed every lot, but the unit-style address corroborates the
    # nearby SP — combined signal confirms.
    _patch_cadastre_two_stage(monkeypatch, [], [_NEIGHBOUR_SP])
    strata = gcr.detect_strata("5/38 Park Rd, Bowral NSW 2576", -34.488, 150.430)
    assert strata["is_strata"] is True
    assert strata["source"] == "cadastre+address"


def test_no_cadastre_result_falls_back_to_address_heuristic(monkeypatch):
    # both queries empty: unit-prefix address still flags likely strata
    _patch_cadastre_two_stage(monkeypatch, [], [])
    strata = gcr.detect_strata("5/38 Park Rd, Bowral NSW 2576", -34.488, 150.430)
    assert strata["is_strata"] is True
    assert strata["source"] == "address_heuristic"

    strata = gcr.detect_strata("38 Park Rd, Bowral NSW 2576", -34.488, 150.430)
    assert strata["is_strata"] is False


# ---------------------------------------------------------------------------
# Jurisdictional overlay filter (false statewide "coastal" hit)
# ---------------------------------------------------------------------------

def test_land_application_row_is_dropped():
    rows = [
        {"layer_type": "coastal_land_application", "value": "Land Application", "instrument": "SEPP R&H 2021", "lga": None},
        {"layer_type": "flood", "value": "Flood Planning Area", "instrument": "LEP", "lga": "WINGECARRIBEE"},
    ]
    out = gcr._drop_jurisdictional_overlays(rows)
    assert [o["layer_type"] for o in out] == ["flood"]


def test_subject_land_row_is_kept():
    rows = [{"layer_type": "coastal_land_application", "value": "Subject Land", "instrument": "SEPP R&H 2021", "lga": None}]
    assert gcr._drop_jurisdictional_overlays(rows) == rows


def test_genuine_coastal_hazard_layers_untouched():
    rows = [
        {"layer_type": "coastal_wetlands", "value": "Proximity", "instrument": "SEPP R&H 2021", "lga": None},
        {"layer_type": "coastal_environment_area", "value": None, "instrument": "SEPP R&H 2021", "lga": None},
    ]
    assert gcr._drop_jurisdictional_overlays(rows) == rows


def test_null_value_land_application_is_dropped():
    rows = [{"layer_type": "coastal_land_application", "value": None, "instrument": "SEPP R&H 2021", "lga": None}]
    assert gcr._drop_jurisdictional_overlays(rows) == []
