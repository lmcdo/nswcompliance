# PRP-8B CHUNK 3: Hierarchy Resolution API Implementation

**SESSION SCOPE**: API endpoints only (Lines 532-843 from PRP-8B)  
**DURATION**: Single session (~45-60 minutes)  
**DEPENDENCIES**: CHUNK_2_MIGRATION_COMPLETE.marker must exist  
**ROLLBACK**: Remove API files and routes if failures  

---

## 🎯 **SPECIFIC IMPLEMENTATION TARGET**

### **PRIMARY OBJECTIVE:**
Implement the HierarchyResolver service and authoritative compliance API endpoints with caching.

### **SCOPE BOUNDARIES:**
- ✅ **DO**: Create HierarchyResolver, API routes, hierarchy cache logic, authority resolution
- ❌ **DON'T**: Create schema (Chunk 1), migrate data (Chunk 2), build frontend (Chunk 4)  
- ❌ **DON'T**: Create visual aids or professional guidance (later chunks)

### **FILES TO REFERENCE:**
- `PRPs/PRP-8B_AUTHORITATIVE_COMPLIANCE_SYSTEM.md` (lines 532-843)
- `prp_checkpoints/CHUNK_2_MIGRATION_COMPLETE.marker` (dependency verification)

---

## 📋 **SUCCESS CRITERIA (BINARY VERIFICATION)**

### **Primary Success Metrics:**
1. **API endpoint works**: `POST /api/authoritative/compliance-check` returns 200
2. **Hierarchy resolution**: Response contains `primary_authorities` object
3. **Authority precedence**: SEPP overrides LEP overrides DCP in responses  
4. **Caching functional**: Second identical request faster than first
5. **Tier classification**: Response shows provisions grouped by tiers 1-5

### **API Response Structure Required:**
```json
{
  "property": {...},
  "tier_1_provisions": [...],
  "tier_2_provisions": [...], 
  "tier_3_provisions": [...],
  "tier_4_provisions": [...],
  "tier_5_provisions": [...],
  "primary_authorities": {
    "setback_front": {...},
    "setback_rear": {...}, 
    "height": {...}
  },
  "complexity_assessment": "string",
  "confidence_level": 0.85,
  "legal_disclaimer": "string"
}
```

---

## 🚨 **FAILURE ANTICIPATION & ERROR CHECKING**

### **Pre-Implementation Dependency Checks:**
```python
import os
import json
import psycopg2

# Check 1: Previous chunk completion
if not os.path.exists('prp_checkpoints/CHUNK_2_MIGRATION_COMPLETE.marker'):
    print("❌ FAILURE: CHUNK_2_MIGRATION_COMPLETE.marker not found")
    print("SOLUTION: Execute CHUNK 2 first") 
    exit(1)

# Check 2: Data exists in authoritative schema
conn = psycopg2.connect(host='localhost', database='nsw_planning', user='postgres', password='postgres')
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM authoritative.planning_provisions")
provision_count = cur.fetchone()[0]
if provision_count < 100:
    print(f"❌ FAILURE: Expected >100 provisions, found {provision_count}")
    print("SOLUTION: Re-run CHUNK 2 migration")
    exit(1)

cur.execute("SELECT COUNT(*) FROM authoritative.provision_authority_tiers") 
tier_count = cur.fetchone()[0]
if tier_count < 100:
    print(f"❌ FAILURE: Expected >100 tiers, found {tier_count}")
    print("SOLUTION: Re-run CHUNK 2 tier classification")
    exit(1)

print(f"✅ Pre-implementation checks passed. Data available: {provision_count} provisions, {tier_count} tiers")
```

### **During Implementation Error Checks:**

#### **Error Check 1: HierarchyResolver Class Validation**
```python
def test_hierarchy_resolver():
    """Test core hierarchy resolution logic"""
    
    try:
        from services.hierarchy_resolver import HierarchyResolver
        resolver = HierarchyResolver(db_pool=None)  # Mock for testing
        
        # Test authority precedence logic
        provisions = [
            {'authority_level': 3, 'document_type': 'DCP', 'numeric_value': 2.0},
            {'authority_level': 1, 'document_type': 'SEPP', 'numeric_value': None}, 
            {'authority_level': 2, 'document_type': 'LEP', 'numeric_value': 3.0}
        ]
        
        # Should return SEPP (authority_level 1) as primary
        primary = resolver.select_primary_authority(provisions)
        
        if primary['authority_level'] != 1:
            raise Exception("❌ SEPP should override LEP and DCP")
            
        print("✅ Hierarchy resolution logic working")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Logic error: {e}")  
        return False
```

