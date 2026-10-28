# Flood calibration against the 2022 NSW floods — result

**Run:** re-measured 2026-10-28 (first run 2026-08-08). Pass mark committed in `flood-calibration-2022-precommit.md` at commit
`fb0a44f7`, before any point was sampled. Raw per-point output:
`flood-calibration-2022-result.json`. Runner: `scripts/run_flood_calibration_2022.py`, seed 20220228.

## Verdict

> **RECALL 0.649 — 24 of 37 scored points, counting only sources other than the mapped 2022 flood extents. Cluster 95% CI 0.083 – 0.902 across 7 councils, which is the interval that governs. Wilson 95% CI 0.488 – 0.782 if the points are treated as independent, which they are not. Pass mark 0.90.**
> **VERDICT: INDISTINGUISHABLE FROM THE MARK. Not a pass, and not a fail.**

> **⚠ RE-MEASURED 2026-10-28. The number went DOWN, from 0.946 to 0.649, and the old one was partly circular.**
>
> Every test point is drawn from a Copernicus mapped 2022 flood extent (EMSR567 Feb–Mar, EMSR570,
> EMSR586 July), and the product's own mapped-flood source holds the same floods: EMSR567 and NSW's
> July and October 2022 maps. Until 2026-10-28 EMSR567 was stored as one 86,349 km² shape (every
> layer of the download merged, including the satellite photo outline), and 11 of the old 35 hits
> came from it lifting another weak source to "moderate". The map is now the real flooded land
> (#1529), and a hit inside any mapped extent alone gives "low" (#1531), so the as-served answer
> partly scores the reference against itself. The headline therefore re-scores every point **with
> every mapped-extent source removed**: do the OTHER sources (planning overlay, council study, water
> history, BOM) flag a place that really flooded? As served, the run found 31 of the 37.
>
> A first pass that removed only EMSR567 gave 0.784; cross-review pointed out that the July points
> (EMSR586) were still being matched by NSW's own July 2022 map of the same flood, and it was right:
> Camden's four "hits" there were exactly that. 0.784 is superseded by 0.649.
>
> The four council flood-study grids (Hawkesbury, Redbank, Tweed, Wollongong) were not readable on
> the machine that ran this. One miss is in Hawkesbury (-33.4287, 150.8118), so with the grid it
> could be 25 of 37 (0.676). No other miss is in one of those councils.

> **⚠ CORRECTED TWICE. Read both, because the second correction moved the number UP.**
>
> **2026-08-10 — the reference counted holes as flooded.** GeoJSON interior rings were being
> discarded, so a point inside a hole — ground Copernicus did NOT map as inundated — could be
> sampled as observed flooding and the product scored as having MISSED it. Respecting the
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

Thirty-seven points is still too few to decide. The interval spans from "three in four" to "almost
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
| fifth | 0.895 (34/38) | Wilson 0.759–0.958 | reproducible, but the reference counted holes as flooded: interior rings were discarded, so points on ground Copernicus did not map as inundated entered a positive-only reference and were scored as misses |
| 2026-08 final | 0.946 (35/37) | **Wilson 0.823–0.985** | holes respected, and the archive set read from the committed manifest rather than a directory glob. Seed 20220228 unchanged. `flood_signal='unavailable'` is still correctly NOT counted as a flood indicator |
| 2026-10-28 first pass | 0.784 (29/37) | Wilson 0.628–0.886; cluster 0.308–0.963 | removed EMSR567 only; NSW's own July 2022 map still matched the July reference points |
| **2026-10-28** | **0.649 (24/37)** | **Wilson 0.488–0.782; cluster 0.083–0.902** | every mapped 2022 extent removed from the scored answer; the stored EMSR567 shape had been 86,349 km² and is now the observed extent only |

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

## The thirteen misses of 2026-10-28

Scored without any mapped 2022 extent. Every one is council-shaped: no scattered misses.

```
RICHMOND VALLEY       EMSR570  -29.0424, 153.2542   served=none  without mapped extents=none
RICHMOND VALLEY       EMSR570  -29.0660, 153.3032   served=none  without mapped extents=none
CANTERBURY-BANKSTOWN  EMSR567  -33.9406, 150.9695   served=none  without mapped extents=none
CANTERBURY-BANKSTOWN  EMSR567  -33.9324, 150.9738   served=none  without mapped extents=none
CANTERBURY-BANKSTOWN  EMSR567  -33.9370, 150.9699   served=none  without mapped extents=none
CANTERBURY-BANKSTOWN  EMSR567  -33.9390, 150.9703   served=none  without mapped extents=none
CAMDEN                EMSR567  -34.0815, 150.7039   served=low   without mapped extents=none
CAMDEN                EMSR567  -34.0917, 150.7100   served=low   without mapped extents=none
CAMDEN                EMSR586  -34.0435, 150.7065   served=low   without mapped extents=none
CAMDEN                EMSR586  -34.0485, 150.7086   served=low   without mapped extents=none
CAMDEN                EMSR586  -34.0448, 150.6751   served=low   without mapped extents=none
CAMPBELLTOWN          EMSR567  -34.1095, 150.7451   served=low   without mapped extents=none
HAWKESBURY            EMSR586  -33.4287, 150.8118   served=low   without mapped extents=none
```

- **Richmond Valley (2):** the same two points as August. The product holds no flood overlay for
  this council.
- **Canterbury-Bankstown (4):** hits in August only because the 86,349 km² shape covered them. No
  other source flags them. AOI12 was missing from the stored map; once re-loaded they are served
  "low" from the map alone.
- **Camden (5), Campbelltown (1), Hawkesbury (1):** served "low" from a mapped 2022 extent, with
  no planning overlay, council study or water history agreeing.

By council, without mapped extents: Ballina 8/8, Hawkesbury 14/15, The Hills 2/2, Camden 0/5,
Campbelltown 0/1, Canterbury-Bankstown 0/4, Richmond Valley 0/2. The screen's own sources find
flooding where a council's flood planning map is loaded (Ballina, Hawkesbury, The Hills) and say
nothing where it is not. The mapped 2022 extents fill some of that gap, but only for places that
flooded in 2022.

## The two misses of 2026-08 — and they are one finding, not two

This section has been wrong twice, in opposite directions. It first reported **one** miss when the
artifact held four — understating the failure. Then respecting polygon holes showed that **two of
those four could not be scored at all**: they fell inside interior rings — ground the reference
does not map as inundated — so they never belonged in a recall denominator built from observed
flooding.

**This is not the same as the product being right about them, and the distinction matters.** A hole
in a Copernicus polygon means "not mapped as inundated here". It may be genuinely dry ground, or it
may be terrain the satellite could not read — dense canopy, building shadow, an excluded class.
This report establishes **no specificity figure**, so nothing here supports a claim that the
product's negative answer at those points was correct. All that changed is that four points left a
positive-only reference they should never have entered.

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
all**, so the overlay-derived signals — the EPI layer, the 1% AEP verdict and the council/SES
extent — can return nothing for any address in that council, whatever the ground is doing. At the
two points sampled here that produced "no flood indicator" on ground the European Commission
photographed under water.

**Stated that narrowly on purpose.** An earlier version of this paragraph said the product "returns
no flood indicator for every address in it", which is more than two points can support and ignores
the non-overlay sources — satellite water history and BOM gauges — which are not council-scoped and
could fire where a polygon does not exist. They did not fire at these two. Whether they would
elsewhere in Richmond Valley is untested, and the honest claim is about the overlay layers and
these two points, not about every address.

The recall figure is measuring, in these two points, an absence of data rather than an absence of
flooding.

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

**Licensed:** *"checked against the Copernicus EMS observed extents of the 2022 NSW floods, and
counting only sources other than the mapped 2022 extents, the screen returned a flood indicator at 24 of 37 points
inside our council coverage (cluster 95% CI 0.083–0.902; Wilson 0.488–0.782). At N=37 this does not
establish whether the product meets the 0.90 mark committed before the run."*

> This wording is the one sentence intended for external quotation, so it is pinned by
> `test_the_licensed_statement_quotes_the_run`. It published the superseded 34-of-38 figure for one
> commit after the corrected run, because the agreement tests checked only the headline line while
> the customer-quotable sentence sat unguarded twenty lines below it. Caught in review, not by the
> guard that existed to catch it.

**Not licensed:**

- **Not "validated".** Nowhere near it.
- **Not a pass.** The point estimate (0.649) is below the 0.90 mark and the governing interval
  (0.083–0.902) only just contains it. 37 points from 7 councils cannot decide it either way.
- **Nothing about the 1% AEP verdict** — deliberately excluded. 2022 exceeded the 1% design event in
  several catchments (Lismore peaked 14.4 m, a record by ~2 m), so comparing them measures construct
  mismatch, not product error. Visible in the raw output: hits carry `in_100yr = False` on ground
  that was demonstrably under water.
- **Nothing about specificity.** A flag outside the 2022 extent may be a correct 1% mapping of ground
  that did not flood that year; the two cannot be separated with this data.

## What would settle it — and the answer is not more points

> **⚠ CORRECTED THREE TIMES, and the third correction reverses the advice.**
>
> This section first claimed *"roughly 150 scored points would put the Wilson lower bound above
> 0.90"*. At the recall then measured (0.895) that was **impossible**: a Wilson lower bound cannot
> exceed its own point estimate. After the hole fix raised recall to 0.946 I recomputed and
> published **153**. That was also wrong — 153 clears only because rounding 0.946 × 153 up to 145
> hits gives 0.9477, slightly above the measured rate. The bound does not *stay* above 0.90 until
> **n = 179**. Caught in cross-review.
>
> **But the real error was upstream of all three numbers**, and it is the one worth reading.

**Every figure above assumes 37 independent observations. They are not independent.**

Whether the screen finds a flooded property depends almost entirely on whether **its council has a
flood overlay loaded** — a property shared by every point in that council. Outcomes arrive in
blocks. Grouped by the council each point actually resolved to:

| Council | Points | Found |
|---|---|---|
| HAWKESBURY | 15 | 15 |
| BALLINA | 8 | 8 |
| CAMDEN | 5 | 5 |
| CANTERBURY-BANKSTOWN | 4 | 4 |
| **RICHMOND VALLEY** | 2 | **0** |
| THE HILLS SHIRE | 2 | 2 |
| CAMPBELLTOWN | 1 | 1 |

**Six of seven councils at 100%, and every miss in the seventh.** Hawkesbury alone supplies 15 of
the 37 points. Resampling whole councils with replacement gives a 95% interval of
**0.727 – 1.000**, against Wilson's 0.823 – 0.985. The conventional figure is far too
narrow, and the entire result rests on one 2-point council.

> An earlier version of this section clustered by Copernicus **activation/AOI** and reported
> 0.786 – 1.000. That was inconsistent with the mechanism being argued in the same paragraph: if
> recall is driven by council coverage, two AOIs inside one council are not independent draws.
> Clustering on the actual council widens the interval further. Caught in cross-review.

**Now the part that changes the plan.** Simulating the observed structure — one council in seven
holding no flood data — the cluster lower bound converges on the true rate, about **0.857**:

| Councils sampled | ≈ points | Cluster 95% lower bound |
|---|---|---|
| 7 | 35 | 0.571 |
| 14 | 70 | 0.643 |
| 28 | 140 | 0.714 |
| 56 | 280 | 0.768 |
| 112 | 560 | 0.786 |

It never reaches 0.90, because under that structure the product's true recall **is not above 0.90**.
**No sample size settles this question.** Sampling harder measures the same coverage gap more
precisely; it does not close it.

**What would actually settle it is not a bigger sample — it is a different question, and a cheaper
one.** The quantity that governs recall is *what fraction of NSW councils hold flood data at all*,
and that is not something to estimate by sampling satellite photographs of a flood. It is a direct
count against our own overlay table. That count, plus loading the missing councils, moves the
number. Another 150 draws would not.

The 179-point figure is retained above only as the corrected arithmetic under an assumption this
run shows to be false. It is not a recommendation.

## Limits, as committed in advance

- **Recall here is biased UP.** Copernicus maps the worst-hit ground, which is also the most likely
  to carry an EPI or council flood layer. Best case, not average case.
- **Permanent water is not excluded.** The reference labels only "Riverine flood" (11,081) and
  "Flash flood" (628); there is no permanent-water class, so some sampled points may be river
  channel. Unquantified, and it inflates recall.
- **Councils covered:** the sampled points fall in the Northern Rivers, south-western Sydney and the
  Hawkesbury. Nothing here extends to a council with no sampled point.
