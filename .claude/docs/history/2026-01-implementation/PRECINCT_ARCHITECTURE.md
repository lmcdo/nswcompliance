# Precinct Architecture Implementation Plan

## Executive Summary

**Problem:** 383 precinct provisions (15 precincts) exist in database but aren't accessible to users
**Current State:** Precinct matching code exists, returns 0 provisions (queries wrong table)
**Solution:** Simple table structure + API integration + UI display (non-breaking, phased rollout)

## 1. Database Architecture

### Table Structure (Simple, Not SEPP-style)

```sql
-- Core precinct provisions table
CREATE TABLE dcp_precinct_provisions (
    id SERIAL PRIMARY KEY,
    precinct_id TEXT NOT NULL,                    -- '9_29'
    precinct_name TEXT NOT NULL,                  -- 'South Western Marrickville'
    lga TEXT NOT NULL,                            -- 'Inner West' or 'Marrickville'
    provision_text TEXT NOT NULL,
    provision_type TEXT,                          -- 'objective', 'control', 'guideline'
    ref_number TEXT,                              -- '9.29.1', '9.29.2'
    section_header TEXT,                          -- 'Desired future character'
    parent_provision_id INTEGER REFERENCES regulatory_provisions(id),
    pdf_page INTEGER,
    display_order INTEGER DEFAULT 999,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for fast queries
CREATE INDEX idx_precinct_prov_lookup ON dcp_precinct_provisions(lga, precinct_id);
CREATE INDEX idx_precinct_prov_parent ON dcp_precinct_provisions(parent_provision_id);
CREATE INDEX idx_precinct_prov_type ON dcp_precinct_provisions(provision_type);

-- Precinct metadata table (optional enhancement)
CREATE TABLE dcp_precinct_metadata (
    id SERIAL PRIMARY KEY,
    precinct_id TEXT NOT NULL UNIQUE,             -- '9_29'
    precinct_name TEXT NOT NULL,                  -- 'South Western Marrickville'
    lga TEXT NOT NULL,
    description TEXT,                             -- 'Established residential area...'
    desired_character TEXT,                       -- Extract from Part 9 introduction
    boundary_streets TEXT[],                      -- ['Illawarra Road', 'Hill Street', ...]
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Why NOT Use SEPP Pattern?

| Aspect | SEPP | Precinct | Decision |
|--------|------|----------|----------|
| **Volume** | 2 rows | 383 provisions (15 precincts) | Too many for manual JSONB curation |
| **Nature** | Pass/fail compliance | Contextual guidance (83% qualitative) | Users need full text, not structured fields |
| **Complexity** | Nested JSONB (categories → requirements → standards) | Simple text provisions | Flat table sufficient |
| **User Need** | "Does this comply?" | "What local controls apply?" | Display text, not compute compliance |

### Data Migration

```sql
-- Populate from regulatory_provisions
INSERT INTO dcp_precinct_provisions (
    precinct_id,
    precinct_name,
    lga,
    provision_text,
    provision_type,
    ref_number,
    section_header,
    parent_provision_id,
    pdf_page
)
SELECT
    (regexp_match(document_id, '9_([0-9_]+)'))[1] as precinct_id,
    -- Extract precinct name from document_id
    regexp_replace(
        regexp_replace(document_id, '^.*9_[0-9_]+_', ''),
        '_', ' ', 'g'
    ) as precinct_name,
    CASE
        WHEN document_id ~ 'Marrickville' THEN 'Inner West'
        WHEN document_id ~ 'Ashfield' THEN 'Inner West'
        WHEN document_id ~ 'Leichhardt' THEN 'Inner West'
        ELSE 'Unknown'
    END as lga,
    provision_text,
    provision_type,
    ref_number,
    section_header,
    id as parent_provision_id,
    pdf_page
