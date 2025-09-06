# PRP-K6: Hierarchy Implementation with Comprehensive Testing

**Status**: READY FOR IMPLEMENTATION  
**Priority**: CRITICAL - Complete Legal Hierarchy Integration  
**Dependencies**: PRP-K4 (Database Migration ✅), PRP-K5 (Activation Plan ✅)  
**Date**: 2025-09-07  
**Estimated Duration**: 2-3 weeks

## Executive Summary

PRP-K6 implements the complete SEPP > LEP > DCP legal hierarchy system with comprehensive testing and validation. This PRP transforms the current DCP-only system into a full NSW planning law compliance engine with proper authority precedence, legal audit trails, and extensive automated testing.

## Current State Analysis

### ✅ **Foundation Complete (PRP-K4):**
- **91 SEPP/LEP overrides** imported to `sepp_lep_overrides` table
- **28,032 supporting records** across 11 database tables
- **96% rule traceability** (46/48 rules linked to source text)
- **PostgreSQL infrastructure** fully operational

### ❌ **Critical Implementation Gaps:**
- **Hierarchy engine inactive** (`sepp-lep-processor.ts.bak`)
- **All rules DCP-level only** (0 SEPP rules, 0 LEP rules)
- **No authority precedence** in API responses
- **No legal audit trails** for compliance decisions

## Implementation Phases

### **Phase 1: Core Hierarchy Engine Activation**

#### **Task 1.1: Restore Hierarchy Processor**
```bash
cd frontend-nextjs/lib/compliance/
mv sepp-lep-processor.ts.bak sepp-lep-processor.ts
```

**Validation:**
- File exists at correct location
- TypeScript compilation successful
- All imports resolve correctly

#### **Task 1.2: Update Zone Rule Authority Levels**
```sql
-- Upgrade rules matching SEPP provisions (highest precedence)
UPDATE zone_setback_rules 
SET authority_type = 'SEPP', precedence_level = 1
WHERE rule_id IN (
    SELECT DISTINCT sepp_provision_id::text 
    FROM sepp_lep_overrides
    WHERE override_type IN ('replaces', 'exempts_from')
);

-- Upgrade rules matching LEP clauses (medium precedence)
UPDATE zone_setback_rules 
SET authority_type = 'LEP', precedence_level = 2
WHERE rule_id IN (
    SELECT DISTINCT lep_clause_reference 
    FROM sepp_lep_overrides 
    WHERE override_type = 'modifies'
);

-- Verify authority distribution
SELECT authority_type, precedence_level, COUNT(*) 
FROM zone_setback_rules 
GROUP BY authority_type, precedence_level 
ORDER BY precedence_level;
```

**Expected Results:**
- Mixed authority distribution (SEPP: 5-10 rules, LEP: 10-15 rules, DCP: 25-35 rules)
- No rules with NULL authority_type
- Precedence levels correctly assigned (1=SEPP, 2=LEP, 3=DCP)

### **Phase 2: API Integration and Legal Audit Trail**

#### **Task 2.1: Integrate Hierarchy Engine into API**
```typescript
// frontend-nextjs/app/api/setbacks/calculate/route.ts
import { SEPPLEPProcessor } from '@/lib/compliance/sepp-lep-processor';

export async function POST(request: NextRequest) {
  const startTime = Date.now();
  
  try {
    // Parse request
    const body = await request.json();
    const { property_zone, property_id, lot_geometry } = body;

    // Initialize hierarchy processor
    const hierarchyProcessor = new SEPPLEPProcessor();
    
    // Get NSW Planning API data if available
    const nswApiLayers = await getNSWPlanningLayers(property_id);
    
    // Process hierarchical compliance
    const hierarchicalResult = await hierarchyProcessor.processHierarchicalCompliance(
      nswApiLayers,
      property_zone,
      'setback'
    );
    
    // Generate legal audit trail
    const auditTrail = hierarchicalResult.audit_trail;
    const controllingAuthority = hierarchicalResult.controlling_authority;
    
    // Get zone-specific rules with hierarchy
    const setbackResults = await getHierarchicalSetbacks(property_zone, hierarchicalResult);
    
    return NextResponse.json({
      success: true,
      setback_results: setbackResults,
      legal_compliance: {
        controlling_authority: controllingAuthority,
        legal_justification: hierarchicalResult.legal_justification,
        applicable_provision: hierarchicalResult.applicable_provision,
        overridden_provisions: hierarchicalResult.overridden_provisions,
        conflict_resolution_method: hierarchicalResult.conflict_resolution_method,
        audit_trail: auditTrail
      },
      processing_time_ms: Date.now() - startTime
    });
    
  } catch (error) {
    // Graceful fallback to existing DCP-only system
    console.error('[API] Hierarchy engine error:', error);
    return await fallbackToDCPOnlyCalculation(request);
  }
}
```

