#!/usr/bin/env python3
"""Fix the regulatory_provisions ID sequence if it's out of sync."""
import psycopg2, os, sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# Check current max ID
cur.execute('SELECT MAX(id) FROM regulatory_provisions')
max_id = cur.fetchone()[0]
print(f'Current max ID: {max_id}')

# Check sequence value
cur.execute("SELECT last_value FROM regulatory_provisions_id_seq")
seq_val = cur.fetchone()[0]
print(f'Sequence last_value: {seq_val}')

if max_id > seq_val:
    print(f'\n⚠️  Sequence is behind! Fixing...')
    cur.execute(f"SELECT setval('regulatory_provisions_id_seq', {max_id})")
    conn.commit()
    print(f'✓ Sequence updated to {max_id}')
else:
    print('\n✓ Sequence is correct')

conn.close()
