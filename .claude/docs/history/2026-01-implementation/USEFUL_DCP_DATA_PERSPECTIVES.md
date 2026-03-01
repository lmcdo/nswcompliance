# Useful DCP Data Perspectives for User Value

## Target User Workflow Analysis

### Real User Questions:
1. "Can I build dual occupancy on this site?" → **Feasibility filter**
2. "What will the council argue with me about?" → **Risk assessment**
3. "Where can I save money by arguing for variation?" → **Flexibility analysis**
4. "What do I need to submit for DA?" → **Evidence requirements**
5. "Who needs to sign off on this?" → **Approval pathway**

## Perspective 1: Requirement Flexibility Spectrum

**CRITICAL INSIGHT:** Not all requirements are equal - some are negotiable, some aren't.

### Classification:
```
ABSOLUTE (0% flexibility):
- "Maximum 2 storeys"
- "Height per LEP Map"
- NO allows_alternative_solutions
- NO performance_criteria
→ User strategy: Must comply or don't proceed

PERFORMANCE-BASED (high flexibility):
- "Maintain established character"
- HAS performance_criteria
- HAS allows_alternative_solutions
- HAS objective explaining intent
→ User strategy: Argue alternative solution if outcome met

GUIDANCE (not enforceable):
- "Council encourages view sharing"
- Words: "should", "encouraged", "consider"
- NOT mandatory language
→ User strategy: Nice to have, not critical
```

**How to exploit:**
- Tag each requirement with `flexibility_level`: "absolute", "performance", "guidance"
- Filter: "Show me only absolute requirements" → binary compliance checklist
- Filter: "Show me flexible requirements" → variation opportunity list

**Implementation:**
```json
{
  "requirement_text": "Development maintains established character",
  "flexibility_level": "performance",
  "flexibility_basis": "Performance criteria + alternative solutions allowed",
  "allows_alternative_solutions": true,
  "performance_criteria": "Character outcome achieved",
  "objective": "To maintain streetscape character"
}
```

## Perspective 2: Compliance Evidence Type

**CRITICAL INSIGHT:** Different requirements need different proof methods.

### Classification:
```
MEASURABLE (objective):
- "6m front setback" → Measure on plans with ruler
- "1 parking space per dwelling" → Count spaces
- Certifier can verify
→ Low risk, clear compliance

CALCULABLE (objective but complex):
- "FSR max 0.5:1" → Calculate floor area ÷ site area
- "Max 40% site coverage" → Calculate building footprint ÷ site area
- Requires submission of calculation
→ Medium risk, must show working

ASSESSABLE (subjective):
- "Bulk compatible with streetscape" → Merit assessment
- "Maintain established character" → Council judgment
- Requires design statement, photos, analysis
→ High risk, council discretion

REPORTABLE (specialist):
- "BASIX certificate" → Sustainability consultant
- "Acoustic report" → Acoustic engineer
- "Waste management plan" → Waste consultant
→ Cost impact, specialist required
```

**How to exploit:**
- Tag each requirement with `evidence_type`: "measurable", "calculable", "assessable", "reportable"
- Generate DA submission checklist: "You need: 3 calculations, 5 reports, 12 plans showing..."
- Cost estimation: "This project requires acoustic + waste reports = $10k consultants"

**Implementation:**
```json
{
  "requirement_text": "FSR maximum 0.5:1 per MLEP 2011",
  "evidence_type": "calculable",
  "evidence_required": "FSR calculation showing: GFA ÷ site area ≤ 0.5",
  "assessed_by": "certifier",
  "risk_level": "low"
},
{
  "requirement_text": "Development compatible with streetscape character",
  "evidence_type": "assessable",
  "evidence_required": "Design statement + streetscape photos + character analysis",
  "assessed_by": "council_planner",
  "risk_level": "high"
}
```

## Perspective 3: Approval Pathway Impact

**CRITICAL INSIGHT:** Some requirements determine HOW you get approval (certifier vs council).

### Classification:
```
COMPLYING DEVELOPMENT ELIGIBLE:
- ALL numeric requirements met
- NO merit assessment needed
- NO variations required
→ Certifier approval (~4 weeks, cheaper)

DA REQUIRED - STRAIGHTFORWARD:
- Minor variation OR single merit item
- Clear compliance otherwise
→ Council approval (~8-12 weeks, standard cost)

DA REQUIRED - COMPLEX:
- Multiple variations OR heritage OR major merit
- Significant council discretion
→ Council approval (~12-20 weeks, expensive, risky)

PROHIBITED:
- Breaches absolute requirement with no variation pathway
→ Refusal certain, don't proceed
```

**How to exploit:**
- Flag requirements that "kill complying development pathway"
- Example: "Dual occupancy on 400m² lot (min 450m² required)" → DA required
- Calculate approval pathway automatically based on site + proposal

**Implementation:**
```json
{
  "requirement_text": "Minimum lot size: 450m²",
  "value_min": 450,
  "unit": "sqm",
  "blocks_complying_dev": true,
  "variation_possible": false,
  "approval_impact": "If breached: DA required, complying dev not available"
}
```

