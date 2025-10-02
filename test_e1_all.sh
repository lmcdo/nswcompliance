#!/bin/bash
echo "Testing E1 zone with all development types:"
echo "============================================"

for dev_type in dwelling_house secondary_dwelling dual_occupancy multi_dwelling shop_top_housing residential_flat boarding_house child_care commercial; do
  status=$(curl -s "http://localhost:3007/api/compliance/constraints" \
    -X POST \
    -H "Content-Type: application/json" \
    -d "{\"zone\":\"E1\",\"lga\":\"Test\",\"developmentType\":\"$dev_type\"}" \
    | python -c "import sys,json; d=json.load(sys.stdin); print(d['data']['permission_status'])" 2>/dev/null)
  
  printf "%-25s %s\n" "$dev_type" "$status"
done
