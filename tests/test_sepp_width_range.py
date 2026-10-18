"""evaluate_eligibility with a width range measured from the road."""
import services.housing_sepp_eligibility as hse
from services.housing_sepp_eligibility import evaluate_eligibility

ALL_FALSE = {"in_lmr_area": False, "in_tod": False, "dual_occ_prohibited": False}


def _standards(monkeypatch, widths):
    grouped = {
        k: {"requires_lmr_area": False, "applicable_zones": ["R2"], "min_lot_size": 300.0, "min_lot_width": w}
        for k, w in widths.items()
    }
    monkeypatch.setattr(hse, "_fetch_standards_grouped", lambda: grouped)


def _run(rng, width=None):
    return {r.development_type: r for r in evaluate_eligibility(
        "R2", 700, width, -33.8, 151.1, gate_inputs=ALL_FALSE, lot_width_range=rng)}


def test_range_meets_one_form_and_depends_for_another(monkeypatch):
    _standards(monkeypatch, {"dual_occupancy": 12.0, "terraces": 18.0})
    res = _run((13.38, 22.4))
    assert res["dual_occupancy"].eligible is True
    t = res["terraces"]
    assert t.eligible is False and t.unconfirmed is True
    assert t.reason.startswith("Depends on where the front building line sits")
    assert "13.4 m wide at its narrowest in the front half and 22.4 m at its widest" in t.reason
    assert "minimum 18 m at the front building line" in t.reason


def test_range_below_minimum_is_ineligible(monkeypatch):
    _standards(monkeypatch, {"dual_occupancy": 12.0})
    r = _run((6.18, 6.44))["dual_occupancy"]
    assert r.eligible is False and r.unconfirmed is False
    assert "at its widest" in r.reason and "6.4 m" in r.reason


def test_range_overrides_rectangle_width(monkeypatch):
    _standards(monkeypatch, {"dual_occupancy": 12.0})
    assert _run((6.18, 6.44), width=30.0)["dual_occupancy"].eligible is False


def test_no_range_keeps_old_behaviour(monkeypatch):
    _standards(monkeypatch, {"dual_occupancy": 12.0})
    assert _run(None, width=20.0)["dual_occupancy"].eligible is True
    assert _run(None, width=None)["dual_occupancy"].unconfirmed is True
