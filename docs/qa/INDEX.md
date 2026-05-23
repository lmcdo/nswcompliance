# QA & Legal Defensibility — Artefact Index

**Purpose:** Single manifest of all QA, audit trail, and legal defensibility artefacts across the PlotDetect satellite product suite. Hand this file to an auditor, lawyer, or due diligence reviewer — every item they need is linked from here.

**Last updated:** 2026-05-23

---

## 0. Architecture & Test Infrastructure

| Artefact | Path | What It Proves |
|---|---|---|
| Architecture Overview | [`docs/qa/architecture-overview.md`](architecture-overview.md) | System topology, data flow, security posture, deployment model. Shows how components interact and where data originates. |
| Test Matrix | [`docs/qa/test-matrix.md`](test-matrix.md) | 415 unit tests across 14 test files covering all 7 pipelines + enrichment + QA infrastructure. Execution <2s, enforced on every push. |
| Full Codebase Scan | [`docs/qa/codebase-scan-2026-05-23.md`](codebase-scan-2026-05-23.md) | 1,177 files scanned with 4 automated scanners. Every finding triaged as true positive, accepted risk, or false positive. |

---

## 1. Policy & Methodology

| Artefact | Path | What It Proves |
|---|---|---|
| QA & Data Provenance Standard | [`docs/QA-DATA-PROVENANCE.md`](../QA-DATA-PROVENANCE.md) | Systematic QA methodology exists. Legal framework (ACL s18, Shaddock, ACL s54). Per-pipeline 5-pass validation standard. Ongoing monitoring obligations. |
| Language Audit Methodology | [`docs/QA-DATA-PROVENANCE.md` §5](../QA-DATA-PROVENANCE.md) | Substitution rules for liability-creating language. Grep patterns. Pre-PR enforcement process. |
| Climate Risk Methodology | [`docs/CLIMATE_RISK_METHODOLOGY.md`](../CLIMATE_RISK_METHODOLOGY.md) | Methodology disclosure for climate risk scoring pipeline. |

---

## 2. Per-Pipeline QA Validation Reports

Each report documents 5 passes: source authority, algorithm correctness, null/edge cases, connection safety, output defensibility. Bugs found are listed with severity and fix status.

| Pipeline | Report | Bugs Found | Status |
|---|---|---|---|
| Bushfire Pre-Screen | [`docs/qa/bushfire_validation.md`](bushfire_validation.md) | 3 found, 3 fixed | Complete |
| Threat Radar | [`docs/qa/threat_radar_validation.md`](threat_radar_validation.md) | 6 found, 6 fixed | Complete |
| Flood Truth | [`docs/qa/flood_truth_validation.md`](flood_truth_validation.md) | 2 found, 2 fixed | Complete |
| Solar Yield | [`docs/qa/solar_yield_validation.md`](solar_yield_validation.md) | 4 found, 4 fixed | Complete |
| Shadow Detector | [`docs/qa/shadow_validation.md`](shadow_validation.md) | 9 found, 9 fixed | Complete |
| Granny Flat | [`docs/qa/granny_flat_validation.md`](granny_flat_validation.md) | 8 found, 8 fixed | Complete |
| Pre-DA History | [`docs/qa/pre_da_history_validation.md`](pre_da_history_validation.md) | 8 found, 8 fixed | Complete |
| **Total** | **7/7 pipelines** | **40 bugs found, 40 fixed** | **All complete** |

---

## 3. Language Audit

| Artefact | Path | What It Proves |
|---|---|---|
| Language Audit Change Register | `docs/qa/language-audit-2026-05-18.md` (on branch `chore/language-audit-liability-cleanup`) | 33 individual text changes across 16 frontend files. Every change documented with before/after and reason. |
| Liability Language Grep Pattern | [`docs/QA-DATA-PROVENANCE.md` §5.2](../QA-DATA-PROVENANCE.md) | Automated detection of risky language patterns. Enforced in pre-PR review checklist. |

---

## 4. Audit Trail Infrastructure

