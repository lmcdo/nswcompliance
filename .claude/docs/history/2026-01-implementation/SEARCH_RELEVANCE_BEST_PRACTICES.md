# SEARCH RELEVANCE: BEST PRACTICES FOR REGULATORY CORPUS
**Objective Analysis of What Actually Works**

---

## EXECUTIVE SUMMARY

**Question:** What relevance logic reliably improves search for regulatory text?

**Short Answer:**
1. **Document hierarchy weighting** (SEPP > LEP > DCP) - HIGH impact
2. **Provision type filtering** (controls vs guidance vs definitions) - HIGH impact
3. **Structured data boost** (provisions with quantitative standards) - MEDIUM-HIGH impact
4. **Click-through learning** (what users actually clicked) - MEDIUM impact (requires data)
5. **Saved searches** - LOW impact (useful for power users, not general search)

---

## CATEGORY 1: LEGAL HIERARCHY WEIGHTING

### The Problem

**Current ranking treats all provisions equally:**
```sql
Search: "building height"

Results ranked by term frequency:
1. DCP provision: "building height" mentioned 5 times (rank: 1.0)
2. SEPP provision: "building height" mentioned 2 times (rank: 0.6)
3. LEP provision: "building height" mentioned 3 times (rank: 0.8)
```

**Legal reality:**
- SEPP overrides everything
- LEP overrides DCP
- DCP provides detailed guidance

**What users need:**
- SEPP provisions should rank FIRST (highest legal authority)
- LEP provisions second
- DCP provisions third (even if they match more terms)

---

### The Solution: Hierarchy Weighting

**Implementation:**
```sql
-- Add document hierarchy to ranking
SELECT
    ref_number,
    provision_text,
    ts_rank(provision_tsv, query) as text_rank,
    -- Boost by legal hierarchy
    CASE document_type
        WHEN 'SEPP' THEN 10.0  -- Highest authority
        WHEN 'LEP' THEN 5.0    -- Medium authority
        WHEN 'DCP' THEN 1.0    -- Detailed guidance
        ELSE 0.5
    END as hierarchy_weight,
    -- Combined ranking
    ts_rank(provision_tsv, query) *
        CASE document_type
            WHEN 'SEPP' THEN 10.0
            WHEN 'LEP' THEN 5.0
            WHEN 'DCP' THEN 1.0
            ELSE 0.5
        END as final_rank
FROM regulatory_provisions
WHERE provision_tsv @@ query
ORDER BY final_rank DESC;
```

**Impact:**

| Search | Current Ranking | With Hierarchy | User Benefit |
|--------|----------------|----------------|--------------|
| "building height" | DCP (5 mentions), SEPP (2 mentions) | SEPP first, then LEP, then DCP | Gets overriding rules first |
| "heritage" | DCP heritage guide, LEP heritage clause | LEP clause first (statutory) | Knows legal requirement |
| "setback" | DCP detailed controls, SEPP exclusions | SEPP exclusions first | Doesn't miss exemptions |

**Reliability:** ✅ **VERY HIGH** - Legal hierarchy is objective and fixed

**Effort to implement:** LOW (just add CASE statement to ranking)

**Industry precedent:**
- AustLII (Australian Legal Information Institute) uses jurisdiction hierarchy
- Westlaw/LexisNexis rank by legal authority
- ePlanning portals prioritize statutory instruments over guidance

---

## CATEGORY 2: PROVISION TYPE CLASSIFICATION

### The Problem

**Not all provisions are equal:**

```
Search: "setback"

Returns mix of:
1. Quantitative controls: "Minimum setback: 0.9m" ← USER WANTS THIS
2. Definitions: "setback means the distance..." ← CONTEXT ONLY
3. Cross-references: "See setback requirements in 4.6" ← POINTER
4. Objectives: "To ensure adequate setbacks" ← HIGH-LEVEL
5. Exemptions: "Setbacks do not apply to..." ← IMPORTANT BUT SPECIFIC
```

**Problem:** Term frequency treats these equally.

---

### The Solution: Provision Type Boost

**Analysis of your database:**

```sql
-- Check what provision metadata exists
SELECT
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE provision_type IS NOT NULL) as has_type,
    COUNT(DISTINCT provision_type) as type_count
FROM regulatory_provisions;
```

