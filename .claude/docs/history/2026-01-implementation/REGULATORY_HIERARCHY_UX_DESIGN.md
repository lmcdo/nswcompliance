# Regulatory Hierarchy UI/UX Design
**SEPP → LEP → DCP Display Strategy**

**Issue:** Currently showing DCP setbacks without SEPP/LEP context
**Risk:** User doesn't know which actually applies
**Solution:** Hierarchical display with visual priority

---

## The Regulatory Reality

### 1. SEPP (State Environmental Planning Policy)
**Purpose:** State-wide standards, complying development pathways
**Setback role:**
- Codes SEPP: Complying development setbacks (IF you qualify)
- Housing SEPP: Secondary dwelling/boarding house standards
- **OVERRIDES** DCP if applicable

**Example:**
> "Complying Development: 4.5m front setback (if lot >400m²)"
> vs
> "DCP: 6m front setback"
>
> If you qualify for complying → use 4.5m, not 6m!

### 2. LEP (Local Environmental Plan)
**Purpose:** Zoning, FSR, height limits
**Setback role:**
- Rarely has setbacks directly
- Controls FSR/height which AFFECT setbacks
- Sets permissibility (can you even build this?)

**Example:**
> "LEP: Height 9m, FSR 0.6:1"
> "LEP: Dwelling house permitted with consent"

### 3. DCP (Development Control Plan)
**Purpose:** Detailed design guidelines
**Setback role:**
- Primary source of specific setback numbers
- Context-based provisions ("match street character")
- Council can vary these

**Example:**
> "DCP: Front 6m, Side 900mm, Rear 4m"
> "DCP: Or match adjoining setbacks"

---

## Current UI Problem

```
┌─ Setback Constraints ─────────────────────┐
│ Front: 6 metres                            │
│ Source: Marrickville DCP 4.2               │
│                                            │
│ Side: 4 metres                             │
│ Source: Marrickville DCP 4.2               │
└────────────────────────────────────────────┘
```

**What's wrong:**
- ❌ No indication SEPP might override
- ❌ No LEP context (permissibility)
- ❌ Looks authoritative but may be wrong
- ❌ User doesn't know DA vs CDC pathway

---

## Proposed UI/UX Solutions

### Option 1: Hierarchical Cards with Priority Badges

```
┌─ SEPP Controls (Highest Priority) ──────────────┐
│ 🏛️ STATE PLANNING POLICY                        │
│                                                  │
│ IF Complying Development (Codes SEPP):          │
│   Front: 4.5m (if lot >900m²)                   │
│   Side: 900mm (if single storey)                │
│   Rear: 6m                                      │
│                                                  │
│ ℹ️ Faster approval, must meet ALL criteria      │
│ 📄 Source: Codes SEPP 2008, Schedule 1         │
└──────────────────────────────────────────────────┘

┌─ LEP Controls (Statutory) ───────────────────────┐
│ 📋 LOCAL ENVIRONMENTAL PLAN                      │
│                                                  │
│ Zone: R2 Low Density Residential                │
│ Permissibility: Permitted with consent          │
│ Height limit: 9 metres                          │
│ FSR: 0.6:1                                      │
│                                                  │
│ 📄 Source: Inner West LEP 2022, Clause 4.3      │
└──────────────────────────────────────────────────┘

┌─ DCP Guidelines (Council Standards) ─────────────┐
│ 🏘️ DEVELOPMENT CONTROL PLAN                     │
│                                                  │
│ Multi-Dwelling Housing Setbacks:                │
│   Front: 6 metres                               │
│   Side: 4m (no driveway) / 7m (driveway)       │
│   Rear: 4m (no driveway) / 7m (driveway)       │
│                                                  │
│ ℹ️ Guidelines - Council may vary                │
│ 📄 Source: Marrickville DCP 4.2.4.3            │
└──────────────────────────────────────────────────┘
```

**Pros:**
- ✅ Clear hierarchy (top = highest priority)
- ✅ User sees ALL options
- ✅ Visual distinction (icons, colors)
- ✅ Explains what each level means

**Cons:**
- ❌ Takes up lots of space
- ❌ Might overwhelm casual users

