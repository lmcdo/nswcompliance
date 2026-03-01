# How to Source ADG (Apartment Design Guide) Data

**Date:** 2025-11-05
**Status:** ✅ COMPLETED - ADG Data Successfully Inserted

---

## ✅ Completion Status

**Task Completed:** 2025-11-05 at 09:15

| Component | Status |
|-----------|--------|
| `setback_rules` table | ✅ Created |
| ADG statutory standards | ✅ 12 standards inserted |
| API endpoint `/api/setbacks/adg` | ✅ Working |
| Height categories | ✅ All 3 working (Up to 12m, 12-25m, Over 25m) |
| Component integration | ✅ Already integrated in ComplianceDashboard |

---

## Summary

The **ADG (Apartment Design Guide) building separation standards** are sourced from the official NSW Government planning documents and inserted into the database using a Python script.

---

## Data Source

### Official Document

**Document:** NSW Apartment Design Guide - Part 3: Siting the Development
**Section:** 3F-1 Visual Privacy - Design Criteria 1
**Page:** 63
**Legal Status:** STATUTORY (Referenced by SEPP (Housing) 2021)
**URL:** https://www.planning.nsw.gov.au/sites/default/files/2023-03/apartment-design-guide-part-3-siting-the-development.pdf

### What the Standards Cover

The ADG specifies **minimum building separation distances** for apartment developments:

- **Side boundaries:** Distances from building to side property line
- **Rear boundaries:** Distances from building to rear property line
- **Room types:**
  - Habitable rooms (bedrooms, living rooms) and balconies
  - Non-habitable rooms (bathrooms, laundries, storage)
- **Building heights:**
  - Up to 12m (up to 4 storeys)
  - 12m-25m (5-8 storeys)
  - Over 25m (9+ storeys)

---

## Standards Summary

### Low Rise (up to 12m / 4 storeys)

| Boundary | Room Type | Minimum Setback |
|----------|-----------|-----------------|
| Side     | Habitable | **6m** |
| Rear     | Habitable | **6m** |
| Side     | Non-habitable | **3m** |
| Rear     | Non-habitable | **3m** |

### Mid Rise (12m-25m / 5-8 storeys)

| Boundary | Room Type | Minimum Setback |
|----------|-----------|-----------------|
| Side     | Habitable | **9m** |
| Rear     | Habitable | **9m** |
| Side     | Non-habitable | **4.5m** |
| Rear     | Non-habitable | **4.5m** |

### High Rise (over 25m / 9+ storeys)

| Boundary | Room Type | Minimum Setback |
|----------|-----------|-----------------|
| Side     | Habitable | **12m** |
| Rear     | Habitable | **12m** |
| Side     | Non-habitable | **6m** |
| Rear     | Non-habitable | **6m** |

---

## Development Types Covered

The ADG standards apply to:
- Multi-dwelling housing
- Residential flat buildings
- Shop-top housing
- Mixed-use developments (residential component)

---

## How to Populate the Database

### Step 1: Verify Database Table Exists

**Check if the `setback_rules` table exists:**

```sql
SELECT * FROM setback_rules LIMIT 1;
```

**If table doesn't exist, create it:**

```bash
psql -d nsw_planning -f migrations/create_setback_rules_table.sql
```

---

### Step 2: Run the Insertion Script

**Script:** `insert_adg_statutory_standards.py`

```bash
python insert_adg_statutory_standards.py
```

**Expected Output:**
```
================================================================================
INSERTING ADG STATUTORY BUILDING SEPARATION STANDARDS
================================================================================

Source: NSW Apartment Design Guide - Part 3: Siting the Development
Section: 3F-1 Visual Privacy - Design Criteria 1
Legal Status: STATUTORY (Referenced by SEPP (Housing) 2021)

[1/4] Verifying setback_rules table exists...
[OK] setback_rules table found

[2/4] Inserting 12 ADG statutory standards...
--------------------------------------------------------------------------------
  [1/12] up to 12m (4 storeys)    | side | habitable    | 6.0m
  [2/12] up to 12m (4 storeys)    | rear | habitable    | 6.0m
  [3/12] up to 12m (4 storeys)    | side | non_habitable | 3.0m
  [4/12] up to 12m (4 storeys)    | rear | non_habitable | 3.0m
  [5/12] up to 25m (5-8 storeys)  | side | habitable    | 9.0m
  [6/12] up to 25m (5-8 storeys)  | rear | habitable    | 9.0m
  [7/12] up to 25m (5-8 storeys)  | side | non_habitable | 4.5m
  [8/12] up to 25m (5-8 storeys)  | rear | non_habitable | 4.5m
  [9/12] over 25m (9+ storeys)    | side | habitable    | 12.0m
  [10/12] over 25m (9+ storeys)   | rear | habitable    | 12.0m
  [11/12] over 25m (9+ storeys)   | side | non_habitable | 6.0m
  [12/12] over 25m (9+ storeys)   | rear | non_habitable | 6.0m

[OK] Inserted 12/12 standards

[3/4] Verifying insertion...
[OK] ADG 3F-1 Standards:
  - Total rules: 12
  - Height categories: 3
  - Boundary types: 2

================================================================================
INSERTION COMPLETE
================================================================================
```

