@echo off
REM Setup PostgreSQL Scheduled Tasks - MULTIPLE ATTEMPTS THROUGHOUT DAY
REM Run this as Administrator
REM Tasks will attempt several times during work hours and at night

echo ================================================================
echo PostgreSQL Database Maintenance - Multiple Attempt Schedule
echo ================================================================
echo.
echo Strategy: Tasks attempt to run multiple times throughout the day
echo   - If laptop is asleep, task is skipped
echo   - Next scheduled time will try again
echo   - Ensures tasks complete even with irregular laptop usage
echo.

REM Get the directory where this script is located
SET SCRIPT_DIR=%~dp0
SET SCRIPT_DIR=%SCRIPT_DIR:~0,-1%

REM Define full paths
SET PYTHON_EXE=C:\Users\lawre\.pyenv\pyenv-win\versions\3.13.5\python.exe
SET HEALTH_CHECK_SCRIPT=%SCRIPT_DIR%\scripts\daily_health_check.py
SET NIGHTLY_MAINT_BAT=%SCRIPT_DIR%\scripts\nightly_maintenance_smart.bat
SET WEEKLY_VACUUM_BAT=%SCRIPT_DIR%\scripts\weekly_vacuum_smart.bat

echo Working Directory: %SCRIPT_DIR%
echo Python Path: %PYTHON_EXE%
echo.

REM Verify files exist
echo Verifying files...
if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python not found at: %PYTHON_EXE%
    echo Please update PYTHON_EXE path in this script
    pause
    exit /b 1
)
echo [OK] Python found

if not exist "%HEALTH_CHECK_SCRIPT%" (
    echo [ERROR] Health check script not found: %HEALTH_CHECK_SCRIPT%
    pause
    exit /b 1
)
echo [OK] Health check script found

if not exist "%NIGHTLY_MAINT_BAT%" (
    echo [ERROR] Nightly maintenance script not found: %NIGHTLY_MAINT_BAT%
    pause
    exit /b 1
)
echo [OK] Nightly maintenance script found

if not exist "%WEEKLY_VACUUM_BAT%" (
    echo [ERROR] Weekly vacuum script not found: %WEEKLY_VACUUM_BAT%
    pause
    exit /b 1
)
echo [OK] Weekly vacuum script found
echo.

REM Delete existing tasks if they exist
echo Removing existing tasks (if any)...
schtasks /Delete /TN "PostgreSQL Health Check" /F >nul 2>&1
schtasks /Delete /TN "PostgreSQL Nightly Maintenance" /F >nul 2>&1
schtasks /Delete /TN "PostgreSQL Weekly Vacuum" /F >nul 2>&1
echo [OK] Old tasks removed
echo.

REM Create logs directory if it doesn't exist
if not exist "%SCRIPT_DIR%\logs" (
    mkdir "%SCRIPT_DIR%\logs"
    echo [OK] Created logs directory
)

echo ================================================================
echo Creating Multiple-Attempt Scheduled Tasks
echo ================================================================
echo.

REM ========================================
REM Task 1: Health Check - 4 times daily
REM ========================================
echo [1/3] Creating: PostgreSQL Health Check
echo        Attempts: 9:00 AM, 12:00 PM, 3:00 PM, 6:00 PM, 2:00 AM
echo.

