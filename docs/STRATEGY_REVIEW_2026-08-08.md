# Strategy review — plain English, 2026-08-08

prior-art-checked: swept `~/.claude/plans/` (all `*2026-08*`, INDEX.md), the memory directory,
`docs/`, and `origin/main`. Three documents written earlier today cover the *measurement* side
of this ground and are cited throughout rather than restated: `ce-verified-capability-statement-2026-08.md`,
`ce-product-status-ledger-2026-08.md`, `ce-product-assurance-position-2026-08.md`. This document
is the **conversation record and the strategic reasoning** — a different artefact. Where it and
those three disagree, **they win**; they were measured, this was discussed.

**What this is.** A record of a strategy conversation held on 8 August 2026, written in plain
language with no jargon, so it can be read later without the surrounding context. It covers what
the project actually contains, what the last fortnight found, what the competition is, what is
salvageable, and what was decided or left open.

**What this is not.** Not a measurement. Every figure here was read from a document or verified
during the conversation, and the source is named. Not pitch material. Not a plan of record.

---

## 0. Read this first — five things I said during the conversation that were wrong

Most of my figures came from the reliability retrospective dated 1 August. The capability
statement re-measured everything on 8 August. Where they differ, the newer measurement wins.

**1. "There is no automated checking. Nothing in the system is capable of failing."**
True on 1 August. **False now.** CI exists and is green on `main` — `.github/workflows/gates.yml`
and `main-red-alarm.yml`, running 3,925 Python tests and 1,034 frontend tests, plus a
schema-contract gate, a controls-provenance gate, a value-derivability check and a
fabricated-verdict check. This matters for the employment thread specifically: those gates are
live, not aspirational, and they are the strongest portfolio exhibits in the repository.

**2. "The DCP surface may be switched off in production."**
**Wrong.** `docs/CONFIGURATION.md` says the flag is unset in production; the capability statement
proved from the deployed JavaScript bundle that it is **on**, with 29 councils enabled. The
configuration document is the thing that is wrong. Separately, the structured-controls API
(`/api/dcp/structured-controls`) reads no environment flag at all and is publicly reachable with
no authentication.

**3. "The development-application data is a frozen extract."**
**Wrong.** Both feeds are live: **181,737** fast-track certificates and **62,016** development
applications, with 896 ingest runs in the last seven days and rows added today.

**4. Several counts were stale.** Controls are **1,071** not 1,069, across **16** control types
not 15. The "applies everywhere" tagging is **93.7% / 91.8%**, not 97.7% / 96.3%. Reproducible
versus traceable is **543 / 528**, not 534 / 535. Effective dates fell from 893 to **365** because
528 unsubstantiated ones were deliberately deleted — that is a repair, not decay.

**5. "The Site Report email capture fix has been open for nine days."**
It has since been **merged** — `af7982a8`, PR #852. It had been returning an HTTP 400 error on
100% of submissions since it shipped.

**One more, found the same day.** The largest table in the database is `nsw_cadastre_lots` at
**3,220,617** parcels, and it appears in none of the asset lists I was working from.

---

## 1. Three words used throughout

**LEP — Local Environmental Plan.** Each council's legally binding zoning document. What zone a
property is in, how tall you can build, how much floor area, minimum lot size.

**DCP — Development Control Plan.** The council's detailed rulebook underneath that. How far back
from the street, how much of the block you can cover, car spaces, landscaping, deep soil.

**SEPP — State Environmental Planning Policy.** A NSW state-wide rule that overrides council
rules. The one that made granny flats broadly allowed is a SEPP.

---

## 2. What the project actually contains

All figures from `ce-verified-capability-statement-2026-08.md`, measured live on 8 August.

### The big, genuinely valuable data

- **1,088,573 mapped shapes** across 25 layer types — biodiversity 394,243; bushfire 225,688;
  riparian 92,340; zoning 68,046; flood 42,572; minimum lot size 41,362; heritage 40,141;
  height 40,094; fire history 37,588; floor space 34,279; landslide 17,483; and fourteen more.
- **3,220,617 land parcels** — every lot in NSW with its legal identifier, shape and area.
- **3,126,418 lots pre-joined to their planning controls**, so "find me every lot over 600 m²
  that isn't heritage" is answerable at all.
