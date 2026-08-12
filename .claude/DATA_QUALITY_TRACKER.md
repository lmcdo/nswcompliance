# Data Quality Tracker

**Purpose:** Track data quality issues systematically across Claude sessions.

**Last Updated:** 2026-08-12
**Session:** DQ-54 fixed (#930) and the ledger made executable — `.claude/dq_checks.json` + `scripts/dq_check.py` now enforce every status in BOTH directions, so a row cannot claim fixed while broken, nor sit open after it has quietly been fixed.

> **Statuses here are enforced, not asserted.** `python scripts/dq_check.py` runs each row's check and fails if a status disagrees with reality. 4 of 55 rows carry a real check today; the other 51 carry an explicit `check: null` plus a reason, and that gap is printed on every run rather than counted as coverage. Adding a row without an entry in `dq_checks.json` fails the coverage test.

---

## Quick Status

| Issue | Status | Priority |
|-------|--------|----------|
| DQ-57: **The SES lookup returns no council name for 80% of flood reports, so the flood three-state fix's council scoping is close to inert.** Measured on all 151 stored flood rows: 30 (20%) fall inside a council study extent and always carry `ses_study_lga`; **109 (72%) were queried, fall outside every extent, and carry NO council name — 100% of them**; 12 (8%) were never queried. `ses_study_lga` is not "which council is this address in", it is "which study matched" — a different question, and it is null precisely when no study matched, which is exactly the case where an absent study would matter. So #892's scoping (report an absent study only when it belongs to this address's council) fires almost only when the study was already consulted. **The measurement inverts the assumption in #892's residual note:** this was written as a rare edge case and it is the common one. The right signal already exists — `services/lga_lookup.py::lookup_lga(lat, lng, conn)` resolves LGA statewide from the `spatial_overlays` height layer by `ST_Contains`, and `flood_truth.py` already opens connections via `_get_conn()`. Flipping the default instead (treat unknown council as not-assessed) would mark ~80% of reports unassessed and destroy the signal, so the rate decides the policy: use the real lookup, do not pick a default. | 🔴 Open — measured 2026-08-08, not fixed. Shipping the Tweed/Wollongong rasters removes today's instance but NOT the structure; the next council with a missing study walks into the same hole. | P2 — correctness of a fix to a P1, not a live false claim |
| DQ-56: **233 tests may assert that an absence produces a NEGATIVE verdict rather than an unknown one — the class that hid the flood defect, and nobody had looked.** Distinct from DQ-53 (tests that CANNOT fail): these can fail and do run, they simply assert the wrong thing, so every gate was green while six of them guarded a false answer on the most consequential field in a property report — one named `test_epi_none_class_not_in_100yr`. Swept by `scripts/sweep_absence_negative_tests.py` (read-only, 200 Python + 81 TS/TSX test files): 55 tier-1 (served hazard verdict), 33 tier-2 (eligibility), 65 tier-3 (other served fields), 80 tier-4 (internal). **A candidate is not a defect** — `False` is right when a source was asked and said no, wrong only when it was never reached, and the two are indistinguishable from test text. Triage is cheap because good names announce themselves: `test_overlay_absent_is_false_only_when_layer_covered`, `test_heritage_lists_are_three_state` and `test_contaminated_failure_vs_genuinely_none_are_distinct` are all already correct, which is evidence #872/#873's typed-absence work landed. **The one confirmed live defect found: `frontend-nextjs/app/api/lot-search/route.ts:195-197` serves `heritage: r.heritage ?? false`, `flood_prone: … ?? false`, `bushfire_prone: … ?? false`** — a NULL overlay, meaning it was never resolved for that lot, is served as "not heritage, not flood prone, not bushfire prone" across three hazard flags at once. Pinned by `__tests__/api/lot-search.test.ts:297`, whose title states the defect as the intended behaviour: *"null heritage/flood/bushfire default to false in response"*. Consumed by `components/prospector/ProspectorClient.tsx` and `SummaryDashboard.tsx` — the Prospector surface, which memory records as shelved for lack of traffic, so the blast radius is small but the code is live. | 🟡 **CLOSED AS NOT WORTH CONTINUING — user ruling 2026-08-08.** One real defect in 233 candidates, on a feature with no traffic: this line of work stopped earning its keep. The lot-search defect is fixed separately. The remaining 232 are NOT adjudicated, the keyword tiering is NOT fixed, and neither should be reopened. Kept logged so the class is on the record and the sweep can be re-run if a served defect of this shape ever surfaces again — not as a backlog. | P2 — one confirmed live three-field defect on a low-traffic surface; the rest unadjudicated |
| DQ-55: **Three docs describe GitHub Actions workflows as current infrastructure; the workflows were deleted in #506 and only `gates.yml` and `main-red-alarm.yml` exist.** `docs/DCP_MONITORING.md:26-27` lists `.github/workflows/dcp-monitor.yml` and `dcp-extract.yml` in a table of live files ("GitHub Actions schedule + manual trigger"); `docs/DCP_UPDATE_GOVERNANCE.md:157` gives `dcp-extract.yml`, `dcp-commit.yml` and `dcp-watchdog.yml` a running cadence ("Daily 10:00 UTC"); `docs/QA-DATA-PROVENANCE.md:312` names `.github/workflows/satellite-freshness-monitor.yml` as the health-checks workflow. Anyone reading these believes scheduled extraction and a freshness monitor are running. Neither is. **`docs/DCP_PIPELINE_ARCHITECTURE_2026-06.md:22` flagged the governance doc as stale in JUNE and it was still stale in August** — a doc that documents its own decay is not a fix. **Correction to PR #890, which said "seven workflows":** 13 distinct filenames are named across 27 citations, but 9 of them are in `docs/RAILWAY_MONITORS.md`, a deliberate "what happened to each workflow" migration table, and are correct by design. Only these three docs carry false CURRENT-state claims. The same filename in a migration table and in a live-infrastructure table means opposite things, and `scripts/doc_claims.py` cannot tell them apart — a reader can. | ✅ **FIXED 2026-08-12.** All three docs corrected against `docs/RAILWAY_MONITORS.md`: the DCP monitor and watchdog run as **Railway crons weekly**, and the satellite freshness monitor is **weekly, not daily**. The important correction is not the names — **DCP extraction is MANUAL and nothing schedules it.** The old auto-trigger was deleted in #506 and never replaced, so a detected change sets `needs_extraction=TRUE` and then waits for a human. The docs claimed a chain that has not run for months. Pinned by `dq_probe_stale_workflow_docs.py`. | P2 — false infrastructure claim, no served-output impact |
| DQ-54: **Any hook-called script that shells out to git can be silently answering about the WRONG repository.** Git exports `GIT_DIR` and `GIT_INDEX_FILE` to its hooks and they OVERRIDE `cwd`. Measured, not assumed: in a **worktree** — this project's standard workflow — all four hooks receive an absolute `GIT_DIR`, and `pre-commit`/`commit-msg`/`post-commit` also receive an absolute `GIT_INDEX_FILE`; in a plain clone `pre-push` receives neither. Demonstrated live: with `GIT_DIR` pointed elsewhere, `git log`, `git rev-parse --git-common-dir` and `git ls-files` run from this worktree all answered about the other repository, exit 0, no warning. **This already caused damage on 2026-08-07:** during a `pre-push` run, `tests/test_doc_claims.py`'s fixture `git commit` landed on the real worktree's branch and replaced its index (recovered by SHA, nothing lost). Exposed today: `scripts/cross_review.py` (2 calls, `cwd=_REPO_ROOT`), `scripts/validate_schema_contract.py:408` (`--git-common-dir` used to locate the `.env` that supplies `DATABASE_URL` — wrong repo means wrong credentials), and `scripts/qa_gate.py:1385` (`git log` for the commit-hash binding, while the SAME FILE scrubs correctly at :393). Already neutralised: `scripts/qa_gate.py:393-400`, `scripts/doc_claims.py` (`git_env()`), `tests/test_doc_claims.py`. Not exposed by design: `lint_bracket_access.py`, `lint_hardcoded_zone_codes.py`, `liability_language_check.py`, `pr_overlap_guard.py` — they pass no `cwd` and genuinely want the hook's repo. | ✅ **Fixed 2026-08-12 — PR #930.** The prescription said "one shared `git_env()` helper at **three** call sites"; an AST ratchet found **nine**. The four the hand-written list missed were `prove_qa_report_binding.py`, `prune_qa_reports.py`, `sol_common.py` and `sweep_absence_negative_tests.py`, then tightening the ratchet to require `git_env()` specifically surfaced `measure_flood_zone_unassessed.py` and `run_flood_calibration_2022.py`. Three of the nine locate the `.env` supplying `DATABASE_URL` or an API key; one DELETES files. Pinned by `tests/test_git_env_ratchet.py` — first run 4 failed / 242 passed against unpatched code, now 246/246 — and by `dq_check.py`, so this row cannot silently rot back. **A second incident occurred between logging and fixing:** #927's push failed because pytest inherited the hook's `GIT_DIR`. Prose did not prevent it; the ratchet does. | P2 — silent wrong answer in gates; two live incidents, no production impact |
| DQ-53b: **PR #883's fifth falsifiability case never held, and nothing noticed.** Re-running #883's proofs through the hardened `scripts/falsifiability.py`: the four RED cases reproduce EXACTLY as claimed (daylight saving ignored → 3 failed, the 183.0 constant restored → 42, suncalc lat/lng swapped → 81, a 0.6° bearing drift → 41), on current main and at #883's own tree, restored byte-identically. **Those four claims survive.** The fifth — a 0.15° drift asserted to be INSIDE the 0.50° pass mark and therefore still passing — goes RED, and goes red at commit `a7edd825` itself, so it never passed. `services/solar_position.py` and `tests/test_shadow_calibration.py` are byte-identical to #883, so this is not drift. Cause: the served bearing is `round(x, 1)`, so quantisation pushes a 0.13–0.15° planted drift past the mark; measured real headroom is 0.10° (0.10 passes, 0.13 and 0.15 fail). Measured worst deviations on the fixture grid: altitude 0.2057° at sep21_12pm/NSW envelope SW, bearing 0.3185° at Tweed Heads, raw azimuth 0.3463° at sep21_12pm/NSW envelope NE (this last figure is the 0.346° in plan §4h — correct). The case was in the throwaway script only, never in #883's QA report, so **no report claim is falsified** — but the script's own output would have read `*** FALSE ALARM ***` and no one recorded it. **PR #885 makes no plant-restore claim at all** — its falsifiability is the repair-verification structure (dry run, md5 guards, independent census, re-run selects zero), so it is unaffected. | 🟢 Verified 2026-08-08. Calibration verdict UNCHANGED — the pass marks were never in question and the numbers were re-derived live against pvlib. Only the tolerance-floor sanity case was mis-sized. | P3 — proof hygiene, no served-output impact |
| DQ-53: **Contract tests that compare two stored artefacts instead of comparing against a live call — a check that cannot fail in the way its own name claims.** `test_climate_hazard_contract_matches_service_to_dict_keys` was commented "locks ClimateHazardOutput to the exact keys HazardScore.to_dict emits", but compared the Pydantic contract to a **stored golden fixture**. When `to_dict` gained `confidence_reason` (output-grounding, 2026-08-03) the contract and the fixture were both missing it — wrong in the same direction — so the comparison stayed green for weeks while neither side matched the service. The module docstring asserted the same thing in prose: captured fixtures "cannot be self-confirming: if a service renames a key, re-capture + these tests diverge." True for a RENAMED key; false for an ADDED one. Same shape as DQ-30's "0% drift" verification, which compared code to itself. **Scope is UNMEASURED:** one instance is fixed, but nobody has counted how many other contract/golden tests across the suite assert artefact-against-artefact. | 🟠 Logged 2026-08-07 — one instance fixed (now references a live `to_dict()`; falsifiability proven by planting 4 mismatches — extra serialised key, re-serialised composite field, contract-only field, stale fixture — all red, all restored byte-identically) and the docstring corrected. **Suite-wide census NOT done.** Fix = enumerate every test asserting a contract against a fixture and re-anchor each on a live call wherever the service runs on the dev box. | P2 — serves no wrong data; it is a gate that silently does not gate |
| DQ-52: **The shadow landing page SOLD "Surface-change screening detail" as a paid-tier feature (`free: false, paid: true`) for a check that has never once returned a reading in 538 attempts.** `landing/data/shadow.ts:57`, beside a $29/$39 price. The detector is 0/538 across the whole stored corpus (231 insufficient-scenes, 10 timeouts, 5 errors, 292 legacy zeros) while all 538 reports rendered a confident negative about neighbouring land. **This is a category beyond DQ-47 (pvlib):** that was a false claim about METHOD with no price attached; this is a commercial representation about WHAT A BUYER RECEIVES, on the paywall comparison table — conduct in trade, not just an inaccurate methodology note. Four further surfaces advertised the same capability: the feature card (`shadow.ts:43-44`), the data-source chip (`:20`), the methodology prose (`:61`) and the public methodology page (`app/how-it-works/page.tsx:72`, "Spectral change detection to identify recent construction near the property"). | 🟢 Logged then removed 2026-08-07 (§4h removal, user ruling) — all five representations deleted; the check itself removed from every render surface; `services/sentinel2.py` deleted (zero remaining consumers). Logged BEFORE removal so the record shows it was found and why it mattered. | P1 — paid-feature misrepresentation |
| DQ-47: **pvlib named as our shadow method on the PDF, the marketing page, the seeded disclaimer and 381 audit-trail rows — while never imported anywhere in the repo.** `git grep -nE "^\s*(import\|from)\s+pvlib"` returns nothing on origin/main 0c41c09d; the only shadow library the code imports is pybdshadow (`shadow_model.py:92`), which derives sun position itself. The disclaimer additionally credited it as "NREL-backed, peer-reviewed". Related: the served `shadow_direction_deg` is a stored per-scenario constant, not a per-report calculation, and nothing said so. | ✅ Fixed 2026-08-06 (Lane 1 / D1) — PDF, marketing, audit-trail source string, docstrings and internal docs now describe pybdshadow only; `migrations/064` seeds `shadow-v2` and supersedes v1. `requirements.txt:197` still pins the unused package — flagged, not removed. | P1 (was) — false method claim on served output |
| DQ-48: **A named SAR flood threshold and endpoint sat in `flood_truth.py` with zero call sites**, reading as a shipped detector: `FLOOD_RATIO = 1.25`, `PC_CATALOG`, `S1_COLLECTION`. No pystac/planetary-computer import; the live path nulls every `sar_*` field and the manifest records `sentinel1_sar.queried: false`. | ✅ Fixed 2026-08-06 (Lane 1 / D2) — all three deleted; grep-confirmed zero references; no served output changes. `services/CLAUDE.md` flood section marked NOT BUILT. | P2 (was) — ambiguity about a capability we do not have |
| DQ-49: **Granny-flat reports served "you confirmed N structures — counts agree" and a "high" confidence for a count the user could not change.** `onCountChange` was passed to `ConfirmationPanel` and never invoked, so `confirmed_structure_count` could only echo the detector. Measured on production: 16 rows carry both counts, 13 "agree" — **0 of 16 carry human input**; both apparent disagreements are the frontend's `: 1` fallback when detection found nothing. 8 of 16 rows are "high" on that basis. Also: the 4-option per-structure answers never left the browser, `detect_id` was accepted and never stored, and the confirm write (`ON CONFLICT DO UPDATE`) deleted the detect row's `detected_structures` — 0 of 87 rows hold a structure and a judgement about it together. | ✅ Fixed 2026-08-06 (Lane 1, items 3+4) — structural provenance field `inputs.confirmed_count_source` (`secondary_detections_classified`/`machine_default`/`unrecorded`, absent ≠ human); `inputs.structure_types` persists per-structure answers bound to `detected_structures[].index`; `inputs.detect_id` stored; `detected_structures` carried through the confirm write; count control wired on both surfaces; "high" now requires `secondary_detections_classified`. 10 old-doctrine tests flipped with reasons. | P1 (was) — served claim of human validation that never occurred |
| DQ-51: **`confirmed_structure_count` drove the SEPP cl 53(1) multi-structure eligibility gate and was caller-supplied** — a request submitting a count lower than the detect run found slipped under the `>= 3` block. Pre-existing; nothing validated the count before. | ✅ Fixed 2026-08-06 (Lane 1, Sol round 11) — the detect row is now read on the SEPP-standards connection BEFORE the eligibility gate, and `_effective_structure_count` derives the gate's count from the detected structures less those answered part_of_main/rejected. The submitted figure is used only when there is nothing better, is kept beside it as `confirmed_structure_count_submitted`, and a divergence is served as a warning. An `existing_gf` answer also now outranks a contradicting `existing_secondary_dwelling=false`. | P2 (was) |
| DQ-50: **143 cached flood rows still carry "Microsoft Planetary Computer S1 RTC" in their stored `data_sources`** (131 inside the 90-day cache window, newest 2026-08-03), and the cache path serves `cached["data_sources"]` verbatim — so DQ-44's fix stops NEW rows naming the unqueried source but old rows keep serving it on a cache hit. Separately `_DATA_SOURCES_BASE` (`flood_truth.py:133`, used at `:1819`) still hardcodes that source as the empty-list fallback; 0 rows can currently reach it. | ✅ **FIXED 2026-08-12 — 143 → 0.** `array_remove` of the single false literal across 143 flood reports (121 of them inside the 90-day cache window). Backup: `property_reports_dq50_backup_20260812`. Repaired inside a transaction with checks BEFORE commit — the first attempt ROLLED BACK because a guard counted 22 source-less reports; they proved pre-existing `solar-yield` rows, **0 of them among the 143**, so the guard was re-scoped to 'no row I TOUCHED ends up empty' rather than loosened. Verified after commit by `dq_probe_live.py --id DQ-50` → 0, and the ratchet went RED on the stale 'open' status until this row was updated. ⚠ **Separate finding, NOT fixed:** those 22 `solar-yield` reports carry NO data sources at all. | P1 — live false source claim on cache-hit reports |
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
| DQ-32: Capacity engine can return a different zone's setback/landscaping number. **Re-measured 2026-08-12: 562 rows across 171 groups.** ⚠ The 560/168 recorded on 2026-07-31 carries **no query**, so the two figures are not comparable and NO trend may be read from them — the earlier "it GREW" claim was unsupported and is retracted. The table gained exactly **2 rows in August** (ryde 1175, burwood 1176) and *neither* sits in an ambiguity group. ⚠ **'not started' was wrong**: a zone filter DOES exist at `scripts/conveyancing_db.py:413`, reached from `app/api/capacity/calculate/route.ts:121`. But it is gated on `applicability='zone_specific'`, which is **24 rows** — so it disambiguates about **4% of the 562**. The dominant gap was **76 rows whose `condition` names a zone while carrying a different `applicability`**, which the filter never examined — tracked as DQ-32b and **repaired 2026-08-12 (59 tagged, 17 adjudicated non-defects)**. Note this does NOT reduce the 562: the DQ-32 probe counts value disagreement and ignores `applicability` entirely, so it cannot see that 40 of those rows are now zone-resolvable. Two further weaknesses found by reading the code are **latent, not live, and must not be overstated**: the filter's hardcoded zone list omits R6/E2–E4/RU*/IN*/SP*/W*/B3–B8 (**0 rows** affected today) and its substring test cannot handle negation (**0 rows**). Both probes are wired into `dq_check.py`. | 🔴 Open — measured, not repaired. Changing what the capacity engine returns is a served-number change and awaits an explicit ruling. | P1 |
| DQ-32b: **76 served controls named a zone in their `condition` text while carrying a non-`zone_specific` `applicability`**, so the zone filter at `scripts/conveyancing_db.py:413` — gated on that field — never examined them. **Repaired 2026-08-12: 59 tagged `zone_specific`** (backup `dcp_setback_controls_dq32b_backup_20260812`). ⚠ **The other 17 must NOT be tagged, and finding that out was the whole job**: the filter is *skip-only*, so a wrong tag can only ever DELETE a correct control. 8 canada_bay rows read `within 800m station or 400m B3/B4` — **proximity to a zone, not membership in one**; 7 are clause/table references the regex mistook for zone codes (`(C1.1.9(e))`, `Table C2.2`, `(B3.8 s3.8.2 C1)`); 1 is a road classification (`major road frontage (C1)`); 1 carries an explicit fallback (`otherwise prevailing`) that tagging would drop outside R3; 1 uses the zone for a **sub-case only**, so the general 60% would be lost outside E4. They are excluded **by id**, not by loosening the regex, so a NEW untagged zone-naming row still fails the check. Verified against served output: Penrith `dwelling_house` landscaping went from 4 values in every zone to **R2→50% only, R4→35% only**. | ✅ **Fixed 2026-08-12 — 76 → 0.** | P1 |
| DQ-31: housing-sepp/eligibility over-eligibility — absent `isLMRArea` meant "yes"; the AI router additionally hardcoded `isLMRArea: true` and invented `zone`/`lotSize`/`lotWidth`. **Over-eligibility CLOSED 2026-08-01; full consolidation onto the Python service still open.** | 🟠 Wrong answer fixed, consolidation open | P1 |
| DQ-30: Applicability tagger — CODE fixed (PR1-4, this PR). **DATA NOT fixed: 286 rows still carry retired zone codes, 14 of them live+actionable in councils the retag covered.** The "0% drift" verification was invalid — it cannot fail. | ✅ **Data FIXED 2026-08-12 — 3 served rows → 0.** Lossless by construction: every one already carried the modern equivalent (E1/E2/MU1) beside the retired B-code, and nothing is zoned B1–B8 any more, so the removed entries could never match a current-zone lookup. Backup `regulatory_provisions_dq30_backup_20260812` (86 rows incl. superseded). **86 superseded rows still carry retired codes and were deliberately NOT touched — they are history, not served.** | P1 — validity, not traffic |
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

## DQ-34: PDF "Housing SEPP 2021: ✓ Applies" line is an ungated definitive claim

**Status:** 🔍 Logged 2026-08-01, not sized — found via a Sol cross-review of the DQ-30 branch,
verified against the code, deliberately not fixed here (out of scope for a zone-taxonomy
consolidation PR).
**Found:** 2026-08-01

**Problem:** `frontend-nextjs/components/pdf/ContextSection.tsx` has two separate pieces of
Housing SEPP eligibility logic in the same file. `determineDevelopmentPathway()` (used for the
main pathway determination) correctly checks `heritage_status` first and returns a hedged reason
("CDC pathway available for eligible development"). But a second, separate JSX block rendering
the "Housing SEPP 2021" table row (around line 304) only checks `HOUSING_SEPP_ZONES.includes(zoneCode)`
and prints an unconditional "✓ Applies — `<zone>` zone eligible for complying development (CDC)
pathway" with no heritage, dev-type, or lot-size gating at all.

**Confirmed pre-existing:** verified via `git diff main` that this PR only swapped the inline
zone-code literal for the shared `HOUSING_SEPP_ZONES` constant at this exact line — the
surrounding "✓ Applies" conditional and copy are unchanged, pre-dating DQ-30. Not introduced or
worsened by the zone-taxonomy consolidation.

**Risk:** a heritage-listed or otherwise CDC-ineligible property zoned E1/MU1 would show
"✓ Applies" in the generated PDF, which reads as a definitive eligibility claim despite zone
membership alone not establishing CDC eligibility — the class of issue
`.claude/rules/pre-pr-review.md`'s liability-language check exists to catch.

**Fix:** not started, not sized. Needs deciding whether to gate this specific display block on
the same heritage check `determineDevelopmentPathway()` already does, or reuse
`determineDevelopmentPathway()`'s result directly instead of re-deriving eligibility inline a
second time in the same file.

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

## DQ-39: 25 control values their own quote does not support (2026-08-02)

**Status:** MEASURED + GATED for all 1,069 rows. Data NOT fixed — each row needs a
ruling against the source PDF, which is extraction work.

**What changed the coverage.** DQ-38 established that only 42 controls can be
checked against the provisions corpus, because 14 of 30 councils have no provisions
ingested. But every row already carries `source_text` — the sentence its number was
taken from. Checking a number against **its own quote** needs no corpus, no PDF and
no ingestion, so it covers **all 1,069 instead of 42.** That is a 25× increase in
what is machine-checkable, achieved by changing the question rather than the data.

**The flag was not the answer.** `value_absent_from_source` flags rows whose digits
do not appear in their quote. Re-measured live: **137 on `value_min`, 11 on
`value_max`, 142 distinct rows** (the remembered "137 table-wide" was `value_min`
only). Reading a sample showed most were legitimate derivations — "900mm" stored as
0.9, "one space per 3 dwellings" stored as 0.333. **A list of flags where most
entries are fine is a list people stop reading**, and that is how a real mismatch
survives inside it.

So each derivation is now a NAMED rule that must produce the substring it matched.
Every row lands in exactly one state (`scripts/validate_control_source_values.py`):

| state | rows | |
|---|---|---|
| `exact_digit_match` | 839 | the number is literally in the quote |
| `ratio_or_rate` | 88 | "1 space per 4 dwellings" → 0.25 |
| `unit_conversion` | 19 | "900mm" → 0.9 m |
| `area_from_dimensions` | 5 | "3m x 3m" → 9 |
| `written_numeral` | 4 | "one car space" → 1 |
| `fraction_literal` | 2 | "min 1/3" → 0.333 |
| `implied_single_unit_rate` | 2 | "a space for every 4 dwellings" → 0.25 |
| `explicit_nil_requirement` | 1 | "no additional parking is required" → 0 |
| `built_to_boundary_zero` | 1 | "may be built to the rear boundary" → 0 |
| `percentage_phrasing` | 0 | reachable, but every real row hits the exact rule first |
| **`UNEXPLAINED`** | **25** | **the finding** |
| `no_value_stored` | 83 | a rule with no number — counted separately, NOT a pass |

**961 of the 986 rows carrying a number (97.5%) are derivable from their own quote.**

### The 25, grouped by what is actually wrong

> **ADJUDICATED 2026-08-03 against source PDFs — group A below was WRONG.**
> Full evidence: `docs/qa/controls-adjudication-2026-08.md`. Verdicts on all 25:
> **12 CORRECT, 8 EXTRACTION_ERROR, 3 NO_NUMERIC_CONTROL_IN_SOURCE, 2 UNVERIFIABLE.**
> Every one of the 11 rows whose source had to be fetched proved CORRECT.

**A. RETRACTED — the four Waverley rows are CORRECT.**
Waverley `deep_soil_min` 631/632 (10%) and 635/636 (15%) are right. The control is
a **two-clause derivation** and `source_text` stored only the second clause:
C1.9(c) *"minimum of **20%** of the total site area … as landscaped area"* ×
C1.9(d) *"minimum **50%** of the landscaped area must be deep soil"* = **10% of
site**; C2.9(b) **30%** × C2.9(c) **50%** = **15%**. Verified verbatim at pages 204
and 233 of WDCP 2022 (v1.1-2026-03-16). Calling these the most serious finding was
an assertion from a partial quote — the same error this workstream keeps repeating.

Of the Cumberland three, only two are errors, and **30 is CORRECT**: Table 1 p.B8
reads *"Rear Setback — Minimum 8m"*. It was flagged because all four Cumberland
rows share a `source_text` truncated at exactly **400 characters**, severing the
rear/corner/secondary rows of the table. **31** (4.0 m) is the *Secondary Frontage*
setback and **32** (5.5 m) is the *garage* setback, both stored as `front_setback`;
both are already `is_current=FALSE`.

**B. The quote is an admission that the value is unverified — 2 rows.**
- **1119** Cumberland POS stores 24 m² with `source_text` = *"...(needs PDF
  verification for numeric values)"*; **1120** Campbelltown POS stores 24 m² with
  *"(needs PDF verification — garbled extraction)"*. Note `fabricated_values`
  should catch this shape and does not: its marker pattern has "to be verified"
  but not "needs PDF verification".

**C. The quote is about a different control — 2 rows.**
- **693** Camden `front_setback` 2.0 m quoted from a clause about **front fence
  height** (1.2 m). This row also exposed the check's own worst false-pass: it
  was briefly "explained" by the `2` of a numbered list item, until numbered-list
  ordinals were excluded from quantity matching.
- **255** Campbelltown `car_parking` 2 spaces quoted from a clause about a
  **36 m² undercover parking area**.

**D. The quote is qualitative and the number is an assumption — 11 rows.**
690, 692 (Camden — "average setback of the 2 nearest dwelling houses"), 3
(Ku-ring-gai objectives text), 883, 884, 885 (City of Sydney — "consistent with the
Building setbacks map", heritage character), 606 (Sutherland — "determined by either
a specified minimum distance or the average"), 13 (Woollahra — envelope defined by a
Figure), 1, 2, 6 (Marrickville — garbled OCR objectives text with no numbers in it;
DQ-29 territory).

**E. A correct value whose derivation is deliberately not machine-named — 3 rows.**
- **229** Georges River: *"1 garage space and 1 driveway space per dwelling"* → 2.
  Plainly right, but a rule that summed arbitrary numbers from a quote could
  "explain" almost any value, so it stays a finding rather than getting a rule.
- **778** Ryde: *"Up to 2 spaces per dwelling house"* → max 2 is quoted, **min 1 is
  not**. **517** Marrickville stores 0 against *"1 per principal dwelling and
  secondary dwelling combined"* and belongs in group A on a re-read.

### How strong is an exact match, really?
**571 of the 839 exact matches (68.1%) sit in a quote that holds more than one
distinct quantity.** The stored value appears in its source — but so do others, so
the match is *consistent*, not *pinned*. Only 268 are uniquely attributable. That
split is now printed, because `exact_digit_match` otherwise reads as stronger
evidence than a number-matching check can give. Closing it properly means reading
clauses rather than matching numbers, which is a different tool.

Five further holes found in adversarial review and closed:
- a value stored with **no source_text at all** returned `no_value_stored` and
  passed as "nothing to check". It is now `MISSING_SOURCE_TEXT`, a failing state.
  0 rows are in it today — which is exactly why it needed one.
- the gate blocked on superseded rows. Only `is_current` rows can fail now (19 of
  the 25); the 6 superseded are reported, never silently dropped. The test is
  `is False`, not falsy, so a future nullable column fails closed.
- **the rounding tolerance was wrong in both directions.** A flat 0.005 let a
  stored 0.005 pass against a quoted "1 space per 1000 dwellings" (0.001) — five
  times too large. Tightening it to 0.0005 then rejected two honest rows, because
  the table stores 2/3 as **0.67** and 1/3 as both **0.33** and **0.333**. The
  tolerance now comes from the stored value's own precision (half its last decimal
  place) AND a 5% relative bound, so a whole number cannot absorb a large gap.
