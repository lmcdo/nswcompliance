"""Tests for the lot search API endpoints."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.lot_search import router, _build_where, LotSearchRequest


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


# ---------------------------------------------------------------------------
# _build_where unit tests
# ---------------------------------------------------------------------------


class TestBuildWhere:
    def test_empty_request(self):
        req = LotSearchRequest()
        where, params = _build_where(req)
        assert where == "TRUE"
        assert params == []

    def test_lga_filter(self):
        req = LotSearchRequest(lga_name="inner west")
        where, params = _build_where(req)
        assert "lga_name = %s" in where
        assert params == ["INNER WEST"]

    def test_zone_filter(self):
        req = LotSearchRequest(zone_codes=["R2", "R3"])
        where, params = _build_where(req)
        assert "zone_code = ANY(%s)" in where
        assert params == [["R2", "R3"]]

    def test_area_range(self):
        req = LotSearchRequest(min_area_m2=400, max_area_m2=800)
        where, params = _build_where(req)
        assert "lot_area_m2 >= %s" in where
        assert "lot_area_m2 <= %s" in where
        assert 400 in params
        assert 800 in params

    def test_gfa_filter(self):
        req = LotSearchRequest(min_gfa_m2=200)
        where, params = _build_where(req)
        assert "ca_realistic_gfa_m2 >= %s" in where
        assert params == [200]

    def test_heritage_true(self):
        req = LotSearchRequest(heritage=True)
        where, params = _build_where(req)
        assert "heritage = %s" in where
        assert params == [True]

    def test_heritage_false(self):
        req = LotSearchRequest(heritage=False)
        where, params = _build_where(req)
        assert "heritage = %s" in where
        assert params == [False]

    def test_flood_filter(self):
        req = LotSearchRequest(flood_prone=False)
        where, params = _build_where(req)
        assert "flood_prone = %s" in where

    def test_bushfire_filter(self):
        req = LotSearchRequest(bushfire_prone=True)
        where, params = _build_where(req)
        assert "bushfire_prone = %s" in where

    def test_min_confidence(self):
        req = LotSearchRequest(min_confidence="medium")
        where, params = _build_where(req)
        assert "ca_confidence = ANY(%s)" in where
        # Should include medium and high
        assert "medium" in params[0]
        assert "high" in params[0]
        assert "low" not in params[0]

    def test_min_confidence_high(self):
        req = LotSearchRequest(min_confidence="high")
        where, params = _build_where(req)
        assert params[0] == ["high"]

    def test_binding_constraint(self):
        req = LotSearchRequest(binding_constraint=["lep_fsr", "dcp_setbacks"])
        where, params = _build_where(req)
        assert "ca_binding_constraint = ANY(%s)" in where

    def test_bbox_filter(self):
        req = LotSearchRequest(bbox=[151.1, -33.9, 151.2, -33.8])
        where, params = _build_where(req)
        assert "ST_Intersects" in where
        assert "ST_MakeEnvelope" in where
        assert 151.1 in params

    def test_multiple_filters_combined(self):
        req = LotSearchRequest(
            lga_name="INNER WEST",
            zone_codes=["R2"],
            min_area_m2=500,
            heritage=False,
        )
        where, params = _build_where(req)
        assert " AND " in where
        assert where.count("AND") == 3  # 4 conditions joined by 3 ANDs

    def test_min_dwellings(self):
        req = LotSearchRequest(min_dwellings=2)
        where, params = _build_where(req)
        assert "ca_realistic_dwellings >= %s" in where
        assert params == [2]


# ---------------------------------------------------------------------------
# Endpoint integration tests (mocked DB)
# ---------------------------------------------------------------------------


def _mock_cursor_for_search(rows, total_count=None):
    """Create a mock cursor that returns rows for lot search queries."""
    cur = MagicMock()
    # First call: COUNT query
    # Second call: SELECT query
    if total_count is None:
        total_count = len(rows)
    cur.fetchone = MagicMock(side_effect=[(total_count,)])
    cur.fetchall = MagicMock(return_value=rows)
    return cur


class TestLotSearchEndpoint:
    @patch("services.lot_search._get_conn")
    def test_basic_search(self, mock_conn, client):
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = (1,)
        mock_cur.fetchall.return_value = [
            ("LOT1//DP1", "INNER WEST", "R2", 600.0,
             9.0, 0.5, False, False,
             False, None,
             280.0, 1,
             "lep_fsr", "medium",
             9.0, 0.5,
             400.0,
             6.0, 6.0, 0.9,
             ["missing frontage"]),
        ]
        conn = MagicMock()
        conn.cursor.return_value = mock_cur
        mock_conn.return_value = conn

        resp = client.post("/lot-search", json={
            "lga_name": "INNER WEST",
            "zone_codes": ["R2"],
            "min_area_m2": 500,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 1
        assert len(data["lots"]) == 1
        lot = data["lots"][0]
        assert lot["lotidstring"] == "LOT1//DP1"
        assert lot["zone_code"] == "R2"
        assert lot["ca_realistic_gfa_m2"] == 280.0
        assert lot["ca_binding_constraint"] == "lep_fsr"

    @patch("services.lot_search._get_conn")
    def test_empty_result(self, mock_conn, client):
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = (0,)
        mock_cur.fetchall.return_value = []
        conn = MagicMock()
        conn.cursor.return_value = mock_cur
        mock_conn.return_value = conn

        resp = client.post("/lot-search", json={"lga_name": "NONEXISTENT"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 0
        assert data["lots"] == []

    @patch("services.lot_search._get_conn")
    def test_order_by_validation(self, mock_conn, client):
        """Invalid order_by columns fall back to default."""
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = (0,)
        mock_cur.fetchall.return_value = []
        conn = MagicMock()
        conn.cursor.return_value = mock_cur
        mock_conn.return_value = conn

        resp = client.post("/lot-search", json={
            "order_by": "DROP TABLE users; --",
        })
        assert resp.status_code == 200

    @patch("services.lot_search._get_conn")
    def test_pagination(self, mock_conn, client):
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = (100,)
        mock_cur.fetchall.return_value = []
        conn = MagicMock()
        conn.cursor.return_value = mock_cur
        mock_conn.return_value = conn

        resp = client.post("/lot-search", json={
            "limit": 10,
            "offset": 50,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 100

    def test_invalid_limit(self, client):
        resp = client.post("/lot-search", json={"limit": 9999})
        assert resp.status_code == 422  # pydantic validation

    def test_invalid_order_dir(self, client):
        resp = client.post("/lot-search", json={"order_dir": "DROP"})
        assert resp.status_code == 422

    def test_invalid_bbox_length(self, client):
        resp = client.post("/lot-search", json={"bbox": [1.0, 2.0]})
        assert resp.status_code == 422


class TestLotSearchSummaryEndpoint:
    @patch("services.lot_search._get_conn")
    def test_basic_summary(self, mock_conn, client):
        mock_cur = MagicMock()
        # Scalar aggregates
        mock_cur.fetchone.return_value = (
            100,   # total
            80,    # with CA
            550.0, # avg area
            250.0, # avg gfa
            230.0, # median gfa
            180.0, # p25
            300.0, # p75
            1.2,   # avg dwellings
            10,    # heritage
            5,     # flood
            3,     # bushfire
            40,    # high
            30,    # medium
            10,    # low
        )
        # Zone distribution + binding distribution
        mock_cur.fetchall = MagicMock(side_effect=[
            [("R2", 60), ("R3", 25), ("R4", 15)],
            [("lep_fsr", 50), ("dcp_setbacks", 30)],
        ])
        conn = MagicMock()
        conn.cursor.return_value = mock_cur
        mock_conn.return_value = conn

        resp = client.post("/lot-search/summary", json={
            "lga_name": "INNER WEST",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_lots"] == 100
        assert data["lots_with_ca"] == 80
        assert data["avg_gfa_m2"] == 250.0
        assert data["median_gfa_m2"] == 230.0
        assert data["heritage_count"] == 10
        assert data["confidence_high"] == 40
        assert len(data["zone_distribution"]) == 3
        assert data["zone_distribution"][0]["zone_code"] == "R2"
        assert len(data["binding_distribution"]) == 2

    @patch("services.lot_search._get_conn")
    def test_empty_summary(self, mock_conn, client):
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = (
            0, 0, None, None, None, None, None, None,
            0, 0, 0, 0, 0, 0,
        )
        mock_cur.fetchall = MagicMock(side_effect=[[], []])
        conn = MagicMock()
        conn.cursor.return_value = mock_cur
        mock_conn.return_value = conn

        resp = client.post("/lot-search/summary", json={
            "lga_name": "EMPTY",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_lots"] == 0
        assert data["avg_gfa_m2"] is None
        assert data["zone_distribution"] == []


# ---------------------------------------------------------------------------
# Build script tests
# ---------------------------------------------------------------------------


class TestBuildHelpers:
    def test_lga_slug_to_overlay_name(self):
        from scripts.build_lot_search_index import _lga_slug_to_overlay_name
        assert _lga_slug_to_overlay_name("inner_west") == "INNER WEST"
        assert _lga_slug_to_overlay_name("sydney") == "SYDNEY"
        assert _lga_slug_to_overlay_name("blue_mountains") == "BLUE MOUNTAINS"

    def test_build_dcp_controls_from_raw_none(self):
        from scripts.build_lot_search_index import _build_dcp_controls_from_raw
        assert _build_dcp_controls_from_raw(None) == []
        assert _build_dcp_controls_from_raw({}) == []

    def test_build_dcp_controls_from_raw_with_data(self):
        from scripts.build_lot_search_index import _build_dcp_controls_from_raw
        raw = {
            "setbacks": [
                {"control_type": "front_setback", "dev_type": "dwelling_house",
                 "requirement": 6.0, "unit": "m", "clause": "C1.2"},
            ],
            "sd_setbacks": [],
            "clause_ref": "Part 3",
        }
        controls = _build_dcp_controls_from_raw(raw)
        assert len(controls) == 1
        assert controls[0].control_type == "front_setback"
        assert controls[0].value_min == 6.0
        assert controls[0].source_ref == "C1.2"
