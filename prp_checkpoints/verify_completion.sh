#!/bin/bash
# PRP Completion Verification Script
# Ensures atomic completion of each micro-PRP before proceeding

echo "🔍 Checking PRP completion status..."
echo "======================================="

# Function to check individual PRP completion
check_prp_completion() {
    local prp_id=$1
    local marker_file="prp_checkpoints/${prp_id}_completed.marker"
    
    if [ -f "$marker_file" ]; then
        echo "✅ PRP-$prp_id: COMPLETED - $(cat "$marker_file")"
        return 0
    else
        echo "❌ PRP-$prp_id: NOT COMPLETED"
        return 1
    fi
}

# Check all PRPs in sequential order - NO SKIPPING ALLOWED
prps_failed=0

for prp in A1 A2 A2-EXT A3 A4 A5 A6 A7; do
    if ! check_prp_completion "$prp"; then
        echo "🛑 CRITICAL: PRP-$prp must be completed before proceeding to next PRP"
        prps_failed=1
        
        # Don't check remaining PRPs if one fails
        case $prp in
            "A1") echo "   → Execute: Package Installation Verification" ;;
            "A2") echo "   → Execute: RagAnything PDF Content Extraction" ;;
            "A2-EXT") echo "   → Execute: Process 85 Missing Marrickville DCP files" ;;
            "A3") echo "   → Execute: LangExtract Source Grounding" ;;
            "A4") echo "   → Execute: AutoSchemaKG Knowledge Graph Construction" ;;
            "A5") echo "   → Execute: LightRAG Integration" ;;
            "A6") echo "   → Execute: Query Interface Creation" ;;
            "A7") echo "   → Execute: Frontend Integration" ;;
        esac
        break
    fi
done

echo "======================================="

if [ $prps_failed -eq 0 ]; then
    echo "🎯 ALL PRPs COMPLETED - VALIDATED 4-TOOL PIPELINE OPERATIONAL"
    echo "✅ RagAnything + LangExtract + AutoSchemaKG + LightRAG = SUCCESS"
    exit 0
else
    echo "⚠️  PIPELINE INCOMPLETE - Execute missing PRPs before using system"
    echo "❌ No workarounds, no shortcuts, no 'close enough' solutions allowed"
    exit 1
fi