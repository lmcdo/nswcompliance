#!/usr/bin/env python3
"""
Convert AutoSchemaKG JSON output to CSV format expected by API
Processes database-driven AutoSchema output into nodes and edges CSV files
"""

import json
import csv
import os
from pathlib import Path
from typing import Dict, List, Set
import re

def process_json_line_by_line(file_path: str) -> List[Dict]:
    """Process JSON file that may contain multiple JSON objects"""
    results = []
    
    # Try different encodings
    encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']
    content = None
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read().strip()
            break
        except UnicodeDecodeError:
            continue
    
    if content is None:
        print(f"Could not read {file_path} with any encoding")
        return results
        
    # Try to parse as single JSON first
    try:
        data = json.loads(content)
        if isinstance(data, list):
            results.extend(data)
        else:
            results.append(data)
        return results
    except json.JSONDecodeError:
        pass
    
    # If single JSON fails, try line-by-line
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        results.append(data)
                    except json.JSONDecodeError as e:
                        print(f"Skipping invalid JSON at line {line_num}: {str(e)[:100]}")
            break
        except UnicodeDecodeError:
            continue
    
    return results

def extract_relationships_from_autoschema(json_files: List[str]) -> tuple[List[Dict], List[Dict]]:
    """Extract nodes and relationships from AutoSchema JSON output"""
    nodes = {}  # Use dict to deduplicate by ID
    edges = []
    
    for json_file in json_files:
        print(f"Processing {json_file}...")
        data_list = process_json_line_by_line(json_file)
        
        for data in data_list:
            if isinstance(data, dict) and 'triples' in data:
                # Process triples from AutoSchema output
                for triple in data['triples']:
                    if isinstance(triple, dict):
                        head = triple.get('head', '').strip()
                        relation = triple.get('relation', '').strip()
                        tail = triple.get('tail', '').strip()
                        
                        if head and relation and tail:
                            # Create nodes
                            head_id = clean_node_id(head)
                            tail_id = clean_node_id(tail)
                            
                            nodes[head_id] = {
                                'name:ID': head_id,
                                'type': infer_node_type(head),
                                'concepts': '',
                                'synsets': '',
                                ':LABEL': 'Entity'
                            }
                            
                            nodes[tail_id] = {
                                'name:ID': tail_id,
                                'type': infer_node_type(tail),
                                'concepts': '',
                                'synsets': '',
                                ':LABEL': 'Entity'
                            }
                            
                            # Create edge
                            edges.append({
                                ':START_ID': head_id,
                                ':END_ID': tail_id,
                                'relation': relation,
                                'concepts': '',
                                'synsets': '',
                                ':TYPE': 'RELATION'
                            })
    
    return list(nodes.values()), edges

def clean_node_id(text: str) -> str:
    """Clean text to create valid node ID"""
    if not text:
        return ''
    # Remove extra whitespace and normalize
    cleaned = ' '.join(text.split())
    # Truncate if too long
    if len(cleaned) > 200:
        cleaned = cleaned[:200] + "..."
    return cleaned

def infer_node_type(text: str) -> str:
    """Infer node type from text content"""
    text_lower = text.lower()
    
    # Check for clause patterns
    clause_patterns = [
        r'\bclause\s+\d+', r'\bc\d+\b', r'\bp\d+\b', 
        r'\bds\d+', r'\bpc-\d+', r'\b\d+\.\d+\.\d+'
    ]
    
    for pattern in clause_patterns:
        if re.search(pattern, text_lower):
            return 'clause'
    
    # Check for regulatory terms
    regulatory_terms = ['development', 'setback', 'height', 'fsr', 'zone', 'control', 'requirement']
    if any(term in text_lower for term in regulatory_terms):
        return 'regulatory_concept'
    
    return 'entity'

def write_csv_files(nodes: List[Dict], edges: List[Dict], output_dir: str):
    """Write nodes and edges to CSV files"""
    os.makedirs(output_dir, exist_ok=True)
    
    nodes_file = os.path.join(output_dir, "triple_nodes_nsw_planning_docs_from_json_without_emb.csv")
    edges_file = os.path.join(output_dir, "triple_edges_nsw_planning_docs_from_json_without_emb.csv")
    
    # Write nodes CSV
    if nodes:
        with open(nodes_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['name:ID', 'type', 'concepts', 'synsets', ':LABEL']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(nodes)
        print(f"Created {nodes_file} with {len(nodes)} nodes")
    
    # Write edges CSV
    if edges:
        with open(edges_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [':START_ID', ':END_ID', 'relation', 'concepts', 'synsets', ':TYPE']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(edges)
        print(f"Created {edges_file} with {len(edges)} edges")

def main():
    """Convert AutoSchema JSON output to CSV format for API integration"""
    print("Converting AutoSchema JSON output to CSV format...")
    
    # Find JSON files
    json_dir = "autoschema_database_output/kg_output/kg_extraction"
    json_files = []
    
    if os.path.exists(json_dir):
        for file in os.listdir(json_dir):
            if file.endswith('.json'):
                json_files.append(os.path.join(json_dir, file))
    
    if not json_files:
        print(f"No JSON files found in {json_dir}")
        return
    
    print(f"Found {len(json_files)} JSON files to process")
    
    # Extract relationships
    nodes, edges = extract_relationships_from_autoschema(json_files)
    
    print(f"Extracted {len(nodes)} unique nodes and {len(edges)} relationships")
    
    # Create output directory expected by API
    output_dir = "autoschemakg_output/triples_csv"
    
    # Write CSV files
    write_csv_files(nodes, edges, output_dir)
    
    print("\nConversion complete!")
    print(f"API can now access:")
    print(f"  - Nodes: {output_dir}/triple_nodes_nsw_planning_docs_from_json_without_emb.csv")
    print(f"  - Edges: {output_dir}/triple_edges_nsw_planning_docs_from_json_without_emb.csv")

if __name__ == "__main__":
    main()