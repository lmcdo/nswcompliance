# Dev-Type Enrichment Implementation Plan

**Created:** 2025-11-24
**Status:** REQUIRED - Blocks production readiness
**Context:** Testing revealed only `dwelling_house` has adequate dev_type coverage

---

## The Problem

The INDEX.md claims "Granular dev-types ✅ COMPLETE" but actual testing shows:

| Dev Type | CDC Provisions | Status |
|----------|----------------|--------|
| dwelling_house | 34 | **OK** |
| secondary_dwelling | 8 | INADEQUATE |
| dual_occupancy | 10 | INADEQUATE |
| multi_dwelling_housing | 10 | INADEQUATE |
| residential_flat_building | 10 | INADEQUATE |
| retail_premises | 11 | INADEQUATE |
| commercial_premises | 0 | MISSING |
| office_premises | 0 | MISSING |
| industrial_development | 6 | INADEQUATE |
| warehouse | 4 | INADEQUATE |
| boarding_house | 9 | INADEQUATE |
| child_care_centre | 1 | MISSING |
| shop_top_housing | 10 | INADEQUATE |

**Root Cause:** 286 provisions tagged with `['ALL']` instead of specific dev_types. The API excludes 'ALL' to prevent result inflation, leaving most dev_types underserved.

---

## Relationship to Original Strategy

From INDEX.md architecture:
```
USER SELECTION ← Dropdowns
Dev type + Assessment type
~400 → ~50-90 provisions
```

**Expected:** Dev_type filter reduces ~400 to ~50-90 for ANY dev type
**Actual:** Only works for dwelling_house (354→34). Others get 0-11.

---

## Implementation Plan

### Phase 1: Audit & Analysis (This Session)
- [x] Identify scope: 12 of 13 dev_types inadequate
- [x] Root cause: 'ALL' tag used instead of specific types
- [x] Document in tracker

### Phase 2: Provision-DevType Mapping Rules
Create mapping logic for each provision source:

**SEPP/LEP Provisions (267 with 'ALL'):**
- State-level controls apply to ALL dev types legitimately
- These SHOULD use 'ALL' - need API to handle correctly

**DCP Provisions (53 with 'ALL'):**
- Council-specific controls should map to specific dev types
- Re-tag based on DCP section/chapter:
  - Part 4.1 Low Density → dwelling_house, secondary_dwelling, dual_occupancy
  - Part 4.2 Multi-dwelling → multi_dwelling_housing, residential_flat_building
  - Part 5 Commercial → retail_premises, commercial_premises, office_premises
  - Part 6 Industrial → industrial_development, warehouse

### Phase 3: Re-Enrichment Script
```python
# Pseudo-code for enrichment
for provision in dcp_provisions:
    if 'Part 4.1' in document_id or 'Low_Density' in document_id:
        add_dev_types(['dwelling_house', 'secondary_dwelling', 'dual_occupancy'])
    elif 'Part 4.2' in document_id or 'Multi_Dwelling' in document_id:
        add_dev_types(['multi_dwelling_housing', 'residential_flat_building'])
    # etc.
```

### Phase 4: API Enhancement
Two approaches:

**Option A: Smart 'ALL' handling**
```sql
WHERE (v2_applicable_dev_types && $1::text[]
       OR ('ALL' = ANY(v2_applicable_dev_types)
           AND source_type IN ('SEPP', 'LEP')))
```

**Option B: Expand 'ALL' in data**
Replace `['ALL']` with explicit list of all applicable dev_types in the database.

### Phase 5: Verification Testing
Re-run professional scenario tests. Target: 30-60 CDC provisions per dev_type.

---

## Success Criteria

| Dev Type | Current | Target | Method |
|----------|---------|--------|--------|
| dwelling_house | 34 | 30-60 | Already OK |
| secondary_dwelling | 8 | 30-60 | Re-tag + API fix |
| dual_occupancy | 10 | 30-60 | Re-tag |
| multi_dwelling_housing | 10 | 30-60 | Re-tag |
| residential_flat_building | 10 | 30-60 | Re-tag |
| retail_premises | 11 | 30-60 | Re-tag |
| commercial_premises | 0 | 20-40 | Re-tag |
| office_premises | 0 | 20-40 | Re-tag |
| industrial_development | 6 | 20-40 | Re-tag |
| warehouse | 4 | 20-40 | Re-tag |
| boarding_house | 9 | 20-40 | Re-tag |
| child_care_centre | 1 | 10-30 | Re-tag |
| shop_top_housing | 10 | 30-60 | Re-tag |

---

## Claude Session Management

**For Next Session:**
1. Read this file first
2. Read INDEX.md for architecture context
3. Start with Phase 2 (mapping rules)
4. One dev_type category per atomic unit of work

**Atomic Work Units:**
1. Residential (dwelling_house family): 4 dev_types
2. Multi-unit (apartments): 2 dev_types
3. Commercial: 3 dev_types
4. Industrial: 2 dev_types
5. Special use: 2 dev_types (boarding, childcare)

---

## Files to Modify

| File | Change |
|------|--------|
| `enrichment/config/*.yaml` | Add dev_type mapping rules per DCP section |
| `enrichment/pipeline.py` | Add dev_type enrichment phase |
| `frontend-nextjs/.../route.ts` | Handle SEPP/LEP 'ALL' correctly |
| `.claude/prp/INDEX.md` | Update status to reflect true state |

---

*This plan ensures the original project goal (50-90 provisions per dev_type) is achievable.*
