# PostGIS Installation for Windows - PostgreSQL 17

## Option 1: Stack Builder (Recommended - GUI)

1. **Launch Stack Builder**:
   - Start Menu → PostgreSQL 17 → Application Stack Builder
   - Or run: `C:\Program Files\PostgreSQL\17\bin\StackBuilder.exe`

2. **Select PostgreSQL Installation**:
   - Choose: PostgreSQL 17 on port 5432

3. **Select PostGIS**:
   - Navigate to: Categories → Spatial Extensions
   - Check: PostGIS 3.4 Bundle for PostgreSQL 17
   - Click Next

4. **Install**:
   - Download and install
   - When prompted for password, use: `Duffysql1!`

5. **Verify**:
   - Run: `python install_postgis.py`
   - Should show: `PostGIS installed: True`

---

## Option 2: Manual Download (If Stack Builder unavailable)

1. **Download PostGIS for Windows**:
   ```
   URL: https://download.osgeo.org/postgis/windows/pg17/
   File: postgis-bundle-pg17-3.4.2x64.zip
   ```

2. **Extract and Copy Files**:
   ```powershell
   # Extract the downloaded ZIP
   # Copy files to PostgreSQL installation directory:

   # Copy DLLs
   xcopy postgis-bundle-pg17\bin\*.dll "C:\Program Files\PostgreSQL\17\bin\" /Y

   # Copy extensions
   xcopy postgis-bundle-pg17\share\extension\* "C:\Program Files\PostgreSQL\17\share\extension\" /Y /S

   # Copy libs
   xcopy postgis-bundle-pg17\lib\* "C:\Program Files\PostgreSQL\17\lib\" /Y /S
   ```

3. **Verify**:
   ```powershell
   # Check if postgis.control exists
   dir "C:\Program Files\PostgreSQL\17\share\extension\postgis.control"
   ```

4. **Install Extension**:
   ```powershell
   python install_postgis.py
   ```

---

## Option 3: Using Application Stack Builder Executable

If you can't find Stack Builder in the Start Menu, run this command:

```powershell
cd "C:\Program Files\PostgreSQL\17\bin"
.\stackbuilder.exe
```

---

## Quick Install Script (PowerShell as Administrator)

```powershell
# Download PostGIS bundle
$url = "https://download.osgeo.org/postgis/windows/pg17/postgis-bundle-pg17-3.4.2x64.zip"
$output = "$env:TEMP\postgis-bundle.zip"
$extract = "$env:TEMP\postgis-bundle"

Write-Host "Downloading PostGIS bundle..."
Invoke-WebRequest -Uri $url -OutFile $output

Write-Host "Extracting files..."
Expand-Archive -Path $output -DestinationPath $extract -Force

Write-Host "Installing to PostgreSQL directory..."
# Copy bin files
Copy-Item "$extract\postgis-bundle-pg17-3.4.2x64\bin\*.dll" "C:\Program Files\PostgreSQL\17\bin\" -Force

# Copy extension files
Copy-Item "$extract\postgis-bundle-pg17-3.4.2x64\share\extension\*" "C:\Program Files\PostgreSQL\17\share\extension\" -Recurse -Force

# Copy lib files
Copy-Item "$extract\postgis-bundle-pg17-3.4.2x64\lib\*" "C:\Program Files\PostgreSQL\17\lib\" -Recurse -Force

Write-Host "PostGIS files installed successfully!"
Write-Host "Now run: python install_postgis.py"
```

Save as `install_postgis.ps1` and run as Administrator.

---

## Troubleshooting

### Error: "extension postgis is not available"
- PostGIS binaries not installed
- Solution: Follow Option 1 or 2 above

### Error: "could not load library"
- Missing DLL dependencies
- Solution: Install Visual C++ Redistributable 2022 (x64)
- Download: https://aka.ms/vs/17/release/vc_redist.x64.exe

### Error: "permission denied"
- Installing files requires admin privileges
- Solution: Run PowerShell as Administrator

---

## Next Steps After Installation

Once PostGIS is installed:

1. **Create boundaries table**:
   ```bash
   python create_precinct_boundaries_table.py
   ```

2. **Extract precinct boundaries**:
   ```bash
   python extract_precinct_boundaries.py
   ```

3. **Update precinct service**:
   - Implement geometric matching in `frontend-nextjs/lib/precinct-service.ts`

4. **Test**:
   ```bash
   python test_precinct_matching.py
   ```
