# Phase 2: API Endpoints for Data Linkage

## Overview
Phase 2 builds API endpoints that leverage the linking tables created in Phase 1. These endpoints provide fast, indexed queries for cross-references, zone applicability, control codes, and enhanced provision data.

## Endpoints Created

### 1. Cross-Reference Resolution API
**Endpoint:** `/api/provisions/cross-references`

**Purpose:** Returns all cross-references for a provision with resolution status

**Query Parameters:**
- `provision_id` (required): Source provision ID
- `type` (optional): Filter by reference type (section, clause, figure, etc.)
- `resolved_only` (optional): Only return resolved references

**Example:**
```
GET /api/provisions/cross-references?provision_id=123&resolved_only=true
```

**Response:**
```json
{
  "success": true,
  "data": {
    "provisionId": 123,
    "crossReferences": [
      {
        "referenceType": "section",
        "referenceNumber": "8.3",
        "targetProvisionId": 456,
        "targetReference": "8.3",
        "resolutionStatus": "resolved",
        "resolutionConfidence": 1.0,
        "isMandatory": true
      }
    ],
    "totalCount": 5,
    "resolvedCount": 3
  },
  "meta": {
    "responseTimeMs": 45
  }
}
```

### 2. Zone Applicability Query API
**Endpoint:** `/api/provisions/zone-applicability`

**Purpose:** Returns provisions applicable to a zone (handles NULL zones via Phase 1 applicability rules)

**Query Parameters:**
- `zone` (required): Zone code (R2, B4, etc.)
- `lga` (optional): LGA name filter
- `document_type` (optional): SEPP, LEP, or DCP
- `limit` (optional): Max results (default 50)

**Example:**
```
GET /api/provisions/zone-applicability?zone=R2&document_type=DCP&limit=20
```

**Response:**
```json
{
  "success": true,
  "data": {
    "provisions": [
      {
        "provisionId": 789,
        "refNumber": "3.2.1",
        "appliesToZone": "R2",
        "appliesToAllZones": false,
        "applicabilitySource": "explicit_zone",
        "confidenceScore": 1.0,
        "provisionCategory": "numeric_control",
        "displayPriority": 2
      }
    ],
    "byPriority": {
      "1": [...],
      "2": [...]
    },
    "totalCount": 15
  },
  "meta": {
    "responseTimeMs": 68,
    "nullZonesHandled": true
  }
}
```

### 3. Control Code Search API
**Endpoint:** `/api/provisions/control-codes`

**Purpose:** Search provisions by individual control codes (resolves multi-code provisions like C17, C18, C19)

**Query Parameters:**
- `code` (optional): Specific code to search (C17, H01, etc.)
- `control_type` (optional): Type filter (setback, height, fsr, parking, etc.)
- `zone` (optional): Zone filter
- `limit` (optional): Max results (default 50)

**Example:**
```
GET /api/provisions/control-codes?code=C17&zone=R2
```

**Response:**
```json
{
  "success": true,
  "data": {
    "provisions": [
      {
        "provisionId": 234,
        "code": "C17",
        "codeGroup": "C17-C22",
        "controlType": "setback",
        "refNumber": "3.4.2",
        "zone": "R2"
      }
    ],
    "byControlType": {
      "setback": [...],
      "height": [...]
    },
    "byCodeGroup": {
      "C17-C22": [...]
    },
    "totalCount": 8
  },
  "meta": {
    "responseTimeMs": 32,
    "multiCodeProvisionsExpanded": true
  }
}
```

### 4. Enhanced Provision API
**Endpoint:** `/api/provisions/[id]/enhanced`

**Purpose:** Single query returning provision with all linked data (cross-references, applicability, control codes)

**Example:**
```
GET /api/provisions/123/enhanced
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 123,
    "refNumber": "3.2.1",
    "provisionText": "...",
    "provisionCategory": "numeric_control",
    "displayPriority": 2,
    "isMandatory": true,

    "applicability": {
      "explicitZone": "R2",
      "appliesToAllZones": false,
      "applicabilitySource": "explicit_zone",
      "confidenceScore": 1.0
    },

    "crossReferences": {
      "total": 3,
      "resolved": 2,
      "references": [...]
    },

    "controlCodes": {
      "total": 6,
      "codeGroup": "C17-C22",
      "controlType": "setback",
      "codes": ["C17", "C18", "C19", "C20", "C21", "C22"]
    }
  },
  "meta": {
    "responseTimeMs": 89,
    "linkedDataLoaded": true
  }
}
```

## Performance Benchmarks

All endpoints use indexed queries from Phase 1 linking tables:

- Cross-reference lookup: <100ms (target: <50ms)
- Zone applicability: <100ms
- Control code search: <50ms
- Enhanced provision: <100ms (single query with 3 JOINs)

## Testing

Run integration tests:
```bash
python phase2_api_tests.py
```

**Prerequisites:**
- Next.js dev server running (`npm run dev` in frontend-nextjs/)
- PostgreSQL database with Phase 1 linking tables populated

## Frontend Integration

### Example Usage:

```typescript
// Get cross-references for a provision
const { data } = await fetch(`/api/provisions/cross-references?provision_id=${id}`)
  .then(r => r.json());

// Get provisions for zone with priority ordering
const { data } = await fetch(`/api/provisions/zone-applicability?zone=R2`)
  .then(r => r.json());
const highPriority = data.byPriority[1]; // Display first
const lowPriority = data.byPriority[5];  // Lazy load

// Search by control code
const { data } = await fetch(`/api/provisions/control-codes?code=C17`)
  .then(r => r.json());

// Get comprehensive provision data
const { data } = await fetch(`/api/provisions/${id}/enhanced`)
  .then(r => r.json());
```

## Migration from Existing Endpoints

The new endpoints complement existing `/api/provisions/route.ts`:

- **Existing:** Text search, document type filtering (uses `ProvisionSearchClient`)
- **New:** Zone-based queries, cross-reference resolution, control code search

Both can coexist. Progressive migration:
1. Use new endpoints for zone-based queries
2. Use enhanced endpoint for provision detail pages
3. Keep existing endpoint for free-text search

## Next Steps

1. Update `ComplianceDashboard` to use zone-applicability endpoint
2. Add cross-reference inline display in provision cards
3. Implement control code filters in search UI
4. Add lazy loading for low-priority provisions
5. (Optional) Implement provision diagram linking (Phase 3)
