# Categorization Script Comparison: Precinct vs General DCP

## THE CRITICAL DIFFERENCE

### Precinct Requirements (BROKEN)
**File:** `categorize_marrickville_provisions_v2.py`

**Lines 219 + 243 - THE BUG:**
```python
# Line 219: Create list of ALL provision IDs
provision_ids = [p['id'] for p in provisions]
# Result: [78851, 78852, 78853, 78854, 78855]
#         page 0,  page 1,  page 2,  page 3,  page 4

# Line 243: ALWAYS use ALL provisions
cur.execute("""
    INSERT INTO dcp_precinct_requirements
    (..., source_provision_ids, ...)
    VALUES (..., %s, ...)
""", (
    ...
    provision_ids,  # ✗ IGNORES LLM, ALWAYS uses ALL pages
    ...
))
```

**What the LLM says:** "This requirement is on page 3 (provision ID 78854)"
**What the script stores:** "Source provisions: [78851, 78852, 78853, 78854, 78855]" (ALL pages 0-4)

**Result:** Runtime page matching has to search through ALL pages including page 0 TOC

---

### General DCP Requirements (SMART)
**File:** `categorize_general_provisions.py`

**Lines 265-289 - INTELLIGENT LOGIC:**
```python
# Line 266: Get LLM's answer
source_prov_id = req.get('source_provision_id')

if source_prov_id:
    # Line 270-271: LLM returned an integer ID → USE IT!
    if isinstance(source_prov_id, int):
        source_ids = [source_prov_id]  # ✓ Just the one the LLM identified
    else:
        # Line 273-285: LLM returned string like "PC7" → TRY TO MATCH IT
        source_prov_id_str = str(source_prov_id).lower()
        matched = False
        for p in provisions:
            header_lower = p['section_header'].lower() if p['section_header'] else ''
            if source_prov_id_str in header_lower:
                source_ids = [p['id']]  # ✓ Found the match
                matched = True
                break
        if not matched:
            # Fallback to all
            source_ids = [p['id'] for p in provisions]
            print(f"    ⚠ Could not match '{source_prov_id}', using all")
else:
    # Line 287-289: LLM didn't provide source_provision_id → FALLBACK
    source_ids = [p['id'] for p in provisions]
    print(f"    ⚠ No source_provision_id, using all provisions")
```

**What the LLM says:** "This requirement is in provision ID 134"
**What the script stores:** "Source provisions: [134]" (JUST THAT ONE)

**Result:** Runtime page matching has ONLY the relevant provision, no page 0 garbage!

---

## WHY THIS MATTERS

### Precinct Requirements (Current State)
```
Category: Character
Requirement: "Maintain single storey streetscapes"
source_provision_ids: [78851, 78852, 78853, 78854, 78855]
                       page 0, page 1, page 2, page 3, page 4
                       ↑
                       TOC - WRONG!

Runtime page matching:
1. Get provisions [78851, 78852, 78853, 78854, 78855]
2. Filter page 0 (OUR FIX) → [78852, 78853, 78854, 78855]
3. Try to match verbatim text to provision_text
4. If match found → use that page ✓
5. If no match → use FIRST provision (page 1, previously page 0) ✗
```

### General DCP Requirements (Better Design)
```
Category: Setback
Requirement: "Minimum side setback: 900mm"
source_provision_ids: [134]
                       ↑
                       ONLY the specific provision!

Runtime page matching:
1. Get provisions [134]
2. No page 0 to filter - list is already clean!
3. Try to match verbatim text to provision_text
4. If match found → use that page ✓
5. If no match → use ONLY provision (which is correct) ✓
```

---

## THE ROOT CAUSE

### Precinct Script Author Was Lazy
```python
# What they SHOULD have done:
source_ids = [req['source_provision_id']]  # Just the LLM's answer

# What they ACTUALLY did:
provision_ids = [p['id'] for p in provisions]  # ALL provisions!
source_ids = provision_ids  # Ignore LLM entirely
```

**This is a copy-paste bug or lazy coding** - they didn't bother implementing the logic to use the LLM's specific answer.

### General Script Author Was Smart
```python
# They actually implemented the logic to USE the LLM's answer:
if source_prov_id:
    if isinstance(source_prov_id, int):
        source_ids = [source_prov_id]  # ✓ Use it!
```

---

## IMPACT ANALYSIS

### How many requirements are affected?

**Precinct Requirements (ALL BROKEN):**
```sql
SELECT COUNT(*)
FROM dcp_precinct_requirements;
-- Result: 1,708 total requirements
-- ALL have source_provision_ids containing ALL pages including page 0
```

**General DCP Requirements (MOSTLY GOOD):**
```sql
SELECT COUNT(*)
FROM dcp_general_requirements;
-- Result: Unknown, but likely MUCH BETTER
-- Only uses ALL provisions as fallback when LLM didn't provide source_provision_id
```

---

## THE FIX WE APPLIED (Runtime Filter)

**What we did:**
```typescript
// precinct-requirements/route.ts Line 176
const allProvisions = (row.all_source_provisions || []).filter((p: any) =>
  p.page_number !== '0'
);
```

**Why it works:**
- Filters out page 0 TOC before text matching
- Fallback now uses page 1 instead of page 0
- Quick fix, no re-categorization needed

**Why it's not perfect:**
- `source_provision_ids` still contains garbage data (ALL provisions)
- Text matching searches through 4 pages instead of just 1
- Slower and less reliable than using the LLM's specific answer

---

## THE PROPER FIX (Re-run Categorization)

**What should be done:**

1. **Fix the script:**
   ```python
   # categorize_marrickville_provisions_v2.py Line 243
   # Change from:
   provision_ids,  # ALL provisions

   # To:
   [req['source_provision_id']],  # Just the LLM's answer
   ```

2. **Re-run categorization for all precincts:**
   ```bash
   python categorize_marrickville_provisions_v2.py
   python categorize_ashfield_provisions.py
   python categorize_leichhardt_provisions_v2.py
   ```

3. **Result:**
   - `source_provision_ids` would contain ONLY the relevant provision
   - No page 0 in the data
   - Faster, more accurate page matching
   - No runtime filtering needed

**Cost:** Time + OpenAI API credits to re-categorize ~1,700 requirements

---

## RECOMMENDATION

**For now:** Runtime filter is good enough (already applied)

**For v2:** Fix the categorization scripts and re-run when you have time/budget

**For new councils:** Use the General DCP script logic, not the Precinct script logic
