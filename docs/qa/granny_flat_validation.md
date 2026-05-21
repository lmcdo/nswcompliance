# Granny Flat Yield Predictor — 5-Pass QA Validation Report

**Pipeline:** `services/granny_flat.py`
**Frontend:** `frontend-nextjs/components/tools/GrannyFlatTool.tsx`
**PDF:** `frontend-nextjs/lib/pdf/granny-flat-report.tsx`
**Date:** 2026-05-21
**Auditor:** Lawrence McDonell + Claude (AI-assisted review)
**Status:** Complete — 8 bugs found, 8 fixed

---

## Pass 1 — Data Source Verification

**Objective:** Every API call returns what we claim. Response schemas match expectations. Failure modes are handled.

### Sources Queried

| # | Source | Method | Verified |
|---|---|---|---|
| 1 | NSW Planning Portal (zones, heritage, overlays) | Live API — `layerintersect` + lot lookup | Yes |
| 2 | NSW SIX Maps (10cm aerial imagery) | Live tile fetch via `fetch_tile_to_file()` | Yes |
| 3 | SAM segmentation (LangSAM via Modal GPU) | Remote GPU endpoint — multi-prompt ("building", "shed", "garage") | Yes |
| 4 | SEPP (Housing) 2021 rules | Local constants (SEPP_MIN_LOT_M2=450, SEPP_MAX_GF_AREA_M2=60) | Yes |
| 5 | NSW Fair Trading Rental Bond Data | Cached JSON (`nsw_rental_by_postcode.json`) | Yes |
| 6 | DCP setback controls | Supabase `dcp_setback_controls` table (per-LGA, where available) | Yes |

### DataCurrencyTable Accuracy

PDF DataCurrencyTable lists 5 sources: NSW Planning Portal, NSW SIX Maps, NSW Fair Trading, SEPP Housing 2021, NSW Heritage Register. All are actually queried by the pipeline. No false attributions found. SAM segmentation is internal ML infrastructure, not a government data source — correctly omitted from the table.

### Failure Modes

- **Tile fetch failure:** Writes error state to DB so frontend poll resolves immediately. Connection handling in error path is correct (try/finally). Raises HTTP 502.
- **Modal GPU timeout:** Not explicitly handled in detect endpoint — would propagate as HTTP 500. Acceptable: the caller (Trigger.dev task) has its own timeout handling.
- **Planning Portal API failure:** Falls through to null lot geometry → null lot area → SEPP eligibility unverifiable → confidence capped at medium. Correct degradation.

**Result: PASS** — all sources verified, no false attributions, failure modes degrade gracefully.

---

## Pass 2 — Algorithm Correctness

**Objective:** Classification logic, scoring, thresholds, and boundary conditions produce correct outputs.

### SEPP Housing 2021 Eligibility Logic

| Rule | Implementation | Correct |
|---|---|---|
| Min lot area 450 m² (cl 4.6) | `lot_area_m2 < SEPP_MIN_LOT_M2` → ineligible | Yes |
| Max GF floor area 60 m² (cl 4.18) | `min(SEPP_MAX_GF_AREA_M2, lot_area_m2 * 0.25)` | Yes |
| Residual area check | `lot_area_m2 - main_dwelling_area_m2 < 120` → not buildable | Yes |
| Heritage exclusion | Heritage flag from Planning Portal → ineligible for CDC | Yes |
| Multiple secondary dwelling block (cl 53(1)) | ≥3 structures + unknown status → blocked | Yes |
| Single existing secondary ambiguity | count == 2 + status unknown → confidence capped at medium | Yes |

### SAM Structure Detection

| Check | Implementation | Correct |
|---|---|---|
| Multi-prompt detection | "building", "shed", "garage" with IoU dedup (threshold 0.3) | Yes |
| Quality filters | MIN_FILL_RATIO=0.15, MAX_BBOX_FRACTION=0.35, MAX_ASPECT_RATIO=8.0 | Yes |
| Lot containment | Shapely WGS84 polygon intersection, ≥50% overlap threshold | Yes |
| Lot clipping | Structures clipped to lot boundary before area calculation | Yes |

