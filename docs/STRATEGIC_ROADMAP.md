# PlotDetect Strategic Roadmap: Next-Level Capabilities
**Date:** 2026-02-06
**Context:** Age of vibe coding agents - what capabilities create defensible moats?

---

## Executive Summary

PlotDetect's current moat: **47,818 curated provisions with structured v2 taxonomy** + **spatial regulatory data** (heritage HCA, precincts, planning portal integration).

**The strategic opportunity:** Transform from "compliance information retrieval" to **"spatial compliance validation engine"** - where professionals upload designs and get automated compliance reports with 3D visualization of pass/fail elements.

**Why this is defensible:**
1. **Data moat:** 47,818 provisions → spatial rule logic (requires deep domain expertise)
2. **Technical moat:** BIM/CAD integration + PostGIS spatial engine + 3D visualization
3. **Accuracy moat:** Real-world validation against approved DAs builds trust over years
4. **Integration moat:** Connections to Revit, SketchUp, surveyor tools require industry relationships

**Vibe coding agents cannot easily reproduce** because they lack:
- Curated provision database (human domain expertise required)
- Spatial rule encoding (ambiguous provision text → precise geometry tests)
- BIM integration (requires deep software partnerships)
- Validation datasets (years of DA outcomes)

---

## Current State Analysis

### What PlotDetect Does Today (Strengths)

**Data Assets:**
- 47,818 DCP provisions across 3 councils (Ashfield, Leichhardt, Marrickville)
- v2 taxonomy: v2_marker (heritage/generic), v2_topic (parking/landscaping/setbacks), v2_is_actionable
- Heritage HCA boundaries with spatial matching
- 102 precincts with v2_precinct_id linkage
- SEPP Housing 2021 structured requirements (241 provisions)
- Planning Portal integration (zone, FSR, height, constraints, BASIX)

**Core Workflows:**
- Property address → filtered provisions (395-701 provisions from 300+ page DCP)
- Regulatory cascade: Planning Portal → SEPP → LEP → DCP
- CDC preliminary check with blocker identification
- Heritage provision filtering (306 provisions organized by topic)
- PDF page citations for verification
- 12-18x faster than manual DCP reading

**User Value by Niche:**
1. **Developer:** Feasibility analysis, cost impact quantification ($32k parking, $22k landscaping)
2. **Architect:** Compliant concept design from day 1, no rework
3. **Town Planner:** DA report provision citations, zero RFI risk
4. **Certifier:** CDC blocker documentation with SEPP citations
5. **Real Estate Agent:** Development potential assessment (20-30% premium for dual occ)
6. **Heritage Consultant:** Complete SOHI provision checklist (30 min vs 3-4 hours)
7. **Conveyancer:** Constraints verification, professional indemnity protection
8. **Builder:** Construction specification extraction for accurate quotes

### What's Missing (Strategic Gaps)

**Current model is PASSIVE:** "Here are the rules, you figure out if you comply"

**Next level is ACTIVE:** "Upload your design, we'll tell you exactly what's compliant/non-compliant and show you in 3D"

**Key gaps:**
1. **No spatial validation:** Can't upload a design and test compliance
2. **No 3D visualization:** Can't see building envelope, shadow impacts, heritage context
3. **No scenario modeling:** Can't test "what if I increase FSR" or "what if I amalgamate lots"
4. **No automated outputs:** Can't generate DA checklists, s4.15 assessment, heritage impact reports
5. **No BIM integration:** Architects use Revit/SketchUp, but can't send geometry to PlotDetect for validation
6. **No site discovery:** Can't search "find me all R3 lots >600sqm near train station with clean constraints"

---

## Strategic Roadmap: Three Horizons

### HORIZON 1 (6-12 months): Spatial Compliance Engine
**Goal:** Transform PlotDetect from information retrieval to active compliance validation

#### 1.1 Design Upload & Validation
**Capability:** Upload proposed design → automated compliance report

**Technical Stack:**
- **Input formats:** GeoJSON, DXF, IFC (Revit), KML
- **Processing:** PostGIS spatial operations (ST_Area, ST_Buffer, ST_Intersects, ST_Distance)
- **Rule engine:** Convert provisions → spatial tests
- **Output:** Pass/fail report with spatial visualization

**Workflow:**
1. User uploads site plan (DXF from surveyor or SketchUp GeoJSON export)
2. PlotDetect extracts:
   - Building footprint polygon
   - Lot boundary polygon
   - Driveway, parking, landscaped areas
   - Property address (for provision filtering)
3. Run spatial tests:
   - **FSR:** ST_Area(building_footprint) / ST_Area(lot_boundary) ≤ max_fsr
   - **Site coverage:** ST_Area(building_footprint) / ST_Area(lot_boundary) ≤ 0.6
   - **Setbacks:** ST_Distance(building_footprint, lot_boundary) ≥ [front:6m, side:0.9m, rear:6m]
   - **Landscaping:** ST_Area(landscaped_polygons) / ST_Area(lot_boundary) ≥ 0.2 (20%)
   - **Parking:** COUNT(parking_spaces) ≥ 2, ST_Area(each_space) ≥ 5.5m × 2.4m
   - **Deep soil:** ST_Area(deep_soil_polygons) with min dimension ≥ 3m
4. Generate compliance matrix:
   - ✅ FSR: 0.65 (complies, max 0.7)
   - ❌ Front setback: 5.2m (fails, min 6m) → **0.8m shortfall**
   - ✅ Site coverage: 58% (complies, max 60%)
   - ❌ Landscaping: 18% (fails, min 20%) → **15 sqm shortfall**
5. Return GeoJSON with color-coded geometry:
   - Green polygons: Compliant elements
   - Red polygons: Non-compliant elements with measurements

**Value Proposition:**
- **Architects:** Validate design before submitting DA → zero assessment RFIs
- **Certifiers:** Instant CDC blocker identification with spatial proof
- **Town Planners:** Generate s4.15 assessment with spatial evidence
- **Developers:** Test feasibility scenarios (change FSR, amalgamate lots)

**Defensibility:**
- Requires encoding 47,818 provisions into spatial rules (deep domain expertise)
- Provision text is ambiguous ("landscaping shall be provided") → how to test? This requires human interpretation
- Validation against real DAs builds accuracy over time (moat grows with usage)

**MVP Provisions to Encode (Ashfield R2):**
- FSR (1 rule)
- Height (1 rule)
- Site coverage (1 rule)
- Setbacks: front/side/rear (3 rules)
- Landscaping percentage (1 rule)
- Parking: count and dimensions (2 rules)
- **Total: ~10 core spatial rules for 80% of value**

#### 1.2 3D Building Envelope Generator
**Capability:** Given lot boundary + DCP provisions → generate 3D compliant building envelope

**Technical Stack:**
- **Input:** Lot boundary polygon (from cadastre or user upload)
- **Processing:** PostGIS 3D operations + custom envelope algorithm
- **Visualization:** CesiumJS for web-based 3D rendering
- **Output:** 3D mesh showing maximum compliant building volume

