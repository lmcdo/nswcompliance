from db_safety_wrapper import get_safe_connection
import json

conn = get_safe_connection()
if conn:
    cur = conn.cursor()
    # Check for clause 4.3 (building height) content
    print("Checking for clause 4.3 content...")
    cur.execute("""
        SELECT clause_number, title, content, source_document
        FROM authoritative_provisions
        WHERE clause_number LIKE '4.3%'
        LIMIT 5
    """)
    results = cur.fetchall()
    if results:
        for row in results:
            print(f'Clause: {row[0]}')
            print(f'Title: {row[1]}')
            print(f'Content length: {len(row[2]) if row[2] else 0}')
            print(f'First 200 chars: {row[2][:200] if row[2] else "No content"}')
            print(f'Source: {row[3]}')
            print('---')
    else:
        print("No clause 4.3 found")

    # Check for clause 4.4 (FSR) content
    print("\nChecking for clause 4.4 content...")
    cur.execute("""
        SELECT clause_number, title, content, source_document
        FROM authoritative_provisions
        WHERE clause_number LIKE '4.4%'
        LIMIT 5
    """)
    results = cur.fetchall()
    if results:
        for row in results:
            print(f'Clause: {row[0]}')
            print(f'Title: {row[1]}')
            print(f'Content length: {len(row[2]) if row[2] else 0}')
            print(f'First 200 chars: {row[2][:200] if row[2] else "No content"}')
            print(f'Source: {row[3]}')
            print('---')
    else:
        print("No clause 4.4 found")

    conn.close()