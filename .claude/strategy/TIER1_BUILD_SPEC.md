# Tier 1 Build Spec — B2C Data Infrastructure

**Date:** 2026-06-15
**Branch:** `feat/context-architecture` (will create `feat/tier1-b2c-data` for implementation)
**Status:** SPEC — all endpoints smoke-tested, data shapes confirmed.

---

## Smoke Test Results (2026-06-15)

All primary endpoints confirmed live, free, no auth:

| Endpoint | Status | Records | MaxPerQuery | Sample Verified |
|---|---|---|---|---|
| DA Tracking MapServer (ASSESMENT_RESULT) | LIVE | 324,617 DAs | 4,000 | Inner West approved DAs returned with full outcome |
| VG Valuation MapServer (land values) | LIVE | Statewide | 1,000 | Haberfield R2 properties, 5-yr value history |
| VG Valuation MapServer (property sales) | LIVE | Sales back to 2001 | 1,000 | Five Dock sales with price, area, date |
| Strata Hub FeatureServer | LIVE | All NSW strata plans | 2,000 | Inner West: SP8 (27 lots), SP36 (21 lots) |
| Fair Trading Trades API | NEEDS AUTH | 2,500/mo free | OAuth 2.0 | Catalogue page loads; verify endpoint needs key |

### DA Tracking — Confirmed Field Schema (63 fields)

Key fields not in the ePlanning API:
```
ASSESMENT_RESULT:     Approved (149,118) | Refused (4,272) | Deferred Commencement Consent (1,560) | NULL (169,667)
STATUS:               22 distinct values (vs ePlanning's ~4)
DETERMINING_AUTHORITY: Council | Local Planning Panel | Court | Minister | RPP
DWELLINGS_TO_BE_CONSTRUCTED, DWELLINGS_TO_BE_DEMOLISHED, PRE_EXISTING_DWELLINGS_ON_SITE
PARKING_SPACES, LOADING_BAYS, STAFF_PROPOSED_NUMBER
GROSS_FLOOR_AREA_OF_BUILDING
DEV_INC_HERITAGE_ITEM_OR_AREA, IMPACTS_THREATENED_SPECIES
IS_AN_INTEGRATED_DA, TYPE_OF_MODIFICATION_REQUESTED
DEVELOPMENT_DETAILED_DESC (free text)
LODGEMENT_DATE, DETERMINED_DATE (string format: "20211215")
X, Y (string coords), SHAPE (point geometry)
```

**Query pattern:** `LGA_NAME LIKE '%Inner West%'` (not COUNCIL_NAME — confirmed working).

### VG Valuation — Confirmed Field Schema

**Layer 5 (Urban Property Valuations):**
```
propid, address, zone_desc, prop_area (string: "651.3 square metres"),
val1_bd..val5_bd (valuation base dates, "1 July 2025"..2021),
val1_lv..val5_lv (land values, " $2,660,000" — string with spaces+$),
conapplies, pbdapplies, UnderspFlag, basis_desc
```

**Layer 1 (Urban Property Sales):**
```
propid, house_no, street, suburb, postcode, price (int), sale_date (string),
area (float), strata (0/1), last_sale ("Y"/"N"), deal_props, bp_address
```

**Both support spatial envelope queries** — comparable analysis = query by bbox around subject property.

### Strata Hub — Confirmed Field Schema

```
plannumber (int), registrationdate (epoch ms), address, suburb, lga,
lottotal (smallint), postcode, planlabel, Shape__Area, Shape__Length, geometry (polygon)
```

**lottotal discrimination:** ≤4 = townhouse, 5-8 = small apartment, ≥9 = apartment block.

---

## Build Items (6 components, ordered by dependency)

### 1. DA Outcome Enrichment Service

**What:** New service module `services/da_outcome.py` that queries the DA Tracking MapServer to get actual approval outcomes.

**Why:** Fixes the structural limitation where `pre_da_history.py` can only see "Determined" but not approved/refused. Enables Product B (approval-gap screening) and Product C2 (approval likelihood proxy with real refusal rates).

**Endpoint:**
```
https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Planning/Planning_Portal_Application_Tracking/MapServer/0/query
```

**Integration pattern:** Follow `portal_constraints.py` — use `query_arcgis_point_buffered()` for spatial queries, `query_arcgis_point()` for point lookups. Same `ARCGIS_TIMEOUT = 8`, same error handling.

**Functions to implement:**

```python
def query_da_outcomes_near(
    lng: float, lat: float, radius_m: int = 200,
    years_back: int = 8,
) -> list[DAOutcome]:
    """
    Query DA Tracking MapServer for all DAs within radius of a point.
    Returns list of DAOutcome with ASSESMENT_RESULT, dates, type, authority.
    
    Uses query_arcgis_point_buffered() from portal_constraints.py.
    Paginate via resultOffset if >4000 results (unlikely for 200m radius).
    """

def query_da_at_address(
    address: str, suburb: str,
) -> list[DAOutcome]:
    """
    Query by PRIMARY_ADDRESS LIKE '%{address}%' AND SUBURBNAME='{suburb}'.
    Fallback for when coordinates aren't available.
    """

def get_refusal_rate(
    lga: str, zone: str, dev_type: str, years: int = 3,
) -> RefusalStats:
    """
    Aggregate query: count Approved vs Refused for a cohort.
    For Product C2 (approval likelihood proxy).
    Uses groupByFieldsForStatistics on the MapServer.
    """
```

**Pydantic models:**

```python
class DAOutcome(BaseModel):
    planning_portal_number: str
    da_number: Optional[str]
    status: str
    outcome: Optional[str]  # ASSESMENT_RESULT: Approved/Refused/Deferred Commencement Consent/None
    determining_authority: Optional[str]
    dev_type: Optional[str]
    dwellings_constructed: Optional[int]
    cost: Optional[str]
    address: str
    suburb: str
    x: Optional[float]
    y: Optional[float]
    lodgement_date: Optional[str]
    determined_date: Optional[str]

class RefusalStats(BaseModel):
    lga: str
    zone: Optional[str]
    dev_type: Optional[str]
    period_years: int
    total_determined: int
    approved: int
    refused: int
    deferred_commencement: int
    refusal_rate: float  # refused / total_determined
```

**Wire into pre_da_history.py:** After the existing ePlanning DA/CDC fetch, cross-reference each DA's `PlanningPortalApplicationNumber` against the MapServer to get the actual outcome. Enrich the timeline with "Approved" / "Refused" instead of just "Determined".

**Tests:**
- Unit: mock MapServer response → verify DAOutcome parsing (date formats: "20211215" → "2021-12-15")
- Unit: mock groupByFieldsForStatistics response → verify RefusalStats calculation
- Integration (live, skippable): query Inner West, verify ASSESMENT_RESULT values match known set
- Edge: NULL ASSESMENT_RESULT (undetermined) → outcome=None, not an error
- Edge: pagination needed (>4000 in radius) — test offset logic
- Edge: address search with special chars (apostrophes, slashes)

