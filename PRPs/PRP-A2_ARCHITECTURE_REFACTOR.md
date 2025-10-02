# PRP-A2: Architecture Refactor - Direct Database Integration
## Universal Technical Implementation Specification Compliance

**Date**: 2025-09-23
**Status**: READY FOR IMPLEMENTATION
**Priority**: HIGH - PRODUCTION ARCHITECTURE
**Duration**: 1 session
**Dependencies**: PRP-A1 (Database Safety Retrofit)

---

## **EXECUTIVE SUMMARY**

This PRP eliminates subprocess spawning and implements direct TypeScript database integration while maintaining the existing UI components unchanged. It transforms the backend from Python subprocess calls to native Node.js/TypeScript database queries, creating a cloud-ready, high-performance architecture.

---

## **ARCHITECTURAL TRANSFORMATION**

### **Current Architecture (Subprocess-Based)**
```
┌─────────────────────────────────────────────────────────────────┐
│ Next.js Frontend (TypeScript)                                  │
├─────────────────────────────────────────────────────────────────┤
│ ComplianceDataClient.spawn() → Python subprocess              │
│ ↓                                                               │
│ get_provision_details.py → PostgreSQL                         │
│ get_setback_provisions.py → PostgreSQL                        │
└─────────────────────────────────────────────────────────────────┘

PROBLEMS:
- Resource leaks (subprocess cleanup)
- Windows process buildup
- No connection pooling
- 2-5 second cold start delays
- Container deployment failures
```

### **Target Architecture (Direct Integration)**
```
┌─────────────────────────────────────────────────────────────────┐
│ Next.js Frontend (TypeScript) - UNCHANGED                      │
├─────────────────────────────────────────────────────────────────┤
│ ComplianceDataClient (Native TypeScript)                       │
│ ↓                                                               │
│ PostgreSQL Client Pool → Direct SQL Queries                   │
│ ↓                                                               │
│ Connection Pool Management → Optimized Performance             │
└─────────────────────────────────────────────────────────────────┘

BENEFITS:
- Zero subprocess overhead
- Native connection pooling
- <200ms response times
- Cloud container ready
- Windows/Linux compatible
```

---

## **IMPLEMENTATION SPECIFICATION**

