# Deployment Guide

## Database Architecture

### Two Database Environments

| Environment | Purpose | Connection |
|------------|---------|------------|
| **Local PostgreSQL** | Development & Testing | `localhost:5432/nsw_planning` |
| **Supabase (Production)** | Production deployment | `aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres` |

### Environment Files

| File | Purpose | Used By |
|------|---------|---------|
| `.env` | Root config for Python scripts | Python extraction/enrichment scripts |
| `frontend-nextjs/.env.local` | Local development | Next.js app (local) |
| `frontend-nextjs/.env.vercel.final` | Production | Vercel deployment |

## Syncing Local and Supabase Databases

### Strategy: Local-First Development

1. **Develop locally** against local PostgreSQL
2. **Run migrations** on Supabase when ready to deploy
3. **Export enriched data** to production

### Option A: Run Migrations on Supabase

```bash
# Connect to Supabase and run migration
psql "postgresql://postgres.llzdrxywpziewrzudwhj:PASSWORD@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres" -f migrations/001_add_v2_columns.sql
```

### Option B: Full Database Sync (Local to Supabase)

```bash
# Export local database
pg_dump -h localhost -U postgres -d nsw_planning > nsw_planning_export.sql

# Import to Supabase (WARNING: This replaces ALL data)
psql "postgresql://postgres.llzdrxywpziewrzudwhj:PASSWORD@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres" < nsw_planning_export.sql
```

### Option C: Selective Table Sync (Recommended)

For syncing just the enriched v2_ columns:

```bash
# Export just regulatory_provisions with v2_ columns
psql -h localhost -U postgres -d nsw_planning -c "\COPY (
  SELECT id, v2_is_actionable, v2_dcp_layer, v2_dcp_part, v2_topic,
         v2_provision_type, v2_precinct_id, v2_marker, v2_display_behavior,
         v2_applicable_zones, v2_applicable_dev_types, v2_site_condition_required,
         v2_has_numeric_value
  FROM regulatory_provisions
  WHERE v2_is_actionable = true
) TO 'v2_provisions_export.csv' WITH CSV HEADER"

# Then use Supabase dashboard CSV import or custom import script
```

## Migration Files

All schema changes are tracked in `migrations/`:

| File | Description |
|------|-------------|
| `001_add_v2_columns.sql` | Adds v2_ columns for 4-layer filtering (idempotent) |

**Important:** Migrations are idempotent (safe to run multiple times).

## Deployment Checklist

### Code Deployment (Vercel)

1. [ ] Merge feature branch to `main`
2. [ ] Vercel auto-deploys from `main`
3. [ ] Verify environment variables in Vercel dashboard

### Database Deployment (Supabase)

1. [ ] Run any pending migrations on Supabase:
   ```bash
   psql $SUPABASE_URL -f migrations/001_add_v2_columns.sql
   ```
2. [ ] Sync enriched data (v2_ columns) if needed
3. [ ] Verify data in Supabase dashboard

### Verification

1. [ ] Test API endpoint: `GET /api/provisions/for-property?zone=R2`
2. [ ] Verify provision counts match local
3. [ ] Test filter cascade: zone -> dev_type -> CDC

## Environment Variables Required

### For Next.js (Vercel)

```env
DATABASE_URL=postgresql://postgres.xxx:PASSWORD@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres
```

### For Python Scripts

Add to `.env`:
```env
# Supabase connection for production scripts
SUPABASE_DB_URL=postgresql://postgres.xxx:PASSWORD@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres

# Local connection (existing)
PGHOST=localhost
PGPORT=5432
PGDATABASE=nsw_planning
PGUSER=postgres
PGPASSWORD=postgres
```

## Feature Branch Strategy

Current branch: `feature/provision-based-architecture`

### Files Modified in This Feature

**API:**
- `frontend-nextjs/app/api/provisions/for-property/route.ts` - 4-layer filtering API

**Components:**
- `frontend-nextjs/components/compliance/ProvisionsByTopic.tsx` - Topic-grouped display

**Page Integration:**
- `frontend-nextjs/app/assessment/page.tsx` - View toggle integration

**Documentation:**
- `.claude/prp/INDEX.md` - Implementation status
- `PROVISION_BASED_ARCHITECTURE_STRATEGY.md` - Architecture docs

**Migrations:**
- `migrations/001_add_v2_columns.sql` - Schema changes

## Backup Strategy

### Before Any Migration

```bash
# Full backup
pg_dump -h localhost -U postgres -d nsw_planning > backups/nsw_planning_$(date +%Y%m%d).sql

# Or just v2 columns
python backup_after_4layer.py
```

### Production Backup (Supabase)

Use Supabase dashboard: Settings > Database > Backups
