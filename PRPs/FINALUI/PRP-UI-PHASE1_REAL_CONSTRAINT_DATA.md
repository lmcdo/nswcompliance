# PRP-UI-PHASE1: Real Constraint Data Integration

## OBJECTIVE
Replace mock data in ComplianceDashboard with real constraint data from the PostgreSQL database (22,105 regulatory provisions).

## SUCCESS CRITERIA
- [ ] New API endpoint `/api/compliance/constraints` returns real database data
- [ ] ComplianceDashboard fetches and displays actual constraints
- [ ] Color coding by authority level (SEPP=Orange, LEP=Blue, DCP=Green) working
- [ ] Data matches property zone and development type
- [ ] Response time <2 seconds for typical property
- [ ] Error handling for missing data
- [ ] Zero TypeScript compilation errors
- [ ] All auto-verification tests pass

## ESTIMATED TIME
**2-3 hours total**
- API endpoint creation: 45 minutes
- Database query optimization: 30 minutes
- Frontend integration: 45 minutes
- Testing & verification: 30 minutes

---

## TECHNICAL SPECIFICATION

### Phase 1A: Database Schema Analysis

**Relevant Tables:**
```sql
-- Main provisions table (22,105 records)
regulatory_provisions (
  id INTEGER PRIMARY KEY,
  document_id TEXT,
  ref_number TEXT,
  section_header TEXT,
  provision_text TEXT,
  provision_type TEXT,
  zone TEXT,
  clause_number TEXT
)

-- Document metadata
documents (
  id TEXT PRIMARY KEY,
  document_name TEXT,
  document_type TEXT,  -- 'LEP', 'DCP', 'SEPP'
  jurisdiction TEXT
)

-- Zone-based permissions (221 records)
development_permissions (
  id INTEGER PRIMARY KEY,
  zone TEXT,
  development_type TEXT,
  permission_status TEXT,  -- 'permitted', 'consent', 'prohibited'
  source_provision_id TEXT,
  lep_name TEXT
)

-- SEPP overrides (91 records)
sepp_lep_overrides (
  id INTEGER PRIMARY KEY,
  sepp_name TEXT,
  override_type TEXT,
  affected_clause TEXT
)
```

**Constraint Type Mapping:**
```typescript
// Map provision_type to constraint categories
const PROVISION_TYPE_MAP = {
  // Building Envelope
  'height_limit': 'height',
  'height_of_buildings': 'height',
  'building_height': 'height',
  'maximum_height': 'height',

  'floor_space_ratio': 'fsr',
  'fsr': 'fsr',
  'density': 'fsr',

  'setback': 'setback',
  'building_setback': 'setback',
  'side_setback': 'setback',
  'front_setback': 'setback',
  'rear_setback': 'setback',

  // Environmental
  'heritage': 'heritage',
  'heritage_conservation': 'heritage',
  'conservation_area': 'heritage',

  'flood': 'environmental',
  'bushfire': 'environmental',
  'acid_sulfate_soils': 'environmental',

  // Special
  'basix': 'special',
  'sepp_override': 'special',
  'car_parking': 'special',
  'landscaping': 'special'
}
```

---

### Phase 1B: API Endpoint Implementation

**File:** `frontend-nextjs/app/api/compliance/constraints/route.ts`

