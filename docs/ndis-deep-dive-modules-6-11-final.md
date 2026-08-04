# NDIS Deep Dive — Modules 6–11 Final Verdict

**Status:** Modules 6–11 COMPLETE. Companion to `ndis-deep-dive-modules-1-5.md`. **Date:** 2026-08-04. **Method:** six parallel research passes (~250 further searches/fetches) covering product design + liability, corpus feasibility in person-weeks, competition sweep, GTM + validation sprint, care-sector expansion, red team, and a direct practitioner-voice hunt across Reddit/Facebook/LinkedIn/forums.

**Executive summary — the final call:**

**GO on NDIS, sequenced as OEM-lead + consultant-parallel. Odds of first paying revenue inside 9 months: ~65%.** Product-shape and pricing landed defensible on the evidence; corpus feasibility is 8.5–12 person-weeks to first demoable and the fetch problem is a sandbox artefact, not a public block; the competitive seat is confirmed empty (category (c) ≈ 0% of buyer wallet); the July 2027 wave doubles the TAM inside the founder's window; and Aged Care is a genuine ~10–15 person-week extension for a ~3× cost multiplier. The three material updates against the Modules 1–5 checkpoint: **(1) BNG SPP is not four peak-body competitors, it is ONE white-label platform underneath ACIA / NDS / ATCA / SHS — selling TO BNG as an OEM content feed is higher-leverage than selling around them; (2) Willow AI (heywillow.ai) launched into NDIS March 2026 as a fresh VC-funded fast-follower — must be watched as a monthly signal; (3) the practitioner voice reveals ~55% of providers made no profit last year, forcing a reframe of the sale from "productivity upgrade" to "pays for itself vs the cost you're already paying."**

**What flips the verdict:** if two of these three go against the founder inside 12 months — (a) OEM vendors decide to build in-house rather than license, (b) BNG SPP or Audit Pilot ships clause-provenance in one release, (c) solo-founder maintenance model produces a single missed amendment discovered by a customer — the perpetual-corpus thesis needs replacement rather than iteration.

---

## MODULE 6 — Product design

### 6A. Library-vs-oracle liability decision (per SKU)

**Founder default is correct: ship as regulatory-content library, not compliance oracle.** Output shape is `{clause_text, citation, effective_date, instrument_version, supersedes}` — never `{status: "compliant"|"non-compliant"}` and never "you must" / "you should" language. This is the same posture LexisNexis and Thomson Reuters have used with statutory annotation for 30+ years without adviser-liability exposure.

**AU legal ground (the real constraint):**
- **Negligent misstatement (tort):** MLC v Evatt (1968) 122 CLR 556 narrows Hedley Byrne — duty arises where defendant is in the business of giving advice, holds out as adviser, or knows reliance will occur without independent inquiry. Positioning as *content infrastructure* rather than *advice* is a live pleading defence. Perre v Apand (1999) requires reliance + vulnerability + defendant control for pure-economic-loss — a B2B customer with their own audit obligations is *not* vulnerable in the required sense.
- **ACL s18 (misleading/deceptive):** cannot be contracted out of. Clayton Utz (2023): "exclusions might not be worth the paper they're written on." The defence is at the *conduct* layer: never claim completeness ("all your obligations"), accuracy ("correct advice"), currency ("always up to date"), or fitness ("audit-ready"). Substitute: "verbatim clause text and citations from the Federal Register of Legislation as at [ingest_timestamp]."
- **No AU tort case directly on-point for software compliance tools** — founder would be a test case if it went that way. Absence of precedent is a warning, not a comfort.

**Comparator disclaimers stolen:**
- BoardPro: "BoardPro is not your adviser or consultant and use of the Service does not constitute the receipt of advice" — clone the first sentence verbatim. NZ jurisdiction clause is not available to an AU founder.
- ACIA: the linguistic move — "self-assessment tool" — shifts liability to the user. **Steal that frame; every output surface reads "self-assessment reference" not "compliance status".**
- RTOs: "current at date of publication" watermark. **Adopt.** Every clause card and PDF export gets a "current at [date]" stamp.

**Oracle-creep vectors per SKU (product-design defence beats paper defence):**

| SKU | Creep vector | Product defence | Contract defence |
|---|---|---|---|
| OEM feed | Licensee wraps content in "compliant/not compliant" UI | Every API response includes `"disclaimer": "Verbatim regulatory text; not compliance advice"`; forbidden-use schedule enumerates 6 UI patterns (traffic lights, pass/fail badges, "action required" prompts unconnected to a clause) | Licence mandates verbatim attribution + effective-date display; prohibits presenting output as licensee's advisory determination; requires back-to-back indemnity |
| Consultant seat | Consultant white-labels a PDF as "the compliance report I prepared" | White-label PDF footer is **not customisable**: "Regulatory reference produced by [Consultant] using content infrastructure licensed from [Rules Engine]. Interpretation and application is the professional responsibility of [Consultant]" | Consultant T&Cs require acknowledgement they are the advising professional; prohibit onward-sale of raw output; indemnify Rules Engine against consultant's advice |
| Provider self-serve | **Highest-risk SKU** — non-sophisticated end-user, no professional intermediary, most sympathetic plaintiff | Sophisticated-user acknowledgement modal at every session; no pass/fail semantics; no "recommended actions"; independent-review suggestion at every PDF export | ToS require sophisticated-user acknowledgement; require obtaining independent professional advice. **Realistic: ToS will not save you if a provider is fined $3.3M under Integrity Act 2026 and blames the tool. Defence is product design, not paper.** |
| Board SKU (Phase 2) | Highest oracle temptation — directors want a green tick | Deferred partly for this reason. If built: structured exposure register (obligation → clause → last-verified-date → responsible-officer field the *provider* fills), not a director dashboard rating the provider |

**Rule of thumb:** if the output would embarrass a barrister asked "is this legal advice?" — cut it.

### 6B. Three SKU specs

