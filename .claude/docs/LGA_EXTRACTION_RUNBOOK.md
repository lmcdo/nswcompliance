# LGA Extraction Runbook

Step-by-step pipeline for integrating a new LGA. Each step has a pass/fail gate — stop and investigate before proceeding if a gate fails. Do not batch steps across LGAs; complete one LGA fully before starting the next.

**Batch 1 order:** Woollahra → City of Sydney → Ku-ring-gai

---

## How the pipeline works

The extraction is semi-automated, not fully automated. Here's what's automated vs. what requires per-LGA work:

| Step | Automated? | Notes |
|------|------------|-------|
| PDF download to R2 + registry insert | ✅ `populate_*.py` | Council PDF URLs need to be filled in once |
| PDF extraction to DB provisions | ✅ `dcp_extract_changed.py` | Downloads from R2, runs pdfplumber, bulk-inserts |
| Section detection | ⚠️ Semi | `SECTION_RE` works for ~80% of councils; the rest need page ranges added manually |
| Enrichment (layer/topic tagging) | ✅ `run_pipeline()` | Requires per-LGA config in `enrichment/config/<lga>_config.py` |
| Formatting QA | ⚠️ Semi | Automated script catches known artifacts; novel artifacts need manual inspection first |
| Scanned PDFs | ❌ Blocker | pdfplumber gets zero text; flag for manual or OCR solution |

The extraction script is triggered by `needs_extraction=TRUE` in `dcp_chapter_registry`. The populate script sets this flag. On successful extraction, it's cleared to `FALSE`. Failed chapters stay `TRUE` and are retried on next run.

**Reference docs (read before starting):**
- `docs/DCP_EXTRACTION_KNOWN_PATTERNS.md` — known artifact classes, detection, and fixes
- `frontend-nextjs/lib/dcp-format-configs.ts` — existing per-council formatting configs

---

## Pre-flight (run once per session)

```bash
# Deps
python -c "import boto3, psycopg2, pdfplumber; print('deps OK')"

# DB connection
python -c "
from dotenv import load_dotenv; load_dotenv('.env')
import os, psycopg2
conn = psycopg2.connect(os.environ['DATABASE_URL'])
print('DB OK:', conn.server_version)
conn.close()
"

# R2 access
python -c "
from dotenv import load_dotenv; load_dotenv('.env')
import os, boto3
s3 = boto3.client('s3',
  endpoint_url=f\"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com\",
  aws_access_key_id=os.environ['R2_ACCESS_KEY_ID'],
  aws_secret_access_key=os.environ['R2_SECRET_ACCESS_KEY'],
  region_name='auto')
s3.list_buckets(); print('R2 OK')
"
```

**Gate:** All three pass. Fix env before touching anything else.

---

## Step 1 — Download PDFs

| LGA | Directory | Council page |
|-----|-----------|--------------|
| woollahra | `woollahra/` | https://www.woollahra.nsw.gov.au/Building-and-development/Development-rules/dcps-background |
| city_of_sydney | `city-of-sydney/` | https://www.cityofsydney.nsw.gov.au/development-control-plans/sydney-dcp-2012 |
| ku_ring_gai | `ku-ring-gai/` | https://www.krg.nsw.gov.au/Planning-and-development/Planning-policies-and-guidelines/Ku-ring-gai-Development-Control-Plan |

Filenames must match `local_filename` in the populate script exactly.

**Gate:** `ls woollahra/*.pdf | wc -l` returns expected chapter count (10 Woollahra, 6 CoS, 9 Ku-ring-gai).

---

## Step 2 — Profile with survey_dcp.py

Run on 2–3 representative chapters before touching the DB. Always include the largest/most complex chapter.

```bash
# Woollahra
python scripts/survey_dcp.py woollahra/part-c1-paddington-hca.pdf
python scripts/survey_dcp.py woollahra/part-b-general.pdf

# City of Sydney — section 2 is critical (75 HCAs, ~12.88 MB)
python scripts/survey_dcp.py city-of-sydney/section-2-locality-statements.pdf
python scripts/survey_dcp.py city-of-sydney/section-3-general-provisions.pdf

# Ku-ring-gai
python scripts/survey_dcp.py ku-ring-gai/principal-dcp.pdf
python scripts/survey_dcp.py ku-ring-gai/dcp-43-car-parking.pdf
```

