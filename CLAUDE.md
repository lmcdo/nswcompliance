### CRITICAL: Primary Directive (READ FIRST)
- **MANDATORY**: Always read `CLAUDE_PRIMARY_DIRECTIVE.md` at the start of EVERY session
- **MANDATORY**: Always read `MCP_SERVER_CONFIGURATION.md` BEFORE touching MCP configs
- **EXECUTION RULE**: One PRP per session - NO EXCEPTIONS
- **MAIN REFERENCE**: `documentation/prps/PRP-A_MICRO_PIPELINE_IMPLEMENTATION.md`
- **SESSION CONTROL**: Run `./prp_checkpoints/session_control.sh` to check next PRP

### PROVISION-BASED ARCHITECTURE (Active Implementation)
When working on **provision extraction, compliance API, filtering, or enrichment**:
- **READ FIRST**: `.claude/prp/INDEX.md` - Quick reference with architecture diagram
- **DATA QUALITY**: `.claude/DATA_QUALITY_TRACKER.md` - Current issues and fix progress
- **FULL DOCS**: `PROVISION_BASED_ARCHITECTURE_STRATEGY.md` - 8-part implementation guide
- **KEY INSIGHT**: Planning Portal API drives automatic filtering (Part 1 is THE CORE)
- **Data Model**: New `v2_` columns on `regulatory_provisions` table
- **MANDATORY**: After completing ANY phase, UPDATE `.claude/prp/INDEX.md` Implementation State table
- **TEST QUALITY**: Run `python test_workflow_quality.py` to assess current data quality

### PRIMARY UI ROUTES (Quick Reference)
- **Main Assessment Page**: `/assessment` (`frontend-nextjs/app/assessment/page.tsx`)
  - 2-column layout: Planning API data (left) + SEPP/LEP/DCP provisions (right)
  - Right column: ComplianceDashboard shows unfiltered provisions from database
  - See: `frontend-nextjs/app/assessment/README.md` for details
- **Dashboard Alternative**: `/assessment/dashboard` (same functionality, different entry point)

### DATABASE SAFETY - READ FIRST
- **NEVER connect to database without reading this section**
- **ALWAYS run `./scripts/db_safety_check.sh` BEFORE any database work**
- **ALWAYS create backup before ANY database operation**
- **NEVER run queries without WHERE clauses on main tables**
- **ALWAYS use timeouts (30 seconds max)**
- **ALWAYS use `db_safety_wrapper.py` for database connections**
- **Database issues = STOP IMMEDIATELY**

### SINGLE DATABASE: SUPABASE
**All components now use Supabase as the single source of truth. No sync needed.**

| Component | Database |
|-----------|----------|
| Frontend local dev | Supabase |
| Production (Vercel) | Supabase |
| Python scripts | Supabase |

Connection is configured in `.env` and `frontend-nextjs/.env.local`.

### Memory Aid for Claude:
1. All database operations go to Supabase directly
2. No local PostgreSQL needed
3. Changes are immediately visible in production

### DEPLOYMENT (Code Only)
- **FULL DOCS**: `DEPLOYMENT.md` - Complete deployment guide
- **MIGRATIONS**: `migrations/` folder contains all schema changes

#### Deployment is just code:
```bash
git push  # Vercel auto-deploys
```

Database changes go directly to Supabase - no sync step needed.

#### CI/CD Actions (Repeatable):
- **Schema changes**: Add new migration to `migrations/`, run on both local and Supabase
- **Data enrichment**: Run locally first, then `sync_v2_to_supabase.py`
- **Code deploy**: Push to `main`, Vercel auto-deploys
- **Rollback**: Use Supabase dashboard backups or `backups/` folder

### DATA INTEGRITY - NEVER CREATE FAKE DATA
- **CRITICAL: NEVER create fake, placeholder, or "approximate" data**
- **NEVER guess coordinates, boundaries, addresses, or any real-world data**
- **NEVER use made-up values when real data is unavailable**
- **If you cannot obtain real data from an API, database, or file: STOP and ASK the user**
- **When you hit a roadblock (API fails, geocoding fails, etc.): ASK instead of taking shortcuts**
- **"Approximate" or "placeholder" data is NEVER acceptable - it's the same as fake data**

### DATA QUALITY - NON-NEGOTIABLE STANDARDS
- **CRITICAL: Data quality issues are NEVER "optional" or "low priority"**
- **DO NOT deprioritize data quality issues because workarounds exist**
- **DO NOT call database corruption "optional" because one component bypasses it**
- **Malformed data in core tables is a STRUCTURAL FAILURE, not a cosmetic issue**

#### Anti-Pattern: Expedience Bias
**WRONG:** "99% of provisions are malformed, but LLM categorization worked despite it, so fixing is optional/low priority"
**RIGHT:** "99% of provisions are malformed. This is Priority 1 regardless of workarounds because:
  1. Future features will inherit garbage data
  2. Database integrity is foundational
  3. Users may see malformed data in other UIs
  4. Search/indexing is affected
  5. Professional credibility is undermined"

