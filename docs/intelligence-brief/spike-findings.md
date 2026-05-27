# Intelligence Brief — Pre-Implementation Spike Findings

**Date:** 2026-05-27
**Script:** `scripts/intelligence_brief_spike.py`
**Addresses tested:** 20 (Inner West, Katoomba, Wahroonga, Hurstville, Windsor, Sydney CBD, Granville, Kurrajong Heights)
**Full results:** `docs/intelligence-brief/spike-results.json`

---

## Executive Summary

20/20 addresses resolved successfully. All pipeline functions returned data. Shadow worked for all 20. LGA detection 100% accurate for onboarded councils. One confirmed strata misclassification. Compound constraint rules need refinement (heritage+bushfire didn't fire when expected). Overlay reporting is correct but was initially misinterpreted (LGA coverage vs property intersection).

**Conclusion:** Stage 1 schema design can proceed. The fixes below are refinements, not blockers.

---

## 1. Compound Constraints — Rules Need Refinement

### What fired

| Address | Rule | Meaning |
|---------|------|---------|
| 15 Fox Valley Rd, Wahroonga | `heritage_postgis_only` | Heritage in PostGIS but not in portal — data gap signal |
| 3/22 Carlton Cres, Summer Hill | `heritage_postgis_only` | Same — PostGIS heritage near property, portal didn't return it |
| 1 George St, Windsor | `heritage_hca_flood` | Heritage conservation area + flood zone — correct compound |

### What didn't fire but should have

- **Heritage + bushfire (Katoomba, Wahroonga):** The rule checks `controls["heritage_hca"]` (conservation areas from portal), but the portal returned heritage *items* not *HCA* for these addresses. The bushfire overlay is also only checked against `overlay_types` which is LGA-level coverage, not property-level intersection.

### Fix applied (PR #384)

1. **DONE:** `heritage_flood` rule now fires on `heritage_items` OR `heritage_hca` (was HCA-only). Rule renamed from `heritage_hca_flood` to `heritage_flood`. Heritage source tracked in output.
2. **Not a bug:** Bushfire/flood check was already using property-level PostGIS intersection (`overlays` list), not LGA coverage (`overlay_types`). The spike initially misread the distinction — see clarification below.
3. Portal `flood_epi` flag was already the primary flood signal — no change needed.

### Clarification: overlay_types vs overlay features

The spike initially appeared to show a bug: addresses with 20 overlay_types but 0 features. This is correct behaviour:
- `overlay_types` (from `covered_layers`) = set of layer types ingested for that LGA (from `spatial_overlays_coverage` table) — "this council has bushfire data"
- `overlays` (results list) = actual features that intersect this specific property — "this property is IN a bushfire zone"

An urban Marrickville lot with 0 environmental overlay features is expected — the lot simply isn't inside any flood/bushfire/biodiversity polygon. The coverage set is used by the UI to distinguish "clear" (data exists, property isn't affected) from "not mapped" (no data for this council).

---

## 2. Strata Heuristic — One Confirmed Misclassification

### Heuristic: `is_apartment = strata AND lot_area > 1500m²`

| Address | Lot Area | Classification | Expected | Correct? |
|---------|----------|---------------|----------|----------|
| 5/1 Treacy St, Hurstville | 1,555m² | apartment | apartment | Yes |
| 3/22 Carlton Cres, Summer Hill | 2,140m² | apartment | development (townhouse) | **No** |
| 2/45 Alt St, Ashfield | 2,055m² | apartment | unclear (community title edge case) | Ambiguous |

### Why the heuristic fails

The 1,500m² threshold catches high-rise apartments (large parent lot = apartment block) but also catches townhouse complexes on large strata-subdivided lots. 3/22 Carlton Crescent is a strata townhouse on a 2,140m² parent lot — the heuristic sees "strata + big lot" and concludes apartment, but it's a townhouse with its own ground-floor access and potential for a granny flat.

