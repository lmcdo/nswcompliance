# 🎯 COMPLIANCE ENGINE FRONTEND-BACKEND INTERFACE SPECIFICATION

## Executive Summary

Complete technical mapping of all API routes, database clients, data flows, and interfaces between the Next.js frontend and PostgreSQL/Python backend systems.

## 📋 API ENDPOINTS CATALOG

### Property & Planning APIs

#### 1. General Property Data
- **`GET /api/property`**
  - **Input**: `?address=<string>`
  - **Backend**: NSW Planning Portal API
  - **Output**: Comprehensive property data with planning layers
  - **Database**: None (external API only)

#### 2. Specific Property Lookup
- **`GET /api/property/[address]`**
  - **Backend**: NSW Planning Portal (multiple endpoints)
  - **Flow**: Address → Property ID → Lot geometry → Planning controls
  - **Fallback**: Manual zone input
  - **Output**: PropertyIntelligenceResponse with lot geometry

#### 3. Lot Geometry
- **`GET /api/property/lot-geometry`**
  - **Backend**: NSW Planning Portal lot API
  - **Purpose**: Geometric calculations for setback analysis

### Compliance Assessment APIs

#### 4. Live Compliance Check
- **`POST /api/compliance/live-check`**
  - **Backend**: Python subprocess (`services/live_compliance_engine.py`)
  - **Timeout**: 30 seconds
  - **Input**: Address, development parameters
  - **Output**: FSR, height, site coverage compliance

#### 5. Enhanced Compliance
- **`POST /api/compliance/enhanced`**
  - **Backend**: Mock data (Python backend "to be fixed")
  - **Input**: Property ID, zone, development type
  - **Output**: Tiered provisions (T1-T5) with feasibility

#### 6. Compliance Dashboard
- **`GET /api/compliance/dashboard`** / **`POST /api/compliance/dashboard`**
  - **Backend**: ComplianceDataClient → PostgreSQL
  - **Database Tables**: `regulatory_provisions`
  - **Input**: zone, heritage, maxHeight, maxFsr, basixWater, lga
  - **Output**: ComplianceData with building_envelope, environmental, special_provisions

### Provision & Regulatory APIs

#### 7. Provision Search
- **`GET /api/provisions`**
  - **Backend**: Python subprocess (`services/provision_search.py`)
  - **Database**: PostgreSQL via subprocess
  - **Input**: query, filters (document types, categories, zones)
  - **Timeout**: Standard subprocess timeout
  - **Fallback**: Empty results on failure

#### 8. Clause Lookup
- **`GET /api/clause/[id]`**
  - **Backend**: Direct PostgreSQL via DatabaseClient
  - **Table**: `regulatory_provisions`
  - **Output**: Full clause text with authority level (SEPP > LEP > DCP)

### Assessment Workflow APIs

#### 9. Assessment Gateway
- **`POST /api/assessment`**
  - **Actions**:
    - `loadProperty`: NSW Planning Portal
    - `getCompliance`: `/api/compliance/enhanced`
    - `searchProvisions`: `/api/provisions`
  - **Pattern**: Gateway orchestrating multiple APIs

#### 10. Version Compliance
- **`POST /api/assessment/version-compliance`**
  - **Purpose**: Version-specific compliance checking

### Setback Calculation APIs

#### 11. Zone Setback Calculation
- **`POST /api/setbacks/calculate`**
  - **Architecture**: PRP-K7 Zone-Aware Development Type System
  - **Backend**: PRPK7DatabaseClient → PostgreSQL
  - **Tables**: `zone_setback_rules`, `regulatory_provisions`
  - **Flow**: Zone query → Group by dev type → Legal hierarchy → Buildable area
  - **Output**: Grouped setbacks by development type with legal authority

### Transport-Oriented Development APIs

#### 12. TOD Parking Calculator
- **`POST /api/tod/parking-calculator`**
  - **Logic**: Pure calculation (no database)
  - **Input**: Development type, unit count, parking rate
  - **Reductions**: Transport proximity (rail, bus)

#### 13. Parking Rates & Transport
- **`GET /api/tod/parking-rates`** - Parking rate lookup
- **`GET /api/tod/transport-autocomplete`** - Transport stop search

### Reporting & Export APIs

#### 14. Report Generation
- **`POST /api/reports/generate`**
  - **Backend**: ReportGenerator service
  - **Input**: Template ID, property data
  - **Output**: Structured compliance reports

#### 15. Report Export
- **`POST /api/reports/export`** - Report export functionality

### Health & Monitoring APIs

#### 16. Health Checks
- **`GET /api/health`** - Comprehensive health monitoring
  - **Types**: Liveness, readiness, full checks
  - **Monitors**: Database, external APIs, environment, filesystem, performance
  - **Architecture**: PRP-A3 enterprise health monitoring

