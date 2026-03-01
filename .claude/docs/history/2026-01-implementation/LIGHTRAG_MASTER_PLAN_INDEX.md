# LightRAG Implementation - Master Plan Index
**Date:** 2025-10-23
**Purpose:** Central index of all LightRAG planning documentation

---

## Overview

This index connects all LightRAG planning documents created on 2025-10-23 to guide implementation of AI-assisted provision categorization for the NSW Planning Compliance Engine.

---

## The Core Problem

**Current State:**
- User searches address → Returns 241+ raw DCP provisions
- Hard to find relevant requirements (setbacks, parking, landscaping, etc.)
- Client can't quickly assess compliance

**Proposed Solution:**
- Pre-process provisions with LightRAG
- Categorize into structured requirements (15-20 per address)
- Display categorized requirements instead of 241 raw provisions
- Maintain full traceability to source provisions

---

## Documentation Structure

### 1. Foundation & Context
**[DATABASE_AND_LIGHTRAG_REALITY_CHECK.md](./DATABASE_AND_LIGHTRAG_REALITY_CHECK.md)**
- Current database state analysis
- Why 241 provisions are shown (86% unclassified)
- LightRAG capabilities and limitations
- Strategy options (A, B, C)
- Decision matrix
- **Key Finding:** Database has provisions but lacks metadata for filtering

---

### 2. Integration Architecture
**[LIGHTRAG_INTEGRATION_WITH_CURRENT_UI.md](./LIGHTRAG_INTEGRATION_WITH_CURRENT_UI.md)**
- How LightRAG fits into existing UI/UX
- Current pipeline (Planning API → Database → UI cards)
- Where LightRAG processes provisions (offline pre-processing)
- Database schema for categorized requirements
- UI component updates
- Regulatory hierarchy display (SEPP → LEP → DCP → Precinct)
- Cost analysis ($10.82 one-time)
- **Key Insight:** Minimal changes to existing pipeline - just swap raw provisions for categorized requirements

**Read this first to understand the integration approach.**

---

### 3. Reliability & Validation
**[LIGHTRAG_RELIABILITY_AND_VALIDATION.md](./LIGHTRAG_RELIABILITY_AND_VALIDATION.md)**
- How to ensure LLM output is compliance-safe
- Provenance tracking (requirement → source provision → PDF page)
- Confidence levels (High/Medium/Low)
- Conditional/exception detection
- Validation workflow (automated → expert review → production)
- Client verification interface
- Handling complex cases (tables, conditionals, cross-references)
- **Key Principle:** Full traceability + expert validation = compliance-safe

**Read this to understand how to make LLM output trustworthy.**

---

### 4. Categorization Quality Assurance
**[LIGHTRAG_CATEGORIZATION_VALIDATION.md](./LIGHTRAG_CATEGORIZATION_VALIDATION.md)**
- How to verify completeness (recall): Did we find ALL setback provisions?
- How to verify precision: Are categorized provisions actually about setbacks?
- Keyword cross-check (find missing provisions)
- Reverse keyword check (find false positives)
- Coverage matrix (visual validation)
- Expert sampling (statistical validation)
- Acceptance criteria (>90% recall, >95% precision)
- Validation dashboard
- **Key Metrics:** Recall, Precision, F1 Score for each category

**Read this to understand how to validate categorization quality.**

---

## Implementation Phases

### Phase 1: Foundation (Week 1)
**Goal:** Establish processing pipeline and validation framework

**Tasks:**
1. Set up LightRAG processing environment
2. Create database schema:
   - `dcp_base_requirements` (generic base requirements)
   - `dcp_precinct_requirements` (precinct supplements)
   - `categorization_validation` (validation tracking)
3. Implement validation queries:
   - Keyword cross-check
   - Reverse keyword check
   - Coverage analysis
4. Build validation dashboard UI

**Deliverables:**
- Database tables created
- Validation queries tested
- Dashboard prototype

---

### Phase 2: Processing & Validation (Week 2)
**Goal:** Process provisions and validate categorization