**Gotchas identified:**
- Date fields are strings in inconsistent formats: LODGEMENT_DATE="20210730000000", DETERMINED_DATE="20211215"
- COST_OF_DEVELOPMENT can be null, "0", or a number string
- X/Y are strings, not floats — need float() conversion
- LGA_NAME field uses "Inner West Council" (or similar) — test exact values

---

### 2. VG Comparable Analysis Service

**What:** New service module `services/vg_comparables.py` that queries the VG Valuation MapServer to find comparable properties and compute over/under-assessment signals.

**Why:** Enables land-tax objection product (recurring, success-fee-able). Also enriches the intelligence brief with market context.

**Endpoints:**
```
Layer 5: https://maps.six.nsw.gov.au/arcgis/rest/services/public/Valuation/MapServer/5/query  (land values)
Layer 1: https://maps.six.nsw.gov.au/arcgis/rest/services/public/Valuation/MapServer/1/query  (sales)
```

**Note:** Layer 5 already queried by `nsw_planning_api.py:191` (single-property by propid). This adds spatial/comparable queries.

**Functions:**

```python
def get_comparable_values(
    lng: float, lat: float,
    zone: str,
    lot_area_m2: float,
    radius_m: int = 500,
    area_tolerance: float = 0.3,  # ±30% of subject lot area
) -> ComparableAnalysis:
    """
    1. Spatial envelope query on Layer 5 within radius.
    2. Filter: same zone_desc, lot area within tolerance.
    3. Parse val1_lv (current) — strip "$", commas, spaces.
    4. Compute: subject vs median/mean comparable, percentile rank.
    5. Return analysis with comparable count, median, subject position.
    """

def get_recent_sales(
    lng: float, lat: float,
    radius_m: int = 500,
    years_back: int = 3,
) -> list[PropertySale]:
    """
    Spatial envelope query on Layer 1.
    Filter by sale_date within years_back.
    Returns sales with price, area, date, address.
    """
```

**Pydantic models:**

```python
class ComparableProperty(BaseModel):
    propid: int
    address: str
    zone: str
    area_m2: float
    land_value: int  # parsed from string
    valuation_date: str

class ComparableAnalysis(BaseModel):
    subject_value: int
    subject_area_m2: float
    comparable_count: int
    median_value: int
    mean_value: int
    percentile_rank: float  # 0-100, where subject sits
    comparables: list[ComparableProperty]
    assessment_signal: str  # "potentially_over" | "in_range" | "potentially_under"
    # over = subject > 75th percentile of comparables on $/m² basis

class PropertySale(BaseModel):
    propid: int
    address: str
    price: int
    area_m2: float
    sale_date: str
    price_per_m2: float
    is_strata: bool
```

**Parsing gotchas (confirmed from smoke test):**
- `val1_lv` = `" $2,660,000"` — leading space, dollar sign, commas. Parse: `int(val.strip().replace('$','').replace(',','').replace(' ',''))`
- `prop_area` = `"651.3 square metres"` — parse: `float(val.split(' ')[0])`
- `sale_date` = `"20 September 2017"` — parse: `datetime.strptime(val, "%d %B %Y")`
- `price` = int (no parsing needed for sales layer)

**Tests:**
- Unit: parse all string formats correctly (edge: "$0", "0 square metres", null values)
- Unit: comparable filtering (same zone, area tolerance, exclude subject property by propid)
- Unit: percentile calculation with various distributions
- Integration: Haberfield R2 query, verify at least 5 comparables returned in 500m
- Edge: very sparse area (rural) — 0 comparables → graceful "insufficient data"
- Edge: strata vs non-strata mixing (use `strata` field to exclude strata from house comparisons)

---

### 3. Exempt Development Screening Calculator

**What:** New service module `services/exempt_screening.py` that classifies detected structures against Codes SEPP exempt thresholds.

**Why:** Critical prerequisite for Product B. Without this, every "no matching approval" flag could be a false alarm on a perfectly legal exempt structure (shed, deck, pergola, carport). This is the filter that turns noise into signal.

**Data inputs (all existing):**
- Structure footprint area_m² from `granny_flat.py::detect_structures_samgeo()` → `DetectedStructure.area_m2`
- Structure height estimate from DEM/terrain (new calc — see §3a)
- Distance from structure centroid to lot boundary (new calc — see §3b)
- Codes SEPP exempt thresholds (must query live from `housing_sepp_standards` table or Planning Portal — NEVER hardcode)
- Crown Land status (relevant per EPI-2026-212: exempt dev now applies to Crown Land under clause 2.40F)

**Regulatory source (Codes SEPP Part 2, Div 1):**

Common exempt thresholds (illustrative — must come from live source at runtime):
- Garden shed/outbuilding: max 20m² floor area, max 3m height, min 900mm from boundary
- Deck/terrace: max 25m² area, max 1m above ground, various setbacks
- Pergola: max 25m² area, max 3m height
- Carport: max 20m² area, max 3m height, specific setback rules
- Fence: max 1.8m height (residential), no area limit
- Retaining wall: max 600mm height, various conditions

**NOTE:** These values are illustrative. The implementation MUST source thresholds from the authoritative database or API at query time. Hardcoded values violate the regulatory-data rule and will become stale.

**Functions:**

```python
def screen_structure_exempt(
    structure: DetectedStructure,
    lot_geometry: dict,  # GeoJSON
    height_estimate_m: Optional[float],
    boundary_distance_m: Optional[float],
    crown_land: bool = False,
) -> ExemptScreenResult:
    """
    Classify a detected structure against Codes SEPP exempt thresholds.
    
    Returns one of:
    - LIKELY_EXEMPT: within all applicable thresholds
    - APPROVAL_GAP: exceeds at least one threshold AND no matching approval found
    - INDETERMINATE: insufficient data to classify (e.g. no height estimate)
    
    NEVER returns "illegal" or "unauthorised" — only factual classification.
    """

def screen_all_structures(
    structures: list[DetectedStructure],
    lot_geometry: dict,
    da_outcomes: list[DAOutcome],  # from da_outcome.py
    cdc_records: list,  # from pre_da_history.py
    crown_land: bool = False,
) -> list[StructureScreenResult]:
    """
    For each detected structure:
    1. Estimate height (DEM at structure centroid vs DEM at ground level)
    2. Calculate distance to nearest lot boundary segment
    3. Screen against exempt thresholds
    4. Cross-reference against DA/CDC records by date proximity
    5. Classify: APPROVAL_LOCATED | LIKELY_EXEMPT | APPROVAL_GAP | INDETERMINATE
    """
```

**Sub-calculations needed:**

