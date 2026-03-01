# YOUR ACTION ITEMS - Deployment Checklist
**What YOU need to do on Supabase and Vercel**

---

## ⚡ QUICK START - Do These Now (30 minutes)

### Step 1: Create Supabase Project (5 minutes)

**Go to**: https://supabase.com

**Actions**:
1. Click "Start your project" → Sign up with GitHub
2. Click "New Project"
3. Fill in:
   - **Organization**: Create new (or select existing)
   - **Project name**: `nsw-planning-compliance`
   - **Database Password**: Click "Generate password" → **COPY AND SAVE THIS!**
   - **Region**: `Sydney (ap-southeast-1)` ← **IMPORTANT: Choose closest to Australia**
   - **Pricing plan**: Free
4. Click "Create new project"
5. Wait 2-3 minutes for provisioning

**What to save**:
```
Database Password: [paste here]
Project URL: [will appear after provisioning]
```

---

### Step 2: Get Supabase Connection Details (2 minutes)

**Once project is ready**:

1. Click on your project
2. Go to **Settings** (left sidebar) → **Database**
3. Scroll to "Connection string"
4. Copy these values:

```
Host: db.______________.supabase.co
Database: postgres
Port: 5432
User: postgres
Password: [the one you saved above]
```

**Save these** - you'll need them for Vercel!

---

### Step 3: Enable PostGIS in Supabase (1 minute)

1. In Supabase, click **SQL Editor** (left sidebar)
2. Click "+ New query"
3. Paste this:
   ```sql
   CREATE EXTENSION IF NOT EXISTS postgis;
   SELECT PostGIS_Version();
   ```
4. Click "Run" (or press Ctrl+Enter)
5. You should see: `3.3.2` or similar

✅ **PostGIS is now enabled!**

---

### Step 4: Export Local Database (5 minutes)

**On your computer**, open PowerShell and run:

```powershell
# Navigate to project
cd "C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine"

# Create export directory
New-Item -ItemType Directory -Force -Path "supabase-export"

# Export database
& "C:\Program Files\PostgreSQL\16\bin\pg_dump.exe" `
  -h localhost `
  -U postgres `
  -d nsw_planning `
  -f "supabase-export\database.sql" `
  --no-owner `
  --no-acl

# Check file was created
Get-Item "supabase-export\database.sql" | Select-Object Name, @{Name="SizeMB";Expression={[math]::Round($_.Length / 1MB, 2)}}
```

**Expected output**: File size ~100-150 MB

**If you see "command not found"**, PostgreSQL bin path may be different. Try:
```powershell
# Find PostgreSQL
Get-ChildItem "C:\Program Files\PostgreSQL\" -Recurse -Filter "pg_dump.exe"
```

---

### Step 5: Import Database to Supabase (10 minutes)

**Option A: Using psql (Recommended)**

```powershell
# Set password environment variable (use YOUR Supabase password)
$env:PGPASSWORD = "your-supabase-password-here"

# Import to Supabase (replace YOUR-PROJECT-ID)
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" `
  -h db.YOUR-PROJECT-ID.supabase.co `
  -U postgres `
  -d postgres `
  -f "supabase-export\database.sql"
```

**This will take 5-10 minutes**. You'll see lots of SQL statements scrolling by.

**Option B: Using Supabase SQL Editor (If psql fails)**

⚠️ **Only for small databases** (<5MB). Your database is ~150MB, so this may timeout.

1. Open `supabase-export\database.sql` in a text editor
2. Copy sections of SQL (e.g., 1000 lines at a time)
3. Paste into Supabase SQL Editor
4. Click "Run"
5. Repeat until all imported

---

### Step 6: Verify Database Import (3 minutes)

**In Supabase SQL Editor**, run these verification queries:

```sql
-- Check row counts (should match local)
SELECT 'regulatory_provisions' as table_name, COUNT(*) FROM regulatory_provisions
UNION ALL SELECT 'dcp_general_requirements', COUNT(*) FROM dcp_general_requirements
UNION ALL SELECT 'dcp_precinct_requirements', COUNT(*) FROM dcp_precinct_requirements
UNION ALL SELECT 'dcp_precinct_boundaries', COUNT(*) FROM dcp_precinct_boundaries;

-- Expected results:
-- regulatory_provisions: 48,087
-- dcp_general_requirements: 1,536
-- dcp_precinct_requirements: 1,231
-- dcp_precinct_boundaries: 90
```

