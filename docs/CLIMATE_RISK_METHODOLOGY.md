# Climate Risk Awareness Score — Methodology Document

**Version:** 1.0
**Date:** 2026-05-15
**Status:** Internal data infrastructure (not publicly exposed)

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

### Step 2: Weighting

V1 uses equal weighting (0.20 per hazard):

| Hazard | Weight | Rationale |
|--------|--------|-----------|
| Flood | 0.20 | Equal — pending loss-based calibration |
| Bushfire | 0.20 | Equal |
| Coastal | 0.20 | Equal |
| Fire history | 0.20 | Equal |
| Heat | 0.20 | Equal |

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
- Validation: Spearman rank correlation against APRA SA3 rankings (target ρ > 0.7)

## Reproducibility

- Deterministic: same (lat, lng) always produces same score given same input data version
- All data versioned by `synced_at` timestamp in spatial_overlays
- NARCliM files are fixed model output (no updates expected)
- Score version and data date embedded in every result
