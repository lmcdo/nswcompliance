# DCP Precinct Filtering - Root Cause Analysis

**Date**: 2025-10-12
**Issue**: 180 Addison Road Marrickville showing wrong precinct-specific provisions

---

## 🔍 Root Cause Identified

### The API IS Using zone_setback_rules!

Looking at **route.ts lines 170-207**, the API DOES query `zone_setback_rules`:

```typescript
// Query 2: Get curated setback rules from zone_setback_rules
const setbackQuery = `
  SELECT ...
  FROM zone_setback_rules zsr
  INNER JOIN regulatory_provisions_canonical rp ON zsr.source_provision_id = rp.id
  WHERE zsr.zone IN (${setbackZonePlaceholders})
    AND zsr.confidence::numeric > 0.90
    AND zsr.source_provision_id IS NOT NULL
    AND rp.provision_text IS NOT NULL
    AND (
      zsr.source_document ~* $${zoneAliases.length + 1}::text  // <- lgaSearchPattern
    )
  ...
`;

const setbackResult = await pool.query(setbackQuery, [...zoneAliases, lgaSearchPattern]);
```

**The problem**: `lgaSearchPattern` for Marrickville is just `"Marrickville"`

**What's in zone_setback_rules?**
```
ID 9: R2 Inner West, Front: 6.0m (Ashfield DCP 2016)
ID 8: R2 Inner West, Side: 0.9m (Ashfield DCP 2016)
ID 12: R2 Inner West, Front: 3.0m (Leichhardt DCP 2013)
ID 11: R2 Inner West, Side: 1.5m (Leichhardt DCP 2013)
```

**Notice**: The `source_document` column contains `"Ashfield DCP 2016"` and `"Leichhardt DCP 2013"`, NOT `"Marrickville DCP 2011"`!

**Result**: Query returns 0 setbacks for Marrickville because:
```sql
WHERE zsr.source_document ~* 'Marrickville'
-- Matches: 0 (no Marrickville entries in zone_setback_rules!)
```

---

## 🚨 Why Marrickville Setbacks Are Missing

### Check 1: What's in zone_setback_rules for Marrickville?

```sql
SELECT * FROM zone_setback_rules
WHERE zone = 'R2'
  AND source_document ILIKE '%marrickville%';
-- Result: 0 rows
```

**Finding**: `zone_setback_rules` has Ashfield and Leichhardt, but NO Marrickville!

---

### Check 2: Why are only Ashfield/Leichhardt in the table?

**Hypothesis**: The extraction/import process only populated 2 of 3 former councils.

**Possible reasons**:
1. Marrickville DCP extraction failed
2. Marrickville setbacks weren't extracted to zone_setback_rules
3. Marrickville setbacks are in a different table
4. Extraction was incomplete

---

## 📊 What Query Actually Runs

### For 180 Addison Road Marrickville 2204:

1. `zone = 'R2'` ✅
2. `address = '180 Addison Road Marrickville 2204'` ✅
3. `formerCouncil = 'Marrickville'` ✅ (from V2 mapper)
4. `lgaSearchPattern = 'Marrickville'` ✅

**Query 1 (development_controls)**:
```sql
WHERE rp.zone IN ('R2')
  AND rp.document_id ~* 'Marrickville'  // lgaSearchPattern
-- Matches: regulatory_provisions_canonical provisions with Marrickville document_id
```

**Query 2 (zone_setback_rules)**:
```sql
WHERE zsr.zone IN ('R2')
  AND zsr.source_document ~* 'Marrickville'  // lgaSearchPattern
-- Matches: 0 (no Marrickville in zone_setback_rules!)
```

**Query 2b (fallback - descriptive provisions)**:
```sql
WHERE rp.provision_text ILIKE '%front%setback%'
  ...
  AND d.pdf_name ~* 'Marrickville'  // lgaSearchPattern
-- Matches: provisions from documents table with Marrickville pdf_name
```

---

## 🔍 What Route.ts Is Actually Doing

### Line 111-149: Query development_controls table
```typescript
const controlsQuery = `
  SELECT ...
  FROM development_controls dc
  JOIN regulatory_provisions_canonical rp ON dc.provision_id = rp.id
  WHERE rp.zone IN (${zonePlaceholders})
    AND rp.document_id ~* $${zoneAliases.length + 2}::text  // lgaSearchPattern
`;
```

**This should return Marrickville provisions IF**:
- `development_controls` has provision_ids for Marrickville R2 provisions
- Those provision_ids link to `regulatory_provisions_canonical` with correct document_id

