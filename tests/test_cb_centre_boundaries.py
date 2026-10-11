"""Canterbury-Bankstown centre outlines and their key rules -- hermetic (no DB, no network).

prior-art-checked: tests the committed data file and RULES only; the build/import scripts
are exercised against the database by their own proof-after-write.
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

shapely = pytest.importorskip("shapely")
from shapely.geometry import Point, shape  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
GEOJSON = REPO / "data" / "canterbury_bankstown_precincts" / "centres.geojson"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, mod)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def centres():
    fc = json.loads(GEOJSON.read_text(encoding="utf-8"))
    return {f["properties"]["precinct_id"]: (shape(f["geometry"]), f["properties"]) for f in fc["features"]}


def test_three_centres_valid_and_in_the_council(centres):
    assert set(centres) == {"6.2", "7.5", "7.6"}
    for pid, (g, _) in centres.items():
        assert g.is_valid and not g.is_empty, pid
        x0, y0, x1, y1 = g.bounds
        assert 150.95 <= x0 and x1 <= 151.18 and -33.99 <= y0 and y1 <= -33.85, pid


def test_centres_do_not_overlap(centres):
    ids = sorted(centres)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            assert centres[a][0].intersection(centres[b][0]).area == 0, (a, b)


def test_audit_addresses_are_in_no_centre(centres):
    imp = _load("import_cb_centre_boundaries")
    assert len(imp.OUTSIDE_ALL) == 3
    for label, (x, y) in imp.OUTSIDE_ALL.items():
        hits = [pid for pid, (g, _) in centres.items() if g.contains(Point(x, y))]
        assert hits == [], label


def test_each_centre_contains_its_own_interior(centres):
    # Guards against an empty or inverted polygon passing the "outside" test above.
    for pid, (g, _) in centres.items():
        assert g.contains(g.representative_point()), pid
        assert g.area > 1e-5, pid  # > ~10 ha in degrees^2 at this latitude


def test_every_centre_carries_its_chapter_quote_and_source(centres):
    for pid, (_, p) in centres.items():
        assert p["quote"].startswith("This "), pid
        assert "as identified in Figure" in p["quote"], pid
        assert p["source"] and p["method"] in {
            "dcp_figure_georeferenced_to_cadastre", "nsw_planning_local_provisions"}, pid


def test_key_rules_match_the_outlines(centres):
    dpk = _load("derive_precinct_keys")
    # The centre rules are the constant-strategy ones; single-site chapters key through their
    # own chapter_map rule (build_site_boundaries.py) and are tested there.
    rules = [r for r in dpk.RULES
             if r["council"] == "canterbury_bankstown" and r["strategy"]["type"] == "constant"]
    keyed = {r["strategy"]["precinct_id"] for r in rules}
    assert keyed == set(centres)
    for r in rules:
        chapter = r["strategy"]["precinct_id"].replace(".", "_")
        assert f"chapter_{chapter}_" in r["where"], r["name"]


def test_former_council_resolves_to_the_rules_council_key():
    # Mirrors frontend-nextjs/lib/council-key.ts: a NULL or wrong value would fall back to
    # 'Marrickville' in precinct-service and serve another council's rules.
    imp = _load("import_cb_centre_boundaries")
    slug = re.sub(r"[^a-z0-9_]", "", re.sub(r"[-\s]+", "_", imp.FORMER_COUNCIL.lower().strip()))
    assert slug == "canterbury_bankstown"
    assert imp.LGA.lower() == "canterbury-bankstown"
