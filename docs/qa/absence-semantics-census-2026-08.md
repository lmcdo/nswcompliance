# Absence-semantics census — 2026-08-03

**Item 0 of the output-grounding campaign** (`~/.claude/plans/ce-output-grounding-campaign-2026-08.md`
§7 revised order). A census, not a fix: no refactors here. The typed-absence design comes
after this says where it matters.

**The nine collapse states** (Sol, accepted): when a check returns "nothing", these
distinct situations can hide inside one empty result —
**S1** searched-and-none-found · **S2** source down/unreachable · **S3** coverage
incomplete (layer/LGA never ingested) · **S4** address/parcel unresolved · **S5** outside
supported geography · **S6** stale cache · **S7** parser/schema failure · **S8** filtered
out (coords missing, page cap, area cap) · **S9** genuinely not applicable.

Every claim below cites file:line, read 2026-08-03 on `fix/output-grounding-items-0-2`
(branched from origin/main d85255e6). "Caller distinguishes": **yes** = the consumer can
tell the states apart; **partial** = some states typed, others collapsed; **no** = one
empty value serves them all.

## The house patterns to spread (found working, cite these — do not design new ones)

| Pattern | Where | What it does |
|---|---|---|
| DA three-state | `services/conveyancing.py:169-206` (`_nearby_da_count`) | None+`fetch_failed` ≠ genuine 0; failure withholds the data-source claim (:355-358) and renders "could not be checked" |
| Typed status dicts | `conveyancing.py:610-775` (`_fetch_anef`, `_fetch_mine_subsidence`, `_fetch_contaminated`, `_fetch_servicing`, `_fetch_coastal`, `_fetch_structures_records`) | `{"status": "failed"}` vs `"empty"` (checked clear) vs `"outside"` — renders "Not assessed", never "Clear" |
| Four-state climate | `conveyancing.py:692-711` (`_fetch_climate` → `query_narclim_state`) | out_of_domain (permanent, S5) deliberately NOT collapsed with unavailable (fixable, S2) |
| Coverage tracking | `conveyancing.py:946-1001` (`covered_layers` → `_compute_confidence` cap) | a missing ingest layer (S3) caps confidence to medium instead of reading as clear |
| Typed flood signal | `services/flood_truth.py:1185-1257` (`_compute_flood_signal`) | `"unavailable"` on EPI failure (:1198) AND on uncovered-LGA-with-no-other-signal (:1224-1230) — refuses to serve "none" where S2/S3 apply |
| query_failed vs none | `flood_truth.py:336-433` (`_query_epi_overlay`) | `epi_flood_class: "none"` (S1) vs `data_currency: "query_failed"` (S2/S7) — distinct fields |
| Computed confidence + contract | `flood_truth.py:1258-1277` | confidence from counted source availability, icontract-guarded |
| confidence_reason | `services/granny_flat.py:338-339, 686` | (confidence, human-readable reason) pair, reason shown in UI; typed `confidence='error'` report rows (:790-793) |
| Per-layer None | `services/portal_constraints.py:412-449` (`fetch_sepp_exclusions`) | per-layer `bool|None`; all-failed → None; partial failure visible per key |
| Fail-loud helpers | `portal_constraints.py:51-97` | ArcGIS helpers raise; the conveyancing wrappers type the exception as `"failed"` — no silent [] |
| Audit-trail error recording | `services/threat_radar.py:294-306`, `shadow_detector.py:346-351` | per-endpoint error strings recorded even when the check proceeds |

## Census table

Severity key: 🔴 = an empty/None/zero is (or can be) served as an affirmative claim;
🟡 = collapse exists but is capped/labelled somewhere; 🟢 = typed, no action indicated.

### services/conveyancing.py — 13 PDF fetchers + free-tier path (paid PDF + free tool)

