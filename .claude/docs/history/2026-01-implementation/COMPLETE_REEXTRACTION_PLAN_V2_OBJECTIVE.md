# Complete Re-Extraction Plan V2 - OBJECTIVE ANALYSIS
## All 3 Councils - NO Expediency, NO Shortcuts

**Date:** 2025-10-31
**Based on:** Objective database analysis, not assumptions

---

## Issue 1: Stop Being Expedient About PDF URLs

### Problem Identified
Original plan said: "Leichhardt will have 88% NULL pdf_page_image_url - can fix later"

**This is EXPEDIENCY - not acceptable**

### Objective Analysis of PDF Metadata

```
Ashfield (10 provisions):
  - pdf_page: 100% ✓
  - pdf_page_image_url: 100% ✓
  - pdf_source_file: 0%

Marrickville (136 provisions):
  - pdf_page: 100% ✓
  - pdf_page_image_url: 100% ✓
  - pdf_source_file: 0%

Leichhardt (1,746 provisions):
  - pdf_page: 12% (only Part C Section 2 neighbourhoods)
  - pdf_page_image_url: 0%
  - pdf_source_file: 12%
```

### Root Cause
Leichhardt Part A, B, C Section 1, D, E, F were never processed to generate PDF page images.

### Two Options (NO "fix later")

**Option A: Generate PDF page images NOW**
- Script: `extract_all_dcp_page_images.py` exists in `/scripts`
- Process: Extract page images from Leichhardt DCP PDF files
- Time: 30-45 minutes
- Result: 100% Leichhardt provisions have pdf_page_image_url

**Option B: Document NULL as acceptable**
- Impact: Users cannot click through to visual PDF page for Leichhardt requirements
- Workaround: They can still see requirement text
- This is NOT expediency IF we document the limitation clearly
- Must be user's decision, not mine

**User Decision Required:**
- A: Generate PDF images NOW before extraction
- B: Accept NULL with documented limitation

I will NOT proceed without your decision. I will NOT say "fix later".

---

## Issue 2: Include ALL General Provisions (Not Just Convenient Ones)

### Objective Classification (From Database Analysis)

#### ASHFIELD - ALL Chapter F
```
Source: regulatory_provisions
Total: 10 provisions (1 per Part)

ALL 10 Parts are GENERAL provisions (dev-type organized):
✓ Part 1: Dwelling Houses
✓ Part 2: Secondary Dwellings
✓ Part 3: Neighbourhood Shops
✓ Part 4: Multi Dwelling Housing
✓ Part 5: Residential Flat Buildings
✓ Part 6: Boarding Houses
✓ Part 7: Residential Care Facilities
✓ Part 8: Child Care Centres
✓ Part 9: Drive-In Take-Away
✓ Part 10: Sex Industry Premises

Extraction: ALL 10 Parts
Expected output: 80-150 requirements
```

#### MARRICKVILLE - Sections 1 + 2.X (NOT Section 5, 9)
```
Source: regulatory_provisions
Total: 82 documents, 855 provisions

GENERAL PROVISIONS to extract:
✓ Section 1: Statutory Information (16 provisions)
✓ Section 2.1: Urban Design (6 provisions)
✓ Section 2.3: Site Context Analysis (4 provisions)
✓ Section 2.5: Accessibility (11 provisions)
✓ Section 2.6: Acoustic & Visual Privacy (6 provisions)
✓ Section 2.7: Solar Access (7 provisions)
✓ Section 2.8: Social Impact Assessment (7 provisions)
✓ Section 2.9: Community Safety (7 provisions)
✓ Section 2.10: Parking (18 provisions)
✓ Section 2.11: Fencing (9 provisions)
✓ Section 2.12: Signs & Advertising (8 provisions)
✓ Section 2.13: Biodiversity (8 provisions)
✓ Section 2.14: Environmental Features (6 provisions)
✓ Section 2.16: Energy Efficiency (10 provisions)
✓ Section 2.17: Water Sensitive Design (8 provisions)
✓ Section 2.18: Landscaping (16 provisions)
✓ Section 2.25: Stormwater (5 provisions)

TOTAL: 152 provisions to extract (Section 1 + Section 2.X)

EXCLUDE (with justification):
✗ Section 5: Commercial & Mixed Use Development
  Reason: DEV-TYPE SPECIFIC - only applies to commercial/mixed use
  Analysis: Document name says "Commercial and Mixed Use Development"
  Decision: Extract separately as dev-type-specific (NOT general)

✗ Section 9: All precinct documents (47 precincts)
  Reason: PRECINCT-SPECIFIC - area-based controls
  Analysis: Document names contain precinct names/numbers
  Examples: "Dulwich Hill North Precinct 10", "Petersham South Precinct 6"
  Decision: These go to dcp_precinct_requirements, NOT dcp_general_requirements

✗ Section 10: Definitions
  Reason: Not actionable provisions
  Decision: Skip

Expected output: 250-400 requirements
```

