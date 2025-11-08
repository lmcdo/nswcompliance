@echo off
REM Smart Weekly full vacuum
REM Only runs once per week even if triggered multiple times
REM Task Name: PostgreSQL Weekly Vacuum

SET PGPASSWORD=postgres
SET LOGFILE=%~dp0..\logs\maintenance.log
SET LOCKFILE=%~dp0..\logs\vacuum_last_run.txt

REM Check if already ran this week
if exist "%LOCKFILE%" (
    REM Read last run date
    set /p LAST_RUN=<"%LOCKFILE%"

    REM Get days since last run
    powershell -Command "$lastRun = Get-Content '%LOCKFILE%'; $lastDate = [datetime]::ParseExact($lastRun, 'ddd MM/dd/yyyy', $null); $daysSince = ((Get-Date) - $lastDate).Days; if ($daysSince -lt 7) { exit 1 } else { exit 0 }" >nul 2>&1

    if %ERRORLEVEL% EQU 1 (
        echo [%time%] Vacuum already ran this week - skipping >> "%LOGFILE%"
        exit /b 0
    )
)

echo ============================================ >> "%LOGFILE%"
echo Weekly VACUUM Started: %date% %time% >> "%LOGFILE%"
echo ============================================ >> "%LOGFILE%"

REM VACUUM ANALYZE documents table
echo [%time%] Running VACUUM ANALYZE on documents... >> "%LOGFILE%"
"C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -h localhost -d nsw_planning -c "VACUUM ANALYZE documents;" >> "%LOGFILE%" 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [%time%] [OK] documents vacuumed successfully >> "%LOGFILE%"
) else (
    echo [%time%] [ERROR] documents vacuum failed with code %ERRORLEVEL% >> "%LOGFILE%"
)

REM VACUUM ANALYZE regulatory_provisions table
echo [%time%] Running VACUUM ANALYZE on regulatory_provisions... >> "%LOGFILE%"
"C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -h localhost -d nsw_planning -c "VACUUM ANALYZE regulatory_provisions;" >> "%LOGFILE%" 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [%time%] [OK] regulatory_provisions vacuumed successfully >> "%LOGFILE%"
) else (
    echo [%time%] [ERROR] regulatory_provisions vacuum failed with code %ERRORLEVEL% >> "%LOGFILE%"
)

REM VACUUM ANALYZE development_controls table
echo [%time%] Running VACUUM ANALYZE on development_controls... >> "%LOGFILE%"
"C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -h localhost -d nsw_planning -c "VACUUM ANALYZE development_controls;" >> "%LOGFILE%" 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [%time%] [OK] development_controls vacuumed successfully >> "%LOGFILE%"
) else (
    echo [%time%] [ERROR] development_controls vacuum failed with code %ERRORLEVEL% >> "%LOGFILE%"
)

echo [%time%] Weekly vacuum completed >> "%LOGFILE%"
echo. >> "%LOGFILE%"

REM Record that vacuum ran today
echo %date%> "%LOCKFILE%"

REM Update status in quickstart document
python "%~dp0update_quickstart_status.py" "weekly_vacuum" "%date% %time%" >> "%LOGFILE%" 2>&1
