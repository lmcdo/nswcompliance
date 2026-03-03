# DCP Extraction — Known Patterns & Pre-Onboarding Checklist

> **Read this before starting any new LGA onboarding.**
> Every section below is a class of bug we have encountered at least once. The fix is known.
> The goal is to detect and fix before import, not after 47,000 provisions are in production.

---

## How to Use This Document

1. **Before extraction:** Read §1–§8 to know what to look for in sample PDFs.
2. **After extraction, before import:** Run `scripts/verify_dcp_formatting.py --council <name>` and follow the pre-import checklist in §9.
3. **When writing `dcp-format-configs.ts` entry:** Use §3 for regex patterns.
4. **When investigating a data quality report:** Jump to the relevant section by bug class.

---

## §1 — LaTeX Math Artifacts

**What it looks like in `provision_text`:**
```
The minimum lot size is 6 0 0 { \mathsf { m } } ^ { 2 }$
The FSR shall not exceed 0 . 6 : 1
Setback of 1 , 5 0 0 mm from boundary
```

**Root cause:** pdfplumber extracts typeset equations from PDF as raw LaTeX tokens. Each digit, operator, and unit is space-separated. This happens when the DCP was produced from a Word document using the MS Word equation editor, which stores equations as LaTeX internally.

**Affected councils:** Marrickville (36 provisions fixed 2026-03-04). Check any council whose source PDF came from a Word template with equation fields.

**Detection:** Search provision_text for `\mathsf`, `\mathtt`, `\mathfrak`, `\star_`, `{ , }`, or digits separated by spaces followed by `^`.

**Fix:** Add `preProcessReplacements` array to the council's `dcp-format-configs.ts` entry. See `marrickville` entry for the full 9-rule sequence. Order is significant — apply in the order shown.

**Key rules (in order):**
```
$( → (           LaTeX math-mode opening paren
\mathsf{mm} → mm   Unit token
\mathsf{m}^{2} → m²  Square metre
{ , } → ,         Thousands separator
$ → (remove)      Math-mode delimiter
1 , 0 → 1,0       Spaced thousands separator (digits on both sides of comma)
3 . 0 → 3.0       Spaced decimal point
1 2 3 → 123        Space-separated digits (triple then double passes)
```

**Verify fix:** No `\math`, `{ ,`, or `{ 2 }` in any provision_text.

---

## §2 — Page Header/Footer Bleed

**What it looks like:**
```
# 5 Marrickville Development Control Plan 2011
Marrickville Development Control Plan 2011
WAVERLEY DEVELOPMENT CONTROL PLAN 2022
4
```

**Root cause:** pdfplumber extracts every text block on the page, including running headers and footers that repeat on each page. When a provision spans multiple pages, these headers bleed into the middle of the provision text.

**Sub-types:**

| Sub-type | Example | Detection regex |
|---|---|---|
| Bare page numbers | `4` or `78` (whole line) | `^\d{1,3}$` |
| Running title | `Marrickville Development Control Plan 2011` | exact prefix match |
| Hash-prefix heading | `# 5 Marrickville Development Control Plan 2011` | `^#\s*\d{1,3}\s+\w` |
| Right-aligned section code | `Ecologically Sustainable Development      B2` | `\s{3,}[A-F]\d{1,2}\s*$` |

**Affected councils:** Marrickville (bare page numbers + hash-prefix + title), Waverley (bare page numbers + right-aligned codes + title), Ashfield (title only). Every council PDF with running headers is a candidate.

**How to identify:** Run `python scripts/verify_dcp_formatting.py --council <name> --limit 50` and inspect flagged lines. Also manually check `pdf_page_image_url` pages that span the page count (high pdf_page values for multi-page provisions).

**Fix:** Add to `skipLinePatterns` and/or `skipLinePrefixes` in the council's `dcp-format-configs.ts` entry.

**Template:**
```ts
mycouncy: {
  skipLinePatterns: [
    /^\d{1,3}$/,              // bare page numbers
    /^#\s*\d{1,3}\s+\w/,     // hash-prefix running headers
    /\s{3,}[A-Z]\d{1,2}\s*$/ // right-aligned section codes (Waverley style)
  ],
  skipLinePrefixes: [
    'My Council Development Control Plan', // exact document title
  ],
},
```

---

## §3 — Chapter Prefix Lines

**What it looks like:**
```
Chapter C

Sustainability controls for new development...
```

**Root cause:** pdfplumber extracts the chapter designation line (`Chapter C`, `Chapter E1`) as a separate text block before the provision text. This is a PDF layout artifact from chapter title pages embedded at the start of each PDF chapter file.

