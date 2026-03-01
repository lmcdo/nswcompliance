# Feasibility Intelligence Roadmap

**Status:** Planning Phase  
**Priority:** Strategic Evaluation (vs Heritage Intelligence & Capacity Calculator)  
**Timeline:** 3 months (12 weeks)  
**Origin:** External strategic analysis (ChatGPT conversation, January 2026)

---

## Executive Summary

**What:** DA/CDC approval analytics system that predicts development feasibility before design stage  
**Positioning:** "Early feasibility intelligence" (pre-design decision filtering)  
**Differentiation:** Competes upstream of Archistar (late-stage compliance checking)  
**Data Foundation:** Existing DA/CDC database with approval history ready to import

---

## Strategic Context

### How This Fits with Vision V2

**Vision V2 Core:** "Make every property instantly understandable through AI"

**Feasibility Intelligence = Pillar 1 Enhancement:**
- Adds temporal/behavioral layer to regulatory data
- Answers "What will actually get approved?" vs "What's permitted?"
- Uses historical DA/CDC approval patterns to predict outcomes

### Relationship to Existing Roadmap Features

| Feature | Strategic Value | Relationship |
|---------|----------------|--------------|
| Heritage Intelligence | Highest priority | Complementary - heritage is risk factor |
| Capacity Calculator | 5-star user value | Complementary - capacity + feasibility = complete answer |
| Smart Filtering | Quick win | Prerequisite - feasibility needs filtered provisions |
| DA Checklist | Table stakes | Complementary - feasibility identifies pathway |

**Recommended Sequencing Options:**

**Option A: Feasibility First**
- Weeks 1-12: Build Feasibility Intelligence
- Week 13+: Add Heritage Intelligence
- Pros: Unique positioning, leverages existing data
- Cons: Defers documented #1 priority, longer to revenue

**Option B: Heritage First** (Existing Roadmap)
- Weeks 1-2: Heritage Intelligence MVP
- Weeks 3-4: Smart Filtering + Capacity Calculator
- Weeks 5-16: Feasibility (if validated)
- Pros: Follows strategy, faster revenue, lower risk
- Cons: Delays competitive positioning

**Option C: Hybrid** (Recommended)
- Week 1: Import DA/CDC data
- Weeks 2-4: Heritage Intelligence MVP
- Weeks 5-6: Smart Filtering + Capacity Calculator
- Weeks 7-12: Complete Feasibility Intelligence
- Pros: Both features, hedged bets
- Cons: Context switching, 12 weeks total

---

## 12-Week Implementation Plan

### Phase 1: Data Foundation (Weeks 1-2)

**Week 1: Import DA/CDC Data**
- Create development_applications table
- Import from existing database
- Validate data quality (>95% completeness)

Files:
- supabase/migrations/003_create_da_tables.sql
- scripts/import_existing_da_data.py

**Week 2: Analytics Aggregation**
- Create approval_behavior_stats table
- Compute metrics by LGA/zone/type
- Implement fallback for small samples

Files:
- supabase/migrations/004_create_stats_tables.sql
- scripts/compute_approval_stats.py

### Phase 2: Feasibility Engine (Weeks 3-5)

**Week 3: Core Scoring Logic**
- Rule-based calculator (NOT ML)
- Four components: approval likelihood (40%), time risk (30%), yield risk (20%), pathway (10%)
- Weighted scoring with adjustments

Files:
- lib/feasibility/scoring.ts
- lib/feasibility/types.ts

**Week 4: Comparable Matching**
- Similarity algorithm (zone, type, cost, recency)
- Return top 5-10 precedents

Files:
- lib/feasibility/comparables.ts

**Week 5: API Endpoints**
- GET /api/feasibility/stats
- POST /api/feasibility/calculate
- POST /api/feasibility/comparables
- POST /api/feasibility/report

### Phase 3: Frontend UI (Weeks 6-9)

**Week 6: Tab Structure**
- Add third tab to /assessment
- useFeasibility hook
- FeasibilityColors in design tokens

**Week 7: Score Components**
- FeasibilityScoreCard (circular gauge)
- RiskIndicators (time/yield/pathway)
- RecommendationPanel (actionable advice)

**Week 8: Comparables Display**
- Table of similar approved DAs
- Links to NSW Planning Portal

**Week 9: Main Component**
- Integrate all sub-components
- Loading states, error handling
- Generate Report button

### Phase 4: Reports (Weeks 10-11)

**Week 10: Report Template**
- Add feasibility sections to report config
- Generator methods for each section

**Week 11: Report Integration**
- Wire up Generate Report button
- Display in Recent Reports

### Phase 5: Testing (Week 12)

**Week 12: Integration & Polish**
- End-to-end tests (4 scenarios)
- Data quality validation
- UX polish (loading, errors, tooltips)
- Documentation

---

## Architecture

**Database:**
- Existing: regulatory_provisions (47,818), nsw_properties
- New: development_applications, approval_behavior_stats

**API:**
- Existing: /api/property, /api/provisions
- New: /api/feasibility/* (4 endpoints)

**Frontend:**
- 3 tabs: SEPP/LEP, DCP, Feasibility Intelligence
- 5 new components under components/feasibility/

**Data Flow:**
Address → Scout → Verify → Validate → Feasibility → Display → Report

---

## Success Metrics

**Data (Week 2):**
- 5000+ DA records
- 80%+ stats coverage
- 20+ samples per group

**Performance (Week 12):**
- Feasibility calc: <2s
- Comparables: <3s
- API P95: <3s

**Quality (Week 12):**
- Validated for 10 properties
- 80%+ comparable relevance

---

## MVP Scope

**In Scope:**
- DA/CDC data import
- Approval stats by LGA/zone/type
- Rule-based scoring
- Comparable matching
- Pathway recommendations
- Time/yield risk indicators
- UI tab and report

**Out of Scope (Phase 2):**
- Machine learning models
- Real-time NSW Portal updates
- Map visualization
- Plan ingestion
- Expansion beyond Inner West

---

## Open Questions

1. Connection string for existing DA/CDC database?
2. How many records in current database?
3. Date range of data?
4. Known data quality issues?
5. PDF or HTML reports for MVP?
6. Strategic choice: Option A, B, or C?

---

## References

**External:**
- ChatGPT strategic analysis (January 2026)
- Competitive positioning vs Archistar
- NSW approval rate analysis (90%+ approval but high time/yield risk)

**Internal:**
- VISION_MISSION_STRATEGY_V2.md
- STRATEGIC_FEATURE_ANALYSIS_PROFESSIONAL_VALUE.md
- NEXT_FEATURES_IMPLEMENTATION_PLAN.md
- GROWTH_STRATEGIES_COMPARISON.md

**Last Updated:** January 11, 2026  
**Status:** Pending Strategic Decision
