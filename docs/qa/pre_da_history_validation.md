# Pre-DA Site History — 5-Pass QA Validation Report

**Pipeline:** `services/pre_da_history.py`
**Frontend:** `frontend-nextjs/components/tools/PreDAHistoryTool.tsx`
**PDF:** `frontend-nextjs/lib/pdf/pre-da-history-report.tsx`
**Date:** 2026-05-21
**Auditor:** Lawrence McDonell + Claude (AI-assisted review)
**Status:** Complete — 8 bugs found, 8 fixed

---

## Pass 1 — Data Source Verification

**Objective:** Every API call returns what we claim. Response schemas match expectations. Failure modes are handled.

### Sources Queried

| # | Source | Method | Verified |
|---|---|---|---|
| 1 | NSW Planning Portal (geocode: address → propId → lot geometry) | Live API — `/ePlanningApi/address` + `/ePlanningApi/lot` | Yes |
| 2 | GeoTessera Clay v1.5 (annual satellite embeddings, 2017–2025) | Local library — `geotessera.GeoTessera().sample_embeddings_at_points()` | Yes |
| 3 | Element84 Sentinel-2 L2A (NDVI/NDBI spectral indices) | Live STAC API — `earth-search.aws.element84.com/v1` | Yes |
| 4 | NSW ePlanning Portal (DA/CDC/CC/OC events) | Live API — `api.apps1.nsw.gov.au/eplanning/data/v0/OnlineDA` + `OnlineCDC` | Yes |
| 5 | PostGIS spatial_overlays (heritage overlay) | Local DB query — `WHERE layer_type = 'heritage'` | Yes |
| 6 | PostGIS spatial_overlays (LGA/council lookup) | Local DB query — `WHERE layer_type = 'height'` | Yes |
| 7 | Esri World Imagery Wayback (SSIM for small lots <300m²) | Live tile API — `wayback.maptiles.arcgis.com` | Yes |
| 8 | Flood/fire event annotations | **Hardcoded bounding boxes** (`NSW_FLOOD_EVENTS`, `NSW_FIRE_EVENTS`) — NOT from SES/RFS API | Yes (see Bug #5-6) |

### PDF Data Sources Attribution

**Before fix:** PDF listed "NSW SES flood event records" and "NSW RFS bushfire records" — implying live feeds from those agencies. In reality, flood/fire annotations use hardcoded event bounding boxes compiled manually. Also listed "via Spatial Days" for Sentinel-2 — actual provider is Element84 Earth Search.

**After fix:** PDF now correctly attributes:
- "Sentinel-2 satellite imagery (ESA/Copernicus, via Element84 Earth Search)"
- "Flood and bushfire event annotations based on known event bounding boxes (indicative, not sourced from live SES/RFS feeds)"

### Failure Modes

- **Geocode failure:** Raises HTTP 422 with clear message. `_mark_error()` updates pre-allocated row.
- **Tessera tile missing:** Returns NaN for that year → timeline shows "no_data". Correct degradation.
- **Sentinel-2 cloud cover:** SCL mask filters contaminated scenes. If all scenes cloudy → NDVI/NDBI null for year. Falls back to Tessera-only classification.
- **ePlanning API failure:** Logged and skipped — DA events empty. Timeline still renders from satellite data.
- **DB write failure:** Raises HTTP 503 — report not stored. Correct: frontend poll would hang on 'pending' forever if write silently failed.

**Result: PASS (after 3 attribution fixes)** — all sources verified, false attributions corrected.

---

## Pass 2 — Algorithm Correctness

**Objective:** Classification logic, scoring, thresholds, and boundary conditions produce correct outputs.

### Tessera Change Detection

| Component | Implementation | Correct |
|---|---|---|
| Cosine similarity | Year-on-year embedding comparison | Yes |
| 5-point lot sampling | Centroid + 4 corners at ~16m offset | Yes |
| 8-point neighbourhood ring | ~40m from centroid, 45° spacing | Yes |
| Neighbourhood suppression | delta < 0.04 AND no strong spectral → suppress | Yes |
| Spectral escalation | Strong NDVI (<-0.15) or NDBI (>0.08) overrides "stable" | Yes |

### Change Classification Thresholds

| Threshold | Value | Purpose |
|---|---|---|
| SIM_STABLE | 0.95 | Above = no change |
| SIM_MINOR | 0.85 | Above = minor change |
| SIM_MODERATE | 0.70 | Above = moderate change |
| Below 0.70 | — | Major change |
| NDVI drop | < -0.05 | Vegetation loss |
| NDBI rise | > 0.03 | Built-up increase |

### NDVI/NDBI Change Type Matrix

| NDVI drop | NDBI rise | Classification |
|---|---|---|
| Yes | Yes | construction |
| Yes | No | vegetation |
| No | Yes | hardening |
| No | No | noise (suppress if minor/stable) |

### DA Event Matching

- Uses `rapidfuzz.fuzz.partial_ratio > 75` for address matching — reasonable threshold
- Paginated up to 10 pages (500 records) per application type
- 400ms delay between pages — polite API usage

### Wayback SSIM

- Only triggered for lots < 300m² (where Tessera 10m resolution is insufficient)
- One release per year, consecutive pair comparison
- Greyscale conversion before SSIM — correct

**Result: PASS** — all algorithms verified, thresholds are reasonable, classification logic is correct.

---

## Pass 3 — Null/Edge Case Hardening

**Objective:** Every `.get()`, `float()`, `int()`, `or default` is checked for null-value traps.

### Issues Found

| # | Location | Issue | Severity |
|---|---|---|---|
| 1 | `_get_council_from_db()` L241-268 | `conn.close()` inside try, not in finally — connection leaks on exception | Medium |
| 2 | `_mark_error()` L1253-1267 | `conn.close()` inside try, not in finally — connection leaks on commit failure | Medium |
| 3 | `geocode_address()` L323 | `lots[0]["geometry"]["rings"][0]` — no null guard on geometry/rings | Medium |

**Bug 1:** Fixed — initialise `conn = None` before try, moved `conn.close()` to finally block.

**Bug 2:** Fixed — same pattern as Bug 1.

**Bug 3:** Fixed — added `.get()` guards: `geom = lots[0].get("geometry") or {}`, `rings = geom.get("rings") or []`, with explicit ValueError if empty.

### Null Handling Verified

| Check | Location | Handling |
|---|---|---|
| Tessera embedding NaN | `_sample_embeddings_with_client()` | Filters NaN rows, returns None if all invalid |
| Sentinel-2 no scenes | `_fetch_ndvi_ndbi_year()` | Returns `{"ndvi": None, "ndbi": None}` |
| DA address match failure | `get_da_events()` | Returns empty list — timeline proceeds without DA data |
| Council not resolved | `_da_events()` inner function | Logs warning, returns empty list |
| NDVI/NDBI deltas None | `build_year_annotation()` | Explicit None checks before threshold comparison |

**Result: PASS (after 3 fixes)** — all null paths verified.

---

## Pass 4 — Connection/Resource Safety

**Objective:** No DB connection leaks, no unguarded blocking I/O in async endpoints, proper error isolation.

### Connection Handling

| Function | Pattern | Safe |
|---|---|---|
| `_get_council_from_db()` | **Was: conn.close() in try. Now: finally block.** | Yes (fixed) |
| `check_heritage_flag()` | `conn = None`, try/finally | Yes |
| `_run_pre_da_history_inner()` (main) | `conn = None`, try/finally | Yes |
| `_mark_error()` | **Was: conn.close() in try. Now: finally block.** | Yes (fixed) |

### Resource Management

- ThreadPoolExecutor bounded at `max_workers=3` (main parallel tasks) and `max_workers=5` (NDVI/NDBI per-year) — reasonable
- GeoTessera client shared between lot and neighbourhood passes, GC between passes — correct memory management
- Sentinel-2 COG fetching uses `rasterio.open()` with context managers — correct

### Error Isolation

- `_mark_error()` is best-effort, never raises — correct
- Audit trail is non-blocking — correct
- Main DB write failure raises HTTP 503 — correct (prevents frontend poll hanging)

**Result: PASS (after 2 fixes)** — all connection paths verified.

---

## Pass 5 — Output Defensibility (Language Audit)

**Objective:** Every user-facing claim is traceable to a specific data source. No interpolation or inference beyond what the data shows. No compliance determinations.

### Issues Found

| # | File | Line | Original Text | Issue | Fix |
|---|---|---|---|---|---|
| 4 | pre-da-history-report.tsx | 641 | "via Spatial Days" | False data source attribution — actual source is Element84 Earth Search | → "ESA/Copernicus, via Element84 Earth Search" |
| 5 | pre-da-history-report.tsx | 642 | "NSW SES flood event records" | False attribution — flood annotations are hardcoded bounding boxes, not from SES API | → "Flood and bushfire event annotations based on known event bounding boxes" |
| 6 | pre-da-history-report.tsx | 642 | "NSW RFS bushfire records" | Same as #5 — hardcoded events, not RFS API | → Combined with #5 fix |
| 7 | pre-da-history-report.tsx | 246 | "any works will require a Statement of Heritage Impact" | "will require" is a compliance determination — should be "may require" | → "may require" |
| 8 | pre-da-history-report.tsx | 668 | "flood risk" | "risk" implies professional risk assessment | → "flood screening" |

### Retained (No Change Needed)

| Location | Text | Reason |
|---|---|---|
| PreDAHistoryTool.tsx:507 | "No indicators of undisclosed or unapproved works were found in the data sources checked" | Properly scoped to "data sources checked" |
| PreDAHistoryTool.tsx:517 | "likely demolition, construction, or significant earthworks" | "likely" is appropriate hedging for satellite observation |
| PreDAHistoryTool.tsx:550 | "may require heritage approval under your LEP" | "may require" is correctly hedged |
| pre-da-history-report.tsx:273 | "No red flags identified in the data sources checked" | Properly scoped |
| pre-da-history-report.tsx:391 | "Suggested next steps" section | Instructions for buyer, not our compliance determination |
| pre-da-history-report.tsx:658 | "This report is for preliminary due diligence purposes only" | Correct positioning |

**Result: PASS (after 5 fixes)** — all user-facing text now describes data observations, not compliance determinations. False data source attributions corrected.

---

## Bug Register

| # | Severity | Category | Description | Status |
|---|---|---|---|---|
| 1 | Medium | Connection safety | `_get_council_from_db()` connection leak — `conn.close()` in try, not finally | FIXED |
| 2 | Medium | Connection safety | `_mark_error()` connection leak — `conn.close()` in try, not finally | FIXED |
| 3 | Medium | Null safety | `geocode_address()` unguarded access to `lots[0]["geometry"]["rings"][0]` | FIXED |
| 4 | Medium | False attribution | PDF "via Spatial Days" — actual source is Element84 Earth Search | FIXED |
| 5 | Medium | False attribution | PDF "NSW SES flood event records" — actually hardcoded event bounding boxes | FIXED |
| 6 | Medium | False attribution | PDF "NSW RFS bushfire records" — actually hardcoded event bounding boxes | FIXED |
| 7 | Low | Language | PDF "will require" heritage impact → "may require" | FIXED |
| 8 | Low | Language | PDF "flood risk" → "flood screening" | FIXED |

---

## Sign-Off

All 5 passes complete. 8 bugs found, 8 fixed:
- 2 connection leaks (council lookup, error marker)
- 1 unguarded null access (lot geometry parsing)
- 3 false data source attributions in PDF (Spatial Days, SES floods, RFS bushfires)
- 2 language fixes (compliance determination, risk language)

The Pre-DA History pipeline correctly:
- Uses 7 independent data layers with clear provenance
- Applies neighbourhood suppression to avoid false positives from systemic environmental events
- Cross-references satellite detections with DA records for corroboration
- Degrades gracefully when individual layers fail (Tessera NaN, cloud cover, API timeout)
- Writes full audit trail with per-source DataSourceQuery tracking
- Labels all outputs as data observations, not compliance determinations

**Note:** The flood/fire event annotations use hardcoded bounding boxes (MVP approach). The comment in the code notes "v2: replace with WFS polygon queries". This is correctly documented in the PDF data sources after the fix.
