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
| `scripts/r2_upload_pdfs.py` | One-time baseline upload — reads local `_origin.pdf` files, uploads to R2, populates registry |
| `scripts/r2_monitor.py` | Weekly monitor — HEAD request + SHA check, uploads new version on change |
| `scripts/check_registry.py` | Diagnostic — shows registry state (count by council, missing hashes) |
| `scripts/run_migration_007.py` | Applies migration 007 via psycopg2 (psql not available on Windows) |
| `scripts/requirements-monitor.txt` | pip deps for CI: boto3, psycopg2-binary, requests, python-dotenv |
| `.github/workflows/dcp-monitor.yml` | GitHub Actions schedule + manual trigger |

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

## When a Chapter Changes

1. Monitor uploads new PDF as `v1.N-{date}` to R2
2. Sets `needs_extraction=TRUE` in `dcp_chapter_registry`
3. Workflow exits 2 — "Changes detected" message in Actions log
4. Manual action required: re-run extraction pipeline on flagged chapters
