import sqlite3

conn = sqlite3.connect('nsw_planning.db')
cursor = conn.cursor()

print('=== EXISTING TABLES ===')
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
for table in cursor.fetchall():
 print(f'Table: {table[0]}')

print('\n=== permissibility_analysis SCHEMA ===')
cursor.execute('PRAGMA table_info(permissibility_analysis)')
for column in cursor.fetchall():
 print(f' {column[1]} ({column[2]})')

print('\n=== development_permissions SCHEMA ===')
try:
 cursor.execute('PRAGMA table_info(development_permissions)')
 for column in cursor.fetchall():
 print(f' {column[1]} ({column[2]})')
except:
 print(' Table does not exist')

print('\n=== SAMPLE permissibility_analysis DATA ===')
cursor.execute('SELECT * FROM permissibility_analysis LIMIT 3')
for row in cursor.fetchall():
 print(f' {row}')

conn.close()