### **Phase 1: Native Database Client**
```typescript
// lib/database/postgres-client.ts
import { Pool, PoolClient } from 'pg';
import type {
  ProvisionContent,
  ComplianceConstraint,
  SetbackProvision
} from '@/types/compliance';

export interface DatabaseConfig {
  host: string;
  database: string;
  user: string;
  password: string;
  port: number;
  max: number;          // Connection pool size
  idleTimeoutMillis: number;
  connectionTimeoutMillis: number;
}

export class PostgreSQLComplianceClient {
  private pool: Pool;
  private static instance: PostgreSQLComplianceClient;

  constructor(config: DatabaseConfig) {
    this.pool = new Pool({
      ...config,
      ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
    });

    // Pool error handling
    this.pool.on('error', (err) => {
      console.error('PostgreSQL pool error:', err);
    });

    // Connection health monitoring
    this.pool.on('connect', (client) => {
      console.log('New PostgreSQL client connected');
    });
  }

  static getInstance(config?: DatabaseConfig): PostgreSQLComplianceClient {
    if (!PostgreSQLComplianceClient.instance) {
      if (!config) {
        throw new Error('Database config required for first initialization');
      }
      PostgreSQLComplianceClient.instance = new PostgreSQLComplianceClient(config);
    }
    return PostgreSQLComplianceClient.instance;
  }

  /**
   * Get detailed provision content for a specific clause
   * Direct PostgreSQL implementation replacing Python subprocess
   */
  async getProvisionDetails(
    clauseReference: string,
    documentType: 'LEP' | 'DCP' | 'SEPP'
  ): Promise<ProvisionContent[]> {
    const client: PoolClient = await this.pool.connect();

    try {
      // Document type patterns matching original Python logic
      let docPattern: string;
      switch (documentType) {
        case 'LEP':
          docPattern = '%Local_Environmental_Plan%';
          break;
        case 'DCP':
          docPattern = '%DCP%';
          break;
        case 'SEPP':
          docPattern = '%Environmental_Planning_Policy%';
          break;
        default:
          docPattern = '%';
      }

      // Direct SQL query with same logic as Python version
      const query = `
        SELECT
          id,
          ref_number,
          section_header,
          provision_text,
          document_id,
          provision_type,
          zone,
          development_type,
          page_number
        FROM regulatory_provisions
        WHERE (
          ref_number ILIKE $1
          OR ref_number ILIKE $2
          OR provision_text ILIKE $3
        )
        AND document_id ILIKE $4
        AND provision_text IS NOT NULL
        AND LENGTH(provision_text) > 50
        ORDER BY
          CASE
            WHEN ref_number ILIKE $5 THEN 1
            WHEN ref_number ILIKE $6 THEN 2
            ELSE 3
          END,
          LENGTH(provision_text) DESC
        LIMIT 10
      `;

      const params = [
        `%${clauseReference}%`,
        `%${clauseReference.replace("Clause ", "")}%`,
        `%${clauseReference}%`,
        docPattern,
        clauseReference,
        clauseReference.replace("Clause ", "")
      ];

      // Execute with timeout
      const result = await Promise.race([
        client.query(query, params),
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error('Query timeout')), 30000)
        )
      ]) as any;

      return result.rows.map((row: any): ProvisionContent => ({
        id: row.id,
        ref_number: row.ref_number,
        section_header: row.section_header,
        provision_text: row.provision_text,
        document_id: row.document_id,
        provision_type: row.provision_type,
        zone: row.zone,
        development_type: row.development_type,
        page_number: row.page_number
      }));

    } catch (error) {
      console.error('PostgreSQL provision query error:', error);
      throw new Error(`Failed to retrieve provisions: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      client.release();
    }
  }

  /**
   * Get setback provisions for a specific zone
   * Direct PostgreSQL implementation replacing Python subprocess
   */
  async getSetbackProvisions(zone: string): Promise<ProvisionContent[]> {
    const client: PoolClient = await this.pool.connect();

    try {
      const query = `
        SELECT DISTINCT
          rp.id,
          rp.ref_number,
          rp.section_header,
          rp.provision_text,
          rp.document_id,
          rp.provision_type,
          rp.zone,
          rp.development_type,
          rp.page_number
        FROM regulatory_provisions rp
        WHERE (
          rp.provision_text ILIKE '%setback%'
          OR rp.provision_text ILIKE '%building line%'
          OR rp.provision_text ILIKE '%front boundary%'
          OR rp.provision_text ILIKE '%side boundary%'
          OR rp.provision_text ILIKE '%rear boundary%'
        )
        AND (
          rp.zone = $1
          OR rp.zone IS NULL
          OR rp.zone = 'all'
        )
        AND rp.provision_text IS NOT NULL
        AND LENGTH(rp.provision_text) > 100
        ORDER BY
          CASE
            WHEN rp.zone = $1 THEN 1
            WHEN rp.zone IS NULL THEN 2
            ELSE 3
          END,
          LENGTH(rp.provision_text) DESC
        LIMIT 15
      `;

      const result = await Promise.race([
        client.query(query, [zone]),
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error('Setback query timeout')), 30000)
        )
      ]) as any;

      return result.rows.map((row: any): ProvisionContent => ({
        id: row.id,
        ref_number: row.ref_number,
        section_header: row.section_header,
        provision_text: row.provision_text,
        document_id: row.document_id,
        provision_type: row.provision_type,
        zone: row.zone,
        development_type: row.development_type,
        page_number: row.page_number
      }));

    } catch (error) {
      console.error('PostgreSQL setback query error:', error);
      throw new Error(`Failed to retrieve setback provisions: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      client.release();
    }
  }

  /**
   * Get comprehensive compliance data with optimized queries
   * Replaces multiple subprocess calls with single connection
   */
  async getComplianceData(
    zone: string,
    heritage: boolean,
    constraints: any
  ): Promise<{
    building_envelope: ComplianceConstraint[];
    environmental: ComplianceConstraint[];
    special_provisions: ComplianceConstraint[];
  }> {
    const client: PoolClient = await this.pool.connect();

    try {
      // Parallel query execution for performance
      const [heightProvisions, fsrProvisions, setbackProvisions, heritageProvisions, seppProvisions] = await Promise.all([
        constraints.maxHeight ? this.getProvisionDetails('Clause 4.3', 'LEP') : Promise.resolve([]),
        constraints.maxFsr ? this.getProvisionDetails('Clause 4.4', 'LEP') : Promise.resolve([]),
        this.getSetbackProvisions(zone),
        heritage ? this.getProvisionDetails('Clause 5.10', 'LEP') : Promise.resolve([]),
        this.getSEPPProvisions(constraints)
      ]);

      // Build envelope constraints
      const buildingEnvelope: ComplianceConstraint[] = [];

      if (constraints.maxHeight) {
        buildingEnvelope.push({
          type: 'height',
          value: constraints.maxHeight,
          unit: 'm',
          source: {
            clause: 'Clause 4.3',
            document: 'Inner West Local Environmental Plan 2022',
            authority_level: 'LEP'
          },
          provisions: heightProvisions
        });
      }

      if (constraints.maxFsr) {
        buildingEnvelope.push({
          type: 'fsr',
          value: constraints.maxFsr,
          unit: ':1',
          source: {
            clause: 'Clause 4.4',
            document: 'Inner West Local Environmental Plan 2022',
            authority_level: 'LEP'
          },
          provisions: fsrProvisions
        });
      }

      if (setbackProvisions.length > 0) {
        buildingEnvelope.push({
          type: 'setback',
          value: 'Various',
          source: {
            clause: 'DCP Setback Requirements',
            document: 'Inner West DCP',
            authority_level: 'DCP'
          },
          provisions: setbackProvisions
        });
      }

      // Environmental constraints
      const environmental: ComplianceConstraint[] = [];

      if (heritage) {
        environmental.push({
          type: 'heritage',
          value: 'Heritage Item',
          source: {
            clause: 'Clause 5.10',
            document: 'Inner West Local Environmental Plan 2022',
            authority_level: 'LEP'
          },
          provisions: heritageProvisions
        });
      }

      // Special provisions (SEPPs)
      const specialProvisions: ComplianceConstraint[] = [];

      if (constraints.basixWater) {
        specialProvisions.push({
          type: 'special',
          value: constraints.basixWater,
          source: {
            clause: 'SEPP Sustainable Buildings',
            document: 'State Environmental Planning Policy (Sustainable Buildings) 2022',
            authority_level: 'SEPP'
          },
          provisions: seppProvisions
        });
      }

      return {
        building_envelope: buildingEnvelope,
        environmental: environmental,
        special_provisions: specialProvisions
      };

    } catch (error) {
      console.error('PostgreSQL compliance data error:', error);
      throw new Error(`Failed to retrieve compliance data: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      client.release();
    }
  }

  /**
   * Get SEPP provisions that may override LEP/DCP
   */
  private async getSEPPProvisions(constraints: any): Promise<ProvisionContent[]> {
    if (!constraints.basixWater) return [];

    return this.getProvisionDetails('BASIX', 'SEPP');
  }

  /**
   * Health check for database connection
   */
  async healthCheck(): Promise<{ healthy: boolean; connections: number; error?: string }> {
    try {
      const client = await this.pool.connect();
      const result = await client.query('SELECT 1 as health_check');
      client.release();

      return {
        healthy: result.rows[0].health_check === 1,
        connections: this.pool.totalCount
      };
    } catch (error) {
      return {
        healthy: false,
        connections: 0,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  /**
   * Close all connections when shutting down
   */
  async close(): Promise<void> {
    await this.pool.end();
  }
}
```

### **Phase 2: Updated Compliance Client**
```typescript
// lib/database/compliance-client.ts - REFACTORED VERSION
import { PostgreSQLComplianceClient } from './postgres-client';
import type {
  ComplianceData,
  ComplianceConstraint,
  ProvisionContent
} from '@/types/compliance';

export class ComplianceDataClient {
  private dbClient: PostgreSQLComplianceClient;

  constructor() {
    // Initialize with environment configuration
    const config = {
      host: process.env.DB_HOST || '127.0.0.1',
      database: process.env.DB_NAME || 'nsw_planning',
      user: process.env.DB_USER || 'postgres',
      password: process.env.DB_PASSWORD || '',
      port: parseInt(process.env.DB_PORT || '5432'),
      max: 20,  // Connection pool size
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 2000,
    };

    this.dbClient = PostgreSQLComplianceClient.getInstance(config);
  }

  /**
   * Get comprehensive compliance data for a property
   * NOW USES DIRECT DATABASE CONNECTION - NO SUBPROCESS
   */
  async getComplianceData(
    zone: string,
    heritage: boolean,
    constraints: any
  ): Promise<ComplianceData> {
    const startTime = Date.now();

    try {
      // Direct database call - NO subprocess spawning
      const result = await this.dbClient.getComplianceData(zone, heritage, constraints);

      const processingTime = Date.now() - startTime;
      console.log(`Compliance data retrieved in ${processingTime}ms (direct database)`);

      return result;

    } catch (error) {
      console.error('Compliance data retrieval error (direct database):', error);
      throw new Error(`Failed to retrieve compliance data: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Get detailed provision content for a specific clause
   * NOW USES DIRECT DATABASE CONNECTION - NO SUBPROCESS
   */
  async getProvisionDetails(
    clauseReference: string,
    documentType: 'LEP' | 'DCP' | 'SEPP'
  ): Promise<ProvisionContent[]> {
    try {
      // Direct database call - NO subprocess spawning
      return await this.dbClient.getProvisionDetails(clauseReference, documentType);
    } catch (error) {
      console.error('Provision details error (direct database):', error);
      return []; // Graceful degradation
    }
  }

  /**
   * Get setback provisions for a zone
   * NOW USES DIRECT DATABASE CONNECTION - NO SUBPROCESS
   */
  async getSetbackProvisions(zone: string): Promise<ProvisionContent[]> {
    try {
      // Direct database call - NO subprocess spawning
      return await this.dbClient.getSetbackProvisions(zone);
    } catch (error) {
      console.error('Setback provisions error (direct database):', error);
      return []; // Graceful degradation
    }
  }

  /**
   * Health check for the entire compliance system
   */
  async healthCheck(): Promise<{ healthy: boolean; details: any }> {
    try {
      const dbHealth = await this.dbClient.healthCheck();
      return {
        healthy: dbHealth.healthy,
        details: {
          database: dbHealth,
          architecture: 'direct_database',
          subprocess_count: 0  // No more subprocesses!
        }
      };
    } catch (error) {
      return {
        healthy: false,
        details: {
          error: error instanceof Error ? error.message : 'Unknown error',
          architecture: 'direct_database'
        }
      };
    }
  }
}
```

### **Phase 3: Environment Configuration**
```typescript
// lib/config/database.ts
export interface DatabaseEnvironment {
  development: DatabaseConfig;
  production: DatabaseConfig;
  test: DatabaseConfig;
}

export const databaseConfig: DatabaseEnvironment = {
  development: {
    host: 'localhost',
    database: 'nsw_planning',
    user: 'postgres',
    password: '',
    port: 5432,
    max: 10,
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 2000,
  },
  production: {
    host: process.env.DATABASE_HOST!,
    database: process.env.DATABASE_NAME!,
    user: process.env.DATABASE_USER!,
    password: process.env.DATABASE_PASSWORD!,
    port: parseInt(process.env.DATABASE_PORT || '5432'),
    max: 50,  // Higher pool for production
    idleTimeoutMillis: 60000,
    connectionTimeoutMillis: 5000,
  },
  test: {
    host: 'localhost',
    database: 'nsw_planning_test',
    user: 'postgres',
    password: '',
    port: 5432,
    max: 5,
    idleTimeoutMillis: 10000,
    connectionTimeoutMillis: 1000,
  }
};

export function getDatabaseConfig(): DatabaseConfig {
  const env = process.env.NODE_ENV || 'development';
  return databaseConfig[env as keyof DatabaseEnvironment];
}
```

### **Phase 4: API Route Updates**
```typescript
// app/api/compliance/dashboard/route.ts - UPDATED FOR DIRECT DATABASE
import { NextRequest, NextResponse } from 'next/server';
import { ComplianceDataClient } from '@/lib/database/compliance-client';
import type { PropertyData } from '@/lib/property-data';

// Initialize single client instance (connection pooling)
const complianceClient = new ComplianceDataClient();

export async function POST(request: NextRequest) {
  const startTime = Date.now();

  try {
    const body = await request.json();
    const { zone, heritage, constraints } = body;

    // Validate inputs
    if (!zone || typeof zone !== 'string') {
      return NextResponse.json(
        { success: false, error: 'Zone is required' },
        { status: 400 }
      );
    }

    // Get compliance data using direct database connection
    const complianceData = await complianceClient.getComplianceData(
      zone,
      Boolean(heritage),
      constraints || {}
    );

    const processingTime = Date.now() - startTime;

    return NextResponse.json({
      success: true,
      data: complianceData,
      metadata: {
        processing_time_ms: processingTime,
        architecture: 'direct_database',
        subprocess_count: 0,
        zone,
        heritage_status: Boolean(heritage)
      }
    });

  } catch (error) {
    const processingTime = Date.now() - startTime;
    console.error('Compliance dashboard API error:', error);

    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        metadata: {
          processing_time_ms: processingTime,
          architecture: 'direct_database'
        }
      },
      { status: 500 }
    );
  }
}

// Health check endpoint
export async function GET() {
  try {
    const health = await complianceClient.healthCheck();

    return NextResponse.json({
      success: true,
      health,
      architecture: 'direct_database',
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Health check failed',
        architecture: 'direct_database'
      },
      { status: 500 }
    );
  }
}
```

---

## **MIGRATION PROCEDURE**

### **Step 1: Database Dependencies**
```bash
# Install PostgreSQL client for Node.js
cd frontend-nextjs
npm install pg @types/pg

# Install connection pooling
npm install pg-pool

# Optional: Install query builder for complex queries
npm install knex
```

### **Step 2: Environment Configuration**
```bash
# Update .env.local
cat > frontend-nextjs/.env.local << EOF
# Database Configuration (Direct Connection)
DB_HOST=127.0.0.1
DB_NAME=nsw_planning
DB_USER=postgres
DB_PASSWORD=
DB_PORT=5432

# Connection Pool Settings
DB_POOL_MIN=2
DB_POOL_MAX=20
DB_IDLE_TIMEOUT=30000
DB_CONNECTION_TIMEOUT=2000

# Architecture Mode
COMPLIANCE_ARCHITECTURE=direct_database
EOF
```

### **Step 3: Gradual Migration Strategy**
```typescript
// Feature flag for gradual migration
export class ComplianceDataClient {
  private useDirectDatabase: boolean;

  constructor() {
    // Feature flag to gradually migrate from subprocess to direct
    this.useDirectDatabase = process.env.COMPLIANCE_ARCHITECTURE === 'direct_database';

    if (this.useDirectDatabase) {
      this.dbClient = PostgreSQLComplianceClient.getInstance(getDatabaseConfig());
    }
  }

  async getProvisionDetails(clauseReference: string, documentType: string): Promise<ProvisionContent[]> {
    if (this.useDirectDatabase) {
      // NEW: Direct database connection
      return await this.dbClient.getProvisionDetails(clauseReference, documentType);
    } else {
      // OLD: Subprocess fallback during migration
      return await this.getProvisionDetailsSubprocess(clauseReference, documentType);
    }
  }
}
```

### **Step 4: Performance Monitoring**
```typescript
// lib/monitoring/performance.ts
export class PerformanceMonitor {
  private metrics: Map<string, number[]> = new Map();

  logQueryTime(operation: string, timeMs: number, method: 'direct' | 'subprocess') {
    const key = `${operation}_${method}`;
    const times = this.metrics.get(key) || [];
    times.push(timeMs);
    this.metrics.set(key, times);

    // Log performance comparison
    if (times.length % 10 === 0) {
      const avg = times.reduce((a, b) => a + b, 0) / times.length;
      console.log(`${key}: Average ${avg.toFixed(2)}ms over ${times.length} operations`);
    }
  }

  getPerformanceReport(): Record<string, { avg: number; min: number; max: number; count: number }> {
    const report: Record<string, any> = {};

    for (const [key, times] of this.metrics.entries()) {
      report[key] = {
        avg: times.reduce((a, b) => a + b, 0) / times.length,
        min: Math.min(...times),
        max: Math.max(...times),
        count: times.length
      };
    }

    return report;
  }
}
```

---

## **TESTING AND VALIDATION**

### **Performance Tests**
```typescript
// tests/performance/direct-database.test.ts
import { ComplianceDataClient } from '@/lib/database/compliance-client';

describe('Direct Database Performance', () => {
  let client: ComplianceDataClient;

  beforeAll(() => {
    client = new ComplianceDataClient();
  });

  test('provision details < 200ms', async () => {
    const start = Date.now();
    const provisions = await client.getProvisionDetails('Clause 4.3', 'LEP');
    const duration = Date.now() - start;

    expect(duration).toBeLessThan(200);
    expect(provisions.length).toBeGreaterThan(0);
  });

  test('full compliance data < 500ms', async () => {
    const start = Date.now();
    const data = await client.getComplianceData('R2', false, {
      maxHeight: 9.5,
      maxFsr: 0.6
    });
    const duration = Date.now() - start;

    expect(duration).toBeLessThan(500);
    expect(data.building_envelope.length).toBeGreaterThan(0);
  });

  test('concurrent requests handled', async () => {
    const promises = Array(10).fill(0).map(() =>
      client.getProvisionDetails('Clause 4.3', 'LEP')
    );

    const start = Date.now();
    const results = await Promise.all(promises);
    const duration = Date.now() - start;

    expect(duration).toBeLessThan(1000); // All 10 requests < 1 second
    expect(results.every(r => r.length > 0)).toBe(true);
  });
});
```

### **Integration Tests**
```typescript
// tests/integration/ui-backend.test.ts
import { render, fireEvent, waitFor } from '@testing-library/react';
import { ComplianceDashboard } from '@/components/compliance/ComplianceDashboard';

describe('UI Integration with Direct Database', () => {
  test('dashboard loads compliance data', async () => {
    const mockProperty = {
      zone: 'R2',
      constraints: { maxHeight: 9.5, maxFsr: 0.6 }
    };

    const { getByText, queryByText } = render(
      <ComplianceDashboard propertyData={mockProperty} />
    );

    // Should show loading initially
    expect(getByText('Loading compliance data...')).toBeInTheDocument();

    // Should load data without subprocess spawning
    await waitFor(() => {
      expect(queryByText('Loading compliance data...')).not.toBeInTheDocument();
      expect(getByText('Building Envelope')).toBeInTheDocument();
    }, { timeout: 1000 }); // Much faster than subprocess version
  });
});
```

---

## **SUCCESS CRITERIA**

### **Performance Metrics**
- ✅ **Provision details < 200ms** (vs 2000ms subprocess)
- ✅ **Full compliance data < 500ms** (vs 5000ms subprocess)
- ✅ **Zero subprocess spawning** (0 Python processes)
- ✅ **Connection pooling active** (20 max connections)
- ✅ **Memory usage stable** (no process buildup)

### **Reliability Metrics**
- ✅ **99%+ query success rate** under normal load
- ✅ **Graceful degradation** on database errors
- ✅ **Timeout protection** (30 seconds per CLAUDE.md)
- ✅ **Connection recovery** from network failures
- ✅ **Resource cleanup** (no connection leaks)

### **Architecture Quality**
- ✅ **UI components unchanged** (zero breaking changes)
- ✅ **API responses identical** (backward compatibility)
- ✅ **Error handling improved** (detailed error messages)
- ✅ **Cloud deployment ready** (container compatible)
- ✅ **Windows/Linux compatible** (no subprocess dependencies)

---

## **DEPLOYMENT CHECKLIST**

### **Pre-Deployment Validation**
```bash
# 1. Install dependencies
cd frontend-nextjs && npm install

# 2. Test database connection
npm run test:database

# 3. Performance benchmark
npm run test:performance

# 4. Integration test
npm run test:integration

# 5. Build verification
npm run build
```

### **Production Deployment**
```bash
# 1. Environment variables
export COMPLIANCE_ARCHITECTURE=direct_database
export DB_POOL_MAX=50

# 2. Health check
curl -f http://localhost:3007/api/compliance/dashboard

# 3. Performance monitoring
tail -f logs/performance.log
```

### **Rollback Plan**
```bash
# Emergency rollback to subprocess architecture
export COMPLIANCE_ARCHITECTURE=subprocess
systemctl restart compliance-engine
```

---

**This PRP transforms the compliance engine from subprocess-based to direct database architecture while maintaining 100% UI compatibility. It delivers cloud-ready performance with professional reliability standards.**

**Architecture Evolution: Subprocess → Direct Database → Production Ready**