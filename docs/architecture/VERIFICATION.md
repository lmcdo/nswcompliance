# Evidence for the diagrams

Every box, arrow and number on [SYSTEM_TECHNICAL.md](SYSTEM_TECHNICAL.md) and
[SYSTEM_INTEGRATED.md](SYSTEM_INTEGRATED.md) has a row here. Each row gives the query or the
file and line that produced it, and the date it was produced.

This file exists so a hostile reader does not have to take my word for anything. If a row's
evidence does not reproduce, the diagram is wrong and should be corrected.

**Code reference point:** `origin/main` at commit `af7982a8`. Reproduce any file claim with
`git show af7982a8:<path>`.
**Database:** the single production Supabase instance. All queries below were run in a
**read-only session** — the connection was opened with `set_session(readonly=True)` and
`SET statement_timeout = 30000`, so no query in this file could write even by accident.

Two dates appear in the tables. **2026-08-09** means I ran it that day. **2026-08-08** means it
was measured by someone else on that date and I am citing rather than re-running; there are only
two such figures, both flagged in section 6.

---

## 1. Database counts — all live-measured 2026-08-09

| Claim on the diagram | Query | Result | Measured |
|---|---|---|---|
| 117 tables | `SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'` | 117 | 2026-08-09 |
| `spatial_overlays` 1,088,573 shapes | `SELECT count(*) FROM spatial_overlays` | 1088573 | 2026-08-09 |
| 25 layer types | `SELECT count(DISTINCT layer_type) FROM spatial_overlays` | 25 | 2026-08-09 |
| `nsw_cadastre_lots` 3,220,617 parcels | `SELECT count(*) FROM nsw_cadastre_lots` | 3220617 | 2026-08-09 |
| `lot_search_index` 3,126,418 lots | `SELECT count(*) FROM lot_search_index` | 3126418 | 2026-08-09 |
| 181,737 certificates | `SELECT count(*) FROM complying_development_certificates` | 181737 | 2026-08-09 |
| 128 councils, certificates | `SELECT count(DISTINCT council_name) FROM complying_development_certificates` | 128 | 2026-08-09 |
| Certificates run 2018 to 2026 | `SELECT min(determination_date), max(determination_date) FROM complying_development_certificates` | 2018-07-09 → 2026-08-07 | 2026-08-09 |
| 62,016 development applications | `SELECT count(*) FROM development_applications` | 62016 | 2026-08-09 |
| Applications start May 2025, not 2018 | `SELECT min(determination_date), max(determination_date) FROM development_applications` | 2025-05-23 → 2026-08-07 | 2026-08-09 |
| 243,753 transaction records combined | 181737 + 62016, from the two rows above | 243753 | 2026-08-09 |
| `regulatory_provisions` 55,696 clauses | `SELECT count(*) FROM regulatory_provisions` | 55696 | 2026-08-09 |
| 19,957 served | `SELECT count(*) FROM regulatory_provisions WHERE is_current = TRUE AND v2_is_actionable = TRUE` | 19957 | 2026-08-09 |
| Only 2,069 carry a number | `... AND v2_has_numeric_value = TRUE` added to the above | 2069 | 2026-08-09 |
| `dcp_setback_controls` 1,071 | `SELECT count(*) FROM dcp_setback_controls` | 1071 | 2026-08-09 |
| 989 live | `SELECT count(*) FROM dcp_setback_controls WHERE is_current = TRUE` | 989 | 2026-08-09 |
| 30 councils | `SELECT count(DISTINCT lga) FROM dcp_setback_controls` | 30 | 2026-08-09 |
| 16 control types | `SELECT count(DISTINCT control_type) FROM dcp_setback_controls` | 16 | 2026-08-09 |
| All 1,071 have the source sentence | `SELECT count(*) FROM dcp_setback_controls WHERE source_text IS NOT NULL AND length(source_text)>0` | 1071 | 2026-08-09 |
| Only 42 have a clause join | `SELECT count(*) FROM dcp_setback_controls WHERE provision_id IS NOT NULL` | 42 | 2026-08-09 |
| Only 365 have an effective date | `SELECT count(*) FROM dcp_setback_controls WHERE effective_date IS NOT NULL` | 365 | 2026-08-09 |
| `lep_land_use_table` 18,196 / 26 councils | `SELECT count(*), count(DISTINCT lga) FROM lep_land_use_table` | 18196, 26 | 2026-08-09 |
| `property_reports` 981 stored runs | `SELECT count(*) FROM property_reports` | 981 | 2026-08-09 |
| Report runs by product | `SELECT product, count(*) FROM property_reports GROUP BY 1` | shadow 539, flood 319, solar-yield 63, bushfire 60 | 2026-08-09 |
| 774 ingest runs in 7 days | `SELECT count(*) FROM etl_metadata WHERE created_at > now() - interval '7 days'` | 774 | 2026-08-09 |
| 128 councils zoning coverage | `SELECT count(DISTINCT lga_name) FROM spatial_overlays WHERE layer_type='zone'` | 128 | 2026-08-09 |
| Heritage 127, lot size 127 | same query with `layer_type` in `('heritage','lot_size')` | 127, 127 | 2026-08-09 |
| Floor space 65, height 75, landslide 6 | same query with `layer_type` in `('fsr','height','landslide')` | 65, 75, 6 | 2026-08-09 |
| Bushfire + fire history 263,276 shapes, no currency date | `SELECT layer_type, count(*), max(currency_date) FROM spatial_overlays WHERE layer_type IN ('bushfire','fire_history') GROUP BY 1` | bushfire 225688 / NULL; fire_history 37588 / NULL | 2026-08-09 |
| Last map sync 13 Apr – 8 Jul 2026 | `SELECT min(synced_at)::date, max(synced_at)::date FROM spatial_overlays` | 2026-04-13 → 2026-07-08 | 2026-08-09 |
| `cdc_lot_link` 181,750 rows | `SELECT count(*) FROM cdc_lot_link` | 181750 | **2026-08-10** |
| …matched to a lot, 98.1% | `SELECT count(*) FROM cdc_lot_link WHERE match_status='matched'` | 178259 | **2026-08-10** |
| …point not inside any lot | `… WHERE match_status='no_lot_at_point'` | 3466 | **2026-08-10** |
| …no coordinates to look up | `… WHERE match_status='no_coordinates'` | 25 | **2026-08-10** |
| Distinct lots with an approval | `SELECT count(DISTINCT lotidstring) FROM cdc_lot_link WHERE lotidstring IS NOT NULL` | 128098 | **2026-08-10** |
| `development_type` double-encoded on 5.9% | `SELECT jsonb_typeof(development_type), count(*) FROM complying_development_certificates GROUP BY 1` | array 171002 · **string 10748** | **2026-08-10** |
| …and all 10,748 decode | `SELECT count(*) FILTER (WHERE jsonb_typeof((development_type #>> '{}')::jsonb)='array') FROM complying_development_certificates WHERE jsonb_typeof(development_type)='string'` | 10748 | **2026-08-10** |
| Certificates grew overnight | `SELECT count(*) FROM complying_development_certificates` on two days | 181,737 → **181,750** | 08-09 → 08-10 |

