# Where Else Does a Provenance-Verified Rules Engine Win? — Phase 0 + 1 Screen

**Status:** Phase 0 (long-list expansion) and Phase 1 (fit test + underserved screen + ranking + top-two pick + buyer-conflict checks) COMPLETE. **Stopped for owner review before Phase 2 deep dives**, per agreed checkpoint discipline.

**Date:** 2026-08-04. **Method:** six parallel research passes (~200 web searches/fetches total) across 21 candidate domains in AU/NZ/UK/US/CA. Every material claim carries a source link or an explicit [INFERENCE]/[UNVERIFIED] tag; absence claims state what was searched. An honesty ledger of unverified items is at the end.

**Scope exclusion honoured:** property, planning, zoning, construction approval and anything adjacent were excluded by definition. WHS construction-site codes were treated as out; general workplace chemical compliance as in.

---

## 0. Ranking weights applied (from the code-level flexibility audit)

The engine + playbook port cleanly (~3–6 person-weeks of clean-room verification-infrastructure rebuild for a text-rules domain); the corpus does not. **Time-to-revenue in any new domain is dominated by the corpus-building grind, not engineering.** The ranking below therefore weights, above raw market attractiveness:

1. **F1 — document accessibility and legal reusability** (a copyright wall is a hard disqualifier, not a discount),
2. **F2 — amendment cadence** (structural, not a one-off reform spike),
3. **Small self-contained starting corpus** — can a first sellable slice exist inside ~8–12 person-weeks of extraction, and
4. **Text-only structure** — every shortlisted domain is text-only, i.e. structurally simpler than the origin domain (no spatial/geospatial subsystem needed).

---

## 1. Phase 0 — Long-list and additions

Seed list (14 domains) screened as given. **Seven domains were added** after quick F1–F5 sniff tests:

| Added domain | Why added |
|---|---|
| **Customs tariff classification & duty rules** | Extreme verified amendment velocity (32 US HTS revisions in 2025), open machine-readable corpus with an official revision archive, and a named paid bridge (customs brokers) that is itself drowning |
| **US telehealth & state healthcare practice rules** | Famously high state-by-state churn, criminal-grade error costs (Done Global executives imprisoned 2026), public-domain corpus |
| **US state privacy laws** | ~20 state statutes each independently amended — a textbook currency problem with public-domain sources |
| **Food labelling (FSANZ-first)** | The corpus is Commonwealth legislative-instrument text — the exact document class the founder's engine already extracts — with a counted ~10 amendments/year |
| **Childcare / early-education compliance (NQF/EYFS/US state licensing)** | Determinate ratios/qualifications/timeframes + a live five-wave AU reform (2025–26) |
| **Aged care / NDIS provider compliance** | AU reform wave (Aged Care Act 2024, NDIS registration reform) with the best-documented consultant fee pool found anywhere in this scan |
| **UK NMW/holiday-pay/statutory payments** (split out from "payroll rules UK") | Scoped separately from IR35 (which fails determinacy) because the scoped set passes all five fit criteria on the cleanest legal licence found (OGL) |

---

## 2. Fit-test scorecard — all 21 domains

Scores are strict 0/1 per the brief. "Grade" = underserved-evidence grade (A strong unmet demand / B moderate / C weak or served). Full per-domain evidence is in §3 and the six underlying screening reports.

