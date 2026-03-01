# Recent Documents Summary (Last 7 Days)
**Date:** 2026-02-06
**Purpose:** Overview of all markdown documents created/modified in the last week

---

## Strategic Planning Documents

### 1. STRATEGIC_ROADMAP.md ❌ OUTDATED
**Location:** Project root
**Created:** Before competitive analysis
**Content:** Original strategic roadmap proposing generic compliance features
**Status:** **SUPERSEDED - DO NOT USE**
**Why outdated:**
- Proposed competing with Archistar on 3D envelopes (they already do this)
- Assumed "data curation" was a moat (Opus 4.6 will commoditize)
- Didn't account for PropCode's NSW digitization
- Generic compliance strategy (not defensible)

---

### 2. STRATEGIC_ROADMAP_REVISED.md ✅ CURRENT
**Location:** Project root
**Created:** After competitive analysis
**Content:** **Revised strategy focusing on heritage compliance niche**
**Status:** **CURRENT STRATEGIC DIRECTION**

**Key insights:**
- Archistar already does 3D envelopes, automated compliance ($22.7M, 130k users)
- PropCode has NSW LEP/DCP digitization
- **Only white space: Heritage compliance automation**
- Pivot from "generic compliance" to "heritage specialist"

**Strategic direction:**
- Heritage SOHI Assistant ($199/month for consultants)
- Heritage Pre-Check ($49 per assessment for architects)
- Council Heritage Co-Pilot ($10k/month white-label)
- Revenue: $60k Y1 → $656k Y3

