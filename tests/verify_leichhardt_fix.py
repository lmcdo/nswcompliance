"""Verify the Leichhardt query fix will return data"""
import psycopg2

conn = psycopg2.connect('postgresql://postgres@127.0.0.1:5432/nsw_planning')
cur = conn.cursor()

# Test the new query
print('=== Testing NEW Leichhardt Query ===')
cur.execute('''
    SELECT COUNT(*) as cnt,
           SUBSTRING(document_id FROM 1 FOR 60) as doc_prefix
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
    AND page_number != '0'
    AND (
        document_id ILIKE '%Part A%'
        OR document_id ILIKE '%Part B%'
        OR document_id ILIKE '%Part D%'
        OR document_id ILIKE '%Part E%'
        OR document_id ILIKE '%Part F%'
        OR document_id ILIKE '%Part C%Section 1%'
        OR document_id ILIKE '%Part C Place Section 1%'
    )
    AND document_id NOT ILIKE '%Section 2%'
    AND document_id NOT ILIKE '%Part G%'
    AND document_id NOT ILIKE '%Distinctive_Neighbour%'
    GROUP BY SUBSTRING(document_id FROM 1 FOR 60)
    ORDER BY cnt DESC
''')
rows = cur.fetchall()
total = sum(r[0] for r in rows)
print(f'\nTotal provisions: {total}')
print('\nBy document:')
for row in rows:
    print(f'  {row[0]:4d}  {row[1]}')

# Compare with old query (should be 0)
print('\n=== OLD Query (for comparison) ===')
cur.execute('''
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
    AND page_number != '0'
    AND (
        document_id ILIKE '%Part%General%'
        OR document_id ILIKE '%Chapter%General%'
    )
''')
old_count = cur.fetchone()[0]
print(f'Old query returned: {old_count}')

print(f'\n=== IMPROVEMENT: {total} vs {old_count} ===')

conn.close()
