# AI Layer Architecture: Data Flow, Templates & UI

**Purpose:** Explain exactly how LLM + data + templates work together, and how UI displays results
**Date:** 2026-02-01

---

## EXECUTIVE SUMMARY

**Key Principle:** LLM is used ONLY for question classification. Everything else is deterministic.

```
User Question
    ↓
[LLM: Classify question] ← ONLY LLM USAGE
    ↓
Route to appropriate workflow
    ↓
[Deterministic: Fetch data from DB/API] ← NO LLM
    ↓
[Deterministic: Apply business logic] ← NO LLM
    ↓
[Template: Format response] ← NO LLM (string templates, not generation)
    ↓
UI Display (progressive disclosure)
```

**LLM Usage:** <5% of process (classification only)
**Deterministic Logic:** >95% of process (data retrieval, calculations, templates)

---

# PART 1: COMPLETE DATA FLOW (Example: "Can I build a granny flat?")

## Step 1: User Input → LLM Classification (ONLY LLM STEP)

**User Question:**
```
"Can I build a granny flat at 123 Main St Marrickville?"
```

**LLM Classification (Gemini Flash):**
```typescript
// frontend-nextjs/app/api/ai/chat/route.ts

export async function POST(request: Request) {
  const { message, propertyContext } = await request.json();

  // STEP 1: LLM classifies question (ONLY LLM usage)
  const classification = await classifyQuestion(message, propertyContext);

  // classification = {
  //   category: 'granny_flat_eligibility',
  //   confidence: 0.92,
  //   parameters: { address: '123 Main St Marrickville' }
  // }

  if (classification.confidence < 0.5) {
    return clarificationResponse("I'm not sure what you're asking. Could you rephrase?");
  }

  // STEP 2: Route to appropriate workflow (NO LLM)
  const workflow = routeToWorkflow(classification.category);

  // workflow = GrannyFlatEligibilityWorkflow

  // STEP 3: Execute workflow (NO LLM - all deterministic)
  const result = await workflow.execute(classification.parameters);

  return Response.json(result);
}

// LLM Classification Function (ONLY place LLM is used)
async function classifyQuestion(message: string, context: PropertyContext) {
  const prompt = `
You are a planning regulation question classifier.

User question: "${message}"
Property context: ${JSON.stringify(context)}

Classify this question into ONE of these categories:
1. granny_flat_eligibility - User asking if granny flat is permitted/viable
2. permissibility_check - User asking if development type is permitted
3. parking_calculation - User asking about parking requirements
4. setback_requirements - User asking about setbacks
5. height_fsr_limits - User asking about height or FSR
6. heritage_constraints - User asking about heritage restrictions
7. out_of_scope - Professional judgment question (refuse to answer)

Output JSON only: { "category": "...", "confidence": 0-1, "parameters": {...} }
`;

  const response = await gemini.generateContent(prompt);
  const parsed = JSON.parse(response.text);

  return {
    category: parsed.category,
    confidence: parsed.confidence,
    parameters: { address: context.address, ...parsed.parameters }
  };
}
```

**LLM Output:**
```json
{
  "category": "granny_flat_eligibility",
  "confidence": 0.92,
  "parameters": {
    "address": "123 Main St Marrickville"
  }
}
```

**LLM is DONE at this point.** Everything below is deterministic.

---

## Step 2: Route to Workflow (NO LLM - just routing logic)

```typescript
// frontend-nextjs/lib/ai/workflow-router.ts

function routeToWorkflow(category: string): Workflow {
  const workflows = {
    'granny_flat_eligibility': GrannyFlatEligibilityWorkflow,
    'permissibility_check': PermissibilityWorkflow,
    'parking_calculation': ParkingCalculationWorkflow,
    'setback_requirements': SetbackWorkflow,
    // ... etc
  };

  return workflows[category] || RefusalWorkflow;
}
```

**No LLM here** - just a lookup table.

---

## Step 3: Execute Workflow (NO LLM - all data fetching & logic)

