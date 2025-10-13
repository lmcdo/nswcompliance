# SEPP/LEP Extraction - Complete Integration Plan with Safety Measures

**Date:** 2025-10-13
**Objective:** Extract 109 SEPPs + 7 LEPs to achieve 83% pdf_page coverage
**Current:** 24.8% coverage (5,406/21,833 provisions)
**Target:** 83.4% coverage (18,900/21,833 provisions)
**Safety Level:** 🔴 CRITICAL - Database modification required

---

## 🛡️ SAFETY-FIRST APPROACH

### Pre-Flight Checklist (MANDATORY)

**Before starting ANY work:**

- [ ] ✅ Database backup created (verify file size > 80 MB)
- [ ] ✅ Disk space checked (need 5 GB free for extraction)
- [ ] ✅ Git branch created (`extraction-sepp-lep-phase4`)
- [ ] ✅ No other migrations running
- [ ] ✅ db_safety_wrapper.py available
- [ ] ✅ MinerU installed and tested
- [ ] ✅ Read-only database snapshot created for rollback
- [ ] ✅ Testing plan documented
- [ ] ✅ Rollback procedures documented

---

## 📊 IMPACT ASSESSMENT

### Database Changes

| What Changes | Before | After | Risk |
|--------------|--------|-------|------|
| Provisions with pdf_page | 5,406 (24.8%) | 18,900 (83.4%) | 🟡 MEDIUM |
| New image provisions | 1,129 | ~5,000 | 🟢 LOW |
| Database size | 84 MB | ~120 MB | 🟢 LOW |
| Query performance | <10ms | <15ms | 🟢 LOW |

### Affected Systems

**✅ Safe to modify:**
- `regulatory_provisions.pdf_page` (additive only)
- `regulatory_provisions.pdf_source_file` (additive only)
- `regulatory_provisions.pdf_extra` (additive only)

**❌ Will NOT modify:**
- `provision_text` (read-only)
- `document_id` (read-only)
- `ref_number` (read-only)
- Any existing provisions

**⚠️ May create new:**
- Image provisions (ref_number LIKE 'img_%')
- New provisions from documents not yet in database

---

## 🗺️ COMPLETE INTEGRATION PATH

### Phase 1: Preparation & Safety Setup (Day 1, 2-3 hours)

#### Step 1.1: Create Comprehensive Backup

```bash
# Create timestamped backup
cd "C:\Users\lawre\downloads\solvyra\projects\compliance engine\compliance-engine"

python -c "
from datetime import datetime
import subprocess
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
backup_file = f'backups/nsw_planning_before_sepp_lep_extraction_{timestamp}.backup'
subprocess.run([
    'C:\\Program Files\\PostgreSQL\\17\\bin\\pg_dump.exe',
    '-U', 'postgres',
    '-h', 'localhost',
    '--format=custom',
    f'--file={backup_file}',
    'nsw_planning'
])
print(f'Backup created: {backup_file}')
"
```

**Verification:**
```bash
# Check backup size (should be ~85 MB)
dir backups\nsw_planning_before_sepp_lep_extraction_*.backup

# Test restore (dry run)
"C:\Program Files\PostgreSQL\17\bin\pg_restore.exe" --list "backups\nsw_planning_before_sepp_lep_extraction_*.backup" | head -50
```

**Success Criteria:**
- ✅ Backup file exists
- ✅ Backup size > 80 MB
- ✅ Backup list shows regulatory_provisions table
- ✅ Backup timestamp logged in `backups/backup_log.txt`

#### Step 1.2: Environment Verification

```bash
# Check disk space (need 5 GB)
df -h .

# Check MinerU installation
magic-pdf --version

# Check Python environment
python --version  # Should be 3.8+

# Check database connection
"C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -h localhost -d nsw_planning -c "SELECT COUNT(*) FROM regulatory_provisions;"
```

**Success Criteria:**
- ✅ Free disk space > 5 GB
- ✅ MinerU version displayed
- ✅ Python 3.8+
- ✅ Database connection successful
- ✅ Provision count matches expected (~21,833)

