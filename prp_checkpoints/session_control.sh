#!/bin/bash
# Session Control Script - Enforces one PRP per session

echo "🔍 SESSION CONTROL CHECK"
echo "========================"

# Check which PRP should be executed next
next_prp=""
for prp in A1 A2 A3 A4 A5 A6 A7; do
    marker_file="prp_checkpoints/${prp}_completed.marker"
    if [ ! -f "$marker_file" ]; then
        next_prp="$prp"
        break
    fi
done

if [ -z "$next_prp" ]; then
    echo "🎯 ALL PRPs COMPLETED - No further work needed"
    echo "✅ 4-Tool Pipeline Implementation Complete"
else
    echo "📋 NEXT PRP TO EXECUTE: PRP-$next_prp"
    echo ""
    
    case $next_prp in
        "A1")
            echo "🔧 PRP-A1: Package Installation Verification"
            echo "   Duration: 15 minutes"
            echo "   Objective: Install and verify all 4 packages"
            echo "   Command: Execute package verification script in WSL2"
            ;;
        "A2") 
            echo "📄 PRP-A2: PDF Content Extraction"
            echo "   Duration: 30 minutes"
            echo "   Objective: Use RagAnything to extract real text from LEP PDF"
            echo "   Dependency: PRP-A1 must be completed first"
            ;;
        "A3")
            echo "🔗 PRP-A3: Source Grounding" 
            echo "   Duration: 30 minutes"
            echo "   Objective: Use LangExtract to add source citations"
            echo "   Dependency: PRP-A2 must be completed first"
            ;;
        "A4")
            echo "🕸️  PRP-A4: Knowledge Graph Construction"
            echo "   Duration: 45 minutes" 
            echo "   Objective: Use AutoSchemaKG to build structured relationships"
            echo "   Dependency: PRP-A3 must be completed first"
            ;;
        "A5")
            echo "🔮 PRP-A5: LightRAG Integration"
            echo "   Duration: 30 minutes"
            echo "   Objective: Insert processed content into LightRAG"
            echo "   Dependency: PRP-A4 must be completed first"
            ;;
        "A6")
            echo "❓ PRP-A6: Query Interface"
            echo "   Duration: 20 minutes"
            echo "   Objective: Create validated query script"
            echo "   Dependency: PRP-A5 must be completed first"
            ;;
        "A7")
            echo "🖥️  PRP-A7: Frontend Integration" 
            echo "   Duration: 20 minutes"
            echo "   Objective: Connect frontend to validated processor"
            echo "   Dependency: PRP-A6 must be completed first"
            ;;
    esac
    
    echo ""
    echo "⚠️  EXECUTION RULE: Complete ONLY this PRP in this session"
    echo "🛑 DO NOT attempt multiple PRPs in one conversation"
    echo "✅ After completion, mark PRP and END SESSION"
fi

echo "========================"