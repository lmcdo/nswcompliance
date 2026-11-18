# Repo audit for open-sourcing (lmcdo/nswcompliance), measured 2026-11-18

All figures measured in the cloud checkout (a shallow clone, so full git history was NOT scanned).

| Fact | Value | Command |
|---|---|---|
| Tracked files | 6,868 | `git ls-files \| wc -l` |
| Checkout size (excl. node_modules) | 1.2 GB | `du -sh --exclude=node_modules .` |
| LICENSE | MIT, "Copyright (c) 2025 Cole Medin" — appears inherited from a template (Cole Medin publishes context-engineering templates); the owner's own copyright is not stated | `head -5 LICENSE` |
| Tracked DB backups | 25 files, 91 MB in `backups/` (pg/SQLite dumps of regulatory tables: regulatory_provisions, development_controls, zone_setback_rules, kg_entities, etc.) | `git ls-files backups` |
| Email addresses in dumps | 1 unique address in `backups/nsw_planning_dump_20251001_065048.sql`; 0 in the others | grep for email pattern |
| DB connection strings in current tree | Present in docs (DEPLOYMENT.md, .claude/docs/history, supabase/.temp/pooler-url) but passwords are placeholders; the real Supabase project ref appears in 3 places | masked grep |
| API keys (Anthropic `sk-ant-`, AWS `AKIA`) in current tree | none found | `git grep -lIE 'sk-ant-...|AKIA...'` |
| Full-history secret scan | NOT done (shallow clone); needs gitleaks/trufflehog on a full clone before any publication | — |

## Business-sensitive content that would become public
- Strategy and sales docs: `plans/strategic/`, `plans/expansion/council-sales-playbook.md`, `.claude/strategy`, `.claude/gtm-strategy-2026`.
- Project rule `.claude/rules/blog-content.md` treats internal pipeline names ("Flood Truth Engine", "Threat Radar", "Shadow Ambush Detector", etc.) and algorithm names as IP not to be published.
- Internal QA/DQ trackers (`.claude/DATA_QUALITY_TRACKER.md`) — honest defect records; could be a positive signal of rigour or a liability depending on framing.

## Separable components (candidates for standalone open-source repos)
From `services/` (83 modules) and repo layout:
- NSW Planning Portal / ArcGIS clients: `services/arcgis_client.py`, `services/portal_constraints.py`, `services/nsw_planning_api.py`
- DA outcome analytics: `services/da_outcome.py` (NSW DA Tracking MapServer: outcome, lodgement/determination dates, dev type, cost, LGA; no applicant field)
- Geometry/QA utilities: `services/geometry_checks.py`, `services/geom_pieces.py`, `services/lot_dimensions.py`, `services/street_frontage.py`
- Solar/shadow: `services/solar_position.py`, `services/shadow_model.py`
- Extraction integrity checks: `services/extracted_data_integrity.py` (fabricated_values, conflicting_values, value_absent_from_source)
- CDC / housing SEPP screening: `services/cdc_screen.py`, `services/housing_sepp_eligibility.py`, `services/lmr_area_decision.py`
- Engineering-discipline tooling: `.githooks/` (QA tier gate, liability-language scan, provenance rules), `scripts/qa_gate.py`, quarantine ratchet — a distinctive "AI-assisted development with guardrails" showcase.
- Dataset: ~55,696 regulatory_provisions rows (CLAUDE.md figure, measured 2026-08-08; live DB unreachable from this session) — publishability depends on source licences (LEP/SEPP vs council DCP copyright).

## Known code defects relevant to a public release
- `services/autoschema_kg_query.py` reads CSVs not in the repo and silently returns empty; callers in `services/property_intelligence_4stack.py:144` and `services/clause_citation_inline.py:41`.
- `services/clause_citation_inline.py` contains a hardcoded `fake_to_real_mapping` of clause references.
