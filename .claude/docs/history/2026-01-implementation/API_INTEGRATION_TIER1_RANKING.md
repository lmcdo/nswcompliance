# API INTEGRATION: TIER 1 RANKING
**How to integrate full-text + Tier 1 ranking into existing APIs**

---

## CURRENT STATE

### Existing API: `/api/provisions`

**File:** `frontend-nextjs/app/api/provisions/route.ts`

**Current flow:**
```
User → /api/provisions?q=setback
  ↓
  ProvisionSearchClient.searchProvisions()
  ↓
  SELECT * FROM regulatory_provisions
  WHERE provision_text ILIKE '%setback%'
  ORDER BY CASE WHEN document_id LIKE '%SEPP%' THEN 1 ELSE 3 END
```

**Issues:**
- Uses ILIKE (slow at scale)
- Basic hierarchy ordering (SEPP > LEP > DCP) but no ranking
- No quantitative boost
- No zone filtering
- Response time: ~150ms (good, but not optimal)

---

## WHAT NEEDS TO CHANGE

### Option 1: Update Existing ProvisionSearchClient (RECOMMENDED)

**Update:** `frontend-nextjs/lib/database/specialized/provision-search-client.ts`

**Changes needed:**

1. **Update `searchProvisions()` to use Tier 1 ranking**
2. **Add optional `userZone` parameter**
3. **Call `search_provisions_tier1()` database function**
4. **Keep backward compatibility**

---

### Option 2: Add New Endpoint (Alternative)

**Create:** `frontend-nextjs/app/api/provisions/search-ranked/route.ts`

**Benefit:** Doesn't touch existing code
**Downside:** Two search endpoints (confusing)

---

## RECOMMENDED IMPLEMENTATION

### Step 1: Update ProvisionSearchClient

**File:** `frontend-nextjs/lib/database/specialized/provision-search-client.ts`

**Add new method:**

