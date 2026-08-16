"""Tests for DB-sourced regulatory constants (SEPP Housing + tax thresholds).

Verifies:
  1. fetch_sepp_housing_standards returns correct shape and filters by zone/dev_type
  2. get_sepp_standard_value returns single float
  3. fetch_tax_thresholds returns correct shape
  4. granny_flat._get_sepp_sd_standards has NO fallback (#817) — covered in
     tests/test_granny_flat_mutation.py (None → endpoints fail closed, 503)
  5. calc_feasibility uses injected configs correctly
"""

import importlib.util
import os
import pytest
from unittest.mock import MagicMock, patch
from decimal import Decimal

# Load conveyancing_db from scripts/
_spec = importlib.util.spec_from_file_location(
    "conveyancing_db",
    os.path.join(os.path.dirname(__file__), "..", "scripts", "conveyancing_db.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

fetch_sepp_housing_standards = _mod.fetch_sepp_housing_standards
get_sepp_standard_value = _mod.get_sepp_standard_value
_validate_sepp_sd_config = _mod._validate_sepp_sd_config
fetch_tax_thresholds = _mod.fetch_tax_thresholds
fetch_heritage_postgis = _mod.fetch_heritage_postgis
fetch_dcp_setbacks = _mod.fetch_dcp_setbacks
fetch_lep_clauses = _mod.fetch_lep_clauses
check_regulatory_freshness = _mod.check_regulatory_freshness

# Load generate_conveyancing_report for calc_feasibility
_gcr_spec = importlib.util.spec_from_file_location(
    "generate_conveyancing_report",
    os.path.join(os.path.dirname(__file__), "..", "scripts", "generate_conveyancing_report.py"),
)
_gcr_mod = importlib.util.module_from_spec(_gcr_spec)
_gcr_spec.loader.exec_module(_gcr_mod)

calc_feasibility = _gcr_mod.calc_feasibility


# ── Helpers ──

def _mock_conn_with_sepp_rows(rows):
    """Create a mock DB connection that returns given rows for SEPP query."""
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    cur.fetchall.return_value = rows
    return conn


def _mock_conn_with_tax_row(row):
    """Create a mock DB connection that returns given row for tax query."""
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    cur.fetchone.return_value = row
    return conn


# ── fetch_sepp_housing_standards ──

class TestFetchSeppHousingStandards:
    def test_returns_all_rows_no_filter(self):
        rows = [
            ("secondary_dwelling", "min_lot_size", Decimal("450"), "m²",
             ["R1", "R2", "R3", "R4"], "53(1)(b)", "SEPP Housing 2021",
             "https://legislation.nsw.gov.au/...", "2021-11-29", None, None),
            ("secondary_dwelling", "max_floor_area", Decimal("60"), "m²",
             ["R1", "R2", "R3", "R4"], "22(1)", "SEPP (E&C) 2008",
             "https://legislation.nsw.gov.au/...", "2021-11-29", None, None),
        ]
        conn = _mock_conn_with_sepp_rows(rows)
        result = fetch_sepp_housing_standards(conn)
        assert len(result) == 2
        assert result[0]["development_type"] == "secondary_dwelling"
        assert result[0]["numeric_value"] == 450.0
        assert result[1]["standard_type"] == "max_floor_area"
        assert result[1]["numeric_value"] == 60.0

    def test_filters_by_development_type(self):
        conn = _mock_conn_with_sepp_rows([])
        fetch_sepp_housing_standards(conn, development_type="dual_occupancy")
        call_args = conn.cursor().execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]
        assert "development_type = %s" in sql
        assert "dual_occupancy" in params

    def test_filters_by_zone(self):
        conn = _mock_conn_with_sepp_rows([])
        fetch_sepp_housing_standards(conn, zone_code="R2 Low Density Residential")
        call_args = conn.cursor().execute.call_args
        params = call_args[0][1]
        assert "R2" in params

    def test_filters_by_both(self):
        conn = _mock_conn_with_sepp_rows([])
        fetch_sepp_housing_standards(conn, zone_code="R3", development_type="secondary_dwelling")
        call_args = conn.cursor().execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]
        assert "development_type = %s" in sql
        assert "ANY(applicable_zones)" in sql
        assert "secondary_dwelling" in params
        assert "R3" in params

    def test_raises_on_db_error_rather_than_dropping_every_standard(self):
        """DQ-82. These are the standards a feasibility answer is computed
        FROM. An empty list silently removes all of them and the arithmetic
        proceeds as though none applied."""
        conn = MagicMock()
        conn.cursor.side_effect = Exception("connection lost")
        with pytest.raises(Exception, match="connection lost"):
            fetch_sepp_housing_standards(conn)

    def test_raises_for_none_conn(self):
        """DQ-82. This previously asserted that None "should not crash —
        returns empty". Not crashing WAS the bug: the caller received [] and
        could not tell it from a genuine absence of standards."""
        with pytest.raises(AttributeError):
            fetch_sepp_housing_standards(None)


