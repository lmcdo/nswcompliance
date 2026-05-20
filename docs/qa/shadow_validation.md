# Shadow Detector — QA Validation Report

**Date:** 2026-05-21
**Pipeline version:** `8238a3ca`
**Service file:** `services/shadow_detector.py` (505 lines)
**Frontend:** `ShadowTool.tsx` (699 lines), `shadow-report.tsx` (662 lines)
**Auditor:** Lawrence McDonell + Claude Code
**Status:** Draft

---

## 1. Source Authority Register

| Source | Provider | Authority Basis | Access Method | Known Limitations | Provider Disclaimer |
|---|---|---|---|---|---|
| **NSW Planning Portal lot API** | NSW DPE | Cadastral boundary under Real Property Act | REST API (free, no auth). `propId` lookup. Returns ArcGIS JSON (EPSG:3857). | Single lot at a time. Strata lots may return parent lot boundary. | N/A |
| **spatial_overlays (height)** | Derived from LEP HOB maps (NSW Planning Portal) | Secondary — LEP instrument is authoritative | PostGIS `ST_Contains` point-in-polygon query | Coverage: ~33 LGAs with height polygons. Value format varies ("9", "9m", "9.0"). | N/A (our derived dataset) |
| **regulatory_provisions (height)** | Extracted from DCP text (Inner West only) | Tertiary — text extraction from provisions | SQL text search with regex | Inner West only. Text extraction may miss non-standard formatting. | N/A (our derived dataset) |
| **Element84 Sentinel-2 L2A** | ESA (via Element84 Earth Search) | Open access satellite imagery (CC-BY-SA 3.0 IGO) | STAC API, free, no auth | 10m resolution. Cloud cover affects availability. BSI change detection is heuristic. | Copernicus Sentinel data |
| **pybdshadow + pvlib** | Computational model | N/A — analytical, not data | Local Python libraries | Geometric model only. Does not account for existing buildings, trees, terrain, or infrastructure. | N/A |

**Assessment:** Primary data (lot boundary) is from the authoritative cadastral source. Height controls are derived from LEP maps with clear fallback chain. Shadow model is computational with documented methodology. **PASS.**

---

## 2. Algorithm Walkthrough

### 2.1 Request flow

```
POST /pipeline/shadow { address, prop_id, lat, lng, report_id, height_m? }
  → Fetch lot geometry from NSW Planning Portal lot API
  → Convert ArcGIS JSON (EPSG:3857) → GeoJSON (WGS84)
  → Get height limit:
      1. spatial_overlays point-in-polygon (33 LGAs)
      2. regulatory_provisions text extraction (Inner West fallback)
      3. Default 9.0m
  → Compute Sentinel-2 change score (ThreadPoolExecutor, 25s timeout)
  → Generate northern_neighbour_proxy (hypothetical building at north boundary)
  → model_all_scenarios(proxy, height_m) for 5 ADG dates
  → Build scenario list with overlap fractions
  → _adg_compliant() — Jun 21 noon gate
  → _write_report() to property_reports
  → log_audit_trail() (non-blocking)
  → return response
```

### 2.2 ArcGIS → GeoJSON conversion (`_arcgis_to_geojson`, lines 102-116)

Standard inverse Mercator projection. R = 20037508.342789244 (half circumference in metres). Converts EPSG:3857 Web Mercator rings to WGS84 coordinates. **Correct.**

### 2.3 Height limit lookup (`_get_height_limit`, lines 165-249)

Three-tier fallback:
1. `spatial_overlays WHERE layer_type='height'` — point-in-polygon, regex extraction of numeric value, 4-30m bounds check. **Correct.**
2. `regulatory_provisions WHERE v2_topic ILIKE '%height%'` — finds nearest `dcp_precinct_boundaries` centroid, then searches provision text. Takes max height in 4-30m range. **Conservative (uses max).**
3. Default 9.0m — typical R2 Low Density height limit. **Reasonable default.**

**Assessment:** Fallback chain is correctly ordered from most to least authoritative. Height extraction regex handles "9", "9m", "9.0" formats. Bounds check (4-30m) prevents unreasonable values. **PASS.**

### 2.4 ADG compliance (`_adg_compliant`, lines 289-307)

**Primary gate: Jun 21 noon only.**

Well-documented rationale: 9am and 3pm produce ~35m shadows regardless of lot size due to low solar altitude. Using them as hard gates produces false "always concern" for all suburban lots. Noon is the definitive test — if noon shadow covers >=40% of the lot, no 2-hour window exists.

**BUG-1:** The response contract comment (line 31) says `"adg_compliant": bool, # True if ≥2 of 3 Jun 21 scenarios do NOT overlap subject lot` — but the actual implementation only checks noon overlap. The comment is wrong. The code is correct.

**Assessment:** The noon-only gate is the right design decision. The 9am/3pm scenarios are retained in output for context. **PASS (code). FIX needed (comment).**

### 2.5 Worst case selection (`_worst_case`, lines 310-314)

`max(scenarios, key=lambda s: s.get("shadow_length_m") or 0.0)["scenario"]` — selects scenario with longest shadow throw. **Correct.** Default fallback to "jun21_9am" when no scenarios exist. **Safe.**

