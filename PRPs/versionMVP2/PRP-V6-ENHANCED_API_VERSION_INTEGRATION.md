# PRP-V6-Enhanced: API Version Integration

## Objective
Make all API endpoints version-aware by adding version parameters, updating response formats to include version metadata, and ensuring backward compatibility with existing API consumers.

## Prerequisites
- PRP-V4-Enhanced completed (baseline versions exist)
- PRP-V5-Enhanced completed (change tracking operational)
- Existing API endpoints functional
- Frontend applications using current API structure

## Technical Specification

### Enhancement 1: Version-Aware API Parameters
```python
# Add to existing API endpoints
@app.route('/api/provisions')
def get_provisions():
    # New optional version parameters
    version = request.args.get('version', 'current')  # current, previous, specific version
    as_at_date = request.args.get('as_at_date')       # YYYY-MM-DD format
    document_type = request.args.get('document_type') # SEPP, LEP, DCP
    document_id = request.args.get('document_id')     # specific document filter

    # Existing parameters (maintain backward compatibility)
    zone = request.args.get('zone')
    development_type = request.args.get('development_type')
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))
```

### Enhancement 2: Version Metadata in Responses
```python
# Enhanced response format
{
    "data": [
        {
            "id": 12345,
            "provision_text": "Maximum height: 12m",
            "zone": "R2",
            "ref_number": "4.3",
            # NEW: Version metadata
            "version_info": {
                "version_id": 15,
                "version_number": "v1.2-baseline",
                "effective_date": "2024-09-20",
                "document_type": "LEP",
                "document_identifier": "Inner West LEP 2022",
                "is_current": true,
                "last_changed": "2024-09-20",
                "change_summary": "Baseline provision from consolidated download"
            }
        }
    ],
    "metadata": {
        "total_count": 1500,
        "returned_count": 100,
        "version_context": {
            "requested_version": "current",
            "as_at_date": null,
            "baseline_coverage": "2024-09-20 forward only",
            "historical_disclaimer": "For compliance queries before 2024-09-20, consult official amendment history"
        }
    }
}
```

### Enhancement 3: New Version-Specific Endpoints
```python
# /api/versions/documents - List available document versions
@app.route('/api/versions/documents')
def get_document_versions():
    document_type = request.args.get('document_type')
    document_identifier = request.args.get('document_identifier')

    return {
        "documents": [
            {
                "document_type": "LEP",
                "document_identifier": "Inner West LEP 2022",
                "versions": [
                    {
                        "version_id": 15,
                        "version_number": "v1.0-baseline",
                        "version_status": "CURRENT",
                        "effective_date": "2024-09-20",
                        "provision_count": 4069,
                        "change_summary": "Baseline version from consolidated download"
                    }
                ]
            }
        ]
    }

# /api/versions/changes - Get change history
@app.route('/api/versions/changes')
def get_version_changes():
    document_identifier = request.args.get('document_identifier', required=True)
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    limit = int(request.args.get('limit', 50))

    return {
        "changes": [
            {
                "version_number": "v1.1",
                "effective_date": "2024-10-15",
                "change_type": "MODIFIED",
                "change_summary": "Height limit increased from 9m to 12m",
                "provision_count": 3,
                "provisions_affected": ["4.3", "4.4", "4.5"]
            }
        ]
    }

# /api/versions/compare - Compare two versions
@app.route('/api/versions/compare')
def compare_versions():
    document_identifier = request.args.get('document_identifier', required=True)
    from_version = request.args.get('from_version', required=True)
    to_version = request.args.get('to_version', required=True)

    return {
        "comparison": {
            "document_identifier": "Inner West LEP 2022",
            "from_version": "v1.0-baseline",
            "to_version": "v1.1",
            "summary": {
                "new_provisions": 5,
                "modified_provisions": 12,
                "deleted_provisions": 1,
                "unchanged_provisions": 4051
            },
            "changes": [
                {
                    "ref_number": "4.3",
                    "change_type": "MODIFIED",
                    "old_content": "Maximum height: 9m",
                    "new_content": "Maximum height: 12m",
                    "change_summary": "Height limit increased from 9m to 12m"
                }
            ]
        }
    }
```

### Enhancement 4: Backward Compatibility Layer
```python
# Wrapper to maintain existing API behavior
def ensure_backward_compatibility(endpoint_func):
    """Decorator to ensure existing API consumers continue working"""

    def wrapper(*args, **kwargs):
        # Check if request includes version parameters
        has_version_params = any(param in request.args for param in
                               ['version', 'as_at_date', 'include_version_info'])

        # Get response from enhanced endpoint
        response = endpoint_func(*args, **kwargs)

        # If no version parameters requested, strip version metadata
        if not has_version_params and isinstance(response, dict):
            if 'data' in response:
                for item in response['data']:
                    item.pop('version_info', None)
            response.pop('version_context', None)

        return response

    return wrapper

# Apply to existing endpoints
@app.route('/api/setbacks/calculate')
@ensure_backward_compatibility
def calculate_setbacks():
    # Existing setback calculation logic
    # Now includes version awareness internally
    pass
```

