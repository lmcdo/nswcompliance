from db_safety_wrapper import get_safe_connection

conn = get_safe_connection()
if conn:
    cur = conn.cursor()
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    tables = cur.fetchall()
    print('Available tables:')
    for table in tables:
        print(f'  - {table[0]}')
    conn.close()