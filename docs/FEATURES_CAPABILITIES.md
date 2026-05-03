# PlotDetect Features & Capabilities

*Last Updated: 2026-01-30*

Quick reference for what PlotDetect can and cannot do.

---

## ✅ **What Users Can Do Now**

### 1. Property Lookup & Context
- **Enter any NSW address** → Get zone, heritage status, flood/bushfire overlays
- **Auto-detect precinct** (90 precincts mapped with GeoJSON boundaries)
- **Former council determination** (Ashfield/Marrickville/Leichhardt)
- **Lot geometry** (polygon coordinates from NSW Planning Portal)

### 2. DCP Provisions (4-Layer Filtering)
- **View relevant DCP provisions** for selected property
- **Filter by:**
  - Topic (parking, setbacks, landscaping, heritage, etc.)
  - Development type (13 types: dwelling_house, dual_occupancy, etc.)
  - Assessment type (CDC = quantitative only, DA = all)
- **Group by:** Topic OR Table of Contents structure
- **Click through** to PDF page screenshots
- **Total:** 47,818 provisions across 3 councils

### 3. AI Chat Assistant
- **Ask questions** in natural language
- **8 question categories:**
  1. Definitions - "What is a habitable room?" ✅
  2. Procedural - "CDC vs DA difference?" ✅
  3. Factual lookup - "What's the height limit?" ✅
  4. Permissibility - "Can I build a duplex?" ✅
  5. Housing SEPP - "Am I eligible for manor house?" ✅
  6. Constraints - "Is this heritage listed?" ✅
  7. Synthesis - "What can I build here?" ⚠️ Limited
  8. Interpretation - REFUSED (requires professional judgment) ❌
- **No content generation** - All responses from precomputed data
- **Citations included** (basic sources, no PDF pages yet)

### 4. Permissibility Checks
- **Check LEP land use table** - "Can I build X in this zone?"
- **Shows alternatives** if development type prohibited
- **Zone description** + LEP clause references
- **Development types:** 20+ types supported

### 5. Compliance Overview
- **Height/FSR limits** from NSW Planning Portal spatial layers
- **Constraint overlay** - Heritage, flood, bushfire
- **BASIX climate/water zones**
- **TOD precinct** identification (SEPP Housing 2021)
- **Local provisions** (Part 6 LEP)

### 6. Pre-DA Site History Report
- **Site development history** for any NSW address (paid $49 report)
- **Data sources:** ePlanning DAs + PCCs (paginated, capped at 10 pages), Sentinel-2 NDVI/NDBI change detection (via Element84 STAC, CRS-aware sampling), heritage overlay (spatial_overlays PostGIS), council zoning
- **Payment:** Stripe Checkout with idempotency key, `is_paid` gate on generate route, webhook sets paid flag before PDF generation
- **PDF report** with DA timeline, vegetation/built change, heritage flag, zoning context
- **Poll-based status** with 60-poll timeout on frontend

### 7. Flood Truth Engine
- **Multi-source flood assessment** for any NSW address
- **Data sources:** NSW EPI WFS (71 LGAs), Sentinel-1 SAR, Copernicus EMS, JRC surface water, BOM gauges, SES/council spatial overlays (100+ LGAs)
- **Council flood study rasters:** Hawkesbury (9 AEPs), Tweed (5 AEPs + 4 historical events), Wollongong (6 AEPs) — depth and water level per AEP event
- **NSW 5m DEM ground elevation** via SIX Maps ImageServer (full NSW, no auth)
- **100-year flood zone headline** derived from EPI + SES + study rasters
- **Flood depth calculation:** flood level minus ground elevation per AEP
- **PDF report** with full AEP depth/level tables (paid), historical event data, aerial imagery
- **Flood signal classification:** none / low / moderate / elevated (multi-source convergence)

---

## ❌ **What PlotDetect Cannot Do (Yet)**

### 1. Multi-Source Synthesis
- **Cannot combine** LEP + DCP + SEPP into one answer
- **Example:** "Can I build a granny flat?"
  - ✅ Tells you: Permitted in R2 zone (LEP)
  - ❌ Doesn't tell you: DCP setbacks, lot size requirements, parking

### 2. Compliance Verification
- **Cannot verify** if your design complies with requirements
- **Example:** "Does my 5m rear setback comply?"
  - ✅ Tells you: Rear setback requirement is 6m
  - ❌ Cannot say: "Your 5m fails the requirement"
- **Missing:** Design input interface + compliance logic

### 3. PDF Citations in AI Chat
- **AI chat doesn't link to PDF pages**
- **Example:** AI says "Check setbacks requirement"
  - ✅ User can see provision in DCP tab
  - ❌ AI doesn't cite "Marrickville DCP Part 2.3 page 87"

### 4. Lot Size Calculation
- **NSW Planning Portal returns polygon geometry but not lot size (m²)**
- **Workaround:** User must know their lot size
- **Fix needed:** Calculate area from polygon coordinates

### 5. Version Tracking
- **No tracking of DCP/LEP/SEPP changes over time**
- **Cannot answer:** "What changed in the 2024 LEP update?"
- **Database has:** `version_count` column but not populated

