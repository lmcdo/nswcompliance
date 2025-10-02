#!/usr/bin/env python3
"""
Create database backup before commit
PRP-A1 Safety Compliant
"""
import subprocess
import datetime
import os
import sys

def create_backup():
    """Create PostgreSQL database backup"""

    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = 'backups'
    os.makedirs(backup_dir, exist_ok=True)

    backup_file = os.path.join(backup_dir, f'nsw_planning_backup_{timestamp}.sql')

    print(f"Creating database backup: {backup_file}")

    cmd = [
        'pg_dump',
        '--host=127.0.0.1',
        '--port=5432',
        '--username=postgres',
        '--dbname=nsw_planning',
        '--no-password',
        f'--file={backup_file}'
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            size_mb = os.path.getsize(backup_file) / (1024 * 1024)
            print(f'✅ Database backup created: {backup_file}')
            print(f'   Size: {size_mb:.2f} MB')
            return True
        else:
            print(f'❌ Backup failed: {result.stderr}')
            return False
    except Exception as e:
        print(f'❌ Backup error: {str(e)}')
        return False

if __name__ == '__main__':
    success = create_backup()
    sys.exit(0 if success else 1)