#!/usr/bin/env python3
import psycopg2

conn = psycopg2.connect(
    host='localhost',
    database='nsw_planning', 
    user='postgres',
    password='postgres',
    port='5432'
)
cursor = conn.cursor()

print("=== CURRENT ZONE COVERAGE IN DATABASE ===\n")

# Check what we have
cursor.execute("""
    SELECT council, zone, boundary_type, COUNT(*) 
    FROM zone_setback_rules 
    GROUP BY council, zone, boundary_type
    ORDER BY council, zone, boundary_type
""")
results = cursor.fetchall()

current_coverage = {}
for council, zone, boundary, count in results:
    if council not in current_coverage:
        current_coverage[council] = {}
    if zone not in current_coverage[council]:
        current_coverage[council][zone] = {}
    current_coverage[council][zone][boundary] = count

for council in sorted(current_coverage.keys()):
    print(f"{council}:")
    for zone in sorted(current_coverage[council].keys()):
        boundaries = current_coverage[council][zone]
        print(f"  {zone}: {', '.join([f'{b}({c})' for b, c in boundaries.items()])}")
    print()

print("\n=== MISSING COVERAGE ===\n")

# Check what zones exist in the main provisions table
cursor.execute("""
    SELECT DISTINCT zone 
    FROM regulatory_provisions 
    WHERE zone IS NOT NULL AND zone != ''
    ORDER BY zone
""")
all_zones = [row[0] for row in cursor.fetchall()]

print(f"Zones in regulatory_provisions table: {', '.join(all_zones)}\n")

# Check for Ashfield, Leichhardt, Marrickville specific documents
cursor.execute("""
    SELECT DISTINCT document_id 
    FROM regulatory_provisions 
    WHERE (document_id ILIKE '%ashfield%' 
           OR document_id ILIKE '%leichhardt%' 
           OR document_id ILIKE '%marrickville%')
    AND provision_text ILIKE '%setback%'
    LIMIT 10
""")
docs = cursor.fetchall()
print("Sample Inner West setback documents:")
for doc in docs:
    print(f"  - {doc[0]}")

# Check for zone data in JSON files
print("\n=== EXPECTED FULL COVERAGE ===")
print("""
Inner West Council (amalgamated from 3 councils) should have setback rules for:

Ashfield (former LGA):
  - Residential: R1, R2, R3, R4
  - Business: B1, B2, B4, B5, B6
  - Industrial: IN1, IN2
  - Special Purpose: SP1, SP2
  
Leichhardt (former LGA):
  - Residential: R1, R2, R3, R4
  - Business: B1, B2, B4, B7
  - Industrial: IN1, IN2
  - Recreation: RE1, RE2
  
Marrickville (former LGA):
  - Residential: R1, R2, R3, R4
  - Business: B1, B2, B4, B5, B6, B7
  - Industrial: IN1, IN2
  - Recreation: RE1
  - Special Purpose: SP2

CURRENT STATUS:
  ✅ Ashfield: R2 only (3 rules)
  ✅ Leichhardt: R2 only (3 rules)  
  ❌ Marrickville: NONE (0 rules)
  
MISSING: All other zones for all councils!
""")

conn.close()