from db_config import get_connection

c = get_connection()
cur = c.cursor()

# Get columns
cur.execute('SELECT * FROM sepp_lep_overrides LIMIT 3')
cols = [desc[0] for desc in cur.description]
print('SEPP_LEP_OVERRIDES Columns:')
print('-' * 60)
for col in cols:
    print(f'  - {col}')

print('\nSample Data:')
print('-' * 60)
cur.execute('SELECT * FROM sepp_lep_overrides LIMIT 3')
for i, row in enumerate(cur.fetchall(), 1):
    print(f'\nRecord {i}:')
    for col, val in zip(cols, row):
        if val:
            val_str = str(val)[:100]
            print(f'  {col}: {val_str}')

print('\nCount:', end=' ')
cur.execute('SELECT COUNT(*) FROM sepp_lep_overrides')
print(f'{cur.fetchone()[0]} records')

c.close()