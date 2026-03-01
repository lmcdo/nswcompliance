# Ashfield Precinct Naming Issues - Complete Analysis

## CRITICAL ISSUES FOUND

### Issue 1: LGA Case Sensitivity (SAME AS BEFORE!)
```
'Inner West':  43 records
'INNER WEST': 704 records
```
**Impact:** Queries with `WHERE lga = 'Inner West'` will miss 704 records!

---

### Issue 2: Precinct ID Mismatch
**Database uses:**
- D1, D2, D4, D5, D6, D7, D8

**New GeoJSON uses:**
- Part 1, Part 2, Part 3, Part 4, Part 7, Part 8, Part 9, Part 10, Part 12, **13** (inconsistent!)

**Problem:** Cannot join provisions to boundaries!

---

### Issue 3: GeoJSON Inconsistent Naming
Most precincts: "Part X"
But Part 13: Just "13" (missing "Part" prefix)

---

### Issue 4: GeoJSON Has Duplicates (OK - Multipolygons)
- Part 1 appears twice (multipolygon for Ashfield Town Centre)
- Part 2 appears twice (multipolygon for Ashfield East)

**This is CORRECT** - compound precincts with multiple areas.

---

## RECOMMENDED FIX STRATEGY

### Step 1: Fix LGA Case Sensitivity
```sql
-- Standardize to 'Inner West' (proper case)
UPDATE dcp_precinct_requirements
SET lga = 'Inner West'
WHERE lga = 'INNER WEST';

-- Verify
SELECT DISTINCT lga, COUNT(*) FROM dcp_precinct_requirements GROUP BY lga;
-- Should show only: 'Inner West' (747 records)
```

### Step 2: Standardize Precinct IDs to "Part X" Format

**Option A: Update Database (RECOMMENDED)**
```sql
-- Convert D1 -> Part 1, D2 -> Part 2, etc.
UPDATE dcp_precinct_requirements
SET precinct_id = 'Part ' || SUBSTRING(precinct_id FROM 2)
WHERE precinct_id SIMILAR TO 'D[0-9]+';

-- After update, database will have:
-- Part 1, Part 2, Part 4, Part 5, Part 6, Part 7, Part 8
```

**Why Option A?**
- PDF uses "Part 1", "Part 2", etc. (not "D1", "D2")
- New GeoJSON uses "Part X" (matches PDF)
- Only 44 records to update (one-time fix)
- Future imports can use PDF naming directly

### Step 3: Fix GeoJSON Part 13 Naming

**Before importing**, fix the inconsistent precinct ID:
```python
# When importing precintboudariesashfield2.geojson:
for feature in geojson['features']:
    precinct_id = feature['properties']['precinct']

    # Fix Part 13 which is just "13"
    if precinct_id == '13':
        feature['properties']['precinct'] = 'Part 13'
```

### Step 4: Import GeoJSON Boundaries

After fixes, import with standardized "Part X" IDs:
```
Part 1  - Ashfield Town Centre (2 polygons)
Part 2  - Ashfield East (2 polygons)
Part 3  - Ashfield West
Part 4  - Croydon Urban Village
Part 7  - Enterprise Zone Hurlstone Park
Part 8  - Summer Hill Urban Village
Part 9  - Summer Hill Flour Mills
Part 10 - Edwards Street B4 Zone
Part 12 - 55-63 Smith Street
Part 13 - 120C Old Canterbury Road
```

### Step 5: Extract Missing Provision Content

Missing from database (need PDF extraction):
- Part 3  - Ashfield West
- Part 9  - Summer Hill Flour Mills
- Part 10 - Edwards Street
- Part 11 - Industrial Zones (zone-based, not boundary)
- Part 12 - 55-63 Smith Street
- Part 13 - 120C Old Canterbury Road

---

## FINAL STATE AFTER FIXES

### Database (dcp_precinct_requirements)
```
precinct_id | precinct_name                          | lga        | requirements
------------|----------------------------------------|------------|-------------
Part 1      | Ashfield Town Centre                   | Inner West | 5
Part 2      | Ashfield East                          | Inner West | 5
Part 3      | Ashfield West                          | Inner West | [NEW]
Part 4      | Croydon Urban Village                  | Inner West | 8
Part 5      | Neighbourhood Centre (B1) Zone         | Inner West | 5
Part 6      | Enterprise Zone (B6) - Parramatta Road | Inner West | 7
Part 7      | Enterprise Zone (B6) - Hurlstone Park  | Inner West | 8
Part 8      | Summer Hill Urban Village              | Inner West | 6
Part 9      | Summer Hill Flour Mills Site           | Inner West | [NEW]
Part 10     | Edwards Street - B4 Zone               | Inner West | [NEW]
Part 12     | 55-63 Smith Street Summer Hill         | Inner West | [NEW]
Part 13     | 120C Old Canterbury Road               | Inner West | [NEW]
```

### Part 11 - Industrial Zones
Store in `dcp_general_requirements` (not precinct-based):
```sql
-- Part 11 applies to ALL IN2 zones in Ashfield, no specific boundary
INSERT INTO dcp_general_requirements (
    requirement_text,
    zone,
    former_council,
    lga
) VALUES (
    'Part 11 requirement...',
    'IN2',
    'Ashfield',
    'Inner West'
);
```

---

## IMPLEMENTATION CHECKLIST

- [ ] Step 1: Fix LGA case sensitivity ('INNER WEST' -> 'Inner West')
- [ ] Step 2: Convert precinct IDs (D1 -> Part 1, D2 -> Part 2, etc.)
- [ ] Step 3: Fix GeoJSON Part 13 naming (13 -> Part 13)
- [ ] Step 4: Import GeoJSON boundaries (10 precincts, 12 polygons total)
- [ ] Step 5: Extract missing provision content (Parts 3, 9, 10, 12, 13)
- [ ] Step 6: Handle Part 11 (Industrial Zones) as general requirement

---

## VERIFICATION QUERIES

After fixes, these should work:
```sql
-- Check LGA standardization
SELECT DISTINCT lga FROM dcp_precinct_requirements;
-- Should show only: 'Inner West'

-- Check precinct ID standardization
SELECT DISTINCT precinct_id FROM dcp_precinct_requirements
WHERE precinct_id ILIKE '%ashfield%' OR precinct_id ILIKE 'Part%'
ORDER BY precinct_id;
-- Should show: Part 1, Part 2, ... Part 13 (no gaps after extraction)

-- Test join between provisions and boundaries
SELECT
    b.precinct_id,
    b.precinct_name,
    COUNT(p.id) as provision_count
FROM precinct_boundaries b
LEFT JOIN dcp_precinct_requirements p ON b.precinct_id = p.precinct_id
WHERE b.former_council = 'Ashfield'
GROUP BY b.precinct_id, b.precinct_name;
-- All precincts should have > 0 provisions (after extraction complete)
```