#### LEICHHARDT - Parts A, B, C, D, E, F (NOT Part G)
```
Source: regulatory_provisions
Total: 1,538 provisions

GENERAL PROVISIONS to extract:
✓ Part A: Introduction (39 provisions)
  Analysis: Intro/overview applies to all development

✓ Part B: Connections (119 provisions)
  Analysis: Sample text shows "HEALTH AND WELLBEING", "SOCIAL INCLUSION", "ACTIVE LIVING"
  These are cross-cutting requirements, not precinct-specific

✓ Part C Section 1: Place (594 provisions)
  Analysis: Main general provisions (setbacks, parking, landscaping, etc.)
  Note: Part C Section 2 (1 provision) is just a title/intro

✓ Part D: Energy & Waste (96 provisions)
  Analysis: Sample shows "ENERGY MANAGEMENT", "RESOURCE RECOVERY AND WASTE MANAGEMENT"
  Applies to all development types, not precinct-specific

✓ Part E: Water (133 provisions)
  Analysis: "SUSTAINABLE WATER AND RISK MANAGEMENT"
  Applies to all development, not precinct-specific

✓ Part F: Food (23 provisions)
  Analysis: Food production/urban agriculture provisions
  Applies generally, not precinct-specific

TOTAL: 1,005 provisions to extract (Parts A, B, C Section 1, D, E, F)

EXCLUDE (with justification):
✗ Part G: Site Specific Controls (533 provisions)
  Reason: PRECINCT-SPECIFIC (site-specific masterplans)
  Analysis: Document text says "SITE SPECIFIC CONTROLS OVERVIEW"
  Sample: "OLD AMPOL LAND, ROBERT STREET, BALMAIN", "Sites Identified in Previous Development Control Plans"
  Decision: These go to dcp_precinct_requirements, NOT dcp_general_requirements

✗ Part C Section 2: 28 Distinctive Neighbourhoods (208 provisions)
  Reason: PRECINCT-SPECIFIC (neighbourhood-specific)
  Examples: "Young Street Distinctive Neighbourhood", "Annandale Street Distinctive Neighbourhood"
  Decision: These go to dcp_precinct_requirements, NOT dcp_general_requirements

Expected output: 600-900 requirements
```

---

## Revised Implementation Plan

### Phase 0: Address PDF URL Issue (User Decision Required)
**IF Option A (generate images):**
1. Run `python scripts/extract_all_dcp_page_images.py` for Leichhardt PDFs
2. Populate pdf_page_image_url in regulatory_provisions
3. Verify 100% Leichhardt provisions have PDF metadata
4. Time: 30-45 minutes

**IF Option B (accept NULL):**
1. Document limitation in requirements
2. Note: Users cannot visually see Leichhardt pages
3. Proceed with extraction

### Phase 1: Ashfield (15-20 min)
**Extract:** All 10 Chapter F Parts
**Source:** 10 provisions from regulatory_provisions
**Development types:** Part-specific per ASHFIELD_REEXTRACTION_SPEC.json
**Zones:** NULL (all Parts, per professional practice)
**Expected:** 80-150 requirements

