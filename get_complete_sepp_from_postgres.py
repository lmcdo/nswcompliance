import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(
    host='localhost',
    database='nsw_planning_corrected',
    user='postgres',
    password='postgres',
    port='5432'
)
cursor = conn.cursor(cursor_factory=RealDictCursor)

print('=== GETTING COMPLETE SEPP TEXT FROM CORRECTED POSTGRESQL ===')
print()

# Search for the SEPP document in PostgreSQL
cursor.execute("""
    SELECT id, pdf_name, char_count, full_text
    FROM documents
    WHERE full_text ILIKE '%competing provision%'
    AND full_text ILIKE '%mains-supplied potable water%'
    LIMIT 1
""")
sepp_doc = cursor.fetchone()

if sepp_doc:
    print(f'SEPP Document found in PostgreSQL:')
    print(f'  ID: {sepp_doc["id"]}')
    print(f'  Name: {sepp_doc["pdf_name"]}')
    print(f'  Char count: {sepp_doc["char_count"]}')
    print()

    # Extract just clause 2.2 from the full text
    full_text = sepp_doc["full_text"]

    # Find the start of clause 2.2
    start_pattern = "2.2"
    start_idx = full_text.find(start_pattern)

    if start_idx != -1:
        # Find the next clause (2.3 or Chapter 3)
        end_patterns = ["Chapter 3", "3.1", "2.3"]
        end_idx = len(full_text)

        for pattern in end_patterns:
            idx = full_text.find(pattern, start_idx + 10)
            if idx != -1 and idx < end_idx:
                end_idx = idx

        clause_text = full_text[start_idx:end_idx].strip()

        print('COMPLETE CLAUSE 2.2 FROM POSTGRESQL:')
        print('=' * 80)
        print(clause_text)
        print('=' * 80)

    else:
        print('Could not find clause 2.2 in the document')

else:
    print('SEPP document NOT found in PostgreSQL!')

cursor.close()
conn.close()