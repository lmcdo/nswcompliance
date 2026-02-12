# LGA Onboarding Automation - Documentation Index

**Investigation Phase Complete:** 2026-02-11
**Status:** Ready for staging deployment
**Risk Level:** LOW-MEDIUM (additive changes, full rollback capability)

---

## Quick Access Links

### Critical Deployment Documents

**Location:** `plans/lga-onboarding/` (project root)

1. **`plans/lga-onboarding/lga-onboarding-versioning-deployment.md`**
   - Complete deployment plan for versioning infrastructure
   - Step-by-step staging and production deployment
   - Validation queries and rollback procedures
   - Post-deployment monitoring checklist
   - **Use this for:** Executing Phase 0 deployment

2. **`plans/lga-onboarding/production-safety-deployment-practices.md`**
   - Production-safe deployment best practices
   - Two-database strategy (staging + production)
   - Backup and restore procedures
   - Feature flag patterns
   - Rollback decision trees
   - **Use this for:** General deployment safety guidelines

3. **`plans/lga-onboarding/lga-onboarding-versioning-research-report.md`**
   - Current state of versioning infrastructure
   - NSW Planning update sources (legislation.nsw.gov.au, Planning Portal)
   - Regulatory update monitoring strategy
   - Council-specific update patterns
   - **Use this for:** Understanding context and research findings

4. **`plans/lga-onboarding/lga-onboarding-architecture-analysis.md`**
   - 6 critical architectural issues blocking automation
   - Root cause analysis (11-19 hours manual effort)
   - Recommended solutions with tradeoff analysis
   - Implementation roadmap (Phase 0-4)
   - **Use this for:** Understanding the WHY behind the implementation plan

### Architectural Analysis (This Session)

**Location:** Plan mode transcript at:
`C:\Users\lawre\.claude\projects\C--Users-lawre-Downloads-solvyra-projects-compliance-engine-compliance-engine\65b0ee1f-5c08-4c22-bd0f-6616c4b7a6d3.jsonl`

**Key Findings:**
- 6 critical architectural issues blocking LGA onboarding automation
- Current manual effort: 11-19 hours per LGA
- Target automated effort: 2-4 hours per LGA (82-88% reduction)
- ROI for 130 LGAs: 1,170-1,950 hours saved

---

## Problem Statement

**Current State:**
- Onboarding new LGA (Local Government Area) requires 11-19 hours of manual engineering work
- Manual DCP structure config creation (4-5 hours)
- Hardcoded Python extraction logic per council
- No automated regulatory update monitoring
- Provision versioning infrastructure exists as code but NOT deployed to production

**Goal:**
- Reduce LGA onboarding to 2-4 hours (82-88% time savings)
- Deploy versioning infrastructure to enable change tracking
- Automate SEPP/LEP update monitoring
- Scale to 130 LGAs across NSW

---

## Phased Implementation Plan

### Phase 0: Deploy Versioning Infrastructure (CRITICAL PATH - CURRENT FOCUS)

**Why First:**
- Foundation for everything else (LGA onboarding, regulatory updates, historical queries)
- Low risk (additive changes only, no data modification)
- Fast rollback (< 5 minutes)

**Timeline:** 3 weeks conservative (1 week aggressive)

**Steps:**
1. **Week 1:** Deploy schema only (provision_versions, provision_change_log tables)
2. **Week 2:** Backfill version 1 baseline (46,585 provisions)
3. **Week 3:** Enable version-aware queries (feature flag)

**Effort:** 4-6 hours staging + 2-3 hours production validation

**Documents:**
- Deployment plan: `lga-onboarding-versioning-deployment.md`
- Safety practices: `production-safety-deployment-practices.md`

**Status:** ⏸️ Awaiting approval for staging deployment

---

### Phase 1: Add Council Schema (Blocked by Phase 0)

**Goal:** Proper relational structure for councils

**Tasks:**
1. Create `councils` reference table
2. Add `council_id` foreign key to `regulatory_provisions`
3. Add `council_id` to `versions.document_versions` (versioning integration)
4. Migrate existing data (parse document_id → council_id)
5. Update API queries to use `council_id` instead of LIKE patterns

