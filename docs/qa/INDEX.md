# QA & Legal Defensibility — Artefact Index

**Purpose:** Single manifest of all QA, audit trail, and legal defensibility artefacts across the PlotDetect satellite product suite. Hand this file to an auditor, lawyer, or due diligence reviewer — every item they need is linked from here.

**Last updated:** 2026-05-21

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
| Bushfire Pre-Screen | [`docs/qa/bushfire_validation.md`](bushfire_validation.md) | 3 found, 3 fixed (multi-feature selection, false DEM attribution, risk labels) | Complete |
| Threat Radar | [`docs/qa/threat_radar_validation.md`](threat_radar_validation.md) | 6 found, 6 fixed (false LEP attribution, label mismatch, 4 language issues) | Complete |
| Flood Truth | — | 70 tests written | Complete (no separate report yet) |
| Solar Yield | — | 31 tests written | Complete (no separate report yet) |
| Shadow Detector | [`docs/qa/shadow_validation.md`](shadow_validation.md) | 9 found, 9 fixed (wrong comment, connection leak, 2 false attributions, wrong lib name, 4 language) | Complete |
| Granny Flat | [`docs/qa/granny_flat_validation.md`](granny_flat_validation.md) | 8 found, 8 fixed (cursor leak, 7 language) | Complete |
| Pre-DA History | — | — | Not started |

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
| GitHub Actions Workflow | [`.github/workflows/satellite-freshness-monitor.yml`](../../.github/workflows/satellite-freshness-monitor.yml) | Cron schedule (daily 06:00 UTC / 16:00 AEST). Manual dispatch with optional source filter. Proves ongoing automated monitoring, not one-off. |

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

## 9. Known Gaps

| # | Gap | Severity | Path to Resolution |
|---|---|---|---|
| 1 | Pre-DA History QA report not yet written | Medium | Continue 5-pass validation |
| 2 | Flood Truth + Solar Yield have tests but no formal QA validation report | Low | Write reports documenting existing test coverage |
| 3 | Audit trail migration run in prod but disclaimer seed data status unverified | Medium | Verify `disclaimer_versions` has 7 rows in Supabase |
| 4 | Language audit branch (`chore/language-audit-liability-cleanup`) not yet merged | High | Merge after QA validation complete |
| 5 | No external legal review of disclaimers | High | Engage Australian technology lawyer (§8.3 of QA-DATA-PROVENANCE.md) |
| 6 | No Professional Indemnity insurance | Critical | Commercial action, pre-revenue |
