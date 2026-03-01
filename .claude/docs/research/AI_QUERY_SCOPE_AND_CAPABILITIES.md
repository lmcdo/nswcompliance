# AI Query Scope & Capabilities - Definitive Specification

**Purpose:** Define exactly what questions the AI can/cannot answer, complexity limits, professional stakeholder needs
**Status:** Critical scoping document - READ BEFORE IMPLEMENTATION
**Date:** 2026-02-01

---

## EXECUTIVE SUMMARY

### What This System IS
- **Intelligent data retrieval** from 46,585 structured provisions
- **Multi-source synthesis** (SEPP + LEP + DCP coordination)
- **Deterministic answers** with exact citations
- **Professional-grade reference tool** for compliance professionals

### What This System IS NOT
- **NOT an approval predictor** (no "will my DA be approved?")
- **NOT a design advisor** (no "should I do X or Y?")
- **NOT a regulatory interpreter** (no judgments on ambiguous clauses)
- **NOT a replacement for professional certifiers**

### Core Capability: "Reference Librarian" for Planning Controls
Think: LexisNexis for planning law, NOT ChatGPT for general advice

---

# PART 1: QUERY TAXONOMY & CAPABILITIES

## 1.1 Question Categories (8 Types)

### Category 1: FACTUAL LOOKUP (Single Data Point)
**Capability:** ✅ FULL - System excels at this

**Definition:** Direct retrieval of single deterministic fact from database or Planning Portal

**Examples (Answerable):**
```
✓ "What is the height limit for this property?"
✓ "What zone is 123 Main St in?"
✓ "Is this property heritage listed?"
✓ "What is the FSR for R3 zones?"
✓ "What is the tree canopy coverage?"
✓ "Is this property in a flood zone?"
✓ "What is the ANEF contour for aircraft noise?"
✓ "Is this a corner lot?"
```

**Data Sources:**
- Planning Portal API (zone, height, FSR, heritage, flood, bushfire, ANEF)
- Database lookups (parking rates, definitions, setbacks)
- Calculated fields (tree canopy, corner lot detection)

**Response Format:**
```
Tree canopy coverage: 25%
Source: NSW Planning Portal, imagery analysis
Confidence: High (direct measurement)
```

**Complexity:** LOW
**Confidence:** 95-100% (deterministic)
**Response Time:** <1s

---

### Category 2: CALCULATION (Apply Formula)
**Capability:** ✅ FULL - System calculates perfectly

**Definition:** Apply documented formula to property-specific data

**Examples (Answerable):**
```
✓ "How many parking spaces are required for 6 units?"
✓ "What is the maximum building height in meters?" (FSR × lot area)
✓ "What is the setback requirement?" (formula based on height)
✓ "What is the TOD parking reduction?" (distance from station)
✓ "What is the deep soil requirement?" (% of lot area by zone)
```

**Calculation Process:**
1. Retrieve base rate (e.g., 1 space per unit)
2. Apply modifiers (TOD reduction: -50% if <400m from station)
3. Show working (transparency)

**Response Format:**
```
Parking required: 3 spaces

Calculation:
- Base requirement: 6 units × 1 space/unit = 6 spaces
- TOD reduction: Within 400m of station = -50%
- Final: 6 × 0.5 = 3 spaces

Source: SEPP Housing 2021 Clause 16.4, Marrickville Station TOD Map
Confidence: High (deterministic calculation)
```

**Complexity:** LOW-MEDIUM
**Confidence:** 95-100% (if formula is unambiguous)
**Response Time:** <2s

---

### Category 3: PERMISSIBILITY CHECK (Land Use Table)
**Capability:** ✅ FULL - Deterministic lookup

**Definition:** Check if development type is permitted/prohibited in zone

**Examples (Answerable):**
```
✓ "Can I build a dwelling house in R2 zone?"
✓ "Is a restaurant permitted in B2 zone?"
✓ "Are boarding houses allowed here?" (check SEPP + LEP)
✓ "Can I run a home business?"
```

**Lookup Process:**
1. Get zone (Planning Portal or database)
2. Get development type (from question or context)
3. Check LEP land use table
4. Check SEPP overrides (e.g., SEPP Housing allows boarding houses in R zones)

**Response Format:**
```
Boarding houses: Permitted with consent

Reasoning:
1. Zone: R3 Medium Density Residential (from Planning Portal)
2. LEP: Boarding houses NOT listed in R3 table (prohibited)
3. SEPP: SEPP Housing 2021 Clause 13 overrides LEP (allows in R zones)
4. Result: Permitted with consent (SEPP override applies)

Sources:
- Inner West LEP 2022 Land Use Table
- SEPP Housing 2021 Clause 13
Confidence: High (clear SEPP override)
```

**Complexity:** MEDIUM (requires SEPP + LEP coordination)
**Confidence:** 90-95% (some ambiguity in development type classification)
**Response Time:** <2s

---

### Category 4: CONTEXTUAL GUIDANCE (Plain Language Explanation)
**Capability:** ✅ FULL - 6,655 pre-written guidance entries

**Definition:** Retrieve plain language explanation of technical DCP clause

**Examples (Answerable):**
```
✓ "What does 'deep soil zone' mean?"
✓ "Explain the setback requirements for corner lots"
✓ "What is a 'primary street frontage'?"
✓ "How is building height measured?"
```

