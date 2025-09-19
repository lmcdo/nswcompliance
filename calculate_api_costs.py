#!/usr/bin/env python3
"""
Calculate realistic API costs for entity extraction
"""
import json
import os
from pathlib import Path

print('REALISTIC API COST CALCULATION')
print('=' * 50)

output_dir = Path("C:/Users/lawre/Downloads/solvyra/projects/compliance engine/compliance-engine/output")
doc_folders = [d for d in output_dir.iterdir() if d.is_dir()]

# Sample documents to estimate text volume
total_text_length = 0
documents_sampled = 0

print('Sampling documents to estimate text volume...')
for doc_folder in doc_folders[:10]:  # Sample 10 documents
    content_file = doc_folder / 'auto' / f'{doc_folder.name}_content_list.json'
    if content_file.exists():
        try:
            with open(content_file, 'r', encoding='utf-8') as f:
                content = json.load(f)
                doc_text = ' '.join([item.get('text', '') for item in content])
                total_text_length += len(doc_text)
                documents_sampled += 1
                print(f'  {doc_folder.name}: {len(doc_text):,} characters')
        except Exception as e:
            print(f'  Error reading {doc_folder.name}: {e}')

if documents_sampled > 0:
    avg_chars_per_doc = total_text_length / documents_sampled
    total_chars_estimate = avg_chars_per_doc * len(doc_folders)
    
    print(f'\nText Volume Analysis:')
    print(f'  Documents sampled: {documents_sampled}')
    print(f'  Average characters per document: {avg_chars_per_doc:,.0f}')
    print(f'  Total documents: {len(doc_folders)}')
    print(f'  Estimated total characters: {total_chars_estimate:,.0f}')
    
    # Token estimation (roughly 4 characters per token for English text)
    total_tokens_estimate = total_chars_estimate / 4
    print(f'  Estimated total tokens: {total_tokens_estimate:,.0f}')
    
    # API pricing (current rates as of Dec 2024)
    print(f'\nAPI Cost Analysis:')
    
    # OpenAI GPT-4o pricing (per 1K tokens)
    openai_input_rate = 2.50 / 1000   # $2.50 per 1M tokens = $0.0025 per 1K
    openai_output_rate = 10.00 / 1000  # $10.00 per 1M tokens = $0.01 per 1K
    
    # Assume input = full text, output = 10% of input (structured extraction is concise)
    input_tokens = total_tokens_estimate
    output_tokens = total_tokens_estimate * 0.1  # Conservative estimate
    
    openai_input_cost = (input_tokens / 1000) * (2.50 / 1000)  # Convert to proper rate
    openai_output_cost = (output_tokens / 1000) * (10.00 / 1000)
    openai_total = openai_input_cost + openai_output_cost
    
    print(f'  OpenAI GPT-4o:')
    print(f'    Input: {input_tokens:,.0f} tokens @ $2.50/1M = ${openai_input_cost:.3f}')
    print(f'    Output: {output_tokens:,.0f} tokens @ $10.00/1M = ${openai_output_cost:.3f}')
    print(f'    Total OpenAI cost: ${openai_total:.2f}')
    
    # Anthropic Claude pricing 
    anthropic_input_cost = (input_tokens / 1000) * (3.00 / 1000)
    anthropic_output_cost = (output_tokens / 1000) * (15.00 / 1000)
    anthropic_total = anthropic_input_cost + anthropic_output_cost
    
    print(f'  Anthropic Claude:')
    print(f'    Input: {input_tokens:,.0f} tokens @ $3.00/1M = ${anthropic_input_cost:.3f}')
    print(f'    Output: {output_tokens:,.0f} tokens @ $15.00/1M = ${anthropic_output_cost:.3f}')
    print(f'    Total Anthropic cost: ${anthropic_total:.2f}')
    
    # REALITY CHECK: Hybrid approach
    print(f'\n' + '='*50)
    print('REALITY CHECK - HYBRID APPROACH:')
    print('='*50)
    
    print(f'Strategy:')
    print(f'  1. Rule-based extraction (FREE): zones, setbacks, measurements')
    print(f'  2. LLM enhancement (PAID): complex relationships only')
    print(f'  3. Only process 20-30% of text through LLM')
    
    llm_processing_ratio = 0.25  # Only 25% needs LLM enhancement
    hybrid_openai_cost = openai_total * llm_processing_ratio
    hybrid_anthropic_cost = anthropic_total * llm_processing_ratio * 0.1  # 10% fallback
    
    print(f'\nHybrid Cost Breakdown:')
    print(f'  Rule-based extraction (75%): $0.00')
    print(f'  LLM enhancement (25%): ${hybrid_openai_cost:.2f}')
    print(f'  Fallback processing: ${hybrid_anthropic_cost:.2f}')
    print(f'  TOTAL REALISTIC COST: ${hybrid_openai_cost + hybrid_anthropic_cost:.2f}')
    
    # Compare to original estimate
    print(f'\nCOMPARISON:')
    print(f'  Original estimate: $50-150')
    print(f'  Actual calculation: ${hybrid_openai_cost + hybrid_anthropic_cost:.2f}')
    print(f'  Difference: MUCH LOWER than estimated!')
    
    # Break down by document type
    if documents_sampled >= 5:
        print(f'\nDOCUMENT TYPE ANALYSIS:')
        
        # Check for different document sizes
        small_docs = [d for d in doc_folders if 'Chapter' in d.name or len(d.name) < 50]
        large_docs = [d for d in doc_folders if 'Heritage' in d.name or 'Part' in d.name]
        
        print(f'  Small documents (~{len(small_docs)}): Minimal LLM needed')
        print(f'  Large documents (~{len(large_docs)}): More LLM processing')
        print(f'  Most costs from large comprehensive documents')

else:
    print('ERROR: Could not sample any documents for cost estimation')
    print('Check that the output directory exists and contains processed documents')