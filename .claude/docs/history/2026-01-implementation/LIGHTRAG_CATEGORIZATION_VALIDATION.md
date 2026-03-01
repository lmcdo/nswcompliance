# LightRAG Categorization Validation Strategy
**Date:** 2025-10-23
**Critical Question:** How to verify we have ALL relevant and NO irrelevant provisions in each category

---

## The Categorization Problem

**Example: Setback Category**

Starting with 241 provisions for (Marrickville, R2, Dwelling House):

**Question 1 (Completeness/Recall):**
- Are there 15 setback provisions in the 241 total?
- Did LightRAG find all 15? Or only 12? (Missing 3 = compliance risk!)

**Question 2 (Precision):**
- Did LightRAG categorize 15 provisions as "setback"?
- Are all 15 actually about setbacks? Or did it include 3 parking provisions by mistake?

**Question 3 (Coverage):**
- Are there provisions about "setback variations for heritage" that got missed?
- Are there provisions in Part 2 General that also apply but got overlooked?

---

## Solution: Multi-Method Validation

### Method 1: Keyword Cross-Check (Automated)

**Verify completeness by searching for keywords:**

```sql
-- 1. What did LightRAG categorize as "setback"?
SELECT provision_id FROM dcp_base_requirements
WHERE category LIKE 'setback%'
-- Returns: [12345, 12346, 12347, ...] (e.g., 12 provisions)

-- 2. What provisions contain setback keywords?
SELECT id, provision_text FROM regulatory_provisions
WHERE provision_text ~* '(setback|set.?back|building line|frontage|boundary)'
AND lga = 'Marrickville'
AND zone = 'R2'
-- Returns: [12345, 12346, 12347, ..., 12358, 12359, 12360] (e.g., 15 provisions)

-- 3. FIND THE GAPS
-- Provisions with "setback" keywords NOT categorized as setback
SELECT id, provision_text FROM regulatory_provisions
WHERE id IN (12358, 12359, 12360)  -- The 3 missing ones
AND id NOT IN (
  SELECT unnest(source_provision_ids)
  FROM dcp_base_requirements
  WHERE category LIKE 'setback%'
)
```

**Output:**
```
⚠️ POTENTIAL MISSING PROVISIONS (3):

Provision #12358 (Part 2.6):
"Setbacks to watercourses shall be a minimum of 10 metres..."
→ Contains "setback" but NOT categorized
→ ACTION: Review if this applies to dwelling houses

Provision #12359 (Part 4.1.3.2):
"Corner lots may reduce the secondary street setback to 4 metres..."
→ Contains "setback" but NOT categorized
→ ACTION: Review if this was intentionally excluded

Provision #12360 (Part 8.2):
"Heritage items: maintain existing setback pattern..."
→ Contains "setback" but NOT categorized
→ ACTION: Review if this applies to R2 zone
```

---

### Method 2: Reverse Keyword Check (Automated)

**Verify precision by checking categorized provisions:**

```sql
-- What did LightRAG categorize as "parking"?
SELECT source_provision_ids FROM dcp_base_requirements
WHERE category = 'parking'
-- Returns: [23456, 23457, 23458]

-- Do these provisions actually mention "parking"?
SELECT id, provision_text FROM regulatory_provisions
WHERE id IN (23456, 23457, 23458)
AND provision_text !~* '(parking|car.?space|vehicle|garage)'
```

**Output:**
```
❌ FALSE POSITIVE DETECTED:

Provision #23458:
"Loading bays shall be provided at the rear of commercial buildings..."
→ Categorized as "parking" but mentions "loading bays"
→ ACTION: Should this be "parking" or "loading"?
```

---

### Method 3: Category Coverage Matrix (Visual)

**Show what got categorized and what didn't:**

```
241 Total Provisions
├─ 65 Categorized (27%)
│  ├─ Setback: 12 provisions
│  ├─ Parking: 8 provisions
│  ├─ Landscaping: 15 provisions
│  ├─ Building Design: 18 provisions
│  ├─ Privacy: 7 provisions
│  └─ Solar Access: 5 provisions
│
└─ 176 NOT Categorized (73%)
   ├─ Contains "setback" keywords: 3 ⚠️ REVIEW
   ├─ Contains "parking" keywords: 1 ⚠️ REVIEW
   ├─ Contains "landscaping" keywords: 2 ⚠️ REVIEW
   └─ No obvious keywords: 170 ✓ Likely procedural/definitions
```