**Effort:** 6-8 hours

**Impact:**
- 10x faster queries (indexed FK vs LIKE pattern)
- Proper normalization for 130 LGAs
- Enables multi-LGA analytics

**Unlocks:** Phase 2 automation tools

---

### Phase 2: Automation Tools (Blocked by Phase 1)

**Goal:** Reduce manual config creation from 6-8 hours to 1-2 hours

**Tools to Build:**

1. **LLM-Assisted DCP Config Generator**
   - Input: DCP PDF table of contents
   - Output: Python config file (e.g., `marrickville_config.py`)
   - Effort: 8-10 hours to build
   - Savings: 4 hours → 1 hour per LGA (75% reduction)

2. **RAG-Assisted Topic Mapper**
   - Input: Council marker (e.g., "C1") + provision text
   - Output: Topic suggestion with confidence score
   - Effort: 6-8 hours to build
   - Savings: 1.5 hours → 20 minutes per LGA (78% reduction)

3. **Config-Driven Marker Extraction**
   - Input: YAML pattern config (regex for C1, DS1, etc.)
   - Output: Extracted markers from provisions
   - Effort: 4-6 hours to build
   - Savings: 1.5 hours → 15 minutes per LGA (83% reduction)

**Total Effort:** 18-24 hours to build tools
**Total Savings:** 7-8 hours per LGA → 1.5-2 hours per LGA

---

### Phase 3: Registry Pattern (Parallel with Phase 2)

**Goal:** Make system extensible without code changes

**Tasks:**
1. Implement council tagger registry
2. Extract existing logic to per-council modules
3. Create template for new councils

**Effort:** 8-10 hours

**Impact:**
- Adding new council = new file, no core code changes
- Enables parallel development (multiple councils at once)
- Scales to 130 LGAs

---

### Phase 4: Regulatory Update Monitoring

**Goal:** Timely detection of SEPP/LEP/DCP updates

**Monitoring Strategy:**

| Document Type | Source | Method | Frequency | Automation |
|---------------|--------|--------|-----------|------------|
| SEPP | NSW Legislation | RSS feed | Daily | ✅ Automated |
| LEP | NSW Legislation + Portal | RSS + Email | Weekly | ✅ Automated |
| DCP | Council websites | Manual check | Monthly | ❌ Manual |

**Tasks:**
1. Build NSW Legislation RSS poller (SEPP/LEP)
2. Subscribe to Planning Portal email notifications
3. Create monthly DCP audit checklist

**Effort:** 8-12 hours

**Savings:** No more manual constant checking, timely update detection

---

## Architecture Issues Identified

### Issue 1: Python DCP Structure Configs Are Completely Manual ⚠️ HIGH IMPACT
**Time Impact:** 4-5 hours per LGA (35% of total manual effort)

**Current:**
- Engineer manually reads 300-page DCP
- Creates Python config mapping structure (e.g., `marrickville_config.py`)
- Error-prone, requires DCP expertise

**Solution:** LLM-assisted config generation (Phase 2)

---

### Issue 2: Layer/Topic Tagging Uses If/Else Council Detection ⚠️ HIGH IMPACT
**Impact:** Doesn't scale beyond 10-20 councils (architectural ceiling)

**Current:**
```python
if 'marrickville' in doc_lower:
    return self._tag_marrickville()
elif 'leichhardt' in doc_lower:
    return self._tag_leichhardt()
# For 130 LGAs, this becomes unmaintainable
```

**Solution:** Registry pattern (Phase 3)

---

### Issue 3: No council_id Field - Councils Identified By String Matching ⚠️ MEDIUM IMPACT
**Impact:** Fragile queries, no relational integrity

**Current:**
```sql
SELECT * FROM regulatory_provisions
WHERE document_id LIKE 'Marrickville%'  -- Fragile string matching
```

**Solution:** Add council_id foreign key (Phase 1)

---

### Issue 4: Topic Marker Mappings Are Static Python Dictionaries ⚠️ MEDIUM IMPACT
**Time Impact:** 1-2 hours per LGA

