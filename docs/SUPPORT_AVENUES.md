# Grants, programs, mentors and support avenues

**Rewritten 2026-08-10.** Supersedes the 2026-04-09 version, which had gone wrong in four ways:
its deadlines had all passed, it was built on a provision count that turned out to be a backup
table, it led with satellite products that have since failed or been withdrawn, and it named a
warm contact who was deleted from the record on 2026-08-06.

**Structure: still a sole trader.** Not incorporated as at 2026-08-10. Every entry below is
tagged for that, because it is the single biggest filter on this list.

> **Dates are as recorded April–May 2026 and have NOT been re-checked against the programs'
> own sites.** Treat every date here as "last known", not "confirmed". Verify before writing
> anything.

---

## 0. What is actually true about the product — read before writing any application

This section exists because the previous version of this document fed a false number into every
application asset. Everything here was measured live, read-only, on the date shown.

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
count are all **98.2%** — 178,510 rows carry a positive cost, median **$186,885**.

**Elapsed time to determination**: median **18 days**, 90th percentile **81 days**, across
181,730 rows holding both dates.

That is the asset. It is a record of what was approved, so there is nothing to calibrate and no
confidence story to tell. It is also the one thing here that survives the NSW planning reforms —
those publish the *rules* at source, which erodes the rules-based products and does nothing to a
record of outcomes.

**Not yet verified:** whether it joins cleanly to the lot database. Latitude and longitude are
100% populated so a spatial join to `nsw_cadastre_lots` (3,220,617 parcels) is available in
principle — the join itself has not been tested. Do not claim "lot-level" until it has.

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
usable comparison points existed, because council coverage barely overlaps the places that
flooded. Climate risk cannot be validated at all and is permanently closed. Solar is a third
party's number. Granny-flat detection recall is unmeasured.

Per-product detail: `~/.claude/plans/ce-product-status-ledger-2026-08.md`.

### Never put these in an application

- ❌ **"47,818 provisions"** — that is the row count of `document_id_backup`, a backup table. It
  appears in `docs/ARCHITECTURE.md`, `docs/FEATURES_CAPABILITIES.md` and three history docs, all
  superseded. The real figures are 55,696 total / 19,957 served.
- ❌ **A flat council count for DCP depth.** Coverage is layered — 25 councils numeric, 15 text,
  3 deep. "128 LGAs" is true only of zoning.
- ❌ **Any accuracy claim for flood, climate, solar or granny-flat detection.** None has been
  externally validated and two never can be.
- ❌ **Traction implying users.** The 981 stored report runs are development traffic;
  `property_reports` has no identity column. There are no paying customers. Say "no revenue" —
  it is the truthful answer and it is normal at this stage.
- ❌ **Internal pipeline names** (see `.claude/rules/blog-content.md`).

---

## 1. Open now, and open to a sole trader

Ranked by what they actually deliver against the current constraint.

### NEIS — New Enterprise Incentive Scheme ✅ SOLE TRADER | Federal, ongoing
https://www.dewr.gov.au/new-enterprise-incentive-scheme

JobSeeker-equivalent income (~$760/fortnight) for up to 39 weeks, plus **structured mentoring and
business training**, delivered through TAFE and registered providers. Built for individuals
starting a business. Requires registration with Services Australia.

This is first on the list because it is the only entry that pays for time rather than costs, and
because the mentoring is bundled. If savings are funding the runway, this is the highest-value
item on the page and it does not require the product to be finished.

### Founder Institute ANZ ✅ SOLE TRADER | Rolling cohorts
https://fi.co/apply/sydney

Explicitly accepts solo founders at idea/pre-seed, pre-revenue, no incorporation. Part-time,
14 weeks, pushes toward investor-readiness milestones. No upfront equity; small pool on
graduation. The most accessible structured accelerator for a sole trader with no revenue.

### Google for Startups Accelerator: AI First (Australia) ✅ SOLE TRADER | Sept–Nov cycle
https://startup.google.com/programs/accelerator/ai-first/australia/