**SKU 1 — OEM Rules Feed ($2–5k/mo per licensee, ship month 3):**
- REST API: `GET /clauses`, `GET /clauses/{id}`, `GET /instruments`, `GET /amendments?since=…`
- Clause object: `{id, instrument, section, subsection, clause_text_verbatim, citation_formatted, effective_from, effective_to, supersedes_id, superseded_by_id, ingest_timestamp, source_url}`
- Webhook on amendments within 48 business hours of Federal Register publication
- Weekly full-corpus snapshot (JSON + Postgres dump); Postgres logical replication bundle for enterprise tier (+$1k/mo)
- Tier A only in v1 (~10 F-instruments verbatim); Tier B (Pricing Schedule) as separate `/pricing_schedule` endpoint with CC-BY-NC attribution **enforced in response headers** and required in licensee UI (audit trail via referrer logging)
- Auth: API key per tenant, 10k requests/day soft quota
- Sandbox environment with full corpus, 30-day free integration window
- Uptime target 99.5% (a solo founder cannot honour four-nine SLA)
- Amendment ingestion is a scheduled scraper against Federal Register RSS + weekly full diff; **human-in-the-loop QA before publish** — this is the moat vs "GPT scrapes it too"
- **Mapping layer document per each of 5 named vendors** — 1-pager showing how Rules Engine clause IDs map into their internal obligation IDs. Do the mapping FOR them in the pilot — this is the sales motion.

**SKU 2 — Consultant Seat ($299/mo, unlimited provider profiles, white-label, ship month 3–4):**
- Web app, email/password + Google SSO
- Consultant creates unlimited provider profiles: legal name, ABN, registration status, service types, LGA, worker headcount bracket, RP indicator, SIL flag — intake wizard ~90 seconds/profile
- Per-profile output: **obligations register** (Tier A clauses filtered by profile, each with citation, effective date, verbatim text, "typical evidence" hint where instrument specifies)
- Export: PDF (white-labelled logo/brand/contact) + CSV + web share link (tokenised)
- Monthly amendment digest email per profile with old-vs-new diff
- Footer disclaimer NOT customisable

**SKU 3 — Provider Self-Serve ($149/mo, single-tenant, inbound-only, ship month 6–9):**
- Same engine, single-tenant
- Freemium: 3 clause detail views free/month before signup
- Web view + PDF export (Rules Engine branded)
- Monthly amendment digest email
- No sales motion — SEO + content + Reddit r/NDIS + LinkedIn organic
- Deliberately narrow — this SKU exists to (a) capture inbound demand you'd otherwise refuse, (b) generate SEO surface, (c) feed data on which obligations providers self-select against (product-discovery signal for Board SKU)

**SKU 4 — Board SKU ($500–1,500/mo per organisation, Phase 2):**
- Trigger to build: Phase 1 combined ≥$1M ARR + ≥5 unsolicited director-level inbounds + ≥1 confirmed Integrity Act enforcement action where director personal liability applied
- Quarterly director briefing pack (PDF) with structured exposure register — obligations, clause citations, provider's own last-reviewed-date and responsible-officer field the provider fills. Board reads the register, board draws its own conclusions.
- Sold to boards, not to CEOs. Separate credentialed access (governance principle: management cannot filter what board sees).

### 6C. Revenue scenarios (AUD MRR, odds subjective priors)

| Horizon | Pessimistic (25%) | Base (55%) | Optimistic (20%) |
|---|---:|---:|---:|
| **6 mo** | $1,942 MRR / $23k ARR | $7,975 / $96k ARR | $17,950 / $215k ARR |
| **12 mo** | $9,470 / $114k | $29,900 / **$359k** | $59,800 / $718k |
| **24 mo** | $18,930 / $227k | $94,150 / **$1.13M** | $229,100 / $2.75M |

**Assumption stress:** base-case 24-month lands at $1.13M ARR — inside the perpetual $2–5M TAM ceiling but well below it. Base assumes 200 consultant seats at month 24 out of ~230–460 addressable firms — **43–87% penetration of the whole consultant TAM. This is aggressive** and depends on 3–4 anchor firms turning into evangelists. Optimistic ($2.75M) approaches the ceiling and would need Boards SKU or corpus expansion (Practice Standards 2.0, graduated-registration Rules) to break through.

**Pessimistic $227k = solo-founder-with-runway outcome, not a business.** Kill zone.

### 6D. Sequencing plan

- **Months 0–3: content ships first** — ~10 F-instruments corpus production-ready, amendment pipeline running, QA workflow in place. Cannot be shortcut; the entire business is the content operation.
- **Month 3: OEM API + consultant seat launch simultaneously** — OEM = high-touch enterprise sales (5 named vendors, founder personal); consultant seat = design-partner motion (anchor targets Provider+, Provider360, Avaana = 14,200 downstream provider surface area between them).
- **Do NOT launch self-serve yet** — demand sink you cannot support until other two are proven.
- **Month 3–6: signal watch. Go/no-go trigger for self-serve** = ship if EITHER (a) OEM has ≥1 signed LOI + 2 active pilots OR (b) consultant seat has ≥15 paid seats within 90 days.
- **Month 6–9: self-serve launches conditionally.** If neither trigger hit, DO NOT ship — the model is broken; run kill-criteria checks and pivot.
- **Month 12: Board SKU trigger checkpoint** (requires $1M ARR + 5+ director inbounds + 1 confirmed Integrity Act enforcement precedent). Otherwise defer indefinitely.

---

## MODULE 7 — Corpus feasibility in person-weeks

### Fetch reality (structural)

Every Australian government host (`legislation.gov.au`, `ndiscommission.gov.au`, `ndis.gov.au`, `austlii.edu.au`) returned 403 in this session — but every URL exists and is indexed. Extraction is not a discovery problem, it is a fetch-from-AU-IP problem. Founder re-runs from home network before locking corpus.

### End-to-end cross-reference chain (feasibility proof)

**Scenario: SIL provider using PRN chemical restraint without state authorisation, not in the BSP.**

Seven hops, four instruments, one guidance doc, three portal actions, one seven-year record artefact:
1. NDIS Act s73Z Reportable incidents (~$330k individual / $1.65M corporate civil penalty)
2. Incident Rules F2018L00633 s16 — sixth category = operative trigger
3. Restrictive Practices Rules F2018L00632 — defines "regulated restrictive practice"; requires BSP authorship + implementer registration alignment
4. Provider Registration & Practice Standards Rules Schedule 3 (Specialist Behaviour Support) + Implementing Behaviour Support Plans module — audit standard + monthly RP-use reporting
5. Quality Indicators Guidelines F2018N00041 — auditor-facing evidence indicators
6. Commission guidance — "Reportable incidents Detailed Guidance for Registered NDIS Providers" — operationalises 24h Immediate vs 5-business-day form split, portal path
7. Operational implications — 24h Immediate Notification Form + 5-business-day form + monthly RP reports + records ≥7 years + internal complaint procedure + BSP revision + worker screening review + Code s6(f)–(g) reasonable-steps evidence

Every hop has a stable primary-source citation — **exactly the depth the founder's NSW engine already handles.**

### Effective-date engine schema (minimum)

