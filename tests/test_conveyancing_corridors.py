"""Golden-sentence tests — conveyancing contributions (Slice A) and
corridors / land-reservation-acquisition (Slice B) sections.

Fixtures are recorded live NSW responses (2026-07-07), never invented:
  concord_cp.json           /cp propId 1456609 — 2 plans + HPC block
  bowral_cp.json            /cp propId 1119594 — 9 plans, empty icdp
  burwood_lra_layer24.json  LRA layer 24, lot polygon of 70 Fitzroy St Burwood
                            (propId 1392038) — Local Road (R2), AUTHORITY Council
  bowral_lra_layer24.json   same query for 38 Park Rd Bowral — 0 features
  goulburn_warn.json        /warn propId 448547 — electrical infrastructure
  burwood_rail_*.json       SydneyTrain_ISEPP layers — 0 features

Pure-logic: requests / arcgis client are monkeypatched, no live HTTP.
"""

import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))
sys.path.insert(0, str(_ROOT / "services"))
sys.path.insert(0, str(_ROOT))

import portal_constraints as pc  # noqa: E402
from generate_conveyancing_report import (  # noqa: E402
    _CORRIDORS_ALL_CLEAR,
    build_contributions_lines,
    build_corridors_lines,
)

FIXTURES = Path(__file__).parent / "fixtures" / "corridors_contributions"


def _fx(name: str):
    with open(FIXTURES / name, encoding="utf-8") as fh:
        return json.load(fh)


class _Resp:
    """Minimal requests.Response stand-in for recorded payloads."""

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


# 70 Fitzroy St Burwood lot polygon is recorded in EPSG:3857 portal rings; the
# pipeline hands the fetcher a 4326 WKT — this small square inside the lot is
# only used to exercise the WKT→rings path, the LAYER RESPONSES are recorded.
_BURWOOD_WKT = (
    "POLYGON((151.1066 -33.8823, 151.1068 -33.8823, "
    "151.1068 -33.8822, 151.1066 -33.8822, 151.1066 -33.8823))"
)


# ---------------------------------------------------------------------------
# Slice A — fetch_contributions_plans three-state semantics
# ---------------------------------------------------------------------------

class TestFetchContributions:
    def _patch(self, monkeypatch, payload=None, exc=None):
        def _get(url, **kwargs):
            if exc:
                raise exc
            return _Resp(payload)
        monkeypatch.setattr(pc.requests, "get", _get)

    def test_concord_fixture_found_plans_verbatim(self, monkeypatch):
        self._patch(monkeypatch, _fx("concord_cp.json"))
        out = pc.fetch_contributions_plans(1456609)
        assert out["status"] == "found"
        names = [p["plan_name"] for p in out["plans"]]
        assert (
            "City of Canada Bay Local Infrastructure Contributions Plan "
            "- Contributions Rates Dec 2024"
        ) in names
        assert out["lga_name"] == "CANADA BAY"
        assert out["hpc"] is not None
        assert out["hpc"]["component"] == "BHPC"
        assert out["hpc"]["commenced_date"]  # value carried from the data

    def test_bowral_fixture_found_without_hpc(self, monkeypatch):
        self._patch(monkeypatch, _fx("bowral_cp.json"))
        out = pc.fetch_contributions_plans(1119594)
        assert out["status"] == "found"
        assert len(out["plans"]) == 9
        assert out["hpc"] is None

    def test_plan_urls_carried_verbatim(self, monkeypatch):
        self._patch(monkeypatch, _fx("concord_cp.json"))
        out = pc.fetch_contributions_plans(1456609)
        assert all(p["plan_url"] for p in out["plans"])

    def test_empty_blocks_are_queried_empty(self, monkeypatch):
        self._patch(monkeypatch, {"cp": {"results": []}, "icdp": {"results": []}})
        out = pc.fetch_contributions_plans(1)
        assert out["status"] == "empty"
        assert out["plans"] == []

    def test_bare_dict_is_failed_not_empty(self, monkeypatch):
        """Mutation check: deleting the missing-blocks raise in _fetch_cp_payload
        turns a transport-degraded {} into 'no plans' — this must fail instead."""
        self._patch(monkeypatch, {})
        assert pc.fetch_contributions_plans(1)["status"] == "failed"

    def test_non_dict_response_is_failed(self, monkeypatch):
        self._patch(monkeypatch, [])
        assert pc.fetch_contributions_plans(1)["status"] == "failed"

    def test_transport_exception_is_failed(self, monkeypatch):
        self._patch(monkeypatch, exc=RuntimeError("timeout"))
        assert pc.fetch_contributions_plans(1)["status"] == "failed"


