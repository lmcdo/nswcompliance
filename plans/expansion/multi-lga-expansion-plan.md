# Multi-LGA Expansion: Research Findings

This document contains research findings only - no proposals or recommendations.

---

## 1. TARGET USERS & THEIR NEEDS

### 1.1 Five User Personas Identified

| Persona | Profile | Primary Need |
|---------|---------|--------------|
| **Private Certifiers** | 50+ DAs/month, time-poor, know DCP intimately | Quick compliance verification in <5 min |
| **Council Planners** | Reviewing DA applications, verifying claims | Confirm applicant citations, find missed requirements |
| **Architects** | Feasibility stage, understanding design envelope | Compare development type options, understand constraints |
| **Developers (Novice)** | First-time, don't know jargon | Plain language, step-by-step guidance |
| **Homeowners** | DIY renovations, basic questions | Simple yes/no answers |

### 1.2 Key User Insights

**Different users need different entry points:**
- Property-centric (current): Enter address → see provisions
- Citation search (missing): Search "Section 4.1.6.2" → verify claim
- Zone/dev type explorer (missing): Browse R2 zones → see all possibilities
- Guided wizard (missing): Step-by-step eligibility checks

**Users context-switch constantly:**
- Start with property view → see provision → want to see full section → check SEPP override → back to property
- Current system doesn't support this workflow well

**DCP structure is paramount for experienced users:**
- Certifiers memorize structure ("parking is in 2.10")
- Council planners cite sections in reports
- Applicants cite sections in DA submissions

**Regulatory hierarchy must be visible:**
- SEPP overrides DCP
- LEP is statutory (must comply), DCP is guideline (may vary)

### 1.3 Current Limitations for Users

- Only serves property-centric workflow
- No citation search
- No zone/dev type explorer without property
- No comparison tool for development options
- No document-centric browse view
- Missing context for verification (no surrounding text preview)

---

## 2. CURRENT FLEXIBILITY & VARIABILITY HANDLING

### 2.1 What's Configurable (Good)

| Aspect | Location | Flexibility |
|--------|----------|-------------|
| Council configs | JSON files | Add new council = new file |
| Topic ordering | Per council, per role | Certifier vs planner ordering |
| Layer labels | Per council | Council-specific terminology |
| Category groupings | Per council | Priority-based UI organization |
| Setback fallback guidance | Per council | Different guidance per council |

### 2.2 What's Hardcoded (Bad)

| Issue | Locations | Impact |
|-------|-----------|--------|
| Council if/else cascades | 20+ locations | Must update multiple files for new council |
| Precinct ID normalization | `precinct-service.ts` | Only handles Marrickville 9_XX format |
| Document ID patterns | SQL queries | `ILIKE '%Marrickville%'` hardcoded |
| Heritage logic | API routes | Ashfield triggers special handling |
| formatPartName() | UI component | Hardcoded Part/Chapter patterns |
| Fallback council | `council-config.ts` | Always returns Marrickville |

### 2.3 How Three Inner West Councils Differ

| Aspect | Marrickville | Leichhardt | Ashfield |
|--------|--------------|------------|----------|
| Provisions | 1,866 | 3,355 | 1,892 |
| Organization | Development type (Parts 4-6) | Topic (Parts C-G) | Heritage-focused (Chapters) |
| Precincts | 48 (format: 9_29) | 43 (format: C2.2.x.x) | 12 (format: Part 1) |
| Heritage | Dedicated Part 8 | Distributed across topics | Intensive Chapter E1 |
| Generic controls | Part 2 | Part C Section 1 | Chapters A-C |

### 2.4 Breaking Points for New Council

What would break if adding a council with different structure:
1. Precinct ID format different from 9_XX → normalizePrecinctId() fails
2. Document ID pattern different → SQL queries return nothing
3. Heritage structure different from Ashfield → condition layer logic wrong
4. Topic markers different from C1-C55 → topic extraction fails
5. Chapter naming different → formatPartName() produces wrong output

---

## 3. EXCEPTION CLAUSE HANDLING

### 3.1 Current State

**Infrastructure exists but is unused:**
- `cross_reference_index` table: 2,111 rows, designed for relationships
- Not populated with DCP exception relationships

**Detection exists but no linking:**
- Type classifier detects "Note:", "Except where", "This does not apply" patterns
- Tags as `v2_provision_type = 'note'`
- Does NOT extract: "This is an exception to Clause 4.1"
- Does NOT link: Exception provision to target provision

### 3.2 Example: What Happens Now

Provision text: "Notwithstanding the minimum setback in Control 2.5, heritage items may apply for variation..."

Current system:
1. ✓ Detects as 'note' type
2. ✓ Tags as actionable/non-actionable
3. ✓ Stores full text
4. ✗ Does NOT extract: "This is an exception to Control 2.5"
5. ✗ Does NOT store: relationship in cross_reference_index
6. ✗ Does NOT link: Exception to base provision

### 3.3 Central Coast Implications

Central Coast has 7+ exception clauses per section (4.1C, 4.1D, 4.1E, etc.):
- Current system would detect them as 'note' type
- Would NOT understand they're exceptions to 4.1
- Would NOT display them grouped with base provision
- Would NOT enable "show base rule + all exceptions" query

### 3.4 Central Coast LEP 2022 vs Inner West LEP 2022 - Detailed Comparison

**Research Date:** 21 Jan 2026

#### Part 4 Minimum Lot Size Exceptions

