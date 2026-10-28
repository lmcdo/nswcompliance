"""The Copernicus ingest keeps only the observed flood extent.

On 2026-10-28 copernicus_flood_events held EMSR567 as one 86,349 km2 shape:
the ingest had merged every layer in each vector ZIP -- the satellite image
footprint (up to 48,000 km2 per area), area of interest, roads, buildings,
land use. The observedEventA layers alone are 333.8 km2. These tests build a
ZIP with the real layer names from EMSR567_AOI01 and check that only the
flood layer survives, and that an extent too big to be flooded land, or none
at all, is refused before anything is written.
"""
from __future__ import annotations

import io
import json
import sys
import zipfile
from pathlib import Path

import pytest
from shapely.geometry import MultiPolygon, box

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import ingest_copernicus_ems as ems  # noqa: E402

PREFIX = "EMSR567_AOI01_DEL_PRODUCT_"
# Every layer in the real AOI01 package (listed 2026-10-28).
LAYERS = ["areaOfInterestA", "builtUpA", "facilitiesA", "facilitiesL", "hydrographyA",
          "hydrographyL", "imageFootprintA", "naturalLandUseA", "observedEventA",
          "transportationL"]

FLOOD = box(153.27, -28.82, 153.29, -28.80)       # ~4.3 km2 near Lismore
FOOTPRINT = box(152.0, -30.0, 154.0, -28.0)       # ~43,000 km2, like imageFootprintA


def _fc(geom) -> bytes:
    return json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {}, "geometry": geom.__geo_interface__}]}).encode()


def _zip(layers: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for lay, geom in layers.items():
            zf.writestr(f"{PREFIX}{lay}_r1_v1.json", _fc(geom))
            zf.writestr(f"{PREFIX}{lay}_r1_v1.shp", b"not read")
    return buf.getvalue()


def test_only_the_observed_flood_layer_is_read():
    layers = {lay: FOOTPRINT for lay in LAYERS}
    layers["observedEventA"] = FLOOD
    geoms = ems._read_observed_geometries(_zip(layers))
    assert len(geoms) == 1
    assert geoms[0].equals(FLOOD)


def test_layer_names():
    assert ems.is_observed_layer(f"sub/{PREFIX}observedEventA_r1_v1.json")
    for lay in LAYERS:
        if lay != "observedEventA":
            assert not ems.is_observed_layer(f"{PREFIX}{lay}_r1_v1.json"), lay
    assert not ems.is_observed_layer(f"{PREFIX}observedEventA_r1_v1.shp")


def test_a_zip_without_the_flood_layer_gives_nothing():
    assert ems._read_observed_geometries(_zip({lay: FOOTPRINT for lay in LAYERS
                                               if lay != "observedEventA"})) == []


def test_area_matches_a_known_box():
    # 0.1 deg x 0.1 deg at 33 S: 11.12 km x 9.33 km = 103.7 km2.
    assert ems.area_km2(box(151.0, -33.05, 151.1, -32.95)) == pytest.approx(103.7, rel=0.01)


def test_area_subtracts_holes():
    outer = box(151.0, -33.1, 151.2, -32.9)
    holed = outer.difference(box(151.05, -33.05, 151.15, -32.95))
    assert ems.area_km2(holed) == pytest.approx(ems.area_km2(outer) * 0.75, rel=0.01)


def test_footprint_sized_extent_is_refused():
    with pytest.raises(ems.ExtentRejected, match="> 5,000 km2"):
        ems.check_extent("EMSR567", MultiPolygon([FOOTPRINT]))


def test_no_extent_is_refused():
    with pytest.raises(ems.ExtentRejected, match="no observed flood extent"):
        ems.check_extent("EMSR567", None)
    with pytest.raises(ems.ExtentRejected, match="no observed flood extent"):
        ems.check_extent("EMSR567", MultiPolygon())


def test_projected_coordinates_are_refused():
    # Metres (e.g. EPSG:3577) read as degrees would be wildly out of range.
    with pytest.raises(ems.ExtentRejected, match="not lon/lat"):
        ems.check_extent("EMSR567", box(2_000_000, -3_300_000, 2_000_100, -3_299_900))


def test_a_real_sized_extent_passes():
    assert ems.check_extent("EMSR567", MultiPolygon([FLOOD])) == pytest.approx(4.3, rel=0.05)


def test_refused_extent_writes_nothing(monkeypatch):
    """build fails before ingest_emsr567 reaches the insert."""
    monkeypatch.setattr(ems, "_fetch_s3_zip_geometries", lambda url: [FOOTPRINT])
    called = []
    monkeypatch.setattr(ems, "_insert_row", lambda *a: called.append(a))
    with pytest.raises(ems.ExtentRejected):
        ems.ingest_emsr567(ems.SOURCE_MAP["EMSR567"], conn=object())
    assert called == []
