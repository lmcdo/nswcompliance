# Intelligence Brief — QA Analysis & Adversity Audit

**Date:** 2026-05-25
**Tier:** Critical (user-facing output informing financial decisions, multiple external APIs, data synthesis, potential liability)
**Depends on:** ce-what-can-i-build-intelligence-brief.md (product plan)

---

## 1. Severity Classification

| Field | Answer |
|-------|--------|
| **Tier** | Critical |
| **Justification** | Output informs property purchase decisions ($500K-$3M), touches 6+ external APIs, synthesises data that users treat as authoritative, LLM layer adds hallucination risk, legal liability if output is wrong |
| **Modes required** | ALL 9 modes at full depth |

---

## 2. Pre-Implementation Questions (Critical — all 6)

| # | Question | Answer |
|---|----------|--------|
| 1 | What existing data/state does this change interact with? | 8+ tables (spatial_overlays, dcp_setback_controls, lep_land_use_table, housing_sepp_standards, regulatory_provisions, dcp_precinct_boundaries, lep_zone_coverage, property_reports). 6+ external APIs (Planning Portal, Cadastre, VG, ePlanning DA, RFS bushfire, DEA WOfS). New tables: cadastre_lots, vg_land_values, school_catchments, epa_contaminated_sites, lot_overlay_flags, lot_dcp_controls |
| 2 | What happens if existing data doesn't match assumptions? | **Specific failure modes below (Section 6)** |
| 3 | Will this change be picked up by existing rows, or only new ones? | Mixed — pre-computed tables serve existing lots; new lots appear via weekly cadastre sync. Intelligence brief is computed fresh each request for satellite layers, but uses pre-computed planning data. Risk: pre-computed data goes stale if underlying source updates but re-computation hasn't run. |
| 4 | What does the external source return on miss/error? | **Per-source failure matrix below (Section 8)** |
| 5 | Does the frontend type need updating? | Yes — new IntelligenceBriefResponse interface, new page components, confidence badge components |
| 6 | What does the user see if this fails? | **Per-component failure UX below (Section 9)** |

---

## 3. Boundary-Trace — Primary Values

### Trace 1: `address` (user input → all pipelines → response)

```
User enters address string
  → orchestrator receives raw string
    → resolve_address() geocodes via Planning Portal
      ⚠️ BOUNDARY: What if geocode fails? (typo, new subdivision, rural address)
      ⚠️ BOUNDARY: What if geocode returns WRONG coordinates? (off-by-one lot)
    → coordinates (lat, lng) passed to ALL downstream pipelines
      ⚠️ BOUNDARY: Some pipelines expect (lat, lng), others expect (lng, lat)
      ⚠️ BOUNDARY: PostGIS uses ST_MakePoint(lng, lat) — easy to swap
    → Planning Portal layerintersect uses propId (not coordinates)
      ⚠️ BOUNDARY: propId from geocode may not match actual property if geocode is imprecise
    → Spatial overlay queries use coordinates
      ⚠️ BOUNDARY: Lot boundary vs centroid — point query may miss edge-case overlays
    → DCP controls lookup uses zone + precinct (derived from coordinates)
      ⚠️ BOUNDARY: precinct_id derived from spatial match — what if lot straddles two precincts?
    → Satellite pipelines use coordinates + lot geometry
      ⚠️ BOUNDARY: SAMGeo uses aerial imagery tile — tile boundary may bisect lot
    → All results assembled into response keyed by original address
      ⚠️ BOUNDARY: Address normalisation — "42 Smith St" vs "42 Smith Street" vs "42 SMITH ST"
```

**Critical issues found:**
1. **lat/lng swap** — must enforce a single convention throughout orchestrator. Python services use (lat, lng). PostGIS uses ST_MakePoint(lng, lat). The existing codebase has this wired correctly per-pipeline, but the orchestrator aggregating them must not introduce swaps.
2. **Geocode precision** — Planning Portal geocode returns propId. If it returns the wrong lot (adjacent), ALL downstream data is wrong for the right address. Mitigation: verify returned address string matches input.
3. **Address normalisation** — the same physical lot can be represented with different address strings. Must normalise before caching or comparing.

### Trace 2: `confidence` (assigned per field → aggregated → rendered)

```
Each data source produces data:
  Planning Portal → authoritative (live gov API)
  DCP controls → extracted (manual + QA'd)
  SAMGeo detection → estimated (model, 70-80% accuracy)
  Climate risk score → estimated (model with documented limitations)
  
Orchestrator assigns confidence per field:
  ⚠️ BOUNDARY: What if a "high confidence" source returns stale data?
    (Planning Portal caches, LEP may have been amended since last API call)
  ⚠️ BOUNDARY: What if DCP extraction was wrong? (it's "extracted" confidence but could be incorrect)
  ⚠️ BOUNDARY: Confidence label creates false assurance — user trusts "authoritative" without checking

Aggregated confidence_summary:
  ⚠️ BOUNDARY: A brief with 35 "authoritative" fields + 2 "not_available" looks complete
    — but one of the "authoritative" fields being wrong is catastrophic
    (e.g. zone returned as R2 when lot is actually R3 due to recent rezoning)
```

**Critical issues found:**
1. **Staleness is invisible** — confidence reflects source type, not currency. A "high confidence" field from Planning Portal may reflect data from before a recent LEP amendment.
2. **False completeness** — 95% of fields green creates perception that the brief is comprehensive. The 5% that's missing might be the binding constraint.
3. **DCP extraction errors look authoritative** — once in the DB, extracted data is served as fact. No automatic re-verification against source.

### Trace 3: `compound_constraints` (multi-source → rule → output text)

