import psycopg2
import sys

# Read the SQL file
with open('scripts/create_authoritative_schema.sql', 'r') as f:
    sql_content = f.read()

# Connect to database
conn = psycopg2.connect(
    host='127.0.0.1',
    database='nsw_planning',
    user='postgres',
    port=5432
)

# Execute the SQL
cursor = conn.cursor()
try:
    cursor.execute(sql_content)
    conn.commit()
    print("Successfully created authoritative schema and tables!")

    # Verify what was created
    cursor.execute("""
        SELECT schemaname, tablename
        FROM pg_tables
        WHERE schemaname = 'authoritative'
        ORDER BY tablename
    """)
    tables = cursor.fetchall()
    print(f"\nCreated {len(tables)} tables in 'authoritative' schema:")
    for schema, table in tables:
        print(f"  - {schema}.{table}")

except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    conn.close()