```typescript
import { NextRequest, NextResponse } from 'next/server';
import { Pool } from 'pg';

// Database connection
const pool = new Pool({
  host: 'localhost',
  port: 5432,
  database: 'nsw_planning',
  user: 'postgres',
  password: 'postgres'
});

interface ConstraintQuery {
  address: string;
  zone: string;
  developmentType?: string;
  propId?: number;
}

interface ProvisionResult {
  id: number;
  provision_text: string;
  provision_type: string;
  clause_number: string;
  ref_number: string;
  section_header: string;
  document_name: string;
  document_type: string;
  zone: string;
}

interface ComplianceConstraint {
  type: 'height' | 'fsr' | 'setback' | 'heritage' | 'environmental' | 'special';
  value: string | number;
  unit?: string;
  source: {
    clause: string;
    document: string;
    authority_level: 'LEP' | 'DCP' | 'SEPP';
  };
  provision_id: number;
  full_text: string;
}

export async function POST(request: NextRequest) {
  const startTime = Date.now();

  try {
    const body: ConstraintQuery = await request.json();
    const { address, zone, developmentType, propId } = body;

    if (!zone) {
      return NextResponse.json({
        success: false,
        error: 'Zone is required'
      }, { status: 400 });
    }

    console.log(`[Constraints API] Query: zone=${zone}, devType=${developmentType}`);

    // Query 1: Get zone-specific provisions
    const provisionsQuery = `
      SELECT
        rp.id,
        rp.provision_text,
        rp.provision_type,
        rp.clause_number,
        rp.ref_number,
        rp.section_header,
        rp.zone,
        d.document_name,
        d.document_type
      FROM regulatory_provisions rp
      LEFT JOIN documents d ON rp.document_id = d.id
      WHERE rp.zone = $1
      AND rp.provision_type IS NOT NULL
      AND rp.provision_type != ''
      ORDER BY
        CASE d.document_type
          WHEN 'SEPP' THEN 1
          WHEN 'LEP' THEN 2
          WHEN 'DCP' THEN 3
          ELSE 4
        END,
        rp.clause_number
      LIMIT 50
    `;

    const provisionsResult = await pool.query(provisionsQuery, [zone]);

    console.log(`[Constraints API] Found ${provisionsResult.rows.length} provisions for zone ${zone}`);

    // Query 2: Get development permissions if developmentType provided
    let permissions: any[] = [];
    if (developmentType) {
      const permissionsQuery = `
        SELECT
          zone,
          development_type,
          permission_status,
          lep_name,
          source_provision_id
        FROM development_permissions
        WHERE zone = $1
        AND development_type = $2
        LIMIT 10
      `;

      const permissionsResult = await pool.query(permissionsQuery, [zone, developmentType]);
      permissions = permissionsResult.rows;

      console.log(`[Constraints API] Found ${permissions.length} permissions for ${developmentType} in ${zone}`);
    }

    // Query 3: Get SEPP overrides
    const seppQuery = `
      SELECT
        sepp_name,
        override_type,
        affected_clause,
        description
      FROM sepp_lep_overrides
      WHERE affected_clause ILIKE $1
      LIMIT 10
    `;

    const seppResult = await pool.query(seppQuery, [`%${zone}%`]);

    console.log(`[Constraints API] Found ${seppResult.rows.length} SEPP overrides`);

    // Transform provisions into constraints
    const constraints = transformProvisionsToConstraints(
      provisionsResult.rows,
      permissions,
      seppResult.rows
    );

    const processingTime = Date.now() - startTime;

    return NextResponse.json({
      success: true,
      data: {
        building_envelope: constraints.filter(c =>
          ['height', 'fsr', 'setback'].includes(c.type)
        ),
        environmental: constraints.filter(c =>
          ['heritage', 'environmental'].includes(c.type)
        ),
        special_provisions: constraints.filter(c =>
          c.type === 'special'
        ),
        development_permissions: permissions,
        sepp_overrides: seppResult.rows
      },
      metadata: {
        zone,
        developmentType,
        totalConstraints: constraints.length,
        processingTimeMs: processingTime,
        timestamp: new Date().toISOString()
      }
    });

  } catch (error) {
    console.error('[Constraints API] Error:', error);

    return NextResponse.json({
      success: false,
      error: error instanceof Error ? error.message : 'Internal server error',
      processingTimeMs: Date.now() - startTime
    }, { status: 500 });
  }
}

/**
 * Transform database provisions into UI-ready constraints
 */
function transformProvisionsToConstraints(
  provisions: ProvisionResult[],
  permissions: any[],
  seppOverrides: any[]
): ComplianceConstraint[] {
  const constraints: ComplianceConstraint[] = [];

  // Provision type to constraint type mapping
  const typeMap: Record<string, ComplianceConstraint['type']> = {
    'height_limit': 'height',
    'height_of_buildings': 'height',
    'building_height': 'height',
    'maximum_height': 'height',
    'floor_space_ratio': 'fsr',
    'fsr': 'fsr',
    'density': 'fsr',
    'setback': 'setback',
    'building_setback': 'setback',
    'heritage': 'heritage',
    'heritage_conservation': 'heritage',
    'flood': 'environmental',
    'bushfire': 'environmental',
    'basix': 'special',
    'car_parking': 'special'
  };

  for (const provision of provisions) {
    const constraintType = typeMap[provision.provision_type?.toLowerCase()] || 'special';

    // Extract numeric value if present
    const value = extractConstraintValue(provision.provision_text, constraintType);

    constraints.push({
      type: constraintType,
      value: value || provision.provision_text.substring(0, 100),
      unit: getUnitForType(constraintType, provision.provision_text),
      source: {
        clause: provision.clause_number || provision.ref_number || 'N/A',
        document: provision.document_name || 'Unknown Document',
        authority_level: (provision.document_type?.toUpperCase() as 'LEP' | 'DCP' | 'SEPP') || 'DCP'
      },
      provision_id: provision.id,
      full_text: provision.provision_text
    });
  }

  // Add SEPP overrides as special constraints
  for (const sepp of seppOverrides) {
    constraints.push({
      type: 'special',
      value: sepp.override_type || 'SEPP Override',
      source: {
        clause: sepp.affected_clause || 'N/A',
        document: sepp.sepp_name || 'SEPP Override',
        authority_level: 'SEPP'
      },
      provision_id: 0,
      full_text: sepp.description || 'SEPP override applies'
    });
  }

  return constraints;
}

/**
 * Extract numeric constraint values from provision text
 */
function extractConstraintValue(text: string, type: string): string | number | null {
  if (!text) return null;

  switch (type) {
    case 'height':
      // Match patterns like "9.5m", "9.5 metres", "9.5 meters"
      const heightMatch = text.match(/(\d+\.?\d*)\s*(m|metres?|meters?)/i);
      return heightMatch ? parseFloat(heightMatch[1]) : null;

    case 'fsr':
      // Match patterns like "0.6:1", "0.6", "1.5:1"
      const fsrMatch = text.match(/(\d+\.?\d*)\s*:?\s*1/);
      return fsrMatch ? parseFloat(fsrMatch[1]) : null;

    case 'setback':
      // Match patterns like "6m", "1.5m", "3 metres"
      const setbackMatches = text.match(/(\d+\.?\d*)\s*(m|metres?|meters?)/gi);
      if (setbackMatches && setbackMatches.length > 0) {
        return setbackMatches.join(', ');
      }
      return null;

    default:
      return null;
  }
}

/**
 * Get appropriate unit for constraint type
 */
function getUnitForType(type: string, text: string): string | undefined {
  switch (type) {
    case 'height':
    case 'setback':
      return 'm';
    case 'fsr':
      return ':1';
    default:
      return undefined;
  }
}
```

