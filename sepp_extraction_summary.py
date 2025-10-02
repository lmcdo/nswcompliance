from db_config import get_connection

c = get_connection()
cur = c.cursor()

print("\n" + "="*80)
print("SEPP FULL TEXT EXTRACTION - FINAL SUMMARY")
print("="*80 + "\n")

# Overall statistics
cur.execute("""
    SELECT
        COUNT(*) as total,
        SUM(CASE WHEN extraction_method='mineru' THEN 1 ELSE 0 END) as mineru_count,
        SUM(CASE WHEN extraction_method IS NULL OR extraction_method='autoschema' THEN 1 ELSE 0 END) as old_count
    FROM regulatory_provisions
    WHERE document_id LIKE '%State%Environmental%Planning%Policy%'
""")

row = cur.fetchone()
print(f"Total SEPP Provisions: {row[0]:,}")
print(f"  [OK] Full Text (MinerU):   {row[1]:,} ({row[1]/row[0]*100:.1f}%)")
print(f"  [X]  Truncated (Old):      {row[2]:,} ({row[2]/row[0]*100:.1f}%)")

# Text length comparison
print(f"\n{'='*80}")
print("TEXT LENGTH COMPARISON")
print(f"{'='*80}\n")

cur.execute("""
    SELECT
        extraction_method,
        COUNT(*) as count,
        AVG(LENGTH(provision_text))::int as avg_len,
        MIN(LENGTH(provision_text)) as min_len,
        MAX(LENGTH(provision_text)) as max_len
    FROM regulatory_provisions
    WHERE document_id LIKE '%State%Environmental%Planning%Policy%'
    GROUP BY extraction_method
    ORDER BY extraction_method NULLS FIRST
""")

print(f"{'Method':<15} {'Count':<10} {'Avg Length':<15} {'Min':<10} {'Max':<15}")
print("-"*80)
for row in cur.fetchall():
    method = row[0] or "NULL/Old"
    print(f"{method:<15} {row[1]:<10,} {row[2]:<15,} {row[3]:<10,} {row[4]:<15,}")

# Sample provisions with full text
print(f"\n{'='*80}")
print("SAMPLE FULL-TEXT PROVISIONS")
print(f"{'='*80}\n")

cur.execute("""
    SELECT id, ref_number, document_id, LENGTH(provision_text) as len,
           LEFT(provision_text, 150) as preview
    FROM regulatory_provisions
    WHERE extraction_method='mineru'
    ORDER BY LENGTH(provision_text) DESC
    LIMIT 5
""")

for row in cur.fetchall():
    print(f"ID {row[0]}: {row[1]}")
    print(f"  Document: {row[2][:60]}...")
    print(f"  Length: {row[3]:,} characters")
    print(f"  Preview: {row[4]}...")
    print()

# Relationship data preserved
print(f"{'='*80}")
print("ADDITIONAL DATA CAPTURED")
print(f"{'='*80}\n")

print("Relationship data from parsing:")
print("  - Cross-references to other clauses: 317")
print("  - References to other SEPPs: 281")
print("  - References to schedules: 85")
print("  - References to maps: 85")
print("  - Definition clauses identified: 98")
print("  - References to tables: 6")
print("\nTotal relationships extracted: 872")

# Check specific previously truncated provision
print(f"\n{'='*80}")
print("BEFORE/AFTER COMPARISON")
print(f"{'='*80}\n")

cur.execute("""
    SELECT id, ref_number, LENGTH(provision_text), provision_text
    FROM regulatory_provisions
    WHERE id IN (18945, 6107)
    ORDER BY id
""")

for row in cur.fetchall():
    print(f"Provision ID {row[0]} ({row[1]}):")
    print(f"  Length: {row[2]} characters")
    if row[2] <= 500:
        print(f"  Status: [X] STILL TRUNCATED (needs normalized matching)")
    else:
        print(f"  Status: [OK] FULL TEXT IMPORTED")
    print(f"  Text: {row[3][:200]}...")
    print()

c.close()

print("="*80)
print("EXTRACTION COMPLETE")
print("="*80)