**Why defensible:**
- Heritage DA outcome dataset (5,000 DAs, manual collection)
- Subjective heritage judgment (AI assists but can't replace)
- Council partnerships (relationship moat)
- Heritage consultancy network (vertical specialization)

**The moat:** "Veeva for Heritage" - vertical depth beats horizontal breadth

---

### 3. propcode-analysis-and-api-services.md ✅ CURRENT
**Location:** .claude/Plans/
**Created:** 2026-02-06
**Content:** **PropCode competitive analysis + PlotDetect API strategy**

**Part 1: PropCode Digitization Analysis**
- PropCode likely has: Zoning maps, LEP controls (FSR, height), land use tables
- PropCode likely does NOT have: Detailed DCP provisions (setbacks, materials, parking specs)
- Gap: PropCode = "planning control lookup", PlotDetect = "DCP provision extraction"

**Part 2: PlotDetect API Services**
5 API options ranked by feasibility + competition gap:

1. **Heritage Provision API** ⭐⭐⭐⭐⭐ ($0.50/call) - NO competitors
2. **DCP Provision Filtering API** ⭐⭐⭐⭐ ($0.30/call) - PropCode unlikely has this
3. **CDC Blocker API** ⭐⭐⭐ ($0.20/call) - Archistar has it but not as API
4. **Heritage Proximity API** ⭐⭐⭐⭐⭐ ($0.40/call) - Unique
5. **Provision Search API** ⭐⭐⭐⭐⭐ ($0.10/call) - Low ROI

**Recommended: Top 3 APIs packaged as "PlotDetect Data API"**
- Pricing: $500/month for 1,000 calls
- Target customers: Archistar/canibuild (white-label), CoreLogic/PropTrack (enrichment), LEAP/InfoTrack (conveyancing)
- Revenue: $30k Y1 → $372k Y3

---

### 4. geospatial-heritage-innovation.md ✅ CURRENT
**Location:** .claude/Plans/
**Created:** 2026-02-06
**Content:** **5 geospatial strategies using Open Geospatial Solutions tools**

**Core insight:** Heritage compliance is manual because consultants can't scale spatial analysis

**5 Strategies:**

1. **Heritage Fabric Spatial Database (SAMGeo)**
   - Extract roof types, materials from aerial imagery across entire HCA
   - Quantify heritage character: "73% hipped roofs, 28° average pitch"
   - Test proposed development: "5/6 elements match HCA character (83% compatible)"
   - Competition gap: ⭐⭐⭐⭐⭐ (NO ONE quantifies heritage spatially)
   - Revenue: $200k-500k/year

2. **Heritage Viewshed Analysis (GRASS r.viewshed + LiDAR)**
   - Automate visual impact assessment from heritage viewpoints
   - "32% visible from State heritage viewpoint → Lower roofline 1.5m"
   - Replace $2k photomontages with $299 automated reports
   - Competition gap: ⭐⭐⭐⭐⭐ (NO ONE does automated viewshed)
   - Revenue: $150k-400k/year

3. **Heritage Change Detection (SAMGeo + Nearmap)**
   - Monitor 100% of heritage properties quarterly (vs 2.5% manual)
   - Detect unauthorized works BEFORE completion
   - Council service: $15k/month
   - Competition gap: ⭐⭐⭐⭐⭐ (NO ONE offers this)
   - Revenue: $180k-600k/year

4. **Spatial DA Predictor (ML + GIS features)**
   - Heritage DA approval prediction with spatial features
   - Accuracy: 82% (vs 65% without spatial features)
   - "Visibility from viewpoint" most important feature (18% weight)
   - Competition gap: ⭐⭐⭐⭐⭐ (NO ONE uses spatial features)
   - Revenue: $100k-250k/year

5. **Aboriginal Heritage Prediction (Random Forest + spatial)**
   - AHIMS database sparse (only 5% of sites registered)
   - Predict high-probability areas using terrain, water, vegetation
   - Avoid $50k emergency salvage + 12 week delays
   - Competition gap: ⭐⭐⭐⭐⭐ (NO ONE offers this)
   - Revenue: $120k-300k/year

**Total revenue potential:** $750k-$2M/year

**Why defensible:** Requires infrastructure (LiDAR, Nearmap $10k/year), data (viewpoints, AHIMS, DA outcomes), expertise (heritage + GIS), and 12-18 months to build

---

### 5. Data/da-history-data-sources.md ✅ CURRENT
**Location:** .claude/Plans/Data/
**Created:** 2026-02-06
**Content:** **How to collect 5,000+ heritage DA records for predictive model**

**The problem:** OnlineDA, OnlineCDC, NSW Planning Portal have minimal data (no refusal reasons, design details, heritage flags)

**7 Data sources ranked:**

1. **Council DA registers (web scraping)** - FREE ⭐⭐⭐⭐⭐
   - Best option for comprehensive data
   - Scrape Inner West Council portal systematically
   - Download assessment PDFs → LLM parsing with Claude
   - Cost: $10-50 (Claude API), Time: 6-8 weeks

2. **PlanningAlerts.org.au API** - FREE ⭐⭐⭐⭐
   - Already scraped all councils
   - Free API, ~10,000 Inner West DAs
   - Basic info only → use as DA list, then scrape for details

3. **GIPA request** - $30-100 ⭐⭐⭐
   - Government Information (Public Access) Act 2009
   - Request bulk DA data from council
   - Template included in document
   - 20 business days response time

4. **NSW Planning Portal** - FREE ⭐⭐
   - State significant DAs only (detailed)
   - Local DAs: basic info, links to council portals

5. **ePlanning API** - FREE ⭐⭐⭐ (if exists)
   - Some councils have undocumented APIs
   - Check browser network tab for endpoints

6. **Domain/REA APIs** - PAID $$$ ⭐
   - $5k-10k/year, basic property data only
   - Not recommended

7. **CoreLogic RP Data** - PAID $$$$ ⭐
   - $10k-50k/year, designed for valuers
   - Not recommended

**Recommended approach: Hybrid**
1. Submit GIPA request ($30, 3 weeks wait)
2. Fetch PlanningAlerts data (1 day)
3. Build scraper while waiting (2 weeks)
4. Scrape council portals (2 weeks runtime)
5. LLM parse PDFs with Claude ($10-50, 2 weeks)
6. Manual validation (1 week, >95% accuracy target)

**Total: 6-8 weeks, $10-50 cost, 2,000+ heritage DAs with full data**

**Code examples included:**
- PlanningAlerts API fetcher
- Council portal scraper
- Claude LLM PDF parser
- Manual validation workflow

---

### 6. leichhardt-precinct-fixes.md
**Location:** .claude/Plans/
**Created:** Earlier (pre-strategic pivot)
**Content:** Technical plan for fixing Leichhardt precinct data issues
**Status:** Technical reference (still relevant for DB fixes)

---

### 7. spicy-skipping-sketch.md
**Location:** .claude/Plans/
**Created:** Earlier
**Content:** Unknown (need to read to determine)
**Status:** Unknown

---

## Product Demonstration Documents (Screencasts)

All screencasts follow identical structure with **comprehensive API testing**:
- [0:00-0:20] Property card (zone, FSR, height, constraints)
- [0:20-0:40] SEPP tab (BASIX requirements)
- [0:40-1:00] LEP tab (zone objectives, permitted uses)
- [1:00-1:40] DCP tab (provisions organized by topic) **← MAIN FEATURE**
- [1:40-2:00] Complete assessment outcome

**Production Checklist section:** Documents all API endpoints tested (property, provisions, CDC, SEPP, permissibility, heritage)

### 8. screencast-certifier.md
**Address:** 10 Railway Parade, Summer Hill (Heritage HCA C95)
**User niche:** Certifier (CDC assessment)
**Workflow:** CDC blocker identification → provide SEPP citation + complete heritage provision list
**APIs tested:** Property, provisions (heritage=true), CDC, SEPP
**Provisions:** 701 total (306 heritage-specific)
**Value:** CDC blocker with exact citation, zero manual DCP reading

---

### 9. screencast-developer.md
**Address:** 35 Albert Street, Ashfield (R2, 736 sqm, clean)
**User niche:** Developer (feasibility analysis)
**Workflow:** Property baseline → SEPP requirements → LEP controls → DCP cost impact
**APIs tested:** Property, provisions, CDC, SEPP
**Provisions:** 395 total (parking 32, landscaping 11, building_form 20)
**Value:** Cost quantification ($32k parking, $22k landscaping, $8k BASIX)

---

### 10. screencast-townplanner.md
**Address:** 35 Albert Street, Ashfield
**User niche:** Town Planner (DA report preparation)
**Workflow:** Complete provision list for DA report citations → zero RFI risk
**APIs tested:** Property, provisions, CDC, SEPP
**Provisions:** 395 total with PDF citations
**Value:** Zero missed provisions = zero assessment RFIs

---

### 11. screencast-architect.md
**Address:** 35 Albert Street, Ashfield
**User niche:** Architect (concept design)
**Workflow:** Design compliant building envelope from day 1
**APIs tested:** Property, provisions, CDC, SEPP
**Provisions:** 395 total (setbacks, building form, materials)
**Value:** No rework, concept compliant from start

---

### 12. screencast-realestateagent.md
**Address:** 35 Albert Street, Ashfield
**User niche:** Real Estate Agent (development potential assessment)
**Workflow:** Identify dual occ potential → 20-30% listing premium
**APIs tested:** Property, provisions, CDC, permissibility, SEPP
**Provisions:** 395 total
**Value:** Development potential = higher listing price

---

### 13. screencast-heritageconsultant.md
**Address:** 10 Railway Parade, Summer Hill (Heritage HCA C95)
**User niche:** Heritage Consultant (SOHI preparation)
**Workflow:** Complete heritage provision checklist organized by topic
**APIs tested:** Property, provisions (heritage), CDC, SEPP
**Provisions:** 306 heritage provisions (Roof 74, Demolition 45, Parking 44, Materials 25)
**Value:** SOHI in 30 min vs 3-4 hours manual DCP reading

---

### 14. screencast-conveyancer.md
**Address:** 35 Albert Street, Ashfield
**User niche:** Conveyancer (property due diligence)
**Workflow:** Complete constraints check (heritage/flood/bushfire/Part 6) + development potential
**APIs tested:** Property, provisions, permissibility, CDC, SEPP
**Provisions:** 395 standard R2 provisions
**Value:** Professional indemnity protection, 10 min vs 2-3 hours (12-18x faster)

---

### 15. screencast-builder.md
**Address:** 35 Albert Street, Ashfield
**User niche:** Builder (construction quote)
**Workflow:** Extract construction specifications from DCP provisions for accurate quoting
**APIs tested:** Property, provisions, CDC, SEPP
**Provisions:** 395 total (parking 32, landscaping 11, building_form 20, materials 15)
**Value:** Accurate quote from day 1, zero cost blowouts ($32k parking, $22k landscaping from exact specs)

---

### 16. SCREENCAST_API_CHECKLIST.md
**Location:** Project root
**Purpose:** Mandatory API testing checklist for all screencasts
**Content:** Complete list of assessment page endpoints
- /api/property
- /api/provisions/for-property
- /api/cdc/preliminary-check
- POST /api/sepp/structured-requirements
- /api/permissibility/check
- /api/heritage/hca-check
- /api/lep/provisions
- /api/tod/transport-autocomplete
- /api/housing-sepp/eligibility
- /api/precinct/match
**Status:** Reference document (ensures comprehensive API testing)

---

## User Story Documents

### 17. USER_STORY_DEVELOPER_DUAL_OCCUPANCY.md
**Address:** 35 Albert Street, Ashfield
**Persona:** Sam Chen, developer (15 years experience)
**Workflow:** Feasibility analysis → cost estimation → DA pathway
**Pain points:** Manual DCP reading (3-4 hours), cost estimation errors, CDC pathway confusion
**Solution:** PlotDetect provides 395 provisions filtered, cost breakdown, CDC blockers identified
**Outcome:** 3 hours → 15 minutes (12x faster)

---

### 18. USER_STORY_TOWNPLANNER_DA_PREP.md
**Address:** 35 Albert Street, Ashfield
**Persona:** Jessica Wong, town planner (8 years experience)
**Workflow:** DA report preparation with provision citations
**Pain points:** Missing provisions = RFI delays (2-4 weeks), client frustration
**Solution:** PlotDetect provides complete provision list with PDF citations (395 provisions)
**Outcome:** Zero RFIs, 2 hours → 30 minutes (4x faster)

---

### 19. USER_STORY_ARCHITECT_CONCEPT.md
**Address:** 35 Albert Street, Ashfield
**Persona:** Michael Torres, architect (12 years experience)
**Workflow:** Concept design compliant with all DCP provisions
**Pain points:** Design rework after consultant review ($15k cost, 3 week delay)
**Solution:** PlotDetect shows all setback, building form, materials provisions upfront
**Outcome:** Compliant concept from day 1, no rework

---

### 20. USER_STORY_BUILDER_EXTENSION_QUOTE.md
**Address:** 185 Parramatta Road, Haberfield (Heritage Item I087)
**Persona:** Tony Russo, builder (20 years experience)
**Workflow:** Construction quote for heritage property addition
**Pain points:** Heritage material specs unclear, cost blowouts during construction
**Solution:** PlotDetect provides exact heritage materials specs from 306 provisions
**Outcome:** Accurate quote ($145k vs original $120k estimate that would have been wrong)

---

### 21. USER_STORY_185_PARRAMATTA_RD.md
**Address:** 185 Parramatta Road, Haberfield (Heritage Item I087)
**Multiple user niches:** Developer, heritage consultant, architect, town planner, certifier
**Heritage context:** Inter-War Californian Bungalow (State significant)
**Provisions:** 850 total (306 heritage + 544 standard R2)
**Use case:** Shows how SAME address used by different professionals for different purposes

---

## Technical Documentation

### 22. API_VERIFICATION_FINDINGS.md
**Location:** Project root
**Created:** During API testing for screencasts
**Content:** Verification that heritage provisions API returns correct data
**Findings:**
- Heritage provisions correctly filtered by v2_marker='heritage'
- HCA spatial check working
- Provision counts verified (306 heritage, 395 standard R2)
**Status:** Technical reference (API validation complete)

---

## Summary by Category

### Strategic Documents (3 current)
1. ✅ STRATEGIC_ROADMAP_REVISED.md - Heritage-first strategy
2. ✅ propcode-analysis-and-api-services.md - Competition analysis + API strategy
3. ✅ geospatial-heritage-innovation.md - 5 geospatial strategies

### Data Collection (1)
4. ✅ da-history-data-sources.md - How to collect 5,000+ heritage DAs

### Product Demos (9 screencasts)
5-13. Screencast scripts for 8 user niches + API checklist

### User Stories (5)
14-18. Detailed user workflows for developer, planner, architect, builder, multi-niche

### Technical Reference (1)
19. API_VERIFICATION_FINDINGS.md - API validation

---

## Key Takeaways

**Strategic pivot:**
- ❌ OLD: Generic compliance (compete with Archistar)
- ✅ NEW: Heritage specialist (no competitors)

**Revenue model:**
- Heritage consultancy augmentation ($199/month)
- Architect pre-checks ($49/assessment)
- Council co-pilot ($10k/month)
- API services ($500/month)

**Defensible moats:**
- Heritage DA dataset (5,000 DAs, 6-8 weeks to collect)
- Geospatial capabilities (SAMGeo, GRASS GIS, 12-18 months to build)
- Council partnerships (relationship moat)
- Heritage consultancy network (vertical specialization)

**Total revenue potential:**
- Heritage platform: $60k Y1 → $656k Y3
- API services: $30k Y1 → $372k Y3
- Geospatial: $750k-$2M/year
- **Combined: $1M-$3M/year**

---

*END OF RECENT DOCUMENTS SUMMARY*