---

### Phase 1C: Frontend Integration

**File:** `frontend-nextjs/components/compliance/ComplianceDashboard.tsx`

**Update lines 54-132 (Replace mock data):**

```typescript
// BEFORE (Mock data - lines 54-132):
// const mockData: ComplianceData = { ... }

// AFTER (Real API call):
useEffect(() => {
  const loadComplianceData = async () => {
    try {
      setLoading(true);
      setError(null);

      if (!propertyData?.constraints?.zone) {
        setError('Property zone not available');
        setLoading(false);
        return;
      }

      console.log('[ComplianceDashboard] Fetching constraints for zone:', propertyData.constraints.zone);

      // Call real API endpoint
      const response = await fetch('/api/compliance/constraints', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          address: propertyData.address,
          zone: propertyData.constraints.zone,
          developmentType: propertyData.developmentType || undefined,
          propId: propertyData.propId
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const apiResponse = await response.json();

      if (!apiResponse.success) {
        throw new Error(apiResponse.error || 'Failed to load constraints');
      }

      console.log('[ComplianceDashboard] Loaded constraints:', apiResponse.data);
      console.log('[ComplianceDashboard] Metadata:', apiResponse.metadata);

      // Set real data from API
      setComplianceData({
        building_envelope: apiResponse.data.building_envelope || [],
        environmental: apiResponse.data.environmental || [],
        special_provisions: apiResponse.data.special_provisions || []
      });

    } catch (err) {
      console.error('[ComplianceDashboard] Failed to load compliance data:', err);
      setError(err instanceof Error ? err.message : 'Failed to load compliance data');
    } finally {
      setLoading(false);
    }
  };

  if (propertyData) {
    loadComplianceData();
  }
}, [propertyData]);
```

**Add TypeScript types (add to imports):**

```typescript
// Add to existing types in ComplianceDashboard.tsx
export interface APIResponse {
  success: boolean;
  data: {
    building_envelope: ComplianceConstraint[];
    environmental: ComplianceConstraint[];
    special_provisions: ComplianceConstraint[];
    development_permissions: any[];
    sepp_overrides: any[];
  };
  metadata: {
    zone: string;
    developmentType?: string;
    totalConstraints: number;
    processingTimeMs: number;
    timestamp: string;
  };
  error?: string;
}
```

---

### Phase 1D: Database Query Optimization

**Create index for performance:**

```sql
-- Add index for zone-based queries
CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_zone
ON regulatory_provisions(zone)
WHERE zone IS NOT NULL;

-- Add index for provision type filtering
CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_type
ON regulatory_provisions(provision_type)
WHERE provision_type IS NOT NULL;

-- Add composite index for common query pattern
CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_zone_type
ON regulatory_provisions(zone, provision_type)
WHERE zone IS NOT NULL AND provision_type IS NOT NULL;

-- Add index for development permissions lookup
CREATE INDEX IF NOT EXISTS idx_development_permissions_zone_type
ON development_permissions(zone, development_type);
```

