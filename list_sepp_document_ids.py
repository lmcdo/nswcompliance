#!/usr/bin/env python3
"""List all SEPP document IDs in regulatory_provisions table"""
import sys
sys.path.insert(0, '.')
from db_safety_wrapper import get_safe_connection

conn = get_safe_connection()
cursor = conn.cursor()

print("=== SEPP DOCUMENT IDs IN DATABASE ===\n")

# Get unique document IDs for SEPP provisions
cursor.execute("""
    SELECT DISTINCT document_id, COUNT(*) as provision_count
    FROM regulatory_provisions
    WHERE document_id ILIKE '%SEPP%'
       OR document_id ILIKE '%Environmental_Planning_Policy%'
    GROUP BY document_id
    ORDER BY provision_count DESC
""")

results = cursor.fetchall()

print(f"Found {len(results)} SEPP documents:\n")
for doc_id, count in results:
    print(f"  {doc_id}")
    print(f"    ({count} provisions)\n")

print("\n=== Planning Portal SEPP Name Examples ===")
print("  State Environmental Planning Policy (Sustainable Buildings) 2022")
print("  State Environmental Planning Policy (Transport and Infrastructure) 2021")
print("  State Environmental Planning Policy (Housing) 2021")
print("  State Environmental Planning Policy (Exempt and Complying Development Codes) 2008")
print("  State Environmental Planning Policy (Biodiversity and Conservation) 2017")

cursor.close()
conn.close()