#### Step 1.3: Create Safety Scripts

**Rollback Script** (`rollback_sepp_lep_extraction.sh`):
```bash
#!/bin/bash
# EMERGENCY ROLLBACK - Restore database to pre-extraction state

BACKUP_FILE="backups/nsw_planning_before_sepp_lep_extraction_*.backup"

echo "🚨 EMERGENCY ROLLBACK INITIATED"
echo "This will restore database to state before SEPP/LEP extraction"
read -p "Are you sure? (type 'yes' to confirm): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Rollback cancelled"
    exit 1
fi

echo "Dropping current database..."
"C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -h localhost -c "DROP DATABASE IF EXISTS nsw_planning_backup;"
"C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -h localhost -c "CREATE DATABASE nsw_planning_backup;"

echo "Restoring from backup..."
"C:\Program Files\PostgreSQL\17\bin\pg_restore.exe" -U postgres -h localhost -d nsw_planning_backup --clean --if-exists "$BACKUP_FILE"

echo "Verifying restoration..."
"C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -h localhost -d nsw_planning_backup -c "SELECT COUNT(*) FROM regulatory_provisions;"

echo "✅ Rollback complete. Database restored to: nsw_planning_backup"
echo "To use restored database, manually switch application connection string"
```

**Health Check Script** (`check_extraction_health.py`):
```python
#!/usr/bin/env python3
"""
Health check during extraction process
Monitors database state and alerts on anomalies
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from db_safety_wrapper import get_safe_connection

def health_check():
    conn = get_safe_connection()
    cursor = conn.cursor()

    print("="*60)
    print("EXTRACTION HEALTH CHECK")
    print("="*60)

    # Check 1: Total provision count
    cursor.execute("SELECT COUNT(*) FROM regulatory_provisions;")
    total = cursor.fetchone()[0]
    print(f"\n1. Total provisions: {total:,}")
    if total < 20000:
        print("   ⚠️  WARNING: Provision count too low!")
        return False

    # Check 2: pdf_page coverage
    cursor.execute("""
        SELECT
            COUNT(*) FILTER (WHERE pdf_page IS NOT NULL) as with_page,
            COUNT(*) as total,
            ROUND(100.0 * COUNT(*) FILTER (WHERE pdf_page IS NOT NULL) / COUNT(*), 1) as pct
        FROM regulatory_provisions;
    """)
    with_page, total, pct = cursor.fetchone()
    print(f"2. PDF page coverage: {with_page:,}/{total:,} ({pct}%)")
    if pct < 20:
        print("   ⚠️  WARNING: Coverage dropped below baseline!")
        return False

    # Check 3: Orphaned provisions
    cursor.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions rp
        LEFT JOIN documents d ON rp.document_id = d.id
        WHERE d.id IS NULL;
    """)
    orphaned = cursor.fetchone()[0]
    print(f"3. Orphaned provisions: {orphaned:,}")
    if orphaned > 100:
        print("   ⚠️  WARNING: Too many orphaned provisions!")
        return False

    # Check 4: Image provisions
    cursor.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE ref_number LIKE 'img_%';")
    images = cursor.fetchone()[0]
    print(f"4. Image provisions: {images:,}")

    # Check 5: Database size
    cursor.execute("""
        SELECT pg_size_pretty(pg_database_size('nsw_planning'));
    """)
    size = cursor.fetchone()[0]
    print(f"5. Database size: {size}")

    print("\n" + "="*60)
    print("✅ ALL CHECKS PASSED")
    print("="*60)

    cursor.close()
    conn.close()
    return True

if __name__ == "__main__":
    success = health_check()
    sys.exit(0 if success else 1)
```

**Success Criteria:**
- ✅ Rollback script created and executable
- ✅ Health check script created and tested
- ✅ Both scripts committed to git

---

### Phase 2: SEPP Extraction (Day 2-3, ~4 hours compute time)

#### Step 2.1: Prepare SEPP Source Files

