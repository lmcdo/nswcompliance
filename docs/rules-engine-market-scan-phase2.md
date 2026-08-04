# Where Else Does a Provenance-Verified Rules Engine Win? — Phase 2 Deep Dives & Final Verdict

**Status:** Phase 2 COMPLETE. Companion to `rules-engine-market-scan-phase0-1.md`. **Date:** 2026-08-04. **Method:** two full adversarial deep dives (US state privacy laws; FSANZ food labelling) + one scoped mini-dive (NDIS obligations wedge), ~95 further searches/fetches. Evidence rules as before: links or [INFERENCE]/[UNVERIFIED] tags; absence claims state searches; several primary AU government/vendor pages returned 403 to the research proxy — flagged where it matters.

**Owner decisions taken (delegated):** top two confirmed as ranked in Phase 1 (US state privacy; FSANZ food labelling); NDIS mini-dive added.

---

## Executive summary — what Phase 2 changed

1. **FSANZ food labelling is DOWNGRADED: A− → B−/B.** Three Phase 1 pillars eroded under checking: (a) the archetypal date-flip — PEAL — is *finished* (transition ended 24 Feb 2024; stock-in-trade window closed 25 Feb 2026), so the urgency wave is behind us, not ahead; (b) FSANZ **abandoned P1058** (mandatory added-sugars NIP change) on 31 Mar 2026, thinning the pipeline of future 1.2.x flips, and the ~10 amendments/yr are dominated by additive/novel-food schedule permissions, *not* labelling obligations (plausibly 0–2 of the last ~10 touched Part 1.2); (c) the competitive vacuum closed in 2025–26: **AKA Label Studio** launched June 2026 — free, uncapped, FDA/EU/UK, off a US$17.2M seed, with a "live regulatory radar" — and **Food Label Maker** (US$49/mo) already markets FSANZ audit capability. FSANZ's own causal analysis also undercuts the recall-fear pitch: the 38%-allergen-recall stat is driven by packaging errors, cross-contamination and supplier spec drift — failure modes a rules engine cannot catch. What survives is a bounded consultant-leverage tool (~$300–800k ARR AU/NZ in good scenarios).

2. **US state privacy SURVIVES with three honest downgrades:** (a) the primary buyer population (fractional privacy officers) is small — est. 1,000–3,000 US practitioners [INFERENCE] — capping the base case at ~$250–300k ARR by month 24 (a strong solo business, not a venture market); (b) the 6–9-month revenue constraint is only met via an **amendments-only v0** (weeks of build), not the full corpus (~20–24 person-weeks for 20 states); (c) the free-artifact space is being colonized (PrivacyLawMap.com covers all 21 laws free), so the trust artifact must win on provenance depth, not existence. Everything else checked out: the empty category (c) is real and price-bracketed, cadence is sustained (2024: 7 new laws; 2025: 9 states amended; 2026 YTD: ≥4 + the CPPA ADMT regulation wave), the library-to-professionals UPL posture is clean with strong precedent, and enforcement keeps compounding.

3. **NDIS: DEFER-UNTIL, with a cheap validation option.** The 1 Oct 2026 SIL application deadline cannot be met by a product started now, and provider-facing SaaS already ships the naive obligations-register. But the corpus-stability kill question *flipped positive* (SIL rules are made and in force; determinate core stable ~9–12 months), and a bigger legislated wave lands July 2027 ($182.6M-funded expansion to personal care/daily living). Recommended: a 2-week consultant validation sprint, not a build.

---

## DEEP DIVE A — US state comprehensive privacy laws

### A1. Buyer map

- **Population:** IAPP ~80,000 members worldwide (2024, up from 50k in 2019); [INFERENCE] ~35–40k US-based as the outermost funnel. The **fractional/consulting privacy officer** category is real and dense — ten distinct firms surfaced in two searches (Red Clover Advisors, Privacy Ref, Newport Thomson, Bamboo Data Consulting, Privageo, Engage Compliance, Richt "CPO On Call", The DPO Group, Weil Consulting, Fractionus marketplace) — but small: est. **1,000–3,000 US practitioners** [INFERENCE; no market census exists — searched "fractional privacy officer market"].
- **Budgets (verified price points):** solo FPO: IAPP membership $295/yr, tooling $2–20k/yr, retainer income $3–15k/mo per client; small-firm counsel: Westlaw $105–400/mo, Practical Law ~$154/mo, bill-out $225–300/hr (specialists $400–800); SMB GC: Osano from $199/mo, SixFifty consultant tier $5,000/yr; enterprise: OneTrust median $11,835/yr with a **$10k contract floor from Q2 2026**; TrustArc Nymity bundled at $15k–250k+ — and TrustArc's own ROI pitch claims its research layer eliminates **"$20,000–50,000/yr in outside counsel research"**, direct evidence the currency budget line exists and is priced enterprise-only.
- **Steel-man:** many fractional DPOs run on IAPP membership + free law-firm trackers because their expertise *is* their product. Counter: their economics are leverage economics — one practitioner × 8–15 clients × 20 states is exactly who feels per-client currency-maintenance pain, and $100–300/mo is <20 minutes of billable time.