```
Compound constraint detection:
  Input: heritage=true AND bushfire_prone=true
  Rule: flag "Heritage × Bushfire: 10/50 clearing may conflict with heritage character"
  
  ⚠️ BOUNDARY: What if heritage data is from Planning Portal but bushfire is from RFS API?
    — Different data currency. Heritage listed yesterday, bushfire map from 2023.
  ⚠️ BOUNDARY: What if the compound constraint doesn't apply to this specific lot?
    — Heritage item on the lot vs HCA for the area vs heritage item on ADJACENT lot
    — 10/50 clearing only applies if vegetation is within APZ distance
    — The rule is generic; the lot may be an exception
  ⚠️ BOUNDARY: What if we flag a compound constraint that's not actually a conflict?
    — User wastes money investigating a non-issue
    — But NOT flagging a real conflict = user buys property unaware of constraint
```

**Critical issues found:**
1. **Generic rules applied to specific lots** — compound constraint detection must be conditional, not just "if A AND B then flag." Need spatial/contextual checks.
2. **False positives vs false negatives** — asymmetric risk. A false positive wastes time. A false negative leads to a bad purchase. Must bias toward over-flagging with clear "verify" language.
3. **Data currency mismatch** — combining data from different timestamps requires noting the oldest data point in the compound constraint output.

---

## 4. Checklist Mode — Five Categories

### 4a. Data Flow