- **181,737 fast-track approval certificates**, 128 councils, 2018 to today, 99.99% with
  coordinates.
- **62,016 development applications**, 128 councils, all with a determination date.

**Where all of it stops.** It is a snapshot, not a feed. Most map layers were last synced between
April and July 2026 — **two to four months old, with no automatic refresh**. Coverage is uneven:
landslide covers 6 councils, floor space 65, height 75, flood 72. Only zoning, lot size and
heritage approach full state coverage. Bushfire and fire history carry **no currency date at all**
— their age is unknown, not merely old.

### The one genuinely special thing

**`dcp_setback_controls` — 1,071 numbers, 30 council labels, 16 control types.**

Council rulebooks are long PDFs of prose. Buried in them are the numbers that decide what you can
build. This table holds 1,071 of those pulled out **as numbers**, each stored with the exact
sentence it came from and the clause reference. That is what a document-search or "AI chat over
the PDF" product structurally cannot do: it returns *front setback = 4.5 m, clause 3.2.1*, not
*"here is a paragraph that mentions setbacks."*

Every one of the 1,071 has the verbatim sentence, the clause reference and the plan version.

| What is missing | Filled | Of 1,071 |
|---|---|---|
| `last_verified_at` | 974 | 90.9% |
| `effective_date` | **365** | **34.1%** |
| `effective_date_basis` | **0** | **0%** |
| `pdf_page` | 193 | 18.0% |
| `provision_id` — the machine-followable link | **42** | **3.9%** |

**Where it stops.**
- 1,071 rows over 30 labels is about **36 controls per council**. That is thin, and it is the
  true size of the defensible surface.
- **528 of 1,071 (49%) have no committed recipe.** Re-checking them means a human reading a PDF.
- **For 706 controls we cannot state when the control came into force.**
- The field recording *how a row was made* does not mean what it says and must never be quoted:
  179 rows labelled "manual" are regenerated by a script, and 323 labelled as pipeline output
  have no committed source.

### The big text corpus is not the advantage

55,696 clauses; 19,957 live and actionable; 15 councils named plus 7,268 with no council (mostly
legitimate state-wide instruments).

- **Only 2,069 of 19,957 (10.4%) carry a number.** The arithmetic surface is roughly 2,000
  clauses plus the 1,071 controls — **not 55,696**.
- **93.7% are tagged "applies to every zone"** and 91.8% "every development type." Those two
  filters barely narrow anything.
- **That tag is unattributable** — the tagging code writes the identical value whether a rule
  said "everywhere" or nothing matched at all. A falsifiable probe found genuine mis-tagging at
  only **0.50%**, so the corpus is not *wrong*, it is *not discriminating*.
- **Page images exist for 6.8% of served rows.** "Every rule cited to its page" is true for the
  numeric controls and Inner West, not for the corpus.

**The honest position:** filtered by council, layer and topic, the corpus is a well-organised
retrieval body. A competent document-search system with good chunking reaches a similar place.
**The corpus is not the differentiator. The 1,071-row controls table is.**

### Council coverage — never quote one number

| Claim | Figure |
|---|---|
| Numeric DCP controls cited to clause | **25** |
| Councils with extracted DCP text | **15** |
| Full DCP browsing, page images, precincts | **3** (Ashfield, Leichhardt, Marrickville) |
| Permitted uses by zone | **26** |
| Zoning, height, hazard overlays | **128** (snapshot 2–4 months old) |
| Transaction records (certificates and applications) | **128** |

The outreach copy's "24 Sydney councils" is wrong; the live endpoint returns 25. And that endpoint
**omits the project's three deepest councils** because they carry a parent-council label — 99
current controls and the only full integrations are invisible to the answer the product itself
gives to "which councils do you cover."

---

## 3. Why nothing caught the mistakes

**Until 1 August there was no automated checking anywhere.** Every gate was a script on one
machine that had to be switched on by hand, once per copy of the code, and there were many copies.

**The proof, in one fact.** A live page had been querying two tables that had been renamed. It
could not have worked for any address. **Every quality check stayed green** — 3,207 Python tests,
about 900 frontend tests, type checking, a bracket linter and a liability-language scanner —
because database table names sit inside ordinary text strings that none of those tools can see.