**Data Source:** `contextual_guidance_real` table (6,655 rows)

**Response Format:**
```
Deep Soil Zone: An area of natural ground that is open to the sky and
free of buildings, structures, and hard paving. Must be at least 6m × 6m
to support tree planting.

Purpose: Supports healthy tree growth, stormwater infiltration, and
urban heat mitigation.

Applies to: Residential zones (R2, R3, R4) for developments >3 dwellings

Source: Marrickville DCP Section 4.1.7, Page 42
Confidence: High (direct quote from DCP guidance)
```

**Complexity:** LOW (direct retrieval)
**Confidence:** 100% (pre-written, no generation)
**Response Time:** <1s

**NOT answerable:**
```
✗ "Is my design sufficient for deep soil requirements?"
  → Requires professional judgment, site inspection
```

---

### Category 5: CROSS-REFERENCE (Related Provisions)
**Capability:** ✅ FULL - 2,111 pre-mapped relationships

**Definition:** Show related provisions that interact with queried control

**Examples (Answerable):**
```
✓ "What other provisions relate to setbacks?"
✓ "Are there heritage controls that affect height limits?"
✓ "What SEPP clauses override local parking rules?"
```

**Data Source:** `cross_reference_index` table (2,111 relationships)

**Response Format:**
```
Related to "Setback Requirements" (DCP 4.2.3):

1. Heritage setbacks (DCP 4.5.2)
   - If heritage item, match street setbacks of adjacent buildings

2. Corner lot provisions (DCP 4.2.4)
   - Additional setback requirements for secondary frontage

3. SEPP Housing override (Clause 17)
   - Reduced setbacks allowed for affordable housing

4. Tree preservation (DCP 4.1.8)
   - Setbacks may need to increase to protect significant trees

Source: Cross-reference index (curated relationships)
Confidence: High (manually verified relationships)
```

**Complexity:** MEDIUM (graph traversal)
**Confidence:** 95% (relationships are pre-verified)
**Response Time:** <2s

---

### Category 6: COMPARISON (Side-by-Side)
**Capability:** ⚠️ LIMITED - Only for structured data

**Definition:** Compare two controls/zones/development types

**Examples (Answerable with limitations):**
```
✓ "Compare parking rates for R2 vs R3 zones"
  → CAN answer (structured data exists)

✓ "What's the difference between a duplex and dual occupancy?"
  → CAN answer (definitions exist in database)

? "Compare setback requirements for Marrickville vs Leichhardt precincts"
  → PARTIAL (can show both, but user must compare)

✗ "Which zone is better for my development?"
  → CANNOT answer (requires professional judgment)
```

**Response Format (Answerable):**
```
Parking rates comparison:

R2 Low Density:
- Dwelling house: 1 space per dwelling
- Multi-dwelling: 1 space per unit
- Visitor parking: 1 space per 5 units

R3 Medium Density:
- Same as R2 (no difference in parking rates)
- Both subject to TOD reductions if applicable

Source: DCP Parking Rates Table, Section 3.8.2
Note: Actual requirement may vary based on unit size, TOD location
```

**Complexity:** MEDIUM (retrieve 2+ datasets, format for comparison)
**Confidence:** 90% (depends on data availability)
**Response Time:** <3s

**Edge Case Handling:**
- If comparison requires interpretation: **REFUSE** ("I can show you both, but you'll need to assess which applies to your situation")
- If data incomplete for one side: Show what's available, flag gaps

---

### Category 7: MULTI-ENDPOINT SYNTHESIS (Complex Multi-Step)
**Capability:** ⚠️ LIMITED - Only for pre-defined workflows

**Definition:** Coordinate multiple data sources to answer complex question

**Examples (Answerable - Pre-Defined Workflows):**

#### Workflow A: "Can I build a granny flat?"
```
✓ Answerable via 5-step synthesis:

Step 1: Permissibility (LEP + SEPP Housing)
- Check if granny flats permitted in zone
- SEPP Housing Clause 44: Allowed in R1-R4, RU5

Step 2: Lot size eligibility
- SEPP Housing: Minimum 450m² lot
- This property: 612m² ✓

Step 3: Existing dwelling requirement
- SEPP Housing: Must have existing dwelling
- Planning Portal: Existing dwelling confirmed ✓

Step 4: Parking calculation
- SEPP Housing: 1 space required (not subject to TOD reduction)
- Requires: 1 space

Step 5: Heritage considerations
- Planning Portal: Not heritage listed ✓
- No additional restrictions

Result: ELIGIBLE (all 5 criteria met)

Sources: SEPP Housing 2021 Clauses 44-48, Planning Portal
Confidence: High (clear SEPP criteria, deterministic checks)
```

**Response Format:**
```markdown
✅ Granny flat appears eligible (subject to detailed design review)

Eligibility checklist:
✓ Permitted in R2 zone (SEPP Housing Clause 44)
✓ Lot size sufficient (612m² > 450m² minimum)
✓ Existing dwelling present
✓ Parking requirement: 1 space needed
✓ No heritage restrictions

⚠️ Important:
- Final approval subject to detailed design (setbacks, height, landscaping)
- Recommend consulting with certifier for site-specific requirements
- This is eligibility only, not approval prediction

Next steps:
1. Review detailed design requirements (DCP Section 4.7)
2. Check setback requirements for secondary dwellings
3. Confirm water/sewer capacity with Sydney Water
```