10 weeks, equity-free, GCP credits plus mentorship. No structure requirement recorded.
**Caveat worth being clear-eyed about:** the program describes itself as seed-or-equivalent
stage, and this has no revenue and no users. The application is cheap; the odds are not good.
Apply, but do not build the plan around it.

### SXSW Sydney Pitch ✅ SOLE TRADER | ~October 2026
https://www.sxswsydney.com/participate/pitch

No stated incorporation requirement. A visibility and credibility play, not a funding one.
Cost is application effort.

### buy.nsw supplier registration ✅ ABN ACCEPTED | Always open
https://buy.nsw.gov.au/supplier

Register as an approved NSW government supplier under software / data services / planning tools.
ACN preferred but ABN accepted at initial registration. Once listed, agencies can procure without
a full tender. Slow-burn institutional credibility; costs an afternoon.

### NSW Boosting Business Innovation / TechVouchers ⚠️ STATUS AMBIGUOUS | Closed intake
https://www.nsw.gov.au/business-and-economy/innovation/grants-and-programs/boosting-business-innovation-program

Up to $50K matched for collaborative R&D between a NSW SME and a publicly funded research
organisation. Closed to direct application — must be sponsored by a delivery partner (UTS, UNSW,
UOW). Sole-trader eligibility is genuinely unclear: targets "SMEs" without explicitly excluding
sole traders, but requires a formal commercialisation agreement. **Worth one email to a delivery
partner to settle it** — if an ABN holder qualifies, this is the only real money on the
sole-trader list.

---

## 2. The incorporation decision — now the main gate

Not incorporated as at 2026-08-10. The April plan targeted "before June/July 2026" and that has
passed. Everything in section 3 is locked behind it.

**Cost:** ~$600 ASIC + ~$500 accountant setup; ~$1.5–2K/year ongoing.

**Unlocks:** MVP Ventures, Startmate, CSIRO Kick-Start, Industry Growth Program, ETCF future
rounds, R&D Tax Incentive, and practically Sydney Angels.

**The timing argument that actually matters.** MVP Ventures Round 4 was expected ~September 2026
and Startmate applications ~October. Incorporation is not instant and both want a company that
exists at application time. If either is genuinely wanted, the decision is now, not later.

**The argument against, stated fairly.** Incorporation costs real money and adds annual
compliance, and it buys access to programs that mostly want revenue or users — neither of which
exists yet. The R&D Tax Incentive is the one benefit that pays back regardless of any program
outcome, and only for spend *after* incorporation. A defensible alternative is to stay a sole
trader, take NEIS and Founder Institute, and incorporate when there is a reason beyond
eligibility. **This is a judgement call, not a recommendation — the numbers above are what it
turns on.**

---

## 3. Locked behind incorporation

| Program | Amount | Last-known timing | Notes |
|---|---|---|---|
| **MVP Ventures Round 4** | $20K–$75K | ~Sept 2026 | NSW HQ, <$400K turnover, ≤10 FTE. **50% cash co-contribution** — needs matching money. |
| **R&D Tax Incentive** | 43.5% refundable | With tax return | No application. Claude API, dev and contractor costs tied to R&D. Only counts post-incorporation. |
| **Startmate Summer 2027** | $120K / 7.5% | ~Oct 2026 apps | Wants a live product, traction and a 2-minute founder video. |
| **Industry Growth Program** | $50K–$250K | Federal, ongoing | Early-stage commercialisation, TRL3–TRL6. |
| **CSIRO Kick-Start** | $10K–$50K matched | Rolling | Requires ACN. <$10M turnover *or* trading <3 years. |
| **ETCF** | $500K–$2M | If it runs 2027 | Requires matched co-funding. |
| **Sydney Angels** | $100K–$1M | 6 cycles/year | Wants demonstrated traction. Not yet applicable. |

---

## 4. Ecosystem and mentors — no incorporation required

- **Tech Central Innovation Hub**, 477 Pitt St — co-working, mentoring, government connections.
  https://sydneystartuphub.com
- **Stone & Chalk PropTech Hub** — 20+ proptech residents, membership open to sole traders, warm
  intros. Where the NSW proptech network is concentrated.
  https://www.stoneandchalk.com.au/proptech
