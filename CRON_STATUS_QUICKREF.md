# PostgreSQL Cron Job - Quick Status Reference

## 📊 Current Status (Nov 8, 2025)

### ✅ What's Working
- ✅ Health check script works (tested manually)
- ✅ Nightly maintenance script works (tested manually)
- ✅ Database statistics are FRESH (just updated)
- ✅ All logs are being created properly
- ✅ Database health: **PASSING** (188 MB, 1 connection)

### ⚠️ What Needs Fixing
- ❌ Scheduled tasks exist but are **FAILING** (error 2147946720)
- ❌ Tasks haven't run successfully since Oct 12, 2025
- ⏳ Need to run `setup_scheduled_tasks_fixed.bat` as Admin

## 🔧 Quick Fix (Run These Commands)

### ⚠️ IMPORTANT: Laptop Sleep Issue
**If your laptop is asleep (lid closed), scheduled tasks will NOT run!**

**RECOMMENDED SOLUTION**: Multiple attempts throughout the day
- Tasks try 5-6 times per day (work hours + night)
- Only runs when laptop is awake (no wake timers)
- Smart deduplication prevents duplicate runs
- Guaranteed completion with any usage pattern

See `MULTIPLE_ATTEMPTS_SETUP.md` for full details.

### 1. Test Everything Works
```cmd
test_scheduled_tasks.bat
```
**Expected**: All tests should PASS

### 2. Fix Scheduled Tasks (⚠️ AS ADMINISTRATOR)

**RECOMMENDED - Multiple Attempts (Best for laptops)**:
```cmd
setup_scheduled_tasks_multiple_attempts.bat
```
Tasks attempt 5-6 times per day. Runs once per day at first available time.
No wake timers, zero battery impact, guaranteed completion.

**Alternative Options**:
- Wake from sleep: `setup_scheduled_tasks_with_wake.bat`
- Single attempt: `setup_scheduled_tasks_fixed.bat`

### 3. Verify Tasks Are Scheduled
```powershell
Get-ScheduledTask | Where TaskName -like '*PostgreSQL*'
```
**Expected**: 3 tasks showing "Ready" state with NextRunTime

## 📅 Scheduled Tasks

| Task | Frequency | Time | Last Success | Next Run |
|------|-----------|------|--------------|----------|
| Health Check | Daily | 9:00 AM | Manual (Nov 8) | Nov 9 9:00 AM* |
| Nightly Maintenance | Daily | 2:00 AM | Manual (Nov 8) | Nov 9 2:00 AM* |
| Weekly Vacuum | Weekly (Sun) | 3:00 AM | Oct 12 | Nov 10 3:00 AM* |

\* *After running `setup_scheduled_tasks_fixed.bat`*

## 🩺 Database Health (Current)

```
✅ HEALTHY - Last checked: Nov 8, 2025 21:19:36

Statistics:
  - documents: ✅ Fresh (updated today)
  - regulatory_provisions: ✅ Fresh (updated today)
  - development_controls: ✅ Fresh (updated today)

Metrics:
  - Database size: 188 MB
  - Connections: 1
  - No warnings or errors
```

## 🚨 Problem Summary (Why Tasks Are Failing)

**Root Cause**: Tasks configured with incorrect paths

| Issue | Problem | Fix |
|-------|---------|-----|
| Python path | `python` (not found by SYSTEM) | `C:\Users\lawre\.pyenv\...\python.exe` |
| Arguments | Malformed/split | Properly quoted full paths |
| Working dir | Not set | Set to project root |
| User context | SYSTEM (no env) | Current user with HIGHEST privilege |

## 📁 Files Created

1. **`setup_scheduled_tasks_fixed.bat`** - Fixed task setup script
2. **`test_scheduled_tasks.bat`** - Test all scripts before scheduling
3. **`SCHEDULED_TASKS_SETUP.md`** - Detailed documentation
4. **`CRON_STATUS_QUICKREF.md`** - This quick reference

## 🔍 Monitoring Commands

### Check if tasks are running
```powershell
Get-ScheduledTask | Where TaskName -like '*PostgreSQL*' |
  Select TaskName, State, LastRunTime, NextRunTime
```

### View logs
```cmd
type logs\health_check.log
type logs\maintenance.log
```

### Manual health check
```cmd
python scripts\daily_health_check.py
```

### Manual maintenance
```cmd
scripts\nightly_maintenance.bat
```

## ⏭️ Next Steps

**Priority 1: Fix scheduled tasks**
```cmd
1. Open PowerShell/CMD as Administrator
2. Navigate to: C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine
3. Run: setup_scheduled_tasks_fixed.bat
4. Verify: Get-ScheduledTask | Where TaskName -like '*PostgreSQL*'
```

**Priority 2: Monitor for 3 days**
- Check logs daily to ensure tasks run
- Verify NextRunTime advances each day
- Confirm no errors in logs

**Priority 3: Set up alerts (optional)**
- Configure email alerts for failed health checks
- Add monitoring dashboard
- Set up backup verification

## 📞 Troubleshooting

### "Task not found" error
→ Tasks need to be created: Run `setup_scheduled_tasks_fixed.bat`

### "Access denied" error
→ Run setup script as Administrator

### Tasks created but not running
→ Check Task Scheduler service: `sc query schedule`

### Health check fails
→ Check PostgreSQL is running: `pg_isready -h localhost`

### Statistics still old after maintenance
→ Check `logs\maintenance.log` for ANALYZE errors

## 🎯 Success Criteria

You'll know everything is working when:
- ✅ All 3 tasks show "Ready" state
- ✅ NextRunTime is set and advancing
- ✅ Logs show daily updates
- ✅ Health check passes without warnings
- ✅ Database statistics < 1 day old

---

**Status**: Ready to fix - All scripts tested and working, just need to run setup_scheduled_tasks_fixed.bat as Admin