REM Create XML with multiple triggers
(
echo ^<?xml version="1.0" encoding="UTF-16"?^>
echo ^<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task"^>
echo   ^<RegistrationInfo^>
echo     ^<Description^>PostgreSQL health check - attempts multiple times daily^</Description^>
echo   ^</RegistrationInfo^>
echo   ^<Triggers^>
echo     ^<CalendarTrigger^>
echo       ^<StartBoundary^>2025-11-09T09:00:00^</StartBoundary^>
echo       ^<Enabled^>true^</Enabled^>
echo       ^<ScheduleByDay^>
echo         ^<DaysInterval^>1^</DaysInterval^>
echo       ^</ScheduleByDay^>
echo     ^</CalendarTrigger^>
echo     ^<CalendarTrigger^>
echo       ^<StartBoundary^>2025-11-09T12:00:00^</StartBoundary^>
echo       ^<Enabled^>true^</Enabled^>
echo       ^<ScheduleByDay^>
echo         ^<DaysInterval^>1^</DaysInterval^>
echo       ^</ScheduleByDay^>
echo     ^</CalendarTrigger^>
echo     ^<CalendarTrigger^>
echo       ^<StartBoundary^>2025-11-09T15:00:00^</StartBoundary^>
echo       ^<Enabled^>true^</Enabled^>
echo       ^<ScheduleByDay^>
echo         ^<DaysInterval^>1^</DaysInterval^>
echo       ^</ScheduleByDay^>
echo     ^</CalendarTrigger^>
echo     ^<CalendarTrigger^>
echo       ^<StartBoundary^>2025-11-09T18:00:00^</StartBoundary^>
echo       ^<Enabled^>true^</Enabled^>
echo       ^<ScheduleByDay^>
echo         ^<DaysInterval^>1^</DaysInterval^>
echo       ^</ScheduleByDay^>
echo     ^</CalendarTrigger^>
echo     ^<CalendarTrigger^>
echo       ^<StartBoundary^>2025-11-09T02:00:00^</StartBoundary^>
echo       ^<Enabled^>true^</Enabled^>
echo       ^<ScheduleByDay^>
echo         ^<DaysInterval^>1^</DaysInterval^>
echo       ^</ScheduleByDay^>
echo     ^</CalendarTrigger^>
echo   ^</Triggers^>
echo   ^<Principals^>
echo     ^<Principal id="Author"^>
echo       ^<UserId^>%USERNAME%^</UserId^>
echo       ^<LogonType^>InteractiveToken^</LogonType^>
echo       ^<RunLevel^>HighestAvailable^</RunLevel^>
echo     ^</Principal^>
echo   ^</Principals^>
echo   ^<Settings^>
echo     ^<MultipleInstancesPolicy^>IgnoreNew^</MultipleInstancesPolicy^>
echo     ^<DisallowStartIfOnBatteries^>false^</DisallowStartIfOnBatteries^>
echo     ^<StopIfGoingOnBatteries^>false^</StopIfGoingOnBatteries^>
echo     ^<AllowHardTerminate^>true^</AllowHardTerminate^>
echo     ^<StartWhenAvailable^>true^</StartWhenAvailable^>
echo     ^<RunOnlyIfNetworkAvailable^>false^</RunOnlyIfNetworkAvailable^>
echo     ^<IdleSettings^>
echo       ^<StopOnIdleEnd^>false^</StopOnIdleEnd^>
echo       ^<RestartOnIdle^>false^</RestartOnIdle^>
echo     ^</IdleSettings^>
echo     ^<AllowStartOnDemand^>true^</AllowStartOnDemand^>
echo     ^<Enabled^>true^</Enabled^>
echo     ^<Hidden^>false^</Hidden^>
echo     ^<RunOnlyIfIdle^>false^</RunOnlyIfIdle^>
echo     ^<WakeToRun^>false^</WakeToRun^>
echo     ^<ExecutionTimeLimit^>PT10M^</ExecutionTimeLimit^>
echo     ^<Priority^>7^</Priority^>
echo   ^</Settings^>
echo   ^<Actions Context="Author"^>
echo     ^<Exec^>
echo       ^<Command^>"%PYTHON_EXE%"^</Command^>
echo       ^<Arguments^>"%HEALTH_CHECK_SCRIPT%"^</Arguments^>
echo     ^</Exec^>
echo   ^</Actions^>
echo ^</Task^>
) > "%TEMP%\health_check_multi.xml"

schtasks /Create /TN "PostgreSQL Health Check" /XML "%TEMP%\health_check_multi.xml" /F
if %ERRORLEVEL% EQU 0 (
    echo [SUCCESS] Health Check task created with 5 daily attempts
) else (
    echo [ERROR] Failed to create Health Check task
)
del "%TEMP%\health_check_multi.xml" >nul 2>&1
echo.

