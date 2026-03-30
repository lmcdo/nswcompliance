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

**This runbook is the single source of truth for LGA onboarding.** Follow it top-to-bottom. Supplementary detail only (not required reading):
- `docs/DCP_EXTRACTION_KNOWN_PATTERNS.md` — extended artifact class catalogue, §7 TOC population detail
- `docs/DCP_SCOPE_CONFIG_REFERENCE.md` — confirmed universalPartKeys/devTypeGatedPartKeys per council
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

The enrichment pipeline requires `v2_is_actionable` to be set before it runs. The extraction script inserts NULL for this column. Set it manually first:

```sql
UPDATE regulatory_provisions
SET v2_is_actionable = TRUE
WHERE source_council = 'woollahra' AND is_current = TRUE AND v2_is_actionable IS NULL;
```

Then run the pipeline phases in order:

```bash
python -m enrichment.pipeline --phase layer
python -m enrichment.pipeline --phase site_condition
python -m enrichment.pipeline --phase type
# Skip --phase numeric (v2_enriched_at column not in current DB schema)
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
```bash
python -m enrichment.pipeline --phase layer
```

---

## Step 7a — Manual Provision Text Inspection

**Read `docs/DCP_EXTRACTION_KNOWN_PATTERNS.md` before this step.** It lists every known artifact class with examples.

Automated checks only catch patterns we've already seen. Novel patterns need human detection first.

```sql
SELECT id, provision_text
FROM regulatory_provisions
WHERE source_council = '<name>'
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
**Pass gate (NULL topics):** ≤ 5% of actionable provisions have NULL v2_topic. Above this = broken enrichment config.

**Fail gate — artifact check (≥ 5%):**
1. Note which labels are flagged
2. Add or update the config entry in `frontend-nextjs/lib/dcp-format-configs.ts`
3. Rerun to confirm pass gate before proceeding

**Fail gate — NULL topics (> 5%):**
If NULL topic provisions are structural artifacts (Contents pages, bare page numbers, definition index pages), mark them non-actionable:
```sql
UPDATE regulatory_provisions SET v2_is_actionable = false
WHERE source_council = '<council>' AND is_current = true
  AND v2_topic IS NULL AND v2_is_actionable = true
  AND (provision_text ILIKE 'Contents%' OR provision_text = '');
```
Inspect any remaining NULL-topic actionable provisions manually before bulk-updating.

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

## Step 7d — Populate `dcp_table_of_contents`

**Required for DA mode section grouping.** Without this, all provisions collapse to a single "General provisions" group because the JOIN on `toc_section_number` always returns NULL.

### Get page ranges from the extracted provisions:

```sql
SELECT document_id, min(pdf_page) as page_start, max(pdf_page) as page_end, count(*) as n
FROM regulatory_provisions
WHERE source_council = '<council>'
  AND is_current = TRUE
GROUP BY document_id
ORDER BY page_start;
```

### Insert one row per chapter PDF:

```sql
INSERT INTO dcp_table_of_contents (document_id, section_number, title, page_start, page_end)
VALUES
  ('<council>_DCP_<year>__<part_slug>', '1', 'Part A Introduction', 1, 45),
  ('<council>_DCP_<year>__<part_slug>', '2', 'Part B Controls', 1, 80),
  -- one row per document_id from the query above
;
```

**Critical:** `document_id` in TOC must exactly match `document_id` on `regulatory_provisions`. Case, underscores, everything.

If a council splits one logical chapter across multiple PDFs (e.g. Leichhardt Part G across 3 files), all three `document_id` values should map to the same `section_number`.

### Verify the JOIN works:

```bash
python scripts/validate_toc_join.py --council <council> --gate --verbose
```

**Gate:** exits 0, reports JOIN rate ≥ 85%. If it fails:

- "NO TOC" — TOC INSERT didn't land. Check the `document_id` values you inserted match the ones in `regulatory_provisions` exactly.
- FAIL with unmatched document_ids listed — `document_id` in TOC doesn't match provisions. Fix the INSERT values and re-run.
- FAIL with low JOIN rate but no unmatched ids — page range gaps. See Known Issues below.

The validator auto-detects whether TOC has been loaded at all, distinguishing a missing import from a broken join. Orphaned TOC entries (TOC rows with no matching provisions) are shown as informational — they don't fail the gate.

**Note — page range gaps:** If provisions exist outside the TOC page ranges (e.g. introductory provisions on page 1 but first TOC entry starts at page 3), extend `page_start` to 1 on the first entry:
```sql
UPDATE dcp_table_of_contents
SET page_start = 1
WHERE document_id = '<council>_DCP_<year>__<part_slug>'
  AND page_start = <original_start>;
```
Re-run the validator to confirm.

