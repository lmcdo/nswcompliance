# Ashfield Chapter F Extraction - IN PROGRESS
**Date:** 2025-11-03 21:23
**Status:** LLM extraction running in background

---

## What's Happening Right Now

**Process ID:** d5490b
**Script:** `extract_ashfield_chapter_f_requirements.py`
**Processing:** 73 Chapter F pages
**Estimated time:** 15-20 minutes (73 pages at ~10-15 seconds per page)

### Progress Monitoring

**Check current count:**
```bash
python -c "import psycopg2, os; from dotenv import load_dotenv; load_dotenv(); conn = psycopg2.connect(host=os.getenv('DB_HOST'), database=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD')); cur = conn.cursor(); cur.execute('''SELECT COUNT(*) FROM dcp_general_requirements WHERE former_council=%s AND primary_source_provision_id IN (SELECT id FROM regulatory_provisions WHERE extraction_method=%s)''', ['Ashfield', 'PyMuPDF_ashfield_chapter_f_2025_11_03']); count = cur.fetchone()[0]; print(f'Chapter F requirements: {count}'); conn.close()"
```

**Watch background process:**
```bash
# View latest output
BashOutput d5490b
```

---

## What's Been Completed So Far

### Phase 1: PDF Page Extraction ✅ (Completed 21:20)
- **Extracted:** 73 pages from Chapter F PDF
- **Created:** 73 page images (PNG files)
- **Stored:** `regulatory_provisions` table with complete metadata
- **Method:** PyMuPDF (same as Marrickville)
- **Result:** Ready for LLM extraction

### Phase 2: LLM Extraction 🔄 (In Progress 21:22)
- **Started:** 21:22
- **Pages:** 0/73 processed so far
- **Model:** OpenAI GPT-4o-mini
- **Batch size:** 10 pages at a time
- **Commits:** Every 10 pages
- **Rate limiting:** 0.5 second delay between pages

**What it's extracting:**
- DS/PC codes (Design Standards / Performance Criteria)
- Requirements text (clean summary + verbatim)
- Categories (31 semantic categories same as Marrickville)
- **Zones** from tables → `applicable_zones[]`
- **DevTypes** from Part numbers → `development_types[]`
- Evidence type (measurable/calculable/assessable/reportable)
- PDF metadata (page, image URL)

---

## Expected Results

### After Extraction Completes:

**Chapter F Requirements:**
- ~200-500 requirements (estimate based on 73 pages)
- Each with zones and development types populated
- Each classified by evidence type
- Each linked to PDF page with image

**Total Ashfield Requirements:**
```
Current (Chapters A, B, C, E1):  586 requirements
+ Chapter F (new):              ~200-500 requirements
= Total:                        ~786-1,086 requirements
```

**Zone Filtering:**
- Query: R2 zone + dwelling_house
- Will return: Part F.1 requirements for R2 zone
- Expected: ~30-60 requirements (highly targeted)

**Evidence Type Distribution (Chapter F only):**
```
Expected:
  measurable:  40-50% (high - lots of setbacks, heights, parking)
  calculable:   5-10% (FSR, site coverage)
  assessable:  30-40% (design quality, character)
  reportable:  10-15% (high - SEPP 65, BASIX, ADG)
```

---

## What Happens Next

### Phase 3: Evidence Type Classification ⏳ (5 minutes)
After extraction completes, run:
```bash
python tag_evidence_types_ashfield_chapter_f.py
```

This will re-classify all Chapter F requirements to ensure accuracy.

### Phase 4: Verification ⏳ (30 minutes)
Test zone + devtype filtering:
```bash
python verify_ashfield_zone_filtering.py
python test_180_addison_road_ashfield.py
```

---

## Comparison: Ashfield vs Marrickville

### Similarities:
1. ✅ Page-by-page extraction (fixes page grouping bug)
2. ✅ 31 semantic categories
3. ✅ Evidence type classification
4. ✅ Complete PDF metadata
5. ✅ OpenAI GPT-4o-mini model

### Differences (Ashfield-specific):
1. 🆕 **Zone extraction** → `applicable_zones[]` (R1, R2, R3...)
2. 🆕 **DevType inference** → `development_types[]` (dwelling_house, RFB...)
3. 🔄 DS/PC codes instead of C/O codes
4. 🔄 Higher SEPP 65 references (20% vs 5%)

### Critical Innovation:
**Ashfield has zone + devtype arrays** = Enables highly targeted filtering
**Marrickville doesn't** = Uses neighbourhood boundaries only

---

## Troubleshooting

### If extraction seems stuck:
```bash
# Check if process is still running
BashOutput d5490b

# Check database for latest count
# (count should increase every ~2-3 minutes)
```

### If extraction fails:
- Check last error in BashOutput
- Common issues:
  - JSON parsing errors (script handles gracefully, continues)
  - API rate limiting (0.5s delay should prevent this)
  - Database connection (commits every 10 pages)

### If you need to stop and restart:
```bash
# Kill background process
KillShell d5490b

# Re-run extraction (safe - inserts are idempotent)
python extract_ashfield_chapter_f_requirements.py
```

---

## Timeline

**Started:**
- 20:48 - Evidence type tagged for existing 586 Ashfield requirements
- 21:20 - PDF pages extracted (73 pages)
- 21:22 - LLM extraction started

**Estimated completion:**
- 21:37 - LLM extraction completes (~15 min)
- 21:42 - Evidence type classification (~5 min)
- 22:12 - Verification and testing (~30 min)

**Total:** ~1.5 hours from start to verified completion

---

## Success Criteria

When complete, Ashfield will have:
- [x] Chapters A, B, C, E1 extracted (586 reqs) ✅
- [ ] Chapter F extracted (~200-500 reqs) 🔄
- [ ] Evidence type classified for all
- [ ] Zone filtering working (R2, B1, etc.)
- [ ] DevType filtering working (dwelling_house, RFB, etc.)
- [ ] Page grouping verified (requirements on correct pages)
- [ ] Same 31 categories as Marrickville

**Then:** Ashfield = COMPLETE and production-ready!

---

## Files Created This Session

1. `extract_ashfield_chapter_f_pages.py` - PDF extraction ✅
2. `extract_ashfield_chapter_f_requirements.py` - LLM extraction 🔄
3. `ASHFIELD_COMPLETE_REEXTRACTION_PLAN.md` - Full plan ✅
4. `ASHFIELD_EXTRACTION_EXECUTION_PLAN.md` - Execution details ✅
5. `ASHFIELD_EXTRACTION_IN_PROGRESS.md` - This file ✅

---

## Next Session Handoff

If continuing in next session:

1. **Check if extraction completed:**
   ```bash
   python -c "import psycopg2, os; from dotenv import load_dotenv; load_dotenv(); conn = psycopg2.connect(host=os.getenv('DB_HOST'), database=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD')); cur = conn.cursor(); cur.execute('''SELECT COUNT(*) FROM dcp_general_requirements WHERE former_council=%s AND primary_source_provision_id IN (SELECT id FROM regulatory_provisions WHERE extraction_method=%s)''', ['Ashfield', 'PyMuPDF_ashfield_chapter_f_2025_11_03']); count = cur.fetchone()[0]; print(f'Chapter F: {count} requirements'); conn.close()"
   ```

2. **If extraction completed (count > 0):**
   - Run evidence type classification
   - Run verification tests
   - Test zone + devtype filtering

3. **If extraction failed (count = 0):**
   - Check BashOutput for errors
   - Re-run extraction script

4. **Files to check:**
   - This file (ASHFIELD_EXTRACTION_IN_PROGRESS.md)
   - Latest count in database
   - Background process status