| # | Domain | F1 | F2 | F3 | F4 | F5 | Fit | Grade | One-line disposition |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **US state privacy laws** | 1 | 1 | 1 | 1 | 1 | 5/5 | **A−** | **TOP TWO** |
| 2 | **Food labelling (FSANZ-first)** | 1 | 1 | 1 | 1 | 1 | 5/5 | **A− (AU/NZ verification slice)** | **TOP TWO** |
| 3 | US telehealth / state practice rules | 1 | 1 | 1 | 1 | 1 | 5/5 | A− | Runner-up (see §6) |
| 4 | Customs tariff duty-rules layer | 1 | 1 | 1* | 1 | 1 | 4/5 | A− (duty layer only) | Runner-up (see §6) |
| 5 | Aged care / NDIS compliance | 1 | 1 | 1 | 1 | 1 | ~5/5 | A (timing asterisk) | Runner-up — rulebook mid-rewrite |
| 6 | Court practice directions — AU | 1 | 1 | 1 | 1 | 1 | 5/5 | A− (AU only; US SERVED) | Fallback niche (small TAM) |
| 7 | AU modern awards (retrospective wedge) | 1 | 1 | 1* | 1 | 1 | 5/5 | B (A− wedge) | Strong but contested-core caveat |
| 8 | Immigration rules (UK/AU wedge) | 1 | 1 | 1 | 1 | 1 | 5/5 | B+ | Strong; AU policy-layer licence unresolved |
| 9 | UK NMW / holiday pay / statutory | 1 | 1 | 1* | 1 | 1 | 5/5 | B+ | Best as second market for an AU payroll product |
| 10 | Childcare / early education (NQF) | 1 | 1 | 1 | 1 | 1 | 4.5/5 | B+ | Reform-spike cadence; fee pool unverified |
| 11 | Product compliance e-commerce | 0 | 1 | 1 | 1 | 1 | 3.5/5 | B | A-grade demand, C-grade corpus rights (ASTM/EN copyright) |
| 12 | Regulated advertising codes | 1 | 1 | 1* | 1 | 1 | 4.5/5 | C+ / B− | Review layer crowded & funded; only a narrow TGA reference wedge |
| 13 | Sanctions / export controls SME | 1 | 1 | 0 | 1 | 1 | 4/5 | B− | Determinate part saturated; open part (ECCN) non-determinate + worst liability |
| 14 | US multi-state payroll | 1 | 1 | 1* | 1 | 1 | 5/5 | C | SERVED — Symmetry, GovDocs, Mosey→Gusto, SixFifty |
| 15 | Drug formulary / scheduling | 1 | 1 | 1 | 1 | 1 | 5/5 | C core / B− wedge | SERVED — FDB/Medi-Span/MIMS/MMIT are healthy provenance engines |
| 16 | Court practice directions — US | 1 | 1 | 1 | 1 | 1 | 5/5 | C | SERVED — CalendarRules (Clio) + LawToolBox |
| 17 | Welfare eligibility rules-as-code | 1 | 1 | 1 | 1 | 1 | 4/5 | C | SERVED by free/philanthropic (PolicyEngine, OpenFisca) |
| 18 | Charity fundraising licensing | 1 | 0 | 1 | 1 | 1 | 4/5 | C | SERVED — Harbor Compliance + Labyrinth (>50% share); low velocity |
| 19 | SDS / chemical & WHS | 1 | 0 | 1 | 0 | 1 | 3/5 | C | SERVED (Chemwatch) + near-static rulebook |
| 20 | Grants & incentive eligibility | 1 | 1 | 0 | 1 | 1 | 3/5 | B mkt / D fit | Corpus treadmill; discretionary core |
| 21 | Clinical guideline currency | 0 | 1 | 0 | 0 | 1 | 2/5 | — | FAILS — NICE no-derivatives licence + judgment-laden content |
| 22 | Climate / sustainability reporting | 0 | 1 | 1* | 1 | 1 | 3/5 | C | FAILS — IFRS Foundation copyright explicitly bars software embedding; demand contracting (CSRD scope −90%) |

\* F3 asterisks: score of 1 applies to a defined determinate slice only (detailed in §3); the domain's headline question is judgment-laden and must stay out of scope.

---

## 3. Phase 1 — Underserved screen for domains passing the fit test

Main table per the brief: domain × (F1–F5, underserved grade, buyer + price anchor, amendment cadence, named incumbents & their gap). Ordered by weighted rank. Enforcement/scandal evidence is inline.

