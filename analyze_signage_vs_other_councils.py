"""
Analyze signage requirements across all three Inner West councils
to see if Marrickville's 111 signage requirements is actually real
"""
import psycopg2

conn = psycopg2.connect('postgresql://postgres:password@localhost/nsw_planning')
cur = conn.cursor()

print('Signage requirements by council:')
print('='*100)

for council in ['Ashfield', 'Marrickville', 'Leichhardt']:
    # Count signage requirements
    cur.execute('''
      SELECT COUNT(*) as total
      FROM dcp_general_requirements
      WHERE lga = 'Inner West'
      AND former_council = %s
    ''', (council,))

    total = cur.fetchone()[0]

    cur.execute('''
      SELECT COUNT(*) as signage_count
      FROM dcp_general_requirements
      WHERE lga = 'Inner West'
      AND former_council = %s
      AND category = 'signage'
    ''', (council,))

    signage_count = cur.fetchone()[0]

    percentage = (signage_count / total * 100) if total > 0 else 0

    print(f'\n{council}:')
    print(f'  Total requirements: {total}')
    print(f'  Signage requirements: {signage_count} ({percentage:.1f}%)')

# Check what sections/parts these signage requirements come from
print('\n' + '='*100)
print('Marrickville signage requirement breakdown by section:')

cur.execute('''
  SELECT
    part_number,
    part_name,
    COUNT(*) as count
  FROM dcp_general_requirements
  WHERE lga = 'Inner West'
  AND former_council = 'Marrickville'
  AND category = 'signage'
  GROUP BY part_number, part_name
  ORDER BY count DESC
''')

for row in cur.fetchall():
    print(f'  {row[0]} - {row[1]}: {row[2]} requirements')

# Check if Ashfield and Leichhardt have Section 2.12 (signage) at all
print('\n' + '='*100)
print('Checking if Ashfield/Leichhardt have signage sections:')

for council in ['Ashfield', 'Leichhardt']:
    cur.execute('''
      SELECT
        part_number,
        part_name,
        COUNT(*) as count
      FROM dcp_general_requirements
      WHERE lga = 'Inner West'
      AND former_council = %s
      AND (
        part_number LIKE '%2.12%'
        OR part_name ILIKE '%sign%'
        OR part_name ILIKE '%advertis%'
      )
      GROUP BY part_number, part_name
      ORDER BY count DESC
    ''', (council,))

    results = cur.fetchall()
    print(f'\n{council}:')
    if results:
        for row in results:
            print(f'  {row[0]} - {row[1]}: {row[2]} requirements')
    else:
        print(f'  NO signage sections found')

# Sample a few signage requirements to verify they're actually about signage
print('\n' + '='*100)
print('Sample Marrickville signage requirements (first 5):')

cur.execute('''
  SELECT
    id,
    part_number,
    part_name,
    requirement_text
  FROM dcp_general_requirements
  WHERE lga = 'Inner West'
  AND former_council = 'Marrickville'
  AND category = 'signage'
  ORDER BY id
  LIMIT 5
''')

for row in cur.fetchall():
    print(f'\n  ID {row[0]}: {row[1]} - {row[2]}')
    print(f'    Text: {row[3][:100]}...')

conn.close()
