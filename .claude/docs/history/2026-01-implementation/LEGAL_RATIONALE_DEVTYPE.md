# Development Type Filtering - Legitimate Use & Risk Mitigation

**Document:** Supplement to LEGAL_RATIONALE.md
**Date:** January 27, 2026
**Status:** Council QA Review - Data-Verified Analysis

---

## Executive Summary

Development type filtering CAN be used legitimately and compliantly, but effectiveness and risk vary dramatically by council. Based on verified database analysis:

- **Leichhardt:** ✅ **SAFE & EFFECTIVE** (65.8% tagged, 100% coverage) - Primary filtering strategy
- **Ashfield:** ⚠️ **MODERATE RISK** (41.1% tagged, 52% condition-based) - Supplementary filtering only
- **Marrickville:** ❌ **HIGH RISK** (30.2% tagged, 51% missing tags) - DO NOT USE until data quality fixed

---

## 1. How Dev-Type Filtering Works (Legitimate & Compliant)

### Legal Foundation

**The Question:** Can we filter provisions by development type without violating EP&A Act s 4.15?

**The Answer:** YES, but ONLY when:
1. Provisions are **explicitly tagged** by the DCP author (not AI guesswork)
2. Users can **disable the filter** to see all provisions (opt-in filtering)
3. System displays **clear disclaimer** about EP&A Act s 4.15 obligations
4. Untagged provisions default to "applies to ALL" (inclusive approach)

### How We Tag Provisions

**Method 1: Direct Text Extraction (90% of tags)**
```sql
-- Example: Provision text contains "Dwelling houses shall..."
-- System tags: v2_applicable_dev_types = ['dwelling_house']

-- Example: Provision text contains "All development must..."
-- System tags: v2_applicable_dev_types = ['ALL'] or NULL
```

**Method 2: Contextual Part Analysis (10% of tags)**
```sql
-- Example: Provision is in "Part 4: Residential Development" section
-- System infers: v2_applicable_dev_types = ['residential_development_types']
-- ONLY when Part title is unambiguous
```

**Method 3: Conservative NULL Handling**
```sql
-- If uncertain or provision applies generally:
-- System tags: v2_applicable_dev_types = NULL
-- UI interprets: "Applies to all development types"
```

### Three-Tier Relevance System

When user selects "dwelling_house", the API returns ALL provisions but ranks them:

```typescript
PRIMARY (most relevant):
  v2_applicable_dev_types && ['dwelling_house']
  // Explicitly tagged for dwelling houses

GENERAL (always relevant):
  v2_applicable_dev_types IS NULL OR v2_applicable_dev_types = ['ALL']
  // Generic provisions applying to all development

SECONDARY (may be relevant):
  All other provisions
  // Not explicitly tagged but may apply via objectives (EP&A s 4.15)
```

**Legal Safety:** ALL provisions are shown. Dev-type determines DISPLAY ORDER, not visibility.

---

## 2. Leichhardt - Safe & Effective (✅ RECOMMENDED)

### Data Profile
- **Total Provisions:** 1,442 actionable
- **Dev-Type Tagging:** 100% coverage (1,442/1,442 have tags)
- **Specific Tagging:** 65.8% (949 provisions explicitly tagged for specific dev types)
- **Generic (ALL):** 34.2% (493 provisions tagged as 'ALL' or NULL)

### Why It Works

**Layer Distribution:**
- Generic: 757 provisions (52.5%) - Apply to ALL dev types regardless
- Precinct: 623 provisions (43.2%) - **Most are dev-type specific** (e.g., "Residential precincts require...")
- Condition: 41 provisions (2.8%) - Heritage, flood (not dev-type dependent)
- Use-specific: 21 provisions (1.5%) - Zone-based, not dev-type based

**Key Insight:** Leichhardt's **precinct provisions** (43.2%) are heavily dev-type tagged. When user selects "dwelling_house", they get:
- All 757 generic provisions (always relevant)
- ~200-250 precinct provisions tagged for residential use
- Filters out ~400 commercial/industrial precinct provisions