**If provision_type exists, use it:**

```sql
SELECT
    ref_number,
    provision_text,
    provision_type,
    ts_rank(provision_tsv, query) as text_rank,
    -- Boost by provision type
    CASE provision_type
        WHEN 'quantitative_standard' THEN 5.0   -- Numeric controls
        WHEN 'performance_criteria' THEN 3.0    -- Qualitative controls
        WHEN 'objective' THEN 2.0               -- High-level guidance
        WHEN 'definition' THEN 1.0              -- Background only
        WHEN 'cross_reference' THEN 0.5         -- Pointer to other
        ELSE 1.0
    END as type_weight,
    -- Combined
    ts_rank(provision_tsv, query) * type_weight as final_rank
FROM regulatory_provisions
WHERE provision_tsv @@ query
ORDER BY final_rank DESC;
```

**If provision_type doesn't exist, INFER from content:**

```sql
-- Classify provisions by content patterns
SELECT
    ref_number,
    provision_text,
    -- Infer type from text patterns
    CASE
        -- Has numeric value + unit = quantitative
        WHEN provision_text ~ '\d+\.?\d*\s*(m|mm|cm|%|ha|m²)' THEN 5.0
        -- Starts with objective language
        WHEN provision_text ~* '^(objective|aim|purpose|to ensure)' THEN 2.0
        -- Is a definition
        WHEN provision_text ~* '(means|refers to|is defined)' THEN 1.0
        -- Cross-reference pattern
        WHEN provision_text ~* '(see|refer to|clause|schedule|section)\s+\d' THEN 0.5
        -- Default
        ELSE 1.0
    END as inferred_type_weight,
    ts_rank(provision_tsv, query) * inferred_type_weight as final_rank
FROM regulatory_provisions
WHERE provision_tsv @@ query
ORDER BY final_rank DESC;
```

**Impact:**

| Search | Without Type Boost | With Type Boost | Improvement |
|--------|-------------------|-----------------|-------------|
| "setback" | Definition first (10 mentions) | "0.9m setback" first (has numeric) | User gets control, not definition |
| "heritage" | Objectives first (generic) | LEP heritage clause (statutory) | User gets legal requirement |
| "height" | "See height controls" (reference) | "Max height: 8.5m" (quantitative) | User gets answer, not pointer |

**Reliability:** ✅ **HIGH** - Provision types are stable and predictable

**Effort:**
- IF provision_type exists: LOW (just add CASE)
- IF need to infer: MEDIUM (need regex patterns)

**Industry precedent:**
- Building codes separate "deemed-to-satisfy" from "performance" provisions
- Legal databases distinguish "binding rules" from "commentary"
- Standards (AS/NZS) rank normative clauses over informative

---

## CATEGORY 3: STRUCTURED DATA BOOST

### The Problem

**Provisions with quantitative standards are more actionable:**

```
Search: "building height"

Provision A: "Buildings should be designed with appropriate heights"
→ Vague guidance, not actionable

Provision B: "Maximum building height: 8.5m"
→ Numeric control, directly actionable
```

**Users want Provision B, but term frequency might rank A higher if "building" and "height" appear more.**

---

### The Solution: Quantitative Boost

**Leverage existing quantitative_standards table:**

```sql
-- Check if provision has linked quantitative data
SELECT
    rp.ref_number,
    rp.provision_text,
    ts_rank(rp.provision_tsv, query) as text_rank,
    -- Boost if has quantitative standard
    CASE
        WHEN qs.id IS NOT NULL THEN 3.0  -- Has numeric standard
        ELSE 1.0                          -- Qualitative only
    END as quant_boost,
    -- Combined
    ts_rank(rp.provision_tsv, query) *
        CASE WHEN qs.id IS NOT NULL THEN 3.0 ELSE 1.0 END as final_rank
FROM regulatory_provisions rp
LEFT JOIN quantitative_standards qs ON rp.id = qs.provision_id
WHERE rp.provision_tsv @@ query
ORDER BY final_rank DESC;
```

**Alternative: Detect numbers in text directly:**