#### **Task 2.2: Enhanced Response Schema**
```typescript
// frontend-nextjs/types/setback.ts
export interface HierarchicalSetbackResponse {
  success: boolean;
  setback_results: SetbackResult[];
  legal_compliance: {
    controlling_authority: 'SEPP' | 'LEP' | 'DCP';
    legal_justification: string;
    applicable_provision: SEPPProvision | LEPProvision;
    overridden_provisions: Array<SEPPProvision | LEPProvision>;
    conflict_resolution_method: 'sepp_override' | 'lep_default' | 'most_restrictive';
    audit_trail: string[];
  };
  buildable_area_analysis: BuildableAreaAnalysis;
  processing_time_ms: number;
  precision_level: string;
  processing_method: string;
}
```

### **Phase 3: Comprehensive Testing Framework**

#### **Test Suite 3.1: Authority Precedence Testing**
```bash
#!/bin/bash
# test_authority_precedence.sh

echo "=== PRP-K6 AUTHORITY PRECEDENCE TESTING ==="

# Test 1: SEPP Override Test
echo "Test 1: SEPP takes precedence over LEP and DCP"
SEPP_RESPONSE=$(curl -s -X POST http://localhost:3007/api/setbacks/calculate \
  -H "Content-Type: application/json" \
  -d '{"property_zone": "R2", "property_id": 1962876, "lot_geometry": {"hasM": false, "hasZ": false, "rings": [[[0,0],[10,0],[10,20],[0,20],[0,0]]], "spatialReference": {"wkid": 4326}}}')

CONTROLLING_AUTHORITY=$(echo $SEPP_RESPONSE | python3 -c "import json, sys; data = json.load(sys.stdin); print(data.get('legal_compliance', {}).get('controlling_authority', 'UNKNOWN'))")

if [ "$CONTROLLING_AUTHORITY" = "SEPP" ]; then
    echo "✅ SEPP precedence test PASSED"
else
    echo "❌ SEPP precedence test FAILED - Got: $CONTROLLING_AUTHORITY"
    exit 1
fi

# Test 2: LEP Default Test (no SEPP)
echo "Test 2: LEP applies when no SEPP override exists"
LEP_RESPONSE=$(curl -s -X POST http://localhost:3007/api/setbacks/calculate \
  -H "Content-Type: application/json" \
  -d '{"property_zone": "R3", "property_id": 1962876, "lot_geometry": {"hasM": false, "hasZ": false, "rings": [[[0,0],[10,0],[10,20],[0,20],[0,0]]], "spatialReference": {"wkid": 4326}}}')

CONTROLLING_AUTHORITY_LEP=$(echo $LEP_RESPONSE | python3 -c "import json, sys; data = json.load(sys.stdin); print(data.get('legal_compliance', {}).get('controlling_authority', 'UNKNOWN'))")

if [ "$CONTROLLING_AUTHORITY_LEP" = "LEP" ] || [ "$CONTROLLING_AUTHORITY_LEP" = "DCP" ]; then
    echo "✅ LEP/DCP precedence test PASSED"
else
    echo "❌ LEP/DCP precedence test FAILED - Got: $CONTROLLING_AUTHORITY_LEP"
    exit 1
fi

# Test 3: Audit Trail Presence
echo "Test 3: Legal audit trail generated"
AUDIT_TRAIL_LENGTH=$(echo $SEPP_RESPONSE | python3 -c "import json, sys; data = json.load(sys.stdin); print(len(data.get('legal_compliance', {}).get('audit_trail', [])))")

if [ "$AUDIT_TRAIL_LENGTH" -gt 0 ]; then
    echo "✅ Audit trail test PASSED - $AUDIT_TRAIL_LENGTH entries"
else
    echo "❌ Audit trail test FAILED - No audit trail generated"
    exit 1
fi

echo "=== AUTHORITY PRECEDENCE TESTING COMPLETE ==="
```

