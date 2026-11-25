"""Guards for the saved state map layers (data/law/maps) and the script that makes them (scripts/lmr_area/download_map_layers.py).

They pin what makes a copy trustworthy: every layer the area check asks for live is present, nothing is truncated or edited, every file fits the repo limit,
and the script never writes a partial copy.
"""
import gzip
import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts" / "lmr_area"))
import download_map_layers as dl  # noqa: E402

MAPS = REPO / "data" / "law" / "maps"
EXPECTED = {"tod_sites": 9597, "accelerated_tod": 8, "lmr_exclusion": 4, "hn_catchment": 11, "georges_catchment": 1,
            "coastal_vuln": 10, "airport_noise": 29, "heritage_shr": 1825, "gas_pipelines": 1425}
# The flood-study copy (scripts/lmr_area/export_flood_copy.py) shares the manifest but is NOT made by download_map_layers.py: the downloader must leave it exactly as it is.
FLOOD_STUDY = {"hn_pmf": 430, "hn_500aep": 393, "hn_100aep": 1607}
LIMIT = 2 * 1024 * 1024


def manifest():
    return json.loads((MAPS / "manifest.json").read_text(encoding="utf-8"))


def test_the_script_names_exactly_the_layers_the_area_check_asks_for_live():
    from services import lmr_area_inputs as inp

    assert set(dl.LAYERS) == set(EXPECTED)
    live_urls = {u.rsplit("/query", 1)[0] for u in inp.LAYERS.values()}
    for name, (url, _use) in dl.LAYERS.items():
        if name != "heritage_shr":   # the SHR layer is read live as heritage_shr by lmr_area_inputs too
            assert url in live_urls, name
    assert dl.LAYERS["heritage_shr"][0] in live_urls


def test_the_manifest_lists_every_layer_with_the_feature_counts_read_on_the_day():
    m = manifest()
    assert set(m["layers"]) == set(EXPECTED) | set(FLOOD_STUDY) and m["read_on"] >= "2026-11-18"
    for name, n in {**EXPECTED, **FLOOD_STUDY}.items():
        assert m["layers"][name]["features"] == n, name
    for name in FLOOD_STUDY:   # a dated study: its own read_on and age limit, and the tolerance it was simplified to
        meta = m["layers"][name]
        assert meta["read_on"] >= "2026-11-22" and meta["max_age_days"] == 400 and meta["simplified_to_deg"] > 0 and meta["study_date"] == "2024-05", name


def test_every_file_is_listed_unmodified_and_fits_the_repo_limit():
    listed = set()
    for name, info in manifest()["layers"].items():
        total = 0
        for f in info["files"]:
            data = (MAPS / f["file"]).read_bytes()
            assert hashlib.sha256(data).hexdigest() == f["sha256"], f["file"]
            assert len(data) == f["bytes"] and len(data) < LIMIT, f["file"]
            fc = json.loads(gzip.decompress(data))
            assert fc["type"] == "FeatureCollection" and len(fc["features"]) == f["features"], f["file"]
            total += len(fc["features"])
            listed.add(f["file"])
        assert total == info["features"], name
    on_disk = {p.name for p in MAPS.glob("*.geojson.gz")}
    assert on_disk == listed        # no stray or missing file


def test_geometry_is_present_and_in_wgs84_over_new_south_wales():
    for name in ("accelerated_tod", "lmr_exclusion", "hn_catchment"):
        for f in manifest()["layers"][name]["files"]:
            for feat in json.loads(gzip.decompress((MAPS / f["file"]).read_bytes()))["features"]:
                g = feat["geometry"]
                assert g and g["type"] in ("Polygon", "MultiPolygon")
                flat = json.dumps(g["coordinates"])
                nums = [float(x) for x in flat.replace("[", " ").replace("]", " ").replace(",", " ").split()]
                lngs, lats = nums[0::2], nums[1::2]
                assert all(140 <= x <= 155 for x in lngs) and all(-38 <= y <= -27 for y in lats), name


