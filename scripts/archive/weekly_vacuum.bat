@echo off
REM Weekly full vacuum
REM Schedule: Sunday at 3:00 AM
REM Task Name: PostgreSQL Weekly Vacuum

SET PGPASSWORD=postgres
SET LOGFILE=%~dp0..\logs\maintenance.log

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

REM Update status in quickstart document
python "%~dp0update_quickstart_status.py" "weekly_vacuum" "%date% %time%" >> "%LOGFILE%" 2>&1
