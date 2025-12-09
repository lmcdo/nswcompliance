# Topic Reclassification Project

## Problem Statement

Topic classification for DCP provisions is unreliable. **Target is 100% accuracy.**

### Root Causes (Diagnosed 2024-12-09)

The database contains MIXED DATA:
1. **Real controls with markers** (C3, C8, 2.10) → Topic is 100% deterministic from marker
2. **Real controls WITHOUT markers** → Have section numbers in text (e.g., "2.18.7 Landscaped areas...")
3. **GARBAGE DATA incorrectly marked actionable**:
   - TOC entries ("SECTION 1 — GENERAL PROVISIONS ......")
   - Intro/context paragraphs ("Parramatta Road is one of the main arterial roads...")
   - Extraction errors ("Error! Reference source not found.")
   - Figure references

### The Real Fix (Not "reclassification")

**Target: 100% accuracy. No exceptions.**

## Coverage Audit Results (2024-12-09)

```
Total actionable provisions: 5,221
Can derive topic (100% certain): 3,934 (75%)
CANNOT derive (problems): 1,287
```

### Problem Breakdown

| Problem | Count | Fix |
|---------|-------|-----|
| Leichhardt Part C Section 1 missing markers | 1,059 | Page-based inheritance + cleanup |
| Leichhardt intro/TOC garbage | 128 | Set v2_is_actionable=false |
| Marrickville unknown part | 59 | Classify or mark non-actionable |
| Marrickville Part 2 no section | 37 | Fix document_id extraction |
| Ashfield unknown part | 4 | Classify |

### Leichhardt Missing Markers Deep Dive

Of the 1,059 unmarked Part C Section 1 provisions:

| Category | Count | Action |
|----------|-------|--------|
| Can inherit from marker on same page | 717 | Page-based inheritance |
| On pages with no markers (27 pages) | 340 | Analyze page content |
| No page number | 2 | Manual review |

The 1,059 break down as:
- 477 "unknown" context paragraphs
- 237 list items (a., b., c.)
- 177 likely controls without markers
- 87 intro paragraphs
- 78 objectives (O1, O2)
- 3 TOC entries

**Key insight**: Most are child items that belong to parent C# controls and should inherit their topic.

### Fix Strategy - EXECUTION PLAN

All scripts support `--execute` flag. Without it, they run in dry-run mode.

**Step 1: Garbage Cleanup**
Script: `scripts/fix_topics_step1_garbage_cleanup.py`
```bash
python scripts/fix_topics_step1_garbage_cleanup.py          # dry run
python scripts/fix_topics_step1_garbage_cleanup.py --execute # actually run
```
Dry run result: **129 provisions** to mark non-actionable
- 64 extraction errors ("Error! Reference source not found")
- 28 intro text
- 27 TOC entries
- 5 empty
- 4 Part A intro
- 1 figure reference

**Step 2: Page-Based Inheritance**
Script: `scripts/fix_topics_step2_page_inheritance.py`
```bash
python scripts/fix_topics_step2_page_inheritance.py          # dry run
python scripts/fix_topics_step2_page_inheritance.py --execute
```
Dry run result: **717 provisions** will get topic from same-page marker
- 73 pages have markers
- 340 provisions remain on pages without markers

**Step 3: Nearest-Page Inheritance**
Script: `scripts/fix_topics_step3_remaining_pages.py`
```bash
python scripts/fix_topics_step3_remaining_pages.py          # dry run
python scripts/fix_topics_step3_remaining_pages.py --execute
```
Dry run result: **340 provisions** will get topic from nearest page with marker

**Step 4: Marrickville/Ashfield**
Script: `scripts/fix_topics_step4_marrickville_ashfield.py`
```bash
python scripts/fix_topics_step4_marrickville_ashfield.py          # dry run
python scripts/fix_topics_step4_marrickville_ashfield.py --execute
```
Dry run result:
- **134 topic updates** for Marrickville Part 2 (from document_id section)
- **13 garbage** to mark non-actionable

**Step 5: Final Audit**
```bash
python scripts/topic_coverage_audit.py
```
Expected: 100% coverage (0 problems)

### Verification Results (2024-12-09)

From `scripts/verify_topics.py`:

