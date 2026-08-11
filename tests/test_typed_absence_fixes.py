"""Typed-absence fixes 2 and 3 (output-grounding, 2026-08-03) — falsifiable pins.

Fix 3 — services/conveyancing._fetch_pdf_db_data: one try-block previously
covered DAs + LEP clauses + DCP setbacks + heritage, so an exception mid-way
left the later results empty and the paid PDF rendered empty-as-absent
(absence census row 1). The pins here FAIL on that code: a mid-failure must
leave the OTHER fetches intact and report itself in the per-fetch failed map.

Fix 2 — cache staleness: conveyancing's pipeline cache gains a 24h max age
(expired entry = miss → full re-run), and flood_truth._write_report accepts
the ORIGINAL run_date so a cached flood result never wears today's date.

Test style follows tests/test_conveyancing_da_threestate.py: patch
psycopg2.connect with a fake connection; no real DB is touched.
"""

import sys
from datetime import date, datetime
from pathlib import Path

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "services"))
sys.path.insert(0, str(_ROOT / "scripts"))
sys.path.insert(0, str(_ROOT))

import psycopg2  # noqa: E402  (may be the conftest stub; connect is patched)

import conveyancing  # noqa: E402

_LAT, _LNG = -33.8, 151.2
_CONTROLS_WITH_CLAUSE = {"key_sites_clause": "cl 6.15", "zone_epi": "X LEP 2013",
                         "zone": "R2"}


class _FakeCursor:
    def __init__(self, rows=None):
        self._rows = rows or []
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _FakeConn:
    def __init__(self, cursor=None):
        self.autocommit = False
        self._cursor = cursor or _FakeCursor()

    def cursor(self, *a, **k):
        return self._cursor

    def commit(self):
        pass

    def close(self):
        pass


def _patch_connect(monkeypatch, conn=None):
    monkeypatch.setattr(psycopg2, "connect", lambda *a, **k: conn or _FakeConn())


# ───────────────────────────── fix 3: _fetch_pdf_db_data ─────────────────────

class TestFetchPdfDbDataSplit:
    URL = "postgresql://unused"

    def test_mid_failure_leaves_other_fetches_intact(self, monkeypatch):
        """THE fix-3 pin: the LEP query raising must NOT empty the DCP and
        heritage results. On the old single-try code, this exact setup
        returned _dcp=None and empty heritage with nothing marked failed —
        empty-rendered-as-absent."""
        _patch_connect(monkeypatch)
        monkeypatch.setattr(conveyancing, "fetch_nearby_das", lambda *a, **k: [{"id": 1}])

        def _lep_boom(*a, **k):
            raise RuntimeError("LEP table exploded")

        monkeypatch.setattr(conveyancing, "fetch_lep_clauses", _lep_boom)
        monkeypatch.setattr(conveyancing, "fetch_dcp_setbacks",
                            lambda *a, **k: {"dcp_name": "X DCP", "setbacks": []})
        monkeypatch.setattr(conveyancing, "fetch_heritage_postgis",
                            lambda *a, **k: {"hca": ["HCA1"], "items": [],
                                             "has_heritage": True, "raw": []})

        das, lep, dcp, heritage, failed = conveyancing._fetch_pdf_db_data(
            self.URL, _LAT, _LNG, None, _CONTROLS_WITH_CLAUSE, "marrickville",
        )
        assert das == [{"id": 1}] and failed["das"] is False
        assert lep == [] and failed["lep"] is True          # failed, typed
        assert dcp == {"dcp_name": "X DCP", "setbacks": []}  # survived
        assert failed["dcp"] is False
        assert heritage["has_heritage"] is True              # survived
        assert failed["heritage"] is False

    def test_connection_failure_fails_every_applicable_fetch(self, monkeypatch):
        def _no_conn(*a, **k):
            raise RuntimeError("connect refused")

        monkeypatch.setattr(psycopg2, "connect", _no_conn)
        das, lep, dcp, heritage, failed = conveyancing._fetch_pdf_db_data(
            self.URL, _LAT, _LNG, None, _CONTROLS_WITH_CLAUSE, "marrickville",
        )
        assert das is None
        assert failed == {"das": True, "lep": True, "dcp": True, "heritage": True}

    def test_all_ok_reports_nothing_failed(self, monkeypatch):
        _patch_connect(monkeypatch)
        monkeypatch.setattr(conveyancing, "fetch_nearby_das", lambda *a, **k: [])
        monkeypatch.setattr(conveyancing, "fetch_lep_clauses", lambda *a, **k: [])
        monkeypatch.setattr(conveyancing, "fetch_dcp_setbacks", lambda *a, **k: None)
        monkeypatch.setattr(conveyancing, "fetch_heritage_postgis",
                            lambda *a, **k: {"hca": [], "items": [],
                                             "has_heritage": False, "raw": []})
        das, lep, dcp, heritage, failed = conveyancing._fetch_pdf_db_data(
            self.URL, _LAT, _LNG, None, _CONTROLS_WITH_CLAUSE, "marrickville",
        )
        assert das == []                                     # genuine zero, not None
        assert failed == {"das": False, "lep": False, "dcp": False,
                          "heritage": False}

    def test_not_applicable_fetches_are_not_failed(self, monkeypatch):
        """No key_sites_clause and no DCP council: lep/dcp were never due to
        run — N/A must not read as failed (three states, never two)."""
        _patch_connect(monkeypatch)
        monkeypatch.setattr(conveyancing, "fetch_nearby_das", lambda *a, **k: [])
        monkeypatch.setattr(conveyancing, "fetch_heritage_postgis",
                            lambda *a, **k: {"hca": [], "items": [],
                                             "has_heritage": False, "raw": []})
        _, _, _, _, failed = conveyancing._fetch_pdf_db_data(
            self.URL, _LAT, _LNG, None, {"zone_epi": "", "zone": ""}, None,
        )
        assert failed["lep"] is False and failed["dcp"] is False