```typescript
// frontend-nextjs/lib/ai/workflows/granny-flat-eligibility.ts

export class GrannyFlatEligibilityWorkflow {
  async execute(params: { address: string }): Promise<WorkflowResult> {
    // STEP 3A: Fetch data from multiple sources (parallel, NO LLM)
    const [zone, lotDimensions, dwelling, parking, heritage] = await Promise.all([
      this.planningPortal.getZone(params.address),           // API call
      this.planningPortal.getLotDimensions(params.address),   // API call
      this.planningPortal.hasExistingDwelling(params.address), // API call
      this.database.getParkingRequirement('secondary_dwelling'), // DB query
      this.planningPortal.getHeritageStatus(params.address)   // API call
    ]);

    // Data returned:
    // zone = { code: 'R2', name: 'Low Density Residential' }
    // lotDimensions = { area: 612, width: 15.3, frontage: 15.3 }
    // dwelling = { exists: true, type: 'dwelling_house' }
    // parking = { required: 1, source: 'SEPP Housing 2021 Clause 38' }
    // heritage = { status: 'none' }

    // STEP 3B: Apply business logic (NO LLM - just if/else)
    const checks = this.performEligibilityChecks({
      zone,
      lotDimensions,
      dwelling,
      heritage
    });

    // checks = {
    //   zone: { pass: true, detail: 'R2 is eligible (R1-R4 permitted)' },
    //   lotSize: { pass: true, detail: '612m² ≥ 450m² minimum' },
    //   existingDwelling: { pass: true, detail: 'Existing dwelling present' },
    //   heritage: { pass: true, detail: 'Not heritage listed' }
    // }

    const eligible = Object.values(checks).every(c => c.pass);

    // STEP 3C: Format response using TEMPLATE (NO LLM - string template)
    return this.formatResponse({
      eligible,
      checks,
      parking,
      pathway: eligible ? 'CDC' : 'DA',
      nextSteps: this.generateNextSteps(eligible)
    });
  }

  performEligibilityChecks(data): EligibilityChecks {
    // Pure business logic - NO LLM
    return {
      zone: {
        pass: ['R1', 'R2', 'R3', 'R4', 'RU5'].includes(data.zone.code),
        detail: data.zone.code === 'R2'
          ? 'R2 is eligible (SEPP Housing permits in R1-R4, RU5)'
          : 'Zone not eligible for granny flats',
        source: 'SEPP Housing 2021 Division 4.1 Clause 44'
      },
      lotSize: {
        pass: data.lotDimensions.area >= 450,
        detail: `${data.lotDimensions.area}m² ${data.lotDimensions.area >= 450 ? '≥' : '<'} 450m² minimum`,
        source: 'SEPP Housing 2021 Clause 44(1)(a)'
      },
      existingDwelling: {
        pass: data.dwelling.exists,
        detail: data.dwelling.exists ? 'Existing dwelling present' : 'No existing dwelling',
        source: 'SEPP Housing 2021 Clause 44(1)(b)'
      },
      heritage: {
        pass: data.heritage.status === 'none',
        detail: data.heritage.status === 'none'
          ? 'Not heritage listed'
          : `Heritage ${data.heritage.status} - additional approval required`,
        source: 'NSW Planning Portal heritage register'
      }
    };
  }

  formatResponse(data): WorkflowResult {
    // TEMPLATE-BASED FORMATTING (NO LLM - just string concatenation)

    // This is NOT LLM generation - it's a template with slots filled in
    const template = `
${data.eligible ? '✅ YES' : '❌ NO'} - Granny flats ${data.eligible ? 'permitted' : 'not currently eligible'}

ELIGIBILITY CHECKS:

${Object.entries(data.checks).map(([key, check]) => `
${check.pass ? '✅' : '❌'} ${this.getCheckLabel(key)}: ${check.detail}
   Source: ${check.source}
`).join('\n')}

REQUIREMENTS:
• Parking: ${data.parking.required} space required
  Source: ${data.parking.source}
  Note: Not eligible for TOD reduction

• Maximum size: 60m² floor area
  Source: SEPP Housing 2021 Clause 45

APPROVAL PATHWAY:
${data.pathway === 'CDC' ? '✅ Complying Development (CDC) - 20 business days' : '⚠️ Development Application (DA) - 40 business days (statutory)'}
  ${data.pathway === 'CDC' ? 'If all design standards met' : 'Variation required - not eligible for CDC'}

NEXT STEPS:
${data.nextSteps.map(step => `• ${step}`).join('\n')}

⚠️ IMPORTANT:
This is eligibility only. Detailed design must meet all SEPP standards
(height, setbacks, landscaping). Recommend certifier consultation.
`;

    return {
      answer: template,
      sources: this.extractSources(data.checks),
      confidence: this.calculateConfidence(data.checks),
      responseTime: Date.now() - this.startTime,
      structured: data // Machine-readable version for UI
    };
  }

  generateNextSteps(eligible: boolean): string[] {
    // Deterministic logic - NO LLM
    if (eligible) {
      return [
        'Review DCP Section 4.7 (secondary dwelling design requirements)',
        'Engage private certifier for CDC assessment',
        'Prepare plans showing 1 parking space + setbacks',
        'Ensure design meets 60m² maximum size requirement'
      ];
    } else {
      return [
        'Review why eligibility criteria not met (see checks above)',
        'Consider if variation is viable (requires DA, not CDC)',
        'Consult town planner for alternative development options'
      ];
    }
  }
}
```

**Key Points:**
- **NO LLM in workflow execution** - all data fetching + logic + formatting is deterministic
- **Templates, not generation** - string concatenation, not "write me a response about granny flats"
- **Business logic is explicit** - if/else rules, not "figure it out"
- **Sources are tracked** - every statement has a citation

---

## Step 4: Template Formatting (NO LLM - String Templates)

**What Templates Look Like:**

```typescript
// frontend-nextjs/lib/ai/templates/granny-flat-response.ts

export function formatGrannyFlatResponse(data: GrannyFlatData): string {
  // This is a TEMPLATE with SLOTS (${variable})
  // NOT LLM generation

  return `