```sql
-- Check indexes exist
SELECT COUNT(*) as index_count
FROM pg_indexes
WHERE schemaname = 'public'
AND indexname LIKE 'idx_%';

-- Expected: 71 or more
```

```sql
-- Test spatial query (bifurcated precinct)
SELECT precinct_id, precinct_name
FROM dcp_precinct_boundaries
WHERE ST_Contains(boundary, ST_SetSRID(ST_MakePoint(151.167823, -33.884520), 4326));

-- Expected: C2.2.1.2 Annandale Street
```

✅ **If all queries return expected results, database is ready!**

---

### Step 7: Push Code to GitHub (5 minutes)

**On your computer**, in PowerShell:

```powershell
cd "C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine"

# Initialize git (if not already done)
git init

# Create .gitignore (don't commit sensitive files)
@"
node_modules/
.env
.env.local
.env.*.local
*.db
*.backup
*.sql
output/
backups/
venv/
__pycache__/
.next/
"@ | Out-File -FilePath .gitignore -Encoding UTF8

# Add all files
git add .

# Commit
git commit -m "Initial commit - NSW Planning Compliance Engine"

# Create GitHub repo (go to github.com/new)
# Then push:
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO-NAME.git
git push -u origin main
```

**If you don't have a GitHub repo yet**:
1. Go to: https://github.com/new
2. Repository name: `nsw-planning-compliance-engine`
3. Make it **Private**
4. Don't initialize with README
5. Click "Create repository"
6. Copy the commands shown and run them

---

### Step 8: Deploy to Vercel (10 minutes)

**Go to**: https://vercel.com

**Actions**:
1. Click "Sign up" → Use GitHub
2. Click "Add New" → "Project"
3. Import your GitHub repository: `nsw-planning-compliance-engine`
4. Click "Import"

**Configure Project**:
1. **Framework Preset**: Next.js (auto-detected)
2. **Root Directory**: `frontend-nextjs` ← **IMPORTANT: Click "Edit" and set this**
3. **Build Command**: `npm run build` (default)
4. **Output Directory**: `.next` (default)
5. **Install Command**: `npm install` (default)
6. **Node.js Version**: 18.x (default)

**Add Environment Variables**:

Click "Environment Variables" and add these **7 variables**:

| Name | Value | Where to Get |
|------|-------|--------------|
| PGHOST | db.YOUR-PROJECT-ID.supabase.co | Supabase Settings → Database |
| PGDATABASE | postgres | Default |
| PGUSER | postgres | Default |
| PGPASSWORD | [your Supabase password] | Step 1 |
| PGPORT | 5432 | Default |
| GOOGLE_PLACES_API_KEY | [your Google API key] | Google Cloud Console |
| NSW_PLANNING_API_BASE_URL | https://api.apps1.nsw.gov.au/planning | Public API |

**Deploy**:
1. Click "Deploy"
2. Wait 3-5 minutes
3. You'll see build logs scrolling
4. When done, you'll get a URL like: `your-app.vercel.app`

✅ **App is now deployed!**

---

### Step 9: Test Deployment (5 minutes)

**Replace `YOUR-APP-URL` with your actual Vercel URL**:

```bash
# Test 1: Health Check
curl https://YOUR-APP-URL.vercel.app/api/health

# Expected: {"status":"ok","database":"connected"}

# Test 2: Property Lookup
curl "https://YOUR-APP-URL.vercel.app/api/property?address=180%20Addison%20Road,%20Marrickville%20NSW%202204"

# Expected: JSON with property data

# Test 3: DCP Complete
curl -X POST https://YOUR-APP-URL.vercel.app/api/compliance/dcp-complete \
  -H "Content-Type: application/json" \
  -d '{"address":"180 Addison Road, Marrickville NSW 2204","zone":"R2","developmentType":"dwelling_house","lga":"Inner West","coordinates":{"lat":-33.911,"lon":151.155}}'

# Expected: JSON with DCP provisions
```

**Or test in browser**:
1. Go to: `https://YOUR-APP-URL.vercel.app`
2. You should see the compliance dashboard
3. Enter an address: `180 Addison Road, Marrickville NSW 2204`
4. Click "Check Compliance"
5. You should see planning provisions

---

## 🎯 Success Checklist

After completing all steps, you should have:

