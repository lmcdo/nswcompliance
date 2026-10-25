# Step 1 tool baseline — 2026-10-25

Code: exact copy of `a6d2e378` (6,527 files, matches `git ls-tree`). Tools and versions: `../review-protocol.md`.
Scored = **856 live files** (served 770 + scheduled 86) from `live_files.tsv`. Whole-repo numbers shown for context.
Every run: `raw/_runs.tsv` (tool, exit code, sha256 of uncompressed output, time, command). Files >1 MB are gzipped.
Failed attempts stay in the log; the row used is named below.

| Metric | Bar (live) | Whole repo | Live | Worst live | Run used |
|---|---|---|---|---|---|
| Lint findings (ruff defaults) | 0 on changed lines | 9,273 | 2,669 | intelligence_brief.py 464 | ruff_default_try2 |
| Swallowed errors (BLE, S110, S112, E722) | 0 on served path | 926 | 336 | granny_flat.py 28 | ruff_swallowed_try2 |
| Functions too complex (cc > 20) | 0 | 275 | 114 | generate_pdf 313 | radon_cc |
| Files maintainability grade C | 0 | 23 | 11 | dcp_extract_changed.py | radon_mi |
| Dead code (vulture ≥80%) | — | 60 | 11 | db_config.py | vulture |
| Security HIGH (bandit) | 0 | 34 | 10 | all B324 (weak hash, md5/sha1) | bandit |
| Security MEDIUM (bandit) | — | 381 | 76 | 56 are B608 (SQL built as string) | bandit |
| Python packages with CVEs, API image | 0 high | 1 of 251 | 1 | pillow 12.3.0, 37 CVEs, fixed in 13.0.0 | pip_audit_api |
| Python packages with CVEs, monitor image | 0 high | 0 of 62 | 0 | — | pip_audit_monitors |
| npm audit high / critical | 0 | 15 / 3 | package level | — | npm_audit |
| eslint errors / warnings | 0 errors | 0 / 64 | 0 / 32 | ProvisionsByTocStructure.tsx 4 | eslint_try3 |
| Unused frontend files (knip) | — | 307 | 2 | route_RELEVANCE_DRAFT.ts | knip_try3 |
| Unused exports (knip) | — | 258 | 236 | lga-configs/index.ts 12 | knip_try3 |
| Import loops, TypeScript | 0 | 2 | 1 | council-quote ↔ page-citation | madge_circular |
| Import loops, Python | 0 | 3 | 2 | brief/arithmetic/conveyancing (5 files) | py_cycles |
| Duplicated lines | ≤ 5% | 7.03% | ≤ 8.5% (upper bound) | legislation_monitor.py | jscpd_try4 |
| Files over 500 lines | ≤ 500 | 232 | 129 | dcp_extract_changed.py 6,207 | line_counts |
| Slow DB queries | none > 1 s | NOT MEASURED | | | needs read-only prod access |

## Checks on the numbers
- Two counts re-done by a different method: files >500 lines live = 129 both ways; ruff live = 2,669 both ways.
- That recount caught a real error: ruff and jscpd skip files listed in `.gitignore` even when git tracks them
  (`enrichment/extractors/`, which is live). First runs undercounted (ruff live 2,471, jscpd 6.24%). Re-run without it.
- pydeps dropped: on a test package with a known loop it printed nothing. Replaced by `py_cycles` (same import graph
  as `qa_live_files.py`, imports only, not spawned scripts); it finds the test loop. One reported loop checked by hand: real.

## Limits (say these when quoting)
- pip-audit resolves unpinned lines to today's versions, which may differ from the built image.
- Root `requirements.txt` cannot be installed (`samgeo` is not on PyPI). It is not what the images install.
- Live duplication % counts both copies of each clone, so it is an upper bound.
- jscpd uses `jscpd-config.json` (minTokens 50, the repo's own setting), not the repo's narrower path list.
- eslint and knip needed a clean `npm ci` of the frozen lockfile; the main checkout's packages were older.
