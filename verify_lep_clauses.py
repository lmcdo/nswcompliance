import psycopg2

conn = psycopg2.connect(host='localhost', database='nsw_planning', user='postgres', password='postgres')
cur = conn.cursor()

cur.execute("""
    SELECT clause_number, clause_title, development_type, requirements
    FROM lep_development_type_clauses
    WHERE lga='Inner West' AND clause_number IN ('4.3', '4.4', '5.4')
    ORDER BY clause_number
""")

print("Inner West LEP 2022 clauses:")
for row in cur.fetchall():
    print(f"\n  Clause {row[0]}: {row[1]}")
    if row[2]:
        print(f"    Dev type: {row[2]}")
    if row[3]:
        print(f"    Requirements: {row[3][:2]}")  # Show first 2 requirements

conn.close()
print("\n[OK] Verification complete")
