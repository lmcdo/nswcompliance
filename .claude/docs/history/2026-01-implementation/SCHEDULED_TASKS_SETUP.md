# PostgreSQL Scheduled Tasks - Setup Guide

## Problem Found

The PostgreSQL database health monitoring cron jobs were configured but **FAILING** with error code `2147946720` (file not found).

### Issues Identified:
1. ❌ Tasks using bare "python" command without full path
2. ❌ Malformed arguments in task configuration
3. ❌ No working directory set
4. ❌ Database statistics were 11 days old (not being maintained)
5. ❌ Tasks last ran successfully on Oct 12, 2025

## Solution

Created fixed setup scripts with:
- ✅ Full absolute paths to Python executable
- ✅ Properly quoted arguments
- ✅ Tasks run as current user (not SYSTEM) for proper environment
- ✅ Elevated privileges for database access

## Files Created/Updated

### 1. `setup_scheduled_tasks_fixed.bat` ⭐ NEW
**Purpose**: One-click setup of all scheduled tasks with correct configuration

**Features**:
- Validates all file paths before creating tasks
- Removes old broken tasks
- Creates three scheduled tasks with proper paths
- Verifies tasks were created successfully
- Provides testing commands

### 2. `test_scheduled_tasks.bat` ⭐ NEW
**Purpose**: Test all maintenance scripts before scheduling

**Tests**:
- Health check script execution
- Nightly maintenance script execution
- Log file creation
- Shows recent log entries

### 3. Existing Scripts (Already Working)
- `scripts/daily_health_check.py` - Monitors database health
- `scripts/nightly_maintenance.bat` - Runs ANALYZE on tables
- `scripts/weekly_vacuum.bat` - Deep cleanup weekly

## Quick Start

### Step 1: Test Scripts Work
```cmd
test_scheduled_tasks.bat
```

This will run all maintenance scripts manually to ensure they work. **All tests should pass.**

### Step 2: Setup Scheduled Tasks
**⚠️ Run as Administrator**

```cmd
setup_scheduled_tasks_fixed.bat
```

This will:
1. Delete old broken tasks
2. Create new tasks with correct configuration
3. Verify tasks are scheduled

### Step 3: Verify Tasks Are Running
```powershell
# Check task status
Get-ScheduledTask | Where TaskName -like '*PostgreSQL*'

# View task details
schtasks /Query /TN "PostgreSQL Health Check" /V
```

### Step 4: Monitor Logs
```cmd
# View health check log
type logs\health_check.log

# View maintenance log
type logs\maintenance.log
```

## Scheduled Tasks Overview

### 1. PostgreSQL Health Check
- **Schedule**: Daily at 9:00 AM
- **Purpose**: Check database health and alert on issues
- **Checks**:
  - Statistics age (warns if > 7 days old)
  - Idle connections (warns if > 5)
  - Long-running queries (warns if > 5 minutes)
  - Database size tracking
- **Action**: Logs warnings to `logs/health_check.log`

### 2. PostgreSQL Nightly Maintenance
- **Schedule**: Daily at 2:00 AM
- **Purpose**: Update table statistics for query optimizer
- **Operations**:
  - `ANALYZE documents`
  - `ANALYZE regulatory_provisions`
  - `ANALYZE development_controls`
- **Action**: Logs results to `logs/maintenance.log`

### 3. PostgreSQL Weekly Vacuum
- **Schedule**: Sunday at 3:00 AM
- **Purpose**: Deep cleanup and reclaim space
- **Operations**:
  - `VACUUM ANALYZE documents`
  - `VACUUM ANALYZE regulatory_provisions`
  - `VACUUM ANALYZE development_controls`
- **Action**: Logs results to `logs/maintenance.log`

## What Changed From Original Setup

| Aspect | Original (Broken) | Fixed |
|--------|------------------|-------|
| Python Path | `python` (not found) | `C:\Users\lawre\.pyenv\pyenv-win\versions\3.13.5\python.exe` |
| Arguments | Split/malformed | Properly quoted full paths |
| Run As | SYSTEM | Current user (`%USERNAME%`) |
| Privilege | Normal | HIGHEST (for DB access) |
| Validation | None | Pre-checks all paths |

## Verification Commands

### Check Task Status
```powershell
Get-ScheduledTask | Where TaskName -like '*PostgreSQL*' |
  Select TaskName, State, LastRunTime, NextRunTime
```

### Get Task Info
```powershell
Get-ScheduledTaskInfo -TaskName "PostgreSQL Health Check"
```

### View Last Run Result
```powershell
(Get-ScheduledTaskInfo -TaskName "PostgreSQL Health Check").LastTaskResult
```

**Result Codes**:
- `0` = Success
- `2147946720` = File not found (the error we fixed)
- `1` = Script exited with warnings

### Run Task Manually (Test)
```cmd
schtasks /Run /TN "PostgreSQL Health Check"
```

## Troubleshooting

### Task Shows "Ready" But Never Runs
1. Check Next Run Time: `schtasks /Query /TN "PostgreSQL Health Check" /V`
2. Ensure computer is on at scheduled time
3. Check Task Scheduler service is running: `sc query schedule`

### Task Fails With Error
1. Check logs: `type logs\health_check.log`
2. Run script manually: `python scripts\daily_health_check.py`
3. Verify Python path: `where python`
4. Check PostgreSQL is running: `pg_isready -h localhost`

### Database Statistics Still Old
1. Run maintenance manually: `scripts\nightly_maintenance.bat`
2. Check if ANALYZE succeeded: `type logs\maintenance.log`
3. Verify in database:
```sql
SELECT relname, last_analyze
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY last_analyze DESC;
```

### Permission Errors
- Ensure PostgreSQL password is correct in `.bat` files
- Check `PGPASSWORD` environment variable
- Verify user has database access

## Health Check Thresholds

The health check script monitors:

| Check | Warning Threshold | Critical Threshold |
|-------|------------------|-------------------|
| Statistics Age | > 3 days | > 7 days |
| Idle Connections | > 5 | > 10 |
| Long Queries | > 5 minutes | > 10 minutes |
| Database Growth | > 10% per day | > 20% per day |

## Logs Location

All logs are stored in: `C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\logs\`

- `health_check.log` - Daily health check results
- `maintenance.log` - ANALYZE and VACUUM operations

## Current Status (After Fix)

✅ **Database statistics updated** (Nov 8, 2025 21:19)
- documents: ✅ Fresh
- regulatory_provisions: ✅ Fresh
- development_controls: ✅ Fresh

✅ **Health check passing**
- Database size: 188 MB
- Connections: 1
- No warnings

⏳ **Scheduled tasks**: Need to run `setup_scheduled_tasks_fixed.bat` as Administrator

## Next Steps

1. **Run `setup_scheduled_tasks_fixed.bat` as Administrator** to fix the scheduled tasks
2. Monitor logs over next few days to ensure tasks run successfully
3. Check health_check.log daily at 9 AM for any warnings
4. Review maintenance.log weekly to confirm ANALYZE operations

## Maintenance Schedule Summary

| Time | Task | Purpose |
|------|------|---------|
| Daily 2:00 AM | ANALYZE | Update statistics for query planner |
| Daily 9:00 AM | Health Check | Monitor database health |
| Sunday 3:00 AM | VACUUM | Deep cleanup and space reclaim |

## Prevention Measures

These scheduled tasks prevent:
- ❌ Stale statistics causing slow queries
- ❌ Bloated tables wasting disk space
- ❌ Connection leaks
- ❌ Long-running queries blocking operations
- ❌ Database corruption

Regular maintenance = Healthy database! 🚀
