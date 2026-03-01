# LightRAG Implementation - Streamlined (No Upfront Validation)
**Date:** 2025-10-23
**Purpose:** Most efficient path to working categorized requirements

---

## Key Decision: Validation UI Later

**Current approach:**
- ✅ Process all 56 batches now
- ✅ Store with confidence levels and source tracking
- ✅ Display categorized requirements in production
- ⏳ Build validation UI for expert review later
- ⏳ Expert validates incrementally as they have time

**Benefits:**
- Faster implementation (1-2 weeks vs 4 weeks)
- User sees value immediately
- Can iterate based on real usage
- Expert validates real-world problem cases first

---

## Streamlined Implementation (2 Weeks)

### Week 1: Database + Processing

**Day 1-2: Database Schema**

```sql
-- Single table for all categorized requirements
CREATE TABLE dcp_categorized_requirements (
  id SERIAL PRIMARY KEY,

  -- Scope
  lga TEXT NOT NULL,
  dcp_section TEXT NOT NULL,        -- 'Part_2', 'Part_4.1', 'Part_4.2', etc.
  precinct_id TEXT,                 -- NULL for base sections, populated for precincts

  -- Categorized requirement
  category TEXT NOT NULL,            -- 'setback_front', 'parking', 'landscaping', etc.
  subcategory TEXT,                 -- 'front', 'side', 'rear' (for setbacks)
  requirement_text TEXT NOT NULL,
  value_numeric NUMERIC,
  unit TEXT,                        -- 'm', '%', 'spaces', 'storeys'

  -- Source tracking (CRITICAL)
  source_provision_ids INTEGER[] NOT NULL,
  source_documents TEXT[],

  -- Quality indicators
  confidence TEXT CHECK (confidence IN ('high', 'medium', 'low')),
  has_conditions BOOLEAN DEFAULT false,
  condition_text TEXT,

  -- For validation UI later
  validated BOOLEAN DEFAULT false,
  validation_notes TEXT,
  validated_by TEXT,
  validated_at TIMESTAMP,

  -- Metadata
  created_at TIMESTAMP DEFAULT NOW(),
  processing_version TEXT DEFAULT '1.0'
);

-- Indexes for fast querying
CREATE INDEX idx_dcp_cat_req_lookup ON dcp_categorized_requirements(lga, dcp_section);
CREATE INDEX idx_dcp_cat_req_precinct ON dcp_categorized_requirements(precinct_id) WHERE precinct_id IS NOT NULL;
CREATE INDEX idx_dcp_cat_req_category ON dcp_categorized_requirements(category);
CREATE INDEX idx_dcp_cat_req_validated ON dcp_categorized_requirements(validated);

-- View for runtime queries
CREATE VIEW dcp_requirements_by_devtype AS
SELECT
  r.*,
  -- Map to development types at query time
  CASE
    WHEN r.dcp_section IN ('Part_2', 'Part_4.1') THEN ARRAY['dwelling_house', 'secondary_dwelling', 'dual_occupancy']
    WHEN r.dcp_section IN ('Part_2', 'Part_4.2') THEN ARRAY['multi_dwelling', 'residential_flat']
    WHEN r.dcp_section IN ('Part_2', 'Part_4.3') THEN ARRAY['shop_top_housing', 'boarding_house']
    WHEN r.dcp_section IN ('Part_2', 'Part_5') THEN ARRAY['commercial', 'child_care', 'industrial']
    ELSE ARRAY['unknown']
  END as applicable_dev_types
FROM dcp_categorized_requirements r;
```

**Day 3-4: LightRAG Processing Script**

