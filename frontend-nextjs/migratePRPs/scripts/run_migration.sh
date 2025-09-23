#!/bin/bash
# Master Migration Orchestrator
# Runs all migration PRPs in sequence with verification

set -e  # Exit on any error

echo "🚀 NSW ASSESSMENT UI MIGRATION ORCHESTRATOR"
echo "==========================================="
echo "Migrating new UI to working backend with Google Autocomplete"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Navigate to frontend-nextjs directory
cd "$(dirname "$0")/../.."
PROJECT_ROOT=$(pwd)
echo "📁 Project root: $PROJECT_ROOT"

# Function to run PRP with verification
run_prp() {
    local prp_num=$1
    local prp_name=$2

    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Running PRP-M${prp_num}: ${prp_name}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # Execute PRP script
    if [ -f "migratePRPs/scripts/execute_prp_m${prp_num}.sh" ]; then
        bash "migratePRPs/scripts/execute_prp_m${prp_num}.sh"

        # Run verification
        echo ""
        echo "Running verification..."
        if [ -f "migratePRPs/verification/verify_prp_m${prp_num}.py" ]; then
            python3 "migratePRPs/verification/verify_prp_m${prp_num}.py" || {
                echo -e "${YELLOW}⚠️ Verification warnings detected${NC}"
                read -p "Continue anyway? (y/n): " -n 1 -r
                echo
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    echo -e "${RED}Migration halted at PRP-M${prp_num}${NC}"
                    exit 1
                fi
            }
        else
            echo -e "${YELLOW}⚠️ No verification script for PRP-M${prp_num}${NC}"
        fi

        echo -e "${GREEN}✅ PRP-M${prp_num} completed successfully${NC}"
    else
        echo -e "${YELLOW}⚠️ PRP-M${prp_num} script not found, skipping...${NC}"
    fi
}

# Pre-flight checks
echo ""
echo "Running pre-flight checks..."
echo "----------------------------"

# Check Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo "✅ Node.js: $NODE_VERSION"
else
    echo -e "${RED}❌ Node.js not found${NC}"
    exit 1
fi

# Check npm
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    echo "✅ npm: $NPM_VERSION"
else
    echo -e "${RED}❌ npm not found${NC}"
    exit 1
fi

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "✅ Python: $PYTHON_VERSION"
else
    echo -e "${YELLOW}⚠️ Python 3 not found (verification will fail)${NC}"
fi

# Check if nsw-assessment exists
if [ -d "../../nsw-assessment" ]; then
    echo "✅ Source UI found: nsw-assessment"
else
    echo -e "${RED}❌ nsw-assessment not found${NC}"
    echo "Expected path: $(realpath ../../nsw-assessment)"
    exit 1
fi

# Check if server is running
if lsof -Pi :3007 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️ Server is running on port 3007${NC}"
    echo "Please stop the server before running migration"
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Migration menu
echo ""
echo "Migration Options:"
echo "=================="
echo "1. Full Migration (All PRPs)"
echo "2. PRP-M1: Component Migration Only"
echo "3. PRP-M2: Google Autocomplete Only"
echo "4. PRP-M3: State Management Bridge"
echo "5. PRP-M4: API Connection Layer"
echo "6. PRP-M5: Testing and Validation"
echo "7. Custom Range (e.g., M1-M3)"
echo ""
read -p "Select option (1-7): " option

case $option in
    1)
        echo ""
        echo "Starting FULL MIGRATION..."
        echo "=========================="

        # Create migration timestamp
        MIGRATION_ID="migration_$(date +%Y%m%d_%H%M%S)"
        echo "Migration ID: $MIGRATION_ID"

        # Create backup
        echo ""
        echo "Creating full backup..."
        BACKUP_DIR="migratePRPs/backup/$MIGRATION_ID"
        mkdir -p "$BACKUP_DIR"

        if [ -d "components" ]; then
            cp -r components "$BACKUP_DIR/components"
        fi
        if [ -d "app" ]; then
            cp -r app "$BACKUP_DIR/app"
        fi
        echo "✅ Backup created: $BACKUP_DIR"

        # Run all PRPs
        run_prp 1 "Component Migration Foundation"
        run_prp 2 "Google Autocomplete Integration"
        run_prp 3 "UI State Management Bridge"
        run_prp 4 "API Connection Layer"
        run_prp 5 "Testing and Validation"

        echo ""
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}🎉 FULL MIGRATION COMPLETE!${NC}"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        ;;

    2)
        run_prp 1 "Component Migration Foundation"
        ;;

    3)
        run_prp 2 "Google Autocomplete Integration"
        ;;

    4)
        run_prp 3 "UI State Management Bridge"
        ;;

    5)
        run_prp 4 "API Connection Layer"
        ;;

    6)
        run_prp 5 "Testing and Validation"
        ;;

    7)
        read -p "Enter range (e.g., 1-3): " range
        IFS='-' read -ra RANGE <<< "$range"
        for i in $(seq ${RANGE[0]} ${RANGE[1]}); do
            case $i in
                1) run_prp 1 "Component Migration Foundation" ;;
                2) run_prp 2 "Google Autocomplete Integration" ;;
                3) run_prp 3 "UI State Management Bridge" ;;
                4) run_prp 4 "API Connection Layer" ;;
                5) run_prp 5 "Testing and Validation" ;;
            esac
        done
        ;;

    *)
        echo -e "${RED}Invalid option${NC}"
        exit 1
        ;;
esac

# Post-migration summary
echo ""
echo "Migration Summary"
echo "================="
echo "✅ Components migrated to: components/new-ui/"
echo "✅ Test pages available at:"
echo "   - http://localhost:3007/new-ui-test"
echo "   - http://localhost:3007/autocomplete-test"
echo ""
echo "📋 Next Steps:"
echo "1. Start the development server: npm run dev"
echo "2. Test the new UI at the URLs above"
echo "3. Verify Google Autocomplete works"
echo "4. Check all API connections"
echo ""

# Generate final report
cat > "migratePRPs/results/migration_summary_$(date +%Y%m%d_%H%M%S).json" << EOF
{
  "migration_id": "$MIGRATION_ID",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")",
  "option_selected": "$option",
  "backup_location": "${BACKUP_DIR:-none}",
  "status": "completed",
  "test_urls": [
    "http://localhost:3007/new-ui-test",
    "http://localhost:3007/autocomplete-test"
  ]
}
EOF

echo "Report saved to: migratePRPs/results/"
echo ""
echo -e "${GREEN}Migration orchestration complete!${NC}"