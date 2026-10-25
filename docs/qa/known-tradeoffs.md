<!-- prior-art-checked: docs/qa has architecture-overview.md and codebase-scan-2026-05-23.md; neither lists deliberate trade-offs. -->
# Known trade-offs (DRAFT — user to confirm)

Frozen review commit: `a6d2e378` (origin/main, 2026-10-24).
Anything on this list is **intentional**. A reviewer reports it as "known trade-off", not as a defect,
unless it has got worse or its "revisit when" condition is now true.

| # | Trade-off | Why | How it is contained | Revisit when | Source |
|---|---|---|---|---|---|
| 1 | One Supabase database, no staging copy; writes are live at once | Solo developer, cost | Backup before every write, guarded WHERE, row count, user's yes | A second developer or paying customers | CLAUDE.md "Database Safety" |
| 2 | No GitHub branch protection | Free plan returns 403 | `scripts/check_pr_gates.py` before every merge; `main-red-alarm.yml` after | Move to GitHub Pro | CLAUDE.md "Never merge on an empty check list" |
| 3 | CI runners are WSL on the developer's PC | No paid runners | Restart script; stuck "pending" = WSL stopped | CI must run when the PC is off | memory: reference-ci-runners-are-wsl-on-this-pc |
| 4 | Pre-push does not run tests; CI does | Pushes were too slow | CI `gates` run is required before merge | — | #1221 |
| 5 | AI reads council PDFs (extraction is not deterministic) | No other way to read 1,000s of PDF pages | Nothing serves without page proof, fidelity gates, review queue never auto-approved; no AI interpretation of rules | — | DQ-101; CLAUDE.md "Deterministic processing" |
| 6 | `scripts/` holds many one-off and repair scripts | A year of data repair work | Tooling, not on the served path; reviewed as "tooling" not scored | Archive pass after review | — |
| 7 | Old DB password is in git history | Committed in early work | Password rotated 2026-10-22 | — | memory: project-live-db-password-in-git-history |
| 8 | Monitor runs as a Railway cron; a deploy kills a running run | Simplest scheduler | No monitor-image merges 02:00-03:00 UTC; `run_unfinished` alarm | — | memory: reference-railway-cron-deploy-traps |
| 9 | Data checks live in an executable DQ ledger, not a ticket tracker | One source of truth that can be re-run | `python scripts/dq_check.py` | — | #931 |
| 10 | npm major upgrades deferred | Decided, risk to a working frontend | Do not re-decide | — | #863 / #770 |

## User to add (10 min)
- Shortcuts you know about that are not here:
- Anything above that is wrong:

## Open gaps (NOT deliberate — to be fixed)
| # | Gap | Evidence | Fix |
|---|---|---|---|
| G1 | No check that every clause in a PDF section was extracted; a page passes with 30% of its rule lines present | `scripts/page_coverage.py:33-37`; City of Sydney 7.4 lost (b),(c) on 2026-10-02 | Per-section clause-marker count; measure missed-clause rate on a sample first |