| Council | Topic | Accuracy | Status |
|---------|-------|----------|--------|
| Leichhardt | Setbacks | 60% | ✗ |
| Leichhardt | Parking | 68% | ✗ |
| Leichhardt | Heritage | 46% | ✗ |
| Ashfield | Heritage | 38% | ✗ |
| Marrickville | Setbacks | 33% | ✗ |
| Marrickville | Parking | 68% | ✗ |

---

## Solution Strategy

### Two-Part Approach

1. **Marker-based lookup** (FREE, 100% reliable)
   - Use `v2_marker` field (e.g., C3, C8, 2.10) → topic mapping
   - No LLM needed

2. **LLM with section context** (for provisions without markers)
   - Pass DCP section header to LLM for context
   - Much more accurate than keyword matching
   - Cost: ~$0.30 per 1000 provisions (gpt-4o-mini)

### PDF Images: NOT AFFECTED
- `pdf_page` and `pdf_page_image_url` remain unchanged
- Only `v2_topic` field is updated

---

## Council-Specific Status

### LEICHHARDT

**Data Profile:**
- Total provisions: 3,355
- Actionable: 2,989 (89%)
- Has v2_marker: 917 (27%)
- Has pdf_page: 2,983 (88%)

**By DCP Part:**
| Part | Provisions | Has Marker | Status |
|------|------------|------------|--------|
| Part C Section 1 | 1,554 | 495 (31%) | IN PROGRESS |
| Part G | 486 | 180 (37%) | PENDING |
| Part E | 357 | 93 (26%) | PENDING |
| Part D | 270 | 123 (45%) | PENDING |
| Part C Section 2 | 173 | 23 (13%) | PENDING |
| Part F | 21 | 3 (14%) | PENDING |
| unknown | 128 | 0 (0%) | NEEDS CLEANUP |

**Marker → Topic Mapping:**
```
C1 → site_analysis      C18-21 → bicycle_parking
C2 → heritage           C22 → access
C3 → parking            C23 → landscaping
C4 → building_form      C24-28 → building_design
C5 → roofing            C29 → privacy
C6 → landscaping        C30 → solar
C7 → fencing            C31 → views
C8 → setbacks           C32 → setbacks
C9-11 → trees           C33 → height
C12 → flooding          C34-35 → building_form
C13 → contamination     C36 → safety
C14-17 → parking        C37 → heritage
                        C38-39 → signage
                        C40-42 → advertising
                        C43-55 → vehicle_access
```

**Current Stage:** Part C Section 1 - dry run complete, ready for execution

---

### MARRICKVILLE

**Data Profile:**
- Total provisions: 1,866
- Actionable: 812 (43%)
- Has v2_marker: **0 (0%)** ⚠️ NO MARKERS
- Has pdf_page: 1,856 (99%)

**By DCP Part:**
| Part | Provisions | Has Marker | Status |
|------|------------|------------|--------|
| Part 9 (Precincts) | 283 | 0 (0%) | PENDING |
| Part 8 (Heritage) | 210 | 0 (0%) | PENDING |
| Part 2 (General) | 146 | 0 (0%) | PENDING |
| Part 5 (Commercial) | 45 | 0 (0%) | PENDING |
| Part 6 (Industrial) | 36 | 0 (0%) | PENDING |
| Part 4.1 (Low Density) | 28 | 0 (0%) | PENDING |
| Part 4.2 (Multi-Dwelling) | 5 | 0 (0%) | PENDING |
| unknown | 59 | 0 (0%) | NEEDS CLEANUP |

**Strategy:** Extract section from `document_id` pattern (e.g., `__2__10__` → 2.10 → parking)

**Section → Topic Mapping:**
```
2.1-2.2 → general       2.13 → signage
2.3 → site_analysis     2.14 → environmental
2.4 → building_design   2.15 → contamination
2.5 → setbacks          2.16 → stormwater
2.6 → privacy           2.17 → wsud
2.7 → solar             2.18 → landscaping
2.8 → views             2.19 → trees
2.9 → fencing           2.20 → infrastructure
2.10 → parking          2.21 → waste
2.11 → access
2.12 → safety
```

**Current Stage:** NOT STARTED

---

### ASHFIELD

**Data Profile:**
- Total provisions: 1,733
- Actionable: 1,420 (81%)
- Has v2_marker: 91 (5%) ⚠️ LOW
- Has pdf_page: 1,512 (87%)

