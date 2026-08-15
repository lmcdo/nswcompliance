import psycopg2, os
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

print('\n=== COUNCIL PROVISION COUNTS ===\n')

councils = [
    ('Leichhardt', 2989),
    ('Marrickville', 2838),
    ('Ashfield', None)
]

for name, expected in councils:
    cur.execute(f"SELECT COUNT(*) FROM regulatory_provisions WHERE document_id LIKE '%{name}%'")
    total = cur.fetchone()[0]

    cur.execute(f"SELECT COUNT(*) FROM regulatory_provisions WHERE document_id LIKE '%{name}%' AND v2_is_actionable = true")
    actionable = cur.fetchone()[0]

    print(f'{name}:')
    print(f'  Total: {total:,}')
    print(f'  Actionable: {actionable:,}')
    if expected:
        diff = total - expected
        pct = (diff / expected * 100) if expected else 0
        print(f'  Expected: {expected:,}')
        print(f'  Difference: {diff:+,} ({pct:+.1f}%)')
        if abs(diff) > expected * 0.1:
            print(f'  [CRITICAL] More than 10% difference!')
    print()
