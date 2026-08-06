# NDIS Technical & Compliance Scope — What Must Be Built, Verified, Licensed and Legally Covered Before Shipping OEM Rules Feed v1 + Consultant Seat v1

**Status:** SCOPING ONLY. No production code, no external commitments.
**Date:** 2026-08-06.
**Branch:** `claude/ndis-compliance-prompt-36lcen`.
**Author scope:** repository read + open-web research, no privileged access to Federal Register / NDIS Commission / NDIA hosts (all 403 from this sandbox, see Z3).
**Companion documents (read first, cited throughout):**
- `docs/rules-engine-market-scan-phase0-1.md` — 21-domain fit scan.
- `docs/rules-engine-market-scan-phase2.md` — top-two deep dive + NDIS mini-dive.
- `docs/ndis-deep-dive-modules-1-5.md` — corpus + market + demand.
- `docs/ndis-deep-dive-modules-6-11-final.md` — SKUs, GTM, red team, verdict.

Cited inline as **[P0], [P2], [M1-5], [M6-11]**.

**Verdict this document assumes as input (from [M6-11]):** GO on NDIS, OEM Rules Feed as SKU 1, Consultant Seat as SKU 2, Provider Self-Serve as SKU 3 (deferred/conditional), Board SKU as SKU 4 (Phase 2 only). Everything below is the delta between the current NSW-planning engine and a shippable v1.

---

## TECHNICAL INVESTIGATION

### T1. Engine Capability Inventory

Method: every file counted by verdict, rebuild hours estimated from lines-of-code, per-module purpose, and the prior 3–6-week port estimate ([M6-11] §Module 7). Hours are `[INFERENCE]` unless otherwise noted; derivation: an NSW-planning-specific module gets its full line count rebuilt at ~30 lines/hour of design + code + tests; a domain-neutral module gets a `PORTS DIRECTLY` verdict with 0–8 hours for import-graph fix-ups. Groupings collapse related file families (all satellite/geospatial into one row) to keep the table readable.

#### T1.a `services/` — 84 files, 36,193 LOC

Grouped into families; every file is verdicted at the family level. Any file called out individually appears on its own row.

| Path | Purpose | Verdict | Rebuild hrs | Notes |
|---|---|---|---:|---|
| `services/audit_trail.py` (205 LOC) | Append-only audit log for every report generation, hashed inputs, deploy SHA | **PORTS DIRECTLY** | 4 | Domain-neutral. Rename table target, retarget from `property_reports` → `ndis_feed_requests` |
| `services/execution_manifest.py` (73 LOC) | "Cite the object the computation actually consumed, not the object named in a config" | **PORTS DIRECTLY** | 4 | Directly applicable: cite the compilation the clause was rendered from, not the F-number pointer |
| `services/brief_manifest.py` (701 LOC) | Per-brief source manifest, DataField → source-instrument mapping | **PORTS WITH MODIFICATION** | 40 | The DataField schema (LEP zone, DCP setback, SEPP standard) has to be re-typed as NDIS-flavoured (F-instrument, section, subsection). Structural pattern reused verbatim |
| `services/extracted_data_integrity.py` (830 LOC, 26 functions) | Generic fabricated-value / conflicting-value / value-absent-from-source detector, table-agnostic per config | **PORTS DIRECTLY** | 8 | Cited [M6-11] §T7 as the reason the port is 3–6 wk not 3–6 mo. Config passed in per-table; no NSW-specific logic in this file |
| `services/clause_citation_inline.py` (198 LOC) | Formats verbatim clause + citation for inline output | **PORTS DIRECTLY** | 4 | Format string is `"{instrument} s{section}"` — retarget from LEP/DCP to Act/Rules |
| `services/compliance_api_server.py`, `services/enhanced_compliance_api.py` | FastAPI shell — routes, auth middleware, error handling | **PORTS WITH MODIFICATION** | 32 | Shell + middleware kept; every domain route (`/nsw_planning/*`) replaced with `/clauses`, `/instruments`, `/amendments` |
| `services/db_config.py` | psycopg2 connection factory | **PORTS DIRECTLY** | 2 | Point at NDIS Supabase instance |
| `services/version_manager.py` (269 LOC) | SEPP/LEP/DCP versioning + `as_at` helpers | **PORTS WITH MODIFICATION** | 24 | Semantics identical (a compilation is in force from X to Y). Enum values change; per-instrument fetch adapter is new |
| `services/provision_search.py` | SQL-backed provision text search | **PORTS DIRECTLY** | 6 | Retarget from `regulatory_provisions` (NSW) to `ndis_clauses` |
| `services/full_clause_extractor.py`, `services/full_clause_langextract_config.py` | AI-assisted clause extraction from PDFs using langextract | **PORTS WITH MODIFICATION** | 40 | Extractor + config split lets you swap the domain prompt; PDF handling reused |
| `services/live_compliance_engine.py`, `services/universal_regulatory_engine.py` | Query LightRAG / AutoSchemaKG data for a specific NSW property | **DELETE (geospatial not needed)** | 0 | Property-scoped; NDIS has no equivalent |
| `services/nsw_planning_api.py`, `services/portal_constraints.py`, `services/arcgis_client.py`, `services/nsw_imagery.py`, `services/dem_service.py`, `services/sentinel2.py` | NSW Planning Portal + ArcGIS + Sentinel-2 + DEM clients | **KEEP AS PARALLEL PRODUCT** | 0 | Not touched. Reused by the retained NSW engine |
| `services/flood_truth.py`, `services/climate_risk_*.py` (3 files), `services/bushfire_prescreen.py`, `services/shadow_*.py` (2 files), `services/solar_yield.py`, `services/reverse_shadow.py`, `services/threat_radar.py`, `services/terrain_analysis.py`, `services/spike_samgeo_buildings.py`, `services/spike_solar_samgeo.py`, `services/pre_da_history.py`, `services/transport_proximity_detector.py`, `services/gsp_servicing.py`, `services/drawdown_verify.py`, `services/lot_search.py`, `services/lot_dimensions.py`, `services/geometry_checks.py`, `services/address_identity.py`, `services/lga_lookup.py`, `services/strata_lookup.py`, `services/lec_collector.py`, `services/da_outcome.py`, `services/vg_comparables.py` | Satellite / geospatial / cadastre / property intelligence subsystem | **DELETE (geospatial not needed)** | 0 | Explicitly out of scope per prompt §Context |
| `services/setback_calculator.py`, `services/authoritative_setback_calculator.py`, `services/dcp_controls_api.py`, `services/compound_constraints.py`, `services/constraint_arithmetic.py`, `services/constraint_models.py`, `services/development_permissions_db.py`, `services/exempt_screening.py`, `services/cdc_screen.py`, `services/cdc_screen_api.py`, `services/upzoning_check.py`, `services/basix_compliance_checker.py`, `services/granny_flat.py`, `services/housing_sepp_eligibility.py`, `services/hierarchy_resolver.py`, `services/special_provisions_integration.py`, `services/special_provisions_processor.py`, `services/sepp_quantitative_extractor.py`, `services/conveyancing.py`, `services/property_intelligence_4stack.py`, `services/intelligence_brief.py`, `services/brief_narration.py`, `services/brief_overlay_api.py`, `services/brief_templates.py`, `services/council_validation_service.py`, `services/clause_number_cleaner.py`, `services/precise_setback_calculator.py.backup`, `*.backup` files | NSW planning controls, setback maths, brief renderer, capacity engine | **KEEP AS PARALLEL PRODUCT** | 0 | Continues to serve existing NSW customers unchanged |
| `services/autoschema_kg_query.py`, `services/integrated_multimodal_query.py.backup`, `services/database_autoschema_query.py.backup` | Legacy AutoSchemaKG / multimodal query paths | **DELETE (not needed)** | 0 | `.backup` files should also be removed at port time |
| `services/forum_webhook.py`, `services/rss_proxy.py` | Community forum + RSS bridging | **KEEP AS PARALLEL PRODUCT** | 0 | Unrelated to compliance surface |

**`services/` totals:** PORTS DIRECTLY 6 files (~28 hrs). PORTS WITH MODIFICATION 5 files (~140 hrs). DELETE 25 files (0 hrs). KEEP AS PARALLEL 48 files (0 hrs).

#### T1.b `enrichment/` — extractor pipeline

| Path | Purpose | Verdict | Rebuild hrs |
|---|---|---|---:|
| `enrichment/pipeline.py` | Phase-1 numeric extraction orchestrator | **PORTS WITH MODIFICATION** | 16 |
| `enrichment/rule_extraction_pipeline.py` | Deterministic-stage (2a) + validation-stage (2c) orchestrator with LLM retry gate | **PORTS DIRECTLY** | 8 |
| `enrichment/extractors/numeric_extractor.py` | Numeric value extractor | **PORTS DIRECTLY** | 4 |
| `enrichment/extractors/marker_extractor.py` | Marker (v2_marker) extractor | **PORTS WITH MODIFICATION** | 12 |
| `enrichment/extractors/reference_extractor.py` | Cross-reference extractor | **PORTS DIRECTLY** | 6 |
| `enrichment/extractors/rule_schema.py` | ExtractedRule shape | **PORTS WITH MODIFICATION** | 8 |
| `enrichment/extractors/compliance_type_classifier.py`, `enrichment/extractors/type_classifier.py`, `enrichment/extractors/actionable_classifier.py` | Classifiers | **PORTS WITH MODIFICATION** | 24 |
| `enrichment/extractors/applicability_tagger.py`, `enrichment/extractors/site_condition_tagger.py`, `enrichment/extractors/layer_topic_tagger.py` | NSW-specific applicability + site-condition tags | **NDIS-SPECIFIC REBUILD** | 40 |
| `enrichment/extractors/extract_secondary_setbacks_*.py` (3 files) | Setback extraction | **DELETE (geospatial not needed)** | 0 |
| `enrichment/extractors/gemini_actionability_classifier.py` | LLM actionability signal | **PORTS DIRECTLY** | 4 |
| `enrichment/precompute_amenity.py` | Amenity precompute | **DELETE** | 0 |

**`enrichment/` totals:** PORTS DIRECTLY 4 files (~22 hrs). PORTS WITH MODIFICATION 5 files (~60 hrs). NDIS-SPECIFIC REBUILD 3 files (~40 hrs). DELETE 4 files.

#### T1.c `src/` — models, processing, regulatory

| Path | Purpose | Verdict | Rebuild hrs |
|---|---|---|---:|
| `src/models.py` | Pydantic models: `FormerCouncilArea`, `SetbackRule`, `DocumentSource` | **NDIS-SPECIFIC REBUILD** | 12 | Same pattern (typed models + provenance fields), NDIS domain object graph |
| `src/processing/rule_generator.py` | RAG-extracted-data → compliance-rule generator | **PORTS WITH MODIFICATION** | 24 |
| `src/processing/rag_enhanced_processor.py`, `src/processing/rag_processor.py`, `src/processing/simple_pdf_processor.py`, `src/processing/schema_extractor.py` | PDF processing / RAG shell | **PORTS DIRECTLY** | 20 |
| `src/processing/spatial_mapper.py` | Geometry-to-council-area mapping | **DELETE (geospatial not needed)** | 0 |
| `src/regulatory/document-router.ts`, `src/regulatory/hierarchy.ts` | TS document router + hierarchy | **PORTS WITH MODIFICATION** | 16 |
| `src/utils/document_finder.py` | File discovery | **PORTS DIRECTLY** | 4 |

**`src/` totals:** PORTS DIRECTLY 5 files (~24 hrs). PORTS WITH MODIFICATION 3 files (~40 hrs). NDIS-SPECIFIC REBUILD 1 file (~12 hrs). DELETE 1 file.

#### T1.d `scripts/` — 249 scripts (grouped)

| Group | Verdict | Rebuild hrs | Notes |
|---|---|---:|---|
| `scripts/liability_language_check.py` (212 LOC) + `scripts/qa_gate.py` (1442 LOC) + `scripts/check_test_baselines.py` + `scripts/brief_field_coverage_ratchet.py` (186 LOC) | **PORTS DIRECTLY** | 16 | Domain-neutral gates. See T7 for per-gate audit |
| `scripts/validate_schema_contract.py` (632 LOC) + `scripts/validate_controls_provenance.py` (299 LOC) + `scripts/validate_control_source_values.py` (447 LOC) + `scripts/verify_extraction_fidelity.py` (219 LOC) + `scripts/lint_fabricated_verdicts.py` (267 LOC) + `scripts/pdf_text_hash.py` (59 LOC) | **PORTS WITH MODIFICATION** | 80 | Table names + baseline files change; check logic reused |
| `scripts/legislation_monitor.py` (849 LOC), `scripts/regulatory_freshness_monitor.py`, `scripts/dcp_watchdog.py`, `scripts/run_monitors.py` | **NDIS-SPECIFIC REBUILD** | 60 | Fetch target changes from NSW-legislation/AustLII to Federal Register; monitoring loop reused; see T4 |
| `scripts/dcp_extract_changed.py` (3,445 LOC), `scripts/dcp_commit_approved.py`, `scripts/dcp_preflight.py` (963 LOC), `scripts/dcp_fidelity_gate.py`, `scripts/dcp_quality_report.py` | **NDIS-SPECIFIC REBUILD** (of the pattern) | 120 | The pattern (extract → preflight → review → commit → fidelity gate → quality report) transfers; the extractor internals are DCP-specific and get rewritten against F-instrument HTML/PDF |
| Baseline JSONs (`mutation-baselines.json`, `schema_contract_baseline.json`, `brief_field_coverage_baseline.json`, `control_source_values_baseline.json`) | **PORTS WITH MODIFICATION** | 8 | Format reused; contents empty and grown as NDIS gates catch things |
| Everything named `*_lep_*`, `*_dcp_*` council-specific, `*_zone_*`, `*_precinct_*`, `*_flood_*`, `*_bushfire_*`, `*_solar_*`, `*_shadow_*`, `*_lot_*`, `*_cadastre_*`, `*_conveyancing_*`, `*_r2_upload_*`, `*_ingest_spatial_*`, `*_backfill_*` | **KEEP AS PARALLEL PRODUCT** | 0 | Continues serving existing NSW work |

**`scripts/` totals:** PORTS DIRECTLY 4 (~16 hrs). PORTS WITH MODIFICATION ~11 (~88 hrs). NDIS-SPECIFIC REBUILD ~10 (~180 hrs). KEEP AS PARALLEL rest.

#### T1.e `frontend-nextjs/` — 47 top-level app routes, 55 API routes

| Group | Verdict | Rebuild hrs |
|---|---|---:|
| `frontend-nextjs/app/layout.tsx`, `globals.css`, `not-found.tsx`, auth pages, `login/`, `contact/`, `privacy/`, `terms/`, `about/`, `pricing/` | **PORTS WITH MODIFICATION** | 32 |
| `frontend-nextjs/components/pdf/*` (10 files, uses `@react-pdf/renderer` 4.5.1) | **PORTS WITH MODIFICATION** | 48 |
| `frontend-nextjs/components/property/*`, `components/compliance/*`, `components/development/*`, `components/dcp-*`, `components/heritage/*`, `components/climate/*`, `components/homepage/*`, `components/browse/*` | **KEEP AS PARALLEL PRODUCT** | 0 |
| `frontend-nextjs/app/api/authoritative/`, `api/dcp/`, `api/compliance/`, `api/environmental/`, `api/heritage/`, `api/housing-sepp/`, `api/cdc/`, `api/canibuildit/`, `api/capacity/`, `api/adg/`, `api/instrument-currency/`, `api/documents/`, `api/dcp-review/`, `api/dcp-interest/`, `api/setbacks/`, `api/upzoning/`, `api/spatial/`, `api/tod/`, `api/pathway/`, `api/permissibility/`, `api/servicing/`, `api/definitions/`, `api/check-*`, `api/browse/`, `api/versions/`, `api/verify-interest/`, `api/health/`, `api/debug-*/`, `api/db-verify/`, `api/environmental/`, `api/da-sessions/`, `api/feedback/`, `api/guides/`, `api/procedural/`, `api/provisions/`, `api/intelligence-brief/`, `api/brief-overlay/`, `api/clause/`, `api/reports/` | **KEEP AS PARALLEL PRODUCT** | 0 |
| `api/admin/`, `api/ai/`, `api/og/`, `api/stripe/`, `api/telegram/`, `api/internal/`, `api/q/`, `api/test-contextual-guidance/` | **PORTS DIRECTLY** | 12 | Cross-cutting admin/AI/payments/OG rendering |
| New NDIS routes needed (see T5/T6) | **NDIS-SPECIFIC REBUILD** | 240 | OEM `/api/oem/*`, Consultant seat pages + API |

**`frontend-nextjs/` totals:** PORTS DIRECTLY ~4 (~12 hrs). PORTS WITH MODIFICATION shell + PDF (~80 hrs). NDIS-SPECIFIC REBUILD new OEM + Seat surface (~240 hrs). KEEP AS PARALLEL most of it.

#### T1.f Summary and coupling call-outs

**Total port effort across services + enrichment + src + scripts + frontend:**

| Verdict | Hours (rounded) |
|---|---:|
| PORTS DIRECTLY | ~118 hrs (~3 weeks at 40 hrs/wk) |
| PORTS WITH MODIFICATION | ~408 hrs (~10 weeks) |
| NDIS-SPECIFIC REBUILD | ~652 hrs (~16 weeks) |
| **TOTAL engine + minimum-viable UI** | **~1,178 hrs ≈ 29 weeks solo** |

That is the ceiling estimate — full port + full corpus + full OEM + full Seat. The MVP path in T10 is much less because it drops the full corpus and defers the Seat until after the OEM signs one licensee.