# ── get_sepp_standard_value ──

class TestGetSeppStandardValue:
    def test_returns_float_for_known_standard(self):
        rows = [
            ("secondary_dwelling", "min_lot_size", Decimal("450"), "m²",
             ["R1", "R2", "R3", "R4"], "53(1)(b)", "SEPP Housing 2021",
             "https://...", "2021-11-29", None, None),
        ]
        conn = _mock_conn_with_sepp_rows(rows)
        val = get_sepp_standard_value(conn, "secondary_dwelling", "min_lot_size")
        assert val == 450.0

    def test_returns_none_for_unknown_standard(self):
        conn = _mock_conn_with_sepp_rows([])
        val = get_sepp_standard_value(conn, "secondary_dwelling", "nonexistent")
        assert val is None


# ── fetch_tax_thresholds ──

class TestFetchTaxThresholds:
    def test_returns_correct_shape(self):
        row = (2025, 1075000, Decimal("0.0160"), 100, 6571000, Decimal("0.0200"),
               "https://revenue.nsw.gov.au/...")
        conn = _mock_conn_with_tax_row(row)
        result = fetch_tax_thresholds(conn, tax_year=2025)
        assert result["tax_year"] == 2025
        assert result["threshold_dollars"] == 1075000
        assert result["rate"] == 0.016
        assert result["base_amount_dollars"] == 100
        assert result["premium_threshold_dollars"] == 6571000
        assert result["premium_rate"] == 0.02

    def test_returns_none_for_missing_year(self):
        conn = _mock_conn_with_tax_row(None)
        result = fetch_tax_thresholds(conn, tax_year=2099)
        assert result is None

    def test_returns_none_on_db_error(self):
        conn = MagicMock()
        conn.cursor.side_effect = Exception("connection lost")
        result = fetch_tax_thresholds(conn)
        assert result is None


# ── calc_feasibility with injected configs ──