- `area_from_dimensions` ignored the unit, so "3m x 3m" could explain a 9 in a
  `spaces/dwelling` column. Now gated on an area unit.
- `written_numeral` matched "one" anywhere, so *"Objective one: provide a minimum
  6m front setback"* explained a stored 1 m setback. The numeral must now be
  counting something within two words.
- the rate rule offered **every** number before a "per" as a numerator, so
  *"Minimum setback 6m and provide 1 space per 4 dwellings"* could explain a
  stored 1.5 as 6/4 — a rate assembled from two unrelated clauses. Only the
  nearest number can be a numerator now.
- `percentage_phrasing` also accepted `pct * 100`, so a quoted 35% explained a
  stored 3500. Nobody stores a percentage that way; that direction existed only to
  manufacture matches, and is gone.
- **the baseline was never made to shrink.** A repaired row stayed accepted
  forever, so restoring its old value later would not have failed. A baseline
  entry that is now explained is a **failure** with the one command to fix it —
  and `--write-baseline` refuses to ADD ids without `--allow-growth`, so the
  remedy cannot double as the bypass.
- **the baseline was keyed on `id` alone**, so a baselined control could have its
  value swapped for a *different* unsupported number, or lose its quote entirely,
  and stay accepted. It now stores `id -> digest(value_min, value_max, unit,
  source_text)`, so any change to what the check reads makes the row new again.