### 6. Complete Coverage
- **Council coverage:** Marrickville (100%), Leichhardt (100%), Ashfield (partial)
- **Missing:** 31 other Inner West LGA councils
- **SEPP provisions:** Only 241 provisions (vs 47,818 DCP provisions)

---

## 🔧 **In Progress / Partially Working**

### 1. Granny Flat Questions (80% Complete)
**Current:**
- ✅ "Can I build a granny flat?" → "Yes, permitted in R2"
- ❌ Missing: DCP requirements, lot size check, CDC pathway

**What's Needed:**
- Multi-endpoint synthesis (combine LEP + DCP + SEPP)
- Citation infrastructure (PDF page links)
- Lot size calculation

**Estimate:** 1 day for basic, 7-10 days for full solution

### 2. Factual Lookups (Partial)
**Current:**
- ✅ Height/FSR from NSW Planning Portal
- ⚠️ Setbacks: Generic only (not DCP-specific)
- ❌ Parking: Can find provisions but doesn't calculate spaces

### 3. Synthesis Questions (Limited)
**Current:**
- ✅ "What can I build here?" → Returns capacity + constraints separately
- ❌ Doesn't combine into "You can build up to 2 storeys, X dwellings, here's why"

---

## 📊 **Data Quality & Coverage**

### Database Statistics
| Table | Rows | Coverage |
|-------|------|----------|
| **regulatory_provisions** | 47,818 | Marrickville, Leichhardt, Ashfield DCPs |
| **regulatory_definitions** | 465+ | DCP, LEP, SEPP terms |
| **lep_land_use_table** | ~500 | All NSW zones × development types |
| **housing_sepp_standards** | 33 | SEPP Housing 2021 standards |
| **dcp_precinct_boundaries** | 90 | GeoJSON boundaries for 102 precincts |
| **dcp_general_requirements** | 3,158 | Structured general requirements |

### Data Completeness
**Strengths:**
- ✅ DCP text extraction (MinerU + manual enrichment)
- ✅ 4-layer filtering model implemented
- ✅ Heritage provisions categorized (907 rows)
- ✅ Precinct boundaries mapped

**Gaps:**
- ⚠️ SEPP Housing 2021: Only 241 provisions (incomplete)
- ⚠️ Ashfield DCP: Partial coverage (some sections missing)
- ⚠️ Lot size: Not available from NSW Planning Portal
- ⚠️ Version tracking: Column exists but not populated

---

## 🎯 **Use Cases: Can PlotDetect Handle It?**

### ✅ **Fully Supported**

| Question | Works? | Data Source |
|----------|--------|-------------|
| "What is a habitable room?" | ✅ YES | 465+ definitions |
| "Should I use CDC or DA?" | ✅ YES | Procedural guidance + checklists |
| "Is this property heritage listed?" | ✅ YES | NSW Planning Portal |
| "Can I build a duplex in R2?" | ✅ YES | LEP land use table |
| "What's the maximum building height?" | ✅ YES | NSW Planning Portal spatial layers |
| "Show me parking requirements" | ✅ YES | DCP provisions (text only) |

### ⚠️ **Partially Supported**

| Question | Works? | Limitation |
|----------|--------|------------|
| "Can I build a granny flat?" | ⚠️ 80% | Permissibility only, no DCP synthesis |
| "What are the setback requirements?" | ⚠️ 70% | Shows provisions, no specific numbers |
| "Am I eligible for manor house?" | ⚠️ 60% | SEPP check only, no DCP integration |
| "What can I build here?" | ⚠️ 50% | Separate data, no synthesis |

### ❌ **Not Supported**

| Question | Works? | What's Needed |
|----------|--------|---------------|
| "Does my design comply?" | ❌ NO | Compliance verification endpoint |
| "How many parking spaces do I need for 4 units?" | ❌ NO | Calculation logic |
| "What's my maximum dwelling yield?" | ❌ NO | Lot size + density calculation |
| "What changed in the 2024 DCP?" | ❌ NO | Version tracking |
| "Can I get a CDC?" | ❌ NO | CDC eligibility checker |

---

## 🚀 **Improvement Priority**

### High Priority (User-facing)
1. **Granny flat synthesis** (80% complete) - 1 day for basic
2. **PDF citations in AI chat** - 1 day
3. **Lot size calculation** - 1 day

### Medium Priority (Reliability)
4. **Compliance verification** - 3-5 days
5. **CDC eligibility checker** - 2-3 days
6. **Parking space calculator** - 2 days

### Low Priority (Nice-to-have)
7. **Version tracking** - 5-7 days
8. **Remaining SEPP provisions** - 3-5 days
9. **Ashfield DCP completion** - 2-3 days

---

## 📝 **For Developers**

When asked "Can PlotDetect do X?":

1. **Check this doc first**
2. **Verify against ARCHITECTURE.md** for technical details
3. **Test with actual API** if unsure
4. **Update this doc** when features change

**Last verified:** 2026-01-30
**Next review:** After major feature release
