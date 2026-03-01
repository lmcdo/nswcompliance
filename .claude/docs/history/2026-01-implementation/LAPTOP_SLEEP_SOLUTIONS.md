# Laptop Sleep - Scheduled Task Solutions

## The Problem You Identified ✅

**You're absolutely right!** The scheduled tasks **will NOT run** if your laptop is:
- 💤 Asleep (lid closed)
- 🔋 Hibernated
- ⚡ Powered off

Current schedule has tasks at **2 AM** and **3 AM** - times when laptops are typically asleep.

## Solutions (Pick What Works for You)

### **Option 1: Wake Timers** ⭐ BEST FOR LAPTOPS

**What it does**: Laptop wakes from sleep, runs maintenance, goes back to sleep

**Pros**:
- ✅ Fully automated
- ✅ Works even when laptop lid is closed
- ✅ Minimal battery impact (1-2 minutes of wake time)
- ✅ Tasks run on schedule

**Cons**:
- ⚠️ Drains a small amount of battery if unplugged
- ⚠️ Laptop fans may briefly turn on at night

**Setup**:
```cmd
# Run as Administrator
setup_scheduled_tasks_with_wake.bat
```

This will:
1. Create tasks with `WakeToRun` enabled
2. Enable wake timers in Windows power settings
3. Configure tasks to run on battery or AC

**Power Settings Modified**:
```
Wake Timers (AC Power): Enabled
Wake Timers (Battery): Enabled (optional - you can disable)
```

---

### **Option 2: Run-When-Available** ⭐ SIMPLE & SAFE

**What it does**: Tasks run as soon as laptop wakes up

**Pros**:
- ✅ No wake timers needed
- ✅ Zero battery impact
- ✅ Simple configuration
- ✅ Tasks always complete

**Cons**:
- ⚠️ Tasks run at unpredictable times (whenever you open laptop)
- ⚠️ Statistics could be 12+ hours old

**Setup**: Use `setup_scheduled_tasks_fixed.bat` (already created)
- Tasks have `StartWhenAvailable = true` already set
- If laptop is asleep at 2 AM, task runs when you wake it (e.g., 8 AM)

**Best for**: People who wake laptop daily in morning

---

### **Option 3: Daytime Schedule** ⭐ NO SLEEP CONFLICTS

**What it does**: Move maintenance to times when laptop is awake

**Suggested Schedule**:
- **Health Check**: 9:00 AM (already configured)
- **Nightly Maintenance**: **12:00 PM** (lunch time)
- **Weekly Vacuum**: **Saturday 10:00 AM**

**Pros**:
- ✅ No wake timers needed
- ✅ Zero battery impact
- ✅ Guaranteed to run if you use laptop during day
- ✅ You can monitor execution

**Cons**:
- ⚠️ May slow down laptop briefly during work hours
- ⚠️ Won't run on days you don't use laptop

**Setup**:
```cmd
# I can create this version if you want
setup_scheduled_tasks_daytime.bat
```

---

### **Option 4: Manual Execution** 💪 FULL CONTROL

**What it does**: You run maintenance when convenient

**Pros**:
- ✅ Zero automation issues
- ✅ You control when it runs
- ✅ No battery or sleep concerns

**Cons**:
- ⚠️ Easy to forget
- ⚠️ Statistics can get very old
- ⚠️ Database health at risk if skipped

**Commands**:
```cmd
# Run weekly or when you remember
scripts\nightly_maintenance.bat
python scripts\daily_health_check.py
```

---

### **Option 5: Hybrid Approach** 🎯 RECOMMENDED

**What it does**: Combine automatic + manual

**Configuration**:
- **Health Check**: 9:00 AM daily (no wake needed - daytime)
- **Nightly Maintenance**: Wake timer at 2:00 AM (automated)
- **Weekly Vacuum**: Manual on demand

**Pros**:
- ✅ Health monitoring always happens
- ✅ Statistics stay fresh (daily ANALYZE)
- ✅ You control heavy vacuum operations
- ✅ Minimal wake events (once per day)

**Setup**: Use `setup_scheduled_tasks_with_wake.bat` then disable weekly vacuum:
```cmd
schtasks /Change /TN "PostgreSQL Weekly Vacuum" /DISABLE
```

---

## Battery Impact Analysis

### Wake Timer Power Consumption

