@echo off
REM Safe PRP Verification Runner
REM Prevents external applications from opening by using explicit Python calls

set PROJECT_ROOT=%~dp0\..
set PRP_DIR=%PROJECT_ROOT%\PRPs\NEWUI\AUTHORITATIVErouteUI

echo ================================================================
echo                 SAFE PRP VERIFICATION RUNNER
echo ================================================================
echo.
echo This script runs PRP verification without triggering external apps
echo Project Root: %PROJECT_ROOT%
echo.

REM Change to PRP directory
cd /d "%PRP_DIR%"

if "%1"=="" (
    echo Usage: run_prp_verification.bat [ui1^|ui2^|ui3^|ui4^|ui5^|all]
    echo.
    echo Example: run_prp_verification.bat ui4
    exit /b 1
)

echo Running verification for %1...
echo.

REM Use explicit Python invocation to avoid file association issues
python verify_ui_migration.py --project-root "../../.." %1

echo.
echo Verification complete.
echo.
echo If external applications still open:
echo 1. Run fix_file_associations.bat as Administrator
echo 2. Use this script instead of direct Python calls
echo 3. Ensure .py files are associated with Python, not Cursor
echo.
pause