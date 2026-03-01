# UX Strategy: AI Layer Integration for Compliance Domain

**Context:** Planning/compliance is high-stakes, professional users need deterministic answers with evidence trails
**Challenge:** Integrate 200+ new data fields (6 phases) without overwhelming users while maintaining trust
**Current Style:** Declarative "Quick Reference" - shows rules, doesn't advise

---

## CURRENT SYSTEM ANALYSIS

### What Works (Keep/Enhance)

**1. Declarative Positioning**
```
"Quick Reference" (not "AI Assistant")
"Instant lookup of planning requirements"
"Shows what LEP, DCP, and SEPP rules say — not whether your project complies"
```
- ✅ Manages expectations (tool, not advisor)
- ✅ Builds trust (factual, not judgmental)
- ✅ Professional tone (for planners/certifiers)

**2. Confidence-Gated Responses**
- <50% confidence → Clarification request (no guessing)
- Suggested questions guide users
- Clear refusal states (amber badge, warning icon)

**3. Evidence Trail**
- Collapsible citations
- Source clauses shown
- Category badges (dev mode)

**4. Progressive Disclosure**
- Quick action chips (demonstrate scope)
- Property context banner (current address)
- Suggested follow-up questions
- Clean empty state

### What's Missing (New Requirements)

**With 6 phases of new data:**
- Tree canopy, ANEF, corner lot confidence
- Contextual guidance (6,655 "How to" explanations)
- Cross-references (2,111 related provisions)
- Multi-endpoint synthesis (granny flat eligibility)
- Database lookups (parking rates, land use tables)
- Safety layers (citation validation, confidence scores)

**Challenge:** How to surface all this without:
❌ Overwhelming users
❌ Breaking the declarative style
❌ Losing professional trust
❌ Making interface complex

---

## DOMAIN-SPECIFIC BEST PRACTICES

### Planning/Compliance Domain Characteristics

**User Types:**
1. **Certifiers** - Need audit trail, evidence, certainty
2. **Planners** - Need comprehensive view, cross-references
3. **Developers** - Need quick answers, feasibility checks
4. **Homeowners** - Need plain language, step-by-step

**Decision Contexts:**
- High stakes ($$$ / legal consequences)
- Multi-layered regulations (SEPP > LEP > DCP)
- Professional liability (certifiers sign off)
- Time-sensitive (project feasibility)

**Information Needs:**
- **Deterministic** over probabilistic
- **Citations** over summaries
- **Complete** over convenient
- **Precise** over approximate

### Best Practices from Adjacent Domains

**Legal Research (LexisNexis, Westlaw):**
- ✅ Show hierarchy (statutes > regulations > case law)
- ✅ Cited passages in context
- ✅ "Cited by" links (our cross-references)
- ✅ Uncertainty flags ("may apply", "depending on...")
- ✅ Professional disclaimers

**Tax/Accounting (TurboTax, H&R Block):**
- ✅ Guided workflows ("Start here" → "Then this")
- ✅ Plain language explanations alongside technical
- ✅ Confidence indicators ("We're certain" vs "You should verify")
- ✅ Line-item evidence (receipts = our citations)

**Medical Diagnosis (UpToDate, DynaMed):**
- ✅ Graded evidence quality
- ✅ "Clinical pearls" (our contextual guidance)
- ✅ Differential diagnosis (our multi-endpoint synthesis)
- ✅ NEVER diagnoses patient (our refusal patterns)

**Code Completion (GitHub Copilot, Cursor):**
- ✅ Inline suggestions (our quick actions)
- ✅ Alternative completions (our suggested questions)
- ✅ Confidence-based display (grey = uncertain)
- ❌ DON'T: Generate code freely (we don't generate regulations)

---

## PROPOSED UX STRATEGY

### Core Principle: Progressive Disclosure with Declarative Tone

**Tier 1: Direct Answers (Current)**
User asks → Single endpoint → Factual response

**Tier 2: Enriched Context (NEW - Phase 1-2)**
Direct answer + Supplementary deterministic data

**Tier 3: Guided Exploration (NEW - Phase 3-4)**
Direct answer + Related provisions + "How to" guidance

**Tier 4: Synthesis (NEW - Phase 5)**
Multi-endpoint combination with template

**Tier 5: Safety Layer (NEW - Phase 6)**
All above + Confidence gating + Citation validation

---

## DETAILED UX PATTERNS