**3a. Structure height estimation:**
```python
def estimate_structure_height(
    structure_centroid: tuple[float, float],
    lot_geometry: dict,
    dem_data: Optional[dict] = None,
) -> Optional[float]:
    """
    Estimate height by comparing DEM at structure centroid vs surrounding ground.
    Uses services/dem_service.py::fetch_dem_region() if available.
    Returns None if DEM unavailable (→ INDETERMINATE classification).
    """
```

**3b. Structure-to-boundary distance:**
```python
def structure_boundary_distance(
    structure_bbox: dict,  # from SAMGeo detection
    lot_geometry: dict,  # GeoJSON polygon
) -> float:
    """
    Minimum distance from structure bounding box to nearest lot boundary segment.
    Uses Shapely: structure polygon → lot boundary LineString → .distance()
    Convert degrees to metres using local scale factor.
    """
```

**Pydantic models:**

```python
class ExemptCategory(str, Enum):
    GARDEN_SHED = "garden_shed"
    DECK = "deck"
    PERGOLA = "pergola"
    CARPORT = "carport"
    FENCE = "fence"
    POOL = "pool"
    OTHER = "other"

class ExemptScreenResult(BaseModel):
    classification: Literal["LIKELY_EXEMPT", "APPROVAL_GAP", "INDETERMINATE"]
    category_tested: ExemptCategory
    area_m2: float
    height_m: Optional[float]
    boundary_distance_m: Optional[float]
    thresholds_checked: dict  # {"max_area_m2": 20, "max_height_m": 3, "min_setback_m": 0.9}
    thresholds_exceeded: list[str]  # ["max_area_m2", "min_setback_m"]
    confidence: Literal["high", "medium", "low"]
    notes: list[str]  # ["Height estimated from DEM — accuracy ±1m"]

class StructureScreenResult(BaseModel):
    structure: DetectedStructure
    exempt_screen: ExemptScreenResult
    matching_approval: Optional[DAOutcome]
    final_classification: Literal[
        "APPROVAL_LOCATED",  # DA/CDC found matching this structure
        "LIKELY_EXEMPT",     # within exempt thresholds
        "APPROVAL_GAP",      # exceeds thresholds + no record
        "INDETERMINATE",     # insufficient data
    ]
    consumer_summary: str  # one-line plain English for the report
```

**Consumer-facing language (examples — factual only):**
- APPROVAL_LOCATED: "A development application (DA/2021/0669, approved 2021-12-08) was found matching this structure."
- LIKELY_EXEMPT: "This structure's estimated dimensions (18m², 2.4m height) fall within the exempt development thresholds — no approval was required."
- APPROVAL_GAP: "This structure (estimated 45m², 4.2m height) exceeds exempt development limits, and no matching application was found on the public register (records reliable from ~2018). Verify with a council s10.7 planning certificate or Building Information Certificate."
- INDETERMINATE: "Insufficient data to classify (height could not be estimated from available elevation data)."

**Tests:**
- Unit: each exempt category against threshold boundaries (at, below, above)
- Unit: boundary distance calculation with known geometries
- Unit: cross-reference logic (DA within ±2 years of detected change date)
- Unit: Crown Land flag → applies post-2026-05-15 per EPI-2026-212
- Edge: structure spanning boundary (shared wall) → distance = 0
- Edge: no DEM available → INDETERMINATE, not APPROVAL_GAP
- Edge: multiple structures, some exempt some not
- Edge: pre-2018 change date → always INDETERMINATE (ePlanning not reliable)
- Mutation targets: classification thresholds, confidence levels, date matching window

---

### 4. Reverse Shadow Model (Neighbour → Subject)

**What:** New function in `services/shadow_model.py` that models shadow cast BY a neighbouring lot's maximum legal building envelope ONTO the subject lot.

**Why:** The most novel B2C product idea. "If your neighbour builds to their maximum allowed height, when does your backyard go dark?" Nobody sells this. Deterministic, defensible, genuinely useful for buyers and existing homeowners.

**What exists:**
- `shadow_model.py::model_shadow()` — computes shadow polygon for a building on the subject lot (subject → neighbours). Works correctly for Southern Hemisphere.
- `shadow_model.py::northern_neighbour_proxy()` — returns a bounding-box footprint shifted north by lot depth. Currently used to model subject's shadow ON the neighbour.
- `constraint_arithmetic.py` — computes max height, max GFA, max footprint after setback erosion for any lot with controls.
- `SHADOW_SCENARIOS` — 5 ADG-standard sun positions (Jun/Sep/Dec).

**What's needed (the flip):**

```python
def model_neighbour_shadow_on_subject(
    subject_lot_geojson: dict,
    neighbour_lot_geojson: Optional[dict],  # if available from cadastre
    neighbour_height_limit_m: float,  # from constraint arithmetic
    neighbour_setbacks: Optional[dict],  # front/rear/side from DCP
    scenario: str = "jun21_12pm",
) -> NeighbourShadowResult:
    """
    1. If neighbour_lot_geojson provided, use it directly.
       Otherwise, use northern_neighbour_proxy() to estimate.
    2. Apply neighbour's setbacks to reduce footprint (same logic as constraint_arithmetic).
    3. Use model_shadow() with neighbour's max height on the neighbour's footprint.
    4. Intersect resulting shadow polygon with subject lot polygon.
    5. Calculate: shadow area / subject lot area = shadow fraction.
    6. Run all 3 Jun-21 scenarios (9am, noon, 3pm) for ADG 2-hour solar access check.
    """

def assess_solar_access_risk(
    subject_lot_geojson: dict,
    neighbour_lots: list[dict],  # surrounding lots with their controls
    open_space_geojson: Optional[dict] = None,  # yard/pool area if detected
) -> SolarAccessRisk:
    """
    Comprehensive assessment: run all neighbours × all Jun-21 scenarios.
    Identify which neighbour(s) at max envelope would most impact solar access.
    
    If open_space_geojson provided (from SAMGeo detection of pool/yard area),
    calculate shadow specifically on that area.
    """
```

**Pydantic models:**

```python
class NeighbourShadowResult(BaseModel):
    scenario: str
    scenario_description: str
    neighbour_height_m: float
    neighbour_footprint_area_m2: float
    shadow_on_subject_m2: float
    subject_lot_area_m2: float
    shadow_fraction: float  # 0.0 to 1.0
    shadow_polygon_geojson: Optional[dict]  # for rendering
    hours_in_shadow: Optional[float]  # if multiple scenarios run

class SolarAccessRisk(BaseModel):
    subject_lot_area_m2: float
    scenarios: list[NeighbourShadowResult]
    worst_case_fraction: float
    adg_compliant: bool  # 2hrs solar access 9am-3pm Jun 21
    risk_level: Literal["low", "moderate", "high"]
    consumer_summary: str
    # "low" = <20% shadow at worst case
    # "moderate" = 20-50% 
    # "high" = >50% or ADG non-compliant
```

