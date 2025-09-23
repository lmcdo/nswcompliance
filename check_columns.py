import psycopg2

conn = psycopg2.connect(
    host='127.0.0.1',
    database='nsw_planning',
    user='postgres',
    port=5432
)

cursor = conn.cursor()

# Check columns
cursor.execute("""
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name = 'regulatory_provisions'
    AND table_schema = 'public'
    ORDER BY ordinal_position
""")

columns = [r[0] for r in cursor.fetchall()]
print(f"Columns in regulatory_provisions: {columns}")

# Get sample data
cursor.execute("SELECT * FROM regulatory_provisions LIMIT 1")
row = cursor.fetchone()

if row:
    print("\nSample row:")
    for col, val in zip(columns, row):
        val_str = str(val) if val else "NULL"
        if len(val_str) > 100:
            val_str = val_str[:100] + "..."
        print(f"  {col}: {val_str}")

conn.close()