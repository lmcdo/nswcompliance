# Universal Technical Implementation Specification
## Systematic Engineering Standards for Professional Software Development

**Purpose**: Prevent common AI-assisted development failures through disciplined engineering practices
**Scope**: Universal application across all software projects
**Authority**: Based on proven production system standards

---

## **CORE PRINCIPLES**

### **1. ZERO MOCK DATA POLICY**
```
ABSOLUTE PROHIBITION: No mock, dummy, sample, or hardcoded data in production code paths
REQUIREMENT: All data sources must connect to real databases, APIs, or services
ENFORCEMENT: Code review gates must verify real data integration
EXCEPTIONS: None - test environments only
```

### **2. REAL SYSTEM INTEGRATION MANDATE**
```
DATABASE: Must connect to actual database with real schema and data
APIs: Must call real external services with proper error handling
SERVICES: Must integrate with actual backend services, not simulations
VALIDATION: All integrations must be verified with real data flows
```

### **3. IMPLEMENTATION COMPLETENESS STANDARD**
```
NO PARTIAL IMPLEMENTATIONS: Every feature must be fully functional
NO "TODO" OR "PLACEHOLDER" CODE: All code paths must be complete
NO COMMENTED-OUT FUNCTIONALITY: Remove or implement, never leave hanging
VERIFICATION: Manual testing required for all code paths
```

---

## **SYSTEM ARCHITECTURE REQUIREMENTS**

### **Full-Stack Architecture Pattern:**
```
┌─────────────────────────────────────────────────────────────────┐
│ FRONTEND APPLICATION │
├─────────────────────────────────────────────────────────────────┤
│ ┌────────────────────────────────────────────────────────────┐ │
│ │ CLIENT COMPONENTS (Real UI, Real Interactions) │ │
│ │ ┌──────────────┐ ┌─────────────┐ ┌─────────────────┐ │ │
│ │ │ Input │→ │ Processing │→ │ Display │ │ │
│ │ │ Components │ │ Components │ │ Components │ │ │
│ │ └──────────────┘ └─────────────┘ └─────────────────┘ │ │
│ └────────────────────────────────────────────────────────────┘ │
│ │ │
│ ↓ Server Actions / API Routes │
│ ┌────────────────────────────────────────────────────────────┐ │
│ │ SERVER COMPONENTS (Real Business Logic) │ │
│ │ ┌──────────────────────────────────────────────────────┐ │ │
│ │ │ API Routes (/api/*) │ │ │
│ │ │ /api/entity/[id] - Entity operations │ │ │
│ │ │ /api/process/execute - Business logic │ │ │
│ │ │ /api/data/query - Data operations │ │ │
│ │ └──────────────────────────────────────────────────────┘ │ │
│ └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
 │
 ┌──────────┴──────────┐
 ↓ ↓
┌──────────────────────────┐ ┌───────────────────────────────┐
│ EXTERNAL SERVICES │ │ BACKEND SERVICES │
├──────────────────────────┤ ├───────────────────────────────┤
│ Third-party APIs │ │ Business Logic Services │
│ - Real API endpoints │ │ - Real processors │
│ - Authenticated access │ │ - Real calculators │
│ - Proper error handling │ │ - Real data transformers │
└──────────────────────────┘ └───────────────────────────────┘
 │
 ↓
┌─────────────────────────────────────────────────────────────────┐
│ DATABASE (Real Production Database) │
├─────────────────────────────────────────────────────────────────┤
│ entities │ relationships │ configurations │
│ (Real records) │ (Real data) │ (Real settings) │
│ business_data │ metadata │ audit_logs │
│ (Real entries) │ (Real info) │ (Real tracking) │
└─────────────────────────────────────────────────────────────────┘
```

### **Data Flow Specification:**
```python
# 1. Frontend Request Flow
UserInput → Validation → APIRequest → Authentication

# 2. Backend Processing Flow
APIRequest → InputValidation → BusinessLogic → DatabaseQuery → ExternalAPI → ResponseAggregation

# 3. Business Processing
DatabaseQuery → BusinessRules → DataTransformation → ResultValidation → ResponseFormatting

# 4. Response Flow
FormattedResult → JSONSerialization → HTTPResponse → FrontendRendering
```