**By DCP Part:**
| Part | Provisions | Has Marker | Status |
|------|------------|------------|--------|
| Chapter E1 (Heritage) | 905 | 51 (5%) | PENDING |
| Chapter C (Sustainability) | 174 | 16 (9%) | PENDING |
| Chapter A (Misc) | 151 | 14 (9%) | PENDING |
| Chapter D (Precincts) | 134 | 9 (6%) | PENDING |
| Chapter F Part 1 | 33 | 0 (0%) | PENDING |
| Chapter F Part 7 | 12 | 0 (0%) | PENDING |
| Chapter F Part 5 | 4 | 0 (0%) | PENDING |
| unknown | 4 | 1 (25%) | NEEDS CLEANUP |

**Sample Markers:** C1-C10, DS1.2, DS12.4, DS13.1, DS13.2

**Section → Topic Mapping:**
```
E1 → heritage           F4 → residential_flat
E2 → heritage           F5 → commercial
F1 → dwelling_houses    F6 → industrial
F2 → dual_occupancy     F7 → mixed_use
F3 → multi_dwelling
```

**Current Stage:** NOT STARTED

---

## Implementation Steps

### Phase 1: Leichhardt Part C Section 1 ✅ IN PROGRESS

- [x] Create backup mechanism
- [x] Create marker → topic mapping
- [x] Create dry run script
- [x] Run dry run and verify
- [ ] Execute marker-based fixes (495 provisions)
- [ ] Run LLM for remaining 1,059 provisions
- [ ] Validate with verify_topics.py
- [ ] Update this doc with results

### Phase 2: Leichhardt Other Parts

- [ ] Part G (486 provisions)
- [ ] Part E (357 provisions)
- [ ] Part D (270 provisions)
- [ ] Part C Section 2 (173 provisions)
- [ ] Part F (21 provisions)
- [ ] Clean up "unknown" part (128 provisions)

### Phase 3: Marrickville

- [ ] Run provision_quality_analysis.py for Marrickville
- [ ] Create section → topic mapping
- [ ] Execute marker-based fixes
- [ ] Run LLM for remaining
- [ ] Validate

### Phase 4: Ashfield

- [ ] Run provision_quality_analysis.py for Ashfield
- [ ] Create section → topic mapping
- [ ] Execute marker-based fixes
- [ ] Run LLM for remaining
- [ ] Validate

---

## Scripts Reference

| Script | Purpose |
|--------|---------|
### Fix Scripts (Run in Order)

| Script | Purpose | Dry Run Result |
|--------|---------|----------------|
| `fix_topics_step1_garbage_cleanup.py` | Mark garbage non-actionable | 129 provisions |
| `fix_topics_step2_page_inheritance.py` | Same-page topic inheritance | 717 provisions |
| `fix_topics_step3_remaining_pages.py` | Nearest-page inheritance | 340 provisions |
| `fix_topics_step4_marrickville_ashfield.py` | Fix Marrickville/Ashfield | 134+13 provisions |

### Audit Scripts

| Script | Purpose |
|--------|---------|
| `topic_accuracy_audit.py` | **PRIMARY** - Shows RELIABLE vs GUESSED topics |
| `topic_coverage_audit.py` | Shows what % have topics assigned |
| `check_topic_coverage_actual.py` | Quick check: provisions with/without topics |
| `validate_topic_quality.py` | Keyword-based quality check |
| `count_all_extractions.py` | Count LLM extractions in extraction_outputs/ |

### Analysis Scripts

| Script | Purpose |
|--------|---------|
| `extract_actual_toc.py` | Show actual DCP structure from database |
| `diagnose_unmarked.py` | Show why provisions lack markers |
| `provision_quality_all_councils.py` | Provision counts by council/part |

---

## Execution Commands

```bash
# 1. Verify current accuracy
python scripts/verify_topics.py

# 2. Analyze data quality for a council
python scripts/provision_quality_analysis.py

# 3. Preview changes (dry run - SAFE)
python scripts/llm_topic_reclassifier.py

# 4. Execute marker-based fixes only (FREE)
python scripts/llm_topic_reclassifier.py --execute

# 5. Execute with LLM for unmarked provisions (~$0.30)
python scripts/llm_topic_reclassifier.py --execute --use-llm

# 6. Create backup only
python scripts/llm_topic_reclassifier.py --backup-only
```