```sql
SELECT
    ref_number,
    provision_text,
    ts_rank(provision_tsv, query) as text_rank,
    -- Boost if contains numeric values
    CASE
        WHEN provision_text ~ '\d+\.?\d*\s*(m|mm|%|ha|m²|degrees)' THEN 2.0
        ELSE 1.0
    END as numeric_boost,
    ts_rank(provision_tsv, query) * numeric_boost as final_rank
FROM regulatory_provisions
WHERE provision_tsv @@ query
ORDER BY final_rank DESC;
```

**Impact:**

| Search | Without Quant Boost | With Quant Boost | User Benefit |
|--------|---------------------|------------------|--------------|
| "setback" | Objectives + controls mixed | "0.9m minimum" first | Gets numeric answer |
| "height" | "appropriate height" first | "8.5m max" first | Gets actionable limit |
| "parking" | "adequate parking" | "1 space per 50m²" first | Gets calculation |

**Reliability:** ✅ **HIGH** - Numbers are objective

**Effort:** LOW (simple regex or JOIN to quantitative_standards)

**Industry precedent:**
- Planning portals highlight "key controls" (numeric)
- Building code search prioritizes "deemed-to-satisfy" (specific) over "performance" (vague)

---

## CATEGORY 4: BEHAVIORAL SIGNALS (Click-Through Learning)

### The Concept

**Track what users actually click:**

```
User searches: "building height"
Results shown:
1. "Building Height Controls: 8.5m max" → User clicks ✓
2. "See building height requirements" → User ignores
3. "Building design and height guidance" → User ignores
4. "Height of buildings shall..." → User clicks ✓

Learning: Results #1 and #4 are more relevant than #2, #3
```

**Implementation:**

```sql
-- Create click tracking table
CREATE TABLE search_analytics (
    id SERIAL PRIMARY KEY,
    search_query TEXT,
    provision_id INTEGER,
    result_position INTEGER,  -- Where in results it appeared
    clicked BOOLEAN,          -- Did user click?
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Query with click-through boost
SELECT
    rp.ref_number,
    rp.provision_text,
    ts_rank(rp.provision_tsv, query) as text_rank,
    -- Boost based on historical clicks
    COALESCE(
        (SELECT COUNT(*) * 0.1
         FROM search_analytics sa
         WHERE sa.provision_id = rp.id
         AND sa.search_query = 'building height'
         AND sa.clicked = TRUE
         AND sa.timestamp > NOW() - INTERVAL '90 days'
        ), 0
    ) as click_boost,
    -- Combined
    ts_rank(rp.provision_tsv, query) + click_boost as final_rank
FROM regulatory_provisions rp
WHERE rp.provision_tsv @@ query
ORDER BY final_rank DESC;
```

**Pros:**
- ✅ Adapts to actual user behavior
- ✅ Learns over time
- ✅ Personalized to your user base

**Cons:**
- ⚠️ Requires user tracking (privacy concerns)
- ⚠️ Needs significant data volume (100+ searches per query)
- ⚠️ Cold start problem (new provisions have no clicks)
- ⚠️ Feedback loops (popular results get more popular)
- ⚠️ Manipulation risk (SEO-like gaming)

**Reliability:** ⚠️ **MEDIUM** - Works well at scale, risky at low volume

**Effort:** MEDIUM-HIGH (tracking, analytics, privacy compliance)

**Industry precedent:**
- Google, Bing use click-through for web search
- LexisNexis uses citation counts (similar signal)
- Not common in regulatory/planning portals (privacy concerns)

**Recommendation for your use case:**
- **Start without it** (too complex for current scale)
- **Add later** if you have 1000+ active users
- **Alternative:** Use expert curation (see below)

---

## CATEGORY 5: SAVED SEARCHES / QUERY TEMPLATES

### The Concept

**Provide pre-built search queries for common tasks:**

```
Common user needs:
- "What are the setback requirements for my zone?"
- "Maximum building height in residential areas"
- "Parking space calculations"
- "Heritage conservation requirements"
```

**Implementation:**

