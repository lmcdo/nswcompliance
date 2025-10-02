#!/usr/bin/env python3
from db_config import get_connection

conn = get_connection()
cur = conn.cursor()

# Check what we have for provision ID 16964
cur.execute("""
    SELECT id, document_id, ref_number, section_header,
           LENGTH(provision_text) as text_len
    FROM regulatory_provisions
    WHERE id = 16964
""")

result = cur.fetchone()
if result:
    print(f'Provision 16964:')
    print(f'  ID: {result[0]}')
    print(f'  Document: {result[1]}')
    print(f'  Ref: {result[2]}')
    print(f'  Header: {result[3]}')
    print(f'  Text length: {result[4]} chars')
else:
    print('Provision 16964 not found')

conn.close()
