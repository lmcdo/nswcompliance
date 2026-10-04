# PlotDetect CLAUDE.md — Universal Rules

## Severity
**CRITICAL** = silent production bugs or data corruption if violated.
**ENFORCED** = checked by git hooks, will block commit/push.

## Worktree Rule
After context compaction, if `.claude/worktrees/` contains directories, check which branch you're on and run all commands from that worktree path.

## Hooks Guard [ENFORCED] — DO THIS AT SESSION START
```bash
git config core.hooksPath .githooks
```
Hooks in `.githooks/`: commit-msg (QA tier), pre-commit (branch guard, secrets scan, large file gate, TSC baseline, bracket lint), post-commit (hash stamp), pre-push (push-to-main guard, qa_gate, liability scan, Sol cross-review; pytest/jest/build/ratchets run in CI only unless `PREPUSH_FULL=1`). Run once per clone/worktree.

## Branch Guard [ENFORCED]
Hook-enforced. If on `main`: `git checkout -b feat/<description>` before any work.

## Critical Warnings
- **NEVER use PM2** on Windows — spawns cmd.exe. claude-mem runs via startup hook.
- **NEVER `taskkill //IM node.exe`** — kills Claude Chat server
- **Kill Next.js dev server by PORT only:** `netstat -ano | findstr :3003` then `taskkill /F /PID <PID>`

## Subdirectory Rules (loaded automatically)
- `frontend-nextjs/CLAUDE.md` — UI bug protocol, component map, reports layout
- `enrichment/CLAUDE.md` — DCP structure model, LGA extraction, onboarding sequence
- `services/CLAUDE.md` — satellite product pipelines, GEE client, report storage

## Path-Scoped Rules (loaded when matching files are touched)
See `.claude/rules/` — regulatory-data, frontend, enrichment, services, blog-content, database, testing-and-qa, pre-pr-review.

## Database Safety [CRITICAL]
- Read `DB_SCHEMA.md` before any database work
- Run `./scripts/db_safety_check.sh` before any database operation
- Create backup before ANY database operation
- NEVER use TRUNCATE, DROP, or CASCADE without explicit user confirmation
- NEVER run queries without WHERE clauses on main tables
- Verify target table and row count BEFORE DELETE/UPDATE
- Timeouts: 30 seconds max
- Single database: Supabase (changes are immediately live in production)

## Data Integrity [CRITICAL]
- NEVER create fake, placeholder, or approximate data
- NEVER guess coordinates, boundaries, addresses, or real-world data
- If data is unavailable: STOP and ASK
- Data quality issues are never optional — >2% affected = Priority 1
- Use real APIs (NSW Planning Portal, geocoding) for coordinates

## Code Standards
- Python: PEP8, type hints, black, pydantic, Google-style docstrings
- TypeScript: for Next.js frontend
- Max 500 lines per file — refactor if approaching
- Tests: pytest in `/tests`, cover expected use + edge case + failure case
- Deterministic processing only — NO AI interpretation of regulations

## AI Behaviour
- Ask if uncertain — never assume
- Never hallucinate libraries or functions
- Confirm file paths exist before referencing
- Never delete/overwrite code unless explicitly instructed
- Never interpret regulations — only extract exact clauses

## Prior-Art Four-Sweep [CRITICAL]
Before ANY claim that something "doesn't exist / isn't built / isn't in the DB",
or before building any new surface (page, sheet, artifact, tool, review UI),
run ALL four sweeps and cite them in the claim:
1. **DB content, not table names**: `documents` by name pattern + `regulatory_provisions` by `document_id`
2. **Frontend surfaces**: `frontend-nextjs/app/**` (including `app/internal`), `components/`, `hooks/` — grep the CONCEPT, not the expected filename
3. **Python**: `services/` `scripts/` `src/` `enrichment/`
4. **Plans + memory indexes** (`~/.claude/plans/INDEX*.md`, MEMORY.md)
A negative claim without its greps is unsupported. Artifact publishes are
hook-gated on a fresh `.claude/.prior-art-surfaces.json` marker (see
`.claude/hooks/surface-prior-art-guard.py`) — reuse an existing surface when
one exists (e.g. `/internal/dcp-review`) instead of building a parallel one.
Origin: four prior-art misses in one session, 2026-07-27.

