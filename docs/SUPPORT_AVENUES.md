# Grants, programs, mentors and support avenues

**Rewritten 2026-08-10, then verified against every program's own site the same day.**
Supersedes the 2026-04-09 version, which had gone wrong in four ways: its deadlines had all
passed, it was built on a provision count that turned out to be a backup table, it led with
satellite products that have since failed or been withdrawn, and it named a warm contact who was
deleted from the record on 2026-08-06.

**Structure: still a sole trader.** Not incorporated as at 2026-08-10. This is the single biggest
filter on the list, and section 3 is now the argument that matters most.

**Every entry below is marked CONFIRMED (quoted from the program's own site on 2026-08-10) or
NOT CONFIRMED.** The previous version's dates were all stale; this one records what was actually
checked so the next reader knows what to re-verify.

---

## 0. What is actually true about the product — read before writing any application

This section exists because the previous version fed a false number into every application asset.
Everything here was measured live, read-only, on the date shown.

### The strongest asset — approved certificates

Measured **2026-08-10** against production, read-only:

| Fact | Value | Query |
|---|---|---|
| Complying development certificates | **181,750** | `SELECT count(*) FROM complying_development_certificates` |
| Councils | **128** | `count(DISTINCT council_name)` |
| Span | **2018-07-09 → 2026-08-08** | `min/max(determination_date)` |
| Still growing | **~775/week** | `count(*) GROUP BY date_trunc('week', created_at)` — 776 / 723 / 802 / 777 / 769 over the last five weeks |

**Depth by council** — 44 councils hold 1,000+ certificates, 15 hold 500–999, 27 hold 100–499,
34 hold 10–99, and 8 hold fewer than 10. Median 367, mean 1,420, deepest Blacktown at 10,156.
So "128 councils" is true but 86 councils is the number with usable depth. Say that.

**Field completeness**, of 181,750 rows: description, address, latitude/longitude, submission
date and determination date are all **100%**. Cost of development, dwelling count and storey
count are all **98.2%** — 178,510 rows carry a positive cost, median **$186,885**, totalling
**$89.37B** of approved construction, of which **$20.61B across 39,214 certificates** falls in
the last twelve months.

**Elapsed time to determination**: median **18 days**, 90th percentile **81 days**, across
181,730 rows holding both dates.

That is the asset. It is a record of what was approved, so there is nothing to calibrate and no
confidence story to tell. It is also the one thing here that survives the NSW planning reforms —
those publish the *rules* at source, which erodes the rules-based products and does nothing to a
record of outcomes.

**Not yet verified:** whether it joins cleanly to the lot database. Latitude and longitude are
100% populated so a spatial join to `nsw_cadastre_lots` (3,220,617 parcels) is available in
principle — the join itself has not been tested. Do not claim "lot-level" until it has.

**⚠ `first_seen_at` on that table is a dead column** — NULL on 146,841 rows and last populated
2026-05-22. Use `created_at` for ingest freshness. Anyone measuring feed health off `first_seen_at`
will wrongly conclude the feed is dead.

### The rest of the estate, measured 2026-08-09

Evidence for all of these: `docs/architecture/VERIFICATION.md`, which carries the query for every
figure and was run read-only against production.

- `spatial_overlays` — 1,088,573 shapes, 25 layer types. Zoning covers all 128 councils; heritage
  and lot size 127; height 75; floor space ratio 65.
- `nsw_cadastre_lots` — 3,220,617 parcels. `lot_search_index` — 3,126,418.
- `regulatory_provisions` — 55,696 clauses, of which **19,957** are live and actionable and only
  **2,069** carry a number.
- `dcp_setback_controls` — 1,071 rows across 30 councils, 989 live, **every one carrying the
  source sentence it came from**. Only 42 have a clause join and only 365 an effective date.
- `development_applications` — 62,016, from May 2025 only.

### What has been checked against the outside world

**One product.** Shadow analysis was compared against pvlib's NREL SPA implementation and
**passed a limit written down before the test ran** — worst error 0.206° altitude and 0.346°
azimuth against a 0.50° mark.

Everything else is source-linked or reproducible, but has never been compared to anything that
could have disagreed. Flood calibration was designed and could not be completed — only seven
usable comparison points existed. Climate risk cannot be validated at all and is permanently
closed. Solar is a third party's number. Granny-flat detection recall is unmeasured.

Per-product detail: `~/.claude/plans/ce-product-status-ledger-2026-08.md`.

### Never put these in an application

- ❌ **"47,818 provisions"** — the row count of `document_id_backup`, a backup table. It appears
  in `docs/ARCHITECTURE.md`, `docs/FEATURES_CAPABILITIES.md` and three history docs, all
  superseded. Real figures: 55,696 total / 19,957 served.
- ❌ **A flat council count for DCP depth.** Coverage is layered — 25 councils numeric, 15 text,
  3 deep. "128 councils" is true of zoning and of certificates, and of nothing else.
- ❌ **Any accuracy claim for flood, climate, solar or granny-flat detection.**
- ❌ **Traction implying users.** The 981 stored report runs are development traffic;
  `property_reports` has no identity column. There are no paying customers. Say "no revenue".
- ❌ **Unsourced market figures.** The old "~90,000 DAs/year / $1.5B granny flat / $200M advisory
  / 3.5M properties" paragraph is retired — the measured $20.61B/12mo replaces it.
- ❌ **Internal pipeline names** (see `.claude/rules/blog-content.md`).

---

## 1. ❌ NEIS — TRIED, DEAD LOSS. Do not re-propose.

The founder completed NEIS. Verdict: **useless.** Every prior version of this document ranked it
first, on the reasoning that it pays income and bundles mentoring. That reasoning was wrong in
practice, and it survived three rewrites because nobody had actually done it.

Recorded rather than deleted so it is not rediscovered and recommended a fourth time. **Treat the
whole "generic government advice for new business owners" category as exhausted** unless a
specific program has a concrete reason to differ. Business NSW ($654/yr) is the same genre —
skip it for the same reason.

---

## 2. Open now, and confirmed open to an unincorporated sole trader

Only four things on this page are both confirmed-eligible and have a live door.

### Startmate Launch Club ✅ CONFIRMED | Open now
https://www.startmate.com/programs/launch-club

8-week pre-accelerator. CONFIRMED targets "pre-launch or already in market" founders and states
explicitly that pre-revenue is not a barrier. No incorporation requirement stated. This is the
realistic Startmate entry point and the only accelerator-adjacent door currently open.

### WSU Launch Pad — Ignition Accelerator ✅ CONFIRMED | Cohort starts August 2026
https://launchpadlive.com.au/ignition-accelerator/ · launchpad@westernsydney.edu.au

**Free and equity-free.** 15 weeks part-time: weekly group clinics, on-request 1:1 mentoring
Tue–Fri, curriculum, office hours, co-working. CONFIRMED open to non-WSU people — "You don't have
to be a Western student." No incorporation requirement found. Cost is time and monthly in-person
attendance in Parramatta.

**The best value on this page.** Also the natural place to resolve the prior-participation
question: the ~$500 / 6-month program completed here previously could not be identified from
public pages, and whether alumni get a re-engagement path is not addressed anywhere on the site.
They hold the enrolment record — one email settles both.

### ASBAS Digital Solutions ✅ CONFIRMED | Ongoing
https://www.digitalsolutions.org.au/register-for-asbas/

CONFIRMED sole-trader eligible — business.gov.au states the program is for businesses under 20
FTE "as well as sole traders." NSW/ACT tier: free workshops, or **~$45 for 4 hours of 1:1
advisory** plus a digital roadmap. CONFIRMED funded through 2029-30.

Generic digital-adoption advice — e-commerce, marketing, record-keeping, cyber — not proptech.
Calibrate to what $45 buys. It is the cheapest formal advisory hour available and the only
survivor of the category NEIS came from.

### buy.nsw supplier registration ✅ ABN ACCEPTED | Always open
https://buy.nsw.gov.au/supplier

Register under software / data services / planning tools. ACN preferred, ABN accepted at initial
registration. Slow-burn institutional credibility; costs an afternoon.

---

## 3. The money question — and why incorporation is now the whole answer

**Verified 2026-08-10: as a sole trader there is essentially no accessible grant capital.**
Every program with real money attached excludes you in its own published words:

| Program | Amount | The exact bar |
|---|---|---|
| NSW MVP Ventures | $20–75K | "a company incorporated in Australia under the Corporations Act 2001 (Cth)" |
| CSIRO Kick-Start | $10–50K matched | must "hold an Australian Company Number (ACN)" — an ABN does not satisfy it |
| Industry Growth Program | $50–250K | "a company incorporated in Australia, a co-operative, or an incorporated trustee" |
| R&D Tax Incentive | 43.5% refundable | companies only; "individuals, sole traders and most trusts generally cannot claim" |

**The one exception — NSW Boosting Business Innovation / TechVouchers.**
https://www.nsw.gov.au/business-and-economy/innovation/grants-and-programs/boosting-business-innovation-program

CONFIRMED published criteria: ABN registered in NSW, under 200 employees, turnover under $10M,
not a subsidiary, holds commercialisation rights, provides matched cash. **Incorporation, ACN and
company structure appear nowhere** — materially unlike every row above. Up to $50K.

The barrier is different from what the April doc assumed: it is not structure, it is the
**dollar-for-dollar cash match**. $50K granted means $50K of your own cash on the table. The
program is closed to direct applicants and runs only through a delivery partner (UTS, UNSW, UOW).
The single remaining unknown is whether a delivery partner's own screening adds a company bar the
published criteria do not state. **One email settles it.**

### The incorporation call

**Cost:** ~$600 ASIC + ~$500 accountant setup; ~$1.5–2K/year ongoing.

Earlier today I argued for waiting, on the grounds that these programs mostly want revenue and
users you do not have. The verified research weakens that argument in one specific place.

**The R&D Tax Incentive is the item that changes the sum.** It is a *refundable* offset, so with
no revenue it pays out as cash rather than reducing tax you do not owe, and it requires no
matching contribution and no application — it goes in with the tax return. Against Claude API,
infrastructure and development spend, it is plausibly the largest number on this page. It only
counts expenditure **after** incorporation, so each month unincorporated forfeits that month's
claim permanently.

That is an accountant's question to size, not this document's. But it is the one benefit that
does not depend on winning anything, and it was underweighted in the morning version.

**Against:** real money out, annual compliance, and MVP Ventures — the largest sole NSW grant it
unlocks — also demands 50% cash co-contribution, so incorporating does not by itself produce
reachable capital.

**Timing:** Startmate applications close **8 Nov 2026** and mechanically require a company to
issue equity to. MVP Ventures Round 4 has no announced date (funding committed through FY2027).

---

## 4. Accelerators — verified, and mostly not what the old doc said

### Founder Institute ANZ (Sydney) — best fit on paper, window just closed
CONFIRMED accepts unincorporated sole traders; CONFIRMED ~60% of each cohort are solo founders;
CONFIRMED targets pre-product, pre-traction founders under $500K revenue. Correction to the
morning version, which said "no upfront equity": there is a **$799 entrance fee** (75% refundable
before session 3) **and a 2.5% equity warrant** — but the warrant activates only on a first
external raise of $100K+, and costs nothing if the company never raises.

The Sydney cohort's final deadline was **28 July 2026** and the program kicked off **10 August
2026** — today. Next Australian intake NOT CONFIRMED; not yet listed on fi.co. Email them rather
than watch the site. https://fi.co/apply/sydney

### Startmate Accelerator — the reverse of what internal memory assumed
The old doc recorded Startmate as needing traction. CONFIRMED wrong: Startmate's own pages state
solo founders are welcome, **"67% of Accelerator companies had no revenue when they applied"**,
and at least one idea-stage pre-MVP company joins every cohort. **Applications close 8 Nov 2026**
for a 25 Jan – 29 Apr 2027 cohort. $120K at $1.5M post-money for first-time raisers.

Incorporation is NOT CONFIRMED either way at application stage — but receiving the investment
mechanically requires a company to issue it to. Worth asking them directly.
https://www.startmate.com/accelerator/program

### Lander & Rogers LawTech Hub — open structure, adjacent sector, between cohorts
CONFIRMED "limited formal eligibility requirements" — no incorporation, revenue or team-size
mandate; spans idea-stage to launched product. Equity-free. Cohort 9 is running now (May–Nov
2026); cohort 10 timing NOT CONFIRMED, ~Dec 2026–Jan 2027 by prior pattern. Framed for legal-tech
— planning compliance is adjacent, not squarely in scope. Email before investing effort.

### Confirmed dead ends — do not re-plan around these

- **Antler** — CONFIRMED structural disqualifier, not a timing one: *"We don't invest in solo
  founders."* The residency exists to pair applicants into teams. Next cohort 21 Sept 2026,
  irrelevant while solo.
- **REACH ANZ** — CONFIRMED growth-stage: cohort companies "have real customers, real revenue."
- **Google for Startups AI First** — CONFIRMED 2026 applications closed **19 July 2026**. The
  Sept–Nov dates are when the selected cohort runs. Also targets Seed–Series A. Watch 2027.
- **Techstars Tech Central Sydney** — CONFIRMED cancelled. NSW did not renew the contract; no
  2026 cohort, local team exited (Feb 2026).
- **EMDG** — sole traders eligible in principle but requires 2+ years ABN and capacity to spend
  $20K/yr on export marketing. CONFIRMED currently closed. No export program to fund.
- **NSW Business Connect** — CONFIRMED ceased 30 September 2025. A $37M successor was announced
  in the 2026-27 budget, to run through the Service NSW Business Bureau, but as at 2026-08-10 no
  live program, eligibility or application process is published. Do not wait on it.

### Flagged, not assessed
**NSW Diversity Pre-Accelerator** ($4M, the Techstars replacement) runs through Remarkable
(disability), Catalysr (migrant/refugee/CALD) and an Indigenous-founder stream. Each is gated on
a demographic criterion. Listed only so it is not missed if one genuinely applies — no assumption
made either way. https://www.nsw.gov.au/business-and-economy/innovation/grants-and-programs/diversitypreaccelerator

---

## 5. Ecosystem and mentors — with real prices

- **Tech Central Innovation Hub**, 477 Pitt St — CONFIRMED "from free and $25/day", now
  Stone & Chalk-operated. Presence and event flow, no structured mentoring at that tier. Go for a
  free day before paying for anything. https://www.techcentralinnovationhub.com.au/options/
- **Stone & Chalk membership** — CONFIRMED hot desk **$615/month**, dedicated $720. Skip: same
  building as Tech Central at a fraction of the cost above.
- **Stone & Chalk "AI Solopreneur"** — a paid course, $1,199–1,399 +GST, no funding or equity
  component. Cohort 1 ran 21 Jul – 25 Aug 2026. Know it exists; it is not an accelerator.
- **PropTech Association Australia** — CONFIRMED Individual $250/yr, Startup $450/yr. Events,
  forums, awards entry. Mentorship and introductions are **not** listed as formal benefits. A
  distribution play — buy only if you will attend. https://www.proptechaustralia.com.au/signup
- **Planning Institute of Australia NSW** — CONFIRMED an "Allied Professional" category exists
  for non-planners, and CONFIRMED PIA runs a mentoring program matching by location and goals.
  NOT CONFIRMED: the Allied Professional fee (page 403'd twice) and whether non-planners can
  access the mentoring. **The most on-target association here** — it is the professional body of
  a named buyer. One email to membership@planning.org.au. https://www.planning.org.au/mentoring
- **ULI Australia Young Leaders** — CONFIRMED 50% dues discount under 35; AU price NOT CONFIRMED.
  Networking, not mentoring.
- **UDIA NSW** — NSW fees NOT CONFIRMED; the WA chapter's published kit runs $4,736–$15,282/yr
  for developer tiers. Aimed at established developers. Skip absent a specific event.
- **GovTech.au** — free mailing list, councils are a named buyer. Thin, but costs nothing.
- **UNSW Founders** — no strict incorporation requirement for initial engagement. Second angle:
  the certificate table is genuinely publishable research material (approval rates, cost and
  elapsed time by council, type and year), which doubles as the sponsor route into TechVouchers.
- **NSW AI Solutions Panel (DPHI)** — daai@planning.nsw.gov.au. Councils procure from it directly.
  Realistically 12–18 months out; the relationship should start before the product is ready.

---

## 6. Test users — still the actual bottleneck

Unchanged and worth stating plainly: **there are no users.** Every grant application and
partnership conversation is materially stronger with one piece of documented user feedback, and
that has been true in every version of this document since April.

> **Standing hold.** `memory/project-outreach-hold-until-status-clear-2026-08.md` holds all
> outreach and institutional pitches from 2026-08-08, lifting only on the founder's explicit
> say-so. This document is a reference, not a prompt to send. Nothing here should be actioned as
> outreach while that hold stands.

**Removed 2026-08-06:** the DocuBuild warm path previously listed here. The contact ghosted and
the early validation was retracted. Do not re-propose it, cite it as validation, or count it as a
channel.

---

## 7. The short list

Four questions, each answerable by one email, and one dated deadline:

1. **WSU Launch Pad** — the August Ignition cohort, and what the prior enrolment was.
   Free, confirmed eligible, best value on the page.
2. **A TechVouchers delivery partner** (UTS/UNSW/UOW) — does their screening add a company bar
   the published criteria don't? This is the only unresolved path to real grant money.
3. **PIA NSW** — Allied Professional fee, and whether non-planners can join the mentoring.
4. **Founder Institute** — when is the next Australian cohort, since the site doesn't say.

**The one dated item: Startmate applications close 8 Nov 2026.** Pre-revenue and solo are both
confirmed acceptable; incorporation is the open question.

**And the structural decision:** incorporation, weighed on section 3 — where the R&D Tax
Incentive, not any program, is the argument.

---

## Related docs

- `~/.claude/plans/biz-application-assets-guide.md` — the reusable application assets, rewritten
  2026-08-10 on the measured figures above
- `~/.claude/plans/ce-product-status-ledger-2026-08.md` — per-product: checked against what
- `docs/architecture/VERIFICATION.md` — every number with the query that produced it
- `docs/WHAT_TO_SELL_AND_WHY_2026-08.md` — the argument for leading with the certificate record
- `memory/founder-context.md` — constraints
