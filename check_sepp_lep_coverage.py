import sqlite3

conn = sqlite3.connect('nsw_planning.db')
cursor = conn.cursor()

print('=== CHECKING SEPP/LEP COVERAGE IN DATABASE ===')
print()

# Check documents table for SEPPs
cursor.execute("""
SELECT DISTINCT document_title
FROM documents
WHERE LOWER(document_title) LIKE '%sepp%'
ORDER BY document_title
""")
sepp_docs = cursor.fetchall()

print(f'SEPP DOCUMENTS FOUND: {len(sepp_docs)}')
for doc in sepp_docs[:10]:  # Show first 10
    print(f'  - {doc[0]}')
if len(sepp_docs) > 10:
    print(f'  ... and {len(sepp_docs)-10} more')

print()

# Check for specific SEPPs mentioned as missing
missing_sepps = ['SEPP 65', 'SEPP-Housing', 'Design Quality', 'Exempt and Complying', 'SEPP (Housing) 2021', 'SEPP Housing']
for sepp in missing_sepps:
    cursor.execute("""
    SELECT document_title
    FROM documents
    WHERE LOWER(document_title) LIKE ?
    LIMIT 5
    """, (f'%{sepp.lower()}%',))
    results = cursor.fetchall()
    if results:
        print(f'✓ "{sepp}" FOUND:')
        for r in results:
            print(f'    - {r[0]}')
    else:
        print(f'✗ "{sepp}" NOT FOUND')

print()

# Check regulatory_provisions for SEPP content
cursor.execute("""
SELECT COUNT(*)
FROM regulatory_provisions
WHERE LOWER(source_document) LIKE '%sepp%'
""")
sepp_provisions = cursor.fetchone()[0]
print(f'SEPP provisions in regulatory_provisions: {sepp_provisions}')

# Sample some SEPP provisions
cursor.execute("""
SELECT DISTINCT source_document
FROM regulatory_provisions
WHERE LOWER(source_document) LIKE '%sepp%'
LIMIT 10
""")
sepp_sources = cursor.fetchall()
print('\nSample SEPP sources in provisions:')
for source in sepp_sources:
    print(f'  - {source[0]}')

print()

# Check for Inner West LEP
cursor.execute("""
SELECT DISTINCT document_title
FROM documents
WHERE LOWER(document_title) LIKE '%inner west%' OR LOWER(document_title) LIKE '%marrickville%'
   OR LOWER(document_title) LIKE '%leichhardt%' OR LOWER(document_title) LIKE '%ashfield%'
ORDER BY document_title
""")
inner_west_docs = cursor.fetchall()

print(f'INNER WEST DOCUMENTS FOUND: {len(inner_west_docs)}')
for doc in inner_west_docs[:10]:
    print(f'  - {doc[0]}')

# Check development_permissions for SEPP-derived permissions
print()
cursor.execute("""
SELECT COUNT(*)
FROM development_permissions
WHERE lep_name LIKE '%SEPP%' OR source_provision_id IN (
    SELECT id FROM regulatory_provisions WHERE LOWER(source_document) LIKE '%sepp%'
)
""")
sepp_dev_perms = cursor.fetchone()[0]
print(f'Development permissions from SEPPs: {sepp_dev_perms}')

# Check permissibility_analysis for SEPP patterns
cursor.execute("""
SELECT COUNT(*)
FROM permissibility_analysis
WHERE LOWER(document_id) LIKE '%sepp%'
""")
sepp_patterns = cursor.fetchone()[0]
print(f'Permissibility patterns from SEPPs: {sepp_patterns}')

conn.close()