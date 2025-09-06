#!/bin/bash
# PRP-D Rollback Script
# Safe rollback of database factorization if issues occur

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    local color=$1
    local message=$2
    echo -e "${color}$message${NC}"
}

print_status "$RED" "=========================================="
print_status "$RED" "🚨 PRP-D ROLLBACK PROCEDURE"
print_status "$RED" "=========================================="

print_status "$YELLOW" "This will:"
print_status "$YELLOW" "1. Restore database from backup"
print_status "$YELLOW" "2. Remove factorized tables"
print_status "$YELLOW" "3. Clear migration markers"
print_status "$YELLOW" "4. Reset to pre-PRP-D state"

# Check for backup files
LATEST_BACKUP=$(ls -1t nsw_planning_backup_*.db 2>/dev/null | head -1)

if [ -z "$LATEST_BACKUP" ]; then
    print_status "$RED" "❌ No backup files found!"
    print_status "$RED" "Cannot safely rollback without backup"
    print_status "$YELLOW" "Available files:"
    ls -la nsw_planning*.db
    exit 1
fi

print_status "$BLUE" "Latest backup found: $LATEST_BACKUP"

# Ask for confirmation
read -p "Are you sure you want to rollback PRP-D? [y/N]: " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_status "$YELLOW" "Rollback cancelled"
    exit 0
fi

print_status "$YELLOW" "\n🔄 Starting rollback procedure..."

# Create rollback log
ROLLBACK_LOG="prp_d_rollback_$(date +%Y%m%d_%H%M%S).log"
echo "PRP-D Rollback Log - $(date)" > "$ROLLBACK_LOG"

# Backup current state before rollback (in case we need it)
CURRENT_BACKUP="nsw_planning_pre_rollback_$(date +%Y%m%d_%H%M%S).db"
cp nsw_planning.db "$CURRENT_BACKUP"
print_status "$GREEN" "✅ Current state backed up to: $CURRENT_BACKUP"
echo "Current state backed up to: $CURRENT_BACKUP" >> "$ROLLBACK_LOG"

# Restore from backup
print_status "$YELLOW" "Restoring database from backup..."
cp "$LATEST_BACKUP" nsw_planning.db
if [ $? -eq 0 ]; then
    print_status "$GREEN" "✅ Database restored from: $LATEST_BACKUP"
    echo "Database restored from: $LATEST_BACKUP" >> "$ROLLBACK_LOG"
else
    print_status "$RED" "❌ Failed to restore database!"
    echo "FAILED: Database restore from $LATEST_BACKUP" >> "$ROLLBACK_LOG"
    exit 1
fi

# Verify restoration
./venv_linux/Scripts/python.exe -c "
import sqlite3
conn = sqlite3.connect('nsw_planning.db')
cursor = conn.cursor()

print('POST-ROLLBACK DATABASE STATE:')
tables = ['regulatory_refs', 'regulatory_provisions', 'kg_entities', 'kg_relationships']
for table in tables:
    try:
        cursor.execute(f'SELECT COUNT(*) FROM {table}')
        count = cursor.fetchone()[0]
        print(f'  {table}: {count:,}')
    except:
        print(f'  {table}: TABLE NOT FOUND')

conn.close()
" >> "$ROLLBACK_LOG" 2>&1

# Remove factorized tables that shouldn't exist in restored state
print_status "$YELLOW" "Cleaning up factorized tables..."
./venv_linux/Scripts/python.exe -c "
import sqlite3
conn = sqlite3.connect('nsw_planning.db')
cursor = conn.cursor()

# Drop factorized tables that may have been created
factorized_tables = [
    'regulatory_provisions_clean',
    'contextual_guidance_real', 
    'visual_elements_real',
    'regulatory_refs_core'
]

dropped = []
for table in factorized_tables:
    try:
        cursor.execute(f'DROP TABLE IF EXISTS {table}')
        dropped.append(table)
    except Exception as e:
        print(f'Error dropping {table}: {e}')

