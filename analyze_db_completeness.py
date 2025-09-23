#!/usr/bin/env python3
"""
Comprehensive analysis of database completeness for NSW Planning provisions
"""

import psycopg2
import json
from collections import defaultdict

conn = psycopg2.connect(
 host='localhost',
 database='nsw_planning',
 user='postgres',
 password='postgres'
)

cur = conn.cursor()

print('=' * 80)
print('NSW PLANNING DATABASE COMPLETENESS REPORT')
print('=' * 80)

# 1. Overall statistics
print('\n=== OVERALL DATABASE STATISTICS ===\n')

cur.execute('''
 SELECT 
 COUNT(*) as total_provisions,
 COUNT(CASE WHEN numeric_value IS NOT NULL THEN 1 END) as with_numeric,
 ROUND(COUNT(CASE WHEN numeric_value IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) as numeric_percent,
 COUNT(DISTINCT document_type) as document_types,
 COUNT(DISTINCT measurement_context) as measurement_contexts
 FROM authoritative.planning_provisions
''')
overall = cur.fetchone()
print(f'Total Provisions in Database: {overall[0]:,}')
print(f'Provisions with Numeric Values: {overall[1]:,} ({overall[2]}%)')
print(f'Document Types: {overall[3]}')
print(f'Measurement Contexts: {overall[4]}')

# 2. Zone coverage analysis
print('\n=== ZONE COVERAGE ANALYSIS ===\n')

cur.execute('''
 WITH zone_provisions AS (
 SELECT 
 UNNEST(applicable_zones) as zone,
 numeric_value,
 measurement_context,
 provision_type,
 document_type
 FROM authoritative.planning_provisions
 WHERE applicable_zones IS NOT NULL AND array_length(applicable_zones, 1) > 0
 )
 SELECT 
 zone,
 COUNT(*) as total_provisions,
 COUNT(CASE WHEN numeric_value IS NOT NULL THEN 1 END) as numeric_provisions,
 COUNT(DISTINCT measurement_context) as unique_measurements,
 ROUND(COUNT(CASE WHEN numeric_value IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) as numeric_percent,
 STRING_AGG(DISTINCT document_type, ', ') as doc_types
 FROM zone_provisions
 WHERE zone LIKE 'R%' OR zone LIKE 'B%' OR zone LIKE 'E%' OR zone LIKE 'IN%'
 GROUP BY zone
 ORDER BY 
 CASE 
 WHEN zone LIKE 'R%' THEN 1
 WHEN zone LIKE 'B%' THEN 2
 WHEN zone LIKE 'E%' THEN 3
 WHEN zone LIKE 'IN%' THEN 4
 ELSE 5
 END,
 zone
''')

zones_data = cur.fetchall()
print(f'{"Zone":<8} {"Total":<8} {"Numeric":<10} {"Coverage":<10} {"Measurements":<15} {"Documents":<30}')
print('-' * 80)
for row in zones_data:
 zone, total, numeric, measurements, percent, doc_types = row
 doc_types_short = doc_types[:25] + '...' if len(doc_types) > 25 else doc_types
 print(f'{zone:<8} {total:<8} {numeric:<10} {percent:>8.1f}% {measurements:<15} {doc_types_short:<30}')

# 3. What specific numeric standards do we have?
print('\n=== NUMERIC STANDARDS AVAILABLE ===\n')

cur.execute('''
 WITH zone_standards AS (
 SELECT 
 measurement_context,
 UNNEST(applicable_zones) as zone,
 numeric_value,
 unit,
 document_type
 FROM authoritative.planning_provisions
 WHERE numeric_value IS NOT NULL
 AND measurement_context IS NOT NULL
 )
 SELECT 
 measurement_context,
 COUNT(DISTINCT zone) as zones_covered,
 COUNT(*) as total_instances,
 MIN(numeric_value) as min_value,
 MAX(numeric_value) as max_value,
 STRING_AGG(DISTINCT unit, ', ') as units,
 STRING_AGG(DISTINCT document_type, ', ') as sources
 FROM zone_standards
 GROUP BY measurement_context
 ORDER BY zones_covered DESC, total_instances DESC
''')

print(f'{"Measurement Context":<35} {"Zones":<8} {"Count":<8} {"Range":<20} {"Units":<15}')
print('-' * 80)
standards = cur.fetchall()
for row in standards:
 context, zones, total, min_val, max_val, units, sources = row
 if context:
 range_str = f'{min_val:.1f}-{max_val:.1f}' if min_val != max_val else f'{min_val:.1f}'
 units_str = units if units else 'N/A'
 print(f'{context:<35} {zones:<8} {total:<8} {range_str:<20} {units_str:<15}')

# 4. Document type analysis
print('\n=== DOCUMENT TYPE BREAKDOWN ===\n')

cur.execute('''
 SELECT 
 document_type,
 document_name,
 COUNT(*) as provisions,
 COUNT(CASE WHEN numeric_value IS NOT NULL THEN 1 END) as numeric,
 ROUND(AVG(extraction_confidence), 2) as avg_confidence
 FROM authoritative.planning_provisions
 GROUP BY document_type, document_name
 ORDER BY provisions DESC
 LIMIT 15
''')

