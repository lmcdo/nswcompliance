# Strategic Data Fields - Hypothetical Hindsight Analysis
**"What fields should we capture NOW that we'll desperately wish we had LATER?"**

**Date:** 2025-11-02
**Context:** Council profiles + LEP enrichment features
**Approach:** Reverse-engineer from future success scenarios

---

## Executive Summary

Based on the council profiles strategy and LEP enrichment plan, here are fields we should capture NOW (or compute retrospectively) that will unlock future capabilities:

**Priority Tiers:**
- **P0 (Critical):** Already have or need immediately
- **P1 (High Value):** Enable key features within 3 months
- **P2 (Strategic):** Unlock advanced features within 6 months
- **P3 (Future):** Enable ML/analytics/comparison tools

---

## 1. DCP Requirements Tables (General + Precinct)

### Currently Have (P0):
```sql
✅ heritage_context TEXT
✅ objective TEXT
✅ performance_criteria TEXT
✅ allows_alternative_solutions BOOLEAN
✅ alternative_solutions_criteria TEXT
✅ confidence VARCHAR(20)
✅ category VARCHAR(100)
✅ former_council VARCHAR(50)
```

### Should Add Immediately (P1):

#### User Guidance Fields
```sql
-- HOW prescriptive is this requirement?
prescriptiveness_score INTEGER CHECK (prescriptiveness_score BETWEEN 0 AND 100);
-- 0 = pure performance-based ("achieve character")
-- 50 = hybrid ("6m setback preferred, or demonstrate...")
-- 100 = absolute rule ("6m setback required, no exceptions")

-- WHY useful: Drives "strict compliance" vs "flexible approach" badges
-- Computed from: Text analysis (presence of "must", "required" vs "should", "may")

-- User action type
user_action_type VARCHAR(50);
-- Values: 'design_requirement' | 'da_submission' | 'informational' | 'consultation_trigger'
-- WHY useful: Filter out noise, show only actionable items
-- Example: "Contact council" = consultation_trigger (not design requirement)

-- Compliance difficulty
compliance_difficulty VARCHAR(20);
-- Values: 'straightforward' | 'moderate' | 'complex' | 'specialist_required'
-- WHY useful: User expectation setting ("this one needs an architect")
-- Computed from: Conditionals, cross-references, technical terminology density
```

#### Traceability Fields
```sql
-- Source traceability
extracted_from_section TEXT;
-- Example: "Chapter F, Section 2.3.1, Control 14"
-- WHY useful: "View in source PDF" linking, verification

source_page_range TEXT;
-- Example: "Pages 42-44"
-- WHY useful: Multi-page requirements context

related_provision_ids INTEGER[];
-- Example: [12345, 12346, 12347]
-- WHY useful: "This requirement relates to X and Y" linking
-- Future: Graph-based requirement exploration

supersedes_provision_id INTEGER;
-- If this requirement replaces an older one
-- WHY useful: Version tracking, "what changed?" features
```

#### Enrichment Metadata
```sql
-- Data completeness
context_completeness_score INTEGER CHECK (context_completeness_score BETWEEN 0 AND 100);
-- 0 = no context ("retain facade" with no explanation)
-- 50 = partial ("for heritage" but no significance)
-- 100 = complete ("Rathgael Estate 1910 subdivision...")
-- WHY useful: Drives enrichment API decisions, completeness badges

missing_context_types TEXT[];
-- Example: ['significance', 'alternatives', 'assessment_criteria']
-- WHY useful: Smart enrichment (fetch only what's missing)

enrichment_available BOOLEAN;
-- Can we enrich this from LEP/heritage studies?
-- WHY useful: Pre-computed flag for UI rendering decisions

recommended_external_resources JSONB;
-- Example: [
--   {"type": "lep_schedule", "clause": "Schedule 5 Item 27", "relevance": "high"},
--   {"type": "heritage_study", "url": "...", "relevance": "moderate"}
-- ]
-- WHY useful: One-click access to supplementary info
```

