#!/usr/bin/env python3
"""
Fix PostgreSQL schema by dropping and recreating with correct structure
"""

import psycopg2

def fix_postgresql_schema():
 """Drop and recreate PostgreSQL schema correctly"""
 try:
 conn = psycopg2.connect(
 host="localhost",
 port=5432,
 database="nsw_planning",
 user="postgres",
 password="postgres"
 )
 cursor = conn.cursor()

 print("Dropping existing regulatory_provisions table...")
 cursor.execute("DROP TABLE IF EXISTS regulatory_provisions CASCADE")

 print("Creating corrected regulatory_provisions table...")
 cursor.execute("""
 CREATE TABLE regulatory_provisions (
 id SERIAL PRIMARY KEY,
 document_id VARCHAR(500) NOT NULL,
 provision_type VARCHAR(150),
 ref_number VARCHAR(300),
 provision_text TEXT NOT NULL,
 zone VARCHAR(100),
 development_type VARCHAR(500),
 page_number INTEGER,
 section_header VARCHAR(100),
 text_level INTEGER,
 original_id INTEGER,
 domain_classification VARCHAR(100) DEFAULT 'GENERAL_PROVISIONS',
 classification_confidence REAL DEFAULT 0.95,
 cross_contamination_checked BOOLEAN DEFAULT FALSE,
 prp_k1_enhanced BOOLEAN DEFAULT FALSE,
 migration_id VARCHAR(100),
 zone_confidence REAL,
 zone_inference_method VARCHAR(100),
 version_id INTEGER,
 version_effective_date DATE,
 is_current BOOLEAN DEFAULT TRUE,
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
 )
 """)

 conn.commit()

 # Verify table creation
 cursor.execute("""
 SELECT column_name, data_type
 FROM information_schema.columns
 WHERE table_name = 'regulatory_provisions'
 ORDER BY ordinal_position
 """)

 columns = cursor.fetchall()
 print(f"Table created successfully with {len(columns)} columns:")
 for col in columns:
 print(f" {col[0]} ({col[1]})")

 conn.close()
 print("\nPostgreSQL schema fixed successfully!")

 except Exception as e:
 print(f"Error fixing PostgreSQL schema: {e}")

if __name__ == "__main__":
 fix_postgresql_schema()