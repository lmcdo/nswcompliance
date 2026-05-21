# PlotDetect — Quality Assurance & Legal Defensibility Summary

PlotDetect operates 7 automated property intelligence pipelines that aggregate government-authoritative data into property-specific reports. These reports are used in property purchase, development feasibility, and insurance decisions — which means they carry legal liability under Australian Consumer Law and the common law duty of care established in *Shaddock v Parramatta City Council* (1981).

This document summarises our QA and defensibility approach. The full technical detail is in [`docs/qa/INDEX.md`](INDEX.md).

---

## The legal exposure

Four obligations shape everything we build:

- **ACL s18 (misleading conduct):** Strict liability. If a reasonable property buyer would be misled by something we say, intent is irrelevant and the obligation cannot be contracted out.
- **Shaddock duty of care:** When you provide information you know will be relied upon for financial decisions, you owe a duty of reasonable care and skill. The test is: did we have a system, did we follow it, and did we fix problems when we found them?
- **ACL s54 (fitness for purpose):** The product must do what the consumer reasonably expects it to do, given how we describe it.
- **ASIC RG 244 (information vs advice):** If our reports cross the line from presenting data into making recommendations, we'd need an Australian Financial Services Licence. We don't have one and don't intend to get one — so our reports must stay on the information side of that line.

## How we address it

**1. Audit trail — proving what we did**

Every report we generate records: which data sources were queried, when, what they returned (SHA-256 hashed for tamper evidence), which version of our code produced the result, and which disclaimer the user was shown. These records are append-only — they cannot be edited or deleted. Retention is 10 years, aligned with the Design and Building Practitioners Act 2020 limitation period. This is the Shaddock answer: if a report is ever questioned, we can reconstruct exactly what happened.

**2. Language audit — controlling what we say**

We systematically reviewed every word of user-facing text across all 7 products for language that implies professional assessment, recommendation, or assurance. 33 individual text changes were made. Examples: "Low bushfire risk" became "Bushfire prone — lower category" (risk classification implies professional assessment); "property values" was removed from development impact descriptions (valuation advice requires licensing); "non-compliant development" became "variation from standard controls" (EPI variations are a lawful mechanism, not non-compliance). A grep-based enforcement check runs before every PR.

**3. Per-pipeline validation — proving the analysis is correct**

Each pipeline undergoes 5 audit passes:

| Pass | What it checks |
|---|---|
| Source authority | Every API we call is the legally authoritative source for that data (e.g., RFS Bush Fire Prone Land Map is the statutory instrument under Rural Fires Act 1997 s146(2)) |
| Algorithm correctness | Classification logic, scoring, thresholds, and boundary conditions produce correct outputs for known inputs |
| Null/edge case hardening | Every data access point is checked for null values, missing keys, type coercion failures, and unexpected API responses |
| Connection/resource safety | No database connection leaks, proper error isolation so one subsystem failure doesn't cascade |
| Output defensibility | Every user-facing claim is traced back to a specific data source; no interpolation beyond what the data shows |

4 of 7 pipelines are complete. 9 bugs were found and fixed across the first two detailed audits — including a bushfire pipeline bug where properties straddling two fire categories only reported the first category found (not the highest-risk), and a threat radar bug that listed a data source we don't actually query.

**4. Data source monitoring — knowing when things change**

An automated monitor probes all 15 external government and commercial endpoints daily at 06:00 UTC. It checks HTTP availability, response time, and schema validity. Results are logged to an append-only database table. Failures trigger alerts. This means we detect a broken or changed data source within 24 hours — not when a customer files a complaint.

**5. Disclaimer architecture — proving what we told the user**

Each product has a versioned disclaimer stored in the database. When a disclaimer is updated, the previous version is preserved with a timestamp. Every report's audit trail records which disclaimer version was active at generation time. Old versions are never deleted — they prove what the user was shown. All disclaimers follow the pattern: "This report is an automated data screening, not professional advice" with product-specific limitations and source attributions.

## Current status

| Area | Status |
|---|---|
| Audit trail infrastructure | Deployed to production |
| Language audit (33 changes) | Complete, pending merge |
| Bushfire QA (5-pass) | Complete — 3 bugs found and fixed |
| Threat Radar QA (5-pass) | Complete — 6 bugs found and fixed |
| Flood Truth QA | Complete — 70 tests |
| Solar Yield QA | Complete — 31 tests |
| Shadow / Granny Flat / Pre-DA History QA | In progress |
| Daily data source monitoring | Live, running in GitHub Actions |
| External legal review of disclaimers | Not yet started |
| Professional indemnity insurance | Not yet obtained |

The last two items are pre-revenue blockers — they require external engagement, not engineering work.