```
instrument(id, f_number, title, principal|amending, made_date, sunset_date)
compilation(id, instrument_id, compilation_no, in_force_from, in_force_to, source_url, source_hash)
clause(id, compilation_id, clause_path, heading, text, parent_clause_id)
clause_history(id, clause_ident_key, compilation_id, text,
               change_type[NEW|AMENDED|REPEALED|RENUMBERED], amending_instrument_id)
defined_term(id, compilation_id, term, definition, defined_in_clause)
cross_ref(id, from_clause_id, to_ref_type[SECTION|RULE|STANDARD|EXTERNAL],
          to_ref_target, to_ref_compilation_id_at_time_of_write)
transitional_rule(id, applies_from, applies_to, participant_scope, source_clause)
```

Key challenge: **cross-reference resolution at a point in time** (when Incident Rules s16 refers to Restrictive Practices Rules, resolve to the RP compilation in force on the same date as the s16 compilation being rendered). Founder's NSW engine already solves this class for LEP/DCP amendments — same shape, 1/50th the scale.

### Person-week estimates (from NSW throughput anchors)

| Component | Full Tier A | MVP subset (obligations + pathway + amendment radar) |
|---|---:|---:|
| Corpus extraction + structuring + verification | ~13–14 person-weeks | ~5.5 person-weeks |
| Amendment monitoring infrastructure | (included) | 40 hrs one-time |
| Engine port (existing NSW engine) | — | 3–6 person-weeks |
| **Total to first demoable** | — | **8.5–11.5 person-weeks** |

**Recommended demo slice: 6-week SIL slice** (Practice Standards Core + SIL supplementary + Restrictive Practices + Quality Indicators Core) = 9–12 person-weeks total. SIL is the highest-liability, highest-margin registration group and the sharpest possible ICP; sellable at ~$500–$1,500/mo per provider on its own.

Small-start alternatives:
- **3-week Code+Incident+Complaints** = 6–9 person-weeks total; shippable as waitlist bait, thin as primary product
- **10-week full MVP** = broader ICP; sellable at $1,000–$3,000/mo

### The Pricing Schedule copyright wrinkle

The NDIS Pricing Schedule 2026-27 (99pp) is on a non-commercial licence — **conflicting search snippets show CC BY-NC 4.0 in one place and CC BY-NC-ND in another. The ND (No Derivatives) tail would block paraphrase as well as verbatim republish.** Founder must verify the notice directly.

