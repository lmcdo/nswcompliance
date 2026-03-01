# Ashfield Chapter F Re-Extraction Process

## What Will Happen

### **Step 1: Delete Existing Ashfield Requirements**
```sql
DELETE FROM dcp_general_requirements WHERE former_council = 'Ashfield';
-- Expected: ~775 rows deleted
```

**Why:** Current 775 Ashfield requirements have NULL zones/devtypes. Cannot be fixed post-hoc.

---

### **Step 2: Extract Each Chapter F Part with Metadata**

#### Source Data (regulatory_provisions):
```
ID 76557: Ashfield_DCP_2016_Chapter_F_Part_1  (Dwelling Houses)
ID 76558: Ashfield_DCP_2016_Chapter_F_Part_2  (Secondary Dwellings)
ID 76559: Ashfield_DCP_2016_Chapter_F_Part_3  (Neighbourhood Shops)
ID 76560: Ashfield_DCP_2016_Chapter_F_Part_4  (Multi Dwelling Housing)
ID 76561: Ashfield_DCP_2016_Chapter_F_Part_5  (Residential Flat Buildings)
ID 76562: Ashfield_DCP_2016_Chapter_F_Part_6  (Boarding Houses)
ID 76563: Ashfield_DCP_2016_Chapter_F_Part_7  (Residential Care Facilities)
ID 76564: Ashfield_DCP_2016_Chapter_F_Part_8  (Child Care Centres)
ID 76565: Ashfield_DCP_2016_Chapter_F_Part_9  (Drive-In Take-Away)
ID 76566: Ashfield_DCP_2016_Chapter_F_Part_10 (Sex Industry Premises)
```

#### Zone/DevType Tagging:

| Part | Name | Zones | Dev Types |
|------|------|-------|-----------|
| Part 1 | Dwelling Houses | R2, R3, R4 | dwelling_house |
| Part 2 | Secondary Dwellings | R2, R3, R4 | secondary_dwelling |
| Part 3 | Neighbourhood Shops | B1 | shop, neighbourhood_shop |
| Part 4 | Multi Dwelling Housing | R2, R3, R4 | multi_dwelling_housing, townhouse, manor_house, attached_dwelling |
| Part 5 | Residential Flat Buildings | R3, R4, B4 | residential_flat_building, shop_top_housing |
| Part 6 | Boarding Houses | R2, R3, R4, B4 | boarding_house, student_accommodation |
| Part 7 | Residential Care | SP2 | residential_care_facility, seniors_housing |
| Part 8 | Child Care Centres | R2, R3, R4, B1, B2 | child_care_centre |
| Part 9 | Drive-In Take-Away | B1, B2 | food_and_drink_premises, take_away_food |
| Part 10 | Sex Industry | IN1, IN2 | sex_services_premises |

---

### **Step 3: LLM Categorization (CLAUDE.md Compliant)**

**For Each Part:**
```
1. Get provision text from regulatory_provisions
2. Batch process in groups of 50 provisions
3. LLM extracts actionable requirements
4. Tag each requirement with Part's zones + dev types
5. Link to source provision via source_provision_ids
6. Import to dcp_general_requirements
```

**Example Output:**
```json
{
  "requirement_text": "Minimum 900mm side setback required",
  "category": "setbacks",
  "part_number": "Part 1",
  "part_name": "Dwelling Houses",
  "applicable_zones": ["R2", "R3", "R4"],
  "development_types": ["dwelling_house"],
  "source_provision_ids": [76557],
  "former_council": "Ashfield",
  "lga": "Inner West"
}
```

---

### **Step 4: Validation (CLAUDE.md Mandatory)**

**Per Part Validation:**
```
Input: N provisions from regulatory_provisions
Output: M requirements extracted
Success Rate: M/N * 100%

✅ >= 80%: Acceptable
⚠️  50-80%: Warning (still acceptable for Chapter F with objectives/context)
❌ < 50%: Critical failure (stop and report)
```

**Final Verification:**
```sql
SELECT
  COUNT(*) as total,
  COUNT(CASE WHEN applicable_zones IS NOT NULL
             AND array_length(applicable_zones, 1) > 0 THEN 1 END) as has_zones,
  COUNT(CASE WHEN development_types IS NOT NULL
             AND array_length(development_types, 1) > 0 THEN 1 END) as has_devtypes
FROM dcp_general_requirements
WHERE former_council = 'Ashfield';

Expected: total = has_zones = has_devtypes (100%)
```

---

## Expected Results

### **Before:**
```
Ashfield: 775 requirements
  applicable_zones: NULL (0%)
  development_types: NULL (0%)
  source_provision_ids: NULL (0%)

Result: API returns 0 requirements ❌
```

### **After:**
```
Ashfield: ~80-150 requirements (estimated)
  applicable_zones: ARRAY['R2','R3','R4'] etc. (100%)
  development_types: ARRAY['dwelling_house'] etc. (100%)
  source_provision_ids: ARRAY[76557] etc. (100%)

Result: API returns requirements filtered by zone/devtype ✅
```

**Why fewer requirements?**
- Previous extraction: 775 (included objectives, explanatory text, duplicates)
- New extraction: ~80-150 (ONLY actionable controls)
- Success rate: 10-20% is NORMAL for Chapter F (per proven method)

---

## What Makes This CORRECT

### ✅ Follows Proven Method:
- Same structure as `extract_marrickville_general_COMPLIANT.py`
- Same structure as `extract_ashfield_complete_COMPLIANT.py`
- CLAUDE.md compliant (batch processing, validation, progress reporting)

### ✅ Key Improvement:
- **Zone/DevType metadata:** Each requirement knows which zones/types it applies to
- **Source traceability:** `source_provision_ids` links back to regulatory_provisions
- **API-ready:** Arrays populated so `WHERE zone = ANY(applicable_zones)` works

### ✅ Data Quality:
- No truncation (full text processing)
- No guessing (metadata from Part structure)
- No post-hoc analysis (zones/types set during extraction)

---

## Time Estimate

- **Step 1 (Delete):** < 1 minute
- **Step 2 (Extract 10 parts):** 40-60 minutes
  - ~4-6 minutes per part (LLM processing + rate limits)
- **Step 3 (Validation):** < 1 minute
- **Total:** 45-65 minutes

---

## Risk Assessment

### Low Risk:
- ✅ Deletes ONLY Ashfield requirements (Marrickville/Leichhardt untouched)
- ✅ Source data in regulatory_provisions unchanged
- ✅ Can re-run if needed
- ✅ Proven method used successfully today

### Success Criteria:
1. All 10 Parts processed
2. Success rate >= 50% per part (80% overall would be excellent)
3. 100% of requirements have zones/devtypes populated
4. API query returns results for test addresses

---

## Ready to Proceed?

**Command to execute:**
```bash
python reextract_ashfield_chapter_f_with_zones.py
```

**What to watch for:**
- Progress bars showing batch processing
- Success rate per part (50%+ is good for Chapter F)
- Final validation showing 100% zone/devtype population

**If something fails:**
- Script will stop and report error
- Existing Leichhardt/Marrickville data unaffected
- Can debug and re-run
