# Sydney Water Growth Servicing Plan (GSP) — smoketest findings

**Date:** 2026-07-25 · **Branch:** `feat/sydney-water-servicing`
**Status:** Download + structure validation + point-in-polygon smoketest PASSED. No DB writes yet.

## What was verified (not assumed)

Three public GeoJSON files pulled from the Sydney Water CDN (no auth, one GET each):

| File | Bytes | Features | Geometry | CRS |
|---|---|---|---|---|
| `GSP_WW.json` (wastewater) | 3,271,497 | 205 | Polygon | none → WGS84 lon/lat |
| `GSP_DW.json` (drinking water) | 3,257,724 | 192 | Polygon | none → WGS84 lon/lat |
| `GSP_AdditionalComments.json` | 56,994 | 4 | Polygon | none → WGS84 lon/lat |

Base URL: `https://www.sydneywater.com.au/content/dam/sydneywater/applications/gsp/`
Coordinate range: lon 150.62–151.21, lat −34.61 to −33.57 (Greater Sydney). Confirms lon/lat order.

Counts and field names match the strategy doc exactly (`plans/strategic/site-acquisition-servicing-intelligence-2026.md`).

## Field reality (drives the serviceability logic)

- **`SWC_Planning_Project_Stage`** — 5 values, the readiness ladder:
  `Design & Deliver` (73) · `Strategic Planning` (36) · `Concept Planning` (32) ·
  `Option Planning` (23) · `Growth precinct boundary. No current Sydney Water projects…` (41).
- **`Special_Comments`** — only **12/205** WW features carry a real
  "capacity and timescale constraints" note. DW file has **no** `Special_Comments` field at all.
- **`Indicative_DSP_Full_Prices_(per_ET)`** — the $ figure is embedded in an HTML blob
  (`$17,686.52 Refer to…<a>`); needs a leading-`$` regex. `$0` is a valid value; 14 rows carry no figure.
- **`Indicative_Timeframe_by_Financial_Year(FY)`** — free text, messy (`FY26`, `FY26-30, Beyond FY30`,
  one typo `YF28`). Treat as a display string, not a parseable date.
- **`Existing_Servicing_Information`** — uniformly `"Refer to GSP2025-2030 PDF document."` (dead pointer, as the doc warned).

## The honest 3-state (+overlay) mapping — implemented in the smoketest

| Polygon stage / condition | Status code | User-facing wording (no "serviceable/ready") |
|---|---|---|
| `Design & Deliver` | `IN_DELIVERY` | Trunk servicing in delivery — subject to feasibility and connection works |
| `Concept` / `Option` / `Strategic Planning` | `PLANNED` | Servicing planned — timeframe indicative only |
| `Growth precinct boundary. No current…` | `NO_CURRENT_PROJECT` | In a growth precinct but no current Sydney Water servicing project |
| `Special_Comments` capacity note present | `CONSTRAINED` (overlay) | Capacity/timescale constraints flagged — … |
| point in no polygon | `NOT_IN_PRECINCT` | Not in a GSP growth precinct — capacity confirmed only via a site-specific Section 73 feasibility |

`NOT_IN_PRECINCT` is the established-suburb gap surfaced honestly — **not** a negative status.

## Smoketest result

`scripts/smoketest_gsp_servicing.py` — loads both layers into a shapely STRtree, resolves lon/lat.
Test points are derived from the real polygon geometry (representative points), not guessed addresses.

```
Loaded WW=205 polygons, DW=192 polygons
[OK] Leppington point → Leppington WW polygon (WW87, South West Growth Area, FY26, DSP $17,686.52/ET)
[OK] Outside point (149.0,-33.0) → NOT_IN_PRECINCT (no false status)
[OK] Constrained polygon → CONSTRAINED status
SMOKETEST PASSED
```

Notable real output: **Leppington North is `Design & Deliver` for WW *and* capacity-constrained** —
the "capacity present ≠ ready to build" case, with a live $/ET charge. Exactly the signal no competitor tool shows.

## Licensing gate (unchanged, still the one real blocker)

Data carries "© Sydney Water, all rights reserved" + "guide only, no warranty" disclaimer; it is **not**
open-data licensed. Internal analysis = low risk. Commercial redistribution needs a licence/partnership
(contact `developerservices@sydneywater.com.au`) or the show-derived-answer-and-link-back pattern. Legal check before shipping externally.

## Next step: Phase-1 ingest into `spatial_overlays`

The existing pattern (`scripts/ingest_spatial_overlays.py`) already does GeoJSON→MultiPolygon WKT via
`shapely.geometry.shape` and inserts into
`spatial_overlays(instrument_key, lga_name, layer_type, value, value_numeric, currency_date, source_oid, geom, synced_at)`.

Proposed layer_types: `sydney_water_ww_servicing`, `sydney_water_dw_servicing`.
- `value` = status code (IN_DELIVERY / PLANNED / NO_CURRENT_PROJECT / CONSTRAINED)
- `value_numeric` = parsed DSP $/ET
- `source_oid` = `SWC_Unique_Identifier` (WW87 / DW192)
- `currency_date` = snapshot date of the GSP25 extract; refresh annually.
- Keep the raw stage/timeframe/growth-area/commentary in a JSON attributes column if one exists, else a side table.

Then a per-address lookup = one point-in-polygon query against those rows, wrapped in the honest-wording layer.
Requires a DB backup + `db_safety_check.sh` per project rules before any write.