### Pattern 1: Inline Confidence Indicators

**Problem:** Corner lot detection is 65% confident, but current UI doesn't show uncertainty

**Current (bad):**
```
Corner lot: Yes
Adjacent roads: Main St, Park Rd
```

**Proposed (declarative + honest):**
```
Corner lot: Possibly ⚠️
Confidence: 65% (medium)
Adjacent roads: Main St, Park Rd

📋 Recommendation: Verify with surveyor before relying on corner lot setback provisions

[Why uncertain?] ←collapse/expand
→ Lot geometry unclear from cadastral data
→ Road intersection proximity: 12m (borderline)
```

**Design:**
- Amber badge for <80% confidence
- Collapsible "Why uncertain?" for transparency
- Actionable recommendation (not just "maybe")
- Still declarative (shows data + limitation)

### Pattern 2: Contextual Guidance as "Plain Language Help"

**Problem:** 6,655 rows of "How to measure X" guidance - how to surface without cluttering?

**BAD APPROACH:**
- Inject guidance into every response (too verbose)
- Separate "Help" tab (disconnected from context)
- LLM explains on demand (hallucination risk)

**PROPOSED: Inline Collapsible Panels**

```
┌─────────────────────────────────────────┐
│ RESPONSE: Building height limit         │
│                                          │
│ Maximum building height: 9m              │
│ Source: Marrickville DCP 2011 Clause... │
│                                          │
│ ┌────────────────────────────────────┐  │
│ │ 📖 How to measure building height  │  │ ← Collapsed by default
│ └────────────────────────────────────┘  │
│   [Click to expand]                      │
│                                          │
│ Related questions:                       │
│ • What is the FSR for this property?    │
│ • Are there heritage setback requirements? │
└─────────────────────────────────────────┘
```

**When expanded:**
```
┌─────────────────────────────────────────┐
│ 📖 How to measure building height        │
│                                          │
│ Building height is measured as the      │
│ vertical distance from natural ground   │
│ level to the highest point of the       │
│ building, excluding:                     │
│ • Chimneys, vents, aerials              │
│ • Solar panels and water tanks          │
│ • Lift overruns                         │
│                                          │
│ Worked Example:                         │
│ [Diagram from DCP - if available]       │
│                                          │
│ Source: Marrickville DCP 2011 Section 2.1.3 │
│ Page 42                                  │
│                                          │
│ ℹ️ This guidance is extracted directly  │
│    from council DCPs (no paraphrasing). │
└─────────────────────────────────────────┘
```

**Why this works:**
- ✅ **Progressive disclosure** - Doesn't clutter main response
- ✅ **Declarative** - Shows existing DCP guidance verbatim
- ✅ **Trusted** - Clear source + "no paraphrasing" notice
- ✅ **Contextual** - Appears when relevant, not separate help section

### Pattern 3: Cross-Reference "Web"

**Problem:** 2,111 related provisions - showing all = overwhelming

**PROPOSED: Smart Collapsible with Categorization**

```
Response:
┌─────────────────────────────────────────┐
│ Side setback: 0.9m minimum               │
│ Source: Marrickville DCP 2011 Clause 2.3.4 │
│                                          │
│ ⚡ 3 related requirements [Show] ▼       │ ← Collapsed by default
└─────────────────────────────────────────┘
```

**When expanded:**
```
┌─────────────────────────────────────────┐
│ ⚡ Related requirements (3)              │
│                                          │
│ ALSO APPLY TO THIS SETBACK:             │
│ • Landscaping within setback (Cl 2.4.2) │
│   → 50% of setback area must be soft    │
│   [View provision →]                     │
│                                          │
│ AFFECTS CALCULATION:                     │
│ • Site coverage limit (Cl 2.3.1)        │
│   → Max 50% site coverage in R2 zone    │
│   [View provision →]                     │
│                                          │
│ IF CORNER LOT:                           │
│ • Secondary street setback (Cl 2.3.5)   │
│   → 3m to secondary street (vs 6m rear) │
│   [View provision →]                     │
│                                          │
│ 💡 These cross-references are from the  │
│    DCP index (not AI-generated links).  │
└─────────────────────────────────────────┘
```

**Categorization Strategy:**
- **"ALSO APPLY"** - Direct requirements for same area
- **"AFFECTS CALCULATION"** - Provisions that interact
- **"IF [condition]"** - Conditional cross-refs