**Central Coast LEP 2022** has extensive exception clauses:
| Clause | Title |
|--------|-------|
| 4.1 | Minimum subdivision lot size |
| 4.1C | Minimum lot sizes for dual occupancies |
| 4.1D | Exceptions to minimum lot sizes for dual occupancies |
| 4.1E | Exceptions to minimum lot sizes for certain residential development |
| 4.1F | Exceptions to minimum subdivision lot sizes for certain split zones |
| 4.1G | Exception to minimum lot size for subdivision of land that includes deferred matter |
| 4.2 | Exceptions to minimum subdivision lot sizes for environmental purposes |
| 4.2A | Rural subdivision |
| 4.2B | Minimum subdivision lot size for strata plan schemes in certain rural, residential and conservation zones |
| 4.2C | Erection of dual occupancies and dwelling houses on land in certain rural and conservation zones |
| 4.2D | Residential development and subdivision prohibited on certain land |
| 4.3 | Boundary adjustments in certain rural and conservation zones |

**Inner West LEP 2022** has minimal exceptions:
| Clause | Title | Status |
|--------|-------|--------|
| 4.1 | Minimum subdivision lot size | Active |
| 4.1AA | Minimum subdivision lot size for community title schemes | **Not adopted** |
| 4.1A | Exceptions to minimum subdivision lot size for certain residential development | Active (limited) |
| 4.2 | Rural subdivision | **Not applicable** |

**Inner West 4.1A** only applies to:
- "Area 1": Semi-detached dwellings (200m², 7m frontage)
- "Area 2": Dwelling houses (174-450m², max 11 lots total)

#### Land Use Zones Differences

| Zone Type | Central Coast | Inner West |
|-----------|---------------|------------|
| **Rural Zones** | RU1, RU2, RU3, RU5, RU6 | ❌ None |
| **Conservation Zones** | C1, C2, C3, C4 | ❌ None |
| **R4 High Density** | ❌ No | ✅ Yes |
| **R5 Large Lot Residential** | ✅ Yes | ❌ No |
| **SP3 Tourist** | ✅ Yes | ❌ No |
| **SP4 Enterprise** | ✅ Yes | ❌ No |
| **W4 Working Waterfront** | ✅ Yes | ✅ Yes |

#### Geographic Scale
- **Central Coast**: ~1,680 km² - coastal, rural, bushland, waterways
- **Inner West**: ~36 km² - fully urbanised inner-city

#### Part 5 Provisions Applicability

| Provision | Central Coast | Inner West |
|-----------|---------------|------------|
| Secondary dwellings in rural zones (5.5) | ✅ Active | Listed but limited |
| Eco-tourist facilities (5.13) | ✅ Active | Minimal application |
| Intensive livestock agriculture (5.18) | ✅ Active | Not applicable |
| Farm stay accommodation (5.24) | ✅ Active | Not applicable |
| Farm gate premises (5.25) | ✅ Active | Not applicable |
| Aquaculture (5.19) | ✅ Active | Limited |

#### Consolidation History
- **Central Coast**: Merged Wyong LEP 2013 + Gosford LEP 2014
- **Inner West**: Merged Ashfield LEP 2013 + Leichhardt LEP 2013 + Marrickville LEP 2011

#### Architecture Implications

1. **Zone taxonomy must expand**: Current system only handles R1-R4, E1-E4, MU1. Central Coast needs RU1-RU6 and C1-C4.
2. **Exception clause linking critical**: Central Coast's 12+ Part 4 exception clauses require `cross_reference_index` population.
3. **Rural subdivision provisions**: Inner West marks 4.2 as "Not applicable" - Central Coast has active complex provisions.
4. **Part 5 feature flags**: Many Part 5 provisions are council-specific (farm stay, aquaculture, etc.).

---

## 4. ENRICHMENT PIPELINE FOR NEW COUNCILS

### 4.1 Configuration Required

| Config Type | Location | Purpose |
|-------------|----------|---------|
| Python config | `enrichment/config/{council}_config.py` | DCP structure → zone/dev type mappings |
| Frontend JSON | `lib/council-configs/{council}.json` | UI behavior, layer labels, topic order |
| Registry update | `lib/council-config.ts` | Import and add to COUNCIL_CONFIGS |
| Extractor updates | 5 Python files | Council detection, config lookups |

### 4.2 Manual Effort Breakdown

| Task | Effort |
|------|--------|
| Analyze DCP structure | 2-4 hours |
| Create Python config | 1-2 hours |
| Create topic mappings | 1-2 hours |
| Create frontend config | 1 hour |
| Update extractors (5 files) | 2-3 hours |
| Load provisions to DB | 1-2 hours |
| Run enrichment pipeline | 1-2 hours |
| QA & validation | 2-3 hours |
| **Total** | **11-19 hours** |

### 4.3 Key Insight: Document_ID-Driven Inheritance

The system uses **document_id patterns**, not text parsing:
- A provision in "Marrickville DCP 2011 - Part 4.1" automatically applies to R2 zones
- This happens via config lookup, not AI interpretation
- Everything is explicit pattern matching
- New DCP structure requires explicit pattern definitions

### 4.4 What Changes for Different Structures

| Structure Variation | Change Required |
|--------------------|-----------------|
| Different chapter/part naming | Update config keys and patterns |
| Different precinct format | Update precinct list and normalization |
| Unique topic markers | Add to COUNCIL_TOPICS dictionary |
| No precincts | Set `is_precinct_specific: False` |
| Different zone scheme | Add zones to constants |

---

## 5. SEPP/LEP AND REGULATORY HIERARCHY

### 5.1 Hierarchy Implementation

```
Level 3: SEPP (State Environmental Planning Policies) ← OVERRIDES LEP/DCP
Level 5: LEP (Local Environmental Plans)
Level 6: DCP (Development Control Plans)
```

