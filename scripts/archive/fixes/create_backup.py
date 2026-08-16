import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv('DATABASE_URL')

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

print("Creating backup table...")

# Drop if exists (for re-running)
cur.execute('DROP TABLE IF EXISTS v2_heritage_type_backup_20260212')

# Create backup table
cur.execute('''
CREATE TABLE v2_heritage_type_backup_20260212 AS
SELECT id, v2_heritage_type, v2_marker, document_id
FROM regulatory_provisions
WHERE v2_marker = 'heritage'
''')

# Verify backup
cur.execute('''
SELECT
    COUNT(*) as total_provisions,
    COUNT(v2_heritage_type) FILTER (WHERE v2_heritage_type IS NOT NULL) as already_tagged
FROM v2_heritage_type_backup_20260212
''')

result = cur.fetchone()
print(f'[OK] Backup created: {result[0]} provisions backed up')
print(f'     Already tagged: {result[1]}')

conn.commit()
cur.close()
conn.close()
print('\nBackup complete. Safe to proceed with tagging.')
