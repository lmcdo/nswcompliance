#!/bin/bash
# PRP-M1 Execution Script with Pre-flight Checks
# ==================================================

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 PRP-M1 RESEARCH ASSISTANT MIGRATION"
echo "======================================"
echo "Timestamp: $(date)"
echo "Working Directory: $SCRIPT_DIR"
echo ""

# ============================================================================
# PRE-FLIGHT CHECKS
# ============================================================================

echo "🔍 PRE-FLIGHT CHECKS"
echo "==================="

# Check required files
echo "📁 Checking required files..."
required_files=(
    "nsw_planning.db"
    "research_assistant_schema_optimized.sql"
    "execute_prp_m1.py"
    "PRP-M1_RESEARCH_ASSISTANT_MIGRATION.md"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ ERROR: Required file missing: $file"
        exit 1
    else
        echo "✅ Found: $file"
    fi
done

# Check SQLite database
echo ""
echo "🗄️  Checking SQLite database..."
if ! command -v sqlite3 &> /dev/null; then
    echo "❌ ERROR: sqlite3 command not found"
    exit 1
fi

# Test SQLite connection and get row counts
echo "📊 SQLite Database Status:"
sqlite3 nsw_planning.db "
SELECT 
    'documents: ' || COUNT(*) 
FROM documents
UNION ALL
SELECT 
    'regulatory_provisions: ' || COUNT(*) 
FROM regulatory_provisions
UNION ALL
SELECT 
    'quantitative_standards: ' || COUNT(*) 
FROM quantitative_standards;
"

# Check PostgreSQL connection
echo ""
echo "🐘 Checking PostgreSQL connection..."
if ! command -v psql &> /dev/null; then
    echo "❌ ERROR: psql command not found"
    exit 1
fi

# Test PostgreSQL connection
if ! psql -h localhost -U postgres -d nsw_planning -c "SELECT version();" > /dev/null 2>&1; then
    echo "❌ ERROR: Cannot connect to PostgreSQL"
    echo "   Make sure PostgreSQL is running and credentials are correct"
    exit 1
else
    echo "✅ PostgreSQL connection successful"
fi

# Check Python environment
echo ""
echo "🐍 Checking Python environment..."
if ! ./venv_linux/Scripts/python.exe --version; then
    echo "❌ ERROR: Python virtual environment not found"
    exit 1
fi

# Check Python dependencies
echo "📦 Checking Python dependencies..."
./venv_linux/Scripts/python.exe -c "
import sqlite3, psycopg2, json
print('✅ All required Python packages available')
"

echo ""
echo "✅ All pre-flight checks passed!"
echo ""

# ============================================================================
# EXECUTION OPTIONS
# ============================================================================

echo "🎛️  EXECUTION OPTIONS"
echo "==================="
echo ""
echo "Choose execution mode:"
echo "[1] Full automated execution (no stops)"
echo "[2] Interactive execution with stage feedback (RECOMMENDED)"
echo "[3] Dry run (validation only, no changes)"
echo "[4] Resume from specific stage"
echo "[5] View previous execution reports"
echo ""

read -p "Select option [1-5]: " choice

case $choice in
    1)
        echo "🤖 Starting AUTOMATED execution..."
        exec_mode="--automated"
        ;;
    2)
        echo "👥 Starting INTERACTIVE execution..."
        exec_mode="--interactive"
        ;;
    3)
        echo "🔍 Starting DRY RUN..."
        exec_mode="--dry-run"
        ;;
    4)
        echo "⏭️  Available stages:"
        echo "  Phase 1: Pre-migration validation (steps 1-5)"
        echo "  Phase 2: Data extraction (steps 6-10)" 
        echo "  Phase 3: Schema population (steps 11-15)"
        echo "  Phase 4: Validation (steps 16-20)"
        echo "  Phase 5: Cutover (steps 21-25)"
        echo ""
        read -p "Enter phase number to resume from [1-5]: " phase
        exec_mode="--resume-from-phase $phase"
        ;;
    5)
        echo "📊 Previous execution reports:"
        ls -la prp_m1_report_*.json 2>/dev/null || echo "No reports found"
        echo ""
        read -p "Enter report filename to view (or press Enter to continue): " report_file
        if [ -n "$report_file" ] && [ -f "$report_file" ]; then
            echo "📋 Report contents:"
            cat "$report_file" | jq '.' 2>/dev/null || cat "$report_file"
            echo ""
            read -p "Press Enter to continue to execution menu..."
            exec bash "$0"  # Restart the menu
        fi
        exec_mode="--interactive"  # Default to interactive
        ;;
    *)
        echo "❌ Invalid choice. Defaulting to interactive mode."
        exec_mode="--interactive"
        ;;
