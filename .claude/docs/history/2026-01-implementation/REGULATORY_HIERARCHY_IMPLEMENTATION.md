# Regulatory Hierarchy Implementation
**Date:** 2025-10-23
**Purpose:** How to integrate LightRAG-processed requirements with proper precedence

---

## Legal Hierarchy (Descending Priority)

```
1. SEPP (State Environmental Planning Policy)
   ├─ Example: "Apartment Design Guide building separation"
   └─ Overrides all below

2. LEP (Local Environmental Plan)
   ├─ Example: "Height limit: 9.5m" (Clause 4.3)
   └─ Subject to SEPP, overrides DCP

3. DCP Base (Generic Controls - Part 2, Part 4.X)
   ├─ Example: "Front setback: 5.5m"
   └─ Cannot contradict LEP/SEPP

4. DCP Precinct (Neighborhood-Specific - Part 9)
   ├─ Example: "Maintain heritage streetscape character"
   └─ Supplements DCP Base, cannot contradict above
```

---

## Database Schema for Requirements

### Option 1: Flat Table with Priority Column

```sql
CREATE TABLE unified_requirements (
  id SERIAL PRIMARY KEY,
  lga TEXT NOT NULL,
  zone TEXT,
  dev_type TEXT,
  precinct_id TEXT,  -- NULL for non-precinct requirements

  -- Requirement details
  category TEXT,     -- 'setback_front', 'height', 'parking', etc.
  requirement_text TEXT,
  value_numeric NUMERIC,
  unit TEXT,

  -- Hierarchy
  source_level INTEGER,  -- 1=SEPP, 2=LEP, 3=DCP_Base, 4=DCP_Precinct
  source_type TEXT,      -- 'SEPP', 'LEP', 'DCP_Base', 'DCP_Precinct'
  source_document TEXT,  -- 'SEPP_Housing_2021', 'Inner_West_LEP_2022', etc.
  source_clause TEXT,    -- 'Clause 4.3', 'Part 4.1 Section 3', etc.

  -- For conflict detection
  override_ids INTEGER[], -- IDs of requirements this overrides

  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_unified_req_lookup ON unified_requirements(lga, zone, dev_type, precinct_id);
CREATE INDEX idx_unified_req_category ON unified_requirements(category);
CREATE INDEX idx_unified_req_level ON unified_requirements(source_level);
```

---

### Option 2: Separate Tables by Level (Cleaner)

```sql
-- Level 1: SEPP Requirements
CREATE TABLE sepp_requirements (
  id SERIAL PRIMARY KEY,
  sepp_id TEXT,              -- 'housing_2021', 'sustainable_buildings_2022'
  schedule TEXT,             -- 'Schedule 1', 'Part 3', etc.
  applies_to_zones TEXT[],   -- ['R1', 'R2', 'R3'] or NULL for all
  applies_to_dev_types TEXT[], -- ['apartment', 'dual_occupancy'] or NULL
  category TEXT,
  requirement_text TEXT,
  value_numeric NUMERIC,
  unit TEXT,
  source_provision_ids INTEGER[]
);

-- Level 2: LEP Requirements
CREATE TABLE lep_requirements (
  id SERIAL PRIMARY KEY,
  lep_id TEXT,               -- 'inner_west_2022'
  clause TEXT,               -- 'Clause 4.3'
  zone TEXT,
  category TEXT,             -- 'height', 'fsr', 'lot_size'
  requirement_text TEXT,
  value_numeric NUMERIC,
  unit TEXT,
  subject_to_sepp BOOLEAN,   -- Flag if SEPP can override
  source_provision_ids INTEGER[]
);

-- Level 3: DCP Base Requirements
CREATE TABLE dcp_base_requirements (
  id SERIAL PRIMARY KEY,
  lga TEXT,
  zone TEXT,
  dev_type TEXT,
  category TEXT,             -- 'setback_front', 'landscaping', 'parking'
  requirement_text TEXT,
  value_numeric NUMERIC,
  unit TEXT,
  source_provision_ids INTEGER[]
);

-- Level 4: DCP Precinct Requirements
CREATE TABLE dcp_precinct_requirements (
  id SERIAL PRIMARY KEY,
  precinct_id TEXT,
  lga TEXT,
  category TEXT,             -- 'character', 'design', 'setback_variation'
  requirement_text TEXT,
  value_numeric NUMERIC,
  unit TEXT,
  supplements_base BOOLEAN,  -- True if it adds to base, False if it modifies
  source_provision_ids INTEGER[]
);
```