```python
# process_dcp_with_lightrag.py
"""
Process all DCP sections with LightRAG categorization
"""
import psycopg2
import os
from dotenv import load_dotenv
from lightrag import LightRAG
import json
from typing import List, Dict

load_dotenv()

# LightRAG setup
rag = LightRAG(
    working_dir="./lightrag_cache",
    llm_model="gpt-4-turbo",
    embedding_model="text-embedding-3-large"
)

# Database connection
conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD')
)

# Define processing batches
BATCHES = [
    # Marrickville
    ('Marrickville', 'Part_2', 'Marrickville.*_2_'),
    ('Marrickville', 'Part_4.1', 'Marrickville.*4\\.1'),
    ('Marrickville', 'Part_4.2', 'Marrickville.*4\\.2'),
    ('Marrickville', 'Part_4.3', 'Marrickville.*4\\.3'),
    ('Marrickville', 'Part_5', 'Marrickville.*_5'),

    # Ashfield
    ('Ashfield', 'Part_2', 'Ashfield.*_2_'),
    ('Ashfield', 'Part_4.1', 'Ashfield.*4\\.1'),
    ('Ashfield', 'Part_4.2', 'Ashfield.*4\\.2'),
    ('Ashfield', 'Part_4.3', 'Ashfield.*4\\.3'),
    ('Ashfield', 'Part_5', 'Ashfield.*_5'),

    # Leichhardt
    ('Leichhardt', 'Part_2', 'Leichhardt.*_2_'),
    ('Leichhardt', 'Part_4.1', 'Leichhardt.*4\\.1'),
    ('Leichhardt', 'Part_4.2', 'Leichhardt.*4\\.2'),
    ('Leichhardt', 'Part_4.3', 'Leichhardt.*4\\.3'),
    ('Leichhardt', 'Part_5', 'Leichhardt.*_5'),
]

def get_provisions_for_section(lga: str, section: str, doc_pattern: str) -> List[Dict]:
    """Fetch all provisions for a DCP section"""
    cur = conn.cursor()
    cur.execute("""
        SELECT
            rp.id,
            rp.provision_text,
            rp.ref_number,
            rp.section_header,
            rp.document_id
        FROM regulatory_provisions rp
        JOIN documents d ON d.id = rp.document_id
        WHERE d.document_type = 'DCP'
        AND rp.document_id ~ %s
        ORDER BY rp.pdf_page, rp.id
    """, [doc_pattern])

    provisions = []
    for row in cur.fetchall():
        provisions.append({
            'id': row[0],
            'text': row[1],
            'ref_number': row[2],
            'section_header': row[3],
            'document_id': row[4]
        })

    cur.close()
    return provisions

def categorize_provisions(lga: str, section: str, provisions: List[Dict]) -> List[Dict]:
    """Use LightRAG to categorize provisions into requirements"""

    # Build prompt
    provision_text = "\n\n".join([
        f"[Provision {p['id']}] {p['section_header']}\n{p['text']}"
        for p in provisions
    ])

    prompt = f"""
You are analyzing DCP (Development Control Plan) provisions from {lga} {section}.

Extract structured planning requirements from these provisions and categorize them.

Categories:
- setback_front: Front setbacks (include numeric value in metres)
- setback_side: Side setbacks (include numeric value in metres)
- setback_rear: Rear setbacks (include numeric value in metres)
- landscaping_front: Front landscaping (include % of site area)
- landscaping_deep_soil: Deep soil requirements (include % of site area)
- parking: Parking space requirements (include numeric value)
- height: Height controls (include numeric value in metres or storeys)
- fsr: Floor space ratio (include numeric ratio)
- privacy: Privacy requirements
- solar_access: Solar access requirements
- design_character: Design and character requirements
- materials: Materials and finishes requirements
- stormwater: Stormwater requirements
- tree_preservation: Tree preservation requirements
- waste: Waste management requirements
- other: Any other requirements

For each requirement you extract, provide:
1. category: One of the categories above
2. subcategory: More specific category (e.g., for setback: 'front', 'side', 'rear')
3. requirement_text: Clear, concise statement of the requirement
4. value_numeric: Extract any numeric value (e.g., 5.5 from "5.5m setback")
5. unit: Unit of measurement (e.g., "m", "%", "spaces", "storeys")
6. source_provision_ids: Array of provision IDs this requirement is based on
7. has_conditions: true if the requirement has conditions (e.g., "except where...", "unless...")
8. condition_text: The condition text if has_conditions is true
9. confidence: 'high' (clear and explicit), 'medium' (somewhat ambiguous), 'low' (unclear)

PROVISIONS:
{provision_text}

Return ONLY a valid JSON array of requirements. Example:
[
  {{
    "category": "setback_front",
    "subcategory": "front",
    "requirement_text": "Front setback: 5.5 metres minimum",
    "value_numeric": 5.5,
    "unit": "m",
    "source_provision_ids": [12345],
    "has_conditions": false,
    "condition_text": null,
    "confidence": "high"
  }},
  {{
    "category": "parking",
    "subcategory": "dwelling_house",
    "requirement_text": "Dwelling house: 1 car parking space minimum",
    "value_numeric": 1,
    "unit": "spaces",
    "source_provision_ids": [12346],
    "has_conditions": true,
    "condition_text": "unless site area is less than 300m²",
    "confidence": "high"
  }}
]
"""

    # Query LightRAG
    response = rag.query(prompt, mode="naive")

    # Parse JSON response
    try:
        # Extract JSON from response (LightRAG may return markdown code blocks)
        json_start = response.find('[')
        json_end = response.rfind(']') + 1
        json_str = response[json_start:json_end]

        requirements = json.loads(json_str)
        return requirements
    except Exception as e:
        print(f"ERROR parsing LightRAG response: {e}")
        print(f"Response: {response[:500]}")
        return []

def store_requirements(lga: str, section: str, requirements: List[Dict]):
    """Store categorized requirements in database"""
    cur = conn.cursor()

    for req in requirements:
        cur.execute("""
            INSERT INTO dcp_categorized_requirements (
                lga,
                dcp_section,
                category,
                subcategory,
                requirement_text,
                value_numeric,
                unit,
                source_provision_ids,
                source_documents,
                confidence,
                has_conditions,
                condition_text
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """, [
            lga,
            section,
            req['category'],
            req.get('subcategory'),
            req['requirement_text'],
            req.get('value_numeric'),
            req.get('unit'),
            req['source_provision_ids'],
            [req.get('source_documents', [])],  # Will extract from provision_ids
            req['confidence'],
            req.get('has_conditions', False),
            req.get('condition_text')
        ])

    conn.commit()
    cur.close()
    print(f"✅ Stored {len(requirements)} requirements for {lga} {section}")

def main():
    print("=" * 80)
    print("LIGHTRAG DCP CATEGORIZATION - STREAMLINED")
    print("=" * 80)

    total_processed = 0
    total_requirements = 0

    for i, (lga, section, doc_pattern) in enumerate(BATCHES, 1):
        print(f"\n[{i}/{len(BATCHES)}] Processing {lga} {section}...")

        # Get provisions
        provisions = get_provisions_for_section(lga, section, doc_pattern)
        print(f"   Found {len(provisions)} provisions")

        if len(provisions) == 0:
            print(f"   ⚠️ No provisions found - skipping")
            continue

        # Categorize with LightRAG
        print(f"   Categorizing with LightRAG...")
        requirements = categorize_provisions(lga, section, provisions)
        print(f"   Extracted {len(requirements)} requirements")

        # Store in database
        store_requirements(lga, section, requirements)

        total_processed += len(provisions)
        total_requirements += len(requirements)

    print("\n" + "=" * 80)
    print("PROCESSING COMPLETE")
    print("=" * 80)
    print(f"Total provisions processed: {total_processed}")
    print(f"Total requirements extracted: {total_requirements}")
    print(f"Reduction: {total_processed} → {total_requirements} ({100 - (total_requirements/total_processed*100):.1f}% reduction)")
    print("=" * 80)

if __name__ == '__main__':
    main()
```