#### Workflow B: "What setbacks apply to this corner lot?"
```
✓ Answerable via 4-source synthesis:

1. General setbacks (DCP 4.2.3)
   - Front: 5.5m (matches street pattern)
   - Side: 0.9m (non-habitable), 1.5m (habitable)
   - Rear: 6m

2. Corner lot provisions (DCP 4.2.4)
   - Secondary street setback: 3m minimum
   - Corner splay: 2m × 2m for sight lines

3. Heritage considerations
   - If heritage: Match adjacent buildings (varies)
   - This property: Not heritage ✓

4. Tree preservation (DCP 4.1.8)
   - 2m additional setback if tree within 5m of boundary
   - Tree present on north boundary: +2m setback required

Final setbacks for this corner lot:
- Primary street (south): 5.5m
- Secondary street (east): 3m
- North side: 1.5m + 2m (tree) = 3.5m
- Rear (west): 6m
```

**Pre-Defined Workflows (Phase 5):**
1. Granny flat eligibility
2. Corner lot setbacks
3. Boarding house compliance
4. Multi-dwelling parking calculation
5. Heritage development constraints

**Complexity:** HIGH (5+ data sources, template synthesis)
**Confidence:** 85-90% (more sources = more edge cases)
**Response Time:** <3s
**Development Effort:** 4 hours per workflow

**NOT answerable (requires custom synthesis):**
```
✗ "What's the full DA approval process for my mixed-use development?"
  → Too complex, too many variables, requires professional assessment

✗ "Can I subdivide and build 3 townhouses with a commercial unit?"
  → Multiple approval pathways, requires planning consultant

✗ "What's the best design strategy for maximizing height while respecting heritage?"
  → Professional design judgment required
```

---

### Category 8: DEFINITION LOOKUP
**Capability:** ✅ FULL - 465+ definitions in database

**Definition:** Retrieve exact definition from LEP/DCP/SEPP

**Examples (Answerable):**
```
✓ "What is a 'dwelling house'?"
✓ "Define 'floor space ratio'"
✓ "What counts as 'habitable room'?"
✓ "What is a 'heritage item'?"
```

**Response Format:**
```
Dwelling House (LEP 2022 Dictionary):

"A building containing only one dwelling"

Excludes:
- Attached dwellings (duplexes, townhouses)
- Secondary dwellings (granny flats)
- Multi-dwelling housing

Source: Inner West LEP 2022, Dictionary (Page 12)
Related: See also "Dual occupancy", "Secondary dwelling"
```

**Complexity:** LOW (dictionary lookup)
**Confidence:** 100% (exact quote)
**Response Time:** <1s

---

## 1.2 COMPLEXITY MATRIX

### Simple Queries (1-2s response, 95-100% confidence)
- Single data point retrieval (height, zone, FSR)
- Definition lookup
- Single calculation (parking for X units)
- Contextual guidance (pre-written)

**Characteristics:**
- 1 data source
- 0-1 calculations
- No conditional logic
- Deterministic answer

**User Experience:** Instant, confident answers

---

### Medium Queries (2-3s response, 85-95% confidence)
- Permissibility checks (LEP + SEPP coordination)
- Cross-references (related provisions)
- Comparisons (structured data only)
- Calculations with modifiers (TOD parking)

**Characteristics:**
- 2-3 data sources
- 1-2 conditional checks
- Some synthesis required
- Mostly deterministic

**User Experience:** Quick, mostly confident, occasional caveats

---

### Complex Queries (3-5s response, 80-90% confidence)
- Multi-endpoint synthesis (granny flat eligibility)
- Corner lot setbacks (4+ considerations)
- Pre-defined workflows only

**Characteristics:**
- 4-5 data sources
- Multiple conditional logic branches
- Template-based synthesis
- Edge cases possible

**User Experience:** Thorough checklist, caveats noted, professional review recommended

**LIMIT:** Only pre-defined workflows (Phase 5: 5 workflows built)

---

### Unviable Queries (Should REFUSE)
- Requires professional judgment
- Ambiguous regulatory interpretation
- Site-specific assessment needed
- Approval prediction
- Design recommendations
- Questions with >5 data dependencies

**Characteristics:**
- >5 data sources OR
- Requires interpretation OR
- Site visit needed OR
- Professional expertise required

**User Experience:** Polite refusal with explanation

---

## 1.3 EDGE CASES & HANDLING STRATEGY

### Edge Case 1: Data Unavailable
**Scenario:** User asks for parking rate, but precinct not in database

**Current Behavior (Bad):**
```
❌ "Parking required: [Unable to determine]"
```

**Correct Behavior (Phase 2 fix):**
```
✓ "I don't have parking rates for [Precinct Name] in my database yet.

General Inner West parking rates:
- Residential: 1 space per unit
- Visitor: 1 space per 5 units

Note: Check your specific precinct in DCP Section 3.8 for exact rates.
I can help you navigate to the right section."
```

**Handling:** Graceful degradation + guide user to manual lookup

---

### Edge Case 2: Ambiguous Question
**Scenario:** "What's the height limit?" (multiple buildings on lot? Existing building? New development?)