**Test volume is not protection.** On one file, 844 tests were run against deliberately broken
code and caught **13%**.

**And the specific trap that keeps recurring.** A data problem was marked fixed using a
measurement showing "0% drift" — but it compared stored values against what the *current code*
produced. If the code is wrong, it still reads zero. Three councils showed 0% drift precisely
*because* they had been consistently wrong since day one.

**The rule that came out of it:** before accepting anything as done, ask — *if the bug were still
there, would this check have gone red?* If no, it is not a check.

---

## 4. The competition, and the four verdicts

From `ce-property-intelligence-competitive-verdict-2026-07.md`. All verified by probing real
output, not by reading marketing.

- **ZoneDSS** — consumer reports, $31.90 / $108.90 per report or $97.90 a month. Its **paid**
  output betrayed it: zero rulebook obligations for North Sydney; oyster aquaculture as a
  permitted use in Cremorne; soil data from "1km south of Woy Woy Station" on a Cremorne lot;
  scores of 605 out of 100; lot dimensions of 47.9 m × 1.3 m.
- **PropCode** — venture-funded, on the NSW Government AI panel. Council rulebooks rendered as
  searchable web pages with an AI answer layer. Structured only on the easy open-data fields.
- **PlanningAI** — an AI writing assistant for certifiers. Generation, not extraction.
- **Archistar** — the real feasibility competitor. **130,000 users, 1,000 firms plus government**,
  partnered with CoreLogic and Domain.
- **Lotsearch** — owns the conveyancing slot, resold through InfoTrack and Dye & Durham. Does not
  do deep planning rules, because conveyancers do not need them.

**Verdict 1. Every standalone market is occupied.** Structural, not bad luck — compliance software
attached to a legal obligation attracts funding.

**Verdict 2. The market does not compete on data depth.** It competes on distribution, audience,
packaging, price and capital. **The proof: ZoneDSS launched a shallower product straight over the
top of PropCode.** If depth were the axis they could not have entered.

**Verdict 3. Accuracy is insourced or unneeded, never purchased.** Planners *are* the accuracy
layer and sell "we don't trust AI for substance." Councils are the source. The cost-cutters buying
the AI tools don't need accuracy — those tools survive on a disclaimer, low-stakes screening, and
a human at council who catches the errors.

**Verdict 4. The depth advantage has a clock on it.** AI made extraction cheap. The NSW Planning
Reforms 2025 and the Digital Plans mandate will publish structured controls at source. And it is
a maintenance advantage, not a compounding one. Roughly one to three years.

**The one opening with a trigger event attached.** Two documented incidents: a **Wagga Wagga**
application where an AI-written planning report got site coverage and landscaped area wrong,
missed a secondary-frontage setback and missed stormwater overland flow — triggering a formal
Additional Information Request, with delay and cost. And **Queanbeyan**, where AI zoning errors had
to be repaired by a planner. The sale is not "our data is better"; it is "your report will get
bounced, here is the check that stops it." **Two incidents is a hypothesis, not a market.**

**The disposition already on file (11 July):** license or sell the stack to someone who has
distribution but lacks depth — CoreLogic buys companies, Landchecker, or PlanningAI, where the AI
competitor actually needs a grounded layer underneath so a competitor becomes a customer. Or
redeploy the founder, on the basis that he built solo what funded teams are still assembling.

---

## 5. What the last fortnight found, product by product

### Shadow — passed, and it is the only product compared against reality

Pass mark of **0.50°** written down before the first run. Compared against pvlib's NREL SPA
implementation — a different algorithm by different authors. **Worst deviation 0.206° altitude,
0.346° azimuth. PASS.** Falsifiability proved by planting four defects (3, 42, 81 and 41 test
failures) then restoring byte-identically.

**Then the repair.** 519 stored reports rewritten. **The compass direction was 100% wrong** — a
stored constant, never computed. Eleven fabricated compliance passes corrected. Afterwards an
independent program sharing no code verified **538 of 538 bearings correct, worst error 0.050°**.

