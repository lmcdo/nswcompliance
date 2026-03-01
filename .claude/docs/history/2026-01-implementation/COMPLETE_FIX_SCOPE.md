# Complete Fix Scope: All 1,708 Precinct Requirements

## Current State (Broken)

| Issue | Count | % |
|-------|-------|---|
| **BROKEN** - No source data at all | 869 | 51% |
| **BAD DATA** - Wrong source_provision_ids array | 735 | 43% |
| **GOOD** - Has correct primary_source_provision_id | 104 | 6% |
| **TOTAL** | 1,708 | 100% |

### Breakdown by Precinct Type

**BROKEN (need full re-extraction):**
- Ashfield: 798 requirements (NO source data in regulatory_provisions!)
- Marrickville: 54 requirements
- Other: 17 requirements

**BAD DATA (have source but it's wrong array):**
- Marrickville: 383 requirements (have array with ALL pages including page 0)
- Leichhardt: 36 requirements
- Rozelle: 50 requirements
- Other: 266 requirements

---

## Root Causes

### 1. Ashfield Has No Source Data (798 broken)
```sql
SELECT COUNT(*) FROM regulatory_provisions WHERE document_id LIKE '%ashfield%';
-- Result: 0
```

Ashfield provisions were extracted to `dcp_general_provisions` table, NOT `regulatory_provisions`.
The precinct categorization script looks in `regulatory_provisions`, finds nothing, creates empty requirements.

### 2. Bad Categorization Script Logic (735 bad data)
Script dumps ALL provision IDs into `source_provision_ids` array instead of using LLM's specific answer.

```python
# Line 219-243 in categorize_marrickville_provisions_v2.py
provision_ids = [p['id'] for p in provisions]  # ALL pages (0, 1, 2, 3, 4)
source_provision_ids = provision_ids  # Ignores LLM!
```

---

## Optimal Fix Plan

### Phase 1: Fix Ashfield (798 requirements) - **IMMEDIATE**

**Problem:** Ashfield provisions are in `dcp_general_provisions`, not `regulatory_provisions`.

**Solution:** Create new script that reads from correct table.

**File:** `categorize_ashfield_precinct_requirements_v3.py`

```python
# Query dcp_general_provisions instead of regulatory_provisions
cur.execute("""
    SELECT id, section_header, provision_text
    FROM dcp_general_provisions
    WHERE part_number LIKE '%Ashfield%'
        AND part_number LIKE '%' || %s || '%'
    ORDER BY display_order
""", (precinct_id,))
```

**Time:** 2 hours to write + test
**Cost:** $5-10 OpenAI API (798 requirements * $0.01/req)
**Impact:** 798 requirements (47% of total) go from BROKEN to WORKING

---

### Phase 2: Fix Script + Re-run Marrickville/Leichhardt (469 requirements)

**Step 1: Fix the script (5 min)**

**File:** `categorize_marrickville_provisions_v2.py`

```python
# Line 243 - CHANGE FROM:
source_provision_ids = provision_ids  # ALL provisions

# TO:
source_provision_ids = [req['source_provision_id']]  # Just what LLM said
```

**Step 2: Re-run for broken/bad Marrickville (437 requirements)**

```bash
# Delete broken + bad data
DELETE FROM dcp_precinct_requirements
WHERE (primary_source_provision_id IS NULL AND source_provision_ids IS NULL)
   OR (array_length(source_provision_ids, 1) > 1);

# Re-run extraction
python categorize_marrickville_provisions_v2.py --reprocess-all
```

**Time:** 1 hour
**Cost:** $5 OpenAI API
**Impact:** 437 Marrickville requirements fixed

**Step 3: Re-run Rozelle + Leichhardt (86 requirements)**

Similar process for these precincts.

---

### Phase 3: Fix Remaining "Other" (283 requirements)

Check what "Other" includes and fix case-by-case.

---

## Total Effort Estimate

| Phase | Requirements | Time | Cost | Status |
|-------|-------------|------|------|--------|
| Phase 1: Ashfield | 798 | 2 hours | $10 | **CRITICAL** |
| Phase 2: Marr/Leich | 469 | 2 hours | $5 | High Priority |
| Phase 3: Other | 283 | 1 hour | $3 | Medium Priority |
| **TOTAL** | **1,550** | **5 hours** | **$18** | |

**Remaining good:** 158 requirements (already working)

---

## Implementation Order

### Priority 1: Ashfield (NOW)
- 798/1,708 = 47% of total
- Completely broken (no source data)
- User likely sees this

### Priority 2: Marrickville/Leichhardt (This Week)
- 469/1,708 = 27% of total
- Works but shows wrong pages
- User sees page 0 TOC (annoying)

### Priority 3: Other (When Time Permits)
- 283/1,708 = 17% of total
- Mixed issues

---

## Quick Win Alternative: Hybrid API (30 min)

Instead of re-extracting, implement hybrid API that uses what we have:

```typescript
// Use primary when available (480 requirements)
if (primary_source_provision_id && page != '0') {
  return primary
}
// Fall back to array with filter (359 requirements)
else if (source_provision_ids) {
  return filter(array, page != '0')
}
// No source data (869 requirements)
else {
  return null  // No PDF link
}
```

**Result:** 839/1,708 (49%) working immediately with no re-extraction.

---

## Recommendation

**Week 1 (This week):**
1. Implement hybrid API (30 min) - gets 839 working NOW
2. Fix Ashfield script + extract (2 hours) - gets 798 more working
3. **Total: 1,637/1,708 (96%) working**

**Week 2:**
4. Fix Marrickville script + re-extract (2 hours) - cleans up bad data
5. **Total: 1,708/1,708 (100%) perfect**

**Cost:** $18 OpenAI API
**Time:** 5 hours total
**Result:** All 1,708 requirements work perfectly
