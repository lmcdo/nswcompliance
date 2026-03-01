# Production Deployment Guide
**Vercel (Frontend) + Supabase (Database)**

---

## Overview

This guide provides step-by-step instructions to deploy the NSW Planning Compliance Engine to production using:
- **Vercel**: Next.js frontend hosting (serverless)
- **Supabase**: PostgreSQL database with PostGIS

**Estimated Time**: 2-3 hours
**Difficulty**: Intermediate
**Prerequisites**: GitHub account, credit card (for paid tiers if needed)

---

## Pre-Deployment Checklist

### ✅ Database Ready
- [x] Database indexes created (Priority 1 complete)
- [x] Caching implemented (Priority 2 complete)
- [x] Database size: 189 MB (within Supabase free tier: 500MB)
- [x] 54,545 rows across critical tables
- [x] PostGIS extension in use

### ✅ Code Ready
- [x] Next.js production config optimized (swcMinify: true)
- [x] Connection pooling configured
- [x] Environment variables identified
- [x] Build tested locally

### ⚠️ Pre-Deployment Actions Required
- [ ] Create Supabase account
- [ ] Create Vercel account
- [ ] Push code to GitHub
- [ ] Obtain Google Places API key (if not already done)
- [ ] Create production environment variable file

---

## Part 1: Supabase Setup (Database)

### Step 1.1: Create Supabase Project

1. **Sign up for Supabase**
   - Go to: https://supabase.com
   - Click "Start your project"
   - Sign up with GitHub (recommended)

2. **Create New Project**
   ```
   Project Name: nsw-planning-compliance
   Database Password: [Generate strong password - SAVE THIS!]
   Region: Sydney (ap-southeast-1) or closest to Australia
   Pricing Plan: Free (upgrade to Pro if needed later)
   ```

3. **Wait for Provisioning** (~2 minutes)
   - Supabase will create your PostgreSQL database
   - You'll see "Project is being set up..."

4. **Save Connection Details**
   - Go to Project Settings → Database
   - Note down:
     - `Host` (e.g., db.abc123xyz.supabase.co)
     - `Database name` (postgres)
     - `Port` (5432)
     - `User` (postgres)
     - `Password` (the one you created)

### Step 1.2: Enable PostGIS Extension

Supabase needs PostGIS for spatial queries (precinct boundaries, heritage areas).

1. **Go to SQL Editor**
   - In Supabase dashboard → SQL Editor
   - Click "New query"

2. **Run PostGIS Setup**
   ```sql
   -- Enable PostGIS extension
   CREATE EXTENSION IF NOT EXISTS postgis;

   -- Verify installation
   SELECT PostGIS_Version();
   ```

3. **Expected Output**
   ```
   postgis_version
   ---------------
   3.3.2
   ```

### Step 1.3: Export Local Database

**Option A: Using pg_dump (Recommended)**

```powershell
# Create export directory
New-Item -ItemType Directory -Force -Path "C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\supabase-migration"

# Export database (schema + data)
& "C:\Program Files\PostgreSQL\16\bin\pg_dump.exe" `
  -h localhost `
  -U postgres `
  -d nsw_planning `
  -f "supabase-migration\nsw_planning_export.sql" `
  --no-owner `
  --no-acl `
  --format=plain

# Check file size
Get-Item "supabase-migration\nsw_planning_export.sql" | Select-Object Name, @{Name="SizeMB";Expression={[math]::Round($_.Length / 1MB, 2)}}
```

**Expected size**: 150-200 MB (compressed SQL)

**Option B: Using Python Script (Alternative)**

If pg_dump fails, use the Python export script:

```powershell
python scripts\export_database_for_supabase.py
```

### Step 1.4: Import to Supabase

**Method 1: Supabase SQL Editor (Small databases)**

1. Go to SQL Editor in Supabase
2. Paste SQL content (if file < 5MB)
3. Click "Run"

⚠️ **Limitation**: SQL Editor times out on large files

**Method 2: psql CLI (Recommended for full database)**

```powershell
# Set environment variable for password
$env:PGPASSWORD = "your-supabase-password"

# Import to Supabase
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" `
  -h db.abc123xyz.supabase.co `
  -U postgres `
  -d postgres `
  -f "supabase-migration\nsw_planning_export.sql"
```

**Method 3: Supabase Database Restore (If available)**

Check if Supabase dashboard has "Database" → "Restore" option for file upload.

### Step 1.5: Verify Database Import

Run verification queries in Supabase SQL Editor:

