# Data Quality Tracker

**Purpose:** Track data quality issues systematically across Claude sessions.

**Last Updated:** 2026-01-24
**Session:** DCP Extraction QA Test Framework

---

## Quick Status

| Issue | Status | Priority |
|-------|--------|----------|
| DQ-28: Ashfield chapter_e2_haberfield TOC — catch-all entry only, no section-level TOC extracted | ⏳ Open | P2 |
| DQ-24: Transport & Infrastructure SEPP v2_topic retag | ⏳ Backlog | P3 |
| DQ-25: Transport & Infrastructure sepp_structured_requirements empty | ⏳ Backlog | P2 |
| DQ-26: Marrickville truncated pdf_page_image_url stems | ✅ Fixed 2026-03-04 | P1 (was) |
| DQ-27: Marrickville LaTeX math artefacts in provision_text | ✅ Fixed 2026-03-04 | P1 (was) |
| DQ-1: Precinct CDC=0 | ✅ Not a bug | N/A |
| DQ-2: Topic misclassification | ✅ Fixed | P1 (was) |
| DQ-3: Headers in provisions | ✅ Fixed | P2 (was) |
| DQ-4: v2_marker NULL | ✅ Accepted | P3 |
| DQ-5: Generic layer 78% | ✅ Expected | P3 |
| DQ-6: Duplicates (2%) | ✅ Accepted | P3 |
| DQ-7: Dev-type coverage | ✅ Fixed | P0 (was) |
| DQ-8: DCP-ONLY scope | ✅ Documented | P1 |
| DQ-9: DCP filter bug (IWLEP) | ✅ FIXED | P1 |
| DQ-10: Council-specific UI/UX | ✅ DOCUMENTED | P1 |
| DQ-11: Heritage sub-categorization | ✅ COMPLETE | P2 (was) |
| DQ-13: Leichhardt uncategorized topics | ✅ FIXED | P1 (was) |
| DQ-14: Leichhardt PDF URL coverage | ✅ FIXED | P1 (was) |
| DQ-15: Topic case inconsistency | ✅ FIXED | P2 (was) |
| DQ-16: Heritage topic fragmentation | ✅ FIXED | P1 (was) |
| DQ-17: "Orphaned" non-heritage provisions | ✅ NOT ORPHANED | N/A |
| DQ-18: Marrickville pdf_page mismatch | ✅ FIXED | P1 (was) |
| DQ-19: Part 9 pattern collision | ✅ FIXED | P1 (was) |
| DQ-20: Part 5/6 vs Part 9 precedence | ✅ FIXED | P2 (was) |
| DQ-21: Double-underscore doc_id patterns | ✅ FIXED | P2 (was) |
| DQ-22: TOC provisions marked actionable | ✅ FIXED | P1 (was) |
| DQ-23: Duplicate provisions in TOC view | ✅ FIXED | P1 (was) |

---

## DQ-28: Ashfield chapter_e2_haberfield TOC — catch-all only

**Status:** ⏳ Open
**Found:** 2026-03-29
**Blocking:** No (catch-all entry inserted in migration 018 — TOC JOIN now 100%)

**Problem:** The Haberfield neighbourhood chapter (121 provisions, all on pdf_page=2) has no extracted section-level TOC data. A depth=0 catch-all entry was inserted so the JOIN works, but all 121 provisions will group under a single "E2 Haberfield Neighbourhood" bucket rather than section-level groupings.

**Required action:** Extract section-level TOC from the Haberfield chapter PDF and insert proper entries, then delete the catch-all. Contact: same chapter PDF used during Ashfield extraction (`Inner_West_Ashfield_DCP_2016__chapter_e2_haberfield`).

---

## DQ-22: TOC Provisions Marked as Actionable

**Status:** ✅ FIXED
**Found:** 2026-01-26
**Fixed:** 2026-01-26

**Problem:** 34 Table of Contents (TOC) provisions had `v2_is_actionable = true`, causing them to appear in the DCP tab UI. User reported Part D showing TOC as first provision for 185 Parramatta Road Annandale.

**Example:** ID 80116 (Leichhardt Part D Energy) contained:
```
SECTION 1 – ENERGY MANAGEMENT .
SECTION 2 – RESOURCE RECOVERY AND WASTE MANAGEMENT .......... .....6
```

**Root Cause:** v2 enrichment process didn't detect TOC patterns (dotted leaders like `........`). The `dcp-complete` route had TOC filters but `for-property` API relied solely on `v2_is_actionable`.

**Fix:** SQL update to set `v2_is_actionable = false` for provisions containing `........`:
```sql
UPDATE regulatory_provisions
SET v2_is_actionable = false
WHERE v2_is_actionable = true
AND provision_text LIKE '%........%'
-- Fixed 34 rows
```

**Affected Documents:** Leichhardt DCP (Parts C, D, G), Marrickville DCP (Parts 2, 4, 6, 7, 8, 9), LEP TOC pages

---

## DQ-23: Duplicate Provisions in TOC View

**Status:** ✅ FIXED
**Found:** 2026-01-26
**Fixed:** 2026-01-26

**Problem:** Provisions appearing multiple times in DCP tab TOC-structured view. User reported "C1.5 CORNER SITES" showing 18 provisions on page 17 (6 provisions × 3 duplicates) and 6 provisions on page 18 (3 provisions × 2 duplicates).

**Root Cause:** The `groupByTocStructure` function (frontend-nextjs/app/api/provisions/for-property/route.ts:685-691) flattened provisions from all 4 layers (generic, use_specific, condition, precinct) WITHOUT deduplication. When the same provision appeared in multiple layers due to the layer query logic, it was added to the TOC structure multiple times.

**Code Location:** `frontend-nextjs/app/api/provisions/for-property/route.ts:688-690`