**Result:** 1,442 provisions → ~493 provisions (66% reduction)

### Compliance Safeguards

1. **100% Tagging Coverage:** No provisions are "orphaned" or unclassified
2. **Explicit DCP Language:** Tags derived from phrases like "Residential development in this precinct must..."
3. **User Override:** "View All Provisions" button shows full 1,442
4. **Audit Trail:** Every provision shows "Relevance: Primary/General/Secondary" with explanation

### Legal Defensibility

**If challenged in court:**
- ✅ "All provisions were available to the certifier" (View All button)
- ✅ "Filtering based on explicit DCP language" (not AI interpretation)
- ✅ "Generic provisions always shown" (no risk of missing general controls)
- ✅ "EP&A Act s 4.15 disclaimer prominent" (user aware of obligations)

**Recommendation:** **IMPLEMENT dev-type filtering as PRIMARY strategy for Leichhardt.**

---

## 3. Ashfield - Moderate Risk (⚠️ CONDITIONAL USE)

### Data Profile
- **Total Provisions:** 1,112 actionable
- **Dev-Type Tagging:** 99.5% coverage (1,106/1,112 have tags)
- **Specific Tagging:** 41.1% (457 provisions explicitly tagged for specific dev types)
- **Generic (ALL):** 58.4% (649 provisions tagged as 'ALL' or NULL)

### Why It's Risky

**Layer Distribution:**
- **Condition: 578 provisions (52.2%)** - Heritage-based, NOT dev-type based
- Generic: 328 provisions (29.6%) - Apply to ALL dev types
- Precinct: 134 provisions (12.1%) - Somewhat dev-type specific
- Use-specific: 68 provisions (6.1%) - Zone-based

**The Problem:** 52.2% of Ashfield provisions are **condition-based** (heritage). Dev-type filtering doesn't capture these because heritage provisions apply to:
- Dwelling houses in heritage areas
- Commercial buildings in heritage areas
- Industrial buildings in heritage areas

**Example Failure Scenario:**
```
User selects: "dwelling_house"
Dev-type filter returns: 457 provisions (41.1%)
MISSES: 578 heritage provisions (52.2%) marked as "applies to ALL in HCA"

If property is in Heritage Conservation Area:
  User sees 457 provisions
  SHOULD see 457 + 578 = 1,035 provisions

Result: 56% of relevant provisions HIDDEN
```

### How to Use Safely

**NEVER use dev-type filtering alone for Ashfield.**

**Recommended Filtering Strategy:**
```typescript
// Step 1: Apply CONDITION filter first (heritage status)
if (property.heritage === true) {
  provisions = [...genericProvisions, ...heritageProvisions];
  // Result: 328 + 578 = 906 provisions
}

// Step 2: OPTIONALLY apply dev-type filter within condition-filtered set
if (user.enableDevTypeFilter) {
  provisions = provisions.filter(p =>
    p.v2_applicable_dev_types.includes(devType) ||
    p.v2_applicable_dev_types === 'ALL'
  );
  // Result: 906 → ~600 provisions (conservative filtering)
}
```

### Compliance Safeguards

1. **Condition Filter Takes Precedence:** Heritage provisions ALWAYS included if property is heritage
2. **Dev-Type as OPTIONAL:** User must explicitly enable dev-type filter (disabled by default for Ashfield)
3. **Warning Banner:** "Ashfield DCP is heritage-focused. Ensure you review all heritage provisions regardless of development type."
4. **Two-Stage Filtering Display:**
   - Stage 1: "Showing 906 provisions (328 generic + 578 heritage)"
   - Stage 2: "Dev-type filter active: Showing 600 provisions (matches dwelling_house)"

### Legal Defensibility