### Strategic Future Fields (P2):

#### Professional Intelligence
```sql
-- Strategic advice
professional_tip TEXT;
-- Example: "Ashfield typically requires heritage architect report for this"
-- WHY useful: Professional-grade insider knowledge
-- Source: Could crowd-source from certifiers/architects over time

typical_variation_examples TEXT;
-- Example: "Reduced setback accepted when screening landscaping provided"
-- WHY useful: Shows "here's how others got approval for alternative"
-- Source: Manual curation from approved DAs

common_non_compliances TEXT;
-- Example: "Applicants often forget to include shadow diagrams"
-- WHY useful: Proactive guidance ("don't forget X!")
-- Source: Could extract from refusal reasons in Planning Portal

assessment_criteria TEXT;
-- Example: "Council assesses based on visual impact from street"
-- WHY useful: Helps users understand HOW compliance is judged
-- Source: Could extract from "Objectives" sections or DCP explanatory text
```

#### ML/Analytics Enablement (P3)
```sql
-- For future ML features
embedding_vector VECTOR(1536);
-- Semantic similarity search for "requirements like this"
-- WHY useful: "Similar requirements in other councils", recommendation engine

nlp_extracted_entities JSONB;
-- Example: {"materials": ["brick", "tile"], "dimensions": ["6m", "0.9m"], "conditions": ["heritage", "corner lot"]}
-- WHY useful: Structured querying, smart filtering

user_query_matches TEXT[];
-- Natural language queries this requirement matches
-- Example: ["front setback", "distance from street", "boundary setback"]
-- WHY useful: Search relevance, query expansion
```

---

## 2. Heritage Conservation Areas Table

### Currently Have (P0):
```sql
✅ h_name TEXT
✅ significance TEXT
✅ lga_name VARCHAR
✅ geometry_json JSONB
✅ bbox coordinates
```

### Should Add Immediately (P1):

```sql
-- Detailed significance
significance_statement_full TEXT;
-- Full text vs abbreviated "Local"
-- WHY useful: Rich enrichment vs "see LEP" link

heritage_values JSONB;
-- Example: {
--   "architectural": ["Federation details", "original fabric"],
--   "historical": ["1910 subdivision", "railway development"],
--   "social": ["community landmark"],
--   "rarity": ["intact streetscape"]
-- }
-- WHY useful: Structured "why it matters" for users

-- Practical guidance
typical_heritage_controls TEXT[];
-- Example: ["retain_facade", "match_materials", "respect_scale"]
-- WHY useful: "Properties in this HCA typically must..."

contributory_elements TEXT[];
-- Example: ["original roof form", "front fence", "street trees"]
-- WHY useful: "These elements contribute to significance (can't change)"

non_contributory_elements TEXT[];
-- Example: ["rear additions", "carports", "modern windows at rear"]
-- WHY useful: "These don't contribute (more flexibility)"

heritage_advisor_typically_required BOOLEAN;
-- Does council usually require heritage consultant for this HCA?
-- WHY useful: Budget/timeline planning

-- Reference material
heritage_study_reference TEXT;
-- Link to detailed heritage study
-- WHY useful: Deep dive for professionals

heritage_study_year INTEGER;
-- When was the study done?
-- WHY useful: Currency/relevance indicator
```

### Strategic Future Fields (P2):

```sql
-- Approval intelligence
typical_approval_conditions TEXT[];
-- Example: ["Heritage Interpretation Plan", "Archival recording", "Materials schedule"]
-- WHY useful: "Expect these DA conditions"
-- Source: Manual curation from approved DAs in this HCA

notable_precedent_das JSONB;
-- Example: [
--   {"da_number": "DA/2023/0123", "summary": "Rear addition approved", "key_factors": "..."},
--   {"da_number": "DA/2023/0456", "summary": "Demolition refused", "key_factors": "..."}
-- ]
-- WHY useful: "Here's what worked/didn't work in your HCA"
-- Source: Planning Portal DA search + manual curation

common_heritage_issues TEXT;
-- Example: "Overly large additions dominating original building"
-- WHY useful: "Avoid this common mistake"
```

