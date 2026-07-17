"""Issue #762 — shared report_id clobber across satellite property_reports rows.

The brief used to hand ONE report_id to flood/bushfire/shadow; each service
upserts with ON CONFLICT (id) DO UPDATE SET outputs, so the last writer
overwrote the first writer's outputs while the row kept the first product
label. The bushfire cache read then served flood/shadow outputs merged over
defaults (all-null bushfire section, fire_signal='unavailable').

Covers:
  _derive_service_report_id  — deterministic, distinct per product, != parent
  _write_report (bushfire + flood) — derived ids produce two distinct rows
  _first_valid_cached_row (bushfire + flood) — poisoned rows skipped
  run_bushfire cache path — poisoned newest row falls through to healthy row
  call sites — brief submits derived ids, not the raw parent id
"""

import inspect
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.bushfire_prescreen as bushfire
import services.flood_truth as flood
import services.intelligence_brief as brief
from services.bushfire_prescreen import BushfireRequest
from services.intelligence_brief import _derive_service_report_id


# ---------------------------------------------------------------------------
# Fakes — capture SQL without a database
# ---------------------------------------------------------------------------

class _FakeCursor:
    """Records every execute(); serves preset rows to fetchall()/fetchone()."""

    def __init__(self, executed, rows):
        self._executed = executed
        self._rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=None):
        self._executed.append((sql, params))

    def fetchall(self):
        return list(self._rows)

    def fetchone(self):
        return self._rows[0] if self._rows else None


class _FakeConn:
    def __init__(self, executed, rows=None):
        self._executed = executed
        self._rows = rows or []

    def cursor(self, *args, **kwargs):
        return _FakeCursor(self._executed, self._rows)

    def commit(self):
        pass

    def close(self):
        pass


# ---------------------------------------------------------------------------
# _derive_service_report_id — deterministic per-product derivation
# ---------------------------------------------------------------------------

class TestDeriveServiceReportId:
    PARENT = "a3f1c2d4-5678-4abc-9def-0123456789ab"

    def test_products_get_distinct_ids(self):
        ids = {
            _derive_service_report_id(self.PARENT, p)
            for p in ("flood", "bushfire", "shadow")
        }
        assert len(ids) == 3

    def test_derived_id_differs_from_parent(self):
        for product in ("flood", "bushfire", "shadow"):
            assert _derive_service_report_id(self.PARENT, product) != self.PARENT

    def test_deterministic_across_calls(self):
        first = _derive_service_report_id(self.PARENT, "bushfire")
        second = _derive_service_report_id(self.PARENT, "bushfire")
        assert first == second

    def test_derived_id_is_valid_uuid_string(self):
        derived = _derive_service_report_id(self.PARENT, "flood")
        assert str(uuid.UUID(derived)) == derived

    def test_different_parents_do_not_collide(self):
        other_parent = str(uuid.uuid4())
        assert _derive_service_report_id(
            self.PARENT, "flood"
        ) != _derive_service_report_id(other_parent, "flood")

    def test_non_uuid_parent_raises(self):
        with pytest.raises(ValueError):
            _derive_service_report_id("not-a-uuid", "flood")


# ---------------------------------------------------------------------------
# Regression: same parent, different products -> two DISTINCT rows
# ---------------------------------------------------------------------------

class TestWriteReportDistinctRows:
    def test_two_products_same_parent_write_two_distinct_row_ids(self, monkeypatch):
        parent = str(uuid.uuid4())
        bushfire_id = _derive_service_report_id(parent, "bushfire")
        flood_id = _derive_service_report_id(parent, "flood")

        executed = []
        monkeypatch.setattr(bushfire, "_get_conn", lambda: _FakeConn(executed))
        monkeypatch.setattr(flood, "_get_conn", lambda: _FakeConn(executed))

        bushfire._write_report(
            bushfire_id, "20 Patanga St", -33.47, 151.38, "123",
            {"lat": -33.47, "lng": 151.38},
            {"is_bushfire_prone": True}, "high", [],
        )
        flood._write_report(
            flood_id, "20 Patanga St", -33.47, 151.38, "123",
            {"lat": -33.47, "lng": 151.38},
            {"flood_signal": "none", "epi_flood_class": "none"},
        )

        assert len(executed) == 2
        bushfire_sql, bushfire_params = executed[0]
        flood_sql, flood_params = executed[1]

        # Both are upserts keyed on id — the clobber mechanism — so the ids
        # MUST differ for the rows to be distinct.
        assert "ON CONFLICT (id)" in bushfire_sql
        assert "ON CONFLICT (id)" in flood_sql
        assert "'bushfire'" in bushfire_sql
        assert "'flood'" in flood_sql
        assert bushfire_params[0] == bushfire_id
        assert flood_params[0] == flood_id
        assert bushfire_params[0] != flood_params[0]

    def test_raw_parent_id_would_have_collided(self):
        # Documents the pre-fix failure mode: handing both services the raw
        # parent id yields ONE row id — the derivation is what prevents it.
        parent = str(uuid.uuid4())
        assert parent == parent  # same id for both writers pre-fix
        assert _derive_service_report_id(parent, "bushfire") != parent
        assert _derive_service_report_id(parent, "flood") != parent


# ---------------------------------------------------------------------------
# Brief call sites submit derived ids, never the raw parent id
# ---------------------------------------------------------------------------