${data.eligible ? '✅ YES' : '❌ NO'} - Granny flats ${data.eligible ? 'permitted' : 'not currently eligible'}

ELIGIBILITY CHECKS:

Zone: ${data.checks.zone.pass ? '✅' : '❌'} ${data.zone.name}
  ${data.checks.zone.detail}
  Source: ${data.checks.zone.source}

Lot Size: ${data.checks.lotSize.pass ? '✅' : '❌'} ${data.lotDimensions.area}m²
  Requirement: ≥450m² minimum
  ${data.checks.lotSize.pass ? 'MEETS requirement' : 'Does NOT meet requirement'}
  Source: ${data.checks.lotSize.source}

Existing Dwelling: ${data.checks.existingDwelling.pass ? '✅' : '❌'}
  ${data.checks.existingDwelling.detail}
  Source: ${data.checks.existingDwelling.source}

Heritage: ${data.checks.heritage.pass ? '✅' : '❌'}
  ${data.checks.heritage.detail}
  Source: ${data.checks.heritage.source}

REQUIREMENTS:
• Parking: ${data.parking.required} space${data.parking.required > 1 ? 's' : ''} required
  Source: ${data.parking.source}

APPROVAL PATHWAY:
${data.pathway === 'CDC' ? '✅ Complying Development (CDC)' : '⚠️ Development Application (DA)'}
  Timeframe: ${data.pathway === 'CDC' ? '20' : '40'} business days

NEXT STEPS:
${data.nextSteps.map((step, i) => `${i + 1}. ${step}`).join('\n')}
`;
}
```

**This is NOT LLM generation.** It's just:
- String concatenation
- Conditional logic (if eligible ? "YES" : "NO")
- Variable substitution (${variable})
- Array mapping (.map())

**Comparison:**