doc_breakdown = cur.fetchall()
print(f'{"Type":<10} {"Document Name":<50} {"Provisions":<12} {"Numeric":<10} {"Confidence":<10}')
print('-' * 92)
for row in doc_breakdown:
 doc_type, doc_name, provisions, numeric, confidence = row
 doc_name_short = doc_name[:45] + '...' if doc_name and len(doc_name) > 45 else (doc_name or 'N/A')
 conf_str = f'{confidence:.2f}' if confidence else 'N/A'
 print(f'{doc_type:<10} {doc_name_short:<50} {provisions:<12} {numeric:<10} {conf_str:<10}')

# 5. Best and worst zones for data completeness
print('\n=== DATA COMPLETENESS RANKINGS ===\n')

cur.execute('''
 WITH zone_stats AS (
 SELECT 
 UNNEST(applicable_zones) as zone,
 numeric_value,
 measurement_context
 FROM authoritative.planning_provisions
 WHERE applicable_zones IS NOT NULL
 ),
 zone_summary AS (
 SELECT 
 zone,
 COUNT(*) as total,
 COUNT(CASE WHEN numeric_value IS NOT NULL THEN 1 END) as numeric,
 COUNT(DISTINCT measurement_context) as contexts,
 ARRAY_AGG(DISTINCT measurement_context) FILTER (WHERE numeric_value IS NOT NULL) as numeric_contexts
 FROM zone_stats
 WHERE zone ~ '^[A-Z][0-9]' -- Standard zone format
 GROUP BY zone
 )
 SELECT zone, total, numeric, contexts, numeric_contexts
 FROM zone_summary
 ORDER BY numeric DESC, total DESC
''')

rankings = cur.fetchall()

print('\nTop 10 Zones with Most Numeric Data:')
print(f'{"Zone":<8} {"Total":<10} {"Numeric":<10} {"Contexts":<10} {"Numeric Measurements Available":<50}')
print('-' * 80)
for row in rankings[:10]:
 zone, total, numeric, contexts, numeric_contexts = row
 contexts_str = ', '.join([c for c in numeric_contexts if c])[:45] if numeric_contexts else 'None'
 print(f'{zone:<8} {total:<10} {numeric:<10} {contexts:<10} {contexts_str:<50}')

print('\nZones with NO Numeric Data:')
no_numeric = [row[0] for row in rankings if row[2] == 0]
if no_numeric:
 print(', '.join(no_numeric[:20]))
 if len(no_numeric) > 20:
 print(f'... and {len(no_numeric) - 20} more zones')
else:
 print('All zones have at least some numeric data')

# 6. Development type coverage
print('\n=== DEVELOPMENT TYPE ANALYSIS ===\n')

cur.execute('''
 WITH dev_provisions AS (
 SELECT 
 UNNEST(applicable_dev_types) as dev_type,
 numeric_value,
 UNNEST(applicable_zones) as zone
 FROM authoritative.planning_provisions
 WHERE applicable_dev_types IS NOT NULL 
 AND array_length(applicable_dev_types, 1) > 0
 AND applicable_zones IS NOT NULL
 )
 SELECT 
 dev_type,
 COUNT(DISTINCT zone) as zones,
 COUNT(*) as provisions,
 COUNT(CASE WHEN numeric_value IS NOT NULL THEN 1 END) as numeric
 FROM dev_provisions
 GROUP BY dev_type
 ORDER BY zones DESC, provisions DESC
 LIMIT 20
''')

print(f'{"Development Type":<40} {"Zones":<8} {"Provisions":<12} {"Numeric":<10}')
print('-' * 70)
dev_types = cur.fetchall()
for row in dev_types:
 dev_type, zones, provisions, numeric = row
 print(f'{dev_type:<40} {zones:<8} {provisions:<12} {numeric:<10}')

# Summary recommendations
print('\n' + '=' * 80)
print('SUMMARY & RECOMMENDATIONS')
print('=' * 80)

# Calculate key metrics
total_provisions = overall[0]
numeric_provisions = overall[1]
numeric_percent = overall[2]

r_zones = [row for row in zones_data if row[0].startswith('R')]
r_zones_with_good_data = [row for row in r_zones if row[2] > 5] # More than 5 numeric provisions

print(f'\n Database contains {total_provisions:,} total provisions')
print(f' {numeric_provisions:,} provisions ({numeric_percent}%) have numeric values')
print(f' {len(r_zones)} residential zones analyzed')
print(f' {len(r_zones_with_good_data)} residential zones have substantial numeric data (>5 provisions)')

print('\nRECOMMENDATIONS:')
print('1. IMMEDIATE USE CASES (High Confidence):')
for zone in r_zones_with_good_data[:5]:
 print(f' - {zone[0]}: {zone[2]} numeric standards available')

print('\n2. ZONES REQUIRING DATA ENHANCEMENT:')
zones_needing_work = [row for row in r_zones if row[2] <= 2]
for zone in zones_needing_work[:5]:
 print(f' - {zone[0]}: Only {zone[2]} numeric standards')

print('\n3. BEST COVERAGE BY MEASUREMENT TYPE:')
for standard in standards[:5]:
 if standard[0]:
 print(f' - {standard[0]}: Available in {standard[1]} zones')

conn.close()