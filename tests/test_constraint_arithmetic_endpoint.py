"""Tests for the constraint arithmetic FastAPI endpoint."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from services.constraint_arithmetic import router, ConstraintArithmeticResult
from fastapi import FastAPI


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestConstraintArithmeticEndpoint:
    def test_basic_request(self, client):
        resp = client.post("/constraint-arithmetic", json={
            "lot_area_m2": 600,
            "dev_type": "dwelling_house",
            "lep_height_str": "9",
            "lep_fsr_str": "0.5",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["lot_area_m2"] == 600
        assert data["dev_type"] == "dwelling_house"
        assert data["lep_height_m"] == 9.0
        assert data["lep_fsr"] == 0.5
        assert data["realistic_gfa_m2"] is not None
        assert data["confidence"] in ("low", "medium", "high")

    def test_with_dcp_controls(self, client):
        resp = client.post("/constraint-arithmetic", json={
            "lot_area_m2": 600,
            "dev_type": "dwelling_house",
            "lep_height_str": "9",
            "lep_fsr_str": "0.5",
            "frontage_m": 15,
            "depth_m": 40,
            "dcp_controls": [
                {"control_type": "front_setback", "dev_type": "dwelling_house",
                 "value_min": 6.0, "unit": "m"},
                {"control_type": "rear_setback", "dev_type": "dwelling_house",
                 "value_min": 6.0, "unit": "m"},
                {"control_type": "side_setback", "dev_type": "dwelling_house",
                 "value_min": 0.9, "unit": "m"},
            ],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["setback_front_m"] == 6.0
        assert data["setback_rear_m"] == 6.0
        assert data["setback_side_m"] == 0.9
        assert data["buildable_footprint_m2"] is not None
        # Footprint should be less than lot area due to setbacks
        assert data["buildable_footprint_m2"] < 600

    def test_with_sepp_override(self, client):
        resp = client.post("/constraint-arithmetic", json={
            "lot_area_m2": 600,
            "dev_type": "dwelling_house",
            "lep_height_str": "9",
            "lep_fsr_str": "0.5",
            "sepp_lep_overrides": [
                {"dev_type": "dwelling_house", "control": "height",
                 "lep_value": 9.0, "sepp_value": 12.0,
                 "note": "SEPP override"},
            ],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["effective_height_m"] == 12.0

    def test_no_lep_data(self, client):
        resp = client.post("/constraint-arithmetic", json={
            "lot_area_m2": 600,
            "dev_type": "dwelling_house",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["gaps"]) >= 2  # missing height + FSR
        assert data["confidence"] == "low"

    def test_validation_error(self, client):
        resp = client.post("/constraint-arithmetic", json={})
        assert resp.status_code == 422  # pydantic validation error

    def test_response_has_steps(self, client):
        resp = client.post("/constraint-arithmetic", json={
            "lot_area_m2": 600,
            "dev_type": "dwelling_house",
            "lep_height_str": "9",
            "lep_fsr_str": "0.5",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["steps"], list)
        assert len(data["steps"]) > 0

    def test_response_has_disclaimer(self, client):
        resp = client.post("/constraint-arithmetic", json={
            "lot_area_m2": 600,
            "dev_type": "dwelling_house",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "preliminary" in data["disclaimer"].lower()
