import psycopg2

conn = psycopg2.connect(
    host='localhost',
    database='nsw_planning',
    user='postgres',
    password='postgres'
)

cur = conn.cursor()
cur.execute("""
    SELECT EXISTS(
        SELECT FROM information_schema.tables
        WHERE table_name='lep_land_use_table'
    )
""")

table_exists = cur.fetchone()[0]
print(f"lep_land_use_table exists: {table_exists}")

if table_exists:
    cur.execute("SELECT COUNT(*) FROM lep_land_use_table")
    count = cur.fetchone()[0]
    print(f"Rows in table: {count}")

conn.close()