| Artefact | Path | What It Proves |
|---|---|---|
| Audit Trail Module | [`services/audit_trail.py`](../../services/audit_trail.py) | `DataSourceQuery` class (SHA-256 response hashing, timing, error tracking). `log_audit_trail()` — non-blocking, append-only. `get_current_disclaimer_version()`. Pipeline version from `RAILWAY_GIT_COMMIT_SHA`. |
| Audit Trail Migration | [`migrations/042_report_audit_trail.sql`](../../migrations/042_report_audit_trail.sql) | `report_audit_trail` table schema — append-only, no UPDATE/DELETE. Links report → pipeline version → data sources → disclaimer version. |
| Disclaimer Versioning Migration | [`migrations/042b_seed_disclaimer_versions.sql`](../../migrations/042b_seed_disclaimer_versions.sql) | `disclaimer_versions` table — versioned, never deleted. v1 disclaimers seeded for all 7 products. Lifecycle: new version inserted, old version's `superseded_at` set. |
| Health Checks Migration | [`migrations/043_data_source_health_checks.sql`](../../migrations/043_data_source_health_checks.sql) | `data_source_health_checks` table — append-only. Records every external endpoint probe with status, response time, response hash, schema validation result. |

---

## 5. Data Source Monitoring

| Artefact | Path | What It Proves |
|---|---|---|
| Satellite Freshness Monitor | [`scripts/satellite_freshness_monitor.py`](../../scripts/satellite_freshness_monitor.py) | Automated daily probing of all 15 external endpoints across 7 pipelines. 8 probe types (ArcGIS, ePlanning, Google Solar, BOM, WCS, etc.). Schema validation. Telegram alerts on failure. Results written to `data_source_health_checks`. |
| Audit Trail Completeness Check | [`scripts/satellite_freshness_monitor.py`](../../scripts/satellite_freshness_monitor.py) | Runs as part of daily freshness check. Finds reports in `property_reports` with no corresponding `report_audit_trail` row (last 7 days). Alerts if audit write silently failed. |
| Output Quality Check | [`scripts/satellite_freshness_monitor.py`](../../scripts/satellite_freshness_monitor.py) | Runs as part of daily freshness check. Finds reports with NULL/empty outputs, NULL confidence, or empty data_sources arrays. Catches "ran successfully but produced garbage". |
| GitHub Actions Workflow | [`.github/workflows/satellite-freshness-monitor.yml`](../../.github/workflows/satellite-freshness-monitor.yml) | Cron schedule (daily 06:00 UTC / 16:00 AEST). Manual dispatch with optional source filter. Failure notification via Telegram. Dead man's switch via healthchecks.io. Proves ongoing automated monitoring, not one-off. |

---

## 6. Disclaimer Architecture

| Artefact | Path | What It Proves |
|---|---|---|
| Per-product disclaimers | `disclaimer_versions` table (Supabase) | Versioned, immutable disclaimer records. Each report's audit trail row records which disclaimer version was active at generation time. |
| Frontend disclaimer constants | [`frontend-nextjs/lib/disclaimers.ts`](../../frontend-nextjs/lib/disclaimers.ts) | `DATA_PROVENANCE` and `PDF_DISCLAIMERS` objects. Every product has attribution text and PDF disclaimer text. |
| Disclaimer lifecycle | [`docs/QA-DATA-PROVENANCE.md` §7](../QA-DATA-PROVENANCE.md) | Insert new → supersede old → never delete. Proves what the user was shown at report generation time. |

---

## 7. Pipeline Service Files

These are the actual pipeline implementations that the QA reports audit.

