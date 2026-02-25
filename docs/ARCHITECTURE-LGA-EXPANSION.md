# LGA Expansion Architecture - Best Practices

**Date**: 2026-02-25
**Status**: Design Document
**Purpose**: Guide for adding new LGAs to PlotDetect with minimal code changes

---

## 🏗️ Current Architecture Analysis

### ✅ **What Works Well** (Leverage These Patterns)

1. **JSON-based Council Configs** (`lib/council-configs/*.json`)
   - ✅ External configuration files
   - ✅ Schema-validated via TypeScript interfaces
   - ✅ No code recompilation needed for config changes
   - ✅ Example: `marrickville.json`, `leichhardt.json`, `ashfield.json`

2. **Centralized Config Loader** (`lib/council-config.ts`)
   - ✅ Single registry: `COUNCIL_CONFIGS`
   - ✅ Alias mapping for fuzzy matching
   - ✅ Fallback behavior: `getCouncilConfig()` with defaults
   - ✅ Utility functions: `detectCouncil()`, `isCouncilConfigured()`

3. **Former Council Mapping** (`lib/inner-west-mapping-v2.ts`)
   - ✅ Lazy-loaded from external JSON
   - ✅ Postcode + suburb-based detection
   - ✅ Handles special cases (split postcodes)

---

## ❌ **What Needs Fixing** (Anti-Patterns to Eliminate)

### 1. **SEPP Tab Hardcoding** (StateLevelControls.tsx)
   - ❌ Hardcoded "Inner West" fallback (line 390)
   - ❌ Hardcoded zone arrays duplicated across file (lines 125, 207, 416)
   - ❌ SEPP mapping object hardcoded in component (lines 101-113)
   - ❌ 15+ hardcoded R2 PDF URLs
   - ❌ Hardcoded regulatory thresholds (800m, 600m, 400m)

### 2. **Missing State-Level Config Layer**
   - ❌ No separation between DCP config (council-level) and SEPP config (state-level)
   - ❌ SEPP requirements hardcoded in components instead of config
   - ❌ No LGA → BASIX area mapping config

### 3. **Inconsistent Config Patterns**
   - ❌ DCP config uses JSON files
   - ❌ SEPP config uses TypeScript constants
   - ❌ PDF URLs scattered throughout components

---

## 🎯 **Recommended Architecture** (3-Layer Config System)

```
┌─────────────────────────────────────────────────────┐
│  Layer 1: State-Level Config (NSW-wide)            │
│  - SEPP mappings                                    │
│  - Regulatory thresholds (TOD, LMR, ADG)           │
│  - BASIX zones                                      │
│  - PDF URL patterns                                 │
│  File: lib/state-config/nsw.json                   │
└─────────────────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────┐
│  Layer 2: LGA-Level Config (Per-LGA)               │
│  - LGA metadata (name, former councils, BASIX area)│
│  - Applicable SEPPs for this LGA                    │
│  - Zone → former council mapping (Inner West only) │
│  - Transport proximity thresholds                   │
│  File: lib/lga-configs/{lga-id}.json               │
└─────────────────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────┐
│  Layer 3: DCP/Council-Level Config (Per-DCP)      │
│  - DCP structure (existing council-config.ts)      │
│  - Topic groupings, layer labels                    │
│  - UI behavior (filters, warnings)                  │
│  File: lib/council-configs/{council-id}.json       │
│  (Already implemented ✅)                           │
└─────────────────────────────────────────────────────┘
```

---

## 📁 **Proposed File Structure**

```
lib/
├── state-config/                      # NEW - State-level NSW constants
│   ├── index.ts                       # Config loader + validation
│   ├── nsw.json                       # NSW regulatory constants
│   └── schema.ts                      # TypeScript interfaces
│
├── lga-configs/                       # NEW - Per-LGA config
│   ├── index.ts                       # LGA registry + loader
│   ├── schema.ts                      # LGAConfig interface
│   ├── inner-west.json                # Inner West LGA config
│   ├── parramatta.json                # Example: New LGA
│   └── __tests__/
│       └── validation.test.ts         # Config validation tests
│
├── council-configs/                   # EXISTING - Per-DCP config
│   ├── marrickville.json              # ✅ Already implemented
│   ├── leichhardt.json                # ✅ Already implemented
│   ├── ashfield.json                  # ✅ Already implemented
│   └── parramatta.json                # Example: New council
│
├── council-config.ts                  # EXISTING - DCP config loader ✅
├── inner-west-mapping-v2.ts           # EXISTING - Address → council ✅
│
├── pdf-url-builder.ts                 # NEW - Centralized PDF URLs
├── regulatory-constants.ts            # NEW - NSW thresholds (800m, etc)
│
└── services/
    ├── lga-detector.ts                # NEW - Auto-detect LGA from address
    └── config-validator.ts            # NEW - Validate all configs at build
```

