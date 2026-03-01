# V2 Extraction Plan: Ashfield & Marrickville (+ Other Inner West Neighbourhoods)

## Executive Summary

**Problem**: Currently, only Leichhardt C2.2.3.x neighbourhoods (5 precincts, 33 requirements) have been extracted with V2 method (verbatim + summary). All other Inner West neighbourhoods still use V1 extraction (summary only), which causes **PDF page matching failures**.

**Solution**: Re-extract all remaining Inner West neighbourhoods using the V2 method to enable reliable PDF page linking.

**Scope**: 65 precincts (51 Marrickville + 14 Ashfield) needing V2 upgrade

---

## Current Status

### Extraction Status by LGA

| LGA Area | Precincts | V2 Extracted | Status |
|----------|-----------|--------------|--------|
| **Leichhardt C2.2.3.x** | 5 | 5 (100%) | ✅ **COMPLETE** |
| **Ashfield C2.2.1.x** | 7 | 0 (0%) | ❌ **NEEDS V2** |
| **Ashfield D-series** | 7 | 0 (0%) | ❌ **NEEDS V2** |
| **Marrickville numbered (1_-47_)** | 45 | 0 (0%) | ❌ **NEEDS V2** |
| **Marrickville C2.2.5.x (Rozelle)** | 6 | 0 (0%) | ❌ **NEEDS V2** |
| **Balmain C2.2.2.x** | 6 | 0 (0%) | ⏸️ **NOT REQUESTED** |
| **Other Leichhardt C2.2.4.x** | 4 | 0 (0%) | ⏸️ **NOT REQUESTED** |

**User-requested scope:** 65 precincts (51 Marrickville + 14 Ashfield)

### What "V2" Means

**V1 Extraction (OLD - BROKEN):**
- LLM extracts `requirement_text` (clean summary only)
- No verbatim source text stored
- PDF page matching uses fuzzy text matching on summary
- **Result**: Page matching fails when LLM paraphrases → wrong pages displayed

**V2 Extraction (NEW - RELIABLE):**
- LLM extracts **both**:
  - `verbatim_source_text`: Exact text from provision (for 100% reliable matching)
  - `requirement_text`: Clean summary (for display)
  - `primary_source_provision_id`: Which provision it came from
- PDF page matching uses verbatim text (exact substring match)
- **Result**: Always shows correct page because verbatim text never changes

---

## Detailed Precinct Inventory

### 1. Ashfield (14 precincts) ❌

#### Group A: C2.2.1.x Neighbourhoods (7 precincts)
```
C2.2.1.1  - Young Street                (11 reqs, V1)
C2.2.1.2  - Annandale Street            (12 reqs, V1)
C2.2.1.3  - Johnston Street             (12 reqs, V1)
C2.2.1.4  - Booth Street                (11 reqs, V1)
C2.2.1.5  - Trafalgar Street            (13 reqs, V1)
C2.2.1.6  - Nelson Street               (12 reqs, V1)
C2.2.1.8  - Camperdown                  (13 reqs, V1)
```

**Source**: `regulatory_provisions` table (fallback method like Leichhardt C2.2.3.x)

#### Group B: D-Series Precincts (7 precincts)
```
D1  - Ashfield Town Centre              (9 reqs, V1)
D2  - Ashfield East                     (8 reqs, V1)
D4  - Croydon Urban Village             (10 reqs, V1)
D5  - Neighbourhood Centre (B1) Zone    (11 reqs, V1)
D6  - Enterprise Zone (B6) - Parramatta Road  (7 reqs, V1)
D7  - Enterprise Zone (B6) - Hurlstone Park   (9 reqs, V1)
D8  - Summer Hill Urban Village         (12 reqs, V1)
```

**Source**: `dcp_precinct_provisions` table (raw provisions - DIFFERENT method)

### 2. Marrickville (51 precincts) ❌

#### Group A: Numbered Precincts (45 precincts)
```
1_   - Lewisham North                   (12 reqs, V1)
2_   - Stanmore Park                    (10 reqs, V1)
3_   - Stanmore Marian St               (10 reqs, V1)
5_   - Lewisham                         (15 reqs, V1)
6_   - Stanmore South                   (16 reqs, V1)
7_   - Old Canterbury Road East         (10 reqs, V1)
8_   - Petersham North                  (12 reqs, V1)
9_   - Stanmore Station                 (9 reqs, V1)
10_  - Dulwich Hill North               (18 reqs, V1)
... (45 precincts total, all V1)
```

**Source**: `regulatory_provisions` table (Marrickville DCP 2011 Part 9 precincts)

#### Group B: C2.2.5.x Neighbourhoods (6 precincts - Rozelle area)
```
C2.2.5.1  - The Valley (Rozelle)        (10 reqs, V1)
C2.2.5.2  - Easton Park                 (8 reqs, V1)
C2.2.5.3  - Callan Park                 (11 reqs, V1)
C2.2.5.4  - Iron Cove                   (11 reqs, V1)
C2.2.5.5  - Rozelle Commercial          (12 reqs, V1)
C2.2.5.6  - Robert Street Industrial    (12 reqs, V1)
```

