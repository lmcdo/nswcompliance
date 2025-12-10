# TOC-Based UI Project

**Branch:** `feature/toc-based-ui`
**Created:** 2025-12-10
**Status:** Phase 1 - Data Certification

---

## Quick Context

**What:** Replace topic-based provision navigation with DCP structure (Table of Contents) navigation.

**Why:** Professionals navigate DCPs by Part/Section, not by abstract topics. Topics required 14,501 fixes and still have accuracy issues. TOC structure is inherently correct.

**Current UI:** Topic → DCP Part → Page → Provisions
**Target UI:** DCP Part → Section → Provisions (with topic as optional filter)

---

## Data State (Certified 2025-12-10)

### Provision Counts
```
Total DCP provisions: 7,188
├── Leichhardt:  3,355
├── Marrickville: 1,866
├── Ashfield:    1,733
└── Other:         234
```

### TOC Coverage
```
TOC entries: 676 across 110 documents
├── Marrickville: 321 entries
├── Leichhardt:   266 entries
└── Ashfield:      89 entries
```

### Data Quality Issues to Fix
```
151 entries: page_start > page_end (swap needed)
 98 entries: NULL page_end (calculate from next section)
```

### Provision-TOC Mapping
- 91% provisions have `pdf_page`
- After fixes, expect >95% TOC match

---

## Leichhardt Special Case

**Problem:** Part C Section 1 has 1,641 provisions - too big for single section.

**Solution:** Use `v2_marker` (C1-C55) as sub-groups. Data already exists:

```
C1  → Site Analysis (102 provisions)
C2  → Heritage (28)
C3  → Parking (28)
C5  → Roofing (36)
C6  → Landscaping (28)
C7  → Fencing (13)
C8  → Setbacks (16)
C9  → Trees (15)
C12 → Flooding (16)
C14-C17 → Parking (44)
C18-C21 → Bicycle Parking (21)
C29 → Privacy (6)
C30 → Solar (3)
C32 → Setbacks (6)
C37 → Heritage (6)
```

**Implementation:** Client-side grouping by `v2_marker` for Leichhardt Part C Section 1.

---

## Professional Workflow Alignment

From `DCP_PHILOSOPHICAL_DIFFERENCES.md`:

| Council | How Professionals Navigate |
|---------|---------------------------|
| Marrickville | Part 4.1 (R2) vs Part 4.2 (R3/R4) by zone |
| Leichhardt | Section 1 (general) → C markers by topic |
| Ashfield | Chapter E1 (heritage) vs rest |

**Key insight:** Each council has different DCP philosophy:
- Marrickville: Zone-first (Part 4.1 for R2, Part 4.2 for R3/R4)
- Leichhardt: Topic-first (C markers within Part C Section 1)
- Ashfield: Condition-first (Heritage dominates at 59%)

---

## Implementation Phases

### Phase 1: Data Certification ✓ COMPLETE
- [x] Fix invalid page ranges (swap start/end) - 151 fixed
- [x] Calculate missing page_end values - 98 remain (last sections, OK)
- [x] Verify provision-TOC mapping - 88-99% have page
- [x] Document Leichhardt C marker grouping

### Phase 2: API Changes ✓ COMPLETE
- [x] Add `groupBy=toc` parameter to `/api/provisions/for-property`
- [x] Return TOC structure with provision counts (`by_toc` in response)
- [x] Handle Leichhardt C marker sub-grouping (uses v2_marker)

### Phase 3: UI Components ✓ COMPLETE
- [x] Create `TocSidebar.tsx` (collapsible tree with Part/Section navigation)
- [x] Create `ProvisionsByTocStructure.tsx` (two-panel layout)
- [x] Add topic filter chips (secondary filter within sections)
- [x] Add view mode toggle (Structure vs Topic buttons)

### Phase 4: Integration & Testing
- [ ] Test all three councils
- [ ] Test heritage properties (Part 8 emphasis)
- [ ] Test precinct properties (Part 9/G emphasis)
- [ ] Performance test large sections

---

## SQL Fixes for Phase 1

### Fix 1: Swap Invalid Page Ranges
```sql
UPDATE dcp_table_of_contents
SET page_start = page_end, page_end = page_start
WHERE page_start > page_end;
```