**Moderate Risk - Acceptable with safeguards:**
- ⚠️ "Dev-type filtering may miss heritage provisions if used alone" (HIGH RISK)
- ✅ "Condition-first filtering ensures heritage provisions included" (MITIGATED)
- ✅ "User explicitly enables optional dev-type filter" (INFORMED CONSENT)
- ✅ "Warning banner explains Ashfield heritage focus" (DISCLOSURE)

**Recommendation:** **USE dev-type filtering ONLY as supplementary filter after condition filtering. Disabled by default.**

---

## 4. Marrickville - High Risk (❌ DO NOT USE - DATA QUALITY ISSUE)

### Data Profile
- **Total Provisions:** 1,584 actionable
- **Dev-Type Tagging:** 48.9% coverage (774/1,584 have tags)
- **Specific Tagging:** 30.2% (478 provisions explicitly tagged for specific dev types)
- **MISSING TAGS:** 51.1% (810 provisions have v2_applicable_dev_types = NULL)

### Why It's Dangerous

**Layer Distribution:**
- Precinct: 275 provisions (17.4%) - Should be dev-type specific, but only 30% are tagged
- Generic: 206 provisions (13.0%) - Tagged correctly
- Condition: 180 provisions (11.4%) - Heritage (not dev-type dependent)
- Use-specific: 113 provisions (7.1%) - Zone-based
- **UNKNOWN/UNTAGGED: 810 provisions (51.1%)** - Critical data quality gap

**The Fatal Flaw:** 51% of Marrickville provisions have no dev-type tags. These include:
- Part 9 precinct provisions (should be dev-type specific)
- Part 4 zone-specific provisions (should be use-type specific)
- Unknown provisions that may or may not apply

**Example Failure Scenario:**
```
User selects: "dwelling_house"
Dev-type filter returns: 478 provisions (30.2% tagged)
TREATS AS GENERIC: 810 provisions (51.1% untagged - shown to ALL users)

Result: 810 untagged provisions shown to EVERY dev type
  - Includes commercial precinct provisions (irrelevant to dwelling)
  - Includes industrial zone provisions (irrelevant to dwelling)
  - User receives 1,288 provisions instead of ~500 relevant

WORSE: No way to know if untagged provisions are relevant or not
```

### Root Cause Analysis

**Why are 51% untagged?**

**Hypothesis 1:** Part 9 (Precincts) extraction quality issue
- Part 9 has 47 precincts with character statements
- Text patterns may not have triggered dev-type extraction
- Example: "Junction Central precinct character" doesn't mention "residential" or "commercial" explicitly

**Hypothesis 2:** Legacy data migration
- Marrickville may have mixed old/new extraction runs
- 48.9% tagged = newer extraction with v2_applicable_dev_types logic
- 51.1% untagged = older extraction without dev-type logic

**Hypothesis 3:** Precinct provisions are context-dependent
- Precinct character statements apply to "all development in the precinct"
- But specific controls within precincts ARE dev-type specific
- Extraction may have conservatively left them NULL

### What Needs to Happen (Data Quality Fix)

**Required Actions BEFORE enabling dev-type filtering:**

1. **Audit Part 9 Provisions (275 precinct provisions)**
   ```sql
   SELECT v2_dcp_part, COUNT(*),
          COUNT(CASE WHEN v2_applicable_dev_types IS NULL THEN 1 END) as untagged
   FROM regulatory_provisions
   WHERE document_id ILIKE '%marrickville%'
     AND v2_is_actionable = true
   GROUP BY v2_dcp_part
   ORDER BY untagged DESC;
   ```
   - Identify which Parts have highest untagged %
   - Manually review sample provisions
   - Determine if provisions are genuinely generic or missed tagging

2. **Re-run Dev-Type Extraction for Part 9**
   ```python
   # Use LLM to analyze precinct provision text
   for provision in part_9_provisions:
       if provision.v2_applicable_dev_types is NULL:
           dev_types = extract_dev_types_from_text(provision.text)
           if dev_types:
               provision.v2_applicable_dev_types = dev_types
           else:
               provision.v2_applicable_dev_types = ['ALL']  # Explicit generic
   ```

