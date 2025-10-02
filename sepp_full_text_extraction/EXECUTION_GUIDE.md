# SEPP Full Text Extraction - Execution Guide

## Overview

This guide provides detailed instructions for extracting full legal text from SEPP PDFs and updating the database to support council verification.

## Prerequisites

### Software Requirements
```bash
# Python packages
pip install magic-pdf  # MinerU for PDF extraction
pip install psycopg2   # PostgreSQL database access

# System tools
pg_dump  # PostgreSQL backup utility (should be in PATH)
psql     # PostgreSQL client (should be in PATH)
```

### Verify Prerequisites
```bash
# Check magic-pdf
magic-pdf --version

# Check PostgreSQL tools
pg_dump --version
psql --version

# Check Python
python --version  # Should be 3.8+
```

## Quick Start

### Option 1: Run All Steps Automatically
```bash
cd sepp_full_text_extraction
python run_all.py
```

This will run all 5 steps sequentially with automatic verification.

### Option 2: Run Steps Manually

```bash
# Step 1: Extract SEPPs (10-30 minutes)
python 01_extract_sepps_mineru.py

# Step 2: Parse to JSON (2-5 minutes)
python 02_parse_markdown_to_json.py

# Step 3: Update schema (1-2 minutes)
python 03_update_database_schema.py

# Step 4: Import provisions (5-10 minutes)
python 04_import_full_provisions.py

# Step 5: Verify completeness (2-5 minutes)
python 05_verify_completeness.py
```

## Detailed Step-by-Step Instructions

### Step 1: Extract SEPPs with MinerU

**What it does:** Extracts full text from all SEPP PDFs using MinerU

**Expected output:**
- Markdown files in `docs/sepps/extracted/`
- `extraction_metadata.json` with extraction logs
- Each SEPP: 100KB-5MB of markdown text

**Success criteria:**
- All 8 SEPPs extracted
- Each SEPP >100KB extracted text
- Provisions contain chapter markers, clauses, definitions

**Verification:**
```bash
# Check extraction metadata
cat docs/sepps/extracted/extraction_metadata.json | grep successful_extractions

# Check file sizes
ls -lh docs/sepps/extracted/**/*.md
```

**Troubleshooting:**
- **MinerU timeout:** Increase timeout in script (line 75)
- **No markdown output:** Check PDF is readable: `pdfinfo <pdf_path>`
- **Small output:** PDF may be scanned image, not text

### Step 2: Parse Markdown to JSON

**What it does:** Converts markdown into structured provision JSON

**Expected output:**
- JSON files: `docs/sepps/extracted/*.json`
- `parsing_report.json` with statistics
- Each SEPP: 100-500 structured provisions

**Success criteria:**
- All 8 SEPPs parsed
- Provisions have ref_number, provision_text, metadata
- Cross-references identified

**Verification:**
```bash
# Check parsing report
cat docs/sepps/extracted/parsing_report.json | grep total_provisions

# Sample a JSON file
python -c "import json; data = json.load(open('docs/sepps/extracted/State_Environmental_Planning_Policy_(Sustainable_Buildings)_2022_-_NSW_Legislation.json')); print(f'Provisions: {len(data[\"provisions\"])}')"
```

**Troubleshooting:**
- **Low provision count:** Markdown headings may not match expected patterns
- **Missing text:** Check provision_text field is populated
- **Parse errors:** Check markdown file encoding (should be UTF-8)

### Step 3: Update Database Schema

**What it does:** Removes 500-char limit, adds metadata columns

**Expected output:**
- Schema backup in `backups/`
- `provision_text` column now unlimited TEXT
- New columns: `full_text_length`, `extraction_method`, `last_updated`

**Success criteria:**
- Backup created successfully
- Schema update committed
- No rollback errors

**Verification:**
```bash
# Check schema
psql -U postgres -d nsw_planning -c "\d regulatory_provisions"

# Verify columns exist
psql -U postgres -d nsw_planning -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_name='regulatory_provisions' AND column_name IN ('full_text_length', 'extraction_method')"
```

**Troubleshooting:**
- **Backup fails:** Check pg_dump in PATH and PostgreSQL permissions
- **Schema update fails:** Restore from backup before retrying
- **Permission denied:** Run as postgres user or grant ALTER permissions

### Step 4: Import Full Provisions

**What it does:** Imports full text from JSON to database

**Expected output:**
- Updated provisions with full text
- `import_log.json` with statistics
- Provisions now 500-5000+ chars

**Success criteria:**
- All matched provisions updated
- New provisions inserted
- extraction_method = 'mineru' for updated provisions

**Verification:**
```bash
# Check import log
cat docs/sepps/extracted/import_log.json | grep provisions_updated

# Sample database provisions
psql -U postgres -d nsw_planning -c "SELECT id, ref_number, full_text_length, extraction_method FROM regulatory_provisions WHERE extraction_method='mineru' LIMIT 5"

# Check text length distribution
psql -U postgres -d nsw_planning -c "SELECT AVG(full_text_length), MIN(full_text_length), MAX(full_text_length) FROM regulatory_provisions WHERE extraction_method='mineru'"
```

**Troubleshooting:**
- **No matches found:** Document IDs may not match between JSON and database
- **Import fails:** Check database connection and permissions
- **Duplicate errors:** Provisions may already exist, update instead of insert