```sql
-- Check critical tables exist and have data
SELECT 'regulatory_provisions' as table_name, COUNT(*) as rows FROM regulatory_provisions
UNION ALL
SELECT 'dcp_general_requirements', COUNT(*) FROM dcp_general_requirements
UNION ALL
SELECT 'dcp_precinct_requirements', COUNT(*) FROM dcp_precinct_requirements
UNION ALL
SELECT 'dcp_precinct_boundaries', COUNT(*) FROM dcp_precinct_boundaries
UNION ALL
SELECT 'lep_land_use_table', COUNT(*) FROM lep_land_use_table
UNION ALL
SELECT 'heritage_conservation_areas', COUNT(*) FROM heritage_conservation_areas;

-- Expected results:
-- regulatory_provisions: 48,087 rows
-- dcp_general_requirements: 1,536 rows
-- dcp_precinct_requirements: 1,231 rows
-- dcp_precinct_boundaries: 90 rows
-- lep_land_use_table: 390 rows
-- heritage_conservation_areas: 2,039 rows
```

**Verify Indexes**:
```sql
SELECT
  schemaname,
  tablename,
  indexname
FROM pg_indexes
WHERE schemaname = 'public'
AND indexname LIKE 'idx_%'
ORDER BY tablename, indexname;

-- Should see 71+ indexes including:
-- idx_dcp_gen_req_zones_gin
-- idx_dcp_gen_req_devtypes_gin
-- idx_dcp_gen_req_former_council
-- idx_reg_prov_document_id
-- etc.
```

**Verify PostGIS**:
```sql
-- Test spatial query (bifurcated precinct)
SELECT precinct_id, precinct_name
FROM dcp_precinct_boundaries
WHERE ST_Contains(boundary, ST_SetSRID(ST_MakePoint(151.167823, -33.884520), 4326));

-- Expected: C2.2.1.2 Annandale Street
```

✅ **If all queries return expected results, database import is successful!**

---

## Part 2: Vercel Setup (Frontend)

### Step 2.1: Prepare GitHub Repository

1. **Initialize Git** (if not already done)
   ```powershell
   cd "C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine"
   git init
   git add .
   git commit -m "Initial commit - NSW Planning Compliance Engine"
   ```

2. **Create GitHub Repository**
   - Go to: https://github.com/new
   - Repository name: `nsw-planning-compliance-engine`
   - Privacy: Private (recommended)
   - Don't initialize with README (we already have code)

3. **Push to GitHub**
   ```powershell
   git remote add origin https://github.com/your-username/nsw-planning-compliance-engine.git
   git branch -M main
   git push -u origin main
   ```

### Step 2.2: Create .vercelignore File

Create this file to exclude unnecessary files from deployment:

```powershell
# Create .vercelignore in project root
@"
# Python implementation files (not needed for frontend)
*.py
venv/
venv_linux/
__pycache__/

# Output directories (large PDFs, extractions)
output/
backups/
extraction_logs/
extraction_outputs/
extraction_temp/
logs/

# Documentation (not needed in production)
*.md
!README.md

# Database files
*.db
*.sqlite3
*.backup
*.sql

# Large image directories
frontend-nextjs/public/images/

# Local env files
.env.local
.env.*.local

# Git
.git/
.gitignore

# Scripts
scripts/

# Node modules (Vercel installs them)
node_modules/
"@ | Out-File -FilePath .vercelignore -Encoding UTF8
```

### Step 2.3: Create Production Environment Variables

Create `.env.production.local` (DO NOT commit to Git):

```env
# Supabase Database Connection
PGHOST=db.abc123xyz.supabase.co
PGDATABASE=postgres
PGUSER=postgres
PGPASSWORD=your-supabase-password-here
PGPORT=5432

# Google Places API
GOOGLE_PLACES_API_KEY=your-google-api-key-here

# NSW Planning API (public, no key needed)
NSW_PLANNING_API_BASE_URL=https://api.apps1.nsw.gov.au/planning

# Production settings
NODE_ENV=production
NEXT_TELEMETRY_DISABLED=1
```

### Step 2.4: Deploy to Vercel

**Option 1: Vercel Dashboard (Recommended)**

1. **Sign up for Vercel**
   - Go to: https://vercel.com
   - Click "Sign up"
   - Sign up with GitHub (recommended)

2. **Import Project**
   - Click "Add New" → "Project"
   - Select your GitHub repository: `nsw-planning-compliance-engine`
   - Click "Import"