---

### Step 3: Verify Data is in Database

**Query to check:**
```sql
SELECT
  ref_number,
  boundary_type,
  setback_meters,
  development_type,
  site_condition
FROM setback_rules
WHERE ref_number = 'ADG 3F-1'
ORDER BY setback_meters DESC;
```

**Expected:** 12 rows returned

---

### Step 4: Test the API

**Test with curl:**
```bash
curl "http://localhost:3007/api/setbacks/adg?building_height=15&development_type=residential_flat_building"
```

**Expected Response:**
```json
{
  "applies": true,
  "building_height_meters": 15,
  "height_category": "Mid Rise",
  "storey_range": "5-8 storeys",
  "development_type": "residential_flat_building",
  "setbacks": {
    "side": {
      "habitable_rooms_and_balconies": 9,
      "non_habitable_rooms": 4.5
    },
    "rear": {
      "habitable_rooms_and_balconies": 9,
      "non_habitable_rooms": 4.5
    }
  },
  "source": {
    "document": "NSW Apartment Design Guide",
    "section": "3F-1 Building Separation",
    "authority": "SEPP (Housing) 2021",
    "legal_status": "STATUTORY - NOT DISCRETIONARY"
  }
}
```

---

## Data Extraction Method

The standards were **manually extracted** from the official PDF document:

1. **Document Review:** Read page 63 of ADG Part 3
2. **Data Extraction:** Extract the building separation table
3. **Verification:** Cross-check against SEPP (Housing) 2021 references
4. **Encoding:** Hard-code into Python insertion script
5. **Validation:** Test against known apartment developments

**Why manual extraction?**
- Only 12 data points (manageable)
- Statutory requirements (must be 100% accurate)
- Tables in PDF are simple and unambiguous
- Official source document is authoritative

---

## Database Schema

### Table: `setback_rules`

**Key fields for ADG standards:**

```sql
CREATE TABLE setback_rules (
  id SERIAL PRIMARY KEY,
  ref_number TEXT,                    -- 'ADG 3F-1'
  boundary_type TEXT,                 -- 'side', 'rear'
  building_element TEXT,              -- 'all' (for habitable), 'non_habitable'
  development_type TEXT[],            -- Array of dev types
  site_condition TEXT[],              -- Array: ['building_height_up_to_12m'], etc.
  setback_meters NUMERIC(5,2),        -- 6.0, 9.0, 12.0, etc.
  document_type TEXT,                 -- 'SEPP'
  document_name TEXT,                 -- Full ADG document name
  priority INTEGER,                   -- 1 (SEPP level)
  manual_verified BOOLEAN,            -- true
  notes TEXT                          -- Source URL and page reference
);
```

---

## API Integration

### API Route

**File:** `frontend-nextjs/app/api/setbacks/adg/route.ts`

**Endpoint:** `GET /api/setbacks/adg`

**Query Parameters:**
- `building_height` (required): Height in meters
- `development_type` (required): e.g., 'residential_flat_building'

**Logic:**
1. Validate building height and development type
2. Determine height category (low/mid/high rise)
3. Query `setback_rules` table for matching standards
4. Return formatted response with side/rear setbacks

---

### Component Integration

**File:** `frontend-nextjs/components/compliance/ADGBuildingSeparationTable.tsx`

**Renders:**
- Height category badge
- Statutory requirement alert (red)
- Setback table (side/rear × habitable/non-habitable)
- Additional requirements
- Source citation with PDF link

**Usage in ComplianceDashboard:**
```typescript
<ADGBuildingSeparationTable
  buildingHeight={buildingHeight}  // from user input or property data
  developmentType={developmentType} // from user selection
/>
```

