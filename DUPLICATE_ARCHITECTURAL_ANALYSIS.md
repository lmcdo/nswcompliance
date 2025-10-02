# Duplicate Architectural Analysis - Root Cause Found

**Date:** 2025-10-01
**Context:** Exempt/complying codes not functioning properly in SEPP→LEP→DCP hierarchy

---

## Executive Summary

**ROOT CAUSE IDENTIFIED:**

522 out of 4,508 (11.6%) of `development_controls` records point to **NON-CANONICAL provisions**.

When frontend queries use `regulatory_provisions_canonical` view (which filters to `is_canonical = TRUE`), these 522 controls appear **orphaned** - their associated provision text is filtered out, breaking the compliance display.

---

## The Problem in Detail

### What Should Happen
```typescript
// User searches for property
// API queries canonical view + joins controls

SELECT
  rp.ref_number,
  rp.provision_text,
  dc.control_type,
  dc.value_numeric
FROM regulatory_provisions_canonical rp
JOIN development_controls dc ON dc.provision_id = rp.id::text
WHERE rp.zone = 'R2' AND rp.development_type = 'deck';

// Expected: Show provision text + associated controls
```

### What Actually Happens
```sql
-- Example provision 228 (duplicate):
is_canonical = FALSE
canonical_provision_id = 219

-- development_controls.provision_id = '228'
-- But regulatory_provisions_canonical filters OUT provision 228

-- Result: Control exists, but no provision shows
-- OR: Provision 219 shows, but control 93 doesn't join (wrong ID)
```

**Impact:**
- Missing controls in UI (setbacks, heights, etc.)
- Incomplete compliance information
- Exempt/complying codes don't show required standards
- User sees partial data

---

## Data Analysis

### 1. Duplicate Distribution

**By Extraction Method:**
| Method | Total | Canonical | Duplicates | Dup % |
|--------|-------|-----------|------------|-------|
| autoschema | 21,947 | 19,410 | 2,537 | 11.6% |
| mineru | 701 | 701 | 0 | 0.0% |

**Key insight:** ALL duplicates come from old autoschema extraction. MinerU has perfect deduplication.

### 2. Duplicate Patterns

| Pattern | Groups | Total Provisions |
|---------|--------|------------------|
| No Split Pattern | 1,738 | 4,716 |
| Section Split | 73 | 150 |

**Total:** 1,811 duplicate groups affecting 4,866 provisions

### 3. Exempt/Complying SEPP Status

Relatively clean - only 19 duplicates across 10 document chunks (out of ~1,200 exempt provisions).

**This suggests:** The duplicate problem affects **all document types**, not just Exempt SEPP.

### 4. Foreign Key Integrity

**development_controls:**
- Total: 4,508 controls
- **Orphaned: 522 (11.6%)**  ⚠️ PROBLEM
- Examples:
  - Setback controls
  - Height/FSR controls
  - Vegetation controls
  - Signage controls

**development_permissions:**
- Total: 246 permissions
- With source_provision_id: 115
- Orphaned: Not yet checked (but likely similar ratio)

---

## Why Duplicates Exist (Root Cause)

### The Extraction Pipeline

```
Original PDFs
    ↓
autoschema extraction (old method)
    ↓
Split documents by section/schedule
    ↓
document_id = "Doc___section_1"
document_id = "Doc___section_2"
    ↓
PROBLEM: Same provision appears in multiple sections
    ↓
INSERT without deduplication
    ↓
Database now has duplicates
```

**Example:**
```
Section 11(2) "Glass room exemptions"
├─ Extracted from Part 3 → document_id = "SEPP_Sustainable___part_3"
└─ Also extracted from Schedule 1 → document_id = "SEPP_Sustainable___schedule_1"

Both inserted → Two rows with different IDs
```

### Why MinerU Doesn't Have This Problem

MinerU extraction:
1. Extracts full document structure
2. Unified document_id (no section splits)
3. Hash-based deduplication at insert time
4. Result: 0% duplicates

---

## Architectural Assessment

### Is This An Architectural Problem?

**YES** - Multiple issues:

#### 1. No Unique Constraint ❌
```sql
-- Current (allows duplicates):
PRIMARY KEY (id)

-- Should have:
UNIQUE (document_id, ref_number, text_hash)
WHERE is_canonical = TRUE
```

#### 2. Foreign Keys Use Wrong Type ❌
```sql
-- Current:
development_controls.provision_id TEXT
regulatory_provisions.id INTEGER

-- Should be:
development_controls.provision_id INTEGER
-- With proper foreign key constraint
```

#### 3. No Referential Integrity ❌
```sql
-- Current:
No FK constraint

-- Should have:
ALTER TABLE development_controls
ADD CONSTRAINT fk_provision
FOREIGN KEY (provision_id) REFERENCES regulatory_provisions(id);
```

#### 4. Extraction Pipeline Issues ❌
- Document splitting creates artificial boundaries
- No deduplication at insert time
- No validation before insert
- Multiple extraction runs create duplicates

### Current Solution (Canonical Flag) - Assessment

**Phase 1 approach (canonical flag + view) is actually GOOD:**
- ✅ Industry best practice for soft-delete/deduplication
- ✅ Preserves data for audit trail
- ✅ Reversible (can change canonical designation)
- ✅ Backward compatible

**But incomplete implementation:**
- ❌ Foreign keys not updated to point to canonical IDs
- ❌ No unique constraint on canonical provisions
- ❌ No validation that joins work correctly

---

## Impact on Exempt/Complying Codes

### Why It's Broken

