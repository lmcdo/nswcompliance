# Provision-Based Architecture - Index

**READ THIS FIRST** when working on provision extraction, compliance API, or filtering.

---

## The Architecture in One Diagram (4-Layer Model)

```
USER ENTERS ADDRESS
        │
        ▼
┌─────────────────────────────────┐
│  PLANNING PORTAL API            │  ← Automatic
│  Returns: zone, heritage,       │
│  flood, bushfire, FSR, height   │
│  (SEPP/LEP data = values here)  │
└─────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────┐
│  DCP 4-LAYER FILTERING          │  ← Based on Portal data
│                                 │
│  Layer 1: Generic (Part 2)      │  ALWAYS include
│  Layer 2: Use (Part 4)          │  Zone-filtered
│  Layer 3: Condition (Part 8)    │  Heritage/flood filtered
│  Layer 4: Precinct (Part 9)     │  Location-filtered
│                                 │
│  ~5,500 DCP → ~350-400          │
└─────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────┐
│  USER SELECTION                 │  ← Dropdowns
│  Dev type + Assessment type     │
│  ~400 → ~50-90 provisions       │
└─────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────┐
│  DISPLAY                        │
│  Original text + metadata       │
│  Grouped by TOPIC               │
└─────────────────────────────────┘
```

**Note:** SEPP/LEP numeric values (FSR, height, etc.) come from Planning Portal API directly. DCP provisions are the focus of this pipeline.

---

## Key Decisions (DO NOT RE-DEBATE)

1. **Planning Portal drives filtering** - It's the first step, not an afterthought
2. **Provision IS the requirement** - Display original text, not LLM summary
3. **v2_ column prefix** - New enrichment columns on `regulatory_provisions`
4. **Dropdown for dev type** - Hierarchical, not free text
5. **Keyword search** - Within filtered results, not semantic
6. **Site condition filtering** - heritage/flood/bushfire provisions only show when property has that condition
7. **Parallel build** - New code alongside old, feature flags for cutover
8. **DCP provisions only** - SEPP/LEP values come from Planning Portal, not provision display
9. **4-Layer Model** (from web research 2025-11-23):
   - Layer 1 (Generic): Part 2/Section 1 - ALWAYS apply regardless of zone
   - Layer 2 (Use-specific): Part 4/Section 3 - Zone-filtered
   - Layer 3 (Condition): Part 8/heritage - If site has condition
   - Layer 4 (Precinct): Part 9/Section 2 - Location-filtered

---

## Implementation State

**Current Phase:** COMPLETE - Ready for deployment

### ✅ DEV-TYPE ENRICHMENT COMPLETE (2025-11-24)

All 13 dev_types now have adequate CDC provision coverage:
- Residential: 277-307 provisions each
- Commercial: 99-122 provisions each
- Industrial: 109-117 provisions each
- Special use: 40-277 provisions each

**Fix Scripts:** `scripts/fixes/DQ7_*.py`

### SESSION PROGRESS (2025-11-23)

| Phase | Status | Result |
|-------|--------|--------|
| Precinct tagging | ✅ COMPLETE | 42% → **94.3%** (all parts >80%) |
| 4-Layer API | ✅ COMPLETE | `/api/provisions/for-property` working |
| New UI | ✅ COMPLETE | `ProvisionsByTopic.tsx` + toggle on `/assessment` |
| Granular dev-types | ✅ COMPLETE | All 13 dev_types have 40-307 CDC provisions |
| Assessment type | ✅ COMPLETE | CDC filter working |
| **Dev-type enrichment** | ✅ COMPLETE | All dev_types meet thresholds |

### COMPLETED

| Step | Status | Notes |
|------|--------|-------|
| Strategy document | ✅ COMPLETE | 8 parts, updated for 4-layer model |
| Feature branch | ✅ COMPLETE | `feature/provision-based-architecture` |
| Database backup | ✅ COMPLETE | `backups/regulatory_provisions_before_v2_20251122_231205.json` |
| Schema migration | ✅ COMPLETE | 16 v2_ columns + 9 indexes added |
| Actionable classification | ✅ COMPLETE | 11,835 actionable / 36,539 boilerplate |
| Numeric extraction | ✅ COMPLETE | 451 provisions with numeric values |
| Site condition tagging | ✅ COMPLETE | Heritage fixed: 1,926 total (was 1,372) |
| Type classification | ✅ COMPLETE | control/objective/definition/note/procedural |
| Applicability tagging | ✅ COMPLETE | DCP-aware configs for 3 councils |
| DCP analysis | ✅ COMPLETE | `DCP_PHILOSOPHICAL_DIFFERENCES.md` |
| Web research | ✅ COMPLETE | Professional workflows for all 3 councils |
| 4-Layer model | ✅ COMPLETE | Generic → Use → Condition → Precinct |
| Strategy doc update | ✅ COMPLETE | Parts 1,2,4,5,7 updated for 4-layer |
| **Layer + Topic tagging** | ✅ COMPLETE | v2_dcp_layer, v2_dcp_part, v2_topic populated (DQ-2 fix: 14,501 topics corrected) |
| **Marker extraction** | ✅ COMPLETE | Leichhardt: 917 C markers, Ashfield: 91 PC/DS/C/O |
| **Precinct tagging** | ✅ COMPLETE | 1,146/1,215 (94.3%) - All parts >80% |
| **New API** | ✅ COMPLETE | `/api/provisions/for-property` with 4-layer query |

