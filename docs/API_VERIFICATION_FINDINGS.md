# API Verification Findings
**Date:** 2026-02-05
**Test Address:** 185 Parramatta Road, Haberfield NSW 2045
**Expected:** Ashfield R2, Heritage Conservation Area C1

---

## Executive Summary

Tested all 4 endpoints used in assessment workflow. **DCP provisions endpoint working perfectly** (701 provisions). **Property endpoint returning incomplete data** (Zone, LGA, FSR all N/A). **SEPP endpoint has no structured requirements** for dual occupancy (must use full-text API or raw provisions).

### Critical Issues for Screencasts
1. ❌ **Cannot show "FSR 0.5:1" on property card** — property API returns N/A
2. ❌ **Cannot show "Max Height 9m"** — property API returns N/A
3. ❌ **Cannot show SEPP parking requirements** — no structured data for dual occupancy
4. ✅ **CAN show 701 DCP provisions** with correct topic breakdown
5. ✅ **CAN show heritage filtering** (306 heritage provisions)
6. ⚠️  **Heritage subtopics showing "None"** — v2_heritage_element field is NULL (database issue)

---

## 1. /api/property Endpoint

### Request
```
GET /api/property?address=185+Parramatta+Road,+Haberfield+NSW+2045
```

### Response (Partial Data)
```json
{
  "success": true,
  "data": {
    "address": "185 PARRAMATTA ROAD HABERFIELD 2045",
    "lga": "N/A",
    "formerCouncil": "N/A",
    "zone": "N/A",
    "lotAreaSqm": "N/A",
    "lep": {
      "maxFSR": "N/A",
      "maxHeight": "N/A",
      "minLotSize": "N/A"
    },
    "heritage": {
      "isHeritage": true,
      "inHCA": false,
      "hcaCode": "N/A",
      "hcaName": "N/A"
    },
    "tod": {
      "inTod": false,
      "category": "N/A",
      "nearestStation": "N/A",
      "distanceToStationM": "N/A"
    }
  }
}
```

### Analysis
- ✅ Address geocoding works
- ❌ Zone, LGA, Former Council = N/A (should be "R2", "Inner West", "Ashfield")
- ❌ FSR, Height = N/A (should be "0.5:1", "9m")
- ⚠️  Heritage detected (isHeritage: true) but HCA details missing
- ❌ TOD data = N/A

### Impact on User Stories
**CANNOT demonstrate:**
- Property card showing FSR 0.5:1 (LEP control)
- Property card showing Max Height 9m (LEP control)
- Zone badge showing "R2 Low Density Residential"
- Heritage badge showing "C1 - Haberfield Heritage Conservation Area"

**WORKAROUND:**
- Show generic "Property located in Inner West LGA, R2 zone" without specific FSR/height
- OR fix property lookup service to return NSW Planning Portal data

---

## 2. /api/sepp/structured-requirements Endpoint

### Request
```json
POST /api/sepp/structured-requirements
{
  "seppId": "housing_2021",
  "developmentType": "dual_occupancy"
}
```

### Response
```json
{
  "success": true,
  "data": {
    "hasStructuredRequirements": false,
    "message": "No manually curated requirements available for this SEPP and development type. Use full-text API instead."
  }
}
```

### Analysis
- ❌ No structured SEPP Housing requirements for dual occupancy
- Database `sepp_structured_requirements` table may be empty OR
- Only specific dev types have curated requirements (e.g., dwelling_house, not dual_occupancy)

### Impact on User Stories
**CANNOT demonstrate:**
- SEPP & LEP tab showing parking requirements (e.g., "2 spaces per dwelling")
- SEPP Housing Schedule 1 requirements
- TOD parking reduction provisions
- ADG design criteria

**WORKAROUND:**
- Use `/api/sepp/full-text` to get raw SEPP provisions (not structured)
- Check `regulatory_provisions` table for SEPP Housing provisions (document_id LIKE '%SEPP%Housing%')
- Show LEP local provisions instead of SEPP (from property endpoint if fixed)

---

## 3. /api/provisions/for-property Endpoint ✅ WORKING