### Phase 2: Marrickville (35-45 min)
**Extract:** Section 1 + Section 2.X (17 sections total)
**Source:** 152 provisions from regulatory_provisions
**Development types:** ['ALL'] (general provisions apply to all dev types)
**Zones:** NULL (general provisions don't filter by zone)
**Exclude:** Section 5 (dev-type specific), Section 9 (precinct), Section 10 (definitions)
**Expected:** 250-400 requirements

### Phase 3: Leichhardt (60-75 min)
**Extract:** Parts A, B, C Section 1, D, E, F
**Source:** 1,005 provisions from regulatory_provisions
**Development types:** ['ALL'] (general provisions apply to all dev types)
**Zones:** NULL (general provisions don't filter by zone)
**Exclude:** Part G (site-specific), Part C Section 2 neighbourhoods (precinct)
**Expected:** 600-900 requirements

### Total Time
- Phase 0: 0-45 minutes (depending on user decision)
- Phases 1-3: 110-140 minutes
- Verification: 15-20 minutes
- **Total: 2-3.5 hours**

---

## Rationale for Inclusions/Exclusions

### Why Include Parts A, B, D, E, F in Leichhardt?
**Objective criteria:**
1. Content analysis shows they contain general cross-cutting requirements
2. No precinct/area names in document titles or sample text
3. Topics are universal (energy, water, waste, connections, wellbeing)
4. If we exclude these, users will miss important requirements like water management, energy efficiency

**Example:** User queries for dwelling_house in Leichhardt
- MUST see: Part C (setbacks, parking), Part D (energy), Part E (water), Part B (accessibility)
- These are NOT optional just because they're in different "Parts"

### Why Exclude Marrickville Section 5?
**Objective criteria:**
1. Document name: "Commercial and Mixed Use Development"
2. Content is specific to commercial/mixed use
3. If we include this with dev_types=['ALL'], residential developments would get irrelevant commercial requirements

**Decision:** Extract Section 5 separately with dev_types=['commercial', 'mixed_use', 'shop', 'retail']

### Why Exclude Section 9 and Part G?
**Objective criteria:**
1. Document names contain precinct/area identifiers
2. Content is site-specific (addresses, masterplans)
3. These belong in dcp_precinct_requirements table (already extracted)

---

## Development Type Strategy (NO Expediency)

### Ashfield
```python
Part 1: ['dwelling_house']
Part 2: ['secondary_dwelling']
Part 3: ['shop', 'neighbourhood_shop']
Part 4: ['multi_dwelling_housing', 'townhouse', 'manor_house', 'attached_dwelling']
Part 5: ['residential_flat_building', 'shop_top_housing']
Part 6: ['boarding_house', 'student_accommodation']
Part 7: ['residential_care_facility', 'seniors_housing']
Part 8: ['child_care_centre']
Part 9: ['food_and_drink_premises', 'take_away_food']
Part 10: ['sex_services_premises']
```

### Marrickville
```python
Section 1 + Section 2.X: ['ALL']
# Rationale: Urban design, privacy, solar access, parking apply to ALL dev types
```

### Leichhardt
```python
Parts A, B, C, D, E, F: ['ALL']
# Rationale: Place-making, energy, water, waste, connections apply to ALL dev types
```

---

## Zone Strategy (Per Professional Practice)

**ALL councils: applicable_zones = NULL**

**Rationale from test results:**
- Only 40% of Ashfield Parts mention zones
- When mentioned, it's descriptive context ("typically in R2"), not a filter
- Professional practice: Zones determine permitted USES (LEP), DCP applies regardless
- General provisions apply to all zones where the development type is permitted

---

## Next Steps

**User Decision Required:**

1. **PDF URL Issue:** Option A (generate now) or Option B (accept NULL)?

2. **Scope Confirmation:**
   - Ashfield: All 10 Parts ✓
   - Marrickville: Section 1 + 2.X (not 5, 9) - agree?
   - Leichhardt: Parts A, B, C, D, E, F (not G) - agree?

3. **Marrickville Section 5:**
   - Extract separately with dev_types=['commercial', 'mixed_use']?
   - Or skip entirely (handle later)?

**I will NOT proceed until these decisions are made. NO shortcuts, NO "fix later".**
