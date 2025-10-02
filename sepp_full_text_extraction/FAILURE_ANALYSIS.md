# SEPP Full Text Extraction - Failure Analysis & Mitigation

## Critical Failure Points & Mitigation Strategies

### STEP 1: MinerU Extraction Failures

#### 1.1 MinerU Not Installed
**Symptom:** `magic-pdf: command not found`
**Cause:** MinerU (magic-pdf) not installed or not in PATH
**Impact:** Complete pipeline failure before starting
**Mitigation:**
```bash
# Install MinerU
pip install magic-pdf

# Verify installation
magic-pdf --version

# If still fails, check PATH
which magic-pdf
```
**Recovery:** Install package, re-run Step 1

---

#### 1.2 PDF Files Missing
**Symptom:** `✗ Missing: State Environmental Planning Policy...`
**Cause:** SEPP PDFs not in `docs/sepps/` directory
**Impact:** Cannot extract missing SEPPs, reduced coverage
**Mitigation:**
- Check prerequisite: all 8 PDFs must be present
- Download missing PDFs from legislation.nsw.gov.au
- Verify file names match expected list exactly
**Recovery:** Download missing PDFs, re-run Step 1

---

#### 1.3 MinerU Extraction Timeout
**Symptom:** `✗ Timeout after 10 minutes`
**Cause:** Large/complex PDF taking too long to process
**Impact:** SEPP not extracted, missing provisions in database
**Mitigation:**
- Increase timeout in `01_extract_sepps_mineru.py` line 75:
  ```python
  timeout=1800  # Increase to 30 minutes
  ```
- Run extraction on faster machine
- Check PDF isn't corrupted
**Recovery:** Increase timeout, re-run Step 1 for failed SEPP

---

#### 1.4 Insufficient Output Size
**Symptom:** `⚠ Output size (50,000 bytes) below expected minimum`
**Cause:**
- PDF is scanned images, not text
- MinerU failed to extract properly
- PDF has OCR issues
**Impact:** Incomplete provisions, missing legal text
**Mitigation:**
- Check PDF is text-based: `pdftotext <pdf> - | wc -w`
- If scanned, need OCR: Add `-m ocr` flag to magic-pdf command
- Try alternative extraction: PyMuPDF with OCR
**Recovery:**
```bash
# Test if PDF has text
pdftotext "docs/sepps/State Environmental Planning Policy (Sustainable Buildings) 2022 - NSW Legislation.pdf" - | head -100

# If empty, PDF is scanned - use OCR mode
# Edit line 75 in 01_extract_sepps_mineru.py:
"-m", "ocr"  # Instead of "auto"
```

---

#### 1.5 MinerU Output Format Issues
**Symptom:** No `.md` files generated in output directory
**Cause:** MinerU changed output format or directory structure
**Impact:** Step 2 cannot find markdown files
**Mitigation:**
- Check MinerU documentation for current output format
- List output directory to find actual files:
  ```bash
  find docs/sepps/extracted -type f
  ```
- Update script line 100 to match actual output pattern
**Recovery:** Update file search pattern, re-run Step 1

---

#### 1.6 Disk Space Exhausted
**Symptom:** `IOError: No space left on device`
**Cause:** Extraction requires 500MB-2GB temporary space
**Impact:** Partial extractions, corrupted output files
**Mitigation:**
- Check disk space before starting:
  ```bash
  df -h .
  ```
- Ensure at least 3GB free space
- Clean temporary files: `rm -rf /tmp/magic-pdf-*`
**Recovery:** Free disk space, delete partial outputs, re-run Step 1

---

### STEP 2: Markdown Parsing Failures

#### 2.1 Markdown Files Not Found
**Symptom:** `✗ Markdown file not found`
**Cause:** Step 1 didn't complete successfully
**Impact:** No provisions parsed, database won't be updated
**Mitigation:**
- Verify Step 1 completed successfully
- Check `extraction_metadata.json` shows `success: true`
- Manually verify .md files exist:
  ```bash
  ls -lh docs/sepps/extracted/**/*.md
  ```
**Recovery:** Complete Step 1 first, then re-run Step 2

---

#### 2.2 Markdown Encoding Issues
**Symptom:** `UnicodeDecodeError: 'charmap' codec can't decode`
**Cause:** Markdown files not UTF-8 encoded
**Impact:** Parsing fails, provisions not extracted
**Mitigation:**
- Open markdown file with explicit encoding:
  ```python
  with open(md_file, 'r', encoding='utf-8', errors='ignore') as f:
  ```
- Convert file encoding:
  ```bash
  iconv -f ISO-8859-1 -t UTF-8 input.md > output.md
  ```
