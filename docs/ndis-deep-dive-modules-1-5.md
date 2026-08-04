# NDIS Deep Dive — Modules 1–5 Checkpoint

**Status:** Modules 1–5 COMPLETE. **Stopped for owner review before Modules 6–11** (product scope, GTM, corpus feasibility in person-weeks, competition, expansion logic, red team, verdict).

**Companion to** `rules-engine-market-scan-phase0-1.md` and `rules-engine-market-scan-phase2.md`. The Phase 2 mini-dive verdict on NDIS was **DEFER-UNTIL**; this deep dive is the "2-week validation sprint" scaled up to a research pass, and it flips the picture in three material ways (below).

**Date:** 2026-08-04. **Method:** four parallel research passes (~200 further searches/fetches); every claim linked or tagged `[INFERENCE]`/`[UNVERIFIED]`/`[UNVERIFIED-PRIMARY]`. All primary AU government hosts (`legislation.gov.au`, `ndiscommission.gov.au`, `ndis.gov.au`, `health.gov.au`, `aph.gov.au`, `oia.pmc.gov.au`) returned 403 to the research proxy — F-numbers and commencement dates verified via search index and mirrored via secondary sources (Team DSC, ClinicComply, MinterEllison, Gilbert+Tobin, Mondaq, APO, AustLII, NDS, IBISWorld). Founder to re-fetch primaries before locking any corpus.

---

## Executive summary — what changed since the Phase 2 mini-dive

The Phase 2 verdict rested on three concerns: (a) the SIL forcing function couldn't be reached in time, (b) consultants might not pay for a determination-only tool, (c) the rulebook was "mid-rewrite." All three now read differently:

1. **The July 2027 wave is bigger, funded, and structurally forced — and it hits a channel already under acute capacity stress.** The OIA impact analysis assigns **~$77.4M/yr in additional regulatory cost** to the expansion; two of the ~17 Approved Quality Auditors (**QIP** and **Citation Certification**) exited the market in April and June 2026; certification wait times have stretched from 6–9 months to **9–12 months**; and the sector is entering the wave in severe financial distress (**~50% of providers in operating deficit; 81% say NDIS pricing is unsustainable; 200% jump in healthcare/social insolvencies since 2023**). Named failures — Centacare SEQ, Annecto, PlayAbility — closed in 2025.

2. **The corpus is smaller and more tractable than expected — but with one strategic constraint that changes the product shape.** The green-zone verbatim corpus is **~10 Federal Register instruments** on a **CC-BY 4.0** licence — small, well-scoped, single-founder-feasible. But the **NDIS Pricing Schedule 2026-27 (99pp) and all NDIA operational guidelines are CC-BY-NC 3.0** — commercial republish of clause-verbatim text is prohibited. Pricing must be handled as a paraphrase-plus-link tier, not embedded. Practice Standards 2.0 beyond SIL has **no published rollout schedule**; graduated-registration Rules for July 2027 are **NOT YET MADE**. Building against them today is speculation.

3. **The demand shape is barbelled — very determinate high-value perpetual jobs and a NEW post-Integrity Act board-segment SKU no incumbent occupies — but a real competitor surfaced.** The **ACIA Quality Portal** already ships policy templates + self-assessments for NDIS Practice Standards claiming "up to 80% time saving on compliance reporting" — the closest thing to the founder's scoped product found anywhere. Positioning must explicitly out-perform ACIA on clause depth, effective-dating, and amendment monitoring, or fold to an OEM play.

**Working verdict at checkpoint:** the domain has become more attractive than the Phase 2 mini-dive suggested, but it needs the founder to (a) choose the product shape between three coherent options (§6 in the next phase), (b) accept a small AU-only TAM ceiling of roughly $2–5M ARR from perpetual layer capture, and (c) make an explicit call on ACIA — compete, partner, or route around. **All three questions should be answered by the validation sprint, not by more desk research.**

---

## MODULE 1 — Regulatory architecture and dated map

### Corpus manifest (machine-buildable)