```typescript
/**
 * Search provisions with Tier 1 ranking
 * Uses full-text search + hierarchy + quantitative + zone weighting
 */
async searchProvisionsTier1(
  query: string,
  filters: ProvisionSearchFilters & { userZone?: string } = {}
): Promise<ProvisionSearchResponse> {
  const startTime = Date.now();
  console.log(`[Tier 1 Ranking] Searching for: "${query}", zone: ${filters.userZone || 'all'}`);

  const client = await this.pool.connect();
  try {
    // Call database function with Tier 1 ranking
    const result = await client.query(`
      SELECT
        provision_id as id,
        ref_number,
        provision_text,
        document_type,
        zone,
        text_rank,
        hierarchy_weight,
        quant_boost,
        zone_boost,
        final_rank
      FROM search_provisions_tier1($1, $2, $3)
    `, [
      query,
      filters.userZone || null,
      filters.limit || 50
    ]);

    const searchTime = Date.now() - startTime;
    console.log(`[Tier 1 Ranking] Search completed in ${searchTime}ms`);

    return {
      provisions: result.rows.map(row => ({
        id: row.id,
        ref_number: row.ref_number,
        provision_text: this.truncateText(row.provision_text, 500),
        document_id: row.document_type, // Note: function returns document_type
        provision_type: row.provision_type,
        authority_level: row.document_type,
        zone: row.zone,
        // Add ranking metadata
        ranking: {
          text_rank: parseFloat(row.text_rank),
          hierarchy_weight: parseFloat(row.hierarchy_weight),
          quant_boost: parseFloat(row.quant_boost),
          zone_boost: parseFloat(row.zone_boost),
          final_rank: parseFloat(row.final_rank)
        }
      })),
      total_count: result.rows.length,
      search_metadata: {
        query,
        filters_applied: filters,
        search_time_ms: searchTime,
        data_source: 'postgresql_tier1_ranking',
        ranking_enabled: true
      }
    };

  } catch (error) {
    console.error('[Tier 1 Ranking] Search error:', error);
    throw new Error(`Tier 1 search failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
  } finally {
    client.release();
  }
}
```

---

### Step 2: Update API Route to Support Tier 1

**File:** `frontend-nextjs/app/api/provisions/route.ts`

**Add query parameter for ranking mode:**

```typescript
export async function GET(request: NextRequest) {
  const startTime = Date.now();
  const requestId = request.headers.get('x-request-id') || `req_${Date.now()}`;

  try {
    const { searchParams } = new URL(request.url);
    const query = searchParams.get('q') || '';
    const userZone = searchParams.get('zone'); // NEW: Zone filter
    const useTier1 = searchParams.get('ranked') === 'true'; // NEW: Enable Tier 1

    // Parse filters from query parameters
    const documentTypes = searchParams.get('document_types');
    const categories = searchParams.get('categories');
    const zones = searchParams.get('zones');
    const developmentTypes = searchParams.get('development_types');

    const filters: ProvisionSearchFilters & { userZone?: string } = {
      documentTypes: documentTypes?.split(','),
      categories: categories?.split(','),
      zones: zones?.split(','),
      developmentTypes: developmentTypes?.split(','),
      limit: parseInt(searchParams.get('limit') || '50'),
      userZone: userZone || undefined // NEW: Add zone to filters
    };

    console.log(`[Provision Search] Query: ${query}, Tier1: ${useTier1}, Zone: ${userZone || 'all'}`);

    // Feature flag: Use PostgreSQL or Python subprocess
    const usePostgreSQL = shouldUsePostgreSQL('provisions', requestId);

    let result: any;
    let implementation: 'postgresql' | 'subprocess' | 'tier1';

    if (usePostgreSQL && useTier1) {
      console.log('[Tier 1 Ranking] Using Tier 1 ranked search');
      implementation = 'tier1';

      const pgClient = new ProvisionSearchClient();
      result = await pgClient.searchProvisionsTier1(query, filters);
      await pgClient.close();

    } else if (usePostgreSQL) {
      console.log('[PostgreSQL Migration] Using direct PostgreSQL client');
      implementation = 'postgresql';

      const pgClient = new ProvisionSearchClient();
      result = await pgClient.searchProvisions(query, filters);
      await pgClient.close();

    } else {
      console.log('[PostgreSQL Migration] Using legacy Python subprocess');
      implementation = 'subprocess';

      result = await searchRealProvisions(query, filters);
    }

    const responseTime = Date.now() - startTime;

    // Log metrics for migration monitoring
    logMigrationMetrics('provisions', implementation, responseTime, true);

    return NextResponse.json({
      success: true,
      data: result,
      meta: {
        implementation,
        response_time_ms: responseTime,
        migration_status: useTier1 ? 'using_tier1_ranking' :
                         usePostgreSQL ? 'using_postgresql' : 'using_subprocess',
        ranking_enabled: useTier1
      }
    });

  } catch (error) {
    // ... error handling unchanged
  }
}
```

---

### Step 3: Update TypeScript Types

**File:** `frontend-nextjs/types/provision-search.ts` (or create if doesn't exist)

**Add ranking metadata:**

```typescript
export interface ProvisionRankingMetadata {
  text_rank: number;
  hierarchy_weight: number;
  quant_boost: number;
  zone_boost: number;
  final_rank: number;
}

export interface ProvisionSearchResult {
  id: number;
  ref_number: string;
  provision_text: string;
  document_id: string;
  provision_type?: string;
  authority_level: string;
  zone?: string;
  development_type?: string;
  page_number?: string;
  confidence_score?: number;
  ranking?: ProvisionRankingMetadata; // NEW: Optional ranking metadata
}

export interface ProvisionSearchFilters {
  documentTypes?: string[];
  categories?: string[];
  zones?: string[];
  developmentTypes?: string[];
  limit?: number;
  userZone?: string; // NEW: User's zone for ranking boost
}

