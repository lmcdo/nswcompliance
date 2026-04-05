# PlotDetect CLAUDE.md — Universal Rules

## ⛔ CRITICAL — READ FIRST ⛔
- **NEVER use PM2** on Windows. Spawns cmd.exe windows. claude-mem runs via startup hook — if broken: `cd ~/.claude/plugins/marketplaces/thedotmack && npm run worker:restart`. Do not fix with PM2, scheduled tasks, or Windows startup scripts.
- **If cmd.exe windows spawn:** Check `wmic startup list full | grep pm2`. Remove: `powershell -Command "Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'PM2'"`
- **NEVER `taskkill //IM node.exe`** — kills Claude Chat server
- **Kill Next.js dev server by PORT only:** `netstat -ano | findstr :3003` then `taskkill /F /PID <PID>`
- **NEVER run queries without WHERE clauses** on main tables
- **NEVER create fake/placeholder data** — ask if real data unavailable
- **UI bug?** → Read `frontend-nextjs/COMPONENT_MAP.md` before touching anything. Full protocol: `frontend-nextjs/CLAUDE.md`
- **LGA onboarding?** → Read `docs/DCP_SCOPE_CONFIG_REFERENCE.md` first. Full rules: `enrichment/CLAUDE.md`
- **Satellite products?** → Full rules: `services/CLAUDE.md`

## Subdirectory Rules (loaded automatically when working in that directory)
- `frontend-nextjs/CLAUDE.md` — UI bug protocol, component map, reports layout
- `enrichment/CLAUDE.md` — DCP structure model, LGA extraction, onboarding sequence
- `services/CLAUDE.md` — satellite product pipelines, GEE client, report storage

## Investigation Before Action (NON-NEGOTIABLE)
- Always investigate thoroughly before making changes or proposing solutions
- Never assume — check actual tables, columns, and data first
- Pattern: Read files → Check DB schema/data → Show findings → Get confirmation → THEN act
- If uncertain about column names or table structure: STOP and CHECK first

## Keep It Simple (NON-NEGOTIABLE)
- Apply changes directly when the target is already identified — don't build detection scripts for known problems
- Do NOT over-engineer with pattern-matching scripts or complex pipelines when a direct operation works
- Ask: "Is there a simpler way to do exactly what the user asked?"

## Database Safety (NON-NEGOTIABLE)
- Read `DB_SCHEMA.md` before any database work
- Run `./scripts/db_safety_check.sh` before any database operation
- Create backup before ANY database operation
- NEVER use TRUNCATE, DROP, or CASCADE without explicit user confirmation
- NEVER run queries without WHERE clauses on main tables
- Verify target table and row count BEFORE DELETE/UPDATE
- Timeouts: 30 seconds max
- Single database: Supabase (changes are immediately live in production)

## Data Integrity (NON-NEGOTIABLE)
- NEVER create fake, placeholder, or approximate data
- NEVER guess coordinates, boundaries, addresses, or real-world data
- If data is unavailable: STOP and ASK
- Data quality issues are never optional — >2% affected = Priority 1
- Use real APIs (NSW Planning Portal, geocoding) for coordinates
- NEVER create rectangular approximations or made-up lat/lon

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

## Deployment & Branching (NON-NEGOTIABLE)
**NEVER push directly to main.** Always branch and open a PR.

Branch naming: `fix/` | `feat/` | `chore/`

Workflow:
1. `git checkout -b fix/description`
2. Do the work, commit normally
3. `bash scripts/pre-pr-tests.sh` — run tests, save trail
4. `git add test-trail/ && git commit -m "chore: test trail for PR"`
5. `gh pr create --title "..." --body "..."`
6. Share Vercel preview URL for QA
7. User says "merge" → `gh pr merge --squash`

Test trail is mandatory for every merged PR.

PR body format:
```
## What
One-line summary.

## Why
The problem it solves or the feature it adds.
```
No "Test plan" section. No "Generated with Claude Code" attribution.

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
- ~42 tables, 47,818 provisions in `regulatory_provisions`
- Use `v2_precinct_id` (102 precincts), NOT `dcp_precinct_provisions` (legacy)
- Common columns: `v2_topic`, `v2_marker`, `former_council`, `v2_precinct_id` — never assume column names

## Plan Files
- Location: `~/.claude/plans/`
- Prefix: `ce-` ComplianceEngine | `biz-` Business | `meta-` Cross-project
- Dashboard: `~/.claude/plans/INDEX.md`
- Pipeline ideas: `~/.claude/plans/pipeline-ideas-log.md`

## Key Reference Docs
- `DB_SCHEMA.md` — database structure (read before any DB work)
- `docs/CONFIGURATION.md` — env vars, feature flags, R2 paths, LGA checklist
- `DEPLOYMENT.md` — deploy guide
- `db-clean-tasks/README.md` — DB cleanup history
- `.claude/DATA_QUALITY_TRACKER.md` — data quality issues and fixes