```sql
-- Saved search templates
CREATE TABLE search_templates (
    id SERIAL PRIMARY KEY,
    template_name TEXT,
    description TEXT,
    base_query TEXT,
    filters JSONB,  -- Additional filters (zone, document_type, etc.)
    boost_provisions INTEGER[],  -- Pre-identified key provisions
    created_by TEXT,
    usage_count INTEGER DEFAULT 0
);

-- Example template
INSERT INTO search_templates (template_name, description, base_query, filters)
VALUES (
    'Setback Requirements',
    'Find setback controls for your zone',
    'setback & (minimum | maximum | required)',
    '{"provision_type": ["quantitative_standard"], "document_type": ["LEP", "DCP"]}'
);

-- Use template with user's zone
SELECT rp.*,
    ts_rank(rp.provision_tsv, to_tsquery('setback & (minimum | maximum)')) as rank
FROM regulatory_provisions rp
WHERE rp.provision_tsv @@ to_tsquery('setback & (minimum | maximum)')
AND rp.zone = 'R2'  -- User's zone
AND rp.document_type IN ('LEP', 'DCP')
ORDER BY rank DESC;
```

**Pros:**
- ✅ Guides users to correct search syntax
- ✅ Applies domain knowledge (what "setback requirements" means)
- ✅ Reduces bad searches

