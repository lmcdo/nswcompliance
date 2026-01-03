# PlotDetect CLAUDE.md - Standing Rules

## Database Safety (NON-NEGOTIABLE)
- Run `./scripts/db_safety_check.sh` BEFORE any database work
- Create backup before ANY database operation
- NEVER run queries without WHERE clauses on main tables
- Use timeouts (30 seconds max)
- Database issues = STOP IMMEDIATELY
- **Single database: Supabase** (no sync needed, changes visible in production immediately)

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

## Reference Docs (read when relevant, not every session)
- `.claude/prp/INDEX.md` - Architecture overview
- `.claude/DATA_QUALITY_TRACKER.md` - DQ issues and fixes
- `DEPLOYMENT.md` - Deploy guide
- `frontend-nextjs/app/assessment/README.md` - UI details

## Deployment
```bash
git push  # Vercel auto-deploys from main
```