FROM regulatory_provisions_canonical
WHERE document_id ~ '9_[0-9]+'
AND provision_text IS NOT NULL
AND LENGTH(provision_text) > 20;  -- Filter out empty/TOC entries
```

**Result:** ~230 clean precinct provisions (filtered from 383 raw)

## 2. API Integration

### 2.1 DCP Provisions API Enhancement

**File:** `frontend-nextjs/app/api/dcp/provisions/route.ts`

**Current Behavior:**
```typescript
// Returns Part 2 + Part 4.X only (241 provisions)
dcpDocumentPatterns = [
  `${lgaSearchPattern}.*_2_`,       // Part 2: General
  `${lgaSearchPattern}.*4\\.1`      // Part 4.1: Low Density
];
```

**Enhanced Behavior (NON-BREAKING):**
```typescript
interface ProvisionsRequest {
  // ... existing fields
  includePrecinct?: boolean;        // NEW: Optional flag (default: false)
  precinctId?: string;              // NEW: Optional precinct filter
}

// Inside route handler:
const includePrecinct = body.includePrecinct ?? false;

// Existing query (unchanged)
const baseProvisions = await queryBaseProvisions(...);

// NEW: Optional precinct supplement
let precinctProvisions = [];
if (includePrecinct && address) {
  const precinct = await getPrecinctForAddress(address, targetLGA);
  if (precinct) {
    precinctProvisions = await queryPrecinctProvisions(precinct.precinctId, lga);
  }
}

return {
  success: true,
  data: {
    base: baseProvisions,              // Part 2 + 4.X (always returned)
    precinct: precinctProvisions,      // Part 9 (optional, address-specific)
    totalCount: baseProvisions.length + precinctProvisions.length,
    precinctInfo: precinct || null     // Precinct metadata
  }
};
```

**New Helper Function:**
```typescript
async function queryPrecinctProvisions(
  precinctId: string,
  lga: string
): Promise<ProvisionResult[]> {
  const query = `
    SELECT
      pp.id,
      pp.ref_number,
      pp.section_header,
      pp.provision_text,
      pp.precinct_name,
      pp.provision_type,
      rpc.document_id,
      rpc.pdf_page,
      rpc.pdf_page_image_url
    FROM dcp_precinct_provisions pp
    JOIN regulatory_provisions_canonical rpc ON pp.parent_provision_id = rpc.id
    WHERE pp.precinct_id = $1
      AND pp.lga = $2
    ORDER BY pp.display_order ASC, pp.ref_number ASC
    LIMIT 50
  `;

  const result = await query(query, [precinctId, lga]);
  return result.rows;
}
```

### 2.2 Constraints API (Already Has Precinct Code)

**File:** `frontend-nextjs/app/api/compliance/constraints/route.ts`

**Fix:** Update `getPrecinctControls()` to query new table instead of `development_controls`

```typescript
// BEFORE (returns 0 - wrong table)
const query = `
  FROM development_controls dc
  JOIN regulatory_provisions_canonical rp ON dc.provision_id = rp.id
  WHERE rp.document_id LIKE '%' || $1 || '%'
`;

// AFTER (returns precinct provisions)
const query = `
  SELECT
    pp.provision_text,
    pp.ref_number,
    pp.section_header,
    pp.precinct_name,
    pp.provision_type
  FROM dcp_precinct_provisions pp
  WHERE pp.precinct_id = $1
    AND pp.lga = $2
  ORDER BY pp.display_order ASC
`;
```

## 3. UI Integration

### 3.1 Display Strategy

**Option A: Separate Section (Recommended)**

Add new collapsible section in `ComplianceDashboard`:

```
┌─ Building Envelope Controls ─────────────┐
│ Height: 9.5m                             │
│ FSR: 0.5:1                               │
└──────────────────────────────────────────┘

┌─ DCP Provisions (241) ───────────────────┐  ← Existing
│ Part 2 (General) + Part 4.1 (Low Density)│
│ [Search/Filter controls]                  │
└──────────────────────────────────────────┘

┌─ Precinct Controls (15) ─────────────────┐  ← NEW
│ Precinct 9.29: South Western Marrickville│
│ [Provisions specific to this location]    │
└──────────────────────────────────────────┘
```

**Option B: Integrated Display**

Merge into existing DCP browser with badge:

```
DCP Provisions (256 total)
  📍 15 precinct-specific provisions
  📋 241 general provisions
