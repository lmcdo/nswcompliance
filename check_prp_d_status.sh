#!/bin/bash
# PRP-D Status Check Script
# Quick verification of PRP-D completion status

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

print_status "$BLUE" "=========================================="
print_status "$BLUE" "🔍 PRP-D DATABASE FACTORIZATION STATUS"
print_status "$BLUE" "=========================================="

# Check if PRP-D has been completed
if [ -f "migration_markers/PRP_D_COMPLETE.marker" ]; then
    print_status "$GREEN" "✅ PRP-D STATUS: COMPLETED"
    print_status "$GREEN" "Completion details:"
    cat migration_markers/PRP_D_COMPLETE.marker | sed 's/^/   /'
    print_status "$GREEN" ""
    
    # Show current database state
    print_status "$BLUE" "📊 CURRENT DATABASE STATE:"
    ./venv_linux/Scripts/python.exe -c "
import sqlite3
conn = sqlite3.connect('nsw_planning.db')
cursor = conn.cursor()

tables = [
    ('regulatory_refs', 'Original regulatory_refs'),
    ('kg_entities', 'AutoSchemaKG entities'),
    ('kg_relationships', 'AutoSchemaKG relationships'),
    ('regulatory_provisions_clean', 'Formal provisions'),
    ('contextual_guidance_real', 'Contextual guidance'),
    ('development_controls', 'Development controls'),
    ('visual_elements_real', 'Visual elements')
]

for table, desc in tables:
    try:
        cursor.execute(f'SELECT COUNT(*) FROM {table}')
        count = cursor.fetchone()[0]
        print(f'   {desc}: {count:,}')
    except:
        print(f'   {desc}: TABLE NOT FOUND')

conn.close()
"
    
    # Test a quick compliance query
    print_status "$BLUE" "\n🧠 TESTING INTELLIGENT QUERY CAPABILITY:"
    ./venv_linux/Scripts/python.exe -c "
import sqlite3
import time

conn = sqlite3.connect('nsw_planning.db')
cursor = conn.cursor()

try:
    start = time.time()
    cursor.execute('''
        SELECT COUNT(*) FROM kg_relationships kr
        WHERE kr.predicate IN ('requires', 'must', 'protect', 'because')
    ''')
    result = cursor.fetchone()[0]
    query_time = time.time() - start
    
    print(f'   Semantic relationships available: {result:,}')
    print(f'   Query time: {query_time:.3f}s')
    
    if result >= 1000 and query_time < 1.0:
        print('   ✅ Intelligent queries: WORKING')
    else:
        print('   ⚠️ Intelligent queries: LIMITED')
        
except Exception as e:
    print(f'   ❌ Query test failed: {e}')
finally:
    conn.close()
"

elif [ -f "migration_markers/factorization_completed.marker" ]; then
    print_status "$YELLOW" "⚠️ PRP-D STATUS: PARTIALLY COMPLETE"
    print_status "$YELLOW" "Factorization completed but final verification pending"
    
elif [ -f "migration_markers/autoschemakg_import_completed.marker" ]; then
    print_status "$YELLOW" "⚠️ PRP-D STATUS: IN PROGRESS"
    print_status "$YELLOW" "AutoSchemaKG imported but factorization pending"
    
else
    print_status "$RED" "❌ PRP-D STATUS: NOT STARTED"
    print_status "$YELLOW" "Current database state (pre-factorization):"
    
    ./venv_linux/Scripts/python.exe -c "
import sqlite3
conn = sqlite3.connect('nsw_planning.db')
cursor = conn.cursor()

tables = ['regulatory_refs', 'regulatory_provisions', 'kg_entities', 'kg_relationships', 'development_controls']
for table in tables:
    cursor.execute(f'SELECT COUNT(*) FROM {table}')
    count = cursor.fetchone()[0]
    print(f'   {table}: {count:,}')

# Check if tables are mirrors (sign of failed factorization)
cursor.execute('SELECT COUNT(*) FROM regulatory_refs')
refs_count = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(*) FROM regulatory_provisions')
provisions_count = cursor.fetchone()[0]

if refs_count == provisions_count == 22092:
    print('   ⚠️ Tables appear to be mirrors - factorization needed')

conn.close()
"
    
    print_status "$YELLOW" "\n📋 TO START PRP-D EXECUTION:"
    print_status "$BLUE" "   chmod +x execute_prp_d.sh"
    print_status "$BLUE" "   ./execute_prp_d.sh"
fi

# Check for backup files
print_status "$BLUE" "\n💾 BACKUP FILES AVAILABLE:"
BACKUPS=$(ls -1 nsw_planning_backup_*.db 2>/dev/null | wc -l)
if [ $BACKUPS -gt 0 ]; then
    print_status "$GREEN" "   $BACKUPS backup files found"
    ls -1t nsw_planning_backup_*.db | head -3 | sed 's/^/   /'
else
    print_status "$YELLOW" "   No backup files found"
fi

# Check for log files
print_status "$BLUE" "\n📋 EXECUTION LOGS AVAILABLE:"
LOGS=$(ls -1 prp_d_execution_*.log 2>/dev/null | wc -l)
if [ $LOGS -gt 0 ]; then
    print_status "$GREEN" "   $LOGS log files found"
    ls -1t prp_d_execution_*.log | head -3 | sed 's/^/   /'
    print_status "$BLUE" "   Use 'tail -f [logfile]' to monitor execution"
else
    print_status "$YELLOW" "   No execution logs found"
fi

print_status "$BLUE" "\n=========================================="

# Show next steps based on status
if [ -f "migration_markers/PRP_D_COMPLETE.marker" ]; then
    print_status "$GREEN" "🎉 READY FOR INTELLIGENT COMPLIANCE QUERIES!"
elif [ ! -f "migration_markers/autoschemakg_import_completed.marker" ]; then
    print_status "$YELLOW" "📋 NEXT STEP: Run './execute_prp_d.sh' to start factorization"
else
    print_status "$YELLOW" "📋 NEXT STEP: Check logs and continue PRP-D execution"
fi

print_status "$BLUE" "=========================================="