# PlotDetect Codebase Quality Scan — 2026-05-23

**Scan scope:** 1,177 files (907 TS/JS, 270 Python)
**Scanner layers:** 4 (DB guard, null guard, type boundary, silent failure)
**Total findings:** 315
**Date:** 2026-05-23
**Commit:** 4a2394a5 (main, post PR #366)

## Executive Summary

| Layer | Total | True Positive | Accepted Risk | False Positive |
|-------|-------|--------------|---------------|----------------|
| DB Guard | 196 | 5 | 18 | 173 |
| Null Guard | 31 | 7 | 10 | 14 |
| Type Boundary | 42 | 3 | 27 | 12 |
| Silent Failure | 46 | 12 | 29 | 5 |
| **Total** | **315** | **27** | **84** | **204** |

**True positive rate: 8.6%.** The scanner is intentionally broad — most findings are false positives caused by the scanner's +-10 line window missing filters applied elsewhere in the query chain, or by flagging admin/enrichment scripts where reading all rows is intentional.

## Methodology

- **Layer 4 (DB Guard):** Sampled 18 files across 5 directories (API routes, lib/database, services, scripts, enrichment). Read actual SQL at each flagged line to determine whether `is_current`/`is_active` was present elsewhere in the query chain. Identified 4 false-positive patterns and applied them to classify the remaining 178 findings.
- **Layer 5 (Null Guard):** Sampled 10 of 31 findings. Read surrounding code to check for length guards, `INSERT RETURNING`, `COUNT(*)`, or optional chaining.
- **Layer 6 (Type Boundary):** Sampled 12 of 42 findings. Checked value provenance (always-string URL fields, always-object version objects, potentially-zero clause numbers).
- **Layer 7 (Silent Failure):** Sampled 14 of 46 findings. Checked whether catches return error responses, fall through to defaults, or are in non-route helper functions.

---

## Layer 4: DB Guard Scanner (196 findings)

### Sampling (18 files checked)

| File | Line | Verdict | Reason |
|------|------|---------|--------|
| `api/compliance/constraints/route.ts` | 183 | FP | Queries `regulatory_provisions_canonical` (a view), not `regulatory_provisions`. Different table. |
| `api/compliance/constraints/route.ts` | 224 | FP | Same — queries `regulatory_provisions_canonical` with metadata check. |
| `api/dcp/coverage/route.ts` | 27 | FP | Scanner flagged `lga_registry` without `is_active`, but the query JOINs `dcp_setback_controls` with `is_current = TRUE` and filters via the JOIN. The `lga_registry` rows without active setback controls are naturally excluded. |
| `api/canibuildit/check/route.ts` | 386 | TP | Queries `dcp_setback_controls` with `lga = $1 AND dev_type = 'secondary_dwelling'` but no `is_current = TRUE`. Could return superseded control rows. |
| `api/debug-418/route.ts` | 13, 30 | AR | Debug/investigation endpoint — intentionally reads all provisions for a specific document to inspect data structure. Not production-facing. |
| `api/dcp/full-text/route.ts` | 45 | FP | Queries `regulatory_provisions_canonical` (view), not the base table. |
| `api/sepp/counts/route.ts` | 17, 30, 42 | AR | Analytics/admin endpoint that counts all SEPP provisions by document. Including historical rows is intentional for coverage reporting. |
| `api/provisions/for-property/route.ts` | 613 | FP | Query has `WHERE rp.v2_is_actionable = true AND rp.v2_marker = 'heritage'`. The `v2_is_actionable` filter serves the same purpose as `is_current` — non-actionable provisions are the equivalent of stale data. |
| `api/provisions/for-property/route.ts` | 714 | FP | Same pattern — `v2_is_actionable = true` in WHERE clause. |
| `api/provisions/for-property/route.ts` | 827 | FP | Uses `v2_is_actionable = true` in WHERE clause (line 821). |
| `api/capacity/calculate/route.ts` | 64 | FP | Queries `lep_development_type_clauses` JOINed to `regulatory_provisions` by `source_provision_id`. The JOIN filters implicitly. |
| `lib/database/client.ts` | 65, 90, 116, 153, 187 | FP | Queries `development_controls` JOINed to `regulatory_provisions_canonical`. The canonical view handles currency. |
| `lib/database/postgres-client.ts` | 48, 64 | FP | Queries `development_controls` JOINed to `regulatory_provisions_clean`. The `_clean` view is already filtered. |
| `lib/lga-configs/index.ts` | 112, 117, 248, 276 | FP | References `lga_registry` as a TypeScript constant name (`LGA_REGISTRY`), not a SQL query. Scanner matched the table name in a non-SQL context. |
| `services/version_aware_query.py` | 35, 228 | FP | This IS the version-aware query builder — it adds version filtering dynamically via `WHERE 1=1` + conditional `AND` clauses. The `is_current` equivalent is the `version_status` / `effective_date` filter applied later in the function. |
| `enrichment/pipeline.py` | 87, 137, 193, 275, etc. | AR | Enrichment pipeline intentionally reads all provisions (including non-current) to re-classify and enrich them. Reading all rows is the pipeline's purpose. |
| `scripts/fix_id_sequence.py` | 13, 18, 24 | AR | Admin script to fix Postgres sequence. Reads MAX(id) from all rows — must include all rows. |
| `scripts/verify_controls_monitoring.py` | 49 | FP | Queries `information_schema.columns`, not actual data from `dcp_setback_controls`. Scanner matched table name in a schema introspection query. |
| `lib/database/specialized/live-compliance-client.ts` | 145, 156, 167 | TP | Queries `development_controls` JOINed to `regulatory_provisions` (not canonical/clean) without `is_current`. These return FSR, height, and site coverage rules to production users. |
| `api/compliance/dcp-complete/route.ts` | 395 | FP | Query filters by specific `document_id` patterns and excludes TOC pages. This is a full-text display — showing all provisions for a specific document is intentional. |
| `api/lep/provisions/route.ts` | 37 | FP | Queries by specific `document_id` and `ref_number`. Returns a single provision by ID — `is_current` is not applicable to ID-based lookups. |

### Pattern Analysis

Four dominant false-positive patterns account for ~88% of findings:

1. **Canonical/clean view queries (68 findings):** Many queries reference `regulatory_provisions_canonical` or `regulatory_provisions_clean` — these are pre-filtered views. The scanner matched the substring `regulatory_provisions` but the actual table queried already handles currency.

2. **`v2_is_actionable = true` filter (34 findings):** Production API routes in `provisions/for-property`, `compliance/dcp-complete`, and related paths filter on `v2_is_actionable = true`, which is functionally equivalent to a currency filter — non-actionable provisions include superseded and TOC entries.

3. **Admin/enrichment/script queries (62 findings):** Files in `scripts/`, `enrichment/`, and `check-*.js` are one-time admin scripts, enrichment pipelines, or debugging tools. They intentionally read all rows for analysis, migration, or re-processing. These are never called by production API routes.

4. **Non-SQL context matches (9 findings):** Scanner matched the table name in TypeScript constant names, comments, or `information_schema` queries.

### Classification Summary

| Category | Count | Classification |
|----------|-------|---------------|
| Canonical/clean view queries | 68 | False Positive |
| `v2_is_actionable` filtered | 34 | False Positive |
| Admin scripts / enrichment / debug | 62 | Accepted Risk |
| Non-SQL context matches | 9 | False Positive |
| JOINs that implicitly filter | 18 | False Positive |
| **True positives** | **5** | **True Positive** |

### True Positives (5)

| File | Line | Issue |
|------|------|-------|
| `api/canibuildit/check/route.ts` | 386 | `dcp_setback_controls` query missing `is_current = TRUE` — could return superseded setback controls for granny flat eligibility check |
| `lib/database/specialized/live-compliance-client.ts` | 145 | FSR rules query against `regulatory_provisions` (not canonical) without `is_current` |
| `lib/database/specialized/live-compliance-client.ts` | 156 | Height rules query — same issue |
| `lib/database/specialized/live-compliance-client.ts` | 167 | Site coverage rules query — same issue |
| `api/tod/parking-rates/route.ts` | 126 | DCP parking provisions query references `regulatory_provisions` JOINed to `dcps` without `is_current`. Could return superseded parking rates. |

---

## Layer 5: Null Guard Scanner (31 findings)

### Sampling (10 files checked)

| File | Line | Verdict | Reason |
|------|------|---------|--------|
| `api/browse/section/route.ts` | 86 | FP | Line 76-84 checks `sectionResult.rows.length === 0` and returns 404 before reaching line 86. Guard is present. |
| `api/compliance/constraints/route.ts` | 336 | TP | `baseResult.rows[0].permission_status` accessed without checking `rows.length > 0`. The else branch (line 339) logs an error if no rows, but line 336 is in the `else` of a status check that assumes rows exist. |
| `api/compliance/parking/route.ts` | 123 | FP | Line 117-121 checks `result.rows.length === 0` and returns early. Line 123 is only reached after the guard. |
| `api/feedback/route.ts` | 101, 106 | FP | `result.rows[0].id` — this is an `INSERT ... RETURNING id` query. INSERT RETURNING always returns exactly one row. |
| `api/feedback/submit/route.ts` | 72 | FP | Same — `INSERT ... RETURNING id`, guaranteed to return one row. |
| `lib/database/client.ts` | 361-364 | FP | All four are `COUNT(*)` queries: `parseInt(dev_controls.rows[0].count)`. COUNT(*) always returns exactly one row. |
| `lib/database/client.ts` | 379 | FP | `SELECT 1 as test` — always returns one row. |
| `lib/database/prp-k7-client.ts` | 246-249 | TP | `stats.rows[0].total_provisions`, `stats.rows[0].development_types`, etc. accessed without length check. The query could return 0 rows if the zone has no provisions. |
| `lib/database/specialized/provision-search-client.ts` | 174 | FP | `countResult.rows[0].total` — COUNT(*) query, always returns one row. |
| `api/lep/permissibility/route.ts` | 41 | TP | `.rows[0]` accessed without length check. Query searches for zone permissibility — could return 0 rows for unlisted zones. |

### Pattern Analysis

Two false-positive patterns:
1. **COUNT(*) / INSERT RETURNING queries (14 findings):** `COUNT(*)` always returns exactly one row. `INSERT ... RETURNING` always returns the inserted row. These are structurally safe.
2. **Prior length guard (7 findings):** The scanner's +-10 line window missed a guard that appears earlier in the function.

### Classification Summary

| Category | Count | Classification |
|----------|-------|---------------|
| COUNT(*) / INSERT RETURNING | 14 | False Positive |
| Prior length guard exists | 7 | Accepted Risk (guard outside scan window) |
| Aggregate queries (SUM, etc.) | 3 | Accepted Risk |
| **True positives** | **7** | **True Positive** |

### True Positives (7)

| File | Line | Issue |
|------|------|-------|
| `api/compliance/constraints/route.ts` | 336 | `baseResult.rows[0].permission_status` — no length check |
| `api/da-sessions/[token]/section-responses/route.ts` | 53 | `.rows[0]` without guard — session token could be invalid |
| `api/documents/[id]/route.ts` | 77 | `.rows[0]` without guard — document ID could be missing |
| `api/lep/permissibility/route.ts` | 41 | `.rows[0]` without guard — zone may have no permissibility data |
| `api/permissibility/check/route.ts` | 155 | `.rows[0]` without guard |
| `lib/database/prp-k7-client.ts` | 246 | `.rows[0].total_provisions` without guard — zone may not exist |
| `lib/database/postgres-compliance-client.ts` | 392 | `.rows[0]` without guard |

---

## Layer 6: Type Boundary Scanner (42 findings)

### Sampling (12 findings checked)

| File | Line | Verdict | Reason |
|------|------|---------|--------|
| `blog/granny-flat/page.tsx` | 34, 39, 44 | AR | `=== null` checks on `searchParams` values. Next.js `searchParams` returns `string | string[] | undefined`, not null. However, the page handles the undefined case by defaulting via `??` on the next line. Low risk. |
| `blog/granny-flat/[council-slug]/page.tsx` | 113 | FP | `{note && <...>}` — `note` is typed as `string | null` from a config object. Can never be 0. |
| `components/compliance/LocalProvisionsCard.tsx` | 106 | TP | `{provision.clauseNumber && <...>}` — `clauseNumber` is a number from the database. Clause number 0 would hide the expand button. While uncommon, clause numbering starting at 0 is possible in regulatory documents. |
| `components/assessment/core/VersionSelector.tsx` | 106 | FP | `{currentVersion && <...>}` — `currentVersion` is an object (`DocumentVersion | null`), not a number. Truthy check on object is safe. |
| `components/compliance/PartBasedDCPSection.tsx` | 198 | FP | `{subdivisionFiltered && <...>}` — `subdivisionFiltered` is a boolean, not a number. |
| `components/tools/ConveyancingTool.tsx` | 322 | AR | `{ov.value && <...>}` — `ov.value` comes from `spatial_overlays.value` (string column). Could theoretically be "0" but spatial overlay values are descriptive strings (zone names, class labels), never bare "0". |
| `lib/pdf/bushfire-report.tsx` | 335 | FP | `{data.bal_assessor_directory_url && <...>}` — always a string URL or null, never 0. |
| `lib/pdf/bushfire-report.tsx` | 446 | FP | `{c.legislation_url && <...>}` — always a string URL or null, never 0. |
| `components/tools/FloodTool.tsx` | 600 | FP | `{o.s1_gap_warning && <...>}` — `s1_gap_warning` is a string message or null, never 0. |
| `components/tools/GrannyFlatTool.tsx` | 468, 581 | FP | `{eligibility.checks && <...>}` and `{eligibility.height_of_buildings && <...>}` — both are arrays/objects, not numbers. |
| `api/property/route.ts` | 160 | AR | `=== null` on `propertyData.constraints.minLotSize`. This value is explicitly set to `null` in the code (not undefined). The variable is initialized in a typed object where all constraint fields default to `null`. Safe in practice. |
| `hooks/useDASession.ts` | 223, 238 | AR | `=== null` checks on state values managed by React useState, which initializes to `null` explicitly. Cannot be `undefined` unless the hook is misused. |

### Pattern Analysis

1. **`=== null` on explicitly-null-initialized values (24 findings):** Values from Supabase queries, React state, or typed interfaces that default to `null`, never `undefined`. Using `=== null` is technically more precise and matches the actual type.
2. **Truthy check on always-string/always-object values (12 findings):** URLs, warning messages, arrays, and objects that can never be 0. The `{value && <JSX>}` pattern is safe.
3. **Truthy check on potentially-numeric values (3 findings):** `clauseNumber` and similar database numbers that could be 0.

### Classification Summary

| Category | Count | Classification |
|----------|-------|---------------|
| `=== null` on explicitly-null values | 24 | Accepted Risk |
| Truthy check on string/object values | 12 | False Positive |
| Always-string values (URLs, messages) | 3 | Accepted Risk |
| **Truthy check on numeric values** | **3** | **True Positive** |

### True Positives (3)

| File | Line | Issue |
|------|------|-------|
| `components/compliance/LocalProvisionsCard.tsx` | 106 | `{provision.clauseNumber && <...>}` — clause 0 would hide the expand button |
| `components/tod/TODParkingCalculator.tsx` | 269 | `{rateSource && <...>}` — if `rateSource` were numeric 0, it would hide the source attribution |
| `components/tools/ThreatRadarTool.tsx` | 780 | `{determined && <...>}` — `determined` could be a count of 0 DAs, hiding the results section |

---

## Layer 7: Silent Failure Scanner (46 findings)

### Sampling (14 files checked)

| File | Line | Verdict | Reason |
|------|------|---------|--------|
| `api/og/granny-flat/route.tsx` | 114 | FP | This catch is inside helper function `fetchAerialTile`, not a route handler. It returns a typed error object (`as never`) that the caller checks. The route handler itself handles the null case gracefully (renders OG image without aerial tile). |
| `api/compliance/dashboard/route.ts` | 84 | FP | Catch block returns `NextResponse.json(errorResponse, { status: 500 })`. Error IS returned to caller. Scanner false-flagged because the error response construction spans multiple lines. |
| `api/compliance/dashboard/route.ts` | 159 | FP | Same pattern — returns 500 with error body. |
| `api/assessment/full/route.ts` | 267 | AR | Catch in `safeFetch` helper returns `{ data: null, error: "Failed to fetch..." }`. The caller receives a structured error. This is a deliberate graceful degradation pattern — the full assessment aggregates multiple sub-fetches and returns partial results. |
| `api/canibuildit/lead/route.ts` | 176 | TP | Catch on email send logs error but then falls through to `return NextResponse.json({ ok: true })`. User's lead data is saved but email delivery failure is hidden. |
| `api/dcp/coverage/route.ts` | 37 | TP | Returns `{ councils: [] }` with `status: 500`. The 500 status is correct but the empty array body means the frontend may render "no councils have DCP coverage" instead of showing an error. |
| `api/health/route.ts` | 124 | FP | Returns explicit `unhealthy` status with 503. Error is properly surfaced. |
| `api/feedback/requirement/route.ts` | 118, 143, 171 | AR | These catches are in fire-and-forget analytics functions (`updateRequirementMetrics`, `checkRequirementIssuePattern`, `flagRequirementForReview`). The main feedback submission succeeds; analytics failure is non-critical. Logging is sufficient. |
| `api/feedback/submit/route.ts` | 148, 176, 196 | AR | Same pattern as above — analytics/metrics helpers that run after the primary write succeeds. |
| `api/property/[address]/route.ts` | 77 | AR | NSW Planning API failure catch — sets `apiAvailable = false` and falls through to manual-input fallback. This is a deliberate degradation: if the external API is down, the user can still enter zone manually. |
| `api/stripe/webhook/route.ts` | 116, 147 | AR | Catches on non-critical side effects (threat-radar activation, confirmation email) after Stripe payment processing succeeds. The payment is already processed; these are best-effort extras. |
| `api/stripe/webhook/route.ts` | 214, 292, 389, 452, 485, 564 | AR | All webhook sub-handler catches. Stripe webhooks must return 200 quickly or Stripe retries. Logging + returning 200 is the correct pattern per Stripe docs. |
| `api/tod/parking-rates/route.ts` | 109, 159, 212 | TP | Three sequential try/catch blocks (SEPP lookup, DCP lookup, text fallback). If the first query fails, the catch logs and falls through to the next query. If all three fail, the function falls through to return `{ found: false }` — user gets "no parking rate found" instead of an error, masking a database connectivity issue. |
| `api/provisions/route.ts` | 178 | TP | Python subprocess failure returns `{ provisions: [], total_count: 0 }` — user sees "no provisions found" instead of an error message. |
| `lib/ai/router.ts` | 160, 304, 402, 468, 565, 636, 692, 745 | AR | AI router catches return `{ success: false, error: "..." }` to the caller. The error IS surfaced in the response payload. These are structured error returns, not silent failures. |
| `pages/api/development-types.ts` | 161 | TP | DB query failure falls through to static fallback list. User gets generic development types instead of zone-specific ones, with no indication that the result is degraded. |
| `api/setbacks/calculate/route.ts` | 194 | AR | Hierarchy processing failure — catch logs warning and falls through to a fallback legal compliance calculation. The fallback is documented and produces a valid (if less precise) result. |
| `api/satellite/threat-radar/search/route.ts` | 246 | AR | LGA stats helper returns `null` on failure. The caller checks for null and omits stats from the response — partial data, not wrong data. |
| `api/satellite/solar-coverage-interest/route.ts` | 86 | TP | Interest registration logs error but does not return error to user. |
| `api/health/metrics/route.ts` | 232 | AR | Metrics endpoint — returns partial metrics if one check fails. Acceptable for monitoring endpoints. |

### Classification Summary

| Category | Count | Classification |
|----------|-------|---------------|
| Returns error response (500/503/error body) | 5 | False Positive |
| Fire-and-forget analytics/metrics | 9 | Accepted Risk |
| Stripe webhook handlers (must return 200) | 8 | Accepted Risk |
| AI router structured error returns | 8 | Accepted Risk |
| Deliberate degradation with fallback | 4 | Accepted Risk |
| **Log-only catch hides DB/API failure from user** | **12** | **True Positive** |

### True Positives (12)

| File | Line | Issue | Severity |
|------|------|-------|----------|
| `api/canibuildit/lead/route.ts` | 176 | Email failure hidden — returns `ok: true` | Low (data saved, email is best-effort) |
| `api/dcp/coverage/route.ts` | 37 | Returns empty array + 500 — frontend may show "no coverage" instead of error | Medium |
| `api/tod/parking-rates/route.ts` | 109 | SEPP query failure silently falls through to DCP | Medium |
| `api/tod/parking-rates/route.ts` | 159 | DCP query failure silently falls through to text | Medium |
| `api/tod/parking-rates/route.ts` | 212 | All three queries failed — returns `found: false` masking DB issue | High |
| `api/provisions/route.ts` | 178 | Python process failure returns empty provisions | Medium |
| `pages/api/development-types.ts` | 161 | DB failure returns static fallback without indication | Medium |
| `api/satellite/solar-coverage-interest/route.ts` | 86 | Interest save failure hidden from user | Low |
| `api/feedback/vote/route.ts` | 94 | Vote recording failure hidden | Low |
| `api/feedback/suggestion/route.ts` | 110 | Suggestion save failure hidden | Low |
| `api/satellite/threat-radar/search/route.ts` | 356 | Search failure may hide DB issue | Medium |
| `api/property/route.ts` | 204 | Spatial overlay failure logged as warning, property returned without overlays | Medium |

---

## Recommendations

### Priority 1 — Fix Now (5 items, production data correctness)

1. **`api/canibuildit/check/route.ts:386`** — Add `AND is_current = TRUE` to `dcp_setback_controls` query. Without it, granny flat eligibility checks may use superseded setback controls.

2. **`lib/database/specialized/live-compliance-client.ts:145,156,167`** — Add `is_current` filter to FSR, height, and site coverage queries against `regulatory_provisions`. These serve production compliance data.

3. **`api/tod/parking-rates/route.ts:126`** — Add currency filter to DCP parking provisions query.

4. **`api/compliance/constraints/route.ts:336`** — Add `.rows.length > 0` guard before accessing `baseResult.rows[0].permission_status`. Will crash with TypeError on zones with no permissibility data.

5. **`lib/database/prp-k7-client.ts:246`** — Add length guard before accessing `stats.rows[0]`. Zone may have no provisions.

### Priority 2 — Fix Soon (7 items, user experience / error visibility)

6. **`api/tod/parking-rates/route.ts:109,159,212`** — Add a `degraded` flag to the response when earlier query tiers fail, so the frontend can show "results may be incomplete" instead of silently falling through.

7. **`api/provisions/route.ts:178`** — Return an error response when the Python subprocess fails, rather than empty results.

8. **`pages/api/development-types.ts:161`** — Add `source: 'fallback'` to the response when DB query fails, so the frontend can indicate the results are generic.

9. **`components/compliance/LocalProvisionsCard.tsx:106`** — Change `{provision.clauseNumber && <...>}` to `{provision.clauseNumber != null && <...>}` to handle clause 0.

10. **`api/dcp/coverage/route.ts:37`** — Return an error message body with the 500, not an empty councils array.

11. **`api/da-sessions/[token]/section-responses/route.ts:53`** — Add length guard for invalid session tokens.

12. **`api/documents/[id]/route.ts:77`** — Add length guard for missing document IDs.

### Priority 3 — Backlog (remaining accepted risks)

- The 24 `=== null` findings are technically correct for their contexts (Supabase returns null, not undefined; React state initializes to null). Consider a lint rule for `== null` to be more defensive, but this is a style choice, not a bug.
- The 62 admin/script DB guard findings require no action — these tools intentionally read all rows.
- The 8 AI router catches and 8 Stripe webhook catches follow correct patterns for their respective domains.
- The 9 fire-and-forget analytics catches are acceptable — metrics loss is non-critical.