#### 17. Performance Metrics
- **`GET /api/health/metrics`** - Detailed performance metrics
- **`GET /api/versions`** - System version information

### Authoritative APIs

#### 18. Authoritative Compliance
- **`POST /api/authoritative/compliance-check`**
  - **Purpose**: Final compliance determination with legal authority

## 🗄️ DATABASE CLIENT ARCHITECTURE

### Direct PostgreSQL Clients

#### 1. DatabaseClient (`lib/database/client.ts`)
- **Type**: Direct node-pg connection
- **Purpose**: PRP-K2 bulletproof PostgreSQL integration
- **Features**: Domain-aware hierarchical queries, cross-contamination prevention
- **Connection Pool**: Max 20 connections, 30-second timeouts

**Tables Accessed**:
- `development_controls` - Planning controls by zone
- `regulatory_provisions` - Full regulatory text
- `quantitative_standards` - Numeric requirements
- `zone_setback_rules` - Merged setback rules with quality tiers
- `kg_relationships` - Knowledge graph relationships

**Key Methods**:
- `getHierarchicalSetbackControls()` - Domain-aware setback queries
- `getZoneSetbackRules()` - Zone rules with confidence scores
- `searchProvisions()` - Full-text provision search
- `getDatabaseStats()` - Table counts and metrics

#### 2. PostgreSQLComplianceClient (`lib/database/postgres-compliance-client.ts`)
- **Type**: PRP-A2 architecture refactor
- **Purpose**: Replace Python subprocess with direct TypeScript integration
- **Performance**: 150ms vs 5000ms subprocess improvement
- **CLAUDE.md Compliant**: 30-second timeouts, safety monitoring

**Key Methods**:
- `getProvisionDetails()` - REPLACES Python subprocess
- `getSetbackProvisions()` - Direct setback queries
- `getComplianceData()` - Main compliance data retrieval
- `healthCheck()` - Connection pool monitoring

#### 3. PostgresClient (`lib/database/postgres-client.ts`)
- **Type**: Simplified PostgreSQL client
- **Tables**: `regulatory_provisions_clean` (cleaned dataset)
- **Purpose**: Basic database operations

#### 4. PRPK7DatabaseClient (`lib/database/prp-k7-client.ts`)
- **Purpose**: PRP-K7 Zone-Aware Development Type System
- **Specialization**: Setback calculations grouped by development type
- **Key Feature**: No aggregation - returns all provisions for transparency

### Subprocess-Based Clients

#### 5. ComplianceDataClient (`lib/database/compliance-client.ts`)
- **Type**: Python subprocess spawning
- **CLAUDE.md Compliant**: 30-second timeouts, safety monitoring
- **Backend Scripts**: `get_provision_details.py`, `get_setback_provisions.py`
- **Safety**: Graceful degradation, timeout handling, process cleanup

## 📊 DATABASE SCHEMA ACCESS PATTERNS

### Core Tables & Usage

#### `regulatory_provisions` (22,105 rows)
```sql
-- Fields: id, ref_number, provision_text, document_id, domain_classification
-- Used by: All clause lookups, provision searches
```

#### `development_controls` (4,526 rows)
```sql
-- Fields: provision_id, control_type, value_numeric, zone_applicable, confidence_score
-- Used by: Setback and planning control queries
```

#### `zone_setback_rules` (6 rows)
```sql
-- Fields: zone, council, boundary_type, base_value, authority_type, precedence_level
-- Used by: PRP-K3 unified setback rules, quality tiers (verified, high-confidence, approximate)
```

#### `quantitative_standards` (832 rows)
```sql
-- Fields: numeric_value, unit, qualifier, context, confidence_score
-- Used by: Numeric requirements extraction
```

#### `kg_relationships` (2,734 rows)
```sql
-- Fields: subject_text, predicate, object_text, confidence_score
-- Used by: Knowledge graph relationships
```

#### Additional Tables
- `contextual_guidance_real` (6,655 rows) - Guidance and context
- `visual_elements_real` (3,017 rows) - OCR extracted visual content
- `development_permissions` (221 rows) - Zone/development type permissions
- `documents` (274 rows) - Document metadata
- `sepp_lep_overrides` (91 rows) - SEPP/LEP hierarchical overrides

## 🔄 DATA FLOW PATTERNS

### 1. Property Intelligence Flow
```
Frontend → /api/property/[address] → NSW Planning Portal API → Property Data
                                  ↓
Frontend ← Comprehensive Property Data ← Planning Controls Extraction
```

### 2. Compliance Assessment Flow
```
Frontend → /api/compliance/enhanced → Mock Data (temporary)
Frontend → /api/compliance/live-check → Python Subprocess → Live Compliance Engine
Frontend → /api/compliance/dashboard → ComplianceDataClient → PostgreSQL
```