**Least-risky architecture (recommended):**
- MVP weeks 1–6: **pointer-only Tier B** — store item number, service-category label, and price limit as facts (uncopyrightable single data points per *IceTV v Nine Network Australia* HCA 2009 — Australian copyright doesn't protect facts). Do NOT store surrounding explanatory text, cancellation rules, travel rules. Link out to the current NDIS.gov.au PDF for any narrative rule. Cite source URL + fetched date on every price fact.
- Post-revenue (month 4+): commercial licence request to NDIA if a customer explicitly demands embedded rules.
- **Never** republish the PDF; **never** paraphrase the narrative rules while the ND uncertainty stands.

Pricing Schedule is deferrable for MVP without loss of value — obligations, incident reporting, and audit prep sit on Tier A CC-BY 4.0 clean.

### Amendment monitoring loop

Daily 07:00 AEST cron pulls the Federal Register "what's new" listing; filter to the 10 watched F-numbers + any child amending instrument citing them; re-extraction trigger on new compilation number or new amending instrument; automated diff within 30 min of daily poll; **manual verification gate before user-facing publish** → effective SLA "amendment made + one business day." Silent-error defence: monthly full-corpus hash re-fetch to catch register-side corrections that didn't trigger a new compilation number.

---

## MODULE 8 — Competition sweep

### The critical finding: BNG SPP is one platform, not four

**The ACIA Quality Portal is a white-labelled BNG SPP instance.** ACIA does not build software; it owns the ACIS standard and licenses the SPP platform from BNG. The same platform underlies NDS Quality Portal, ATCA Quality Portal, and SHS Quality Standards Portal. Peak-body channel is **ONE PLATFORM, NOT FOUR**.

BNG SPP has 60+ cross-mapped standards, 1,500+ customers, and an aged-care→NDIS cross-mapping ("satisfies 70% of Core Module, 90% of Code of Conduct"). Priced from **$871.20 incl GST/year**, income-scaled, 15% NDS member discount, 10% ACIA member discount. 20+ years in market. Adding clause-level `source_ref + effective_date` is a **schema change on existing content, not a rebuild**. BNG's competency is portal software + peak-body relationships + template curation — **amendment monitoring is a data-pipeline competency they don't have.** The realistic move is BNG licensing a rules feed rather than building it in-house.

**The founder's opportunity: be the content feed BNG cannot afford not to license.** This is the higher-leverage play than selling around them.

### Fast-follower ranking

| Rank | Vendor | Threat | Why |
|---|---|---|---|
| 1 | BNG SPP | HIGH | Distribution moat + schema-only upgrade needed. **Sell TO them.** |
| 2 | Audit Pilot | HIGH | 800+ providers, aggressive marketing, 13,000+ automated checks daily. Weakness (AI-at-answer-time) is exactly founder's differentiator, but can rebrand a citation layer in a quarter. |
| 3 | Willow AI (heywillow.ai) | MEDIUM-HIGH | **NEW March 2026 launch** — Willow Compliance Pty Ltd, Sydney, contact James Driscoll. AI-native compliance orchestration, VC-funded push. Most likely to buy content feed rather than build. |
| 4 | FormaOS | MEDIUM-HIGH | **From $297/mo**; obligation register mapped per registration group at signup; blog already gestures at effective-dating awareness. Credible <2Q build. |
| 5 | Centro ASSIST (Holocentric / Volaris) | MEDIUM | 3,000+ NDIS+Aged Care providers; enterprise parent engineering resources; incumbent playbook (renewal workflow + templates) needs strategic pivot not sprint. HIGH threat via installed-base leverage. |
| — | PQM Pro / Provider+ | MEDIUM | "Manual-provenance" model — sells outcome (up-to-date policies) without rules engine. Closest philosophical competitor. Win-condition: make clause-linked provenance visibly better than a consultant's promise. |

**Category share of buyer wallet:**
- (a) Newsletter/template packs: ~35–45% (Effective Policy, DSP, Provider360, Etsy, Lemma Hub, PQM Pro manual stream)
- (b) Workflow/checklist SaaS: ~50–60% (Smart Compliance, Centro, FormaOS, Audit Pilot, GoodHuman, FlowLogic, BNG SPP, ClinicComply, Complynce, Willow, Vertex360)
- **(c) Genuine clause-cited effective-dated deterministic rules engine with amendment radar: ~0% — CONFIRMED EMPTY**

Absence claim: searched category-A directory pages (Capterra AU, SoftwareSuggest, SlashDot, SourceForge), all named incumbents' product pages, and targeted keyword searches (`"clause"`, `"citation"`, `"effective-dated"`, `"amendment monitoring"` in NDIS regtech context). No vendor publishes clause-level source references in their compliance surfaces; no vendor publishes a public standards changelog scoped to the NDIS Practice Standards. **The seat is empty. Moat is real for at least 2 quarters.**

### Operations platforms = distribution partners, not competitors

Lumary, ShiftCare, Brevity, GoodHuman, SupportAbility, CarePlan, CareMaster, CareVision, Splose. **ShiftCare already partners with Provider360 for policy content** — the content-OEM partnership template already exists in this market.

### The Commission's own platform is not a competitor

New NDIS Commission Provider Portal available H2 2026 — transactional (registrations + reportable incidents + BSPs consolidated), "links to legislation directly on screens", PRODA→myID/RAM cutover 30 Sept 2026. Not a rules engine. LOW threat as direct competitor. **MEDIUM threat as an upstream data source** — if the Commission publishes machine-readable Standards, it commoditises the data-acquisition step upstream of the product. Watch for procurement notices on austender.gov.au.

---

## MODULE 9 — GTM + validation sprint

### Named contacts (OEM)

- **Centro ASSIST** — CEO Bruce Nixon; co-founder/CTO Derek Renouf; **enter via Arahni Sont (Strategy & Partnerships)** — softest surface. Volaris/Constellation portfolio company; expects formal MSA + quarterly budget cycles + 60–90 day procurement.
- **FormaOS** — priority target #1 (heaviest content maintenance burden across multiple regulatory regimes). No named exec public; `hello@formaos.com.au` + LinkedIn company-page monitoring.
- **ClinicComply** — RACGP/Privacy Act core; NDIS is a sidecar; feels content-debt pressure most acutely. Cold contact form + LinkedIn.
- **Smart Compliance Systems** — `scs@effectivepolicy.com.au` (Effective Policy spinout). Consultancy-owned = views content as moat. Lowest-probability of the five.
- **Audit Pilot** — `hello@auditpilot.com.au`. "Built by 130 auditors" narrative = hardest to convince they need external content. Position: "our clause-cited feed makes your AI checks defensible in an actual QAO audit finding review."

### Named contacts (consultants)

- **Tania Gomez** — Sydney, qualified auditor, hosts *The Profitable NDIS Provider* podcast. **Podcast guest slot is warmest entry**.
- **Provider+** (Tania Gomez co-founded, now spun out; current CEO "Will" [surname unverified]) — 8,200+ providers; approach as frenemy peer, not supplier.
- **Provider360** (rebranded from Centric 2024, Adelaide) — 3,000+ providers; publishes free tooling; friendly to content-first partners.
- **Engels Floyd Quality Consulting** — Sharon Floyd + Jennifer Engels (founded 2012); publishes SIL mandatory-registration explainer.
- **Avaana NDIS** — team of former lawyers, 3,000+ providers; **lawyer-DNA firm = perfect design partner** (they will scrutinise clause-citation quality hardest).
- **HCPA (Kyle Hunt, Founder & CEO, ~130 staff, 10,500+ clients)** — **too big for a $299 seat, treat as sixth OEM prospect** (HCPA runs its own NDIS compliance software).
- **Team DSC** (Roland + Evie Naufal) — media/education-first; may **distribute the trust artifact rather than license the tool**.
- Nacre Consulting (Cathy Love, allied-health lean), Sky Staff, EnableUs, Paperbark NDIS, Provider Institute (VeriCert), LMS Compliance — cold contact.

### Named podcasts + LinkedIn voices

Podcasts to guest on: **NDIS Insights with Dr George** (Dr George Taleporos, biggest reach); *Disability Done Different* (Team DSC); *The Profitable NDIS Provider* (Tania Gomez); *The Provider NDIS Mentor* (Greg Chadwick); *The Steadway NDIS Podcast* (Chris Hall).

LinkedIn highest-signal voices to engage substantively before pitching: **Michael Perusco (NDS CEO Nov 2024–)**, **Hayley Dean (NDS Board President 2026)**, Kyle Hunt, Tania Gomez, Cathy Love, Evie Naufal.

### Peak-body timing

- **DIA** (Disability Intermediaries Australia): CEO transition — Jess Harper departed 24 April 2026 for Cultura CEO; Tanya Walford is Acting; Board searching for permanent CEO Q3–Q4 2026. **Wait for the new CEO before pitching partnership** — org's strategic priorities will reset.
- **NDS**: apply for supplier membership → pitch a members-only clause-diff briefing series → convert to preferred tooling status.

### 2026–27 events (verified dates)

| Event | Dates | Play |
|---|---|---|
| NDS Disability at Work Conference | 5–6 Aug 2026, Sydney | Too soon to sponsor — attend as observer |
| **DSC Annual NDIS Conference** | **13–14 Aug 2026, Brisbane** | **Highest-value networking event — delegate pass + 15 booked-in-advance coffees** |
| National Care Sectors Conference (NDIS/Aged/Childcare) | 28 Aug 2026, Melbourne + livestream | Cross-sector — useful for the aged-care OEM crossover conversation |
| NDS Executive Leaders Conference | 30 Nov – 1 Dec 2026, Melbourne | Buyer-heavy CEO/board audience — 2027 budget sponsorship candidate |

### Free trust artifact — recommendation

Ship one page combining a chronological reform timeline (every commencement date 2024–2030) with a live amendment ledger (every Rules change with clause diff and effective date). Every entry is a citable, backlinkable URL. Competitors literally cannot match this without a rules engine.

**Kill criterion for the artifact:** by day 60, if <500 unique monthly visitors AND <10 external backlinks AND <5 inbound demo requests attributed to it, retire and reallocate to consultant-channel spend.

### The 2-week validation sprint (fully specified)

**Mock-up:** Figma/PDF prototype of the obligations profile — 3 input fields (registration groups, staff count, target audit date), 5 outputs (pathway assignment cited to source rule; applicable Practice Standards modules with clause references; obligations checklist 15–40 rows each linked to mandating clause with effective date; "what changed in last 30 days" panel; audit-prep gap indicator).

**Interview script — 10 questions, ordered to surface willingness-to-pay BEFORE price:**
1. Walk me through how your team stays current on NDIS Rules changes today.
2. When did the Securing the NDIS for Future Generations Bill 2026 enter your work, and how did you first find out about it?
3. Staff-hours per month tracking and applying regulatory change? What's that costing you?
4. Tell me about the last time a Rules change caught you off-guard. What was the consequence?
5. If a change slipped through to an audit finding, what would that cost — reputation, remediation, lost provider status?
6. [Show mock-up.] Walk me through what you'd expect this to do. What's missing? Confusing?
7. If this worked exactly as shown, what problem does it actually solve for you? In your words.
8. Who else in your organisation would need to see this before you'd buy?
9. What's on your compliance-tooling budget line this year, and who owns it?
10. [Reveal price.] At $X/mo would you sign a founding-member LOI today to lock the discounted rate for 24 months?

**Pre-commit instruments:** OEM = signed 2-page LOI (no deposit); consultants = Stripe pre-auth for month-1 charge at $199/mo founding vs $299 standard (24-month lock); providers = signup + card-on-file for free 30-day trial auto-converting at $99/mo founding vs $149 standard.

**Pass/fail thresholds:**

| Segment | Reachable in 2 wks | Demo threshold | Verbal commit | Pre-commit |
|---|---|---|---|---|
| OEM | 5 vendors | ≥3 of 5 take a call | ≥2 of 5 pilot | ≥1 of 5 LOI signed |
| Consultants | 15 firms cold-approached | ≥6 of 15 book demo | ≥3 of 15 founding-member | ≥2 of 15 Stripe pre-auth |
| Providers | 25 free-trial signups | 25 signups | ≥8 of 25 activate | ≥3 of 25 card-on-file |

**GO / DEFER / NO-GO matrix:**
- OEM GO: ≥2 pilots verbally + ≥1 LOI. DEFER: 1 pilot + ≥3 demos (rerun in 30 days). NO-GO: 0 LOIs + <2 demos.
- Consultants GO: ≥3 seats + ≥2 pre-auths. DEFER: 2 pre-auths OR ≥6 demos with strong pain (retest at $149 founding). NO-GO: <2 pre-auths + <4 demos.
- Providers GO: ≥3 pre-auths + ≥25 trials + artifact SEO baseline. DEFER: 3 pre-auths but low signup (promote artifact). NO-GO: <1 pre-auth + <10 signups.

**Compound rules:**
- OEM GO + Consultant GO + Provider DEFER → build OEM-first, consultant seat parallel, defer self-serve UX
- OEM DEFER + Consultant GO → consultant seat leads (fastest cash), OEM re-approached in 60 days armed with consultant logos as social proof
- All 3 DEFER → problem is packaging, not demand; return to Module 6 pricing
- **All 3 NO-GO → this is the kill signal. Re-scope to a different regulator (aged-care Strengthened Standards) or a different buyer (auditors themselves).**

### 90-day launch plan

- Weeks 1–2: sprint (Figma mock + outbound to 5 OEMs + 15 consultants + landing page for trial signups)
- Weeks 3–4: decision + first-SKU build initiation; publish trust artifact v1; pitch podcast guest slots (recording weeks 5–8)
- Weeks 5–6: build v1 of winning SKU; private beta to first pre-committer; 2 demos/week
- Weeks 7–8: second SKU begins if compound-GO; podcast episodes air; **book DSC Annual NDIS Conference 13–14 Aug Brisbane**
- Weeks 9–10: design-partner in production use; public launch page live; case study drafted
- Week 11: first paid invoice
- Week 12: second and third paying customers close from pre-commit list

**Timing pressure:** the 1 Oct 2026 SIL registration deadline is a hard external forcing function on both consultant and provider segments. Every week between now and 1 Oct pulls demand forward. **Start the sprint no later than mid-August 2026** to capture that window.

---

## MODULE 10 — Care-sector expansion

### The beachhead thesis: NDIS + Aged Care is one market with shared machinery

| Candidate | Verdict | Reason |
|---|---|---|
| **Aged Care** (Act 2024 + Rules 2025) | **BEACHHEAD (strong)** | Same publisher, same Act architecture, same civil-penalty catalyst, ~10–15 person-weeks incremental (vs ~40–60 from scratch — 3–4× multiplier), 15–30% buyer overlap [INFERENCE], larger ACV |
| Childcare / NQF | ADJACENT (weaker) | State-national dual-track architecture = 20–30 person-weeks incremental; buyer overlap essentially zero; not year 1 |
| DVA / Veterans | UNRELATED | Fee-schedule not rights-based Act; billing-integrity not practice-standards; wrong product shape |

**Aged Care Act 2024** (Act 104/2024) commenced **1 Nov 2025** (deferred from 1 Jul 2025 — providers were not ready). **Aged Care Rules 2025 (F2025L01173) = 666 pages confirmed.** 7 Strengthened Quality Standards effective 1 Nov 2025 with the same intent/expectation/measurable-outcomes structure as NDIS Practice Standards.

**Personal-liability mechanism is 1:1 with NDIS.** Section 180 imposes a due-diligence duty on "certain responsible persons" (executive decision-makers of non-government registered providers) with civil penalties up to **4,800 penalty units** for repeated/serious breaches. This is the direct analogue of the NDIS Integrity Act's catalyst.

**Sector distress is present:** ACCPA State-of-Sector — 17% of providers "not at all" optimistic about ability to deliver by 2027; 63% confidence for <50 residents vs 83% for >100; 64% report workforce shortages. Same distress signature as NDIS.

**TAM correction:** residential aged care alone is **$38.7bn in 2025** (up 10.7% YoY — corrected from the earlier ~$32bn). Total sector ~$40–45bn — comparable to NDIS's ~$44.7bn — but with **~60× fewer buyers** (~1,509 vs ~25,000). **Per-provider ACV is probably 2–5× NDIS's.**

**Incumbents are the same shape as NDIS:** Ideagen CompliSpace (enterprise, monitors 250+ laws/regulations/guidelines/codes), BNG SPP + ACIA Quality Portal (already covers Aged Care Quality Standards alongside NDIS Practice Standards in a single portal — **proof the cross-sector product shape is commercially viable**). The wedge is identical: "measurable outcomes with a citation on every claim."

**Sequencing:** NDIS only for months 0–12; begin Aged Care corpus build in parallel from month 9–12 (~10–15 person-weeks + regulatory-analyst time on the 7 Strengthened Standards mapping); Aged Care launch months 12–18, targeting the ~15–30% of NDIS customers who are dual-registered first (zero-CAC cross-sell). Reassess NQF at month 18–24, and only if a distribution partner (peak body, insurer, state regulator) will co-sell.

**Do not pursue: DVA, standalone OOHC, mental health.**

The upgraded pitch: **"One provenance-verified rules engine across your two regulators"** for the 15–30% of buyers who are dual-registered — stronger than either NDIS or Aged Care standalone.

---

## MODULE 11 — Adversarial red team

**12 failure modes, ordered by severity × likelihood. Each carries evidence, an early-warning sign, and a kill criterion.**

### #1 Solo-founder maintenance SLA trap — HIGHEST SEVERITY
Amendment monitoring IS the value proposition. Solo founder + 48-hour SLA + holiday/illness = statistical certainty of a miss inside 24 months. A single miss discovered by a customer destroys "provenance-verified" positioning retroactively across every account.
- Early warning: first customer sees an amendment in a Commission bulletin before the feed; any 72+ hour gap between Federal Register publish and feed update; any single-founder unavailability >5 business days without a hot backup.
- **Kill:** two missed-amendment incidents in a rolling 12 months, or one miss ≥5 business days undetected → hire content-ops FTE before month 12 regardless of ARR, or partner with a legal-publishing firm, or narrow SLA to weekly (not 48h) and reprice down.

### #2 Incumbent adds clause-provenance in one release
Centro ASSIST or FormaOS is the highest-risk incumbent. Adding citation + effective-date fields to their existing content object is a 1-quarter engineering task, not a rebuild.
- Early warning: incumbent release notes reference "citation"/"source"/"regulatory reference"; incumbent posts job listing for "regulatory content operations"; any incumbent partners with a legal-publishing firm or AustLII; OEM sales conversations stall citing "we're evaluating whether to build internally."
- **Kill:** if Centro Assist or FormaOS ships citation + effective-date in a major release *before* 2 signed OEM licensees, the OEM channel is over — pivot to consultant + self-serve. If both ship it within the same quarter, differentiation collapses across all SKUs — consider corpus expansion as the new moat basis, or exit.

### #3 2027 Rules land late or radically different
Securing Bill Senate committee final report was due 14 Aug 2026 (10 days from research). Graduated-registration Rules for July 2027 are NOT YET MADE. Historical AU government legislative-instrument slippage is 6–18 months.
- Early warning: 14 Aug Senate report recommends structural changes; consultation drafts diverge from the four-tier model; Rules ETA slips past Q1 2027.
- **Kill:** if Rules haven't materialised by 1 April 2027 (3 months before rollout), the 2027-registration marketing window closes — pivot messaging to Integrity Act + existing Practice Standards. If Rules land with a fundamentally different tier taxonomy, budget 8–12 weeks of full-time corpus re-mapping.

### #4 Commission ships free obligations tooling
Commission already publishes fact sheets, a self-assessment workbook, and Practice Standards guides. A taxpayer-funded obligations tool is plausible.
- Early warning: any Commission tender for "provider obligations platform"; ministerial press release referencing "free compliance support for small providers"; any Commission-vendor partnership announcement.
- **Kill:** if Commission announces a free platform returning clause + citation + effective date, provider self-serve SKU dies immediately, consultant SKU is degraded ~40%. Freeze self-serve marketing within 30 days; reposition consultant SKU around workflow features Commission won't replicate.

### #5 Political / funding shock to the scheme
Thriving Kids diverts children ≤8 with dev delay/autism to state programs from 1 Jan 2028; ADHD boundary contested; next federal election due mid-2028; NDIS cost trajectory is an election-cycle target.
- Early warning: registered-provider count (currently 17,374) drops for two consecutive quarters; Commonwealth budget line-item reducing NDIS forecast beyond MYEFO baseline; bipartisan announcement narrowing eligibility.
- **Kill:** if registered-provider count falls >15% within any 12-month window post-launch, TAM has compressed enough that base-case revenue is invalid — re-baseline.

### #6 Consultant channel rejects as self-cannibalising
Behavioural resistance is separate from mathematical logic. Consultants who have built proprietary policy libraries will emotionally resist ceding that ground even where economics favour it.
- Early warning: first 3 fixed-fee firms decline pilot despite pricing; firms that sign don't onboard beyond 1–2 profiles; firms request source-database access rather than product-layer access (reverting to OEM shape); renewal <60% at 90 days.
- **Kill:** <5 consultant seats paid by month 6 across 3+ firm approaches → investigate product-fit vs pricing vs channel-rejection. Not fixable = pivot to direct-to-provider with self-serve as primary SKU.

### #7 Validation-sprint false positive
Enterprise SaaS pattern — polite "yes" from validation calls, no actual conversion. Particularly true of AU professional-services buyers.
- Early warning: any validation "yes" not accompanied by named budget owner + specific pilot-start timeline + named provider profile they'd use it on first.
- **Kill:** convert-to-paid <30% at 60 days from validation "yes" → require paid pilot ($500 for 30 days credited to first month) from every validation contact.

### #8 Sector financial distress collapses WTP
Practitioner voice: **~55% of providers made no profit in 2024–25; 14% planning to close; 50% considering exit within 3 years.** At some point providers cut every discretionary line, and compliance tooling is discretionary until a fine lands.
- Early warning: self-serve churn >8%/month within first 6 months (SMB SaaS benchmark 3–5%); free-tier-to-paid conversion <2%; consultant seats renew but reduce active profiles per seat.
- **Kill:** self-serve churn >10%/month sustained across 3 months = price above WTP → drop to $79/mo tier (halving revenue) or kill self-serve entirely.

### #9 Determinate slice IS the free-guidance slice
The clauses easiest to extract deterministically may be exactly the ones the Commission already summarises free.
- Early warning: customer discovery reveals providers already use Commission fact sheets and can't articulate what they'd additionally pay for; pilot users spend session on clause text (freely available) not the value-add layer.
- **Kill:** <30% of paid-user session time on the value-add layer (amendments, filtering, per-profile registers) → reprice to reflect the product is *workflow* not *content*, or partner with the Commission to be their delivery layer.

### #10 OEM vendors decide to build in-house
$2–5k/mo × 12 = $24–60k/yr to license vs 6–8 engineer-weeks (~$40–80k) to build. Payback in year 1.
- Early warning: OEM pilot conversations focus on data-model questions (reverse-engineering, not integrating); vendors request longer sandbox with fewer restrictions; vendors decline back-to-back indemnity.
- **Kill:** ≥3 of 5 named vendors decline within 6 months → pivot OEM value from "content" to "content-plus-ops-plus-legal-review-attestation" (insurance-shaped SLA on freshness). Requires founder PI insurance and shifts risk posture materially — links back to #1.

### #11 ACIA responds by adding clause-provenance to Quality Portal within 6 months
Since ACIA Quality Portal IS BNG SPP white-labelled, this is really the BNG SPP roadmap question. Adding clause citations to BNG's existing self-assessment framework is a content-annotation project — months, not years.
- Early warning: BNG SPP release notes reference "clause"/"provision"/"source reference"; new "Standards Library" or "Change Log" surface in the portal; consultant seat pilots include firms whose provider clients are ACIA/NDS/ATCA/SHS members.
- **Kill:** if BNG ships clause-provenance in Quality Portal *before* 30 consultant seats paid, direct-consultant differentiation weakens — refocus on the SKUs BNG doesn't have (OEM to non-competing vendors; self-serve for unregistered providers BNG doesn't sell to). If BNG additionally opens the portal to non-members within the same window, exit the consultant channel and repivot to OEM-only.

