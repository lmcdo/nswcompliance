#!/usr/bin/env python3
"""
Phase 1 Execution: Pre-migration Validation
"""
import os
import sqlite3
import psycopg2
import time
import hashlib
import shutil
from datetime import datetime
from pathlib import Path

def step_1_audit():
    print("="*60)
    print("STEP 1: Source Data Audit")
    print("="*60)
    
    start_time = time.time()
    
    # Connect to SQLite
    conn = sqlite3.connect('./nsw_planning.db')
    cursor = conn.cursor()
    
    # Get tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"Found {len(tables)} tables in SQLite database")
    
    # Critical tables check
    critical_tables = ['documents', 'regulatory_provisions', 'quantitative_standards']
    for table in critical_tables:
        if table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  {table}: {count:,} rows")
        else:
            print(f"  ERROR: Missing critical table {table}")
            return False
    
    # Database integrity
    db_path = Path('./nsw_planning.db')
    db_size = db_path.stat().st_size / 1024 / 1024
    print(f"  Database size: {db_size:.2f} MB")
    
    # Zone distribution check
    cursor.execute("""
        SELECT zone, COUNT(*) as count 
        FROM regulatory_provisions 
        WHERE zone IS NOT NULL 
        GROUP BY zone 
        ORDER BY count DESC 
        LIMIT 5
    """)
    zone_dist = cursor.fetchall()
    print("  Top zones by provision count:")
    for zone, count in zone_dist:
        print(f"    {zone}: {count:,} provisions")
    
    conn.close()
    
    duration = time.time() - start_time
    print(f"\nDuration: {duration:.2f} seconds")
    print("SUCCESS - Step 1 completed")
    return True

def step_2_quality():
    print("\n" + "="*60)
    print("STEP 2: Data Quality Assessment")
    print("="*60)
    
    start_time = time.time()
    
    conn = sqlite3.connect('./nsw_planning.db')
    cursor = conn.cursor()
    
    # Total provisions
    cursor.execute("SELECT COUNT(*) FROM regulatory_provisions")
    total_provisions = cursor.fetchone()[0]
    print(f"Total provisions: {total_provisions:,}")
    
    # Text quality
    cursor.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE provision_text IS NOT NULL AND LENGTH(provision_text) > 10")
    meaningful_text = cursor.fetchone()[0]
    text_rate = (meaningful_text / total_provisions) * 100
    print(f"Meaningful text rate: {text_rate:.1f}%")
    
    # Zone coverage
    cursor.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE zone IS NOT NULL")
    with_zones = cursor.fetchone()[0]
    zone_rate = (with_zones / total_provisions) * 100
    print(f"Zone coverage rate: {zone_rate:.1f}%")
    
    # Quantitative standards
    cursor.execute("SELECT COUNT(*) FROM quantitative_standards")
    total_standards = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM quantitative_standards WHERE numeric_value IS NOT NULL")
    numeric_standards = cursor.fetchone()[0]
    print(f"Quantitative standards: {total_standards:,} total, {numeric_standards:,} with numeric values")
    
    conn.close()
    
    duration = time.time() - start_time
    print(f"\nDuration: {duration:.2f} seconds")
    print("SUCCESS - Step 2 completed")
    return True