---

## 🔧 **Implementation Patterns**

### Pattern 1: **State-Level Constants** (NSW-wide, never changes per LGA)

```typescript
// lib/state-config/nsw.json
{
  "regulatory_thresholds": {
    "tod": {
      "heavy_rail_walkable_m": 800,
      "light_rail_walkable_m": 600,
      "bus_walkable_m": 400,
      "transport_proximity_search_m": 1000
    },
    "housing_sepp": {
      "default_lot_width_m": 15,
      "lmr_eligible_zones": ["R1", "R2", "R3", "R4"]
    }
  },
  "sepp_id_mapping": {
    "SEPP_HOUSING_2021": "housing_2021",
    "SEPP_65": "housing_2021",
    "SEPP_SUSTAINABLE_BUILDINGS_2022": "sustainable_buildings_2022"
  },
  "pdf_base_url": "https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev"
}
```

**Usage:**
```typescript
import { getNSWConfig } from '@/lib/state-config';

const config = getNSWConfig();
const threshold = config.regulatory_thresholds.tod.heavy_rail_walkable_m; // 800
```

---

### Pattern 2: **LGA-Level Config** (Per-LGA, but not per-DCP)

```typescript
// lib/lga-configs/inner-west.json
{
  "id": "inner_west",
  "name": "Inner West",
  "type": "amalgamated",
  "former_councils": ["Ashfield", "Leichhardt", "Marrickville"],
  "basix": {
    "area_code": "Area 5",
    "area_name": "Inner West",
    "climate_zone": "56",
    "water_target_percent": 40
  },
  "planning": {
    "residential_zones": ["R1", "R2", "R3", "R4", "R5", "B1", "B2", "B4", "MU1", "RU5"],
    "industrial_zones": ["IN1", "IN2", "E4", "E5", "B5", "B6", "B7", "E3", "B3"],
    "apartment_permitting_zones": ["R1", "R2", "R3", "R4", "B1", "B2", "B3", "B4", "MU1"]
  },
  "applicable_sepps": [
    "SEPP_HOUSING_2021",
    "SEPP_SUSTAINABLE_BUILDINGS_2022",
    "SEPP_RESILIENCE_HAZARDS_2021"
  ],
  "requires_former_council_detection": true
}
```

**Usage:**
```typescript
import { getLGAConfig } from '@/lib/lga-configs';

const lgaConfig = getLGAConfig('inner_west');
const basixArea = lgaConfig.basix.area_code; // "Area 5"
const zones = lgaConfig.planning.residential_zones; // ["R1", "R2", ...]
```

---

### Pattern 3: **DCP-Level Config** (Existing - Keep As-Is ✅)

```typescript
// lib/council-configs/marrickville.json (EXISTING)
{
  "id": "marrickville",
  "name": "Marrickville",
  "parentLGA": "Inner West",
  "dcpCitation": "Marrickville Development Control Plan 2011",
  "totalProvisions": 1866,
  "layerLabels": {
    "generic": "Marrickville-wide",
    "precinct": "Precinct Character"
  },
  "categoryGroups": { ... }
}
```

**Usage:** (No changes needed - already working ✅)
```typescript
import { getCouncilConfig } from '@/lib/council-config';

const councilConfig = getCouncilConfig('marrickville');
const label = councilConfig.layerLabels.generic; // "Marrickville-wide"
```

---

## 🚀 **Adding a New LGA: Step-by-Step**

### Example: Adding **Parramatta LGA**

#### Step 1: Create LGA Config
```bash
# Create new LGA config file
cp lib/lga-configs/inner-west.json lib/lga-configs/parramatta.json
```

Edit `parramatta.json`:
```json
{
  "id": "parramatta",
  "name": "Parramatta",
  "type": "single",
  "former_councils": [],
  "basix": {
    "area_code": "Area 3",
    "area_name": "Parramatta",
    "climate_zone": "56",
    "water_target_percent": 40
  },
  "planning": {
    "residential_zones": ["R1", "R2", "R3", "R4"],
    "industrial_zones": ["IN1", "IN2", "IN3"],
    "apartment_permitting_zones": ["R3", "R4", "B3", "B4"]
  },
  "applicable_sepps": [
    "SEPP_HOUSING_2021",
    "SEPP_SUSTAINABLE_BUILDINGS_2022"
  ],
  "requires_former_council_detection": false
}
```

#### Step 2: Create DCP Config
```bash
# Create council config for Parramatta DCP
cp lib/council-configs/marrickville.json lib/council-configs/parramatta.json
```

