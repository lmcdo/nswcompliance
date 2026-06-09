# DCP Change Detection — Methodology Statement

**Version:** 1.0
**Date:** June 2026
**System:** PlotDetect DCP Monitoring Pipeline

---

## Purpose

This document describes the methodology used to detect, extract, and verify changes to NSW council Development Control Plans (DCPs). It is intended for QA auditors, government stakeholders, and non-technical decision-makers who need to understand how the system maintains accuracy and currency of planning control data.

---

## What the system does

The system continuously monitors 546 DCP chapter documents across 30 NSW councils. When a council publishes a new version of a DCP chapter, the system detects the change, extracts the updated provisions, compares them against the previous version, and determines whether any numeric planning control values (setbacks, heights, floor areas, parking rates) have changed.

The system does not interpret regulatory meaning. It extracts text verbatim from published council documents and performs deterministic numeric comparison.

---

## Detection methodology

### Source documents

All monitored documents are publicly available PDFs published by NSW councils on their official websites. Each document is registered in a chapter registry that records:

- Council name and DCP instrument
- The canonical URL where the council publishes the PDF
- A SHA-256 content hash of the most recently downloaded version
- The timestamp of last check and last detected change

### Change detection

The system polls each registered URL on a scheduled basis. For each chapter:

1. **Download** the current PDF from the council's website
2. **Compute** the SHA-256 hash of the downloaded content
3. **Compare** against the stored hash from the previous check
4. If the hash differs, the PDF content has changed — flag for extraction

SHA-256 is a cryptographic hash function. Two documents produce the same hash only if they are byte-for-byte identical. Any change — a single character, a reformatted table, a new page — produces a different hash.

### What this does not detect

- Changes to council websites that do not alter the PDF file itself (e.g. page layout changes around the download link)
- New DCP chapters that did not previously exist in the registry (these require manual registration)
- Changes to non-PDF planning instruments (e.g. interactive web-based controls)

---

## Extraction methodology

When a change is detected, the system extracts provisions from the updated PDF:

1. **PDF text extraction** using pdfplumber (open-source, deterministic text extraction — no AI/ML)
2. **Section identification** using per-council page range configurations or regex-based section detection
3. **Provision segmentation** into individual clauses, each tagged with section header, page number, and reference number

### Quality gates

The extraction pipeline applies three quality gates before committing changes:

| Gate | Threshold | Purpose |
|------|-----------|---------|
| Provision count | >25% drop from previous extraction → abort | Catches scanned PDFs, format changes, or extraction failures |
| Zero sections | 0 sections extracted → abort | Catches empty or image-only PDFs |
| Artifact detection | Hash-prefix headers, LaTeX tokens, two-column interleave | Identifies extraction quality issues for manual review |

Each extraction is graded A (clean), B (minor artifacts), or C (needs review) based on artifact counts.

---

## Comparison methodology

After extraction, the system compares the new provisions against the current database provisions for that chapter:

### Text comparison

1. **Normalise** both old and new text: NFKC unicode normalisation, whitespace collapse
2. **Match** provisions by reference number (exact match first, then 90% character similarity for renumbering detection)
3. **Classify** each provision as: unchanged, changed, added, removed, or renumbered

### Numeric change detection

For every changed provision, the system extracts all numeric values using pattern matching:

- Pattern: digits with optional decimal point, followed by optional unit (m, mm, %, sqm, ha, storeys)
- Example: "minimum setback of 6 metres" → extracts `6m`

If the set of numeric values in the old text differs from the new text, the provision is flagged as having a **numeric change**. This is a deterministic comparison — no AI interpretation is involved.

### Change classification

| Status | Meaning | Action |
|--------|---------|--------|
| `regeneration_artifact` | >30% of provisions show tiny diffs (<25 chars avg), no numeric changes | Auto-verified — PDF was re-exported with no substantive changes |
| `map_change` | Hash changed but zero text extracted | Flagged for manual spatial review |
| `restructure` | >50% of provisions unmatched | Full re-extraction with structural change alert |
| `ok` | Normal diff with matched provisions | Smart flagging based on numeric change detection |

---

## Smart flagging — when to alert

The system uses a three-tier severity model for alerts:

| Severity | Trigger | Action |
|----------|---------|--------|
| **CRITICAL** | Numeric values changed in provision text (e.g. setback 6m → 4.5m) | Human review required — control values may need updating |
| **STANDARD** | Structural changes (provisions added/removed in restructure) | Human review required — new controls may need extraction |
| **Auto-verified** | Text-only changes (rewording, pagination, formatting) | No action — system confirms values unchanged, updates verification timestamp |

This eliminates false alarms from cosmetic PDF republishes while ensuring genuine value changes are always flagged for human review.

---

## Audit trail

Every change detected by the system is recorded in the `provision_changes` table:

- Timestamp of detection
- Council and chapter identification
- Change type (changed, added, removed, renumbered, page_shift, restructure)
- Old and new provision text (verbatim)
- Whether the change involved numeric values
- Old and new PDF page numbers

This provides a complete, queryable history of every DCP provision change detected by the system, with full text before and after.

---

## Data provenance

Every structured control value (setback, height, floor area, etc.) stored in the system traces to:

1. **Source document** — identified by council, DCP name, chapter key
2. **Source text** — the original clause text from which the value was extracted (stored verbatim, max 250 characters)
3. **Section reference** — the DCP section and clause number
4. **Extraction method** — how the value was obtained (pdfplumber-ci, manual)
5. **Verification status** — when the value was last confirmed against the source document

---

## Known limitations

1. **PDF text extraction accuracy** — pdfplumber extracts text from digitally-created PDFs with high accuracy. Scanned PDFs (images of text) may fail extraction entirely. The provision count gate catches this and aborts rather than producing incorrect data.

2. **Numeric pattern matching** — the regex-based extractor identifies standard numeric formats (integers, decimals with units). Unusual formats (e.g. "six metres", fractional expressions, ranges expressed in prose) may not be detected as numeric changes. In these cases, the text change is still recorded but may not trigger a CRITICAL alert.

3. **Council URL changes** — when a council restructures their website, PDF URLs may change. The system detects download failures and alerts after 3+ consecutive failures. New URLs must be manually updated.

4. **Scope** — the system monitors DCP chapters registered in the chapter registry. It does not automatically discover new DCP chapters, new councils, or changes to LEPs/SEPPs (which are monitored through separate ePlanning integration).

5. **Not a substitute for professional advice** — the system extracts and tracks published planning controls. It does not interpret their application to specific development proposals. Users should verify controls against the original DCP document and seek professional planning advice for development decisions.

---

## System statistics (as at June 2026)

| Metric | Value |
|--------|-------|
| Councils monitored | 30 |
| DCP chapters tracked | 546 |
| Structured control values | 1,001 across 28 LGAs |
| Control types | 16 (setbacks, height, floor area, site coverage, landscaping, parking, etc.) |
| Provision changes recorded | 45 (across 2 councils with detected changes to date) |
| ePlanning layers monitored | 8 state-wide planning layers |
| Automated tests | 1,794 (Python) + 615 (frontend) |