| Tier | Content | Licence | Handling |
|---|---|---|---|
| **A — verbatim clause + citation** | NDIS Act 2013 (`C2013A00020`); Code of Conduct Rules (`F2018L00629`); Provider Registration & Practice Standards Rules (`F2018L00631` — contains the Practice Standards modules as schedules); Restrictive Practices & Behaviour Support Rules (`F2018L00632`); Incident Management & Reportable Incidents Rules (`F2018L00633`); Complaints Management & Resolution Rules (`F2018L00634`); Quality Indicators Guidelines (`F2018N00041`); Approved Quality Auditors Rules 2025 (`F2025L01383`); Worker Screening Rules; Procedural Fairness Guidelines (F-nums to verify); NDIS Supports Transitional Rules 2024 (`F2024L01257` — mark SUNSET-PENDING) | **CC-BY 4.0** (Federal Register) | Extract, verbatim, effective-dated |
| **B — paraphrase + link** | NDIS Pricing Schedule 2026-27 (99pp, released 22 Jun 2026, effective 1 Jul 2026); Annual Pricing Review 2026; NDIS Support Catalogue (not yet released for 2026-27); all NDIA operational guidelines; Regulated Restrictive Practices Guide (Commission, but CC-BY-NC Int'l) | **CC-BY-NC 3.0** — **cannot republish verbatim** | Ingest for internal reasoning; surface via link + paraphrase |
| **C — persuasive background** | Practice Standards booklet Nov 2021 v4 (~45pp); Provider/Worker Code of Conduct Guidance; Feb 2026 Position Statements batch; Sep 2024 Detailed Guidance (Incident Management, Complaints) | CC-BY 4.0 AU (Commission website default) | Ingest as background, cite as persuasive |
| **DEFER — do not include** | Securing the NDIS for Future Generations Bill 2026 (r7487); graduated-registration Rules for Jul 2027 wave; Practice Standards 2.0 wider review outputs; commissioned support coordination model (Jul 2028); 90-day claiming rule; Thriving Kids access pathway | draft/emerging | Watch, do not build against |

### Amendment velocity — last 24 months (Aug 2024 → Aug 2026)

Velocity is **elevated but concentrated**:

- **NDIS Act 2013**: 3 amending Acts in window (No. 104/2024 at commencement edge; No. 45/2025; No. 41/2026 — the Integrity & Safeguarding Act, Royal Assent 8 April 2026)
- **Provider Registration & Practice Standards Rules `F2018L00631`**: 1 major amendment (Mandatory Registration & Other Matters, commenced 1 Jul 2026) — this is the churn driver
- **Complaints Rules `F2018L00634`**: 1 (Dealing with Complaints Amendment 2025)
- **Code of Conduct `F2018L00629`**: 0 (last amended Dec 2023 — 8 elements locked in)
- **Incident Management Rules `F2018L00633`**: 0
- **Restrictive Practices & Behaviour Support Rules `F2018L00632`**: 0 identified since 2020 compilation
- **Worker Screening Rules**: 0 identified in 24 months
- **Quality Indicators Guidelines `F2018N00041`**: 1 (SIL amendment 1 Jul 2026)
- **Approved Quality Auditors framework**: NEW Rules 2025 replacing 2018 Guidelines architecture
- **Pricing Schedule**: annual + quarterly patches (perpetual — but LICENCE-BLOCKED for verbatim republish anyway)

Verdict: two instruments and one Guidelines being rewritten; **four (Code, Incident, RRP-BS, Worker Screening) are structurally quiet for 24+ months** — the stable spine on which to build first.

### Stability rating per instrument

- **STABLE (build-now)**: Code of Conduct; Incident Management Rules; Restrictive Practices & Behaviour Support Rules; Worker Screening Rules; Procedural Fairness Guidelines; Act baseline
- **AMENDING (build-with-versioning)**: Complaints Rules; Quality Indicators
- **REWRITING (build-but-expect-churn)**: Provider Registration & Practice Standards Rules — the biggest single obligations surface, must have effective-date engine before shipping
- **DO NOT INCLUDE VERBATIM**: all NDIA pricing/operational (NC licence)
- **DEFER**: everything under Securing Bill

### Dated timeline (Jan 2024 → Dec 2030) — critical milestones

| Date | Event |
|---|---|
| 3 Oct 2024 | Getting the NDIS Back on Track No. 1 Act commences (s.10 supports lists) |
| 2 Oct 2025 | NDIS Supports grace period ENDS |
| 1 Nov 2025 | Aged Care Act 2024 + Rules 2025 commence (65+ boundary) |
| 26 Nov 2025 | Integrity & Safeguarding Bill introduced |
| 8 Apr 2026 | Integrity & Safeguarding Act Royal Assent (Act 41/2026) |
| 9 Apr / 6 May 2026 | Integrity Act schedules commence (civil penalties to $3.3M–$16.5M corp; whistleblower; banning powers) |
| 14 May 2026 | Securing the NDIS for Future Generations Bill INTRODUCED (r7487) |
| 22 Jun 2026 | Annual Pricing Review 2026 + Pricing Schedule 2026-27 released |
| 1 Jul 2026 | **SIL WAVE**: Mandatory Registration Rules commence; SIL Practice Standards module commences; digital platform providers must register; new SIL Quality Indicators commence; new Pricing Schedule takes effect |
| **14 Aug 2026** | **Securing Bill Senate Committee FINAL REPORT DUE (10 days from this report's date)** |
| 1 Oct 2026 | **SIL DEADLINE**: unregistered SIL providers who did not apply must stop delivering |
| 1 Oct 2026 | Thriving Kids replaces NDIS pathway for many children ≤8 [UNVERIFIED-PRIMARY] |
| 1 Dec 2026 | 90-day claiming rule commences [UNVERIFIED-PRIMARY] |
| 1 Jul 2027 | Mandatory registration expansion (personal care / daily living / closed settings) — **Rules NOT YET MADE** |
| 1 Jul 2028 | Commissioned model for support coordination [UNVERIFIED-PRIMARY] |
| Dec 2030 | Full graduated registration model rollout target |

**RECHECK items** (must resolve before commit to build):
- Securing Bill status as at 4 Aug 2026: **NOT ENACTED** — Senate inquiry active; final Committee report due **14 Aug 2026** (10 days). Government–Greens agreement on amendments exists but Bill has not returned to a chamber vote.
- Practice Standards 2.0 rollout beyond SIL: **NOT SCHEDULED** (consultation only)
- Graduated registration Rules: **NOT YET MADE** — category definitions and sequencing "through 2026 and 2027" per Roadmap. Anyone selling a "July 2027 personal care compliance product" today is selling vapour.

---

## MODULE 2 — Market structure and sizing

### Baseline (verified)

- **Q1 2025-26 (30 Sep 2025): 17,374 active REGISTERED providers / 257,318 active UNREGISTERED**
- IBISWorld: 22,495 enterprises (2024); market $44.7B (2025); 5-yr revenue CAGR 9.3%
- No single company holds >5% market share (industry structure highly fragmented)

### By registration group (mostly missing)

**No publicly published headline table** maps the 16k+ registered providers to the 38 registration groups. Data available:

- Plan management: **2,871 registered providers** (CompareSupports)
- SDA: 15,099 participants using SDA; $411M annualised payments 2025 (+34% p.a. over 2 yrs); [industry knowledge] <300 registered SDA providers
- Behaviour support: +6% quarterly increase in "suitable" practitioners
- New SIL registration group **0138** takes effect 1 Jul 2026
- **SIL applications received to date**: not published

**Gap** — dataresearch.ndis.gov.au CSVs would resolve this; blocked by 403 in this session.

### July 2027 expansion cohort — the wave that matters

- OIA Supplementary Analysis 2026: proposal adds **~$77.4M/yr in average regulatory costs**
- Full mandatory registration rollout by December 2030
- [INFERENCE range] personal care + daily living = >40% of Core Supports payment volume, translating to **~40–70k active ABNs currently delivering these supports unregistered**; of which perhaps **10–20k are businesses** (>1 worker) — the immediate policy target
- Closed settings: low thousands, overlapping heavily with SIL

### Provider financial health — this changes the pricing math

NDS *State of the Disability Sector Report 2025* (survey of ~500 provider organisations):

- ~50% of providers in operating deficit 2024-25; 55% in prior year
- 81% cannot deliver at current prices
- 85% report conditions worsened YoY
- 77% delivered unfunded services averaging ~$500k per provider
- Only 28% confident about 12-month sustainability
- >60% cite rising admin/compliance costs as top pressure

RSM 2025 data: **200% increase in Healthcare & Social Assistance insolvencies since 2023**. Named 2025 exits: Centacare SEQ (~700 participants, 600 staff), Annecto (4,400 clients / 4 states), PlayAbility (Bega Valley).

**Implication**: buyers face compressed margins and are the "buy a $2–4k/yr subscription only if it visibly shifts hours" segment. Consultant fees at $2.5–10k per engagement are already resistance-tested; below that is the room to compete.

### Consultant census

- No dedicated NDIS-consultant association or trade body exists (verified via search)
- Named firms with scale (extending Phase 2's list): Provider+ (8,200+ providers, 6,800+ successful applications; proprietary PQMPro doc platform), Provider360 (3,000+; rebranded from Centric 2024), Avaana (3,000+; ex-lawyers; "up to 60% cheaper"), EnableUs (3,000+ claimed), HCPA (10,500+ clients, 99% first-time approval), Engels Floyd, Tania Gomez, Health Care Consulting Australia, HealthQ, Sky Staff (Melbourne/Sydney/Brisbane + offshore staffing), DHD Consultancy (freemium acquisition), LMS Compliance Services, Regis Provider Consulting, NDIS Consultants, NDISregistration.com, CentroQMS/Centro ASSIST, Quality & Safety Consulting, ISO Professionals, Better Care Delivered, Lama Care, MD Home Care, Provider Partners, Vertex360, VCCG, Effective Policy
- [INFERENCE] ~30–60 established firms with real websites and >1 consultant; ~200–400 additional solo/micro-firms Australia-wide

### AQA capacity — a supply shock during a demand wave

- **QIP** ceased NDIS auditing 30 Apr 2026 after strategic review
- **Citation Certification** ceased new NDIS audits 31 May 2026; all activity concluded 30 Jun 2026
- Active AQAs now: BSI Group ANZ, DNV, Global-Mark, SAI Global, HDAA, Platinum Certification, Quantum Certification Services, Certifii, Auditwise Group, Australian Quality Certification, Global Compliance Certification (GCC), IHCA Certification, Certification Partner Global (CPG), Sustainable Certification
- **~13–15 active AQAs as of Aug 2026 (down from ~17 pre-2026)** [RECHECK live Commission page]
- Certification registration now takes **9–12 months** from standing start (up from 6–9 pre-2026)
- FlowLogic (Aug 2026): "wait times stretching and will get worse through H2 2026"

**Would auditors buy the tool?** Not directly — they bill fixed-fee per audit, so reducing hours per audit hurts revenue. Better framing: **pre-work product providers use before booking their audit** — auditors will recommend it because it lowers their NCR-remediation friction and raises pass rates.

### Peak bodies

- **NDS** (1,000+ members, employ 100k, support 500k people): distribute-friendly at member-benefits level; has commercial partnerships (Ability Roundtable) so expect revenue-share ask
- **DIA** (Disability Intermediaries Australia, founded 2018; members deliver services to **2/3 of NDIS participants**): **highly aligned distribution partner** for the 2027 expansion — intermediaries are the cohort under mandatory registration for support coordination
- **ACIA** — **CRITICAL: direct competitor.** ACIA Quality Portal ships policy templates + self-assessments for NDIS Practice Standards + SIRS + NSQHS + Aged Care Standards; claims "up to 80% time saving on compliance reporting"
- **ILC** (Information, Linkages & Capacity Building): **$364.5M over 5 years from 2024-25** — potential grant pathway if positioned as capability-building infrastructure

### Geographic & size

- Ranking: NSW > QLD > VIC > SA > WA > ACT > TAS > NT
- [INFERENCE from historical splits] NSW ~30–33%, VIC ~24–27%, QLD ~20–22%, WA ~8–10%, SA ~7–9%, others ~5% combined
- [INFERENCE] size distribution: sole trader/<5 staff 55–65% of registered by count, 5–10% of revenue; small (5–19) 20–25% count, 15–20% revenue; medium (20–100) 10–15% count, 25–30% revenue; large (100+) 3–5% count, 40–50% revenue
- Ability Roundtable's 90+ orgs represent ~20% of registered-provider payments — the "large" segment already runs internal quality teams and buys enterprise compliance software (Riskonnect, GoodHuman enterprise)

---

## MODULE 3 — Demand nature (jobs decomposed)

The single most important input to go/no-go: **what share of each compliance job is rule-lookup (the engine's territory) versus drafting/hand-holding (the consultant's moat)?**

### Job-by-job rule-lookup share

| Job | Frequency | Price today | Rule-lookup share | Wedge quality |
|---|---|---|---|---|
| Initial registration application | one-off | $2–3.5k guidance / $4–7k full-service | 30–35% | Wave |
| Verification audit (low-risk) | 3-yr | $900–1,800 headline; $3.5–6k all-in for small | 40% | Wave, cycle |
| Certification audit (SIL/higher-risk) | 3-yr | $2.8–12k; $7–15k larger | 30% | Wave |
| Mid-term surveillance audit | ~18 mo | $1.5–5k; +$6k on top of $12k cycle | 25% | Perpetual |
| Renewal / re-audit | 3-yr | ~70% of first-cycle | 40–60% (rises if standards changed) | Perpetual |
| **Scope changes (add reg groups)** | ad hoc | out-of-cycle audit unless bundled | **60% — clean wedge** | Perpetual |
| **Reportable-incident handling** | **perpetual, high volume** | consultant time | **80% — highest-value perpetual job** | Perpetual |
| **Worker-screening administration** | perpetual | absorbed in HR SaaS | **90% — near-pure engine territory** | Perpetual |
| Policy & procedure drafting | on registration + standards updates | $2–8k consultant / $500–5k templates | 35% (classic consultant moat) | Wave amplifier |
| Responding to Commission action | ad hoc rising | above ordinary consulting | 20% (draft/politics heavy) | Retention lever only |
| Governance / board reporting | perpetual mo/qtr | absorbed in retainers today | 50% | NEW SKU |
| **Restrictive-practice authorisation & reporting** | **monthly** for BSP-implementing | consultant tier | 55% (per-state matrix determinate) | Perpetual, small segment |

**Corroboration**: NDS 2025 says **50% of providers have not modernised** (mix of spreadsheets/consultants/fragmented software); **25% rely entirely on spreadsheets**; sector spends **4–6% of revenue on compliance**. That's the buyer's status quo the tool competes against.

### Wave-driven vs perpetual demand

- **WAVE** (refills funnel but doesn't sustain subscriptions): SIL mandatory registration; Jul 2027 personal care/daily living/closed settings expansion; worker screening renewal wave (Feb 2026 → 2027, all 2021-issued clearances)
- **PERPETUAL** (recurring, independent of wave): ~5,791 full re-audits/yr (17,374 ÷ 3); ~2,900 mid-term audits/yr; reportable incidents [INFERENCE ~70,000/yr at 3–5 per provider]; ~30,000 monthly RP reports/yr for BSP-implementing subset; ~69,500 worker-screening renewals/yr; ~7,000 amendment-driven policy refreshes/yr

### Perpetual layer TAM

| Component | Vol/yr | Hrs/event | $/hr | Annual $ pool |
|---|---:|---:|---:|---:|
| Full re-audits | 5,791 | 40 | $120 | ~$27.8M |
| Mid-term | 2,900 | 20 | $120 | ~$7.0M |
| Reportable incidents | 70,000 | 2 | $120 | ~$16.8M |
| Monthly RP reports | 30,000 | 1 | $120 | ~$3.6M |
| Worker screening renewals | 69,500 | 0.5 | $80 | ~$2.8M |
| Amendment-driven policy refresh | 7,000 | 4 | $120 | ~$3.4M |
| **PERPETUAL TAM (provider-side)** | | | | **~$61M/yr** |

At 3–8% realistic annual capture, **$2–5M ARR ceiling from the perpetual layer alone at current pool size**, expandable with the Jul 2027 wave.

### Enforcement momentum

Commission Q1 2025: >6,800 compliance and enforcement activities; 5 provider + 55 individual banning orders; 1,036 corrective action requests. Commission's #1 priority 2025-26 is regulated restrictive practices; enforcement in that area is up **214% YoY**. Integrity & Safeguarding Act 2026 exposes directors/managers/sole traders **personally** to criminal provisions (2 years for unregistered provision; 5 years for banning-order breach) and lifts civil penalties to **$3.3M per serious contravention**.

---

## MODULE 4 — Buyer constraints (per segment)

### 4A. Registration consultants (leverage channel)

- Billing mix [INFERENCE, no census]: **~65% fixed-fee packages / ~30% hourly / ~5% subscription retainers**
- **Fixed-fee tier is the customer** — a consultant selling a $5,000 fixed package who completes it in 20 hrs instead of 40 gains $250/hr effective rate; that's the sale
- **Hourly tier is the enemy** — the tool erases visible billable hours
- Frenemy signal: several consultants (Audit Pilot, FormaOS, ClinicComply, Effective Policy) already ship their own tools — appetite to build or partner exists, and appetite to compete does too
- Etsy template packs floor at **$50–200** — commodity baseline
- White-label appetite [INFERENCE]: weaker for reasoning tools than for template packs; mid-tier positions expertise-as-brand
- Trigger event: the SIL Oct 2026 apps + Jul 2027 wave force one-consultant-serves-3× clients-at-once
- Closing objection: *"My clients pay ME for expertise. If your tool tells them the answer, why do they need me?"*
- **The wedge must be positioned as a billable-hour compressor for fixed-fee packages, not as a replacement for advisory judgment**

### 4B. Owner-operator providers (10–50 staff)

- Existing software stack (published pricing): ShiftCare ~$8–9/user/mo Starter; Brevity ~$15–30/user/mo; Lumary >$50/user/mo enterprise; Splose/VisiCase/SupportAbility pricing not published
- 25-person provider spend on existing stack: ~$225–750/mo
- Compliance tool at $99–299/mo sits below existing spend but **must fight for attention** in a saturated tab-row
- Primary user is **not the owner** — the quality manager, office manager, or clinical lead pulling double-duty
- $2M-revenue provider: ~$80–120k/yr compliance-attributable cost — room for a $2–4k/yr subscription **only if it visibly shifts hours**
- Software fatigue is real: "software becoming full-time job rather than supporting care delivery" (Vertex360)
- Trigger events: audit notice (~90 days out, highest intent); reportable incident triggering Commission follow-up; new registration group being added; 1 Oct 2026 SIL hard deadline; consultant/auditor/board recommendation
- Objection: *"consultant already does this"* / *"we've got templates"* — beat with **provenance + amendment monitoring** (consultants and Etsy templates cannot ship a live *"which clauses moved since your last audit"* register)

### 4C. Boards / governance (NEW SKU, post-Integrity Act)

- Verified named risks:
  - Civil penalties **up to $3.3M per serious contravention**
  - Criminal: 2 years for unregistered provision; 5 years for banning-order breach
  - **Directors, managers, sole traders exposed personally** to criminal provisions
  - Expanded banning powers cover applicants, auditors + employees, registration consultants
  - Whistleblower reforms (anonymous OK, good-faith requirement removed, former workers protected)
- Practice Standards Module 2 (Governance) requires board minutes showing **substantive** oversight of quality/risk items, not just attendance
- Post-Integrity board question: *"What NDIS obligations changed this quarter, and have we minuted our oversight of them?"* = a deterministic clause-cited engine query. **No incumbent tool answers this in NDIS context.**
- Signer: Company Secretary / Audit-Risk Chair (larger providers); CEO/MD (owner-operator boards); independent directors want personal-liability protection
- **BoardPro/Diligent/Sherpany are meeting-cycle tools** — not obligation registers with provenance
- **Wedge: per-board (not per-user) "NDIS Obligations Register + Amendment Feed" module** outputting a board-pack section, priced **$500–1,500/mo per organisation**, positioned alongside BoardPro
- Small pool (registered providers with a formal board = subset of 17,374, [INFERENCE] ~3–5k) but very high WTP per organisation
- Deal-breakers: legal defensibility (clause-cited to the Act version in force at the time) + change-log audit trail (proof board was informed of changes when they occurred)

---

## MODULE 5 — Use-case inventory + sequencing

### Verdicts (each use case: BUILD FIRST / BUILD LATER / KILL / OEM-ONLY)

| Use case | Determinacy | Verdict | Why |
|---|---|---|---|
| (a) **Obligations-profile determination** — clause-cited "what applies to your groups from what dates" | HIGH — pure enacted text mapping | **BUILD FIRST** | Proves the moat; no incumbent found selling clause-cited effective-dated obligations register per registration group; low customer-input friction (structured picklists only) |
| (b) Registration-group / audit-pathway | HIGH group→pathway; MEDIUM group selection from prose | **BUILD FIRST as FREE top-of-funnel** feeding (a); **OEM-viable widget** for consultants | Free content everywhere; seeds CRM into (a) |
| (c) **Amendment radar** — mapped to provider's registered groups + jurisdiction | HIGH for detection/diff/effective-date | **BUILD FIRST** | Monetises moat perpetually; highest alignment with founder's declared moat; no incumbent found selling per-registered-group amendment radar with effective-date + stock-in-trade windows |
| (d) Audit-evidence pack generation | HIGH for obligation→required-evidence type; LOW for policy adequacy | **BUILD LATER / OEM-ONLY** | Densely served (Centro Assist, FormaOS, ClinicComply, Audit Pilot, BNG SPP, Willow AI); direct build = feature war |
| (e) Incident-notification timeframe engine | HIGH timeframe rule; LOW severity classification | **KILL as standalone; OEM-ONLY** for content layer | **FormaOS explicitly markets "24-hour countdown timers for priority incidents and 5-business-day tracking"** as headline feature; commodified across incumbents |
| (f) Worker-screening obligation checker | HIGH rule; MEDIUM role classification | **KILL for direct; OEM-ONLY** for content | Commodified in HR/rostering SaaS $8–25/user; roster integration is a moat founder shouldn't build |
| (g) Policy-coverage gap mapping | MIXED — required-topic list determinate but "adequately addresses" needs prose reading | **KILL** | Accurate version requires AI-at-answer-time (contradicts founder's positioning); Audit Pilot already ships |
| (h) **Board/directors compliance attestation report** | MIXED — obligations state derivable if (a)+(c) built; attestation is judgment | **BUILD LATER as upsell to (a)+(c)** | No incumbent found; existential director exposure; wait for first Integrity Act prosecutions ~12–24 months post-assent |
| (i) Restrictive-practice authorisation & reporting | HIGH freq/timeframes/state matrix; LOW classifying regulated practice | **BUILD LATER** | High value (Commission #1 priority, +214% YoY enforcement) but jurisdictional scope is a corpus-building project |
| (j) New-staff onboarding compliance pack | MEDIUM | **KILL** | LMS commodity (etrainu, iinduct, Induct for Work, ShiftCare); no rules-engine moat |
| (k1) Key personnel suitability + change-notification | HIGH | **OEM-ONLY** — bundle into (c) amendment radar | Small standalone niche |
| (k2) BSP practitioner suitability | — | **KILL** | Buyer segment too narrow |
| (k3) Whistleblower framework compliance | — | **BUILD LATER** as component of (h) | Undefended white space, small standalone |
| (k4) Interim PBSP 30-day window tracker | HIGH determinate timeframe | Fold into (i) | Small standalone |
| (k5) Fair pricing / PAPL compliance | — | **KILL** | Commodified in billing platforms (Brevity, ShiftCare) |

### MVP slice — recommended sequencing

**Build first, in order: (a) OBLIGATIONS-PROFILE → (c) AMENDMENT RADAR → (b) REGISTRATION-GROUP / PATHWAY (as free top-of-funnel).** Phase 2 upsell: **(h) BOARD ATTESTATION REPORT** once Integrity Act penalty case-law lands.

Why these cohere:
- (a) proves the moat — every stated obligation carries a clause id + effective date + legislative-instrument link. Incumbents cannot produce this at their price point. This is the *show-don't-tell* for provenance
- (c) monetises the moat perpetually. Amendment radar is only useful if cited and dated per your groups — the two capabilities are inseparable, which locks out anyone shipping only one
- (b) is the free top-of-funnel — every prospective new provider Googles *"verification or certification"*; capturing them with a determinate widget seeds the CRM into (a)
- (h) is the upsell to directors once the first Integrity Act prosecutions land (expect 12–24 months post-assent)

**Who it serves**: ~2,000–4,000 SIL / behaviour-support / certification-pathway providers registering or renewing in the Jul 2026–Jul 2027 window, plus their ~5,000–8,000 [INFERENCE] quality leads/directors under Integrity Act personal-exposure pressure. Consultants become a **channel**, not a competitor — (a)/(c) are what they currently bill against by hand.

### OEM parallel revenue opportunity

Sell deterministic content layers as a data feed to **Centro Assist**, **FormaOS**, **ClinicComply**, **Smart Compliance Systems**, and **Audit Pilot** — all of whom already ship the surface but none of whom can defend clause-provenance and effective-date discipline. Layers to license:

- Obligation → required-evidence type map (feeds their audit-pack products)
- Incident-timeframe rules (feeds their incident modules)
- Worker-screening rules by jurisdiction (feeds their HR modules)

This is the cleanest way to monetise the corpus without building rostering/HR/LMS integrations.

---

## What Modules 1–5 changed vs the Phase 2 mini-dive

| Phase 2 concern | Module 1–5 finding |
|---|---|
| "Corpus mid-rewrite; hostile to a deterministic DB" | The green-zone verbatim corpus is ~10 F-instruments; the churn is concentrated in ONE instrument (Provider Registration & Practice Standards Rules); four instruments are structurally quiet 24+ months |
| "1 Oct 2026 SIL deadline unreachable" | Confirmed unreachable as a wave play; but the **1 Jul 2027 expansion is bigger, funded ($77.4M/yr in additional regulatory cost) and has consultant channels already at capacity limits** — the auditor exodus (2 of ~17 AQAs exited Apr/May 2026) creates a structural bottleneck that a validated pre-audit workflow tool exploits |
| "Consultant WTP for determination-only unvalidated" | Consultant billing is ~65% fixed-fee packages — **margin expansion, not cannibalisation** — with named firms already shipping their own tools (Audit Pilot, ClinicComply, FormaOS, Effective Policy); appetite exists |
| "Naive obligations register already shipped by SaaS incumbents" | Confirmed for e/f/g/j (kill list). **But no incumbent found selling clause-cited effective-dated obligations register + per-registered-group amendment radar** — the wedge is real. New competitor surfaced: **ACIA Quality Portal** must be explicitly out-performed on clause depth + effective-dating |
| "Nothing new for boards" | **Integrity & Safeguarding Act 2026 creates a genuine NEW SKU** — per-board NDIS obligations register + amendment feed, priced $500–1,500/mo, alongside BoardPro/Diligent — no incumbent occupies it |

---

## Decisions for the founder — before Modules 6–11

1. **Product shape (Module 6 input)**. Three coherent options: (i) **consultant white-label obligations engine** — sell to the ~30–60 named firms as a billable-hour compressor; (ii) **provider self-serve subscription with amendment radar** — sell direct to owner-operators + quality managers at $99–299/mo, expecting 3–8% capture of the perpetual pain; (iii) **OEM rules layer** licensed to the existing provider-SaaS vendors (Smart Compliance Systems, FormaOS, ClinicComply, Centro Assist) — they lack provenance and would buy the content feed. Options (i) and (ii) can run in parallel; option (iii) is orthogonal.
2. **ACIA call**. Compete on clause-provenance depth (highest-risk); partner (they already have distribution and NDS-adjacent trust); or route around (aim at boards and consultants rather than provider self-serve). This is the single most consequential competition decision.
3. **Pricing anchor.** At what price point is the SME provider willing to buy: $99, $199, $299/mo — or is the reality that only consultants and boards are willing to pay, at $500–1,500/mo per organisation? Modules 6–8 (product, GTM, revenue scenarios) all pivot on this.
4. **Corpus scope.** Confirm the Tier A build-set (~10 F-instruments); confirm the paraphrase-plus-link handling for Pricing Schedule 2026-27 (CC-BY-NC constraint is non-negotiable); confirm the **defer** list for the 2027 wave until commencement instruments issue.

---

## Honesty ledger

- **All primary AU government hosts (`legislation.gov.au`, `ndiscommission.gov.au`, `ndis.gov.au`, `health.gov.au`, `aph.gov.au`, `oia.pmc.gov.au`) returned 403 to the research proxy in this session.** F-numbers, dates, and instrument identifiers verified via search index; content via secondary sources (commentators, law firms, peak bodies, IBISWorld, ANAO). Founder must re-fetch every F-number and commencement date on a browser before locking a corpus.
- Provider count by registration group: not publicly published in aggregate; dataresearch.ndis.gov.au CSV download required (blocked in session)
- Exact AQA count Aug 2026: needs Commission's live *Find an Auditor* page (blocked)
- OIA Supplementary Analysis 2026 headline provider-count for Jul 2027 cohort: PDF blocked; range is inferred from IBISWorld enterprise count and NDIA payment-category splits
- SIL applications received to date: no public running tally; Commission media contact required
- State % splits: needs CSV download
- Reddit r/NDIS practitioner voice: did not surface through WebSearch's Reddit indexing — a direct pass through Reddit search or Facebook groups would strengthen practitioner-quote evidence
- All revenue math is [INFERENCE] — no comparable-product benchmarks exist in this niche