---

## 3. Council Compliance Profiles Table (NEW)

### Essential Structure (P1):

```sql
CREATE TABLE council_compliance_profiles (
  id SERIAL PRIMARY KEY,

  -- Identity
  council_name VARCHAR(100) NOT NULL UNIQUE,
  former_council_of VARCHAR(100), -- "Inner West"

  -- Compliance personality
  compliance_style VARCHAR(50) NOT NULL, -- prescriptive | performance | process | hybrid
  strictness_level VARCHAR(20) NOT NULL, -- low | moderate | high

  -- Quantitative metrics (auto-calculated)
  heritage_context_pct DECIMAL(5,2) NOT NULL,
  allows_alternatives_pct DECIMAL(5,2) NOT NULL,
  objectives_coverage_pct DECIMAL(5,2) NOT NULL,
  prescriptiveness_avg_score INTEGER, -- Average of all requirements

  -- User guidance
  strategy_guidance TEXT NOT NULL,
  enrichment_priority VARCHAR(20) NOT NULL, -- low | moderate | high

  -- Professional intelligence (P2)
  typical_assessment_time_days INTEGER,
  -- Example: Ashfield = 60 days, Marrickville = 45 days
  -- WHY useful: Timeline planning

  pre_da_consultation_recommended BOOLEAN,
  -- Should users do pre-DA meeting?
  -- WHY useful: Process guidance

  planning_focus_areas TEXT[],
  -- Example: ["heritage_conservation", "sustainability", "affordable_housing"]
  -- WHY useful: "This council emphasizes X"

  common_refusal_reasons TEXT[],
  -- Example: ["insufficient_setbacks", "heritage_impact", "overdevelopment"]
  -- WHY useful: "Watch out for these"

  approval_rate_pct DECIMAL(5,2),
  -- % of DAs approved (if available from open data)
  -- WHY useful: Difficulty gauge

  -- Metadata
  last_calculated TIMESTAMP NOT NULL,
  data_version VARCHAR(20) -- "v2_compliant"
);
```

### Strategic Future Fields (P3):

```sql
-- Advanced analytics
design_excellence_required_threshold JSONB;
-- Example: {"min_height_m": 21, "zones": ["B4"], "or_fsr": 2.5}
-- WHY useful: "Your project triggers design excellence"

heritage_architect_required_when TEXT[];
-- Example: ["hca_alterations", "heritage_item_within_10m", "demolition"]
-- WHY useful: "You'll need specialist for this"

notable_planning_decisions TEXT;
-- Recent interesting/controversial decisions
-- WHY useful: Shows council's current priorities

council_character_keywords TEXT[];
-- Example: ["rigorous", "collaborative", "sustainability-focused"]
-- WHY useful: Setting expectations
```

---

## 4. Requirement Enrichment Metadata (NEW)

### Purpose: Track enrichment status and sources

```sql
CREATE TABLE requirement_enrichment_metadata (
  id SERIAL PRIMARY KEY,
  requirement_id INTEGER NOT NULL REFERENCES dcp_general_requirements(id),

  -- Enrichment status
  needs_enrichment BOOLEAN NOT NULL,
  enrichment_available BOOLEAN NOT NULL,
  enrichment_last_checked TIMESTAMP,

  -- Sources
  lep_provision_id INTEGER REFERENCES regulatory_provisions(id),
  hca_id INTEGER REFERENCES heritage_conservation_areas(id),
  heritage_study_reference TEXT,
  nsw_heritage_db_id VARCHAR(50),

  -- Quality scoring
  original_context_score INTEGER CHECK (original_context_score BETWEEN 0 AND 100),
  enriched_context_score INTEGER CHECK (enriched_context_score BETWEEN 0 AND 100),

  -- User experience
  display_strategy VARCHAR(50),
  -- Values: 'show_dcp_only' | 'show_dcp_plus_lep' | 'show_lep_prominent' | 'show_external_link'

  confidence_badge VARCHAR(50),
  -- Values: 'complete_info' | 'supplemented_with_lep' | 'external_source_recommended'

  -- Cache
  enrichment_cache JSONB,
  cache_expiry TIMESTAMP
);
```

