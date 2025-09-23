import psycopg2

conn = psycopg2.connect(
    host='127.0.0.1',
    database='nsw_planning',
    user='postgres',
    port=5432
)

cursor = conn.cursor()

# Get all tables
cursor.execute("""
    SELECT schemaname, tablename
    FROM pg_tables
    WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
    ORDER BY schemaname, tablename
""")

tables = cursor.fetchall()
print(f"Total tables found: {len(tables)}\n")

# Group by schema
schemas = {}
for schema, table in tables:
    if schema not in schemas:
        schemas[schema] = []
    schemas[schema].append(table)

# Print by schema
for schema, table_list in schemas.items():
    print(f"\nSchema: {schema} ({len(table_list)} tables)")
    print("-" * 40)
    for table in table_list[:10]:  # First 10 tables per schema
        # Get row count
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {schema}.{table}")
            count = cursor.fetchone()[0]
            print(f"  {table}: {count:,} rows")
        except:
            print(f"  {table}: (error counting)")

conn.close()