**Handling:**
```
Clarification needed:

Are you asking about:
1. Maximum building height allowed (planning control)
2. Height of existing building on this property
3. Height limit for a specific development type

Please clarify and I'll provide the exact answer.
```

**Strategy:** Never guess - always ask for clarification

---

### Edge Case 3: Conflicting Controls
**Scenario:** LEP says 11m, DCP says 10.5m, SEPP allows bonus height

**Handling:**
```
Height limit: COMPLEX - Multiple controls apply

LEP 2022: 11m maximum
DCP 2016: 10.5m recommended (design excellence)
SEPP Housing: Up to 12m for affordable housing (bonus)

Which applies? Depends on:
- Development type (affordable housing eligible for SEPP bonus?)
- Design excellence (does DCP "recommended" override LEP "maximum"?)

⚠️ Professional advice recommended
This requires interpretation - consult with certifier or planner.

I can show you the exact clauses:
- [LEP 2022 Height Map]
- [DCP Section 4.3.2]
- [SEPP Housing Clause 27]
```

**Strategy:** Show all controls, flag conflict, recommend professional interpretation

---

### Edge Case 4: Partial Data
**Scenario:** Corner lot detection confidence = 62% (below 80% threshold)

**Handling:**
```
Corner lot status: UNCERTAIN (62% confidence)

Why uncertain?
- Aerial imagery shows possible laneway frontage
- Cadastral boundaries unclear in this area
- May be corner lot OR side laneway lot

Recommendation:
- Check certificate of title for legal boundaries
- Verify with council GIS system

If corner lot:
- Additional setback requirements apply (DCP 4.2.4)
- Corner splay required for sight lines

[Show both scenarios]
```

**Strategy:** Show uncertainty explicitly, provide decision tree for both outcomes

---

### Edge Case 5: Out-of-Scope Question
**Scenario:** "Will my DA be approved?"

**Handling:**
```
I cannot predict DA approval outcomes.

Approval depends on:
- Detailed design quality
- Neighbor objections
- Council assessment priorities
- Site-specific conditions
- Professional assessment

What I CAN help with:
✓ Check if development type is permitted
✓ Calculate parking, setbacks, FSR
✓ Identify relevant planning controls
✓ Show DCP design requirements

For approval prediction: Consult with:
- Private certifier (complying development)
- Town planner (complex DAs)
- Council pre-DA meeting
```

**Strategy:** Explicit refusal + redirect to what system CAN do + professional referral

---

### Edge Case 6: Stale Data
**Scenario:** User asks about provision, but LEP was amended 3 months ago

**Handling (Future - not Phase 1):**
```
⚠️ This LEP clause was amended on [date]

Showing: Current version (Amendment 23, gazetted 2025-11-15)
Previous version available: [link to version history]

Height limit (CURRENT): 11m
Height limit (Previous): 9m
Change: Increased 2m via Amendment 23

Always verify latest version with council before lodging DA.
```

**Strategy:** Version tracking + amendment history (Phase 6 feature)

**Phase 1 Fallback:** Show date of last data update
```
Data current as of: 2026-01-15
Check NSW Planning Portal for any recent amendments.
```

---

### Edge Case 7: Multiple Valid Interpretations
**Scenario:** "Dwelling house" could mean existing house or proposed house

**Handling:**
```
"Dwelling house" has multiple meanings in your question:

Context 1: Land use definition
- "Dwelling house" = Single detached dwelling (LEP definition)
- Permitted in R1, R2, R3, R4 zones

Context 2: Existing building
- This property has an existing dwelling house (1920s Californian Bungalow)
- Heritage status: Not listed

Which are you asking about?
1. Can I build a dwelling house here? (permissibility)
2. Information about existing dwelling (building details)
3. Difference between dwelling house and other dwelling types (definition)
```

**Strategy:** Show all valid interpretations, ask user to specify

---

## 1.4 QUESTION STRUCTURING GUIDANCE (User Education)

### How to Ask Simple Questions (Best Results)

**GOOD Examples:**
```
✓ "What is the height limit?" (assumes current property context)
✓ "How many parking spaces for 6 units?"
✓ "Is this property heritage listed?"
✓ "What zone is this property in?"
```

**Why good:** One clear intent, system has all needed context

---

### How to Ask Complex Questions

**GOOD (Structured):**
```
✓ "For a 6-unit development on this property:
   1. What is the parking requirement?
   2. What is the FSR limit?
   3. What setbacks apply?"
```

**Why good:** Breaks complex question into answerable sub-questions

**BAD (Too broad):**
```
✗ "What do I need to know to build 6 units here?"
  → Too open-ended, unclear what aspect (parking? setbacks? approval process?)
```

**How system handles:**
```
Your question is broad. I can help with specific aspects:

For a 6-unit development, I can answer:
- Parking requirements
- Setback requirements
- FSR/height limits
- Permissibility check
- Deep soil requirements

Which would you like to know about? (You can ask multiple)
```

---

### How to Ask Multi-Step Questions

**GOOD:**
```
✓ "Can I build a granny flat?"
  → System has pre-defined workflow for this

✓ "What setbacks apply to this corner lot?"
  → System has pre-defined workflow for this
```

