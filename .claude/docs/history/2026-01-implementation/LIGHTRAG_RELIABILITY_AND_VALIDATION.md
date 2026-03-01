# LightRAG Reliability & Validation Strategy
**Date:** 2025-10-23
**Critical Question:** How to ensure LLM-categorized provisions are reliable for compliance use

---

## The Compliance Problem

**Scenario:**
```
LightRAG says: "Front setback: 5.5m"
Certifier asks: "Where in the DCP does it say that?"
Developer asks: "Are you SURE there are no exceptions?"
```

**Risk:**
- LLM might misinterpret conditional requirements
- LLM might miss important caveats ("except where...")
- LLM might merge multiple provisions incorrectly
- LLM might hallucinate values

**Legal requirement:**
- Every compliance determination must trace back to exact regulatory text
- Client must be able to verify the interpretation
- System cannot be a "black box"

---

## Solution: Multi-Layer Validation Architecture

### Layer 1: Full Provenance Tracking

**Every requirement MUST link to source provisions:**

```typescript
interface Requirement {
  id: number;
  category: 'setback_front' | 'landscaping_street' | ...;
  requirement_text: string;          // "Front setback: 5.5 metres"
  value_numeric?: number;            // 5.5
  unit?: string;                     // 'm'

  // CRITICAL: Full source tracking
  source_provisions: {
    provision_id: number;            // Link to regulatory_provisions table
    provision_text: string;          // Full original text
    document_id: string;             // "Marrickville_DCP_2011_4.1"
    section: string;                 // "Section 3.2 - Setbacks"
    pdf_page: number;                // 45
    pdf_page_image_url?: string;     // URL to actual PDF page image
  }[];

  // Quality indicators
  confidence: 'high' | 'medium' | 'low';
  extraction_method: 'llm' | 'structured' | 'manual';
  llm_confidence_score?: number;     // 0.0-1.0

  // Validation status
  validated: boolean;
  validated_by?: string;             // User ID
  validated_at?: Date;
  validation_notes?: string;

  // Caveats/conditions
  conditions?: string[];             // ["Except for corner lots", "Unless heritage overlay"]
  exceptions_detected: boolean;
}
```

---

### Layer 2: Extraction Quality Levels

**Categorize by reliability:**

#### Level 1: STRUCTURED (100% Reliable)
```sql
-- These are already extracted to structured tables
-- No LLM involved, pure database query
SELECT * FROM zone_setback_rules
WHERE zone = 'R2' AND dev_type = 'dwelling_house'

Example:
  Front setback: 5.5m
  Source: Direct extraction, no interpretation
  Confidence: HIGH (database fact)
  Validation: Not needed
```

#### Level 2: LLM HIGH CONFIDENCE (>90%)
```
LLM extracts: "Front setback: 5.5 metres"
From text: "The minimum setback from the primary street frontage
            shall be 5.5 metres for dwelling houses in R2 zones."

Confidence indicators:
✓ Clear numeric value stated
✓ Category explicitly mentioned ("setback")
✓ No conditional language detected
✓ Single source provision
✓ LLM confidence score: 0.95

Status: Show by default, flag for spot-check validation
```

#### Level 3: LLM MEDIUM CONFIDENCE (70-90%)
```
LLM extracts: "Front setback: 5.5m OR match existing street pattern"
From text: "The minimum setback shall be 5.5 metres, however Council
            may accept a variation where the proposal matches the
            prevailing street setback pattern..."

Confidence indicators:
⚠ Multiple options detected
⚠ Conditional language ("however", "may accept")
✓ Numeric value clear
✓ Category clear

Status: Show with warning, require validation before use
```

#### Level 4: LLM LOW CONFIDENCE (<70%)
```
LLM extracts: "Front setback varies - refer to DCP Section 3.2"
From text: Complex multi-paragraph provision with tables, exceptions,
            and cross-references

Confidence indicators:
✗ No clear numeric value
✗ Multiple conditions
✗ References to tables/figures
✗ Cross-references to other sections

Status: Do NOT show as requirement, show link to raw provision instead
```

---

### Layer 3: UI Validation Interface

#### Display Format with Full Traceability