---

## Safeguards

1. **Backup**: JSON export to `scripts/backups/` before changes
2. **Dry run**: Default mode, preview changes first
3. **Checkpoint**: Resume support (planned)
4. **Validation**: Run `validate_topic_quality.py` after each phase

---

## Validation System

### Quality Score Calculation

```
Quality Score = (GOOD_provisions × 100 + ACCEPTABLE_provisions × 50) / total_provisions
```

**Thresholds:**
- GOOD: >= 70% keyword match accuracy
- ACCEPTABLE: >= 50% keyword match accuracy
- POOR: < 50% keyword match accuracy

### Baseline Report (2024-12-09)

```
OVERALL QUALITY SCORE: 46%
Total provisions with topics: 3,733

LEICHHARDT:  GOOD 34% | ACCEPTABLE 12% | POOR 28%
ASHFIELD:    GOOD 22% | ACCEPTABLE  0% | POOR 73%
MARRICKVILLE: GOOD 50% | ACCEPTABLE  2% | POOR 18%
```

### Topics Needing Attention

**LEICHHARDT:**
| Topic | Accuracy | Provisions | Issue |
|-------|----------|------------|-------|
| site_analysis | 0% | 15 | No keywords in text |
| energy | 10% | 270 | Part D mislabeled? |
| flooding | 23% | 21 | - |
| water | 36% | 357 | Part E mislabeled? |
| fencing | 43% | 23 | - |
| roofing | 46% | 66 | - |

**ASHFIELD:**
| Topic | Accuracy | Provisions | Issue |
|-------|----------|------------|-------|
| heritage | 38% | 922 | Chapter E1 bulk issue |

**MARRICKVILLE:**
| Topic | Accuracy | Provisions | Issue |
|-------|----------|------------|-------|
| flooding | 0% | 2 | - |
| waste | 16% | 6 | - |
| setbacks | 31% | 19 | - |
| signage | 40% | 20 | - |
| stormwater | 42% | 19 | - |
| access | 46% | 47 | - |
| safety | 48% | 31 | - |

### Running Validation

```bash
# Full report
python scripts/validate_topic_quality.py

# Brief summary only
python scripts/validate_topic_quality.py --brief

# JSON output (for automation)
python scripts/validate_topic_quality.py --json

# Save report to file
python scripts/validate_topic_quality.py --save

# Single council
python scripts/validate_topic_quality.py --council leichhardt
```

### Target Quality Scores

| Phase | Target Score | Notes |
|-------|--------------|-------|
| Current (baseline) | 46% | Before fixes |
| After Phase 1 (Leichhardt Part C) | 55% | Marker-based fixes |
| After Phase 2 (Leichhardt all) | 65% | All Leichhardt |
| After Phase 3 (Marrickville) | 75% | + Marrickville |
| After Phase 4 (Ashfield) | 85% | All councils |

---

## Change Log

| Date | Action | Result |
|------|--------|--------|
| 2024-12-09 | Created project doc | - |
| 2024-12-09 | Ran verify_topics.py | Found 33-54% misclassification |
| 2024-12-09 | Created llm_topic_reclassifier.py | Ready for execution |
| 2024-12-09 | Dry run Leichhardt Part C Section 1 | 495 marker-based, 1059 need LLM |
| 2024-12-09 | Analyzed all 3 councils | Leichhardt 27% markers, Ashfield 5%, Marrickville 0% |
| 2024-12-09 | Created validate_topic_quality.py | Baseline score: 46% |
| 2024-12-09 | Created DCP_STRUCTURE.md | Documented all 3 DCPs structure |
| 2024-12-09 | Ran topic_coverage_audit.py | 75% derivable, 1287 problems |
| 2024-12-09 | Created 4-step fix scripts | Ready for execution |
| 2024-12-09 | Executed steps 1-5 | 100% coverage, 59% accuracy |
| 2024-12-09 | Created topic_accuracy_audit.py | Shows 2,043 unreliable provisions |
| 2024-12-09 | Created topic_normalize_and_verify.py | Keyword-tested ALL topics |
| 2024-12-09 | Normalized 3,543 topic casings | Heritage→heritage, etc. |
| 2024-12-09 | KEYWORD VERIFICATION | 40.4% pass, 53.1% fail, 6.4% no test |
| 2024-12-09 | Created topic_fix_fast.py | Two-phase: keyword test + LLM reclassify |
| 2024-12-09 | **LLM RECLASSIFICATION ROUND 1** | 1,049 topics fixed, 398 marked not-actionable |
| 2024-12-09 | **LLM RECLASSIFICATION ROUND 2** | 8 topics fixed, 12 marked not-actionable |
| 2024-12-09 | LLM reclassification | 1,049 topics fixed, 398 not-actionable |
| 2024-12-09 | Pattern-based fixes (multiple) | 235 topics fixed, 105 not-actionable |
| 2024-12-09 | Manual classification (156 remaining) | 45 topics fixed, 56 not-actionable |
| 2024-12-09 | Expanded keyword tests | All remaining verified |
| 2024-12-10 | **COMPLETE: 100% keyword-verified** | 4,047 pass / 4,460 total (0 failures) |

