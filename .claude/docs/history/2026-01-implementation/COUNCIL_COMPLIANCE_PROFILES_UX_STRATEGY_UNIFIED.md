# Council Compliance Profiles - Unified UX Strategy
**Turning Data Quality Differences into Strategic User Insights**

**Date:** 2025-11-02 (Updated with Leichhardt data)
**Status:** Ready for Implementation
**Context:** Three-council analysis reveals distinct compliance personalities requiring unified UX approach

---

## Executive Summary

Data extraction revealed that **all three Inner West DCPs have distinct compliance personalities:**

| Council | Heritage Context | Allows Alternatives | Objectives | Style |
|---------|-----------------|---------------------|-----------|-------|
| **Marrickville** | 56.0% | 2.3% | 10.5% | **Performance-based** |
| **Ashfield** | 5.6% | 1.7% | 12.6% | **Prescriptive** |
| **Leichhardt** | 0.4% | 5.0% | 11.4% | **Prescriptive+** |

**Key Insight:** Marrickville stands alone as performance-based (rich heritage context). Ashfield and Leichhardt are both prescriptive but express it differently (Ashfield = technical rules, Leichhardt = process-based with flexibility).

**Strategic Opportunity:** Create a **unified UX framework** that adapts intelligently to each council's personality while maintaining consistent user experience.

---

## The Data Reality

### Marrickville DCP (Performance-Based)

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Heritage context populated | 56.0% | Rich significance narratives |
| Allow alternative solutions | 2.3% (general), 33.6% (precincts) | Context-driven flexibility |
| Objectives present | 10.5% | Design intent encouraged |

**Writing Style:**
```
"The area is of historical significance as the 1910 'Rathgael Estate'
subdivision around Rathgael house (1870)..."

Requirement: "Alterations should respect heritage significance"
→ WHY explained
→ Design intent emphasized
→ Alternatives possible if objectives met
```

### Ashfield DCP (Prescriptive/Technical)

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Heritage context populated | 5.6% | Minimal significance narratives |
| Allow alternative solutions | 1.7% | Rigid, prescriptive |
| Objectives present | 12.6% | Similar to Marrickville |

**Writing Style:**
```
"Glass or clear balustrades are not permitted where visible from
the public domain."

Requirement: Technical rule
→ No context about "why"
→ Black and white compliance
→ No alternatives mentioned
```

### Leichhardt DCP (Prescriptive+/Process-Based)

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Heritage context populated | 0.4% | Lowest of all three councils |
| Allow alternative solutions | 5.0% | Moderate flexibility (3x Ashfield) |
| Objectives present | 11.4% | Similar to others |

**Writing Style:**
```
"Renewable energy sources may be considered when passive methods
are insufficient."

Requirement: Procedural with conditions
→ Minimal "why" context
→ More flexibility than Ashfield
→ Process-based alternatives (5.0% vs 1.7%)
```

**Leichhardt's Unique Position:** Most prescriptive on heritage context (0.4%) but most flexible on alternatives (5.0%) - suggests a "follow the process and we'll work with you" approach.

---

## UX Unification Challenge

**The Problem:**
Users navigating between councils face:
1. **Inconsistent information depth** - Marrickville tells them WHY, Ashfield/Leichhardt don't
2. **Varying flexibility** - Same requirement type has different flexibility per council
3. **Lost context** - No understanding of whether gaps are data issues or council style
4. **Reduced control** - Users can't tell if they're seeing complete information

**User's Mental Model Break:**
```
User in Marrickville:
"I understand this requirement because context is provided"

User in Ashfield:
"Why this rule? Is info missing? Can I do anything different?"
→ Confusion, lack of control
```

---

## UX Unification Strategies

### Strategy 1: Adaptive Information Architecture 🏆 **RECOMMENDED**

**Concept:** Same UI framework, intelligent content adaptation per council

**Implementation:**

