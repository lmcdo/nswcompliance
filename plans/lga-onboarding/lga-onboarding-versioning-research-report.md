# LGA Onboarding Automation: Versioning Infrastructure & Update Sources Research

**Research Date:** 2026-02-10
**Status:** Complete

---

## Section 1: Current Versioning State

### 1.1 Database Schema Status

**Document-Level Versioning (versions.document_versions)**
- ✅ **EXISTS** and is **POPULATED**
- Schema: `versions` (separate from public schema)
- Row count: **110 documents** (74 DCP, 29 LEP, 7 SEPP)
- All documents marked as `CURRENT` status
- Version number: `v1.0-baseline` (established 2024-09-20)
- No superseded documents yet (all `superseded_date` is NULL)

**Provision-Level Versioning (provision_versions)**
- ❌ **DOES NOT EXIST**
- Migration script exists at: `scripts/migrations/create_version_schema.sql`
- Schema defined but **NOT APPLIED** to production database
- References this table exist in:
  - `services/version_tracking.py` (boilerplate)
  - `frontend-nextjs/app/api/provisions/changes/route.ts` (API endpoint exists but would fail)

**Change Tracking (provision_change_log)**
- ❌ **DOES NOT EXIST**
- Schema defined in migration script but not applied

### 1.2 regulatory_provisions Table Status

**Version-Related Columns:**
- ❌ `version_id` - **DOES NOT EXIST**
- ❌ `current_version_id` - **DOES NOT EXIST**
- ❌ `first_seen_date` - **DOES NOT EXIST**
- ❌ `last_modified_date` - **DOES NOT EXIST**
- ❌ `version_count` - **DOES NOT EXIST**
- ❌ `is_current` - **DOES NOT EXIST**
- ❌ `text_hash_current` - **DOES NOT EXIST**

**Current State:**
- Total provisions: 46,585 (per DB_SCHEMA.md)
- No provision-level versioning metadata
- No linkage to versions.document_versions

### 1.3 Code Usage Analysis

**Python Services (Boilerplate, Not Active)**
- `services/version_manager.py` - Document-level version manager (works with versions.document_versions)
- `services/version_aware_query.py` - Query wrapper for historical provisions (expects provision_versions table)
- `sepp_full_text_extraction/version_tracking.py` - Provision versioning utilities (expects provision_versions table)

**Frontend API Routes (Mixed Status)**
- ✅ `/api/versions/route.ts` - EXISTS, calls version_manager.py via subprocess
  - Has PostgreSQL migration path started (VersionClient)
  - Currently uses Python subprocess as fallback
  - Feature flag controlled: `shouldUsePostgreSQL('versions', requestId)`