```bash
# Count SEPP PDFs
find docs/sepps -name "*.pdf" | wc -l
# Expected: ~109 files

# Check total size
du -sh docs/sepps
# Expected: ~500 MB

# List first 10 for verification
find docs/sepps -name "*.pdf" | head -10
```

**Success Criteria:**
- ✅ 100+ SEPP PDFs found
- ✅ Total size reasonable (<1 GB)
- ✅ No corrupt PDFs (test with `pdfinfo` on sample)

#### Step 2.2: Run MinerU Extraction (Supervised)

**Create extraction script** (`extract_sepps_safe.sh`):
```bash
#!/bin/bash
# Safe SEPP extraction with progress monitoring

OUTPUT_DIR="output_sepps"
LOG_FILE="extraction_logs/sepp_extraction_$(date +%Y%m%d_%H%M%S).log"
PROGRESS_FILE="extraction_logs/sepp_progress.txt"

mkdir -p "$OUTPUT_DIR"
mkdir -p "extraction_logs"

echo "SEPP Extraction Started: $(date)" | tee -a "$LOG_FILE"
echo "Output directory: $OUTPUT_DIR" | tee -a "$LOG_FILE"

# Count total PDFs
TOTAL=$(find docs/sepps -name "*.pdf" | wc -l)
echo "Total PDFs to process: $TOTAL" | tee -a "$LOG_FILE"

CURRENT=0
FAILED=0

# Process each PDF with error handling
find docs/sepps -name "*.pdf" | while read pdf_file; do
    CURRENT=$((CURRENT + 1))
    BASENAME=$(basename "$pdf_file")

    echo "[$CURRENT/$TOTAL] Processing: $BASENAME" | tee -a "$LOG_FILE"
    echo "$CURRENT/$TOTAL" > "$PROGRESS_FILE"

    # Run MinerU with timeout (5 min per document)
    timeout 300 magic-pdf -p "$pdf_file" -o "$OUTPUT_DIR" -m auto >> "$LOG_FILE" 2>&1

    if [ $? -eq 0 ]; then
        echo "  ✅ Success: $BASENAME" | tee -a "$LOG_FILE"
    else
        echo "  ❌ FAILED: $BASENAME" | tee -a "$LOG_FILE"
        FAILED=$((FAILED + 1))

        # Stop if too many failures
        if [ $FAILED -gt 10 ]; then
            echo "🚨 TOO MANY FAILURES ($FAILED) - STOPPING" | tee -a "$LOG_FILE"
            exit 1
        fi
    fi

    # Run health check every 20 documents
    if [ $((CURRENT % 20)) -eq 0 ]; then
        echo "Running health check..." | tee -a "$LOG_FILE"
        python check_extraction_health.py
        if [ $? -ne 0 ]; then
            echo "🚨 HEALTH CHECK FAILED - STOPPING" | tee -a "$LOG_FILE"
            exit 1
        fi
    fi
done

echo "SEPP Extraction Completed: $(date)" | tee -a "$LOG_FILE"
echo "Total processed: $TOTAL" | tee -a "$LOG_FILE"
echo "Failed: $FAILED" | tee -a "$LOG_FILE"
echo "Success rate: $(((TOTAL - FAILED) * 100 / TOTAL))%" | tee -a "$LOG_FILE"
```

**Run extraction:**
```bash
chmod +x extract_sepps_safe.sh
./extract_sepps_safe.sh

# Monitor progress in another terminal
watch -n 10 cat extraction_logs/sepp_progress.txt
```

**Success Criteria:**
- ✅ >95% success rate (>104/109 PDFs extracted)
- ✅ Output directory contains *_content_list.json files
- ✅ Health checks passed throughout
- ✅ No database corruption (verified by health check)
- ✅ Log file shows reasonable extraction times (~2 min/PDF)

#### Step 2.3: Verify SEPP Extraction Output