### Request
```
GET /api/provisions/for-property?lga=Inner+West&zone=R2&former_council=Ashfield&heritage=true&hca=C1
```

### Response
```json
{
  "success": true,
  "data": {
    "summary": {
      "total_provisions": 701,
      "layer_1_generic": 341,
      "layer_2_use_specific": 54,
      "layer_3_condition": 306,
      "layer_4_precinct": 0
    },
    "by_topic": {
      "parking": [76 provisions],
      "waste": [74 provisions],
      "roof": [74 provisions],
      "trees": [52 provisions],
      "demolition": [45 provisions],
      "residential": [41 provisions],
      "general": [38 provisions],
      "materials": [25 provisions],
      "fencing": [24 provisions],
      "character": [24 provisions],
      "verandah": [21 provisions],
      "building_form": [20 provisions],
      "access": [19 provisions],
      "additions": [19 provisions],
      "signage": [18 provisions]
    }
  }
}
```

### Analysis
- ✅ 701 provisions returned (correct for Ashfield R2 + heritage)
- ✅ 4-layer filtering working (341 generic, 54 use-specific, 306 heritage condition)
- ✅ Topic grouping correct (parking 76, waste 74, roof 74, etc.)
- ✅ Heritage provisions: 306 (Layer 3 condition)
- ✅ Numeric provisions: 77 (quantitative controls)
- ⚠️  Heritage subtopics showing "None" — v2_heritage_element is NULL (database issue)

### Impact on User Stories
**CAN demonstrate:**
- DCP Provisions tab showing 701 provisions
- Topic filtering: Parking (76), Heritage (306), Setbacks (4), etc.
- Heritage button showing 306 provisions
- Layer breakdown: 341 generic, 54 use-specific, 306 condition
- Numeric provision badge showing 77 quantitative controls

**Heritage Subtopic Issue:**
- Database has v2_heritage_element = NULL for all 306 heritage provisions
- Should be populated with: "Additions", "Demolition", "Materials", "Character", "Fencing", etc.
- Currently shows "None: 306" instead of proper breakdown
- **THIS IS A DATA QUALITY ISSUE** per CLAUDE.md rules (>2% data affected = Priority 1)

---

## 4. /api/capacity/calculate Endpoint ⚠️ PARTIAL

### Request
```json
POST /api/capacity/calculate
{
  "address": "185 Parramatta Road, Haberfield NSW 2045",
  "lotSize": 600,
  "frontage": 15.0,
  "zone": "R2",
  "lga": "Inner West",
  "former_council": "Ashfield"
}
```

### Response
```json
{
  "success": true,
  "capacity": {
    "maxGFA": null,
    "gfaSource": "",
    "maxHeight": null,
    "maxFSR": null,
    "approxStoreys": null,
    "lotArea": 600
  },
  "setbacks": {
    "type": "not_available",
    "message": "Setback data not yet available for Unknown",
    "method": "Refer to DCP provisions or contact Council"
  },
  "parking": [],
  "landscaping": [],
  "lepClauses": [...]
}
```

### Analysis
- ⚠️  Endpoint exists but returns mostly null values
- ⚠️  Setbacks: "not_available" (should calculate from DCP numeric provisions)
- ⚠️  Max GFA, FSR, Height all null
- ✅ LEP clauses returned (4.3 Height of buildings)

### Impact on User Stories
**CANNOT demonstrate:**
- Buildable envelope calculations (max GFA, setbacks, footprint)
- "Rear setback: 6m" (fabricated in previous screencasts — NOT IN API)
- "Max 300 sqm floor area" (FSR x lot area)

**WORKAROUND:**
- Show DCP numeric provisions instead (77 provisions with v2_has_numeric_value=true)
- Calculate client-side: FSR 0.5:1 x 600 sqm = 300 sqm (IF property API returns FSR)

---

## Recommendations for Screencasts

### Architect Screencast (Buildable Envelope)
**CANNOT show:**
- "FSR 0.5:1" on property card (API returns N/A)
- "Max Height 9m" on property card (API returns N/A)
- "Rear setback 6m" from capacity API (returns "not_available")

