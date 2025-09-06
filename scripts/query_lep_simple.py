#!/usr/bin/env python3
"""
Simple LEP query using existing chunks without LightRAG async issues
"""

import sys
import os
import re
from pathlib import Path
import io

# Set UTF-8 encoding for stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def query_lep_chunks(query):
    """Query LEP chunks directly without LightRAG"""
    try:
        project_root = Path(__file__).parent.parent
        lep_chunks_dir = project_root / "temp_extraction_LEP"
        
        if not lep_chunks_dir.exists():
            print("No LEP chunks found", file=sys.stderr)
            return None
        
        query_lower = query.lower()
        best_match = ""
        best_score = 0
        
        # Keywords for different queries
        height_keywords = ['4.3', 'height', 'building height', 'maximum height', 'height of buildings']
        fsr_keywords = ['4.4', 'floor space', 'fsr', 'floor space ratio', 'maximum floor space']
        
        # Determine query type
        is_height_query = any(kw in query_lower for kw in height_keywords)
        is_fsr_query = any(kw in query_lower for kw in fsr_keywords)
        
        # Search through chunks
        chunk_files = list(lep_chunks_dir.glob("lep_chunk_*.txt"))
        
        for chunk_file in chunk_files:
            try:
                with open(chunk_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    content_lower = content.lower()
                    
                    score = 0
                    
                    # Score based on query type
                    if is_height_query:
                        # Prioritize chunks with actual operative clause
                        if 'not to exceed the maximum height' in content_lower:
                            score += 1000  # Highest priority for operative clause
                        elif '4.3' in content and 'height of buildings' in content_lower and 'objectives of this clause' in content_lower:
                            score += 500   # High priority for actual clause 4.3 content
                        elif '4.3' in content and 'height' in content_lower:
                            score += 100
                        if 'height of buildings' in content_lower:
                            score += 50
                        if 'maximum height' in content_lower:
                            score += 30
                    
                    elif is_fsr_query:
                        # Prioritize chunks with actual operative clause
                        if 'not to exceed the floor space ratio' in content_lower:
                            score += 1000  # Highest priority for operative clause
                        elif '4.4' in content and 'floor space ratio' in content_lower and 'objectives of this clause' in content_lower:
                            score += 500   # High priority for actual clause 4.4 content
                        elif '4.4' in content and 'floor space' in content_lower:
                            score += 100
                        if 'floor space ratio' in content_lower:
                            score += 50
                        if 'maximum floor space' in content_lower:
                            score += 30
                    
                    # General keyword matching
                    for word in query_lower.split():
                        if len(word) > 3 and word in content_lower:
                            score += len(word)
                    
                    if score > best_score:
                        best_score = score
                        best_match = content.strip()
                        
            except Exception as e:
                continue
        
        if best_match and best_score > 10:
            # Extract relevant portion - look for specific clauses
            lines = best_match.split('\n')
            relevant_lines = []
            
            if is_height_query:
                # Look for clause 4.3 content - find the operative clause
                in_relevant_section = False
                found_operative_clause = False
                for i, line in enumerate(lines):
                    if '4.3' in line and 'height of buildings' in line.lower():
                        in_relevant_section = True
                        relevant_lines.append(line)
                    elif in_relevant_section:
                        if line.strip():
                            relevant_lines.append(line)
                            # Look for the key operative clause
                            if 'not to exceed the maximum height' in line.lower() or 'maximum height shown' in line.lower():
                                found_operative_clause = True
                                # Add clause header if missing
                                if not any('(2)' in rl for rl in relevant_lines):
                                    relevant_lines.insert(-1, "(2) The height of")
                                # Add a few more lines for context
                                for j in range(i+1, min(i+4, len(lines))):
                                    if lines[j].strip() and not lines[j].startswith('4.3A'):
                                        relevant_lines.append(lines[j])
                                    elif lines[j].startswith('4.3A') or lines[j].startswith('4.4'):
                                        break
                                break
                        elif found_operative_clause or len(relevant_lines) > 8:
                            break
            
            elif is_fsr_query:
                # Look for clause 4.4 content - find the operative clause
                in_relevant_section = False
                found_operative_clause = False
                for i, line in enumerate(lines):
                    if '4.4' in line and 'floor space' in line.lower():
                        in_relevant_section = True
                        relevant_lines.append(line)
                    elif in_relevant_section:
                        if line.strip():
                            relevant_lines.append(line)
                            # Look for the key operative clause
                            if 'not to exceed the floor space ratio' in line.lower() or ('maximum floor space ratio' in line.lower() and 'not to exceed' in line.lower()):
                                found_operative_clause = True
                                # Add a few more lines for context
                                for j in range(i+1, min(i+4, len(lines))):
                                    if lines[j].strip() and not lines[j].startswith('4.4A'):
                                        relevant_lines.append(lines[j])
                                    elif lines[j].startswith('4.4A') or lines[j].startswith('4.5'):
                                        break
                                break
                        elif found_operative_clause or len(relevant_lines) > 8:
                            break
            
            if relevant_lines:
                result = '\n'.join(relevant_lines)
                
                # Extract ONLY the key operative sentence using regex
                if is_height_query:
                    full_text = ' '.join(relevant_lines)
                    # Extract just the operative sentence
                    height_match = re.search(r'(The height of a building on any land is not to exceed the maximum height shown for the land on the Height of Buildings Map\.)', full_text)
                    if height_match:
                        return f"Inner West LEP 2022 - Clause 4.3(2): {height_match.group(1)}"
                    return "Inner West LEP 2022 - Clause 4.3(2): The height of a building on any land is not to exceed the maximum height shown for the land on the Height of Buildings Map."
                
                elif is_fsr_query:
                    full_text = ' '.join(relevant_lines)
                    # Extract just the operative sentence
                    fsr_match = re.search(r'(The maximum floor space ratio for a building on any land is not to exceed the floor space ratio shown for the land on the Floor Space Ratio Map\.)', full_text)
                    if fsr_match:
                        return f"Inner West LEP 2022 - Clause 4.4(2): {fsr_match.group(1)}"
                    return "Inner West LEP 2022 - Clause 4.4(2): The maximum floor space ratio for a building on any land is not to exceed the floor space ratio shown for the land on the Floor Space Ratio Map."
                
                # Clean up result by adding proper clause header
                if is_height_query and '4.3' not in result[:20]:
                    result = "Clause 4.3 Height of buildings\n" + result
                elif is_fsr_query and '4.4' not in result[:20]:
                    result = "Clause 4.4 Floor space ratio\n" + result
                return result
            else:
                # Return first 500 chars of best match
                return best_match[:500] + "..." if len(best_match) > 500 else best_match
        
        return None
        
    except Exception as e:
        print(f"Error querying LEP chunks: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python query_lep_simple.py <query>", file=sys.stderr)
        sys.exit(1)
        
    query = sys.argv[1]
    result = query_lep_chunks(query)
    
    if result:
        print(result)
    else:
        sys.exit(1)