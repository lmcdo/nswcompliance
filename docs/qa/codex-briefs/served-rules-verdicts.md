# Served rules — verdicts on Codex findings (frozen a6d2e378, 2026-10-25)

Codex: 8 findings, all marked P1, 0 blocked reads, 239 s (`out-served.json`). Every one opened and checked by Opus
in the frozen copy. **7 real, 1 intentional.** Plus 1 extra finding of ours that the check exposed.

| # | Rule | Where | Verdict | Evidence |
|---|---|---|---|---|
| 0 | 5 whole lot | app/api/property/route.ts:82 | **REAL P1** | `ST_Contains(geom, ST_Point(lon,lat))` for flood, riparian, wetlands etc. A lot partly in a flood area reads "No" if the address point is outside it. |
| 1 | 2/3 failed ≠ No | components/compliance/LepControls.tsx:261 | **REAL P1** | Flood cell shows `'No'` with no not-checked guard. The route marks `notChecked('spatial_overlays')` on failure (route.ts:222) and the PDF honours it (lib/assessment/reports.ts:443), but this screen does not. Bushfire, ANEF etc. on the same card do have the guard. |
| 2 | 2 failed ≠ none | components/compliance/StateLevelControls.tsx:305-325 | **REAL P1** | Non-OK response or exception leaves `[]`; UI then says "No Housing SEPP structured requirements for this development type" (line 861). |
| 3 | 1 typed figures | lib/regulatory-constants.ts:43 | **REAL P1** | Typed zone lists (`RESIDENTIAL`, `APARTMENT_PERMITTING`) decide applicability. No check covers it: zone lint checks only new lines; not in `zone_code_baseline.json`. |
| 4 | 1 typed figures | lib/pdf/granny-flat-report.tsx:88 | **INTENTIONAL** | Every row is in `.claude/regulatory_figure_ledger.json` with fate `cited` (verbatim SEPP Sch 1 quote naming clause). House ledger allows this. |
| 5 | 1 typed figures | lib/requirement-prioritization.ts:160 | **REAL P1** | `return areaSqm >= 450;` decides whether subdivision rules are hidden (used at ComplianceDashboard.tsx:253, 278). |
| 6 | 1 typed figures | components/compliance/PatternBookEligibilityCard.tsx:496 | **REAL P2** | "300m² min … 1500m² min" in shipped text. Explanatory, not a decision, so P2. |
| 7 | 1 typed figures | components/compliance/ADGSummaryCard.tsx:94 | **REAL P1** | Local `APARTMENT_RESTRICTED_ZONES` list drives the apartment warning. Same gap as #3. |

## Extra finding (ours): the typed-figure scanner has holes — P1 for the gate, not the page
`scripts/lint_hardcoded_regulatory_numbers.py` reports "0 unlisted" yet misses #5, #6 and #7:
- #6: the line passes `JSX_TEXT` but is dropped by the `PLANNING` keyword filter — "min" is not in the list (only "minimum").
- #5: a bare number in a comparison (`>= 450`) has no unit, so `FIGURE` never matches.
- #3/#7: zone lists are not numbers; the zone lint only checks newly added lines.
So "typed figures open: 83" (the ledger count) undercounts. Fix = widen the scanner, then re-measure before any claim.

## Precision (this area)
7 of 8 real (88%). One finding is a house-approved exception Codex could not know about.
Codex reported only 8 items (cap was all P1 + 15). It did not report anything outside the 8 house rules.