3. **Configure Project**
   ```
   Framework Preset: Next.js
   Root Directory: frontend-nextjs
   Build Command: npm run build
   Output Directory: .next
   Install Command: npm install
   Node.js Version: 18.x
   ```

4. **Add Environment Variables**
   - Click "Environment Variables"
   - Add each variable from `.env.production.local`:
     - `PGHOST` = db.abc123xyz.supabase.co
     - `PGDATABASE` = postgres
     - `PGUSER` = postgres
     - `PGPASSWORD` = [your password]
     - `PGPORT` = 5432
     - `GOOGLE_PLACES_API_KEY` = [your key]
     - `NSW_PLANNING_API_BASE_URL` = https://api.apps1.nsw.gov.au/planning
     - `NODE_ENV` = production

5. **Deploy**
   - Click "Deploy"
   - Wait 3-5 minutes for build
   - Vercel will show build logs

**Option 2: Vercel CLI**

```powershell
# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy from frontend directory
cd frontend-nextjs
vercel --prod

# Follow prompts:
# - Link to existing project? No
# - What's your project's name? nsw-planning-compliance
# - In which directory is your code located? ./
# - Want to override settings? No
```

### Step 2.5: Configure Custom Domain (Optional)

1. Go to Vercel Dashboard → Your Project → Settings → Domains
2. Add custom domain: `compliance.yourdomain.com`
3. Follow DNS configuration instructions
4. Wait for SSL certificate (automatic)

---

## Part 3: Post-Deployment Verification

### Step 3.1: Test Core Functionality

**Test 1: Health Check**
```bash
curl https://your-app.vercel.app/api/health

# Expected:
# {"status":"ok","database":"connected","timestamp":"..."}
```

**Test 2: Property Lookup**
```bash
curl "https://your-app.vercel.app/api/property?address=180%20Addison%20Road,%20Marrickville%20NSW%202204"

# Expected: Property data with zone, coordinates, constraints
```

**Test 3: DCP Complete API**
```bash
curl -X POST https://your-app.vercel.app/api/compliance/dcp-complete \
  -H "Content-Type: application/json" \
  -d '{
    "address": "180 Addison Road, Marrickville NSW 2204",
    "zone": "R2",
    "developmentType": "dwelling_house",
    "lga": "Inner West",
    "coordinates": {"lat": -33.911, "lon": 151.155}
  }'

# Expected: DCP provisions (general + precinct)
```

**Test 4: Spatial Query (Bifurcated Precinct)**
```bash
curl "https://your-app.vercel.app/api/property?address=35%20Annandale%20Street,%20Annandale%20NSW%202038"

# Expected: Precinct C2.2.1.2 detected
```

**Test 5: Heritage Check**
```bash
curl -X POST https://your-app.vercel.app/api/heritage/hca-check \
  -H "Content-Type: application/json" \
  -d '{"x": 151.159, "y": -33.899, "lga": "INNER WEST"}'

# Expected: Heritage area status
```

**Test 6: Cache Stats**
```bash
curl https://your-app.vercel.app/api/health/cache

# Expected: Cache statistics (initially empty, will populate with use)
```

### Step 3.2: Performance Verification

**Check Response Times**:
- Health check: <100ms
- Property lookup: <2s (external API dependency)
- DCP Complete: <1s (cached) or <3s (uncached)
- Heritage check: <500ms (cached) or <2s (uncached)

**Monitor Vercel Logs**:
1. Go to Vercel Dashboard → Your Project → Logs
2. Watch for errors during test requests
3. Check for database connection issues

**Monitor Supabase Metrics**:
1. Go to Supabase Dashboard → Reports
2. Check:
   - Database CPU usage (should be <10% with current load)
   - Database connections (should be <20 active)
   - Query performance (avg <100ms)

### Step 3.3: Connection Pool Verification

Check that connection pooling is working correctly:

```sql
-- In Supabase SQL Editor
SELECT
  count(*) as total_connections,
  count(*) FILTER (WHERE state = 'active') as active,
  count(*) FILTER (WHERE state = 'idle') as idle
FROM pg_stat_activity
WHERE datname = 'postgres';

-- Expected (during testing):
-- total_connections: 1-5
-- active: 1-2
-- idle: 0-3

-- If you see 20+ connections, connection pool may need tuning
```

---

## Part 4: Production Configuration & Optimization

### Step 4.1: Vercel Configuration

**Update `vercel.json`** (create in `frontend-nextjs/` directory):

