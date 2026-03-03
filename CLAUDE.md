# PlotDetect CLAUDE.md - Standing Rules

## ⛔ CRITICAL - READ FIRST ⛔
- **NEVER use `taskkill //IM node.exe`** - kills Claude Chat server
- **Kill Next.js dev server by PORT only**: `netstat -ano | findstr :3003` then `taskkill /F /PID <PID>`
- **NEVER run queries without WHERE clauses** on main tables
- **NEVER create fake/placeholder data** - ask if real data unavailable
- **BEFORE FIXING ANY UI BUG:** Read `frontend-nextjs/COMPONENT_MAP.md` to find the ACTUAL component being used
- **BEFORE ANY LGA ONBOARDING WORK:** Read `docs/DCP_EXTRACTION_KNOWN_PATTERNS.md` — covers all known artifact classes, pre-import QA checklist, and onboarding sequence. Also read `frontend-nextjs/lib/dcp-format-configs.ts` to see existing council patterns.

## Investigation Before Action (NON-NEGOTIABLE)
- **ALWAYS investigate thoroughly BEFORE making changes or proposing solutions**
- Never assume - check actual tables, columns, and data first
- Do NOT jump to implementation until you have confirmed your understanding with evidence
- When asked to explore or plan, stay in exploration/planning mode until explicitly told to implement
- **Pattern:** Read files → Check database schema/data → Show findings → Get confirmation → THEN act
- If uncertain about column names, table structure, or data state: STOP and CHECK first

## Keep It Simple (NON-NEGOTIABLE)
- When the user has already identified specific records/items to change, apply the change directly
- Do NOT over-engineer solutions with pattern-matching scripts, regex analyzers, or complex pipelines when a simple direct operation is what's needed
- Do NOT make redundant API calls or re-fetch data that is already available
- Ask yourself: "Is there a simpler way to do exactly what the user asked?"
- **Example:** If user says "818 records with condition X are bad, mark them Y" → just UPDATE those records directly, don't build a detection script

## Database Safety (NON-NEGOTIABLE)
- **Read DB_SCHEMA.md FIRST** before any database work to understand table structure
- Run `./scripts/db_safety_check.sh` BEFORE any database operation
- Create backup before ANY database operation
- **NEVER use TRUNCATE, DROP, or CASCADE** operations without explicit user confirmation
- NEVER run queries without WHERE clauses on main tables
- Verify target table and row count BEFORE DELETE/UPDATE operations
- Use timeouts (30 seconds max)
- Database issues = STOP IMMEDIATELY
- **Single database: Supabase** (no sync needed, changes visible in production immediately)

## Reuse Existing Data
- When the API or frontend already has data available (from a previous fetch, passed as props, or in session state), use it directly
- Do NOT make redundant API calls or re-fetch data that is already accessible
- Check what data is already available before writing new fetch logic
- **Example:** If provision data is already in the component props, don't fetch it again from the API

## Database Quick Reference
- **Always check DB_SCHEMA.md** before writing queries
- ~42 tables (after 2026-02 cleanup), 47,818 provisions in `regulatory_provisions`
- Use `v2_precinct_id` (102 precincts), NOT `dcp_precinct_provisions` (legacy, incomplete)
- SEPP Housing 2021: 241 provisions in `regulatory_provisions`, query by document_id
- Full schema details in DB_SCHEMA_RAW.txt
- **DB Cleanup:** See `db-clean-tasks/README.md` for cleanup history and scripts

## Data Integrity (NON-NEGOTIABLE)
- **NEVER create fake, placeholder, or "approximate" data**
- NEVER guess coordinates, boundaries, addresses, or real-world data
- If data unavailable from API/database/file: STOP and ASK
- When blocked: ASK instead of taking shortcuts
- Data quality issues are NEVER "optional" - workarounds don't excuse corruption
- >2% affected data = Priority 1, must fix before "complete"