# ---------------------------------------------------------------------------
# Slice B — fetch_corridors_reservations three-state per sub-check
# ---------------------------------------------------------------------------

def _patch_layers(monkeypatch, lra=None, rail1=None, rail2=None, warn=None,
                  lra_exc=None, rail_exc=None, warn_exc=None):
    """Route the two transport seams to recorded payloads (or exceptions)."""
    import services.arcgis_client as ac

    def _arcgis(url, params, timeout=None):
        if "MapServer/24" in url:
            if lra_exc:
                raise lra_exc
            return lra if lra is not None else {}
        if rail_exc:
            raise rail_exc
        if "SydneyTrain_ISEPP/MapServer/1" in url:
            return rail1 if rail1 is not None else {}
        if "SydneyTrain_ISEPP/MapServer/2" in url:
            return rail2 if rail2 is not None else {}
        raise AssertionError(f"unexpected layer url {url}")

    def _get(url, **kwargs):
        if warn_exc:
            raise warn_exc
        return _Resp(warn if warn is not None else [])

    monkeypatch.setattr(ac, "arcgis_get_with_retry", _arcgis)
    monkeypatch.setattr(pc.requests, "get", _get)


_EMPTY_FEATURES = {"features": []}


class TestFetchCorridors:
    def test_burwood_lra_positive_fixture(self, monkeypatch):
        _patch_layers(
            monkeypatch,
            lra=_fx("burwood_lra_layer24.json"),
            rail1=_fx("burwood_rail_corridor_l1.json"),
            rail2=_fx("burwood_rail_infra_l2.json"),
            warn=_fx("burwood_warn.json"),
        )
        out = pc.fetch_corridors_reservations(
            -33.8823, 151.1067, lot_wkt=_BURWOOD_WKT, prop_id=1392038,
        )
        assert out["query_basis"] == "lot_polygon"
        assert out["lra"]["status"] == "found"
        item = out["lra"]["items"][0]
        assert item["LABEL"] == "Local Road (R2)"
        assert item["AUTHORITY"] == "Council"
        assert item["EPI_NAME"] == "Burwood Local Environmental Plan 2012"
        # CURRENCY_DATE 1487289600000 ms — date derived from the data itself
        assert item["currency_date"] == "2017-02-17"
        assert out["data_currency"] == "2017-02-17"
        assert out["rail_corridors"]["status"] == "empty"
        assert out["warnings"]["status"] == "empty"

    def test_bowral_all_empty_fixture(self, monkeypatch):
        _patch_layers(
            monkeypatch,
            lra=_fx("bowral_lra_layer24.json"),
            rail1=_fx("bowral_rail_corridor_l1.json"),
            rail2=_fx("bowral_rail_infra_l2.json"),
            warn=_fx("bowral_warn.json"),
        )
        out = pc.fetch_corridors_reservations(-34.4818, 150.4110, prop_id=1119594)
        assert out["lra"]["status"] == "empty"
        assert out["rail_corridors"]["status"] == "empty"
        assert out["warnings"]["status"] == "empty"
        assert out["data_currency"] is None

    def test_arcgis_error_body_is_failed_not_empty(self, monkeypatch):
        """Mutation check: the silent-zero trap. arcgis_get_with_retry returns {}
        on an HTTP-200 ArcGIS error body — removing the missing-`features` raise
        would record 'empty' (renders as checked-clean). Must be 'failed'."""
        _patch_layers(monkeypatch, lra={}, rail1=_EMPTY_FEATURES,
                      rail2=_EMPTY_FEATURES, warn=[])
        out = pc.fetch_corridors_reservations(-33.88, 151.10, prop_id=1)
        assert out["lra"]["status"] == "failed"
        assert out["rail_corridors"]["status"] == "empty"

    def test_rail_failure_isolated_from_lra(self, monkeypatch):
        _patch_layers(monkeypatch, lra=_fx("burwood_lra_layer24.json"),
                      rail_exc=RuntimeError("boom"), warn=[])
        out = pc.fetch_corridors_reservations(
            -33.8823, 151.1067, lot_wkt=_BURWOOD_WKT, prop_id=1,
        )
        assert out["lra"]["status"] == "found"
        assert out["rail_corridors"]["status"] == "failed"

    def test_warn_failure_is_failed(self, monkeypatch):
        _patch_layers(monkeypatch, lra=_EMPTY_FEATURES, rail1=_EMPTY_FEATURES,
                      rail2=_EMPTY_FEATURES, warn_exc=RuntimeError("503"))
        out = pc.fetch_corridors_reservations(-33.88, 151.10, prop_id=1)
        assert out["warnings"]["status"] == "failed"

    def test_no_propid_warnings_not_assessed(self, monkeypatch):
        _patch_layers(monkeypatch, lra=_EMPTY_FEATURES, rail1=_EMPTY_FEATURES,
                      rail2=_EMPTY_FEATURES)
        out = pc.fetch_corridors_reservations(-33.88, 151.10, prop_id=None)
        assert out["warnings"]["status"] == "failed"

    def test_no_wkt_falls_back_to_centroid_basis(self, monkeypatch):
        _patch_layers(monkeypatch, lra=_EMPTY_FEATURES, rail1=_EMPTY_FEATURES,
                      rail2=_EMPTY_FEATURES, warn=[])
        out = pc.fetch_corridors_reservations(-33.88, 151.10, prop_id=1)
        assert out["query_basis"] == "centroid_30m"

    def test_unparseable_wkt_falls_back_to_centroid_basis(self, monkeypatch):
        _patch_layers(monkeypatch, lra=_EMPTY_FEATURES, rail1=_EMPTY_FEATURES,
                      rail2=_EMPTY_FEATURES, warn=[])
        out = pc.fetch_corridors_reservations(
            -33.88, 151.10, lot_wkt="POLYGON((garbage))", prop_id=1,
        )
        assert out["query_basis"] == "centroid_30m"

    def test_unknown_warn_layerref_captured_verbatim(self, monkeypatch):
        """Fail-open (SDWC precedent): a layerRef we have never seen renders,
        never drops."""
        _patch_layers(
            monkeypatch, lra=_EMPTY_FEATURES, rail1=_EMPTY_FEATURES,
            rail2=_EMPTY_FEATURES,
            warn=[{"banner": True, "layerRef": "ZombieNewLayer2027",
                   "modal": True, "title": "Zombie New Warning"}],
        )
        out = pc.fetch_corridors_reservations(-33.88, 151.10, prop_id=1)
        assert out["warnings"]["status"] == "found"
        assert out["warnings"]["items"][0]["title"] == "Zombie New Warning"
        assert out["warnings"]["items"][0]["layerRef"] == "ZombieNewLayer2027"

    def test_goulburn_warn_fixture_found(self, monkeypatch):
        _patch_layers(monkeypatch, lra=_EMPTY_FEATURES, rail1=_EMPTY_FEATURES,
                      rail2=_EMPTY_FEATURES, warn=_fx("goulburn_warn.json"))
        out = pc.fetch_corridors_reservations(-34.75, 149.72, prop_id=448547)
        assert out["warnings"]["status"] == "found"
        assert out["warnings"]["items"][0]["title"] == "Land near Electrical Infrastructure"


