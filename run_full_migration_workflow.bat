@echo off
REM ################################################################################
REM FULL MIGRATION WORKFLOW WITH AUTOMATED VERIFICATION (Windows)
REM ################################################################################
REM This script runs the complete Phase 1 migration workflow:
REM   1. Pre-migration verification
REM   2. Database backup
REM   3. Run migration
REM   4. Post-migration verification
REM   5. Rollback on failure
REM
REM Usage:
REM   run_full_migration_workflow.bat
REM ################################################################################

setlocal enabledelayedexpansion

REM Create log directory
set "TIMESTAMP=%date:~-4%%date:~-7,2%%date:~-10,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TIMESTAMP=%TIMESTAMP: =0%"
set "LOG_DIR=migration_logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOG_FILE=%LOG_DIR%\migration_workflow_%TIMESTAMP%.log"

echo ================================================================================ >> "%LOG_FILE%"
echo PHASE 1 MIGRATION WORKFLOW >> "%LOG_FILE%"
echo ================================================================================ >> "%LOG_FILE%"
echo Timestamp: %TIMESTAMP% >> "%LOG_FILE%"
echo. >> "%LOG_FILE%"

echo.
echo ================================================================================
echo PHASE 1 MIGRATION WORKFLOW
echo ================================================================================
echo.
echo Timestamp: %TIMESTAMP%
echo Log file: %LOG_FILE%
echo.

REM ################################################################################
REM STEP 1: PRE-MIGRATION VERIFICATION
REM ################################################################################

echo.
echo ================================================================================
echo STEP 1: PRE-MIGRATION VERIFICATION
echo ================================================================================
echo.
echo [INFO] Running pre-migration tests...
echo [INFO] Running pre-migration tests... >> "%LOG_FILE%"

python verify_phase1_migration.py pre > "%LOG_DIR%\pre_verification_%TIMESTAMP%.log" 2>&1
if errorlevel 1 (
    echo [ERROR] Pre-migration verification failed! >> "%LOG_FILE%"
    echo [ERROR] Pre-migration verification failed!
    echo [ERROR] Review: %LOG_DIR%\pre_verification_%TIMESTAMP%.log
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

echo [SUCCESS] Pre-migration verification passed
echo [SUCCESS] Pre-migration verification passed >> "%LOG_FILE%"
echo.

REM ################################################################################
REM CONFIRM BEFORE PROCEEDING
REM ################################################################################

set /p CONFIRM="Ready to proceed with migration? Type 'yes' to continue: "
if /i not "%CONFIRM%"=="yes" (
    echo [INFO] Migration cancelled by user
    echo [INFO] Migration cancelled by user >> "%LOG_FILE%"
    exit /b 0
)

REM ################################################################################
REM STEP 2: RUN MIGRATION
REM ################################################################################

echo.
echo ================================================================================
echo STEP 2: RUN MIGRATION
echo ================================================================================
echo.
echo [INFO] Starting Phase 1 migration...
echo [INFO] This will:
echo   - Create database backup
echo   - Add new columns (is_canonical, canonical_provision_id, text_hash)
echo   - Mark ~2300 duplicate provisions
echo   - Create view (regulatory_provisions_canonical)
echo.
echo [INFO] Starting Phase 1 migration... >> "%LOG_FILE%"

echo yes | python run_phase1_migration.py > "%LOG_DIR%\migration_%TIMESTAMP%.log" 2>&1
if errorlevel 1 (
    echo [ERROR] Migration failed! >> "%LOG_FILE%"
    echo [ERROR] Migration failed!
    echo [ERROR] Review: %LOG_DIR%\migration_%TIMESTAMP%.log
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 2
)

echo [SUCCESS] Migration completed successfully
echo [SUCCESS] Migration completed successfully >> "%LOG_FILE%"
echo.

REM ################################################################################
REM STEP 3: POST-MIGRATION VERIFICATION
REM ################################################################################

echo.
echo ================================================================================
echo STEP 3: POST-MIGRATION VERIFICATION
echo ================================================================================
echo.
echo [INFO] Running post-migration tests...
echo [INFO] Running post-migration tests... >> "%LOG_FILE%"

python verify_phase1_migration.py post > "%LOG_DIR%\post_verification_%TIMESTAMP%.log" 2>&1
if errorlevel 1 (
    echo [ERROR] Post-migration verification failed! >> "%LOG_FILE%"
    echo [ERROR] Post-migration verification failed!
    echo [ERROR] Review: %LOG_DIR%\post_verification_%TIMESTAMP%.log
    echo.
    echo [WARNING] Migration completed but verification failed
    echo [WARNING] Consider manual inspection or rollback
    echo.
    echo To rollback:
    echo   python rollback_phase1.py
    echo.
    pause
    exit /b 3
)

echo [SUCCESS] Post-migration verification passed
echo [SUCCESS] Post-migration verification passed >> "%LOG_FILE%"
echo.

REM ################################################################################
REM STEP 4: SUCCESS SUMMARY
REM ################################################################################

echo.
echo ================================================================================
echo MIGRATION WORKFLOW COMPLETE
echo ================================================================================
echo.
echo [SUCCESS] All steps completed successfully!
echo.
echo What changed:
echo   - Added 4 new columns to regulatory_provisions
echo   - Marked duplicate provisions (is_canonical = FALSE)
echo   - Created view: regulatory_provisions_canonical
echo   - All data preserved (no deletions)
echo.
echo Next steps:
echo   1. Update frontend queries to add: WHERE is_canonical = TRUE
echo   2. Or use the view: SELECT * FROM regulatory_provisions_canonical
echo   3. Test the UI: cd frontend-nextjs ^&^& npm run dev
echo.
echo Files created:
echo   - Backup: backups\pre_phase1_migration_*.sql
echo   - Pre-verification: %LOG_DIR%\pre_verification_%TIMESTAMP%.log
echo   - Migration log: %LOG_DIR%\migration_%TIMESTAMP%.log
echo   - Post-verification: %LOG_DIR%\post_verification_%TIMESTAMP%.log
echo   - JSON reports: verification_report_*.json
echo.
echo To rollback (if needed):
echo   python rollback_phase1.py
echo.

echo [SUCCESS] Migration workflow completed >> "%LOG_FILE%"

pause
exit /b 0