- ⚠️ `/api/provisions/changes/route.ts` - EXISTS but **WOULD FAIL**
  - Queries provision_change_log and provision_versions tables (don't exist)
  - Not currently used in production
- ✅ `/api/provisions/for-property/route.ts` - EXISTS and WORKING
  - Supports `version_date` parameter for historical queries
  - Expects `is_current` column in regulatory_provisions (doesn't exist yet)
  - Has provision_versions JOIN logic (lines 689-713) but NOT ACTIVE

**Migration Status:**
- Migration scripts exist but NOT RUN:
  - `migrations/add_version_tracking.sql` - Document-level metadata (likely already applied)
  - `scripts/migrations/create_version_schema.sql` - Provision-level versioning (NOT applied)
  - `scripts/migrations/optimize_version_performance.sql` - Indexes (NOT applied)

### 1.4 Summary: Is Versioning Active or Dormant?

**Status: PARTIALLY DORMANT**

**Active Components:**
- ✅ Document-level versioning (versions.document_versions) is LIVE with 110 documents
- ✅ API endpoint `/api/versions` is operational for document-level queries
- ✅ Version manager service works for document metadata

**Dormant Components:**
- ❌ Provision-level versioning is COMPLETELY DORMANT (tables don't exist)
- ❌ Historical "as-of-date" queries for provisions would FAIL (no provision_versions table)
- ❌ Change tracking is NOT ACTIVE (no provision_change_log)
- ❌ Most version-aware query code is boilerplate/unused

**Verdict:**
The versioning infrastructure is a **scaffolded prototype** - document-level tracking exists as a baseline, but provision-level versioning (the critical component for LGA onboarding automation) has **NOT been deployed to production**.

---

## Section 2: Regulatory Update Sources

### 2.1 Official Government Sources

#### NSW Legislation Website (legislation.nsw.gov.au)
**Authority Level:** ⭐⭐⭐⭐⭐ PRIMARY SOURCE
**Document Types:** SEPP, LEP
**Update Mechanism:**
- ✅ RSS/Atom feeds available
- ✅ Archive from 2008-2026
- ✅ Updates loaded within 3 business days of commencement
- ✅ Interactive tables showing status of EPIs (Environmental Planning Instruments)

**Access Method:**
- RSS feeds: Available on homepage under "Legislation feeds (Atom)"
- Browse: State Environmental Planning Policies under "EPIs" section
- Browse: Local Environmental Plans under "EPIs" section (alphabetical)

**Update Frequency:** Within 3 business days of legislative commencement

**Sources:**
- [NSW Legislation Notifications](https://legislation.nsw.gov.au/epub)
- [Accessing Legislation - NSW Parliamentary Counsel's Office](https://pco.nsw.gov.au/accessing-legislation.html)

---

#### NSW Planning Portal (planningportal.nsw.gov.au)
**Authority Level:** ⭐⭐⭐⭐⭐ PRIMARY SOURCE
**Document Types:** SEPP, LEP, DCP
**Update Mechanism:**
- ✅ Email notification subscription service available
- ✅ LEP Update program (lep-update.planning.nsw.gov.au)
- ✅ Planning proposal tracker
- ❌ No public API for planning instrument amendments (API is for DA lodgement only)

**Access Method:**
- Subscribe: [Subscribe for Notifications](https://www.planningportal.nsw.gov.au/major-projects/services/subscribe-notifications)
- Browse: [State Environmental Planning Policies](https://www.planning.nsw.gov.au/policy-and-legislation/state-environmental-planning-policies)
- Track: [LEP Update Program](https://lep-update.planning.nsw.gov.au/)

**Update Frequency:** Real-time for major projects, ongoing for LEP updates

**API Status:**
- ePlanning APIs exist for **DA lodgement** (councils/certifiers)
- Requires API key via email request to ePlanning team
- **NO public API for planning instrument change notifications**

**Sources:**
- [NSW Planning Portal Subscribe for Notifications](https://www.planningportal.nsw.gov.au/major-projects/services/subscribe-notifications)
- [LEP Update Program](https://lep-update.planning.nsw.gov.au/)
- [APIs for ePlanning Digital Services](https://www.planningportal.nsw.gov.au/API)

---

#### NSW Department of Planning Environment
**Authority Level:** ⭐⭐⭐⭐⭐ PRIMARY SOURCE
**Document Types:** SEPP, Planning reforms
**Update Mechanism:**
- ✅ Planning Portal notifications
- ✅ Email updates for major reforms
- ⚠️ No dedicated DCP amendment API

**Key Programs (2026):**
- LEP Update Program: 18 Sydney councils updating LEPs (2-year timeline)
- Remaining Sydney councils: 3-year timeline for LEP updates
- Planning System Reforms Act 2025: Phased implementation over 12 months

**Sources:**
- [NSW Planning Portal Roadmap](https://www.planningportal.nsw.gov.au/NSW-Planning-Portal)
- [Planning Reforms](https://www.planning.nsw.gov.au/policy-and-legislation/planning-reforms)

---

### 2.2 Council-Level Sources

#### Inner West Council (Example: Marrickville, Leichhardt, Ashfield DCPs)
**Authority Level:** ⭐⭐⭐⭐ AUTHORITATIVE
**Document Types:** DCP, LEP amendments
**Update Mechanism:**
- ✅ "Your Say Inner West" portal for public exhibitions
- ✅ Council website news/announcements
- ❌ No RSS feed
- ❌ No API
- ⚠️ Amendment records embedded in PDF documents

**Access Method:**
- Browse: [Development Controls (LEP and DCP)](https://www.innerwest.nsw.gov.au/develop/plans-policies-and-controls/development-controls-lep-and-dcp)
- Track amendments: [Previous Development Controls](https://www.innerwest.nsw.gov.au/develop/plans-policies-and-controls/development-controls-lep-and-dcp/previous-development-controls-and-codes)
- Public exhibition: [Your Say Inner West](https://yoursay.innerwest.nsw.gov.au/)

**Amendment Pattern:**
- DCP amendments announced via council resolution
- Amendment records embedded in DCP PDFs (e.g., "Amendment 11 came into force on 1 August 2019")
- Historical DCP versions kept under "Previous development controls"

**Update Frequency:**
- Major amendments: 6-12 months
- Minor/housekeeping: 1-2 years

**Sources:**
- [Inner West Council Development Controls](https://www.innerwest.nsw.gov.au/develop/plans-policies-and-controls/development-controls-lep-and-dcp)
- [Amendment to DCP - Administrative Updates](https://yoursay.innerwest.nsw.gov.au/amendment-to-dcp-administrative-and-legislative-updates)

---

### 2.3 Community/Third-Party Sources

#### PlanningAlerts.org.au
**Authority Level:** ⭐⭐ INFORMATIONAL ONLY
**Document Types:** Development Applications (NOT DCP/LEP amendments)
**Update Mechanism:**
- ✅ Email alerts for DAs in area
- ❌ Does NOT track DCP/LEP amendments
- ❌ Not useful for regulatory update tracking

**Assessment:** **NOT SUITABLE** for LGA onboarding automation - only tracks DAs, not planning instrument changes.

**Source:**
- [PlanningAlerts.org.au](https://www.planningalerts.org.au/)

---

### 2.4 Source Reliability Ranking

| Rank | Source | Authority | Coverage | Automation | Recommended Use |
|------|--------|-----------|----------|------------|-----------------|
| 1 | NSW Legislation (legislation.nsw.gov.au) | ⭐⭐⭐⭐⭐ | SEPP, LEP | ✅ RSS | **SEPP/LEP monitoring** |
| 2 | NSW Planning Portal | ⭐⭐⭐⭐⭐ | SEPP, LEP, DCP | ⚠️ Email | **Notification subscription** |
| 3 | Council Websites | ⭐⭐⭐⭐ | DCP, LEP | ❌ Manual | **DCP change tracking** |
| 4 | Your Say / Council Portals | ⭐⭐⭐ | DCP, LEP | ❌ Manual | **Public exhibition tracking** |
| 5 | PlanningAlerts.org.au | ⭐⭐ | DA only | ❌ N/A | **Not suitable** |

---

## Section 3: Integration Recommendations

### 3.1 Recommended Monitoring Approach

#### Tier 1: Automated (State-Level)
**SEPP Amendments**
- **Source:** NSW Legislation RSS feed (legislation.nsw.gov.au)
- **Method:** Daily RSS polling
- **Alert Threshold:** New SEPP or amendment detected
- **Action:** Flag for review, trigger extraction pipeline
- **Implementation Complexity:** LOW (RSS feed parser)

**LEP Gazettal**
- **Source:** NSW Legislation RSS feed + Planning Portal notifications
- **Method:** Daily RSS polling + email parsing (if subscription available)
- **Alert Threshold:** LEP amendment gazetted
- **Action:** Flag affected LGA, trigger boundary update check
- **Implementation Complexity:** MEDIUM (RSS + email integration)

---

#### Tier 2: Semi-Automated (Council-Level)
**DCP Amendments**
- **Source:** Council websites + Your Say portals
- **Method:** Weekly web scraping of council news/announcements pages
- **Detection Pattern:**
  - Keywords: "DCP", "Development Control Plan", "amendment", "adopted", "came into force"
  - URLs: Monitor council's DCP page for new PDF URLs
  - File metadata: Check PDF last-modified dates
- **Alert Threshold:** New DCP PDF URL or announcement
- **Action:** Manual review → Extract new DCP → Import to database
- **Implementation Complexity:** MEDIUM-HIGH (web scraping, change detection)

**Council-Specific Strategies:**
- Inner West: Monitor https://www.innerwest.nsw.gov.au/about/news/announcements
- Inner West: Subscribe to "Your Say Inner West" updates
- Each council: Weekly check of DCP page for new PDF URLs

---

#### Tier 3: Manual Review (Low Frequency)
**Planning Reforms**
- **Source:** NSW Planning Portal + Department announcements
- **Frequency:** Monthly review
- **Action:** Assess impact on extraction logic/taxonomy

**Housekeeping Amendments**
- **Source:** Council DCP amendment tables (embedded in PDFs)
- **Frequency:** Quarterly audit
- **Action:** Minor corrections only (typos, formatting)

---

### 3.2 Automated Monitoring: Build vs Subscribe

**Option A: Build Automated Scraper**
**Pros:**
- Full control over timing and granularity
- Can detect changes before official notifications
- Supports historical audit trail

**Cons:**
- Maintenance burden (council sites change frequently)
- False positives from formatting changes
- Ethical/legal considerations (scraping frequency)

**Estimated Effort:** 2-3 weeks initial build + ongoing maintenance

---

**Option B: Subscribe to Notifications + Manual Monitoring**
**Pros:**
- Official notification from authoritative sources
- No scraping maintenance
- Legally compliant

**Cons:**
- Dependent on external notification timing
- May miss unannounced "housekeeping" amendments
- Notification frequency varies by council

**Estimated Effort:** 1 day setup + weekly manual checks

---

**Recommendation:** **Hybrid Approach**
1. **Automate:** NSW Legislation RSS monitoring (SEPP/LEP)
2. **Subscribe:** NSW Planning Portal email notifications
3. **Manual:** Monthly council website checks (DCP)
4. **Quarterly:** Audit DCP amendment tables in PDFs

**Rationale:**
- SEPP/LEP changes are high-impact and centralized → automate
- DCP changes are low-frequency (1-2 per year per council) → manual acceptable
- Hybrid balances automation ROI vs maintenance burden

---

### 3.3 Update Frequency by Document Type

| Document Type | Typical Update Frequency | Impact on Onboarding | Recommended Monitoring |
|---------------|-------------------------|---------------------|------------------------|
| **SEPP** | 2-4 times/year (state-wide) | HIGH (affects all LGAs) | Daily RSS check |
| **LEP** | 1-2 times/year per LGA | HIGH (zoning, land use) | Weekly RSS check |
| **DCP** | 1-2 times/year per LGA | MEDIUM (controls) | Monthly manual check |
| **DCP Housekeeping** | 1-3 times/year per LGA | LOW (typos, formatting) | Quarterly audit |

---

### 3.4 Priority Implementation Order

**Phase 1 (Week 1-2): Infrastructure Foundation**
1. ✅ Run provision versioning migration (`create_version_schema.sql`)
2. ✅ Backfill existing provisions with version 1 baseline
3. ✅ Test historical "as-of-date" queries
4. ✅ Validate provision_change_log functionality

**Phase 2 (Week 3-4): Automated Monitoring (SEPP/LEP)**
1. Build NSW Legislation RSS poller
2. Parse SEPP/LEP amendment notifications
3. Set up email alerts for new entries
4. Test with recent SEPP Housing 2021 amendments

**Phase 3 (Month 2): Council DCP Monitoring**
1. Subscribe to NSW Planning Portal notifications
2. Create manual monitoring checklist for councils (Inner West, etc.)
3. Set up quarterly DCP audit process
4. Document council-specific update patterns

**Phase 4 (Month 3): Integration with Onboarding Pipeline**
1. Trigger extraction pipeline on SEPP/LEP alerts
2. Create "DCP update detected" workflow for manual review
3. Build version comparison UI for certifiers
4. Test with historical amendment (e.g., Inner West DCP Amendment 11)

---

### 3.5 Critical Gaps to Address

**Database Schema:**
- ❌ provision_versions table MUST be created before onboarding automation
- ❌ regulatory_provisions versioning columns MUST be added
- ❌ provision_change_log table needed for audit trail

**Extraction Pipeline:**
- ⚠️ No mechanism to detect "which provisions changed" between DCP versions
- ⚠️ Need diff algorithm to compare old vs new DCP extractions
- ⚠️ Need deduplication logic (same provision, updated text)

**Data Quality:**
- ⚠️ versions.document_versions has 110 records but no linkage to regulatory_provisions
- ⚠️ No "last_verified_date" field in regulatory_provisions
- ⚠️ No staleness warnings for certifiers

---

## Section 4: Conclusion

### Current State Summary
- **Document versioning:** LIVE but unused (110 baseline records, no history yet)
- **Provision versioning:** SCHEMA DEFINED but NOT DEPLOYED
- **Update monitoring:** NO automation in place

### Readiness for LGA Onboarding Automation
**Status: NOT READY**

**Blockers:**
1. Provision versioning infrastructure NOT deployed (tables don't exist)
2. No automated monitoring of regulatory updates
3. No diff/change detection for DCP amendments

### Next Steps
1. **Immediate:** Run provision versioning migration to production
2. **Week 1:** Build NSW Legislation RSS monitor for SEPP/LEP
3. **Week 2:** Subscribe to Planning Portal notifications
4. **Month 1:** Establish manual DCP monitoring process for target councils
5. **Month 2:** Build provision diff algorithm for amendment detection
6. **Month 3:** Integrate with LGA onboarding pipeline

### Estimated Timeline to Production-Ready
- **Minimum viable:** 4-6 weeks (manual monitoring + provision versioning)
- **Fully automated:** 8-12 weeks (RSS monitoring + diff detection + pipeline integration)

---

## Appendix: Key Resources

### Migration Scripts
- `migrations/add_version_tracking.sql` - Document-level versioning
- `scripts/migrations/create_version_schema.sql` - Provision-level versioning
- `scripts/migrations/optimize_version_performance.sql` - Version query indexes

### Python Services
- `services/version_manager.py` - Document version management
- `services/version_aware_query.py` - Historical provision queries
- `sepp_full_text_extraction/version_tracking.py` - Change detection utilities

### API Endpoints
- `/api/versions` - Document version queries (works)
- `/api/provisions/changes` - Provision change log (broken - tables don't exist)
- `/api/provisions/for-property` - Has version support (not active yet)

### Official Sources
- NSW Legislation: https://legislation.nsw.gov.au/epub
- NSW Planning Portal: https://www.planningportal.nsw.gov.au/
- LEP Update Program: https://lep-update.planning.nsw.gov.au/
- Inner West Council: https://www.innerwest.nsw.gov.au/develop/plans-policies-and-controls/development-controls-lep-and-dcp

---

**Report Compiled By:** Claude Sonnet 4.5
**Date:** 2026-02-10
