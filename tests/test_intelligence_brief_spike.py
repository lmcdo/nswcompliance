"""Tests for intelligence brief spike logic: compound constraints + strata classification."""

import pytest

from scripts.intelligence_brief_spike import (
    classify_strata,
    evaluate_compound_constraints,
)


# ── Compound constraints ──────────────────────────────────────────────


class TestCompoundConstraints:
    """Test evaluate_compound_constraints fires correctly for heritage + hazard combos."""

    def test_heritage_hca_plus_flood_epi(self):
        controls = {"heritage_hca": ["Some HCA"], "flood_epi": True}
        fired = evaluate_compound_constraints(controls, overlays=[], heritage_postgis={})
        rules = [c["rule"] for c in fired]
        assert "heritage_flood" in rules

    def test_heritage_item_plus_flood_epi(self):
        """Heritage items (not just HCA) should also fire the flood rule."""
        controls = {"heritage_items": [{"name": "Some Item"}], "flood_epi": True}
        fired = evaluate_compound_constraints(controls, overlays=[], heritage_postgis={})
        rules = [c["rule"] for c in fired]
        assert "heritage_flood" in rules

    def test_heritage_item_plus_flood_epi_source_is_portal_item(self):
        controls = {"heritage_items": [{"name": "X"}], "flood_epi": True}
        fired = evaluate_compound_constraints(controls, overlays=[], heritage_postgis={})
        flood_rule = [c for c in fired if c["rule"] == "heritage_flood"][0]
        assert flood_rule["heritage_source"] == "portal_item"

    def test_heritage_hca_source_is_portal_hca(self):
        controls = {"heritage_hca": ["HCA"], "flood_epi": True}
        fired = evaluate_compound_constraints(controls, overlays=[], heritage_postgis={})
        flood_rule = [c for c in fired if c["rule"] == "heritage_flood"][0]
        assert flood_rule["heritage_source"] == "portal_hca"

    def test_heritage_item_plus_postgis_flood(self):
        """Heritage item + flood in PostGIS overlays (no EPI flag)."""
        controls = {"heritage_items": [{"name": "X"}]}
        overlays = [{"layer_type": "flood", "value": "1% AEP"}]
        fired = evaluate_compound_constraints(controls, overlays, heritage_postgis={})
        rules = [c["rule"] for c in fired]
        assert "heritage_flood" in rules

    def test_no_heritage_no_flood_rule(self):
        controls = {"flood_epi": True}
        fired = evaluate_compound_constraints(controls, overlays=[], heritage_postgis={})
        rules = [c["rule"] for c in fired]
        assert "heritage_flood" not in rules

    def test_heritage_item_plus_bushfire(self):
        controls = {"heritage_items": [{"name": "X"}]}
        overlays = [{"layer_type": "bushfire", "value": "Vegetation Category 1"}]
        fired = evaluate_compound_constraints(controls, overlays, heritage_postgis={})
        rules = [c["rule"] for c in fired]
        assert "heritage_bushfire_1050" in rules

    def test_heritage_hca_plus_bushfire(self):
        controls = {"heritage_hca": ["HCA"]}
        overlays = [{"layer_type": "bushfire", "value": "Vegetation Buffer"}]
        fired = evaluate_compound_constraints(controls, overlays, heritage_postgis={})
        rules = [c["rule"] for c in fired]
        assert "heritage_bushfire_1050" in rules

    def test_tod_plus_heritage_item(self):
        controls = {"heritage_items": [{"name": "X"}], "tod_area": True}
        fired = evaluate_compound_constraints(controls, overlays=[], heritage_postgis={})
        rules = [c["rule"] for c in fired]
        assert "tod_heritage_density" in rules

    def test_clean_lot_no_rules_fire(self):
        controls = {}
        fired = evaluate_compound_constraints(controls, overlays=[], heritage_postgis={})
        assert fired == []


# ── Strata classification ─────────────────────────────────────────────


class TestClassifyStrata:
    """Test classify_strata uses sp_lot_count from the Cadastre API."""

    def test_not_strata(self):
        assert classify_strata({"is_strata": False}, {}) == "not_strata"

    def test_no_lot_count_returns_unknown(self):
        assert classify_strata({"is_strata": True}, {}) == "strata_unknown"

    def test_high_lot_count_is_apartment(self):
        """50-unit block → apartment."""
        strata = {"is_strata": True, "sp_lot_count": 50}
        assert classify_strata(strata, {}) == "apartment"

    def test_seven_lots_is_apartment(self):
        strata = {"is_strata": True, "sp_lot_count": 7}
        assert classify_strata(strata, {}) == "apartment"

    def test_three_lots_is_development(self):
        """3-unit townhouse complex → development (has GF potential)."""
        strata = {"is_strata": True, "sp_lot_count": 3}
        assert classify_strata(strata, {}) == "development"

    def test_two_lots_is_development(self):
        strata = {"is_strata": True, "sp_lot_count": 2}
        assert classify_strata(strata, {}) == "development"

    def test_six_lots_is_development(self):
        """Boundary: 6 lots = development (townhouse/villa complex)."""
        strata = {"is_strata": True, "sp_lot_count": 6}
        assert classify_strata(strata, {}) == "development"

    def test_single_lot_is_unknown(self):
        """1 SP lot is an edge case — can't determine building type."""
        strata = {"is_strata": True, "sp_lot_count": 1}
        assert classify_strata(strata, {}) == "strata_unknown"

    def test_carlton_cres_townhouse_not_apartment(self):
        """Regression: 3/22 Carlton Cres Summer Hill — strata townhouse on 2140m² lot.
        Old heuristic classified as apartment because lot_area > 1500.
        With sp_lot_count, a small number of lots = development, not apartment."""
        strata = {"is_strata": True, "sp_lot_count": 3}
        valuation = {"lot_area_m2": 2140}
        result = classify_strata(strata, valuation)
        assert result == "development", (
            "Carlton Cres townhouse (3 lots, 2140m²) should be 'development', not 'apartment'"
        )