**Note — absolute vs relative page numbers:** If a council compiled multiple chapters into one PDF for TOC extraction but extracted provisions per-chapter PDF, page numbers will be mismatched (TOC shows absolute pages 300+, provisions use relative pages 1+). Solution: add a depth=0 catch-all entry with page_start=1, page_end=NULL for affected chapters. See migration 017 comments for the pattern.

**Deferred TOC items — tagging policy (NON-NEGOTIABLE):** If a chapter cannot be given a real TOC entry at this stage (e.g. PDF not available, OCR required, section structure unclear), you MUST:

1. Insert a catch-all entry so the JOIN doesn't fail:
   ```sql
   -- TODO: replace catch-all once <reason> is resolved — <what needs to happen>
   INSERT INTO dcp_table_of_contents (document_id, section_number, section_title, page_start, page_end)
   VALUES ('<document_id>', 'CATCHALL', '<chapter title> (catch-all)', 1, NULL);
   ```
2. Add a line to `.claude/DATA_QUALITY_TRACKER.md` under the council's section:
   ```
   - [ ] TOC: <chapter_key> — <reason deferred> — requires: <action>
   ```
3. The open issue must be visible in `DATA_QUALITY_TRACKER.md` before you mark the council complete.

Do NOT leave a deferred TOC item as a comment in a migration file only. It will be forgotten.

---

## Step 7e — Rule Extraction (Deterministic Phase)

**Mandatory. Run after enrichment. Do not defer to Phase 3.**

```bash
python -m enrichment.rule_extraction_pipeline --phase deterministic --council <council>
```

This runs the deterministic extractor against all actionable provisions for the council and writes `v2_extracted_rules` (jsonb) and `v2_extraction_status` (text) to `regulatory_provisions`. No LLM required — this phase is pure regex + classifier.

**Gate — DB check:**

```sql
SELECT v2_extraction_status, COUNT(*)
FROM regulatory_provisions
WHERE source_council = '<council>' AND is_current = TRUE AND v2_is_actionable = TRUE
GROUP BY v2_extraction_status ORDER BY 1;
```

Expected distribution: most provisions in `complete` or `needs_llm`. `NULL` status = pipeline did not run.

| Status | Meaning |
|--------|---------|
| `complete` | Rule fully extracted deterministically |
| `needs_llm` | Provision has conditions/cross-refs that require LLM phase — acceptable at this stage |
| `NULL` | Pipeline never ran — extraction step failed silently, re-run |

**Gate:** < 5% NULL status. If NULL rate is high, check council key matches `source_council` exactly and re-run.

**Note:** The `needs_llm` backlog is tracked — do not try to resolve it here. That is Phase 3 work. The gate only requires deterministic phase completed (< 5% NULL).

---

## Step 8 — Frontend Verification

1. Deploy or run local dev server
2. Enter an address in the LGA (see `frontend-nextjs/lib/lga-configs/{lga}.json` → `metadata.notes` for suburbs)
3. DCP section appears in assessment results
4. For heritage addresses (Woollahra: Paddington, Double Bay), heritage provisions appear

**Gate:** Address lookup returns DCP provisions. If LGA not detected, check `LGA_ALIASES` in `frontend-nextjs/lib/lga-configs/index.ts`.

---

## Step 9 — Quality Gate (Must Pass Before Council is Complete)

A council is not complete until it reaches **Grade A**. Grade B is not acceptable for a council marked production-ready.

```bash
python scripts/dcp_quality_report.py --council <council> --gate
```

**Gate:** exits 0 with `Grade: A` (score ≥ 85).

| Grade | Score | Status |
|-------|-------|--------|
| A | ≥ 85 | ✅ Council complete — proceed to merge + deploy |
| B | 70–84 | ❌ **Stop.** Diagnose which sub-scores are pulling below 85 and fix before proceeding. |
| C or below | < 70 | ❌ Major structural problem — re-investigate from Step 7. |

**How to diagnose a B score:**

The report breaks score into sub-components. Common causes:

| Sub-score failing | Likely cause | Fix |
|-------------------|-------------|-----|
| Low granularity (median chars high, O/C markers present) | Provisions not split at Objective/Control boundaries | Add split patterns to `COUNCIL_SUBSECTION_PATTERNS` in `dcp_extract_changed.py`, re-extract |
| High NULL topic rate | Enrichment config missing section codes | Fix `enrichment/config/{lga}_config.py`, re-run Step 7 |
| Low rule extraction coverage | Deterministic phase not run or low completion | Re-run Step 7e |
| Low TOC JOIN rate | Page range gaps or unmatched document_ids | Fix via Step 7d, re-run `validate_toc_join.py` |

Do not mark a council complete or open a PR for it until Grade A is confirmed.

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
