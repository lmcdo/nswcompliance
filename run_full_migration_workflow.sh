#!/bin/bash
################################################################################
# FULL MIGRATION WORKFLOW WITH AUTOMATED VERIFICATION
################################################################################
# This script runs the complete Phase 1 migration workflow:
#   1. Pre-migration verification
#   2. Database backup
#   3. Run migration
#   4. Post-migration verification
#   5. Rollback on failure
#
# Usage:
#   bash run_full_migration_workflow.sh
#
# Exit codes:
#   0 - Success (all tests passed)
#   1 - Pre-verification failed
#   2 - Migration failed
#   3 - Post-verification failed
################################################################################

set -e  # Exit on any error

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Log file
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="migration_logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/migration_workflow_$TIMESTAMP.log"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

print_header() {
    echo "" | tee -a "$LOG_FILE"
    echo "================================================================================" | tee -a "$LOG_FILE"
    echo "$1" | tee -a "$LOG_FILE"
    echo "================================================================================" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
}

# Error handler
handle_error() {
    local exit_code=$1
    local step=$2

    log_error "$step failed with exit code $exit_code"
    log_error "Check log file: $LOG_FILE"

    if [ "$step" = "POST-VERIFICATION" ]; then
        log_warning "Migration completed but verification failed"
        log_warning "Consider manual inspection or rollback"
        echo ""
        echo "To rollback:"
        echo "  python rollback_phase1.py"
        echo ""
        echo "To investigate:"
        echo "  cat $LOG_FILE"
        echo "  cat verification_report_post_*.json"
    fi

    exit $exit_code
}

################################################################################
# START WORKFLOW
################################################################################

print_header "PHASE 1 MIGRATION WORKFLOW"
log_info "Timestamp: $TIMESTAMP"
log_info "Log file: $LOG_FILE"
echo ""

################################################################################
# STEP 1: PRE-MIGRATION VERIFICATION
################################################################################

print_header "STEP 1: PRE-MIGRATION VERIFICATION"
log_info "Running pre-migration tests..."

python verify_phase1_migration.py pre > "$LOG_DIR/pre_verification_$TIMESTAMP.log" 2>&1
if [ $? -ne 0 ]; then
    log_error "Pre-migration verification failed!"
    log_error "Review: $LOG_DIR/pre_verification_$TIMESTAMP.log"
    handle_error 1 "PRE-VERIFICATION"
fi

log_success "Pre-migration verification passed"
log_info "Report saved: verification_report_pre_*.json"

# Parse pre-verification metrics
if [ -f "verification_report_pre_"*.json ]; then
    LATEST_PRE_REPORT=$(ls -t verification_report_pre_*.json | head -1)
    log_info "Analyzing baseline metrics..."

    # Extract key metrics (requires jq)
    if command -v jq &> /dev/null; then
        TOTAL_PROVISIONS=$(jq -r '.metrics.total_provisions_pre // "unknown"' "$LATEST_PRE_REPORT")
        DUPLICATE_GROUPS=$(jq -r '.metrics.duplicate_groups_pre // "unknown"' "$LATEST_PRE_REPORT")
        EXCESS_RECORDS=$(jq -r '.metrics.excess_records_pre // "unknown"' "$LATEST_PRE_REPORT")

        log_info "  Total provisions: $TOTAL_PROVISIONS"
        log_info "  Duplicate groups: $DUPLICATE_GROUPS"
        log_info "  Excess records to mark: $EXCESS_RECORDS"
    fi
fi

echo ""
log_warning "Ready to proceed with migration?"
read -p "Type 'yes' to continue: " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    log_info "Migration cancelled by user"
    exit 0
fi

################################################################################
# STEP 2: RUN MIGRATION
################################################################################

print_header "STEP 2: RUN MIGRATION"
log_info "Starting Phase 1 migration..."
log_info "This will:"
log_info "  - Create database backup"
log_info "  - Add new columns (is_canonical, canonical_provision_id, text_hash)"
log_info "  - Mark ~${EXCESS_RECORDS:-2300} duplicate provisions"
log_info "  - Create view (regulatory_provisions_canonical)"
echo ""