| Check | Issue found? | Severity |
|-------|-------------|----------|
| Every field entering orchestrator has valid type at exit | YES — satellite pipelines return different response shapes (some nest under `outputs`, some don't). Must normalise before assembly. | Medium |
| null vs undefined vs false distinguished | YES — Python returns None, TypeScript uses undefined and null. Cross-boundary (Python API → JS frontend) must map consistently. | Medium |
| Array fields: empty array vs null vs missing key | YES — `heritage_items: []` vs `heritage_items: null` vs missing key have different meanings (no heritage vs data unavailable vs field not queried). Must distinguish in schema. | High |
| Date/time fields: timezone consistency | YES — Planning Portal dates are Sydney local. SAR dates are UTC. Climate data dates vary. Must normalise to ISO 8601 with timezone in response. | Medium |
| Numeric precision: float vs int vs string | YES — VG land values stored as "$1,920,000" strings. DCP controls use float (value_min, value_max). FSR is a ratio (0.5:1). Height is metres (9.5). All need explicit type in response schema. | Medium |

### 4b. Auth/Gate

| Check | Issue found? | Severity |
|-------|-------------|----------|
| Satellite data (paid tier) gated correctly | DESIGN NEEDED — include_satellite flag must be enforced server-side. Client can't just set flag=true. Needs auth token + Stripe subscription check. | High |
| Batch endpoint can't be abused for free bulk queries | DESIGN NEEDED — rate limiting per API key. Free tier: 5 briefs/day. Batch endpoint: paid only. | High |
| Prospector query can't be used to dump entire cadastre | DESIGN NEEDED — max results per query (500). No "WHERE 1=1" equivalent. Require at least one filter criterion. | High |
| LLM costs don't spiral on free tier | DESIGN NEEDED — LLM synthesis only on paid tier, or budget-cap per user/day. | Medium |

### 4c. Error Propagation

| Check | Issue found? | Severity |
|-------|-------------|----------|
| Planning Portal down → what does user see? | MUST DEFINE — partial brief (other sources still work) with planning fields marked "temporarily unavailable", NOT a full error page. | High |
| One satellite pipeline fails → other results still returned? | MUST IMPLEMENT — each pipeline in its own try/except. Failure of one doesn't block others. Return partial results with failed pipeline marked "unavailable". | High |
| Geocode fails → entire brief fails | ACCEPTABLE — can't produce any meaningful data without coordinates. But error message must be helpful ("Address not found. Try including suburb and state.") | Medium |
| Pre-computed data not yet available for this lot → what happens? | MUST HANDLE — fall back to real-time queries (slower but correct). Don't show blank brief. | Medium |

### 4d. Concurrency

| Check | Issue found? | Severity |
|-------|-------------|----------|
| Parallel API calls share rate limits | YES — Planning Portal has undocumented rate limits. If orchestrator fires 6 parallel calls to same API, may hit 429. Need shared rate limiter across concurrent requests. | High |
| Thread pool isolation | YES — if shadow_detector hangs (pybdshadow calculation edge case), must not block flood_truth response. Per-pipeline timeout required. | Medium |
| Batch endpoint: 50 briefs × 6 API calls each = 300 concurrent API calls | YES — must limit concurrency. Max 4-8 parallel brief computations in batch. Queue the rest. | High |
| Pre-computation script: bulk spatial queries lock DB | POSSIBLE — `ST_Contains` across millions of rows can lock spatial_overlays for reads if vacuum is running. Use read replica or run during low-traffic. | Low |

### 4e. Locale/Formatting

| Check | Issue found? | Severity |
|-------|-------------|----------|
| Dollar amounts: locale-explicit | YES — VG returns "$1,920,000". Must parse to numeric for computation, format back with locale for display. | Low |
| Area: m² symbol rendering | YES — must use proper Unicode ² in LLM output and frontend, not "m2" or "sqm" (professionalism signal). | Low |
| Coordinates: decimal places | YES — 6 decimal places standard for sub-metre precision. Don't serve raw float (15+ decimals). | Low |
| Dates: ISO 8601 in API, DD/MM/YYYY in UI | YES — consistent across all pipelines. Python `date.isoformat()` in API. Frontend formats for display. | Low |

---

## 5. Adversarial Mode — Full

| # | Scenario | What happens | Severity | Mitigation |
|---|----------|-------------|----------|------------|
| 1 | User queries address that was recently rezoned (LEP amendment gazetted last week). Planning Portal returns NEW zone. DCP controls in our DB are for OLD zone. | Brief shows new zone R3 but DCP setbacks are R2 setbacks from before rezoning. Contradictory data. User sees: "Zone: R3. Rear setback: 8m (DCP)" — but 8m was the R2 control. | **Critical** | DCP controls lookup must join on zone. If zone from Portal ≠ zone in DCP extraction → flag gap: "DCP controls not yet verified for current zoning." Periodic re-extraction when zone changes detected. |
| 2 | User queries a strata lot (apartment). System treats it like a development site. FSR, setbacks, granny flat eligibility all returned as if it's a detached lot. | Completely misleading brief. "Granny flat eligible: lot > 450m²" — but it's a 90m² apartment. The 450m² is the parent title area. | **Critical** | Strata detection (existing: detect_strata) must gate the entire brief framing. If strata → different output template: "This is a strata lot. Development controls apply to the strata scheme, not individual lots. Renovation/modification scope only." Skip granny flat, skip dual occ, skip FSR utilisation. |
| 3 | Two users query the same address simultaneously. Both trigger satellite pipelines. SAMGeo runs twice on same imagery, doubling compute cost. | Cost issue, not correctness issue. But at scale (100 concurrent users), compute bill spikes. | Medium | Cache satellite results per address with 24h TTL. Second request reads cache. Key: normalised address + pipeline name + date. |
| 4 | User queries an address in an LGA with no DCP extraction. Brief returns planning controls (Zone, height, FSR) but ALL DCP fields are "not_available". LLM synthesis generates narrative that reads as complete ("Your property has height 9.5m and FSR 0.5:1") without mentioning the missing DCP context. | User thinks the brief is comprehensive because the LLM wrote confidently about what IS available. The missing setback data (which might be the binding constraint) is buried in a "gaps" section they don't read. | **High** | LLM prompt MUST include explicit instruction: "If DCP controls are not available, the FIRST sentence of the planning section must state this." Alternatively: don't generate LLM narrative unless confidence_summary.not_available < threshold. |
| 5 | Geocode returns coordinates 50m off (rural address, long driveway). Point lands on adjacent lot. ALL spatial overlay queries use wrong lot. Heritage flag comes back as "not heritage" but the actual lot IS heritage-listed. | Entire brief is for the wrong lot. User trusts it because everything else looks reasonable. They buy the property not knowing it's heritage-listed. | **Critical** | Return the resolved address string from geocode. If it doesn't match input (after normalisation), warn: "Resolved to: [resolved address]. If this doesn't match your property, provide Lot/DP number for precise lookup." Also: cross-check returned propId against lot geometry — is the coordinate inside the lot polygon? If not, flag discrepancy. |
| 6 | LLM hallucinates a constraint that doesn't exist in the structured data. E.g., "Note: this property requires a geotechnical assessment due to slope" — but no slope data is in the JSON input. | User believes a non-existent constraint applies. Either wastes money on unnecessary assessment, or (worse) if LLM says "no constraints" when there are some. | **High** | LLM synthesis must be STRUCTURALLY constrained: output template has fixed sections, each section can ONLY reference fields present in the input JSON. Post-processing: regex or assertion that every factual claim in the output maps to a JSON field. If unmapped claim detected → strip it and log for review. |
| 7 | Pre-computed overlay flags become stale. Council uploads new flood study to SEED. Pre-computed table says "not flood prone." Real-time query would return "flood planning area." | User buys property based on stale pre-computed data that says no flood. Actual flood planning area applies. | **Critical** | Two-tier: pre-computed data used for Prospector filtering. Intelligence Brief (per-address) must ALWAYS run real-time spatial query against live spatial_overlays table (which is updated by ingest scripts). Pre-computed flags are for search/filter speed only, never served as authoritative per-address. |
| 8 | ePlanning DA API returns "Determined" for a nearby DA. Brief says "1 determined DA within 200m." User interprets as "approved." Actually it was refused. | Misleading neighbourhood context. If it was a large RFB that was refused, user's amenity isn't threatened. If it was approved, it is. The brief can't distinguish. | **Medium** | Brief text must explicitly state: "Determined status (approval or refusal not distinguished in NSW Planning Portal data)." Never imply determined = approved. This is already documented in memory but must be enforced in LLM prompt and structured output. |
| 9 | User submits batch of 50 addresses. 48 succeed, 2 fail (geocode timeout). Batch endpoint returns partial results. User doesn't notice 2 are missing from the CSV export. | Data gap in bulk output that user may not check. | Medium | Batch response must include explicit `failed: [{address, reason}]` array at TOP of response (not buried). CSV export must include failed rows with "FAILED — [reason]" in data columns. Never silently omit. |
| 10 | Competitor scrapes the intelligence brief endpoint. Reverse-engineers our DCP data by querying every address in an LGA. | IP theft of manually-extracted DCP controls — our most defensible moat. | **High** | Rate limiting per API key. IP-based throttling on free tier. Require account creation for any API access. Don't expose raw DCP control values in free tier — show "DCP setback controls available" as a teaser, reveal values on paid tier only. Prospector endpoint: paid-only from day 1. |

---

## 6. Security Mode

| Check | Issue found? | Severity | Mitigation |
|-------|-------------|----------|------------|
| SQL injection via address input | RISK — address string used in text search queries. Must be parameterised everywhere. | High | All DB queries use parameterised inputs ($1, $2). Never string interpolation. Already pattern in codebase — verify in orchestrator. |
| SSRF via address → geocode | LOW — geocode calls fixed Planning Portal URL with address as query param. Not user-controllable URL. | Low | N/A |
| LLM prompt injection via address | RISK — if address string contains "Ignore all previous instructions..." and is passed into LLM prompt, could manipulate output. | Medium | Address must be sanitised before inclusion in LLM prompt. Strip non-alphanumeric except standard address chars (comma, space, hyphen, slash). |
| API key theft via client-side exposure | RISK — if Claude API key is called from frontend, exposed in network tab. | High | LLM synthesis MUST be server-side only. Frontend calls our API, which calls Claude internally. Never expose Claude API key to client. |
| Bulk data dump via prospector | RISK — unrestricted queries could export entire cadastre dataset. | High | Max 500 results per query. Require minimum 2 filter criteria. Require authentication. Paid tier only for prospector. |
| PII in logs | RISK — intelligence brief contains address + lot details. If we log full requests, we're storing users' property research patterns. | Medium | Log: API key hash + address hash + timestamp + latency. Do NOT log full response bodies. Audit trail logs data sources consulted but not full output. |

---

## 7. Performance Mode

| Check | Issue found? | Severity | Mitigation |
|-------|-------------|----------|------------|
| N+1 queries in orchestrator | YES — if each of 15+ data sources is a separate DB query, that's 15 round trips. | Medium | Batch spatial queries: single ST_Contains query with UNION ALL for all overlay types. Batch DCP: single query with zone + precinct. Reduce to ~4-5 DB calls total. |
| Planning Portal in hot path | YES — geocode + layerintersect = 2 external API calls before any local data. ~1-3s latency each. | High | Cache geocode results per address (long TTL — addresses don't move). Cache layerintersect with 24h TTL (LEP changes are infrequent). Serve cached data instantly, background-refresh if stale. |
| Satellite pipeline latency (SAMGeo 15s, pre_da_history 30s) | YES — full brief with all satellites takes 30-45s. Unacceptable UX for synchronous response. | High | Two-phase response: (1) return planning brief instantly (<3s), (2) satellite results stream in via SSE or polling. Frontend shows planning data immediately, satellite sections show "computing..." then populate. |
| LLM API latency (~2-5s for Claude) | Medium — adds latency on top of data assembly. | Medium | Optional: return structured JSON immediately, LLM narrative as separate async call. User can read structured data while narrative generates. Or: stream LLM response. |
| Batch: 50 addresses × 4 DB calls each = 200 queries | HIGH — batch endpoint must not hammer DB. | High | Connection pooling (pgBouncer). Batch spatial queries: one query with array of points, not 50 separate queries. Limit concurrent batch processing to 8 briefs at a time. |
| Pre-computation: 2M lots × ST_Contains against spatial_overlays | HIGH — could take hours if not batched properly. | Medium | Use spatial index (GIST). Batch in 10K-lot chunks. Parallelize across LGAs. Estimated: ~1 hour total with proper indexing. |

---

## 8. Dependency-Failure Mode — Per External Source

| External Source | What if DOWN? | What if SLOW (>10s)? | What if WRONG DATA? | Timeout | Fallback |
|---|---|---|---|---|---|
| **Planning Portal geocode** | Brief cannot proceed — need coordinates | Brief delayed — user sees spinner >10s | Wrong coordinates → wrong lot (see adversarial #5) | 8s | Return error: "Address resolution failed. Try Lot/DP lookup." |
| **Planning Portal layerintersect** | Zone/height/FSR unavailable | Brief delayed | Zone recently changed, API lags (see adversarial #1) | 8s | Serve from pre-computed cache if available. Flag: "Planning Portal unavailable — data may be up to 24h old." |
| **NSW Cadastre API** | Lot geometry unavailable — no corner lot detection, no frontage/depth | Brief degraded (no dimensions) | Geometry slightly off (surveying precision) | 8s | Serve brief without dimensions. Flag "lot geometry unavailable." |
| **RFS Bushfire API** | Bushfire section blank | Brief degraded | Map data outdated (infrequent updates) | 5s | Return "bushfire data temporarily unavailable" |
| **ePlanning DA API** | Neighbourhood section blank | Brief degraded | API lag (new DAs take 1-7 days to appear) | 8s | "Nearby DA data temporarily unavailable" |
| **DEA WOfS (flood)** | WOfS frequency unavailable | Brief degraded (flood section thinner) | Band index wrong (fixed bug — verify on change) | 10s | Fall back to EPI + JRC only. Flag missing source. |
| **Microsoft Planetary Computer (SAR)** | SAR flood detection unavailable | SAR section fails | Sentinel-1B gap (documented) | 15s | Flag "SAR data unavailable for requested period" |
| **Claude API (LLM synthesis)** | No narrative generated | Narrative delayed | Hallucination (see adversarial #6) | 30s | Return structured JSON only. "Narrative generation temporarily unavailable." |
| **NSW SIX Maps imagery (SAMGeo)** | Structure detection fails | Detection slow | Imagery outdated (12-24 months typical) | 20s | "Structure detection unavailable. Verify with site visit." |
| **BoM/WaterNSW gauges** | Gauge history unavailable | Brief degraded | Gauge data lag (hours to days) | 5s | Omit gauge section. Other flood sources still work. |

**Architecture principle:** Every external call has explicit timeout. Every failure degrades gracefully to a thinner brief, never a full error. The brief ALWAYS returns — it just has more "not_available" fields when sources fail.

---

## 9. Recovery Mode

| Failure | User impact | Recovery path |
|---|---|---|
| Payment succeeds but brief generation fails | User charged but no data | Store payment intent. Retry brief generation. If still fails within 5 min: refund automatically. Notify user: "Your brief is being regenerated. If not received within 10 minutes, you will be refunded." |
| Batch partially completes (40/50) then system crashes | User has incomplete batch | Persist per-address results as they complete. Resume failed batch from last completed address. Never re-process already-completed addresses. |
| Pre-computation job dies mid-run (1.5M of 3.35M lots processed) | Pre-computed data incomplete for some LGAs | Idempotent: track last processed lotidstring. Resume from checkpoint. Real-time fallback for lots not yet pre-computed. |
| LLM generates harmful output (despite constraints) | User sees misleading narrative | Post-processing assertion layer: check every claim maps to data. If assertion fails: serve structured data only, log for review. Never serve unverified LLM output. |
| DCP data found to be incorrect post-launch | Users received wrong setback values | Incident response: identify affected addresses, notify affected users (if account-based), correct data, re-generate cached briefs. DCP extraction has `last_verified_at` — flag stale extractions for re-verification. |

---

## 10. Observability Mode

| Check | Required? | Implementation |
|-------|-----------|---------------|
| Per-brief structured log | YES | Log: request_id, address_hash, api_key_hash, latency_ms, sources_queried, sources_failed, confidence_summary, cached_hit, timestamp. NOT: full address, full response, user identity. |
| Per-pipeline latency tracking | YES | Each pipeline call timed separately. Aggregate: P50/P95/P99 latency per pipeline. Alert if any pipeline P95 > 2× baseline. |
| Upstream API health tracking | YES | Track success/failure rate per external API over rolling 5-min window. If failure rate > 20%: alert. If > 50%: circuit-break (serve cached/degraded). |
| LLM cost tracking | YES | Log token count (input + output) per brief. Daily cost rollup. Alert if daily cost exceeds budget. |
| User-facing error clarity | YES | Every "not_available" field in the response must have a `reason` sub-field: "Planning Portal timeout", "DCP not yet extracted for this council", "Satellite pipeline failed — retry later". |
| Conversion funnel tracking | YES | Events: address_entered → brief_requested → brief_returned → satellite_requested → payment_started → payment_completed → PDF_downloaded. Each event with latency since previous. |

---

## 11. Spatial Mode (GIS-specific)

| Check | Issue found? | Severity | Mitigation |
|-------|-------------|----------|------------|
| CRS mismatch between sources | YES — Planning Portal returns EPSG:4326. Cadastre FeatureServer returns EPSG:3857. PostGIS stores in 4326. SAMGeo imagery tiles in Web Mercator. | High | All geometry converted to EPSG:4326 on ingest. Orchestrator operates exclusively in 4326. Conversions documented per ingest script. |
| lat/lng order | YES — PostGIS: ST_MakePoint(lng, lat). GeoJSON: [lng, lat]. Python convention: (lat, lng). Frontend Leaflet: (lat, lng). | High | Define canonical order in orchestrator: all internal functions use named parameters `lat=`, `lng=` (never positional). All PostGIS queries use ST_MakePoint($lng, $lat) explicitly named. |
| Point outside raster extent | YES — NARCliM rasters cover NSW only. Address in ACT (cross-border) → NoData or exception. DEA WOfS doesn't cover urban areas well. | Medium | Check extent before query. If outside: return None with reason "outside coverage area". Never serve NoData value as data. |
| Lot boundary precision | MODERATE — Cadastre polygon precision varies. Some lots have 1m accuracy, some have 10m. Corner lot detection uses boundary angles — imprecise geometry may give false positives. | Low | Document accuracy limitation. Corner lot detection uses threshold (angle > 160° AND two road frontages) — tolerant of minor imprecision. |
| Multi-polygon lots (irregular shapes, battle-axe) | YES — battle-axe lots have narrow handle + wide area. Centroid of battle-axe may be in the handle (not the developable area). Point-based spatial queries using centroid may miss overlays that apply to the buildable portion. | Medium | For battle-axe lots: use the widest polygon part centroid, not the whole-lot centroid. Detection: lot has any edge < 4m width (existing logic in lot-shape-analysis.ts). |
| Spatial overlay accuracy | YES — some spatial_overlays layers have coarse geometry (council-uploaded, not surveyed). A "heritage conservation area" boundary may be 5-10m imprecise. Lot right on boundary: is it in or out? | Medium | If lot centroid is within 20m of overlay boundary: flag as "near boundary — verify with council." Never serve a definitive yes/no for boundary cases. |

---

## 12. Implementation Breakdown — Risk-Ordered

> **SUPERSEDED:** This section was the initial risk-ordered phasing derived from the QA analysis. It has been absorbed into and replaced by `ce-intelligence-brief-implementation-procedure.md` (the AUTHORITY build plan), which incorporates these phases plus: 12 corrections from draft review, 3 silent failure fixes (LGA boundary validation, zone dev_type advisory, shadow temporal gap), four-layer legal defence architecture with Australian case law analysis, updated liability matrix, and per-stage verification gates. **Do not implement from this section — use the implementation procedure doc.**

Based on the above analysis, the implementation must be sequenced by **risk reduction**, not feature completeness. Build the safeguards FIRST, then the features on top.

### Phase 0: Safeguards & Schema (Week 1, Days 1-3)

These are boring but non-negotiable. Without them, every subsequent phase has latent correctness issues.

```
0.1 Response schema (Pydantic models)
    - IntelligenceBriefResponse with EVERY field typed + Optional[] where nullable
    - Per-field ConfidenceLevel enum: authoritative | extracted | estimated | not_available
    - Per-field DataCurrency: { source: str, last_updated: datetime, is_stale: bool }
    - CompoundConstraint model: { type, description, affected_fields, data_sources, caveat }
    - Explicit distinction: null (not queried) vs [] (queried, no results) vs None (query failed)
    → Test: serialisation round-trip, null handling, date formatting

0.2 Address resolution + validation
    - resolve_address() wrapper that:
      a) Normalises input (strip, title case, expand abbreviations)
      b) Calls Planning Portal geocode
      c) Validates: returned address matches input (fuzzy match > 0.8)
      d) Validates: coordinates are inside NSW bounding box
      e) Returns: { lat, lng, prop_id, resolved_address, match_confidence }
    - If match_confidence < 0.8: return warning, don't proceed blindly
    → Test: known addresses resolve correctly. Typos return low confidence. Interstate addresses rejected.

0.3 Strata gate
    - detect_strata() runs FIRST
    - If strata: completely different brief template (renovation scope, not development scope)
    - If strata + user asked about development: explicit message explaining why
    → Test: known strata lot returns strata-scoped brief. Non-strata lot returns full brief.

0.4 Per-pipeline timeout + error isolation
    - Each data source call wrapped in:
      try/except with explicit timeout (source-specific)
      On failure: return { field: None, confidence: "not_available", reason: str }
      On timeout: same, with reason: "source timeout"
    - Orchestrator assembles partial results — NEVER raises on single-source failure
    → Test: mock each source to timeout → brief still returns with appropriate gaps.

0.5 Rate limiter
    - Per-source rate limiter (Planning Portal: 2/s, ePlanning: 5/s, RFS: 5/s)
    - Per-user rate limiter (free tier: 5/day, paid: 100/day)
    - Batch endpoint: paid-only, max 50 addresses, 8 concurrent processing
    → Test: 10 rapid requests → rate limited gracefully, not crashed.
```

### Phase 1: Orchestrator Core (Week 1, Days 3-5)

```
1.1 Parallel fan-out to Layer A sources
    - asyncio.gather (or ThreadPoolExecutor) for all planning data queries
    - Sources: Planning Portal, PostGIS overlays, DCP controls, SEPP eligibility, VG valuation, ePlanning DA
    - Each in its own timeout wrapper (from 0.4)
    - Results assembled into IntelligenceBriefResponse
    → Test: 50 Inner West addresses. Verify all fields populated. Compare against existing /api/property endpoint for consistency.

1.2 Compound constraint detection
    - Input: assembled Layer A data
    - Rules (deterministic, testable):
      - heritage_hca AND bushfire_prone → flag (with caveat: "conflict applies if vegetation contributes to heritage character")
      - heritage_item AND flood_planning_area → flag (with caveat: "floor level mitigation may require Heritage NSW concurrence")
      - tod_precinct AND heritage_hca → flag ("density bonus may be restricted by heritage character provisions")
      - zone_residential AND (lot_area < min_lot_size * 1.1) → flag ("lot area is marginal for zone — verify with survey")
    - Each rule must have a `applies_when` predicate (not just A AND B — also check it's relevant)
    - Each rule must have a `caveat` (what the user should verify)
    → Test: fixture data with known compound constraints. False positive rate checked on 50 Inner West addresses.

1.3 Confidence assignment
    - Rules per source:
      - Planning Portal direct response → authoritative
      - PostGIS spatial_overlays → authoritative (ingested from gov source, but check ingest_date)
      - DCP controls from dcp_setback_controls → extracted (manual process, verified but not live)
      - Computed fields (headroom, feasibility) → derived (depends on input confidence)
    - Staleness check: if any source's data is older than configured threshold, downgrade to "stale"
      - Planning Portal cache > 7 days → stale
      - Spatial overlays ingest > 90 days → flag
      - DCP controls last_verified_at > 180 days → flag
    → Test: fixture with stale dates → confidence correctly downgraded.

1.4 Response assembly + gap disclosure
    - Gaps section: every field that's None or not_available, with reason
    - Explicit: "DCP setback controls not yet extracted for [council]. Refer to [DCP name] (PDF link)."
    - Summary: "This brief covers X of Y possible data fields. Major gaps: [list]."
    → Test: LGA with no DCP data → gaps section correctly populated. Inner West (deep) → gaps section nearly empty.
```

### Phase 2: Satellite Integration (Week 2)

```
2.1 Satellite pipeline wiring (optional, paid tier)
    - Wrap each satellite pipeline call: shadow, flood, bushfire, climate_risk
    - Each has its own timeout (shadow: 10s, flood: 15s, bushfire: 5s, climate: 5s)
    - Granny flat and pre_da_history: separate "deep analysis" tier (longer timeout: 30s, 45s)
    - Results merged into brief under physical_reality / environmental sections
    → Test: paid user → satellite fields populated. Free user → satellite fields null. One pipeline failure → others still returned.

2.2 Cache layer
    - Redis or in-memory cache per pipeline per address
    - TTL by source: Planning Portal 24h, satellite results 7d, pre-computed data until invalidation
    - Cache key: normalised_address + pipeline_name + date
    - Cache invalidation: when underlying data source is re-ingested
    → Test: second request for same address → cache hit, <100ms response.

2.3 Two-phase response architecture
    - Phase 1 response: planning data only (fast, <3s)
    - Phase 2: satellite results streamed via SSE or returned on poll
    - Frontend: shows planning brief immediately, satellite sections show "computing..." then populate
    - API contract: { status: "partial" | "complete", planning: {...}, satellite: null | {...} }
    → Test: client receives partial response immediately, then complete response within 30s.
```

### Phase 3: LLM Synthesis (Week 2-3)

```
3.1 Prompt design
    - System prompt: "You are a property data reporter. You present factual data only. You never recommend, predict, or advise."
    - Template: 6 sections with explicit field references
    - Every sentence must cite a specific field from the input JSON
    - Prohibited patterns: "you should", "we recommend", "it is likely", "this property is safe/suitable/compliant"
    - Required: if DCP data unavailable, first sentence of planning section must state this
    - Required: disclaimer appended programmatically (not LLM-generated, can't be hallucinated away)
    → Test: golden set of 20 input JSONs. Assertions: no prohibited language, all claims traceable, sections present.

3.2 Post-processing validation
    - Parse LLM output
    - For each factual claim: verify it exists in the input JSON
    - If unmapped claim detected: strip it, replace with "[data not available]"
    - Log stripped claims for prompt iteration
    - Count: if >2 claims stripped, regenerate with stricter prompt
    → Test: deliberately inject hallucination-prone input (address with "ignore all instructions" in it) → output clean.

3.3 Cost control
    - Estimate input tokens per brief (~2000-4000 tokens depending on satellite inclusion)
    - Estimate output tokens (~800-1500 per narrative)
    - Cost per brief: ~$0.02-0.05 (Sonnet) or ~$0.08-0.15 (Opus)
    - Use Sonnet for narrative generation (sufficient quality, 5× cheaper)
    - Daily cost cap: alert if daily spend > $20 (400-1000 briefs)
    - Free tier: NO LLM narrative. Structured data only.
    → Test: 50 briefs, measure actual token usage and cost.

3.4 Regression test suite
    - 20 fixture JSONs (Inner West addresses with known data)
    - Expected output assertions (not exact match — structural/content assertions):
      - All 6 sections present
      - No prohibited language (regex scan)
      - Heritage mentioned if heritage_hca=true
      - Flood mentioned if flood_epi=true
      - Gaps acknowledged if DCP not_available
      - Disclaimer present at end
    - Run before any prompt change merges
    → Pipeline: pytest, mock Claude API with fixture responses for unit tests. Live Claude API for integration tests (20 calls).
```

### Phase 4: Pre-Computation & Bulk (Week 3-4)

```
4.1 Cadastre ingest
    - scripts/ingest_cadastre_lots.py
    - Paginate FeatureServer/8 (2000/page)
    - PostGIS table with GIST spatial index
    - Transform EPSG:3857 → EPSG:4326 on ingest
    - Filter: urban only for v1 (urbanity='U')
    - Exclude strata sub-lots for prospector (hasstratum=0 OR stratumlevel=0)
    - Weekly incremental: WHERE modifieddate > last_sync
    → Test: count matches source. Spatial query returns known lots. Performance: random bbox query <100ms.

4.2 VG land values ingest
    - scripts/ingest_vg_values.py
    - Parse "$1,920,000" → integer on ingest (cents, avoid float)
    - Join on propid where possible, spatial fallback where not
    - Monthly refresh (corrections), annual full (new valuations)
    → Test: known address returns correct land value. Join with cadastre_lots works.

4.3 Pre-computed overlay flags
    - scripts/precompute_lot_overlays.py
    - For each lot centroid: batch ST_Contains query
    - Store: lot_overlay_flags (lotidstring FK, flood bool, heritage bool, bushfire bool, ...)
    - CRITICAL: these are for SEARCH/FILTER only. Never served as authoritative per-address response.
    - Staleness marker: precomputed_at timestamp. If > 90 days, flag for refresh.
    → Test: known heritage lot has heritage=true. Known flood lot has flood=true.

4.4 Prospector endpoint
    - POST /pipeline/prospector
    - Pure PostGIS query on pre-computed tables
    - Required: min 2 filter criteria
    - Max 500 results
    - Response: GeoJSON for map rendering + tabular summary
    - CRITICAL: results are CANDIDATES. Each candidate links to "Generate full brief" (which runs real-time verification).
    - Never claim a prospector result is heritage-free/flood-free based solely on pre-computed flag.
    → Test: known filter criteria return expected lots. Max 500 enforced. Empty criteria rejected.

4.5 Batch endpoint
    - POST /pipeline/intelligence-brief/batch
    - Paid tier only (auth check)
    - Max 50 addresses per batch
    - Queue-based: return batch_id immediately, process async
    - Per-address: same orchestrator as single brief
    - Progress: GET /pipeline/intelligence-brief/batch/:id
    - On completion: webhook to customer URL (if configured) + email
    - Failed addresses: explicit in response (never silently omit)
    → Test: 10-address batch completes. 2 failures → reported in failed array. Exceeding 50 → rejected.
```

### Phase 5: Data Source Expansion (Week 4-5)

```
5.1 School catchments
    - Source: data.nsw.gov.au GeoJSON
    - PostGIS table: school_catchments (school_name, school_type, icsea_score, level, geometry)
    - Ingest: download GeoJSON, load with ogr2ogr or Python
    - Query: lot centroid → ST_Contains → school_catchments → return matches
    - Nightly refresh (source updates nightly)
    → Test: Marrickville address → Marrickville Public + Marrickville High with ICSEA scores.

5.2 EPA contaminated land
    - Source: EPA register (monthly CSV export or scrape)
    - PostGIS table: epa_contaminated_sites (site_name, address, classification, status, geometry)
    - Geocode addresses that don't have coordinates (batch geocoding)
    - Query: proximity (lots within 500m of listed site)
    - Monthly refresh
    - CRITICAL: distinguish "site IS contaminated" vs "site is NEAR contaminated site"
    → Test: known contaminated address → flagged. Address 400m away → flagged with distance. Address 600m away → not flagged.

5.3 ABS construction cost proxy
    - Static lookup table: building_type × region → $/m² (from ABS PPI 6427.0)
    - Updated quarterly (manual — check ABS release calendar)
    - Integration: FSR × lot area × $/m² → rough total construction cost
    - MUST caveat: "Rough estimate based on ABS Producer Price Index. Not a quantity surveyor assessment."
    → Test: known FSR + lot → reasonable cost range.

5.4 Easement layer
    - Source: NSW Cadastre FeatureServer Layer 9
    - PostGIS table: lot_easements (easement_id, easement_type, width_m, beneficiary, geometry)
    - Query: spatial intersection with lot polygon
    - CRITICAL for granny flat: easement through rear yard = reduced buildable area
    - Integrate into granny_flat.py: subtract easement area from residual
    → Test: known easement lot → easement returned with type + width.

5.5 Domain API (if free tier viable)
    - Sign up, test free tier capabilities
    - If listings available: query by address → listed (bool), asking_price, days_on_market
    - If not available on free tier: defer to paid tier decision later
    - NEVER display asking price without "as listed on Domain — not a valuation" caveat
    → Test: known listed property → returns listing data. Unlisted → null (not error).
```

### Phase 6: Production Hardening (Week 5-6)

```
6.1 Auth + billing
    - API key generation (Supabase auth or custom)
    - Stripe subscription tiers: Free (5 briefs/day), Pro ($149/mo, 100/day), Enterprise (custom)
    - Satellite data: Pro+ only
    - LLM narrative: Pro+ only
    - Batch/Prospector: Pro+ only
    → Test: free tier user → satellite fields null. Pro user → full brief. Rate limit enforced.

6.2 Monitoring + alerting
    - Per-pipeline latency (P50/P95/P99)
    - Upstream API health (success rate per 5-min window)
    - LLM cost per day
    - Brief generation success rate
    - Cache hit rate
    - Alert thresholds: P95 latency > 10s, upstream failure > 20%, daily LLM cost > $30
    → Test: simulate upstream failure → alert fires. Simulate cost spike → alert fires.

6.3 Audit trail
    - Extend existing audit_trail.py
    - Per brief: request_id, timestamp, address_hash, sources_queried, sources_failed, confidence_summary, latency_breakdown
    - NOT logged: full address, full response body, user identity (privacy)
    - Retained: 90 days (sufficient for incident investigation)
    → Test: brief generation → audit trail entry created with correct fields.

6.4 Legal/disclaimer framework
    - Per-response programmatic disclaimer (not LLM-generated)
    - Terms of service: "Information only, not planning/legal/financial advice"
    - Per-field confidence rendering in frontend (green/amber/grey)
    - Data currency shown for each source ("Planning Portal data as at: [date]")
    → Test: every brief response contains disclaimer. Frontend renders confidence badges.
```

---

## 13. Key Architectural Decisions (From This Analysis)

| Decision | Rationale | Risk if violated |
|---|---|---|
| Pre-computed data is for SEARCH ONLY, never served as authoritative per-address | Pre-computed flags can be stale. Per-address brief must always hit live data. | User buys property based on stale pre-computed data (Critical) |
| Every external call has explicit timeout and graceful degradation | Any upstream failure must produce a thinner brief, never a crash | User sees 500 error, loses trust, doesn't retry (High) |
| LLM output is VALIDATED before serving | Hallucinations in a property context = liability | User acts on false constraint or false "no constraint" (Critical) |
| Strata lots get a completely different brief template | Strata lot with parent title area passes all thresholds but is NOT a development site | Misleading development potential output for apartments (Critical) |
| Free tier sees no satellite data, no LLM narrative, no raw DCP values | Protects compute costs + protects DCP extraction IP from scraping | Cost spiral on free tier / competitor extracts our data (High) |
| Batch/Prospector results are CANDIDATES, not authoritative | Pre-computed flags are for filtering speed. Each result must link to real-time verification. | User trusts prospector result without verifying → buys flood-prone lot (High) |
| Address resolution discrepancies are surfaced, not hidden | If geocode confidence < 0.8, warn user. Don't serve data for the wrong lot. | Entire brief is for wrong property (Critical) |

---

## 14. What Could Go Wrong — Top 5 Catastrophic Scenarios

| # | Scenario | Likelihood | Impact | Prevention |
|---|----------|-----------|--------|-----------|
| 1 | Brief says "not flood prone" for a lot that IS flood prone (due to stale overlay data or geocode offset) → user buys → floods | Low-Medium | Extreme (financial loss + reputational destruction) | ALWAYS query live spatial_overlays (not pre-computed). Cross-check EPI + JRC + WOfS. If ANY source indicates flood: flag it. Bias toward over-warning. |
| 2 | Brief says "granny flat eligible" for a lot that isn't (heritage exclusion from CDC, or lot is strata) → user buys for GF potential → denied | Medium | High (user overpaid for property based on false potential) | Strata gate (0.3). Heritage + CDC exclusion check. NEVER say "eligible" — say "meets SEPP Housing minimum thresholds (450m², R2 zone). Complying development pathway subject to additional exclusion conditions — verify with certifier." |
| 3 | LLM narrative confidently states a constraint that doesn't exist in the data → user unnecessarily abandons purchase or pays for unneeded consultant | Medium | Medium (financial waste, trust loss) | Post-processing validation (3.2). Strip unmapped claims. Log for review. |
| 4 | Competitor systematically scrapes the paid endpoint to extract DCP data → replicates our moat for free | Low | Extreme (business-ending moat loss) | Rate limiting. Account verification. Don't expose raw structured DCP values on any free or cheaply-accessible tier. Monitor for systematic access patterns. |
| 5 | Planning Portal API changes response format without notice → all briefs return wrong or missing data for days before anyone notices | Low | High (many users affected with wrong data) | Response schema validation on every Portal response. If fields missing or types changed → alert immediately. Serve cached data with "source temporarily unavailable" rather than serving malformed data. |

---

## 15. Summary: What This Analysis Changes About the Build Plan

| Original plan assumption | Issue found | Revised approach |
|---|---|---|
| Pre-computed data speeds up everything | Stale pre-computed data served as authoritative = catastrophic | Pre-computed for search/filter ONLY. Brief always hits live sources. |
| Parallel fan-out to all sources | Rate limiting + concurrent API calls can 429 | Shared rate limiter per source. Max concurrency per external API. |
| LLM synthesis adds value | LLM can hallucinate constraints or miss gaps | Post-processing validation mandatory. Free tier gets NO LLM. |
| Compound constraints are additive value | Generic rules without spatial context = false positives | Each rule needs `applies_when` predicate + `caveat`. Over-flag with "verify" language. |
| Schema is straightforward | null vs [] vs missing have different semantics | Explicit schema with Optional[] typing and distinct meanings documented. |
| Geocode is reliable | 50m offset = wrong lot = wrong brief | Match confidence check. Lot polygon containment verification. Warning on low confidence. |
| Strata lots are edge cases | Strata lot passing 450m² threshold = completely wrong brief | Strata gate runs FIRST. Different template for strata lots. |
| Batch is just "loop over single" | 50 × 6 API calls = rate limit hell + partial failures need handling | Concurrency limit. Checkpoint-based resumption. Explicit failure reporting. |
