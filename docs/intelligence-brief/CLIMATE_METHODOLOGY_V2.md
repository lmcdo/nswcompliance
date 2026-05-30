# Climate Disclosure Profile — Methodology v2.0

**Status:** Approved design — not yet implemented
**Date:** 2026-05-30
**Supersedes:** Climate Risk Awareness Score v1.1 (equal-weight composite)
**Pre-launch requirement:** Legal review of framing, action register language, and
liability position before any user-facing deployment.

## Design decision

Replace the composite climate risk score (1-100, equal-weight across hazards) with a
structured **Climate Disclosure Profile** organised into three epistemological layers,
with cross-layer gap detection and an action register.

No composite risk score is computed. The only aggregate numbers are:

- `statutory_count` — count of government-designated hazard constraints (integer)
- `gap_alert_count` — count of cross-layer data discrepancies (integer)
- `checks_performed` — count of hazard categories assessed (integer)
- `coverage_pct` — checks_successful / checks_performed (float)

## Motivation

The original composite score conflated three fundamentally different types of data:

1. Statutory designations (legally binding, present-day constraints)
2. Empirical observations (measured data, no legal status)
3. Climate projections (model-dependent, scenario-specific futures)

Weighting these equally (or at all) creates a category error. A flood planning area
designation has legal consequences for development assessment, insurance, and vendor
disclosure. A projected heat trajectory does not. A single number that treats them as
equivalent is misleading regardless of methodology.

The primary use case — certification of positive compliance action — requires evidence
of systematic assessment, not a risk ranking. APRA CPG 229, TCFD/TNFD reporting, ESG
frameworks, and DA submission requirements all need: what was checked, what was found,
what needs follow-up. A composite score doesn't serve this. A structured disclosure
profile does.

## Data model

```
ClimateDisclosureProfile:
  assessment_date: date
  methodology_version: str          # "2.0"

  manifest:
    categories_assessed: int        # total hazard categories in scope (fixed per version)
    sources_queried: int            # data sources attempted
    sources_successful: int         # data sources that returned data
    sources_unavailable: list       # [{source, reason}]
    coverage_pct: float             # sources_successful / sources_queried
    data_quality_notes: list[str]   # cross-source discrepancies (internal QA)

  scope_limitations: list[str]      # MANDATORY — what is NOT assessed (see section below)

  statutory:                        # Layer 1 — government-designated constraints
    designations: list[StatutoryFinding]
      # each: hazard, designation, source, legislation_ref, as_at, confidence,
      #        geometry_relationship (intersects|contains), statutory_data_age_days
    count: int

  empirical:                        # Layer 2 — observed/measured data
    observations: list[EmpiricalFinding]
      # each: hazard, value, unit, source, data_date, confidence,
      #        false_positive_likelihood (low|moderate|high)

  projected:                        # Layer 3 — model-dependent futures
    trajectories: list[ProjectedFinding]
      # each: hazard, value, model, scenario, timeframe, confidence

  gap_alerts: list[CompoundConstraint]
    # cross-layer discrepancies (existing type from compound_constraints.py)

  action_register: list[ActionItem]
    # derived from: gap alerts + stale data + unavailable sources
    # each: description, category (verify|investigate|monitor),
    #        recommended_source, verify_url
    # FRAMING: "Recommended verification" — never directive language

  per_hazard_detail: list[HazardScore]
    # existing normalized 0-1 scores per hazard for drill-down detail
    # NOT composited, NOT used for sorting/ranking
```

## Three layers

### Layer 1 — Statutory Record

Government-designated hazard constraints with legal planning consequences.