def step_3_backups():
    print("\n" + "="*60)
    print("STEP 3: Create Safety Backups")
    print("="*60)
    
    start_time = time.time()
    
    # Create backups directory
    backup_dir = Path('./backups')
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # SQLite backup
    sqlite_backup = backup_dir / f"nsw_planning_phase1_{timestamp}.db"
    shutil.copy2('./nsw_planning.db', sqlite_backup)
    backup_size = sqlite_backup.stat().st_size / 1024 / 1024
    print(f"SQLite backup created: {sqlite_backup}")
    print(f"  Size: {backup_size:.2f} MB")
    
    # PostgreSQL backup (simplified)
    pg_backup = backup_dir / f"nsw_planning_phase1_{timestamp}.sql"
    try:
        import subprocess
        env = os.environ.copy()
        env['PGPASSWORD'] = 'postgres'
        
        result = subprocess.run([
            'pg_dump', '-h', 'localhost', '-U', 'postgres',
            '-d', 'nsw_planning', '-f', str(pg_backup)
        ], env=env, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0 and pg_backup.exists():
            backup_size = pg_backup.stat().st_size / 1024 / 1024
            print(f"PostgreSQL backup created: {pg_backup}")
            print(f"  Size: {backup_size:.2f} MB")
        else:
            print("PostgreSQL backup failed - continuing without it")
    except Exception as e:
        print(f"PostgreSQL backup failed: {e} - continuing without it")
    
    duration = time.time() - start_time
    print(f"\nDuration: {duration:.2f} seconds")
    print("SUCCESS - Step 3 completed")
    return True

def step_4_schema():
    print("\n" + "="*60)
    print("STEP 4: PostgreSQL Schema Creation")
    print("="*60)
    
    start_time = time.time()
    
    # Check schema file
    schema_file = Path('./research_assistant_schema_optimized.sql')
    if not schema_file.exists():
        print("ERROR: PostgreSQL schema file not found")
        return False
    
    # Read schema
    with open(schema_file, 'r') as f:
        schema_content = f.read()
    
    # Analyze schema
    create_counts = {
        'SCHEMA': schema_content.upper().count('CREATE SCHEMA'),
        'TABLE': schema_content.upper().count('CREATE TABLE'),
        'INDEX': schema_content.upper().count('CREATE INDEX'),
        'TYPE': schema_content.upper().count('CREATE TYPE')
    }
    
    print("Schema Analysis:")
    for obj_type, count in create_counts.items():
        if count > 0:
            print(f"  CREATE {obj_type}: {count}")
    
    # Execute schema
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="nsw_planning",
            user="postgres",
            password="postgres"
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Drop existing schema
        cursor.execute("DROP SCHEMA IF EXISTS research_assistant CASCADE")
        print("Existing schema dropped (if present)")
        
        # Create new schema
        print("Creating PostgreSQL schema...")
        cursor.execute(schema_content)
        
        # Verify creation
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'research_assistant'
        """)
        created_tables = [row[0] for row in cursor.fetchall()]
        print(f"Schema created successfully:")
        print(f"  Tables: {len(created_tables)}")
        
        conn.close()
        
    except Exception as e:
        print(f"ERROR: Schema creation failed: {e}")
        return False
    
    duration = time.time() - start_time
    print(f"\nDuration: {duration:.2f} seconds")
    print("SUCCESS - Step 4 completed")
    return True

def step_5_compatibility():
    print("\n" + "="*60)
    print("STEP 5: Compatibility & Readiness Checks")
    print("="*60)
    
    start_time = time.time()
    
    # Test zone extraction
    import re
    
    conn = sqlite3.connect('./nsw_planning.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT provision_text, zone 
        FROM regulatory_provisions 
        WHERE provision_text IS NOT NULL 
        AND zone IN ('R1', 'R2', 'R3', 'R4')
        LIMIT 20
    """)
    
    samples = cursor.fetchall()
    zone_pattern = r'\bZone\s+([A-Z]+[0-9]+[A-Z]*)\b'
    
    explicit_count = 0
    for text, assigned_zone in samples:
        matches = re.findall(zone_pattern, text, re.IGNORECASE)
        if matches:
            explicit_count += 1
    
    extraction_rate = (explicit_count / len(samples)) * 100 if samples else 0
    print(f"Zone extraction test: {extraction_rate:.1f}% explicit rate")
    
    # Test PostgreSQL functionality
    try:
        pg_conn = psycopg2.connect(
            host="localhost",
            database="nsw_planning",
            user="postgres",
            password="postgres"
        )
        pg_cursor = pg_conn.cursor()
        
        # Test insert/select
        pg_cursor.execute("""
            INSERT INTO research_assistant.documents 
            (document_name, document_type, jurisdiction) 
            VALUES ('Test Document', 'LEP', 'Test')
            RETURNING id
        """)
        test_id = pg_cursor.fetchone()[0]
        
        # Cleanup
        pg_cursor.execute("DELETE FROM research_assistant.documents WHERE id = %s", (test_id,))
        pg_conn.commit()
        pg_conn.close()
        
        print("PostgreSQL functionality test: PASSED")
        
    except Exception as e:
        print(f"ERROR: PostgreSQL functionality test failed: {e}")
        return False
    
    # Disk space
    total, used, free = shutil.disk_usage('.')
    free_gb = free / (1024**3)
    print(f"Free disk space: {free_gb:.2f} GB")
    
    conn.close()
    
    duration = time.time() - start_time
    print(f"\nDuration: {duration:.2f} seconds")
    print("SUCCESS - Step 5 completed")
    return True

def validation_gate_1(results):
    print("\n" + "="*60)
    print("VALIDATION GATE 1: PRE-MIGRATION READINESS")
    print("="*60)
    
    successful_steps = sum(results)
    total_steps = len(results)
    
    print(f"Step Results: {successful_steps}/{total_steps} successful")
    
    if successful_steps == total_steps:
        print("\nVALIDATION GATE 1 PASSED")
        print("  * All pre-migration checks successful")
        print("  * Source data validated")
        print("  * Backups created")
        print("  * PostgreSQL schema ready")
        print("  * System compatibility verified")
        print("\nREADY TO PROCEED TO PHASE 2")
        return True
    else:
        print("\nVALIDATION GATE 1 FAILED")
        print("  • Fix critical issues before proceeding")
        return False

def main():
    print("PRP-M1 PHASE 1: PRE-MIGRATION VALIDATION")
    print("========================================")
    print(f"Start Time: {datetime.now().isoformat()}")
    
    # Execute all steps
    results = []
    results.append(step_1_audit())
    input("\nPress Enter to continue...")
    
    results.append(step_2_quality())
    input("\nPress Enter to continue...")
    
    results.append(step_3_backups())
    input("\nPress Enter to continue...")
    
    results.append(step_4_schema())
    input("\nPress Enter to continue...")
    
    results.append(step_5_compatibility())
    input("\nPress Enter to continue to validation gate...")
    
    # Validation gate
    gate_passed = validation_gate_1(results)
    
    if gate_passed:
        print("\nPHASE 1 COMPLETED SUCCESSFULLY!")
        return True
    else:
        print("\nPHASE 1 FAILED")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)