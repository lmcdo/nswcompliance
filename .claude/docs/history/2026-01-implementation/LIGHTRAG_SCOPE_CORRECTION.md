# LightRAG Scope Correction
**Date:** 2025-10-23
**Purpose:** Correct the processing scope based on actual database structure

---

## Original Assumption (WRONG ❌)

```
Scope: Process (LGA, Zone, DevType) combinations
Assumption: regulatory_provisions has zone/devtype populated
Estimated combinations: ~100
Cost estimate: $10.00
```

---

## Actual Reality (CORRECT ✅)

### Database Facts

```sql
-- Checked regulatory_provisions table
Total DCP provisions: 240
With zone populated: 0 (0.0%)
With dev_type populated: 0 (0.0%)

-- Provisions are filtered by DOCUMENT_ID, not zone/devtype!
```

### How DCP Provisions Are Actually Queried

From `frontend-nextjs/app/api/dcp/provisions/route.ts`:

```typescript
// Development types map to DOCUMENT_ID patterns:
'dwelling_house': {
  patterns: [
    `${lgaSearchPattern}.*_2_`,      // Part 2: General controls
    `${lgaSearchPattern}.*4\\.1`     // Part 4.1: Low density
  ],
  section: 'Part 2 (General) + Part 4.1 (Low Density)'
}

// NOT filtered by zone/devtype in regulatory_provisions table!
// Filtered by document_id pattern matching!
```

---

## Revised Processing Scope

### Base DCP Sections (by LGA × Development Type)

| LGA | Part 2 | Part 4.1 | Part 4.2 | Part 4.3 | Part 5 | Total |
|-----|--------|----------|----------|----------|--------|-------|
| Marrickville | ✓ | ✓ | ✓ | ✓ | ✓ | 5 |
| Ashfield | ✓ | ✓ | ✓ | ✓ | ✓ | 5 |
| Leichhardt | ✓ | ✓ | ✓ | ✓ | ✓ | 5 |
| **Total** | | | | | | **15** |

### Precinct Sections (Address-Specific)

```
Marrickville precincts: 41
Ashfield precincts: TBD
Leichhardt precincts: TBD
Total precincts: ~41 (currently)
```

---

## Corrected Processing Plan

### Approach: Process by Document Section

```python
processing_batches = [
    # Base DCP sections
    ('Marrickville', 'Part_2'),
    ('Marrickville', 'Part_4.1'),
    ('Marrickville', 'Part_4.2'),
    ('Marrickville', 'Part_4.3'),
    ('Marrickville', 'Part_5'),

    ('Ashfield', 'Part_2'),
    ('Ashfield', 'Part_4.1'),
    ('Ashfield', 'Part_4.2'),
    ('Ashfield', 'Part_4.3'),
    ('Ashfield', 'Part_5'),

    ('Leichhardt', 'Part_2'),
    ('Leichhardt', 'Part_4.1'),
    ('Leichhardt', 'Part_4.2'),
    ('Leichhardt', 'Part_4.3'),
    ('Leichhardt', 'Part_5'),

    # Precincts (separate table)
    # ... 41 Marrickville precincts from dcp_precinct_provisions
]

Total batches: 15 + 41 = 56
```

### Database Schema (REVISED)

```sql
-- Store by document section, NOT by zone/devtype
CREATE TABLE dcp_section_requirements (
  id SERIAL PRIMARY KEY,
  lga TEXT NOT NULL,
  dcp_section TEXT NOT NULL,           -- 'Part_2', 'Part_4.1', etc.
  category TEXT NOT NULL,               -- 'setback_front', 'parking', etc.
  requirement_text TEXT NOT NULL,
  value_numeric NUMERIC,
  unit TEXT,

  -- Source tracking
  source_provision_ids INTEGER[] NOT NULL,
  source_documents TEXT[],

  -- Quality metadata
  confidence TEXT CHECK (confidence IN ('high', 'medium', 'low')),
  validated BOOLEAN DEFAULT false
);

-- Runtime query joins section_requirements with dev_type mapping:
-- SELECT * FROM dcp_section_requirements
-- WHERE lga = 'Marrickville'
-- AND dcp_section IN ('Part_2', 'Part_4.1')  -- Based on dev_type
```

### Runtime Query Logic

```typescript
// Map development type to DCP sections
const devTypeToSections = {
  'dwelling_house': ['Part_2', 'Part_4.1'],
  'multi_dwelling': ['Part_2', 'Part_4.2'],
  'shop_top_housing': ['Part_2', 'Part_4.3'],
  'commercial': ['Part_2', 'Part_5']
};

// Query categorized requirements
const sections = devTypeToSections[developmentType];
const requirements = await db.query(`
  SELECT * FROM dcp_section_requirements
  WHERE lga = $1
  AND dcp_section = ANY($2)
  AND validated = true
`, [lga, sections]);

// Merge with precinct requirements if applicable
if (precinctId) {
  const precinctReqs = await db.query(`
    SELECT * FROM dcp_precinct_requirements
    WHERE precinct_id = $1
    AND validated = true
  `, [precinctId]);

  requirements.push(...precinctReqs);
}
```

---

## Revised Cost Estimate

```
Base DCP Sections:
  - 3 LGAs × 5 sections = 15 batches
  - Each batch: ~30-50 provisions
  - Cost per batch: $0.05
  - Total: 15 × $0.05 = $0.75

Precinct Sections:
  - 41 precincts
  - Each precinct: ~5-10 provisions
  - Cost per precinct: $0.01
  - Total: 41 × $0.01 = $0.41

TOTAL ONE-TIME COST: $1.16
Runtime cost: $0 per address
```

---

## Key Changes from Original Plan

### BEFORE (Wrong):
- Scope: 100 (LGA, Zone, DevType) combinations
- Cost: $10.82
- Schema: `dcp_base_requirements(lga, zone, dev_type, ...)`

### AFTER (Correct):
- Scope: 15 (LGA, Section) combinations + 41 precincts
- Cost: $1.16
- Schema: `dcp_section_requirements(lga, dcp_section, ...)`

### Why This Is Better:
1. **Aligns with actual data structure** - no zone/devtype in regulatory_provisions
2. **Matches current API logic** - queries by document_id patterns
3. **Simpler processing** - 56 batches vs 100+ combinations
4. **Lower cost** - $1.16 vs $10.82
5. **Easier to validate** - clear section boundaries

---

## Summary

The original "100 combinations" assumption was based on:
- **Theoretical** database schema with zone/devtype populated
- **NOT** the actual implementation which filters by document_id

The **actual** scope is:
- **15 DCP section batches** (3 LGAs × 5 sections)
- **41 precinct batches** (from dcp_precinct_provisions table)
- **56 total batches**
- **$1.16 total cost** (not $10.82)

This is MUCH simpler and cheaper than originally estimated! ✅