```

**Recommendation:** Option A (clearer separation of base vs local controls)

### 3.2 Component Structure

**New Component:** `PrecinctProvisionsBrowser.tsx`

```typescript
interface PrecinctProvisionsBrowserProps {
  lga: string;
  address: string;                    // Required for precinct matching
  onViewProvision: (provision: ProvisionResult) => void;
}

export function PrecinctProvisionsBrowser({
  lga,
  address,
  onViewProvision
}: PrecinctProvisionsBrowserProps) {
  const [precinct, setPrecinct] = useState<PrecinctInfo | null>(null);
  const [provisions, setProvisions] = useState<PrecinctProvision[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 1. Match address to precinct
    fetch('/api/precinct/match', {
      method: 'POST',
      body: JSON.stringify({ address, lga })
    })
      .then(res => res.json())
      .then(data => {
        setPrecinct(data.precinct);
        if (data.precinct) {
          // 2. Fetch precinct provisions
          return fetch('/api/precinct/provisions', {
            method: 'POST',
            body: JSON.stringify({
              precinctId: data.precinct.precinctId,
              lga
            })
          });
        }
      })
      .then(res => res?.json())
      .then(data => {
        setProvisions(data?.provisions || []);
        setLoading(false);
      });
  }, [address, lga]);

  if (loading) return <div>Checking precinct...</div>;
  if (!precinct) return <div>No precinct controls apply</div>;

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          Precinct {precinct.precinctNumber}: {precinct.precinctName}
        </CardTitle>
        <p className="text-sm text-gray-600">
          {provisions.length} location-specific controls
        </p>
      </CardHeader>
      <CardContent>
        {provisions.map(provision => (
          <div key={provision.id} className="border-b py-3">
            <Badge variant="outline">{provision.ref_number}</Badge>
            <h4 className="font-semibold mt-1">{provision.section_header}</h4>
            <p className="text-sm mt-1">
              {provision.provision_text.slice(0, 200)}...
            </p>
            <Button
              variant="link"
              onClick={() => onViewProvision(provision)}
            >
              View Full Text
            </Button>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
```

### 3.3 Integration into ComplianceDashboard

**File:** `frontend-nextjs/components/compliance/ComplianceDashboard.tsx`

```typescript
import { PrecinctProvisionsBrowser } from './PrecinctProvisionsBrowser';

export function ComplianceDashboard({ propertyData, ... }) {
  // ... existing state

  return (
    <div className={className}>
      {/* Existing sections... */}

      {/* DCP Provisions Browser (existing) */}
      <DCPProvisionsBrowser
        lga={propertyData.council}
        zone={propertyData.constraints?.zone || ''}
        developmentType={developmentType}
        address={propertyData.address}
        onViewProvision={handleViewProvision}
      />

      {/* NEW: Precinct Provisions (only if address available) */}
      {propertyData.address && (
        <PrecinctProvisionsBrowser
          lga={propertyData.council}
          address={propertyData.address}
          onViewProvision={handleViewProvision}
        />
      )}
    </div>
  );
}
```

## 4. Precinct Service Enhancement

**File:** `frontend-nextjs/lib/precinct-service.ts`

### Current Status
- ✅ Street-to-precinct mapping exists (Marrickville only)
- ✅ `getPrecinctForAddress()` works
- ❌ `getPrecinctControls()` queries wrong table (development_controls)

### Fixes Needed

```typescript
// REPLACE existing getPrecinctControls()
export async function getPrecinctProvisions(
  precinctId: string,
  lga: string
): Promise<any[]> {
  try {
    const query = `
      SELECT
        pp.id,
        pp.precinct_id,
        pp.precinct_name,
        pp.provision_text,
        pp.provision_type,
        pp.ref_number,
        pp.section_header,
        pp.pdf_page,
        rpc.document_id,
        rpc.pdf_page_image_url
      FROM dcp_precinct_provisions pp
      JOIN regulatory_provisions_canonical rpc ON pp.parent_provision_id = rpc.id
      WHERE pp.precinct_id = $1
        AND pp.lga = $2
      ORDER BY pp.display_order ASC, pp.ref_number ASC
    `;

    const result = await pool.query(query, [precinctId, lga]);
    return result.rows;
  } catch (error) {
    console.error('[Precinct Service] Error getting provisions:', error);
    return [];
  }
}

// ADD: Precinct metadata helper
export async function getPrecinctMetadata(
  precinctId: string
): Promise<any | null> {
  try {
    const query = `
      SELECT
        precinct_id,
        precinct_name,
        lga,
        description,
        desired_character,
        boundary_streets
      FROM dcp_precinct_metadata
      WHERE precinct_id = $1
    `;

    const result = await pool.query(query, [precinctId]);
    return result.rows[0] || null;
  } catch (error) {
    console.error('[Precinct Service] Error getting metadata:', error);
    return null;
  }
}
```

## 5. New API Routes

### 5.1 Precinct Matching API

**File:** `frontend-nextjs/app/api/precinct/match/route.ts`

```typescript
import { NextRequest, NextResponse } from 'next/server';
import { getPrecinctForAddress } from '@/lib/precinct-service';

export async function POST(request: NextRequest) {
  try {
    const { address, lga } = await request.json();

    if (!address || !lga) {
      return NextResponse.json({
        success: false,
        error: 'address and lga are required'
      }, { status: 400 });
    }

    const precinct = await getPrecinctForAddress(address, lga);

    return NextResponse.json({
      success: true,
      precinct: precinct,
      hasPrecinct: !!precinct
    });
  } catch (error) {
    console.error('[Precinct Match API] Error:', error);
    return NextResponse.json({
      success: false,
      error: 'Internal server error'
    }, { status: 500 });
  }
}
```

### 5.2 Precinct Provisions API

**File:** `frontend-nextjs/app/api/precinct/provisions/route.ts`

```typescript
import { NextRequest, NextResponse } from 'next/server';
import { getPrecinctProvisions } from '@/lib/precinct-service';

export async function POST(request: NextRequest) {
  try {
    const { precinctId, lga } = await request.json();

    if (!precinctId || !lga) {
      return NextResponse.json({
        success: false,
        error: 'precinctId and lga are required'
      }, { status: 400 });
    }

    const provisions = await getPrecinctProvisions(precinctId, lga);

    return NextResponse.json({
      success: true,
      data: {
        provisions,
        count: provisions.length
      }
    });
  } catch (error) {
    console.error('[Precinct Provisions API] Error:', error);
    return NextResponse.json({
      success: false,
      error: 'Internal server error'
    }, { status: 500 });
  }
}
```

## 6. Migration Plan (Phased, Non-Breaking)

### Phase 1: Database Setup (No UI Impact)
- [ ] Create `dcp_precinct_provisions` table
- [ ] Run migration to populate from `regulatory_provisions_canonical`
- [ ] Verify data quality (check sample provisions)
- [ ] Create indexes
- [ ] **Status:** Backend only, no user-facing changes

### Phase 2: API Implementation (Feature Flag)
- [ ] Create `/api/precinct/match` route
- [ ] Create `/api/precinct/provisions` route
- [ ] Update `precinct-service.ts` functions
- [ ] Add `includePrecinct` flag to DCP provisions API
- [ ] Test with Postman/curl
- [ ] **Status:** Available but not consumed by UI

### Phase 3: UI Integration (Opt-in)
- [ ] Create `PrecinctProvisionsBrowser` component
- [ ] Add to `ComplianceDashboard` (initially hidden behind feature flag)
- [ ] Test with known addresses (22 Illawarra Rd, Marrickville)
- [ ] Add environment variable: `NEXT_PUBLIC_ENABLE_PRECINCT_CONTROLS=true`
- [ ] **Status:** Available but opt-in

### Phase 4: Full Release
- [ ] Remove feature flag
- [ ] Update documentation
- [ ] Monitor for errors/performance
- [ ] Add remaining LGAs (Ashfield, Leichhardt)

## 7. Testing Strategy

### 7.1 Database Tests

```sql
-- Verify precinct data exists
SELECT precinct_id, precinct_name, COUNT(*) as provision_count
FROM dcp_precinct_provisions
GROUP BY precinct_id, precinct_name
ORDER BY precinct_id;

-- Expected: 15 precincts, ~15-20 provisions each

-- Test specific precinct
SELECT * FROM dcp_precinct_provisions
WHERE precinct_id = '9_29'
ORDER BY display_order;

-- Verify canonical join
SELECT pp.id, pp.provision_text, rpc.document_id
FROM dcp_precinct_provisions pp
JOIN regulatory_provisions_canonical rpc ON pp.parent_provision_id = rpc.id
WHERE pp.precinct_id = '9_29'
LIMIT 5;
```

### 7.2 API Tests

```bash
# Test precinct matching
curl -X POST http://localhost:3000/api/precinct/match \
  -H "Content-Type: application/json" \
  -d '{"address": "22 Illawarra Road, Marrickville", "lga": "Inner West"}'

# Expected: { success: true, precinct: { precinctNumber: "9_29", ... } }

# Test precinct provisions
curl -X POST http://localhost:3000/api/precinct/provisions \
  -H "Content-Type: application/json" \
  -d '{"precinctId": "9_29", "lga": "Inner West"}'

# Expected: { success: true, data: { provisions: [...], count: 15 } }
```

### 7.3 UI Tests

**Test Addresses (Known Precincts):**
- `22 Illawarra Road, Marrickville` → Precinct 9_29 (South Western Marrickville)
- `15 Addison Road, Marrickville` → Precinct 9_47 (Victoria Road)
- `100 Crystal Street, Petersham` → Precinct 9_3 (Stanmore North)

**Expected Behavior:**
1. Address entered → Precinct matched
2. Precinct section appears below DCP provisions
3. 15-20 precinct provisions displayed
4. Clicking provision shows full text in slide-out panel

## 8. Backward Compatibility

### Non-Breaking Changes
- ✅ New table (doesn't affect existing queries)
- ✅ New API routes (additive)
- ✅ Optional UI component (can be hidden)
- ✅ Feature flag controlled rollout

### Existing Functionality Preserved
- ✅ DCP provisions API unchanged (unless `includePrecinct=true`)
- ✅ Constraints API still works (just gets better data)
- ✅ All existing UI components unaffected
- ✅ Database queries use canonical view (correct pattern)

## 9. Performance Considerations

### Query Performance
- Precinct provisions: ~15-20 rows per query (fast)
- Indexed on `(lga, precinct_id)` for instant lookups
- JOIN to canonical view uses existing indexes

### Caching Strategy
```typescript
// Client-side: Cache precinct match result per address
const precinctCache = new Map<string, PrecinctInfo>();

// Server-side: Consider Redis cache for precinct→provisions mapping
// Key: `precinct:9_29:provisions`
// TTL: 24 hours (precincts rarely change)
```

## 10. Future Enhancements

### Phase 5: Advanced Features (Optional)
1. **Precinct Character Images**
   - Add `character_images` column (JSONB array of image URLs)
   - Display in UI for context

2. **Precinct Boundaries (GeoJSON)**
   - Add `boundary_geometry` column (JSONB polygon)
   - Enable map visualization
   - More accurate matching (point-in-polygon vs street matching)

3. **Cross-Precinct Analysis**
   - "Similar precincts" feature
   - Compare controls across precincts

4. **LGA Expansion**
   - Add Ashfield precincts (street mappings needed)
   - Add Leichhardt precincts (street mappings needed)
   - Generalize to other councils

## Summary

**Database:** Simple table (not SEPP-style JSONB) - 383 provisions → ~230 clean provisions
**API:** Two new routes + enhancement to existing DCP API (non-breaking)
**UI:** New component similar to DCPProvisionsBrowser (separate section)
**Migration:** Phased with feature flags (zero risk to existing functionality)
**Pattern:** Always use `regulatory_provisions_canonical` (follows established standard)

**Timeline Estimate:**
- Phase 1 (DB): 2 hours
- Phase 2 (API): 4 hours
- Phase 3 (UI): 6 hours
- Testing: 4 hours
- **Total: ~2 days**
