# B2C Niche Opportunities — Unique Data, Leverage & Irresistible Offers

**Date:** 2026-06-13
**Author:** strategy research (branch `claude/b2c-niche-research-pd4qbv`)
**Question asked:** Find unique B2C data we already own, calculate the leverage, and design
irresistible offers for an underserved, creative, scalable niche.

**TL;DR.** The whole company is currently aimed at ~2,000 NSW certifiers and planners (B2B,
high-touch, slow sales). But the same pipelines already built for them produce three pieces of
data **no consumer property product in Australia sells**. The biggest unlock is not a new
pipeline — it is re-pointing existing ones at homeowners and buyers, where the emotional stakes
(your sun, your privacy, a $1M fine you inherit) make the offer sell itself.

The recommended wedge is a **recurring** consumer subscription — *impact-scored* development
alerts ("will the plan next door block my winter sun?") — funded by a **high-margin one-off**
transaction product — *unpermitted-works detection* for buyers. Both run on pipelines that
already exist in `services/`.

---

## 1. Method

1. Audited what data we **already produce** (not what we could build) — `services/` pipelines,
   `regulatory_provisions`, spatial overlays, ePlanning feeds.
2. Filtered to data that is **(a) consumer-relevant, (b) emotionally charged, and (c) not sold
   by any incumbent** — the intersection is the moat.
3. Validated market size, willingness-to-pay and the competitive gap with external sources
   (see §8).
4. Scored each niche on a leverage formula and designed the offer for the top three.

**Leverage formula used:**

```
Leverage  =  (Reachable buyers × Willingness-to-pay × Recurrence)
             ───────────────────────────────────────────────────  × Data uniqueness × Emotional pull
                        (Cost-to-serve + CAC)
```

"Irresistible" = high emotional pull × high specificity ("about *your* house, this week") ×
*nobody else can tell me this*. Recurrence is the multiplier that turns a tool into a business.

---

## 2. The data moat — what we own that consumers can't get elsewhere

Everything below is **already running** in `services/`. The point is that each one was built
for a professional use case but encodes a fact a homeowner or buyer desperately wants and
**cannot currently buy**.

| Asset (existing pipeline) | The unique fact it produces | Who sells this to consumers today |
|---|---|---|
| `threat_radar.py` — ePlanning DA + CDC feed, 200 m radius, weekly cron, **already a subscription model** | "A plan was filed near you" | PlanningAlerts (free), Landchecker — but **raw alerts only** |
| `shadow_detector.py` + `shadow_model.py` — pybdshadow ADG solar scenarios, Southern-Hemisphere-correct | "That plan's building will cast a shadow **over your back yard** at 9am on Jun 21" | **Nobody** |
| `pre_da_history.py` — 8-yr Sentinel-2 NDVI/NDBI + Tessera change detection **cross-referenced against DA/CC/OC approval records** | "A structure appeared in 2021 with **no matching approval record**" | **Nobody** |
| `granny_flat.py` — SAMGeo structure detection + SEPP Housing yield + rent data | "Your backyard fits a 60 m² secondary dwelling worth ~$X/wk" | Builders (sales-biased), not neutral |
| `climate_risk_pipeline.py` — NARCliM 2.0 (NSW state climate projections) + flood-study rasters + bushfire overlays | "By 2050 this address sees N extra days >35°C, plus flood depth at 1% AEP" | Climate Valuation/XDI — institutional, expensive |
| `flood_truth.py` — multi-source flood (EPI WFS 71 LGAs, SAR, BoM gauges, council study rasters with per-AEP depth) | "Flood depth at *this* address for each AEP event" | Generic flood-overlay only; depth is rare |
| `solar_yield.py` — Google Solar API clipped to the cadastral lot | "Your roof, lot-clipped, yields N kWh/yr" | Solar retailers (sales-biased) |

**Two of these — shadow-scored alerts and unpermitted-works detection — have no consumer
competitor at all.** That is the irresistible, defensible core.

---

## 3. Niche opportunity scoring

Scored 1–5 on each leverage factor (5 = best). "Build state" reflects how much of the
pipeline already exists.

| Niche | Reach | WTP | Recurrence | Data uniqueness | Emotional pull | CAC ease | Build state | **Score** |
|---|---|---|---|---|---|---|---|---|
| **A. Development Watch** (impact-scored neighbour alerts) | 5 | 3 | **5** | 5 | 5 | 4 | **90%** | **★ 32** |
| **B. "Was it approved?"** (unpermitted-works buyer report) | 4 | **5** | 2 | **5** | 5 | 4 | 85% | **★ 30** |
| C. Future-Proof (forward climate + hazard report) | 4 | 3 | 2 | 4 | 4 | 3 | 80% | 23 |
| D. Backyard Income (granny-flat yield) | 3 | 4 | 1 | 4 | 4 | 3 | 90% | 22 |
| E. Solar second-opinion | 3 | 2 | 1 | 3 | 3 | 3 | 95% | 18 |

