"""Unit tests for conveyancing report forensic fixes.

Tests the specific bug fixes:
1. Zone IndexError when zone is empty/None
2. FSR threshold: 10:1 ratio should be treated as ratio, not sqm
3. Silent omission: lot_area=None should produce "unavailable" entries
"""

import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from generate_conveyancing_report import calc_development_headroom, calc_feasibility


class TestZoneIndexError:
    """Regression: ''.split()[0] crashes with IndexError when zone is None/empty."""

    def test_calc_feasibility_zone_none(self):
        controls = {"zone": None}
        valuation = {"lot_area_m2": 600}
        # Should not raise IndexError
        results = calc_feasibility(controls, valuation, [])
        assert isinstance(results, list)

    def test_calc_feasibility_zone_empty_string(self):
        controls = {"zone": ""}
        valuation = {"lot_area_m2": 600}
        results = calc_feasibility(controls, valuation, [])
        assert isinstance(results, list)

    def test_calc_feasibility_zone_whitespace_only(self):
        controls = {"zone": "   "}
        valuation = {"lot_area_m2": 600}
        results = calc_feasibility(controls, valuation, [])
        assert isinstance(results, list)

    def test_calc_feasibility_zone_normal(self):
        controls = {"zone": "R2 Low Density Residential"}
        valuation = {"lot_area_m2": 600}
        results = calc_feasibility(controls, valuation, [])
        assert isinstance(results, list)


class TestFSRThreshold:
    """Regression: FSR 10:1 was excluded by `< 10` check."""

    def test_fsr_10_to_1_is_ratio(self):
        controls = {"fsr": "10:1"}
        valuation = {"lot_area_m2": 1000}
        result = calc_development_headroom(controls, valuation)
        assert "max_gfa_m2" in result
        assert result["max_gfa_m2"] == 10000

    def test_fsr_15_to_1_is_ratio(self):
        controls = {"fsr": "15:1"}
        valuation = {"lot_area_m2": 1000}
        result = calc_development_headroom(controls, valuation)
        assert "max_gfa_m2" in result
        assert result["max_gfa_m2"] == 15000

    def test_fsr_16_is_treated_as_sqm(self):
        """Values above 15 are probably raw sqm, not a ratio."""
        controls = {"fsr": "84"}
        valuation = {"lot_area_m2": 1000}
        result = calc_development_headroom(controls, valuation)
        assert "max_gfa_m2" not in result

    def test_fsr_normal_ratio(self):
        controls = {"fsr": "0.65:1"}
        valuation = {"lot_area_m2": 500}
        result = calc_development_headroom(controls, valuation)
        assert "max_gfa_m2" in result
        assert result["max_gfa_m2"] == 325


class TestSilentOmission:
    """Regression: lot_area=None caused secondary dwelling and subdivision to silently vanish."""

    def test_secondary_dwelling_unavailable_when_no_lot_area(self):
        controls = {"zone": "R2"}
        valuation = {"lot_area_m2": None}
        # SEPP config injected: without it the config-missing branch renders
        # "Not assessed" first (#684) and the lot-area path never runs.
        results = calc_feasibility(
            controls, valuation, [], is_strata=False,
            sepp_standards={"sd_min_lot": 450.0, "sd_zones": {"R1", "R2", "R3", "R4"}},
        )
        sd = [r for r in results if "Secondary dwelling" in r["question"]]
        assert len(sd) == 1
        assert "unavailable" in sd[0]["answer"].lower()

    def test_subdivision_unavailable_when_no_lot_area(self):
        controls = {"zone": "R2", "lot_size": "450"}
        valuation = {"lot_area_m2": None}
        results = calc_feasibility(controls, valuation, [], is_strata=False)
        sub = [r for r in results if "subdivision" in r["question"].lower()]
        assert len(sub) == 1
        assert "unavailable" in sub[0]["answer"].lower()

    def test_strata_still_gets_strata_message(self):
        """Strata path should be unaffected by the fallback."""
        controls = {"zone": "R2"}
        valuation = {"lot_area_m2": None}
        results = calc_feasibility(controls, valuation, [], is_strata=True)
        sd = [r for r in results if "Secondary dwelling" in r["question"]]
        assert len(sd) == 1
        assert "strata" in sd[0]["answer"].lower()


class TestCalcDevelopmentHeadroom:
    """Verify calc_development_headroom returns expected keys."""

    def test_empty_inputs(self):
        result = calc_development_headroom({}, {})
        assert result == {}

    def test_lot_area_only(self):
        result = calc_development_headroom({}, {"lot_area_m2": 600})
        assert result["lot_area_m2"] == 600
        assert "lot_area_display" in result
        assert "max_gfa_m2" not in result

    def test_lot_area_and_fsr(self):
        result = calc_development_headroom({"fsr": "0.5:1"}, {"lot_area_m2": 800})
        assert result["max_gfa_m2"] == 400
        assert result["fsr_numeric"] == 0.5
        assert "max_gfa_display" in result

    def test_land_value(self):
        result = calc_development_headroom({}, {"lot_area_m2": 500, "land_value": 1000000, "val_base_date": "2024-07-01"})
        assert result["land_value"] == 1000000
        assert "land_value_display" in result
        assert result["land_value_per_m2"] == 2000