**Why this works:**
- ✅ **Prevents missed requirements** - Certifiers see complete picture
- ✅ **Deterministic** - Graph query, not LLM-guessed relationships
- ✅ **Actionable** - Links to view full provision
- ✅ **Not overwhelming** - Collapsed by default, categorized when shown

### Pattern 4: Multi-Endpoint Synthesis with Transparency

**Problem:** Granny flat eligibility requires 5 endpoints - how to show without "black box" feeling?

**BAD APPROACH:**
```
Q: Can I build a granny flat?
A: Yes, you can build a granny flat here.
```
→ No evidence, no transparency, professional can't verify

**PROPOSED: Structured Checklist with Sources**

```
Q: Can I build a granny flat?

┌─────────────────────────────────────────┐
│ ✅ YES - Granny flats permitted          │
│                                          │
│ ELIGIBILITY CHECKS:                      │
│ ✅ Lot size: 450m²                       │
│    Requirement: 450m² minimum            │
│    Source: SEPP Housing 2021 Div 4.1    │
│    [View provision →]                    │
│                                          │
│ ✅ Zone: R2 Low Density Residential      │
│    Status: Permitted with consent        │
│    Source: Inner West LEP 2022 Cl 2.3   │
│    [View land use table →]               │
│                                          │
│ REQUIREMENTS:                            │
│ • Parking: 1 space required              │
│   Source: SEPP Housing 2021 Cl 38       │
│   TOD reduction: 25% available ℹ️        │
│   Final: 1 space (no reduction applied)  │
│                                          │
│ • Side setback: 0.9m minimum             │
│   Source: Marrickville DCP Part 2.3     │
│   ⚡ 2 related requirements [Show]       │
│                                          │
│ • Maximum GFA: 60m²                      │
│   Source: SEPP Housing 2021              │
│                                          │
│ APPROVAL PATHWAY:                        │
│ Option 1: Complying Development (CDC)   │
│   → If all standards met (no variations) │
│   → 20 business days                     │
│                                          │
│ Option 2: Development Application (DA)  │
│   → If variation needed                  │
│   → 40 business days (statutory)         │
│                                          │
│ 📋 Data sources (5):                     │
│ • NSW Planning Portal (lot size)        │
│ • SEPP Housing 2021 (eligibility)       │
│ • Inner West LEP 2022 (permissibility)  │
│ • Marrickville DCP 2011 (setbacks)      │
│ • TOD calculator (parking reductions)   │
│                                          │
│ ⚠️ DISCLAIMER:                           │
│ This synthesis combines multiple data   │
│ sources. Each requirement should be     │
│ verified in the source document before  │
│ submitting an application.              │
│                                          │
│ [Download full checklist PDF →]         │
└─────────────────────────────────────────┘
```

**Why this works:**
- ✅ **Audit trail** - Every statement has source
- ✅ **Verifiable** - Professional can check each item
- ✅ **Comprehensive** - Nothing hidden
- ✅ **Actionable** - Clear pathway (CDC vs DA)
- ✅ **Honest** - Disclaimer about synthesis
- ✅ **Declarative** - Shows what rules say, not "I recommend"

### Pattern 5: Safety Layer - Citation Validation UI

**Problem:** If hallucination detected, how to handle gracefully?

**PROPOSED: Transparent Error with Fallback**

```
Q: What are the parking requirements?

┌─────────────────────────────────────────┐
│ ⚠️ VERIFICATION ISSUE DETECTED           │
│                                          │
│ The system attempted to cite:            │
│ "SEPP Housing 2021 Clause 99"           │
│                                          │
│ This clause does not exist in our       │
│ database. This may indicate:            │
│ • Recent SEPP update not yet indexed    │
│ • Transcription error in our database   │
│ • Hallucination (incorrect citation)    │
│                                          │
│ FALLBACK: View all parking provisions   │
│ [Browse SEPP Housing parking rules →]   │
│                                          │
│ Or ask a planner to verify manually.    │
│                                          │
│ 📧 Report this issue [Click]            │
└─────────────────────────────────────────┘
```

**Why this works:**
- ✅ **Honest about limitation** - Doesn't hide errors
- ✅ **Actionable fallback** - User not stuck
- ✅ **Builds trust** - Shows quality control working
- ✅ **Feedback loop** - Report button improves system

---

## INFORMATION ARCHITECTURE

### Reorganize Response Structure (All Phases)

