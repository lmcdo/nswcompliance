# Standard Operating Procedures - Index

**Last Updated:** 2025-10-27
**Project:** NSW Planning Compliance Engine

---

## Quick Reference

### Main SOP Document

**[SOP_PRECINCT_INTEGRATION_AND_UX.md](SOP_PRECINCT_INTEGRATION_AND_UX.md)**

Comprehensive SOP covering:
- Data quality assessment
- Provision text cleanup
- Precinct coverage analysis
- UX improvements implementation
- UX testing procedures
- Troubleshooting
- Rollback procedures

---

## SOP Quick Access

### SOP-001: Data Quality Assessment
**Purpose:** Identify and prioritize data quality issues
**Frequency:** Monthly, or after PDF extraction
**Time:** 30-45 minutes
**[Go to SOP-001 →](SOP_PRECINCT_INTEGRATION_AND_UX.md#sop-001-data-quality-assessment)**

**Key Steps:**
1. Create safety backup
2. Identify malformed provisions
3. Apply data quality decision matrix
4. Document findings
5. Verify against standards

---

### SOP-002: Provision Text Cleanup
**Purpose:** Remove PDF extraction artifacts
**Frequency:** When >2% provisions malformed
**Time:** 1-2 hours
**[Go to SOP-002 →](SOP_PRECINCT_INTEGRATION_AND_UX.md#sop-002-provision-text-cleanup)**

**Key Steps:**
1. Pre-cleanup safety backup
2. Analyze malformation patterns
3. Design cleanup patterns
4. Test on sample data
5. Execute bulk cleanup
6. Migrate to dependent tables
7. Verify cleanup
8. Document results

---

### SOP-003: Precinct Coverage Analysis
**Purpose:** Analyze completeness of precinct data
**Frequency:** Monthly, or after precinct extraction
**Time:** 30 minutes
**[Go to SOP-003 →](SOP_PRECINCT_INTEGRATION_AND_UX.md#sop-003-precinct-coverage-analysis)**

**Key Steps:**
1. Check precinct boundary coverage
2. Identify missing provisions
3. Analyze provision density
4. Check LLM categorization coverage
5. Document findings

---

### SOP-004: UX Improvements Implementation
**Purpose:** Implement UX enhancements for precinct integration
**Frequency:** As needed for UX improvements
**Time:** 2-4 hours
**[Go to SOP-004 →](SOP_PRECINCT_INTEGRATION_AND_UX.md#sop-004-ux-improvements-implementation)**

**Key Steps:**
1. Review requirements
2. Create Git branch
3. Implement frontend changes
4. Test locally
5. Create documentation
6. Commit changes

---

### SOP-005: UX Testing Procedures
**Purpose:** Systematically test UX improvements
**Frequency:** After every UX implementation
**Time:** 1-2 hours
**[Go to SOP-005 →](SOP_PRECINCT_INTEGRATION_AND_UX.md#sop-005-ux-testing-procedures)**

**Key Steps:**
1. Setup test environment
2. Execute 8 test cases
3. Document test results
4. Cross-browser testing (optional)
5. Mobile responsiveness testing

**Test Cases:**
1. Info Box Display
2. Cross-Reference - Setback Overlap
3. Scroll Functionality
4. Category Filter Overlap
5. No Overlap - General Notice
6. No Precinct - No Warning
7. Multiple Category Filters
8. Info Box Accessibility

---

## Emergency Procedures

### Database Issues
**[Go to Troubleshooting →](SOP_PRECINCT_INTEGRATION_AND_UX.md#troubleshooting-guide)**

Common issues:
- Database connection fails
- Backup fails
- Regex cleanup removes too much content

### Frontend Issues
**[Go to Troubleshooting →](SOP_PRECINCT_INTEGRATION_AND_UX.md#troubleshooting-guide)**

Common issues:
- Cross-reference link not appearing
- Scroll not working
- LLM categorization missing

### Rollback Procedures
**[Go to Rollback →](SOP_PRECINCT_INTEGRATION_AND_UX.md#rollback-procedures)**

Three levels:
1. Single table restore (quick)
2. Full database restore (comprehensive)
3. Git revert (frontend changes)

---

## Data Quality Decision Matrix

Quick reference for prioritizing data quality issues:

| Percentage Affected | Core Table? | Priority |
|---------------------|-------------|----------|
| > 2% | Yes | Priority 1 |
| 0.5-2% | Yes | Priority 2 |
| < 0.5% | Yes | Priority 3 |
| Any | No | Lower priority |

**IMPORTANT:** Workarounds do NOT lower priority for core table issues!

**[See full matrix in CLAUDE.md →](CLAUDE.md)**

---

## Database Safety Checklist

Before ANY database operation:

- [ ] Read CLAUDE.md database section
- [ ] Create full backup
- [ ] Verify backup file exists (size > 0)
- [ ] Test on sample data first
- [ ] Use transaction (BEGIN/COMMIT/ROLLBACK)
- [ ] Use timeouts (30 seconds max)
- [ ] Use db_safety_wrapper.py
- [ ] Document what you're doing
- [ ] Have rollback plan ready

**If ANY issue: STOP, ROLLBACK, INVESTIGATE**

---

## Test Data Reference

**Test Address for UX Testing:**

**123 Fisher Street, Petersham**
- Precinct: 6_ (Petersham South)
- Provisions: 34
- Categorization: ✅ Complete
- Categories:
  - building_height: 1
  - landscaping: 2
  - other: 3
  - setback_front: 1
  - setback_rear: 1
  - setback_side: 1

**[See full test data →](SOP_PRECINCT_INTEGRATION_AND_UX.md#appendix-a-test-data-reference)**

---

## File Locations

### Documentation
- **Main SOP:** `SOP_PRECINCT_INTEGRATION_AND_UX.md`
- **This Index:** `SOP_INDEX.md`
- **Project Instructions:** `CLAUDE.md`
- **Primary Directive:** `CLAUDE_PRIMARY_DIRECTIVE.md`

### Frontend Components
- `frontend-nextjs/components/compliance/ComplianceDashboard.tsx`
- `frontend-nextjs/components/compliance/DCPProvisionsBrowser.tsx`
- `frontend-nextjs/components/compliance/CategorizedRequirementsCard.tsx`

### API Routes
- `frontend-nextjs/app/api/compliance/precinct-requirements/route.ts`
- `frontend-nextjs/app/api/dcp/provisions/route.ts`

### Database Migrations
- `migrations/populate_dcp_precinct_provisions.sql`
- `migrations/create_precinct_boundaries.sql`

### Backups
- Location: `backups/`
- Format: `nsw_planning_[purpose]_[YYYYMMDD_HHMMSS].backup`

---

## Recent Completion Reports

### Completed Work (2025-10-27)

1. **[PROVISION_TEXT_CLEANUP_COMPLETE.md](PROVISION_TEXT_CLEANUP_COMPLETE.md)**
   - Cleaned 99% of malformed Marrickville DCP provisions
   - Removed PDF headers while preserving structure
   - Status: ✅ Complete

2. **[PRECINCT_INTEGRATION_DEEP_DIVE.md](PRECINCT_INTEGRATION_DEEP_DIVE.md)**
   - Analyzed precinct coverage (45/46 have provisions)
   - Documented LLM categorization (42/46 complete)
   - Explained general vs precinct UX architecture
   - Status: ✅ Complete

3. **[UX_IMPROVEMENTS_IMPLEMENTATION_COMPLETE.md](UX_IMPROVEMENTS_IMPLEMENTATION_COMPLETE.md)**
   - Implemented "Supplement or Override" info box
   - Added cross-reference link with overlap detection
   - Added scroll-to-precinct functionality
   - Status: ✅ Ready for testing

---

## Next Actions

### Immediate (This Week)
1. **Test UX Improvements** - Execute all 8 test cases from SOP-005
2. **Fix Missing Provisions** - 4 precincts (2, 36, 38, 40) have no provisions
3. **Fix Missing Categorization** - 2 precincts (4, 47) need LLM categorization

### Short-Term (This Month)
1. **Apply cleanup to other documents** - Check if other DCPs have PDF header issues
2. **Enrich sparse precincts** - 27 precincts have < 8 provisions
3. **Cross-browser testing** - Test on Chrome, Firefox, Safari, Edge

### Long-Term (This Quarter)
1. **Prevent future PDF issues** - Update extraction scripts
2. **Monitor data quality** - Add to daily health checks
3. **User feedback** - Collect feedback on UX improvements

---

## Glossary

**DCP:** Development Control Plan - Local planning controls
**LEP:** Local Environmental Plan - Zoning regulations
**SEPP:** State Environmental Planning Policy - State-level overrides
**LGA:** Local Government Area (e.g., Inner West Council)
**Precinct:** Sub-area within LGA with specific planning controls
**Provision:** Individual planning requirement or control
**Categorization:** LLM-processed grouping of provisions by type
**Malformation:** Data corruption from PDF extraction artifacts

---

## Support

### Documentation Issues
- Check: This index for quick links
- Read: Full SOP for detailed procedures
- Refer: CLAUDE.md for project standards

### Technical Issues
- Database: See Troubleshooting Guide
- Frontend: Check browser console
- Rollback: See Rollback Procedures section

### Questions
- Consult: SOP_PRECINCT_INTEGRATION_AND_UX.md
- Review: Appendices for reference data
- Check: Recent completion reports for context

---

**Last Review:** 2025-10-27
**Next Review:** 2025-11-27 (or after major changes)
