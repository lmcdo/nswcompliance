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

---

## Part 4 — Data Source Ledger (so this research is not re-run)

**Verified June 2026. Check this table BEFORE researching external APIs again.** The capability
audit confirms most "missing" data is already in-house; the genuine gaps are the *severity* layers.

### Confirmed licence facts
- **NSW Valuer General land values + sales = CC BY** (commercial use + resale of derived output OK,
  attribution required). NSW-wide; sales ~8 weeks post-settlement; free monthly bulk by LGA from
  2017. → **Land-Tax product data is green and resale-safe.**
- **Overture / Microsoft / OSM building footprints = ODbL** (share-alike). Risk of forcing our
  derived database open → **NOT safe for a proprietary paid report.** Confirms paying **Geoscape**
  ($300/mo Team, derived-report-through-app permitted) is the correct footprint+height source.
- **Geoscape** (confirmed earlier, §7A of GTM plan): Free 20k credits ≈ 1,666 buildings/mo, no
  overage, not a commercial licence. Team $300/mo, 30k credits, $0.015/credit overage, 12
  credits/building → ~$0.18/address. Height pack refreshes quarterly, national.

### Already in-house vs genuinely missing
| Need | In-house already | Genuinely missing (no public resale-safe API exists) |
|---|---|---|
| DEM (bare earth) | `dem_service.py` | DSM-by-API (ELVIS = LiDAR, no API; compute via whitebox or use Geoscape height) |
| Building footprint/height | `spike_samgeo_buildings.py` (spike) + Geoscape (paid, clean) | — |
| Setbacks/DCP controls | `authoritative_setback_calculator.py` (12 LGAs) | **Statewide** setback controls — nobody has this |
| Flood **presence** | spatial_overlays Hazard + Portal `floodData` + `flood_truth.py` | Resale-safe per-address flood **depth/AEP** (NFID = insurer-only) |
| Bushfire **category** | spatial_overlays BFPL + Portal `bushfireCategory` + `bushfire_prescreen.py` | Per-property bushfire **intensity/FFDI** |
| Climate severity | `climate_risk_*` (NARCliM, suburb-res) | Per-property — solved only via **XDI reseller** (paid) |
| Strata | `intelligence_brief.py: classify_strata` | Strata **financials feed**, Building Commission orders API, iCIRT API — all scrape-only |
| Solar | `solar_yield.py` (Google Solar + pvlib) | Cheaper-than-Google API (minor; PVGIS free fallback exists) |

**Rule of thumb:** the missing items are the *severity* signals (flood depth, bushfire intensity,
per-property climate) and the *strata/builder* feeds. These have **no self-serve resale-safe API** —
the market answer is **XDI reseller** (climate/flood/bushfire) and **scraping** (strata/iCIRT). Do
not re-research these expecting a clean API; there isn't one.

### Sources (Part 4)
- Capability audit (in-house): session capability index — `dem_service.py`, `spatial_overlays`
  (27 layers incl. flood/BFPL/coastal), 134 Planning Portal constraint types, `classify_strata`.
- VG land values CC BY: https://data.nsw.gov.au/data/dataset/http-www-valuergeneral-nsw-gov-au-land-value-summaries-lv-php
- Overture ODbL: https://docs.overturemaps.org/ ; https://opendatacommons.org/licenses/odbl/
- Geoscape pricing/licence: confirmed in-account + Geoscape General Terms of Use v2.0 (July 2025).

---

## Part 5 — Deep-research verdicts, adversarial (June 2026)

Source: deep-research run (92 agents, 20/21 claims survived 3-vote adversarial verification).
**These overturn the earlier "Land-Tax + Solar robust core."**

### Market scale (high-confidence anchor)
NSW **194,729 settlements CY2024**; Greater Sydney residential **116,360** (+13.3%); **$230.3B**
residential value (largest state); national $714.7B (+17.3% YoY). [PEXA]

### Product verdicts
| Product | Verdict | Single biggest kill-risk |
|---|---|---|
| **Land-Tax Objection** | **MARGINAL→VIABLE** | Base structurally narrow (principal residence exempt → only investors/large holders) **and already commoditised** by valuers + land-tax lawyers. Threshold freeze is a real tailwind. |
| **Solar Payback Report** | **WEAK (as a paid report)** | **SunSPOT** (UNSW/APVI, govt+ARENA funded) does the exact job **free**; Solar Choice gives 3 free quotes. **No consumer WTP.** |
| **Predictive Overshadowing** | **UNVALIDATED** | Zero demand/pricing evidence survived; *Butcher v Lachlan Elder* (High Court) flags **liability for representations in buyer reports** — risky for a *prediction* of a neighbour's future build. |

### Strategy impact (changes to prior plan)
- **Solar is NOT a paid consumer product.** Reframe as **installer lead-generation** (Solar Choice
  model: installers pay for the introduction). Different business; keep only as a free funnel/lead.
- **Overshadowing: demote** from "build next" to **validate-demand-first**, and prefer folding it
  into **Development Watch** as a *factual* "DA lodged / shadow modelled" feature rather than selling
  a standalone *prediction* (liability).