| Hazard / Constraint | Source | Authority | Status |
|---------------------|--------|-----------|--------|
| Flood planning area | Hazard/Layer 1 | NSW Planning Portal EPI | In spatial_overlays |
| Bushfire prone land | Fire/BFPL/Layer 0 + RFS live API fallback | NSW Rural Fire Service | In spatial_overlays |
| Coastal hazards (wetlands, littoral, env area, use area) | SEPP R&H 2021 / CoastalManagementSEPP | NSW Planning Portal | In spatial_overlays + frontend live queries |
| Landslide risk | Hazard/Layer 2 | NSW Planning Portal EPI | In spatial_overlays |
| Acid sulfate soils | Protection/Layer 1 | NSW Planning Portal EPI | In spatial_overlays |
| Terrestrial biodiversity | Protection/Layer 10 | NSW Planning Portal EPI (LEP Part 5) | In spatial_overlays + SEE intake |
| Riparian lands & watercourses | Protection/Layer 7 | NSW Planning Portal EPI | In spatial_overlays |
| Wetlands (LEP) | Protection/Layer 11 | NSW Planning Portal EPI | In spatial_overlays |
| ANEF aircraft noise | Protection/Layer 2 | SEPP Transport Infrastructure 2021 | In spatial_overlays + SEE intake + frontend |
| Drinking water catchment | Protection/Layer 3 | SEPP R&H 2021 Ch.2 | Live in compliance engine (frontend) + SEE intake |
| Mine subsidence districts | NSW Admin Boundaries FeatureServer/7 | NSW Spatial Services | Live in compliance engine (frontend) + SEE intake |
| Contaminated land (EPA notified sites, 500m) | EPA MapServer/0 | NSW EPA | Live in compliance engine (frontend) + SEE intake |
| Groundwater vulnerability | Protection/Layer 4 | NSW Planning Portal EPI | Available, not yet ingested |
| Salinity | Protection/Layer 8 | NSW Planning Portal EPI | Available, not yet ingested |

**Already-live endpoints (from compliance engine `nsw-planning-portal.ts`):**
- Mine subsidence: `https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Administrative_Boundaries_Theme/FeatureServer/7`
- Contaminated land: `https://mapprod2.environment.nsw.gov.au/arcgis/rest/services/EPA/Contaminated_land_notified_sites/MapServer/0`
- Drinking water: `https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Planning/Protection/MapServer/3`
- ANEF: `https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Planning/Protection/MapServer/2`
- Coastal: `https://mapprod1.environment.nsw.gov.au/arcgis/rest/services/CoastalManagementSEPP/CoastalManagementSEPP/MapServer` (layers 1, 3, 6)

All are free, unauthenticated ArcGIS REST services.

Each designation: present/absent, source attribution, legislation reference, data date,
geometry relationship (intersects vs contains), data age in days.

Framing: "These are legally designated constraints sourced from NSW government spatial
datasets. They affect development assessment, insurance premiums, and vendor disclosure
obligations under s10.7 planning certificates. Verify current status via s10.7
certificate before acting on any finding."

### Layer 2 — Empirical Evidence

Measured/observed data from authoritative datasets. No legal planning status.

| Hazard | Source | Data type | False positive likelihood |
|--------|--------|-----------|--------------------------|
| Fire history | spatial_overlays (NPWS) | Event count at location | Low |
| Urban heat island | NSW Planning Portal ArcGIS (UHGC/Layer 0) | UHI intensity (degrees C above baseline) | Low (dated 2016) |
| Heat vulnerability index | NSW Planning Portal ArcGIS (UHGC/Layer 1) | Vulnerability index value | Low (dated 2016) |
| Active fire detections | NASA FIRMS (VIIRS/MODIS) | Hotspot detections within radius | Moderate (controlled burns) |
| Extreme rainfall IFD | ARR Data Hub (BOM) | Design rainfall depths by duration/AEP | Low (calculated, not observed) |
| Satellite flood evidence | JRC Global Surface Water, DEA WOfS | Historical water occurrence % | Moderate (irrigation, dams) |
| Satellite structure detection | samgeo (granny flat pipeline) | Structure count on lot | Moderate (requires confirmation) |

Framing: "These are observations from authoritative datasets. They reflect what has been
measured or detected at this location. Findings with moderate false positive likelihood
require independent verification before reliance."

### Layer 3 — Projected Trajectory

Climate model output. Scenario-dependent, model-dependent, not predictions.

| Hazard | Source | Specification |
|--------|--------|---------------|
| Heat trajectory | NARCliM 2.0 (AdaptNSW) | Hot days delta, ACCESS-ESM1.5, SSP3-7.0, 4km |
| Precipitation trend | NARCliM 2.0 (AdaptNSW) | Rainfall delta (when available) |

Framing: "These are climate model projections. They are scenario-dependent, based on a
single GCM (ACCESS-ESM1.5), and do not represent predictions of future conditions.
They are provided as contextual information only and do not contribute to statutory
or empirical findings."

## Scope limitations (mandatory field)

Every profile MUST include a scope_limitations list. This is structural — embedded in
the data model, not appended as a disclaimer string. Minimum contents:

