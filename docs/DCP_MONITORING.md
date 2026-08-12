# DCP Chapter Monitoring — Operations Guide

## What It Does

Weekly automated check: did any council DCP chapter PDF change since we last extracted provisions from it?

- Runs every Monday 02:00 UTC via GitHub Actions
- Compares SHA-256 hash of current council PDF against stored hash in `dcp_chapter_registry`
- On change: uploads new version to R2, sets `needs_extraction=TRUE`, exits code 2
- No change: exits 0. Error: exits 1

## Components

| File | Purpose |
|------|---------|
| `migrations/007_dcp_chapter_registry.sql` | DB table tracking each chapter's hash, R2 path, version label |
| `migrations/008_extraction_columns.sql` | Adds `source_chapter_key`, `source_council`, `is_current` to `regulatory_provisions`; adds `last_extracted_at`, `last_extracted_version` to registry |
| `scripts/r2_upload_pdfs.py` | One-time baseline upload — reads local `_origin.pdf` files, uploads to R2, populates registry |
| `scripts/r2_monitor.py` | Weekly monitor — HEAD request + SHA check, uploads new version on change |
| `scripts/dcp_extract_changed.py` | Extraction pipeline — downloads flagged chapters from R2, extracts with pdfplumber, soft-deletes old provisions, inserts new |
| `scripts/check_registry.py` | Diagnostic — shows registry state (count by council, missing hashes) |
| `scripts/run_migration_007.py` | Applies migration 007 via psycopg2 (psql not available on Windows) |
| `scripts/run_migration_008.py` | Applies migration 008 via psycopg2 |
| `scripts/requirements-monitor.txt` | pip deps for CI monitor: boto3, psycopg2-binary, requests, python-dotenv |
| `scripts/requirements-extract.txt` | pip deps for CI extraction: pdfplumber, psycopg2-binary, boto3, python-dotenv |
| Railway cron `monitor-dcp` | Weekly Mon 02:00 UTC, all councils sequential. **Not a GitHub Actions workflow** — the old Actions monitor workflow was deleted in #506; see `docs/RAILWAY_MONITORS.md`. |
| `scripts/dcp_extract_changed.py` | Run **locally, on demand**. There is no scheduled extraction: the old Actions extraction workflow was deleted in #506 and nothing replaced its trigger. |

## R2 Bucket Structure

Bucket: `nsw-planning-pdfs`

```
source-pdfs/dcps/{council}/v1.0-baseline/{chapter_key}.pdf
source-pdfs/dcps/{council}/v1.1-{date}/{chapter_key}.pdf
source-pdfs/dcps/{council}/v1.2-{date}/{chapter_key}.pdf
```

Councils: `marrickville`, `leichhardt`, `ashfield`

## Database Table

`dcp_chapter_registry` — one row per chapter (113 total: 84 Marrickville, 16 Leichhardt, 10 Ashfield, 3 state)

Key columns: `council`, `chapter_key`, `content_hash`, `r2_current_path`, `r2_version_label`, `needs_extraction`, `url_last_changed`

## Baseline Source

The v1.0-baseline hashes were generated from the locally-stored `_origin.pdf` files in:
```
archive/2026-01-pipeline-outputs/output/{folder}/auto/{folder}_origin.pdf
```
These are the exact PDFs provisions were extracted from. The monitor compares against live council URLs — any divergence means a real update since extraction.

## GitHub Actions Secrets (Repository level)

All 5 set as **repository secrets** (not environment secrets):

- `R2_ACCOUNT_ID`
- `R2_BUCKET_NAME`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `DATABASE_URL`

## Manual Trigger

Go to: **Actions → DCP Chapter Monitor → Run workflow**

Optional inputs:
- `council` — filter to single council (blank = all)
- `dry_run` — no DB writes or R2 uploads
- `force` — re-download all regardless of Content-Length

**Do NOT use the "Re-run" button** on a failed run — it uses the old workflow YAML, not the latest commit. Always trigger a fresh run via "Run workflow".

## Exit Codes