**Source**: `regulatory_provisions` table (Leichhardt DCP 2013 Part C Section 2)

### 3. Balmain (C2.2.2.x) - 6 neighbourhoods ❌
```
C2.2.2.1  - Darling Street
C2.2.2.2  - Balmain East
C2.2.2.3  - Gladstone Park
C2.2.2.4  - The Valley (Balmain)
C2.2.2.5  - Mort Bay
C2.2.2.6  - Birchgrove
```

### 4. Other Leichhardt (C2.2.4.x) - 4 neighbourhoods ❌
```
C2.2.4.1  - Catherine Street
C2.2.4.2  - Nanny Goat Hill
C2.2.4.3  - Leichhardt Park
C2.2.4.4  - Iron Cove Parklands
```

### 5. Other Precincts ❌
```
E2   - Haberfield Heritage Conservation Area
2_   - Petersham North
36_  - Petersham Commercial Precinct 36
38_  - Dulwich Hill Commercial Precinct 38
```

---

## Implementation Strategy

### Phase 1: Priority Neighbourhoods (Ashfield & Marrickville)

**Why These First?**
1. You explicitly requested them
2. Ashfield has 14 neighbourhoods (largest scope)
3. Marrickville has 7 neighbourhoods (second largest)
4. Together: 21 neighbourhoods, 222 requirements
5. Both have source provisions available

### Phase 2: Remaining Neighbourhoods (Optional)

**Scope**: Balmain, Other Leichhardt, Haberfield, Commercial precincts
**When**: After Phase 1 is validated and working

---

## Technical Approach

### Step 1: Create V2 Extraction Scripts

**For Ashfield:**
- Copy `categorize_leichhardt_provisions_v2.py` → `categorize_ashfield_provisions_v2.py`
- Update precinct ID patterns to match Ashfield (C2.2.1.x and D-series)
- Keep same V2 prompt (verbatim + summary extraction)

**For Marrickville:**
- Copy `categorize_leichhardt_provisions_v2.py` → `categorize_marrickville_provisions_v2.py`
- Update precinct ID patterns to match Marrickville (C2.2.5.x and 40_)
- Keep same V2 prompt

### Step 2: Database Preparation

**Before Extraction:**
```sql
-- 1. Backup current data
-- Already have columns: verbatim_source_text, primary_source_provision_id, pdf_page_image_url

-- 2. No schema changes needed (columns already exist from Leichhardt V2)

-- 3. Verify source provisions exist
SELECT COUNT(DISTINCT rp.id)
FROM regulatory_provisions rp
WHERE rp.id IN (
    SELECT UNNEST(source_provision_ids)
    FROM dcp_precinct_requirements
    WHERE precinct_id LIKE 'C2.2.1%' OR precinct_id LIKE 'D%'
);
-- Should return > 0
```

### Step 3: Safe Extraction Process

**For Each LGA:**

1. **Create backup**
   ```python
   timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
   backup_file = f'backups/dcp_precinct_requirements_before_v2_{lga}_{timestamp}.json'
   # Backup all rows for that LGA
   ```

2. **Delete old V1 extractions**
   ```sql
   DELETE FROM dcp_precinct_requirements
   WHERE precinct_id LIKE 'C2.2.1%' OR precinct_id LIKE 'D%';  -- Ashfield

   DELETE FROM dcp_precinct_requirements
   WHERE precinct_id LIKE 'C2.2.5%' OR precinct_id = '40_';  -- Marrickville
   ```

3. **Run V2 extraction**
   ```bash
   python categorize_ashfield_provisions_v2.py
   python categorize_marrickville_provisions_v2.py
   ```

4. **Populate PDF metadata**
   ```sql
   -- Populate pdf_page_image_url from primary_source_provision_id
   UPDATE dcp_precinct_requirements dpr
   SET pdf_page_image_url = rp.pdf_page_image_url
   FROM regulatory_provisions rp
   WHERE dpr.primary_source_provision_id = rp.id
   AND dpr.precinct_id LIKE 'C2.2.1%';  -- Repeat for each LGA

   -- Populate pdf_pages array
   UPDATE dcp_precinct_requirements dpr
   SET pdf_pages = ARRAY[rp.page_number::integer]
   FROM regulatory_provisions rp
   WHERE dpr.primary_source_provision_id = rp.id
   AND dpr.precinct_id LIKE 'C2.2.1%';  -- Repeat for each LGA
   ```

5. **Verify data quality**
   ```sql
   SELECT
       precinct_id,
       COUNT(*) as total,
       COUNT(verbatim_source_text) as has_verbatim,
       COUNT(primary_source_provision_id) as has_prov_id,
       COUNT(pdf_page_image_url) as has_url
   FROM dcp_precinct_requirements
   WHERE precinct_id LIKE 'C2.2.1%'
   GROUP BY precinct_id;

   -- All counts should be equal (100% coverage)
   ```

### Step 4: API Verification