#### Universal Requirement Card Structure
```
┌─────────────────────────────────────────────────────────────────┐
│ [REQUIREMENT CARD - Consistent Structure]                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ 1. COMPLIANCE PROFILE HEADER (Council-specific badge)          │
│    → Marrickville: "Performance-based | Rich context"          │
│    → Ashfield: "Prescriptive | Seek LEP for context"           │
│    → Leichhardt: "Process-based | Moderate flexibility"        │
│                                                                 │
│ 2. REQUIREMENT TEXT (Always present)                           │
│    → Same format for all councils                              │
│                                                                 │
│ 3. STRATEGIC CONTEXT (Adaptive section)                        │
│    a. Heritage Context (if DCP provides):                      │
│       - Marrickville: Show rich DCP context                    │
│       - Ashfield: Show "Context not in DCP" + LEP link         │
│       - Leichhardt: Show "Context not in DCP" + LEP link       │
│                                                                 │
│    b. Objectives (if present):                                 │
│       - All councils: Show when available (~10-13%)            │
│                                                                 │
│    c. Flexibility Indicator (Always show):                     │
│       - Marrickville: "Heritage objectives approach possible"  │
│       - Ashfield: "Strict compliance required"                 │
│       - Leichhardt: "Process-based flexibility may apply"      │
│                                                                 │
│ 4. EXTERNAL RESOURCES (Adaptive)                               │
│    - Marrickville: Optional (context already rich)             │
│    - Ashfield/Leichhardt: Prominent LEP/heritage study links   │
│                                                                 │
│ 5. CONFIDENCE INDICATOR (Always present)                       │
│    → "Complete DCP information"                                │
│    → "DCP + LEP recommended"                                   │
│    → "Seek council clarification"                              │
└─────────────────────────────────────────────────────────────────┘
```

**Key Principle:** SAME CARD STRUCTURE, DIFFERENT CONTENT DEPTH + SIGNPOSTING

---

### Strategy 2: Smart Context Enrichment System

**Concept:** Automatically fill gaps with LEP/external data when DCP lacks context

**Implementation:**

```typescript
interface EnrichedRequirement {
  // Core data (from DCP extraction)
  requirement_text: string;
  category: string;
  heritage_context?: string; // Marrickville rich, Ashfield/Leichhardt sparse

  // Smart enrichment (computed)
  enrichment_status: 'complete' | 'dcp_partial' | 'external_needed';
  enrichment_sources: {
    lep_heritage_schedule?: {
      text: string;
      source: string; // "Inner West LEP 2022 Schedule 5"
    };
    nsw_heritage_db?: {
      listing_url: string;
      significance_level: string;
    };
    council_heritage_study?: {
      pdf_url: string;
      relevant_section: string;
    };
  };

  // User guidance (computed per council)
  compliance_strategy: string;
  flexibility_level: 'none' | 'process' | 'performance';
}
```

**Enrichment Rules:**

| Council | Heritage Context | Enrichment Strategy |
|---------|-----------------|---------------------|
| **Marrickville** | 56% present | Show DCP context, LEP as "Additional info" |
| **Ashfield** | 5.6% present | Proactively show LEP, label as "Essential context" |
| **Leichhardt** | 0.4% present | Proactively show LEP, label as "Essential context" |

---

### Strategy 3: Unified Compliance Strategy Guide

**Concept:** Per-council guidance that gives users a mental model and sense of control

**Implementation:**

#### Assessment Page Header (Council-Specific)

**Marrickville:**
```
┌─────────────────────────────────────────────────────────────────┐
│ MARRICKVILLE COMPLIANCE APPROACH                                │
├─────────────────────────────────────────────────────────────────┤
│ Style: Performance-based                                        │
│                                                                 │
│ What to expect:                                                 │
│  ✓ Rich heritage context explains WHY requirements exist       │
│  ✓ Design intent matters as much as technical specs            │
│  ✓ Alternative solutions possible if objectives demonstrated   │
│                                                                 │
│ Your strategy:                                                  │
│  1. Understand heritage significance (provided in requirements) │
│  2. Demonstrate how design meets objectives                     │
│  3. Consider performance-based alternatives                     │
│                                                                 │
│ Confidence level: HIGH - Complete DCP information provided      │
└─────────────────────────────────────────────────────────────────┘
```

**Ashfield:**
```
┌─────────────────────────────────────────────────────────────────┐
│ ASHFIELD COMPLIANCE APPROACH                                    │
├─────────────────────────────────────────────────────────────────┤
│ Style: Prescriptive (Technical)                                │
│                                                                 │
│ What to expect:                                                 │
│  ⚠️  Technical rules without "why" explanations                │
│  ⚠️  Strict compliance (limited flexibility: 1.7%)             │
│  ⚠️  Heritage context not in DCP - seek LEP/studies            │
│                                                                 │
│ Your strategy:                                                  │
│  1. Meet exact technical specifications                         │
│  2. Consult LEP Heritage Schedule for context (linked below)   │
│  3. Expect rigorous compliance assessment                       │
│                                                                 │
│ Confidence level: MODERATE - Supplement with LEP/heritage data  │
│                                                                 │
│ [View LEP Heritage Schedule →] [Heritage Study →]              │
└─────────────────────────────────────────────────────────────────┘
```

