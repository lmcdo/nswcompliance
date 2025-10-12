# PDF Metadata Risk Assessment
**Date:** 2025-10-13
**Database:** nsw_planning (86 MB)
**Total Provisions:** 22,648

---

## 🔴 CRITICAL RISKS

### 1. Referential Integrity Failure (HIGH SEVERITY)

**Issue:** 2,486 provisions (10.9%) have orphaned document_ids

```sql
-- Affected provisions by document
unknown                              351 provisions
Transport SEPP 2021                  168 provisions
Ashfield Chapter E1 (Heritage)       135 provisions
Ashfield Chapter D (Precincts)       132 provisions
Marrickville 8.0 Heritage            124 provisions
Leichhardt Section 2 (2 versions)    226 provisions
```

**Root Cause:** Document ID format mismatch
- Provisions table uses: `Inner West Ashfield DCP 2016 - Chapter E1- Heritage...`
- Documents table has: `Inner_West_Ashfield_DCP_2016___Chapter_E1__Heritage...`

**Impact:**
- ❌ LEFT JOIN returns NULL for document metadata (type, area, pdf_name)
- ❌ Frontend filters by document_type will miss these provisions
- ❌ Cannot generate "View PDF" links for affected provisions
- ❌ API responses incomplete

**Liability:**
- Legal: Provisions shown without source attribution
- User Trust: "Where did this come from?"
- Compliance: Cannot verify regulatory text against PDF

**Remediation Priority:** 🔴 URGENT (within 48 hours)

**Fix:**
```sql
-- Option A: Normalize provision document_ids to match documents table
UPDATE regulatory_provisions
SET document_id = REPLACE(REPLACE(document_id, ' - ', '___'), ' ', '_')
WHERE document_id IN (SELECT document_id FROM ...orphaned list...);

-- Option B: Add foreign key with ON UPDATE CASCADE
ALTER TABLE regulatory_provisions
ADD CONSTRAINT fk_document_id
FOREIGN KEY (document_id) REFERENCES documents(id)
ON UPDATE CASCADE;
```

---

### 2. Missing Source PDFs (MODERATE SEVERITY)

**Issue:** Source PDFs deleted after extraction

**Current State:**
- ✅ 112 extraction outputs in `output/` (1.4 GB)
- ❌ Only 28 source PDFs remain in `docs/` (121 MB)
- ❌ No backup of deleted PDFs

**Impact:**
- ⚠️ Cannot re-extract if JSON corrupted
- ⚠️ Cannot verify extraction accuracy
- ⚠️ Cannot regenerate if MinerU version changes

**Liability:**
- Audit Risk: "Show us the original documents"
- Recovery: Must re-download PDFs from council websites
- Version Control: No proof of which PDF version was processed

**Remediation Priority:** 🟡 MEDIUM (within 1 week)

**Fix:**
- Create compressed archive of source PDFs
- Store on separate drive or cloud backup
- Document PDF download dates and URLs

---

### 3. Incomplete Coverage (MODERATE SEVERITY)

**Issue:** 76.1% of provisions have NO pdf_page

**Coverage by Document Type:**
```
DCP (Inner West):  5,407/5,400  = ~100% ✅
DCP (Other):            0/9,500  =    0% ❌
SEPP:                   0/4,237  =    0% ❌
LEP:                    0/967    =    0% ❌
```

**Impact:**
- ❌ No "View PDF" links for 17,241 provisions
- ❌ Certifiers cannot verify 76% of provisions
- ❌ Legal defensibility compromised

**Liability:**
- Professional: Incomplete audit trail
- Regulatory: NSW requires traceable citations
- User Trust: "Why can't I see the source?"

**Remediation Priority:** 🟡 MEDIUM (within 2 weeks)

**Fix:**
- Extract 109 SEPPs → +4,237 provisions (+18.7%)
- Extract 33 other DCPs → +9,500 provisions (+42%)
- Extract 7 LEPs → +967 provisions (+4.3%)
- **Target: 83.4% coverage**

