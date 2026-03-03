# LGA Extraction Runbook

Step-by-step pipeline for integrating a new LGA. Each step has a pass/fail gate — stop and investigate before proceeding if a gate fails. Do not batch steps across LGAs; complete one LGA fully before starting the next.

**Batch 1 order:** Woollahra → City of Sydney → Ku-ring-gai

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
# Check enrichment/pipeline.py for exact invocation
python -c "from enrichment.pipeline import run_pipeline; run_pipeline(council='woollahra')"
```

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

---

## Step 7b — Format Verification

After enrichment completes, check that provision text is free of PDF extraction artifacts before exposing to users.

```bash
python scripts/verify_dcp_formatting.py --council <name> --limit 50
```

**Pass gate:** < 5% of sampled provisions have flagged artifact lines — no action needed.

**Fail gate (≥ 5%):**
1. Note which artifact labels are flagged (bare page numbers, hash-prefix headers, chapter prefix lines, long lines without punctuation)
2. Add a config entry in `frontend-nextjs/lib/dcp-format-configs.ts` under the council key
3. Rerun the script to confirm pass gate before proceeding

Example config entry (adjust patterns to match actual artifacts):
```typescript
my_council: {
  skipLinePrefixes: ['My Council Development Control Plan'],
  skipLinePatterns: [/^\d{1,3}$/],
},
```

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
