# Strategic Development Type Filtering Enhancement Plan

**Current State:** Binary filter (include/exclude)
**Opportunity:** Multi-tier relevance system inspired by environmental-relevance-filter.ts
**Goal:** Surface the RIGHT information at the RIGHT time for user decision-making

---

## Problem with Pure Binary Filtering

### Current Behavior
```
✅ SHOW: "Front setback 6m minimum" (clearly relevant)
❌ HIDE: "Commercial signage on residential boundaries" (clearly irrelevant)
```

### The Gap
```
❓ What about requirements that are:
   - Conditionally relevant (if lot size > X)
   - Potentially relevant (if future subdivision planned)
   - Contextually relevant (if heritage overlay applies)
   - Edge case relevant (if corner lot)
```

**Current approach:** Show everything uncertain (conservative)
**Better approach:** Show with CONTEXT about relevance

---

## Inspiration: Environmental Relevance Filter Success

The existing `environmental-relevance-filter.ts` does this brilliantly:

```typescript
interface FilterResult {
  isRelevant: boolean;        // Should we show it?
  requiresAction: boolean;    // Must user act on this?
  reason?: string;            // WHY is this relevant/not?
  category?: 'basix' | 'environmental_overlay' | 'informational' | 'prohibition';
}
```

**Example in action:**
- **Acid Sulfate Soils Class 5:** Show as "informational" with reason "Lowest risk - no management plan required"
- **Acid Sulfate Soils Class 1-4:** Show as "requires action" with reason "Management plan required before works"

**This is brilliant because:**
1. User still sees both
2. But understands priority/severity
3. Can make informed decisions
4. Doesn't waste time on Class 5

---

## Proposed Enhancement: Relevance Tiers for DCP Requirements

### Tier System (4 levels)

#### 1️⃣ TIER 1: Core Requirements (Always Applicable)
**Characteristics:**
- High confidence (90%+) of applicability
- No conditionals or edge cases
- Universal to this development type

**Examples for dwelling_house:**
- "Front setback 6m minimum"
- "Maximum building height 9m"
- "Private open space 50m²"

**UI Treatment:**
- Show by default
- No special badges
- Standard display

---

#### 2️⃣ TIER 2: Conditional Requirements (Context-Dependent)
**Characteristics:**
- Applies IF specific conditions met
- Contains "where", "if", "when" language
- Needs user to assess trigger

**Examples for dwelling_house:**
- "Where lot depth exceeds 50m, rear setback increases to 10m"
- "If within 10m of heritage item, heritage controls apply"
- "For corner lots, secondary street setback 3m minimum"

**UI Treatment:**
- Show with **"Conditional"** badge (already exists)
- Highlight trigger condition
- User assesses if applies to their site

**Detection Logic:**
```typescript
const CONDITIONAL_TRIGGERS = [
  /\bwhere\b/i,
  /\bif\b/i,
  /\bwhen\b/i,
  /\bfor lots?\b/i,
  /\bfor properties?\b/i,
  /\bexceeds?\b/i,
  /\bgreater than\b/i,
  /\bwithin \d+m?\b/i,
];

function hasConditionalTriggers(text: string): boolean {
  return CONDITIONAL_TRIGGERS.some(pattern => pattern.test(text));
}
```

---

#### 3️⃣ TIER 3: Edge Case Requirements (Rarely Applicable)
**Characteristics:**
- Only applies to unusual scenarios
- Most users can ignore
- Expert/niche situations

**Examples for dwelling_house:**
- "Dwelling on battle-axe lots require..." (rare lot shape)
- "Dwellings with private swimming pools..." (< 30% of homes)
- "Dual occupancy subdivision provisions" (not doing subdivision)

**UI Treatment:**
- Collapse by default under "Edge Cases & Special Situations"
- Badge: **"Specialized"** or **"Advanced"**
- Expandable accordion