```
scope_limitations:
  - "This assessment covers {N} defined hazard categories from government and
     authoritative datasets. It does not constitute a comprehensive site-specific
     risk assessment."
  - "Not assessed: localised drainage, building-specific vulnerability, construction
     type, floor height, mitigation works, site-specific contamination investigation
     (EPA notified sites checked within 500m only), soil testing, geotechnical
     conditions, asbestos."
  - "Statutory findings based on spatial data ingested {date}. Current designations
     available via s10.7 planning certificate from the relevant council."
  - "Empirical observations may include false positives. See per-finding false
     positive likelihood rating."
  - "Projected trajectories are model-dependent and scenario-specific. They do not
     represent predictions."
```

## Gap detection

Cross-layer discrepancies surfaced as gap alerts. These are the product's primary
differentiator — nobody else cross-references statutory designations against satellite
evidence against empirical data for property buyers.

### Existing rules (from compound_constraints.py)

- `flood_evidence_exceeds_statutory` — JRC/WOfS > 2% but no EPI flood designation
- `structure_no_da_record` — satellite detects >1 structure but no secondary dwelling DA
- `heritage_hca_bushfire_vegetation` — 10/50 clearing entitlement vs heritage landscape

### New rules (to implement with v2 data sources)

- `fire_detected_no_bushfire_designation` — FIRMS active fire within 500m AND >2
  detections in 12 months, but property not in bushfire prone land
- `extreme_rainfall_no_flood_designation` — ARR IFD 1% AEP depth exceeds typical OSD
  threshold (varies by council) but no flood planning area designated
- `uhi_high_no_heat_trajectory` — UHI intensity > 4 degrees C above baseline but
  NARCliM data unavailable (coverage gap, not risk gap)

### False positive thresholds

Each gap alert rule has a minimum evidence bar to reduce false positives:

| Rule | Threshold | Rationale |
|------|-----------|-----------|
| `flood_evidence_exceeds_statutory` | JRC > 2% OR WOfS > 2% | Below 2% is noise (irrigation, temporary ponding) |
| `fire_detected_no_bushfire_designation` | FIRMS: within 500m AND > 2 detections/12mo | Single detection likely controlled burn. 500m avoids distant fires |
| `extreme_rainfall_no_flood_designation` | ARR 1% AEP depth > council-specific OSD threshold | Threshold varies — use 100mm/hr as default if council threshold unknown |
| `structure_no_da_record` | > 1 structure detected | Single structure = main dwelling (expected) |

Each gap alert includes:
- `id`, `description`, `caveat`, `severity`, `data_sources_used`
- `false_positive_likelihood`: low / moderate / high (based on source characteristics)

## Action register

Derived automatically from three sources:

1. **Gap alerts** → "Data discrepancy: [description]. Verification available from
   [authority] at [verify_url]"
2. **Stale data** → "Statutory data from [source] is [N] days old (threshold: [T] days).
   Current status available via s10.7 planning certificate"
3. **Unavailable sources** → "[Category] not assessed: [source] could not be queried.
   [Reason]"

### Framing rules (liability-critical)

Action items use **informational language**, never directive language:

- YES: "Verification available from [authority]"
- YES: "Current status available via s10.7 planning certificate"
- YES: "Data discrepancy identified between [source A] and [source B]"
- NO: "Contact council to verify"
- NO: "You should investigate"
- NO: "We recommend obtaining"
- NO: "Action required"

The distinction: we state where information can be found, not what the user should do.
This maintains the information/advice boundary.

### Standing action items

Every profile auto-includes:

1. "Statutory findings based on spatial data ingested [date]. Current designations
   available via s10.7 planning certificate from [council]." — ALWAYS present when
   any statutory data source is older than 90 days.

## Stale statutory data handling

Statutory findings are the highest-liability data in the profile. Stale statutory data
that presents as current is worse than no data.

**Thresholds** (from existing staleness detection):
- `spatial_overlays`: 365 days
- `nsw_valuation_service`: 365 days
- `plotdetect_dcp`: 180 days

**When statutory data exceeds threshold:**

1. Confidence demoted from AUTHORITATIVE to STALE (existing behaviour)
2. `statutory_data_age_days` field populated on the finding
3. Finding remains in statutory layer but is visually distinguished (stale, not current)
4. Action register auto-generates: "Statutory data from [source] is [N] days old.
   Current status available via s10.7 planning certificate from [council]."
5. Manifest includes: "One or more statutory findings may not reflect current
   designations. See action register."

A stale finding that still presents as "this property IS in a flood planning area"
without qualification is a liability. The demotion + action item makes staleness
visible.

## Partial intersection detection

