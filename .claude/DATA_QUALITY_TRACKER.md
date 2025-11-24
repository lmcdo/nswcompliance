# Data Quality Tracker

**Purpose:** Track data quality issues systematically across Claude sessions.

**Last Updated:** 2024-11-24
**Session:** Post 4-layer API implementation

---

## Context Files to Read First

| Priority | File | Purpose |
|----------|------|---------|
| 1 | `.claude/prp/INDEX.md` | Architecture overview, implementation state |
| 2 | `PROVISION_BASED_ARCHITECTURE_STRATEGY.md` | Full 8-part strategy |
| 3 | `DEPLOYMENT.md` | How to sync local/Supabase |
| 4 | **THIS FILE** | Current quality issues and fix progress |

---

## Current Quality Issues (Priority Order)

### DQ-1: Precinct Filtering Returns 0 Provisions
**Status:** NOT STARTED
**Priority:** P1 - CRITICAL
**Evidence:** Full cascade with `precinct_id='12_'` returns Layer 4 = 0
**Root Cause:** Unknown - either no provisions tagged with '12_' or format mismatch
**Fix Script:** TBD
**Verification:** `test_workflow_quality.py` should show >0 precinct provisions

### DQ-2: Topic Misclassification
**Status:** NOT STARTED
**Priority:** P1 - HIGH
**Evidence:** "Car parking design controls" tagged as HEIGHT topic
**Root Cause:** v2_topic enrichment logic flawed or incomplete
**Fix Script:** TBD - re-run topic classification
**Verification:** Parking provisions should be under 'parking' topic

### DQ-3: Provision Text Contains Headers Not Controls
**Status:** NOT STARTED
**Priority:** P2 - MEDIUM
**Evidence:** "Part 4 Multi Dwelling Housing" is a chapter title, not actionable
**Root Cause:** Extraction captured structure, not filtered to controls only
**Fix Script:** Filter out provisions that are headers/titles
**Verification:** Sample provisions should all be actionable controls

### DQ-4: v2_marker Mostly NULL
**Status:** NOT STARTED
**Priority:** P2 - MEDIUM
**Evidence:** Most provisions show marker=None
**Root Cause:** Marker extraction (C1, DS2, etc.) not working
**Fix Script:** Re-extract markers from provision_text
**Verification:** >50% of controls should have markers

### DQ-5: Generic Layer Dominates (83%)
**Status:** NOT STARTED
**Priority:** P3 - LOW
**Evidence:** 500/600 provisions are generic, only 43 zone-specific
**Root Cause:** v2_applicable_zones not populated for many provisions
**Fix Script:** Enrich zone applicability from DCP source
**Verification:** Zone filter should significantly reduce count

### DQ-6: Duplicate Provisions
**Status:** NOT STARTED
**Priority:** P3 - LOW
**Evidence:** C15 appears twice in parking results
**Root Cause:** Duplicate rows in regulatory_provisions
**Fix Script:** Deduplicate by provision_text hash
**Verification:** No duplicate texts in results

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

### Next Session Should:
1. Start with DQ-1 (precinct filtering)
2. Investigate why precinct_id='12_' returns 0 provisions
3. Check v2_precinct_id values in database
