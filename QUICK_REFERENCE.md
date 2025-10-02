# SEPP Extraction - Quick Reference

## Status Check

```bash
# Overall summary
python sepp_extraction_summary.py

# Before/after comparison
python before_after_example.py

# Check MinerU provisions
python check_mineru_imports.py
```

## Current Coverage: 14% (664 / 4,743 provisions)

### Why Only 14%?
- ❌ **Missing:** "Exempt and Complying Development Codes" (3,237 provisions = 68%)
- ❌ **Partial:** "Housing" sections (712 provisions = 15%)
- ✅ **Complete:** 8 other SEPPs (794 provisions = 17%)

## Quick Expand to 85%

1. Download missing PDF:
   ```
   "State Environmental Planning Policy (Exempt and Complying Development Codes) 2008"
   ```

2. Place in: `docs/sepps/`

3. Run pipeline:
   ```bash
   python sepp_full_text_extraction/01_extract_sepps_mineru.py
   python sepp_full_text_extraction/02_parse_markdown_to_json_FIXED.py
   python sepp_full_text_extraction/04_import_full_provisions_FIXED.py
   ```

## Database Backups

### Created Today (2025-09-30)
```
backups/pre_step4_schema_backup_20250930_092056.json    (5.7 KB)
backups/nsw_planning_backup_metadata_20250930_092132.json    (624 B)
```

### Restore From Backup
```python
# View backup
import json
with open('backups/nsw_planning_backup_metadata_20250930_092132.json') as f:
    print(json.dumps(json.load(f), indent=2))
```

## Safety Checks

### Before Any Database Operation
```bash
./scripts/db_safety_check.sh
```

### Create New Backup
```bash
python create_database_backup.py
python create_full_sql_backup.py
```

## Files Reference

| Type | Location | Purpose |
|------|----------|---------|
| **Pipeline** | `sepp_full_text_extraction/` | Extraction tools |
| **Data** | `docs/sepps/extracted/` | Parsed provisions |
| **Backups** | `backups/` | Database backups |
| **Docs** | Root | Documentation |

## Key Metrics

```
Text Quality:
  OLD: 143 chars avg, max 500    ❌ Truncated
  NEW: 1,695 chars avg, max 11,818  ✅ Complete
  Improvement: 11.8x

Extraction Methods:
  autoschema: 21,947 provisions (143 chars avg)
  mineru:        664 provisions (1,695 chars avg)

Relationships Extracted: 872
  - Clause references: 317
  - Other SEPPs: 281
  - Schedules: 85
  - Maps: 85
  - Definitions: 98
  - Tables: 6
```

## Troubleshooting

### "pg_dump not found"
- Expected on Windows
- JSON backups still work
- Alternative: Use pgAdmin for SQL export

### "No provisions matched"
- Check document_id format in database
- Verify PDF was extracted
- Check parsing_report.json for errors

### "Duplicate key error"
- Sequence fixed in new script
- Use: `04_import_full_provisions_FIXED.py`

## Contact

See full documentation:
- `SEPP_EXTRACTION_COMPLETE.md` - Technical details
- `COVERAGE_ANALYSIS.md` - Why 14% coverage
- `sepp_full_text_extraction/EXECUTION_GUIDE.md` - How to run