**Old Structure:**
```
User asks
 ↓
Single paragraph response
 ↓
Citations (collapsed)
 ↓
Suggested questions
```

**New Structure (Progressive Disclosure):**
```
User asks
 ↓
[CORE ANSWER]
  - Direct factual response
  - Primary source citation
 ↓
[CONFIDENCE INDICATORS] (if <80%)
  - Warning badge
  - Uncertainty explanation
  - Recommendation to verify
 ↓
[CONTEXTUAL GUIDANCE] (collapsible)
  - "How to measure/calculate" from DCP
  - Worked examples
  - Diagrams (if available)
 ↓
[RELATED REQUIREMENTS] (collapsible)
  - Cross-referenced provisions
  - Categorized (ALSO APPLY, AFFECTS, IF...)
 ↓
[SUPPLEMENTARY DATA] (collapsible)
  - Tree canopy, ANEF, environmental
  - Only if relevant to question
 ↓
[ALL SOURCES] (collapsible)
  - Complete citation list
  - Data provenance (Planning Portal, DB, etc.)
 ↓
[SUGGESTED QUESTIONS]
  - Guided next steps
```

**Visual Hierarchy:**
- **Bold** = Core answer (always visible)
- **Collapsible panels** = Progressive disclosure
- **Badges** = Visual signifiers (confidence, data type)
- **Icons** = Quick recognition (📖 guidance, ⚡ cross-refs, ⚠️ uncertainty)

---

## IMPLEMENTATION APPROACH

### Phase-by-Phase UX Rollout

**Phase 1: Confidence Indicators**
- Add uncertainty badges to existing responses
- "Why uncertain?" collapsible
- NO new data display (just honesty about existing)

**Phase 2: Database Lookups (Invisible to User)**
- Backend change only
- User sees same UI, but data from DB not hardcoded
- Verify no UX regression

**Phase 3: Contextual Guidance**
- Add "📖 How to..." collapsible panel
- Appears when guidance available
- User testing: Do they expand it? Is placement right?

**Phase 4: Cross-References**
- Add "⚡ Related requirements" collapsible
- Categorized display
- User testing: Does it help or overwhelm?

**Phase 5: Multi-Endpoint Synthesis**
- Add structured checklist format
- Comprehensive source list
- Disclaimer about synthesis
- User testing: Do certifiers trust it?

**Phase 6: Safety Layer**
- Add citation validation error UI
- Report button for issues
- Monitor hallucination rate

### A/B Testing Strategy

**Test 1: Guidance Panel Placement**
- A: Above suggested questions
- B: Below suggested questions
- C: Inline within answer (contextual)
- Metric: Expansion rate, perceived helpfulness

**Test 2: Cross-Reference Display**
- A: Flat list
- B: Categorized (ALSO APPLY, AFFECTS, IF...)
- C: Graph visualization
- Metric: Comprehension, missed requirements

**Test 3: Synthesis Format**
- A: Paragraph (current style)
- B: Checklist (proposed)
- C: Table
- Metric: Professional trust, verifiability

---

## MOCKUPS (TEXT-BASED)

### Example 1: Simple Query with Phase 1-3 Enhancements

**Query:** "What's the height limit?"

```
┌─────────────────────────────────────────┐
│ 👤 What's the height limit?             │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ 🏛️ Maximum building height: 9m           │
│                                          │
│ Source: Inner West LEP 2022 Clause 4.3  │
│ [View provision →]                       │
│                                          │
│ ┌────────────────────────────────────┐  │
│ │ 📖 How to measure building height  │  │
│ └───────────────────[Expand ▼]──────┘  │
│                                          │
│ ┌────────────────────────────────────┐  │
│ │ ⚡ 1 related requirement           │  │
│ └───────────────────[Show ▼]────────┘  │
│                                          │
│ Related questions:                       │
│ • What is the FSR for this property?    │
│ • Are there setback requirements?       │
│                                          │
│ 2 sources • Response time: 1.2s         │
└─────────────────────────────────────────┘
```

### Example 2: Uncertain Data with Phase 1+6

**Query:** "Is this a corner lot?"