### Enhancement 5: Version-Aware Database Queries
```python
def get_provisions_with_version_awareness(zone=None,
                                        development_type=None,
                                        version='current',
                                        as_at_date=None,
                                        document_type=None,
                                        document_id=None,
                                        limit=100,
                                        offset=0):
    """Enhanced provision query with version parameters"""

    # Use VersionAwareQuery service
    from services.version_aware_query import VersionAwareQuery

    # Get version-filtered provisions
    provisions = VersionAwareQuery.get_provisions(
        document_id=document_id,
        version=version,
        as_at_date=as_at_date
    )

    # Apply additional filters
    filtered_provisions = []
    for provision in provisions:
        if zone and provision.get('zone') != zone:
            continue
        if development_type and provision.get('development_type') != development_type:
            continue
        if document_type and provision.get('document_type') != document_type:
            continue

        filtered_provisions.append(provision)

    # Apply pagination
    total_count = len(filtered_provisions)
    paginated = filtered_provisions[offset:offset + limit]

    return {
        'provisions': paginated,
        'total_count': total_count,
        'returned_count': len(paginated)
    }
```

## Implementation Steps

### Step 1: Update Existing API Endpoints (60 minutes)
1. **Add version parameters** to all provision query endpoints
2. **Enhance response format** to include version metadata
3. **Implement backward compatibility** wrapper
4. **Test existing API consumers** continue working

### Step 2: Create New Version Endpoints (45 minutes)
1. **Document versions endpoint** for listing available versions
2. **Change history endpoint** for amendment tracking
3. **Version comparison endpoint** for diff analysis
4. **Version statistics endpoint** for dashboard data

### Step 3: Integration with Services (30 minutes)
1. **Connect APIs to VersionAwareQuery** service
2. **Add error handling** for invalid version requests
3. **Implement caching** for version metadata
4. **Add request validation** for version parameters

### Step 4: Documentation and Testing (30 minutes)
1. **Update API documentation** with version parameters
2. **Create example requests/responses**
3. **Test version parameter combinations**
4. **Validate performance benchmarks**

## Granular Verification Requirements

### API Endpoint Verification
- [ ] **GET /api/provisions** - accepts version parameters without breaking
- [ ] **GET /api/provisions?version=current** - returns current provisions with metadata
- [ ] **GET /api/provisions?version=previous** - returns previous version provisions
- [ ] **GET /api/provisions?as_at_date=2024-09-20** - returns point-in-time provisions
- [ ] **GET /api/provisions** (no version params) - backward compatibility maintained
- [ ] **Response format** - includes version_info when requested
- [ ] **Response format** - excludes version_info when not requested
- [ ] **Error handling** - invalid version parameter returns 400
- [ ] **Error handling** - invalid date format returns 400

### New Endpoint Verification
- [ ] **GET /api/versions/documents** - lists document versions correctly
- [ ] **GET /api/versions/documents?document_type=LEP** - filters by type
- [ ] **GET /api/versions/changes?document_identifier=X** - returns change history
- [ ] **GET /api/versions/compare?from_version=X&to_version=Y** - compares versions
- [ ] **POST requests** - properly rejected with 405 Method Not Allowed
- [ ] **Missing required parameters** - return 400 with clear error message
- [ ] **Invalid document identifiers** - return 404 with helpful message
- [ ] **Response schemas** - match documented format exactly

### Data Integration Verification
- [ ] **VersionAwareQuery integration** - correctly filters by version
- [ ] **Database performance** - queries complete in <2 seconds
- [ ] **Provision metadata** - accurate version information included
- [ ] **Change tracking data** - properly exposed through API
- [ ] **Document version data** - correctly retrieved and formatted
- [ ] **Pagination** - works correctly with version filtering
- [ ] **Count accuracy** - total_count matches actual filtered results
- [ ] **Memory usage** - large result sets don't cause memory issues

### Backward Compatibility Verification
- [ ] **Existing frontend apps** - continue working without modification
- [ ] **Existing API consumers** - receive expected response format
- [ ] **Response structure** - maintains existing field names and types
- [ ] **Error responses** - maintain existing error format
- [ ] **Performance** - no degradation for non-version requests
- [ ] **Caching** - existing cache keys remain valid
- [ ] **Authentication** - existing auth mechanisms work unchanged
- [ ] **Rate limiting** - existing limits apply correctly

### Security and Validation Verification
- [ ] **Input sanitization** - version parameters properly escaped
- [ ] **SQL injection protection** - parameterized queries used
- [ ] **Cross-site scripting** - output properly encoded
- [ ] **Authorization** - version access respects user permissions
- [ ] **Rate limiting** - version endpoints included in limits
- [ ] **Audit logging** - version requests logged appropriately
- [ ] **Error information** - doesn't leak sensitive data
- [ ] **Resource limits** - prevents abuse of expensive version queries

## Deliverables

1. **Enhanced API endpoints** - with version parameter support
2. **New version-specific endpoints** - for version management workflows
3. **Backward compatibility layer** - maintains existing functionality
4. **Updated API documentation** - with version parameter examples
5. **Comprehensive test suite** - covering all version scenarios

## Success Criteria
✅ All existing API consumers work without modification
✅ Version parameters enable point-in-time queries
✅ New endpoints provide complete version management
✅ API responses include accurate version metadata
✅ Performance maintains <2 second response times
✅ Error handling provides clear, helpful messages
✅ Documentation enables easy adoption of version features

## Estimated Time
**2.5 hours total**
- Endpoint updates: 60 minutes
- New endpoints: 45 minutes
- Integration: 30 minutes
- Testing/docs: 30 minutes
- Verification: 5 minutes