### #12 Director demand routes to D&O insurance not tooling
The first-instinct AU director protection is D&O insurance, not compliance tooling. If AU D&O carriers write NDIS-specific policies, directors get psychological safety through premium payment, not through Rules Engine.
- Early warning: any AU D&O carrier announces NDIS-director-specific policy; director-level inbounds ask "will this reduce my premium?" not "will this reduce my risk?"
- **Kill:** if Board SKU checkpoint (month 12) shows director inbounds are premium-driven → pivot Board SKU to a **carrier partnership** — sell to underwriters as risk-underwriting input, not to directors as risk-reduction tool. Per-policy fee replaces per-board subscription; revenue model changes materially.

### Cross-cutting red-team observations

- **Highest severity × likelihood: #1 (maintenance SLA) + #2 (incumbent provenance)** — both attack the moat directly. Both need named mitigation owners and monthly review.
- **#4, #9, #11 cluster around "the free/existing tier is closer to your product than assumed"** — pre-launch validation task: buy 3 hours of a Commission-savvy consultant's time to walk through Commission-published free resources and rate how much of Tier A is already covered by fact sheets. If >50%, revalue the corpus.
- **#6, #7, #10 cluster around "the buyer isn't who you think it is"** — mitigation is paid pilots with named-person budget owners, not free trials with polite yes-sayers.
- **Practice Standards 2.0 NOT SCHEDULED + graduated-registration Rules NOT YET MADE means the corpus is thinner than the marketing story requires.** If either scope reduction persists past 24 months, revenue ceiling drops below the perpetual TAM ceiling estimated in Modules 1–5.

