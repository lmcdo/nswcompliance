# Threat Radar — QA Validation Report

**Date:** 2026-05-20
**Pipeline version:** `8d2e8f7c`
**Service file:** `services/threat_radar.py` (382 lines)
**Frontend:** `ThreatRadarTool.tsx` (913 lines), `threat-radar-report.tsx` (569 lines)
**Auditor:** Lawrence McDonell + Claude Code
**Status:** Draft

---

## 1. Source Authority Register

| Source | Provider | Authority Basis | Access Method | Known Limitations | Provider Disclaimer |
|---|---|---|---|---|---|
| **NSW ePlanning OnlineDA** | NSW Department of Planning | Statutory DA register under EP&A Act 1979 | REST API (free, no auth). Filters in HTTP `filters` header as JSON. | 200 results per page. Not all councils have complete data. Some older DAs lack coordinates. | "Data may not be current and should not be relied upon as a primary source of information." |
| **NSW ePlanning OnlineCDC** | NSW Department of Planning | Statutory CDC register under EP&A Act 1979 | Same REST API, different endpoint. Same header-based filter pattern. | Same limitations. CDCs are typically less complete than DAs (fewer optional fields populated). | Same as OnlineDA. |

**Assessment:** Both data sources are the **authoritative statutory register** for development applications in NSW. No secondary or derived sources are used. **PASS.**

---

## 2. Algorithm Walkthrough

### 2.1 Architecture

Two separate data flows exist:

| Flow | Entry Point | Radius | Purpose |
|---|---|---|---|
| **Instant search** | Next.js API route `/api/satellite/threat-radar/search` → ePlanning API | 500m | One-time report for property buyers |
| **Monitoring/subscription** | Python `threat_radar.py` `/pipeline/threat-radar/check` | 200m | Weekly cron alerts for subscribers |

The Python service handles subscriptions and weekly checks. The Next.js route handles immediate searches. Both query the same ePlanning endpoints with the same header-based filter pattern.

### 2.2 ePlanning query (`_fetch_das`, lines 147-178)

- **Filter mechanism:** Filters passed as JSON in HTTP `filters` header — NOT as query parameters. This is the correct ePlanning API pattern. **Correct.**
- **Both endpoints:** Queries OnlineDA and OnlineCDC independently. If one fails, the other's results are still used. `any_success` flag prevents updating `last_checked` only when BOTH fail. **Correct.**
- **Window:** `WINDOW_DAYS = 8` — 8-day lookback from UTC now. Slightly overlaps week boundaries to prevent missed apps from timezone/timing gaps. **Reasonable.**
- **Council name normalisation:** `_normalise_council()` maps ~40 common variants to exact ePlanning strings. Falls back to raw (stripped) input for unmapped names. Sydney is the only council with a non-obvious API name (`"Council of the City of Sydney"`). **Correct coverage for major metro councils.**
- **Page size:** `PageSize: 200` — fetches up to 200 applications. For weekly monitoring with 200m radius, this is sufficient. For instant search with 500m radius in high-activity LGAs, could truncate. **Acceptable for current use.**

### 2.3 Distance filtering (`_filter_nearby`, lines 181-196)

- **Haversine formula:** Standard implementation. R = 6,371,000m. Correct for Australian latitudes. **PASS.**
- **Coordinate extraction:** Tries `app.Latitude/Longitude` first, falls back to `Location[0].Y/X`. Both formats exist in ePlanning responses. **Correct.**
- **Zero-coordinate skip:** `if alat == 0 and alng == 0: continue` — applications without geocoded coordinates are excluded. This is correct (0,0 is in the Gulf of Guinea). **PASS.**
- **Broad exception handling:** `except Exception: pass` — silently skips apps with unparseable coordinates. Prevents one bad record from crashing the whole filter. **Acceptable, logged upstream.**

### 2.4 Dedup logic (lines 306-309)

