# QA & Data Provenance — Satellite Product Pipelines

**Version:** 1.0
**Date:** 2026-05-18
**Author:** Lawrence McDonell
**Status:** Active

---

## 1. Overview

PlotDetect operates 7 satellite property intelligence pipelines that aggregate government-authoritative data into property-specific reports. Because these reports are used in property purchase, development, and insurance decisions, they carry legal liability under Australian Consumer Law (ACL) and common law negligence.

This document describes the QA methodology, data provenance architecture, and audit trail infrastructure that ensures every report is traceable, defensible, and accurate. It serves three audiences:

1. **Legal/compliance** — demonstrates reasonable care and skill under Shaddock duty of care
2. **Investors/due diligence** — demonstrates systematic quality assurance across the product suite
3. **Internal engineering** — defines the standard every pipeline must meet before deployment

---

## 2. Legal Framework

### 2.1 Applicable Law

| Statute / Authority | Risk | Our Mitigation |
|---|---|---|
| **ACL s18** — misleading or deceptive conduct | Strict liability. If a reasonable consumer would be misled, intent is irrelevant. Cannot be contracted out. | Language audit (see §5): all user-facing text describes factual data observations, never compliance determinations or recommendations. |
| **Shaddock negligence** (1981 HCA 59) | Duty of care when providing information you know will be relied upon. Standard: reasonable care and skill. | Audit trail (see §4): every report records exactly what data was queried, when, from which source, and what the response was. |
| **ACL s54** — fitness for purpose | Software must be fit for the purpose the consumer makes known. | Product positioning as "preliminary data screening" not "compliance assessment". Scope is bounded in disclaimers. |
| **ASIC RG 244** — information vs advice | Recommendations require AFSL. Factual information does not. | No recommendation language in any report. Reports present data; users make decisions. |

### 2.2 Key Case Law

- **Butcher v Lachlan Elder Realty** [2004] HCA 60 — test is whether conduct would mislead a reasonable member of the class (property buyers and advisors).
- **Shaddock v Parramatta CC** [1981] HCA 59 — information provider who knows information will be relied upon owes duty of care.

---

## 3. Pipeline Architecture & Data Sources

### 3.1 Pipeline Inventory

| # | Pipeline | Service File | Data Sources | Output |
|---|---|---|---|---|
| 1 | Bushfire Prescreen | `services/bushfire_prescreen.py` | RFS Bushfire Prone Land, NSW Heritage, NSW Planning Portal (zone, flood) | Risk assessment with source attribution |
| 2 | Solar Yield | `services/solar_yield.py` | Google Solar API, NSW Heritage, council HOB limits | Yield estimate, panel layout, ROI projection |
| 3 | Flood Truth | `services/flood_truth.py` | EPI Flood Planning (NSW PP), Copernicus EMS, JRC Global Flood, DEA WOfS, BOM, SES flood studies, DEM | Multi-source flood signal with confidence scoring |
| 4 | Shadow Detector | `services/shadow_detector.py` | NSW Lot API, Sentinel-2 imagery, pybdshadow model, council height limits | Shadow analysis against ADG solar access test |
| 5 | Granny Flat | `services/granny_flat.py` | SAM segmentation, SIX Maps imagery, SEPP Housing rules, zone/heritage lookups | Structure detection, SEPP eligibility, yield estimate |
| 6 | Threat Radar | `services/threat_radar.py` | OnlineDA, OnlineCDC (NSW Planning Portal) | Nearby development applications within radius |
| 7 | Pre-DA History | `services/pre_da_history.py` | Geocoding, Tessera mapping, Sentinel-2, ePlanning, Heritage, Wayback Machine | Site history timeline with change detection |

### 3.2 Data Source Authority

Every data source used falls into one of two categories:

**Government-authoritative (primary):**
- NSW Planning Portal (layerintersect, zone, EPI overlays)
- NSW Rural Fire Service (Bushfire Prone Land Map)
- NSW Heritage (State Heritage Register, s170 registers)
- Bureau of Meteorology (rainfall, flood data)
- Copernicus Emergency Management Service (EU)
- Digital Earth Australia (Water Observations from Space)
- JRC Global Surface Water (EU Joint Research Centre)

