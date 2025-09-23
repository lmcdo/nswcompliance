import psycopg2

conn = psycopg2.connect(host='localhost', database='nsw_planning', user='postgres', password='postgres')
cur = conn.cursor()

cur.execute('SELECT provision_type, ref_number FROM regulatory_provisions WHERE zone IS NOT NULL LIMIT 10')
for row in cur.fetchall():
 print(f'provision_type: {row[0][:60] if row[0] else None}')
 print(f'ref_number: {row[1][:60] if row[1] else None}')
 print('---')

conn.close()