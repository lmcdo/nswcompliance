#!/usr/bin/env python3
"""
PRP-K1: Fixed PostgreSQL Migration Script
=========================================
Corrected version that handles the actual SQLite schema properly
"""

import sqlite3
import psycopg2
import psycopg2.extras
import logging
import json
from datetime import datetime
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PostgreSQLMigration:
    def __init__(self):
        self.sqlite_path = 'nsw_planning.db'
        self.pg_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'nsw_planning',
            'user': 'postgres',
            'password': 'postgres'
        }
        
    def setup_postgresql(self):
        """Set up PostgreSQL database and schema"""
        try:
            # Connect to postgres database first to create our database
            conn = psycopg2.connect(
                host=self.pg_config['host'],
                port=self.pg_config['port'],
                database='postgres',
                user=self.pg_config['user'],
                password=self.pg_config['password']
            )
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Create database if it doesn't exist
            cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", 
                          (self.pg_config['database'],))
            exists = cursor.fetchone()
            
            if not exists:
                logger.info(f"Creating PostgreSQL database: {self.pg_config['database']}")
                cursor.execute(f'CREATE DATABASE "{self.pg_config["database"]}"')
            else:
                logger.info(f"Database {self.pg_config['database']} already exists")
                
            cursor.close()
            conn.close()
            
            # Connect to our database
            conn = psycopg2.connect(**self.pg_config)
            cursor = conn.cursor()
            
            logger.info("Creating PostgreSQL schema...")
            
            # Create main tables with proper schema
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS regulatory_provisions (
                    id SERIAL PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    provision_type TEXT NOT NULL,
                    ref_number TEXT,
                    provision_text TEXT NOT NULL,
                    zone TEXT,
                    development_type TEXT,
                    page_number INTEGER,
                    section_header TEXT,
                    text_level INTEGER,
                    original_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    domain_classification TEXT DEFAULT 'GENERAL_PROVISIONS',
                    classification_confidence REAL DEFAULT 0.95,
                    cross_contamination_checked BOOLEAN DEFAULT FALSE,
                    prp_k1_enhanced BOOLEAN DEFAULT FALSE,
                    migration_id TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS development_controls (
                    id SERIAL PRIMARY KEY,
                    provision_id INTEGER REFERENCES regulatory_provisions(id),
                    control_type TEXT NOT NULL,
                    value_text TEXT,
                    zone_applicable TEXT,
                    confidence_score REAL DEFAULT 0.5,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS quantitative_standards (
                    id SERIAL PRIMARY KEY,
                    provision_id INTEGER REFERENCES regulatory_provisions(id),
                    numeric_value REAL,
                    unit TEXT,
                    qualifier TEXT,
                    context TEXT,
                    confidence_score REAL DEFAULT 0.5,
                    raw_text TEXT,
                    manual_verified BOOLEAN DEFAULT FALSE,
                    created_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS kg_relationships (
                    id SERIAL PRIMARY KEY,
                    subject_text TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object_text TEXT NOT NULL,
                    subject_entity_id INTEGER,
                    object_entity_id INTEGER,
                    relationship_context TEXT,
                    document_id TEXT,
                    page_number INTEGER,
                    section_header TEXT,
                    confidence_score REAL DEFAULT 0.5,
                    original_ref_type TEXT,
                    original_ref_id INTEGER,
                    extraction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS development_pathways (
                    id SERIAL PRIMARY KEY,
                    development_type TEXT,
                    zone TEXT,
                    qualification_criteria JSONB,
                    pathway_type TEXT,
                    confidence_score REAL DEFAULT 0.5,
                    source_provision_ids TEXT,
                    manual_verified BOOLEAN DEFAULT FALSE,
                    created_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for performance
            indexes = [
                'CREATE INDEX IF NOT EXISTS idx_rp_domain ON regulatory_provisions(domain_classification)',
                'CREATE INDEX IF NOT EXISTS idx_rp_document ON regulatory_provisions(document_id)',
                'CREATE INDEX IF NOT EXISTS idx_rp_zone ON regulatory_provisions(zone)',
                'CREATE INDEX IF NOT EXISTS idx_dc_type ON development_controls(control_type)',
                'CREATE INDEX IF NOT EXISTS idx_dc_zone ON development_controls(zone_applicable)',
                'CREATE INDEX IF NOT EXISTS idx_kg_predicate ON kg_relationships(predicate)',
            ]
            
            for index_sql in indexes:
                cursor.execute(index_sql)
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info("PostgreSQL schema created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set up PostgreSQL: {e}")
            return False
    
    def migrate_data(self):
        """Migrate data from SQLite to PostgreSQL"""
        try:
            # Connect to SQLite
            sqlite_conn = sqlite3.connect(self.sqlite_path)
            sqlite_conn.row_factory = sqlite3.Row
            sqlite_cursor = sqlite_conn.cursor()
            
            # Connect to PostgreSQL
            pg_conn = psycopg2.connect(**self.pg_config)
            pg_cursor = pg_conn.cursor()
            
            # Migrate regulatory_provisions
            logger.info("Migrating regulatory_provisions...")
            sqlite_cursor.execute("SELECT COUNT(*) FROM regulatory_provisions")
            total_provisions = sqlite_cursor.fetchone()[0]
            logger.info(f"Found {total_provisions} regulatory provisions to migrate")
            
            sqlite_cursor.execute("SELECT * FROM regulatory_provisions")
            provisions = sqlite_cursor.fetchall()
            
            for i, row in enumerate(provisions, 1):
                pg_cursor.execute('''
                    INSERT INTO regulatory_provisions 
                    (document_id, provision_type, ref_number, provision_text, zone, 
                     development_type, page_number, section_header, text_level, original_id,
                     created_at, domain_classification, classification_confidence,
                     cross_contamination_checked, prp_k1_enhanced, migration_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    row['document_id'], row['provision_type'], row['ref_number'],
                    row['provision_text'], row['zone'], row['development_type'],
                    row['page_number'], row['section_header'], row['text_level'],
                    row['original_id'], row['created_at'], row['domain_classification'],
                    row['classification_confidence'], 
                    bool(row['cross_contamination_checked']) if row['cross_contamination_checked'] is not None else False,
                    bool(row['prp_k1_enhanced']) if row['prp_k1_enhanced'] is not None else False,
                    row['migration_id']
                ))
                
                if i % 1000 == 0:
                    logger.info(f"Migrated {i}/{total_provisions} provisions ({i/total_provisions*100:.1f}%)")
                    pg_conn.commit()
            
            pg_conn.commit()
            logger.info(f"Successfully migrated {total_provisions} regulatory provisions")
            
            # Migrate other tables if they exist
            tables_to_migrate = [
                'development_controls',
                'quantitative_standards', 
                'kg_relationships',
                'development_pathways'
            ]
            
            for table in tables_to_migrate:
                try:
                    sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = sqlite_cursor.fetchone()[0]
                    if count > 0:
                        logger.info(f"Migrating {count} records from {table}...")
                        sqlite_cursor.execute(f"SELECT * FROM {table}")
                        rows = sqlite_cursor.fetchall()
                        
                        for row in rows:
                            # Build dynamic insert based on columns (excluding id)
                            columns = [col for col in row.keys() if col != 'id']
                            values = []
                            
                            for col in columns:
                                val = row[col]
                                # Convert SQLite boolean (0/1) to PostgreSQL boolean for specific columns
                                if col in ['manual_verified', 'cross_contamination_checked', 'prp_k1_enhanced'] and val is not None:
                                    val = bool(val)
                                values.append(val)
                            
                            placeholders = ','.join(['%s'] * len(values))
                            columns_str = ','.join(columns)
                            
                            pg_cursor.execute(
                                f'INSERT INTO {table} ({columns_str}) VALUES ({placeholders})',
                                values
                            )
                        
                        pg_conn.commit()
                        logger.info(f"Successfully migrated {count} records from {table}")
                        
                except sqlite3.OperationalError:
                    logger.info(f"Table {table} doesn't exist in SQLite, skipping")
                    
            # Close connections
            sqlite_cursor.close()
            sqlite_conn.close()
            pg_cursor.close()
            pg_conn.close()
            
            logger.info("Data migration completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False
    
    def verify_migration(self):
        """Verify the migration was successful"""
        try:
            # Connect to PostgreSQL
            pg_conn = psycopg2.connect(**self.pg_config)
            pg_cursor = pg_conn.cursor()
            
            # Check record counts
            pg_cursor.execute("SELECT COUNT(*) FROM regulatory_provisions")
            pg_count = pg_cursor.fetchone()[0]
            
            # Connect to SQLite to compare
            sqlite_conn = sqlite3.connect(self.sqlite_path)
            sqlite_cursor = sqlite_conn.cursor()
            sqlite_cursor.execute("SELECT COUNT(*) FROM regulatory_provisions")
            sqlite_count = sqlite_cursor.fetchone()[0]
            
            logger.info(f"SQLite provisions: {sqlite_count}")
            logger.info(f"PostgreSQL provisions: {pg_count}")
            
            if pg_count == sqlite_count:
                logger.info("✅ Migration verification successful!")
                
                # Test a sample query
                pg_cursor.execute("""
                    SELECT domain_classification, COUNT(*) 
                    FROM regulatory_provisions 
                    GROUP BY domain_classification 
                    LIMIT 5
                """)
                
                results = pg_cursor.fetchall()
                logger.info("Sample domain classification counts:")
                for domain, count in results:
                    logger.info(f"  {domain}: {count}")
                
                return True
            else:
                logger.error(f"❌ Record count mismatch!")
                return False
                
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return False
        finally:
            if 'pg_cursor' in locals():
                pg_cursor.close()
            if 'pg_conn' in locals():
                pg_conn.close()
            if 'sqlite_cursor' in locals():
                sqlite_cursor.close()
            if 'sqlite_conn' in locals():
                sqlite_conn.close()

def main():
    """Execute the PostgreSQL migration"""
    logger.info("🚀 Starting PRP-K1 PostgreSQL Migration (Fixed Version)")
    
    migration = PostgreSQLMigration()
    
    # Step 1: Set up PostgreSQL
    if not migration.setup_postgresql():
        logger.error("❌ Failed to set up PostgreSQL")
        return False
    
    # Step 2: Migrate data
    if not migration.migrate_data():
        logger.error("❌ Failed to migrate data") 
        return False
    
    # Step 3: Verify migration
    if not migration.verify_migration():
        logger.error("❌ Migration verification failed")
        return False
        
    logger.info("✅ PRP-K1 PostgreSQL Migration completed successfully!")
    logger.info("NextJS frontend can now connect to PostgreSQL database")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)