class TestCalcFeasibilityWithConfigs:
    """Verify calc_feasibility uses injected SEPP and tax configs."""

    _base_controls = {"zone": "R2 Low Density Residential", "zone_epi": "Inner West LEP"}
    _base_valuation = {"lot_area_m2": 500, "land_value": 1_200_000}
    _base_overlays = []

    def test_uses_injected_sepp_min_lot(self):
        """When SEPP says 600m², a 500m² lot should fail."""
        sepp = {"sd_min_lot": 600, "sd_zones": {"R1", "R2", "R3", "R4"}}
        result = calc_feasibility(
            self._base_controls, self._base_valuation, self._base_overlays,
            sepp_standards=sepp,
        )
        sd_item = next(r for r in result if "granny flat" in r["question"].lower())
        assert sd_item["flag"] == "warn"
        assert "600" in sd_item["basis"]

    def test_uses_injected_sepp_zones(self):
        """When SEPP zones exclude R2, secondary dwelling should show zone check required."""
        sepp = {"sd_min_lot": 450, "sd_zones": {"R3", "R4"}}
        result = calc_feasibility(
            self._base_controls, self._base_valuation, self._base_overlays,
            sepp_standards=sepp,
        )
        sd_item = next(r for r in result if "granny flat" in r["question"].lower())
        assert sd_item["flag"] == "warn"
        assert "Zone check" in sd_item["answer"]

    def test_uses_injected_tax_config(self):
        """When tax threshold is 1M, a 1.2M property should show tax."""
        tax = {"tax_year": 2026, "threshold_dollars": 1_000_000, "rate": 0.02, "base_amount_dollars": 200}
        result = calc_feasibility(
            self._base_controls, self._base_valuation, self._base_overlays,
            tax_config=tax,
        )
        lt_item = next(r for r in result if "land tax" in r["question"].lower())
        assert lt_item["flag"] == "warn"
        assert "2026" in lt_item["question"]
        assert "$1,000,000" in lt_item["basis"]

    def test_validator_rejects_zero_minimum(self):
        """A 0 m² minimum would silently pass every lot — corrupt row fails closed."""
        row = {"numeric_value": 0, "applicable_zones": ["R2"]}
        assert _validate_sepp_sd_config(row) is None

    def test_validator_rejects_negative_and_nonfinite(self):
        for bad in (-450, float("nan"), float("inf"), None, "abc"):
            row = {"numeric_value": bad, "applicable_zones": ["R2"]}
            assert _validate_sepp_sd_config(row) is None, bad

    def test_validator_rejects_null_or_empty_zone_entries(self):
        """A null zone entry would crash sorted() mid-render — fail closed instead."""
        for bad_zones in (["R1", None], ["R1", ""], ["R1", "  "], [], None, "R1"):
            row = {"numeric_value": 450, "applicable_zones": bad_zones}
            assert _validate_sepp_sd_config(row) is None, bad_zones

    def test_validator_accepts_and_normalises_valid_row(self):
        row = {"numeric_value": "450", "applicable_zones": [" R1 ", "R2"]}
        cfg = _validate_sepp_sd_config(row)
        assert cfg == {"sd_min_lot": 450.0, "sd_zones": {"R1", "R2"}}

    def test_no_configs_renders_not_assessed(self):
        """Without injected configs there is NO fallback (#684): the
        secondary-dwelling row renders 'Not assessed' and states no figure."""
        result = calc_feasibility(
            self._base_controls, self._base_valuation, self._base_overlays,
        )
        sd_item = next(r for r in result if "granny flat" in r["question"].lower())
        assert sd_item["answer"] == "Not assessed"
        assert sd_item["flag"] == "warn"
        assert "450" not in sd_item["basis"]

    def test_strata_skips_secondary_dwelling_and_tax(self):
        """Strata lots should skip granny flat and land tax regardless of configs."""
        sepp = {"sd_min_lot": 450, "sd_zones": {"R1", "R2", "R3", "R4"}}
        tax = {"tax_year": 2025, "threshold_dollars": 1_000_000, "rate": 0.016, "base_amount_dollars": 100}
        result = calc_feasibility(
            self._base_controls, self._base_valuation, self._base_overlays,
            is_strata=True,
            sepp_standards=sepp,
            tax_config=tax,
        )
        sd_item = next(r for r in result if "granny flat" in r["question"].lower())
        assert sd_item["flag"] == "warn"
        assert "strata" in sd_item["answer"].lower()
        # Land tax should not appear for strata
        lt_items = [r for r in result if "land tax" in r["question"].lower()]
        assert len(lt_items) == 0


# ── check_regulatory_freshness ──