**APIs are already updated** (from Leichhardt V2 work):
- `/api/compliance/precinct-requirements` - Uses verbatim matching (line 181)
- `/api/compliance/dcp-complete` - Uses pdf_pages[1] and pdf_page_image_url

**No code changes needed** - just verify data flows correctly after extraction.

---

## JSON Escape Sequence Handling

### Known Issue
LaTeX/math notation in provisions causes JSON parsing errors:
```
"Building height of $_ { 3 . 6 \mathsf { m } }$"
                              ^ Unescaped backslash breaks JSON
```

### Solution Already Implemented
`categorize_leichhardt_provisions_v2.py` (lines 102-113) includes error handling:
```python
try:
    requirements = json.loads(content)
except json.JSONDecodeError:
    # Fix unescaped backslashes
    fixed_content = re.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', r'\\\\', content)
    requirements = json.loads(fixed_content)
```

**Copy this fix** to Ashfield and Marrickville V2 scripts.

---

## Estimation

### Time per Precinct
- **Leichhardt average**: 5 precincts in ~3 minutes = 36 seconds per precinct
- **With 65 precincts** (51 Marrickville + 14 Ashfield): ~40 minutes total LLM time
- **Plus prep/verification**: ~60-90 minutes total

### Cost Estimate
- **GPT-4o-mini pricing**: $0.150 per 1M input tokens, $0.600 per 1M output tokens
- **Leichhardt cost**: 5 precincts ≈ $0.05
- **Projected cost** (65 precincts): ~$0.65

---

## Validation Checklist

After extraction, verify for **each LGA**:

- [ ] All neighbourhoods extracted (check count matches expected)
- [ ] All requirements have `verbatim_source_text` (100% coverage)
- [ ] All requirements have `primary_source_provision_id` (100% coverage)
- [ ] All requirements have `pdf_page_image_url` (100% coverage)
- [ ] All requirements have `pdf_pages` array populated (100% coverage)
- [ ] Sample 3 random requirements - verify verbatim text matches source provision
- [ ] Test one requirement in browser - verify "View PDF" shows correct page
- [ ] Compare V1 vs V2 page numbers - confirm differences where expected

---

## Risk Assessment

### Low Risk ✅
- **Data safety**: Backup created before deletion
- **Schema**: No changes needed (columns already exist)
- **APIs**: Already updated (no code changes)
- **Pattern proven**: Leichhardt V2 worked successfully

### Medium Risk ⚠️
- **JSON parsing**: LaTeX notation may cause issues (but fix already implemented)
- **LLM consistency**: GPT-4o-mini might extract differently for different LGAs
  - Mitigation: Use same prompt as Leichhardt V2
- **Time**: 21 neighbourhoods = 13 min LLM time (longer than Leichhardt's 3 min)

### Zero Risk 🚫
- **Breaking production**: Only affects neighbourhoods being re-extracted
- **Data loss**: Backups prevent permanent data loss
- **API breakage**: APIs work with both V1 and V2 data (backwards compatible)

---

## Recommended Approach

### Option A: Sequential (Safest)
1. Extract Ashfield (14 precincts: 7 C2.2.1.x + 7 D-series, ~8 min)
2. Verify Ashfield works in UI
3. Extract Marrickville (51 precincts: 45 numbered + 6 C2.2.5.x, ~30 min)
4. Verify Marrickville works in UI

**Pros**: Can catch issues early
**Cons**: Takes longer (2 sessions)

### Option B: Batch (Faster)
1. Extract both Ashfield + Marrickville in one session (~40 min)
2. Verify both in UI

**Pros**: Faster completion
**Cons**: If issues found, affects both

**Recommendation**: **Option A (Sequential)** - Ashfield first (smaller scope for testing), then Marrickville.

---

## Success Criteria

### Phase 1 Complete When:
1. All 65 precincts (51 Marrickville + 14 Ashfield) extracted with V2
2. 100% verbatim coverage for all requirements
3. PDF page links work correctly in UI (spot check 5 random requirements)
4. No V1 extractions remaining for these 65 precincts

### System-Wide Complete When:
1. All 77 Inner West precincts (28 C2.2.x + 45 numbered + 7 D-series) extracted with V2
2. All APIs consistently returning correct PDF pages
3. User can click "View PDF" and always see the correct page
4. V1 extraction scripts deprecated

---

## Next Steps

1. **Get user confirmation**: Ashfield first, then Marrickville? Or batch?
2. **Create V2 scripts**: Copy Leichhardt V2 script, update patterns
3. **Create backups**: One per LGA
4. **Run extractions**: With JSON escape sequence handling
5. **Populate metadata**: pdf_page_image_url and pdf_pages
6. **Verify in UI**: Test random requirements
7. **Document results**: Update this plan with completion status

---

## Open Questions

1. **Priority**: Just Ashfield + Marrickville, or all 35+ neighbourhoods?
2. **Approach**: Sequential (safer) or batch (faster)?
3. **Validation depth**: Spot check 5 requirements, or full verification?
4. **Phase 2 scope**: When to tackle Balmain, Other Leichhardt, Haberfield?