REM ========================================
REM Task 2: Nightly Maintenance - 6 times daily
REM ========================================
echo [2/3] Creating: PostgreSQL Nightly Maintenance
echo        Attempts: 2:00 AM, 8:00 AM, 11:00 AM, 2:00 PM, 5:00 PM, 10:00 PM
echo.

(
echo ^<?xml version="1.0" encoding="UTF-16"?^>
echo ^<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task"^>
echo   ^<RegistrationInfo^>
echo     ^<Description^>PostgreSQL nightly maintenance (ANALYZE) - attempts multiple times daily^</Description^>
echo   ^</RegistrationInfo^>
echo   ^<Triggers^>
echo     ^<CalendarTrigger^>
echo       ^<StartBoundary^>2025-11-09T02:00:00^</StartBoundary^>
echo       ^<Enabled^>true^</Enabled^>
echo       ^<ScheduleByDay^>
echo         ^<DaysInterval^>1^</DaysInterval^>
echo       ^</ScheduleByDay^>
echo     ^</CalendarTrigger^>
echo     ^<CalendarTrigger^>
echo       ^<StartBoundary^>2025-11-09T08:00:00^</StartBoundary^>
echo       ^<Enabled^>true^</Enabled^>
echo       ^<ScheduleByDay^>
echo         ^<DaysInterval^>1^</DaysInterval^>
echo       ^</ScheduleByDay^>
echo     ^</CalendarTrigger^>
echo     ^<CalendarTrigger^>
echo       ^<StartBoundary^>2025-11-09T11:00:00^</StartBoundary^>
echo       ^<Enabled^>true^</Enabled^>
echo       ^<ScheduleByDay^>
echo         ^<DaysInterval^>1^</DaysInterval^>
echo       ^</ScheduleByDay^>
echo     ^</CalendarTrigger^>
echo     ^<CalendarTrigger^>
echo       ^<StartBoundary^>2025-11-09T14:00:00^</StartBoundary^>
echo       ^<Enabled^>true^</Enabled^>
echo       ^<ScheduleByDay^>
echo         ^<DaysInterval^>1^</DaysInterval^>
echo       ^</ScheduleByDay^>
echo     ^</CalendarTrigger^>
echo     ^<CalendarTrigger^>
echo       ^<StartBoundary^>2025-11-09T17:00:00^</StartBoundary^>
echo       ^<Enabled^>true^</Enabled^>
echo       ^<ScheduleByDay^>
echo         ^<DaysInterval^>1^</DaysInterval^>
echo       ^</ScheduleByDay^>
echo     ^</CalendarTrigger^>
echo     ^<CalendarTrigger^>
echo       ^<StartBoundary^>2025-11-09T22:00:00^</StartBoundary^>
echo       ^<Enabled^>true^</Enabled^>
echo       ^<ScheduleByDay^>
echo         ^<DaysInterval^>1^</DaysInterval^>
echo       ^</ScheduleByDay^>
echo     ^</CalendarTrigger^>
echo   ^</Triggers^>
echo   ^<Principals^>
echo     ^<Principal id="Author"^>
echo       ^<UserId^>%USERNAME%^</UserId^>
echo       ^<LogonType^>InteractiveToken^</LogonType^>
echo       ^<RunLevel^>HighestAvailable^</RunLevel^>
echo     ^</Principal^>
echo   ^</Principals^>
echo   ^<Settings^>
echo     ^<MultipleInstancesPolicy^>IgnoreNew^</MultipleInstancesPolicy^>
echo     ^<DisallowStartIfOnBatteries^>false^</DisallowStartIfOnBatteries^>
echo     ^<StopIfGoingOnBatteries^>false^</StopIfGoingOnBatteries^>
echo     ^<AllowHardTerminate^>true^</AllowHardTerminate^>
echo     ^<StartWhenAvailable^>true^</StartWhenAvailable^>
echo     ^<RunOnlyIfNetworkAvailable^>false^</RunOnlyIfNetworkAvailable^>
echo     ^<IdleSettings^>
echo       ^<StopOnIdleEnd^>false^</StopOnIdleEnd^>
echo       ^<RestartOnIdle^>false^</RestartOnIdle^>
echo     ^</IdleSettings^>
echo     ^<AllowStartOnDemand^>true^</AllowStartOnDemand^>
echo     ^<Enabled^>true^</Enabled^>
echo     ^<Hidden^>false^</Hidden^>
echo     ^<RunOnlyIfIdle^>false^</RunOnlyIfIdle^>
echo     ^<WakeToRun^>false^</WakeToRun^>
echo     ^<ExecutionTimeLimit^>PT15M^</ExecutionTimeLimit^>
echo     ^<Priority^>7^</Priority^>
echo   ^</Settings^>
echo   ^<Actions Context="Author"^>
echo     ^<Exec^>
echo       ^<Command^>"%NIGHTLY_MAINT_BAT%"^</Command^>
echo     ^</Exec^>
echo   ^</Actions^>
echo ^</Task^>
) > "%TEMP%\maintenance_multi.xml"