**Detection Logic:**
```typescript
const EDGE_CASE_INDICATORS = [
  /\bbattle-?axe\b/i,
  /\bswimming pool/i,
  /\btennis court/i,
  /\bsubdivision\b/i,
  /\bstrata\b/i,
  /\bdual occupancy\b/i,  // When viewing dwelling_house
  /\bdemolition\b/i,       // Unless user flags intent
];
```

---

#### 4️⃣ TIER 4: Informational (Good to Know)
**Characteristics:**
- No direct compliance requirement
- Background context
- Design guidance vs. rules

**Examples for dwelling_house:**
- "Objectives: Maintain streetscape character" (objective, not requirement)
- "Note: Council encourages sustainable design" (encouragement, not rule)
- "Character description: Area features..." (context, not control)

**UI Treatment:**
- Badge: **"Informational"** or **"Guidance"**
- Lighter visual weight (gray vs. black text)
- Collapsible under "Design Guidance & Context"

**Detection Logic:**
```typescript
const INFORMATIONAL_PATTERNS = [
  /^objectives?:/i,
  /^note:/i,
  /\bencourage/i,
  /\bprefer/i,
  /\bshould consider/i,
  /\bcharacter description/i,
  /\bbackground\b/i,
];
```

---

## Strategic Benefits

### 1. Reduces Cognitive Load
**Before:** User sees 830 requirements, must read all
**After:** User sees:
- 350 Core (must comply)
- 200 Conditional (assess if applies)
- 150 Edge Cases (collapsed - expand if relevant)
- 130 Informational (skim for context)