A and B are the clear winners and they **pair**: B is a one-off you buy at the moment of
highest pain (just before settlement); A is the subscription you keep afterwards because you now
*own* the home you were scared about. Run B as the cash-printing front door, convert to A for
recurring revenue.

---

## 4. Niche A — "Development Watch": impact-scored neighbour alerts  ★ PRIMARY

### The insight (why it's underserved)
- Free incumbents (PlanningAlerts, ~544 councils; Landchecker) send **raw** alerts: *"DA-2026/123
  lodged at 14 Smith St."* The homeowner still has to read the plans, find the shadow diagrams,
  and work out whether it actually hurts them — most don't, and miss the objection window.
- **The legal gap that makes this irresistible:** under the Exempt & Complying Development Codes
  SEPP, a neighbour's **complying development** (a whole second storey, in many cases) triggers
  notification **only after it's certified — immediately before construction**. Councils legally
  cannot warn you in time. Our `threat_radar.py` already reads the ePlanning **CDC** feed
  directly, so we can.
- Overshadowing, privacy/overlooking and building bulk are the top valid objection grounds, and
  shadow diagrams are modelled for Jun 21 — **exactly what `shadow_detector.py` computes.**

### The offer
> **"We watch every plan filed within 200 m of your home and tell you — in plain English —
> whether it will block your winter sun, overlook your yard, or tower over your fence. Before the
> objection window closes."**

- **Free tier:** raw "something was filed near you" alert (matches incumbents — denies them
  oxygen, builds the list).
- **Paid — "Sunlight Guard", ~$39–59/yr:** every nearby DA/CDC is auto-scored for **impact on
  *your* lot** — shadow cast over your boundary (with the diagram), proximity, height/bulk versus
  the prevailing controls — and you get a plain-English verdict plus, when impact is detected, an
  **objection-ready evidence pack** (the shadow diagram + the exact control it appears to exceed,
  cited to source) before the submission deadline.

### Why it's irresistible + scalable
- **Emotional, specific, time-critical** — "*your* sun, this week, deadline Friday." Saves the
  thing people fear losing most about their home.
- **Recurring by nature** — you subscribe once and forget; churn is low because the threat is
  permanent and unpredictable.
- **Reach = every NSW dwelling** (~2.8M), not 2,000 certifiers. TAM expands automatically with
  every LGA we add for the B2B product.
- **Defensible** — incumbents would have to build shadow modelling + ADG logic + the CDC-feed
  early-warning; we already have all three.

### Leverage calc (illustrative, conservative)
- Even **0.5%** of ~2.8M NSW dwellings = 14,000 subscribers × $49/yr = **~$686k ARR**, on a
  pipeline that already exists and a cron that already runs.
- Cost-to-serve is near-zero: ePlanning is free/no-auth, shadow modelling is compute-only, alerts
  are email. No marginal regulatory data cost.

### Build delta
`threat_radar.py` already does subscribe + weekly check + dedup. Missing piece is wiring the
**shadow/impact score** (already in `shadow_model.py`) into the alert and templating the verdict.
Estimate: small — this is integration, not new science.

---

## 5. Niche B — "Was it approved?": unpermitted-works buyer report  ★ CASH FRONT DOOR

### The insight (why it's underserved + high-WTP)
- In NSW there is **no statute of limitations** on unauthorised building work. A buyer inherits
  the liability: councils can order removal years later, insurers refuse cover, lenders reduce or
  refuse finance, and penalties run to **$1M for individuals**. Conveyancers flag the *risk* but
  **cannot detect it** — there is no public "is this structure approved?" lookup.
- ~**186,000 NSW property settlements/yr** (FY24, PEXA), each a buyer at peak anxiety and peak
  willingness to spend a few hundred dollars to avoid a six-figure mistake.
- Generic pre-purchase reports (Landchecker premium ~$24.90; Before You Bid) sell **planning
  data**, not **change-vs-approval reconciliation**. Nobody compares what was *built* to what was
  *approved*.

### The offer
> **"Before you buy, find the deck, pool, granny flat or extension the seller built without
> council approval — the liability you'd inherit at settlement."**

- One-off report, **~$79–149**, ordered the moment a buyer is serious (post-inspection,
  pre-auction).
- Output: an 8-year satellite timeline of structural change at the address, each change marked
  against the DA/CC/OC approval record, flagging **changes with no matching approval** — stated
  factually ("structure detected c.2021; no corresponding consent located on the public record"),
  never as a legal conclusion.

### Why it's irresistible
- **Loss-aversion at maximum** — spend $99 to not inherit a $1M problem and a demolition order.
- **Unique** — built directly on `pre_da_history.py`, which already fuses change detection with
  the ePlanning approval feed. This is the single most defensible consumer product we can ship.

### Leverage calc (illustrative, conservative)
- **1%** of 186k NSW settlements = 1,860 reports × $99 = **~$184k/yr**, high margin, one analyst's
  worth of QA. Distribution via buyer's agents and conveyancers (B2B2C) multiplies reach without
  consumer CAC.