| Pipeline | Service | Frontend Component | PDF Report |
|---|---|---|---|
| Bushfire Pre-Screen | [`services/bushfire_prescreen.py`](../../services/bushfire_prescreen.py) | [`frontend-nextjs/components/tools/BushfireResultCard.tsx`](../../frontend-nextjs/components/tools/BushfireResultCard.tsx) | [`frontend-nextjs/lib/pdf/bushfire-report.tsx`](../../frontend-nextjs/lib/pdf/bushfire-report.tsx) |
| Threat Radar | [`services/threat_radar.py`](../../services/threat_radar.py) | [`frontend-nextjs/components/tools/ThreatRadarTool.tsx`](../../frontend-nextjs/components/tools/ThreatRadarTool.tsx) | [`frontend-nextjs/lib/pdf/threat-radar-report.tsx`](../../frontend-nextjs/lib/pdf/threat-radar-report.tsx) |
| Flood Truth | [`services/flood_truth.py`](../../services/flood_truth.py) | [`frontend-nextjs/components/tools/FloodTruthTool.tsx`](../../frontend-nextjs/components/tools/FloodTruthTool.tsx) | [`frontend-nextjs/lib/pdf/flood-report.tsx`](../../frontend-nextjs/lib/pdf/flood-report.tsx) |
| Solar Yield | [`services/solar_yield.py`](../../services/solar_yield.py) | [`frontend-nextjs/components/tools/SolarYieldTool.tsx`](../../frontend-nextjs/components/tools/SolarYieldTool.tsx) | [`frontend-nextjs/lib/pdf/solar-report.tsx`](../../frontend-nextjs/lib/pdf/solar-report.tsx) |
| Shadow Detector | [`services/shadow_detector.py`](../../services/shadow_detector.py) | [`frontend-nextjs/components/tools/ShadowDetectorTool.tsx`](../../frontend-nextjs/components/tools/ShadowDetectorTool.tsx) | [`frontend-nextjs/lib/pdf/shadow-report.tsx`](../../frontend-nextjs/lib/pdf/shadow-report.tsx) |
| Granny Flat | [`services/granny_flat.py`](../../services/granny_flat.py) | [`frontend-nextjs/components/tools/GrannyFlatTool.tsx`](../../frontend-nextjs/components/tools/GrannyFlatTool.tsx) | [`frontend-nextjs/lib/pdf/granny-flat-report.tsx`](../../frontend-nextjs/lib/pdf/granny-flat-report.tsx) |
| Pre-DA History | [`services/pre_da_history.py`](../../services/pre_da_history.py) | [`frontend-nextjs/components/tools/PreDAHistoryTool.tsx`](../../frontend-nextjs/components/tools/PreDAHistoryTool.tsx) | [`frontend-nextjs/lib/pdf/pre-da-report.tsx`](../../frontend-nextjs/lib/pdf/pre-da-report.tsx) |

---

## 8. Legal Requirements Traceability

| Legal Requirement | How We Address It | Evidence |
|---|---|---|
| **ACL s18** — misleading or deceptive conduct | Language audit: no compliance determinations, no risk assessments, no recommendations. All text describes factual data observations. | §3 (language audit), §2 (per-pipeline Pass 5) |
| **Shaddock negligence** — duty of care when info relied upon | Audit trail: every report records exact data queried, when, from which source, response hash. | §4 (audit trail infrastructure) |
| **ACL s54** — fitness for purpose | Product positioned as "preliminary data screening" not "compliance assessment". Disclaimers bound scope. | §6 (disclaimer architecture) |
| **ASIC RG 244** — information vs advice | No recommendation language. Reports present data; users make decisions. | §3 (language audit substitution rules) |
| **Design & Building Practitioners Act 2020** — 10-year limitation | Audit trail retention policy: append-only, no DELETE. | §4 (migration 042) |

---

## 9. Data Provenance

| Artefact | Path | What It Proves |
|---|---|---|
| DCP Controls Provenance | [`docs/qa/dcp-data-provenance.md`](dcp-data-provenance.md) | 999 structured numeric controls across 29 LGAs traced to council DCP source documents. Extraction methodology, dedup checks, three-state review model, 17 automated data integrity tests. |
| Regulatory Provisions | `regulatory_provisions` table | 46,585 provisions with `source_ref`, `effective_date`, `document_id` linking to specific planning instruments. Enriched with `v2_is_actionable`, `v2_applicable_dev_types`, `v2_topic`. |
| Spatial Overlays | `spatial_overlays` table | 128 LGAs with 14 overlay types. Each overlay references the statutory instrument (e.g., EPI flood mapping under EP&A Act s9.1). |

---

## 10. Automated Code Quality Gates

Every code change passes through 7 automated scanner layers before it can reach production. These gates are enforced by git hooks — they cannot be bypassed without explicit `--no-verify` (which is prohibited by team policy and flagged in code review).

| Layer | Scanner | What It Catches | Hook | Added |
|---|---|---|---|---|
| 1 | QA tier classifier | Missing `QA: [Tier]` line in commit message | `commit-msg` | PR #344 |
| 2 | TSC error count | TypeScript errors above baseline (664) | `pre-commit` | PR #347 |
| 3 | Python test suite | 415 unit tests across 7 pipelines + enrichment | `pre-push` | PR #362 |
| 4 | DB guard scanner | SQL queries missing `is_current = TRUE` on scoped tables | `pre-push` (qa_gate.py) | PR #362 |
| 5 | Null guard scanner | `.rows[0]` access without prior length check | `pre-push` (qa_gate.py) | PR #365 |
| 6 | Type boundary scanner | Falsy JSX guards and `=== null` without undefined coverage | `pre-push` (qa_gate.py) | PR #366 |
| 7 | Silent failure scanner | Empty/log-only catch blocks and success-on-error in API routes | `pre-push` (qa_gate.py) | PR #366 |

