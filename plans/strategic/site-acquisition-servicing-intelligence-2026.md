# Site Acquisition & Servicing Intelligence — Strategy (2026)

## Executive Summary

The largest, most defensible opportunity in front of PlotDetect is **not** another
consumer report and **not** a fight with CoreLogic/Domain on "what a property is."
It is to sell **site-acquisition intelligence** to the professionals racing to build
under the NSW 2025 Low- and Mid-Rise (LMR) / Transport-Oriented Development (TOD)
reforms — and to win on the one data layer nobody has productised: **water/sewer
servicing capacity**.

Everyone can now tell a developer the *planning envelope* of an upzoned site
(Archistar, Landchecker, Feasly). That was commoditised the day the reforms dropped.
Two questions still decide whether a site can actually be built, and neither appears
in any competitor tool:

1. **Servicing** — can the site be connected to water/sewer feasibly, or is the
   catchment capacity-constrained? (A 15,000-home SW Sydney scheme is stalled on
   wastewater; Sydney Water flags whole areas as not-feasible-to-service within 5
   years.)
2. **Amalgamation** — which adjoining lots must combine to make a viable site, and
   which of those owners is likely to sell?

These are hyper-local, regulatory, infrastructure-bound problems — structurally
unattractive to global platforms, structurally perfect for PlotDetect. The buyer
(a developer) earns tens to hundreds of thousands of margin per deal, so
willingness-to-pay dwarfs any $49-report consumer. This is the segment that funds a
real business where B2C never could.

---

## The Strategic Reframe

| | Competitors sell | PlotDetect's white space |
|---|---|---|
| Frame | **What a property IS** — price, comparables, title, hazards | **What it COULD BECOME** + **what's CHANGING** |
| Market | Crowded (CoreLogic, Domain/REA, PriceFinder, Landchecker) | Under-served |
| PlotDetect fit | Weak (late, smaller) | Strong (upzoning, buildable yield, DA odds, terrain, cadastre) |

