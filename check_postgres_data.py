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

# Check total provisions with zones
cursor.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE zone IS NOT NULL AND zone != ''")
zone_count = cursor.fetchone()[0]
print(f"Provisions with zones: {zone_count}")

# Check setback provisions by zone
cursor.execute("""
    SELECT zone, COUNT(*) 
    FROM regulatory_provisions 
    WHERE zone IS NOT NULL 
    AND zone != '' 
    AND provision_text ILIKE '%setback%' 
    GROUP BY zone 
    ORDER BY COUNT(*) DESC 
    LIMIT 10
""")
results = cursor.fetchall()
print("Zone setback counts:")
for zone, count in results:
    print(f"  {zone}: {count}")

# Check for R2 specific provisions
cursor.execute("""
    SELECT COUNT(*) 
    FROM regulatory_provisions 
    WHERE zone = 'R2' 
    AND provision_text ILIKE '%setback%'
""")
r2_count = cursor.fetchone()[0]
print(f"R2 setback provisions: {r2_count}")

# Sample R2 setback provisions
cursor.execute("""
    SELECT ref_number, provision_text, document_id 
    FROM regulatory_provisions 
    WHERE zone = 'R2' 
    AND provision_text ILIKE '%setback%'
    LIMIT 5
""")
r2_samples = cursor.fetchall()
print("\nSample R2 setback provisions:")
for ref, text, doc in r2_samples:
    print(f"  {ref}: {text[:100]}... (doc: {doc})")

conn.close()