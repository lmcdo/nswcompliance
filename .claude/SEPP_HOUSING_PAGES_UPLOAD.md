# SEPP Housing 2021 PDF Pages - Upload Instructions

## ✅ Extracted Pages

Successfully extracted 4 pages from SEPP Housing 2021 PDF:

| Page | File | Size | Provision | Description |
|------|------|------|-----------|-------------|
| 35 | page-35_infill_affordable.png | 274 KB | provision_597 | In-Fill Affordable: 0.2 spaces/dwelling in accessible area |
| 47 | page-47_seniors_independent.png | 249 KB | provision_765/766 | Seniors: 1/5 dwellings (social) OR 0.5/bedroom |
| 72 | page-72_tod_affordable.png | 294 KB | provision_1189 | TOD Affordable: 0.4/0.5/1.0 by bedrooms |
| 115 | page-115_accessible_area_def.png | 298 KB | Schedule 10 | Accessible Area: 800m rail, 400m bus |

## 📂 Files Location

Local: `scripts/sepp-housing-2021-pages/`
Public (gitignored): `frontend-nextjs/public/pdf-pages/sepp-housing-2021/`

## ⚠️ Upload Required

PDF pages are in .gitignore (too large for git). Need to upload to R2 storage.

### R2 Upload Process

Current rclone config has read-only access. To upload:

1. **Option A: Use Cloudflare Dashboard**
   - Go to Cloudflare R2 bucket: `plotdetect-public`
   - Navigate to `pdf-pages/sepp-housing-2021/`
   - Upload the 4 PNG files manually

2. **Option B: Configure rclone write access**
   ```bash
   rclone config update r2
   # Update with write-enabled API token
   ```

3. **Option C: Use wrangler CLI**
   ```bash
   wrangler r2 object put plotdetect-public/pdf-pages/sepp-housing-2021/page-35_infill_affordable.png \
     --file scripts/sepp-housing-2021-pages/page-35_infill_affordable.png
   ```

### Target URLs

After upload, pages will be available at:
- `https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/pdf-pages/sepp-housing-2021/page-35_infill_affordable.png`
- `https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/pdf-pages/sepp-housing-2021/page-47_seniors_independent.png`
- `https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/pdf-pages/sepp-housing-2021/page-72_tod_affordable.png`
- `https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/pdf-pages/sepp-housing-2021/page-115_accessible_area_def.png`

OR use local public path (for development):
- `/pdf-pages/sepp-housing-2021/page-35_infill_affordable.png`

## 🔧 Next Steps

1. ✅ Extract pages (DONE)
2. ⏳ Upload to R2 (NEEDS R2 CREDENTIALS)
3. ⏳ Add to StateLevelControls.tsx
4. ⏳ Test in frontend

## Frontend Integration

See `frontend-nextjs/public/pdf-pages/sepp-housing-2021/README.md` for URL constants to use in code.