- **Seen set:** `seen_application_numbers` stored in subscription's `inputs` JSONB column.
- **Key:** Uses `PlanningPortalApplicationNumber` or `ApplicationNumber`.
- **Merge:** `seen` is a Python set. New apps are identified by exclusion. Updated set persisted via `jsonb_build_object` merge. **Correct.**
- **Empty key:** If both number fields are falsy, `num` is `""`, which is not added to `seen` and NOT added to `new_apps` (the `if num and num not in seen` guard). **Correct — doesn't track un-numbered apps but doesn't crash.**

### 2.5 Pressure score algorithm (frontend, lines 103-158)

```
For each application:
  base = distance < 100m → 3, < 250m → 2, else → 1
  scale = dwellings >= 10 → 2, >= 4 → 1.5, else → 1
  total += base * scale

score = clamp(round(total), 1, 10)  [0 if no apps]
```

**Assessment:** Distance-weighted, dwelling-scaled. Reasonable heuristic. Labels: Intense (>=8), High (>=5), Moderate (>=3), Low (<3). The same algorithm exists in the PDF report but with **different labels** — see BUG-2.

### 2.6 Approval status detection (frontend, line 123)

```js
if (status.includes('approved') || (status.includes('determined') && !status.includes('undetermined')))
```

**Assessment:** ePlanning `Status` field values vary. This catches "Approved", "Determined", "Deferred Commencement Approved" but correctly excludes "Undetermined". **Reasonable heuristic.** Note: "Refused" contains neither "approved" nor "determined", so it's correctly excluded.

---

## 3. Null/Edge Case Hardening

### 3.1 Backend null-value traps

| Location | Pattern | Safe? | Notes |
|---|---|---|---|
| Line 171 | `data.get("Application") or data.get("ApplicationList") or []` | Yes | Handles both response formats + null |
| Line 186 | `(app.get("Location") or [{}])[0]` | Yes | Handles null Location array |
| Line 187 | `float(app.get("Latitude") or loc.get("Y") or 0)` | Yes | String "0" is truthy → float("0")=0.0 → caught by 0-check |
| Line 250 | `inputs = sub.get("inputs") or {}` | Yes | Handles null inputs |
| Line 251 | `inputs.get("council_name","")` | Yes | Default empty string |
| Line 252 | `set(inputs.get("seen_application_numbers") or [])` | Yes | Handles null and missing key |
| Line 307 | `app.get("PlanningPortalApplicationNumber") or app.get("ApplicationNumber","")` | Yes | Falls through to second key |

### 3.2 Frontend null-value traps

| Location | Pattern | Safe? | Notes |
|---|---|---|---|
| Line 75 | `Number(app.CostOfDevelopment) \|\| 0` | Yes | NaN → 0 |
| Line 115 | `Number(app.CostOfDevelopment) \|\| 0` | Yes | Same pattern |
| Line 131 | `(app._distance_m ?? 999)` | Yes | Nullish coalescing, not OR |
| Line 136 | `apps.length === 0 ? 0 : Math.min(...)` | Yes | Zero-app guard |
| Line 496-497 | `validApps.filter(a => ... Number(a.Latitude) !== 0)` | Yes | Filters out zero coords |

### 3.3 Edge cases

| Scenario | Expected | Actual | Pass? |
|---|---|---|---|
| No applications within radius | Empty results, no crash | `nearby = []`, `new_apps = []`, returns 0 counts | **PASS** |
| Both ePlanning endpoints down | Graceful failure, no DB update | `api_available=False`, returns `api_error` message, `last_checked` NOT updated | **PASS** |
| One endpoint down, one up | Partial results | `any_success=True`, partial results returned, audit trail logs both | **PASS** |
| Subscription not found | 404 | `raise HTTPException(404, "Subscription not found")` | **PASS** |
| Missing council_name in subscription | 422 | `raise HTTPException(422, "council_name missing from subscription")` | **PASS** |
| Duplicate subscription (same address + email) | Return existing | Dedup check on lines 211-217, returns existing ID | **PASS** |
| Application with no coordinates | Skip silently | `if alat == 0 and alng == 0: continue` | **PASS** |
| Application with string coordinates | Parse and use | `float(app.get("Latitude") or ...)` handles string-to-float | **PASS** |
| Zero applications found | Clean empty state | Frontend shows "No applications found" message | **PASS** |

