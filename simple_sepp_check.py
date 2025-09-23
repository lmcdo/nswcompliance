import sqlite3

conn = sqlite3.connect('nsw_planning.db')
cursor = conn.cursor()

print('=== SEPP COVERAGE IN DATABASE ===')

# Check regulatory_provisions for SEPP content
cursor.execute("""
SELECT COUNT(DISTINCT source_document)
FROM regulatory_provisions
WHERE LOWER(source_document) LIKE '%sepp%'
""")
sepp_count = cursor.fetchone()[0]
print(f'Total SEPP documents: {sepp_count}')

# Check for specific SEPPs
print('\nChecking for specific SEPPs:')
sepps = ['exempt', 'complying', 'housing', 'transport', 'biodiversity', '65', 'design quality']
for sepp in sepps:
 cursor.execute("""
 SELECT COUNT(*)
 FROM regulatory_provisions
 WHERE LOWER(source_document) LIKE ?
 """, (f'%{sepp}%',))
 count = cursor.fetchone()[0]
 status = 'FOUND' if count > 0 else 'NOT FOUND'
 print(f' {sepp}: {count} provisions - {status}')

print('\n=== INNER WEST LEP COVERAGE ===')
cursor.execute("""
SELECT COUNT(*)
FROM regulatory_provisions
WHERE LOWER(source_document) LIKE '%inner west lep%'
""")
lep_count = cursor.fetchone()[0]
print(f'Inner West LEP provisions: {lep_count}')

# Check for any LEP
cursor.execute("""
SELECT COUNT(*)
FROM regulatory_provisions
WHERE LOWER(source_document) LIKE '%lep%'
""")
any_lep = cursor.fetchone()[0]
print(f'Any LEP provisions: {any_lep}')

print('\n=== DEVELOPMENT PERMISSIONS DATABASE ===')
cursor.execute('SELECT COUNT(*) FROM development_permissions')
total = cursor.fetchone()[0]
print(f'Total development permissions: {total}')

cursor.execute("""
SELECT COUNT(DISTINCT zone), COUNT(DISTINCT development_type)
FROM development_permissions
""")
zones, types = cursor.fetchone()
print(f'Zones covered: {zones}')
print(f'Development types: {types}')

# Check what's actually being used for permissions
print('\n=== ACTUAL PERMISSION SOURCES ===')
cursor.execute("""
SELECT source_type, COUNT(*)
FROM development_permissions
GROUP BY source_type
""")
sources = cursor.fetchall()
for source, count in sources:
 print(f' {source}: {count}')

conn.close()