**Override logic exists:**
- SEPP takes precedence when applicable
- Audit trail tracks: "SEPP {name} takes precedence over LEP"
- UI separates state-level (SEPP) from council-level (DCP)

### 5.2 Current SEPP Integration

| SEPP | Status | Tables |
|------|--------|--------|
| Housing 2021 | ✓ Integrated | `housing_sepp_standards` (33 rows), `regulatory_provisions` (241 provisions) |
| Sustainable Buildings 2022 | ✓ Integrated | `sepp_structured_requirements` |
| Resilience & Hazards 2021 | ✓ Integrated | `sepp_structured_requirements` |
| **Coastal Management** | ✗ NOT integrated | No tables, no zone detection |

### 5.3 Coastal SEPP Gap (Central Coast)

**Not currently implemented:**
- No Coastal SEPP in SEPP_MAPPINGS
- No zone detection for coastal areas
- No coastal-specific controls (setback from water, erosion)
- Would need to be added before Central Coast deployment

---

## 6. PROVISION DISPLAY AND FILTERING

### 6.1 Organization Patterns

**Primary: 4-Layer Model**
1. Generic Layer: LGA-wide requirements (78% of data)
2. Use-Specific Layer: Zone-specific controls (1%)
3. Condition Layer: Heritage-related (10%)
4. Precinct Layer: Location-specific (10%)

**Secondary: By Document Structure**
- TOC sidebar with Parts/Sections
- Page grouping preserving PDF context
- Topic filtering within sections

### 6.2 Filtering Cascade

User starts with ~5,566 DCP provisions:
1. After layer filter (generic): 4,351
2. After dev_type (dwelling_house): 307
3. After topic (parking): ~40
4. Result: Focused compliance requirements

### 6.3 Actionable vs Informational

**Actionable** (11,826 provisions):
- Development controls with specific requirements
- Always displayed to users

**Non-Actionable** (filtered out):
- TOC entries, objectives, definitions, references
- 88% of DCP text is filtered as non-actionable

### 6.4 What Users See

| Metadata | Displayed | Purpose |
|----------|-----------|---------|
| Layer badge | ✓ | Shows regulatory level |
| Topic badge | ✓ | Shows requirement category |
| DCP Part | ✓ | Document context |
| PDF page | ✓ | Source reference |
| Marker (C1, O1) | ✓ | Control vs objective |
| Heritage type | ✓ (if applicable) | Heritage categorization |

---

## 7. SUMMARY OF GAPS FOR MULTI-LGA

### 7.1 Architectural Gaps

| Gap | Current State | Impact |
|-----|---------------|--------|
| Hardcoded council detection | 20+ if/else cascades | Each new council needs multiple file updates |
| Precinct normalization | Only Marrickville format | New formats break silently |
| Exception relationships | Detected but not linked | Can't query "base rule + exceptions" |
| Coastal SEPP | Not integrated | Central Coast needs this |

### 7.2 Data Gaps

| Gap | Current State | Impact |
|-----|---------------|--------|
| Rural/Conservation zones | No RU*/C* tagged provisions | Zone filtering won't work |
| Multiple site conditions | Single value column | Can't handle bushfire + flood + coastal |
| Coastal topics | Keywords don't exist | Topic filtering won't find coastal provisions |

### 7.3 Process Gaps

| Gap | Current State | Impact |
|-----|---------------|--------|
| Council adapter pattern | Doesn't exist | No clean extension point |
| Config validation | No schema validation | Invalid configs fail silently |
| Enrichment documentation | Tribal knowledge | Hard to onboard new councils |

---

## 8. BACKWARD COMPATIBILITY ANALYSIS

### 8.1 What's Already Additive (Safe to Extend)

| Component | Location | How It Works |
|-----------|----------|--------------|
| External config loader | `council-configs/loader.ts:36-133` | Reads `lga-data/{council}/config.json` without code changes |
| LGA mappings data | `config/lga-mappings.json` | JSON entries for postcodes, suburbs, former councils |
| Database layer | All services | Uses `lga`, `former_council` columns - no hardcoding |
| Precinct pattern registration | `precinct-service.ts:383-385` | `registerPrecinctPatterns()` function exists (unused) |

### 8.2 What Requires Code Modification (Risk Points)

| Component | Location | What Breaks | Impact |
|-----------|----------|-------------|--------|
| Config imports | `council-config.ts:10-14` | New council needs import line | Low - additive change |
| Config registry | `council-config.ts:90-94` | New council needs entry in COUNCIL_CONFIGS | Low - additive change |
| LGA_CONFIGS dict | `lga-configs/index.ts:51-58` | New council needs entry | Low - additive change |
| Precinct patterns | `precinct-service.ts:315-354` | New patterns needed in PRECINCT_ID_PATTERNS | Medium - shared data structure |
| Enrichment mappings | `DQ7_devtype_enrichment.py:22-58` | New section→devtype mappings | Medium - shared data structure |

### 8.3 Graceful Fallbacks (Safety Net)

The system already handles unknown councils safely:

| Scenario | Current Behavior | Risk |
|----------|-----------------|------|
| Unknown council ID | Falls back to Marrickville config | UI works, wrong labels possible |
| Unknown zone | Returns generic 5-item dev type list | User sees options, may be incomplete |
| Unknown document_id | Returns 'generic' layer + ['ALL'] zones | Provisions shown, filtering less precise |
| Unknown precinct pattern | Returns 'Marrickville' as default | Wrong council attribution |

### 8.4 Existing Test Coverage for Inner West

