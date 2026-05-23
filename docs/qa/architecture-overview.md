# PlotDetect — Technical Architecture Overview

**Last updated:** 2026-05-23

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USERS                                         │
│   Property buyers · Developers · Conveyancers · Planners · Insurers │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js on Vercel)                      │
│                                                                      │
│  Assessment UI ─── Report Pages ─── Blog ─── Tools ─── PDF Gen      │
│  /assessment       /reports/*       /blog     /tools    react-pdf    │
│                                                                      │
│  API Routes (frontend-nextjs/app/api/)                               │
│  ├── /compliance/*     → regulatory provision queries                │
│  ├── /dcp/*            → structured DCP controls                     │
│  ├── /property         → address lookup + spatial overlays           │
│  ├── /reports/*        → satellite product API calls                 │
│  ├── /canibuildit      → permissibility + compliance check          │
│  └── /sepp/*           → SEPP exempt/complying provisions            │
└────────────┬──────────────────────────────┬─────────────────────────┘
             │                              │
             ▼                              ▼
┌────────────────────────┐    ┌────────────────────────────────────────┐
│   SUPABASE (PostgreSQL) │    │  SATELLITE SERVICES (Python on Railway) │
│                          │    │                                        │
│  regulatory_provisions   │    │  bushfire_prescreen.py                 │
│  (46,585 rows)           │    │  flood_truth.py                        │
│                          │    │  shadow_detector.py                    │
│  dcp_setback_controls    │    │  solar_yield.py                        │
│  (999 rows, 16 types)    │    │  threat_radar.py                       │
│                          │    │  granny_flat.py                        │
│  spatial_overlays        │    │  pre_da_history.py                     │
│  (128 LGAs, 14 types)   │    │  climate_risk_score.py                 │
│                          │    │                                        │
│  dcp_table_of_contents   │    │  audit_trail.py (append-only logging)  │
│  lga_registry            │    │  report_image.py (map rendering)       │
│  property_reports        │    │                                        │
│  report_audit_trail      │    │  Each pipeline:                        │
│  disclaimer_versions     │    │  1. Receives address/coordinates       │
│  data_source_health      │    │  2. Queries govt APIs + DB overlays    │
│                          │    │  3. Computes analysis                  │
│  ~42 tables total        │    │  4. Returns structured JSON            │
│  Single production DB    │    │  5. Logs to audit_trail                │
│  Changes are live        │    │  6. Stores in property_reports         │
└────────────┬─────────────┘    └───────────────┬────────────────────────┘
             │                                  │
             │                                  ▼
             │                  ┌────────────────────────────────────────┐
             │                  │     EXTERNAL DATA SOURCES              │
             │                  │                                        │
             │                  │  NSW Planning Portal API               │
             │                  │  ├── layerintersect (zone, FSR, HOB)   │
             │                  │  ├── zone_full (permissibility)        │
             │                  │  └── legislation_url (source links)    │
             │                  │                                        │
             │                  │  ePlanning MapServer (6 services)      │
             │                  │  ├── Heritage conservation areas       │
             │                  │  ├── Flood planning areas              │
             │                  │  ├── Bushfire prone land               │
             │                  │  └── Biodiversity, acid sulfate, etc   │
             │                  │                                        │
             │                  │  RFS ArcGIS REST (bushfire BAL)        │
             │                  │  BOM SILO (climate data)               │
             │                  │  Google Solar API (panel yield)        │
             │                  │  DEA WOfS (water observation freq)     │
             │                  │  Geoscience AU DEM (elevation)         │
             │                  │  Sentinel-1 SAR (change detection)     │
             │                  │  15 endpoints, monitored daily         │
             │                  └────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ENRICHMENT PIPELINE                                │
│                                                                      │
│  rule_extraction_pipeline.py  → v2_extracted_rules                   │
│  applicability_tagger.py      → v2_applicable_dev_types/zones        │
│  layer_topic_tagger.py        → v2_topic, v2_layer classifications   │
│  actionable_classifier.py     → v2_is_actionable (true/false)        │
│                                                                      │
│  Runs offline. Enriches regulatory_provisions in Supabase.           │
│  ~80% complete across all instruments.                               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Deployment Topology

| Component | Host | URL |
|-----------|------|-----|
| Frontend + API routes | Vercel | canibuildit.com.au / verify.plotdetect.com.au |
| Satellite services | Railway | Internal API endpoints |
| Database | Supabase | PostgreSQL (single production instance) |
| EnvelopeView (3D) | Vercel | envelope.plotdetect.com.au |
| Data source monitor | GitHub Actions | Cron daily 06:00 UTC |
| Legislation monitor | GitHub Actions | Weekly |

---

## Data Flow: Property Assessment

```
User enters address
        │
        ▼
NSW Planning Portal API
  → zone, FSR, HOB, lot_size, legislation_url
        │
        ▼
Supabase: spatial_overlays
  → heritage, flood, bushfire, biodiversity, acid sulfate,
    ANEF, TOD, contamination, key sites (14 overlay types)
        │
        ▼
Supabase: regulatory_provisions
  → SEPP provisions (exempt/complying dev codes)
  → LEP provisions (zone-specific controls)
  → DCP provisions (council-specific development controls)
        │
        ▼
Supabase: dcp_setback_controls
  → Structured numeric values (setbacks, parking, landscaping,
    deep soil, site coverage, tree canopy, solar access hours,
    bicycle parking, communal open space, private open space)
        │
        ▼
Frontend renders 4-layer compliance view:
  Tab 1: SEPP (state-level)
  Tab 2: LEP (local plan)
  Tab 3: Questions (zone permissibility)
  Tab 4: DCP (council controls with structured numerics)
```

---

## Security Posture

| Control | Implementation |
|---------|----------------|
| Authentication | Supabase Auth (JWT) |
| Database access | Row-level security policies; API routes use service role |
| Secret management | Environment variables via Vercel/Railway; not in source |
| HTTPS | Enforced on all endpoints (Vercel + Railway) |
| Dependency scanning | GitHub Dependabot alerts |
| Git hooks | Enforced commit classification, test gates, language audit |
| Audit trail | Append-only table, no UPDATE/DELETE, SHA-256 response hashing |
| Data integrity | No fake/placeholder data policy; all values from authoritative sources |
| Code review | Branch protection; all changes via PR with QA report |

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Next.js 16 (TypeScript) | UI, API routes, PDF generation |
| Backend | Python 3.11 | Satellite pipelines, enrichment, scripts |
| Database | PostgreSQL (Supabase) | All persistent storage |
| PDF generation | react-pdf | Downloadable property reports |
| Maps | Leaflet, ArcGIS REST | Spatial visualisation |
| Testing | pytest (415 tests) | Unit + integration tests |
| CI/CD | Vercel (frontend), Railway (services), GitHub Actions (monitoring) |
| Version control | Git + GitHub | Branch protection, PR workflow |
