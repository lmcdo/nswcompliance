#!/bin/bash
# Master PRP Execution Script for NSW Assessment UI Integration

set -e

PRP_NAME=$1
if [ -z "$PRP_NAME" ]; then
    echo "Usage: ./run_prp.sh <prp_name>"
    echo ""
    echo "Available PRPs:"
    echo "  a1 - Foundation & Project Merge"
    echo "  a2 - API Integration Using Existing Infrastructure"
    echo "  a3 - Database Bridge & Version Integration"
    echo "  a4 - UI Data Binding"
    echo "  a5 - State Management & Caching"
    echo "  a6 - Compliance Engine Integration"
    echo "  a7 - Report Generation"
    echo "  a8 - End-to-End Testing"
    echo ""
    echo "Example: ./run_prp.sh a1"
    exit 1
fi

# Navigate to project root
cd "$(dirname "$0")/../.."
PROJECT_ROOT=$(pwd)

echo "🚀 NSW Assessment UI Integration - PRP-${PRP_NAME^^}"
echo "=============================================="
echo "Project root: $PROJECT_ROOT"
echo "Timestamp: $(date)"
echo ""

# Function to run PRP and verification
run_prp() {
    local prp_id=$1
    local prp_name=$2

    echo "📋 Executing PRP-${prp_id^^}: $prp_name"
    echo "----------------------------------------"

    # Check if execution script exists
    if [ ! -f "PRPs/NEWUI/execute_prp_${prp_id}.sh" ]; then
        echo "❌ Execution script not found: execute_prp_${prp_id}.sh"
        exit 1
    fi

    # Execute PRP
    echo "🔧 Running execution script..."
    chmod +x "PRPs/NEWUI/execute_prp_${prp_id}.sh"
    bash "PRPs/NEWUI/execute_prp_${prp_id}.sh"

    echo ""
    echo "✅ Execution complete"
    echo ""

    # Run verification
    echo "🔍 Running verification script..."
    if [ -f "PRPs/NEWUI/scripts/verify_prp_${prp_id}.py" ]; then
        python "PRPs/NEWUI/scripts/verify_prp_${prp_id}.py"
        verification_result=$?

        if [ $verification_result -eq 0 ]; then
            echo ""
            echo "🎉 PRP-${prp_id^^} COMPLETED SUCCESSFULLY!"
            echo "✅ All verification checks passed"
            echo "✅ Ready to proceed to next PRP"

            # Create success marker
            echo "$(date): PRP-${prp_id^^} completed successfully" >> PRPs/NEWUI/results/completion_log.txt

        else
            echo ""
            echo "❌ PRP-${prp_id^^} VERIFICATION FAILED"
            echo "🔧 Please fix the issues before proceeding"
            echo "📁 Check results in: PRPs/NEWUI/results/prp_${prp_id}_results.json"
            exit 1
        fi
    else
        echo "⚠️ No verification script found for PRP-${prp_id^^}"
        echo "📝 Manual verification required"
    fi
}

# Execute based on PRP name
case $PRP_NAME in
    "a1")
        run_prp "a1" "Foundation & Project Merge"
        ;;
    "a2")
        run_prp "a2" "API Integration Using Existing Infrastructure"
        ;;
    "a3")
        run_prp "a3" "Database Bridge & Version Integration"
        ;;
    "a4")
        run_prp "a4" "UI Data Binding"
        ;;
    "a5")
        run_prp "a5" "State Management & Caching"
        ;;
    "a6")
        run_prp "a6" "Compliance Engine Integration"
        ;;
    "a7")
        run_prp "a7" "Report Generation"
        echo "📋 Coming soon: Report Generation"
        exit 1
        ;;
    "a8")
        run_prp "a8" "End-to-End Testing"
        echo "📋 Coming soon: End-to-End Testing"
        exit 1
        ;;
    *)
        echo "❌ Unknown PRP: $PRP_NAME"
        echo "Valid options: a1, a2, a3, a4, a5, a6, a7, a8"
        exit 1
        ;;
esac

echo ""
echo "🎯 PRP Pipeline Status:"
echo "✅ PRP-A1: Foundation & Project Merge"
if [ -f "PRPs/NEWUI/results/prp_a2_results.json" ]; then
    echo "✅ PRP-A2: API Integration"
else
    echo "⏳ PRP-A2: API Integration"
fi
echo "⏳ PRP-A3: Database Bridge"
echo "⏳ PRP-A4: UI Data Binding"
echo "⏳ PRP-A5: State Management"
echo "⏳ PRP-A6: Compliance Engine"
echo "⏳ PRP-A7: Report Generation"
echo "⏳ PRP-A8: End-to-End Testing"
echo ""
echo "📊 Overall Progress: $(ls PRPs/NEWUI/results/prp_a*_results.json 2>/dev/null | wc -l)/8 PRPs completed"