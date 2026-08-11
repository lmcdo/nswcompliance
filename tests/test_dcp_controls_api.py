"""Campaign item 5 — /pipeline/dcp-controls, the guarded read over HTTP.

What must hold: the endpoint serves fetch_dcp_setbacks verbatim (rows +
as-at + registry PDF map), keeps three states distinguishable (rows /
checked-none / source-unavailable), and never invents rows on failure.

Mutation notes: returning {} from a failed read fails
test_db_failure_is_503; collapsing available=False into an empty rows list
fails test_none_result_is_checked_none (reason must be present).
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "services"))
sys.path.insert(0, str(ROOT / "scripts"))

from fastapi import HTTPException  # noqa: E402

from services import dcp_controls_api  # noqa: E402


def _patch_connect(monkeypatch, ok=True):
    import psycopg2

    if ok:
        monkeypatch.setattr(psycopg2, "connect", lambda *_a, **_k: MagicMock(),
                            raising=False)
    else:
        def boom(*_a, **_k):
            raise RuntimeError("db down")
        monkeypatch.setattr(psycopg2, "connect", boom, raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgres://x")


class TestDcpControlsEndpoint:
    def test_serves_the_guarded_result_verbatim(self, monkeypatch):
        _patch_connect(monkeypatch)
        monkeypatch.setattr(
            dcp_controls_api, "fetch_dcp_setbacks",
            lambda conn, lga, zone, raise_on_error=False: {
                "dcp_name": "Waverley DCP 2022", "dcp_url": "u",
                "caveat": None, "clause_ref": "B2.1",
                "zone_filter_applied": "R2",
                "as_at": {"date": "2022-01-01", "precision": "year",
                          "kind": "effective", "basis": "stated_in_document"},
                "as_at_status": "resolved", "as_at_line": "In force from 2022",
                "registry_pdf_urls": {"part-b": "https://r2/w.pdf"},
                "setbacks": [{"semantic_type": "front_setback"}],
                "sd_setbacks": [{"semantic_type": "rear_setback"}],
            })
        out = dcp_controls_api.dcp_controls("waverley", "R2 Low Density")
        assert out["available"] is True
        assert len(out["rows"]) == 2  # dh + sd flattened
        assert out["registry_pdf_urls"] == {"part-b": "https://r2/w.pdf"}
        assert out["as_at_line"] == "In force from 2022"

    def test_none_result_is_checked_none(self, monkeypatch):
        _patch_connect(monkeypatch)
        monkeypatch.setattr(dcp_controls_api, "fetch_dcp_setbacks",
                            lambda conn, lga, zone, raise_on_error=False: None)
        out = dcp_controls_api.dcp_controls("nowhere")
        assert out["available"] is False
        assert out["reason"]

    def test_db_failure_is_503(self, monkeypatch):
        _patch_connect(monkeypatch, ok=False)
        with pytest.raises(HTTPException) as exc:
            dcp_controls_api.dcp_controls("waverley")
        assert exc.value.status_code == 503

    def test_empty_slug_is_checked_none_not_a_query(self, monkeypatch):
        out = dcp_controls_api.dcp_controls("   ")
        assert out["available"] is False
        assert "no LGA slug" in out["reason"]

    def test_missing_database_url_is_503(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        with pytest.raises(HTTPException) as exc:
            dcp_controls_api.dcp_controls("waverley")
        assert exc.value.status_code == 503