# ───────────────────────────── fix 2: cache max-age ──────────────────────────

class TestPipelineCacheMaxAge:
    def test_expired_entry_is_a_miss(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://unused")
        cur = _FakeCursor(rows=[({"controls": {}}, True)])   # expired=True
        _patch_connect(monkeypatch, _FakeConn(cur))
        assert conveyancing._load_pipeline_cache("r1") is None
        # And the age policy actually reached the SQL:
        assert "expired" in cur.executed[0][0]
        assert conveyancing._PIPELINE_CACHE_MAX_AGE_HOURS in cur.executed[0][1]

    def test_fresh_entry_is_served(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://unused")
        cur = _FakeCursor(rows=[({"controls": {"zone": "R2"}}, False)])
        _patch_connect(monkeypatch, _FakeConn(cur))
        out = conveyancing._load_pipeline_cache("r1")
        assert out == {"controls": {"zone": "R2"}}


class TestFloodRunDateSurvives:
    def test_write_report_carries_original_run_date(self, monkeypatch):
        """THE fix-2 flood pin: a cache-copied row must keep the ORIGINAL
        run_date. On the old signature, _write_report always stamped
        date.today() — a stale result wearing today's date."""
        import flood_truth

        cur = _FakeCursor()
        monkeypatch.setattr(flood_truth, "_get_conn", lambda: _FakeConn(cur))
        original = date(2026, 5, 1)
        flood_truth._write_report(
            "rid", "1 Test St", _LAT, _LNG, None, {}, {}, run_date=original,
        )
        params = cur.executed[0][1]
        assert params[5] == original
        assert params[5] != date.today()

    def test_write_report_defaults_to_today_for_fresh_runs(self, monkeypatch):
        import flood_truth

        cur = _FakeCursor()
        monkeypatch.setattr(flood_truth, "_get_conn", lambda: _FakeConn(cur))
        flood_truth._write_report("rid", "1 Test St", _LAT, _LNG, None, {}, {})
        assert cur.executed[0][1][5] == date.today()


# ─────────────── free-tier confidence sees its own absence state ─────────────

class TestConfidenceSeesAbsence:
    def _full_inputs(self):
        controls = {"zone": "R2", "height": "9.5", "fsr": "0.5"}
        valuation = {"lot_area_m2": 500}
        overlays = [{"layer_type": "flood"}]
        covered = ["flood", "riparian", "wetlands", "landslide", "biodiversity"]
        return controls, overlays, valuation, covered

    def test_one_failure_caps_high_to_medium(self):
        controls, overlays, valuation, covered = self._full_inputs()
        base = conveyancing._compute_confidence(
            controls, overlays, valuation, covered_layers=covered)
        assert base == "high"
        capped = conveyancing._compute_confidence(
            controls, overlays, valuation, covered_layers=covered,
            live_query_failures=1)
        assert capped == "medium"

    def test_two_failures_cap_to_low(self):
        controls, overlays, valuation, covered = self._full_inputs()
        assert conveyancing._compute_confidence(
            controls, overlays, valuation, covered_layers=covered,
            live_query_failures=2) == "low"
