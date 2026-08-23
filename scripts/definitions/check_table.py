#!/usr/bin/env python3
"""Check if regulatory_definitions table exists."""

import os
import psycopg2

DB_CONFIG = {
    'dbname': 'nsw_planning',
    'user': 'postgres',
    'password': os.environ['DB_PASSWORD'],
    'host': 'localhost'
}

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

# Check if table exists
cur.execute("""
    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_name = 'regulatory_definitions'
    );
""")
exists = cur.fetchone()[0]
print(f"Table exists: {exists}")

if not exists:
    print("Creating table...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS regulatory_definitions (
          id SERIAL PRIMARY KEY,
          term VARCHAR(200) NOT NULL,
          term_normalized VARCHAR(200) NOT NULL,
          definition_text TEXT NOT NULL,
          definition_summary VARCHAR(500),
          source_document TEXT NOT NULL,
          source_clause VARCHAR(100),
          legislation_type VARCHAR(30) NOT NULL,
          lga VARCHAR(50),
          former_council VARCHAR(50),
          pdf_page INTEGER,
          pdf_source_file TEXT,
          pdf_page_image_url TEXT,
          domain_tags TEXT[],
          extraction_confidence NUMERIC(3,2) DEFAULT 1.0,
          manual_verified BOOLEAN DEFAULT false,
          created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
          updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
          UNIQUE (term_normalized, source_document)
        );
    """)
    conn.commit()
    print("Table created.")

# List tables
cur.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    ORDER BY table_name;
""")
print("\nTables in database:")
for row in cur.fetchall():
    if 'defin' in row[0].lower() or 'regula' in row[0].lower():
        print(f"  * {row[0]}")

cur.close()
conn.close()