**The largest single finding of the campaign.** The adjacent-lot construction detector **never once
returned a reading in 538 attempts** — 231 insufficient scenes, 10 timeouts, 5 errors, 292 legacy
zeros — while all 538 reports rendered a confident negative about neighbouring land. **It was sold
as a paid feature.** Removed from all nine surfaces. The stored evidence fields were deliberately
kept, because deleting them would look like tidying while destroying the proof.

### Climate — permanently unknowable, and correctly closed

Two premises in the brief were false and both came from our own documents: the pre-written
correlation test **never existed** (it was one line under "planned improvements", copied into three
documents), and the reference data is not missing — it is in the APRA report **as pictures**, not
extractable numbers.

**Even with the data the test could not have falsified anything.** APRA measures the insurance
protection gap; this score measures exposure to mapped hazards — different constructs. And at a
sample of 20, the uncertainty on the correlation is about ±0.4, so a 0.7 pass mark is
indistinguishable from 0.4.

**Why the ceiling is permanent.** Five of the six components are membership of a mapped regulatory
overlay, and **an overlay is not a prediction that can be wrong — it is the ground truth for its
own question.** The only invented parts are the weights, four interaction bonuses and the band
cut-offs, and none has an external referent **even in principle**, because the score does not claim
to predict an outcome. A quantity that forecasts nothing has no error term, so there is nothing to
calibrate. **It must not appear on any list of pending calibrations.**

### Granny flat — now reports what the scan did

The confidence grade was replaced with five plain states. Measured first: **24 of 60 detection runs
found zero structures — not even a house.** Four of eleven "High confidence" reports became "Not
assessed" — they had graded High while the scan produced no count at all.

**Zero rows have ever carried human input.** The "13 of 16 human confirmations" was the machine
agreeing with itself; both apparent disagreements were a frontend fallback value. The confirm
button was never wired, so every answer a user gave was calculated in the browser and discarded.

**Detection accuracy is unmeasured and blocked on the founder** — it needs a human to label 50 to
100 blocks against aerial imagery, and with no users that human is him.

### Solar — a third party's number, passed through

It sums the Google Solar API's per-panel figures. Its correct ceiling is "source-linked." pvlib
and PVGIS were named as the method for months and are imported nowhere. **Do not describe it as
modelling.**

### Flood — and a discrepancy between two documents written the same day

`ce-product-assurance-position-2026-08.md` says flood **was** checked against Copernicus observed
2022 flood extents — recall **0.857 on 6 of 7 points**, 95% confidence interval **0.487 to 0.974**,
against a 0.90 mark set beforehand, verdict **"indistinguishable from the mark. Not a pass."** —
citing PR #897.

`ce-product-status-ledger-2026-08.md` says **"Calibration designed, not run."**

**One of them is stale.** The assurance position cites a specific PR and result file, so it is
probably the newer. Flagged rather than resolved — this is the same doc-decay pattern that
produced four false premises this fortnight.