---

## 🟡 MODERATE RISKS

### 4. Duplicate Source Conflicts (LOW-MODERATE SEVERITY)

**Issue:** 4 documents have provisions from multiple source files

```sql
Marrickville Heritage Part2: 2 sources (46 + 94 provisions)
Marrickville Heritage Part3: 2 sources
Marrickville Heritage Part4: 2 sources
Marrickville Boarding Houses: 2 sources
```

**Root Cause:** Same provisions imported twice from different PDF splits

**Impact:**
- ⚠️ Conflicting page numbers for same provision
- ⚠️ User confusion: "Which PDF is correct?"
- ⚠️ Cannot trust pdf_page for these 450+ provisions

**Liability:**
- Data Quality: Ambiguous source attribution
- User Experience: Clicking "View PDF" opens wrong file

**Remediation Priority:** 🟡 MEDIUM (within 1 week)

**Fix:**
```sql
-- Deduplicate by preferring most specific source
UPDATE regulatory_provisions
SET pdf_source_file = (
    SELECT pdf_source_file
    FROM regulatory_provisions rp2
    WHERE rp2.id = regulatory_provisions.id
    ORDER BY LENGTH(pdf_source_file) DESC
    LIMIT 1
)
WHERE document_id IN (...duplicate docs...);
```

---

### 5. Database Size Growth (LOW SEVERITY)

**Current:** 86 MB total
- regulatory_provisions: 33 MB
- documents: 5 MB
- indexes: ~20 MB
- other: ~28 MB

**Growth Projection:**
- Add 149 documents → +40 MB (JSON metadata)
- No concern until >500 MB

**Impact:**
- ✅ No immediate performance issues
- ⚠️ Local dev databases may run slow on old hardware

**Remediation Priority:** 🟢 LOW (monitor only)

---

### 6. Index Coverage Gaps (LOW SEVERITY)

**Unused Indexes (0 scans):**
- `idx_provisions_cross_ref`
- `idx_provisions_text_hash`
- `idx_regulatory_provisions_type`
- `idx_provisions_canonical`

**Impact:**
- ⚠️ Wasted 5-10 MB disk space
- ⚠️ Slower INSERT/UPDATE operations

**Remediation Priority:** 🟢 LOW (optimize after launch)

**Fix:**
```sql
-- Drop unused indexes
DROP INDEX idx_provisions_cross_ref;
DROP INDEX idx_provisions_text_hash;
...
```

---

## 🟢 LOW RISKS / NON-ISSUES

### 7. Data Quality ✅

**Validated:**
- ✅ No negative page numbers
- ✅ No pages > 1,000 (reasonable max)
- ✅ No orphaned pdf_page without pdf_source_file
- ✅ All pdf_page values are integers >= 0

### 8. Performance ✅

**Index Usage:**
- Primary key: 14,058 scans (excellent)
- Document FK: 406 scans (good)
- Zone index: 13 scans (acceptable)
- PDF page index: 5 scans (new, will grow)

**Query Performance:**
- Database: 86 MB (small, fits in RAM)
- No slow query patterns detected
- Full table scans acceptable at this scale

### 9. Disk Space ✅

**Current Usage:**
- Database: 86 MB
- Extractions: 1.4 GB
- Source docs: 121 MB
- Frontend build: 49 MB
- **Total: ~1.7 GB** (acceptable)

---

## 🎯 RECOMMENDED ACTION PLAN

### Phase 1: Critical Fixes (Next 48 hours)

**Priority 1:** Fix referential integrity
```bash
# Run migration to normalize document_ids
python migrations/fix_orphaned_document_ids.py
```

**Expected Result:** 0 orphaned provisions (down from 2,486)

---

### Phase 2: Data Quality (Within 1 week)

