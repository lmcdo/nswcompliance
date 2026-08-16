"""QA script for services/pre_da_history.py — tests each layer in isolation."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services'))

import pre_da_history as m

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


# ---------------------------------------------------------------------------
# Layer 1 — Geocoder
# ---------------------------------------------------------------------------
section("Layer 1 — Geocoder")
try:
    lat, lon, council = m.geocode_address("14 Smith Street Marrickville NSW 2204")
    # Marrickville is Inner West — roughly lat=-33.9, lon=151.16
    assert -33.95 < lat < -33.85, f"lat out of expected range: {lat}"
    assert 151.10 < lon < 151.22, f"lon out of expected range: {lon}"
    print(f"[{PASS}] lat={lat:.5f} lon={lon:.5f} council={council!r}")
    if council:
        print(f"[{PASS}] council resolved: {council!r}")
    else:
        print(f"[WARN] council empty — DB spatial_overlays may not cover this point")
except Exception as e:
    print(f"[{FAIL}] geocode_address raised: {e}")


# ---------------------------------------------------------------------------
# Layer 2 — Tessera similarity helpers (no network — pure numpy)
# ---------------------------------------------------------------------------
section("Layer 2 — Tessera similarity helpers (unit test, no download)")
import numpy as np

def fake_embs(n_years, dims=128, seed=42):
    rng = np.random.default_rng(seed)
    years = list(range(2017, 2017 + n_years))
    base = rng.standard_normal(dims).astype(np.float32)
    embs = {}
    for i, yr in enumerate(years):
        noise = rng.standard_normal(dims).astype(np.float32) * (0.01 * i)
        e = base + noise
        embs[yr] = e / np.linalg.norm(e)
    return embs

embs = fake_embs(9)
sim_tl = m.compute_similarity_timeline(embs)
print(f"[{PASS}] similarity_timeline keys: {sorted(sim_tl.keys())}")
vals = [v for v in sim_tl.values() if v is not None]
assert all(0.0 < v <= 1.001 for v in vals), "Similarities out of expected range"
print(f"[{PASS}] Similarity range: {min(vals):.4f} – {max(vals):.4f}")

# None propagation
embs_with_gap = dict(embs)
embs_with_gap[2020] = None
sim_tl_gap = m.compute_similarity_timeline(embs_with_gap)
assert sim_tl_gap.get(2021) is None, "Expected None when prev year is missing"
print(f"[{PASS}] None propagation through gap year: OK")


# ---------------------------------------------------------------------------
# Layer 3 — NDVI/NDBI delta helper (unit test)
# ---------------------------------------------------------------------------
section("Layer 3 — NDVI/NDBI delta helper (unit test)")
ndvi_ndbi = {
    2017: {"ndvi": 0.4, "ndbi": -0.1},
    2018: {"ndvi": 0.2, "ndbi": 0.1},   # construction year
    2019: {"ndvi": 0.3, "ndbi": -0.05},
    2020: {"ndvi": None, "ndbi": None},  # cloud gap
    2021: {"ndvi": 0.38, "ndbi": -0.09},
}
deltas = m.compute_ndvi_ndbi_deltas(ndvi_ndbi)
d2018 = deltas.get(2018, {})
assert d2018.get("ndvi_delta") is not None, "2018 ndvi_delta should be computed"
assert d2018["ndvi_delta"] < 0, "2018 should show vegetation drop"
assert d2018["ndbi_delta"] > 0, "2018 should show built-up increase"
print(f"[{PASS}] 2018 ndvi_delta={d2018['ndvi_delta']:.3f} ndbi_delta={d2018['ndbi_delta']:.3f}")

d2021 = deltas.get(2021, {})
assert d2021.get("ndvi_delta") is None, "2021 delta should be None (prev year missing)"
print(f"[{PASS}] None propagation through cloud gap: OK")


# ---------------------------------------------------------------------------
# Layer 4 — ePlanning filter format (live API call, 1 page)
# ---------------------------------------------------------------------------
section("Layer 4 — ePlanning API (live, 1 page)")
try:
    batch = m._fetch_eplanning_page(
        "OnlineDA",
        {"CouncilName": ["Inner West Council"]},
        1,
    )
    print(f"[{PASS}] _fetch_eplanning_page: {len(batch)} records returned")
    if batch:
        flat = m._extract_da_fields(batch[0])
        print(f"[{PASS}] _extract_da_fields: pan={flat['pan']} address={flat['address']!r} "
              f"lat={flat['lat']} lon={flat['lon']} dev_type={flat['dev_type']!r}")
        # Check council filter is actually working
        councils = set()
        for rec in batch:
            loc_council = (rec.get("Council") or {}).get("CouncilName", "?")
            councils.add(loc_council)
        print(f"       Councils in result: {councils}")
        if len(councils) == 1 and "Inner West" in list(councils)[0]:
            print(f"[{PASS}] Council filter working correctly")
        else:
            print(f"[WARN] Council filter may not be restricting results — got: {councils}")
except Exception as e:
    print(f"[{FAIL}] _fetch_eplanning_page raised: {e}")


# ---------------------------------------------------------------------------
# Layer 6 — Flood/fire annotation (unit test)
# ---------------------------------------------------------------------------
section("Layer 6 — Flood/fire annotation (unit test)")
# Lismore lat/lon, 2022 Northern Rivers flood
flood_ann = m.get_flood_annotations(-28.8, 153.28, 2022)
assert any("Northern Rivers" in a for a in flood_ann), f"Expected Northern Rivers flood: {flood_ann}"
print(f"[{PASS}] Flood annotation Lismore 2022: {flood_ann}")

# Inner West (Sydney) — should NOT get Northern Rivers annotation
no_flood = m.get_flood_annotations(-33.9, 151.15, 2022)
inner_west_northern_rivers = [a for a in no_flood if "Northern Rivers" in a]
assert not inner_west_northern_rivers, f"Inner West should not get Northern Rivers: {no_flood}"
print(f"[{PASS}] Inner West 2022 flood (should not include NR): {no_flood}")

# Black Summer 2020 — should annotate Blue Mountains area
fire_ann = m.get_fire_annotations(-33.7, 150.3, 2020)
assert any("Black Summer" in a for a in fire_ann), f"Expected Black Summer: {fire_ann}"
print(f"[{PASS}] Fire annotation Blue Mountains 2020: {fire_ann}")


# ---------------------------------------------------------------------------
# Layer 7 — Wayback releases fetch (live)
# ---------------------------------------------------------------------------
section("Layer 7 — Wayback releases (live fetch)")
try:
    releases = m.get_wayback_releases()
    print(f"[{PASS}] get_wayback_releases: {len(releases)} releases")
    pre2020 = [r for r in releases if r['date'][:4] <= '2019']
    post2024 = [r for r in releases if r['date'][:4] >= '2024']
    print(f"       Pre-2020: {len(pre2020)}  Post-2024: {len(post2024)}")
    print(f"       Earliest: {releases[0]['date']}  Latest: {releases[-1]['date']}")
    print(f"       First: releaseNum={releases[0]['releaseNum']} date={releases[0]['date']}")

    # Tile test: fetch one tile at Marrickville
    rel_2017 = next((r for r in releases if r['date'][:4] == '2017'), None)
    rel_2025 = next((r for r in reversed(releases) if r['date'][:4] == '2025'), None)
    for label, rel in [('2017', rel_2017), ('2025', rel_2025)]:
        if rel:
            img = m.fetch_wayback_tile(rel['releaseNum'], -33.9139, 151.1554)
            if img:
                print(f"[{PASS}] Wayback tile {label} (M={rel['releaseNum']}): {img.size} {img.mode}")
            else:
                print(f"[FAIL] Wayback tile {label}: fetch returned None")
        else:
            print(f"[SKIP] No {label} release found")
except Exception as e:
    print(f"[{FAIL}] Wayback raised: {e}")


# ---------------------------------------------------------------------------
# Layer 8 — build_year_annotation (unit tests)
# ---------------------------------------------------------------------------
section("Layer 8 — build_year_annotation (unit tests)")

# Case A: stable year, no DA
ann = m.build_year_annotation(2022, 0.972, None, None, None, [], [], [])
assert ann['level'] == 'stable', f"Expected stable: {ann}"
print(f"[{PASS}] Case A (stable): level={ann['level']} label={ann['label']!r}")

# Case B: neighbourhood suppression
ann_supp = m.build_year_annotation(2019, 0.88, 0.87, None, None, [], [], [])
assert ann_supp.get('suppressed'), f"Expected suppression: {ann_supp}"
print(f"[{PASS}] Case B (neighbourhood suppression): suppressed={ann_supp['suppressed']}")

# Case C: construction year — Tessera drops, NDVI drops, NDBI rises, DA present
da_events = [{"pan": "PAN-123", "status": "Determination", "app_type": "Development Application",
               "dev_type": "Alterations and additions to residential development",
               "date_updated": "2022-03-01", "address": "14 Smith St", "suburb": "MARRICKVILLE",
               "lon": 151.15, "lat": -33.90}]
ann_da = m.build_year_annotation(2022, 0.68, None, -0.12, 0.08, da_events, [], [])
assert ann_da['level'] == 'major', f"Expected major: {ann_da}"
assert ann_da['change_type'] == 'construction', f"Expected construction: {ann_da}"
assert 'PAN-123' in ann_da['da_events'], f"Expected PAN in da_events: {ann_da}"
print(f"[{PASS}] Case C (construction + DA): level={ann_da['level']} type={ann_da['change_type']} explanation={ann_da.get('explanation')!r}")

# Case D: vegetation change + tree removal DA
tree_da = [{"pan": "PAN-456", "status": "Approved", "app_type": "Development Application",
             "dev_type": "Tree removal", "date_updated": "2021-08-01",
             "address": "14 Smith St", "suburb": "MARRICKVILLE",
             "lon": 151.15, "lat": -33.90}]
ann_tree = m.build_year_annotation(2021, 0.78, None, -0.10, 0.00, tree_da, [], [])
assert ann_tree['level'] == 'minor', f"Expected downgraded to minor: {ann_tree}"
assert 'tree' in ann_tree.get('explanation', '').lower(), f"Expected tree in explanation: {ann_tree}"
print(f"[{PASS}] Case D (tree removal DA): level={ann_tree['level']} explanation={ann_tree.get('explanation')!r}")

# Case E: flood event annotation (Hawkesbury 2022)
ann_flood = m.build_year_annotation(2022, 0.72, None, -0.08, 0.02, [],
                                     ["Known flood event: February–March 2022 Hawkesbury-Nepean Floods"], [])
assert ann_flood['level'] == 'moderate', f"Expected moderate: {ann_flood}"
assert 'Hawkesbury' in ann_flood.get('explanation', ''), f"Expected flood in explanation: {ann_flood}"
print(f"[{PASS}] Case E (flood annotation): level={ann_flood['level']} explanation={ann_flood.get('explanation')!r}")

# Case F: NDVI/NDBI both stable → noise → suppress if minor
ann_noise = m.build_year_annotation(2020, 0.89, None, 0.01, -0.01, [], [], [])
assert ann_noise['level'] == 'stable', f"Expected noise suppressed to stable: {ann_noise}"
assert ann_noise.get('change_type') == 'noise', f"Expected noise type: {ann_noise}"
print(f"[{PASS}] Case F (noise suppression): level={ann_noise['level']} type={ann_noise['change_type']}")

print("\n" + "="*60)
print("  QA COMPLETE")
print("="*60)

sys.stdout.flush()
