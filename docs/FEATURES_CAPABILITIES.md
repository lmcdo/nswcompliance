# PlotDetect: what it is and what it does (rewritten 2026-11-26)

This file replaces the January 2026 feature list, which was out of date (it said three councils, 47,818 provisions and version tracking that never held data).
It states what the product is and where each piece lives. **Every number is in section 4 with the query that produces it; re-run the query, do not copy the number.**
What may be said to outsiders is in `PlotDetect Outreach/CLAIMS - what you can and cannot say.md`, not here.

## 1. Value proposition

For one NSW address, PlotDetect gives the rules that apply to that property and nothing else, in the council's own words, with the page or clause they are printed on.
It adds the new housing-reform tests (including a walking distance measured along real footpaths), site limits such as flood and gas pipelines shown as limits, and a short evidence statement.
When it cannot tell, it says "can't tell". It does not guess, and it does not call anything compliant: the planner or certifier decides.
The difference from a search or a chatbot is that every answer can be traced to a council document we hold, with the date we stored it.
It is a private pilot (10 councils named in the claims sheet), with no price, and no proof that anyone relies on it or would pay for it (the claims sheet says to agree with that).

## 2. What it does (surfaces on main; a route existing is not proof it is good today)

**A. Council rules for a property.** Address in, only that property's rules out: the council's chapters filtered to the zone and development type, each rule with its source page.
Where: `/assessment`, `/property`, `/canibuildit/check`, `/dcp-browse`; API `provisions/for-property`, `dcp/structured-controls`, `dcp/coverage`.

**B. Project brief ("Your project").** For a house in a given zone and a development type, the council's own rules ranked, each with a verdict word that is only "indicative", or "not found, open the plan" when nothing is found.
Where: `YourProjectSummary` component; API `brief/for-property`, `brief-overlay`. Claims OC-22 to OC-30 govern what can be said.

**C. Housing reform (low and mid-rise, transport-oriented areas).** Eligibility, exclusions clause by clause, and the walking distance to the station or town centre.
Where: API `housing-sepp/eligibility`, `housing-sepp/gates`, `housing-sepp/area-check`, `housing-sepp/evidence`; page `reports/evidence-statement`; `duplex-check`; `tools/upzoning-check`.

**D. Site limits.** Flood (our own copy of studies), bushfire, heritage and conservation areas, nearest gas pipeline, shadow, solar, granny-flat site, climate risk, aircraft noise (ANEF), nearby development applications.
Where: `reports/flood`, `reports/bushfire`, `reports/shadow`, `reports/solar-yield`, `reports/granny-flat`, `reports/threat-radar`, `climate-risk`, API `environmental/anef`, `heritage/hca-check`, `compliance/constraints`.

**E. Permitted uses and standards.** Permitted uses by zone from the LEP land use tables; pattern-book and CDC checks; setback and parking numbers from plans.
Where: API `lep/permissibility`, `permissibility/check`, `pathway/pattern-book-eligibility`, `cdc/preliminary-check`, `cdc/setback-check`, `compliance/parking`; `tools/zoning-check`, `tools/subdivision-check`.

**F. Reports.** Evidence statement, conveyancing, pre-DA site history, intelligence brief, flood, bushfire, shadow, solar, granny-flat, threat-radar.
Where: `/reports/*`.

**G. DA response workflow.** Saved sessions that hold a user's answers to the requirements for a DA. Where: API `da-sessions/*`.

**H. Currency and honesty machinery.** Dated copies of council plan files; a monitor that flags changed state laws until a person has compared them; a ledger of checks that decides which claims may be made (`.claude/dq_checks.json`, `python scripts/dq_check.py`).

**I. Audiences with their own pages.** `/for/planners`, `/for/builders`, `/for/buyers-agents`, `/for/conveyancers`, `/for/councils`, `/for/homebuyers`, `/for/students`.

**Not checked today (do not claim either way):** the January list said these were not supported: checking a user's own design against the rules, a parking calculator, version tracking of rules, lot size from the polygon, existing-structure detection from imagery, a climate score. Routes such as `cdc/compliance-check` and `compliance/parking` now exist, so open the code before saying a thing is or is not built.

## 3. Principles the product holds

- Rules come from council documents or the NSW Planning Portal, never typed in by hand. No regulatory table is hardcoded.
- Missing data is stated as missing. A "no" is shown only when it was computed.
- Nothing is called compliant, eligible, approved, safe or guaranteed.
- A rule is served only if its page link was checked against the council's current PDF; state-law text is served only when proven in the same transaction (migration 113).

## 4. Measured 2026-11-26 (run the query; do not trust the number)

| Fact | Value | Query |
|---|---|---|
| Rules served | 61,225 | `SELECT count(*) FROM regulatory_provisions WHERE is_current AND v2_is_actionable` |
| ...council rules / councils with some | 57,784 / 18 | `... AND source_council IS NOT NULL` ; `count(DISTINCT source_council)` |
| ...state-law rules | 3,441 | `... AND source_council IS NULL` |
| Council rules whose page link was checked against the current PDF | 57,076 of 57,784 | `count(*) FILTER (WHERE page_check IN ('on_page','moved'))` on the council set |
| Served rules with no decided scope (zone/type) | 5,452 (mostly state law, which has no council config) | `v2_zone_source IN ('no_config','config_silent','filtered_to_all') OR v2_zone_source IS NULL` |
| Served rules whose scope was read from the plan as "all" | 41,286 | `v2_zone_source = 'config_all'` |
| Numeric controls (setbacks, parking, landscaping) served / held | 307 / 829 | `dcp_setback_controls WHERE is_current` split on `needs_review` |
| Project brief rows / councils | 8,533 / 17 | `SELECT count(*), count(DISTINCT council) FROM project_brief_rows` |
| Land use table rows | 19,551 | `SELECT count(*) FROM lep_land_use_table` |
| Dated council plan copies | 806 | `SELECT count(*) FROM dcp_source_versions_dated` |
| Review flags on state law (DQ-88) | 0 | `python scripts/dq_probe_live.py --id DQ-88` |

**Older documents said otherwise, and were wrong or out of date:** "93.7% of served rows are tagged zone ALL" (August; the scope work since has made most of that a decision read from the plan);
"3 councils" (January); "47,818 provisions" (a backup table's row count); "the page-checked share is 6.8%" (August).

## 5. Known weak spots (so nobody is surprised)

- 18 councils have served rules, but only the 10 pilot councils are described to outsiders. Never quote a flat council count.
- 829 numeric controls are held back for review. For Waverley the reasons are car-parking table cells, deep soil and tree canopy values that the council's own words do not state as a number; other councils have other reasons (`dcp_setback_controls.review_reason`).
- The walking distance has no agreement figure yet: the earlier ones were measured on the old answer.
- About 52 stored state-law rows that are not served still hold wording the law has removed (DQ-88 note).
- The walk and its check both use OpenStreetMap; a missing footpath would affect both.
- No proof of reliance and no known buyer; the claims sheet tells you to agree when someone says nobody pays for this.

## 6. Keeping this true

If a number changes, change the query's result here, not the prose. If a surface is removed, remove it from section 2. Outreach wording lives only in the claims sheet.
