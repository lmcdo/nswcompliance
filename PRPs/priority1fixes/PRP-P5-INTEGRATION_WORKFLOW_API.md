# PRP-P5: Integration - Workflow API Implementation

## OBJECTIVE
Enhance existing API endpoints with consolidated development type logic from PRP-P3 to extend current address resolution workflows without creating redundant APIs.

## SUCCESS CRITERIA
- [ ] Enhance existing /api/authoritative/compliance-check with development permissions
- [ ] Integrate consolidated dataset with existing hierarchy resolver
- [ ] Add development type logic to existing address→zone workflow
- [ ] Maintain backward compatibility with current API responses
- [ ] Achieve <2 second response time within existing API architecture

## TECHNICAL SPECIFICATION

### Phase 5A: Enhanced Existing Endpoints
```typescript
// Enhance existing endpoints instead of creating new ones
ENHANCED: /api/authoritative/compliance-check
  - Add optional development_permissions field to response
  - Add optional development_type parameter for feasibility checking

ENHANCED: /api/setbacks/calculate
  - Include development type considerations in setback calculations
  - Maintain existing response structure

NEW OPTIONAL: /api/authoritative/development-permissions/{zone}
  - Only if needed for frontend, otherwise integrate into compliance-check
```

### Phase 5B: Enhanced Existing Response Structure
```typescript
// Extend existing AuthoritativeComplianceResponse
interface EnhancedComplianceResponse extends AuthoritativeComplianceResponse {
  // Existing fields preserved
  property: PropertyIntelligence;
  zone: string;
  setbacks: SetbackResults;

  // NEW: Optional development permissions (only if requested)
  development_permissions?: {
    permitted_without_consent: string[];
    permitted_with_consent: string[];
    prohibited: string[];
    source: 'consolidated_dataset' | 'nsw_standard';
    coverage_note?: string;
  };

  // NEW: Optional feasibility check (only if development_type provided)
  feasibility_check?: {
    development_type: string;
    permission_status: 'permitted' | 'consent' | 'prohibited' | 'unknown';
    confidence: 'high' | 'medium' | 'low';
    source_provision?: string;
  };
}

// Enhanced request interface
interface EnhancedComplianceRequest {
  address: string;
  include_development_permissions?: boolean;  // NEW: Optional flag
  development_type?: string;  // NEW: Optional for feasibility check
  // All existing parameters preserved
}
```

### Phase 5C: Integration with Existing Authoritative API
```python
class EnhancedAuthoritativeComplianceAPI:
    def __init__(self):
        # Use existing services - no new dependencies
        self.existing_api = AuthoritativeComplianceAPI()
        self.dev_permissions_db = DevelopmentPermissionsDB()  # NEW: Access consolidated dataset

    async def enhanced_compliance_check(self, request: EnhancedComplianceRequest):
        # 1. Call existing compliance check (preserves all current functionality)
        base_response = await self.existing_api.get_compliance(request.address)

        # 2. Optionally add development permissions if requested
        if request.include_development_permissions:
            dev_permissions = await self.get_zone_development_permissions(base_response.zone)
            base_response.development_permissions = dev_permissions

        # 3. Optionally check feasibility if development_type provided
        if request.development_type:
            feasibility = await self.check_development_feasibility(
                base_response.zone, request.development_type
            )
            base_response.feasibility_check = feasibility

        return base_response
```

## IMPLEMENTATION STEPS

### Step 1: Create Development Permissions Database Access (30 minutes)
```python
class DevelopmentPermissionsDB:
    def __init__(self, db_connection):
        self.db = db_connection  # Use existing database connection

    def get_zone_permissions(self, zone: str) -> Dict:
        """Get development permissions for a zone from consolidated dataset"""
        query = """
        SELECT development_type, permission_status, source_type
        FROM development_permissions
        WHERE zone = ? AND confidence_score > 0.7
        ORDER BY permission_status, development_type
        """
        # Return structured permissions by status

    def check_development_feasibility(self, zone: str, development_type: str) -> Dict:
        """Check if specific development type is allowed in zone"""
        query = """
        SELECT permission_status, source_provision, confidence_score
        FROM development_permissions
        WHERE zone = ? AND development_type = ?
        ORDER BY confidence_score DESC LIMIT 1
        """
        # Return feasibility result with confidence
```

### Step 2: Enhance Existing Compliance Check Endpoint (45 minutes)
```typescript
// Enhanced /api/authoritative/compliance-check
export async function POST(request: NextRequest) {
  const {
    address,
    include_development_permissions,
    development_type
  } = await request.json();

  try {
    // 1. Call existing compliance check (maintains backward compatibility)
    const baseResponse = await getExistingComplianceCheck(address);

    // 2. Optionally add development permissions
    if (include_development_permissions) {
      const devPermissions = await getDevelopmentPermissions(baseResponse.zone);
      baseResponse.development_permissions = devPermissions;
    }

    // 3. Optionally check feasibility
    if (development_type) {
      const feasibility = await checkFeasibility(baseResponse.zone, development_type);
      baseResponse.feasibility_check = feasibility;
    }

    return NextResponse.json(baseResponse);
  } catch (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
```