**NOT YET ANSWERABLE (future workflow):**
```
? "Can I subdivide and build 2 duplexes?"
  → Would require custom workflow (not yet built)
  → Phase 5+: Could be added as workflow #6
```

**How system handles:**
```
I don't have a pre-built workflow for subdivision + duplex development.

I can help with parts of your question:
✓ Check if duplexes are permitted in your zone
✓ Calculate parking for 4 total dwellings (2 duplexes)
✓ Show subdivision minimum lot sizes (LEP)

For full subdivision + development feasibility: Consult town planner
This involves multiple approval pathways and requires professional assessment.
```

---

### User Education: Suggested Questions Panel

**When user opens AI chat, show:**
```
What can I help you with?

Popular questions:
- "What is the height limit?"
- "How many parking spaces for X units?"
- "Can I build a granny flat?"
- "What setbacks apply to corner lots?"
- "Is this property heritage listed?"

Or ask your own question about planning controls.
```

**After answering, suggest related:**
```
Related questions you might ask:
- "What is the FSR limit?" (related control)
- "Are there heritage restrictions?" (common follow-up)
- "What is a dwelling house?" (definition)
```

---

# PART 2: PROFESSIONAL STAKEHOLDER NEEDS

## 2.1 Professional User Personas

### Persona 1: Private Certifier
**Profile:**
- Issues complying development certificates (CDCs)
- Needs: Fast, accurate regulatory lookups to verify compliance
- Pain points: Manual DCP navigation, multiple PDFs open, risk of missing controls
- Time pressure: Assessments must be quick (30-60 min per project)

**High-Value Needs:**
1. **Fast permissibility checks** ("Is granny flat permitted here?")
2. **Parking calculations** (with TOD reductions shown)
3. **Setback requirements** (all applicable controls in one place)
4. **Cross-reference warnings** ("Don't forget heritage setbacks!")
5. **Confidence in accuracy** (citations to exact clauses)

**How System Satisfies:**
- ✅ Granny flat eligibility workflow (saves 10 min per project)
- ✅ Parking calculator with working shown (saves 5 min, prevents errors)
- ✅ Corner lot setback synthesis (saves 15 min, catches edge cases)
- ✅ Cross-reference alerts (prevents missed requirements)
- ✅ Exact clause citations (confidence in accuracy)

**ROI for Certifier:**
- Time saved: 30 min per project
- Projects per day: 6 → 8 (+33% productivity)
- Error reduction: 95% accuracy vs 85% manual
- Professional confidence: Citations allow quick verification

**Adoption Path:**
1. Use for simple lookups (zone, height) → build trust
2. Try parking calculator → see time savings
3. Use granny flat workflow → high value, complex synthesis
4. Become power user → faster assessments, fewer errors

---

### Persona 2: Town Planner (Consultancy)
**Profile:**
- Prepares complex DAs for clients
- Needs: Comprehensive understanding of all applicable controls
- Pain points: Missing obscure controls, client asks "but what about...?"
- Time pressure: Proposals need to be thorough but efficient

**High-Value Needs:**
1. **Comprehensive control discovery** ("What ALL controls apply?")
2. **Cross-reference web** ("What heritage provisions affect height?")
3. **SEPP override identification** ("Does SEPP Housing apply here?")
4. **Contextual guidance** ("What does 'design excellence' mean in practice?")
5. **Comparison tools** ("Compare R2 vs R3 for this development type")

**How System Satisfies:**
- ✅ Cross-reference index (discovers related provisions)
- ✅ SEPP + LEP + DCP coordination (shows all layers)
- ✅ Contextual guidance (6,655 plain language explanations)
- ⚠️ Comparison (limited - shows side-by-side, user interprets)
- ✅ Comprehensive checklists (multi-endpoint synthesis)

**ROI for Planner:**
- Discovery time: 2 hours → 30 min (cross-reference web)
- Risk reduction: Catches obscure controls (e.g., tree preservation setbacks)
- Client confidence: "We checked every applicable control"
- Proposal quality: Comprehensive, defensible

**Adoption Path:**
1. Use for research (definitions, guidance) → discover value
2. Try cross-reference tool → find missed controls
3. Use for proposal review → QA checklist
4. Integrate into workflow → every proposal gets AI review

---

### Persona 3: Architect (Design Stage)
**Profile:**
- Designing residential development
- Needs: Quick feasibility checks during concept design
- Pain points: Don't want to read full DCP, just need key numbers
- Time pressure: Concept iterations need to be fast

**High-Value Needs:**
1. **Key numbers fast** ("Height, FSR, setbacks - that's it")
2. **Massing feasibility** ("Can I fit 6 units on this lot?")
3. **Parking reality check** ("How many spaces actually needed?")
4. **Heritage constraints** ("Will heritage kill this design?")
5. **Design guidance** ("What does DCP say about streetscape?")

**How System Satisfies:**
- ✅ Instant key numbers (height, FSR, setbacks in <2s)
- ⚠️ Massing calculation (FSR shown, architect calculates fit)
- ✅ Parking calculator (with TOD discounts)
- ✅ Heritage status check (quick yes/no)
- ✅ Contextual guidance (DCP design intent explained)