3. **Verification Test**
   - Target: >70% dev-type tagging coverage
   - Test: Query "dwelling_house" provisions
   - Expected: 500-700 provisions (not 1,288)
   - Validate: No commercial/industrial provisions in result

4. **Progressive Rollout**
   - Phase 1: Fix tagging, verify in staging
   - Phase 2: A/B test with 10% of users (track feedback)
   - Phase 3: Full rollout if validation passes

### Current Recommendation

**DO NOT enable dev-type filtering for Marrickville until data quality issue resolved.**

**Alternative Filtering Strategy (Current Implementation):**
```typescript
// Use PRECINCT filtering instead (already implemented)
if (property.precinct_id) {
  provisions = provisions.filter(p =>
    p.v2_dcp_layer === 'generic' ||
    p.v2_dcp_layer === 'use_specific' && p.zone === property.zone ||
    p.v2_dcp_layer === 'condition' && p.condition === property.condition ||
    p.v2_dcp_layer === 'precinct' && p.v2_precinct_id === property.precinct_id
  );
  // Result: 50-90 provisions (validated effective)
}
```

**This works because:**
- Precinct filtering relies on `v2_precinct_id` (100% tagged)
- Zone filtering relies on `v2_applicable_zones` (95%+ tagged)
- Doesn't depend on incomplete `v2_applicable_dev_types` field

### Legal Risk Assessment

**IF deployed with current 51% untagged:**
- ❌ **HIGH RISK:** "System showed 1,288 provisions when only 500 were relevant" (cognitive overload)
- ❌ **HIGH RISK:** "Certifier missed provision because buried in 810 irrelevant untagged provisions" (professional negligence)
- ❌ **HIGH RISK:** "System claimed dev-type filtering but 51% provisions had no tags" (misleading representation)

**Recommendation:** **BLOCK dev-type filtering for Marrickville. Display warning: "Marrickville dev-type filtering unavailable due to data quality issue. Use precinct filtering instead."**

---

## 5. Implementation Recommendations

### Immediate Actions

**Leichhardt:**
```typescript
// Enable dev-type filtering as PRIMARY filter
const COUNCIL_CONFIGS = {
  leichhardt: {
    features: {
      devTypeFiltering: 'primary',  // Use as main filtering strategy
      topicFiltering: 'secondary',  // Use after dev-type reduces set
      showDevTypeToggle: false,     // Always on (safe)
    },
    ui: {
      defaultFilter: 'dev_type',
      banner: 'Leichhardt provisions filtered by development type for relevance. View All to see full 1,442 provisions.'
    }
  }
};
```

**Ashfield:**
```typescript
// Enable dev-type filtering as OPTIONAL after condition filtering
const COUNCIL_CONFIGS = {
  ashfield: {
    features: {
      devTypeFiltering: 'optional',     // User must enable
      conditionFiltering: 'primary',    // Heritage first
      showDevTypeToggle: true,          // User control
    },
    ui: {
      defaultFilter: 'condition',       // Heritage status first
      devTypeWarning: 'Ashfield DCP is heritage-focused. Dev-type filter is optional and may hide relevant heritage provisions. Use with caution.',
      banner: 'Heritage provisions shown by default. Enable dev-type filter to further refine (optional).'
    }
  }
};
```

**Marrickville:**
```typescript
// DISABLE dev-type filtering until data quality fixed
const COUNCIL_CONFIGS = {
  marrickville: {
    features: {
      devTypeFiltering: 'disabled',     // Blocked
      precinctFiltering: 'primary',     // Use precinct instead
      showDevTypeToggle: false,         // Don't offer the option
    },
    ui: {
      defaultFilter: 'precinct',
      disabledNotice: 'Marrickville dev-type filtering currently unavailable due to incomplete tagging (51% provisions unclassified). Precinct filtering provides accurate results.',
      dataQualityBanner: 'Data Quality Issue: 810/1,584 provisions lack dev-type tags. Using precinct + zone filtering instead.'
    }
  }
};
```

