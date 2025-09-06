#!/bin/bash
# test_authority_precedence.sh - PRP-K6 Authority Precedence Testing

echo "=== PRP-K6 AUTHORITY PRECEDENCE TESTING ==="

# Test 1: Basic API Response with Legal Compliance
echo "Test 1: API returns legal_compliance section"
RESPONSE=$(curl -s -X POST http://localhost:3007/api/setbacks/calculate \
  -H "Content-Type: application/json" \
  -d '{"property_id": 1962876, "property_zone": "R2", "lot_geometry": {"hasM": false, "hasZ": false, "rings": [[[0,0],[10,0],[10,20],[0,20],[0,0]]], "spatialReference": {"wkid": 4326}}}')

echo "Response preview:"
echo $RESPONSE | head -c 200
echo "..."

# Check if legal_compliance exists in response  
HAS_LEGAL_COMPLIANCE=$(echo $RESPONSE | venv_linux/Scripts/python.exe -c "
import json, sys
try:
    data = json.load(sys.stdin)
    has_legal = 'legal_compliance' in data
    print('true' if has_legal else 'false')
except Exception as e:
    print('false')
")

if [ "$HAS_LEGAL_COMPLIANCE" = "true" ]; then
    echo "✅ Test 1 PASSED - legal_compliance section present"
else
    echo "❌ Test 1 FAILED - No legal_compliance section"
    exit 1
fi

# Test 2: Controlling Authority Detection
echo "Test 2: Controlling authority properly identified"
CONTROLLING_AUTHORITY=$(echo $RESPONSE | venv_linux/Scripts/python.exe -c "
import json, sys
try:
    data = json.load(sys.stdin)
    auth = data.get('legal_compliance', {}).get('controlling_authority', 'UNKNOWN')
    print(auth)
except Exception as e:
    print('ERROR')
")

if [ "$CONTROLLING_AUTHORITY" = "SEPP" ] || [ "$CONTROLLING_AUTHORITY" = "LEP" ] || [ "$CONTROLLING_AUTHORITY" = "DCP" ]; then
    echo "✅ Test 2 PASSED - Controlling authority: $CONTROLLING_AUTHORITY"
else
    echo "❌ Test 2 FAILED - Invalid authority: $CONTROLLING_AUTHORITY"
    exit 1
fi

# Test 3: Audit Trail Generation
echo "Test 3: Legal audit trail generated"
AUDIT_TRAIL_LENGTH=$(echo $RESPONSE | venv_linux/Scripts/python.exe -c "
import json, sys
try:
    data = json.load(sys.stdin)
    trail = data.get('legal_compliance', {}).get('audit_trail', [])
    print(len(trail))
except Exception as e:
    print('0')
")

if [ "$AUDIT_TRAIL_LENGTH" -gt 0 ]; then
    echo "✅ Test 3 PASSED - Audit trail with $AUDIT_TRAIL_LENGTH entries"
else
    echo "❌ Test 3 FAILED - No audit trail generated"
    exit 1
fi

# Test 4: Processing Method Updated
echo "Test 4: Processing method indicates hierarchy engine"
PROCESSING_METHOD=$(echo $RESPONSE | venv_linux/Scripts/python.exe -c "
import json, sys
try:
    data = json.load(sys.stdin)
    method = data.get('processing_method', '')
    print(method)
except Exception as e:
    print('ERROR')
")

if [[ "$PROCESSING_METHOD" == *"Hierarchical"* ]] || [[ "$PROCESSING_METHOD" == *"K6"* ]]; then
    echo "✅ Test 4 PASSED - Processing method: $PROCESSING_METHOD"
else
    echo "❌ Test 4 FAILED - Method doesn't indicate hierarchy: $PROCESSING_METHOD"
    exit 1
fi

# Test 5: Performance Check
echo "Test 5: Response time within acceptable limits"
start_time=$(date +%s%N)
PERF_RESPONSE=$(curl -s -X POST http://localhost:3007/api/setbacks/calculate \
  -H "Content-Type: application/json" \
  -d '{"property_id": 1962876, "property_zone": "R2", "lot_geometry": {"hasM": false, "hasZ": false, "rings": [[[0,0],[10,0],[10,20],[0,20],[0,0]]], "spatialReference": {"wkid": 4326}}}')
end_time=$(date +%s%N)

response_time=$(( (end_time - start_time) / 1000000 )) # Convert to milliseconds

if [ $response_time -lt 2000 ]; then
    echo "✅ Test 5 PASSED - Response time: ${response_time}ms"
else
    echo "⚠️ Test 5 WARNING - Slow response: ${response_time}ms (target: <2000ms)"
fi

echo ""
echo "=== AUTHORITY PRECEDENCE TESTING COMPLETE ==="
echo "✅ All core hierarchy tests passed"
echo "🎯 Legal compliance integration successful"