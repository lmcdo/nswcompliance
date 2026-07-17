"""
Pre-DA history — fail-closed on Tessera coverage gaps (issue #751).

Tests:
  1. _consecutive_covered_pairs math (all / none / sparse / alternating)
  2. check_tessera_coverage — registry-only probe over lot+nbhd bounds
  3. Pre-flight refusal: zero covered pairs refuses BEFORE the heavy run
  4. Refusal marks the pre-allocated async row as errored
  5. Backstop: all-no_data timeline refuses even when pre-flight passed
  6. Pre-flight check failure does NOT refuse — sampling proceeds, backstop guards
  7. Partial coverage (one consecutive pair) completes, not refused
  8. Brief: refused payload → detail None + refusal reason on the DataField
"""
import sys
import types

import numpy as np
import pytest

from services import pre_da_history as pda
from services.pre_da_history import (
    YEARS,
    PreDAHistoryRequest,
    _consecutive_covered_pairs,
    check_tessera_coverage,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

KINCUMBER_LAT, KINCUMBER_LON = -33.4772502, 151.4013914


class _FakeRegistry:
    def __init__(self, covered_years):
        self.covered_years = set(covered_years)
        self.seen_bounds = []

    def iter_tiles_in_region(self, bounds, year):
        self.seen_bounds.append(bounds)
        if year in self.covered_years:
            yield (year, 151.45, -33.45)


class _FakeGT:
    def __init__(self, covered_years=()):
        self.registry = _FakeRegistry(covered_years)


def _install_fake_geotessera(monkeypatch, gt=None, ctor_raises=False):
    """Make ``from geotessera import GeoTessera`` inside the pipeline resolve
    to a stub (the real library is not a test dependency)."""
    mod = types.SimpleNamespace()
    if ctor_raises:
        def _boom():
            raise RuntimeError("geotessera unavailable")
        mod.GeoTessera = _boom
    else:
        mod.GeoTessera = lambda: (gt if gt is not None else _FakeGT())
    monkeypatch.setitem(sys.modules, "geotessera", mod)


def _stub_side_sources(monkeypatch):
    """Cheap deterministic stands-ins for the non-Tessera parallel sources."""
    monkeypatch.setattr(pda, "get_ndvi_ndbi_timeline", lambda lat, lon: {})
    monkeypatch.setattr(pda, "compute_ndvi_ndbi_deltas", lambda raw: {})
    monkeypatch.setattr(pda, "get_da_events", lambda council, addr: [])
    monkeypatch.setattr(pda, "get_pcc_events", lambda council, addr: [])
    monkeypatch.setattr(pda, "check_heritage_flag", lambda lat, lon: {"flag": False})
    monkeypatch.setattr(pda, "log_audit_trail", lambda **kw: None)
    monkeypatch.setattr(
        pda, "geocode_address",
        lambda addr: (KINCUMBER_LAT, KINCUMBER_LON, "Central Coast"),
    )


def _request(report_id=None):
    return PreDAHistoryRequest(
        address="20 PATANGA STREET KINCUMBER 2251", report_id=report_id,
    )


# ---------------------------------------------------------------------------
# 1. Consecutive-pair math
# ---------------------------------------------------------------------------

class TestConsecutiveCoveredPairs:
    def test_full_coverage_yields_all_pairs(self):
        assert _consecutive_covered_pairs(set(YEARS), YEARS) == len(YEARS) - 1

    def test_single_year_yields_zero(self):
        # The live Kincumber case: only 2024 published.
        assert _consecutive_covered_pairs({2024}, YEARS) == 0

    def test_empty_coverage_yields_zero(self):
        assert _consecutive_covered_pairs(set(), YEARS) == 0

    def test_alternating_years_yield_zero(self):
        assert _consecutive_covered_pairs({2018, 2020, 2022, 2024}, YEARS) == 0

    def test_one_adjacent_pair_counts_one(self):
        assert _consecutive_covered_pairs({2020, 2023, 2024}, YEARS) == 1

    def test_covered_year_outside_years_list_ignored(self):
        assert _consecutive_covered_pairs({1999, 2000}, YEARS) == 0


# ---------------------------------------------------------------------------
# 2. Registry probe
# ---------------------------------------------------------------------------

class TestCheckTesseraCoverage:
    def test_reports_only_registry_covered_years(self):
        gt = _FakeGT(covered_years={2023, 2024})
        covered = check_tessera_coverage(gt, KINCUMBER_LAT, KINCUMBER_LON, YEARS)
        assert covered == {2023, 2024}

    def test_bounds_span_lot_and_neighbourhood_points(self):
        gt = _FakeGT(covered_years=set(YEARS))
        check_tessera_coverage(gt, KINCUMBER_LAT, KINCUMBER_LON, YEARS)
        (min_lon, min_lat, max_lon, max_lat) = gt.registry.seen_bounds[0]
        pts = pda._lot_points(KINCUMBER_LAT, KINCUMBER_LON) + pda._nbhd_points(
            KINCUMBER_LAT, KINCUMBER_LON
        )
        for lon, lat in pts:
            assert min_lon <= lon <= max_lon
            assert min_lat <= lat <= max_lat


# ---------------------------------------------------------------------------
# 3/4. Pre-flight refusal
# ---------------------------------------------------------------------------

class TestPreflightRefusal:
    def _refuse_setup(self, monkeypatch):
        _stub_side_sources(monkeypatch)
        _install_fake_geotessera(monkeypatch, gt=_FakeGT(covered_years={2024}))

        def _never_sample(*a, **kw):
            raise AssertionError("heavy sampling ran despite zero covered pairs")

        monkeypatch.setattr(pda, "_sample_embeddings_with_client", _never_sample)

    def test_zero_pairs_refuses_before_sampling(self, monkeypatch):
        self._refuse_setup(monkeypatch)
        result = pda._run_pre_da_history_inner(_request())
        assert result["refused"] is True
        assert result["reason_code"] == "satellite_coverage_unavailable"
        assert result["covered_years"] == [2024]
        assert "timeline" not in result

    def test_refusal_reason_is_prose_not_code(self, monkeypatch):
        self._refuse_setup(monkeypatch)
        result = pda._run_pre_da_history_inner(_request())
        assert "cannot be computed" in result["reason"]

    def test_refusal_marks_async_row_errored(self, monkeypatch):
        self._refuse_setup(monkeypatch)
        marked = {}
        monkeypatch.setattr(
            pda, "_mark_error",
            lambda report_id, msg: marked.update({"id": report_id, "msg": msg}),
        )
        pda._run_pre_da_history_inner(_request(report_id="abc-123"))
        assert marked["id"] == "abc-123"
        assert "cannot be computed" in marked["msg"]


# ---------------------------------------------------------------------------
# 5/6. Backstop gate
# ---------------------------------------------------------------------------

class TestBackstopGate:
    def _all_nan_sampler(self, monkeypatch):
        monkeypatch.setattr(
            pda, "_sample_embeddings_with_client",
            lambda gt, points, years: {y: None for y in years},
        )

    def test_all_no_data_timeline_refuses_not_completes(self, monkeypatch):
        # Pre-flight says covered (registry lies / tiles fail to download) —
        # sampling still yields nothing; the run must NOT store a hollow report.
        _stub_side_sources(monkeypatch)
        _install_fake_geotessera(monkeypatch, gt=_FakeGT(covered_years=set(YEARS)))
        self._all_nan_sampler(monkeypatch)

        def _no_db(*a, **kw):
            raise AssertionError("refused run must not reach the DB write")

        monkeypatch.setattr(pda, "_get_conn", _no_db)
        result = pda._run_pre_da_history_inner(_request())
        assert result["refused"] is True
        assert result["reason_code"] == "satellite_timeline_empty"

    def test_preflight_failure_proceeds_then_backstop_refuses(self, monkeypatch):
        # A broken coverage check is not evidence of a coverage gap: the run
        # proceeds, and the backstop still fails it closed.
        _stub_side_sources(monkeypatch)
        _install_fake_geotessera(monkeypatch, gt=_FakeGT(covered_years=set(YEARS)))
        monkeypatch.setattr(
            pda, "check_tessera_coverage",
            lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("registry down")),
        )
        self._all_nan_sampler(monkeypatch)
        result = pda._run_pre_da_history_inner(_request())
        assert result["refused"] is True
        assert result["reason_code"] == "satellite_timeline_empty"
        assert result["covered_years"] is None