**WHY useful:**
- Drives smart enrichment decisions
- Tracks what's been enriched (avoid re-fetching)
- A/B testing different enrichment strategies
- Performance optimization (cached enrichment)

---

## 5. Alternative Solutions Library (NEW - P2)

### Purpose: Precedent database for "here's how others got approval"

```sql
CREATE TABLE alternative_solutions_library (
  id SERIAL PRIMARY KEY,

  -- Requirement context
  requirement_category VARCHAR(100) NOT NULL,
  standard_requirement TEXT NOT NULL,
  -- Example: "6.0m front setback required"

  -- Alternative approach
  alternative_approach TEXT NOT NULL,
  -- Example: "4.5m setback with screening landscaping"

  acceptance_criteria TEXT NOT NULL,
  -- Example: "Demonstrate visual privacy maintained through 2m+ hedge"

  -- Validation
  precedent_da_number VARCHAR(50),
  precedent_council VARCHAR(100) NOT NULL,
  approval_date DATE,

  -- Case study
  case_study_summary TEXT,
  case_study_images TEXT[], -- URLs

  -- Searchability
  tags TEXT[],
  applicable_zones TEXT[],
  applicable_development_types TEXT[]
);
```

**WHY useful:**
- "X other applicants got approval with Y approach"
- Shows real-world flexibility vs theoretical
- Builds user confidence
- Could become a paid "pro tier" feature

**Source:** Manual curation from Planning Portal DAs over time

---

## 6. Cross-Council Comparison Data (NEW - P3)

### Purpose: Enable "council comparison" features

```sql
CREATE TABLE requirement_cross_council_comparison (
  id SERIAL PRIMARY KEY,

  -- Standardized requirement type
  requirement_type_standardized VARCHAR(100) NOT NULL,
  -- Example: "front_setback_residential"

  -- Per-council data
  marrickville_requirement_id INTEGER REFERENCES dcp_general_requirements(id),
  marrickville_rule TEXT,
  marrickville_context_richness INTEGER, -- 0-100
  marrickville_flexibility INTEGER, -- 0-100

  ashfield_requirement_id INTEGER REFERENCES dcp_general_requirements(id),
  ashfield_rule TEXT,
  ashfield_context_richness INTEGER,
  ashfield_flexibility INTEGER,

  leichhardt_requirement_id INTEGER REFERENCES dcp_general_requirements(id),
  leichhardt_rule TEXT,
  leichhardt_context_richness INTEGER,
  leichhardt_flexibility INTEGER,

  -- Comparison metadata
  variation_magnitude VARCHAR(20), -- low | moderate | high
  most_prescriptive_council VARCHAR(100),
  most_flexible_council VARCHAR(100),

  -- User value
  comparison_insight TEXT,
  -- Example: "Marrickville allows 4.5m, Ashfield requires 6m, Leichhardt allows 'appropriate setback'"

  created_at TIMESTAMP DEFAULT NOW()
);
```

**WHY useful:**
- "How does my council compare?" feature
- Shows regional variations in planning approach
- Helps users understand if their council is stricter/more flexible than neighbors
- Could enable "council shopping" insights for developers

**Source:** Manual curation across councils (one-time effort, high value)

---

## 7. User Interaction Analytics (NEW - P3)

### Purpose: Learn from user behavior to improve recommendations

