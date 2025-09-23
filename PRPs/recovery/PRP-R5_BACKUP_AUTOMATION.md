# PRP-R5: Backup Automation

## Objective
Implement automatic database backup system to prevent future data loss

## Prerequisites
- PRP-R4 completed (database fully operational)
- PostgreSQL pg_dump available
- Sufficient disk space for backups

## Implementation Steps

### Step 1: Create Backup Script
```bash
# backup_database.bat
@echo off
set BACKUP_DIR=C:\backups\postgresql
set TIMESTAMP=%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set BACKUP_FILE=%BACKUP_DIR%\nsw_planning_%TIMESTAMP%.sql

pg_dump -U postgres -d nsw_planning > %BACKUP_FILE%
echo Backup created: %BACKUP_FILE%
```

### Step 2: Schedule Daily Backups
```bash
# Windows Task Scheduler
schtasks /create /tn "PostgreSQL Daily Backup" /tr "C:\scripts\backup_database.bat" /sc daily /st 02:00
```

### Step 3: Pre-Commit Hook
```bash
# .git/hooks/pre-commit
#!/bin/bash
echo "Creating database backup before commit..."
pg_dump -U postgres -d nsw_planning > backups/pre_commit_$(date +%Y%m%d_%H%M%S).sql
```

### Step 4: Backup Rotation
- Keep daily backups for 7 days
- Keep weekly backups for 4 weeks
- Keep monthly backups for 3 months

### Step 5: Backup Verification
- Test restore process monthly
- Verify backup integrity
- Monitor backup sizes

## Verification
- Backup script creates valid dumps
- Scheduled task runs successfully
- Pre-commit hook triggers
- Old backups auto-deleted

## Completion Gate
- Automated backups running
- Retention policy active
- Marker file: `recovery_checkpoints/R5_complete.marker`