class TestWktRings:
    def test_polygon_wkt_parses_to_rings(self):
        rings = pc._wkt_polygon_rings(_BURWOOD_WKT)
        assert rings is not None
        assert len(rings) == 1
        assert rings[0][0] == [151.1066, -33.8823]
        assert len(rings[0]) == 5

    def test_absent_and_garbage_return_none(self):
        assert pc._wkt_polygon_rings(None) is None
        assert pc._wkt_polygon_rings("") is None
        assert pc._wkt_polygon_rings("POINT(151 -33)") is None
        assert pc._wkt_polygon_rings("POLYGON((a b, c d, e f, a b))") is None


# ---------------------------------------------------------------------------
# Slice A — build_contributions_lines golden sentences
# ---------------------------------------------------------------------------

def _concord_result(monkeypatch_none=None):
    """Concord /cp fixture parsed through the real fetch parse."""
    data = _fx("concord_cp.json")
    plans = []
    for entry in data["cp"]["results"]:
        for cp in entry["cpResults"]:
            plans.append({"plan_name": cp["planName"], "plan_url": cp["planURL"]})
    res = data["icdp"]["results"][0]["results"][0]
    hpc = {
        "name": res["Name"],
        "component": res["Component"],
        "commenced_date": res["Commenced Date"],
        "ministerial_order_url": res["Ministerial Order"],
    }
    return {"status": "found", "plans": plans, "hpc": hpc, "lga_name": "CANADA BAY"}


