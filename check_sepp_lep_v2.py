import sqlite3

conn = sqlite3.connect('nsw_planning.db')
cursor = conn.cursor()

print('=== CHECKING DATABASE STRUCTURE ===')

# First check what tables we have
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f'Tables in database: {len(tables)}')

# Check documents table structure
print('\n=== DOCUMENTS TABLE ===')
cursor.execute("PRAGMA table_info(documents)")
doc_columns = cursor.fetchall()
print('Columns:', [col[1] for col in doc_columns])

# Check actual content
cursor.execute("SELECT * FROM documents LIMIT 5")
sample_docs = cursor.fetchall()
print(f'Sample documents: {len(sample_docs)} rows')
for doc in sample_docs:
 print(f' {doc}')

print('\n=== CHECKING REGULATORY PROVISIONS FOR SEPP/LEP ===')

# Check regulatory_provisions for SEPP content
cursor.execute("""
SELECT COUNT(*)
FROM regulatory_provisions
WHERE LOWER(source_document) LIKE '%sepp%'
""")
sepp_count = cursor.fetchone()[0]
print(f'SEPP provisions found: {sepp_count}')

# Sample SEPP provisions
cursor.execute("""
SELECT DISTINCT source_document
FROM regulatory_provisions
WHERE LOWER(source_document) LIKE '%sepp%'
LIMIT 10
""")
sepp_sources = cursor.fetchall()
if sepp_sources:
 print('Sample SEPP sources:')
 for source in sepp_sources:
 print(f' - {source[0]}')

# Check for specific SEPPs
print('\n=== CHECKING FOR SPECIFIC SEPPs ===')
specific_sepps = [
 'Exempt and Complying',
 'Housing',
 'Design Quality',
 'Transport and Infrastructure',
 'Biodiversity',
 'Primary Production'
]

for sepp in specific_sepps:
 cursor.execute("""
 SELECT COUNT(DISTINCT source_document)
 FROM regulatory_provisions
 WHERE LOWER(source_document) LIKE ?
 """, (f'%{sepp.lower()}%',))
 count = cursor.fetchone()[0]
 if count > 0:
 print(f' SEPP containing "{sepp}": {count} documents')
 # Get sample
 cursor.execute("""
 SELECT DISTINCT source_document
 FROM regulatory_provisions
 WHERE LOWER(source_document) LIKE ?
 LIMIT 2
 """, (f'%{sepp.lower()}%',))
 samples = cursor.fetchall()
 for s in samples:
 print(f' {s[0][:100]}...')
 else:
 print(f' SEPP containing "{sepp}": NOT FOUND')

# Check for LEPs
print('\n=== CHECKING FOR LEPs ===')
cursor.execute("""
SELECT COUNT(DISTINCT source_document)
FROM regulatory_provisions
WHERE LOWER(source_document) LIKE '%lep%' OR LOWER(source_document) LIKE '%local environmental%'
""")
lep_count = cursor.fetchone()[0]
print(f'LEP documents found: {lep_count}')

# Sample LEPs
cursor.execute("""
SELECT DISTINCT source_document
FROM regulatory_provisions
WHERE LOWER(source_document) LIKE '%lep%' OR LOWER(source_document) LIKE '%local environmental%'
LIMIT 10
""")
lep_sources = cursor.fetchall()
if lep_sources:
 print('Sample LEP sources:')
 for source in lep_sources[:5]:
 print(f' - {source[0][:100]}...')

# Check for Inner West specifically
print('\n=== CHECKING FOR INNER WEST ===')
inner_west_terms = ['inner west', 'marrickville', 'leichhardt', 'ashfield']
for term in inner_west_terms:
 cursor.execute("""
 SELECT COUNT(DISTINCT source_document)
 FROM regulatory_provisions
 WHERE LOWER(source_document) LIKE ?
 """, (f'%{term}%',))
 count = cursor.fetchone()[0]
 if count > 0:
 print(f' "{term.title()}": {count} documents')

# Check development_permissions sources
print('\n=== DEVELOPMENT PERMISSIONS SOURCES ===')
cursor.execute("""
SELECT DISTINCT lep_name
FROM development_permissions
WHERE lep_name IS NOT NULL
LIMIT 10
""")
lep_names = cursor.fetchall()
for lep in lep_names:
 print(f' - {lep[0]}')

conn.close()