Additionally, the QA gate (`scripts/qa_gate.py`) validates per-PR quality reports:
- **AST grounding:** file:line references in report verified against actual source code
- **Tier floor:** >3 files changed = cannot use Minor tier
- **Commit hash binding:** report cryptographically pinned to specific commit
- **Break-it specificity:** each failure scenario requires a concrete reproduction step
- **Liability language:** new user-facing text scanned for terms that create legal liability

**Artefacts:**
| Artefact | Path |
|---|---|
| QA gate script (all scanners) | [`scripts/qa_gate.py`](../../scripts/qa_gate.py) |
| Liability language scanner | [`scripts/liability_language_check.py`](../../scripts/liability_language_check.py) |
| QA report template | [`scripts/qa_report_template.json`](../../scripts/qa_report_template.json) |
| Commit-msg hook | [`.githooks/commit-msg`](../../.githooks/commit-msg) |
| Pre-commit hook | [`.githooks/pre-commit`](../../.githooks/pre-commit) |
| Pre-push hook | [`.githooks/pre-push`](../../.githooks/pre-push) |
| Scanner unit tests | [`tests/test_qa_scanners.py`](../../tests/test_qa_scanners.py) |

**Compliance evidence:**
- 100% of commits since hook activation include QA classification (15/15)
- QA tier distribution: 8 Standard, 5 Minor, 2 Critical
- Full codebase scan: [`docs/qa/codebase-scan-2026-05-23.md`](codebase-scan-2026-05-23.md)

---

## 11. Test Infrastructure

| Metric | Value |
|---|---|
| Total unit tests | 415 |
| Test execution time | <2 seconds |
| Pipelines with dedicated test suites | 7/7 |
| Mock injection | `conftest_mocks.py` stubs external deps (psycopg2, requests, pyproj) |
| Test framework | pytest with pydantic validation |
| Pre-push enforcement | Tests must pass before code can be pushed |

### Test coverage by pipeline

| Pipeline | Test file | Tests | Coverage focus |
|---|---|---|---|
| Bushfire Pre-Screen | `tests/test_bushfire_prescreen.py` | 51 | BAL classification, multi-feature, null handling |
| Flood Truth | `tests/test_flood_truth.py` | 70 | Multi-source validation, WOfS bands, EPI tiers |
| Granny Flat | `tests/test_granny_flat_logic.py` + `_geometry.py` | 35 | CDC eligibility, lot geometry, edge cases |
| Shadow Detector | `tests/test_shadow_detector.py` | 18 | Seasonal shadow, height limits, boundary conditions |
| Solar Yield | `tests/test_solar_yield.py` | 31 | Panel yield, shading loss, battery sizing |
| Threat Radar | `tests/test_threat_radar.py` | 25 | DA monitoring, distance calculation, status parsing |
| Climate Risk Score | `tests/test_climate_risk_score.py` | 51 | Multi-hazard scoring, raster query, edge cases |
| Enrichment | `tests/enrichment/` | 88 | Provision tagging, layer classification, applicability |
| QA Scanners | `tests/test_qa_scanners.py` | 14 | Scanner false positive/negative validation |
| Insert Scripts | `tests/test_insert_scripts.py` | 17 | DCP control data integrity, dedup, constraint compliance |

---

## 12. Known Gaps

| # | Gap | Severity | Path to Resolution | Status |
|---|---|---|---|---|
| 3 | Audit trail migration run in prod but disclaimer seed data status unverified | Medium | Verify `disclaimer_versions` has 7 rows in Supabase | Open |
| 4 | ~~Language audit branch not yet merged~~ | ~~High~~ | ~~Merge after QA validation~~ | **RESOLVED** — merged |
| 5 | No external legal review of disclaimers | High | Engage Australian technology lawyer (§8.3 of QA-DATA-PROVENANCE.md) | Open |
| 6 | No Professional Indemnity insurance | Critical | Commercial action, pre-revenue | Open |
| 7 | 31 unguarded `.rows[0]` accesses in API routes | Medium | Fix with optional chaining or length check | Open — see codebase scan |
| 8 | 45 log-only catch blocks in API routes | Low | Add error responses or document as accepted risk | Open — see codebase scan |
