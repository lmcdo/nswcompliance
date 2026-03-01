# TODO: Add PDF Page Links to General DCP Provisions

**Date Created:** 2025-10-28
**Status:** 🔴 NOT STARTED - Needs fresh session
**Estimated Time:** 4-6 hours
**Priority:** HIGH (blocking full UX completeness)

---

## The Problem

Our newly implemented GeneralDCPSection component displays DCP requirements extracted by LLM, but has NO "View PDF" buttons like the old system had.

### Current State
- ✅ 130 general provisions extracted and displayed
- ❌ 0 have pdf_page numbers
- ❌ 0 have pdf_page_image_url links
- ❌ Users cannot verify source text in PDF

### What Users See Now
```
🌳 Landscaping
2 requirements

General Controls
landscaping
High Confidence
Minimum planting area: 3m along boundaries with residential zones
```

### What Users SHOULD See
```
🌳 Landscaping
2 requirements

General Controls
landscaping
High Confidence
Minimum planting area: 3m along boundaries with residential zones
[View PDF Page 47] ← MISSING!
```

---

## The Solution: Re-extract with PDF Tracking

We need to re-extract provisions FROM THE ORIGINAL PDFs (not markdown) and track:
1. `pdf_path` - Path to source PDF
2. `pdf_page` - Page number in PDF where provision appears
3. `pdf_page_image_url` - URL to rendered PDF page image

### Affected Tables
```sql
-- These tables need PDF metadata added:
dcp_general_provisions (130 records)
dcp_precinct_provisions (still using old system with PDF links)
```

---

## Implementation Steps

### Phase 1: Locate Source PDFs (30 min)
```bash
# Find the PDFs we extracted from
find . -name "*Ashfield*.pdf"
find . -name "*Marrickville*.pdf"
find . -name "*Leichhardt*.pdf"

# Key PDFs needed:
- Ashfield DCP 2017 Chapter F (General Controls)
- Marrickville DCP 2009 Part 4.1 (Low Density)
- Marrickville DCP 2009 Part 4.2 (Medium Density)
- Leichhardt DCP 2013 Part C.1 (General Controls)
```

### Phase 2: Create PDF Extraction Script (2 hours)
```python
# extract_general_provisions_with_pdf_tracking.py

import fitz  # PyMuPDF
from pathlib import Path
import json

def extract_provision_with_page(pdf_path, section_name):
    """
    Extract provisions and track which PDF page they came from

    Returns:
        {
            "provision_id": "...",
            "text": "...",
            "pdf_path": "docs/...",
            "pdf_page": 47,
            "ref_number": "4.1.2"
        }
    """
    pass

# Process each LGA:
# 1. Ashfield: Chapter F (65 provisions)
# 2. Marrickville: Part 4.1 + 4.2 (27 provisions)
# 3. Leichhardt: Part C.1 (38 provisions)
```

### Phase 3: Generate PDF Page Images (1.5 hours)
```python
# generate_pdf_page_images.py

def render_pdf_page_to_image(pdf_path, page_num, output_dir):
    """
    Render PDF page to PNG image for quick preview

    Output: frontend-nextjs/public/pdf-pages/{doc_id}_page_{num}.png
    Returns: /pdf-pages/{doc_id}_page_{num}.png
    """
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    pix = page.get_pixmap(dpi=150)
    pix.save(f"{output_dir}/{doc_id}_page_{page_num}.png")
    return f"/pdf-pages/{doc_id}_page_{page_num}.png"
```

### Phase 4: Update Database (30 min)
```sql
-- Add PDF metadata to existing provisions
UPDATE dcp_general_provisions
SET
    pdf_page = %(page_num)s,
    pdf_page_image_url = %(image_url)s
WHERE provision_id = %(provision_id)s;
```

### Phase 5: Update Frontend Component (1 hour)
```typescript
// frontend-nextjs/components/compliance/GeneralDCPSection.tsx

// Add PDF viewing to each requirement:
{requirement.pdf_page_image_url && (
  <Button
    size="sm"
    variant="outline"
    onClick={() => setViewingPdf(requirement.pdf_page_image_url)}
  >
    <FileText className="h-4 w-4 mr-1" />
    View PDF Page {requirement.pdf_page}
  </Button>
)}

// Add modal for PDF viewing
<PdfViewerModal
  imageUrl={viewingPdf}
  onClose={() => setViewingPdf(null)}
/>
```

