# SEPP Full Text Extraction & Database Migration

## Problem Statement

Current database provisions are truncated at 500 characters, making full legal text unavailable for council verification. SEPPs were extracted using AutoSchema which only captured document headers (1-2KB) instead of full legal text (100-500KB per SEPP).

## Objectives

1. Re-extract all SEPP PDFs with MinerU to get full legal text
2. Store extracted JSON alongside PDFs in `docs/sepps/`
3. Remove 500-character truncation from database import
4. Migrate existing provisions to full text
5. Verify completeness with automated tests

## Technical Implementation

### Phase 1: Full Text Extraction with MinerU
- Extract all 8 SEPP PDFs using MinerU
- Convert markdown output to structured JSON
- Store JSON files in `docs/sepps/extracted/`
- Verify extraction completeness

### Phase 2: Database Schema Update
- Remove 500-char truncation limit
- Add `full_text_length` column for verification
- Add `extraction_method` column ('mineru', 'autoschema', 'manual')
- Add `extraction_timestamp` for tracking

### Phase 3: Provision Re-import
- Parse MinerU markdown into provisions
- Match provisions to existing database records
- Update with full text
- Preserve all existing relationships

### Phase 4: Verification & Testing
- Automated completeness checks
- Provision length validation
- Content verification tests
- Council verification report generation

## Directory Structure

```
docs/sepps/
├── *.pdf                           # Original SEPP PDFs
├── extracted/                      # New extraction output
│   ├── *.md                       # MinerU markdown output
│   ├── *.json                     # Structured provision data
│   └── extraction_metadata.json   # Extraction logs
└── verification/                   # Test outputs
    ├── completeness_report.json
    ├── provision_lengths.json
    └── sample_provisions.txt
```

## Scripts

1. `01_extract_sepps_mineru.py` - Run MinerU extraction
2. `02_parse_markdown_to_json.py` - Convert MD to structured JSON
3. `03_update_database_schema.py` - Add new columns, remove limits
4. `04_import_full_provisions.py` - Import full text to database
5. `05_verify_completeness.py` - Run all verification tests

## Execution Order

Run scripts in numbered order. Each script produces verification output and exits with status code 0 on success.