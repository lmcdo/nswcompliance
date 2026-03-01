# Standard Operating Procedure: Precinct Integration & UX Improvements

**Version:** 1.0
**Date:** 2025-10-27
**Applies To:** NSW Planning Compliance Engine
**Frequency:** As needed (data quality issues, UX updates)
**Owner:** Development Team

---

## Table of Contents

1. [Overview](#overview)
2. [SOP-001: Data Quality Assessment](#sop-001-data-quality-assessment)
3. [SOP-002: Provision Text Cleanup](#sop-002-provision-text-cleanup)
4. [SOP-003: Precinct Coverage Analysis](#sop-003-precinct-coverage-analysis)
5. [SOP-004: UX Improvements Implementation](#sop-004-ux-improvements-implementation)
6. [SOP-005: UX Testing Procedures](#sop-005-ux-testing-procedures)
7. [Troubleshooting Guide](#troubleshooting-guide)
8. [Rollback Procedures](#rollback-procedures)
9. [Appendices](#appendices)

---

## Overview

### Purpose

This SOP documents the complete workflow for:
1. Assessing data quality issues in DCP provisions
2. Cleaning malformed provision text
3. Analyzing precinct coverage and categorization
4. Implementing UX improvements for precinct integration
5. Testing UX improvements

### Scope

- **In Scope:** Marrickville DCP provisions, precinct boundaries, LLM categorization, frontend UX
- **Out of Scope:** Other LGAs, SEPP provisions, LEP data

### Prerequisites

**Required Access:**
- PostgreSQL database access (localhost:5432/nsw_planning)
- Python environment with psycopg2, dotenv
- Next.js development environment
- Git access to repository

**Required Knowledge:**
- SQL queries and regex patterns
- React/TypeScript
- PostgreSQL database operations
- Git version control

**Safety Requirements:**
- ALWAYS create database backup before any operation
- ALWAYS use `db_safety_wrapper.py` for database connections
- ALWAYS test on sample data before bulk operations

---

## SOP-001: Data Quality Assessment

### Purpose
Identify and prioritize data quality issues in regulatory provisions using the data quality decision matrix.

### Frequency
- Before any major database migration
- After PDF extraction/re-extraction
- Monthly data quality audits

### Procedure

#### Step 1: Create Safety Backup

```bash
# Navigate to project root
cd /path/to/compliance-engine

# Create timestamped backup
python -c "
import subprocess
from datetime import datetime

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
backup_file = f'backups/nsw_planning_quality_audit_{timestamp}.backup'

subprocess.run([
    'C:\\Program Files\\PostgreSQL\\17\\bin\\pg_dump.exe',
    '-h', 'localhost',
    '-p', '5432',
    '-U', 'postgres',
    '-d', 'nsw_planning',
    '-F', 'c',
    '-f', backup_file
])

print(f'Backup created: {backup_file}')
"
```

**Verification:** Check that backup file exists and has size > 0 bytes.

#### Step 2: Identify Malformed Provisions

Create analysis script `check_data_quality.py`:

```python
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='nsw_planning',
    user='postgres',
    password=os.getenv('DB_PASSWORD', 'postgres')
)

cur = conn.cursor()

print("=" * 60)
print("DATA QUALITY AUDIT - regulatory_provisions")
print("=" * 60)

# Check 1: Provisions with PDF headers
cur.execute("""
    SELECT
        document_id,
        COUNT(*) as total,
        COUNT(*) FILTER (WHERE provision_text ~ '^# [0-9]+ ') as malformed,
        ROUND(COUNT(*) FILTER (WHERE provision_text ~ '^# [0-9]+ ')::NUMERIC / COUNT(*) * 100, 1) as pct_malformed
    FROM regulatory_provisions
    WHERE document_id ~ 'Marrickville_DCP'
    GROUP BY document_id
    ORDER BY pct_malformed DESC
""")

print("\n1. PDF Header Malformation:")
for doc_id, total, malformed, pct in cur.fetchall():
    print(f"   {doc_id}: {malformed}/{total} ({pct}%)")

# Check 2: Very short provisions (likely incomplete)
cur.execute("""
    SELECT
        COUNT(*) as short_provisions,
        ROUND(COUNT(*)::NUMERIC / (SELECT COUNT(*) FROM regulatory_provisions WHERE document_id ~ 'Marrickville_DCP') * 100, 1) as pct
    FROM regulatory_provisions
    WHERE document_id ~ 'Marrickville_DCP'
    AND LENGTH(provision_text) < 50
""")

short_count, pct_short = cur.fetchone()
print(f"\n2. Very Short Provisions (<50 chars):")
print(f"   Count: {short_count} ({pct_short}%)")

# Check 3: Error messages in text
cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE document_id ~ 'Marrickville_DCP'
    AND provision_text ~ 'Error! Reference source not found'
""")

error_count = cur.fetchone()[0]
print(f"\n3. PDF Error Messages:")
print(f"   Count: {error_count}")

# Check 4: Sample malformed text
print("\n4. Sample Malformed Text:")
cur.execute("""
    SELECT provision_text
    FROM regulatory_provisions
    WHERE document_id ~ 'Marrickville_DCP'
    AND provision_text ~ '^# [0-9]+ '
    LIMIT 1
""")

sample = cur.fetchone()
if sample:
    print(f"   First 200 chars: {sample[0][:200]}")

conn.close()

print("\n" + "=" * 60)
print("AUDIT COMPLETE")
print("=" * 60)
```

**Run:**
```bash
python check_data_quality.py
```

#### Step 3: Apply Data Quality Decision Matrix

Use the decision matrix from `CLAUDE.md`:

| Question | Threshold | Priority |
|----------|-----------|----------|
| Does this affect a core data table? | Yes | Priority 1 or 2 |
| What percentage of data is affected? | >2% | Priority 1 |
| | 0.5-2% | Priority 2 |
| | <0.5% | Priority 3 |
| Do workarounds exist? | IRRELEVANT | Does not affect priority |
| Could future features use this data? | Yes | Must be fixed |

**Example Application:**
- 54.7% of provisions malformed → Priority 1
- Affects core table (regulatory_provisions) → Priority 1
- Workarounds exist (LLM categorization) → STILL Priority 1

#### Step 4: Document Findings

Create issue report:

```markdown
# Data Quality Issue: [Issue Name]

**Date:** YYYY-MM-DD
**Affected Table:** regulatory_provisions
**Percentage Affected:** XX.X%
**Priority:** Priority 1 (based on decision matrix)

## Issue Description
[Describe the malformation pattern]

## Impact Assessment
- Core table affected: Yes/No
- Percentage affected: XX%
- Future features impacted: Yes/No

## Recommended Action
[Cleanup procedure reference]

## Estimated Time
[Time estimate]
```

#### Step 5: Verify Against Standards

Check against CLAUDE.md standards:

- [ ] Priority correctly assigned using decision matrix
- [ ] Not deprioritized due to workarounds
- [ ] Core table impact assessed
- [ ] Future feature impact considered

### Deliverables

1. Data quality audit report
2. Sample malformed data
3. Priority assignment with justification
4. Recommended cleanup procedure

### Success Criteria

- All data quality issues identified
- Priority correctly assigned using decision matrix
- Backup created before analysis
- Findings documented

---

## SOP-002: Provision Text Cleanup

### Purpose
Remove PDF extraction artifacts (page headers, error messages) from regulatory provisions while preserving content and context.

### Frequency
- After data quality assessment identifies >2% malformation
- After PDF re-extraction
- When new DCP documents added

### Procedure

#### Step 1: Pre-Cleanup Safety

```bash
# Create backup (if not already created in SOP-001)
python -c "
import subprocess
from datetime import datetime

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
backup_file = f'backups/nsw_planning_before_provision_cleanup_{timestamp}.backup'

subprocess.run([
    'C:\\Program Files\\PostgreSQL\\17\\bin\\pg_dump.exe',
    '-h', 'localhost',
    '-p', '5432',
    '-U', 'postgres',
    '-d', 'nsw_planning',
    '-F', 'c',
    '-f', backup_file
])

print(f'Backup created: {backup_file}')
"
```

**Verification:** Backup file exists and size > 50 MB.

#### Step 2: Analyze Malformation Patterns

Create pattern analysis script `analyze_malformation_patterns.py`:

```python
import psycopg2
import os
from dotenv import load_dotenv
import re
from collections import Counter

load_dotenv()

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='nsw_planning',
    user='postgres',
    password=os.getenv('DB_PASSWORD', 'postgres')
)

cur = conn.cursor()

# Fetch all malformed provisions
cur.execute("""
    SELECT provision_text
    FROM regulatory_provisions
    WHERE document_id ~ 'Marrickville_DCP'
    AND provision_text ~ '^# [0-9]+ '
    LIMIT 100
""")

patterns = []
for row in cur.fetchall():
    text = row[0]
    # Extract first 3 lines
    lines = text.split('\n')[:3]
    pattern = '\n'.join(lines)
    patterns.append(pattern)

# Count pattern frequency
pattern_counts = Counter(patterns)

print("TOP 5 MALFORMATION PATTERNS:")
print("=" * 80)
for i, (pattern, count) in enumerate(pattern_counts.most_common(5), 1):
    print(f"\nPattern {i} (appears {count} times):")
    print(pattern[:200])
    print("-" * 80)

conn.close()
```

**Run:**
```bash
python analyze_malformation_patterns.py
```

#### Step 3: Design Cleanup Patterns

Based on analysis, create regex patterns:

**Pattern 1: Standard PDF Header with Repetition**
```regex
^# [0-9]+ Marrickville Development Control Plan 2011\n\n[0-9]+\nMarrickville Development Control Plan 2011\n
```

**Pattern 2: Headers with Error Messages**
```regex
^# [0-9]+ Marrickville Development Control Plan 2011\n\nError! Reference source not found\..*?\n
```

**Pattern 3: Simple Headers**
```regex
^# [0-9]+ Marrickville Development Control Plan 2011\n\n(?=[^0-9])
```

#### Step 4: Test on Sample Data

**CRITICAL:** Test on small sample before bulk operation.

```sql
-- Create test table
CREATE TEMP TABLE provision_cleanup_test AS
SELECT provision_id, provision_text
FROM regulatory_provisions
WHERE document_id ~ 'Marrickville_DCP'
AND provision_text ~ '^# [0-9]+ '
LIMIT 10;

-- Test Pattern 1
UPDATE provision_cleanup_test
SET provision_text = regexp_replace(
    provision_text,
    '^# [0-9]+ Marrickville Development Control Plan 2011\n\n[0-9]+\nMarrickville Development Control Plan 2011\n',
    ''
)
WHERE provision_text ~ '^# [0-9]+ Marrickville Development Control Plan';

-- Manually review results
SELECT provision_id, LEFT(provision_text, 200)
FROM provision_cleanup_test;
```

**Verification:**
- [ ] Headers removed correctly
- [ ] Content preserved
- [ ] No data loss
- [ ] Section identifiers kept

#### Step 5: Execute Bulk Cleanup

**ONLY proceed if Step 4 successful.**

Create cleanup script `cleanup_provision_text.sql`:

```sql
-- Begin transaction for safety
BEGIN;

-- Pattern 1: Standard PDF header with repetition
UPDATE regulatory_provisions
SET provision_text = regexp_replace(
    provision_text,
    '^# [0-9]+ Marrickville Development Control Plan 2011\n\n[0-9]+\nMarrickville Development Control Plan 2011\n',
    ''
)
WHERE document_id ~ 'Marrickville_DCP'
AND provision_text ~ '^# [0-9]+ Marrickville Development Control Plan';

-- Check affected rows
SELECT COUNT(*) as pattern1_cleaned FROM regulatory_provisions
WHERE document_id ~ 'Marrickville_DCP'
AND provision_text NOT LIKE '#%';

-- Pattern 2: Headers with error messages
UPDATE regulatory_provisions
SET provision_text = regexp_replace(
    provision_text,
    '^# [0-9]+ Marrickville Development Control Plan 2011\n\nError! Reference source not found\..*?\n',
    '',
    'n'
)
WHERE document_id ~ 'Marrickville_DCP'
AND provision_text ~ '^# [0-9]+ Marrickville.*Error!';

-- Pattern 3: Simple headers
UPDATE regulatory_provisions
SET provision_text = regexp_replace(
    provision_text,
    '^# [0-9]+ Marrickville Development Control Plan 2011\n\n',
    ''
)
WHERE document_id ~ 'Marrickville_DCP'
AND provision_text ~ '^# [0-9]+ Marrickville Development Control Plan 2011\n\n[^0-9]';

-- Final verification
SELECT
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE provision_text ~ '^#') as still_malformed,
    ROUND(COUNT(*) FILTER (WHERE provision_text ~ '^#')::NUMERIC / COUNT(*) * 100, 1) as pct_malformed
FROM regulatory_provisions
WHERE document_id ~ 'Marrickville_DCP';

-- If results look good, commit
-- If not, ROLLBACK
COMMIT;
```

**Execute:**
```bash
psql -h localhost -p 5432 -U postgres -d nsw_planning -f cleanup_provision_text.sql
```

#### Step 6: Migrate to Dependent Tables

If cleanup successful, update dependent tables:

```bash
# Re-run migration to dcp_precinct_provisions
psql -h localhost -p 5432 -U postgres -d nsw_planning -f migrations/populate_dcp_precinct_provisions.sql
```

#### Step 7: Verify Cleanup

Create verification script `verify_cleanup.py`:

```python
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='nsw_planning',
    user='postgres',
    password=os.getenv('DB_PASSWORD', 'postgres')
)

cur = conn.cursor()

print("=" * 60)
print("CLEANUP VERIFICATION")
print("=" * 60)

# Check malformation rate
cur.execute("""
    SELECT
        COUNT(*) as total,
        COUNT(*) FILTER (WHERE provision_text ~ '^#') as malformed,
        ROUND(COUNT(*) FILTER (WHERE provision_text ~ '^#')::NUMERIC / COUNT(*) * 100, 1) as pct
    FROM regulatory_provisions
    WHERE document_id ~ 'Marrickville_DCP'
""")

total, malformed, pct = cur.fetchone()
print(f"\nMalformation Rate: {malformed}/{total} ({pct}%)")

if pct < 2.0:
    print("✅ PASS: Malformation rate < 2%")
else:
    print("❌ FAIL: Malformation rate still too high")

# Sample cleaned text
print("\nSample Cleaned Text:")
cur.execute("""
    SELECT provision_text
    FROM regulatory_provisions
    WHERE document_id ~ 'Marrickville_DCP'
    AND provision_text NOT LIKE '#%'
    LIMIT 1
""")

sample = cur.fetchone()
if sample:
    print(f"First 300 chars: {sample[0][:300]}")

conn.close()

print("\n" + "=" * 60)
```

**Run:**
```bash
python verify_cleanup.py
```

#### Step 8: Document Results

Create completion report `PROVISION_TEXT_CLEANUP_[DATE].md`:

```markdown
# Provision Text Cleanup - [Date]

## Summary
- Total provisions: XXX
- Cleaned: XXX (XX.X%)
- Remaining malformed: XXX (X.X%)

## Patterns Applied
1. Pattern 1: XXX provisions
2. Pattern 2: XXX provisions
3. Pattern 3: XXX provisions

## Before/After Samples
[Include samples]

## Verification Results
- Malformation rate: X.X%
- Pass criteria: < 2%
- Status: PASS/FAIL

## Backup Location
backups/nsw_planning_before_provision_cleanup_YYYYMMDD_HHMMSS.backup
```

### Deliverables

1. Database backup before cleanup
2. Cleanup SQL script
3. Verification report
4. Completion documentation

### Success Criteria

- [ ] Malformation rate reduced to < 2%
- [ ] No data loss
- [ ] Section identifiers preserved
- [ ] Dependent tables updated
- [ ] Backup created and verified
- [ ] Completion report created

### Rollback Procedure

If cleanup fails or causes issues:

```bash
# Restore from backup
python -c "
import subprocess

backup_file = 'backups/nsw_planning_before_provision_cleanup_20251027.backup'

subprocess.run([
    'C:\\Program Files\\PostgreSQL\\17\\bin\\pg_restore.exe',
    '-h', 'localhost',
    '-p', '5432',
    '-U', 'postgres',
    '-d', 'nsw_planning',
    '--clean',
    backup_file
])

print('Database restored from backup')
"
```

---

## SOP-003: Precinct Coverage Analysis

### Purpose
Analyze the completeness of precinct provision data and LLM categorization to identify gaps.

### Frequency
- After new precinct extraction
- Monthly coverage audits
- Before major releases

### Procedure

#### Step 1: Check Precinct Boundary Coverage

```python
# check_precinct_coverage.py
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='nsw_planning',
    user='postgres',
    password=os.getenv('DB_PASSWORD', 'postgres')
)

cur = conn.cursor()

print("=" * 60)
print("PRECINCT COVERAGE ANALYSIS")
print("=" * 60)

# Total precincts
cur.execute("SELECT COUNT(*) FROM dcp_precinct_boundaries")
total_precincts = cur.fetchone()[0]
print(f"\nTotal Precincts: {total_precincts}")

# Precincts with boundaries
cur.execute("""
    SELECT COUNT(*)
    FROM dcp_precinct_boundaries
    WHERE boundary_geom IS NOT NULL
""")
with_boundaries = cur.fetchone()[0]
print(f"With Boundaries: {with_boundaries}/{total_precincts}")

# Precincts with provisions
cur.execute("""
    SELECT COUNT(DISTINCT precinct_id)
    FROM dcp_precinct_provisions
""")
with_provisions = cur.fetchone()[0]
print(f"With Provisions: {with_provisions}/{total_precincts}")

# Precincts with categorization
cur.execute("""
    SELECT COUNT(DISTINCT precinct_id)
    FROM dcp_precinct_requirements
""")
with_categorization = cur.fetchone()[0]
print(f"With LLM Categorization: {with_categorization}/{total_precincts}")

conn.close()

print("\n" + "=" * 60)
```

**Run:**
```bash
python check_precinct_coverage.py
```

#### Step 2: Identify Missing Provisions

```sql
-- missing_precinct_provisions.sql
SELECT
    pb.precinct_id,
    pb.precinct_name,
    COUNT(pp.provision_id) as provision_count
FROM dcp_precinct_boundaries pb
LEFT JOIN dcp_precinct_provisions pp ON pb.precinct_id = pp.precinct_id
GROUP BY pb.precinct_id, pb.precinct_name
HAVING COUNT(pp.provision_id) = 0
ORDER BY pb.precinct_id;
```

**Output:**
```
precinct_id | precinct_name | provision_count
------------|---------------|----------------
2_          | ...           | 0
36_         | ...           | 0
38_         | ...           | 0
40_         | ...           | 0
```

#### Step 3: Analyze Provision Density

```sql
-- provision_density.sql
SELECT
    pb.precinct_id,
    pb.precinct_name,
    COUNT(pp.provision_id) as provision_count,
    CASE
        WHEN COUNT(pp.provision_id) >= 20 THEN 'High'
        WHEN COUNT(pp.provision_id) BETWEEN 8 AND 19 THEN 'Medium'
        WHEN COUNT(pp.provision_id) BETWEEN 3 AND 7 THEN 'Low'
        WHEN COUNT(pp.provision_id) = 2 THEN 'Minimal'
        ELSE 'None'
    END as density_tier
FROM dcp_precinct_boundaries pb
LEFT JOIN dcp_precinct_provisions pp ON pb.precinct_id = pp.precinct_id
GROUP BY pb.precinct_id, pb.precinct_name
ORDER BY provision_count DESC;
```

#### Step 4: Check LLM Categorization Coverage

```sql
-- categorization_gaps.sql
SELECT
    pb.precinct_id,
    pb.precinct_name,
    COUNT(DISTINCT pp.provision_id) as total_provisions,
    COUNT(DISTINCT pr.id) as categorized_requirements,
    CASE
        WHEN COUNT(DISTINCT pr.id) > 0 THEN 'Categorized'
        WHEN COUNT(DISTINCT pp.provision_id) > 0 THEN 'No Categorization'
        ELSE 'No Provisions'
    END as status
FROM dcp_precinct_boundaries pb
LEFT JOIN dcp_precinct_provisions pp ON pb.precinct_id = pp.precinct_id
LEFT JOIN dcp_precinct_requirements pr ON pb.precinct_id = pr.precinct_id
GROUP BY pb.precinct_id, pb.precinct_name
HAVING COUNT(DISTINCT pp.provision_id) > 0
   AND COUNT(DISTINCT pr.id) = 0
ORDER BY pb.precinct_id;
```

#### Step 5: Document Findings

Create analysis report `PRECINCT_COVERAGE_ANALYSIS_[DATE].md`:

```markdown
# Precinct Coverage Analysis - [Date]

## Summary Statistics
- Total Precincts: XX
- With Boundaries: XX (XX%)
- With Provisions: XX (XX%)
- With LLM Categorization: XX (XX%)

## Missing Provisions
[List precincts with no provisions]

## Missing Categorization
[List precincts with provisions but no categorization]

## Provision Density Distribution
| Tier | Count Range | Number of Precincts |
|------|-------------|---------------------|
| High | 20+ | X |
| Medium | 8-19 | X |
| Low | 3-7 | X |
| Minimal | 2 | X |
| None | 0 | X |

## Recommended Actions
1. Priority 1: Extract provisions for precincts [list]
2. Priority 2: Run LLM categorization for precincts [list]
3. Priority 3: Review sparse precincts [list]
```

### Deliverables

1. Coverage statistics report
2. List of precincts with missing data
3. Provision density analysis
4. Recommended action items with priorities

### Success Criteria

- [ ] All precincts analyzed
- [ ] Missing data identified
- [ ] Priorities assigned
- [ ] Action items created

---

## SOP-004: UX Improvements Implementation

### Purpose
Implement UX enhancements for precinct integration, including info boxes, cross-references, and scroll functionality.

### Frequency
- As needed for UX improvements
- After user feedback
- During feature development

### Procedure

#### Step 1: Review Requirements

Create requirements document:

```markdown
# UX Improvement Requirements

## Feature 1: [Feature Name]
- **Purpose:** [What problem does it solve]
- **User Story:** As a [user], I want [feature] so that [benefit]
- **Acceptance Criteria:**
  - [ ] Criterion 1
  - [ ] Criterion 2

## Feature 2: [Feature Name]
[Same structure]
```

**Example from previous session:**

**Feature 1: "Supplement or Override" Info Box**
- **Purpose:** Explain relationship between general and precinct controls
- **User Story:** As a certifier, I want to understand when precinct controls override general controls so that I can apply the correct requirements
- **Acceptance Criteria:**
  - [ ] Info box visible in precinct section
  - [ ] Clear explanation of precedence rules
  - [ ] Professional styling

#### Step 2: Create Git Branch

```bash
git checkout -b feature/ux-precinct-improvements
```

#### Step 3: Implement Frontend Changes

**Component 1: CategorizedRequirementsCard.tsx**

Location: `frontend-nextjs/components/compliance/CategorizedRequirementsCard.tsx`

```typescript
// Add ID for scroll target
<Card
  id="precinct-requirements-card"
  className={`${className} border-purple-200 bg-purple-50/30 transition-all`}
>
  <CardHeader>
    {/* ... existing header */}
  </CardHeader>

  <CardContent className="space-y-3">
    {/* NEW: Info Box */}
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
      <div className="flex items-start gap-2">
        <span className="text-blue-600 text-lg flex-shrink-0">💡</span>
        <div className="text-sm text-gray-700">
          <strong className="text-blue-900">How Precinct Controls Work:</strong>
          <p className="mt-1">
            These location-specific requirements <strong>supplement or override</strong>
            the general DCP controls shown above.
          </p>
          <ul className="mt-2 ml-4 space-y-1 text-xs">
            <li>If a precinct control conflicts with a general control,
                the precinct control takes precedence.</li>
            <li>Precinct controls may add additional requirements
                not found in general controls.</li>
          </ul>
        </div>
      </div>
    </div>

    {/* ... rest of component */}
  </CardContent>
</Card>
```

**Component 2: DCPProvisionsBrowser.tsx**

Location: `frontend-nextjs/components/compliance/DCPProvisionsBrowser.tsx`

```typescript
// Add new props
interface DCPProvisionsBrowserProps {
  // ... existing props
  precinctDetected?: boolean;
  precinctName?: string;
  precinctCategories?: Record<string, number>;
}

// Add category mapping
const categoryMapping: Record<string, string[]> = {
  'setback': ['setback_front', 'setback_side', 'setback_rear'],
  'landscaping': ['landscaping'],
  'privacy': ['privacy'],
  'solar': ['solar'],
  'design': ['character', 'design'],
  'open_space': ['open_space']
};

// Add scroll function
const scrollToPrecinct = () => {
  const element = document.getElementById('precinct-requirements-card');
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    // Flash effect
    element.classList.add('ring-4', 'ring-purple-400', 'ring-opacity-50');
    setTimeout(() => {
      element.classList.remove('ring-4', 'ring-purple-400', 'ring-opacity-50');
    }, 2000);
  }
};

// Add detection logic in render
{precinctDetected && (
  <div className="mb-4">
    {/* Overlap detection logic here */}
    {hasOverlap && (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
        {/* Warning UI */}
      </div>
    )}
  </div>
)}
```

**Component 3: ComplianceDashboard.tsx**

Location: `frontend-nextjs/components/compliance/ComplianceDashboard.tsx`

```typescript
// Pass precinct data to DCPProvisionsBrowser
<DCPProvisionsBrowser
  lga={propertyData.constraints.lga || ''}
  zone={propertyData.constraints.zone}
  developmentType={developmentType}
  address={propertyData.address}
  onViewProvision={handleViewProvision}
  // NEW: Pass precinct data
  precinctDetected={!!categorizedRequirements}
  precinctName={categorizedRequirements?.precinct?.precinct_name}
  precinctCategories={categorizedRequirements?.categories?.reduce((acc, cat) => {
    acc[cat.category] = cat.total_count;
    return acc;
  }, {} as Record<string, number>)}
/>
```

#### Step 4: Test Locally

```bash
cd frontend-nextjs
npm run dev
```

Navigate to `http://localhost:3000/assessment` and test:
- [ ] Info box displays
- [ ] Cross-reference link appears when appropriate
- [ ] Scroll functionality works
- [ ] Flash effect triggers

#### Step 5: Create Documentation

Create implementation guide `UX_IMPROVEMENTS_IMPLEMENTATION_[FEATURE].md`:

```markdown
# UX Improvements Implementation - [Feature Name]

## Summary
[Brief description]

## Components Modified
1. Component 1 (lines changed)
2. Component 2 (lines changed)

## Testing Instructions
[Detailed test cases]

## Known Limitations
[Any limitations]
```

#### Step 6: Commit Changes

```bash
git add frontend-nextjs/components/compliance/
git commit -m "feat: Implement precinct UX improvements

- Add 'supplement or override' info box to CategorizedRequirementsCard
- Add cross-reference link with overlap detection in DCPProvisionsBrowser
- Add scroll-to-precinct functionality with visual flash
- Pass precinct data from ComplianceDashboard

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Deliverables

1. Modified frontend components
2. Implementation documentation
3. Test cases
4. Git commit with changes

### Success Criteria

- [ ] All components implemented
- [ ] Local testing passed
- [ ] Documentation created
- [ ] Changes committed to git
- [ ] No console errors

---

## SOP-005: UX Testing Procedures

### Purpose
Systematically test UX improvements to ensure they work correctly across different scenarios.

### Frequency
- After every UX implementation
- Before production deployment
- After bug fixes

### Procedure

#### Step 1: Setup Test Environment

```bash
# Start Next.js dev server
cd frontend-nextjs
npm run dev

# Open browser to assessment page
# Navigate to: http://localhost:3000/assessment
```

#### Step 2: Execute Test Cases

**Test Case 1: Info Box Display**

**Objective:** Verify "supplement or override" info box shows correctly

**Steps:**
1. Enter address: "123 Fisher Street, Petersham" (Precinct 6)
2. Wait for precinct detection
3. Scroll down to "Precinct Requirements" card

**Expected Result:**
- Blue info box visible at top of precinct requirements
- Contains text: "How Precinct Controls Work"
- Explains supplement and override relationship
- Two bullet points visible

**Pass Criteria:** ✅ Info box renders with correct styling and text

**Record Results:**
```markdown
- Test Case: 1
- Date: YYYY-MM-DD
- Status: PASS/FAIL
- Notes: [Any issues observed]
- Screenshot: [Path to screenshot]
```

---

**Test Case 2: Cross-Reference - Setback Overlap**

**Objective:** Verify cross-reference link appears when searching for setbacks

**Steps:**
1. Enter address: "123 Fisher Street, Petersham" (Precinct 6)
2. Click "Browse All Dwelling House Provisions" to expand
3. Type "setback" in search bar

**Expected Result:**
- Yellow warning box appears below the blue info box
- Text: "⚠️ Don't miss precinct-specific controls:"
- Text: "This address is in Petersham South Precinct 6"
- Link: "→ View 3 additional setback requirements specific to this precinct below"

**Pass Criteria:** ✅ Warning box shows with correct count (3 setback requirements)

---

**Test Case 3: Scroll Functionality**

**Objective:** Verify clicking cross-reference link scrolls to precinct section

**Steps:**
1. Continue from Test Case 2
2. Click the blue link "→ View 3 additional setback requirements..."
3. Observe scroll behavior

**Expected Result:**
- Page smoothly scrolls down to precinct requirements card
- Precinct card briefly flashes with purple ring (2 seconds)
- Focus on precinct section

**Pass Criteria:** ✅ Smooth scroll + flash effect works

---

**Test Case 4: Category Filter Overlap**

**Objective:** Verify cross-reference detects category filter overlaps

**Steps:**
1. Enter address: "123 Fisher Street, Petersham" (Precinct 6)
2. Expand "Browse All Dwelling House Provisions"
3. Click "Landscaping" category filter button

**Expected Result:**
- Yellow warning box appears
- Link: "→ View 2 additional Landscaping requirements specific to this precinct below"

**Pass Criteria:** ✅ Warning detects category filter and shows correct count (2)

---

**Test Case 5: No Overlap - General Notice**

**Objective:** Verify purple notice shows when no search/filter overlap

**Steps:**
1. Enter address: "123 Fisher Street, Petersham" (Precinct 6)
2. Expand "Browse All Dwelling House Provisions"
3. Type "parking" in search (Precinct 6 has no parking requirements)

**Expected Result:**
- Purple notice appears (NOT yellow warning)
- Text: "📍 This address is in Petersham South Precinct 6"
- Link: "View precinct-specific requirements below"

**Pass Criteria:** ✅ Purple notice shows when no overlap detected

---

**Test Case 6: No Precinct - No Warning**

**Objective:** Verify nothing shows when address not in precinct

**Steps:**
1. Enter address: "1 George Street, Sydney" (not in any Marrickville precinct)
2. Expand "Browse All Dwelling House Provisions"
3. Search for "setback"

**Expected Result:**
- No yellow warning box
- No purple notice
- Only the standard blue info box about Part 2 + Part 4.X

**Pass Criteria:** ✅ No cross-reference UI when no precinct detected

---

**Test Case 7: Multiple Category Filters**

**Objective:** Verify detection works with multiple category filters

**Steps:**
1. Enter address: "123 Fisher Street, Petersham" (Precinct 6)
2. Expand "Browse All Dwelling House Provisions"
3. Click both "Setbacks" AND "Landscaping" category filters

**Expected Result:**
- Yellow warning box appears
- Link: "→ View 5 additional Setbacks, Landscaping requirements..."
- Count: 3 (setbacks) + 2 (landscaping) = 5 total

**Pass Criteria:** ✅ Correctly aggregates multiple category overlaps

---

**Test Case 8: Info Box Accessibility**

**Objective:** Verify info box is readable and accessible

**Steps:**
1. Enter address with precinct
2. Scroll to precinct requirements
3. Read the info box content

**Expected Result:**
- Text is legible (font size appropriate)
- Color contrast passes WCAG guidelines (blue on light blue)
- Content is understandable by non-technical users
- Icons (💡) render correctly

**Pass Criteria:** ✅ Info box is accessible and user-friendly

---

#### Step 3: Document Test Results

Create test report `UX_TESTING_REPORT_[DATE].md`:

```markdown
# UX Testing Report - [Date]

## Test Environment
- Browser: Chrome 120.x
- OS: Windows 11
- Next.js: Dev mode
- Date: YYYY-MM-DD

## Test Results Summary
- Total Test Cases: 8
- Passed: X
- Failed: X
- Pass Rate: XX%

## Individual Test Results

### Test Case 1: Info Box Display
- Status: PASS/FAIL
- Notes: [observations]
- Screenshot: [path]

[Repeat for all test cases]

## Issues Found
1. [Issue description, severity, component affected]
2. [Issue description, severity, component affected]

## Recommendations
[Any recommendations for fixes or improvements]

## Sign-off
- Tester: [Name]
- Date: [Date]
- Approved for: Staging / Production / Needs fixes
```

#### Step 4: Cross-Browser Testing (Optional but Recommended)

Test on multiple browsers:
- [ ] Chrome
- [ ] Firefox
- [ ] Safari (if on Mac)
- [ ] Edge

#### Step 5: Mobile Responsiveness Testing

Test on mobile devices or browser dev tools:
- [ ] iPhone 13 (390x844)
- [ ] Samsung Galaxy (412x915)
- [ ] iPad (768x1024)

### Deliverables

1. Completed test report
2. Screenshots of pass/fail states
3. List of issues found
4. Sign-off for next stage

### Success Criteria

- [ ] All test cases executed
- [ ] Pass rate > 90%
- [ ] Critical issues identified
- [ ] Report documented
- [ ] Sign-off obtained

---

## Troubleshooting Guide

### Issue 1: Database Connection Fails

**Symptoms:**
- Python scripts throw connection errors
- "psycopg2.OperationalError: could not connect"

**Causes:**
- PostgreSQL service not running
- Incorrect credentials
- Database doesn't exist

**Solutions:**

1. Check PostgreSQL service:
```bash
# Windows
services.msc
# Look for "postgresql-x64-17"
```

2. Verify credentials in `.env`:
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=nsw_planning
DB_USER=postgres
DB_PASSWORD=postgres
```

3. Test connection:
```bash
psql -h localhost -p 5432 -U postgres -d nsw_planning
```

---

### Issue 2: Backup Fails

**Symptoms:**
- pg_dump returns error
- Backup file is 0 bytes

**Causes:**
- Insufficient disk space
- Permissions issue
- Invalid database name

**Solutions:**

1. Check disk space:
```bash
dir C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\backups
```

2. Verify path exists:
```bash
mkdir backups  # if doesn't exist
```

3. Test pg_dump manually:
```bash
"C:\Program Files\PostgreSQL\17\bin\pg_dump.exe" -h localhost -p 5432 -U postgres -d nsw_planning -F c -f test_backup.backup
```

---

### Issue 3: Regex Cleanup Removes Too Much Content

**Symptoms:**
- Provisions are blank or truncated
- Important content missing

**Causes:**
- Regex pattern too aggressive
- Pattern matches actual content

**Solutions:**

1. **IMMEDIATELY ROLLBACK:**
```bash
# Restore from backup
pg_restore -h localhost -p 5432 -U postgres -d nsw_planning --clean backups/[backup_file].backup
```

2. Review regex pattern:
- Test on small sample first
- Check for edge cases
- Use negative lookahead to avoid content

3. Adjust pattern to be more conservative:
```regex
# BAD: Too aggressive
^#.*?\n\n

# GOOD: Specific pattern
^# [0-9]+ Marrickville Development Control Plan 2011\n\n
```

---

### Issue 4: Cross-Reference Link Not Appearing

**Symptoms:**
- Yellow warning box doesn't show when expected
- Purple notice not displaying

**Causes:**
- `categorizedRequirements` state not populated
- Props not passed correctly
- Category mapping mismatch

**Solutions:**

1. Check browser console:
```javascript
// Look for console.log from ComplianceDashboard
[ComplianceDashboard] Loaded X categorized requirements
```

2. Verify props in React DevTools:
```
DCPProvisionsBrowser
  - precinctDetected: true
  - precinctName: "Petersham South Precinct 6"
  - precinctCategories: { setback_front: 1, ... }
```

3. Check category mapping matches database:
```sql
SELECT DISTINCT category
FROM dcp_precinct_requirements
WHERE precinct_id = '6_';
```

4. Verify API response:
```bash
curl -X POST http://localhost:3000/api/compliance/precinct-requirements \
  -H "Content-Type: application/json" \
  -d '{"address":"123 Fisher Street, Petersham","lga":"Inner West"}'
```

---

### Issue 5: Scroll Not Working

**Symptoms:**
- Clicking link does nothing
- No scroll animation
- No flash effect

**Causes:**
- Element ID missing
- JavaScript error
- CSS transition not applied

**Solutions:**

1. Inspect element:
```html
<!-- Should exist -->
<div id="precinct-requirements-card" class="transition-all ...">
```

2. Check browser console for errors

3. Test scroll manually in console:
```javascript
const element = document.getElementById('precinct-requirements-card');
console.log(element); // Should not be null
element.scrollIntoView({ behavior: 'smooth', block: 'start' });
```

4. Verify `transition-all` class exists:
```css
/* Should be in Card component */
className="transition-all"
```

---

### Issue 6: LLM Categorization Missing

**Symptoms:**
- Precinct has provisions but no categorized requirements
- `dcp_precinct_requirements` empty for precinct

**Causes:**
- Malformed text prevented categorization
- LLM processing failed
- Precinct excluded from batch

**Solutions:**

1. Check if provisions exist:
```sql
SELECT COUNT(*)
FROM dcp_precinct_provisions
WHERE precinct_id = '47_';
```

2. Check if categorization ran:
```sql
SELECT *
FROM dcp_precinct_requirements
WHERE precinct_id = '47_';
```

3. Check extraction metadata:
```sql
SELECT extraction_metadata
FROM dcp_precinct_requirements
WHERE precinct_id = '6_'
LIMIT 1;
```

4. Re-run LLM categorization (if script exists):
```bash
python scripts/categorize_precinct_requirements.py --precinct-id 47_
```

---

## Rollback Procedures

### Rollback Level 1: Single Table Restore

**When to use:** Only one table affected, need quick rollback

```sql
-- Create temp table from backup
CREATE TABLE regulatory_provisions_backup AS
SELECT * FROM regulatory_provisions;

-- Restore specific table
DELETE FROM regulatory_provisions WHERE document_id ~ 'Marrickville_DCP';

-- Re-insert from backup table
INSERT INTO regulatory_provisions
SELECT * FROM regulatory_provisions_backup
WHERE document_id ~ 'Marrickville_DCP';

-- Verify
SELECT COUNT(*) FROM regulatory_provisions WHERE document_id ~ 'Marrickville_DCP';

-- Drop backup
DROP TABLE regulatory_provisions_backup;
```

---

### Rollback Level 2: Full Database Restore

**When to use:** Multiple tables affected, major corruption

```bash
# Stop application
# Kill Next.js dev server (Ctrl+C)

# Restore database from backup
python -c "
import subprocess

backup_file = 'backups/nsw_planning_before_provision_cleanup_20251027.backup'

# Clean and restore
subprocess.run([
    'C:\\Program Files\\PostgreSQL\\17\\bin\\pg_restore.exe',
    '-h', 'localhost',
    '-p', '5432',
    '-U', 'postgres',
    '-d', 'nsw_planning',
    '--clean',
    '--if-exists',
    backup_file
], check=True)

print('✅ Database restored from backup')
"

# Verify restoration
psql -h localhost -p 5432 -U postgres -d nsw_planning -c "SELECT COUNT(*) FROM regulatory_provisions WHERE document_id ~ 'Marrickville_DCP';"

# Restart application
cd frontend-nextjs
npm run dev
```

---

### Rollback Level 3: Git Revert (Frontend Changes)

**When to use:** Frontend changes causing issues

```bash
# Check current branch
git branch

# View recent commits
git log --oneline -5

# Revert specific commit (keeps history)
git revert [commit-hash]

# OR hard reset (destructive, use with caution)
git reset --hard HEAD~1

# Rebuild Next.js
cd frontend-nextjs
rm -rf .next
npm run dev
```

---

## Appendices

### Appendix A: Test Data Reference

**Test Addresses:**

| Address | Precinct | Provisions | Categorization | Notes |
|---------|----------|------------|----------------|-------|
| 123 Fisher Street, Petersham | 6_ (Petersham South) | 34 | ✅ | Good test case |
| 40 Lackey Street, Marrickville | 40_ (Town Centre) | 0 | ❌ | Missing provisions |
| 20 Pile Street, Marrickville | 47_ (Victoria Road) | 46 | ❌ | Most provisions |

**Expected Categorization for Precinct 6:**
```json
{
  "building_height": 1,
  "landscaping": 2,
  "other": 3,
  "setback_front": 1,
  "setback_rear": 1,
  "setback_side": 1
}
```

---

### Appendix B: SQL Query Library

**Query 1: Check Malformation Rate**
```sql
SELECT
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE provision_text ~ '^#') as malformed,
    ROUND(COUNT(*) FILTER (WHERE provision_text ~ '^#')::NUMERIC / COUNT(*) * 100, 1) as pct
FROM regulatory_provisions
WHERE document_id ~ 'Marrickville_DCP';
```

**Query 2: Sample Malformed Text**
```sql
SELECT provision_id, LEFT(provision_text, 200)
FROM regulatory_provisions
WHERE document_id ~ 'Marrickville_DCP'
AND provision_text ~ '^#'
LIMIT 5;
```

**Query 3: Precinct Coverage Summary**
```sql
SELECT
    pb.precinct_id,
    pb.precinct_name,
    COUNT(DISTINCT pp.provision_id) as provisions,
    COUNT(DISTINCT pr.id) as requirements,
    CASE
        WHEN COUNT(DISTINCT pr.id) > 0 THEN '✅ Complete'
        WHEN COUNT(DISTINCT pp.provision_id) > 0 THEN '⚠️ No Categorization'
        ELSE '❌ No Provisions'
    END as status
FROM dcp_precinct_boundaries pb
LEFT JOIN dcp_precinct_provisions pp ON pb.precinct_id = pp.precinct_id
LEFT JOIN dcp_precinct_requirements pr ON pb.precinct_id = pr.precinct_id
GROUP BY pb.precinct_id, pb.precinct_name
ORDER BY pb.precinct_id;
```

**Query 4: Category Distribution**
```sql
SELECT
    category,
    COUNT(*) as requirement_count,
    COUNT(DISTINCT precinct_id) as precinct_count
FROM dcp_precinct_requirements
GROUP BY category
ORDER BY requirement_count DESC;
```

---

### Appendix C: Database Safety Checklist

Before ANY database operation:

- [ ] Read CLAUDE.md database section
- [ ] Create full backup
- [ ] Verify backup file exists and size > 0
- [ ] Test operation on sample data first
- [ ] Use transaction (BEGIN/COMMIT/ROLLBACK)
- [ ] Use timeouts (30 seconds max)
- [ ] Use db_safety_wrapper.py for connections
- [ ] Document what you're doing
- [ ] Have rollback plan ready

**If ANY issue:**
- [ ] STOP immediately
- [ ] Do NOT proceed
- [ ] Restore from backup
- [ ] Investigate root cause
- [ ] Document incident

---

### Appendix D: File Locations Reference

**Documentation:**
- SOP: `SOP_PRECINCT_INTEGRATION_AND_UX.md`
- CLAUDE.md: `CLAUDE.md`
- Primary Directive: `CLAUDE_PRIMARY_DIRECTIVE.md`

**Frontend Components:**
- ComplianceDashboard: `frontend-nextjs/components/compliance/ComplianceDashboard.tsx`
- DCPProvisionsBrowser: `frontend-nextjs/components/compliance/DCPProvisionsBrowser.tsx`
- CategorizedRequirementsCard: `frontend-nextjs/components/compliance/CategorizedRequirementsCard.tsx`
- PrecinctProvisionsBrowser: `frontend-nextjs/components/compliance/PrecinctProvisionsBrowser.tsx`

**API Routes:**
- Precinct Requirements: `frontend-nextjs/app/api/compliance/precinct-requirements/route.ts`
- DCP Provisions: `frontend-nextjs/app/api/dcp/provisions/route.ts`
- Precinct Match: `frontend-nextjs/app/api/precinct/match/route.ts`

**Database Migrations:**
- Precinct Provisions: `migrations/populate_dcp_precinct_provisions.sql`
- Precinct Boundaries: `migrations/create_precinct_boundaries.sql`

**Backups:**
- Location: `backups/`
- Naming: `nsw_planning_[purpose]_[YYYYMMDD_HHMMSS].backup`

---

### Appendix E: Glossary

**DCP:** Development Control Plan - Local planning controls
**LEP:** Local Environmental Plan - Zoning regulations
**SEPP:** State Environmental Planning Policy - State-level overrides
**LGA:** Local Government Area (e.g., Inner West Council)
**Precinct:** Sub-area within an LGA with specific planning controls
**Provision:** Individual planning requirement or control
**Categorization:** LLM-processed grouping of provisions by type
**Malformation:** Data corruption from PDF extraction artifacts

**Categories:**
- `setback_front`: Front boundary setback requirements
- `setback_side`: Side boundary setback requirements
- `setback_rear`: Rear boundary setback requirements
- `building_height`: Maximum building height controls
- `landscaping`: Landscape and vegetation requirements
- `character`: Heritage and streetscape character requirements
- `privacy`: Privacy and overlooking controls
- `solar`: Solar access requirements
- `parking`: Vehicle parking requirements
- `other`: Miscellaneous requirements

---

### Appendix F: Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-27 | Claude | Initial SOP creation |

---

### Appendix G: Contact Information

**For Database Issues:**
- Refer to: CLAUDE.md database section
- Run: `./scripts/db_safety_check.sh`

**For Frontend Issues:**
- Check: Browser console for errors
- Use: React DevTools for component inspection

**For Rollback:**
- See: Rollback Procedures section
- Backup location: `backups/` directory

---

**END OF SOP**
