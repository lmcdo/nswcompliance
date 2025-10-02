from db_config import get_connection

c = get_connection()
cur = c.cursor()

print("=== FULL PROVISION TEXT ANALYSIS ===\n")

# Sample provisions from different Planning Portal detections
provision_ids = [
    # Thermal Energy from Waste
    18945,
    # Climate Zones
    6172, 6169,
    # Water Use
    6107, 6131
]

print("CHECKING FULL TEXT LENGTH AND CONTENT\n")
print("="*80 + "\n")

for prov_id in provision_ids:
    cur.execute("""
        SELECT id, ref_number, provision_text, document_id, provision_type
        FROM regulatory_provisions
        WHERE id = %s
    """, (prov_id,))

    row = cur.fetchone()
    if row:
        text = row[2]
        text_length = len(text)

        print(f"PROVISION ID: {row[0]}")
        print(f"Reference: {row[1]}")
        print(f"Document: {row[3]}")
        print(f"Type: {row[4]}")
        print(f"Text Length: {text_length} characters ({text_length/1000:.1f}KB)")
        print(f"\nFULL TEXT:\n")
        print(text)
        print("\n" + "="*80 + "\n")

print("\n=== TEXT LENGTH SUMMARY ===\n")

# Get average and distribution of text lengths
cur.execute("""
    SELECT
        provision_type,
        COUNT(*) as count,
        AVG(LENGTH(provision_text)) as avg_length,
        MIN(LENGTH(provision_text)) as min_length,
        MAX(LENGTH(provision_text)) as max_length
    FROM regulatory_provisions
    WHERE document_id LIKE '%Sustainable_Buildings%'
    OR document_id LIKE '%Planning_Systems%'
    OR document_id LIKE '%Transport_and_Infrastructure%'
    GROUP BY provision_type
    ORDER BY avg_length DESC
    LIMIT 20
""")

rows = cur.fetchall()
print("Provision Type | Count | Avg Length | Min | Max")
print("-" * 70)
for row in rows:
    print(f"{row[0][:30]:30} | {row[1]:5d} | {row[2]:10.0f} | {row[3]:4d} | {row[4]:5d}")

print("\n" + "="*80 + "\n")

# Check for provisions with very short text (might be incomplete)
print("PROVISIONS WITH SHORT TEXT (< 100 chars) - Possibly Incomplete:\n")

cur.execute("""
    SELECT id, ref_number, provision_text, document_id
    FROM regulatory_provisions
    WHERE (document_id LIKE '%Sustainable_Buildings%'
       OR document_id LIKE '%Transport_and_Infrastructure%'
       OR document_id LIKE '%Planning_Systems%')
    AND LENGTH(provision_text) < 100
    LIMIT 10
""")

rows = cur.fetchall()
for row in rows:
    print(f"ID {row[0]}: {row[1]} - {len(row[2])} chars")
    print(f"  {row[2]}")
    print()

print("="*80 + "\n")

# Check specific thermal provision for completeness
print("DETAILED CHECK: Thermal Energy Waste Provision 18945\n")

cur.execute("""
    SELECT provision_text
    FROM regulatory_provisions
    WHERE id = 18945
""")

text = cur.fetchone()[0]
print(f"Total length: {len(text)} characters\n")

# Check if it contains key elements that should be in a complete provision
checks = [
    ("Has subsections (a), (b)", "(a)" in text and "(b)" in text),
    ("Has dollar amount", "$30 million" in text or "$30,000,000" in text),
    ("Mentions thermal treatment", "thermal treatment" in text.lower()),
    ("Mentions waste", "waste" in text.lower()),
    ("Has full clause structure", len(text) > 500),
]

for check, result in checks:
    status = "✓" if result else "✗"
    print(f"{status} {check}")

c.close()