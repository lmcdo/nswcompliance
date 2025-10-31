"""
Check if Ashfield/Leichhardt have signage controls in the source provisions
that just haven't been migrated to dcp_general_requirements yet
"""
import psycopg2

conn = psycopg2.connect('postgresql://postgres:password@localhost/nsw_planning')
cur = conn.cursor()

print('Checking for signage in source regulatory_provisions:')
print('='*100)

for council in ['Ashfield', 'Leichhardt']:
    cur.execute('''
      SELECT COUNT(*) as count
      FROM regulatory_provisions
      WHERE document_id LIKE %s
      AND (
        provision_text ILIKE '%%sign%%'
        OR provision_text ILIKE '%%advertis%%'
        OR section_header ILIKE '%%sign%%'
      )
    ''', (f'%{council}%',))

    count = cur.fetchone()[0]
    print(f'\n{council}:')
    print(f'  Provisions mentioning signs/advertising: {count}')

    # Get sample provisions
    cur.execute('''
      SELECT
        section_header,
        provision_text
      FROM regulatory_provisions
      WHERE document_id LIKE %s
      AND (
        provision_text ILIKE '%%sign%%'
        OR provision_text ILIKE '%%advertis%%'
      )
      LIMIT 3
    ''', (f'%{council}%',))

    print(f'  Sample provisions:')
    for row in cur.fetchall():
        print(f'    Section: {row[0]}')
        print(f'    Text: {row[1][:100]}...')
        print()

# Check what we actually extracted for Ashfield/Leichhardt
print('='*100)
print('\nWhat we actually extracted (by part/section):')

for council in ['Ashfield', 'Leichhardt']:
    cur.execute('''
      SELECT DISTINCT
        part_number,
        part_name
      FROM dcp_general_requirements
      WHERE lga = 'Inner West'
      AND former_council = %s
      ORDER BY part_number
    ''', (council,))

    print(f'\n{council} extracted sections:')
    for row in cur.fetchall():
        print(f'  {row[0]} - {row[1]}')

conn.close()