**Commercial/derived (secondary, always attributed):**
- Google Solar API (solar potential modelling)
- Sentinel-2 satellite imagery (ESA, open access)
- SAM (Meta's Segment Anything Model — structure detection)

No pipeline uses scraped, user-contributed, or unverifiable data sources.

---

## 4. Audit Trail Infrastructure

### 4.1 Design Principles

1. **Append-only** — no UPDATE or DELETE on audit tables. Immutability is the legal requirement.
2. **Non-blocking** — audit logging failure does not prevent report delivery. A user never loses their report because logging failed.
3. **Complete provenance** — every external API call is individually tracked with timing, response hash, and feature count.
4. **10-year retention** — aligns with Design and Building Practitioners Act 2020 limitation period.

### 4.2 Database Schema

#### `report_audit_trail` (append-only)

| Column | Type | Description |
|---|---|---|
| `id` | UUID PK | Unique audit record |
| `report_id` | UUID | Links to `property_reports.id` or `pre_da_history_reports.id` |
| `pipeline_name` | TEXT | Which pipeline generated this report |
| `pipeline_version` | TEXT | Git commit SHA at deploy time (via `RAILWAY_GIT_COMMIT_SHA`) |
| `input_params` | JSONB | Address, lat, lng, lot geometry — exactly what was submitted |
| `data_sources_queried` | JSONB | Array of source records (see §4.3) |
| `intermediate_calculations` | JSONB | Key algorithmic steps for traceability |
| `output_summary` | JSONB | The outputs JSON written to the report table |
| `disclaimer_version` | TEXT | Which disclaimer version was active when report was generated |
| `created_at` | TIMESTAMPTZ | Immutable timestamp |

#### `disclaimer_versions` (versioned, never deleted)

| Column | Type | Description |
|---|---|---|
| `pipeline_name` | TEXT | Matches audit trail |
| `version` | TEXT | e.g. `bushfire-v1`, `flood-v2` |
| `headline_disclaimer` | TEXT | Short disclaimer shown on report |
| `limitations_text` | TEXT | Product-specific limitations |
| `source_attributions` | TEXT | Data source names and their disclaimers |
| `effective_from` | TIMESTAMPTZ | When this version became active |
| `superseded_at` | TIMESTAMPTZ | NULL = currently active |

### 4.3 Per-Source Tracking (DataSourceQuery)

Every external API call within a pipeline is wrapped in a `DataSourceQuery` object that records:

```
{
  "source_name": "rfs_bushfire_prone_land",
  "url": "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/...",
  "query_timestamp_utc": "2026-05-18T10:23:45.123Z",
  "response_time_ms": 342,
  "response_hash_sha256": "a1b2c3d4...",
  "features_returned": 3,
  "cache_hit": false,
  "error": null
}
```

The SHA-256 hash of each API response body provides tamper-evident data provenance. If a source is later questioned, we can prove exactly what data was returned at query time.

### 4.4 Pipeline Version Tracking

Each deployed service includes its git commit SHA via Railway's `RAILWAY_GIT_COMMIT_SHA` environment variable. This is recorded in every audit trail row, creating a permanent link between report output and the exact code version that generated it.

For local/dev environments, the version falls back to `"dev"`.

---

## 5. Language Audit

### 5.1 Purpose

A systematic review of all user-facing text to ensure no statement crosses the boundary from factual information into advice, recommendation, or assurance that exceeds what the data supports.

### 5.2 Methodology

1. **Automated grep** across all frontend files for liability-creating language patterns:
   ```
   safe|feasible|compliant|should|recommend|suitable|adequate|sufficient|
   approved|guaranteed|certified|confirmed|verified|ensure|assure|accurate|
   definitive|comprehensive|complete|reliable|risk-free|no risk|low risk|
   high risk|determine|proof|proves|protect
   ```
2. **Manual classification** of each match as: CHANGE (liability risk), KEEP (factual use), or CONTEXT (acceptable in context).
3. **Targeted replacement** following the substitution rules below.

### 5.3 Substitution Rules

| Risky Pattern | Replacement | Reason |
|---|---|---|
| "ADG compliant" | "Meets ADG solar access test" | Compliance is a formal determination we can't make |
| "recommended" / "we recommend" | "based on available data" / removed | Crosses into advice (ASIC RG 244) |
| "safe" / "no risk" | "No indicators found in the data sources checked" | Absence of evidence ≠ evidence of absence |
| "confirmed" / "verified" | "indicates" / "based on" | Implies certainty beyond what automated screening provides |
| "comprehensive" / "complete" | "based on [N] data sources" | No screening is truly comprehensive |
| "should [action]" | Removed or rephrased as factual | Recommendation language triggers advice classification |
| "low risk" / "high risk" | Bounded observation with source | Risk classification implies professional assessment |

### 5.4 Scope

- 16 frontend files across 7 products
- 33 individual text changes
- Full change register in `docs/qa/language-audit-2026-05-18.md` (on branch `chore/language-audit-liability-cleanup`)

### 5.5 Pre-PR Enforcement

The pre-PR review checklist (CLAUDE.md) includes a mandatory liability language check:

> **#5 — Liability language:** grep all changed frontend files for `recommend|should|safe|compliant|verified|confirmed|certified|comprehensive|complete|guaranteed|no risk|low risk|high risk`. Each match must be reviewed in context. Factual technical uses (e.g. TypeScript types, internal comments) are OK. User-facing text that implies assurance, advice, or compliance determination must be rewritten.

---

## 6. Per-Pipeline QA Validation

### 6.1 Methodology (5-Pass Validation per Pipeline)

Each pipeline undergoes 5 passes:

| Pass | Name | What It Validates |
|---|---|---|
| **Pass 1** | Data source verification | Every API call returns what we claim. Response schemas match expectations. Failure modes are handled. |
| **Pass 2** | Algorithm correctness | Classification logic, scoring, thresholds, and boundary conditions produce correct outputs for known inputs. |
| **Pass 3** | Null/edge case hardening | Every `.get()`, `float()`, `int()`, `or default` is checked for null-value traps where key can exist with null value. |
| **Pass 4** | Connection/resource safety | No DB connection leaks, no unguarded blocking I/O in async endpoints, proper error isolation. |
| **Pass 5** | Output defensibility | Every user-facing claim is traceable to a specific data source. No interpolation or inference beyond what the data shows. |

### 6.2 Pipeline QA Status

| Pipeline | Pass 1 | Pass 2 | Pass 3 | Pass 4 | Pass 5 | Test Count | Status |
|---|---|---|---|---|---|---|---|
| Flood Truth | Done | Done | Done | Done | Done | 70 tests | Complete |
| Solar Yield | Done | Done | Done | Done | Done | 31 tests | Complete |
| Shadow | Scanned | — | — | — | — | 0 | In progress |
| Threat Radar | Scanned | — | — | — | — | 0 | In progress |
| Granny Flat | Partial | Partial | — | — | — | 13 tests (geometry only) | In progress |
| Bushfire | Done | Done | Done | Done | Done | 3 bugs fixed | Complete |
| Pre-DA History | — | — | — | — | — | 0 | Not started |

### 6.3 Bug Classes Found and Fixed

Across completed pipelines, the following bug categories were identified:

1. **Null-value traps** — `.get("key", 0)` where key exists with `null` value (returns null, not 0). Fixed with `or 0` post-guard.
2. **Empty string classification gaps** — `class=""` not matching `(None, "none")` check, causing incorrect signal propagation.
3. **Connection leaks** — psycopg2 `with conn:` does NOT close connection. Fixed with `try/finally conn.close()`.
4. **Unguarded DB writes** — `_write_report()` failure causing 500 despite successful analysis. Fixed with try/except isolation.
5. **Type coercion failures** — ArcGIS integer dates not coerced to string before comparison.
6. **Cache path divergence** — normalisation logic not applied to cached results, causing inconsistent outputs.

Full bug register: `docs/satellite-services-qa-tasklist.md`

---

## 7. Disclaimer Architecture

### 7.1 Per-Product Disclaimers

Each pipeline has a versioned disclaimer stored in `disclaimer_versions` with:
- **Headline disclaimer** — shown prominently on every report
- **Limitations text** — product-specific limitations
- **Source attributions** — data source names with their own licence/disclaimer terms

### 7.2 Disclaimer Lifecycle

1. New disclaimer version is inserted with `effective_from = NOW()`, `superseded_at = NULL`
2. Previous version's `superseded_at` is set to `NOW()`
3. Every report audit trail row records which disclaimer version was active at generation time
4. Old versions are never deleted — they prove what the user was shown

### 7.3 Active Disclaimers (v1)

All 7 products have v1 disclaimers seeded. Each follows the pattern:
- "This report is an automated data screening, not professional advice"
- Product-specific limitations (e.g. flood: "Does not account for localised stormwater or overland flow")
- Source attributions with government agency names

---

## 8. Ongoing Obligations

### 8.1 Data Source Currency

**Automated monitoring:** `scripts/satellite_freshness_monitor.py` probes all 15 external endpoints daily via GitHub Actions (`satellite-freshness-monitor.yml`, 06:00 UTC). Results are logged to `data_source_health_checks` (append-only, migration 043). Failures trigger Telegram alerts.

| Check | Frequency | Method |
|---|---|---|
| All satellite pipeline data sources (15 endpoints) | Daily (automated) | `satellite_freshness_monitor.py` — HTTP probe, schema validation, response time check |
| EPI layer amendment detection | Weekly | DCP monitoring pipeline (`scripts/r2_monitor.py`) |
| NSW legislation version changes | Weekly | `scripts/legislation_monitor.py` (PCO + AustLII) |
| RFS Bushfire Prone Land Map version | Annually | Manual check against RFS publication |
| Google Solar API schema changes | Per-release | Response validation against Pydantic models |
| Disclaimer review | Quarterly | Manual review of all active disclaimer versions |

### 8.2 New Pipeline Checklist

Before any new satellite pipeline can be deployed to production:

- [ ] All 5 QA passes completed and documented
- [ ] Adversarial test suite written (minimum 20 tests)
- [ ] Audit trail wired in (DataSourceQuery per external call + log_audit_trail on output)
- [ ] v1 disclaimer seeded in `disclaimer_versions`
- [ ] Language audit completed on all user-facing text
- [ ] Added to this document's pipeline inventory table

### 8.3 Priority 0 Legal Actions (Pre-Revenue)

- [ ] Engage Australian technology lawyer for ToS + disclaimer review
- [ ] Obtain Professional Indemnity insurance
- [ ] Confirm ASIC classification (information provider, not financial advice)
- [ ] Verify audit trail retention meets Design and Building Practitioners Act requirements

---

## 9. Known Gaps

| # | Gap | Severity | Status |
|---|---|---|---|
| 1 | SEPP R&H 2021 — `sepp_structured_requirements` has 0 rows for `resilience_hazards_2021` | High | Not fixed. Schema + API ready, needs population script. |
| 2 | Shadow, Threat Radar, Granny Flat — QA passes 2-5 incomplete | Medium | In progress. See §6.2. |
| 3 | Bushfire, Pre-DA History — QA not started | Medium | Queued. |
| 4 | Audit trail migration not yet run in production | High | SQL ready (`migrations/042_report_audit_trail.sql`). Run in Supabase. |
| 5 | Language audit branch not yet merged | High | Branch `chore/language-audit-liability-cleanup` has all changes. |

---

## 10. File References

| Artefact | Location |
|---|---|
| This document | `docs/QA-DATA-PROVENANCE.md` |
| Language audit change register | `docs/qa/language-audit-2026-05-18.md` (on `chore/language-audit-liability-cleanup` branch) |
| Audit trail module | `services/audit_trail.py` (on `chore/language-audit-liability-cleanup` branch) |
| Audit trail migration | `migrations/042_report_audit_trail.sql` (on `chore/language-audit-liability-cleanup` branch) |
| Disclaimer seed data | `migrations/042b_seed_disclaimer_versions.sql` (on `chore/language-audit-liability-cleanup` branch) |
| Per-pipeline QA tasklist | `docs/satellite-services-qa-tasklist.md` |
| Climate risk methodology | `docs/CLIMATE_RISK_METHODOLOGY.md` |
| Satellite QA validation plan | `~/.claude/plans/ce-satellite-qa-validation-plan.md` |
| Legal defensibility research | `~/.claude/plans/ce-qa-legal-defensibility-research.md` |
| Data source freshness monitor | `scripts/satellite_freshness_monitor.py` |
| Health checks migration | `migrations/043_data_source_health_checks.sql` |
| Health checks workflow | `.github/workflows/satellite-freshness-monitor.yml` |