# ---------------------------------------------------------------------------
# 7. Partial coverage completes
# ---------------------------------------------------------------------------

class _FakeCursor:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        pass

    def fetchone(self):
        return ("11111111-2222-3333-4444-555555555555",)


class _FakeConn:
    def cursor(self):
        return _FakeCursor()

    def commit(self):
        pass

    def close(self):
        pass


class TestPartialCoverageCompletes:
    def test_one_consecutive_pair_produces_report(self, monkeypatch):
        _stub_side_sources(monkeypatch)
        _install_fake_geotessera(monkeypatch, gt=_FakeGT(covered_years={2023, 2024}))

        rng = np.random.default_rng(42)
        emb = rng.random(128).astype(np.float32)

        def _sampler(gt, points, years):
            return {y: (emb if y in (2023, 2024) else None) for y in years}

        monkeypatch.setattr(pda, "_sample_embeddings_with_client", _sampler)
        monkeypatch.setattr(pda, "_get_conn", lambda: _FakeConn())

        result = pda._run_pre_da_history_inner(_request())
        assert "refused" not in result
        levels = {e["year"]: e["level"] for e in result["timeline"]}
        assert levels[2024] != "no_data"  # identical embeddings → stable, but data
        assert levels[2023] == "no_data"  # 2022 uncovered → no pair


# ---------------------------------------------------------------------------
# 8. Brief-side reason threading
# ---------------------------------------------------------------------------

REFUSED_RAW = {
    "refused": True,
    "reason_code": "satellite_coverage_unavailable",
    "reason": (
        "Satellite embedding coverage is not published for this location for "
        "two consecutive years, so the year-on-year change timeline cannot be "
        "computed. No report was generated."
    ),
    "covered_years": [2024],
}


class TestBriefReasonThreading:
    def test_refused_payload_builds_no_detail(self):
        from services.intelligence_brief import _build_pre_da_detail

        assert _build_pre_da_detail(REFUSED_RAW) is None

    def test_refusal_reason_reaches_datafield(self):
        from services.intelligence_brief import (
            ConfidenceLevel,
            _build_satellite_data,
        )

        sat = _build_satellite_data(
            bushfire_raw=None, flood_raw=None, climate_raw=None,
            granny_flat_raw=None, pre_da_raw=REFUSED_RAW,
        )
        assert sat.pre_da_history.value is None
        assert sat.pre_da_history.confidence == ConfidenceLevel.NOT_AVAILABLE
        assert sat.pre_da_history.reason == REFUSED_RAW["reason"]

    def test_non_refused_absent_payload_keeps_generic_reason(self):
        from services.intelligence_brief import _build_satellite_data

        sat = _build_satellite_data(
            bushfire_raw=None, flood_raw=None, climate_raw=None,
            granny_flat_raw=None, pre_da_raw=None,
        )
        assert sat.pre_da_history.reason == "Pre-DA history not requested or failed"
