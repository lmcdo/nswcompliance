# Intelligent Knowledgebase Project Postmortem

**Project:** NSW Property Development Compliance Engine
**Timeline:** Sep 6, 2025 → Dec 10, 2025 (~3 months)
**Purpose:** Extract lessons for content creation and future niche applications

---

## Executive Summary

Built an intelligent knowledgebase that filters 48,000 NSW planning provisions down to ~50 relevant ones per property address. The system integrates government APIs, PDF extraction, LLM enrichment, and multi-layer filtering.

**Key Metrics:**
- 395 commits over 3 months
- 169 fixes (43%) vs 108 features (27%)
- Fix:Feature ratio of 1.6:1
- 7 reverts
- 4 debug commits left in history (investigation traces)

---

## Part 1: Pain Point Analysis

### 1.1 Recurring Bug Patterns

#### Loading State Saga (10 commits for same conceptual problem)

```
fix: Show loading skeleton when DCP tab clicked
fix: Show visible loading spinner when DCP tab first clicked
fix: Show loading state in DCP tab by removing keepPreviousData
fix: DCP tab loading state and stale data on address change
fix: Add minimum 400ms loading time for visible spinner feedback
fix: Button loading state - explicit gray bg, fixed width, flexbox centering
fix: Use flushSync for immediate loading state render on first click
fix: Add 50ms delay after autocomplete select to let UI settle before loading
fix: Require explicit button click to analyze - remove auto-trigger on dropdown select
debug: Add timestamps to loading state logs
```

**Root causes identified:**
- SWR caching behavior vs user expectations
- Tab switching with async data
- Stale data on address change
- Race conditions between loading states
- React render batching hiding state changes
- Autocomplete selection triggering before UI ready

**Lesson:** Loading states multiply with async complexity. Each new async path (tabs, cache, autocomplete) creates new edge cases. Consider a loading state machine rather than boolean flags.

---

#### PDF Page Number Odyssey (13+ commits, multiple reverts, ongoing)

```
fix: Apply Leichhardt DCP page offsets for accurate page numbers
fix: Remove confusing page numbers from PDF viewer - use generic labels
fix: Correct Building Form display and PDF page numbers
fix: PDF button shows URL page number, not database field
fix: Correct Part C Section 2 offset to 112 (page 19 → DCP 131)
fix: Correct Part C Section 2 offset to 110 (page_19 shows DCP 129)
fix: Remove incorrect PDF page URL adjustment for Leichhardt
feat: Show DCP Part/Section in provision page headers
fix: Use part_number instead of part_name for DCP Part display
revert: Remove PDF page URL adjustment - causing wrong pages
```

**Three different "page number" concepts:**
1. `pdf_page`: Database field from extraction tool
2. `pdf_page_image_url`: Image filename with different page number
3. Display page: Actual PDF page user sees when they open document

**Each DCP document has different offset:**
- Leichhardt Part C Section 2: offset of 110-112 (changed twice)
- Each PDF split has its own offset
- MinerU extraction starts at 0, PDFs start at 1 or have front matter

**Lesson:** Normalize page number concepts immediately or accept perpetual maintenance. Create a single `canonical_page` field and calculate all others from it.

---

#### Council/Location Mapping (48+ commits)

```
fix: Handle multi-word suburbs in former council mapping
fix: Check suburb name before postcode for former council detection
fix: Add missing Summer Hill postcode 2130 to Ashfield mapping
fix: Add Dulwich Hill precinct mappings (2203 postcode)
Revert "fix: Add Dulwich Hill precinct mappings (2203 postcode)"
fix: Exclude non-heritage sections from heritage provisions query
```

**Root causes:**
- Merged councils (Inner West = Marrickville + Leichhardt + Ashfield)
- Postcodes span multiple former councils
- Multi-word suburb names break string matching
- Heritage sections in non-heritage parts of DCP

**Lesson:** Geographic/jurisdictional mapping has infinite edge cases. Build with geospatial lookup from start, not string matching.

---

### 1.2 The 20% File Problem

**ProvisionsByTopic.tsx: 76 commits (19% of all project commits)**

This single component handles:
- Topic grouping logic
- 4-layer filtering display
- Heritage sub-categorization (HCA grouping)
- PDF page linking and page headers
- Council-specific behavior variations
- Expand/collapse state management
- Element filtering (roof, fence, materials)
- Page grouping (provisions on same PDF page)
- DCP Part/Section display

**Recent additions that increased complexity:**
- PageGroupedProvisions integration (3 commits)
- DCP Part/Section headers (2 commits)

