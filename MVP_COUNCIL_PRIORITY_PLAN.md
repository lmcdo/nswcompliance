# MVP Priority for Council Demonstration

## CRITICAL BLOCKER: Full Clause Citations (Must Fix First)
Currently, the system only has **summarized clause text**, not full regulatory paragraphs. Councils need complete, verifiable citations for legal authority.

**Priority 0: Fix Citation Data Gap**
```python
# Need to implement:
services/full_clause_extractor.py # Extract complete clause paragraphs from PDFs
services/clause_citation_store.py # Store clause_number → full_text mapping
services/citation_enrichment.py # Enhance existing results with full citations
```

## Recommended MVP Scope (in order):

### 1⃣ PRP-B1: Property Intelligence Engine (Week 1)
**Why Critical:** Councils want to see immediate value - "You can build X on this property"
- Calculate FSR, height, setbacks for specific properties
- Show buildable area calculations
- Demonstrate zone-specific intelligence
- **Council Value:** Reduces repetitive planning inquiries

### 2⃣ Full Citation System (Week 1-2)
**Why Critical:** Regulatory authority and legal compliance
- Complete clause text extraction from source PDFs
- Clause number → full paragraph mapping
- In-line citation display with source references
- **Council Value:** Provides authoritative, verifiable guidance

### 3⃣ PRP-B3: Rule-to-Action Transformer (Week 2)
**Why Critical:** Makes regulations actionable for residents
- Convert "Section 4.3.2" → "Measure 6m from front boundary"
- Step-by-step compliance instructions
- Plain English explanations
- **Council Value:** Reduces "how do I comply?" questions

### 4⃣ Confidence & Verification Layer (Week 3)
**Why Critical:** Council needs trust and transparency
- Show data sources for every calculation
- Confidence scores with explanations
- "Requires professional verification" flags
- Audit trail for all determinations
- **Council Value:** Manages liability and sets expectations

## MVP Demo Script for Council:

```
"Here's 34 Pile St, Dulwich Hill - a typical R2 property"

1. IMMEDIATE VALUE:
 "You can build 400m² on this 667m² lot"
 "Maximum 2 stories within 9.5m height limit"
 
2. FULL CITATIONS:
 "According to Marrickville DCP 2011, Section 4.1.5.1:"
 [Shows complete clause text with highlighting]
 
3. ACTIONABLE GUIDANCE:
 "To comply with setbacks:
 Step 1: Measure 6m from front boundary
 Step 2: Mark 0.9m from side boundaries"
 
4. COUNCIL EFFICIENCY:
 "This query would typically require 30 minutes 
 of council planner time. Now instant."
```

## What NOT to Include in MVP:
- Complex B2/B4 commercial zones (start with R2/R3)
- Heritage overlays (too complex initially)
- CDC pathway (DA only for MVP)
- Multi-council support (Inner West only)

## Success Metrics for Council:
1. **Accuracy**: 95%+ match with council determinations
2. **Time Savings**: 30 min → 30 sec per inquiry
3. **Citation Completeness**: 100% full text citations
4. **User Satisfaction**: Clear, actionable guidance

## Implementation Order:
```bash
# Week 1: Foundation
1. Fix citation data gap (extract full paragraphs)
2. Implement PRP-B1 (property intelligence)

# Week 2: Actionability 
3. Implement PRP-B3 (rule-to-action)
4. Add confidence scoring

# Week 3: Polish
5. Professional verification flags
6. Council branding/styling
7. Demo preparation
```

**The citation gap is the #1 blocker** - without full authoritative text, councils won't trust the system. This should be fixed before any other enhancements.