---

### Option 2: Tabbed Interface (Pathway Selection)

```
┌─ Choose Your Pathway ────────────────────────────┐
│                                                  │
│  [Complying Development] [Development Application]│
│   └─ SEPP pathway          └─ LEP/DCP pathway    │
│      Faster approval          More flexibility   │
│                                                  │
└──────────────────────────────────────────────────┘

┌─ Complying Development (Codes SEPP) ─────────────┐
│ ⚡ FAST TRACK (10 days)                          │
│                                                  │
│ Setbacks (ALL must be met):                     │
│   Front: 4.5m                                   │
│   Side: 900mm (single storey)                   │
│   Rear: 6m                                      │
│                                                  │
│ Other requirements:                             │
│   • Lot size ≥ 900m²                            │
│   • Not in heritage area                        │
│   • Max building height 9m                      │
│                                                  │
│ 🔴 CRITICAL: If ANY criterion not met, must use DA│
│ 📄 Source: Codes SEPP 2008, Schedule 1          │
└──────────────────────────────────────────────────┘

[vs when DA tab selected:]

┌─ Development Application (LEP + DCP) ────────────┐
│ 📋 STANDARD PATHWAY (60-90 days)                 │
│                                                  │
│ LEP Requirements:                                │
│   Zone: R2 - Permitted with consent             │
│   Height: 9m max                                │
│   FSR: 0.6:1                                    │
│                                                  │
│ DCP Guidelines (may be varied):                 │
│   Front: 6m                                     │
│   Side: 4m / 7m (with driveway)                │
│   Rear: 4m / 7m (with driveway)                │
│                                                  │
│ ℹ️ Council has discretion to vary DCP standards │
│ 📄 Source: Inner West LEP 2022 + Marrickville DCP│
└──────────────────────────────────────────────────┘
```

**Pros:**
- ✅ User chooses pathway first
- ✅ Only shows relevant info
- ✅ Clearer what applies to them
- ✅ Less overwhelming

**Cons:**
- ❌ User might pick wrong pathway
- ❌ Hides alternative options

---

### Option 3: Inline Hierarchy with Badges (Compact)

```
┌─ Setback Requirements ───────────────────────────┐
│                                                  │
│ FRONT SETBACK                                    │
│ ├─ 🏛️ SEPP: 4.5m (if complying)                 │
│ └─ 🏘️ DCP:  6m (if DA)                          │
│                                                  │
│ SIDE SETBACK                                     │
│ ├─ 🏛️ SEPP: 900mm (if complying)                │
│ └─ 🏘️ DCP:  4m (if DA)                          │
│                                                  │
│ REAR SETBACK                                     │
│ ├─ 🏛️ SEPP: 6m (if complying)                   │
│ └─ 🏘️ DCP:  4m (if DA)                          │
│                                                  │
│ ℹ️ SEPP pathway faster but stricter              │
│ 📋 LEP: Dwelling permitted, Height 9m, FSR 0.6:1│
└──────────────────────────────────────────────────┘
```

**Pros:**
- ✅ Compact - shows both options
- ✅ Easy to compare
- ✅ Visual hierarchy (tree structure)
- ✅ User sees tradeoff

**Cons:**
- ❌ Still shows both even if one doesn't apply
- ❌ Requires explanation

---

### Option 4: Priority Banner System (Recommended for MVP)