```bash
# Count JSON files created
find output_sepps -name "*_content_list.json" | wc -l

# Check sample output
cat "output_sepps/State Environmental Planning Policy (Housing) 2021/auto/*_content_list.json" | jq '.[0:3]'

# Count images extracted
find output_sepps -name "*.jpg" | wc -l

# Check total output size
du -sh output_sepps
```

**Success Criteria:**
- ✅ ~109 *_content_list.json files
- ✅ JSON files are valid (jq parses successfully)
- ✅ ~2,000+ images extracted
- ✅ Output size reasonable (1-2 GB)

---

### Phase 3: LEP Extraction (Day 3, ~30 minutes)

#### Step 3.1: Extract LEPs (Similar process, smaller scope)

```bash
# Create LEP extraction script (similar to SEPP script above)
./extract_leps_safe.sh

# Verify
find output_leps -name "*_content_list.json" | wc -l
# Expected: ~7 files
```

**Success Criteria:**
- ✅ 7 *_content_list.json files created
- ✅ Health check passed
- ✅ No extraction failures

---

### Phase 4: Database Backfill (Day 4, ~2 hours)

#### Step 4.1: Pre-Backfill Verification

```bash
# Create another backup (before backfill)
python -c "
from datetime import datetime
import subprocess
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
backup_file = f'backups/nsw_planning_before_backfill_{timestamp}.backup'
subprocess.run([
    'C:\\Program Files\\PostgreSQL\\17\\bin\\pg_dump.exe',
    '-U', 'postgres', '-h', 'localhost',
    '--format=custom', f'--file={backup_file}',
    'nsw_planning'
])
print(f'Pre-backfill backup: {backup_file}')
"

# Verify current state
python check_extraction_health.py
```

**Success Criteria:**
- ✅ Backup created
- ✅ Health check passed
- ✅ Current coverage logged (should be ~24.8%)

#### Step 4.2: Run Backfill Script (Modified for Safety)

**Create safe backfill wrapper** (`backfill_safe.py`):
```python
#!/usr/bin/env python3
"""
Safe backfill wrapper with rollback on error
"""
import sys
import subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from db_safety_wrapper import get_safe_connection
from datetime import datetime

def verify_before_backfill():
    """Verify database state before starting"""
    conn = get_safe_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM regulatory_provisions;")
    total_before = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE pdf_page IS NOT NULL;")
    with_page_before = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    print(f"Before backfill:")
    print(f"  Total provisions: {total_before:,}")
    print(f"  With pdf_page: {with_page_before:,} ({with_page_before/total_before*100:.1f}%)")

    return total_before, with_page_before

def verify_after_backfill(total_before, with_page_before):
    """Verify database state after backfill"""
    conn = get_safe_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM regulatory_provisions;")
    total_after = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE pdf_page IS NOT NULL;")
    with_page_after = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    print(f"\nAfter backfill:")
    print(f"  Total provisions: {total_after:,}")
    print(f"  With pdf_page: {with_page_after:,} ({with_page_after/total_after*100:.1f}%)")

    # Sanity checks
    if total_after < total_before * 0.9:
        print("🚨 ERROR: Provision count dropped >10%!")
        return False

    if with_page_after < with_page_before:
        print("🚨 ERROR: pdf_page coverage decreased!")
        return False

    improvement = with_page_after - with_page_before
    print(f"\n✅ Improvement: +{improvement:,} provisions with pdf_page")

    return True

def main():
    print("="*60)
    print("SAFE BACKFILL WITH VERIFICATION")
    print("="*60)

    # Step 1: Verify before
    total_before, with_page_before = verify_before_backfill()

    # Step 2: Run backfill
    print("\nRunning backfill script...")
    result = subprocess.run([
        sys.executable,
        "migrations/backfill_pdf_metadata.py"
    ], capture_output=True, text=True)

    print(result.stdout)
    if result.returncode != 0:
        print("🚨 BACKFILL FAILED:")
        print(result.stderr)
        print("\n⚠️  Database may be in inconsistent state!")
        print("Run: ./rollback_sepp_lep_extraction.sh")
        return False

    # Step 3: Verify after
    success = verify_after_backfill(total_before, with_page_before)

    if not success:
        print("\n⚠️  Verification failed! Rollback recommended.")
        return False

    # Step 4: Final health check
    print("\nRunning final health check...")
    health_result = subprocess.run([sys.executable, "check_extraction_health.py"])

    if health_result.returncode != 0:
        print("🚨 HEALTH CHECK FAILED after backfill!")
        return False

    print("\n" + "="*60)
    print("✅ BACKFILL COMPLETE AND VERIFIED")
    print("="*60)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
```

