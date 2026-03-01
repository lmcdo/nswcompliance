# Hybrid Implementation: Scope & Safety Check

## Summary of Work Done So Far

### Phase 1: Database Migration ✓ COMPLETE
**Target:** `dcp_general_requirements` table ONLY
**Changes:**
- Added `user_category` VARCHAR(50)
- Added `priority_level` INTEGER DEFAULT 2
- Added `section_type` VARCHAR(50)
- Added `display_in_ui` BOOLEAN DEFAULT TRUE
- Created indexes on new fields

**Result:** 4 new columns, 3 new indexes

### Phase 2: Clean "Other" Category ✓ COMPLETE
**Target:** 152 provisions in `dcp_general_requirements` WHERE `category = 'other'`
**Changes:**
- Used keyword matching to assign `user_category` values
- Identified `section_type` (objective, performance_criteria, control)
- Set `priority_level` based on category importance

**Result:**
- 59 provisions recategorized (38.8% reduction)
- 93 provisions remain as "other" (down from 152)
- Breakdown:
  - Environmental & Sustainability: 21
  - Access & Parking: 15
  - Documentation: 12
  - Amenity & Privacy: 6
  - Heritage & Character: 4
  - Site & Building Envelope: 1
  - Still unmapped: 93

---

## What Tables Exist & What They're Used For

### Tables with DCP Requirements/Provisions:

1. **`dcp_general_requirements`** ← **OUR TARGET**
   - Used by: `dcp-complete/route.ts` API
   - Purpose: General (Chapter F) requirements for all 3 former councils
   - Row count: ~1460 provisions
   - Has hybrid fields: ✓ YES (added in Phase 1)
   - Columns queried by API: `id, category, subcategory, requirement_text, verbatim_source_text, value_numeric, value_min, value_max, unit, has_conditionals, conditional_text, confidence, pdf_page, pdf_page_image_url, pdf_path`

2. **`dcp_precinct_requirements`**
   - Used by: `dcp-complete/route.ts` API
   - Purpose: Precinct-specific requirements (neighborhood/area controls)
   - Has hybrid fields: ✗ NO
   - Columns queried by API: `precinct_id, precinct_name, category, subcategory, requirement_text, value_numeric, unit, has_conditionals, conditional_text, confidence, pdf_pages, pdf_page_image_url`

3. **`dcp_general_provisions`**
   - Used by: `dcp-complete/route.ts` API (as JOIN reference)
   - Purpose: General provisions (Chapter F) - source text
   - Has hybrid fields: ✗ NO
   - Not a direct target - just referenced for PDF page fallback

4. **`dcp_precinct_provisions`**
   - Used by: `dcp-complete/route.ts` API
   - Purpose: Precinct-specific provisions - source text
   - Has hybrid fields: ✗ NO
   - Not a direct target

5. **Other tables** (backups, legacy, views)
   - Not used by current API
   - Safe to ignore

---

## Current API Queries: Will They Break?

### Query 1: General Requirements (Ashfield)
```sql
SELECT DISTINCT ON (dgr.id)
  dgr.id,
  dgr.category,           -- ✓ SAFE: Existing field, untouched
  dgr.subcategory,        -- ✓ SAFE: Existing field, untouched
  dgr.requirement_text,   -- ✓ SAFE: Existing field, untouched
  dgr.verbatim_source_text,
  dgr.value_numeric,
  dgr.value_min,
  dgr.value_max,
  dgr.unit,
  dgr.has_conditionals,
  dgr.conditional_text,
  dgr.confidence,
  COALESCE(dgr.pdf_page, dgp.pdf_page) as pdf_page,
  COALESCE(dgr.pdf_page_image_url, dgp.pdf_page_image_url) as pdf_page_image_url,
  COALESCE(dgr.pdf_path, dgp.pdf_path) as pdf_path
FROM dcp_general_requirements dgr
LEFT JOIN dcp_general_provisions dgp ON dgp.id = dgr.source_provision_ids[1]
WHERE dgr.lga = $1
AND $2 = ANY(dgr.applicable_zones)
AND $3 = ANY(dgr.development_types)
AND dgr.former_council = $4
ORDER BY dgr.id
```