**18 test files found** covering:
- ✓ Zone-specific provision retrieval (R2, E1, B1)
- ✓ Development type filtering per council
- ✓ Precinct provision filtering
- ✓ Former council mapping (Ashfield/Marrickville/Leichhardt)
- ✓ API endpoint integration
- ✓ Numeric value extraction

**Missing (regression risk):**
- ✗ Baseline provision counts per council/zone/devtype
- ✗ Cross-council consistency tests
- ✗ Precinct boundary mapping validation
- ✗ SEPP override verification

---

## 9. SAFE EXTENSION STRATEGY

### 9.1 Principle: Test-First, Additive Changes

1. **Create baseline tests BEFORE adding Central Coast**
2. **Use additive patterns where they exist**
3. **Make minimal additions to hardcoded registries**
4. **Run full test suite after each change**

### 9.2 Safe Extension Sequence

```
Phase 1: Freeze Inner West Baseline
├── Create provision count baseline tests
├── Create API response snapshot tests
├── Run existing 18 test files, ensure all pass
└── Commit baseline tests

Phase 2: Add Central Coast Config (Additive)
├── Create lga-data/central-coast/config.json (uses existing loader)
├── Add entry to lga-mappings.json (additive JSON)
├── Run tests - Inner West should still pass
└── Commit

Phase 3: Register Central Coast in Hardcoded Lists (Minimal)
├── Add import + entry to council-config.ts (2 lines)
├── Add entry to LGA_CONFIGS (1 line)
├── Add patterns to PRECINCT_ID_PATTERNS (1 entry)
├── Run tests - Inner West should still pass
└── Commit

Phase 4: Enrichment Pipeline (Isolated)
├── Create enrichment/config/central_coast_config.py (new file)
├── Add Central Coast mappings to SECTION_DEVTYPE_MAPPING (additive dict entries)
├── Run enrichment on Central Coast PDFs only
├── Verify Inner West provision counts unchanged
└── Commit

Phase 5: Validation
├── Run full test suite
├── Manual smoke test Inner West addresses
├── Manual smoke test Central Coast addresses
└── Deploy to staging
```

### 9.3 Rollback Strategy

Each phase is independently revertible:
- Phase 2-3: Delete config files, revert registry additions
- Phase 4: Drop Central Coast provisions from database
- Database: `DELETE FROM regulatory_provisions WHERE lga = 'Central Coast'`

### 9.4 What NOT to Do

| Anti-Pattern | Why Risky |
|--------------|-----------|
| Refactor to adapter pattern during addition | Changes core architecture while adding data |
| Modify existing Inner West configs | Could break tested behavior |
| Share data structures between councils | Central Coast bugs could affect Inner West |
| Skip baseline tests | No way to detect silent regressions |

---

## 10. STRATEGIC ANALYSIS: SCALING TO 130+ LGAs

### 10.1 The Scalability Problem

Current state: Adding 1 new LGA requires modifying 5+ files
- `council-config.ts` (imports + registry)
- `lga-configs/index.ts` (LGA_CONFIGS dict)
- `precinct-service.ts` (PRECINCT_ID_PATTERNS)
- `enrichment/config/{council}_config.py` (new file)
- `DQ7_devtype_enrichment.py` (SECTION_DEVTYPE_MAPPING)

**At this rate for 130 NSW LGAs:**
- 650+ file modifications
- Each modification risks regression
- Tribal knowledge required for each addition
- No schema validation = silent failures

### 10.2 Three Strategic Approaches

**Approach A: Quick Addition (Tactical)**
```
Effort: ~2-3 days per LGA
Risk: Low for 2nd LGA, increases with each addition
Pattern: Add entries to existing hardcoded structures
```
- Pros: Fast to Central Coast, minimal disruption
- Cons: Tech debt compounds, 10th LGA will be painful

**Approach B: Refactor First (Foundational)**
```
Effort: ~2 weeks upfront, then ~1 day per LGA
Risk: Medium (touching core code), but controlled via tests
Pattern: Council adapter interface + config-driven loading
```
- Pros: Sustainable for 130+ LGAs, clean architecture
- Cons: Delays Central Coast, requires careful Inner West migration

**Approach C: Hybrid - Refactor While Adding (Pragmatic)**
```
Effort: ~1 week upfront, ~2 days per LGA initially, decreasing
Risk: Medium, mitigated by parallel development
Pattern: Build adapter for Central Coast, retrofit Inner West
```
- Pros: Ships Central Coast, establishes good pattern, Inner West migrated safely
- Cons: More complex initially, two patterns coexist temporarily

### 10.3 Recommended: Approach C (Hybrid)

**Rationale:**
1. Central Coast is different enough to expose architecture weaknesses
2. Building adapter for Central Coast validates the pattern
3. Inner West can migrate after Central Coast proves the pattern
4. Each subsequent LGA becomes easier

**Implementation Sequence:**
```
Week 1: Foundation
├── Define CouncilAdapter interface
├── Create Central Coast adapter (new pattern)
├── Central Coast config.json in lga-data/
└── Tests for adapter contract

Week 2: Central Coast Integration
├── Load Central Coast via adapter
├── Enrichment pipeline for Central Coast
├── Validate filtering works
└── Inner West still uses old pattern (unchanged)

Week 3: Inner West Migration
├── Create Inner West adapter (wraps existing)
├── Gradual migration of hardcoded logic
├── Run existing 18 tests continuously
└── Both patterns work in parallel

Week 4+: Cleanup
├── Remove hardcoded if/else cascades
├── Single config format for all councils
├── Documentation for adding new LGAs
└── Schema validation for configs
```

