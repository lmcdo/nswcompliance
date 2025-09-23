#!/usr/bin/env python3
import psycopg2

conn = psycopg2.connect(host='localhost', port=5432, database='nsw_planning', user='postgres', password='postgres')
cursor = conn.cursor()

# Create authoritative schema
cursor.execute('CREATE SCHEMA IF NOT EXISTS authoritative')

# Create hierarchy_resolution_cache table
cursor.execute('''
CREATE TABLE IF NOT EXISTS authoritative.hierarchy_resolution_cache (
 cache_key VARCHAR(255) PRIMARY KEY,
 query_params JSONB,
 result_data JSONB,
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 expires_at TIMESTAMP,
 cache_version INTEGER DEFAULT 1
)
''')

conn.commit()
print('Created authoritative schema and hierarchy_resolution_cache table')
conn.close()