**Lesson:** Integration points absorb commits. Either split proactively or accept ~20% of work touches this file.

---

### 1.3 Investigation Patterns

**4 debug commits remain in history:**
```
debug: Add logging for precinct filter in provisions API
debug: Add timestamps to loading state logs
debug: Add console.log to track loading prop in PropertySearch
debug: Add detailed logging to trace Ashfield query path
```

**What they reveal:**
- Precinct filtering logic needed tracing
- Loading state timing issues required timestamps
- Component prop flow unclear
- Database query path for specific councils needed visibility

**Lesson:** Debug commits indicate architecture blind spots. If you need logging to understand flow, the code structure may need clarification.

---

### 1.4 Domain Complexity Tax

**Heritage System (32+ commits)**

Required understanding:
- Heritage Conservation Areas (HCAs) vs Heritage Items
- Different HCA structures per council
- Character statements vs controls vs guidance
- Element-specific requirements
- Excluding non-heritage sections from heritage queries (recent fix)

**Council Philosophy Differences:**

| Council | Primary Layer | Approach | Provision Count |
|---------|---------------|----------|-----------------|
| Marrickville | Precinct (34%) | Location-first | 1,051 |
| Leichhardt | Generic (77%) | Topic-first | 2,989 |
| Ashfield | Condition (59%) | Site-condition-first | 1,526 |

**Lesson:** Domain complexity multiplies by jurisdiction. Same data model requires different UX patterns.

---

### 1.5 Revert Analysis

**7 reverts total:**

1. `revert: Restore working NSW API code`
2. `revert: Remove PDF page URL adjustment - causing wrong pages`
3. `revert: Restore exact working code from eb426540`
4. `revert(db): Restore original working DB connection config`
5. `Revert "fix: Add Dulwich Hill precinct mappings"`
6. `fix: Revert to LAST provision PDF button`
7. `fix: Rename Condition to Heritage, hide if 0, revert Zone/Precinct labels`

**Pattern:** Most reverts involve:
- Config changes with side effects
- "Fixes" that broke more than they fixed
- Edge case handling that affected main case

---

## Part 2: Architecture Decisions

### 2.1 Decisions That Held Up

**Planning Portal API as First Filter**
- External government API provides zone, heritage, flood, FSR, height
- System knows property context automatically
- Drives filtering: 48,000 → 350 provisions without user input

**v2_ Column Prefix Strategy**
- New enrichment columns with `v2_` prefix
- Legacy columns preserved
- Easy rollback, clear separation

**Original Text Preservation**
- Never summarize regulations
- Store exact provision text
- Link to exact PDF page for citation

**4-Layer Filtering Model**
```
Layer 1: Generic (always applies)
Layer 2: Zone-Specific (filtered by zone)
Layer 3: Condition (heritage/flood/bushfire)
Layer 4: Precinct (location-specific)
```

### 2.2 Decisions That Caused Pain

**Single Component for Display Logic**
- ProvisionsByTopic.tsx became god component
- Should split: ProvisionCard, ProvisionGroup, ProvisionFilters, ProvisionList

**Multiple Page Number Concepts**
- Three different meanings of "page number"
- Should normalize to single canonical source

**Council Detection by Postcode**
- Edge cases everywhere
- Should use geospatial lookup

---

## Part 3: Time Analysis

### 3.1 Effort Multipliers

| Area | Expected | Actual Commits | Multiplier |
|------|----------|----------------|------------|
| PDF page handling | 1 week | 13+ commits | 5-7x |
| Heritage tagging | 2 days | 32+ commits | 8-10x |
| Loading states | 1 hour | 10 commits | 10x |
| Council mapping | 1 day | 48+ commits | 10x+ |
| UI (one component) | 2 weeks | 76 commits | 3x |

### 3.2 What Shipped Fast

| Area | Why Fast |
|------|----------|
| Initial API endpoint | Clear data model |
| Topic grouping UI | Well-defined structure |
| Planning Portal integration | Clean external API |
| LLM enrichment | Tiered processing |
| Database schema | v2_ prefix = no migration risk |

### 3.3 Effort Distribution

```
PDF/Document Processing:  25%
UI/UX Iterations:         25%
Data Quality/Enrichment:  20%
API Development:          15%
Integration/Debugging:    10%
Documentation:             5%
```

---

## Part 4: Technical Insights

### 4.1 LLM Cost Optimization

**97% cost reduction via tiered processing:**