class TestContributionsLines:
    def test_found_renders_plan_names_verbatim(self):
        out = build_contributions_lines(_concord_result())
        assert out["state"] == "found"
        assert "contributions plans apply to development in this location" in out["intro"]
        assert "does not calculate contribution amounts" in out["intro"]
        names = [p["name"] for p in out["plan_lines"]]
        assert (
            "City of Canada Bay Local Infrastructure Contributions Plan "
            "- Contributions Rates Dec 2024"
        ) in names
        assert "City of Canada Bay Local Infrastructure Contributions Plan" in names

    def test_found_hpc_line_carries_data_derived_date(self):
        out = build_contributions_lines(_concord_result())
        assert out["hpc_line"].startswith(
            "Housing and Productivity Contribution: "
            "Housing and Productivity Contribution Regions Map Greater Sydney Region"
        )
        assert "component BHPC" in out["hpc_line"]
        # commencement date comes from the recorded response, not config
        fixture_date = _fx("concord_cp.json")["icdp"]["results"][0]["results"][0]["Commenced Date"]
        assert f"commenced {fixture_date}" in out["hpc_line"]
        assert out["hpc_url"]

    def test_queried_empty_sentence(self):
        out = build_contributions_lines(
            {"status": "empty", "plans": [], "hpc": None, "lga_name": None}
        )
        assert out["state"] == "empty"
        assert out["status_line"] == (
            "No contributions plans returned for this location by the NSW Planning Portal."
        )
        assert out["plan_lines"] == []

    def test_hpc_only_response_does_not_announce_a_plan_list(self):
        """An icdp-only /cp result (HPC, zero plans) must not render the
        'following contributions plans apply' intro over an empty list — it
        states the queried-empty plans fact and still renders the HPC line."""
        res = _concord_result()
        res["plans"] = []
        out = build_contributions_lines(res)
        assert out["state"] == "found"
        assert out["intro"] is None
        assert out["plan_lines"] == []
        assert out["status_line"] == (
            "No contributions plans returned for this location by the NSW Planning Portal."
        )
        assert out["hpc_line"].startswith("Housing and Productivity Contribution: ")

    def test_failed_is_not_assessed_never_no_plans(self):
        for failed in ({"status": "failed"}, None, {}):
            out = build_contributions_lines(failed)
            assert out["state"] == "failed"
            assert out["status_line"].startswith(
                "Not assessed — contributions lookup unavailable"
            )
            assert "No contributions plans" not in out["status_line"]


# ---------------------------------------------------------------------------
# Slice B — build_corridors_lines golden sentences
# ---------------------------------------------------------------------------

def _burwood_lra_payload(basis="lot_polygon"):
    """Corridors payload assembled from the recorded Burwood LRA feature."""
    attrs = dict(_fx("burwood_lra_layer24.json")["features"][0]["attributes"])
    attrs["currency_date"] = "2017-02-17"
    attrs["commenced_date"] = "2012-11-09"
    return {
        "query_basis": basis,
        "data_currency": "2017-02-17",
        "lra": {"status": "found", "items": [attrs]},
        "rail_corridors": {"status": "empty", "items": []},
        "warnings": {"status": "empty", "items": []},
    }


def _all_empty_payload():
    return {
        "query_basis": "lot_polygon",
        "data_currency": None,
        "lra": {"status": "empty", "items": []},
        "rail_corridors": {"status": "empty", "items": []},
        "warnings": {"status": "empty", "items": []},
    }


