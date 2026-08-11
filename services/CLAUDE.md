# services/ — Python Backend Standing Rules

## Read These First (Satellite Product Work)
- `~/.claude/plans/ce-satellite-products-comprehensive.md` — **READ THIS FIRST.** Full tech stack, tool choices, licences, per-product specs, blockers, deployment architecture. GEE is not required.
- `~/.claude/plans/pipeline-ideas-log.md` — spike status, revenue models, bot run history
- `~/.claude/plans/biz-platform-strategy-spatial-vs-document.md` — product structure, moat, how satellite fits the platform
- `memory/project-cross-repo-architecture.md` — why products live here, not in plotdetect-agents

## Satellite Product Pipelines

Five satellite/ML products are built here. See `~/.claude/plans/pipeline-ideas-log.md` for full status.

### Products and their files

| Product | File | Status |
|---|---|---|
| Rooftop Solar Yield Underwriter | `solar_yield.py` | not started |
| Construction Shadow Ambush Detector | `shadow_detector.py` | not started |
| Neighbour Development Threat Radar | `threat_radar.py` | not started |
| Wet Season Flood Truth Engine | `flood_truth.py` | not started |
| Granny Flat Yield Predictor | `granny_flat.py` | not started |
| GEE client (shared) | `gee_client.py` | not started |

### Data sources per product

**Solar Yield** — **Primary path: Geoscape Buildings API Solar module** (panel presence, roof area, power estimate) at **$0.12/address** (12 credits × $0.01 on Team plan $300/month). Free tier: 1,666 lookups/month. Eliminates ML training entirely if Geoscape returns sufficient panel area data. Test first: sign up Geoscape Hub free tier, run 10 addresses, confirm whether polygon geometry or just Yes/No+kW estimate is returned. pvlib + PVGIS API for yield (free, no key). Heritage flag from Supabase. Fallback if Geoscape insufficient: Brisbane AU weights (`dbaofd/solar-panels-detection`) fine-tuned on NSW chips via GroundedSAM pseudo-labels. NOT GeoAI SolarPanelDetector (Davis CA only). NOT GeoDeep (AGPLv3, commercially incompatible).
> ⚠ **The above is the original PLAN, not what shipped.** `solar_yield.py` is a Google Solar API pass-through: it sums Google's per-panel `yearlyEnergyDcKwh`. Neither pvlib nor PVGIS is called. Do not cite them as the solar method. (Lane 1 grep, 2026-08-06; the solar method claim itself is Lane 5's item.)