```tsx
<RequirementCard>
  {/* Main requirement */}
  <div className="requirement-header">
    <Badge variant={confidence}>
      {confidence === 'high' ? '✓ HIGH CONFIDENCE' :
       confidence === 'medium' ? '⚠ NEEDS REVIEW' :
       '❌ LOW CONFIDENCE'}
    </Badge>
    <h3>Front Setback: 5.5 metres</h3>
  </div>

  {/* Source provisions - ALWAYS visible */}
  <div className="sources">
    <h4>📄 Source Provisions ({sourceProvisions.length})</h4>

    {sourceProvisions.map(source => (
      <details key={source.provision_id} open={confidence !== 'high'}>
        <summary>
          {source.document_id} - {source.section} (Page {source.pdf_page})
        </summary>

        <div className="original-text">
          {/* Show EXACT original text */}
          <blockquote>
            {source.provision_text}
          </blockquote>

          {/* Link to PDF page image */}
          {source.pdf_page_image_url && (
            <button onClick={() => viewPDF(source.pdf_page_image_url)}>
              📄 View PDF Page {source.pdf_page}
            </button>
          )}
        </div>
      </details>
    ))}
  </div>

  {/* Extraction details */}
  <div className="extraction-info">
    <details>
      <summary>🔍 How this was extracted</summary>
      <ul>
        <li>Method: {extractionMethod}</li>
        <li>LLM Confidence: {llmConfidenceScore * 100}%</li>
        <li>Conditions detected: {conditionsDetected.length}</li>
        <li>Exceptions detected: {exceptionsDetected ? 'Yes' : 'No'}</li>
      </ul>
    </details>
  </div>

  {/* Validation controls */}
  {!validated && (
    <div className="validation-controls">
      <button onClick={() => markValidated(true)}>
        ✓ This is correct
      </button>
      <button onClick={() => markValidated(false)}>
        ✗ This is incorrect
      </button>
      <textarea placeholder="Add notes about issues..." />
    </div>
  )}

  {validated && (
    <div className="validation-status">
      ✓ Validated by {validatedBy} on {validatedAt}
      {validationNotes && <p>{validationNotes}</p>}
    </div>
  )}
</RequirementCard>
```

---

### Layer 4: Conditional/Exception Detection

**Critical: LLM MUST flag conditional provisions**

#### Pattern Detection in Prompt

```typescript
const lightragPrompt = `
Analyze these DCP provisions and extract requirements.

CRITICAL RULES:
1. If provision contains "except", "however", "unless", "where", "may" → flag as CONDITIONAL
2. If provision references tables/figures → flag as REQUIRES_VISUAL
3. If provision cross-references other sections → flag as CROSS_REFERENCE
4. If numeric value has ranges or options → flag as VARIABLE

For each requirement:
- Extract base value
- List ALL conditions/exceptions
- Note ALL cross-references
- Assign confidence level

Example output:
{
  "category": "setback_front",
  "value": 5.5,
  "unit": "m",
  "text": "Front setback: 5.5m",
  "conditions": [
    "Except corner lots may use 4m",
    "Unless heritage overlay applies"
  ],
  "exceptions_detected": true,
  "cross_references": ["Section 8.2 - Heritage"],
  "confidence": "medium"  // MEDIUM because exceptions exist
}
`;
```

#### Display Conditionals Clearly

```tsx
<RequirementCard>
  <h3>Front Setback: 5.5 metres</h3>

  {conditions.length > 0 && (
    <div className="conditions border-l-4 border-yellow-500 pl-3 my-2">
      <h4 className="text-yellow-700 font-semibold">⚠️ Conditions Apply:</h4>
      <ul className="list-disc ml-5">
        {conditions.map(c => (
          <li key={c}>{c}</li>
        ))}
      </ul>
    </div>
  )}

  {crossReferences.length > 0 && (
    <div className="cross-refs border-l-4 border-blue-500 pl-3 my-2">
      <h4 className="text-blue-700 font-semibold">🔗 See Also:</h4>
      <ul className="list-disc ml-5">
        {crossReferences.map(ref => (
          <li key={ref}>
            <a href={`#provision-${ref}`}>{ref}</a>
          </li>
        ))}
      </ul>
    </div>
  )}
</RequirementCard>
```

---

### Layer 5: Progressive Validation Workflow

#### Phase 1: Initial Processing (Automated)
```
1. Run LightRAG on all provisions
2. Generate requirements with confidence scores
3. Flag high/medium/low confidence
4. Store in database with validated=false
```

#### Phase 2: Expert Review (Manual)
```
1. Review HIGH confidence items (spot check 10%)
2. Review ALL MEDIUM confidence items
3. Review ALL LOW confidence items
4. Mark as validated or flag for correction
```

#### Phase 3: Production Use
```
1. Show ONLY validated requirements by default
2. Optionally show high-confidence unvalidated (with disclaimer)
3. Link to raw provisions for anything uncertain
```

---

### Layer 6: Comparison View (Before/After)

**Show user what LLM did:**

```tsx
<ComparisonView>
  <div className="original">
    <h4>📄 Original Provision Text</h4>
    <p>
      "The minimum setback from the primary street frontage shall be
      5.5 metres for dwelling houses. However, Council may accept a
      variation where the development maintains the prevailing street
      setback pattern and does not adversely impact adjoining properties."
    </p>
  </div>

  <div className="arrow">→</div>

  <div className="extracted">
    <h4>🤖 LLM Extracted</h4>
    <div className="requirement">
      <strong>Base requirement:</strong> Front setback: 5.5m
    </div>
    <div className="conditions">
      <strong>Conditions:</strong>
      <ul>
        <li>Council may accept variation</li>
        <li>If maintains street pattern</li>
        <li>If no adverse impact on neighbors</li>
      </ul>
    </div>
    <div className="confidence">
      <strong>Confidence:</strong> MEDIUM (conditional language detected)
    </div>
  </div>

  <div className="validation">
    <button>✓ Correct</button>
    <button>✗ Incorrect - needs adjustment</button>
  </div>
