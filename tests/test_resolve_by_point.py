"""Coordinate-first parcel resolution (resolve_propid_by_point) + the
_resolve_address priority wiring.

The contract under test is the safeguard: the coordinate path resolves a propId
ONLY when the cadastre address passes the same parcel-identity cross-check, so a
pin that lands on a neighbouring parcel is rejected (GATE-0 preserved), not
served as the wrong parcel.
"""
import pytest

# Importing the brief first runs its sys.path setup so the bare module name works.
import services.intelligence_brief as ib  # noqa: F401,E402
import generate_conveyancing_report as gcr  # noqa: E402
from services.intelligence_brief import IntelligenceBriefRequest, _resolve_address  # noqa: E402


class _FakeResp:
    def __init__(self, payload):
        self._p = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._p


def _feat(propid, address):
    return {"attributes": {"propid": propid, "address": address}}


def _patch_point(monkeypatch, features):
    monkeypatch.setattr(gcr.requests, "get", lambda *a, **k: _FakeResp({"features": features}))
    monkeypatch.setattr(gcr, "_lot_centroid_wkt", lambda pid: (-33.8, 151.1, "POLYGON((0 0))"))


# --- resolve_propid_by_point ------------------------------------------------

def test_point_match_resolves(monkeypatch):
    _patch_point(monkeypatch, [_feat(1456609, "14 STANLEY STREET CONCORD")])
    out = gcr.resolve_propid_by_point(-33.86, 151.10, "14 Stanley Street, Concord NSW 2137")
    assert out is not None and out[0] == 1456609
    assert out[3].startswith("POLYGON")


def test_wrong_parcel_is_rejected(monkeypatch):
    # The pin landed on a DIFFERENT parcel — address mismatch — so GATE-0 rejects
    # it and the resolver returns None (caller falls back to text).
    _patch_point(monkeypatch, [_feat(999, "3 NORTHWOOD STREET STANHOPE GARDENS")])
    assert gcr.resolve_propid_by_point(
        -33.7, 150.9, "22 Northwood Street, Stanhope Gardens NSW 2768") is None


def test_strata_block_collapses_to_one_propid(monkeypatch):
    # An apartment/strata block returns many address points sharing one propId.
    feats = [
        _feat(4241915, "1 TREACY STREET HURSTVILLE"),
        _feat(4241915, "406/1 TREACY STREET HURSTVILLE"),
        _feat(4241915, "506/1 TREACY STREET HURSTVILLE"),
    ]
    _patch_point(monkeypatch, feats)
    out = gcr.resolve_propid_by_point(-33.96, 151.10, "5/1 Treacy Street, Hurstville NSW 2220")
    assert out is not None and out[0] == 4241915


def test_unit_request_matches_base_property(monkeypatch):
    # "2/45 Alt St" — the unit prefix is stripped both sides, so it matches the
    # base-property cadastre address. (This was a text-path false-close.)
    _patch_point(monkeypatch, [_feat(1291953, "45 ALT STREET ASHFIELD")])
    out = gcr.resolve_propid_by_point(-33.88, 151.12, "2/45 Alt Street, Ashfield NSW 2131")
    assert out is not None and out[0] == 1291953


def test_ambiguous_distinct_propids_returns_none(monkeypatch):
    # Two parcels match the address tokens but have different propIds -> ambiguous.
    _patch_point(monkeypatch, [
        _feat(11, "10 ORPINGTON STREET ASHFIELD"),
        _feat(22, "10 ORPINGTON STREET ASHFIELD"),
    ])
    assert gcr.resolve_propid_by_point(
        -33.88, 151.12, "10 Orpington Street, Ashfield NSW 2131") is None


def test_no_features_returns_none(monkeypatch):
    _patch_point(monkeypatch, [])
    assert gcr.resolve_propid_by_point(-33.8, 151.1, "1 Nowhere Street, Nullville NSW 2000") is None


def test_endpoint_error_returns_none(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(gcr.requests, "get", _boom)
    assert gcr.resolve_propid_by_point(-33.8, 151.1, "14 Stanley Street, Concord NSW 2137") is None


# --- _resolve_address priority ----------------------------------------------

def test_coord_present_uses_point_not_text(monkeypatch):
    monkeypatch.setattr(ib, "resolve_propid_by_point", lambda lat, lng, addr: (123, lat, lng, "WKT"))

    def _no_text(addr):
        raise AssertionError("text resolver must not run when the point path succeeds")

    monkeypatch.setattr(ib, "resolve_address", _no_text)
    req = IntelligenceBriefRequest(address="14 Stanley Street, Concord NSW 2137", lat=-33.86, lng=151.10)
    assert _resolve_address(req)[0] == 123


def test_point_miss_falls_back_to_text(monkeypatch):
    monkeypatch.setattr(ib, "resolve_propid_by_point", lambda lat, lng, addr: None)
    monkeypatch.setattr(ib, "resolve_address", lambda addr: (456, -33.8, 151.1, "WKT"))
    req = IntelligenceBriefRequest(address="14 Stanley Street, Concord NSW 2137", lat=-33.86, lng=151.10)
    assert _resolve_address(req)[0] == 456


def test_no_coord_uses_text_and_skips_point(monkeypatch):
    called = {"point": 0}

    def _count(*a, **k):
        called["point"] += 1
        return None

    monkeypatch.setattr(ib, "resolve_propid_by_point", _count)
    monkeypatch.setattr(ib, "resolve_address", lambda addr: (789, -33.8, 151.1, "WKT"))
    req = IntelligenceBriefRequest(address="14 Stanley Street, Concord NSW 2137")
    out = _resolve_address(req)
    assert out[0] == 789 and called["point"] == 0