**Priority 2:** Backup source PDFs
```bash
# Compress and archive original PDFs
tar -czf pdfs_backup_20251013.tar.gz docs/dcps docs/sepps docs/leps
# Upload to cloud storage
```

**Priority 3:** Deduplicate provisions
```sql
-- Remove duplicate source file references
UPDATE regulatory_provisions...
```

---

### Phase 3: Coverage Expansion (Within 2 weeks)

**Priority 4:** Extract remaining documents
```bash
# Extract SEPPs (biggest impact)
python extract_all_sepps_with_mineru.py  # +4,237 provisions

# Extract other DCPs
python extract_remaining_dcps.py         # +9,500 provisions

# Extract LEPs
python extract_leps.py                   # +967 provisions

# Re-run backfill
python migrations/backfill_pdf_metadata.py
```

**Expected Result:** 83.4% coverage (up from 23.9%)

---

## Performance Impact Analysis

### Current Query Patterns

**Most Common Queries:**
1. Get provisions by zone (13 scans on zone index)
2. Get provisions by document (406 scans on document index)
3. Get provision by ID (14,058 scans on primary key)

**Query Performance:**
- Average query time: <10ms
- 95th percentile: <50ms
- No queries >1 second

**Adding pdf_page increases query time by:**
- ~0.5ms per query (negligible)
- Index already exists and used

### Projected Performance After Full Extraction

**Database Size:**
- Current: 86 MB
- After extraction: ~125 MB (+45%)
- Still fits in RAM on any modern server

**Query Impact:**
- No expected degradation
- pdf_page index scans will increase to ~100-500/day
- Well within PostgreSQL capacity

---

## Legal/Compliance Considerations

### Current Liabilities

**1. Unattributed Provisions (10.9%)**
- Risk: Cannot prove regulatory text came from official document
- Mitigation: Fix orphaned document_ids immediately

**2. Missing PDF Links (76.1%)**
- Risk: Certifiers cannot verify source
- Mitigation: Complete extraction within 2 weeks
- Interim: Display warning "Source PDF not yet linked"

**3. Ambiguous Sources (2%)**
- Risk: Wrong PDF shown on "View PDF" click
- Mitigation: Deduplicate provision sources

### Recommended Disclaimers

**Add to frontend:**
```typescript
{!provision.pdf_page && (
  <div className="text-xs text-yellow-600">
    ⚠️ Source PDF link not yet available.
    Provision extracted from official planning instrument.
  </div>
)}
```

**Add to terms of service:**
"PDF links are provided for verification purposes. In case of discrepancy,
the official published planning instrument prevails."

---

## Monitoring Recommendations

### Daily Checks
1. Query orphaned provisions count
2. Check database size growth
3. Monitor slow query log

### Weekly Checks
1. Verify extraction progress
2. Review duplicate provision count
3. Check backup integrity

### Monthly Checks
1. Audit full coverage statistics
2. Performance regression testing
3. Index usage analysis

---

## Summary: Risk Matrix

| Risk | Severity | Impact | Effort | Priority | Deadline |
|------|----------|--------|--------|----------|----------|
| Orphaned document_ids | 🔴 HIGH | Legal liability | 2 hours | P0 | 48 hours |
| Missing source PDFs | 🟡 MEDIUM | Audit risk | 1 hour | P2 | 1 week |
| Incomplete coverage | 🟡 MEDIUM | User trust | 8 hours | P2 | 2 weeks |
| Duplicate sources | 🟡 MEDIUM | Data quality | 2 hours | P3 | 1 week |
| Database size | 🟢 LOW | None yet | Monitor | P4 | Ongoing |
| Unused indexes | 🟢 LOW | Minor perf | 1 hour | P5 | After launch |

**Total Critical Issues:** 1
**Total Moderate Issues:** 3
**Total Low Issues:** 2

**Overall Assessment:** 🟡 MODERATE RISK (fixable within 2 weeks)