**Algorithm:**
1. Start with lot boundary polygon
2. Apply setback buffers:
   - ST_Buffer(lot_boundary, -6m) → front setback zone
   - ST_Buffer(lot_boundary, -0.9m) → side setback zone
   - ST_Buffer(lot_boundary, -6m) → rear setback zone
   - Intersect buffers → buildable footprint area
3. Extrude buildable area to max height (9m for R2)
4. Apply FSR constraint:
   - Max GFA = lot_area × max_fsr
   - If extruded volume > max GFA, truncate height
5. Generate 3D Tiles for streaming to CesiumJS
6. Overlay on Nearmap aerial imagery + 3D buildings

**Workflow:**
1. User enters address: "35 Albert Street, Ashfield"
2. PlotDetect retrieves lot boundary from cadastre
3. Filters provisions: R2, max FSR 0.7, max height 9m, setbacks 6m/0.9m/6m
4. Generates 3D envelope mesh
5. Displays in CesiumJS with controls:
   - Rotate, zoom, pan
   - Toggle between "max envelope" and "typical design"
   - Show shadow animation (see Horizon 2)

**Value Proposition:**
- **Architects:** See buildable area in 3D before starting concept design
- **Developers:** Understand site capacity instantly (feasibility check)
- **Real Estate Agents:** Show buyers "here's what you can build" in 3D
- **Town Planners:** Visual communication tool for community consultation

**Defensibility:**
- Requires spatial algorithm development (setback logic, FSR vs height optimization)
- 3D visualization infrastructure (CesiumJS hosting, 3D Tiles generation)
- Cadastre integration (requires data partnerships or web scraping Planning Portal)

#### 1.3 Heritage Impact Visualization
**Capability:** Proposed design → 3D visualization in heritage context

**Technical Stack:**
- **Heritage data:** HCA boundaries, heritage item points from PlotDetect database
- **Building data:** NSW 3D buildings (if available) or extrude footprints to typical heights
- **Proposed design:** User-uploaded IFC/DXF converted to 3D mesh
- **Visualization:** CesiumJS with heritage items highlighted

**Workflow:**
1. User uploads proposed design for 10 Railway Parade, Summer Hill (Heritage HCA C95)
2. PlotDetect:
   - Loads heritage HCA boundary polygon
   - Loads nearby heritage items within 100m (ST_Buffer query)
   - Loads existing 3D building context
   - Converts proposed design to 3D mesh
3. Renders in CesiumJS:
   - Heritage HCA boundary: Yellow outline
   - Heritage items: Red markers with significance level
   - Existing buildings: Grey 3D meshes
   - Proposed building: Blue 3D mesh (semi-transparent)
   - User can toggle proposed on/off to see impact
4. Generates comparison images:
   - Before: Existing context
   - After: With proposed development
   - Side-by-side: Visual impact assessment

**Value Proposition:**
- **Heritage Consultants:** Generate SOHI visual impact images in 10 minutes vs 2 hours in SketchUp
- **Architects:** Demonstrate heritage sensitivity to council
- **Town Planners:** Support s4.15(1)(c) heritage impact assessment

**Defensibility:**
- Requires heritage spatial database (PlotDetect already has this)
- 3D building data (partnership opportunity with NSW government or scrape Planning Portal)
- Domain expertise in heritage assessment (which views matter, what scale is appropriate)

---

### HORIZON 2 (12-24 months): Solar, Shadow & Viewshed Analysis
**Goal:** Automated environmental impact assessment (solar access, shadow, visual catchment)

#### 2.1 Solar Access Validation (SEPP Housing 2021)
**Capability:** Proposed design → automated solar access compliance check

**Regulatory Context:**
- SEPP Housing 2021 requires 3 hours solar access to:
  - 50% of private open space (midwinter, 9am-3pm)
  - Living room window of each dwelling
- Critical for dual occupancy, multi-dwelling, apartment DA approval

**Technical Stack:**
- **Solar engine:** GRASS GIS r.sun or custom shadow projection
- **Input:** 3D building mesh + neighboring buildings + latitude/longitude
- **Processing:** Calculate sun position at hourly intervals (9am-3pm, June 21)
- **Output:** Solar access map showing hours of direct sunlight

**Algorithm:**
1. User uploads proposed dual occupancy design for 35 Albert Street
2. PlotDetect extracts:
   - Private open space polygons (2 × 24 sqm)
   - Living room window points
   - Building geometry (roof, walls)
3. Load context:
   - Neighboring building 3D meshes within 50m
   - Lot boundaries and elevations
4. Run r.sun shadow projection:
   - June 21 (midwinter), 9am, 10am, 11am, 12pm, 1pm, 2pm, 3pm
   - For each hour: identify shadowed areas
   - Aggregate: calculate total hours of sunlight per pixel
5. Test SEPP Housing compliance:
   - ✅ Dwelling 1 POS: 68% receives 3+ hours (complies, min 50%)
   - ❌ Dwelling 2 POS: 42% receives 3+ hours (fails, min 50%)
   - ✅ Dwelling 1 living window: 5 hours direct sun (complies)
   - ❌ Dwelling 2 living window: 2 hours direct sun (fails, min 3 hours)
6. Generate report:
   - Solar access heatmap (red = 0 hours, green = 7+ hours)
   - Compliance summary with provision citations
   - Suggested modifications: "Reduce building height by 0.5m to achieve compliance"

**Value Proposition:**
- **Architects:** Validate solar access before DA submission → zero RFIs on SEPP Housing
- **Certifiers:** Instant CDC blocker identification (solar non-compliance)
- **Town Planners:** Automated s4.15(1)(a)(iii) SEPP compliance assessment

**Defensibility:**
- Requires solar calculation engine (GRASS GIS integration or custom algorithm)
- 3D building context data (neighboring buildings)
- Provision-specific testing logic (SEPP Housing 3-hour rule, ADG apartment rules)

#### 2.2 Shadow Impact Assessment
**Capability:** Proposed design → shadow diagrams for neighbor impact assessment

**Regulatory Context:**
- Councils assess "overshadowing of adjacent properties" under s4.15
- Heritage Impact Assessments require shadow diagrams on heritage items
- ADG apartments: shadow analysis on public open space

**Technical Stack:**
- **Shadow engine:** GRASS GIS r.sun or UMEP Shadow Generator
- **Visualization:** 2D shadow diagrams + 3D CesiumJS animation
- **Input:** Proposed building 3D mesh + neighboring properties

**Workflow:**
1. User uploads proposed development for 35 Albert Street
2. PlotDetect identifies neighboring properties within 50m
3. Runs shadow projection:
   - Midwinter (June 21): 9am, 12pm, 3pm
   - Equinox (March 21): 9am, 12pm, 3pm
   - Midsummer (December 21): 9am, 12pm, 3pm
4. Generates shadow diagrams:
   - Plan view showing shadow extent overlaid on neighboring lots
   - 3D CesiumJS animation showing shadow movement throughout day
5. Quantifies impact:
   - "33 Albert Street: 15% of backyard receives additional 2 hours shadow in midwinter"
   - "37 Albert Street: No additional overshadowing"
