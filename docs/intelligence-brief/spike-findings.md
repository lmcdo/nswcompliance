# Intelligence Brief Spike — Findings

**Date:** 2026-05-26
**Addresses tested:** 20
**Total runtime:** 580s (avg 29s/address)
**Raw data:** `docs/intelligence-brief/spike-results.json`

---

## Critical Findings (must fix before Stage 1)

### Finding 1: DB Connection Poisoning — Silent Total Failure

**Severity:** CRITICAL
**What happened:** The first `fetch_heritage_postgis` call hit an error (likely the `tax_thresholds` query from the regulatory freshness check poisoned the transaction). After that, EVERY subsequent PostGIS function (`fetch_dcp_setbacks`, `fetch_heritage_postgis`) returned empty results with no crash — just a warning `current transaction is aborted, commands ignored until end of transaction block`.

**Impact:** ALL 20 addresses got zero DCP setback data and zero heritage PostGIS data. This is a **silent total failure** — the response looks valid but is missing critical data.

**Root cause:** Single psycopg2 connection shared across all calls without `autocommit=True` or per-function `conn.rollback()`. One failed query poisons the entire transaction.

**Fix required:** Either:
- (a) Set `conn.autocommit = True` in the spike/orchestrator, OR
- (b) Each DB function wraps its query in a try/except with `conn.rollback()` on failure, OR
- (c) Each function opens its own cursor and handles errors independently

**Schema implication:** The orchestrator MUST use autocommit or independent connections per function. This is not a "nice to have" — without it, a single PostGIS query failure silently kills all downstream DB-dependent data.

---

### Finding 2: Heritage Dual-Source Gap

**Severity:** HIGH
**What happened:** Heritage data comes from TWO independent sources:
1. **Planning Portal** `parse_controls` → `heritage_items` list (from layerintersect API)
2. **PostGIS** `spatial_overlays` → `heritage` layer type (from ingested EPI data)

These sources DON'T always agree. The spike found:
- Windsor: heritage in BOTH Portal (3 items) AND PostGIS (spatial overlay)
- Balmain: heritage in Portal (1 item) but NOT in PostGIS spatial_overlays
- Haberfield: heritage in Portal (1 item) but NOT in PostGIS spatial_overlays
- Newcastle: heritage in Portal (2 items) but NOT in PostGIS spatial_overlays
- Manly: heritage in Portal (2 items) but NOT in PostGIS spatial_overlays

**Impact:** Compound constraint rules that check ONLY `spatial_overlays` for heritage would miss 4 out of 5 heritage properties. The compound constraint evaluation must check BOTH sources.

**Fix required:** `evaluate_compound_constraints` must use:
```python
has_heritage = bool(controls.get("heritage_items")) or "heritage" in overlay_types
```
(Already implemented in the spike script — confirmed working.)

**Schema implication:** The intelligence brief response should include `heritage_source: "portal" | "postgis" | "both"` to distinguish coverage.

---

### Finding 3: Shadow Latency Dominates Response Time

**Severity:** HIGH (UX, not correctness)
**What happened:** Shadow pipeline averages 20.3s per address (max 31.2s). This is 70% of total response time. Without shadow, average would be ~8.7s.

**Latency breakdown (averages):**
| Source | Avg | Max |
|---|---|---|
| shadow | 20.34s | 31.23s |
| nearby_das | 4.07s | 25.05s |
| overlays (PostGIS) | 2.89s | 10.57s |
| controls (Portal) | 0.57s | 1.04s |
| resolve_address | 0.51s | 1.36s |
| strata | 0.35s | 1.14s |
| valuation | 0.23s | 0.85s |

**Impact:** The implementation procedure puts shadow in the free tier (Stage 2.6) because it's "planning-derived, not satellite." But at 20s it makes the free tier response unacceptably slow.

**Options:**
1. Move shadow to paid tier (simplest, but reduces free tier value)
2. Make shadow async — return planning data immediately, shadow loads later
3. Optimize the shadow pipeline (Railway cold start may be a factor)
4. Cache shadow results aggressively (shadow only changes when LEP height changes)

**Schema implication:** Response schema must support `loading` state per section, not just `available | not_available`.

---

### Finding 4: Nearby DAs All Zero

**Severity:** MEDIUM
**What happened:** All 20 addresses returned 0 nearby DAs. The ePlanning API was called successfully (no errors) but returned empty results.