class TestCorridorsLines:
    def test_lra_hit_alert_sentence_and_tile_flip(self):
        out = build_corridors_lines(_burwood_lra_payload())
        assert out["tile_flip"] is True
        assert len(out["alert_rows"]) == 1
        text = out["alert_rows"][0]
        assert text.startswith("Part of this lot is within a Land Reservation Acquisition area")
        assert "Local Road (R2)" in text
        assert "acquiring authority: Council" in text
        assert "Burwood Local Environmental Plan 2012" in text
        assert "map current to 2017-02-17" in text
        assert "A s10.7 certificate and the LEP acquisition clause state the effect." in text

    def test_lra_hit_states_map_presence_not_intent(self):
        """We state map presence, never acquisition intent."""
        text = out = build_corridors_lines(_burwood_lra_payload())["alert_rows"][0]
        assert "will be acquired" not in text
        assert "compulsory acquisition" not in text

    def test_centroid_basis_changes_prefix_and_adds_note(self):
        out = build_corridors_lines(_burwood_lra_payload(basis="centroid_30m"))
        assert out["alert_rows"][0].startswith(
            "A Land Reservation Acquisition area is mapped within 30 m of the lot centroid"
        )
        assert out["basis_note"] is not None
        assert "30 m radius around the lot centroid" in out["basis_note"]

    def test_lot_basis_has_no_basis_note(self):
        assert build_corridors_lines(_burwood_lra_payload())["basis_note"] is None

    def test_all_empty_renders_exact_clean_sentence_no_flip(self):
        out = build_corridors_lines(_all_empty_payload())
        assert out["tile_flip"] is False
        assert out["alert_rows"] == []
        assert out["clean_line"] == (
            "No land-reservation-acquisition areas, mapped rail corridor zones, "
            "or portal property warnings were returned for this lot."
        )
        assert out["not_assessed_rows"] == []

    def test_failed_subcheck_never_reads_clean(self):
        """Mutation check: an LRA failure must surface as Not assessed and the
        full checked-clean sentence must NOT render."""
        payload = _all_empty_payload()
        payload["lra"] = {"status": "failed", "items": []}
        out = build_corridors_lines(payload)
        assert out["clean_line"] != _CORRIDORS_ALL_CLEAR
        assert "land-reservation-acquisition" not in (out["clean_line"] or "")
        assert any(
            row.startswith("Not assessed — land-reservation-acquisition map lookup unavailable")
            for row in out["not_assessed_rows"]
        )
        # the sub-checks that DID run still render their empty result
        assert "mapped rail corridor zones" in out["clean_line"]
        assert "portal property warnings" in out["clean_line"]

    def test_rail_hit_is_note_row_not_tile_flip(self):
        payload = _all_empty_payload()
        # attribute values recorded live from SydneyTrain_ISEPP layer 1 (2026-07-07)
        payload["rail_corridors"] = {"status": "found", "items": [{
            "zone": "Corridor Protection Zone",
            "agency": "SydneyTrains Property",
            "defining_legislation": "Clause 86/Concurrence",
        }]}
        out = build_corridors_lines(payload)
        assert out["tile_flip"] is False
        assert out["alert_rows"] == []
        assert len(out["note_rows"]) == 1
        assert "Corridor Protection Zone" in out["note_rows"][0]
        assert "SydneyTrains Property" in out["note_rows"][0]
        assert "Clause 86/Concurrence" in out["note_rows"][0]

    def test_warning_title_rendered_verbatim(self):
        payload = _all_empty_payload()
        payload["warnings"] = {"status": "found", "items": [
            {"title": "Land near Electrical Infrastructure",
             "layerRef": "LandnearElectricalInfrastructure"},
        ]}
        out = build_corridors_lines(payload)
        assert out["note_rows"] == [
            "NSW Planning Portal property warning: Land near Electrical Infrastructure."
        ]
        assert out["tile_flip"] is False

    def test_none_payload_everything_not_assessed(self):
        out = build_corridors_lines(None)
        assert out["tile_flip"] is False
        assert out["clean_line"] is None
        assert len(out["not_assessed_rows"]) == 3

    def test_lra_missing_authority_stated_not_invented(self):
        payload = _burwood_lra_payload()
        payload["lra"]["items"][0]["AUTHORITY"] = None
        text = build_corridors_lines(payload)["alert_rows"][0]
        assert "acquiring authority: not stated in the mapping layer" in text