### 2.6 Confidence scoring (line 448)

```python
confidence = "medium" if height_m != DEFAULT_HEIGHT_M and lep_name != "Local Environmental Plan" else "low"
```

Never returns "high" — maximum is "medium" when a real height control is found. This is conservative. **PASS.**

---

## 3. Null/Edge Case Hardening

### 3.1 Null-value traps

| Location | Pattern | Safe? | Notes |
|---|---|---|---|
| Line 109 | `geometry.get("rings") or []` | Yes | Handles null rings |
| Line 124 | `data[0].get("geometry") if data else None` | Partial | Safe if API returns list. Would fail on dict response. API consistently returns list. |
| Line 136 | `if not lga_name` | Yes | Handles empty/null LGA name |
| Line 197-198 | `if row and row[0]` | Yes | Double null check |
| Line 223 | `(row[0] or "").strip() if row else ""` | Yes | Handles null row and null value |
| Line 263 | `shadow_map.get(key) or {}` | Yes | Handles missing scenario |
| Line 264 | `"error" in shadow_geojson` | Yes | Checks for error key |
| Line 353 | `if request.height_m` | Partial | height_m=0 would be falsy. 0m makes no sense — safe in practice. |
| Line 389 | `change.get("change_score") is not None` | Yes | Explicit None check |
| Line 444 | `bool(change.get("construction_detected", False))` | Yes | Default False |

### 3.2 Edge cases