**Possible causes:**
1. Council name extraction from `zone_epi` may not match ePlanning API's `CouncilName` parameter
2. The API's date filter (365 days) may be too narrow for councils with low DA volume
3. Some addresses are in LGAs where ePlanning data is sparse

**Impact:** Cannot validate Fix C (DA-shadow interaction compound constraint). The DA-shadow rule never fires because there are no DAs to evaluate.

**Fix required:** Debug `get_nearby_das` with a known high-DA-volume address (e.g., central Sydney). May need to check council name normalization.

---

### Finding 5: Strata Heuristic Partially Works

**Severity:** MEDIUM
**What happened:** 5 addresses classified as strata:
| Address | lot_area | plan | Classification | Correct? |
|---|---|---|---|---|
| 12 Victoria Rd, Marrickville | 6,580m² | SP81199 | apartment_strata | Likely yes (MU1 zone, 23m height) |
| 1 Stanmore Rd, Stanmore | 525.7m² | SP30364 | strata_house | Likely yes (R1, small lot) |
| 1 Smith St, Summer Hill | 3,415m² | SP49675 | apartment_strata | Likely yes (R3, 12.5m height, large lot) |
| 41 Porter St, N. Wollongong | 499.5m² | SP77492 | strata_house | Likely yes (R2, small lot) |
| 15 King St, Newcastle | 1,107m² | SP1533 | strata_house | UNCLEAR — MU1 zone, 10m height, 2 heritage items. Could be commercial strata. |

**The lot_area > 1500 threshold** correctly separated small-lot strata (houses/townhouses) from large-lot strata (apartment blocks) in 4/5 cases. Newcastle is the edge case.

**Improvement:** Add zone to the heuristic — MU1/B1/B2 strata is almost certainly commercial/mixed, regardless of lot size.

---

### Finding 6: DCP Data Validation Blocked

**Severity:** MEDIUM (blocked by Finding 1)
**What happened:** DB connection poisoning meant ALL `fetch_dcp_setbacks` calls returned empty. Cannot validate DCP data availability for any LGA.

**After fixing Finding 1:** Re-run spike to validate:
- Inner West addresses → DCP data should be present
- Non-onboarded LGAs → DCP should be absent with gap disclosure
- Boundary suburb LGA slugs → correct slug → correct DCP data

---

## Compound Constraint Validation

| Rule | Fired? | Correct? | Notes |
|---|---|---|---|
| heritage_flood | Yes (Windsor) | Yes | Heritage item + 100AEP flood overlay |
| heritage_bushfire | No | Expected — no test address had both | Need address with heritage HCA + bushfire |
| tod_heritage | No | Expected — no TOD overlay in test data | `tod_precinct` layer may not be populated |
| zone_permits_higher_density | Yes (3 addresses) | Yes | R3 Summer Hill, R4 Lakemba, R3 Baulkham Hills |
| marginal_lot_size | No | ISSUE — Wollongong lot_size overlay=449 but VG lot_area=499.5 | Two different lot area sources disagree |
| da_shadow_interaction | No | Cannot test — zero DAs returned | Blocked by Finding 4 |

**Marginal lot size discrepancy:** The spatial_overlays `lot_size` layer shows 449m² for Wollongong, but VG API returns 499.5m². The compound constraint checks `overlay.value_numeric` but `calc_feasibility` uses `valuation.lot_area_m2`. These are different numbers from different sources. The schema must decide which is authoritative.

---

## Schema Design Implications

1. **Heritage source tracking** — must record `portal`, `postgis`, or `both`
2. **Per-section loading state** — `available | loading | not_available | error`
3. **Lot area source** — must specify whether from Cadastre overlay, VG API, or survey
4. **Compound constraints** must check controls AND overlays for heritage
5. **DB connection** — autocommit or per-function error isolation, non-negotiable
6. **Shadow** — either async or cached, cannot gate free tier at 20s

---

## Next Steps

1. **Fix DB connection issue** — add `autocommit=True` in orchestrator (Finding 1)
2. **Re-run spike** with fixed DB connection to validate DCP + heritage PostGIS
3. **Debug nearby DAs** — test with known high-volume LGA (Finding 4)
4. **Find heritage+bushfire test address** — spatial query or manual research
5. **Decide shadow strategy** — async vs cache vs paid-only
6. **Proceed to Stage 1** with these findings informing schema design