**File:** `PRPs/FINALUI/scripts/create_constraint_indexes.sql`

---

### Phase 1E: Error Handling & Edge Cases

**Error Scenarios to Handle:**

1. **No constraints found for zone**
```typescript
if (constraints.length === 0) {
  return NextResponse.json({
    success: true,
    data: {
      building_envelope: [],
      environmental: [],
      special_provisions: []
    },
    metadata: {
      zone,
      totalConstraints: 0,
      processingTimeMs: Date.now() - startTime,
      warning: 'No constraints found for this zone'
    }
  });
}
```

2. **Invalid zone code**
```typescript
const validZonePattern = /^[A-Z]{1,3}\d{0,2}$/;
if (!validZonePattern.test(zone)) {
  return NextResponse.json({
    success: false,
    error: `Invalid zone code: ${zone}`
  }, { status: 400 });
}
```

3. **Database connection failure**
```typescript
try {
  await pool.query('SELECT 1');
} catch (error) {
  console.error('[Constraints API] Database connection failed:', error);
  return NextResponse.json({
    success: false,
    error: 'Database service unavailable'
  }, { status: 503 });
}
```

4. **Timeout protection**
```typescript
const QUERY_TIMEOUT = 5000; // 5 seconds

const timeoutPromise = new Promise((_, reject) =>
  setTimeout(() => reject(new Error('Query timeout')), QUERY_TIMEOUT)
);

const queryPromise = pool.query(provisionsQuery, [zone]);

const result = await Promise.race([queryPromise, timeoutPromise]);
```

---

## DELIVERABLES

1. **API Endpoint**
   - File: `frontend-nextjs/app/api/compliance/constraints/route.ts`
   - Lines: ~350
   - Features: Real database queries, constraint transformation, error handling

2. **Frontend Integration**
   - File: `frontend-nextjs/components/compliance/ComplianceDashboard.tsx`
   - Changes: Lines 54-132 (replace mock data)
   - Features: API call, loading states, error display

3. **Database Indexes**
   - File: `PRPs/FINALUI/scripts/create_constraint_indexes.sql`
   - Lines: ~25
   - Features: Performance optimization for zone queries

4. **TypeScript Types**
   - Updated types in ComplianceDashboard.tsx
   - New APIResponse interface
   - Constraint transformation types

5. **Verification Script**
   - File: `PRPs/FINALUI/scripts/verify_phase1.py`
   - Comprehensive automated testing

---

## VERIFICATION CHECKLIST

### Manual Verification (Quick Test)
- [ ] Navigate to `/assessment/dashboard`
- [ ] Enter test address: "30 Illawarra Road, Marrickville NSW"
- [ ] Verify constraint cards display with real data (not mock)
- [ ] Check color coding: SEPP=Orange, LEP=Blue, DCP=Green
- [ ] Confirm constraints match property zone (R2)
- [ ] Check browser console for API response logs
- [ ] Verify no TypeScript compilation errors

### Automated Verification
- [ ] Run: `python PRPs/FINALUI/scripts/verify_phase1.py`
- [ ] All tests pass (see verification script below)
- [ ] Performance benchmark <2s for typical query
- [ ] Database indexes created successfully
- [ ] API returns proper JSON structure

---

## ROLLBACK PLAN

If issues discovered:

```bash
# 1. Revert frontend changes
git checkout frontend-nextjs/components/compliance/ComplianceDashboard.tsx

# 2. Remove API endpoint
rm frontend-nextjs/app/api/compliance/constraints/route.ts

# 3. Drop indexes if causing issues
psql -U postgres -d nsw_planning -c "
DROP INDEX IF EXISTS idx_regulatory_provisions_zone;
DROP INDEX IF EXISTS idx_regulatory_provisions_type;
DROP INDEX IF EXISTS idx_regulatory_provisions_zone_type;
DROP INDEX IF EXISTS idx_development_permissions_zone_type;
"
```

---

## COMPLETION CRITERIA

✅ **Phase 1 Complete When:**
1. API endpoint returns real constraint data
2. Frontend displays actual provisions (not mock)
3. All 100+ auto-verification tests pass
4. Performance <2s for typical property
5. Zero compilation/runtime errors
6. Color coding working correctly
7. Data matches database content

**Time to completion:** 2-3 hours
**Risk level:** Low (no breaking changes to existing features)
**Dependencies:** PostgreSQL database operational, 22,105 provisions available