#### **Test Suite 3.2: Database Integrity Testing**
```python
#!/usr/bin/env python3
# test_database_integrity.py

import psycopg2
import json
from datetime import datetime

def test_database_integrity():
    """Test database integrity and hierarchy data quality."""
    
    print("=== PRP-K6 DATABASE INTEGRITY TESTING ===")
    
    conn = psycopg2.connect(
        host='localhost', 
        database='nsw_planning', 
        user='postgres', 
        password='postgres'
    )
    cursor = conn.cursor()
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Authority Distribution
    tests_total += 1
    cursor.execute('''
        SELECT authority_type, COUNT(*) 
        FROM zone_setback_rules 
        GROUP BY authority_type 
        ORDER BY authority_type
    ''')
    authority_dist = cursor.fetchall()
    
    authority_types = {auth: count for auth, count in authority_dist}
    
    if len(authority_types) >= 2:  # Should have SEPP/LEP + DCP
        print(f"✅ Test 1 PASSED - Authority distribution: {authority_types}")
        tests_passed += 1
    else:
        print(f"❌ Test 1 FAILED - Only {len(authority_types)} authority types")
    
    # Test 2: Precedence Levels
    tests_total += 1
    cursor.execute('''
        SELECT precedence_level, COUNT(*) 
        FROM zone_setback_rules 
        GROUP BY precedence_level 
        ORDER BY precedence_level
    ''')
    precedence_dist = cursor.fetchall()
    
    precedence_levels = {level: count for level, count in precedence_dist}
    
    if 1 in precedence_levels or 2 in precedence_levels:  # SEPP or LEP present
        print(f"✅ Test 2 PASSED - Precedence distribution: {precedence_levels}")
        tests_passed += 1
    else:
        print(f"❌ Test 2 FAILED - No SEPP/LEP precedence levels found")
    
    # Test 3: SEPP/LEP Overrides Table
    tests_total += 1
    cursor.execute('SELECT COUNT(*) FROM sepp_lep_overrides')
    override_count = cursor.fetchone()[0]
    
    if override_count == 91:
        print(f"✅ Test 3 PASSED - SEPP/LEP overrides: {override_count}")
        tests_passed += 1
    else:
        print(f"❌ Test 3 FAILED - Expected 91 overrides, got {override_count}")
    
    # Test 4: Source Text Traceability
    tests_total += 1
    cursor.execute('''
        SELECT COUNT(*) as total, 
               COUNT(source_paragraph_text) as with_text 
        FROM zone_setback_rules
    ''')
    total, with_text = cursor.fetchone()
    traceability_percent = (with_text / total) * 100
    
    if traceability_percent >= 90:
        print(f"✅ Test 4 PASSED - Source traceability: {traceability_percent:.1f}%")
        tests_passed += 1
    else:
        print(f"❌ Test 4 FAILED - Source traceability only {traceability_percent:.1f}%")
    
    # Test 5: Authority Upgrade Validation
    tests_total += 1
    cursor.execute('''
        SELECT COUNT(*) FROM zone_setback_rules zsr
        JOIN sepp_lep_overrides slo ON zsr.rule_id = slo.sepp_provision_id::text
        WHERE zsr.authority_type = 'SEPP'
    ''')
    sepp_upgrades = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT COUNT(*) FROM zone_setback_rules zsr
        JOIN sepp_lep_overrides slo ON zsr.rule_id = slo.lep_clause_reference
        WHERE zsr.authority_type = 'LEP'
    ''')
    lep_upgrades = cursor.fetchone()[0]
    
    if sepp_upgrades > 0 or lep_upgrades > 0:
        print(f"✅ Test 5 PASSED - Authority upgrades: SEPP={sepp_upgrades}, LEP={lep_upgrades}")
        tests_passed += 1
    else:
        print(f"❌ Test 5 FAILED - No authority upgrades found")
    
    conn.close()
    
    # Generate test report
    test_report = {
        "test_suite": "PRP-K6 Database Integrity",
        "timestamp": datetime.now().isoformat(),
        "tests_passed": tests_passed,
        "tests_total": tests_total,
        "success_rate": (tests_passed / tests_total) * 100,
        "authority_distribution": authority_types if 'authority_types' in locals() else {},
        "precedence_distribution": precedence_levels if 'precedence_levels' in locals() else {},
        "traceability_percent": traceability_percent if 'traceability_percent' in locals() else 0
    }
    
    with open('prp_k6_database_test_report.json', 'w') as f:
        json.dump(test_report, f, indent=2)
    
    print(f"\n=== DATABASE INTEGRITY TESTING COMPLETE ===")
    print(f"Tests Passed: {tests_passed}/{tests_total} ({(tests_passed/tests_total)*100:.1f}%)")
    
    return tests_passed == tests_total

if __name__ == "__main__":
    success = test_database_integrity()
    exit(0 if success else 1)
```

