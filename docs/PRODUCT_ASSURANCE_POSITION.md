# Product assurance position — what each product claims, and what backs it

**As at 2026-08-08.** Every figure below is a measurement with a command, file or query behind it.
Nothing here is an estimate.

**Ladder wording, used strictly:**

- **source-linked** — the output names the source it came from, and that source is real and reachable.
- **reproducible** — re-running the same input returns the same number, and the code that produced it can be pointed at.
- **checked against X** — compared with an authority this project neither produces nor influences, with the result stated.

**"Verified" is banned.** No product on this page is verified. Where a product cannot be checked,
*"cannot be validated with available data"* is a finished answer, not a gap to be filled later.

---

## The table

| Product | What it claims | Checked against — and the result | NOT checked against — the honest limit | Holds for |
|---|---|---|---|---|
| **Shadow** | Where a modelled building's shadow falls on a property at five dates/times, and the compass direction of that shadow | **Checked against pvlib's NREL SPA** (Reda & Andreas 2004) — a different algorithm by different authors, imported at module scope so an absent library is a red build, never a green skip. Worst deviation **0.206° altitude, 0.318° bearing** against a **0.50° mark committed before the first run**. 5 scenarios × 8 NSW envelope corners. `tests/test_shadow_calibration.py`, PR #883 | **No real shadow was ever observed.** This checks sun geometry against a second calculation, not the shadow against a photograph. Nothing checks the building-height assumption, the lot boundary, or whether the modelled building resembles what gets built. The tolerance floor case (a 0.15° planted drift asserted to still pass) **never passed** — real headroom is 0.10°, not 0.15° (DQ-53b) | Statewide NSW. The five scenarios are fixed dates/times, not arbitrary ones |
| **Flood** | Whether a property sits in a 1% AEP flood extent; a screening signal from EPI, council/SES study extents, satellite water history and BOM gauges | **Checked against Copernicus EMS observed 2022 flood extents** — recall **0.946, 35 of 37 points** inside council coverage, **95% CI 0.786–1.000** clustering by AOI (Wilson 0.823–0.985 treating the points as independent, which they are not — both misses fall in one 2-point cluster), against a **0.90 mark committed before the run**. **VERDICT: indistinguishable from the mark. Not a pass.** `docs/qa/flood-calibration-2022-result.md`, PR #897 | **No sample size settles it, and this replaces the earlier '~150 more points' answer.** Outcomes cluster by council: seven of eight AOI clusters scored 100% and both misses sit in the eighth. Under that structure the true recall is bounded by the fraction of councils holding flood data (~0.875 here), so a larger sample measures the coverage gap more precisely rather than clearing the mark. What moves the number is loading the missing councils' flood data. Recall is measured only inside Copernicus-mapped disaster areas, the best-mapped ground, so it is a **best case**. The reference has no permanent-water class, so some sampled points may be river channel, which inflates it. **The 1% AEP verdict itself is not checked at all** — 2022 exceeded the 1% event, so comparing them measures construct mismatch. **No specificity figure exists.** no sample size settles it — see the result doc | Northern Rivers, south-western Sydney, Hawkesbury — the councils the 37 points fell in. Council flood-study grids: Hawkesbury, Redbank, Tweed, Wollongong |
| **Granny flat** | Whether secondary structures are present on a lot, and what the scan did or did not establish | **Nothing.** Detection recall has never been measured. The "13 of 16 human confirmations" that once supported it were **zero** — the frontend's fallback default, not people (PR #878) | **Cannot be validated with available data.** Measuring recall needs a human to label ~50–100 blocks of imagery against the detector, and with no users that human is the founder. Until then the product reports **what the scan did**, not what is there: reviewed / found-not-reviewed / nothing-found / inconclusive / not assessed (PR #881) | Wherever NSW SIX Maps imagery exists. 8 of 60 historic detect rows are genuinely ambiguous and never granted "reviewed" |
| **Solar** | Annual generation potential for a roof | **Source-linked only.** It is a pass-through: `solar_yield.py` sums Google Solar API per-panel `yearlyEnergyDcKwh` (services/solar_yield.py:276). **Not reproducible, and previously described here as though it were.** The number is whatever Google returns at query time; nothing pins a provider dataset or model version, and no response is stored, so if Google updates its model or imagery the answer changes and we could not detect that it had | **Cannot be validated with available data, and this is the correct ceiling.** Checking it needs metered generation from installed systems at known addresses, which this project does not have and cannot obtain. **pvlib and PVGIS were named as the method for months and are not imported anywhere** — removed PR #878. Do not describe this as modelling; it is a third party's number, passed through | Wherever Google Solar has coverage — Google's footprint, not ours |
| **Climate** | Per-hazard exposure facts — flood, bushfire, coastal, heat, landslide, fire history | **Attempted and closed: UNKNOWABLE.** The APRA reference was found **not extractable** — the SA3 results in *Mind the Gap* exist as rasters (Figs 9–10), not tables. The pre-written correlation test that three documents described **never existed** (PR #887) | **Cannot be validated with available data, permanently.** Five of six components are membership of a mapped regulatory overlay — an EPI flood layer is not a prediction that can be wrong, it *is* the ground truth for its own question. What is arbitrary is only the equal weights, four interaction bonuses and band cut-offs, and **none has an external referent even in principle**: the score forecasts nothing, so it has no error term. **The composite score renders on no customer surface** | Per-hazard facts hold wherever the underlying overlay exists. The composite is not served |

---

## What is true across all five

**Nothing on this page is verified, and three of the five cannot be.** Solar and climate carry
permanent ceilings for reasons of construct, not effort — no amount of work makes a pass-through
into a measurement or gives a non-predictive score an error term. Granny-flat's ceiling is
temporary and lifts the day someone hand-labels imagery.

**Two products have been compared against an outside authority.** Shadow passed its pre-committed
mark. Flood did not clear its own, and is reported as indistinguishable from it.

**Every pass mark was written down before the run.** Shadow's 0.50° at PR #883, flood's 0.90 at
commit `fb0a44f7`. Neither was moved afterwards. The one time a mark was restated more leniently
mid-draft, the cross-review caught it and it was reverted (PR #887).

**A source that FAILED is never rendered as a negative — but a source that is ABSENT still is,
and that gap is live.** When a query errors or returns nothing, the product now says "not assessed"
with the source named. What it does not yet distinguish is a council for which **no flood overlay
was ever loaded**: there, every layer answers cleanly and the property is reported as showing no
flood indicator. The calibration on this page found exactly that — two points in **Richmond Valley**
returned `flood_signal=none`, `1pct=false`, `ses=false` against ground the European Commission
photographed under water, because that council holds **zero flood polygons**. Lismore holds one.
Until coverage is checked before the answer is composed, an unmapped council is indistinguishable
from an unaffected one. The narrower claim below is what has been fixed:
`in_100yr_flood_zone` started life as `False` and only four positive signals could move it, so
**12 of the 142 stored reports that served "not in a flood zone" had never established it** —
among them addresses in Lismore, Murwillumbah and Telarah (PR #892).

---

## Corrections this position rests on

Each of these was a claim the product made that was not true. They are listed because an assurance
page whose history is hidden is worth less than one that shows it.

| Was claimed | Was true | Closed |
|---|---|---|
| pvlib was our shadow method — on the PDF, the marketing page and the seeded disclaimer | Never imported anywhere in the repo | #878 |
| A SAR flood detector with a named threshold and endpoint | Zero call sites; unreachable code | #878 |
| 13 of 16 granny-flat results confirmed by a person | Zero. The frontend's fallback default | #878 |
| "Surface-change screening detail", sold as a **paid** feature | 0 readings in 538 attempts. A price was attached to a capability that never once worked | #886 |
| Shadow direction, per property | A stored constant — 519 of 519 wrong, S where SW was correct | #883, repaired |
| A pre-written APRA correlation test with a 0.7 line | Existed in no branch. One line under "Planned V2 improvements" | #887 |
| "Not in a flood zone" | Sometimes: nobody checked | #892 |
| Three hazard flags on lot search | A NULL overlay served as three clean negatives | #897 |

---

## How to read a number on this page

Ask three things. Every row above answers all three or says it cannot.

1. **What was it compared against, and is that thing independent of us?** Shadow: pvlib, yes.
   Flood: Copernicus EMS, yes. Solar: nothing. Climate: nothing exists that could serve.
2. **Was the pass mark written down first?** If not, the result is a description, not a test.
3. **What is the sample, and how wide is the interval?** Flood's point estimate looks strong at
   0.946 and does not settle the question at N=37: the lower bound is 0.823. The interval is the
   honest part.

---

## Evidence

| Claim | Where to check it |
|---|---|
| Shadow calibration | `tests/test_shadow_calibration.py` · PR #883 · proofs re-run through the hardened harness, DQ-53b |
| Flood calibration | `docs/qa/flood-calibration-2022-precommit.md` (mark, committed first) · `-result.md` · `-result.json` · `scripts/run_flood_calibration_2022.py`, seed 20220228 |
| Flood stored-report census | `scripts/measure_flood_zone_unassessed.py` |
| Climate reference search | `scripts/measure_climate_reference_availability.py` · 22 documents, 1,303 pages |
| Granny-flat states | `scripts/measure_granny_confidence_states.py` |
| Falsifiability proofs | `scripts/falsifiability.py` — hash-checked plant and restore; a proof that cannot plant, raises |
| Open defects | `.claude/DATA_QUALITY_TRACKER.md` — DQ-53b, 54, 55, 56, 57 |

**Reproducing the flood number:** `python scripts/run_flood_calibration_2022.py`. Fixed seed, and
it aborts rather than sampling if any reference archive will not open.