**Fix:** Added Map-based deduplication by provision ID before grouping:
```typescript
// Before (buggy):
const allProvisions: any[] = [];
for (const layer of layers) {
  for (const provision of layer.provisions) {
    allProvisions.push({ ...provision, layer: layer.layer });
  }
}

// After (fixed):
const provisionMap = new Map<number, any>();
for (const layer of layers) {
  for (const provision of layer.provisions) {
    if (!provisionMap.has(provision.id)) {
      provisionMap.set(provision.id, { ...provision, layer: layer.layer });
    }
  }
}
const allProvisions = Array.from(provisionMap.values());
```

**Impact:** Prevents duplicate provision display in DCP tab. Keeps first occurrence (preserves layer priority order: generic → use_specific → condition → precinct).

**Test:** Reload 185 Parramatta Road Annandale assessment - C1.5 Corner Sites should now show 6 unique provisions on page 17, 3 unique provisions on page 18.

---

## DQ-19: Part 9 Pattern Collision with Section Numbers

**Status:** ✅ FIXED
**Found:** 2026-01-24 (via automated test suite)
**Fixed:** 2026-01-24

**Problem:** Layer tagger pattern `'9__' in doc` matched section numbers like `19__` or `29__`, causing Part 2 sections to be misclassified as Part 9 precincts.

**Example:** `Marrickville__DCP__2011__-__2__19__Trees` (Section 2.19 Trees) was classified as `precinct` instead of `generic`.

**Root Cause:** Pattern `'9__'` is a substring of `19__`, `29__`, etc.

**Fix:** Added leading delimiter requirement in `layer_topic_tagger.py:179`:
```python
# Before: if '9_' in doc or '9__' in doc or 'Precinct' in doc:
# After:
if '_9_' in doc or '_9__' in doc or '-9_' in doc or '-9__' in doc or 'Precinct' in doc:
```

**Validation:** Test `test_marrickville_part2_section_topics` now passes.

---

## DQ-20: Part 5/6 vs Part 9 Precedence Issue

**Status:** ✅ FIXED
**Found:** 2026-01-24 (via automated test suite)
**Fixed:** 2026-01-24

**Problem:** Part 5 check for `'Commercial' in doc` matched before Part 9 for precinct names containing "Commercial".

**Example:** `Marrickville__DCP__2011__-__9__40__Town__Centre__Commercial` was classified as `use_specific` (Part 5) instead of `precinct` (Part 9).

**Fix:** Reordered Part 9 check to run before Part 5/6 in `layer_topic_tagger.py:169-177`.

**Validation:** Test `test_part9_precinct` now passes.

---

## DQ-21: Double-Underscore Document_ID Patterns

**Status:** ✅ FIXED
**Found:** 2026-01-24 (via automated test suite)
**Fixed:** 2026-01-24

**Problem:** Part 4.1/4.2 detection only checked `'4_1'` and `'4.1'`, missing `'4__1'` patterns used in some document_ids.

**Fix:** Added `'4__1'` and `'4__2'` patterns to `layer_topic_tagger.py:159-166`.

**Validation:** Test `test_part4_1_use_specific` now passes.

---

## Two-Table Architecture: Raw vs LLM-Curated

**IMPORTANT: Do not assume low LLM coverage means incomplete extraction.**

There are TWO provision data sources:

1. **`regulatory_provisions`** (raw) - PDF paragraphs with regex-classified `v2_topic`
   - Complete coverage (all PDF content)
   - Lower quality (includes headers, intro text, cross-references)
   - 43 unique topics

2. **`dcp_general_requirements`** (LLM-curated) - Extracted actionable requirements with `category`
   - Intentionally selective (only actionable development controls)
   - Higher quality (distilled requirements)
   - 64 unique categories

**LLM Extraction is SELECTIVE by design:**
- The LLM is instructed to "Extract ALL actionable development controls"
- This EXCLUDES: headers, objectives, definitions, explanatory context, cross-references
- A 20-30% extraction rate is NORMAL - most DCP text is not actionable

**Coverage by council (as of 2025-12-01):**
- Ashfield: 791 LLM / 1,579 raw = 50%
- Marrickville: 1,338 LLM / 985 raw = 136% (expansion from multi-requirement paragraphs)
- Leichhardt: 834 LLM / 2,989 raw = 28%

**Leichhardt's 28% is NOT incomplete** - Part C Section 1 alone has 1,782 raw provisions but only 342 extracted requirements (19%). This is correct - most Part C content is objectives and context, not controls.

**Current API usage:**
- Heritage (condition layer): Uses LLM-curated `dcp_general_requirements`
- All other queries: Uses raw `regulatory_provisions` with `v2_topic`

---

## Context Files to Read First

| Priority | File | Purpose |
|----------|------|---------|
| 1 | `.claude/prp/INDEX.md` | Architecture overview, implementation state |
| 2 | `PROVISION_BASED_ARCHITECTURE_STRATEGY.md` | Full 8-part strategy |
| 3 | `DEPLOYMENT.md` | How to sync local/Supabase |
| 4 | **THIS FILE** | Current quality issues and fix progress |
| 5 | `.claude/DQ11_HERITAGE_SUBCATEGORIZATION.md` | Heritage enrichment research & plan |

---

## Current Quality Issues (Priority Order)

### DQ-1: Precinct Filtering Returns 0 Provisions (CDC)
**Status:** ✅ RESOLVED - NOT A BUG
**Priority:** N/A - Expected behavior
**Evidence:** Full cascade with `precinct_id='12_'` + `assessment_type=CDC` returns Layer 4 = 0
**Root Cause:**
- Precinct 12_ (Marrickville Park and Morton Park) has 8 provisions for DA
- All 8 are character statements (qualitative, no numeric values)
- CDC filter requires `v2_has_numeric_value = true`
- Therefore CDC correctly returns 0 for this precinct

**NOT A BUG:** Other precincts (G7=6, Part 1=6, 25_=4, 10_=4) have CDC-compatible provisions with numeric values.