</ComparisonView>
```

---

## Implementation: Database Schema for Validation

```sql
CREATE TABLE dcp_base_requirements (
  id SERIAL PRIMARY KEY,
  lga TEXT NOT NULL,
  zone TEXT NOT NULL,
  dev_type TEXT NOT NULL,

  -- Extracted requirement
  category TEXT NOT NULL,
  requirement_text TEXT NOT NULL,
  value_numeric NUMERIC,
  unit TEXT,

  -- Source tracking (CRITICAL)
  source_provision_ids INTEGER[] NOT NULL,     -- Must have sources
  source_documents TEXT[],
  source_sections TEXT[],

  -- Quality indicators
  confidence TEXT CHECK (confidence IN ('high', 'medium', 'low')),
  llm_confidence_score NUMERIC CHECK (llm_confidence_score BETWEEN 0 AND 1),
  extraction_method TEXT CHECK (extraction_method IN ('llm', 'structured', 'manual')),

  -- Conditional flags
  has_conditions BOOLEAN DEFAULT false,
  conditions TEXT[],                           -- List of conditions
  has_exceptions BOOLEAN DEFAULT false,
  exceptions TEXT[],                           -- List of exceptions
  has_cross_references BOOLEAN DEFAULT false,
  cross_references TEXT[],                     -- Links to other provisions

  -- Validation status
  validated BOOLEAN DEFAULT false,
  validated_by TEXT,
  validated_at TIMESTAMP,
  validation_notes TEXT,
  validation_status TEXT CHECK (validation_status IN ('correct', 'incorrect', 'needs_review')),

  -- Override capability
  manual_override BOOLEAN DEFAULT false,
  override_text TEXT,
  override_by TEXT,
  override_at TIMESTAMP,

  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for validation workflow
CREATE INDEX idx_needs_validation ON dcp_base_requirements(validated, confidence);

-- Index for production queries (only show validated)
CREATE INDEX idx_validated_lookup ON dcp_base_requirements(lga, zone, dev_type, validated);
```

---

## API: Validation Endpoints

```typescript
// GET /api/requirements/validation-queue
// Returns requirements needing validation
interface ValidationQueueResponse {
  high_confidence_unvalidated: Requirement[];      // Spot check these
  medium_confidence_unvalidated: Requirement[];    // Review ALL these
  low_confidence_unvalidated: Requirement[];       // Review ALL these
  total_validated: number;
  total_unvalidated: number;
  validation_progress: number;                     // Percentage
}

// POST /api/requirements/{id}/validate
interface ValidateRequest {
  status: 'correct' | 'incorrect' | 'needs_review';
  notes?: string;
  override?: {
    new_text: string;
    new_value?: number;
    new_unit?: string;
  };
}

// GET /api/requirements/validated
// Returns only validated requirements for production use
interface ProductionRequirementsResponse {
  requirements: Requirement[];
  all_validated: boolean;
  validation_coverage: number;  // Percentage of provisions covered
}
```

---

## UI: Validation Dashboard

```tsx
<ValidationDashboard>
  <ProgressBar>
    Validation Progress: 245/300 requirements validated (82%)
  </ProgressBar>

  <Tabs>
    <Tab label="Needs Review (55)">
      {/* Medium/low confidence items */}
      <RequirementReviewList
        requirements={needsReview}
        onValidate={handleValidate}
      />
    </Tab>

    <Tab label="Validated (245)">
      {/* Already reviewed and approved */}
      <ValidatedRequirementsList requirements={validated} />
    </Tab>

    <Tab label="Issues (12)">
      {/* Marked as incorrect, needs manual correction */}
      <IssuesList requirements={issues} />
    </Tab>
  </Tabs>
</ValidationDashboard>
```

---

## Production Mode: Show Only Validated

```typescript
// Default query - production safe
const requirements = await db.query(`
  SELECT * FROM dcp_base_requirements
  WHERE lga = $1
  AND zone = $2
  AND dev_type = $3
  AND validated = true              -- ONLY show validated
  AND validation_status = 'correct' -- ONLY show correct ones
  ORDER BY category, requirement_text
`, [lga, zone, devType]);

// If insufficient validated requirements, fall back to raw provisions
if (requirements.length < 5) {
  return {
    mode: 'raw_provisions',
    message: 'Categorized requirements not yet validated. Showing raw provisions.',
    raw_provisions: await getRawProvisions(lga, zone, devType)
  };
}
```

---

## Client Validation Workflow

### Step 1: Client Views Requirement
```
Front Setback: 5.5m
[View Source Provisions (2)]
```

### Step 2: Client Expands Sources
```
📄 Source Provisions (2)

Provision 1: Marrickville DCP 2011, Part 4.1, Section 3.2 (Page 45)
"The minimum setback from the primary street frontage shall be
5.5 metres for dwelling houses in R2 zones."

[📄 View PDF Page 45]

Provision 2: Marrickville DCP 2011, Part 4.1, Section 3.2.1 (Page 46)
"Variations to the front setback may be considered where..."

[📄 View PDF Page 46]
```

### Step 3: Client Verifies Against PDF
```
[Opens PDF viewer showing page 45]
✓ Client confirms: Yes, it says 5.5m
✓ Client sees variation clause on next page
✓ Client can now advise with confidence
```

---

## Handling Complex Cases

### Case 1: Table-Based Requirements

**If provision references a table:**
```
LLM output:
{
  category: 'setback_front',
  text: 'Refer to Table 4.1 for front setback requirements',
  value: null,
  confidence: 'low',
  requires_visual: true,
  source_provisions: [12345],
  extraction_notes: 'Requirement defined in table - manual review required'
}

Display:
❌ LOW CONFIDENCE - Requires Manual Review
Category: Front Setback
Source: Table 4.1 (Page 47)
[📄 View PDF Page 47] ← User must check table themselves
```

### Case 2: Conditional Requirements

**If provision has conditions:**
```
LLM output:
{
  category: 'setback_front',
  text: 'Front setback: 5.5m (with conditions)',
  value: 5.5,
  unit: 'm',
  confidence: 'medium',
  has_conditions: true,
  conditions: [
    'Except corner lots: 4m minimum',
    'Heritage overlay: Match existing'
  ]
}

Display:
⚠️ MEDIUM CONFIDENCE - Conditions Apply
Front Setback: 5.5m

⚠️ Conditions:
• Corner lots: 4m minimum (not 5.5m)
• Heritage overlay: Match existing setback

[View Full Provision Text]
```

---

## Recommendation: Phased Rollout

### Phase 1: Internal Validation (Week 1)
- Process 100 combinations with LightRAG
- Expert reviews ALL outputs
- Validates high-confidence items
- Corrects medium/low confidence items
- Builds confidence in categorization

### Phase 2: Beta Testing (Week 2-3)
- Show validated requirements to beta users
- Collect feedback on accuracy
- Refine categorization based on feedback
- Always show source provisions

### Phase 3: Production (Week 4+)
- Only show validated requirements
- Fall back to raw provisions if insufficient validated data
- Continue validation workflow in background
- Build up validated coverage over time

---

## Key Principles for Compliance

1. **Full Traceability:** Every requirement MUST link to source provision text
2. **No Black Boxes:** User can ALWAYS view original regulatory text
3. **Confidence Indicators:** Clear HIGH/MEDIUM/LOW badges
4. **Validation Required:** Don't show unvalidated medium/low confidence
5. **Fallback to Raw:** If uncertain, show raw provisions instead
6. **PDF Access:** Link to actual PDF pages for verification
7. **Expert Review:** Human validation for production use
8. **Audit Trail:** Track who validated what and when

---

## Summary

**The compliance-safe approach:**

1. LightRAG categorizes provisions (automated)
2. System flags confidence levels (automated)
3. Expert validates outputs (manual)
4. Production shows ONLY validated requirements (safe)
5. Every requirement links to source provisions (traceable)
6. User can view PDF pages (verifiable)
7. Uncertain items fall back to raw provisions (conservative)

**Result:**
- Client can verify every single requirement
- Full audit trail from requirement → source provision → PDF page
- Conservative approach: when in doubt, show raw text
- Builds trust through transparency, not blind AI output

**Cost:**
- Processing: $10.82 one-time
- Validation: ~20 hours expert time for 100 combinations
- ROI: Saves hours per address search thereafter
