# Fresh Clone Setup

Step-by-step for getting the project running from a clean clone.

## Prerequisites

- Node.js 20 LTS and npm (the lockfiles are committed)
- Python 3.11+
- Git
- Linux build tools for geospatial/Python wheels: `build-essential gdal-bin libgdal-dev libgeos-dev libproj-dev`
- Access to the Supabase project (database credentials)

## 1. Clone and configure git hooks

```bash
git clone <repo-url> compliance-engine
cd compliance-engine
git config core.hooksPath .githooks
```

The hooks enforce:
- `commit-msg` — QA tier classification required on every commit
- `pre-commit` — TypeScript error count gate (baseline 664)
- `pre-push` — Python tests + QA report validation + liability language scan

## 2. Environment variables

```bash
cp .env.example .env
# Edit .env with real values (get from Supabase dashboard + team)

cp .env.example frontend-nextjs/.env.local
# Edit frontend-nextjs/.env.local — only NEXT_PUBLIC_* and DB vars needed
```

See `docs/CONFIGURATION.md` for detailed documentation of every variable.

## 3. Python setup

```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
# OR: venv\Scripts\activate  # Windows

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-test.txt

# Verify
python -m pytest tests/ -x -q --tb=short
# Expected: ~370 tests pass in <1s (mocked, no DB needed)
```

## 4. Frontend setup

```bash
cd frontend-nextjs
npm ci
npm run dev   # Starts on http://localhost:3003
```

## 5. Python API (optional — for satellite/conveyancing pipelines)

```bash
# From project root, with venv active
uvicorn services.main:app --reload --port 8000
```

## 6. Database

The database is a live Supabase instance. Migrations are in `migrations/` (numbered SQL files). They are idempotent and applied directly:

```bash
psql $DATABASE_URL -f migrations/001_add_v2_columns.sql
# ... etc
```

For read-only exploration: connect via any PostgreSQL client using the `DATABASE_URL`.

See `DB_SCHEMA.md` for table documentation.

## 7. Verify everything works

```bash
# Tests (no DB needed)
python -m pytest tests/ -x -q

# TypeScript check
cd frontend-nextjs && npx tsc --noEmit 2>&1 | tail -1
# Expected: some errors (baseline 664) — pre-commit hook gates this

# Frontend builds
npm run build
```

## Project structure

```
services/          Python backend (FastAPI on Railway)
enrichment/        DCP extraction pipeline
frontend-nextjs/   Next.js app (Vercel)
scripts/           Utility scripts, DB helpers
tests/             pytest suite (~370 tests)
migrations/        Numbered SQL migrations
docs/              Reference documentation
.githooks/         Git hooks (commit-msg, pre-commit, pre-push)
```

## Key documentation

| Doc | Read when |
|-----|-----------|
| `CLAUDE.md` | Before any work (standing rules) |
| `DB_SCHEMA.md` | Before any database work |
| `docs/CONFIGURATION.md` | Setting up env vars |
| `DEPLOYMENT.md` | Deploying changes |
| `frontend-nextjs/CLAUDE.md` | UI work |
| `services/CLAUDE.md` | Satellite pipeline work |
| `enrichment/CLAUDE.md` | DCP extraction work |
| `docs/intelligence-brief/` | Intelligence Brief product build |
