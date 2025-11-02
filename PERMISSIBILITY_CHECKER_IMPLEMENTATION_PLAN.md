# Permissibility Checker - Complete Implementation Plan

**Priority:** P0 (CRITICAL - First professional question)
**Estimated Time:** 3-4 weeks
**Start Date:** 2025-11-02
**Status:** READY TO START

---

## Why This is Priority 1

**The First Question Professionals Ask:**
> "Can I build a granny flat / dual occupancy / shop-top housing at [address]?"

**Without This:**
- Users must manually check LEP PDF Land Use Tables (slow, confusing)
- Can't answer basic permissibility questions
- Platform shows compliance requirements for unpermitted development (wasted effort)

**With This:**
- Instant YES/NO answer to "Can I build X here?"
- Show only relevant LEP clauses for that dev type
- Foundation for all other features (permissibility → compliance requirements)

---

## Product Vision

### User Flow (Before):
```
User: "Can I build a granny flat at 181 Addison Road, Ashfield?"
Current Platform: [Shows all DCP requirements, no permissibility check]
User: "Wait, is this even allowed?"
User: [Opens LEP PDF, searches for R2 Land Use Table, confused]
```

### User Flow (After):
```
User: "Can I build a granny flat at 181 Addison Road, Ashfield?"
Platform:
┌─────────────────────────────────────────────┐
│ ✅ YES - Secondary Dwellings ARE PERMITTED │
│                                             │
│ Zone: R2 Low Density Residential           │
│ Permissibility: Permitted with consent     │
│                                             │
│ LEP Controls:                               │
│ ├─ Max 60m² (Clause 5.4)                  │
│ ├─ Height 9m (Clause 4.3)                 │
│ └─ FSR 0.5:1 (Clause 4.4)                 │
│                                             │
│ DCP Requirements: 12 controls in Part 4.2  │
│                                             │
│ [View Detailed Requirements →]             │
└─────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Data Extraction (Week 1-2)

#### Task 1.1: Extract LEP Land Use Tables (3-4 days)

**Source:** Inner West LEP 2022 - Schedule 1 (Land Use Table)

**Structure:**
```python
# Database table: lep_land_use_table
{
    "zone": "R2",
    "zone_name": "Low Density Residential",
    "lga": "Inner West",
    "development_type": "dwelling_houses",
    "permissibility": "permitted",  # or "prohibited", "permissible"
    "notes": null
}
```

**Zones to Extract:**
- R1 General Residential
- R2 Low Density Residential
- R3 Medium Density Residential
- R4 High Density Residential
- B1 Neighbourhood Centre
- B2 Local Centre
- B4 Mixed Use
- B6 Enterprise Corridor
- B7 Business Park
- IN1 General Industrial
- IN2 Light Industrial
- RE1 Public Recreation
- RE2 Private Recreation
- SP2 Infrastructure
- E1 Local Centre (Ashfield legacy)
- E2 Commercial (Marrickville/Leichhardt legacy)

**Development Types to Extract:**
```
Residential:
- Dwelling houses
- Secondary dwellings (granny flats)
- Dual occupancies
- Multi dwelling housing
- Residential flat buildings
- Boarding houses
- Group homes

Commercial:
- Shop top housing
- Business premises
- Office premises
- Retail premises

Mixed Use:
- Mixed use development

Other:
- Child care centres
- Community facilities
- Educational establishments
- Entertainment facilities
- Places of public worship
```

**Extraction Script:**

```python
# File: extract_lep_land_use_tables.py

import json
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

# LEP Land Use Table data (extracted from LEP PDF Schedule 1)
# This is the COMPLETE data - extract from LEP PDF manually first

LAND_USE_TABLE = {
    "R2": {
        "zone_name": "Low Density Residential",
        "permitted": [
            "dwelling_houses",
            "secondary_dwellings",
            "group_homes"
        ],
        "permissible": [
            "bed_and_breakfast_accommodation",
            "boarding_houses",
            "child_care_centres",
            "community_facilities",
            "home_businesses",
            "home_industries",
            "places_of_public_worship",
            "respite_day_care_centres"
        ],
        "prohibited": [
            "advertising_structures",
            "agriculture",
            "air_transport_facilities",
            # ... (everything else not listed above)
        ]
    },
    # Add all other zones...
}

conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD')
)

cur = conn.cursor()

# Create table
cur.execute("""
    CREATE TABLE IF NOT EXISTS lep_land_use_table (
        id SERIAL PRIMARY KEY,
        zone VARCHAR(10) NOT NULL,
        zone_name VARCHAR(255) NOT NULL,
        lga VARCHAR(255) NOT NULL,
        development_type VARCHAR(255) NOT NULL,
        permissibility VARCHAR(50) NOT NULL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        UNIQUE(zone, lga, development_type)
    )
""")

# Insert data
for zone, data in LAND_USE_TABLE.items():
    zone_name = data['zone_name']

    for dev_type in data['permitted']:
        cur.execute("""
            INSERT INTO lep_land_use_table
            (zone, zone_name, lga, development_type, permissibility)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (zone, lga, development_type) DO NOTHING
        """, (zone, zone_name, "Inner West", dev_type, "permitted"))

    for dev_type in data['permissible']:
        cur.execute("""
            INSERT INTO lep_land_use_table
            (zone, zone_name, lga, development_type, permissibility)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (zone, lga, development_type) DO NOTHING
        """, (zone, zone_name, "Inner West", dev_type, "permissible"))

conn.commit()
conn.close()

print("LEP Land Use Table extracted successfully")
```

**Action:** Manually extract complete Land Use Table from Inner West LEP 2022 PDF (Schedule 1), then run script.

---

#### Task 1.2: Extract Dev-Type-Specific LEP Clauses (2-3 days)

**Source:** Inner West LEP 2022 - Part 5 (Miscellaneous Provisions)

**Dev-Type-Specific Clauses:**
- **Clause 5.4:** Controls relating to secondary dwellings
- **Clause 5.5:** Controls relating to dual occupancies
- **Clause 5.6:** Architectural roof features
- **Clause 5.10:** Heritage conservation
- **Clause 5.11:** Bush fire hazard reduction
- etc.

**Structure:**
```python
# Database table: lep_development_type_clauses
{
    "lga": "Inner West",
    "clause_number": "5.4",
    "clause_title": "Controls relating to secondary dwellings",
    "development_type": "secondary_dwellings",
    "requirements": [
        "Maximum floor area: 60m²",
        "Must be on same lot as principal dwelling",
        "One secondary dwelling per lot",
        "Consent authority may impose conditions"
    ],
    "applies_to_zones": ["R2", "R3", "E4"],
    "full_text": "..."
}
```

**Extraction Script:**

```python
# File: extract_lep_dev_type_clauses.py

import json
from openai import OpenAI
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Read Inner West LEP 2022 Part 5 (already extracted with MinerU)
with open('docs/inner_west_lep_2022_part5.md', 'r') as f:
    lep_part5_text = f.read()

# Extract dev-type-specific clauses using LLM
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": """You are a planning law specialist.
Extract development-type-specific clauses from LEP Part 5.
For each clause, extract:
- Clause number (e.g., 5.4)
- Clause title
- Development type it applies to
- List of specific requirements/controls
- Zones it applies to (if specified)

Return as JSON array."""},
        {"role": "user", "content": lep_part5_text}
    ],
    temperature=0.1
)

clauses = json.loads(response.choices[0].message.content)

# Insert into database
conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD')
)

cur = conn.cursor()

# Create table
cur.execute("""
    CREATE TABLE IF NOT EXISTS lep_development_type_clauses (
        id SERIAL PRIMARY KEY,
        lga VARCHAR(255) NOT NULL,
        clause_number VARCHAR(50) NOT NULL,
        clause_title TEXT NOT NULL,
        development_type VARCHAR(255),
        requirements JSONB,
        applies_to_zones JSONB,
        full_text TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        UNIQUE(lga, clause_number)
    )