---

## **PROJECT STRUCTURE STANDARDS**

### **Mandatory Directory Structure:**
```
project-name/
├── app/ # Main application (Next.js App Router or equivalent)
│ ├── (feature-groups)/ # Logical route groupings
│ │ ├── layout.tsx # Feature-specific layouts
│ │ ├── page.tsx # Feature pages
│ │ └── [dynamic]/ # Dynamic routes
│ ├── api/ # API Routes (Server-side only)
│ │ ├── entity/
│ │ │ └── [id]/route.ts # RESTful entity operations
│ │ ├── process/
│ │ │ └── execute/route.ts # Business process endpoints
│ │ └── data/
│ │ └── query/route.ts # Data query endpoints
│ ├── globals.css # Global styles only
│ ├── layout.tsx # Root layout
│ └── page.tsx # Root page
├── components/ # Reusable components only
│ ├── ui/ # Base UI components
│ │ ├── button.tsx
│ │ ├── card.tsx
│ │ ├── input.tsx
│ │ └── loading.tsx
│ ├── feature/ # Feature-specific components
│ │ ├── FeatureDisplay.tsx
│ │ ├── FeatureForm.tsx
│ │ └── FeatureList.tsx
│ └── shared/ # Cross-feature components
│ ├── Header.tsx
│ ├── Navigation.tsx
│ └── ErrorBoundary.tsx
├── lib/ # Business logic and utilities
│ ├── api/ # API client functions
│ │ ├── entity.ts
│ │ ├── process.ts
│ │ └── types.ts
│ ├── database/ # Database layer
│ │ ├── client.ts # Database connection
│ │ ├── queries.ts # Query builders
│ │ └── migrations.ts # Schema changes
│ ├── business/ # Business logic
│ │ ├── rules.ts # Business rules
│ │ ├── validators.ts # Data validation
│ │ └── processors.ts # Data processing
│ └── utils.ts # Pure utility functions
├── types/ # TypeScript definitions
│ ├── api.ts
│ ├── business.ts
│ ├── database.ts
│ └── ui.ts
├── hooks/ # Custom React hooks (React projects)
│ ├── useEntityData.ts
│ ├── useBusinessProcess.ts
│ └── useFormValidation.ts
├── services/ # External service integrations
│ ├── third-party-api.ts
│ ├── email-service.ts
│ └── file-storage.ts
├── tests/ # Test files mirroring src structure
│ ├── components/
│ ├── lib/
│ ├── api/
│ └── integration/
├── docs/ # Documentation
├── config/ # Configuration files
├── scripts/ # Build and deployment scripts
└── README.md # Project documentation
```

### **File Naming Conventions:**
```
Components: PascalCase.tsx (UserProfile.tsx)
Hooks: camelCase.ts (useUserData.ts)
Utilities: camelCase.ts (formatDate.ts)
API Routes: route.ts (in folders)
Types: camelCase.ts (userTypes.ts)
Constants: SCREAMING_SNAKE_CASE.ts (API_ENDPOINTS.ts)
```

---

## **API IMPLEMENTATION STANDARDS**

### **API Route Template:**
```typescript
// app/api/entity/[id]/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { DatabaseClient } from '@/lib/database/client';
import { EntityValidator } from '@/lib/business/validators';
import { EntityProcessor } from '@/lib/business/processors';
import { ApiResponse, EntityRequest, EntityResponse } from '@/types/api';

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    // 1. Input Validation
    const entityId = EntityValidator.validateId(params.id);

    // 2. Authentication/Authorization
    const user = await validateUser(request);
    if (!user || !user.canAccess(entityId)) {
      return NextResponse.json(
        { success: false, error: 'Unauthorized' },
        { status: 401 }
      );
    }

    // 3. Business Logic
    const db = new DatabaseClient();
    const processor = new EntityProcessor(db);

    const entity = await processor.getEntity(entityId);

    if (!entity) {
      return NextResponse.json(
        { success: false, error: 'Entity not found' },
        { status: 404 }
      );
    }

    // 4. Response Formation
    const response: EntityResponse = {
      success: true,
      data: entity,
      metadata: {
        processed_at: new Date().toISOString(),
        version: '1.0'
      }
    };

    return NextResponse.json(response);

  } catch (error) {
    console.error('Entity retrieval error:', error);

    return NextResponse.json(
      {
        success: false,
        error: 'Internal server error',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body: EntityRequest = await request.json();

    // Input validation
    const validatedData = EntityValidator.validateCreateRequest(body);

    // Authentication
    const user = await validateUser(request);
    if (!user?.canCreate()) {
      return NextResponse.json(
        { success: false, error: 'Insufficient permissions' },
        { status: 403 }
      );
    }

    // Business processing
    const db = new DatabaseClient();
    const processor = new EntityProcessor(db);

    const result = await processor.createEntity(validatedData);

    return NextResponse.json({
      success: true,
      data: result
    });

  } catch (error) {
    console.error('Entity creation error:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}
```