**Leichhardt:**
```
┌─────────────────────────────────────────────────────────────────┐
│ LEICHHARDT COMPLIANCE APPROACH                                  │
├─────────────────────────────────────────────────────────────────┤
│ Style: Process-based (Prescriptive with flexibility)           │
│                                                                 │
│ What to expect:                                                 │
│  ✓ Process-based requirements (moderate flexibility: 5.0%)     │
│  ⚠️  Heritage context not in DCP - seek LEP/studies            │
│  ✓ More flexibility than Ashfield for alternative approaches   │
│                                                                 │
│ Your strategy:                                                  │
│  1. Follow prescribed processes                                 │
│  2. Consult LEP Heritage Schedule for context (linked below)   │
│  3. Explore alternative solutions where indicated              │
│                                                                 │
│ Confidence level: MODERATE - Supplement with LEP/heritage data  │
│                                                                 │
│ [View LEP Heritage Schedule →] [Heritage Study →]              │
└─────────────────────────────────────────────────────────────────┘
```

---

### Strategy 4: Transparency & Control Indicators

**Concept:** Always show users what they're seeing, what's missing, and why

**Implementation:**

#### Data Completeness Badge (Per Requirement)
```
[COMPLETE] - DCP provides full context
  → Marrickville: 56% of heritage requirements

[PARTIAL] - DCP provides rule but not context
  → Ashfield/Leichhardt: ~94% of heritage requirements
  → Actionable: "View LEP for heritage significance"

[EXTERNAL SOURCES RECOMMENDED] - Consult additional resources
  → Links to LEP, heritage studies, NSW database
```

#### Flexibility Badge (Per Requirement)
```
[NO FLEXIBILITY] - Strict compliance required
  → Ashfield: 98.3% of requirements
  → User knows: "Must meet exactly as stated"

[PROCESS-BASED FLEXIBILITY] - Follow prescribed alternatives
  → Leichhardt: 5.0% of requirements
  → User knows: "Alternative pathways exist"

[PERFORMANCE-BASED] - Objectives-driven alternatives
  → Marrickville: 2.3% general, 33.6% precincts
  → User knows: "Demonstrate design intent"
```

#### Council Personality Legend (Always Visible)
```
[?] What's my council's compliance style?
  → Click to see: Comparison table
  → Shows: Where your council sits on spectrum
  → Explains: What to expect, how to prepare
```

---

### Strategy 5: Standardized Requirement Grouping

**Concept:** Group requirements the same way for all councils, compensating for missing data

**Implementation:**

#### Category-First, Council-Adaptive Display
```
HERITAGE REQUIREMENTS
├─ Building Alterations (5 requirements)
│  ├─ [MARRICKVILLE]
│  │  ✓ Heritage context provided in requirements
│  │  ✓ Objectives stated
│  │
│  └─ [ASHFIELD/LEICHHARDT]
│     ⚠️  Heritage context not in DCP
│     → View LEP Heritage Schedule for this area
│     → View Council Heritage Study (2015)
│
├─ Facade Retention (3 requirements)
│  ... (same adaptive pattern)
```

**Key Principle:** CONSISTENT CATEGORIES, ADAPTIVE CONTEXT

---

### Strategy 6: Cross-Council Intelligence (Advanced)

**Concept:** Help users understand relative differences and make strategic choices

**Implementation:**