**ROI for Architect:**
- Concept iterations: 3 per day → 5 per day
- Fewer non-compliant designs: Catch issues early
- Client communication: "Here's what DCP requires" (instant cite)
- Design confidence: Know constraints upfront

**Adoption Path:**
1. Use during concept stage → get key numbers fast
2. Check parking during design → avoid redesign later
3. Review contextual guidance → understand DCP intent
4. Use before every client meeting → answer client questions instantly

---

### Persona 4: Developer (Feasibility Stage)
**Profile:**
- Assessing site acquisition
- Needs: Quick go/no-go decision on development potential
- Pain points: Paying consultant for every feasibility check (expensive)
- Time pressure: Must assess multiple sites per week

**High-Value Needs:**
1. **Permissibility** ("Can I build what I want here?")
2. **Yield calculation** ("How many units fit?")
3. **Parking burden** ("Will parking kill feasibility?")
4. **Heritage risk** ("Is this a heritage nightmare?")
5. **Granny flat eligibility** ("Can I add granny flat for yield?")

**How System Satisfies:**
- ✅ Permissibility check (land use table + SEPP overrides)
- ⚠️ Yield (shows FSR, developer calculates unit count)
- ✅ Parking calculator (shows total requirement + cost impact)
- ✅ Heritage status (instant red flag or green light)
- ✅ Granny flat workflow (full eligibility check)

**ROI for Developer:**
- Feasibility checks: $2,000 consultant → $0 (self-service)
- Speed: 3 days → 30 minutes (instant)
- Sites assessed: 1/week → 10/week (faster deal flow)
- Confidence: Preliminary check before committing consultant $$

**Adoption Path:**
1. Use for quick site screening → see speed advantage
2. Run granny flat check → discover bonus yield opportunities
3. Check parking burden → avoid high-parking sites
4. Become daily user → screen every potential acquisition

---

### Persona 5: Homeowner (DIY or Pre-Consult)
**Profile:**
- Considering renovation or granny flat
- Needs: Understand what's possible before hiring architect
- Pain points: DCP is impenetrable, don't know where to start
- Budget pressure: Want to know if project is feasible before spending on consultants

**High-Value Needs:**
1. **"Can I do this?"** (granny flat, extension, subdivision)
2. **Simple language** (no jargon, plain explanations)
3. **What's next** (if feasible, what are next steps?)
4. **Ballpark costs** (parking requirement = cost driver)
5. **When to hire professional** (clear guidance on limits)

**How System Satisfies:**
- ✅ Granny flat eligibility (instant go/no-go)
- ✅ Contextual guidance (plain language DCP explanations)
- ✅ Next steps guidance (system suggests "consult certifier")
- ✅ Parking shown (homeowner can estimate cost)
- ✅ Professional referral (system refuses complex questions, recommends expert)

**ROI for Homeowner:**
- Pre-consult research: 0 hours (too hard) → 30 min (guided)
- Avoided wasted consultations: $1,500 saved (if project not feasible)
- Confidence: Educated discussion with architect/certifier
- Realistic expectations: Understands constraints before committing

**Adoption Path:**
1. Try granny flat check → instant value (yes/no answer)
2. Read contextual guidance → understand DCP language
3. Get professional referral → knows when to hire expert
4. Returns for next project → trusted resource

---

## 2.2 Value Proposition Matrix

| User Type | Top Need | System Feature | Value Delivered | Adoption Trigger |
|-----------|----------|----------------|-----------------|------------------|
| **Certifier** | Fast compliance checks | Granny flat workflow | 30 min saved/project | First use of parking calculator |
| **Planner** | Comprehensive discovery | Cross-reference web | Catches missed controls | Discovers obscure provision they missed |
| **Architect** | Key numbers fast | Instant lookups | 2 iterations/day more | First time answers client Q in meeting |
| **Developer** | Feasibility screening | Permissibility + parking | $2k saved per site | Screens 10 sites in one day |
| **Homeowner** | "Can I do this?" | Granny flat eligibility | $1.5k consult avoided | Instant yes/no on granny flat |

---

## 2.3 Professional Trust Requirements

### What Builds Trust (CRITICAL)
1. **Exact citations** - Clause numbers, PDF page numbers
2. **Show working** - Calculations transparent (not black box)
3. **Flag uncertainty** - Confidence scores, "requires interpretation"
4. **Refuse when appropriate** - "This needs professional judgment"
5. **No hallucinations** - NEVER invent provisions or numbers

### What Destroys Trust (NEVER DO)
1. ❌ Invented clause numbers
2. ❌ Vague sources ("DCP says..." without section number)
3. ❌ Overconfident on ambiguous questions
4. ❌ Prediction of approval outcomes
5. ❌ Wrong calculations (worse than no answer)

### Trust Metrics
- **Citation accuracy:** 100% (every citation must be verifiable)
- **Calculation accuracy:** 100% (math errors are unacceptable)
- **Refusal rate:** 20-30% of questions (shows appropriate restraint)
- **False positives:** <1% (saying "yes" when should say "no")
- **False negatives:** <5% (saying "no" when should say "yes" - safer)

**Philosophy:** Better to refuse than to mislead

---

# PART 3: SYSTEM BOUNDARIES & LIMITATIONS

## 3.1 Hard Boundaries (Never Cross)

