from db_config import get_connection

conn = get_connection()
cursor = conn.cursor()

cursor.execute('SELECT provision_type FROM special_provisions_registry WHERE active = TRUE')
types = cursor.fetchall()

print('Special provision types in registry:')
for t in types:
 print(f' - {t[0]}')

conn.close()