**Verification:**
```sql
-- DA returns 8 for precinct 12_
SELECT COUNT(*) FROM regulatory_provisions
WHERE v2_is_actionable = true AND v2_dcp_layer = 'precinct' AND v2_precinct_id = '12_';
-- Result: 8

-- CDC returns 0 (expected - no numeric values in this precinct)
SELECT COUNT(*) FROM regulatory_provisions
WHERE v2_is_actionable = true AND v2_dcp_layer = 'precinct'
AND v2_precinct_id = '12_' AND v2_provision_type = 'control' AND v2_has_numeric_value = true;
-- Result: 0
```

### DQ-2: Topic Misclassification
**Status:** ✅ RESOLVED
**Priority:** P1 - HIGH (was)
**Evidence:** "Car parking design controls" (ID 78329) was tagged as HEIGHT topic
**Root Cause:** Two issues in `layer_topic_tagger.py`:
1. **Dictionary iteration order**: `TOPIC_KEYWORDS` checked `height` before `parking`
2. **Unused section mapping**: `MARRICKVILLE_PART2_TOPICS` was never used

**Fix Applied (2025-11-24):**
1. Added `_extract_marrickville_part2_topic_from_docid()` method to use document_id section number
2. Changed `_extract_topic_from_text()` to return earliest match by position

**Results:**
- 14,501 provisions had topics updated
- ID 78329 now correctly tagged as `parking`
- "parking" provisions: 347 → 722 (+375)
- "parking" provisions wrongly tagged as height: 124 → 64 (-60)

**Fix Script:** `scripts/fixes/DQ2_fix_topic_classification.py`

### DQ-3: Provision Text Contains Headers Not Controls
**Status:** RESOLVED
**Priority:** P2 - MEDIUM (was)
**Evidence:** "Part 1 Preliminary..." TOC entries marked as actionable
**Root Cause:** LEP table of contents extracted as provisions
**Fix Applied (2025-11-24):** Marked 9 TOC entries as `v2_is_actionable = false`
**Result:** 11,835 -> 11,826 actionable provisions
**Fix Script:** `scripts/fixes/DQ3_fix_toc_entries.py`

### DQ-4: v2_marker Mostly NULL
**Status:** ACCEPTED - Design Limitation
**Priority:** P3 - LOW
**Evidence:** 8.5% have markers (1,008/11,826)
**Root Cause:** Extractor handles C markers only, not O (Objectives). 248 missing are all "O1" boilerplate objectives.
**Decision:** Accept as-is. C markers (topic mapping) work. O markers are qualitative, not needed for CDC.
**Impact:** None - fitness test passed without full marker coverage.

### DQ-5: Generic Layer Dominates (78%)
**Status:** ACCEPTED - Expected
**Priority:** P3 - LOW
**Evidence:** generic=78%, condition=10%, precinct=10%, use_specific=1%
**Assessment:** This is normal for DCP structure. Dev_type filter reduces 354→34 (90%). Working as intended.

### DQ-6: Duplicate Provisions
**Status:** ACCEPTED - Minor
**Priority:** P3 - LOW
**Evidence:** 246 duplicates in 10 groups (2% of total)
**Assessment:** Mostly SEPP boilerplate text repeated across contexts. Minor impact, not blocking.

### DQ-7: Dev-Type Coverage
**Status:** ✅ RESOLVED
**Priority:** P0 - CRITICAL (was)
**Evidence:** All 13 dev_types now have adequate CDC provision coverage.

| Dev Type | Before | After | Status |
|----------|--------|-------|--------|
| dwelling_house | 34 | 307 | OK |
| secondary_dwelling | 8 | 281 | OK |
| dual_occupancy | 10 | 283 | OK |
| multi_dwelling_housing | 10 | 282 | OK |
| residential_flat_building | 10 | 280 | OK |
| retail_premises | 11 | 109 | OK |
| commercial_premises | 0 | 99 | OK |
| office_premises | 0 | 122 | OK |
| industrial_development | 6 | 117 | OK |
| warehouse | 4 | 109 | OK |
| boarding_house | 9 | 277 | OK |
| child_care_centre | 1 | 40 | OK |
| shop_top_housing | 10 | 53 | OK |

**Root Cause:** 286 provisions tagged `['ALL']` instead of specific dev_types.

**Fix Applied (2025-11-24):**
1. `DQ7_devtype_enrichment.py` - Section-based + keyword mapping for residential
2. `DQ7_commercial_industrial_enrichment.py` - Zone-based enrichment for B/IN zones
3. `DQ7_remaining_devtypes.py` - Text matching + parking provisions for all types

**Fix Scripts:** `scripts/fixes/DQ7_*.py`

---

## Fix Workflow

### Per-Issue Process
```
1. Read this file to understand issue
2. Investigate root cause with diagnostic queries
3. Create fix script in scripts/fixes/DQ-{N}_fix_{description}.py
4. Run fix on LOCAL first
5. Verify with test_workflow_quality.py
6. Sync to Supabase: python scripts/sync_v2_to_supabase.py
7. Update status in this file
8. Commit with message: "fix(data): DQ-{N} {description}"
```

### Session Start Checklist
```
[ ] Read .claude/prp/INDEX.md
[ ] Read this file (DATA_QUALITY_TRACKER.md)
[ ] Check which DQ-N is next to fix
[ ] Run test_workflow_quality.py to see current state
[ ] Pick ONE issue to fix this session
```

---

## Test Commands

```bash
# Run quality assessment
python test_workflow_quality.py

# Check sync status
python scripts/compare_local_supabase.py

# Check specific issue
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
import psycopg2
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL') or 'dbname=nsw_planning')
cur = conn.cursor()
# Add diagnostic query here
"
```

---

## Session Log

### 2024-11-24: Initial Assessment
- Completed 4-layer API implementation
- Ran workflow quality tests
- Identified 6 data quality issues
- Created this tracking file