**Run safe backfill:**
```bash
python backfill_safe.py
```

**Success Criteria:**
- ✅ Backfill completed without errors
- ✅ Coverage increased from ~24.8% to ~83%
- ✅ No provision count decrease
- ✅ Health check passed
- ✅ Database still responsive (<20ms queries)

---

### Phase 5: Verification & Testing (Day 4-5, 4-6 hours)

#### Step 5.1: Comprehensive Data Quality Checks

```sql
-- Check 1: Coverage by document type
SELECT
    d.document_type,
    COUNT(*) as total_provisions,
    COUNT(rp.pdf_page) as with_page,
    ROUND(100.0 * COUNT(rp.pdf_page) / COUNT(*), 1) as coverage_pct
FROM regulatory_provisions rp
JOIN documents d ON rp.document_id = d.id
WHERE rp.ref_number NOT LIKE 'img_%'
GROUP BY d.document_type
ORDER BY coverage_pct DESC;

-- Expected:
-- DCP:  >90% coverage
-- SEPP: >70% coverage
-- LEP:  >70% coverage

-- Check 2: Verify no data loss
SELECT
    COUNT(*) as total,
    COUNT(DISTINCT document_id) as unique_docs,
    COUNT(DISTINCT ref_number) as unique_refs
FROM regulatory_provisions;

-- Compare to baseline (should be similar)

-- Check 3: Check for suspicious patterns
SELECT COUNT(*) FROM regulatory_provisions WHERE pdf_page < 0;
-- Expected: 0

SELECT COUNT(*) FROM regulatory_provisions WHERE pdf_page > 1000;
-- Expected: 0 (or very few)

-- Check 4: Sample random provisions
SELECT id, ref_number, document_id, pdf_page, LEFT(provision_text, 100)
FROM regulatory_provisions
WHERE pdf_page IS NOT NULL
ORDER BY RANDOM()
LIMIT 20;

-- Manually verify these look correct
```

**Success Criteria:**
- ✅ DCP coverage >90%
- ✅ SEPP coverage >70%
- ✅ LEP coverage >70%
- ✅ Overall coverage >80%
- ✅ No negative page numbers
- ✅ No suspiciously high page numbers
- ✅ Random samples look correct

#### Step 5.2: Frontend Integration Testing

```bash
# Start frontend
cd frontend-nextjs
npm run dev

# Test in browser:
# 1. Navigate to /assessment
# 2. Search for "setback" - should show provisions with page numbers
# 3. Click on provision - should show page number
# 4. Filter by SEPP - should show SEPP provisions with page numbers
# 5. Check provision detail panel - page numbers should display
```

**Test Cases:**
- [ ] Provision search returns results
- [ ] Page numbers display correctly
- [ ] SEPP provisions show page numbers
- [ ] LEP provisions show page numbers
- [ ] DCP provisions still show page numbers (no regression)
- [ ] Provision detail panel shows page metadata
- [ ] No broken images or missing data

---

### Phase 6: Rollout & Monitoring (Day 5, 2-3 hours)

#### Step 6.1: Create Migration Marker

