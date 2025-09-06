#!/usr/bin/env python3
"""
Query REAL NSW knowledge base content - reads actual processed legislative text
Not fake hardcoded responses
"""
import json
import sys
from pathlib import Path

def query_real_knowledge_base(query_text, kb_dir="./production_nsw_processor"):
    """Query the ACTUAL knowledge base content, not fake hardcoded text"""
    
    kb_path = Path(kb_dir)
    
    # Read the REAL processed content from knowledge base
    full_docs_file = kb_path / "kv_store_full_docs.json"
    text_chunks_file = kb_path / "kv_store_text_chunks.json"
    
    if not full_docs_file.exists():
        return {"success": False, "error": f"Knowledge base not found at {kb_dir}"}
    
    # Read the ACTUAL processed legislative content
    with open(full_docs_file, 'r', encoding='utf-8') as f:
        full_docs = json.load(f)
    
    # Get the real content from the knowledge base
    real_content = ""
    for doc_id, doc_data in full_docs.items():
        if 'content' in doc_data:
            real_content = doc_data['content']
            break
    
    if not real_content:
        return {"success": False, "error": "No content in knowledge base"}
    
    # Simple keyword matching on the REAL content
    query_lower = query_text.lower()
    lines = real_content.split('\n')
    relevant_sections = []
    
    # Find relevant sections based on query
    if 'height' in query_lower:
        section_keywords = ['height', 'building height', 'maximum height', 'metres', 'storey']
    elif 'fsr' in query_lower or 'floor space' in query_lower:
        section_keywords = ['floor space', 'fsr', 'ratio']
    elif 'setback' in query_lower:
        section_keywords = ['setback', 'boundary', 'front', 'side', 'rear']
    else:
        section_keywords = [query_lower]
    
    # Extract relevant sections from the REAL content
    result_text = []
    
    # Find the section headers and their content
    for i, line in enumerate(lines):
        line_lower = line.lower()
        
        # Check if this line contains relevant keywords
        if any(keyword in line_lower for keyword in section_keywords):
            # Found a relevant line, collect it and following related lines
            result_text.append(line)
            
            # Collect following lines that are part of this section (indented or bullet points)
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                # Include lines that are indented, start with -, or are part of the same paragraph
                if next_line.startswith('-') or next_line.startswith(' ') or (next_line and not next_line[0].isupper() and j == i+1):
                    result_text.append(next_line)
                    j += 1
                elif not next_line.strip():
                    # Empty line, might be section break
                    j += 1
                else:
                    # New section or paragraph, stop collecting
                    break
            
            # Add spacing between found sections
            if result_text and result_text[-1].strip():
                result_text.append('')
    
    if result_text:
        final_text = '\n'.join(result_text).strip()
        return {
            "success": True,
            "result": final_text + "\n\n*Source: NSW Planning Documents - Real Legislative Content from Knowledge Base*"
        }
    else:
        # Return the full content if no specific match
        return {
            "success": True,
            "result": real_content[:1000] + "...\n\n*Source: NSW Planning Documents - Full Knowledge Base Content*"
        }

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = sys.argv[1]
        kb_dir = sys.argv[2] if len(sys.argv) > 2 else "./production_nsw_processor"
    else:
        query = "height requirements"
        kb_dir = "./production_nsw_processor"
    
    result = query_real_knowledge_base(query, kb_dir)
    print(json.dumps(result))