```sql
CREATE TABLE user_interaction_analytics (
  id SERIAL PRIMARY KEY,

  -- Interaction context
  session_id VARCHAR(100) NOT NULL,
  property_address TEXT,
  development_type VARCHAR(100),
  council VARCHAR(100),

  -- User behavior
  requirements_viewed INTEGER[],
  -- Which requirement IDs did user view?

  time_spent_per_requirement JSONB,
  -- Example: {"12345": 45, "12346": 120} (seconds)

  clicked_pdf_links INTEGER[],
  clicked_lep_enrichment_links INTEGER[],
  clicked_alternative_solutions INTEGER[],

  -- Outcome
  user_expressed_confusion BOOLEAN,
  user_requested_clarification INTEGER,
  -- Which requirement ID confused them?

  compliance_strategy_selected VARCHAR(50),
  -- "strict_compliance" | "performance_based" | "seek_variation"

  -- Metadata
  interaction_timestamp TIMESTAMP DEFAULT NOW()
);
```

**WHY useful:**
- A/B testing enrichment strategies
- Identify confusing requirements (improve UX)
- Learn which requirements users spend most time on (prioritize enrichment)
- Understand user compliance strategies (adapt UI recommendations)

**Privacy:** Anonymized, no PII, session-based only

---

## 8. Implementation Priority Matrix

### Immediate (Next 2-4 weeks):

| Field | Table | Priority | Effort | Value |
|-------|-------|----------|--------|-------|
| `prescriptiveness_score` | dcp_requirements | P1 | 2-3 hours | HIGH |
| `user_action_type` | dcp_requirements | P1 | 2-3 hours | HIGH |
| `context_completeness_score` | dcp_requirements | P1 | 4-6 hours | HIGH |
| `enrichment_available` | dcp_requirements | P1 | 1-2 hours | HIGH |
| `significance_statement_full` | heritage_areas | P1 | 4-6 hours | HIGH |
| `heritage_values` | heritage_areas | P1 | 6-8 hours | VERY HIGH |

**Total effort:** 20-28 hours (1-2 weeks)

### Short-term (Next 1-3 months):

| Field | Table | Priority | Effort | Value |
|-------|-------|----------|--------|-------|
| `compliance_difficulty` | dcp_requirements | P1 | 4-6 hours | MODERATE |
| `related_provision_ids` | dcp_requirements | P1 | 8-10 hours | HIGH |
| `typical_heritage_controls` | heritage_areas | P1 | 10-12 hours | HIGH |
| Council profiles table | NEW | P1 | 12-16 hours | VERY HIGH |
| Enrichment metadata table | NEW | P1 | 8-10 hours | HIGH |

**Total effort:** 42-54 hours (3-4 weeks)

### Strategic (Next 3-6 months):

| Field | Table | Priority | Effort | Value |
|-------|-------|----------|--------|-------|
| `professional_tip` | dcp_requirements | P2 | 20-30 hours | HIGH |
| `typical_variation_examples` | dcp_requirements | P2 | 20-30 hours | HIGH |
| Alternative solutions library | NEW | P2 | 40-60 hours | VERY HIGH |
| `notable_precedent_das` | heritage_areas | P2 | 30-40 hours | HIGH |
| Cross-council comparison | NEW | P3 | 60-80 hours | MODERATE |

**Total effort:** 170-240 hours (6-8 weeks)

---

## 9. Field Computation Strategies

### Auto-Computable (via code):

**`prescriptiveness_score`:**
```python
def calculate_prescriptiveness(provision_text):
    must_count = text.lower().count('must') + text.lower().count('required')
    may_count = text.lower().count('may') + text.lower().count('should')
    numeric_specs = len(re.findall(r'\d+\.?\d*\s*m', text))

    score = 50  # baseline
    score += must_count * 10
    score -= may_count * 5
    score += numeric_specs * 5
    return min(max(score, 0), 100)
```

