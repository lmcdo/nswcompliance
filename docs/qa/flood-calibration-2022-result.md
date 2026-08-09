# Flood calibration against the 2022 NSW floods — result

**Run:** 2026-08-08. Pass mark committed in `flood-calibration-2022-precommit.md` at commit
`fb0a44f7`, before any point was sampled. Raw per-point output:
`flood-calibration-2022-result.json`. Runner: `scripts/run_flood_calibration_2022.py`, seed 20220228.

## Verdict

> **RECALL 0.946 — 35 of 37 scored points. Wilson 95% CI 0.823 – 0.985. Pass mark 0.90.**
> **VERDICT: INDISTINGUISHABLE FROM THE MARK. Not a pass, and not a fail.**

> **⚠ CORRECTED TWICE. Read both, because the second correction moved the number UP.**
>
> **2026-08-10 — the reference contained dry land.** GeoJSON polygon holes were being discarded, so
> a dry island inside an inundation polygon could be sampled as observed flooding. The product
> correctly answered "no flood" at those points and was scored as MISSING them. Respecting the
> holes removed 2 of the 4 misses and moved recall from 0.895 to **0.946**. Also fixed in the same
> pass: the runner globbed the archive directory instead of reading the committed manifest, so an
> unmanifested archive could join the reference set and change the result. A number that rises
> after a fix deserves more scrutiny than one that falls — the check here is that both defects were
> found by adversarial review rather than by looking for a better figure, and the VERDICT is
> unchanged.
>
> **2026-08-09.** This section previously published **0.857 (6 of 7)**, which the
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
| fifth | 0.895 (34/38) | Wilson 0.759–0.958 | reproducible, but the reference still contained dry land: polygon holes were discarded, so dry islands inside inundation polygons were sampled as flooded and the product was scored as missing them |
| **final** | **0.946 (35/37)** | **Wilson 0.823–0.985** | holes respected, and the archive set read from the committed manifest rather than a directory glob. Seed 20220228 unchanged. `flood_signal='unavailable'` is still correctly NOT counted as a flood indicator |

Every one of those corrections came from the cross-review, not from me.

## What was run

26,569 observed flood polygons across 47 Copernicus EMS archives (EMSR567, EMSR570, EMSR586).
**150 raw draws** with a fixed seed (20220228), stratified round-robin across 23 activation/AOI
pairs, per `flood-calibration-2022-amendment-01.md`.

**Scope filter:** each draw tested against the product's own NSW council coverage via `lookup_lga`.
**150 raw draws → 37 in coverage, 113 outside, 0 unresolved.** An earlier version of this section
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

## The two misses — and they are one finding, not two

This section has been wrong twice, in opposite directions. It first reported **one** miss when the
artifact held four — understating the failure. Then respecting polygon holes showed that **two of
those four were not misses at all**: they fell on dry islands inside inundation polygons, where the
product's "no flood" was correct and the reference was wrong.

```
AOI01  -29.0424, 153.2542   signal=none  1pct=False  ses=False
AOI01  -29.0660, 153.3032   signal=none  1pct=False  ses=False
```

**Both are identical and both are in the same place.** Same AOI, roughly 4 km apart, the same
signature: nothing from the EPI layer, nothing from the 1% AEP verdict, nothing from the
council/SES extent. Two independent failures would not look like that.

**Cause, measured rather than inferred, and it survived the correction.** Both fall in **Richmond
Valley** council, and a point-in-polygon check returns **zero flood polygons covering either**. Compare the
neighbouring councils in `spatial_overlays`:

| Council | Flood polygons held |
|---|---|
| Ballina | 191 |
| Clarence Valley | 12 |
| **Lismore** | **1** |
| **Richmond Valley** | **0** |

So this is not a detection failure. **The product holds no flood overlay for Richmond Valley at
all**, and returns "no flood indicator" for every address in it — including ground the European
Commission photographed under water. The recall figure is measuring, in these two points, an
absence of data rather than an absence of flooding.

**Lismore holding a single polygon deserves its own look.** It is the council that recorded the
most catastrophic flood in Australian history in 2022. One polygon is unlikely to be its true
extent, and no point in this sample landed there to test it.

**This changes what the headline number means.** 0.946 is not "the screen misses about one in
twenty flooded places at random". Both remaining misses come from a single council holding no flood
data, so it is closer to "the screen works where flood data has been loaded, and returns a
confident negative where it has not". Those are very different products, and only the second one is
dangerous. A higher recall does not soften that — it sharpens it, because the failures are now
entirely explained by a coverage gap rather than spread thinly across the sample.

## What this licenses

**Licensed:** *"checked against the Copernicus EMS observed extents of the 2022 NSW floods — the
served screen returned a flood indicator at 35 of 37 points inside our council coverage (Wilson 95%
CI 0.823–0.985). At N=37 this does not establish whether the product meets the 0.90 mark committed
before the run."*

> This wording is the one sentence intended for external quotation, so it is pinned by
> `test_the_licensed_statement_quotes_the_run`. It published the superseded 34-of-38 figure for one
> commit after the corrected run, because the agreement tests checked only the headline line while
> the customer-quotable sentence sat unguarded twenty lines below it. Caught in review, not by the
> guard that existed to catch it.

**Not licensed:**

- **Not "validated".** Nowhere near it.
- **Not a pass.** The point estimate (0.946) is above the 0.90 mark but the interval still contains
  it — the lower bound is 0.823. Being above the mark on 37 points is not the same as clearing it.
- **Nothing about the 1% AEP verdict** — deliberately excluded. 2022 exceeded the 1% design event in
  several catchments (Lismore peaked 14.4 m, a record by ~2 m), so comparing them measures construct
  mismatch, not product error. Visible in the raw output: hits carry `in_100yr = False` on ground
  that was demonstrably under water.
- **Nothing about specificity.** A flag outside the 2022 extent may be a correct 1% mapping of ground
  that did not flood that year; the two cannot be separated with this data.

## What would settle it

> **⚠ CORRECTED TWICE.** This section first claimed *"roughly 150 scored points would put the
> Wilson lower bound above 0.90"*. At the recall then measured (0.895) that was **impossible** — a
> Wilson lower bound converges on the point estimate from below and can never exceed it, so no
> sample size lifted it past 0.90. Once the reference was corrected for polygon holes the measured
> recall rose to **0.946**, and at that recall the claim becomes true — at **153** scored points,
> not 150 by coincidence. Recomputed rather than restored:

| Scored points, recall held at 0.946 | Wilson 95% CI | Lower bound ≥ 0.90? |
|---|---|---|
| 37 (this run) | 0.823 – 0.985 | no |
| 75 | 0.871 – 0.979 | no |
| **153** | ~0.900 – 0.974 | **yes — first n that clears it** |
| 300 | 0.915 – 0.967 | yes |

**So there is now a concrete, reachable target: about 153 scored points.** At this run's yield —
37 scored from 150 raw draws, roughly one in four landing inside covered councils — that is on the
order of **620 raw draws**.

Two cautions on reading that. It assumes the true recall really is near 0.946; if the larger sample
pulls it back toward 0.90 the bound will not clear, and that is the outcome the exercise exists to
find out. And it would still be recall **inside Copernicus-mapped disaster areas**, which remains a
best case.

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