When property lot geometry is available (from `/api/property/lot-geometry`):

- `ST_Contains(designation_geom, lot_geom)` → "Property contained within [designation]"
- `ST_Intersects` true but `ST_Contains` false → "Property intersects [designation]
  boundary — partial overlap"

Partial overlap is meaningful: a property where 5% of the lot touches a flood planning
area is different from one entirely within it. The statutory finding should note this
when geometry data permits.

When lot geometry is not available, the finding reports intersection only (current
behaviour) without claiming full containment.

## Cross-source validation (internal QA)

When multiple sources query the same hazard:
- Bushfire: spatial_overlays vs RFS live API (both query BPL)
- Flood: spatial_overlays (EPI) vs JRC/WOfS (satellite)

If two sources for the same hazard disagree about the same property, the manifest
records a `data_quality_note` explaining the discrepancy. This is internal QA — not
surfaced to the user as a gap alert (which is cross-LAYER, not cross-source for the
same layer).

Example: "spatial_overlays reports bushfire=absent for this location, but RFS live API
reports Vegetation Category 1. spatial_overlays data may be stale or bbox-limited."

## Coverage percentage

The only aggregate metric. Measures assessment thoroughness, not property risk.

```
coverage_pct = sources_successful / categories_assessed
```

### Fixed category list (v2.0)

The denominator is a fixed, enumerated list per methodology version. Adding a new
category requires a version bump. This prevents gaming (inflating coverage with
trivial checks).

**v2.0 categories (22):**

Statutory (14):
1. Flood planning area (Hazard/1)
2. Bushfire prone land (Fire/BFPL/0)
3. Coastal hazards — wetlands, littoral, env area, use area (SEPP R&H)
4. Landslide risk (Hazard/2)
5. Acid sulfate soils (Protection/1)
6. Terrestrial biodiversity (Protection/10)
7. Riparian lands & watercourses (Protection/7)
8. Wetlands — LEP (Protection/11)
9. ANEF aircraft noise (Protection/2)
10. Drinking water catchment (Protection/3)
11. Mine subsidence districts (NSW Spatial Services FS/7)
12. Contaminated land — EPA notified sites within 500m (EPA MapServer/0)
13. Groundwater vulnerability (Protection/4)
14. Salinity (Protection/8)

Empirical (6):
15. Fire history (NPWS spatial_overlays)
16. Urban heat island (UHGC MapServer/0)
17. Active fire detections (NASA FIRMS)
18. Extreme rainfall IFD (ARR Data Hub)
19. Satellite flood evidence (JRC/WOfS)
20. Satellite structure detection (samgeo)

Projected (2):
21. Heat trajectory (NARCliM 2.0)
22. Precipitation trend (NARCliM 2.0)

Of these, categories 1-5, 15 are already in spatial_overlays. Categories 6-8 are in
spatial_overlays but not yet wired into the disclosure profile. Categories 9-12 are
live in the compliance engine frontend but need porting to Python. Categories 13-14
have confirmed ArcGIS endpoints but aren't ingested yet. Categories 16-20 are new
Stage 4b data sources. Categories 21-22 are existing NARCliM.

Coverage example: "19 of 22 categories assessed (86%). Unavailable: NARCliM heat
trajectory (outside raster domain), groundwater vulnerability (not yet ingested),
salinity (not yet ingested)."

### Version-pinned coverage

Every assessment records `methodology_version`. Coverage is calculated against the
category list for THAT version. Historical assessments are valid for their version.

If the methodology adds categories in v2.1, a v2.0 assessment showing 13/15 (87%)
is NOT retroactively recalculated to 13/18 (72%). The profile states:
"Assessment performed under methodology v2.0. Current methodology is v2.1."

Users wanting a current assessment request a new one.

## Sorting and comparison

For portfolio/shortlist comparison:

- **Primary sort:** `statutory_count` (descending) — more statutory constraints = more constrained
- **Secondary sort:** `gap_alert_count` (descending) — more discrepancies = more to investigate
- **Coverage indicator:** `coverage_pct` — assessment completeness, not risk level

These are all counts of facts, not computed assessments. No weighting decision required.

## What happens to per-hazard scores

The existing `HazardScore` dataclass (hazard, raw_score 0-1, weight, present, detail,
confidence, data_source, available) remains in `per_hazard_detail` for drill-down.

They are:
- NOT composited across hazards
- NOT used for sorting or ranking
- NOT labelled as risk scores in the UI
- Available for detailed inspection within each layer

