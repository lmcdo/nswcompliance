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