## Geographic/Boundary Data
- Use existing scripts (e.g., `extract_precinct_boundaries.py`) as methodology
- Use real APIs (NSW Planning Portal, geocoding) for coordinates
- NEVER create rectangular approximations or made-up lat/lon

## Code Standards
- Python: PEP8, type hints, black, pydantic, Google-style docstrings
- TypeScript: for Next.js frontend
- Max 500 lines per file - refactor if approaching
- Tests: pytest in `/tests`, cover expected use + edge case + failure case
- Deterministic processing only - NO AI interpretation of regulations

## UI Copy
- Never truncate words in labels
- Use full prose: "429 provisions in this section" not "429 in section"
- Labels must be self-explanatory without context

## AI Behavior
- Ask questions if uncertain - never assume
- Never hallucinate libraries/functions
- Confirm file paths exist before referencing
- Never delete/overwrite code unless explicitly instructed
- Never interpret regulations - only extract exact clauses
- Don't use markdown tables in chat responses

## UI Bug Debugging Protocol (MANDATORY)
**When user reports UI showing wrong data:**
1. Read `frontend-nextjs/COMPONENT_MAP.md` FIRST
2. Look up the route/view → find which component renders it
3. Call production API with EXACT user parameters to verify data
4. Search codebase for exact UI text pattern to confirm component
5. Fix ONLY the component identified in step 2
6. Update COMPONENT_MAP.md if component tree has changed

**NEVER guess which component is used. ALWAYS use COMPONENT_MAP.md.**

## Project Structure
- `regulatory-engine/` - RAG processing
- `compliance/` - Compliance logic
- `frontend-nextjs/` - Next.js app
- Virtual env: `venv_linux`

## Project Stack & Domain Context
- **Languages:** Python (backend/ETL/scripts), TypeScript (frontend/compliance engine)
- **Database:** Supabase (PostgreSQL) - single production database
- **Domain:** Regulatory compliance engine for Australian council planning provisions (LEP, DCP, SEPP)
- **Key tables:** `regulatory_provisions` (47,818 rows with columns: v2_topic, v2_marker, v2_is_actionable, former_council, pdf_page, document_id, precinct_id), `documents`, `heritage_conservation_areas`, `precincts`
- **Common columns to check:** v2_topic (not "topic"), v2_marker (not "marker"), former_council (not "council"), v2_precinct_id (not "precinct_id")
- **Never assume column names** - always check DB_SCHEMA.md or query information_schema.columns first

## Plan Mode Files
- **Location:** `~/.claude/plans/` (C:\Users\lawre\.claude\plans\)
- **Prefix convention:** `ce-` ComplianceEngine | `pd-` PlotDetect | `biz-` Business/Strategy | `meta-` Cross-project
- **Format:** `{prefix}-descriptive-name.md` (hyphens, lowercase)
- **Dashboard:** `~/.claude/plans/INDEX.md`
- Check here FIRST when user references a plan file

## Reference Docs (read when relevant, not every session)
- `DB_SCHEMA.md` - Database structure quick reference (READ BEFORE DB WORK)
- `db-clean-tasks/README.md` - DB cleanup history (2026-02: dropped 16 tables)
- `.claude/prp/INDEX.md` - Architecture overview
- `.claude/DATA_QUALITY_TRACKER.md` - DQ issues and fixes
- `docs/DCP_EXTRACTION_KNOWN_PATTERNS.md` - Known artifact classes + pre-import QA checklist (READ AT START OF EVERY NEW LGA ONBOARDING)
- `DEPLOYMENT.md` - Deploy guide
- `frontend-nextjs/app/assessment/README.md` - UI details
- `docs/screencasts/INDEX.md` - Screencast scripts index
- `docs/user-stories/` - User story documents
- `docs/DCP_MONITORING.md` - DCP chapter PDF versioning & monitoring system (R2, dcp_chapter_registry, GitHub Actions)

## Deployment
```bash
git push  # Vercel auto-deploys from main
```
