#!/usr/bin/env python3
"""
Extract R-Zone Data (R1, R2, R3, R4, R5) from JSON Files
========================================================
Focus specifically on residential zones with setback requirements
"""

import json
import sqlite3
import re
import os
from pathlib import Path

def extract_r_zones():
    print("EXTRACTING R-ZONE DATA FROM JSON FILES")
    print("=" * 50)
    
    r_zone_provisions = {}
    
    # Target files that likely contain residential zone data
    target_files = [
        # Compliance results with specific rules
        'compliance_result.json',
        
        # AutoSchemaKG data with planning documents
        'autoschemakg_data_ollama_final/nsw_planning_docs_015.json',
        
        # Multimodal relationships
        'multimodal_relationships_complete.json',
        
        # Any files with "residential" in the name
    ]
    
    # Also search for files containing residential terms
    for json_file in Path('.').rglob('*.json'):
        if json_file.is_file() and json_file.stat().st_size < 20_000_000:  # Skip huge files
            file_name = str(json_file).lower()
            if any(term in file_name for term in ['residential', 'low_density', 'medium_density', 'high_density', 'r1', 'r2', 'r3', 'r4', 'r5']):
                target_files.append(str(json_file))
    
    target_files = list(set(target_files))  # Remove duplicates
    print(f"Searching {len(target_files)} files for R-zone data...")
    
    for json_file in target_files:
        if not os.path.exists(json_file):
            continue
            
        try:
            print(f"Processing {json_file}...")
            
            with open(json_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Look for R-zone patterns in the raw text first
            r_zone_patterns = [
                r'(R[1-5])[^\w]*(?:.*?)(?:setback|distance|minimum)[^\d]*(\d+(?:\.\d+)?)\s*(?:metres?|meters?|m)',
                r'Zone (R[1-5])[^\w]*(?:.*?)(?:setback|distance|minimum)[^\d]*(\d+(?:\.\d+)?)\s*(?:metres?|meters?|m)',
                r'(R[1-5])\s*[-–—]\s*(?:Low|Medium|High|General)?\s*(?:Density)?\s*Residential[^\d]*(?:setback|distance|minimum)[^\d]*(\d+(?:\.\d+)?)\s*(?:metres?|meters?|m)',
                r'(?:setback|distance|minimum)[^\d]*(\d+(?:\.\d+)?)\s*(?:metres?|meters?|m)[^\w]*(?:.*?)Zone (R[1-5])',
                r'(?:setback|distance|minimum)[^\d]*(\d+(?:\.\d+)?)\s*(?:metres?|meters?|m)[^\w]*(?:.*?)(R[1-5])\s*[-–—]\s*(?:Low|Medium|High|General)?\s*(?:Density)?\s*Residential',
            ]
            
            for pattern in r_zone_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    if len(match) == 2:
                        # Determine which is zone and which is measurement
                        if re.match(r'^R[1-5]$', match[0]):
                            zone, measurement = match[0], match[1]
                        else:
                            zone, measurement = match[1], match[0]
                        
                        key = f"{zone}_{json_file}"
                        if key not in r_zone_provisions:
                            r_zone_provisions[key] = []
                        
                        # Get context around the match
                        match_pos = content.find(f"{zone}")
                        if match_pos > 0:
                            context_start = max(0, match_pos - 100)
                            context_end = min(len(content), match_pos + 200)
                            context = content[context_start:context_end]
                        else:
                            context = f"{zone} setback {measurement}m"
                        
                        r_zone_provisions[key].append({
                            'zone': zone,
                            'measurement': float(measurement),
                            'document': json_file,
                            'context': context.replace('\\n', ' ').replace('\\t', ' ')[:200]
                        })
            
            # Now try to parse as JSON for structured data
            try:
                data = json.loads(content)
                
                # Process different JSON structures
                if isinstance(data, dict):
                    # Look for compliance results or rule structures
                    if 'results' in data:
                        for result in data['results']:
                            if isinstance(result, dict) and 'rule_id' in result:
                                rule_id = result.get('rule_id', '')
                                if 'R2' in rule_id or 'R1' in rule_id or 'R3' in rule_id:
                                    # Extract zone from rule ID
                                    zone_match = re.search(r'(R[1-5])', rule_id)
                                    if zone_match:
                                        zone = zone_match.group(1)
                                        
                                        # Get setback value
                                        if 'required_value' in result:
                                            measurement = result['required_value']
                                            
                                            key = f"{zone}_{json_file}_rule"
                                            if key not in r_zone_provisions:
                                                r_zone_provisions[key] = []
                                            
                                            r_zone_provisions[key].append({
                                                'zone': zone,
                                                'measurement': float(measurement),
                                                'document': json_file,
                                                'context': result.get('regulatory_text', rule_id)[:200],
                                                'rule_id': rule_id,
                                                'confidence': result.get('confidence', 'UNKNOWN'),
                                                'requirement_type': result.get('requirement_type', 'setback')
                                            })
                    
                    # Look for text content in various structures
                    text_fields = ['text', 'content', 'regulatory_text', 'provision_text']
                    for field in text_fields:
                        if field in data:
                            text_content = str(data[field])
                            # Apply same pattern matching to structured text
                            for pattern in r_zone_patterns:
                                matches = re.findall(pattern, text_content, re.IGNORECASE | re.DOTALL)
                                for match in matches:
                                    if len(match) == 2:
                                        if re.match(r'^R[1-5]$', match[0]):
                                            zone, measurement = match[0], match[1]
                                        else:
                                            zone, measurement = match[1], match[0]
                                        
                                        key = f"{zone}_{json_file}_structured"
                                        if key not in r_zone_provisions:
                                            r_zone_provisions[key] = []
                                        
                                        r_zone_provisions[key].append({
                                            'zone': zone,
                                            'measurement': float(measurement),
                                            'document': json_file,
                                            'context': text_content[:200]
                                        })
                
                elif isinstance(data, list):
                    # Process list items
                    for item in data:
                        if isinstance(item, dict):
                            # Look for text fields
                            for field in ['text', 'content', 'table_body']:
                                if field in item:
                                    text_content = str(item[field])
                                    # Apply pattern matching
                                    for pattern in r_zone_patterns:
                                        matches = re.findall(pattern, text_content, re.IGNORECASE | re.DOTALL)
                                        for match in matches:
                                            if len(match) == 2:
                                                if re.match(r'^R[1-5]$', match[0]):
                                                    zone, measurement = match[0], match[1]
                                                else:
                                                    zone, measurement = match[1], match[0]
                                                
                                                key = f"{zone}_{json_file}_list"
                                                if key not in r_zone_provisions:
                                                    r_zone_provisions[key] = []
                                                
                                                r_zone_provisions[key].append({
                                                    'zone': zone,
                                                    'measurement': float(measurement),
                                                    'document': json_file,
                                                    'context': text_content[:200]
                                                })
                            
            except json.JSONDecodeError:
                # File is not valid JSON, but we already processed it as text
                pass
                
        except Exception as e:
            print(f"Error processing {json_file}: {e}")
            continue
    
    print(f"\nFound {len(r_zone_provisions)} R-zone provisions")
    
    # Display findings
    for key, provisions in r_zone_provisions.items():
        if provisions:
            zone = provisions[0]['zone']
            doc = provisions[0]['document']
            measurements = [p['measurement'] for p in provisions]
            print(f"\n{zone} in {doc}:")
            print(f"  Setbacks: {sorted(set(measurements))} metres")
            if 'rule_id' in provisions[0]:
                print(f"  Rule: {provisions[0]['rule_id']}")
                print(f"  Type: {provisions[0].get('requirement_type', 'N/A')}")
                print(f"  Confidence: {provisions[0].get('confidence', 'N/A')}")
            print(f"  Context: {provisions[0]['context'][:150]}...")
    
    # Update database with R-zone data
    if r_zone_provisions:
        print(f"\nUpdating database with {len(r_zone_provisions)} R-zone relationships...")
        conn = sqlite3.connect('nsw_planning.db')
        cursor = conn.cursor()
        
        updates_made = 0
        
        try:
            for key, provisions in r_zone_provisions.items():
                if not provisions:
                    continue
                    
                zone = provisions[0]['zone']
                document = provisions[0]['document']
                
                # Update provisions that mention this R-zone
                cursor.execute("""
                    UPDATE regulatory_provisions 
                    SET zone = ?
                    WHERE (provision_text LIKE ? OR provision_text LIKE ? OR document_id LIKE ?)
                    AND (zone IS NULL OR zone = '')
                """, (
                    zone,
                    f'%{zone}%',
                    f'%{zone} %',
                    f'%{document.replace(".json", "").replace("_", "%")}%'
                ))
                
                rows_updated = cursor.rowcount
                if rows_updated > 0:
                    print(f"Updated {rows_updated} records with zone {zone}")
                    updates_made += rows_updated
            
            conn.commit()
            
            # Check final results
            cursor.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE zone LIKE 'R%' AND zone IS NOT NULL AND zone != ''")
            r_zone_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE zone IS NOT NULL AND zone != ''")
            total_zone_count = cursor.fetchone()[0]
            
            print(f"\nR-ZONE RESULTS:")
            print(f"R-zone records: {r_zone_count}/{total_zone_count}")
            print(f"New R-zone updates: {updates_made}")
            
            return r_zone_count
            
        except Exception as e:
            print(f"Database error: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()
    
    return 0

if __name__ == "__main__":
    extract_r_zones()