### 10.4 Council Adapter Pattern (Conceptual)

```typescript
interface CouncilAdapter {
  id: string;
  name: string;

  // Config
  getLayerLabels(): LayerLabels;
  getCategoryGroups(): CategoryGroups;
  getPrecinctPatterns(): RegExp[];

  // Enrichment
  getSectionDevTypeMapping(): Record<string, string[]>;
  getTopicKeywords(): Record<string, RegExp>;

  // Feature flags
  hasCoastalProvisions(): boolean;
  hasExceptionLinking(): boolean;
  hasPrecintSpecificControls(): boolean;
}

// Registry (config-driven, no if/else)
const adapters = new Map<string, CouncilAdapter>();
adapters.set('inner-west', new InnerWestAdapter());
adapters.set('central-coast', new CentralCoastAdapter());
```

### 10.5 Pros vs Cons Summary

| Factor | Quick Add | Refactor First | Hybrid |
|--------|-----------|----------------|--------|
| Time to Central Coast | 1 week | 4 weeks | 2 weeks |
| Risk to Inner West | Low | Medium | Low-Medium |
| Time to 10th LGA | 3 weeks each | 1 week each | 1 week each |
| Tech debt | Grows | Minimal | Controlled |
| Maintainability | Decreases | Good | Good |
| Documentation need | High | Low | Medium |

### 10.6 Decision Factors

Choose **Quick Add** if:
- Only need 1-2 more LGAs ever
- Tight deadline for Central Coast
- Team capacity is limited

Choose **Refactor First** if:
- Clear roadmap for 10+ LGAs
- Can delay Central Coast 3-4 weeks
- Technical excellence is priority

Choose **Hybrid** if:
- Need Central Coast soon AND more LGAs later
- Can invest 1 extra week upfront
- Want sustainable growth without blocking current delivery

---

## 11. RECOMMENDED APPROACH: HYBRID

**Based on:**
- 5-10 LGAs planned in next 12 months
- Flexible timeline (2+ months for Central Coast)
- Compliance priority, serving certifiers + developers

### 11.1 Why Hybrid is Optimal

| Factor | Quick Add | Hybrid | Refactor First |
|--------|-----------|--------|----------------|
| Fits 5-10 LGA goal | ❌ Painful at scale | ✅ Sustainable | ✅ Overkill |
| Fits 2+ month timeline | ✅ | ✅ | ✅ |
| Ships Central Coast | Week 1 | Week 2-3 | Week 4+ |
| Inner West risk | Low | Low-Medium | Medium |
| Future LGA effort | 3 days each | 1-2 days each | 1 day each |

### 11.2 Implementation Phases

**Phase 1: Foundation (Week 1)**
- Define `CouncilAdapter` TypeScript interface
- Create baseline tests for Inner West (freeze current behavior)
- Set up `lga-data/central-coast/config.json` structure

**Phase 2: Central Coast Adapter (Week 2)**
- Implement `CentralCoastAdapter` using new pattern
- Create `enrichment/config/central_coast_config.py`
- Load Central Coast provisions to database
- Test filtering works independently

**Phase 3: Integration (Week 3)**
- Wire Central Coast adapter into existing UI
- Add precinct patterns via `registerPrecinctPatterns()` (uses existing function)
- Verify Central Coast works end-to-end
- Inner West unchanged, still uses old pattern

**Phase 4: Inner West Migration (Week 4)**
- Create `InnerWestAdapter` wrapping existing configs
- Gradually move hardcoded logic into adapter
- Run 18 existing tests after each change
- Both adapters coexist in registry

**Phase 5: Cleanup (Week 5-6)**
- Remove hardcoded if/else cascades
- Consolidate to single config format
- Add JSON Schema validation
- Document "How to Add an LGA" process

### 11.3 Key Artifacts to Create

```
compliance-engine/
├── frontend-nextjs/
│   ├── lib/
│   │   ├── adapters/
│   │   │   ├── types.ts              # CouncilAdapter interface
│   │   │   ├── registry.ts           # Adapter registry (replaces if/else)
│   │   │   ├── inner-west.ts         # InnerWestAdapter
│   │   │   └── central-coast.ts      # CentralCoastAdapter
│   │   └── council-configs/
│   │       └── schema.json           # JSON Schema for validation
│   └── tests/
│       └── baseline/
│           ├── inner-west-counts.test.ts    # Provision count baselines
│           └── inner-west-api.test.ts       # API response snapshots

lga-data/
├── central-coast/
│   ├── config.json                   # Council config
│   ├── docs/                         # DCP PDFs
│   └── boundaries/                   # GeoJSON files
└── _template/
    └── config.schema.json            # Validation schema

enrichment/
└── config/
    └── central_coast_config.py       # DCP structure mappings
```

### 11.4 Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Break Inner West during adapter migration | Baseline tests run after every change |
| Central Coast config incorrect | Schema validation catches errors before runtime |
| Enrichment produces wrong data | Separate database table for Central Coast initially |
| Performance degradation | Adapter lookup is O(1) via Map, same as current if/else |

### 11.5 Success Criteria

- [ ] Inner West: All 18 existing tests pass
- [ ] Inner West: Provision counts unchanged (baseline test)
- [ ] Central Coast: Provisions load and filter correctly
- [ ] Central Coast: Precinct detection works
- [ ] Architecture: Adding 3rd LGA requires <1 day effort
- [ ] Documentation: "Add an LGA" guide exists

---

## 12. TOP GROWTH LGAs ANALYSIS (5-10 LGA ROADMAP)

### 12.1 NSW Housing Targets & Development Demand