## Perspective 4: Conditional Applicability Logic

**CRITICAL INSIGHT:** Requirements have complex conditional logic that can be parsed.

### Current State:
```json
{
  "conditional_text": "for corner lots where there is consistent secondary boundary setback"
}
```

### Enhanced Structure:
```json
{
  "conditional_text": "for corner lots where there is consistent secondary boundary setback",
  "conditions": [
    {
      "type": "site_characteristic",
      "criterion": "corner_lot",
      "value": true
    },
    {
      "type": "context_characteristic",
      "criterion": "secondary_boundary_pattern_exists",
      "value": true
    }
  ],
  "applies_to_address": null  // Populated when address known
}
```

**How to exploit:**
- Parse conditionals into structured logic
- Filter: "This is a corner lot" → auto-show only corner lot requirements
- Filter: "Not in HCA" → hide all HCA requirements
- Smart filtering reduces cognitive load dramatically

## Perspective 5: Requirement Relationship Mapping

**CRITICAL INSIGHT:** Requirements don't exist in isolation - they interact and conflict.

### Relationship Types:

**SUPPORTS (helps meet other requirement):**
- Deep soil planting → helps meet landscaping requirement
- Building setback → helps meet solar access requirement

**CONFLICTS (competing requirements):**
- Large setbacks → reduces site coverage available
- Parking spaces → consumes deep soil area
- Must balance competing demands

**DEPENDS ON (prerequisite):**
- "Upper floor setback" depends on "building has upper floor"
- "Secondary dwelling rules" depend on "primary dwelling exists"

**SUPERSEDES (hierarchy):**
- SEPP > DCP for same topic
- LEP > DCP for same topic

**How to exploit:**
- Show user: "Meeting this parking requirement will consume 40m² (conflicts with deep soil 30m² requirement)"
- Warn: "To meet both parking + deep soil, you need minimum 600m² site"
- Smart requirement bundling for decision-making

**Implementation:**
```json
{
  "requirement_text": "Minimum 2 parking spaces for dual occupancy",
  "conflicts_with": [
    {
      "requirement_id": 1234,
      "requirement": "Minimum 30m² deep soil",
      "conflict_type": "competes_for_space",
      "resolution": "Need sufficient site area for both (600m² minimum recommended)"
    }
  ]
}
```

## Perspective 6: Cost/Value Impact Tags

**CRITICAL INSIGHT:** Some requirements have massive cost impacts, others don't.

### Classification:
```
HIGH COST IMPACT:
- Parking (basement): $40-80k per space
- Heritage controls: 50-200% cost premium
- Acoustic requirements: $15-30k consultant + construction
- Deep soil on podium: $500-1000/m² vs $50/m² ground level

MEDIUM COST IMPACT:
- Setback variations: reduce sellable area → revenue loss
- Landscaping: $200-500/m²
- Fencing: $200-500/m

LOW COST IMPACT:
- Paint colors: minimal
- Window types: standard vs premium 10-20% difference
```

**How to exploit:**
- Tag: `cost_impact_level`: "high", "medium", "low"
- Flag: "These 3 requirements will add $150k to project cost"
- Prioritize: "Focus design effort on varying these high-cost requirements"

## Perspective 7: Temporal/Transition Provisions

**CRITICAL INSIGHT:** When requirements changed affects existing buildings.

### Scenarios:
```
EXISTING BUILDING (pre-2022):
- Built under Marrickville DCP 2011
- Alterations assessed under Inner West LEP 2022 + DCP
- May not meet current standards but "existing" is acceptable

NEW DEVELOPMENT (post-2022):
- Must meet all current requirements
- No grandfathering

TRANSITION PROVISIONS:
- "Development applications lodged before [date]..."
- Important for projects in progress
```

**How to exploit:**
- Tag requirements with `introduced_date`, `applies_to`
- Filter: "Show me only requirements for alterations to existing dwellings"
- Separate pathway: new build vs alterations + additions

## Perspective 8: Professional Involvement Required

**CRITICAL INSIGHT:** Different requirements need different specialists.

### Professional Tags:
```
ARCHITECT/DESIGNER:
- Building form, setbacks, character

TOWN PLANNER:
- Zoning compliance, DA lodgement, council liaison

CERTIFIER:
- BCA compliance, construction compliance

HERITAGE ARCHITECT:
- Heritage item alterations, HCA design

LANDSCAPE ARCHITECT:
- Landscaping plans, tree reports

ACOUSTIC ENGINEER:
- Noise reports (mixed use, near rail, etc.)

WASTE CONSULTANT:
- Waste management plans

BASIX ASSESSOR:
- Sustainability certificates

SURVEYOR:
- Site dimensions, setback certification
```

**How to exploit:**
- Tag requirements with `specialist_required`: ["architect", "acoustic_engineer"]
- Cost estimation: "This project needs architect + planner + acoustic = $50k consultants"
- Team assembly: Auto-suggest which professionals to engage

## Perspective 9: Multi-Dimensional Filtering

**CRITICAL INSIGHT:** Users need to slice data multiple ways simultaneously.

