# Upload Precinct PDFs to Cloudflare R2

## ✅ Storage Check (PASSED)
- **Total size**: 244 MB (112 PDFs)
- **R2 Free Tier**: 10 GB/month
- **Usage**: 2.4% of free tier
- **Cost**: **$0.00** ✅

---

## Step 1: Install Rclone

### Windows (PowerShell - Run as Administrator)
```powershell
# Download rclone
Invoke-WebRequest -Uri "https://downloads.rclone.org/rclone-current-windows-amd64.zip" -OutFile "$env:TEMP\rclone.zip"

# Extract
Expand-Archive -Path "$env:TEMP\rclone.zip" -DestinationPath "$env:TEMP\rclone" -Force

# Copy to Program Files
$rclonePath = "C:\Program Files\rclone"
New-Item -ItemType Directory -Force -Path $rclonePath
Copy-Item -Path "$env:TEMP\rclone\rclone-*\rclone.exe" -Destination "$rclonePath\rclone.exe"

# Add to PATH
$currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
if ($currentPath -notlike "*$rclonePath*") {
    [Environment]::SetEnvironmentVariable("Path", "$currentPath;$rclonePath", "Machine")
}

# Verify installation (restart PowerShell first!)
rclone version
```

---

## Step 2: Get Cloudflare R2 Credentials

1. **Go to Cloudflare Dashboard**:
   - Visit: https://dash.cloudflare.com
   - Navigate to: **R2** → **Overview**

2. **Get Account ID**:
   - Look for "Account ID" on the right sidebar
   - Copy it (looks like: `abc123def456...`)

3. **Create API Token**:
   - Click **"Manage R2 API Tokens"**
   - Click **"Create API Token"**
   - Name: `rclone-upload`
   - Permissions: **Object Read & Write**
   - Click **"Create API Token"**
   - **SAVE BOTH**: Access Key ID and Secret Access Key

---

## Step 3: Configure Rclone for R2

```powershell
rclone config
```

### Interactive Configuration:
```
n) New remote
name> r2
Type of storage> s3
Choose a number from below, or type in your own value.
 5 / Cloudflare R2 Storage
provider> Cloudflare
Option env_auth.
Enter a boolean value (true or false). Press Enter for the default (false).
env_auth> false
Option access_key_id.
AWS Access Key ID.
access_key_id> [PASTE YOUR ACCESS KEY ID]
Option secret_access_key.
AWS Secret Access Key (password).
secret_access_key> [PASTE YOUR SECRET ACCESS KEY]
Option region.
Leave blank if you are using an S3 clone and you don't have a region.
region> [PRESS ENTER]
Option endpoint.
Endpoint for S3 API.
endpoint> https://[YOUR-ACCOUNT-ID].r2.cloudflarestorage.com
Advanced config? (y/n)
y/n> n
Edit advanced config? (y/n)
y/n> n
Keep this "r2" remote? (y/n)
y/n> y
```

**Verify:**
```powershell
rclone lsd r2:pub-7f3b945f2f0045d6991a6b9d6db51cd8
```

---

## Step 4: Upload Precinct PDFs

### Option A: Use the Upload Script (Recommended)
```powershell
.\upload_precincts_to_r2.ps1
```

### Option B: Manual Upload (if script fails)

#### Upload Marrickville Precincts (67 MB)
```powershell
Get-ChildItem -Path ".\output" -Directory | Where-Object {
    $_.Name -match "^Marrickville DCP 2011 - 9 \d+"
} | ForEach-Object {
    $folderName = $_.Name
    $pdfPath = Join-Path $_.FullName "auto\${folderName}_origin.pdf"
    if (Test-Path $pdfPath) {
        Write-Host "Uploading: $folderName" -ForegroundColor Green
        rclone copy "$pdfPath" "r2:pub-7f3b945f2f0045d6991a6b9d6db51cd8/dcps/INNERWEST/marrickville/precincts/$folderName/" --progress
    }
}
```