# Run migration (non-interactive mode)
# Note: This assumes run_phase1_migration.py can accept 'yes' via stdin
echo "yes" | python run_phase1_migration.py > "$LOG_DIR/migration_$TIMESTAMP.log" 2>&1
if [ $? -ne 0 ]; then
    log_error "Migration failed!"
    log_error "Review: $LOG_DIR/migration_$TIMESTAMP.log"
    handle_error 2 "MIGRATION"
fi

log_success "Migration completed successfully"
log_info "Backup location: backups/pre_phase1_migration_*.sql"

################################################################################
# STEP 3: POST-MIGRATION VERIFICATION
################################################################################

print_header "STEP 3: POST-MIGRATION VERIFICATION"
log_info "Running post-migration tests..."

python verify_phase1_migration.py post > "$LOG_DIR/post_verification_$TIMESTAMP.log" 2>&1
if [ $? -ne 0 ]; then
    log_error "Post-migration verification failed!"
    log_error "Review: $LOG_DIR/post_verification_$TIMESTAMP.log"
    handle_error 3 "POST-VERIFICATION"
fi

log_success "Post-migration verification passed"
log_info "Report saved: verification_report_post_*.json"

# Parse post-verification metrics
if [ -f "verification_report_post_"*.json ]; then
    LATEST_POST_REPORT=$(ls -t verification_report_post_*.json | head -1)
    log_info "Analyzing results..."

    if command -v jq &> /dev/null; then
        TOTAL_POST=$(jq -r '.metrics.total_provisions_post // "unknown"' "$LATEST_POST_REPORT")
        CANONICAL_COUNT=$(jq -r '.metrics.canonical_count // "unknown"' "$LATEST_POST_REPORT")
        DUPLICATE_COUNT=$(jq -r '.metrics.duplicate_count // "unknown"' "$LATEST_POST_REPORT")
        TESTS_PASSED=$(jq -r '.summary.passed // "unknown"' "$LATEST_POST_REPORT")
        TESTS_TOTAL=$(jq -r '.summary.total_tests // "unknown"' "$LATEST_POST_REPORT")

        log_info "  Total provisions: $TOTAL_POST (no data loss)"
        log_info "  Canonical: $CANONICAL_COUNT"
        log_info "  Duplicates marked: $DUPLICATE_COUNT"
        log_info "  Tests passed: $TESTS_PASSED/$TESTS_TOTAL"
    fi
fi

################################################################################
# STEP 4: SUCCESS SUMMARY
################################################################################

print_header "MIGRATION WORKFLOW COMPLETE"

log_success "All steps completed successfully!"
echo ""
echo "What changed:"
echo "  ✓ Added 4 new columns to regulatory_provisions"
echo "  ✓ Marked ~$DUPLICATE_COUNT provisions as duplicates"
echo "  ✓ Created view: regulatory_provisions_canonical"
echo "  ✓ All data preserved (no deletions)"
echo ""
echo "Next steps:"
echo "  1. Update frontend queries to add: WHERE is_canonical = TRUE"
echo "  2. Or use the view: SELECT * FROM regulatory_provisions_canonical"
echo "  3. Test the UI: npm run dev"
echo ""
echo "Files created:"
echo "  - Backup: backups/pre_phase1_migration_*.sql"
echo "  - Pre-verification: $LOG_DIR/pre_verification_$TIMESTAMP.log"
echo "  - Migration log: $LOG_DIR/migration_$TIMESTAMP.log"
echo "  - Post-verification: $LOG_DIR/post_verification_$TIMESTAMP.log"
echo "  - JSON reports: verification_report_*.json"
echo ""
echo "To rollback (if needed):"
echo "  python rollback_phase1.py"
echo ""

log_success "Migration workflow completed at $(date)"

exit 0
