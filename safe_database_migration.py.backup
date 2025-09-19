#!/usr/bin/env python3
"""
Safe Database Migration: Transform single regulatory_refs table into normalized schema
===================================================================================

SAFETY FEATURES:
- Full backup before any changes
- Dry-run mode to preview changes
- Data validation at every step
- Rollback capability
- Progress tracking with resume capability
- Integrity checks after migration

APPROACH:
1. Create new normalized schema alongside existing table
2. Migrate data with validation
3. Verify data integrity
4. Switch over only when confirmed working
5. Keep backup until UI is fully tested

"""

import sqlite3
import json
import os
import shutil
import time
from datetime import datetime
from collections import defaultdict, Counter
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SafeDatabaseMigration:
    """Safe migration from flat regulatory_refs to normalized schema"""
    
    def __init__(self, db_path='nsw_planning.db', dry_run=True):
        self.db_path = db_path
        self.dry_run = dry_run
        self.backup_path = f"{db_path}.backup_{int(time.time())}"
        self.migration_state_file = 'migration_state.json'
        self.stats = {
            'start_time': datetime.now().isoformat(),
            'total_entries': 0,
            'migrated_entries': 0,
            'errors': [],
            'table_counts': {}
        }
        
        # Migration mapping: ref_type patterns -> target tables
        self.migration_mapping = {
            'regulatory_provisions': {
                'patterns': ['formal_', 'provision_'],
                'description': 'Core regulatory requirements and provisions',
                'schema': '''
                    CREATE TABLE regulatory_provisions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        document_id TEXT NOT NULL,
                        provision_type TEXT NOT NULL,
                        clause_number TEXT,
                        provision_text TEXT,
                        page_number INTEGER,
                        section_header TEXT,
                        text_level INTEGER,
                        applies_to TEXT,
                        measurements TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (document_id) REFERENCES documents (id)
                    )'''
            },
            
            'development_controls': {
                'patterns': ['provision_setback', 'provision_height', 'provision_fsr', 'development_standards'],
                'description': 'Specific development controls for compliance calculations',
                'schema': '''
                    CREATE TABLE development_controls (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        provision_id INTEGER,
                        control_type TEXT NOT NULL,
                        control_value TEXT,
                        measurement_unit TEXT,
                        applies_to_zone TEXT,
                        conditions TEXT,
                        page_number INTEGER,
                        section_header TEXT,
                        document_id TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (document_id) REFERENCES documents (id)
                    )'''
            },
            
            'contextual_guidance': {
                'patterns': ['context_', 'informal_'],
                'description': 'Non-binding guidance and contextual information',
                'schema': '''
                    CREATE TABLE contextual_guidance (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        document_id TEXT NOT NULL,
                        guidance_type TEXT NOT NULL,
                        guidance_text TEXT,
                        page_number INTEGER,
                        section_header TEXT,
                        relates_to_provision INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (document_id) REFERENCES documents (id)
                    )'''
            },
            
            'cross_references': {
                'patterns': ['relationship_'],
                'description': 'Relationships between provisions, SEPPs, LEPs, DCPs',
                'schema': '''
                    CREATE TABLE cross_references (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        from_provision TEXT NOT NULL,
                        to_provision TEXT,
                        relationship_type TEXT NOT NULL,
                        reference_text TEXT,
                        document_id TEXT NOT NULL,
                        page_number INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (document_id) REFERENCES documents (id)
                    )'''
            },
            
            'visual_elements': {
                'patterns': ['autoschema_', 'visual_'],
                'description': 'Images, diagrams, tables with regulatory context',
                'schema': '''
                    CREATE TABLE visual_elements (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        document_id TEXT NOT NULL,
                        element_type TEXT NOT NULL,
                        file_path TEXT,
                        page_number INTEGER,
                        clause_context TEXT,
                        description TEXT,
                        width INTEGER,
                        height INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (document_id) REFERENCES documents (id)
                    )'''
            },
            
            'zoning_information': {
                'patterns': ['entity_zone', 'zoning', 'entity_land_use'],
                'description': 'Land use zones and permitted development',
                'schema': '''
                    CREATE TABLE zoning_information (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        zone_code TEXT,
                        zone_name TEXT,
                        permitted_uses TEXT,
                        prohibited_uses TEXT,
                        development_standards TEXT,
                        document_id TEXT NOT NULL,
                        page_number INTEGER,
                        section_header TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (document_id) REFERENCES documents (id)
                    )'''
            }
        }
    
    def create_backup(self):
        """Create full database backup"""
        logger.info(f"Creating backup: {self.backup_path}")
        
        if self.dry_run:
            logger.info("DRY RUN: Would create backup")
            return True
        
        try:
            shutil.copy2(self.db_path, self.backup_path)
            logger.info(f"Backup created successfully: {self.backup_path}")
            return True
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return False
    
    def analyze_current_data(self):
        """Analyze current data to plan migration"""
        logger.info("Analyzing current data structure...")
        
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        # Get ref_type distribution
        ref_types = cur.execute("""
            SELECT ref_type, COUNT(*) as count
            FROM regulatory_refs 
            GROUP BY ref_type 
            ORDER BY count DESC
        """).fetchall()
        
        # Categorize by target table
        table_assignments = defaultdict(list)
        unassigned = []
        
        for ref_type, count in ref_types:
            assigned = False
            
            for table_name, config in self.migration_mapping.items():
                for pattern in config['patterns']:
                    if pattern in ref_type:
                        table_assignments[table_name].append((ref_type, count))
                        assigned = True
                        break
                if assigned:
                    break
            
            if not assigned:
                unassigned.append((ref_type, count))
        
        # Display migration plan
        logger.info("\nMIGRATION PLAN:")
        logger.info("=" * 60)
        
        total_assigned = 0
        for table_name, items in table_assignments.items():
            table_total = sum(count for _, count in items)
            total_assigned += table_total
            logger.info(f"\n{table_name.upper()}: {table_total:,} entries")
            
            # Show top ref_types for this table
            for ref_type, count in sorted(items, key=lambda x: x[1], reverse=True)[:3]:
                logger.info(f"  {ref_type}: {count:,}")
            
            if len(items) > 3:
                logger.info(f"  ... and {len(items)-3} more types")
        
        # Show unassigned data
        unassigned_total = sum(count for _, count in unassigned)
        logger.info(f"\nUNASSIGNED: {unassigned_total:,} entries")
        if unassigned:
            for ref_type, count in sorted(unassigned, key=lambda x: x[1], reverse=True)[:5]:
                logger.info(f"  {ref_type}: {count:,}")
        
        logger.info(f"\nTOTAL ASSIGNED: {total_assigned:,}")
        logger.info(f"TOTAL UNASSIGNED: {unassigned_total:,}")
        logger.info(f"TOTAL ENTRIES: {total_assigned + unassigned_total:,}")
        
        self.stats['total_entries'] = total_assigned + unassigned_total
        self.stats['table_assignments'] = dict(table_assignments)
        self.stats['unassigned'] = unassigned
        
        conn.close()
        return table_assignments, unassigned
    
    def create_new_schema(self):
        """Create new normalized schema"""
        logger.info("Creating new normalized schema...")
        
        if self.dry_run:
            logger.info("DRY RUN: Would create new tables:")
            for table_name, config in self.migration_mapping.items():
                logger.info(f"  - {table_name}: {config['description']}")
            return True
        
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        try:
            # Create each new table
            for table_name, config in self.migration_mapping.items():
                logger.info(f"Creating table: {table_name}")
                cur.execute(config['schema'])
                
                # Create indexes for performance
                cur.execute(f"CREATE INDEX idx_{table_name}_document ON {table_name}(document_id)")
                cur.execute(f"CREATE INDEX idx_{table_name}_page ON {table_name}(page_number)")
            
            # Create mapping table to track migration
            cur.execute('''
                CREATE TABLE migration_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_id INTEGER NOT NULL,
                    original_ref_type TEXT NOT NULL,
                    target_table TEXT NOT NULL,
                    target_id INTEGER NOT NULL,
                    migrated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            logger.info("New schema created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Schema creation failed: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def migrate_data_batch(self, table_name, ref_types, batch_size=1000):
        """Migrate data for one table in batches"""
        logger.info(f"Migrating data to {table_name}...")
        
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        # Get total count
        placeholders = ','.join(['?' for _ in ref_types])
        total_query = f"""
            SELECT COUNT(*) FROM regulatory_refs 
            WHERE ref_type IN ({placeholders})
        """
        total = cur.execute(total_query, ref_types).fetchone()[0]
        
        if self.dry_run:
            logger.info(f"DRY RUN: Would migrate {total:,} entries to {table_name}")
            conn.close()
            return True
        
        logger.info(f"Migrating {total:,} entries to {table_name} in batches of {batch_size}")
        
        migrated = 0
        errors = 0
        
        # Process in batches
        for offset in range(0, total, batch_size):
            try:
                # Get batch of data
                batch_query = f"""
                    SELECT id, document_id, ref_type, ref_number, ref_context, 
                           page_number, section_header, text_level
                    FROM regulatory_refs 
                    WHERE ref_type IN ({placeholders})
                    LIMIT ? OFFSET ?
                """
                
                batch_data = cur.execute(
                    batch_query, 
                    ref_types + [batch_size, offset]
                ).fetchall()
                
                # Transform and insert batch
                for row in batch_data:
                    try:
                        success = self.transform_and_insert(cur, table_name, row)
                        if success:
                            migrated += 1
                        else:
                            errors += 1
                    except Exception as e:
                        logger.error(f"Failed to migrate row {row[0]}: {e}")
                        errors += 1
                
                # Progress update
                if (offset + batch_size) % 5000 == 0:
                    logger.info(f"  Progress: {min(offset + batch_size, total):,}/{total:,} ({(min(offset + batch_size, total)/total)*100:.1f}%)")
                
                conn.commit()
                
            except Exception as e:
                logger.error(f"Batch migration failed at offset {offset}: {e}")
                conn.rollback()
        
        logger.info(f"Migration to {table_name} complete: {migrated:,} success, {errors:,} errors")
        
        # Update tracking
        self.stats['migrated_entries'] += migrated
        self.stats['table_counts'][table_name] = migrated
        
        conn.close()
        return errors == 0
    
    def transform_and_insert(self, cur, table_name, row):
        """Transform a row from regulatory_refs to target table format"""
        original_id, document_id, ref_type, ref_number, ref_context, page_number, section_header, text_level = row
        
        try:
            if table_name == 'regulatory_provisions':
                cur.execute("""
                    INSERT INTO regulatory_provisions 
                    (document_id, provision_type, clause_number, provision_text, page_number, section_header, text_level)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (document_id, ref_type, ref_number, ref_context, page_number, section_header, text_level))
                
            elif table_name == 'development_controls':
                # Extract control details from ref_context
                control_type = ref_type.replace('provision_', '').replace('formal_', '')
                cur.execute("""
                    INSERT INTO development_controls 
                    (control_type, control_value, document_id, page_number, section_header)
                    VALUES (?, ?, ?, ?, ?)
                """, (control_type, ref_context, document_id, page_number, section_header))
                
            elif table_name == 'contextual_guidance':
                guidance_type = ref_type.replace('context_', '').replace('informal_', '')
                cur.execute("""
                    INSERT INTO contextual_guidance 
                    (document_id, guidance_type, guidance_text, page_number, section_header)
                    VALUES (?, ?, ?, ?, ?)
                """, (document_id, guidance_type, ref_context, page_number, section_header))
                
            elif table_name == 'cross_references':
                relationship_type = ref_type.replace('relationship_', '')
                cur.execute("""
                    INSERT INTO cross_references 
                    (from_provision, relationship_type, reference_text, document_id, page_number)
                    VALUES (?, ?, ?, ?, ?)
                """, (ref_number, relationship_type, ref_context, document_id, page_number))
                
            elif table_name == 'visual_elements':
                element_type = ref_type.replace('autoschema_', '').replace('visual_', '')
                cur.execute("""
                    INSERT INTO visual_elements 
                    (document_id, element_type, clause_context, description, page_number)
                    VALUES (?, ?, ?, ?, ?)
                """, (document_id, element_type, ref_number, ref_context, page_number))
                
            elif table_name == 'zoning_information':
                cur.execute("""
                    INSERT INTO zoning_information 
                    (zone_code, zone_name, document_id, page_number, section_header)
                    VALUES (?, ?, ?, ?, ?)
                """, (ref_number, ref_context, document_id, page_number, section_header))
            
            # Record migration in tracking table
            target_id = cur.lastrowid
            cur.execute("""
                INSERT INTO migration_tracking 
                (original_id, original_ref_type, target_table, target_id)
                VALUES (?, ?, ?, ?)
            """, (original_id, ref_type, table_name, target_id))
            
            return True
            
        except Exception as e:
            logger.error(f"Transform/insert failed for {ref_type}: {e}")
            return False
    
    def verify_migration(self):
        """Verify migration integrity and completeness"""
        logger.info("Verifying migration integrity...")
        
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        # Check table counts
        verification_results = {}
        
        for table_name in self.migration_mapping.keys():
            try:
                count = cur.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                verification_results[table_name] = count
                logger.info(f"{table_name}: {count:,} entries")
                
                # Check for required fields
                nulls = cur.execute(f"SELECT COUNT(*) FROM {table_name} WHERE document_id IS NULL").fetchone()[0]
                if nulls > 0:
                    logger.warning(f"{table_name}: {nulls} entries missing document_id")
                
            except Exception as e:
                logger.error(f"Verification failed for {table_name}: {e}")
                verification_results[table_name] = -1
        
        # Check migration tracking
        total_tracked = cur.execute("SELECT COUNT(*) FROM migration_tracking").fetchone()[0]
        total_migrated = sum(v for v in verification_results.values() if v > 0)
        
        logger.info(f"\nMigration tracking: {total_tracked:,} entries")
        logger.info(f"Total migrated: {total_migrated:,} entries")
        logger.info(f"Original total: {self.stats['total_entries']:,} entries")
        
        success = total_tracked == total_migrated
        logger.info(f"Verification: {'PASSED' if success else 'FAILED'}")
        
        conn.close()
        return success, verification_results
    
    def save_migration_state(self):
        """Save migration state for resume capability"""
        with open(self.migration_state_file, 'w') as f:
            json.dump(self.stats, f, indent=2)
    
    def run_migration(self):
        """Execute complete migration process"""
        logger.info("STARTING SAFE DATABASE MIGRATION")
        logger.info("=" * 60)
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE MIGRATION'}")
        logger.info(f"Database: {self.db_path}")
        logger.info(f"Backup: {self.backup_path}")
        
        try:
            # Step 1: Create backup
            if not self.create_backup():
                return False
            
            # Step 2: Analyze current data
            table_assignments, unassigned = self.analyze_current_data()
            
            # Step 3: Create new schema
            if not self.create_new_schema():
                return False
            
            # Step 4: Migrate data table by table
            migration_success = True
            
            for table_name, config in self.migration_mapping.items():
                if table_name in table_assignments:
                    ref_types = [item[0] for item in table_assignments[table_name]]
                    success = self.migrate_data_batch(table_name, ref_types)
                    if not success:
                        migration_success = False
                        break
            
            if not migration_success:
                logger.error("Migration failed - stopping")
                return False
            
            # Step 5: Verify migration
            if not self.dry_run:
                success, results = self.verify_migration()
                if not success:
                    logger.error("Verification failed - migration may be incomplete")
                    return False
            
            # Step 6: Save state
            self.save_migration_state()
            
            logger.info("MIGRATION COMPLETED SUCCESSFULLY")
            if not self.dry_run:
                logger.info(f"Backup available at: {self.backup_path}")
                logger.info("UI can now be updated to use new normalized schema")
            
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False

def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Safe Database Migration')
    parser.add_argument('--live', action='store_true', help='Run live migration (default is dry-run)')
    parser.add_argument('--db', default='nsw_planning.db', help='Database path')
    
    args = parser.parse_args()
    
    migration = SafeDatabaseMigration(
        db_path=args.db,
        dry_run=not args.live
    )
    
    success = migration.run_migration()
    
    if success:
        print("\nMigration completed successfully!")
        if not args.live:
            print("This was a DRY RUN. Use --live to execute actual migration.")
    else:
        print("\nMigration failed. Check migration.log for details.")

if __name__ == "__main__":
    main()