#### Upload Leichhardt Precincts (52 MB)
```powershell
Get-ChildItem -Path ".\output" -Directory | Where-Object {
    $_.Name -match "Leichhardt DCP 2013.*(Part C Section 2|Part G Section)"
} | ForEach-Object {
    $folderName = $_.Name
    $pdfPath = Join-Path $_.FullName "auto\${folderName}_origin.pdf"
    if (Test-Path $pdfPath) {
        Write-Host "Uploading: $folderName" -ForegroundColor Green
        rclone copy "$pdfPath" "r2:pub-7f3b945f2f0045d6991a6b9d6db51cd8/dcps/INNERWEST/leichhardt/precincts/$folderName/" --progress
    }
}
```

#### Upload Ashfield Precincts (if individual PDFs exist)
```powershell
# Check if Ashfield Chapter D has individual precinct PDFs
Get-ChildItem -Path ".\output" -Directory | Where-Object {
    $_.Name -match "Inner West Ashfield.*Chapter D"
} | ForEach-Object {
    Write-Host "Ashfield Chapter D: $($_.Name)"
    Get-ChildItem -Path $_.FullName -Recurse -Filter "*_origin.pdf"
}
```

---

## Step 5: Verify Upload

```powershell
# List all uploaded precincts
rclone lsf r2:pub-7f3b945f2f0045d6991a6b9d6db51cd8/dcps/INNERWEST/ --dirs-only

# Check Marrickville precincts
rclone lsf r2:pub-7f3b945f2f0045d6991a6b9d6db51cd8/dcps/INNERWEST/marrickville/precincts/ --dirs-only

# Check specific precinct PDF
rclone ls r2:pub-7f3b945f2f0045d6991a6b9d6db51cd8/dcps/INNERWEST/marrickville/precincts/ | grep "9 13 Henson Park"
```

---

## Step 6: Test in Browser

1. **Open app**: http://localhost:3000/assessment
2. **Enter address**: `150 Addison Rd, Marrickville NSW 2204, Australia`
3. **Check console** for:
   ```
   [PDF Mapper] Converted document_id: "Marrickville__DCP__2011__-__9__13__Henson__Park" → "Marrickville DCP 2011 - 9 13 Henson Park"
   [PDF Mapper] Constructed R2 path: https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/dcps/INNERWEST/marrickville/precincts/...
   ```
4. **Look for**: "Special Provisions" section with PDF buttons
5. **Click**: "View PDF Page 6" button
6. **Verify**: PDF.js modal opens with Henson Park precinct PDF

---

## Troubleshooting

### Upload fails with "403 Forbidden"
- Check API token permissions (need "Object Read & Write")
- Verify endpoint URL has correct account ID
- Regenerate API token if needed

### PDF button shows but PDF doesn't load
- Check browser console for 404 errors
- Verify R2 URL in console matches uploaded path
- Test direct access: `https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/dcps/INNERWEST/marrickville/precincts/Marrickville%20DCP%202011%20-%209%2013%20Henson%20Park/Marrickville%20DCP%202011%20-%209%2013%20Henson%20Park_origin.pdf`

### Rclone command not found (after install)
- Restart PowerShell
- Check PATH: `$env:Path -split ';' | Select-String rclone`
- Manually add to PATH if needed

---

## Cost Monitoring

**View R2 usage**:
- Cloudflare Dashboard → R2 → Storage → Usage
- Check "Storage Used" (should be ~244 MB after upload)
- Check "Class A Operations" (uploads)
- All should be well within free tier

**Free Tier Limits**:
- ✅ Storage: 10 GB/month (you're using 244 MB = 2.4%)
- ✅ Class A ops: 1M/month (uploads)
- ✅ Class B ops: 10M/month (downloads)
- ✅ Egress: 0 (using R2.dev domain)

---

## Next Steps After Upload

1. ✅ Verify all PDFs accessible via R2.dev URLs
2. ✅ Test PDF buttons across different precincts
3. ✅ Monitor console for any getPDFUrl() warnings
4. ✅ Update documentation with final R2 structure
5. ✅ Deploy code changes to production
