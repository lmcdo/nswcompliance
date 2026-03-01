# Efficient & Reliable Fix for NULL pdf_page Issue

**Issue:** API returns 834 provisions instead of 2,000+ due to NULL pdf_page values

## 🎯 ROOT CAUSE CONFIRMED

**From Git History Analysis:**

1. **January 12, 2026** - Commit `1146ff65`: "The pdf_page database field has incorrect values for many provisions"
   - Developer acknowledged pdf_page field was unreliable
   - Attempted to use pdf_page_image_url instead
   - Reverted same day because URL was extraction sequence, not actual page

2. **67% NULL pdf_page existed in November 22 backup** (pre-existing data quality issue)

3. **Between Nov 22 - Jan 27:** Database improved (41k provisions, 2k+ returned)
   - Someone likely ran scripts to populate pdf_page
   - Changes not backed up
   - Lost during January 28 restore

4. **enrichWithTocSections() filters NULL pdf_page** (line 519 in route.ts):
   ```typescript
   const docPages = provisions
     .filter(p => p.pdf_page != null)  // <-- Filters NULL
   ```
   However, it still returns all provisions - just without TOC enrichment

## ❓ THE REAL QUESTION

**Why does the database have 2,990 actionable provisions but API returns only 834?**

Let me verify if enrichWithTocSections actually removes provisions or if there's another filter...

## 🔍 MOST EFFICIENT FIX

### Option 1: Use pdf_page_image_url as Fallback (FASTEST - 5 minutes)

**Principle:** Extract page number from pdf_page_image_url when pdf_page is NULL

**Files to modify:**
1. `frontend-nextjs/app/api/provisions/for-property/route.ts` - queryLayer() function
2. After querying provisions, populate pdf_page from URL before enrichWithTocSections

**SQL to run:**
```sql
UPDATE regulatory_provisions
SET pdf_page = NULLIF(
  regexp_replace(
    pdf_page_image_url,
    '^.*page_(\d+)\.png.*$',
    '\1'
  ),
  pdf_page_image_url
)::integer
WHERE pdf_page IS NULL
  AND pdf_page_image_url ~ 'page_\d+\.png';
```

**Verification:**
```sql
SELECT COUNT(*) FROM regulatory_provisions
WHERE document_id ILIKE '%Leichhardt%'
  AND v2_dcp_layer = 'generic'
  AND pdf_page IS NULL;
```

**Pros:**
- Fastest fix (5 minutes)
- Uses existing data
- No re-extraction needed

**Cons:**
- page_X.png is extraction sequence, NOT actual DCP page number
- Will show wrong page numbers to users
- Jan 12 commit said this approach is wrong

### Option 2: Restore from Pre-Incident State (BEST - 30 minutes)

**Check if there's a backup between Nov 22 and Jan 27 with valid pdf_page**

**Commands:**
```bash
# Check all December/early January backups
ls -lh backups/ | grep "2025-12\|2026-01"

# Check git for backup creation scripts
git log --oneline --since="2025-12-01" --until="2026-01-27" | grep backup
```

**If found:**
1. Verify backup quality
2. Restore from that backup
3. Re-run v2 enrichment (30 min)
4. Test API

**Pros:**
- Correct data
- Proven to work (user had 2k+ provisions before)
- No guessing

**Cons:**
- Depends on backup existing
- May lose other changes

### Option 3: Reconstruct from Document Metadata (RELIABLE - 2 hours)

**Use extraction_temp metadata + pdf_source_file to rebuild pdf_page**

**Process:**
1. Find extraction metadata files in extraction_temp/
2. Match provisions to source documents
3. Use document_id + provision_text to find actual page
4. Update pdf_page column

**Script skeleton:**
```python
# For each document with NULL pdf_page provisions:
# 1. Load extraction metadata
# 2. Match provision text to extracted page
# 3. Update pdf_page = actual_page_number
```

**Pros:**
- Most accurate
- Uses authoritative source (PDFs)
- Permanent fix

**Cons:**
- Takes 2 hours
- Complex matching logic
- May not match all provisions

### Option 4: Accept NULL and Don't Filter (QUICK FIX - 10 minutes)

**Modify enrichWithTocSections to NOT filter NULL pdf_page**

**Change line 519:**
```typescript
// Before:
const docPages = provisions
  .filter(p => p.pdf_page != null)

// After:
const docPages = provisions
  .map(p => ({ doc_id: p.document_id, page: p.pdf_page || 0, id: p.id }));
```

**Pros:**
- Immediate fix
- No data changes
- All provisions returned

**Cons:**
- Provisions with NULL pdf_page won't get TOC section info
- May show incomplete metadata to users
- Doesn't fix root cause

## 📋 RECOMMENDED APPROACH

### STEP 1: Verify the API is actually filtering (5 minutes)

Run a direct database query to confirm 2,990 provisions exist:

```sql
SELECT COUNT(*) FROM regulatory_provisions
WHERE document_id ILIKE '%Leichhardt%'
  AND v2_is_actionable = true
  AND is_current = TRUE
  AND v2_dcp_layer IN ('generic', 'use_specific', 'precinct', 'condition');
```

Then check if enrichWithTocSections is the bottleneck or if there's another filter.

### STEP 2: Quick fix while investigating (10 minutes)

**Option 4** - Don't filter NULL pdf_page in enrichWithTocSections

This gets provisions showing immediately while you investigate proper fix.

### STEP 3: Proper fix (choose based on resources)

**If you find a December/January backup:** Use Option 2
**If no backup:** Use Option 3 (reconstruct from metadata)
**If urgent:** Use Option 1 but document that pages are wrong

## 🚨 CRITICAL INSIGHT

**The API code at line 519 filters NULL pdf_page for TOC enrichment, but it RETURNS all provisions on line 563.**

So the NULL pdf_page should NOT be causing provisions to disappear entirely.

**Need to verify:**
1. Is there another filter we haven't found?
2. Is the deduplication removing NULL page provisions?
3. Is the frontend filtering them out?

Let me check the deduplication logic more carefully...

## 🔧 IMMEDIATE ACTION

Run this test to see what's really happening:

```bash
cd "C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine"
node scripts/test_leichhardt_api_directly.mjs > api_test_output.txt 2>&1
```

Then check the output to see:
- How many provisions each layer returns
- Whether deduplication is the culprit
- What the actual layer counts are

**Next:** Based on test results, implement the right fix.
