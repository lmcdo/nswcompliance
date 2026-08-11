# SEPP Extraction Quality Control Rules

**Created:** 2026-02-20
**Purpose:** Prevent low-quality, duplicate, and hallucinated extractions

## Root Cause Analysis

### What Went Wrong:
1. **Duplication:** Single 353-char provision → 19 requirements (mostly duplicates)
2. **Over-extraction:** Provisions with <50 chars per requirement
3. **Confidence uniformity:** All requirements from a provision having identical confidence scores
4. **No validation:** Script accepted any array length from Claude without checking

### Why It Happened:
- Prompt didn't explicitly forbid duplicates
- No max_items constraint on tool schema
- No post-extraction deduplication
- No statistical validation before INSERT
- Tool schema allowed unlimited array length

---

## DETECTION MECHANISMS

### 1. Exact Duplicate Detection
**Rule:** Flag if same (provision_id + requirement_category + exclusion_type + metric_name + applies_to) appears >1 time

**Implementation:**
```sql
-- Run after each batch
SELECT
  provision_id,
  requirement_category,
  exclusion_type,
  metric_name,
  applies_to,
  COUNT(*) as duplicate_count
FROM sepp_structured_requirements
GROUP BY provision_id, requirement_category, exclusion_type, metric_name, applies_to
HAVING COUNT(*) > 1
```

**Action:** Delete duplicates, keep only 1

---

### 2. Over-Extraction Detection
**Rule:** Flag if chars_per_requirement < 50

**Calculation:**
```javascript
const charsPerReq = provision.provision_text.length / requirements.length;
if (charsPerReq < 50) {
  console.warn(`⚠️ OVER-EXTRACTION: ${requirements.length} reqs from ${provision.provision_text.length} chars`);
  // Reject extraction, log for review
}
```

**Thresholds:**
- `<50 chars/req`: ❌ REJECT (hallucination)
- `50-100 chars/req`: ⚠️ FLAG for manual review
- `>100 chars/req`: ✅ ACCEPT

---

### 3. Confidence Score Uniformity
**Rule:** Flag if >5 requirements from same provision have identical confidence

**Implementation:**
```javascript
const uniqueConfidences = new Set(requirements.map(r => r.extraction_confidence));
if (requirements.length > 5 && uniqueConfidences.size === 1) {
  console.warn(`⚠️ UNIFORM CONFIDENCE: All ${requirements.length} reqs have confidence ${[...uniqueConfidences][0]}`);
  // Flag for review
}
```

---

### 4. Statistical Outlier Detection
**Rule:** Flag if requirement_count > (mean + 2σ)

**Current stats:** Mean=7.1, StdDev=5.5 → Threshold=18.1

**Implementation:**
```javascript
if (requirements.length > 15) {  // Hardcoded conservative threshold
  console.warn(`⚠️ OUTLIER: ${requirements.length} requirements (threshold: 15)`);
  // Require manual review before saving
}
```

---

### 5. Provision Length Validation
**Rule:** Provisions <200 chars should yield ≤2 requirements

**Implementation:**
```javascript
if (provision.provision_text.length < 200 && requirements.length > 2) {
  console.warn(`⚠️ SHORT PROVISION: ${provision.provision_text.length} chars yielded ${requirements.length} reqs (expected ≤2)`);
  // Cap at 2, discard rest
}
```

---

## PREVENTION MECHANISMS

### 1. Improved Prompt Engineering

**Add these constraints:**
```
CRITICAL INSTRUCTIONS:
1. Extract UNIQUE, DISTINCT requirements only
2. Each requirement must represent a DIFFERENT rule/constraint
3. DO NOT extract duplicates or near-duplicates
4. If a provision states ONE rule with multiple conditions, extract it as ONE requirement with context JSON
5. Maximum 5 requirements per provision (typical: 1-3)
6. If the provision is <200 characters, extract at most 1-2 requirements

Examples of CORRECT extraction:
- Single rule about biodiversity threshold → 1 requirement (exclusion)
- Rule with 3 zone conditions → 1 requirement with context: {"zones": ["R1", "R2", "R3"]}

Examples of INCORRECT extraction:
- Extracting same exclusion type 8 times with different confidence scores → WRONG
- Splitting one rule into multiple requirements → WRONG
```

---

### 2. Tool Schema Constraints

**Add max_items:**
```typescript
requirements: {
  type: 'array',
  maxItems: 5,  // Hard cap at 5 requirements per provision
  items: { ... }
}
```

**Make fields more specific:**
```typescript
// Change this:
applies_to: { type: 'string' }

// To this:
applies_to: {
  type: 'string',
  enum: ['CDC', 'Pattern_Book', 'all', 'DA', 'subdivision']
}
```

---

### 3. Post-Extraction Deduplication

**Before saving, deduplicate in-memory:**
```typescript
function deduplicateRequirements(requirements: any[]): any[] {
  const seen = new Set<string>();
  return requirements.filter(req => {
    const key = JSON.stringify({
      category: req.requirement_category,
      exclusion: req.exclusion_type,
      metric: req.metric_name,
      applies: req.applies_to
    });

    if (seen.has(key)) {
      console.log(`  ⚠️ Skipping duplicate: ${key}`);
      return false;
    }
    seen.add(key);
    return true;
  });
}
```

