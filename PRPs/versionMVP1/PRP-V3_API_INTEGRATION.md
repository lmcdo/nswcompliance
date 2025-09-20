# PRP-V3: API Version Integration

## Objective
Integrate version awareness into existing API endpoints with backward compatibility and minimal disruption.

## Prerequisites
- PRP-V1 and PRP-V2 completed
- API server running (api_server.py)
- Version service layer operational

## Implementation

### Step 1: Modify API Models
```python
# File: api_server.py - Add to existing imports
from typing import Optional, Literal
from datetime import date
from services.version_manager import VersionManager, DocumentType
from services.version_aware_query import VersionAwareQuery

# Add version parameters to request models
class ProvisionsRequest(BaseModel):
    document_id: Optional[str] = None
    version: Literal["current", "previous", "all"] = "current"
    as_at_date: Optional[date] = None
    include_version_info: bool = False

class ComplianceCheckRequest(BaseModel):
    property_id: str
    development_type: str
    assessment_date: Optional[date] = None  # Use current if not specified
    version_context: bool = True  # Include version info in response
```

### Step 2: Update Core API Endpoints
```python
# Modify existing provisions endpoint
@app.get("/api/provisions")
async def get_provisions(
    document_id: Optional[str] = Query(None),
    version: str = Query("current", regex="^(current|previous|all)$"),
    as_at_date: Optional[date] = Query(None),
    include_version_info: bool = Query(False)
):
    """
    Get regulatory provisions with version awareness
    - version: "current" (default), "previous", or "all"
    - as_at_date: Get provisions as they were on specific date
    - include_version_info: Add version metadata to response
    """
    try:
        provisions = VersionAwareQuery.get_provisions(
            document_id=document_id,
            version=version,
            as_at_date=as_at_date
        )

        if include_version_info:
            # Enrich with version metadata
            vm = VersionManager()
            for prov in provisions:
                if prov.get('version_id'):
                    # Add version details to each provision
                    pass

        return {
            "status": "success",
            "query_params": {
                "version": version,
                "as_at_date": as_at_date.isoformat() if as_at_date else None,
                "document_id": document_id
            },
            "count": len(provisions),
            "provisions": provisions
        }
    except Exception as e:
        logger.error(f"Error fetching provisions: {e}")
        return {"status": "error", "message": str(e)}

# Add new version-specific endpoints
@app.get("/api/versions/current")
async def get_current_versions():
    """Get all current document versions"""
    vm = VersionManager()
    try:
        stats = vm.get_version_statistics()
        return {
            "status": "success",
            "statistics": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        vm.close()

@app.get("/api/versions/{document_type}/{document_identifier}")
async def get_document_versions(
    document_type: str,
    document_identifier: str
):
    """Get version history for a specific document"""
    vm = VersionManager()
    try:
        doc_type = DocumentType(document_type.upper())
        current, previous = vm.get_version_comparison(doc_type, document_identifier)

        return {
            "status": "success",
            "document": {
                "type": document_type,
                "identifier": document_identifier
            },
            "versions": {
                "current": current.dict() if current else None,
                "previous": previous.dict() if previous else None
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        vm.close()

@app.post("/api/versions/create")
async def create_new_version(
    document_type: str = Body(...),
    document_identifier: str = Body(...),
    version_number: str = Body(...),
    effective_date: date = Body(...),
    document_url: Optional[str] = Body(None),
    change_summary: Optional[str] = Body(None),
    api_key: str = Header(...)
):
    """
    Create a new document version (requires admin API key)
    """
    # Validate API key for admin operations
    if api_key != os.getenv("ADMIN_API_KEY", ""):
        raise HTTPException(status_code=403, detail="Invalid API key")

    vm = VersionManager()
    try:
        doc_type = DocumentType(document_type.upper())
        new_version = vm.create_new_version(
            document_type=doc_type,
            document_identifier=document_identifier,
            version_number=version_number,
            effective_date=effective_date,
            document_url=document_url,
            change_summary=change_summary,
            created_by="api_admin"
        )

        return {
            "status": "success",
            "message": f"Created version {version_number}",
            "version": new_version.dict()
        }
    except Exception as e:
        logger.error(f"Failed to create version: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        vm.close()
```