| # | Function (file:line) | Empty return | Collapse states possible | Caller distinguishes | Served surface | Channel |
|---|---|---|---|---|---|---|
| 1 | `_fetch_db_data` :539-578 | `_das=None`, `_lep=[]`, `_dcp=None`, `_heritage={empty}` | one try-block covers four fetches (:552-574): an exception mid-way leaves later results empty — S2/S7 collapse into S1/S9 for **lep_clauses, dcp_setbacks, heritage**; `[]` for `_lep` also means "no key_sites_clause" (S9, :568) | **partial** — DAs yes (None typed, :545); lep/dcp/heritage **no**: PDF merge at :805-817 treats empty heritage as no-heritage silently | paid PDF (LEP clauses, setbacks, heritage rows) | 🔴 paid |
| 2 | `_fetch_shadow` :580-590 | None | S4 (no prop_id, :583) collapsed with whatever `get_shadow_risk` failure returns — S2/S7 | no (single None) | paid PDF shadow section | 🟡 paid (renders omitted/not-assessed) |
| 3 | `_fetch_bushfire` :592-608 | None | S2/S7 → None (:606-608); inner `_query_rfs_bfpl` result states untyped here | partial — docstring contract: None renders "Not assessed" never "Clear" (:595) | paid PDF bushfire row | 🟢 paid |
| 4 | `_fetch_anef` :610-624 | `{"status":"failed"}` | typed | yes | paid PDF ANEF row | 🟢 paid |
| 5 | `_fetch_contributions` :626-644 | `{"status":"failed"}` | S4 (no prop_id, :634) collapsed with S2 into "failed" — both render Not assessed | partial (rendering identical, cause lost) | paid PDF contributions | 🟢 paid |
| 6 | `_fetch_corridors` :646-660 | None | S2/S7 → None; sub-checks all become "Not assessed" | yes (per contract :648-649) | paid PDF corridors | 🟢 paid |
| 7 | `_fetch_tod` :662-675 | `(None, None)` | S2/S7 → section **omitted** from the PDF (:668-669) — the reader cannot tell "checked, not in TOD" from "never checked"; DQ-36's own subject-matter | **no** at the reader level | paid PDF TOD section | 🔴 paid |
| 8 | `_fetch_structures_records` :677-690 | `(None,"failed")` | typed | yes | paid PDF records | 🟢 paid |
| 9 | `_fetch_climate` :692-711 | `{"state":"unavailable"}` | four states kept distinct by design | yes | paid PDF climate | 🟢 paid |
| 10 | `_fetch_mine_subsidence` :713-726 | `{"status":"failed"}` | typed ("empty" = checked clear) | yes | paid PDF | 🟢 paid |
| 11 | `_fetch_contaminated` :728-741 | `{"status":"failed"}` | typed | yes | paid PDF contaminated-land row | 🟢 paid |
| 12 | `_fetch_servicing` :743-757 | `{"status":"failed"}` | typed | yes | paid PDF servicing | 🟢 paid |
| 13 | `_fetch_coastal` :759-775 | `{"status":"outside"|"failed"}` | typed (outside = checked non-intersection) | yes | paid PDF coastal | 🟢 paid |
| 14 | free-tier `parse_controls(get_raw_controls(...))` :301 | zone/height/fsr = None | Portal outage (S2) vs control-not-mapped (S9) both → null fields; `_compute_confidence` :981-996 scores them identically low | partial (confidence drops, cause lost) | free tool + cached into PDF | 🟡 free+paid |
| 15 | `_load_pipeline_cache` :916-940 | dict or None | **no age filter on the cache read (:927-930)** — S6 undetectable; a PDF can be built from an arbitrarily old free-tier run | no | paid PDF (whole report base) | 🔴 paid |
| 16 | `get_unique_overlays` consumption :310-321 | `[]` overlays | S3 typed via `covered_layers` + confidence cap :998-1001 | yes | free + paid | 🟢 |

### Satellite services (free tool pages + paid PDF wrappers)

