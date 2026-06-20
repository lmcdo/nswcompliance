# Import Database via Supabase Dashboard
**Solution for psql connectivity issues**

---

## Problem

Your system doesn't have IPv6 connectivity, and psql can't resolve the Supabase hostname. This is a common Windows + PostgreSQL issue.

## ✅ SOLUTION: Use Supabase SQL Editor

This is actually **easier** than psql!

---

## Step-by-Step Instructions

### Step 1: Go to Supabase SQL Editor

**URL**: https://supabase.com/dashboard/project/llzdrxywpziewrzudwhj/sql/new

Or navigate:
1. Go to: https://supabase.com/dashboard
2. Click your project: **complianceProject**
3. Click **SQL Editor** (left sidebar)
4. Click **"+ New query"**

---

### Step 2: Prepare the Export File

Your database export is already ready:
```
Location: C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\supabase-export\database.sql
Size: 89.16 MB
```

**Problem**: File is too large to paste all at once (SQL Editor has limits)

**Solution**: Split into chunks

---

### Step 3: Split the SQL File

**Option A: Use This PowerShell Script** (Automatic - Recommended)

Run this to split into manageable chunks:

```powershell
cd "C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine"

# Create chunks directory
New-Item -ItemType Directory -Force -Path "supabase-export\chunks"

# Split file into 10MB chunks
$inputFile = "supabase-export\database.sql"
$outputDir = "supabase-export\chunks"
$chunkSize = 10MB

$content = Get-Content $inputFile -Raw
$contentLength = $content.Length
$chunks = [Math]::Ceiling($contentLength / $chunkSize)

Write-Host "Splitting $contentLength bytes into $chunks chunks..."

for ($i = 0; $i -lt $chunks; $i++) {
    $start = $i * $chunkSize
    $length = [Math]::Min($chunkSize, $contentLength - $start)
    $chunk = $content.Substring($start, $length)

    $chunkFile = Join-Path $outputDir "chunk_$($i+1)_of_$chunks.sql"
    $chunk | Out-File $chunkFile -Encoding UTF8 -NoNewline

    Write-Host "Created: chunk_$($i+1)_of_$chunks.sql ($([Math]::Round($length/1MB, 2)) MB)"
}

Write-Host ""
Write-Host "Done! Import each chunk in order in Supabase SQL Editor." -ForegroundColor Green
```

**Option B: Manual Split** (If PowerShell fails)

1. Open `supabase-export\database.sql` in VS Code or Notepad++
2. Copy first 5000 lines → Save as `chunk_1.sql`
3. Copy next 5000 lines → Save as `chunk_2.sql`
4. Continue until end of file

---

### Step 4: Import Each Chunk

For each chunk file:

1. **Open the chunk file** in a text editor
2. **Copy all contents** (Ctrl+A, Ctrl+C)
3. **Paste into Supabase SQL Editor**
4. **Click "Run"** (or press Ctrl+Enter)
5. **Wait for completion** (you'll see "Success" or error messages)
6. **Repeat for next chunk**

**Progress**:
- ✅ Chunk 1 of 9 complete
- ✅ Chunk 2 of 9 complete
- ... continue ...

---

## Alternative: Use Supabase CLI (Faster)

If you have Node.js installed:

```powershell
# Install Supabase CLI
npm install -g supabase

# Login (opens browser)
supabase login

# Link to your project
supabase link --project-ref llzdrxywpziewrzudwhj

# Import via CLI
supabase db dump --file supabase-export\database.sql
```

---

## Alternative: Use pgAdmin (GUI Tool)

1. **Download pgAdmin**: https://www.pgadmin.org/download/
2. **Install and open**
3. **Create new server connection**:
   - Host: `db.llzdrxywpziewrzudwhj.supabase.co`
   - Port: `5432`
   - Database: `postgres`
   - Username: `postgres`
   - Password: `REDACTED_MOVED_TO_ENV`
4. **Right-click database** → **Restore**
5. **Select file**: `supabase-export\database.sql`
6. **Format**: Plain
7. **Click Restore**

pgAdmin may handle the connection better than psql.

---

## After Import: Verify

Once import completes (via any method), verify:

```sql
-- In Supabase SQL Editor, run:
SELECT 'regulatory_provisions' as table_name, COUNT(*) FROM regulatory_provisions
UNION ALL SELECT 'dcp_general_requirements', COUNT(*) FROM dcp_general_requirements
UNION ALL SELECT 'dcp_precinct_requirements', COUNT(*) FROM dcp_precinct_requirements;

-- Expected:
-- regulatory_provisions: 48,087
-- dcp_general_requirements: 1,536
-- dcp_precinct_requirements: 1,231
```

---

## Then Deploy to Vercel

Once database is verified, proceed with Vercel deployment:

1. Push code to GitHub
2. Import project on Vercel
3. Set Root Directory: `frontend-nextjs`
4. Add environment variables:
   ```
   PGHOST=db.llzdrxywpziewrzudwhj.supabase.co
   PGDATABASE=postgres
   PGUSER=postgres
   PGPASSWORD=REDACTED_MOVED_TO_ENV
   PGPORT=5432
   ```
5. Deploy!

---

## Summary

**Problem**: psql can't connect (no IPv6, DNS issues)

**Solutions** (in order of ease):
1. ✅ **Supabase SQL Editor** (split into chunks) ← Recommended
2. ✅ **Supabase CLI** (if Node.js available)
3. ✅ **pgAdmin** (GUI tool, may handle connection better)

All three methods will work. Choose whichever is easiest for you!

---

**Your database export is ready**: `supabase-export\database.sql` (89.16 MB)

**Next step**: Choose a method above and import! 🚀