**Affected councils:** Ashfield (~65 provisions). Applies to any council that uses per-chapter PDFs where the chapter identifier is typeset as a large display heading on its own line.

**Detection:** Provisions starting with `^Chapter [A-Z]\d*` followed by a blank line. Run: `grep -c "^Chapter [A-Z]" in raw sample`.

**Fix:** `preProcessReplacements` with a whole-text regex:
```ts
{ from: /^Chapter [A-Z]\d*[^\n]*\n+/m, to: '' },
```
This strips only the first `Chapter X` line; subsequent text is preserved.

---

## §4 — Table of Contents Provisions

**What it looks like:**
```
1.1  Site Analysis...............................................12
1.2  Setbacks...................................................14
1.3  Height.....................................................16
```

**Root cause:** If the DCP PDF has a table of contents chapter, pdfplumber extracts it as provisions when it falls within the page range assigned to a chapter. The dotted leaders (`.......`) and page number references are extracted verbatim.

**Detection:** Provisions containing 4+ consecutive dots (`\.{4,}`) or ending with a bare page number after whitespace. Also: `v2_is_actionable` should be False for these — check if any are accidentally marked True.

**Fix:** Mark as `v2_is_actionable = False` via DB update. Do NOT delete — they serve as navigational context.

**Verify:** Query for `provision_text ~ '\.{5,}'` and confirm all are `v2_is_actionable = False`.

---

## §5 — Word Cross-Reference Artifacts

**What it looks like:**
```
See clause Error! Reference source not found. for setback requirements.
The heritage study (Error! Reference source not found.) identifies...
```

**Root cause:** DCP was authored in Microsoft Word with internal cross-references (bookmarks). When exported to PDF without resolving references, Word writes the literal error text `Error! Reference source not found.` in place of the cross-reference destination.

**Affected councils:** Marrickville (186 provisions cleaned 2026-02-05).

**Detection:** `SELECT count(*) FROM regulatory_provisions WHERE provision_text LIKE '%Error! Reference source not found.%' AND former_council = 'marrickville'`

**Fix:** Replace the error text with a neutral placeholder. Do NOT delete the surrounding sentence (it contains real control content). Use:
```sql
UPDATE regulatory_provisions
SET provision_text = REPLACE(provision_text, 'Error! Reference source not found.', '[cross-reference]')
WHERE provision_text LIKE '%Error! Reference source not found.%'
  AND former_council = 'marrickville';
```

**Note:** The `[cross-reference]` placeholder is intentionally visible to users so they know context is missing. Do not silently strip it.

---

## §6 — Truncated `pdf_page_image_url` Stems

**What it looks like:**
```
-- Old extraction (truncated)
https://r2.example.com/.../Landscaping_page_42.png

-- New re-extraction (correct)
https://r2.example.com/.../Landscaping_and_Tree_Management_page_42.png
```

**Root cause:** First-pass extractions used a truncated filename derived from a short chapter code or first-word slug. Later re-extractions used the full chapter title as the filename stem. The database retains old URLs for provisions that were never re-extracted (they still have `is_current=True` from the original pass).

**Affected councils:** Marrickville (57 chapters, 391 provisions fixed 2026-03-04). Any council with two generations of extraction is a candidate.

**Detection algorithm:**
1. Extract URL stems: `regexp_replace(pdf_page_image_url, '_page_\d+\.png$', '')`
2. Find stems with ONLY old provisions (document_id with single underscores): `document_id !~ '__'` detects new-format doc IDs
3. Find a longer sibling stem that is a prefix match — that's the correct full stem
4. **CRITICAL:** Use `~ '__'` regex, NOT `LIKE '%__%'` — in SQL, `_` is a wildcard for any character

**Fix template (run per council):**
```sql
-- For each (short_stem, full_stem) pair:
UPDATE regulatory_provisions
SET pdf_page_image_url = REPLACE(pdf_page_image_url, short_stem || '_page_', full_stem || '_page_')
WHERE former_council = 'marrickville'
  AND pdf_page_image_url LIKE short_stem || '_page_%';
```

**Edge cases:**
- Double underscores in filenames like `Statutory_Information__page_` are **correct** — the double underscore is part of the actual R2 filename, not a truncation artifact
- Heritage false positive: `8.0_Heritage` is a valid complete chapter name even though `8.0_Heritage_-_Part` exists and is longer — check new provision count before classifying as truncated
- Orphaned stems (no full-name sibling exists, e.g., `8.0_Heritage_-_Part` with 4 provisions) — leave as-is, investigate manually

---

## §7 — Duplicate `is_current=True` Provisions