- `unit_conversion` accepted both directions, so a quoted "0.9mm" explained a
  stored 900 m. One direction only now.
- a matched quantity whose text says it measures something else explained a value
  anyway — *"a minimum of 3 hours of sunlight"* explained a **3 metre** setback.
  A trailing unit in a different family (length / area / ratio / time / count /
  rate) now disqualifies the match, and only when BOTH sides are known, so an
  unlabelled number is never rejected on a guess.
- **the unit guard existed in one rule and its stored-unit map covered 6 strings.**
  `spaces/dwelling` and its eight siblings — **450+ rows, the largest unit group in
  the table** — fell outside it, so those rows were treated as "unknown unit" and
  the guard never fired for them. The map now resolves by prefix (`%…` → ratio,
  `spaces/…` → rate), and the guard is applied in `written_numeral` too, not only
  in exact matching. `percentage_phrasing` is gated on a ratio column (a quoted
  35% was explaining a 0.35 **metre** setback) and `unit_conversion` on a length
  column (it also accepted `m2` and unlabelled columns).
- the lead-in to a rate was cut on any `.`, **which split decimals**:
  *"0.5 spaces per 4 dwellings"* left `5 spaces` and produced 5/4, so a stored
  1.25 passed against a quote stating 0.125. The cut now ignores a full stop
  between two digits.

- a **whole-number** stored value got half-a-unit of slack, so *"24 spaces per 25
  dwellings"* (0.96) explained a stored **1**. Rounding a rate to a whole number is
  a judgement, not a derivation the text states; whole numbers must now match
  exactly. All five whole-number derived rows are exact products, so this cost
  nothing.
- the rate rules had **no column gate**, so *"1 visitor space per 4 dwellings"*
  could explain a stored 0.25 **metre** setback on a row whose `source_text` was
  attached to the wrong control. Refused on length, area and time columns.
- a **NaN** stored value read as explained. Postgres `numeric` accepts NaN and
  every comparison against it is False, so the exact rule's own "skip if not
  equal" test was False and the row fell through into a match. NaN and infinity
  are now findings.

- a clause label with a **space** was still a quantity: the number-token guard
  only caught a label glued on (`s4.3.6`), so *"Clause 4.3: minimum setback is
  6m"* explained a stored **4.3** — the citation vouching for the value it is
  supposed to be evidence against. Clause/Part/Table/Control/Figure/Objective and
  eleven more labels are now excluded.
- `written_numeral`'s unit guard read the position straight after the numeral, so
  *"three **full** hours"* put a word where the unit scan looked and the conflict
  went undetected. It now reads the noun the rule itself matched.