| Code | Meaning | CI behaviour |
|------|---------|-------------|
| 0 | No changes | Green |
| 1 | Script error | Red (fails workflow) |
| 2 | Changes detected | Yellow (`continue-on-error: true`) |

## Known Gotcha: `set +e` Required

GitHub Actions bash runs with `set -e` by default. If the python script exits non-zero (e.g. code 2), bash exits the run block immediately — the `echo "exit_code=$?" >> $GITHUB_OUTPUT` line never runs, leaving the output variable empty.

Fix (already applied): `set +e` before the python call in the "Run DCP monitor" step.

## Sanity Gate

If >40% of chapters show changed in a single run, the monitor flags for human review rather than auto-uploading. This prevents false positives from council website restructures or CDN changes.

## Automated Flow (End-to-End)

```
Monday 02:00 UTC
  → Railway cron `monitor-dcp` (weekly)
    → r2_monitor.py
      → detects change → uploads v1.N to R2 → sets needs_extraction=TRUE → exits 2

  ⚠ THE CHAIN STOPS HERE. Extraction is NOT triggered automatically.
    The old Actions extraction workflow fired on workflow_run when the monitor finished;
    it was deleted in #506 and nothing replaced it. A detected change sets
    needs_extraction=TRUE and then waits for someone to run:
  → dcp_extract_changed.py   (manual, local)
      → queries needs_extraction=TRUE chapters
      → for each chapter:
          downloads PDF from R2
          extracts sections with pdfplumber
          [DB transaction]
            UPDATE regulatory_provisions SET is_current=FALSE  (old provisions)
            INSERT new provisions with source_chapter_key, source_council, is_current=TRUE
            UPDATE dcp_chapter_registry SET needs_extraction=FALSE, last_extracted_at=NOW()
          [commit]
      → exits 2 (success) or 1 (all failed)
```

If no chapter has `needs_extraction=TRUE`, the extraction script exits 0 immediately (adds ~5 seconds to every Monday run).

## Partial Failure Behaviour

If chapter A succeeds and chapter B fails, A is committed with updated provisions. B rolls back — old provisions stay live, `needs_extraction` stays TRUE. The next monitor run (or manual trigger) retries B.

## Extraction DB Columns

Added by `migrations/008_extraction_columns.sql`:

**`regulatory_provisions`**
- `source_chapter_key` — matches `chapter_key` in `dcp_chapter_registry` (NULL for legacy provisions)
- `source_council` — matches `council` in `dcp_chapter_registry` (NULL for legacy provisions)
- `is_current` — FALSE for provisions superseded by a re-extraction (default TRUE)

**`dcp_chapter_registry`**
- `last_extracted_at` — timestamp of most recent successful extraction
- `last_extracted_version` — R2 version label that was extracted (e.g. `v1.2-2026-03-01`)

## Sanity Query

After a chapter is re-extracted, verify soft-delete worked correctly:

```sql
SELECT source_council, source_chapter_key,
  COUNT(*) FILTER (WHERE is_current)      AS current,
  COUNT(*) FILTER (WHERE NOT is_current)  AS historical
FROM regulatory_provisions
WHERE source_chapter_key IS NOT NULL
GROUP BY 1, 2
ORDER BY 1, 2;
```

## Extraction Exit Codes

| Code | Meaning | CI behaviour |
|------|---------|-------------|
| 0 | Nothing to extract | Green |
| 1 | All chapters failed | Red (fails workflow) |
| 2 | At least one chapter succeeded | Green (`continue-on-error: true`) |

## Manual Extraction Trigger

Go to: **Actions → DCP Chapter Extraction → Run workflow**

Optional inputs:
- `council` — filter to single council (blank = all flagged chapters)
- `dry_run` — extract and report but no DB writes

## Historical note: workflow_run required the default branch

⚠ **This no longer applies.** The Actions extraction workflow was deleted in #506; there is no
`workflow_run` trigger and no automatic extraction. Kept because the constraint
matters if anyone reinstates a workflow: `workflow_run` only fires when the
calling YAML exists on the default branch, so a new extraction workflow on a
feature branch would not auto-trigger.
