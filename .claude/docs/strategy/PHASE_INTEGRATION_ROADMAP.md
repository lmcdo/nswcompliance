# Phase Integration Roadmap - Complex Workflows

**Purpose:** Integrate complex workflow implementation into existing 6-phase timeline
**Date:** 2026-02-01

---

## CURRENT PHASE STRUCTURE (16 Days Total)

### Phase 1 (2 days): Deterministic Data
- Enable unused data (tree canopy, ANEF, corner lot confidence)
- Low risk, high value quick wins

### Phase 2 (2 days): Database Lookups
- Replace hardcoded with database queries
- Parking rates, setback tables, definitions

### Phase 3 (3 days): Contextual Guidance
- Integrate 6,655 plain language explanations
- Progressive disclosure UX

### Phase 4 (3 days): Cross-Reference Graph
- 2,111 relationship mappings
- "Related provisions" discovery

### Phase 5 (4 days): Multi-Endpoint Synthesis
- **THIS IS WHERE COMPLEX WORKFLOWS GO**
- Currently vague - needs specifics

### Phase 6 (2 days): Safety Layers
- Citation validation
- Hallucination detection
- Confidence gating

---

## PROBLEM: Phase 5 Too Vague

**Current description:** "Multi-endpoint synthesis"
- Which workflows exactly?
- In what order?
- 5 already exist vs 10 to build - which are which?

**Research findings:**
- 5 workflows ALREADY IMPLEMENTED (granny flat, permissibility, parking, capacity, precinct)
- 10 workflows PRIORITIZED for build (15 hours development)

**Question:** Does Phase 5 build the existing 5, or the next 10?

---

## REVISED PHASE 5 STRUCTURE (Detailed)

### Phase 5A: Validate Existing Workflows (Day 13)

**Assumption:** The 5 "implemented" workflows exist but need AI layer integration

**Workflows to Validate (6 hours):**
1. **Granny flat eligibility** (1 hour)
   - Verify API `/api/housing-sepp/eligibility` works
   - Add AI chat integration (route from question classification)
   - Test response formatting

2. **Permissibility check** (1 hour)
   - Verify API `/api/permissibility/check`
   - Add SEPP override synthesis to responses
   - Test with 5 dev types

3. **Parking calculation with TOD** (1 hour)
   - Verify TOD distance calculation
   - Add "show working" to response
   - Test with 10 addresses

4. **Capacity calculation** (2 hours)
   - Verify FSR + setback + parking synthesis
   - Add comprehensive checklist output
   - Test edge cases

5. **Precinct requirements** (1 hour)
   - Verify categorization logic
   - Add cross-reference links
   - Test with 5 precincts

**Remaining Day 13 (2 hours):**
- Integration testing
- Response format consistency
- Error handling

---

### Phase 5B: Build Priority Workflows (Days 14-15)

#### Day 14 Morning: Corner Lot Setbacks (4 hours)

**Implementation:**
```typescript
// lib/ai/workflows/corner-lot-setbacks.ts

interface CornerLotSetbacksInput {
  zone: string;
  formerCouncil: string;
  isCornerLot: boolean;
  heritage: boolean;
  hasTreesNearBoundary: boolean;
  coordinates: [number, number];
}

async function synthesizeCornerLotSetbacks(input: CornerLotSetbacksInput) {
  // Step 1: General setbacks (always)
  const general = await db.getGeneralSetbacks(input.zone, input.formerCouncil);

  // Step 2: Corner provisions (conditional)
  const corner = input.isCornerLot
    ? await db.getCornerLotProvisions(input.zone, input.formerCouncil)
    : null;

  // Step 3: Heritage modifications (conditional)
  const heritage = input.heritage
    ? await db.getHeritageSetbackModifications(input.heritage)
    : null;

  // Step 4: Tree preservation (conditional)
  const trees = input.hasTreesNearBoundary
    ? await db.getTreePreservationSetbacks(input.coordinates)
    : null;

  return formatCornerLotSetbackResponse({
    primary: general.front,
    secondary: corner?.secondaryStreet || general.side,
    side: general.side + (trees?.buffer || 0),
    rear: general.rear,
    modifications: [...heritage?.mods || [], ...trees?.buffers || []],
    sources: [general.source, corner?.source, heritage?.source, trees?.source].filter(Boolean),
    caveats: generateCaveats(input)
  });
}
```

**Testing:** 10 corner lot addresses, verify secondary street setback shown

---

#### Day 14 Afternoon: Heritage + Setback Interaction (3 hours)