**What it looks like:** Two provisions with the same `provision_text` content but different `document_id` formats — one old-style (single-underscore), one new-style (double-underscore) — both with `is_current=True`.

**Root cause:** First-pass extractions set `is_current=True` with `source_chapter_key=NULL`. The retirement step in `dcp_extract_changed.py` uses `WHERE source_chapter_key = %s` — so it cannot retire these original provisions. When a chapter is re-extracted, both old and new provisions coexist as current.

**Detection:**
```sql
SELECT former_council, source_chapter_key, count(*)
FROM regulatory_provisions
WHERE is_current = TRUE
  AND former_council = 'marrickville'
GROUP BY former_council, source_chapter_key
HAVING count(*) > (SELECT count(*) FROM regulatory_provisions WHERE source_chapter_key IS NULL AND is_current = TRUE AND former_council = 'marrickville' LIMIT 1)
ORDER BY count(*) DESC;
```

Or simpler: count provisions where `source_chapter_key IS NULL AND is_current = TRUE` per council — if > 0, those are unretiable first-pass provisions.

**Fix:** For each re-extracted chapter, manually retire old provisions:
```sql
UPDATE regulatory_provisions
SET is_current = FALSE
WHERE former_council = 'marrickville'
  AND source_chapter_key IS NULL
  AND pdf_page_image_url LIKE '%ChapterName%';
```

**Prevention:** The retirement logic in `dcp_extract_changed.py` (lines 416–424) works correctly for all extractions run after 2026-01-01 (source_chapter_key is populated). First-pass provisions are a one-time legacy issue per council.

---

## §8 — Topic / Layer Misclassification

**What it looks like:** Heritage provisions appearing under "Setbacks" topic, or SEPP provisions mixed into DCP results.

**Sub-types and causes:**

| Type | Cause | Detection |
|---|---|---|
| Heritage marked as generic | `v2_marker` not set to `heritage` | `WHERE v2_topic LIKE '%heritage%' AND v2_marker != 'heritage'` |
| "General" heritage = non-actionable | Intro text, objectives, historical narrative | `WHERE v2_marker='heritage' AND v2_topic='General'` — all should be `v2_is_actionable=False` |
| Wrong topic from section code | Tagger config has wrong part→topic mapping | Compare sample provisions against DCP structure map |
| Precinct provisions in generic layer | `v2_dcp_layer` not set to `precinct` | Check provisions from E-parts (Waverley) or site-specific chapters |

**Marrickville-specific:**
- Heritage "General" category (intro/objectives/definitions) → `v2_is_actionable=False` (818 provisions fixed 2026-02-05)
- HCA-specific provisions: tag with `v2_heritage_hca` only if ONE specific HCA is mentioned by name or DCP number
- `hca_N` slugs do NOT always correspond to LEP C-codes: always verify slug→HCA mapping via provision text content

**New council checklist:**
1. Run `LayerTopicTagger` on 20 sample provisions per chapter, inspect output
2. Verify heritage chapter provisions get `v2_marker='heritage'` and `v2_dcp_layer='condition'`
3. Confirm "General" provisions in heritage chapter are `v2_is_actionable=False`
4. Check topic distribution: no single topic should have >40% of all provisions (suggests config error)

---

## §9 — Pre-Import QA Checklist

Run this for every council before bulk import to production.

### Step 1: Format artifact scan
```bash
python scripts/verify_dcp_formatting.py --council <name> --limit 100
```
**Pass gate:** <5% of provisions have flagged artifact lines per check type.

If any check fails:
- Add config to `frontend-nextjs/lib/dcp-format-configs.ts` (see §2, §3)
- Re-run to confirm pass

### Step 2: Known artifact spot checks
Run these SQL queries against the staging / new provisions:

```sql
-- LaTeX tokens
SELECT count(*) FROM regulatory_provisions
WHERE former_council = '<council>'
  AND (provision_text LIKE '%\math%' OR provision_text LIKE '%{ , }%' OR provision_text ~ '\d \d \d');

-- Word cross-references
SELECT count(*) FROM regulatory_provisions
WHERE former_council = '<council>'
  AND provision_text LIKE '%Error! Reference source not found.%';

-- TOC dotted leaders
SELECT count(*) FROM regulatory_provisions
WHERE former_council = '<council>'
  AND provision_text ~ '\.{5,}';

-- Very short provisions (likely artifacts or headings imported as provisions)
SELECT count(*) FROM regulatory_provisions
WHERE former_council = '<council>'
  AND length(provision_text) < 20
  AND v2_is_actionable = TRUE;
```

All should return 0. If not, investigate and fix before import.