**Recovery:** Fix encoding in script line 111, re-run Step 2

---

#### 2.3 Provision Pattern Mismatch
**Symptom:** Very low provision count (< 20 provisions per SEPP)
**Cause:** Markdown heading patterns don't match expected regex
**Impact:** Most provisions not extracted, incomplete database
**Mitigation:**
- Manually inspect markdown file structure
- Check heading formats:
  ```bash
  grep '^#' docs/sepps/extracted/State*.md | head -20
  ```
- Update regex patterns in `02_parse_markdown_to_json.py` lines 25-32
**Example Fix:**
```python
# If clauses use format "3.1   Name of clause" instead of "3.1 Name"
'clause': re.compile(r'^#+\s*(\d+[A-Z]?)\s+(.+?)$', re.MULTILINE),
```
**Recovery:** Update patterns, re-run Step 2

---

#### 2.4 Memory Exhaustion
**Symptom:** `MemoryError` or process killed
**Cause:** Very large markdown files (>100MB) loaded entirely into memory
**Impact:** Parsing fails for large SEPPs
**Mitigation:**
- Process markdown in chunks instead of loading whole file
- Add streaming parser for large files
- Increase system memory or use swap
**Recovery:** Add chunked processing, re-run Step 2

---

### STEP 3: Database Schema Update Failures

#### 3.1 PostgreSQL Not Running
**Symptom:** `could not connect to server: Connection refused`
**Cause:** PostgreSQL service not started
**Impact:** Cannot update schema, pipeline blocked
**Mitigation:**
```bash
# Start PostgreSQL service
sudo service postgresql start

# Or on Windows
net start postgresql-x64-14

# Verify connection
psql -U postgres -d nsw_planning -c "SELECT 1"
```
**Recovery:** Start PostgreSQL, re-run Step 3

---

#### 3.2 Database Connection Permission Denied
**Symptom:** `FATAL: password authentication failed for user "postgres"`
**Cause:** Incorrect database credentials in `db_config.py`
**Impact:** Cannot access database, schema update fails
**Mitigation:**
- Verify credentials in `db_config.py`
- Test connection manually:
  ```bash
  psql -U postgres -d nsw_planning
  ```
- Update credentials or use `.pgpass` file
**Recovery:** Fix credentials, re-run Step 3

---

#### 3.3 Backup Creation Fails
**Symptom:** `✗ Backup failed: pg_dump: command not found`
**Cause:** PostgreSQL tools not in PATH
**Impact:** No backup created - risky to proceed with schema changes
**Mitigation:**
```bash
# Find pg_dump
find /usr -name pg_dump 2>/dev/null

# Add to PATH
export PATH=$PATH:/usr/lib/postgresql/14/bin

# Or use full path in script
```
**Recovery:** Install PostgreSQL client tools, re-run Step 3

---

#### 3.4 Schema Update Permission Denied
**Symptom:** `ERROR: must be owner of table regulatory_provisions`
**Cause:** Database user lacks ALTER TABLE permissions
**Impact:** Schema not updated, cannot store full text
**Mitigation:**
```sql
-- Grant permissions as superuser
psql -U postgres -d nsw_planning
GRANT ALL ON TABLE regulatory_provisions TO your_user;
ALTER TABLE regulatory_provisions OWNER TO your_user;
```
**Recovery:** Grant permissions, re-run Step 3

---

#### 3.5 Schema Already Updated
**Symptom:** `✓ Column already unlimited`
**Cause:** Step 3 already completed successfully in previous run
**Impact:** None - this is expected on re-runs
**Mitigation:** Skip to Step 4
**Recovery:** Not needed - continue to Step 4

---

#### 3.6 Column Type Conversion Fails
**Symptom:** `ERROR: column "provision_text" cannot be cast automatically`
**Cause:** Complex type conversion with existing data
**Impact:** Schema update incomplete
**Mitigation:**
```sql
-- Manual column update with explicit cast
ALTER TABLE regulatory_provisions
ALTER COLUMN provision_text TYPE TEXT
USING provision_text::TEXT;
```
**Recovery:** Run manual SQL, then re-run Step 3 verification

---

### STEP 4: Import Failures

#### 4.1 JSON Files Not Found
**Symptom:** `✗ Parsing report not found`
**Cause:** Step 2 didn't complete successfully
**Impact:** No provisions to import
**Mitigation:**
- Verify Step 2 completed successfully
- Check `parsing_report.json` exists:
  ```bash
  cat docs/sepps/extracted/parsing_report.json
  ```
**Recovery:** Complete Step 2, then re-run Step 4

---