**Gate:**

| SECTION_RE hit rate | Action |
|---------------------|--------|
| ≥ 50% | Proceed. Regex extraction will work. |
| < 50% | **Stop.** Add `{LGA}_PAGE_RANGES` to `dcp_extract_changed.py` before Step 4. |
| 0% | PDF may be scanned/image-based. Check with `pdfplumber.open(f).pages[0].extract_text()`. If None → flag for manual/OCR, do not proceed. |

If page ranges are needed:
1. Read the PDF TOC to identify section page ranges
2. Add list + `COUNCIL_PAGE_RANGES` entry in `dcp_extract_changed.py`
3. `git add -f scripts/dcp_extract_changed.py && git commit -m "feat: {lga} page ranges"`

---

## Step 3 — Fill Council URLs

```bash
grep -n "FILL_IN" scripts/populate_woollahra_registry.py
```

Replace `<FILL_IN>` with direct PDF download URLs (right-click → Copy Link in browser).
If council uses redirect-based downloads, leave `<FILL_IN>` — the council page URL is stored as fallback.

**Gate:** `WOOLLAHRA_COUNCIL_PAGE` (or equivalent constant) points to a real URL.

---

## Step 4 — Populate Registry

The populate script does two things in one run: uploads each PDF to R2 and inserts a row into `dcp_chapter_registry` with `needs_extraction=TRUE`. Both must succeed before extraction can run.

```bash
# Dry-run first
python scripts/populate_woollahra_registry.py --dry-run

# Real run (uploads to R2 + inserts DB rows)
python scripts/populate_woollahra_registry.py

# Single chapter (for missing PDF catch-up)
python scripts/populate_woollahra_registry.py --chapter part-c1-paddington-hca
```

**Gate — DB check:**

```sql
SELECT council, chapter_key, needs_extraction, r2_current_path IS NOT NULL as has_r2_path
FROM dcp_chapter_registry
WHERE council = 'woollahra'
ORDER BY sort_order;
```

All chapters present, `needs_extraction = TRUE`, `has_r2_path = TRUE`.

If chapters are missing (PDF was not found), download the missing PDFs and re-run with `--chapter`.

---

## Step 5 — Extraction Dry-Run

```bash
python scripts/dcp_extract_changed.py --council woollahra --dry-run
```

The script queries `dcp_chapter_registry` for `needs_extraction=TRUE` rows, downloads each PDF from R2 to a temp dir, runs pdfplumber, and reports what would be inserted — no DB writes.

**Gate per chapter:**

| Output | Status | Action |
|--------|--------|--------|
| "Extracted: N sections" N ≥ page_count/30 | ✅ | Continue |
| "page-range fallback: N sections" | ✅ | Page ranges working |
| "ABORT: N sections from P-page PDF" | ❌ | Add page ranges (Step 2) |
| "R2 download failed" | ❌ | Check R2 creds, re-run Step 4 |
| 0 sections extracted | ❌ | PDF likely scanned/image-based — flag for manual review |

---

## Step 6 — Extract

```bash
python scripts/dcp_extract_changed.py --council woollahra
```

Each chapter is an atomic transaction: provisions are inserted and `needs_extraction` cleared to `FALSE` in one commit. If a chapter fails, it rolls back — old provisions stay live, `needs_extraction` stays `TRUE`.

**Gate — DB checks:**

```sql
-- Total provisions
SELECT COUNT(*) FROM regulatory_provisions
WHERE source_council = 'woollahra' AND is_current = TRUE;
-- Expected: 200–2000

-- Per-chapter (flag any chapter < 5 provisions)
SELECT source_chapter_key, COUNT(*) as n
FROM regulatory_provisions
WHERE source_council = 'woollahra' AND is_current = TRUE
GROUP BY source_chapter_key ORDER BY source_chapter_key;

-- Registry cleared
SELECT chapter_key, needs_extraction FROM dcp_chapter_registry
WHERE council = 'woollahra' AND is_active = TRUE;
-- All needs_extraction = FALSE
```

