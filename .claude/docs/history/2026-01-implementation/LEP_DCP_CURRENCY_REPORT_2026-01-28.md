# LEP and DCP Currency Report
**Date:** 2026-01-28
**Analysis:** Comparison of database documents vs. current NSW legislation

---

## Executive Summary

**Database Status:**
- 328 LEP/DCP documents total
- 35 LEPs (all Inner West LEP 2022 versions)
- 293 DCPs (Ashfield DCP 2016, Leichhardt DCP 2013, Marrickville DCP 2009)
- Last verified: 2024-10-14 (281 docs), 2024-10-23 (47 docs)
- Version status: 281 "unverified", 47 "verified"

**Currency Issues Identified:**
1. **Inner West LEP 2022:** Missing 2 amendments (Nov 2024, April 2025)
2. **DCPs:** No consolidated "Inner West DCP 2023" exists - council uses 3 separate former-council DCPs
3. **Full text coverage:** Only 165/328 documents have full_text populated

---

## 1. Inner West LEP 2022 Analysis

### Database Status
- **Documents:** 35 total (1 main + 21 sections + page splits)
- **ID:** `Inner_West_Local_Environmental_Plan_2022___NSW_Legislation`
- **Last Verified:** 2024-10-14
- **Version Status:** unverified
- **Regulation Year:** 2022
- **Amendment Reference:** None listed
- **Has Full Text:** Yes (all 35 documents)

