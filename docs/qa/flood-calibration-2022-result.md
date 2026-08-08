# Flood calibration against the 2022 NSW floods — result

**Run:** 2026-08-08. Pass mark committed in `flood-calibration-2022-precommit.md` at commit
`fb0a44f7`, before any point was sampled. Raw per-point output: `flood-calibration-2022-result.json`.

## Verdict

> **RECALL 0.976 — 40 of 41 scored points. Wilson 95% CI 0.874 – 0.996. Pass mark 0.90.**
> **VERDICT: INDISTINGUISHABLE FROM THE MARK. Not a pass.**

The point estimate is above 0.90 and the interval contains it, so at this sample size the result
cannot be told apart from the mark in either direction.

This was nearly reported as a clean pass. The first version used a Wald interval, which put the
lower bound at 0.929 — above the mark — and printed PASS. Wald is invalid at a proportion this close
to 1. The Wilson interval puts the lower bound at **0.874**, below the mark, and the pre-commit
written before the run says in terms: *"a result within it of the mark is reported as
indistinguishable from the mark, not as a pass."* That is the stricter rule, it was written before
the number was known, and it is the one that applies. Caught by the cross-review, not by me.

**What would settle it:** more points. At this recall, roughly 150 scored points would put the
Wilson lower bound above 0.90. The sample is small because each point is a live pipeline run.

## What was run

50 points sampled with a fixed seed (`20220228`) from inside Copernicus EMS `observedEventA`
polygons — 11,353 observed flood polygons across 15 AOIs in activations EMSR567, EMSR570 and
EMSR586 — stratified round-robin across activation/AOI pairs so no single event dominates. Each
point was put through the live served pipeline (`run_flood`), and counted as a hit if it returned
any of: a `flood_signal` other than `none`, `in_100yr_flood_zone` true, or a council/SES flood
extent match.

**9 of the 50 were not scored, and that is the product behaving correctly.** Only an explicit
outside-NSW refusal is treated as out of scope — every one of the nine carried
`422: latitude … outside NSW`, checked individually. Any other failure now counts as a miss, because
dropping an in-scope error from the denominator would let ten database failures read as 100% recall
on the forty points that worked. EMSR567 covered
south-east Queensland as well as northern NSW, and the pipeline refused those points outright —
`422: latitude … outside NSW`. A refusal is not a miss; a NSW product declining to answer for
Queensland is the right answer, and those points are excluded rather than counted either way.

## The one miss

```
EMSR570 / AOI01   -29.019576, 153.221912
flood_signal = none    in_100yr_flood_zone = False    ses_in_flood_planning_area = False
```

Northern Rivers, in the March–April 2022 second wave. The product returned `none` at a location the
European Commission mapped as inundated. One miss in 41 is inside the committed mark, but it is a
real miss on the record and is not being smoothed away.

## What this result does and does not license

**Licensed:** *"checked against the Copernicus EMS observed extents of the 2022 NSW floods — the
served screen returned a flood indicator at 40 of 41 sampled points (97.6%, Wilson 95% CI
0.874–0.996). At N=41 that is indistinguishable from the 0.90 mark committed before the run."*

**Not licensed, and stated before the run rather than after:**

- **Not "validated".** The word is banned in this project and this result does not earn it.
- **Nothing about the 1% AEP verdict.** It was deliberately excluded from the test. The 2022 events
  exceeded the 1% design event in several catchments — Lismore peaked at 14.4 m, a record by about
  two metres — so a point flooded in 2022 can legitimately sit outside the mapped 1% extent.
  Comparing them would measure construct mismatch, not product error. The raw output shows exactly
  this: many hits carry `in_100yr = False` while the ground was demonstrably under water.
- **Nothing about specificity.** A flag outside the 2022 extent may be a correct 1% mapping of
  ground that simply did not flood that year. The two cannot be separated with this data, so no
  false-positive rate is reported.
- **Nothing about depth or extent.** Only whether the product said something.

## Limits of the sample, as committed in advance

- **Recall is biased UP.** Copernicus maps the areas the EU was asked to map — the worst-hit places,
  which are also the most likely to carry an EPI or council flood layer. This is a best case, not an
  average case, and it says nothing about recall in an unmapped catchment.
- **Permanent water is not excluded.** The reference labels its polygons only "Riverine flood"
  (11,081) and "Flash flood" (628); there is no permanent-water class. A point falling in a river
  channel is trivially wet, and some proportion of the sample will be exactly that. The contamination
  is real, unquantified, and inflates recall.
- **N=41 scored.** Small. The interval is reported with the figure.
- **Councils covered** are those the sampled AOIs fall in — the Northern Rivers, Hawkesbury-Nepean
  and Hunter. The result does not extend to councils with no sampled point.