#### **Test Suite 3.3: API Response Validation**
```python
#!/usr/bin/env python3
# test_api_response_validation.py

import requests
import json
from datetime import datetime
import time

def test_api_responses():
    """Test API response structure and legal compliance fields."""
    
    print("=== PRP-K6 API RESPONSE VALIDATION ===")
    
    base_url = "http://localhost:3007/api/setbacks/calculate"
    
    test_cases = [
        {
            "name": "R2 Marrickville Test",
            "payload": {
                "property_id": 1962876,
                "property_zone": "R2",
                "lot_geometry": {
                    "hasM": False,
                    "hasZ": False,
                    "rings": [[[0,0],[10,0],[10,20],[0,20],[0,0]]],
                    "spatialReference": {"wkid": 4326}
                }
            }
        },
        {
            "name": "R1 Ashfield Test",
            "payload": {
                "property_id": 1962876,
                "property_zone": "R1",
                "lot_geometry": {
                    "hasM": False,
                    "hasZ": False,
                    "rings": [[[0,0],[15,0],[15,25],[0,25],[0,0]]],
                    "spatialReference": {"wkid": 4326}
                }
            }
        }
    ]
    
    test_results = []
    
    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        
        start_time = time.time()
        response = requests.post(base_url, json=test_case['payload'], timeout=30)
        response_time = (time.time() - start_time) * 1000
        
        if response.status_code != 200:
            print(f"❌ HTTP Error: {response.status_code}")
            continue
        
        data = response.json()
        
        # Test response structure
        required_fields = [
            'success', 'setback_results', 'legal_compliance',
            'processing_time_ms', 'processing_method'
        ]
        
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            print(f"❌ Missing fields: {missing_fields}")
            continue
        
        # Test legal compliance structure
        legal_compliance = data.get('legal_compliance', {})
        legal_required = [
            'controlling_authority', 'legal_justification',
            'audit_trail', 'conflict_resolution_method'
        ]
        
        legal_missing = [field for field in legal_required if field not in legal_compliance]
        
        if legal_missing:
            print(f"❌ Missing legal fields: {legal_missing}")
            continue
        
        # Validate controlling authority
        authority = legal_compliance.get('controlling_authority')
        if authority not in ['SEPP', 'LEP', 'DCP']:
            print(f"❌ Invalid authority: {authority}")
            continue
        
        # Validate audit trail
        audit_trail = legal_compliance.get('audit_trail', [])
        if not audit_trail or len(audit_trail) == 0:
            print(f"❌ Empty audit trail")
            continue
        
        # Validate response time
        if response_time > 2000:  # 2 second limit
            print(f"⚠️ Slow response: {response_time:.1f}ms")
        
        test_result = {
            "test_case": test_case['name'],
            "success": True,
            "response_time_ms": response_time,
            "controlling_authority": authority,
            "audit_trail_entries": len(audit_trail),
            "setback_results_count": len(data.get('setback_results', [])),
            "legal_justification_length": len(legal_compliance.get('legal_justification', ''))
        }
        
        test_results.append(test_result)
        print(f"✅ {test_case['name']} PASSED")
        print(f"   Authority: {authority}")
        print(f"   Response: {response_time:.1f}ms")
        print(f"   Audit entries: {len(audit_trail)}")
    
    # Generate test report
    report = {
        "test_suite": "PRP-K6 API Response Validation",
        "timestamp": datetime.now().isoformat(),
        "tests_total": len(test_cases),
        "tests_passed": len(test_results),
        "success_rate": (len(test_results) / len(test_cases)) * 100,
        "test_results": test_results
    }
    
    with open('prp_k6_api_test_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n=== API RESPONSE VALIDATION COMPLETE ===")
    print(f"Tests Passed: {len(test_results)}/{len(test_cases)} ({(len(test_results)/len(test_cases))*100:.1f}%)")
    
    return len(test_results) == len(test_cases)

if __name__ == "__main__":
    success = test_api_responses()
    exit(0 if success else 1)
```

### **Phase 4: Performance and Integration Testing**

#### **Task 4.1: Load Testing**
```bash
#!/bin/bash
# load_test_hierarchy.sh

echo "=== PRP-K6 LOAD TESTING ==="

# Test concurrent requests with hierarchy engine
echo "Testing 10 concurrent requests..."

for i in {1..10}; do
  curl -s -X POST http://localhost:3007/api/setbacks/calculate \
    -H "Content-Type: application/json" \
    -d '{"property_id": '$i', "property_zone": "R2", "lot_geometry": {"hasM": false, "hasZ": false, "rings": [[[0,0],[10,0],[10,20],[0,20],[0,0]]], "spatialReference": {"wkid": 4326}}}' \
    -w "Request $i: %{time_total}s\n" \
    -o /dev/null &
done

wait

echo "Load testing complete"
```