**Impact:** ✓ NO BREAKING CHANGES
- API does NOT query `user_category`, `priority_level`, `section_type`, or `display_in_ui`
- API only queries `category` (existing field, unchanged)
- New fields are NULL-safe (won't cause errors)

### Query 2: Precinct Requirements
```sql
SELECT
  dpr.precinct_id,
  dpr.precinct_name,
  dpr.category,           -- ✓ SAFE: dcp_precinct_requirements has no hybrid fields
  dpr.subcategory,
  dpr.requirement_text,
  dpr.value_numeric,
  dpr.unit,
  dpr.has_conditionals,
  dpr.conditional_text,
  dpr.confidence,
  dpr.pdf_pages[1] as pdf_page,
  dpr.pdf_page_image_url
FROM dcp_precinct_requirements dpr
WHERE dpr.precinct_id = $1
ORDER BY dpr.category, dpr.id
```

**Impact:** ✓ NO BREAKING CHANGES
- This table doesn't have hybrid fields at all
- Nothing changed

---

## What Phase 3 Would Do

**Phase 3: Categorize ALL Provisions**

**Target:** All 1460 provisions in `dcp_general_requirements` (not just "other")

**What it does:**
1. Maps existing `category` values → `user_category` values
   - Example: `category='parking'` → `user_category='access_parking'`
   - Example: `category='setbacks'` → `user_category='site_building_envelope'`
   - Example: `category='heritage'` → `user_category='heritage_character'`

2. Sets `priority_level` for provisions without one
   - Critical categories (site envelope, amenity): priority 1
   - All others: priority 2

3. Sets `section_type = 'control'` for provisions without one

**Impact on API:** ✓ NO BREAKING CHANGES
- API still queries `category` field (unchanged)
- New fields (`user_category`, `priority_level`, `section_type`) are not queried by current API
- This is prep work for FUTURE UI improvements

---

## Safety Confirmation

### ✓ Will existing pipeline work?
**YES** - Current API queries only use existing fields:
- `category` (unchanged)
- `subcategory` (unchanged)
- `requirement_text` (unchanged)
- All other existing fields (unchanged)

### ✓ Will new fields cause errors?
**NO** - New fields have safe defaults:
- `user_category` VARCHAR(50) DEFAULT NULL (safe)
- `priority_level` INTEGER DEFAULT 2 (safe)
- `section_type` VARCHAR(50) DEFAULT NULL (safe)
- `display_in_ui` BOOLEAN DEFAULT TRUE (safe)

### ✓ Can we test before deploying?
**YES** - We have backup:
- `backups/dcp_general_requirements_before_hybrid_20251109_174802.json` (1460 provisions)
- Can restore if anything goes wrong

### ✓ Which tables are affected?
**ONLY `dcp_general_requirements`**
- `dcp_precinct_requirements` - NOT AFFECTED
- `dcp_general_provisions` - NOT AFFECTED
- All other tables - NOT AFFECTED

---

## Recommendation

**SAFE TO PROCEED with Phase 3** because:

1. **No breaking changes** - API doesn't query new fields
2. **Backwards compatible** - All new fields have safe defaults
3. **Single table scope** - Only touching `dcp_general_requirements`
4. **Backup exists** - Can restore if needed
5. **Preparation for future** - Sets up UI improvements without disrupting current functionality

**When UI is updated** (later), we'll:
1. Modify API to SELECT new fields (`user_category`, `priority_level`, `section_type`)
2. Update `GeneralDCPSection.tsx` to group by `user_category` instead of `category`
3. Add priority badges and icons

But that's a FUTURE step - not required now.

---

## Phase 3 Execution Plan

1. Run `phase3_categorize_all_provisions.py`
2. Verify results:
   - Check `user_category` distribution
   - Verify `priority_level` assignments
   - Confirm unmapped provisions count
3. Test current API still works (make test request to `/api/compliance/dcp-complete`)
4. If all good → commit changes
5. If issues → restore from backup

**Estimated time:** 5 minutes
**Risk level:** LOW