### ALL STEPS COMPLETE

| Step | Status | Purpose | Impact |
|------|--------|---------|--------|
| **1. New UI** | ✅ COMPLETE | Provision display grouped by TOPIC | ProvisionsByTopic.tsx + toggle on /assessment |
| **2. Granular dev-types** | ✅ COMPLETE | Hierarchical filter with dropdown | 1048 → 600 (dwelling) → 177 (secondary) |
| **3. Assessment type support** | ✅ COMPLETE | CDC = quantitative only | 600 → **46** provisions |

### Key Files

| File | Purpose |
|------|---------|
| `frontend-nextjs/app/api/provisions/for-property/route.ts` | 4-layer API endpoint |
| `frontend-nextjs/components/compliance/ProvisionsByTopic.tsx` | **NEW: Topic-grouped UI** |
| `frontend-nextjs/app/assessment/page.tsx` | Assessment page with view toggle |
| `test_4layer_api.py` | Test 4-layer filtering logic |
| `verify_precinct_tagging.py` | Check current tagging state |
| `fix_chapter_d_pages.py` | Chapter D precinct mapping via MinerU JSON |
| `fix_part_g_pages.py` | Part G precinct mapping via MinerU JSON |

### Step 1 Detail: Layer + Topic Tagging (4-Layer Model)

All three councils share the same 4-layer architecture despite surface differences:

**MARRICKVILLE** - Topic-based generic + zone-specific + precinct-specific
- **How professionals use it:** Check Part 2 (ALL topics) + Part 4 (zone) + Part 9 (precinct)
- **Multiple parts apply per property:**
  - Part 2: Generic Provisions (topic-based) - applies to ALL
    - 2.6 Privacy, 2.7 Solar, 2.10 Parking, 2.18 Landscaping, etc.
  - Part 4: Residential (zone-based) - 4.1 Low Density (R2), 4.2 Multi-dwelling (R3/R4)
  - Part 8: Heritage (IF heritage item or in HCA)
  - Part 9: Planning Precincts (47 precincts with character statements)
- **Similar to Leichhardt:** Part 2 = topic controls, Part 4 = use controls, Part 9 = location controls
- **Filtering approach:** LGA → Part 2 (ALL) → Part 4 (zone) → Part 8 (if heritage) → Part 9 (precinct)

**LEICHHARDT** - Merit-based, topic-organized, multi-section
- **How professionals use it:** Navigate by TOPIC across multiple sections
- **Multiple sections apply per property:**
  - Part C Section 1: General Provisions (C1-C55 topic controls) - ALL dev
  - Part C Section 3: Residential Provisions (setbacks, height, solar) - residential
  - Part C Section 2: Urban Character (IF in Distinctive Neighbourhood)
- **Merit-based assessment:** Show objectives first, controls as "acceptable solutions"
- **C markers ARE topic identifiers:** C1=site analysis, C2=heritage, C15=parking rates
- **Filtering approach:** LGA → Zone → Neighbourhood → Topic → Dev type

**ASHFIELD** - Performance Criteria / Design Solutions format
- Most provisions (83%) are NARRATIVE, not controls
- Only ~260 are checkable requirements:
  - DS (Design Solutions): 29 - quantitative controls
  - PC (Performance Criteria): 134 - objectives
  - C/O markers: 99 - additional controls
- Tag by marker type, NOT keyword filtering

| Ashfield Marker | Count | Display Behavior |
|-----------------|-------|------------------|
| DS (Design Solutions) | 29 | Always show for CDC |
| PC (Performance Criteria) | 134 | Show for DA, cite for variations |
| C/O controls | 99 | Show for DA |
| Unmarked (narrative) | 1,264 | Collapsed "Context" section |

### Current DCP Provision Counts (After Filtering)

For **non-heritage** property:

| Council | Total | After Heritage | Target | Gap |
|---------|-------|----------------|--------|-----|
| Marrickville | 1,051 | 406 | ~50 | Need precinct + zone + dev-type |
| Ashfield | 1,526 | 596 | ~50 | Need precinct + categories |
| Leichhardt | 2,989 | 2,780 | ~50 | **Need topic tagging + section filtering** |

### Critical Insight: Leichhardt Professional Workflow

**How professionals actually use Leichhardt DCP** (from web research):

1. **Identify applicable sections** for the dev type:
   - Section 1 (General) applies to ALL
   - Section 3 (Residential) applies to residential
   - Section 2 (Neighbourhoods) if property in one

