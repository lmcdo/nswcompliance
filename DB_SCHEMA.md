# Database Schema - Complete Reference

Last Updated: **2026-08-10** (header figures re-measured live; the per-table sections below
still carry their original February numbers except where marked — treat any unmarked count as
unverified and re-run the query)
Total Tables: **118** base tables
Total Provisions: **55,696** (19,957 current + actionable — the served set)

> **Every figure here carries the query that produces it. Re-run rather than quote —
> a number without its query is how this file was wrong for six months.**
> The header previously read "58 tables / 46,585 provisions (10,008 actionable)". All three
> were stale by roughly half.

| Fact | Measured 2026-08-10 | Query |
|---|---|---|
| Base tables | **118** | `SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'` |
| `regulatory_provisions` | **55,696** | `SELECT count(*) FROM regulatory_provisions` |
| …current + actionable (served) | **19,957** | `… WHERE is_current AND v2_is_actionable` |
| `dcp_setback_controls` | **1,071** | `SELECT count(*) FROM dcp_setback_controls` |
| `dcp_precinct_boundaries` | **274** | `SELECT count(*) FROM dcp_precinct_boundaries` |
| Distinct `v2_precinct_id` | **433** | `SELECT count(DISTINCT v2_precinct_id) FROM regulatory_provisions WHERE v2_precinct_id IS NOT NULL` |
| `sepp_structured_requirements` | **560** | `SELECT count(*) FROM sepp_structured_requirements` |
| `housing_sepp_standards` | **45** | `SELECT count(*) FROM housing_sepp_standards` |

For full column details, query the live catalog rather than a file:
`SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name='<table>' ORDER BY ordinal_position`.
(This line used to point at a raw schema dump that was deleted in commit `1587970d` during a repo
cleanup — the pointer outlived the file by months. Recover it with
`git show 1587970d^ --stat` if you ever want the old dump.)

## ⚠️ TABLE STATUS — READ FIRST (which table to use)

Every table below is also labelled **inside the database** (`COMMENT ON TABLE`). To see a table's status live:
`SELECT relname, obj_description(oid) FROM pg_class WHERE relname='<table>';`

**USE THESE (canonical, maintained):**
- **DCP / LEP / SEPP provision TEXT** → `regulatory_provisions` (written by `scripts/dcp_commit_approved.py`; enriched read view `regulatory_provisions_canonical`).
- **Numeric DCP CONTROLS** (setbacks, parking, landscaping, height) → `dcp_setback_controls` (written by `/internal/setback-review` + `insert_*`/`ocr_*` scripts). Feeds the conveyancing report AND the brief capacity engine.
- **Capacity / constraint arithmetic** → the Python engine `services/constraint_arithmetic.py` (which reads `dcp_setback_controls`) — not a table you query directly.
- DCP pipeline: `dcp_chapter_registry` (monitor/registry), `dcp_table_of_contents` (TOC), `dcp_review_queue` (change-review inbox), `dcp_precinct_boundaries` (precinct polygons).

**NEVER READ — frozen legacy / empty (being retired; see `~/.claude/plans/ce-dcp-table-architecture-remediation-2026-07.md`):**
- `dcp_general_requirements`, `dcp_general_provisions` — FROZEN Oct-2025 one-off snapshot, no live writer. (Only `/api/capacity/calculate` + `/api/compliance/dcp-complete` still read them; being repointed onto `dcp_setback_controls`.)
- `regulatory_provisions_clean` (and the phantom `regulatory_provisions_clean_clean`) — frozen, no writer.
- `dcp_precinct_requirements`, `dcp_precinct_provisions`, `provision_versions` — empty.
- `*_backup_*`, `*_corrupted_*`, `*_old_*` — backups / dead.

**Rule of thumb:** if code reads a NEVER-READ table, that's a bug — the maintained equivalent is listed above.

## The four largest tables — absent from this file until 2026-08-10