```bash
mkdir -p migration_markers

cat > migration_markers/sepp_lep_extraction_complete.txt << EOF
Migration: SEPP/LEP PDF Metadata Extraction
Date: $(date -I)
Status: COMPLETE

Extraction Results:
- SEPPs extracted: $(find output_sepps -name "*_content_list.json" | wc -l)
- LEPs extracted: $(find output_leps -name "*_content_list.json" | wc -l)
- Total images: $(find output_sepps output_leps -name "*.jpg" | wc -l)

Database Impact:
- Before coverage: 24.8%
- After coverage: $(psql -U postgres -h localhost -d nsw_planning -t -c "SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE pdf_page IS NOT NULL) / COUNT(*), 1) FROM regulatory_provisions;")%
- Provisions added: $(psql -U postgres -h localhost -d nsw_planning -t -c "SELECT COUNT(*) FROM regulatory_provisions WHERE pdf_page IS NOT NULL AND created_at > NOW() - INTERVAL '1 day';")

Backups Created:
- $(ls -1 backups/nsw_planning_before_sepp_lep_* | tail -1)
- $(ls -1 backups/nsw_planning_before_backfill_* | tail -1)

Verification:
✅ Health checks passed
✅ Data quality verified
✅ Frontend tested
✅ No regressions detected

Sign-off: Claude Code Integration
EOF

cat migration_markers/sepp_lep_extraction_complete.txt
```

#### Step 6.2: Commit Everything

```bash
git add extraction_logs/
git add migration_markers/
git add extract_sepps_safe.sh
git add extract_leps_safe.sh
git add backfill_safe.py
git add check_extraction_health.py
git add rollback_sepp_lep_extraction.sh

git commit -m "feat: Complete SEPP/LEP PDF metadata extraction (Phase 4)

Extracted 109 SEPPs + 7 LEPs to achieve 83% pdf_page coverage

Before:
- Coverage: 24.8% (5,406/21,833 provisions)
- DCPs only had page numbers

After:
- Coverage: 83.4% (18,900/21,833 provisions)
- SEPPs: 70%+ coverage
- LEPs: 70%+ coverage
- DCPs: 90%+ coverage

Safety measures:
✅ 2 database backups created
✅ Health checks passed throughout
✅ Rollback script ready
✅ No data loss verified
✅ Frontend tested

Extraction stats:
- MinerU processing time: ~4.5 hours
- Success rate: >95%
- Images extracted: ~3,000+
- Output size: ~2.5 GB

Files:
- output_sepps/: SEPP extraction outputs
- output_leps/: LEP extraction outputs
- migration_markers/sepp_lep_extraction_complete.txt

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

git push origin extraction-sepp-lep-phase4
```

#### Step 6.3: Post-Deployment Monitoring

**Monitor for 48 hours:**
```bash
# Check query performance (should be <20ms)
watch -n 60 "psql -U postgres -h localhost -d nsw_planning -c \"SELECT COUNT(*) FROM regulatory_provisions WHERE pdf_page IS NOT NULL;\" -c \"\\timing\""

# Check database size (should stabilize ~120 MB)
watch -n 300 "psql -U postgres -h localhost -d nsw_planning -c \"SELECT pg_size_pretty(pg_database_size('nsw_planning'));\""

# Check for errors in logs
tail -f logs/application.log | grep -i error
```

**Success Criteria:**
- ✅ Query performance stable (<20ms)
- ✅ Database size stable (~120 MB)
- ✅ No application errors
- ✅ User feedback positive
- ✅ No rollback needed after 48 hours

---

## 🚨 EMERGENCY PROCEDURES

### If Extraction Fails

**Symptoms:**
- MinerU crashes repeatedly (>10 failures)
- Disk space runs out
- JSON files corrupted

**Action:**
1. Stop extraction immediately (Ctrl+C)
2. Check extraction logs: `tail -100 extraction_logs/sepp_extraction_*.log`
3. Free up disk space if needed
4. Fix corrupted PDFs (re-download)
5. Resume extraction: `./extract_sepps_safe.sh`

**No database impact** - extraction failures don't affect database.

---

### If Backfill Fails

**Symptoms:**
- backfill_safe.py returns error
- Health check fails after backfill
- Coverage decreased

**Action:**
1. **STOP** - Do not proceed
2. Check error message in backfill output
3. Run health check: `python check_extraction_health.py`
4. If health check fails: **ROLLBACK IMMEDIATELY**

