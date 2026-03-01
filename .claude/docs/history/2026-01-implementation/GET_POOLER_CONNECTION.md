# Get Supabase Pooler Connection String

## The Problem

We've been guessing the pooler connection details, but they vary by project. We need to get the **exact connection string** from your Supabase dashboard.

---

## Get Your Connection String (2 minutes)

### Step 1: Go to Project Settings

**URL**: https://supabase.com/dashboard/project/llzdrxywpziewrzudwhj/settings/database

Or navigate:
1. Go to https://supabase.com/dashboard
2. Click your project: **complianceProject**
3. Click **Settings** (gear icon, bottom left)
4. Click **Database**

### Step 2: Find Connection Pooling Section

Scroll down to **Connection Pooling** section

### Step 3: Select "Session" Mode

Click on **Session** tab (not Transaction)

### Step 4: Copy the Connection String

You'll see something like:

```
postgres://postgres.[PROJECT_REF]:[YOUR-PASSWORD]@aws-X-[REGION].pooler.supabase.com:5432/postgres
```

**Copy this entire string**

### Step 5: Extract the Parts

From the connection string, we need:
- **Host**: `aws-X-[REGION].pooler.supabase.com` (e.g., `aws-0-us-east-1.pooler.supabase.com`)
- **Port**: `5432`
- **User**: `postgres.[PROJECT_REF]` (e.g., `postgres.llzdrxywpziewrzudwhj`)
- **Database**: `postgres`
- **Password**: `eDDIYq8ottiaO9ll` (you already have this)

---

## Once You Have the Details

### Option 1: Run Import Directly

Update and run this command:

```powershell
cd "C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine"

$env:PGPASSWORD = "eDDIYq8ottiaO9ll"
$env:PGSSLMODE = "require"

& "C:\Program Files\PostgreSQL\17\bin\psql.exe" `
  -h YOUR_POOLER_HOST_HERE `
  -U YOUR_POOLER_USER_HERE `
  -d postgres `
  -p 5432 `
  -f "supabase-export\database_cleaned.sql"
```

**Replace**:
- `YOUR_POOLER_HOST_HERE` with the host from dashboard
- `YOUR_POOLER_USER_HERE` with the username from dashboard

### Option 2: Use pgAdmin (Easier)

Since we keep hitting connection issues, pgAdmin is more reliable:

1. **Download**: https://www.pgadmin.org/download/
2. **Install** and open
3. **Add Server**:
   - Name: Supabase - complianceProject
   - Host: (from pooler connection string)
   - Port: 5432
   - Username: (from pooler connection string)
   - Password: eDDIYq8ottiaO9ll
4. **Right-click database** → **Restore**
5. **Select file**: `supabase-export\database_cleaned.sql`
6. **Format**: Plain
7. **Click Restore**

---

## Why This Matters

The error "Tenant or user not found" means:
- ❌ The pooler hostname might not be `aws-0-us-east-1` for your project
- ❌ The username format needs to exactly match what Supabase expects
- ✅ Your dashboard has the correct values for your specific project

Different projects get assigned to different pooler servers (`aws-0`, `aws-1`, etc.) and different regions.

---

## Next Steps

**Please do ONE of the following:**

### A. Get Pooler Connection String (Recommended)
1. Go to dashboard link above
2. Copy the **Session** mode connection string
3. Share the **host** and **username** parts
4. I'll create a working import script

### B. Use pgAdmin (Alternative)
1. Download pgAdmin
2. Use the pooler connection string from dashboard
3. Follow restore steps above
4. This bypasses all command-line connection issues

---

**Dashboard link**: https://supabase.com/dashboard/project/llzdrxywpziewrzudwhj/settings/database

Let me know which option you prefer! 🚀