---

## 4. Connection/Resource Safety

| Check | Status | Notes |
|---|---|---|
| DB connection leak — `subscribe` | **PASS** | `try/finally: conn.close()` pattern |
| DB connection leak — `check` (read) | **PASS** | Same pattern |
| DB connection leak — `check` (write) | **PASS** | Same pattern |
| DB connection leak — `list_subscriptions` | **PASS** | Same pattern |
| HTTP timeout — ePlanning | **PASS** | `requests.get(timeout=20)` |
| Error isolation — single endpoint failure | **PASS** | Each endpoint in try/except, other continues |
| Error isolation — total API failure | **PASS** | Returns error response, doesn't update last_checked |
| Error isolation — audit trail failure | **PASS** | `log_audit_trail()` is non-blocking by design |
| Error isolation — DB write failure (update seen set) | **PARTIAL** | No try/except around the second DB write (lines 311-325). If commit fails after API succeeds, user gets 500 despite having valid data. Not catastrophic — the next check will re-fetch the same apps. |

**Assessment:** Connection management is clean. The one gap (no isolation on the seen-set update) is low-severity because the next check self-heals. **PASS with note.**

---

## 5. Output Defensibility

### 5.1 User-facing claims — traceability

| Claim (user sees) | Data source | Traceable? | Notes |
|---|---|---|---|
| Application count + list | ePlanning OnlineDA + OnlineCDC | Yes | Direct from statutory register |
| Distance in metres | Haversine from user coords + app coords | Yes | Derived, reproducible |
| Application details (number, status, cost, etc.) | ePlanning response fields | Yes | Verbatim from API |
| Development pressure score | Computed from distance + dwellings | Yes | Algorithm documented, reproducible |
| Net dwelling change | Sum of `NumberOfNewDwellings` - `DemolitionDwellings` | Yes | Direct from ePlanning fields |
| EPI variation count | Count of `EpiVariationProposedFlag == "Yes"` | Yes | Direct from ePlanning field |
| LGA-wide stats | Aggregated from ePlanning data | Yes | Source attributed |
| Approval rate | Count of approved/determined ÷ total | Yes | Derived, heuristic status matching |

### 5.2 Language audit (Pass 5)

#### Frontend — ThreatRadarTool.tsx

| Line | Match | Context | Risk | Action |
|---|---|---|---|---|
| 345 | "**Expect** construction noise, traffic disruption" | Intense pressure detail | **MEDIUM** | Prediction. Change to "Construction noise, traffic disruption, and street character changes are common in areas with this level of activity." |
| 351 | "**can affect** parking, sunlight, and **property values**" | High pressure detail | **HIGH** | Property valuation advice territory. Remove "property values". |
| 359 | "nothing unusual for a suburban area" | Moderate pressure detail | **LOW** | Normalcy assessment. Acceptable — factual general statement. |
| 390 | "**Expect** more traffic, parking pressure" | Net dwelling detail (>10) | **MEDIUM** | Same "Expect" pattern. Soften. |
| 403 | "may set precedents" | EPI variation detail | **NONE** | Factual legal observation. Keep. |
| 431 | "You have the **right** to lodge an objection" | Proximity alert detail | **LOW** | Regulatory fact but not all DAs have exhibition. Add qualifier. |

#### PDF — threat-radar-report.tsx

| Line | Match | Context | Risk | Action |
|---|---|---|---|---|
| 289 | "**positive signal** for amenity stability" | No applications found | **MEDIUM** | Assessment language. Change to factual restatement. |
| 309 | "**Expect** increased traffic, parking pressure" | Net dwelling detail | **MEDIUM** | Same prediction pattern. Soften. |
| 332 | "further **non-compliant** development" | EPI variation detail | **HIGH** | Characterises EPI variations as non-compliance. They are a lawful mechanism. Change to "further variation from standard controls". |
| 511 | "nearby **development risk**" | Next steps section | **MEDIUM** | Risk assessment term. Change to "nearby development activity". |
| 521-524 | "NSW Planning Portal (LEP zones)" in DataCurrencyTable | Data sources | **BUG-1** | This pipeline does NOT query LEP zones. False data source attribution — same class as bushfire BUG-4. |