**Current:**
```python
LEICHHARDT_C_TOPICS = {
    'C1': 'site_analysis',
    'C2': 'heritage',
    # ... 53 more hardcoded mappings
}
```

**Solution:** RAG-assisted topic mapping (Phase 2)

---

### Issue 5: Marker Extraction Logic Hardcoded Per Council ⚠️ MEDIUM IMPACT
**Time Impact:** 1-2 hours per LGA

**Current:**
```python
def extract_ashfield_marker(self, text: str):
    # Custom regex for DS1, PC1, C1-C10, O1-O10
    # 4 different marker types, custom regex each
```

**Solution:** Config-driven regex patterns (Phase 2)

---

### Issue 6: Frontend Precinct Normalization Is Council-Specific ⚠️ LOW IMPACT
**Impact:** Coupling concern, not time-critical

**Current:**
```typescript
if (lga.toLowerCase().includes('marrickville')) {
    return precinct_id.replace(/^9_/, '') || precinct_id;
}
```

**Solution:** Move normalization to backend (Phase 4 cleanup)

---

## Versioning Infrastructure Details

### Current State (Pre-Deployment)

**EXISTS:**
- ✅ `versions.document_versions` table (110 documents)
- ✅ Version manager code (`services/version_manager.py`)
- ✅ Migration scripts (tested in archive)

**MISSING:**
- ❌ `provision_versions` table (migration exists but never run)
- ❌ `provision_change_log` table (migration exists but never run)
- ❌ Versioning columns in `regulatory_provisions` (version_id, is_current, current_version_id, etc.)

**Translation:** 46,585 provisions have ZERO version tracking

---

### Deployment Approach (Conservative)

**Week 1: Schema Only**
- Deploy empty tables
- Add nullable columns to regulatory_provisions
- Risk: VERY LOW (no data changes)
- Rollback: < 1 minute (drop empty tables)

**Week 2: Backfill Data**
- Populate version 1 baseline for all provisions
- Risk: LOW (just inserting data)
- Rollback: 5 minutes (truncate tables, set columns to NULL)

**Week 3: Enable Version-Aware Queries**
- Deploy code with feature flag
- Risk: LOW (instant rollback via flag toggle)
- Rollback: 30 seconds (disable flag)

---

## Regulatory Update Sources

### NSW Legislation Website (SEPP/LEP) - ⭐⭐⭐⭐⭐
**URL:** https://legislation.nsw.gov.au/
- ✅ RSS/Atom feeds available
- ✅ Updates within 3 business days
- ✅ Complete archive 2008-2026
- **Recommendation:** Daily RSS polling

### NSW Planning Portal - ⭐⭐⭐⭐⭐
**URL:** https://www.planningportal.nsw.gov.au/
- ✅ Email notification subscription
- ✅ LEP Update program tracker
- ❌ NO public API for amendments
- **Recommendation:** Subscribe + manual monthly check

### Council Websites (DCP) - ⭐⭐⭐⭐
**Example:** https://www.innerwest.nsw.gov.au/develop/plans-policies-and-controls/development-controls-lep-and-dcp
- ✅ Authoritative source for DCP amendments
- ❌ NO RSS feeds or APIs
- ⚠️ Amendment records embedded in PDF
- **Recommendation:** Monthly manual checks

### Update Frequency Reality Check
- **SEPP:** 2-4 updates per year (state-wide)
- **LEP:** 1-2 updates per LGA per year
- **DCP:** 1-2 updates per LGA per year (often administrative)

**Translation:** Regulatory updates are NOT constant. Monthly monitoring sufficient.

---

## Success Metrics

### Phase 0 Success Criteria
- ✅ All 46,585 provisions have version 1 baseline
- ✅ All provisions marked `is_current = true`
- ✅ API endpoints return correct data (no errors)
- ✅ Query performance within 10% of baseline
- ✅ Zero version-related errors for 24 hours post-deployment

