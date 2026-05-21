# Flood Truth Engine — QA Validation Report

**Pipeline:** `services/flood_truth.py`
**Frontend:** `frontend-nextjs/components/tools/FloodTool.tsx`
**PDF report:** `frontend-nextjs/lib/pdf/flood-truth-report.tsx`
**Date:** 2026-05-21
**Validator:** Claude (automated 5-pass validation)
**Test coverage:** 70 tests in `tests/test_flood_truth.py`

---

## Pass 1 — Data Source Verification

**Objective:** Confirm every data source listed in the code is correctly identified, queried with correct parameters, and attributed accurately.

### Sources verified

| # | Source | Endpoint / Method | Verified |
|---|---|---|---|
| 1 | NSW SEED EPI Flood WFS | `mapprod3.environment.nsw.gov.au` Layer 1 ArcGIS REST, point-in-polygon | Yes |
| 2 | Copernicus EMS flood events | PostGIS `copernicus_flood_events` table, `ST_Intersects` | Yes |
| 3 | JRC Global Surface Water | GCS tiles `storage.googleapis.com`, rasterio vsicurl point sample | Yes |
| 4 | DEA Water Observations (WOfS) | `ows.dea.ga.gov.au` WCS GetCoverage, `ga_ls_wo_fq_myear_3` | Yes |
| 5 | BOM Water Data Online | SOS2 XML API, pre-seeded 13 NSW gauges, Haversine nearest | Yes |
| 6 | SES / Council flood studies | PostGIS `spatial_overlays` where `layer_type = 'flood'` | Yes |
| 7 | Flood study rasters | Local `.tif`/`.asc` files (Hawkesbury, Tweed, Wollongong) | Yes |
| 8 | NSW 5m DEM | `maps.six.nsw.gov.au` ImageServer identify endpoint | Yes |
| 9 | Sentinel-1 RTC | Microsoft Planetary Computer (batch only, Phase 3B) | Yes (documented as not yet active for on-demand) |

### Findings

- **No false attributions found.** The PDF `DataCurrencyTable` accurately lists all queried sources.
- Each source has a corresponding `DataSourceQuery` audit trail object created before the query runs and recorded after.
- All 9 source queries run concurrently via `ThreadPoolExecutor(max_workers=9)`.

**Result: PASS**

---

## Pass 2 — Algorithm Correctness

**Objective:** Verify that scoring, signal computation, and derived fields produce correct results.

### Flood signal algorithm (`_compute_flood_signal`)

The flood signal is a multi-source convergence indicator with 5 levels. Verified logic:

| Signal | Condition | Verified |
|---|---|---|
| `unavailable` | EPI query failed (`data_currency == "query_failed"`) | Yes |
| `unavailable` | EPI returned "none" AND no local SES study AND no strong observational signal | Yes — prevents false "no flood" for uncovered LGAs |
| `elevated` | Multiple independent sources converge (e.g., overlay + EMS, or JRC ≥ 40%) | Yes |
| `moderate` | One strong observed signal OR two weaker signals | Yes |
| `low` | Statutory overlay only, no observed inundation | Yes |
| `none` | No indicators across any source | Yes |

### Confidence algorithm (`_compute_confidence`)

| Level | Condition | Verified |
|---|---|---|
| `high` | ≥ 3 spatial layers + ≥ 1 SAR season | Yes |
| `medium` | ≥ 1 spatial layer OR ≥ 1 SAR season | Yes |
| `low` | Nothing available | Yes |

### Key correctness checks

- JRC tile URL computation handles Southern Hemisphere correctly (lat_base uses `ceil` for NW corner).
- BOM flood history correctly identifies contiguous flood events (above major flood level) and caps at 3.
- `in_100yr_flood_zone` correctly derived from EPI, SES, flood study rasters, and Hawkesbury backward-compat.
- Flood depth computed from `level_m_ahd - ground_elevation_m_ahd` with `max(0.0, ...)` floor.
- `_normalise_outputs` handles legacy bool format (`in_epi_overlay`) and recomputes missing labels.

**Test coverage:** 70 tests covering signal computation (24 tests), confidence (7 tests), normalisation (15 tests), data sources (7 tests), S1 gap (11 tests), geography (6 tests).

**Result: PASS**

---

## Pass 3 — Null / Edge Case Hardening

**Objective:** Verify that null, missing, or unexpected inputs don't crash the pipeline.

### Null handling verified

| Field | Null behaviour | Verified |
|---|---|---|
| EPI `attributes` | `feats[0].get("attributes") or {}` — safe | Yes |
| EPI `CURRENCY_DATE` | Falls back through 4 field names, converts epoch-ms or returns "unknown" | Yes |
| EPI unrecognised `FloodClass` | Logs warning, defaults to `flood_planning_area` (safe false-positive over false-negative) | Yes |
| EMS `copernicus_flood_events` empty | Returns `None` (distinct from `False`) | Yes |
| JRC `occurrence == 255` | Returns `None` (nodata, not 0%) | Yes |
| DEA WOfS `-999.0` | Returns `None` | Yes |
| DEA WOfS non-GeoTIFF response | Content-Type + magic bytes check | Yes |
| BOM no gauge within 75km | Returns null result (not error) | Yes |
| BOM no observations in SOS2 XML | Returns `(None, None)` for peak | Yes |
| SES no flood rows in `spatial_overlays` | Returns `None` (distinct from `False`) | Yes |
| DEM `"NoData"` string | Returns `None` | Yes |
| Flood study raster directory missing | `os.path.exists` check, skips with log | Yes |
| Raster point outside bounds | Bounds check before sampling | Yes |
| `_normalise_outputs` with all-null raw | Handles gracefully, tested | Yes |

