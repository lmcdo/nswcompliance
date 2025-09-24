# 🚀 POSTGRESQL MIGRATION PLAN - API ENDPOINTS

## Executive Summary

**Goal**: Migrate all remaining API endpoints from Python subprocess + SQLite to direct PostgreSQL integration for 30x performance improvement.

**Current Status**: 3/8 endpoints migrated, 5 still using legacy SQLite subprocess calls.

## 📊 MIGRATION TARGETS

### ❌ **Priority 1: High-Impact Endpoints**

#### 1. `/api/provisions` - Provision Search
- **Current**: Python subprocess → `provision_search.py` → SQLite
- **Usage**: Search regulatory provisions with filters
- **Performance Impact**: HIGH (most used endpoint)
- **Migration Complexity**: MEDIUM

#### 2. `/api/compliance/live-check` - Live Compliance
- **Current**: Python subprocess → `live_compliance_engine.py`
- **Usage**: Real-time FSR/height compliance calculations
- **Performance Impact**: HIGH (user-facing calculations)
- **Migration Complexity**: LOW (already uses NSW Planning API)

### ❌ **Priority 2: Supporting Endpoints**

#### 3. `/api/assessment/version-compliance` - Version Compliance
- **Current**: Python subprocess → `enhanced_compliance_api.py`
- **Usage**: Version-specific compliance checking
- **Performance Impact**: MEDIUM
- **Migration Complexity**: MEDIUM

#### 4. `/api/versions` - Version Management
- **Current**: Python subprocess → `version_manager.py`
- **Usage**: System version information
- **Performance Impact**: LOW
- **Migration Complexity**: LOW

#### 5. `/api/tod/parking-rates` - Parking Rates
- **Current**: Python subprocess → `parking_rates_fetcher.py`
- **Usage**: TOD parking rate lookup
- **Performance Impact**: LOW
- **Migration Complexity**: LOW

## 🏗️ MIGRATION STRATEGY BY ENDPOINT

### **1. `/api/provisions` → PostgreSQL Provision Search Client**

**Current SQLite Query Pattern**:
```python
# provision_search.py (SQLite)
SELECT id, clause_number, clause_title, content, document_type, document_name
FROM regulatory_provisions
WHERE content LIKE ? AND document_type IN (?)
```

**New PostgreSQL Implementation**:
```typescript
// lib/database/provision-search-client.ts
class ProvisionSearchClient {
  async searchProvisions(query: string, filters: SearchFilters) {
    const result = await this.pool.query(`
      SELECT rp.id, rp.ref_number, rp.provision_text, rp.document_id, rp.provision_type
      FROM regulatory_provisions rp
      WHERE rp.provision_text ILIKE $1
      AND ($2::text IS NULL OR rp.document_id ILIKE $2)
      ORDER BY rp.created_at DESC
      LIMIT $3
    `, [`%${query}%`, filters.documentType, filters.limit]);
    return result.rows;
  }
}
```

**Migration Steps**:
1. Create `ProvisionSearchClient` class
2. Replace subprocess call with direct client
3. Map SQLite column names to PostgreSQL schema
4. Add TypeScript types for response

### **2. `/api/compliance/live-check` → Direct PostgreSQL + NSW API**

**Current Architecture**:
- Subprocess → Python script → NSW Planning API + SQLite

**New Architecture**:
- Direct TypeScript → NSW Planning API + PostgreSQL validation

**Implementation**:
```typescript
// lib/compliance/live-compliance-client.ts
class LiveComplianceClient {
  async calculateCompliance(address: string, developmentParams: any) {
    // 1. Get property data from NSW Planning API (keep existing)
    const propertyData = await this.nswPlanningClient.getProperty(address);

    // 2. Get compliance rules from PostgreSQL (replace SQLite)
    const rules = await this.dbClient.getComplianceRules(propertyData.zone);

    // 3. Calculate compliance (pure TypeScript)
    return this.calculateFSRHeightCompliance(developmentParams, rules);
  }
}
```

### **3. `/api/assessment/version-compliance` → Version-Aware PostgreSQL Client**

**Migration**: Create version-aware compliance client that queries PostgreSQL with version filters.

### **4. `/api/versions` → Simple PostgreSQL Metadata Query**

**Migration**: Replace subprocess with direct PostgreSQL query to get database version info.

### **5. `/api/tod/parking-rates` → Static PostgreSQL Table**

**Migration**: Create `parking_rates` table in PostgreSQL and query directly.

## 🔧 IMPLEMENTATION PATTERNS

### **Pattern 1: Direct Replacement**
```typescript
// Before: Python subprocess
const python = spawn('python', [scriptPath, ...args]);

// After: PostgreSQL client
const client = new SpecializedClient();
const result = await client.queryMethod(params);
```

### **Pattern 2: Hybrid (External API + PostgreSQL validation)**
```typescript
// For endpoints that use external APIs + database validation
const externalData = await externalAPI.getData();
const validationRules = await pgClient.getValidationRules();
return validateAndProcess(externalData, validationRules);
```

