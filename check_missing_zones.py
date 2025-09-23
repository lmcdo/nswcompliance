import sqlite3

conn = sqlite3.connect('nsw_planning.db')
cursor = conn.cursor()

print('=== ZONES WITH DEVELOPMENT PERMISSIONS ===')
cursor.execute('SELECT zone, COUNT(*) as count FROM development_permissions GROUP BY zone ORDER BY count DESC')
zones_with_perms = cursor.fetchall()
for zone, count in zones_with_perms:
 print(f'{zone}: {count} permissions')

print('\n=== ZONES IN PERMISSIBILITY_ANALYSIS (potential sources) ===')
cursor.execute('SELECT zone, COUNT(*) as count FROM permissibility_analysis WHERE zone IS NOT NULL GROUP BY zone ORDER BY count DESC')
zones_in_analysis = cursor.fetchall()
for zone, count in zones_in_analysis[:15]: # Top 15
 print(f'{zone}: {count} patterns')

print('\n=== MISSING STANDARD ZONES ===')
standard_zones = ['R1', 'R5', 'B3', 'B4', 'B5', 'B6', 'B7', 'IN2', 'IN3', 'E1', 'E2', 'E3', 'E4', 'RE1', 'RE2', 'RU1', 'RU2', 'RU3', 'RU4', 'RU5', 'RU6', 'SP1', 'SP2', 'SP3']
current_zones = [row[0] for row in zones_with_perms]
missing = [z for z in standard_zones if z not in current_zones]
print(f'Missing zones: {missing}')

conn.close()