**Cons:**
- ⚠️ Only helps if users use templates (most won't)
- ⚠️ Maintenance burden (need to keep updated)
- ⚠️ Doesn't help exploratory/one-off searches

**Reliability:** ✅ **HIGH** - When used, very accurate

**Usage rate:** ⚠️ **LOW** - Typically <10% of searches use templates

**Effort:** MEDIUM (build templates, UI for selection)

**Industry precedent:**
- ePlanning portals have "topic guides" (similar concept)
- Westlaw has "practice area filters" (similar)
- Google Scholar has "case law searches" (templates)

**Better alternative: Query suggestions**

```sql
-- Auto-suggest better queries based on input
User types: "setback"
System suggests:
  - "setback requirements [zone]"
  - "minimum setback residential"
  - "setback calculations"

User types: "height"
System suggests:
  - "building height maximum"
  - "height controls [zone]"
  - "height variation applications"
```

**This has higher adoption** than saved searches (20-40% usage).

---

## CATEGORY 6: EXPERT CURATION (Manual Boosting)

### The Concept

**Subject matter experts identify "key provisions" that should rank higher:**

```sql
-- Expert-curated importance
CREATE TABLE provision_importance (
    provision_id INTEGER PRIMARY KEY,
    importance_score NUMERIC(3,2),  -- 0.0 to 5.0
    reason TEXT,
    curated_by TEXT,
    curated_date DATE
);

-- Examples
INSERT INTO provision_importance VALUES
(12345, 5.0, 'Core setback control for R2 zones', 'town_planner', '2025-01-15'),
(12346, 4.0, 'Heritage overlay requirements', 'heritage_advisor', '2025-01-20'),
(12347, 1.0, 'Definition only, not actionable', 'town_planner', '2025-01-15');

-- Use in ranking
SELECT
    rp.ref_number,
    rp.provision_text,
    ts_rank(rp.provision_tsv, query) as text_rank,
    COALESCE(pi.importance_score, 1.0) as expert_weight,
    ts_rank(rp.provision_tsv, query) *
        COALESCE(pi.importance_score, 1.0) as final_rank
FROM regulatory_provisions rp
LEFT JOIN provision_importance pi ON rp.id = pi.provision_id
WHERE rp.provision_tsv @@ query
ORDER BY final_rank DESC;
```

**Pros:**
- ✅ Highly accurate (domain experts know what matters)
- ✅ No cold start problem
- ✅ No privacy concerns
- ✅ Transparent (can show "expert recommended")

**Cons:**
- ⚠️ Labor intensive (requires SME time)
- ⚠️ Doesn't scale (22K provisions = too many to curate)
- ⚠️ Becomes stale (regulations change)

**Reliability:** ✅ **VERY HIGH** - But only for curated provisions

**Coverage:** ⚠️ **LOW** - Can only curate ~1-5% of provisions

**Effort:** HIGH (ongoing SME time)

**Industry precedent:**
- AustLII has "notable cases"
- Planning portals have "key controls" sections
- Building codes highlight "main requirements"

**Practical approach:**
- Curate **top 100 most-searched provisions** (Pareto: 80% of searches hit 20% of provisions)
- Let text ranking handle the rest

---

## CATEGORY 7: CONTEXTUAL SIGNALS (Zone, Property Type, etc.)

### The Concept

**Search results depend on user's context:**

```
Search: "building height"

For user in R2 zone:
  1. R2 height limits: 8.5m (MOST RELEVANT)
  2. General height controls (SOMEWHAT RELEVANT)
  3. R3 height limits: 12m (LESS RELEVANT)

For user in B4 zone:
  1. B4 height limits: 15m (MOST RELEVANT)
  2. General height controls (SOMEWHAT RELEVANT)
  3. R2 height limits: 8.5m (LESS RELEVANT)
```

**Implementation:**

```sql
-- Search with zone context
SELECT
    rp.ref_number,
    rp.provision_text,
    ts_rank(rp.provision_tsv, query) as text_rank,
    -- Boost if matches user's zone
    CASE
        WHEN rp.zone = 'R2' THEN 5.0  -- User's zone (from session)
        WHEN rp.zone IS NULL THEN 2.0  -- General provision
        ELSE 0.5                        -- Other zones
    END as zone_boost,
    ts_rank(rp.provision_tsv, query) * zone_boost as final_rank
FROM regulatory_provisions rp
WHERE rp.provision_tsv @@ query
ORDER BY final_rank DESC;
```

**Pros:**
- ✅ Highly relevant (user gets zone-specific answers)
- ✅ Reduces noise (don't show R3 controls to R2 user)
- ✅ Improves precision dramatically

**Cons:**
- ⚠️ Requires knowing user's context (zone, property type, etc.)
- ⚠️ May hide relevant info (user might want to compare zones)
- ⚠️ UI needs context input

**Reliability:** ✅ **VERY HIGH** - When context is known

**Effort:** LOW (just add WHERE clause or boost)

**Industry precedent:**
- **Every planning portal does this** (ePlanning NSW, VicPlan, etc.)
- Property search sites (Domain, REA) filter by location
- This is **table stakes** for planning search

**Your database already supports this:**
- `zone` column exists in regulatory_provisions
- `lga_name` exists in documents
- Just need UI to capture user's context

---

## RANKING STRATEGY: RECOMMENDED PRIORITY

### Tier 1: IMPLEMENT NOW (High Impact, Low Effort)

| Feature | Impact | Effort | Reliability | Priority |
|---------|--------|--------|-------------|----------|
| **1. Hierarchy weighting** (SEPP > LEP > DCP) | HIGH | LOW | VERY HIGH | ⭐⭐⭐⭐⭐ |
| **2. Quantitative boost** (has numbers) | HIGH | LOW | HIGH | ⭐⭐⭐⭐⭐ |
| **3. Zone filtering** (user's context) | VERY HIGH | LOW | VERY HIGH | ⭐⭐⭐⭐⭐ |

**Combined impact:**
```sql
-- Production-ready ranking formula
SELECT
    rp.ref_number,
    rp.provision_text,
    ts_rank(rp.provision_tsv, query) as text_rank,

    -- Legal hierarchy boost
    CASE d.document_type
        WHEN 'SEPP' THEN 10.0
        WHEN 'LEP' THEN 5.0
        WHEN 'DCP' THEN 1.0
    END as hierarchy_weight,

    -- Quantitative provision boost
    CASE WHEN qs.id IS NOT NULL THEN 2.0 ELSE 1.0 END as quant_boost,

    -- Zone relevance boost
    CASE
        WHEN rp.zone = user_zone THEN 5.0
        WHEN rp.zone IS NULL THEN 1.0
        ELSE 0.3
    END as zone_boost,

    -- FINAL RANK
    ts_rank(rp.provision_tsv, query) *
        hierarchy_weight *
        quant_boost *
        zone_boost as final_rank

FROM regulatory_provisions rp
JOIN documents d ON rp.document_id = d.id
LEFT JOIN quantitative_standards qs ON rp.id = qs.provision_id
WHERE rp.provision_tsv @@ query
ORDER BY final_rank DESC;
```

**Estimated improvement:**
- Current: User scans 50-100 results to find answer
- With this: User finds answer in top 3-5 results
- **10-20x improvement in user efficiency**

---

### Tier 2: IMPLEMENT SOON (Medium Impact, Medium Effort)

| Feature | Impact | Effort | Reliability | Priority |
|---------|--------|--------|-------------|----------|
| **4. Provision type classification** | MEDIUM-HIGH | MEDIUM | HIGH | ⭐⭐⭐⭐ |
| **5. Query suggestions** | MEDIUM | MEDIUM | MEDIUM | ⭐⭐⭐ |
| **6. Expert curation** (top 100) | HIGH | HIGH | VERY HIGH | ⭐⭐⭐ |

**Provision type** - If you don't have provision_type column:
```sql
-- Add provision_type inference
ALTER TABLE regulatory_provisions ADD COLUMN inferred_type TEXT;

UPDATE regulatory_provisions SET inferred_type =
    CASE
        WHEN provision_text ~ '\d+\.?\d*\s*(m|mm|%|ha)' THEN 'quantitative'
        WHEN provision_text ~* '^(objective|aim|purpose)' THEN 'objective'
        WHEN provision_text ~* '(means|refers to|defined)' THEN 'definition'
        WHEN provision_text ~* '(see|refer|clause|schedule)\s+\d' THEN 'reference'
        ELSE 'general'
    END;

CREATE INDEX idx_provisions_type ON regulatory_provisions(inferred_type);
```

---

### Tier 3: IMPLEMENT LATER (Low Priority / High Complexity)

| Feature | Impact | Effort | Reliability | When |
|---------|--------|--------|-------------|------|
| **7. Click-through learning** | MEDIUM | HIGH | MEDIUM | At 1000+ users |
| **8. Saved searches** | LOW | MEDIUM | HIGH | If users request |
| **9. ML-based ranking** | UNKNOWN | VERY HIGH | LOW | Never (overkill) |

---

## WHAT NOT TO DO

### ❌ Don't: Machine Learning Ranking (at your scale)

**Why it's tempting:**
- "AI can learn what's relevant!"
- "Other search engines use ML!"

**Why it's wrong for you:**
- Requires 10,000+ training examples
- Black box (can't explain why provision ranked high)
- Regulatory context has clear rules (hierarchy, types) that ML would have to re-learn
- Overkill for 22K provisions

**Better approach:** Rule-based ranking (hierarchy + types + context)

---

### ❌ Don't: User-editable saved searches (at first)

**Why it's tempting:**
- "Power users can build complex queries!"

**Why it's wrong:**
- <5% of users will use it
- Maintenance burden (users create bad searches)
- Better to spend time on default ranking

**Better approach:** Auto-suggestions + good default ranking

---

### ❌ Don't: Personalization (yet)

**Why it's tempting:**
- "Each user has different needs!"

**Why it's wrong:**
- Privacy concerns (tracking individual behavior)
- Regulatory requirements are objective (not subjective)
- Context (zone) is more important than individual preferences

**Better approach:** Zone/property-type filtering (contextual, not personal)

---

## THE BOTTOM LINE

**Your question:** "What relevance logic could reliably help this?"

**Answer: Three tiers**

### Must Have (Implement with full-text search):
1. ✅ **Legal hierarchy** (SEPP > LEP > DCP) - 10x boost for SEPP
2. ✅ **Quantitative boost** (provisions with numbers) - 2-3x boost
3. ✅ **Zone filtering** (user's context) - 5x boost for matching zone

**Combined formula:**
```
final_rank = text_rank × hierarchy_weight × quant_boost × zone_boost
```

**Estimated impact:** 10-20x better than text ranking alone

---

### Should Have (Next iteration):
4. ⚠️ **Provision type** (controls > definitions) - Requires classification
5. ⚠️ **Query suggestions** - Helps users phrase better searches
6. ⚠️ **Expert curation** - Top 100 provisions manually ranked

---

### Could Have (Future):
7. 🔮 **Click-through learning** - Only at scale (1000+ users)
8. 🔮 **Saved searches** - If users request

---

### Won't Have:
9. ❌ **ML ranking** - Overkill, black box, unnecessary
10. ❌ **Personalization** - Privacy concerns, objective domain

---

**The reliable core:**
- Legal hierarchy (objective, stable)
- Provision structure (objective, stable)
- User context (objective, known)

**Avoid:**
- Behavioral signals (privacy, complexity)
- Black-box ML (unexplainable)
- Over-personalization (regulatory is objective)

**Saved searches:** Useful for power users (<10% adoption), but not a replacement for good default ranking.

---

*End of Best Practices Analysis*
