import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(host='localhost', database='nsw_planning_corrected', user='postgres', password='postgres', port='5432')
cursor = conn.cursor(cursor_factory=RealDictCursor)

cursor.execute('SELECT instrument_type, COUNT(*) as count FROM legal_instruments GROUP BY instrument_type ORDER BY count DESC')
instruments = cursor.fetchall()

print('Legal Instruments by type:')
for inst in instruments:
    print(f'  {inst["instrument_type"]}: {inst["count"]} instruments')

cursor.execute("SELECT COUNT(*) as count FROM regulatory_provisions WHERE provision_text ILIKE '%water%'")
water_count = cursor.fetchone()['count']
print(f'Water provisions found: {water_count}')

cursor.close()
conn.close()