6. Heritage-specific:
   - If heritage item within 50m, generate heritage shadow diagrams
   - Test against heritage provision: "New development shall not overshadow significant heritage facades"

**Value Proposition:**
- **Architects:** Demonstrate amenity impact to council (required for DA)
- **Heritage Consultants:** Auto-generate SOHI shadow diagrams (30 min vs 3 hours)
- **Town Planners:** Support s4.15(1)(b) amenity impact assessment

**Defensibility:**
- Requires shadow calculation engine
- Heritage provision database to identify which items need shadow analysis
- Domain expertise: What shadow impact is "acceptable"? (requires case law / DA outcome analysis)

#### 2.3 Heritage Viewshed Analysis
**Capability:** Proposed design → visual catchment map showing where it's visible from heritage viewpoints

**Regulatory Context:**
- Heritage Impact Assessments must address "visual impact on heritage item setting"
- Some LEPs have "view corridor" clauses protecting views to/from heritage items
- Design excellence precincts (Barangaroo, Green Square) protect public domain views

**Technical Stack:**
- **Viewshed engine:** GRASS GIS r.viewshed or QGIS Visibility Analysis plugin
- **Input:** Heritage item viewpoints + proposed building 3D mesh + DEM (terrain model)
- **Output:** Map showing areas from which proposed building is visible

**Algorithm:**
1. User uploads proposed development for heritage site (10 Railway Parade, Summer Hill HCA C95)
2. PlotDetect identifies heritage context:
   - Heritage HCA boundary
   - Individual heritage items within 200m
   - Significant public viewpoints (street corners, parks, railway station)
3. For each viewpoint, run r.viewshed:
   - Input: Viewpoint coordinates (x, y, observer height 1.6m)
   - Target: Proposed building 3D mesh
   - DEM: NSW elevation model
   - Output: Boolean raster (visible = 1, not visible = 0)
4. Aggregate viewsheds → visual catchment map:
   - Red zones: Proposed building visible from heritage items
   - Yellow zones: Visible from public domain
   - Green zones: Not visible (screened by existing buildings/trees)
5. Generate heritage impact report:
   - "Proposed development visible from Heritage Item #123 (Campbell Street Federation cottage, State Significant)"
   - "Proposed roofline intrudes into view corridor from Railway Parade to heritage church spire"
   - "Mitigation: Reduce height by 1.5m or setback upper storey 3m from Campbell St boundary"

**Value Proposition:**
- **Heritage Consultants:** Automate visual impact assessment (1 hour vs 1 day manual photography + photomontage)
- **Architects:** Identify visual impact issues before DA submission
- **Town Planners:** Support s4.15(1)(c) heritage impact assessment with spatial evidence

**Defensibility:**
- Requires heritage viewpoint database (which views are "significant"?)
- DEM integration (NSW government elevation data)
- Domain expertise: Which viewshed results matter for heritage assessment?

---

### HORIZON 3 (24-36 months): AI-Powered Site Discovery & Predictive Compliance
**Goal:** From reactive ("check this site") to proactive ("find the best sites") + predictive analytics

#### 3.1 Development Site Finder
**Capability:** Search "Find me all R3 lots >600 sqm, <800m to train station, no heritage, FSR >0.75" → ranked list

**Technical Stack:**
- **Database:** PostGIS with cadastre, zoning, transport, heritage, constraints layers
- **Query engine:** Spatial SQL with scoring algorithm
- **Frontend:** Map interface with filter sliders

**Workflow:**
1. User (developer) sets criteria:
   - Zone: R3, R4, B4
   - Min lot size: 600 sqm
   - Max distance to train station: 800m
   - Constraints: No heritage, no flood, no bushfire
   - Min FSR: 0.75
   - Min height: 12m
2. PlotDetect runs PostGIS query:
   ```sql
   SELECT
     cadastre.address,
     cadastre.lot_size,
     zoning.zone,
     zoning.max_fsr,
     zoning.max_height,
     ST_Distance(cadastre.geom, transport.geom) as dist_to_station,
     constraints.heritage,
     constraints.flood,
     constraints.bushfire,
     -- Scoring
     (cadastre.lot_size * zoning.max_fsr * zoning.max_height) as development_potential_score
   FROM cadastre
   JOIN zoning ON ST_Intersects(cadastre.geom, zoning.geom)
   LEFT JOIN transport ON ST_DWithin(cadastre.geom, transport.geom, 800)
   LEFT JOIN constraints ON cadastre.lot_id = constraints.lot_id
   WHERE zoning.zone IN ('R3', 'R4', 'B4')
     AND cadastre.lot_size >= 600
     AND ST_DWithin(cadastre.geom, transport.geom, 800)
     AND constraints.heritage = FALSE
     AND constraints.flood = FALSE
     AND constraints.bushfire = FALSE
     AND zoning.max_fsr >= 0.75
   ORDER BY development_potential_score DESC
   LIMIT 50;
   ```
3. Returns ranked list:
   - 1. **123 Parramatta Road, Ashfield** - 850 sqm, R4, FSR 1.0, Height 15m, 450m to station → Score: 12,750
   - 2. **45 Frederick Street, Ashfield** - 720 sqm, R3, FSR 0.9, Height 12m, 620m to station → Score: 7,776
4. User clicks address → full PlotDetect assessment (provisions, envelope, feasibility)

**Value Proposition:**
- **Developers:** Find acquisition targets proactively (competitive advantage)
- **Real Estate Agents:** Identify off-market development opportunities
- **Investors:** Data-driven site selection for development portfolios

**Defensibility:**
- Requires comprehensive spatial database (cadastre + zoning + transport + constraints)
- Scoring algorithm based on development economics (FSR × height × land value → yield)
- Cadastre data is hard to acquire (requires scraping Planning Portal or data partnership with NSW government)

#### 3.2 Amalgamation Opportunity Finder
**Capability:** Given subject lot → identify adjacent lot amalgamation scenarios with yield uplift

**Technical Stack:**
- **Topology:** PostGIS topology for cadastre (shared edges, neighbors)
- **Yield model:** FSR × lot size → GFA → unit count → revenue
- **Output:** "Amalgamate with 37 Albert St → +45% yield ($850k revenue uplift)"

**Algorithm:**
1. User selects subject lot: 35 Albert Street, Ashfield (736 sqm, R2, FSR 0.7)
2. PlotDetect identifies adjacent lots using PostGIS topology:
   - ST_Touches(subject_lot.geom, cadastre.geom) → 33 Albert St, 37 Albert St
3. For each adjacent lot, calculate amalgamation scenario:
   - **Scenario A:** 35 + 37 Albert St
     - Combined area: 736 + 680 = 1,416 sqm
     - Max GFA: 1,416 × 0.7 = 991 sqm (vs 515 sqm single lot)
     - Unit potential: 5 × 2-bed apartments (vs 2 townhouses)
     - Revenue uplift: 5 × $950k - 2 × $850k = $3,050k vs $1,700k = **+79% revenue**
   - **Scenario B:** 35 + 33 Albert St
     - Combined area: 736 + 590 = 1,326 sqm
     - Max GFA: 1,326 × 0.7 = 928 sqm
     - Unit potential: 4 × 2-bed apartments
     - Revenue uplift: +65%
