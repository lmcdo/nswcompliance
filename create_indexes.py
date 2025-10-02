import psycopg2

# Connect to corrected database
conn = psycopg2.connect(
    host='localhost',
    database='nsw_planning_corrected',
    user='postgres',
    password='postgres',
    port='5432'
)
conn.autocommit = True
cursor = conn.cursor()

print('Creating performance indexes on nsw_planning_corrected...')
print()

indexes = [
    # Primary key indexes (may already exist)
    ("idx_regulatory_provisions_id", "regulatory_provisions", "(id)"),
    ("idx_legal_instruments_id", "legal_instruments", "(id)"),
    ("idx_documents_id", "documents", "(id)"),

    # Foreign key relationship indexes
    ("idx_regulatory_provisions_instrument_id", "regulatory_provisions", "(instrument_id)"),
    ("idx_regulatory_provisions_document_id", "regulatory_provisions", "(document_id)"),

    # Search optimization indexes
    ("idx_regulatory_provisions_ref_number", "regulatory_provisions", "(ref_number)"),
    ("idx_legal_instruments_type", "legal_instruments", "(instrument_type)"),
    ("idx_legal_instruments_precedence", "legal_instruments", "(legal_precedence)"),

    # Composite index for main API query
    ("idx_provision_complete_lookup", "regulatory_provisions", "(id, instrument_id, document_id)"),
]

for index_name, table_name, columns in indexes:
    try:
        sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} {columns}"
        cursor.execute(sql)
        print(f"✓ Created index: {index_name}")
    except Exception as e:
        print(f"✗ Error creating {index_name}: {e}")

print()
print('Verifying created indexes:')
cursor.execute("""
    SELECT schemaname, tablename, indexname
    FROM pg_indexes
    WHERE tablename IN ('regulatory_provisions', 'legal_instruments', 'documents')
    AND indexname LIKE 'idx_%'
    ORDER BY tablename, indexname
""")

results = cursor.fetchall()
for schema, table, index in results:
    print(f"  {table}: {index}")

cursor.close()
conn.close()

print()
print('Performance indexes created successfully!')