---

### Line 170-207: Query zone_setback_rules table
```typescript
const setbackQuery = `
  SELECT ...
  FROM zone_setback_rules zsr
  INNER JOIN regulatory_provisions_canonical rp ON zsr.source_provision_id = rp.id
  WHERE zsr.zone IN (${setbackZonePlaceholders})
    AND zsr.source_document ~* $${zoneAliases.length + 1}::text  // lgaSearchPattern
`;
```

**This returns 0 for Marrickville because**:
- `zone_setback_rules` has no Marrickville entries
- Only has Ashfield and Leichhardt

---

### Line 209-252: Fallback to descriptive provisions
```typescript
if (setbackResult.rows.length === 0) {
  console.log(`No specific setback rules found, searching for descriptive provisions...`);

  const descriptiveSetbackQuery = `
    SELECT ...
    FROM regulatory_provisions_canonical rp
    JOIN documents d ON rp.document_id = d.id
    WHERE (
      rp.provision_text ILIKE '%front%setback%'
      OR rp.provision_text ILIKE '%side%setback%'
      OR rp.provision_text ILIKE '%rear%setback%'
    )
    AND rp.provision_text ~ '[0-9]+\\.?[0-9]*\\s*(m|metre)'
    AND (d.pdf_name ~* $1::text)  // lgaSearchPattern
  `;
}
```

**This should return Marrickville provisions from documents table**

---

## 🎯 The Real Question

### Why is the UI showing wrong provisions?

**User said**: Showing "Timber Yards Sub-precinct", "Precinct 13 (Henson Park)"

**These are coming from the fallback query** (lines 209-252) which searches:
```sql
FROM regulatory_provisions_canonical rp
JOIN documents d ON rp.document_id = d.id
WHERE ...
  AND (d.pdf_name ~* 'Marrickville')
```

**Issue**: The `documents` table `pdf_name` filter is matching:
- Marrickville_DCP_2011___9_13_Henson_Park (Precinct 13)
- Marrickville_DCP_2011___9_47_Victoria_Road (Timber Yards)
- Marrickville_DCP_2011___4.1_Low_Density_Residential ← THIS IS WHAT WE WANT!

**But the query returns precinct-specific ones first because**:
- No ORDER BY to prioritize Section 4.1 over Section 9
- Precinct-specific provisions happen to match the search criteria

---

## ✅ Solution

### Option 1: Fix zone_setback_rules (Populate Marrickville data)
**Time**: 2-4 hours
**Action**: Extract Marrickville R2 setbacks and insert into zone_setback_rules

### Option 2: Filter out Section 9 (Precinct documents)
**Time**: 5 minutes
**Action**: Add to fallback query:
```sql
AND rp.document_id NOT ILIKE '%9_%'  -- Exclude Section 9 (precincts)
AND rp.document_id ILIKE '%4.1%'     -- Prioritize Section 4.1 (general R2)
```

### Option 3: Fix documents.pdf_name filter
**Time**: 10 minutes
**Action**: Add precinct filter to documents join:
```sql
AND d.pdf_name NOT ILIKE '%precinct%'
AND d.pdf_name NOT ILIKE '%9_%'
```

---

## 📝 Summary

**User's Question**: "why isnt it using this [zone_setback_rules]?"

**Answer**: The API IS using `zone_setback_rules`, but:
1. The table only has Ashfield and Leichhardt entries
2. No Marrickville R2 setbacks in the table
3. Falls back to descriptive provisions from `regulatory_provisions_canonical`
4. Fallback query returns precinct-specific provisions (Section 9) instead of general (Section 4.1)

**The term "hardcoded zones like B1"** means:
- B1 has hardcoded setback values in route.ts lines 313-375
- R2 tries to use zone_setback_rules but fails because no Marrickville data
- Falls back to searching regulatory_provisions_canonical which returns wrong provisions

---

## 🎯 Recommended Fix

**Quick (5 min)**: Filter out Section 9 documents in fallback query
```typescript
AND rp.document_id NOT ILIKE '%_9_%'  // Exclude Section 9 (precincts)
OR rp.document_id ILIKE '%4.1%'       // Prioritize Section 4.1 (Low Density Residential)
```

**Proper (2-4 hours)**: Extract Marrickville R2 setbacks to zone_setback_rules table

---

**Status**: Root cause identified - Missing Marrickville data in zone_setback_rules + no precinct filtering in fallback query