#### Comparison View (Optional Feature)
```
┌─────────────────────────────────────────────────────────────────┐
│ YOUR REQUIREMENT ACROSS INNER WEST COUNCILS                     │
├─────────────────────────────────────────────────────────────────┤
│ Requirement: Setback for heritage buildings                     │
│                                                                 │
│ Marrickville:                                                   │
│  → 6.0m setback recommended for heritage significance          │
│  → Context: Preserve streetscape character of 1920s estate     │
│  → Flexibility: May vary if heritage objectives demonstrated   │
│                                                                 │
│ Ashfield:                                                       │
│  → 6.0m setback required                                       │
│  → Context: Not specified (see LEP)                            │
│  → Flexibility: None (1.7% allow alternatives)                 │
│                                                                 │
│ Leichhardt:                                                     │
│  → 6.0m setback required unless alternative demonstrated       │
│  → Context: Not specified (see LEP)                            │
│  → Flexibility: Process-based (5.0% allow alternatives)        │
│                                                                 │
│ Insight: Marrickville most flexible, Ashfield most strict      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Unified Design System

### Visual Consistency

**Color Coding (Council Personality):**
- **Performance-based** (Marrickville): Blue/Green (#3B82F6 / #10B981)
- **Prescriptive** (Ashfield): Amber/Orange (#F59E0B)
- **Process-based** (Leichhardt): Purple (#8B5CF6)

**Badge System:**
```css
.council-badge {
  /* Same size, position for all councils */
  padding: 8px 12px;
  border-radius: 6px;
  font-weight: 600;
  font-size: 14px;
}

