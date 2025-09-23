# PRP-F2: Metadata Validation Fix

## Objective
Fix V7 Pydantic metadata validation errors where dict is expected but None is provided.

## Root Cause Analysis
Error: `1 validation error for DocumentVersion metadata Input should be a valid dictionary [type=dict_type, input_value=None, input_type=NoneType]`
- Pydantic models expect metadata field to be a dictionary
- Code is passing None instead of empty dict {}
- Need to ensure default values and validation

## Technical Implementation

### Phase 1: Pydantic Model Analysis
```python
# Check current DocumentVersion model definition
from pydantic import BaseModel
from typing import Optional, Dict, Any

class DocumentVersion(BaseModel):
    metadata: Optional[Dict[str, Any]] = {}  # Should default to empty dict
```

### Phase 2: Database Schema Validation
```sql
-- Ensure metadata column has proper default
ALTER TABLE versions.document_versions
ALTER COLUMN metadata SET DEFAULT '{}';

-- Update existing NULL values
UPDATE versions.document_versions
SET metadata = '{}'
WHERE metadata IS NULL;
```

### Phase 3: Code Validation Fixes
```python
# Ensure metadata is always a dict
def create_document_version(data):
    if data.get('metadata') is None:
        data['metadata'] = {}
    return DocumentVersion(**data)
```

## Success Criteria
- All metadata fields have valid dict values
- Pydantic validation passes
- V7 verification succeeds
- No validation errors in logs

## Verification Commands
```bash
python verify_f2_metadata_validation.py
```

## Dependencies
- Pydantic models defined
- versions.document_versions table exists
- Python validation working