import sqlite3

conn = sqlite3.connect('nsw_planning.db')
cursor = conn.cursor()

# Final verification
cursor.execute('SELECT COUNT(*) FROM development_permissions')
total = cursor.fetchone()[0]
print(f'FINAL TOTAL: {total} development type combinations')

cursor.execute('SELECT COUNT(DISTINCT zone) FROM development_permissions WHERE zone IS NOT NULL')
zone_count = cursor.fetchone()[0]
print(f'ZONE COVERAGE: {zone_count} zones')

# Check major zones specifically
major_zones = ['R1', 'R2', 'R3', 'R4', 'B1', 'B2', 'B3', 'B4', 'IN1', 'IN2']
print('\nMAJOR ZONE COVERAGE:')
for zone in major_zones:
 cursor.execute('SELECT COUNT(*) FROM development_permissions WHERE zone = ?', (zone,))
 count = cursor.fetchone()[0]
 print(f' {zone}: {count} permissions')

cursor.execute('SELECT zone, COUNT(*) as count FROM development_permissions GROUP BY zone ORDER BY count DESC LIMIT 10')
top_zones = cursor.fetchall()
print('\nTOP 10 ZONES BY PERMISSIONS:')
for zone, count in top_zones:
 print(f' {zone}: {count}')

# Check R1 specifically to show it's properly covered now
print('\nR1 PERMISSIONS DETAIL:')
cursor.execute('SELECT development_type, permission_status, source_type FROM development_permissions WHERE zone = "R1" ORDER BY permission_status')
r1_perms = cursor.fetchall()
for dev_type, status, source in r1_perms:
 print(f' {dev_type}: {status} ({source})')

conn.close()