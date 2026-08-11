# "What Can I Build On This Lot" — Intelligence Brief Product Plan

**Date:** 2026-05-24
**Status:** Scoping complete, ready for build decision
**Trigger:** Inner West Nest meeting (Hamada, week of 2026-05-26) + LLM layer prioritisation
**Depends on:** ce-llm-intelligence-layer-strategy.md, ce-killer-llm-data-services.md, ce-lot-inventory-and-api-pricing-research.md, project-value-exploitation-audit-decisions.md

---

## 1. What This Product Actually Is

Not a chatbot. Not a search engine over DCP PDFs. A **per-address intelligence brief** that assembles every data layer PlotDetect has into a single structured document, optionally narrated by LLM.

The product answers: "For this specific lot, what do the planning rules allow, what physical reality constrains it, what environmental risks exist, what's happening in the neighbourhood, and what don't we know?"

No conclusions. No recommendations. Every statement cites a data source. Every gap is disclosed.

### Why This Is Different From PropCode/PlanningAI

| Dimension | PropCode (RAG) | Archistar | PlotDetect Intelligence Brief |
|---|---|---|---|
| Data source | PDF text of DCPs | Planning rules + 3D massing | Structured DB + satellite + spatial + DA history |
| Question answered | "What does the DCP say about X?" | "What envelope fits on this lot?" | "Everything relevant to this lot, across all sources" |
| Satellite evidence | None | Nearmap imagery (visual only) | SAR flood, shadow geometry, structure detection, NDVI change, climate projection |
| Environmental risk | None | None | 6-hazard climate score, flood truth (6 sources), bushfire BAL, compound constraints |
| Neighbourhood context | None | None | DA activity within 200m, shadow from allowable envelope, densification velocity |
| Physical reality | None | None | Structure detection (SAMGeo), residual buildable area, existing DA/CDC cross-reference |
| Confidence signals | Implicit | Implicit | Per-field (authoritative / extracted / not available / verify with council) |
| Failure mode | Hallucinated numbers, missed cross-refs | No environmental context | Disclosed gaps — can't hallucinate structured data |

**The moat is not any single layer — it's that 15+ data layers are assembled per-address in one system.** A competitor replicating one pipeline (e.g., flood) still lacks the other 14.

---

## 2. The Full Data Stack Per Address (What Exists Today)

### Layer A — Planning Controls (deterministic, authoritative)