**Consumer-facing language:**
- Low: "At maximum permissible building height (9m), the neighbouring lot to your north would cast shadow over approximately 15% of your lot at midday on the winter solstice."
- High: "If built to the maximum height limit (12m), the lot to your north could shadow approximately 65% of your property from 2pm at the winter solstice, potentially affecting solar access to your rear yard."

**Getting neighbour lot data:**
- Best case: PostGIS `spatial_overlays` → query adjacent lots by `ST_Touches` or `ST_DWithin`
- For each adjacent lot: query Planning Portal for height/FSR controls → run constraint_arithmetic → get max height
- Fallback: use `northern_neighbour_proxy()` with subject lot's own height limit (conservative estimate)

**Tests:**
- Unit: known lot geometry + known height → verify shadow polygon is south of the building (Southern Hemisphere)
- Unit: shadow fraction calculation with simple rectangular lots
- Unit: ADG compliance check (2hr solar access window)
- Unit: neighbour setback erosion reduces footprint correctly
- Integration: real lot from PostGIS → neighbour lookup → shadow calc → verify reasonable fraction
- Edge: lot on southern boundary of block (no northern neighbour) → no shadow risk
- Edge: neighbour height = 0 (vacant lot) → zero shadow
- Edge: very narrow lot → high shadow fraction even at moderate heights

---

### 5. Strata Classification Service

**What:** New service module `services/strata_lookup.py` that queries the Strata Hub FeatureServer.

**Why:** Discriminates apartment vs townhouse vs house. Opens apartment market (~30% of Sydney) for all products. Prerequisite for apartment risk report (Tier 2).

**Endpoint:**
```
https://portal.spatial.nsw.gov.au/server/rest/services/StrataHub/FeatureServer/0/query
```

**Functions:**

```python
def query_strata_at_point(
    lng: float, lat: float,
) -> Optional[StrataInfo]:
    """
    Spatial intersect query — is this point inside a strata plan polygon?
    Returns strata plan info or None (not strata = house/standalone).
    Uses query_arcgis_point() from portal_constraints.py.
    """

def query_strata_near(
    lng: float, lat: float, radius_m: int = 200,
) -> list[StrataInfo]:
    """
    Nearby strata plans — for neighbourhood density analysis.
    """

def classify_dwelling_type(
    lottotal: int,
) -> str:
    """
    ≤2: duplex/semi
    3-4: townhouse
    5-8: small apartment block
    ≥9: apartment building
    """
```

**Pydantic model:**

```python
class StrataInfo(BaseModel):
    plan_number: int
    plan_label: str  # "SP8"
    address: str
    suburb: str
    lga: str
    lot_total: int
    registration_date: Optional[str]  # parsed from epoch ms
    area_m2: float  # Shape__Area
    dwelling_type: str  # from classify_dwelling_type()
```

**Parsing gotchas:**
- `registrationdate` is epoch milliseconds (can be negative for old plans — SP8 registered 1961)
- Parse: `datetime.fromtimestamp(val / 1000).strftime('%Y-%m-%d')` — handle negative epochs

**Tests:**
- Unit: dwelling type classification boundaries (2, 4, 8, 9)
- Unit: epoch date parsing (positive and negative values)
- Integration: query Haberfield point, verify returns strata plan or None correctly
- Edge: point on boundary between two strata plans → may return multiple → take the one with smallest area (most specific)

---

### 6. Integration — Wire Into Intelligence Brief Pipeline

**What:** Connect all 4 new services into the existing `intelligence_brief.py` orchestrator so they flow through to the Property Profile Hub and future B2C products.

**New sections in the intelligence brief output:**

```python
# In the DevelopmentBrief or separate response model:

class EnrichedPropertyProfile(BaseModel):
    # ... existing fields ...
    
    # NEW: DA outcomes (from da_outcome.py)
    da_outcomes: list[DAOutcome]
    refusal_stats: Optional[RefusalStats]  # cohort stats for this zone/LGA
    
    # NEW: VG comparables (from vg_comparables.py)
    comparable_analysis: Optional[ComparableAnalysis]
    recent_sales: list[PropertySale]
    
    # NEW: Structure screening (from exempt_screening.py)
    detected_structures: list[StructureScreenResult]  # only if satellite data run
    
    # NEW: Solar access risk (from shadow_model.py)
    solar_access_risk: Optional[SolarAccessRisk]  # neighbour shadow assessment
    
    # NEW: Strata classification (from strata_lookup.py)
    strata_info: Optional[StrataInfo]
    dwelling_type: str  # "house" | "duplex" | "townhouse" | "small_apartment" | "apartment"
```

