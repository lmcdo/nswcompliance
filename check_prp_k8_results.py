#!/usr/bin/env python3
"""Quick check of PRP-K8 results"""

from db_config import get_connection # Unified PostgreSQL connection

conn = get_connection()
cursor = conn.cursor()

# Get stats
cursor.execute("SELECT COUNT(*) FROM regulatory_provisions")
total = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE zone IS NOT NULL AND zone != ''")
with_zones = cursor.fetchone()[0]

# Get zone distribution
cursor.execute("""
 SELECT zone, COUNT(*) as count 
 FROM regulatory_provisions 
 WHERE zone IS NOT NULL AND zone != ''
 GROUP BY zone 
 ORDER BY count DESC
 LIMIT 10
""")
zone_dist = cursor.fetchall()

conn.close()

print("=== PRP-K8 RESULTS ===")
print(f"Total provisions: {total:,}")
print(f"Provisions with zones: {with_zones:,}")
print(f"Zone coverage: {with_zones/total*100:.1f}%")
print(f"Improvement from 8.7%: +{with_zones/total*100 - 8.7:.1f}%")
print()
print("Top zones:")
for zone, count in zone_dist:
 print(f" {zone}: {count:,}")