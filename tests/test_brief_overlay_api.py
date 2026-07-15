"""Tests for services/brief_overlay_api.py — the flag-gated overlay endpoint.

The engine itself is covered by test_brief_narration.py; these tests cover the
HTTP contract: flag off answers enabled=false without touching the engine,
request validation rejects garbage at the gate, and engine output passes
through unchanged.
"""

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import services.brief_overlay_api as overlay_api
from services.brief_templates import RenderedLine, RenderedOverlay


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(overlay_api.router)
    return TestClient(app)


VALID_BODY = {
    "brief": {"address": "14 Stanley Street, Concord NSW 2137",
              "brief_type": "development"},
    "persona": "homeowner",
    "intent": "granny_flat",
}


class TestFlagGate:
    def test_flag_off_returns_disabled_without_calling_engine(self, client, monkeypatch):
        monkeypatch.delenv("BRIEF_LLM_OVERLAY_ENABLED", raising=False)
        with patch.object(overlay_api, "generate_overlay") as gen:
            res = client.post("/pipeline/brief-overlay", json=VALID_BODY)
        assert res.status_code == 200
        assert res.json() == {"enabled": False, "overlay": None}
        gen.assert_not_called()

    def test_flag_on_passes_engine_output_through(self, client, monkeypatch):
        monkeypatch.setenv("BRIEF_LLM_OVERLAY_ENABLED", "true")
        overlay = RenderedOverlay(
            headline="Zoning context — zone: R3",
            lines=[RenderedLine(template_id="T_ZONE_CONTEXT",
                                text="Zoning context — zone: R3 (authoritative)",
                                citation_ids=["F001"])],
            declined=False,
        )
        with patch.object(overlay_api, "generate_overlay", return_value=overlay) as gen:
            res = client.post("/pipeline/brief-overlay", json=VALID_BODY)
        assert res.status_code == 200
        body = res.json()
        assert body["enabled"] is True
        assert body["overlay"]["lines"][0]["citation_ids"] == ["F001"]
        # The endpoint pre-checks the flag once and forces enabled=True through
        # so the env is not consulted twice with different answers mid-request.
        assert gen.call_args.kwargs["enabled"] is True

    def test_flag_on_engine_none_returns_enabled_with_null_overlay(self, client, monkeypatch):
        # enabled:true + overlay:null tells the UI "feature on, nothing to
        # show for this request" — distinct from the flag-off shape.
        monkeypatch.setenv("BRIEF_LLM_OVERLAY_ENABLED", "true")
        with patch.object(overlay_api, "generate_overlay", return_value=None):
            res = client.post("/pipeline/brief-overlay", json=VALID_BODY)
        assert res.status_code == 200
        assert res.json() == {"enabled": True, "overlay": None}


class TestRequestValidation:
    def test_unknown_persona_rejected_422(self, client):
        res = client.post("/pipeline/brief-overlay",
                          json={**VALID_BODY, "persona": "influencer"})
        assert res.status_code == 422

    def test_unknown_intent_rejected_422(self, client):
        res = client.post("/pipeline/brief-overlay",
                          json={**VALID_BODY, "intent": "build_a_castle"})
        assert res.status_code == 422

    def test_brief_without_address_rejected_422(self, client):
        res = client.post("/pipeline/brief-overlay",
                          json={**VALID_BODY, "brief": {"zone": "R2"}})
        assert res.status_code == 422

    def test_oversize_question_rejected_422(self, client):
        res = client.post("/pipeline/brief-overlay",
                          json={**VALID_BODY, "question": "x" * 301})
        assert res.status_code == 422

    def test_intent_null_is_valid(self, client, monkeypatch):
        monkeypatch.setenv("BRIEF_LLM_OVERLAY_ENABLED", "true")
        with patch.object(overlay_api, "generate_overlay", return_value=None):
            res = client.post("/pipeline/brief-overlay",
                              json={**VALID_BODY, "intent": None})
        assert res.status_code == 200


class TestErrorIsolation:
    def test_engine_raising_returns_500_not_traceback(self, client, monkeypatch):
        monkeypatch.setenv("BRIEF_LLM_OVERLAY_ENABLED", "true")
        with patch.object(overlay_api, "generate_overlay",
                          side_effect=RuntimeError("boom")):
            res = client.post("/pipeline/brief-overlay", json=VALID_BODY)
        assert res.status_code == 500
        assert res.json()["detail"] == "overlay generation failed"
