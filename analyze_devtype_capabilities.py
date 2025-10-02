#!/usr/bin/env python3
"""Analyze database capabilities for development type filtering."""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.db_config import get_dict_connection

conn = get_dict_connection()
cursor = conn.cursor()

print('='*80)
print('DEVELOPMENT TYPE FILTERING ANALYSIS')
print('='*80)

# 1. Check regulatory_provisions structure
print('\n1. REGULATORY_PROVISIONS TABLE STRUCTURE')
print('-' * 80)
cursor.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'regulatory_provisions'
    ORDER BY ordinal_position
""")
cols = cursor.fetchall()
for col in cols:
    print(f"  {col['column_name']:<30} {col['data_type']}")

# 2. Check what development types we have
print('\n2. DEVELOPMENT TYPES IN DATABASE')
print('-' * 80)
cursor.execute("""
    SELECT development_type, provision_type, COUNT(*) as count
    FROM regulatory_provisions
    WHERE development_type IS NOT NULL
    GROUP BY development_type, provision_type
    ORDER BY count DESC
""")
rows = cursor.fetchall()
print(f"{'Development Type':<30} {'Doc Type':<15} {'Count':>10}")
print('-' * 80)
for r in rows:
    print(f"{r['development_type']:<30} {r['provision_type']:<15} {r['count']:>10}")

# 3. Check documents by type
print('\n3. PROVISION TYPES (SEPP/LEP/DCP) DISTRIBUTION')
print('-' * 80)
cursor.execute("""
    SELECT provision_type, COUNT(*) as count
    FROM regulatory_provisions
    GROUP BY provision_type
    ORDER BY count DESC
""")
rows = cursor.fetchall()
for r in rows:
    print(f"  {r['provision_type']:<20} {r['count']:>8} provisions")

# 4. Sample DCP provisions with dev types
print('\n4. SAMPLE DCP PROVISIONS WITH DEVELOPMENT TYPES')
print('-' * 80)
cursor.execute("""
    SELECT id, document_id, ref_number, section_header, development_type
    FROM regulatory_provisions
    WHERE provision_type = 'DCP'
      AND development_type IS NOT NULL
    LIMIT 10
""")
rows = cursor.fetchall()
for r in rows:
    doc_short = r['document_id'][:40] if r['document_id'] else 'N/A'
    section_short = r['section_header'][:40] if r['section_header'] else 'N/A'
    print(f"  [{r['development_type']:<20}] {section_short}")

# 5. Check LEP provisions with dev types
print('\n5. SAMPLE LEP PROVISIONS WITH DEVELOPMENT TYPES')
print('-' * 80)
cursor.execute("""
    SELECT id, ref_number, section_header, development_type
    FROM regulatory_provisions
    WHERE provision_type = 'LEP'
      AND development_type IS NOT NULL
    LIMIT 10
""")
rows = cursor.fetchall()
for r in rows:
    section_short = r['section_header'][:50] if r['section_header'] else 'N/A'
    print(f"  [{r['development_type']:<20}] {r['ref_number']:<10} {section_short}")

# 6. Check SEPP provisions with dev types
print('\n6. SAMPLE SEPP PROVISIONS WITH DEVELOPMENT TYPES')
print('-' * 80)
cursor.execute("""
    SELECT id, ref_number, section_header, development_type
    FROM regulatory_provisions
    WHERE provision_type = 'SEPP'
      AND development_type IS NOT NULL
    LIMIT 10
""")
rows = cursor.fetchall()
for r in rows:
    section_short = r['section_header'][:50] if r['section_header'] else 'N/A'
    print(f"  [{r['development_type']:<20}] {r['ref_number']:<10} {section_short}")

# 7. Check KG entities
print('\n7. KNOWLEDGE GRAPH ENTITIES')
print('-' * 80)
cursor.execute("""
    SELECT entity_type, COUNT(*) as count
    FROM kg_entities
    GROUP BY entity_type
    ORDER BY count DESC
    LIMIT 15
""")
rows = cursor.fetchall()
for r in rows:
    print(f"  {r['entity_type']:<30} {r['count']:>8} entities")

# 8. Check if we have dev type entities
print('\n8. DEVELOPMENT TYPE ENTITIES IN KG')
print('-' * 80)
cursor.execute("""
    SELECT entity_value, source_provision_id
    FROM kg_entities
    WHERE entity_type IN ('DEVELOPMENT_TYPE', 'LAND_USE', 'BUILDING_TYPE')
    LIMIT 20
""")
rows = cursor.fetchall()
if rows:
    for r in rows:
        print(f"  {r['entity_value'][:60]}")
else:
    print("  No DEVELOPMENT_TYPE entities found in knowledge graph")

# 9. Check relationships
print('\n9. KNOWLEDGE GRAPH RELATIONSHIPS')
print('-' * 80)
cursor.execute("""
    SELECT relationship_type, COUNT(*) as count
    FROM kg_relationships
    GROUP BY relationship_type
    ORDER BY count DESC
    LIMIT 15
""")
rows = cursor.fetchall()
for r in rows:
    print(f"  {r['relationship_type']:<40} {r['count']:>8} relationships")

# 10. Check if we can map dev types to provisions
print('\n10. SAMPLE: CAN WE FILTER BY DEV TYPE?')
print('-' * 80)
print("Query: Get all provisions for 'dwelling_house'")
cursor.execute("""
    SELECT provision_type, COUNT(*) as count
    FROM regulatory_provisions
    WHERE development_type = 'dwelling_house'
    GROUP BY provision_type
""")
rows = cursor.fetchall()
if rows:
    for r in rows:
        print(f"  {r['provision_type']:<20} {r['count']:>8} provisions")
else:
    print("  No provisions found for 'dwelling_house'")

print('\n' + '='*80)
print('ANALYSIS COMPLETE')
print('='*80)

cursor.close()
conn.close()