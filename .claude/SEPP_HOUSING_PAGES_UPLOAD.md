# SEPP Housing 2021 PDF Pages - Upload Complete

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
R2 Storage: `nsw-planning-pdfs/pdf-pages/sepp-housing-2021/`

## ✅ R2 Upload Complete

All 4 PDF pages successfully uploaded to R2 storage on 2026-01-10 using `upload_sepp_housing_2021_pages.py`

**Upload Method**: Python boto3 script with R2 credentials from `.env`
```bash
python upload_sepp_housing_2021_pages.py
```

**Results**:
- Bucket: `nsw-planning-pdfs`
- Total uploaded: 4 files (1.1 MB)
- Status: All files uploaded successfully

## 🌐 Live URLs

Pages are publicly accessible at:
- `https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/pdf-pages/sepp-housing-2021/page-35_infill_affordable.png`
- `https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/pdf-pages/sepp-housing-2021/page-47_seniors_independent.png`
- `https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/pdf-pages/sepp-housing-2021/page-72_tod_affordable.png`
- `https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/pdf-pages/sepp-housing-2021/page-115_accessible_area_def.png`

Local development path (works in Next.js public directory):
- `/pdf-pages/sepp-housing-2021/page-35_infill_affordable.png`

## 🔧 Next Steps

1. ✅ Extract pages (DONE)
2. ✅ Upload to R2 (DONE)
3. ⏳ Add to StateLevelControls.tsx
4. ⏳ Test in frontend

## Frontend Integration

See `frontend-nextjs/public/pdf-pages/sepp-housing-2021/README.md` for URL constants to use in code.