""")

for clause in clauses:
    cur.execute("""
        INSERT INTO lep_development_type_clauses
        (lga, clause_number, clause_title, development_type, requirements, applies_to_zones, full_text)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (lga, clause_number) DO NOTHING
    """, (
        "Inner West",
        clause['clause_number'],
        clause['clause_title'],
        clause.get('development_type'),
        json.dumps(clause['requirements']),
        json.dumps(clause.get('applies_to_zones', [])),
        clause.get('full_text')
    ))

conn.commit()
conn.close()

print(f"Extracted {len(clauses)} dev-type-specific LEP clauses")
```

---

#### Task 1.3: Update Dev Type Mappings (1 day)

**Current Mapping (Incorrect):**
```json
// frontend-nextjs/config/development-type-mappings.json
{
  "ui_to_lep": {
    "secondary_dwelling": "dwelling_house",  // WRONG
    "multi_dwelling": "multi_dwelling_housing",  // OK
    "shop_top_housing": "business_premises"  // WRONG
  }
}
```

**Corrected Mapping:**
```json
{
  "ui_to_lep": {
    "secondary_dwelling": "secondary_dwellings",
    "granny_flat": "secondary_dwellings",
    "dual_occupancy": "dual_occupancies",
    "multi_dwelling": "multi_dwelling_housing",
    "residential_flat": "residential_flat_buildings",
    "shop_top_housing": "shop_top_housing",
    "commercial": "business_premises",
    "child_care": "child_care_centres",
    "mixed_use": "mixed_use_development"
  },
  "lep_to_ui": {
    "secondary_dwellings": "secondary_dwelling",
    "dual_occupancies": "dual_occupancy",
    "multi_dwelling_housing": "multi_dwelling",
    "residential_flat_buildings": "residential_flat",
    "shop_top_housing": "shop_top_housing",
    "business_premises": "commercial",
    "child_care_centres": "child_care",
    "mixed_use_development": "mixed_use"
  }
}
```

**Action:** Update `development-type-mappings.json` with correct LEP terminology.

---

### Phase 2: API Implementation (Week 2-3)

#### Task 2.1: Create Permissibility API Endpoint (2-3 days)

**File:** `frontend-nextjs/app/api/permissibility/check/route.ts`

```typescript
import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/db';
import { NSWPlanningPortalService } from '@/lib/nsw-planning-portal';
import { determineFormerCouncilArea } from '@/lib/inner-west-mapping-v2';
import { normalizeDevType } from '@/lib/dev-type-loader';

interface PermissibilityRequest {
  address: string;
  developmentType: string;
}

export async function POST(request: NextRequest) {
  try {
    const { address, developmentType }: PermissibilityRequest = await request.json();

    if (!address || !developmentType) {
      return NextResponse.json({
        success: false,
        error: 'Address and development type are required'
      }, { status: 400 });
    }

    // 1. Get property details from Planning Portal
    const property = await NSWPlanningPortalService.searchProperty(address);

    if (!property) {
      return NextResponse.json({
        success: false,
        error: 'Property not found'
      }, { status: 404 });
    }

    const constraints = await NSWPlanningPortalService.getPropertyDetails(property.propId);

    const zone = constraints.zone;  // e.g., "R2"
    const lga = constraints.lga;    // e.g., "Inner West"
    const formerCouncil = determineFormerCouncilArea(address, lga);

    // 2. Normalize dev type to LEP terminology
    const lepDevType = normalizeDevType(developmentType);

    // 3. Check LEP Land Use Table
    const permissibilityResult = await query(`
      SELECT permissibility, zone_name, notes
      FROM lep_land_use_table
      WHERE zone = $1
        AND lga = $2
        AND development_type = $3
    `, [zone, lga, lepDevType]);

    if (!permissibilityResult.rows.length || permissibilityResult.rows[0].permissibility === 'prohibited') {
      // Find alternative options
      const alternatives = await query(`
        SELECT DISTINCT development_type
        FROM lep_land_use_table
        WHERE zone = $1
          AND lga = $2
          AND permissibility IN ('permitted', 'permissible')
        LIMIT 10
      `, [zone, lga]);

      return NextResponse.json({
        success: false,
        permitted: false,
        zone: zone,
        zone_name: permissibilityResult.rows[0]?.zone_name || `${zone} Zone`,
        lga: lga,
        formerCouncil: formerCouncil,
        reason: `${lepDevType} is prohibited in ${zone} zone`,
        alternative_options: alternatives.rows.map(r => r.development_type)
      });
    }

    const permissibility = permissibilityResult.rows[0];

    // 4. Get LEP dev-type-specific clauses
    const lepClauses = await query(`
      SELECT clause_number, clause_title, requirements, applies_to_zones
      FROM lep_development_type_clauses
      WHERE lga = $1
        AND (development_type = $2 OR $3 = ANY(applies_to_zones))
    `, [lga, lepDevType, zone]);

    // 5. Get general LEP controls (height, FSR)
    const generalControls = {
      max_height: constraints.maxHeight,
      max_fsr: constraints.maxFsr
    };

    // 6. Get DCP section info
    const dcpSections = await query(`
      SELECT section_id, section_title, COUNT(*) as requirement_count,
             ARRAY_AGG(DISTINCT category) as categories
      FROM dcp_general_requirements
      WHERE former_council = $1
        AND (development_type = $2 OR development_type IS NULL)
      GROUP BY section_id, section_title
      ORDER BY requirement_count DESC
      LIMIT 5
    `, [formerCouncil, developmentType]);

    return NextResponse.json({
      success: true,
      permitted: true,
      permissibility: permissibility.permissibility,
      zone: zone,
      zone_name: permissibility.zone_name,
      lga: lga,
      formerCouncil: formerCouncil,
      lep_controls: {
        general: generalControls,
        dev_type_specific: lepClauses.rows
      },
      dcp_sections: dcpSections.rows,
      summary: generateSummary(permissibility, lepClauses.rows, generalControls)
    });

  } catch (error) {
    console.error('Permissibility check error:', error);
    return NextResponse.json({
      success: false,
      error: 'Failed to check permissibility'
    }, { status: 500 });
  }
}

function generateSummary(permissibility: any, lepClauses: any[], generalControls: any): string {
  const devTypeDisplay = permissibility.development_type.replace(/_/g, ' ');

  if (permissibility.permissibility === 'permitted') {
    return `${devTypeDisplay} are PERMITTED with consent in ${permissibility.zone_name}. ${lepClauses.length > 0 ? `See LEP Clause ${lepClauses[0].clause_number} for specific controls.` : ''}`;
  } else if (permissibility.permissibility === 'permissible') {
    return `${devTypeDisplay} are PERMISSIBLE in ${permissibility.zone_name} (requires consent and assessment). ${lepClauses.length > 0 ? `See LEP Clause ${lepClauses[0].clause_number} for specific controls.` : ''}`;
  }

  return `Check permissibility status for ${devTypeDisplay} in ${permissibility.zone_name}.`;
}
```

---

#### Task 2.2: Create Normalization Helper (1 day)

**Update:** `frontend-nextjs/lib/dev-type-loader.ts`

```typescript
// Add new function
export function normalizeDevTypeToLEP(uiType: string): string {
  const mappings = getDevTypeMappings();
  const lepType = mappings.ui_to_lep[uiType];

  if (!lepType) {
    console.warn(`No LEP mapping for dev type: ${uiType}`);
    return uiType; // Fallback to original
  }

  return lepType;
}

// Update existing function to use correct mappings
export function normalizeDevType(uiType: string): string {
  return normalizeDevTypeToLEP(uiType);
}
```

---

### Phase 3: UI Implementation (Week 3-4)

#### Task 3.1: Create Permissibility Checker Component (3-4 days)

**File:** `frontend-nextjs/components/compliance/PermissibilityChecker.tsx`

```typescript
'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';

const DEVELOPMENT_TYPES = [
  { value: 'secondary_dwelling', label: 'Granny Flat / Secondary Dwelling' },
  { value: 'dual_occupancy', label: 'Dual Occupancy' },
  { value: 'multi_dwelling', label: 'Multi Dwelling Housing (Townhouses)' },
  { value: 'residential_flat', label: 'Residential Flat Building (Apartments)' },
  { value: 'shop_top_housing', label: 'Shop Top Housing' },
  { value: 'commercial', label: 'Commercial / Business Premises' },
  { value: 'child_care', label: 'Child Care Centre' },
  { value: 'mixed_use', label: 'Mixed Use Development' }
];

interface PermissibilityCheckerProps {
  propertyAddress: string;
}

export function PermissibilityChecker({ propertyAddress }: PermissibilityCheckerProps) {
  const [selectedDevType, setSelectedDevType] = useState('');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  async function checkPermissibility() {
    if (!selectedDevType) return;

    setLoading(true);
    try {
      const response = await fetch('/api/permissibility/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          address: propertyAddress,
          developmentType: selectedDevType
        })
      });

      const data = await response.json();
      setResult(data);
    } catch (error) {
      console.error('Permissibility check failed:', error);
      setResult({ success: false, error: 'Failed to check permissibility' });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-white border rounded-lg p-6 mb-6">
      <h2 className="text-xl font-semibold mb-4">Can I Build...?</h2>

      <div className="flex gap-4 items-end">
        <div className="flex-1">
          <label className="block text-sm font-medium mb-2">
            Select Development Type
          </label>
          <select
            value={selectedDevType}
            onChange={(e) => setSelectedDevType(e.target.value)}
            className="w-full p-2 border rounded-md"
          >
            <option value="">Choose development type...</option>
            {DEVELOPMENT_TYPES.map(dt => (
              <option key={dt.value} value={dt.value}>
                {dt.label}
              </option>
            ))}
          </select>
        </div>

        <Button
          onClick={checkPermissibility}
          disabled={!selectedDevType || loading}
        >
          {loading ? 'Checking...' : 'Check Permissibility'}
        </Button>
      </div>

      {result && (
        <div className={`mt-6 p-4 rounded-lg border-2 ${
          result.permitted
            ? 'bg-green-50 border-green-500'
            : 'bg-red-50 border-red-500'
        }`}>
          <div className="flex items-start gap-3">
            <span className="text-3xl">
              {result.permitted ? '✅' : '❌'}
            </span>

            <div className="flex-1">
              <h3 className={`text-lg font-semibold mb-2 ${
                result.permitted ? 'text-green-900' : 'text-red-900'
              }`}>
                {result.permitted ? 'YES - PERMITTED' : 'NO - PROHIBITED'}
              </h3>

              {result.permitted ? (
                <>
                  <p className="text-sm text-gray-700 mb-3">
                    {result.summary}
                  </p>

                  {result.lep_controls?.dev_type_specific?.length > 0 && (
                    <div className="mb-3">
                      <h4 className="font-medium text-sm mb-2">LEP Controls:</h4>
                      {result.lep_controls.dev_type_specific.map((clause: any) => (
                        <div key={clause.clause_number} className="mb-2">
                          <p className="text-sm font-medium">
                            Clause {clause.clause_number}: {clause.clause_title}
                          </p>
                          <ul className="text-sm text-gray-600 ml-4 list-disc">
                            {clause.requirements.map((req: string, i: number) => (
                              <li key={i}>{req}</li>
                            ))}
                          </ul>
                        </div>
                      ))}
                    </div>
                  )}

                  {result.lep_controls?.general && (
                    <div className="mb-3">
                      <h4 className="font-medium text-sm mb-2">General Controls:</h4>
                      <ul className="text-sm text-gray-600 ml-4 list-disc">
                        {result.lep_controls.general.max_height && (
                          <li>Maximum height: {result.lep_controls.general.max_height}m</li>
                        )}
                        {result.lep_controls.general.max_fsr && (
                          <li>Maximum FSR: {result.lep_controls.general.max_fsr}:1</li>
                        )}
                      </ul>
                    </div>
                  )}

                  {result.dcp_sections?.length > 0 && (
                    <div>
                      <h4 className="font-medium text-sm mb-2">DCP Requirements:</h4>
                      <p className="text-sm text-gray-600">
                        {result.dcp_sections.reduce((sum: number, s: any) => sum + s.requirement_count, 0)} requirements across {result.dcp_sections.length} DCP sections
                      </p>
                    </div>
                  )}
                </>
              ) : (
                <>
                  <p className="text-sm text-red-700 mb-3">
                    {result.reason}
                  </p>

                  {result.alternative_options?.length > 0 && (
                    <div>
                      <h4 className="font-medium text-sm mb-2">
                        Alternative development types permitted in {result.zone} zone:
                      </h4>
                      <ul className="text-sm text-gray-600 ml-4 list-disc">
                        {result.alternative_options.slice(0, 5).map((alt: string, i: number) => (
                          <li key={i}>{alt.replace(/_/g, ' ')}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              )}

              <div className="text-xs text-gray-500 mt-3">
                Zone: {result.zone_name} ({result.zone}) • {result.formerCouncil}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
```

---

#### Task 3.2: Integrate into Assessment Page (1 day)

**File:** `frontend-nextjs/app/assessment/page.tsx`

```typescript
// Add import
import { PermissibilityChecker } from '@/components/compliance/PermissibilityChecker';

// Add before ComplianceDashboard
{propertyData && (
  <PermissibilityChecker propertyAddress={propertyData.address} />
)}

<ComplianceDashboard
  address={propertyData.address}
  zone={propertyData.zoneDescription}
  // ... rest of props
/>
```

---

### Phase 4: Testing & Refinement (Week 4)

#### Task 4.1: Test All Dev Types (2 days)

**Test Matrix:**

| Dev Type | R2 Zone | B2 Zone | E1 Zone | Expected Result |
|----------|---------|---------|---------|-----------------|
| Secondary dwelling | ✅ Permitted | ❌ Prohibited | ❌ Prohibited | Correct |
| Dual occupancy | ⚠️ Permissible | ❌ Prohibited | ❌ Prohibited | Correct |
| Shop top housing | ❌ Prohibited | ✅ Permitted | ✅ Permitted | Correct |
| Residential flat | ❌ Prohibited | ⚠️ Permissible | ✅ Permitted | Correct |

**Test Addresses:**
- **R2 Zone:** 181 Addison Road, Ashfield
- **B2 Zone:** 1 Marrickville Road, Marrickville
- **E1 Zone:** 260 Liverpool Road, Ashfield
- **R3 Zone:** 40 Lackey Street, Marrickville

**Success Criteria:**
- 100% correct permissibility determination
- LEP controls shown for permitted types
- Alternative options shown for prohibited types

---

#### Task 4.2: Edge Case Handling (2 days)

**Edge Cases to Handle:**

1. **Property not found in Planning Portal**
   - Fallback: Manual zone selection

2. **Dev type not in LEP Land Use Table**
   - Show: "Development type not found in LEP, manual assessment required"

3. **Multiple zones on one property**
   - Show: "Property spans multiple zones, permissibility varies"

4. **Heritage overlay affects permissibility**
   - Show: "Heritage controls may apply (see heritage requirements)"

5. **Transitional provisions (Ashfield/Marrickville/Leichhardt legacy zones)**
   - Map E1 → B2, E2 → B4 (already handled in zone translation)

---

## Testing Plan

### Unit Tests
```typescript
// File: __tests__/permissibility.test.ts

describe('Permissibility Checker', () => {
  test('Secondary dwelling permitted in R2', async () => {
    const result = await checkPermissibility({
      address: '181 Addison Road, Ashfield',
      developmentType: 'secondary_dwelling'
    });

    expect(result.permitted).toBe(true);
    expect(result.zone).toBe('R2');
    expect(result.lep_controls.dev_type_specific).toContainEqual(
      expect.objectContaining({
        clause_number: '5.4'
      })
    );
  });

  test('Shop top housing prohibited in R2', async () => {
    const result = await checkPermissibility({
      address: '181 Addison Road, Ashfield',
      developmentType: 'shop_top_housing'
    });

    expect(result.permitted).toBe(false);
    expect(result.reason).toContain('prohibited');
    expect(result.alternative_options.length).toBeGreaterThan(0);
  });
});
```

### Integration Tests
```bash
# Test full user flow
1. Enter address: "181 Addison Road, Ashfield"
2. Select dev type: "Granny Flat / Secondary Dwelling"
3. Click "Check Permissibility"
4. Verify: ✅ YES - PERMITTED shown
5. Verify: LEP Clause 5.4 controls displayed
6. Verify: DCP requirements count shown
```

---

## Deliverables

### Code
- ✅ `extract_lep_land_use_tables.py` - LEP data extraction
- ✅ `extract_lep_dev_type_clauses.py` - Dev-type clause extraction
- ✅ `app/api/permissibility/check/route.ts` - API endpoint
- ✅ `components/compliance/PermissibilityChecker.tsx` - UI component
- ✅ `development-type-mappings.json` - Updated mappings

### Database
- ✅ `lep_land_use_table` - LEP Land Use Table data
- ✅ `lep_development_type_clauses` - Dev-type-specific LEP clauses

### Documentation
- ✅ This file: Implementation plan
- ✅ API documentation
- ✅ Testing guide

---

## Success Metrics

**Functional:**
- 100% correct permissibility determination for test cases
- <500ms API response time
- LEP controls displayed for permitted types
- Alternative options shown for prohibited types

**User Experience:**
- Simple 2-step flow (select dev type → click button)
- Clear YES/NO answer
- LEP clause references for citation in DA
- Integration with existing assessment page

**Professional Value:**
- Answer the FIRST question professionals ask
- Foundation for showing only relevant compliance requirements
- Prevent wasted effort on unpermitted development

---

## Dependencies

**Data Sources:**
- ✅ Inner West LEP 2022 (already have PDF)
- ✅ NSW Planning Portal API (already integrated)
- ✅ Former council mapping (already implemented)

**Technical:**
- ✅ Database (PostgreSQL already set up)
- ✅ API framework (Next.js already set up)
- ✅ UI components (already have design system)

**No blockers - ready to start immediately.**

---

## Time Estimate Breakdown

| Task | Effort | Notes |
|------|--------|-------|
| Extract LEP Land Use Tables | 3-4 days | Manual extraction from LEP PDF + script |
| Extract Dev-Type Clauses | 2-3 days | LLM-based extraction from Part 5 |
| Update Dev Type Mappings | 1 day | Correct LEP terminology |
| Create API Endpoint | 2-3 days | Permissibility logic + LEP queries |
| Create UI Component | 3-4 days | Dropdown + results display |
| Integration | 1 day | Add to assessment page |
| Testing | 4 days | Unit + integration tests |
| **Total** | **16-20 days** | **~3-4 weeks** |

---

## Next Steps

**Day 1-2:**
1. Open Inner West LEP 2022 PDF
2. Navigate to Schedule 1 (Land Use Table)
3. Manually extract complete Land Use Table for all zones
4. Create `LAND_USE_TABLE` dictionary in `extract_lep_land_use_tables.py`
5. Run extraction script

**Day 3-4:**
1. Extract Part 5 from Inner West LEP 2022 (if not already done with MinerU)
2. Run `extract_lep_dev_type_clauses.py` with LLM extraction
3. Verify dev-type-specific clauses extracted correctly

**Day 5-10:**
1. Implement API endpoint
2. Create UI component
3. Integrate into assessment page

**Day 11-16:**
1. Test all dev types
2. Handle edge cases
3. Polish UI/UX

**Day 17-20:**
1. Buffer for issues
2. Documentation
3. Deploy

---

**Status:** Ready to start. No blockers. Heritage Intelligence safely paused.