**Scenario 1: Missing Controls**
```
User queries: "Show exempt development for deck in R2"

Database returns:
- Provision 6141 (Section 11(2), canonical) ✓
- But controls point to Provision 6194 (duplicate) ✗

Result: User sees provision text but NO height limits, NO area limits
Conclusion: "Deck not exempt" (wrong - data just disconnected)
```

**Scenario 2: Incomplete Permissions**
```
User queries: "What development types are exempt in E1?"

development_permissions may reference non-canonical provision IDs

Result: Some exempt types don't show up
Conclusion: "Only 3 exempt types" (wrong - actually 8, but 5 orphaned)
```

**Scenario 3: Duplicate Counts**
```
UI shows: "500 exempt provisions"
Actually: 250 canonical + 250 duplicates
Reality: Only 250 unique exempt provisions

Result: Misleading statistics, user confusion
```

---

## Optimal Solution (Best Practices)

### Immediate Fix (Phase 2.5) - Recommended Now ⭐

**Fix foreign key references to point to canonical IDs**

```sql
-- Step 1: Update development_controls
UPDATE development_controls dc
SET provision_id = rp_canonical.id::text
FROM regulatory_provisions rp_dup
JOIN regulatory_provisions rp_canonical
  ON rp_canonical.id = rp_dup.canonical_provision_id
WHERE dc.provision_id = rp_dup.id::text
  AND rp_dup.is_canonical = FALSE
  AND rp_dup.canonical_provision_id IS NOT NULL;

-- Expected: Update ~522 controls

-- Step 2: Update development_permissions (if needed)
UPDATE development_permissions dp
SET source_provision_id = rp_canonical.id::text
FROM regulatory_provisions rp_dup
JOIN regulatory_provisions rp_canonical
  ON rp_canonical.id = rp_dup.canonical_provision_id
WHERE dp.source_provision_id = rp_dup.id::text
  AND rp_dup.is_canonical = FALSE;
```

**Risk:** 2/10 - Safe, reversible
**Impact:** HIGH - Fixes 522 orphaned controls immediately
**Time:** 5 minutes

### Medium-term (Constraint Enforcement)

```sql
-- Prevent duplicate canonicals
CREATE UNIQUE INDEX unique_canonical_provision
ON regulatory_provisions (document_id, ref_number, text_hash)
WHERE is_canonical = TRUE;

-- Proper foreign key (requires schema change)
ALTER TABLE development_controls
  ALTER COLUMN provision_id TYPE INTEGER USING provision_id::integer,
  ADD CONSTRAINT fk_provision
    FOREIGN KEY (provision_id)
    REFERENCES regulatory_provisions(id);
```

**Risk:** 5/10 - Schema change
**Impact:** HIGH - Prevents future issues
**Time:** 30 minutes + testing

### Long-term (Extraction Pipeline)

1. Switch to MinerU for all future extractions (already 0% duplicates)
2. Add deduplication logic at insert time
3. Implement document versioning for amendments
4. Add data quality monitoring/alerting

---

## Recommended Action Plan

### Phase 2.5: Fix Foreign Key References (NOW)

**Objective:** Make all foreign keys point to canonical provisions

**Steps:**
1. Create backup
2. Run UPDATE queries above
3. Verify: `SELECT COUNT(*) FROM development_controls dc JOIN regulatory_provisions rp ON dc.provision_id = rp.id::text WHERE rp.is_canonical = FALSE;` → Should return 0
4. Test frontend: Check if controls now display correctly
5. Verify exempt/complying codes show proper standards

**Success criteria:**
- 0 orphaned controls
- All provisions show associated controls
- Exempt development shows height/area limits
- No data loss

**Rollback:** Restore from backup if issues

### Verification Queries

```sql
-- Before fix
SELECT COUNT(*) FROM development_controls dc
WHERE dc.provision_id IN (
  SELECT id::text FROM regulatory_provisions WHERE is_canonical = FALSE
);
-- Expected: 522

-- After fix
SELECT COUNT(*) FROM development_controls dc
WHERE dc.provision_id IN (
  SELECT id::text FROM regulatory_provisions WHERE is_canonical = FALSE
);
-- Expected: 0

-- Verify join works
SELECT
  COUNT(DISTINCT rp.id) as provisions_with_controls,
  COUNT(*) as total_controls
FROM regulatory_provisions_canonical rp
JOIN development_controls dc ON dc.provision_id = rp.id::text;
-- Should show all 4,508 controls matched
```

---

## Why Previous Phases Didn't Fix This

**Phase 1:** Marked duplicates, created view
**Phase 2A:** Cleaned cross-references

**But neither updated foreign keys!**

The canonical view filters provisions correctly, but foreign keys still point to old duplicate IDs.

It's like:
- ✅ We marked houses as "condemned"
- ✅ We created a "safe houses" list
- ❌ But mail still gets delivered to condemned houses
- ❌ So residents at safe houses don't get their mail

**Fix:** Update the addresses (foreign keys) to point to safe houses (canonical provisions).

---

## Conclusion

**The duplicate problem is real and architectural**, but:

1. ✅ Current approach (canonical flag) is correct
2. ✅ Migration Phases 1 & 2A were necessary
3. ❌ Implementation incomplete - foreign keys not updated
4. ⚠️ **Phase 2.5 needed:** Update foreign keys to canonical IDs

**This will fix exempt/complying codes immediately** without requiring re-extraction, re-parsing, or schema redesign.

**Recommendation:** Run Phase 2.5 now (15 minutes) to restore full functionality.