schtasks /Create /TN "PostgreSQL Nightly Maintenance" /XML "%TEMP%\maintenance_multi.xml" /F
if %ERRORLEVEL% EQU 0 (
    echo [SUCCESS] Nightly Maintenance task created with 6 daily attempts
) else (
    echo [ERROR] Failed to create Nightly Maintenance task
)
del "%TEMP%\maintenance_multi.xml" >nul 2>&1
echo.

REM ========================================
REM Task 3: Weekly Vacuum - 2 times weekly
REM ========================================
echo [3/3] Creating: PostgreSQL Weekly Vacuum
echo        Attempts: Sunday 3:00 AM, Saturday 10:00 AM
echo.

(
echo ^<?xml version="1.0" encoding="UTF-16"?^>
echo ^<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task"^>
echo   ^<RegistrationInfo^>
echo     ^<Description^>PostgreSQL weekly vacuum - attempts twice per week^</Description^>
echo   ^</RegistrationInfo^>
echo   ^<Triggers^>
echo     ^<CalendarTrigger^>
echo       ^<StartBoundary^>2025-11-09T03:00:00^</StartBoundary^>
echo       ^<Enabled^>true^</Enabled^>
echo       ^<ScheduleByWeek^>
echo         ^<DaysOfWeek^>
echo           ^<Sunday /^>
echo         ^</DaysOfWeek^>
echo         ^<WeeksInterval^>1^</WeeksInterval^>
echo       ^</ScheduleByWeek^>
echo     ^</CalendarTrigger^>
echo     ^<CalendarTrigger^>
echo       ^<StartBoundary^>2025-11-09T10:00:00^</StartBoundary^>
echo       ^<Enabled^>true^</Enabled^>
echo       ^<ScheduleByWeek^>
echo         ^<DaysOfWeek^>
echo           ^<Saturday /^>
echo         ^</DaysOfWeek^>
echo         ^<WeeksInterval^>1^</WeeksInterval^>
echo       ^</ScheduleByWeek^>
echo     ^</CalendarTrigger^>
echo   ^</Triggers^>
echo   ^<Principals^>
echo     ^<Principal id="Author"^>
echo       ^<UserId^>%USERNAME%^</UserId^>
echo       ^<LogonType^>InteractiveToken^</LogonType^>
echo       ^<RunLevel^>HighestAvailable^</RunLevel^>
echo     ^</Principal^>
echo   ^</Principals^>
echo   ^<Settings^>
echo     ^<MultipleInstancesPolicy^>IgnoreNew^</MultipleInstancesPolicy^>
echo     ^<DisallowStartIfOnBatteries^>false^</DisallowStartIfOnBatteries^>
echo     ^<StopIfGoingOnBatteries^>false^</StopIfGoingOnBatteries^>
echo     ^<AllowHardTerminate^>true^</AllowHardTerminate^>
echo     ^<StartWhenAvailable^>true^</StartWhenAvailable^>
echo     ^<RunOnlyIfNetworkAvailable^>false^</RunOnlyIfNetworkAvailable^>
echo     ^<IdleSettings^>
echo       ^<StopOnIdleEnd^>false^</StopOnIdleEnd^>
echo       ^<RestartOnIdle^>false^</RestartOnIdle^>
echo     ^</IdleSettings^>
echo     ^<AllowStartOnDemand^>true^</AllowStartOnDemand^>
echo     ^<Enabled^>true^</Enabled^>
echo     ^<Hidden^>false^</Hidden^>
echo     ^<RunOnlyIfIdle^>false^</RunOnlyIfIdle^>
echo     ^<WakeToRun^>false^</WakeToRun^>
echo     ^<ExecutionTimeLimit^>PT30M^</ExecutionTimeLimit^>
echo     ^<Priority^>7^</Priority^>
echo   ^</Settings^>
echo   ^<Actions Context="Author"^>
echo     ^<Exec^>
echo       ^<Command^>"%WEEKLY_VACUUM_BAT%"^</Command^>
echo     ^</Exec^>
echo   ^</Actions^>
echo ^</Task^>
) > "%TEMP%\vacuum_multi.xml"