#### 4.2 No Provision Matches Found
**Symptom:** `Exact matches: 0, New provisions: 1500`
**Cause:** Document ID format mismatch between JSON and database
**Impact:** All provisions treated as new inserts instead of updates
**Mitigation:**
- Check document_id format in database:
  ```sql
  SELECT DISTINCT document_id FROM regulatory_provisions WHERE document_id LIKE '%Sustainable%';
  ```
- Check document_id in JSON:
  ```bash
  python -c "import json; data=json.load(open('docs/sepps/extracted/State_Environmental_Planning_Policy_(Sustainable_Buildings)_2022_-_NSW_Legislation.json')); print(data['sepp_name'])"
  ```
- Update matching logic in script lines 150-180
**Recovery:** Fix document_id format matching, re-run Step 4

---

#### 4.3 Database Update Timeout
**Symptom:** `ERROR: canceling statement due to statement timeout`
**Cause:** Updating 1000+ provisions takes too long
**Impact:** Partial import, some provisions not updated
**Mitigation:**
```sql
-- Increase statement timeout
ALTER DATABASE nsw_planning SET statement_timeout = '600s';
```
Or in script:
```python
cur.execute("SET statement_timeout = '600s'")
```
**Recovery:** Increase timeout, re-run Step 4 (idempotent)

---

#### 4.4 Duplicate Key Violations
**Symptom:** `ERROR: duplicate key value violates unique constraint`
**Cause:** Trying to insert provisions that already exist
**Impact:** Some provisions not imported
**Mitigation:**
- Use UPSERT instead of INSERT:
  ```sql
  INSERT INTO regulatory_provisions (...) VALUES (...)
  ON CONFLICT (document_id, ref_number) DO UPDATE SET ...
  ```
- Or skip duplicates:
  ```sql
  ON CONFLICT DO NOTHING
  ```
**Recovery:** Update insert logic, re-run Step 4

---

#### 4.5 Transaction Rollback on Error
**Symptom:** `✗ Database update failed: ... ROLLBACK`
**Cause:** Single provision update failed, entire transaction rolled back
**Impact:** No provisions updated, must fix error and retry all
**Mitigation:**
- Use savepoints for each provision:
  ```python
  for provision in provisions:
      try:
          cur.execute("SAVEPOINT sp1")
          # update provision
          cur.execute("RELEASE SAVEPOINT sp1")
      except:
          cur.execute("ROLLBACK TO SAVEPOINT sp1")
          errors.append(...)
  ```
- Or commit in batches of 100 provisions
**Recovery:** Add error handling, re-run Step 4

---

#### 4.6 Import Confirmation Skipped
**Symptom:** User doesn't type "yes", import aborted
**Cause:** User typed "y" or "Yes" instead of exactly "yes"
**Impact:** Import not performed
**Mitigation:**
- Update confirmation check to accept multiple formats:
  ```python
  if response.lower() in ['yes', 'y']:
  ```
- Or remove confirmation for automated runs
**Recovery:** Re-run Step 4, type "yes" exactly

---

### STEP 5: Verification Failures

#### 5.1 Test Failures Due to Missing Provisions
**Symptom:** `✗ FAIL - Content Completeness (0/20 provisions passed)`
**Cause:** Import didn't complete, known provisions missing
**Impact:** Verification shows problems, but may be expected if import incomplete
**Mitigation:**
- Check import log to see if Step 4 completed
- Verify provisions exist:
  ```sql
  SELECT COUNT(*) FROM regulatory_provisions WHERE id IN (18945, 19101, 19195);
  ```
**Recovery:** Complete Step 4 successfully, then re-run Step 5

---

#### 5.2 Text Length Tests Fail
**Symptom:** `✗ FAIL - Text Length Distribution (1200 truncated provisions)`
**Cause:** Provisions still have truncated text from old extraction
**Impact:** Import didn't update all provisions
**Mitigation:**
- Check which provisions weren't updated:
  ```sql
  SELECT id, ref_number, full_text_length, extraction_method
  FROM regulatory_provisions
  WHERE document_id LIKE '%SEPP%' AND full_text_length <= 500;
  ```
- Manual update if needed:
  ```sql
  UPDATE regulatory_provisions SET extraction_method = NULL WHERE full_text_length <= 500;
  ```
- Re-run Step 4 to update remaining provisions
**Recovery:** Investigate why provisions weren't matched, re-run Step 4

---

#### 5.3 Content Completeness False Positives
**Symptom:** `✗ Content check failed: thermal not found`
**Cause:** Required keywords too specific, legitimate provisions fail check
**Impact:** False negative - provisions are actually complete
**Mitigation:**
- Review provision text manually:
  ```sql
  SELECT provision_text FROM regulatory_provisions WHERE id = 18945;
  ```
