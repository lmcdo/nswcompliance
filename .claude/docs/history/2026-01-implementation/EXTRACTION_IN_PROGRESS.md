# Marrickville DCP Extraction - IN PROGRESS

## Current Status: RUNNING ✅

**Script:** `extract_marrickville_CATEGORIZED.py`
**Started:** 2025-11-03
**Est. Completion:** 2-3 hours

### What's Running

The extraction is processing **1,303 Marrickville DCP pages** with proper categorization:

**General Requirements (851 pages → `dcp_general_requirements`):**
- Part 1: Statutory Information
- Part 2.X: Urban Design, Parking, Landscaping, Heritage, Environmental, etc.
- Part 3: Subdivision
- Part 4: Residential Development
- Part 5: Commercial Development
- Part 6: Industrial Development
- Part 7: Special Uses
- Part 8: Heritage
- Part 10: Definitions

**Precinct Requirements (452 pages → `dcp_precinct_requirements`):**
- Part 9.1-9.48: Geographic precincts (Lewisham North, Dulwich Hill, Marrickville Town Centre, etc.)

### Key Features

1. **Page-by-Page Processing** - Fixes original bug where all requirements from multi-page sections got assigned to first page
2. **Proper Table Routing** - General vs Precinct requirements go to correct tables
3. **Complete Metadata** - pdf_page, pdf_page_image_url, verbatim_source_text, categories
4. **Structured Extraction** - Numeric values, conditionals, control codes, confidence scores

### Monitoring Progress

**Check requirements count:**
```bash
python -c "import psycopg2; conn = psycopg2.connect(host='localhost', database='nsw_planning', user='postgres', password='postgres'); cur = conn.cursor(); cur.execute('SELECT COUNT(*) FROM dcp_general_requirements WHERE former_council = \\'Marrickville\\''); general = cur.fetchone()[0]; cur.execute('SELECT COUNT(*) FROM dcp_precinct_requirements WHERE former_council = \\'Marrickville\\''); precinct = cur.fetchone()[0]; print(f'General: {general}, Precinct: {precinct}, Total: {general+precinct}'); conn.close()"
```

**Watch log:**
```bash
tail -f categorized_extraction.log
```

### Expected Results

**General Requirements:** ~1,200-1,500 requirements
- Apply to ALL properties in Inner West (former Marrickville)
- Used for baseline compliance checks
- Examples: Minimum parking, setbacks, landscaping percentages

**Precinct Requirements:** ~600-900 requirements
- Apply ONLY to properties within specific geographic boundaries
- Require spatial matching (point-in-polygon)
- Examples: Character controls, height limits for specific areas

**Total:** ~1,800-2,400 requirements

### Next Steps After Completion

1. **Verify counts** match expectations
2. **Test spatial matching** for precinct requirements
3. **Verify page grouping** - Check that 180 Addison Road shows requirements from correct pages
4. **Test UI integration** - Both general and precinct requirements appear correctly
5. **Remove duplicates** from old regulatory_provisions data (870 provisions)

### Architecture

```
regulatory_provisions (1,303 pages)
    ├─> General (851 pages)
    │   └─> LLM Extraction
    │       └─> dcp_general_requirements (~1,200-1,500 reqs)
    │
    └─> Precinct (452 pages)
        └─> LLM Extraction
            └─> dcp_precinct_requirements (~600-900 reqs)
```

### Files

- `extract_marrickville_CATEGORIZED.py` - Main extraction script ✅
- `categorized_extraction.log` - Live progress log
- `analyze_general_vs_precinct.py` - Document classification analysis
- `EXTRACTION_IN_PROGRESS.md` - This file

### Troubleshooting

**If extraction stops:**
- Check log for errors: `tail -100 categorized_extraction.log`
- Check database: Scripts commit every 10 pages, so partial data is safe
- Restart: `python extract_marrickville_CATEGORIZED.py`

**If JSON parsing errors:**
- Script handles gracefully, counts as failed page
- Continues with next page
- Review at end to see failure rate

**If API rate limiting:**
- OpenAI GPT-4o-mini has high rate limits
- Script doesn't have rate limiting built in (should add if needed)
- May need to add sleep(0.5) between calls if hitting limits