Based on research from [NSW Planning Portal](https://www.planning.nsw.gov.au/policy-and-legislation/housing/housing-targets) and [Council League Table](https://www.planning.nsw.gov.au/policy-and-legislation/housing/faster-assessments-program/council-league-table):

| LGA | 5-Year Housing Target | Growth Drivers | TOD Precincts |
|-----|----------------------|----------------|---------------|
| **City of Sydney** | 18,900 homes | Inner city density | Central, Redfern |
| **Parramatta** | ~15,000 (est.) | CBD status, TOD | Parramatta, Westmead |
| **Blacktown** | ~12,000 (est.) | Western Sydney corridor | Mount Druitt |
| **Canterbury-Bankstown** | ~10,000 (est.) | TOD accelerated | Bankstown, Belmore, Lakemba |
| **Penrith** | 8,400 homes | Airport precinct | Penrith, St Marys |
| **Cumberland** | ~8,000 (est.) | Auburn growth | Merrylands |
| **Northern Beaches** | ~6,000 (est.) | Mid-rise reforms | Dee Why, Frenchs Forest |

### 12.2 DCP Structural Complexity by LGA

| LGA | Organization | Former Councils | Current State | Complexity |
|-----|--------------|-----------------|---------------|------------|
| **Parramatta** | Theme-based Parts 3-10+ | 5 (Parramatta, Auburn, Hills, Holroyd, Hornsby) | Harmonized 2023 | HIGH |
| **Canterbury-Bankstown** | Chapters 6-10 by precinct | 2 (Canterbury, Bankstown) | Harmonized 2023 | HIGH |
| **Cumberland** | Parts A-G + precinct F1/F2 | 3+ (Auburn, Holroyd, Parramatta parts) | Harmonized 2021 | MEDIUM |
| **Blacktown** | Zone-based Parts A-Q | 1 (never merged) | Single DCP | MEDIUM |
| **Penrith** | 2 volumes, Parts A-F + precincts | 1 (never merged) | Single DCP | MEDIUM |
| **Northern Beaches** | 3 SEPARATE DCPs | 3 (Manly, Warringah, Pittwater) | NOT harmonized | HIGHEST |
| **Central Coast** | Chapters 1-6, 55 precincts | 2 (Gosford, Wyong) | Harmonized 2022 | HIGH |

### 12.3 Pattern Recognition

**Pattern A: Single-Council LGAs** (Blacktown, Penrith)
- Simplest to onboard
- No former council detection needed
- Single DCP structure
- Effort: ~1 day with adapter pattern

**Pattern B: Merged & Harmonized** (Parramatta, Canterbury-Bankstown, Cumberland)
- Similar to Inner West
- Former council detection sometimes needed for legacy references
- Single harmonized DCP
- Effort: ~2 days with adapter pattern

**Pattern C: Merged but NOT Harmonized** (Northern Beaches)
- Most complex - like Inner West but worse
- 3 completely separate DCPs
- Must maintain 3 separate configs
- Effort: ~3-4 days (essentially 3 LGAs)

**Pattern D: Regional/Coastal** (Central Coast)
- Large geographic area
- Coastal SEPP applies
- Many precincts (55+)
- Rural zones (RU1-RU6)
- Effort: ~3 days with adapter + SEPP work

### 12.4 Optimal Onboarding Sequence

Based on complexity vs value:

```
RECOMMENDED SEQUENCE (5-10 LGAs over 12 months):

Phase 1: Prove the Pattern (Months 1-2)
├── Central Coast (already researched, tests adapter architecture)
└── Penrith (single-council, high demand, proves simplicity)

Phase 2: Scale Merged Councils (Months 3-5)
├── Canterbury-Bankstown (TOD precincts, similar to Inner West)
├── Cumberland (familiar pattern, Auburn/Merrylands demand)
└── Parramatta (high value, complex but harmonized)

Phase 3: Expand Western Sydney (Months 6-8)
├── Blacktown (high volume, simpler structure)
└── Liverpool (not researched, likely Pattern A/B)

Phase 4: Complex Cases (Months 9-12)
├── Northern Beaches (Pattern C - 3 DCPs)
└── City of Sydney (unique density controls)
```

### 12.5 Architecture Implications

**What the Adapter Must Handle:**

| Scenario | LGAs Affected | Adapter Requirement |
|----------|---------------|---------------------|
| Former council detection | Inner West, Parramatta, Cumberland | `getFormerCouncil(address)` method |
| Multi-DCP within LGA | Northern Beaches, Inner West | Array of DCP configs per adapter |
| TOD precinct overlays | Canterbury-Bankstown, Parramatta | State-level provision override |
| Rural zones (RU*) | Central Coast, Penrith | Extended zone taxonomy |
| Coastal provisions | Central Coast, Northern Beaches | Coastal SEPP integration |
| 50+ precincts | Central Coast, Parramatta | Scalable precinct registry |

**What the Adapter Interface Should Include:**

```typescript
interface CouncilAdapter {
  // Identity
  id: string;                          // 'central-coast', 'parramatta'
  name: string;                        // 'Central Coast Council'
  pattern: 'single' | 'merged-harmonized' | 'merged-separate';

  // Structure (varies by pattern)
  dcpConfigs: DCPConfig[];             // 1 for single, 3 for Northern Beaches
  formerCouncils?: FormerCouncil[];    // Only for merged LGAs

  // Zones
  residentialZones: string[];          // ['R1', 'R2', 'R3', 'R4', 'R5']
  ruralZones?: string[];               // ['RU1', 'RU2', 'RU3', 'RU4', 'RU5', 'RU6']
  conservationZones?: string[];        // ['C1', 'C2', 'C3', 'C4']

  // Capabilities (feature flags)
  hasCoastalProvisions: boolean;
  hasTODPrecincts: boolean;
  hasRuralZones: boolean;
  hasMultipleDCPs: boolean;

  // Methods
  detectFormerCouncil(address: string): string | null;
  getPrecinctPatterns(): RegExp[];
  getSectionDevTypeMapping(): Record<string, string[]>;
}
```

### 12.6 Effort Estimates with Adapter Pattern

| LGA | Without Adapter | With Adapter | Savings |
|-----|-----------------|--------------|---------|
| Central Coast | 3 days | 3 days | 0 (first, builds pattern) |
| Penrith | 3 days | 1 day | 2 days |
| Canterbury-Bankstown | 4 days | 2 days | 2 days |
| Cumberland | 4 days | 2 days | 2 days |
| Parramatta | 5 days | 2 days | 3 days |
| Blacktown | 3 days | 1 day | 2 days |
| Northern Beaches | 9 days | 4 days | 5 days |
| **Total (7 LGAs)** | **31 days** | **15 days** | **16 days saved** |

### 12.7 Key Variables Affecting Architecture

| Variable | Low Complexity | High Complexity |
|----------|---------------|-----------------|
| Former councils | 0-1 | 3-5 |
| DCP count per LGA | 1 | 3 |
| Precinct count | 10-20 | 50+ |
| Zone types | R1-R4 only | R1-R5 + RU1-RU6 + C1-C4 |
| SEPP overlays | None | Coastal + TOD |
| Exception clauses | Simple | 7+ per section |

**Central Coast tests ALL the hard variables** - making it ideal as the first adapter implementation.

---

## 13. CODE SAFETY & SESSION MANAGEMENT

### 13.1 Your Existing Safety Infrastructure (Already Good)

| Tool | Purpose | How to Leverage |
|------|---------|-----------------|
| `pre-edit-guard.py` | Blocks edits to .env, lock files | Keep as-is |
| `DATA_QUALITY_TRACKER.md` | Issue tracking with session logs | Add LGA-EXPANSION section |
| `SYSTEMATIC_VERIFICATION.md` | N instances = N checks | Apply to adapter changes |
| `claude-mem` MCP | Cross-session memory | Record each LGA's completion state |
| `beads` MCP | Issue tracking | Create LGA expansion epic |
| Feature branches | Git hygiene | One branch per LGA |

### 13.2 Branch Strategy for Multi-LGA Expansion

```
main (protected - Inner West production)
│
├── feature/council-adapter-pattern (Week 1-2)
│   └── PR when adapter interface + Inner West baseline tests pass
│
├── feature/lga-central-coast (Week 2-4)
│   └── PR when Central Coast works, Inner West tests still pass
│
├── feature/lga-penrith (Month 2)
│   └── PR when Penrith works, previous LGAs tests pass
│
└── (etc. for each LGA)
```

**Rules:**
1. Never commit directly to main
2. Run Inner West tests before EVERY PR
3. Each LGA branch starts from latest main
4. Merge only when ALL existing LGA tests pass

### 13.3 Session Boundaries (Prevent Context Loss)

**One Session = One LGA or One Adapter Phase**

| Session Type | Scope | Deliverable |
|-------------|-------|-------------|
| Adapter Foundation | Interface + baseline tests | PR to main |
| LGA Onboarding | Single LGA config + enrichment | PR to main |
| Bug Fix | Single issue across all LGAs | PR to main |

**Never in same session:**
- Multiple LGAs
- Adapter refactor + new LGA
- Core changes + data changes

### 13.4 Claude-Mem Usage for LGA Expansion

Record these at session end:

```bash
# After completing Central Coast adapter
claude-mem record --type "milestone" --project "compliance-engine" \
  "Central Coast adapter complete. Config: lga-data/central-coast/config.json.
   Tests: tests/lga/central-coast/. Inner West tests: ALL PASS."

# After each LGA
claude-mem record --type "lga-complete" --project "compliance-engine" \
  "Penrith onboarded. Pattern: single-council.
   Effort: 1.5 days. Tests: 12 passing. Inner West: unchanged."
```

### 13.5 Beads Issue Structure for LGA Expansion

```bash
# Create epic
beads create --type epic --title "Multi-LGA Expansion (5 LGAs)" \
  --description "Adapter pattern + 5 LGAs in 12 months"

# Create sub-issues
beads create --parent LGA-EPIC --title "Council Adapter Interface" --priority 1
beads create --parent LGA-EPIC --title "Inner West Baseline Tests" --priority 1
beads create --parent LGA-EPIC --title "Central Coast Adapter" --priority 2
beads create --parent LGA-EPIC --title "Penrith Adapter" --priority 3
# etc.

# Track progress
beads update LGA-CENTRAL-COAST --status in_progress
beads close LGA-CENTRAL-COAST --reason "Complete: 2,847 provisions, 55 precincts"
```

### 13.6 Pre-Edit Guard Enhancement (Add to hook)

Add LGA-specific protection to `pre-edit-guard.py`:

```python
# CRITICAL: Inner West configs - require confirmation for any edit
INNER_WEST_PROTECTED = [
    'council-configs/marrickville.json',
    'council-configs/leichhardt.json',
    'council-configs/ashfield.json',
    'enrichment/config/marrickville_config.py',
    'enrichment/config/leichhardt_config.py',
    'enrichment/config/ashfield_config.py',
]

# If editing Inner West config, warn loudly
for pattern in INNER_WEST_PROTECTED:
    if pattern in file_path_lower:
        print(f"⚠️ WARNING: Editing Inner West production config: {file_path}", file=sys.stderr)
        print("Run Inner West tests before committing!", file=sys.stderr)
        # Don't block, just warn
```

### 13.7 LGA Expansion Tracker (Add to DATA_QUALITY_TRACKER.md)

```markdown
## LGA Expansion Status

| LGA | Status | Branch | Tests | Provisions | Notes |
|-----|--------|--------|-------|------------|-------|
| Inner West | ✅ PRODUCTION | main | 18 passing | 5,566 | Protected baseline |
| Central Coast | 🔄 IN PROGRESS | feature/lga-central-coast | - | - | Week 1-2 |
| Penrith | 📋 PLANNED | - | - | - | After Central Coast |
| Canterbury-Bankstown | 📋 PLANNED | - | - | - | Month 4-5 |
| Cumberland | 📋 PLANNED | - | - | - | Month 5-6 |
| Parramatta | 📋 PLANNED | - | - | - | Month 7-8 |

### Session Checklist (Copy Before Each Session)

```
[ ] Read DATA_QUALITY_TRACKER.md LGA section
[ ] Check which LGA is current focus
[ ] Verify on correct branch: git branch
[ ] Run Inner West baseline: npm test -- inner-west
[ ] ONE LGA per session only
[ ] At end: Update tracker, commit, record to claude-mem
```
```

### 13.8 File Isolation Rules

**NEVER mix in same file:**

| Pattern | Why |
|---------|-----|
| Inner West config + new LGA config | Risk of accidental Inner West change |
| Adapter interface + adapter implementation | Changing interface breaks all implementations |
| Database schema + data load | Schema change requires migration |

**Always separate files:**
- `adapters/types.ts` - Interface only
- `adapters/inner-west.ts` - Inner West adapter
- `adapters/central-coast.ts` - Central Coast adapter
- Each LGA gets its own adapter file

### 13.9 Test Gates (Automated Protection)

Add to CI/CD (or run manually before PR):

```bash
# Must pass before any PR to main
npm run test:inner-west     # Existing 18 tests
npm run test:adapter        # New adapter contract tests
npm run test:lga:all        # All LGA-specific tests

# Quick check during development
npm run test:baseline       # Just provision counts
```

### 13.10 Recovery Procedures

**If Inner West breaks:**
```bash
# Immediate rollback
git checkout main -- frontend-nextjs/lib/council-configs/
git checkout main -- enrichment/config/

# Verify
npm run test:inner-west

# Identify what changed
git diff HEAD~5 -- '*inner*' '*marrickville*' '*leichhardt*' '*ashfield*'
```

**If LGA data corrupted:**
```sql
-- Isolate: Central Coast provisions are separate
DELETE FROM regulatory_provisions WHERE lga = 'Central Coast';
-- Inner West unaffected
```

**If adapter pattern breaks all LGAs:**
```bash
# Revert to pre-adapter
git checkout v1.0-pre-adapter -- frontend-nextjs/lib/

# Or use feature flags
# In council-config.ts:
const USE_ADAPTER = false; // Disable new pattern
```

---

## 14. DEFERRED ITEMS

To keep scope manageable, defer these to later phases:

1. **Coastal SEPP** - Add after Central Coast DCP core works (before production launch)
2. **Exception linking** - Populate `cross_reference_index` after base provisions work
3. **Citation search** - New feature, not required for LGA expansion
4. **Zone/dev type explorer** - New feature, not required for LGA expansion
5. **TOD precinct handling** - Add when Canterbury-Bankstown onboarded

---

## 15. SUMMARY: RECOMMENDED APPROACH

### 15.1 Architecture Decision
**Hybrid Approach** with Council Adapter Pattern

### 15.2 First 5 LGAs (12-month roadmap)
1. **Central Coast** (Month 1-2) - Tests full adapter complexity
2. **Penrith** (Month 2-3) - Validates single-council simplicity
3. **Canterbury-Bankstown** (Month 4-5) - Proves merged-council pattern
4. **Cumberland** (Month 5-6) - Scales merged-council pattern
5. **Parramatta** (Month 7-8) - High-value complex case

### 15.3 Key Artifacts to Build
1. `CouncilAdapter` interface (TypeScript)
2. Baseline tests for Inner West
3. Central Coast adapter (first implementation)
4. JSON Schema for config validation
5. "Add an LGA" documentation

### 15.4 Success Metrics
- Inner West: All existing tests pass
- Each new LGA: <2 days to onboard after adapter exists
- Architecture: No if/else cascades for council detection
- Data quality: >80% provision classification accuracy

### 15.5 Risk Mitigation
- Test-first approach protects Inner West
- Phased rollout catches issues early
- Central Coast tests hardest variables first
- Each phase is independently revertible

### 15.6 Code Safety Summary
- **Branch per LGA**: Never mix LGAs in same branch
- **Session per LGA**: One session = one LGA or one adapter phase
- **Inner West protected**: Hook warns on config edits
- **claude-mem**: Record completion state after each session
- **beads**: Track LGA epic with sub-issues
- **Rollback ready**: Each change is revertible

---

## 16. NEXT STEPS

1. **Approve this plan** - Confirm Hybrid approach with 5-LGA roadmap
2. **Phase 1 Implementation:**
   - Define `CouncilAdapter` TypeScript interface
   - Create baseline tests for Inner West provision counts
   - Enhance `pre-edit-guard.py` for Inner West protection
   - Set up beads epic for LGA expansion tracking
   - Set up `lga-data/central-coast/config.json` structure
3. **Begin Central Coast** - First adapter implementation