### 2025-11-24: DQ-1 and DQ-2 Resolution + Fitness Assessment
- **DQ-1 RESOLVED**: Not a bug - expected behavior
  - Precinct 12_ has 8 DA provisions but 0 CDC provisions (no numeric values)
  - Other precincts (G7, Part 1, 25_) have CDC-compatible provisions
- **DQ-2 RESOLVED**: Topic misclassification fixed
  - Root cause: Dictionary iteration order + unused section mapping
  - Fix: Added section-based topic extraction + earliest-match algorithm
  - Result: 14,501 provisions updated, ID 78329 now correctly tagged

**FITNESS FOR PURPOSE ASSESSMENT:**
```
Scenario: R2 Zone, Dwelling House, CDC Assessment
  Layer 1 (Generic + dev_type): 34
  Layer 2 (Zone R2):            3
  Layer 3 (Condition):          0 (non-heritage)
  Layer 4 (Precinct 12_):       0 (qualitative only)
  TOTAL:                        37 provisions

VERDICT: PASS - Within target range (30-100)
```

Key findings:
- Full cascade with dev_type filter reduces 354 -> 34 (90% reduction)
- v2_applicable_dev_types is 100% populated for generic layer
- Topic classification working for Marrickville Part 2.10 (all 38 = parking)
- System is FIT FOR PURPOSE for CDC certifier workflow

### 2025-11-24: DQ-7 Dev-Type Enrichment Complete
- **DQ-7 RESOLVED**: All 13 dev_types now have adequate CDC provision coverage
  - Before: Only dwelling_house (34) worked, others had 0-11
  - After: All types have 40-307 provisions
- **Fix approach**:
  1. `DQ7_devtype_enrichment.py` - Section/keyword mapping for residential (8,103 updated)
  2. `DQ7_commercial_industrial_enrichment.py` - Zone-based enrichment for B/IN zones
  3. `DQ7_remaining_devtypes.py` - Text matching + parking provisions for remaining types

**ALL DATA QUALITY ISSUES NOW RESOLVED**

### DQ-8: DCP-ONLY Scope Clarification (2025-11-24)
**Finding**: Previous DQ-7 enrichment incorrectly included SEPP/LEP provisions.
**Scope**: This pipeline is DCP-ONLY. SEPP/LEP values come from Planning Portal API.

**Actual DCP CDC Data:**
| Council | Total DCP | CDC-eligible |
|---------|-----------|--------------|
| Marrickville | 1,051 | 79 (8%) |
| Leichhardt | 2,989 | 43 (1%) |
| Ashfield | 1,526 | 10 (1%) |
| **TOTAL** | **5,566** | **132 (2%)** |

**Reality**: Only 2% of DCP provisions are CDC-eligible (have numeric values).
This is DATA REALITY - DCPs are mostly qualitative (objectives, character statements).
The 132 DCP CDC provisions ARE correctly dev_type tagged.

### Professional Scenario Testing (2025-11-24)
- **CDC scenarios**: All pass (272-274 provisions for residential, 86-88 for commercial/industrial)
- **DA scenarios**: Return more results (7000+) - expected, DA includes objectives not just controls
- **Zone handling**: 'ALL' correctly treated as wildcard (matches any zone)
  - Marrickville uses specific zones (R2, R3/R4 for Part 4)
  - Leichhardt/Ashfield use 'ALL' (zone not a determinant for those DCPs)

### DQ-9: DCP Filter Bug - IWLEP Reference (2025-11-24)
**Status:** ✅ FIXED
**Priority:** P1 - HIGH (was)
**Finding**: Wrong DCP filter was excluding valid DCP provisions.

**Root Cause:**
- WRONG filter: `NOT ILIKE '%LEP%'` - excluded DCP files with "IWLEP" in name
- CORRECT filter: `NOT ILIKE '%Local_Environmental_Plan%'` - only excludes actual LEP docs

**Impact:**
- 2,330 Leichhardt DCP provisions were incorrectly filtered out
- Leichhardt appeared to have "659" provisions but actually has **2,989**

**Corrected Data:**
| Council | generic | precinct | condition | use_specific | TOTAL |
|---------|---------|----------|-----------|--------------|-------|
| Marrickville | 230 (22%) | 359 (34%) | 315 (30%) | 147 (14%) | 1,051 |
| **Leichhardt** | **2,309 (77%)** | 659 (22%) | 0 | 21 (1%) | **2,989** |
| Ashfield | 422 (28%) | 197 (13%) | 907 (59%) | 0 | 1,526 |

**Fix:** Updated filter in INDEX.md and test files to use correct pattern

### DQ-10: Council-Specific UI/UX Strategy (2025-11-24)
**Status:** ✅ DOCUMENTED
**Priority:** P1 - HIGH

**Finding**: Each council's DCP has a DIFFERENT compliance philosophy that UI should reflect.

**Council DCP Structures:**
| Council | Primary Layer | Filter Strategy |
|---------|---------------|-----------------|
| Marrickville | Balanced (precinct 34%, condition 30%, generic 22%) | Zone + Precinct + Topic |
| Leichhardt | **Generic-heavy (77%)** | Topic is PRIMARY filter (reduces 2,211 → 30-85) |
| Ashfield | Condition-heavy (59%) | Site conditions + Topic |

**Test Results (dwelling_house filter with correct DCP filter):**
| Council | dwelling_house count | Layer distribution |
|---------|---------------------|-------------------|
| Marrickville | 228 | generic 53%, use_specific 21%, precinct 15%, condition 11% |
| **Leichhardt** | **2,211** | generic 98%, precinct 2% |
| Ashfield | 394 | generic 99%, condition 1% |

**UI/UX Implications:**
1. **Leichhardt**: Has 2,211 dwelling_house provisions - MUST use topic filter to narrow
   - Topic options: parking (85), building_form (81), landscaping (34), heritage (30)
2. **Marrickville**: Zone filter effective, also use topic
3. **Ashfield**: Site condition (heritage) is key filter, also use topic

