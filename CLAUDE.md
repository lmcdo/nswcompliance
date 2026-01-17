# PlotDetect CLAUDE.md - Standing Rules

## Database Safety (NON-NEGOTIABLE)
- **Read DB_SCHEMA.md FIRST** before any database work to understand table structure
- Run `./scripts/db_safety_check.sh` BEFORE any database operation
- Create backup before ANY database operation
- NEVER run queries without WHERE clauses on main tables
- Use timeouts (30 seconds max)
- Database issues = STOP IMMEDIATELY
- **Single database: Supabase** (no sync needed, changes visible in production immediately)

## Database Quick Reference
- **Always check DB_SCHEMA.md** before writing queries
- 58 tables, 47,818 provisions in `regulatory_provisions`
- Use `v2_precinct_id` (102 precincts), NOT `dcp_precinct_provisions` (legacy, incomplete)
- SEPP Housing 2021: 241 provisions in `regulatory_provisions`, query by document_id
- Full schema details in DB_SCHEMA_RAW.txt

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

## Project Structure
- `regulatory-engine/` - RAG processing
- `compliance/` - Compliance logic
- `frontend-nextjs/` - Next.js app
- Virtual env: `venv_linux`

## Plan Mode Files
- **Location:** `~/.claude/plans/` (C:\Users\lawre\.claude\plans\)
- **Format:** `word-word-word.md` (hyphens, lowercase)
- Check here FIRST when user references a plan file

## Reference Docs (read when relevant, not every session)
- `DB_SCHEMA.md` - Database structure quick reference (READ BEFORE DB WORK)
- `.claude/prp/INDEX.md` - Architecture overview
- `.claude/DATA_QUALITY_TRACKER.md` - DQ issues and fixes
- `DEPLOYMENT.md` - Deploy guide
- `frontend-nextjs/app/assessment/README.md` - UI details

## Deployment
```bash
git push  # Vercel auto-deploys from main
```