These were never documented here despite being, by a wide margin, the biggest things in the
database. All counts measured 2026-08-10.

```
nsw_cadastre_lots        3,220,617 rows   every lot in NSW: lotidstring, geom (SRID 4326),
                                          planlotarea. GIST index idx_cadastre_lots_geom.
lot_search_index         3,126,418 rows   lots pre-joined to planning controls (zone, height,
                                          FSR, hazard flags) so filtered lot search is possible
                                          at all. Written by the lot-index build; drift-checked
                                          by scripts/validate_lot_index.py.
spatial_overlays         1,088,573 rows   25 layer types. A SNAPSHOT, not a feed — synced_at
                                          runs 2026-04-13 to 2026-07-08 with no scheduled job.
                                          bushfire and fire_history carry NO currency_date.
complying_development_
  certificates             181,750 rows   128 councils, Jul-2018 to date, ~99.99% with
                                          coordinates. LIVE — rows arrive daily.
development_applications    62,018 rows   128 councils. Determinations only run back to
                                          2025-05-23; the eight-year depth is certificates only.
```

## cdc_lot_link — added 2026-08-10

Answers "for a lot like this one, what got approved, how long did it take, what did it cost".
Built by `scripts/build_cdc_lot_link.py` — additive, idempotent, resumable. Dropping the table
reverses it completely.

```
cdc_lot_link               181,750 rows   one per certificate
  cdc_id       uuid PK  -> complying_development_certificates.id
  lotidstring  text     the lot the certificate's coordinates fall inside
  lot_area_m2  float    denormalised from the cadastre so "lots this size" avoids a
                        3.2M-row join on every query
  dev_types    text[]   normalised development types (see the trap below)
  match_status text     matched | no_lot_at_point | no_coordinates
```

Result: **matched 178,259 (98.1%) · no_lot_at_point 3,466 (1.9%) · no_coordinates 25.**
128,098 distinct lots carry at least one certificate; 26,434 carry more than one. Unmatched rows
cluster in dense strata councils (City of Sydney 687, Parramatta 283) where the address point
falls outside the parcel polygon. A point inside stacked strata parcels takes `LIMIT 1`, so the
linked lot is the parcel footprint, not the unit.

**⚠ TRAP — `development_type` is double-encoded on 5.9% of rows.** It is `jsonb`, but in two
shapes: 171,002 rows are a jsonb *array*, and **10,748 are a jsonb *string* whose text is itself
a JSON array**. Guarding with `jsonb_typeof(...) = 'array'` and letting the rest fall through
silently blanks the "what was built" field on those 10,748, and a NULL there is indistinguishable
from a certificate that recorded no type. Decode with:

```sql
CASE jsonb_typeof(development_type)
     WHEN 'array'  THEN development_type
     WHEN 'string' THEN (development_type #>> '{}')::jsonb
END
```

Verified: that recovers all 10,748, leaving **0 undecodable, 36 explicitly-empty, 181,714 with
types**. Anything else in the codebase reading `development_type` has the same trap.

## Core Tables (Must Know)

regulatory_provisions - **55,696** rows (2026-08-10), 51 cols
  Main provision table. **19,957** current + actionable — the served set
  Use v2_precinct_id (**433** distinct), v2_dcp_part, pdf_page_image_url
  ⚠ `former_council` and `source_ref` DO NOT EXIST here — use `source_council` and `ref_number`

sepp_structured_requirements - **560** rows (2026-08-10), 12 cols
  Curated SEPP data with JSONB requirement_data and PDF links
  (this file said 3 rows from Feb-2026 until 2026-08-10)

dcp_precinct_boundaries - **274** rows (2026-08-10), 18 cols
  GeoJSON boundaries for address->precinct matching

dcp_general_requirements - 3,158 rows, 60 cols
  Structured general DCP requirements

housing_sepp_standards - **45** rows (2026-08-10), 18 cols
  SEPP Housing 2021 standards

