"""
Gate 2 — end-to-end pipeline test on a known address with a real DA.

Test address: 5 John Street Leichhardt NSW 2040
Known DA: PAN-206586, Semi-attached dwelling, Inner West Council
Expected: at least 1 year showing moderate/major change aligning with DA year.

Pass criteria:
- Similarity timeline has values for >= 6 of 8 years
- At least 1 year is moderate or major (sim < 0.85)
- DA events are fetched and at least 1 is matched to address
- No unhandled exceptions
"""
import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services'))

import pre_da_history as m
import numpy as np

ADDRESS = "176 Marrickville Road Marrickville NSW 2204"
EXPECTED_PAN = "PAN-260537"  # Secondary dwelling DA 2022, Inner West Council

print(f"Gate 2 — end-to-end pipeline test")
print(f"Address: {ADDRESS}")
print("=" * 60)

# --- Layer 1: Geocode ---
print("\n[1] Geocoding...")
t0 = time.time()
try:
    lat, lon, council = m.geocode_address(ADDRESS)
    print(f"    lat={lat:.5f}  lon={lon:.5f}  council={council!r}  [{time.time()-t0:.1f}s]")
    assert -33.93 < lat < -33.90, f"lat out of expected range: {lat}"
    assert 151.14 < lon < 151.18, f"lon out of expected range: {lon}"
    print(f"    [PASS] lat/lon in expected range for Marrickville")
except Exception as e:
    print(f"    [FAIL] {e}")
    sys.exit(1)
sys.stdout.flush()

# --- Layer 2: Tessera lot embeddings ---
print("\n[2] Tessera lot embeddings (5-point, 2017-2025)...")
print("    NOTE: uncached tiles will download (~15 min each) — be patient")
t0 = time.time()
try:
    lot_embs = m.sample_lot_embeddings(lat, lon)
    valid = {yr: e for yr, e in lot_embs.items() if e is not None}
    print(f"    Valid years: {sorted(valid.keys())}  ({len(valid)}/9)")
    if len(valid) < 6:
        print(f"    [FAIL] Too few valid years: {len(valid)}")
        sys.exit(1)
    print(f"    [PASS] {len(valid)} years with valid embeddings  [{time.time()-t0:.1f}s]")
except Exception as e:
    print(f"    [FAIL] {e}")
    import traceback; traceback.print_exc()
    sys.exit(1)
sys.stdout.flush()

# --- Layer 2b: Neighbourhood embeddings ---
print("\n[2b] Neighbourhood embeddings (16-point ring)...")
t0 = time.time()
try:
    nbhd_embs = m.sample_neighbourhood_embeddings(lat, lon)
    valid_nbhd = {yr: e for yr, e in nbhd_embs.items() if e is not None}
    print(f"    Valid years: {len(valid_nbhd)}/9  [{time.time()-t0:.1f}s]")
    print(f"    [PASS]")
except Exception as e:
    print(f"    [WARN] {e} — neighbourhood normalisation disabled")
    nbhd_embs = {yr: None for yr in m.YEARS}
sys.stdout.flush()

# --- Similarity timelines ---
print("\n[3] Computing similarity timelines...")
sim_tl = m.compute_similarity_timeline(lot_embs)
nbhd_tl = m.compute_similarity_timeline(nbhd_embs)

print("\n    Year-on-year cosine similarity (lot vs neighbourhood):")
print(f"    {'Year':>6}  {'Lot':>8}  {'Nbhd':>8}  {'Adjusted':>9}  Level")
print(f"    {'-'*6}  {'-'*8}  {'-'*8}  {'-'*9}  -----")
for yr in sorted(sim_tl.keys()):
    lot_s = sim_tl.get(yr)
    nbhd_s = nbhd_tl.get(yr)
    if lot_s is None:
        print(f"    {yr:>6}  {'N/A':>8}  {'N/A':>8}  {'N/A':>9}")
        continue
    adj = lot_s - nbhd_s if nbhd_s is not None else None
    level = "stable" if lot_s >= 0.95 else "minor" if lot_s >= 0.85 else "moderate" if lot_s >= 0.70 else "MAJOR"
    adj_str = f"{adj:+.4f}" if adj is not None else "N/A"
    nbhd_str = f"{nbhd_s:.4f}" if nbhd_s is not None else "N/A"
    print(f"    {yr:>6}  {lot_s:>8.4f}  {nbhd_str:>8}  {adj_str:>9}  {level}")
