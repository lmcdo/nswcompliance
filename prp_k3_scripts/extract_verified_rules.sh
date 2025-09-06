#!/bin/bash
# extract_verified_rules.sh - PRP-K3 Phase 1A

echo "=== PRP-K3 PHASE 1A: HIGH-CONFIDENCE RULE EXTRACTION ==="

# Process only verified, structured data sources
venv_linux/Scripts/python.exe extract_zone_rules_phase1.py \
  --sources "public/regulatory-data/inner-west-compliance-rules.json,compliance_result.json" \
  --output-table "zone_setback_rules" \
  --confidence-threshold 0.9 \
  --verify-against-source true

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
    cursor.execute('SELECT COUNT(*) FROM zone_setback_rules WHERE confidence >= 0.9')
    count = cursor.fetchone()[0]
    print(count)
    conn.close()
except Exception as e:
    print(0)
")
echo "Phase 1A Complete: $RULES_COUNT high-confidence rules extracted"

# Create completion marker
if [ "$RULES_COUNT" -ge 6 ]; then
    echo "Phase1A_completed" > prp_checkpoints/K3_Phase1A_completed.marker
    echo "✅ Phase 1A: PASSED - Extracted $RULES_COUNT verified rules"
    exit 0
else
    echo "❌ Phase 1A: FAILED - Only $RULES_COUNT rules extracted (expected ≥6)"
    exit 1
fi