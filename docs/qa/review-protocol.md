<!-- prior-art-checked: docs/qa has no review protocol; known-tradeoffs.md is the trade-offs list only. -->
# Code-quality review protocol (pre-registered 2026-10-25)

Written and committed BEFORE any Step 1 tool output exists. The commit time proves the rules came first.
Full plan: `~/.claude/plans/ce-NEXT-PROMPT-2026-10-25-codex-functional-qa.md` (ROBUSTNESS GATES rev 3).

## Frozen code
Review sha: `a6d2e378` (origin/main, 2026-10-24). Findings on later code are out of scope.

## Tool versions (pinned)
ruff 0.17.2 · radon 6.0.1 · vulture 2.16 · bandit 1.9.4 · pip-audit 2.10.1 · pydeps 3.0.9 ·
eslint 8.57.1 (project) · knip 6.43.0 · jscpd 5.4.2 · madge 8.0.0 · node 22.19.0 · python 3.11.0.
Configs: project config where one exists (`frontend-nextjs/.eslintrc.json`); none for ruff, so ruff defaults.
Each run saves: command, exit code, raw output, sha256 of output.

## Which files are scored (G1)
Only files `scripts/qa_live_files.py` marks `served` or `scheduled`. Output: `quality-baseline-2026-10-25/live_files.tsv`.
`ci` and `unreached` are reported, not scored. Nobody re-labels a file by hand.

## Bars (live files only)
Copied unchanged from the plan's benchmark table: radon cc ≤ 20 per function (C needs a reason) · MI A/B ·
≤ 500 lines · ≤ 5% duplication, any duplicate on served-rules path = P2 · 0 lint errors on changed lines ·
0 high/critical security · no swallowed error on a served path · each served-rules/monitor entry point has a
test that fails if it returns [] · no query > 1 s, no DB call in a loop on served path · no import cycles.
"After" = same tools, versions, config; compared file by file.

## Codex benchmark (Step 2)
Cases = the last 5 merged fix PRs touching served rules or DCP monitor that include a test. List + one-line
answer key written here BEFORE Codex runs. Exports strip .git, the fix's test, docs/, .claude/, plans, DQ lines,
comments naming the bug. "Found" = right file AND mechanism, scored by Sonnet against the key. Reported as k/5,
an indication only.

## Review (Step 4)
Codex lists ALL P1 candidates, then top 15 others. Phase 1: every P1 and P2 verified. Every rejection cites
file:line; rejected P1/P2 go back to Codex once; overrule rate reported. Bug fix = test red on frozen sha,
green after. Trade-offs list `known-tradeoffs.md` is frozen at this commit; later additions marked post-hoc.

## Step 2 cases (selected by rule 2026-10-25, before any Codex run)
Rule applied mechanically: merged `fix/` PRs that are ancestors of `a6d2e378`, change a test file, and touch
served rules (`services/`, `app/api/provisions/for-property/`) or the DCP monitor (`r2_monitor.py`,
`hub_scrapers/`, `verifyops_record.py`); newest 5. Not hand-picked; two are "typed figure" policy fixes, kept.
Pre-fix code = the PR's merge commit parent (`<sha>^`).

| PR | Area | Category | Answer key ("found" = right file AND this mechanism) |
|---|---|---|---|
| #1492 | monitor | bug | When a chapter's link is re-pointed, the stored file tag / last-download date are kept, so a header-only check calls the NEW file "unchanged" without downloading it |
| #1491 | monitor | bug | Several list links match one chapter; the loop keeps the last match ("last link wins"), so the stored link flips between an in-force and a repealed/draft file |
| #1490 | served | error handling | A failed lookup (timeout/busy/error) returns empty and is shown as "no rules apply / no precinct / council not covered" instead of "not checked" |
| #1489 | served | consistency | Planning-rule numbers typed into live screens (not read from DB/source), against the house rule |
| #1481 | served | consistency + bug | Battle-axe CDC limits (3 m access, 12x12 m) are typed constants, not read from `cdc_eligibility_standards`; a missing/stale row could still pass |

## Codex settings (pinned before any Codex output, used for Steps 2 and 4)
`codex-cli 0.156.0`, model `gpt-5.6-terra` (the user's configured model), `model_reasoning_effort=high`,
`--sandbox read-only --ephemeral --ignore-user-config --skip-git-repo-check`. Brief = `codex-bench/stance.txt` +
one area file. A first launch was stopped before any output: `--ignore-user-config` had dropped reasoning to "none",
which would have under-scored Codex.