**Full layer breakdown** (rows · councils · newest currency date), from
`SELECT layer_type, count(*), count(DISTINCT lga_name), max(currency_date) FROM spatial_overlays GROUP BY 1`,
run 2026-08-09:

biodiversity 394,243 · 79 · 2026-03-27 — bushfire 225,688 · 0 · none — riparian 92,340 · 66 ·
2025-11-21 — zone 68,046 · 128 · 2026-04-02 — flood 42,572 · 72 · 2026-04-30 — lot_size 41,362 ·
127 · 2026-04-02 — heritage 40,141 · 127 · 2026-04-10 — height 40,094 · 75 · 2026-04-17 —
fire_history 37,588 · 0 · none — fsr 34,279 · 65 · 2026-06-12 — landslide 17,483 · 6 ·
2019-12-06 — wetlands 14,473 · 36 · 2025-11-21 — acid_sulfate 9,013 · 51 · 2026-02-27 — and
twelve smaller layers.

---

## 2. Code structure — all checked 2026-08-09 at `af7982a8`

| Claim on the diagram | Evidence | Measured |
|---|---|---|
| 76 Python modules in `services/` | `ls services/*.py \| wc -l` → 76 | 2026-08-09 |
| One FastAPI application | `grep -rln "FastAPI(" services/` → only `services/compliance_api_server.py` | 2026-08-09 |
| 20 routers mounted | `services/compliance_api_server.py:78-97`, twenty consecutive `app.include_router(...)` lines | 2026-08-09 |
| Routes sit under `/pipeline` | `services/shadow_detector.py:93` — `APIRouter(prefix="/pipeline", tags=["satellite"])`. Three other prefixes exist: `/pipeline/lec`, `/api/proxy`, `/api/telegram` | 2026-08-09 |
| 32 distinct pipeline routes | `grep -rhoE '@router\.(get\|post)\(\s*"[^"]+"' services/ \| sort -u \| wc -l` → 32 | 2026-08-09 |
| 140 Next.js API routes | `find frontend-nextjs/app/api -name route.ts \| wc -l` → 140 | 2026-08-09 |
| 123 pages | `find frontend-nextjs/app -name page.tsx \| wc -l` → 123 | 2026-08-09 |
| 10 report surfaces | `ls frontend-nextjs/app/reports/` → bushfire, conveyancing, flood, granny-flat, intelligence-brief, pre-da-history, shadow, solar-yield, threat-radar, plus the index page | 2026-08-09 |
| 8 Stripe checkout routes | `find frontend-nextjs/app/api/stripe -name route.ts` → eight `checkout/*` plus `webhook` | 2026-08-09 |
| 3 internal review surfaces | `ls frontend-nextjs/app/internal/` → dcp-review, setback-review, leads | 2026-08-09 |
| `intelligence_brief.py` 4,357 lines | `wc -l services/intelligence_brief.py` | 2026-08-09 |
| `conveyancing.py` 13 parallel fetchers | `grep -c "    def _fetch_" services/conveyancing.py` → 13, at lines 626–810 | 2026-08-09 |
| DCP intake scripts exist | `scripts/r2_monitor.py`, `dcp_extract_changed.py`, `dcp_preflight.py`, `dcp_commit_approved.py`, `derive_precinct_keys.py`, `dcp_watchdog.py`, `run_monitors.py` — all present | 2026-08-09 |
| A human approves before DCP rows land | `scripts/run_monitors.py:39` runs `dcp_extract_changed.py --review`; the commit step at line 55 is a separate monitor running `dcp_commit_approved.py --commit` | 2026-08-09 |