### Step 3: Update Frontend Integration (25 minutes)
```typescript
// Update existing frontend components to use enhanced API
// AuthoritativeComplianceDisplay.tsx - add optional development permissions display
// PropertySearch.tsx - add option to include development permissions

// Backward compatible API calls
const basicResponse = await fetch('/api/authoritative/compliance-check', {
  method: 'POST',
  body: JSON.stringify({ address })  // Existing functionality preserved
});

// Enhanced API calls (optional)
const enhancedResponse = await fetch('/api/authoritative/compliance-check', {
  method: 'POST',
  body: JSON.stringify({
    address,
    include_development_permissions: true,  // NEW
    development_type: 'retail_premises'     // NEW
  })
});
```

### Step 4: Add Basic Conditional Logic (30 minutes)
```python
class BasicDevelopmentConditions:
    def get_basic_conditions(self, zone: str, dev_type: str) -> List[str]:
        """
        Return basic conditions from consolidated dataset
        Focus on simple, high-confidence rules from extraction
        """
        query = """
        SELECT conditions_text
        FROM development_permissions
        WHERE zone = ? AND development_type = ? AND conditions_text IS NOT NULL
        ORDER BY confidence_score DESC
        """
        # Return available conditions without complex evaluation
```

### Step 5: Testing & Documentation (25 minutes)
```python
def test_enhanced_api():
    # Test backward compatibility
    # Test optional development permissions
    # Test feasibility checking
    # Document API changes and limitations
```

## VERIFICATION CHECKLIST

### API Functionality (Realistic Scope)
- [ ] Enhanced compliance-check returns development permissions when requested
- [ ] Feasibility check works for available development types in consolidated dataset
- [ ] Existing address/compliance functionality fully preserved
- [ ] Basic conditional information returned from available data
- [ ] Error handling maintains existing robustness

### Performance Requirements
- [ ] End-to-end response time: <2 seconds for complete workflow
- [ ] Database query optimization: <500ms for development permissions
- [ ] Concurrent request handling: >10 simultaneous requests
- [ ] Memory usage: Acceptable for production environment
- [ ] API response size: <100KB for typical requests

### Integration Validation
- [ ] Existing address API functionality preserved
- [ ] NSW Planning Portal integration still works
- [ ] Setback calculator integration maintained
- [ ] Hierarchy resolver integration intact
- [ ] Frontend compatibility maintained

### Data Quality
- [ ] Development permissions accuracy: >95% correct
- [ ] Conditional logic accuracy: >90% correct evaluations
- [ ] Zone coverage: All major zones supported
- [ ] Development type coverage: >15 types supported
- [ ] Error rate: <5% of requests result in errors

## DELIVERABLES

1. **development_type_engine.py** - Core development type query engine
2. **API route implementations** - All new endpoint implementations
3. **integration_tests.py** - Comprehensive API testing suite
4. **performance_benchmarks.json** - Performance test results
5. **api_documentation.md** - Complete API documentation
6. **frontend_integration_guide.md** - Frontend usage examples
7. **deployment_checklist.md** - Production deployment requirements

## API TESTING SCENARIOS

### Integration Tests
```python
def test_what_can_i_build_workflow():
    # Test complete workflow from address to development permissions
    response = requests.post('/api/development/what-can-i-build', 
                           json={'address': '15 Norton St Leichhardt'})
    assert response.status_code == 200
    assert 'development_permissions' in response.json()
    assert response.json()['property']['zone'] == 'R2'

def test_feasibility_check():
    response = requests.post('/api/development/feasibility-check',
                           json={'address': '15 Norton St Leichhardt',
                                'development_type': 'dual_occupancy'})
    assert response.json()['feasibility_result']['permission_status'] in ['permitted', 'consent']
```

### Performance Tests
```python
def test_response_time():
    start_time = time.time()
    response = requests.post('/api/development/what-can-i-build',
                           json={'address': '15 Norton St Leichhardt'})
    execution_time = (time.time() - start_time) * 1000
    assert execution_time < 2000  # Less than 2 seconds
```

## ROLLBACK PLAN
```typescript
// If issues found, implement feature flags to disable new functionality
const ENABLE_DEVELOPMENT_TYPE_API = process.env.ENABLE_DEV_TYPE_API === 'true';

if (!ENABLE_DEVELOPMENT_TYPE_API) {
  // Return basic address resolution without development permissions
  return legacyAddressResponse(address);
}
```

## DEPENDENCIES
- **Requires:** PRP-P1 through PRP-P4 completion (all development type logic implemented)
- **Integrates with:** Existing NSW Planning Portal API, address resolution, setback calculator
- **Feeds into:** Production planner workflow deployment

## ESTIMATED TIME
**2.5 hours total**
- Development permissions database access: 30 minutes
- Enhanced compliance check endpoint: 45 minutes
- Frontend integration updates: 25 minutes
- Basic conditional logic: 30 minutes
- Testing and documentation: 25 minutes

## COMPLETION CRITERIA (Realistic Integration)
✅ Enhanced API endpoints functional with existing systems maintained
✅ Backward compatibility fully preserved
✅ Performance requirements met (<2 second response time)
✅ Basic development permissions integrated from consolidated dataset
✅ Phase 1 deployment ready with documented scope
✅ Enhanced workflow: address → zone → compliance + optional development permissions

## SUCCESS METRICS (Realistic Targets)
- **End-to-end workflow time:** <2 seconds including optional development permissions
- **API accuracy:** Available development permissions from consolidated dataset
- **Integration stability:** Zero regression in existing functionality
- **Production readiness:** Phase 1 deployment with enhanced capabilities