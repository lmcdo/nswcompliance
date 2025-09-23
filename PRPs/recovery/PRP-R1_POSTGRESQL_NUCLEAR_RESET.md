# PRP-R1: PostgreSQL Nuclear Reset

## Objective
Complete PostgreSQL instance reset to recover from corruption/deadlock state

## Prerequisites
- Administrator access to Windows system
- PostgreSQL 17 installation path confirmed
- All database work saved/backed up

## Technical Specification

### Phase 1: Service Termination
```powershell
# Stop PostgreSQL Windows service
net stop postgresql-x64-17

# Wait for graceful shutdown (10 seconds)
Start-Sleep -Seconds 10

# Force kill any remaining processes
taskkill /F /IM postgres.exe
```

### Phase 2: Lock File Cleanup
```powershell
# Remove PostgreSQL lock files
Remove-Item "C:\Program Files\PostgreSQL\17\data\postmaster.pid" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\Program Files\PostgreSQL\17\data\postmaster.opts" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\Program Files\PostgreSQL\17\data\postgresql.auto.conf.tmp" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\Program Files\PostgreSQL\17\data\global\pg_internal.init" -Force -ErrorAction SilentlyContinue
```

### Phase 3: Shared Memory Reset
```powershell
# Clear Windows shared memory segments
# PostgreSQL uses Windows shared memory for inter-process communication
ipconfig /release
ipconfig /flushdns
net stop "Windows Search"
net start "Windows Search"
```

### Phase 4: Service Restart
```powershell
# Start PostgreSQL with fresh state
net start postgresql-x64-17

# Verify service is running
sc query postgresql-x64-17

# Test basic connectivity
"C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -c "SELECT 1;"
```

## Autocomplete Verification

### Success Criteria
- ✅ All postgres.exe processes terminated
- ✅ Lock files removed
- ✅ Service restarted successfully
- ✅ Basic query responds within 5 seconds
- ✅ No error messages in PostgreSQL log

### Failure Recovery
- If service won't stop: Use Windows Services Manager
- If processes persist: Restart Windows
- If connectivity fails: Check Windows Firewall
- If shared memory issues: Run Windows Memory Diagnostic

## Completion Marker
Creates: `recovery_checkpoints/R1_nuclear_reset_complete.marker`