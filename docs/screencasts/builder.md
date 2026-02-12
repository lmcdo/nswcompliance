# Builder Screencast Script
**Duration:** 2:00
**User Niche:** Builder (Dual Occupancy Construction Quote)
**Address:** 35 Albert Street, Ashfield NSW 2131

---

## Production Checklist: Live API Testing

### Address Details
- **Property:** 35 Albert Street, Ashfield NSW 2131
- **Land Area:** 736 sqm
- **Zone:** R2 Low Density Residential
- **Max FSR:** 0.7 (515 sqm GFA available)
- **Max Height:** 9m
- **Development Type:** Dual occupancy (attached)
- **Land Value:** $2,380,000

### API Endpoints Tested

#### 1. `/api/property?address=35 Albert Street, Ashfield NSW 2131`
**Status:** ✓ Success
**Response:**
- Zone: R2 Low Density Residential
- Max FSR: 0.7
- Max Height: 9m
- Land Area: 736 sqm
- Constraints:
  - Heritage: False
  - Flood Prone: False
  - Bushfire Prone: False
  - BASIX Climate: Zone 3
  - BASIX Water: Zone 3
- Land Value: $2,380,000

#### 2. `/api/provisions/for-property?address=35 Albert Street, Ashfield NSW 2131`
**Status:** ✓ Success
**Response:** 395 DCP provisions across 4 layers:
- **Generic layer (231 provisions):** Standard Ashfield R2 requirements
- **Use-specific layer (164 provisions):** Dual occupancy controls
- **Condition layer (0 provisions):** No heritage/flood constraints
- **Precinct layer (0 provisions):** No specific precinct

**Builder-Relevant Provision Topics:**
- `parking`: 32 provisions
  - Car space dimensions: 5.5m x 2.4m minimum
  - Setback from boundary: 1m minimum
  - Maximum gradient: 1:4 (25%)
  - Surface: Permeable paving or drainage connection
  - Visitor parking: 1 space per 3 dwellings
- `landscaping`: 11 provisions
  - Minimum landscaped area: 20% of site (147 sqm for 736 sqm lot)
  - Minimum planting depth: 3m
  - Canopy tree requirement: 1 per 250 sqm (3 trees required)
  - Species: Native/endemic preferred
  - Irrigation system required
- `building_form`: 20 provisions
  - Front setback: 6m minimum
  - Side setback: 0.9m minimum
  - Rear setback: 6m minimum
  - Maximum site coverage: 60% (442 sqm)
  - Building separation: 3m minimum between dwellings
- `outdoor_areas`: 8 provisions
  - Minimum private open space: 24 sqm per dwelling
  - Minimum dimension: 4m
  - Solar access: 3 hours midwinter to 50% of area
- `materials`: 15 provisions
  - Roof pitch: 25-35 degrees
  - Roof color: Earth tones, no highly reflective
  - Wall materials: Brick, rendered masonry, weatherboard
  - Fencing: Max 1.2m front, 1.8m side/rear
- `driveways`: 7 provisions
  - Maximum width: 3m for single, 5.5m for double
  - Maximum gradient: 1:4 (25%)
  - Cross-fall: 1:40 maximum
  - Apron connection to street
- `setbacks`: 4 provisions
  - Front: 6m
  - Side: 0.9m (single storey), 1.2m (two storey)
  - Rear: 6m
  - From drainage easement: 2m
- `swimming_pools`: 6 provisions
  - Setback from boundary: 1m minimum
  - Fencing: AS 1926.1-2012 compliant
  - Pool equipment: Screened from street, max 50dB
- `fencing`: 9 provisions
  - Front fence: Max 1.2m, 50% transparency above 0.9m
  - Side/rear: Max 1.8m
  - Materials: Matching building materials
  - On-boundary construction permitted with consent

**PDF Citations:** All provisions include PDF page references for verification
- Part A General Provisions: Pages 15-78
- Part D2 Dual Occupancy: Pages 156-189
- Part E5 Parking: Pages 245-267
- Part E7 Landscaping: Pages 289-301

#### 3. `/api/cdc/preliminary-check?address=35 Albert Street, Ashfield NSW 2131`
**Status:** ✓ Success
**Response:**
- Pathway: DA (Development Application)
- Blockers: 0
- Reason: Dual occupancy (attached) requires DA under ISEPP 2021 cl 2.81
- CDC not available for attached dual occupancy in R2 zone