**Implementation:**
```typescript
// lib/ai/workflows/heritage-setback-interaction.ts

async function synthesizeHeritageSetbacks(input: PropertyInput) {
  const heritage = await planningPortal.getHeritageStatus(input.address);

  if (!heritage || heritage === 'none') {
    return { heritageStatus: 'none', useGeneralSetbacks: true };
  }

  const general = await db.getGeneralSetbacks(input.zone, input.formerCouncil);
  const hca = heritage.conservationArea
    ? await db.getHCAProvisions(heritage.conservationArea)
    : null;

  // Key logic: Heritage often requires "match prevailing setback"
  const setbackModifications = [];
  if (hca?.setbackRequirement === 'match_adjacent') {
    setbackModifications.push({
      type: 'match_adjacent',
      description: 'Front setback must match adjacent heritage buildings',
      source: hca.source,
      caveat: 'Requires surveyor measurement + heritage consultant interpretation'
    });
  }

  return formatHeritageSetbackResponse({
    heritageStatus: heritage.type,
    setbackModifications,
    generalSetbacks: general,
    professionalRequired: true,
    nextSteps: ['Engage heritage consultant', 'Pre-DA meeting with council']
  });
}
```

**Testing:** 10 heritage properties, verify "match adjacent" guidance shown

---

#### Day 15 Morning: Multi-Dwelling Parking + Boarding House (5 hours)

**Multi-Dwelling Parking (2 hours):**
```typescript
// lib/ai/workflows/multi-dwelling-parking.ts

async function calculateMultiDwellingParking(
  units: { type: '1bed' | '2bed' | '3bed'; count: number }[],
  coordinates: [number, number]
) {
  // Resident parking (varies by unit size)
  const residentBreakdown = await Promise.all(
    units.map(async u => ({
      unitType: u.type,
      count: u.count,
      rate: await db.getParkingRate('multi_dwelling', u.type),
      subtotal: u.count * (await db.getParkingRate('multi_dwelling', u.type))
    }))
  );

  const residentTotal = residentBreakdown.reduce((sum, u) => sum + u.subtotal, 0);

  // TOD reduction
  const todReduction = await calculateTODReduction(coordinates, residentTotal);

  // Visitor (1 per 5 units)
  const totalUnits = units.reduce((sum, u) => sum + u.count, 0);
  const visitorSpaces = Math.ceil(totalUnits / 5);

  // Accessibility (1 per 50 spaces, min 1)
  const accessibilitySpaces = Math.max(1, Math.ceil((todReduction?.reducedTotal || residentTotal) / 50));

  return formatMultiDwellingParkingResponse({
    resident: { breakdown: residentBreakdown, total: residentTotal, todReduction },
    visitor: { required: visitorSpaces },
    accessibility: { required: accessibilitySpaces },
    total: (todReduction?.reducedTotal || residentTotal) + visitorSpaces
  });
}
```

**Boarding House Compliance (3 hours):**
```typescript
// lib/ai/workflows/boarding-house-compliance.ts

async function checkBoardingHouseCompliance(address: string, rooms: number) {
  // Step 1: Permissibility (SEPP override)
  const zone = await planningPortal.getZone(address);
  const permitted = await checkSEPPHousingOverride('boarding_house', zone);

  // Step 2: SEPP Housing standards
  const standards = await db.getSEPPHousingStandards('boarding_house');

  // Step 3: Lot size check
  const lotDimensions = await planningPortal.getLotDimensions(address);
  const meetsLotSize = lotDimensions.area >= standards.minLotSize;

  // Step 4: Parking calculation
  const parking = rooms <= 12
    ? { required: 0, reason: 'Boarding houses ≤12 rooms: no parking required (SEPP Clause 29)' }
    : { required: Math.ceil(rooms / 5), reason: `${rooms} rooms: 1 space per 5 rooms` };

  return formatBoardingHouseResponse({
    permitted,
    standards,
    meetsLotSize,
    parking,
    pathway: permitted && meetsLotSize ? 'DA' : 'Not viable',
    professionalRecommendation: 'Town planner required - boarding houses have complex requirements'
  });
}
```

---

#### Day 15 Afternoon: Subdivision + Deep Soil (5 hours)

