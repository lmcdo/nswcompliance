"""Unit tests for the legislation-monitor refresh-runbook connector."""
from __future__ import annotations

from scripts.refresh_runbook import (
    build_refresh_runbook,
    instrument_lga,
)


class TestInstrumentLga:
    def test_naive_slug_maps_to_overlay_name(self):
        assert instrument_lga("bayside_lep_2021") == "BAYSIDE"

    def test_multiword_slug(self):
        assert instrument_lga("georges_river_lep_2021") == "GEORGES RIVER"

    def test_override_hyphenated(self):
        assert instrument_lga("canterbury_bankstown_lep_2023") == "CANTERBURY-BANKSTOWN"

    def test_override_city_of(self):
        assert instrument_lga("parramatta_lep_2023") == "CITY OF PARRAMATTA"

    def test_override_shire(self):
        assert instrument_lga("sutherland_lep_2015") == "SUTHERLAND SHIRE"
        assert instrument_lga("the_hills_lep_2019") == "THE HILLS SHIRE"

    def test_sepp_is_statewide_none(self):
        assert instrument_lga("sepp_housing_2021") is None
        assert instrument_lga("sepp_exempt_complying_2008") is None


class TestBuildRefreshRunbook:
    def test_empty_returns_empty_string(self):
        assert build_refresh_runbook([]) == ""

    def test_lep_block_has_scoped_three_command_chain(self):
        out = build_refresh_runbook([("inner_west_lep_2022", "Inner West LEP 2022")])
        # the scoped LGA must appear in every command of the chain
        assert "INNER WEST" in out
        assert "update_instrument_provisions.py --key inner_west_lep_2022" in out
        assert 'ingest_spatial_overlays.py --all-layers --lga "INNER WEST"' in out
        assert 'build_lot_search_index.py --phase all --lga "INNER WEST"' in out
        assert "--trigger legislation_change" in out

    def test_lep_uses_override_lga_not_naive(self):
        # regression: the naive transform would emit "PARRAMATTA"; must be CITY OF
        out = build_refresh_runbook([("parramatta_lep_2023", "Parramatta LEP 2023")])
        assert 'ingest_spatial_overlays.py --all-layers --lga "CITY OF PARRAMATTA"' in out
        assert '--lga "PARRAMATTA"' not in out  # the wrong, naive name

    def test_sepp_block_is_statewide_no_scoped_recompute(self):
        out = build_refresh_runbook([("sepp_housing_2021", "SEPP Housing 2021")])
        assert "STATEWIDE" in out
        assert "update_instrument_provisions.py --key sepp_housing_2021" in out
        # a SEPP must NOT emit a per-LGA build command
        assert "build_lot_search_index.py" not in out
        assert "live" in out.lower()

    def test_mixed_lep_and_sepp(self):
        out = build_refresh_runbook([
            ("bayside_lep_2021", "Bayside LEP 2021"),
            ("sepp_housing_2021", "SEPP Housing 2021"),
        ])
        assert "BAYSIDE" in out
        assert "STATEWIDE" in out
        # exactly one scoped build command (the LEP), not for the SEPP
        assert out.count("build_lot_search_index.py") == 1

    def test_runbook_leads_with_verify_first(self):
        out = build_refresh_runbook([("bayside_lep_2021", "Bayside LEP 2021")])
        assert "legislation.nsw.gov.au" in out
