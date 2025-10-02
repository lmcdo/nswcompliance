import sqlite3

conn = sqlite3.connect('nsw_planning.db')
cursor = conn.cursor()

print("=== DOCUMENTS TABLE ===")
cursor.execute('PRAGMA table_info(documents)')
columns = cursor.fetchall()
for col in columns:
    print(f'{col[1]} ({col[2]})')

cursor.execute('SELECT * FROM documents LIMIT 2')
samples = cursor.fetchall()
for sample in samples:
    print(sample)

print("\n=== REGULATORY PROVISIONS ===")
cursor.execute('SELECT COUNT(*) FROM regulatory_provisions WHERE provision_text LIKE "%SEPP%"')
sepp_count = cursor.fetchone()[0]
print(f'SEPP mentions: {sepp_count}')

print("\n=== SEPP LEP OVERRIDES ===")
cursor.execute('SELECT COUNT(*) FROM sepp_lep_overrides')
override_count = cursor.fetchone()[0]
print(f'SEPP override records: {override_count}')

if override_count > 0:
    cursor.execute('SELECT * FROM sepp_lep_overrides LIMIT 3')
    overrides = cursor.fetchall()
    for override in overrides:
        print(override)

conn.close()