| Domain | Cadence (counted) | Live-gap evidence (<24 mo) | Buyer + price anchor | Named incumbents → the gap |
|---|---|---|---|---|
| **US state privacy** | 20 states with comprehensive laws in effect 2026; **8 of the existing states amended their laws in the 2025 session alone** (CO, CT, KY, MT, OR, TX, UT, VA); IN/KY/RI effective 1 Jan 2026, CT/AR/UT changes Jul 2026, CA data-broker rules Aug 2026; plus health/biometric/children's strata | CCPA record fine broken 3× in 15 months: GM **$12.75M** (May 2026), Disney $2.75M (Feb 2026), Healthline $1.55M (Jul 2025), Tractor Supply $1.35M (Sep 2025); Texas AG: Google **$1.375B**, Meta **$1.4B**; statutory $2,663–$7,988 *per violation*; 2026 dubbed "the year state enforcement takes center stage" | Fractional/consulting DPOs and privacy officers, privacy counsel at small/mid firms, GC at SMB SaaS. Anchor: counsel $225–300/hr floor; SMB compliance projects $5–15k; OneTrust min ~$10k/yr | OneTrust (b: workflow, killed its entry tier — mid-market complaint pattern "paying for enterprise complexity they don't need"; owns DataGuidance = lawyer-written prose); TrustArc/Nymity (closest: 1,796 rules/130 laws, but enterprise, opaque, no exposed clause citation or effective-dating); Osano $199/mo (operational consent/DSAR, not a law reference); IAPP/law-firm trackers (a: static charts). **Category (c) — a clause-cited, effective-dated, queryable answer layer — is empty between free static charts and $10k workflow suites** |
| **Food labelling (FSANZ)** | Counted from gazettes: **~26 numbered Code amendments in ~2.5 yrs ≈ 10/yr** + continuous notification circulars; PEAL allergen transition (mandatory 25 Feb 2024 → stock-in-trade end 25 Feb 2026) is the archetypal date-effective rule flip; FDA front-of-package rule pending mid-2026 | FSANZ: **92 recalls in 2025; undeclared allergens = 35 (38%), the leading cause**; 197 allergen recalls 2021–25 driven by packaging errors and failure to communicate ingredient changes; UK: restaurant fined £43,816 after allergen hospitalisation (2025); allergen prosecutions "soaring" (Lexology) | QA Manager / Regulatory & Technical Manager at SME food manufacturers; food-labelling consultants (leverage channel); private-label managers. Anchor: consultants $90–150/hr, fixed-fee label reviews (hundreds of $/SKU); Ashbury built a global business on human line-by-line label verification ("500,000 products approved") | FoodWorks/Xyris (c — but for the *generation* slice only: recipe → compliant NIP/allergen statement); Nutritics, Food Label Maker (shallower generation); FoodDocs, Safefood 360 (b: HACCP/workflow); FSANZ circulars (a). **The verification-with-provenance slice — "is this existing label compliant today, cite the clause, and alert me when an amendment touches my SKUs" — is done only by humans at consultant prices. No software found doing clause-cited label audit + portfolio-level amendment monitoring** |
| US telehealth rules | CCHP re-verifies all 54 jurisdictions 3×/yr; DEA telemedicine flexibility extended a **fourth** time (Dec 2025 → expires Dec 2026) = institutionalised annual cliff; Oregon SB 951 (Jun 2025) rewrote CPOM with staged deadlines Jan 2026/Jan 2029; parallel PE/CPOM bills in multiple states | **Done Global founder convicted and imprisoned 2026** ($100M Adderall scheme); Cerebral $3.6M NPA (Nov 2024) + $7M FTC; Zealthy receivership (2026); DOJ formally expanded telehealth enforcement (Aug 2024) | Head of Compliance / GC / VP Clinical Ops at telehealth cos and MSO structures. Anchor: BigLaw health counsel $400+/hr [INFERENCE]; Manatt on Health premium subscription proves WTP; entry $500–2,500/mo [INFERENCE] | Foley 50-state PDFs (a — editions 2019/2021/2024); **CCHP Policy Finder (free, grant-funded, no API, no diffs, no effective-date schema, 3×/yr)**; Medallion/Certify (b — licensure *ops*, not practice rules); Manatt tracker (a, premium). **No telehealth-specific provenance rules engine found** |
| Customs duty-rules | **32 US HTS revisions in 2025** (+10 by Jun 2026, USITC revision archive); IEEPA/§232 changes effective with hours of notice; HS 2028 cycle began Aug 2025 | **Ceratizit $54.4M FCA settlement (Dec 2025)** — largest customs FCA ever, whistleblower took $9.75M; DOJ/DHS Trade Fraud Task Force (Aug 2025); FCA recoveries $6.8B FY2025 with customs a named growth lane | Small/mid customs brokerages, import compliance managers at SME importers. Anchor: $50–200/classification, $100–500/entry, $150–350/hr. **The human bridge is a buyer, not an adversary**: NCBFAA members — "CBP systems and broker databases haven't kept up… exposing brokers and their customers to fines or overpaying" | Classification-AI knife-fight (Avalara, Zonos-free, Gaia Dynamics — already markets CROSS citations); Descartes CustomsInfo/3CE, ONESOURCE, SAP GTS (enterprise). **The duty-rules/effective-dating layer — "the complete lawful rate stack for code/origin/date, each layer cited" — has no visible SME product** |
| Aged care / NDIS | Aged Care Act 2024 commenced 1 Nov 2025 (Rules 2025 = a 666-page instrument, released in waves); NDIS SIL mandatory registration 1 Jul 2026 (applications due 1 Oct 2026); Integrity Bill (Nov 2025) lifts max penalties $412,500 → >$15M; Practice Standards 2.0 mid-reform | 34 banning orders in one quarter (up 75%); first-ever NDIS civil-penalty proceedings (2025); exposure $330k individual / $1.6M corporate per contravention; providers report the transition "far more resource-intensive than expected" (300+ leader survey) | Owner-operators & Quality/Compliance Managers of SME providers; NDIS registration consultants (leverage channel); boards (now personally accountable). Anchor: **registration consultants $2,000–$10,000 per engagement (best-documented fee pool in this scan)**; audits $900–$12,000/3-yr cycle | BNG SPP (closest — self-assessment portals with peak-body distribution, but not clause-cited/effective-dated/diffed); ShiftCare/Brevity (b, editorial content); consultants (human). No category (c) found — **but both regimes are mid-rewrite (see §6)** |
| Court rules — AU | UK PD updates 163rd→171st inside ~6 months (proxy); NSW SC Gen 23 AI practice note issued Nov 2024 and *revised within 3 months*; 9 AU jurisdictions × rules + practice notes | Missed deadline ≈ dismissal + malpractice claim; PI insurers already price the error | Litigation partners / legal-ops / practice managers at small-mid AU litigation firms. Anchor: LawToolBox US$49/user/mo (US price); one dismissed claim = six-figure PI event | US is SERVED (CalendarRules — Clio-owned; LawToolBox). **In AU, Clio's court-rules support covers "a limited set of conveyancing rule sets" only; no AU rules-based litigation calendaring engine found** |
| AU modern awards | Annual Wage Review re-rates ~120 awards every 1 July; ~50 awards varied Jan 2025; 155 awards varied for delegates' rights, then 9 determinations quashed by the Full Federal Court (Dec 2025) | Criminal wage theft since 1 Jan 2025 (10 yrs / max(3× underpayment, $7.825M)); **Woolworths/Coles remediation >$1B (Sept 2025)**; Sushi Bay $15.3M (FWO's highest ever); FWO recovered $358M FY24-25 | Payroll managers/CFOs mid-market; accountants & bookkeepers as channel. Anchor: employment lawyers $300–700/hr; audit firms $45–85/hr for weeks-long engagements | Prospective payroll-time interpretation SERVED (Tanda/Deputy/Employment Hero, ~30 managed awards); retrospective audit = enterprise-only (Yellow Canary — interpretation outsourced to law firms; PaidRight → Wrkr Feb 2026). **Gap: audit-grade retrospective verification with clause provenance below the enterprise tier.** Caveat: the FWC's MAPD API hands everyone the rates data; the contested parts (classification, set-off) are exactly what a deterministic engine must refuse |
| Immigration (UK/AU) | UK: ~5–6 Statements of Changes/yr (9 instruments Sep 2024–Mar 2026; historically 548pp of changes in one year against 1,133pp of Rules); USCIS ≥26 policy alerts in 2025; AU CSOL annual review + OSCA reclassification | UK IAA can fine advisers up to £15,000 + order repayment to £250,000 (2025, covers unregulated actors); 5 AU agents sanctioned since Jun 2025; one refusal burns A$9,365–11,710 in non-refundable fees | RMAs (AU), IAA advisers (UK), RCICs (CA). Anchor: **OMARA accepts a LEGENDcom subscription (~A$730/yr) as satisfying the professional-library obligation — the regulator literally mandates paying for rule currency**; agent fees A$2,000–15,000/matter | LEGENDcom (official AU reference library — no criteria extraction, no caseload diffing, no API); Migration Manager/Docketwise (b: workflow/forms); Free Movement/EIN (a). **No true (c) for UK or CA at all.** Caveat: AU policy layer (PAM3) is distributed only via the government's own paid DB — republication rights unresolved |
| UK NMW/holiday | NMW rates annual, but holiday-pay regime rewritten Jan/Apr 2024; Employment Rights Act rollout 2025–27; Fair Work Agency (single enforcer) launched Apr 2026 | Naming rounds: 518 employers/£7.4M (May 2025) + 491 employers/>£10M fines (Oct 2025); penalties 200% of arrears to £20k/worker; most named employers are technical breaches, not rogues | Payroll bureau owners (they run payroll for millions of UK SME employees); heads of payroll in retail/hospitality/care. Anchor: Big-4 NMW reviews (5–6 figures [INFERENCE]); Brightmine subs | Brightmine/Croner (a/b: content+alerts, 7,500+ customers); payroll engines embed calcs without provenance; only embryonic niche (c) tools. **Big-4 humans are doing engine work by hand — that's the gap.** Caveat: 1 rate change/yr weakens the currency pitch; costliest failures (worker categorisation) are the non-determinate part |
| Childcare (NQF) | Five dated NQF child-safety waves Sep 2025→Feb 2026; penalties up to 900% higher; National Worker Register live 27 Feb 2026; UK: new EYFS (Sep 2025) + new Ofsted framework (Nov 2025) | WA SAT penalties $30–33k (supervision/ratio breaches, 2025); NSW fines to $500k legislated; CCS funding suspension = business death [INFERENCE] | Approved providers / centre directors / multi-site compliance managers. Anchor: CCMS per-child spend + consultant A&R prep [fees UNVERIFIED] | 1Place/Xap/QikKids/brightwheel (b: checklists hand-authored, not derived from a provenance-tracked regulation DB). Caveats: reform spike, uniform national rulebook (a solo consultant *can* stay current), incumbents own the director's screen |