Also found (PR #892): **12 of 142 stored flood reports served "not in a flood zone" without ever
establishing it** — among them addresses in Lismore, Murwillumbah and Telarah.

### Other findings

- **The test suite was silently off for three days.** One test imported a PDF library not installed
  on the build server; the runner stopped at the first failure, so about 1,800 tests never ran.
  Five consecutive builds were decorative.
- **A scientific library was named as the method on the disclaimer, the PDF and the marketing
  page.** No code used it. A scan of all 1,043 text columns found it in exactly two places.
- **A panel published neighbours' street addresses beside an invented rent figure.** Removed.
- **The invented urgency.** A session twice argued a repair was urgent because "seven customers
  were shown a false pass." On challenge: **there are no customers.** No identity column, no link
  from reports to leads, no orders table. 812 reports over ~420 addresses, bursts of 11 a day, four
  in one minute, landmark test addresses. A business-risk argument built on the existence of rows.
- **Our own documents are now the leading source of false premises.** Flagged three separate times
  in two days. A services document claimed one product shared another's satellite pipeline — it
  never has — and that one false line caused a session to miss five product surfaces, one of them
  the paid feature above.

---

## 6. What may be said publicly

**None of this is legally required.** The industry standard is disclaim and cap. CoreLogic says its
data is "not a complete and accurate record." PropTrack caps liability at $100. The government
Planning Portal disclaims itself. There is no certification scheme for this category.

**The reason to do it anyway.** Disclaimers protect a middleman who passes data through. This
product *derives* answers and invites reliance. Under Australian Consumer Law section 18 the maker
carries the burden of reasonable grounds and cannot contract out of it. A confidence badge is
itself a claim, so a hardcoded "high" is a false claim sitting *inside* the legal defence.

**The reviewer's verdict, verbatim:** *"The current campaign is useful provenance work, but it is
not a verification regime. Presenting it as one is the campaign's largest new liability."*

**The ladder, enforced:**

| Wording | Meaning |
|---|---|
| **source-linked** | We can show where the number came from. |
| **reproducible** | Re-running a committed recipe gives the same number. |
| **checked against X** | Compared to something outside itself that could have disagreed. |
| ~~verified~~ | **Banned.** Umbrella word implying all three. |

**Exactly one product is on rung 3: shadow sun-geometry.** Everything else is rung 1 or 2.

**The biggest open risk.** Nine genuinely different situations still collapse into one empty
result: queried and found nothing · source unavailable · coverage incomplete · parcel unresolved ·
unsupported geography · stale cache · parser failure · filtered out · genuinely not applicable.
Called the highest-value silent-wrong-answer risk in the system.

---

## 7. What people actually search for

From `ce-keyword-demand-map-2026-07.md`.

**Consumers search shallow "am I allowed to" questions. Businesses do not search the category at
all — they search competitor brand names.**

| Consumer cluster | Per month | Note |
|---|---|---|
| Planning portal terms | ~46,000 | They want the government site |
| Flood | ~1,280 @ $2.87 | Best commercial consumer surface |
| Granny flat | ~850 + suburb tail | |
| Exempt / complying development | ~730 | **Competition almost zero (0.01)** — the strongest wedge |

**Confirmed at effectively zero:** duplex, subdivision, "what can I build on my land" (20),
**"what can I build in [suburb]" (zero — this kills per-suburb pages)**, every upzoning and
housing-reform term, setbacks, every business category term.

| Competitor brand | Per month |
|---|---|
| corelogic rpdata | **90,500** |
| pricefinder | **22,200** |
| **landchecker** | **8,100, growing 13%** |
| archistar | 2,900 |
| forbury | 390 @ $42.65/click |

**"corelogic alternative" gets 10 searches a month. Every other alternative, versus or pricing term
gets zero.** Nobody shops for a switch through search. Business-to-business is entirely
introductions and referrals; comparison pages are worthless.

**The definitive finding:** the property economy's volume sits entirely in four buckets this
product does not touch — finance (mortgage calculator 90,500, stamp duty 49,500), valuation,
transactions, and finding tradespeople. Regulatory site analysis is low-frequency and
professionally mediated, so its terms are permanently in the hundreds. **There is no large consumer
search channel for this product and there never was. Stop looking for one.**

---

## 8. "Why not just extract the missing councils?"

Because "we probably have the DCPs and the scripts" is the assumption that has cost the most.

**There is no pipeline in that sense.** The scripts folder holds roughly twenty throwaway one-offs
— `_extract_ashfield_parking.py`, `_extract_blacktown_parking.py`, `_extract_blacktown_parking2.py`,
`_extract_krg_22r.py`, `_extract_landscaping.py` through `_extract_landscaping_r2.py`,
`_extract_nb_parking.py` / `2` / `3`, `_extract_parramatta_parking.py` / `2`. One script per council
per control type, several on their second and third attempt.

**What a new council costs today.** A hand-tuned formatting config first — the post-mortem's
recurring pain #4, in its own words *"every council needs hand-tuned two-column configs; doesn't
generalize."* Then bespoke extraction per control type. And the output is rows the next
re-extraction destroys, because identity is keyed by page position: **page-based re-keying
reproduces 60%.**

**The 13 councils that hold controls but no text** (canterbury_bankstown 68, canada_bay 40,
bayside 38, fairfield 33, wingecarribee 32, sutherland_shire 32, randwick 28, burwood 28,
liverpool 27, strathfield 25, ryde 24, the_hills 23, camden 23 — 421 controls):

**Zero of the 13 have ever been extracted.** Only **Canterbury-Bankstown is ready to start** — 66
PDFs held, 68 active chapters. **The other eleven hold chapter stubs with no PDF, no content hash
and no source URL** — a re-extraction there begins with acquiring documents, not parsing them.

**The evidence it does not get easier.** On 29 July a full day went to re-fixing City of Sydney,
Ashfield, Leichhardt, Marrickville and Ku-ring-gai *again*, and every failure mode hit that day was
already written down in June 2026. The document's own decision: **"Stop re-planning and stop
hand-re-extracting."**

**What would make it simple.** The June Phase 0+1 plan. Verified today, the honest answer is
*mixed*, not "unbuilt":

- ✅ Keying as a re-runnable derivation — **built** (`scripts/derive_precinct_keys.py`).
- ✅ Clause identity no longer positional — **largely fixed**; only 14 rows sit in a collision.
- ✅ Layout preflight — **built** (`scripts/dcp_preflight.py`).
- ❌ Schema-validate-before-commit and the per-chapter semantic gate — **not standing gates**.
- ❌ **Fail-closed staleness does not work.** 330 chapters carry a hash signal that they are not
  extracted from current content; **only 5 are flagged as needing extraction.**

**And the strategic caution:** there is no per-council search demand, so more councils adds no
demand. It only pays if a named buyer asks for a named council.

---

## 9. The strategic answers

### Is the project lame?

**On the product question, largely yes, and the documents say so twice.** Verification is not
sellable — accuracy is insourced or unneeded, never purchased. And none of it is legally required.

**Your read that "users are satisfied with RAG" is nearly right, and worth sharpening.** It is not
that users are satisfied with worse data. It is that the people who buy these tools don't need
accuracy, and the people who need accuracy produce it themselves. Both roads end in the same place.

**But three things in it are not lame and do not depend on the DCP problem:**

1. **The spatial estate.** A million mapped shapes, 3.2 million parcels, 244,000 approval records.
   None of it melts when the state publishes structured plans.
2. **The portable extraction playbook** — seven domain-agnostic rules in
   `docs/EXTRACTION_WHY_IT_RECURS_AND_THE_DURABLE_FIX_2026-07.md`. That is the real twelve-month
   output and it transfers to any regulated-document domain.
3. **The demonstrated method** — build a large system solo, then build the machinery to find which
   parts were false, then delete them. Rare, and the one asset with no expiry.

### The data layer is already scoped, and it routes around everything broken

`ce-mcp-agent-feed-execution-plan-2026-07.md` is decided through Phase 0.4. Licensing is a **GO**
with two carve-outs. The v1 field list is settled: **zone, height limit, floor space ratio, minimum
lot size, flood flag, bushfire flag, heritage flag, statutory land value.**

**Every one comes from the state-wide open-licensed map layers. Not one comes from the DCP corpus.**
Setbacks, capacity, yield, permissibility, satellite products and sale prices are all explicit hard
exclusions. So the salvageable data layer is state-wide, not 30 councils, and someone already
scoped it that way. What remains is the manifest serializer, the server, and commercial packaging.

**Two carve-outs to remember:** attribution travels in the payload as a non-null field, and **no
sale prices** — land *value* is open-licensed, sale *price* is not.

### NDIS — answered on 7 August, and it is a no for now

- **The competitive seat is not empty.** Audit Pilot claims 800+ providers and markets *"updates
  with every new NDIS standard the day it's released."* Provider Institute sells a change digest at
  **$1,199 a year — one third of the proposed $299/month seat.**
- **It fails the founder's own filter**, written in July: only chase domains where the valuable data
  is generated by usage or gated by a relationship, **never public-and-scrapable**. The NDIS corpus
  is public and scrapable. Of five channel targets only one has real distribution and it is the
  incumbent; the others are micro-businesses.
- **The market is contingent on registration being enforced.** The most repeated community advice is
  not to register at all.
- **Keep the amendment log running.** `lmcdo/ndis-amendment-log`, public, polling the federal
  register every six hours. Its entire value is elapsed time and it costs nothing. It is the only
  compounding asset requiring no distribution.

### Aged care — already killed

On the sixteen named-incumbent domains in the idea ledger. Note also that the "55% of providers made
no profit" figure making that sector look distressed was traced to a competitor's blog and appears
to be a *residential aged care* number.

### The pattern to take from all of it

Planning, NDIS, aged care — **the same shape: public data that is messy, where being better at
extracting it feels like an advantage.** It has not been one since AI made extraction cheap for
everybody. The filter was written in July and then not applied to the next idea. So "which niche
next" is the wrong question; every answer of that shape fails the same way.

### The prudent path

**Do not rearchitect and continue.** Cost: the deferred Phase 0+1 plus re-extraction. Return:
cheaper councils in a market with zero per-council demand, on an asset with one to three years left.

**Do not restart in a new niche.** 120 ideas reviewed; standalone diversifications die on competitor
check every time.

**Do convert this to a credential and an income.** Disposition 2 in the teardown — *the founder is
the asset that doesn't melt* — and the retrospective's note that provability produces exactly the
artefact you would show an insurer, a buyer or a due-diligence process. The career plan's
top-ranked path is direct outreach to NSW govtech and proptech, leading with the work rather than
the resume. **That path has never been attempted.**

**And one thing no document has written down.** Every plan says the binding constraint is
distribution. That was true when there was time to build distribution. **The binding constraint is
runway, and no document has re-run that calculation.** If it is short, the credential path is not
the consolation prize — it is the only one whose payoff arrives inside the time available.

---

## 10. What already exists, and what is genuinely left

### Written on 8 August, before this conversation — do not rebuild

| Document | What it is |
|---|---|
| `ce-verified-capability-statement-2026-08.md` | Every asset measured live, in plain English, with its ceiling. 49 KB. Includes a 16-row register of document-vs-database disagreements. |
| `ce-product-status-ledger-2026-08.md` | The same audit cut by **product** rather than dataset. |
| `ce-product-assurance-position-2026-08.md` | The customer-facing honest-ceiling table — what each product claims, what it was checked against, what it was not. |

### The outreach hold — standing, and already applied

`memory/project-outreach-hold-until-status-clear-2026-08.md`: **all outreach, sends, seeding,
posting and institutional pitches are on hard hold from 8 August.** Hold stamps are already applied
to the send queue, the master calendar, the beachhead doc, the institutional GTM and the conveyancer
GTM, with the bodies left intact as held-not-retracted.

**The memory's own wording: "Treat any recommendation to send as a rule violation, not a judgement
call."** The hold lifts only on explicit say-so.

**Recorded for honesty: this session violated that rule.** Its first substantive recommendation was
to send the fifteen planner DMs. It also wrote a dispatch prompt instructing a session to create the
capability statement, which already existed — a prior-art miss of exactly the class the four-sweep
rule exists to prevent.

### Genuinely left

**A. The employment package.** No document dated today covers it. Its precondition — the capability
statement — is now satisfied. Prior art to retrieve rather than regenerate:
`biz-career-employment-strategy-apr30.md`, `3d-geospatial-showcase-career-plan.md`,
`ce-linkedin-rewrite-2026-06.md` (⚠ written 22 June, before the truth-in-claims campaign — every
product claim in it is suspect), `biz-gis-training-and-certs.md`.

`biz-application-assets-guide.md` is **quarantined** — it carries at least four claims disproved in
August, including a "47,818 provisions" figure that turns out to be the exact row count of
`document_id_backup`, a backup table.

**B. The data layer, commercial packaging.** The technical scope is decided, so this is not a design
job — it is who buys, what the offer is, what it costs. **Constraint: the MCP plan's revenue path is
design-partner conversations, which the outreach hold covers.** So this can produce the scope and
the offer, but not the approach to anyone.

### Open questions

1. The flood discrepancy between the assurance position and the status ledger (§5).
2. Whether `/api/dcp/coverage` should include Inner West — a 3-council, 99-control gap in the
   project's own answer to "which councils do you cover".
3. Four deployed Python references to tables that have never existed — meaning any drawdown audit
   write is silently lost.
4. The cadastre redistribution licence, never independently confirmed.
5. Whether the 706 controls with no effective date can have one sourced from the Planning Portal.
6. Whether Stripe shows any real transaction. It is not mirrored into this database, so it is the
   only way to settle "are there users" absolutely — and it is the founder's check, not one any
   document here can make.