**Orchestration order (respects dependencies):**
1. Strata lookup (independent — runs in parallel with everything)
2. DA outcomes near address (independent — runs in parallel)
3. VG comparables (needs lot area + zone from existing pipeline — runs after lot lookup)
4. Constraint arithmetic for neighbour lots (needs neighbour lot geometries)
5. Reverse shadow model (needs #4 output)
6. Structure detection + exempt screening (needs SAMGeo + DEM + DA outcomes from #2)

Steps 1, 2 can run in parallel.
Steps 3, 4 can run in parallel (after their dependencies).
Steps 5, 6 run after their dependencies.

**API endpoint additions:**
- `GET /api/property/da-outcomes?lng=X&lat=Y&radius=200` — standalone DA outcome query
- `GET /api/property/comparables?lng=X&lat=Y&zone=R2&area=650` — standalone VG comparables
- `GET /api/property/strata?lng=X&lat=Y` — standalone strata check
- `GET /api/property/solar-risk?address=X` — standalone solar access risk assessment
- These also integrate into the main intelligence brief endpoint.

---

## Cross-Cutting Concerns

### Error Handling Pattern (from portal_constraints.py)
```python
try:
    resp = requests.get(url, params=params, timeout=ARCGIS_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    features = data.get("features") or []
    return [parse_feature(f) for f in features]
except requests.Timeout:
    logger.warning(f"Timeout querying {url}")
    return []  # degrade gracefully — never block the pipeline
except Exception as e:
    logger.error(f"Error querying {url}: {e}")
    return []
```

### Caching Strategy
- DA outcomes: cache by address+radius for 24h (DAs don't change outcome after determination)
- VG values: cache by propid for 7 days (values update annually)
- Strata info: cache by plan_number for 30 days (rarely changes)
- Shadow calculations: cache by lot_id+scenario indefinitely (deterministic)

### Liability Language Audit
Every consumer-facing string in this spec uses factual language only:
- "detected", "estimated", "found", "no matching record located"
- NEVER: "safe", "compliant", "illegal", "unapproved", "suitable", "guaranteed"
- Always cite source and date
- Always direct to authoritative verification (s10.7, BIC, council) for APPROVAL_GAP

---

## Implementation Prompting Guide

### How to prompt for bulletproof implementation of each component

**Principle:** Each component should be implemented in a single session with this structure:

```
1. READ the spec section for component N
2. READ the existing code it integrates with (specific files + line numbers)
3. READ the test patterns from conftest.py and an existing test file
4. IMPLEMENT the service module
5. IMPLEMENT the tests
6. RUN pytest on the new tests
7. RUN the existing test suite to verify no regressions
8. REVIEW against the pre-PR 5-check list
```

**Template prompt for each component:**

```
## Context
I'm implementing [COMPONENT NAME] from the Tier 1 B2C build spec at
.claude/strategy/TIER1_BUILD_SPEC.md, section [N].

## What exists (read these first)
- services/portal_constraints.py — ArcGIS query pattern (query_arcgis_point, query_arcgis_point_buffered)
- services/[related_service].py — [what it does, which functions to wire into]
- tests/conftest_mocks.py — mock injection pattern
- tests/test_[related].py — test patterns to follow

## What to build
[Copy the relevant spec section — functions, models, tests, gotchas]

## Constraints
- Follow the existing ArcGIS query pattern in portal_constraints.py (same timeout, error handling, return shape)
- Pydantic models go in services/constraint_models.py (or a new models file if >100 lines)
- Tests: expected use + edge case + failure case (per CLAUDE.md)
- Parse all string fields defensively (the spec lists exact formats from smoke tests)
- NEVER hardcode regulatory thresholds — query from DB or API at runtime
- Consumer-facing strings: factual only, cite source+date, never "safe/illegal/compliant"
- Run existing tests after to verify no regressions

## Verify before PR
1. DB query filters: correct WHERE clauses
2. Unguarded nulls: every API response field null-checked
3. Type assumptions: string→int/float parsing at boundary
4. Silent failure: if MapServer is down, function returns empty list + logs warning (never crashes pipeline)
5. Liability language: grep output strings for banned words
```

**Per-component prompts:**

**Component 1 (DA Outcome):**
```
Implement services/da_outcome.py per TIER1_BUILD_SPEC.md §1.
Read first: portal_constraints.py (query_arcgis_point_buffered pattern),
pre_da_history.py lines 580-630 (_extract_da_fields — the ePlanning fetch to enrich).
Endpoint confirmed live: see smoke test at spec top.
Key gotcha: date strings are "20210730000000" and "20211215" (inconsistent lengths).
Wire into pre_da_history.py: after ePlanning fetch, cross-reference by PlanningPortalApplicationNumber.
```

**Component 2 (VG Comparables):**
```
Implement services/vg_comparables.py per TIER1_BUILD_SPEC.md §2.
Read first: nsw_planning_api.py:185-224 (existing single-property VG query pattern),
portal_constraints.py:42-62 (ArcGIS query pattern).
Key gotcha: val1_lv = " $2,660,000" (string); prop_area = "651.3 square metres" (string).
Parse defensively. Spatial query uses esriGeometryEnvelope with inSR=4326.
```

**Component 3 (Exempt Screening):**
```
Implement services/exempt_screening.py per TIER1_BUILD_SPEC.md §3.
Read first: granny_flat.py:269-275 (DetectedStructure model),
granny_flat.py:408-571 (detect_structures_samgeo — what it returns),
services/lot_dimensions.py (lot geometry utilities).
Key principle: thresholds from live source, NEVER hardcoded.
Check housing_sepp_standards table schema before deciding threshold source.
Crown Land: per EPI-2026-212 (gazetted 2026-05-15), clause 2.40F now includes Crown Land.
```

**Component 4 (Reverse Shadow):**
```
Implement reverse shadow in services/shadow_model.py per TIER1_BUILD_SPEC.md §4.
Read first: shadow_model.py (entire file — model_shadow, northern_neighbour_proxy, SHADOW_SCENARIOS),
constraint_arithmetic.py:240-320 (max height, setback erosion — needed for neighbour envelope).
The flip: model_shadow() currently takes SUBJECT lot geometry + height.
Call it with NEIGHBOUR lot geometry + NEIGHBOUR's max height, then intersect result with subject lot.
Most of the maths already exists — this is a composition, not a rewrite.
```

**Component 5 (Strata):**
```
Implement services/strata_lookup.py per TIER1_BUILD_SPEC.md §5.
Read first: portal_constraints.py (query_arcgis_point pattern — reuse directly).
Endpoint confirmed live: StrataHub FeatureServer, MaxRecordCount=2000, no auth.
Key gotcha: registrationdate is epoch milliseconds (can be negative for pre-1970 plans).
Simple module — should be <100 lines.
```

**Component 6 (Integration):**
```
Wire components 1-5 into intelligence_brief.py per TIER1_BUILD_SPEC.md §6.
Read first: intelligence_brief.py (orchestrator flow — understand existing pipeline stages),
services/compound_constraints.py (parallel data fetching pattern).
Orchestration: strata + DA outcomes in parallel first, then VG comparables + neighbour envelope,
then reverse shadow + exempt screening. Never block the pipeline on a failed external query.
Add FastAPI endpoints per spec.
```

---

## Definition of Done

Each component is done when:
1. Service module implements all functions from spec
2. Pydantic models validate (run `python -c "from services.X import Y"`)
3. All unit tests pass (expected + edge + failure)
4. Existing test suite still passes (pytest full run)
5. No hardcoded regulatory values
6. No liability language in consumer-facing strings
7. Graceful degradation when external API is down (return empty/None, log warning)
8. Integration with intelligence brief pipeline tested end-to-end for at least 1 real address

---

## AMENDMENT 1 — Adversarial Review (2026-06-15)

### Address Input Path Audit — Injection Risk Downgraded

**Finding:** Traced all address entry paths through the entire stack:

| Path | Input Method | Validation | Reaches ArcGIS WHERE? |
|---|---|---|---|
| PropertySearch.tsx | Google Maps autocomplete | Enforced: `usedAutocomplete` flag blocks manual submit | No — resolves to lat/lng |
| AddressAutocomplete.tsx | Google Maps autocomplete | NSW-only `strictBounds`, post-selection NSW check | No — resolves to lat/lng |
| /api/canibuildit/check | JSON body | trim + empty check | No — uses `encodeURIComponent()` for Portal API |
| /api/property/[address] | URL param | Zod schema | No — uses `encodeURIComponent()` for Portal API |
| /pipeline/intelligence-brief | JSON body | Pydantic (5-200 chars, stripped) | No — resolves to lat/lng, spatial queries only |
| /pipeline/threat-radar/subscribe | JSON body | Pydantic | No — parameterized psycopg2 `%s` |
| AddressSearchForm.tsx (granny-flat) | **Raw text input** | **None** | No — URL-encoded to Portal API |

**Conclusion on Issue #1 (ArcGIS WHERE injection):** The existing codebase NEVER passes user address
strings into ArcGIS WHERE clauses. All spatial queries use lat/lng coordinates (floats). Address
strings go to the NSW Planning Portal geocoder via `encodeURIComponent()`, or to PostgreSQL via
parameterized `%s` bindings.

**However, the spec PROPOSES a new path that would create this risk:**
```python
def query_da_at_address(address: str, suburb: str):
    # "Query by PRIMARY_ADDRESS LIKE '%{address}%' AND SUBURBNAME='{suburb}'"
```

**Decision: REMOVE `query_da_at_address()`.** It's unnecessary. The correct flow is:
1. Frontend resolves address → lat/lng via Google autocomplete (already enforced)
2. Backend receives lat/lng (validated by Pydantic with NSW bounds)
3. All ArcGIS queries use spatial point/buffer with validated float coordinates
4. Cross-reference DAs by `PLANNING_PORTAL_APP_NUMBER` (system-generated ID, not user input)

The address-based WHERE fallback was spec'd for "when coordinates aren't available" — but coordinates
are ALWAYS available because the frontend enforces autocomplete selection. Kill the unnecessary
attack surface.

**One raw text path exists** (AddressSearchForm.tsx on granny-flat page) but it never reaches an
ArcGIS WHERE clause — it goes to the Planning Portal geocoder which handles its own input sanitization.

### Revised Issue Severity Table

| # | Original Severity | Revised | Issue | Status |
|---|---|---|---|---|
| 1 | CRITICAL | **ELIMINATED** | ArcGIS WHERE injection | Remove `query_da_at_address()`, use spatial queries only |
| 2 | CRITICAL | **HIGH** | Input validation on new endpoints | Add Pydantic request models (pattern exists in intelligence_brief.py) |
| 3 | HIGH | **HIGH** | No retry on government endpoints | Standardize on 2x backoff. See §A1.1 below. |
| 4 | HIGH | **MEDIUM** | No circuit breaker | Lightweight per-endpoint cooldown. See §A1.2 below. |
| 5 | HIGH | **MEDIUM** | No client-side rate limiting | Semaphore per endpoint for batch mode. See §A1.3 below. |
| 6 | HIGH | **HIGH — CONFIRMED** | VG Layer 5 spatial query quirks | See §A1.4 below — critical implementation gotcha found. |
| 7 | HIGH | **HIGH** | Strata/house contamination in comparables | Cross-reference strata. See §A1.5 below. |
| 8 | HIGH | **HIGH** | SAMGeo ±27% accuracy | Tolerance margin required. See §A1.6 below. |
| 9 | HIGH | **HIGH** | Missing exempt exclusion zones | Check `fetch_sepp_exclusions()` first. See §A1.7 below. |
| 10 | HIGH | **HIGH** | Only northern neighbour | Add east+west. See §A1.8 below. |
| 11 | MEDIUM | MEDIUM | No caching | TTLCache for API responses. See §A1.9 below. |
| 12 | MEDIUM | MEDIUM | No observability | Replicate timings pattern. See §A1.10 below. |
| 13 | MEDIUM | MEDIUM | No data freshness indicator | Surface LAST_UPDATED_DATE. |
| 14 | MEDIUM | **HIGH — CONFIRMED** | String date comparison | Tested: lexicographic works. See §A1.11 below. |
| 15 | LOW | LOW | No API versioning | Use existing route pattern. |
| 16 | LOW | LOW | Crown Land detection | Separate investigation. |
| 17 | LOW | MEDIUM | No batch rate protection | Semaphore for Prospector mode. |

### §A1.1 — Retry Pattern (standardized)

All new service modules MUST use this wrapper instead of raw `requests.get()`:

```python
import time
import requests
import logging

logger = logging.getLogger(__name__)

ARCGIS_TIMEOUT = 8  # seconds
MAX_RETRIES = 2
RETRY_BACKOFF = [1.0, 2.0]  # seconds between retries

def arcgis_get_with_retry(
    url: str, params: dict, timeout: int = ARCGIS_TIMEOUT,
) -> dict:
    """GET with retry on timeout/5xx. Returns parsed JSON or empty dict on failure."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            if resp.status_code == 429:
                logger.warning(f"Rate limited by {url} — not retrying")
                return {}
            if resp.status_code >= 500 and attempt < MAX_RETRIES:
                logger.warning(f"{url} returned {resp.status_code}, retry {attempt+1}")
                time.sleep(RETRY_BACKOFF[attempt])
                continue
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                logger.warning(f"ArcGIS error from {url}: {data['error'].get('message','')}")
                return {}
            return data
        except requests.Timeout:
            if attempt < MAX_RETRIES:
                logger.warning(f"Timeout on {url}, retry {attempt+1}")
                time.sleep(RETRY_BACKOFF[attempt])
                continue
            logger.error(f"Final timeout on {url}")
            return {}
        except Exception as e:
            logger.error(f"Error querying {url}: {e}")
            return {}
    return {}
```

### §A1.2 — Circuit Breaker (lightweight)

```python
import threading

class EndpointHealth:
    """Per-endpoint circuit breaker. After 3 consecutive failures, skip for 60s."""
    def __init__(self, cooldown_s: int = 60, threshold: int = 3):
        self._failures: dict[str, int] = {}
        self._cooldown_until: dict[str, float] = {}
        self._lock = threading.Lock()
        self._cooldown_s = cooldown_s
        self._threshold = threshold

    def is_healthy(self, endpoint: str) -> bool:
        with self._lock:
            until = self._cooldown_until.get(endpoint, 0)
            if time.monotonic() < until:
                return False
            return True

    def record_success(self, endpoint: str):
        with self._lock:
            self._failures[endpoint] = 0

    def record_failure(self, endpoint: str):
        with self._lock:
            count = self._failures.get(endpoint, 0) + 1
            self._failures[endpoint] = count
            if count >= self._threshold:
                self._cooldown_until[endpoint] = time.monotonic() + self._cooldown_s
                logger.warning(f"Circuit open for {endpoint} — cooling down {self._cooldown_s}s")

# Singleton instance shared across the service layer
endpoint_health = EndpointHealth()
```

Integrate into `arcgis_get_with_retry()`: check `endpoint_health.is_healthy(url)` before querying;
call `record_success`/`record_failure` after.

### §A1.3 — Outbound Rate Limiter

```python
# Per-endpoint concurrency limiter for batch mode (Prospector)
_endpoint_semaphores: dict[str, threading.Semaphore] = {}

def get_semaphore(endpoint_key: str, max_concurrent: int = 3) -> threading.Semaphore:
    if endpoint_key not in _endpoint_semaphores:
        _endpoint_semaphores[endpoint_key] = threading.Semaphore(max_concurrent)
    return _endpoint_semaphores[endpoint_key]
```

Use in batch/Prospector mode only. Single-property lookups don't need throttling.

### §A1.4 — VG MapServer Critical Gotcha (discovered during review)

**VG Valuation Layer 5 spatial queries require `OBJECTID` in `outFields`.**

Tested 2026-06-15:
```
outFields=*                             → OK (3 results)
outFields=OBJECTID                      → OK
outFields=OBJECTID,propid,address,...    → OK
outFields=propid                        → FAIL (400 error)
outFields=propid,address,zone_desc      → FAIL (400 error)
```

This is a known ArcGIS REST server quirk on some endpoints. The fix is simple:
**Always include `OBJECTID` as the first field in `outFields` for VG Layer 5 spatial queries.**

```python
# WRONG:
params["outFields"] = "propid,address,zone_desc,val1_lv"

# RIGHT:
params["outFields"] = "OBJECTID,propid,address,zone_desc,prop_area,val1_lv"
```

This does NOT affect WHERE-based queries (e.g. `where=propid=123` works with any outFields).
Only spatial queries (envelope/point geometry) require OBJECTID.

**Also confirmed:** VG Layer 5 does NOT support distance buffer queries despite
`supportsQueryWithDistance: True` in capabilities. Use `esriGeometryEnvelope` only, with
`inSR=4326` as an integer (not string). Post-filter by Haversine distance for accurate radius.

**VG comparable query pattern (correct):**
```python
def _query_vg_spatial(lng, lat, radius_m=500):
    # Convert radius to approximate degree offset for bbox
    lat_offset = radius_m / 111_000
    lng_offset = radius_m / (111_000 * math.cos(math.radians(lat)))
    
    params = {
        "geometry": f"{lng - lng_offset},{lat - lat_offset},{lng + lng_offset},{lat + lat_offset}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": 4326,  # must be int, not string
        "outFields": "OBJECTID,propid,address,zone_desc,prop_area,val1_lv,val1_bd",  # OBJECTID first!
        "resultRecordCount": 1000,
        "f": "json",
    }
    data = arcgis_get_with_retry(VG_LAYER5_URL, params)
    features = data.get("features") or []
    
    # Post-filter by actual Haversine distance (bbox is rectangular, not circular)
    return [f for f in features if _haversine_m(lat, lng, f) <= radius_m]
```

### §A1.5 — Strata/House Contamination in Comparables

**Problem:** If a property is inside a strata plan (apartment/townhouse), its VG land value is a
fraction of the parent lot — meaningless when compared to freestanding houses. Vice versa, comparing
a house to strata lots deflates the comparison unfairly.

**Fix — query order matters:**
1. Run strata lookup (component 5) BEFORE VG comparables (component 2)
2. If subject is strata (`strata_info is not None`):
   - Only compare against other properties inside strata plans in the same area
   - Use `lottotal` from Strata Hub to normalize (value per lot, not raw land value)
3. If subject is NOT strata:
   - Exclude properties inside strata plan polygons from the comparable set
   - Or use the VG sales layer `strata` field (0/1) to filter

This changes the dependency graph: strata lookup must complete before VG comparables can run.

### §A1.6 — SAMGeo Accuracy Tolerance

**Problem:** SAMGeo validated at 64% accuracy with ~0.27 excess detections per lot. A structure
truly 18m² could be measured as 22m², crossing the 20m² exempt threshold and triggering a false
APPROVAL_GAP flag.

**Fix — add uncertainty margin to classification:**

```python
SAMGEO_AREA_UNCERTAINTY = 0.30  # ±30% based on validation (7/11 correct)
SAMGEO_HEIGHT_UNCERTAINTY = 1.0  # ±1m for DEM-derived height estimates

def _classify_with_uncertainty(
    measured_area_m2: float,
    threshold_area_m2: float,
    measured_height_m: Optional[float],
    threshold_height_m: Optional[float],
) -> str:
    """
    LIKELY_EXEMPT: measured + uncertainty < threshold (confident it's under)
    APPROVAL_GAP: measured - uncertainty > threshold (confident it's over)
    INDETERMINATE: measured is within uncertainty of threshold (can't tell)
    """
    area_margin = measured_area_m2 * SAMGEO_AREA_UNCERTAINTY
    
    if measured_area_m2 + area_margin < threshold_area_m2:
        return "LIKELY_EXEMPT"
    if measured_area_m2 - area_margin > threshold_area_m2:
        # Only flag as gap if also passes height check (or height unknown)
        if measured_height_m is not None and threshold_height_m is not None:
            if measured_height_m - SAMGEO_HEIGHT_UNCERTAINTY > threshold_height_m:
                return "APPROVAL_GAP"
            if measured_height_m + SAMGEO_HEIGHT_UNCERTAINTY < threshold_height_m:
                return "LIKELY_EXEMPT"  # height is clearly under even if area is over
            return "INDETERMINATE"  # height uncertain
        return "APPROVAL_GAP"  # area clearly over, no height data
    return "INDETERMINATE"  # area within uncertainty band
```

**Consumer language for INDETERMINATE:** "A structure was detected with estimated dimensions near
the exempt development thresholds (measurement accuracy ±30%). A council Building Information
Certificate search can confirm whether approval was required."

**This is conservative by design** — it minimizes false accusations. Better to say "we're not sure"
than to wrongly flag a legal structure.

### §A1.7 — Exempt Development Exclusion Zones

**Problem:** The Codes SEPP exempt provisions don't apply in certain areas. The spec checks structure
dimensions but not whether exempt development is even available at this location.

**Existing code:** `portal_constraints.py::fetch_sepp_exclusions()` queries ePlanning layer 93
(exemptExclusion). Returns `{"exempt": True}` if the lot is IN the exclusion zone — meaning
exempt development is NOT available.

**Fix — add prerequisite check:**

```python
def screen_all_structures(...):
    # FIRST: check if exempt development is available at this location
    exclusions = fetch_sepp_exclusions(lat, lng)
    exempt_excluded = exclusions and exclusions.get("exempt") is True
    
    for structure in structures:
        if exempt_excluded:
            # Can't use exempt pathway — skip dimension check
            # If no DA/CDC found, it's a gap (or pre-digital, or error)
            result.exempt_screen = ExemptScreenResult(
                classification="INDETERMINATE",
                notes=["Exempt development may not be available at this location "
                       "(SEPP exclusion zone). Dimension check not applicable."]
            )
        else:
            # Normal dimension screening
            result.exempt_screen = screen_structure_exempt(structure, ...)
```

Also check: heritage conservation area, flood planning area, bushfire-prone land (Category 1).
These exclusions are already fetched by the intelligence brief pipeline — pass them through.

### §A1.8 — Multi-Directional Shadow (East + West + North)

**Problem:** Only checking the northern neighbour misses morning (eastern) and afternoon (western)
shadow impact.

**Shadow direction by scenario (Sydney, Southern Hemisphere):**
```
jun21_9am:  sun NE 42.6° → shadow extends SW (222.6°) → EASTERN neighbour shadows you
jun21_12pm: sun N 359.2° → shadow extends S (179.2°)  → NORTHERN neighbour shadows you  
jun21_3pm:  sun NW 316.3° → shadow extends SE (136.3°) → WESTERN neighbour shadows you
```

**Fix — expand `assess_solar_access_risk()` to check 3 neighbours:**

```python
NEIGHBOUR_DIRECTIONS = {
    "jun21_9am": "east",    # eastern neighbour's shadow falls west onto subject
    "jun21_12pm": "north",  # northern neighbour's shadow falls south onto subject
    "jun21_3pm": "west",    # western neighbour's shadow falls east onto subject
}

def assess_solar_access_risk(subject_lot, adjacent_lots, ...):
    for scenario_key, direction in NEIGHBOUR_DIRECTIONS.items():
        neighbour = adjacent_lots.get(direction)
        if neighbour is None:
            neighbour = _estimate_neighbour(subject_lot, direction)  # proxy
        
        shadow = model_neighbour_shadow_on_subject(
            subject_lot, neighbour, neighbour_height, scenario=scenario_key
        )
        results.append(shadow)
```

**Getting adjacent lots:** PostGIS `ST_Touches` or `ST_DWithin(1m)` on cadastre polygons. Classify
direction by comparing neighbour centroid to subject centroid azimuth. Fallback: proxy rectangles
offset in each direction (extend the `northern_neighbour_proxy()` pattern).

### §A1.9 — Caching (minimal, effective)

```python
from cachetools import TTLCache

# Per-module caches — keep it simple
_da_cache = TTLCache(maxsize=500, ttl=86400)     # 24h — outcomes don't change
_vg_cache = TTLCache(maxsize=200, ttl=604800)     # 7 days — values update annually
_strata_cache = TTLCache(maxsize=300, ttl=2592000) # 30 days — rarely changes

def _cache_key(lat: float, lng: float, radius: int) -> str:
    return f"{round(lat,5)},{round(lng,5)},{radius}"
```

Add `cachetools` to `requirements.txt` (lightweight, no external deps).

### §A1.10 — Observability

Replicate the existing `timings` + `DataSourceQuery` pattern from `intelligence_brief.py`:

```python
# In every new service function:
start = time.monotonic()
data = arcgis_get_with_retry(url, params)
elapsed_ms = int((time.monotonic() - start) * 1000)
logger.info(f"da_tracking query: {len(features)} results in {elapsed_ms}ms")

# Return timing metadata alongside data:
return results, {"source": "da_tracking_mapserver", "elapsed_ms": elapsed_ms, "count": len(features)}
```

### §A1.11 — Date Filtering on DA Tracking MapServer

**Tested:** LODGEMENT_DATE is stored as string "20210730000000". Lexicographic comparison works:
```sql
LODGEMENT_DATE >= '20180615'
```
This correctly filters because the date format is YYYYMMDD (zero-padded, lexicographically sortable).

**Gotcha:** Some records have the short format "20211215" (8 chars) while others have "20210730000000"
(14 chars). Use `>=` with 8-char prefix — lexicographic comparison handles both correctly because
"20211215" > "20180615" and "20210730000000" > "20180615000000" are both true.

### §A1.12 — Input Validation for New Endpoints

**Every new endpoint MUST have a Pydantic request model.** Follow the `IntelligenceBriefRequest`
pattern:

```python
class PropertyQueryRequest(BaseModel):
    """Shared base for all new property query endpoints."""
    lat: float = Field(..., ge=-37.5, le=-28.0, description="Latitude (NSW bounds)")
    lng: float = Field(..., ge=140.9, le=153.7, description="Longitude (NSW bounds)")
    radius_m: int = Field(200, ge=50, le=2000, description="Search radius in metres")

class DAOutcomeRequest(PropertyQueryRequest):
    years_back: int = Field(8, ge=1, le=20)

class ComparableRequest(PropertyQueryRequest):
    zone: str = Field(..., pattern=r"^[A-Z][A-Z0-9]{1,4}$", description="Zone code e.g. R2")
    lot_area_m2: float = Field(..., ge=10, le=100000)
    radius_m: int = Field(500, ge=100, le=2000)

class StrataRequest(BaseModel):
    lat: float = Field(..., ge=-37.5, le=-28.0)
    lng: float = Field(..., ge=140.9, le=153.7)
```

### Security Architecture Summary (post-audit)

```
User Browser
  → Vercel/Nginx (TLS)
  → Next.js middleware (rate limiting: Redis/Upstash, per-tier limits)
  → Next.js API route (Zod validation, address regex, coordinate bounds)
  → Address → Google Maps Autocomplete → lat/lng (pre-validated)
  → FastAPI (internal only, CORS-restricted, Pydantic validation)
  → ArcGIS queries: spatial only (float coords), NEVER user strings in WHERE
  → PostgreSQL: parameterized queries only (%s bindings)
```

No user-supplied string ever reaches an ArcGIS WHERE clause or an unparameterized SQL query.
The only raw text path (granny-flat AddressSearchForm) is URL-encoded and sent to the Planning
Portal geocoder, which handles its own sanitization.

---

## AMENDMENT 2 — QA Validation Findings (2026-06-15)

Full QA report: `.claude/strategy/TIER1_QA_REPORT.md`
Test scripts: `qa_phase1_test.py`, `qa_phase2_failure.py`, `qa_phase3_liability.py`

**44 tests run across 3 phases. 4 real bugs found, 0 logic errors, 0 security vulnerabilities.**

### §A2.1 — Windows-Safe Epoch Parsing [BUG-1, CRITICAL]

`datetime.fromtimestamp()` throws `OSError` on Windows for negative epoch ms (pre-1970 strata plans).
Replace ALL epoch parsing with:

```python
_EPOCH = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)

def safe_epoch_to_datetime(epoch_ms: int | None) -> datetime.datetime | None:
    if epoch_ms is None:
        return None
    return _EPOCH + datetime.timedelta(milliseconds=epoch_ms)
```

### §A2.2 — Liability Language Fixes [BUG-2 + BUG-3, HIGH]

APPROVAL_GAP template — change:
- "may have been approved under a different reference" → "may have received consent under a different reference"

Disclaimer — change:
- "For definitive approval status" → "To confirm approval history, obtain a Building Information Certificate (s6.26 EP&A Act) from the relevant council"
- "may have been approved under references" → "may have received consent under references"

### §A2.3 — Circuit Breaker MANDATORY [BUG-4, MEDIUM→REQUIRED]

VG MapServer returned 404 after ~20 sustained queries. `EndpointHealth` circuit breaker (§A1.2)
is upgraded from optional to **required for implementation**.

### §A2.4 — VG Null Value Handling

`val1_lv` can be `None`. String parser must handle:
```python
def parse_land_value(val_str: str | None) -> int | None:
    if not val_str or not val_str.strip():
        return None
    cleaned = val_str.replace("$", "").replace(",", "").replace(" ", "")
    try:
        return int(cleaned)
    except ValueError:
        return None
```

### §A2.5 — Earliest Data Coverage

DA Tracking MapServer earliest record: 2 July 2019 (Inner West). Consumer output MUST state
the search date range explicitly. APPROVAL_GAP is only meaningful for post-2019 structures.