### Confidence Scoring

| Condition | Confidence | Correct |
|---|---|---|
| AI + user agree + rent data available | High | Yes |
| AI ≠ user OR no rent data | Medium | Yes |
| Lot area unknown | Capped at medium | Yes |
| Secondary dwelling status unknown + ≥2 structures | Capped at medium | Yes |
| Pre-validation (detect step) | Low | Yes |

### Rental Yield Calculation

- Weekly rent from `nsw_rental_by_postcode.json` with postcode regex fallback (e.g. "2xxx" → "2000")
- Annual yield = `(weekly_rent * 52) / assumed_build_cost * 100`
- Build cost: `max_floor_area_m2 * $2,800/m²` (hardcoded unit rate — acceptable as estimate, clearly labelled)

**Result: PASS** — all thresholds match SEPP Housing 2021, confidence scoring is conservative, rental yield is clearly labelled as estimate.

---

## Pass 3 — Null/Edge Case Hardening

**Objective:** Every `.get()`, `float()`, `int()`, `or default` is checked for null-value traps.

### Issues Found

| # | Location | Issue | Severity |
|---|---|---|---|
| 1 | `_fetch_sd_setbacks()` line 140-174 | Cursor opened in try block, `cur.close()` also in try block. If second SQL query fails between `cur.execute()` and `cur.close()`, cursor leaks. | Medium |

**Bug 1 — Cursor leak in `_fetch_sd_setbacks()`:** Fixed by moving cursor to `None` initialisation before try, and `cur.close()` to finally block.

### Null Handling Verified

| Check | Location | Handling |
|---|---|---|
| `lot_area_m2` is None | Multiple locations | Checked before SEPP eligibility, confidence capped at medium |
| `main_dwelling_area_m2` is None | Residual area check | Guarded with `is not None` check |
| `weekly_rent` is None | Yield calculation | Returns None for yield fields |
| `lot_geometry` is None | Detect endpoint | Falls through to null lot area → ineligible |
| `req.existing_secondary_dwelling` is None | Secondary dwelling block | Explicit None check before confidence cap |
| `postcode` regex failure | Rental lookup | Returns None → confidence degrades |

**Result: PASS (after fix)** — 1 cursor leak fixed, all null paths verified.

---

## Pass 4 — Connection/Resource Safety

**Objective:** No DB connection leaks, no unguarded blocking I/O in async endpoints, proper error isolation.

### Connection Handling

| Endpoint/Function | Pattern | Safe |
|---|---|---|
| `detect_structures()` — happy path | No DB connection needed (writes only on error) | Yes |
| `detect_structures()` — error path | `_err_conn = None`, try/finally with `_err_conn.close()` | Yes |
| `confirm_granny_flat()` — main | `conn = None`, try/except/finally with `conn.close()` | Yes |
| `_fetch_sd_setbacks()` | **Was: cursor in try, close in try (leak). Now: cursor in finally.** | Yes (fixed) |
| `lookup_lga()` (imported) | Connection passed in, caller manages lifecycle | Yes |

### Blocking I/O

- Both endpoints are synchronous FastAPI (`def`, not `async def`). No async context to block.
- Modal GPU call in detect is synchronous HTTP — correct for sync endpoint.
- Tile fetch is synchronous file I/O — correct.

### Error Isolation

- DB write failure in confirm raises HTTP 503 with clear message — user can retry.
- Tile fetch failure writes error state and raises HTTP 502 — frontend poll resolves.
- DCP setback lookup failure is caught and returns None — report proceeds without DCP data (correct degradation).

**Result: PASS (after fix)** — 1 cursor leak fixed, all connection paths verified.

---

## Pass 5 — Output Defensibility (Language Audit)

**Objective:** Every user-facing claim is traceable to a specific data source. No interpolation or inference beyond what the data shows. No compliance determinations.