esac

# ============================================================================
# BACKUP CREATION
# ============================================================================

echo ""
echo "💾 CREATING SAFETY BACKUPS"
echo "=========================="

# Create backups directory
mkdir -p backups

# Backup SQLite
backup_timestamp=$(date +%Y%m%d_%H%M%S)
sqlite_backup="backups/nsw_planning_pre_prp_m1_$backup_timestamp.db"
echo "📦 Creating SQLite backup: $sqlite_backup"
cp nsw_planning.db "$sqlite_backup"

# Backup PostgreSQL
pg_backup="backups/nsw_planning_pre_prp_m1_$backup_timestamp.sql"
echo "📦 Creating PostgreSQL backup: $pg_backup"
PGPASSWORD=postgres pg_dump -h localhost -U postgres -d nsw_planning > "$pg_backup"

# Create checksums
echo "🔐 Creating checksums..."
(
    cd backups
    md5sum *_$backup_timestamp.* > checksums_$backup_timestamp.txt
    echo "✅ Checksums saved to checksums_$backup_timestamp.txt"
)

echo "✅ Backups completed successfully"
echo ""

# ============================================================================
# FINAL CONFIRMATION
# ============================================================================

echo "⚠️  FINAL CONFIRMATION"
echo "====================="
echo ""
echo "🎯 About to execute PRP-M1 Research Assistant Migration"
echo "📊 This will:"
echo "   • Analyze your existing SQLite data"
echo "   • Fix the zone inference problems"
echo "   • Create optimized PostgreSQL schema"
echo "   • Migrate data with explicit zone extraction"
echo "   • Enable research assistant functionality"
echo ""
echo "💾 Backups created:"
echo "   • SQLite: $sqlite_backup"
echo "   • PostgreSQL: $pg_backup"
echo ""
echo "⏱️  Estimated execution time:"
case $exec_mode in
    *automated*)
        echo "   • Automated: 15-30 minutes"
        ;;
    *interactive*)
        echo "   • Interactive: 30-60 minutes (includes review time)"
        ;;
    *dry-run*)
        echo "   • Dry run: 5-10 minutes"
        ;;
esac
echo ""

read -p "❓ Are you ready to proceed? [y/N]: " confirm

if [[ $confirm =~ ^[Yy]$ ]]; then
    echo ""
    echo "🚀 STARTING PRP-M1 EXECUTION"
    echo "============================"
    echo ""
    
    # Execute the Python script
    if ./venv_linux/Scripts/python.exe execute_prp_m1.py $exec_mode; then
        echo ""
        echo "🎉 PRP-M1 COMPLETED SUCCESSFULLY!"
        echo "================================="
        echo ""
        echo "✅ Migration completed"
        echo "📊 Check the execution report for details"
        echo "🔍 Run validation queries to verify data integrity"
        echo ""
        echo "Next steps:"
        echo "1. Review the execution report"
        echo "2. Test the research assistant functionality"
        echo "3. Update your application configuration"
        echo ""
    else
        echo ""
        echo "❌ PRP-M1 EXECUTION FAILED"
        echo "=========================="
        echo ""
        echo "🔧 Troubleshooting steps:"
        echo "1. Check the execution log for errors"
        echo "2. Verify database connections"
        echo "3. Ensure sufficient disk space"
        echo "4. Consider restoring from backup and retrying"
        echo ""
        echo "💾 Backup locations:"
        echo "   • SQLite: $sqlite_backup"
        echo "   • PostgreSQL: $pg_backup"
        echo ""
        exit 1
    fi
else
    echo ""
    echo "🛑 Execution cancelled by user"
    echo "Backups are preserved in backups/ directory"
    echo ""
    exit 0
fi