- **Land-Tax: keep, but gated** on the licensing question below before any build.
- **Unchallenged → now the real core:** **Product B "Was it approved?"**, **Development Watch**, and
  the **Apartment/Strata** play. None were undercut by this research.

### Open land-tax gaps (must close before building — drives the GO/NO-GO)
1. How many NSW parcels/owners actually pay land tax; total revenue; investor share (the SAM).
2. Real objection success rates + typical over-valuation magnitude.
3. **Is giving objection advice a licensed/regulated activity** (valuer registration / legal advice
   / ASIC financial-advice boundary)? This is the make-or-break for a success-fee model.

### Land-tax regulatory finding — RESOLVED to CONDITIONAL-GO (follow-up run + direct verification)
The success-fee model is **lawful in NSW IF scoped to the land-VALUE objection (Valuer-General path,
via a CPV), not legal advice on liability/exemptions (Revenue-NSW path).**
- **Valuer licensing: cleared.** NSW abolished state valuer registration (Valuers Act 2003 repealed
  1 Mar 2016); "suitably qualified valuer" = API Certified Practising Valuer — a credential, not a
  legal licence. Use a CPV for evidence credibility, not because law requires it.
- **Success fee: lawful for us.** s183 Legal Profession Uniform Law contingency-fee ban binds **law
  practices only** — a non-lawyer valuation/advisory service is not caught.
- **TPB: N/A** (TASA = Commonwealth tax only; state land tax is outside it). **ASIC: N/A** (not a
  financial product).
- **The deciding risk:** advising on a *state tax* can be characterised as "legal advice." Stay in
  the **value-challenge lane** (comparable sales, CPV) = valuation work = safe. Stray into
  liability/exemption/aggregation advice = legal practice = s183 kills the success fee.
- **GATE before launch:** NSW lawyer to confirm the value-lane characterisation. Competitor scan
  found valuation firms doing fixed-fee objections but **no success-fee model in market** (open
  angle, or a hint others avoid it — confirm with the lawyer).
- **Still unquantified:** exact land-tax payer count + total revenue (Revenue NSW stats 403'd);
  base is large/growing ($3.09T NSW land value 2025, residential +4.2%, freeze +$1.5B/4yrs).

### Caveat
Revenue NSW + PEXA pages 403'd the fetchers → verified from cached snippets (high-confidence, one
step removed). Overshadowing verdict is "unvalidated", not "stress-tested as non-viable".

### Sources (Part 5)
- PEXA CY24 settlements: https://www.pexa-group.com/content-hub/property-insights-and-reports/property-insights-cy-24/
- NSW land tax thresholds/rates: https://www.revenue.nsw.gov.au/taxes-duties-levies-royalties/land-tax/understanding-land-tax/thresholds-and-rates
- NSW land tax objections (60-day, dual path, onus): https://www.revenue.nsw.gov.au/taxes-duties-levies-royalties/land-tax/your-assessment-notice/land-tax-objections
- SunSPOT free calculator: https://www.sunspot.org.au/ ; Solar Choice free brokerage: https://www.solarchoice.net.au/about-us/

---

## Part 6 — Consolidated B2C portfolio verdict (5 deep-research runs, June 2026)

All evidence in. Ranked by verified viability. **Corrections to earlier claims noted.**

### Per-product verdicts
| Product | Verdict | Evidence highlight | Single biggest kill-risk |
|---|---|---|---|
| **"Was it approved?" (Product B)** | **VIABLE (framing-gated)** | ~10% NSW properties have non-compliant works; B&P inspections ($350–900) explicitly DON'T check approval-on-record → real gap; $99 anchors cheap | False-positive↔liability — survive via *Butcher v Lachlan Elder* conduit+disclaimer framing ("records gap, verify with council", never "illegal") |
| **Development Watch** | **VIABLE** (unchallenged) | Recurring, our own data, nearest-neighbour DA alerts | Conversion/retention (not data) |
| **Land-Tax Objection** | **CONDITIONAL-GO** | Success fee lawful in the value-lane (CPV, not legal advice); no success-fee competitor in market; big growing base ($3.09T) | Must stay valuation-not-legal lane → NSW lawyer sign-off; SAM (payer count) still unquantified |
| **Apartment / Strata** | **MARGINAL→WEAK** | 17% of NSW in strata, BUT core report commoditised — Before You Bid ~$84, conveyancer reports $250–400 already cover fund/financials | Saturated cheap commodity; our locational layer is the only differentiator and has **no proven WTP** |
| **Solar Payback** | **WEAK as paid** | — | Free govt SunSPOT does the job → reframe to installer **lead-gen** only |
| **Predictive Overshadowing** | **UNVALIDATED** | Zero demand evidence | Speculative + liability → fold into Development Watch as a *factual* feature; validate before standalone |

### Refuted earlier claims (do not reuse)
- "53% of NSW apartment buildings have serious defects" — REFUTED (1-2); newer-building defects are trending DOWN.
- "83,998 NSW strata schemes" — REFUTED (0-3); exact NSW count unconfirmed.

