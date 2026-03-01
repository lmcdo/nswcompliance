# Database Import Solution - Final Approach
**NSW Planning Compliance Engine → Supabase**

---

## Problem Analysis

All `psql`-based import attempts failed due to:
1. DNS resolution issues with Supabase hostname
2. No IPv6 connectivity on your system
3. Windows PostgreSQL client incompatibility

**The chart-viewer project works because it uses Supabase's REST API, NOT direct PostgreSQL connections.**

---

## ✅ WORKING SOLUTION: Split SQL File + Supabase SQL Editor

This is the **most reliable method** that doesn't require psql connectivity.

---

## Step 1: Split the SQL File (5 minutes)

Your export file is 89.16 MB, which is too large for the SQL Editor. We need to split it into ~5MB chunks.

**Run this PowerShell script:**

```powershell
cd "C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine"

# Create chunks directory
New-Item -ItemType Directory -Force -Path "supabase-export\chunks"

# Split file by line count (approximately 5MB per chunk)
$inputFile = "supabase-export\database.sql"
$outputDir = "supabase-export\chunks"
$linesPerChunk = 3000

Write-Host "Splitting SQL file into chunks..." -ForegroundColor Cyan

$lineNumber = 0
$chunkNumber = 1
$currentChunk = @()

Get-Content $inputFile | ForEach-Object {
    $currentChunk += $_
    $lineNumber++

    if ($lineNumber -ge $linesPerChunk) {
        $chunkFile = Join-Path $outputDir "chunk_$($chunkNumber.ToString('00')).sql"
        $currentChunk | Out-File $chunkFile -Encoding UTF8

        $chunkSize = [math]::Round((Get-Item $chunkFile).Length / 1MB, 2)
        Write-Host "Created: chunk_$($chunkNumber.ToString('00')).sql ($chunkSize MB)" -ForegroundColor Green

        $currentChunk = @()
        $lineNumber = 0
        $chunkNumber++
    }
}

# Write remaining lines
if ($currentChunk.Count -gt 0) {
    $chunkFile = Join-Path $outputDir "chunk_$($chunkNumber.ToString('00')).sql"
    $currentChunk | Out-File $chunkFile -Encoding UTF8

    $chunkSize = [math]::Round((Get-Item $chunkFile).Length / 1MB, 2)
    Write-Host "Created: chunk_$($chunkNumber.ToString('00')).sql ($chunkSize MB)" -ForegroundColor Green
}

Write-Host ""
Write-Host "Done! Created $chunkNumber chunks in supabase-export\chunks\" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next: Import each chunk in Supabase SQL Editor" -ForegroundColor Yellow
Write-Host "URL: https://supabase.com/dashboard/project/llzdrxywpziewrzudwhj/sql/new" -ForegroundColor White
```

---

## Step 2: Import Each Chunk (20-30 minutes)

### Access Supabase SQL Editor

**Direct URL**: https://supabase.com/dashboard/project/llzdrxywpziewrzudwhj/sql/new

Or navigate:
1. Go to: https://supabase.com/dashboard
2. Click your project: **complianceProject**
3. Click **SQL Editor** (left sidebar)
4. Click **"+ New query"**

### Import Process (for each chunk)

1. **Open chunk file** (e.g., `supabase-export\chunks\chunk_01.sql`) in VS Code or Notepad
2. **Copy all contents** (Ctrl+A, Ctrl+C)
3. **Paste into Supabase SQL Editor**
4. **Click "Run"** (or press Ctrl+Enter)
5. **Wait for completion** - you'll see "Success" or error messages
6. **Repeat for next chunk** (chunk_02.sql, chunk_03.sql, etc.)

### Progress Tracking

- ✅ chunk_01.sql
- ✅ chunk_02.sql
- ... (continue until all chunks imported)

### Important Notes

- **Order matters**: Import chunks in numerical order (01, 02, 03, etc.)
- **Check for errors**: If a chunk fails, check the error message before proceeding
- **Take breaks**: The SQL Editor may become slow after multiple large imports. Refresh the page if needed.
- **Tables are created first**: The first few chunks create table schemas, later chunks insert data

---

## Step 3: Verify Import (5 minutes)

Once all chunks are imported, run this verification query in the SQL Editor:

```sql
-- Check row counts
SELECT 'regulatory_provisions' as table_name, COUNT(*) as row_count FROM regulatory_provisions
UNION ALL SELECT 'dcp_general_requirements', COUNT(*) FROM dcp_general_requirements
UNION ALL SELECT 'dcp_precinct_requirements', COUNT(*) FROM dcp_precinct_requirements
UNION ALL SELECT 'lep_provisions', COUNT(*) FROM lep_provisions
UNION ALL SELECT 'spatial_precincts', COUNT(*) FROM spatial_precincts
UNION ALL SELECT 'heritage_conservation_areas', COUNT(*) FROM heritage_conservation_areas
UNION ALL SELECT 'version_tracking', COUNT(*) FROM version_tracking;

-- Expected totals:
-- regulatory_provisions: 48,087
-- dcp_general_requirements: 1,536
-- dcp_precinct_requirements: 1,231
-- lep_provisions: 1,846
-- spatial_precincts: ~20
-- heritage_conservation_areas: ~1,825
-- version_tracking: 10+
```

**Expected Total**: ~54,545 rows

---

## Alternative: Supabase CLI (Faster, if you have Node.js)

If you have Node.js installed, this is faster:

```powershell
# Install Supabase CLI
npm install -g supabase

# Login (opens browser)
supabase login

# Link to your project
supabase link --project-ref llzdrxywpziewrzudwhj

# You'll be prompted for the database password: eDDIYq8ottiaO9ll

# Import database
supabase db push --db-url postgresql://postgres:eDDIYq8ottiaO9ll@db.llzdrxywpziewrzudwhj.supabase.co:5432/postgres --file "supabase-export\database.sql"
```

**Note**: This still requires network connectivity to Supabase, so it may fail with the same DNS issues. The SQL Editor method is more reliable.

---

## After Import Success → Deploy to Vercel

Once database verification passes:

### 1. Push Code to GitHub (5 minutes)

```powershell
cd "C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine"

# Initialize git (if not done)
git init

# Add .gitignore
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

# Push to GitHub (create repo first at github.com/new)
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO.git
git push -u origin main
```

### 2. Deploy to Vercel (10 minutes)

**Go to**: https://vercel.com

1. **Sign in** with GitHub
2. Click **"Add New"** → **"Project"**
3. **Import** your GitHub repository
4. **Configure**:
   - Framework: Next.js (auto-detected)
   - Root Directory: **`frontend-nextjs`** ← CRITICAL
   - Build Command: `npm run build`
   - Node.js Version: 18.x

5. **Add Environment Variables**:

```env
PGHOST=db.llzdrxywpziewrzudwhj.supabase.co
PGDATABASE=postgres
PGUSER=postgres
PGPASSWORD=eDDIYq8ottiaO9ll
PGPORT=5432
GOOGLE_PLACES_API_KEY=your-google-api-key-here
NSW_PLANNING_API_BASE_URL=https://api.apps1.nsw.gov.au/planning
NODE_ENV=production
```

6. Click **"Deploy"**
7. Wait 3-5 minutes
8. Get your production URL: `https://your-app.vercel.app`

### 3. Test Production (5 minutes)

```bash
# Health check
curl https://YOUR-APP-URL.vercel.app/api/health

# Property lookup
curl "https://YOUR-APP-URL.vercel.app/api/property?address=180%20Addison%20Road,%20Marrickville%20NSW%202204"
```

---

## Why This Works (vs. chart-viewer)

**chart-viewer** uses Supabase's **JavaScript client library** which connects via REST API:
```typescript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  'https://yfzvvghmywbhhwdhhbjo.supabase.co',
  'service_role_key_here'
)
```

**This project** uses **direct PostgreSQL connections** via `node-postgres`:
```typescript
import { Pool } from 'pg'

const pool = new Pool({
  host: 'db.llzdrxywpziewrzudwhj.supabase.co',
  database: 'postgres',
  user: 'postgres',
  password: 'eDDIYq8ottiaO9ll',
  port: 5432
})
```

Both methods work for **runtime** (the deployed app will work fine), but for **importing** the database, we need to use the SQL Editor or CLI since `psql` has connectivity issues.

---

## Summary

**What to do now:**

1. ✅ Run the PowerShell script above to split SQL file into chunks
2. ✅ Import each chunk in Supabase SQL Editor (20-30 min)
3. ✅ Verify import with the SQL query provided
4. ✅ Push code to GitHub
5. ✅ Deploy to Vercel
6. ✅ Test production

**Total time**: 45-60 minutes

---

**Database export ready**: `supabase-export\database.sql` (89.16 MB)

**Next command to run**:
```powershell
cd "C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine"
# Then run the split script above
```

🚀 Let's get this deployed!
