# Plans Directory

**Purpose:** Actionable planning documents for PlotDetect/ComplianceEngine development and strategy.

**Organization:** Documents are organized by category for easy navigation.

---

## Directory Structure

```
plans/
├── lga-onboarding/          # LGA automation deployment plans
├── strategic/               # Strategic direction and competitive analysis
├── expansion/               # Multi-LGA expansion and council sales
└── README.md               # This file
```

---

## LGA Onboarding (`lga-onboarding/`)

**Focus:** Deploy versioning infrastructure and automation tools to reduce LGA onboarding from 11-19 hours to 2-4 hours.

### Documents

1. **`lga-onboarding-infrastructure.md`**
   - Scalable LGA onboarding framework for DCP processing
   - 5-phase automation pipeline (DCP discovery, priority ID, schema config, tagging, UI)
   - Universal vs council-specific architecture patterns
   - Config-driven UI (eliminates hardcoded council logic)
   - Onboarding target: 1-week per LGA (vs current undefined/manual)
   - Incorporates latest Inner West learnings (heritage bugs, spatial areas)

2. **`extraction-pipeline-implementation.md`**
   - Production-grade extraction pipeline (PDF → DB)
   - 8-stage architecture (ingestion, structure, extraction, splitting, LLM, spatial, QA, insert)
   - Dual-pass LLM validation with review queue
   - Error handling (DLQ, checkpoints, retry logic)
   - Testing strategy and success metrics
   - Target: <8 hours processing, >95% accuracy, zero data loss

3. **`lga-onboarding-versioning-deployment.md`**
   - Complete deployment plan for Phase 0 (versioning infrastructure)
   - Step-by-step staging and production deployment
   - Validation queries and rollback procedures
   - Post-deployment monitoring checklist
   - Rollback time: < 5 minutes

4. **`lga-onboarding-versioning-research-report.md`**
   - Current state of versioning infrastructure (partially dormant)
   - NSW Planning update sources (legislation.nsw.gov.au, Planning Portal)
   - Regulatory update monitoring strategy (automated SEPP/LEP, manual DCP)
   - Council-specific update patterns

5. **`production-safety-deployment-practices.md`**
   - Production-safe deployment best practices
   - Two-database strategy (staging + production)
   - Backup and restore procedures
   - Feature flag patterns
   - Rollback decision trees

### Current Status
- **Phase 0:** Ready for staging deployment (versioning infrastructure)
- **Phase 1:** Blocked (council schema - needs Phase 0 first)
- **Phase 2-4:** Planned

---

## Strategic Documents (`strategic/`)

**Focus:** Heritage specialist niche positioning, competitive landscape, and revenue strategies.

### Documents

1. **`recent-documents-summary.md`**
   - Master index of all 22 documents from last 7 days
   - Strategic pivot from generic compliance to heritage specialist
   - Overview of all screencasts, user stories, technical docs
   - Revenue potential: $1M-$3M/year

2. **`competitive-landscape-jan2026.md`**
   - Archistar competitive analysis ($22.7M, 130k users, 3D envelopes)
   - PropCode NSW digitization (LEP/DCP data)
   - Only white space: Heritage compliance automation
   - Why generic compliance is not defensible

3. **`propcode-analysis-and-api-services.md`**
   - PropCode capability gaps (has LEP zoning, likely not DCP provisions)
   - PlotDetect API strategy (Heritage Provision API, DCP Filtering API)
   - API pricing: $500/month for 1,000 calls
   - Target customers: Archistar, CoreLogic, LEAP/InfoTrack
   - Revenue: $30k Y1 → $372k Y3

4. **`geospatial-heritage-innovation.md`**
   - 5 geospatial strategies using Open Geospatial Solutions tools
   - Heritage Fabric Database (SAMGeo aerial imagery → quantify character)
   - Viewshed Analysis (GRASS r.viewshed + LiDAR → visual impact)
   - Change Detection (SAMGeo + Nearmap → monitor 100% of heritage properties)
   - Spatial DA Predictor (ML + GIS → 82% accuracy)
   - Aboriginal Heritage Prediction (Random Forest → avoid $50k salvage costs)
   - Revenue potential: $750k-$2M/year

### Strategic Direction
- **Niche:** Heritage compliance automation
- **Target:** Heritage consultants, architects, councils
- **Revenue:** $60k Y1 → $656k Y3 (platform) + $750k-$2M/year (geospatial)
- **Moat:** Heritage DA dataset (5,000 DAs), geospatial infrastructure, council partnerships

---

## Expansion Planning (`expansion/`)

**Focus:** Multi-LGA expansion strategy and council acquisition.

### Documents

1. **`multi-lga-expansion-plan.md`**
   - Previous LGA expansion planning
   - Council prioritization criteria
   - Onboarding process (before automation)

2. **`council-sales-playbook.md`**
   - Council acquisition strategy
   - Partnership models
   - White-label co-pilot offering ($10k/month)

---

## Navigation

**Master Index:** See `.claude/LGA_ONBOARDING_INDEX.md` for complete cross-referenced navigation of all plans, strategic docs, and technical documentation.

**Quick Access:**
```bash
# View all plans
ls -R plans/

# LGA onboarding plans
ls plans/lga-onboarding/

# Strategic documents
ls plans/strategic/

# Expansion plans
ls plans/expansion/
```

---

## Document Lifecycle

**Active Plans:**
- Located in this directory
- Regularly updated as implementation progresses
- Version controlled in git

**Completed Plans:**
- Archived in `plans/archive/` (create as needed)
- Kept for reference and post-mortem analysis

**User-Specific Plans:**
- Personal planning documents at `C:\Users\lawre\.claude\plans\`
- Not tracked in git (user-specific location)

---

**Last Updated:** 2026-02-13
**Status:** Reorganized to project root for better visibility and accessibility