export interface ProvisionSearchMetadata {
  query: string;
  filters_applied: ProvisionSearchFilters;
  search_time_ms: number;
  data_source: string;
  performance_improvement?: string;
  ranking_enabled?: boolean; // NEW: Indicates if Tier 1 ranking used
}

export interface ProvisionSearchResponse {
  provisions: ProvisionSearchResult[];
  total_count: number;
  search_metadata: ProvisionSearchMetadata;
}
```

---

## USAGE EXAMPLES

### Frontend API Calls

**Basic search (old behavior, still works):**
```typescript
// Current: ILIKE search, no ranking
const response = await fetch('/api/provisions?q=setback&limit=20');
const data = await response.json();
// Returns provisions in arbitrary order
```

**Tier 1 ranked search (new):**
```typescript
// New: Full-text + Tier 1 ranking
const response = await fetch('/api/provisions?q=setback&ranked=true&limit=20');
const data = await response.json();
// Returns provisions ranked by hierarchy + quantitative + zone
```

**Tier 1 with zone filter:**
```typescript
// Best: Full-text + Tier 1 + zone filtering
const response = await fetch('/api/provisions?q=setback&ranked=true&zone=R2&limit=20');
const data = await response.json();
// Returns R2 provisions ranked highest (5x boost)
```

---

### Frontend Component Example

**Using ranked search in a React component:**

```typescript
// frontend-nextjs/components/provision-search.tsx

import { useState } from 'react';