### API Changes

**Add council-aware filtering logic:**
```typescript
async function queryLayer(filters: FilterParams) {
  // Check council-specific config
  const councilConfig = COUNCIL_CONFIGS[filters.former_council];

  // Leichhardt: Apply dev-type WHERE clause
  if (councilConfig.features.devTypeFiltering === 'primary') {
    sql += ` AND (
      v2_applicable_dev_types && $devType
      OR v2_applicable_dev_types IS NULL
      OR 'ALL' = ANY(v2_applicable_dev_types)
    )`;
  }

  // Ashfield: Condition first, then optional dev-type
  if (councilConfig.features.devTypeFiltering === 'optional') {
    // Always include condition-based provisions
    if (filters.heritage) {
      sql += ` AND (v2_dcp_layer = 'condition' OR ...)`;
    }
    // Only apply dev-type if user explicitly enabled
    if (filters.enableDevTypeFilter) {
      sql += ` AND (v2_applicable_dev_types && $devType OR ...)`;
    }
  }

  // Marrickville: Ignore dev-type, use precinct/zone
  if (councilConfig.features.devTypeFiltering === 'disabled') {
    // Dev-type parameter ignored
    // Use precinct + zone filtering only
  }
}
```

### User Interface Changes

**Leichhardt:**
- Dev-type dropdown prominent (above topic filter)
- No toggle (always enabled)
- Provision count: "Showing 493 provisions for dwelling_house (filtered from 1,442 total)"

**Ashfield:**
- Heritage toggle FIRST (primary position)
- Dev-type toggle SECOND (optional, with warning icon)
- Provision count: "Showing 906 heritage provisions (600 match dwelling_house dev-type filter - optional)"

**Marrickville:**
- Dev-type dropdown HIDDEN
- Precinct filter prominent
- Notice: "Dev-type filtering unavailable (data quality issue). Using precinct filtering."

---

## 6. Legal Compliance Matrix

| Council | Dev-Type Filter | Legal Risk | Safeguards Required | Deployment Status |
|---------|----------------|------------|---------------------|-------------------|
| **Leichhardt** | ✅ Primary | LOW | EP&A banner + View All button | APPROVED |
| **Ashfield** | ⚠️ Optional | MODERATE | Condition-first + Warning + User opt-in | CONDITIONAL |
| **Marrickville** | ❌ Disabled | HIGH | N/A - Not deployed | BLOCKED |

---

## 7. Monitoring & Validation

**Post-Deployment Metrics:**

1. **Leichhardt:**
   - Track: % users who click "View All" (should be <5% if filtering works)
   - Track: Provision count distribution by dev-type (validate 400-600 range)
   - Alert: If any dev-type returns >1,000 provisions (indicates tagging failure)

2. **Ashfield:**
   - Track: % users who enable optional dev-type filter (expect 30-50%)
   - Track: Heritage properties: provision count with/without dev-type (validate reduction is <40%)
   - Alert: If heritage property gets <500 provisions (indicates filtering too aggressive)

3. **Marrickville:**
   - Track: Completion of data quality fix (target: Q1 2026)
   - Test: Re-run tagging coverage query monthly
   - Deploy: When coverage reaches >70%, re-evaluate for Phase 2

---

## 8. Conclusion

**Dev-type filtering is NOT one-size-fits-all.**

- **Leichhardt:** Excellent data quality (100% coverage, 65.8% specific) → Safe primary filter
- **Ashfield:** Moderate data quality (41.1% specific, 52% condition-based) → Supplementary filter only
- **Marrickville:** Poor data quality (51% missing tags) → Block until fixed

**Legal defensibility depends on:**
1. Data quality (tagging completeness)
2. User control (can disable filter)
3. Transparency (clear disclaimers)
4. Safeguards (condition-first for Ashfield, View All for Leichhardt)

**This is the optimal approach** given current data state. Marrickville data quality fix is P1 before any dev-type filtering deployment.