- `implied_single_unit_rate` invented its numerator: *"Visitor parking must be
  considered for every 4 dwellings"* became 1/4 although the quote states no
  quantity. The implied "one" must now be written as something ("**a** parking
  **space** for every 4 dwellings").
- `fraction_literal` had no column gate, so *"At least 1/3 of the landscaped
  area"* could explain a stored 0.333 **metre** setback. Same gate as the rates.
- a row whose value is **NULLed by a migration** moved into `no_value_stored` and
  passed as "nothing to check". The check cannot tell an intentional blank from a
  lost one, so the count is now ratcheted in the baseline (83) and a rise fails.

None of these eighteen changed the finding count — it stayed at 25 throughout —
which is the point: they closed paths by which a *future* wrong value would have
passed, not paths that were hiding current ones. Two were measured against live
data before being applied, to confirm they cost no legitimate row: whole-number
exactness affects 5 rows and all 5 are exact products, and the rate column gate
affects 0 of the 90 rate-explained rows.

**Where the hardening stopped, and why.** Seven rounds of adversarial review each
returned real findings, and the count of *data* findings did not move after the
first. That is the signal to stop: the remaining suggestions harden a check that
no longer changes its answer. One was declined outright — failing every exact
match that sits in a multi-quantity quote would put 571 of 839 rows in the finding
list, which is a re-statement of the method's ceiling rather than a defect list.
Closing that genuinely means reading clauses instead of matching numbers.

### Why this check can fail
Two ways: a NEW unexplained row fails against the baseline, and a value edited to
something its quote does not support becomes unexplained on the next run.
**Demonstrated firing** — three ids removed from the baseline produced
`NEW (not in the baseline): 3` and exit 1. The baseline is shrink-only.

Mutation-checked, because a rule that always explained would make this a check that
cannot fail: forcing the tolerance to always match, replacing exact matching with a
substring test, and letting the implied-rate rule ignore a written numerator were
all **killed by the tests**.

### What it does NOT prove
That the number is correct — only that it is consistent with the sentence stored
beside it. If the quote itself was mis-transcribed, both agree and this passes.
That failure mode belongs to the extraction gates.

### Named false-explanation traps the rules refuse
- a numbered-list ordinal explaining a value (this one was live: it hid Camden 693)
- a clause reference explaining a value (`s4.3.6` must not explain a stored 4.3)
- a bare number read as millimetres, or divided by 100 to reach a percentage
- `2 spaces per 5 dwellings` stored as 0.2 being "explained" as 1/5
- City of Sydney's *"where no front setback is shown on the map"* explaining a
  stored 0 — the map being silent is not a control of zero

Two of those were not hypothetical. Excluding clause references cost 5 rows their
explanation and excluding list ordinals cost 1 more — six rows that had been
reading as verified on the strength of a citation or a bullet number.

**Wired:** pre-push `[1f/5]` and CI (`gates.yml`, schema-contract job — the one with
live DB access). Exit 2 on no `DATABASE_URL` is a skip, never a pass.

---

## DQ-38: only 42 of 1,069 controls can be machine-checked against the corpus (2026-08-02)

**Status:** 42 links live. Ceiling reported, not chased. **Heading and cause corrected
2026-08-02** — the original title asserted a single cause ("the corpus lacks their
chapters") that is measurably false for most of the affected rows. See *Why the other
545 do not match* below.

**What it is.** DQ-37 left 535 controls in state `traceable` — a human can re-check
them against a clause reference. Linking each to `regulatory_provisions.provision_id`
would make that a machine's job. Measured across all 1,069 controls:

| outcome | rows |
|---|---|
| exactly one CURRENT provision contains the control's quote | **41** |
| multiple provisions match (ambiguous) | 2 |
| no provision contains the quote | 545 |
| **council has NO provisions in the corpus at all** | **450** |
| quote under 30 chars, not distinctive | 31 |

**Restricting candidates to current, actionable provisions IMPROVED the result.**
It removes superseded duplicates of the same clause, so ambiguity fell 23 -> 2 and
linkable rose 35 -> 41. Filtering for correctness made the numbers better, not
worse. It also caught a live defect: the first run had written **3 links to a
superseded Marrickville provision** (controls 1, 2, 6 -> provision 102098,
`is_current=False`). Those are now cleared to NULL — pointing a future automated
check at withdrawn text is worse than admitting there is no link.

**The finding is the ceiling, not the 41.** 14 of 30 control LGAs have zero
provisions ingested — Canterbury-Bankstown (68 controls), Canada Bay (40), Bayside
(38), Fairfield (33), Wingecarribee (32), Sutherland Shire (32), Randwick (28),
Liverpool (27), Burwood (27), Strathfield (25), The Hills (23), Ryde (23), Camden
(23), plus `nsw_statewide` (31). **That 450 figure was measured directly and stands.**

### Why the other 545 do not match — CORRECTED, and still partly unknown

The first version of this entry said those 545 "belong to councils that ARE in the
corpus but whose specific chapter was never ingested." **That is false for most of
them**, and it was asserted rather than measured. Marrickville has 8,413 provisions
loaded, Ashfield 7,429, Woollahra 6,546; the chapters are there and the quotes still
do not match. Measured 2026-08-02 by `scripts/measure_control_quote_gap.py`:

| test | result |
|---|---|
| a provision document exists for the control's own `source_chapter_key` | **339 / 545 (62.2%)** |
| no ingested document for that chapter — original explanation holds | 206 / 545 (37.8%) |
| quote IS in the corpus, but only on a provision excluded by `is_current`/`v2_is_actionable` | 15 |

Of those 545, **498 are `is_current` and 47 are superseded control versions.** The
population is deliberately unfiltered so it reconciles with the linker, which also
reads all 1,069 — but note the linker links superseded controls too, which is
harmless and worth knowing.

Independently, by longest contiguous shared word-run against the best provision in
that council (a set-overlap score was tried first and discarded — a long provision
contains all the words of a short quote by chance, so it proved nothing):

| how much of the quote appears verbatim | rows |
|---|---|
| ≥80% — the sentence IS there; substring match failed on punctuation/OCR alone | 57 (10.5%) |
| 40–80% — partly verbatim | 119 (21.8%) |
| 20–40% — fragmentary | 236 (43.3%) |
| <20% — not present in any recognisable form | 133 (24.4%) |

**The cause is mixed, and for the majority it is UNKNOWN.** What is established:
"chapter not ingested" is disproven for 62% of these rows, and the 57 verbatim rows
prove both the chapter and the sentence are present — those fail on normalisation,
not coverage. What is NOT established: the low-overlap bands are equally consistent
with "someone summarised the clause in their own words" and with "that sentence is
absent from the ingested text", and this measurement cannot tell them apart. One
weak supporting signal for the paraphrase hypothesis: **61 of 545 (11.2%) source_texts
OPEN with a document citation** ("Ashfield DCP 2016 A-Part8 Table 2: ..."), which is
editorial framing a sentence inside a PDF would not contain. That is 11%, not a
cause for the other 89%. **Do not write a cause into this entry without measuring it.**

Two named limits of the chapter test, so its 62.2% is not over-read: it compares
identifier token-sets (`chapter-f-dev-category` vs
`Inner_West_Ashfield_DCP_2016__chapter_f_dev_category`) after stripping council/year
noise, so a chapter whose key diverges by more than separators reads as "not ingested"
when it is present, and two chapters sharing a token-set could read as ingested when
the wrong one is. `section_ref` was tried as the test first and abandoned: **0 of 530**
control `section_ref` values exist as a `ref_number` in their council, because the two
columns use unrelated vocabularies ('chapter-f-dev-category/DS5.2' vs a clause number)
— that 0 measures the vocabulary gap, not the corpus.

Closing the 206-row coverage half is extraction work, out of scope per
`docs/EXTRACTION_WHY_IT_RECURS_AND_THE_DURABLE_FIX_2026-07.md`. The 57 verbatim rows
are a normalisation fix and are worth doing. The rest needs a cause before it needs a fix.

**Why only exact single matches were written.** A wrong link is worse than no link:
it would let a later check compare a number against someone else's clause and report
a confident false verdict. Matching is substring containment on normalised text — no
similarity score, so no threshold to tune wrong. The 2 ambiguous and 545 unmatched
stay NULL.

**Caught during the dry run:** the plan would have OVERWRITTEN the one pre-existing
human-made link (control 3 -> provision 98149; the matcher resolves it to 97850).
The same clause exists as more than one provision row, so "exactly one substring
match" can legitimately land on a different duplicate than a person chose. Neither
is provably right, so `PRESERVE_EXISTING_LINKS` keeps the human's link and the
disagreement is counted. The UPDATE also carries `AND provision_id IS NULL` so a
stale plan cannot clobber a link written since.

**Two safety defects found in my own script before the final write:**
1. Staleness was only handled inside the `linkable` branch, so a stale link on a row
   that no longer matched anything current was silently RETAINED. All 3 live rows
   were in exactly that state. Staleness is now tested before the outcome branch.
2. `CREATE TABLE IF NOT EXISTS` reused the previous run's backup table, and the
   `count >= plan` check passed spuriously (34 >= 13) while covering none of the rows
   about to change. The guard now asserts every planned id is present in the backup,
   and it was demonstrated firing: "10 planned rows missing", abort before any UPDATE.

**Falsifiable check:** `python scripts/link_controls_to_provisions.py` (dry-run
default). Predicted before the final write: 13 rows written (10 new + 3 cleared),
0 skipped, 42 linked after. All matched. Post-write verification, **re-run against the
live DB 2026-08-02**: 42 links, 0 dangling (FK), 0 pointing at a superseded or
non-actionable provision, controls 1/2/6 confirmed NULL, and **41 of 42 quotes verified
present inside the linked provision text** — the one exception being control 3, whose
link a different method made. Note an earlier verification query reported 14/35 because
it compared un-normalised SQL text; re-run with the matcher's own normalisation it
passes. The check was wrong, not the links.

**Rollback:** `dcp_setback_controls_provlink_backup_20260802b` (13 rows, holding the
pre-run provision_id and is_current for every changed row), SQL printed by the
script. The earlier `...20260802` table (34 rows) restores the pre-any-change state.

**Re-runnable by design.** As councils are ingested, re-running links more rows with
no code change. `scripts/validate_controls_provenance.py` now reports link coverage
so the number is visible over time.

**Advisory, not a gate:** requiring a link would fail on absent corpus rather than
on a defect, so link coverage never affects an exit code.

---

## DQ-37: `extraction_method` is not a provenance signal (measured 2026-08-02, no data change)

**Status:** MEASURED + GATED. No production write — the states are derived, not stored.

**What it is.** `dcp_setback_controls.extraction_method` was being read as if it
recorded how a row was produced. It does not. Measured against the repo:

| claimed method | a committed script regenerates it | it does not |
|---|---|---|
| `text_extraction` | 187 | **253** |
| `mistral_ocr` | 170 | **77** |
| `manual` | **145** | 205 |
| `manual_curation` | **32** | 0 |

So 330 rows labelled pipeline-extracted have no committed literal, and 177 rows
labelled hand-made are regenerable from a tracked script. The label and the
reality are close to uncorrelated.

**Why it drifted.** `scripts/insert_inner_west_landscaping.py` stamps
`extraction_method: "text_extraction"` onto hand-typed dict literals, and
`scripts/update_needs_review_controls.py:226` overwrites the column outright.
Neither is wrong locally; together they make the column a claim rather than a fact.

**Consequence for the retrospective.** `ce-reliability-retrospective-and-asset-inventory-2026-08.md`
§5.5 read "382 of 1,069 (36%) unreproducible" off this column. Measured against the
repo the split is **534 reproducible / 535 not** — half the table, not 36%. The
number was worse than reported, and it was worse because the measurement trusted a
self-reported field. Same shape as DQ-30's "0% drift": a check that compared code
to itself.

**What was NOT concluded.** Absence of a committed literal does not prove a row is
unreproducible — a genuine PDF-extraction pipeline holds no hardcoded text. Proving
those 330 would mean re-running extraction over council PDFs, which
`docs/EXTRACTION_WHY_IT_RECURS_AND_THE_DURABLE_FIX_2026-07.md` exists to stop. So
the mismatch is reported as advisory and never as a failure.

**The three states, all derived from existing columns:**
`reproducible` 534 (verbatim literal in a committed writer) / `traceable` 535
(`source_text` + `section_ref`, so re-checkable) / `unverifiable` **0**.

**Falsifiable check:** `python scripts/validate_controls_provenance.py`
— exit 1 if any row is `unverifiable`, exit 2 if it could not run (nothing verified
is not a pass). Wired into pre-push `[1e/5]` and the CI `schema-contract` job.
Predicted 534 / 535 / 0 before running; actual matched exactly. Demonstrated failing
on a synthetic row with no provenance, and on an empty writer tree.

**No migration.** A stored status column was considered and rejected: it goes stale
the moment a writer changes, whereas a derived one cannot. `needs_review` was also
considered and rejected — it is already consumed by four production routes
(`dcp/structured-controls`, `capacity/calculate`, `tod/parking-rates`,
`internal/setback-review`) and repurposing it would change served output.

**Open, not chased:** `provision_id` is populated on 1 row of 1,069 — table-wide
dead, so no manual row is missing it relative to any other row. Linking controls to
`regulatory_provisions.id` would make state (b) machine-checkable rather than
human-checkable, and is the natural next step before §5.6 grows the table.

---

## DQ-33: Case-sensitive document-naming mismatch causes silent ALL/ALL applicability fallthrough

**Status:** 🔍 Logged 2026-08-01, not sized — found while finishing DQ-30 PR3. Scope
deliberately not investigated further yet; this entry exists so it isn't lost, not as a
completed diagnosis.
**Found:** 2026-08-01

**Problem (as currently understood):** the DCP config lookups in
`enrichment/extractors/applicability_tagger.py` match `document_id` against config part
keys using plain case-sensitive substring checks (e.g. `_get_leichhardt_config()`:
`part_pattern in document_id or part_key in doc`, where `part_pattern`/`part_key` come from
`LEICHHARDT_CONFIG['parts']`'s Title-Case keys like `"Part A"`, `"Part C Section 1"`). Some
document IDs use an older, verbose naming convention (matching this casing) and others use a
newer slug-style convention (different case), so the same substring match silently succeeds
for one naming generation and silently fails for the other — a failed match falls through to
the unconditional `{'applicable_zones': ['ALL'], 'applicable_dev_types': ['ALL']}` default at
the end of the method, with no error or warning.

**Confirmed so far:** 18+ Leichhardt rows exhibit this ALL/ALL fallthrough due to the naming
mismatch. **Not yet checked:** whether the same old-verbose/new-slug split exists for the
other 6 configured councils (Ashfield, Marrickville, Waverley, Woollahra, City of Sydney,
Ku-ring-gai) — each has its own `_get_<council>_config()` method with its own matching logic,
so the exposure needs confirming per-council, not assumed from the Leichhardt case.

**Relationship to DQ-30:** a distinct defect class — DQ-30 is wrong/stale *zone-code values*
(legacy vs current NSW zone taxonomy); this is a *document-matching* failure that produces the
same symptom (ALL/ALL, ungated applicability) via a completely different mechanism (naming
convention drift, not zone taxonomy drift). Found as a side effect of DQ-30 PR3 verification,
deliberately not folded into that fix.

**Fix:** not started, not sized. Needs: (1) confirming the exact old-verbose vs new-slug
naming conventions in play and where each originates (extraction pipeline vs onboarding
script), (2) scoping how many rows/councils are affected before deciding whether to
case-normalize the match, fix the naming convention at the source, or both.

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

## DQ-33: document_id naming mismatch (fixed + re-tagged 2026-08-01)

**The defect.** The Marrickville / Ashfield / Leichhardt matchers in
`applicability_tagger.py` were written for a verbose document_id convention
("Chapter E1", "4.1", "_4_1_"). Every document_id in production uses a slug:
`Marrickville_DCP_2011__part4_s1_low_density`, `..._chapter_e1_heritage`,
`..._part_c_s2_urban_character`. `_detect_council()` still matched, so the row looked
handled — but the PART never resolved and it fell through to ALL/ALL. 9,854 served rows
across 107 document_ids; 85 of 100 sampled recorded `no_config`.

**Why this one needed a higher bar than the 241-row zone repair.** It NARROWS. Showing an
irrelevant control is noise; hiding a binding one is the liability, and hiding a rule that
applies is the original DQ-30 harm. So: a slug resolves ONLY to a key the council's config
already declares; nothing is invented; anything unrecognised stays ALL with source
`no_config`. `chapter_e2_haberfield` (118 rows) and `part2_s21` (131 rows) deliberately do
NOT resolve — the configs declare no such key, and resolving to the nearest neighbour would
be a guess. Under-matching is a missed improvement; over-matching is a hidden control.

**Blast radius, measured BEFORE the write** (22,007 rows in scope):
- 1,928 rows change values; 20,079 change provenance only
- 815 served rows narrow on zones, 882 on dev types
- highest risk — narrowed to a SINGLE zone: 2 documents / 369 rows
  (`part4_s1_low_density` → R2, `part6_industrial` → E4; both verified against
  `lep_zone_coverage` for Inner West)

**Prediction stated before running, and the actual after:** `config_all` 7,761 ·
`config_specific` 815 · `no_config` 1,278 — matched exactly. Zero rows narrowed while still
recording `no_config` (which would have meant a guess). Every written zone code exists in
Inner West's live land-use table.

**Consumer.** `ProvisionsByTocStructure` told Leichhardt users "all N provisions apply
regardless of dev type — your selection … does not remove any". Correcting the tagger gave
Leichhardt Part F (food premises) real dev types, making that sentence false. The copy is now
derived from the data (`anyDevTypeSpecific`) so it cannot drift again. No count display or
empty-state breaks on a shrunken list, and no row holds an empty zone array (checked, not
assumed — an empty array would match no zone at all).

**Rollback:** `regulatory_provisions_dq33_backup_20260801` (22,007 rows, all four columns).
Script: `scripts/retag_applicability_slug_docids.py` (dry-run default, backup-before-write,
null-safe per-row guard, printed rollback SQL).

**Still open, deliberately:** the ~20% of served provisions that are not controls at all
(historical narrative, TOC fragments, LaTeX garble). Real, separate, and narrowing
applicability does not touch it.

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

## DQ-35 / DQ-34 / DQ-36: wrong content in an exported PDF (fixed 2026-08-01)

**DQ-35 — a citation to a control the report deliberately hid.**
`scripts/conveyancing_db.py::fetch_dcp_setbacks` builds the rendered control lists by
skipping rows two ways: `needs_review` (a control flagged after a DCP amendment, suppressed
on purpose) and a `zone_specific` control whose `condition` names zones excluding this
property. It then set `clause_ref = rows[0][7]` — the RAW query's first row. So the single
clause reference a conveyancer reads could point at a suppressed control, or at one that
applies to a different zone entirely. Fixed to take the first clause from the rows that
survived; empty when nothing survived, because an invented reference is worse than none.

**DQ-34 — one PDF, two contradictory answers.**
`ContextSection.tsx` decided "Housing SEPP 2021: ✓ Applies — zone eligible for complying
development (CDC) pathway" from the ZONE ALONE, while `determineDevelopmentPathway()` in the
same file correctly checks heritage first and returns "Development Application (DA) — CDC and
exempt development not permitted". On heritage-listed land the exported PDF printed both, in
the same table. Now gated identically, and a zone match is reported as the zone test passing
rather than as an eligibility verdict on a proposal the report has never seen.

**DQ-36 — a site fact asserted without ever checking it.** (found while fixing DQ-34)
The same table hardcoded `Transport Oriented Development: ✗ Not applicable — Property not
within 400m of metro station or 800m of strategic centre`. The component is passed no TOD or
LMR catchment data at all, so no code path could ever print anything else: for any property
inside a catchment the PDF stated a falsehood about that site. Now reports "Not assessed in
this report" and points at the Portal TOD maps. Four further SEPPs (Design Quality,
Affordable Rental Housing, Seniors/Disability, Build-to-Rent) asserted "✗ Not applicable"
about proposals the report never sees; they now state their scope instead, which is the part
that is actually known.

Guarded by `tests/test_conveyancing_clause_citation.py` (7) and
`frontend-nextjs/__tests__/components/pdf-context-claims.test.ts` (8). Both mutation-verified:
restoring the old code fails them.

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

## DQ-28: Ashfield chapter_e2_haberfield TOC — catch-all only

**Status:** ✅ Fixed 2026-03-30
**Found:** 2026-03-29
**Fixed:** 2026-03-30

**Problem:** The Haberfield neighbourhood chapter (121 provisions, all on pdf_page=2) had no extracted section-level TOC data. A depth=0 catch-all entry was inserted in migration 018 so the JOIN worked, but all 121 provisions grouped under a single bucket.

**Root cause:** `COUNCIL_CHAPTER_RANGES` for both `chapter_b_public_domain` and `chapter_e2_haberfield` had a single entry covering the whole chapter. The extractor sets `pdf_page = page_start` of the matching range, so all provisions got the same page.

**Fix (migration 024):**
- Expanded `COUNCIL_CHAPTER_RANGES` to per-section entries (7 for chapter_b, 17 for chapter_e2)
- Re-extracted both chapters: chapter_b 49→55 provisions across 7 pages; chapter_e2 121→134 across 17 pages
- Deleted old overlapping TOC entries; inserted 7 (chapter_b) + 17 (chapter_e2) non-overlapping TOC entries
- `KNOWN_GRANULARITY_EXEMPTIONS` emptied — both chapters now pass the granularity gate
- Ashfield grade: 93.7% → 100% TOC JOIN; Grade A confirmed

---

## DQ-22: TOC Provisions Marked as Actionable

**Status:** ✅ FIXED
**Found:** 2026-01-26
**Fixed:** 2026-01-26

**Problem:** 34 Table of Contents (TOC) provisions had `v2_is_actionable = true`, causing them to appear in the DCP tab UI. User reported Part D showing TOC as first provision for 185 Parramatta Road Annandale.

**Example:** ID 80116 (Leichhardt Part D Energy) contained:
```
SECTION 1 – ENERGY MANAGEMENT .
SECTION 2 – RESOURCE RECOVERY AND WASTE MANAGEMENT .......... .....6
```

**Root Cause:** v2 enrichment process didn't detect TOC patterns (dotted leaders like `........`). The `dcp-complete` route had TOC filters but `for-property` API relied solely on `v2_is_actionable`.

**Fix:** SQL update to set `v2_is_actionable = false` for provisions containing `........`:
```sql
UPDATE regulatory_provisions
SET v2_is_actionable = false
WHERE v2_is_actionable = true
AND provision_text LIKE '%........%'
-- Fixed 34 rows
```

**Affected Documents:** Leichhardt DCP (Parts C, D, G), Marrickville DCP (Parts 2, 4, 6, 7, 8, 9), LEP TOC pages

---

## DQ-23: Duplicate Provisions in TOC View

**Status:** ✅ FIXED
**Found:** 2026-01-26
**Fixed:** 2026-01-26

**Problem:** Provisions appearing multiple times in DCP tab TOC-structured view. User reported "C1.5 CORNER SITES" showing 18 provisions on page 17 (6 provisions × 3 duplicates) and 6 provisions on page 18 (3 provisions × 2 duplicates).

**Root Cause:** The `groupByTocStructure` function (frontend-nextjs/app/api/provisions/for-property/route.ts:685-691) flattened provisions from all 4 layers (generic, use_specific, condition, precinct) WITHOUT deduplication. When the same provision appeared in multiple layers due to the layer query logic, it was added to the TOC structure multiple times.

**Code Location:** `frontend-nextjs/app/api/provisions/for-property/route.ts:688-690`

**Fix:** Added Map-based deduplication by provision ID before grouping:
```typescript
// Before (buggy):
const allProvisions: any[] = [];
for (const layer of layers) {
  for (const provision of layer.provisions) {
    allProvisions.push({ ...provision, layer: layer.layer });
  }
}

// After (fixed):
const provisionMap = new Map<number, any>();
for (const layer of layers) {
  for (const provision of layer.provisions) {
    if (!provisionMap.has(provision.id)) {
      provisionMap.set(provision.id, { ...provision, layer: layer.layer });
    }
  }
}
const allProvisions = Array.from(provisionMap.values());
```

**Impact:** Prevents duplicate provision display in DCP tab. Keeps first occurrence (preserves layer priority order: generic → use_specific → condition → precinct).

**Test:** Reload 185 Parramatta Road Annandale assessment - C1.5 Corner Sites should now show 6 unique provisions on page 17, 3 unique provisions on page 18.

---

## DQ-19: Part 9 Pattern Collision with Section Numbers

**Status:** ✅ FIXED
**Found:** 2026-01-24 (via automated test suite)
**Fixed:** 2026-01-24

**Problem:** Layer tagger pattern `'9__' in doc` matched section numbers like `19__` or `29__`, causing Part 2 sections to be misclassified as Part 9 precincts.

**Example:** `Marrickville__DCP__2011__-__2__19__Trees` (Section 2.19 Trees) was classified as `precinct` instead of `generic`.

**Root Cause:** Pattern `'9__'` is a substring of `19__`, `29__`, etc.

**Fix:** Added leading delimiter requirement in `layer_topic_tagger.py:179`:
```python
# Before: if '9_' in doc or '9__' in doc or 'Precinct' in doc:
# After:
if '_9_' in doc or '_9__' in doc or '-9_' in doc or '-9__' in doc or 'Precinct' in doc:
```

**Validation:** Test `test_marrickville_part2_section_topics` now passes.

---

## DQ-20: Part 5/6 vs Part 9 Precedence Issue

**Status:** ✅ FIXED
**Found:** 2026-01-24 (via automated test suite)
**Fixed:** 2026-01-24

**Problem:** Part 5 check for `'Commercial' in doc` matched before Part 9 for precinct names containing "Commercial".

**Example:** `Marrickville__DCP__2011__-__9__40__Town__Centre__Commercial` was classified as `use_specific` (Part 5) instead of `precinct` (Part 9).

**Fix:** Reordered Part 9 check to run before Part 5/6 in `layer_topic_tagger.py:169-177`.

**Validation:** Test `test_part9_precinct` now passes.

---

## DQ-21: Double-Underscore Document_ID Patterns

**Status:** ✅ FIXED
**Found:** 2026-01-24 (via automated test suite)
**Fixed:** 2026-01-24

**Problem:** Part 4.1/4.2 detection only checked `'4_1'` and `'4.1'`, missing `'4__1'` patterns used in some document_ids.

**Fix:** Added `'4__1'` and `'4__2'` patterns to `layer_topic_tagger.py:159-166`.

**Validation:** Test `test_part4_1_use_specific` now passes.

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

## Current Quality Issues (Priority Order)

### DQ-1: Precinct Filtering Returns 0 Provisions (CDC)
**Status:** ✅ RESOLVED - NOT A BUG
**Priority:** N/A - Expected behavior
**Evidence:** Full cascade with `precinct_id='12_'` + `assessment_type=CDC` returns Layer 4 = 0
**Root Cause:**
- Precinct 12_ (Marrickville Park and Morton Park) has 8 provisions for DA
- All 8 are character statements (qualitative, no numeric values)
- CDC filter requires `v2_has_numeric_value = true`
- Therefore CDC correctly returns 0 for this precinct

**NOT A BUG:** Other precincts (G7=6, Part 1=6, 25_=4, 10_=4) have CDC-compatible provisions with numeric values.

**Verification:**
```sql
-- DA returns 8 for precinct 12_
SELECT COUNT(*) FROM regulatory_provisions
WHERE v2_is_actionable = true AND v2_dcp_layer = 'precinct' AND v2_precinct_id = '12_';
-- Result: 8

-- CDC returns 0 (expected - no numeric values in this precinct)
SELECT COUNT(*) FROM regulatory_provisions
WHERE v2_is_actionable = true AND v2_dcp_layer = 'precinct'
AND v2_precinct_id = '12_' AND v2_provision_type = 'control' AND v2_has_numeric_value = true;
-- Result: 0
```

### DQ-2: Topic Misclassification
**Status:** ✅ RESOLVED
**Priority:** P1 - HIGH (was)
**Evidence:** "Car parking design controls" (ID 78329) was tagged as HEIGHT topic
**Root Cause:** Two issues in `layer_topic_tagger.py`:
1. **Dictionary iteration order**: `TOPIC_KEYWORDS` checked `height` before `parking`
2. **Unused section mapping**: `MARRICKVILLE_PART2_TOPICS` was never used

**Fix Applied (2025-11-24):**
1. Added `_extract_marrickville_part2_topic_from_docid()` method to use document_id section number
2. Changed `_extract_topic_from_text()` to return earliest match by position

**Results:**
- 14,501 provisions had topics updated
- ID 78329 now correctly tagged as `parking`
- "parking" provisions: 347 → 722 (+375)
- "parking" provisions wrongly tagged as height: 124 → 64 (-60)

**Fix Script:** `scripts/fixes/DQ2_fix_topic_classification.py`

### DQ-3: Provision Text Contains Headers Not Controls
**Status:** RESOLVED
**Priority:** P2 - MEDIUM (was)
**Evidence:** "Part 1 Preliminary..." TOC entries marked as actionable
**Root Cause:** LEP table of contents extracted as provisions
**Fix Applied (2025-11-24):** Marked 9 TOC entries as `v2_is_actionable = false`
**Result:** 11,835 -> 11,826 actionable provisions
**Fix Script:** `scripts/fixes/DQ3_fix_toc_entries.py`

### DQ-4: v2_marker Mostly NULL
**Status:** ACCEPTED - Design Limitation
**Priority:** P3 - LOW
**Evidence:** 8.5% have markers (1,008/11,826)
**Root Cause:** Extractor handles C markers only, not O (Objectives). 248 missing are all "O1" boilerplate objectives.
**Decision:** Accept as-is. C markers (topic mapping) work. O markers are qualitative, not needed for CDC.
**Impact:** None - fitness test passed without full marker coverage.

### DQ-5: Generic Layer Dominates (78%)
**Status:** ACCEPTED - Expected
**Priority:** P3 - LOW
**Evidence:** generic=78%, condition=10%, precinct=10%, use_specific=1%
**Assessment:** This is normal for DCP structure. Dev_type filter reduces 354→34 (90%). Working as intended.

### DQ-6: Duplicate Provisions
**Status:** ACCEPTED - Minor
**Priority:** P3 - LOW
**Evidence:** 246 duplicates in 10 groups (2% of total)
**Assessment:** Mostly SEPP boilerplate text repeated across contexts. Minor impact, not blocking.

### DQ-7: Dev-Type Coverage
**Status:** ✅ RESOLVED
**Priority:** P0 - CRITICAL (was)
**Evidence:** All 13 dev_types now have adequate CDC provision coverage.

| Dev Type | Before | After | Status |
|----------|--------|-------|--------|
| dwelling_house | 34 | 307 | OK |
| secondary_dwelling | 8 | 281 | OK |
| dual_occupancy | 10 | 283 | OK |
| multi_dwelling_housing | 10 | 282 | OK |
| residential_flat_building | 10 | 280 | OK |
| retail_premises | 11 | 109 | OK |
| commercial_premises | 0 | 99 | OK |
| office_premises | 0 | 122 | OK |
| industrial_development | 6 | 117 | OK |
| warehouse | 4 | 109 | OK |
| boarding_house | 9 | 277 | OK |
| child_care_centre | 1 | 40 | OK |
| shop_top_housing | 10 | 53 | OK |

**Root Cause:** 286 provisions tagged `['ALL']` instead of specific dev_types.

**Fix Applied (2025-11-24):**
1. `DQ7_devtype_enrichment.py` - Section-based + keyword mapping for residential
2. `DQ7_commercial_industrial_enrichment.py` - Zone-based enrichment for B/IN zones
3. `DQ7_remaining_devtypes.py` - Text matching + parking provisions for all types

**Fix Scripts:** `scripts/fixes/DQ7_*.py`

---

## Fix Workflow

### Per-Issue Process
```
1. Read this file to understand issue
2. Investigate root cause with diagnostic queries
3. Create fix script in scripts/fixes/DQ-{N}_fix_{description}.py
4. Run fix on LOCAL first
5. Verify with test_workflow_quality.py
6. Sync to Supabase: python scripts/sync_v2_to_supabase.py
7. Update status in this file
8. Commit with message: "fix(data): DQ-{N} {description}"
```

### Session Start Checklist
```
[ ] Read .claude/prp/INDEX.md
[ ] Read this file (DATA_QUALITY_TRACKER.md)
[ ] Check which DQ-N is next to fix
[ ] Run test_workflow_quality.py to see current state
[ ] Pick ONE issue to fix this session
```

---

## Test Commands

```bash
# Run quality assessment
python test_workflow_quality.py

# Check sync status
python scripts/compare_local_supabase.py

# Check specific issue
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
import psycopg2
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL') or 'dbname=nsw_planning')
cur = conn.cursor()
# Add diagnostic query here
"
```

---

## Session Log

### 2024-11-24: Initial Assessment
- Completed 4-layer API implementation
- Ran workflow quality tests
- Identified 6 data quality issues
- Created this tracking file

### 2025-11-24: DQ-1 and DQ-2 Resolution + Fitness Assessment
- **DQ-1 RESOLVED**: Not a bug - expected behavior
  - Precinct 12_ has 8 DA provisions but 0 CDC provisions (no numeric values)
  - Other precincts (G7, Part 1, 25_) have CDC-compatible provisions
- **DQ-2 RESOLVED**: Topic misclassification fixed
  - Root cause: Dictionary iteration order + unused section mapping
  - Fix: Added section-based topic extraction + earliest-match algorithm
  - Result: 14,501 provisions updated, ID 78329 now correctly tagged

**FITNESS FOR PURPOSE ASSESSMENT:**
```
Scenario: R2 Zone, Dwelling House, CDC Assessment
  Layer 1 (Generic + dev_type): 34
  Layer 2 (Zone R2):            3
  Layer 3 (Condition):          0 (non-heritage)
  Layer 4 (Precinct 12_):       0 (qualitative only)
  TOTAL:                        37 provisions

VERDICT: PASS - Within target range (30-100)
```

Key findings:
- Full cascade with dev_type filter reduces 354 -> 34 (90% reduction)
- v2_applicable_dev_types is 100% populated for generic layer
- Topic classification working for Marrickville Part 2.10 (all 38 = parking)
- System is FIT FOR PURPOSE for CDC certifier workflow

### 2025-11-24: DQ-7 Dev-Type Enrichment Complete
- **DQ-7 RESOLVED**: All 13 dev_types now have adequate CDC provision coverage
  - Before: Only dwelling_house (34) worked, others had 0-11
  - After: All types have 40-307 provisions
- **Fix approach**:
  1. `DQ7_devtype_enrichment.py` - Section/keyword mapping for residential (8,103 updated)
  2. `DQ7_commercial_industrial_enrichment.py` - Zone-based enrichment for B/IN zones
  3. `DQ7_remaining_devtypes.py` - Text matching + parking provisions for remaining types

**ALL DATA QUALITY ISSUES NOW RESOLVED**

### DQ-8: DCP-ONLY Scope Clarification (2025-11-24)
**Finding**: Previous DQ-7 enrichment incorrectly included SEPP/LEP provisions.
**Scope**: This pipeline is DCP-ONLY. SEPP/LEP values come from Planning Portal API.

**Actual DCP CDC Data:**
| Council | Total DCP | CDC-eligible |
|---------|-----------|--------------|
| Marrickville | 1,051 | 79 (8%) |
| Leichhardt | 2,989 | 43 (1%) |
| Ashfield | 1,526 | 10 (1%) |
| **TOTAL** | **5,566** | **132 (2%)** |

**Reality**: Only 2% of DCP provisions are CDC-eligible (have numeric values).
This is DATA REALITY - DCPs are mostly qualitative (objectives, character statements).
The 132 DCP CDC provisions ARE correctly dev_type tagged.

### Professional Scenario Testing (2025-11-24)
- **CDC scenarios**: All pass (272-274 provisions for residential, 86-88 for commercial/industrial)
- **DA scenarios**: Return more results (7000+) - expected, DA includes objectives not just controls
- **Zone handling**: 'ALL' correctly treated as wildcard (matches any zone)
  - Marrickville uses specific zones (R2, R3/R4 for Part 4)
  - Leichhardt/Ashfield use 'ALL' (zone not a determinant for those DCPs)

### DQ-9: DCP Filter Bug - IWLEP Reference (2025-11-24)
**Status:** ✅ FIXED
**Priority:** P1 - HIGH (was)
**Finding**: Wrong DCP filter was excluding valid DCP provisions.

**Root Cause:**
- WRONG filter: `NOT ILIKE '%LEP%'` - excluded DCP files with "IWLEP" in name
- CORRECT filter: `NOT ILIKE '%Local_Environmental_Plan%'` - only excludes actual LEP docs

**Impact:**
- 2,330 Leichhardt DCP provisions were incorrectly filtered out
- Leichhardt appeared to have "659" provisions but actually has **2,989**

**Corrected Data:**
| Council | generic | precinct | condition | use_specific | TOTAL |
|---------|---------|----------|-----------|--------------|-------|
| Marrickville | 230 (22%) | 359 (34%) | 315 (30%) | 147 (14%) | 1,051 |
| **Leichhardt** | **2,309 (77%)** | 659 (22%) | 0 | 21 (1%) | **2,989** |
| Ashfield | 422 (28%) | 197 (13%) | 907 (59%) | 0 | 1,526 |

**Fix:** Updated filter in INDEX.md and test files to use correct pattern

### DQ-10: Council-Specific UI/UX Strategy (2025-11-24)
**Status:** ✅ DOCUMENTED
**Priority:** P1 - HIGH

**Finding**: Each council's DCP has a DIFFERENT compliance philosophy that UI should reflect.

**Council DCP Structures:**
| Council | Primary Layer | Filter Strategy |
|---------|---------------|-----------------|
| Marrickville | Balanced (precinct 34%, condition 30%, generic 22%) | Zone + Precinct + Topic |
| Leichhardt | **Generic-heavy (77%)** | Topic is PRIMARY filter (reduces 2,211 → 30-85) |
| Ashfield | Condition-heavy (59%) | Site conditions + Topic |

**Test Results (dwelling_house filter with correct DCP filter):**
| Council | dwelling_house count | Layer distribution |
|---------|---------------------|-------------------|
| Marrickville | 228 | generic 53%, use_specific 21%, precinct 15%, condition 11% |
| **Leichhardt** | **2,211** | generic 98%, precinct 2% |
| Ashfield | 394 | generic 99%, condition 1% |

**UI/UX Implications:**
1. **Leichhardt**: Has 2,211 dwelling_house provisions - MUST use topic filter to narrow
   - Topic options: parking (85), building_form (81), landscaping (34), heritage (30)
2. **Marrickville**: Zone filter effective, also use topic
3. **Ashfield**: Site condition (heritage) is key filter, also use topic

**For certifier workflow:**
- Leichhardt CDC: 21 provisions (workable)
- Marrickville CDC: 17 provisions (workable)
- Topic filtering reduces DA queries by 80-95%

### Comprehensive Professional Testing (2025-11-24)
**Test Suite:** `test_comprehensive_professional.py`, `test_tailored_filters.py`
**Results:** 9/13 scenarios PASS

**Scenario Results:**
| Scenario | Count | Expected | Status |
|----------|-------|----------|--------|
| Marrickville R2 Dwelling DA | 193 | 50+ | PASS |
| Marrickville R2 Dwelling CDC | 17 | 5+ | PASS |
| Marrickville R3 Multi-Dwelling DA | 109 | 30+ | PASS |
| Marrickville B2 Retail CDC | 25 | 3+ | PASS |
| Leichhardt R2 Dwelling DA | 39 | 100+ | FAIL (data gap) |
| Leichhardt R2 Dwelling CDC | 2 | 5+ | FAIL (data gap) |
| Ashfield R2 Dwelling DA | 390 | 50+ | PASS |
| Ashfield Dual Occ DA | 397 | 30+ | PASS |
| ALL COUNCILS R2 Dwelling DA | 649 | 200+ | PASS |

**Key Insights:**
1. **Marrickville**: Full 4-layer support, zone filtering effective (34% zone-specific)
2. **Leichhardt**: Generic-heavy (77% generic, 2,989 total) - topic filter CRITICAL
3. **Ashfield**: Condition-heavy (59% condition layer), low CDC is data reality

**Filter Effectiveness by Type:**
- **Dev_type**: Effective for ALL councils (reduces to 2-30% of total)
- **Topic**: Very effective (2-8% per topic, 80-95% reduction)
- **Zone**: Only for Marrickville (34% zone-specific)

### Session Log: Council-Specific UI Implementation (2025-11-24)

**Completed:**
1. ✅ Fixed DCP filter bug (`NOT ILIKE '%LEP%'` was wrong - excluded IWLEP-referenced files)
2. ✅ Correct filter: `NOT ILIKE '%Local_Environmental_Plan%'`
3. ✅ Discovered Leichhardt has 2,989 provisions (not 659) - was filter bug, not data gap
4. ✅ Implemented council-specific UI in `ProvisionsByTopic.tsx`:
   - Topic filter buttons with council-specific suggested topics
   - Warning for Leichhardt when no topic selected
   - Professional priority ordering of topics
5. ✅ Created `frontend-nextjs/lib/council-config.ts`
6. ✅ Created `PROFESSIONAL_USER_GUIDE.md` for trial users
7. ✅ Created git tag `v1.0-pre-council-ux` on main before merge
8. ✅ Pushed tag to remote

### Next Steps:
1. ✅ ~~Fix DQ-9~~ (was filter bug, not data gap - FIXED)
2. ✅ ~~Implement council-aware filtering~~ (DONE)
3. Merge to main and deploy to Vercel
4. Test production with professional users

### DQ-11: Heritage Sub-Categorization (2025-11-25)
**Status:** ✅ COMPLETE
**Priority:** P2 (was)
**Scope:** Ashfield Chapter E1 heritage provisions (907 total)

**Problem:** 907 heritage provisions shown as undifferentiated list. No way to find relevant controls.

**Solution Applied:** LLM categorization using OpenAI gpt-4o-mini

**Final Results (verified in database):**
| Type | Count | Description |
|------|-------|-------------|
| control | 163 | Actionable requirements with C markers or imperative verbs |
| character | 422 | HCA-specific descriptions and significance statements |
| descriptive | 322 | Historical narratives, style definitions, background |

**Element Tagging (controls):**
- fence: 39, materials: 37, roof: 29, verandah: 21, scale: 16
- car_parking: 15, window: 14, facade: 14, demolition: 13, chimney: 12

**HCA Tagging:**
- ashfield_heights: 142, summer_hill: 49, queen_street: 17, victoria_square: 16
- murrell: 11, farleigh: 7, tintern: 6, moonagee: 6, holwood: 6

**Schema columns added:**
- `v2_heritage_type` (TEXT)
- `v2_heritage_element` (TEXT[])
- `v2_heritage_hca` (TEXT)

**Fix Script:** `scripts/fixes/DQ11_heritage_categorization.py`

### DQ-13: Leichhardt Uncategorized Topics (2025-11-29)
**Status:** ✅ FIXED
**Priority:** P1 (was)
**Problem:** 42% of Leichhardt provisions (1,242/2,962) had NULL v2_topic

**Root Cause:** Bug in `enrichment/extractors/layer_topic_tagger.py`
- Section 1 handler only used C marker extraction
- Many provisions lack C markers but have keyword matches
- Missing fallback: `or self._extract_topic_from_text(provision_text)`

**Fixes Applied:**
1. Fixed `layer_topic_tagger.py` - added keyword fallback for Section 1
2. Marked 124 Part A (Introduction) provisions as non-actionable
3. Re-classified 1,164 Part C Section 1 provisions

**Results:**
- Uncategorized: 42% → 10.1% (reduced by 32 percentage points)
- 878 provisions now have topics assigned
- Part A correctly marked non-actionable (procedural, not requirements)

**Fix Script:** `scripts/fixes/DQ13_leichhardt_fixes.py`

### DQ-14: Leichhardt PDF URL Coverage (2025-11-29)
**Status:** ✅ FIXED
**Priority:** P1 (was)
**Problem:** Only 26% of Leichhardt provisions had PDF page image URLs (vs 100% for Marrickville/Ashfield)

**Root Cause:** Multiple issues
1. `pdf_page_image_url` column was NULL, needed population from `pdf_page`
2. Folder mapping regex: "Section 1" matched before "Part G"
3. Part G offset: `pdf_page` has +100 offset, should use `page_number` column
4. Missing PNG files: pages 10, 21, 23, 24, 25, 35 not extracted

**Fixes Applied:**
1. `DQ14_leichhardt_pdf_urls.py` - Initial URL population (2,097 provisions)
2. `extract_missing_pdf_pages.py` - Extracted 115 missing pages using PyMuPDF
3. `DQ14b_fix_part_g_urls.py` - Fixed Part G using `page_number` (487 provisions)
4. `extract_missing_part_g.py` - Extracted 6 additional Part G pages
5. Uploaded all new PNG files to Cloudflare R2

**Results:**
| Metric | Before | After |
|--------|--------|-------|
| PDF URL coverage | 26% (773/2,962) | **100%** (2,838/2,838) |
| Part G coverage | 0% | 100% |
| Missing PNG files | 160 | 0 |

**Key Insight:** Part G has inconsistent offset pattern (pdf_page ≠ page_number).
Always use `page_number` column for Part G PDF URLs.

**Fix Scripts:** `scripts/fixes/DQ14_leichhardt_pdf_urls.py`, `scripts/fixes/DQ14b_fix_part_g_urls.py`

### DQ-15: Topic Case Inconsistency (2025-11-29)
**Status:** ✅ FIXED
**Priority:** P2 (was)
**Problem:** Leichhardt had duplicate topics differing only by case (e.g., `parking` vs `Parking`)

**Root Cause:** Inconsistent capitalization during topic extraction
- 17 topics affected: heritage, height, setbacks, parking, access, landscaping, trees, signage, waste, privacy, stormwater, fencing, flooding, contamination, safety, roofing, solar

**Fix Applied:**
1. Normalized all topics to Title Case
2. Fixed `building_form` → `Building Form`

**Results:**
- 845 provisions updated (725 case normalization + 120 building_form)
- All topics now use consistent Title Case
- Leichhardt topic distribution now accurate

**Fix Script:** `scripts/fixes/DQ15_normalize_topic_case.py`

### 50-Address Comprehensive Test (2025-11-29)
**Status:** ✅ ALL PASS
**Scope:** 50 representative addresses across all Inner West councils

**Test Results:**
| Council | Tests | Pass | Warn | Fail | Avg Provisions | Topic | PDF |
|---------|-------|------|------|------|----------------|-------|-----|
| Marrickville | 17 | 17 | 0 | 0 | 623 | 95% | 100% |
| Leichhardt | 17 | 17 | 0 | 0 | 2,790 | 90% | 100% |
| Ashfield | 16 | 16 | 0 | 0 | 1,502 | 93% | 100% |
| **TOTAL** | **50** | **50** | **0** | **0** | - | - | - |

**Zones Tested:**
- R2, R3 (residential)
- B1, B2, B4 (business)
- IN1, IN2 (industrial)

**Conclusion:** All 50 addresses return complete, accurate provision data with 100% PDF coverage.

### Two-Table Architecture Clarification (2025-12-01)
**Status:** DOCUMENTED

**Issue:** Previous sessions incorrectly assumed Leichhardt's 28% LLM coverage meant incomplete extraction.

**Reality:**
- LLM extraction is INTENTIONALLY SELECTIVE - only extracts actionable development controls
- 20-30% extraction rate is NORMAL - most DCP text is objectives, definitions, context
- Leichhardt Part C Section 1: 1,782 raw → 342 LLM (19%) is CORRECT
- Marrickville >100% is also correct - one paragraph can yield multiple requirements

**Coverage (verified 2025-12-01):**
- Ashfield: 791 LLM / 1,579 raw = 50%
- Marrickville: 1,338 LLM / 985 raw = 136%
- Leichhardt: 834 LLM / 2,989 raw = 28%

**DO NOT** assume low percentage means extraction needs to be re-run.

### DQ-16: Heritage Topic Fragmentation (2025-12-07)
**Status:** ✅ FIXED
**Priority:** P1 - HIGH (was)
**Problem:** Ashfield Heritage chapter provisions split across multiple topics in UI

**Evidence:**
- User sees: Heritage (187), Character (80), Fencing (22), Streetscape (22), etc.
- Reality: ALL 364 provisions are from Heritage chapter (part_name='Heritage')
- The `category` field (subject matter) is being used as `v2_topic` in API response

**Root Cause:**
In `queryHeritageFromDcpGeneralRequirements()` (for-property/route.ts:363):
```sql
INITCAP(REPLACE(category, '_', ' ')) as v2_topic
```
This maps `category` (e.g., 'character', 'fencing') to `v2_topic` instead of using 'Heritage'.

**Fix Applied (2025-12-07):**

1. **API change** (`for-property/route.ts`):
   - Changed: `CASE WHEN part_name = 'Heritage' THEN 'Heritage' ELSE ... END as v2_topic`
   - Added: `INITCAP(REPLACE(category, '_', ' ')) as v2_heritage_subcategory`
   - Fixed: Changed `part_name ILIKE '%Heritage%'` to exact match `part_name = 'Heritage'`
     (Excludes Leichhardt "Connections (Heritage and Transport)" which is NOT heritage)

2. **TypeScript types** (`ProvisionsByTopic.tsx`):
   - Added `v2_heritage_subcategory?: string` to Provision interface

3. **UI enhancement** (`ProvisionsByTopic.tsx`):
   - Added subcategory grouping within Heritage topic
   - Shows collapsible sections: Character (80), Fencing (22), Heritage (187), etc.

**Result:**
- Before: Heritage: 187, Character: 80, Fencing: 22 (separate topics)
- After: Heritage: 364 (consolidated with subcategory grouping)

**Also Fixed:**
- Leichhardt "Connections (Heritage and Transport)" no longer incorrectly included as heritage
- 78 provisions correctly excluded (they're about events/safety, not heritage)

### DQ-17: "Orphaned" Non-Heritage Provisions (2025-12-07)
**Status:** ✅ RESOLVED - NOT ORPHANED
**Priority:** N/A - Working as intended
**Initial Concern:** 1,072 provisions in `dcp_general_requirements` not returned by provisions UI

**Investigation (2025-12-07):**

Provisions by council not shown in main provisions UI:
- Leichhardt: 695 (83% of their 834 LLM provisions)
- Ashfield: 212 (27% of their 791)
- Marrickville: 69 (5% of their 1,338)

**Key Discovery: These ARE Used by Capacity API**

Tested `/api/capacity/calculate` in production - it queries `dcp_general_requirements` for:
- **Parking**: Returns clean data like "One car parking space is required per dwelling"
- **Setbacks**: Returns 8 structured setback values
- **Landscaping**: Queries this table (currently returns empty for Ashfield)

**Why Two Tables Exist (Intentional Architecture):**

| Table | Used By | Data Quality | Purpose |
|-------|---------|--------------|---------|
| `regulatory_provisions` | Provisions UI | Raw PDF text, OCR artifacts, verbose | Show full DCP context |
| `dcp_general_requirements` | Capacity API, Heritage UI | LLM-cleaned, distilled | Power calculations |

**Raw vs LLM Quality Comparison:**

LLM (capacity API):
> "One car parking space is required per dwelling"

Raw (provisions UI):
> "Parking requirement for restaurant $2 0 0 { \mathrm { m } } 2 - 1$ space per $4 0 \mathrm { m } 2$..."

The raw data has LaTeX artifacts and OCR noise. LLM extraction cleaned this into usable requirements.

**Conclusion:**
The "orphaned" provisions are NOT orphaned - they power the capacity calculator with clean data.
The two-table architecture is intentional separation of concerns:
- Raw table → provisions display (full context)
- LLM table → calculations (clean values)

**No action required.** Architecture is correct.

### DQ-18: Marrickville pdf_page Field (2026-01-12)
**Status:** ✅ FIXED
**Priority:** P1 (was)

**Understanding:**
- Marrickville DCP was split into 19+ separate PDF files by section
- Each section PDF starts at page 1 (relative numbering)
- `pdf_page` stores the relative page within each section (CORRECT)
- `pdf_page_image_url` contains absolute page numbers across combined document
- Images load correctly from URL; labels show relative page within section

**Incorrect "Fix" Applied & Reverted (2026-01-12):**
1. `DQ18_fix_marrickville_page_numbers.py` incorrectly changed pdf_page to absolute numbers
2. This broke the UI labels (e.g., "Page 5" instead of "Page 1" for first page of Landscaping section)
3. `DQ18_revert_marrickville_pages.py` restored correct relative page numbers
4. Formula: `relative_page = url_page - section_min_page + 1`
5. 1,671 provisions corrected back to relative numbering

**Part 4.1 Specific Issue (2026-01-12):**
- Part 4.1 Zone-Specific provisions showed wrong page numbers (e.g., "Page 5" when PDF footer showed "Page 1")
- Root cause: URL filename truncation created two groups (`_4.1_Low_Density_Res` vs `_4.1_Low_Density_Resid`)
- Each group calculated separate min_url, giving wrong offsets for the truncated variant
- Additional issue: TOC pages (url pages 3-6) were included in min calculation, but actual content starts at page 7

**Fix Applied:**
1. `DQ18_fix_by_section_number.py` - Groups by section number (e.g., "4_1") instead of URL filename
2. `DQ18_fix_exclude_toc.py` - Excludes TOC pages (containing "........") from min calculation
3. `DQ18_fix_part41_direct.py` - Direct fix using confirmed data: page_7.png = PDF page 1
   - MIN_CONTENT_URL = 7 (user confirmed from PDF footer inspection)
   - TOC pages (url 3-6) set to pdf_page = 1
   - Content pages: `pdf_page = url_page - 7 + 1`

**Verification:**
- url_page=7 → pdf_page=1 ✓
- UI now shows correct page numbers matching PDF footers

**Fix Scripts:** `scripts/fixes/DQ18_*.py`

**Current State:**
- `pdf_page` = relative page within each section PDF (correct for display)
- Images load from URL with absolute pages (correct rendering)
- UI shows "View Part 2 Page 1" for first page of each section (correct)

### DQ-25: Transport & Infrastructure sepp_structured_requirements Empty (2026-02-14)
**Status:** ⏳ BACKLOG
**Priority:** P2 — blocks classified road noise feature for certifiers

**Problem:** `sepp_structured_requirements` table has zero rows for `sepp_id = 'transport_infrastructure_2021'`. The UI transport section (`StateLevelControls.tsx` lines 658-672) is fully wired but never renders because the underlying data was never populated.

**What's blocking the feature:**
- `sepp-router.ts` adds `SEPP_TRANSPORT_INFRASTRUCTURE_2021` to every property unconditionally (line 126-128)
- `StateLevelControls` fetches `/api/sepp/structured-requirements` with `seppId = 'transport_infrastructure_2021'`
- API queries `sepp_structured_requirements WHERE sepp_id = 'transport_infrastructure_2021'` → empty → nothing renders

**What needs to go in this table:**
Three provision categories relevant to residential certifiers:
1. **Classified road corridor** — noise attenuation requirements for dwellings within X metres of classified roads (State Roads, RMS/TfNSW). Affects large % of inner-Sydney properties (Parramatta Rd, King St etc.). Most important for CDC certifiers.
2. **Rail corridor** — noise/vibration requirements near railway lines
3. **Airport obstacle limitation surfaces** — height controls near Sydney/Bankstown airports

**Source document:** `State_Environmental_Planning_Policy_Transport_and_Infrastructure_2021__NSW_Legislation` (2,733 provisions) — but v2_topic tagging is wrong (see DQ-24). Will need either:
- Manual curation of the specific classified road/rail/airport clauses into `sepp_structured_requirements`, OR
- Fix DQ-24 first (retag document), then build query-based lookup

**Triggering condition:** Should only show when Planning Portal API detects classified road corridor or rail corridor proximity — not for every property. Currently added unconditionally in sepp-router.ts (should be conditional).

**Do not fix until:** Classified road/rail corridor detection from Planning Portal is confirmed working for a test address on a classified road.

---

### DQ-24: Transport & Infrastructure SEPP v2_topic Retag (2026-02-14)
**Status:** ⏳ BACKLOG
**Priority:** P3 — No current production impact
**Document:** `State_Environmental_Planning_Policy_Transport_and_Infrastructure_2021__NSW_Legislation` (2,733 provisions)

**Problem:** Entire document tagged with DCP-style topic taxonomy (heritage, building_form, height, landscaping, waste, signage etc.) which is wrong for a state infrastructure instrument. Solar/wind turbine provisions (the main use case) are tagged `waste` instead of `solar`.

**Distribution of wrong tags:**
- (null): 1,724 (63%)
- heritage: 116, building_form: 110, height: 106, landscaping: 95, safety: 94, access: 87, waste: 83, signage: 59, stormwater: 47, trees: 41, fencing: 40, flooding: 38, parking: 33
- solar: 20 (only correct ones)

**Root cause:** DCP topic taxonomy applied to a SEPP document during an earlier tagging pass. DCP labels (setbacks, heritage, signage etc.) are meaningless for infrastructure development types.

**Current production impact:** ZERO — live app uses `sepp_structured_requirements` table for the transport section, not `regulatory_provisions`. Broken tags are never queried by the UI.

**Future impact:** Blocks solar provision browser — certifier filtering by Solar would see 0 actionable provisions.

**Fix required:**
1. Clear all v2_topic values for this document
2. Re-run classification with infrastructure-appropriate taxonomy: roads, rail, electricity/solar, water/stormwater, parking, community_infrastructure, general
3. Note: the 168-provision duplicate (`State_Environmental_Planning_Policy_(Transport_and_Infrastructure)_2021___NSW_Legislation` with parentheses) also exists — may need cleanup

**Do not fix until:** Solar provision browser is being built.

---

### DQ-26: Marrickville Truncated pdf_page_image_url Stems (2026-03-04)
**Status:** ✅ FIXED
**Priority:** P1 (was)

**Problem:** Old Marrickville provisions (double-underscore document_id format from first extraction pass) had `pdf_page_image_url` pointing to truncated R2 image filenames (e.g., `Signs_and_Adv_page_5.png` instead of `Signs_and_Advertising_page_5.png`). New re-extraction provisions used full names matching actual R2 filenames. When old images were absent from R2, PDF link buttons showed broken images.

**Scope:** 57 chapters, 391 provisions. Heritage chapter (`8.0_Heritage`) correctly excluded — it has 244 new provisions confirming it's a valid complete chapter name, not a truncation.

**Root Cause:** First extraction pass used truncated PDF filenames (likely Windows path-length limit). Image files were uploaded to R2 with truncated names. Re-extraction used full filenames. Some old images were deleted/overwritten; others remain. For Landscaping chapter (first reported), old images were absent from R2.

**Fix Applied:**
```sql
-- Pattern: replace truncated stem with full stem, keep _page_N.png suffix
-- Example: Landscaping_an_page_N -> Landscaping_and_Open_Spaces_page_N
-- 57 UPDATE statements run in a single transaction, 391 total rows changed
```
Full-name images confirmed to exist in R2 (verified by working new provisions). Page numbers preserved exactly.

**Also fixed separately (2026-03-04):** The Landscaping chapter (14 provisions, first user-reported broken link) was fixed in the same session before this batch fix.

---

### DQ-27: Marrickville LaTeX Math Artefacts in provision_text (2026-03-04)
**Status:** ✅ FIXED
**Priority:** P1 (was)

**Problem:** 36 Marrickville provisions contained raw LaTeX math mode tokens from pdfplumber extraction. Example: "Contour lines and levels for sites in excess of 6 0 0 { \mathsf { m } } ^ { 2 }$" instead of "600m²".

**Patterns cleaned:**
- `\mathsf`, `\mathfrak`, `\mathtt` math font commands
- `{ \mathsf { m } } ^ { 2 }$` → `m²` (two variants: with and without outer `{ }`)
- `\mathsf { m m }` → `mm`, `\mathsf { p m }` → `pm`
- `\mathtt { x 0.6 }` → `x 0.6` (strip wrapper, keep content)
- `\star _ { \mathsf { N B } }` → `` (NB note markers)
- `{ , }` → `,` (LaTeX thousands separator)
- Trailing `$` delimiters
- Spaced digits: `6 0 0` → `600` (via lookbehind/lookahead patterns)

**Fix applied:** Python script + companion `preProcessReplacements` added to Marrickville config in `frontend-nextjs/lib/dcp-format-configs.ts` (safety net for future re-extractions).

**Script:** `scripts/fix_marrickville_latex.py` (gitignored, not committed to repo)

---

### Provision Text Formatting Enhancement (2026-01-12)
**Status:** ✅ IMPLEMENTED
**File:** `frontend-nextjs/lib/provision-text-formatter.ts`

**Issue:** Numbered lists (1. text 2. text 3. text) not being rendered as list items in provision display

**Fix Applied:**
Added numbered list detection to `splitInlineList()` function:
```typescript
// Pattern for numbered lists: "1. text 2. text 3. text"
const numberPattern = /(?:^|\s)(\d+)\.\s+/g;
const numberMatches = text.match(numberPattern);

if (numberMatches && numberMatches.length >= 2) {
  const parts = text.split(/(?=(?:^|\s)\d+\.\s+)/);
  const cleanParts = parts.map(p => p.trim()).filter(p => p.length > 0 && /^\d+\./.test(p));
  if (cleanParts.length >= 2) {
    return cleanParts;
  }
}
```

**Result:** Numbered lists now render as proper list items alongside roman numerals (i., ii.) and letters (a., b.)
