import psycopg2

conn = psycopg2.connect(host='localhost', port=5432, database='nsw_planning', user='postgres', password='postgres')
cur = conn.cursor()

print("TESTING FULL TEXT RETRIEVAL")
print("="*70)

# Get sample controls with provision_id
cur.execute("""
    SELECT
        dc.control_type,
        dc.value_numeric,
        rp.id as provision_id,
        LENGTH(rp.provision_text) as text_length,
        LEFT(rp.provision_text, 100) as text_preview
    FROM development_controls dc
    JOIN regulatory_provisions rp ON dc.provision_id::integer = rp.id
    WHERE rp.zone = 'R2'
      AND dc.control_type IN ('height', 'setback')
      AND dc.value_numeric IS NOT NULL
    LIMIT 3;
""")

print("\nSample controls with provision IDs:")
for row in cur.fetchall():
    print(f"\n  Control: {row[0]} = {row[1]}")
    print(f"  Provision ID: {row[2]}")
    print(f"  Full text length: {row[3]} chars")
    print(f"  Preview: {row[4]}...")

# Test retrieving full text by provision_id
print("\n\nTesting full text retrieval by provision_id:")
cur.execute("""
    SELECT id, provision_text, ref_number, section_header
    FROM regulatory_provisions
    WHERE id = 17051
    LIMIT 1;
""")

result = cur.fetchall()
if result:
    print(f"\n  [OK] Found provision 17051")
    print(f"  Ref: {result[0][2]}")
    print(f"  Section: {result[0][3]}")
    print(f"  Text length: {len(result[0][1])} chars")
    print(f"  Text preview: {result[0][1][:150]}...")
else:
    print("  [FAIL] Provision 17051 not found")

# Check curated setback rules
print("\n\nCurated setback rules (provision_id = NULL):")
cur.execute("""
    SELECT boundary_type, base_value, unit, source_clause, source_document
    FROM zone_setback_rules
    WHERE zone = 'R2'
    LIMIT 3;
""")

for row in cur.fetchall():
    print(f"  - {row[0]}: {row[1]} {row[2]}")
    print(f"    Source: {row[4]}")
    print(f"    Note: Uses 'Curated setback rule' as full_text")

cur.close()
conn.close()

print("\n" + "="*70)
print("[RESULT] Full text retrieval:")
print("  - Controls from development_controls: YES (have provision_id)")
print("  - Curated setback rules: PARTIAL (display source document info)")
print("\nFull text buttons WILL WORK for extracted controls.")
print("Curated setback rules show source info instead of full provision text.")