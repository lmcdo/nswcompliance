@echo off
REM Test Scheduled Tasks
REM Tests each maintenance script to ensure they work before scheduling

echo ================================================================
echo Testing PostgreSQL Maintenance Scripts
echo ================================================================
echo.

SET SCRIPT_DIR=%~dp0
SET PYTHON_EXE=C:\Users\lawre\.pyenv\pyenv-win\versions\3.13.5\python.exe

echo Test 1: Health Check Script
echo ----------------------------
"%PYTHON_EXE%" "%SCRIPT_DIR%scripts\daily_health_check.py"
if %ERRORLEVEL% EQU 0 (
    echo [PASS] Health check completed successfully
) else (
    echo [FAIL] Health check failed with error code %ERRORLEVEL%
)
echo.

echo Test 2: Nightly Maintenance Script
echo ------------------------------------
call "%SCRIPT_DIR%scripts\nightly_maintenance.bat"
if %ERRORLEVEL% EQU 0 (
    echo [PASS] Nightly maintenance completed successfully
) else (
    echo [FAIL] Nightly maintenance failed with error code %ERRORLEVEL%
)
echo.

echo Test 3: Verify Logs Were Created
echo ----------------------------------
if exist "%SCRIPT_DIR%logs\health_check.log" (
    echo [PASS] Health check log exists
) else (
    echo [FAIL] Health check log not found
)

if exist "%SCRIPT_DIR%logs\maintenance.log" (
    echo [PASS] Maintenance log exists
) else (
    echo [FAIL] Maintenance log not found
)
echo.

echo ================================================================
echo Test Summary
echo ================================================================
echo.
echo Recent Health Check Log:
echo ------------------------
type "%SCRIPT_DIR%logs\health_check.log" | find /N "" | findstr /R "\[[0-9]*\]" | more +/E:-5
echo.
echo Recent Maintenance Log:
echo -----------------------
type "%SCRIPT_DIR%logs\maintenance.log" | find /N "" | findstr /R "\[[0-9]*\]" | more +/E:-10
echo.
echo ================================================================
echo All tests completed!
echo ================================================================
echo.
echo If all tests passed, you can now set up the scheduled tasks by running:
echo   setup_scheduled_tasks_fixed.bat (as Administrator)
echo.

pause