### **Database Client Standards:**
```typescript
// lib/database/client.ts
export class DatabaseClient {
  private db: Database;

  constructor(dbPath?: string) {
    // MUST connect to real database - no mocks allowed
    this.db = new Database(dbPath || process.env.DATABASE_PATH);
    this.db.pragma('journal_mode = WAL'); // Performance optimization
  }

  // All queries must use prepared statements
  getEntity(id: number): Entity | null {
    const stmt = this.db.prepare(`
      SELECT e.*, m.metadata
      FROM entities e
      LEFT JOIN metadata m ON e.id = m.entity_id
      WHERE e.id = ?
      AND e.deleted_at IS NULL
      ORDER BY e.updated_at DESC
      LIMIT 1
    `);

    return stmt.get(id) as Entity | null;
  }

  // All mutations must be transactional
  createEntity(data: CreateEntityRequest): Entity {
    const transaction = this.db.transaction(() => {
      const insertStmt = this.db.prepare(`
        INSERT INTO entities (name, type, data, created_at, updated_at)
        VALUES (?, ?, ?, datetime('now'), datetime('now'))
      `);

      const result = insertStmt.run(data.name, data.type, JSON.stringify(data.data));

      const metadataStmt = this.db.prepare(`
        INSERT INTO metadata (entity_id, key, value)
        VALUES (?, ?, ?)
      `);

      for (const [key, value] of Object.entries(data.metadata || {})) {
        metadataStmt.run(result.lastInsertRowid, key, value);
      }

      return this.getEntity(result.lastInsertRowid as number);
    });

    return transaction();
  }

  close() {
    this.db.close();
  }
}
```

---

## **COMPONENT IMPLEMENTATION STANDARDS**

### **Component Template:**
```typescript
// components/feature/EntityDisplay.tsx
'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useEntityData } from '@/hooks/useEntityData';
import { EntityValidator } from '@/lib/business/validators';
import type { Entity, EntityDisplayProps } from '@/types/business';

export function EntityDisplay({
  entityId,
  onUpdate,
  loading: externalLoading = false
}: EntityDisplayProps) {
  // State management
  const {
    entity,
    loading: dataLoading,
    error,
    updateEntity
  } = useEntityData(entityId);

  const [localState, setLocalState] = useState<string>('');
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  // Effect for data synchronization
  useEffect(() => {
    if (entity && entity.name !== localState) {
      setLocalState(entity.name);
    }
  }, [entity]);

  // Event handlers
  const handleUpdate = useCallback(async (newValue: string) => {
    try {
      // Validate input
      const validation = EntityValidator.validateName(newValue);
      if (!validation.isValid) {
        setValidationErrors(validation.errors);
        return;
      }

      setValidationErrors([]);

      // Update entity
      await updateEntity({ name: newValue });

      // Notify parent
      onUpdate?.(newValue);

    } catch (error) {
      console.error('Update failed:', error);
      setValidationErrors([error.message]);
    }
  }, [updateEntity, onUpdate]);

  // Loading state
  const isLoading = externalLoading || dataLoading;
  if (isLoading) {
    return <EntityDisplaySkeleton />;
  }

  // Error state
  if (error) {
    return <EntityDisplayError error={error} />;
  }

  // Empty state
  if (!entity) {
    return <EntityDisplayEmpty />;
  }

  // Main render
  return (
    <Card>
      <CardHeader>
        <CardTitle>Entity: {entity.name}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div>
            <input
              value={localState}
              onChange={(e) => setLocalState(e.target.value)}
              className="w-full p-2 border rounded"
            />
            {validationErrors.length > 0 && (
              <div className="text-red-500 text-sm mt-1">
                {validationErrors.map((error, i) => (
                  <div key={i}>{error}</div>
                ))}
              </div>
            )}
          </div>

          <Button
            onClick={() => handleUpdate(localState)}
            disabled={localState === entity.name || validationErrors.length > 0}
          >
            Update Entity
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// Required sub-components
function EntityDisplaySkeleton() {
  return (
    <Card>
      <CardHeader>
        <div className="h-6 bg-gray-200 rounded animate-pulse" />
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <div className="h-4 bg-gray-200 rounded animate-pulse" />
          <div className="h-8 bg-gray-200 rounded animate-pulse" />
        </div>
      </CardContent>
    </Card>
  );
}

function EntityDisplayError({ error }: { error: string }) {
  return (
    <Card className="border-red-200 bg-red-50">
      <CardContent className="p-4">
        <div className="text-red-800">
          <div className="font-medium">Error loading entity</div>
          <div className="text-sm mt-1">{error}</div>
        </div>
      </CardContent>
    </Card>
  );
}

function EntityDisplayEmpty() {
  return (
    <Card>
      <CardContent className="p-6 text-center text-gray-500">
        <div>No entity data available</div>
      </CardContent>
    </Card>
  );
}
```

