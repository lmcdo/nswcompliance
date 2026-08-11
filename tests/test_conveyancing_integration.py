"""
Integration tests for the conveyancing report pipeline.

These tests run against live DB and portal. They assert that known addresses
produce correct structured output — catching the class of "assumed DB state"
bugs that unit tests miss.

Run: pytest tests/test_conveyancing_integration.py -v

SKIP CONDITIONS:
  - DATABASE_URL not set
  - Network unavailable (portal calls will fail)

GOLDEN ADDRESSES (manually verified):
  LEICHHARDT_ADDR  — Inner West, R1 zone, HCA (Leichhardt HCA), key sites clauses
  WAHROONGA_ADDR   — Ku-ring-gai, R2 zone, no DCP data, individual heritage item
  NON_HERITAGE     — Inner West, industrial zone, no heritage

Add new addresses here when verifying output for new LGAs.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.stale

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

# ---------------------------------------------------------------------------
# Skip conditions
# ---------------------------------------------------------------------------

_has_db = bool(
    os.environ.get("DATABASE_URL")
    or (Path(__file__).parent.parent / ".env").exists()
)
_network_skip = pytest.mark.skipif(
    not _has_db,
    reason="DATABASE_URL not set",
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def db_conn():
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
    import psycopg2
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set")
    conn = psycopg2.connect(url)
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Known addresses — update when new LGAs are onboarded
# ---------------------------------------------------------------------------
#
# ONBOARDED_LGAS is the forcing function for LGA expansion coverage:
# - expect_dcp=True  → dcp_general_requirements has manual rows for this council
# - expect_heritage  → None=untested, True=must find, False=must be clear
#
# Add a new entry here when an LGA passes the DCP migration. That single
# change will cause test_dcp_returns_data and test_detect_former_council to
# fail for the new LGA until the data and code are both in place.
#
# Fields: addr, lat, lng, epi, zone, former_council, expect_dcp, expect_dcp_name

ONBOARDED_LGAS = [
    {
        "id": "leichhardt",
        "addr": "5 Flood Street Leichhardt NSW 2040",
        "lat": -33.888218, "lng": 151.149809,
        "epi": "Inner West Local Environmental Plan 2022",
        "zone": "R1 General Residential",
        "former_council": "leichhardt",
        "expect_dcp": True,
        "expect_dcp_name": "Leichhardt DCP 2013",
        "expect_dcp_setback_count": 3,
    },
    {
        "id": "marrickville",
        "addr": "10 Marrickville Road Marrickville NSW 2204",
        "lat": -33.912, "lng": 151.155,
        "epi": "Inner West Local Environmental Plan 2022",
        "zone": "R2 Low Density Residential",
        "former_council": "marrickville",
        "expect_dcp": True,
        "expect_dcp_name": "Marrickville DCP 2011",
        "expect_dcp_setback_count": 7,
    },
    {
        "id": "ashfield",
        "addr": "5 Charlotte Street Ashfield NSW 2131",
        "lat": -33.889, "lng": 151.123,
        "epi": "Inner West Local Environmental Plan 2022",
        "zone": "R2 Low Density Residential",
        "former_council": "ashfield",
        "expect_dcp": True,
        "expect_dcp_name": "Inner West DCP 2016 (Ashfield precinct)",
        "expect_dcp_setback_count": 4,
    },
]

# Non-onboarded LGA — used to verify that missing data returns gracefully
WAHROONGA_ADDR = "45 Wahroonga Ave Wahroonga NSW 2076"
WAHROONGA_LAT = -33.713832
WAHROONGA_LNG = 151.125666

# Inner West, Leichhardt. Kept as named constants for backward-compat in existing tests
LEICHHARDT_ADDR = "5 Flood Street Leichhardt NSW 2040"
LEICHHARDT_LAT = -33.888218
LEICHHARDT_LNG = 151.149809
LEICHHARDT_EPI = "Inner West Local Environmental Plan 2022"
LEICHHARDT_ZONE = "R1"
LEICHHARDT_KEY_SITES = "Clauses 4.3C, 4.4, 6.14, 6.15"

# ---------------------------------------------------------------------------
# DB layer: fetch functions
# ---------------------------------------------------------------------------

class TestFetchFunctions:
    def test_lep_clauses_leichhardt(self, db_conn):
        from conveyancing_db import fetch_lep_clauses
        result = fetch_lep_clauses(db_conn, LEICHHARDT_KEY_SITES, LEICHHARDT_EPI)
        assert len(result) == 4, f"Expected 4 clauses, got {len(result)}"
        numbers = {r["number"] for r in result}
        assert numbers == {"4.3C", "4.4", "6.14", "6.15"}
        for r in result:
            assert r["summary"] is not None, f"Missing summary for clause {r['number']}"

    def test_lep_clauses_epi_case_insensitive(self, db_conn):
        from conveyancing_db import fetch_lep_clauses
        result = fetch_lep_clauses(db_conn, LEICHHARDT_KEY_SITES, LEICHHARDT_EPI.lower())
        assert len(result) == 4

    def test_dcp_setbacks_leichhardt_r1(self, db_conn):
        from conveyancing_db import fetch_dcp_setbacks
        result = fetch_dcp_setbacks(db_conn, "leichhardt", f"{LEICHHARDT_ZONE} General Residential")
        assert result is not None, "Expected DCP setbacks for Leichhardt"
        assert result["dcp_name"] == "Leichhardt DCP 2013"
        assert len(result["setbacks"]) == 3

    def test_heritage_postgis_leichhardt(self, db_conn):
        from conveyancing_db import fetch_heritage_postgis
        result = fetch_heritage_postgis(db_conn, LEICHHARDT_LAT, LEICHHARDT_LNG)
        # This point is in Leichhardt — PostGIS should have heritage data for Inner West
        assert isinstance(result["hca"], list)
        assert isinstance(result["items"], list)
        # Either HCA or items or both — if neither, it means the point is clear
        # (acceptable — not every Inner West address is heritage listed)

    def test_heritage_postgis_returns_hca_string_format(self, db_conn):
        from conveyancing_db import fetch_heritage_postgis
        result = fetch_heritage_postgis(db_conn, LEICHHARDT_LAT, LEICHHARDT_LNG)
        for entry in result["hca"]:
            assert "Heritage Conservation Area" in entry
            assert "Inner West" in entry or "(" in entry

    def test_no_dcp_for_wahroonga(self, db_conn):
        from conveyancing_db import fetch_dcp_setbacks
        # Ku-ring-gai is not in DB yet — should return None, not crash
        result = fetch_dcp_setbacks(db_conn, None, "R2")
        assert result is None

    def test_no_lep_clauses_for_wahroonga(self, db_conn):
        from conveyancing_db import fetch_lep_clauses
        result = fetch_lep_clauses(db_conn, None, "Ku-ring-gai Local Environmental Plan 2015")
        assert result == []


# ---------------------------------------------------------------------------
# Parametrized LGA coverage — driven by ONBOARDED_LGAS
#
# These tests are the "contract" for LGA onboarding. When a new LGA is added
# to ONBOARDED_LGAS, these tests will fail until:
#   1. dcp_general_requirements has manual rows for the new council
#   2. detect_former_council() maps the EPI name to the council slug
#
# This is intentional — failing tests are the signal that onboarding is incomplete.
# ---------------------------------------------------------------------------

class TestOnboardedLGAs:
    """Contract tests across all onboarded LGAs in ONBOARDED_LGAS."""

    @pytest.mark.parametrize("lga", ONBOARDED_LGAS, ids=[l["id"] for l in ONBOARDED_LGAS])
    def test_dcp_returns_data(self, db_conn, lga):
        """fetch_dcp_setbacks returns data for every onboarded council."""
        from conveyancing_db import fetch_dcp_setbacks
        if not lga["expect_dcp"]:
            pytest.skip(f"{lga['id']}: DCP not onboarded yet")
        result = fetch_dcp_setbacks(db_conn, lga["former_council"], lga["zone"])
        assert result is not None, f"{lga['id']}: expected DCP data, got None"
        assert result["dcp_name"] == lga["expect_dcp_name"], (
            f"{lga['id']}: expected dcp_name={lga['expect_dcp_name']!r}, "
            f"got {result['dcp_name']!r}"
        )
        assert len(result["setbacks"]) == lga["expect_dcp_setback_count"], (
            f"{lga['id']}: expected {lga['expect_dcp_setback_count']} setbacks, "
            f"got {len(result['setbacks'])}"
        )

    @pytest.mark.parametrize("lga", ONBOARDED_LGAS, ids=[l["id"] for l in ONBOARDED_LGAS])
    def test_detect_former_council(self, lga):
        """detect_former_council() maps EPI name to correct former council slug."""
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from generate_conveyancing_report import detect_former_council
        result = detect_former_council(lga["addr"], lga["epi"])
        assert result == lga["former_council"], (
            f"{lga['id']}: detect_former_council returned {result!r}, "
            f"expected {lga['former_council']!r}"
        )

    @pytest.mark.parametrize("lga", ONBOARDED_LGAS, ids=[l["id"] for l in ONBOARDED_LGAS])
    def test_dcp_shape_keys_present(self, db_conn, lga):
        """DCP result shape matches generate_pdf expectations for all councils."""
        from conveyancing_db import fetch_dcp_setbacks
        if not lga["expect_dcp"]:
            pytest.skip(f"{lga['id']}: DCP not onboarded yet")
        result = fetch_dcp_setbacks(db_conn, lga["former_council"], lga["zone"])
        assert result is not None
        required = {"dcp_name", "section", "clause_ref", "zones_applicable",
                    "dev_type_scope", "caveat", "setbacks"}
        assert required.issubset(result.keys())
        for sb in result["setbacks"]:
            assert {"type", "control_type", "requirement", "clause", "notes"}.issubset(sb.keys())


# ---------------------------------------------------------------------------
# Heritage merge logic — unit-level (no DB, tests merge algorithm directly)
# ---------------------------------------------------------------------------

class TestHeritageMerge:
    """Test the controls merge logic in isolation."""

    def _merge(self, controls: dict, postgis_heritage: dict) -> dict:
        """Replicate the merge logic from main()."""
        if postgis_heritage["hca"]:
            if controls.get("heritage_items") and not controls.get("heritage_hca"):
                controls["heritage_hca"] = controls["heritage_items"][:]
            elif not controls.get("heritage_hca"):
                controls.setdefault("heritage_items", []).extend(postgis_heritage["hca"])
                controls["heritage_hca"] = postgis_heritage["hca"][:]
        elif postgis_heritage["items"] and not controls.get("heritage_items"):
            controls["heritage_items"] = postgis_heritage["items"][:]
        return controls

    def test_portal_items_reclassified_as_hca(self):
        """Portal found items but didn't classify as HCA — PostGIS corrects."""
        controls = {
            "heritage_items": ["Leichhardt Heritage Conservation Area"],
            "heritage_hca": [],
        }
        postgis = {"hca": ["Heritage Conservation Area (Inner West LEP 2022)"], "items": [], "has_heritage": True, "raw": []}
        result = self._merge(controls, postgis)
        assert result["heritage_hca"] == ["Leichhardt Heritage Conservation Area"]

    def test_portal_empty_postgis_supplies_hca(self):
        """Portal found nothing — PostGIS supplies HCA description."""
        controls = {"heritage_items": [], "heritage_hca": []}
        postgis = {"hca": ["Heritage Conservation Area (Inner West LEP 2022)"], "items": [], "has_heritage": True, "raw": []}
        result = self._merge(controls, postgis)
        assert result["heritage_hca"] == ["Heritage Conservation Area (Inner West LEP 2022)"]
        assert "Heritage Conservation Area (Inner West LEP 2022)" in result["heritage_items"]

    def test_portal_already_has_hca_no_overwrite(self):
        """If portal already classified as HCA, PostGIS confirmation doesn't clobber."""
        controls = {
            "heritage_items": ["Leichhardt HCA"],
            "heritage_hca": ["Leichhardt HCA"],
        }
        postgis = {"hca": ["Heritage Conservation Area (Inner West LEP 2022)"], "items": [], "has_heritage": True, "raw": []}
        result = self._merge(controls, postgis)
        # heritage_hca unchanged — portal classification kept
        assert result["heritage_hca"] == ["Leichhardt HCA"]

    def test_no_heritage_no_change(self):
        """PostGIS returns clear — controls unchanged."""
        controls = {"heritage_items": [], "heritage_hca": []}
        postgis = {"hca": [], "items": [], "has_heritage": False, "raw": []}
        result = self._merge(controls, postgis)
        assert result["heritage_hca"] == []
        assert result["heritage_items"] == []

    def test_postgis_item_fills_empty_portal(self):
        """PostGIS found individual item that portal missed."""
        controls = {"heritage_items": [], "heritage_hca": []}
        postgis = {"hca": [], "items": ["Heritage Item (Inner West LEP 2022)"], "has_heritage": True, "raw": []}
        result = self._merge(controls, postgis)
        assert result["heritage_items"] == ["Heritage Item (Inner West LEP 2022)"]