**CAN show:**
- 701 DCP provisions filtered by topic
- 4 setback provisions (topic filter)
- 77 numeric provisions (quantitative controls)
- Heritage button: 306 provisions

**REVISED USER STORY:**
- Architect needs to find **applicable DCP provisions** for buildable envelope
- Shows filtering by topic (setbacks, height, solar access)
- Shows numeric provision badge (77 quantitative controls)
- Does NOT claim specific "6m" values (those must come from reading provision text)

### Town Planner Screencast (DA Preparation)
**CANNOT show:**
- SEPP parking requirements (no structured data)
- Property card with FSR/height/zone badges

**CAN show:**
- 701 DCP provisions organized by DA section
- Parking topic: 76 provisions
- Heritage topic: 306 provisions
- Waste topic: 74 provisions
- All provisions with PDF citations

**REVISED USER STORY:**
- Town planner needs to **cite all applicable provisions** in DA report
- Shows topic filtering (parking 76, heritage 306, waste 74)
- Shows provision text + PDF page citation
- Does NOT make claims about "2 spaces per dwelling" (must come from provision text)

### Developer Screencast (Feasibility)
**CANNOT show:**
- FSR bonus from TOD (tod API returns N/A)
- SEPP parking reduction (no structured data)

**CAN show:**
- 701 provisions filtered by zone + heritage
- Parking provisions: 76
- Topic-based compliance checklist

---

## Database Issues to Fix

### Priority 1: Heritage Subtopics
**Issue:** v2_heritage_element = NULL for all 306 heritage provisions
**Expected:** Should be "Additions", "Demolition", "Materials", "Character", "Fencing", "Roof", "Verandah", "Signage", etc.
**Impact:** Heritage subtopic filtering doesn't work (shows "None: 306")
**Affected Data:** 306 / 701 = 43.7% of Ashfield R2 heritage provisions
**CLAUDE.md Rule:** >2% = Priority 1 (MUST FIX)

**Fix Required:**
```sql
-- Check current state
SELECT v2_heritage_element, COUNT(*)
FROM regulatory_provisions
WHERE v2_marker = 'heritage'
  AND document_id ILIKE '%Ashfield%'
GROUP BY v2_heritage_element;

-- Expected result should show:
-- Additions: 19
-- Demolition: 45
-- Materials: 25
-- Character: 24
-- Fencing: 21
-- NOT: NULL: 306
```

### Priority 2: Property Lookup Service
**Issue:** /api/property returns N/A for zone, LGA, FSR, height
**Expected:** Should return R2, Inner West, Ashfield, FSR 0.5:1, Height 9m
**Impact:** Cannot demonstrate property card with LEP controls
**Root Cause:** PropertyDataService.getPropertyComplianceData() not connecting to NSW Planning Portal OR geocoding failing

---

## Conclusion

### What We CAN Show (Verified with Real APIs)
1. ✅ 701 DCP provisions filtered by zone + heritage (4-layer model working)
2. ✅ Topic filtering: parking (76), heritage (306), waste (74), roof (74), etc.
3. ✅ Heritage button: 306 provisions (Layer 3 condition)
4. ✅ Numeric provisions: 77 quantitative controls
5. ✅ PDF citations on all provisions
6. ✅ Provision text with full content

### What We CANNOT Show (APIs Return N/A or No Data)
1. ❌ Property card with FSR 0.5:1, Max Height 9m
2. ❌ Zone badge "R2 Low Density Residential"
3. ❌ Heritage badge "C1 - Haberfield HCA"
4. ❌ SEPP parking requirements (no structured data)
5. ❌ TOD parking reduction (tod data N/A)
6. ❌ Setback calculations (capacity API returns "not_available")
7. ❌ Heritage subtopics (v2_heritage_element NULL — database issue)

### Action Required
1. **Fix property lookup service** — PropertyDataService needs to return real NSW Planning Portal data
2. **Fix heritage subtopics** — Populate v2_heritage_element field (Priority 1 data quality issue)
3. **Check SEPP structured requirements** — Either populate table OR revise screencasts to show raw SEPP provisions
4. **Revise all 5 screencasts** — Remove fabricated claims ("6m rear setback", "FSR 0.5:1"), show what APIs actually return