def test_coordinates_are_rounded_to_six_places_and_the_same_data_gives_the_same_bytes():
    assert dl.round_coords([[1.123456789, -33.1234567891], [2, 3]]) == [[1.123457, -33.123457], [2.0, 3.0]]
    a = gzip.compress(b"abc", 9, mtime=0)
    assert a == gzip.compress(b"abc", 9, mtime=0)


# ---- the script never writes a partial copy ---------------------------------------------------------------------------------------

def test_a_layer_whose_count_or_pages_cannot_be_read_is_not_saved(monkeypatch):
    monkeypatch.setattr(dl, "get", lambda url, params, tries=4: None)
    assert dl.fetch_layer("http://x") is None
    calls = []

    def fake(url, params, tries=4):
        calls.append(params)
        if params.get("returnCountOnly"):
            return {"count": 3}
        return {"features": [{"type": "Feature", "geometry": None, "properties": {"OBJECTID": 1}}]} if len(calls) == 2 else None

    monkeypatch.setattr(dl, "get", fake)
    assert dl.fetch_layer("http://x") is None      # second page failed: nothing returned, so nothing written


def test_a_service_that_repeats_a_page_is_not_saved(monkeypatch):
    """Review case: the service ignores the page offset and returns the same 2 features twice for a layer of 4."""
    def fake(url, params, tries=4):
        if params.get("returnCountOnly"):
            return {"count": 4}
        return {"features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [1, 2]}, "properties": {"OBJECTID": 1}}, {"type": "Feature", "geometry": {"type": "Point", "coordinates": [1, 2]}, "properties": {"OBJECTID": 2}}]}

    monkeypatch.setattr(dl, "get", fake)
    assert dl.fetch_layer("http://x") is None


def test_a_feature_with_no_geometry_rejects_the_layer(monkeypatch):
    """Review case: right count, unique ids, but one feature has geometry None: a saved copy would silently miss that area."""
    feat = lambda n, g: {"type": "Feature", "geometry": g, "properties": {"OBJECTID": n}}  # noqa: E731
    poly = {"type": "Polygon", "coordinates": [[[151.0, -33.0], [151.1, -33.0], [151.1, -33.1], [151.0, -33.0]]]}
    monkeypatch.setattr(dl, "get", lambda url, params, tries=4: {"count": 2} if params.get("returnCountOnly") else {"features": [feat(1, poly), feat(2, None)]})
    assert dl.fetch_layer("http://x") is None
    monkeypatch.setattr(dl, "get", lambda url, params, tries=4: {"count": 2} if params.get("returnCountOnly") else {"features": [feat(1, poly), feat(2, poly)]})
    assert dl.fetch_layer("http://x") is not None


def test_features_without_an_id_are_not_trusted(monkeypatch):
    monkeypatch.setattr(dl, "get", lambda url, params, tries=4: {"count": 1} if params.get("returnCountOnly") else {"features": [{"type": "Feature", "geometry": None, "properties": {}}]})
    assert dl.fetch_layer("http://x") is None


def test_nothing_is_overwritten_when_a_later_layer_fails(monkeypatch, tmp_path):
    """Review case: layer a is read fine, layer b fails: the old files and manifest must stay exactly as they were."""
    monkeypatch.setattr(dl, "OUT_DIR", tmp_path)
    (tmp_path / "a.geojson.gz").write_bytes(b"OLD")
    (tmp_path / "manifest.json").write_text("OLD")
    monkeypatch.setattr(dl, "LAYERS", {"a": ("http://a", "use a"), "b": ("http://b", "use b")})
    fc = {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": None, "properties": {"OBJECTID": 1}}]}
    monkeypatch.setattr(dl, "fetch_layer", lambda url: fc if url == "http://a" else None)
    assert dl.main(["--apply"]) == 1
    assert (tmp_path / "a.geojson.gz").read_bytes() == b"OLD" and (tmp_path / "manifest.json").read_text() == "OLD"


def test_a_layer_that_returns_fewer_features_than_its_count_is_not_saved(monkeypatch):
    def fake(url, params, tries=4):
        return {"count": 5} if params.get("returnCountOnly") else {"features": [{"type": "Feature", "geometry": None}] * 4}

    monkeypatch.setattr(dl, "get", fake)
    assert dl.fetch_layer("http://x") is None


def test_dry_run_writes_nothing_and_a_failed_layer_stops_the_manifest(monkeypatch, tmp_path):
    monkeypatch.setattr(dl, "OUT_DIR", tmp_path)
    monkeypatch.setattr(dl, "LAYERS", {"a": ("http://a", "use a"), "b": ("http://b", "use b")})
    fc = {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[151.0, -33.0]]]}, "properties": {}}]}
    monkeypatch.setattr(dl, "fetch_layer", lambda url: fc if url == "http://a" else None)
    assert dl.main([]) == 1 and list(tmp_path.iterdir()) == []                 # dry run, one failed
    assert dl.main(["--apply"]) == 1 and not (tmp_path / "manifest.json").exists()   # a failed layer: no manifest, so no half-trusted set
    monkeypatch.setattr(dl, "fetch_layer", lambda url: fc)
    assert dl.main(["--apply"]) == 0 and (tmp_path / "manifest.json").exists()


