# Flood calibration against the 2022 NSW floods — result

**Run:** 2026-08-08. Pass mark committed in `flood-calibration-2022-precommit.md` at commit
`fb0a44f7`, before any point was sampled. Raw per-point output:
`flood-calibration-2022-result.json`. Runner: `scripts/run_flood_calibration_2022.py`, seed 20220228.

## Verdict

> **RECALL 0.857 — 6 of 7 scored points. Wilson 95% CI 0.487 – 0.974. Pass mark 0.90.**
> **VERDICT: INDISTINGUISHABLE FROM THE MARK. Not a pass, and not a fail.**

Seven points is far too few to decide anything. The interval spans from "half the time" to "almost
always", and it contains the mark, so the honest reading is that this run did not establish whether
the product clears 0.90 or not. That is the third state, and it is the answer.

## How the number got smaller three times

Reported plainly, because each correction moved it down and the first version would have been
published as a pass.

| Version | Recall | Interval | What was wrong |
|---|---|---|---|
| first run | — | — | every report_id was an invalid UUID; 0 of 50 scored, and the harness printed **FAIL** from a 0/0 division. Discarded — a harness that could not run has measured nothing |
| second | 0.976 (40/41) | Wald ±0.047 → lower 0.929 | reported **PASS**. Wald is invalid at a proportion this close to 1 |
| third | 0.976 (40/41) | Wilson 0.874–0.996 | lower bound below the mark, so **indistinguishable**, per the rule written before the run |
| **final** | **0.857 (6/7)** | **Wilson 0.487–0.974** | the denominator was wrong: 34 of the 41 were outside the product's council coverage, several in south-east Queensland, and `flood_signal='unavailable'` was being counted as a flood indicator |

Every one of those corrections came from the cross-review, not from me.

## What was run

26,569 observed flood polygons across 47 Copernicus EMS archives (EMSR567, EMSR570, EMSR586). 50
points sampled with a fixed seed, stratified round-robin across 23 activation/AOI pairs.

**Scope filter:** each point tested against the product's own NSW council coverage via
`lookup_lga`. **7 of 50 passed.** The other 43 are outside it — EMSR567 mapped south-east
Queensland as well as northern NSW, and the pipeline's own latitude envelope is coarse enough to
accept Brisbane-area points, which is how the earlier 41-point denominator came about. Scoring a
Queensland observation as NSW recall measures the wrong thing.

**Hit definition:** an allowlist — `flood_signal` in `low`/`moderate`/`elevated`, or
`in_100yr_flood_zone` true, or a council/SES extent match. `unavailable` is explicitly **not** a
hit: it means the sources could not be consulted, so the product supplied no flood indicator.
Counting it as one would be the absence-as-answer error this whole campaign is about, committed
inside the instrument measuring it.

**Reference integrity:** the runner aborts if any archive will not open. It did — one truncated
download — and the file was re-fetched before the run that produced this number. An AOI silently
missing from the sample can only flatter the result.

## The one miss

```
EMSR570 / AOI01   -29.0424, 153.2542
flood_signal = none   in_100yr_flood_zone = False   ses_in_flood_planning_area = False
```

Northern Rivers, March–April 2022 second wave. The product returned `none` at a location the
European Commission mapped as inundated.

## What this licenses

**Licensed:** *"checked against the Copernicus EMS observed extents of the 2022 NSW floods — the
served screen returned a flood indicator at 6 of 7 points inside our council coverage (Wilson 95% CI
0.49–0.97). At N=7 this does not establish whether the product meets the 0.90 mark committed before
the run."*

**Not licensed:**

- **Not "validated".** Nowhere near it.
- **Not a pass.** The point estimate is below the mark and the interval contains it.
- **Nothing about the 1% AEP verdict** — deliberately excluded. 2022 exceeded the 1% design event in
  several catchments (Lismore peaked 14.4 m, a record by ~2 m), so comparing them measures construct
  mismatch, not product error. Visible in the raw output: hits carry `in_100yr = False` on ground
  that was demonstrably under water.
- **Nothing about specificity.** A flag outside the 2022 extent may be a correct 1% mapping of ground
  that did not flood that year; the two cannot be separated with this data.

## What would settle it

More points inside council coverage. At this recall roughly 150 scored points would put the Wilson
lower bound above 0.90. The binding constraint is not compute — it is that Copernicus mapped only
the areas the EU was asked to map, and only a fraction of those fall in councils this product
covers. Widening either the council coverage or the reference set is the work.

## Limits, as committed in advance

- **Recall here is biased UP.** Copernicus maps the worst-hit ground, which is also the most likely
  to carry an EPI or council flood layer. Best case, not average case.
- **Permanent water is not excluded.** The reference labels only "Riverine flood" (11,081) and
  "Flash flood" (628); there is no permanent-water class, so some sampled points may be river
  channel. Unquantified, and it inflates recall.
- **Councils covered:** the sampled points fall in the Northern Rivers, south-western Sydney and the
  Hawkesbury. Nothing here extends to a council with no sampled point.