#### **Task 4.2: Regression Testing**
```bash
#!/bin/bash
# regression_test_suite.sh

echo "=== PRP-K6 REGRESSION TESTING ==="

# Ensure all previous functionality still works
test_commands=(
  "bash test_authority_precedence.sh"
  "python3 test_database_integrity.py"  
  "python3 test_api_response_validation.py"
  "bash load_test_hierarchy.sh"
)

passed=0
total=${#test_commands[@]}

for cmd in "${test_commands[@]}"; do
  echo "Running: $cmd"
  if $cmd; then
    echo "✅ $cmd PASSED"
    ((passed++))
  else
    echo "❌ $cmd FAILED"
  fi
  echo ""
done

echo "=== REGRESSION TESTING SUMMARY ==="
echo "Passed: $passed/$total tests"

if [ $passed -eq $total ]; then
  echo "🎉 ALL REGRESSION TESTS PASSED"
  echo "PRP-K6 ready for production deployment"
  exit 0
else
  echo "❌ REGRESSION TESTS FAILED"
  echo "Fix failing tests before deployment"
  exit 1
fi
```

## Success Criteria

### **Functional Requirements ✅:**
1. **Authority Precedence**: SEPP overrides LEP and DCP, LEP overrides DCP
2. **Mixed Authority Distribution**: Minimum 5 SEPP rules, 10 LEP rules, 25 DCP rules
3. **Legal Audit Trail**: Every response includes complete decision reasoning
4. **API Response Enhancement**: Legal compliance section in all responses
5. **Graceful Fallback**: DCP-only system maintains if hierarchy fails

### **Performance Requirements ⚡:**
1. **Response Time**: <1000ms including hierarchy processing
2. **Concurrent Load**: Handle 10+ simultaneous requests
3. **Database Performance**: Hierarchy queries <100ms
4. **Memory Usage**: No memory leaks during extended operation

### **Data Quality Requirements 📊:**
1. **Authority Accuracy**: Correct SEPP/LEP/DCP classification 
2. **Source Traceability**: 95%+ rules linked to legal documents
3. **Conflict Resolution**: Proper handling of contradictory provisions
4. **Audit Completeness**: Full decision path documentation

## Risk Mitigation

### **Technical Risks:**
- **Hierarchy Engine Bugs**: Comprehensive unit and integration testing
- **Performance Degradation**: Load testing and optimization
- **Database Corruption**: Automated backups before authority upgrades

### **Compatibility Risks:**  
- **API Breaking Changes**: Maintain backward compatibility
- **Frontend Integration**: Gradual rollout with feature flags
- **Third-party Dependencies**: Version pinning and compatibility testing

## Deployment Strategy

### **Phase Rollout:**
1. **Development**: Complete implementation and testing
2. **Staging**: Deploy with real NSW planning data
3. **Production**: Gradual rollout with monitoring
4. **Full Release**: Complete hierarchy system activation

### **Rollback Plan:**
- **Database rollback** scripts for authority downgrades
- **File system rollback** (restore .bak files)
- **API fallback** mechanisms maintained

## Completion Verification

### **Automated Checks:**
```bash
# Final verification script
bash prp_k6_final_verification.sh

# Expected outputs:
# ✅ sepp-lep-processor.ts active (not .bak)
# ✅ Mixed authority distribution in database
# ✅ API responses include legal_compliance section
# ✅ All test suites pass (100% success rate)
# ✅ Performance within acceptable limits
# ✅ Graceful fallback functional
```

### **Manual Verification:**
1. **Real Property Queries**: Test with actual Inner West addresses
2. **Legal Authority Validation**: Verify SEPP/LEP precedence with planning experts
3. **User Acceptance**: Frontend displays legal reasoning clearly
4. **Documentation**: Complete system documentation updated

---

## Timeline

### **Week 1: Core Implementation**
- Restore hierarchy processor
- Upgrade zone rule authority levels
- Basic API integration
- Unit testing

### **Week 2: Integration & Testing**
- Complete API integration
- Comprehensive test suite development
- Performance optimization
- Error handling enhancement

### **Week 3: Validation & Deployment**
- Regression testing
- Load testing
- User acceptance testing
- Production deployment

---

**PRP-K6 delivers a fully functional SEPP > LEP > DCP hierarchy system with comprehensive testing, transforming the compliance engine into a complete NSW planning law implementation with proper legal authority precedence and audit trails.** 🎯⚖️