**Subdivision Feasibility (3 hours):**
```typescript
// lib/ai/workflows/subdivision-feasibility.ts

async function checkSubdivisionFeasibility(address: string, proposedLots: number) {
  const zone = await planningPortal.getZone(address);
  const currentLot = await planningPortal.getLotDimensions(address);

  // Step 1: Minimum lot size (by zone)
  const minLotSize = await db.getMinimumLotSize(zone);

  // Step 2: Minimum frontage
  const minFrontage = await db.getMinimumFrontage(zone);

  // Step 3: Access requirements
  const accessReqs = await db.getAccessRequirements(zone);

  const resultingLotSize = currentLot.area / proposedLots;
  const viable = resultingLotSize >= minLotSize;

  return formatSubdivisionResponse({
    currentLotSize: currentLot.area,
    proposedLots,
    resultingLotSize,
    minLotSize,
    viable,
    frontageRequirement: minFrontage,
    accessRequirement: accessReqs,
    caveats: [
      'Subdivision requires DA approval',
      'Each lot must meet minimum frontage',
      'Battle-axe lots have additional access width requirements',
      'Recommend surveyor + town planner consultation'
    ]
  });
}
```

**Deep Soil Calculation (2 hours):**
```typescript
// lib/ai/workflows/deep-soil-calculation.ts

async function calculateDeepSoilRequirement(zone: string, lotArea: number, dwellings: number) {
  // Step 1: Get percentage requirement (by zone)
  const deepSoilPercent = await db.getDeepSoilPercentage(zone);

  // Step 2: Exemptions (small lots)
  const exemptions = await db.getDeepSoilExemptions(zone, lotArea);

  // Step 3: Minimum dimensions (6m × 6m for trees)
  const minDimensions = { width: 6, depth: 6 };

  const required = exemptions.exempt
    ? { area: 0, reason: exemptions.reason }
    : { area: lotArea * (deepSoilPercent / 100), percentage: deepSoilPercent };

  return formatDeepSoilResponse({
    lotArea,
    required,
    minDimensions,
    treePlanting: required.area >= 36 ? 'Required (space sufficient for tree)' : 'Not required',
    sources: [/* DCP sections */]
  });
}
```

---

#### Day 16: Testing, Refinement, Integration (8 hours)

**Morning (4 hours): Comprehensive Testing**
- Test all 10 workflows with 100 real queries
- Edge case testing (missing data, conflicts, low confidence)
- Performance testing (response time <3s)
- Citation accuracy verification (100% must be verifiable)

**Afternoon (4 hours): UX Integration**
- Progressive disclosure (collapsible sections)
- Confidence indicators (<80% = warning badge)
- "Show working" for calculations
- Professional recommendations (when to consult expert)
- Suggested follow-up questions

---

## REVISED 16-DAY TIMELINE

| Day | Phase | Activities | Workflows Added |
|-----|-------|------------|-----------------|
| 1-2 | Phase 1 | Enable deterministic data | Tree canopy, ANEF, corner lot confidence |
| 3-4 | Phase 2 | Database lookups | Parking rates, setback tables |
| 5-7 | Phase 3 | Contextual guidance | 6,655 plain language explanations |
| 8-10 | Phase 4 | Cross-references | 2,111 relationship mappings |
| 11-12 | Phase 4 | Cross-reference UX | Related provisions display |
| **13** | **Phase 5A** | **Validate existing workflows** | **Granny flat, permissibility, parking, capacity, precinct (5)** |
| **14** | **Phase 5B** | **Build: Corner lot + Heritage** | **Corner lot setbacks, Heritage + setback (2)** |
| **15** | **Phase 5B** | **Build: Parking + Subdivision** | **Multi-dwelling parking, Boarding house, Subdivision, Deep soil (4)** |
| **16** | **Phase 5B** | **Testing + Integration** | **All 10 workflows tested, UX refined** |
| 17-18 | Phase 6 | Safety layers | Citation validation, hallucination detection |

**Total:** 18 days (was 16, added 2 for workflow builds)

---

## ALTERNATIVE: PARALLEL WORKFLOW BUILDS

If 18 days is too long, build workflows in parallel with other phases:

### Parallel Option 1: Start Workflows in Phase 3

| Day | Primary Phase | Parallel Workflow Build (2h/day) |
|-----|---------------|----------------------------------|
| 5-7 | Phase 3 (Contextual guidance) | Corner lot setbacks (2h × 2 days = 4h total) |
| 8-10 | Phase 4 (Cross-references) | Heritage interaction (2h × 2 days = 3h, buffer 1h) |
| 11-12 | Phase 4 (UX) | Multi-dwelling parking (2h × 1 day = 2h) |
| 13-14 | Phase 5 | Boarding house + Subdivision (3h + 3h = 6h) |
| 15-16 | Phase 5 | Deep soil + Testing (2h + 6h = 8h) |

