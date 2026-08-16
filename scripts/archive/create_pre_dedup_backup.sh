#!/usr/bin/env bash
# Create backup before deduplication

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups"
BACKUP_FILE="${BACKUP_DIR}/regulatory_provisions_pre_dedup_${TIMESTAMP}.sql"

echo "======================================================================"
echo "CREATING PRE-DEDUPLICATION BACKUP"
echo "======================================================================"
echo ""
echo "Backup file: ${BACKUP_FILE}"
echo ""
echo "This will take a few minutes..."
echo ""

# Export regulatory_provisions table
pg_dump \
  --host=aws-1-ap-southeast-2.pooler.supabase.com \
  --port=5432 \
  --username=postgres.llzdrxywpziewrzudwhj \
  --dbname=postgres \
  --table=regulatory_provisions \
  --no-owner \
  --no-acl \
  --format=plain \
  --file="${BACKUP_FILE}"

echo ""
echo "✅ Backup created successfully!"
echo ""
ls -lh "${BACKUP_FILE}"
echo ""
echo "Backup location: $(pwd)/${BACKUP_FILE}"