```
┌─ Your Planning Pathway ──────────────────────────┐
│ 📋 Development Application (LEP/DCP)             │
│ └─ Reason: SEPP complying not available          │
│    (lot size <400m² required minimum)            │
└──────────────────────────────────────────────────┘

┌─ LEP Requirements (Must Meet) ───────────────────┐
│ 🔴 STATUTORY                                     │
│                                                  │
│ ✓ Permissibility: Dwelling house permitted      │
│ ✓ Zone: R2 Low Density Residential              │
│ • Height limit: 9 metres (check your design)    │
│ • FSR: 0.6:1 (check your design)                │
│                                                  │
│ 📄 Inner West LEP 2022, Clauses 4.3, 4.6        │
└──────────────────────────────────────────────────┘

┌─ DCP Setbacks (Council Guidelines) ──────────────┐
│ 🟡 GUIDELINE (may be varied)                     │
│                                                  │
│ Front: 6 metres                                  │
│ Side: 4m (no driveway) / 7m (with driveway)     │
│ Rear: 4m (no driveway) / 7m (with driveway)     │
│                                                  │
│ Or: Match existing street setback pattern       │
│                                                  │
│ 📄 Marrickville DCP 2011, Section 4.2.4.3       │
└──────────────────────────────────────────────────┘

[Alternative if SEPP applies:]

┌─ Your Planning Pathway ──────────────────────────┐
│ ⚡ FAST TRACK AVAILABLE                          │
│ └─ Complying Development (Codes SEPP)            │
│    10 day approval if ALL criteria met          │
└──────────────────────────────────────────────────┘

┌─ SEPP Complying Development Standards ───────────┐
│ 🟢 FAST TRACK (ALL must be met)                  │
│                                                  │
│ Setbacks:                                        │
│   Front: 4.5m                                   │
│   Side: 900mm (single storey)                   │
│   Rear: 6m                                      │
│                                                  │
│ Site requirements:                              │
│   • Lot size ≥ 900m²  [Your lot: 650m² ❌]      │
│   • Not in heritage area  [✓]                   │
│   • Single storey  [✓]                          │
│                                                  │
│ 🔴 Your property doesn't qualify - use DA pathway│
│ 📄 Codes SEPP 2008, Schedule 1                  │
└──────────────────────────────────────────────────┘
```

**Color System:**
- 🔴 Red border = STATUTORY (must comply, no variation)
- 🟡 Yellow border = GUIDELINE (Council may vary)
- 🟢 Green border = FAST TRACK (optional pathway)
- ⚫ Gray border = NOT APPLICABLE

**Badge System:**
- 🏛️ SEPP (state law)
- 📋 LEP (local law)
- 🏘️ DCP (council guidelines)

---

## MVP Implementation Strategy

### Phase 1: Basic Hierarchy (Now)
```typescript
interface ConstraintHierarchy {
  pathway: 'complying' | 'da' | 'unknown';
  sepp: Constraint[] | null;
  lep: Constraint[];
  dcp: Constraint[];
  whichApplies: 'sepp' | 'lep-dcp';
}
```

**Display:**
1. Determine pathway (check SEPP eligibility)
2. Show banner: "Your pathway: [DA/Complying]"
3. Show applicable level with colored border
4. Collapse non-applicable levels

### Phase 2: Comparison View
- Add "Compare pathways" toggle
- Show SEPP vs DCP side-by-side
- Highlight differences

### Phase 3: Interactive Assessment
- User inputs property details
- System determines SEPP eligibility
- Real-time updates on which pathway applies

---

## Data Requirements

### 1. SEPP Eligibility Rules
```sql
CREATE TABLE sepp_eligibility_rules (
    id SERIAL PRIMARY KEY,
    sepp_name TEXT NOT NULL,
    development_type TEXT NOT NULL,
    zone_applicable TEXT[],

    -- Eligibility criteria
    min_lot_size NUMERIC,
    max_lot_size NUMERIC,
    max_storeys INTEGER,
    excludes_heritage BOOLEAN,
    excludes_flood BOOLEAN,

    -- Standards if eligible
    front_setback_m NUMERIC,
    side_setback_m NUMERIC,
    rear_setback_m NUMERIC,

    source_provision_id INTEGER REFERENCES regulatory_provisions(id)
);
```

### 2. Pathway Detection Query
```sql
-- Check if property qualifies for SEPP complying
SELECT
    CASE
        WHEN lot_size >= ser.min_lot_size
            AND storeys <= ser.max_storeys
            AND (NOT ser.excludes_heritage OR NOT in_hca)
        THEN 'complying_available'
        ELSE 'da_required'
    END as pathway,
    ser.front_setback_m as sepp_front,
    dcp.provision_text as dcp_setback
FROM sepp_eligibility_rules ser
CROSS JOIN property_data
LEFT JOIN regulatory_provisions dcp ON ...
WHERE ser.development_type = 'dwelling_house'
    AND property_data.address = $1;
```

