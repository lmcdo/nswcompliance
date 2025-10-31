"""
Check if Marrickville signage requirements have zone/development type metadata
that could be used to filter them for residential properties
"""
import psycopg2

conn = psycopg2.connect('postgresql://postgres:password@localhost/nsw_planning')
cur = conn.cursor()

print('Analyzing Marrickville signage requirements for filtering metadata:')
print('='*100)

# Check applicable_zones and development_types fields
cur.execute('''
  SELECT
    id,
    part_number,
    part_name,
    applicable_zones,
    development_types,
    requirement_text
  FROM dcp_general_requirements
  WHERE lga = 'Inner West'
  AND former_council = 'Marrickville'
  AND category = 'signage'
  LIMIT 10
''')

print('\nSample signage requirements (first 10):')
for row in cur.fetchall():
    print(f'\nID {row[0]}: {row[1]} - {row[2]}')
    print(f'  applicable_zones: {row[3]}')
    print(f'  development_types: {row[4]}')
    print(f'  Text: {row[5][:80]}...')

# Count how many have zone/devtype metadata
cur.execute('''
  SELECT
    COUNT(*) as total,
    COUNT(CASE WHEN applicable_zones IS NOT NULL THEN 1 END) as has_zones,
    COUNT(CASE WHEN development_types IS NOT NULL THEN 1 END) as has_devtypes
  FROM dcp_general_requirements
  WHERE lga = 'Inner West'
  AND former_council = 'Marrickville'
  AND category = 'signage'
''')

row = cur.fetchone()
print('\n' + '='*100)
print(f'Signage metadata coverage:')
print(f'  Total: {row[0]}')
print(f'  With applicable_zones: {row[1]} ({row[1]/row[0]*100:.1f}%)')
print(f'  With development_types: {row[2]} ({row[2]/row[0]*100:.1f}%)')

# Check the verbatim text to see if zone/use info is embedded in the text
cur.execute('''
  SELECT
    id,
    requirement_text,
    verbatim_source_text
  FROM dcp_general_requirements
  WHERE lga = 'Inner West'
  AND former_council = 'Marrickville'
  AND category = 'signage'
  AND (
    verbatim_source_text ILIKE '%residential%'
    OR verbatim_source_text ILIKE '%commercial%'
    OR verbatim_source_text ILIKE '%industrial%'
    OR verbatim_source_text ILIKE '% zone%'
  )
  LIMIT 5
''')

print('\n' + '='*100)
print('Signage requirements with zone/use keywords in text:')
for row in cur.fetchall():
    print(f'\nID {row[0]}:')
    print(f'  Requirement: {row[1][:100]}...')
    print(f'  Verbatim: {row[2][:150]}...')

# Check specific parts to see if they're zone-specific
cur.execute('''
  SELECT
    part_number,
    part_name,
    COUNT(*) as count,
    MIN(requirement_text) as sample_text
  FROM dcp_general_requirements
  WHERE lga = 'Inner West'
  AND former_council = 'Marrickville'
  AND category = 'signage'
  GROUP BY part_number, part_name
  ORDER BY part_number
''')

print('\n' + '='*100)
print('Signage requirements by section (with sample):')
for row in cur.fetchall():
    print(f'\n{row[0]} - {row[1]}: {row[2]} requirements')
    print(f'  Sample: {row[3][:100]}...')

conn.close()