#### **Error Check 2: API Route Registration**
```python
def test_api_routes():
    """Verify API routes are registered correctly"""
    
    import requests
    import time
    
    try:
        # Test health check first
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code != 200:
            print("❌ Base API server not running")
            return False
        
        # Test our new endpoint
        test_payload = {
            "property_id": 1,
            "zone_code": "R2",
            "development_type": "dwelling_house"
        }
        
        response = requests.post(
            "http://localhost:8000/api/authoritative/compliance-check",
            json=test_payload,
            timeout=10
        )
        
        if response.status_code == 404:
            print("❌ Route not registered - check FastAPI router setup")
            return False
        elif response.status_code == 500:
            print("❌ Internal server error - check implementation logic")
            return False
        elif response.status_code != 200:
            print(f"❌ Unexpected status: {response.status_code}")
            return False
            
        data = response.json()
        required_fields = ['tier_1_provisions', 'primary_authorities', 'confidence_level']
        
        for field in required_fields:
            if field not in data:
                print(f"❌ Missing required field: {field}")
                return False
        
        print("✅ API route working correctly")
        return True
        
    except requests.exceptions.ConnectoinError:
        print("❌ Cannot connect to API server - is it running?")
        return False
    except Exception as e:
        print(f"❌ API test error: {e}")
        return False
```

#### **Error Check 3: Cache Performance Validation**
```python
def test_hierarchy_cache():
    """Test caching improves performance"""
    
    import time
    import requests
    
    test_payload = {
        "property_id": 1,
        "zone_code": "R2", 
        "development_type": "dwelling_house"
    }
    
    try:
        # First request (cache miss)
        start_time = time.time()
        response1 = requests.post(
            "http://localhost:8000/api/authoritative/compliance-check",
            json=test_payload,
            timeout=10
        )
        first_request_time = time.time() - start_time
        
        if response1.status_code != 200:
            print("❌ First request failed")
            return False
        
        # Second request (cache hit)
        start_time = time.time()
        response2 = requests.post(
            "http://localhost:8000/api/authoritative/compliance-check", 
            json=test_payload,
            timeout=10
        )
        second_request_time = time.time() - start_time
        
        if response2.status_code != 200:
            print("❌ Second request failed")
            return False
            
        # Cache should make it faster
        if second_request_time >= first_request_time:
            print(f"⚠️ WARNING: Cache may not be working. First: {first_request_time:.3f}s, Second: {second_request_time:.3f}s")
            return False
        
        speedup = first_request_time / second_request_time
        print(f"✅ Cache working. Speedup: {speedup:.1f}x")
        return True
        
    except Exception as e:
        print(f"❌ Cache test error: {e}")
        return False
```

### **Common Failure Scenarios & Diagnosis:**

#### **Failure Scenario 1: Database Pool Connection Issues**
```
ERROR: asyncpg.exceptions.TooManyConnectionsError
DIAGNOSIS: Database connection pool exhausted
SOLUTION: Reduce pool size or fix connection leaks  
ROLLBACK: Restart API server and check connection management
```

#### **Failure Scenario 2: Authority Resolution Logic Error**
```
ERROR: KeyError: 'authority_level' 
DIAGNOSIS: Provision missing authority_level field from migration
SOLUTION: Verify CHUNK 2 migration completed properly
ROLLBACK: Check authoritative.planning_provisions schema
```

#### **Failure Scenario 3: Cache Key Collision**
```
ERROR: Same cache key returns different results
DIAGNOSIS: Cache key generation logic flawed
SOLUTION: Review cache key construction in hierarchy resolver
ROLLBACK: Clear cache table and fix key generation
```

#### **Failure Scenario 4: API Response Serialization**  
```
ERROR: Object of type 'Decimal' is not JSON serializable
DIAGNOSIS: Database Decimal types not handled in JSON response
SOLUTION: Add Decimal to JSON encoder or convert to float
ROLLBACK: Fix serialization before deploying API
```

---

## 🔧 **IMPLEMENTATION PROCEDURE**

### **Step 1: Pre-flight Verification**
Execute dependency checks above. **STOP if any fail.**

