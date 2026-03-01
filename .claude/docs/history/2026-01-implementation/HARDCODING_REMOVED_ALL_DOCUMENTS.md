# Hardcoding Removed: Dynamic Document Loading

**Date:** 2025-10-14
**Issue:** DCPSelector had 5 hardcoded documents
**Solution:** Dynamic API endpoint serving all 110 DCP documents

---

## What Was Fixed

### Before (Hardcoded):
```typescript
const documents = [
  { id: 'Marrickville_DCP_2011__2_10_Parking', label: '2.10 Parking' },
  { id: 'Marrickville_DCP_2011__4.1_Low_Density...', label: '4.1 Low Density' },
  // Only 5 documents total
];
```

### After (Dynamic):
```typescript
useEffect(() => {
  fetch('/api/browse/documents')
    .then(data => setDocuments(data.documents));
}, []);
// Returns all 110 documents from database
```

---

## Database Coverage

**Total DCP Documents: 110**

| LGA | Documents | With TOC | Without TOC |
|-----|-----------|----------|-------------|
| **Marrickville** | 82 | 42 | 40 |
| **Ashfield** | 9 | 0 | 9 |
| **Leichhardt** | 19 | 0 | 19 |
| **TOTAL** | **110** | **42** | **68** |

---

## Implementation

### 1. New API Endpoint: `/api/browse/documents`

**File:** `frontend-nextjs/app/api/browse/documents/route.ts`

**Query:**
```sql
SELECT
  p.document_id,
  EXISTS(SELECT 1 FROM dcp_table_of_contents t
         WHERE t.document_id = p.document_id) as has_toc,
  COUNT(p.id) as provision_count
FROM regulatory_provisions p
WHERE p.document_id LIKE '%Marrickville_DCP%'
   OR p.document_id LIKE '%Ashfield_DCP%'
   OR p.document_id LIKE '%Leichhardt_DCP%'
GROUP BY p.document_id
ORDER BY p.document_id
```

**Response:**
```json
{
  "success": true,
  "data": {
    "documents": [
      {
        "documentId": "Marrickville_DCP_2011__2_10_Parking",
        "label": "2.10 Parking",
        "hasTOC": true,
        "provisionCount": 123,
        "partNumber": "Part 2"
      },
      // ... 109 more
    ],
    "grouped": {
      "Part 2": [...],
      "Part 4": [...],
      "Part 5": [...]
    },
    "totalDocuments": 110,
    "withTOC": 42,
    "withoutTOC": 68
  }
}
```

---

### 2. Updated DCPSelector Component

**Changes:**
- ✅ Fetches documents from API on mount
- ✅ Shows loading spinner during fetch
- ✅ Shows error state with retry button
- ✅ Groups documents by Part number
- ✅ Shows "No TOC" badge for documents without TOC
- ✅ Shows provision counts
- ✅ Sticky part headers in dropdown

**New Features:**

**Loading State:**
```
[🔄] Loading documents...
```

**Grouped Dropdown:**
```
┌─ Part 2 (15 sections) ────────────────┐
│ 2.10 Parking              [123 prov]  │
│ 2.11 Fencing              [45 prov]   │
├─ Part 4 (20 sections) ────────────────┤
│ 4.1 Low Density           [No TOC] 89 │
│ 4.2 Multi-Dwelling        [234 prov]  │
├─ Part 9 (40 sections) ────────────────┤
│ 9.1 Tempe Lands           [No TOC] 12 │
└────────────────────────────────────────┘
110 total documents • 42 with TOC
```

**Selected Document with No TOC:**
```
[4.1 Low Density Residential] [No TOC] ▼
```

---

### 3. Enhanced TOCTree Component

**Handles documents without TOC:**

```
┌─────────────────────────────────────┐
│  📄  No Table of Contents           │
│                                     │
│  This document doesn't have an      │
│  extracted TOC, but you can still   │
│  browse all provisions.             │
│                                     │
│  All provisions from this section   │
│  will be displayed without          │
│  subsection navigation.             │
└─────────────────────────────────────┘
```