**Tasks:**
1. Process DCP base provisions:
   - Extract ~100 (LGA, Zone, DevType) combinations
   - Run LightRAG categorization
   - Store in `dcp_base_requirements`
   - **Cost:** ~$10
2. Process DCP precinct provisions:
   - Extract 41 precincts (Marrickville)
   - Run LightRAG categorization
   - Store in `dcp_precinct_requirements`
   - **Cost:** ~$0.75
3. Run automated validation:
   - Keyword cross-checks
   - Calculate recall/precision metrics
   - Flag provisions for review
4. Expert review:
   - Review ALL flagged provisions (~50-100)
   - Validate high-confidence samples (10-20%)
   - Correct false positives/negatives
   - Mark validated requirements

**Deliverables:**
- All provisions processed
- Validation metrics meet thresholds (>90% recall, >95% precision)
- Requirements marked as validated

---

### Phase 3: API & UI Integration (Week 3)
**Goal:** Integrate categorized requirements into production UI

**Tasks:**
1. Update API endpoint `/api/compliance/constraints`:
   - Query `dcp_base_requirements` table
   - Query `dcp_precinct_requirements` table (if address in precinct)
   - Merge and return categorized requirements
   - Maintain link to raw provisions
2. Update UI component `ComplianceDashboard.tsx`:
   - Display categorized requirements grouped by category
   - Show source provision links
   - Collapse raw provisions browser by default
   - Add validation status badges
3. Testing:
   - Test with 20+ different addresses
   - Verify all categories display correctly
   - Verify source links work
   - Verify PDF page viewer works

**Deliverables:**
- API returns categorized requirements
- UI displays requirements cleanly
- Source traceability works
- Beta testing complete

---

### Phase 4: Production Rollout (Week 4)
**Goal:** Deploy to production with monitoring

**Tasks:**
1. Production deployment:
   - Enable feature flag for categorized requirements
   - Monitor user feedback
   - Track which requirements are clicked/viewed
2. Ongoing validation:
   - Continue expert review of medium/low confidence items
   - Track false positive/negative reports
   - Refine categorization as needed
3. Documentation:
   - User guide for categorized requirements
   - Admin guide for validation workflow
   - API documentation update

**Deliverables:**
- Feature live in production
- Monitoring dashboard
- User documentation

---

## Quick Reference

### Key Costs
```
One-Time Processing:
├─ DCP Base: 100 combos × $0.10 = $10.00
├─ DCP Precinct: 41 precincts × $0.02 = $0.82
└─ Total: $10.82

Runtime (Per Address):
├─ Database query: $0
├─ Response time: <100ms
└─ Total: $0 per search
```

### Key Metrics
```
Before:
├─ Provisions displayed: 241-289
├─ User effort: Browse 241 items, use filters
└─ Categorization: Manual by user

After:
├─ Requirements displayed: 18-28 (92% reduction)
├─ User effort: Review categorized list
└─ Categorization: Pre-processed, validated
```

### Quality Thresholds
```
Category          | Min Recall | Min Precision | F1 Score
------------------|-----------|---------------|----------
Setback           | 90%       | 95%           | 92%
Parking           | 90%       | 95%           | 92%
Landscaping       | 85%       | 90%           | 87%
Building Design   | 80%       | 85%           | 82%
```

---

## Database Schema Overview

### Core Tables