---

### 4. Validation Pipeline

**Run BEFORE saving to database:**
```typescript
function validateExtraction(provision: any, requirements: any[]): {valid: boolean, issues: string[]} {
  const issues: string[] = [];

  // Rule 1: Max count
  if (requirements.length > 15) {
    issues.push(`Too many requirements: ${requirements.length} (max: 15)`);
  }

  // Rule 2: Chars per requirement
  const charsPerReq = provision.provision_text.length / requirements.length;
  if (charsPerReq < 50) {
    issues.push(`Over-extraction: ${charsPerReq.toFixed(0)} chars/req (min: 50)`);
  }

  // Rule 3: Confidence uniformity
  const uniqueConfidences = new Set(requirements.map(r => r.extraction_confidence));
  if (requirements.length > 5 && uniqueConfidences.size === 1) {
    issues.push(`Uniform confidence: all ${requirements.length} have confidence ${[...uniqueConfidences][0]}`);
  }

  // Rule 4: Short provision cap
  if (provision.provision_text.length < 200 && requirements.length > 2) {
    issues.push(`Short provision (<200 chars) yielded ${requirements.length} reqs (max: 2)`);
  }

  return {
    valid: issues.length === 0,
    issues
  };
}
```

**Usage:**
```typescript
const { valid, issues } = validateExtraction(provision, requirements);
if (!valid) {
  console.error(`❌ VALIDATION FAILED: ${issues.join('; ')}`);
  // Log to review queue instead of saving
  saveForManualReview(provision.id, requirements, issues);
  return 0;  // Don't save
}
```

---

### 5. Database-Level Constraints

**Add UNIQUE constraint (partial):**
```sql
CREATE UNIQUE INDEX idx_unique_requirement
ON sepp_structured_requirements (
  provision_id,
  requirement_category,
  COALESCE(exclusion_type, ''),
  COALESCE(metric_name, '')
)
WHERE extraction_confidence > 0.7;
```

This prevents exact duplicates from being inserted.

---

### 6. Extended Thinking Mode

**Use Claude's extended thinking for complex provisions:**
```typescript
const response = await client.messages.create({
  model: MODEL,
  max_tokens: 8192,
  thinking: {
    type: "enabled",
    budget_tokens: 4000
  },
  tools: [SEPP_EXTRACTION_TOOL],
  messages: [{
    role: 'user',
    content: prompt
  }]
});
```

This allows Claude to reason about whether requirements are truly distinct.

---

### 7. Two-Pass Review

**After extraction, ask Claude to review:**
```typescript
// Pass 1: Extract
const extraction = await extractStructuredRequirements(provision);

// Pass 2: Review and deduplicate
const review = await client.messages.create({
  model: MODEL,
  max_tokens: 2048,
  messages: [{
    role: 'user',
    content: `Review these ${extraction.requirements.length} requirements extracted from a provision.

Are there any duplicates or near-duplicates? If so, merge them into unique requirements.

Original provision: ${provision.provision_text}

Extracted requirements: ${JSON.stringify(extraction.requirements, null, 2)}

Return only the UNIQUE requirements.`
  }]
});
```

---

## QUALITY METRICS

Track these per batch:

1. **Duplication Rate:** % of requirements that are exact duplicates
   - **Target:** <5%

2. **Over-Extraction Rate:** % of provisions with <50 chars/req
   - **Target:** <2%

3. **Average Requirements per Provision:**
   - **Target:** 2-4 (current: 7.1 is too high)

4. **Confidence Distribution:**
   - **Target:** Normal distribution, not clustered

5. **Manual Review Queue Size:**
   - **Target:** <10% of provisions need review

---

## IMPLEMENTATION PRIORITY

**Phase 1 (CRITICAL):**
1. ✅ Add validation pipeline (chars/req, max count, uniformity checks)
2. ✅ Add deduplication logic
3. ✅ Update prompt with explicit anti-duplication instructions
4. ✅ Add maxItems: 5 to tool schema

**Phase 2 (HIGH):**
5. Add database UNIQUE constraint
6. Implement manual review queue for flagged extractions
7. Add statistics logging after each batch

**Phase 3 (MEDIUM):**
8. Implement two-pass review for high-count provisions
9. Add extended thinking for complex provisions (>500 chars)
10. Build quality dashboard

---

## TESTING PROTOCOL

Before running full extraction:

1. **Test on 10 known provisions** (manually verify correctness)
2. **Run validation on test output** (check all rules pass)
3. **Extract 50 provisions** (Phase 0.5)
4. **Run quality analysis** (duplication rate, chars/req, outliers)
5. **Manual review of flagged items**
6. **Adjust thresholds** if needed
7. **THEN proceed to Phase 1 (200 provisions)**

---

## CLEANUP STRATEGY

**For existing 128 rows:**
1. Delete all (clean slate)
2. Re-extract with improved prompt + validation
3. Quality will be guaranteed by prevention mechanisms

**Command:**
```sql
TRUNCATE TABLE sepp_structured_requirements;
```