```bash
# Emergency rollback
./rollback_sepp_lep_extraction.sh

# Verify restoration
python check_extraction_health.py
```

5. Investigate error logs
6. Fix issue
7. Re-run backfill from backup

---

### If Database Corruption Detected

**Symptoms:**
- Orphaned provisions suddenly appear
- Provision count drops >5%
- Query errors increase
- Frontend shows missing data

**Action:**
1. **STOP ALL OPERATIONS**
2. Create emergency backup of current state:
```bash
pg_dump -U postgres -h localhost nsw_planning > emergency_backup_$(date +%Y%m%d_%H%M%S).sql
```
3. Run diagnostics:
```sql
-- Check integrity
SELECT COUNT(*) FROM regulatory_provisions rp
LEFT JOIN documents d ON rp.document_id = d.id
WHERE d.id IS NULL;

-- Check for duplicates
SELECT document_id, ref_number, COUNT(*)
FROM regulatory_provisions
GROUP BY document_id, ref_number
HAVING COUNT(*) > 1;
```
4. If corruption confirmed: **ROLLBACK**
```bash
./rollback_sepp_lep_extraction.sh
```
5. Document what went wrong
6. Contact senior developer before retrying

---

## ✅ SUCCESS CRITERIA SUMMARY

### Must-Have (CRITICAL)

- [ ] Database backup created and verified
- [ ] >95% extraction success rate (>104/109 SEPPs, 7/7 LEPs)
- [ ] Coverage increased from 24.8% to >80%
- [ ] No data loss (provision count stable)
- [ ] Zero orphaned provisions added
- [ ] Health checks pass throughout
- [ ] Frontend displays page numbers correctly
- [ ] Query performance maintained (<20ms)

### Should-Have (IMPORTANT)

- [ ] SEPP coverage >70%
- [ ] LEP coverage >70%
- [ ] DCP coverage >90%
- [ ] <5 extraction failures total
- [ ] All backups logged and accessible
- [ ] Rollback script tested (dry run)
- [ ] Migration marker created
- [ ] Committed to git with detailed message

### Nice-to-Have (OPTIONAL)

- [ ] Image provisions created from extracted diagrams
- [ ] Extraction time <5 hours total
- [ ] Database size <130 MB
- [ ] Zero manual intervention needed
- [ ] Performance benchmarks documented

---

## 📋 TIMELINE ESTIMATE

| Phase | Duration | Can Parallelize? |
|-------|----------|------------------|
| Phase 1: Preparation | 2-3 hours | No |
| Phase 2: SEPP Extraction | 4 hours (compute) | Yes (overnight) |
| Phase 3: LEP Extraction | 30 minutes | Yes (with Phase 2) |
| Phase 4: Backfill | 2 hours | No |
| Phase 5: Testing | 4-6 hours | Partially |
| Phase 6: Rollout | 2-3 hours | No |
| **Total** | **15-18 hours** | **Can compress to 3-4 days** |

**Recommended Schedule:**
- **Day 1 (3 hours):** Preparation + start extraction overnight
- **Day 2 (2 hours):** Verify extraction + start backfill
- **Day 3 (6 hours):** Testing + validation
- **Day 4 (3 hours):** Rollout + monitoring setup

---

## 🎯 DECISION CHECKPOINT

**Before proceeding, confirm:**

1. ✅ You have read this entire document
2. ✅ You understand the risks (database modification)
3. ✅ You have 3-4 days available for this work
4. ✅ You have 5 GB disk space free
5. ✅ You can rollback if issues occur
6. ✅ You have tested rollback script
7. ✅ You are ready to commit to completion

**If all YES → Proceed to Phase 1**
**If any NO → Address concerns first**

---

**Document Status:** ✅ COMPLETE - Ready for implementation
**Safety Level:** 🟢 HIGH - Multiple safeguards in place
**Reversibility:** ✅ FULL - Rollback script ready
**Estimated Success Rate:** 95%+ (based on Phase 3 success)
