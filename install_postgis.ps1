# PostGIS Installation Script for PostgreSQL 17 on Windows
# Run as Administrator

$ErrorActionPreference = "Stop"

Write-Host "=== PostGIS Installation for PostgreSQL 17 ===" -ForegroundColor Cyan
Write-Host ""

# Configuration
$postgisUrl = "https://download.osgeo.org/postgis/windows/pg17/postgis-bundle-pg17-3.5.3x64.zip"
$tempDir = "$env:TEMP\postgis-install"
$zipFile = "$tempDir\postgis-bundle.zip"
$extractDir = "$tempDir\extract"
$pgDir = "C:\Program Files\PostgreSQL\17"

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Check if PostgreSQL 17 is installed
if (-not (Test-Path $pgDir)) {
    Write-Host "ERROR: PostgreSQL 17 not found at $pgDir" -ForegroundColor Red
    exit 1
}

Write-Host "PostgreSQL 17 found at: $pgDir" -ForegroundColor Green

# Create temp directory
Write-Host "Creating temporary directory..."
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
New-Item -ItemType Directory -Force -Path $extractDir | Out-Null

# Download PostGIS bundle
Write-Host "Downloading PostGIS bundle from osgeo.org..."
Write-Host "URL: $postgisUrl" -ForegroundColor Gray
try {
    Invoke-WebRequest -Uri $postgisUrl -OutFile $zipFile -UseBasicParsing
    Write-Host "Download complete!" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Failed to download PostGIS bundle" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

# Extract ZIP
Write-Host "Extracting PostGIS bundle..."
try {
    Expand-Archive -Path $zipFile -DestinationPath $extractDir -Force
    Write-Host "Extraction complete!" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Failed to extract ZIP file" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

# Find the extracted directory (may vary)
$postgisExtracted = Get-ChildItem -Path $extractDir -Directory | Select-Object -First 1
if (-not $postgisExtracted) {
    Write-Host "ERROR: Could not find extracted PostGIS directory" -ForegroundColor Red
    exit 1
}

Write-Host "Found PostGIS directory: $($postgisExtracted.Name)" -ForegroundColor Gray

# Copy files to PostgreSQL installation
Write-Host ""
Write-Host "Installing PostGIS files to PostgreSQL directory..." -ForegroundColor Cyan

# Copy bin files (DLLs)
Write-Host "  - Copying DLL files to bin..."
$binSource = Join-Path $postgisExtracted.FullName "bin"
$binDest = Join-Path $pgDir "bin"
if (Test-Path $binSource) {
    Copy-Item "$binSource\*.dll" $binDest -Force -ErrorAction SilentlyContinue
    Write-Host "    Copied DLL files" -ForegroundColor Green
}

# Copy extension files
Write-Host "  - Copying extension files..."
$shareSource = Join-Path $postgisExtracted.FullName "share\extension"
$shareDest = Join-Path $pgDir "share\extension"
if (Test-Path $shareSource) {
    Copy-Item "$shareSource\*" $shareDest -Recurse -Force
    Write-Host "    Copied extension files" -ForegroundColor Green
}

# Copy lib files
Write-Host "  - Copying library files..."
$libSource = Join-Path $postgisExtracted.FullName "lib"
$libDest = Join-Path $pgDir "lib"
if (Test-Path $libSource) {
    Copy-Item "$libSource\*" $libDest -Recurse -Force
    Write-Host "    Copied library files" -ForegroundColor Green
}

# Verify installation
Write-Host ""
Write-Host "Verifying PostGIS installation..." -ForegroundColor Cyan
$postgisControl = Join-Path $pgDir "share\extension\postgis.control"
if (Test-Path $postgisControl) {
    Write-Host "SUCCESS: postgis.control found!" -ForegroundColor Green
} else {
    Write-Host "WARNING: postgis.control not found" -ForegroundColor Yellow
    Write-Host "Path checked: $postgisControl" -ForegroundColor Gray
}

# Cleanup
Write-Host ""
Write-Host "Cleaning up temporary files..."
Remove-Item -Path $tempDir -Recurse -Force
Write-Host "Cleanup complete!" -ForegroundColor Green

# Final message
Write-Host ""
Write-Host "=== PostGIS Installation Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Run: python install_postgis.py" -ForegroundColor White
Write-Host "2. Run: python create_precinct_boundaries_table.py" -ForegroundColor White
Write-Host "3. Run: python extract_precinct_boundaries.py" -ForegroundColor White
Write-Host ""
