# Flood calibration against the 2022 NSW floods — result

**Run:** 2026-08-08. Pass mark committed in `flood-calibration-2022-precommit.md` at commit
`fb0a44f7`, before any point was sampled. Raw per-point output:
`flood-calibration-2022-result.json`. Runner: `scripts/run_flood_calibration_2022.py`, seed 20220228.

## Verdict

> **RECALL 0.895 — 34 of 38 scored points. Wilson 95% CI 0.759 – 0.958. Pass mark 0.90.**
> **VERDICT: INDISTINGUISHABLE FROM THE MARK. Not a pass, and not a fail.**

> **⚠ CORRECTED 2026-08-09.** This section previously published **0.857 (6 of 7)**, which the
> committed runner does not produce. Re-running `scripts/run_flood_calibration_2022.py` at seed
> 20220228 reproduces `flood-calibration-2022-result.json` byte-identically — 38 sampled, 38 in
> coverage, 34 hits — so the JSON is the reproducible artifact and the 6-of-7 figure was an
> intermediate run that was never refreshed here. The VERDICT is unchanged either way, which is
> the only reason this was a documentation defect rather than a wrong conclusion. Found by the
> cross-review, which flagged that the markdown and its own cited JSON disagreed.

Thirty-eight points is still too few to decide. The interval spans from "three in four" to "almost
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
| fourth | 0.857 (6/7) | Wilson 0.487–0.974 | an intermediate run. Its denominator excluded all but 7 points as outside council coverage; the committed runner, with a working `lookup_lga`, scopes IN 38 of 38. Not reproducible — superseded |
| **final** | **0.895 (34/38)** | **Wilson 0.759–0.958** | what `scripts/run_flood_calibration_2022.py` produces at seed 20220228, verified by re-running it and diffing the JSON: identical. `flood_signal='unavailable'` is correctly NOT counted as a flood indicator |

Every one of those corrections came from the cross-review, not from me.

## What was run

26,569 observed flood polygons across 47 Copernicus EMS archives (EMSR567, EMSR570, EMSR586).
**150 raw draws** with a fixed seed (20220228), stratified round-robin across 23 activation/AOI
pairs, per `flood-calibration-2022-amendment-01.md`.

**Scope filter:** each draw tested against the product's own NSW council coverage via `lookup_lga`.
**150 raw draws → 38 in coverage, 112 outside, 0 unresolved.** An earlier version of this section
said "38 of 38, none excluded", because the artifact recorded only the post-filter count — the 112
discarded draws were invisible, and any lookup FAILURES among them would have been indistinguishable
from genuine out-of-coverage points. The three counts are now written separately, and a draw whose
lookup fails is recorded as `scope_unresolved` rather than folded in with the ones known to be
outside. A coarse latitude pre-filter
now drops the south-east Queensland polygons before sampling — EMSR567 mapped both states, and
without that filter the stratified walk spent most of its draws in Queensland, which is how the
earlier run scored only 7 points. `lookup_lga` remains the authoritative test; the pre-filter only
stops the sample being wasted. An unresolvable lookup returns `None` — unknown scope, excluded,
never silently treated as in-scope.

**Hit definition:** an allowlist — `flood_signal` in `low`/`moderate`/`elevated`, or
`in_100yr_flood_zone` true, or a council/SES extent match. `unavailable` is explicitly **not** a
hit: it means the sources could not be consulted, so the product supplied no flood indicator.
Counting it as one would be the absence-as-answer error this whole campaign is about, committed
inside the instrument measuring it.

**Reference integrity:** the runner aborts if any archive will not open. It did — one truncated
download — and the file was re-fetched before the run that produced this number. An AOI silently
missing from the sample can only flatter the result.

## The four misses — and they are one finding, not four

An earlier version of this section reported **one** miss. The artifact records **four**, and
naming only one understated the failure by a factor of four in a document written to be relied on.

```
AOI01  -29.0424, 153.2542   signal=none  1pct=False  ses=False
AOI01  -29.0253, 153.1980   signal=none  1pct=False  ses=False
AOI01  -29.0921, 153.3311   signal=none  1pct=False  ses=False
AOI01  -29.0660, 153.3032   signal=none  1pct=False  ses=False
```