**NSW-planning primitives that leak into modules that ought to be domain-neutral** (X1 addresses each):
- `services/version_manager.py` — the `DocumentType` enum hardcodes `{SEPP, LEP, DCP}`. Should be a table-driven registry.
- `enrichment/extractors/applicability_tagger.py`, `site_condition_tagger.py`, `layer_topic_tagger.py` — coupled to NSW zone/precinct semantics.
- `services/nsw_planning_api.py` — a nominally-generic name that only serves the NSW Planning Portal. Not a leak into other modules, but a naming trap for a future dev.
- `src/models.py` — `FormerCouncilArea` enum (`ASHFIELD`, `LEICHHARDT`, `MARRICKVILLE`) is the strongest domain coupling in the whole `src/` tree. Any rebuild here should replace with a `Jurisdiction` enum or drop entirely.
- `scripts/schema_contract_baseline.json` — the baseline is over the NSW DB schema; the tool ports directly but the baseline must be regenerated per-DB.

---

### T2. Extraction Pipeline Scoping — Tier A F-instruments

The ~10 Tier A instruments were fixed as input by [M1-5] §Module 1. This section scopes each one.

**Sandbox constraint (see Z3):** every URL under `legislation.gov.au` returned HTTP 403 to WebFetch in this session (verified 2026-08-06), matching the pattern the prior four documents documented. Per-instrument page counts, section counts and licence notices are `[UNVERIFIED-PRIMARY]` in this document and must be re-fetched from an AU home network before build. Search-index-level facts from [M1-5] §Module 1 are cited unchanged; nothing below invents a fact the prior docs did not already state.

#### T2.a Per-instrument scoping

Fetch strategy shorthand: **HTML-primary** = fetch `/{f_number}/latest/text` HTML; **PDF-fallback** = fetch `/{f_number}/latest/pdf` and text-extract; **XML** = the compilation XML export at `/{f_number}/latest/xml` if published for that instrument.

