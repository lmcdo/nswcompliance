# Fixing the "Semantic Types" Problem

## Problem Summary

**Current Database Schema:**
```
regulatory_provisions:
  provision_type = 'formal_Schedule'  ← Semantic meaning (WHAT kind)
  document_id = 'State Environmental Planning Policy (Housing) 2021'  ← Document reference
```

**What's Wrong:**
- Cannot query `WHERE provision_type = 'SEPP'` (returns 0 results)
- Must use fragile pattern matching: `WHERE document_id LIKE '%SEPP%'`
- Semantic classification (formal/informal) is stored in same column as document type

**Evidence:**
```
Query: SELECT * WHERE provision_type = 'SEPP'
Result: 0 provisions [FAIL]

Query: SELECT * WHERE provision_type = 'LEP'
Result: 0 provisions [FAIL]

Query: SELECT * WHERE provision_type = 'DCP'
Result: 6 provisions [FAIL] (Expected 15,136)

Workaround: SELECT * WHERE document_id LIKE '%SEPP%'
Result: 972 provisions [OK] (But fragile)
```

---

## Solution Options

### **Option 1: Add `document_category` Column (FAST FIX)**

**Migration:** `migrations/fix_document_type_classification.sql`

```sql
ALTER TABLE regulatory_provisions
ADD COLUMN document_category TEXT;

UPDATE regulatory_provisions
SET document_category = CASE
    WHEN document_id LIKE '%SEPP%' THEN 'SEPP'
    WHEN document_id LIKE '%LEP%' THEN 'LEP'
    WHEN document_id LIKE '%DCP%' THEN 'DCP'
    ELSE 'OTHER'
END;

CREATE INDEX idx_regulatory_provisions_document_category
ON regulatory_provisions(document_category);
```

**Pros:**
- ✅ Fast to implement (1 minute)
- ✅ No code changes needed (just add WHERE clause)
- ✅ Indexed for performance

**Cons:**
- ⚠️ Still uses pattern matching (fragile)
- ⚠️ Duplicates data from `documents` table

**Use Case:** Ship today, fix properly later

---

### **Option 2: JOIN with `documents` Table (PROPER FIX)**

The `documents` table **already has** a `document_type` column with correct SEPP/LEP/DCP values!

```sql
SELECT rp.*
FROM regulatory_provisions rp
JOIN documents d ON rp.document_id = d.id
WHERE d.document_type = 'SEPP';
```

**Pros:**
- ✅ Single source of truth
- ✅ No schema migration needed
- ✅ Correct classification (from documents table)

**Cons:**
- ⚠️ Requires JOIN on every query (slower)
- ⚠️ All queries need to be updated

**Use Case:** Proper architecture, worth the refactor

---

### **Option 3: Create VIEW (HYBRID - RECOMMENDED)**

Best of both worlds:

```sql
CREATE OR REPLACE VIEW provisions_with_category AS
SELECT
    rp.*,
    d.document_type as document_category
FROM regulatory_provisions rp
LEFT JOIN documents d ON rp.document_id = d.id;

-- Then query the view:
SELECT * FROM provisions_with_category WHERE document_category = 'SEPP';
```

**Pros:**
- ✅ No schema migration
- ✅ Single source of truth (documents table)
- ✅ Can optimize query planner
- ✅ Easy to switch to (just change table name in queries)

**Cons:**
- ⚠️ Slightly slower than direct column (but negligible)

**Use Case:** **RECOMMENDED** - Clean, maintainable, no downtime

---

## Recommendation

**Ship Option 3 (VIEW) immediately:**

1. Create view (1 line of SQL)
2. Update API queries to use `provisions_with_category` view
3. Can switch to Option 1 (column) later for performance if needed

**Implementation:**

```bash
# Run migration
psql $DB_URL -f migrations/fix_document_type_classification.sql

# Update API code
# BEFORE:
WHERE document_id LIKE '%SEPP%'

# AFTER:
WHERE document_category = 'SEPP'
```

---

## Impact on Dev Type Filtering

**Before Fix:**
```typescript
// Fragile
const seppProvisions = await query(`
  SELECT * FROM regulatory_provisions
  WHERE document_id LIKE '%SEPP%'
    AND section_header LIKE '%secondary dwelling%'
`);
```

**After Fix:**
```typescript
// Clean
const seppProvisions = await query(`
  SELECT * FROM provisions_with_category
  WHERE document_category = 'SEPP'
    AND section_header LIKE '%secondary dwelling%'
`);
```

**Benefit:** Can now properly filter SEPP/LEP/DCP for development type workflows!