| # | Function (file:line) | Empty return | Collapse states possible | Caller distinguishes | Served surface | Channel |
|---|---|---|---|---|---|---|
| 17 | `flood_truth.run_flood` cache :1716-1751 | cached row | **no age filter** (`ORDER BY run_date DESC LIMIT 5`, :1718-1720) AND the stale outputs are re-written under the new report_id with **today's** run_date (:1730-1734) — S6 re-labelled as current | no | flood tool + PDF flood | 🔴 free+paid |
| 18 | `flood_truth._fetch_bom_peak` :591-616, `_fetch_bom_flood_history` :631-687 | `(None,None)` / `[]` | S1 vs S2 collapsed inside BOM history; gauge availability separately tracked (:1268) so confidence unaffected | partial | flood history list | 🟡 |
| 19 | `shadow_detector._build_scenario_list` :264-269 | scenario with `shadow_length_m=0.0`, `overlaps=False` | **a scenario whose computation errored (S7) is served as numeric "no shadow"** — polygon nulled but the numbers and the overlap verdict stay | **no** — and it feeds `_adg_compliant` | shadow tool scenarios | 🔴 free |
| 20 | `shadow_detector._adg_compliant` :305-308 | `True` | noon scenario missing or errored → "can't assess — default to compliant" (comment admits it, :307); via row 19 an errored noon serves **adg_compliant: true** | no | shadow tool ADG verdict | 🔴 free |
| 21 | `shadow_detector._get_height_limit` :165-250 | `DEFAULT_HEIGHT_M, "default"` | S2/S3/S7 all land in "default"; but height_source is served, audit-labelled honestly (:469-474), and confidence drops to "low" (:453) | partial (default typed, cause lost) | shadow tool | 🟡 free |
| 22 | `solar_yield._parse_solar_response` :390-398 | `_no_coverage_output()` | **schema-validation failure (S7) deliberately collapsed into no-coverage (S5)** — log-only (:393); user sees "no coverage" for a Google schema drift | no | solar tool | 🔴 free |
| 23 | `solar_yield._check_heritage` :467-495 | `False` | DB failure (S2) → `is_heritage=False` "safe default" (:490-492) — a heritage property renders non-heritage on the report | no | solar tool heritage flag | 🔴 free |
| 24 | `solar_yield._clip_panels_to_lot` :227-242 + confidence :590-597 | unclipped `sp` | shapely missing / invalid polygon → clip silently skipped; confidence checks polygon **provided** (:592), never `_lot_clipped` (:294) → **"high" confidence on whole-complex numbers** | no | solar tool numbers + badge | 🔴 free |
| 25 | `solar_yield._lookup_neighbour_hob` :498-529 | None | S1 vs S2 collapsed (cross-sell teaser only) | no | solar tool teaser | 🟢 free |
| 26 | `threat_radar._fetch_das` :180-211 + check :290-357 | half-empty `apps` | **one endpoint down (S2-partial) while the other succeeds → `any_success=True`, `last_checked`+seen-set updated (:346-357), count served from half the data**; only both-failed is typed (:308-337) | partial (per-endpoint errors reach the audit trail :297-306, not the user response) | threat-radar alert emails | 🔴 free |
| 27 | `threat_radar._filter_nearby` :214-229 | apps dropped | missing/zero coords (S8) silently skipped (:222, :227-228); page cap 200/no pagination (:192-193) truncates silently (S8) | no | threat-radar alerts | 🔴 free |
| 28 | `threat_radar._lookup_property_context` :60-90 | `{zone:None, tod:None}` | S2 collapsed with S1 (:85-86) | no | alert context block | 🟡 free |
| 29 | `climate_risk_score._normalize_bushfire` :218-259 | `present=False, confidence="high"` | overlay empty (S1/S3) + **RFS fallback raised (S2, swallowed :243-247)** → "Bushfire Prone Land: No" at **"high"** — item 1's subject | no (`available` stays True; heat's `available=False` pattern :341-352 not used) | climate tool hazard card | 🔴 free |
| 30 | `climate_risk_score._normalize_flood/coastal/landslide/fire_history` :201-334 | `present=False, confidence="high"` | overlay empty: S1 vs S3 indistinguishable — spatial_overlays ingest is geographically partial (bushfire's own docstring :225-227 says bbox-limited) yet all four hardcode "high" (:213, :297, :314, :332) | no | climate tool hazard cards | 🔴 free |
| 31 | `terrain_analysis` endpoint :1300-1326 | — | fails loud (500, :1324-1326); interpretive Nones internal | yes | terrain sections | 🟢 |
| 32 | `granny_flat._detect_structures_samgeo` :455-464 | `[]` | detection failure (S7) vs no structures (S1) — **mitigated by the mandatory human-confirm gate** and typed `confidence='error'` rows (:790-793) | partial by design | granny tool | 🟡 free |
| 33 | `granny_flat._fetch_sd_setbacks` :170-221 | None | no-LGA (S4) vs error (S2) collapsed | no | granny tool setback hints | 🟡 free |

### services/portal_constraints.py (feeds Site Report + conveyancing wrappers)

| # | Function | Empty return | Collapse states | Caller distinguishes | Channel |
|---|---|---|---|---|---|
| 34 | `fetch_mine_subsidence` :112-141, `fetch_contaminated_land` :144-178, `fetch_anef` :201+, etc. | None = checked-clear; failures **raise** | typed-by-exception: S1 → None, S2/S7 → raise; the conveyancing wrappers convert to `"failed"`/`"empty"` | yes (when callers catch — the conveyancing wrappers do; any caller that swallows to None re-collapses) | site report + paid PDF 🟢 |
| 35 | `fetch_sepp_exclusions` :412-449 | per-layer `bool|None` | per-layer typed; all-failed → None | yes | screening 🟢 |

## Counts

- **Return paths examined: 35** (13 conveyancing fetchers, 3 conveyancing-path extras,
  14 satellite paths, 2 portal groups, 3 support paths).
- **🔴 collapse served as an affirmative claim: 11** (rows 1, 7, 15, 17, 19, 20, 22, 23,
  24, 26+27 counted once per product path, 29+30 counted once per file).
  Of these, **3 sit on the PAID conveyancing channel** (rows 1, 7, 15) and 8 on free tools.
- **🟡 partially mitigated (typed somewhere, cause lost): 8.**
- **🟢 typed / fail-loud: 16.**
- By product: conveyancing PDF is the best surface (10 of its 13 fetchers typed — the
  three-state doctrine landed there); climate_risk_score is the worst per-capita (5 of 6
  hazard normalizers hardcode "high" on empty); shadow's errored-scenario→0.0 chain is the
  single sharpest silent-wrong-number (an S7 becomes a served ADG verdict).
- **Stale cache (S6) is systemically unhandled**: neither cache read has an age filter
  (conveyancing :927-930, flood :1718-1720), and flood re-stamps stale outputs with a
  fresh run_date.
- threat_radar has **no confidence field at all** (whole file — nothing to cap when
  completeness degrades); noted for the lint (item 2), design deferred per the brief.

## Notes for the language ladder (flag, don't fix — none changed here)

`grep -n "verified" <nine census files>` (run 2026-08-03), classified:
- **Served user-facing text — 2 hits, both in granny_flat, both NEGATIVE uses:**
  `services/granny_flat.py:1023` "The … minimum under SEPP Housing 2021 (cl 53) could not
  be verified." and `:1171` "Lot area could not be verified — eligibility is unconfirmed."
  The ladder bans the umbrella word; a negative use still anchors the frame that other
  outputs ARE "verified". Flagged for the ladder pass, not changed here.
- Internal comments/docstrings only (not served): `conveyancing.py:326`,
  `flood_truth.py:269`, `shadow_detector.py:7`, `portal_constraints.py:287,731,750`.