### Boundary 1: No Professional Judgment
**REFUSE:**
- "Will my DA be approved?"
- "Should I hire an architect or use a designer?"
- "Is this design good enough?"
- "Which option is better: X or Y?"

**Why:** Professional liability, requires site assessment, subjective

---

### Boundary 2: No Regulatory Interpretation
**REFUSE:**
- "What does 'unreasonable impact' mean in this case?"
- "Is my garage a 'carport' or 'garage'?" (ambiguous classification)
- "Does 'design excellence' apply here?"

**Why:** Requires legal/professional interpretation, councils disagree

---

### Boundary 3: No Site-Specific Assessment
**REFUSE:**
- "Where exactly should I place my building?"
- "Will this tree need to be removed?"
- "Is my soil suitable for on-site detention?"

**Why:** Requires site visit, professional assessment, engineering

---

### Boundary 4: No Predictions
**REFUSE:**
- "How long will DA approval take?"
- "Will neighbors object?"
- "Will council require a traffic study?"

**Why:** Unknowable, process varies, council discretion

---

### Boundary 5: No Legal Advice
**REFUSE:**
- "Can I sue council if they reject my DA?"
- "What are my legal rights under the EPA Act?"
- "Is this development legal or illegal?"

**Why:** Legal advice requires lawyer, professional liability

---

## 3.2 Soft Boundaries (Case-by-Case)

### Guidance Available, Application Requires Professional

**ANSWER (with caveat):**
```
Q: "What setbacks apply if I have a heritage item next door?"

A: "DCP Section 4.5.2 says: Developments adjacent to heritage items
should match the setback pattern of heritage buildings.

In practice: This requires:
- Measurement of adjacent heritage setbacks
- Assessment of 'predominant pattern'
- Professional judgment on what 'match' means

I can show you the DCP clause, but applying it to your site requires
a heritage consultant or planner.

[Show DCP clause excerpt]
```

**Strategy:** Provide the control, explain why application requires professional, show exactly where to look

---

### Data Available, Interpretation Required

**ANSWER (with caveat):**
```
Q: "How many units can I fit on this lot?"

A: "Maximum FSR: 0.75:1
Lot size: 800m²
Maximum GFA: 600m²

How many units? Depends on:
- Unit sizes (1-bed, 2-bed, 3-bed mix)
- Efficiency of design (circulation, parking access)
- Deep soil and landscaping requirements (reduce buildable area)

Typical yield:
- 1-bed (50m²): ~12 units (tight)
- 2-bed (75m²): ~8 units
- 3-bed (100m²): ~6 units

This is a ROUGH estimate. Architect must design to confirm actual yield.
```

**Strategy:** Provide data, show calculation, explain variables, refuse specific prediction

---

## 3.3 Complexity Limits

### Maximum Synthesis Complexity: 5 Endpoints

**Current Limit (Phase 5):**
- Granny flat eligibility: 5 endpoints (permissibility, lot size, parking, heritage, existing dwelling)
- Corner lot setbacks: 4 endpoints (general setbacks, corner provisions, heritage, trees)

**Why 5?**
- Response time: >5 endpoints = >5s response time (poor UX)
- Error compounding: Each endpoint adds 2-3% error risk
- Template complexity: >5 endpoints hard to synthesize coherently
- Edge case explosion: 2^5 = 32 possible combinations

**Future:** Could expand to 7-8 endpoints with caching, but diminishing returns

---

### Maximum Question Complexity: 3 Sub-Questions

**Answerable:**
```
✓ "For a 6-unit development: What's the parking requirement, setbacks, and height limit?"
  → 3 sub-questions, each answerable independently
```

**Too Complex:**
```
✗ "For a mixed-use development with retail, office, and 12 apartments, considering heritage overlay, flood zone, and acid sulfate soils, what approvals do I need and how long will it take?"
  → 10+ sub-questions, many unanswerable (predictions, process questions)
```

**How System Handles:**
```
Your question has multiple complex aspects. Let me break it down:

I CAN answer:
✓ Permissibility of mixed-use in your zone
✓ Parking requirements (retail + office + residential)
✓ Heritage restrictions that apply
✓ Flood controls
✓ Acid sulfate soil requirements

I CANNOT answer:
✗ "What approvals needed" (requires professional assessment of pathway)
✗ "How long will it take" (process timing unpredictable)

Would you like me to address the answerable parts?
```

---

# PART 4: IMPLEMENTATION PRIORITIES

## 4.1 Phase 1-2 (Simple Queries) - FOUNDATION

**Focus:** High-volume, high-confidence, low-complexity

**Answerable:**
- Factual lookups (zone, height, FSR, heritage)
- Single calculations (parking for X units)
- Definitions (465+ terms)
- Contextual guidance (6,655 entries)

**Not Yet:**
- Cross-references
- Multi-endpoint synthesis
- Comparisons

**Success Metric:** 80% of questions are this type, 95%+ accuracy

---

## 4.2 Phase 3-4 (Medium Queries) - DISCOVERY

**Focus:** Professional value, cross-provision discovery

**Add:**
- Cross-reference web (2,111 relationships)
- Permissibility checks (SEPP + LEP coordination)
- Comparisons (structured data only)

**Success Metric:** Professionals discover provisions they would have missed manually

---

## 4.3 Phase 5 (Complex Queries) - HIGH VALUE