### Fix applied (PR #384)

The Cadastre API already returns individual SP/CP lot features for every lot in a strata plan. `get_cadastral_info` now counts lots sharing the same `planlabel` and returns `sp_lot_count`. `classify_strata` uses this directly:

- **>6 lots** → `apartment` (high-density block)
- **2-6 lots** → `development` (townhouse/villa — GF potential)
- **1 lot or no count** → `strata_unknown`

Carlton Cres (3 lots on same SP) now correctly classifies as `development`.

---

## 3. LGA Detection — 100% Accurate

14 addresses returned an LGA slug. All correct:

| Suburb | Expected | Got | Correct? |
|--------|----------|-----|----------|
| Marrickville (x8) | marrickville | marrickville | Yes |
| Leichhardt (x2) | leichhardt | leichhardt | Yes |
| Summer Hill | ashfield | ashfield | Yes |
| Ashfield | ashfield | ashfield | Yes |
| Wahroonga | ku_ring_gai | ku_ring_gai | Yes |
| Stanmore (boundary) | marrickville | marrickville | Yes |
| Dulwich Hill (boundary) | marrickville | marrickville | Yes |

6 addresses returned `None` — all correctly, because those LGAs (Blue Mountains, Georges River, Hawkesbury, City of Sydney, Cumberland, Penrith) are not in `ZONE_EPI_TO_LGA_SLUG`. This is by design — DCP setbacks only exist for onboarded councils.

**No spatial fix needed for v1.** The EPI-name matching is sufficient for current coverage.

---

## 4. Timing Analysis

| Step | Avg (s) | Max (s) | % of total | Notes |
|------|---------|---------|------------|-------|
| resolve | 0.47 | 0.72 | 2% | Planning Portal address + lot API |
| controls | 0.48 | 1.44 | 2% | Portal layerintersect |
| valuation | 0.20 | 0.67 | 1% | NSW SIX Maps valuation API |
| strata | 1.28 | 10.09 | 5% | Cadastre API — one timeout |
| overlays | 2.74 | 8.26 | 11% | PostGIS spatial queries (biggest DB cost) |
| DAs (local DB) | 0.08 | 0.68 | <1% | Bounding box + Haversine — fast |
| heritage DB | 0.11 | 0.88 | <1% | PostGIS heritage query |
| LEP DB | 0.01 | 0.08 | <1% | Fast |
| DCP DB | 0.06 | 0.15 | <1% | Fast |
| LGA | 0.00 | 0.00 | <1% | In-memory string match |
| **shadow** | **18.64** | **33.12** | **77%** | Railway geometric model — dominates |

### Why shadow is slow and nothing else is

Shadow is the ONLY satellite product wired into the intelligence brief pipeline. It makes an HTTP POST to Railway (`PYTHON_API_URL/pipeline/shadow`), which runs:
1. pybdshadow geometric shadow polygon calculation for multiple sun positions (solstice/equinox x morning/midday/afternoon)
2. pvlib solar position calculation for each time point
3. Building envelope model from LEP height limits
4. Result assembly and response

The other satellite products (granny flat, solar yield, flood truth, threat radar, climate risk) are NOT called — they are separate standalone pipelines not yet integrated into the intelligence brief. Shadow was already part of the conveyancing report, so it transferred over when the intelligence brief was built on top of the conveyancing orchestrator.

Everything else is either a fast API call (<0.5s per portal endpoint) or a PostGIS query (<0.1s for indexed spatial lookups). The overlay queries are the slowest DB operation at 2.74s avg because they run multiple ST_Contains/ST_Intersects checks across large polygon datasets.

### Optimisation opportunities

