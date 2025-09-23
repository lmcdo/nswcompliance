# PRP-R3: Schema Migration from SQLite to PostgreSQL

## Objective
Migrate schema and data from SQLite backup to fresh PostgreSQL database

## Prerequisites
- PRP-R2 completed (fresh database created)
- SQLite database available: `nsw_planning.db`
- PostgreSQL database empty and ready

## Implementation Steps

### Step 1: Extract Schema from SQLite
- Read all table definitions from SQLite
- Convert SQLite types to PostgreSQL types
- Handle constraints and indexes

### Step 2: Create PostgreSQL Schema
- Create all tables with proper types
- Add primary keys and foreign keys
- Create sequences for auto-increment fields

### Step 3: Migrate Data Table by Table
- Export data from SQLite tables
- Transform data types as needed
- Import into PostgreSQL with validation

### Step 4: Create Indexes
- Add indexes for performance
- Create unique constraints
- Add check constraints

### Step 5: Validate Data Integrity
- Row counts match between databases
- Foreign key relationships intact
- No data corruption

## Verification
- All 31 tables created
- 22,105 regulatory_provisions migrated
- All indexes created
- Foreign keys validated

## Completion Gate
- Data migration 100% complete
- Integrity checks pass
- Marker file: `recovery_checkpoints/R3_complete.marker`