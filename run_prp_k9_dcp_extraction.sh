#!/bin/bash
# PRP-K9: Extract ALL DCP documents for complete zone coverage

echo "Starting PRP-K9 DCP Extraction"
echo "=============================="

# Create output directory
mkdir -p prp_k9_complete_dcp_extraction

# Counter for tracking
count=0
total=$(find docs/dcps/INNERWEST -name "*.pdf" -not -name "*Map*" | wc -l)

echo "Found $total DCP documents to process (excluding maps)"

# Extract all DCP documents (excluding maps)
find docs/dcps/INNERWEST -name "*.pdf" -not -name "*Map*" | while read file; do
    count=$((count + 1))
    echo "[$count/$total] Processing: $(basename "$file")"
    
    # Run MinerU extraction
    ./venv_linux/Scripts/mineru.exe --path "$file" \
        --output "prp_k9_complete_dcp_extraction" \
        --method auto --backend pipeline
    
    # Add small delay to avoid overwhelming system
    sleep 2
done

echo "DCP Extraction complete!"
echo "Output directory: prp_k9_complete_dcp_extraction"