**Benefit:** Still 16 days total
**Risk:** Divided attention, potential for errors

---

## RECOMMENDED APPROACH

### Option A: Sequential (Safest)
- 18 days total (16 + 2 for workflows)
- Phase 5 fully dedicated to complex workflows
- Lower risk, easier to debug

### Option B: Parallel (Faster)
- 16 days total (as planned)
- 2 hours/day on workflows starting Day 5
- Higher risk, requires strong focus

### Option C: Post-Launch Iteration (Pragmatic)
- 16 days as planned
- Phase 5: Validate 5 existing workflows only
- Build 10 new workflows AFTER launch (Week 3-4)
- Benefit: Launch faster, iterate based on usage data

**Recommendation:** **Option C (Post-Launch Iteration)**

**Rationale:**
1. 5 existing workflows already provide high value
2. Launch faster = faster professional feedback
3. Build new workflows based on actual usage patterns
4. Lower risk (proven workflows first)

---

## PHASE 5 DETAILED SCHEDULE (Option C)

### Phase 5: Days 13-16 (Validate Existing)

#### Day 13: Granny Flat + Permissibility (8 hours)
- **Morning:** Validate granny flat eligibility API
  - Test with 20 addresses (pass/fail cases)
  - Add AI chat routing
  - Format response with progressive disclosure
- **Afternoon:** Validate permissibility check API
  - Test SEPP overrides (boarding house, granny flat, multi-dwelling)
  - Add "reasoning" step-by-step output
  - Test with 15 development types

#### Day 14: Parking + Capacity (8 hours)
- **Morning:** Validate parking calculation with TOD
  - Test TOD reductions (0%, 25%, 50%)
  - Add "show working" calculation steps
  - Test with 10 multi-dwelling scenarios
- **Afternoon:** Validate capacity calculation
  - Test FSR + setback + parking synthesis
  - Add checklist output format
  - Test edge cases (small lots, heritage constraints)

#### Day 15: Precinct + Integration (8 hours)
- **Morning:** Validate precinct requirements
  - Test spatial matching (coordinates → precinct)
  - Add HCA universal provisions
  - Test categorization by topic
- **Afternoon:** Integration testing
  - Test all 5 workflows end-to-end
  - Response format consistency
  - Error handling (missing data, API failures)

#### Day 16: UX Polish + Safety (8 hours)
- **Morning:** UX refinement
  - Progressive disclosure (collapsible sections)
  - Confidence indicators
  - Professional recommendations
  - Suggested follow-up questions
- **Afternoon:** Safety layer integration
  - Citation validation (verify all sources exist)
  - Confidence gating (<80% = warning)
  - Appropriate refusals (professional judgment boundaries)

---

## POST-LAUNCH: Build Additional Workflows (Week 3-4)

### Week 3: Top 5 Priority Workflows (15 hours)
- **Mon-Tue:** Corner lot setbacks (4h) + Heritage interaction (3h)
- **Wed:** Multi-dwelling parking detailed (2h)
- **Thu:** Boarding house compliance (3h)
- **Fri:** Subdivision feasibility (3h)

### Week 4: Next 5 Workflows (12 hours)
- **Mon:** Deep soil calculation (2h)
- **Tue:** Flood + development controls (3h)
- **Wed:** Tree preservation + setbacks (4h)
- **Thu:** Testing + refinement (3h)

**Total:** 27 hours over 2 weeks (3-4 hours/day pace)

---

## SUCCESS CRITERIA (Phase 5 Complete)

**Functional:**
- [ ] All 5 existing workflows validated and tested
- [ ] AI chat routes to correct workflow based on question
- [ ] Response format consistent across workflows
- [ ] <3s response time (90th percentile)
- [ ] Error handling graceful (no crashes)

**Quality:**
- [ ] 100% citation accuracy (every source verifiable)
- [ ] <1% hallucination rate (no invented data)
- [ ] 20-30% appropriate refusal rate (professional judgment)
- [ ] Confidence scores calibrated (high = 95%+ accurate)

**Professional Adoption:**
- [ ] 5 certifiers test and provide feedback
- [ ] 3 planners validate accuracy
- [ ] Trust score >4.5/5 ("I trust this tool")
- [ ] Would recommend >4.0/5

---

**Next:** Choose Option A (18 days), B (16 days parallel), or C (16 days + post-launch) and integrate into master plan.

**Last Updated:** 2026-02-01
**Status:** Integration roadmap complete
**Recommendation:** Option C (post-launch iteration for new workflows)
