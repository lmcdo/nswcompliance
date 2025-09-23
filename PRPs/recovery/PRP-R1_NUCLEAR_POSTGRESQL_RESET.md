# PRP-R1: Nuclear PostgreSQL Reset

## Objective
Complete PostgreSQL instance reset to recover from corruption/deadlock state

## Prerequisites
- Administrator access
- PostgreSQL 17 installed
- Backup of critical data

## Implementation Steps

### Step 1: Service Termination
```bash
# Stop PostgreSQL service completely
net stop postgresql-x64-17

# Kill any remaining processes
taskkill /F /IM postgres.exe
```

### Step 2: Lock File Cleanup
```bash
# Remove lock files and shared memory
del "C:\Program Files\PostgreSQL\17\data\postmaster.pid"
del "C:\Program Files\PostgreSQL\17\data\postgresql.auto.conf.tmp"
```

### Step 3: Service Restart
```bash
# Start with fresh shared memory
net start postgresql-x64-17
```

## Verification
- All postgres.exe processes terminated
- Lock files removed
- Service restarted successfully
- Connection test passes: `psql -U postgres -c "SELECT 1;"`

## Completion Gate
- PostgreSQL responds to queries within 5 seconds
- No error messages in log
- Marker file: `recovery_checkpoints/R1_complete.marker`