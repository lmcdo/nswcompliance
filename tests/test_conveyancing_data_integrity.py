"""
Adversarial tests for conveyancing data integrity fixes:
  Fix #22 — boundary suburb mapping (Glebe, Alexandria, etc.)
  Fix #21 — PostGIS cross-validation of former council
  Fix #23 — heritage merge logic (items vs HCA)

These tests target silent wrong results, not crashes.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# Ensure scripts/ and services/ are importable
_project_root = Path(__file__).parent.parent
_scripts_dir = _project_root / "scripts"
_services_dir = _project_root / "services"
sys.path.insert(0, str(_scripts_dir))
sys.path.insert(0, str(_services_dir))


# ── Fix #22: Suburb mapping data errors ──────────────────────────────────────


class TestSuburbMapping:
    """Verify boundary suburbs are NOT in the text-based mapping."""

    def test_glebe_not_in_suburb_mapping(self):
        """Glebe is City of Sydney, not Inner West. Was mapped to marrickville."""
        from generate_conveyancing_report import SUBURB_TO_FORMER_COUNCIL

        assert "glebe" not in SUBURB_TO_FORMER_COUNCIL, (
            "Glebe is in City of Sydney LGA — must not be in Inner West suburb mapping"
        )

    def test_alexandria_not_in_suburb_mapping(self):
        """Alexandria is City of Sydney, not Inner West."""
        from generate_conveyancing_report import SUBURB_TO_FORMER_COUNCIL

        assert "alexandria" not in SUBURB_TO_FORMER_COUNCIL

    def test_erskineville_not_in_suburb_mapping(self):
        """Erskineville is City of Sydney, not Inner West."""
        from generate_conveyancing_report import SUBURB_TO_FORMER_COUNCIL

        assert "erskineville" not in SUBURB_TO_FORMER_COUNCIL

    def test_camperdown_not_in_suburb_mapping(self):
        """Camperdown is split between Inner West and City of Sydney."""
        from generate_conveyancing_report import SUBURB_TO_FORMER_COUNCIL

        assert "camperdown" not in SUBURB_TO_FORMER_COUNCIL

    def test_stanmore_not_in_suburb_mapping(self):
        """Stanmore is split between Inner West and City of Sydney."""
        from generate_conveyancing_report import SUBURB_TO_FORMER_COUNCIL

        assert "stanmore" not in SUBURB_TO_FORMER_COUNCIL

    def test_newtown_not_in_suburb_mapping(self):
        """Newtown is split — text matching can't determine which side."""
        from generate_conveyancing_report import SUBURB_TO_FORMER_COUNCIL

        assert "newtown" not in SUBURB_TO_FORMER_COUNCIL

    def test_st_peters_not_in_suburb_mapping(self):
        """St Peters is split between Inner West and City of Sydney."""
        from generate_conveyancing_report import SUBURB_TO_FORMER_COUNCIL

        assert "st peters" not in SUBURB_TO_FORMER_COUNCIL

    def test_unambiguous_suburbs_still_mapped(self):
        """Suburbs fully within Inner West must still resolve correctly."""
        from generate_conveyancing_report import SUBURB_TO_FORMER_COUNCIL

        # Marrickville precinct
        assert SUBURB_TO_FORMER_COUNCIL["marrickville"] == "marrickville"
        assert SUBURB_TO_FORMER_COUNCIL["dulwich hill"] == "marrickville"
        assert SUBURB_TO_FORMER_COUNCIL["enmore"] == "marrickville"
        # Leichhardt precinct
        assert SUBURB_TO_FORMER_COUNCIL["leichhardt"] == "leichhardt"
        assert SUBURB_TO_FORMER_COUNCIL["balmain"] == "leichhardt"
        assert SUBURB_TO_FORMER_COUNCIL["annandale"] == "leichhardt"
        # Ashfield precinct
        assert SUBURB_TO_FORMER_COUNCIL["ashfield"] == "ashfield"
        assert SUBURB_TO_FORMER_COUNCIL["summer hill"] == "ashfield"

    def test_detect_former_council_returns_none_for_boundary_suburb(self):
        """Boundary suburbs should return None from text matching (PostGIS resolves later)."""
        from generate_conveyancing_report import detect_former_council

        result = detect_former_council(
            "100 King St, Newtown NSW 2042",
            zone_epi="INNER WEST LOCAL ENVIRONMENTAL PLAN 2022",
        )
        assert result is None, (
            "Newtown is a boundary suburb — text matching must return None, "
            "PostGIS cross-validation resolves the correct former council"
        )

    def test_detect_former_council_unambiguous_suburb_still_works(self):
        """Unambiguous suburbs must still resolve via text matching."""
        from generate_conveyancing_report import detect_former_council

        result = detect_former_council(
            "42 Marrickville Rd, Marrickville NSW 2204",
            zone_epi="INNER WEST LOCAL ENVIRONMENTAL PLAN 2022",
        )
        assert result == "marrickville"

    def test_address_containing_removed_suburb_as_street_name(self):
        """'42 Stanmore Road, Enmore' should resolve via 'enmore', not fail on 'stanmore'."""
        from generate_conveyancing_report import detect_former_council

        result = detect_former_council(
            "42 Stanmore Rd, Enmore NSW 2042",
            zone_epi="INNER WEST LOCAL ENVIRONMENTAL PLAN 2022",
        )
        # "stanmore" not in mapping, but "enmore" is — should match enmore → marrickville
        assert result == "marrickville"