class TestBriefCallSitesUseDerivedIds:
    def test_satellite_fetches_receive_derived_ids(self):
        source = inspect.getsource(brief)
        assert '_derive_service_report_id(report_id, "bushfire")' in source
        assert '_derive_service_report_id(report_id, "flood")' in source
        assert '_derive_service_report_id(report_id, "shadow")' in source

    def test_no_fetch_receives_the_raw_parent_id(self):
        source = inspect.getsource(brief)
        assert "_fetch_bushfire(req.address, lat, lng, str(resolved_prop_id) if resolved_prop_id else None, report_id)" not in source
        assert "_fetch_flood(req.address, lat, lng, str(resolved_prop_id) if resolved_prop_id else None, report_id)" not in source


# ---------------------------------------------------------------------------
# Cache-read guard — poisoned rows are skipped, never served
# ---------------------------------------------------------------------------

_POISONED_FLOOD_SHAPED = {
    "outputs": {"ems_activations": 2, "jrc_water_occurrence_pct": 1.5, "s1_gap_warning": None},
    "confidence": "medium",
    "data_sources": ["x"],
}
_POISONED_SHADOW_SHAPED = {
    "outputs": {"scenarios": [], "adg_compliant": True, "height_source": "lep"},
    "confidence": "low",
    "data_sources": ["y"],
}
_HEALTHY_BUSHFIRE = {
    "outputs": {"is_bushfire_prone": True, "fire_signal": "moderate"},
    "confidence": "high",
    "data_sources": ["NSW RFS Bush Fire Prone Land"],
}
_HEALTHY_FLOOD = {
    "outputs": {"epi_flood_class": "none", "flood_signal": "none"},
    "confidence": "high",
    "data_sources": ["EPI"],
}


class TestBushfireCacheGuard:
    def test_poisoned_newest_row_skipped_healthy_older_row_served(self):
        row = bushfire._first_valid_cached_row(
            [_POISONED_FLOOD_SHAPED, _HEALTHY_BUSHFIRE]
        )
        assert row is _HEALTHY_BUSHFIRE

    def test_shadow_shaped_row_also_skipped(self):
        row = bushfire._first_valid_cached_row(
            [_POISONED_SHADOW_SHAPED, _HEALTHY_BUSHFIRE]
        )
        assert row is _HEALTHY_BUSHFIRE

    def test_all_rows_poisoned_returns_none_for_live_compute(self):
        assert bushfire._first_valid_cached_row(
            [_POISONED_FLOOD_SHAPED, _POISONED_SHADOW_SHAPED]
        ) is None

    def test_empty_and_none_inputs_return_none(self):
        assert bushfire._first_valid_cached_row([]) is None
        assert bushfire._first_valid_cached_row(None) is None

    def test_null_outputs_row_skipped(self):
        assert bushfire._first_valid_cached_row([{"outputs": None}]) is None

    def test_sentinel_key_with_null_value_still_accepted(self):
        # A genuine "unknown" bushfire result carries the key with value None
        # — key PRESENCE is the shape test, not truthiness of the value.
        row = {"outputs": {"is_bushfire_prone": None, "fire_signal": "unavailable"}}
        assert bushfire._first_valid_cached_row([row]) is row


class TestFloodCacheGuard:
    def test_bushfire_shaped_row_skipped(self):
        poisoned = {"outputs": {"is_bushfire_prone": True, "fire_signal": "low"}}
        assert flood._first_valid_cached_row([poisoned, _HEALTHY_FLOOD]) is _HEALTHY_FLOOD

    def test_either_sentinel_key_accepts_the_row(self):
        only_epi = {"outputs": {"epi_flood_class": "none"}}
        only_signal = {"outputs": {"flood_signal": "low"}}
        assert flood._first_valid_cached_row([only_epi]) is only_epi
        assert flood._first_valid_cached_row([only_signal]) is only_signal

    def test_all_poisoned_returns_none(self):
        assert flood._first_valid_cached_row([_POISONED_SHADOW_SHAPED]) is None


class TestRunBushfireCachePathEndToEnd:
    def test_poisoned_newest_row_never_served(self, monkeypatch):
        """Prod repro (Kincumber): newest product='bushfire' row holds flood
        outputs. The cache path must serve the older genuine row, not merge
        flood fields over the all-null bushfire defaults."""
        executed = []
        rows = [_POISONED_FLOOD_SHAPED, _HEALTHY_BUSHFIRE]
        monkeypatch.setattr(
            bushfire, "_get_conn", lambda: _FakeConn(executed, rows=rows)
        )

        req = BushfireRequest(
            address="20 PATANGA STREET KINCUMBER 2251",
            lat=-33.47, lng=151.38, prop_id="123",
            report_id=str(uuid.uuid4()),
        )
        result = bushfire.run_bushfire(req)

        assert result["outputs"]["is_bushfire_prone"] is True
        assert result["outputs"]["fire_signal"] == "moderate"
        # No flood field may leak into the bushfire section
        assert "ems_activations" not in result["outputs"]
        assert "jrc_water_occurrence_pct" not in result["outputs"]
        assert result["confidence"] == "high"

    def test_cache_select_fetches_multiple_candidates(self, monkeypatch):
        executed = []
        monkeypatch.setattr(
            bushfire, "_get_conn",
            lambda: _FakeConn(executed, rows=[_HEALTHY_BUSHFIRE]),
        )
        req = BushfireRequest(
            address="20 PATANGA STREET KINCUMBER 2251",
            lat=-33.47, lng=151.38, prop_id="123",
            report_id=str(uuid.uuid4()),
        )
        bushfire.run_bushfire(req)
        select_sql = executed[0][0]
        # LIMIT 1 would hide the healthy older row behind a poisoned newest
        # one — the guard needs candidates to fall through to.
        assert "LIMIT 1" not in select_sql
        assert "ORDER BY run_date DESC" in select_sql