### Overall Project Success (All Phases Complete)
- ✅ LGA onboarding reduced from 11-19 hours to 2-4 hours
- ✅ 82-88% time savings validated across 3+ new LGAs
- ✅ Automated SEPP/LEP monitoring operational
- ✅ Version tracking for all provision changes
- ✅ Registry pattern supports 130 LGAs
- ✅ Council schema enables multi-LGA analytics

---

## Risk Assessment

### Phase 0 (Versioning Infrastructure)
**Risk Level:** LOW-MEDIUM
- Changes are additive (no data modification)
- All changes are reversible
- Rollback time < 5 minutes
- Failure modes are recoverable

### Phase 1 (Council Schema)
**Risk Level:** MEDIUM
- Requires data migration (parse document_id → council_id)
- Foreign key constraints must be validated
- Rollback requires restoring from backup
- Mitigation: Extensive staging testing

### Phase 2 (Automation Tools)
**Risk Level:** LOW
- New tools don't affect existing functionality
- Can be tested in isolation
- Rollback: Just don't use the tools

### Phase 3 (Registry Pattern)
**Risk Level:** MEDIUM
- Refactors core extraction logic
- Must maintain backward compatibility
- Extensive testing required
- Mitigation: Keep old code as fallback for 1 release

---

## Next Actions

### Immediate (This Week)
- [ ] Review deployment plans with stakeholders
- [ ] Set up staging database (if not exists)
- [ ] Sync production schema to staging
- [ ] Run Phase 0 deployment on staging
- [ ] Validate versioning infrastructure works

### Short-Term (Next 2-4 Weeks)
- [ ] Deploy versioning to production (Phase 0)
- [ ] Begin Phase 1 (council schema) design
- [ ] Research LLM config generation approach
- [ ] Subscribe to NSW Planning Portal notifications

### Medium-Term (Next 2-3 Months)
- [ ] Complete Phase 1 (council schema)
- [ ] Build automation tools (Phase 2)
- [ ] Implement registry pattern (Phase 3)
- [ ] Onboard 2-3 test LGAs with new tools
- [ ] Validate 82-88% time savings

### Long-Term (6+ Months)
- [ ] Scale to 130 LGAs
- [ ] Automated regulatory update pipeline
- [ ] Version comparison UI for certifiers
- [ ] Multi-LGA analytics capabilities

---

## MapLibre Expansion Plan (Active)

**Location:** `C:\Users\lawre\.claude\plans\noble-honking-coral.md`

**Purpose:** Service offering exploration for MapLibre GL Components integration with PlotDetect

**6 Options Explored:**
| Option | Summary | Effort | Competition |
|--------|---------|--------|-------------|
| A: Heritage Explorer | Interactive heritage map | 4-6 wks | None |
| B: Scout Revival | Site finder | 8-12 wks | Archistar |
| C: Council Dashboard | Heritage monitoring | 12-16 wks | None |
| D: Verify Map Context | Mini-map in Property Card | 2-3 wks | None |
| E: Embed Widgets | White-label for partners | 4-6 wks | None |
| F: Hybrid Scout+Heritage | Differentiated site finder | 10-14 wks | Partial |

**Recommended Path:** D → A (validate with mini-map, then Heritage Explorer)

**Includes:**
- 3D Building Height Data sources (NSW Spatial Digital Twin, Overture Maps)
- Implementation & Rollout Management best practices
- Feature flag strategy
- Database protection approach
- Granular rollout phases (internal → beta → GA)
- Pre-deploy checklist

---

## Related Documentation

### Related Strategic Documents
**Location:** `plans/strategic/` and `plans/expansion/`

**Strategic Context (Heritage pivot):**
- **`plans/strategic/recent-documents-summary.md`** - Index of all 22 documents from last 7 days
  - Strategic pivot from generic compliance to heritage specialist
  - Heritage SOHI Assistant, Pre-Check, Council Co-Pilot
  - Revenue potential: $1M-$3M/year

- **`plans/strategic/competitive-landscape-jan2026.md`** - Archistar/PropCode competitive analysis
  - Archistar already dominates 3D envelopes ($22.7M, 130k users)
  - PropCode has NSW LEP/DCP digitization
  - Only white space: Heritage compliance automation