**Day 5: Process Precincts**

```python
# process_precincts.py
"""
Process precinct provisions (already in dcp_precinct_provisions table)
"""
# Similar to above, but query from dcp_precinct_provisions
# Process 41 Marrickville precincts
# Store in same table with precinct_id populated
```

**Day 6-7: Run Processing + Monitor**

```bash
# Process all DCP sections (15 batches)
python process_dcp_with_lightrag.py

# Process precincts (41 batches)
python process_precincts.py

# Total: 56 batches
# Estimated time: 2-3 hours
# Estimated cost: $1-2
```

---

### Week 2: API + UI Integration

**Day 8-9: API Endpoint**

```typescript
// frontend-nextjs/app/api/compliance/categorized-requirements/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/db';

interface CategorizedRequirementsRequest {
  lga: string;
  developmentType: string;
  precinctId?: string;
}

export async function POST(request: NextRequest) {
  const { lga, developmentType, precinctId } = await request.json();

  // Map dev type to DCP sections
  const devTypeToSections: Record<string, string[]> = {
    'dwelling_house': ['Part_2', 'Part_4.1'],
    'secondary_dwelling': ['Part_2', 'Part_4.1'],
    'dual_occupancy': ['Part_2', 'Part_4.1'],
    'multi_dwelling': ['Part_2', 'Part_4.2'],
    'residential_flat': ['Part_2', 'Part_4.2'],
    'shop_top_housing': ['Part_2', 'Part_4.3'],
    'boarding_house': ['Part_2', 'Part_4.3'],
    'commercial': ['Part_2', 'Part_5'],
    'child_care': ['Part_2', 'Part_5'],
  };

  const sections = devTypeToSections[developmentType] || ['Part_2'];

  // Query base requirements
  const baseRequirements = await query(`
    SELECT
      id,
      category,
      subcategory,
      requirement_text,
      value_numeric,
      unit,
      source_provision_ids,
      confidence,
      has_conditions,
      condition_text
    FROM dcp_categorized_requirements
    WHERE lga = $1
    AND dcp_section = ANY($2)
    AND precinct_id IS NULL
    ORDER BY
      CASE category
        WHEN 'setback_front' THEN 1
        WHEN 'setback_side' THEN 2
        WHEN 'setback_rear' THEN 3
        WHEN 'parking' THEN 4
        WHEN 'landscaping_front' THEN 5
        ELSE 10
      END,
      id
  `, [lga, sections]);

  // Query precinct requirements if applicable
  let precinctRequirements = [];
  if (precinctId) {
    const result = await query(`
      SELECT
        id,
        category,
        subcategory,
        requirement_text,
        value_numeric,
        unit,
        source_provision_ids,
        confidence,
        has_conditions,
        condition_text
      FROM dcp_categorized_requirements
      WHERE precinct_id = $1
      ORDER BY category, id
    `, [precinctId]);

    precinctRequirements = result.rows;
  }

  // Group by category
  const groupedBase = groupByCategory(baseRequirements.rows);
  const groupedPrecinct = groupByCategory(precinctRequirements);

  return NextResponse.json({
    success: true,
    data: {
      base: groupedBase,
      precinct: groupedPrecinct,
      totalCount: baseRequirements.rows.length + precinctRequirements.length
    }
  });
}

function groupByCategory(requirements: any[]) {
  const grouped: Record<string, any[]> = {};

  for (const req of requirements) {
    const category = req.category;
    if (!grouped[category]) {
      grouped[category] = [];
    }
    grouped[category].push(req);
  }

  return grouped;
}
```