---

## Runtime Query Logic

### Query Order (Highest Priority First)

```typescript
async function getAllRequirements(
  lga: string,
  zone: string,
  devType: string,
  precinctId?: string
) {
  const requirements = {
    sepp: [],
    lep: [],
    dcp_base: [],
    dcp_precinct: []
  };

  // 1. Get SEPP requirements (highest priority)
  requirements.sepp = await db.query(`
    SELECT * FROM sepp_requirements
    WHERE (applies_to_zones IS NULL OR $1 = ANY(applies_to_zones))
    AND (applies_to_dev_types IS NULL OR $2 = ANY(applies_to_dev_types))
  `, [zone, devType]);

  // 2. Get LEP requirements
  requirements.lep = await db.query(`
    SELECT * FROM lep_requirements
    WHERE lep_id = $1 AND zone = $2
  `, [getLepId(lga), zone]);

  // 3. Get DCP Base requirements
  requirements.dcp_base = await db.query(`
    SELECT * FROM dcp_base_requirements
    WHERE lga = $1 AND zone = $2 AND dev_type = $3
  `, [lga, zone, devType]);

  // 4. Get DCP Precinct requirements (if applicable)
  if (precinctId) {
    requirements.dcp_precinct = await db.query(`
      SELECT * FROM dcp_precinct_requirements
      WHERE precinct_id = $1
    `, [precinctId]);
  }

  return requirements;
}
```

---

## Conflict Resolution

### Detecting Conflicts

```typescript
function detectConflicts(requirements) {
  const conflicts = [];
  const byCategory = groupByCategory(requirements);

  // For each category (e.g., 'setback_front')
  for (const [category, reqs] of Object.entries(byCategory)) {
    // Sort by priority: SEPP > LEP > DCP_Base > DCP_Precinct
    const sorted = reqs.sort((a, b) => a.source_level - b.source_level);

    // Check if lower levels contradict higher levels
    const highestPriority = sorted[0];
    const conflicts = sorted.slice(1).filter(req =>
      contradicts(req, highestPriority)
    );

    if (conflicts.length > 0) {
      return {
        category,
        winner: highestPriority,
        overridden: conflicts,
        resolution: `${highestPriority.source_type} requirement overrides ${conflicts.map(c => c.source_type).join(', ')}`
      };
    }
  }

  return null;
}

function contradicts(req1, req2) {
  // Same category but different values
  if (req1.category !== req2.category) return false;

  // If both have numeric values, check if they differ
  if (req1.value_numeric && req2.value_numeric) {
    return req1.value_numeric !== req2.value_numeric;
  }

  // If both have text values, use semantic comparison
  // (This would need LLM or rules-based logic)
  return false;
}
```

---

## UI Display with Hierarchy

### Visual Hierarchy Indicator

```tsx
<div className="requirements-list">
  {/* SEPP - Highest Priority */}
  <div className="requirement-group border-l-4 border-red-600">
    <div className="header bg-red-50">
      <Badge variant="destructive">SEPP</Badge>
      <span className="text-xs">Highest Priority - Overrides all below</span>
    </div>
    <div className="requirements">
      <RequirementItem
        category="Building Separation"
        value="12m between buildings"
        source="SEPP Housing 2021, Part 3"
      />
    </div>
  </div>

  {/* LEP - Second Priority */}
  <div className="requirement-group border-l-4 border-orange-600">
    <div className="header bg-orange-50">
      <Badge variant="warning">LEP</Badge>
      <span className="text-xs">Subject to SEPP</span>
    </div>
    <div className="requirements">
      <RequirementItem
        category="Maximum Height"
        value="9.5m"
        source="Inner West LEP 2022, Clause 4.3"
      />
    </div>
  </div>

  {/* DCP Base - Third Priority */}
  <div className="requirement-group border-l-4 border-blue-600">
    <div className="header bg-blue-50">
      <Badge variant="secondary">DCP</Badge>
      <span className="text-xs">Cannot contradict LEP/SEPP</span>
    </div>
    <div className="requirements">
      <RequirementItem
        category="Front Setback"
        value="5.5m"
        source="Marrickville DCP 2011, Part 4.1"
      />
    </div>
  </div>

  {/* DCP Precinct - Lowest Priority (Supplements) */}
  {precinctId && (
    <div className="requirement-group border-l-4 border-green-600">
      <div className="header bg-green-50">
        <Badge variant="outline">Precinct</Badge>
        <span className="text-xs">Neighborhood-specific supplements</span>
      </div>
      <div className="requirements">
        <RequirementItem
          category="Character"
          value="Maintain low-density residential character"
          source={`Precinct ${precinctId} - South Western Marrickville`}
        />
      </div>
    </div>
  )}
</div>
```