- **`plans/strategic/propcode-analysis-and-api-services.md`** - PropCode gaps + PlotDetect API strategy
  - PropCode likely has: Zoning, LEP controls
  - PropCode likely doesn't have: Detailed DCP provisions
  - PlotDetect API services: Heritage Provision API ($0.50/call), DCP Filtering API ($0.30/call)

- **`plans/strategic/geospatial-heritage-innovation.md`** - 5 geospatial strategies
  - Heritage Fabric Database (SAMGeo aerial imagery analysis)
  - Viewshed Analysis (GRASS r.viewshed + LiDAR)
  - Change Detection (SAMGeo + Nearmap quarterly monitoring)
  - Spatial DA Predictor (ML + GIS features, 82% accuracy)
  - Aboriginal Heritage Prediction (Random Forest + terrain)
  - Revenue potential: $750k-$2M/year

**Expansion Planning:**
- **`plans/expansion/multi-lga-expansion-plan.md`** - Previous LGA expansion planning
- **`plans/expansion/council-sales-playbook.md`** - Council acquisition strategy

### Project Documentation (.claude directory)
- `COUNCIL_ONBOARDING_RESEARCH.md` - Previous council onboarding research
- `DATA_QUALITY_TRACKER.md` - Data quality issues and fixes
- `DB_SCHEMA.md` - Database schema quick reference

### Database Documentation
- `DB_SCHEMA.md` - Quick reference (project root)
- `DB_SCHEMA_RAW.txt` - Full schema dump (project root)

### Migration Files
- `migrations/add_version_tracking.sql` - Document-level versioning (already run)
- `scripts/migrations/create_version_schema.sql` - Provision-level versioning (READY TO RUN)
- `scripts/migrations/optimize_version_performance.sql` - Performance optimization (run after backfill)

### Python Services
- `services/version_manager.py` - Document version management
- `services/version_aware_query.py` - Version-aware query wrappers
- `scripts/backfill_provision_versions.py` - Version 1 baseline creation

### API Routes
- `frontend-nextjs/app/api/versions/route.ts` - Version management API
- `frontend-nextjs/app/api/provisions/changes/route.ts` - Change tracking API
- `frontend-nextjs/app/api/provisions/for-property/route.ts` - Provisions API (lines 689-713 have version support)

---

## Questions & Decisions

### Resolved
- ✅ **Use two-database approach?** YES (staging + production)
- ✅ **Deploy versioning first?** YES (unblocks everything else)
- ✅ **Phased deployment?** YES (3 weeks conservative, 1 week aggressive)
- ✅ **Automated DCP monitoring?** NO initially (manual monthly sufficient)
- ✅ **Build RSS monitor for SEPP/LEP?** YES (high-impact, easy to automate)

### Pending
- ⏸️ **Approve Phase 0 staging deployment?** Awaiting user confirmation
- ⏸️ **Timeline preference?** Conservative (3 weeks) or aggressive (1 week)?
- ⏸️ **Feature flags for version queries?** Recommended but optional
- ⏸️ **Council schema design details?** Blocked until Phase 0 complete

---

## Changelog

**2026-02-11:**
- Created LGA Onboarding Index
- Completed architectural analysis (6 critical issues identified)
- Researched NSW planning update sources
- Created deployment plans for versioning infrastructure
- Created production safety best practices guide
- Status: Ready for Phase 0 staging deployment

---

## Contact & Escalation

**For Questions About:**
- Deployment plans: Review `production-safety-deployment-practices.md`
- Versioning infrastructure: Review `lga-onboarding-versioning-deployment.md`
- Research findings: Review `lga-onboarding-versioning-research-report.md`
- Architectural issues: Review plan mode transcript (65b0ee1f-5c08-4c22-bd0f-6616c4b7a6d3.jsonl)

**For Deployment Issues:**
- Database: Refer to rollback procedures in deployment plan
- Application: Feature flag toggle (instant rollback)
- Data integrity: Restore from backup (10 minutes)

---

**Last Updated:** 2026-02-11
**Status:** Documentation complete, ready for deployment execution