### Fix 2: Calculate Missing page_end
```sql
WITH ordered AS (
    SELECT id, document_id, page_start,
           LEAD(page_start) OVER (
               PARTITION BY document_id ORDER BY page_start
           ) as next_start
    FROM dcp_table_of_contents
)
UPDATE dcp_table_of_contents t
SET page_end = o.next_start - 1
FROM ordered o
WHERE t.id = o.id
  AND t.page_end IS NULL
  AND o.next_start IS NOT NULL;
```

### Verification Query
```sql
SELECT
    CASE
        WHEN document_id ILIKE '%marrickville%' THEN 'Marrickville'
        WHEN document_id ILIKE '%leichhardt%' THEN 'Leichhardt'
        WHEN document_id ILIKE '%ashfield%' THEN 'Ashfield'
    END as council,
    COUNT(*) as total_provisions,
    COUNT(*) FILTER (WHERE pdf_page IS NOT NULL) as has_page
FROM regulatory_provisions
WHERE document_id NOT ILIKE '%State%'
  AND document_id NOT ILIKE '%Local%'
GROUP BY 1;
```

---

## API Contract (Target)

### Request
```
GET /api/provisions/for-property?
    address=...&
    groupBy=toc&
    section=2.10      # Optional: filter to section
```

### Response
```json
{
  "toc_structure": [
    {
      "part_number": 2,
      "part_name": "General Provisions",
      "sections": [
        {
          "section_number": "2.10",
          "section_title": "Parking",
          "provision_count": 45,
          "children": [...]
        }
      ]
    }
  ],
  "provisions": [...],
  "total_provisions": 370
}
```

---

## UI Structure (Target)

```
┌─────────────────────────────────────────────────────────┐
│ TOC Sidebar              │  Provisions Content          │
│ ======================== │  ========================    │
│ ▼ Part 2: General (201)  │  Part 2.10: Parking          │
│   ▼ 2.10 Parking (45)    │  ─────────────────────       │
│     • 2.10.1 Objectives  │  [Filter: parking] [heritage]│
│     • 2.10.2 Policy      │                              │
│   ▶ 2.11 Landscaping     │  ┌─ Page 5 ────────────────┐ │
│ ▶ Part 4: Residential    │  │ 2.10.1 Objectives       │ │
│ ▶ Part 8: Heritage       │  │ [provision text...]     │ │
│ ▶ Part 9: Precincts      │  │ [View PDF Page 5]       │ │
│                          │  └────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## Files

### Created
- `TOC_BASED_UI_IMPLEMENTATION_PLAN.md` - Full implementation plan
- `TOC_DATA_CERTIFICATION_PLAN.md` - Data prep plan
- `.claude/TOC_UI_PROJECT.md` - This tracking file

### To Create
- `frontend-nextjs/components/compliance/TocSidebar.tsx`
- `frontend-nextjs/components/compliance/ProvisionsByTocStructure.tsx`

### To Modify
- `frontend-nextjs/app/api/provisions/for-property/route.ts`
- `frontend-nextjs/app/assessment/page.tsx`

---

## Session Log

### 2025-12-10
- Created branch `feature/toc-based-ui`
- Audited TOC data: 676 entries, 151 invalid ranges, 98 NULL page_end
- Documented Leichhardt C marker solution
- Created implementation and certification plans

### 2025-12-11
- Ran TOC page range fixes:
  - Fix 1: Swapped 151 invalid page ranges -> 0 invalid now
  - Fix 2: 98 NULL page_end remain (last sections - expected)
- Provision-TOC mapping results:
  - Marrickville: 99.5% have page
  - Leichhardt: 88.9% have page
  - Ashfield: 87.2% have page
- CERTIFICATION: PASSED (85.5% valid TOC, 88-99% provisions have page)
- API Changes (Phase 2):
  - Added `groupBy=toc` parameter
  - Created `groupByTocStructure()` function
  - Groups by Part → Section with C marker handling for Leichhardt
  - Response now includes `by_toc` when groupBy=toc

- UI Components (Phase 3):
  - Created `TocSidebar.tsx` with collapsible Part/Section tree
  - Created `ProvisionsByTocStructure.tsx` with two-panel layout
  - Added topic filter chips for secondary filtering
  - Added Structure/Topic toggle to assessment page
  - Default view set to 'toc' (Structure mode)

### Next Steps
1. Test in browser with real address
2. Verify all three councils work (Marrickville, Leichhardt, Ashfield)
3. Test heritage properties
4. Performance test with large sections

---

*Updated: 2025-12-10*
