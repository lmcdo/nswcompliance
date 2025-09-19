#!/usr/bin/env python3
"""
Migration Rollback Script
========================

Safely rollback database migration if issues are found.
Can restore from backup or selectively remove new tables.
"""

import sqlite3
import os
import shutil
import glob
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MigrationRollback:
    """Handle migration rollback scenarios"""
    
    def __init__(self, db_path='nsw_planning.db'):
        self.db_path = db_path
        self.new_tables = [
            'regulatory_provisions',
            'development_controls', 
            'contextual_guidance',
            'cross_references',
            'visual_elements',
            'zoning_information',
            'migration_tracking'
        ]
    
    def list_backups(self):
        """List available backups"""
        pattern = f"{self.db_path}.backup_*"
        backups = glob.glob(pattern)
        backups.sort(reverse=True)  # Most recent first
        
        logger.info("Available backups:")
        for i, backup in enumerate(backups):
            stat = os.stat(backup)
            size_mb = stat.st_size / (1024*1024)
            modified = datetime.fromtimestamp(stat.st_mtime)
            logger.info(f"  {i+1}. {backup} ({size_mb:.1f}MB, {modified})")
        
        return backups
    
    def restore_from_backup(self, backup_path=None):
        """Restore database from backup"""
        if backup_path is None:
            backups = self.list_backups()
            if not backups:
                logger.error("No backups found")
                return False
            backup_path = backups[0]  # Use most recent
        
        if not os.path.exists(backup_path):
            logger.error(f"Backup not found: {backup_path}")
            return False
        
        logger.info(f"Restoring from backup: {backup_path}")
        
        try:
            # Create current backup before restore
            current_backup = f"{self.db_path}.pre_rollback_{int(datetime.now().timestamp())}"
            shutil.copy2(self.db_path, current_backup)
            logger.info(f"Current state backed up to: {current_backup}")
            
            # Restore
            shutil.copy2(backup_path, self.db_path)
            logger.info("Database restored successfully")
            return True
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False
    
    def remove_new_tables_only(self):
        """Remove only new tables, keep original regulatory_refs"""
        logger.info("Removing new migration tables only...")
        
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        try:
            for table in self.new_tables:
                try:
                    # Check if table exists
                    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                    if cur.fetchone():
                        cur.execute(f"DROP TABLE {table}")
                        logger.info(f"Dropped table: {table}")
                    else:
                        logger.info(f"Table not found: {table}")
                except Exception as e:
                    logger.warning(f"Could not drop {table}: {e}")
            
            conn.commit()
            logger.info("New tables removed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove new tables: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def verify_original_data(self):
        """Verify original regulatory_refs table is intact"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        try:
            # Check if regulatory_refs exists
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='regulatory_refs'")
            if not cur.fetchone():
                logger.error("Original regulatory_refs table missing!")
                return False
            
            # Check record count
            count = cur.execute("SELECT COUNT(*) FROM regulatory_refs").fetchone()[0]
            logger.info(f"regulatory_refs contains {count:,} records")
            
            # Check structure
            columns = cur.execute("PRAGMA table_info(regulatory_refs)").fetchall()
            column_names = [col[1] for col in columns]
            expected_columns = ['id', 'document_id', 'ref_type', 'ref_number', 'ref_context', 'page_number', 'section_header', 'text_level']
            
            missing = set(expected_columns) - set(column_names)
            if missing:
                logger.warning(f"Missing columns: {missing}")
            else:
                logger.info("All expected columns present")
            
            return True
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return False
        finally:
            conn.close()

def main():
    """Main rollback interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migration Rollback')
    parser.add_argument('--action', choices=['list', 'restore', 'clean', 'verify'], 
                       default='list', help='Rollback action')
    parser.add_argument('--backup', help='Specific backup file to restore from')
    parser.add_argument('--confirm', action='store_true', help='Confirm destructive actions')
    
    args = parser.parse_args()
    
    rollback = MigrationRollback()
    
    if args.action == 'list':
        rollback.list_backups()
        
    elif args.action == 'restore':
        if not args.confirm:
            print("This will restore database from backup, losing current data.")
            print("Use --confirm to proceed.")
            return
        
        success = rollback.restore_from_backup(args.backup)
        if success:
            rollback.verify_original_data()
            
    elif args.action == 'clean':
        if not args.confirm:
            print("This will remove new migration tables.")
            print("Use --confirm to proceed.")
            return
            
        rollback.remove_new_tables_only()
        rollback.verify_original_data()
        
    elif args.action == 'verify':
        rollback.verify_original_data()

if __name__ == "__main__":
    main()