conn.commit()
conn.close()

if dropped:
    print(f'Dropped factorized tables: {dropped}')
else:
    print('No factorized tables to remove')
" >> "$ROLLBACK_LOG" 2>&1

# Clear migration markers
print_status "$YELLOW" "Clearing migration markers..."
if [ -d "migration_markers" ]; then
    mv migration_markers "migration_markers_rolled_back_$(date +%Y%m%d_%H%M%S)"
    print_status "$GREEN" "✅ Migration markers archived"
    echo "Migration markers archived" >> "$ROLLBACK_LOG"
fi

# Clear script files
if [ -d "prp_scripts" ]; then
    mv prp_scripts "prp_scripts_rolled_back_$(date +%Y%m%d_%H%M%S)"
    print_status "$GREEN" "✅ PRP scripts archived"
    echo "PRP scripts archived" >> "$ROLLBACK_LOG"
fi

# Final verification
print_status "$BLUE" "\n🔍 ROLLBACK VERIFICATION:"
./venv_linux/Scripts/python.exe -c "
import sqlite3
conn = sqlite3.connect('nsw_planning.db')
cursor = conn.cursor()

# Check if we're back to original state
cursor.execute('SELECT COUNT(*) FROM regulatory_refs')
refs_count = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM regulatory_provisions')
provisions_count = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM kg_entities')
entities_count = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM kg_relationships')
relationships_count = cursor.fetchone()[0]

print(f'regulatory_refs: {refs_count:,}')
print(f'regulatory_provisions: {provisions_count:,}')
print(f'kg_entities: {entities_count:,}')
print(f'kg_relationships: {relationships_count:,}')

# Check if we're back to pre-PRP-D state
if refs_count == provisions_count == 22092 and entities_count == 0 and relationships_count == 0:
    print('\\n✅ ROLLBACK SUCCESSFUL - Back to pre-PRP-D state')
    rollback_success = True
else:
    print('\\n❌ ROLLBACK VERIFICATION FAILED')
    print('Database may not be in expected pre-PRP-D state')
    rollback_success = False

conn.close()
exit(0 if rollback_success else 1)
"

if [ $? -eq 0 ]; then
    print_status "$GREEN" "\n🎉 ROLLBACK COMPLETED SUCCESSFULLY"
    print_status "$GREEN" "========================================="
    print_status "$GREEN" "✅ Database restored to pre-PRP-D state"
    print_status "$GREEN" "✅ Factorized tables removed"
    print_status "$GREEN" "✅ Migration markers cleared"
    print_status "$GREEN" "✅ Current state backed up for safety"
    print_status "$GREEN" ""
    print_status "$BLUE" "📋 Rollback log: $ROLLBACK_LOG"
    print_status "$BLUE" "📋 Pre-rollback backup: $CURRENT_BACKUP"
    print_status "$BLUE" "📋 Original backup used: $LATEST_BACKUP"
    print_status "$GREEN" "========================================="
    
    print_status "$YELLOW" "\n📋 NEXT STEPS:"
    print_status "$BLUE" "1. Investigate why PRP-D needed rollback"
    print_status "$BLUE" "2. Fix any issues in the factorization scripts"
    print_status "$BLUE" "3. Run './check_prp_d_status.sh' to verify current state"
    print_status "$BLUE" "4. Re-run './execute_prp_d.sh' when ready"
    
    echo "ROLLBACK COMPLETED SUCCESSFULLY" >> "$ROLLBACK_LOG"
else
    print_status "$RED" "\n❌ ROLLBACK VERIFICATION FAILED"
    print_status "$RED" "Manual investigation required"
    print_status "$YELLOW" "Check $ROLLBACK_LOG for details"
    
    echo "ROLLBACK VERIFICATION FAILED" >> "$ROLLBACK_LOG"
    exit 1
fi