**Before:** Red error for missing TOC
**After:** Amber informational message

---

## Why 68 Documents Have No TOC?

### Phase 0 Extraction Limitations:

**What happened:**
- Phase 0 script (`extract_dcp_toc.py`) extracted TOC from `content_list.json` files
- Only looked for text blocks with patterns like "2.10 Parking...... 5"
- If PDF didn't have a traditional TOC page, extraction failed

**Examples of documents without TOC:**
1. **Precinct Plans** (Part 9) - Often just maps/diagrams, no formal TOC
2. **Ashfield/Leichhardt** - Different PDF structure, TOC not detected
3. **Heritage sections** - Short documents without formal TOC
4. **Amendment documents** - Update existing sections, no standalone TOC

**Can we extract TOC for the 68?**
- Possibly, but would require:
  - Different extraction strategy per document type
  - Manual TOC creation for precinct plans
  - Parsing section headers from provision text
- **Not worth it** - provisions still browsable without TOC

---

## User Experience

### Documents WITH TOC (42 documents):
```
1. Select "2.10 Parking" from dropdown
2. TOC tree loads with 5 subsections
3. Click "2.10.2 Policy approach"
4. View 44 provisions for that subsection
```

### Documents WITHOUT TOC (68 documents):
```
1. Select "9.1 Tempe Lands Precinct" [No TOC badge shown]
2. Left panel shows amber message: "No TOC available"
3. Right panel shows ALL 12 provisions for entire document
4. User can still filter/search provisions
```

**Both workflows are valid and useful!**

---

## Testing Verification

### API Endpoint Test:
```bash
curl http://localhost:3007/api/browse/documents

# Expected response time: ~50-100ms
# Returns 110 documents
# 42 with hasTOC: true
# 68 with hasTOC: false
```

### UI Test Cases:
- [x] Dropdown shows loading state on mount
- [x] All 110 documents appear in dropdown
- [x] Documents grouped by Part number
- [x] "No TOC" badge shows for 68 documents
- [x] Provision counts display correctly
- [x] Selecting document with TOC → shows TOC tree
- [x] Selecting document without TOC → shows amber message
- [x] Error handling works (network failure)

---

## Database Query Performance

**Query:** Returns all documents with TOC status
**Execution time:** ~60ms
**Rows returned:** 110
**Indexes used:**
- `regulatory_provisions(document_id)` - for GROUP BY
- `dcp_table_of_contents(document_id)` - for EXISTS check

**Acceptable:** Only runs once on page load

---

## Future Enhancements

### Option 1: Fallback TOC Generation
For documents without extracted TOC:
- Parse section headers from provision text
- Build dynamic TOC based on header hierarchy
- Effort: 2-3 days

### Option 2: Manual TOC Entry
For critical documents (Part 9 precincts):
- Create `manual_toc` table
- Council staff can add section structure
- Effort: 1 day + ongoing data entry

### Option 3: Hybrid View
Documents without TOC show:
- "Browse by page number" instead of subsections
- Page 1-5, Page 6-10, etc.
- Effort: 1 day

**Decision:** Not needed for MVP. Current solution is sufficient.

---

## Files Modified

1. **Created:** `frontend-nextjs/app/api/browse/documents/route.ts` (130 lines)
2. **Modified:** `frontend-nextjs/components/browse/DCPSelector.tsx` (+100 lines)
3. **Modified:** `frontend-nextjs/components/browse/TOCTree.tsx` (+30 lines)

---

## Summary

**Before:**
- 5 hardcoded documents
- Only Marrickville parking and residential sections
- No visibility into other 105 documents

**After:**
- 110 dynamic documents from API
- All Inner West LGAs (Marrickville, Ashfield, Leichhardt)
- Clear indication of TOC availability
- Graceful handling of documents without TOC
- Grouped by Part number for easy navigation

**Result:** Professional, scalable, data-driven document selector ✅

---

**Status:** Hardcoding removed - All documents now loaded dynamically
**Impact:** Users can browse ALL DCP sections, not just the 5 hardcoded ones
**Next:** User testing with documents that have no TOC