**Domains screened out with the honest "SERVED" verdict** (category (c) present and healthy): US multi-state payroll (Symmetry, GovDocs, Mosey→Gusto at 500k SMBs, SixFifty $75/mo); drug formulary core (FDB/Medi-Span/MIMS/MMIT); US court deadlines (CalendarRules/LawToolBox); welfare rules-as-code (PolicyEngine/OpenFisca — free and philanthropically funded); charity registration (Harbor+Labyrinth >50% share); SDS/chemicals (Chemwatch at enterprise, SDS Manager at $9.99/user/mo). **Domains screened out on structural failure:** clinical guidelines (NICE licence forbids restructuring recommendations; no stale-protocol liability case found); climate reporting (IFRS Foundation licence explicitly bars integration into software without a commercial licence, and CSRD scope was cut ~90% by the Omnibus — demand is being legislated away); sanctions classification (ECCN determination needs product-engineering facts no rules DB can hold); grants (corpus is a treadmill of one-off superseding guidelines — the stable amended corpus the engine needs never forms).

---

## 4. Ranking and the TOP TWO

Applying the §0 weights (corpus accessibility → cadence → small-start feasibility → then market attractiveness):

### #1 — US state privacy laws (grade A−, fit 5/5)

The strongest all-round candidate in the scan, and the one whose shape most exactly matches the engine:

- **Corpus:** ~20 state statutes + a handful of regulation sets, all public-domain (government-edicts doctrine). The smallest high-value corpus found — a fraction of the origin domain's 47k provisions. **Small start verified in principle:** ship 5–8 states (CA/CO/TX/CT/VA + the Jan 2026 cohort) or even just "the deltas from a CPRA baseline" and be useful on day one.
- **Cadence is structural, not a spike:** new states every year plus **8 amendments to existing laws in one session** — the currency problem regenerates annually by the nature of 50-state federalism.
- **Determinate slice is the painful part:** thresholds (35k–100k consumers, varies by state), cure periods and their sunsets, response deadlines, rights catalogs, notice content, DPA triggers, opt-out signal dates — exactly the variance practitioners complain about ("kaleidoscope… more dizzying every week" — IAPP).
- **Price umbrella is documented:** OneTrust killed its entry tier (min ~$10k); below it, only cookie-banner tools; the humans cost $225–300/hr. Empty category (c).
- **Enforcement trendline steepening:** record CCPA fine broken three times in 15 months; Texas AG in the billions.
- Main risks (steel-manned in §5): OneTrust bundling, lawyer-buyer dynamics, CPRA convergence, federal preemption tail-risk, and a US market with no home-market advantage.

### #2 — Food labelling, FSANZ-first (grade A− for the AU/NZ verification slice, fit 5/5)

The best *corpus-fit* and *founder-fit* candidate — chosen over three other A-grade runners-up specifically because of the §0 weighting:

- **The corpus is the same document class the founder already extracts.** The Food Standards Code is Commonwealth legislative-instrument text on the Federal Register of Legislation — same source system, same format, same amendment-gazette mechanics as the current product's corpus. Of all 21 domains this is the one where the corpus grind is most predictable, and it needs zero spatial machinery.
- **Cleanest F1 in the entire scan:** open legislation end-to-end; the paywalled bits (ISO/AOAC analytical methods) are peripheral to labelling logic.
- **Counted cadence:** ~10 numbered amendments/yr + circulars, with multi-year date-effective transitions (PEAL) that are precisely what effective-dating is for.
- **Small start verified:** the labelling standards (Standard 1.2.1–1.2.8 + associated schedules) are a self-contained slice of the Code — a first product ("clause-cited label verification + amendment-to-SKU alerts") doesn't need the other chapters.
- **The gap is the founder's exact shape:** the *generation* half of the market is served (FoodWorks); the *verification-with-provenance* half is done by humans at $90–150/hr up to Ashbury's global consultancy. Nobody found does clause-cited audit of existing labels with portfolio-level amendment monitoring.
- **Home-market trust sale** without depending on property-domain reputation, plus a consultant channel (sell leverage to the human bridge, not against it).
- Main risks: FoodWorks fast-follow; felt churn between PEAL-scale events may be quiet; recall causes are dominated by process errors the engine can't prevent (steel-manned in §5).

---

## 5. Buyer-conflict checks (top two)

### US state privacy
- **Whose paid expertise does it commoditize?** Outside privacy counsel's 50-state research ($225–300/hr+) and the know-how base of fractional DPOs/privacy consultants.
- **Do they gatekeep the sale?** Partially. SMB SaaS often asks its counsel what to rely on; fractional DPOs choose their own tooling. In-house teams that own OneTrust still pay counsel for "what does Montana's amendment change for us, cited" — that spend is the direct target.
- **Library-not-oracle version:** Yes, and it should be the lead. Sold *to* counsel and fractional DPOs as their research/evidence layer ("clause-cited, effective-dated, diff on every amendment — you sign the advice"), it avoids unauthorized-practice-of-law exposure, converts the threatened expert into the buyer, and matches how the analogous incumbents (SixFifty via Wilson Sonsini; Manatt on Health) are structured. The oracle version (answers direct to businesses) is a later, riskier layer.

### Food labelling (FSANZ)
- **Whose paid expertise does it commoditize?** Food regulatory consultants doing per-SKU label reviews at $90–150/hr, up to Ashbury/RSSL-class consultancies; also part of what FoodLegal-style subscription advisers sell.
- **Do they gatekeep the sale?** Moderately. SME QA managers can buy directly, but consultants are trusted advisers to exactly the SMEs that can't afford Ashbury; a consultant recommending against the tool can kill a deal.
- **Library-not-oracle version:** Yes — "audit 10× the SKUs at the same headcount, every finding clause-cited" sold to consultants as leverage is the safer wedge, with direct-to-QA-manager sales framed as *evidence generation* (findings + citations + effective dates), never "compliant/safe" verdicts. The founder's existing liability-language discipline transfers verbatim. Note the oracle boundary: label compliance conclusions edge toward regulated advice territory only weakly here (no licensed-profession monopoly equivalent to law), which makes food the lower-liability of the two.

---

## 6. Runners-up — what would promote them