## Deployment & Branching [ENFORCED]
Branch naming: `fix/` | `feat/` | `chore/`
Workflow: branch → work → commit → `gh pr create` → share preview → user says "merge" →
**`python scripts/check_pr_gates.py <PR>`** → `gh pr merge --squash`
PR body: `## What` (one-line) + `## Why` (problem/feature). No "Test plan". No attribution.

**Never merge on an empty check list. [CRITICAL]**
A PR that is **CONFLICTING gets no GitHub Actions run at all** — `pull_request` workflows execute
against the merge commit, and a conflicting branch has none to build. Nothing fails; nothing
starts. The PR page shows no checks, which looks exactly like "not finished yet".
Measured 2026-08-10: PR #907 sat 40+ min with zero runs, rebasing cleared the conflict, and the
run appeared **20 seconds** later. PR #902 was merged 10 seconds *before* its run was created.
- `python scripts/check_pr_gates.py <PR>` exits non-zero unless a `gates` run exists for the
  PR's current head sha **and** passed. Run it immediately before `gh pr merge`.
- If it says NOT-RUN: `git fetch origin && git rebase origin/main`, resolve, force-push.
- Branch protection would block this properly, but the API returns 403 "Upgrade to GitHub Pro" —
  unavailable on a private repo on the free plan. Until then this check is the gate.
- Safety net if one slips through: `gates` also runs on push to `main`, and `main-red-alarm.yml`
  raises an issue if main's HEAD has no successful run. That catches it *after* landing, not before.

## Project Structure
- `services/` — Python backend (compliance API, satellite product pipelines)
- `enrichment/` — LGA extraction, rule extraction pipeline
- `frontend-nextjs/` — Next.js app (compliance UI + reports UI)
- `src/` — models, processing, regulatory logic
- Virtual env: `venv_linux`

## Project Stack
- Python (backend/ETL/scripts), TypeScript (frontend)
- Supabase (PostgreSQL) — single production database, changes are immediately live
- Domain: NSW planning compliance + satellite property intelligence

## Database Quick Reference
- Always check `DB_SCHEMA.md` before writing queries
- **Every figure here carries the query that produces it. Re-run it rather than quoting this
  file — a number without its query is how this section was wrong for months.**

| Fact | Value (measured 2026-08-08) | Query |
|---|---|---|
| Base tables | **116** (130 relations incl. views) | `SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'` |
| `regulatory_provisions` rows | **55,696** | `SELECT count(*) FROM regulatory_provisions` |
| …of which live + actionable (the served set) | **19,957** | `... WHERE is_current AND v2_is_actionable` |
| Distinct `v2_precinct_id` | **433** (423 current, 418 live+actionable) | `SELECT count(DISTINCT v2_precinct_id) FROM regulatory_provisions WHERE v2_precinct_id IS NOT NULL` |
| `dcp_setback_controls` rows | **1,071** | `SELECT count(*) FROM dcp_setback_controls` |

- Use `v2_precinct_id`, NOT `dcp_precinct_provisions` (legacy, **0 rows**)
- Common columns: `v2_topic`, `v2_marker`, `source_council`, `ref_number`, `v2_precinct_id`
- ⚠ **`former_council` and `source_ref` DO NOT EXIST on `regulatory_provisions`.** Use
  `source_council` (lowercase slugs, ~19.7k NULL for statewide instruments) and `ref_number`.
  Several older docs and scripts still assume the old names.
- **Never quote a flat council count** — coverage is layered. See
  `memory/verify-dcp-coverage-status.md` and
  `~/.claude/plans/ce-verified-capability-statement-2026-08.md` §3.2.

## Plan Files
- Location: `~/.claude/plans/`
- Prefix: `ce-` ComplianceEngine | `biz-` Business | `meta-` Cross-project
- Dashboard: `~/.claude/plans/INDEX.md`

## Key Reference Docs
- `DB_SCHEMA.md` — database structure (read before any DB work)
- `docs/CONFIGURATION.md` — env vars, feature flags, R2 paths, LGA checklist
- `DEPLOYMENT.md` — deploy guide
- `.claude/DATA_QUALITY_TRACKER.md` — data quality issues and fixes