- [ ] ✅ Supabase project created
- [ ] ✅ PostGIS enabled
- [ ] ✅ Database exported (150MB file created)
- [ ] ✅ Database imported to Supabase
- [ ] ✅ All tables verified (54,545 total rows)
- [ ] ✅ All indexes verified (71 indexes)
- [ ] ✅ Spatial queries tested
- [ ] ✅ Code pushed to GitHub
- [ ] ✅ Vercel project created
- [ ] ✅ Environment variables configured (7 vars)
- [ ] ✅ First deployment successful
- [ ] ✅ Health check passes
- [ ] ✅ Property lookup works
- [ ] ✅ DCP Complete API works

---

## 🆘 If Something Goes Wrong

### Database Export Fails
**Error**: `pg_dump: command not found`

**Fix**: Find PostgreSQL installation
```powershell
Get-ChildItem "C:\Program Files\" -Recurse -Filter "pg_dump.exe" -ErrorAction SilentlyContinue
# Use the full path in the export command
```

### Database Import Takes Forever
**Symptom**: Import running for >20 minutes

**Fix**: This is normal for large databases. Wait patiently. Check Supabase dashboard for activity.

### Vercel Build Fails
**Error**: "Build failed with exit code 1"

**Fix**:
1. Check build logs in Vercel
2. Test locally first:
   ```powershell
   cd frontend-nextjs
   npm install
   npm run build
   ```
3. Fix any TypeScript errors
4. Commit and push fix
5. Vercel will auto-redeploy

### "Database connection failed" After Deployment
**Error**: 500 errors, can't connect to database

**Fix**: Check environment variables in Vercel
1. Go to Vercel → Your Project → Settings → Environment Variables
2. Verify `PGHOST` is correct (should be `db._____.supabase.co`)
3. Verify `PGPASSWORD` is correct
4. If you change env vars, redeploy: Vercel → Deployments → Redeploy

### PostGIS Function Not Found
**Error**: `function st_contains does not exist`

**Fix**: Run in Supabase SQL Editor:
```sql
CREATE EXTENSION IF NOT EXISTS postgis;
```

---

## 📊 What to Expect

### Deployment Costs
- **Supabase Free**: $0 (sufficient for 6-12 months)
- **Vercel Hobby**: $0 (sufficient for 6-12 months)
- **Total**: $0/month

### Performance
- **Health check**: <100ms
- **Property lookup**: 1-2 seconds (external API)
- **DCP Complete**: <1s (cached) or <3s (uncached)
- **Database queries**: 50-200ms average

### Limits (Free Tier)
- **Supabase**: 500MB database (you're at 189MB = 38%)
- **Vercel**: 100GB bandwidth/month (plenty for testing)
- **Connections**: 500 concurrent (you'll use ~5-20)

---

## 🎉 After Successful Deployment

**You'll have**:
1. Production URL (e.g., `nsw-planning.vercel.app`)
2. Automatic SSL certificate (HTTPS)
3. Global CDN distribution
4. Automatic deployments on every GitHub push
5. 99.9% uptime guarantee

**Next Steps**:
1. Share the URL with testers
2. Monitor Vercel logs for 24 hours
3. Check Supabase metrics
4. Set up custom domain (optional)
5. Enable analytics (Vercel → Analytics)

---

## 💡 Pro Tips

1. **Redeploy After Env Var Changes**
   - Environment variables only apply to NEW deployments
   - After changing env vars, go to Deployments → Redeploy

2. **Check Logs**
   - Vercel: Dashboard → Your Project → Logs
   - Supabase: Dashboard → Reports

3. **Monitor Database Size**
   - Supabase: Dashboard → Database → Size
   - Alert when approaching 400MB (80% of free tier)

4. **Automatic Deployments**
   - Every `git push` to main branch = auto-deploy
   - Preview deployments for branches
   - Rollback in 1 click if issues

5. **Custom Domain**
   - Vercel → Settings → Domains
   - Add `compliance.yourdomain.com`
   - Update DNS records as instructed
   - SSL certificate automatic

---

## 📞 Need Help?

**Check These First**:
1. Full guide: `DEPLOYMENT_GUIDE_VERCEL_SUPABASE.md`
2. Quick start: `DEPLOYMENT_QUICKSTART.md`
3. Vercel docs: https://vercel.com/docs
4. Supabase docs: https://supabase.com/docs

**Common Issues**:
- Database connection: Check env vars in Vercel
- Build failures: Test `npm run build` locally first
- Slow responses: Check `/api/health/cache` endpoint

---

**Your Deployment Checklist Version**: 1.0
**Estimated Total Time**: 1-2 hours
**Difficulty**: Beginner-Friendly (Step-by-step)

🚀 **Ready to deploy? Start with Step 1!**
