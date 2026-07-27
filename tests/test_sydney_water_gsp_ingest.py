"""Unit tests for the Sydney Water GSP ingest pure-logic functions.

Covers expected / edge / failure cases for the transforms that decide what lands in
`sydney_water_gsp_servicing`. No DB, no network — the risky pieces are the price
parse, the status derivation (which drives user-facing serviceability wording), and
the geometry coercion. These are the functions a silent bug would corrupt.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

# The ingest module imports shapely at top level. The pre-push suite runs under a
# system python without native geo deps (conftest_mocks stubs psycopg2/requests/pyproj,
# not shapely), so skip this file there — it runs under venv_linux and in CI where
# shapely is installed. Mirrors the rasterio importorskip in test_flood_truth.
pytest.importorskip("shapely")

# Load the ingest module directly from scripts/ (no package __init__ there).
_MOD_PATH = Path(__file__).resolve().parent.parent / "scripts" / "ingest_sydney_water_gsp.py"
_spec = importlib.util.spec_from_file_location("gsp_ingest", _MOD_PATH)
gsp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gsp)


# ---------------------------------------------------------------- parse_dsp_price
class TestParseDspPrice:
    def test_full_price_with_html_tail(self):
        raw = ("$17,686.52 Refer to the <a href='/x'>Land development</a> page for the "
               "current DSP price including CPI adjustments.")
        assert gsp.parse_dsp_price(raw) == 17686.52

    def test_zero_is_valid_not_none(self):
        # $0 is a real value (already-serviced areas) — must not collapse to None.
        assert gsp.parse_dsp_price("$0 Refer to the page.") == 0.0

    def test_no_dollar_figure_returns_none(self):
        raw = "Refer to the <a href='/x'>Land development</a> page for the DSP area and price."
        assert gsp.parse_dsp_price(raw) is None

    def test_none_input(self):
        assert gsp.parse_dsp_price(None) is None

    def test_empty_string(self):
        assert gsp.parse_dsp_price("") is None

    def test_thousands_separator_stripped(self):
        assert gsp.parse_dsp_price("$24,472.33 extra") == 24472.33

    def test_bare_dollar_no_tail(self):
        assert gsp.parse_dsp_price("$888.41") == 888.41


# ------------------------------------------------------------------ derive_status
class TestDeriveStatus:
    @pytest.mark.parametrize("stage,expected", [
        ("Design & Deliver", "IN_DELIVERY"),
        ("Concept Planning", "PLANNED"),
        ("Option Planning", "PLANNED"),
        ("Strategic Planning", "PLANNED"),
    ])
    def test_stage_ladder(self, stage, expected):
        status, constrained = gsp.derive_status(stage, None)
        assert status == expected
        assert constrained is False

    def test_growth_precinct_boundary_is_no_current_project(self):
        status, constrained = gsp.derive_status(
            "Growth precinct boundary. No current Sydney Water projects in this area", None)
        assert status == "NO_CURRENT_PROJECT"
        assert constrained is False

    def test_capacity_constraint_sets_flag_not_status(self):
        # constrained is a separate overlay — it must NOT change the base status_code.
        status, constrained = gsp.derive_status(
            "Design & Deliver",
            "There are capacity and timescale constraints in this area that may affect servicing")
        assert status == "IN_DELIVERY"
        assert constrained is True

    def test_dphi_note_is_not_constrained(self):
        # The narrow flag must ignore the 'under investigation' note.
        status, constrained = gsp.derive_status(
            "Design & Deliver", "Under investigation by DPHI. Sydney Water is undertaking studies")
        assert status == "IN_DELIVERY"
        assert constrained is False

    def test_unmapped_stage_is_unknown(self):
        status, constrained = gsp.derive_status("Something Unexpected", None)
        assert status == "UNKNOWN_STAGE"
        assert constrained is False

    def test_none_stage_is_unknown(self):
        status, constrained = gsp.derive_status(None, None)
        assert status == "UNKNOWN_STAGE"
        assert constrained is False

    def test_constraint_match_is_case_insensitive(self):
        _, constrained = gsp.derive_status(
            "Concept Planning", "CAPACITY AND TIMESCALE CONSTRAINTS apply here")
        assert constrained is True


# -------------------------------------------------------------------------- clean
class TestClean:
    def test_strips_html_tags(self):
        assert gsp.clean("<a href='/x'>Nepean River</a>") == "Nepean River"

    def test_none_input(self):
        assert gsp.clean(None) is None

    def test_trims_whitespace(self):
        assert gsp.clean("  South West Growth Area  ") == "South West Growth Area"

    def test_empty_string_returns_none(self):
        assert gsp.clean("") is None

    def test_tags_only_returns_none(self):
        assert gsp.clean("<b></b>") is None


# --------------------------------------------------------- geom_to_multipolygon_wkt
SQUARE = {"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]}
MULTI = {"type": "MultiPolygon",
         "coordinates": [[[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]]}
# Self-intersecting bow-tie — invalid until buffer(0) repair, then two triangles.
BOWTIE = {"type": "Polygon", "coordinates": [[[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]]]}


class TestGeomToMultipolygonWkt:
    def test_polygon_becomes_multipolygon(self):
        assert gsp.geom_to_multipolygon_wkt(SQUARE).startswith("MULTIPOLYGON")

    def test_multipolygon_stays_multipolygon(self):
        assert gsp.geom_to_multipolygon_wkt(MULTI).startswith("MULTIPOLYGON")

    def test_invalid_bowtie_repaired_to_multipolygon(self):
        wkt = gsp.geom_to_multipolygon_wkt(BOWTIE)
        assert wkt.startswith("MULTIPOLYGON")

    def test_invalid_bowtie_preserves_both_lobes(self):
        # make_valid on a bow-tie yields two triangles; both must survive (buffer(0)
        # could keep only one — silent footprint loss).
        from shapely import wkt as shp_wkt
        mp = shp_wkt.loads(gsp.geom_to_multipolygon_wkt(BOWTIE))
        assert len(mp.geoms) == 2

    def test_empty_geometry_raises(self):
        empty = {"type": "Polygon", "coordinates": []}
        with pytest.raises(ValueError):
            gsp.geom_to_multipolygon_wkt(empty)

    def test_point_geometry_raises(self):
        with pytest.raises(ValueError):
            gsp.geom_to_multipolygon_wkt({"type": "Point", "coordinates": [0, 0]})