---

## Handling Overrides

### Example Conflict: SEPP Overrides DCP

**Scenario:**
- DCP says: "Front setback: 5.5m"
- SEPP Housing says: "Front setback: 4m for social housing"

**Resolution:**
```tsx
<div className="requirement-conflict">
  <div className="active-requirement border-l-4 border-red-600">
    <Badge variant="destructive">SEPP - APPLIES</Badge>
    <RequirementItem
      category="Front Setback"
      value="4m (for social housing)"
      source="SEPP Housing 2021"
    />
  </div>

  <div className="overridden-requirement opacity-50">
    <Badge variant="outline">DCP - OVERRIDDEN</Badge>
    <RequirementItem
      category="Front Setback"
      value="5.5m"
      source="Marrickville DCP 2011"
      strikethrough
    />
    <div className="text-xs text-gray-600">
      ℹ️ This requirement is overridden by SEPP Housing 2021
    </div>
  </div>
</div>
```

---

## LightRAG Processing with Hierarchy Context

### Prompt for LightRAG

When processing provisions, include hierarchy context:

```typescript
const prompt = `
You are processing ${sourceType} provisions for categorization.

IMPORTANT HIERARCHY RULES:
${sourceType === 'SEPP' ? '- This is HIGHEST priority - overrides LEP and DCP' : ''}
${sourceType === 'LEP' ? '- This is subject to SEPP but overrides DCP' : ''}
${sourceType === 'DCP_Base' ? '- This cannot contradict LEP or SEPP' : ''}
${sourceType === 'DCP_Precinct' ? '- This supplements DCP Base, cannot contradict LEP/SEPP' : ''}

Extract requirements from these provisions:
${provisions.map(p => p.text).join('\n\n')}

For each requirement, specify:
1. Category (setback_front, height, parking, etc.)
2. Value (numeric if applicable)
3. Unit (m, %, spaces, etc.)
4. Full text description
5. Confidence level
`;
```

---

## Implementation Steps

### Phase 1: Process by Level
1. Process SEPP provisions → `sepp_requirements`
2. Process LEP provisions → `lep_requirements`
3. Process DCP base provisions → `dcp_base_requirements`
4. Process DCP precinct provisions → `dcp_precinct_requirements`

### Phase 2: Build Conflict Detection
1. Create conflict detection function
2. Flag known overrides (SEPP > LEP > DCP)
3. Store override relationships

### Phase 3: Update UI
1. Display requirements grouped by level
2. Show visual hierarchy (color-coded borders)
3. Display conflicts with resolution

### Phase 4: Runtime Query
1. Query all 4 levels
2. Merge with precedence
3. Return with hierarchy metadata

---

## Cost Estimate

### Processing Costs

```
SEPP Requirements:
  - ~30 SEPP documents × $0.10 = $3.00

LEP Requirements:
  - ~5 LEP documents × $0.10 = $0.50

DCP Base Requirements:
  - ~100 combinations × $0.10 = $10.00

DCP Precinct Requirements:
  - ~41 precincts × $0.02 = $0.82

Total: ~$14.32 one-time
Runtime: $0 per address
```

---

## Summary

**Hierarchy Enforcement:**
1. Query all 4 levels separately
2. Sort by priority (1=SEPP, 2=LEP, 3=DCP, 4=Precinct)
3. Detect conflicts where same category has different values
4. Display with visual hierarchy
5. Show overrides/conflicts clearly to user

**Benefits:**
- Clear legal precedence
- Transparent conflict resolution
- User sees which requirement "wins"
- Compliant with planning law

**Next Step:** Choose Option 1 (flat table) or Option 2 (separate tables) for storing requirements.