#### 4. `POST /api/sepp/structured-requirements`
**Request Body:**
```json
{
  "seppId": "housing-2021",
  "developmentType": "dual-occupancy"
}
```
**Status:** ✓ Success
**Response:** 3 requirement sections
- **BASIX:** 40 points energy, 40 points water (standard residential)
- **Minimum Standards:**
  - Each dwelling: Min 2 bedrooms
  - Min internal area: 70 sqm per dwelling
  - Min ceiling height: 2.7m living areas, 2.4m other
  - Solar access: 3 hours to living room window
- **Site Requirements:**
  - Min lot size: 450 sqm (✓ 736 sqm complies)
  - Min lot width: 15m
  - Stormwater: On-site detention required

#### 5. `/api/permissibility/check?address=35 Albert Street, Ashfield NSW 2131`
**Status:** ✓ Success
**Response:**
- Zone: R2 Low Density Residential
- Dual occupancy (attached): Permitted with consent
- Land use: Residential
- LEP Clause: 2.3, 4.1

---

## Screencast Script

### [0:00-0:05] Opening Title
**Screen:** PlotDetect logo
**Voiceover:**
*"You're quoting a dual occupancy construction in Ashfield. You need exact DCP specifications for accurate costing—parking dimensions, landscaping percentages, material requirements. Normally, this means reading 300 pages of council DCPs. Here's the PlotDetect way."*

**Text Overlay:**
*Builder: Dual Occupancy Construction Quote*
*Challenge: Extract exact specifications from 395 DCP provisions*
*Time: 10 minutes vs 2-3 hours*

---

### [0:05-0:20] Property Card - Construction Baseline
**Screen:** Property assessment page, Property card expanded
**Voiceover:**
*"Enter the address: 35 Albert Street, Ashfield. The property card shows your construction baseline. 736 square meter R2 lot. Maximum FSR 0.7 gives you 515 square meters of gross floor area. Maximum height 9 meters allows two storeys. Land value 2.38 million. Clean site—no heritage, flood, or bushfire constraints."*

**Text Overlay (appears as mentioned):**
*R2 Low Density Residential*
*736 sqm lot*
*FSR 0.7 = 515 sqm GFA available*
*Height 9m = 2 storeys*
*CLEAN: No heritage/flood/bushfire*
*Land Value: $2.38M*

**Interaction:**
- Type address in search bar
- Property card auto-expands showing zone, FSR, height, constraints
- Highlight FSR calculation: 736 x 0.7 = 515 sqm

---

### [0:20-0:40] SEPP Tab - BASIX Cost Item
**Screen:** Click SEPP tab
**Voiceover:**
*"The SEPP tab shows Housing SEPP 2021 requirements. BASIX: 40 points energy, 40 points water—that's roughly $8,000 in your quote for solar, insulation, and water-saving fixtures. Minimum standards: Each dwelling needs 2 bedrooms minimum, 70 square meters internal area, 2.7 meter ceiling in living areas. These are your base construction specs before you even look at council DCP."*

**Text Overlay (appears as mentioned):**
*BASIX Requirements:*
*40 energy points + 40 water points*
*Cost: ~$8,000 (solar, insulation, water fixtures)*

*Minimum Standards:*
*2 bedrooms per dwelling*
*70 sqm internal area*
*2.7m ceiling (living), 2.4m (other)*

*Site Requirements:*
*Min 450 sqm lot (✓ 736 sqm complies)*
*On-site stormwater detention required*

**Interaction:**
- Click SEPP tab
- Scroll through Housing SEPP 2021 structured requirements
- Highlight BASIX section, minimum standards, site requirements

---

### [0:40-1:00] LEP Tab - Zoning Compliance
**Screen:** Click LEP tab
**Voiceover:**
*"The LEP tab confirms dual occupancy is permitted with consent in R2 zone. Zone objectives: Low density housing, landscaped setting. These objectives inform the DCP controls you'll see next. Maximum FSR 0.7 and height 9 meters are your building envelope constraints."*

**Text Overlay (appears as mentioned):**
*R2 Zone Objectives:*
*Low density housing in landscaped setting*

*Permitted Development:*
*Dual occupancy (attached) - WITH CONSENT*

*Building Envelope:*
*FSR 0.7 (515 sqm max GFA)*
*Height 9m (2 storeys)*