### **Step 2: Create Core Services**
Based on PRP-8B lines 590-687:

1. **HierarchyResolver Service**: `services/hierarchy_resolver.py`
2. **Authority Classification**: `services/authority_classifier.py`  
3. **Cache Manager**: `services/hierarchy_cache.py`

### **Step 3: Create API Routes**
Based on PRP-8B lines 688-843:

1. **Main Compliance Endpoint**: `app/api/authoritative/compliance.py`
2. **Response Models**: `app/models/authoritative_response.py`
3. **Request Validation**: `app/models/authoritative_request.py`

### **Step 4: Test Each Component Independently**
```python
# Test sequence with error isolation
def test_implementation_sequence():
    
    tests = [
        ("Database connection", test_db_connection),
        ("Hierarchy resolver", test_hierarchy_resolver), 
        ("API routes", test_api_routes),
        ("Cache performance", test_hierarchy_cache),
        ("Response structure", test_response_structure)
    ]
    
    for test_name, test_func in tests:
        print(f"Testing {test_name}...")
        
        try:
            success = test_func()
            if not success:
                print(f"❌ {test_name} failed - stopping implementation")
                return False
            print(f"✅ {test_name} passed")
            
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            return False
    
    return True
```

### **Step 5: Integration Testing**
```python
def test_full_integration():
    """Test complete API workflow"""
    
    test_cases = [
        # Test SEPP override
        {"zone": "R2", "dev_type": "dwelling_house", "expected_primary": "SEPP"},
        
        # Test LEP fallback  
        {"zone": "R3", "dev_type": "dual_occupancy", "expected_primary": "LEP"},
        
        # Test DCP implementation
        {"zone": "R4", "dev_type": "apartment", "expected_primary": "DCP"},
    ]
    
    for case in test_cases:
        response = call_api(case)
        
        if not verify_hierarchy_correct(response, case):
            print(f"❌ Hierarchy test failed: {case}")
            return False
            
    return True
```

---

## 📊 **COMPLETION VERIFICATION**

### **Final API Integration Test:**
```python
#!/usr/bin/env python3
"""
CHUNK 3 Comprehensive API Verification
Tests all hierarchy resolution requirements  
"""

import requests
import json
import time
from datetime import datetime

def verify_chunk3_completion():
    
    base_url = "http://localhost:8000"
    tests = []
    errors = []
    
    # Test 1: API endpoint exists and responds
    try:
        response = requests.post(
            f"{base_url}/api/authoritative/compliance-check",
            json={"property_id": 1, "zone_code": "R2", "development_type": "dwelling_house"},
            timeout=10
        )
        
        api_works = response.status_code == 200
        tests.append(('API endpoint responds', api_works, f'Status: {response.status_code}'))
        
        if api_works:
            data = response.json()
            
            # Test 2: Required response structure
            required_fields = [
                'tier_1_provisions', 'tier_2_provisions', 'tier_3_provisions',
                'tier_4_provisions', 'tier_5_provisions', 'primary_authorities',
                'confidence_level', 'legal_disclaimer'
            ]
            
            for field in required_fields:
                has_field = field in data
                tests.append((f'Field {field}', has_field, 'Present' if has_field else 'Missing'))
            
            # Test 3: Hierarchy resolution working
            has_primary_auth = len(data.get('primary_authorities', {})) > 0
            tests.append(('Primary authorities', has_primary_auth, f'{len(data.get("primary_authorities", {}))} authorities'))
            
            # Test 4: Tier classification 
            total_provisions = sum(len(data.get(f'tier_{i}_provisions', [])) for i in range(1, 6))
            tests.append(('Tier classification', total_provisions > 0, f'{total_provisions} provisions classified'))
            
            # Test 5: Confidence calculation
            confidence = data.get('confidence_level', 0)
            tests.append(('Confidence level', 0 < confidence <= 1, f'Confidence: {confidence}'))
            
        else:
            errors.append(f"API endpoint failed: {response.text}")
            
    except Exception as e:
        tests.append(('API connection', False, f'Error: {str(e)}'))
        errors.append(f"Cannot connect to API: {e}")
    
    # Test 6: Cache performance
    try:
        # First request
        start = time.time()
        requests.post(f"{base_url}/api/authoritative/compliance-check", 
                     json={"property_id": 1, "zone_code": "R2", "development_type": "dwelling_house"},
                     timeout=10)
        first_time = time.time() - start
        
        # Second request (should be cached)
        start = time.time()
        requests.post(f"{base_url}/api/authoritative/compliance-check",
                     json={"property_id": 1, "zone_code": "R2", "development_type": "dwelling_house"}, 
                     timeout=10)
        second_time = time.time() - start
        
        cache_working = second_time < first_time
        tests.append(('Cache performance', cache_working, 
                     f'First: {first_time:.3f}s, Second: {second_time:.3f}s'))
        
    except Exception as e:
        tests.append(('Cache test', False, f'Error: {str(e)}'))
    
    # Print results
    print('CHUNK 3 VERIFICATION RESULTS:')
    print('=' * 60)
    
    all_passed = True
    for test_name, passed, detail in tests:
        status = 'PASS' if passed else 'FAIL'
        print(f'{status:4} | {test_name:<25} | {detail}')
        if not passed:
            all_passed = False
    
    print('=' * 60)
    
    if all_passed and not errors:
        print('✅ ALL TESTS PASSED - CHUNK 3 COMPLETE')
        
        # Create completion marker
        with open('prp_checkpoints/CHUNK_3_HIERARCHY_API_COMPLETE.marker', 'w') as f:
            json.dump({
                'chunk': 'PRP-8B-CHUNK-3',
                'completed_at': datetime.now().isoformat(),
                'api_endpoint': '/api/authoritative/compliance-check',
                'cache_performance': f'{first_time:.3f}s -> {second_time:.3f}s',
                'verification_passed': True,
                'next_chunk': 'CHUNK_4_FRONTEND_COMPONENTS'
            }, f, indent=2)
            
        print('📄 Completion marker created: CHUNK_3_HIERARCHY_API_COMPLETE.marker')
        
    else:
        print('❌ VERIFICATION FAILED')
        if errors:
            print('\nErrors encountered:')
            for error in errors:
                print(f'  - {error}')
    
    return all_passed and not errors

if __name__ == "__main__":
    success = verify_chunk3_completion()
    exit(0 if success else 1)
```