```sql
-- Base requirements (constant per LGA/Zone/DevType)
CREATE TABLE dcp_base_requirements (
  id SERIAL PRIMARY KEY,
  lga TEXT,
  zone TEXT,
  dev_type TEXT,
  category TEXT,                    -- 'setback_front', 'parking', etc.
  requirement_text TEXT,
  value_numeric NUMERIC,
  unit TEXT,
  source_provision_ids INTEGER[],   -- Links to regulatory_provisions
  confidence TEXT,                  -- 'high', 'medium', 'low'
  validated BOOLEAN,
  validated_by TEXT,
  validated_at TIMESTAMP
);

-- Precinct supplements (varies by address)
CREATE TABLE dcp_precinct_requirements (
  id SERIAL PRIMARY KEY,
  precinct_id TEXT,
  lga TEXT,
  category TEXT,
  requirement_text TEXT,
  value_numeric NUMERIC,
  unit TEXT,
  source_provision_ids INTEGER[],
  confidence TEXT,
  validated BOOLEAN
);

-- Validation tracking
CREATE TABLE categorization_validation (
  id SERIAL PRIMARY KEY,
  provision_id INTEGER,
  llm_category TEXT,
  expert_category TEXT,
  validation_status TEXT,           -- 'correct', 'false_negative', etc.
  expert_notes TEXT,
  expert_reviewed_by TEXT,
  expert_reviewed_at TIMESTAMP
);
```

---

## API Response Format

### Current (Raw Provisions)
```json
{
  "lep": { "height": 9.5, "fsr": 0.6 },
  "sepp": { "water": "40%" },
  "dcp": {
    "provisions": [
      { "text": "The minimum setback..." },
      { "text": "Parking spaces shall..." },
      // ... 239 more provisions
    ]
  }
}
```

### After LightRAG (Categorized Requirements)
```json
{
  "lep": { "height": 9.5, "fsr": 0.6 },
  "sepp": { "water": "40%" },
  "dcp_base": [
    {
      "category": "setback_front",
      "text": "Front setback: 5.5m",
      "value": 5.5,
      "unit": "m",
      "source_provisions": [12345, 12346],
      "confidence": "high",
      "validated": true
    },
    {
      "category": "parking",
      "text": "Dwelling house: 1 space minimum",
      "value": 1,
      "unit": "spaces",
      "source_provisions": [23456],
      "confidence": "high",
      "validated": true
    }
    // ... 16 more requirements (not 241 provisions!)
  ],
  "dcp_precinct": [
    {
      "category": "character",
      "text": "Maintain low-density residential character",
      "source_provisions": [55],
      "confidence": "high"
    }
    // ... 3-8 more precinct-specific requirements
  ],
  "raw_provisions_link": "/api/dcp/provisions?lga=Marrickville&zone=R2&devType=dwelling_house"
}
```

---

## UI Component Hierarchy

```
ComplianceDashboard
├─ 🟥 SEPP Card (from Planning API)
├─ 🟦 LEP Card (from Planning API)
├─ 🟢 DCP Card (NEW: categorized requirements)
│  ├─ Category: Setbacks
│  │  ├─ Front: 5.5m [View Source]
│  │  ├─ Side: 0.9m [View Source]
│  │  └─ Rear: 6m [View Source]
│  ├─ Category: Landscaping
│  │  └─ Front: 40% [View Source]
│  ├─ Category: Parking
│  │  └─ 1 space minimum [View Source]
│  └─ [Collapse] View Raw Provisions (241)
│     └─ DCPProvisionsBrowser (existing component)
├─ 📍 Precinct Card (NEW: precinct supplements)
│  ├─ Character: Low-density residential
│  └─ [Collapse] View Raw Provisions (3)
│     └─ PrecinctProvisionsBrowser (existing component)
└─ 🅿️ Parking Card (existing)
```

---

## Validation Workflow Diagram

```
┌─────────────────────────────────────┐
│ LightRAG Processing (Offline)       │
│ Input: 241 provisions               │
│ Output: 65 requirements             │
│ Confidence: High(45), Med(15), Low(5)│
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│ Automated Validation                │
│ - Keyword cross-check               │
│ - Reverse keyword check             │
│ - Coverage analysis                 │
│ Output: 20 flagged for review       │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│ Expert Review                       │
│ - Review 20 flagged provisions      │
│ - Spot-check 10% of high-confidence │
│ - Mark validated or correct         │
│ Output: All requirements validated  │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│ Production Query                    │
│ SELECT * WHERE validated = true     │
│ Returns: 18 validated requirements  │
│ Fallback: Raw provisions if <5      │
└─────────────────────────────────────┘
```