**Action Items:**
- Review the 3 uncategorized provisions with "setback" keywords
- Review the 1 uncategorized provision with "parking" keywords
- Spot-check a sample of the 170 uncategorized to ensure nothing missed

---

### Method 4: Manual Sampling (Statistical)

**Systematic review of random samples:**

#### Sample 1: Verify Completeness (Recall)
```
Take 50 random provisions from the uncategorized 176:
├─ Expert reads each one
├─ Marks: "Should this be categorized? Under what category?"
└─ Calculates: False Negative Rate

Example:
Out of 50 random uncategorized provisions:
- 45 are correctly uncategorized (definitions, procedures, cross-refs)
- 5 should have been categorized
  - 2 setback provisions
  - 1 parking provision
  - 2 landscaping provisions

False Negative Rate: 5/50 = 10%
Estimated total missed: 176 × 10% = ~18 provisions

Action: Review all 176 uncategorized to find the ~18 missed
```

#### Sample 2: Verify Precision
```
Take all 12 provisions categorized as "setback":
├─ Expert reads each one
├─ Marks: "Is this actually about setbacks?"
└─ Calculates: False Positive Rate

Example:
Out of 12 categorized as "setback":
- 11 are correctly categorized
- 1 is actually about "boundary fencing" (not setback)

False Positive Rate: 1/12 = 8.3%

Action: Review this provision and recategorize
```

---

### Method 5: Keyword Frequency Analysis

**Statistical validation of categorization:**

```python
# For each category, analyze keyword frequency

setback_requirements = get_requirements(category='setback')
setback_provision_texts = [r.provision_text for r in setback_requirements]

# Count keyword occurrences
setback_keywords = count_keywords(setback_provision_texts, [
    'setback', 'set back', 'building line', 'frontage',
    'boundary', 'distance from', 'minimum distance'
])

# Expected: High frequency of setback keywords
# Actual:
#   "setback" appears in 10/12 provisions (83%)
#   "building line" appears in 3/12 provisions (25%)
#   "frontage" appears in 8/12 provisions (67%)

# RED FLAG if <70% contain primary keyword
if keyword_frequency < 0.7:
    print("⚠️ WARNING: Low keyword frequency suggests miscategorization")
```

**Example Output:**
```
Category: Setback
└─ 12 provisions categorized
   ├─ "setback" appears in: 10/12 (83%) ✓
   ├─ "building line" appears in: 3/12 (25%)
   ├─ "frontage" appears in: 8/12 (67%)
   └─ No keywords found in: 2/12 ⚠️ REVIEW THESE

Provisions without keywords:
- Provision #12347: "Development shall maintain adequate separation..."
  → Uses "separation" not "setback" - still valid

- Provision #12350: "Corner sites shall comply with Section 3.2.1..."
  → Cross-reference, no explicit keyword - verify manually
```

---

### Method 6: Hierarchical Category Tree

**Ensure no provisions fall through the cracks:**

```
DCP Provisions (241)
│
├─ SITE PLANNING (40)
│  ├─ Setbacks (12)
│  ├─ Parking (8)
│  └─ Vehicular Access (5)
│  └─ Uncategorized (15) ⚠️ REVIEW
│
├─ BUILDING DESIGN (35)
│  ├─ Building Form (10)
│  ├─ Materials (8)
│  └─ Roof Design (7)
│  └─ Uncategorized (10) ⚠️ REVIEW
│
├─ LANDSCAPING (28)
│  ├─ Front Setback (12)
│  ├─ Rear Yard (8)
│  └─ Tree Preservation (8)
│
├─ ENVIRONMENTAL (15)
│  ├─ Solar Access (5)
│  ├─ Privacy (7)
│  └─ Stormwater (3)
│
└─ PROCEDURAL/DEFINITIONS (123)
   └─ Correctly uncategorized ✓
```

**Flag for review:** Any section with >20% uncategorized

---

### Method 7: Comparative Analysis (Gold Standard)

**Expert manually categorizes a sample, compare to LightRAG:**

#### Step 1: Expert Categorization (Sample of 50)
```
Expert reviews 50 random provisions:
├─ 18 categorized as "setback"
├─ 12 categorized as "parking"
├─ 8 categorized as "landscaping"
├─ 5 categorized as "building design"
└─ 7 not categorized (procedural)
```

#### Step 2: LightRAG Categorization (Same 50)
```
LightRAG categorizes same 50:
├─ 16 categorized as "setback"
├─ 13 categorized as "parking"
├─ 7 categorized as "landscaping"
├─ 6 categorized as "building design"
└─ 8 not categorized
```