**Every miss is identical and they are all in the same place.** Same AOI, a span of roughly
7 km × 12 km, and the same signature at all four: nothing from the EPI layer, nothing from the 1%
AEP verdict, nothing from the council/SES extent. Four independent failures would look different
from each other. These do not.

**Cause, measured rather than inferred.** All four fall in **Richmond Valley** council, and a
point-in-polygon check returns **zero flood polygons covering any of them**. Compare the
neighbouring councils in `spatial_overlays`:

| Council | Flood polygons held |
|---|---|
| Ballina | 191 |
| Clarence Valley | 12 |
| **Lismore** | **1** |
| **Richmond Valley** | **0** |

So this is not a detection failure. **The product holds no flood overlay for Richmond Valley at
all**, and returns "no flood indicator" for every address in it — including ground the European
Commission photographed under water. The recall figure is measuring, in these four points, an
absence of data rather than an absence of flooding.

**Lismore holding a single polygon deserves its own look.** It is the council that recorded the
most catastrophic flood in Australian history in 2022. One polygon is unlikely to be its true
extent, and no point in this sample landed there to test it.

**This changes what the headline number means.** 0.895 is not "the screen misses about one in ten
flooded places at random". It is closer to "the screen works where flood data has been loaded, and
returns a confident negative where it has not". Those are very different products, and only the
second one is dangerous.

## What this licenses

**Licensed:** *"checked against the Copernicus EMS observed extents of the 2022 NSW floods — the
served screen returned a flood indicator at 34 of 38 points inside our council coverage (Wilson 95%
CI 0.76–0.96). At N=38 this does not establish whether the product meets the 0.90 mark committed
before the run."*

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

> **⚠ CORRECTED 2026-08-10.** This section previously said *"at this recall roughly 150 scored
> points would put the Wilson lower bound above 0.90"*. **That is impossible.** A Wilson lower
> bound converges on the point estimate from below and can never exceed it, so at an observed
> recall of 0.895 no sample size whatsoever lifts the bound past 0.90. Computed:

| Scored points, recall held at 0.895 | Wilson 95% CI | Lower bound ≥ 0.90? |
|---|---|---|
| 38 (this run) | 0.759 – 0.958 | no |
| 150 | 0.834 – 0.933 | no |
| 600 | 0.868 – 0.917 | **still no** |

**More points cannot turn this result into a pass.** They can only do one of two things: reveal
that the true recall is higher than 0.895 and the small sample understated it, or tighten the
interval until 0.895 can be declared a **fail** with confidence — which happens somewhere past
600 scored points.

For the bound to clear 0.90 the TRUE recall has to be above it, and then the sample needed is:

| If true recall is | Scored points needed for the lower bound to clear 0.90 |
|---|---|
| 0.93 | ~375 |
| 0.95 | ~130 |
| 0.97 | ~70 |

So the honest framing is not "we need 150 more points". It is: **on the evidence so far this
product has not demonstrated 90% recall, and the cheapest way to find out whether it can is to fix
the Richmond Valley class of coverage gap first** — four of the four misses came from one council
holding no flood data at all, so the measured recall is currently bounded by data coverage rather
than by detection.

The binding constraint on sample size is not compute — it is that Copernicus mapped only the areas
the EU was asked to map, and only a fraction of those fall in councils this product covers.
Widening either the council coverage or the reference set is the work.

## Limits, as committed in advance

- **Recall here is biased UP.** Copernicus maps the worst-hit ground, which is also the most likely
  to carry an EPI or council flood layer. Best case, not average case.
- **Permanent water is not excluded.** The reference labels only "Riverine flood" (11,081) and
  "Flash flood" (628); there is no permanent-water class, so some sampled points may be river
  channel. Unquantified, and it inflates recall.
- **Councils covered:** the sampled points fall in the Northern Rivers, south-western Sydney and the
  Hawkesbury. Nothing here extends to a council with no sampled point.
