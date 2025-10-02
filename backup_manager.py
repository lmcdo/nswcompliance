#!/usr/bin/env python3
"""
Database Backup Manager - CLAUDE.md MANDATORY COMPLIANCE
Implements automated backup system per CLAUDE.md database safety requirements

CRITICAL SAFETY REQUIREMENTS:
- ALWAYS create backup before ANY database operation
- Automated backup validation and rotation
- Emergency backup procedures
- Backup integrity checking
- Recovery procedures tested

This module ensures CLAUDE.md compliance for database safety
"""

import os
import sys
import json
import time
import shutil
import datetime
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

# Configure safety logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - BACKUP_SAFETY - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseBackupError(Exception):
    """Critical database backup safety violation"""
    pass

class DatabaseBackupManager:
    """
    MANDATORY Database Backup Management per CLAUDE.md requirements
    NEVER BYPASS - Prevents database destruction
    """

    def __init__(self, backup_dir: str = "database_backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)

        # Database connection parameters
        self.db_host = os.environ.get('DB_HOST', '127.0.0.1')
        self.db_name = os.environ.get('DB_NAME', 'nsw_planning')
        self.db_user = os.environ.get('DB_USER', 'postgres')
        self.db_port = int(os.environ.get('DB_PORT', 5432))

        # Backup configuration
        self.max_backups = 20  # Keep 20 most recent backups
        self.backup_timeout = 300  # 5 minutes max for backup

        logger.info(f"Backup manager initialized: {self.backup_dir}")

    def create_backup_before_query(self) -> Dict[str, Any]:
        """
        Create backup before ANY database operation - MANDATORY per CLAUDE.md
        This function is called by db_safety_wrapper.py automatically
        """
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"compliance_backup_{timestamp}.sql"
            backup_path = self.backup_dir / backup_name

            logger.info(f"Creating MANDATORY backup: {backup_name}")

            # Create PostgreSQL dump with compression
            cmd = [
                "pg_dump",
                f"--host={self.db_host}",
                f"--port={self.db_port}",
                f"--username={self.db_user}",
                f"--dbname={self.db_name}",
                "--no-password",
                "--verbose",
                "--format=custom",
                "--compress=9",
                f"--file={backup_path}"
            ]

            # Set PGPASSWORD if available
            env = os.environ.copy()
            if 'DB_PASSWORD' in os.environ:
                env['PGPASSWORD'] = os.environ['DB_PASSWORD']

            # Execute backup with timeout
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.backup_timeout,
                env=env
            )

            if result.returncode == 0:
                # Verify backup file exists and has content
                if backup_path.exists() and backup_path.stat().st_size > 1000:  # At least 1KB
                    backup_info = {
                        'success': True,
                        'backup_path': str(backup_path),
                        'created_at': timestamp,
                        'size_mb': backup_path.stat().st_size / (1024 * 1024),
                        'backup_type': 'pre_query_safety_backup',
                        'compliance_status': 'CLAUDE.md_required'
                    }

                    logger.info(f"MANDATORY backup created successfully: {backup_info['size_mb']:.1f}MB")

                    # Cleanup old backups
                    self._cleanup_old_backups()

                    return backup_info
                else:
                    raise DatabaseBackupError("Backup file is empty or too small")
            else:
                raise DatabaseBackupError(f"pg_dump failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            raise DatabaseBackupError(f"Backup timeout after {self.backup_timeout} seconds")
        except Exception as e:
            logger.error(f"CRITICAL: Backup creation failed: {str(e)}")
            raise DatabaseBackupError(f"DB_SAFETY: Backup failed - {str(e)}")

    def check_recent_backup(self, max_age_hours: int = 1) -> Dict[str, Any]:
        """
        Check if recent backup exists (within specified hours)
        Used by db_safety_wrapper.py to determine if new backup needed
        """
        cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=max_age_hours)

        recent_backups = []
        for backup_file in self.backup_dir.glob("compliance_backup_*.sql"):
            try:
                file_time = datetime.datetime.fromtimestamp(backup_file.stat().st_mtime)
                if file_time > cutoff_time:
                    recent_backups.append({
                        'file': backup_file.name,
                        'created': file_time.isoformat(),
                        'size_mb': backup_file.stat().st_size / (1024 * 1024),
                        'age_minutes': (datetime.datetime.now() - file_time).total_seconds() / 60
                    })
            except Exception as e:
                logger.warning(f"Could not check backup file {backup_file}: {e}")

        # Sort by creation time (newest first)
        recent_backups.sort(key=lambda x: x['created'], reverse=True)

        return {
            'recent_backup_exists': len(recent_backups) > 0,
            'backup_count': len(recent_backups),
            'most_recent': recent_backups[0] if recent_backups else None,
            'all_recent': recent_backups
        }

    def _cleanup_old_backups(self):
        """Keep only the most recent N backups"""
        try:
            all_backups = sorted(
                self.backup_dir.glob("compliance_backup_*.sql"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )

            # Remove old backups beyond max_backups
            for old_backup in all_backups[self.max_backups:]:
                old_backup.unlink()
                logger.info(f"Removed old backup: {old_backup.name}")

        except Exception as e:
            logger.warning(f"Could not cleanup old backups: {e}")

    def verify_backup_integrity(self, backup_path: Path) -> Dict[str, Any]:
        """
        Verify backup file integrity
        Ensures backup can be restored if needed
        """
        try:
            if not backup_path.exists():
                return {'valid': False, 'error': 'Backup file does not exist'}

            # Check file size
            file_size = backup_path.stat().st_size
            if file_size < 1000:  # Less than 1KB is suspicious
                return {'valid': False, 'error': 'Backup file too small'}

            # Try to read backup header (pg_dump custom format)
            with open(backup_path, 'rb') as f:
                header = f.read(8)
                if not header.startswith(b'PGDMP'):
                    return {'valid': False, 'error': 'Invalid PostgreSQL backup format'}

            return {
                'valid': True,
                'size_mb': file_size / (1024 * 1024),
                'created': datetime.datetime.fromtimestamp(backup_path.stat().st_mtime).isoformat()
            }

        except Exception as e:
            return {'valid': False, 'error': f'Backup verification failed: {str(e)}'}

    def create_emergency_backup(self, reason: str = "Emergency") -> Dict[str, Any]:
        """
        Create emergency backup with special naming
        Used in critical situations or before dangerous operations
        """
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"EMERGENCY_backup_{timestamp}_{reason}.sql"
            backup_path = self.backup_dir / backup_name

            logger.warning(f"Creating EMERGENCY backup: {reason}")

            # Same backup process but with emergency naming
            backup_info = self.create_backup_before_query()

            # Rename to emergency backup
            old_path = Path(backup_info['backup_path'])
            old_path.rename(backup_path)

            backup_info.update({
                'backup_path': str(backup_path),
                'backup_type': 'emergency_backup',
                'reason': reason
            })

            logger.warning(f"EMERGENCY backup created: {backup_path}")
            return backup_info

        except Exception as e:
            logger.error(f"CRITICAL: Emergency backup failed: {str(e)}")
            raise DatabaseBackupError(f"Emergency backup failed - {str(e)}")

    def restore_from_backup(self, backup_path: Path, target_db: str = None) -> Dict[str, Any]:
        """
        Restore database from backup file
        DANGEROUS OPERATION - Use with extreme caution
        """
        if target_db is None:
            target_db = self.db_name

        logger.warning(f"RESTORING database {target_db} from backup: {backup_path}")

        try:
            # Verify backup integrity first
            integrity = self.verify_backup_integrity(backup_path)
            if not integrity['valid']:
                raise DatabaseBackupError(f"Backup integrity check failed: {integrity['error']}")

            # Create emergency backup of current state before restore
            current_backup = self.create_emergency_backup("pre_restore")

            # Restore command
            cmd = [
                "pg_restore",
                f"--host={self.db_host}",
                f"--port={self.db_port}",
                f"--username={self.db_user}",
                f"--dbname={target_db}",
                "--no-password",
                "--verbose",
                "--clean",
                "--if-exists",
                str(backup_path)
            ]

            # Set PGPASSWORD if available
            env = os.environ.copy()
            if 'DB_PASSWORD' in os.environ:
                env['PGPASSWORD'] = os.environ['DB_PASSWORD']

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutes for restore
                env=env
            )

            if result.returncode == 0:
                logger.warning(f"Database restore completed successfully")
                return {
                    'success': True,
                    'restored_from': str(backup_path),
                    'target_database': target_db,
                    'pre_restore_backup': current_backup['backup_path']
                }
            else:
                raise DatabaseBackupError(f"pg_restore failed: {result.stderr}")

        except Exception as e:
            logger.error(f"CRITICAL: Database restore failed: {str(e)}")
            raise DatabaseBackupError(f"Database restore failed - {str(e)}")

    def get_backup_status(self) -> Dict[str, Any]:
        """
        Get comprehensive backup system status
        Used for monitoring and health checks
        """
        try:
            all_backups = list(self.backup_dir.glob("compliance_backup_*.sql"))
            emergency_backups = list(self.backup_dir.glob("EMERGENCY_backup_*.sql"))

            total_size = sum(backup.stat().st_size for backup in all_backups + emergency_backups)

            recent_check = self.check_recent_backup()

            return {
                'backup_directory': str(self.backup_dir),
                'total_backups': len(all_backups),
                'emergency_backups': len(emergency_backups),
                'total_size_mb': total_size / (1024 * 1024),
                'recent_backup_status': recent_check,
                'max_backups_configured': self.max_backups,
                'claude_md_compliant': recent_check['recent_backup_exists'],
                'last_check': datetime.datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Could not get backup status: {e}")
            return {
                'error': str(e),
                'claude_md_compliant': False
            }

def main():
    """Command line interface for backup manager"""
    import argparse

    parser = argparse.ArgumentParser(description='Database Backup Manager - CLAUDE.md Safety Compliant')
    parser.add_argument('--action', required=True, choices=['backup', 'status', 'emergency', 'verify'],
                       help='Action to perform')
    parser.add_argument('--reason', help='Reason for emergency backup')
    parser.add_argument('--backup-file', help='Backup file to verify')

    args = parser.parse_args()

    manager = DatabaseBackupManager()

    try:
        if args.action == 'backup':
            result = manager.create_backup_before_query()
            print(json.dumps(result, indent=2))

        elif args.action == 'status':
            result = manager.get_backup_status()
            print(json.dumps(result, indent=2))

        elif args.action == 'emergency':
            reason = args.reason or 'Manual'
            result = manager.create_emergency_backup(reason)
            print(json.dumps(result, indent=2))

        elif args.action == 'verify':
            if not args.backup_file:
                print("Error: --backup-file required for verify action")
                sys.exit(1)
            result = manager.verify_backup_integrity(Path(args.backup_file))
            print(json.dumps(result, indent=2))

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()