**Interaction:**
- Click LEP tab
- Scroll through Ashfield LEP 2013 zone objectives
- Highlight Land Use Table showing dual occupancy permitted with consent
- Show FSR and height controls

---

### [1:00-1:40] DCP Tab - Extract Construction Specifications (KEY SECTION)
**Screen:** Click DCP tab
**Voiceover:**
*"Here's where PlotDetect saves you 2-3 hours. The DCP tab shows 395 provisions filtered for this R2 dual occupancy development, organized by topic. Let's extract your construction quote specifications."*

**Text Overlay:**
*395 DCP provisions filtered*
*Topics: Parking, Landscaping, Building Form, Materials, Fencing*

**Scroll to Parking (32 provisions):**
**Voiceover:**
*"Parking: 32 provisions. You need 2 car spaces, each 5.5 meters by 2.4 meters minimum. Setback 1 meter from boundary. Maximum gradient 1-in-4. That's $15,000 per space for excavation, slab, drainage. Plus one visitor space per 3 dwellings. Total parking cost: $32,000."*

**Text Overlay (appears as mentioned):**
*PARKING (32 provisions):*
*2 resident spaces required*
*Dimensions: 5.5m x 2.4m each*
*Setback: 1m from boundary*
*Max gradient: 1:4 (25%)*
*Surface: Permeable or drainage connected*
*Cost: 2 spaces @ $15k = $30,000*
*+ 1 visitor space = $32,000 total*

**Scroll to Landscaping (11 provisions):**
**Voiceover:**
*"Landscaping: 11 provisions. Minimum 20% of site must be landscaped—that's 147 square meters for a 736 square meter lot. Minimum 3 meters depth, canopy trees required, irrigation system. At $150 per square meter, landscaping costs $22,000."*

**Text Overlay (appears as mentioned):**
*LANDSCAPING (11 provisions):*
*Minimum 20% of site = 147 sqm*
*Min depth: 3m*
*Canopy trees: 3 required (1 per 250 sqm)*
*Irrigation: Required*
*Cost: 147 sqm @ $150/sqm = $22,000*

**Scroll to Building Form (20 provisions):**
**Voiceover:**
*"Building form: 20 provisions. Front setback 6 meters, side setback 0.9 meters single storey or 1.2 meters two-storey, rear setback 6 meters. Maximum site coverage 60%—that's 442 square meters. Building separation 3 meters between dwellings. These setbacks determine your floor plate and construction staging."*

**Text Overlay (appears as mentioned):**
*BUILDING FORM (20 provisions):*
*Front setback: 6m*
*Side setback: 0.9m (single), 1.2m (two storey)*
*Rear setback: 6m*
*Max site coverage: 60% = 442 sqm*
*Building separation: 3m between dwellings*

**Scroll to Materials (15 provisions):**
**Voiceover:**
*"Materials: 15 provisions. Roof pitch 25-35 degrees, earth tone colors, no highly reflective. Walls must be brick, rendered masonry, or weatherboard. Fencing maximum 1.2 meters front, 1.8 meters side and rear. These material specs go straight into your quote."*

**Text Overlay (appears as mentioned):**
*MATERIALS (15 provisions):*
*Roof: 25-35° pitch, earth tones*
*Walls: Brick, rendered masonry, weatherboard*
*Fencing: 1.2m max (front), 1.8m max (side/rear)*
*Front fence: 50% transparency above 0.9m*

**Scroll to Outdoor Areas (8 provisions):**
**Voiceover:**
*"Outdoor areas: 8 provisions. Each dwelling needs 24 square meters private open space minimum, 4 meter minimum dimension, 3 hours solar access in midwinter. That's 48 square meters total outdoor space required."*

**Text Overlay (appears as mentioned):**
*OUTDOOR AREAS (8 provisions):*
*Min 24 sqm per dwelling = 48 sqm total*
*Min dimension: 4m*
*Solar access: 3 hours midwinter to 50%*

**Voiceover (continuing):**
*"Every single provision includes a PDF page citation. If you need to verify the exact wording—parking gradient, tree species, fence materials—you can jump straight to the source DCP page. No more reading 300 pages front-to-back."*

**Text Overlay:**
*PDF Citations: All 395 provisions linked to source pages*
*Part E5 Parking: pp.245-267*
*Part E7 Landscaping: pp.289-301*
*Part D2 Dual Occupancy: pp.156-189*

---