### Build delta
`pre_da_history.py` already produces the change timeline + DA/CC/OC events + Stripe-gated PDF.
The delta is the explicit **"change with no matching approval" reconciliation flag** and consumer
framing. Estimate: moderate; the hard pipeline is done.

---

## 6. Niche C — "Future-Proof" (attach product, not a lead)

`climate_risk_pipeline.py` already runs **NARCliM 2.0** (the actual NSW state climate
projections) + flood-study rasters + bushfire. A consumer "how will this home fare in 2050 —
heatwave days, flood depth, fire" report is emotionally resonant and insurance-relevant. But
Climate Valuation/XDI already occupy the serious end, frequency is one-off, and it competes for
the same "pre-purchase" moment as B. **Recommendation: bundle it as an upsell inside B**, not a
standalone launch.

Niche D (granny-flat yield, `granny_flat.py`) is a real booming market — ~4,320 NSW secondary
dwellings approved/yr, builds tipped 10× by 2026, 20–24% gross yield — but it's a narrower
audience (yield-seeking owners) and builders give biased "free" quotes. Hold as a **second
vertical** once A+B prove the consumer motion.

---

## 7. Recommended sequence — wedge → land → expand

1. **Ship B ("Was it approved?") first.** Highest WTP, clearest uniqueness, transaction-triggered
   demand, distributable through conveyancers/buyer's agents. It funds everything.
2. **Convert every B buyer into an A subscriber** at settlement: *"You just bought it — now keep
   watch over it."* Same email, near-zero CAC.
3. **Grow A as the recurring engine.** Free raw alert to build the list; paid impact score to
   monetise. ARR compounds with every LGA the B2B side already onboards.
4. **Bundle C as B's upsell; hold D as vertical two.**

This keeps the existing B2B certifier business intact (it shares the same pipelines and LGA
expansion roadmap) while opening a consumer revenue line that is **larger in reach, recurring,
and defended by data nobody else has wired together.**

---

## 8. Guardrails (non-negotiable, per CLAUDE.md)

These offers touch liability-sensitive territory, so the framing must stay **factual and
deterministic**:

- **Never** say "illegal", "unapproved", "safe", "compliant", or "recommend". State observations:
  *"structure detected c.2021; no corresponding consent located on the public record — verify with
  council."* Never draw the legal conclusion for the user.
- **Never** predict approval outcomes or objection success.
- Every fact carries its **source + date**; flag uncertainty (detection confidence, data gaps)
  rather than smoothing it over.
- No hardcoded regulatory values — controls cited in the shadow/impact pack must come from the
  authoritative live source (`regulatory_provisions`, Planning Portal), consistent with the
  regulatory-data rule.
- Use generic public-facing product names; keep internal pipeline names (`threat_radar`,
  `pre_da_history`, etc.) out of any consumer-facing copy (IP-protection rule).

---

## 9. Sources

- PEXA Group — NSW property settlements FY24 (186,355): https://www.pexa-group.com/content-hub/property-insights-and-reports/pi-june-24/
- Unapproved works penalties / no statute of limitations / insurance void (NSW): https://pbl.legal/insights/unapproved-or-unauthorised-building-works-consequences-of-illegal-construction-in-nsw/ ; https://www.slconveyancing.com.au/post/what-happens-if-you-buy-a-property-with-unapproved-building-works-in-nsw ; https://duoinsurance.com.au/blog/unapproved-structures-in-australia/
- Pre-purchase report incumbents & pricing (Landchecker $24.90 premium; Before You Bid): https://landchecker.com.au/products/property-reports/ ; https://landchecker.com.au/pricing/subscriptions/
- Complying development notifies only after certification (objection-timing gap): https://www.es.au/do-my-neighbours-need-to-be-notified-of-a-complying-development/ ; https://www.planningportal.nsw.gov.au/development-and-assessment/planning-approval-pathways/complying-development/what-tell-your-neighbours
- Free raw-alert incumbents (PlanningAlerts, 544 councils): https://planningalerts.com.au/ ; https://landchecker.com.au/functionalities/permit-da-filtering-and-alerts/
- Overshadowing as valid objection ground / Jun 21 shadow diagrams: https://www.hunterlegal.com.au/summarising-development-applications-das/
- Granny-flat market (≈4,320 approvals/yr, 10× boom, 20–24% yield): https://hia.com.au/our-industry/housing/in-focus/2024/03/granny-flat-fever ; https://www.newcastleherald.com.au/story/9231001/nab-data-granny-flat-boom-expected-to-reshape-property-value/
- Climate risk to property value ($170B by 2050, 751k high-risk dwellings — Climate Valuation/XDI): https://climatevaluation.com/flood-risk-threatens-australian-property-value/ ; https://theconversation.com/new-climate-report-warns-property-prices-face-a-611-billion-hit-what-does-that-mean-265284
- NSW DA/CDC volume dashboards (ePlanning league table): https://planningportal.nsw.gov.au/eplanningreport
</content>
</invoke>