---

## Maintenance

### When to Update

Update ADG data when:
1. NSW Department of Planning publishes new ADG version
2. SEPP (Housing) 2021 is amended with new separation standards
3. Building height categories are changed

### How to Update

1. Download latest ADG PDF from NSW Planning website
2. Compare Section 3F-1 standards with existing data
3. Update `insert_adg_statutory_standards.py` if changed
4. Delete old standards: `DELETE FROM setback_rules WHERE ref_number = 'ADG 3F-1';`
5. Re-run insertion script
6. Test API endpoint

---

## Data Verification

### Cross-Reference Sources

**Primary source:** ADG PDF
**Secondary verification:**
- SEPP (Housing) 2021 text
- NSW Planning Portal guidance
- Council DCP references to ADG

**Test addresses for verification:**
- Mid-rise apartments in Marrickville (5-8 storeys)
- High-rise apartments in Sydney CBD (9+ storeys)
- Low-rise multi-dwelling in Leichhardt (up to 4 storeys)

---

## Troubleshooting

### Error: "setback_rules table not found"

**Solution:** Create the table first
```bash
psql -d nsw_planning -f migrations/create_setback_rules_table.sql
```

### Error: "Failed to fetch ADG standards from database"

**Possible causes:**
1. Table is empty → Run insertion script
2. Development type mismatch → Check if dev type is ADG-applicable
3. Database connection error → Check .env file

**Solution:**
```bash
# Check if data exists
psql -d nsw_planning -c "SELECT COUNT(*) FROM setback_rules WHERE ref_number = 'ADG 3F-1';"

# Should return: 12

# If returns 0, run:
python insert_adg_statutory_standards.py
```

### Error: "Duplicate key violation"

**Cause:** Standards already inserted

**Solution:**
```sql
-- Delete existing standards first
DELETE FROM setback_rules WHERE ref_number LIKE 'ADG 3F-1%';

-- Then re-run insertion script
```

---

## Related Files

| File | Purpose |
|------|---------|
| `insert_adg_statutory_standards.py` | **Main insertion script** |
| `extract_adg_building_separation.py` | Extract data from PDF (experimental) |
| `test_adg_integration.py` | Integration tests |
| `cleanup_adg_duplicates.py` | Remove duplicate entries |
| `check_adg_provisions.py` | Verify data in database |
| `find_adg_data.py` | Search for ADG-related data |

---

## Complete Workflow

### First Time Setup:

```bash
# 1. Create database table
psql -d nsw_planning -f migrations/create_setback_rules_table.sql

# 2. Insert ADG standards
python insert_adg_statutory_standards.py

# 3. Verify insertion
python check_adg_provisions.py

# 4. Test API
curl "http://localhost:3007/api/setbacks/adg?building_height=15&development_type=residential_flat_building"

# 5. Check in browser
# Navigate to assessment page and enter apartment development
```

### If Data is Missing:

```bash
# Check if data exists
psql -d nsw_planning -c "SELECT COUNT(*) FROM setback_rules WHERE ref_number = 'ADG 3F-1';"

# If 0, run insertion
python insert_adg_statutory_standards.py

# Verify again
psql -d nsw_planning -c "SELECT ref_number, boundary_type, setback_meters FROM setback_rules WHERE ref_number = 'ADG 3F-1' LIMIT 5;"
```

---

## Legal Status

**Authority:** SEPP (Housing) 2021
**Compliance Level:** **STATUTORY** (not discretionary)
**Applicability:** State-wide (all of NSW)
**Variations:** Cannot be reduced by consent authority
**Compliance Pathway:** Must be met for CDC (Complying Development Certificate)

**User Impact:**
- Red border + "STATUTORY" badge in UI
- Same priority level as SEPP provisions
- Clear warning that these cannot be varied
- Link to official PDF source

---

## Summary

**Data Source:** Manual extraction from official NSW Planning PDF (page 63)
**Insertion Method:** Python script with hard-coded standards
**Verification:** Cross-checked against SEPP (Housing) 2021
**Database Table:** `setback_rules`
**Total Records:** 12 standards (3 height categories × 2 boundaries × 2 room types)
**API Endpoint:** `/api/setbacks/adg`
**Component:** `ADGBuildingSeparationTable.tsx`

**To populate the database:**
```bash
python insert_adg_statutory_standards.py
```

That's it! The script contains all the data extracted from the official source.
