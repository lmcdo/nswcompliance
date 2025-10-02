#!/bin/bash

# Test script to demonstrate what should change with different development types
# Run this to verify the system correctly filters provisions by development type

echo "=================================================="
echo "DEVELOPMENT TYPE FILTERING TEST"
echo "=================================================="
echo ""

# Test address
ADDRESS="54 ILLAWARRA ROAD MARRICKVILLE 2204"
ZONE="R2"
LGA="INNER WEST"
API="http://localhost:3007/api/compliance/constraints"

echo "Test Property: $ADDRESS"
echo "Zone: $ZONE"
echo "LGA: $LGA"
echo ""

# Test 1: Dwelling House
echo "=================================================="
echo "TEST 1: DWELLING HOUSE"
echo "=================================================="
echo ""
echo "Expected Provisions:"
echo "✓ DCP front setback: 6m (standard)"
echo "✓ SEPP shed override: 3m (Provision 16964)"
echo "✓ SEPP rear lane: 900mm (Provision 16963)"
echo ""
echo "Actual Results:"
curl -s -X POST "$API" \
  -H "Content-Type: application/json" \
  -d "{\"address\":\"$ADDRESS\",\"zone\":\"$ZONE\",\"lga\":\"$LGA\",\"developmentType\":\"Dwelling House\"}" \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"Total constraints: {len(data.get('constraints', []))}\")
for c in data.get('constraints', []):
    if 'document' in c.get('source', {}):
        doc = c['source']['document']
        val = c.get('value')
        unit = c.get('unit', '')
        typ = c.get('type')
        print(f\"  - {typ}: {val}{unit} ({doc})\")
"
echo ""

# Test 2: Secondary Dwelling
echo "=================================================="
echo "TEST 2: SECONDARY DWELLING"
echo "=================================================="
echo ""
echo "Expected Provisions:"
echo "✓ DCP front setback: 3m (REDUCED for secondary dwelling)"
echo "✓ Max size: 60m² (specific to secondary dwelling)"
echo "✓ Different SEPP provisions than dwelling house"
echo ""
echo "Actual Results:"
curl -s -X POST "$API" \
  -H "Content-Type: application/json" \
  -d "{\"address\":\"$ADDRESS\",\"zone\":\"$ZONE\",\"lga\":\"$LGA\",\"developmentType\":\"Secondary Dwelling\"}" \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"Total constraints: {len(data.get('constraints', []))}\")
for c in data.get('constraints', []):
    if 'document' in c.get('source', {}):
        doc = c['source']['document']
        val = c.get('value')
        unit = c.get('unit', '')
        typ = c.get('type')
        print(f\"  - {typ}: {val}{unit} ({doc})\")
"
echo ""

# Test 3: Multi Dwelling Housing
echo "=================================================="
echo "TEST 3: MULTI DWELLING HOUSING"
echo "=================================================="
echo ""
echo "Expected Provisions:"
echo "✓ DCP front setback: 6m"
echo "✓ Deep soil: 15% minimum"
echo "✓ Communal open space: 25m² per dwelling"
echo "✓ DIFFERENT SEPPs than dwelling house (no shed override)"
echo ""
echo "Actual Results:"
curl -s -X POST "$API" \
  -H "Content-Type: application/json" \
  -d "{\"address\":\"$ADDRESS\",\"zone\":\"$ZONE\",\"lga\":\"$LGA\",\"developmentType\":\"Multi Dwelling Housing\"}" \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"Total constraints: {len(data.get('constraints', []))}\")
for c in data.get('constraints', []):
    if 'document' in c.get('source', {}):
        doc = c['source']['document']
        val = c.get('value')
        unit = c.get('unit', '')
        typ = c.get('type')
        print(f\"  - {typ}: {val}{unit} ({doc})\")
"
echo ""

# Test 4: Check SEPP Filtering
echo "=================================================="
echo "TEST 4: SEPP PROVISION FILTERING"
echo "=================================================="
echo ""
echo "Checking if SEPP provisions change based on development type..."
echo ""

echo "Dwelling House - SEPP Provisions:"
curl -s -X POST "$API" \
  -H "Content-Type: application/json" \
  -d "{\"address\":\"$ADDRESS\",\"zone\":\"$ZONE\",\"lga\":\"$LGA\",\"developmentType\":\"Dwelling House\"}" \
  | grep -o '"document":"SEPP[^"]*"' | sort | uniq
echo ""

echo "Secondary Dwelling - SEPP Provisions:"
curl -s -X POST "$API" \
  -H "Content-Type: application/json" \
  -d "{\"address\":\"$ADDRESS\",\"zone\":\"$ZONE\",\"lga\":\"$LGA\",\"developmentType\":\"Secondary Dwelling\"}" \
  | grep -o '"document":"SEPP[^"]*"' | sort | uniq
echo ""

echo "Multi Dwelling - SEPP Provisions:"
curl -s -X POST "$API" \
  -H "Content-Type: application/json" \
  -d "{\"address\":\"$ADDRESS\",\"zone\":\"$ZONE\",\"lga\":\"$LGA\",\"developmentType\":\"Multi Dwelling Housing\"}" \
  | grep -o '"document":"SEPP[^"]*"' | sort | uniq
echo ""

# Test 5: Specific Provision Check
echo "=================================================="
echo "TEST 5: PROVISION 16964 (Shed Override) FILTERING"
echo "=================================================="
echo ""
echo "This provision should ONLY appear for development types that allow accessory buildings"
echo ""

for DEV_TYPE in "Dwelling House" "Secondary Dwelling" "Multi Dwelling Housing" "Child Care Centre"; do
  echo -n "$DEV_TYPE: "
  RESULT=$(curl -s -X POST "$API" \
    -H "Content-Type: application/json" \
    -d "{\"address\":\"$ADDRESS\",\"zone\":\"$ZONE\",\"lga\":\"$LGA\",\"developmentType\":\"$DEV_TYPE\"}" \
    | grep -o "16964" | head -1)

  if [ -z "$RESULT" ]; then
    echo "❌ NOT FOUND (correct for non-dwelling types)"
  else
    echo "✓ FOUND (should appear for dwelling house)"
  fi
done
echo ""

# Summary
echo "=================================================="
echo "SUMMARY"
echo "=================================================="
echo ""
echo "✓ Tests complete. Review results above."
echo ""
echo "Expected Behavior:"
echo "1. Different development types should return DIFFERENT provisions"
echo "2. Secondary dwelling should have reduced setbacks (3m vs 6m)"
echo "3. SEPP shed override (16964) should only appear for dwelling houses"
echo "4. Multi dwelling should have additional requirements (deep soil, etc.)"
echo ""
echo "If all types return the SAME provisions, development type filtering"
echo "is not working correctly and needs to be fixed."
echo ""