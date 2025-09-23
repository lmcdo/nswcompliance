from db_safety_wrapper import get_safe_connection
import json

conn = get_safe_connection()
if conn:
    cur = conn.cursor()

    # Check regulatory_provisions table structure
    print("Checking regulatory_provisions table structure...")
    cur.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'regulatory_provisions'
        ORDER BY ordinal_position
    """)
    columns = cur.fetchall()
    print("Columns:")
    for col in columns:
        print(f"  - {col[0]}: {col[1]}")

    # Check for clause 4.3 and 4.4 content
    print("\n\nChecking for clause 4.3 and 4.4 content...")
    cur.execute("""
        SELECT clause_number, title, content
        FROM regulatory_provisions
        WHERE clause_number IN ('4.3', '4.4', '4.3A', '4.3B', '4.4A', '4.4B')
           OR clause_number LIKE '4.3%'
           OR clause_number LIKE '4.4%'
        LIMIT 10
    """)
    results = cur.fetchall()
    if results:
        for row in results:
            print(f'\nClause: {row[0]}')
            print(f'Title: {row[1]}')
            if row[2]:
                print(f'Content length: {len(row[2])}')
                print(f'First 300 chars: {row[2][:300]}...')
            else:
                print('Content: None')
            print('---')
    else:
        print("No clauses 4.3 or 4.4 found")

    conn.close()