**Day 10-11: UI Component**

```tsx
// frontend-nextjs/components/compliance/CategorizedRequirements.tsx
'use client';

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ChevronDown, ChevronRight, ExternalLink } from 'lucide-react';

interface Requirement {
  id: number;
  category: string;
  subcategory?: string;
  requirement_text: string;
  value_numeric?: number;
  unit?: string;
  source_provision_ids: number[];
  confidence: 'high' | 'medium' | 'low';
  has_conditions: boolean;
  condition_text?: string;
}

interface CategorizedRequirementsProps {
  baseRequirements: Record<string, Requirement[]>;
  precinctRequirements?: Record<string, Requirement[]>;
  onViewSource?: (provisionIds: number[]) => void;
}

const CATEGORY_LABELS: Record<string, string> = {
  'setback_front': '🏠 Front Setback',
  'setback_side': '🏠 Side Setback',
  'setback_rear': '🏠 Rear Setback',
  'parking': '🅿️ Parking',
  'landscaping_front': '🌳 Front Landscaping',
  'landscaping_deep_soil': '🌳 Deep Soil',
  'height': '📏 Height',
  'privacy': '🔒 Privacy',
  'solar_access': '☀️ Solar Access',
  'design_character': '🎨 Design & Character',
};

export function CategorizedRequirements({
  baseRequirements,
  precinctRequirements,
  onViewSource
}: CategorizedRequirementsProps) {
  const [expandedCategories, setExpandedCategories] = React.useState<Set<string>>(
    new Set(Object.keys(baseRequirements))
  );

  const toggleCategory = (category: string) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(category)) {
      newExpanded.delete(category);
    } else {
      newExpanded.add(category);
    }
    setExpandedCategories(newExpanded);
  };

  return (
    <div className="space-y-4">
      {/* Base Requirements */}
      <Card>
        <CardHeader>
          <CardTitle>DCP Requirements (Categorized)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {Object.entries(baseRequirements).map(([category, requirements]) => (
              <div key={category} className="border rounded-lg">
                {/* Category Header */}
                <button
                  onClick={() => toggleCategory(category)}
                  className="w-full flex items-center justify-between p-3 hover:bg-gray-50"
                >
                  <div className="flex items-center gap-2">
                    {expandedCategories.has(category) ? (
                      <ChevronDown className="w-4 h-4" />
                    ) : (
                      <ChevronRight className="w-4 h-4" />
                    )}
                    <span className="font-medium">
                      {CATEGORY_LABELS[category] || category}
                    </span>
                    <Badge variant="secondary">{requirements.length}</Badge>
                  </div>
                </button>

                {/* Category Requirements */}
                {expandedCategories.has(category) && (
                  <div className="p-3 pt-0 space-y-2">
                    {requirements.map((req) => (
                      <div
                        key={req.id}
                        className="flex items-start justify-between p-2 bg-gray-50 rounded"
                      >
                        <div className="flex-1">
                          <p className="text-sm">{req.requirement_text}</p>

                          {req.has_conditions && req.condition_text && (
                            <p className="text-xs text-amber-600 mt-1">
                              ⚠️ Condition: {req.condition_text}
                            </p>
                          )}

                          <div className="flex items-center gap-2 mt-1">
                            <Badge variant={
                              req.confidence === 'high' ? 'default' :
                              req.confidence === 'medium' ? 'secondary' : 'outline'
                            } className="text-xs">
                              {req.confidence} confidence
                            </Badge>
                          </div>
                        </div>

                        <button
                          onClick={() => onViewSource?.(req.source_provision_ids)}
                          className="ml-2 text-blue-600 hover:text-blue-800"
                          title="View source provision"
                        >
                          <ExternalLink className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Precinct Requirements */}
      {precinctRequirements && Object.keys(precinctRequirements).length > 0 && (
        <Card className="border-green-200">
          <CardHeader>
            <CardTitle className="text-green-700">
              📍 Precinct-Specific Requirements
            </CardTitle>
          </CardHeader>
          <CardContent>
            {/* Similar structure to base requirements */}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
```