| Data Point | Source | Coverage | Confidence |
|---|---|---|---|
| Zone + permissibility matrix | Planning Portal API + lep_land_use_table | All NSW | High (live API) |
| Height limit | Planning Portal layerintersect | All NSW | High |
| FSR | Planning Portal layerintersect | All NSW | High |
| Minimum lot size | Planning Portal layerintersect | All NSW | High |
| DCP setbacks (front/rear/side) | dcp_setback_controls (extracted) | 29 LGAs, 16 control types | Medium-High (extracted, QA'd) |
| DCP parking, landscaping, deep soil, site coverage, tree canopy, solar access, privacy, fencing, bicycle parking, communal OS, dwelling size, separation | dcp_setback_controls | Varies by LGA/type (999 rows) | Medium-High |
| Precinct-specific overrides | v2_precinct_id (102 precincts) | Inner West deep, others partial | Medium |
| SEPP Housing standards | housing_sepp_standards (33 rows) | All NSW (zone-gated) | High |
| Heritage items + HCA | Planning Portal + PostGIS spatial_overlays | All NSW | High |
| TOD/accelerated TOD | Planning Portal layerintersect | All NSW | High |
| Lot dimensions (frontage, depth, area) | NSW Cadastre API | All NSW | High |
| Corner lot detection | lot-shape-analysis.ts | All NSW (geometry-derived) | High |

### Layer B — Satellite / Remote Sensing (physical evidence)

| Data Point | Pipeline | Coverage | Confidence |
|---|---|---|---|
| Shadow impact at ADG hours (Jun/Mar/Sep/Dec solstice/equinox) | shadow_detector.py (pybdshadow) | Any address | Medium (geometric model, not 3D scan) |
| ADG solar access compliance | shadow_detector.py | Any address | Medium |
| Shadow from neighbour's allowable envelope | shadow_model.py + LEP height limits | Any address with height data | Medium |
| Flood truth (6-source fusion) | flood_truth.py (EPI + EMS + JRC + DEA WOfS + BoM gauge + S-1 SAR) | ~71 LGAs EPI, JRC/WOfS all NSW | Medium-High (multi-source convergence) |
| Multi-AEP flood tiers | flood_truth.py (Campbelltown 7-tier, Hawkesbury) | ~12 LGAs | High (council flood study data) |
| Ground elevation (AHD) | NSW 5m DEM via SIX Maps | All NSW | High |
| Bushfire BAL pre-screen | bushfire_prescreen.py (RFS BFPL live API) | All NSW | Medium (estimated, not certified BAL) |
| 10/50 clearing + RFS referral triggers | bushfire_prescreen.py | All NSW bushfire prone | High (statutory rules) |
| CDC pathway availability (bushfire context) | bushfire_prescreen.py | All NSW bushfire prone | High |
| Structure detection (main dwelling + outbuildings) | granny_flat.py (SAMGeo + NSW SIX 10cm) | Any address | Medium (70-80% clean lots, lower for complex) |
| Residual buildable area | granny_flat.py | Any address | Medium (depends on detection accuracy) |
| ePlanning DA/CDC cross-reference | granny_flat.py + threat_radar.py | All NSW (post-2012) | Medium (Determined ≠ approved) |
| Site change timeline 2017-2025 | pre_da_history.py (Tessera + S-2 NDVI/NDBI + Wayback) | Any address | Medium (requires interpretation) |
| Unauthorised works signal | pre_da_history.py cross-ref with ePlanning | Any address | Low-Medium (indicative only) |
| Nearby DA activity (200m radius) | threat_radar.py (ePlanning API) | All NSW | High (live API) |
| Climate risk score (6-hazard composite) | climate_risk_score.py + climate_risk_raster.py | All NSW | Medium (equal-weight model, documented limitations) |
| NARCliM climate projections (heat, precipitation) | climate_risk_raster.py (AdaptNSW 4km) | All NSW | Medium (single GCM) |
| Construction change detection (SAR coherence) | drawdown_verify.py | Any address | Low-Medium (79% baseline, needs validation) |
| Solar yield estimate | solar_yield.py (Google Solar API pass-through — neither pvlib nor PVGIS is used; corrected 2026-08-06) | Any address | Medium (Google's model, not measured generation) |

### Layer C — Valuation / Economics (context)

| Data Point | Source | Coverage | Confidence |
|---|---|---|---|
| Unimproved land value (current + 5yr history) | NSW VG API (already integrated) | All NSW | High (statutory valuation) |
| Lot area (plan-registered) | NSW Cadastre FeatureServer | All NSW | High |
| Strata detection | Cadastre lot attributes | All NSW | High |
| Rental yield by postcode | NSW Fair Trading bond data | All NSW | Medium (postcode average, not address-specific) |
| Development headroom (available height/FSR) | Computed from LEP controls | All NSW | High |
| Feasibility score | Computed from permissibility × constraints | All NSW | Medium (simplified model) |

### Layer D — Currently Not Integrated But Available Free

| Data Point | Source | Cost | Effort to Integrate | Value for Buy Agents |
|---|---|---|---|---|
| School catchment zones | NSW Dept of Education GeoJSON (nightly) | $0 | 1-2 days (spatial join) | **Very high** — family buyers' #1 criterion |
| Transit accessibility | TfNSW GTFS (continuous) | $0 | 2-3 days (compute walking isochrones) | High — walkability score |
| EPA contaminated land | EPA register (monthly CSV) | $0 | 1-2 days (address match + spatial) | **Very high** — critical risk flag, insurability |
| ABS construction cost index | ABS PPI (quarterly) | $0 | 0.5 days (lookup table) | Medium — rough construction cost proxy |
| ABS dwelling commencements | ABS Building Activity (quarterly) | $0 | 0.5 days (LGA lookup) | Medium — market activity signal |
| Current listings (on market now) | Domain API free tier | $0 | 1-2 days (address match) | High — "is this lot for sale?" |
| NSW Heritage Inventory (detailed) | DCCEEW shapefile/WMS | $0 | 1 day (spatial overlay) | Medium — significance statements beyond "item" |
| Road classification | NSW Cadastre (functional hierarchy) | $0 | Already partially integrated | Low-Medium — arterial road noise flag |
| Air quality monitoring | DPIE API (free) | $0 | 1 day (nearest station) | Low — relevant for specific areas |
| NBN availability | NBN API | $0 | 0.5 days | Low — but buyers ask |

**Quick wins (< 1 week combined, outsized value):**
1. School catchments — 1-2 days, spatial join, massive value for family buyers
2. EPA contaminated land — 1-2 days, address/spatial match, critical risk flag
3. ABS PPI construction cost proxy — 0.5 days, enables rough feasibility numbers
4. Domain API free tier — 1-2 days, "is this lot currently listed for sale"

These four additions make the intelligence brief answer questions that no other tool assembles: contamination + school zone + estimated construction cost + listing status + everything we already have.

---

## 3. Bulk Data Scenarios

### 3a. Pre-Computed Intelligence (Inner West First)

**Concept:** Instead of computing per-address on demand, pre-compute Layer A + partial Layer C for every lot in target LGAs and store in PostGIS. Satellite layers (Layer B) remain on-demand (expensive to pre-compute for 78K lots).

| Scope | Lots | Pre-compute time | Storage |
|---|---|---|---|
| Inner West | 78,259 | ~2-3 hours (Planning Portal rate-limited) | ~200 MB |
| Greater Sydney (33 LGAs) | 1.38M | ~1-2 days | ~3.5 GB |
| All NSW (urban) | ~2M | ~2-3 days | ~5 GB |

**What pre-computation enables:**
- **Instant response** — no API latency on page load. Planning controls served from local DB.
- **Site Prospector** — "Show me all R2 lots >600m² in Marrickville with no heritage, no flood" → PostGIS query, <1 second, returns map + list.
- **Comparative analysis** — "How does this lot compare to others in the same zone?" becomes trivial.
- **Portfolio screening** — "Here are 20 addresses, rank them by development potential" → batch query, seconds.
- **Market intelligence** — aggregate statistics by zone/LGA/precinct that no one else publishes.

**What remains on-demand:**
- Satellite pipelines (shadow, flood SAR, structure detection, site history) — compute-intensive, per-address
- ePlanning DA cross-reference — live API, fresh data needed
- Climate risk scoring — fast enough to compute on-demand (~2s)

### 3b. Bulk Use Cases by Customer Type

**Buy agents (Hamada's use case):**
- Weekly auction list: "Run intelligence briefs on these 8 properties going to auction Saturday"
- Client shortlist: "My client wants R2 in Inner West, 500m²+, granny flat eligible, under $1.5M land value — show me lots"
- Due diligence package: "Full report on 42 Smith St — everything you have, PDF for my client"
- Monitoring: "Alert me when any new DA is lodged within 200m of my client's purchase at 15 Jones St"

**Developers (future):**
- Site acquisition: "All R3/R4 lots >1000m² in Canterbury-Bankstown with no heritage" → map + ranked list
- Feasibility screening: "For each of these 50 lots, what's the max GFA, binding constraint, and estimated land value per m² of GFA?"
- Portfolio analysis: "I own 12 sites. Which ones have changed in regulatory status since I bought them?"

**Conveyancers (existing channel):**
- Pre-purchase due diligence: everything in the intelligence brief, formatted for solicitor review
- Risk flags: contamination + flood + heritage + unauthorised works signal → "3 items require further investigation"
- Batch processing: 10-20 settlements per week, each needs a report

**Institutional (future — AASB S2, insurers):**
- Portfolio risk scoring: "Score these 5,000 addresses for climate risk + regulatory constraint"
- Annual re-assessment: "What changed in the regulatory environment for our portfolio since last year?"
- Insurance repricing: "Flag all properties in our book where flood evidence contradicts EPI designation"

### 3c. Bulk API Architecture

```
POST /api/intelligence/brief          — single address, full brief
POST /api/intelligence/brief/batch    — list of addresses (max 50), queued processing
POST /api/intelligence/prospector     — filter query (zone + lot size + constraints), returns matching lots
GET  /api/intelligence/brief/:id      — retrieve completed brief by report ID
GET  /api/intelligence/batch/:id      — retrieve batch status + completed briefs

Webhook: POST to customer URL when batch/brief complete
```

**Rate model:**
- Single brief: $29-49 (consumer) / $15-25 (subscription)
- Batch (10-50): $12-20 per address (volume discount)
- Prospector query: $49-99/search or $499/mo unlimited
- Portfolio scoring (1000+): $5-10/address (institutional)

### 3d. Pre-Computation Pipeline (Foundation Layer)

This is the infrastructure that makes everything else fast:

```
Step 1: Ingest cadastre lots into PostGIS (32 min, $0)
        → cadastre_lots table: 3.35M lots with geometry, lotidstring, area, urbanity, strata

Step 2: Ingest VG land values into PostGIS (18 min, $0)
        → vg_land_values table: 2.18M records with propid, address, zone, 5yr values

Step 3: Spatial join lots ↔ spatial_overlays (batch, ~1 hour)
        → pre-computed overlay flags per lot (flood, heritage, bushfire, biodiversity, etc.)

Step 4: Spatial join lots ↔ dcp_precinct_boundaries (batch, ~10 min)
        → pre-computed precinct_id per lot

Step 5: Join lots ↔ DCP controls via zone + precinct (batch, ~5 min)
        → pre-computed applicable DCP controls per lot

Step 6: Compute SEPP Housing eligibility per lot (batch, ~30 min)
        → pre-computed: granny flat eligible, dual occ eligible, manor house eligible

Result: Every urban lot in NSW has pre-computed planning + overlay + DCP + eligibility flags.
        Prospector queries become pure PostGIS filters — sub-second for any criteria combination.
```

**Incremental maintenance:**
- Cadastre: weekly sync using `modifieddate` field (~100-500 changed lots/week)
- VG values: monthly refresh (corrections) + annual full refresh (new valuations)
- Spatial overlays: re-run affected lots when overlay layers update (quarterly)
- DCP controls: re-run affected lots when new controls extracted (manual trigger)

---

## 4. Additional Data Source Integrations — Prioritised

### Tier 1 — Integrate Now (< 1 week combined, $0, outsized value)

**School Catchments (NSW Dept of Education)**
- Source: data.nsw.gov.au GeoJSON, nightly updates, CC-BY
- Integration: spatial join lot point → catchment polygon → school name + type + ICSEA score
- Value: Family buyers' #1 decision criterion. Buy agents currently check this manually on findmyschool.nsw.gov.au. **No proptech tool includes this in a property report.**
- Output: "Lot is within catchment for Marrickville Public School (ICSEA 1105) and Marrickville High School (ICSEA 1032)"
- Maintenance: automated nightly sync, zero ongoing effort

**EPA Contaminated Land Register**
- Source: Monthly CSV export from EPA, or scrape searchable register
- Integration: address/lot match + spatial proximity (lots within 500m of listed site)
- Value: **Critical risk flag for any property purchase.** Contamination = insurance refusal, mortgage issues, remediation costs. Buy agents currently check this manually.
- Output: "No contaminated site at this address. 1 listed site within 500m: former service station at 88 Illawarra Rd (Class 2 — investigation required before development)"
- Maintenance: monthly CSV refresh, automated

**ABS Construction Cost Proxy (PPI)**
- Source: ABS 6427.0 Producer Price Indexes, quarterly, free API
- Integration: lookup table: building type × Sydney region → $/m² estimate
- Value: Enables rough feasibility calculation without Rawlinsons or QS. "3-unit townhouse × 210m² × $3,200/m² ≈ $672K construction cost. Land value $850K. Estimated GDV at comparable sale rates..."
- Maintenance: quarterly manual update of lookup table (~15 min)

**Domain API Free Tier (Listings)**
- Source: developer.domain.com.au, free signup
- Integration: address → listing status, asking price, days on market
- Value: "Is this lot currently listed for sale?" transforms the intelligence brief from research to action. For prospector: filter to "matching lots that are actually for sale right now."
- Maintenance: API calls at query time, no data storage needed

### Tier 2 — Integrate Next (1-2 weeks, $0, valuable)

**TfNSW GTFS (Transit Accessibility)**
- Source: opendata.transport.nsw.gov.au, GTFS static + realtime, free
- Integration: compute walking distance to nearest bus/train/ferry stop. Compute service frequency score.
- Value: Walk score / transit score. Correlates with property value. Useful for TOD analysis.
- Output: "Nearest train: Marrickville station (450m walk, 12 min frequency). Nearest bus: route 423 (200m, 8 min frequency). Transit score: 78/100."
- Maintenance: GTFS updates continuously, re-sync monthly

**NSW Heritage Inventory (Detailed Significance)**
- Source: DCCEEW shapefile + WMS, as updated
- Integration: spatial overlay → significance statement, listing date, curtilage
- Value: Current system says "heritage item I123." Inventory adds: "Marrickville Town Hall, state heritage significance, 1880, includes curtilage extending to lot boundary. Development within curtilage requires Heritage NSW concurrence."
- Maintenance: annual re-sync

**Easement Layer (NSW Cadastre)**
- Source: NSW Cadastre FeatureServer Layer 9 (easements), free, CC-BY
- Integration: spatial intersection with lot → easement type + width
- Value: Easements restrict buildable area. A 3m sewer easement through the rear of a lot = no granny flat placement there. Currently invisible to the system.
- Output: "1 easement affecting lot: 2.44m wide sewer easement along rear boundary (Sydney Water)"
- Maintenance: syncs with cadastre refresh (weekly)

### Tier 3 — Integrate When Revenue Justifies ($0 but more effort)

**BioNet (Threatened Species)**
- Source: DCCEEW BioNet Atlas API, free for non-commercial research (check terms for SaaS)
- Integration: species records within 500m of lot, triggers for BDAR thresholds
- Value: Biodiversity is a development blocker that surprises buyers. "2 threatened species recorded within 500m: Powerful Owl, Grey-headed Flying Fox. BDAR may be required if clearing exceeds 0.25ha."

**Historical Aerial Imagery Timeline**
- Source: NSW SIX Maps historical imagery (varies by year, free tiles)
- Integration: pre_da_history.py already uses Wayback + Tessera. Extend with NSW historical aerials for pre-2017 comparison.
- Value: Deeper site history — what was on this lot in 1990? Detects filled land, demolished structures, changed watercourses.

**Noise Mapping**
- Source: Some councils publish road traffic noise maps. TfNSW publishes rail noise contours.
- Integration: spatial overlay
- Value: Noise affects property value and livability. "Lot is within 40m of classified road (New Canterbury Rd, >40,000 AADT). DCP requires noise attenuation for new dwellings."

### Tier 4 — Paid Data (Post-Revenue)

| Source | Cost | What It Adds | When |
|---|---|---|---|
| Value NSW PSI commercial license | Unknown (call first) | Comparable sales → residual land value calculation | After first revenue |
| PropTrack API | Unknown | AVM (current estimated value for any property) | After first revenue |
| Domain paid tier | Unknown | Price estimates, enriched property data | After first revenue |
| CoreLogic | $50-100K+/yr | Full sales history, AVM, building attributes | Year 2+ |
| Geoscape Buildings | Credits (~$0.12/address) | Precise building footprints + heights | If SAMGeo accuracy insufficient |

---

## 5. Creative / Imaginative Use Cases

### 5a. Compound Constraint Intelligence (unique to PlotDetect)

These insights ONLY emerge when multiple data layers are combined. No competitor can produce them because no competitor has all the layers:

**Heritage × Bushfire** — "Property is in Heritage Conservation Area AND bushfire prone. 10/50 vegetation clearing entitlement may conflict with heritage conservation requirements — vegetation contributing to heritage character cannot be cleared under 10/50. Consult Heritage NSW and RFS."

**Flood × Heritage** — "Property is flood affected (1% AEP) AND heritage listed. Flood mitigation (raising floor level) may require Heritage NSW concurrence. Standard flood-compatible design modifications may not be permissible."

**Shadow from Allowable Envelope × Solar Access** — "If the R3 zoned lot to the north is developed to its maximum 11.5m height limit, this property loses approximately 2.1 hours of winter solar access to the rear yard (Jun 21 midday shadow extends 17.4m south). DCP requires minimum 3 hours solar to living areas — potential compliance issue for future development on this lot."

**Structure Detection × DA Records × Timeline** — "AI detected a ~65m² structure in the rear yard (Pre-DA Site History shows it appeared between 2019 and 2021 imagery). No matching development application found in ePlanning records for this period. This may indicate an unapproved structure — verify with council s10.7(5) certificate."

**Densification Velocity × Shadow Impact** — "14 DAs lodged within 400m in last 24 months (8 for multi-dwelling housing). Suburb is densifying. Shadow analysis shows that if 3 nearest R3 lots are developed to height limit, cumulative shadow impact reduces winter solar access to this property by ~40%."

**Flood Evidence vs Statutory Designation** — "Property is NOT in flood planning area (EPI clear). However: JRC 40-year water occurrence shows 3.2% frequency at this location, and Sentinel-1 SAR detected surface water within 150m during March 2022 La Niña event. Ground elevation is only 1.8m above nearest modelled flood level. The statutory designation may understate actual flood exposure."

**TOD × DCP × Heritage** — "Property is in Transport Oriented Development precinct (650m from Dulwich Hill station) with bonus FSR of 0.8:1 (vs base 0.5:1). However, Heritage Conservation Area designation may prevent development to TOD bonus density — heritage character provisions typically override density uplift. Verify with council."

### 5b. Derived Products from the Intelligence Brief

Each of these is a repackaging of the same underlying data, not a new pipeline:

**"Buy or Skip" Risk Summary** — For buy agents. Top 3 risk flags + top 3 opportunities, one paragraph each. Not a recommendation — a structured risk/opportunity framework. "Risk 1: Heritage conservation area restricts complying development pathway — all external modifications require DA. Risk 2: Northern neighbour lot is underdeveloped R3 — shadow impact from future development. Opportunity 1: Lot exceeds 450m² SEPP Housing threshold — secondary dwelling eligible (subject to CDC exclusion check)."

**"Conveyancing Red Flags"** — For conveyancers/solicitors. Strips the brief to just risk items that require further investigation. "3 items flagged: (1) AI-detected structure with no matching DA/CDC record, (2) within 500m of EPA-listed contaminated site, (3) flood evidence from satellite exceeds statutory designation."

**"Development Potential Card"** — For developers. One-page summary: permitted dev types, max GFA from FSR, max height, binding constraint, estimated construction cost (ABS proxy), land value trend (VG 5yr), comparable DA approval rate. Designed for portfolio screening — scan 50 in 10 minutes.

**"Neighbourhood Intelligence Update"** — For existing homeowners (monitoring product). Monthly: new DAs within 200m, any overlay changes, land value change, new contaminated site listings. Subscription $9.99/month. Low compute (pre-computed base, incremental DA check).

### 5c. Imaginative Scope — Things Nobody Is Doing

**Pre-Purchase "What They Didn't Tell You" Report** — Cross-reference the real estate listing claims against data. Listing says "quiet street" → road classification shows arterial road. Listing says "flood-free" → SAR detected water within 100m. Listing says "development potential" → heritage HCA restricts CDC pathway. This is legal (factual data, no defamation) and enormously valuable for buyers who suspect agents are overselling.

**"Regulatory Arbitrage Finder"** — Where does the same building type face the least constraints? "Dual occupancy in R2: Inner West requires 8m rear setback, Canterbury-Bankstown requires 6m, Georges River requires 5m. For a 15m-wide lot, Georges River yields 15m² more GFA." Only possible with structured DCP data across 29 LGAs.

**"Shadow Reciprocity Map"** — For any lot, model both (a) shadow cast BY this lot's allowable envelope onto neighbours, and (b) shadow cast by neighbours' allowable envelopes onto this lot. The buyer sees their worst case; the developer sees their exposure to neighbour objections. Nobody does this.

**"Unauthorised Works Probability Score"** — Combine: (1) SAMGeo structure count, (2) ePlanning DA/CDC record count for this lot, (3) pre-DA site history change events, (4) building age proxy from imagery timeline. If structures appeared after 2012 with no matching DA record, flag. Not a definitive claim — a probability indicator that suggests ordering a s10.7(5) certificate.

**"Climate-Adjusted Land Value"** — Current land value (VG) adjusted by climate risk score and regulatory trajectory. "Land value $850K. Climate risk 7.2/10 (high — coastal erosion + flood exposure). Under AASB S2, institutional holders must disclose this risk from 2027-28. Comparable lots outside climate risk zones: $920K (+8%)." Defensible as factual comparison, not advice.

**"CDC Eligibility Passport"** — For any lot, compute all the SEPP (Exempt & Complying) 2008 exclusion conditions that apply. Heritage → excluded. Flood → excluded (unless minor). Bushfire → excluded (unless BAL-LOW). ANEF → excluded (above 20). Output: "This lot is CDC-eligible for: dwelling house modifications (Category 1), secondary dwelling (SEPP Housing), demolition. CDC-ineligible for: new dwelling house (heritage exclusion), dual occupancy (flood exclusion)." This is a deterministic computation on data we already have. Nobody offers this systematically.

---

## 6. Orchestrator Endpoint — Technical Scope

### Architecture

```
POST /api/intelligence/brief
  Body: { address: string, include_satellite?: boolean, include_economics?: boolean }

  Orchestrator (Python FastAPI):
    1. Geocode + resolve lot geometry (existing: resolve_address)
    2. Fan out to data sources in parallel:

       ┌─ Planning Portal layerintersect (zone, height, FSR, heritage, overlays)
       ├─ NSW Cadastre API (lot boundary, dimensions, corner lot)
       ├─ PostGIS spatial_overlays (15 layer types)
       ├─ DCP controls lookup (zone + precinct → setbacks, parking, etc.)
       ├─ SEPP Housing eligibility check
       ├─ DCP precinct match (geospatial)
       ├─ NSW VG API (land value, 5yr history)
       ├─ ePlanning DA/CDC search (200m radius)
       ├─ Strata detection
       ├─ [NEW] School catchment (spatial join)
       ├─ [NEW] EPA contaminated land (address + proximity)
       └─ [NEW] Domain API (listing status — if integrated)

    3. If include_satellite=true (paid tier), fan out:
       ├─ Shadow detector (geometric, ~3s)
       ├─ Flood truth (multi-source, ~5s)
       ├─ Bushfire prescreen (RFS API, ~2s)
       ├─ Granny flat detection (SAMGeo, ~10-15s)
       ├─ Climate risk score (~2s)
       └─ Pre-DA site history (Tessera + S-2, ~20-30s)

    4. Compound constraint detection (deterministic rules):
       - Heritage × bushfire conflict
       - Heritage × flood mitigation conflict
       - Shadow from neighbour envelope × solar access
       - Structure detected × no DA record
       - Flood evidence × statutory designation mismatch
       - TOD bonus × heritage restriction

    5. Confidence assignment per field:
       - "authoritative" — live government API
       - "extracted" — DCP extraction, QA'd
       - "satellite_estimated" — model output, verify on site
       - "not_available" — data not yet extracted for this council
       - "verify_with_council" — gap or edge case

    6. Assemble unified JSON response

    7. Optional: LLM synthesis (Claude API tool use)
       - Input: unified JSON
       - Output: 6-section natural language brief
       - Every sentence maps to a JSON field
       - Gaps rendered as "not available — refer to [source]"
       - Disclaimer appended to every response

  Response: IntelligenceBriefResponse (JSON)
    ├─ address, coordinates, lot_id
    ├─ planning_controls: { zone, permissibility, height, fsr, lot_size, dcp_controls, sepp_housing }
    ├─ physical_reality: { structures, residual_area, existing_da_records }
    ├─ environmental_constraints: { flood, bushfire, heritage, biodiversity, climate_risk, contamination }
    ├─ neighbourhood: { nearby_das, shadow_impact, densification_signal }
    ├─ economics: { land_value, rental_yield, construction_cost_proxy, listing_status }
    ├─ compound_constraints: [ { type, description, data_sources } ]
    ├─ gaps: [ { field, reason, fallback_source } ]
    ├─ confidence_summary: { high_count, medium_count, low_count, not_available_count }
    ├─ narrative: string | null (LLM synthesis, if requested)
    └─ disclaimer: string
```

### What Needs Building vs What Exists

| Component | Status | Work Required |
|---|---|---|
| Geocode + lot resolve | **Exists** (resolve_address in conveyancing.py) | Wire into orchestrator |
| Planning Portal fetch | **Exists** (getPropertyComplianceData in nsw-planning-portal.ts, get_raw_controls in generate_conveyancing_report.py) | Wire into orchestrator |
| Cadastre lot geometry | **Exists** (lot-geometry API route) | Wire |
| PostGIS spatial overlays | **Exists** (spatial_overlays queries in multiple pipelines) | Wire |
| DCP controls lookup | **Exists** (structured-controls API route, dcp_setback_controls table) | Wire |
| SEPP Housing eligibility | **Exists** (housing_sepp_standards table + eligibility endpoint) | Wire |
| Precinct matching | **Exists** (geospatial match in assessment flow) | Wire |
| VG valuation | **Exists** (get_valuation in conveyancing.py) | Wire |
| ePlanning DA search | **Exists** (threat_radar.py search logic) | Wire |
| Strata detection | **Exists** (detect_strata in conveyancing.py) | Wire |
| Shadow detector | **Exists** (shadow_detector.py) | Wire as optional |
| Flood truth | **Exists** (flood_truth.py) | Wire as optional |
| Bushfire prescreen | **Exists** (bushfire_prescreen.py) | Wire as optional |
| Granny flat detection | **Exists** (granny_flat.py) | Wire as optional |
| Climate risk score | **Exists** (climate_risk_score.py) | Wire as optional |
| Pre-DA site history | **Exists** (pre_da_history.py) | Wire as optional |
| **Orchestrator (fan-out + assembly)** | **NEW** | 3-4 days |
| **Compound constraint detection** | **NEW** | 2 days |
| **Confidence assignment** | **NEW** | 1 day |
| **LLM synthesis prompt** | **NEW** | 2-3 days (prompt engineering + golden tests) |
| **School catchment integration** | **NEW** | 1-2 days |
| **EPA contamination integration** | **NEW** | 1-2 days |
| **ABS cost proxy** | **NEW** | 0.5 days |
| **Batch endpoint** | **NEW** | 2 days |
| **Frontend brief view** | **NEW** | 3-4 days |

### Build Phases

**Phase 1 — Orchestrator + Planning-Only Brief (1.5 weeks)**
- Build orchestrator endpoint with parallel fan-out to all existing Layer A sources
- Compound constraint detection (deterministic rules)
- Confidence assignment per field
- JSON response — no LLM yet, no satellite
- Frontend: structured brief view (sections, expand/collapse, confidence badges)
- Test: 50 Inner West addresses covering edge cases
- **Deliverable:** Instant planning intelligence brief for any NSW address

**Phase 2 — Satellite Integration + LLM Narration (1.5 weeks)**
- Wire satellite pipelines as optional includes (paid tier)
- LLM synthesis via Claude API (tool use → structured JSON → narrative)
- Golden test set: 20 Inner West addresses with known satellite results
- Prompt regression tests (input JSON → expected narrative assertions)
- **Deliverable:** Full intelligence brief with satellite evidence + LLM summary

**Phase 3 — Data Source Expansion (1 week)**
- School catchments (spatial join)
- EPA contaminated land (address + proximity match)
- ABS construction cost proxy
- Domain API free tier (listing status)
- **Deliverable:** Brief now answers contamination, school, cost, and listing questions

**Phase 4 — Bulk + Pre-Computation (1.5 weeks)**
- Cadastre lot ingest (3.35M lots, 14 min)
- VG land values ingest (2.18M records, 18 min)
- Pre-compute overlay flags + DCP controls per lot
- Batch endpoint (POST list of addresses)
- Prospector query endpoint (filter criteria → matching lots)
- **Deliverable:** Bulk screening, sub-second prospector queries

**Total: ~5.5 weeks for full product. Phase 1 alone (1.5 weeks) is demo-ready.**

---

## 7. Defensibility Framework

### What the system says vs what it doesn't

| Safe (factual presentation) | Unsafe (advice/recommendation) |
|---|---|
| "R2 zoning permits secondary dwellings" | "You can build a granny flat here" |
| "DCP rear setback is 8m (Section 2.3.4)" | "Your granny flat should be positioned here" |
| "Sentinel-1 SAR detected surface water within 150m during March 2022" | "This property will flood" |
| "AI detected a ~65m² structure with no matching DA record" | "This structure is illegal" |
| "Climate risk score 7.2/10 based on flood + coastal erosion exposure" | "This property is unsafe to buy" |
| "If northern lot developed to 11.5m height limit, shadow extends 17.4m south" | "Your solar access will be destroyed" |

**Rule: present data, cite sources, disclose gaps. Never synthesize into a conclusion the user should act on.**

### How competitors handle this (and survive)

PropCode, Archistar, CoreLogic — all present planning/property data that users make decisions with. They all use disclaimer frameworks:

1. **"Information not advice"** — standard across industry
2. **Source citation** — every data point attributed
3. **Currency disclosure** — "data as at [date]"
4. **"Verify with authority"** — redirect to council/certifier for confirmation
5. **Professional user assumption** — terms of service assume user is qualified to interpret

We should use all five. The satellite data adds a sixth defence:

6. **Confidence labeling** — "satellite estimated (verify on site)" is more honest than presenting extracted PDF text as definitive. Our transparency about uncertainty is itself a differentiator.

### Legal architecture

- Terms of service: "PlotDetect provides planning and environmental data for research purposes. It does not constitute planning, legal, or financial advice."
- Per-response disclaimer: appended to every intelligence brief
- Confidence signals: visual (green/amber/grey) on every data field
- Audit trail: every query logged with data sources consulted (already built — audit_trail.py)
- No prohibited outputs: no predictions, no recommendations, no "should" statements, no likelihood assessments

---

## 8. For the Hamada Meeting

**Don't demo the LLM layer (not built). Demo the data stack.**

1. Type an Inner West address into the existing assessment page
2. Walk through: zone → permissibility → height/FSR → setbacks → heritage → flood → bushfire → nearby DAs
3. Show the satellite reports: shadow analysis, flood truth, granny flat detection
4. Narrate: "Imagine this as a single page — everything about this lot, one click, 30 seconds"
5. Ask: "In your workflow, what question does this answer? What's missing?"

**What to listen for:**
- Does he want comprehensive analysis (intelligence brief) or specific answers (chatbot)?
- Does he care about satellite data or is planning compliance enough?
- Does he need PDF reports for clients or screen-based workflow?
- How many properties does he screen per week? (bulk value)
- Would he pay per-report or subscription?
- What does he currently use? (CoreLogic? Manual council website checks?)

**His answer determines Phase 1 scope.** If he says "I need to check 20 properties before Saturday auction" → build batch + prospector first. If he says "I need a one-pager for my client's solicitor" → build the PDF brief first. If he says "I need to answer 'can they build a granny flat'" → the existing granny flat tool might be enough with better UX.

---

## 9. Key Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Planning Portal API rate limiting on bulk queries | High | Slows pre-computation | Implement backoff + cache aggressively |
| LLM cost at scale ($0.01-0.05/brief) | Medium | Margin erosion on cheap tiers | Cache LLM output per address (invalidate on data change) |
| Satellite pipeline latency (SAMGeo ~15s, site history ~30s) | High | Bad UX for full brief | Async: return planning data instantly, satellite results stream in |
| DCP coverage gaps outside Inner West | Certain | Brief is thin for some councils | Explicit gap disclosure + PDF link to source DCP |
| User treats brief as advice despite disclaimers | Medium | Liability exposure | Legal review of disclaimer framework before public launch |
| Upstream API changes (Planning Portal, Cadastre) | Low-Medium | Breaks data fetch | Existing monitoring + audit trail detects stale data |

---

## 10. Success Metrics

| Metric | Phase 1 target | Phase 4 target |
|---|---|---|
| Addresses covered (planning-only brief) | All NSW | All NSW |
| Addresses covered (satellite brief) | Inner West + Greater Sydney | All NSW |
| Brief generation time (planning only) | <5s | <1s (pre-computed) |
| Brief generation time (with satellite) | <30s | <30s |
| Data fields per brief | ~40 | ~55 (with Tier 1 new sources) |
| Compound constraints detected | 5 types | 8+ types |
| Confidence: % fields at "authoritative" | >60% (Inner West) | >60% (all NSW) |
| Batch processing | N/A | 50 addresses in <5 min |
| Prospector query response | N/A | <1s for any criteria combination |