### 3. Setback Calculation Flow
```
Frontend → /api/setbacks/calculate → PRPK7DatabaseClient → PostgreSQL
                                   ↓
Zone-Specific Rules ← Domain-Aware Queries ← Cross-Contamination Prevention
                                   ↓
Frontend ← Grouped by Development Type ← Legal Hierarchy Applied (SEPP > LEP > DCP)
```

### 4. Provision Search Flow
```
Frontend → /api/provisions → Python Subprocess → provision_search.py → PostgreSQL
                          ↓
Frontend ← JSON Results ← Script Output ← Real Database Query
```

### 5. Clause Lookup Flow
```
Frontend → /api/clause/[id] → DatabaseClient → Direct PostgreSQL Query
                            ↓
Frontend ← Full Clause Text ← Authority Level Classification (SEPP > LEP > DCP)
```

## 🔌 WEBSOCKET ARCHITECTURE

### ComplianceWebSocketManager
- **Endpoint Pattern**: `/api/compliance/ws/{assessmentId}`
- **Features**:
  - Automatic reconnection with exponential backoff
  - Connection pooling per assessment
  - Graceful degradation on connection failure
- **Message Types**: ComplianceUpdate events
- **Lifecycle**: Auto-cleanup on page unload

## ⚡ ERROR HANDLING PATTERNS

### 1. Graceful Degradation
- **Database Failures**: Return empty arrays instead of throwing errors
- **API Unavailable**: Fallback to manual input modes
- **Timeout Handling**: Promise.race with timeout promises

### 2. CLAUDE.md Safety Compliance
- **30-second timeouts**: All database operations
- **Safety monitoring**: Logging and status verification
- **Subprocess cleanup**: Proper process termination

### 3. Hierarchical Fallbacks
- **NSW Planning API**: Fallback to manual zone selection
- **Database Queries**: Multiple fallback levels (SEPP → LEP → DCP)
- **Subprocess Failures**: Switch to direct database queries

## 🔒 SECURITY & PERFORMANCE

### Connection Management
- **Pool Limits**: Maximum 20 connections per client
- **Timeouts**: 30-second limit on all operations
- **Idle Management**: 30-second idle timeout
- **SSL**: Production SSL with certificate validation disabled

### Performance Optimizations
- **Parallel Queries**: Promise.all for multiple database operations
- **Connection Pooling**: Reuse of database connections
- **Direct Database**: PRP-A2 eliminates subprocess overhead (150ms vs 5000ms)
- **Caching**: Assessment cache and storage management

## 🌐 EXTERNAL INTEGRATION POINTS

### NSW Planning Portal API
- **Base URL**: `https://api.apps1.nsw.gov.au/planning`
- **Endpoints**:
  - `/address` - Property lookup
  - `/lot` - Lot geometry
  - `/layerintersect` - Planning controls
- **Headers**: Origin and Referer for CORS
- **Fallback**: Manual input when unavailable

### Google Maps API
- **Purpose**: Address geocoding and mapping
- **Integration**: Health check monitoring
- **Key**: Environment variable `GOOGLE_MAPS_API_KEY`

## 🏗️ DEVELOPMENT ARCHITECTURE (PRP System)

### Project Requirement Phases
- **PRP-A2**: Architecture refactor (subprocess → direct DB)
- **PRP-A3**: Cloud deployment preparation with health checks
- **PRP-K2**: Bulletproof PostgreSQL integration
- **PRP-K3**: Zone-specific calculation engine
- **PRP-K6**: Hierarchical legal compliance engine
- **PRP-K7**: Zone-aware development type system

### Code Organization
- **API Routes**: `/app/api/**/route.ts` - Next.js App Router pattern
- **Database Clients**: `/lib/database/` - Separated by connection type
- **Types**: `/types/` - TypeScript definitions for all interfaces
- **Services**: Python backends in root directory

## 📈 INTERFACE SUMMARY

### Total API Endpoints: 18
- **Property APIs**: 3
- **Compliance APIs**: 3
- **Provision APIs**: 2
- **Assessment APIs**: 2
- **Setback APIs**: 1
- **TOD APIs**: 3
- **Reporting APIs**: 2
- **Health APIs**: 2

### Database Clients: 5
- **Direct PostgreSQL**: 4 clients
- **Subprocess-based**: 1 client

### Database Tables Accessed: 24
- **Core Tables**: 10 heavily used
- **Supporting Tables**: 14 additional

### External APIs: 2
- **NSW Planning Portal**: Primary data source
- **Google Maps**: Geocoding and mapping

This architecture demonstrates a sophisticated compliance system balancing performance, reliability, and legal accuracy through multiple data access layers, fallback mechanisms, and real-time capabilities.