### 3. Display Priority Logic
```typescript
function determineDisplay(constraints: ConstraintHierarchy) {
  if (constraints.pathway === 'complying' && constraints.sepp) {
    return {
      primary: constraints.sepp,
      primaryLevel: 'SEPP',
      primaryColor: 'green',
      secondary: constraints.dcp,
      secondaryLabel: 'Alternative: Development Application'
    };
  } else {
    return {
      primary: constraints.lep,
      primaryLevel: 'LEP',
      primaryColor: 'red',
      secondary: constraints.dcp,
      secondaryLevel: 'DCP',
      secondaryColor: 'yellow'
    };
  }
}
```

---

## MVP Scope (Realistic)

**Include:**
1. ✅ Pathway banner ("Your pathway: DA")
2. ✅ LEP constraints with red border ("STATUTORY")
3. ✅ DCP constraints with yellow border ("GUIDELINE")
4. ✅ Source citations for each
5. ✅ Simple explanation tooltips

**Exclude (future):**
1. ❌ SEPP eligibility checking (requires lot size, heritage data)
2. ❌ Interactive pathway comparison
3. ❌ Real-time qualification assessment

**Reason:**
- SEPP data not in database yet
- Property characteristics (lot size, storeys) not captured
- Focus on showing DCP correctly first

---

## Implementation Files

1. **Types:**
   - `types/regulatory-hierarchy.ts` - Define hierarchy types

2. **API Route:**
   - `app/api/compliance/constraints/route.ts` - Already separates LEP/DCP
   - Add `pathway` detection
   - Add `authority_level` to each constraint

3. **UI Components:**
   - `ConstraintCard.tsx` - Add colored border based on authority level
   - `PathwayBanner.tsx` - New component showing which pathway applies
   - `HierarchyExplainer.tsx` - Tooltip explaining SEPP/LEP/DCP

4. **Color Scheme:**
```css
.statutory-lep { border-left: 4px solid #dc2626; }  /* Red */
.guideline-dcp { border-left: 4px solid #eab308; }  /* Yellow */
.complying-sepp { border-left: 4px solid #16a34a; } /* Green */
```

---

## User Flow

**Scenario 1: User queries 180 Addison Rd (R2, dwelling house)**

1. System detects: Zone R2, Dev type: dwelling_house
2. System checks: SEPP complying available? (Future: NO - lot too small)
3. Display shows:
   ```
   ┌─ Your Planning Pathway ─────────────┐
   │ Development Application (LEP + DCP) │
   └─────────────────────────────────────┘

   [RED BORDER] LEP Controls (Must Meet)
   [YELLOW BORDER] DCP Setbacks (Guidelines)
   ```

**Scenario 2: Future - SEPP data available**

1. System detects: Lot 1,200m², single storey, not in HCA
2. System checks: SEPP complying ✓ Available
3. Display shows:
   ```
   ┌─ Your Planning Pathway ─────────────┐
   │ ⚡ FAST TRACK AVAILABLE              │
   │ Complying Development (10 days)     │
   └─────────────────────────────────────┘

   [GREEN BORDER] SEPP Complying Standards
   [Show/Hide] Alternative: DA pathway
   ```

---

## Recommendation for MVP

**Use Option 4: Priority Banner System**

**Why:**
- Simple to implement (just add colored borders + banner)
- Doesn't require SEPP data yet
- Shows hierarchy clearly (LEP = red, DCP = yellow)
- Extensible (add green SEPP borders later)
- User isn't overwhelmed

**Implementation:**
1. Add `authority_level: 'LEP' | 'DCP' | 'SEPP'` to constraints
2. Add colored border CSS classes
3. Add pathway banner component
4. Group constraints by authority level

**Next steps after MVP:**
1. Extract SEPP complying standards
2. Add property characteristics capture
3. Build pathway comparison feature

---

**Summary:**
- SEPP > LEP > DCP hierarchy is CRITICAL for correct advice
- MVP: Show LEP (red) vs DCP (yellow) clearly
- Future: Add SEPP (green) when data ready
- User always knows which level applies