### Phase 6: Update API to Return PDF Fields (15 min)
```typescript
// frontend-nextjs/app/api/compliance/dcp-complete/route.ts

// Add to SELECT query:
SELECT
  dgp.provision_id,
  dgp.category,
  dgp.subcategory,
  dgp.text,
  dgp.pdf_path,          -- ADD
  dgp.pdf_page,          -- ADD
  dgp.pdf_page_image_url -- ADD
FROM dcp_general_provisions dgp
```

---

## Testing Checklist

### Database Verification
```sql
-- Check PDF metadata was added
SELECT
    lga,
    COUNT(*) as total,
    COUNT(pdf_page) as with_page,
    COUNT(pdf_page_image_url) as with_image
FROM dcp_general_provisions
GROUP BY lga;

-- Should see:
-- Ashfield:     65 total, 65 with_page, 65 with_image
-- Marrickville: 27 total, 27 with_page, 27 with_image
-- Leichhardt:   38 total, 38 with_page, 38 with_image
```

### UI Testing
1. Navigate to http://localhost:3007/assessment
2. Enter "123 Smith St, Ashfield" + "dwelling_house"
3. Verify:
   - ✅ General Controls section shows
   - ✅ Each requirement has "View PDF Page X" button
   - ✅ Clicking button opens PDF page modal
   - ✅ PDF page image loads correctly
4. Repeat for Marrickville and Leichhardt addresses

---

## Files to Reference

### Existing PDF Extraction Scripts
```bash
# These scripts already extract from PDFs:
scripts/extract_dcp_toc.py
scripts/complete_dcp_extraction_pdfplumber.py
extract_ashfield_chapter_f.py
```

### Database Schema
```sql
-- Check current schema:
\d dcp_general_provisions

-- Columns we're adding:
pdf_page: integer
pdf_page_image_url: text
```

### Frontend Reference (OLD system with PDF buttons)
```
frontend-nextjs/components/compliance/DCPProvisionsBrowser.tsx
  - Lines 200-220: View PDF button implementation
  - Lines 450-500: PDF viewer modal
```

---

## Expected Outcomes

### Before (Current)
- User sees: "Minimum planting area: 3m..."
- User cannot verify source
- User cannot see full context

### After (With PDF Links)
- User sees: "Minimum planting area: 3m... [View PDF Page 47]"
- Clicking button → Opens PDF page 47 showing original provision
- User can verify LLM extraction accuracy
- User can see full diagrams/tables on that page

---

## Acceptance Criteria

- [ ] All 130 general provisions have pdf_page numbers
- [ ] All 130 general provisions have pdf_page_image_url links
- [ ] PDF page images render correctly in frontend
- [ ] Clicking "View PDF" button opens correct page
- [ ] PDF images are clear and readable (150 DPI minimum)
- [ ] All 3 LGAs tested (Ashfield, Marrickville, Leichhardt)

---

## Notes for Fresh Session

**READ THESE FIRST:**
1. `UNIFIED_DCP_DISPLAY_IMPLEMENTATION_COMPLETE.md` - What we just built
2. `CLAUDE.md` - Database safety rules
3. This file - What needs to be done next

**START HERE:**
```bash
# 1. Find source PDFs
find docs/ -name "*Ashfield*Chapter*F*.pdf"
find docs/ -name "*Marrickville*Part*4*.pdf"
find docs/ -name "*Leichhardt*Part*C*.pdf"

# 2. Check existing extraction scripts for reference
cat extract_ashfield_chapter_f.py
cat scripts/complete_dcp_extraction_pdfplumber.py

# 3. Create backup before any changes
python create_backup.py "before_pdf_extraction"
```

**AVOID THESE MISTAKES:**
- ❌ DON'T extract from markdown files (no page numbers!)
- ❌ DON'T guess page numbers
- ❌ DON'T skip database backup
- ✅ DO extract directly from PDFs
- ✅ DO track page numbers as you extract
- ✅ DO test on all 3 LGAs

---

## Related Documents
- `UNIFIED_DCP_DISPLAY_IMPLEMENTATION_COMPLETE.md` - What we built today
- `frontend-nextjs/components/compliance/GeneralDCPSection.tsx` - Component needing PDF buttons
- `frontend-nextjs/app/api/compliance/dcp-complete/route.ts` - API needing PDF fields
- `DATABASE_QUICK_REFERENCE.md` - Database schema reference

---

**STATUS: 🔴 Ready for fresh session with full context budget**
