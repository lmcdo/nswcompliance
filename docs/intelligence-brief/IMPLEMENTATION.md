# Intelligence Brief — Implementation Procedure (Corrected)

**Date:** 2026-05-25
**Status:** Definitive build plan
**Inputs:** ce-what-can-i-build-intelligence-brief.md (product), ce-intelligence-brief-qa-analysis.md (QA audit)
**Corrections vs draft:** See Section 0 below

---

## 0. Corrections From Draft

| # | Error in draft | Reality | Impact |
|---|---|---|---|
| 1 | Stage 3 said "wire DCP controls" as if new work | `fetch_dcp_setbacks` already queries `dcp_setback_controls` by LGA in the conveyancing PDF path (conveyancing.py:344). Returns all 16 control types. | Stage 3 is ~half a day of including existing data in JSON response, not 2 days of integration |
| 2 | Stage 5 said "wire shadow_detector" as new satellite work | `get_shadow_risk` is already imported and called in conveyancing PDF path (conveyancing.py:371). Shadow uses LEP height envelope, not satellite imagery. | Shadow is Layer A (planning-derived), not Layer B (satellite). Already wired. |
| 3 | Draft treated shadow_detector as satellite pipeline | Shadow uses pybdshadow geometric model + pvlib solar position + LEP height limits. No satellite data. It's deterministic from planning data + sun geometry. | Move shadow from "satellite tier" to "planning tier" — available in free brief |
| 4 | Draft said "strata lot NEVER receives development-framed output" | Strata townhouses and strata-titled duplexes DO have development potential. Strata ≠ apartment. `detect_strata` returns `is_strata: bool` but a strata duplex on its own lot still has granny flat potential. | Need `is_apartment_strata` vs `is_strata_house` distinction. Gate on building type, not just strata title. |
| 5 | Draft said "VG values → integer cents" | $1.92M = 192,000,000 cents. Conceptually odd and risks confusion. Better: integer dollars. Max NSW land value ~$50M = fits int32 easily. | Store as integer dollars |
| 6 | Draft proposed two-phase polling architecture for satellite | Over-engineered for v1. Simpler: accept longer response time (30-45s) with streaming/loading state. Polling adds client complexity, cache management, and a second endpoint. | v1: single synchronous response with timeout. v2: async if latency is validated as a real UX problem with users. |
| 7 | Draft's pricing ($149/mo Pro) conflicts with operating plan | Operating plan (biz-pricing-revision-and-actions.md) has different pricing structure. | Mark all pricing as placeholder. Don't commit pricing in technical plan. |
| 8 | Draft Stage 5 referenced pipelines as if all are satellite-based | Bushfire prescreen queries RFS ArcGIS REST (government API, no satellite). It's a live spatial query like Planning Portal — deterministic, authoritative for designation. Only the BAL estimate is modelled. | Bushfire is Layer A (authoritative designation) with a Layer B component (estimated BAL). Split accordingly. |
| 9 | Draft's liability scan targets "all text fields" | Must only scan LLM-generated content, not programmatic disclaimer, not data field names, not source names. | Scope scan to `narrative` field only |
| 10 | services/CLAUDE.md lists all pipelines as "not started" | All 5+ pipelines are live on Railway, merged (PR #181 bushfire, PR #170 flood, etc.). services/CLAUDE.md is stale. | Don't reference services/CLAUDE.md status. Trust INDEX_SATELLITE.md (memory) which shows live state. |
| 11 | Draft claimed intelligence brief needs `services/models/` new directory | No models directory exists. Could just put Pydantic models in `services/intelligence_brief.py` itself — same pattern as every other service file. | Don't create new directory structure for one file |
| 12 | `housing_sepp` in conveyancing response is just a boolean | It's derived in `parse_controls` from Planning Portal response — checks if SEPP Housing overlay applies. But doesn't include the detailed standards (min lot area, max GFA, setbacks). Those come from `housing_sepp_standards` table. | Brief needs both: the boolean flag (already have) AND the detailed standards (query `housing_sepp_standards` by zone — small addition) |

---

## Governing Principle

The conveyancing pipeline (`services/conveyancing.py`) already does the majority of what the intelligence brief needs. It:
- Resolves addresses via Planning Portal
- Fetches LEP controls (zone, height, FSR, heritage, SEPP overlays)
- Queries PostGIS spatial_overlays (15 layer types)
- Detects strata
- Gets land valuation (VG API)
- Searches nearby DAs (ePlanning API)
- Fetches DCP setbacks (PDF path — `fetch_dcp_setbacks`)
- Runs shadow analysis (PDF path — `get_shadow_risk`)
- Fetches heritage PostGIS (PDF path)
- Calculates development headroom + feasibility

The intelligence brief orchestrator = conveyancing pipeline + DCP values in JSON + SEPP Housing standards + satellite pipelines + compound constraints + LLM narration + new data sources.

**Don't rebuild. Extend.**

---

## Implementation Stages

### Stage 1: Contract + Schema (1.5 days)

**What:** Define the response schema. Every downstream stage implements against this contract.

**Deliverables:**
- Pydantic models in `services/intelligence_brief.py` (top of file, before route logic)
- `ConfidenceLevel` enum: `authoritative | extracted | estimated | derived | not_available | stale`
- `DataField` generic wrapper: `{ value, confidence, source, as_at, reason }`
- Three-state distinction: present data / queried-no-results / not-queried (per field)
- Two response templates: `DevelopmentBrief` (freestanding lots), `RenovationBrief` (apartment strata)
- Strata classification: apartment strata (no development analysis) vs house-on-strata-title (full analysis). Use lot area + building type, not just strata flag.

**Verification:**
- Write 4 fixture JSONs by hand: Inner West house, strata apartment, strata townhouse, rural lot
- Review schema covers all 4 correctly
- No code runs — this is a design checkpoint

**Why first:** If the schema is wrong, everything built on it needs rework. Getting null vs empty vs missing semantics right now prevents confusion later.

---

### Stage 2: Orchestrator (3 days)

**What:** New FastAPI endpoint that calls existing service functions, assembles results into the schema. No new data sources, no satellite, no LLM. Just restructure what conveyancing already produces.

**2.1 Endpoint skeleton**

`services/intelligence_brief.py`:
- Router: `POST /pipeline/intelligence-brief`
- Request: `{ address, lat?, lng?, prop_id?, include_satellite: bool = false }`
- Uses same imports as `conveyancing.py` (lines 71-85): `resolve_address`, `get_raw_controls`, `parse_controls`, `get_valuation`, `get_unique_overlays`, `detect_strata`, `detect_former_council`, `get_nearby_das`, `get_shadow_risk`
- Plus: `fetch_dcp_setbacks`, `fetch_heritage_postgis` from `conveyancing_db`

**2.2 Per-source wrappers (error isolation)**

Every external call wrapped:
```python
def _safe_call(fn, timeout_s, source_name, confidence_level):
    try:
        result = _run_with_timeout(fn, timeout_s)
        return DataField(value=result, confidence=confidence_level, source=source_name, as_at=now())
    except Exception as e:
        return DataField(value=None, confidence="not_available", source=source_name, reason=str(e))
```

Timeouts: Planning Portal 8s, PostGIS 3s, VG 5s, ePlanning DA 8s, shadow 10s.

**2.3 Address validation**

After geocode, verify:
- Coordinates inside NSW bbox (lat -37.5 to -28.0, lng 140.9 to 153.7)
- If lot geometry available: point is inside lot polygon
- If mismatch: include `address_quality: "approximate"` warning in response

**2.4 Strata handling**

```python
strata = detect_strata(address, lat, lng)
is_apartment = strata["is_strata"] and (lot_area > 1500 or unit_count > 4)  # heuristic
if is_apartment:
    return _build_renovation_brief(...)  # different template
# else: full development brief
```

**2.5 Include DCP values in response**

The conveyancing PDF path already calls `fetch_dcp_setbacks(conn, former_council, zone)`. The intelligence brief calls it too and includes the values directly in the JSON response (not hidden behind PDF generation). Additionally, query `housing_sepp_standards` for detailed SEPP eligibility standards (min lot area, max GFA, setbacks per dev type).

**2.6 Include shadow in free tier**

Shadow risk is planning-derived (geometric model from LEP height + sun position), not satellite. Include it in the free tier response. It's already called via `get_shadow_risk` — just include the result in the JSON.

**Verification:**
- `tests/test_intelligence_brief_parity.py`: call both `/pipeline/conveyancing` and `/pipeline/intelligence-brief` for 10 Inner West addresses. Assert shared fields (zone, height, FSR, heritage, flood, lot area, da_count) match exactly.
- Additionally verify: DCP controls populated, shadow result populated, SEPP standards populated (for eligible lots).

---

### Stage 3: Compound Constraints + Confidence (2 days)

**What:** The intelligence that emerges from combining data layers. Plus: staleness detection and gap disclosure.

**3.1 Compound constraint rules**

`services/compound_constraints.py`:

Each rule: predicate (does it potentially apply?) + caveat (what to verify) + severity (warning/info).

Rules for v1:
- heritage_hca AND bushfire_prone → severity depends on heritage subtype:
  - If `spatial_overlays.value` = "Conservation Area - Landscape" OR "garden" IN `v2_heritage_element` → HIGH: "10/50 clearing may conflict with heritage landscape character"
  - If "Conservation Area - General" AND "garden" NOT IN elements → MEDIUM: "10/50 clearing may apply — heritage character does not appear to involve vegetation (verify with council)"
- heritage_item AND flood_planning_area → "flood mitigation may require Heritage NSW concurrence"
- tod_precinct AND heritage_hca → "heritage character may restrict TOD density bonus"
- lot_area < (min_lot_size × 1.1) → "lot area is marginal for zone minimum — verify with survey"
- flood_epi AND heritage_item → "floor level mitigation may be heritage-restricted"
- zone_permits_higher_density (Fix B) → R3/R4/B1/B2 + dev_type=dwelling_house → "Zone permits higher-density types — controls shown are for dwelling house only"
- da_shadow_interaction (Fix C) → approved/assessed DA within 100m + multi-storey description pattern → "Active/approved DA within [X]m may affect future shadow"

Satellite-dependent rules (only evaluated when satellite data present, Phase 4):
- structure_detected AND no_da_record → "potential unapproved structure" (with caveat)
- NOT flood_epi AND (jrc > 2% OR sar_detected) → "flood evidence exceeds statutory designation"
- shadow_from_neighbour > 2hrs AND solar_access_requirement → "future development may impact solar"

Each rule outputs: `{ id, description, caveat, severity, data_sources_used }`

**3.2 Confidence + staleness**

Per-field confidence assigned based on source:
- Planning Portal → authoritative
- PostGIS spatial_overlays → authoritative (gov-sourced, but check ingest date)
- DCP controls → extracted (manual, QA'd). If `last_verified_at` > 180 days → stale
- Shadow model → derived (deterministic from authoritative inputs)
- VG land values → authoritative (if within 12 months of val base date, else stale)

Response includes:
- `data_currency_warnings`: list of sources approaching/exceeding staleness
- `gaps`: list of `{ field, reason, verify_url }` for every not_available field

**3.3 Gap disclosure**

If DCP not available: `{ field: "dcp_controls", reason: "DCP controls not yet extracted for [council]", verify_url: "[DCP PDF URL]" }`
If satellite not requested: not a gap (user chose not to include it) — don't list

**Verification:**
- `tests/test_compound_constraints.py`: 10+ fixture cases (each rule fires correctly, negatives don't fire)
- Known compound-constraint addresses produce correct flags
- Inner West address with no compound constraints → empty array

---

### Stage 4: Satellite Integration (3 days)

**What:** Wire the satellite pipelines that require separate processing: flood_truth, bushfire_prescreen, climate_risk_score, granny_flat (structure detection), pre_da_history.

Note: shadow is NOT here (it's in Stage 2, planning tier). Bushfire designation is authoritative (free tier); only BAL estimate is "estimated" confidence.

**4.1 Wire pipelines**

Each called via direct Python import (all in same Railway process):

| Pipeline | Module | Timeout | Confidence | Tier |
|---|---|---|---|---|
| flood_truth | services.flood_truth | 15s | estimated (multi-source) | Paid |
| bushfire_prescreen | services.bushfire_prescreen | 5s | authoritative (designation) / estimated (BAL) | Free (designation) / Paid (BAL detail) |
| climate_risk_score | services.climate_risk_score | 5s | estimated | Paid |
| granny_flat (detection) | services.granny_flat | 20s | estimated (70-80%) | Paid |
| pre_da_history | services.pre_da_history | 45s | estimated | Paid (premium) |

Each uses `_safe_call` wrapper from Stage 2. Failure of one doesn't block others.

**4.2 Response structure**

Synchronous for v1: client accepts longer response time (up to 45s with pre_da_history). Frontend shows loading state per-section.

If latency is a validated problem with real users (not hypothetical), THEN add async/polling in v2. Don't pre-optimise.

**4.3 Satellite compound constraints**

After satellite results, evaluate satellite-dependent rules from Stage 3.1. Append to compound_constraints array.

**4.4 Climate v2 additions (extend climate_risk_score from 5-hazard to 9+ hazard)**

Wire these alongside existing satellite pipelines. All use `_safe_call`. All return `DataField`.

| Source | Gap # | Data Source | Effort | Confidence |
|--------|-------|-------------|--------|------------|
| Sea level rise projections | #3 | AdaptNSW 2025 via SEED WFS | 2 days | authoritative (gov scenario) |
| Urban heat island (Phase 1) | #4 | NSW SEED UHI mesh block, ArcGIS REST | 2 days | authoritative (Landsat-derived, gov-published) |
| ARR design rainfall | #7 | ARR Data Hub REST API (any lat/lon) | 1 day | authoritative (BoM/ARR) |
| FIRMS fire proximity | #8 | NASA FIRMS REST API, VIIRS 375m | 0.5 day | estimated (satellite observation) |
| Vegetation/fuel load | #6 | samgeo extension (already in use for granny_flat) | 3 days | estimated (70-80%) |

Pre-Stage 4 bug fix (integrate into Stage 2): bushfire bbox limited to Greater Sydney in spatial_overlays — fall back to live RFS API when outside bbox.

Pre-Stage 4 bug fix (integrate into Stage 3): landslide data already in spatial_overlays but not wired into climate_risk_score — add as input.

**Parallel track (runs alongside Stage 5, not blocking):**
- xarray multi-GCM ensemble: NARCliM 2.0 has 10 members, we use 1. Pre-compute ensemble stats (min/median/max/P10/P90) to PostGIS via batch job. Brief queries PostGIS rows, not raw NetCDF. 1 week. Biggest credibility upgrade for APRA/AASB S2 scenario requirements.

**Stage 7 additions:**
- whitebox-tools (MIT): DEM-based watershed delineation + slope analysis. NSW 5m LiDAR from SEED. Pre-compute per-lot terrain metrics to PostGIS. 1 week.
- xarray ERA5-Land soil moisture: reactive clay/ground movement risk indicator. Pre-compute temporal stats to PostGIS. 3 days.

**Key constraint:** Heavy processing (xarray, whitebox-tools, rasterio thermal) is always pre-computed to PostGIS by batch jobs. The intelligence brief request path only queries PostGIS. No raw raster processing in-request.

Repos identified by repo-research v2 (2026-05-28): xarray (Apache-2.0), whitebox-tools (MIT), rasterio (BSD-3), samgeo (MIT).

**Verification (extends base Stage 4 gate):**
- SLR: coastal property shows current zone + 2050/2100 projected inundation
- UHI: Sydney metro property shows mesh block UHI delta vs rural baseline
- ARR: location IFD matches Bureau published tables
- FIRMS: property near 2019-20 fire perimeter shows satellite-detected events
- Vegetation: bushland-adjacent property shows higher fuel load than cleared suburban lot

---

### Stage 5: LLM Synthesis (3 days)

**What:** Natural language narration of the structured brief. Last feature layer — every field it references is already validated.

**5.1 Prompt template**

System prompt enforcing: factual only, every sentence maps to data, no recommendations, no prohibited language, gaps acknowledged explicitly.

6-section output template: Planning Controls → Physical Reality → Environmental → Neighbourhood → Economics → Data Gaps.

**5.2 Validation cage (mandatory)**

After LLM generates:
1. Prohibited language regex scan (targets narrative only, not disclaimer)
2. Numeric verification: every number in narrative exists in input JSON (within tolerance)
3. Section structure check: all 6 sections present
4. If >3 validation issues: reject narrative, serve structured data only, log for prompt iteration

**5.3 Cost controls**

- Claude Sonnet (sufficient quality, ~$0.01-0.03/brief)
- Free tier: NO narrative (structured data only)
- Cache: per normalised address, 24h TTL
- Daily cap: alert at $20, hard stop at $50

**5.4 Programmatic disclaimer**

Appended by code, not by LLM. Cannot be edited, shortened, or omitted by the model.

**Verification:**
- 20 fixture JSONs → generate → validate → all pass
- Adversarial input (prompt injection in address) → clean output
- Data with gaps → narrative acknowledges gaps in first sentence of relevant section
- Cost tracking: confirm <$0.03 per brief (Sonnet)

---

### Stage 6: Pre-Computation + Bulk (5 days)

**What:** Make it fast (pre-computed search index) and scalable (batch + prospector).

CRITICAL DESIGN PRINCIPLE: Pre-computed data is a **search index** — used for filtering/ranking candidate lots. The per-address intelligence brief ALWAYS queries live sources. The search index is never served as authoritative per-address data.

**6.1 Cadastre ingest** (1 day)
- `scripts/ingest_cadastre_lots.py`
- NSW FeatureServer/8, paginate 2000/page, ~14 min
- Transform EPSG:3857 → EPSG:4326
- Table: `cadastre_lots` (lotidstring PK, geometry GIST, area_m2, urbanity, has_strata, plan_label)
- Filter: urbanity='U' for search index (~2M lots)
- Weekly incremental sync via `modifieddate`

**6.2 VG ingest** (1 day)
- `scripts/ingest_vg_values.py`
- Valuation/MapServer/5, paginate 1000/page, ~18 min
- Parse "$1,920,000" → integer dollars
- Table: `vg_land_values` (propid PK, address, zone_desc, prop_area_m2, val1..val5 int, base_date1..5)
- Monthly refresh

**6.3 Search index** (1 day)
- `scripts/precompute_search_index.py`
- For each urban lot centroid: batch spatial query against spatial_overlays
- Table: `lot_search_index` (lotidstring FK, zone, area_m2, land_value_dollars, flood bool, heritage_hca bool, bushfire_prone bool, tod bool, precomputed_at timestamp)
- Name deliberately includes "search_index" — not "lot_data" or "lot_flags"
- Column `precomputed_at` enables staleness detection
- Refresh: re-run when spatial_overlays updated

**6.4 Prospector endpoint** (1 day)
- `POST /pipeline/prospector`
- Pure PostGIS query on `lot_search_index` joined with `cadastre_lots` + `vg_land_values`
- Requires min 2 filter criteria. Max 500 results. Paid only.
- Each result links to "Generate full brief" (real-time verification)
- Response caveat: "Based on pre-computed data. Generate a full brief to verify current status."

**6.5 Batch endpoint** (1 day)
- `POST /pipeline/intelligence-brief/batch`
- Paid only. Max 50 addresses. Auth required.
- 8 concurrent brief computations (rate-limit aware)
- Progress endpoint: `GET .../batch/{batch_id}`
- Failed addresses: explicit in response (never omitted)

**Verification:**
- Cadastre count ≈ 3.35M (spatial query for Inner West bbox ≈ 78K)
- VG join works (known address → correct land value)
- Search index: known heritage lot → heritage=true. Cross-check with real-time query.
- Prospector: reasonable result count for typical filter. Max 500 enforced. Empty filter rejected.
- Batch: 10 addresses complete correctly. 2 failures reported explicitly.

---

### Stage 7: Data Source Expansion (5 days)

Each is independent. Order by value/effort:

**7.1 School catchments** (1.5 days)
- Source: data.nsw.gov.au GeoJSON (nightly, CC-BY)
- Table: `school_catchments` (school_name, school_type, icsea_score, level, geometry GIST)
- Query: lot centroid → ST_Contains → school_catchments
- Refresh: weekly
- Test: Marrickville address → Marrickville Public + Marrickville High + ICSEA scores

**7.2 EPA contaminated sites** (1.5 days)
- Source: EPA register (monthly CSV or scrape)
- Table: `epa_contaminated_sites` (site_name, address, classification, status, geometry GIST)
- Geocode addresses without coordinates
- Query: lot within 500m of site. Distinguish on_site vs nearby.
- Test: known contaminated address → flagged on_site

**7.3 Easement layer** (1 day)
- Source: NSW Cadastre FeatureServer Layer 9 (CC-BY)
- Table: `lot_easements` (easement_type, width_m, beneficiary, geometry GIST)
- Query: spatial intersection with lot polygon
- Test: known easement lot → type + width returned

**7.4 ABS construction cost proxy** (0.5 days)
- Static: `services/data/abs_construction_cost.json` ($/m² by building type × region)
- Updated manually quarterly
- Computation: FSR × lot_area × $/m² → rough construction cost
- Caveat: "ABS PPI estimate, not QS assessment"

**7.5 Domain API listing status** (0.5 days if free tier works)
- Sign up first. Test free tier. Wire if listings available.
- If free tier doesn't expose listings: defer (don't pay for API before product has revenue)

**Verification:**
- Run 20 Inner West addresses → new fields populated
- Run 20 addresses in LGA with no DCP → gaps disclosed, new sources still populate
- EPA: test proximity logic (on_site vs 400m vs 600m)

---

### Stage 8: Production Hardening (3 days)

**8.1 Auth + rate limiting**
- API key via Supabase auth
- Per-key daily limits (tiers TBD — not committed here)
- Per-source upstream rate limiter (shared across all requests)
- Satellite + LLM + batch + prospector: paid tier only

**8.2 Caching**
- Planning brief: per normalised address, 24h TTL
- Satellite: per address + pipeline, 7d TTL
- LLM narrative: per address, 24h TTL (invalidate on data change)
- Search index: refreshed by ingest scripts, no TTL

**8.3 Monitoring**
- Per-pipeline latency (P50/P95/P99)
- Upstream API success rate (5-min rolling)
- LLM daily cost
- Brief success rate
- Cache hit rate
- Alerts: P95 > 10s, upstream > 20% failure, LLM > $30/day

**8.4 Audit trail**
- Extend existing `audit_trail.py`
- Log: request_id, address_hash, sources queried/failed, confidence summary, latency
- NOT: full address, full response, user identity

**8.5 Legal** (implements Four-Layer Defence — see "Legal & Liability Strategy" section below)
- Layer 1 (don't be wrong): Fixes A/B/C already implemented in Stages 2-3. Add "Report an error" button → DCP re-verification queue. Minimum viable brief policy (>30% not_available → refuse to serve + refund).
- Layer 2 (visual uncertainty): Confidence badges on every non-authoritative field. Gap disclosure as FIRST section. Header banner with data date. Per-source "as at" dates. Temporal coherence warning if oldest > 6mo from newest.
- Layer 3 (product framing): "Site Screening Brief" naming. "Preliminary screening only" label. 5-point Archistar-model limitations list. "Engage a town planner" CTA. Pass-through NSW DPHI disclaimer verbatim.
- Layer 4 (ToS): Liability cap at 6 months fees / $500 floor. Consequential loss exclusion. "As is" baseline. Scope limited to standard residential. Legal review before public launch (solicitor, non-negotiable).

---

## Silent Failure Fixes (Integrated into Stages 2-3)

Three silent failures identified through adversity drill-down — failures where the system returns a valid-looking response that is wrong or misleading, with no error. Each has a concrete fix costed at ~1.5 days total.

### Fix A: LGA Boundary Misclassification (integrate into Stage 2.2)

**Failure:** `detect_former_council` uses pure substring matching on address text. No coordinates. "Stanmore" → hardcoded to "marrickville". If property is actually in Leichhardt territory (boundary suburb), wrong DCP controls served.

**Root cause:** Function signature doesn't accept lat/lng. No PostGIS validation against LGA boundaries.

**Fix (0.5 day):**
```python
def _validate_lga_slug(slug: str, lat: float, lng: float, conn) -> tuple[str, bool]:
    """Cross-check text-derived LGA slug against spatial boundary.
    Returns (slug, is_validated). If mismatch: returns (corrected_slug, False)."""
    row = conn.execute("""
        SELECT slug FROM lga_registry r
        JOIN spatial_overlays s ON s.layer_type = 'lga_boundary'
        WHERE ST_Contains(s.geom, ST_SetSRID(ST_Point(%s, %s), 4326))
        LIMIT 1
    """, (lng, lat)).fetchone()
    if row and row[0] != slug:
        return row[0], False  # corrected
    return slug, True  # validated
```

Add after `detect_former_council()` call in orchestrator. If mismatch detected: use corrected slug + add advisory to response: "LGA boundary verified by spatial lookup (text-based detection returned [wrong], coordinates confirm [right])."

**If spatial_overlays doesn't have lga_boundary layer:** Fall back to checking if coordinates are inside any spatial overlay whose `instrument_key` matches the expected LGA name. Still better than nothing.

**Verification:** 5 boundary suburb addresses (Stanmore, Dulwich Hill, Summer Hill, Petersham, Annandale) → all resolve correctly.

---

### Fix B: Zone-Aware Dev Type Advisory (integrate into Stage 3.1)

**Failure:** `dcp_setback_controls` has NO zone column. Same controls returned for R2, R3, R4. When a lot is rezoned from R2→R3, user still sees dwelling_house controls with no awareness that multi-dwelling housing is now permitted.

**Root cause:** DCP controls are genuinely uniform per dev_type in most councils. The issue isn't wrong setbacks — it's missed opportunity (user doesn't know higher-density types are permitted).

**Fix (2 hours):** Add to compound constraints (Stage 3.1):

```python
ZONE_DEV_TYPE_ADVISORY = {
    "R3": ["multi_dwelling_housing", "residential_flat_building"],
    "R4": ["residential_flat_building", "shop_top_housing"],
    "B1": ["commercial_premises", "shop_top_housing"],
    "B2": ["commercial_premises", "residential_flat_building"],
}

def _check_zone_dev_type_awareness(zone: str, requested_dev_type: str) -> Optional[CompoundConstraint]:
    zone_prefix = zone.split(" ")[0] if zone else ""
    additional = ZONE_DEV_TYPE_ADVISORY.get(zone_prefix)
    if additional and requested_dev_type == "dwelling_house":
        return CompoundConstraint(
            id="zone_permits_higher_density",
            description=f"Zone {zone_prefix} permits additional development types: {', '.join(additional)}. Controls shown are for dwelling house only.",
            severity="info",
            caveat="Check LEP land use table for full list of permissible uses in this zone."
        )
```

**Not a liability risk** — no case law for "you didn't tell me I could build more." But significant value-add for buyer's agents assessing development upside.

**Verification:** R3 lot with dev_type=dwelling_house → advisory appears. R2 lot → no advisory.

---

### Fix C: Shadow Temporal Gap + DA Cross-Reference (integrate into Stage 3.1)

**Failure:** Shadow model returns `overlap=0` (correct today). RFB approved 50m away last month. User interprets "no shadow" as permanent. Shadow report only says "re-run if LEP updated" — no mention of future developments.

**Root cause:** `get_nearby_das()` returns DA description but not proposed height. No connection between DA data and shadow model. Temporal disclaimer is weak.

**Fix — two parts:**

**Part 1: Temporal disclaimer (30 min).** Add to shadow output:
```python
"temporal_caveat": "Shadow analysis reflects current height controls only. Does not account for approved or pending development applications on adjacent lots. Check NSW Planning Portal for nearby DAs."
```

**Part 2: DA→shadow compound constraint (4 hours).** When nearby DAs are fetched:
```python
import re

HIGH_DENSITY_PATTERN = re.compile(
    r'\d+\s*stor|apartment|RFB|residential flat|multi.?storey|mixed.?use',
    re.IGNORECASE
)

def _check_da_shadow_interaction(das: list, shadow_result: dict, lat: float, lng: float) -> Optional[CompoundConstraint]:
    """Flag if approved/assessed DA nearby could affect future shadow."""
    for da in das:
        if da.get("status") in ("Approved", "Determination", "Under Assessment"):
            if da.get("distance_m", 999) <= 100:
                if HIGH_DENSITY_PATTERN.search(da.get("description", "")):
                    return CompoundConstraint(
                        id="da_shadow_interaction",
                        description=f"Active/approved DA within {da['distance_m']}m ({da['number']}) appears to involve multi-storey development. Future shadow impact possible.",
                        severity="warning",
                        caveat="Shadow model uses current LEP height envelope. Actual approved heights may differ. Check DA documentation on NSW Planning Portal.",
                        data_sources_used=["ePlanning DA API", "shadow_detector"]
                    )
    return None
```

**v2 enhancement (NOT v1):** Extract proposed height from ePlanning API response object and recalculate shadow with that height as a scenario. This requires parsing deeper into the DA API response — defer until product has users.

**Verification:** Address with approved RFB within 100m → compound constraint fires. Address with no nearby high-density DAs → no flag. Shadow temporal caveat present on all shadow outputs.

---

## Legal & Liability Strategy

### Case Law Position

Based on analysis of Australian proptech litigation (Shaddock, Tepko, Esanda, Butcher, Makings, Hyder, Geju, Lorenzato):

**Our strongest defences:**
- **Tepko v Water Board [2001] HCA:** Info labelled as provisional/indicative + recipient has professional advisers = no duty of care. Strong for B2B (buyer's agents, planners).
- **Butcher v Lachlan Elder [2004] HCA:** Prominent disclaimer + provider clearly a conduit + reasonable person would understand = disclaimer effective. Blueprint for our in-product language.
- **Esanda v Peat Marwick [1997] HCA:** Publishing to general class without knowing specific transaction = no assumption of responsibility.
- **Hyder v McGrath [2018]:** Even where s18 ACL proven, buyer's contributory negligence reduces damages 50-67%.

**Our risk scenario:**
- **Shaddock v Parramatta [1981] HCA:** Specific information, clearly relied upon, factually wrong = duty of care. Applies if: DIY homeowner, no planner, builds to our setback number, council enforces.
- Mitigated by: "extracted" confidence label, "verify with council" CTA, per-field source attribution, prominent disclaimers.

**Industry precedent:** CoreLogic has operated 40 years without a successful data accuracy claim. No Australian proptech has lost a case for data inaccuracy. PropTrack caps liability at $100. BYDA (life-safety data for underground utilities) caps at $100. The NSW Planning Portal itself disclaims its own accuracy.

### Four-Layer Defence Architecture

**Layer 1: Don't be wrong** (eliminates the claim entirely)
- Fix A: PostGIS LGA validation (0.5 day)
- Fix B: Zone dev_type advisory (2 hours)
- Fix C: Shadow temporal disclaimer + DA compound constraint (4.5 hours)
- User feedback loop: "Report an error" button → feeds DCP re-verification queue
- Minimum viable brief policy: if >30% of Layer A fields are not_available, refuse to serve — return "insufficient data for screening" with refund

**Layer 2: Make uncertainty visually undeniable** (defeats "I didn't see the disclaimer" — Butcher standard)
- Every DataField with confidence < "authoritative" → amber visual indicator (not fine print)
- Compound constraints → interstitial cards between sections, not footnotes
- Gap disclosure → FIRST section of the brief, not last
- DCP source attribution inline: "Extracted [date] — verify against current DCP"
- Brief header banner: "Site screening data as of [date]. Conditions may have changed."
- Per-source "data as at" dates visible on every field group
- Temporal coherence warning: if oldest source > 6 months from newest, prominent "Data spans [oldest] to [newest]" notice

**Layer 3: Product framing** (sets legal characterisation as "information" not "advice")
- Product name: "Site Screening Brief" — never "Assessment" or "Report" or "Certificate"
- Every output labelled: "For preliminary screening purposes only"
- Explicit limitations list (Archistar model):
  1. Generated without physical site inspection
  2. Does not consider site-specific conditions visible only on site
  3. Does not account for future development applications on adjacent lots
  4. Data sourced from NSW government and council sources — accuracy not independently verified
  5. Not a substitute for professional planning, legal, or building advice
- CTA: "Engage a qualified town planner for site-specific assessment"
- Compound constraint language: "Potential interaction identified" not "conflict detected"; "may" not "will" or "does"

**Layer 4: Terms of service** (last resort, reduces quantum)
- Liability cap: 6 months subscription fees (Archistar precedent) or $500, whichever is greater
- Consequential loss exclusion (universal industry practice — excludes lost profits, bad purchase decisions, demolition costs)
- "As is, as available" baseline
- Pass-through NSW Planning Portal disclaimer verbatim: "DPHI does not warrant this material is free from errors or omission"
- Statutory rights preservation (ACL s64A — legally required, cannot contract out)
- "Reasonable endeavours" for error correction (not "best efforts" — lower legal standard)
- Clear scope: "standard residential properties including freestanding dwellings, secondary dwellings, and dual occupancies" (Microburbs model — limits product scope explicitly)
- Legal review by solicitor before public launch (non-negotiable)

### Liability Matrix (Updated)

| Risk | What goes wrong | Likelihood | Impact | Mitigation | Legal defence | Residual |
|---|---|---|---|---|---|---|
| Wrong LGA (boundary suburb) | detect_former_council resolves to wrong former council | Medium | High (wrong DCP) | **Fix A: PostGIS cross-check** (Stage 2) | If fix works: no claim. If fix somehow fails: Tepko (provisional) + Hyder (contributory negligence) | Low after fix |
| Wrong zone | Recent LEP amendment, Portal lag | Low | High (wrong controls) | Planning Portal is authoritative. Data currency shown. Zone mismatch → gap disclosure. | Upstream responsibility. We relay, not interpret. Butcher (conduit). | Low |
| Wrong overlay (geocode offset) | 50m offset → wrong lot → wrong overlays | Medium | Critical | Address validation (Stage 2.3). Lot polygon containment check. Warning on low match confidence. | Tepko (provisional) + Butcher (disclaimer prominent) | Medium — geocode imprecision inherent |
| Wrong DCP value (extraction typo) | Manual extraction error in db | Medium | High (wrong setback) | `last_verified_at` staleness. PDF source link. "Extracted — verify with council." User error reporting. | Tepko (provisional info) + Hyder (user should verify) + "extracted" confidence (not "authoritative") | Medium — can't catch at runtime |
| Zone change → stale DCP | R2→R3 rezone, DCP still shows R2 controls | Low | Medium | **Fix B: advisory** (Stage 3). DCP filter is by dev_type not zone. Controls often zone-agnostic for dwelling_house. | Low actual liability (controls usually still valid for requested dev_type). Advisory covers the gap. | Low |
| Shadow temporal gap | Shadow=0 today, RFB approved next door | Medium | Medium (missed future impact) | **Fix C: temporal disclaimer + DA compound constraint** (Stage 3) | Tepko (data clearly dated). No case law for "didn't predict future." Data was correct when issued. | Low after fix |
| False "no flood" | EPI clear + stale overlays + no satellite | Low | Critical (financial loss) | 6-source flood fusion (paid). EPI-only note: "statutory designation only." Cross-source mismatch → flag. | Butcher (prominent limitations). Upstream data responsibility. | Low (multi-source) |
| LLM hallucination | States constraint not in data | Medium | High | Validation cage. No LLM on free tier. Template structure constrains output. | If cage catches: no claim. If slips through: immediate removal + Butcher (prominent "AI-generated" label). | Low (cage catches most) |
| Strata misclassification | Strata townhouse treated as apartment (or vice versa) | Low | Critical (wrong brief template) | Multi-signal gate (lot area + building type). Conservative: uncertain → renovation scope. | Tepko (provisional). Conservative bias = user gets less, not wrong info. | Low |
| Compound constraint false positive | Rule fires but doesn't apply to specific lot | Medium | Medium (wasted investigation) | Every rule has caveat + verify link. Language: "may" not "will." Heritage subtype narrows false positives (Fix: use v2_heritage_element). | Not a liability risk (over-caution, not harmful advice). Information, not recommendation. | Accepted |
| IP theft (DCP scraped) | Competitor extracts our moat via API | Medium | High (moat erosion) | Rate limiting. No raw DCP on free tier. Account verification. | Not a safety risk — commercial risk. Managed by access controls. | Medium |
| DIY homeowner builds to wrong setback | DCP typo + no planner + council enforcement | Very low | Critical (demolition order) | All 4 layers active. "Verify with council" on every DCP value. "Engage a planner" CTA. Error report button. | Tepko weakened (no adviser). BUT: liability cap ($500/6mo fees), consequential loss excluded, Hyder reduces 50-67%. Realistic worst case: refund subscription. | Low (probability × capped exposure) |

### Nuclear Scenario Assessment

**Theoretical worst case:** ACCC enforcement for systematic misleading conduct (ACL s18). Pattern of wrong data across multiple users.

**Probability:** Near zero. ACCC has never pursued a proptech company for data accuracy. They pursue property spruikers making return guarantees — a completely different pattern. Our product makes no claims, guarantees, or recommendations. Every field carries confidence + source + date.

**If it happened:** The four-layer defence means conduct is unlikely to be characterised as "misleading" — we explicitly disclaim accuracy, label confidence, show gaps, and direct to professionals. The product literally shows you what it doesn't know.

### Minimum Viable Brief Policy

If >30% of planning-tier (Layer A) fields are `not_available` after all queries complete:
- Do NOT serve the brief
- Return: "Insufficient data available for this address. [X] of [Y] data sources returned errors. Try again later or contact support."
- If payment was taken: automatic refund
- Log: alert for investigation (upstream API issues?)

Threshold: 30% of Layer A fields = approximately 5+ core fields failed (zone, height, FSR, lot_area, heritage, flood, overlays all down). This only happens during major API outage, not normal operation.

---

## What NOT to Build (and why)

| Feature | Why not |
|---|---|
| Conversational chatbot | Uncontrollable output surface. Every response needs validation. Brief is single-generation (controllable). Chatbot is Year 2 after brief proves market. |
| CDC eligibility determination | ~15 exclusion conditions in SEPP (E&C) 2008. Getting any wrong = wrong pathway advice. Say "meets minimum thresholds" + "verify CDC eligibility with certifier." |
| Async/polling response architecture (v1) | Over-engineered. Accept 30-45s response with loading state. Add polling only if real users validate latency as a problem. |
| DA outcome prediction | No data (ePlanning doesn't distinguish approved/refused). Year 2 when web-scraped outcome data exists. |
| Multi-state expansion | Different APIs, regulations, spatial formats per state. Prove NSW works and earns revenue first. |
| Separate models/ directory | All other services have models inline. Don't create new structure for one file. |
| Pre-computed data served as authoritative | Stale data served as fact = catastrophic. Search index only. Brief always queries live. |

---

## Timing Summary

| Stage | Days | Cumulative | Deliverable | Silent Failure Fixes Included |
|---|---|---|---|---|
| 1. Contract + Schema ✅ 2026-05-27 | 1.5 | 1.5 | Schema reviewed, fixtures validated (PR #386) | — |
| 2. Orchestrator 🔧 in progress | 3.5 | 5 | `/pipeline/intelligence-brief` returns full planning brief (free tier) | Fix A (LGA PostGIS validation) |
| 3. Compound Constraints | 2.5 | 7.5 | Multi-source insights + confidence + gap disclosure | Fix B (zone dev_type advisory) + Fix C (shadow temporal + DA cross-ref) |
| 4. Satellite + Climate v2 | 10 | 17.5 | Paid tier with satellite evidence + SLR, UHI, ARR, FIRMS, vegetation | Bushfire bbox fix (Stage 2 prep) |
| 5. LLM Synthesis | 3 | 20.5 | Natural language narrative (paid tier) | — |
| 5.5 Multi-GCM ensemble (parallel) | 5 | — | xarray ensemble stats pre-computed to PostGIS | — |
| 6. Pre-Computation + Bulk | 5 | 25.5 | Prospector + batch endpoints | — |
| 7. Data Source Expansion | 8 | 33.5 | School, contamination, easements, cost proxy + whitebox hydrology, ERA5 soil moisture | — |
| 8. Production Hardening | 3 | 36.5 | Auth, billing, monitoring, legal review | — |

**Net addition from silent failure fixes: +1 day.** Climate v2 additions: +10 days. Total: ~36.5 days.

**Demo-ready for buyer's agents: after Stage 2 (day 5).** Planning brief with DCP controls, shadow analysis, SEPP eligibility, all overlays, nearby DAs, land value, LGA validation — richer than anything else on the market. Satellite, climate v2, and LLM are "coming soon" features to discuss, not demo.

---

## Per-Stage Verification Gates

No stage proceeds until the previous stage's verification passes. This is the stability mechanism.

| After Stage | Must pass before proceeding |
|---|---|
| 1 | Schema review: 4 fixture JSONs correctly represent all scenarios |
| 2 | Parity test: 10 addresses match conveyancing output + DCP values populated. **Fix A gate:** 5 boundary suburb addresses (Stanmore, Dulwich Hill, Summer Hill, Petersham, Annandale) all resolve to correct former council via PostGIS validation. |
| 3 | Compound constraints: 10+ fixture cases (positives + negatives). **Fix B gate:** R3 lot with dev_type=dwelling_house → zone advisory appears; R2 lot → no advisory. **Fix C gate:** Address with approved RFB within 100m → DA-shadow compound constraint fires; shadow temporal caveat present on all shadow outputs. Heritage compound constraints use `v2_heritage_element` to distinguish landscape vs general. |
| 4 | Satellite: standalone pipeline output matches brief satellite output for 5 addresses |
| 5 | LLM: 20 fixture JSONs → validation cage passes on all. No prohibited language. Disclaimer is programmatic (appended by code, not LLM-generated). |
| 6 | Bulk: prospector returns reasonable results. Search index matches real-time for 10 addresses. |
| 7 | New sources: per-source test cases pass. No regressions on existing fields. |
| 8 | Load test: 50 concurrent requests handled. Monitoring dashboard accurate. Legal: solicitor has reviewed ToS + in-product disclaimers + four-layer defence architecture. |

Each gate is a pytest file. Green = proceed. Red = fix before next stage.