1. **Parallelisation (DONE — PR #382):** Shadow + all DB queries now run concurrently via ThreadPoolExecutor. Saves ~3-5s wall time.
2. **Shadow caching:** Same address with same height limit = same shadow result. Cache in `shadow_reports` table with TTL. Would eliminate 18s for repeat lookups.
3. **Overlay query batching:** Currently runs 5+ sequential PostGIS queries (environmental, classified road, TOD, APU, key sites). Could batch into a single SQL with UNION ALL.
4. **Strata API timeout:** One address took 10s on Cadastre API. Add circuit breaker or reduce timeout from 10s to 5s with retry.
5. **Future satellite products:** When granny flat / flood truth / climate risk are wired in, they MUST run in the parallel fan-out (ThreadPoolExecutor), not sequentially. Each adds 5-30s if serial.

---

## 5. Data Availability

### DAs: 18/20 addresses had nearby DAs

Only Katoomba (0) and Kurrajong Heights (0) had no DAs — rural/regional areas with very few applications in the 50K-row local DB. All Inner West addresses had 1-8 DAs within 200m. The PR #382 local DB query at 0.08s avg is working as designed (vs 18s from the old live ePlanning API call).

### Heritage PostGIS: 7/20 addresses

Heritage items found near: Marrickville (#1), Wahroonga (#5), Leichhardt (#6, #17), Dulwich Hill (#8), Summer Hill (#10), Windsor (#18). This depends on the `spatial_overlays` heritage layer having features near the lat/lng. 13 addresses had no nearby heritage in PostGIS — but some of these DID have heritage items from the Planning Portal (`controls.heritage_items`). The two sources are complementary:
- Portal heritage = items affecting THIS lot (from layerintersect)
- PostGIS heritage = items NEAR this lot (from spatial proximity query)

Both are useful for the intelligence brief. The `heritage_postgis_only` compound rule fires when PostGIS finds heritage that the portal missed — a genuine data gap signal.

### DCP setbacks: 14/20 addresses

All Inner West + Ku-ring-gai addresses returned DCP setbacks. The 6 without are non-onboarded LGAs (correct behaviour — DCP tab shows interest form for those).

### Valuation: 18/20 addresses

Two addresses returned None for lot_area and land_value:
- 88 Marrickville Rd (#14) — SP2 Infrastructure zoning, likely a rail corridor or utility lot
- 123 Bells Line of Road (#15) — rural, possibly the VG API doesn't cover this propId

---

## 6. Schema Implications for Stage 1

Based on these findings:

1. **Strata classification field:** Use `strata_type ENUM ('apartment', 'development', 'ambiguous', 'not_strata')` with `strata_lot_area_m2` and `strata_source` fields. Don't force binary apartment/development for v1.

2. **Compound constraints:** Store fired rules as JSONB array, not boolean flags. Rules will evolve and new combinations will be discovered. Schema: `compound_constraints JSONB DEFAULT '[]'`.

3. **Overlay data:** Store both `overlay_coverage` (set of layer types ingested for this LGA) and `overlay_hits` (features that actually intersect). The distinction matters for "clear" vs "not mapped" display.

4. **Shadow result:** Store as optional JSONB. 77% of runtime — caching is the biggest optimisation win. Include `shadow_computed_at` timestamp for cache invalidation.

5. **DA snapshot:** Store nearby DA count and nearest DA at report generation time. DAs change — the count at report time is what the user paid for.

---

## 7. Demo-Ready Addresses (for Inner West Nest meeting)

Based on spike results, these Inner West addresses show the most data and are good demo candidates:

| Address | Why it's good for demo |
|---------|----------------------|
| 100 Stanmore Rd, Stanmore | R2, 467m², DCP setbacks, 8 nearby DAs, shadow, boundary suburb correctly resolved |
| 42 Norton St, Leichhardt | E1 mixed use, full DCP, heritage in PostGIS, 2 DAs, shadow |
| 10 Hollands Ave, Marrickville | R2, heritage DB confirmed, 4 DAs, shadow, full DCP |
| 15 Marrickville Rd, Dulwich Hill | E1, 17m height, FSR 2.2, heritage, 5 DAs — shows density controls |
