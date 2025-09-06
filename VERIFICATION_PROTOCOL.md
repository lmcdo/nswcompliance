# VERIFICATION PROTOCOL FOR CLAUDE CODE FIXES

## Purpose
This document establishes mandatory evidence requirements to prevent false claims about fixes working when they don't.

## 1. MANDATORY EVIDENCE PROTOCOL

Before Claude can claim ANY fix works, Claude MUST provide:

### A. API Response Evidence
```bash
# Test the actual API endpoint and save response
curl -X POST http://localhost:8006/enhanced-complete-assessment \
  -H "Content-Type: application/json" \
  -d '{"address":"34 Pile St, Dulwich Hill NSW 2203, Australia","query_type":"complete_assessment"}' \
  | python -m json.tool > actual_api_response.json

# Show the exact response file
cat actual_api_response.json
```

### B. Database Query Verification
Create and run `test_real_database.py`:
```python
#!/usr/bin/env python3
import sqlite3
import json

def verify_database():
    conn = sqlite3.connect('nsw_planning.db')
    cur = conn.cursor()
    
    print("=== ACTUAL DATABASE CONTENT VERIFICATION ===")
    
    # 1. Count setback records
    setbacks = cur.execute("SELECT COUNT(*) FROM development_controls WHERE control_type = 'setback'").fetchone()[0]
    print(f"Total setback records: {setbacks}")
    
    # 2. Show sample setback values
    sample_setbacks = cur.execute("""
        SELECT dc.value_numeric, dc.value_text, rp.document_id 
        FROM development_controls dc 
        JOIN regulatory_provisions rp ON dc.provision_id = rp.id 
        WHERE dc.control_type = 'setback' AND dc.value_numeric > 0
        LIMIT 5
    """).fetchall()
    
    print("Sample setback values:")
    for val_num, val_text, doc in sample_setbacks:
        print(f"  {val_num}m - '{val_text}' from {doc[:50]}...")
    
    # 3. Count connected requirements
    total_provisions = cur.execute("SELECT COUNT(*) FROM regulatory_provisions").fetchone()[0]
    print(f"Total regulatory provisions: {total_provisions}")
    
    # 4. Count development controls by type
    control_types = cur.execute("""
        SELECT control_type, COUNT(*) as count 
        FROM development_controls 
        GROUP BY control_type 
        ORDER BY count DESC
    """).fetchall()
    
    print("Development controls by type:")
    for ctrl_type, count in control_types:
        print(f"  {ctrl_type}: {count}")
    
    conn.close()
    return {
        'setback_count': setbacks,
        'total_provisions': total_provisions,
        'sample_setbacks': sample_setbacks
    }

if __name__ == "__main__":
    verify_database()
```

### C. Frontend Response Parsing
```bash
# Extract specific values from API response
echo "=== SETBACK CALCULATIONS ==="
curl -s localhost:8006/enhanced-complete-assessment \
  -H "Content-Type: application/json" \
  -d '{"address":"34 Pile St, Dulwich Hill NSW 2203, Australia","query_type":"complete_assessment"}' \
  | jq '.setback_calculations'

echo "=== CONNECTED REQUIREMENTS COUNTS ==="
curl -s localhost:8006/enhanced-complete-assessment \
  -H "Content-Type: application/json" \
  -d '{"address":"34 Pile St, Dulwich Hill NSW 2203, Australia","query_type":"complete_assessment"}' \
  | jq '.connected_requirements | {
    direct_connections: (.direct_connections | length),
    zone_requirements: (.zone_requirements | length), 
    development_context: (.development_context | length),
    regulatory_links: (.regulatory_links | length)
  }'

echo "=== VISUAL CONTENT COUNT ==="
curl -s localhost:8006/enhanced-complete-assessment \
  -H "Content-Type: application/json" \
  -d '{"address":"34 Pile St, Dulwich Hill NSW 2203, Australia","query_type":"complete_assessment"}' \
  | jq '.visual_content | length'
```

## 2. AUTOMATED VERIFICATION SCRIPT

Create `verify_fix.sh`:
```bash
#!/bin/bash
echo "======================================="
echo "MANDATORY VERIFICATION FOR CLAUDE FIXES"
echo "======================================="

echo ""
echo "1. TESTING DATABASE CONTENT:"
echo "----------------------------"
python test_real_database.py

echo ""
echo "2. TESTING API RESPONSE:"
echo "-----------------------"
curl -s localhost:8006/enhanced-complete-assessment \
  -H "Content-Type: application/json" \
  -d '{"address":"34 Pile St, Dulwich Hill NSW 2203, Australia","query_type":"complete_assessment"}' \
  | jq '.setback_calculations'

echo ""
echo "3. TESTING CONNECTED REQUIREMENTS:"
echo "---------------------------------"
curl -s localhost:8006/enhanced-complete-assessment \
  -H "Content-Type: application/json" \
  -d '{"address":"34 Pile St, Dulwich Hill NSW 2203, Australia","query_type":"complete_assessment"}' \
  | jq '.connected_requirements | {
    direct: (.direct_connections | length),
    zone: (.zone_requirements | length), 
    context: (.development_context | length)
  }'

echo ""
echo "4. FRONTEND UI VERIFICATION:"
echo "----------------------------"
echo "MANUAL STEP: Open localhost:3000 and verify:"
echo "- Setbacks show actual values (not 'Not determined')"
echo "- Visual Guides shows count > 0" 
echo "- Connected Rules shows count > 0"
echo "- Progressive disclosure panels work"

echo ""
echo "======================================="
echo "VERIFICATION COMPLETE"
echo "======================================="
```

## 3. MANDATORY REQUIREMENTS FOR CLAUDE

### Before claiming ANY fix works, Claude MUST:

1. **Create the verification files** above if they don't exist
2. **Run the verification script** and show full output
3. **Provide screenshot evidence** of the frontend UI working
4. **Show the actual API response JSON** with real data
5. **Demonstrate database contains real values** (not fallbacks)

### Forbidden Claims Without Evidence:

- ❌ "The system is working"
- ❌ "I tested it and it works"  
- ❌ "The logic should work"
- ❌ "Everything is fixed now"
- ❌ "The API is returning correct values"

### Required Evidence Format:

```
## VERIFICATION EVIDENCE

### Database Content:
[Output from test_real_database.py]

### API Response:
[Full JSON response from curl command]

### Frontend Counts:
- Visual Guides: X (expected > 0)
- Connected Rules: Y (expected > 0) 
- Setbacks: [actual values, not "Not determined"]

### Screenshot:
[Screenshot of localhost:3000 working UI]
```

## 4. ENFORCEMENT

**The user should reject ANY fix claim that doesn't include:**
1. Database verification output
2. Complete API response  
3. Frontend UI evidence
4. Specific numeric values (not generic claims)

**Make Claude run `verify_fix.sh` for every claimed fix.**

## File Locations

- This protocol: `VERIFICATION_PROTOCOL.md`
- Database test: `test_real_database.py` (to be created)
- Verification script: `verify_fix.sh` (to be created)
- API responses: `actual_api_response.json` (generated each test)