### **Custom Hook Standards:**
```typescript
// hooks/useEntityData.ts
import { useState, useCallback, useEffect } from 'react';
import { EntityAPI } from '@/lib/api/entity';
import type { Entity, UpdateEntityRequest } from '@/types/business';

export function useEntityData(entityId?: number) {
  const [entity, setEntity] = useState<Entity | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchEntity = useCallback(async (id: number) => {
    setLoading(true);
    setError(null);

    try {
      const response = await EntityAPI.getById(id);

      if (response.success) {
        setEntity(response.data);
      } else {
        throw new Error(response.error || 'Failed to fetch entity');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      setEntity(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const updateEntity = useCallback(async (updates: UpdateEntityRequest) => {
    if (!entity) return;

    setLoading(true);
    setError(null);

    try {
      const response = await EntityAPI.update(entity.id, updates);

      if (response.success) {
        setEntity(response.data);
      } else {
        throw new Error(response.error || 'Failed to update entity');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Update failed';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [entity]);

  useEffect(() => {
    if (entityId) {
      fetchEntity(entityId);
    }
  }, [entityId, fetchEntity]);

  return {
    entity,
    loading,
    error,
    updateEntity,
    refetch: () => entityId ? fetchEntity(entityId) : null
  };
}
```

---

## **TESTING REQUIREMENTS**

### **Test Coverage Standards:**
```
MINIMUM COVERAGE: 85% for all production code
CRITICAL PATH COVERAGE: 100% for business logic
API ENDPOINT COVERAGE: 100% for all routes
COMPONENT COVERAGE: 90% for UI components
```

### **Unit Test Template:**
```typescript
// tests/lib/business/validators.test.ts
import { describe, test, expect, beforeEach } from '@jest/globals';
import { EntityValidator } from '@/lib/business/validators';

describe('EntityValidator', () => {
  describe('validateId', () => {
    test('accepts valid positive integer', () => {
      const result = EntityValidator.validateId('123');
      expect(result).toBe(123);
    });

    test('rejects negative numbers', () => {
      expect(() => EntityValidator.validateId('-1')).toThrow('ID must be positive');
    });

    test('rejects non-numeric strings', () => {
      expect(() => EntityValidator.validateId('abc')).toThrow('ID must be numeric');
    });

    test('rejects empty string', () => {
      expect(() => EntityValidator.validateId('')).toThrow('ID is required');
    });
  });

  describe('validateName', () => {
    test('accepts valid name', () => {
      const result = EntityValidator.validateName('Valid Entity Name');
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    test('rejects empty name', () => {
      const result = EntityValidator.validateName('');
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Name is required');
    });

    test('rejects name too long', () => {
      const longName = 'a'.repeat(101);
      const result = EntityValidator.validateName(longName);
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Name must be 100 characters or less');
    });
  });
});
```