Climate/physical-risk data is **not** a moat — it is commodity owned by well-funded
incumbents (Cotality/CoreLogic, XDI, Climate Valuation, Jupiter, Moody's/RMS). The
moat is the **NSW planning + servicing layer** those players will never build.

---

## The Trend (the wave)

- NSW LMR/TOD reforms unlock **112,000 homes over 5 years** (~22,400 dwellings/yr).
  [NSW Gov](https://www.nsw.gov.au/ministerial-releases/low-and-mid-rise-policy-to-unlock-112000-homes-five-years)
- New controls apply within **800 m of 171 town centres and stations** across metro
  Sydney, Central Coast, Illawarra-Shoalhaven and the Hunter — dual-occs, terraces,
  townhouses, residential flat buildings. Up to 6 storeys within 400 m; 4–5 storeys
  400–800 m.
- Stage 1 (Jul 2024): dual-occ + semi-detached in **R2 across all of NSW**.
- The government's own bottleneck: sites won't get built without **amalgamation**
  (no mechanism to force it) and **infrastructure servicing** (capacity cliffs).
  [Egis analysis](https://www.egis-group.com/all-insights/is-the-nsw-government-s-low-mid-rise-housing-policy-going-to-achieve-its-target-the-devil-is-in-the-detail),
  [The Urban Developer](https://www.theurbandeveloper.com/articles/western-sydney-water-wastewater-greater-parramatta-olympic-peninsula-sewer-camelia)

At ~4 dwellings per missing-middle project, that's **~5,600 development sites/yr**
being selected and assembled in the reform footprint — each needing site selection
and a servicing check.

---

## The Insight (why the obvious play is dead)

"Tell people the planning envelope of an upzoned site" was commoditised on day one.
The information that still decides a deal — and that no tool surfaces — is
**serviceability** and **amalgamation + seller-likelihood**. Servicing is checked
today by **phoning Sydney Water (13 20 92)** or hiring an accredited Water Servicing
Coordinator, and reading the **Growth Servicing Plan** — there is no clean API and
the e-Developer platform is only being replaced in 2026. That difficulty *is* the
moat.

---

## Target Persona

Not homeowners, not selling agents. **Site-acquisition professionals:**

| Segment | Est. NSW seats | Notes |
|---|---|---|
| Residential infill developers / builder-developers (Gtr Sydney) | 2,000–4,000 | Active medium-density players |
| Development-focused buyer's agents / site sourcers | 500–1,000 | Niche, growing |
| BTR / co-living / institutional site analysts | 100–300 | Small, high-value |
| Planning & development consultancies (site DD) | 500–1,000 | Do this manually today |
| **Addressable seats** | **~3,000–6,000** | midpoint ~4,000 |

---

## The Product

**Site Acquisition Radar** — rank every developable lot-cluster across the 171
catchments, gated behind a professional subscription, plus a per-site deep report.

**The proprietary calculation — Site Acquisition Score (per lot-cluster):**

> uplift × buildable yield × **serviceability** × DA-approval odds × seller-likelihood

Every competitor can compute the first two. **Serviceability is the ingredient none
of them have**, and it is the one that determines whether a deal is real. That single
factor turns replicable planning data into a scarce signal worth a subscription.

---

## Build Scope (from codebase audit)

### Already have — reuse, don't rebuild
- **Cadastre polygons in PostGIS** (`nsw_cadastre_lots.geom`) → adjoining-lot /
  amalgamation query is a *small* net-new addition (`ST_Touches`/`ST_DWithin`), not a
  data project.
- **Upzoning envelope** (`services/upzoning_check.py`), **buildable yield**
  (`services/constraint_arithmetic.py`).
- **DA approval evidence** (`services/da_outcome.py`) + **LEC decisions**
  (`services/lec_collector.py`) → approval odds.
- **Valuer General sale dates** (`services/vg_comparables.py`) → owner tenure →
  likely-seller ranking. Free.
- **Terrain primitives** — HAND, drainage direction, slope, elevation range
  (`services/terrain_analysis.py`) → inputs for gravity-drainage feasibility.
- **s7.11/7.12 + Housing & Productivity contributions** and **SP2 land-reservation /
  rail corridors** already wired (`services/portal_constraints.py`).
- **ArcGIS ingestion framework** (`scripts/ingest_spatial_overlays.py` `LAYER_CONFIG`)
  — extensible pattern for adding new spatial layers.

### Net-new — and this is the moat
- **Sydney Water servicing-capacity zones.** CONFIRMED available as three static public
  GeoJSON files (`GSP_WW.json` / `GSP_DW.json` / `GSP_AdditionalComments.json`) with
  per-polygon stage, timeframe, DSP $/ET and constraint flags. Ingestible today. See
  de-risk below.
- **Gravity-drain-to-connection feasibility** (property-level) — reuses terrain fall,
  needs sewer-main geometry.
- **Adjoining-lot amalgamation query** — data substrate exists; query is net-new
  (easy win).
- **Site Acquisition Score** fusion calc.

### Build order (fastest value first)
| Phase | Ships | Data | Effort |
|---|---|---|---|
| **0 — Radar v1** | Amalgamation finder + uplift + seller-likelihood + DA-approval odds, ranked across 171 catchments | **All data already held** | Weeks. Small. |
| **1 — The moat** | "serviceable / constrained / deferred" flag + timeframe + DSP $/ET per growth polygon | Ingest 2 public GeoJSON files (confirmed) | Days. The differentiator |
| **2 — Deep feasibility** | Property-level gravity-drainage + sewer connection | Sydney Water asset data (may need partnership) | Harder; gated on access |

Phase 0 is shippable almost entirely from assets already owned. Phase 1 makes it
un-copyable.

---

## Moat De-risk — Growth Servicing Plan — CONFIRMED (GREEN)

Verified via a browser network capture (HAR) of the live map. The Growth Servicing Plan
map is a Google Maps front-end that loads its entire servicing dataset from **three
static GeoJSON files on the public Sydney Water CDN** — no login, no token, one GET each:

- `…/content/dam/sydneywater/applications/gsp/GSP_WW.json` — **wastewater**, 205 polygon
  features (~3.3 MB)
- `…/content/dam/sydneywater/applications/gsp/GSP_DW.json` — **drinking water**, 192
  polygon features (~3.3 MB)
- `…/content/dam/sydneywater/applications/gsp/GSP_AdditionalComments.json` — 4 features
  (~57 KB)

Each is a standard GeoJSON `FeatureCollection` with `Polygon` geometry — directly
ingestible with the existing `scripts/ingest_spatial_overlays.py` pattern, then queried
per-address by point-in-polygon against PostGIS. **Phase 1 collapses from "reverse-
engineer an API" to "ingest two GeoJSON files."**

Per-polygon properties give exactly the serviceability signal needed:

| Field | Use | Example values |
|---|---|---|
| `Growth_Polygon_Name` | Area label | "Leppington North (Phase 1)" |
| `Growth_Area` | Region grouping | "South West Growth Area" |
| `SWC_Planning_Project_Stage` | **Servicing-readiness ladder** | Design & Deliver / Concept Planning / Strategic Planning / Option Planning / "Growth precinct boundary. No current project" |
| `Indicative_Timeframe_by_Financial_Year(FY)` | **Timing** | "FY26", "No timeframe noted" |
| `Special_Comments` | **Constraint flag** | "capacity and timescale constraints in this area…", "Under investigation by DPHI…", "None" |
| `Indicative_DSP_Full_Prices_(per_ET)` | **Cost — actual $/ET** | $17,686.52, $888.41, $0 |
| `GSP_Commentary` | Capacity narrative | "Trunk capacity in FY26 dependent upon…" |
| `Development_Servicing_Plan_(DSP)_Area` | Named DSP area | "Nepean River", "North Head" |
| `SWC_Unique_Identifier` | Join key | WW87, DW100 |

Note: the **DSP dollar charge per ET is present** — the codebase audit had flagged
DSP/s64 charge estimation as net-new/missing; this file supplies it directly for
growth-area polygons.

A "serviceable / constrained / deferred" flag is derivable from
`SWC_Planning_Project_Stage` + `Special_Comments` + timeframe, per address, today.

**Confirmed caveats:**
- **Coverage = named growth / renewal / investigation precincts only** — not a metro-wide
  tile. The 205 WW / 192 DW polygons group under: Greater Macarthur, South West Growth
  Area, Illawarra, Greater Parramatta to Olympic Park (GPOP), North West Growth Area,
  Western Sydney Aerotropolis, **Sydenham to Bankstown**, Greater Penrith to Eastern
  Creek, **Metro Northwest Priority Urban Renewal Corridor**, **Epping to St Leonards**,
  Bays West, Liverpool, and a few small areas. Several of these are *established-area
  renewal corridors* that overlap the LMR/TOD footprint heavily (Sydenham–Bankstown,
  Epping–St Leonards, GPOP, Metro NW) — good. But **scattered R2/R3 infill in an ordinary
  established suburb outside a named precinct returns no polygon** → "unknown / not in a
  GSP precinct." (See established-suburb strategy below.)
- `GSP_AdditionalComments.json` is just 4 features (one constrained call-out — the Picton
  wastewater scheme, "not in GSP, capacity constraints"). Minor.
- `Existing_Servicing_Information` for every feature just says "Refer to GSP2025-2030 PDF"
  — some depth remains PDF-only, but the structured fields above are rich enough for a
  first product.
- Data is a dated snapshot (`GSP25_WW_Ext`); refresh annually.

## Licensing — a real gate, resolve before commercialising

- Sydney Water website content is **protected under the Copyright Act 1968 (Cth)**; a
  Terms of Use page governs (`sydneywater.com.au/terms-of-use.html`). The GSP data does
  **not** appear on SEED / data.nsw as an openly-licensed (CC-BY) download.
- **Default assumption: proprietary / all-rights-reserved, not open data.** Ingesting for
  internal analysis is one thing; **redistributing a derived per-address servicing status
  commercially likely needs permission or a data-sharing agreement.**
- Safer postures to weigh with a lawyer: (a) present derived status **with attribution +
  link back** to Sydney Water's map rather than republishing the raw dataset; (b) request
  a **data licence / reuse agreement** from Sydney Water's developer/data team; (c) get
  written advice before launch. **This is the one gate to clear before building on it.**

## Established-suburb strategy (filling the coverage gap)

There is **no bulk public dataset** of established-area local reticulation capacity — it
is resolved per-site via a **Section 73 Feasibility Application** lodged through an
accredited **Water Servicing Coordinator (WSC)**, which returns a *Notice of
Requirements*. Model serviceability in **three honest states** (never fabricate — per
CLAUDE.md data-integrity rules):

1. **In a GSP precinct** → rich status: stage + FY timeframe + DSP $/ET + constraint flag.
2. **Established serviced suburb (no polygon)** → "existing network present; local capacity
   determined by s73 feasibility" + PlotDetect proxies: terrain gravity-fall to street
   (`terrain_analysis.py`), nearby DA servicing outcomes (`da_outcome.py`), DSP $/ET for
   the catchment.
3. **Constrained call-out** (AdditionalComments / "Projects in your area" / "under
   investigation by DPHI") → explicit warning.

**Turn the gap into product, not a hole:**
- **s73 feasibility pack** — auto-generate a pre-filled feasibility application for the
  site and route to a WSC. Monetise via WSC referral/partnership; the developer gets
  exactly the answer the data can't give directly.
- **Data flywheel** — capture the *Notice of Requirements / s73 outcomes* users receive
  and accumulate them. Over time this becomes the **only proprietary dataset of actual
  established-area servicing outcomes** — the established-suburb capacity signal neither
  competitors nor Sydney Water's public map offer. This is the long-term moat that closes
  the gap.

### PDF — still to mine
`GSP2025-2030.pdf` (Sydney Water host egress-blocked in dev; IPART mirror also 403) holds
the `Existing_Servicing_Information` depth and any system-level capacity narrative not in
the GeoJSON. Obtain the PDF directly and extract: per-system capacity tables, established-
area narrative, and any constraint detail beyond the structured fields.

Sources:
[Growth Servicing Plan & map](https://www.sydneywater.com.au/plumbing-building-developing/developing/growth-servicing-plan.html),
[Growth servicing & system capacity](https://www.sydneywater.com.au/plumbing-building-developing/developing/growth-servicing-plan/growth-servicing-system-capacity.html)

---

## Market Sizing

Transparent estimates — every assumption stated; adjust inputs as needed. Clean public
counts of "active developers" do not exist, so these are modelled, not researched
precise figures.

- **Pricing benchmark** (Landchecker/Archistar/CoreLogic run ~$1.5k–$15k/seat/yr):
  Prosumer ~$1,200/yr · Pro ~$4,800/yr · Team ~$12k/yr → blended **~$4,500/seat/yr**.
- **SAM** (site-acquisition subscribers who'd pay for this): 4,000 seats × $4,500 ≈
  **$18M/yr** (range ~$12–27M by seat count and price).
- **SOM** (realistic 3-yr capture): 8–15% of SAM = **~$1.4M–$2.7M ARR**. A real,
  fundable niche business off a NSW-only, hard-to-copy product.
- **Transactional add-on**: per-site deep servicing+feasibility report $250–$500.
  5,600 sites/yr × 15% penetration × $350 ≈ **~$0.3M/yr** on top.
- **TAM** framing: total NSW professional property-data/feasibility spend ≈
  **$50–100M/yr** (the pool CoreLogic/Domain/Landchecker/Archistar divide) — only a
  sliver is needed, taken with a layer none of them have.

**Geographic scope:** the 171 catchments (metro Sydney, Central Coast,
Illawarra-Shoalhaven, Hunter) for Stage 2 typologies, plus all-NSW R2 dual-occ
(Stage 1). **Beachhead:** servicing-constrained hotspots — GPOP/Parramatta and SW
Sydney — where pain is acute, deal volume is high, and the servicing flag is worth the
most. Win there, expand outward.

**Why the numbers hold under pressure:** willingness-to-pay is anchored to deal margin
(tens to hundreds of thousands per site), not to a $49 report — so a $4.5k/yr seat is
trivial to a developer who avoids one un-serviceable dud.

---

## Ownership / Contact Data (cheap path)

Do **not** buy bulk owner data (CoreLogic's expensive licensed moat). Instead:
- Squeeze the **free NSW Valuer General Property Sales Information** for last-sale-date
  → owner tenure → likely-seller signal. No name needed. (Already parsed via
  `vg_comparables.py`.)
- Deliver the ranked *address* cluster; the developer/agent does their own outreach.
- If a name is genuinely needed for one site: NSW LRS title search is **$18 incl GST**,
  on demand, pass-through. Never bulk.

---

## Pressure Test / Risks

- **Envelope data commoditises** → keep value in the *calculation* (serviceability),
  not the raw upzoning flag.
- **Servicing granularity** → strongest in growth areas; weaker for scattered
  established-suburb infill. Start where data is rich.
- **Sewer/water asset geometry** is licensed/restricted → property-level Phase 2 may
  need a Sydney Water partnership. Catchment-level Phase 1 is achievable now.
- **Archistar/Landchecker exist** → do not fight head-on; add the two layers they lack.

---

## Recommended Next Steps

1. Ship **Phase 0 (Site Acquisition Radar v1)** from data already held — validate
   demand with real site-acquisition users before building the servicing layer.
2. **Reverse-engineer the Growth Servicing Plan map endpoint** to confirm a queryable
   spatial backend for the Phase 1 servicing flag.
3. Scope a **Sydney Water partnership / data-access path** for Phase 2 property-level
   feasibility.

---

## Sources
- [NSW Gov — LMR policy, 112,000 homes](https://www.nsw.gov.au/ministerial-releases/low-and-mid-rise-policy-to-unlock-112000-homes-five-years)
- [NSW Planning — Low & Mid-Rise policy](https://www.planning.nsw.gov.au/policy-and-legislation/housing/low-and-mid-rise-housing-policy)
- [Egis — will the policy hit its target (amalgamation bottleneck)](https://www.egis-group.com/all-insights/is-the-nsw-government-s-low-mid-rise-housing-policy-going-to-achieve-its-target-the-devil-is-in-the-detail)
- [The Urban Developer — Western Sydney sewer capacity cliff](https://www.theurbandeveloper.com/articles/western-sydney-water-wastewater-greater-parramatta-olympic-peninsula-sewer-camelia)
- [Sydney Water — Growth Servicing Plan & map](https://www.sydneywater.com.au/plumbing-building-developing/developing/growth-servicing-plan.html)
- [Sydney Water — Growth servicing & system capacity](https://www.sydneywater.com.au/plumbing-building-developing/developing/growth-servicing-plan/growth-servicing-system-capacity.html)
- [Landchecker — LMR housing planning layer](https://landchecker.com.au/articles/low-and-mid-rise-housing-policy-new-south-wales/)
- [Archistar — Precinct Planner](https://www.archistar.ai/blog/shaping-the-future-of-urban-landscapes-introducing-our-precinct-planner-tool/)