def test_a_layer_over_the_repo_limit_is_split_into_numbered_parts(monkeypatch, tmp_path):
    import os

    monkeypatch.setattr(dl, "OUT_DIR", tmp_path)
    monkeypatch.setattr(dl, "LAYERS", {"big": ("http://big", "use")})
    monkeypatch.setattr(dl, "REPO_FILE_LIMIT", 3000)
    rnd = os.urandom
    feats = [{"type": "Feature", "geometry": None, "properties": {"OBJECTID": n, "k": rnd(300).hex()}} for n in range(12)]   # incompressible
    monkeypatch.setattr(dl, "fetch_layer", lambda url: {"type": "FeatureCollection", "features": feats})
    assert dl.main(["--apply"]) == 0
    info = json.loads((tmp_path / "manifest.json").read_text())["layers"]["big"]
    assert len(info["files"]) > 1 and sum(f["features"] for f in info["files"]) == 12
    assert all(f["file"].startswith("big.part") for f in info["files"])


def test_the_downloader_keeps_the_flood_study_layers_it_does_not_own(tmp_path, monkeypatch):
    """Its next --apply rewrites the manifest from its own LAYERS; the flood layers must survive that, or the flood check silently stops answering."""
    import types

    src = manifest()
    out = tmp_path / "maps"
    out.mkdir()
    (out / "manifest.json").write_text(json.dumps(src), encoding="utf-8")
    monkeypatch.setattr(dl, "OUT_DIR", out)
    fc = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"OBJECTID": 1}, "geometry": {"type": "Point", "coordinates": [151.0, -33.0]}}]}
    monkeypatch.setattr(dl, "fetch_layer", lambda url: json.loads(json.dumps(fc)))
    assert dl.main(["--apply"]) == 0
    after = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    for name in FLOOD_STUDY:
        assert after["layers"][name] == src["layers"][name], name
    assert set(after["layers"]) == set(EXPECTED) | set(FLOOD_STUDY)