**Shadow Detector** — pybdshadow (geometric shadow polygon; derives sun position internally from the modelled UTC instant) + zoning height limits from this DB + lot boundary from `/api/property/lot-geometry`.
> ⚠ **The Sentinel-2 adjacent-lot change check was REMOVED 2026-08-07 (§4h).** It returned a reading in **0 of 538** attempts, and even working it cannot answer the question: at 20 m SWIR a suburban lot is ~1 pixel, so it measured ~30–40 properties at once while the prose named one neighbour. `services/sentinel2.py` is deleted. Shadow queries no satellite imagery at all — do not re-add it, and do not describe shadow as a satellite product.
No GEE, no ML for shadow. **pvlib is NOT used** — it was named here and on served surfaces for months while never being imported anywhere in the repo (Lane 1 / D1, 2026-08-06). Do not reintroduce the name.
The Southern-Hemisphere direction caveat is CLOSED (#883, 2026-08-07): `tests/test_shadow_calibration.py` asserts it across latitude, season and hour against pvlib's independent NREL SPA, and `shadow_direction_deg` is now computed per address — it is no longer a stored constant. Calibration measured 0.206° altitude / 0.346° azimuth against a 0.50° pass mark committed before the first run.

**Threat Radar** — NSW ePlanning API (public, no auth): `https://api.apps1.nsw.gov.au/eplanning/data/v0/OnlineDA` and `/OnlineCDC`. Filter by CouncilName, filter results by Haversine distance in Python — coordinates (X/Y) are in the response. Pattern already implemented in `map-viewer-restructured/app/api/da/route.ts` in sibling project. No bulk ETL needed. Cache seen `PlanningPortalApplicationNumber` values in Supabase for dedup.
> ⚠ **Correction 2026-08-07:** this section previously read "same Sentinel-2 pipeline as Shadow Detector". `threat_radar.py` contains **zero** Sentinel-2 references — grep-verified — and never did. The false shared-pipeline claim is how the §4h surface census was written short: a doc that misstates the architecture hands the next session a false premise. Threat Radar is a lodged-DA feed, not an imagery product.

**Flood Truth** — Sentinel-1 RTC from Microsoft Planetary Computer (`sentinel-1-rtc`, free but requires `PC_SDK_SUBSCRIPTION_KEY` env var — verify free key availability before build). VH change detection against dry-season baseline (ratio > 1.25 = flood, NOT fixed dB threshold — no universal values exist). `odc-stac` with `groupby='solar_day'` for multi-temporal stacking. SEED EPI Flood WFS (`https://mapprod3.environment.nsw.gov.au/arcgis/services/Planning/Hazard/MapServer/WFSServer`) confirmed live, free. Note: Sentinel-1B dead Dec 2021–Mar 2025 — document gap in output.
> ⚠ **NOT BUILT.** Everything in the Sentinel-1 half of this paragraph is a FUTURE Phase-3B design, not running code. `flood_truth.py` makes no S1 query: it nulls every `sar_*` field and its execution manifest records `sentinel1_sar.queried = False`. The `ratio > 1.25` constant and the Planetary Computer catalogue address were deleted from the module on 2026-08-06 (Lane 1 / D2) precisely because they were unreachable. The live flood screen is EPI + EMS + JRC + WOfS + BOM + SES + study rasters + DEM. Do not cite S1/SAR as a flood source.

**Granny Flat** — **samgeo (MIT) + NSW SIX Maps 10cm (CC-BY, free).** Same pipeline as Solar Yield: download SIX Maps tile → SAM segmentation → filter by area/shape → intersect with lot boundary. ⚠ **MEASURED 2026-08-10 AND IT DOES NOT DO THIS.** Against human labels on 56 lots
across four councils it found **14 of 38** visible secondary structures (recall
**0.368**, 95% CI 0.23–0.53) and reported 15 that were not there (precision 0.483).
The pass mark, committed before any label existed, was recall ≥ 0.70 / precision ≥ 0.60.
The claim this sentence used to make — that it *"solves the small-structure gap that
Microsoft footprints (64.95% recall, 2013–2018) and OSM (20.1% Sydney completeness)
cannot"* — is inverted: 0.368 is roughly **half** the recall of the dataset it claimed
to beat, and that 64.95% was the stated reason for building this instead of buying it.
Recall is 0.30–0.42 in **every** council measured, including the "clean suburban lots"
band predicted at 70–80%, so it cannot be rescued by scoping. It is reliable on the
**main dwelling only** (46 of 50 placed correctly). See
`scripts/measure_structure_detection_recall.py` and `data/gf_recall_001_result.json`. User confirmation step mandatory: show detected footprints on aerial tile, user confirms before calculation runs. Geoscape Buildings API requires Team plan ($300/month) — Buildings not available on free tier, Clip tool costs credits even on free. Defer Geoscape until post-revenue. NSW Fair Trading bond data for rent: `https://www.nsw.gov.au/housing-and-construction/rental-forms-surveys-and-data/rental-bond-data`.

### GEE client

**GEE is not required for any product.** Do not build `gee_client.py`.
- Sentinel-2: Element84 Earth Search (free, no auth) via `pystac-client`
- Sentinel-1 RTC: Microsoft Planetary Computer (`planetary-computer` pip package)
- AlphaEarth: GCS bucket `gs://alphaearth_foundations` (CC-BY 4.0) if needed for v2 change detection

### Trigger.dev relationship

Long-running jobs (>60s Vercel timeout) run as thin Trigger.dev tasks in `plotdetect-agents/trigger/`.
Those tasks call endpoints in this services layer — they do not contain pipeline logic themselves.
Pattern: Trigger task → POST `/api/pipeline/solar-yield` → `solar_yield.py` does the work → returns JSON → Trigger task sends to Telegram or frontend.

### Report storage

Each product writes to its own Supabase table:
- `solar_yield_reports`
- `shadow_reports`
- `threat_radar_alerts`
- `flood_truth_reports`
- `granny_flat_reports`

Common envelope for all reports:
```json
{
  "product": "solar-yield",
  "version": "1",
  "address": "...",
  "lat": 0.0,
  "lng": 0.0,
  "run_date": "2026-04-04",
  "inputs": {},
  "outputs": {},
  "confidence": "high|medium|low",
  "data_sources": []
}
```

### Frontend
Reports UI lives at `frontend-nextjs/app/reports/` — separate route group with its own layout.
Non-compliance users see only the reports section. See `frontend-nextjs/CLAUDE.md` for layout details.