# ── Fix #22b: lga_lookup.py keeps boundary suburbs (PostGIS-validated) ───────


class TestLgaLookupSuburbMapping:
    """lga_lookup.py _IW_SUBURB_TO_FORMER retains boundary suburbs because
    it's only consulted AFTER PostGIS confirms the point is in Inner West."""

    def test_boundary_suburbs_in_postgis_validated_mapping(self):
        """Boundary suburbs must exist in lga_lookup (PostGIS pre-validated)."""
        from lga_lookup import _IW_SUBURB_TO_FORMER

        # These were removed from generate_conveyancing_report.py but KEPT here
        assert "newtown" in _IW_SUBURB_TO_FORMER
        assert "stanmore" in _IW_SUBURB_TO_FORMER
        assert "camperdown" in _IW_SUBURB_TO_FORMER
        assert "st peters" in _IW_SUBURB_TO_FORMER
        assert "erskineville" in _IW_SUBURB_TO_FORMER

    def test_glebe_not_in_postgis_validated_mapping(self):
        """Glebe is entirely in City of Sydney — not even PostGIS-validated."""
        from lga_lookup import _IW_SUBURB_TO_FORMER

        assert "glebe" not in _IW_SUBURB_TO_FORMER

    def test_alexandria_not_in_postgis_validated_mapping(self):
        """Alexandria is entirely in City of Sydney."""
        from lga_lookup import _IW_SUBURB_TO_FORMER

        assert "alexandria" not in _IW_SUBURB_TO_FORMER


# ── Fix #21: PostGIS cross-validation ────────────────────────────────────────


