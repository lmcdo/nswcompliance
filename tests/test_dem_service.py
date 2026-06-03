"""
Unit tests for services/dem_service.py.

Pure-logic functions + mocked HTTP calls — no network, no native deps.

Covers:
  _buffer_to_degrees    — metric buffer → lat/lng degree conversion
  _is_tiff              — GeoTIFF magic byte detection
  _fetch_ga_wcs         — GA WCS primary fetch (mocked HTTP)
  _fetch_sixmaps        — NSW SIX Maps fallback (mocked HTTP)
  fetch_dem_region      — orchestration: GA → SIX Maps → RuntimeError
"""

import io
import math
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.dem_service import (
    _buffer_to_degrees,
    _is_tiff,
    _fetch_ga_wcs,
    _fetch_sixmaps,
    fetch_dem_region,
    _TIFF_LE,
    _TIFF_BE,
    _M_PER_DEG_LAT,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Minimal valid GeoTIFF: TIFF LE magic + enough padding
FAKE_TIFF = _TIFF_LE + b"\x00" * 100


class MockResponse:
    """Minimal requests.Response stand-in."""

    def __init__(self, content: bytes, status_code: int = 200, content_type: str = "image/tiff"):
        self.content = content
        self.status_code = status_code
        self.headers = {"Content-Type": content_type}
        self.ok = 200 <= status_code < 400

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(f"HTTP {self.status_code}")


# ---------------------------------------------------------------------------
# _buffer_to_degrees
# ---------------------------------------------------------------------------


class TestBufferToDegrees:
    def test_equator(self):
        d_lat, d_lng = _buffer_to_degrees(0.0, 1000.0)
        assert pytest.approx(d_lat, rel=1e-3) == 1000.0 / _M_PER_DEG_LAT
        # At equator cos(0)=1, so d_lng == d_lat
        assert pytest.approx(d_lng, rel=1e-3) == d_lat

    def test_sydney_latitude(self):
        """At -33.87° latitude, d_lng should be larger than d_lat."""
        d_lat, d_lng = _buffer_to_degrees(-33.87, 500.0)
        assert d_lat > 0
        assert d_lng > d_lat  # cos(33.87°) < 1 → d_lng > d_lat

    def test_zero_buffer(self):
        d_lat, d_lng = _buffer_to_degrees(-33.87, 0.0)
        assert d_lat == 0.0
        assert d_lng == 0.0

    def test_high_latitude(self):
        """Near poles, d_lng should be much larger than d_lat."""
        d_lat, d_lng = _buffer_to_degrees(-80.0, 500.0)
        assert d_lng > d_lat * 3


# ---------------------------------------------------------------------------
# _is_tiff
# ---------------------------------------------------------------------------


class TestIsTiff:
    def test_little_endian(self):
        assert _is_tiff(_TIFF_LE + b"\x00" * 10) is True

    def test_big_endian(self):
        assert _is_tiff(_TIFF_BE + b"\x00" * 10) is True

    def test_not_tiff(self):
        assert _is_tiff(b"<?xml version") is False

    def test_empty(self):
        assert _is_tiff(b"") is False

    def test_short(self):
        assert _is_tiff(b"II*") is False  # only 3 bytes

    def test_json_response(self):
        assert _is_tiff(b'{"error":"not found"}') is False


# ---------------------------------------------------------------------------
# _fetch_ga_wcs (mocked)
# ---------------------------------------------------------------------------


class TestFetchGaWcs:
    def test_success_v1(self, monkeypatch):
        """WCS 1.0.0 returns valid TIFF → BytesIO returned."""
        import requests as req_mod

        monkeypatch.setattr(req_mod, "get", lambda *a, **kw: MockResponse(FAKE_TIFF))
        result = _fetch_ga_wcs(-33.87, 151.21, 500.0, timeout=5)
        assert result is not None
        assert isinstance(result, io.BytesIO)
        assert result.read(4) == _TIFF_LE

    def test_v1_rejected_falls_to_v2(self, monkeypatch):
        """WCS 1.0.0 returns 400 → falls back to 2.0.1."""
        import requests as req_mod

        call_count = {"n": 0}

        def mock_get(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return MockResponse(b"<error/>", status_code=400)
            return MockResponse(FAKE_TIFF)

        monkeypatch.setattr(req_mod, "get", mock_get)
        result = _fetch_ga_wcs(-33.87, 151.21, 500.0, timeout=5)
        assert result is not None
        assert call_count["n"] == 2

    def test_both_versions_fail(self, monkeypatch):
        """Both WCS versions fail → returns None."""
        import requests as req_mod

        monkeypatch.setattr(
            req_mod, "get",
            lambda *a, **kw: MockResponse(b"<error/>", status_code=500),
        )
        result = _fetch_ga_wcs(-33.87, 151.21, 500.0, timeout=5)
        assert result is None

    def test_non_tiff_response(self, monkeypatch):
        """Server returns 200 but content is not TIFF → returns None."""
        import requests as req_mod

        monkeypatch.setattr(
            req_mod, "get",
            lambda *a, **kw: MockResponse(b'{"error":"coverage not found"}', status_code=200, content_type="application/json"),
        )
        result = _fetch_ga_wcs(-33.87, 151.21, 500.0, timeout=5)
        assert result is None

    def test_timeout(self, monkeypatch):
        """Network timeout → returns None."""
        import requests as req_mod

        def raise_timeout(*a, **kw):
            raise req_mod.RequestException("Connection timed out")

        monkeypatch.setattr(req_mod, "get", raise_timeout)
        result = _fetch_ga_wcs(-33.87, 151.21, 500.0, timeout=1)
        assert result is None


# ---------------------------------------------------------------------------
# _fetch_sixmaps (mocked)
# ---------------------------------------------------------------------------


class TestFetchSixmaps:
    def test_success(self, monkeypatch):
        import requests as req_mod

        monkeypatch.setattr(req_mod, "get", lambda *a, **kw: MockResponse(FAKE_TIFF))
        result = _fetch_sixmaps(-33.87, 151.21, 500.0, timeout=5)
        assert result is not None
        assert isinstance(result, io.BytesIO)

    def test_non_tiff(self, monkeypatch):
        import requests as req_mod

        monkeypatch.setattr(
            req_mod, "get",
            lambda *a, **kw: MockResponse(b"PNG image data", content_type="image/png"),
        )
        result = _fetch_sixmaps(-33.87, 151.21, 500.0, timeout=5)
        assert result is None

    def test_server_error(self, monkeypatch):
        import requests as req_mod

        def raise_err(*a, **kw):
            raise req_mod.RequestException("503 Service Unavailable")

        monkeypatch.setattr(req_mod, "get", raise_err)
        result = _fetch_sixmaps(-33.87, 151.21, 500.0, timeout=5)
        assert result is None


# ---------------------------------------------------------------------------
# fetch_dem_region (orchestration)
# ---------------------------------------------------------------------------


class TestFetchDemRegion:
    def test_ga_success_no_fallback(self, monkeypatch):
        """GA WCS succeeds → SIX Maps never called."""
        import services.dem_service as mod

        monkeypatch.setattr(mod, "_fetch_ga_wcs", lambda *a, **kw: io.BytesIO(FAKE_TIFF))
        sixmaps_called = {"called": False}
        original = mod._fetch_sixmaps

        def spy(*a, **kw):
            sixmaps_called["called"] = True
            return original(*a, **kw)

        monkeypatch.setattr(mod, "_fetch_sixmaps", spy)

        result = fetch_dem_region(-33.87, 151.21, 500.0, timeout=5)
        assert isinstance(result, io.BytesIO)
        assert sixmaps_called["called"] is False

    def test_ga_fails_sixmaps_succeeds(self, monkeypatch):
        """GA WCS returns None → SIX Maps fallback succeeds."""
        import services.dem_service as mod

        monkeypatch.setattr(mod, "_fetch_ga_wcs", lambda *a, **kw: None)
        monkeypatch.setattr(mod, "_fetch_sixmaps", lambda *a, **kw: io.BytesIO(FAKE_TIFF))

        result = fetch_dem_region(-33.87, 151.21, 500.0, timeout=5)
        assert isinstance(result, io.BytesIO)

    def test_both_fail_raises(self, monkeypatch):
        """Both sources fail → RuntimeError."""
        import services.dem_service as mod

        monkeypatch.setattr(mod, "_fetch_ga_wcs", lambda *a, **kw: None)
        monkeypatch.setattr(mod, "_fetch_sixmaps", lambda *a, **kw: None)

        with pytest.raises(RuntimeError, match="DEM fetch failed"):
            fetch_dem_region(-33.87, 151.21, 500.0, timeout=5)
