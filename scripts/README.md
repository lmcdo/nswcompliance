# SEPP Curation Utilities

Utilities for curating SEPP requirements in Phases 3+.

## Quick Start

```bash
# 1. Extract PDF pages (manual - use PyMuPDF or similar)

# 2. Upload PDFs to R2
python scripts/r2_pdf_uploader.py sepp-name 20 21 23

# 3. Create requirement_data.json using template
cp scripts/templates/sepp_requirement_template.json my_requirement.json
# Edit my_requirement.json with actual data

# 4. Validate schema and brand safety
python scripts/validate_requirement_data.py my_requirement.json

# 5. Validate PDF coverage
python scripts/validate_pdf_coverage.py my_requirement.json

# 6. Insert into database (use existing Node.js scripts)
# 7. Deploy and test
```

---

## Utilities

### 1. `r2_pdf_uploader.py`

Upload PDF page images to Cloudflare R2 storage.

**Usage:**
```bash
# Upload single page
python scripts/r2_pdf_uploader.py sepp-resilience-hazards 23

# Upload multiple pages
python scripts/r2_pdf_uploader.py sepp-housing-2021 35 47 72 115
```

**Requirements:**
- R2 credentials in `.env` (R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY)
- Local PDF pages in `frontend-nextjs/public/pdf-pages/{sepp-name}/page-{num}.png`
- boto3, python-dotenv

**Features:**
- Uses boto3 (NOT wrangler - learned from Phase 1)
- Uploads with ContentType=image/png
- Verifies upload with HTTP HEAD request
- Returns public R2 URLs

---

### 2. `validate_requirement_data.py`

Validate requirement_data JSON against schema and brand safety rules.

**Usage:**
```bash
python scripts/validate_requirement_data.py my_requirement.json
```

**Validation checks:**
- Required fields: title, categories
- Categories structure (name, reference, requirements)
- **BRAND SAFETY**: No cost estimates in categories (e.g., "$8-15k")
- **BRAND SAFETY**: No timeline estimates in categories (e.g., "4-6 weeks")
- PDF references have required fields
- PDF URLs are absolute R2 URLs
- PDF references sorted by page number
- feasibility_note structure (if present)

**Example output:**
```
Validating: my_requirement.json
============================================================

ERROR ERRORS (2):
  • BRAND SAFETY: categories[0].requirements[1] has cost estimate
  • pdf_references[2].url must be absolute R2 URL

WARNING WARNINGS (1):
  • pdf_references not sorted by page number

ERROR Failed with 2 errors
```

---

### 3. `validate_pdf_coverage.py`

Verify all referenced sections have PDF pages (local AND R2).

**Usage:**
```bash
python scripts/validate_pdf_coverage.py my_requirement.json
```

**Checks:**
- Local files exist in `frontend-nextjs/public/pdf-pages/`
- R2 URLs return HTTP 200
- Reports missing/inaccessible PDFs

**Example output:**
```
Validating PDF coverage: my_requirement.json
============================================================

ERROR MISSING LOCAL FILES (1):
  Page 23 (Section 4.7): frontend-nextjs/public/pdf-pages/sepp-name/page-23.png

ERROR INACCESSIBLE R2 URLS (1):
  Page 23 (Section 4.7): HTTP 404
```

---

## Template

### `templates/sepp_requirement_template.json`

Starting point for new SEPP requirements. Copy and modify for Phase 3+.

**Key sections:**
- `title`: SEPP name and section
- `description`: Optional context
- `categories[]`: Regulatory requirements ONLY (no costs/timelines)
- `pdf_references[]`: Sorted by page number, absolute R2 URLs
- `feasibility_note`: Optional guidance with authoritative links

**Remove before database insert:**
- `_instructions` key (documentation only)

---

## Brand Safety Rules (Critical)

**DO NOT include in `categories`:**
- Cost estimates ($8-15k, $50,000, etc.)
- Timeline estimates (4-6 weeks, 3-12 months, etc.)
- AI interpretation or paraphrasing
- Professional opinions

**ONLY include in `categories`:**
- Exact clauses from legislation
- Specific legal requirements
- Explicit standards/thresholds
- Direct quotes with `legal_text` field

**Generic guidance goes in `feasibility_note`:**
- Site-specific variation acknowledgment
- Links to NSW EPA, Planning Portal (authoritative only)
- Generic "consult expert" advice

---

## Workflow for Phase 3+

1. **Identify sections** - Map exact clauses to PDF pages
2. **Extract PDFs** - PyMuPDF with 2x zoom
3. **Upload to R2** - `r2_pdf_uploader.py`
4. **Create JSON** - Copy template, fill with EXACT regulatory text
5. **Validate schema** - `validate_requirement_data.py` (catches brand safety violations)
6. **Validate PDFs** - `validate_pdf_coverage.py` (catches missing pages)
7. **Insert to database** - Use existing Node.js scripts
8. **Test in UI** - Verify PDF buttons, collapsible sections work
9. **Git commit and deploy**

---

## Lessons from Phase 1 (Contamination)

**Use boto3, NOT wrangler:**
- Wrangler defaults to local simulator
- Wrangler requires `--remote` + CLOUDFLARE_API_TOKEN
- boto3 "just works" with R2 credentials from `.env`

**Separate regulation from guidance:**
- Mixed cost estimates ($8-15k) with legal requirements = brand safety violation
- Caused user to question credibility
- Solution: Pure regulation in `categories`, generic guidance in `feasibility_note`

**Verify PDF coverage early:**
- Phase 1 discovered missing page 23 late in process
- `validate_pdf_coverage.py` catches this upfront

**Zone-based vs dev-type-based:**
- Contamination applies to ZONES (E4, IN1), not dev types
- Database structure needs to support "applies to all dev types"

---

## Dependencies

```bash
pip install boto3 python-dotenv requests
```

---

## Future: High-Level Skill

After Phase 3 validates these utilities, build `.claude/skills/sepp-curator/skill.md` to orchestrate:
1. PDF extraction guidance
2. R2 upload (automated)
3. Template generation (interactive)
4. Validation (automated)
5. Database insert (guided)
6. Git commit (automated)

Defer until utilities proven in practice.