### Step 3: URL stem check
```sql
-- Any provisions missing pdf_page_image_url?
SELECT count(*) FROM regulatory_provisions
WHERE former_council = '<council>'
  AND (pdf_page_image_url IS NULL OR pdf_page_image_url = '');

-- Check for obvious mismatches (provision text from chapter A with URL from chapter B)
SELECT distinct
  regexp_replace(pdf_page_image_url, '_page_\d+\.png$', '') as stem,
  count(*) as n
FROM regulatory_provisions
WHERE former_council = '<council>'
GROUP BY stem
ORDER BY n DESC
LIMIT 20;
```

### Step 4: Topic distribution sanity check
```sql
SELECT v2_topic, count(*) as n,
  round(100.0 * count(*) / sum(count(*)) over (), 1) as pct
FROM regulatory_provisions
WHERE former_council = '<council>'
GROUP BY v2_topic
ORDER BY n DESC;
```
Flag if any topic > 40% of total (suggests a config miss) or if any topic has 0 provisions (suggests a missed chapter).

### Step 5: Duplicate is_current check
```sql
-- Provisions with NULL source_chapter_key and is_current=True
-- These cannot be retired by the pipeline. Fix manually if re-extracting.
SELECT count(*) FROM regulatory_provisions
WHERE former_council = '<council>'
  AND source_chapter_key IS NULL
  AND is_current = TRUE;
```

### Step 6: Manual spot inspection (10 provisions)
Select 10 provisions across different chapters and compare against the actual DCP PDF pages. Verify:
- No header/footer bleed
- Correct chapter attribution (provision_text matches the page shown in pdf_page_image_url)
- Numeric values are readable (no LaTeX token remnants)
- No mid-sentence truncation

---

## §10 — Onboarding Sequence

This is the recommended order for a clean onboarding:

1. **Survey the PDF structure** — `python scripts/survey_dcp.py <pdf>` — understand chapters, page ranges, section codes
2. **Extract 50 provisions as a sample** — `python scripts/dcp_extract_changed.py --council <name> --dry-run --limit 50`
3. **Run verify script** — identify formatting artifacts (§1–§4)
4. **Write `dcp-format-configs.ts` entry** — add cleanup rules for detected artifacts
5. **Run pre-import QA** (§9) on full extraction in staging
6. **Write `enrichment/config/<name>_config.py`** — layer/topic mapping; verify with 20-provision spot check (§8)
7. **Run populate script** — insert into `dcp_chapter_registry`
8. **Full extract + enrich** — layer, site_condition, type, numeric phases
9. **Final QA** — all §9 checks pass, 10-provision manual spot check
10. **Import to production** — `is_current=True` for new provisions, retire old if applicable

---

## Appendix A — `dcp-format-configs.ts` Entry Template

```ts
mycouncil: {
  skipLinePatterns: [
    /^\d{1,3}$/,              // bare page numbers
    /^#\s*\d{1,3}\s+\w/,     // hash-prefix running headers
    // add council-specific patterns here
  ],
  skipLinePrefixes: [
    'My Council Development Control Plan 20XX', // exact document title
  ],
  preProcessReplacements: [
    // Chapter prefix (Ashfield-style)
    { from: /^Chapter [A-Z]\d*[^\n]*\n+/m, to: '' },
    // LaTeX (Marrickville-style — add only if LaTeX artifacts found)
    // ... copy from marrickville entry if needed
  ],
},
```

---

## Appendix B — Scripts Reference

| Script | Purpose |
|---|---|
| `scripts/verify_dcp_formatting.py` | Format artifact scan — 5 check types, pass/fail gate |
| `scripts/survey_dcp.py` | PDF structure profiler — chapters, page counts, section codes |
| `scripts/dcp_extract_changed.py` | Main extraction + retirement pipeline |
| `scripts/populate_<council>_registry.py` | Insert chapter registry rows |
| `enrichment/extractors/layer_topic_tagger.py` | Layer/topic assignment |
| `enrichment/config/<council>_config.py` | Per-council tagger config |

---

## Appendix C — Data Quality Issues Log

| DQ# | Council | Description | Provisions | Fixed |
|---|---|---|---|---|
| DQ-01 | Marrickville | Word cross-references (`Error! Reference source not found.`) | 186 | 2026-02-05 |
| DQ-02 | Marrickville | Heritage "General" marked actionable (intro/objectives text) | 818 | 2026-02-05 |
| DQ-26 | Marrickville | Truncated `pdf_page_image_url` stems | 391 (57 chapters) | 2026-03-04 |
| DQ-27 | Marrickville | LaTeX math token artifacts | 36 | 2026-03-04 |

See `.claude/DATA_QUALITY_TRACKER.md` for full issue history.