schtasks /Create /TN "PostgreSQL Weekly Vacuum" /XML "%TEMP%\vacuum_multi.xml" /F
if %ERRORLEVEL% EQU 0 (
    echo [SUCCESS] Weekly Vacuum task created with 2 weekly attempts
) else (
    echo [ERROR] Failed to create Weekly Vacuum task
)
del "%TEMP%\vacuum_multi.xml" >nul 2>&1
echo.

REM Verify tasks were created
echo ================================================================
echo Verifying scheduled tasks...
echo ================================================================
schtasks /Query /TN "PostgreSQL Health Check" /FO LIST | findstr "TaskName State Next"
echo.
schtasks /Query /TN "PostgreSQL Nightly Maintenance" /FO LIST | findstr "TaskName State Next"
echo.
schtasks /Query /TN "PostgreSQL Weekly Vacuum" /FO LIST | findstr "TaskName State Next"
echo.

echo ================================================================
echo Setup Complete!
echo ================================================================
echo.
echo SCHEDULE SUMMARY
echo ================
echo.
echo Health Check (5 attempts daily):
echo   - 9:00 AM  (work hours)
echo   - 12:00 PM (lunch)
echo   - 3:00 PM  (afternoon)
echo   - 6:00 PM  (evening)
echo   - 2:00 AM  (night)
echo.
echo Nightly Maintenance / ANALYZE (6 attempts daily):
echo   - 2:00 AM  (night)
echo   - 8:00 AM  (morning)
echo   - 11:00 AM (late morning)
echo   - 2:00 PM  (afternoon)
echo   - 5:00 PM  (evening)
echo   - 10:00 PM (late evening)
echo.
echo Weekly Vacuum (2 attempts weekly):
echo   - Sunday 3:00 AM    (overnight)
echo   - Saturday 10:00 AM (weekend morning)
echo.
echo BEHAVIOR
echo ========
echo - Tasks run ONLY if laptop is awake
echo - If laptop is asleep, task is skipped (no wake)
echo - Next scheduled time will attempt again
echo - StartWhenAvailable = true (catches up if missed)
echo - MultipleInstancesPolicy = IgnoreNew (prevents overlaps)
echo.
echo EXPECTED OUTCOME
echo ================
echo - At least 1 health check completes per day
echo - At least 1 maintenance (ANALYZE) completes per day
echo - At least 1 vacuum completes per week
echo - Database statistics stay fresh (^< 24 hours old)
echo - No wake timers, no battery drain
echo.
echo To view all triggers for a task:
echo   powershell "Get-ScheduledTask -TaskName 'PostgreSQL Health Check' | Select -ExpandProperty Triggers"
echo.
echo To check which tasks ran today:
echo   type logs\health_check.log
echo   type logs\maintenance.log
echo.

pause
