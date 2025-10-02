from db_safety_wrapper import get_safe_connection

conn = get_safe_connection()
cur = conn.cursor()

print('=== CURRENT DATABASE STATE ===\n')

# Check schema
cur.execute("""
    SELECT column_name, data_type, character_maximum_length
    FROM information_schema.columns
    WHERE table_name = 'regulatory_provisions'
    AND column_name IN ('provision_text', 'full_text_length', 'extraction_method', 'last_updated')
    ORDER BY column_name
""")
print('Schema columns:')
for row in cur.fetchall():
    length = f'({row[2]} chars)' if row[2] else '(unlimited)'
    print(f'  {row[0]:20} {row[1]:15} {length}')

# Check data state
cur.execute("""
    SELECT
        COUNT(*) as total,
        COUNT(*) FILTER (WHERE extraction_method = 'autoschema') as autoschema,
        COUNT(*) FILTER (WHERE extraction_method = 'pymupdf') as pymupdf,
        COUNT(*) FILTER (WHERE extraction_method IS NULL) as no_method,
        AVG(full_text_length) as avg_len,
        MAX(full_text_length) as max_len
    FROM regulatory_provisions
""")
row = cur.fetchone()
print(f'\nData statistics:')
print(f'  Total provisions:  {row[0]:,}')
print(f'  Autoschema:        {row[1]:,}')
print(f'  PyMuPDF:           {row[2]:,}')
print(f'  No method:         {row[3]:,}')
print(f'  Average length:    {float(row[4]):.1f} chars')
print(f'  Max length:        {row[5]:,} chars')

# Check SEPP provisions
cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE document_id LIKE '%State_Environmental_Planning_Policy%'
""")
sepp_count = cur.fetchone()[0]
print(f'  SEPP provisions:   {sepp_count:,}')

conn.close()
print('\n[OK] Database state verified')