**Day 12: Integration**

```tsx
// Update ComplianceDashboard.tsx to use CategorizedRequirements
// Add toggle: "Categorized View" vs "Raw Provisions"
```

**Day 13-14: Testing + Refinement**

- Test with 20+ different addresses
- Verify categories make sense
- Verify source links work
- Fix any data quality issues

---

## Conservative Fallback Strategy

```typescript
// If insufficient categorized requirements, show raw provisions
const requirements = await getCategorizedRequirements(lga, devType, precinctId);

if (requirements.totalCount < 5) {
  // Fall back to raw provisions browser
  return <DCPProvisionsBrowser lga={lga} zone={zone} devType={devType} />;
}

// Otherwise, show categorized requirements
return <CategorizedRequirements {...requirements} />;
```

---

## Validation UI (Build Later - Week 3+)

When you have access to an expert:

```tsx
// frontend-nextjs/app/admin/validate-requirements/page.tsx
'use client';

// Shows all requirements grouped by confidence
// Expert can:
// - Mark as "correct" / "incorrect" / "needs refinement"
// - Add notes
// - Edit requirement text
// - Update confidence level

// Filters:
// - Show only unvalidated
// - Show by confidence level
// - Show by category
// - Show by LGA
```

---

## Summary: Most Efficient Path

### Week 1 (Database + Processing)
1. ✅ Create `dcp_categorized_requirements` table (1 day)
2. ✅ Write `process_dcp_with_lightrag.py` script (2 days)
3. ✅ Run processing on all 56 batches (1 day)
4. ✅ QA spot check results (1 day)

### Week 2 (API + UI)
1. ✅ Create API endpoint `/api/compliance/categorized-requirements` (2 days)
2. ✅ Build `CategorizedRequirements.tsx` component (2 days)
3. ✅ Integrate into `ComplianceDashboard.tsx` (1 day)
4. ✅ Test with real addresses (2 days)

### Week 3+ (Validation UI - When Expert Available)
1. ⏳ Build admin validation interface
2. ⏳ Expert validates incrementally
3. ⏳ Iterate based on feedback

**Total time to working prototype: 2 weeks**
**Total cost: ~$1-2 for LLM processing**

---

## Key Advantages of This Approach

1. **No bottleneck**: Don't wait for expert availability
2. **Fast feedback**: Users see categorized requirements immediately
3. **Real validation**: Expert validates based on real usage patterns
4. **Iterative improvement**: Can refine categories based on user needs
5. **Low risk**: Conservative fallback to raw provisions if needed
6. **Full traceability**: Every requirement links to source provision

---

## Next Step

Ready to start? I can:
1. ✅ Create the database schema
2. ✅ Write the LightRAG processing script
3. ✅ Process a single test batch (Marrickville Part_2) to verify approach
4. ✅ Review results together before processing all batches

Which would you like to do first?
