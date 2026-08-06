# Data Quality Tracker

**Purpose:** Track data quality issues systematically across Claude sessions.

**Last Updated:** 2026-08-06
**Session:** Memory-consolidation pass — closed-issue narratives moved to `DATA_QUALITY_ARCHIVE.md`

---

## Quick Status

| Issue | Status | Priority |
|-------|--------|----------|
| DQ-44: **Flood served "Microsoft Planetary Computer S1 RTC" as a data source on EVERY report while no S1 query has ever run** (`sar_flood_detected` hard-nulled; batch is a Phase-3B stub) — a named source with no query behind it, on the flood report + PDF ("Most recent pass" implied an analysis). | ✅ Fixed 2026-08-03 — source appears only with a SAR result (`flood_truth._build_data_sources`); PDF SAR row says "Not analysed in this report"; manifest records `sentinel1_sar.queried: false`. Two old-doctrine tests flipped with reasons. | P1 (was) — false source claim on served output |
| DQ-45: **granny_flat lot clipping crashed on every surviving detection** — the filter-loop variable `bbox` shadowed the tile-bbox dict, so WGS84 conversion and `_pixel_area_to_m2` string-indexed a pixel LIST → TypeError → whole run collapsed to `detection_failed` whenever detection got that far. | ✅ Fixed 2026-08-03 — renamed to `bbox_px`; pinned by two loop-survival tests (test_execution_manifests.py). | P1 (was) — silent product-killing crash |
| DQ-46: **Terrain asserted "Geoscience Australia 5m DEM" even when the SIX Maps photogrammetry fallback served the raster** — the provider decision was only logged; the interpretation's `data_source` was a static claim. | ✅ Fixed 2026-08-03 — `fetch_dem_region_with_provider` returns the actual provider; `data_source` names it (or says "provider not recorded"); old pin flipped. | P2 (was) — misattributed source on served output |
| DQ-43: **`dcp_plan_as_at` is keyed by LGA, not plan identity** — an as-at date binds to the plan named in the section header, but a council serving current controls sourced from TWO plans (Waverley holds 4 `v2012-current` rows beside its 2022-plan rows) would date the older rows with the newer plan's date. Not live today: the only date-rendering LGAs were verified single-plan (ashfield portal; 8 stated LGAs), and Waverley renders no date. Durable fix needs the plan-identity model from the condition-structuring workstream — deriving identity from `dcp_version` labels is the banned parsing class. | 🟠 Logged 2026-08-03 (Sol finding, overridden with reason) — revisit when plan identity exists | P2 — latent, no live exposure |
| DQ-41: **528 of 893 `dcp_setback_controls.effective_date` values were `YYYY-01-01` manufactured from `dcp_version` labels** (migration 040's parser: `v2016-current` → 2016-01-01; `v2014-amended-feb-2026` → 2014-01-01, contradicting its own label). | ✅ Fixed 2026-08-03 — cohort NULLED (authorized): 528/528 via `scripts/repair_dq41_null_label_derived_dates.py`, backup `dcp_setback_controls_dq41_null_20260803`, verify 365 dates remain / 0 Jan-1. Nothing lost: `dcp_version` retained, `dcp_plan_as_at` is the precision-honest re-derivation home. The 365 surviving non-Jan-1 dates still carry no basis (separate question, unattributed, not served). | P2 (was) |
| DQ-42: **NSW Planning Portal `/dcp` records are stale for 5+ served LGAs** — lists pre-merger plans for Canterbury-Bankstown (Bankstown 2015 / Canterbury 2012), Cumberland (Auburn/Holroyd) and Georges River (Hurstville/Kogarah); Canada Bay shows DCP 2017 vs the council's 2020 plan; Hornsby shows DCP 2013 (amended 2019) vs the 2024 plan; all Inner West parcels map only to the Ashfield comprehensive plan. Permanent evidence that the portal-first authority hierarchy REQUIRES the served-plan identity cross-check in `scripts/fetch_dcp_as_at_dates.py` — a portal date must never attach across an identity mismatch. | 🟠 Logged 2026-08-03 — guarded in code (identity match + fail-closed), portal upstream not fixable by us | P2 — guarded, permanent constraint |
| DQ-40: **28 controls whose `control_type` contradicts their own quote — 26 SERVED.** A secondary-street setback (2–4m) served as the primary front setback (4.5–6m), across ≥10 councils. 24 of the 28 PASS the value checker: the number matches, the control is wrong. A class that check structurally cannot see. | 🟢 Fixed 2026-08-03 — 20 re-filed (migration 054), canada_bay 701 repaired 1.5→6.0, MISSING_PRIMARY set adjudicated against source (2 adds, 1 retire, 2 fail-closed flags); 3 rows remain open pending non-local sources / authorisation (see section below) | P1 (was) |
| DQ-39: **25 of 986 stored control values are not derivable from their own quoted `source_text`.** Four Waverley deep-soil rows store 10%/15% against a quote that says 50%; three Cumberland setbacks store 4.0/5.5/8.0 m against a quote whose only figure is "Minimum 6m"; two rows store a number while their own quote says "needs PDF verification". Now gated for all 1,069 rows. | 🟠 Measured + gated 2026-08-02, data not fixed | P1 — the number IS the product |
| DQ-36: Provisions PDF hardcoded "Transport Oriented Development: ✗ Not applicable — property not within 400m of metro station"; the component receives NO TOD data, so the claim was unconditional. Four further SEPPs asserted "✗ Not applicable" for a proposal the report never sees. | ✅ Fixed 2026-08-01 | P1 — false statement of site fact |
| DQ-35: conveyancing_db.fetch_dcp_setbacks cited rows[0] from the UNFILTERED list, so clause_ref could name a control the function had just suppressed (needs_review) or excluded as belonging to a DIFFERENT zone | ✅ Fixed 2026-08-01 | P1 — citation is the product claim |
| DQ-34: ContextSection.tsx PDF "Housing SEPP 2021: ✓ Applies" line was a zone-only check, contradicting this same file's own determineDevelopmentPathway() on heritage land | ✅ Fixed 2026-08-01 | P1 — liability language on a definitive claim |
| DQ-33: document_id naming mismatch (verbose vs slug) caused silent ALL/ALL applicability fallthrough across Marrickville/Ashfield/Leichhardt — **9,854 served rows. FIXED + re-tagged 2026-08-01**; `no_config` on served rows 9,854 → 1,278 | ✅ Fixed 2026-08-01 | P1 — silent fallthrough class |
| DQ-32: Capacity engine ignores zone when picking setback/landscaping numbers — 560 rows across 168 lga/dev-type groups can return the wrong value | ⏳ Tracked 2026-07-31, not started | P1 |
| DQ-31: housing-sepp/eligibility over-eligibility — absent `isLMRArea` meant "yes"; the AI router additionally hardcoded `isLMRArea: true` and invented `zone`/`lotSize`/`lotWidth`. **Over-eligibility CLOSED 2026-08-01; full consolidation onto the Python service still open.** | 🟠 Wrong answer fixed, consolidation open | P1 |
| DQ-30: Applicability tagger — CODE fixed (PR1-4, this PR). **DATA NOT fixed: 286 rows still carry retired zone codes, 14 of them live+actionable in councils the retag covered.** The "0% drift" verification was invalid — it cannot fail. | 🟠 Code fixed, data open 2026-08-01 | P1 — validity, not traffic |
| DQ-29: Doubled-character OCR corruption in provision_text — 845 header lines stripped (backup saved); 22 scrambled-body rows remain for re-extraction | 🟡 Partially fixed 2026-07-15 | P1 |
| DQ-28: Ashfield chapter_e2_haberfield TOC — catch-all entry only, no section-level TOC extracted | ✅ Fixed 2026-03-30 | P2 (was) |
| DQ-24: Transport & Infrastructure SEPP v2_topic retag | ⏳ Backlog | P3 |
| DQ-25: Transport & Infrastructure sepp_structured_requirements empty | ⏳ Backlog | P2 |
| DQ-26: Marrickville truncated pdf_page_image_url stems | ✅ Fixed 2026-03-04 | P1 (was) |
| DQ-27: Marrickville LaTeX math artefacts in provision_text | ✅ Fixed 2026-03-04 | P1 (was) |
| DQ-1: Precinct CDC=0 | ✅ Not a bug | N/A |
| DQ-2: Topic misclassification | ✅ Fixed | P1 (was) |
| DQ-3: Headers in provisions | ✅ Fixed | P2 (was) |
| DQ-4: v2_marker NULL | ✅ Accepted | P3 |
| DQ-5: Generic layer 78% | ✅ Expected | P3 |
| DQ-6: Duplicates (2%) | ✅ Accepted | P3 |
| DQ-7: Dev-type coverage | ✅ Fixed | P0 (was) |
| DQ-8: DCP-ONLY scope | ✅ Documented | P1 |
| DQ-9: DCP filter bug (IWLEP) | ✅ FIXED | P1 |
| DQ-10: Council-specific UI/UX | ✅ DOCUMENTED | P1 |
| DQ-11: Heritage sub-categorization | ✅ COMPLETE | P2 (was) |
| DQ-13: Leichhardt uncategorized topics | ✅ FIXED | P1 (was) |
| DQ-14: Leichhardt PDF URL coverage | ✅ FIXED | P1 (was) |
| DQ-15: Topic case inconsistency | ✅ FIXED | P2 (was) |
| DQ-16: Heritage topic fragmentation | ✅ FIXED | P1 (was) |
| DQ-17: "Orphaned" non-heritage provisions | ✅ NOT ORPHANED | N/A |
| DQ-18: Marrickville pdf_page mismatch | ✅ FIXED | P1 (was) |
| DQ-19: Part 9 pattern collision | ✅ FIXED | P1 (was) |
| DQ-20: Part 5/6 vs Part 9 precedence | ✅ FIXED | P2 (was) |
| DQ-21: Double-underscore doc_id patterns | ✅ FIXED | P2 (was) |
| DQ-22: TOC provisions marked actionable | ✅ FIXED | P1 (was) |
| DQ-23: Duplicate provisions in TOC view | ✅ FIXED | P1 (was) |

---

## DQ-40: control_type contradicts its own quote (2026-08-03) — CLOSED with 3 open rows

**Status:** 🟢 Fixed 2026-08-03. Detector: `scripts/measure_control_type_mismatch.py`
(v2 — matches boundary wording, the v1 blind spot that hid canada_bay 701).

**What was done (all against source PDFs in `data/dcps/`, evidence STRONG):**
- **canada_bay 701** — served rear 1.5m was the second-storey SIDE setback (C6 table,
  400-char truncated quote); corrected to **6.0m per C9 printed p.E-15**, quote replaced
  in the same write (rule 2b). `scripts/repair_canada_bay_rear_setback.py`; backup
  `dcp_setback_controls_cb701_repair_20260803`.
- **20 rows re-filed** `front_setback` → `secondary_street_setback` (migration 054 +
  `scripts/refile_secondary_street_setbacks.py`, applied 2026-08-02; backup
  `dcp_setback_controls_refile_backup_20260803`). Vocabulary synced 2026-08-03 across
  `enforce_control_type_vocabulary.sql`, `enrichment/config/control_type_vocabulary.py`,
  the structured-controls TS maps and SEE CATEGORY_MAP (served rows previously rendered
  under "Other" with a raw slug).
- **MISSING_PRIMARY adjudication** (`scripts/repair_missing_primary_controls.py`; backup
  `dcp_setback_controls_missing_primary_20260803`): ryde front 6.0m ADDED (id 1175,
  s2.9.1(a) p.25 — was stored NOWHERE); ryde 680 re-filed front→rear (its quote is
  s2.9.3(a), 8m floor of a greater-of rule) and 681 conditioned as the s2.9.3(b)
  exception; burwood side 0.9–1.5m ADDED (id 1176, Ch4 s4.5 Table 3 p.221) and 707
  conditioned as the P10 garage-wall rule; camden 691 re-quoted to Table 4-2 side 0.9m;
  fairfield 715 re-quoted to 5B.2.3.1(a) and **714 RETIRED** (its 6m is a Chapter 5C
  narrow-lot garage setback; 5B prescribes NO numeric front setback for secondary
  dwellings — camden-692 model); fairfield 716 and ryde 682 flagged `needs_review`
  (fail closed) — see open items.
- **Truncation escape closed (Sol's case):** `evidence_is_truncated` no longer exempts a
  400-char quote ending in punctuation — a cut can land after punctuation, and at the
  extractor cap a complete quote is indistinguishable from a severed one. All 21
  at-limit rows ended mid-word, so no verdict changed; the hole is closed for the next
  extraction.
- Detector heuristics: NARROWING terms inherent to a control type no longer flag it
  (car_parking↔garage, secondary_street_setback↔corner); settled false positives are
  suppressed with per-row reasons (KNOWN_FALSE_POSITIVES).

**After state (2026-08-03):** category A = **3 open** (was 28/26 served), category B =
**0** (was 6), truncated = 19. Value checker green, baseline 41 → 38 (shrink-only).

**Open rows (A):**
- **884 city_of_sydney** — clause 4.1.2 contains no numbers; stored 0m encodes an
  observed pattern. Fix (NULL + qualitative) adjudicated but not authorised; also
  provisional against the Jan-2026 amendment.
- **570 georges_river** — front 5.5m garage/carport clause; source PDF not local,
  UNVERIFIABLE this pass.
- **895 marrickville** — side/rear one-clause shape, likely correct (577/109/105
  pattern) but source not read; open until it is.

**Held fail-closed — APPLIED 2026-08-03 (authorised):** both repairs executed via
`scripts/repair_authorized_held_rows.py` (backup
`dcp_setback_controls_authorized_repairs_20260803`, all-or-nothing, rule 2b):
- **fairfield 716** — rear 6.0m (Chapter 5C narrow-lot first-floor value) →
  **0.9m per 5B.2.3.1(a)**, quote replaced in the same write, needs_review cleared.
- **ryde 682** — side 4.0m (design-preference quote) → **0.9–1.5m per
  s2.9.2(a)/(b)** (900mm one storey / 1.5m two storey, range-row per burwood
  1080/1176), needs_review cleared. Baseline 38 → 37 (682 left TRUNCATED_EVIDENCE).

**Extraction gaps found while ruling (ADD candidates, STRONG sources local, NOT done —
new extraction was out of scope):** ryde side 0.9/1.5 (s2.9.2) + secondary street 2m
(s2.9.1(b)); camden secondary street 2m + front tiers 6.5m/10m (Table 4-2); fairfield
corner secondary street 1.5m (5B.2.3.1(c)); burwood two-storey front 9m (Table 3);
cumberland secondary-dwelling rear 0.9/3m and side 0.9/1.5m per the Table quoted by row
34 (row 35's 1.2m side carries a basement quote — suspect).

---

## DQ-39: 25 control values their own quote does not support (2026-08-02) — SUMMARY

**Status:** MEASURED + GATED for all 1,069 rows; the 25 were ADJUDICATED 2026-08-03
against source PDFs: **12 CORRECT, 8 EXTRACTION_ERROR, 3 NO_NUMERIC_CONTROL_IN_SOURCE,
2 UNVERIFIABLE.** Full evidence: `docs/qa/controls-adjudication-2026-08.md`.
Remaining data work tracked under DQ-40's open rows.

Checking a number against **its own stored quote** needs no corpus or PDF, so coverage
went from 42 machine-checkable rows to all 1,069. Each derivation is a NAMED rule that
must produce the substring it matched (`scripts/validate_control_source_values.py`);
961 of 986 value-carrying rows (97.5%) are derivable from their own quote.

**Caveats that must not be forgotten:**
- 571 of 839 exact matches sit in quotes holding >1 quantity — *consistent*, not *pinned*.
- The check proves quote-consistency, NOT correctness; a mis-transcribed quote passes.
  That failure mode belongs to the extraction gates.
- Baseline is shrink-only, keyed on `id -> digest(value_min, value_max, unit, source_text)`.

**Wired:** pre-push `[1f/5]` and CI (`gates.yml` schema-contract job). Exit 2 on missing
`DATABASE_URL` is a skip, never a pass.

The 18 hardening rounds (false-explanation traps, unit gates, tolerance derivation,
NaN/baseline defects) are preserved verbatim in `DATA_QUALITY_ARCHIVE.md` — read them
before modifying the validator.

---

## DQ-38: only 42 of 1,069 controls can be machine-checked against the corpus (2026-08-02) — SUMMARY

**Status:** 42 links live (`dcp_setback_controls.provision_id`). Ceiling reported, not
chased. **The finding is the ceiling, not the 41:** 14 of 30 control LGAs have zero
provisions ingested (450 rows unmatchable). Of the remaining 545 unmatched, the cause is
mixed and for the majority UNKNOWN — "chapter not ingested" is disproven for 62% of them;
57 rows fail on normalisation alone. **Do not write a cause into this entry without
measuring it.**

- Linker: `scripts/link_controls_to_provisions.py` (dry-run default, exact single
  substring match only, `PRESERVE_EXISTING_LINKS`, re-runnable as councils are ingested).
- Gap measurement: `scripts/measure_control_quote_gap.py`.
- Coverage visible via `scripts/validate_controls_provenance.py`.
- **Advisory, never a gate** — requiring a link would fail on absent corpus, not defects.
- Rollback: `dcp_setback_controls_provlink_backup_20260802b` (13 rows) /
  `...20260802` (34 rows, pre-any-change).

Full analysis (cause tables, word-run overlap bands, the two safety defects caught in the
linker before the final write) preserved verbatim in `DATA_QUALITY_ARCHIVE.md`.

---

## DQ-32: Capacity engine picks setback/landscaping numbers without checking zone

**Status:** Tracked 2026-07-31, not started — found while checking DQ-30 didn't miss the real engine
**Found:** 2026-07-31

**Plain version:** `getSetbacks()` in `app/api/capacity/calculate/route.ts` is given the
property's zone but never uses it in the `dcp_setback_controls` query — it only filters by
council + dev type. When a council has different numbers for different zones (e.g. Penrith
`multi_dwelling_housing` landscaping: R1=40%, R3=40%, R4=35%), the query can hand back the
wrong one. Checked the DB: **168 council/dev-type groups, 560 rows, where this can give a
wrong number** — not a display bug, a wrong feasibility number shown to a real user.

**Fix:** not started. Needs the query to filter/select by zone against the `condition` text
column (free text like "zone R4 High Density Residential" — no clean zone column exists),
designed and tested carefully since it changes what the capacity engine returns.

**Also found (2026-07-31, not investigated further yet):** the scripts that WRITE
`dcp_setback_controls` in the first place (`scripts/insert_*_parking.py`,
`insert_*_landscaping.py`, `dcp_extract_changed.py`, `ai_extractor.py`,
`generate_conveyancing_report.py`, `conveyancing_db.py`, `dcp_preflight.py` — one per
council onboarding) also hardcode zone-code lists, some with the same retired B1/B2/B4
codes. Found via `python scripts/lint_hardcoded_zone_codes.py --all` (PR4). Means the
zone-code problem may go all the way back to how this table's data was written, not just
how it's queried. Needs its own look — not sized yet.

---

## DQ-31: housing-sepp/eligibility route never migrated to the Python service

**Status:** ⏳ Tracked 2026-07-31, not started — found as a side-effect of DQ-30 PR3, deliberately not folded into it
**Found:** 2026-07-31

**Problem:** `services/housing_sepp_eligibility.py`'s own docstring states it was written
specifically to *replace* `frontend-nextjs/app/api/housing-sepp/eligibility/route.ts`'s
logic — computing `inLMRArea` and TOD catchment **authoritatively** from live gate/polygon
data, because the frontend route "defaulted [inLMRArea] to true — a silent over-eligibility
bug" and "used a mock hardcoded station list + Haversine" instead of the real TOD catchment.
The docstring frames this as done ("the two surfaces can no longer disagree"), but the
migration never actually happened: the TS route still runs its own independent eligibility
logic and does not call the Python service. `app/api/upzoning/route.ts` proxies to
`/pipeline/upzoning` (which internally calls `housing_sepp_eligibility.evaluate_eligibility()`)
for a *different* frontend surface (the upzoning-check tool, input = bare address); there is
no equivalent live endpoint for `housing-sepp/eligibility`'s exact request shape
(`{address, zone, lotSize, developmentType, lga?, coordinates?}` — pre-resolved inputs).

**Why not a drop-in proxy fix:** `evaluate_eligibility()` only returns the eligibility gate
result (list of `FormEligibility`) — it does not replicate the numeric-standards DB fetch the
TS route also performs. Migrating this properly means either a new backend endpoint that
wraps both, or a more surgical partial fix — not a mechanical swap like `/api/upzoning` was.
Live-route regression risk: `components/compliance/HousingSEPPEligibilityCard.tsx` (rendered
on the assessment page) depends on the current response shape.

**Fixed 2026-08-01 — the wrong ANSWER, not the duplication.** Full consolidation onto
`services/housing_sepp_eligibility.py` remains open (it returns only the gate result, not the
numeric-standards fetch the TS route also performs, so it is not a drop-in). What was closed:

1. `const inLMRArea = isLMRArea !== false` → an ABSENT input meant "yes, in an LMR area", the
   single input the endpoint turns on, resolved in the claimant's favour. Now three-state:
   true / false / not-assessed, with not-assessed yielding "cannot confirm" rather than
   eligible — matching the Python service's fail-conservative contract.
2. **`lib/ai/router.ts` was worse than the route.** It hardcoded `isLMRArea: true` and
   substituted `zone || 'R2'`, `lotSize || 450`, `lotWidth || 12` — inventing four site
   measurements to force an answer for a property whose real values were unknown. Missing
   inputs now stop the check.
3. A SECOND fabrication in the same file: `handleDcpProvisionLookup` used `zone || 'R2'`, so
   an unknown zone returned **R2's DCP provisions** presented as this property's. The zone
   param is now omitted (it is optional on `for-property`, route.ts:297).

**Still open after this fix (raised by cross-review, verified, deliberately not fixed here):**
the endpoint treats a caller-supplied `isLMRArea: true` as authoritative, but the live page
derives it from `isLMRApplicable(zone, lga)` — a zone/LGA heuristic, NOT the parcel-level 776
exclusion layer that `services/housing_sepp_eligibility.py` uses. A parcel individually excluded
from the reform area can therefore still be reported eligible. Fixing it properly IS the
consolidation described above, not a patch: the alternative — refusing to trust any client
boolean — would make the Housing SEPP card read "Not Assessed" for every property until the
server-side derivation is wired, which is a product decision, not a code cleanup.

Same class as DQ-36: a verdict asserted from data nobody supplied. Guarded by
`frontend-nextjs/__tests__/api/housing-sepp-lmr-default.test.ts` (6 tests, mutation-verified).

---

## DQ-30: Applicability tagger (v2_applicable_zones / v2_applicable_dev_types) drift + config gaps

**Status:** 🟠 **CODE fixed, DATA still open, 2026-08-01.** An earlier revision of this entry
said "✅ Fixed" on the strength of a "0% drift" check. **That verification was invalid and the
status was wrong — corrected here.**

PR1 (shared zone taxonomy source), PR2 (DCP tagger config fixes), PR3 (frontend/Python
consolidation) and PR4 (CI guard) are complete on branch `fix/zone-taxonomy-consolidation`
(PR #853, not yet merged). pytest 3223 + jest 917 green.

**Why the verification was invalid.** "0% drift" re-runs the tagger and compares its output to
the stored DB value. That is a *self-consistency* check: if the code still emits a retired zone
code, drift is 0% and the data is still wrong. **A check that cannot fail when the bug is
present is not a verification.** This entry's own text warned about exactly this trap for
Ashfield/Leichhardt/Marrickville ("0% drift does NOT mean correct") and the metric was used
anyway.

**Actual DB state, queried against production 2026-08-01** — `regulatory_provisions` still holds
**286 rows with retired B/IN zone codes**:

| Scope | Rows | Note |
|---|---|---|
| ku_ring_gai + woollahra, `is_current` AND `v2_is_actionable` | **14** | **Served today, in councils PR5 covered.** 13 are Ku-ring-gai local-centre provisions tagged `B2`/`B4` (St Ives, Turramurra, Pymble, Gordon) — the original DQ-30 symptom, still live |
| woollahra, superseded | 71 | Not served, still wrong |
| NULL `source_council` | 142 | Never in retag scope — invisible to it |
| 7 no-config councils | 51 | Known out of scope |
| `dcp_all_provisions.applicable_zones` | 32 | Separate table, never examined |

**The correct check, replacing drift:** every stored zone code must exist in `lep_zone_coverage`
for that LGA where `is_complete = TRUE`. Exact set membership against ground truth — no regex, no
false positives, and it *can* fail when the bug is present. It would have caught all 286
instantly. Where coverage is incomplete it must report `unverifiable`, never `clean`. Spec:
`~/.claude/plans/ce-dcp-condition-structuring-2026-08.md` §2.5.

**Remaining work:** implement that check, then re-run the retag against it (not against drift),
including the NULL-council rows and `dcp_all_provisions`.
**Found:** 2026-07-31
**Priority:** P1 — driven by whether the data is **valid and legitimate**, not by whether
a given council is currently receiving traffic. Live/staged status is explicitly NOT
the triage signal for this issue (see `feedback-prioritize-validity-not-traffic.md`).
Do not close or deprioritize this on "council X isn't live yet" grounds.

**Problem (as originally understood):**
`enrichment/extractors/applicability_tagger.py` (`ApplicabilityTagger`) writes
`v2_applicable_zones` / `v2_applicable_dev_types`, consumed as a **hard filter** (not
just display) by `frontend-nextjs/app/api/provisions/for-property/route.ts` for
`layer='use_specific'` queries, plus relevance sorting for dev_types. Two distinct defect
classes found first:

1. **Stale pre-fix rows never retagged.** PR #341 (2026-05-22) added `_get_config_driven()`
   so councils with a structural config (Waverley, Woollahra, City of Sydney, Ku-ring-gai)
   stop guessing zones from free text — free-text regex was matching DCP chapter/topic
   labels as zone codes (e.g. Waverley Part B7 = "Transport" chapter, regex read "B7" as
   zone B7). `run_applicability_tagging()` only retags rows where `v2_applicable_zones IS
   NULL` (`enrichment/pipeline.py:671`), so rows tagged before #341 were never revisited.
   Re-running the (then-current) tagger against every already-tagged row and diffing against
   the stored value:

   | Council | Tagged rows | Disagree with current code | % |
   |---|---|---|---|
   | Waverley | 2,854 | 1,493 | 52.3% |
   | Ku-ring-gai | 2,524 | 1,011 | 40.1% |
   | City of Sydney | 742 | 269 | 36.3% |
   | Woollahra | 6,214 | 226 | 3.6% |
   | Ashfield / Leichhardt / Marrickville | 21,557 | 0 | 0% |

   Note: 0% drift does NOT mean correct — it means stored value == current code output,
   which is also wrong if current code itself has always been wrong (see below).

2. **Config-file / tagger-code drift (Marrickville) and undeclared intent (Waverley,
   Ku-ring-gai, City of Sydney).** `MARRICKVILLE_CONFIG['parts']` in
   `enrichment/config/marrickville_config.py` was not actually read by
   `ApplicabilityTagger._get_marrickville_config()` for zone/dev-type values — that method
   hardcoded its own separate copy inline, and the two had drifted (e.g. Part 4.3 Boarding
   Houses: config said zones restricted to residential+business, tagger said `ALL`). Waverley's
   own file header names C1/C2 and D1/D2 as distinct sub-parts with different zones, but
   `WAVERLEY_CONFIG['parts']` only had one "C" and one "D" key, so both collapsed to the same
   zone list. Ku-ring-gai's and City of Sydney's `chapter_topics` entries never set
   `applicable_zones`/`applicable_dev_types` at all (despite being labelled `use_specific`
   or `precinct`), so `_get_config_driven()` silently defaulted them to `ALL`/`ALL`.

**Verification pass (2026-07-31) found the issue was larger than the initial summary above:**

3. **ROOT CAUSE: the hardcoded zone constants themselves predate the NSW zone reform,
   and this project already had the fix (`lep_zone_coverage`) sitting unused.**
   `enrichment/config/{waverley,woollahra,ashfield,leichhardt,marrickville}_config.py` all
   hardcoded zone-code Python constants (`RESIDENTIAL_ZONES`, `BUSINESS_ZONES =
   ['B1','B2','B4']`, `INDUSTRIAL_ZONES = ['IN1','IN2']`, etc.) — exactly the
   pattern `.claude/rules/regulatory-data.md` prohibits ("NEVER hardcode NSW planning
   regulatory data... flag it and replace before shipping"). Cross-checked against
   `lep_zone_coverage` (live-scraped LEP land-use table, 26 LGAs, `is_complete=true`,
   scraped 2026-05-12, previously gate-verified per
   `memory/project-zone-permissibility-unblocked-2026-07.md`):

   | LGA (real, current) | Actual zones in `lep_zone_coverage` |
   |---|---|
   | Waverley | C2, E1, E2, MU1, R2, R3, R4, RE1, RE2, SP2 |
   | Woollahra | C1, C2, E1, MU1, R2, R3, RE1, RE2, SP2, SP3 |
   | Sydney (City of Sydney) | E1, E2, E3, E4, MU1, R1, R2, RE1, SP1, SP2, SP5 |
   | Inner West (Ashfield/Marrickville/Leichhardt's real current LGA) | E1, E2, E3, E4, MU1, R1, R2, R3, R4, RE1, RE2, SP1, SP2, W1, W2, W4 |
   | Ku-ring-gai | C1, C2, C3, C4, E1, E3, MU1, R1–R5, RE1, RE2, SP1, SP2, W1 |

   **None of these five LGAs has a single B-zone or IN-zone today.** Real April 2023 NSW
   Employment Zones Reform mapping, confirmed against DPE's own transition table:
   B1,B2→E1; B3,B8→E2; B5,B6,B7→E3; IN1,IN2→E4; IN3→E5; B4→MU1; IN4→W4. (An earlier
   attempt at this mapping in `frontend-nextjs/lib/zone-translation.ts` had B4 wrongly
   under E2, IN1/IN4 wrongly under E4, IN2 wrongly under E5 — corrected in PR1 below.)
   `MARRICKVILLE_CONFIG`/`ASHFIELD_CONFIG`/`LEICHHARDT_CONFIG` actively tagged every
   Commercial-part provision with `B1/B2/B4` and every Industrial-part provision with
   `IN1/IN2` — codes that do not exist in the real Inner West LEP. For Marrickville Part 5
   (Commercial) this was harmless in practice because `MU1` was unioned into the
   same list alongside the dead codes, so real MU1-zoned properties still matched. **For
   Marrickville Part 6, Ashfield Chapter F Part 7, and Leichhardt Part F (Industrial),
   the zone list was `['IN1','IN2']` with no current-code fallback at all** — meaning,
   under the hard-filter query in `for-property/route.ts:936-940`, these provisions could
   not match ANY real property, because no property is zoned IN1/IN2 anymore. This was the
   exact "hide a rule, nobody would find out" failure the original conversation opened with
   — not hypothetical, and not confined to the 4 councils with drift.

   This also means the "0% drift" reported for Ashfield/Leichhardt/Marrickville above
   was misleading on its own: 0% drift only means the code agreed with itself over
   time — it says nothing about whether the zone codes were ever right. They were not.

4. **Systematic (not manual) config-vs-tagger diff across all 7 config-driven councils**
   confirmed the 3 Marrickville divergences already listed (Part 4.3, Part 5 dev_types,
   Part 6 dev_types) and surfaced one new, previously-unknown, latent bug: Ashfield's
   `chapter_f_parts` lookup in `_get_ashfield_config()` iterated the dict in insertion
   order and did unanchored substring matching (`f'Part_{part_num}' in document_id`) —
   `"Part_1"` matched inside `"Part_10"`, so any Chapter F Part 10 document would have been
   silently mistagged as Part 1 (Dwelling Houses) instead of the correct
   ALL-zones/ALL-dev-types. Same bug class as the already-fixed DQ-19 (Part 9 pattern
   collision). **Current DB impact: zero** — no Ashfield document_id matching Part_1X
   exists yet (checked directly), so this was latent, not live. Confirmed no equivalent
   collision in Leichhardt/Woollahra/Waverley/CoS/Ku-ring-gai.

5. **The ~9 councils with no structural config at all (Parramatta, Hornsby, Penrith,
   Blacktown, Campbelltown, Northern Beaches, Georges River, Cumberland, Inner West-as-
   tagged) are not a staleness issue — they are a standing, since-day-one exposure to the
   exact blind-text-regex false-positive class PR #341 was written to fix for the other 4,
   because they were simply never given a config.** ~175 of ~1,124 tagged rows carry
   multi-zone "kitchen sink" tags (e.g. Northern Beaches: one provision tagged
   `[B1,B2,B5,B7,E3,IN1,IN2,R2,R3]` — 9 zones on one provision, the signature of text-regex
   picking up every zone mentioned anywhere in the passage, not genuine applicability).
   Out of scope for the current fix — needs new structural configs per council, a separate
   follow-up. Partial investigation for Northern Beaches (only Warringah is actually
   ingested — 49 rows, one document_id, `v2_dcp_part='unknown'` for every row, no per-part
   structure to key a config off yet; `docs/DCP_SCOPE_CONFIG_REFERENCE.md` has partial
   structural knowledge — Parts A-E universal, zone differentiation in Part F — but that's
   for a *different* config system, `lib/council-configs/{council}.json`'s DA-mode scope
   filtering, not `enrichment/config/*.py`'s applicability tagging).
   Cheap interim mitigation identified for these 9 (not yet built): intersect the blind
   regex's zone matches against `get_valid_zones_for_lga()` (PR1) before returning, killing
   the "kitchen sink" false-positive class without needing DCP structure knowledge.

6. **The B→E zone-code confusion is codebase-wide, not confined to the DCP tagger — and a
   correct fix for it already exists but was barely adopted.** Full-repo grep for hardcoded
   zone-code array literals (not just the applicability tagger) found the same defunct
   B1-B8/IN1-IN4 codes hardcoded independently in ~20+ locations: `frontend-nextjs/lib/
   regulatory-constants.ts` (NSW_STANDARD_ZONES, feeds LMR/apartment-eligibility checks
   across granny flat, CDC screener, exempt/complying, SEE builder), `services/
   housing_sepp_eligibility.py` (`RESIDENTIAL_ZONES` — confirmed correct on investigation,
   see PR3 below), and a `HOUSING_SEPP_ZONES = ['R1','R2','R3','R4','B1',
   'B2','B4']` literal copy-pasted verbatim across 4 separate files (`see-helpers.ts`,
   `seeBuilders.ts`, `section-aggregation.ts`, `ContextSection.tsx`), among
   others (`environmental-relevance-filter.ts` — confirmed dead code, `ADGSummaryCard.tsx`
   — a *separate* real bug found and fixed in PR3, see below, `ComplianceDashboard.tsx` and
   `pages/api/development-types.ts` — confirmed dead code). None of these imported a shared
   source or queried `lep_zone_coverage`.

   **This exact problem (B1/B2 vs E1 zone-code mismatch) had already happened once before,
   in a *different* table/pipeline**, per
   `.claude/docs/history/2026-01-implementation/ZONE_AND_DEVTYPE_TRANSLATION_CONTEXT.md`
   (Nov 2025): `dcp_general_requirements.applicable_zones` (the LLM-curated table behind
   the capacity/compliance API, separate from `regulatory_provisions.v2_applicable_zones`
   behind the provisions display) had the identical defect. The fix built then —
   `frontend-nextjs/lib/zone-translation.ts`, `ZONE_TRANSLATION_MAP` — modelled the right
   *concept* but, on verification, had its own mapping errors (see #3 above). It was also
   only ever wired into 2 routes (`/api/compliance/constraints`, `/api/compliance/
   dcp-complete`) — and a full reachability audit found **both of those routes are
   themselves dead code**, only reachable through the orphaned `ComplianceDashboard.tsx`
   which nothing in the live app renders. So `zone-translation.ts` had zero live consumers
   before this fix. The real live critical path for DCP provisions is
   `ProvisionsByTocStructure.tsx` → `app/assessment/page.tsx`, confirmed via reachability
   audit, which is what the applicability tagger (PR2) actually feeds.

**Fix — sequenced as PR1 through PR5 (see `~/.claude/plans/twinkly-bouncing-valiant.md` for
the full plan):**
- **PR1 (done):** `frontend-nextjs/shared/zone-taxonomy.json` — single corrected
  legacy↔current alias map, generated by `scripts/generate_zone_taxonomy.py` (CI drift-check
  via `--check`), consumed by both `frontend-nextjs/lib/zone-translation.ts` (TS) and the new
  `enrichment/config/zone_taxonomy.py` (Python) — no more independent copies. Added
  `getValidZonesForLga()` to both `frontend-nextjs/lib/db.ts` and `services/db_config.py`
  (live query against `lep_zone_coverage`, short in-process cache) for the separate question
  of "what zones currently exist in LGA X."
- **PR2 (done):** Marrickville tagger now reads `MARRICKVILLE_CONFIG['parts']` directly
  instead of a hardcoded shadow copy; Ashfield `Part_1`/`Part_10` collision fixed (word-
  boundary anchored); Waverley `WAVERLEY_CONFIG['parts']` split into C1/C2 (R2 vs R3,R4) and
  D1/D2 (E1,E2 vs MU1), matching the file's own documented distinction; Ku-ring-gai's 5
  residential parts whose name *is* the dev type now set `applicable_dev_types`; all 7
  configs' zone constants swapped to current-era codes; Woollahra's Part D/F3 direct B-zone
  literals fixed (not routed through a constant, hardcoded per-entry — same translation
  applied inline). City of Sydney's `section_4` and Ku-ring-gai's `part_8_mixed_use`/
  `part_9_non_residential` deliberately NOT filled in — would mean guessing at regulatory
  scope, not translating something already stated. Extended
  `tests/enrichment/test_applicability_tagger.py` with regression tests per bug (46 tests
  total, 13 new, all passing).
- **PR3 (done):** consolidated live frontend/Python zone hardcodes onto PR1's shared
  source — `regulatory-constants.ts`, `housing_sepp_eligibility.py`, the granny flat cluster
  (`app/api/satellite/granny-flat/route.ts`, `app/reports/granny-flat/page.tsx`,
  `app/api/canibuildit/check/route.ts`, `app/api/og/granny-flat/route.tsx`), and the
  SEE/CDC/pattern-book cluster (`lib/see/seeBuilders.ts`, `lib/see/section-aggregation.ts`,
  `lib/pdf/see-helpers.ts`, `components/pdf/ContextSection.tsx`,
  `components/compliance/ExemptComplyingProvisions.tsx`,
  `components/compliance/CDCScreener.tsx`, `components/compliance/ADGSummaryCard.tsx`,
  `app/api/sepp/exempt-complying/route.ts`, and
  `lib/pattern-book-eligibility/check-exclusions.ts`'s `isZoneEligible()`, whose own
  `['R1','R2','R3']` literal was the last remaining hardcode — now a new
  `PATTERN_BOOK_CDC.ELIGIBLE_ZONES` export in `regulatory-constants.ts`, deliberately not
  merged with `CDC_HOUSING_CODE_ZONES` since Pattern Book excludes R4/RU5). Also found and
  fixed a **separate real bug** while doing this: `components/compliance/ADGSummaryCard.tsx`'s
  `APARTMENT_RESTRICTED_ZONES` had current Employment zones E1-E4 mislabelled as "Environment
  zones," directly contradicting `NSW_STANDARD_ZONES.APARTMENT_PERMITTING` (E1/E2 correctly
  permit apartments/shop-top housing) — fixed. Also found `app/api/housing-sepp/eligibility/
  route.ts` has a deeper, separate issue than zone-code staleness (tracked as DQ-31 above, not
  folded into this fix). Verified clean via `python scripts/lint_hardcoded_zone_codes.py --all`
  (only pre-existing, out-of-scope hits remain: historical `scripts/fixes/DQ*.py` one-off
  scripts, the free-text `ZONE_PATTERNS`/`ZONE_CATEGORY_PATTERNS` regex fallback in
  `applicability_tagger.py` used for the ~9 no-config councils, and other pre-existing files
  untouched by PR1-3 — none are new hardcodes introduced by this work).
- **PR4 (done):** CI guard `scripts/lint_hardcoded_zone_codes.py` (following
  `scripts/lint_bracket_access.py`'s staged-diff pattern) wired into `.githooks/pre-commit`
  step 8 — fails a commit that introduces a new hardcoded zone-code array in a file that
  doesn't already import the shared taxonomy, with a `# noqa: zone-codes` escape hatch.
  Diff-scoped (only checks staged additions), so it does not fail-red on pre-existing
  hardcodes not yet fixed (the 9 no-config councils, City of Sydney's `section_4`, the
  historical `scripts/fixes/DQ*.py` scripts).
- **PR5 (done):** backup + guarded reset of `v2_applicable_zones`/`v2_applicable_dev_types`
  to NULL for the 7 configured councils' affected rows, re-ran `run_applicability_tagging()`
  with the fixed tagger. Verified: re-running the drift script (fixed tagger output vs stored
  DB value) shows **0% disagreement** across all 7 configured councils, confirming the retag
  matches current code by construction.

---

## DQ-29: Doubled-character OCR corruption in provision_text

**Status:** 🟡 Partially fixed 2026-07-15 — 845 header lines stripped in DB; 22 scrambled-body rows remain for re-extraction
**Found:** 2026-07-15 (surfaced by the latent-scope duplicate-audit lane)
**Priority:** P1 (>2% threshold breached for affected councils; City of Sydney ~97% of live actionable rules)

**Problem:** In affected provisions every character of the extracted text is
doubled, e.g. `SSPPEECCIIFFIICC SSIITTEESS`, `KKuu--rriinngg--ggaaii`,
`DDeevveellooppmmeenntt`. The `provision_text` is effectively unreadable — the
field customer-facing reports and the capacity/compliance engines read from.

**How it was found:** The cross-council duplicate audit
(`scripts/latent_scope_dup_audit.py`) returned false "contradiction" pairs
because TF-IDF was matching this garbled boilerplate rather than rule meaning.
Investigating the noise revealed the systematic corruption.

**Scope (live DB, full `regulatory_provisions`, 53,716 rows, 2026-07-15):**
854 corrupted rows total (1.6% overall), concentrated by council:

| Council | Corrupted | Live (`is_current`) |
|---|---|---|
| city_of_sydney | 684 | 644 |
| ku_ring_gai | 98 | 14 |
| campbelltown | 37 | 37 |
| ashfield | 27 | 0 (not served) |
| northern_beaches | 3 | 3 |
| (NULL council) | 5 | 5 |

**Detection query (read-only; regenerates the full ID list any time):**
```sql
SELECT id, source_council, is_current, v2_is_actionable
FROM regulatory_provisions
WHERE provision_text ~ '([A-Za-z])\1([A-Za-z])\2([A-Za-z])\3'
ORDER BY source_council NULLS LAST, id;
```
Snapshot of all 854 IDs + snippets: `data/latent_scope/ocr_corruption_worklist.csv` (git-ignored, local).

**Root cause (suspected):** the PDF→text extraction step for these documents
(City of Sydney DCP 2012 in particular) doubled every glyph — likely a specific
extractor/font path, not a content problem. Needs confirming against the source
extractor before re-running.

**Impact / urgency (traced 2026-07-15):**
- **SERVED customer-facing: YES, but confined to the DCP provisions display panel.**
  City of Sydney is configured and reachable (`frontend-nextjs/lib/council-config.ts:191`,
  no disable gate). `app/api/provisions/for-property/route.ts` selects `provision_text`,
  filters `is_current = TRUE` and `document_id ILIKE '%Sydney_DCP%'` (route.ts:548,846,873),
  and `components/compliance/PageGroupedProvisions.tsx` renders it raw. So a CoS address
  lookup shows the 644 live doubled-character rows in the provisions list.
- **Existing sanitisation does NOT help:** `stripOcrHeaderPrefix` (route.ts:125) is a
  Marrickville-only page-header regex — a no-op for CoS; it does not touch doubled chars.
- **NOT affected:** capacity/constraint engine (reads `dcp_setback_controls`, where CoS is
  clean — 0/27 corrupted source_text, 0 controls linked to a corrupted provision),
  intelligence brief, and conveyancing (none read `regulatory_provisions`).
- **Net severity:** a user-facing *display* defect in the provisions panel, NOT a
  wrong-number / liability defect. Computed numbers and verdicts for CoS remain correct.
  Business open question: actual CoS lookup traffic (config is live, but CoS is not a
  beachhead council).

**Fix applied 2026-07-15 (production read+transform+write):**
- Stripped the doubled-glyph header lines from `provision_text` for **845 rows** via a
  guarded transactional UPDATE — per-id, `WHERE id=%s AND provision_text=<backup value>`
  (optimistic-concurrency guard), never blanking a row, `statement_timeout=30s`.
- Verified: City of Sydney sample (id 95298) now renders clean; detection count dropped
  854 → 57 still matching the pattern, of which **35 are legitimate doubled-letter words**
  (e.g. the suburb "Woolloomooloo") — false positives, no action.
- **Backup / rollback source:** `data/latent_scope/ocr_fix_backup.json` (all 854 pre-fix rows,
  `{id, council, before}`). To roll back, UPDATE each id back to its `before` value.

**Remaining — 22 rows need SOURCE re-extraction (NOT strip-fixable):**
Their body text is doubled *and* scrambled (e.g. `PPrirmimaarryy` = "Primary"), which is not
losslessly reversible. Split: city_of_sydney 7, ku_ring_gai 10, campbelltown 4, (null) 1.
Worklist: `data/latent_scope/reextraction_worklist.csv`. Regenerate any time with the
detection query above (then exclude legitimate doubled-letter words).

**Root cause identified 2026-07-15 (investigated for re-extraction):** the source PDFs carry a
DUPLICATED text layer. pymupdf on the local Campbelltown Part 3 PDF returns each line twice
("Each dwelling shall have a minimum of / Each dwelling shall have a minimum of"); the original
extractor concatenated the overlapping copies, producing the char-interleaved scramble. A clean
re-extraction must therefore: (a) DEDUPLICATE the doubled text layer during extraction,
(b) re-chunk by clause, (c) re-map pages (DB `pdf_page` does not align with the PDF page index —
DB page 21 pointed at a different clause than the PDF's page 21). This is a pipeline job, not an
in-place fix: the char-interleaved DB text is not losslessly reversible, and blind page-dumping
would merge clauses (unsafe for legal text). City of Sydney section-6 source PDF is not local
(only sections 3-4 are present in `data/dcps/`) → must be re-downloaded first. Deferred to the
enrichment pipeline; scrambled bodies are already reduced (headers stripped in the 2026-07-15 pass).

**UI exposure + mitigation 2026-07-15:** Of the 22, only 7 were customer-visible (provisions panel
filters `is_current AND v2_is_actionable`); the other 15 sit in the DB unused. None have a
`pdf_page_image_url`, so there is no figure image to fall back on — only the OCR'd text. The 2
genuinely-unreadable ones (ids 95802, 95807 — City of Sydney section-6 figure/site-plan pages,
e.g. Cahill Expressway / Herald Square public-domain plans, which appear only for those specific
sites) were set `v2_is_actionable=false` to remove the text-soup from display (backup:
`data/latent_scope/actionable_flag_backup.json`; reversible). They are figure legends — the
enforceable setback controls live in separate text provisions / `dcp_setback_controls`, so nothing
enforceable was hidden. The remaining 5 shown rows (4 Campbelltown, 1 Ku-ring-gai) are
readable-but-untidy and left in place pending re-extraction.

---

## Two-Table Architecture: Raw vs LLM-Curated

**IMPORTANT: Do not assume low LLM coverage means incomplete extraction.**

There are TWO provision data sources:

1. **`regulatory_provisions`** (raw) - PDF paragraphs with regex-classified `v2_topic`
   - Complete coverage (all PDF content)
   - Lower quality (includes headers, intro text, cross-references)
   - 43 unique topics

2. **`dcp_general_requirements`** (LLM-curated) - Extracted actionable requirements with `category`
   - Intentionally selective (only actionable development controls)
   - Higher quality (distilled requirements)
   - 64 unique categories

**LLM Extraction is SELECTIVE by design:**
- The LLM is instructed to "Extract ALL actionable development controls"
- This EXCLUDES: headers, objectives, definitions, explanatory context, cross-references
- A 20-30% extraction rate is NORMAL - most DCP text is not actionable

**Coverage by council (as of 2025-12-01):**
- Ashfield: 791 LLM / 1,579 raw = 50%
- Marrickville: 1,338 LLM / 985 raw = 136% (expansion from multi-requirement paragraphs)
- Leichhardt: 834 LLM / 2,989 raw = 28%

**Leichhardt's 28% is NOT incomplete** - Part C Section 1 alone has 1,782 raw provisions but only 342 extracted requirements (19%). This is correct - most Part C content is objectives and context, not controls.

**Current API usage:**
- Heritage (condition layer): Uses LLM-curated `dcp_general_requirements`
- All other queries: Uses raw `regulatory_provisions` with `v2_topic`

---

## Context Files to Read First

| Priority | File | Purpose |
|----------|------|---------|
| 1 | `.claude/prp/INDEX.md` | Architecture overview, implementation state |
| 2 | `PROVISION_BASED_ARCHITECTURE_STRATEGY.md` | Full 8-part strategy |
| 3 | `DEPLOYMENT.md` | How to sync local/Supabase |
| 4 | **THIS FILE** | Current quality issues and fix progress |
| 5 | `.claude/DQ11_HERITAGE_SUBCATEGORIZATION.md` | Heritage enrichment research & plan |

---

## Archive

Closed-issue post-mortems, the DQ-1..7 era details, the pre-single-DB fix workflow,
and the full Session Log live in `.claude/DATA_QUALITY_ARCHIVE.md` (moved verbatim
2026-08-06). The Quick Status table above remains the complete index of every issue,
open and closed. Nothing was deleted.
