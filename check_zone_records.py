#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('nsw_planning.db')
cursor = conn.cursor()

# Get records that actually have zone data
results = cursor.execute("SELECT zone, development_type, document_id, provision_text FROM regulatory_provisions WHERE zone IS NOT NULL AND zone != '' LIMIT 20").fetchall()

print(f"Found {len(results)} records with zone data:")
print()

for i, row in enumerate(results[:10]):
 print(f"{i+1}. Zone: {row[0]}")
 print(f" DevType: {row[1]}") 
 print(f" Document: {row[2][:50]}...")
 print(f" Text: {row[3][:100]}...")
 print()

# Check zone distribution
zone_distribution = cursor.execute("SELECT zone, COUNT(*) FROM regulatory_provisions WHERE zone IS NOT NULL AND zone != '' GROUP BY zone ORDER BY COUNT(*) DESC").fetchall()

print("Zone distribution:")
for zone, count in zone_distribution:
 print(f" {zone}: {count} records")

conn.close()