class TestCheckRegulatoryFreshness:
    def test_returns_critical_for_none_conn(self):
        warnings = check_regulatory_freshness(None)
        assert len(warnings) == 1
        assert "CRITICAL" in warnings[0]

    def test_returns_empty_when_all_present(self):
        """Both SEPP rows and current-year tax row exist → no warnings."""
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        # First call: SEPP standards
        # Second call: tax thresholds
        from datetime import date
        cur.fetchall.return_value = [
            ("min_lot_size", 450.0),
            ("max_floor_area", 60.0),
        ]
        cur.fetchone.return_value = (date.today().year,)
        warnings = check_regulatory_freshness(conn)
        assert warnings == []

    def test_warns_when_sepp_rows_missing(self):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        from datetime import date
        cur.fetchall.return_value = []  # no SEPP rows
        cur.fetchone.return_value = (date.today().year,)
        warnings = check_regulatory_freshness(conn)
        assert any("min_lot_size" in w for w in warnings)
        assert any("max_floor_area" in w for w in warnings)

    def test_warns_when_tax_year_stale(self):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchall.return_value = [
            ("min_lot_size", 450.0),
            ("max_floor_area", 60.0),
        ]
        cur.fetchone.return_value = (2024,)  # stale year
        warnings = check_regulatory_freshness(conn)
        assert any("stale" in w for w in warnings)

    def test_warns_when_no_tax_rows(self):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchall.return_value = [
            ("min_lot_size", 450.0),
            ("max_floor_area", 60.0),
        ]
        cur.fetchone.return_value = None  # no tax rows
        warnings = check_regulatory_freshness(conn)
        assert any("no tax_thresholds" in w for w in warnings)


# ── Connection isolation (Finding 1 fix) ──

class TestConnectionIsolation:
    """Verify that a failed DB query doesn't poison subsequent calls on the same connection."""

    def test_rollback_called_on_query_failure(self):
        """When a DB function's query raises, conn.rollback() must be called."""
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.execute.side_effect = Exception("current transaction is aborted")
        fetch_dcp_setbacks(conn, "inner-west")
        conn.rollback.assert_called_once()

    # DQ-82: these three still assert the rollback, which is the connection
    # hygiene they were written for and is unchanged. What changed is the
    # second half: the fetchers no longer hand back a clean-looking answer on
    # the way out. Rolling back AND returning [] left the connection usable and
    # the caller misinformed, which is the worse half of the two.

    def test_heritage_rolls_back_and_raises(self):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.execute.side_effect = Exception("relation does not exist")
        with pytest.raises(Exception, match="relation does not exist"):
            fetch_heritage_postgis(conn, -33.8, 151.2)
        conn.rollback.assert_called_once()

    def test_lep_clauses_rolls_back_and_raises(self):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.execute.side_effect = Exception("timeout")
        with pytest.raises(Exception, match="timeout"):
            fetch_lep_clauses(conn, "Clause 4.3C", "Inner West LEP 2022")
        conn.rollback.assert_called_once()

    def test_sepp_rolls_back_and_raises(self):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.execute.side_effect = Exception("connection reset")
        with pytest.raises(Exception, match="connection reset"):
            fetch_sepp_housing_standards(conn)
        conn.rollback.assert_called_once()

    def test_tax_rollback_on_failure(self):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.execute.side_effect = Exception("statement timeout")
        result = fetch_tax_thresholds(conn)
        assert result is None
        conn.rollback.assert_called_once()

    def test_sequential_calls_survive_first_failure(self):
        """Simulate the exact spike bug: first call fails, second call succeeds."""
        conn = MagicMock()
        call_count = {"n": 0}

        def _cursor_factory():
            call_count["n"] += 1
            cur = MagicMock()
            if call_count["n"] == 1:
                # First cursor: query fails (simulating poisoned transaction)
                cur.execute.side_effect = Exception("current transaction is aborted")
            else:
                # Second cursor: query succeeds (after rollback)
                cur.fetchall.return_value = []
                cur.fetchone.return_value = None
            return cur

        conn.cursor.side_effect = _cursor_factory

        # First call fails
        result1 = fetch_dcp_setbacks(conn, "inner-west")
        assert result1 is None
        conn.rollback.assert_called_once()

        # Second call on same connection succeeds (not poisoned)
        result2 = fetch_heritage_postgis(conn, -33.8, 151.2)
        assert result2 == {"hca": [], "items": [], "has_heritage": False, "raw": []}