**Three most consequential decisions to revisit at the month-6 checkpoint:**
1. OEM licensees actually pay rather than build (#10)
2. BNG SPP or Audit Pilot ships competing provenance (#2, #11)
3. Solo-founder maintenance model survives amendment cadence (#1)

**If any TWO of these three go against the founder inside 12 months, the perpetual-corpus thesis needs REPLACEMENT rather than iteration.**

---

## Practitioner voice — what the field actually says

Reach was constrained (proxy blocked Reddit, Facebook, Trustpilot, Crikey, Parliament PDFs); quotes are search-snippet-level. Founder should re-run from home network to capture verbatim. The highest-signal findings still change the plan in three places:

### The killer numbers

- **"14 per cent of NDIS businesses are already planning to close their doors and a further 50 per cent of providers are actively considering exiting the sector within the next three years. 55 per cent of providers made no profit in 2024–25."** (ShiftCare, 2026)
- "Administrative burden consuming 25 to 35% of operational time." (Vertex360, 2026)
- **"Over 60% of small-to-medium NDIS providers are still using a combination of spreadsheets, standalone rostering apps, and manual billing processes."** (Feb 2026 sector survey via CareVision)

### The consultant-trust story

- **Crikey, 21 April 2026, anonymous 15+-year NDIS quality auditor:** "The process of auditing NDIS providers is embedded with potential conflicts of interest … while the focus is on providers rorting the NDIS, the process of auditing those providers is embedded with potential conflicts of interest."
- **JASANZ enforcement, December 2025:** JPS Audit Specialists lost accreditation for "promoting an NDIS consultancy business to providers it was auditing" — conduct that "undermined impartiality and breached the standards expected of AQAs." (Global Compliance Certification acquired JPS's book.)
- **Consultant blogs:** "Interpretation of standards varies wildly between auditors, between AQAs, and even within the same auditing firms."
- **Avaana Trustpilot:** "Beware before paying this company any money — quick to take it then don't do any work." (One high-volume consultant name with visible trust damage — verify individual reviews before quoting.)

### The personal-liability story (new since April 2026)

- **Mondaq legal analysis:** "Criminal exposure applies to individuals, not merely corporate entities, with a sole trader operating an unregistered SIL service after 1 July 2026 personally exposed to criminal prosecution with strict liability."
- **MinterEllison:** "Civil penalties up to $3.64 million per contravention, new criminal offences for unregistered providers, expanded enforcement powers … banning orders **expanded to cover auditors, consultants, and facilitators.**"

### Five direct implications

1. **Do not price per-user or per-participant.** The two most-named incumbent grievances are per-seat scaling (ShiftCare $8/user/mo) and per-participant scaling (Brevity $6.49/client/mo). Flat or tiered-by-provider-size is a positioning wedge on its own.
2. **Lead with the "independent from consultants" story, not with features.** Copy angle: **"The rulebook, not the consultant."** The Crikey insider + JPS revocation + widespread auditor-interpretation-inconsistency form a coherent narrative that a tool sitting outside the consultant/audit supply chain solves.
3. **Time the entire 2026 GTM around the July → October SIL window.** Peak marketing: June (pre-1-July anxiety), September (pre-1-October registration deadline), and the 18-month mark after each cohort for mid-term audit re-scramble. A one-time "SIL Registration Sprint" pricing pack doubles as a lead magnet.
4. **Own the director-personal-liability lever.** This is new since April 2026 and not fully priced into buyer psychology yet. A single landing page for "sole-trader / director" explaining the new personal criminal exposure and showing how the product creates the audit trail that discharges the duty of care will convert.
5. **The buying committee is smaller than aged-care but the pain is more personal.** At small/medium providers the buyer is the director/owner-operator AND the quality manager (often the same person). Sell to that composite persona. Enterprise sales motion is a trap in this segment; free trial + heavy self-serve is the natural motion.

### Five assumption flips vs Modules 1–5

- **A. Consultants themselves now face banning orders under the Integrity Act.** Modules 1–5 treated consultants as the buyer's most trusted channel partner. That is shifting. A tool consultants *use with clients* (rather than instead-of) reduces the consultant's own personal-liability exposure.
- **B. The 55% no-profit number breaks the "discretionary IT spend" assumption.** Positioning must be *"pays for itself vs the cost you're already paying"* (consultant fee, staff turnover, audit rework), not *"productivity upgrade."*
- **C. Auditor capacity is materially constrained** — wait times are stretching from 6–9 months to 9–12. The unmet job is "get in the queue with your evidence pack ready", not "prepare after you've booked an audit."
- **D. Reddit and Facebook matter less than assumed; LinkedIn is where practitioner voice actually lives.** Any Reddit/FB seeding budget is better spent on LinkedIn thought-leadership + Team-DSC-adjacent syndication.
- **E. The consultant category has visible public trust damage** on Trustpilot (Avaana quotes above). Room to be "the anti-registration-consultant" in copy.

---

## The 5 questions only buyer conversations can settle

1. **Do 2 of 5 named OEM vendors sign a paid pilot LOI at $2k/mo within 30 days of first pitch?** (Tests: whether "content ops" is a buy-versus-build value proposition or whether SaaS vendors will fork the concept.)
2. **Does an anchor fixed-fee consultant firm (Provider+, Provider360, Avaana, EnableUs, or HCPA) commit to a founding-member seat at $199/mo with intent to onboard 20+ profiles?** (Tests: whether margin-expansion economics beat behavioural resistance to "another vendor in the room.")
3. **Under demo conditions, what proportion of a paid-user's session time is spent on the value-add layer — amendment diffs, per-profile filtering, evidence exports — versus raw clause reading?** (Tests: is the monetisable surface *content* or *workflow*, and therefore is $299 or $79 the natural anchor?)
4. **Are unsolicited director-level enquiries premium-recognition-driven ("will this lower my D&O premium?") or risk-reduction-driven ("will this reduce my personal exposure?")?** (Tests: whether the Board SKU is a subscription product or a carrier-partnership product.)
5. **After 4 months of trust-artifact promotion + 3 podcast episodes, what is inbound trial signup conversion?** (Tests: whether the free-artifact-plus-content GTM produces the SEO surface the model assumes, or whether direct outreach must carry 100% of top-of-funnel.)

---

## THE VERDICT

**GO on NDIS, sequenced as OEM-lead + consultant-parallel, self-serve conditional at month 3–6, Aged Care as SKU #2 from month 9–12. Odds of first paying revenue inside 9 months: ~65%.**

The base case at 24 months is $1.13M ARR — a strong solo enterprise, not a venture outcome. The optimistic case ($2.75M) requires the Boards SKU or corpus expansion to break through the perpetual TAM ceiling.

**The single biggest positive update since Modules 1–5:** BNG SPP is one platform underneath ACIA / NDS / ATCA / SHS, not four competitors. That makes the peak-body channel a **single OEM sales conversation, not a distribution war** — the founder's fastest route through the whole peak-body layer is to sell TO BNG rather than around them.

**The single biggest negative update:** the practitioner voice reveals a sector where **~55% of providers made no profit in 2024–25**, which forces the entire pitch to reframe from "productivity upgrade" to "pays for itself vs the cost you're already paying." Provider self-serve at $149/mo may be above the pain threshold for the distressed segment; a $79/mo fallback tier is a required backup.

**Kill switches (any two triggering inside 12 months = replace the thesis, not iterate):**
1. OEM vendors decide to build in-house (≥3 of 5 decline within 6 months)
2. BNG SPP, Audit Pilot, or FormaOS ships clause-provenance in a major release before you have 2 signed OEM licensees or 30 consultant seats paid
3. A single missed amendment is discovered by a customer AND survives >5 business days undetected

**What flips the verdict positive → aggressive:** Aged Care Rules 2025 personal-liability provisions producing the first prosecuted case with named director exposure inside 12 months, combined with a signed OEM licensee. That combination unlocks the Board SKU and the cross-sector "one rules engine, two regulators" pitch, and takes the 24-month ARR ceiling from $1.13M to $2.5–3M without requiring any new corpus work beyond the planned Aged Care extension.

---

## Honesty ledger — session limits

- Every AU government host (`legislation.gov.au`, `ndiscommission.gov.au`, `ndis.gov.au`, `health.gov.au`, `aph.gov.au`, `oia.pmc.gov.au`, `austlii.edu.au`) returned 403 to the research proxy in this session. F-numbers, dates, and instrument identifiers verified via search-index snippets and mirrored secondary sources (Team DSC, ClinicComply, MinterEllison, Gilbert+Tobin, Mondaq, APO, ANAO, IBISWorld). Founder must re-fetch each F-number and each commencement date on a browser before locking any build.
- Reddit, Facebook, Trustpilot, Crikey, LinkedIn post/comment content — all blocked (403) or non-indexed. Practitioner voice is search-snippet-level, not verbatim. Founder should re-run from home network + read the Crikey April 21 2026 insider piece + open the ~10 named NSW Parliament submissions from actual providers (Regal Home Health, Macarthur Disability Services, The Ella Centre, etc.) directly.
- The Pricing Schedule 2026-27 copyright notice was NOT verified this session — search snippets returned conflicting reads (CC BY-NC 4.0 vs CC BY-NC-ND). Founder must open the current PDF and read the notice verbatim before deciding architecture (pointer-only vs paraphrase). If ND, paraphrase-plus-link is blocked and only fact-level storage remains lawful.
- Provider count by registration group — no publicly published aggregate table; dataresearch.ndis.gov.au CSV required (blocked in session).
- Exact AQA count Aug 2026 — Commission's live *Find an Auditor* page (blocked); best evidence is 13–15 down from ~17 pre-2026 (QIP and Citation Certification exits confirmed via secondary).
- OIA Supplementary Analysis 2026 headline provider count for the July 2027 cohort — PDF blocked; inferred range 10–20k businesses from IBISWorld enterprise count and NDIA payment-category splits.
- ACIA membership size — not publicly published; the "route-around vs sell-to-BNG" tradeoff would be sharper with a real member-count anchor.
- The Federal Register RSS/Atom feed URL — not confirmed; amendment-monitoring loop may need to fall back to daily "what's new" HTML scraping (~<20 new items/day AU-wide, filterable).
- FormaOS, ClinicComply, Smart Compliance Systems, Audit Pilot, Sky Staff, EnableUs, Provider+ CEO surname, NDS 2026 membership dues — named-executive/pricing detail unverified.
- All revenue math is [INFERENCE] — there are no comparable-product benchmarks in this niche. Base-case penetration assumptions are aggressive (43–87% of consultant TAM at 24 months) and depend on 3–4 anchor firms turning into evangelists.