## Liability considerations

- **No composite risk claim.** We never rank heterogeneous hazards against each other.
- **Source attribution on every finding.** Every data point traces to a government or
  authoritative dataset with date and confidence.
- **Gap alerts are factual observations.** "These datasets disagree" is verifiable, not
  interpretive.
- **False positive likelihood rated per source.** User knows which findings need
  independent verification.
- **Caveat on every gap.** Limitations and recommended verification steps are explicit.
- **Action register uses informational framing.** "Verification available from [X]"
  not "You should contact [X]." Information, not advice.
- **Coverage metric is about our process.** "We assessed 13 of 15 categories" is a fact
  about our methodology, not a claim about the property.
- **Scope limitations are structural.** Embedded in the data model as a mandatory field,
  listing what is NOT assessed. Not a disclaimer string.
- **Stale statutory data demoted.** Findings older than threshold are visually
  distinguished and auto-generate action items. Never presented as current.
- **s149 parallel.** Statutory layer presents the same government data that s10.7
  planning certificates already disclose, in a more accessible format.
- **Legal review required.** Framing, action register language, and liability position
  must be reviewed by a lawyer before user-facing deployment.

## Known data source gaps

| Data | Why unavailable | Workaround |
|------|-----------------|------------|
| Coastal vulnerability (SLR 2025) | SEED spatial viewer only, no REST/WFS API | Existing SEPP R&H coastal layers cover statutory designation; 2025 assessment is contextual only |
| NARCliM outside domain | Raster files cover NSW only, edge locations may miss | Heat marked unavailable, excluded from coverage denominator for that assessment |

## Verified data sources (Stage 4b — new)

| Source | Status | Endpoint | Auth |
|--------|--------|----------|------|
| ARR Data Hub | CONFIRMED | `https://data.arr-software.org/?lon_coord={lng}&lat_coord={lat}&type=json&All=1` | None |
| NASA FIRMS | CONFIRMED | `https://firms.modaps.eosdis.nasa.gov/api/area/csv/{KEY}/{SOURCE}/{bbox}/{days}` | Free MAP_KEY (email registration) |
| NSW UHI | CONFIRMED | `https://mapprod2.environment.nsw.gov.au/arcgis/rest/services/UHGC/UHGC/MapServer` | None |
| Mine subsidence | CONFIRMED | `https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Administrative_Boundaries_Theme/FeatureServer/7` | None |
| Contaminated land | CONFIRMED | `https://mapprod2.environment.nsw.gov.au/arcgis/rest/services/EPA/Contaminated_land_notified_sites/MapServer/0` | None |
| NSW Groundwater | CONFIRMED | `https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Planning/Protection/MapServer/4` | None |
| NSW Salinity | CONFIRMED | `https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Planning/Protection/MapServer/8` | None |
| NSW Coastal SLR | PARTIAL | SEED viewer only. Existing SEPP coastal layers already ingested. | N/A |

Note: Mine subsidence and contaminated land are already live in the compliance engine
(`nsw-planning-portal.ts`). They need to be ported to the Python intelligence brief
service, not built from scratch.

## Implementation sequence

### Phase A: Wire existing data (no new APIs)
1. Refactor `ClimateRiskResult` -> `ClimateDisclosureProfile` data model
2. Remove composite score calculation from `climate_risk_score.py`
3. Add manifest, scope_limitations, and coverage tracking
4. Wire biodiversity, riparian, wetlands into statutory layer (already in spatial_overlays)
5. Port mine subsidence, contaminated land, drinking water, ANEF queries from
   frontend TypeScript to Python service (endpoints already confirmed, just porting)
6. Add acid sulfate soils to statutory layer (already in spatial_overlays, not in climate scoring)

### Phase B: New external data sources
7. Ingest groundwater vulnerability + salinity into spatial_overlays
8. Wire ARR Data Hub (IFD rainfall) as empirical layer source
9. Wire NASA FIRMS (active fire) as empirical layer source
10. Wire NSW UHI (ArcGIS UHGC) as empirical layer source

### Phase C: Cross-layer intelligence
11. Add new gap detection rules to `compound_constraints.py` with false positive thresholds
12. Add action register derivation with informational framing
13. Add partial intersection detection (ST_Contains vs ST_Intersects)
14. Add cross-source validation (data_quality_notes in manifest)

### Phase D: Integration
15. Update intelligence brief orchestrator to use new profile structure
16. Legal review of framing and action register language