### A2. Offer design — LIBRARY, decisively

- **UPL line:** legal *information* (what the law says) is protected; legal *advice* (application to a person's facts) is regulated. A database queried by a professional who applies it to their client keeps the application step with the licensee (ABA Law Practice 2024 guidance; Westlaw/Practical Law/Nymity precedent — no UPL enforcement against professional-audience research tools found; searched).
- **The DoNotPay lesson (FTC final order Feb 2025, $193k):** the oracle posture fails on FTC *substantiation* before it fails on UPL — DoNotPay was punished for unproven "AI lawyer replaces lawyers" claims. A library never makes that claim; its claims (verified sourcing, currency) are literally provable from the provenance layer.
- **SixFifty precedent:** Wilson Sonsini's own subsidiary — 900 lawyers behind it, domiciled in permissive Utah — still retreats to library posture with UPL disclaimers. A solo AU non-lawyer should not take risk a firm like that declines.
- **v1 shape:** (i) per-state determinate facts, clause-cited + effective-dated (thresholds, rights catalogs, sensitive-data consent, notice contents, DPA triggers, cure periods + sunsets, opt-out signal dates, data-broker registration — verified live wedge: CA $6,000/yr, TX $300, OR $600, VT $100→$900 in 2027); (ii) **client-footprint amendment diffs** (old text → new text, effective date, which clients touched — e.g., CT SB 4 signed 2026-05-27, effective 2026-10-01); (iii) **one-click evidence export** — a memo appendix (clause text + citation + retrieval date + amendment history) the professional attaches to advice. That third feature is what monetizes provenance directly; no free tracker has it.

### A3. Corpus feasibility

| State | Documents | Effort |
|---|---|---|
| CA | Civ. Code §§1798.100–199.100 + CCPA Regs (66pp, 2023) **+ the ADMT/risk-assessment/cyber-audit package approved Sept 2025, effective Jan 2026, staggered to 2030** + Delete Act | **3–4 wks — the monster (~60–70% of 5-state effort)** |
| CO | CPA + substantive rules (4 CCR 904-3, ~50pp, amended 2025 for biometrics) | 1.5–2 wks |
| CT | ~15 sections, **most amendment-churned in the set** (2023, SB 1295 2025, SB 4 2026) — the diff-showcase state | 1–1.5 wks |
| TX | Ch. 541, statute-only (no rulemaking authority) | 1 wk |
| VA | 12 sections, no regs | 0.5 wk |

- **5-state determinate slice: ~10 person-weeks** with verification gates; full 20-state: **~20–24 person-weeks** (the 15 Virginia-model states are statute-only with high schema reuse). Cross-reference density is bounded: model the GLBA/HIPAA exemption block once, instantiate 15×; only CA requires external-statute pointer modelling.
- **Small-start verification:** "everything-but-California" is NOT viable (CA anchors every footprint). Two viable shapes: **(1) CA+CO deep, 18 states determinate-shallow; (2) — the recommended entry — an amendments-only v0**: baseline text capture + session monitoring + clause-level diff alerts mapped to client footprints. Weeks of build, directly attacks the 2025–26 amendment-wave pain, de-risks the full corpus, and is the only path meeting the 6–9-month revenue constraint.

### A4. Regulatory constraints

Selling to professionals substantially resolves UPL (research-tool precedent). Mitigations: professional-use terms with click-through; verbatim clause text always displayed beside structured fields (the field is an *index into* the law, not a restatement); no "you must/should" language — the founder's existing liability-language gate ports verbatim; E&O insurance; one-time US counsel review (~$2–5k); never claim the product replaces counsel or "detects violations" (FTC substantiation). No state licenses privacy-tool vendors; IAPP certification is voluntary (searched — no regime found).

### A5. Pricing

| Tier | Price | Anchor logic |
|---|---|---|
| Watchtower | **$79/mo / $790/yr** | Solo FPO/solo counsel; between IAPP ($295/yr) and Osano ($2,400/yr); < 20 min of billable time/mo |
| Practice | **$249/mo** (5 seats) | Boutique firms/FPO shops; = one counsel-hour/mo; adds evidence export + client workspaces |
| Embedded | **$700–1,200/mo** | API/CSV/white-label; deliberately under OneTrust's $10k floor, at the level TrustArc says research is worth |

Annual-prepay bias for cash flow; the free tier is the public trust artifact, not a crippled app; consultants get white-label rights at Practice+ (their client memos are the distribution).

### A6. GTM — first 10 buyers + trust artifact

First 10 by name-type: solo fractional CIPP/US with 6–12 SMB SaaS clients (IAPP Connect/LinkedIn); principals at 3–8-person privacy consultancies (the §A1 firm list *is* the prospect list); a 3-lawyer Texas privacy boutique (Paxton's $1.375B Google settlement made TX privacy defense a growth practice); privacy lead at a 200-person martech firm (owns OneTrust, still emails counsel); a regional-firm lawyer who "inherited" privacy; an auto/IoT compliance consultant (GM $12.75M is this quarter's outbound hook); a data-broker compliance manager (4 states, 4 agencies, 4 fee schedules); fractional-GC marketplaces (one deal, many seats); a consent-platform vendor (Embedded tier); an AU/UK firm advising US market entry (home-turf network).

**Trust artifact:** a public 20-state determinate matrix where **every cell is a claim backed by pinned verbatim clause text, citation, effective date** — with future-dated rows ("current until 2026-09-30 / from 2026-10-01"), a machine-verifiable amendment changelog with clause-level diffs, per-cell "last verified against source" timestamps, and CSV/JSON download. Existing free competition is real but shallow: IAPP's tracker is a 14-provision X-mark chart; law-firm trackers silently overwrite; **PrivacyLawMap.com** (free, all 21 laws, cure/GPC/thresholds, apparently an SEO play) is the nearest threat and the watch item. The honest pitch: *"Every tracker tells you what the law says. This one proves it, and shows you what it said last month."*

Channels (verified live): IAPP Privacy Advisor accepts contributed articles; podcasts — Serious Privacy, The Privacy Advisor Podcast, Data Diva, Shifting Privacy Left; Luiza's Newsletter (~98k subs); the LinkedIn privacy community (where fractional DPOs market themselves — findable *and* reachable). Async channels suit the AU timezone; IAPP Global Privacy Summit is a year-2 accelerant, not a launch dependency.

### A7. Competition counterfactual — why the provenance seat is empty

- **OneTrust/DataGuidance:** lawyer-network prose + alerts inside a platform whose floor just rose to $10k; clause-level structured data would cannibalize the analyst network and be invisible in enterprise dashboard demos. Killing the entry tier shows their strategy is up-market consolidation — the opposite direction.
- **TrustArc/Nymity:** monetizes research as suite lock-in ("8 hours per law → 10 minutes"); unbundling would undercut suite deals.
- **IAPP:** the tracker is a membership-marketing asset; a paid SaaS would compete with its own members.
- **Westlaw/Lexis/Bloomberg:** scale on lawyer-authored prose, and chose *generative* AI over deterministic provenance — Stanford RegLab (peer-reviewed, JELS 2025) measured 17% hallucination in Lexis+ AI and 33% in Westlaw AIAR. Their innovation budget is on the opposite architecture.
- **Law-firm trackers:** business development for $500/hr work — structurally capped at shallow.
- **New-entrant scan:** PrivacyLawMap (watch); MARK37/Secure Privacy/Consenteo/Truame are consent-product content marketing. **No one found selling clause-cited, effective-dated determinate data with amendment diffs as the product** (searched: "privacy law tracker SaaS startup 2025 2026", "state privacy law API", "clause-level compliance research tool").
- **Steel-man:** the empty niche may mean thin paying demand — everyone gets currency free, bundled, or bills it through. TrustArc's $20–50k replacement claim and free trackers going observably stale between annual refreshes argue otherwise, but this is precisely what the first 10 sales test.

### A8. Revenue scenarios (USD, MRR)

| Scenario | Odds | M6 | M12 | M24 |
|---|---|---|---|---|
| Pessimistic — "trackers are good enough" | ~35% | $450 | $1.3k | $2.7k → **kill zone** |
| Base — fractional niche buys, firms trickle | ~45% | $1.4k | $6.3k | **~$22k (~$260k ARR)** — solo-viable |
| Optimistic — category artifact + enforcement wave | ~20% | $3k | $16k | ~$50k (~$600k ARR) |

Only base/optimistic produce meaningful month-9 revenue, and only with the amendments-first entry. This domain pays back on a 12–24-month curve.

### A9. Red team (failure modes → early warning → kill criterion)

1. **Cadence collapses:** 2024 = 7 new + 3 amending; 2025 = 0 new + 9 amending; 2026 YTD ≥4 + CPPA reg wave — sustained, but **seasonal (Apr–Jun)**. Kill: two consecutive sessions with <3 material amendments AND diff-alert engagement <30%.
2. **Incumbent ships provenance:** most likely PrivacyLawMap monetizing or IAPP paid tool; 2–3 quarters if chosen. Tell: DataGuidance shifting to "source-linked/audit-ready" language; IAPP adding effective-date columns/API. Kill: incumbent ships clause-pinned diffs at sub-$3k/yr → sell the corpus/tech rather than compete.
3. **No small start:** buyer footprints are national. Mitigation: 20-state determinate-shallow early. Kill: pilots demand full 20-state deep + health/biometric/children's strata before paying (>~25 person-weeks pre-revenue).
4. **Federal preemption:** APRA died Jan 2025, not reintroduced as of Mar 2026; new drafts face "an uphill battle." Kill: passage through one chamber → re-scope to surviving strata; the engine ports, the corpus is sunk cost.
5. **CPRA convergence:** current evidence shows *increasing* spread (MD data-minimization, CA ADMT, CT serial divergence, DE narrowing exemptions).
6. **Trust wall (AU non-lawyer vendor):** mitigate with a named US privacy lawyer as paid reviewer on the masthead + SOC2-lite. Kill: consultants cite vendor trust in >50% of losses by M9.
7. **Free-rider on the artifact:** paid layer is dynamic (diffs, footprint mapping, evidence export, API); artifact is static-snapshot. Kill: <0.3% conversion after gating experiments → paying demand is illusory.
8. **AI legal research:** an LLM can research; **it can't be a changelog**. Current benchmarks favor the moat (17–33% hallucination in incumbent AI tools). Kill: independent <2% hallucination on statutory-currency questions at <$200/mo → Plan B: sell the corpus as grounding data via API.
9. **Solo maintenance SLA trap:** one silently-missed amendment destroys the promise retroactively. Mitigate: the automated monitoring + verification gates, an honest published SLA, a public miss-register. Kill: maintenance >40% of founder time steady-state.

---

## DEEP DIVE B — FSANZ food labelling (downgraded)

### B0. The three reversals (headline)

1. **PEAL is over.** Transition ended 24 Feb 2024; stock-in-trade closed 25 Feb 2026 (NSW Food Authority; Allergen Bureau). No date-driven forcing function currently exists in the labelling slice.
2. **The pipeline thinned.** FSANZ abandoned P1058 (added-sugars NIP) 31 Mar 2026. Cadence verification: amendments 235→241 = 7 instruments in ~6 months (~10–14/yr holds) **but** content is dominated by application-driven permissions (additives, processing aids, novel/GM foods — Schedules 3/15/18/25/26). Plausibly **0–2 of the last ~10 amendments touched Part 1.2** [full tally blocked by 403s on FSANZ pages]. The last transformative labelling flips: PEAL (2021→2026) and pregnancy warnings (2020→2023).
3. **The vacuum closed.** AKA Label Studio (free, uncapped, US$17.2M seed, "live regulatory radar", FDA/EU/UK — launched June 2026; ANZ an obvious roadmap line). Food Label Maker (US$49/mo) ships FSANZ NIP generation and markets FSANZ audit. Truli (pay-per-scan AI review, claims FSANZ). GoVisually adding AI label checks. None do provenance-verified determinism or amendment-to-SKU monitoring — a real moat — but "free" now sets the buyer's reference price.

Also: FSANZ attributes allergen recalls to "packaging errors, accidental cross contamination and failure to communicate ingredient changes" — process failures a rules engine cannot catch. The recall-fear pitch is contradicted by the regulator's own causal analysis.

### B1–B5 condensed findings

- **Buyers:** realistic ICP is 2,000–5,000 AU manufacturers with packaged SKUs + named QA function [INFERENCE from AFGC's 14,000-business count minus the micro/bakery tail]; ~100–300 active label consultants (AIFST state registers are both census and prospect list; named: Quality Associates, Correct Food Systems, Tastebuddies, TMT, Regulatory Matters, MSAC, Complete Food Consultants, FoodLegal, Ashbury AU). Per-SKU review ≈ **$300–800** [INFERENCE: 2–5 hrs at the verified $90–150/hr]. NZ is a genuine free expansion (same Code; MPI fined importers $28,000 for undeclared soy; 57 recalls 2025, 45.6% allergen).
- **Offer:** LIBRARY. No licensing monopoly exists (anyone may review labels — verified: AIFST registers are voluntary; states license food businesses and auditors, not label reviewers), so the binding constraint is liability, not licensing: negligent misstatement (assumption of responsibility; disclaimers scrutinised) plus **ACL s18** (misleading conduct — cannot be contracted out of; "ensures compliance" marketing is itself exposure). Worst case — allergen death behind a "passed" label — is existential for a solo founder regardless of merits. v1: consultant-facing Label Audit Workbench with a load-bearing three-state output (pass / fail / **needs-judgment** — routing claims and characterising-ingredient questions to the human) + Amendment-to-SKU Radar.
- **Corpus:** the Code is ~80 standards + 29 schedules, each a separate Federal Register instrument — the founder's exact document class; the port premise holds. Labelling slice: Std 1.1.1/1.1.2 + 1.2.1–1.2.11 + Schedules 9/10/11/12/13 (+1, 4, 5, 7, 8), est. 250–450pp [±50%]. Allergen chain verified at the joints (1.2.3 → Sch 9 → 1.1.2 defs → 1.2.1 applicability) — bounded, easier than LEP/DCP spatial cross-referencing. **Starter slice (allergen+NIP+mandatory statements): 3–5 person-weeks; full labelling corpus: 8–12.** Country of Origin is separate ACL law (ACCC-enforced) — v1.5. **PEAL-only is no longer sellable** (deadline passed; free guides abundant).
- **Pricing:** consultant seat A$350–500/mo (pays for itself at ~3 hrs saved; turns a $500 manual review into a 1-hour review-and-sign — the sale is margin expansion); manufacturer portfolio A$500–900/mo by SKU count; per-report A$150–250. AU ceiling stated honestly: ~$1–3M captureable ARR long-run.
- **GTM:** first 10 = sole-trader consultant (Tastebuddies archetype); small food-safety consultancy bundling label work; the consultant already hand-writing Code-update content (MSAC — sell them the radar they're writing manually); QA manager at a 30–80-person condiment maker; contract packer technical manager (pure verification demand); claims-heavy health-food NPD lead; independent own-brand coordinator; NZ consultancy; food-law boutique's technical team; RTO trainer. Trust artifact: **public clause-cited Amendment Radar** (per-amendment: instruments touched, whether any 1.2.x obligation changed, effective + stock-in-trade dates, who's affected) — verified gap (FSANZ circulars are authoritative but unmapped to impact; FoodLegal InHouse is paywalled) — but §B6(a) means most entries will read "no labelling impact": trust-building, weak lead-gen.

### B6. Red team (the ones that bite)

1. **Cadence is real but labelling-irrelevant — CONFIRMED weakness.** Kill: <2 portfolio-relevant labelling changes in 12 months AND churn citing silent alerts. Partial rescue: widen the radar to composition schedules (7/8/15/18) which do hit ingredient statements.
2. **Incumbent provenance:** FoodWorks (holds recipes + trust; observed release tempo slow, but the work is months not years); Food Label Maker already claims FSANZ audit; AKA announcing ANZ is the tell. Kill: clause-cited FSANZ verification shipped at ≤your price before ~20 paying accounts.
3. **Small start: refuted on corpus, CONFIRMED on timing** — the slice exists (3–5 wks) but no buyer can name the event that makes them buy this quarter. Kill: 3 months of outreach without that event named.
4. **The determinate slice is the cheap slice:** the tool may compress the $150 part of a $600 review; consultants keep the judgment bottleneck. Kill: pilot time-saving <25% of review time.
5. **SME WTP above the free floor:** government gives away label guidance (QLD Label Buster, NSW Food Labelling Assistant); AKA is free; no evidence found of SME food-manufacturer SaaS spend at A$500+/mo except mandated systems. Kill: <2 of 20 manufacturer trials convert → consultant-only.
6. **Garbage-in determinism:** the tool verifies label-vs-rules, never label-vs-actual-recipe — and allergen injury sits at the end of that chain. Design constraint: scope reports as "label vs supplied spec", gap explicit.
7. **AU TAM ceiling + export economics:** expansion targets (FDA 21 CFR 101, UK FIC) are where the funded competitors already live; the AU advantage does not travel. Kill: if the plan ever requires beating funded US competitors on FDA turf, stop.

**B verdict:** the mechanism ports cleanly (same document class, bounded cross-references, 3–5-week starter corpus, no licensing barrier, genuinely unserved provenance artifact) — but the domain enters Phase 3 as a **bounded consultant-leverage play (~$300–800k ARR ceiling in good scenarios) with no current forcing function**, evaluable within ~4 months of a pilot. Revised grade **B−/B**.

---

## MINI-DIVE — NDIS obligations wedge: DEFER-UNTIL

- **Forcing function:** SIL mandatory registration commenced 1 Jul 2026 (new group 0138 + SIL Practice Standards module); applications due **1 Oct 2026** — ~8 weeks out, unreachable for a new build. Scramble is real (auditor capacity "severely constrained"; QIP and Citation Certification exited the auditor market; thousands of SIL providers competing for audits). Unregistered SIL is now criminal (2 yrs/120 units); Integrity & Safeguarding Act 2026 (assent 8 Apr 2026) adds civil penalties to $3.64M. **The next wave is bigger:** the Securing the NDIS Bill 2026 expands mandatory registration from **July 2027** to personal care/daily living/closed settings ($182.6M funded, full rollout to 2030) — a rolling 4-year series of forcing functions.
- **Channel:** fees hold ($2,500–$7,000 engagements; all-in to $15k); consultant headcount unknown (est. low hundreds of boutiques). **Kill-adjacent finding:** provider-facing SaaS already ships the naive wedge — Smart Compliance Systems markets "obligation register live in minutes"; FormaOS, ClinicComply, Checkbase, Centro Assist adjacent. Not found anywhere: clause-level provenance + effective dates + amendment monitoring — that differentiation is open, but consultant WTP for determination-only output is unvalidated.
- **Corpus stability — flipped positive since Phase 1:** the SIL rules landed and are in force; the determinate core (registration groups, certification-vs-verification pathways, notification timeframes, worker screening, audit types, effective dates) is stable ~9–12 months with quarterly deltas. The mid-2027 re-cut is the *product's selling point* for an amendment-monitoring engine, not its failure mode.
- **Revenue math:** v1 (white-labelled clause-cited "Provider Obligations Profile", $199–299/mo seat or $99–149/report, 8–12 weeks build → live ~Nov 2026): M6 base ~$3–4k MRR (audit-prep tail keeps demand alive past 1 Oct); M12 base ~$8–12k MRR riding the 2027 wave. Meaningful MRR arrives months 9–12 — the outer edge of the founder's window.
- **Verdict: DEFER-UNTIL (a) the graduated-registration Rules for the July 2027 expansion are published AND (b) 3+ consultants pre-commit at ~$200/mo.** Run a **2-week validation sprint now** (mocked clause-cited profile shown to 5–10 registration consultants) — not a build. If 3+ pre-commit, promote to GO targeting the 2027 wave.

---

## What Phase 2 changed vs Phase 1 — the honest ledger

| Phase 1 claim | Phase 2 finding |
|---|---|
| FSANZ A−: PEAL as the archetypal live date-flip | PEAL fully expired Feb 2026 — the archetype is a *past* event |
| FSANZ: ~10 amendments/yr = currency pain | Cadence confirmed, but content is mostly additive/novel-food permissions; labelling standards nearly static; next big flip abandoned |
| FSANZ: verification vacuum | Closed 2025–26: free AKA ($17.2M seed), $49/mo FLM with FSANZ, AI checkers. Provenance determinism remains unique but "free" resets price expectations |
| Privacy A−: empty category (c) | **Confirmed** with verified price brackets; PrivacyLawMap is the free-layer watch item |
| Privacy: cadence structural | **Confirmed** (7 new/2024; 9 amended/2025; ≥4 + CPPA wave 2026 YTD); seasonal Apr–Jun |
| Privacy: 6–9-month revenue path "clearest" | True only via amendments-only v0; full-corpus-first breaches the constraint |
| NDIS: rulebook mid-rewrite (hostile) | Flipped: SIL rules in force, core stable ~9–12 months; the blocker is now channel WTP + the missed 1 Oct spike |

---

## The 5 questions only buyer conversations can answer

1. **Privacy WTP:** How many hours per month does a fractional DPO or SMB-serving privacy lawyer actually spend re-verifying state-law currency across their client footprint — and would clause-pinned amendment diffs plus an evidence export reduce it enough to pay $79–249/mo, given free trackers exist? (Tests the §A7 steel-man that free suppresses all paying demand.)
2. **Privacy trust threshold:** What is the minimum credibility asset that lets a US professional rely on a solo AU non-lawyer vendor's data — a named US privacy lawyer as reviewer, SOC2, a public miss-register, an insurance certificate — and does any combination work at all for law-firm buyers (vs consultants)?
3. **Privacy scope floor:** Is the amendments-only v0 independently purchasable, or do buyers require the full 20-state determinate reference from day one? (Directly tests red-team item A9.3 — the kill criterion on pre-revenue corpus scope.)
4. **Food consultant economics:** What fraction of a $300–800 per-SKU label review is the mechanically-checkable slice, and would a consultant pay A$350–500/mo for a tool that compresses it — or does the billing model (hours) make time-saving a *disincentive*? (Tests red-team item B6.4, the domain's live-or-die question.)
5. **NDIS pre-commitment:** Will 3+ registration consultants pre-commit ~$200/mo for a white-labelled, clause-cited obligations profile aimed at the July 2027 expansion wave, sight of a mock-up unseen product? (The DEFER-UNTIL gate.)

---

## VERDICT — the next 90 days

**US state privacy laws gets the 90 days — entered amendments-first, validated conversation-first.** Weeks 1–2: 15–20 buyer conversations with fractional DPOs and small-firm privacy counsel (questions 1–3 above) while building the baseline text capture for the current 20 statutes; weeks 3–8: ship the public trust artifact (clause-pinned matrix + amendment ledger) and the amendments-only v0 at $79/mo; weeks 9–13: convert conversations to the first 5–10 paying subscribers and start CA+CO deep extraction only if the scope-floor answer permits. In parallel, run the 2-week NDIS validation sprint (AU-daytime work that complements US-async outreach) as the hedge. **Odds of first paying revenue inside 9 months: ~60%** (the deep dive's base+optimistic cases sum to ~65% for *meaningful* M9 revenue; first-dollar is an easier bar, discounted for the cold-start trust wall). **What flips this verdict:** (a) ≥10 buyer conversations converging on "free trackers suffice" or demanding the full deep corpus before any payment — flip to the NDIS wedge if its sprint pre-commits, else to AU court practice directions as the bounded fallback; (b) an incumbent (PrivacyLawMap, IAPP, DataGuidance) shipping clause-pinned, effective-dated diffs under $3k/yr before launch — same fallback; (c) FSANZ re-entering only if a major Part 1.2 reform (added-sugars revival, front-of-pack) re-enters the FSANZ work programme with a dated transition window, which would restore the forcing function this domain currently lacks. The food labelling engine-fit is real and the corpus is the cheapest to build — it stays on the shelf as the fast follow-on, not the lead.

---

## Honesty ledger — Phase 2 additions

- FSANZ compilation page counts (403 on PDFs — labelling-slice estimate ±50%); full per-amendment 1.2.x tally for amendments 235–249 incomplete (verified subset only).
- FoodWorks/Xyris exact AUD pricing (403; category norm US$500–1,500/user/yr via a competitor's PR). FoodLegal InHouse subscription terms unfetchable.
- Fractional privacy officer population (1,000–3,000) is [INFERENCE] — no census exists; the §A1 firm list is the evidence base.
- PrivacyLawMap ownership/funding unverified (site blocked direct fetch). Ashbury revenue/headcount figures from ZoomInfo, treated as unverified.
- No official count of SIL providers affected by the 1 Oct 2026 deadline (Commission publishes none; "thousands" inferred from auditor-demand commentary).
- AU/US legal positions on negligent misstatement for software checkers and Parsons/Quicken UPL history applied from doctrine, not re-verified case law this session.
- All revenue scenarios are [INFERENCE] — no comparable-product benchmarks exist in either niche.