```
┌─────────────────────────────────────────┐
│ 👤 Is this a corner lot?                │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ 🏛️ Corner lot: Possibly ⚠️                │
│                                          │
│ Confidence: 65% (MEDIUM)                 │
│                                          │
│ Adjacent roads:                          │
│ • Main St                                │
│ • Park Rd                                │
│                                          │
│ ┌────────────────────────────────────┐  │
│ │ ⚠️ Why uncertain?                  │  │
│ │ • Lot geometry unclear from        │  │
│ │   cadastral data                   │  │
│ │ • Road intersection proximity:     │  │
│ │   12m (borderline)                 │  │
│ │                                    │  │
│ │ Detection method: Geometric        │  │
│ │ analysis of road parcels          │  │
│ └────────────────────────────────────┘  │
│                                          │
│ 📋 RECOMMENDATION:                       │
│ Engage surveyor to verify corner lot    │
│ status before relying on corner lot     │
│ setback provisions (3m secondary street  │
│ vs 6m rear for non-corner).             │
│                                          │
│ ┌────────────────────────────────────┐  │
│ │ 📖 What is a corner lot?           │  │
│ └───────────────────[Expand ▼]──────┘  │
│                                          │
│ Related questions:                       │
│ • What are the setback requirements?    │
│ • What is the secondary street setback? │
│                                          │
│ Source: Calculated from cadastral data  │
└─────────────────────────────────────────┘
```

### Example 3: Granny Flat Synthesis (Phase 5)

**Query:** "Can I build a granny flat?"

```
┌─────────────────────────────────────────┐
│ 👤 Can I build a granny flat?           │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ 🏛️ ✅ YES - Granny flats permitted       │
│                                          │
│ ELIGIBILITY:                             │
│ ✅ Lot size: 450m²                       │
│    └─ Requirement: 450m² minimum        │
│       Source: SEPP Housing 2021 Div 4.1 │
│                                          │
│ ✅ Zone: R2 Low Density Residential      │
│    └─ Status: Permitted with consent    │
│       Source: Inner West LEP 2022       │
│                                          │
│ REQUIREMENTS:                            │
│ • Parking: 1 space                       │
│   └─ SEPP Housing 2021 Cl 38            │
│       TOD reduction: 25% available ℹ️    │
│                                          │
│ • Side setback: 0.9m minimum             │
│   └─ Marrickville DCP Part 2.3          │
│       ⚡ 2 related [Show]                │
│                                          │
│ • Maximum GFA: 60m²                      │
│   └─ SEPP Housing 2021                  │
│                                          │
│ ┌────────────────────────────────────┐  │
│ │ APPROVAL PATHWAY                   │  │
│ │                                    │  │
│ │ ✅ Complying Development (CDC)      │  │
│ │ If all standards met               │  │
│ │ • 20 business days                 │  │
│ │ • Certifier approval               │  │
│ │                                    │  │
│ │ OR                                 │  │
│ │                                    │  │
│ │ Development Application (DA)       │  │
│ │ If variation needed                │  │
│ │ • 40 business days (statutory)     │  │
│ │ • Council approval                 │  │
│ └────────────────────────────────────┘  │
│                                          │
│ ┌────────────────────────────────────┐  │
│ │ 📋 DATA SOURCES (5)                │  │
│ │ • NSW Planning Portal (lot size)   │  │
│ │ • SEPP Housing 2021 (eligibility)  │  │
│ │ • Inner West LEP 2022 (zone)       │  │
│ │ • Marrickville DCP (setbacks)      │  │
│ │ • TOD calculator (parking)         │  │
│ └────────────────────────────────────┘  │
│                                          │
│ ⚠️ DISCLAIMER:                           │
│ This synthesis combines multiple data   │
│ sources. Verify each requirement in     │
│ source document before applying.        │
│                                          │
│ [Download checklist PDF →]              │
│                                          │
│ Related questions:                       │
│ • What are the SEPP Housing design standards? │
│ • How do I apply for a CDC?             │
│                                          │
│ 5 sources • Response time: 2.8s         │
└─────────────────────────────────────────┘
```

---

## USER TESTING PROTOCOL

### Phase 1-3 Testing (5 Users)

**Participants:**
- 2 certifiers
- 2 planners
- 1 developer

**Tasks:**
1. "Find the height limit for 123 Main St"
   - Do they notice guidance panel?
   - Do they expand it?
   - Do they trust the guidance?

2. "Check if corner lot"
   - Do they understand uncertainty?
   - Do they follow recommendation?
   - Does it change their confidence in system?

3. "Find setback requirements"
   - Do they notice cross-references?
   - Do they find them helpful?
   - Do they view related provisions?

