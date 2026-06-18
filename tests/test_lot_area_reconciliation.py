"""Tests for the lot-area sanity guard (VG valuation vs cadastral polygon)."""
from __future__ import annotations

import services.intelligence_brief as ib
from services.intelligence_brief import _reconcile_lot_area, _apply_lot_area_reconciliation


class TestReconcileLotArea:
    def test_agree_within_tolerance_keeps_valuation(self):
        c = _reconcile_lot_area(312.0, 320.0)  # ~2.5% apart
        assert c.area_m2 == 312.0
        assert c.source == "valuation"
        assert c.diverged is False
        assert c.note is None

    def test_exact_match(self):
        c = _reconcile_lot_area(500.0, 500.0)
        assert c.area_m2 == 500.0 and c.diverged is False

    def test_at_tolerance_boundary_not_diverged(self):
        # exactly 25% apart -> <= tol -> still agreement
        c = _reconcile_lot_area(125.0, 100.0, tol_pct=0.25)
        assert c.diverged is False
        assert c.area_m2 == 125.0

    def test_aggregated_parcel_diverges_and_trusts_geometry(self):
        # the real failure: VG returns an aggregated 4452 m2, lot is 312 m2
        c = _reconcile_lot_area(4452.0, 312.0)
        assert c.diverged is True
        assert c.area_m2 == 312.0          # geometry wins
        assert c.source == "geometry"
        assert c.note is not None
        assert "4452" in c.note and "312" in c.note

    def test_valuation_only_no_geometry_kept_unflagged(self):
        c = _reconcile_lot_area(600.0, None)
        assert c.area_m2 == 600.0
        assert c.source == "valuation"
        assert c.diverged is False         # nothing to cross-check against

    def test_geometry_only_used(self):
        c = _reconcile_lot_area(None, 450.0)
        assert c.area_m2 == 450.0 and c.source == "geometry" and c.diverged is False

    def test_neither_returns_none(self):
        c = _reconcile_lot_area(None, None)
        assert c.area_m2 is None and c.source == "none" and c.diverged is False

    def test_zero_or_negative_treated_as_missing(self):
        assert _reconcile_lot_area(0.0, 500.0).area_m2 == 500.0     # vg 0 ignored
        assert _reconcile_lot_area(500.0, 0.0).area_m2 == 500.0     # geom 0 ignored
        assert _reconcile_lot_area(-1.0, -1.0).area_m2 is None


class TestApplyLotAreaReconciliation:
    def test_no_geometry_keeps_valuation_returns_no_warning(self):
        val = {"lot_area_m2": 600.0}
        warning = _apply_lot_area_reconciliation(val, None)
        assert warning is None
        assert val["lot_area_m2"] == 600.0
        assert "lot_area_caveat" not in val

    def test_divergence_mutates_valuation_and_returns_warning(self, monkeypatch):
        # stub geometry-area extraction to a small lot vs a huge valuation parcel
        class _Dims:
            area_m2 = 312.0
        monkeypatch.setattr(ib, "calculate_lot_dimensions", lambda g: _Dims())
        val = {"lot_area_m2": 4452.0}
        warning = _apply_lot_area_reconciliation(val, {"rings": [[]]})
        assert warning is not None
        assert val["lot_area_m2"] == 312.0           # corrected to geometry
        assert val["lot_area_caveat"] == warning     # caveat recorded for economics

    def test_agreement_no_caveat(self, monkeypatch):
        class _Dims:
            area_m2 = 315.0
        monkeypatch.setattr(ib, "calculate_lot_dimensions", lambda g: _Dims())
        val = {"lot_area_m2": 312.0}
        warning = _apply_lot_area_reconciliation(val, {"rings": [[]]})
        assert warning is None
        assert val["lot_area_m2"] == 312.0
        assert "lot_area_caveat" not in val


class TestEconomicsConfidenceDowngrade:
    def test_caveat_downgrades_lot_area_to_derived(self):
        econ = ib._build_economics({
            "lot_area_m2": 312.0,
            "lot_area_caveat": "valuation may aggregate parcels",
            "land_value": None, "val_base_date": None, "val_history": [],
        })
        assert econ.lot_area_m2.confidence == ib.ConfidenceLevel.DERIVED
        assert econ.lot_area_m2.source == "planning_portal_lot"
        assert econ.lot_area_m2.reason == "valuation may aggregate parcels"

    def test_no_caveat_stays_authoritative(self):
        econ = ib._build_economics({
            "lot_area_m2": 312.0,
            "land_value": None, "val_base_date": None, "val_history": [],
        })
        assert econ.lot_area_m2.confidence == ib.ConfidenceLevel.AUTHORITATIVE
        assert econ.lot_area_m2.source == "nsw_valuation_service"

    def test_missing_area_not_available(self):
        econ = ib._build_economics({
            "lot_area_m2": None,
            "land_value": None, "val_base_date": None, "val_history": [],
        })
        assert econ.lot_area_m2.confidence == ib.ConfidenceLevel.NOT_AVAILABLE
