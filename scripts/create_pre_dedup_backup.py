#!/usr/bin/env python3
"""Create backup before deduplication."""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import subprocess
from datetime import datetime
import os

TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
BACKUP_DIR = 'backups'
BACKUP_FILE = f'{BACKUP_DIR}/regulatory_provisions_pre_dedup_{TIMESTAMP}.sql'

print('=' * 70)
print('CREATING PRE-DEDUPLICATION BACKUP')
print('=' * 70)
print()
print(f'Backup file: {BACKUP_FILE}')
print()
print('This will take a few minutes...')
print()

# Set password in environment
env = os.environ.copy()
env['PGPASSWORD'] = 'eDDIYq8ottiaO9ll'

# Run pg_dump
result = subprocess.run([
    'pg_dump',
    '--host=aws-1-ap-southeast-2.pooler.supabase.com',
    '--port=5432',
    '--username=postgres.llzdrxywpziewrzudwhj',
    '--dbname=postgres',
    '--table=regulatory_provisions',
    '--no-owner',
    '--no-acl',
    '--format=plain',
    f'--file={BACKUP_FILE}'
], env=env, capture_output=True, text=True)

if result.returncode != 0:
    print('❌ ERROR creating backup:')
    print(result.stderr)
    sys.exit(1)

# Check file size
file_size = os.path.getsize(BACKUP_FILE)
print()
print(f'✅ Backup created successfully!')
print()
print(f'File: {BACKUP_FILE}')
print(f'Size: {file_size / 1024 / 1024:.2f} MB')
print()
print('You can now proceed with deduplication.')