Edit values for Parramatta DCP structure.

#### Step 3: Register in Loaders
```typescript
// lib/lga-configs/index.ts
import parramattaConfig from './parramatta.json';

export const LGA_REGISTRY: Record<string, LGAConfig> = {
  'inner_west': innerWestConfig,
  'parramatta': parramattaConfig, // Add new LGA
};
```

```typescript
// lib/council-config.ts
import parramattaCouncilConfig from './council-configs/parramatta.json';

export const COUNCIL_CONFIGS: Record<string, CouncilConfig> = {
  marrickville: marrickvilleConfig,
  leichhardt: leichhardtConfig,
  ashfield: ashfieldConfig,
  parramatta: parramattaCouncilConfig, // Add new DCP
};
```

#### Step 4: Add Database Data
```sql
-- migrations/XXX_add_parramatta.sql
INSERT INTO lgas (name, code, bounds) VALUES
  ('Parramatta', 'PARR', ST_GeomFromGeoJSON('...'));

-- Import DCP provisions for Parramatta
INSERT INTO regulatory_provisions (...)
SELECT ... FROM parramatta_dcp_extraction;
```

#### Step 5: Test
```typescript
// __tests__/parramatta.test.ts
describe('Parramatta LGA', () => {
  it('loads LGA config', () => {
    const config = getLGAConfig('parramatta');
    expect(config.name).toBe('Parramatta');
  });

  it('loads DCP config', () => {
    const config = getCouncilConfig('parramatta');
    expect(config.parentLGA).toBe('Parramatta');
  });
});
```

---

## ✅ **Validation & Safety**

### Build-Time Validation
```typescript
// lib/services/config-validator.ts
export function validateAllConfigs() {
  // 1. Check all LGA configs have valid schemas
  for (const [id, config] of Object.entries(LGA_REGISTRY)) {
    validateLGAConfig(config);
  }

  // 2. Check all DCP configs reference valid LGAs
  for (const [id, config] of Object.entries(COUNCIL_CONFIGS)) {
    if (config.parentLGA && !LGA_REGISTRY[config.parentLGA.toLowerCase()]) {
      throw new Error(`Council ${id} references unknown LGA: ${config.parentLGA}`);
    }
  }

  // 3. Check zone codes are valid NSW codes
  const validZones = ['R1', 'R2', 'R3', 'R4', 'B1', 'B2', ...];
  // ... validation logic
}
```

Run in CI:
```json
// package.json
{
  "scripts": {
    "validate-configs": "ts-node scripts/validate-configs.ts",
    "build": "npm run validate-configs && next build"
  }
}
```

---

## 🎯 **Key Principles**

1. **Separation of Concerns**
   - State-level (NSW) → Never changes per LGA
   - LGA-level → Changes per LGA, but not per DCP
   - DCP-level → Changes per council/DCP

2. **Config > Code**
   - Prefer JSON configs over TypeScript constants
   - Move all LGA-specific data to configs
   - Components should be data-driven

3. **Fail Fast**
   - Validate configs at build time
   - Throw errors for missing LGAs (no silent fallbacks)
   - Type-safe configs with TypeScript

4. **Single Source of Truth**
   - NSW thresholds → `lib/state-config/nsw.json`
   - LGA metadata → `lib/lga-configs/{lga}.json`
   - DCP structure → `lib/council-configs/{council}.json`

5. **Leverage Existing Patterns**
   - ✅ Keep `council-config.ts` pattern (works well)
   - ✅ Keep JSON-based config approach
   - ✅ Keep lazy-loading for performance
   - ❌ Replace hardcoded arrays in components

---

## 📊 **Migration Priority**

| Priority | Task | Impact | Effort |
|----------|------|--------|--------|
| **P0** | Remove "Inner West" fallback | Blocks all non-IW LGAs | Low |
| **P1** | Create LGA config layer | Enables multi-LGA | Medium |
| **P1** | Extract SEPP mappings to config | Reduces component bloat | Low |
| **P1** | Centralize PDF URLs | Easier R2 migration | Low |
| **P2** | Extract regulatory constants | Better documentation | Low |
| **P2** | Create LGA detector service | Better UX | Medium |
| **P3** | Extract UI text strings | i18n-ready | Medium |

---

## 🔗 **Related Files**

- Task list: See tasks #27-#36 in task tracker
- Hardcoding audit: Run `grep -r "Inner West" frontend-nextjs/`
- Existing config pattern: `lib/council-config.ts`
- SEPP component: `components/compliance/StateLevelControls.tsx`

---

**Next Steps**: Start with Task #28 (Create LGA configuration schema)