---

## 🔄 **ROLLBACK PROCEDURES**

### **Complete Rollback (Critical Failures):**
```bash
# Remove API files
rm -f app/api/authoritative/compliance.py
rm -f services/hierarchy_resolver.py  
rm -f services/authority_classifier.py
rm -f services/hierarchy_cache.py

# Clear hierarchy cache
psql -d nsw_planning -c "TRUNCATE TABLE authoritative.hierarchy_resolution_cache;"

# Restart API server
kill -9 $(pgrep -f "uvicorn")
# Manual restart required
```

### **Partial Rollback (Specific Issues):**
```sql
-- If cache corrupted:
TRUNCATE TABLE authoritative.hierarchy_resolution_cache;

-- If performance issues:
-- Review connection pool settings and query optimization
```

---

## 📁 **COMPLETION ARTIFACTS**

### **Files Created:**
- `services/hierarchy_resolver.py` - Core hierarchy resolution logic
- `app/api/authoritative/compliance.py` - Main API endpoint
- `app/models/authoritative_response.py` - Response structure models
- `prp_checkpoints/CHUNK_3_HIERARCHY_API_COMPLETE.marker` - Completion verification

### **API Endpoints Created:**
- `POST /api/authoritative/compliance-check` - Main compliance endpoint
- Proper request validation with Pydantic models
- Response structure matching PRP-8B specification

### **Database Changes:**
- `authoritative.hierarchy_resolution_cache` populated with common queries
- Performance indexes utilized for fast hierarchy resolution

### **Next Chunk Preparation:**
Upon completion, `CHUNK_4_FRONTEND_COMPONENTS.md` can be executed to:
- Deploy AuthoritativeComplianceDisplay component
- Add tier badges and visual hierarchy
- Implement full text expansion

---

## ⚠️ **CRITICAL SUCCESS FACTORS**

1. **Dependency Verification**: CHUNK_2_MIGRATION_COMPLETE.marker must exist
2. **API Server Running**: FastAPI/Uvicorn must be operational
3. **Database Pool Management**: No connection leaks or pool exhaustion
4. **Error Handling**: Graceful failure modes for all edge cases
5. **Performance**: Cache must provide measurable speedup (>2x)
6. **Response Structure**: Exact match to PRP-8B specification

**Expected Performance**: <200ms for cached requests, <1s for uncached requests