- **PropTech Association Australia** — cheap membership, investor/partner intros, PropTech Awards
  entry. https://www.proptechaustralia.com.au/benefits
- **WSU Launch Pad** — ⚠️ **prior participation**: a ~$500 / 6-month mentoring program was
  completed here previously. Confirm the exact program name before re-engaging; the alumni
  connection is the cheapest live mentor path on this page.
  https://launchpadlive.com.au/launch-pad-membership/
- **Planning Institute of Australia NSW** — a retired senior planner or council assessment
  officer as an advisor costs nothing. Also the channel to the target user. Apply proactively for
  a 2026 State Conference speaking slot. https://www.planning.org.au/pia/divisions/nsw-home.aspx
- **ULI Australia Young Leaders Group** — 50% membership discount under 35; reach into councils
  and major developers. https://australia.uli.org/programmes/young-leaders-group/
- **UDIA NSW** — 500+ members, developer-side. Awards entries build credibility with buyers.
- **Startmate mentor network** — accessible via community events without joining the program.
- **UNSW Founders** — no strict incorporation requirement for initial engagement. Second angle:
  approach the Built Environment school about research collaboration on approval-rate data. The
  certificate table is genuinely publishable material.
- **NSW AI Solutions Panel (DPHI)** — daai@planning.nsw.gov.au. Vetted list councils can procure
  from. Realistically 12–18 months out, but the relationship should start before the product is
  ready.

---

## 5. Closed or passed — do not re-plan around these

UNSW C10x (18 May) · Antler AUS16 (cohort began 27 July) · YC S26 (4 May) · Startmate Winter 2026
(11 May) · CRC-P Round 19 (12 May) · IRENA NewGen (3 May) · iAwards (1 May) · ETCF 2026 (29 April)
· MVP Ventures Round 3 (5 April) · Lander & Rogers LawTech Hub cohort 9 (1 April — watch for
cohort 10, ~Jan 2027) · REINSW WIRE 2026 (28 April) · Sydney Build Expo (29–30 April) · Startup
World Cup Melbourne (14 May) · PropTech Awards entries (17 April).

**REACH ANZ** — growth-stage PropTech accelerator, skews to revenue-generating companies. Check
eligibility before spending effort; pre-revenue is likely excluded.

---

## 6. Test users — still the actual bottleneck

Unchanged and worth stating plainly: **there are no users.** Every grant application and
partnership conversation is materially stronger with one piece of documented user feedback, and
that has been true in every version of this document since April.

For the compliance product, one town planning consultant is the right first user — they write SEE
documents and do pre-DA checks manually. Reachable via PIA NSW or LinkedIn.

> **Standing hold.** `memory/project-outreach-hold-until-status-clear-2026-08.md` holds all
> outreach and institutional pitches from 2026-08-08, lifting only on the founder's explicit
> say-so. This document is a reference, not a prompt to send. Nothing here should be actioned as
> outreach while that hold stands.

**Removed 2026-08-06:** the DocuBuild warm path previously listed here. The contact ghosted and
the early validation was retracted — the product was not reliable at that stage. Do not re-propose
it, cite it as validation, or count it as a channel.

---

## 7. If you only do four things

1. **Assess NEIS eligibility.** Income plus mentoring, sole-trader eligible, available now.
2. **Email a TechVouchers delivery partner** (UTS or UNSW) to settle whether an ABN holder
   qualifies. One email decides whether $50K matched is reachable without incorporating.
3. **Confirm the WSU Launch Pad program name** and re-open the alumni connection.
4. **Make the incorporation call** on the section 2 numbers — before September if MVP Ventures
   or Startmate matter, or consciously not at all.

---

## Related docs

- `~/.claude/plans/biz-application-assets-guide.md` — the reusable application assets, rewritten
  2026-08-10 on the measured figures above
- `~/.claude/plans/ce-product-status-ledger-2026-08.md` — per-product: checked against what, and
  not checked against what
- `docs/architecture/VERIFICATION.md` — every number with the query that produced it
- `docs/WHAT_TO_SELL_AND_WHY_2026-08.md` — the argument for leading with the certificate record
- `memory/founder-context.md` — constraints