### Filter Dimensions:
```
1. Address/Site → determines zone, HCA, precinct
2. Development Type → filters applicable requirements
3. Category → groups by topic (setbacks, parking, etc.)
4. Flexibility → shows negotiable vs absolute
5. Evidence Type → groups by proof method
6. Cost Impact → prioritizes high-impact items
7. Specialist Required → identifies team needs
8. Approval Pathway → determines process
```

**How to exploit:**
- Combined filters: "Show me flexible, high-cost requirements for dual occupancy in R2 zone"
- Returns: 8 requirements where variation argument could save $100k+
- Strategic focus: Spend design effort where it matters most

## Perspective 10: Requirement Hierarchy Visualization

**CRITICAL INSIGHT:** Requirements have parent-child relationships.

### Structure:
```
Section 4.1.6 Built form and character
├── Objectives (context)
│   ├── O10: Scale and form enhances streetscape
│   └── O11: Period dwellings - character preservation
│
├── C7: Maximum FSR/height per LEP (ABSOLUTE)
│
├── C8: Demonstrate acceptable bulk/mass (PERFORMANCE)
│   ├── C8i: Overshadowing/privacy
│   ├── C8ii: Streetscape bulk/scale
│   ├── C8iii: Building setbacks
│   ├── C8iv: Parking/landscape
│   ├── C8v: Views
│   ├── C8vi: Significant trees
│   └── C8vii: Lot size/shape/topography
│
└── C10: Building setbacks (CONDITIONAL)
    ├── C10i: Front setback
    │   ├── C10ia: Match adjoining (corner lots)
    │   └── C10ib: Match secondary pattern (corner lots)
    ├── C10ii: Side setback per table
    └── C10iii: Rear setback
```

**How to exploit:**
- Tree view for navigation
- Show parent objective when viewing child requirement
- "Why is this required?" → link to objective explains intent
- Enables variation arguments: "I meet O11 (character) via alternative to C10ia (setback)"

## Implementation Priority

### Phase 1 (Immediate - Can extract now):
1. ✅ Flexibility tags (`allows_alternative_solutions`, `performance_criteria`)
2. ✅ Numeric vs qualitative (`value_numeric` present/absent)
3. ✅ Conditional logic (`has_conditionals`, `conditional_text`)
4. ✅ Development type filtering (`development_types`)
5. ✅ Category grouping (`category`, `subcategory`)

### Phase 2 (Enhanced - Needs new extraction fields):
1. Evidence type classification
2. Cost impact tagging
3. Specialist requirement tagging
4. Approval pathway impact flags
5. Flexibility level scoring

### Phase 3 (Advanced - Needs relationship analysis):
1. Requirement conflict detection
2. Dependency mapping
3. Cross-reference linking
4. Cumulative impact calculation

## User Experience Examples

### Example 1: Architect designing dual occupancy

**Query:** "What requirements apply to dual occupancy on 40 Lackey St?"

**System returns:**
- 47 requirements total
- Filtered by: `development_types: ["dual_occupancy"]` AND address zone
- Grouped by: category (setbacks: 8, parking: 3, landscaping: 5, etc.)
- Flagged: 3 high-cost requirements (parking, deep soil, heritage)
- Tagged: 2 require specialist (acoustic, heritage)
- Highlighted: 5 have flexibility for variation

**User sees:**
- "✅ 35 straightforward requirements (certifier can assess)"
- "⚠️ 8 merit-based requirements (council assessment needed)"
- "💰 3 high-cost requirements ($120k impact)"
- "👥 Specialists needed: Heritage architect, Acoustic engineer"
- "📋 Evidence: 12 plans, 3 calculations, 2 reports"

### Example 2: Developer feasibility analysis

**Query:** "Can I vary the front setback from 6m to 4.5m?"

**System analyzes:**
- Requirement: C10ia - Front setback 6m
- Flexibility: `allows_alternative_solutions: true`
- Objective: O11 - "Maintain garden setting character"
- Performance criteria: "Sufficient landscaping buffer"
- Alternative criteria: "Demonstrate character compatibility + equivalent landscaping"

**User sees:**
- "✅ Variation possible if you demonstrate:"
  - "1. Character compatibility (photos + analysis)"
  - "2. Equivalent landscaping outcome (landscape plan)"
  - "3. Justification against O11 objective"
- "📊 Success probability: Medium (subjective assessment)"
- "💼 Recommend: Engage heritage consultant for statement"

## Summary

**Most Valuable Perspectives:**

1. **Flexibility spectrum** → Tells user what's negotiable
2. **Evidence requirements** → Tells user what to submit
3. **Cost impact** → Tells user where money matters
4. **Approval pathway** → Tells user certifier vs council
5. **Conditional logic** → Filters irrelevant requirements
6. **Professional involvement** → Tells user who to hire
7. **Requirement relationships** → Warns about conflicts

**Key Insight:** Raw requirement text is necessary but not sufficient. The META-INFORMATION about requirements (flexibility, cost, evidence, relationships) is what enables smart decision-making.