### Step 3: Update Compliance Check Endpoints
```python
# Modify existing compliance check endpoint
@app.post("/api/compliance/check")
async def check_compliance(request: ComplianceCheckRequest):
    """
    Check compliance with version awareness
    Uses provisions effective at assessment_date
    """
    assessment_date = request.assessment_date or date.today()

    # Get provisions valid at assessment date
    provisions = VersionAwareQuery.get_provisions(
        as_at_date=assessment_date
    )

    # Existing compliance logic here...
    # Add version context to response
    response = {
        "status": "success",
        "assessment_context": {
            "date": assessment_date.isoformat(),
            "provisions_count": len(provisions),
            "version_aware": True
        },
        "compliance_result": {
            # Existing compliance results...
        }
    }

    if request.version_context:
        # Add version information
        response["version_info"] = {
            "assessed_as_at": assessment_date.isoformat(),
            "current_date": date.today().isoformat(),
            "using_historical": assessment_date < date.today()
        }

    return response
```

### Step 4: Add Version Headers to Responses
```python
# Add middleware to include version headers
@app.middleware("http")
async def add_version_headers(request: Request, call_next):
    response = await call_next(request)

    # Add version-related headers
    response.headers["X-API-Version"] = "2.0.0"
    response.headers["X-Version-Support"] = "enabled"
    response.headers["X-Version-Mode"] = request.query_params.get("version", "current")

    if "as_at_date" in request.query_params:
        response.headers["X-Version-Date"] = request.query_params["as_at_date"]

    return response
```

### Step 5: API Documentation Updates
```python
# Update OpenAPI documentation
app = FastAPI(
    title="NSW Planning API",
    version="2.0.0",
    description="""
    NSW Planning Compliance API with Version Management

    ## Version Support
    All provision endpoints now support version parameters:
    - `version`: Select current, previous, or all versions
    - `as_at_date`: Get provisions as they were on a specific date

    ## Breaking Changes
    None - all existing endpoints remain backward compatible

    ## New Features
    - Version-aware provision queries
    - Historical compliance checking
    - Version comparison endpoints
    """
)
```

## Verification Checklist

### API Functionality
- [ ] Existing endpoints still work without version params
- [ ] Version parameters correctly filter results
- [ ] Date-based queries return accurate data
- [ ] Admin endpoints secured with API key
- [ ] Response headers include version info

### Performance
- [ ] Response time <2s for version queries
- [ ] No timeout errors on complex queries
- [ ] Caching still effective
- [ ] Database connection pooling working

### Documentation
- [ ] OpenAPI docs updated
- [ ] Version parameters documented
- [ ] Example requests provided
- [ ] Breaking changes noted (should be none)

## Testing Commands

```bash
# Test current version query
curl "http://localhost:8000/api/provisions?version=current"

# Test date-based query
curl "http://localhost:8000/api/provisions?as_at_date=2023-06-01"

# Test version comparison
curl "http://localhost:8000/api/versions/LEP/Inner-West-LEP-2022"

# Test compliance with assessment date
curl -X POST "http://localhost:8000/api/compliance/check" \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": "123",
    "development_type": "dwelling",
    "assessment_date": "2023-12-01"
  }'
```

## Success Criteria

1. ✅ All existing endpoints remain functional
2. ✅ Version parameters work correctly
3. ✅ Historical queries return accurate data
4. ✅ API documentation complete and accurate
5. ✅ Performance within acceptable limits (<2s)

## Next Steps

1. Run `verify_v3_api.py` to test endpoints
2. Proceed to PRP-V4_MIGRATION_PIPELINE.md
3. Document API changes for frontend team