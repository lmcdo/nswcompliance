# Extraction vs Categorization: Time Comparison

## What You Did (30 minutes) - V2 Categorization

**Script**: `categorize_marrickville_provisions_v2.py`

**Process:**
1. Query existing data from `regulatory_provisions` (already in database)
2. Send text to GPT-4o-mini for categorization
3. Store results in `dcp_precinct_requirements`

**Time:**
- 51 Marrickville precincts × ~35 seconds each = ~30 minutes ✓

**Why it's fast:**
- No PDF parsing needed
- Just LLM API calls
- Data already extracted

---

## What I Estimated (8-10 hours) - PDF Re-extraction

**Script**: `scripts/complete_dcp_extraction_pdfplumber.py`

**Process:**
1. Open each PDF with pdfplumber
2. Extract text page by page
3. Split into sections based on headings
4. Store in `regulatory_provisions`
5. THEN run V2 categorization (another 30 mins)

**Why I thought it was slow:**
- PDF parsing is I/O heavy
- Text extraction can be slow
- Had to process multiple DCP PDFs

**But looking at the script:**
- It's automated!
- Already exists!
- Probably only takes 30-60 minutes too!

---

## The Real Issue: Current Script Logic

**Line 66-82 in `complete_dcp_extraction_pdfplumber.py`:**

```python
# Look for section headings (like "4.1.5 Streetscape and design")
section_match = re.search(r'^(\d+(?:\.\d+)*)\s+([A-Z][^\n]+)$', text, re.MULTILINE)

if section_match:
    # Save previous section
    if current_section:
        current_section['page_end'] = page_num - 1
        sections.append(current_section)

    # Start new section
    current_section = {
        'section_number': section_match.group(1),
        'section_title': section_match.group(2).strip(),
        'content': '',
        'tables': [],
        'page_start': page_num,   # <-- ONLY STORES START PAGE
        'page_end': page_num
    }

# Add content to current section
if current_section:
    current_section['content'] += f"\n\n{text}"  # <-- ACCUMULATES ACROSS PAGES
```

**Line 282 - Database insertion:**
```python
cursor.execute("""
    INSERT INTO regulatory_provisions (
        ...
        pdf_page,
        ...
    ) VALUES (%s, %s, %s, %s, %s, %s)
""", (
    ...
    section['page_start'],  # <-- ONLY START PAGE STORED
    ...
))
```

**Result:**
- Section "9.10.1 Existing character" starts on page 5
- But spans pages 5, 6, 7
- Database only stores: `pdf_page = 5`
- Setback text is on page 7, but we show page 5!

---

## Solution: Modify Extraction Script

### Option A: Store Page Ranges (Easy - 30 mins to code, 30 mins to run)

**Change line 66-82 to track page range:**

```python
# Instead of just page_start, track all pages
if current_section:
    current_section['content'] += f"\n\n{text}"
    current_section['pages'].append(page_num)  # Track every page
```

**Change database schema:**

```sql
ALTER TABLE regulatory_provisions ADD COLUMN page_range int[];
```

**Then when LLM extracts verbatim text:**
- Search provision text for verbatim position
- Calculate: `actual_page = pages[int(position / (len(text) / len(pages)))]`
- Store actual page, not start page

**Total time: 1 hour (30 mins coding + 30 mins running)**

---

### Option B: Extract Page-by-Page (Harder - 1 hour to code, 30 mins to run)

**Change line 66-82 to split by page instead of section:**

```python
# Don't accumulate across pages
# Each page = one provision with page-specific ID

for page_num, page in enumerate(pdf.pages, start=1):
    text = page.extract_text() or ""

    # Store this page immediately
    sections.append({
        'section_number': f'{current_section_num}_page_{page_num}',
        'section_title': current_section_title,
        'content': text,  # Only this page's text
        'page_start': page_num,
        'page_end': page_num
    })
```

**Result:**
- 10x more database records (one per page instead of per section)
- Always accurate page numbers
- LLM has to categorize more provisions

**Total time: 1.5 hours (1 hour coding + 30 mins running)**

---

## My Revised Recommendation

**Go with Option A: Store Page Ranges**

**Why:**
- Minimal code changes
- Doesn't bloat database
- Uses same extraction logic
- Just adds page tracking

**Implementation:**
1. Modify `complete_dcp_extraction_pdfplumber.py` (30 mins)
2. Add `page_range` column to `regulatory_provisions` (5 mins)
3. Re-run extraction for Marrickville DCP only (30 mins)
4. Update V2 categorization to calculate correct page (15 mins)
5. Test with Precinct 10_ (10 mins)

**Total: ~90 minutes (not 8-10 hours!)**

I apologize for the bad initial estimate. I hadn't reviewed the extraction script yet.

---

**Want me to implement Option A now?**