4. Rank scenarios by yield uplift
5. Generate report with 3D envelope visualization of amalgamated site

**Value Proposition:**
- **Developers:** Identify site assembly opportunities (competitive advantage)
- **Landowners:** Understand amalgamation value for negotiation
- **Real Estate Agents:** Advisory service for sellers ("sell jointly with neighbor for +65% value")

**Defensibility:**
- Requires cadastre topology (expensive to build, requires data partnerships)
- Yield modeling algorithm (unit mix optimization based on GFA, market pricing)
- Provision-aware (some zones restrict amalgamation, some encourage it)

#### 3.3 Predictive DA Approval Probability
**Capability:** Upload design → "72% approval probability" based on historical DA outcomes

**Technical Stack:**
- **Training data:** Historical DA outcomes (approved/refused) with design attributes
- **Model:** Gradient boosting (XGBoost) or neural network
- **Features:** FSR ratio, setback compliance, heritage proximity, objections count, design quality
- **Output:** Approval probability + risk factors

**Data Collection:**
1. Scrape council DA registers:
   - DA number, address, description, outcome (approved/refused/withdrawn)
   - Design attributes: FSR, height, use, site area
   - Assessment attributes: Objections count, officer recommendation, refusal reasons
2. Join with PlotDetect data:
   - Provision compliance (how many provisions did the design comply with?)
   - Heritage context (distance to heritage item, HCA yes/no)
   - Precinct (some precincts have higher approval rates)
3. Build training dataset:
   - 10,000 historical DAs across Inner West councils
   - Features: fsr_ratio, height_ratio, setback_front_compliance, setback_side_compliance, heritage_hca, objections_count, provision_compliance_rate
   - Label: approved (1) or refused (0)

**Model Training:**
```python
import xgboost as xgb

# Features
X = [
  'fsr_ratio',  # actual_fsr / max_fsr (0.0-1.5, >1.0 = non-compliant)
  'height_ratio',  # actual_height / max_height
  'setback_front_compliance',  # bool
  'setback_side_compliance',  # bool
  'setback_rear_compliance',  # bool
  'landscaping_compliance',  # bool
  'heritage_hca',  # bool (in HCA = higher refusal risk)
  'heritage_item_within_50m',  # bool
  'objections_count',  # integer
  'provision_compliance_rate',  # float 0.0-1.0 (% of provisions complied with)
  'council',  # categorical (some councils more strict)
  'use_type',  # categorical (dual_occ, multi_dwelling, subdivision)
]

# Target
y = df['approved']  # 1 = approved, 0 = refused

# Train model
model = xgb.XGBClassifier(objective='binary:logistic')
model.fit(X_train, y_train)

# Predict approval probability
approval_prob = model.predict_proba(X_test)[:, 1]
```

**Workflow:**
1. User uploads proposed dual occupancy design for 35 Albert Street
2. PlotDetect runs spatial compliance validation (from Horizon 1)
3. Extracts features:
   - fsr_ratio: 0.65 / 0.7 = 0.93 (compliant)
   - height_ratio: 8.5 / 9.0 = 0.94 (compliant)
   - setback_front_compliance: False (5.2m vs 6m required)
   - setback_side_compliance: True
   - setback_rear_compliance: True
   - landscaping_compliance: False (18% vs 20% required)
   - heritage_hca: False
   - heritage_item_within_50m: False
   - provision_compliance_rate: 0.88 (350/395 provisions complied)
   - council: Ashfield
   - use_type: dual_occ
4. Model predicts: **68% approval probability**
5. Generates report:
   - "**68% approval probability** (based on 1,247 similar Ashfield dual occupancy DAs)"
   - "**Risk factors:**"
     - "Front setback non-compliance (5.2m vs 6m) reduces approval probability by 15%"
     - "Landscaping non-compliance (18% vs 20%) reduces probability by 8%"
   - "**Recommendations:**"
     - "Increase front setback to 6m → approval probability increases to 79%"
     - "Add 15 sqm landscaping → approval probability increases to 75%"
     - "Fix both → approval probability increases to 86%"