**Focus:** 5 pre-defined workflows for highest-value questions

**Build:**
1. Granny flat eligibility (developer/homeowner value)
2. Corner lot setbacks (certifier pain point)
3. Boarding house compliance (planner need)
4. Multi-dwelling parking (common question)
5. Heritage development constraints (architect need)

**Success Metric:** Each workflow saves 20-30 min of professional time

---

## 4.4 Phase 6 (Safety & Trust) - CREDIBILITY

**Focus:** Ensure professional trust maintained

**Add:**
- Citation validation (verify all cited clauses exist)
- Confidence gating (block low-confidence responses)
- Hallucination detection (if template has {missing_field}, refuse)
- Appropriate refusals (boundary enforcement)

**Success Metric:** 0 false citations, <1% hallucinations

---

# PART 5: USER EDUCATION STRATEGY

## 5.1 First-Time User Experience

**Goal:** Set accurate expectations, avoid disappointment

**On first open:**
```
Welcome to PlotDetect AI Quick Reference

I can help you with:
✓ Planning control lookups (height, FSR, setbacks)
✓ Parking calculations
✓ Granny flat eligibility checks
✓ Definitions and guidance

I CANNOT:
✗ Predict DA approval
✗ Provide design advice
✗ Interpret ambiguous regulations

Ask a question to get started, or try:
- "What is the height limit?"
- "Can I build a granny flat?"
```

---

## 5.2 Question Suggestions (Contextual)

**After user enters address, suggest:**
```
Questions for 123 Main St, Marrickville:

Property-specific:
- "What zone is this property in?"
- "Is this property heritage listed?"
- "What is the height limit here?"

Common questions:
- "Can I build a granny flat?"
- "How many parking spaces for 6 units?"
- "What setbacks apply to corner lots?"
```

---

## 5.3 Refusal Education

**When refusing, teach what system CAN do:**
```
I cannot predict DA approval outcomes.

However, I CAN help you:
✓ Check if your development type is permitted
✓ Calculate parking, setbacks, FSR compliance
✓ Identify applicable planning controls
✓ Show DCP design requirements

These are the regulatory inputs to DA assessment.
For approval prediction: Consult certifier or planner.

Would you like to check any of the above?
```

---

## 5.4 Power User Features (Professional Mode)

**For professionals, offer:**
```
Professional Tools:

- Cross-reference web: See all related provisions
- Show working: See calculation steps
- Citation links: Jump to exact PDF page
- Version history: See when provision last amended
- Export answer: Save as PDF with citations

Enable Professional Mode? (More detail, less handholding)
```

---

# PART 6: SUCCESS METRICS & VALIDATION

## 6.1 Accuracy Metrics

**Target by Question Type:**

| Question Type | Target Accuracy | Current (Est.) | Gap |
|---------------|-----------------|----------------|-----|
| Factual lookup | 98% | 95% | -3% (Planning Portal API reliability) |
| Calculation | 99% | 90% | -9% (hardcoded rates, not DB) |
| Permissibility | 95% | 85% | -10% (SEPP overrides missed) |
| Contextual guidance | 100% | N/A | New feature |
| Cross-references | 95% | N/A | New feature |
| Multi-endpoint synthesis | 90% | N/A | New feature |

**How to Measure:**
- Sample 100 questions per type
- Compare AI answer vs manual lookup by professional
- Track false positives (wrong answer) separately from false negatives (refused when should answer)

---

## 6.2 Professional Adoption Metrics

**Leading Indicators:**
- Daily active professionals (certifiers, planners, architects)
- Questions per professional per day (engagement)
- Return rate (% who return after first use)

**Lagging Indicators:**
- Net Promoter Score (would you recommend?)
- Time saved per project (self-reported)
- Errors caught (provisions discovered that user missed)

**Target:**
- 60% of professional users return within 7 days
- Average 5 questions per professional per session
- NPS >50 (would recommend to colleagues)

---

## 6.3 Trust Metrics

**Track these rigorously:**
- Citation accuracy: 100% (every citation verifiable)
- Hallucination rate: <0.5% (strict detection)
- Refusal rate: 20-30% (shows restraint)
- Confidence calibration: When system says "High confidence", 95%+ accurate

**Red Flags (indicate trust erosion):**
- Users ask same question multiple times (don't trust first answer)
- Low click-through on citations (users don't verify = blind trust OR no trust)
- High question abandonment (start typing, don't submit = lost confidence)

---

**END OF SPECIFICATION**

---

## SUMMARY CHECKLIST

Before implementation, confirm:

- [ ] All 8 question categories defined with examples
- [ ] Complexity matrix understood (simple/medium/complex/refuse)
- [ ] 7 edge cases have handling strategies
- [ ] 5 professional personas mapped to value props
- [ ] Hard boundaries documented (never cross)
- [ ] Soft boundaries have templated caveats
- [ ] Phase 1-6 priorities aligned with capabilities
- [ ] User education strategy defined
- [ ] Success metrics measurable

**This document is the definitive scope. If a question type isn't listed above, default action: REFUSE and flag for future consideration.**

---

**Last Updated:** 2026-02-01
**Status:** CRITICAL - Read before implementation
**Next:** Integrate into master plan (Phase scoping)
**Owner:** Product/Implementation Team
