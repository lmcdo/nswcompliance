# PostgreSQL Scheduled Tasks - Multiple Attempts Strategy

## Overview

This setup runs database maintenance **multiple times throughout the day** to ensure completion even with irregular laptop usage.

### Key Features

✅ **No Wake Timers** - Tasks only run when laptop is awake
✅ **Multiple Attempts** - Tasks try several times per day
✅ **Smart Deduplication** - Only runs once per day/week (prevents duplicates)
✅ **Zero Battery Impact** - No wake from sleep
✅ **StartWhenAvailable** - Catches up if laptop was asleep
✅ **Guaranteed Completion** - At least one attempt succeeds per day

---

## Schedule Summary

### Health Check (5 attempts daily)
| Time | Context |
|------|---------|
| 9:00 AM | Morning work hours |
| 12:00 PM | Lunch break |
| 3:00 PM | Afternoon |
| 6:00 PM | Evening |
| 2:00 AM | Overnight (if laptop on) |

**Behavior**: Runs first time laptop is awake at any of these times

---

### Nightly Maintenance / ANALYZE (6 attempts daily)
| Time | Context |
|------|---------|
| 2:00 AM | Overnight (if laptop on) |
| 8:00 AM | Morning startup |
| 11:00 AM | Late morning |
| 2:00 PM | Afternoon |
| 5:00 PM | End of workday |
| 10:00 PM | Evening |

**Behavior**: Runs ONCE per day at first available time
**Smart Logic**: Lockfile prevents duplicate runs on same day

---

### Weekly Vacuum (2 attempts weekly)
| Time | Context |
|------|---------|
| Sunday 3:00 AM | Overnight (if laptop on) |
| Saturday 10:00 AM | Weekend morning |

**Behavior**: Runs ONCE per week at first available time
**Smart Logic**: Lockfile prevents duplicate runs within 7 days

---

## Setup Instructions

### Prerequisites
1. PostgreSQL 17 installed and running
2. Python 3.13.5 at `C:\Users\lawre\.pyenv\pyenv-win\versions\3.13.5\python.exe`
3. Administrator privileges

### Installation

**1. Test scripts work:**
```cmd
test_scheduled_tasks.bat
```

**2. Run setup as Administrator:**
```cmd
setup_scheduled_tasks_multiple_attempts.bat
```

**3. Verify tasks created:**
```powershell
Get-ScheduledTask | Where TaskName -like '*PostgreSQL*' |
  Select TaskName, State, @{N='NextRun';E={(Get-ScheduledTaskInfo $_.TaskName).NextRunTime}}
```

---

## How It Works

### Smart Deduplication

**Problem**: Multiple triggers per day could cause ANALYZE to run 6 times
**Solution**: Lockfiles prevent duplicate execution

#### Maintenance Script Logic
```batch
1. Check if lockfile exists: logs\maintenance_last_run.txt
2. If exists, read date from file
3. If date == today's date: Skip execution
4. If date != today's date: Run ANALYZE
5. After completion: Write today's date to lockfile
```

#### Vacuum Script Logic
```batch
1. Check if lockfile exists: logs\vacuum_last_run.txt
2. If exists, calculate days since last run
3. If < 7 days: Skip execution
4. If >= 7 days: Run VACUUM
5. After completion: Write today's date to lockfile
```

### Example Scenario

**Monday (laptop usage: 9 AM - 6 PM)**

| Time | Task Triggered | Outcome |
|------|----------------|---------|
| 2:00 AM | Maintenance | ❌ Laptop asleep - skipped |
| 8:00 AM | Maintenance | ✅ **RUNS** - first awake time |
| 9:00 AM | Health Check | ✅ **RUNS** |
| 11:00 AM | Maintenance | ⏭️ Skipped - already ran today (lockfile) |
| 12:00 PM | Health Check | ⏭️ Skipped - already ran today |
| 2:00 PM | Maintenance | ⏭️ Skipped - already ran today (lockfile) |
| 3:00 PM | Health Check | ⏭️ Skipped - already ran today |
| 5:00 PM | Maintenance | ⏭️ Skipped - already ran today (lockfile) |
| 6:00 PM | Health Check | ⏭️ Skipped - already ran today |

**Result**: Maintenance ran once at 8 AM, health check ran once at 9 AM ✅

---

## Files Created

### Setup Script
- **`setup_scheduled_tasks_multiple_attempts.bat`** - Creates all tasks

### Smart Scripts (Prevent Duplicates)
- **`scripts/nightly_maintenance_smart.bat`** - ANALYZE with daily lockfile
- **`scripts/weekly_vacuum_smart.bat`** - VACUUM with weekly lockfile

### Lockfiles (Auto-Generated)
- **`logs/maintenance_last_run.txt`** - Stores last ANALYZE date
- **`logs/vacuum_last_run.txt`** - Stores last VACUUM date

### Logs
- **`logs/health_check.log`** - Health check results
- **`logs/maintenance.log`** - ANALYZE and VACUUM results

---

## Monitoring

### Check Task Status
```powershell
# See all PostgreSQL tasks
Get-ScheduledTask | Where TaskName -like '*PostgreSQL*'

# See next run times
Get-ScheduledTask | Where TaskName -like '*PostgreSQL*' |
  ForEach-Object {
    [PSCustomObject]@{
      Task = $_.TaskName
      State = $_.State
      NextRun = (Get-ScheduledTaskInfo $_.TaskName).NextRunTime
    }
  }
```

### View Logs
```cmd
# Recent maintenance runs
type logs\maintenance.log | find "Nightly Maintenance Started" | more +/E:-10

# Recent health checks
type logs\health_check.log | find "[OK]" | more +/E:-5

# Check if maintenance ran today
type logs\maintenance_last_run.txt

# Check when vacuum last ran
type logs\vacuum_last_run.txt
```