#### Data Quality Decision Matrix
When evaluating data issues, answer these questions:
1. **Does this affect a core data table?** (regulatory_provisions, dcp_precinct_provisions, etc.)
   - YES = Priority 1 or 2, NEVER optional
2. **What percentage of data is affected?**
   - >2% = Priority 1
   - 0.5-2% = Priority 2
   - <0.5% = Priority 3
3. **Do workarounds exist?**
   - **IRRELEVANT** - workarounds don't excuse data corruption
4. **Could future features use this data?**
   - If YES = Must be fixed before "complete"

#### Example: PDF Header Malformation
- **Affected:** 54.7% of all Marrickville DCP provisions (646 of 1,182)
- **Pattern:** First 150 chars are PDF page headers, not content
- **Workaround exists:** LLM categorization bypasses by reading through garbage
- **CORRECT PRIORITY:** Priority 1 (not optional!)
- **Reasoning:** Core table corruption affecting majority of data

#### Never Say:
- ❌ "Low priority - categorized requirements bypass this"
- ❌ "Optional - LLM worked despite malformation"
- ❌ "Can wait - users see structured data not raw text"

#### Always Say:
- ✅ "Priority 1 - 50%+ of core table data is malformed"
- ✅ "Must fix before v1 - database integrity is foundational"
- ✅ "Blocking issue - future features will inherit this corruption"

### Geographic/Boundary Data Rules:
1. **ALWAYS use existing scripts** (like `extract_precinct_boundaries.py`) as the methodology
2. **ALWAYS use real APIs** (NSW Planning Portal, geocoding services) for coordinate data
3. **If a script exists for a task, READ IT FIRST and follow its approach exactly**
4. **NEVER create rectangular approximations** - real boundaries are irregular and follow streets/features
5. **NEVER make up lat/lon coordinates** - every coordinate must come from a verified source
6. **Check existing code** in the repo before implementing - the correct method likely already exists

### When Blocked - Proper Response:
**DON'T DO THIS:** "Geocoding failed, so I'll create approximate rectangles as placeholders"
**DO THIS:** "Geocoding failed. I see `extract_precinct_boundaries.py` uses NSW Planning Portal API. Should I use that method to get real coordinates? I will NOT create fake/approximate boundaries."

### Project Awareness & Context 
- **Always read `PLANNING.md`** at the start of a new conversation to understand the project's architecture, goals, style, and constraints.
- **Check `TASK.md`** before starting a new task. If the task isn't listed, add it with a brief description and today's date.
- **Use consistent naming conventions, file structure, and architecture patterns** as described in `PLANNING.md`.
- **Use venv_linux** (the virtual environment) whenever executing Python commands.

### Code Structure & Modularity
- **Never create a file longer than 500 lines of code.** If a file approaches this limit, refactor by splitting it into modules or helper files.
- **Organize code into clearly separated modules**:
 - `regulatory-engine/` - RAG-Anything processing
 - `compliance/` - Compliance checking logic
- **Use clear, consistent imports** (prefer relative imports within packages).
- **Use python_dotenv and load_env()** for environment variables.

### Testing & Reliability
- **Always create Pytest unit tests for new features**
- **Tests should live in a `/tests` folder** mirroring the main app structure.
 - Include at least:
 - 1 test for expected use
 - 1 edge case
 - 1 failure case

### Task Completion
- **Mark completed tasks in `TASK.md`** immediately after finishing them.
- Add new sub-tasks or TODOs discovered during development to `TASK.md` under "Discovered During Work".

### Style & Conventions
- **Use Python** for regulatory processing, TypeScript for Next.js integration
- **Follow PEP8**, use type hints, and format with `black`.
- **Use `pydantic` for data validation**.
- **Deterministic processing only** - NO AI interpretation of regulations
- Write **docstrings for every function** using the Google style

### UI Copy & Labels
- **Never truncate or elide words** in user-facing labels and descriptions
- **Use full prose for human beings** - write complete, clear sentences
- **BAD**: "429 in section", "558 total"
- **GOOD**: "429 provisions in this section", "558 total provisions for this property"
- Labels should be self-explanatory without requiring context or guesswork

### Documentation & Explainability
- **Update `README.md`** when new features are added
- **Comment non-obvious code** and ensure everything is understandable
- When writing complex logic, **add an inline `# Reason:` comment**

### AI Behavior Rules
- **Never assume missing context. Ask questions if uncertain.**
- **Never hallucinate libraries or functions** – only use known, verified Python packages.
- **Always confirm file paths and module names** exist before referencing them
- **Never delete or overwrite existing code** unless explicitly instructed
- **Never interpret regulations** - only extract and apply exact clauses
- **Never claim AI is interpreting regulations** - only retrieving exact clauses
- **Only use constraints that map to existing data fields** in the app
- dont use markdown tables in chat