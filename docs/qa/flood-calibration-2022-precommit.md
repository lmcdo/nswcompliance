# Flood calibration against the 2022 NSW floods — pass mark, committed BEFORE the run

**Written:** 2026-08-08, before any point was sampled and before any result was seen.
**Reference data:** Copernicus EMS rapid-mapping `observedEventA` polygons from activations
EMSR567 (Feb–Mar 2022, Northern Rivers + Sydney basin), EMSR570 (Mar–Apr 2022, Lismore/Coraki
second wave) and EMSR586 (Jul 2022, Hawkesbury/Hunter). Free, no auth, produced by the European
Commission from satellite imagery — an authority this project neither produces nor influences.

---

## 1. What is NOT being tested, and why

**The 1% AEP verdict is not compared against the 2022 extents.** It would be the obvious thing to
do and it would be wrong. The 1% AEP is a *design event* — a modelled 1-in-100-year extent. The
2022 floods *exceeded* it in several catchments: Lismore peaked at 14.4 m, a record by roughly two
metres. So ground that was under water in 2022 can legitimately sit outside the mapped 1% extent,
and ground inside the 1% extent can legitimately have stayed dry in 2022.

Comparing them would produce a number, and the number would measure construct mismatch rather than
product error. That is the same trap the climate lane walked into with APRA's protection gap, and
it is being refused for the same reason: a quantity that answers a different question is not a
reference.

**Nor is specificity measured.** A point outside the observed 2022 extent that the product flags is
not necessarily a false positive — it may sit in a genuine 1% mapped extent that simply did not
flood that year. There is no way to separate the two from this data, so no specificity figure is
reported. Reporting one would be inventing precision.

## 2. What IS being tested

**The recall of the served flood screen against ground that demonstrably went under water.**

For a point inside an observed 2022 inundation polygon, the product is asked what it serves today.
The claim under test is the screening claim — that the product surfaces a flood indicator where
flood risk exists. A `flood_signal` of `none` at such a point means the product said nothing while
the water was, on the record, there.

This is a directional test of a screening tool, not a validation of a flood model. It can only fail
the product; it cannot certify it.

## 3. The pass mark — committed before the run

> **PASS: recall ≥ 0.90.** At least 90% of sampled points observed under water in 2022 must return
> a `flood_signal` other than `none`, OR `in_100yr_flood_zone` true, OR a non-null council/SES flood
> extent match. Any one of those counts as the product having said something.
>
> **FAIL: recall < 0.90.** Reported as a failure, with the number.

Rationale for 0.90 rather than a softer mark: this is the least demanding thing a screening product
can be asked. The bar is not "did it get the depth right" or "did it match the extent" — it is "did
it say anything at all about flooding, at a location that flooded". A product that misses more than
one in ten such points is not screening.

**Sample:** 50 points, stratified across activations and AOIs, sampled inside `observedEventA`
polygons. Points are sampled with a fixed seed so the run is reproducible.

**Known limits of the sample, stated in advance:**

- Copernicus AOIs cover the areas the EU was asked to map, not all of NSW. Recall measured here is
  recall *in mapped disaster areas*, which are the worst-affected places and therefore the ones most
  likely to carry an EPI or council flood layer. **This biases recall UP.** The figure is a
  best case, not an average case.
- `observedEventA` includes permanent water bodies in some products. Points falling in a river are
  trivially "flooded" and would inflate recall. Where the reference distinguishes them they are
  excluded; where it does not, the contamination is reported rather than assumed away.
- N=50 is small. At recall near 0.9 the 95% confidence interval is roughly ±8 points. The verdict is
  reported with that interval and a result within it of the mark is reported as indistinguishable
  from the mark, not as a pass.

## 4. What a pass would and would not license

A pass licenses: *"checked against the Copernicus EMS observed extents of the 2022 NSW floods —
recall X% at N points."* Nothing more. Specifically it does NOT license "validated", does not
license any claim about depth, extent or the 1% verdict, and does not extend beyond the councils the
sampled AOIs fall in.

A fail is a finding and is reported as one.
