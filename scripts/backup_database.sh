#!/bin/bash
# Emergency Database Backup - MANDATORY before any database changes
# NEVER REMOVE THIS SCRIPT

echo "🚨 CREATING EMERGENCY DATABASE BACKUP 🚨"
echo "========================================"

# Generate timestamp
timestamp=$(date +"%Y%m%d_%H%M%S")
backup_dir="backups"
backup_file="${backup_dir}/emergency_backup_${timestamp}.sql"

# Create backup directory if it doesn't exist
mkdir -p "$backup_dir"

echo "Creating backup: $backup_file"

# Create backup with timeout
timeout 300 "C:\Program Files\PostgreSQL\17\bin\pg_dump.exe" \
    -U postgres \
    -h 127.0.0.1 \
    -d nsw_planning \
    --no-password \
    > "$backup_file" 2>/dev/null

if [ $? -eq 0 ] && [ -s "$backup_file" ]; then
    file_size=$(stat -c%s "$backup_file" 2>/dev/null || wc -c < "$backup_file")
    echo "✅ Backup created successfully ($file_size bytes)"

    # Keep only last 5 backups to save space
    cd "$backup_dir"
    ls -t emergency_backup_*.sql | tail -n +6 | xargs rm -f 2>/dev/null || true
    cd ..

    echo "✅ Old backups cleaned up"
    echo "🟢 EMERGENCY BACKUP COMPLETE"
    echo "========================================"
    exit 0
else
    echo "❌ BACKUP FAILED - ABORTING ALL DATABASE OPERATIONS"
    echo "Cannot proceed without backup"
    echo "========================================"
    exit 1
fi