### **Integration Test Template:**
```typescript
// tests/integration/api/entity.test.ts
import { describe, test, expect, beforeAll, afterAll } from '@jest/globals';
import { testClient } from '@/tests/utils/test-client';
import { DatabaseTestUtils } from '@/tests/utils/database';

describe('Entity API Integration', () => {
  beforeAll(async () => {
    await DatabaseTestUtils.setupTestDatabase();
  });

  afterAll(async () => {
    await DatabaseTestUtils.cleanupTestDatabase();
  });

  test('complete entity lifecycle', async () => {
    // Create entity
    const createResponse = await testClient.post('/api/entity', {
      name: 'Test Entity',
      type: 'test',
      data: { key: 'value' }
    });

    expect(createResponse.status).toBe(200);
    expect(createResponse.data.success).toBe(true);

    const entityId = createResponse.data.data.id;

    // Get entity
    const getResponse = await testClient.get(`/api/entity/${entityId}`);

    expect(getResponse.status).toBe(200);
    expect(getResponse.data.success).toBe(true);
    expect(getResponse.data.data.name).toBe('Test Entity');

    // Update entity
    const updateResponse = await testClient.patch(`/api/entity/${entityId}`, {
      name: 'Updated Entity'
    });

    expect(updateResponse.status).toBe(200);
    expect(updateResponse.data.data.name).toBe('Updated Entity');

    // Delete entity
    const deleteResponse = await testClient.delete(`/api/entity/${entityId}`);
    expect(deleteResponse.status).toBe(200);

    // Verify deletion
    const getDeletedResponse = await testClient.get(`/api/entity/${entityId}`);
    expect(getDeletedResponse.status).toBe(404);
  });
});
```

---

## **ERROR HANDLING STANDARDS**

### **Error Handling Template:**
```typescript
// lib/business/error-handler.ts
export class BusinessError extends Error {
  constructor(
    message: string,
    public code: string,
    public statusCode: number = 400,
    public details?: any
  ) {
    super(message);
    this.name = 'BusinessError';
  }
}

export class ValidationError extends BusinessError {
  constructor(message: string, public fields: string[] = []) {
    super(message, 'VALIDATION_ERROR', 400, { fields });
    this.name = 'ValidationError';
  }
}

export class NotFoundError extends BusinessError {
  constructor(resource: string, id: string | number) {
    super(`${resource} with ID ${id} not found`, 'NOT_FOUND', 404);
    this.name = 'NotFoundError';
  }
}

export class UnauthorizedError extends BusinessError {
  constructor(message: string = 'Unauthorized access') {
    super(message, 'UNAUTHORIZED', 401);
    this.name = 'UnauthorizedError';
  }
}

export function handleApiError(error: unknown): {
  message: string;
  code: string;
  statusCode: number;
  details?: any;
} {
  if (error instanceof BusinessError) {
    return {
      message: error.message,
      code: error.code,
      statusCode: error.statusCode,
      details: error.details
    };
  }

  if (error instanceof Error) {
    console.error('Unexpected error:', error);
    return {
      message: 'Internal server error',
      code: 'INTERNAL_ERROR',
      statusCode: 500,
      details: process.env.NODE_ENV === 'development' ? error.stack : undefined
    };
  }

  console.error('Unknown error type:', error);
  return {
    message: 'An unexpected error occurred',
    code: 'UNKNOWN_ERROR',
    statusCode: 500
  };
}
```

### **API Error Response Format:**
```typescript
// All API responses must follow this format
interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  code?: string;
  details?: any;
  timestamp: string;
}

// Success response
{
  "success": true,
  "data": { /* actual data */ },
  "timestamp": "2023-12-07T10:30:00.000Z"
}

// Error response
{
  "success": false,
  "error": "Validation failed",
  "code": "VALIDATION_ERROR",
  "details": {
    "fields": ["name", "email"]
  },
  "timestamp": "2023-12-07T10:30:00.000Z"
}
```

---

## **VALIDATION STANDARDS**