- **US telehealth state rules (A−):** promoted if buyer-quality concerns dissipate (the pool includes distressed/deceased companies: Done, Cerebral, Zealthy) and the DEA Special Registration rule *doesn't* stabilise the biggest churn source in 2026. Free CCHP anchors the reference layer at $0; the sale must be machine-readability + diffs + effective-dating. Bigger corpus grind than privacy (54 jurisdictions × licensure/modality/prescribing/consent/CPOM/payer strata).
- **Customs duty-rules layer (A−):** the most engine-shaped gap found (rate stack per code/origin/date, each layer cited to the Federal Register, with the broker association itself testifying nobody's systems keep up) — but the extreme 2025–26 velocity is policy-driven and could mean-revert, the classification-AI knife-fight will confuse the category, and the market is US-only from an AU base. Promoted if tariff churn persists into 2027 and a broker design-partner materialises.
- **Aged care/NDIS (A demand):** the loudest current pain and best-documented consultant fees, with a dated forcing function (SIL registration applications due 1 Oct 2026). Held out of the top two for one reason: **both regimes are mid-rewrite** (Practice Standards 2.0, graduated registration 2027, Rules still landing in waves) — a provenance engine extracting from moving instruments re-does its corpus monthly and competes with free government transition guidance. Promoted the moment the rulebooks stabilise (~2027), at which point the founder's amendment-monitoring becomes the retention hook. A scoped obligations-and-deadlines product sold through registration consultants is a credible fast-revenue play *now* for a founder willing to ride the rewrite.
- **AU court practice directions (A− underserved, small TAM):** clean corpus, real gap (Clio's AU coverage is conveyancing-only), insurer-priced error cost — but a ~A$500k–2M ARR niche that is malpractice-adjacent. A good second product for whichever AU-facing base the founder builds, not a first bet.

---

## 7. Cross-cutting findings

1. **The provenance seat is occupied more often than the brief assumed.** Six of 21 domains have healthy category (c) incumbents (US payroll, formulary, US court rules, welfare, charity, SDS). The empty seats cluster where the corpus is fragmented across jurisdictions (privacy, telehealth, immigration) or where the incumbent monetises humans instead of software (food labelling, UK NMW, customs duty rules).
2. **Copyright is the most common hard disqualifier**, and it hides in the "operative layer": ISSB/IFRS (explicit software-integration ban), NICE (no-derivatives), ASTM/EN product standards, WCO Explanatory Notes, AU Therapeutic Guidelines, AANA/ABAC codes, AU immigration policy manuals. Every shortlisted domain runs on legislation or public records end-to-end.
3. **Spike vs structural churn matters.** Aged care/NDIS and childcare are reform spikes; privacy, food, customs, telehealth, immigration have churn generated structurally (federalism, annual gazette cycles, annual DEA cliffs). Subscriptions survive on structural churn.
4. **In every shortlisted domain the safe product is the same:** deterministic verification of everything downstream of a human-confirmed input (classification, worker category, HTS code, state footprint), clause-cited, effective-dated — sold as a library to the professional who signs the judgment. The oracle version is where the liability lives.

---

## 8. Honesty ledger — what this screen could not verify

- FWC MAPD API commercial-use terms (ToU page 403'd; verify with awards@fwc.gov.au) — affects the awards wedge only.
- PBS Schedule Data API licence text (403); LEGENDcom current price (only a 2016 A$730 figure); Labyrinth per-state fees (403).
- Exact BIS annual rule counts; exact NICE annual update counts; CMS Part D CMP dollar amounts (in linked CMS PDFs, fetch blocked); Done Global sentencing terms differ across outlets (6–8 yrs).
- Childcare A&R consultant fees; aged-care (non-NDIS) consultant fees; Big-4 NMW engagement fees; BigLaw health-regulatory hourly rates — all [INFERENCE] ranges.
- Verbatim practitioner forum quotes were found for privacy (IAPP "kaleidoscope"), customs (NCBFAA "the teacher's not there"), e-commerce (Etsy sellers abandoning the EU) and aged care (survey quotes), but **not** for immigration, UK payroll, or telehealth despite searching — regulator-documented complexity stood in for them there.
- Products named in the brief that could not be found at all: Kollaris/Odysseus (UK immigration), Sourcery (grants), "Simple Charity Registration", TelehealthDocs, Parallel (telehealth), Tariffy (details).
- Several cost benchmarks come from vendor content-marketing (flagged [CM] in the underlying reports).

---

## 9. Next step — awaiting review

Phase 2 (adversarial deep dives) is scoped and ready to run on the top two — **US state privacy laws** and **FSANZ food labelling** — covering: buyer maps with titles/budgets, library-vs-oracle offer design, corpus feasibility in person-weeks with cross-reference tracing, regulated-advice boundary analysis, pricing anchored to the human bridge, first-10-buyers GTM + free trust artifact, the competition counterfactual ("why hasn't FoodWorks/OneTrust built provenance?"), three revenue scenarios at months 6/12/24 with odds, and a 6+ failure-mode red team including the three mandated kill criteria (cadence lower than claimed / incumbent adds provenance in one release / no small starting corpus).

**Owner decisions requested before Phase 2:**
1. Confirm or amend the top two (the closest calls were privacy vs telehealth for the US slot, and food vs aged-care/NDIS for the AU slot — rationale in §4/§6).
2. Whether Phase 2 should also carry a "fast-revenue AU option" mini-dive on the NDIS obligations-and-deadlines wedge given the 1 Oct 2026 SIL deadline, at the cost of some depth on the main two.
