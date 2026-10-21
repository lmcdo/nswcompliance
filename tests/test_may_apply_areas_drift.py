"""frontend-nextjs/shared/may-apply-areas.json must match the data file."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import export_may_apply_areas as ex  # noqa: E402


def test_shared_file_matches_data_file():
    assert ex.TARGET.read_text(encoding="utf-8") == ex.render(ex.build()), (
        "run: python scripts/export_may_apply_areas.py"
    )


def test_build_groups_by_council_and_normalised_suburb(tmp_path):
    src = tmp_path / "s.json"
    src.write_text(json.dumps({"areas": [
        {"council": "c", "suburb": "winston  hills", "area_id": "b"},
        {"council": "c", "suburb": "WINSTON HILLS", "area_id": "a"},
    ]}), encoding="utf-8")
    assert [a["area_id"] for a in ex.build(src)["c"]["WINSTON HILLS"]] == ["a", "b"]


def test_exporter_uses_the_frontend_suburb_form_and_fans_out_suburbs(tmp_path):
    import json
    import export_may_apply_areas as ex
    src = tmp_path / "s.json"
    src.write_text(json.dumps({"areas": [
        {"area_id": "a", "council": "northern_beaches", "suburbs": ["Freshwater", "Harbord, NSW 2096"]},
        {"area_id": "b", "council": "northern_beaches", "suburbs": [], "shown_to_everyone": True},
    ]}), encoding="utf-8")
    out = ex.build(src)
    assert set(out["northern_beaches"]) == {"FRESHWATER", "HARBORD"}
    assert ex.canonical_suburb("Dee Why, NSW 2099") == "DEE WHY"


def test_an_area_with_no_suburb_must_say_it_shows_to_everyone(tmp_path):
    import json
    import pytest
    import export_may_apply_areas as ex
    src = tmp_path / "s.json"
    src.write_text(json.dumps({"areas": [{"area_id": "typo", "council": "x", "subrub": ["A"]}]}), encoding="utf-8")
    with pytest.raises(ValueError, match="typo"):
        ex.build(src)


def test_map_image_url_only_when_base_url_is_set(tmp_path):
    import export_may_apply_areas as ex
    src = tmp_path / "s.json"
    src.write_text(json.dumps({"areas": [
        {"council": "c", "suburb": "X", "area_id": "a"},
        {"council": "c", "suburb": "X", "area_id": "b"},
    ]}), encoding="utf-8")
    idx = tmp_path / "i.json"
    idx.write_text(json.dumps({"a": {"file": "a.png", "reviewed": True}, "b": {"skipped": "no figure"},
                               "c": {"file": "c.png"}}), encoding="utf-8")
    off = ex.build(src, base_url="", maps_index=idx)["c"]["X"]
    assert all("map_image_url" not in r for r in off)
    on = {r["area_id"]: r for r in ex.build(src, base_url="https://img.test/", maps_index=idx)["c"]["X"]}
    assert on["a"]["map_image_url"] == "https://img.test/may-apply-maps/a.png"
    assert "map_image_url" not in on["b"]


def test_unreviewed_image_is_never_published(tmp_path):
    # A rerun of the heuristic renderer writes files without 'reviewed'; they must not reach the page.
    import export_may_apply_areas as ex
    src = tmp_path / "s.json"
    src.write_text(json.dumps({"areas": [{"council": "c", "suburb": "X", "area_id": "c"}]}), encoding="utf-8")
    idx = tmp_path / "i.json"
    idx.write_text(json.dumps({"c": {"file": "c.png"}}), encoding="utf-8")
    assert "map_image_url" not in ex.build(src, base_url="https://img.test/", maps_index=idx)["c"]["X"][0]


def test_base_url_points_at_the_uploaded_maps():
    # Uploaded 2026-10-21 (scripts/upload_may_apply_maps.py --commit): the public R2 folder of the PNGs.
    import export_may_apply_areas as ex
    # The exporter adds the 'may-apply-maps/' folder itself, so the base is the bucket root (a doubled folder broke
    # every image, found in review 2026-10-21).
    assert ex.MAP_BASE_URL.startswith("https://") and "may-apply-maps" not in ex.MAP_BASE_URL
    import json
    from pathlib import Path
    shared = json.loads((Path(__file__).resolve().parent.parent / "frontend-nextjs/shared/may-apply-areas.json").read_text(encoding="utf-8"))
    urls = [a["map_image_url"] for c in shared.values() for l in c.values() for a in l if a.get("map_image_url")]
    assert urls and all(u.count("may-apply-maps/") == 1 for u in urls)