### **Input Validation Template:**
```typescript
// lib/business/validators.ts
import { z } from 'zod';

export class ValidationResult {
  constructor(
    public isValid: boolean,
    public errors: string[] = [],
    public data?: any
  ) {}
}

export class EntityValidator {
  private static nameSchema = z.string()
    .min(1, 'Name is required')
    .max(100, 'Name must be 100 characters or less')
    .regex(/^[a-zA-Z0-9\s\-_]+$/, 'Name contains invalid characters');

  private static idSchema = z.number()
    .int('ID must be an integer')
    .positive('ID must be positive');

  static validateId(id: string | number): number {
    const numericId = typeof id === 'string' ? parseInt(id, 10) : id;

    if (isNaN(numericId)) {
      throw new ValidationError('ID must be numeric');
    }

    const result = this.idSchema.safeParse(numericId);
    if (!result.success) {
      throw new ValidationError(result.error.issues[0].message);
    }

    return result.data;
  }

  static validateName(name: string): ValidationResult {
    const result = this.nameSchema.safeParse(name);

    if (result.success) {
      return new ValidationResult(true, [], result.data);
    }

    const errors = result.error.issues.map(issue => issue.message);
    return new ValidationResult(false, errors);
  }

  static validateCreateRequest(data: any): CreateEntityRequest {
    const schema = z.object({
      name: this.nameSchema,
      type: z.string().min(1, 'Type is required'),
      data: z.record(z.any()).optional(),
      metadata: z.record(z.string()).optional()
    });

    const result = schema.safeParse(data);
    if (!result.success) {
      const errors = result.error.issues.map(issue =>
        `${issue.path.join('.')}: ${issue.message}`
      );
      throw new ValidationError('Validation failed', errors);
    }

    return result.data;
  }
}
```

---

## **SECURITY REQUIREMENTS**

### **Authentication Template:**
```typescript
// lib/auth/authentication.ts
export async function validateUser(request: NextRequest): Promise<User | null> {
  try {
    const token = extractToken(request);
    if (!token) return null;

    const decoded = jwt.verify(token, process.env.JWT_SECRET!);
    const user = await getUserFromToken(decoded);

    return user;
  } catch (error) {
    console.error('Authentication error:', error);
    return null;
  }
}

export function requireAuth(handler: Function) {
  return async (request: NextRequest, context: any) => {
    const user = await validateUser(request);
    if (!user) {
      return NextResponse.json(
        { success: false, error: 'Authentication required' },
        { status: 401 }
      );
    }

    // Add user to context
    return handler(request, { ...context, user });
  };
}

export function requirePermission(permission: string) {
  return (handler: Function) => {
    return async (request: NextRequest, context: any) => {
      const user = await validateUser(request);
      if (!user || !user.hasPermission(permission)) {
        return NextResponse.json(
          { success: false, error: 'Insufficient permissions' },
          { status: 403 }
        );
      }

      return handler(request, { ...context, user });
    };
  };
}
```

### **Input Sanitization:**
```typescript
// lib/security/sanitization.ts
export class InputSanitizer {
  static sanitizeString(input: string): string {
    return input
      .trim()
      .replace(/[<>]/g, '') // Remove potential HTML tags
      .replace(/'/g, "''") // Escape single quotes for SQL
      .substring(0, 1000); // Limit length
  }

  static sanitizeNumber(input: any): number {
    const num = parseFloat(input);
    if (isNaN(num) || !isFinite(num)) {
      throw new ValidationError('Invalid number format');
    }
    return num;
  }

  static sanitizeEmail(input: string): string {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const sanitized = this.sanitizeString(input).toLowerCase();

    if (!emailRegex.test(sanitized)) {
      throw new ValidationError('Invalid email format');
    }

    return sanitized;
  }
}
```

---

## **PERFORMANCE STANDARDS**

### **Performance Requirements:**
```typescript
// config/performance.ts
export const PERFORMANCE_REQUIREMENTS = {
  api_response_time: {
    simple_queries: 200, // ms
    complex_queries: 1000, // ms
    file_uploads: 5000, // ms
    reports: 10000, // ms
  },
  database_query_time: {
    single_table: 50, // ms
    join_query: 200, // ms
    complex_aggregation: 500, // ms
  },
  frontend_metrics: {
    first_contentful_paint: 1500, // ms
    largest_contentful_paint: 2500, // ms
    cumulative_layout_shift: 0.1, // score
    time_to_interactive: 3000, // ms
  },
  concurrent_users: 100,
  requests_per_second: 50,
  error_rate_threshold: 0.01 // 1%
};
```

