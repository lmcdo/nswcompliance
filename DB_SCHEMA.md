# Database Schema - Complete Reference

Last Updated: 2026-02-01
Total Tables: 58
Total Provisions: 46,585 (10,008 actionable)

See DB_SCHEMA_RAW.txt for full column details.

## Core Tables (Must Know)

regulatory_provisions - 46,585 rows, 51 cols
  Main provision table. 10,008 actionable (v2_is_actionable=true)
  Use v2_precinct_id (102 precincts), v2_dcp_part, pdf_page_image_url

sepp_structured_requirements - 3 rows, 12 cols  
  Curated SEPP data with JSONB requirement_data and PDF links

dcp_precinct_boundaries - 90 rows, 18 cols
  GeoJSON boundaries for address->precinct matching

dcp_general_requirements - 3,158 rows, 60 cols
  Structured general DCP requirements

housing_sepp_standards - 33 rows, 18 cols
  SEPP Housing 2021 standards

## Precinct Data (102 total)

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

## Important: What's Missing

dcp_precinct_metadata: 0 rows (don't use)
dcp_precinct_provisions: Only 8 Ashfield precincts (legacy, don't use)
Use regulatory_provisions.v2_precinct_id instead
