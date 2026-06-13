# B2C Research — Extension & Correction (Data Limits + Killer New Opportunities)

**Date:** 2026-06-13
**Branch:** `claude/b2c-niche-research-pd4qbv`
**Extends:** `B2C_NICHE_RESEARCH_2026.md`, `B2C_GTM_PLAN_2026.md`
**Why this doc:** (1) corrects an overclaim in Product B once the real limits of the ePlanning
feeds are accounted for, and (2) maps the *killer* opportunities that open up with new targeted
APIs and calculations.

---

## Part 1 — Correction: what the approval feeds actually support

### The data reality (verified in `services/pre_da_history.py`)
- `_extract_da_fields()` reads only `ApplicationStatus`, `ApplicationType`, `DevelopmentType`,
  `DateLastUpdated`. The code comment is explicit: *"LodgementDate not in API response"* — and
  there is **no clean approved/refused determination outcome**.
- `OnlineCDC` (ApplicationType *Complying Development Certificate*): a CDC **is** the approval, so
  its presence is a genuine positive signal — "approved pathway used."
- `OnlineDA` (ApplicationType *Development Application*): gives a **status** ("Determined", "Under
  Assessment"…), **not an outcome**. "Determined" does not tell us approved vs refused, and the
  dates are unreliable (only `DateLastUpdated`).

### Therefore "no matching approval" ≠ "illegal works"
A built structure can have **no record in these feeds for three perfectly lawful reasons**:
1. **Exempt development** — it never needed any approval (e.g. a shed ≤20 m² / ≤3 m / ≥900 mm
   from boundary; a deck ≤25 m² / ≤1 m high — thresholds set by the Codes SEPP).
2. **Pre-digital records** — the ePlanning open data is essentially **~2018 onward**; older
   consents sit on paper at the council and are invisible to the API.
3. **Certificate/linkage gaps** — a CC/OC may exist while the DA linkage is messy or absent.

So the original "find the illegal deck" framing **overclaims**. We cannot assert illegality, and
absence of a record is weak evidence on its own.

### The defensible reframe: Product B = "Approval-Gap Screen" (triage, not verdict)
Reposition B from *verdict* to **triage that tells the buyer's conveyancer exactly where to point
a formal search**. The pipeline becomes a classifier, not an accuser:

```
For each structural change detected from satellite (with an approx. date):
  1. Search OnlineDA + OnlineCDC for any record at the address near that date.
  2. Estimate the structure's footprint (SAMGeo, already in granny_flat.py),
     height (DEM/terrain), and boundary setback (lot geometry).
  3. Compare against the Codes SEPP EXEMPT thresholds (pulled live — never hardcoded).

  Classify:
   • "Approval located"      → CDC present, or DA record near the change date.
   • "Likely exempt"         → within exempt limits → no approval was required.
   • "Approval gap"          → EXCEEDS exempt limits AND no record found AND change is
                               post-~2018 → worth a formal council search.
```

Only the **"Approval gap"** bucket is surfaced as actionable, framed factually:
> *"A structure exceeding the exempt-development limits was detected c.2021 with no matching
> application on the public ePlanning register (records reliable from ~2018). This may be a
> pre-digital consent or unrecorded — confirm with a council s10.7 planning certificate or a
> Building Information Certificate search before exchange."*

**Net effect:** fewer, higher-confidence flags; fully defensible; still uniquely valuable —
because the alternative (a blanket "get a building cert search") costs the buyer time and money on
*every* structure, whereas we point them at the *one* that matters. The value is **triage**.

**This makes the exempt-development screening calculation a prerequisite, not a nice-to-have** —
it is what turns a noisy "no record" signal into a credible product. (See Part 2, Calc #1.)

---

## Part 2 — Killer opportunities from new calculations & targeted APIs

Two buckets: (A) **new calculations on data we already pull** (cheap, fast), and (B) **new
targeted APIs that open entire new franchises** (bigger, need integration + validation).

### A. New calculations on existing data

| # | Calculation | Built from (existing) | Unlocks |
|---|---|---|---|
| 1 | **Exempt-development screening** | SAMGeo footprints (`granny_flat.py`) + DEM height + lot geometry + Codes SEPP limits (live) | Fixes Product B; standalone "is my shed/deck/pergola exempt?" check |
| 2 | **Maximum development envelope** | height limit × FSR × setbacks (Planning Portal + DCP, live) | Foundational input for #3, #4 below |
| 3 | **Predictive overshadowing** | neighbour's *max legal envelope* (#2) → shadow model (`shadow_model.py`) | **Upgrades Development Watch from reactive to predictive** |
| 4 | **Subdivision / dual-occ / second-storey upside** | lot size vs minimum lot size + LEP permissibility | "What can I add, and is it allowed?" for owners/investors |
| 5 | **Solar $ payback** | kWh (`solar_yield.py`) × tariff + battery | Consumer-grade payback years, not just kWh |

**Standout: #3 Predictive Overshadowing.** Today Development Watch reacts to *lodged* DAs. By
applying the *neighbour's maximum permissible building envelope* to the shadow model, we can warn
**before anyone files anything**:
> *"The single-storey house to your north could be built up to ~9 m under its current controls,
> which would place your pool in shadow from ~2 pm at the winter solstice."*
Nobody sells forward-looking, envelope-based solar-access risk to consumers. It is novel,
defensible (deterministic from published controls), and turns A into a "buy-before-you-buy"
must-have — homeowners would pay to know this *before* purchasing.

### B. New targeted APIs — new franchises (ranked by leverage)

#### B1. **Apartment / Strata Risk Report** ★ biggest new franchise
The current products are all house/land-centric — they **completely miss apartments**, ~30 %+ of
the Sydney market and the most anxious buyer segment post-Opal/Mascot.
- **New data:** NSW **Strata Hub** (public strata search: levies, 10-yr capital-works-fund health,
  insurance status) + Building Commission NSW **public register** of rectification / prohibition /
  stop-work orders + **iCIRT** developer/builder ratings.
- **The offer:** *"Before you buy this apartment, see the building's defect orders, levy history,
  capital-works-fund health, and the developer/builder's track record."*
- **Why killer:** 53 % of buildings have had serious common-property defects; a special levy can
  be six figures per lot; **no consumer product synthesizes these three sources** into a buy /
  walk-away triage. One-off at purchase **plus** recurring for owners ("watch my building's defect
  and levy status").
- **Research/validation needed:** Strata Hub exposes a public *search* (likely web UI, not a clean
  bulk API → may need permitted scraping or a data agreement); Building Commission register is a
  public web register (scrapeable); **iCIRT is a commercial/rated tool — confirm public-tier
  access before relying on it.** Validate access model before committing.

#### B2. **Land Value / Land-Tax Objection** ★ most recurring & sticky
- **New data:** Valuer General NSW land values + sales (free Valuation Portal / Land Values map).
- **The offer:** *"Your land is assessed at $X; comparable lots nearby sit at $Y. You may be
  over-assessed — and your objection deadline is [date]. Here's the comparable evidence."*
- **Why killer:** recurs **every annual revaluation**; investors have high WTP for anything that
  cuts land tax; the **60-day objection deadline** creates hard urgency; and it can be priced as a
  **success fee (% of tax saved)** — irresistible because it's risk-free to the customer.
- **Calc:** comparable-land analysis (subject vs nearby like-zoned lots) — deterministic,
  defensible, sourced.

#### B3. **Builder / Developer Background Check**
- **New data:** NSW Fair Trading licence + disciplinary register + Building Commission orders +
  iCIRT.
- **The offer:** *"Check your builder before you sign"* — licence status, past orders, rating.
- **Why:** anxiety-driven, low build cost (mostly the same sources as B1), serves the renovation /
  new-build market that the property products don't.

#### B4. **Insurance-Trajectory / "Insurable by 2050"**
- **New data:** none new — combines existing flood depth (`flood_truth.py`) + bushfire + **NARCliM
  2.0** future climate (`climate_risk_pipeline.py`).
- **The offer:** address-level insurability/premium outlook to 2050.
- **Why:** consumer-priced gap beneath the institutional incumbents (Climate Valuation/XDI);
  bundles as an upsell to the buyer report.

### Ranking (new-opportunity leverage)
1. **Apartment/Strata Risk (B1)** — opens a new market segment; highest strategic value.
2. **Land-Tax Objection (B2)** — most recurring, success-fee-able, high investor WTP.
3. **Predictive Overshadowing (A#3)** — most novel; upgrades the flagship recurring product.
4. **Subdivision/Upside (A#4)** — strong investor WTP; reuses envelope calc.
5. **Builder Check (B3)** / **Insurance Trajectory (B4)** — cheap add-ons / upsells.

---

## Part 3 — How this changes the plan

- **Immediately:** build **Calc #1 (exempt-development screening)** — it is the credibility
  prerequisite for Product B as corrected above. Soften all B copy from "illegal/unapproved" to
  "approval gap — verify with council."
- **Next horizon:** **Predictive Overshadowing (#3)** as the differentiator that makes Development
  Watch a *pre-purchase* must-have, and **Land-Tax Objection (B2)** as a second recurring revenue
  line for investors (success-fee pricing).
- **Bigger bet (validate first):** **Apartment/Strata Risk (B1)** — confirm Strata Hub /
  Building Commission / iCIRT access models, then it becomes a whole second franchise beside the
  house/land products.

## Guardrails (unchanged, reinforced)
- Never assert illegality, approval outcome, defect severity, or valuation as fact — surface the
  record (or its absence), the source, the date, the confidence, and the next verification step.
- No hardcoded regulatory values — exempt thresholds, envelope controls, lot minimums, etc. must
  come from the live authoritative source.
- Keep internal pipeline names out of consumer-facing copy.

## Sources
- ePlanning field limits — verified in `services/pre_da_history.py` (`_extract_da_fields`, lines ~580–598, 624).
- Exempt development thresholds (Codes SEPP): https://www.planning.nsw.gov.au/assess-and-regulate/development-assessment/planning-approval-pathways/exempt-development ; https://www.straightlineplanning.com.au/post/8-things-you-can-build-without-council-approval-in-nsw
- NSW Strata Hub public search (levies, capital works fund, defects; 53% serious-defect stat): https://www.nsw.gov.au/housing-and-construction/strata/strata-hub ; https://www.nsw.gov.au/departments-and-agencies/building-commission/news/survey-shows-serious-defects-down-newer-apartment-buildings
- Building Commission public register of orders + iCIRT: https://www.nsw.gov.au/departments-and-agencies/building-commission ; https://www.nsw.gov.au/departments-and-agencies/building-commission/register-of-building-work-orders/building-work-rectification-order-for-stm123-no17-pty-ltd
- Valuer General land values + 60-day objection deadline: https://valuation.property.nsw.gov.au/ ; https://www.revenue.nsw.gov.au/taxes-duties-levies-royalties/land-tax/your-assessment-notice/land-tax-objections
</content>