### The portfolio that the evidence supports
1. **Core = Product B + Development Watch** — cash now + recurring, both on our own data, both survived adversarial review. Build first.
2. **Strong adjacent = Land-Tax** (investor segment, recurring annually, success-fee, legal-gated) — second product behind a lawyer's value-lane sign-off.
3. **Apartment/Solar/Overshadowing are NOT standalone products** — they are a **locational add-on** (apartment), a **lead-gen funnel** (solar), and a **factual feature** (overshadowing), respectively. Sell where we're unique, not where we'd be the 5th cheap commodity.

### Caveat
The apartment run's synthesis stage failed (returned placeholder output); its verdict here is reconstructed from the intact verify log (18 claims → 14 confirmed, 4 killed) — confident in the votes, but not the harness's own synthesis. Revenue NSW / PEXA pages 403'd across runs → several figures verified from cached snippets.

---

## Part 7 — Satellite apps re-judged + the killer-idea pattern + B2C reality

### The 6 satellite apps mapped onto the research verdicts
| Satellite app | Research verdict | Action |
|---|---|---|
| **Neighbour Development Threat Radar** (`threat_radar.py`) | = Development Watch → **VIABLE** | ★ Lead with it — already built (subscribe/check/list) |
| **Flood Truth Engine** (`flood_truth.py`) | **Underrated** — *did-it-flood* is a factual record (ours); flood *depth* is the locked market (NFID) | Validate next; strong B2B (insurer) pull |
| **Shadow Ambush Detector** (`shadow_detector.py`) | Overshadowing **UNVALIDATED** | Demote → factual feature inside Development Watch |
| **Solar Yield Underwriter** (`solar_yield.py`) | **WEAK as B2C** (free SunSPOT) | Lead-gen, or test the B2B "underwriter" angle |
| **Granny Flat Yield Predictor** (`granny_flat.py`) | **Untested** + prediction-liability | Validate demand before betting |
| GEE client | infra | Don't build (per CLAUDE.md) |

### The killer-idea pattern (the durable lesson)
Everything that **survived** is a **uniquely-assembled factual record** (Was-it-approved, Threat
Radar/Development Watch, Flood-truth). Everything that **died** is a **prediction/advisory** (solar
payback, overshadowing, granny-flat yield). **The market punishes predictions (free incumbents +
liability + no WTP) and pays for facts nobody else compiles.** Generate future ideas inside this
pattern only. Note: "Was it approved" runs on the *same* Sentinel-2 change-detection pipeline as the
satellite apps — the tech was sound; it was pointed at predictions instead of records.

### B2C reality (the "massive retail" question)
- **Direct mass retail is not realistic.** The buyable population is hard-capped at people
  *currently transacting* (~194,729 NSW settlements/yr); 1–5% at $99 = ~$190k–$960k/yr. Solid SME,
  not a viral-retail rocket. The decision is delegated to conveyancers, so the channel is B2B2C.
- **Realistic B2C = point-of-sale + recurring**, advisor-distributed (Was-it-approved + Development
  Watch). Alive and worth building.
- **Genuine scale = B2B** (insurers/lenders/councils paying recurring for the same factual records).
  → B2B-buyers research sweep launched separately.

### Decision
Stop generic B2C idea-hunting (diminishing returns; WTP only resolves by shipping). **Build Product
B + Development Watch; gate Land-Tax on a lawyer; run one B2B sweep.** Everything else = feature,
funnel, or add-on.

---

## Part 8 — Objectivity caveat (read before treating any verdict as final)

The verdicts above are **tilted bearish** by three mechanisms — don't mistake "weak/unvalidated" for
"dead":
1. **The research robot's verify step is skeptical by design** — it tries to *refute* every claim and
   kills what it can't quickly stand up. Great at catching false claims (correctly killed the "53%
   defects" stat), but it also **suppresses true-but-hard-to-source claims**, which return as
   "unvalidated" and read as negative.
2. **The prompts asked for the bear case** ("strongest reasons each would FAIL") — output is a failure
   list, not a balanced go/no-go.
3. **Gov sites 403'd the fetchers** (Revenue NSW, PEXA, Data.NSW) — exactly the sources holding the
   *positive/quantitative* evidence (payer counts, revenue, success rates), so "insufficient/
   unquantified" is partly an access artifact.

**Separate two things every time:** REFUTED (proven false → discard) vs UNPROVEN (not found here,
often a 403 → revisit).
- **Trustworthy (rest on confirmed *positive* facts):** Solar weak (free SunSPOT); flood locked by
  NFID; approval-gap has no incumbent; land-tax mechanics; Product B demand/gap.
- **Over-coloured (really "unproven", not "bad"):** overshadowing demand, apartment willingness-to-pay
  for the locational layer, land-tax market size.

**Also:** synthesis crashes under broad prompts (apartment + B2B runs died at write-up). Fix = narrow,
single-focus, **balanced** (bull+bear) re-runs — which also reads more objectively. Balanced re-runs
of the over-coloured items are in progress.
</content>