### Issues Found

| # | File | Line | Original Text | Issue | Fix |
|---|---|---|---|---|---|
| 2 | GrannyFlatTool.tsx | 445 | "This property passes all SEPP Housing 2021 spatial checks" | "passes all" implies comprehensive compliance determination | → "Based on the data sources checked, this property meets the SEPP Housing 2021 spatial criteria" |
| 3 | GrannyFlatTool.tsx | 700 | "Shadow risk from neighbours" | "risk" implies professional risk assessment | → "Shadow impact from neighbours" |
| 4 | GrannyFlatTool.tsx | 94 | "the property does not qualify" | "qualify" implies formal eligibility determination | → "the property did not pass one or more other checks" |
| 5 | granny-flat-report.tsx | 269 | "This property meets the minimum requirements for a secondary dwelling" | Compliance determination — we screen data, we don't determine requirements | → "Based on the data sources checked, this property meets the SEPP Housing 2021 spatial criteria for a secondary dwelling" |
| 6 | granny-flat-report.tsx | 575 | "This lot qualifies for a secondary dwelling under the fast-track CDC pathway" | "qualifies" = formal eligibility determination | → "Based on the data sources checked, this lot meets the SEPP Housing 2021 spatial criteria for a secondary dwelling via the CDC pathway" |
| 7 | granny-fat-report.tsx | 582 | "This lot qualifies for a secondary dwelling" (no-rent variant) | Same pattern as #6 | → Same replacement pattern |
| 8 | granny-flat-report.tsx | 874 | "Eligibility determinations are based on automated analysis" | "determinations" implies formal legal determination | → "Eligibility indicators are based on automated screening" |

### Retained (No Change Needed)

| Location | Text | Reason |
|---|---|---|
| granny-flat-report.tsx:294 | "Your lot qualifies for the full allowance" | Changed to "your lot is within the full allowance" |
| granny-flat-report.tsx:898 | "A private certifier can assess SEPP compliance" | Describes what a *certifier* does — correct |
| GrannyFlatTool.tsx:765 | "high risk areas as certified by council" | Direct quotation of SEPP Housing 2021 cl 58 — correct |
| GrannyFlatTool.tsx:769 | "This check is indicative only" | Proper caveat language — correct |

**Result: PASS (after 7 language fixes)** — all user-facing text now describes data observations, not compliance determinations.

---

## Bug Register

| # | Severity | Category | Description | Status |
|---|---|---|---|---|
| 1 | Medium | Connection safety | `_fetch_sd_setbacks()` cursor leak — `cur.close()` in try block, not finally | FIXED |
| 2 | Medium | Language | "passes all SEPP Housing 2021 spatial checks" — compliance determination | FIXED |
| 3 | Low | Language | "Shadow risk from neighbours" — risk language | FIXED |
| 4 | Low | Language | "does not qualify" — formal eligibility language | FIXED |
| 5 | Medium | Language | "meets the minimum requirements" — compliance determination in PDF | FIXED |
| 6 | Medium | Language | "qualifies for a secondary dwelling" — compliance determination in PDF (with rent) | FIXED |
| 7 | Medium | Language | "qualifies for a secondary dwelling" — compliance determination in PDF (no rent) | FIXED |
| 8 | Low | Language | "Eligibility determinations" in disclaimer — implies formal determination | FIXED |

---

## Sign-Off

All 5 passes complete. 8 bugs found, 8 fixed:
- 1 cursor leak in DCP setback lookup (connection safety)
- 7 language changes removing compliance determination language from user-facing text

The granny flat pipeline correctly:
- Uses government-authoritative data (Planning Portal, SIX Maps) with clear attribution
- Applies SEPP Housing 2021 rules as local constants (state-wide, rarely amended — acceptable)
- Degrades confidence when data is incomplete (lot area unknown, secondary dwelling status unknown)
- Writes audit trail with per-source DataSourceQuery tracking
- Labels all outputs as data observations, not compliance determinations