---

## 3. The arrows

Only drawn where a call from A to B can be pointed at in code.

| Arrow | Evidence | Measured |
|---|---|---|
| Browser layer → NSW Planning Portal, **direct, no Python** | `frontend-nextjs/lib/nsw-planning-portal.ts:386` sets `BASE_URL = 'https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi'`; 19 `fetch(` calls in that one file | 2026-08-09 |
| Browser layer → NSW ArcGIS, direct | same file, lines 1165, 1194, 1204, 1218, 1224–1226 — `mapprod1/2/3.environment.nsw.gov.au` | 2026-08-09 |
| Browser layer → SIX Maps land value, direct | same file, line 387 — `VALUATION_URL = 'https://maps.six.nsw.gov.au/.../Valuation/MapServer/5/query'` | 2026-08-09 |
| Property profile → portal service | `frontend-nextjs/app/api/property/profile/route.ts:2` imports `NSWPlanningPortalService` | 2026-08-09 |
| Profile → lot dimensions from polygon | same file, line 3 imports `calculateLotDimensions` | 2026-08-09 |
| Profile is rate limited, 20/min | same file, line 21 — `checkRateLimit(..., 20, 60_000)` | 2026-08-09 |
| Next.js → FastAPI | `PYTHON_API_URL` referenced in 15 files under `frontend-nextjs/app` | 2026-08-09 |
| Shadow report → `/pipeline/shadow` | `services/shadow_detector.py:527` — `@router.post("/shadow")`, prefix at line 93 | 2026-08-09 |
| Python → Google Solar | `solar.googleapis.com` appears in `services/` | 2026-08-09 |
| Sentinel-2 → `pre_da_history.py` **only** | `services/pre_da_history.py:66` sets `ELEMENT84_URL = "https://earth-search.aws.element84.com/v1"`; line 501 requests `collections=["sentinel-2-l2a"]` | 2026-08-09 |
| Sentinel-1 → `drawdown_verify.py` **only** | `services/drawdown_verify.py:250` — `_find_sentinel1_scenes`, using `asf_search` (Alaska Satellite Facility). No hardcoded host | 2026-08-09 |
| Shadow uses **no** imagery | `grep -rn "sentinel\|element84\|stac" services/shadow_detector.py services/shadow_model.py` → zero matches. The Sentinel-2 module was deleted in commit `c6d64edb`, "remove the adjacent-lot construction check from the product (#886)" | 2026-08-09 |
| Flood queries **no** SAR | `services/flood_truth.py:120-126` — the module nulls every `sar_*` field and its execution manifest records that the query was not made | 2026-08-09 |
| Python → other gov feeds | `services/` calls `www.bom.gov.au`, `www.rfs.nsw.gov.au`, `www.valuergeneral.nsw.gov.au`, `www.sydneywater.com.au`, `legislation.nsw.gov.au`, `www.austlii.edu.au`, `firms.modaps.eosdis.nasa.gov`, `ows.dea.ga.gov.au` | 2026-08-09 |
| R2 storage | `pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev` referenced from both `services/` and `frontend-nextjs/`; `_upload_to_r2` at `services/conveyancing.py:910` | 2026-08-09 |
| Cadastre → lot search index | Both tables carry `lotidstring`; `lot_search_index` also carries `zone_code`, `lep_height_m`, `lep_fsr` — cadastre joined to planning attributes | 2026-08-09 |