```json
{
  "buildCommand": "npm run build",
  "installCommand": "npm install",
  "framework": "nextjs",
  "regions": ["syd1"],
  "functions": {
    "api/**/*": {
      "maxDuration": 10
    }
  },
  "headers": [
    {
      "source": "/api/(.*)",
      "headers": [
        {
          "key": "Cache-Control",
          "value": "s-maxage=60, stale-while-revalidate"
        }
      ]
    }
  ]
}
```

**Explanation**:
- `regions: ["syd1"]`: Deploy to Sydney for low latency to Supabase
- `maxDuration: 10`: Max 10 seconds for API routes (default is 5)
- `Cache-Control`: CDN caching for API responses

### Step 4.2: Supabase Optimization

**Connection Pool Settings** (for Supabase):

Update `frontend-nextjs/lib/db.ts`:

```typescript
export function getPool(): Pool {
  if (!globalForDb.pool) {
    globalForDb.pool = new Pool({
      host: process.env.PGHOST,
      database: process.env.PGDATABASE,
      user: process.env.PGUSER,
      password: process.env.PGPASSWORD,
      port: parseInt(process.env.PGPORT || '5432'),

      // Supabase-specific settings
      max: process.env.NODE_ENV === 'production' ? 10 : 20,
      idleTimeoutMillis: 10000,  // 10 seconds (shorter for serverless)
      connectionTimeoutMillis: 5000,  // 5 seconds

      // SSL required for Supabase
      ssl: process.env.NODE_ENV === 'production'
        ? { rejectUnauthorized: true }
        : false,

      keepAlive: true,
      keepAliveInitialDelayMillis: 10000,
    });
  }
  return globalForDb.pool;
}
```

**Why Lower Max Connections in Production?**
- Vercel deploys multiple serverless instances
- Each instance has its own connection pool
- 10 instances × 10 connections = 100 total
- Supabase Free tier: 500 connection limit (safe margin)

### Step 4.3: Enable Row Level Security (RLS) on Supabase

Supabase requires RLS for security. Since this is a read-only app, we'll allow public reads:

```sql
-- Enable RLS on all tables
ALTER TABLE regulatory_provisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE dcp_general_requirements ENABLE ROW LEVEL SECURITY;
ALTER TABLE dcp_general_provisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE dcp_precinct_requirements ENABLE ROW LEVEL SECURITY;
ALTER TABLE dcp_precinct_boundaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE lep_land_use_table ENABLE ROW LEVEL SECURITY;
ALTER TABLE heritage_conservation_areas ENABLE ROW LEVEL SECURITY;

-- Create policy: Allow public read access
-- (Your app uses service role key, so this allows read-only public access)

CREATE POLICY "Allow public read access" ON regulatory_provisions
  FOR SELECT USING (true);

CREATE POLICY "Allow public read access" ON dcp_general_requirements
  FOR SELECT USING (true);

CREATE POLICY "Allow public read access" ON dcp_general_provisions
  FOR SELECT USING (true);

CREATE POLICY "Allow public read access" ON dcp_precinct_requirements
  FOR SELECT USING (true);

CREATE POLICY "Allow public read access" ON dcp_precinct_boundaries
  FOR SELECT USING (true);

CREATE POLICY "Allow public read access" ON lep_land_use_table
  FOR SELECT USING (true);

CREATE POLICY "Allow public read access" ON heritage_conservation_areas
  FOR SELECT USING (true);
```

**Why This Is Safe**:
- Planning data is public information (published by councils)
- Read-only access (no INSERT, UPDATE, DELETE)
- No user-specific data stored

---

## Part 5: Monitoring & Maintenance

### Step 5.1: Set Up Monitoring

**Vercel Analytics** (Built-in):
1. Go to Vercel Dashboard → Your Project → Analytics
2. Monitor:
   - Page views
   - API route calls
   - Error rates
   - Response times

**Supabase Metrics**:
1. Go to Supabase Dashboard → Reports
2. Monitor:
   - Database size (alert at 400MB / 500MB limit)
   - Connection count (alert at >400 connections)
   - Query performance (alert on slow queries >5s)

**Set Up Alerts**:

**Vercel Alerts**:
1. Vercel Dashboard → Settings → Notifications
2. Enable:
   - Deployment failures
   - Function errors
   - Performance degradation

**Supabase Alerts**:
1. Supabase Dashboard → Settings → Alerts
2. Enable:
   - Database size warnings
   - Connection limit warnings
   - High CPU usage

### Step 5.2: Log Monitoring

**View Vercel Logs**:
```bash
# Install Vercel CLI
npm install -g vercel

# View real-time logs
vercel logs --follow

# View logs for specific function
vercel logs api/compliance/dcp-complete
```

