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
        {"area_id": "b", "council": "northern_beaches", "suburbs": []},
    ]}), encoding="utf-8")
    out = ex.build(src)
    assert set(out["northern_beaches"]) == {"FRESHWATER", "HARBORD"}
    assert ex.canonical_suburb("Dee Why, NSW 2099") == "DEE WHY"