## Precinct Data (**433** distinct v2_precinct_id as at 2026-08-10)

⚠ The per-council breakdown below is the Feb-2026 figure and totals 102. The live count is 433.
Never quote a flat precinct or council number — see `memory/verify-dcp-coverage-status.md`.

Marrickville: 47 precincts (1_ to 48_) in Part 9
Leichhardt: 43 precincts (C2.2.x.x + G1-G12)  
Ashfield: 12 precincts (Part 1 to Part 12b)

Query: SELECT DISTINCT v2_precinct_id FROM regulatory_provisions WHERE v2_precinct_id IS NOT NULL

## SEPP Housing 2021 (241 provisions extracted)

NOT in sepp_structured_requirements yet
IS in regulatory_provisions:
  - State_Environmental_Planning_Policy_(Housing)_2021__NSW_Legislation_section_X

Query accessible area parking from regulatory_provisions, NOT hardcoded rates.

## Common Patterns

Document IDs follow: {Council}_DCP_{Year}__{Part}_{Precinct}
PDF URLs: https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/pdf-pages/{sepp-name}/page-{N}.png
v2_marker values: TOD, heritage, contamination, flood, bushfire

## Satellite Product Tables (added 2026-04-06)

property_reports - satellite pipeline outputs (all 5 products)
  product, address, lat, lng, prop_id, run_date, inputs jsonb, outputs jsonb,
  confidence ('high'|'medium'|'low'), data_sources text[]
  Index: (product, address), (run_date DESC)

threat_radar_subscriptions - weekly DA monitoring subscriptions
  address, prop_id, lat, lng, email, active, last_checked, inputs jsonb
  inputs stores: { council_name, seen_application_numbers: [] }
  Unique constraint: (email, address)
  Index: active=true only

pipeline_idea_runs - GIS bot / pipeline discovery runs
  run_id, run_date, repos_scanned, tier1/2/3_repos jsonb, pipeline_combinations jsonb

## Audit Trail Tables (added 2026-05-18)

report_audit_trail - APPEND-ONLY log of every report generation (legal defensibility)
  id uuid PK, report_id uuid, pipeline_name text, pipeline_version text (git SHA),
  input_params jsonb, data_sources_queried jsonb (array of source queries with response hashes),
  intermediate_calculations jsonb, output_summary jsonb, disclaimer_version text,
  created_at timestamptz
  Index: (report_id), (pipeline_name, created_at DESC)
  Policy: INSERT only — NO UPDATE or DELETE (immutability required)
  Retention: 10 years (Design and Building Practitioners Act 2020)

disclaimer_versions - versioned disclaimer text per product
  id serial PK, pipeline_name text, version text, headline_disclaimer text,
  limitations_text text, source_attributions text, effective_from timestamptz,
  superseded_at timestamptz (NULL = active), created_at timestamptz
  Unique: (pipeline_name, version)
  Index: (pipeline_name, effective_from DESC) WHERE superseded_at IS NULL

data_source_health_checks - APPEND-ONLY log of external API health probes
  id uuid PK, run_id uuid (groups checks from one run), source_key text,
  source_name text, endpoint_url text, pipeline_names text[],
  status text ('ok'|'degraded'|'down'|'schema_changed'|'stale'),
  http_status int, response_time_ms int, response_hash text (SHA-256),
  schema_valid boolean, error_message text, metadata jsonb, checked_at timestamptz
  Index: (source_key, checked_at DESC), (run_id), (status, checked_at DESC) WHERE status != 'ok'
  Policy: INSERT only — NO UPDATE or DELETE (immutability required)
  Retention: aligned with report_audit_trail (10 years)

## Important: What's Missing

dcp_precinct_metadata: 0 rows (don't use)
dcp_precinct_provisions: Only 8 Ashfield precincts (legacy, don't use)
Use regulatory_provisions.v2_precinct_id instead
