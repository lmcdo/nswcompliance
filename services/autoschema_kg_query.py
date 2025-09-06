#!/usr/bin/env python3
"""
AutoSchemaKG Query Interface
Connects to the knowledge graph CSV files to retrieve clause information
"""

import csv
import os
from typing import Dict, List, Optional

class AutoSchemaKGQuery:
    def __init__(self, kg_path: str = "autoschemakg_output/triples_csv"):
        self.kg_path = kg_path
        self.nodes_file = os.path.join(kg_path, "triple_nodes_nsw_planning_docs_from_json_without_emb.csv")
        self.edges_file = os.path.join(kg_path, "triple_edges_nsw_planning_docs_from_json_without_emb.csv")
        
        # Load nodes and edges
        self.nodes = self._load_nodes()
        self.edges = self._load_edges()
    
    def _load_nodes(self) -> Dict[str, Dict]:
        """Load all nodes from the knowledge graph"""
        nodes = {}
        
        if not os.path.exists(self.nodes_file):
            print(f"Nodes file not found: {self.nodes_file}")
            return nodes
            
        try:
            with open(self.nodes_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    node_id = row.get('name:ID', '')
                    nodes[node_id] = {
                        'type': row.get('type', ''),
                        'concepts': row.get('concepts', ''),
                        'synsets': row.get('synsets', ''),
                        'label': row.get(':LABEL', '')
                    }
        except Exception as e:
            print(f"Error loading nodes: {e}")
            
        return nodes
    
    def _load_edges(self) -> List[Dict]:
        """Load all edges from the knowledge graph"""
        edges = []
        
        if not os.path.exists(self.edges_file):
            print(f"Edges file not found: {self.edges_file}")
            return edges
            
        try:
            with open(self.edges_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    edges.append({
                        'start': row.get(':START_ID', ''),
                        'end': row.get(':END_ID', ''),
                        'relation': row.get('relation', ''),
                        'concepts': row.get('concepts', ''),
                        'synsets': row.get('synsets', ''),
                        'type': row.get(':TYPE', '')
                    })
        except Exception as e:
            print(f"Error loading edges: {e}")
            
        return edges
    
    def find_clause_node(self, clause_ref: str) -> Optional[Dict]:
        """Find a clause node by reference"""
        # Normalize the clause reference for search
        # Convert "Clause 4.2.4(c)" to variations like "4.2.4.3", "4.2.4c", etc.
        search_variations = [clause_ref]
        
        # Add format variations
        if '(' in clause_ref and ')' in clause_ref:
            # "Clause 4.2.4(c)" -> "Clause 4.2.4.3" (assuming c=3, b=2, etc.)
            letter_map = {'a': '1', 'b': '2', 'c': '3', 'd': '4', 'e': '5'}
            for letter, number in letter_map.items():
                if f'({letter})' in clause_ref.lower():
                    dot_version = clause_ref.replace(f'({letter})', f'.{number}').replace(f'({letter.upper()})', f'.{number}')
                    search_variations.append(dot_version)
        
        # Look for matches with any variation
        for variation in search_variations:
            for node_id, node_data in self.nodes.items():
                if self._clause_matches(variation, node_id):
                    return {
                        'id': node_id,
                        'content': node_id,  # The node ID contains the clause text
                        'type': node_data['type'],
                        'concepts': node_data['concepts'],
                        'label': node_data['label']
                    }
        
        return None
    
    def _clause_matches(self, clause_ref: str, node_id: str) -> bool:
        """Check if a clause reference matches a node ID"""
        clause_lower = clause_ref.lower()
        node_lower = node_id.lower()
        
        # Must contain the clause reference
        if clause_lower not in node_lower:
            return False
            
        # Must look like clause content (has regulatory keywords)
        regulatory_indicators = ['setback', 'height', 'control', ':', 'development', 'building', 'clause']
        if any(indicator in node_lower for indicator in regulatory_indicators):
            return True
            
        return False
    
    def find_setback_clauses(self) -> List[Dict]:
        """Find all setback-related clauses with real clause numbers extracted"""
        setback_clauses = []
        
        for node_id, node_data in self.nodes.items():
            if ('setback' in node_id.lower() and 'clause' in node_id.lower()) or \
               ('clause' in node_id.lower() and 'setback' in node_id.lower()):
                
                # Extract real clause information from the content
                extracted = self.extract_clause_text(node_id)
                
                setback_clauses.append({
                    'id': node_id,
                    'content': node_id,
                    'type': node_data['type'],
                    'concepts': node_data['concepts'],
                    'label': node_data['label'],
                    'real_clause_number': extracted['clause_number'],
                    'real_clause_text': extracted['clause_text']
                })
        
        # Sort clauses to prioritize ones with real clause numbers (not "Unknown")
        setback_clauses.sort(key=lambda x: (
            x['real_clause_number'] == 'Unknown',  # False comes first, so real clauses first
            x['id']  # Then sort alphabetically by ID
        ))
        
        return setback_clauses
    
    def get_clause_relationships(self, clause_ref: str) -> List[Dict]:
        """Get relationships for a specific clause"""
        relationships = []
        
        for edge in self.edges:
            if clause_ref.lower() in edge['start'].lower() or \
               clause_ref.lower() in edge['end'].lower():
                relationships.append(edge)
        
        return relationships
    
    def extract_clause_text(self, node_content: str) -> Dict:
        """Extract structured information from clause node content"""
        # Parse clause node content to find REAL clause numbers like:
        # "Clause 4.2.4(b) - setback (development_control): 4.2.4.2 Building heights"
        # We want to extract the REAL "4.2.4.2" from the content, not the fake "4.2.4(b)"
        
        import re
        clause_number = ""
        clause_type = ""
        clause_text = ""
        source_doc = ""
        
        # Look for real clause numbers in the content (format: x.x.x.x)
        real_clause_match = re.search(r'(\d+\.\d+\.\d+\.\d+)\s+([^,]+)', node_content)
        if real_clause_match:
            clause_number = f"Clause {real_clause_match.group(1)}"
            clause_text = real_clause_match.group(2).strip()
            clause_type = "regulatory_provision"
        else:
            # Fallback: try to extract from standard format
            if ' - ' in node_content and ':' in node_content:
                # Split on ' - ' to get clause number part
                parts = node_content.split(' - ', 1)
                if len(parts) >= 2:
                    # Look for the REAL clause number in the content after the colon
                    rest = parts[1]
                    if ':' in rest:
                        type_part, text_part = rest.split(':', 1)
                        
                        # Extract type from parentheses
                        if '(' in type_part and ')' in type_part:
                            clause_type = type_part.split('(')[0].strip()
                        
                        # Look for real clause number in the text part
                        real_clause_in_text = re.search(r'(\d+\.\d+\.\d+\.\d+)', text_part)
                        if real_clause_in_text:
                            clause_number = f"Clause {real_clause_in_text.group(1)}"
                            # Extract the actual regulatory text after the clause number
                            remaining_text = text_part.split(real_clause_in_text.group(1), 1)
                            if len(remaining_text) > 1:
                                clause_text = remaining_text[1].strip()
                            else:
                                clause_text = text_part.strip()
                        else:
                            clause_text = text_part.strip()
        
        # If we still couldn't extract anything meaningful, use the whole content as text
        if not clause_text:
            clause_text = node_content
            
        # Clean up clause text
        clause_text = clause_text.replace('..', '.').replace('  ', ' ').strip()
        
        # Additional cleaning for common patterns
        if clause_text.startswith('- height_limit:'):
            clause_text = clause_text.replace('- height_limit:', '').strip()
            if clause_text.lower() == 'building heights':
                clause_text = 'Specifies building height controls and limitations for development'
        elif clause_text.startswith('- setback:'):
            clause_text = clause_text.replace('- setback:', '').strip()
            if clause_text.lower() == 'building setbacks':
                clause_text = 'Specifies minimum setback distances from property boundaries'
        elif clause_text.startswith('- fsr_control:'):
            clause_text = clause_text.replace('- fsr_control:', '').strip()
            if 'floor space ratio' in clause_text.lower():
                clause_text = 'Specifies floor space ratio and site coverage controls'
            
        return {
            'clause_number': clause_number or 'Unknown',
            'clause_type': clause_type or 'regulatory_provision',
            'clause_text': clause_text,
            'source': 'NSW Planning Documents (AutoSchemaKG Knowledge Graph)'
        }

# Usage example
if __name__ == "__main__":
    kg = AutoSchemaKGQuery()
    
    print(f"Loaded {len(kg.nodes)} nodes and {len(kg.edges)} edges")
    
    # Test setback clause search
    setback_clauses = kg.find_setback_clauses()
    print(f"\nFound {len(setback_clauses)} setback clauses:")
    for clause in setback_clauses[:3]:
        print(f"- {clause['id']}")
    
    # Test specific clause lookup
    clause = kg.find_clause_node("4.2.4")
    if clause:
        print(f"\nFound clause: {clause['content']}")
        extracted = kg.extract_clause_text(clause['content'])
        print(f"Extracted: {extracted}")