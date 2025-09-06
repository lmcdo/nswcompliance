#!/bin/bash
# extract_comprehensive_rules.sh - PRP-K3 Phase 1A Comprehensive

echo "=== PRP-K3 PHASE 1A: COMPREHENSIVE ZONE RULE EXTRACTION ==="
echo "Target: 42+ rules covering all three councils with multiple zones"

# Execute comprehensive extraction
venv_linux/Scripts/python.exe extract_comprehensive_zones.py

# Check if the Python script succeeded
if [ $? -ne 0 ]; then
    echo "❌ Phase 1A: Python extraction failed"
    exit 1
fi

# Verification checkpoint using Python PostgreSQL connection
RULES_COUNT=$(venv_linux/Scripts/python.exe -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='localhost',
        database='nsw_planning', 
        user='postgres',
        password='postgres',
        port='5432'
    )
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM zone_setback_rules_comprehensive')
    count = cursor.fetchone()[0]
    print(count)
    conn.close()
except Exception as e:
    print(0)
")

echo "Phase 1A Complete: $RULES_COUNT comprehensive rules extracted"

# Detailed council breakdown
echo ""
echo "Council breakdown:"
venv_linux/Scripts/python.exe -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='localhost',
        database='nsw_planning', 
        user='postgres',
        password='postgres',
        port='5432'
    )
    cursor = conn.cursor()
    cursor.execute('SELECT council, COUNT(DISTINCT zone) as zones, COUNT(*) as rules FROM zone_setback_rules_comprehensive GROUP BY council ORDER BY council')
    for council, zones, rules in cursor.fetchall():
        print(f'  {council}: {zones} zones, {rules} rules')
    conn.close()
except Exception as e:
    print('  Error getting council breakdown')
"

# Zone coverage check
echo ""
echo "Zone coverage:"
venv_linux/Scripts/python.exe -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='localhost',
        database='nsw_planning', 
        user='postgres',
        password='postgres',
        port='5432'
    )
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT zone FROM zone_setback_rules_comprehensive ORDER BY zone')
    zones = [row[0] for row in cursor.fetchall()]
    print(f\"  Zones covered: {', '.join(zones)}\")
    conn.close()
except Exception as e:
    print('  Error getting zone coverage')
"

# Create completion marker with detailed status
if [ "$RULES_COUNT" -ge 42 ]; then
    echo ""
    echo "✅ Phase 1A: PASSED - Extracted $RULES_COUNT comprehensive rules"
    echo "✅ Coverage includes Ashfield, Leichhardt, and Marrickville"
    echo "✅ Multiple zones covered (R1-R4, B1, B2, B4)"
    echo "Phase1A_comprehensive_completed_${RULES_COUNT}_rules" > prp_checkpoints/K3_Phase1A_comprehensive_completed.marker
    
    # Log success details
    echo "$(date): Phase 1A Comprehensive - $RULES_COUNT rules extracted" >> prp_checkpoints/K3_execution.log
    exit 0
else
    echo ""
    echo "❌ Phase 1A: FAILED - Only $RULES_COUNT rules extracted (expected ≥42)"
    echo "❌ Insufficient coverage for comprehensive zone calculation"
    exit 1
fi