**For certifier workflow:**
- Leichhardt CDC: 21 provisions (workable)
- Marrickville CDC: 17 provisions (workable)
- Topic filtering reduces DA queries by 80-95%

### Comprehensive Professional Testing (2025-11-24)
**Test Suite:** `test_comprehensive_professional.py`, `test_tailored_filters.py`
**Results:** 9/13 scenarios PASS

**Scenario Results:**
| Scenario | Count | Expected | Status |
|----------|-------|----------|--------|
| Marrickville R2 Dwelling DA | 193 | 50+ | PASS |
| Marrickville R2 Dwelling CDC | 17 | 5+ | PASS |
| Marrickville R3 Multi-Dwelling DA | 109 | 30+ | PASS |
| Marrickville B2 Retail CDC | 25 | 3+ | PASS |
| Leichhardt R2 Dwelling DA | 39 | 100+ | FAIL (data gap) |
| Leichhardt R2 Dwelling CDC | 2 | 5+ | FAIL (data gap) |
| Ashfield R2 Dwelling DA | 390 | 50+ | PASS |
| Ashfield Dual Occ DA | 397 | 30+ | PASS |
| ALL COUNCILS R2 Dwelling DA | 649 | 200+ | PASS |

**Key Insights:**
1. **Marrickville**: Full 4-layer support, zone filtering effective (34% zone-specific)
2. **Leichhardt**: Generic-heavy (77% generic, 2,989 total) - topic filter CRITICAL
3. **Ashfield**: Condition-heavy (59% condition layer), low CDC is data reality

**Filter Effectiveness by Type:**
- **Dev_type**: Effective for ALL councils (reduces to 2-30% of total)
- **Topic**: Very effective (2-8% per topic, 80-95% reduction)
- **Zone**: Only for Marrickville (34% zone-specific)

### Session Log: Council-Specific UI Implementation (2025-11-24)

**Completed:**
1. ✅ Fixed DCP filter bug (`NOT ILIKE '%LEP%'` was wrong - excluded IWLEP-referenced files)
2. ✅ Correct filter: `NOT ILIKE '%Local_Environmental_Plan%'`
3. ✅ Discovered Leichhardt has 2,989 provisions (not 659) - was filter bug, not data gap
4. ✅ Implemented council-specific UI in `ProvisionsByTopic.tsx`:
   - Topic filter buttons with council-specific suggested topics
   - Warning for Leichhardt when no topic selected
   - Professional priority ordering of topics
5. ✅ Created `frontend-nextjs/lib/council-config.ts`
6. ✅ Created `PROFESSIONAL_USER_GUIDE.md` for trial users
7. ✅ Created git tag `v1.0-pre-council-ux` on main before merge
8. ✅ Pushed tag to remote

### Next Steps:
1. ✅ ~~Fix DQ-9~~ (was filter bug, not data gap - FIXED)
2. ✅ ~~Implement council-aware filtering~~ (DONE)
3. Merge to main and deploy to Vercel
4. Test production with professional users

### DQ-11: Heritage Sub-Categorization (2025-11-25)
**Status:** ✅ COMPLETE
**Priority:** P2 (was)
**Scope:** Ashfield Chapter E1 heritage provisions (907 total)

**Problem:** 907 heritage provisions shown as undifferentiated list. No way to find relevant controls.

**Solution Applied:** LLM categorization using OpenAI gpt-4o-mini

**Final Results (verified in database):**
| Type | Count | Description |
|------|-------|-------------|
| control | 163 | Actionable requirements with C markers or imperative verbs |
| character | 422 | HCA-specific descriptions and significance statements |
| descriptive | 322 | Historical narratives, style definitions, background |

**Element Tagging (controls):**
- fence: 39, materials: 37, roof: 29, verandah: 21, scale: 16
- car_parking: 15, window: 14, facade: 14, demolition: 13, chimney: 12

**HCA Tagging:**
- ashfield_heights: 142, summer_hill: 49, queen_street: 17, victoria_square: 16
- murrell: 11, farleigh: 7, tintern: 6, moonagee: 6, holwood: 6

**Schema columns added:**
- `v2_heritage_type` (TEXT)
- `v2_heritage_element` (TEXT[])
- `v2_heritage_hca` (TEXT)

**Fix Script:** `scripts/fixes/DQ11_heritage_categorization.py`

### DQ-13: Leichhardt Uncategorized Topics (2025-11-29)
**Status:** ✅ FIXED
**Priority:** P1 (was)
**Problem:** 42% of Leichhardt provisions (1,242/2,962) had NULL v2_topic

**Root Cause:** Bug in `enrichment/extractors/layer_topic_tagger.py`
- Section 1 handler only used C marker extraction
- Many provisions lack C markers but have keyword matches
- Missing fallback: `or self._extract_topic_from_text(provision_text)`

**Fixes Applied:**
1. Fixed `layer_topic_tagger.py` - added keyword fallback for Section 1
2. Marked 124 Part A (Introduction) provisions as non-actionable
3. Re-classified 1,164 Part C Section 1 provisions

**Results:**
- Uncategorized: 42% → 10.1% (reduced by 32 percentage points)
- 878 provisions now have topics assigned
- Part A correctly marked non-actionable (procedural, not requirements)

**Fix Script:** `scripts/fixes/DQ13_leichhardt_fixes.py`

### DQ-14: Leichhardt PDF URL Coverage (2025-11-29)
**Status:** ✅ FIXED
**Priority:** P1 (was)
**Problem:** Only 26% of Leichhardt provisions had PDF page image URLs (vs 100% for Marrickville/Ashfield)

**Root Cause:** Multiple issues
1. `pdf_page_image_url` column was NULL, needed population from `pdf_page`
2. Folder mapping regex: "Section 1" matched before "Part G"
3. Part G offset: `pdf_page` has +100 offset, should use `page_number` column
4. Missing PNG files: pages 10, 21, 23, 24, 25, 35 not extracted

