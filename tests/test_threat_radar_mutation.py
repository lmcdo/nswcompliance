"""
Mutation-testing-grade tests for services/threat_radar.py.

Targets untested functions:
  - check (endpoint)
  - subscribe (endpoint)
  - _fetch_das
  - _lookup_property_context (with DB mocked)
  - list_subscriptions
  - _get_conn

These tests mock DB and HTTP to exercise branching logic that mutmut targets.
"""

import sys
import os
import json
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.threat_radar as tr
from services.threat_radar import (
    SubscribeRequest,
    CheckRequest,
    ALERT_RADIUS_M,
    WINDOW_DAYS,
    DA_URL,
    CDC_URL,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_conn(rows=None, fetchone_val=None):
    """Create a fake psycopg2 connection with cursor context manager."""
    conn = MagicMock()
    cur = MagicMock()
    cur.fetchall.return_value = rows or []
    cur.fetchone.return_value = fetchone_val
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cur
    return conn, cur


def _subscription_row(
    sub_id="sub-123",
    address="1 Test St, Sydney",
    lat=-33.87,
    lng=151.21,
    email="user@test.com",
    council="Inner West",
    seen=None,
):
    """Build a fake subscription DB row dict."""
    return {
        "id": sub_id,
        "address": address,
        "lat": lat,
        "lng": lng,
        "email": email,
        "active": True,
        "inputs": {
            "council_name": council,
            "seen_application_numbers": seen or [],
        },
    }


def _da_app(num="DA/2026/001", lat=-33.87, lng=151.21):
    """Build a minimal ePlanning DA response item within radius."""
    return {
        "PlanningPortalApplicationNumber": num,
        "ApplicationNumber": num,
        "Latitude": str(lat),
        "Longitude": str(lng),
        "Location": [{"Y": str(lat), "X": str(lng)}],
        "ApplicationType": "Development Application",
    }


# ---------------------------------------------------------------------------
# _get_conn
# ---------------------------------------------------------------------------

class TestGetConn:
    def test_uses_database_url_when_set(self, monkeypatch):
        mock_connect = MagicMock()
        monkeypatch.setattr(tr.psycopg2, "connect", mock_connect)
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
        tr._get_conn()
        mock_connect.assert_called_once_with("postgresql://user:pass@host/db")

    def test_uses_individual_params_without_database_url(self, monkeypatch):
        mock_connect = MagicMock()
        monkeypatch.setattr(tr.psycopg2, "connect", mock_connect)
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("DB_HOST", "myhost")
        monkeypatch.setenv("DB_NAME", "mydb")
        monkeypatch.setenv("DB_USER", "myuser")
        monkeypatch.setenv("DB_PASSWORD", "mypass")
        monkeypatch.setenv("DB_PORT", "5433")
        tr._get_conn()
        mock_connect.assert_called_once_with(
            host="myhost", database="mydb", user="myuser", password="mypass", port=5433
        )

    def test_default_params_when_no_env(self, monkeypatch):
        mock_connect = MagicMock()
        monkeypatch.setattr(tr.psycopg2, "connect", mock_connect)
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("DB_HOST", raising=False)
        monkeypatch.delenv("DB_NAME", raising=False)
        monkeypatch.delenv("DB_USER", raising=False)
        monkeypatch.delenv("DB_PASSWORD", raising=False)
        monkeypatch.delenv("DB_PORT", raising=False)
        tr._get_conn()
        mock_connect.assert_called_once_with(
            host="127.0.0.1", database="nsw_planning", user="postgres", password="", port=5432
        )


# ---------------------------------------------------------------------------
# _lookup_property_context — with mocked DB
# ---------------------------------------------------------------------------

class TestLookupPropertyContext:
    def test_returns_zone_from_db(self, monkeypatch):
        conn, cur = _fake_conn(rows=[
            {"value": "R2", "layer_type": "zone"},
        ])
        monkeypatch.setattr(tr, "_get_conn", lambda: conn)
        result = tr._lookup_property_context(-33.87, 151.21)
        assert result["zone"] == "R2"
        assert result["tod_precinct"] is None

    def test_returns_tod_precinct_from_db(self, monkeypatch):
        conn, cur = _fake_conn(rows=[
            {"value": "Sydenham", "layer_type": "tod_precinct"},
        ])
        monkeypatch.setattr(tr, "_get_conn", lambda: conn)
        result = tr._lookup_property_context(-33.87, 151.21)
        assert result["tod_precinct"] is True
        assert result["tod_type"] == "tod_precinct"

    def test_returns_tod_accelerated(self, monkeypatch):
        conn, cur = _fake_conn(rows=[
            {"value": "Bankstown", "layer_type": "tod_accelerated"},
        ])
        monkeypatch.setattr(tr, "_get_conn", lambda: conn)
        result = tr._lookup_property_context(-33.87, 151.21)
        assert result["tod_precinct"] is True
        assert result["tod_type"] == "tod_accelerated"

    def test_zone_and_tod_combined(self, monkeypatch):
        conn, cur = _fake_conn(rows=[
            {"value": "R3", "layer_type": "zone"},
            {"value": "Marrickville", "layer_type": "tod_precinct"},
        ])
        monkeypatch.setattr(tr, "_get_conn", lambda: conn)
        result = tr._lookup_property_context(-33.87, 151.21)
        assert result["zone"] == "R3"
        assert result["tod_precinct"] is True
        assert result["tod_type"] == "tod_precinct"

    def test_db_error_returns_none_defaults(self, monkeypatch):
        def boom():
            raise Exception("connection refused")
        monkeypatch.setattr(tr, "_get_conn", boom)
        result = tr._lookup_property_context(-33.87, 151.21)
        assert result == {"zone": None, "tod_precinct": None, "tod_type": None}

    def test_empty_rows_returns_none_defaults(self, monkeypatch):
        conn, cur = _fake_conn(rows=[])
        monkeypatch.setattr(tr, "_get_conn", lambda: conn)
        result = tr._lookup_property_context(-33.87, 151.21)
        assert result == {"zone": None, "tod_precinct": None, "tod_type": None}

    def test_passes_lng_lat_in_correct_order(self, monkeypatch):
        """SQL uses ST_MakePoint(lng, lat) — verify arg order."""
        conn, cur = _fake_conn(rows=[])
        monkeypatch.setattr(tr, "_get_conn", lambda: conn)
        tr._lookup_property_context(-33.87, 151.21)
        # Second execute call (first is SET LOCAL statement_timeout)
        calls = cur.execute.call_args_list
        assert len(calls) == 2
        sql_call = calls[1]
        params = sql_call[0][1]  # (lng, lat)
        assert params == (151.21, -33.87)

    def test_conn_closed_on_success(self, monkeypatch):
        conn, cur = _fake_conn(rows=[])
        monkeypatch.setattr(tr, "_get_conn", lambda: conn)
        tr._lookup_property_context(-33.87, 151.21)
        conn.close.assert_called_once()


# ---------------------------------------------------------------------------
# _fetch_das
# ---------------------------------------------------------------------------

class TestFetchDas:
    def test_successful_fetch_both_endpoints(self, monkeypatch):
        resp_da = MagicMock()
        resp_da.json.return_value = {"Application": [_da_app("DA/001"), _da_app("DA/002")]}
        resp_da.raise_for_status = MagicMock()

        resp_cdc = MagicMock()
        resp_cdc.json.return_value = {"Application": [_da_app("CDC/001")]}
        resp_cdc.raise_for_status = MagicMock()

        def mock_get(url, headers=None, timeout=None):
            if "OnlineDA" in url:
                return resp_da
            return resp_cdc

        monkeypatch.setattr(tr.requests, "get", mock_get)
        apps, available, counts = tr._fetch_das("Inner West")
        assert available is True
        assert len(apps) == 3
        assert counts[DA_URL] == 2
        assert counts[CDC_URL] == 1

    def test_uses_application_list_key(self, monkeypatch):
        """Some responses use 'ApplicationList' instead of 'Application'."""
        resp = MagicMock()
        resp.json.return_value = {"ApplicationList": [_da_app("DA/X")]}
        resp.raise_for_status = MagicMock()
        monkeypatch.setattr(tr.requests, "get", lambda *a, **kw: resp)
        apps, available, counts = tr._fetch_das("Randwick")
        assert len(apps) == 2  # same response for both DA+CDC URLs
        assert available is True

    def test_both_endpoints_fail_returns_unavailable(self, monkeypatch):
        def boom(*a, **kw):
            raise Exception("timeout")
        monkeypatch.setattr(tr.requests, "get", boom)
        apps, available, counts = tr._fetch_das("Inner West")
        assert apps == []
        assert available is False
        assert "error" in str(counts[DA_URL])
        assert "error" in str(counts[CDC_URL])

    def test_one_endpoint_fails_still_available(self, monkeypatch):
        call_count = [0]
        def mock_get(url, **kw):
            call_count[0] += 1
            if "OnlineDA" in url:
                raise Exception("fail")
            resp = MagicMock()
            resp.json.return_value = {"Application": [_da_app("CDC/1")]}
            resp.raise_for_status = MagicMock()
            return resp
        monkeypatch.setattr(tr.requests, "get", mock_get)
        apps, available, counts = tr._fetch_das("Inner West")
        assert available is True
        assert len(apps) == 1
        assert "error" in str(counts[DA_URL])
        assert counts[CDC_URL] == 1

    def test_normalises_council_name(self, monkeypatch):
        """Verify council name is normalised before passing to API."""
        captured_headers = []
        resp = MagicMock()
        resp.json.return_value = {"Application": []}
        resp.raise_for_status = MagicMock()
        def mock_get(url, headers=None, **kw):
            captured_headers.append(headers)
            return resp
        monkeypatch.setattr(tr.requests, "get", mock_get)
        tr._fetch_das("inner west")
        filters = json.loads(captured_headers[0]["filters"])
        assert filters["filters"]["CouncilName"] == ["Inner West Council"]

    def test_days_back_parameter_affects_date(self, monkeypatch):
        captured_headers = []
        resp = MagicMock()
        resp.json.return_value = {"Application": []}
        resp.raise_for_status = MagicMock()
        def mock_get(url, headers=None, **kw):
            captured_headers.append(headers)
            return resp
        monkeypatch.setattr(tr.requests, "get", mock_get)
        tr._fetch_das("Inner West", days_back=30)
        filters = json.loads(captured_headers[0]["filters"])
        since_str = filters["filters"]["LodgementDateFrom"]
        since_date = datetime.strptime(since_str, "%Y-%m-%d").date()
        expected = (datetime.utcnow() - timedelta(days=30)).date()
        assert since_date == expected

    def test_empty_response_returns_empty_list(self, monkeypatch):
        resp = MagicMock()
        resp.json.return_value = {}  # no Application or ApplicationList key
        resp.raise_for_status = MagicMock()
        monkeypatch.setattr(tr.requests, "get", lambda *a, **kw: resp)
        apps, available, counts = tr._fetch_das("Inner West")
        assert apps == []
        assert available is True
        assert counts[DA_URL] == 0

    def test_headers_include_pagination(self, monkeypatch):
        captured = []
        resp = MagicMock()
        resp.json.return_value = {"Application": []}
        resp.raise_for_status = MagicMock()
        def mock_get(url, headers=None, **kw):
            captured.append(headers)
            return resp
        monkeypatch.setattr(tr.requests, "get", mock_get)
        tr._fetch_das("Inner West")
        assert captured[0]["PageSize"] == "200"
        assert captured[0]["PageNumber"] == "1"

    def test_timeout_is_20(self, monkeypatch):
        captured_kwargs = []
        resp = MagicMock()
        resp.json.return_value = {"Application": []}
        resp.raise_for_status = MagicMock()
        def mock_get(url, **kw):
            captured_kwargs.append(kw)
            return resp
        monkeypatch.setattr(tr.requests, "get", mock_get)
        tr._fetch_das("Inner West")
        assert captured_kwargs[0]["timeout"] == 20


# ---------------------------------------------------------------------------
# subscribe endpoint
# ---------------------------------------------------------------------------

class TestSubscribe:
    def test_new_subscription_returns_id(self, monkeypatch):
        conn, cur = _fake_conn()
        # First fetchone (duplicate check) returns None
        # Second fetchone (INSERT RETURNING) returns new id
        cur.fetchone.side_effect = [None, {"id": "new-id-456"}]
        monkeypatch.setattr(tr, "_get_conn", lambda: conn)

        req = SubscribeRequest(
            address="1 Test St",
            lat=-33.87,
            lng=151.21,
            email="user@test.com",
            council_name="Inner West",
        )
        result = tr.subscribe(req)
        assert result["subscription_id"] == "new-id-456"
        assert result["status"] == "active"
        assert result["address"] == "1 Test St"
        conn.commit.assert_called_once()

    def test_existing_subscription_returns_existing_id(self, monkeypatch):
        conn, cur = _fake_conn()
        cur.fetchone.return_value = {"id": "existing-789"}
        monkeypatch.setattr(tr, "_get_conn", lambda: conn)

        req = SubscribeRequest(
            address="1 Test St",
            lat=-33.87,
            lng=151.21,
            email="user@test.com",
            council_name="Inner West",
        )
        result = tr.subscribe(req)
        assert result["subscription_id"] == "existing-789"
        assert result["status"] == "active"
        # Should NOT commit (no insert happened)
        conn.commit.assert_not_called()

    def test_invalid_email_raises_422(self, monkeypatch):
        from fastapi import HTTPException
        req = SubscribeRequest(
            address="1 Test St",
            lat=-33.87,
            lng=151.21,
            email="bademail",
            council_name="Inner West",
        )
        with pytest.raises(HTTPException) as exc_info:
            tr.subscribe(req)
        assert exc_info.value.status_code == 422

    def test_conn_closed_even_on_success(self, monkeypatch):
        conn, cur = _fake_conn()
        cur.fetchone.side_effect = [None, {"id": "x"}]
        monkeypatch.setattr(tr, "_get_conn", lambda: conn)
        req = SubscribeRequest(
            address="1 Test St", lat=-33.87, lng=151.21,
            email="a@b.com", council_name="Inner West",
        )
        tr.subscribe(req)
        conn.close.assert_called_once()


# ---------------------------------------------------------------------------
# check endpoint
# ---------------------------------------------------------------------------

class TestCheck:
    def _setup_check(self, monkeypatch, sub_row=None, apps=None, api_available=True):
        """Wire up all mocks for the check endpoint."""
        sub = sub_row or _subscription_row()
        conn1, cur1 = _fake_conn(fetchone_val=sub)
        conn2, cur2 = _fake_conn()

        conns = [conn1, conn2]
        conn_idx = [0]
        def get_conn():
            c = conns[conn_idx[0]]
            conn_idx[0] += 1
            return c
        monkeypatch.setattr(tr, "_get_conn", get_conn)

        fetch_apps = apps if apps is not None else []
        per_endpoint = {DA_URL: len(fetch_apps), CDC_URL: 0}
        monkeypatch.setattr(
            tr, "_fetch_das",
            lambda council, **kw: (fetch_apps, api_available, per_endpoint),
        )
        monkeypatch.setattr(
            tr, "_lookup_property_context",
            lambda lat, lng: {"zone": "R2", "tod_precinct": None, "tod_type": None},
        )
        monkeypatch.setattr(tr, "log_audit_trail", MagicMock())
        return conn2, cur2

    def test_check_returns_required_keys(self, monkeypatch):
        self._setup_check(monkeypatch)
        req = CheckRequest(subscription_id="sub-123")
        result = tr.check(req)
        assert "subscription_id" in result
        assert "address" in result
        assert "new_application_count" in result
        assert "new_applications" in result
        assert "total_nearby" in result
        assert "checked_at" in result
        assert "property_context" in result

    def test_check_not_found_raises_404(self, monkeypatch):
        conn, cur = _fake_conn(fetchone_val=None)
        monkeypatch.setattr(tr, "_get_conn", lambda: conn)
        from fastapi import HTTPException
        req = CheckRequest(subscription_id="nonexistent")
        with pytest.raises(HTTPException) as exc_info:
            tr.check(req)
        assert exc_info.value.status_code == 404

    def test_check_missing_council_raises_422(self, monkeypatch):
        sub = _subscription_row()
        sub["inputs"]["council_name"] = ""
        conn, cur = _fake_conn(fetchone_val=sub)
        monkeypatch.setattr(tr, "_get_conn", lambda: conn)
        monkeypatch.setattr(
            tr, "_lookup_property_context",
            lambda lat, lng: {"zone": None, "tod_precinct": None, "tod_type": None},
        )
        from fastapi import HTTPException
        req = CheckRequest(subscription_id="sub-123")
        with pytest.raises(HTTPException) as exc_info:
            tr.check(req)
        assert exc_info.value.status_code == 422

    def test_check_with_nearby_apps(self, monkeypatch):
        apps = [_da_app("DA/2026/001", lat=-33.87, lng=151.21)]
        self._setup_check(monkeypatch, apps=apps)
        req = CheckRequest(subscription_id="sub-123")
        result = tr.check(req)
        assert result["new_application_count"] == 1
        assert result["total_nearby"] == 1
        assert len(result["new_applications"]) == 1

    def test_check_deduplicates_seen_apps(self, monkeypatch):
        """Apps already in 'seen' list should not appear as new."""
        sub = _subscription_row(seen=["DA/2026/001"])
        apps = [_da_app("DA/2026/001", lat=-33.87, lng=151.21)]
        self._setup_check(monkeypatch, sub_row=sub, apps=apps)
        req = CheckRequest(subscription_id="sub-123")
        result = tr.check(req)
        assert result["new_application_count"] == 0
        assert result["total_nearby"] == 1  # still nearby, just not new

    def test_check_api_unavailable_returns_error(self, monkeypatch):
        sub = _subscription_row()
        conn, cur = _fake_conn(fetchone_val=sub)
        monkeypatch.setattr(tr, "_get_conn", lambda: conn)
        monkeypatch.setattr(
            tr, "_fetch_das",
            lambda council, **kw: ([], False, {DA_URL: "error: timeout", CDC_URL: "error: timeout"}),
        )
        monkeypatch.setattr(
            tr, "_lookup_property_context",
            lambda lat, lng: {"zone": "R2", "tod_precinct": None, "tod_type": None},
        )
        monkeypatch.setattr(tr, "log_audit_trail", MagicMock())
        req = CheckRequest(subscription_id="sub-123")
        result = tr.check(req)
        assert result["api_error"] is not None
        assert result["new_application_count"] == 0
        assert result["checked_at"] is None

    def test_check_updates_seen_set_in_db(self, monkeypatch):
        apps = [_da_app("DA/NEW/001", lat=-33.87, lng=151.21)]
        conn2, cur2 = self._setup_check(monkeypatch, apps=apps)
        req = CheckRequest(subscription_id="sub-123")
        tr.check(req)
        # Verify the UPDATE was called
        cur2.execute.assert_called()
        conn2.commit.assert_called_once()

    def test_check_empty_apps_returns_zero_counts(self, monkeypatch):
        self._setup_check(monkeypatch, apps=[])
        req = CheckRequest(subscription_id="sub-123")
        result = tr.check(req)
        assert result["new_application_count"] == 0
        assert result["total_nearby"] == 0
        assert result["new_applications"] == []

    def test_check_property_context_included(self, monkeypatch):
        self._setup_check(monkeypatch)
        req = CheckRequest(subscription_id="sub-123")
        result = tr.check(req)
        assert result["property_context"]["zone"] == "R2"

    def test_check_null_inputs_handled(self, monkeypatch):
        """Sub row with inputs=None should not crash."""
        sub = _subscription_row()
        sub["inputs"] = None
        conn, cur = _fake_conn(fetchone_val=sub)
        monkeypatch.setattr(tr, "_get_conn", lambda: conn)
        monkeypatch.setattr(
            tr, "_lookup_property_context",
            lambda lat, lng: {"zone": None, "tod_precinct": None, "tod_type": None},
        )
        from fastapi import HTTPException
        req = CheckRequest(subscription_id="sub-123")
        # council_name will be "" from `inputs.get("council_name") or ""`
        with pytest.raises(HTTPException) as exc_info:
            tr.check(req)
        assert exc_info.value.status_code == 422

    def test_check_app_without_planning_portal_number_uses_application_number(self, monkeypatch):
        """Falls back to ApplicationNumber when PlanningPortalApplicationNumber is missing."""
        app = _da_app("DA/FALLBACK/001", lat=-33.87, lng=151.21)
        app["PlanningPortalApplicationNumber"] = None
        app["ApplicationNumber"] = "AN/001"
        self._setup_check(monkeypatch, apps=[app])
        req = CheckRequest(subscription_id="sub-123")
        result = tr.check(req)
        assert result["new_application_count"] == 1

    def test_check_app_with_no_number_not_deduped(self, monkeypatch):
        """App with empty string number should not be added to seen."""
        app = _da_app("", lat=-33.87, lng=151.21)
        app["PlanningPortalApplicationNumber"] = ""
        app["ApplicationNumber"] = ""
        self._setup_check(monkeypatch, apps=[app])
        req = CheckRequest(subscription_id="sub-123")
        result = tr.check(req)
        # Empty number → `if num and num not in seen` → False, not appended
        assert result["new_application_count"] == 0

    def test_check_subscription_id_in_response(self, monkeypatch):
        self._setup_check(monkeypatch)
        req = CheckRequest(subscription_id="sub-123")
        result = tr.check(req)
        assert result["subscription_id"] == "sub-123"

    def test_check_address_from_subscription(self, monkeypatch):
        sub = _subscription_row(address="42 Custom Rd")
        self._setup_check(monkeypatch, sub_row=sub)
        req = CheckRequest(subscription_id="sub-123")
        result = tr.check(req)
        assert result["address"] == "42 Custom Rd"


# ---------------------------------------------------------------------------
# list_subscriptions endpoint
# ---------------------------------------------------------------------------

class TestListSubscriptions:
    def test_returns_subscriptions_list(self, monkeypatch):
        conn, cur = _fake_conn(rows=[
            {"id": "1", "address": "10 Test St", "email": "a@b.com", "lat": -33.87, "lng": 151.21},
            {"id": "2", "address": "20 Test St", "email": "c@d.com", "lat": -33.88, "lng": 151.22},
        ])
        monkeypatch.setattr(tr, "_get_conn", lambda: conn)
        result = tr.list_subscriptions()
        assert len(result["subscriptions"]) == 2
        assert result["subscriptions"][0]["id"] == "1"
        assert result["subscriptions"][1]["address"] == "20 Test St"

    def test_empty_subscriptions(self, monkeypatch):
        conn, cur = _fake_conn(rows=[])
        monkeypatch.setattr(tr, "_get_conn", lambda: conn)
        result = tr.list_subscriptions()
        assert result["subscriptions"] == []

    def test_conn_closed(self, monkeypatch):
        conn, cur = _fake_conn(rows=[])
        monkeypatch.setattr(tr, "_get_conn", lambda: conn)
        tr.list_subscriptions()
        conn.close.assert_called_once()

    def test_result_is_dict_not_realdict(self, monkeypatch):
        """Ensure rows are converted to plain dicts."""
        row = MagicMock()
        row.__iter__ = MagicMock(return_value=iter([("id", "1"), ("address", "x")]))
        row.keys = MagicMock(return_value=["id", "address"])
        row.__getitem__ = lambda self, k: {"id": "1", "address": "x"}[k]

        conn, cur = _fake_conn(rows=[{"id": "1", "address": "x", "email": "e@f.com", "lat": -33.0, "lng": 151.0}])
        monkeypatch.setattr(tr, "_get_conn", lambda: conn)
        result = tr.list_subscriptions()
        assert isinstance(result["subscriptions"][0], dict)


# ---------------------------------------------------------------------------
# Constants (mutmut likes to change these)
# ---------------------------------------------------------------------------

class TestConstants:
    def test_alert_radius_is_200(self):
        assert ALERT_RADIUS_M == 200

    def test_window_days_is_8(self):
        assert WINDOW_DAYS == 8

    def test_da_url_correct(self):
        assert DA_URL == "https://api.apps1.nsw.gov.au/eplanning/data/v0/OnlineDA"

    def test_cdc_url_correct(self):
        assert CDC_URL == "https://api.apps1.nsw.gov.au/eplanning/data/v0/OnlineCDC"


# ---------------------------------------------------------------------------
# SubscribeRequest model
# ---------------------------------------------------------------------------

class TestSubscribeRequestModel:
    def test_prop_id_defaults_to_none(self):
        req = SubscribeRequest(
            address="x", lat=0, lng=0, email="a@b.com", council_name="test"
        )
        assert req.prop_id is None

    def test_all_fields_set(self):
        req = SubscribeRequest(
            address="1 Main St", prop_id="LOT1", lat=-33.5, lng=151.0,
            email="test@example.com", council_name="Inner West"
        )
        assert req.address == "1 Main St"
        assert req.prop_id == "LOT1"
        assert req.lat == -33.5
        assert req.lng == 151.0
        assert req.email == "test@example.com"
        assert req.council_name == "Inner West"


# ---------------------------------------------------------------------------
# _filter_nearby — additional mutation-killing tests
# ---------------------------------------------------------------------------

class TestFilterNearbyMutationKillers:
    """Tests designed to kill specific mutants that survive in _filter_nearby."""

    def test_lat_only_zero_is_not_skipped(self):
        """App at lat=0 but valid lng should NOT be skipped (it's on the equator).
        Kills mutant: `if alat != 0 and alng == 0` and `if alat == 0 or alng == 0`."""
        from services.threat_radar import _filter_nearby
        # Subject is at equator — app at same location should be found
        app = {"Latitude": "0.0001", "Longitude": "0.0001", "Location": [{"Y": "0.0001", "X": "0.0001"}],
               "PlanningPortalApplicationNumber": "EQ1"}
        result = _filter_nearby([app], 0.0001, 0.0001)
        assert len(result) == 1

    def test_lng_only_zero_is_not_skipped(self):
        """App at lng=0 (prime meridian) but valid lat should NOT be skipped.
        Kills mutant: `if alat == 0 and alng != 0` and `if alat == 0 or alng == 0`."""
        from services.threat_radar import _filter_nearby
        app = {"Latitude": "51.5", "Longitude": "0.0001", "Location": [{"Y": "51.5", "X": "0.0001"}],
               "PlanningPortalApplicationNumber": "PM1"}
        result = _filter_nearby([app], 51.5, 0.0001)
        assert len(result) == 1

    def test_both_zero_is_skipped(self):
        """App at exactly (0,0) must be skipped — null island.
        Kills mutant: `if alat == 1 and alng == 0`."""
        from services.threat_radar import _filter_nearby
        app = {"Latitude": "0", "Longitude": "0", "Location": [{"Y": "0", "X": "0"}],
               "PlanningPortalApplicationNumber": "NULL1"}
        result = _filter_nearby([app], 0.0, 0.0)
        assert len(result) == 0

    def test_continue_vs_break_with_multiple_apps(self):
        """Zero-coord app followed by valid app — both must be processed.
        Kills mutant: `continue` → `break`."""
        from services.threat_radar import _filter_nearby
        apps = [
            {"Latitude": "0", "Longitude": "0", "PlanningPortalApplicationNumber": "SKIP"},
            {"Latitude": "-33.87", "Longitude": "151.21", "PlanningPortalApplicationNumber": "KEEP",
             "Location": [{"Y": "-33.87", "X": "151.21"}]},
        ]
        result = _filter_nearby(apps, -33.87, 151.21)
        assert len(result) == 1
        assert result[0]["PlanningPortalApplicationNumber"] == "KEEP"

    def test_distance_boundary_at_exactly_radius(self):
        """App at exactly ALERT_RADIUS_M should be included (<=, not <).
        Kills mutant: `d <= ALERT_RADIUS_M` → `d < ALERT_RADIUS_M`."""
        from services.threat_radar import _filter_nearby, _haversine, ALERT_RADIUS_M
        # Find a lat offset that gives exactly ~200m
        # 200m ≈ 0.0018° latitude at Sydney
        base_lat, base_lng = -33.87, 151.21
        # Binary search for exact boundary
        lo, hi = 0.0017, 0.0019
        for _ in range(50):
            mid = (lo + hi) / 2
            d = _haversine(base_lat, base_lng, base_lat + mid, base_lng)
            if d < ALERT_RADIUS_M:
                lo = mid
            else:
                hi = mid
        # Use lo — just under the boundary (guaranteed <=)
        app_lat = base_lat + lo
        app = {"Latitude": str(app_lat), "Longitude": str(base_lng),
               "Location": [{"Y": str(app_lat), "X": str(base_lng)}],
               "PlanningPortalApplicationNumber": "BOUNDARY"}
        result = _filter_nearby([app], base_lat, base_lng)
        assert len(result) == 1

    def test_latitude_key_used_over_location_when_present(self):
        """When Latitude key is present and non-None, it should be used (not Location fallback).
        Kills mutant: `app.get("XXLatitudeXX")` → falls through to loc.get("Y")."""
        from services.threat_radar import _filter_nearby
        # Latitude says "nearby", Location says "far away"
        app = {
            "Latitude": "-33.87",
            "Longitude": "151.21",
            "Location": [{"Y": "0", "X": "0"}],  # Would be null-island (skipped)
            "PlanningPortalApplicationNumber": "LATPRIO",
        }
        result = _filter_nearby([app], -33.87, 151.21)
        assert len(result) == 1
        assert result[0]["PlanningPortalApplicationNumber"] == "LATPRIO"

    def test_longitude_key_used_over_location_when_present(self):
        """When Longitude key is present and non-None, it should be used.
        Kills mutant: `app.get("XXLongitudeXX")` → falls through to loc.get("X")."""
        from services.threat_radar import _filter_nearby
        # Longitude says "nearby", Location X says "far"
        app = {
            "Latitude": "-33.87",
            "Longitude": "151.21",
            "Location": [{"Y": "-33.87", "X": "0"}],  # X=0 but Longitude overrides
            "PlanningPortalApplicationNumber": "LNGPRIO",
        }
        result = _filter_nearby([app], -33.87, 151.21)
        assert len(result) == 1

    def test_distance_rounded_to_one_decimal(self):
        """_distance_m should be rounded to 1 decimal place.
        Kills mutant: `round(d, 1)` → `round(d, 2)`."""
        from services.threat_radar import _filter_nearby
        app = {"Latitude": "-33.8701", "Longitude": "151.21",
               "Location": [{"Y": "-33.8701", "X": "151.21"}],
               "PlanningPortalApplicationNumber": "RND"}
        result = _filter_nearby([app], -33.87, 151.21)
        assert len(result) == 1
        dist_str = str(result[0]["_distance_m"])
        # Should have at most 1 decimal place
        if "." in dist_str:
            assert len(dist_str.split(".")[1]) <= 1