### **Pattern 3: Pure PostgreSQL**
```typescript
// For endpoints that only need database queries
const pgClient = new DatabaseClient();
const result = await pgClient.complexQuery(filters);
return formatResponse(result);
```

## 📋 STEP-BY-STEP IMPLEMENTATION

### **Phase 1: Infrastructure (Week 1)**

1. **Create specialized PostgreSQL clients**:
   ```bash
   mkdir frontend-nextjs/lib/database/specialized/
   # Create: provision-search-client.ts
   # Create: live-compliance-client.ts
   # Create: version-client.ts
   # Create: parking-rates-client.ts
   ```

2. **Schema mapping analysis**:
   - Map SQLite column names to PostgreSQL equivalents
   - Identify missing indexes needed for performance
   - Create migration-specific database views if needed

3. **Create TypeScript types**:
   ```typescript
   // types/provision-search.ts
   export interface ProvisionSearchResult {
     id: number;
     ref_number: string;
     provision_text: string;
     document_id: string;
     authority_level: 'SEPP' | 'LEP' | 'DCP';
   }
   ```

### **Phase 2: High-Impact Migration (Week 2)**

#### **Day 1-2: `/api/provisions` Migration**
```typescript
// frontend-nextjs/app/api/provisions/route.ts
import { ProvisionSearchClient } from '@/lib/database/specialized/provision-search-client';

export async function GET(request: NextRequest) {
  const client = new ProvisionSearchClient();
  const results = await client.searchProvisions(query, filters);
  return NextResponse.json({ provisions: results });
}
```

#### **Day 3-4: `/api/compliance/live-check` Migration**
```typescript
// frontend-nextjs/app/api/compliance/live-check/route.ts
import { LiveComplianceClient } from '@/lib/compliance/live-compliance-client';

export async function POST(request: NextRequest) {
  const client = new LiveComplianceClient();
  const compliance = await client.calculateCompliance(address, params);
  return NextResponse.json(compliance);
}
```

#### **Day 5: Testing & Validation**
- A/B test both implementations
- Performance benchmarking
- Verify data consistency

### **Phase 3: Supporting Endpoints (Week 3)**

- Migrate remaining 3 endpoints
- Performance optimization
- Remove Python dependencies

### **Phase 4: Cleanup (Week 4)**

- Remove SQLite database files
- Clean up Python subprocess code
- Update documentation
- Performance monitoring

## 🛡️ RISK MITIGATION

### **Feature Flags**
```typescript
// lib/feature-flags.ts
export const usePostgreSQLProvisions = () => {
  return process.env.USE_POSTGRESQL_PROVISIONS === 'true';
};

// In API route:
if (usePostgreSQLProvisions()) {
  return await postgresqlClient.search(query);
} else {
  return await pythonSubprocess.search(query);
}
```

### **A/B Testing Pattern**
```typescript
async function handleProvisionSearch(query: string) {
  const useNewImplementation = Math.random() < 0.5; // 50/50 split

  if (useNewImplementation) {
    console.log('[A/B] Using PostgreSQL implementation');
    return await postgresqlClient.search(query);
  } else {
    console.log('[A/B] Using Python subprocess implementation');
    return await pythonSubprocess.search(query);
  }
}
```

### **Rollback Strategy**
1. Keep Python scripts intact during migration
2. Use feature flags to switch between implementations
3. Monitor error rates and performance metrics
4. Instant rollback capability via environment variable

### **Data Validation**
```typescript
// Validate PostgreSQL results match SQLite results during migration
async function validateMigration(query: string) {
  const [pgResult, sqliteResult] = await Promise.all([
    postgresqlClient.search(query),
    pythonSubprocess.search(query)
  ]);

  const match = compareResults(pgResult, sqliteResult);
  if (!match) {
    logDiscrepancy(query, pgResult, sqliteResult);
  }

  return pgResult; // Use PostgreSQL result but log differences
}
```

## 📈 EXPECTED BENEFITS

### **Performance Improvements**
- **30x faster** response times (150ms vs 5000ms)
- **Reduced memory usage** (no subprocess spawning)
- **Better concurrency** (connection pooling vs process spawning)

### **Reliability Improvements**
- **No subprocess failures**
- **Better error handling**
- **Connection pooling** with automatic retry
- **TypeScript type safety**

### **Operational Benefits**
- **Simplified deployment** (no Python dependencies)
- **Better monitoring** (database connection metrics)
- **Cloud readiness** (no subprocess restrictions)
- **Unified logging** (all TypeScript)

## 🎯 SUCCESS METRICS

### **Performance KPIs**
- API response times < 200ms (vs current 3000-5000ms)
- 99.9% success rate (vs current ~95% with subprocess failures)
- Memory usage reduction by 70%

### **Migration Milestones**
- [ ] Week 1: Infrastructure complete
- [ ] Week 2: High-impact endpoints migrated (50% traffic)
- [ ] Week 3: All endpoints using PostgreSQL
- [ ] Week 4: Python cleanup complete

This plan provides a systematic, risk-minimized approach to migrate all API endpoints to PostgreSQL while maintaining system reliability throughout the process.