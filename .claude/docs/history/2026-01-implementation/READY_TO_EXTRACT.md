# Ready to Extract - Marrickville DCP Requirements

## Status: ALL PREPARATION COMPLETE ✅

### What's Done

1. ✅ **Deleted old incomplete data** (1,836 requirements + 1,311 incomplete provisions)
2. ✅ **Extracted 1,303 pages** from 82 Marrickville PDFs with PyMuPDF
3. ✅ **Created 1,150 page images** (PNG files for UI linking)
4. ✅ **Populated complete metadata:**
   - `page_number` - PDF page number
   - `pdf_page_image_url` - Path to page image (e.g., `/pdf-pages/marr_Marrickville_DCP_2011_-_2_1_Urban_Design_page_3.png`)
   - `provision_text` - Plain text (NO LaTeX)
   - `provision_type` - 'DCP_General'
   - `extraction_method` - 'PyMuPDF_complete_reextraction_2025_11_03'

5. ✅ **Created optimized extraction script** with high-quality prompt:
   - `extract_marrickville_OPTIMIZED.py`
   - Combines best elements from successful Ashfield/Leichhardt/Marrickville V2 extractions
   - Extracts structured requirements with:
     - Numeric values (value_numeric, value_min, value_max, unit)
     - Conditionals (has_conditionals, conditional_text)
     - Control codes (in extraction_context JSON)
     - Confidence scoring
     - Categories and subcategories
     - Mandatory vs recommended (in extraction_context JSON)

### What's Needed: ANTHROPIC_API_KEY

**Current Issue:** The script is looking for `ANTHROPIC_API_KEY` in environment variables but can't find it.

**Where to add it:**

**Option 1: Add to .env file (recommended)**
```bash
echo "ANTHROPIC_API_KEY=sk-ant-your-key-here" >> .env
```

**Option 2: Set as system environment variable**
```bash
# Windows Command Prompt
setx ANTHROPIC_API_KEY "sk-ant-your-key-here"

# PowerShell
[Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "sk-ant-your-key-here", "User")
```

**Option 3: Check if it's in a different env file**
```bash
# Check .env.local
cat .env.local

# Check .env.local.backup
cat .env.local.backup
```

### How to Run

Once API key is available:

```bash
python extract_marrickville_OPTIMIZED.py
```

**What it will do:**
- Process 1,303 provisions ONE PAGE AT A TIME
- Extract ~1,800-2,000 requirements with CORRECT page assignments
- Each requirement inherits page number from its source provision
- Estimated time: 2-3 hours

**Progress tracking:**
- Prints progress every 10 pages
- Commits to database every 10 pages
- Log saved to: `optimized_extraction.log`

### Expected Results

**Success criteria:**
- ~1,800-2,000 requirements extracted
- Each requirement has correct `pdf_page` matching actual PDF page
- No LaTeX formatting in `verbatim_source_text`
- Requirements grouped by actual page (not all on first page of section)
- Page 6 requirements show content from page 6 only

**Example fix:**
- OLD: Section 2.18 Landscaping (pages 6-10) → all 22 requirements assigned to page 10
- NEW: Page 6 → 3-5 requirements from page 6, Page 7 → 4-6 requirements from page 7, etc.

### Database State

**Current:**
```
regulatory_provisions:
  - PyMuPDF_complete_reextraction_2025_11_03: 1,303 provisions ✅
  - NULL (old data): 870 provisions (has duplicates) ⚠️

dcp_general_requirements:
  - Marrickville: 0 requirements (ready for extraction) ✅
```

**After extraction:**
```
dcp_general_requirements:
  - Marrickville: ~1,800-2,000 requirements
  - Each with correct pdf_page
  - Each linked to source provision via primary_source_provision_id
```

### Verification Steps

After extraction completes:

1. **Check total count:**
   ```bash
   python -c "import psycopg2; conn = psycopg2.connect(host='localhost', database='nsw_planning', user='postgres', password='postgres'); cur = conn.cursor(); cur.execute('SELECT COUNT(*) FROM dcp_general_requirements WHERE former_council = \\'Marrickville\\''); print(f'Total: {cur.fetchone()[0]}'); conn.close()"
   ```

2. **Check page grouping for 180 Addison Road:**
   - Should show landscaping requirements from MULTIPLE pages, not all from one page
   - Each requirement should have correct pdf_page

3. **Check for LaTeX formatting:**
   ```bash
   python -c "import psycopg2; conn = psycopg2.connect(host='localhost', database='nsw_planning', user='postgres', password='postgres'); cur = conn.cursor(); cur.execute('SELECT COUNT(*) FROM dcp_general_requirements WHERE former_council = \\'Marrickville\\' AND verbatim_source_text LIKE \\'%\\\\mathsf%\\''); print(f'LaTeX count: {cur.fetchone()[0]} (should be 0)'); conn.close()"
   ```

4. **Check pdf_page_image_url links work:**
   - Navigate to frontend in browser
   - Query 180 Addison Road
   - Click on requirement
   - Should show correct PDF page image

### Files Created This Session

**Extraction Scripts:**
- `extract_marrickville_complete_with_images.py` - ✅ Complete (extracted 1,303 pages)
- `extract_marrickville_OPTIMIZED.py` - ✅ Ready to run (needs API key)

**Documentation:**
- `MARRICKVILLE_REEXTRACTION_SESSION_SUMMARY.md` - Complete session details
- `READY_TO_EXTRACT.md` - This file

**Analysis/Audit:**
- `audit_marrickville_extraction.py` - Database state checker
- `compare_provisions.py` - Compare old vs new metadata
- `analyze_required_metadata.py` - Identify required fields

### High-Quality Prompt Features

The OPTIMIZED extraction script includes:

1. **Detailed JSON Schema** - Clear output structure with 15+ fields
2. **Numeric Extraction** - Captures values, min/max, units
3. **Conditional Detection** - Flags "except", "however", "unless", "where", "if"
4. **Control Code Tracking** - Extracts C1.1, C2.5, etc.
5. **Confidence Scoring** - High/medium/low based on clarity
6. **Category/Subcategory** - 2-level classification
7. **Mandatory Detection** - "must" vs "should"
8. **Verbatim Requirements** - EXACT text (no LaTeX, no paraphrasing)
9. **Examples in Prompt** - Shows good vs bad extraction
10. **Page Scope Enforcement** - Explicitly warns against cross-page inference

### Next Steps

1. **Locate/add ANTHROPIC_API_KEY**
2. **Run:** `python extract_marrickville_OPTIMIZED.py`
3. **Wait:** ~2-3 hours
4. **Verify:** Run verification steps above
5. **Test:** Check 180 Addison Road in UI

### Troubleshooting

**If extraction fails:**
- Check `optimized_extraction.log` for errors
- Common issues:
  - API rate limiting (script has no rate limiting - might need to add)
  - JSON parsing errors (script handles this gracefully)
  - Database connection issues (commits every 10 pages)

**If API key still not found:**
- Check: `cat .env | grep ANTHROPIC`
- Check: `echo $ANTHROPIC_API_KEY`
- Check: Windows Environment Variables GUI
- Last resort: Hard-code in script temporarily (NOT recommended for production)
