> # ⚠ SUPERSEDED — historical protocol record only
>
> **Do not quote any figure from this file.** It was written and committed BEFORE the re-run, on
> purpose, so that the protocol change (N=50 → N=150) was on record ahead of seeing the result. It
> therefore preserves what was known at that moment: **0.800 at N=50 and 0.895 at N=150, 34 of 38
> scored points.**
>
> Two later defects in the reference construction changed those numbers. Interior polygon rings
> were being discarded, and the runner globbed the archive directory instead of reading the
> committed manifest. **The authoritative result is `flood-calibration-2022-result.md`: recall
> 0.946, 35 of 37 scored points.**
>
> The suggestion below that roughly 150 scored points would settle the question is also
> superseded, and not by arithmetic — the points are not independent. Outcomes cluster by council,
> and under that structure no sample size clears the 0.90 mark. See "What would settle it" in the
> result document.
>
> This file is kept unedited beneath this banner because a protocol commitment that gets rewritten
> after the result is no longer a commitment.

# Flood calibration 2022 — Amendment 01: sample size

**Written:** 2026-08-10. **Amends:** `flood-calibration-2022-precommit.md` (commit `fb0a44f7`).

---

## This is an amendment, not a fresh pre-commitment. Read that first.

A pre-commitment is only worth anything if it is written before the answer is
known. **The answer is already known here**, so this document must not pretend
otherwise:

| Sample size | Result | Verdict |
|---|---|---|
| N = 50 (the original protocol) | 12 of 15 scored, **recall 0.800**, Wilson 0.548–0.930 | indistinguishable from the mark |
| N = 150 (what actually ran) | 34 of 38 scored, **recall 0.895**, Wilson 0.759–0.958 | indistinguishable from the mark |

Both numbers are on the record above so that nobody, later, can present the
chosen one as if it were the only one produced.

## What is being amended, and what is not

**Amended:** the sample size, from 50 to 150 raw draws.

**NOT amended — and this is the whole point:** the pass mark stays at
**recall ≥ 0.90**. It was committed at `fb0a44f7` before any point was sampled
and has never moved. The rule about reporting a result inside the confidence
interval as *indistinguishable from the mark* rather than as a pass is also
unchanged.

Moving a pass mark after seeing a result is the failure this project has
already recorded twice (the "0% drift" metric; the climate lane's draft table
restating its own mark as ≥ 0.7 while calling it pre-committed). **Enlarging a
sample is a different act.** It cannot make a failing product pass on its own —
it narrows the interval and makes whatever is true easier to see. But it was
done after seeing that N=50 gave an interval too wide to be useful, so it needs
recording rather than absorbing.

## Why the original 50 was wrong, in the protocol's own terms

The original document anticipated this and got the reason right for the wrong
size. It said:

> *"N=50 is small. At recall near 0.9 the 95% confidence interval is roughly
> ±8 points."*

That estimate assumed 50 **scored** points. In practice 50 raw draws yielded
**15** scored points, because the Copernicus activations mapped south-east
Queensland as well as NSW and most draws landed outside the councils this
product covers. Fifteen points gives an interval of 0.548–0.930 — a span from
"one in two" to "almost always", which cannot distinguish a working product
from a broken one.

The sample size was specified in the wrong unit: **raw draws, not scored
points.** That is the defect being corrected.

## The amended protocol

**Sample:** 150 raw draws, stratified across activations and AOIs, sampled
inside `observedEventA` polygons, fixed seed 20220228.

**Scope test unchanged:** a point counts only if `lookup_lga` places it inside
NSW LGA coverage. An unresolvable lookup is `None` — unknown scope, excluded,
and never silently treated as in scope.

**Expected yield:** roughly 38 scored points, on the observed NSW-hit rate. The
protocol now states the target in the unit that matters: **at least 30 scored
points**, below which the run reports UNKNOWABLE rather than a figure.

**Everything else — the pass mark, the hit definition, the licensing rules and
the stated sample biases — carries over from `fb0a44f7` unchanged.**

## What this still does not buy

The amendment fixes a units error. It does not fix the two limits the original
document already named, and neither is closed by more points:

- Recall is measured only inside Copernicus-mapped disaster areas — the
  best-mapped, worst-affected ground, and therefore a **best case**.
- The reference has no permanent-water class, so some sampled points may be
  river channel. Unquantified, and it inflates recall.

And one the original did not name: **there is still no specificity figure.**
Recall alone cannot distinguish a discriminating screen from one that says
"possible flooding" everywhere. A product that returned a flood signal for
every address in NSW would score 1.00 here.

## The honest reading of a 0.895 result

Not a pass. The lower bound of the interval (0.759) sits below the mark, so the
rule written at `fb0a44f7` applies: **indistinguishable from the mark.** The
larger sample narrowed the interval from 0.38 wide to 0.20 wide; it did not
close the question. Roughly 150 *scored* points — not 150 draws — would.
