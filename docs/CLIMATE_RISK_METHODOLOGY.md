# Climate Risk Awareness Score — Methodology Document

**Version:** 1.0 (this document)
**Date:** 2026-05-15, validation status appended 2026-08-07
**Status:** Computed and returned by the API. NOT rendered as a score on any
customer-facing surface — see [Validation status](#validation-status).

> **⚠ This document lags the code.** `services/climate_risk_score.py` is at
> `methodology_version = "1.1"` with a v1.2 changelog entry. The sections below
> marked **[corrected 2026-08-07]** were measured against the running code; the
> rest has not been re-checked. Where this document and the code disagree, the
> code is authoritative.

---

## What this score is

A deterministic composite indicator (1-100) of climate hazard exposure at a specific geographic point in NSW, Australia. It quantifies the degree to which a property is located within known hazard zones and projected climate change trajectories.

## What this score is NOT

- Not financial, insurance, or property advice
- Not a prediction of future loss or damage
- Not a building assessment (does not consider construction type, floor height, or materials)
- Not a guarantee of future conditions
- Not a recommendation to buy, sell, insure, or lend

## Data sources

All inputs are government-authoritative:

| Hazard | Source | Authority | Update frequency |
|--------|--------|-----------|-----------------|
| Flood | EPI Flood Planning layers | NSW Planning Portal | Per LEP amendment |
| Bushfire | Bushfire Prone Land Map | NSW Rural Fire Service | Annual review |
| Landslide **[added 2026-08-07]** | EPI Landslide Risk layer | NSW Planning Portal | Per LEP amendment |
| Coastal hazard | SEPP (Resilience & Hazards) 2021 layers 1,3,4,6,7 | NSW DPE | Per SEPP amendment |
| Fire history | NPWS Fire History | NSW National Parks | Post-season update |
| Heat trajectory | NARCliM 2.0 (TXge35) | AdaptNSW / NSW DCCEEW | Fixed (model output) |
| Precipitation | NARCliM 2.0 (prAdjust) | AdaptNSW / NSW DCCEEW | Fixed (model output) |

## Calculation method

### Step 1: Per-hazard normalization (0 to 1)

Each hazard input is normalized to a 0-1 scale:

- **Flood:** Binary. 1.0 if property intersects any flood planning polygon, 0.0 otherwise.
- **Bushfire:** Binary. 1.0 if property intersects Bushfire Prone Land, 0.0 otherwise.
- **Coastal:** Graduated. Count of SEPP R&H 2021 coastal layers intersecting the point, divided by 3 (capped at 1.0). More overlapping coastal designations = higher exposure.
- **Fire history:** Graduated. Count of distinct NPWS historical fire polygons at location × 0.3 (capped at 1.0). Repeated burning indicates persistent structural risk.
- **Heat trajectory:** Continuous. NARCliM 2.0 projected increase in days ≥35°C from baseline (2015-2024) to late-century (2080-2099) under SSP3-7.0, normalized against the statewide maximum observed delta (45 days).

### Step 2: Weighting **[corrected 2026-08-07]**

Equal weighting across **six** hazards. This table previously listed five at
0.20; landslide was added in code v1.1 (2026-05-18) and the table was never
updated. Values below are read from `WEIGHTS` in `services/climate_risk_score.py`:

| Hazard | Weight | Rationale |
|--------|--------|-----------|
| Flood | 0.167 | Equal — pending loss-based calibration |
| Bushfire | 0.167 | Equal |
| Coastal | 0.167 | Equal |
| Fire history | 0.167 | Equal |
| Heat | 0.167 | Equal |
| Landslide | 0.165 | Equal (absorbs the rounding remainder to sum to 1.0) |

Hazards whose data source is unavailable are excluded from the denominator and
the remainder rescaled, so a missing source does not read as absence of hazard.

**Why equal weighting:** Loss-proportional weighting (the gold standard per FEMA NRI methodology) requires actuarial loss data at property level, which is not publicly available in Australia. Equal weighting is a documented simplifying assumption that will be replaced with APRA/ICA loss-calibrated weights when SA3-level loss data becomes accessible for validation.

### Step 3: Interaction bonus

Documented compound hazard pathways receive an additive bonus:

| Pair | Bonus | Justification |
|------|-------|---------------|
| Bushfire + Fire history | +0.05 | Repeated burning = persistent ignition/fuel conditions |
| Flood + Coastal | +0.05 | Riverine + tidal compound inundation |
| Bushfire + Heat | +0.05 | Heat dries vegetation → increased fire intensity |
| Flood + Heat | +0.03 | Intense convective storms from heat → flash flooding |

Justification: IPCC AR6 WGII Ch11 states "climate impacts are cascading and compounding across sectors and socioeconomic and natural systems (high confidence)".

### Step 4: Composite calculation

```
composite = (Σ hazard_raw_score × weight) + interaction_bonus
score = clamp(round(composite × 100), 1, 100)
```

### Step 5: Band assignment

| Score | Band | Interpretation |
|-------|------|----------------|
| 1-20 | Low | Minimal climate hazard exposure detected |
| 21-40 | Moderate | Some hazard exposure; standard conditions |
| 41-60 | High | Significant exposure to one or more hazards |
| 61-80 | Very High | Multiple or severe hazard exposures |
| 81-100 | Extreme | Maximum detected hazard exposure |

## Confidence levels

- **High:** Spatial overlay layers (flood, bushfire, coastal, fire history) — authoritative vector data with defined legal boundaries
- **Medium:** NARCliM projections — model-dependent, scenario-dependent, 4km grid resolution
- **Low:** NARCliM data unavailable for location (outside SE Australia domain)

## Known limitations

1. Binary flood/bushfire scoring does not differentiate severity (e.g., 1-in-100yr vs 1-in-20yr flood, Vegetation Category 1 vs buffer zone)
2. Single GCM (ACCESS-ESM1.5) — full ensemble would use 10 model members
3. No property-specific vulnerability factors (construction, floor height, drainage)
4. No adaptation offset (flood levees, bushfire asset protection zones, seawalls)
5. Equal weighting is a simplifying assumption — does not reflect that flood causes 240% more projected loss increase than other perils (APRA 2026)
6. Score reflects hazard EXPOSURE, not PROBABILITY of loss

## Planned V2 improvements

- Loss-proportional weighting calibrated against APRA Insurance CVA SA3 risk rankings
- Bushfire category differentiation (Vegetation Category 1/2/3, buffer)
- Flood severity differentiation (if depth/ARI data becomes accessible)
- Multi-GCM ensemble (when additional NARCliM downloads complete)
- ~~Validation: Spearman rank correlation against APRA SA3 rankings (target ρ > 0.7)~~
  — **attempted 2026-08-07, could not be run.** See [Validation status](#validation-status).

## Validation status

**Ladder rung: 1 (source-linked). Not 2, not 3.** Every value can be traced to
the government layer it came from, and the same point returns the same score.
The composite has **never been compared against anything that happened.**

### The pre-committed check

| | |
|---|---|
| **Check** | Spearman rank correlation, composite score vs APRA SA3 protection-gap rankings |
| **Pass mark** | **ρ > 0.7** (strict) — written into this document 2026-05-15, **before** any run, and reproduced here exactly as written. A result of exactly 0.700 is not a pass. |
| **Consequence of failure** | Decision D3 (ruled 2026-08-06): at or below 0.7 the composite stops rendering as a score and reverts to per-hazard presence facts |
| **Run date** | 2026-08-07 |
| **Result** | **UNKNOWABLE — not a pass, and not a fail.** The reference is not *absent*; it is **not extractable**. |

### Why it could not be run

The APRA SA3 series **exists** — as pictures. Figures 9 and 10 of *Mind the Gap
2026* are the protection-gap results by SA3, and they are raster images
occupying 20.7% and 38.4% of their pages. Nothing short of OCR, or digitising a
choropleth, would recover them, and digitising a choropleth does not return
reliable per-region values. So the honest statement is not "there is no
reference" but "the reference cannot be read from what we hold".

What *is* absent is any machine-readable form of it:

The reference vector does not exist. Measured, not assumed —
`scripts/measure_climate_reference_availability.py` sweeps the reference corpus
(**22 documents, 1,303 pages**) and reports:

- **Zero** documents contain a table pairing a rankable set of labels with
  numeric values on a page naming an ASGS geography.
- The largest label-to-value table found **anywhere in the corpus holds 7
  pairs**, against a floor of 10 — and it is a Wollongong mitigation table, not
  an APRA series.
- `SA3` appears **twice in total**, in prose, on one page of *APRA Mind the Gap
  2026* — the only document in the corpus that mentions an ASGS unit at all.
  The word `rank` appears **zero** times in that report.
- APRA's regional results (Figures 9 and 10) are **raster images**. The
  underlying SA3 series is not published in the report.
- The report's only regional statement is an aggregate: *"Of the 20 SA3 regions
  with the widest protection gaps in Australia today, 90% are in New South Wales
  or Queensland"* (p.17) — it does not name them or give their values.

> The corpus is 22 documents, not 17. An earlier top-level-only, case-sensitive
> glob silently skipped the five PDFs in `climate_risk_intel/council_strategies/`
> and still printed a confident verdict over the other 17. Caught by
> cross-review; the sweep now recurses and match extensions case-insensitively.
> The verdict did not change, but it had been asserted over an incomplete corpus.

Detection is **name-agnostic**: it looks for the structure of a reference — one
table pairing at least ten distinct text labels with parseable numbers, on a
page naming an ASGS geography — not for a hardcoded list of place names. An
earlier draft gated on 27 hand-written NSW names; NSW has roughly 130 SA3s, so
a real table of Bathurst, Orange, Goulburn-Mulwaree and Snowy Mountains would
have scored zero and been reported as "no reference". Name-agnostically, the
largest label-to-value table anywhere in the 1,303 pages holds **7 pairs**.

The check is falsifiable and was proven so across ten planted cases:

| Planted | Verdict | Exit |
|---|---|---|
| Nothing | REFERENCE ABSENT | 0 |
| Ten region names in prose + an unrelated 2-row table | REFERENCE ABSENT | 0 |
| A 12-row insurer/revenue table on a page headed "Regional…" | REFERENCE ABSENT | 0 |
| A 12-row SA3 annex using names **not** on any list | REFERENCE AVAILABLE | 1 |
| That annex **plus** an unrelated scanned brochure | REFERENCE AVAILABLE | 1 |
| The same annex in a **subdirectory**, named `.PDF` | REFERENCE AVAILABLE | 1 |
| A scanned page with no text layer, alone | RED — UNKNOWABLE | 1 |
| An unread raster page inside a document that **mentions SA3** | NOT EXTRACTABLE | 1 |
| A **figure-sized raster beside full prose** in an SA3 document | NOT EXTRACTABLE | 1 |
| Pairs accumulating across tables without one clearing the bar | POSSIBLE SPLIT SERIES | 1 |

A reference that *was* positively found answers the existence question
regardless of what else is unreadable, so candidates are reported first.
**Exit 0 — the only "we looked and it is not there" outcome — requires that no
content-sized raster went unread anywhere in the corpus.** That is strict on
purpose: a section heading rendered inside an image cannot be detected from
text, so a document that never says "SA3" in its text layer still cannot be
cleared while it holds unread pictures.

**Stated ceiling.** 374 pages of the 1,303 carry a content-sized image that
nothing in the sweep can read; a table rendered as a picture on any of them
would not have been detected. The script prints the count and names every
affected document, marking which of them mention an ASGS geography.

> **A claim of mine that this check falsified.** An earlier version of this
> section said `APRA_Mind_the_Gap_Insurance_CVA_2026.pdf` "was read in full" and
> leaned on that as the reason the verdict was safe. It is **not** read in full:
> it carries **7 content-image pages**, and pages 16–17 — Figures 9 and 10, at
> 20.7% and 38.4% image coverage — *are the SA3 protection-gap results*. The
> earlier text-layer heuristic scored those pages as "read" because prose sits
> beside the figure. The correct verdict is therefore NOT EXTRACTABLE rather
> than ABSENT, which is what the script now returns. The conclusion for the
> calibration does not change; the reason for it does, and the stronger-sounding
> version of the claim was wrong.

Two reviewer findings were **not** adopted, recorded here rather than silently
declined. Both would tighten detection, and both trade a false positive — which
only sends a human to look, as the `REFERENCE AVAILABLE` message instructs — for
a false negative, the direction that would make this verdict wrong.

1. *Tie geography context to the table or its caption rather than the page.*
   Real annexes often put "SA3" only in a heading above the table.
2. *Accept SA3 only, not SA4.* APRA reports at both — footnote 28 on p.15 states
   the protection-gap regions are "at SA4 regional scale", while p.17 discusses
   SA3. An SA4 series would not directly satisfy the SA3 pre-commitment, but it
   is plainly evidence a person should see rather than have filtered out.

### Two reasons the correlation would still not validate the score

Obtaining the missing numbers would **not** be sufficient. Both problems below
are properties of the comparison itself, not of the missing data:

1. **Construct mismatch.** APRA's CVA measures the *insurance protection gap* —
   the share of households facing affordability stress or non-insurance. That is
   an economic measure driven by premium levels against household income. This
   score measures hazard *exposure* and contains no income, premium, or tenure
   term. Correlating them asks "does hazard exposure track insurance
   affordability" — a question about the world, not a validation of this
   score's weighting. A pass would not vindicate the weights; a fail would be
   ambiguous between "the score is wrong" and "protection gap is not a hazard
   proxy".

2. **Geographic incommensurability, with a free parameter.** This score is a
   function of a point; APRA's unit is an SA3. Aggregating requires a sampling
   scheme, and because the composite is dominated by binary flood/bushfire
   flags, the SA3 aggregate is close to "fraction of sampled points inside a
   hazard polygon" — which moves substantially depending on whether points are
   sampled by area, by population, or by address. That is a researcher degree of
   freedom large enough to steer the result toward any target. A correlation
   that can be tuned to pass cannot falsify anything.

A third limit is arithmetic: the largest sample the source could support is
N = 20. At that N the 95% confidence interval on a Spearman ρ is roughly ±0.4
wide, so ρ = 0.7 is not statistically distinguishable from ρ = 0.4 or ρ = 0.9.
The pass mark could not discriminate even with perfect data.

### The honest ceiling

**This composite score cannot be validated with available data.** That is a
completed outcome, not an outstanding task. It is recorded here so no surface,
document, or marketing claim describes the score as validated, calibrated, or
benchmarked — it is none of those things.

What would change it is loss or claims data keyed to a geography we can resolve
a point into, which is not publicly available in Australia at property level.
Until then the correct posture is the one already in force: report the
per-hazard facts, which are pass-through from government layers and sound, and
do not present the composite as a score.

### D3 was not triggered, and is already substantially in force

D3's consequence fires on a result at or below 0.7. There is no result, so **D3 was
not implemented on the strength of this run.** Recording that explicitly because
"could not determine" must not be quietly converted into a fail.

Separately, and for legal rather than calibration reasons (#699), the composite
is already withheld from every customer-facing surface — measured 2026-08-07 by
reading each renderer:

| Surface | Renders the composite? | Evidence |
|---|---|---|
| Tool result card | No | `ClimateRiskResultCard.tsx` declares `score`/`band` but renders neither; headline is "N of M mapped hazard categories present" |
| `/climate-risk` page | No | "It is not scored, ranked, or colour-coded into a risk verdict" |
| Conveyancing PDF | No | `conveyancing.py` `_fetch_climate` — "NO composite score (barred by the legal assessment; #699)" |
| Intelligence Brief | No | `ClimateDisclosureProfile` — "replaces composite climate risk score… No composite score" |
| **API JSON** | **Yes** | `climate_risk_pipeline.py` returns `outputs.score` and `outputs.band` |

The API response is the one place an unvalidated composite still escapes.

## Reproducibility

- Deterministic: same (lat, lng) always produces same score given same input data version
- All data versioned by `synced_at` timestamp in spatial_overlays
- NARCliM files are fixed model output (no updates expected)
- Score version and data date embedded in every result