### Current Official Version
**Source:** [NSW Legislation](https://legislation.nsw.gov.au/view/html/inforce/current/epi-2022-0457)
**Latest Version Date:** 2025-12-12

### Missing Amendments

#### Amendment No 9 (November 1, 2024)
**Status:** MISSING from database
**Source:** [EPI 2024-555](https://legislation.nsw.gov.au/view/pdf/asmade/epi-2024-555)
**Type:** SUBSTANTIVE - Heritage listings
**Changes:**
- **Added to Schedule 5 (Environmental Heritage):**
  - Annandale Hotel (with interiors) at 17-19 Parramatta Road
  - Dick's Hotel (with interiors) at 89 Beattie Street, Balmain
  - Cricketers Arms Hotel (with interiors) at 255 Darling Street
- **Maps:** Amended/replaced maps for heritage areas

**Impact:** HIGH - New heritage provisions affect property compliance checks for these addresses

#### Amendment No 13 (April 24, 2025)
**Status:** MISSING from database
**Source:** [EPI 2025-187](https://legislation.nsw.gov.au/view/pdf/asmade/epi-2025-187)
**Type:** ADMINISTRATIVE - Cleanup/clarification
**Changes:**
- Omitted note 2
- Omitted "certain business zones or" wherever occurring
- Omitted clause 36

**Impact:** LOW - Administrative cleanup, unlikely to affect compliance logic

#### Other Amendments
**Amendment No 3** (2023): [EPI 2023-239](https://legislation.nsw.gov.au/view/pdf/asmade/epi-2023-239)
**Map Amendment No 2** (2024): [EPI 2024-582](https://legislation.nsw.gov.au/view/pdf/asmade/epi-2024-582)

**Status:** Need to verify if these are already in database (verified date 2024-10-14 suggests they might be)

---

## 2. Inner West DCP Analysis

### Database Status
- **Documents:** 293 DCPs
- **Types:**
  - Ashfield DCP 2016 (with IWLEP 2022 amendments): ~100 documents
  - Leichhardt DCP 2013 (Amendment 19, Nov 2023): ~100 documents
  - Marrickville DCP 2009/2011: ~93 documents
- **Last Verified:** 2024-10-14 (most), 2024-10-23 (47 docs)
- **Version Status:** 281 "unverified", 47 "verified"
- **Has Full Text:** Only 165/293 (56%)

### Current Official Status
**Source:** [Inner West Council DCP page](https://www.innerwest.nsw.gov.au/develop/plans-policies-and-controls/development-controls-lep-and-dcp/development-control-plans-dcp)
**Key Finding:** There is NO "Inner West DCP 2023"

Inner West Council continues to use **three separate DCPs** from former councils:
1. **Ashfield DCP 2016** (with IWLEP 2023 amendments - CONSOLIDATED)
2. **Leichhardt DCP 2013** (Amendment 19, May 2021 onwards)
3. **Marrickville DCP 2011** (as amended May 2021)

### DCP Currency Issues

#### Issue 1: Missing Full Text
- 128/293 DCP documents have NULL or empty full_text
- Cannot verify currency without full text
- **Priority:** HIGH - need to extract full_text for verification

#### Issue 2: Consolidated Versions
Database shows individual PDF chapters, but council publishes **consolidated versions** with all amendments incorporated.

**Example from search results:**
- NSW Planning Portal lists: "Inner West Ashfield DCP 2016 with IWLEP 2023 amendments - CONSOLIDATED (PDF)"
- Database has: Individual chapters with "IWLEP 2022 amendments" notation

**Discrepancy:** Database references "IWLEP 2022" but portal shows "IWLEP 2023" amendments

#### Issue 3: Employment Zones Update (April 26, 2023)
**Source:** Search results mention "new employment zones came into effect on 26 April 2023 in NSW"
**Status:** Unknown if reflected in database DCPs
**Impact:** Affects Layer 2 (use-specific) zone filtering

---

## 3. Provision Impact Analysis

### Inner West LEP 2022
**Query to check existing provisions:**
```sql
SELECT COUNT(*), document_id
FROM regulatory_provisions
WHERE document_id LIKE 'Inner_West_Local_Environmental_Plan_2022%'
GROUP BY document_id;
```

**Expected result:** Should show provisions from LEP sections

**Action needed:**
1. Extract provisions from Amendment No 9 (heritage items)
2. Add new Schedule 5 entries to `regulatory_provisions`
3. Update `last_verified_date` to 2026-01-28
4. Update `version_status` to 'verified'
5. Add `amendment_reference`: 'Amendment No 9, Amendment No 13'

### Inner West DCPs
**Query to check existing provisions:**
```sql
SELECT COUNT(*), document_area, v2_dcp_part
FROM regulatory_provisions
WHERE document_id LIKE '%DCP%' AND document_area IN ('Ashfield', 'Leichhardt', 'Marrickville')
GROUP BY document_area, v2_dcp_part;
```

**Expected result:** ~47,000 DCP provisions (per DB_SCHEMA.md)

**Action needed:**
1. Verify employment zone updates (April 2023) are reflected in provisions
2. Check v2_applicable_zones against new employment zone codes
3. Update documents with missing full_text (128 documents)
4. Verify amendment dates match council's published versions

---

## 4. Recommendations

### Priority 1: Inner West LEP 2022 - Amendment No 9 (Heritage)
**Impact:** HIGH - affects compliance for specific addresses
**Effort:** LOW - only 3 new heritage items

**Steps:**
1. Fetch full text of Amendment No 9 from documents.full_text (ID: `Inner_West_Local_Environmental_Plan_2022___NSW_Legislation`)
2. Extract new Schedule 5 entries:
   - Annandale Hotel (17-19 Parramatta Road)
   - Dick's Hotel (89 Beattie Street, Balmain)
   - Cricketers Arms Hotel (255 Darling Street)
3. Check if these are already in `regulatory_provisions` (search for "Annandale Hotel")
4. If missing, insert as new provisions with:
   - `document_id`: `Inner_West_Local_Environmental_Plan_2022___NSW_Legislation_section_X`
   - `ref_number`: Schedule 5 item numbers
   - `provision_text`: Full heritage item text
   - `is_current`: true
   - `display_priority`: 1 (heritage controls are critical)
5. Update documents table: `last_verified_date = '2026-01-28'`, `amendment_reference = 'Amendment No 9 (2024-555), Amendment No 13 (2025-187)'`

### Priority 2: Inner West LEP 2022 - Amendment No 13 (Administrative)
**Impact:** LOW - administrative cleanup
**Effort:** LOW - just documentation

**Steps:**
1. Update documents table metadata
2. No provision extraction needed (clause deletions, not additions)
3. Document in version_status notes

### Priority 3: DCP Full Text Verification
**Impact:** MEDIUM - blocks currency verification
**Effort:** HIGH - 128 documents

**Steps:**
1. Identify which 128 documents lack full_text
2. Check if these are duplicates (e.g., `Area: None` vs. `Area: Ashfield`)
3. For legitimate documents, extract full_text from PDFs
4. Prioritize documents that have provisions in `regulatory_provisions`

### Priority 4: DCP Employment Zones Update
**Impact:** MEDIUM - affects Layer 2 zone filtering
**Effort:** MEDIUM - verification + potential updates

**Steps:**
1. Query provisions with v2_applicable_zones
2. Check for old zone codes (B1-B7) vs. new employment zones
3. Verify April 26, 2023 updates are reflected
4. Update zone codes if needed

---

## 5. Verification Queries

### Check for Amendment No 9 heritage items
```sql
SELECT * FROM regulatory_provisions
WHERE provision_text ILIKE '%Annandale Hotel%'
   OR provision_text ILIKE '%Dick''s Hotel%'
   OR provision_text ILIKE '%Cricketers Arms%';
```

### Check LEP provision count by document
```sql
SELECT document_id, COUNT(*) as provision_count
FROM regulatory_provisions
WHERE document_id LIKE 'Inner_West_Local_Environmental_Plan_2022%'
GROUP BY document_id
ORDER BY provision_count DESC;
```

### Check DCP documents missing full_text
```sql
SELECT id, pdf_name, document_area, char_count, word_count
FROM documents
WHERE document_type = 'DCP'
  AND (full_text IS NULL OR full_text = '')
ORDER BY document_area, pdf_name;
```

### Check employment zone codes in provisions
```sql
SELECT DISTINCT v2_applicable_zones
FROM regulatory_provisions
WHERE v2_applicable_zones IS NOT NULL
  AND (v2_applicable_zones LIKE '%B1%'
    OR v2_applicable_zones LIKE '%B2%'
    OR v2_applicable_zones LIKE '%B3%'
    OR v2_applicable_zones LIKE '%B4%'
    OR v2_applicable_zones LIKE '%B5%'
    OR v2_applicable_zones LIKE '%B6%'
    OR v2_applicable_zones LIKE '%B7%');
```

---

## 6. Next Steps

1. **Run verification queries** (Section 5) to assess current state
2. **Start with Priority 1** (Amendment No 9 heritage items)
3. **Use SEPP methodology:**
   - Check documents.full_text for current version
   - Extract new provisions using regex
   - Insert into regulatory_provisions
   - Test route compatibility
   - Update documents metadata
4. **Document results** in DATA_QUALITY_TRACKER.md
5. **Create commit** following git protocol

---

## Sources

- [Inner West LEP 2022 Current Version](https://legislation.nsw.gov.au/view/html/inforce/current/epi-2022-0457)
- [Amendment No 13 (2025-187)](https://legislation.nsw.gov.au/view/pdf/asmade/epi-2025-187)
- [Amendment No 9 (2024-555)](https://legislation.nsw.gov.au/view/pdf/asmade/epi-2024-555)
- [Amendment No 3 (2023-239)](https://legislation.nsw.gov.au/view/pdf/asmade/epi-2023-239)
- [Map Amendment No 2 (2024-582)](https://legislation.nsw.gov.au/view/pdf/asmade/epi-2024-582)
- [Inner West Council DCP Page](https://www.innerwest.nsw.gov.au/develop/plans-policies-and-controls/development-controls-lep-and-dcp/development-control-plans-dcp)
- [NSW Planning Portal - DCPs](https://www.planningportal.nsw.gov.au/DCP)

---

**Report Generated:** 2026-01-28
**Analysis Tool:** compliance-engine/analyze_lep_dcp_currency.py