**Value Proposition:**
- **Developers:** De-risk DA submission (don't proceed with <60% approval probability)
- **Architects:** Optimize design for approval before submitting
- **Town Planners:** Advise clients on approval likelihood

**Defensibility:**
- Requires historical DA outcome dataset (expensive to scrape and maintain)
- Model training expertise (which features matter, how to encode them)
- Continuous learning: Model improves with each new DA outcome
- Network effect: More DAs assessed → more outcome data → better predictions

---

## Technical Architecture: The Full Stack

### Data Layer (PostGIS + PostgreSQL)

**Core Tables:**
- `regulatory_provisions` (47,818 rows) - existing PlotDetect provision database
- `cadastre` - lot boundaries, lot size, address (scraped from Planning Portal or data partnership)
- `zoning` - zone polygons with max FSR, max height, permitted uses
- `heritage_items` - heritage item points/polygons with significance level
- `heritage_conservation_areas` - HCA polygons with slugs (existing)
- `precincts` - precinct polygons with v2_precinct_id (existing)
- `transport_nodes` - train stations, light rail stops, bus stops (for TOD analysis)
- `constraints` - flood, bushfire, contamination, acid sulfate soil polygons
- `buildings_3d` - 3D building footprints with heights (from NSW government or inferred)
- `development_applications` - historical DA outcomes for predictive modeling
- `elevation_dem` - digital elevation model raster for viewshed/shadow analysis

**Spatial Indexes:**
- GIST indexes on all geometry columns for fast ST_Intersects queries
- Topology for cadastre (shared edges for adjacency queries)

**Key Spatial Operations:**
- `ST_Intersects(lot, zone)` - which zone is this lot in?
- `ST_Buffer(lot, -6)` - apply setback to create buildable area
- `ST_Area(polygon)` - calculate FSR, site coverage, landscaping %
- `ST_Distance(lot, heritage_item)` - proximity to heritage
- `ST_DWithin(lot, train_station, 800)` - TOD distance filter
- `ST_Touches(lot1, lot2)` - find adjacent lots for amalgamation
- `ST_3DIntersects(building, height_plane)` - 3D height compliance

### Processing Layer (Python + Spatial Libraries)

**Core Libraries:**
- **PostGIS:** Spatial database engine
- **GDAL/OGR:** Geometry format conversion (DXF → GeoJSON, IFC → PostGIS)
- **Shapely:** Python geometry manipulation
- **GeoPandas:** Spatial dataframes for analysis
- **GRASS GIS (r.sun, r.viewshed):** Solar and viewshed analysis via Python bindings
- **IfcOpenShell:** Parse Revit IFC files to extract building geometry
- **ezdxf:** Parse DXF files from surveyor/architect
- **XGBoost / scikit-learn:** Predictive DA approval modeling

**Processing Workflows:**

1. **Design Upload Processing:**
   ```python
   # DXF upload
   import ezdxf
   doc = ezdxf.readfile("site_plan.dxf")

   # Extract building footprint from POLYLINE layer
   building_footprint = extract_polylines(doc, layer="BUILDING")

   # Convert to GeoJSON
   geojson = shapely_to_geojson(building_footprint)

   # Insert into PostGIS
   cursor.execute("""
     INSERT INTO user_designs (user_id, geom, upload_date)
     VALUES (%s, ST_GeomFromGeoJSON(%s), NOW())
   """, (user_id, geojson))
   ```

2. **Spatial Compliance Validation:**
   ```python
   # Get lot boundary and provisions
   lot_geom = get_lot_boundary(address)
   provisions = get_provisions(address)

   # Extract rules from provisions
   rules = parse_spatial_rules(provisions)
   # Example: {"front_setback_min": 6.0, "max_fsr": 0.7, "max_site_coverage": 0.6}

   # Test building against rules
   results = {}

   # FSR test
   building_gfa = query_db("SELECT ST_Area(geom) FROM user_designs WHERE id = %s", design_id)
   lot_area = query_db("SELECT ST_Area(geom) FROM cadastre WHERE address = %s", address)
   actual_fsr = building_gfa / lot_area
   results['fsr'] = {
     'complies': actual_fsr <= rules['max_fsr'],
     'actual': actual_fsr,
     'required': rules['max_fsr']
   }

   # Setback test
   front_setback_actual = query_db("""
     SELECT ST_Distance(
       (SELECT geom FROM user_designs WHERE id = %s),
       (SELECT ST_Boundary(geom) FROM cadastre WHERE address = %s AND boundary_type = 'front')
     )
   """, (design_id, address))
   results['front_setback'] = {
     'complies': front_setback_actual >= rules['front_setback_min'],
     'actual': front_setback_actual,
     'required': rules['front_setback_min']
   }

   return results
   ```

3. **3D Building Envelope Generation:**
   ```python
   # Get lot boundary
   lot_geom = get_lot_boundary(address)

   # Apply setback buffers
   buildable_area = query_db("""
     WITH setbacks AS (
       SELECT
         ST_Buffer(geom, -6.0, 'endcap=flat join=mitre') as front,
         ST_Buffer(geom, -0.9, 'side=left') as side_left,
         ST_Buffer(geom, -0.9, 'side=right') as side_right,
         ST_Buffer(geom, -6.0, 'endcap=flat join=mitre') as rear
       FROM cadastre WHERE address = %s
     )
     SELECT ST_Intersection(front, side_left, side_right, rear) as buildable
     FROM setbacks
   """, address)

   # Extrude to max height
   max_height = get_max_height(address)  # 9m for R2
   envelope_3d = extrude_polygon(buildable_area, max_height)

   # Convert to 3D Tiles for CesiumJS
   tiles = generate_3d_tiles(envelope_3d)

   return tiles
   ```

4. **Solar Access Analysis:**
   ```python
   import grass.script as gscript

   # Prepare DSM (Digital Surface Model) with buildings
   dsm = create_dsm(buildings_3d, elevation_dem)

   # Run r.sun for June 21 (midwinter)
   for hour in range(9, 16):  # 9am to 3pm
     gscript.run_command(
       'r.sun',
       elevation='dsm',
       aspect='aspect',
       slope='slope',
       day=172,  # June 21
       time=hour,
       beam_rad=f'beam_rad_{hour}',
       diff_rad=f'diff_rad_{hour}'
     )

   # Aggregate hours of direct sunlight
   gscript.mapcalc("""
     solar_hours =
       (beam_rad_9 > 0) + (beam_rad_10 > 0) + (beam_rad_11 > 0) +
       (beam_rad_12 > 0) + (beam_rad_13 > 0) + (beam_rad_14 > 0) + (beam_rad_15 > 0)
   """)

   # Test compliance: 50% of POS must receive 3+ hours
   pos_geom = get_private_open_space(design_id)
   compliance = query_grass("""
     SELECT
       SUM(CASE WHEN solar_hours >= 3 THEN pixel_area ELSE 0 END) / SUM(pixel_area) as percentage_compliant
     FROM solar_hours
     WHERE ST_Intersects(pixel_geom, %s)
   """, pos_geom)

   return compliance >= 0.5  # SEPP Housing requirement
   ```

### API Layer (Next.js API Routes)

**New Endpoints:**

```typescript
// Design upload and validation
POST /api/compliance/validate-design
Request: {
  address: string,
  design: GeoJSON | File (DXF/IFC),
  testTypes: ['fsr', 'setbacks', 'landscaping', 'solar', 'shadow', 'viewshed']
}
Response: {
  compliance: {
    fsr: { complies: boolean, actual: number, required: number },
    front_setback: { complies: boolean, actual: number, required: number },
    ...
  },
  visualization: {
    compliantGeometry: GeoJSON,  // green polygons
    nonCompliantGeometry: GeoJSON,  // red polygons
    measurements: GeoJSON  // dimension lines
  },
  recommendations: string[]
}

// 3D building envelope
GET /api/envelope/generate?address={address}
Response: {
  envelope3D: URL,  // 3D Tiles URL for CesiumJS
  buildableArea: GeoJSON,
  maxGFA: number,
  maxHeight: number
}

// Solar access analysis
POST /api/solar/analyze
Request: {
  designId: string,
  testDate: string,  // "2026-06-21" for midwinter
  analysisType: 'sepp_housing' | 'neighbor_impact' | 'pv_potential'
}
Response: {
  compliance: {
    dwelling1_pos: { percentage_compliant: number, hours_min: number, complies: boolean },
    dwelling1_living_window: { hours: number, complies: boolean }
  },
  solarMap: URL,  // raster heatmap
  shadowDiagrams: { time: string, imageUrl: string }[]
}

// Site finder
POST /api/sites/search
Request: {
  filters: {
    zones: string[],
    minLotSize: number,
    maxDistanceToTransport: number,
    constraints: { heritage: boolean, flood: boolean, bushfire: boolean },
    minFSR: number
  },
  sortBy: 'development_potential' | 'proximity_to_transport' | 'lot_size'
}
Response: {
  sites: {
    address: string,
    lotSize: number,
    zone: string,
    maxFSR: number,
    maxHeight: number,
    distanceToStation: number,
    developmentPotentialScore: number
  }[],
  totalCount: number
}

// Amalgamation opportunities
GET /api/amalgamation/opportunities?address={address}
Response: {
  scenarios: {
    adjacentAddress: string,
    combinedArea: number,
    yieldUplift: number,
    revenueUplift: number,
    envelope3D: URL
  }[]
}

// Predictive approval probability
POST /api/prediction/approval-probability
Request: {
  designId: string,
  address: string
}
Response: {
  approvalProbability: number,  // 0.0 - 1.0
  riskFactors: {
    factor: string,
    impact: number,  // percentage point reduction
    recommendation: string
  }[],
  comparableDataPoints: number  // "based on 1,247 similar DAs"
}
```

### Frontend Layer (CesiumJS + OpenLayers + React)

**3D Visualization (CesiumJS):**
```typescript
import { Viewer, Cesium3DTileset, Entity } from 'cesium';

// Initialize viewer
const viewer = new Viewer('cesiumContainer', {
  terrainProvider: await createWorldTerrainAsync(),
  baseLayerPicker: false
});

// Load 3D building envelope
const envelope = await Cesium3DTileset.fromUrl('/api/envelope/tiles/35-albert-street');
viewer.scene.primitives.add(envelope);

// Load heritage context
const heritageItems = await fetch('/api/heritage/items?address=35 Albert Street');
heritageItems.forEach(item => {
  viewer.entities.add({
    position: Cesium.Cartesian3.fromDegrees(item.longitude, item.latitude),
    point: { pixelSize: 10, color: Cesium.Color.RED },
    label: { text: item.name, font: '14px sans-serif' }
  });
});

// Load proposed design
const proposedDesign = await fetch('/api/designs/123/3d-tiles');
const designTileset = await Cesium3DTileset.fromUrl(proposedDesign.url);
designTileset.style = new Cesium3DTileStyle({
  color: "color('blue', 0.5)"  // semi-transparent blue
});
viewer.scene.primitives.add(designTileset);

// Shadow animation
const shadowLayer = viewer.imageryLayers.addImageryProvider(
  new SingleTileImageryProvider({ url: '/api/solar/shadow-sequence' })
);
// Animate through time steps
```

**2D Compliance Visualization (OpenLayers):**
```typescript
import Map from 'ol/Map';
import VectorLayer from 'ol/layer/Vector';
import GeoJSON from 'ol/format/GeoJSON';

// Create map
const map = new Map({
  target: 'map',
  view: new View({ center: [lng, lat], zoom: 18 })
});

// Load compliance results
const complianceData = await fetch('/api/compliance/validate-design', { ... });

// Add compliant geometry (green)
const compliantLayer = new VectorLayer({
  source: new VectorSource({
    features: new GeoJSON().readFeatures(complianceData.compliantGeometry)
  }),
  style: new Style({ fill: new Fill({ color: 'rgba(0, 255, 0, 0.3)' }) })
});
map.addLayer(compliantLayer);

// Add non-compliant geometry (red) with labels
const nonCompliantLayer = new VectorLayer({
  source: new VectorSource({
    features: new GeoJSON().readFeatures(complianceData.nonCompliantGeometry)
  }),
  style: feature => new Style({
    fill: new Fill({ color: 'rgba(255, 0, 0, 0.3)' }),
    text: new Text({
      text: feature.get('shortfall'),  // "0.8m shortfall"
      font: '12px sans-serif',
      fill: new Fill({ color: 'red' })
    })
  })
});
map.addLayer(nonCompliantLayer);
```

---

## Business Model & Pricing

### Current Model (Freemium / Pay-per-Assessment)
- **Free tier:** Basic property lookup, zone/FSR/height, limited provisions
- **Pro tier ($49/month):** Unlimited assessments, all provisions, PDF citations, heritage filtering
- **Enterprise ($499/month):** API access, white-label, bulk assessments

### New Model (Value-Based Pricing for Spatial Capabilities)

#### Tier 1: Compliance Validation ($149/month)
- Design upload & spatial validation (FSR, setbacks, landscaping, parking)
- Compliance report with pass/fail matrix
- 2D visualization of compliant/non-compliant elements
- Up to 20 designs/month
- **Target:** Architects, certifiers, town planners

#### Tier 2: 3D & Environmental ($299/month)
- All Tier 1 features
- 3D building envelope generation
- Solar access analysis (SEPP Housing compliance)
- Shadow impact assessment
- Heritage context visualization
- Up to 50 designs/month
- **Target:** Architects, heritage consultants, developers

#### Tier 3: Site Intelligence ($599/month)
- All Tier 2 features
- Development site finder (unlimited searches)
- Amalgamation opportunity finder
- Viewshed analysis for heritage impact
- Predictive DA approval probability
- Up to 100 designs/month
- **Target:** Developers, investors, real estate agents

#### Enterprise: Custom ($2,000+/month)
- Unlimited designs and searches
- API access for integration with Revit/SketchUp
- White-label for councils/consultancies
- Dedicated support and custom provision encoding
- Historical DA outcome data access
- **Target:** Large consultancies, councils, PropTech platforms

### Revenue Projections (Conservative)

**Year 1 (Horizon 1 launch):**
- 50 Tier 1 subscribers × $149 × 12 = $89,400
- 20 Tier 2 subscribers × $299 × 12 = $71,760
- 5 Enterprise × $2,000 × 12 = $120,000
- **Total: $281,160**

**Year 2 (Horizon 2 launch):**
- 150 Tier 1 × $149 × 12 = $268,200
- 75 Tier 2 × $299 × 12 = $268,650
- 30 Tier 3 × $599 × 12 = $215,640
- 10 Enterprise × $2,500 × 12 = $300,000
- **Total: $1,052,490**

**Year 3 (Horizon 3 launch + expansion to other councils):**
- 400 Tier 1 × $149 × 12 = $715,200
- 200 Tier 2 × $299 × 12 = $717,600
- 100 Tier 3 × $599 × 12 = $718,800
- 25 Enterprise × $3,000 × 12 = $900,000
- **Total: $3,051,600**

---

## Competitive Moat Analysis

### What Makes This Defensible Against Vibe Coding Agents?

**1. Data Moat (Years to Replicate)**
- 47,818 provisions curated with v2 taxonomy → spatial rule logic
- Heritage HCA boundaries (not publicly available, requires scraping Planning Portal)
- Cadastre topology (requires data partnerships or expensive scraping)
- Historical DA outcomes (10,000+ DAs with outcomes, manual collection)
- 3D building heights (not publicly available, requires inference or partnerships)
- **Moat strength:** ⭐⭐⭐⭐⭐ (5/5) - Data curation requires human domain expertise

**2. Domain Expertise Moat (Hard to Encode)**
- Converting ambiguous provision text → precise spatial tests
  - Example: "landscaping shall be provided in a manner that contributes to amenity"
  - How do you test this? Requires understanding case law, DA outcomes, planner interpretation
- Understanding which provisions are spatial vs policy
  - Example: "development should be compatible with heritage character" vs "setback min 6m"
  - First is subjective, second is testable
- Heritage viewshed: Which viewpoints matter? Not all views are equal (domain expertise)
- **Moat strength:** ⭐⭐⭐⭐ (4/5) - AI can parse text but struggles with ambiguity

**3. Technical Moat (Complex Infrastructure)**
- PostGIS spatial database with topology
- GRASS GIS integration for solar/viewshed analysis
- CesiumJS 3D visualization with streaming 3D Tiles
- IFC/DXF parsers for BIM/CAD integration
- Real-time spatial queries at scale (GIST indexes, query optimization)
- **Moat strength:** ⭐⭐⭐ (3/5) - Open source tools available but integration is complex

**4. Integration Moat (Industry Relationships)**
- Revit plugin for BIM export to PlotDetect
- SketchUp plugin for 3D model validation
- Cadastre data partnerships (NSW government or Planning Portal)
- Council DA register access (may require formal partnerships)
- **Moat strength:** ⭐⭐⭐⭐ (4/5) - Partnerships take years to build

**5. Accuracy Moat (Network Effects)**
- Spatial rule validation against real DA outcomes
- User feedback: "This compliance report was wrong" → improve rule logic
- Predictive model improves with each new DA outcome
- **Moat strength:** ⭐⭐⭐⭐⭐ (5/5) - Accuracy compounds over time

**6. User Lock-In Moat (Workflow Integration)**
- Architects integrate PlotDetect into DA workflow (upload → validate → submit)
- Developers build internal processes around site finder
- Consultancies white-label for clients (switching cost = rebuild client reports)
- **Moat strength:** ⭐⭐⭐⭐ (4/5) - Workflow integration creates stickiness

### Why Vibe Coding Agents Can't Easily Replicate This

**What vibe coding can do:**
- Build basic UI for displaying provisions ✅
- Parse DCP PDFs and extract text ✅
- Create simple spatial queries (ST_Intersects) ✅
- Generate basic 2D maps ✅

**What vibe coding struggles with:**
- Curating 47,818 provisions with actionable/informational flagging ❌ (requires domain expertise)
- Converting provision text to spatial rule logic ❌ (ambiguous language)
- Acquiring cadastre data ❌ (no public API, requires scraping or partnerships)
- Building accurate solar/shadow/viewshed engines ❌ (requires GIS expertise + DEM integration)
- Validating accuracy against real DA outcomes ❌ (requires historical data collection)
- BIM integration ❌ (requires Revit/SketchUp SDK expertise)

**Example of difficulty:**

*Provision text:* "Parking shall be setback a minimum of 1m from the front boundary, with a maximum gradient of 1 in 4, and provided with permeable paving or connection to stormwater drainage."

*Vibe coding output:* "Oh, this is about parking setbacks, let me extract '1m' and '1 in 4'"

*PlotDetect spatial rule logic:*
```sql
-- Test 1: Setback
SELECT ST_Distance(parking_space.geom, lot_boundary.front_edge) >= 1.0

-- Test 2: Gradient (requires elevation data at parking space)
SELECT (max_elevation - min_elevation) / ST_Length(parking_space.geom) <= 0.25  -- 1:4 = 25%

-- Test 3: Surface type (requires attribute data from BIM/CAD)
SELECT parking_space.surface_type IN ('permeable_paving', 'drainage_connected')
```

This requires:
1. Parsing provision into 3 separate tests
2. Understanding that "1 in 4" = 25% gradient
3. Knowing that gradient requires elevation data (DEM or design elevations)
4. Knowing that surface type comes from BIM attributes, not geometry
5. Knowing which lot edge is "front" (requires cadastre topology + street frontage identification)

**Vibe coding agents can't reliably do this level of domain-aware parsing.**

---

## Implementation Roadmap

### Horizon 1 (Months 1-12): Spatial Compliance Engine

**Q1 2026 (Months 1-3): Foundation**
- [ ] PostGIS database schema: cadastre, zoning, buildings_3d tables
- [ ] Cadastre data acquisition: Scrape Planning Portal or partnership with NSW Spatial Services
- [ ] DXF parser: ezdxf integration for site plan upload
- [ ] Spatial rule engine: Core logic for FSR, setbacks, site coverage tests
- [ ] API endpoint: POST /api/compliance/validate-design
- [ ] Frontend: Design upload UI with drag-drop DXF/GeoJSON

**Q2 2026 (Months 4-6): Validation & Visualization**
- [ ] OpenLayers integration: 2D compliance visualization (green/red polygons)
- [ ] Rule encoding: 10 core Ashfield R2 provisions (FSR, setbacks, landscaping, parking)
- [ ] Compliance report: PDF generation with pass/fail matrix + recommendations
- [ ] Testing: Validate against 50 real approved DAs (accuracy check)
- [ ] Beta launch: 20 architect/planner beta users

**Q3 2026 (Months 7-9): 3D Building Envelope**
- [ ] Buildable area algorithm: PostGIS setback buffers + FSR optimization
- [ ] 3D extrusion: Convert buildable area → 3D mesh
- [ ] CesiumJS integration: Web-based 3D visualization
- [ ] 3D Tiles: Streaming format for large city models
- [ ] API endpoint: GET /api/envelope/generate
- [ ] Frontend: Interactive 3D envelope viewer with controls

**Q4 2026 (Months 10-12): Heritage Context**
- [ ] 3D building data: Scrape/infer building heights for Inner West
- [ ] Heritage visualization: CesiumJS with heritage items + HCA boundaries
- [ ] Proposed design overlay: Upload IFC/DXF → display in heritage context
- [ ] Comparison views: Before/after, side-by-side
- [ ] Public launch: Tier 1 ($149/month) + Tier 2 ($299/month) pricing
- [ ] Goal: 50 paying subscribers by end of Q4

### Horizon 2 (Months 13-24): Environmental Impact Analysis

**Q1 2027 (Months 13-15): Solar Access**
- [ ] GRASS GIS integration: r.sun Python bindings
- [ ] DSM creation: Buildings_3d + DEM → digital surface model
- [ ] Solar analysis: June 21 (midwinter) 9am-3pm hourly shadow projection
- [ ] SEPP Housing validation: 3 hours to 50% of POS, living room window
- [ ] API endpoint: POST /api/solar/analyze
- [ ] Frontend: Solar heatmap overlay + compliance summary

**Q2 2027 (Months 16-18): Shadow Impact**
- [ ] Multi-date shadow: June 21, March 21, December 21
- [ ] Neighbor impact quantification: "15% of backyard receives additional 2 hours shadow"
- [ ] Heritage shadow diagrams: Auto-generate for heritage items within 50m
- [ ] 3D shadow animation: CesiumJS time-slider showing shadow movement
- [ ] PDF report: Shadow diagrams for DA submission

**Q3 2027 (Months 19-21): Viewshed Analysis**
- [ ] GRASS GIS r.viewshed: Python integration
- [ ] DEM integration: NSW elevation model download/storage
- [ ] Heritage viewpoint database: Identify significant viewpoints (manual curation + community input)
- [ ] Visual catchment maps: Aggregate viewsheds → "visible from heritage item" zones
- [ ] API endpoint: POST /api/viewshed/analyze
- [ ] Frontend: Viewshed map overlay + heritage impact report

**Q4 2027 (Months 22-24): Tier 3 Launch**
- [ ] Package all Horizon 2 features into Tier 2 ($299/month)
- [ ] Marketing: Case studies from beta users
- [ ] Goal: 75 Tier 2 subscribers, 150 Tier 1 subscribers

### Horizon 3 (Months 25-36): AI-Powered Site Discovery

**Q1 2028 (Months 25-27): Site Finder**
- [ ] Comprehensive spatial database: Cadastre + zoning + transport + constraints for Inner West
- [ ] PostGIS spatial queries: Distance to transport, constraint filtering, ranking algorithm
- [ ] Development potential scoring: FSR × height × lot size → GFA → unit count → revenue
- [ ] API endpoint: POST /api/sites/search
- [ ] Frontend: Map-based site finder with filter sliders

**Q2 2028 (Months 28-30): Amalgamation Opportunities**
- [ ] Cadastre topology: Build topological adjacency for all Inner West lots
- [ ] Amalgamation scenarios: For each lot, test all adjacent lot combinations
- [ ] Yield modeling: Combined FSR → unit mix optimization → revenue uplift
- [ ] API endpoint: GET /api/amalgamation/opportunities
- [ ] Frontend: Amalgamation scenario comparison with 3D envelopes

**Q3 2028 (Months 31-33): Predictive DA Approval**
- [ ] DA outcome data collection: Scrape Ashfield, Leichhardt, Marrickville DA registers (target: 10,000 DAs)
- [ ] Feature engineering: Extract design attributes, compliance metrics, context factors
- [ ] Model training: XGBoost classifier for approval probability
- [ ] Validation: Test on held-out 2,000 DAs (target: >75% accuracy)
- [ ] API endpoint: POST /api/prediction/approval-probability
- [ ] Frontend: Approval probability dashboard with risk factors

**Q4 2028 (Months 34-36): Tier 3 Launch + Council Expansion**
- [ ] Tier 3 pricing: $599/month with site finder + amalgamation + predictive
- [ ] Council expansion: Extend cadastre, zoning, DA outcome data to 10 additional Sydney councils
- [ ] Enterprise tier: Custom pricing for large consultancies (white-label, API access)
- [ ] Goal: 100 Tier 3 subscribers, 200 Tier 2, 400 Tier 1, 25 Enterprise
- [ ] **Total revenue target: $3M ARR**

---

## Risk Mitigation

### Technical Risks

**Risk 1: Cadastre data acquisition difficult**
- **Mitigation:** Start with user-uploaded lot boundaries (GeoJSON from surveyor), build cadastre database incrementally
- **Mitigation:** Partnership with NSW Spatial Services or Planning Portal for official cadastre access

**Risk 2: Spatial rule encoding inaccurate**
- **Mitigation:** Validate all rules against approved DAs, iterate based on false positives/negatives
- **Mitigation:** User feedback loop: "Report incorrect compliance result" → manual review → fix rule logic

**Risk 3: Solar/viewshed analysis computationally expensive**
- **Mitigation:** Pre-compute DSM/DEM for Inner West (one-time cost), cache results
- **Mitigation:** Run analyses asynchronously with email notification when complete

**Risk 4: BIM/CAD integration complex**
- **Mitigation:** Start with DXF (simpler format), add IFC later
- **Mitigation:** Partnership with BIM software vendors (Autodesk, Trimble) for official plugins

### Business Risks

**Risk 1: Low adoption of design upload feature**
- **Mitigation:** Offer free compliance validation for first 5 designs (freemium onboarding)
- **Mitigation:** Content marketing: Case studies showing time saved, RFIs avoided

**Risk 2: Competitors replicate spatial validation**
- **Mitigation:** Focus on accuracy moat (continuous validation against DA outcomes)
- **Mitigation:** Build integration moat (Revit/SketchUp plugins, council partnerships)

**Risk 3: Council changes provisions frequently**
- **Mitigation:** Automated DCP change detection (scrape council websites monthly)
- **Mitigation:** User reporting: "This provision has changed" → manual review

### Regulatory Risks

**Risk 1: Councils resist automated compliance tools**
- **Mitigation:** Position as "assessment support tool" not "automated approval"
- **Mitigation:** Partnership with councils: White-label for internal assessment (revenue share)

**Risk 2: Professional indemnity liability**
- **Mitigation:** Clear disclaimer: "PlotDetect provides information only, not professional advice"
- **Mitigation:** Insurance: Professional indemnity policy for PlotDetect Pty Ltd

---

## Success Metrics (KPIs)

### Product Metrics

**Horizon 1 (Months 1-12):**
- Design uploads: 500/month by Q4
- Compliance validation accuracy: >90% (validated against 100 real approved DAs)
- User retention: >70% month-over-month
- NPS: >50

**Horizon 2 (Months 13-24):**
- Solar analyses: 200/month by Q4 2027
- Shadow reports generated: 150/month
- Viewshed analyses: 50/month
- Compliance validation accuracy: >95% (validated against 500 DAs)

**Horizon 3 (Months 25-36):**
- Site searches: 1,000/month by Q4 2028
- Amalgamation scenarios generated: 300/month
- Predictive model accuracy: >75% (DA approval prediction)
- Council coverage: 13 councils (Inner West + 10 additional Sydney LGAs)

### Business Metrics

**Revenue:**
- Year 1: $281k ARR
- Year 2: $1.05M ARR (3.7x growth)
- Year 3: $3.05M ARR (2.9x growth)

**Customer Acquisition:**
- Year 1: 75 paying subscribers (50 Tier 1, 20 Tier 2, 5 Enterprise)
- Year 2: 265 paying subscribers (150 Tier 1, 75 Tier 2, 30 Tier 3, 10 Enterprise)
- Year 3: 725 paying subscribers (400 Tier 1, 200 Tier 2, 100 Tier 3, 25 Enterprise)

**CAC Payback:**
- Target: <6 months (CAC / MRR)
- Channels: Content marketing (SEO), industry partnerships (BIM software vendors, industry associations), council partnerships

**Churn:**
- Target: <5% monthly churn
- Retention tactics: Continuous accuracy improvements, new feature releases, customer success support

---

## Conclusion: The Defensible Moat

PlotDetect's path to an defensible moat in the age of vibe coding agents:

**1. Start with data moat:** 47,818 provisions with v2 taxonomy (already built)

**2. Add spatial validation moat:** Convert provisions → spatial tests (Horizon 1)
- Requires domain expertise to parse ambiguous provision text
- Requires validation against real DA outcomes (accuracy compounds over time)
- Vibe coding agents can't reliably do this

**3. Add technical moat:** 3D visualization + solar/shadow/viewshed (Horizon 2)
- Requires GIS infrastructure (PostGIS, GRASS GIS, CesiumJS)
- Requires spatial data (DEM, 3D buildings, cadastre)
- Vibe coding agents can call APIs but can't build the infrastructure

**4. Add integration moat:** BIM/CAD plugins + council partnerships (ongoing)
- Requires industry relationships (Autodesk, Trimble, councils)
- Requires trust-building over years

**5. Add network effects moat:** Predictive DA approval (Horizon 3)
- Requires historical DA outcome data (10,000+ DAs collected)
- Model improves with each new DA assessed
- First-mover advantage: More data → better predictions → more users → more data

**The result:** A compliance platform that is NOT just "information retrieval" (easy to replicate with AI) but **"spatial validation engine"** (hard to replicate without years of data curation, domain expertise, technical infrastructure, and industry partnerships).

**Time to replicate:** Estimated 3-5 years for a well-funded competitor starting from scratch

**PlotDetect's advantage:** 18-24 month head start (Horizon 1-2 launched before competitors build equivalent data moat)

---

*END OF STRATEGIC ROADMAP*