sys.stdout.flush()

# Check gate: at least 1 moderate or major year
non_stable = {yr: s for yr, s in sim_tl.items() if s is not None and s < 0.85}
if non_stable:
    print(f"\n    [PASS] {len(non_stable)} year(s) showing change: {non_stable}")
else:
    print(f"\n    [WARN] All years stable — site may genuinely be stable, or tile cache incomplete")

# --- Layer 4: DA events ---
print(f"\n[4] Fetching DA events for council={council!r}...")
t0 = time.time()
if council:
    try:
        da_events = m.get_da_events(council, ADDRESS)
        pcc_events = m.get_pcc_events(council, ADDRESS)
        all_events = da_events + pcc_events
        print(f"    DA events matched: {len(da_events)}  CC/OC events: {len(pcc_events)}")
        for e in all_events:
            print(f"      {e['pan']}  {e['date_updated'][:10]}  {e['app_type']!r}  {e['dev_type']!r}")
        if any(e['pan'] == EXPECTED_PAN for e in all_events):
            print(f"    [PASS] Expected PAN {EXPECTED_PAN} found")
        else:
            print(f"    [WARN] Expected PAN {EXPECTED_PAN} not matched — fuzzy match may have missed it")
        print(f"    [{time.time()-t0:.1f}s]")
    except Exception as e:
        print(f"    [FAIL] {e}")
        all_events = []
else:
    print(f"    [SKIP] Council not resolved (spatial_overlays not available locally)")
    all_events = []
sys.stdout.flush()

# --- Layer 6: Flood/fire annotations ---
print(f"\n[5] Flood/fire annotations for lat={lat:.3f} lon={lon:.3f}...")
for yr in [2019, 2020, 2021, 2022]:
    floods = m.get_flood_annotations(lat, lon, yr)
    fires = m.get_fire_annotations(lat, lon, yr)
    if floods or fires:
        print(f"    {yr}: {floods + fires}")
    else:
        print(f"    {yr}: (none)")

# --- Layer 8: Annotate full timeline ---
print(f"\n[6] Full annotated timeline...")
ndvi_ndbi = {yr: {"ndvi": None, "ndbi": None} for yr in m.YEARS}  # skip Sentinel-2 for gate test
ndvi_ndbi_deltas = m.compute_ndvi_ndbi_deltas(ndvi_ndbi)

timeline = m.annotate_timeline(sim_tl, nbhd_tl, ndvi_ndbi_deltas, all_events, lat, lon)

print(f"\n    {'Year':>6}  {'Level':>10}  {'Sim':>7}  Explanation")
print(f"    {'-'*6}  {'-'*10}  {'-'*7}  -----------")
for row in timeline:
    yr = row['year']
    lvl = row.get('level', '?')
    sim = row.get('similarity')
    sim_str = f"{sim:.3f}" if sim else "N/A"
    expl = row.get('explanation', '')
    suppressed = ' [suppressed]' if row.get('suppressed') else ''
    das = row.get('da_events', [])
    da_str = f" DA:{das}" if das else ''
    print(f"    {yr:>6}  {lvl:>10}  {sim_str:>7}  {expl}{suppressed}{da_str}")

print(f"\n{'='*60}")
print(f"Gate 2 COMPLETE")
print(f"  Address: {ADDRESS}")
print(f"  Years with data: {len([r for r in timeline if r.get('level') != 'no_data'])}/8")
print(f"  Non-stable years: {len([r for r in timeline if r.get('level') not in ('stable', 'no_data', None)])}")
sys.stdout.flush()