### [1:40-2:00] Complete Construction Quote - Cost Summary
**Screen:** Scroll to top of DCP tab, show complete provision list
**Voiceover:**
*"In 10 minutes, you've extracted complete construction specifications from 395 DCP provisions. Parking: $32,000. Landscaping: $22,000. BASIX: $8,000. Setbacks, materials, outdoor areas—all specified exactly. Your quote is accurate from day one. No cost blowouts during construction because you missed a DCP requirement buried on page 247."*

**Text Overlay (appears as mentioned):**
*CONSTRUCTION QUOTE READY:*
*Parking: $32,000 (2 resident + 1 visitor)*
*Landscaping: $22,000 (147 sqm)*
*BASIX: $8,000 (energy + water)*
*Materials: Specified (brick/masonry, roof pitch)*
*Setbacks: Confirmed (6m front, 0.9m/1.2m side, 6m rear)*
*Outdoor space: 48 sqm (24 sqm per dwelling)*

**Voiceover (final):**
*"PlotDetect: Complete DCP specifications for construction quotes. 10 minutes instead of 2-3 hours. Zero missed requirements, zero cost blowouts. This is how builders quote dual occupancy developments."*

**Text Overlay (final screen):**
*PlotDetect for Builders*
*✓ 395 DCP provisions filtered*
*✓ Exact specifications extracted*
*✓ 10 min vs 2-3 hours (12-18x faster)*
*✓ Accurate quote, zero cost blowouts*
*www.plotdetect.com.au*

**Screen fades to PlotDetect logo.**

---

## Key Talking Points

### Pain Point
- Builders must extract exact specifications from DCPs for accurate construction quotes
- Reading 300+ pages of council DCP manually (2-3 hours)
- Risk: Miss a requirement (e.g., parking gradient, landscaping percentage) = cost blowout during construction
- Example: Forget visitor parking requirement = $16k cost blowout mid-construction

### PlotDetect Solution
- 395 DCP provisions filtered for R2 dual occupancy, organized by topic
- Builder-relevant specifications extracted:
  - **Parking:** 32 provisions → 2 spaces, 5.5m x 2.4m, 1m setback, 1:4 gradient, $32k
  - **Landscaping:** 11 provisions → 20% = 147 sqm, 3m depth, 3 canopy trees, $22k
  - **Building form:** 20 provisions → Setbacks (6m/0.9m/6m), site coverage 60%
  - **Materials:** 15 provisions → Roof pitch 25-35°, brick/masonry walls, fence heights
  - **Outdoor areas:** 8 provisions → 24 sqm per dwelling, 4m dimension, solar access
- PDF page citations for every provision (verify exact wording instantly)
- Complete specifications in 10 minutes vs 2-3 hours manual reading

### Value Proposition
- **Speed:** 12-18x faster (10 min vs 2-3 hours)
- **Accuracy:** Zero missed requirements = zero cost blowouts
- **Complete specifications:** All dimensions, percentages, materials extracted from 395 provisions
- **Cost impact example:**
  - Parking: $32k (2 resident + 1 visitor, exact dimensions from provisions)
  - Landscaping: $22k (20% requirement = 147 sqm calculated automatically)
  - BASIX: $8k (energy + water requirements from SEPP)
  - Total: $62k in major cost items specified exactly
- **Risk mitigation:** No surprises during construction, accurate client quotes, professional reputation protected

### Regulatory Cascade (Planning Portal → SEPP → LEP → DCP)
1. **Planning Portal:** Property baseline (736 sqm R2, FSR 0.7, height 9m, clean site)
2. **SEPP Housing 2021:** BASIX 40/40 points, minimum 2 beds, 70 sqm internal, 2.7m ceiling
3. **Ashfield LEP 2013:** Dual occ permitted with consent, FSR 0.7, height 9m
4. **Ashfield DCP 2015:** 395 provisions with exact construction specs (parking, landscaping, setbacks, materials)

### DCP Provisions as THE MAIN FEATURE
- Competitors show "check council DCP manually" → not helpful for builders needing exact specs
- PlotDetect shows 395 filtered provisions organized by construction topic
- Every provision has PDF page citation for verification
- Builders can extract specifications in 10 minutes that previously took 2-3 hours
- This is the differentiator: Not just CDC yes/no, but complete construction specifications for accurate quoting

---

## Technical Notes