**`context_completeness_score`:**
```python
def calculate_context_completeness(requirement):
    score = 0
    if requirement.heritage_context: score += 30
    if requirement.objective: score += 25
    if requirement.performance_criteria: score += 25
    if requirement.allows_alternative_solutions: score += 20
    return score
```

**`enrichment_available`:**
```python
def check_enrichment_available(requirement, hca_table, lep_table):
    if requirement.category != 'heritage':
        return False
    if requirement.heritage_context and len(requirement.heritage_context) > 200:
        return False  # Already rich
    # Check if property in HCA with LEP provision
    return property_in_hca_with_lep(requirement.property_address)
```

### Manual Curation Required:

**`professional_tip`:**
- Source: Interview certifiers, architects, council planners
- Method: Manual entry during requirement review
- Frequency: Quarterly updates

**`typical_variation_examples`:**
- Source: Approved DA search on Planning Portal
- Method: Manual extraction + summarization
- Frequency: Bi-annual updates

**`heritage_values` (structured):**
- Source: Heritage studies, LEP schedules
- Method: One-time structured extraction + manual verification
- Frequency: Update when heritage studies revised

### ML/LLM-Assisted:

**`user_action_type` (initial classification):**
```python
# LLM prompt
prompt = f"""
Classify this planning requirement into ONE category:
- design_requirement: Specifies how to design (setbacks, materials, height)
- da_submission: Specifies what to submit with DA (reports, plans)
- informational: Background info (objectives, context)
- consultation_trigger: Requires consultation with council/agency

Requirement: {requirement.provision_text}
Category:
"""
```

**`compliance_difficulty`:**
```python
# LLM analysis of complexity
prompt = f"""
Rate compliance difficulty (straightforward/moderate/complex/specialist_required):
Factors:
- Number of conditions: {condition_count}
- Cross-references: {cross_ref_count}
- Technical terms: {technical_term_count}
- Requirement text: {requirement.provision_text}

Difficulty:
"""
```

**`comparison_insight`:**
```python
# LLM synthesis
prompt = f"""
Summarize the key difference between these 3 council requirements:
- Marrickville: {marr_rule}
- Ashfield: {ash_rule}
- Leichhardt: {leich_rule}

Insight (1 sentence):
"""
```

---

## 10. Quick Wins vs Long-Term Strategy

### Quick Wins (Capture NOW, minimal effort):

1. **Add columns today (< 4 hours total):**
   ```sql
   ALTER TABLE dcp_general_requirements
     ADD COLUMN prescriptiveness_score INTEGER,
     ADD COLUMN context_completeness_score INTEGER,
     ADD COLUMN enrichment_available BOOLEAN DEFAULT FALSE;

   ALTER TABLE heritage_conservation_areas
     ADD COLUMN significance_statement_full TEXT,
     ADD COLUMN heritage_values JSONB;
   ```

2. **Compute initial values (< 8 hours):**
   - Run `calculate_prescriptiveness()` on all requirements
   - Run `calculate_context_completeness()` on all requirements
   - Run `check_enrichment_available()` for heritage requirements
   - Backfill scores in batch

3. **Create council profiles table (< 16 hours):**
   - Schema already designed (see Section 3)
   - Populate from existing quality metrics
   - Compute averages from dcp_general_requirements

**Total quick win effort: 28 hours (1 week)**

### Long-Term Strategic Captures (Phase 2+):

**Professional intelligence fields:**
- Build precedent database over 6-12 months
- Interview professionals quarterly
- Curate approved DA examples

**ML/Analytics fields:**
- Add embedding vectors when implementing semantic search
- Add NLP entities when building smart filters
- Add user interaction tracking when deploying analytics

**Cross-council comparison:**
- Implement after all councils extracted
- Requires standardization layer
- Manual curation for ~100 common requirement types

---

## 11. Summary Recommendations

### Must Capture NOW (Before v1 Launch):