### **Caching Strategy:**
```typescript
// lib/cache/strategy.ts
export class CacheManager {
  private cache: Map<string, { data: any; expires: number }> = new Map();

  set(key: string, data: any, ttlMs: number = 3600000): void {
    const expires = Date.now() + ttlMs;
    this.cache.set(key, { data, expires });
  }

  get(key: string): any | null {
    const cached = this.cache.get(key);
    if (!cached || cached.expires < Date.now()) {
      this.cache.delete(key);
      return null;
    }
    return cached.data;
  }

  async getOrSet<T>(
    key: string,
    fetcher: () => Promise<T>,
    ttlMs: number = 3600000
  ): Promise<T> {
    const cached = this.get(key);
    if (cached) return cached;

    const data = await fetcher();
    this.set(key, data, ttlMs);
    return data;
  }
}
```

---

## **DEPLOYMENT STANDARDS**

### **Environment Configuration:**
```bash
# .env.production template
# Database
DATABASE_URL=postgresql://user:pass@host:port/dbname
DATABASE_POOL_SIZE=20
DATABASE_TIMEOUT=30

# API Configuration
API_HOST=0.0.0.0
API_PORT=3000
API_WORKERS=4

# Security
JWT_SECRET=your-super-secret-jwt-key
ENCRYPTION_KEY=your-32-char-encryption-key
SESSION_SECRET=your-session-secret

# External Services
THIRD_PARTY_API_KEY=your-api-key
EMAIL_SERVICE_KEY=your-email-key
FILE_STORAGE_KEY=your-storage-key

# Monitoring
SENTRY_DSN=your-sentry-dsn
LOG_LEVEL=info
METRICS_ENABLED=true

# Feature Flags
FEATURE_NEW_UI=true
FEATURE_ANALYTICS=true
```

### **Health Check Implementation:**
```typescript
// app/api/health/route.ts
export async function GET() {
  const checks = {
    database: await checkDatabase(),
    external_apis: await checkExternalAPIs(),
    cache: await checkCache(),
    disk_space: checkDiskSpace(),
    memory_usage: checkMemoryUsage()
  };

  const allHealthy = Object.values(checks).every(check => check.healthy);

  return NextResponse.json(
    {
      status: allHealthy ? 'healthy' : 'degraded',
      checks,
      timestamp: new Date().toISOString(),
      version: process.env.APP_VERSION || '1.0.0'
    },
    { status: allHealthy ? 200 : 503 }
  );
}
```

---

## **QUALITY GATES**

### **Pre-Deployment Checklist:**
```
☐ All tests passing (unit, integration, e2e)
☐ Code coverage above 85%
☐ No critical security vulnerabilities
☐ Performance benchmarks met
☐ Database migrations tested
☐ Environment variables configured
☐ Health checks functional
☐ Error handling verified
☐ Logging configured
☐ Monitoring setup
☐ Documentation updated
☐ Rollback plan prepared
```

### **Code Quality Standards:**
```python
# quality_gates.py
QUALITY_GATES = {
  'test_coverage': 85, # Minimum test coverage %
  'cyclomatic_complexity': 10, # Maximum complexity per function
  'code_duplication': 5, # Maximum duplication %
  'security_issues': 0, # Critical security issues
  'performance_regression': 10, # Maximum % performance regression
  'documentation_coverage': 80, # Minimum documentation %
  'type_safety': 100 # TypeScript strict mode compliance
}
```

---

## **SUCCESS METRICS**

### **Technical Metrics:**
- Zero mock data in production code paths
- 100% real system integration
- All API endpoints respond within SLA
- Database queries optimized with indexes
- 95%+ test coverage for critical paths
- Zero critical security vulnerabilities

### **Operational Metrics:**
- 99.9% uptime during business hours
- <1% error rate under normal load
- Performance requirements met
- Automated deployment pipeline functional
- Monitoring and alerting operational

---

**This specification provides the systematic engineering foundation for professional-grade software development, eliminating common AI-assisted development failures through disciplined practices and comprehensive standards.**