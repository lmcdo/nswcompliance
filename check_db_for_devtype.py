#!/usr/bin/env python3
"""Check database structure for development type filtering capabilities."""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.db_config import get_dict_connection

conn = get_dict_connection()
cursor = conn.cursor()

# Check all tables
cursor.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    ORDER BY table_name
""")
tables = cursor.fetchall()
print('=== ALL TABLES ===')
for t in tables:
    print(f"  {t['table_name']}")

# Check provisions table structure
print('\n=== PROVISIONS TABLE STRUCTURE ===')
cursor.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'provisions'
    ORDER BY ordinal_position
""")
cols = cursor.fetchall()
for col in cols:
    print(f"  {col['column_name']} ({col['data_type']})")

# Check if we have regulatory_provisions development_type column
print('\n=== REGULATORY_PROVISIONS development_type ===')
cursor.execute("""
    SELECT development_type, COUNT(*) as count
    FROM regulatory_provisions
    WHERE development_type IS NOT NULL
    GROUP BY development_type
    ORDER BY count DESC
    LIMIT 20
""")
rows = cursor.fetchall()
if rows:
    print("Development types found:")
    for r in rows:
        print(f"  {r['development_type']}: {r['count']} provisions")
else:
    print("  No development_type data found in regulatory_provisions")

# Sample DCP provisions
print('\n=== SAMPLE DCP PROVISIONS ===')
cursor.execute("""
    SELECT id, document_id, section_title, control_number, category
    FROM provisions
    WHERE document_id LIKE '%DCP%'
    LIMIT 5
""")
rows = cursor.fetchall()
for r in rows:
    print(f"  ID={r.get('id')}, section={r.get('section_title', 'N/A')[:50]}, control={r.get('control_number')}")

# Check entities table
print('\n=== ENTITIES TABLE ===')
cursor.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'entities'
    ORDER BY ordinal_position
""")
cols = cursor.fetchall()
for col in cols:
    print(f"  {col['column_name']} ({col['data_type']})")

# Check entity types
print('\n=== ENTITY TYPES DISTRIBUTION ===')
cursor.execute("""
    SELECT entity_type, COUNT(*) as count
    FROM entities
    GROUP BY entity_type
    ORDER BY count DESC
    LIMIT 15
""")
rows = cursor.fetchall()
for r in rows:
    print(f"  {r['entity_type']}: {r['count']}")

# Sample entities related to development types
print('\n=== SAMPLE DEVELOPMENT-RELATED ENTITIES ===')
cursor.execute("""
    SELECT entity_type, entity_value, source_document
    FROM entities
    WHERE entity_type IN ('DEVELOPMENT_TYPE', 'ZONE', 'LAND_USE')
    LIMIT 10
""")
rows = cursor.fetchall()
for r in rows:
    print(f"  {r['entity_type']}: {r['entity_value'][:50]} (from {r['source_document'][:40]})")

# Check relationships
print('\n=== RELATIONSHIPS TABLE ===')
cursor.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'relationships'
    ORDER BY ordinal_position
""")
cols = cursor.fetchall()
for col in cols:
    print(f"  {col['column_name']} ({col['data_type']})")

# Sample relationships
print('\n=== SAMPLE RELATIONSHIPS ===')
cursor.execute("""
    SELECT relationship_type, COUNT(*) as count
    FROM relationships
    GROUP BY relationship_type
    ORDER BY count DESC
    LIMIT 10
""")
rows = cursor.fetchall()
for r in rows:
    print(f"  {r['relationship_type']}: {r['count']}")

cursor.close()
conn.close()