---

## 4. Unverified — drawn dashed, and why

Each line below is on a diagram as a dashed edge or a grey box. Nothing unverified is drawn as
though it were solid.

| Marked unverified | What I tried | Why it did not resolve |
|---|---|---|
| **Trigger.dev → FastAPI** | Found the outbound call: `frontend-nextjs/app/api/intelligence-brief/route.ts:22` posts to `https://api.trigger.dev/api/v1/tasks/intelligence-brief/trigger`; the same pattern is at `api/satellite/granny-flat/route.ts:43` and `api/satellite/pre-da-history/route.ts:22`. | The task definitions live in a **separate repository** (`plotdetect-agents`) which is not checked out here. I can show the call leaving; I cannot show what it calls next. Drawing that hop solid would be inventing structure. |
| **`doc_claims.py` as a blocking gate** | Read `scripts/doc_claims.py`. | Its own docstring says: *"Reports; blocks nothing. `--strict` exists but is wired into no hook and no gate."* Drawn grey dashed for that reason. |
| **Deployment liveness** | Confirmed in code that Next.js reaches FastAPI via `PYTHON_API_URL`, and that CI runs on push. | I did not call the deployed Railway or Vercel endpoints. Every arrow here is a **code** claim, not a claim that production is up right now. |
| **"Map layer sync — manual, no schedule"** | Listed every registered job in `scripts/run_monitors.py` (satellite freshness, legislation, r2_monitor, dcp_extract_changed ×2, dcp_commit_approved, dcp_watchdog, alerts dispatch, regulatory freshness, security, mutation health, refresh stats). None syncs spatial layers. `spatial_overlays.synced_at` clusters at 2026-04-13 and stops at 2026-07-08. | Absence from one registry plus a stalled timestamp is strong but not conclusive — a sync could run from somewhere I did not look. This is the weakest claim on the page and is labelled as such here. |

---

## 5. The seven gates

All six scripts confirmed present at `af7982a8` on 2026-08-09 by direct read and line count. The
seventh is the hook and CI wiring that runs them.

| Gate | File | Lines | What it does, in its own words |
|---|---|---|---|
| Falsifiability / plant-restore | `scripts/falsifiability.py` | 588 | *"Plant-restore harness for falsifiability proofs"* — plants a defect, confirms the test goes red, restores the file byte-identically. |
| Schema contract | `scripts/validate_schema_contract.py` | 632 | Compares every SQL identifier written in code against the live database schema. |
| Fabricated verdicts | `scripts/lint_fabricated_verdicts.py` | 267 | Asks *"whether a user-facing VERDICT is backed by data the emitting component actually receives"*. |
| Liability language | `scripts/liability_language_check.py` | 212 | Scans changed lines in user-facing files for wording that could create liability under Australian Consumer Law s18. |
| QA report | `scripts/qa_gate.py` | 1,544 | Validates a structured QA report against tier requirements and binds it to a commit hash. |
| Doc claims | `scripts/doc_claims.py` | 1,120 | Checks path, version and dependency claims in documents against code. **Observation mode.** |
| Hook + CI wiring | `.githooks/pre-push`, `.github/workflows/gates.yml`, `.github/workflows/main-red-alarm.yml` | — | Runs the above locally on push and again server-side on pull request and on push to main. |