**Fixes Applied:**
1. `DQ14_leichhardt_pdf_urls.py` - Initial URL population (2,097 provisions)
2. `extract_missing_pdf_pages.py` - Extracted 115 missing pages using PyMuPDF
3. `DQ14b_fix_part_g_urls.py` - Fixed Part G using `page_number` (487 provisions)
4. `extract_missing_part_g.py` - Extracted 6 additional Part G pages
5. Uploaded all new PNG files to Cloudflare R2

**Results:**
| Metric | Before | After |
|--------|--------|-------|
| PDF URL coverage | 26% (773/2,962) | **100%** (2,838/2,838) |
| Part G coverage | 0% | 100% |
| Missing PNG files | 160 | 0 |

**Key Insight:** Part G has inconsistent offset pattern (pdf_page ≠ page_number).
Always use `page_number` column for Part G PDF URLs.

**Fix Scripts:** `scripts/fixes/DQ14_leichhardt_pdf_urls.py`, `scripts/fixes/DQ14b_fix_part_g_urls.py`

### DQ-15: Topic Case Inconsistency (2025-11-29)
**Status:** ✅ FIXED
**Priority:** P2 (was)
**Problem:** Leichhardt had duplicate topics differing only by case (e.g., `parking` vs `Parking`)

**Root Cause:** Inconsistent capitalization during topic extraction
- 17 topics affected: heritage, height, setbacks, parking, access, landscaping, trees, signage, waste, privacy, stormwater, fencing, flooding, contamination, safety, roofing, solar

**Fix Applied:**
1. Normalized all topics to Title Case
2. Fixed `building_form` → `Building Form`

**Results:**
- 845 provisions updated (725 case normalization + 120 building_form)
- All topics now use consistent Title Case
- Leichhardt topic distribution now accurate

**Fix Script:** `scripts/fixes/DQ15_normalize_topic_case.py`

### 50-Address Comprehensive Test (2025-11-29)
**Status:** ✅ ALL PASS
**Scope:** 50 representative addresses across all Inner West councils

**Test Results:**
| Council | Tests | Pass | Warn | Fail | Avg Provisions | Topic | PDF |
|---------|-------|------|------|------|----------------|-------|-----|
| Marrickville | 17 | 17 | 0 | 0 | 623 | 95% | 100% |
| Leichhardt | 17 | 17 | 0 | 0 | 2,790 | 90% | 100% |
| Ashfield | 16 | 16 | 0 | 0 | 1,502 | 93% | 100% |
| **TOTAL** | **50** | **50** | **0** | **0** | - | - | - |

**Zones Tested:**
- R2, R3 (residential)
- B1, B2, B4 (business)
- IN1, IN2 (industrial)

**Conclusion:** All 50 addresses return complete, accurate provision data with 100% PDF coverage.

### Two-Table Architecture Clarification (2025-12-01)
**Status:** DOCUMENTED

**Issue:** Previous sessions incorrectly assumed Leichhardt's 28% LLM coverage meant incomplete extraction.

**Reality:**
- LLM extraction is INTENTIONALLY SELECTIVE - only extracts actionable development controls
- 20-30% extraction rate is NORMAL - most DCP text is objectives, definitions, context
- Leichhardt Part C Section 1: 1,782 raw → 342 LLM (19%) is CORRECT
- Marrickville >100% is also correct - one paragraph can yield multiple requirements

**Coverage (verified 2025-12-01):**
- Ashfield: 791 LLM / 1,579 raw = 50%
- Marrickville: 1,338 LLM / 985 raw = 136%
- Leichhardt: 834 LLM / 2,989 raw = 28%

**DO NOT** assume low percentage means extraction needs to be re-run.

### DQ-16: Heritage Topic Fragmentation (2025-12-07)
**Status:** ✅ FIXED
**Priority:** P1 - HIGH (was)
**Problem:** Ashfield Heritage chapter provisions split across multiple topics in UI

**Evidence:**
- User sees: Heritage (187), Character (80), Fencing (22), Streetscape (22), etc.
- Reality: ALL 364 provisions are from Heritage chapter (part_name='Heritage')
- The `category` field (subject matter) is being used as `v2_topic` in API response

**Root Cause:**
In `queryHeritageFromDcpGeneralRequirements()` (for-property/route.ts:363):
```sql
INITCAP(REPLACE(category, '_', ' ')) as v2_topic
```
This maps `category` (e.g., 'character', 'fencing') to `v2_topic` instead of using 'Heritage'.

**Fix Applied (2025-12-07):**

1. **API change** (`for-property/route.ts`):
   - Changed: `CASE WHEN part_name = 'Heritage' THEN 'Heritage' ELSE ... END as v2_topic`
   - Added: `INITCAP(REPLACE(category, '_', ' ')) as v2_heritage_subcategory`
   - Fixed: Changed `part_name ILIKE '%Heritage%'` to exact match `part_name = 'Heritage'`
     (Excludes Leichhardt "Connections (Heritage and Transport)" which is NOT heritage)

2. **TypeScript types** (`ProvisionsByTopic.tsx`):
   - Added `v2_heritage_subcategory?: string` to Provision interface

3. **UI enhancement** (`ProvisionsByTopic.tsx`):
   - Added subcategory grouping within Heritage topic
   - Shows collapsible sections: Character (80), Fencing (22), Heritage (187), etc.

**Result:**
- Before: Heritage: 187, Character: 80, Fencing: 22 (separate topics)
- After: Heritage: 364 (consolidated with subcategory grouping)

