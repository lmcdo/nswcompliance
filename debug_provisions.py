from db_config import get_connection

conn = get_connection()
cursor = conn.cursor()

# Check what the verification script is actually looking for
cursor.execute('''
 SELECT provision_type, COUNT(*) as count
 FROM special_provisions_registry
 WHERE active = TRUE
 GROUP BY provision_type
 ORDER BY count DESC
''')
provision_types = cursor.fetchall()

print('Provision types with counts:')
for ptype, count in provision_types:
 print(f' {ptype}: {count}')

print('\nTotal count:')
cursor.execute('SELECT COUNT(*) FROM special_provisions_registry')
total = cursor.fetchone()[0]
print(f'Total registry provisions: {total}')

# Check what critical types are being looked for
critical_types = [
 'Climate Zones',
 'Flood Planning',
 'Bushfire Prone Land',
 'State Environmental Planning Policy'
]

existing_types = {ptype for ptype, _ in provision_types}
missing_critical = set(critical_types) - existing_types

print(f'\nCritical types check:')
print(f'Expected: {critical_types}')
print(f'Found: {list(existing_types)}')
print(f'Missing: {list(missing_critical)}')

# Check the specific validation logic
registry_count = total
print(f'\nValidation logic:')
print(f'Registry count >= 5: {registry_count >= 5} (actual: {registry_count})')
print(f'Missing critical == 0: {len(missing_critical) == 0} (missing: {len(missing_critical)})')
print(f'Overall pass: {registry_count >= 5 and len(missing_critical) == 0}')

conn.close()