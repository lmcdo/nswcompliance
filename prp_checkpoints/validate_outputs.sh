#!/bin/bash
# PRP Output Validation Script
# Verifies that each PRP created the required output files with correct content

echo "🔍 Validating PRP Output Files..."
echo "================================="

validation_failed=0

# PRP-A1: Package Installation Verification
if [ -f "prp_checkpoints/A1_completed.marker" ]; then
    echo "📦 Validating PRP-A1 Package Installation..."
    
    # Test package imports in WSL2
    wsl_test=$(wsl -- bash -c "
        source /home/lawre/compliance_rag_env/bin/activate 2>/dev/null
        python3 -c 'from raganything import RAGAnything; print(\"RagAnything: OK\")' 2>/dev/null
        python3 -c 'from atlas_rag.kg_construction.triple_extraction import KnowledgeGraphExtractor; print(\"AutoSchemaKG: OK\")' 2>/dev/null  
        python3 -c 'import langextract as lx; print(\"LangExtract: OK\")' 2>/dev/null
        python3 -c 'from lightrag import LightRAG; print(\"LightRAG: OK\")' 2>/dev/null
    " 2>/dev/null)
    
    if [[ $wsl_test == *"RagAnything: OK"* ]] && [[ $wsl_test == *"AutoSchemaKG: OK"* ]] && [[ $wsl_test == *"LangExtract: OK"* ]] && [[ $wsl_test == *"LightRAG: OK"* ]]; then
        echo "  ✅ All 4 packages verified successfully"
    else
        echo "  ❌ Package verification failed"
        validation_failed=1
    fi
fi

# PRP-A2: Complete PDF Content Extraction
if [ -f "prp_checkpoints/A2_completed.marker" ]; then
    echo "📄 Validating PRP-A2 Complete PDF Extraction..."
    
    if [ -f "validated_outputs/A2_complete_extracted_content.json" ]; then
        # Check for 54 document entries
        doc_count=$(grep -c '"source_path"' "validated_outputs/A2_complete_extracted_content.json")
        if [ "$doc_count" -eq 54 ]; then
            echo "  ✅ All 54 PDFs processed and stored"
        else
            echo "  ❌ Expected 54 PDFs, found $doc_count entries"
            validation_failed=1
        fi
        
        # Check for required content from different document types
        if grep -q "4.3 Height of buildings" "validated_outputs/A2_complete_extracted_content.json" && 
           grep -q "setback" "validated_outputs/A2_complete_extracted_content.json" &&
           grep -q "State Environmental Planning Policy" "validated_outputs/A2_complete_extracted_content.json"; then
            echo "  ✅ Contains LEP, DCP, and SEPP content"
        else
            echo "  ❌ Missing required content from LEP, DCP, or SEPP documents"
            validation_failed=1
        fi
        
        # Check for no error messages
        if ! grep -q "Sorry, I'm not able to provide an answer" "validated_outputs/A2_complete_extracted_content.json"; then
            echo "  ✅ No error messages in extracted content"
        else
            echo "  ❌ Found error messages in extracted content"
            validation_failed=1
        fi
    else
        echo "  ❌ Missing output file: validated_outputs/A2_complete_extracted_content.json"
        validation_failed=1
    fi
fi

# PRP-A3: Source Grounding
if [ -f "prp_checkpoints/A3_completed.marker" ]; then
    echo "🔗 Validating PRP-A3 Source Grounding..."
    
    if [ -f "validated_outputs/A3_grounded_content.json" ]; then
        # Check for required citation fields
        if grep -q "char_start" "validated_outputs/A3_grounded_content.json" && 
           grep -q "source_location" "validated_outputs/A3_grounded_content.json"; then
            echo "  ✅ LangExtract grounding contains required citation fields"
        else
            echo "  ❌ Grounded content missing required citation metadata"
            validation_failed=1
        fi
    else
        echo "  ❌ Missing output file: validated_outputs/A3_grounded_content.json"
        validation_failed=1
    fi
fi

# PRP-A4: Knowledge Graph Construction
if [ -f "prp_checkpoints/A4_completed.marker" ]; then
    echo "🕸️  Validating PRP-A4 Knowledge Graph..."
    
    if [ -f "validated_outputs/A4_knowledge_graph.json" ]; then
        # Check for required planning entities
        if grep -q "height" "validated_outputs/A4_knowledge_graph.json" && 
           grep -q "FSR" "validated_outputs/A4_knowledge_graph.json" && 
           grep -q "setback" "validated_outputs/A4_knowledge_graph.json"; then
            echo "  ✅ AutoSchemaKG graph contains required planning entities"
        else
            echo "  ❌ Knowledge graph missing required planning entities"
            validation_failed=1
        fi
    else
        echo "  ❌ Missing output file: validated_outputs/A4_knowledge_graph.json"
        validation_failed=1
    fi
fi

# PRP-A5: LightRAG Integration
if [ -f "prp_checkpoints/A5_completed.marker" ]; then
    echo "🔮 Validating PRP-A5 LightRAG Integration..."
    
    if [ -f "validated_nsw_processor/kv_store_full_docs.json" ]; then
        # Check that knowledge base contains actual legislative text
        if grep -q "4.3 Height of buildings" "validated_nsw_processor/kv_store_full_docs.json"; then
            echo "  ✅ LightRAG knowledge base contains real legislative content"
        else
            echo "  ❌ LightRAG knowledge base missing Clause 4.3 content"
            validation_failed=1
        fi
    else
        echo "  ❌ Missing LightRAG knowledge base: validated_nsw_processor/"
        validation_failed=1
    fi
fi

# PRP-A6: Query Interface  
if [ -f "prp_checkpoints/A6_completed.marker" ]; then
    echo "❓ Validating PRP-A6 Query Interface..."
    
    if [ -f "scripts/validated_nsw_query.py" ]; then
        echo "  ✅ Validated query script exists"
    else
        echo "  ❌ Missing query script: scripts/validated_nsw_query.py"
        validation_failed=1
    fi
fi

# PRP-A7: Frontend Integration
if [ -f "prp_checkpoints/A7_completed.marker" ]; then
    echo "🖥️  Validating PRP-A7 Frontend Integration..."
    
    if grep -q "validated_nsw_processor" "frontend/server.py" 2>/dev/null; then
        echo "  ✅ Frontend configured to use validated processor"
    else
        echo "  ❌ Frontend not properly connected to validated processor"
        validation_failed=1
    fi
fi

echo "================================="

if [ $validation_failed -eq 0 ]; then
    echo "🎯 ALL PRP OUTPUTS VALIDATED - 4-TOOL PIPELINE VERIFIED"
    echo "✅ System ready for production use with real legislative content"
else
    echo "⚠️  VALIDATION FAILED - Some PRP outputs are missing or invalid"
    echo "❌ Do not proceed until all validation issues are resolved"
    exit 1
fi