### 2. Improves Decision Speed
**Scenario:** User checking front setback for standard rectangular lot
- **Tier 1:** Immediately finds "Front setback 6m" (main requirement)
- **Tier 2:** Sees "Corner lot: 3m secondary street" (doesn't apply, skip)
- **Tier 3:** Ignores battle-axe provisions (collapsed)

### 3. Educates Users
**Instead of hiding** "heritage overlay controls", show as:
> ⚠️ **Conditional**: Applies if heritage item within 10m. Check heritage map.

User learns:
1. These controls exist
2. When they trigger
3. How to check if applicable

### 4. Supports Expert Users
**Advanced users** can expand Tier 3 edge cases for comprehensive review
**DIY users** can focus on Tier 1 core requirements
**Designers** pay attention to Tier 2 conditionals

---

## Implementation Plan

### Phase 1: Data Enhancement (2-3 hours)

Add `relevance_tier` field to filtering logic:

```typescript
interface FilterableRequirement {
  id: number;
  category: string;
  requirement_text: string;
  verbatim_source_text?: string;
  // ... existing fields

  // NEW: Relevance classification
  relevance_tier?: 1 | 2 | 3 | 4;
  relevance_reason?: string;
  trigger_condition?: string;  // For Tier 2 conditionals
}

interface RelevanceAssessment {
  tier: 1 | 2 | 3 | 4;
  reason: string;
  confidence: number;
  trigger?: string;
}
```

### Phase 2: Classification Logic (3-4 hours)

```typescript
function assessRequirementRelevance(
  requirement: FilterableRequirement,
  developmentType: string,
  propertyContext?: PropertyContext  // Optional: lot size, heritage, etc.
): RelevanceAssessment {
  const text = requirement.verbatim_source_text || requirement.requirement_text;

  // Check for informational patterns
  if (INFORMATIONAL_PATTERNS.some(p => p.test(text))) {
    return {
      tier: 4,
      reason: 'Design guidance or contextual information',
      confidence: 0.85
    };
  }

  // Check for edge case indicators
  if (EDGE_CASE_INDICATORS.some(p => p.test(text))) {
    return {
      tier: 3,
      reason: 'Specialized scenario - only applicable in specific situations',
      confidence: 0.75
    };
  }

  // Check for conditionals
  const conditionalMatch = CONDITIONAL_TRIGGERS.find(p => p.test(text));
  if (conditionalMatch) {
    const trigger = extractTriggerCondition(text);
    return {
      tier: 2,
      reason: 'Conditional requirement - assess if trigger applies',
      confidence: 0.80,
      trigger
    };
  }

  // Default: Core requirement
  return {
    tier: 1,
    reason: 'Core requirement applicable to this development type',
    confidence: 0.90
  };
}
```

### Phase 3: UI Integration (4-5 hours)

**Component Updates:**

1. **CategorySection.tsx** - Add tier badges and grouping
2. **RequirementItem.tsx** - Visual distinction by tier
3. **GeneralDCPSection.tsx** - Collapsible tier sections

**Example UI:**

```tsx
<div className="requirements-by-tier">
  {/* Tier 1: Always expanded */}
  <div className="tier-1-requirements">
    <h4>Core Requirements (350)</h4>
    {tier1Requirements.map(req => (
      <RequirementItem {...req} tier={1} />
    ))}
  </div>

  {/* Tier 2: Expanded by default */}
  <div className="tier-2-requirements">
    <h4>Conditional Requirements (200)</h4>
    <p className="text-xs text-gray-600">
      Check if trigger conditions apply to your site
    </p>
    {tier2Requirements.map(req => (
      <RequirementItem
        {...req}
        tier={2}
        showTrigger={true}
        badge="Conditional"
      />
    ))}
  </div>

  {/* Tier 3: Collapsed by default */}
  <Collapsible defaultOpen={false}>
    <CollapsibleTrigger>
      <h4>Edge Cases & Special Situations (150)</h4>
      <p className="text-xs">Battle-axe lots, pools, subdivisions, etc.</p>
    </CollapsibleTrigger>
    <CollapsibleContent>
      {tier3Requirements.map(req => (
        <RequirementItem {...req} tier={3} badge="Specialized" />
      ))}
    </CollapsibleContent>
  </Collapsible>

  {/* Tier 4: Collapsed by default */}
  <Collapsible defaultOpen={false}>
    <CollapsibleTrigger>
      <h4>Design Guidance & Context (130)</h4>
      <p className="text-xs">Objectives, notes, character descriptions</p>
    </CollapsibleTrigger>
    <CollapsibleContent>
      {tier4Requirements.map(req => (
        <RequirementItem {...req} tier={4} badge="Informational" />
      ))}
    </CollapsibleContent>
  </Collapsible>
</div>
```

---

## Advanced: Context-Aware Filtering (Phase 4 - Optional)

### Property Context Integration

If we capture additional property details:

```typescript
interface PropertyContext {
  lotSize?: number;
  lotDepth?: number;
  lotWidth?: number;
  isCornerLot?: boolean;
  isBattleAxe?: boolean;
  hasHeritageOverlay?: boolean;
  hasPoolPlanned?: boolean;
  demolitionPlanned?: boolean;
}
```

We can **auto-promote** conditionals to Tier 1:

```typescript
function assessWithContext(
  requirement: FilterableRequirement,
  context: PropertyContext
): RelevanceAssessment {
  const baseAssessment = assessRequirementRelevance(requirement, ...);

  // Auto-promote Tier 2 to Tier 1 if condition is MET
  if (baseAssessment.tier === 2) {
    if (requirement.requirement_text.includes('corner lot') && context.isCornerLot) {
      return {
        tier: 1,
        reason: 'Conditional requirement applies to this corner lot',
        confidence: 0.95
      };
    }

    if (requirement.requirement_text.includes('swimming pool') && context.hasPoolPlanned) {
      return {
        tier: 1,
        reason: 'Pool controls apply (user flagged pool intent)',
        confidence: 0.95
      };
    }
  }

  // Auto-demote Tier 2 to Tier 3 if condition NOT met
  if (baseAssessment.tier === 2) {
    if (requirement.requirement_text.includes('corner lot') && !context.isCornerLot) {
      return {
        tier: 3,
        reason: 'Not a corner lot - requirement does not apply',
        confidence: 0.90
      };
    }
  }

  return baseAssessment;
}
```

**User Experience:**
1. User enters address → We detect corner lot from cadastre
2. "Corner lot setback 3m" **auto-promotes** from Tier 2 → Tier 1
3. "Battle-axe access width" **auto-demotes** from Tier 2 → Tier 3
4. User sees exactly what applies to their specific property

---

## Comparison with Current Approach

### Current Binary System
```
Filter: Show/Hide based on development type
Result: 830 requirements visible (3.6% filtered out)
User workflow: Read all 830 requirements
```

### Enhanced Tier System
```
Filter: Classify + Show with context
Result:
  - Tier 1 (Core): 350 shown prominently
  - Tier 2 (Conditional): 200 shown with trigger conditions
  - Tier 3 (Edge cases): 150 collapsed by default
  - Tier 4 (Informational): 130 collapsed by default

User workflow:
  - Focus on 350 core requirements
  - Assess 200 conditionals (quick yes/no for trigger)
  - Ignore 280 collapsed items unless relevant

Effective cognitive load: 550 instead of 830 (34% reduction)
```

---

## Tactical Quick Wins (Implement These First)

### Quick Win 1: Flag Conditionals (30 minutes)
Already detecting `has_conditionals` in database.
**Just add visual distinction:**

```tsx
{requirement.has_conditionals && (
  <div className="conditional-trigger bg-yellow-50 border-l-4 border-yellow-400 p-2 mt-2">
    <strong>⚠️ Trigger Condition:</strong> {requirement.conditional_text}
    <p className="text-xs mt-1">Assess if this applies to your property</p>
  </div>
)}
```

### Quick Win 2: Collapse Objectives (1 hour)
Objectives are informational, not requirements.

```tsx
const isObjective = requirement.section_type === 'objective' ||
                    requirement.requirement_text.startsWith('Objective:');

if (isObjective) {
  // Show under collapsed "Objectives & Context" section
  // Gray text, lighter weight
}
```

### Quick Win 3: Highlight Numerics (30 minutes)
Requirements with numeric values are actionable.

```tsx
const hasNumeric = requirement.value_numeric || requirement.value_min || requirement.value_max;

{hasNumeric && (
  <span className="font-bold text-blue-600">
    {requirement.value_numeric}{requirement.unit}
  </span>
)}
```

---

## ROI Analysis

### Implementation Cost
- **Quick Wins (Phase 0):** 2 hours
- **Phase 1-2 (Classification):** 5-7 hours
- **Phase 3 (UI):** 4-5 hours
- **Phase 4 (Context-aware):** 10-15 hours (optional)

**Total:** 11-14 hours (without Phase 4)

### User Benefit
- **Cognitive load:** -34% (830 → 550 effective requirements)
- **Time to find key requirements:** -60% (scan 350 instead of 830)
- **Decision confidence:** +High (clear tier labels explain why shown)
- **Expert vs. DIY differentiation:** Experts can expand all, DIY focuses on core

---

## Recommendation

**Start with Quick Wins (2 hours):**
1. Visual distinction for conditionals (already detected)
2. Collapse objectives/informational
3. Highlight numeric requirements

**Then implement Phase 1-3 (9-12 hours):**
- Full 4-tier relevance system
- UI grouping by tier
- Collapsible sections for Tier 3-4

**Phase 4 (context-aware):**
- Only if we add property context inputs (lot size, corner lot checkbox, etc.)
- High value but requires UX for context capture

---

## Inspiration: How Google Maps Does This

Google Maps doesn't hide ALL non-restaurants when you search "restaurants":
- **Tier 1:** Restaurants (bold, big pins)
- **Tier 2:** Cafes with food (lighter pins, "Also consider")
- **Tier 3:** Grocery stores (collapsed under "More places")
- **Tier 4:** Gas stations (informational context)

**We can do the same:**
- **Tier 1:** Core dwelling house requirements (bold, expanded)
- **Tier 2:** Conditionals (visible, with "Check if applies")
- **Tier 3:** Edge cases (collapsed, "Specialized situations")
- **Tier 4:** Objectives (collapsed, "Design context")
