# Quality statement: how we check the planning rules we show

**Status: DRAFT for the owner's sign-off. Not linked from the site. Not sent to anyone.**
Measured 2026-11-04. Every figure below has the command that prints it. A figure without its
command is not a figure; re-run the command, do not quote this page.

This page says what we check, how, and what we know is still wrong. It makes no claim of
certification against any standard.

## 1. What a served rule is

A rule shown to a user is the council's own sentence, copied from its published plan, with:

- the **quote** (`council_quote`) and the **page** it is printed on (`quote_page`, `pdf_page`, `printed_page_label`);
- the **document** it came from (`documents.pdf_name`, `r2_pdf_url`) and that document's dates
  (`amendment_date`, `consolidated_as_of_date`, `last_verified_date`, `version_status`);
- the **area** it covers (section 2).

The law is the council's PDF. The database copy of the text (`provision_text`) is a working copy, never the reference.

| Figure | Value 2026-11-04 | Command |
|---|---|---|
| Rules in the served set | 61,246 | `SELECT count(*) FROM regulatory_provisions WHERE is_current AND v2_is_actionable` |

## 2. How a rule is tied to a property

A rule is shown at an address only if the address falls in the area the rule covers. The area is
decided from the first source on this ladder that exists. The ladder runs top to bottom:

1. An **official map layer** (NSW Planning Portal / NSW spatial services).
2. **Council map data** we hold for that area.
3. A **lot or address named in the plan's own text**, checked against NSW registers.
4. A **figure traced** to the plan's own words.
5. Otherwise the rule is **not shown as applying**. It goes in a "may apply" box. We never draw a boundary by guess.

Known gap, measured: rules written for an area, where the area has no map, reach no house.

| Figure | Value 2026-11-04 | Command |
|---|---|---|
| Rules from a part-of-council chapter shown to every house (DQ-143) | 0 | `python scripts/dq_probe_live.py --id DQ-143` |
| Rules whose land no machine has confirmed, upper bound (DQ-144) | 7,386 | `python scripts/dq_probe_live.py --id DQ-144` |
| Rules shown to no house (DQ-146) | 2,245 | `python scripts/dq_probe_live.py --id DQ-146` |

DQ-144 is a ceiling that may only fall. It counts rules where no script has confirmed the land
from the plan's own words. The audit in section 3 is what measures wrong-area errors.

## 3. The audit

Full method: `docs/qa/audit-method.md`. In short:

- **Sample.** Random points inside each audited council area, the nearest NSW address point,
  the rules the live product serves at that address, and 10 random rules per address.
- **Reader.** A person reads each rule against the page of the council's plan.
- **Serious error** (any one of): a rule for another property or area; words that are not the council's; a page that does not hold the words.
- **Counting.** `severe` and `unsure` both count as serious (conservative). Rules not read count as passing the code pass. This is stated, not hidden.
- **Rate.** Exact one-sided 95% Poisson upper limit per 100 rules shown.
- **Evidence.** `data/address_audit/<date>-<run>/` (`packets.jsonl`, `to_read.jsonl`, `labels.jsonl`, `summary.json`), committed to git.
- **Repeat.** At least every 30 days. The claim lapses when the newest labelled run is older than 30 days.

| Figure | Value 2026-11-04 | Command |
|---|---|---|
| Labelled runs in the 30-day window | 4 | `python scripts/audit_rate_check.py` |
| Rules shown / addresses | 1,120 / 112 | same |
| Rules read by a person | 275 | same |
| Serious (severe 14, unsure 5) | 19 | same |
| Upper 95% bound per 100 rules shown | **2.49** (severe only 1.95) | same |
| Newest labelled run | 18 days old | same |

Runs 6 to 8 alone gave 1.89 (9 serious in 830 rules). Run 9 was labelled on 2026-11-04 and alone gave 10 serious in 290 rules.
Adding it takes the bound above the 2.0 limit the outreach claim OC-18 states, so **that claim does not hold on today's evidence.**
Run 9's labels are one reader's (no second reader). Three of its serious labels rest on the property record showing no
matching area (Pipeline corridor, Pound Road, Hornsby Town Centre). Dropping those three still gives 2.17.

What this number is: **no worse than 2.49 serious errors per 100 rules shown, at the audited addresses, by this method.**
It is not a statement that the other rules are correct.

## 4. Known limits

- **The reader is not deterministic.** The extraction reader can return different output on a re-run of the same page. Most defects are caught by the checks above, not prevented.
- **Review queue.** 11,406 extracted rules wait for review and do not reach users. `SELECT count(*) FROM dcp_review_queue WHERE status='pending'`
- **Rules that reach no house:** 2,245 (section 2, DQ-146).
- **Citations not proven by a script:** 248 served rules. `python scripts/dq_probe_live.py --id DQ-145`
- **Heritage-tagged rows.** The area gate for these has a recorded scope limit (`scripts/dq_probe_live.py`, the `_ALL_HERITAGE` rule). The DQ-146 query leaves heritage-marked rows out (`LOWER(v2_marker) <> 'heritage'`), so 2,245 is a floor. DQ-143 to DQ-145 were not checked for the same exclusion.
- **The audit's first pass.** See the first limit in `docs/qa/audit-method.md`: the three labelled runs were read from a first pass that flagged fewer rules than the code now committed. The recorded rate stands for that pass.
- **Outreach claims.** 16 of 21 passed before run 9 was labelled (4 not yet, 1 not checkable from here, 0 contradicted). OC-18 now fails the 2.0 limit; re-run for the current count. `python scripts/dq_check.py --outreach`

## 5. What we do not do

- We do not interpret regulations. We extract the council's sentence and show where it is printed.
- We are not a substitute for the council's own certificate, a planning certificate under section 10.7, or advice from a planner or lawyer.
- We do not show a figure we did not compute.

## 6. External reference point: ISO 19157 data quality elements

This is a map of our checks onto the standard's vocabulary. We have **not** been assessed against ISO 19157 and do not claim to meet it.

| ISO 19157 element | Our check | Where measured |
|---|---|---|
| Completeness (omission) | Rules shown to no house; rules waiting in review | DQ-146; review queue |
| Completeness (commission) | A rule shown at an address outside its area | DQ-143; audit "wrong-area" |
| Logical consistency | Rule fields agree with the page: quote on the page, number on the page, citation | DQ-145; `scripts/citation_proof.py` |
| Positional accuracy | Address to area: which map decided it | Ladder in section 2; DQ-144 |
| Thematic accuracy | Words are the council's; rule is for this property | Audit, section 3 |
| Temporal quality | Plan edition and date in force | `documents.consolidated_as_of_date`, `version_status` |
