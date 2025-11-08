@echo off
REM Smart Nightly database maintenance
REM Only runs once per day even if triggered multiple times
REM Task Name: PostgreSQL Nightly Maintenance

SET PGPASSWORD=postgres
SET LOGFILE=%~dp0..\logs\maintenance.log
SET LOCKFILE=%~dp0..\logs\maintenance_last_run.txt

REM Check if already ran today
if exist "%LOCKFILE%" (
    REM Read last run date
    set /p LAST_RUN=<"%LOCKFILE%"

    REM Compare with today's date
    if "%LAST_RUN%"=="%date%" (
        echo [%time%] Maintenance already ran today (%date%) - skipping >> "%LOGFILE%"
        exit /b 0
    )
)

echo ============================================ >> "%LOGFILE%"
echo Nightly Maintenance Started: %date% %time% >> "%LOGFILE%"
echo ============================================ >> "%LOGFILE%"

REM Analyze documents table
echo [%time%] Running ANALYZE on documents... >> "%LOGFILE%"
"C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -h localhost -d nsw_planning -c "ANALYZE documents;" >> "%LOGFILE%" 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [%time%] [OK] documents analyzed successfully >> "%LOGFILE%"
) else (
    echo [%time%] [ERROR] documents analyze failed with code %ERRORLEVEL% >> "%LOGFILE%"
)

REM Analyze regulatory_provisions table
echo [%time%] Running ANALYZE on regulatory_provisions... >> "%LOGFILE%"
"C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -h localhost -d nsw_planning -c "ANALYZE regulatory_provisions;" >> "%LOGFILE%" 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [%time%] [OK] regulatory_provisions analyzed successfully >> "%LOGFILE%"
) else (
    echo [%time%] [ERROR] regulatory_provisions analyze failed with code %ERRORLEVEL% >> "%LOGFILE%"
)

REM Analyze development_controls table
echo [%time%] Running ANALYZE on development_controls... >> "%LOGFILE%"
"C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -h localhost -d nsw_planning -c "ANALYZE development_controls;" >> "%LOGFILE%" 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [%time%] [OK] development_controls analyzed successfully >> "%LOGFILE%"
) else (
    echo [%time%] [ERROR] development_controls analyze failed with code %ERRORLEVEL% >> "%LOGFILE%"
)

echo [%time%] Nightly maintenance completed >> "%LOGFILE%"
echo. >> "%LOGFILE%"

REM Record that maintenance ran today
echo %date%> "%LOCKFILE%"

REM Update status in quickstart document
python "%~dp0update_quickstart_status.py" "nightly_maintenance" "%date% %time%" >> "%LOGFILE%" 2>&1