| Instrument | F/C-number | Fetch | Parser | Pages (est) | Clauses (est) | Defined terms | Cross-refs | Extractor hrs |
|---|---|---|---|---:|---:|---|---|---:|
| NDIS Act 2013 | `C2013A00020` | HTML-primary, PDF-fallback | HTML sectionizer + defined-term extractor | ~380 `[UNVERIFIED-PRIMARY]` | ~250 sections + subs `[INFERENCE]` | 3 Dictionary (s9) + interpretive | To Rules by name; to other Cth Acts (Age Discrimination Act, ACL) | 40 |
| Code of Conduct Rules | `F2018L00629` | HTML-primary | Simple sectionizer (8 conduct elements) | ~10 | ~15 rules | 4 (via s6 Act dictionary) | To Act s73V, s73J | 12 |
| Provider Registration & Practice Standards Rules | `F2018L00631` | HTML+PDF (schedules are the Practice Standards modules) | Schedule-aware — each schedule is a Practice Standards module | ~120 `[UNVERIFIED-PRIMARY]` | ~180 rules + Schedule 1-6 modules | ~30 | To Quality Indicators; to Act s73E, s73T, s73V; new SIL supp module (1 Jul 2026) | 60 |
| Restrictive Practices & Behaviour Support Rules | `F2018L00632` | HTML-primary | Sectionizer + BSP-lifecycle mapper | ~40 | ~35 rules | ~15 (regulated practice types) | To state authorisation regimes (per-jurisdiction matrix); to Incident Rules | 32 |
| Incident Management & Reportable Incidents Rules | `F2018L00633` | HTML-primary | Sectionizer + timeframe extractor (24-hr Immediate, 5-business-day) | ~30 | ~30 rules | ~10 | To Act s73Z; to Restrictive Practices Rules | 24 |
| Complaints Management & Resolution Rules | `F2018L00634` | HTML-primary | Sectionizer + timeframe extractor | ~15 | ~25 rules | ~5 | To Act s73X | 20 |
| Quality Indicators Guidelines | `F2018N00041` | HTML | Indicator-list parser (per-standard) | ~50 | ~120 indicators | domain terms | Back-references to Practice Standards | 32 |
| Approved Quality Auditors Rules 2025 | `F2025L01383` | HTML-primary | Sectionizer + auditor-obligations mapper | ~35 `[INFERENCE]` | ~40 rules | ~8 | To Practice Standards Rules; replaces 2018 Guidelines architecture | 24 |
| NDIS Supports Transitional Rules 2024 | `F2024L01257` | HTML-primary — TAG SUNSET-PENDING | Simple sectionizer + transition-date extractor | ~20 `[INFERENCE]` | ~15 rules | | To Act s10 | 12 |
| Worker Screening Rules | `F2018L00887` (principal, in force effective 31/07/2018 — F-number confirmed 2026-08-06 from Federal Register search). **Extract-on-hand is compilation No. 4 (2021) at `docs/corpus-primary-sources/text/F2021C00788.txt`; verify no newer compilation exists before the extractor is coded, otherwise re-fetch and re-extract — see Z1 decision on freshness and Z3.** | HTML-primary | Sectionizer + jurisdiction-mapper | ~50 `[INFERENCE]` | ~40 rules | ~10 | To state worker-screening Acts; to Act s73L | 32 |
| Procedural Fairness Guidelines *(Notifiable Instrument — Ni tag)* | `F2018N00155` (principal; currently in force via compilation `F2026C00166`, comp #1 dated 28/01/2026 — F-number and compilation confirmed 2026-08-06 from Federal Register search + founder-provided PDF extract at `docs/corpus-primary-sources/text/F2026C00166.txt`) | HTML/PDF — **Notifiable Instrument variant of the OPC template** (see note below) | Non-obligation extract | ~20 `[INFERENCE]` (950 lines in extracted text) | ~20 procedural | | To Act s73B, s73Z (banning) | 18 (+2 vs L-Rules baseline for Ni template variance) |

**Per-instrument extractor hours: ~306 hrs ≈ 7.65 person-weeks** (the +2 hrs vs the previous rollup is the Notifiable-Instrument template variance for F2018N00155 called out above; noise-floor delta, no change to the person-week rollup).

That is the greenfield estimate. Because the Provider Registration & Practice Standards Rules (F2018L00631) alone accounts for ~60 hrs — and its Schedules are the Practice Standards modules that drive the whole audit-pack downstream product — the MVP demo slice ([M6-11] §Module 7: "6-week SIL slice = Practice Standards Core + SIL supplementary + Restrictive Practices + Quality Indicators Core") corresponds to F2018L00631 + F2018L00632 + F2018N00041 + Code of Conduct = ~136 hrs ≈ **3.4 person-weeks of extractor work**. Add 40 hrs of amendment-monitoring infrastructure = ~4.4 weeks — inside the [M6-11] "MVP subset ~5.5 person-weeks corpus" number, within the noise floor.

**Notifiable-Instrument (Ni) template variance note.** Two Tier A documents use the `N` collection tag rather than `L`: F2018N00041 (Quality Indicators Guidelines) and F2018N00155 (Procedural Fairness Guidelines). OPC's Notifiable-Instrument template shares the front-matter block with the Legislative-Instrument template but differs in endnote layout and in the "made under" attribution formatting. The delta is small — probably a shared parser with a per-tag branch on the endnote block — and is estimated at +2 hours per Ni instrument versus the L-Rules baseline. The +2 hours is baked into F2018N00155's row above; F2018N00041's row already uses an indicator-list parser that sidesteps most of the template-variance surface, so no adjustment for that one.

#### T2.b Corpus-wide extractor architecture

```
                    ┌─────────────────────────────────────────┐
                    │  Federal Register of Legislation        │
                    │  (legislation.gov.au)                   │
                    │                                         │
                    │  Per-F-number canonical URLs:           │
                    │  /{fnum}/latest/{text|pdf|xml}          │
                    └──────────────┬──────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │  fetch_manager               │
                    │  - polite retry, respects    │
                    │    Retry-After                │
                    │  - source_hash on every       │
                    │    fetch                      │
                    │  - stores raw + snapshot ts   │
                    └──────────────┬──────────────┘
                                   │  raw HTML/PDF/XML + hash
                    ┌──────────────▼──────────────┐
                    │  per-instrument parser       │
                    │  (dispatch on f_number)      │
                    │                              │
                    │  Common primitives (reused): │
                    │  - sectionizer               │
                    │  - defined_term_extractor    │
                    │  - cross_ref_extractor       │
                    │  - numeric_value_extractor   │
                    │  - timeframe_extractor       │
                    └──────────────┬──────────────┘
                                   │  parsed clauses
                    ┌──────────────▼──────────────┐
                    │  verification gates          │
                    │  (port of existing 10)       │
                    │  - fabricated-value          │
                    │  - conflicting-value         │
                    │  - value-absent-from-source  │
                    │  - source-text-hash          │
                    │  - controls-provenance       │
                    │  - liability-language        │
                    └──────────────┬──────────────┘
                                   │  gated clauses
                    ┌──────────────▼──────────────┐
                    │  human-in-the-loop review    │
                    │  (dcp_review_queue → ndis_)  │
                    └──────────────┬──────────────┘
                                   │  approved
                    ┌──────────────▼──────────────┐
                    │  ndis_clauses (verbatim)     │
                    │  + compilation + history +   │
                    │  cross_ref tables (T3)       │
                    └──────────────────────────────┘
```

**Licence-parsing simplification (per C1.a finding).** Because zero of the 15 extracted Tier A PDFs carry a per-document copyright notice (verified 2026-08-06), the extractor does NOT need per-document licence-parsing logic. Licence is stored per-source at ingest time from a host-keyed lookup table:

```
LICENCE_BY_HOST = {
    'legislation.gov.au':  ('cc-by-4.0',       'https://www.legislation.gov.au/...'),
    'ndis.gov.au':         ('cc-by-nc-3.0-au', 'https://www.ndis.gov.au/policies-rules-and-legal/using-our-websites-and-social-media/copyright'),
    'ndiscommission.gov.au': ('cc-by-nc-3.0-au', 'https://www.ndis.gov.au/...'),  # baseline pending per-doc capture — see Z3
}
```

At ingest time, the fetch_manager writes `instrument.licence_status`, `instrument.licence_notice_url`, and `instrument.attribution_string` from this table by host, and does not attempt to parse the PDF for a licence notice. This simplifies the licence-tracking schema recommendation from C2 to a one-time seed of the lookup table rather than a per-fetch parse. The `per-doc-override` value in `licence_status` remains available for future documents that DO carry a per-doc notice, but is dormant for the Tier A corpus as verified today.

#### T2.c Corpus totals reconciled to [M6-11]

Corpus extraction (full Tier A): T2.a rolls up to **~304 hrs ≈ 7.6 person-weeks**. [M6-11] §Module 7 estimated **~13–14 person-weeks** for the same. The delta is ~6 person-weeks and is real: [M6-11]'s number includes verification-gate wiring, human-in-loop review time (not just extractor authoring), and NDIS-specific rebuild of the applicability-tagger family. When those are added back (T7 gate ports ~80 hrs; T1.b applicability rebuild 40 hrs; reviewer sessions ~120 hrs at 0.5 hr per clause × ~240 reviewable clauses) the corpus total lands at **7.6 + 80/40 + 40/40 + 120/40 ≈ 13 person-weeks** — matching [M6-11] within one week. This document does not overwrite the [M6-11] estimate.

MVP demo slice (Practice Standards Core + SIL supp + Restrictive Practices + Quality Indicators Core): 3.4 wk extractor + 1.0 wk monitoring + 1.0 wk gates + 0.5 wk review ≈ **~6 person-weeks corpus**, aligned to [M6-11] §Module 7's "MVP subset ~5.5 person-weeks corpus" within the noise floor.

---

### T3. Effective-Date Engine Specification

#### T3.a Point-in-time semantics

Every clause resolves through `as_at(t)`:
- `as_at(t)` returns the row from `clause_history` where `t ∈ [compilation.in_force_from, compilation.in_force_to)` AND the clause is present in that compilation (i.e. not REPEALED at time `t`).
- Cross-references resolve at the **same** `t`: when Incident Rules s16 refers to Restrictive Practices Rules, the target compilation is the one in force at `t` (this is the "cross-reference resolution at a point in time" call-out in [M6-11] §Module 7 — the NSW engine already solves this at 50× the scale).
- **Three-state, never two:** `PRESENT`, `REPEALED`, `NEVER_EXISTED` — the NSW-engine discipline (see `scripts/validate_schema_contract.py:37-66` on how three-state discipline prevents silent green ticks).

#### T3.b Compilation-diff pipeline design

1. Poll the Federal Register for the watched F-numbers (see T4 for cadence).
2. On any new `compilation_no`, download HTML + PDF + XML, hash each, write to `compilation(id, instrument_id, compilation_no, in_force_from, in_force_to, source_url, source_hash)`.
3. Re-parse into a **candidate** `clause_history` set (never overwriting the current set).
4. Compute a clause-level diff against the previous compilation: `NEW | AMENDED | REPEALED | RENUMBERED | UNCHANGED`.
5. **Manual review gate** (see T4.c). Only approved rows land in the served table.
6. On approval, write the new `clause_history` rows and update `clause.current_compilation_id` for changed clauses; publish an amendment event on the webhook bus (T5.c).

#### T3.c Transitional rules and F2024L01257

`F2024L01257` (NDIS Supports Transitional Rules 2024) is tagged **SUNSET-PENDING** per [M1-5] §Module 1. The engine must:
- Store the sunset date as a first-class column on `instrument`.
- Emit a monitoring alert 90/60/30 days before sunset.
- After sunset, mark all clauses in the instrument as `REPEALED` at `t = sunset_date` unless a replacement instrument is published earlier.
- Never silently drop transitional rules — they may still be referenced by an audit-time question about a period before sunset.

#### T3.d Stock-in-trade / grandfathering windows

The NSW engine's PEAL-style transition handling (mandatory-from date + stock-in-trade cutoff date + old-vs-new dual-currency window) ports directly. In NDIS the analogue is:
- Practice Standards modules with staged commencement (SIL supplementary module 1 Jul 2026; the graduated-registration Rules for 1 Jul 2027 which are NOT YET MADE per [M1-5] §Module 1).
- Worker screening renewal wave — 5-year clearances issued 2021 falling due Feb 2026 → 2027.

Verdict: **PORT the existing NSW mechanism**, don't rebuild. The mechanism is data (a `transitional_rule` table with `applies_from`, `applies_to`, `participant_scope`, `source_clause`), not code.

#### T3.e Minimum schema

Copied verbatim from [M6-11] §Module 7 (already validated) with two additions justified by T3.a and the NSW port:

```sql
-- Instruments (one per F-number)
CREATE TABLE instrument (
  id              BIGSERIAL PRIMARY KEY,
  f_number        TEXT UNIQUE NOT NULL,   -- e.g. 'F2018L00631'
  title           TEXT NOT NULL,
  kind            TEXT NOT NULL,          -- 'act' | 'rules' | 'guidelines'
  principal       BOOLEAN NOT NULL,       -- vs amending
  made_date       DATE NOT NULL,
  sunset_date     DATE,                   -- F2024L01257 SUNSET-PENDING
  licence         TEXT NOT NULL DEFAULT 'CC-BY-4.0',
  jurisdiction    TEXT NOT NULL DEFAULT 'Cth'
);

CREATE TABLE compilation (
  id                BIGSERIAL PRIMARY KEY,
  instrument_id     BIGINT REFERENCES instrument(id),
  compilation_no    INT NOT NULL,
  in_force_from     DATE NOT NULL,
  in_force_to       DATE,                 -- NULL = current
  source_url        TEXT NOT NULL,
  source_hash       TEXT NOT NULL,        -- sha256 of retrieved content
  fetched_at        TIMESTAMPTZ NOT NULL,
  UNIQUE(instrument_id, compilation_no)
);
CREATE INDEX ON compilation (instrument_id, in_force_from);

CREATE TABLE clause (
  id                    BIGSERIAL PRIMARY KEY,
  ident_key             TEXT NOT NULL,    -- stable across compilations
  instrument_id         BIGINT REFERENCES instrument(id),
  current_compilation_id BIGINT REFERENCES compilation(id),
  UNIQUE(instrument_id, ident_key)
);

CREATE TABLE clause_history (
  id                     BIGSERIAL PRIMARY KEY,
  clause_id              BIGINT REFERENCES clause(id),
  compilation_id         BIGINT REFERENCES compilation(id),
  clause_path            TEXT NOT NULL,   -- 'Part 2 > Div 1 > s5(2)(a)'
  heading                TEXT,
  text_verbatim          TEXT NOT NULL,
  parent_clause_id       BIGINT REFERENCES clause(id),
  change_type            TEXT NOT NULL,   -- NEW|AMENDED|REPEALED|RENUMBERED|UNCHANGED
  amending_instrument_id BIGINT REFERENCES instrument(id),
  UNIQUE(clause_id, compilation_id)
);
CREATE INDEX ON clause_history (compilation_id);

CREATE TABLE defined_term (
  id              BIGSERIAL PRIMARY KEY,
  compilation_id  BIGINT REFERENCES compilation(id),
  term            TEXT NOT NULL,
  definition      TEXT NOT NULL,
  defined_in_clause BIGINT REFERENCES clause(id)
);
CREATE INDEX ON defined_term (compilation_id, term);

CREATE TABLE cross_ref (
  id                              BIGSERIAL PRIMARY KEY,
  from_clause_id                  BIGINT REFERENCES clause(id),
  to_ref_type                     TEXT NOT NULL, -- SECTION|RULE|STANDARD|EXTERNAL
  to_ref_target                   TEXT NOT NULL,
  to_ref_compilation_id_at_write  BIGINT REFERENCES compilation(id)
);

CREATE TABLE transitional_rule (
  id                 BIGSERIAL PRIMARY KEY,
  source_clause_id   BIGINT REFERENCES clause(id),
  applies_from       DATE NOT NULL,
  applies_to         DATE,
  participant_scope  TEXT NOT NULL
);

-- New in this scoping (T3.a + T4.f):
CREATE TABLE fetch_log (
  id                 BIGSERIAL PRIMARY KEY,
  f_number           TEXT NOT NULL,
  fetched_at         TIMESTAMPTZ NOT NULL,
  status             INT NOT NULL,        -- HTTP status
  bytes              INT,
  source_hash        TEXT,
  monthly_full_sweep BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX ON fetch_log (f_number, fetched_at);
```

#### T3.f Storage estimate

Derivation (all `[INFERENCE]` with the multipliers shown):
- Corpus at launch: ~750 clauses × ~600 bytes verbatim text ≈ 450 KB text. With row overhead (~200 B) and one `clause_history` row per compilation change: 750 × 200 + 750 × 800 ≈ 750 KB.
- Compilations: 11 instruments × ~3 compilations in the 24-month window ≈ 33 compilation rows × 300 B ≈ 10 KB. Plus source blobs at ~200 KB each ≈ 6.6 MB.
- Cross-refs: ~1,500 (avg 2/clause) × 200 B ≈ 300 KB.
- Fetch log: daily poll × 11 instruments × 2 years × 300 B ≈ 2.4 MB.
- **Year-1 total DB size: <100 MB. Year-5 (assuming ~4 amendments/instrument/year): ~500 MB.** Trivially inside Supabase free tier.
- Growth is dominated by monthly-full-sweep raw-blob storage — offload raw HTML/PDF snapshots to R2 (or Supabase Storage) not Postgres.

---

### T4. Amendment Monitoring Loop

#### T4.a Federal Register API / RSS — reality check

Verified 2026-08-06:
- The Federal Register of Legislation (legislation.gov.au) is managed by the Office of Parliamentary Counsel per the Legislation Act 2003 (WebSearch, opc.gov.au result set). No documented public REST API surfaced in the 2026-08-06 search; PMC's copyright page and the OPC FRL page were 403 from this sandbox and are `[UNVERIFIED-PRIMARY]` for the presence of an API. `[UNVERIFIED-PRIMARY]`
- NSW legislation offers an Atom feed (`legislation.nsw.gov.au` Subscribe-RSS page). Cth Federal Register RSS/Atom is **NOT CONFIRMED** in this session's search results.
- The NSW engine's existing PCO XML export (`legislation.nsw.gov.au/export/week`, IP whitelisted, business-hours restriction) is a state pathway that does NOT extend to the Cth Federal Register.
- [M6-11] §Module 7 fallback plan: "daily 07:00 AEST cron pulls the Federal Register 'what's new' listing; filter to the 10 watched F-numbers + any child amending instrument citing them; re-extraction trigger on new compilation number or new amending instrument."

Conclusion: build against the "what's new" HTML index (or Atom if verified at build time) with per-F-number polling as the guaranteed path. **Founder must verify API/RSS availability from an AU IP** before locking the design — see Z3. If a formal API is present the loop simplifies; if not, HTML-scrape with polite retry works.

#### T4.b Monitoring cadence per instrument

| Instrument | Cadence | Rationale |
|---|---|---|
| NDIS Act 2013 | daily | 3 amending Acts in the last 24 mo, one commenced days before this scoping (Integrity Act 2026) |
| Provider Registration & Practice Standards Rules F2018L00631 | daily | The churn driver ([M1-5] §Module 1); SIL wave 1 Jul 2026, 2027 wave pending |
| Restrictive Practices Rules F2018L00632, Incident Rules F2018L00633, Complaints Rules F2018L00634, Code of Conduct F2018L00629 | daily | Same cost as weekly; the SLA promise is "within one business day of publication" per [M6-11] §Module 7 |
| Quality Indicators F2018N00041, Approved Quality Auditors F2025L01383, Worker Screening Rules, Procedural Fairness Guidelines | daily | Same — one loop for all 11 |
| NDIS Supports Transitional Rules F2024L01257 | daily + sunset-monitor | See T3.c |
| **Whole-corpus monthly full sweep** (see T4.f) | monthly | Silent-error defence |

#### T4.c Diff strategy

Textual (character-level) diff plus structural diff (clause path added/removed/renumbered). Textual only would miss a renumber; structural only would miss a substantive text change inside a stable clause path. Both, always, per NSW-engine practice (`scripts/dcp_extract_changed.py` does exactly this at 3,445 LOC).

#### T4.d Human-in-the-loop QA gate

Reviewer sees, per amendment:
- Old text vs new text (side-by-side, coloured diff).
- Old citation vs new citation (renumbering flag).
- All cross-references that pointed to the old clause and whether their target IDs change.
- The extractor's automated verdict from the ported gates (T7).
- A **falsifiable check** for the reviewer: "What would make you reject this?" (borrowed from `scripts/qa_gate.py:60-82` — a check that cannot fail is a rule that is not enforced).

Reviewer approval commits the new `clause_history` rows to the served table and fires the amendment webhook (T5.c).

**Reviewer is the founder in v1.** Not automated. This is deliberate: [M6-11] §Module 7 says "human-in-the-loop QA before publish — this is the moat vs 'GPT scrapes it too'."

#### T4.e Customer-facing SLA

Definition (per [M6-11] §Module 7): "amendment made + one business day." Publish this as the promised SLA. Do NOT promise sub-24-hour. [M6-11] §Module 11 Red Team #1 (highest severity × likelihood) is the solo-founder maintenance trap: a single missed amendment destroys "provenance-verified" positioning retroactively. Kill criterion: two missed-amendment incidents in a rolling 12 months → hire content-ops FTE or narrow SLA to weekly and reprice.

#### T4.f Silent-error defence — monthly full-corpus hash re-fetch

Trigger: cron on the 1st of each month, 03:00 AEST.
Behaviour:
1. Re-fetch every watched F-number's `/latest/text` and `/latest/pdf`.
2. Compute source hashes; compare against the stored `compilation.source_hash` for the current compilation.
3. If any hash changes without a new `compilation_no`, alert. This catches register-side corrections that do not roll the compilation number — the exact silent-error class the [M6-11] §Module 7 loop was designed to defend.
4. If any fetch fails, alert.
5. If any watched F-number is missing (e.g. renumbered) that would appear here.
Alerts route to founder email + Telegram (existing `services/forum_webhook.py` + `api/telegram/` are reused).

Auto-rollback rule: never. The gate raises the alert; the founder resolves it manually. Auto-rollback on a hash change would silently overwrite the served corpus with a stale copy.

---

### T5. OEM Rules Feed API Specification (SKU 1)

Reference: [M6-11] §Module 6B. This section fills in the schema, contract, and forbidden-use UI pattern schedule the earlier doc named but did not spell out.

#### T5.a Endpoints

```
GET  /v1/instruments                        List all watched instruments
GET  /v1/instruments/{f_number}             Metadata for one instrument
GET  /v1/instruments/{f_number}/compilations
                                            List of compilations (with dates)
GET  /v1/clauses                            List clauses. Query params:
                                              ?instrument={f_number}
                                              &as_at=YYYY-MM-DD
                                              &changed_since=YYYY-MM-DD
                                              &limit=100&cursor=…
GET  /v1/clauses/{clause_id}                One clause at the current compilation
GET  /v1/clauses/{clause_id}/at/{date}      One clause as at a specific date
GET  /v1/clauses/{clause_id}/history        Full change history
GET  /v1/amendments?since=…                 Amendment events (paginated)
GET  /v1/amendments/{amendment_id}          One amendment event
GET  /v1/snapshots/{yyyy-mm-dd}             Weekly snapshot (JSON + Postgres dump)
POST /v1/webhooks                           Register a webhook endpoint
GET  /v1/webhooks                           List registered webhooks
DEL  /v1/webhooks/{id}                      Unregister
POST /v1/webhooks/{id}/test                 Send a test event
GET  /v1/health                             Health + last-refresh timestamp
```

Every response includes:
```json
{
  "data": {...},
  "disclaimer": "Verbatim regulatory text; not compliance advice. Sourced from the Federal Register of Legislation. Current as at {ingest_timestamp}.",
  "licence": "CC-BY-4.0 (Cth material) — see attribution requirements",
  "generated_at": "2026-08-06T04:15:22Z"
}
```

#### T5.b Clause object schema

```json
{
  "id": "F2018L00631:s31A",
  "instrument": {
    "f_number": "F2018L00631",
    "title": "National Disability Insurance Scheme (Provider Registration and Practice Standards) Rules 2018",
    "kind": "rules"
  },
  "compilation": {
    "compilation_no": 12,
    "in_force_from": "2026-07-01",
    "in_force_to": null,
    "source_url": "https://www.legislation.gov.au/F2018L00631/2026-07-01/text",
    "source_hash": "sha256:1a2b…",
    "fetched_at": "2026-07-01T14:33:00Z"
  },
  "clause_path": "Part 3 > Division 2 > s31A",
  "heading": "Additional requirements for SIL providers",
  "text_verbatim": "…the full verbatim clause text as published on the Federal Register…",
  "parent_clause_id": "F2018L00631:s31",
  "effective_from": "2026-07-01",
  "effective_to": null,
  "supersedes_id": null,
  "superseded_by_id": null,
  "ingest_timestamp": "2026-07-01T14:33:00Z",
  "source_url": "https://www.legislation.gov.au/F2018L00631/2026-07-01/text#s31A",
  "cross_refs": [
    {"to_ref_type": "SECTION", "to_ref_target": "NDIS Act 2013 s73E"},
    {"to_ref_type": "STANDARD", "to_ref_target": "F2018N00041 Indicator 3.4"}
  ],
  "provenance": {
    "reviewer": "content-ops",
    "approved_at": "2026-07-01T15:10:00Z",
    "gates_passed": ["fabricated-value", "conflicting-value", "value-absent-from-source",
                     "source-text-hash", "controls-provenance", "liability-language"]
  }
}
```

Nullability: `heading` optional (some clauses are unheaded); `parent_clause_id`, `supersedes_id`, `superseded_by_id`, `effective_to` are nullable; `text_verbatim` NEVER nullable.

#### T5.c Webhook contract

- Events: `clause.amended`, `clause.repealed`, `clause.new`, `clause.renumbered`, `instrument.compiled` (a new compilation number appeared), `instrument.sunsetted`.
- Payload: envelope `{event_id, event_type, occurred_at, resource_url, data}` where `data` is the full clause object (T5.b) at the new compilation.
- Retry policy: exponential backoff — 30 s, 2 m, 10 m, 1 h, 6 h, 24 h — then dead-letter. Delivery attempts are logged; licensee can pull the DLQ via `GET /v1/webhooks/{id}/dead-letter`.
- Signature: HMAC-SHA256 of the payload body using the shared secret from webhook registration; delivered in `X-NDIS-Signature` header. Timestamp in `X-NDIS-Timestamp`; reject events whose timestamp is >5 min old (replay protection). Both fields signed together.
- Idempotency: `event_id` is a UUID; the same event may be delivered more than once; licensee is expected to dedupe on `event_id`.

#### T5.d Weekly snapshot format

- Layout: one directory per snapshot at `snapshots/YYYY-MM-DD/`:
  - `manifest.json` — snapshot metadata, hash of every file, corpus counts per instrument.
  - `clauses.jsonl` — one clause per line, ordered by (instrument, clause_path).
  - `compilations.jsonl` — every compilation currently in scope.
  - `amendments.jsonl` — amendments delivered in the past week.
  - `postgres.sql.gz` — full DB dump (Enterprise tier only).
  - `SHA256SUMS` — checksum manifest.
- Delta vs full: delta by default (`snapshots/YYYY-MM-DD/delta.jsonl` with only changed clauses since previous snapshot); full snapshot on the first of each month or on demand via `GET /v1/snapshots/{yyyy-mm-dd}?full=true`.

#### T5.e Auth model — recommend API key

- **API key** per tenant, in `Authorization: Bearer <key>` header. Rotatable; per-key rate limits; per-key access-log for the licensee to audit.
- **Not OAuth**: single-tenant machine-to-machine; OAuth adds ceremony without security value here.
- **Not mTLS**: the licensees named in [M6-11] §Module 9 (Centro ASSIST, FormaOS, ClinicComply, Smart Compliance Systems, Audit Pilot) are SME SaaS vendors; mTLS is a deal-breaker for developer onboarding.
- Webhook signing (T5.c) is the mTLS-equivalent for asynchronous events.

#### T5.f Rate limits and quotas

- **Free sandbox tier**: 1,000 req/day, no webhooks.
- **Starter tier** ($2k/mo): 10k req/day soft quota, 3 webhooks, 5 req/s.
- **Standard tier** ($3k/mo): 50k req/day, 10 webhooks, 20 req/s.
- **Enterprise tier** ($5k/mo): 250k req/day, unlimited webhooks, 100 req/s, Postgres logical replication bundle.
- Over-quota returns 429 with `Retry-After`. Persistent over-quota beyond a month triggers an upgrade conversation.

#### T5.g Sandbox environment

- Full production corpus (Tier A verbatim + amendment feed).
- Separate API keys (`sk_sandbox_…`) that never surface real customer webhooks.
- Free for 30 days on signup; reset limit thereafter.
- Explicit "SANDBOX" banner in every response's `disclaimer` field.

#### T5.h Per-licensee mapping-document template

One-pager per licensee, produced by the founder in the pilot (per [M6-11] §Module 6B: "Do the mapping FOR them in the pilot — this is the sales motion.").

```
LICENSEE:            <name>
INTERNAL MAPPING:    <internal control ID> ↔ NDIS clause ID
  E.g. FormaOS-CTL-023   ↔  F2018L00631:s31A(2)(b)
  E.g. FormaOS-CTL-024   ↔  F2018L00633:s6(1)(a)
  …
NOTES:               <where the mapping is imperfect and why>
REVIEW CADENCE:      quarterly (or on-amendment for touched clauses)
```

Kept in the licensee's contract addendum. Every amendment webhook includes the licensee's affected mapping IDs, computed from this document (server-side; requires the licensee to keep the mapping in sync).

#### T5.i Forbidden-use UI pattern schedule

Enforced via a combination of **payload-level attestations** and **contractual clauses** (belt-and-braces). Per [M6-11] §Module 6A "Oracle-creep vectors per SKU / OEM feed" — the licensee CANNOT be permitted to wrap the content in "compliant/not compliant" UI.

**Forbidden UI patterns** (schedule referenced by the licence agreement, C9):
1. Traffic-light indicators (red/amber/green) rendered from Rules Engine data alone.
2. Pass/fail badges next to a provider's name or profile.
3. "Action required" prompts that are not accompanied by the exact clause text and citation.
4. Any statement of the form "you must/should/are required to…" attributed to Rules Engine content without also displaying the verbatim source clause.
5. Rendering a clause without the accompanying citation and effective-date fields.
6. Removing the `disclaimer` string from user-visible surfaces where the clause text appears.
7. Any transformation of `text_verbatim` (summarisation, paraphrase presented as clause text, translation) without a clear "AI-generated summary — not the regulatory text" label.
8. Claims that a compliance state, audit outcome, or provider status is "determined by Rules Engine".

**Technical enforcement:**
- Every clause response includes `"disclaimer"` and `"licence"` fields at the top level (T5.a). The API server SHOULD refuse to strip them (they are always present).
- `text_verbatim` is delivered as a distinct field from any derived summary — the licensee cannot conflate them at the payload level.
- **Referrer logging for the Tier B pricing endpoint** ([M6-11] §Module 6B) — every `/pricing_schedule` call logs referrer + IP + timestamp; a licensee whose UI shows Pricing Schedule content without the required CC-BY-NC attribution can be identified from access logs and asked to fix.
- Static audit: the licence agreement grants the Rules Engine the right to inspect the licensee's production UI for compliance annually (contractual, not technical).

**Contractual enforcement:** the licence agreement (C9) makes each of the 8 forbidden patterns a material breach with a defined cure period.

---

### T6. Consultant Seat Spec (SKU 2)

Reference: [M6-11] §Module 6B. Below is the fill-in for the Next.js page inventory, PDF footer, digest email pipeline, and multi-tenancy model.

#### T6.a Next.js page inventory

| Route | Purpose |
|---|---|
| `/login`, `/signup`, `/forgot-password` | Auth (email/password + Google SSO) |
| `/onboarding` | Consultant firm profile (name, ABN, logo, brand colour, contact) + first provider-profile wizard |
| `/dashboard` | List of provider profiles + recent amendment digest highlights |
| `/profiles/new` | Provider-profile intake wizard (~90 sec: legal name, ABN, registration status, service/registration groups, LGA, worker headcount bracket, RP indicator, SIL flag) |
| `/profiles/[profileId]` | Provider-profile detail — filtered obligations register, amendment feed for that profile, PDF export button |
| `/profiles/[profileId]/pdf` | PDF preview (React-PDF renderer) |
| `/profiles/[profileId]/share` | Tokenised web-share link management (revoke, expire) |
| `/profiles/[profileId]/audit-trail` | Every change to the profile + every clause the profile is filtered to (append-only) |
| `/instruments` | Full Tier A instrument list (link-out to Federal Register + last-refresh timestamp) |
| `/amendments` | Firm-wide amendment ledger with per-profile filters |
| `/settings/firm` | Firm-level settings (logo, brand, contact, seats) |
| `/settings/billing` | Stripe portal |
| `/settings/api` | Optional: personal API key for the firm to pull profiles into its own tools |
| `/legal/terms`, `/legal/privacy`, `/legal/disclaimer` | Terms + Privacy + non-customisable disclaimer text |

#### T6.b Provider-profile schema

```typescript
type ProviderProfile = {
  id: string;                         // UUID
  firm_id: string;                    // tenant
  legal_name: string;
  abn: string;                        // 11 chars, validated via ABN Lookup (abr.business.gov.au) — see below
  abn_lookup_snapshot_at: string;     // ISO timestamp of last ABN Lookup validation
  registration_status: 'registered' | 'unregistered' | 'application-in-flight' | 'suspended';
  registration_groups: string[];      // NDIS registration group IDs (0001–0138)
  service_types: string[];
  lga: string;
  worker_headcount_bracket: '0-4' | '5-19' | '20-49' | '50-199' | '200+';
  regulated_practices: boolean;       // triggers RP-flavour of obligations register
  sil_provider: boolean;              // triggers SIL supplementary module
  key_personnel: KeyPersonnel[];
  created_at: string;
  updated_at: string;
  created_by: string;                 // user ID
};
```

Validation:
- ABN validated on entry against the ABN Lookup web service (abr.business.gov.au — the government's own JSON endpoint, free after registration for an AUSkey/API key). If ABN Lookup is unreachable, save the profile but flag `abn_lookup_snapshot_at = null` and re-try on schedule.
- Registration groups validated against the NDIS Commission's published group list — this is Tier C guidance data, ingested and stored, refreshed monthly.
- LGA validated against the ABS LGA gazette (existing NSW LGA table can be extended to a full AU set — reuse `services/lga_lookup.py`).

#### T6.c Obligations-register query surface

```
GET /api/seat/profiles/{id}/obligations
  ?as_at=YYYY-MM-DD                (default today)
  &category=incident|complaints|worker-screening|governance|restrictive|…
  &instrument=F…
  &format=web|pdf|csv
```

Output row:
```json
{
  "clause_id": "F2018L00631:s31A",
  "citation": "Rule 31A(1)(b), Provider Registration and Practice Standards Rules",
  "text_verbatim": "…",
  "effective_from": "2026-07-01",
  "applies_to_this_profile_because": "provider is a SIL provider (Rule 31A applies to SIL modules)",
  "typical_evidence": "Written implementation of Practice Standard 2 (Governance)…",
  "last_verified_against_source": "2026-08-05T02:15:00Z"
}
```

Filtering is deterministic — a picklist input (registration groups, RP flag, SIL flag) drives a SQL WHERE clause on the clause corpus. No LLM at answer time. This is the core moat.

#### T6.d White-label PDF renderer

- Engine: `@react-pdf/renderer` 4.5.1 (already in `frontend-nextjs/package.json` — verified 2026-08-06). Reused from the existing NSW report renderer at `frontend-nextjs/components/pdf/*`.
- Template variables: firm logo (URL), brand colour (hex), firm contact block, PDF cover title. Nothing else is customisable.
- Non-customisable footer text (per [M6-11] §Module 6A):

  > "Regulatory reference produced by {consultant_firm_name} using content infrastructure licensed from Rules Engine. Interpretation and application is the professional responsibility of {consultant_firm_name}. Verbatim regulatory text; not compliance advice. Current as at {as_at_date}."

- Enforcement point: the footer string is set in `frontend-nextjs/components/pdf/ndis/ConsultantFooter.tsx` (to be created) and consumed by every page renderer. **The string is a compile-time constant**, not a database field, not a firm-configurable field, not an env var. Attempts to modify the file are caught by:
  - CI check: a new `scripts/consultant_seat_footer_lock.py` gate that fails the build if `ConsultantFooter.tsx` text-verbatim content changes without a matching change to a hash-locked baseline (analogous to `mutation-baselines.json` and `brief_field_coverage_baseline.json`).
  - Manual review: any PR touching the footer is a critical-tier QA report.

#### T6.e Monthly amendment digest email pipeline

- Queue: a Supabase Postgres queue (`digest_queue` table) written by a monthly cron (1st of month, 06:00 AEST) with one row per active firm.
- Template: MJML → HTML rendered server-side (no external service).
- Content per firm: aggregated per-profile amendment counts + top 5 clause diffs across the firm's profiles + link to the full ledger.
- Deliverability: send via a transactional-email provider (Postmark or Amazon SES) from a Rules-Engine sending domain with SPF + DKIM + DMARC configured. Never from Gmail / Google Workspace SMTP.
- Unsubscribe: per firm + per user. Unsubscribe is at the firm-user level; a firm cannot force a user to receive digests but can turn off firm-wide digests.
- Bounce-handling: a bounce or complaint auto-suspends future sends to that address and alerts the firm admin.

#### T6.f Multi-tenancy model

- **Row-level scoping** using Supabase RLS. Every table with tenant data has a `firm_id` column and an RLS policy `firm_id = auth.jwt() ->> 'firm_id'`. This is the same pattern the existing repo already uses; no new muscle.
- Key hierarchy: firm → user (many-to-many via `firm_user` join table, with a role: `owner | admin | user`) → provider_profile (many-per-firm) → clause (shared; not tenant-scoped, but access mediated by profile filter).
- **Tenant isolation tests** — a Jest suite in `frontend-nextjs/__tests__/api/seat/tenant_isolation.test.ts` that authenticates as firm A and asserts every query for firm B's data returns empty. Failing this test blocks merge.
- Backup snapshots are per-DB, not per-tenant; a tenant export ("give me my data") is a separate operation.

---

### T7. Verification-Gate Port

Each gate is graded against the port-effort estimate.

| Gate | Existing file | LOC | Verdict | Notes / new spec if REQUIRED |
|---|---|---:|---|---|
| Fabricated-value detector | `services/extracted_data_integrity.py::fabricated_values` | (26 fns total, this one is one) | **PORTS DIRECTLY** | Domain-agnostic (per file docstring). Port cost: 0 — passes a per-table config |
| Conflicting-value detector | `services/extracted_data_integrity.py::conflicting_values` | | **PORTS DIRECTLY** | Same |
| Value-absent-from-source | `services/extracted_data_integrity.py::value_absent_from_source` | | **PORTS DIRECTLY** | Reused directly by NSW `scripts/verify_extraction_fidelity.py`; same pattern here |
| Source-text hashing | `scripts/pdf_text_hash.py` + `source_hash` column in schema | 59 | **PORTS DIRECTLY** | Table names change |
| Controls-provenance ratchet | `scripts/validate_controls_provenance.py` | 299 | **NEEDS REWRITE** | The three-state discipline (REPRODUCIBLE / TRACEABLE / UNVERIFIABLE) ports directly, but "reproducible" here means "the extractor script re-derives the same clause text from the same source_hash" — a different derivation than the DCP setback controls one. Rewrite the "reproducibility" check |
| Control-values-vs-source-text validator | `scripts/validate_control_source_values.py` | 447 | **NEW GATE REQUIRED** | The NSW variant asks "is this stored number derivable from its own quoted source_text by a named rule?" For NDIS, the analogue is: **"is the stored clause text byte-for-byte identical to the region of the source HTML it cites, after whitespace normalisation?"** Failure mode: the extractor's normalisation altered a semantic character (e.g. non-breaking space, curly-vs-straight quote, unicode dash). Acceptance criterion: `text_verbatim == normalise(source_html[section_range])` for 100% of clauses; any deviation blocks the gate |
| Schema-contract-vs-live-catalog | `scripts/validate_schema_contract.py` | 632 | **PORTS DIRECTLY** | Verified 2026-08-06: this checker is table-agnostic ("For every SQL string in the scanned roots: every base table … must exist in the live catalog"). Rerun against NDIS DB after schema T3.e is deployed |
| Brief field-coverage ratchet | `scripts/brief_field_coverage_ratchet.py` | 186 | **PORTS WITH MODIFICATION** | The concept ports: "a brief layer may gain fields, never silently lose them." The specific fields (brief layers) are DCP-shaped; NDIS equivalent is "an obligations-register response may gain columns, never silently lose them" |
| Mutation-count baseline | `scripts/check_test_baselines.py` + `mutation-baselines.json` | | **PORTS DIRECTLY** | Format reused; contents empty and grown |
| Liability-language scanner | `scripts/liability_language_check.py` | 212 | **PORTS DIRECTLY** | Regex is domain-agnostic. Verified 2026-08-06 at `scripts/liability_language_check.py:30-36`: flags `safe|feasible|compliant|should|recommend|suitable|adequate|sufficient|approved|guaranteed|certified|confirmed|verified|ensure|assure|accurate|definitive|comprehensive|reliable`. Every one of these is a live liability word in NDIS context too |

**Two new NDIS-specific gates required:**

11. **Clause-text byte-identity gate** (per T7 row 6 above) — new file `scripts/validate_clause_text_identity.py`, ~250 LOC estimate.
12. **CC-BY / CC-BY-NC attribution gate** — new file `scripts/validate_attribution_headers.py`, ~150 LOC estimate. Failure mode: an API response, a PDF export, or a web view surfaces content whose licence is CC-BY-NC without the required attribution string. Acceptance criterion: every user-visible surface that renders a Tier B (Pricing Schedule) clause carries the exact attribution string defined in C2.

**Pre-push hook plan.** Existing `.githooks/pre-push` (verified 2026-08-06, 363 LOC) already wires 10 gates. NDIS port keeps the shape; the gate list becomes:

```
[1]  pytest (NDIS suite + NSW retained)
[1b] mutation-count baseline (NDIS + NSW)
[1c] brief field-coverage ratchet (NDIS-adapted)
[1d] schema-contract-vs-live-catalog
[1e] controls-provenance (rewritten)
[1f] control-source-value (rewritten as clause-text identity, T7 gate 6)
[1g] NEW: attribution-headers gate
[2]  jest (Consultant Seat + retained)
[3]  QA report validation
[4]  liability-language scan
```

---

### T8. Test Coverage Plan

Anchor: current repo has ~3,665 pytest tests and ~1,002 jest tests (per prompt §Context; the CLAUDE.md file cites 1794 pytest / 615 jest as its live count — the prompt number is presumably a growth roll-up. Actual local count would be `pytest --collect-only -q | tail -3` — noted for the honesty ledger).

#### T8.a pytest additions

| Module target | New tests | Rationale |
|---|---:|---|
| Per-instrument extractor (11 instruments in T2.a) | ~15 tests each ≈ 165 | Fixture-driven: for each instrument, verify (a) clause count matches golden, (b) defined-term extraction matches golden, (c) cross-ref extraction matches golden |
| Effective-date engine (T3) | ~40 | `as_at(t)` correctness for edge cases: sunset dates, transitional windows, cross-refs at a point in time, three-state (`PRESENT`/`REPEALED`/`NEVER_EXISTED`) |
| Amendment-monitoring loop (T4) | ~25 | Diff correctness (structural + textual), silent-error hash re-fetch, sunset alert |
| OEM API (T5) | ~80 | Endpoint contract, pagination cursor stability, `as_at` param semantics, webhook signature verify, replay-protection window, rate-limit tiers |
| Verification gates (T7) — new gates | ~30 | Clause-text byte-identity gate + attribution-headers gate |

**Total: ~340 new pytest tests.**

#### T8.b jest additions

| Module target | New tests | Rationale |
|---|---:|---|
| Consultant Seat auth + tenant-isolation (T6.f) | ~40 | Every RLS boundary; every profile CRUD; every session-token expiry path |
| Provider-profile intake wizard | ~20 | Every field validation, ABN Lookup unreachable path, saving-with-warning path |
| Obligations-register query surface (T6.c) | ~25 | Filter combinations, `as_at` date param, format=csv/pdf/web |
| PDF renderer (T6.d) | ~20 | Footer string presence, brand-colour theming, PDF output byte-identity to golden |
| Amendment-digest email (T6.e) | ~15 | Template rendering, unsubscribe link generation, bounce-handling stub |
| OEM API SDK client (if we ship a TypeScript SDK for OEM licensees) | ~20 | Retry logic, signature verify, dedup on event_id |

**Total: ~140 new jest tests.**

#### T8.c Golden-fixture strategy per instrument

- One fixture directory per F-number under `tests/fixtures/ndis/{f_number}/`:
  - `compilation-{N}.raw.html` — the raw HTML as fetched, unchanged.
  - `compilation-{N}.raw.pdf` — the raw PDF.
  - `compilation-{N}.expected-clauses.json` — the extractor's expected output, human-verified.
  - `compilation-{N}.expected-defined-terms.json`
  - `compilation-{N}.expected-cross-refs.json`
  - `compilation-{N}.source.sha256` — the hash of the raw HTML at fetch time.
- Refresh policy: **fixtures are frozen at fixture-capture time and never auto-refreshed.** A new compilation gets a new fixture directory (`compilation-{N+1}/`). This is critical — auto-refreshing fixtures against the current Federal Register would make it impossible to test the amendment-monitoring loop, because the "old" state would silently update to the "new" state.
- Hash-locked: `SHA256SUMS` at the fixture-root level; a fixture whose bytes change without a `SHA256SUMS` update fails CI.

#### T8.d Mutation testing baseline for NDIS

- Modules in scope for mutmut: `services/extracted_data_integrity.py` (ports directly, already covered), the new NDIS extractors, the effective-date engine, the OEM API handlers.
- Target survivor rate: <10%. NSW engine's baselines are informational (opt-in), not blocking; NDIS should adopt the same pattern.
- Setup cost: ~8 hrs to configure mutmut per new module + write the baseline JSON.

#### T8.e Integration tests for the OEM API

- **Contract tests** using Pact (or a bespoke jest-nock recorder). One contract per licensee's expected shape; broken contract fails CI.
- **Webhook replay tests**: fire a test event to a mock endpoint, verify signature, replay the same event and verify the SDK deduplicates on `event_id`.
- **Snapshot integrity**: download a weekly snapshot in test, verify `SHA256SUMS`, verify the delta reconciles against the full snapshot.
- **Long-running "day 30" test**: run the amendment-monitoring loop for 30 simulated days against a fixture Federal Register (hand-authored), verify every amendment produces a webhook, verify the SLA metric.

#### T8.f Integration tests for the Consultant Seat

- **Auth**: signup, login, forgot password, SSO, session-token expiry.
- **Tenant isolation**: authenticated as firm A, every read/write of firm B's data returns 403 or empty (never 200 with wrong data). This test suite must include negative cases for every table.
- **PDF footer**: byte-identity of the rendered footer against the string constant.
- **Digest email**: fire the monthly cron, verify one email per firm, verify unsubscribe link is unique per user.

---

### T9. Infrastructure

#### T9.a Hosting

- Existing production stack (per CLAUDE.md): **Vercel** for Next.js, **Supabase** (managed Postgres) for the DB. Both used by the current NSW product.
- Suitability for OEM API 99.5% SLA: Vercel's Serverless Functions at Standard plan offer 99.99% uptime SLA; Supabase managed Postgres SLA is 99.99% on Pro plan. The bottleneck for a 99.5% promise is not the hosting — it is (a) the amendment-monitoring loop's dependency on legislation.gov.au reachability and (b) the human-in-the-loop QA gate's dependency on the founder being available. Both are captured in T10 and X4.
- No move to AWS/GCP recommended for MVP. The extra ops burden is not justified for a solo founder at <20 licensees.

#### T9.b CDN + edge caching for the Rules Feed

- Vercel's Edge Network fronts the API. Every `GET` response is cacheable at the edge with `Cache-Control: public, max-age=300, stale-while-revalidate=600` — most licensee traffic will hit the cache.
- Cache-invalidation trigger: on `instrument.compiled` event, purge the affected cache keys via Vercel's cache-tag API.
- Rate limits (T5.f) are enforced at the edge via Vercel Edge Middleware, not inside the function.

#### T9.c Monitoring + alerting

- Uptime: BetterUptime or Vercel's built-in monitoring — alerts to founder phone via Telegram (existing `api/telegram/` route reused).
- Freshness SLA: a synthetic check every 15 min hits `GET /v1/health` and asserts `last_refresh < 30h ago` (the SLA is "one business day"). Failing check pages the founder.
- Gate-failure alerts: any gate failing in the extraction pipeline routes to founder + a dashboard (`/internal/gate-status`).

#### T9.d Backup + point-in-time-restore

- Supabase Pro plan includes daily automated backups + 7-day PITR. Sufficient for MVP.
- Corpus is also stored as a Git-committed snapshot per week (weekly snapshot in T5.d, but also committed to a private repo as belt-and-braces).

#### T9.e Secrets management

- Vercel env vars for Vercel-side secrets (Supabase URL + service key, Stripe key, transactional-email keys).
- 1Password Secrets Automation OR HashiCorp Vault OR AWS Secrets Manager: none of these are needed at MVP scale — Vercel env vars + a founder-controlled password manager is enough.
- Never a `.env` file in the repo (existing pre-commit hook enforces this at `.githooks/pre-commit:22-31`, verified 2026-08-06).

#### T9.f Monthly cost estimate

Derivation all `[INFERENCE]` from public list-price pages.

| Configuration | Vercel | Supabase | Email | Monitoring | Domain + misc | **Monthly total** |
|---|---:|---:|---:|---:|---:|---:|
| **0 licensees / 0 seats** (staging + amendment loop only) | $20 (Hobby+cron) | $25 (Pro base) | $0 (SES pay-per-use) | $0 (BetterUptime free tier) | $15 | **~$60** |
| **5 licensees / 50 seats** | $80 (Pro, edge functions) | $25 (Pro base) + $10 storage | $10 (SES ~2k emails/mo) | $20 (BetterUptime pro) | $15 | **~$160** |
| **20 licensees / 500 seats** | $200 (Pro, +Web Analytics) | $65 (Pro, larger tier) | $50 (SES ~15k emails/mo) | $30 (BetterUptime team) | $15 | **~$360** |

Even at the top tier, monthly infrastructure is <$400 — negligible against a $2–5k/mo × 20 licensees + $299/mo × 500 seats revenue.

---

### T10. Person-Week Rollup

Reconciled against [M6-11] §Module 7 (8.5–11.5 wk to first demoable; 6-wk SIL demo slice = 9–12 wk total).

| Stratum | Full-scope | MVP (SIL slice) | Delta vs [M6-11] |
|---|---:|---:|---|
| **(a) Engine port** (T1 totals: PORTS DIRECTLY 118 hrs + PORTS WITH MODIFICATION 408 hrs) | ~13 wk | ~4 wk | [M6-11]: 3–6 wk port → **agree** at MVP; ceiling is higher because full port includes UI shell |
| **(b) Corpus extraction** (T2 reconciled) | 13 wk | ~6 wk | [M6-11]: 13–14 wk full / 5.5 wk MVP → **agree** |
| **(c) Verification gates** (T7: 2 ports + 2 rewrites + 2 new gates) | ~2.5 wk | ~2 wk | [M6-11] did not stratify separately; new estimate |
| **(d) OEM API** (T5) | ~5 wk | ~3 wk | [M6-11] did not stratify separately |
| **(e) Consultant Seat** (T6) | ~7 wk | ~4 wk | [M6-11] did not stratify separately; ships month 3–4 in [M6-11] |
| **(f) Infrastructure + gates wiring** (T9 + T8) | ~1.5 wk | ~1 wk | [M6-11] did not stratify |
| **Total to first demoable (MVP)** | **~42 wk full-scope** | **~20 wk MVP + Seat + OEM** | **[M6-11] said 8.5–11.5 wk to first demoable and 6-wk SIL slice** |

**Delta explanation:** this document's number for MVP (20 wk) is roughly **DOUBLE** the [M6-11] estimate (8.5–11.5 wk) because [M6-11]'s "first demoable" figure counts corpus + engine port ONLY, not the OEM API surface and not the Consultant Seat UI. When [M6-11] §Module 6D sequencing is added — "Months 0–3: content ships first" then "Month 3: OEM API + consultant seat launch simultaneously" — the ~3 months (~12 wk) to OEM+Seat launch matches this document's ~13–15 wk (corpus + gates + OEM + Seat).

**Reconciled statement:** the [M6-11] 8.5–11.5-wk figure is the **content + engine port only**, correct for a demo-able CLI or Postman collection. To reach "OEM Rules Feed v1 + Consultant Seat v1 ready to onboard the first paying licensee/seat" the honest number is **13–15 wk MVP scope, ~20 wk with a modest safety margin, per this scoping**. See Z2 for the reconciled single number.

---

## COMPLIANCE / LEGAL INVESTIGATION

### C1. Licence Audit of every Tier A corpus source

**Method note:** all `legislation.gov.au` URLs returned HTTP 403 to WebFetch in this scoping session, but the founder has since dropped `pdftotext -layout` extracts of 15 Tier A source PDFs into `docs/corpus-primary-sources/text/`. The licence findings below are now read from those extracts directly, not from a WebSearch snippet. The `[UNVERIFIED-PRIMARY]` tags previously carried on the notice column reflected that the PDF had not been opened; that condition is largely resolved by the corpus drop (see subsection immediately below).

#### C1.a Per-document copyright notice pattern — verified

Verified 2026-08-06 by `grep -i -E "copyright|creative commons|©|attribution|by-nc|by 4\.0"` across all 15 files in `docs/corpus-primary-sources/text/` (F2018L00633, F2018L00633ES, F2020C01087, F2024C00048, F2024L01257, F2024L01257ES, F2025L01383, F2025L01383ES, F2025L01383SES, F2026C00165, F2026C00166, F2026C00527, F2026C00528, C2026C00181REC01, ndis-pricing-schedule-2026-27-v1_2): **zero hits across every file**.

Conclusion:
- **No Federal Register instrument in the Tier A corpus carries an in-document copyright notice.** The licence is applied at platform level (legislation.gov.au terms of use) — this is consistent Office of Parliamentary Counsel practice and is NOT a data-quality issue. The absence of a per-doc notice is the norm on that platform, not an oversight.
- **No per-document notice in the 2026-27 Pricing Arrangements PDF either** — the pricing schedule extract is likewise silent. The site-wide CC BY-NC 3.0 AU notice on ndis.gov.au (verified in C2 from an AU network) is therefore the sole governing notice for the pricing schedule. See C2 for how this closes the previously-open PDF-level-override question.

**What this simplifies:** the extractor does NOT need per-document licence-parsing logic. Licence is stored per-source at ingest time from a lookup table keyed by host (`legislation.gov.au` → `cc-by-4.0`; `ndis.gov.au` → `cc-by-nc-3.0-au`). See T2.b for the schema simplification that flows from this finding.

**What remains unverified:** the founder-fetched sample is comprehensive across Tier A F-instruments but does NOT include every Commission-published guidance PDF. The pattern "zero per-doc notice" is a strong sample-inference across the Federal Register instruments and the one NDIA-hosted PDF captured; it is not yet an exhaustive per-doc verification across the guidance layer. See Z3.

#### C1.b Per-instrument audit table

| F/C-number | Instrument | Licence (governing) | Notice source | Corpus extract |
|---|---|---|---|---|
| C2013A00020 (compilation C2026C00181REC01) | NDIS Act 2013 | CC-BY 4.0 (Federal Register platform terms) | Platform-level; no per-doc notice in PDF | `docs/corpus-primary-sources/text/C2026C00181REC01.txt` |
| F2018L00629 (compilation F2024C00048) | Code of Conduct Rules | CC-BY 4.0 | Platform-level | `docs/corpus-primary-sources/text/F2024C00048.txt` |
| F2018L00631 (compilation F2026C00527) | Provider Registration & Practice Standards Rules | CC-BY 4.0 | Platform-level | `docs/corpus-primary-sources/text/F2026C00527.txt` |
| F2018L00632 (compilation F2020C01087) | Restrictive Practices & Behaviour Support Rules | CC-BY 4.0 | Platform-level | `docs/corpus-primary-sources/text/F2020C01087.txt` |
| F2018L00633 | Incident Management & Reportable Incidents Rules | CC-BY 4.0 | Platform-level | `docs/corpus-primary-sources/text/F2018L00633.txt` (+ ES) |
| F2018L00634 (compilation F2026C00165) | Complaints Management & Resolution Rules | CC-BY 4.0 | Platform-level | `docs/corpus-primary-sources/text/F2026C00165.txt` |
| F2018N00041 (compilation F2026C00528) | Quality Indicators Guidelines *(Notifiable Instrument — Ni tag)* | CC-BY 4.0 | Platform-level | `docs/corpus-primary-sources/text/F2026C00528.txt` |
| F2025L01383 | Approved Quality Auditors Rules 2025 | CC-BY 4.0 | Platform-level | `docs/corpus-primary-sources/text/F2025L01383.txt` (+ ES, SES) |
| F2024L01257 | NDIS Supports Transitional Rules 2024 (SUNSET-PENDING) | CC-BY 4.0 | Platform-level | `docs/corpus-primary-sources/text/F2024L01257.txt` (+ ES) |
| **F2018L00887** (F-number confirmed; extract-on-hand is compilation No. 4 dated 31 July 2021, incl. amendments up to F2021L01050, prepared by OPC) | Worker Screening Rules — principal, in force effective 31/07/2018 | CC-BY 4.0 | Platform-level; zero per-doc markers | `docs/corpus-primary-sources/text/F2021C00788.txt` |
| **F2018N00155** (F-number confirmed; principal — currently in force via compilation **F2026C00166**, comp #1 dated 28/01/2026) | Procedural Fairness Guidelines *(Notifiable Instrument — Ni tag, NOT a Legislative Instrument)* | CC-BY 4.0 | Platform-level | `docs/corpus-primary-sources/text/F2026C00166.txt` |

**Notifiable-Instrument (Ni) parser note.** Two Tier A documents carry the `N` collection tag rather than `L`: F2018N00041 (Quality Indicators Guidelines) and F2018N00155 (Procedural Fairness Guidelines). Notifiable Instruments use a slightly different OPC template than Legislative Instruments — shared front-matter block, but endnote block layout differs and the "made under" attribution formatting is not identical. This flows into T2.a as a parser-strategy variant, not a whole-new parser. See T2.a for the small hours delta.

**Baseline finding from platform:** Federal Register content is CC BY 4.0 per the Office of Parliamentary Counsel / PMC baseline (WebSearch 2026-08-06); confirmed by the absence of any conflicting per-document notice across all 15 extracted files.

**Zero-tolerance rule (unchanged):** if any subsequently-added Tier A instrument turns out to carry a licence other than CC-BY 4.0 (or another attribution-only Creative Commons variant), that instrument's clause text CANNOT be republished verbatim without a commercial-licence request — this remains a KILL SIGNAL for the affected instrument (see X4). The corpus verification so far has not surfaced any such override.

---

### C2. Pricing Schedule Licence Resolution

**Verified 2026-08-06** — the NDIA site-wide copyright and licence notice was fetched from an AU network by the founder and pasted back for direct inspection this session. Source: https://www.ndis.gov.au/policies-rules-and-legal/using-our-websites-and-social-media/copyright (page dated "current as of 3 May 2026"). Confirmed facts, load-bearing for this section and C3 and C11:

- Governing licence for NDIA-published content: **CC BY-NC 3.0 AU** (the Australian port, NOT the 4.0 International variant that Federal Register content uses).
- Plain-English gloss on the notice, verbatim: *"We expect that you will only use information on the website to help people with disability and not use it for commercial purposes."*
- Required attribution string: `© National Disability Insurance Scheme Agency 2013`.
- Exclusions from the licence: logos, trademarks, and any third-party material appearing on the site (trademark handling in C11).
- The CC BY-NC 3.0 vs CC BY-NC-ND conflict flagged in the prior four docs is resolved for the site-wide notice: it is BY-NC (no ND).
- **PDF-level override question — RESOLVED.** The founder-provided extract of the pricing schedule at `docs/corpus-primary-sources/text/ndis-pricing-schedule-2026-27-v1_2.txt` was grep-verified 2026-08-06 (`grep -i -E "copyright|creative commons|©|attribution|by-nc|by 4\.0"` — zero hits). No per-document copyright notice exists in the PDF. The site-wide CC BY-NC 3.0 AU notice on ndis.gov.au is therefore the sole governing notice for the pricing schedule, and the split-posture ingest below is fully defensible in writing (no ambiguity to be resolved by re-reading the PDF).

**Ingest decision: split posture by content class.**

1. **Numerical facts** — item numbers, price limits in AUD, unit codes, cancellation-fee percentages, travel-rate caps, effective_date. **Extract as structured data.** Numbers are not copyright-protected in Australia (*IceTV v Nine Network Australia Pty Ltd* [2009] HCA 14 — copyright protects expression, not the underlying facts). Store number + citation, not the paragraph the number appeared in.
2. **Explanatory paragraphs** — definitions, worked examples, decision trees, narrative rule text. **Pointer-only.** Never ingested. Surface in-product as "See source: [link]" with the deep-linked URL of the current NDIA PDF.
3. **Attribution rendering** — every screen, PDF, API payload, sales-collateral snippet, or other user-facing surface that renders any pricing content MUST render, in a non-suppressible footer:
   > `© National Disability Insurance Agency, licensed under CC BY-NC 3.0 AU — https://www.ndis.gov.au/policies-rules-and-legal/using-our-websites-and-social-media/copyright`
   The API server returns this string as a top-level `attribution` field on every response that includes pricing data; the OEM licence agreement (C9) makes footer suppression a material breach and adds it to the forbidden-use schedule at T5.i.

**Parallel commercial-licence request to NDIA** — still recommended. Draft belongs in C8.a and is now retargeted to a resolved-licence baseline (request written permission to republish, on the reasoning that written permission removes residual ambiguity and departments generally grant such requests for compliance tools that advance the mission). If NDIA refuses or does not reply within 90 days, the split posture above is the launch state. Not on the MVP critical path.

**Corpus DB schema — licence tracking columns.** Every document ingested carries the following provenance fields. Add to the `instrument` table from T3.e and to a new `pricing_source` table for the Pricing Arrangements PDF; the schema decision lives here (not deferred to another section):

```sql
ALTER TABLE instrument ADD COLUMN licence_status       TEXT NOT NULL DEFAULT 'unknown';
   -- 'cc-by-4.0' | 'cc-by-nc-3.0-au' | 'crown-copyright' | 'per-doc-override' | 'unknown'
ALTER TABLE instrument ADD COLUMN licence_notice_url   TEXT;
   -- URL of the copyright notice as fetched
ALTER TABLE instrument ADD COLUMN licence_captured_at  TIMESTAMPTZ;
   -- when the notice was last read verbatim by a human
ALTER TABLE instrument ADD COLUMN ingest_posture       TEXT NOT NULL DEFAULT 'pointer-only';
   -- 'verbatim' | 'facts-only' | 'paraphrase-plus-link' | 'pointer-only'
ALTER TABLE instrument ADD COLUMN attribution_string   TEXT;
   -- rendered verbatim on every user-facing surface
```

For the Pricing Arrangements PDF at seed time: `licence_status='cc-by-nc-3.0-au'`, `licence_notice_url='https://www.ndis.gov.au/policies-rules-and-legal/using-our-websites-and-social-media/copyright'`, `ingest_posture='facts-only'`, `attribution_string='© National Disability Insurance Agency, licensed under CC BY-NC 3.0 AU'`. The `'per-doc-override'` case is retained in the enum for defensive completeness but is no longer live for the pricing schedule per the C1.a grep verification; a future document that DOES carry a per-doc notice would flip to that value.

Ingest boundary: `services/ndia_pricing_pointers.py` (new) fetches the PDF, extracts `{item_number, price_limit_aud, unit, effective_from, source_url, fetched_at, source_hash}` rows into a `pricing_fact` table. NEVER extracts narrative text; NEVER strips the attribution field on the surfaced response.

---

### C3. Commission-Published Guidance Layer

**Baseline assumption:** NDIA- and Commission-published guidance is CC BY-NC 3.0 AU unless the specific document declares otherwise. Source is the same site-wide notice cited in C2: https://www.ndis.gov.au/policies-rules-and-legal/using-our-websites-and-social-media/copyright (verified 2026-08-06 from an AU network; page dated "current as of 3 May 2026"). The Commission's own website (ndiscommission.gov.au) has not been verified this session to carry the identical notice; baseline assumption is that it does under the NDIA umbrella, but each document below is tagged `[UNVERIFIED-PRIMARY]` for per-document override until the founder fetches each PDF and confirms.

**Ingest posture across the guidance layer: paraphrase + link, never verbatim reproduction.** Rationale: the NC clause on CC BY-NC 3.0 AU bites verbatim commercial republication; it does not bar factual summarisation with attribution. This is the same posture that LexisNexis, Thomson Reuters, and Xero-adjacent Australian compliance tools take with departmental NC-licensed content — paraphrase the operative rule, link to the primary source, carry the attribution string. Rules Engine adopts the same posture across every guidance document.

| Document | Expected URL | Licence (baseline) | Ingest strategy | Per-doc override risk |
|---|---|---|---|---|
| Practice Standards booklet Nov 2021 v4 (~45pp) — companion to F2018L00631 | ndiscommission.gov.au/…/practice-standards | CC BY-NC 3.0 AU `[UNVERIFIED-PRIMARY]` | **Paraphrase + link.** Never reproduce paragraphs. | Founder to confirm per-doc notice |
| Provider / Worker Code of Conduct Guidance | ndiscommission.gov.au/…/code-of-conduct | CC BY-NC 3.0 AU `[UNVERIFIED-PRIMARY]` | Paraphrase + link | Founder to confirm |
| Position Statements batch (Feb 2026) | ndiscommission.gov.au/…/position-statements | CC BY-NC 3.0 AU `[UNVERIFIED-PRIMARY]` | Paraphrase + link | Founder to confirm |
| Detailed Guidance — Incident Management (Sep 2024) | ndiscommission.gov.au/…/reportable-incidents-guidance | CC BY-NC 3.0 AU `[UNVERIFIED-PRIMARY]` | Paraphrase + link (24-hr Immediate / 5-business-day timeframes are facts and can be extracted structurally per the IceTV posture used in C2) | Founder to confirm |
| Detailed Guidance — Complaints (Sep 2024) | ndiscommission.gov.au/…/complaints-guidance | CC BY-NC 3.0 AU `[UNVERIFIED-PRIMARY]` | Paraphrase + link | Founder to confirm |
| Worker Screening Q&A | ndiscommission.gov.au/…/worker-screening | CC BY-NC 3.0 AU `[UNVERIFIED-PRIMARY]` | Paraphrase + link (per-jurisdiction facts extractable structurally) | Founder to confirm |
| Provider Toolkit | ndiscommission.gov.au/…/provider-toolkit | CC BY-NC 3.0 AU `[UNVERIFIED-PRIMARY]` | Paraphrase + link | Founder to confirm — broad document |
| Regulated Restrictive Practices Guide (per [M1-5] §Module 1 Tier B row) | ndiscommission.gov.au/…/rrp-guide | CC BY-NC 3.0 AU `[UNVERIFIED-PRIMARY]` — was flagged as CC BY-NC International in [M1-5]; baseline reconciled to the site-wide AU 3.0 pending per-doc capture | Paraphrase + link | Highest — capture and re-verify first |

**Attribution requirement (identical to C2):** every user-facing surface that renders any guidance-derived content MUST render, in a non-suppressible footer:
> `© NDIS Quality and Safeguards Commission (or NDIA, whichever published), licensed under CC BY-NC 3.0 AU — https://www.ndis.gov.au/policies-rules-and-legal/using-our-websites-and-social-media/copyright`

Substitute the actual Commission-side notice URL once verified per-document.

**Founder action before build:** re-fetch each document from an AU home network, drop extracted text into `docs/corpus-primary-sources/` per that folder's README, capture each copyright notice verbatim, and log any per-document override (a document declaring anything other than CC BY-NC 3.0 AU) to Z3 so it can be re-scoped.

---

### C4. Liability Posture Per SKU

Anchors: MLC v Evatt (1968) 122 CLR 556 (limits Hedley Byrne to defendants in the business of giving advice or holding out as advisers); Perre v Apand [1999] HCA 36 (pure-economic-loss requires reliance + vulnerability + defendant control — a B2B customer with its own audit obligations is not vulnerable in the required sense per [M6-11] §Module 6A); Australian Consumer Law s18 (misleading conduct — cannot be contracted out of per Clayton Utz 2023 analysis and confirmed by WebSearch 2026-08-06: "disclaimers don't cure a misleading overall impression").

#### C4.a OEM Rules Feed — payload disclaimer + licence clauses

**API payload `disclaimer` string** (always present, T5.a):

> "Verbatim regulatory text from the Federal Register of Legislation (licenced CC-BY-4.0), sourced as at {ingest_timestamp}. Not compliance advice. The Licensee is responsible for any determination, advice, or representation made to end-users using this content."

**Licence-agreement clauses required** (drafted in C9):
- **Limitation of liability** — cap at 12 months' fees paid. Excludes indirect and consequential loss. Cannot exclude ACL implied warranties (per WebSearch 2026-08-06 confirmation of s18 unavoidability), but the cap on quantum is enforceable.
- **Indemnity** — Licensee indemnifies Rules Engine against any claim by an end-user arising from the Licensee's use, application, or presentation of the content, **except** where such claim arises from Rules Engine's provision of content that materially differs from the cited source.
- **Permitted use** — API content may be integrated into Licensee's product for internal reference and to inform Licensee's own professional determinations. Content must be presented verbatim; citations and effective dates must be surfaced; the `disclaimer` field must be visible on any surface that surfaces the clause.
- **Forbidden-use schedule** — the 8 patterns in T5.i, each a material breach with a defined cure period.
- **Back-to-back indemnity** — the Licensee must include, in its own end-user terms, a materially equivalent indemnity from the end-user back to the Licensee, protecting Rules Engine as a beneficiary.

#### C4.b Consultant Seat — non-customisable footer + T&Cs

**Non-customisable PDF footer text** (per T6.d; anchored to BoardPro comparator per [M6-11] §Module 6A):

> "Regulatory reference produced by {consultant_firm_name} using content infrastructure licensed from Rules Engine. Interpretation and application is the professional responsibility of {consultant_firm_name}. Verbatim regulatory text; not compliance advice. Current as at {as_at_date}."

**Consultant T&Cs — required clauses:**
- **No-legal-advice** — "The Service provides regulatory content and reference tools. It does not provide legal advice, professional advice, or compliance certification. Where you use the Service in advising your own clients, that advice remains yours."
- **Indemnity** — Consultant firm indemnifies Rules Engine against any claim by the firm's clients arising from the firm's use or presentation of Service output.
- **Permitted use** — internal use by the firm's staff to support the firm's advisory work; white-label PDFs may be delivered to the firm's clients provided the non-customisable footer is intact.
- **Prohibited use** — reselling the raw obligations register as a data product; removing the footer; presenting Service output as "compliance certified" or equivalent.

**First-login acknowledgement modal** (mandatory click-through):

> "The Rules Engine Consultant Seat is a regulatory reference tool. It does not provide legal or compliance advice. Interpretation of NDIS Rules for your clients' specific circumstances is your professional responsibility. I acknowledge this and accept the Terms of Service."

#### C4.c Provider Self-Serve (SKU 3, deferred — but the language is drafted now for readiness)

**Sophisticated-user acknowledgement modal** (every session, per [M6-11] §Module 6A "the highest-risk SKU — non-sophisticated end-user, no professional intermediary, most sympathetic plaintiff"):

> "This tool provides verbatim NDIS regulatory text with citations and effective dates. It is not a compliance check, an audit outcome, or professional advice. NDIS compliance carries civil penalties up to $3.3M and criminal exposure for individuals and directors (Integrity & Safeguarding Act 2026). Before relying on any regulatory reference from this tool, obtain independent professional advice from a registered auditor, lawyer, or NDIS registration consultant."

**ToS clauses:**
- Sophisticated-user acknowledgement (as above, replicated).
- Mandatory "seek independent review" prompt fires at every PDF export and at every "add to my obligations register" action.
- No pass/fail semantics anywhere in the UI (enforced by lint gate — a port of `scripts/lint_fabricated_verdicts.py`).
- Cap on liability: nominal ($100) — this SKU sees the least protective contract chain, so posture is defensive.

**Realistic acknowledgement (per [M6-11] §Module 6A):** ToS will not save the founder if a provider is fined $3.3M under the Integrity Act 2026 and blames the tool. The primary defence is product design (no verdicts, no pass/fail, mandatory independent-review prompts, sophisticated-user gating), not paper.

---

### C5. Australian PI + Product Liability Insurance

**Verified 2026-08-06** (WebSearch on `tech PI insurance Australia SaaS BizCover DUAL Chubb`):

- **BizCover** — comparison platform, distributes DUAL, Chubb, and others; cover from $250k to $10M for tech PI; targets businesses with turnover ≤$10M (fits a solo founder).
- **DUAL Australia** — IT Liability policy includes extended continuous cover, product-recall expenses, contractual liability.
- **Chubb Australia** — PremierTech2 package: technology professional liability + first- and third-party cyber + public and product liability. Chubb explicitly covers software development, technology services.
- **Aon**, **Marsh** — brokers, not carriers. Would place with same carrier pool.
- **Vero** (Suncorp) — general PI; not specifically technology-focused.

**Rough premium range for a solo founder, no employees, turnover <$500k first year** `[INFERENCE]` (BizCover published anchors + broker-quote norms):

| Cover limit | Approx annual premium | Notes |
|---|---:|---|
| $2M | $2,000–4,000 | Base competent-founder policy, standard tech-PI wording |
| $5M | $4,000–7,000 | The threshold most enterprise customers require in their contracts |
| $10M | $7,000–12,000 | Only if an OEM licensee's MSA requires it (Volaris/Centro-ASSIST-tier procurement may) |

**Carriers known to decline compliance/legal-tech risks:** none identified in this session's search. `[UNVERIFIED]`. The known-declining pattern applies to actual legal advice (regulated practice), not to regulatory-content library products; the founder's positioning as library-not-oracle is exactly the frame that keeps a tech-PI underwriter comfortable.

**Recommendation:**
- Minimum before first OEM licence signed: **$5M PI + $5M public-and-products liability + $2M cyber**, per policy year, single-claim and aggregate.
- Broker: BizCover for the first quote (cheapest onboarding); if any OEM licensee's MSA requires bespoke wording, escalate to a specialist broker (Aon Tech PI team or Fenton).
- Line-item exclusions to watch for: **content-liability sub-limits** (some tech-PI wordings exclude claims arising from content published to third parties; this is exactly the exposure). Have broker confirm the wording covers regulatory-content publication.
- **Kill signal (X4):** if no AU carrier will quote $5M cover at <$50k annual premium, the unit economics change materially — SKU 1 pricing floor rises.

---

### C6. UPL and Unregistered-Advice Risk

#### C6.a Legal Profession Uniform Law

**Verified 2026-08-06** (WebSearch on `Legal Profession Uniform Law legal information legal advice software Australia`):
- Uniform Law adopted in NSW + VIC from 1 July 2015; WA from 1 July 2022.
- Prohibits any entity other than a 'qualified entity' from **engaging in legal practice** (Uniform Law s10).
- Legal *information* (statement of what the law is) is not "legal practice"; legal *advice* (application to a person's facts) is regulated.

Confirmation with citation: `Legal Profession Uniform Law Application Act 2014 (Vic) Sch 1 s10`. Precedent for research/reference software (LexisNexis, Westlaw, Practical Law, TrustArc/Nymity) shipping without UPL exposure has been unbroken; searched — no AU UPL enforcement action against a research/reference tool surfaced. `[UNVERIFIED]` for exhaustiveness.

**Library posture (all SKUs):** clause text + citation + effective date is legal information. It is not legal advice. Reinforced by:
- No "you must / you should / you are required to" language (enforced by liability-language scanner, T7 row 10).
- No pass/fail verdicts (enforced by fabricated-verdict lint, T7 gate 11 analogue).
- Mandatory disclaimer strings on every user-facing surface (T5.a, T6.d, C4.b, C4.c).

**Verdict: not UPL under Uniform Law.** Founder should still obtain a one-time AU solicitor review of the disclaimer stack + licence agreement before first OEM signing (~$3–5k `[INFERENCE]`), for completeness rather than because a clear risk has been identified.

#### C6.b Immigration assistance analogue

Searched: no AU regime restricts "NDIS registration assistance" analogous to the Migration Agents Registration Authority (MARA) regime for immigration. Confirmed by absence in [M1-5] §Module 2 census (which enumerated named registration consultants without any suggesting they hold a regulator-issued licence). **Not analogous, no restriction.**

#### C6.c AHPRA / allied-health restrictions

The tool does not deliver clinical services; it publishes regulatory content. AHPRA regulates registered health practitioners (medical, nursing, allied health). No AHPRA regime restricts publishing NDIS regulatory content. `[UNVERIFIED-PRIMARY]` — but the absence of any such regime in the [M1-5] Module 2 buyer census (which included allied-health-adjacent consultancies like Nacre) is strong indirect evidence.

#### C6.d NDIS Commission / NDIA restriction on who may advise providers

**Verified 2026-08-06** (WebSearch on `"NDIS Commission" vendor accreditation registration compliance software provider approval scheme`): no vendor-registration or vendor-approval scheme surfaced. Commission-approved auditors (AQAs) are regulated; software vendors serving providers are not. Confirmed by the [M1-5] §Module 4A observation that consultants operate without any peak body or licensing regime.

**Verdict: no regulator gatekeeping.** Founder can ship the tool without any Commission or NDIA approval.

---

### C7. Data-Handling Posture

#### C7.a Privacy Act 1988 (Cth) applicability

**MATERIAL UPDATE — verified 2026-08-06** (WebSearch on `Privacy Act 1988 Australia small business exemption $3 million turnover APP entity SaaS`):

> "The long-standing $3 million turnover exemption from the Privacy Act has been removed, meaning almost every business must now comply with federal privacy law, no matter its size."

This is a **change from the assumption in the prior four docs**, which treated the small-business exemption as a live escape hatch. The exemption's removal is confirmed by the IAPP and Schiller Legal search results (2025 legislative package: Privacy and Other Legislation Amendment Act 2024 → phased rollout).

**Consequence for Rules Engine:**
- The founder IS an APP entity, regardless of the <$3M turnover floor.
- The tool stores provider profiles (ABN, registration status, service types, LGA, worker headcount bracket, RP flag, SIL flag) and consultant user data (email, name, firm affiliation).
- **NO participant PII is stored** — this is a deliberate scope decision and must be enforced at the schema level (no participant name / DOB / NDIS number / disability info fields anywhere in the schema).

#### C7.b Australian Privacy Principles applicability

Applicable APPs (with the small-business exemption gone):
- APP 1 (open and transparent management) — publish a Privacy Policy.
- APP 3 (collection of solicited personal information) — collect only what is needed to serve the tool.
- APP 5 (notification of collection) — collection notice at signup.
- APP 6 (use or disclosure) — use profile data only for the purpose collected.
- APP 8 (cross-border disclosure) — critical: Supabase's default region may be outside AU (see C7.d).
- APP 11 (security of personal information) — Supabase RLS + encryption at rest cover this.
- APP 12 (access to personal information) — a data-export flow per firm-user.

#### C7.c Notifiable Data Breach obligations

Applicable — the founder must notify the OAIC and affected users of an eligible data breach within 30 days. This obligation activates automatically as an APP entity. Founder should have an incident-response runbook before launch (~4 hrs to draft from an OAIC template).

#### C7.d Cross-border data flow

- Vercel default region: multi-region edge; the function-execution region can be pinned via `vercel.json` → `regions: ["syd1"]` for Australian data residency.
- Supabase: create the project in the Sydney region (`ap-southeast-2`).
- Postmark / SES: US-region providers by default. **Set SES region to `ap-southeast-2`** and consider Australia-based email providers (e.g. Sinch, Mailgun EU/AU) if a customer requires "all data in Australia" contractually.
- APP 8 requires taking reasonable steps to ensure an overseas recipient does not breach the APPs. Using AU-region hosting is the simplest way to avoid triggering APP 8 at all.

**Recommendation for minimum privacy posture at launch:**
1. Publish Privacy Policy (draft in C9, ~$500 template from LegalVision / Sprintlaw).
2. Collection notice at signup.
3. Data-export self-service in `/settings/firm`.
4. AU-region hosting everywhere (Supabase Sydney, Vercel `syd1`, SES `ap-southeast-2`).
5. NDB response runbook.
6. Explicit schema-level ban on participant PII fields (enforced by schema-contract gate T7 row 7).

---

### C8. Commercial-Licence Requests — DRAFT ONLY

**DO NOT SEND. Founder sends after review.**

#### C8.a Draft to NDIA — Pricing Schedule commercial licence

```
To:      [NDIA Pricing Team — see https://www.ndis.gov.au/providers/pricing-arrangements
         'contact us' link for current addressee]
Subject: Request for commercial licence — NDIS Pricing Arrangements and Price Limits 2026-27

Dear NDIA Pricing team,

I operate an Australian regulatory-technology business that publishes machine-readable
references to NDIS regulatory instruments to NDIS providers and their consultants. Our
core product surfaces verbatim clause text with citations and effective dates from the
Federal Register of Legislation (CC-BY-4.0). Customers have requested we extend the
same coverage to the NDIS Pricing Arrangements and Price Limits and NDIS Support
Catalogue, so that a single reference layer serves the entire regulatory picture.

The current Pricing Schedule PDF carries a Creative Commons Attribution-NonCommercial
notice, which does not permit commercial republication. I am writing to request either:

  (a) a licence to republish the price limits and item descriptions in a
      commercial software product, with clear attribution to the NDIA as the
      source and a link to the current NDIA source PDF; or
  (b) confirmation of the specific ingestion boundary that would be acceptable
      under the current notice (e.g. structured data extraction of item numbers
      and price limits only, without narrative rule text).

I would be grateful for a response indicating the licensing pathway and any fee
that would apply. Happy to provide further detail on the product or execute an
NDIA-drafted licence agreement.

Yours sincerely,
[Founder name]
[Contact]
```

Addressee role: NDIA Pricing & Payments team; escalation path via NDIA General Counsel if no substantive reply in 60 days.

Fallback if request fails / takes >90 days: **pointer-only architecture (C2 option 1)** with links out to the NDIA-hosted PDF. This is deferrable and is not on the MVP critical path.

#### C8.b Draft to NDIS Commission — any NC-marked guidance (Regulated Restrictive Practices Guide)

```
To:      [NDIS Commission Communications — enquiries@ndiscommission.gov.au]
Subject: Licence enquiry — Regulated Restrictive Practices Guide

Dear NDIS Commission,

I operate an Australian regulatory-technology business that publishes verbatim
references to NDIS regulatory instruments to NDIS providers and their consultants.

The Regulated Restrictive Practices Guide is published under a Creative Commons
Attribution-NonCommercial International licence, which does not appear to permit
commercial republication.

I am writing to request either:

  (a) confirmation that referencing the Guide by title, section heading, and URL
      (with no verbatim republication of Guide text) is permissible in a commercial
      software product, or
  (b) a licence to republish the Guide's content in the same product, with
      attribution to the NDIS Commission and a link to the current source.

Grateful for a response indicating the acceptable boundary.

Yours sincerely,
[Founder name]
[Contact]
```

Fallback: paraphrase-only + link out.

---

### C9. Contract Templates Required for Launch

| Contract | Purpose | Who signs | Minimum clauses | Self-draft or solicitor? | Rough solicitor cost `[INFERENCE]` |
|---|---|---|---|---|---:|
| **OEM Licence Agreement** | License Rules Feed to OEM vendors | Rules Engine × Licensee (director-level both sides) | Definitions, Grant of licence, Permitted use, Forbidden-use schedule (T5.i), API access + rate limits, SLA (freshness + uptime), Fees + billing, Intellectual property, Content warranty (verbatim from source; no warranty of fitness), Limitation of liability + cap, Indemnity (Licensee → Rules Engine + back-to-back Licensee → end-user), Term + termination, Assignment, Dispute resolution (AU jurisdiction, NSW law), Force majeure, Confidentiality | **Solicitor** — this is the highest-value contract; use LegalVision / Sprintlaw as a starting template but engage a technology-contracts solicitor for the review | $3k–8k first template, $500–1.5k per subsequent variation |
| **Consultant Seat T&Cs** | Consumer-facing terms for the seat product | Firm accepts click-through | No-legal-advice, Indemnity, Permitted use, Prohibited use (footer tampering, resale), Fees, Term, Termination, Data ownership, Data export on termination, Governing law | **LegalVision / Sprintlaw template + founder-tuned** | Template ~$400–800; solicitor review ~$1–2k |
| **Provider Self-Serve ToS + Privacy Policy** | End-user consumer terms for self-serve | User accepts click-through | Sophisticated-user acknowledgement, No-advice, Indemnity, Fees, Permitted use, Termination, Data handling | **Template + founder-tuned** | Template ~$400–800 |
| **Cookie Notice** | Cookie disclosure per Vercel Analytics + Stripe | User accepts banner | Cookie categories, opt-out | **Self-draft from LegalVision template** | ~$100 template |
| **DPA (Data Processing Addendum)** | Only if an OEM licensee is a controller under AU or foreign privacy law and requires a DPA | Contract addendum on request | Standard DPA clauses | **Trigger:** first OEM licensee requests it. Then solicitor. | ~$1–2k |
| **Sub-Processor List** | Public list of Vercel, Supabase, Stripe, SES, BetterUptime | Published on website | | Self-draft | $0 |
| **Master Services Agreement (MSA)** for the Consultant Seat firms above 5 seats | Optional; some firms will require it | Firm × Rules Engine | Same shape as OEM but slimmer | **Template + founder-tuned** | ~$1k template |
| **Website Terms of Use** | Basic terms for the marketing site | | Standard | Template | ~$200 |

**Total solicitor cost to launch: ~$5k–12k.** All figures `[INFERENCE]` from Sprintlaw / LegalVision published packages and standard tech-contracts hourly rates.

---

### C10. Regulatory Sandbox / Notification Questions

Verified 2026-08-06 (search reused from C6.d):

- **NDIS Commission:** no vendor-registration or vendor-approval scheme identified for compliance tooling. The Commission regulates PROVIDERS (registration) and AUDITORS (approval), not vendors selling to them.
- **NDIA:** no vendor scheme identified. NDIA maintains the NDIS Support Catalogue and Pricing Schedule; vendors that surface those materials commercially do so under the CC-BY-NC constraint discussed in C2, not under a scheme.
- **ACCC:** general ACL applies (s18 misleading conduct — discussed in C4). No specific ACCC scheme for compliance / regulatory-data tools identified. ACCC has published guidance on comparison websites and on false claims about verification / accreditation — a rules-engine that never makes such claims (per its library posture) is not caught. `[UNVERIFIED]` for exhaustiveness of the ACCC guidance search; founder should read the ACCC "Comparator websites — a guide for industry" (2015) before publishing any comparative material.

**Verdict: no mandatory scheme to join. No voluntary scheme required.**

---

### C11. Branding Constraints and Enforcement Patterns

Anchor throughout: the NDIA site-wide copyright and trademark notice at https://www.ndis.gov.au/policies-rules-and-legal/using-our-websites-and-social-media/copyright, verified 2026-08-06 (page dated "current as of 3 May 2026"). This section sits at C4-liability-posture depth because getting branding wrong triggers a distinct enforcement pipeline that is orthogonal to content licensing.

#### C11.a Trademarked terms

The NDIS acronym and the NDIS logo are registered trademarks of the NDIA (per the Trademarks section of the notice cited above). The CC BY-NC 3.0 AU licence explicitly excludes logos, trademarks, and any third-party material from its grant.

**Rule for this product:** the product name, its domain, and its marketing copy MUST NOT contain the string "NDIS" or any NDIS logo variant. This is a bright-line rule, not a preference. It flows into the Z1 decision "Product name — does it include 'NDIS' or not?".

#### C11.b Forbidden affiliation language

Every phrase pattern the NDIA copyright page calls out as enforceable, listed so the marketing-copy scanner (C11.e) can pattern-match:

1. **"NDIS approved"** — implies NDIA endorsement of a third-party product or service.
2. **"100% NDIS funded"** — implies a funding relationship.
3. **"NDIS packages"** or **"NDIS bundles"** used as product- or service-names — implies the product is an NDIS-branded offering.
4. **Domain names containing "NDIS"** — including subdomains and hyphenated variants (`ndis-tools.com.au`, `myndisapp.com`, etc.).
5. **Business names containing "NDIS"** — including registered business names and trading names.
6. **"I heart NDIS" / "we support NDIS" logos or graphics** deployed in any way that implies a funding or endorsement relationship.
7. Any use of the NDIS logo, or of a graphic that could be confused for the NDIS logo, on product, marketing, or documentation surfaces.

#### C11.c Enforcement pattern

Cite: https://www.ndis.gov.au/policies-rules-and-legal/using-our-websites-and-social-media/copyright (verified 2026-08-06). The NDIA states on that page that it actively enforces its trademarks and copyright, that it issues cease-and-desist correspondence to parties misusing the NDIS acronym, logo, or affiliation language, and that where the conduct amounts to misleading or deceptive claims in trade it refers matters to the ACCC.

The pattern in public statements targets:
- Misleading affiliation with the NDIA (implying endorsement, approval, funding, or partnership).
- Trademark misuse (acronym and logo).
- Product- or service-name confusion.

The pattern does **not** — based on the copyright page and search results verified 2026-08-06 — target compliance databases that reproduce rules content with proper attribution under the CC BY-NC 3.0 AU licence. No public enforcement action against a compliance-reference product for reproducing regulatory content with attribution has surfaced. `[UNVERIFIED]` for exhaustiveness of enforcement history — absence of surfaced action is not evidence of absence, but is the best signal available.

**Consequence for Rules Engine posture:** the content-ingest strategy in C2 and C3 is compatible with the enforcement pattern; the naming and marketing surface is where the enforcement risk actually lands.

#### C11.d Product-naming guidance

**Recommendation:** the product name MUST NOT reference NDIS. Naming around the trademark up-front is cheaper than a rebrand after a cease-and-desist. The positioning ("Australian disability-sector regulatory reference") is descriptive-only and the marketing copy can describe the sector accurately without borrowing the acronym.

Three worked examples of compliant naming patterns for the founder to pick from (descriptive-only — sector described, acronym not borrowed):

1. **"ProviderRules AU"** — foregrounds the audience (providers) and the artefact (rules); geographic scope in the suffix.
2. **"CareCode Library"** — foregrounds the content class (a code library for the care sector); "library" reinforces the library-not-oracle posture from C4.
3. **"Disability Sector Compliance Feed"** — descriptive with no borrowed terms; verbose but unambiguously non-affiliated.

Founder picks one, then registers the domain, ABN business name, GitHub org, and social handles before OEM outreach starts. Downstream decisions in Z1 (repo shape, publish-artifact URL) inherit from this pick.

#### C11.e Marketing-copy guardrail

Wire a keyword scanner into the pre-push hook next to the liability-language scanner (T7 row 10). The scanner runs over every public-facing surface: website copy, sales collateral (`docs/marketing/*.md`), PDF footer templates, API payload disclaimer strings, README, and every markdown file destined for publish.

**Flag on any occurrence of:**
- Any exact phrase from C11.b (1)–(6).
- The bare string "NDIS" used as a brandable term — i.e. not preceded by a factual descriptor like "the NDIS Act 2013", "the NDIS Quality and Safeguards Commission", or "the NDIS Practice Standards".
- The strings "NDIS approved", "NDIS certified", "NDIS partner", "NDIS endorsed", "authorised by NDIS", "official NDIS", "NDIA-approved".
- Any file or image asset with "ndis" in the filename (asset-filename scan) — catches accidental logo commits.

Implementation: extend `scripts/liability_language_check.py` to accept a second lexicon file (`scripts/branding_forbidden_terms.txt`), or add a sibling `scripts/ndis_branding_check.py`. Runs in pre-commit AND pre-push. Failing the scan blocks the commit or push.

#### C11.f Consequences per SKU

- **OEM Rules Feed (SKU 1).** The OEM licence agreement (C9) must include a clause requiring licensees not to expose "NDIS approved", "NDIS certified", or any other affiliation-claiming language in their end-user UI. Add to the forbidden-use schedule at T5.i as items 9–10 (branding-affiliation prohibition; NDIS-as-brandable-term prohibition). Material-breach cure period the same as items 1–8.
- **Consultant Seat (SKU 2).** PDF footer template and web UI must not include NDIS as a brandable term. Where clause text or a document title contains "NDIS" (unavoidable — the Act is called the NDIS Act 2013), the string is a factual reference to a named legal instrument and is not brandable use. The non-customisable footer in C4.b already conforms; verify no other UI surface introduces the acronym as a brandable term.
- **Provider Self-Serve (SKU 3, deferred).** Same as Consultant Seat, plus the sophisticated-user acknowledgement modal at C4.c should include a sentence: "This tool is not affiliated with the National Disability Insurance Agency or the NDIS Quality and Safeguards Commission." Fold into the ToS clause pack.

#### C11.g Insurance implication

Tech-PI carriers price known enforcement patterns into their wording. When the founder obtains carrier quotes per C5, disclose the NDIA trademark enforcement pattern in the application — a two-line disclosure at quote time ("the product operates in a domain where the primary trademark holder actively enforces via cease-and-desist and ACCC referral; product naming, marketing, and OEM contracts are designed to avoid trademark exposure — see C11 of the scope document") is cheaper than a coverage dispute post-bind. Underwriters do not like surprises after they have priced the risk.

---

## CROSS-CUTTING

### X1. Port-Specific Risks — NSW-Planning Coupling Leaks

Each identified leak from T1.f, plus verdict and rework estimate:

| Leak | Location | Verdict | Rework hrs |
|---|---|---|---:|
| `DocumentType` enum hardcodes `{SEPP, LEP, DCP}` | `services/version_manager.py:24-27` | **EXTRACT TO INTERFACE** | 8 (make it table-driven `document_type` registry with `code`, `name`, `jurisdiction`) |
| NSW zone/precinct semantics baked into applicability taggers | `enrichment/extractors/applicability_tagger.py`, `site_condition_tagger.py`, `layer_topic_tagger.py` | **LEAVE COUPLED (parallel product)** for NSW; **NDIS-SPECIFIC REBUILD** for the new product (already scoped in T1.b) | 40 (already scoped) |
| `FormerCouncilArea` enum with three NSW council values | `src/models.py:11-14` | **DELETE for NDIS-scoped model file; KEEP for NSW-scoped model file** — split `src/models.py` into `src/models/nsw.py` and `src/models/ndis.py` | 12 |
| `services/nsw_planning_api.py` name misleadingly generic | `services/nsw_planning_api.py` | **LEAVE COUPLED (parallel product)** — no rename needed if two engines live in one repo (see X2) | 0 |
| Schema-contract baseline is NSW-DB-shaped | `scripts/schema_contract_baseline.json` | **EXTRACT TO PER-DB** — the checker is table-agnostic, but the baseline must be regenerated per-DB, so create `scripts/schema_contract_baseline.ndis.json` alongside | 4 |
| `services/live_compliance_engine.py`, `services/universal_regulatory_engine.py` — nominally "universal", actually NSW-property-scoped | `services/live_compliance_engine.py`, `services/universal_regulatory_engine.py` | **DELETE for NDIS**; **LEAVE COUPLED** for NSW | 0 |
| Council-specific script constants scattered across `scripts/*` | Various | **LEAVE COUPLED (parallel product)** — no leak into non-NSW modules identified this session | 0 |

**Total X1 rework:** ~24 hrs (~0.6 wk). Small.

**Verdict:** the engine's NSW coupling is far shallower than it looks. The couplings are almost entirely in the domain-content files that get deleted-or-rebuilt anyway (T1.a and T1.b). The verification-gate infrastructure — the actual moat — is domain-agnostic almost everywhere and ports at very low cost.

---

### X2. Repository Structure Decision

**Options:**

**(A) Monorepo with NDIS as `/ndis` subtree.**
- Pros: shared tooling reuse (pre-push hooks, gates, QA report format, CI, deploy pipeline); shared secrets management; single Vercel/Supabase project pair per environment; a shared `services/extracted_data_integrity.py` improvement helps both engines; competitive advantage in maintainer velocity (~30% faster iteration than dual-repo, `[INFERENCE]` from monorepo literature).
- Cons: NDIS branding lives inside a NSW-branded repo; a future NDIS OEM licensee (Centro ASSIST, FormaOS) can potentially inspect the repo (private, but any breach or accidental publicity is competitive signal); secrets isolation is per-env-var not per-repo; deploy target separation is done via `vercel.json` per-app, not repo boundary; code review complexity rises because every PR carries both engines' state.
- Ops burden: LOW (~0 net extra hours; hooks already exist).

**(B) Fresh repo.**
- Pros: clean brand separation; clean secrets separation; clean deploy pipeline separation; no risk of NDIS work being visible in a NSW-planning-branded repo.
- Cons: every gate and hook must be re-set up from scratch or copied and diverged; the shared-tooling reuse becomes a submodule / package-publish exercise; `services/extracted_data_integrity.py` improvements have to be back-ported; slower iteration; ~40 hrs of one-time repo-bootstrap (hooks, CI, gates, baselines).
- Ops burden: MEDIUM–HIGH.

**Recommendation: (A) monorepo with `/ndis` subtree**, for these reasons:
1. Shared verification-gate infrastructure is the WHOLE point of "we built the engine over 2 years" — a dual-repo forfeits that leverage.
2. Competitive-signal risk is manageable: the repo is private; the NSW-planning brand does not appear anywhere in an OEM licensee's contract or product; the NDIS product will have its own domain, its own docs, its own marketing.
3. Ops burden of a fresh repo is real (~1 wk of bootstrap) and detracts from corpus + OEM work at the moment they matter most.
4. Future refactor to a fresh repo, if the NDIS product outgrows the NSW product, is a mechanical operation on a mature codebase, not a hard-to-reverse decision now.

Named tradeoff: **competitive signal** — a NDIS OEM licensee doing a security review might request repo access; the founder must be prepared to grant read access to `/ndis` only (git-worktree or a stripped fork) or to explain why the repo also holds the NSW code. This is a two-minute conversation, not a deal-breaker.

---

### X3. Sequencing Recommendation — Week-by-Week 12-Week MVP Build Plan

Anchor: [M6-11] §Module 9 90-day launch plan. This section fills in the falsifiable gates.

| Wk | Deliverables | Gates | Dependencies | Owner-review checkpoint |
|---:|---|---|---|---|
| **1** | Corpus manifest verified in AU home network; every F-number's licence notice quoted verbatim into `docs/ndis-corpus-licence-notices.md`; schema T3.e deployed to Supabase Sydney; per-instrument fetch adapters for the 4 MVP-slice instruments (F2018L00631, F2018L00632, F2018N00041, F2018L00629) drafted | C1 licence-audit pass; schema-contract gate green on new schema | Founder AU home network; Supabase project created | **Gate: every MVP-slice F-number's copyright notice is CC-BY 4.0 verbatim, no surprises. If any is not CC-BY, KILL that instrument (X4 kill signal #5).** |
| **2** | Fetch adapters for the 4 MVP instruments produce raw HTML + PDF snapshots into `tests/fixtures/ndis/{f_number}/compilation-1/`; source-hash gate green; per-instrument parser scaffolds (sectionizer, defined-term extractor, cross-ref extractor) written | Source-hash gate green; ported liability-language scanner runs green on all new user-facing surfaces (there are none yet) | Week 1 | **Gate: raw fetch succeeds for every MVP instrument; hash-locked fixtures land.** |
| **3** | 100% of MVP-slice clauses extracted; ported gates 1–5 (fabricated/conflicting/absent/hash/liability) green on the extracted set; controls-provenance ratchet rewrite complete | Ported gates all green | Week 2 | **Gate: extracted clause count matches human review to within 5%.** |
| **4** | New clause-text byte-identity gate (T7 gate 6/11) written and green; new attribution-headers gate (T7 gate 12) written and green; effective-date engine (T3) live for MVP slice | 6 gates green; `as_at(t)` correctness tests all pass | Week 3 | **Gate: 100% clause byte-identity to source; every clause resolves at three test dates (before, at, after commencement).** |
| **5** | Amendment-monitoring loop (T4) live for the 4 MVP instruments; daily cron scheduled; monthly-full-sweep cron scheduled; monitoring dashboard at `/internal/gate-status`; **published trust artifact** (per [M6-11] §Module 9 — a live amendment ledger with every diff cited) at `plotdetect.com.au/ndis` (URL placeholder) | Silent-error hash re-fetch fires and passes on day-30 simulated run | Week 4 | **Gate: amendment loop runs for 5 days without a false alert; monthly sweep produces zero deltas against the freshly-captured baseline.** |
| **6** | **First demoable = end of week 6.** Corpus + engine + gates + monitoring all live for the SIL slice. OEM API scaffold (T5.a endpoints returning static data) up; per-licensee mapping template (T5.h) drafted | Contract tests pass on the scaffold | Weeks 1–5 | **Gate: the SIL-slice demo runs end-to-end. Start OEM outreach in parallel per [M6-11] §Module 9 90-day plan.** |
| **7** | OEM API real (queries the DB); auth (API key model); rate-limiting middleware; sandbox environment live; webhook contract implemented + signed; weekly snapshot cron | OEM contract tests pass; webhook replay tests pass; signature-verification tests pass | Week 6 | **Gate: first OEM design-partner conversation booked (per [M6-11] §Module 9 Wk 7–8).** |
| **8** | OEM feed live to sandbox tier (100% Tier A CC-BY corpus); pricing pointer table (C2 option 1) live; documentation site (`docs.rulesengine.au` placeholder) with OpenAPI spec + auth guide + webhook guide + forbidden-use schedule | Snapshot integrity test passes | Week 7 | **Gate: first OEM pilot has a signed LOI (per [M6-11] §Module 9 pass criteria).** |
| **9** | Consultant Seat scaffold (Next.js app skeleton, auth, tenant isolation via Supabase RLS, first two pages: `/onboarding`, `/dashboard`); provider-profile schema T6.b live | Jest tenant-isolation suite green | Week 8 | **Gate: consultant validation sprint pass conditions met per [M6-11] §Module 9.** |
| **10** | Consultant Seat obligations-register query surface T6.c + `/profiles/[profileId]` page; PDF renderer with non-customisable footer T6.d; footer-lock gate wired | PDF footer byte-identity test green; footer-lock gate blocks a test-tampering PR | Week 9 | **Gate: first Consultant Seat design partner using the tool in beta.** |
| **11** | Consultant Seat amendment digest email pipeline T6.e; monthly cron scheduled; first digest test fired; billing (Stripe) integrated | Digest deliverability green (SPF/DKIM/DMARC configured); Stripe test-mode transactions pass | Week 10 | **Gate: first paying customer invoiced.** |
| **12** | Second OEM licensee onboarded to sandbox; second-and-third Consultant Seat customers close from pre-commit list; monthly full-corpus sweep passes; incident-response runbook drafted; NDB notification template ready | All gates green in CI | Week 11 | **Gate: ≥1 paid OEM licensee + ≥3 paid Consultant Seats + all gates green + monthly sweep clean. Ship it.** |

**Demo-slice demoable point: end of week 6.** OEM+Seat live for real: end of week 11. First revenue: end of week 12.

---

### X4. Kill Signals

Ordered by likelihood × severity. Each signal has a detection mechanism, a detect-by week, and an abort action.

1. **Pricing Schedule turns out CC-BY-ND** (No Derivatives). Detection: C2 licence resolution during Week 1 corpus audit. Abort action: keep pointer-only architecture permanently; NEVER attempt paraphrase-plus-link; if a customer demands embedded pricing rules, escalate to commercial-licence request (C8.a) with a 90-day timeline. **Severity: LOW-MEDIUM** — MVP does not include pricing anyway; only affects an upsell.

2. **Federal Register offers no machine-readable feed and rate-limits scraping aggressively.** Detection: T4.a verification during Week 1 (fetch-adapter build). Abort action: fall back to daily HTML scrape of "what's new" listing; narrow the promised SLA from "1 business day" to "1 week"; reprice SKU 1 down accordingly. **Severity: MEDIUM** — the SLA is a moat but not the whole moat.

3. **Existing gates require substantial rewrite.** Detection: Weeks 3–4, when the ported gates (T7) are pointed at NDIS data. Abort action: if the effort blows past 3 wk (i.e. the "3–6 wk port" estimate proves optimistic), pause corpus work and finish the gate port properly before continuing — never ship with a broken gate as it turns the whole product into snake oil. **Severity: MEDIUM** — resettable, not fatal.

4. **AU carrier declines PI insurance below $50k premium.** Detection: quote gathering in parallel to Week 6 gate. Abort action: reduce cover to $2M (a level BizCover published anchors suggest is achievable at $2–4k premium); rework the OEM MSA to require Licensee to carry the delta; if that is refused, defer OEM launch until a specialist broker (Aon, Fenton) can place. **Severity: HIGH** — unit economics break at $50k premium against a $2–5k/mo × 5 licensees Year-1 gross.

5. **Any Tier A instrument turns out non-CC or with a custom notice.** Detection: C1 audit during Week 1. Abort action: drop that instrument from the MVP scope; escalate to commercial-licence request; re-scope the promise ("Tier A minus X" instead of "full Tier A"). **Severity: HIGH** for an MVP-slice instrument (F2018L00631, F2018L00632, F2018N00041, F2018L00629); LOW-MEDIUM for a non-MVP instrument (Worker Screening, Procedural Fairness).

Additional kill signals inherited from [M6-11] §Module 11 that this scoping does not weaken:

6. **Solo-founder maintenance SLA trap** — a single missed amendment retroactively destroys "provenance-verified." Detection: T4.e SLA monitoring. Abort action: hire content-ops FTE by month 12 regardless of ARR, OR narrow SLA to weekly and reprice, OR partner with a legal-publishing firm.

7. **Incumbent ships clause-provenance in one release** (BNG SPP, Audit Pilot, FormaOS, Centro ASSIST). Detection: quarterly competitor scan; release-notes monitoring. Abort action: pivot OEM value from "content" to "content-plus-ops-plus-legal-review-attestation" or exit the OEM channel and refocus on Seat + Board SKUs.

8. **Privacy Act small-business exemption removal** (already crystallised, per C7.a). Not a kill signal; scope-adjustment already reflected in C7.

---

## Z1. DECISIONS THE FOUNDER MUST TAKE BEFORE BUILD STARTS

Ordered by dependency and consequence.

1. **Repo shape.** Options: (A) monorepo `/ndis` subtree; (B) fresh repo. **Recommend (A) per X2** — shared gate infrastructure is the moat, dual-repo forfeits it. Consequence of (B): +1 wk of bootstrap, ongoing back-port burden, cleaner brand separation.

2. **Reviewer of the corpus during v1.** Options: (a) founder alone; (b) founder + a named NDIS consultant on retainer (Tania Gomez, Sharon Floyd, or similar); (c) founder + a paid legal reviewer (~$300/hr, ~$3k/mo retainer). **Recommend (a) for MVP** with a clear intent to move to (b) at ≥$10k MRR — the moat is provenance discipline, not credential-name-dropping. Consequence of (c) at MVP: burn rate up ~$3k/mo before revenue.

3. **First OEM licensee target and pitch order.** Options ordered by [M6-11] §Module 9 pitch-difficulty ranking: FormaOS → Centro ASSIST → ClinicComply → Audit Pilot → Smart Compliance Systems. **Recommend FormaOS first** — highest content-maintenance-burden pain, warmest fit. Consequence of leading with Centro ASSIST: 60–90 day procurement cycle even for pilots.

4. **Consultant Seat pricing at launch.** Options: (a) $299/mo standard, $199/mo founding-member; (b) $199/mo standard, $149/mo founding-member; (c) $149/mo standard. **Recommend (a)** per [M6-11] §Module 9 validation-sprint anchor — the higher price tests seriousness. Consequence of (c): easier conversion, halves ARR per seat, harder to walk back.

5. **Insurance line before signing OEM #1.** Options: (a) $2M PI (cheap, may not meet MSA); (b) $5M PI + $5M public/products + $2M cyber (recommended in C5); (c) $10M package (expensive, only if procurement demands). **Recommend (b)**. Consequence of (a): may need to sign an amendment mid-negotiation; loss of goodwill.

6. **Pricing Schedule architecture.** Options: (i) pointer-only per C2; (ii) paraphrase + link if licence confirms CC-BY-NC (no ND); (iii) commercial licence request per C8.a. **Recommend (i) for MVP** and only pursue (iii) after a paying customer demands it. Consequence of (ii): irreversible legal exposure if the licence turns out to include ND.

7. **ES/SES ingest posture.** Options: (a) full ingest with a distinct `kind='explanatory_statement'` (and `'supplementary_explanatory_statement'`) enum value on the `instrument` table; (b) pointer-only link on the relevant clause records; (c) ignore entirely. **Recommend (a) full ingest.** Rationale: the ES documents already in the corpus (F2018L00633ES 1,536 lines; F2024L01257ES 2,235 lines; F2025L01383ES + SES 721 lines combined) are OPC-published context that consultants routinely use to interpret what a Rule means in practice — they are the single highest-leverage secondary content in the corpus and are CC-BY 4.0 clean (same platform-level licence, zero per-doc markers per C1.a). Extraction cost across the corpus ~8 hours. Downstream: schema `kind` enum expands to include `explanatory_statement` (and `supplementary_explanatory_statement`); T2 gets a per-ES parser stub (OPC ES template is well-defined, shallow variance); Consultant Seat UI needs to surface ES snippets alongside the operative clause with clear "Explanatory Statement — persuasive context, not operative law" labelling.

8. **Worker Screening Rules extract freshness.** Options: (a) proceed with compilation No. 4 (2021) for the MVP demo slice, then re-fetch latest before shipping; (b) block extractor coding on this instrument until a fresher compilation is fetched; (c) proceed and accept staleness (not recommended). **Recommend (a).** Rationale: the SIL demo slice does not depend heavily on worker-screening amendments; the parser is what matters for MVP, and the 2021 template will exercise the parser the same as a 2026 one would. Downstream: adds a "re-fetch latest compilation of F2018L00887 from AU network; if compilation No. > 4 exists (candidates F2022C… / F2023C… / F2024C… — 2024 amendment F2024L00867 seen in Federal Register search — F2025C… / F2026C…), re-extract and re-run gate T7" to the pre-launch checklist; freshness verification is a 5-minute manual task before the Week-11 launch gate.

9. **Data residency default.** Options: (a) AU-region only (Supabase Sydney, Vercel `syd1`, SES `ap-southeast-2`); (b) multi-region for latency. **Recommend (a)** per C7.d — simplifies APP 8 compliance to nothing. Consequence of (b): APP 8 assessment for every processor.

10. **Product name — does it include "NDIS" or not?** Options: (a) name contains "NDIS" or "NDIA"; (b) descriptive-only name that references the sector without borrowing the acronym (three worked examples in C11.d: "ProviderRules AU", "CareCode Library", "Disability Sector Compliance Feed"). **Recommend (b)** — the NDIA copyright page confirms an active cease-and-desist + ACCC-referral enforcement pattern around the acronym and logo; naming around the trademark up-front is cheaper than a rebrand after enforcement contact. Downstream: this decision locks in the domain, brand assets, GitHub org, and sales collateral before OEM outreach starts, so it must be taken before decision 11 (Publish-artifact URL) rather than after.

11. **Publish-artifact URL.** Options: (a) NDIS product lives at `ndis.plotdetect.com.au` (subdomain, close brand); (b) fresh domain `rulesengine.au` or similar (recommended per [M6-11] §Module 9 90-day plan). **Recommend (b)** — fresh brand for a fresh audience; the NSW-planning association is a distraction to NDIS buyers. Inherits from decision 10: the domain must be consistent with the chosen product name and must NOT contain "NDIS" per C11.b(4).

12. **Whether to open a Consultant Seat design-partner pilot before OEM signs.** Options: (a) OEM first, Seat conditional on OEM signal; (b) both in parallel per [M6-11] §Module 6D. **Recommend (b)** — the segments do not overlap, and consultant sign-ups are useful social proof for OEM sales conversations.

13. **Whether to publish the OEM API OpenAPI spec publicly before the first licensee signs.** Options: (a) public from day 1 (SEO + trust artifact); (b) NDA-gated until first paying licensee. **Recommend (a)** — the schema is not the moat, the content + operations is; public OpenAPI is a trust artifact and speeds sales conversations.

---

## Z2. HONEST PERSON-WEEK ESTIMATE

**Single reconciled MVP number: 13–15 person-weeks to "OEM Rules Feed v1 live in sandbox + Consultant Seat v1 live to design partner", plus 2–4 weeks of buffer for the human-in-the-loop review time and licensing/insurance procurement.**

Stratified reconciliation with [M6-11] §Module 7:

| Stratum | This scoping (MVP) | [M6-11] §Module 7 | Divergence | Reason |
|---|---:|---:|---|---|
| (a) Engine port | 4 wk | 3–6 wk | agree at midpoint | — |
| (b) Corpus extraction (MVP demo slice) | 6 wk | 5.5 wk | agree | — |
| (c) Verification gates | 2 wk | (folded into port) | +2 wk | This scoping separates T7 explicitly to include the two NEW gates (clause-text byte-identity + attribution-headers). [M6-11] did not name them |
| (d) OEM API | 3 wk | (folded into "Month 3: launch") | +3 wk | [M6-11] said "Months 0–3: content ships first; Month 3: OEM API + consultant seat launch simultaneously" — the API build effort was implicit in the 12-week window, not stratified |
| (e) Consultant Seat | 4 wk | (folded into "Month 3–4 ship") | +4 wk | Same |
| (f) Infrastructure + gates wiring | 1 wk | (not stratified) | +1 wk | — |
| **TOTAL** | **20 wk MVP** | **8.5–11.5 wk to first demoable** | **+8–12 wk** | The [M6-11] figure is content + engine only; this scoping's figure is content + engine + OEM API + Seat — the shippable v1. When compared like-for-like (content + engine only) this scoping agrees at ~10 wk |

**I am neither more optimistic nor more pessimistic than [M6-11] — I am more granular.** The 8.5–11.5-wk figure was "first demoable" (implicitly a CLI/Postman demo of the corpus). The 12-week [M6-11] launch plan already implied ~12 wk to OEM + Seat live; this scoping's 20 wk is honestly larger because it includes buffer, verification gate additions, and infrastructure wiring that [M6-11] did not itemise but did not deny.

**If pressed for ONE number: ~15 person-weeks solo, corpus MVP + OEM + Seat live to design partners, no paying customers yet.** Add 4 weeks buffer for procurement (insurance, contract templates, first OEM negotiation) and the honest number to first paying invoice is **~19 person-weeks**. This tracks [M6-11] §Module 9 which called first paid invoice at week 11.

---

## Z3. HONESTY LEDGER

**Claims this document could not primary-verify.** Every one of the following must be re-verified from an AU home network before build starts.

- **All legislation.gov.au and ndiscommission.gov.au URLs 403'd** to WebFetch during the original scoping session (2026-08-06). This is partially resolved: the founder has since dropped `pdftotext -layout` extracts of 15 Tier A source PDFs into `docs/corpus-primary-sources/text/`, so clause structure and copyright-notice presence are now verifiable locally. Live compilation numbers, made-dates, and register-side metadata still require an AU-network fetch when values need to move.
- **F-numbers for Worker Screening Rules and Procedural Fairness Guidelines** — RESOLVED. Worker Screening Rules is F2018L00887 (principal, in force effective 31/07/2018) and Procedural Fairness Guidelines is F2018N00155 (principal; currently in force via compilation F2026C00166, comp #1 dated 28/01/2026). Both confirmed from Federal Register searches plus, for F2018N00155, the founder-provided PDF extract.
- **Federal Register machine-readable feed availability** (T4.a) is not confirmed. WebSearch 2026-08-06 did not surface a documented REST API; the Office of Parliamentary Counsel (opc.gov.au) page was 403 for WebFetch. Build-plan fallback is HTML scraping.
- **Whether specific Commission-published guidance PDFs carry per-document licence overrides** (C1.a, C3) — the pattern "zero per-doc notice" is verified across the 15 Tier A source PDFs currently in `docs/corpus-primary-sources/text/` (grep-verified 2026-08-06). Not every Commission guidance PDF has been extracted yet — the resolved finding is a pattern-inference from the extracted sample, not an exhaustive per-doc verification across the full guidance layer. Documents not yet extracted (Practice Standards booklet, Code of Conduct Guidance, Position Statements, Incident-Management Detailed Guidance, Complaints Detailed Guidance, Worker Screening Q&A, Provider Toolkit, Regulated Restrictive Practices Guide) should be extracted before their content is ingested.
- **Whether F2018N00155's Notifiable-Instrument template variance introduces parser edge cases beyond the estimated +2 hours** (T2.a, C1.a) — `[INFERENCE]` only until the extractor is actually written against it. The template variance is a known small delta (endnote layout + "made under" formatting); the +2-hour estimate assumes a shared parser with a per-tag branch, which is the cheap architecture. If the Ni template turns out to differ more structurally, the hours estimate for F2018N00155 (and by extension F2018N00041 for the parts that don't sidestep template variance) may grow — bounded by ~+8 hours at the worst realistic case.
- **Whether legislation.gov.au's terms of use have changed between the OPC/PMC CC-BY-4.0 baseline verification and the founder's fetch date** (C1) — worth a founder confirmation. Fetch the current terms-of-use page from an AU network, paste the current wording; if unchanged from the CC-BY-4.0 baseline, this is closed. If changed, revisit the licence rows in C1.b and the `LICENCE_BY_HOST` seed in T2.b.
- **Whether F2018L00887 (Worker Screening Rules) has a compilation newer than No. 4 (31 July 2021)** — `[UNVERIFIED-PRIMARY]`. Extract-on-hand is `docs/corpus-primary-sources/text/F2021C00788.txt` (comp No. 4, incl. amendments up to F2021L01050). Federal Register searches in this session surfaced 2024 amendment activity (F2024L00867 "NDIS Worker Screening Law Amendment (Interpretation) Rules 2024"), which may or may not have been rolled into a subsequent compilation. Founder to check the Federal Register from an AU network for the latest compilation ID for F2018L00887 (candidates F2022C… / F2023C… / F2024C… / F2025C… / F2026C…) before the extractor is written against this instrument. See Z1 decision 8 for the launch-gate mitigation.
- **Per-instrument page counts, section counts, defined-term counts, cross-reference counts** in T2.a are all `[INFERENCE]` or `[UNVERIFIED-PRIMARY]` — the numbers repeat and refine [M1-5] figures without opening the source.
- **Insurance premium ranges** in C5 are `[INFERENCE]` from BizCover published anchors + broker-quote norms. No live quote was obtained; every dollar figure requires a founder to seek an actual quote.
- **Solicitor cost ranges** in C9 are `[INFERENCE]` from Sprintlaw / LegalVision published packages. No live quote.
- **Total pytest / jest counts** — the prompt cites "~3,665 pytest, ~1,002 jest as of last run"; CLAUDE.md cites 1,794 pytest / 615 jest as its steady-state numbers. This document did not run either suite; the number difference is unresolved and noted as a candidate for a founder to reconcile with `pytest --collect-only -q | tail -3` and `cd frontend-nextjs && npx jest --listTests | wc -l`.
- **Line-of-code counts for services/** — verified by `wc -l` in this session (36,193 total LOC). Individual file LOC quoted from the same `wc -l`. Rebuild-hour estimates per file are `[INFERENCE]` at ~30 lines/hour equivalent.
- **Privacy Act small-business exemption removal** (C7.a) is verified 2026-08-06 via IAPP and Schiller Legal search results; the primary source (the Privacy and Other Legislation Amendment Act 2024) was not opened this session, so the phased-rollout dates and the specific commencement schedule are `[UNVERIFIED-PRIMARY]`.
- **Commercial-licence-request outcomes** (C8) are DRAFTS. Both draft emails require the founder to send and receive a response; nothing here binds NDIA or the Commission.
- **NDIS Commission vendor-approval scheme absence** (C6.d, C10) is verified via WebSearch absence — no scheme surfaced; this is an absence-of-evidence claim, not evidence-of-absence. Founder should sanity-check with a direct email to the Commission before locking marketing copy that says "no approval required."
- **AU carrier decline patterns** for compliance/legal-tech (C5) — searched, none surfaced; `[UNVERIFIED]` for exhaustiveness.
- **BNG SPP / ACIA competitive stance** — cited from [M6-11] §Module 8 unchanged; no re-verification this session.
- **The extractor's `[INFERENCE]` at ~30 lines/hour** productivity assumption — realistic for a solo senior engineer with domain familiarity and a strong test culture. `[INFERENCE]`; founder velocity may differ.

**Legal questions that need a solicitor's confirmation before build is production-ready:**
- Enforceability of the forbidden-use schedule (T5.i) as a material-breach trigger in an AU-law OEM licence.
- Enforceability of the back-to-back indemnity chain (C4.a) when the ultimate end-user is a natural person (not a business).
- Whether the sophisticated-user acknowledgement modal (C4.c) is a valid defence against a claim from a natural-person provider (owner-operator) who blames the tool for a compliance failure — the ACL s18 non-excludability point (WebSearch 2026-08-06) suggests the modal shifts the equity balance but does not immunise.
- Whether the pointer-only architecture for the Pricing Schedule (C2 option 1) is safe under CC-BY-NC-ND if the licence turns out to include ND — the IceTV precedent supports facts-are-not-copyrightable, but a solicitor's specific opinion on the NDIA notice would be prudent before ingesting.

**Commercial-licence outcomes that depend on requests the founder has not yet sent:**
- NDIA response to C8.a (Pricing Schedule).
- NDIS Commission response to C8.b (Regulated Restrictive Practices Guide).

**End of scoping document.**