If a chapter failed: `needs_extraction` stays `TRUE`, old provisions remain live. Safe to re-run immediately.

To re-extract a specific chapter after fixing:
```sql
UPDATE dcp_chapter_registry SET needs_extraction = TRUE
WHERE council = 'woollahra' AND chapter_key = 'part-c1-paddington-hca';
```
Then re-run `dcp_extract_changed.py --council woollahra`.

---

## Step 7 — Enrichment

```bash
python -c "from enrichment.pipeline import run_pipeline; run_pipeline(council='woollahra')"
```

This requires `enrichment/config/woollahra_config.py` to exist with the correct section-code → layer/topic mapping. If the config is missing or wrong, enrichment will either skip the council or tag everything as `generic`.

**Gate — DB checks:**

```sql
-- Layer distribution (must not be all 'generic')
SELECT v2_dcp_layer, COUNT(*) FROM regulatory_provisions
WHERE source_council = 'woollahra' AND is_current = TRUE
GROUP BY v2_dcp_layer ORDER BY 1;
-- Expected mix: generic, use_specific, condition

-- Heritage chapters tagged correctly
SELECT source_chapter_key, v2_dcp_layer, v2_topic, COUNT(*)
FROM regulatory_provisions
WHERE source_council = 'woollahra'
  AND source_chapter_key LIKE 'part-c%'
  AND is_current = TRUE
GROUP BY 1, 2, 3 ORDER BY 1;
-- All C chapters: layer='condition', topic='heritage'

-- Untagged rate
SELECT
  COUNT(*) FILTER (WHERE v2_topic IS NULL) AS untagged,
  COUNT(*) AS total,
  ROUND(COUNT(*) FILTER (WHERE v2_topic IS NULL) * 100.0 / COUNT(*), 1) AS pct_untagged
FROM regulatory_provisions
WHERE source_council = 'woollahra' AND is_current = TRUE;
-- < 20% untagged is acceptable
```

If enrichment tags are wrong: fix `enrichment/config/{lga}_config.py`, re-run enrichment, re-check.

To re-run enrichment only (no re-extraction):
```python
from enrichment.pipeline import run_pipeline
run_pipeline(council='woollahra', phases=['layer_topic'])
```

---

## Step 7a — Manual Provision Text Inspection

**Read `docs/DCP_EXTRACTION_KNOWN_PATTERNS.md` before this step.** It lists every known artifact class with examples.

Automated checks only catch patterns we've already seen. Novel patterns need human detection first.

```sql
SELECT id, provision_text
FROM regulatory_provisions
WHERE former_council = '<name>'
  AND v2_is_actionable = true
ORDER BY random()
LIMIT 10;
```

Read 10 provisions. Look for:
- Repeated document title lines (e.g., "Waverley Development Control Plan 2022")
- Running header lines (e.g., "Waste      B1" with multiple spaces before the code)
- Bare page numbers (a line containing just "4" or "78")
- Chapter/section prefix lines that aren't part of the control text
- LaTeX math tokens (`\mathsf`, `{ , }`, spaced digits like `6 0 0`)
- Word cross-references (`Error! Reference source not found.`)
- TOC dotted leaders (`1.1  Site Analysis.............12`)
- Any other line that clearly doesn't belong

If you spot a new artifact pattern not in `frontend-nextjs/lib/dcp-format-configs.ts` → add it before Step 7b.

**Known patterns by council (already configured):**

| Council | Artifacts |
|---------|-----------|
| marrickville | `# N Title` hash headers, bare page numbers, "Marrickville Development Control Plan", LaTeX math tokens, Word cross-references |
| ashfield | "Comprehensive Inner West DCP 2016", "Chapter X" prefix lines |
| waverley | "Title      B1" right-aligned headers, "WAVERLEY DEVELOPMENT CONTROL PLAN 2022", bare page numbers |
| leichhardt | None (clean) |

---

## Step 7b — Format Verification (Automated)

```bash
python scripts/verify_dcp_formatting.py --council <name> --limit 100
```