class TestFetchNearbyDas:
    """Tests for fetch_nearby_das (local DB DA query)."""

    def test_returns_sorted_by_distance(self):
        from conveyancing_db import fetch_nearby_das

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("PAN-111", "10 Far St", "SUBURB", "Determined", -33.895, 151.142, "2026-01-01", "2026-03-01", None, 100000),
            ("PAN-222", "5 Near St", "SUBURB", "Determined", -33.8941, 151.1414, "2026-02-01", "2026-04-01", None, 200000),
        ]
        conn = MagicMock()
        conn.cursor.return_value = mock_cursor

        result = fetch_nearby_das(conn, -33.894, 151.1414, radius_m=500)
        assert len(result) == 2
        assert result[0]["number"] == "PAN-222"  # closer
        assert result[1]["number"] == "PAN-111"
        assert result[0]["distance_m"] < result[1]["distance_m"]

    def test_filters_beyond_radius(self):
        from conveyancing_db import fetch_nearby_das

        mock_cursor = MagicMock()
        # One DA within 100m, one 2km away
        mock_cursor.fetchall.return_value = [
            ("PAN-111", "5 Near St", "SUBURB", "Determined", -33.8941, 151.1414, "2026-01-01", "2026-03-01", None, 100000),
            ("PAN-222", "99 Far St", "SUBURB", "Determined", -33.910, 151.160, "2026-02-01", "2026-04-01", None, 200000),
        ]
        conn = MagicMock()
        conn.cursor.return_value = mock_cursor

        result = fetch_nearby_das(conn, -33.894, 151.1414, radius_m=200)
        assert len(result) == 1
        assert result[0]["number"] == "PAN-111"

    def test_rolls_back_and_raises_on_db_error(self):
        """DQ-82. [] renders as "no recent development applications nearby" --
        a claim about the street, not about our connection. This function's own
        comments already record a buggy council filter producing exactly that
        false "no DAs"; this was the same wrong answer by a different route."""
        from conveyancing_db import fetch_nearby_das

        conn = MagicMock()
        conn.cursor.side_effect = Exception("connection lost")

        with pytest.raises(Exception, match="connection lost"):
            fetch_nearby_das(conn, -33.894, 151.141)
        conn.rollback.assert_called_once()

    def test_parses_jsonb_development_type(self):
        from conveyancing_db import fetch_nearby_das

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("PAN-333", "1 Test St", "SUBURB", "Determined", -33.8940, 151.1414,
             "2026-01-01", "2026-03-01",
             [{"DevelopmentType": "Dwelling house"}, {"DevelopmentType": "Demolition"}],
             500000),
        ]
        conn = MagicMock()
        conn.cursor.return_value = mock_cursor

        result = fetch_nearby_das(conn, -33.894, 151.1414, radius_m=500)
        assert len(result) == 1
        assert "Dwelling house" in result[0]["description"]
        assert "Demolition" in result[0]["description"]

    def test_respects_limit(self):
        from conveyancing_db import fetch_nearby_das

        mock_cursor = MagicMock()
        # 5 DAs all very close
        mock_cursor.fetchall.return_value = [
            (f"PAN-{i}", f"{i} St", "SUB", "Determined", -33.894 + i * 0.00001, 151.1414,
             "2026-01-01", "2026-03-01", None, 10000)
            for i in range(5)
        ]
        conn = MagicMock()
        conn.cursor.return_value = mock_cursor

        result = fetch_nearby_das(conn, -33.894, 151.1414, radius_m=500, limit=3)
        assert len(result) == 3
