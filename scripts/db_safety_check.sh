#!/bin/bash
# Database Safety Check - MANDATORY before any database operations
# NEVER REMOVE THIS SCRIPT

echo "🚨 DATABASE SAFETY CHECK - MANDATORY 🚨"
echo "========================================"

# Set error handling
set -e

# Check if PostgreSQL is responsive
echo "1. Checking PostgreSQL health..."
"C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -h 127.0.0.1 -d nsw_planning -c "SELECT 1;" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✅ PostgreSQL responsive"
else
    echo "   ❌ PostgreSQL not responsive - ABORTING"
    exit 1
fi

# Check disk space
echo "2. Checking disk space..."
available_space=$(df . | tail -1 | awk '{print $4}')
if [ "$available_space" -lt 1000000 ]; then
    echo "   ❌ Low disk space (<1GB) - ABORTING"
    exit 1
else
    echo "   ✅ Disk space OK"
fi

# Check for active connections
echo "3. Checking database connections..."
active_connections=$("C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -h 127.0.0.1 -d nsw_planning -t -c "SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active';" 2>/dev/null | tr -d ' ')
if [ "$active_connections" -gt 50 ]; then
    echo "   ⚠️  Many active connections ($active_connections) - proceed with caution"
else
    echo "   ✅ Connection count OK ($active_connections)"
fi

# Check for locks
echo "4. Checking for database locks..."
locks=$("C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -h 127.0.0.1 -d nsw_planning -t -c "SELECT COUNT(*) FROM pg_locks WHERE NOT granted;" 2>/dev/null | tr -d ' ')
if [ "$locks" -gt 0 ]; then
    echo "   ❌ Database locks detected ($locks) - ABORTING"
    exit 1
else
    echo "   ✅ No locks detected"
fi

# Verify backup directory exists
echo "5. Checking backup infrastructure..."
backup_dir="backups"
mkdir -p "$backup_dir"
if [ -d "$backup_dir" ]; then
    echo "   ✅ Backup directory ready"
else
    echo "   ❌ Cannot create backup directory - ABORTING"
    exit 1
fi

echo ""
echo "🟢 DATABASE SAFETY CHECK PASSED"
echo "You may proceed with database operations"
echo "REMEMBER: All operations will auto-timeout at 30 seconds"
echo "========================================"