2. **Navigate by TOPIC** across sections:
   | Topic | Where to Find |
   |-------|---------------|
   | Setbacks | Section 3 + Section 1 C markers |
   | Height/Envelope | Section 3 (2.4m, 3.6m, 6.0m, 7.2m) |
   | Solar Access | Section 3 (3hrs min to 50% open space) |
   | Privacy | Section 3 + Section 1 |
   | Parking | Section 1: C3, C14, C15, C18-C21, C43-C55 |
   | Heritage | Section 1: C2, C37 |
   | Landscaping | Section 1: C6, C9-C11, C23, C26 |

3. **Demonstrate merit** - objectives first, controls as solutions

**Part C Section 1 marker distribution** (1,782 provisions total):
- 504 WITH C markers (C1-C55) - topic-grouped controls
- 1,278 WITHOUT markers - Tables, Figures, Objectives (O1, O2), narrative

**Implementation approach:**
- Tag by TOPIC (setbacks, parking, solar, height, privacy, heritage, landscaping)
- Tag by SECTION (Section 1, Section 2, Section 3)
- Extract C markers as category identifiers
- Group objectives with their related controls

---

## Completion Details by Phase

### Phase 1-4 (2025-11-22)
- Schema, actionable, numeric, site condition, type classification
- See `enrichment/pipeline.py` for all phases

### Phase 5 (2025-11-22, revised 2025-11-23)
- DCP-aware config files: `enrichment/config/`
- Heritage tagging fixed: 554 provisions updated via document structure
- Precinct coverage analysis:
  - Marrickville: 48 precincts = 100% coverage (SELECTOR)
  - Leichhardt: 23+ neighbourhoods = 100% coverage (SELECTOR)
  - Ashfield: 17 precincts = partial coverage (FILTER)

---

## Filter Cascade (Per Strategy)

```
DCP Provisions for Inner West: ~5,500
        │
        ▼ LGA filter (user's council)
    ~2,000
        │
        ▼ Zone filter (R2)
    ~800
        │
        ▼ Heritage = false
    ~750
        │
        ▼ Precinct selection (user's precinct only)
    ~200
        │
        ▼ Dev type (dwelling_addition_rear)
    ~90
        │
        ▼ Assessment type (CDC = quantitative)
    ~50

TARGET: ~50 provisions
```

---

## Quick Reference

### Planning Portal → Database Query

| Portal Returns | Filter Logic |
|----------------|--------------|
| `zone: "R2"` | `WHERE 'R2' = ANY(v2_applicable_zones)` |
| `heritage: false` | `WHERE v2_site_condition_required != 'heritage'` |
| `floodProne: false` | `WHERE v2_site_condition_required != 'flood'` |
| `bushfireProne: false` | `WHERE v2_site_condition_required != 'bushfire'` |
| `precinct: "X"` | `WHERE v2_scope = 'general' OR v2_precinct_id = 'X'` |

### User Selection → Database Query

| User Selects | Filter Logic |
|--------------|--------------|
| Dev type: `rear_addition` | `WHERE 'rear_addition' = ANY(v2_applicable_dev_types)` |
| Assessment: `CDC` | `WHERE v2_provision_type = 'control' AND v2_has_numeric_value = true` |

### File Locations

| Purpose | Location |
|---------|----------|
| Enrichment pipeline | `enrichment/pipeline.py` |
| DCP configs | `enrichment/config/` (ashfield, leichhardt, marrickville) |
| Extractors | `enrichment/extractors/` |
| DCP analysis | `DCP_PHILOSOPHICAL_DIFFERENCES.md` |
| New API | `frontend-nextjs/app/api/provisions/for-property/route.ts` |
| New UI | `frontend-nextjs/components/compliance/ProvisionsByTopic.tsx` |
| DQ Fix Scripts | `scripts/fixes/DQ*.py` |

---

## MANDATORY: Update This Section After Each Phase

**CLAUDE MUST** update the Implementation State table above after completing any phase.
This ensures continuity across sessions and prevents duplicate work.

---

## Session Log

### 2025-11-24: DQ-7 Dev-Type Enrichment Complete
- **DQ-1**: Resolved - Not a bug (precinct 12_ has qualitative-only provisions)
- **DQ-2**: Fixed - 14,501 topics corrected via position-based matching
- **DQ-3**: Fixed - 9 TOC entries marked non-actionable
- **DQ-4**: Accepted - O markers design limitation
- **DQ-5**: Accepted - 78% generic expected for DCP structure
- **DQ-6**: Accepted - 2% duplicates are SEPP boilerplate
- **DQ-7**: Fixed - All 13 dev_types now have 40-307 CDC provisions
  - Scripts: `DQ7_devtype_enrichment.py`, `DQ7_commercial_industrial_enrichment.py`, `DQ7_remaining_devtypes.py`

**STATUS: READY FOR DEPLOYMENT**
- All data quality issues resolved
- Professional scenario testing passed for CDC workflows
- Zone handling: 'ALL' = wildcard (correct for Leichhardt/Ashfield structure)
- Next: `python scripts/sync_v2_to_supabase.py` then deploy

---

*Last updated: 2025-11-24 (DQ-7 dev-type enrichment complete - all 13 dev_types now have adequate coverage)*