**Tier 1 - User Experience Fields:**
```sql
-- Add to dcp_general_requirements
ALTER TABLE dcp_general_requirements
  ADD COLUMN prescriptiveness_score INTEGER CHECK (prescriptiveness_score BETWEEN 0 AND 100),
  ADD COLUMN user_action_type VARCHAR(50),
  ADD COLUMN context_completeness_score INTEGER CHECK (context_completeness_score BETWEEN 0 AND 100),
  ADD COLUMN enrichment_available BOOLEAN DEFAULT FALSE;
```

**Tier 2 - Enrichment Infrastructure:**
```sql
-- Create council profiles table (enables UX strategy)
CREATE TABLE council_compliance_profiles (...);  -- See Section 3

-- Create enrichment metadata table (enables smart LEP enrichment)
CREATE TABLE requirement_enrichment_metadata (...);  -- See Section 4
```

**Tier 3 - Heritage Enhancement:**
```sql
-- Add to heritage_conservation_areas
ALTER TABLE heritage_conservation_areas
  ADD COLUMN significance_statement_full TEXT,
  ADD COLUMN heritage_values JSONB,
  ADD COLUMN typical_heritage_controls TEXT[],
  ADD COLUMN contributory_elements TEXT[];
```

### Should Capture in Phase 2 (Next 3-6 months):

1. **Alternative Solutions Library** - Precedent database
2. **Professional Tips** - Certifier/architect insights
3. **Traceability Fields** - Cross-reference linking
4. **Analytics Infrastructure** - User interaction tracking

### Can Wait for Phase 3+ (Future):

1. **Cross-Council Comparison** - After all NSW councils extracted
2. **ML Features** - Embeddings, NLP entities
3. **Approval Intelligence** - Typical conditions, refusal reasons

---

## 12. Risk of NOT Capturing These Fields

### Critical Risks (Capture NOW):

**`prescriptiveness_score` not captured:**
- **Impact:** Users can't filter by compliance approach
- **Result:** Overwhelmed by 100+ requirements without guidance
- **Cost to fix later:** Requires re-processing all provisions

**`enrichment_available` not captured:**
- **Impact:** Every heritage requirement triggers expensive LEP query
- **Result:** Slow API response, wasted resources
- **Cost to fix later:** Manual backfill or batch processing

**Council profiles not captured:**
- **Impact:** Users don't understand why councils differ
- **Result:** Confusion, frustration, loss of trust
- **Cost to fix later:** Minimal (can compute from existing data)

### Moderate Risks (Capture in Phase 2):

**`related_provision_ids` not captured:**
- **Impact:** Users can't explore related requirements
- **Result:** Miss dependencies, incomplete compliance
- **Cost to fix later:** LLM batch processing (~$50-100)

**Alternative solutions not captured:**
- **Impact:** Users don't know flexibility exists
- **Result:** Over-specified designs, missed opportunities
- **Cost to fix later:** Manual curation (100+ hours)

### Low Risks (Can wait):

**Cross-council comparison not built:**
- **Impact:** Power users can't benchmark councils
- **Result:** Limited strategic insights
- **Cost to fix later:** Same as now (future feature)

---

## Final Recommendations

### Do This Week:
1. Add P1 UX fields to dcp_general_requirements (4 hours)
2. Create council_compliance_profiles table (8 hours)
3. Compute initial prescriptiveness/completeness scores (8 hours)

### Do This Month:
1. Extract LEP Schedule 5 significance statements (6 hours)
2. Create requirement_enrichment_metadata table (8 hours)
3. Implement enrichment_available logic (4 hours)

### Do This Quarter:
1. Build alternative solutions library (40 hours)
2. Interview professionals for tips (20 hours)
3. Implement related_provision_ids linking (10 hours)

**Total immediate effort: 58 hours (2-3 weeks)**

**Payoff:** Professional-grade UX with intelligent enrichment that scales to all NSW councils.