| Scenario | Expected | Actual | Pass? |
|---|---|---|---|
| Lot geometry not found | 422 error | `raise HTTPException(422, ...)` | **PASS** |
| Height limit not in DB | Use 9.0m default | Falls through to `DEFAULT_HEIGHT_M`, confidence="low" | **PASS** |
| Sentinel-2 timeout | Graceful degradation | Caught, returns null score, change_detected=False | **PASS** |
| Shadow model failure | 500 error | `raise HTTPException(500, str(e))` | **PASS** |
| Non-residential zone | Indicated on UI | `NON_RESIDENTIAL_ZONE_PREFIXES` check in frontend, ADG marked "indicative only" | **PASS** |
| No scenarios computed | Safe default | `_worst_case` returns "jun21_9am", `_adg_compliant` returns True (can't assess) | **PASS** |
| height_m provided in request | Skip DB lookup | Uses provided height, still looks up LEP label | **PASS** |

---

## 4. Connection/Resource Safety

| Check | Status | Notes |
|---|---|---|
| _get_height_limit | **PASS** | try/finally conn.close() |
| _get_lep_label | **PASS** | try/finally conn.close() |
| _write_report | **PASS** | try/finally conn.close() |
| height_m override LEP lookup (lines 358-375) | **PASS** | try/finally _lep_conn.close() |
| LGA lookup (lines 427-432) | **BUG-2** | `_lga_conn.close()` inside try, NOT in finally. If `lookup_lga()` raises, connection leaks. |
| ThreadPoolExecutor | **PASS** | `with` context manager ensures shutdown |
| Thread timeout | **PASS** | `.result(timeout=25)` |
| HTTP timeout | **PASS** | `requests.get(timeout=15)` |
| Error isolation — Sentinel-2 | **PASS** | TimeoutError and Exception both caught |
| Error isolation — DB write | **PASS** | Raises 503 with user-friendly message |
| Error isolation — audit trail | **PASS** | Non-blocking |

---

## 5. Output Defensibility

### 5.1 User-facing claims — traceability

| Claim (user sees) | Data source | Traceable? | Notes |
|---|---|---|---|
| "Meets/does not meet ADG solar access test" | Computed from shadow overlap on Jun 21 noon | Yes | Labelled as model output, not formal assessment |
| Shadow length in metres | pybdshadow geometric model | Yes | Derived, reproducible from height + solar position |
| Shadow overlap fraction | Intersection of shadow polygon with lot polygon | Yes | Derived, geometric |
| Building height limit | spatial_overlays or regulatory_provisions | Yes | Source attributed (LEP name shown) |
| Lot boundary | NSW Planning Portal lot API | Yes | Direct from authoritative cadastre |
| Construction activity | Sentinel-2 BSI change score | Yes | Source attributed, score shown |

### 5.2 Language audit (Pass 5)

#### Response contract comment

| Line | Match | Context | Risk | Action |
|---|---|---|---|---|
| 31 | `"adg_compliant": bool, # True if ≥2 of 3 Jun 21 scenarios do NOT overlap` | Code comment | **MEDIUM** | Comment describes different logic than implementation (noon-only gate). Fix comment. |

#### Frontend — ShadowTool.tsx

| Line | Match | Context | Risk | Action |
|---|---|---|---|---|
| 16 | "Checking ADG solar access **compliance**" | Operational transparency step | **MEDIUM** | "compliance" implies formal compliance check. Change to "Checking ADG solar access test". |
| 511 | "your property **would still receive** at least 2 hours" | ADG compliant finding detail | **MEDIUM** | Assurance/guarantee language. Change to "the model indicates your property would receive". |

#### PDF — shadow-report.tsx

| Line | Match | Context | Risk | Action |
|---|---|---|---|---|
| 257 | "**would not significantly shadow** this property" | ADG compliant, no overlap | **MEDIUM** | Assurance. Change to "the model shows no significant shadow impact on". |
| 258 | "ADG solar access requirements **are met**" | ADG compliant finding | **MEDIUM** | Compliance determination. Add qualifier: "based on this model". |
| 307 | "This is a **strong result** for solar access" | No overlap detected | **MEDIUM** | Evaluative judgment. Change to factual: "No shadow overlap was detected in any test scenario." |
| 557-560 | "NSW Building Footprints" + "NSW DEM" in DataCurrencyTable | Data sources | **BUG-9** | Pipeline does NOT use Building Footprints or DEM. Two false data source attributions. |
| 567 | "**pysolar**" in methodology | Methodology section | **BUG-10** | Pipeline uses pvlib, not pysolar. Wrong library name. |

### 5.3 Bugs found

**BUG-1: Response contract comment wrong about ADG logic (line 31)**

Comment says "True if ≥2 of 3 Jun 21 scenarios do NOT overlap subject lot" but actual implementation checks noon-only gate. Comment is misleading to developers.

**Severity:** Low. Internal comment, not user-facing. But could cause confusion if another developer reads it.

**Fix:** Update comment to describe actual logic.

**BUG-2: LGA connection not in finally block (lines 427-432)**

```python
try:
    _lga_conn = _get_conn()
    lga_info = lookup_lga(request.lat, request.lng, _lga_conn)
    _lga_conn.close()
except Exception:
    pass
```

If `lookup_lga()` raises, `_lga_conn.close()` is skipped. Connection leak.

**Severity:** Medium. Each leaked connection ties up a Supabase connection slot until the process exits.

**Fix:** Move close to finally block.

**BUG-3: "compliance" in transparency step label (ShadowTool.tsx line 16)**

"Checking ADG solar access compliance" — implies a formal compliance determination. The tool performs an indicative model check, not a compliance assessment.

**Severity:** Medium. User-facing during analysis.

**Fix:** Change to "Checking ADG solar access test".

**BUG-4: "would still receive" — assurance language (ShadowTool.tsx line 511)**

"your property would still receive at least 2 hours of direct sunlight" — guarantee language.

**Severity:** Medium. Under Shaddock, we shouldn't guarantee outcomes based on a geometric model.

**Fix:** Change to "the model indicates your property would receive".

**BUG-5: "would not significantly shadow" — assurance (PDF line 257)**

**Severity:** Medium. Same class.

**Fix:** Change to "the model shows no significant shadow impact on".

**BUG-6: "requirements are met" — compliance determination (PDF line 258)**

**Severity:** Medium. "are met" is a definitive compliance statement.

**Fix:** Add qualifier: "are met based on this model".

**BUG-7: "strong result" — evaluative judgment (PDF line 307)**

**Severity:** Low-Medium.

**Fix:** Change to "No shadow overlap was detected in any test scenario."

**BUG-8: Two false data sources in PDF DataCurrencyTable (lines 557-560)**

Pipeline does NOT query NSW Building Footprints or NSW DEM. Same class as bushfire BUG-4 and threat radar BUG-1.

**Severity:** Medium. False attribution undermines audit trail credibility.

**Fix:** Replace with actual data sources (NSW Planning Portal lot API, spatial_overlays height, pybdshadow + pvlib, Sentinel-2).

**BUG-9: Wrong library name in methodology (PDF line 567)**

States "pysolar" but the pipeline uses pvlib for solar position and pybdshadow for shadow casting.

**Severity:** Low. Methodology section names a library not used.

**Fix:** Change to "pvlib Solar Position Algorithm + pybdshadow shadow casting".

---

## 6. Limitations Statement

This pipeline CANNOT:
- Account for shadow from existing buildings, trees, fences, or infrastructure
- Model terrain slope (assumes flat ground)
- Account for road width between the subject lot and the northern neighbour
- Provide a formal shadow impact assessment (requires site-specific modelling by a qualified planner/architect)
- Determine compliance with site-specific DCP shadow controls
- Assess impact on specific windows, rooms, or private open space areas
- Replace shadow diagrams required for DA submission

---

## 7. Sign-off

- [x] All data sources documented with provenance
- [x] Algorithm correctly implements stated methodology
- [x] Response contract comment corrected (BUG-1 FIXED)
- [x] Connection leak fixed with finally block (BUG-2 FIXED)
- [x] "compliance" → "test" in transparency step (BUG-3 FIXED)
- [x] Assurance/guarantee language replaced (BUG-4, BUG-5, BUG-6 FIXED)
- [x] "strong result" evaluative language removed (BUG-7 FIXED)
- [x] PDF data currency table corrected — false sources removed (BUG-8 FIXED)
- [x] Wrong library name corrected (BUG-9 FIXED)
- [x] Disclaimer covers all identified limitations
- [x] Audit trail logging implemented for this pipeline

**Bugs found and fixed:** 9 (1 wrong comment, 1 connection leak, 2 false data attributions, 1 wrong library name, 4 language issues)