#### Step 3: Calculate Metrics
```
Setback Category:
- Expert found: 18
- LightRAG found: 16
- Overlap: 15
- False Negatives (missed by LLM): 3 (Expert found but LLM didn't)
- False Positives (wrong by LLM): 1 (LLM found but Expert didn't)
- Recall: 15/18 = 83.3%
- Precision: 15/16 = 93.8%
- F1 Score: 88.2%

Action: Review the 3 missed and 1 incorrect
```

---

## Validation Database Schema

```sql
CREATE TABLE categorization_validation (
  id SERIAL PRIMARY KEY,
  provision_id INTEGER REFERENCES regulatory_provisions(id),
  lga TEXT,
  zone TEXT,
  dev_type TEXT,

  -- LightRAG categorization
  llm_category TEXT,
  llm_confidence NUMERIC,
  llm_rationale TEXT,

  -- Keyword check
  contains_keywords TEXT[],
  primary_keyword_found BOOLEAN,

  -- Expert review
  expert_category TEXT,
  expert_notes TEXT,
  expert_reviewed_by TEXT,
  expert_reviewed_at TIMESTAMP,

  -- Validation result
  categorization_correct BOOLEAN,
  should_be_category TEXT,  -- If incorrect, what should it be?

  validation_status TEXT CHECK (validation_status IN (
    'correct',           -- LLM category matches expert
    'false_negative',    -- Should be categorized but wasn't
    'false_positive',    -- Incorrectly categorized
    'wrong_category'     -- Categorized but in wrong category
  )),

  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_validation_status ON categorization_validation(validation_status);
CREATE INDEX idx_llm_category ON categorization_validation(llm_category);
CREATE INDEX idx_expert_category ON categorization_validation(expert_category);
```

---

## Automated Validation Queries

### Query 1: Find Potential False Negatives
```sql
-- Provisions with setback keywords NOT categorized as setback
SELECT
  rp.id,
  rp.provision_text,
  rp.document_id,
  (SELECT array_agg(category)
   FROM dcp_base_requirements dbr
   WHERE rp.id = ANY(dbr.source_provision_ids)) as current_categories
FROM regulatory_provisions rp
WHERE rp.lga = 'Marrickville'
  AND rp.zone = 'R2'
  AND rp.provision_text ~* '(setback|set.?back|building.?line)'
  AND rp.id NOT IN (
    SELECT unnest(source_provision_ids)
    FROM dcp_base_requirements
    WHERE category LIKE 'setback%'
  )
ORDER BY rp.document_id;
```

### Query 2: Find Potential False Positives
```sql
-- Provisions categorized as setback WITHOUT setback keywords
SELECT
  rp.id,
  rp.provision_text,
  dbr.category,
  dbr.requirement_text
FROM dcp_base_requirements dbr
JOIN regulatory_provisions rp ON rp.id = ANY(dbr.source_provision_ids)
WHERE dbr.category LIKE 'setback%'
  AND rp.provision_text !~* '(setback|set.?back|building.?line|frontage|boundary|distance)'
ORDER BY dbr.category;
```

### Query 3: Coverage Summary
```sql
-- How many provisions are categorized vs uncategorized?
SELECT
  COUNT(DISTINCT rp.id) as total_provisions,
  COUNT(DISTINCT CASE
    WHEN rp.id IN (
      SELECT unnest(source_provision_ids) FROM dcp_base_requirements
    ) THEN rp.id END
  ) as categorized_provisions,
  COUNT(DISTINCT CASE
    WHEN rp.id NOT IN (
      SELECT unnest(source_provision_ids) FROM dcp_base_requirements
    ) THEN rp.id END
  ) as uncategorized_provisions
FROM regulatory_provisions rp
WHERE rp.lga = 'Marrickville'
  AND rp.zone = 'R2'
  AND rp.dev_type = 'dwelling_house';
```

---

## Validation UI/Dashboard