```
Tier 1: Regex patterns (free)
  - Extract markers (C1, DS, PC, O1)
  - Identify section headers
  - Detect numeric values

Tier 2: Rule-based classification (free)
  - Zone applicability from keywords
  - Topic from section headers
  - Layer from document structure

Tier 3: Batch LLM (cheap)
  - Provisions failing Tier 1-2
  - gpt-4o-mini for cost efficiency

Tier 4: Full LLM (expensive, rare)
  - Heritage sub-categorization
  - Ambiguous cases only
```

### 4.2 Data Quality Issues Resolved

| Issue | Scope | Resolution |
|-------|-------|------------|
| DQ-2: Wrong topics | 14,501 provisions | Position-based matching |
| DQ-7: Dev-type gaps | 13 dev types | Enrichment scripts |
| DQ-11: Heritage undifferentiated | 907 provisions | LLM categorization |
| Duplicate provisions | 1,186 removed | Deduplication query |
| Topic display labels | Missing labels | Added to config |

### 4.3 Recent Feature Additions

**Page Grouping (Dec 2025)**
- Provisions on same PDF page grouped visually
- Reduces visual clutter
- Single PDF button per page group

**DCP Part/Section Headers (Dec 2025)**
- Provisions show source section
- Uses `part_number` not `part_name`
- Helps professionals locate in physical DCP

---

## Part 5: Content Angles

### 5.1 Tweet-Ready Numbers

- 48,000 provisions → 50 per property (99.9% reduction)
- 395 commits in 3 months
- 1.6:1 fix:feature ratio
- 19% of commits on one component (76 commits)
- 10 commits to fix loading spinners
- 13+ commits for PDF page numbers (still ongoing)
- 7 reverts
- 97% LLM cost reduction

### 5.2 Narrative Angles

- "The loading spinner that took 10 commits"
- "13 commits later, we still don't agree what 'page number' means"
- "Built one product, discovered three compliance philosophies"
- "The god component that absorbed 19% of all work"
- "Why 4 debug commits are still in our git history"

### 5.3 Blog Topics

1. **"The 4-Layer Model for Regulatory Filtering"**
2. **"Why AI Summaries Are Wrong for Professional Tools"**
3. **"97% LLM Cost Reduction: Tiered Processing"**
4. **"The God Component Problem"**
5. **"Page Numbers: A Horror Story in 13 Commits"**
6. **"Debug Commits as Architecture Smell"**

---

## Part 6: Reusable Playbook

### 6.1 For New Niche Applications

1. **Identify External Data Source** - API for automatic context
2. **Define Layer Model** - Generic → Type → Condition → Location
3. **Preserve Original Text** - No summaries, citations required
4. **Build Enrichment Pipeline** - v2_ prefix, tiered LLM
5. **Expect 3x Domain Complexity** - Per jurisdiction/region
6. **Identify Integration Points Early** - They'll absorb 20% of commits

### 6.2 Technical Checklist

```
[ ] External API for automatic context
[ ] Original text with source linking
[ ] v2_ column prefix for enrichment
[ ] Tiered LLM processing
[ ] Layer-based filtering model
[ ] Loading state machine (not booleans)
[ ] Single canonical page number concept
[ ] Geospatial location detection
[ ] Logging for complex query paths
[ ] Revert-friendly architecture
```

### 6.3 Anti-Patterns

1. Multiple definitions of same concept (page numbers)
2. Postcode-only location detection
3. Monolithic display component
4. Boolean loading states for complex async
5. Fixing edge cases without regression tests

---

## Part 7: Metrics

### 7.1 Commit Type Distribution

```
169 fix      (43%)
108 feat     (27%)
 27 docs     (7%)
 18 fix(api) (5%)
 11 fix(ui)  (3%)
  8 feat(ui) (2%)
  7 chore    (2%)
  5 refactor (1%)
  4 debug    (1%)
  4 trigger  (1%)
```

### 7.2 Most Modified Files

```
76 ProvisionsByTopic.tsx      (19%)
49 ComplianceDashboard.tsx    (12%)
41 for-property/route.ts      (10%)
31 assessment/page.tsx         (8%)
26 council-config.ts           (7%)
18 nsw-planning-portal.ts      (5%)
17 PropertySearch.tsx          (4%)
16 db.ts                       (4%)
```

### 7.3 Keyword Clusters

```
Heritage/HCA:        32+ commits
Provisions/Filter:   90+ commits
PDF/Page:            54+ commits (13 page-specific)
Precinct/Zone:       48+ commits
Loading/State:       10 commits
```

---

*Document created: 2025-12-10*
*Last updated: 2025-12-10*
*Commit count at time of writing: 395*
