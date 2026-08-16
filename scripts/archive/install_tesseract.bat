@echo off
REM Install Tesseract OCR for table re-extraction
REM Run this script as Administrator

echo ============================================
echo Installing Tesseract OCR
echo ============================================

REM Check if Chocolatey is installed
choco --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Chocolatey is not installed
    echo Please install Chocolatey first: https://chocolatey.org/install
    echo.
    echo Or download Tesseract manually from:
    echo https://github.com/UB-Mannheim/tesseract/wiki
    pause
    exit /b 1
)

echo Installing Tesseract via Chocolatey...
choco install tesseract -y

echo.
echo Installing Python dependencies...
pip install pytesseract pdf2image Pillow

echo.
echo Checking installation...
tesseract --version

if %errorlevel% equ 0 (
    echo.
    echo ============================================
    echo SUCCESS: Tesseract installed successfully!
    echo ============================================
    echo.
    echo Next step: Run python scripts/reextract_with_tesseract.py
) else (
    echo.
    echo ERROR: Tesseract installation failed
    echo Please install manually from:
    echo https://github.com/UB-Mannheim/tesseract/wiki
)

pause
