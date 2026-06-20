# Final Import Solution - pgAdmin (Most Reliable)
**NSW Planning Compliance Engine → Supabase**

---

## Why pgAdmin?

After multiple failed attempts with:
- ❌ psql (DNS resolution issues)
- ❌ IPv6 direct connection (no IPv6 on system)
- ❌ Supabase CLI (npm install no longer supported, Node.js version issues)
- ❌ SQL Editor (56MB chunk too large)

**pgAdmin is the most reliable option** because:
- ✅ GUI tool with better connection handling
- ✅ Handles large files (89MB is fine)
- ✅ Works around DNS issues better than psql
- ✅ Free and easy to install
- ✅ Single-click import

---

## Step 1: Download and Install pgAdmin (5 minutes)

### Download
**URL**: https://www.pgadmin.org/download/pgadmin-4-windows/

**Or direct link**: https://ftp.postgresql.org/pub/pgadmin/pgadmin4/v8.12/windows/pgadmin4-8.12-x64.exe

### Install
1. Run the installer
2. Accept defaults
3. Set a master password (you'll need this once)
4. Wait for installation to complete

---

## Step 2: Connect to Supabase (2 minutes)

### Open pgAdmin
Launch pgAdmin 4 from Start Menu

### Add Supabase Server

1. **Right-click "Servers"** in left panel → **Register** → **Server**

2. **General Tab**:
   - Name: `Supabase - complianceProject`

3. **Connection Tab**:
   - Host: `db.llzdrxywpziewrzudwhj.supabase.co`
   - Port: `5432`
   - Maintenance database: `postgres`
   - Username: `postgres`
   - Password: `REDACTED_MOVED_TO_ENV`
   - ✅ Save password

4. **SSL Tab**:
   - SSL mode: `Prefer`

5. **Click "Save"**

### Test Connection
You should see "Supabase - complianceProject" appear in the left panel with a green checkmark.

---

## Step 3: Import Database (10-15 minutes)

### Navigate to Database

1. Expand **Supabase - complianceProject** in left panel
2. Expand **Databases**
3. Right-click **postgres** database
4. Select **Restore...**

### Configure Restore

**Restore Dialog**:

1. **Filename**:
   - Click folder icon
   - Navigate to: `C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\supabase-export\`
   - Select: `database_cleaned.sql`

2. **Format**: `Plain`

3. **Role name**: `postgres`

4. **Options tab** (important):
   - ✅ Check: `Clean before restore` (removes existing objects)
   - ✅ Check: `Ignore errors` (continues on minor errors)
   - ✅ Check: `Verbose messages` (shows progress)

5. **Click "Restore"**

### Monitor Progress

A progress window will show:
- SQL statements being executed
- Tables being created
- Data being inserted

**Expected time**: 10-15 minutes for 89MB file

### Success Indicators

You'll see messages like:
```
Processing object type SCHEMA
Processing object type EXTENSION
Processing object type TABLE
Processing object type CONSTRAINT
Processing object type INDEX
Processing object type TRIGGER
...
Restore completed successfully
```

---

## Step 4: Verify Import (5 minutes)

### Run Verification Query

1. In pgAdmin, right-click **postgres** database
2. Select **Query Tool**
3. Paste this query:

```sql
SELECT 'regulatory_provisions' as table_name, COUNT(*) as row_count
FROM regulatory_provisions
UNION ALL
SELECT 'dcp_general_requirements', COUNT(*)
FROM dcp_general_requirements
UNION ALL
SELECT 'dcp_precinct_requirements', COUNT(*)
FROM dcp_precinct_requirements
UNION ALL
SELECT 'lep_provisions', COUNT(*)
FROM lep_provisions
UNION ALL
SELECT 'spatial_precincts', COUNT(*)
FROM spatial_precincts
UNION ALL
SELECT 'heritage_conservation_areas', COUNT(*)
FROM heritage_conservation_areas
UNION ALL
SELECT 'version_tracking', COUNT(*)
FROM version_tracking;
```

4. Click **Execute** (F5)

### Expected Results

```
table_name                     | row_count
-------------------------------|----------
regulatory_provisions          | 48,087
dcp_general_requirements       | 1,536
dcp_precinct_requirements      | 1,231
lep_provisions                 | 1,846
spatial_precincts              | ~20
heritage_conservation_areas    | ~1,825
version_tracking               | 10+
```

**Total**: ~54,545 rows

### Verify PostGIS

```sql
SELECT PostGIS_Version();
```

Should return version info (e.g., `3.4.2`)

### Test Spatial Query

```sql
SELECT name, suburb, precinct_number
FROM spatial_precincts
WHERE lga = 'Inner West'
LIMIT 5;
```

Should return precinct data.

---

## Step 5: Deploy to Vercel (15 minutes)

Once database is verified, proceed with Vercel deployment.

### Push Code to GitHub

```powershell
cd "C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine"

# Create .gitignore
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
supabase-export/
"@ | Out-File -FilePath .gitignore -Encoding UTF8

# Commit
git add .
git commit -m "feat: NSW Planning Compliance Engine - Production Ready"

# Push (create repo first at github.com/new)
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO.git
git push -u origin main
```

### Deploy to Vercel

1. Go to: https://vercel.com
2. Sign in with GitHub
3. Click **"Add New"** → **"Project"**
4. Import your GitHub repository
5. Configure:
   - Framework: Next.js (auto-detected)
   - **Root Directory**: `frontend-nextjs` ← CRITICAL
   - Build Command: `npm run build`
   - Node.js Version: 18.x

6. **Add Environment Variables**:

```env
PGHOST=db.llzdrxywpziewrzudwhj.supabase.co
PGDATABASE=postgres
PGUSER=postgres
PGPASSWORD=REDACTED_MOVED_TO_ENV
PGPORT=5432
GOOGLE_PLACES_API_KEY=your-google-api-key-here
NSW_PLANNING_API_BASE_URL=https://api.apps1.nsw.gov.au/planning
NODE_ENV=production
```

7. Click **"Deploy"**
8. Wait 3-5 minutes
9. Get your production URL: `https://your-app.vercel.app`

### Test Production

```bash
# Health check
curl https://YOUR-APP-URL.vercel.app/api/health

# Property lookup
curl "https://YOUR-APP-URL.vercel.app/api/property?address=180%20Addison%20Road,%20Marrickville%20NSW%202204"
```

---

## Troubleshooting

### If pgAdmin Can't Connect

**Error**: "Could not connect to server"

**Solutions**:
1. Check Supabase dashboard is accessible
2. Verify password: `REDACTED_MOVED_TO_ENV`
3. Try SSL mode: `Require` instead of `Prefer`
4. Check firewall isn't blocking port 5432

### If Restore Fails

**Error**: "Permission denied" or "Role does not exist"

**Fix**:
1. In Options tab, uncheck "Owner" checkbox
2. Set Role name to `postgres`
3. Try again

### If Tables Already Exist

**Error**: "relation already exists"

**Fix**:
1. In Options tab, check "Clean before restore"
2. This drops existing tables first

---

## Summary

**Total time**: 30-40 minutes

**Steps**:
1. ✅ Install pgAdmin (5 min)
2. ✅ Connect to Supabase (2 min)
3. ✅ Import database (10-15 min)
4. ✅ Verify import (5 min)
5. ✅ Deploy to Vercel (15 min)

**Files ready**:
- SQL export: `supabase-export\database_cleaned.sql` (89.75 MB)

**Next step**: Download pgAdmin from https://www.pgadmin.org/download/

---

🚀 **This will work!** pgAdmin is designed for exactly this use case.