class TestPostGISCrossValidation:
    """Test _validate_former_council_postgis logic.

    psycopg2 is imported inside the function body, so we patch it via
    sys.modules (already mocked by conftest_mocks). We patch lookup_lga
    at the conveyancing module level where it's imported.
    """

    def _get_validator(self):
        from conveyancing import _validate_former_council_postgis
        return _validate_former_council_postgis

    def _run_with_postgis(self, text_slug, lat, lng, address, zone_epi, lga_result):
        """Run validator with mocked PostGIS lookup returning lga_result."""
        validate = self._get_validator()

        # psycopg2 is already a MagicMock in sys.modules (conftest_mocks).
        # Just configure its connect() return value.
        import psycopg2
        mock_conn = MagicMock()
        original_connect = psycopg2.connect
        psycopg2.connect = MagicMock(return_value=mock_conn)

        try:
            with patch.dict("os.environ", {"DATABASE_URL": "postgresql://test"}), \
                 patch("conveyancing.lookup_lga", return_value=lga_result):
                result = validate(text_slug, lat, lng, address, zone_epi)
        finally:
            psycopg2.connect = original_connect

        return result

    def test_postgis_overrides_wrong_inner_west_match(self):
        """Property in City of Sydney wrongly matched to marrickville — PostGIS corrects."""
        result = self._run_with_postgis(
            text_slug="marrickville",
            lat=-33.8841, lng=151.1812,
            address="42 Glebe Point Rd, Glebe NSW 2037",
            zone_epi="INNER WEST LOCAL ENVIRONMENTAL PLAN 2022",
            lga_result={"lga_name": "Sydney", "lga_slug": "sydney", "has_dcp_setbacks": False},
        )
        assert result is None, (
            "PostGIS says Sydney, not Inner West — text match must be overridden to None"
        )

    def test_postgis_confirms_correct_inner_west_match(self):
        """Property genuinely in Inner West — PostGIS confirms, text match preserved."""
        result = self._run_with_postgis(
            text_slug="marrickville",
            lat=-33.8988, lng=151.1554,
            address="42 Marrickville Rd, Marrickville NSW 2204",
            zone_epi="INNER WEST LOCAL ENVIRONMENTAL PLAN 2022",
            lga_result={"lga_name": "Inner West", "lga_slug": "marrickville", "has_dcp_setbacks": True},
        )
        assert result == "marrickville"

    def test_postgis_resolves_unmapped_boundary_suburb(self):
        """Boundary suburb (newtown) returns None from text, PostGIS resolves to marrickville."""
        result = self._run_with_postgis(
            text_slug=None,  # detect_former_council returned None (newtown removed from text)
            lat=-33.8977, lng=151.1793,
            address="100 King St, Newtown NSW 2042",
            zone_epi="INNER WEST LOCAL ENVIRONMENTAL PLAN 2022",
            lga_result={"lga_name": "Inner West", "lga_slug": "marrickville", "has_dcp_setbacks": True},
        )
        assert result == "marrickville", (
            "PostGIS confirmed Inner West + disambiguated to marrickville — must return slug"
        )

    def test_postgis_undisambiguated_inner_west_returns_none(self):
        """PostGIS says Inner West but can't disambiguate to former council — returns None."""
        result = self._run_with_postgis(
            text_slug=None,
            lat=-33.90, lng=151.17,
            address="Unknown Address",
            zone_epi="INNER WEST LOCAL ENVIRONMENTAL PLAN 2022",
            lga_result={"lga_name": "Inner West", "lga_slug": "inner_west", "has_dcp_setbacks": True},
        )
        assert result is None

    def test_postgis_db_failure_falls_back_to_text_slug(self):
        """DB connection failure — must fall back to text match, not crash."""
        validate = self._get_validator()

        import psycopg2
        original_connect = psycopg2.connect
        psycopg2.connect = MagicMock(side_effect=Exception("Connection refused"))
        try:
            with patch.dict("os.environ", {"DATABASE_URL": "postgresql://test"}):
                result = validate(
                    text_slug="marrickville",
                    lat=-33.8988, lng=151.1554,
                    address="42 Marrickville Rd, Marrickville NSW 2204",
                    zone_epi="INNER WEST LOCAL ENVIRONMENTAL PLAN 2022",
                )
        finally:
            psycopg2.connect = original_connect

        assert result == "marrickville"

    def test_no_database_url_passes_through_text_slug(self):
        """Without DATABASE_URL, PostGIS validation is skipped — text match used as-is."""
        validate = self._get_validator()
        import os
        old = os.environ.pop("DATABASE_URL", None)
        try:
            result = validate(
                text_slug="leichhardt",
                lat=-33.88, lng=151.15,
                address="42 Norton St, Leichhardt NSW 2040",
                zone_epi="INNER WEST LOCAL ENVIRONMENTAL PLAN 2022",
            )
        finally:
            if old is not None:
                os.environ["DATABASE_URL"] = old

        assert result == "leichhardt"

    def test_non_inner_west_slug_passes_through_unvalidated(self):
        """Non-Inner-West slugs (waverley, etc.) are returned as-is regardless of PostGIS."""
        result = self._run_with_postgis(
            text_slug="waverley",
            lat=-33.8983, lng=151.2533,
            address="42 Bondi Rd, Bondi NSW 2026",
            zone_epi="WAVERLEY LOCAL ENVIRONMENTAL PLAN 2012",
            lga_result={"lga_name": "Waverley", "lga_slug": "waverley", "has_dcp_setbacks": True},
        )
        assert result == "waverley"

    def test_postgis_empty_lga_name_does_not_override(self):
        """PostGIS returns empty lga_name — must NOT override a valid text match."""
        result = self._run_with_postgis(
            text_slug="marrickville",
            lat=-33.8988, lng=151.1554,
            address="42 Marrickville Rd, Marrickville NSW 2204",
            zone_epi="INNER WEST LOCAL ENVIRONMENTAL PLAN 2022",
            lga_result={"lga_name": None, "lga_slug": None, "has_dcp_setbacks": False},
        )
        assert result == "marrickville"