**Maintenance Duration**: 1-2 minutes
**Operations**: Database ANALYZE (CPU only, no disk writes)
**Power Draw**: ~5-10 Wh (equivalent to 1-2 minutes of normal use)

**Impact on 60Wh battery**: ~0.1% battery per wake event

**Daily wake at 2 AM**:
- Battery drain: 0.1% × 1 event = **0.1% per night**
- Monthly: **~3% battery**

**Negligible** unless laptop is unplugged for weeks.

---

## Recommended Configuration (Pick One)

### For Regular Daily Use (Laptop Opened Daily)
→ **Option 2: Run-When-Available**
- Use `setup_scheduled_tasks_fixed.bat`
- Tasks run when you open laptop in morning
- Zero battery impact

### For 24/7 Reliability (Development/Server Use)
→ **Option 1: Wake Timers**
- Use `setup_scheduled_tasks_with_wake.bat`
- Laptop always maintained
- Minimal battery impact

### For Workday Schedule Only
→ **Option 3: Daytime Schedule**
- Use daytime schedule (I can create this)
- Tasks run during work hours
- No sleep conflicts

### For Minimal Automation
→ **Option 5: Hybrid**
- Use `setup_scheduled_tasks_with_wake.bat`
- Disable weekly vacuum
- Run vacuum manually monthly

---

## How to Check Wake Timer Status

### See if wake timers are enabled:
```powershell
powercfg /query SCHEME_CURRENT SUB_SLEEP RTCWAKE
```

**Output**:
- `0x00000000` = Disabled (tasks won't wake laptop)
- `0x00000001` = Enabled (tasks will wake laptop)

### See which tasks can wake computer:
```powershell
Get-ScheduledTask |
  Where {$_.Settings.WakeToRun} |
  Select TaskName, State
```

### See next wake event:
```powershell
powercfg /waketimers
```

---

## Disable Wake on Battery (If Desired)

If you want tasks to wake on AC only (not battery):

```cmd
# Disable wake on battery
powercfg /SETDCVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 0

# Keep wake on AC power
powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 1

# Apply changes
powercfg /SETACTIVE SCHEME_CURRENT
```

This way:
- ✅ Plugged in: Tasks wake laptop
- ✅ On battery: Tasks wait until you wake it

---

## Testing Wake Timers

### Test if wake works:

1. **Create a test task**:
```cmd
# Schedule a task 5 minutes from now
schtasks /Create /TN "Wake Test" /TR "notepad.exe" /SC ONCE /ST 21:30 /RU %USERNAME% /RL HIGHEST /F
```

2. **Enable wake for this task**:
```powershell
$task = Get-ScheduledTask -TaskName "Wake Test"
$task.Settings.WakeToRun = $true
Set-ScheduledTask $task
```

3. **Put laptop to sleep** (close lid or Start > Sleep)

4. **Wait 5 minutes** - laptop should wake and open Notepad

5. **Delete test task**:
```cmd
schtasks /Delete /TN "Wake Test" /F
```

---

## My Recommendation 🎯

Based on typical laptop usage, I recommend:

**Option 5: Hybrid Approach**

```cmd
# Run this as Administrator
setup_scheduled_tasks_with_wake.bat

# Then optionally disable wake on battery (to save power)
powercfg /SETDCVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 0
powercfg /SETACTIVE SCHEME_CURRENT
```

**Result**:
- ✅ Health check at 9 AM (when you're using laptop)
- ✅ Maintenance at 2 AM (if plugged in, or next morning if on battery)
- ✅ Weekly vacuum runs automatically (or disable and run manually)
- ✅ Database stays healthy
- ✅ Minimal battery impact

---

## Files Available

| File | Purpose | Wake Support |
|------|---------|--------------|
| `setup_scheduled_tasks_fixed.bat` | Basic setup, no wake | ❌ Won't wake laptop |
| `setup_scheduled_tasks_with_wake.bat` | Full automation with wake | ✅ Wakes laptop |
| `test_scheduled_tasks.bat` | Test scripts work | N/A (manual test) |

---

## What I'd Choose 🤔

If this were my laptop:
1. Use **Option 1: Wake Timers** with wake-on-battery **disabled**
2. Result: Tasks run at night if plugged in, or in morning if not
3. Run weekly vacuum manually once a month
4. Check logs weekly to ensure tasks ran

**Why**: Best balance of automation and battery life.

---

**Want me to create the daytime schedule version or help you set up a different option?**
