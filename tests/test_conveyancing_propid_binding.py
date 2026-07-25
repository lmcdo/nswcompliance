"""prop_id, coordinates and lot geometry must all come from the ONE address.

Regression for the conveyancing adversarial sweep finding #1: the report accepted a
caller-supplied (prop_id, lat, lng) triple unverified, so LEP controls / valuation
(keyed by prop_id) and overlays / strata / nearby DAs (keyed by lat,lng) could
describe two different properties under a single address label. _resolve_property
now derives all four values from resolve_address(req.address) and never trusts the
caller's triple. Also covers the lot_wkt-None point-query gap (finding #3): the old
fast path left lot_wkt None, so overlay point-queries missed edge-only layers.
"""

import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "services"))
sys.path.insert(0, str(_ROOT / "scripts"))
sys.path.insert(0, str(_ROOT))

import conveyancing  # noqa: E402


def _req(**kw):
    address = kw.pop("address", "1 Test St, Sydney NSW 2000")
    return conveyancing.ConveyancingRequest(address=address, **kw)


class TestResolveProperty:
    def test_all_values_from_one_address(self, monkeypatch):
        monkeypatch.setattr(
            conveyancing, "resolve_address",
            lambda a: (111, -33.87, 151.21, "POLYGON((0 0))"),
        )
        pid, lat, lng, wkt = conveyancing._resolve_property(_req())
        assert pid == 111
        assert (lat, lng) == (-33.87, 151.21)
        assert wkt == "POLYGON((0 0))"

    def test_caller_triple_is_ignored(self, monkeypatch):
        # Caller passes a DIFFERENT property's prop_id and coords; the resolved
        # values (bound to the address) must win — never a mixed report.
        monkeypatch.setattr(
            conveyancing, "resolve_address",
            lambda a: (111, -33.87, 151.21, "POLYGON((A))"),
        )
        pid, lat, lng, wkt = conveyancing._resolve_property(
            _req(prop_id="999", lat=-30.0, lng=145.0)
        )
        assert pid == 111  # not the caller's 999
        assert (lat, lng) == (-33.87, 151.21)  # not the caller's coords
        assert wkt == "POLYGON((A))"

    def test_lot_wkt_bound_even_when_caller_had_none(self, monkeypatch):
        # The old fast path left lot_wkt None (overlay point-query gap); resolving
        # from the address binds the parcel polygon.
        monkeypatch.setattr(
            conveyancing, "resolve_address",
            lambda a: (111, -33.87, 151.21, "POLYGON((edge))"),
        )
        _, _, _, wkt = conveyancing._resolve_property(
            _req(prop_id="111", lat=-33.87, lng=151.21)
        )
        assert wkt == "POLYGON((edge))"

    def test_unresolvable_address_raises_422(self, monkeypatch):
        # GATE-0 / no parcel → resolve_address returns all None → fail closed,
        # even though the caller supplied a plausible triple.
        monkeypatch.setattr(
            conveyancing, "resolve_address", lambda a: (None, None, None, None)
        )
        with pytest.raises(HTTPException) as ei:
            conveyancing._resolve_property(_req(prop_id="999", lat=-30.0, lng=145.0))
        assert ei.value.status_code == 422

    def test_operational_failure_raises_503_not_422(self, monkeypatch):
        # An exception from resolve_address is an outage (Portal unreachable), not
        # an invalid address — surface a retryable 503, never a 422 that blames the
        # user's valid address. (A genuine not-found returns None -> 422 above.)
        def _boom(a):
            raise RuntimeError("portal down")

        monkeypatch.setattr(conveyancing, "resolve_address", _boom)
        with pytest.raises(HTTPException) as ei:
            conveyancing._resolve_property(_req())
        assert ei.value.status_code == 503

    def test_matching_caller_prop_id_passes_through(self, monkeypatch):
        monkeypatch.setattr(
            conveyancing, "resolve_address",
            lambda a: (111, -33.87, 151.21, None),
        )
        pid, _, _, _ = conveyancing._resolve_property(_req(prop_id="111"))
        assert pid == 111