.council-badge--marrickville {
  background: linear-gradient(135deg, #3B82F6 0%, #10B981 100%);
  color: white;
}

.council-badge--ashfield {
  background: #FEF3C7;
  border: 2px solid #F59E0B;
  color: #92400E;
}

.council-badge--leichhardt {
  background: #EDE9FE;
  border: 2px solid #8B5CF6;
  color: #5B21B6;
}
```

### Icon System (Unified)

| Icon | Meaning | All Councils |
|------|---------|--------------|
| ✓ | Complete information | Yes |
| ⚠️  | Supplement with LEP | Yes |
| 🔒 | No flexibility | Yes |
| 🔓 | Flexibility available | Yes |
| 🏛️  | Heritage context | Yes |
| 💡 | Strategic guidance | Yes |

---

## Implementation Roadmap

### Phase 1: Unified Framework (Week 1-2)

**Components:**
1. **Council Profile Config** (`config/council-profiles.ts`)
   ```typescript
   export const COUNCIL_PROFILES = {
     Marrickville: {
       style: 'performance',
       strictness: 'moderate',
       heritage_context_pct: 56.0,
       alternatives_pct: 2.3,
       guidance: 'Rich heritage context provided...',
       enrichment_priority: 'low', // Already has context
     },
     Ashfield: {
       style: 'prescriptive',
       strictness: 'high',
       heritage_context_pct: 5.6,
       alternatives_pct: 1.7,
       guidance: 'Technical rules require exact compliance...',
       enrichment_priority: 'high', // Needs LEP context
     },
     Leichhardt: {
       style: 'process',
       strictness: 'moderate',
       heritage_context_pct: 0.4,
       alternatives_pct: 5.0,
       guidance: 'Process-based with moderate flexibility...',
       enrichment_priority: 'high', // Needs LEP context
     },
   };
   ```

2. **Adaptive Requirement Card Component**
   ```typescript
   <RequirementCard
     requirement={req}
     councilProfile={COUNCIL_PROFILES[req.former_council]}
     enrichmentData={enrichmentService.get(req.id)}
   />
   ```

3. **Council Strategy Header Component**
   ```typescript
   <CouncilStrategyHeader council={councilName} />
   ```

**Effort:** 12-16 hours
**Value:** High (unified UX foundation)

### Phase 2: Context Enrichment (Week 3-4)

**Components:**
1. LEP Heritage Schedule extraction (one-time)
2. Cross-reference service (address → LEP data)
3. External links (NSW Heritage DB, council studies)
4. Smart "missing context" detection

**Effort:** 16-20 hours
**Value:** High (fills Ashfield/Leichhardt gaps)

### Phase 3: Intelligence Features (Week 5-6)

**Components:**
1. Data completeness badges
2. Flexibility indicators
3. Council comparison view (optional)
4. Confidence scoring

**Effort:** 12-16 hours
**Value:** Moderate (polish and insight)

---

## User Value Proposition

### Before (Current State - Inconsistent)
```
Marrickville user:
  ✓ Rich heritage context
  ✓ Understanding of WHY
  ✓ Confidence in information

Ashfield user:
  ✗ No heritage context
  ✗ No understanding of WHY
  ✗ Uncertain if information is complete
  → Frustration, reduced confidence

Leichhardt user:
  ✗ No heritage context
  ~ Some flexibility mentioned
  ✗ Uncertain about data quality
  → Confusion, lack of control
```

### After (Unified Strategy - Consistent)
```
All users:
  ✓ Understand their council's personality upfront
  ✓ Know what to expect from DCP vs LEP
  ✓ Clear guidance on compliance strategy
  ✓ Confidence in data completeness
  ✓ Sense of control

Marrickville user:
  → "This council values design intent"

Ashfield user:
  → "This council is prescriptive, I'll check LEP for context"

Leichhardt user:
  → "This council allows process-based alternatives"
```

---

## Competitive Advantage

**No other planning tool provides:**
1. ✅ **Council personality insights** - data-driven compliance profiles
2. ✅ **Adaptive UX** - same framework, intelligent content adaptation
3. ✅ **Transparency** - explicit about what's missing and why
4. ✅ **Strategic guidance** - actionable per-council advice
5. ✅ **Smart enrichment** - fills gaps intelligently
6. ✅ **Cross-council intelligence** - comparison and insights

**This is a STRATEGIC DIFFERENTIATOR:**
- Based on actual data (not assumptions)
- Unifies inconsistent sources intelligently
- Gives users control through transparency
- Professional-level strategic intelligence

---

## Success Metrics

**User Understanding:**
- "I understand this council's approach": >80% agreement
- "I know where to find missing information": >90% agreement
- "I feel confident in the data quality": >75% agreement

**User Behavior:**
- Click-through rate on LEP links (Ashfield/Leichhardt): >40%
- Time spent viewing council strategy guide: >30 seconds
- Bounce rate reduction on requirements page: >20%

**User Satisfaction:**
- NPS increase: +15 points
- "Sense of control" rating: >4/5
- Support questions about missing data: -50%

---

## Technical Implementation

### Data Pipeline
```
Extraction → Quality Analysis → Profile Calculation → Enrichment → UI
   ↓              ↓                   ↓                  ↓          ↓
 LLM         Python stats        Council config      LEP data   React
```

### Automated Profile Updates
```python
# scripts/calculate_council_profiles.py
def calculate_unified_profiles() -> dict[str, CouncilProfile]:
    """
    Calculate profiles for all councils
    Ensures consistent classification logic
    """
    councils = ['Marrickville', 'Ashfield', 'Leichhardt']
    profiles = {}

    for council in councils:
        stats = get_council_stats(council)

        # Unified classification
        if stats.heritage_pct > 40 and stats.alternatives_pct > 25:
            style = 'performance'
            strictness = 'moderate'
            enrichment_priority = 'low'
        elif stats.heritage_pct < 20 and stats.alternatives_pct < 5:
            style = 'prescriptive'
            strictness = 'high'
            enrichment_priority = 'high'
        elif stats.alternatives_pct >= 5.0:
            style = 'process'
            strictness = 'moderate'
            enrichment_priority = 'high'
        else:
            style = 'hybrid'
            strictness = 'moderate'
            enrichment_priority = 'moderate'

        profiles[council] = CouncilProfile(
            style=style,
            strictness=strictness,
            heritage_context_pct=stats.heritage_pct,
            allows_alternatives_pct=stats.alternatives_pct,
            enrichment_priority=enrichment_priority,
            strategy_guidance=generate_guidance(council, style, strictness)
        )

    return profiles
```

---

## Conclusion

**The three-council analysis reveals an OPPORTUNITY for unified UX:**

Instead of treating data inconsistency as a problem:
1. ✅ **Expose differences transparently** as council personalities
2. ✅ **Provide unified framework** with intelligent adaptation
3. ✅ **Give users control** through transparency and guidance
4. ✅ **Enrich intelligently** to compensate for gaps
5. ✅ **Differentiate our product** with strategic intelligence

**This turns inconsistent source data into a unified, professional user experience.**

---

## Next Steps

1. ✅ **Complete:** Leichhardt extraction (in progress)
2. **Design:** Create UI mockups for unified framework (2-3 days)
3. **Implement Phase 1:** Unified framework (Week 1-2)
4. **Test:** User feedback on council personality insights
5. **Implement Phase 2:** Context enrichment (Week 3-4)
6. **Iterate:** Phase 3 based on feedback (Week 5-6)

---

## References

- Quality analysis: `check_leichhardt_v2_quality_simple.py`, `check_ashfield_v2_quality.py`
- Three-council comparison data: Session 2025-11-02
- Extraction scripts: `extract_*_v2_COMPLIANT.py`
- Original strategy: `COUNCIL_COMPLIANCE_PROFILES_UX_STRATEGY.md`
