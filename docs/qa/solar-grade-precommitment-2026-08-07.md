# Solar A–F suitability grade — decision rule, PRE-COMMITTED

**Written:** 2026-08-07, BEFORE any investigation of where the cut-offs came from.
**Authority:** user ruling, this session. Same discipline as the climate lane's
`ρ > 0.7` mark: the rule is fixed before the evidence is seen so the outcome
cannot be renegotiated once it is known.

**Base commit when written:** `aa316200` (head of `fix/climate-apra-calibration`, PR #887).

---

## The question this rule decides

**Where do the A–F cut-offs come from?**

The grade is computed in two places from Google Solar API values (pitch, azimuth,
`maxSunshineHoursPerYear`):

- `frontend-nextjs/components/tools/SolarYieldTool.tsx:65-105` — free tool card
- `frontend-nextjs/app/api/reports/solar-yield/generate/route.ts:58` — paid PDF

It is rendered as a letter with severity colouring (`SolarYieldTool.tsx:368`,
`lib/pdf/solar-yield-report.tsx:246`) and is sold as a listed feature
(`components/reports/landing/data/solar.ts:52`, `free: true, paid: true`; also a
heroStat at `:12`).

## Scope note (user, this session)

"No model changes" in the dispatch brief meant **do not recalculate solar maths**.
It was never intended to shield a served claim from scrutiny. A grade with
severity colouring is a claim, and it is the shape #699 barred the climate
composite from taking (`ClimateRiskResultCard.tsx:3-9`).

## The rule

### Branch 1 — cut-offs come from a published, citable source
An industry kWh/kW/year band, a standard, or a government benchmark.

→ The grade is **SOURCE-LINKED**. **The letter stays.** Cite the source on the surface.
→ **The traffic-light colouring still goes**, unless the source itself makes the
  severity judgment. Colour asserts good/bad; a yield band does not say whether a
  number is good for *this* customer's purpose.

### Branch 2 — cut-offs were chosen by us with no external basis
→ **RETIRE THE GRADE** from served surfaces. The factual pitch, azimuth and
  sunshine figures remain.
→ This is exactly the climate remedy. Applying #699 to one product and not the
  other would make it a one-off rather than the principle it is.

### Branch 3 — cannot determine where they came from
→ **UNKNOWABLE**, and it **resolves the same way as Branch 2**. An unattributable
  threshold is not source-linked. Missing evidence is never a pass.

## Obligations regardless of which branch fires

1. Report which branch fired and the evidence for it.
2. State blast radius **before shipping**: what a customer sees on the card and on
   the PDF, before and after.
3. Execute the selected branch in this pass — not defer it.

## Second question, same pass

Does anything else in solar convert a pass-through number into **our own
judgment** — a rating, a band, a recommendation, or a colour? The grade may not be
the only one. Findings recorded with file:line.

---

## OUTCOME

*(To be completed after investigation. Left empty deliberately at pre-commitment
time — a filled-in outcome here would mean the rule was written after the fact.)*