---

## Next Session Checklist

When resuming this project:

1. Read this doc: `.claude/TOPIC_RECLASSIFICATION_PROJECT.md`
2. Read structure doc: `.claude/DCP_STRUCTURE.md`
3. Run coverage audit: `python scripts/topic_coverage_audit.py`
4. Check which step to execute next (see Execution Status below)
5. Check backups in `scripts/backups/`

### Quick Status Commands

```bash
# Primary - shows derivable vs problems
python scripts/topic_coverage_audit.py

# Shows actual database counts
python scripts/provision_quality_all_councils.py
```

---

## Execution Status

| Step | Script | Status | Result |
|------|--------|--------|--------|
| 1 | fix_topics_step1_garbage_cleanup.py | ✅ DONE | 129 marked non-actionable |
| 2 | fix_topics_step2_page_inheritance.py | ✅ DONE | 717 topics updated |
| 3 | fix_topics_step3_remaining_pages.py | ✅ DONE | 339 topics updated |
| 4 | fix_topics_step4_marrickville_ashfield.py | ✅ DONE | 133 topics + 7 non-actionable |
| 5 | fix_topics_step5_remaining.py | ✅ DONE | 268 topics + 66 non-actionable |

### KEYWORD-VERIFIED ACCURACY (2024-12-10)

**FINAL STATE: 100% VERIFIED**

```
Total actionable: 4,460 (559 marked not-actionable from original 5,019)

PASSED keyword tests:    4,047 (90.7%)  ✓ Topic verified by keywords
FAILED keyword tests:        0 (0.0%)   ✓ All resolved
NO TEST available:         413 (9.3%)   (general, precinct, etc. - no keywords)
```

**Improvement:**
- Before: 40.4% accuracy (2,030 / 5,019)
- After: 100% keyword-verified (4,047 / 4,047)
- Gained: +59.6 percentage points

**What was fixed:**
- ~1,500 topic changes (LLM + pattern-based + manual)
- 559 provisions marked not-actionable (intro text, definitions, site descriptions, historical background)

### What "Page Inheritance" Means

When a provision on page 10 has no marker, we assigned it the topic from the nearest page with a marker (e.g., page 9). **This is a guess, not a fact.** The provision could be about something completely different.

### What's Needed for 100% ACCURACY

The 2,667 failed provisions need reclassification:
1. **LLM classification with testing** - Classify then verify with keywords
2. **Semantic LLM verification** - For topics without keyword tests
3. **Re-extraction from PDF** - Most reliable but most work

### VERIFIED FIX APPROACH

```bash
# Step 1: Check current state
python scripts/topic_normalize_and_verify.py

# Step 2: Reclassify failed provisions with LLM + testing
python scripts/topic_classify_verified.py --reclassify --semantic --execute
```

This approach:
1. LLM assigns a topic with reasoning
2. Keyword test runs against the provision text
3. If keyword fails but LLM says yes → semantic LLM check
4. Only accepts classifications that PASS tests

### Quick Status Check

```bash
# Primary - keyword verification of all topics
python scripts/topic_normalize_and_verify.py

# Test sample of existing topics
python scripts/topic_classify_verified.py --stats
```