**Metrics:**
- Task completion rate
- Time to answer
- Confidence in answer (1-5 scale)
- Trust in system (1-5 scale)
- Feature discovery rate

**Success Criteria:**
- >80% task completion
- Confidence ≥4.0
- Trust ≥4.0 (no decrease from current)

### Phase 5 Testing (Granny Flat Synthesis)

**Critical question:** Do certifiers trust synthesized responses?

**Test:**
1. Show granny flat synthesis
2. Ask: "Would you use this in your professional practice?"
3. Ask: "What would you need to verify independently?"
4. Ask: "How does this compare to your manual process?"

**Success Criteria:**
- >60% say "yes, would use"
- Can articulate what to verify (shows understanding)
- Faster than manual process

---

## RISK MITIGATION

### Risk 1: Information Overload

**Symptom:** Users stop engaging because too much content

**Mitigation:**
- Collapsible panels (progressive disclosure)
- Smart defaults (only show relevant sections)
- User testing at each phase
- Analytics: Track expansion rates

**Rollback:** Remove collapsible features, back to flat response

### Risk 2: Lost "Declarative" Tone

**Symptom:** Synthesis responses feel like AI advice, not factual lookup

**Mitigation:**
- Template-based formatting (no free LLM generation)
- Every statement has citation
- Disclaimer about synthesis
- "Shows what rules say" framing maintained

**Validation:** User testing - does it still feel like "Quick Reference"?

### Risk 3: Professional Trust Erosion

**Symptom:** Certifiers stop using because can't verify sources

**Mitigation:**
- Hyper-transparent sourcing (list all 5 endpoints)
- "Verify before applying" disclaimer
- Citation validation catches errors
- Feedback mechanism for issues

**Monitoring:** Track certifier usage over time, survey quarterly

### Risk 4: Performance Degradation

**Symptom:** Response time >3 seconds, users frustrated

**Mitigation:**
- Parallel endpoint calls (Phase 5)
- Cache guidance/cross-refs
- Progressive loading (show core answer first, enrich later)
- Performance budget: 3s max

**Monitoring:** Log response times, alert if >3s for >10% of requests

---

## SUCCESS METRICS

### Quantitative

**Engagement:**
- Daily active users (maintain or grow)
- Questions per session (increase expected with more features)
- Expansion rate on collapsible panels (>20% = users find value)

**Performance:**
- Response time <3s (95th percentile)
- Error rate <1% (hallucination + citation validation)
- Uptime >99.9%

**Quality:**
- Accuracy: 95%+ match vs manual lookup
- Citation validation pass rate >99%
- User-reported issues <5 per week

### Qualitative

**User Satisfaction (Survey):**
- "I trust this tool" ≥4.5/5
- "This is faster than manual lookup" ≥4.0/5
- "I understand the source of information" ≥4.5/5
- "I would recommend to colleague" ≥4.0/5

**Professional Adoption:**
- Certifiers using in practice >20%
- Planners using daily >50%
- Developers using for feasibility >60%

---

## RECOMMENDATIONS

### Immediate (Pre-Implementation)

1. ✅ **User test current system** - Establish baseline metrics
2. ✅ **Mockup Phase 1-3** - Get user feedback before coding
3. ✅ **Define analytics** - What to track at each phase

### Phase Rollout

1. **Phase 1 (Confidence)** - Low risk, high trust-building
2. **Phase 2 (DB lookups)** - Invisible to user, validate no regression
3. **Phase 3 (Guidance)** - Test expansion rates, placement
4. **Phase 4 (Cross-refs)** - Test comprehension, usefulness
5. **Phase 5 (Synthesis)** - Most risky, extensive testing before launch
6. **Phase 6 (Safety)** - Continuous monitoring

### Long-term

- **Personalization** - Remember user role (certifier vs homeowner), adjust UX
- **Saved queries** - "My common questions" for professionals
- **Export options** - PDF checklist, CSV for records
- **Comparison mode** - "Compare 2 properties" for developers

---

## CONCLUSION

**Declarative style is the right approach** - maintains professional trust in high-stakes domain

**Progressive disclosure is key** - Show complexity only when needed

**Transparency builds trust** - Every synthesis must show sources, every uncertainty must be flagged

**Test incrementally** - Each phase validated before next

**The goal:** Professional tool that shows complete picture without overwhelming users, maintains deterministic feel while leveraging all 200+ data fields

**Next:** Mockups → User testing → Refine → Implement