@pytest.mark.parametrize("content", ["{ not json", "[]", '{"read_on": "2026-11-18"}', '{"layers": []}'])
def test_the_downloader_stops_without_writing_anything_when_the_existing_manifest_cannot_be_read(tmp_path, monkeypatch, content, capsys):
    """Carrying on would delete the flood layers it does not own; it must stop, say why, and leave every file as it found it."""
    out = tmp_path / "maps"
    out.mkdir()
    (out / "manifest.json").write_text(content, encoding="utf-8")
    monkeypatch.setattr(dl, "OUT_DIR", out)
    fc = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"OBJECTID": 1}, "geometry": {"type": "Point", "coordinates": [151.0, -33.0]}}]}
    monkeypatch.setattr(dl, "fetch_layer", lambda url: json.loads(json.dumps(fc)))
    assert dl.main(["--apply"]) == 1
    assert "STOPPED" in capsys.readouterr().out
    assert (out / "manifest.json").read_text(encoding="utf-8") == content
    assert sorted(p.name for p in out.iterdir()) == ["manifest.json"]   # no layer file was written either


def test_the_downloader_may_initialise_when_there_is_no_manifest_yet(tmp_path, monkeypatch):
    out = tmp_path / "maps"
    monkeypatch.setattr(dl, "OUT_DIR", out)
    fc = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"OBJECTID": 1}, "geometry": {"type": "Point", "coordinates": [151.0, -33.0]}}]}
    monkeypatch.setattr(dl, "fetch_layer", lambda url: json.loads(json.dumps(fc)))
    assert dl.main(["--apply"]) == 0
    assert set(json.loads((out / "manifest.json").read_text(encoding="utf-8"))["layers"]) == set(EXPECTED)


def test_only_one_layer_refreshes_just_that_layer_and_dates_it_alone(tmp_path, monkeypatch):
    """--only NAME rewrites that layer's file and manifest entry (with its own read_on) and leaves every other layer, the file-wide read_on and the note exactly as they were."""
    src = manifest()
    out = tmp_path / "maps"
    out.mkdir()
    (out / "manifest.json").write_text(json.dumps(src), encoding="utf-8")
    monkeypatch.setattr(dl, "OUT_DIR", out)
    fc = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"OBJECTID": 1, "feature_name": "X"}, "geometry": {"type": "LineString", "coordinates": [[151.0, -33.0], [151.1, -33.1]]}}]}
    monkeypatch.setattr(dl, "fetch_layer", lambda url: json.loads(json.dumps(fc)))
    assert dl.main(["--only", "gas_pipelines", "--apply"]) == 0
    after = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    for name, entry in src["layers"].items():
        if name != "gas_pipelines":
            assert after["layers"][name] == entry, name
    assert after["read_on"] == src["read_on"] and after["note"] == src["note"]
    assert after["layers"]["gas_pipelines"]["features"] == 1 and after["layers"]["gas_pipelines"]["read_on"] == dl._today_utc().isoformat()
    assert [p.name for p in out.iterdir()] == sorted(["gas_pipelines.geojson.gz", "manifest.json"])   # no other layer file was written


def test_only_with_an_unknown_layer_name_or_no_name_writes_nothing_and_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(dl, "OUT_DIR", tmp_path)
    monkeypatch.setattr(dl, "fetch_layer", lambda url: (_ for _ in ()).throw(AssertionError("no layer should be fetched")))
    assert dl.main(["--only", "nope", "--apply"]) == 2
    assert dl.main(["--only"]) == 2
    assert list(tmp_path.iterdir()) == []


def test_a_one_layer_refresh_that_fails_leaves_the_manifest_alone(tmp_path, monkeypatch):
    src = manifest()
    out = tmp_path / "maps"
    out.mkdir()
    (out / "manifest.json").write_text(json.dumps(src), encoding="utf-8")
    before = (out / "manifest.json").read_text(encoding="utf-8")
    monkeypatch.setattr(dl, "OUT_DIR", out)
    monkeypatch.setattr(dl, "fetch_layer", lambda url: None)
    assert dl.main(["--only", "gas_pipelines", "--apply"]) == 1
    assert (out / "manifest.json").read_text(encoding="utf-8") == before


def test_the_downloader_dates_a_copy_by_the_utc_date_the_service_compares_against(monkeypatch):
    from datetime import datetime, timezone

    assert dl._today_utc() == datetime.now(timezone.utc).date()