### Step 5: Verify Completeness

**What it does:** Runs comprehensive tests and generates verification reports

**Expected output:**
- `docs/sepps/verification/completeness_report.json`
- `docs/sepps/verification/sample_provisions_for_council.txt`
- `docs/sepps/verification/test_results.json`

**Success criteria:**
- All tests pass
- No truncated provisions from MinerU
- Sample provisions contain full legal text

**Verification:**
```bash
# Check completeness report
cat docs/sepps/verification/completeness_report.json | grep all_tests_passed

# Review sample provisions
head -100 docs/sepps/verification/sample_provisions_for_council.txt
```

**Troubleshooting:**
- **Tests fail:** Review test details in completeness_report.json
- **Short provisions:** May be legitimately short (definitions, cross-refs)
- **Content checks fail:** Verify required keywords appropriate for provision type

## Output Files

### Extraction Outputs
```
docs/sepps/extracted/
├── extraction_metadata.json           # Extraction logs and stats
├── parsing_report.json                # Parsing results
├── import_log.json                    # Database import log
├── State_.../*.md                     # MinerU markdown output
└── State_.../*.json                   # Structured provisions
```

### Verification Outputs
```
docs/sepps/verification/
├── completeness_report.json           # Test results summary
├── sample_provisions_for_council.txt  # Full text samples for review
└── test_results.json                  # Detailed test data
```

### Backups
```
backups/
└── schema_backup_YYYYMMDD_HHMMSS.sql  # Database schema backup
```

## Recovery Procedures

### If Extraction Fails
```bash
# Re-run extraction for specific SEPP
python 01_extract_sepps_mineru.py
# Then manually edit extraction_metadata.json to mark as successful
```

### If Schema Update Fails
```bash
# Restore from backup
psql -U postgres -d nsw_planning -f backups/schema_backup_YYYYMMDD_HHMMSS.sql

# Re-run schema update
python 03_update_database_schema.py
```

### If Import Fails
```bash
# Check import log for errors
cat docs/sepps/extracted/import_log.json

# Re-run import (idempotent - safe to retry)
python 04_import_full_provisions.py
```

## Validation Queries

### Check Provision Lengths
```sql
SELECT
  extraction_method,
  COUNT(*) as count,
  AVG(full_text_length) as avg_length,
  MIN(full_text_length) as min_length,
  MAX(full_text_length) as max_length
FROM regulatory_provisions
WHERE document_id LIKE '%State_Environmental_Planning_Policy%'
GROUP BY extraction_method;
```

### Find Specific Provision
```sql
SELECT id, ref_number, full_text_length, LEFT(provision_text, 200) as preview
FROM regulatory_provisions
WHERE id = 18945;  -- Thermal energy waste provision
```

### Check Import Coverage
```sql
SELECT
  document_id,
  COUNT(*) as provisions,
  COUNT(*) FILTER (WHERE extraction_method = 'mineru') as mineru_count,
  COUNT(*) FILTER (WHERE full_text_length > 500) as full_text_count
FROM regulatory_provisions
WHERE document_id LIKE '%State_Environmental_Planning_Policy%'
GROUP BY document_id
ORDER BY document_id;
```

## Performance Considerations

### Extraction Speed
- **MinerU extraction:** ~2-5 minutes per SEPP
- **Total extraction time:** 15-30 minutes for all 8 SEPPs
- **Factors:** PDF size, complexity, system resources

### Database Import Speed
- **Matching:** ~1-2 seconds per 1000 provisions
- **Updates:** ~10-20 provisions per second
- **Total import time:** 5-10 minutes for all SEPPs

### Storage Requirements
- **Extracted markdown:** ~10-50 MB
- **JSON provisions:** ~20-100 MB
- **Database increase:** ~50-200 MB

## Next Steps

After successful extraction and import:

1. **Review Sample Provisions**
   - Check `docs/sepps/verification/sample_provisions_for_council.txt`
   - Verify full legal text is present and readable

2. **Test Database Queries**
   - Query specific provisions by ID
   - Test provision search and filtering
   - Verify full text is returned in API responses

3. **Update API Endpoints**
   - Ensure API returns `provision_text` field
   - Add `full_text_length` to responses
   - Implement provision detail endpoint for council review

4. **Council Verification**
   - Provide sample provisions to council planners
   - Confirm text matches official legislation
   - Validate provision references are correct

## Support

If issues persist:

1. Check logs in `docs/sepps/extracted/`
2. Review error messages in console output
3. Verify database connection and permissions
4. Ensure all prerequisites are installed

## Appendix: Expected Provision Counts

| SEPP                              | Expected Provisions | Avg Length (chars) |
|-----------------------------------|--------------------:|-------------------:|
| Sustainable Buildings 2022        |            120-150 |           800-1500 |
| Transport & Infrastructure 2021   |             50-100 |          600-1200 |
| Planning Systems 2021             |            150-200 |          800-2000 |
| Housing 2021                      |            200-300 |          700-1500 |
| Biodiversity & Conservation 2021  |            250-350 |          900-2000 |
| Resilience & Hazards 2021         |            100-150 |          700-1400 |
| Industry & Employment 2021        |            100-150 |          800-1600 |
| Primary Production 2021           |             80-120 |          700-1300 |

**Total Expected:** 1050-1500 provisions with full legal text