| Approach | How It Works | Risk |
|----------|--------------|------|
| **Template (Our approach)** | `"Lot size: ${area}m² ≥ 450m² = ${pass ? 'PASS' : 'FAIL'}"` | ZERO - deterministic |
| **LLM Generation (DON'T DO)** | `gemini.generate("Write a response about granny flat eligibility with this data...")` | HIGH - hallucinations, inconsistent format |

---

## Step 5: UI Display (Progressive Disclosure)

**From UX_STRATEGY_AI_LAYER.md - Pattern 2: Contextual Information Panels**

### UI Layout (Text-Based Mockup)

```
┌─────────────────────────────────────────────────────────────────┐
│ AI Quick Reference                                        [✕]    │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│ Your question:                                                   │
│ "Can I build a granny flat?"                                    │
│                                                                   │
│ ┌───────────────────────────────────────────────────────────┐  │
│ │ ✅ YES - Granny flats permitted                           │  │
│ │                                                             │  │
│ │ Quick summary:                                             │  │
│ │ • Lot size: 612m² (✓ meets 450m² minimum)                 │  │
│ │ • Zone: R2 Low Density (✓ permitted)                      │  │
│ │ • Existing dwelling: Present (✓)                           │  │
│ │ • Heritage: Not listed (✓)                                 │  │
│ │                                                             │  │
│ │ Approval pathway: CDC (20 business days)                   │  │
│ │ Parking required: 1 space                                  │  │
│ └───────────────────────────────────────────────────────────┘  │
│                                                                   │
│ ▼ Show detailed checks (5 sources)                              │  ← COLLAPSIBLE
│                                                                   │
│ ▼ What happens next? (4 steps)                                  │  ← COLLAPSIBLE
│                                                                   │
│ ▼ View all sources (5)                                          │  ← COLLAPSIBLE
│                                                                   │
│ ─────────────────────────────────────────────────────────────── │
│                                                                   │
│ Related questions you might ask:                                │
│ • What setbacks apply to granny flats?                          │
│ • How much does a granny flat cost to build?                    │
│ • Can I rent out a granny flat?                                 │
│                                                                   │
└───────────────────────────────────────────────────────────────┘
```

### When User Clicks "▼ Show detailed checks"

```
┌─────────────────────────────────────────────────────────────────┐
│ ▲ Show detailed checks (5 sources)                              │  ← NOW EXPANDED
│                                                                   │
│ ┌───────────────────────────────────────────────────────────┐  │
│ │ ELIGIBILITY CHECKS                                          │  │
│ │                                                             │  │
│ │ ✅ Zone: R2 Low Density Residential                        │  │
│ │    Status: Permitted with consent                          │  │
│ │    Why: SEPP Housing 2021 permits granny flats in R1-R4   │  │
│ │    Source: SEPP Housing 2021 Division 4.1 Clause 44       │  │
│ │    [View provision →]                                       │  │
│ │                                                             │  │
│ │ ✅ Lot Size: 612m²                                         │  │
│ │    Requirement: ≥450m² minimum                             │  │
│ │    Status: MEETS requirement (612 > 450)                   │  │
│ │    Source: SEPP Housing 2021 Clause 44(1)(a)              │  │
│ │    [View provision →]                                       │  │
│ │                                                             │  │
│ │ ✅ Lot Width: 15.3m                                        │  │
│ │    Requirement: ≥12m minimum                               │  │
│ │    Status: MEETS requirement                               │  │
│ │    Source: SEPP Housing 2021 Clause 44(1)(a)              │  │
│ │                                                             │  │
│ │ ✅ Existing Dwelling: Present                              │  │
│ │    Type: Dwelling house (confirmed via Planning Portal)    │  │
│ │    Requirement: Must have existing dwelling on site        │  │
│ │    Source: SEPP Housing 2021 Clause 44(1)(b)              │  │
│ │                                                             │  │
│ │ ✅ Heritage: Not heritage listed                           │  │
│ │    Status: No heritage restrictions identified             │  │
│ │    Checked: Heritage item register, Conservation areas     │  │
│ │    Source: NSW Planning Portal heritage register           │  │
│ │                                                             │  │
│ │ ⚠️ Important Caveats:                                      │  │
│ │ • Detailed design must still meet all SEPP standards      │  │
│ │ • Council may have additional DCP requirements            │  │
│ │ • Recommend certifier review before proceeding            │  │
│ └───────────────────────────────────────────────────────────┘  │
│                                                                   │
└───────────────────────────────────────────────────────────────┘
```

### When User Clicks "▼ What happens next?"

```
┌─────────────────────────────────────────────────────────────────┐
│ ▲ What happens next? (4 steps)                                  │  ← NOW EXPANDED
│                                                                   │
│ ┌───────────────────────────────────────────────────────────┐  │
│ │ NEXT STEPS                                                  │  │
│ │                                                             │  │
│ │ 1. Review detailed design requirements                      │  │
│ │    □ Read DCP Section 4.7 (Secondary Dwelling Design)      │  │
│ │    □ Note setback requirements (0.9m side, 6m rear)        │  │
│ │    □ Maximum size: 60m² floor area                         │  │
│ │    [View DCP Section 4.7 →]                                 │  │
│ │                                                             │  │
│ │ 2. Prepare preliminary design                               │  │
│ │    □ Show 1 parking space (can be tandem/behind garage)    │  │
│ │    □ Ensure setbacks met                                   │  │
│ │    □ Keep floor area ≤60m²                                 │  │
│ │    Typical cost: $150,000-$200,000 construction            │  │
│ │                                                             │  │
│ │ 3. Engage private certifier                                 │  │
│ │    Why: CDC pathway requires certifier (faster than DA)    │  │
│ │    Timeframe: 20 business days from application            │  │
│ │    Cost: ~$2,000-$3,000 certifier fees                     │  │
│ │    [Find certifier →]                                       │  │
│ │                                                             │  │
│ │ 4. Submit CDC application                                   │  │
│ │    Documents needed:                                        │  │
│ │    □ Site plan                                             │  │
│ │    □ Floor plans + elevations                              │  │
│ │    □ BASIX certificate                                     │  │
│ │    □ Parking plan                                          │  │
│ │    [CDC checklist →]                                        │  │
│ └───────────────────────────────────────────────────────────┘  │
│                                                                   │
└───────────────────────────────────────────────────────────────┘
```

### When User Clicks "▼ View all sources"

```
┌─────────────────────────────────────────────────────────────────┐
│ ▲ View all sources (5)                                          │  ← NOW EXPANDED
│                                                                   │
│ ┌───────────────────────────────────────────────────────────┐  │
│ │ DATA SOURCES                                                │  │
│ │                                                             │  │
│ │ 1. SEPP Housing 2021 Division 4.1 (Granny Flats)          │  │
│ │    Clause 44: Where development permitted                  │  │
│ │    Clause 45: Development standards                        │  │
│ │    Clause 38: Parking requirements                         │  │
│ │    [View full SEPP Housing PDF →]                          │  │
│ │                                                             │  │
│ │ 2. NSW Planning Portal (Property Data)                     │  │
│ │    Retrieved: 2026-02-01 10:30am                           │  │
│ │    Data: Zone (R2), Lot dimensions (612m²), Heritage (nil) │  │
│ │    [View Planning Portal for this property →]              │  │
│ │                                                             │  │
│ │ 3. Marrickville DCP 2011 Section 4.7                       │  │
│ │    Secondary Dwelling Design Requirements                   │  │
│ │    Pages: 87-92                                            │  │
│ │    [View DCP PDF (Section 4.7) →]                          │  │
│ │                                                             │  │
│ │ 4. Inner West LEP 2022 Dictionary                          │  │
│ │    Definition: "Secondary dwelling"                         │  │
│ │    [View LEP dictionary →]                                  │  │
│ │                                                             │  │
│ │ 5. BASIX Requirements                                       │  │
│ │    Energy: 50 points minimum                               │  │
│ │    Water: 40 points minimum                                │  │
│ │    [BASIX calculator →]                                     │  │
│ │                                                             │  │
│ │ ⚠️ Data Currency:                                          │  │
│ │ All sources checked as of 2026-02-01                       │  │
│ │ Always verify with official sources before lodging         │  │
│ └───────────────────────────────────────────────────────────┘  │
│                                                                   │
└───────────────────────────────────────────────────────────────┘
```

---

# PART 2: WHERE LLM IS (AND ISN'T) USED

## LLM Usage Map

```
USER JOURNEY:

1. User types question
   ↓
2. [LLM] Classify question → category + confidence ← ONLY LLM USAGE (5% of process)
   ↓
3. [Logic] Route to workflow (if/else lookup)
   ↓
4. [API/DB] Fetch data (Planning Portal, database)
   ↓
5. [Logic] Apply business rules (if/else, calculations)
   ↓
6. [Template] Format response (string substitution)
   ↓
7. [UI] Display with progressive disclosure
   ↓
8. User clicks "Show detailed checks"
   ↓
9. [UI] Expand collapsible section (NO NEW PROCESSING)
```

**LLM Used:** Step 2 only (question classification)
**LLM NOT Used:** Steps 3-9 (everything else)

## LLM vs Deterministic Breakdown

| Step | Component | LLM? | Why/Why Not |
|------|-----------|------|-------------|
| Classification | Gemini Flash | ✅ YES | Handles natural language variation ("Can I?", "Am I allowed to?", "Is it possible to?") |
| Parameter extraction | Gemini Flash | ✅ YES | Extracts structured data from unstructured question |
| Routing | If/else logic | ❌ NO | Simple lookup table |
| Data fetching | API/DB calls | ❌ NO | Direct queries to Planning Portal + database |
| Business logic | If/else rules | ❌ NO | Explicit criteria (lot size ≥ 450m², zone in [R1,R2,R3,R4]) |
| Calculations | Math | ❌ NO | Simple arithmetic (6 units × 1 space = 6 spaces) |
| Template formatting | String concat | ❌ NO | Variable substitution, not generation |
| UI rendering | React | ❌ NO | Standard web components |

**Total Process:**
- LLM: ~2% (classification + extraction)
- Deterministic: ~98% (everything else)

---

# PART 3: TEMPLATE EXAMPLES (All Workflows)

## Template 1: Granny Flat Eligibility

```typescript
// lib/ai/templates/granny-flat.ts

export function formatGrannyFlatResponse(data: GrannyFlatData): string {
  const eligibilityIcon = data.eligible ? '✅' : '❌';
  const eligibilityText = data.eligible ? 'permitted' : 'not currently eligible';

  // Core answer (always visible)
  let response = `${eligibilityIcon} ${eligibilityText.toUpperCase()} - Granny flats ${eligibilityText}\n\n`;

  // Quick summary (always visible)
  response += `Quick summary:\n`;
  response += `• Lot size: ${data.lotSize}m² (${data.checks.lotSize.pass ? '✓' : '✗'} ${data.checks.lotSize.pass ? 'meets' : 'below'} 450m² minimum)\n`;
  response += `• Zone: ${data.zone} (${data.checks.zone.pass ? '✓ permitted' : '✗ not permitted'})\n`;
  response += `• Existing dwelling: ${data.checks.existingDwelling.pass ? '✓ Present' : '✗ Not present'}\n`;
  response += `• Heritage: ${data.checks.heritage.pass ? '✓ Not listed' : '✗ ' + data.heritage.type}\n\n`;

  // Approval pathway (always visible)
  response += `Approval pathway: ${data.pathway}\n`;
  response += `Timeframe: ${data.pathway === 'CDC' ? '20' : '40'} business days\n`;
  response += `Parking required: ${data.parking.required} space${data.parking.required > 1 ? 's' : ''}\n\n`;

  return response;
}
```

**Key Point:** This is **string manipulation**, not LLM generation.

## Template 2: Corner Lot Setbacks

```typescript
// lib/ai/templates/corner-lot-setbacks.ts

export function formatCornerLotSetbacks(data: SetbackData): string {
  let response = `SETBACK REQUIREMENTS (Corner Lot)\n\n`;

  // Primary street
  response += `Primary street (${data.primaryOrientation}): ${data.setbacks.primary}m\n`;
  response += `  Source: ${data.sources.primary}\n\n`;

  // Secondary street (corner lot specific)
  if (data.isCornerLot) {
    response += `Secondary street (${data.secondaryOrientation}): ${data.setbacks.secondary}m minimum\n`;
    response += `  ⚠️ Corner lot provision applies\n`;
    response += `  Source: ${data.sources.corner}\n`;
    response += `  Plus corner splay: 2m × 2m for sightlines\n\n`;
  }

  // Side setbacks (with modifications)
  response += `Side setback: ${data.setbacks.side}m\n`;
  if (data.modifications.tree) {
    response += `  General requirement: ${data.setbacks.sideBase}m\n`;
    response += `  PLUS tree preservation buffer: +${data.modifications.tree.buffer}m\n`;
    response += `  Reason: ${data.modifications.tree.reason}\n`;
  }
  response += `  Source: ${data.sources.side}\n\n`;

  // Rear setback
  response += `Rear setback: ${data.setbacks.rear}m\n`;
  response += `  Source: ${data.sources.rear}\n\n`;

  // Modifications summary
  if (data.modifications.length > 0) {
    response += `MODIFICATIONS:\n`;
    data.modifications.forEach(mod => {
      response += `⚠️ ${mod.type}: ${mod.description}\n`;
      response += `   ${mod.detail}\n\n`;
    });
  }

  // Caveats
  if (data.caveats.length > 0) {
    response += `IMPORTANT CAVEATS:\n`;
    data.caveats.forEach(caveat => {
      response += `• ${caveat}\n`;
    });
  }

  return response;
}
```

## Template 3: Yield Optimizer

```typescript
// lib/ai/templates/yield-optimizer.ts

export function formatYieldOptimization(data: YieldData): string {
  let response = `YIELD OPTIMIZATION ANALYSIS\n\n`;

  response += `Site: ${data.lotArea}m² lot, ${data.zone} zone, ${data.todDistance}m from station\n\n`;

  // Baseline
  response += `BASELINE YIELD (Standard Controls):\n`;
  response += `• FSR: ${data.baseline.fsr} → ${data.baseline.gfa}m² GFA\n`;
  response += `• Typical unit size: ${data.baseline.unitSize}m²\n`;
  response += `• Baseline: ${data.baseline.gfa} ÷ ${data.baseline.unitSize} = ${data.baseline.units} units\n\n`;

  // Constraints
  response += `CONSTRAINTS (Reduce Yield):\n`;
  data.constraints.forEach(constraint => {
    response += `• ${constraint.name}: ${constraint.impact}\n`;
    response += `  ${constraint.detail}\n`;
  });
  response += `\n`;

  // Optimizations
  response += `OPTIMIZATIONS (Increase Yield):\n`;
  data.optimizations.forEach(opt => {
    response += `${opt.viable ? '✅' : '❌'} ${opt.name}: ${opt.impact}\n`;
    response += `  ${opt.detail}\n`;
  });
  response += `\n`;

  // Scenarios comparison
  response += `OPTIMIZED YIELD SCENARIOS:\n\n`;
  data.scenarios.forEach((scenario, i) => {
    response += `Scenario ${String.fromCharCode(65 + i)}: ${scenario.name}\n`;
    response += `  • ${scenario.units} units × ${scenario.unitSize}m² = ${scenario.gfa}m² GFA\n`;
    response += `  • Parking: ${scenario.parking} spaces\n`;
    response += `  • Profit: $${(scenario.profit / 1000000).toFixed(1)}M\n`;
    if (scenario.tradeoff) {
      response += `  • Trade-off: ${scenario.tradeoff}\n`;
    }
    response += `\n`;
  });

  // Recommendation
  response += `RECOMMENDATION: ${data.recommendation.scenario}\n`;
  response += `  ${data.recommendation.reason}\n\n`;

  return response;
}
```

---

# PART 4: DATA + CALCULATION + LLM CONNECTION

## Flow Diagram (Text-Based)

```
┌─────────────────────────────────────────────────────────────────┐
│                          USER INPUT                              │
│                  "Can I build a granny flat?"                    │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ↓
┌────────────────────────────────────────────────────────────────┐
│                    LLM CLASSIFICATION                           │
│  [Gemini Flash] → category: "granny_flat_eligibility"          │
│                → confidence: 0.92                               │
│                → parameters: { address: "123 Main St" }         │
└────────────────────────┬───────────────────────────────────────┘
                         │
                         ↓
┌────────────────────────────────────────────────────────────────┐
│                      WORKFLOW ROUTING                           │
│  if (category === "granny_flat_eligibility")                   │
│    return GrannyFlatEligibilityWorkflow                        │
└────────────────────────┬───────────────────────────────────────┘
                         │
                         ↓
┌────────────────────────────────────────────────────────────────┐
│                    DATA FETCHING (Parallel)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Planning     │  │ Database     │  │ Planning     │         │
│  │ Portal API   │  │ Query        │  │ Portal API   │         │
│  │              │  │              │  │              │         │
│  │ getZone()    │  │ getParking() │  │ getHeritage()│         │
│  │ → "R2"       │  │ → 1 space    │  │ → "none"     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐                           │
│  │ Planning     │  │ Planning     │                           │
│  │ Portal API   │  │ Portal API   │                           │
│  │              │  │              │                           │
│  │ getLotSize() │  │ getDwelling()│                           │
│  │ → 612m²      │  │ → exists     │                           │
│  └──────────────┘  └──────────────┘                           │
└────────────────────────┬───────────────────────────────────────┘
                         │
                         ↓
┌────────────────────────────────────────────────────────────────┐
│                    BUSINESS LOGIC (Deterministic)               │
│                                                                  │
│  checks = {                                                     │
│    zone: {                                                      │
│      pass: ["R1","R2","R3","R4"].includes("R2"),  ← if/else    │
│      detail: "R2 is eligible",                                 │
│      source: "SEPP Housing 2021 Clause 44"                     │
│    },                                                           │
│    lotSize: {                                                   │
│      pass: 612 >= 450,  ← arithmetic comparison                │
│      detail: "612m² ≥ 450m² minimum",                          │
│      source: "SEPP Housing 2021 Clause 44(1)(a)"              │
│    },                                                           │
│    existingDwelling: {                                          │
│      pass: dwelling.exists === true,  ← boolean check          │
│      detail: "Existing dwelling present",                      │
│      source: "SEPP Housing 2021 Clause 44(1)(b)"              │
│    },                                                           │
│    heritage: {                                                  │
│      pass: heritage.status === "none",  ← string comparison    │
│      detail: "Not heritage listed",                            │
│      source: "NSW Planning Portal"                             │
│    }                                                            │
│  }                                                              │
│                                                                  │
│  eligible = checks.zone.pass && checks.lotSize.pass &&         │
│              checks.existingDwelling.pass && checks.heritage.pass │
│                                                                  │
│  ↓ eligible = true (all checks passed)                         │
└────────────────────────┬───────────────────────────────────────┘
                         │
                         ↓
┌────────────────────────────────────────────────────────────────┐
│                  TEMPLATE FORMATTING (String Concat)            │
│                                                                  │
│  response = `                                                   │
│    ${eligible ? "✅ YES" : "❌ NO"} - Granny flats permitted   │
│                                                                  │
│    ELIGIBILITY CHECKS:                                          │
│                                                                  │
│    ${checks.zone.pass ? "✅" : "❌"} Zone: ${zone}             │
│      ${checks.zone.detail}                                      │
│      Source: ${checks.zone.source}                             │
│                                                                  │
│    ${checks.lotSize.pass ? "✅" : "❌"} Lot Size: ${lotArea}m² │
│      ${checks.lotSize.detail}                                   │
│      Source: ${checks.lotSize.source}                          │
│                                                                  │
│    ... (repeat for each check)                                 │
│  `                                                              │
│                                                                  │
│  ↓ Formatted string ready for UI                               │
└────────────────────────┬───────────────────────────────────────┘
                         │
                         ↓
┌────────────────────────────────────────────────────────────────┐
│                       UI RENDERING (React)                      │
│                                                                  │
│  <AIResponsePanel>                                              │
│    <CoreAnswer collapsible={false}>                            │
│      ✅ YES - Granny flats permitted                           │
│    </CoreAnswer>                                                │
│                                                                  │
│    <QuickSummary collapsible={false}>                          │
│      • Lot size: 612m² (✓ meets minimum)                       │
│      • Zone: R2 (✓ permitted)                                   │
│      ...                                                        │
│    </QuickSummary>                                              │
│                                                                  │
│    <DetailedChecks collapsible={true} defaultExpanded={false}>│
│      [Detailed eligibility checks]                             │
│    </DetailedChecks>                                            │
│                                                                  │
│    <NextSteps collapsible={true} defaultExpanded={false}>      │
│      [Step-by-step guidance]                                   │
│    </NextSteps>                                                 │
│                                                                  │
│    <AllSources collapsible={true} defaultExpanded={false}>     │
│      [5 data sources with links]                               │
│    </AllSources>                                                │
│  </AIResponsePanel>                                             │
└─────────────────────────────────────────────────────────────────┘
```

**Key Insight:** LLM touches the process ONCE at the beginning (classification), then everything is deterministic data flow.

---

# PART 5: UI IMPLEMENTATION (React Components)

## Component Structure

```typescript
// frontend-nextjs/components/ai-assistant/WorkflowResponse.tsx

interface WorkflowResponseProps {
  result: WorkflowResult;
}

export function WorkflowResponse({ result }: WorkflowResponseProps) {
  return (
    <div className="workflow-response">
      {/* ALWAYS VISIBLE - Core answer */}
      <CoreAnswer
        eligible={result.structured.eligible}
        answer={result.structured.answer}
      />

      {/* ALWAYS VISIBLE - Quick summary */}
      <QuickSummary
        checks={result.structured.checks}
        pathway={result.structured.pathway}
        parking={result.structured.parking}
      />

      {/* COLLAPSIBLE - Detailed checks */}
      <CollapsibleSection
        title="Show detailed checks"
        count={Object.keys(result.structured.checks).length}
        defaultExpanded={false}
      >
        <DetailedChecks checks={result.structured.checks} />
      </CollapsibleSection>

      {/* COLLAPSIBLE - Next steps */}
      <CollapsibleSection
        title="What happens next?"
        count={result.structured.nextSteps.length}
        defaultExpanded={false}
      >
        <NextSteps steps={result.structured.nextSteps} />
      </CollapsibleSection>

      {/* COLLAPSIBLE - All sources */}
      <CollapsibleSection
        title="View all sources"
        count={result.sources.length}
        defaultExpanded={false}
      >
        <SourceList sources={result.sources} />
      </CollapsibleSection>

      {/* Confidence indicator */}
      <ConfidenceIndicator
        confidence={result.confidence}
        responseTime={result.responseTime}
      />

      {/* Related questions */}
      <SuggestedQuestions
        questions={generateRelatedQuestions(result.structured.category)}
      />
    </div>
  );
}
```

## Progressive Disclosure Pattern

```typescript
// frontend-nextjs/components/ai-assistant/CollapsibleSection.tsx

interface CollapsibleSectionProps {
  title: string;
  count?: number;
  defaultExpanded?: boolean;
  children: React.ReactNode;
}

export function CollapsibleSection({
  title,
  count,
  defaultExpanded = false,
  children
}: CollapsibleSectionProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  return (
    <div className="collapsible-section">
      <button
        onClick={() => setExpanded(!expanded)}
        className="collapsible-header"
      >
        <span className="icon">{expanded ? '▲' : '▼'}</span>
        <span className="title">{title}</span>
        {count && <span className="count">({count})</span>}
      </button>

      {expanded && (
        <div className="collapsible-content">
          {children}
        </div>
      )}
    </div>
  );
}
```

---

# PART 6: CONFIDENCE INDICATORS

## How Confidence is Calculated (Deterministic)

```typescript
// lib/ai/confidence-calculator.ts

export function calculateConfidence(data: WorkflowData): ConfidenceLevel {
  let score = 100;

  // Deduct points for missing data
  if (!data.zone) score -= 20; // Critical data missing
  if (!data.lotDimensions) score -= 20;
  if (!data.heritage) score -= 10; // Less critical

  // Deduct points for edge cases
  if (data.lotSize < 460 && data.lotSize >= 450) {
    score -= 15; // Close to threshold = less confidence
  }

  // Deduct points for conflicts
  if (data.hasConflicts) score -= 25; // LEP vs DCP conflict = uncertain

  // Deduct points for interpretation needed
  if (data.requiresInterpretation) score -= 30; // Professional judgment needed

  // Convert score to confidence level
  if (score >= 85) return { level: 'high', score, display: 'High confidence' };
  if (score >= 65) return { level: 'medium', score, display: 'Medium confidence' };
  return { level: 'low', score, display: 'Low confidence - verify with professional' };
}
```

## UI Display of Confidence

```typescript
// frontend-nextjs/components/ai-assistant/ConfidenceIndicator.tsx

export function ConfidenceIndicator({ confidence }: { confidence: ConfidenceLevel }) {
  const colors = {
    high: 'text-green-600 bg-green-50',
    medium: 'text-amber-600 bg-amber-50',
    low: 'text-red-600 bg-red-50'
  };

  return (
    <div className={`confidence-indicator ${colors[confidence.level]}`}>
      <span className="label">Confidence:</span>
      <span className="value">{confidence.display}</span>

      {confidence.level === 'low' && (
        <div className="warning">
          ⚠️ Professional verification recommended
          Reason: {confidence.reason}
        </div>
      )}

      <div className="metadata">
        Response time: {responseTime}ms
        Data sources: {sourceCount}
      </div>
    </div>
  );
}
```

---

# SUMMARY: HOW IT ALL WORKS

## The Complete Picture

**1. User Question → LLM Classification (5% of process)**
- User: "Can I build a granny flat?"
- LLM (Gemini Flash): "This is a `granny_flat_eligibility` question with 92% confidence"
- LLM extracts parameters: `{ address: "123 Main St" }`

**2. Routing → Deterministic (NO LLM)**
- System: `if (category === "granny_flat_eligibility") → GrannyFlatWorkflow`

**3. Data Fetching → APIs/Database (NO LLM)**
- Planning Portal API: Zone = R2, Lot = 612m², Heritage = none
- Database: Parking = 1 space required

**4. Business Logic → If/Else Rules (NO LLM)**
- `zone in [R1,R2,R3,R4]` → TRUE
- `lot_size >= 450` → TRUE
- `existing_dwelling === true` → TRUE
- `heritage === "none"` → TRUE
- Result: `eligible = TRUE`

**5. Template Formatting → String Substitution (NO LLM)**
- `"${eligible ? 'YES' : 'NO'} - Granny flats permitted"`
- `"Lot size: ${lotSize}m² ≥ 450m² minimum"`
- NOT: `gemini.generate("Write a response about...")`

**6. UI Display → React Components (NO LLM)**
- Core answer always visible
- Detailed checks collapsible
- Sources collapsible
- Next steps collapsible

**Total LLM Usage:** 5% (classification only)
**Total Deterministic:** 95% (everything else)

**Why This Approach:**
- ✅ **Zero hallucinations** - Templates can't invent data
- ✅ **100% citation accuracy** - Every fact has a source
- ✅ **Fast** - No LLM generation latency (<1s vs 3-5s)
- ✅ **Cheap** - Only one LLM call (classification), not generation
- ✅ **Verifiable** - Professionals can check each step
- ✅ **Maintainable** - Templates easier to update than prompts
- ✅ **Professional trust** - Deterministic = consistent = trustworthy

---

**Last Updated:** 2026-02-01
**Status:** Complete architectural documentation
**Reference:** Integrate with COMPLEX_WORKFLOW_CATALOG.md for workflow-specific templates
