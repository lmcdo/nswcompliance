# Electricity & utilities — Phase 1 coverage audit

Started 2026-08-19 on branch `claude/electricity-utilities-research-vd3enq`.
Purpose: decide whether the method in **arXiv 2606.21352** (Zhang &
Maharjan, "Urban Power Grid Topology and Hierarchy Identification from Open
Data") is worth applying to NSW — specifically, whether OSM `power=*`
density in each of our 28 Solar-Yield LGAs supports the paper's HDBSCAN /
MST / Dijkstra reconstruction.

## Prior context

A pivot memo from 2026-01
(`.claude/docs/history/2026-01-implementation/PLATFORM_PIVOT_OPPORTUNITIES.md`)
proposed **Renewable Energy Site Selection** as Opportunity 2 — targeting
solar/wind/battery developers with substation-proximity queries and
transmission-capacity data. Ranked runner-up; not built. That memo
predates the state government publishing similar tooling (see below).

## What the paper actually gives us

- **Method:** fuses OSM (power lines, poles, substations, transformers,
  land-use polygons, road network, building footprints) with government-
  published utility data (they use NVE in Norway).
- **Grid skeleton:** graph algorithm respecting voltage hierarchy, Dijkstra
  on road-intersecting potential points.
- **LV / last-mile:** HDBSCAN clusters buildings within a land-use polygon,
  MST within cluster along road distance, attach cluster to whichever is
  closer by road — nearest pole or nearest LV line.
- **Case study:** Alna, Oslo — 7,330 buildings, 2,787 utility poles,
  127 power lines, 8 substations. → **0.38 poles / building**.
- **Explicit caveat from the authors:** "100 % accurate reconstruction is
  impossible, particularly because the ground-truth data are missing for
  the last-mile connections." No accuracy number is reported for LV.

## What already exists in NSW (search-only, not fetched)

Every URL below is blocked by this container's egress proxy — findings are
from web-search summaries, not direct page reads. Verify before quoting.

| Resource | What it publishes | Access |
|---|---|---|
| [NSW Network Opportunities Map](https://data.nsw.gov.au/data/dataset/1-f1d4c73ef5df4c6a937d93618b264309) (DCCEEW × Ausgrid × Endeavour × Essential) | Substation hosting capacity for renewable connections | **View-only, no redistribution** |
| [Ausgrid DTAPR portal](https://www.ausgrid.com.au/about-us/regulation-and-compliance/network-planning/dtapr) | Zone substations, sub-transmission layers, DAPR PDFs | Web viewer + PDFs |
| [Endeavour Energy DAPR / Connection Opportunity Map](https://dapr.endeavourenergy.com.au/connections/) | Feeders, 132/66/33/22/11 kV sub-transmission and distribution, substations | Web viewer (Rosetta) |
| [Essential Energy Overhead Network Maps](https://www.essentialenergy.com.au/our-network/overhead-network-maps) | Overhead spans for regional NSW | PDFs + on-request GIS |
| [Essential Energy Overhead Spans on NSW Spatial Portal](https://portal.spatial.nsw.gov.au/portal/home/item.html?id=5a59e7941b324453a2cb80078bdcd3f9) | Overhead span geometry | ArcGIS item (licence TBD) |
| [REI Energy_Infrastructure MapServer](https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/REI/Energy_Infrastructure/MapServer) | Statewide NSW renewable-energy infrastructure | **ArcGIS REST** — same pattern as our current `spatial_overlays` feeds |
| [NSW_Electricity_Feeder_Lines MapServer](https://spatialportalarcgistst.dpie.nsw.gov.au/sarcgis/rest/services/FutureFarmingApp/NSW_Electricity_Feeder_Lines/MapServer/4) | Feeder lines statewide | ArcGIS REST — on a `-tst` portal (test env), verify prod URL |
| [Digital Atlas of Australia — Electricity Transmission Lines](https://digital.atlas.gov.au/datasets/digitalatlas::electricity-transmission-lines/about) | National HV transmission | Downloadable dataset |
| [Open Infrastructure Map — Australia](https://openinframap.org/stats/area/Australia) | AU total from OSM: 802 plants, 76,336 MW, 123,070 km lines | Free, OSM-derived |

**The material finding:** NSW already publishes HV/MV network topology
through the REI Energy_Infrastructure ArcGIS MapServer, on the same
platform our 27 existing `spatial_overlays` layers come from. The paper's
HV/MV reconstruction leg is largely redundant here — we can just query it.

The paper's *actual* remaining value in NSW is the LV / last-mile
reconstruction, which none of the state-published layers include.

## Implications for our product roadmap

1. **HV/MV substation proximity, capacity, feeder-name lookup** — solvable
   today by wiring the REI Energy_Infrastructure MapServer into
   `services/portal_constraints.py`, following the exact ArcGIS-REST
   pattern already used for the 27 planning layers. No paper method
   needed. This alone would deliver the substation-distance / hosting-
   capacity signal the 2026-01 pivot memo proposed for renewable
   developers.
2. **LV / grid-export-risk on Solar Yield** — this is where the paper's
   method matters. It attempts to infer which cluster of buildings shares
   an LV drop. In NSW that inference has no ground truth to validate
   against (Ausgrid/Endeavour/Essential do not publish LV feeder shapes),
   so we would ship an *inferred* signal and be bound by
   `.claude/rules/regulatory-data.md` and the language-audit rules — no
   "adequate", no "reliable", no "confirmed". The signal is directional at
   best.
3. **Renewable Energy Site Selection product** — the NSW NOM covers the
   headline use case already, view-only. Reselling the same picture with
   nicer UX is a UX play, not a data play. If we go here, our
   differentiator has to be the property-level integration with our
   compliance stack (zoning, heritage, bushfire, flood, portal
   constraints), not the grid data itself.

## What the audit couldn't run in this container

The script `phase1_coverage_audit.py` in this directory hits Overpass API
plus the two NSW ArcGIS endpoints. Every relevant host is blocked by the
egress proxy in the Claude Code on-the-web session:

```
overpass-api.de:443              → 403 Forbidden
overpass.kumi.systems:443        → 403 Forbidden
mapprod3.environment.nsw.gov.au  → EGRESS_BLOCKED
portal.spatial.nsw.gov.au        → EGRESS_BLOCKED
data.nsw.gov.au                  → EGRESS_BLOCKED
openinframap.org                 → EGRESS_BLOCKED
wiki.openstreetmap.org           → EGRESS_BLOCKED
digital.atlas.gov.au             → EGRESS_BLOCKED
```

Attempted 28 LGAs, 28/28 failed at the CONNECT tunnel. Results file was
therefore not written.

**To finish Phase 1**, either:

- Run the script from a local dev shell (the same one that runs
  `python -m pytest` today):
  ```
  source venv_linux/bin/activate
  python .claude/research/electricity-utilities-2026-08/phase1_coverage_audit.py
  ```
  Expected runtime: ~2 minutes (28 LGAs × 3 s rate-limit + Overpass
  latency). Writes `results.csv` and `results.md` next to the script,
  cached at `.cache/`.

- **Or** add the hosts above to the on-the-web session's egress allowlist
  and re-run this task. That's a one-time policy change, and every
  subsequent task that needs OSM or NSW spatial data will inherit it.

## Deliverables in this folder

| File | Status |
|---|---|
| `README.md` | this memo |
| `phase1_coverage_audit.py` | ready to run, offline against Overpass + NSW ArcGIS |
| `results.csv` | **not written** — audit couldn't reach hosts |
| `results.md` | **not written** — audit couldn't reach hosts |

## Next step recommendation

Two forks depending on how the audit reads:

**If Phase 1 shows OSM pole density < 25 % of Alna** in most NSW LGAs
(the likely outcome — Australian OSM `power=pole` coverage is patchy
outside mapping-party areas), then park the paper's method. Instead spike
a small integration:

1. Add `power_infrastructure` layer to `spatial_overlays` sourced from the
   REI Energy_Infrastructure MapServer.
2. Add "nearest zone substation" and "distance to sub-transmission" as
   fields on the property brief / Solar Yield output. Informational only,
   no adjective from the liability-audit list.
3. Measure whether users engage with the field before investing further.

**If Phase 1 shows a handful of dense-coverage LGAs** (Inner West, City of
Sydney, and a few inner suburbs are the plausible candidates), pick one
suburb inside a dense LGA where a DNSP-published LV shape is obtainable,
run the paper's Algorithm 1-3, and measure feeder-assignment accuracy
against ground truth. That is Phase 3 in the plan from the previous
message.

Either fork keeps the work bounded and reversible; neither commits us to
building a new user-facing surface before we know what the data supports.
