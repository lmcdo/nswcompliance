<!-- prior-art-checked: docs/qa/codex-briefs did not exist; diagrams/served-rules.md is the traced flow, reused here. -->
# Codex brief — area: address → served rules (Step 4, frozen a6d2e378)

Written 2026-10-25, AFTER the Step 2 result (recall 1/5). The house-rule checks below were added because Codex
missed every bug that needed project knowledge. So this area's results are NOT comparable to the Step 2 score.

## What the area must do
A user enters an NSW address. The app finds the property (planning portal, spatial layers, council) and shows
ONLY the rules that apply to that property, in the council's exact words, with document and page.
Flow: `docs/qa/diagrams/served-rules.md`. Files in scope (298, machine list): `served-rules-files.txt`.

## House rules — check every file in scope against each (these caused real past bugs)
1. **No typed planning figures.** Setbacks, heights, lot sizes, distances, rates, zone lists must come from the
   database or an official API with a source. A planning number written into code is a P1.
2. **A failed check says "not checked".** A timeout, error, busy server or missing row must never show as
   "no rules apply", "No", "not covered", an empty list, or a pass.
3. **Unknown is not No.** null / undefined / missing must never be turned into false, "No" or 0.
4. **Only this property's rules.** Council, zone, precinct and map-layer filters must be applied. A filter that
   cannot be worked out must fail loudly, not quietly let everything through or drop everything.
5. **Whole lot, not one point,** where the rule is about the land (flood, riparian, heritage area).
6. **No AI interpreting rules.** AI may not decide what a rule says or whether it applies.
7. **No swallowed errors** on this path (`except: pass`, empty `catch {}`, returning [] on error).
8. `former_council` exists only for Inner West lots; joining on it elsewhere silently drops data.

## Known trade-offs (intentional — do not report unless worse than stated)
`docs/qa/known-tradeoffs.md` items 1–10.

## Tool numbers for this area
`docs/qa/quality-baseline-2026-10-25/README.md` (live files: 129 over 500 lines, 114 functions cc>20 repo-wide live).

## Output
Same JSON format as `codex-bench/stance.txt`. Add `"house_rule": N` when a finding breaks rule N.
All P1 candidates first, then at most 15 others.