- Adjust required keywords if too strict:
  ```python
  # In 05_verify_completeness.py
  'must_contain': ['thermal', 'waste']  # Remove '$30 million' if not always present
  ```
**Recovery:** Adjust test criteria, re-run Step 5

---

### CROSS-CUTTING FAILURES

#### CC.1 Database Connection Pool Exhausted
**Symptom:** `FATAL: too many connections for database "nsw_planning"`
**Cause:** Script doesn't close connections properly
**Impact:** Later steps cannot connect to database
**Mitigation:**
- Always close connections in finally blocks
- Use connection pooling with limits
- Kill hanging connections:
  ```sql
  SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'nsw_planning' AND state = 'idle';
  ```
**Recovery:** Close connections, restart PostgreSQL if needed

---

#### CC.2 Filesystem Permission Errors
**Symptom:** `PermissionError: [Errno 13] Permission denied: 'docs/sepps/extracted'`
**Cause:** Script running as user without write permissions
**Impact:** Cannot write output files
**Mitigation:**
```bash
# Fix permissions
chmod 755 docs/sepps/
chmod 755 docs/sepps/extracted/

# Or run as correct user
sudo -u postgres python run_all.py
```
**Recovery:** Fix permissions, re-run failed step

---

#### CC.3 Python Dependencies Missing
**Symptom:** `ModuleNotFoundError: No module named 'psycopg2'`
**Cause:** Required Python packages not installed
**Impact:** Script cannot run
**Mitigation:**
```bash
# Install dependencies
pip install psycopg2-binary pathlib

# Or use requirements file
pip install -r requirements.txt
```
**Recovery:** Install dependencies, re-run

---

#### CC.4 Path Issues on Windows
**Symptom:** `FileNotFoundError: [WinError 3] The system cannot find the path specified: 'docs/sepps/extracted'`
**Cause:** Windows path separators or long paths
**Impact:** Script cannot find files
**Mitigation:**
- Use Path objects (already done in scripts)
- Or explicit Windows paths:
  ```python
  path = Path("C:\\Users\\lawre\\Downloads\\solvyra\\...\\docs\\sepps\\extracted")
  ```
- Enable long paths on Windows:
  ```
  HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\FileSystem
  Set LongPathsEnabled to 1
  ```
**Recovery:** Fix path handling, re-run

---

## Failure Recovery Matrix

| Step | Failure Type | Severity | Recovery Time | Data Loss Risk |
|------|-------------|----------|---------------|----------------|
| 1 | MinerU crash | High | 30 min (re-extract) | None (re-runnable) |
| 1 | Timeout | Medium | 5 min (increase timeout) | None |
| 2 | Parsing error | Medium | 10 min (fix patterns) | None |
| 3 | Schema update | HIGH | 30 min (restore backup) | **HIGH if no backup** |
| 3 | Permission denied | Low | 5 min (grant perms) | None |
| 4 | Import failure | Medium | 20 min (re-import) | None (transaction rolled back) |
| 4 | Partial import | Low | 10 min (re-run, idempotent) | None |
| 5 | Test failures | Low | 5 min (review/adjust) | None (read-only) |

---

## Prevention Checklist

Before starting pipeline:

- [ ] PostgreSQL running and accessible
- [ ] `magic-pdf` installed: `magic-pdf --version`
- [ ] All 8 SEPP PDFs present in `docs/sepps/`
- [ ] Disk space >3GB available
- [ ] Database user has ALTER TABLE permissions
- [ ] Python dependencies installed: `pip list | grep psycopg2`
- [ ] Test database connection: `python -c "from db_config import get_connection; get_connection()"`
- [ ] Backup exists: `ls backups/*.sql`

## Emergency Contacts / Resources

- **PostgreSQL Docs:** https://www.postgresql.org/docs/
- **MinerU Issues:** https://github.com/opendatalab/MinerU/issues
- **Database Backup Location:** `backups/schema_backup_*.sql`
- **Import Logs:** `docs/sepps/extracted/import_log.json`

## Post-Failure Debugging Commands

```bash
# Check extraction status
cat docs/sepps/extracted/extraction_metadata.json | python -m json.tool

# Check parsing status
cat docs/sepps/extracted/parsing_report.json | python -m json.tool

# Check import status
cat docs/sepps/extracted/import_log.json | python -m json.tool

# Check database provisions
psql -U postgres -d nsw_planning -c "SELECT extraction_method, COUNT(*), AVG(full_text_length) FROM regulatory_provisions WHERE document_id LIKE '%SEPP%' GROUP BY extraction_method"

# Check for errors in logs
grep -i "error\|fail" docs/sepps/extracted/*.json
```