# ── Fix #23: Heritage merge logic ────────────────────────────────────────────


class TestHeritageMerge:
    """Test the heritage merge logic in the PDF endpoint."""

    def _merge_heritage(self, controls: dict, postgis_heritage: dict) -> dict:
        """Apply the same merge logic as conveyancing.py:500-512."""
        # Reproduce the exact merge logic from conveyancing.py
        if postgis_heritage["hca"]:
            existing_hca = controls.get("heritage_hca") or []
            merged_hca = list(dict.fromkeys(existing_hca + postgis_heritage["hca"]))
            controls["heritage_hca"] = merged_hca
            existing_items = controls.get("heritage_items") or []
            controls["heritage_items"] = list(dict.fromkeys(existing_items + postgis_heritage["hca"]))
        if postgis_heritage["items"]:
            existing_items = controls.get("heritage_items") or []
            controls["heritage_items"] = list(dict.fromkeys(existing_items + postgis_heritage["items"]))
        return controls

    def test_heritage_item_not_reclassified_as_hca(self):
        """Portal heritage item must NOT be moved to heritage_hca when PostGIS finds HCA.

        This was the original bug: code assumed portal items were HCA
        when PostGIS also found HCA on the same lot.

        Portal returns raw strings like "Item I123" (from layerintersect).
        PostGIS returns formatted strings like "Heritage Conservation Area (...)".
        """
        controls = {
            # Portal-style: raw heritage item name from layerintersect
            "heritage_items": ["Item I123"],
            # No heritage_hca from portal (portal didn't find a conservation area)
        }
        postgis = {
            # PostGIS-style: formatted from fetch_heritage_postgis
            "hca": ["Heritage Conservation Area (Inner West LEP 2022)"],
            "items": [],
            "has_heritage": True,
            "raw": [],
        }

        result = self._merge_heritage(controls, postgis)

        # PostGIS HCA goes into heritage_hca
        assert "Heritage Conservation Area (Inner West LEP 2022)" in result["heritage_hca"]
        # Portal item stays in heritage_items but must NOT be in heritage_hca
        assert "Item I123" in result["heritage_items"]
        assert "Item I123" not in result["heritage_hca"]
        # heritage_hca should only have the PostGIS HCA
        assert len(result["heritage_hca"]) == 1

    def test_postgis_hca_added_to_existing_portal_hca(self):
        """When both portal and PostGIS have HCA, they merge without duplication."""
        controls = {
            "heritage_hca": ["Heritage Conservation Area (Portal)"],
            "heritage_items": ["Heritage Conservation Area (Portal)"],
        }
        postgis = {
            "hca": ["Heritage Conservation Area (PostGIS)"],
            "items": [],
            "has_heritage": True,
            "raw": [],
        }

        result = self._merge_heritage(controls, postgis)

        assert len(result["heritage_hca"]) == 2
        assert "Heritage Conservation Area (Portal)" in result["heritage_hca"]
        assert "Heritage Conservation Area (PostGIS)" in result["heritage_hca"]

    def test_duplicate_hca_deduplicated(self):
        """Identical HCA entries from portal and PostGIS appear once."""
        controls = {
            "heritage_hca": ["Heritage Conservation Area (Inner West LEP 2022)"],
            "heritage_items": ["Heritage Conservation Area (Inner West LEP 2022)"],
        }
        postgis = {
            "hca": ["Heritage Conservation Area (Inner West LEP 2022)"],
            "items": [],
            "has_heritage": True,
            "raw": [],
        }

        result = self._merge_heritage(controls, postgis)

        assert result["heritage_hca"].count("Heritage Conservation Area (Inner West LEP 2022)") == 1

    def test_postgis_items_merge_with_portal_items(self):
        """PostGIS individual items merge into portal items list."""
        controls = {
            "heritage_items": ["Item - General (Portal)"],
        }
        postgis = {
            "hca": [],
            "items": ["Item - Landscape (PostGIS)"],
            "has_heritage": True,
            "raw": [],
        }

        result = self._merge_heritage(controls, postgis)

        assert "Item - General (Portal)" in result["heritage_items"]
        assert "Item - Landscape (PostGIS)" in result["heritage_items"]
        # No HCA should be created
        assert "heritage_hca" not in result

    def test_empty_postgis_no_changes(self):
        """When PostGIS returns no heritage, controls are unchanged."""
        controls = {
            "heritage_items": ["Item - General (Portal)"],
            "heritage_hca": ["HCA (Portal)"],
        }
        postgis = {
            "hca": [],
            "items": [],
            "has_heritage": False,
            "raw": [],
        }

        result = self._merge_heritage(controls, postgis)

        assert result["heritage_items"] == ["Item - General (Portal)"]
        assert result["heritage_hca"] == ["HCA (Portal)"]

    def test_both_hca_and_items_from_postgis(self):
        """PostGIS returns both HCA and individual items — both merge correctly."""
        controls = {}
        postgis = {
            "hca": ["Heritage Conservation Area (LEP)"],
            "items": ["Item - General (LEP)"],
            "has_heritage": True,
            "raw": [],
        }

        result = self._merge_heritage(controls, postgis)

        assert result["heritage_hca"] == ["Heritage Conservation Area (LEP)"]
        assert "Heritage Conservation Area (LEP)" in result["heritage_items"]
        assert "Item - General (LEP)" in result["heritage_items"]

    def test_no_portal_heritage_postgis_provides_all(self):
        """No heritage from portal — PostGIS populates both fields."""
        controls = {}  # No heritage_items, no heritage_hca
        postgis = {
            "hca": ["Heritage Conservation Area (PostGIS)"],
            "items": ["Item - General (PostGIS)"],
            "has_heritage": True,
            "raw": [],
        }

        result = self._merge_heritage(controls, postgis)

        assert result["heritage_hca"] == ["Heritage Conservation Area (PostGIS)"]
        assert len(result["heritage_items"]) == 2


class TestWingecarribeeOnboarding:
    """Wingecarribee numeric controls (Bowral/Mittagong/Moss Vale town plans) —
    the slug must derive from the EPI name and be accepted by the onboarding gate,
    so fetch_dcp_setbacks serves the loaded rows (insert_wingecarribee_setbacks.py)."""

    def test_wingecarribee_slug_is_onboarded(self):
        from generate_conveyancing_report import DCP_ONBOARDED_SLUGS
        assert "wingecarribee" in DCP_ONBOARDED_SLUGS

    def test_detect_former_council_resolves_wingecarribee_from_epi(self):
        from generate_conveyancing_report import detect_former_council
        result = detect_former_council(
            "38 Park Road, Bowral NSW 2576",
            zone_epi="Wingecarribee Local Environmental Plan 2010",
        )
        assert result == "wingecarribee"
