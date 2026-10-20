"""Greenweb overlay loader, its gate rule, and the DQ probe lists that must name 'greenweb'.

prior-art-checked: new tests for the new loader; test_gate_rules.py covers the other gate rules.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import dq_probe_live as probes  # noqa: E402
import gate_rules as g  # noqa: E402
import load_greenweb_overlay as gw  # noqa: E402


def test_file_is_the_five_categories_within_size_and_valid_shape():
    feats = gw.load_features()
    assert {f["properties"]["category"] for f in feats} == gw.EXPECTED_CATEGORIES
    assert gw.GEOJSON.stat().st_size < 8_000_000
    for f in feats:
        assert f["properties"]["source"] and f["properties"]["registration"]
    lon, lat = feats[0]["geometry"]["coordinates"][0][0][0]
    assert 150.5 < lon < 151.5 and -34 < lat < -33.4, "EPSG:4326 lon,lat expected"


def test_load_features_refuses_a_missing_or_duplicated_category(tmp_path):
    f = tmp_path / "x.geojson"
    geom = {"type": "Polygon", "coordinates": []}
    feats = [{"properties": {"category": c}, "geometry": geom} for c in sorted(gw.EXPECTED_CATEGORIES)]
    f.write_text(json.dumps({"features": feats[:-1]}))
    with pytest.raises(ValueError):
        gw.load_features(f)
    f.write_text(json.dumps({"features": feats + [feats[0]]}))
    with pytest.raises(ValueError):
        gw.load_features(f)


def test_loader_writes_only_greenweb_rows_and_is_dry_run_by_default():
    src = Path(gw.__file__).read_text(encoding="utf-8")
    assert "DELETE FROM spatial_overlays WHERE layer_type = %s AND lga_name = %s" in src
    assert gw.LAYER_TYPE == "greenweb" and gw.LGA_NAME == "KU-RING-GAI"
    assert 'add_argument("--commit", action="store_true"' in src
    assert "readonly=not commit" in src


def test_gate_rule_tags_part_18_as_a_greenweb_condition():
    rule = next(r for r in g.GATE_RULES if r["name"] == "krg_18_greenweb")
    assert rule["council"] == "ku_ring_gai"
    assert "section-b-part-18-biodiversity" in rule["where"]
    assert rule["set"] == {"v2_dcp_layer": "condition", "v2_site_condition_required": "greenweb"}


def test_dq_probes_treat_greenweb_as_a_condition_the_page_can_send():
    for sql in (probes._GATED_FOR_ITS_CHAPTER, probes._REACHES_NOBODY):
        assert "'riparian', 'greenweb'" in sql