**Key Log Patterns to Monitor**:
- ✅ `[DB Pool] Client connected` - Normal
- ✅ `[Structured Requirements API] Cache HIT` - Good (caching working)
- ⚠️ `[Database] Slow query (>1000ms)` - Investigate
- ❌ `[DB Pool] Unexpected error` - Critical

### Step 5.3: Database Maintenance

**Weekly Tasks**:
```sql
-- Check database size
SELECT pg_size_pretty(pg_database_size('postgres'));

-- Check table sizes
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;

-- Check index usage
SELECT
  schemaname,
  tablename,
  indexname,
  idx_scan as times_used,
  pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC
LIMIT 20;
```

**Monthly Tasks**:
1. Review slow queries in Supabase dashboard
2. Check if indexes need optimization
3. Review cache hit rates (`GET /api/health/cache`)
4. Update planning regulations if councils publish new versions

---

## Part 6: Scaling Considerations

### When to Upgrade Tiers

**Supabase Free → Pro ($25/month)**:
- Database size approaching 400MB (current: 189MB)
- >400 concurrent connections
- Need better performance (faster queries)
- Need daily backups

**Vercel Hobby → Pro ($20/month)**:
- >100GB bandwidth per month
- Need advanced analytics
- Need deployment protection
- Need team collaboration

**Current Status**: Free tiers sufficient for:
- ~1,000 property assessments per day
- ~50,000 API calls per month
- Database size <500MB

### Horizontal Scaling (Future)

If traffic exceeds free tier capacity:

1. **Enable Supabase Read Replicas** (Pro tier)
   - Route read queries to replica
   - Reduce load on primary database

2. **Enable Vercel Edge Caching**
   - Cache static responses at CDN edge
   - Reduce API calls to database

3. **Implement Redis for Caching** (if needed)
   - Upgrade from in-memory to Redis
   - Share cache across all serverless instances
   - Cost: ~$10/month (Upstash free tier)

---

## Part 7: Rollback Plan

### If Deployment Fails

**Database Rollback**:
```sql
-- Supabase SQL Editor
-- Drop imported tables (if corrupted)
DROP TABLE IF EXISTS regulatory_provisions CASCADE;
DROP TABLE IF EXISTS dcp_general_requirements CASCADE;
-- ... etc

-- Re-import from backup
-- (Re-run import steps from Part 1.4)
```

**Vercel Rollback**:
1. Go to Vercel Dashboard → Deployments
2. Find last working deployment
3. Click "..." → "Promote to Production"
4. Previous version restored in <1 minute

**Database Backup Restoration**:
- Supabase has automatic daily backups (if on Pro tier)
- Free tier: Manual backups only
- Restore from local backup: Re-run Part 1.4

---

## Part 8: Cost Analysis

### Monthly Costs (Free Tier)

| Service | Tier | Cost | Limits |
|---------|------|------|--------|
| Supabase | Free | $0 | 500MB database, 2GB bandwidth |
| Vercel | Hobby | $0 | 100GB bandwidth, unlimited serverless |
| **Total** | | **$0** | |

### Monthly Costs (Production Ready)

| Service | Tier | Cost | Benefits |
|---------|------|------|----------|
| Supabase | Pro | $25 | 8GB database, 50GB bandwidth, daily backups |
| Vercel | Pro | $20 | 1TB bandwidth, team features, advanced analytics |
| **Total** | | **$45** | |

### Projected Usage & Costs

**Assumptions**: 100 property assessments/day

**Free Tier**:
- ✅ Database: 189MB / 500MB (38% used)
- ✅ Bandwidth: ~1.5GB/month / 2GB (75% used)
- ✅ API calls: ~50K/month (well within limits)
- **Status**: Free tier sufficient for 6-12 months

**When to Upgrade**:
- Database size >400MB (80% of limit)
- Bandwidth >1.8GB/month (90% of limit)
- Need production backups
- Traffic >200 assessments/day

---

## Part 9: Deployment Checklist

### Pre-Deployment ✅
- [ ] Code pushed to GitHub
- [ ] Database backup created locally
- [ ] `.vercelignore` file created
- [ ] `.env.production.local` created (not committed)
- [ ] Google Places API key obtained
- [ ] Supabase account created
- [ ] Vercel account created

