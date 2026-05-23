import pytest
pytestmark = pytest.mark.stale

"""
Tests for scripts/conveyancing_db.py

Pure-function tests run always.
DB integration tests require DATABASE_URL and skip if absent.

Run: pytest tests/test_conveyancing_db.py -v
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.conveyancing_db import (
    fetch_dcp_setbacks,
    fetch_heritage_postgis,
    fetch_lep_clauses,
    interpret_sepp,
    normalise_clauses,
)


# ---------------------------------------------------------------------------
# DB fixture
# ---------------------------------------------------------------------------

def _get_conn():
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
    import psycopg2
    url = os.environ.get("DATABASE_URL")
    if not url:
        return None
    return psycopg2.connect(url)


DB_SKIP = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL") and not (Path(__file__).parent.parent / ".env").exists(),
    reason="DATABASE_URL not set",
)


@pytest.fixture(scope="module")
def conn():
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
    import psycopg2
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set")
    c = psycopg2.connect(url)
    yield c
    c.close()


# ===========================================================================
# normalise_clauses — pure function
# ===========================================================================

class TestNormaliseClauses:
    def test_single_clause(self):
        assert normalise_clauses("Clause 4.3C") == ["4.3C"]

    def test_plural_clauses_comma(self):
        assert normalise_clauses("Clauses 4.3C, 4.4") == ["4.3C", "4.4"]

    def test_plural_clauses_and(self):
        assert normalise_clauses("Clauses 4.3C and 4.4") == ["4.3C", "4.4"]

    def test_semicolon_separator(self):
        assert normalise_clauses("Clause 6.14; 6.15") == ["6.14", "6.15"]

    def test_short_form_cl(self):
        assert normalise_clauses("cl. 4.3C") == ["4.3C"]

    def test_no_prefix(self):
        # Raw number — no prefix to strip
        assert normalise_clauses("4.3C") == ["4.3C"]

    def test_empty_string(self):
        assert normalise_clauses("") == []

    def test_none(self):
        assert normalise_clauses(None) == []

    def test_comma_no_space(self):
        assert normalise_clauses("Clauses 4.3C,4.4") == ["4.3C", "4.4"]

    def test_mixed_case_clause(self):
        assert normalise_clauses("CLAUSE 4.3C") == ["4.3C"]

    def test_clause_list_three(self):
        result = normalise_clauses("Clauses 4.3C, 4.4, 6.14")
        assert result == ["4.3C", "4.4", "6.14"]


# ===========================================================================
# interpret_sepp — pure function
# ===========================================================================

class TestInterpretSepp:
    def test_tod_suppressed(self):
        result = interpret_sepp(
            "SEPP Housing 2021", "Transport Oriented Development", "TOD Tier 1", "https://..."
        )
        assert result is None

    def test_bushfire_suppressed(self):
        result = interpret_sepp(
            "SEPP Resilience 2021", "Bushfire", "Bushfire Prone Land", "https://..."
        )
        assert result is None

    def test_anef_suppressed(self):
        result = interpret_sepp(
            "SEPP Transport 2021", "Aircraft Noise", "ANEF 20-25", "https://..."
        )
        assert result is None

    def test_bushfire_prone_land_suppressed(self):
        result = interpret_sepp(
            "SEPP Resilience 2021", "Bushfire Prone Land", "FPI", "https://..."
        )
        assert result is None

    def test_normal_sepp_returns_string(self):
        result = interpret_sepp(
            "SEPP Housing 2021", "Affordable Rental Housing", "ARH Zone", "https://leg.nsw.gov.au/abc"
        )
        assert isinstance(result, str)
        assert "Affordable Rental Housing" in result

    def test_label_appended_when_different(self):
        result = interpret_sepp(
            "SEPP Housing 2021", "Affordable Rental Housing", "ARH Zone", "https://leg.nsw.gov.au/abc"
        )
        assert "ARH Zone" in result

    def test_label_not_duplicated_when_same_as_type(self):
        result = interpret_sepp(
            "SEPP Housing 2021", "Affordable Rental Housing",
            "affordable rental housing", "https://leg.nsw.gov.au/abc"
        )
        # label.lower() == type_.lower() → not appended
        assert result.count("Affordable Rental Housing") == 1

    def test_legislation_url_appended(self):
        url = "https://leg.nsw.gov.au/abc"
        result = interpret_sepp("SEPP Housing 2021", "Heritage", "Heritage Item", url)
        assert url in result

    def test_no_url(self):
        result = interpret_sepp("SEPP Housing 2021", "Heritage", "Heritage Item", "")
        assert isinstance(result, str)
        assert "See" not in result

    def test_empty_type_uses_epi_name(self):
        result = interpret_sepp("SEPP Housing 2021", "", "", "")
        assert "SEPP Housing 2021" in result

    def test_none_type(self):
        result = interpret_sepp("SEPP Housing 2021", None, None, "")
        assert isinstance(result, str)


# ===========================================================================
# fetch_lep_clauses — DB integration
# ===========================================================================

class TestFetchLepClauses:
    def test_known_clause_returns_summary(self, conn):
        results = fetch_lep_clauses(
            conn,
            "Clause 4.3C",
            "Inner West Local Environmental Plan 2022",
        )
        assert len(results) == 1
        r = results[0]
        assert r["number"] == "4.3C"
        assert r["summary"] is not None
        assert "height" in r["summary"].lower() or "Height" in r["summary"]

    def test_multiple_clauses(self, conn):
        results = fetch_lep_clauses(
            conn,
            "Clauses 6.14 and 6.15",
            "Inner West Local Environmental Plan 2022",
        )
        assert len(results) == 2
        numbers = {r["number"] for r in results}
        assert numbers == {"6.14", "6.15"}

    def test_unknown_clause_returns_none_summary(self, conn):
        results = fetch_lep_clauses(
            conn,
            "Clause 99.99",
            "Inner West Local Environmental Plan 2022",
        )
        assert len(results) == 1
        assert results[0]["number"] == "99.99"
        assert results[0]["summary"] is None

    def test_unknown_epi_returns_none_summary(self, conn):
        results = fetch_lep_clauses(
            conn,
            "Clause 4.3C",
            "Nonexistent Council LEP 2099",
        )
        assert len(results) == 1
        assert results[0]["summary"] is None

    def test_empty_clause_returns_empty(self, conn):
        assert fetch_lep_clauses(conn, "", "Inner West Local Environmental Plan 2022") == []

    def test_none_clause_returns_empty(self, conn):
        assert fetch_lep_clauses(conn, None, "Inner West Local Environmental Plan 2022") == []

    def test_none_epi_returns_empty(self, conn):
        assert fetch_lep_clauses(conn, "Clause 4.3C", None) == []

    def test_all_four_iw_clauses(self, conn):
        """All 4 seeded IW clauses must be findable."""
        for clause_num in ["4.3C", "4.4", "6.14", "6.15"]:
            results = fetch_lep_clauses(
                conn,
                f"Clause {clause_num}",
                "Inner West Local Environmental Plan 2022",
            )
            assert results[0]["summary"] is not None, f"Missing summary for IW clause {clause_num}"


# ===========================================================================
# fetch_dcp_setbacks — DB integration (requires migration to have run)
# ===========================================================================

class TestFetchDcpSetbacks:
    def test_marrickville_r2_returns_setbacks(self, conn):
        result = fetch_dcp_setbacks(conn, "marrickville", "R2 Low Density Residential")
        assert result is not None
        assert result["dcp_name"] == "Marrickville DCP 2011"
        assert len(result["setbacks"]) >= 5

    def test_leichhardt_any_zone_returns_setbacks(self, conn):
        # Leichhardt zones stored as ['ALL'] — should match any zone
        result = fetch_dcp_setbacks(conn, "leichhardt", "R2 Low Density Residential")
        assert result is not None
        assert result["dcp_name"] == "Leichhardt DCP 2013"
        assert len(result["setbacks"]) == 3

    def test_ashfield_r2_returns_setbacks(self, conn):
        result = fetch_dcp_setbacks(conn, "ashfield", "R2 Low Density Residential")
        assert result is not None
        assert "Ashfield" in result["dcp_name"]
        assert len(result["setbacks"]) == 4

    def test_unknown_council_returns_none(self, conn):
        assert fetch_dcp_setbacks(conn, "parramatta", "R2") is None

    def test_none_council_returns_none(self, conn):
        assert fetch_dcp_setbacks(conn, None, "R2") is None

    def test_empty_council_returns_none(self, conn):
        assert fetch_dcp_setbacks(conn, "", "R2") is None

    def test_council_case_insensitive(self, conn):
        # detect_former_council() returns lowercase — must normalise to title case
        result_lower = fetch_dcp_setbacks(conn, "marrickville", "R2")
        result_title = fetch_dcp_setbacks(conn, "Marrickville", "R2")
        assert result_lower is not None
        assert result_title is not None
        assert result_lower["dcp_name"] == result_title["dcp_name"]

    def test_dict_shape_matches_dcp_setbacks(self, conn):
        """Shape must be identical to DCP_SETBACKS entries for zero render changes."""
        result = fetch_dcp_setbacks(conn, "marrickville", "R2")
        assert result is not None
        required_keys = {"dcp_name", "section", "clause_ref", "zones_applicable",
                         "dev_type_scope", "caveat", "setbacks"}
        assert required_keys.issubset(result.keys())
        for sb in result["setbacks"]:
            assert {"type", "control_type", "requirement", "clause", "notes"}.issubset(sb.keys())

    def test_prescribed_setback_has_numeric_requirement(self, conn):
        result = fetch_dcp_setbacks(conn, "marrickville", "R2")
        prescribed = [sb for sb in result["setbacks"] if sb["control_type"] == "prescribed"]
        assert len(prescribed) > 0
        for sb in prescribed:
            # prescribed rows have value_numeric → requirement should be "N m minimum"
            assert "m" in sb["requirement"] or "mm" in sb["requirement"]

    def test_marrickville_front_is_site_derived(self, conn):
        result = fetch_dcp_setbacks(conn, "marrickville", "R2")
        front = next(sb for sb in result["setbacks"] if "Front" in sb["type"])
        assert front["control_type"] == "site_derived"

    def test_zone_code_stripped_from_description(self, conn):
        # "R2 Low Density Residential" → zone_clean "R2"
        result = fetch_dcp_setbacks(conn, "ashfield", "R2 Low Density Residential")
        assert result is not None
        # zones_applicable should be ['R2'] (cleaned)
        assert "R2" in result["zones_applicable"]


# ===========================================================================
# fetch_heritage_postgis — DB integration
# ===========================================================================

# Known Inner West HCA coordinates (Annandale/Leichhardt area — Inner West HCA)
# These are within the Inner West LGA heritage layer
_IW_HCA_LAT = -33.8882
_IW_HCA_LNG = 151.1498  # 5 Flood Street Leichhardt area

# Point in open water (Sydney Harbour) — no heritage polygons
_NO_HERITAGE_LAT = -33.8500
_NO_HERITAGE_LNG = 151.2100  # Sydney Harbour, north of CBD


class TestFetchHeritagePostgis:
    def test_return_shape_always_correct(self, conn):
        """Return dict must always have the expected keys."""
        result = fetch_heritage_postgis(conn, _IW_HCA_LAT, _IW_HCA_LNG)
        assert isinstance(result, dict)
        assert {"hca", "items", "has_heritage", "raw"}.issubset(result.keys())
        assert isinstance(result["hca"], list)
        assert isinstance(result["items"], list)
        assert isinstance(result["has_heritage"], bool)
        assert isinstance(result["raw"], list)

    def test_non_heritage_location_returns_empty(self, conn):
        """Point in non-heritage area should return has_heritage=False."""
        result = fetch_heritage_postgis(conn, _NO_HERITAGE_LAT, _NO_HERITAGE_LNG)
        assert result["has_heritage"] is False
        assert result["hca"] == []

    def test_hca_display_string_format(self, conn):
        """HCA entries should contain 'Heritage Conservation Area' + instrument."""
        result = fetch_heritage_postgis(conn, _IW_HCA_LAT, _IW_HCA_LNG)
        if result["hca"]:  # point may or may not be in HCA — just check format
            for entry in result["hca"]:
                assert "Heritage Conservation Area" in entry
                assert "(" in entry  # instrument wrapped in parens

    def test_raw_rows_have_value_and_instrument(self, conn):
        """Raw rows must have both value and instrument_key keys."""
        result = fetch_heritage_postgis(conn, _IW_HCA_LAT, _IW_HCA_LNG)
        for row in result["raw"]:
            assert "value" in row
            assert "instrument_key" in row

    def test_lot_wkt_param_accepted(self, conn):
        """Passing lot_wkt should not raise — uses polygon path."""
        # Small square polygon around Leichhardt
        wkt = "POLYGON((151.149 -33.889, 151.150 -33.889, 151.150 -33.888, 151.149 -33.888, 151.149 -33.889))"
        result = fetch_heritage_postgis(conn, _IW_HCA_LAT, _IW_HCA_LNG, lot_wkt=wkt)
        assert isinstance(result, dict)
        assert "has_heritage" in result

    def test_deduplication(self, conn):
        """Multiple polygon intersections for same HCA should not produce duplicates."""
        wkt = "POLYGON((151.148 -33.890, 151.152 -33.890, 151.152 -33.886, 151.148 -33.886, 151.148 -33.890))"
        result = fetch_heritage_postgis(conn, _IW_HCA_LAT, _IW_HCA_LNG, lot_wkt=wkt)
        # No duplicate strings in hca list
        assert len(result["hca"]) == len(set(result["hca"]))

    def test_epi_ilike_fetch_lep_clauses(self, conn):
        """ILIKE match — different capitalisation should still find Inner West clauses."""
        result = fetch_lep_clauses(
            conn,
            "Clause 4.3C",
            "inner west local environmental plan 2022",  # all lowercase
        )
        assert len(result) == 1
        assert result[0]["summary"] is not None


# ===========================================================================
# spatial_overlays_coverage — integrity tests
#
# These tests lock in the covered_layers fix:
#   - Global layers (bushfire, anef) must have an 'ALL' row with feature_count > 0
#     and no per-LGA rows. This is the post-migrate_coverage_global_layers.py state.
#   - Per-LGA layers must NOT have spurious 'ALL' rows.
#   - The covered_layers query logic is validated by checking that the correct
#     layers appear for a known LGA.
# ===========================================================================

class TestCoverageTableIntegrity:
    def test_global_layers_have_all_row(self, conn):
        """bushfire and anef must have a single 'ALL' row with feature_count > 0."""
        cur = conn.cursor()
        for layer in ("bushfire", "anef"):
            cur.execute(
                "SELECT feature_count FROM spatial_overlays_coverage WHERE lga_name='ALL' AND layer_type=%s",
                (layer,),
            )
            row = cur.fetchone()
            assert row is not None, f"{layer}: missing 'ALL' coverage row — run migrate_coverage_global_layers.py"
            assert row[0] > 0, f"{layer}: 'ALL' row has feature_count=0 — ingest may have failed"
        cur.close()

    def test_global_layers_have_no_per_lga_rows(self, conn):
        """After migration, no per-LGA rows should exist for bushfire or anef."""
        cur = conn.cursor()
        for layer in ("bushfire", "anef"):
            cur.execute(
                "SELECT COUNT(*) FROM spatial_overlays_coverage WHERE layer_type=%s AND lga_name!='ALL'",
                (layer,),
            )
            count = cur.fetchone()[0]
            assert count == 0, (
                f"{layer}: {count} stale per-LGA coverage rows found. "
                f"Run migrate_coverage_global_layers.py to clean up."
            )
        cur.close()

    def test_per_lga_layers_have_no_all_row(self, conn):
        """Per-LGA layers (zone, heritage, biodiversity) must not have an 'ALL' row."""
        cur = conn.cursor()
        for layer in ("zone", "heritage", "biodiversity"):
            cur.execute(
                "SELECT COUNT(*) FROM spatial_overlays_coverage WHERE layer_type=%s AND lga_name='ALL'",
                (layer,),
            )
            count = cur.fetchone()[0]
            assert count == 0, f"{layer}: unexpected 'ALL' coverage row found"
        cur.close()

    def test_inner_west_coverage_excludes_zero_feature_layers(self, conn):
        """covered_layers logic: Inner West should not include layers with feature_count=0."""
        cur = conn.cursor()
        # Layers where Inner West has 0 features (confirmed from diagnostic)
        # landslide has only 6 LGAs with data — Inner West should not be one
        cur.execute(
            "SELECT feature_count FROM spatial_overlays_coverage WHERE lga_name='INNER WEST' AND layer_type='landslide'"
        )
        row = cur.fetchone()
        if row is not None:
            # If row exists, it should be 0 features (Inner West is flat — no landslide risk)
            assert row[0] == 0, "Unexpected landslide features for Inner West — verify data"
        cur.close()

    def test_bushfire_covered_via_all_row_not_per_lga(self, conn):
        """The new covered_layers query must find bushfire via 'ALL', not per-LGA rows."""
        cur = conn.cursor()
        # Simulate the new covered_layers logic
        cur.execute(
            "SELECT layer_type FROM spatial_overlays_coverage WHERE lga_name='INNER WEST' AND feature_count > 0"
        )
        per_lga_layers = {r[0] for r in cur.fetchall()}

        cur.execute(
            "SELECT layer_type FROM spatial_overlays_coverage WHERE lga_name='ALL' AND feature_count > 0"
        )
        global_layers = {r[0] for r in cur.fetchall()}

        covered = per_lga_layers | global_layers

        # Bushfire must come from 'ALL' row, not per-LGA
        assert "bushfire" not in per_lga_layers, "bushfire should not be in per-LGA covered set"
        assert "bushfire" in global_layers, "bushfire 'ALL' row must exist with features > 0"
        assert "bushfire" in covered, "bushfire must be in final covered_layers set"

        # anef same
        assert "anef" not in per_lga_layers
        assert "anef" in global_layers
        cur.close()