`gates.yml` opens with a mapping table accounting for every `pre-push` step, including the two
it deliberately drops and the one — the push-to-main guard — it marks as a **GAP** because it is
not portable to CI. That is a fair thing to point at in an interview: the file documents its own
hole rather than implying complete coverage.

---

## 6. Disagreements found between documents and the database

Logged rather than silently resolved. Each is a case where a committed document says one thing
and the live database or code says another, checked 2026-08-09.

| Document says | Reality says | Verdict |
|---|---|---|
| `docs/ARCHITECTURE.md` (2026-05-02) and `.claude/docs/ARCHITECTURE.md` (2026-01-30): "47,818 provisions" | `regulatory_provisions` = 55,696. **47,818 is the exact row count of `document_id_backup`**, a backup table. | Both architecture docs wrong. Superseded by this set. |
| `docs/WHAT_TO_SELL_AND_WHY_2026-08.md` (2026-08-08): "156,000 approved building certificates" | 181,737 | Doc understates by roughly 26,000. `STRATEGY_REVIEW_2026-08-08.md` gives 181,737, which matches live. |
| `services/CLAUDE.md`: all five satellite products "not started" | All five have shipped modules, routers and report pages; `property_reports` holds 981 runs across four of them. | Doc stale on that table. Not used as an evidence source anywhere in this set. |
| A plain `grep -rl "sentinel" services/` suggests six modules use satellite imagery | Two do. In `bushfire_prescreen.py`, `cdc_screen.py` and `solar_yield.py` the word means a **sentinel value**, a programming term unrelated to satellites. | Near-miss, caught by opening each file. Would have put a false edge on the diagram — the same class of error as the "Threat Radar shares the Sentinel-2 pipeline" line that misled three sessions. |
| `STRATEGY_REVIEW_2026-08-08.md` §2: 25 layer types, 1,088,573 shapes | 25 and 1,088,573 | **Agrees exactly.** |
| `STRATEGY_REVIEW_2026-08-08.md` §2: 1,071 controls, 30 labels, 16 types, 365 effective dates, 42 provision links | 1,071 / 30 / 16 / 365 / 42 | **Agrees exactly.** |

The two figures cited rather than re-measured, both dated **2026-08-08** and both from
`STRATEGY_REVIEW_2026-08-08.md`: the test counts (3,925 Python, 1,034 frontend) and the shadow
calibration result (0.206° altitude, 0.346° azimuth against a 0.50° mark set beforehand). The
calibration result appears on the integrated diagram as "0.21° of a 0.50° limit" and is
doc-sourced, not re-run here.

---

## 7. These three files were run through the project's own doc gate

`scripts/doc_claims.py` checks whether the file paths, version numbers and dependencies named in
a document actually resolve in the code. Run it against this set:

```
python scripts/doc_claims.py --docs docs/architecture/SYSTEM_TECHNICAL.md \
    docs/architecture/SYSTEM_INTEGRATED.md docs/architecture/VERIFICATION.md
```

On 2026-08-09 it returned **no path and no version findings against these three files.** The
seven dependency findings it reports are pre-existing repository issues about requirements files
and test imports, unrelated to this documentation.

It found one thing on the first run, worth recording because it shows the gate working and shows
its edge. An earlier draft cited the now-deleted Sentinel-2 module by its old path, as evidence
that shadow uses no imagery. The gate flagged that path as unresolvable — correctly, since the
file is gone — but it cannot tell the difference between a document naming a file that *should*
exist and one correctly asserting a file was removed. Both read as a dangling path. The row now
cites the deleting commit `c6d64edb` instead, which is better evidence anyway, and the gate is
clean.

Worth knowing if you extend these docs: **naming a deleted file, even to say it is deleted, will
trip this check.** Cite the commit that removed it.

---

## 8. What this file does not establish

It shows that each box and arrow corresponds to something real in the code or the database on
2026-08-09. It does not show that the system produces correct answers, that the deployed services
are running, or that the gates have caught anything since they were built. Those are different
questions needing different evidence, and conflating them is the exact failure the assurance
ladder exists to prevent.