### Edge cases

- **S1B gap (Dec 2021 – Mar 2025):** `_s1b_gap_affected()` correctly uses closed-interval comparison. 11 boundary tests covering exactly-on-start, exactly-on-end, one-day-after-end.
- **JRC tile at 0°/180° longitude boundary:** Tile naming handles E/W correctly.
- **Hawkesbury raster ARI→AEP mapping:** Backward-compat field naming (`100aep` = 1% AEP) correctly mapped.

**Result: PASS**

---

## Pass 4 — Connection / Resource Safety

**Objective:** Verify all database connections and external resource handles are properly released.

### Connection patterns

| Function | Pattern | Safe |
|---|---|---|
| `_query_copernicus_ems` | `conn = None; try/finally: conn.close()` with `with conn.cursor()` | Yes |
| `_query_ses_flood_study` | `conn = None; try/finally: conn.close()` with `with conn.cursor()` | Yes |
| `_write_report` | `conn = None; try/finally: conn.close()` with `with conn.cursor()` | Yes |
| `run_flood` cache lookup | `conn = None; try/finally: conn.close()` with `with conn.cursor()` | Yes |
| `_query_jrc_surface_water` | rasterio `with` context manager inside ThreadPoolExecutor with 25s timeout | Yes |
| `_query_dea_wofs` | rasterio `with` context manager inside ThreadPoolExecutor with 25s timeout | Yes |
| `_sample_raster` | rasterio `with` context manager | Yes |
| `_query_ground_elevation` | Pure HTTP (no connection to manage) | Yes |
| `_query_epi_overlay` | Pure HTTP (no connection to manage) | Yes |
| `_fetch_bom_observations` | Pure HTTP (no connection to manage) | Yes |

### Timeout protection

- EPI REST: 20s `requests` timeout
- JRC: 12s GDAL_HTTP_TIMEOUT + 25s ThreadPoolExecutor hard timeout
- DEA WOfS: 20s `requests` timeout + 25s ThreadPoolExecutor hard timeout
- DEM: 15s `requests` timeout
- BOM: 15s `requests` timeout
- DB queries: `SET LOCAL statement_timeout = '5000'` (5s)

**No connection leaks found.**

**Result: PASS**

---

## Pass 5 — Output Defensibility / Language Audit

**Objective:** Verify all user-facing text uses factual, non-advisory language.

### Bugs found and fixed

| # | File | Line | Before | After | Severity |
|---|---|---|---|---|---|
| 1 | `FloodTool.tsx` | 18 | `'Assembling risk assessment…'` | `'Assembling flood screening…'` | Medium — "risk assessment" implies formal professional assessment |
| 2 | `FloodTool.tsx` | 98 | `'professional flood assessment recommended'` | `'professional flood study recommended'` | Low — "assessment" is less precise than "study" which is the correct NSW instrument name |

### Language verified as acceptable

- "Screening tool — not a legal flood determination" (line 603) — correctly positions as screening
- "not a formal Section 10.7 Planning Certificate" (PDF disclaimer) — correctly disclaims
- "data convergence indicator, not a flood risk determination" (code comment) — correct internal documentation
- Signal labels use factual language: "No flood indicators detected", "Low flood signal", "Moderate flood signal", "Elevated flood signal"
- "Absence of data is not clearance" (unavailable state) — appropriately cautious

### Data source attribution

- PDF `DataCurrencyTable` correctly lists all queried sources with accurate currency descriptions.
- No false attributions found (unlike other pipelines).

**Result: PASS (2 bugs fixed)**

---

## Summary

| Pass | Result | Bugs |
|---|---|---|
| 1. Data source verification | PASS | 0 |
| 2. Algorithm correctness | PASS | 0 |
| 3. Null / edge case hardening | PASS | 0 |
| 4. Connection / resource safety | PASS | 0 |
| 5. Output defensibility | PASS | 2 fixed |

**Total: 2 bugs found and fixed.**

### Notes

- This pipeline has the strongest test coverage of any satellite product (70 tests covering all major code paths).
- The `_compute_flood_signal` algorithm includes a deliberate false-negative prevention mechanism for uncovered LGAs (returns "unavailable" instead of "none" when EPI has no data and no local SES study exists).
- All connection and resource patterns follow the `conn = None; try/finally` pattern consistently.
- The `how-it-works` page lists inaccurate data sources for the Flood tool (says "NSW Flood Data Service (SES)" and "PostGIS spatial database" without listing JRC, DEA WOfS, BOM, EMS, DEM, or flood study rasters). This is a content accuracy issue for separate resolution.