---

## Critical Compliance Safeguards

### 1. Full Traceability
- Every requirement links to source provision(s)
- Every provision links to PDF page
- Client can verify in 2 clicks

### 2. Confidence Indicators
- HIGH (>90%): Show by default
- MEDIUM (70-90%): Show with warning
- LOW (<70%): Don't show - link to raw provision

### 3. Conditional Flagging
- Detect "except", "however", "unless", "where"
- Flag as MEDIUM confidence automatically
- Display conditions clearly

### 4. Expert Validation Required
- Don't show unvalidated medium/low confidence
- Require human review before production
- Track who validated what and when

### 5. Conservative Fallback
- If <5 validated requirements → show raw provisions
- If uncertain → show raw provisions
- When in doubt → be transparent, not clever

---

## Related Documentation

### Existing LightRAG Docs
- `LIGHTRAG_EXPLAINED.md` - Technical overview of LightRAG
- `LIGHTRAG_DEPLOYMENT_STRATEGY.md` - Deployment considerations
- `TEST_LIGHTRAG_CAPABILITIES.md` - Testing approach

### Related System Docs
- `REGULATORY_HIERARCHY_UX_DESIGN.md` - SEPP/LEP/DCP display hierarchy
- `REGULATORY_HIERARCHY_IMPLEMENTATION.md` - How to enforce precedence
- `PRECINCT_ARCHITECTURE.md` - Precinct provisions architecture

---

## Next Steps

### Immediate (This Week)
1. ✅ Review all LightRAG planning documents
2. ⬜ Approve processing approach (Option B: Base + Precinct)
3. ⬜ Set up database schema
4. ⬜ Build validation dashboard
5. ⬜ Process first test batch (Marrickville R2 Dwelling House)

### Week 2
6. ⬜ Process all 100 combinations
7. ⬜ Run validation suite
8. ⬜ Expert review session
9. ⬜ Validate metrics meet thresholds

### Week 3
10. ⬜ Integrate into API
11. ⬜ Update UI components
12. ⬜ Beta testing

### Week 4
13. ⬜ Production rollout
14. ⬜ Monitoring
15. ⬜ User documentation

---

## Questions & Decisions Log

### Decided
- ✅ Use LightRAG for categorization (not real-time LLM calls)
- ✅ Pre-process provisions offline ($10.82 one-time cost)
- ✅ Require expert validation before production
- ✅ Maintain full traceability to source provisions
- ✅ Use Option B: Process base + precinct separately

### Pending
- ⬜ Which LGA to start with? (Recommend: Marrickville - has most data)
- ⬜ Who will do expert validation? (Need planning expert)
- ⬜ Acceptance thresholds final? (Currently: 90% recall, 95% precision)
- ⬜ Timeline approval? (Proposed: 4 weeks)

---

## Key Contacts & Roles

### Required for Implementation
- **Developer:** API/database integration, validation dashboard
- **Planning Expert:** Provision review, validation, quality assurance
- **QA Tester:** Beta testing, user acceptance testing
- **Product Owner:** Approve approach, timeline, acceptance criteria

---

## Success Criteria

### Technical
- ✅ All provisions processed and categorized
- ✅ Validation metrics meet thresholds (>90% recall, >95% precision)
- ✅ API returns categorized requirements in <100ms
- ✅ Full traceability to source provisions maintained
- ✅ Fallback to raw provisions works

### User Experience
- ✅ 92% reduction in provisions displayed (241 → 18)
- ✅ Requirements grouped by clear categories
- ✅ Source verification available in 2 clicks
- ✅ Positive user feedback from beta testers

### Compliance
- ✅ Every requirement traceable to source
- ✅ Expert validated all production requirements
- ✅ Confidence levels clearly indicated
- ✅ Conditionals/exceptions flagged
- ✅ Audit trail complete

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-23 | Claude | Initial master plan index |

---

**This index is the single source of truth for LightRAG implementation planning. All referenced documents should be read in order for complete understanding.**