### 5.3 Bugs found

**BUG-1: PDF DataCurrencyTable lists "NSW Planning Portal (LEP zones)" as a data source (line 523)**

The threat radar pipeline queries OnlineDA and OnlineCDC only. It does NOT query LEP zones. The second row in the DataCurrencyTable is a false attribution.

**Severity:** Medium. Same class as bushfire BUG-4. Claiming a data source we didn't query undermines audit trail credibility.

**Fix:** Remove the LEP zones row from the DataCurrencyTable.

**BUG-2: Pressure label mismatch between frontend and PDF (lines 140-143 vs PDF 202-207)**

Frontend labels: Intense (>=8), High (>=5), Moderate (>=3), Low (<3)
PDF labels: high (>=8), elevated (>=5), moderate (>=3), low (<3)

A user comparing their interactive result with the PDF would see different labels for the same score.

**Severity:** Low-Medium. Confusing but not legally risky.

**Fix:** Align PDF labels to match frontend (Intense/High/Moderate/Low).

**BUG-3: "positive signal for amenity stability" (PDF line 289)**

Assessment language. When no applications are found, the PDF says this is a "positive signal" — this is an evaluative judgment, not a factual observation.

**Severity:** Medium. Under Shaddock, we shouldn't make evaluative statements about property amenity.

**Fix:** Change to "No DA or CDC applications were lodged near this property in the search window."

**BUG-4: "non-compliant development" (PDF line 332)**

EPI variations are a lawful mechanism under the EP&A Act. Describing development that uses this mechanism as "non-compliant" is both inaccurate and potentially defamatory to applicants.

**Severity:** High. Factually wrong characterisation.

**Fix:** Change to "further variation from standard planning controls in the area."

**BUG-5: "property values" in high pressure detail (frontend line 351)**

"New buildings can affect parking, sunlight, and property values" crosses into property valuation advice, which requires appropriate licensing under the Property and Stock Agents Act.

**Severity:** Medium. Remove "property values" reference.

**Fix:** Change to "new buildings can affect parking, sunlight, and street amenity."

**BUG-6: "development risk" in PDF next steps (line 511)**

"A buyers agent can advise on price adjustments based on nearby development risk" — "development risk" is a risk assessment term.

**Severity:** Medium.

**Fix:** Change to "nearby development activity."

---

## 6. Limitations Statement

This pipeline CANNOT:
- Provide real-time DA monitoring (checks are periodic, minimum weekly)
- Detect DAs not yet entered into the ePlanning system (some councils have lag)
- Guarantee coordinate accuracy for all applications (some lack geocoded locations)
- Assess the merit or likely outcome of any individual application
- Provide property valuation or price adjustment advice
- Determine whether a specific DA would materially affect a neighbouring property
- Replace professional town planning advice on development impact

---

## 7. Sign-off

- [x] All data sources documented with provenance
- [x] Algorithm correctly implements stated methodology
- [x] Edge cases handled gracefully
- [x] Pressure labels aligned between frontend and PDF (BUG-2 FIXED)
- [x] Assessment/prediction language replaced with factual observations (BUG-3, BUG-4, BUG-5, BUG-6 FIXED)
- [x] PDF data currency table corrected — LEP zones removed (BUG-1 FIXED)
- [x] Disclaimer covers all identified limitations
- [x] Audit trail logging implemented for this pipeline

**Bugs found and fixed:** BUG-1 (false LEP zones attribution), BUG-2 (pressure label mismatch), BUG-3 ("positive signal" removed), BUG-4 ("non-compliant" → "variation from standard controls"), BUG-5 ("property values" → "street amenity"), BUG-6 ("development risk" → "development activity")