**Also Fixed:**
- Leichhardt "Connections (Heritage and Transport)" no longer incorrectly included as heritage
- 78 provisions correctly excluded (they're about events/safety, not heritage)

### DQ-17: "Orphaned" Non-Heritage Provisions (2025-12-07)
**Status:** ✅ RESOLVED - NOT ORPHANED
**Priority:** N/A - Working as intended
**Initial Concern:** 1,072 provisions in `dcp_general_requirements` not returned by provisions UI

**Investigation (2025-12-07):**

Provisions by council not shown in main provisions UI:
- Leichhardt: 695 (83% of their 834 LLM provisions)
- Ashfield: 212 (27% of their 791)
- Marrickville: 69 (5% of their 1,338)

**Key Discovery: These ARE Used by Capacity API**

Tested `/api/capacity/calculate` in production - it queries `dcp_general_requirements` for:
- **Parking**: Returns clean data like "One car parking space is required per dwelling"
- **Setbacks**: Returns 8 structured setback values
- **Landscaping**: Queries this table (currently returns empty for Ashfield)

**Why Two Tables Exist (Intentional Architecture):**

| Table | Used By | Data Quality | Purpose |
|-------|---------|--------------|---------|
| `regulatory_provisions` | Provisions UI | Raw PDF text, OCR artifacts, verbose | Show full DCP context |
| `dcp_general_requirements` | Capacity API, Heritage UI | LLM-cleaned, distilled | Power calculations |

**Raw vs LLM Quality Comparison:**

LLM (capacity API):
> "One car parking space is required per dwelling"

Raw (provisions UI):
> "Parking requirement for restaurant $2 0 0 { \mathrm { m } } 2 - 1$ space per $4 0 \mathrm { m } 2$..."

The raw data has LaTeX artifacts and OCR noise. LLM extraction cleaned this into usable requirements.

**Conclusion:**
The "orphaned" provisions are NOT orphaned - they power the capacity calculator with clean data.
The two-table architecture is intentional separation of concerns:
- Raw table → provisions display (full context)
- LLM table → calculations (clean values)

**No action required.** Architecture is correct.

### DQ-18: Marrickville pdf_page Field (2026-01-12)
**Status:** ✅ FIXED
**Priority:** P1 (was)

**Understanding:**
- Marrickville DCP was split into 19+ separate PDF files by section
- Each section PDF starts at page 1 (relative numbering)
- `pdf_page` stores the relative page within each section (CORRECT)
- `pdf_page_image_url` contains absolute page numbers across combined document
- Images load correctly from URL; labels show relative page within section

**Incorrect "Fix" Applied & Reverted (2026-01-12):**
1. `DQ18_fix_marrickville_page_numbers.py` incorrectly changed pdf_page to absolute numbers
2. This broke the UI labels (e.g., "Page 5" instead of "Page 1" for first page of Landscaping section)
3. `DQ18_revert_marrickville_pages.py` restored correct relative page numbers
4. Formula: `relative_page = url_page - section_min_page + 1`
5. 1,671 provisions corrected back to relative numbering

**Part 4.1 Specific Issue (2026-01-12):**
- Part 4.1 Zone-Specific provisions showed wrong page numbers (e.g., "Page 5" when PDF footer showed "Page 1")
- Root cause: URL filename truncation created two groups (`_4.1_Low_Density_Res` vs `_4.1_Low_Density_Resid`)
- Each group calculated separate min_url, giving wrong offsets for the truncated variant
- Additional issue: TOC pages (url pages 3-6) were included in min calculation, but actual content starts at page 7

**Fix Applied:**
1. `DQ18_fix_by_section_number.py` - Groups by section number (e.g., "4_1") instead of URL filename
2. `DQ18_fix_exclude_toc.py` - Excludes TOC pages (containing "........") from min calculation
3. `DQ18_fix_part41_direct.py` - Direct fix using confirmed data: page_7.png = PDF page 1
   - MIN_CONTENT_URL = 7 (user confirmed from PDF footer inspection)
   - TOC pages (url 3-6) set to pdf_page = 1
   - Content pages: `pdf_page = url_page - 7 + 1`

**Verification:**
- url_page=7 → pdf_page=1 ✓
- UI now shows correct page numbers matching PDF footers

**Fix Scripts:** `scripts/fixes/DQ18_*.py`

**Current State:**
- `pdf_page` = relative page within each section PDF (correct for display)
- Images load from URL with absolute pages (correct rendering)
- UI shows "View Part 2 Page 1" for first page of each section (correct)

### DQ-25: Transport & Infrastructure sepp_structured_requirements Empty (2026-02-14)
**Status:** ⏳ BACKLOG
**Priority:** P2 — blocks classified road noise feature for certifiers

**Problem:** `sepp_structured_requirements` table has zero rows for `sepp_id = 'transport_infrastructure_2021'`. The UI transport section (`StateLevelControls.tsx` lines 658-672) is fully wired but never renders because the underlying data was never populated.

**What's blocking the feature:**
- `sepp-router.ts` adds `SEPP_TRANSPORT_INFRASTRUCTURE_2021` to every property unconditionally (line 126-128)
- `StateLevelControls` fetches `/api/sepp/structured-requirements` with `seppId = 'transport_infrastructure_2021'`
- API queries `sepp_structured_requirements WHERE sepp_id = 'transport_infrastructure_2021'` → empty → nothing renders

**What needs to go in this table:**
Three provision categories relevant to residential certifiers:
1. **Classified road corridor** — noise attenuation requirements for dwellings within X metres of classified roads (State Roads, RMS/TfNSW). Affects large % of inner-Sydney properties (Parramatta Rd, King St etc.). Most important for CDC certifiers.
2. **Rail corridor** — noise/vibration requirements near railway lines
3. **Airport obstacle limitation surfaces** — height controls near Sydney/Bankstown airports

**Source document:** `State_Environmental_Planning_Policy_Transport_and_Infrastructure_2021__NSW_Legislation` (2,733 provisions) — but v2_topic tagging is wrong (see DQ-24). Will need either:
- Manual curation of the specific classified road/rail/airport clauses into `sepp_structured_requirements`, OR
- Fix DQ-24 first (retag document), then build query-based lookup

**Triggering condition:** Should only show when Planning Portal API detects classified road corridor or rail corridor proximity — not for every property. Currently added unconditionally in sepp-router.ts (should be conditional).

**Do not fix until:** Classified road/rail corridor detection from Planning Portal is confirmed working for a test address on a classified road.

---

### DQ-24: Transport & Infrastructure SEPP v2_topic Retag (2026-02-14)
**Status:** ⏳ BACKLOG
**Priority:** P3 — No current production impact
**Document:** `State_Environmental_Planning_Policy_Transport_and_Infrastructure_2021__NSW_Legislation` (2,733 provisions)

**Problem:** Entire document tagged with DCP-style topic taxonomy (heritage, building_form, height, landscaping, waste, signage etc.) which is wrong for a state infrastructure instrument. Solar/wind turbine provisions (the main use case) are tagged `waste` instead of `solar`.

**Distribution of wrong tags:**
- (null): 1,724 (63%)
- heritage: 116, building_form: 110, height: 106, landscaping: 95, safety: 94, access: 87, waste: 83, signage: 59, stormwater: 47, trees: 41, fencing: 40, flooding: 38, parking: 33
- solar: 20 (only correct ones)

**Root cause:** DCP topic taxonomy applied to a SEPP document during an earlier tagging pass. DCP labels (setbacks, heritage, signage etc.) are meaningless for infrastructure development types.

**Current production impact:** ZERO — live app uses `sepp_structured_requirements` table for the transport section, not `regulatory_provisions`. Broken tags are never queried by the UI.

**Future impact:** Blocks solar provision browser — certifier filtering by Solar would see 0 actionable provisions.

**Fix required:**
1. Clear all v2_topic values for this document
2. Re-run classification with infrastructure-appropriate taxonomy: roads, rail, electricity/solar, water/stormwater, parking, community_infrastructure, general
3. Note: the 168-provision duplicate (`State_Environmental_Planning_Policy_(Transport_and_Infrastructure)_2021___NSW_Legislation` with parentheses) also exists — may need cleanup

**Do not fix until:** Solar provision browser is being built.

---

### DQ-26: Marrickville Truncated pdf_page_image_url Stems (2026-03-04)
**Status:** ✅ FIXED
**Priority:** P1 (was)

**Problem:** Old Marrickville provisions (double-underscore document_id format from first extraction pass) had `pdf_page_image_url` pointing to truncated R2 image filenames (e.g., `Signs_and_Adv_page_5.png` instead of `Signs_and_Advertising_page_5.png`). New re-extraction provisions used full names matching actual R2 filenames. When old images were absent from R2, PDF link buttons showed broken images.

**Scope:** 57 chapters, 391 provisions. Heritage chapter (`8.0_Heritage`) correctly excluded — it has 244 new provisions confirming it's a valid complete chapter name, not a truncation.

**Root Cause:** First extraction pass used truncated PDF filenames (likely Windows path-length limit). Image files were uploaded to R2 with truncated names. Re-extraction used full filenames. Some old images were deleted/overwritten; others remain. For Landscaping chapter (first reported), old images were absent from R2.

**Fix Applied:**
```sql
-- Pattern: replace truncated stem with full stem, keep _page_N.png suffix
-- Example: Landscaping_an_page_N -> Landscaping_and_Open_Spaces_page_N
-- 57 UPDATE statements run in a single transaction, 391 total rows changed
```
Full-name images confirmed to exist in R2 (verified by working new provisions). Page numbers preserved exactly.

**Also fixed separately (2026-03-04):** The Landscaping chapter (14 provisions, first user-reported broken link) was fixed in the same session before this batch fix.

---

### DQ-27: Marrickville LaTeX Math Artefacts in provision_text (2026-03-04)
**Status:** ✅ FIXED
**Priority:** P1 (was)

**Problem:** 36 Marrickville provisions contained raw LaTeX math mode tokens from pdfplumber extraction. Example: "Contour lines and levels for sites in excess of 6 0 0 { \mathsf { m } } ^ { 2 }$" instead of "600m²".

**Patterns cleaned:**
- `\mathsf`, `\mathfrak`, `\mathtt` math font commands
- `{ \mathsf { m } } ^ { 2 }$` → `m²` (two variants: with and without outer `{ }`)
- `\mathsf { m m }` → `mm`, `\mathsf { p m }` → `pm`
- `\mathtt { x 0.6 }` → `x 0.6` (strip wrapper, keep content)
- `\star _ { \mathsf { N B } }` → `` (NB note markers)
- `{ , }` → `,` (LaTeX thousands separator)
- Trailing `$` delimiters
- Spaced digits: `6 0 0` → `600` (via lookbehind/lookahead patterns)

**Fix applied:** Python script + companion `preProcessReplacements` added to Marrickville config in `frontend-nextjs/lib/dcp-format-configs.ts` (safety net for future re-extractions).

**Script:** `scripts/fix_marrickville_latex.py` (gitignored, not committed to repo)

---

### Provision Text Formatting Enhancement (2026-01-12)
**Status:** ✅ IMPLEMENTED
**File:** `frontend-nextjs/lib/provision-text-formatter.ts`

**Issue:** Numbered lists (1. text 2. text 3. text) not being rendered as list items in provision display

**Fix Applied:**
Added numbered list detection to `splitInlineList()` function:
```typescript
// Pattern for numbered lists: "1. text 2. text 3. text"
const numberPattern = /(?:^|\s)(\d+)\.\s+/g;
const numberMatches = text.match(numberPattern);

if (numberMatches && numberMatches.length >= 2) {
  const parts = text.split(/(?=(?:^|\s)\d+\.\s+)/);
  const cleanParts = parts.map(p => p.trim()).filter(p => p.length > 0 && /^\d+\./.test(p));
  if (cleanParts.length >= 2) {
    return cleanParts;
  }
}
```

**Result:** Numbered lists now render as proper list items alongside roman numerals (i., ii.) and letters (a., b.)
