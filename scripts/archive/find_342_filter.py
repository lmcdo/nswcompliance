#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, io, psycopg2
from dotenv import load_dotenv
from urllib.parse import urlparse

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('SUPABASE_DB_URL')
url = urlparse(DATABASE_URL)

conn = psycopg2.connect(
    host=url.hostname, port=url.port or 5432,
    database=url.path[1:], user=url.username, password=url.password
)
cur = conn.cursor()

# Test: Parts D + E only
cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
      AND v2_is_actionable = true
      AND is_current = TRUE
      AND v2_dcp_layer = 'generic'
      AND v2_dcp_part IN ('Part D', 'Part E')
""")
only_d_e = cur.fetchone()[0]

# Test: Without ALL Part C
cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
      AND v2_is_actionable = true
      AND is_current = TRUE
      AND v2_dcp_layer = 'generic'
      AND (v2_dcp_part NOT LIKE 'Part C%' OR v2_dcp_part IS NULL)
""")
without_part_c = cur.fetchone()[0]

print(f'Database has: 2,309 generic provisions')
print(f'API returns: 342 provisions')
print(f'')
print(f'Testing filters:')
print(f'  Only Part D + E: {only_d_e:,}')
print(f'  Without Part C: {without_part_c:,}')
print(f'')

if only_d_e == 342:
    print(f'🎯 FOUND IT! API is only including Part D + E')
    print(f'   Part D + E = 342 provisions')
    print(f'   Part C = {2309 - only_d_e:,} provisions (excluded)')
elif abs(without_part_c - 342) < 10:
    print(f'🎯 FOUND IT! API is excluding Part C')
else:
    print(f'Testing more combinations...')

conn.close()