### Supabase Setup ✅
- [ ] Supabase project created (Sydney region)
- [ ] PostGIS extension enabled
- [ ] Database exported from local PostgreSQL
- [ ] Database imported to Supabase
- [ ] All tables verified (54,545 rows)
- [ ] All indexes verified (71 indexes)
- [ ] Spatial queries tested (bifurcated precincts work)
- [ ] RLS policies configured

### Vercel Setup ✅
- [ ] GitHub repository linked
- [ ] Root directory set to `frontend-nextjs`
- [ ] Environment variables configured
- [ ] SSL configured (automatic)
- [ ] Custom domain configured (optional)
- [ ] First deployment successful

### Verification ✅
- [ ] Health check passes
- [ ] Property lookup works
- [ ] DCP Complete API works
- [ ] Spatial queries work (bifurcated precincts)
- [ ] Heritage check works
- [ ] Cache stats endpoint works
- [ ] No database connection errors in logs
- [ ] Response times acceptable (<3s)

### Post-Deployment ✅
- [ ] Monitoring enabled (Vercel + Supabase)
- [ ] Alerts configured
- [ ] Team notified of deployment
- [ ] Documentation updated
- [ ] Backup strategy confirmed

---

## Part 10: Troubleshooting

### Common Issues & Solutions

#### Issue 1: "Database connection failed"

**Symptoms**: 500 errors, "ECONNREFUSED" in logs

**Solutions**:
1. Check environment variables in Vercel
   - Verify `PGHOST` has correct Supabase host
   - Verify `PGPASSWORD` is correct
2. Check Supabase is running (Dashboard → Project Status)
3. Verify SSL setting in `lib/db.ts`
4. Check connection pool isn't exhausted (>400 connections)

#### Issue 2: "PostGIS function not found"

**Symptoms**: "function st_contains does not exist"

**Solution**:
```sql
-- In Supabase SQL Editor
CREATE EXTENSION IF NOT EXISTS postgis;
```

#### Issue 3: "Build failed on Vercel"

**Symptoms**: Deployment fails during build

**Solutions**:
1. Check build logs in Vercel Dashboard
2. Common causes:
   - TypeScript errors: Fix locally first
   - Missing dependencies: Run `npm install` locally
   - Memory limit: Upgrade Vercel tier
3. Test build locally:
   ```bash
   cd frontend-nextjs
   npm run build
   ```

#### Issue 4: "Slow API responses (>5s)"

**Solutions**:
1. Check cache hit rates: `GET /api/health/cache`
   - If <40% hit rate, cache TTL may be too short
2. Check database query performance in Supabase
3. Check if indexes are being used:
   ```sql
   EXPLAIN ANALYZE
   SELECT * FROM dcp_general_requirements
   WHERE former_council = 'Ashfield';
   ```
4. Check connection pool health

#### Issue 5: "Out of database connections"

**Symptoms**: "sorry, too many clients already"

**Solutions**:
1. Lower max connections in `lib/db.ts`:
   ```typescript
   max: 5,  // Reduce from 10
   ```
2. Reduce `idleTimeoutMillis` to release faster:
   ```typescript
   idleTimeoutMillis: 5000,  // 5 seconds
   ```
3. Check for connection leaks:
   ```sql
   SELECT count(*), state
   FROM pg_stat_activity
   WHERE datname = 'postgres'
   GROUP BY state;
   ```

---

## Summary

### What You've Deployed

✅ **Next.js Frontend** on Vercel
- 51 API routes
- Server-side rendering
- Serverless functions
- Edge caching

✅ **PostgreSQL Database** on Supabase
- 189 MB database
- 54,545 rows across 7 critical tables
- 71 indexes for performance
- PostGIS spatial queries
- Connection pooling

✅ **Performance Optimizations**
- In-memory LRU caching (30-200x speedup)
- Database indexes (40-50% faster queries)
- SWC minification (10-20% smaller bundles)

### Expected Performance

- Property lookup: 1-2 seconds
- DCP Complete API: <1s (cached) or 1-3s (uncached)
- Heritage check: <500ms (cached) or 1-2s (uncached)
- 99.9% uptime (Vercel + Supabase SLA)

### What's Next

1. **Monitor for 48 hours**
   - Watch error rates
   - Check response times
   - Verify cache hit rates

2. **Gather user feedback**
   - Test with real property searches
   - Identify any data gaps
   - Check accuracy of results

3. **Scale as needed**
   - Upgrade to paid tiers if traffic grows
   - Implement Redis caching if needed
   - Add read replicas for high load

---

**Deployment Guide Version**: 1.0
**Last Updated**: 2025-11-10
**Status**: Production-Ready