Runs 3 sections:
1. **Text artifact checks** (8 patterns): bare_page_numbers, hash_prefix_headers, chapter_prefix_lines, right_aligned_headers, latex_tokens, word_cross_references, toc_dotted_leaders, short_provision
2. **Topic distribution**: flags any topic > 40% of all provisions (suggests enrichment config issue)
3. **is_current audit**: counts first-pass provisions with NULL source_chapter_key (these cannot be auto-retired if re-extracted)

**Pass gate (Section 1):** < 5% of sampled provisions have flagged artifact lines.

**Fail gate (≥ 5%):**
1. Note which labels are flagged
2. Add or update the config entry in `frontend-nextjs/lib/dcp-format-configs.ts`
3. Rerun to confirm pass gate before proceeding

The script prints a `dcp-format-configs.ts` skeleton automatically when format checks fail — use it as a starting point, but verify the exact patterns against what you saw in Step 7a.

---

## Step 7c — Heritage Verification (if council has heritage chapters)

```sql
-- All heritage provisions correctly tagged
SELECT v2_marker, v2_dcp_layer, COUNT(*)
FROM regulatory_provisions
WHERE source_council = 'woollahra'
  AND source_chapter_key LIKE 'part-c%'
  AND is_current = TRUE
GROUP BY 1, 2;
-- v2_marker='heritage', v2_dcp_layer='condition'

-- General subtopic should be non-actionable
SELECT v2_topic, v2_is_actionable, COUNT(*)
FROM regulatory_provisions
WHERE source_council = 'woollahra'
  AND v2_marker = 'heritage'
  AND is_current = TRUE
GROUP BY 1, 2 ORDER BY 1;
-- v2_topic='General' → v2_is_actionable=FALSE (intro/objectives text)
```

See `memory/heritage.md` for HCA tagging rules if this council has individual HCA sections.

---

## Step 8 — Frontend Verification

1. Deploy or run local dev server
2. Enter an address in the LGA (see `frontend-nextjs/lib/lga-configs/{lga}.json` → `metadata.notes` for suburbs)
3. DCP section appears in assessment results
4. For heritage addresses (Woollahra: Paddington, Double Bay), heritage provisions appear

**Gate:** Address lookup returns DCP provisions. If LGA not detected, check `LGA_ALIASES` in `frontend-nextjs/lib/lga-configs/index.ts`.

---

## Recovery Procedures

### Extraction failed mid-run
Old provisions stay live (rollback on failure). `needs_extraction=TRUE` on failed chapter. Re-run immediately — pipeline retries only failed chapters.

### Need to re-run enrichment only (no re-extraction)
```python
from enrichment.pipeline import run_pipeline
run_pipeline(council='woollahra', phases=['layer_topic'])
```

### Wrong config discovered after extraction
```
1. Fix enrichment/config/{lga}_config.py
2. git add -f enrichment/config/{lga}_config.py && git commit
3. Re-run enrichment (Step 7)
4. Re-check tags (Step 7 SQL)
```

### SECTION_RE miss discovered after extraction (low section counts)
```sql
-- Re-flag all chapters
UPDATE dcp_chapter_registry SET needs_extraction = TRUE
WHERE council = 'woollahra' AND is_active = TRUE;
```
Then add page ranges to `dcp_extract_changed.py` and re-run extraction (Step 6).

---

## Chapter Counts Quick Reference

| LGA | DB council key | Chapters | Expected provisions | PDF dir |
|-----|---------------|----------|---------------------|---------|
| Woollahra | `woollahra` | 10 | 300–800 | `woollahra/` |
| City of Sydney | `city_of_sydney` | 6 | 1000–3000 | `city-of-sydney/` |
| Ku-ring-gai | `ku_ring_gai` | 9 | 500–1500 | `ku-ring-gai/` |

---

## Config-Driven Tagger Reference

Woollahra and Waverley use `parts` (section-code prefix from provision_text heading).
City of Sydney and Ku-ring-gai use `chapter_topics` (chapter_key substring from document_id).

If a new LGA's sections don't parse correctly, check:
1. Does `_extract_section_code()` match the heading format in provision_text?
2. Are the `parts` / `chapter_topics` keys matching the actual codes/slugs?
3. Is the council key in `COUNCIL_CONFIGS` (enrichment/config/__init__.py) present in the document_id?