export function ProvisionSearch({ userZone }: { userZone?: string }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    setLoading(true);
    try {
      // Use Tier 1 ranking if zone available
      const useTier1 = userZone ? true : false;
      const zoneParam = userZone ? `&zone=${userZone}` : '';

      const response = await fetch(
        `/api/provisions?q=${encodeURIComponent(query)}&ranked=${useTier1}${zoneParam}&limit=20`
      );

      const data = await response.json();

      if (data.success) {
        setResults(data.data.provisions);
        console.log(`Search completed in ${data.meta.response_time_ms}ms`);
        console.log(`Ranking enabled: ${data.meta.ranking_enabled}`);
      }
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search provisions..."
      />
      <button onClick={handleSearch} disabled={loading}>
        {loading ? 'Searching...' : 'Search'}
      </button>

      {userZone && (
        <div className="text-sm text-gray-600">
          Searching in zone: {userZone} (results will be ranked by relevance)
        </div>
      )}

      <div className="results">
        {results.map((provision) => (
          <div key={provision.id} className="provision-result">
            <div className="font-bold">[{provision.authority_level}] {provision.ref_number}</div>
            <div className="text-sm">{provision.provision_text}</div>

            {/* Show ranking metadata if available */}
            {provision.ranking && (
              <div className="text-xs text-gray-500">
                Rank: {provision.ranking.final_rank.toFixed(2)}
                (hierarchy: {provision.ranking.hierarchy_weight}x,
                 quant: {provision.ranking.quant_boost}x,
                 zone: {provision.ranking.zone_boost}x)
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## MIGRATION STRATEGY

### Phase 1: Add Tier 1 Support (Zero Breaking Changes)

**Week 1:**
1. ✅ Add `searchProvisionsTier1()` method to ProvisionSearchClient
2. ✅ Update `/api/provisions` to accept `?ranked=true` parameter
3. ✅ Update TypeScript types
4. ✅ Test with `ranked=false` (old behavior) and `ranked=true` (new behavior)

**Result:** Both old and new search work simultaneously

---

### Phase 2: Gradual Frontend Migration

**Week 2:**
1. Update search components to use `ranked=true` by default
2. Pass user's zone when available (from property context)
3. Monitor performance metrics (should be 2-3x faster)
4. Collect user feedback

**Result:** Users see ranked results, can fall back to old search if issues

---

### Phase 3: Make Tier 1 Default

**Week 3:**
1. Make `ranked=true` the default behavior
2. Add `ranked=false` for legacy fallback
3. Update documentation
4. Remove Python subprocess fallback (if PostgreSQL migration complete)

**Result:** Tier 1 ranking is standard, old search available as fallback

---

## TESTING CHECKLIST

### Backend Tests

```typescript
// Test 1: Basic Tier 1 search
const response = await fetch('/api/provisions?q=setback&ranked=true');
// Expected: Returns ranked results, ~10-20ms

// Test 2: Zone filtering
const response = await fetch('/api/provisions?q=setback&ranked=true&zone=R2');
// Expected: R2 provisions ranked highest

// Test 3: Backward compatibility
const response = await fetch('/api/provisions?q=setback&ranked=false');
// Expected: Old ILIKE search, ~50-150ms

// Test 4: No query
const response = await fetch('/api/provisions?ranked=true');
// Expected: Returns empty or all provisions (depends on business logic)

// Test 5: Invalid zone
const response = await fetch('/api/provisions?q=setback&ranked=true&zone=INVALID');
// Expected: Treats as general search (zone_boost=1.0)
```

### Frontend Tests

```typescript
// Test 1: Search without zone
<ProvisionSearch />
// Expected: Uses ranked=true, zone=null

// Test 2: Search with zone
<ProvisionSearch userZone="R2" />
// Expected: Uses ranked=true, zone=R2, R2 results ranked 5x higher

// Test 3: Results display ranking metadata
// Expected: Shows hierarchy weight, quant boost, zone boost in UI
```

---

## PERFORMANCE EXPECTATIONS

### Before Tier 1:

| Query | Response Time | Ranking | Top Result |
|-------|---------------|---------|------------|
| "setback" | ~150ms | Random order | Could be DCP reference |
| "building height" | ~100ms | SEPP/LEP/DCP mixed | Arbitrary |

### After Tier 1:

| Query | Response Time | Ranking | Top Result |
|-------|---------------|---------|------------|
| "setback" | ~10-20ms | Hierarchical | SEPP with quant standards |
| "setback" + zone=R2 | ~5-10ms | Zone-boosted | R2 SEPP provisions |
| "building height" | ~5-10ms | Hierarchical | SEPP building height clause |

**Improvement:**
- Speed: 5-10x faster
- Ranking: ∞ improvement (none → Tier 1)
- User productivity: 10-20x (find answer in top 5 vs scanning 50-100)

---

## ROLLBACK PLAN

**If Tier 1 ranking causes issues:**

1. **Frontend:** Set `ranked=false` as default in search components
2. **Backend:** Keep old `searchProvisions()` method active
3. **Database:** Tier 1 function still exists but not called

**Result:** Instant fallback to old behavior, zero downtime

---

## MINIMAL CODE CHANGES REQUIRED

### Summary of Changes:

| File | Changes | Lines Added | Risk |
|------|---------|-------------|------|
| `provision-search-client.ts` | Add `searchProvisionsTier1()` | ~60 | LOW (additive) |
| `route.ts` (provisions API) | Add `ranked` and `zone` params | ~15 | LOW (backward compatible) |
| `provision-search.ts` (types) | Add ranking metadata types | ~15 | ZERO (types only) |
| **TOTAL** | **3 files** | **~90 lines** | **LOW** |

**Existing code:** Unchanged, continues to work
**New functionality:** Opt-in with `?ranked=true`
**Breaking changes:** ZERO

---

## RECOMMENDATION

**Implement Phase 1 immediately:**

1. Add `searchProvisionsTier1()` method (30 min)
2. Update `/api/provisions` route (15 min)
3. Update TypeScript types (10 min)
4. Test both `ranked=true` and `ranked=false` (15 min)

**Total time: ~70 minutes**

**Benefits:**
- 2-3x faster queries
- Proper hierarchical ranking
- Zone filtering ready
- Zero breaking changes
- Backward compatible

**The API already exists, we just need to wire it up to the new database function.**

---

*End of API Integration Guide*