```tsx
<ValidationDashboard>
  <CategoryMetrics>
    <Metric category="setback">
      <h3>Setback Provisions</h3>
      <Stats>
        <Stat label="Categorized" value={12} />
        <Stat label="Keyword Matches" value={15} status="warning" />
        <Stat label="Uncategorized with Keywords" value={3} status="error" />
        <Stat label="Precision" value="92%" status="good" />
        <Stat label="Recall" value="80%" status="warning" />
      </Stats>

      <Actions>
        <button>Review 3 Potentially Missed Provisions</button>
        <button>Review 1 False Positive</button>
      </Actions>
    </Metric>

    <Metric category="parking">
      <h3>Parking Provisions</h3>
      <Stats>
        <Stat label="Categorized" value={8} />
        <Stat label="Keyword Matches" value={8} status="good" />
        <Stat label="Precision" value="100%" status="good" />
        <Stat label="Recall" value="100%" status="good" />
      </Stats>

      <Actions>
        <button disabled>✓ No Issues Detected</button>
      </Actions>
    </Metric>
  </CategoryMetrics>

  <UncategorizedReview>
    <h3>Uncategorized Provisions (176)</h3>

    <Filter>
      <label>Show:</label>
      <select>
        <option>All uncategorized (176)</option>
        <option>With "setback" keywords (3) ⚠️</option>
        <option>With "parking" keywords (1) ⚠️</option>
        <option>With "landscaping" keywords (2) ⚠️</option>
        <option>No obvious keywords (170)</option>
      </select>
    </Filter>

    <ProvisionList>
      {uncategorized.map(provision => (
        <ProvisionCard key={provision.id}>
          <div className="text">{provision.provision_text}</div>
          <div className="keywords">
            Keywords found: {provision.detected_keywords.join(', ')}
          </div>
          <div className="actions">
            <select onChange={e => categorize(provision.id, e.target.value)}>
              <option value="">Categorize as...</option>
              <option value="setback">Setback</option>
              <option value="parking">Parking</option>
              <option value="landscaping">Landscaping</option>
              <option value="not_applicable">Not Applicable</option>
            </select>
            <button>✓ Correct - Leave Uncategorized</button>
          </div>
        </ProvisionCard>
      ))}
    </ProvisionList>
  </UncategorizedReview>
</ValidationDashboard>
```

---

## Validation Workflow

### Step 1: Initial Processing
```bash
# Run LightRAG categorization
python lightrag_categorize.py --lga Marrickville --zone R2 --dev-type dwelling_house

# Output: dcp_base_requirements table populated
```

### Step 2: Automated Validation
```bash
# Run automated checks
python validate_categorization.py

# Output:
# ✓ Setback: 12 categorized, 3 keyword matches uncategorized
# ✓ Parking: 8 categorized, 1 keyword match uncategorized
# ✓ Landscaping: 15 categorized, 2 keyword matches uncategorized
# ⚠️ Total categorized: 65/241 (27%)
# ⚠️ Review queue: 6 provisions flagged for review
```

### Step 3: Expert Review
```
Expert reviews flagged provisions:
1. Provision #12358 (uncategorized, has "setback" keyword)
   → Decision: Add to setback category

2. Provision #12359 (uncategorized, has "setback" keyword)
   → Decision: Correct - this is about setback to watercourses, not buildings

3. Provision #23458 (categorized as parking, no parking keywords)
   → Decision: Recategorize as "loading" not "parking"
```

### Step 4: Statistical Sampling
```
Sample 50 random uncategorized provisions:
- Expert categorizes 5/50 as missed
- False Negative Rate: 10%
- Estimated total missed: 176 × 10% = ~18

Action: Review all 176 or expand sample to 100
```

### Step 5: Calculate Final Metrics
```
Setback Category:
- Total provisions with setback content: 15 (expert count)
- LightRAG found: 12
- After review, added: 2
- Final count: 14/15 = 93.3% recall
- False positives: 0
- Precision: 100%
```

---

## Acceptance Criteria

**Before going to production:**

| Category | Recall (Completeness) | Precision | F1 Score |
|----------|----------------------|-----------|----------|
| Setback | >90% | >95% | >92% |
| Parking | >90% | >95% | >92% |
| Landscaping | >85% | >90% | >87% |
| Building Design | >80% | >85% | >82% |

**If metrics below threshold:**
- Review all flagged provisions
- Improve LightRAG prompt
- Re-run categorization
- Re-validate

---

## Key Validation Steps (Summary)

1. **Keyword Cross-Check:** Find uncategorized provisions with category keywords
2. **Reverse Keyword Check:** Verify categorized provisions contain expected keywords
3. **Coverage Matrix:** Visualize what % got categorized
4. **Manual Sampling:** Expert reviews random sample, calculate recall/precision
5. **Comparative Analysis:** Expert categorizes same set, compare to LightRAG
6. **Validation Dashboard:** UI to review flagged provisions
7. **Acceptance Testing:** Metrics must meet thresholds before production

**Result:** Quantifiable confidence in completeness and precision of categorization.