### Verify Database Statistics Are Fresh
```sql
SELECT
    relname,
    last_analyze,
    NOW() - last_analyze as age
FROM pg_stat_user_tables
WHERE schemaname = 'public'
  AND relname IN ('documents', 'regulatory_provisions', 'development_controls')
ORDER BY age DESC;
```

**Expected**: Age < 24 hours

---

## Task Configuration Details

### MultipleInstancesPolicy = IgnoreNew
Prevents overlapping executions. If task is still running when next trigger fires, the new instance is skipped.

### StartWhenAvailable = true
If laptop was asleep at trigger time, task runs as soon as laptop wakes.

**Example**:
- Task scheduled: 8:00 AM
- Laptop asleep until 9:30 AM
- Task runs at 9:30 AM (catch-up)

### WakeToRun = false
Tasks do NOT wake laptop from sleep. Zero battery impact.

### DisallowStartIfOnBatteries = false
Tasks run on battery power (ANALYZE uses minimal power).

---

## Advantages Over Single Daily Schedule

| Aspect | Single Schedule (2 AM) | Multiple Attempts |
|--------|----------------------|-------------------|
| Success rate | Low (laptop usually asleep) | High (≥ 1 attempt succeeds) |
| Statistics freshness | Can be days old | Always < 24 hours |
| Battery impact | Requires wake timers | Zero |
| Reliability | Depends on laptop being on at 2 AM | Works with any usage pattern |
| Flexibility | Rigid timing | Adapts to your schedule |

---

## Troubleshooting

### Tasks Not Running
**Check if laptop was awake at any trigger time:**
```powershell
# See last run time
Get-ScheduledTaskInfo -TaskName "PostgreSQL Nightly Maintenance" |
  Select LastRunTime, LastTaskResult
```

**Check logs:**
```cmd
type logs\maintenance.log
```

### Statistics Still Old
**Check if maintenance completed successfully:**
```cmd
# Look for errors in log
type logs\maintenance.log | find "ERROR"
```

**Check lockfile:**
```cmd
# See when last ran
type logs\maintenance_last_run.txt
```

**Force run manually:**
```cmd
scripts\nightly_maintenance_smart.bat
```

### Vacuum Not Running
**Check days since last vacuum:**
```cmd
type logs\vacuum_last_run.txt
```

**Force vacuum manually:**
```cmd
scripts\weekly_vacuum_smart.bat
```

### Duplicate Runs (Should Not Happen)
**Verify lockfile logic:**
```cmd
# Check maintenance lockfile
type logs\maintenance_last_run.txt
echo Expected: Today's date (%date%)

# Check vacuum lockfile
type logs\vacuum_last_run.txt
echo Expected: Date within last 7 days
```

---

## Customization

### Change Trigger Times

Edit `setup_scheduled_tasks_multiple_attempts.bat` and modify the `StartBoundary` values:

```xml
<!-- Example: Change health check from 9:00 AM to 10:00 AM -->
<StartBoundary>2025-11-09T10:00:00</StartBoundary>
```

Then re-run the setup script.

### Add More Attempts

Add additional `<CalendarTrigger>` blocks in the XML sections.

**Example**: Add 4 PM health check:
```xml
<CalendarTrigger>
  <StartBoundary>2025-11-09T16:00:00</StartBoundary>
  <Enabled>true</Enabled>
  <ScheduleByDay>
    <DaysInterval>1</DaysInterval>
  </ScheduleByDay>
</CalendarTrigger>
```

### Disable Certain Attempts

Use `schtasks` to disable individual triggers (not easily done - easier to recreate task).

Or edit task in Task Scheduler GUI:
1. Open Task Scheduler (`taskschd.msc`)
2. Find task under root folder
3. Right-click → Properties
4. Triggers tab → Disable unwanted triggers

---

## Expected Behavior

### Typical Weekday (9 AM - 6 PM laptop use)
- ✅ Maintenance runs once (likely 8 AM)
- ✅ Health check runs once (likely 9 AM)
- ✅ Database statistics < 12 hours old
- ✅ Health check log shows "OK"

### Typical Weekend (irregular laptop use)
- ✅ Maintenance runs when laptop first opened
- ✅ Vacuum runs Saturday 10 AM or Sunday 3 AM (whichever laptop is on)
- ✅ Database statistics < 36 hours old (still acceptable)

### Extended Offline (laptop not used for 3+ days)
- ⚠️ Tasks do not run (laptop off/asleep)
- ⚠️ Statistics get stale (> 3 days old)
- ✅ **Catch-up**: When laptop wakes, StartWhenAvailable runs all missed tasks
- ✅ Database recovers to fresh state within 1 hour of laptop use

---

## Recommendations

### For Daily Laptop Users
✅ **Use this setup** - guaranteed to work
- Maintenance runs automatically when you work
- No intervention needed
- Database stays healthy

### For Infrequent Laptop Users (2-3 days/week)
⚠️ **Consider hybrid approach**:
- Use multiple attempts setup
- Manually run maintenance on first use each week:
  ```cmd
  scripts\nightly_maintenance_smart.bat
  ```

### For 24/7 Server Use
❌ **Don't use this setup** - use single schedule or wake timers
- Laptop is always on
- No need for multiple attempts
- Use `setup_scheduled_tasks_fixed.bat` instead

---

## Summary

**This setup ensures your PostgreSQL database gets maintained even with unpredictable laptop usage patterns.**

✅ Multiple attempts throughout day
✅ Smart deduplication (no duplicate runs)
✅ Zero battery impact (no wake timers)
✅ StartWhenAvailable catches up missed runs
✅ Guaranteed fresh statistics (< 24 hours)

**Perfect for laptops with irregular usage patterns!**
