# PRP-R2: Database Recreation

## Objective
Drop corrupted database and recreate fresh instance

## Prerequisites
- PRP-R1 completed (PostgreSQL reset)
- PostgreSQL service running
- psql accessible

## Implementation Steps

### Step 1: Drop Corrupted Database
```bash
# Drop and recreate the corrupted database
psql -U postgres -c "DROP DATABASE IF EXISTS nsw_planning;"
```

### Step 2: Create Fresh Database
```bash
psql -U postgres -c "CREATE DATABASE nsw_planning;"
```

### Step 3: Verify Creation
```bash
psql -U postgres -d nsw_planning -c "SELECT version();"
```

## Verification
- Database nsw_planning exists
- Can connect to database
- No errors during creation
- Empty database (0 tables)

## Completion Gate
- Database created successfully
- Connection test passes
- Marker file: `recovery_checkpoints/R2_complete.marker`