### Address Selection
- **35 Albert Street, Ashfield NSW 2131** chosen for:
  - Standard R2 dual occupancy development (common builder scenario)
  - Clean site (no heritage/flood/bushfire constraints = simpler quote)
  - Good provision count (395 provisions = comprehensive specifications)
  - Builder-relevant topics well-represented (parking 32, landscaping 11, building_form 20)

### API Data Sources
- Property card: `/api/property` (zone, FSR, height, land area, constraints, land value)
- SEPP tab: `POST /api/sepp/structured-requirements` (BASIX, minimum standards, site requirements)
- LEP tab: `/api/permissibility/check`, `/api/lep/provisions` (zone objectives, permitted uses, FSR/height controls)
- DCP tab: `/api/provisions/for-property` (395 provisions filtered by zone/council/heritage, organized by v2_topic)
- CDC check: `/api/cdc/preliminary-check` (pathway = DA, blockers = 0)

### Builder-Specific Provision Topics
Focus on construction specification topics:
- `parking`: Car space dimensions, setbacks, gradients, surface requirements
- `landscaping`: Minimum percentages, planting depth, tree counts, species, irrigation
- `building_form`: Setbacks, site coverage, building separation, floor plates
- `materials`: Roof pitch, colors, wall materials, fencing specifications
- `outdoor_areas`: Private open space minimums, dimensions, solar access
- `driveways`: Width, gradient, cross-fall, apron connection
- `setbacks`: Front/side/rear distances, single vs two storey
- `swimming_pools`: Setbacks, fencing compliance, equipment screening
- `fencing`: Height limits, transparency, materials, on-boundary construction

### Cost Impact Examples (Builder Context)
All costs based on standard NSW residential construction rates:
- **Parking:** $15,000 per space (excavation, slab, drainage, permeable paving)
- **Visitor parking:** $16,000 (additional space required per 3 dwellings)
- **Landscaping:** $150 per sqm (soil preparation, plants, irrigation, mulch)
- **BASIX compliance:** $8,000 (solar panels, insulation upgrades, water-saving fixtures)
- **Total quantified:** $62,000 in major cost items extracted from provisions

### Timing Breakdown
- **0:00-0:20** (20s): Property card → construction baseline (zone, FSR, height, land area, clean site)
- **0:20-0:40** (20s): SEPP tab → BASIX cost item ($8k), minimum standards
- **0:40-1:00** (20s): LEP tab → Dual occ permitted, zone objectives, FSR/height controls
- **1:00-1:40** (40s): DCP tab → Extract construction specs from 395 provisions (parking, landscaping, building form, materials, outdoor areas)
- **1:40-2:00** (20s): Complete quote summary → Cost breakdown, time saved, zero blowouts

---

## Production Requirements

### Text Overlays
- All data points must have text overlays (zone, FSR, height, land area, provision counts, costs)
- Cost calculations shown as they're mentioned (e.g., "20% = 147 sqm", "147 sqm @ $150 = $22,000")
- Use full prose: "395 provisions filtered" not "395 provisions"
- Provision topics with counts: "parking (32 provisions)", "landscaping (11 provisions)"
- Final summary screen with complete cost breakdown

### Screen Recording
- Record at http://localhost:3003/assessment
- Use address: 35 Albert Street, Ashfield NSW 2131
- Ensure all tabs (Property, SEPP, LEP, DCP) are visible and functional
- Scroll smoothly through DCP provisions by topic (parking, landscaping, building_form, materials, outdoor_areas)
- Show PDF page citations (Part E5 pp.245-267, Part E7 pp.289-301)

### Voiceover
- Professional builder context throughout (construction quotes, cost items, specifications)
- Emphasize time saved: "10 minutes vs 2-3 hours"
- Highlight accuracy: "Zero missed requirements, zero cost blowouts"
- Explain cost impact: "$32k parking, $22k landscaping, $8k BASIX"
- Show DCP provisions as main feature: "395 provisions organized by topic, PDF citations for verification"

### Live API Testing Documentation
All API endpoints tested and documented in Production Checklist section:
- Property API: Zone, FSR, height, land area, constraints verified
- Provisions API: 395 provisions, builder-relevant topics counted
- CDC API: DA pathway confirmed
- SEPP API: BASIX requirements, minimum standards extracted
- Permissibility API: Dual occ permitted with consent verified

Builder screencast demonstrates complete construction specifications extraction from DCP provisions for accurate quoting.
