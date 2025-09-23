@echo off
REM Fix File Associations to Prevent External Apps Opening
REM This script ensures Python files are run with Python interpreter

echo Fixing file associations to prevent external applications from opening...

REM Check if Python is available
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is not installed or not in PATH
    exit /b 1
)

REM Fix .py file association
echo Setting .py files to open with Python interpreter...
assoc .py=Python.File
ftype Python.File="python.exe" "%%1" %%*

REM Fix .ts and .tsx associations to prevent MediaPlayer opening
echo Fixing TypeScript file associations...
assoc .ts=TypeScript.File
ftype TypeScript.File="notepad.exe" "%%1"

assoc .tsx=TypeScriptReact.File
ftype TypeScriptReact.File="notepad.exe" "%%1"

REM Fix .js and .jsx associations
echo Fixing JavaScript file associations...
assoc .js=JavaScript.File
ftype JavaScript.File="notepad.exe" "%%1"

assoc .jsx=JavaScriptReact.File
ftype JavaScriptReact.File="notepad.exe" "%%1"

echo.
echo File associations fixed successfully!
echo.
echo NOTE: You may need to run this script as Administrator for changes to take effect.
echo If issues persist, use explicit Python calls: python script.py
echo.
pause