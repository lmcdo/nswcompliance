# AI Layer Documentation Index

**Investigation Phase Complete:** 2026-02-01
**Ready for Implementation**

---

## Investigation Documents

### 1. Data Substrate Investigation
**File:** `docs/COMPLETE_DATA_SUBSTRATE_MAP.md`
**Purpose:** Complete inventory of all 200+ data fields available
**Key Findings:**
- 120 fields currently displayed (60% utilization)
- 80 fields exist but unused (tree canopy, ANEF, contextual guidance, cross-refs)
- All data sources mapped (Planning Portal, database, calculated)

### 2. Implementation Plan
**File:** `.claude/COMPLETE_DATA_EXPLOITATION_PLAN.md`
**Purpose:** Comprehensive plan to exploit ALL data with zero hallucination
**Key Decisions:**
- Use LLM ONLY for classification (current approach is safe)
- Replace LLM formatting with templates (safer, faster, cheaper)
- Enable all unused deterministic data (ZERO risk)
- Build multi-endpoint synthesis with templates (LOW risk)
- Implement safety layers (citation validation, confidence gating)

**Timeline:** 16 days total (6 phases)

### 3. Strategic Design
**File:** `docs/AI_LAYER_STRATEGIC_DESIGN.md`
**Purpose:** How to reference existing data, not regenerate
**Key Principles:**
- Cite exact sources (LEP clause, DCP page, SEPP section)
- Use determinate data (Planning Portal, database, calculations)
- Flag uncertainty (confidence scores, missing data)
- Refuse professional judgment (approval prediction, design advice)

### 4. Defensible Scope
**File:** `docs/AI_LAYER_DEFENSIBLE_SCOPE.md`
**Purpose:** What AI can/cannot answer, competitive positioning
**Key Claims:**
- 10,000+ actionable controls (vs PropCode's 1,000)
- Multi-layer synthesis (SEPP + LEP + DCP)
- 95-100% accuracy for factual lookups
- All answers cite exact regulatory sources

### 5. Provision Counts
**File:** `.claude/PROVISION_COUNTS.md`
**Purpose:** Accurate provision count breakdown for competitive defense
**Key Numbers:**
- 46,585 total provisions (10,008 actionable)
- 35,028 SEPP (State)
- 5,836 Inner West LEP (Local Law)
- 5,721 DCP (Design Guidelines)

---

## Quick Reference

### What Can AI Answer? (Defensible)

**Tier 1 - Fully Determinate (ZERO hallucination risk):**
- Lot dimensions (size, frontage, depth)
- Planning controls (height, FSR, zone)
- Property constraints (heritage, flood, bushfire)
- Parking calculations (rate × units × TOD)
- Permissibility (LEP land use table)
- Definitions (465+ terms in database)

**Tier 2 - Multi-Endpoint Synthesis (LOW risk, template-based):**
- "Can I build a granny flat?" (5 endpoints + template)
- "What setbacks apply?" (corner lot + heritage + precinct logic)
- "How many parking spaces for X units?" (calculation + template)

**Tier 3 - Refuse (Professional judgment):**
- "Will my DA be approved?" → REFUSE
- "Is this a good investment?" → REFUSE
- "Should I proceed?" → REFUSE

### What's Unused? (High Value)

**Zero Risk to Enable:**
- Tree canopy coverage (30 min)
- ANEF building acceptability (1 day)
- Corner lot confidence scores (1 hour)
- Amendment history (2 hours)

**Low Risk to Enable:**
- Contextual guidance (6,655 rows - plain language explanations)
- Cross-reference index (2,111 rows - related provisions)
- Database lookups replacing hardcoded data

### Implementation Priority

**Phase 1 (2 days):** Enable unused deterministic data
**Phase 2 (2 days):** Replace hardcoded with database
**Phase 3 (3 days):** Contextual guidance integration
**Phase 4 (3 days):** Cross-reference graph
**Phase 5 (4 days):** Multi-endpoint synthesis
**Phase 6 (2 days):** Safety layers

**Total:** 16 days to full exploitation

---

## Key Decisions

### ✅ KEEP: LLM for Classification
- **Why:** Handles natural language variation
- **Model:** Gemini Flash (cheap, fast, accurate enough)
- **Risk:** LOW (routing only, confidence threshold)

### ✅ CHANGE: Replace LLM Formatting with Templates
- **Why:** Safer (no free generation), faster, cheaper
- **How:** String templates with slot filling
- **Risk:** ZERO (no LLM involved)

### ✅ ADD: Safety Layers
- **Citation validation:** Verify all citations exist in database
- **Confidence gating:** Show uncertainty scores
- **Refusal patterns:** Block professional judgment questions

### ❌ DON'T: LLM for Content Generation
- **Never:** Generate regulatory text
- **Never:** Invent clause numbers or provisions
- **Never:** Fill missing data with estimates
- **Never:** Use multiple LLMs for "verification"

---

## Competitive Positioning

**PropCode Claims:**
- "1,000+ rules as code"
- Unknown accuracy, coverage, or citation quality

**PlotDetect Defensible Claims:**
- ✅ "10,000+ actionable controls" (verified)
- ✅ "Multi-layer synthesis (SEPP + LEP + DCP)" (unique)
- ✅ "95-100% accuracy for factual lookups" (deterministic)
- ✅ "All answers cite exact PDF pages" (verified)
- ✅ "Calculates parking with TOD reductions" (functional)

**Marketing Language:**
> "PlotDetect is the only planning tool that synthesizes State law (SEPP),
> Local law (LEP), and design standards (DCP) into one answer - with citations
> to exact PDF pages. Ask complex questions like 'Can I build a granny flat?'
> and get full eligibility checks, parking calculations, and setback requirements -
> all backed by 10,000+ structured planning controls."

---

## Next Steps

1. **Review plan** with stakeholders
2. **Start Phase 1** (enable tree canopy, ANEF, confidence - 2 days)
3. **Build Phase 5** (granny flat synthesis - 4 days) in parallel if desired
4. **Test with 5 real users** before wider release
5. **Launch outreach** with granny flat synthesis as hero feature

---

**Status:** Investigation complete, ready for implementation
**Last Updated:** 2026-02-01
**Contact:** See COMPLETE_DATA_EXPLOITATION_PLAN.md for technical details
