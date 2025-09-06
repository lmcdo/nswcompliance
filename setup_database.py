#!/usr/bin/env python3
"""
Database Setup Script for NSW Planning Compliance Engine
Creates PostgreSQL database with zone setback rules from export data
"""

import psycopg2
import json
import os
from typing import List, Tuple

def create_database_and_user():
    """Create the nsw_planning database and setup user permissions"""
    try:
        # Connect to PostgreSQL as superuser to create database
        conn = psycopg2.connect(
            host='localhost',
            database='postgres',  # Connect to default postgres db first
            user='postgres',
            password='postgres'
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Create database if it doesn't exist
        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = 'nsw_planning'")
        if not cursor.fetchone():
            print("Creating nsw_planning database...")
            cursor.execute('CREATE DATABASE nsw_planning')
        else:
            print("Database nsw_planning already exists")
            
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error creating database: {e}")
        return False
    
    return True

def create_zone_setback_rules_table():
    """Create the zone_setback_rules table with proper schema"""
    
    # Load the exported schema
    if not os.path.exists('database_export.json'):
        print("ERROR: database_export.json not found!")
        print("This file should contain the exported database schema and data.")
        return False
        
    with open('database_export.json', 'r') as f:
        export_data = json.load(f)
    
    try:
        # Connect to nsw_planning database
        conn = psycopg2.connect(
            host='localhost',
            database='nsw_planning',
            user='postgres', 
            password='postgres'
        )
        cursor = conn.cursor()
        
        # Drop table if exists (for clean setup)
        print("Dropping existing table (if any)...")
        cursor.execute('DROP TABLE IF EXISTS zone_setback_rules CASCADE')
        
        # Create table with exact schema from export
        print("Creating zone_setback_rules table...")
        create_sql = '''
        CREATE TABLE zone_setback_rules (
            id SERIAL PRIMARY KEY,
            rule_id VARCHAR(200) UNIQUE,
            zone VARCHAR(10) NOT NULL,
            council VARCHAR(100),
            boundary_type VARCHAR(50),
            base_value DECIMAL(8,2),
            unit VARCHAR(20) DEFAULT 'metres',
            operator VARCHAR(10) DEFAULT '>=',
            authority_type VARCHAR(20),
            precedence_level INTEGER,
            conditions TEXT,
            source_document TEXT,
            source_clause TEXT,
            effective_date DATE,
            quality_score DECIMAL(3,2),
            extraction_method VARCHAR(50),
            source_file TEXT,
            confidence DECIMAL(3,2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        '''
        cursor.execute(create_sql)
        
        # Create indexes for performance
        print("Creating indexes...")
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_zone_rules_lookup ON zone_setback_rules (zone, council, boundary_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_zone_rules_precedence ON zone_setback_rules (zone, precedence_level)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_zone_rules_confidence ON zone_setback_rules (confidence DESC)')
        
        # Insert data from export
        print(f"Inserting {export_data['count']} records...")
        
        # Prepare insert statement (skip id column, let it auto-increment)
        insert_sql = '''
        INSERT INTO zone_setback_rules (
            rule_id, zone, council, boundary_type, base_value, unit, operator,
            authority_type, precedence_level, conditions, source_document, 
            source_clause, effective_date, quality_score, extraction_method,
            source_file, confidence, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''
        
        # Insert each record (skip first column which is the auto-increment id, and last column if extra)
        for record in export_data['data']:
            # Take only the first 19 columns (skip id=0, include 1-18)
            record_data = record[1:19]  # Skip first column (id) and any extra columns
            cursor.execute(insert_sql, record_data)
        
        conn.commit()
        
        # Verify data was inserted
        cursor.execute('SELECT COUNT(*) FROM zone_setback_rules')
        count = cursor.fetchone()[0]
        print(f"Successfully inserted {count} records")
        
        # Show sample data
        cursor.execute('''
            SELECT zone, council, boundary_type, base_value, unit, confidence 
            FROM zone_setback_rules 
            WHERE zone = 'R2' AND council = 'Marrickville' 
            LIMIT 3
        ''')
        sample_data = cursor.fetchall()
        
        print("\nSample R2 Marrickville rules:")
        for row in sample_data:
            zone, council, boundary, value, unit, conf = row
            print(f"  {boundary}: {value}{unit} (confidence: {conf})")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Error setting up database: {e}")
        return False

def test_database_connection():
    """Test that the database setup works correctly"""
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='nsw_planning',
            user='postgres',
            password='postgres'
        )
        cursor = conn.cursor()
        
        # Test the exact query used by the frontend
        cursor.execute('''
            SELECT rule_id, zone, council, boundary_type, base_value, unit, 
                   confidence, conditions, source_document, source_clause
            FROM zone_setback_rules 
            WHERE zone = %s AND council ILIKE %s AND confidence >= %s
            ORDER BY precedence_level ASC, confidence DESC, boundary_type ASC
        ''', ('R2', '%Marrickville%', 0.75))
        
        results = cursor.fetchall()
        
        if results:
            print(f"Database test PASSED - Found {len(results)} R2 Marrickville setback rules")
            print("   Frontend API calls will work correctly!")
        else:
            print("Database test FAILED - No R2 Marrickville rules found")
            return False
            
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Database test FAILED: {e}")
        return False

def main():
    """Main setup function"""
    print("NSW Planning Compliance Engine - Database Setup")
    print("=" * 60)
    
    # Step 1: Create database
    if not create_database_and_user():
        print("FAILED to create database")
        return False
    
    # Step 2: Create tables and import data  
    if not create_zone_setback_rules_table():
        print("FAILED to create tables")
        return False
    
    # Step 3: Test everything works
    if not test_database_connection():
        print("Database test FAILED")
        return False
    
    print("\nDATABASE SETUP COMPLETE!")
    print("\nNext steps:")
    print("1. cd frontend-nextjs")
    print("2. npm install")
    print("3. cp .env.local.template .env.local")
    print("4. npm run dev")
    print("\nThe PRP-K3 zone-specific calculation engine is ready!")
    
    return True

if __name__ == "__main__":
    main()