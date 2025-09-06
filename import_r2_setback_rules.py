#!/usr/bin/env python3
"""
Import R2 Setback Rules from Verified Legislation Data
====================================================
Import the verified R2 setback data from inner-west-compliance-rules.json
with full metadata and proper database structure
"""

import json
import sqlite3
from datetime import datetime

def import_r2_setback_rules():
    print("IMPORTING VERIFIED R2 SETBACK RULES FROM LEGISLATION PDFS")
    print("=" * 60)
    
    # Load the verified compliance rules
    with open('public/regulatory-data/inner-west-compliance-rules.json', 'r', encoding='utf-8') as f:
        compliance_data = json.load(f)
    
    print(f"Found {compliance_data['rule_count']} compliance rules")
    print(f"Generated: {compliance_data['generated_at']}")
    print(f"Method: {compliance_data['metadata']['method']}")
    print()
    
    # Connect to database
    conn = sqlite3.connect('nsw_planning.db')
    cursor = conn.cursor()
    
    # Create a dedicated table for verified compliance rules if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS verified_compliance_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_id TEXT UNIQUE NOT NULL,
            jurisdiction TEXT,
            authority TEXT,
            lga TEXT,
            zones TEXT,
            former_council TEXT,
            requirement_type TEXT,
            requirement_subtype TEXT,
            operator TEXT,
            value_numeric REAL,
            units TEXT,
            context TEXT,
            confidence TEXT,
            source_document TEXT,
            source_section TEXT,
            source_clause TEXT,
            source_url TEXT,
            effective_date TEXT,
            priority INTEGER,
            extraction_method TEXT,
            quality_score REAL,
            extracted_at TEXT,
            source_file TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    imported_count = 0
    r2_setback_count = 0
    
    # Process each rule
    for rule in compliance_data['rules']:
        rule_id = rule['id']
        jurisdiction = rule['jurisdiction']
        authority = rule['authority']
        
        # Extract applies_to information
        applies_to = rule['applies_to']
        lga = applies_to.get('lga', '')
        zones = json.dumps(applies_to.get('zones', []))  # Store as JSON array
        former_council = applies_to.get('former_council', '')
        
        # Process each requirement in the rule
        for req in rule['requirements']:
            requirement_type = req['type']
            requirement_subtype = req['subtype']
            operator = req['operator']
            value_numeric = req['value']
            units = req['units']
            context = req['context']
            confidence = req['confidence']
            
            # Extract source information
            source = rule['source']
            source_document = source['document']
            source_section = source['section']
            source_clause = source['clause']
            source_url = source['url']
            effective_date = source['effective_date']
            
            # Extract metadata
            priority = rule['priority']
            extraction_meta = rule['extraction_metadata']
            extraction_method = extraction_meta['method']
            quality_score = extraction_meta['quality_score']
            extracted_at = extraction_meta['extracted_at']
            source_file = extraction_meta['source_file']
            
            try:
                # Insert into verified_compliance_rules table
                cursor.execute('''
                    INSERT OR REPLACE INTO verified_compliance_rules (
                        rule_id, jurisdiction, authority, lga, zones, former_council,
                        requirement_type, requirement_subtype, operator, value_numeric,
                        units, context, confidence, source_document, source_section,
                        source_clause, source_url, effective_date, priority,
                        extraction_method, quality_score, extracted_at, source_file
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    rule_id, jurisdiction, authority, lga, zones, former_council,
                    requirement_type, requirement_subtype, operator, value_numeric,
                    units, context, confidence, source_document, source_section,
                    source_clause, source_url, effective_date, priority,
                    extraction_method, quality_score, extracted_at, source_file
                ))
                
                imported_count += 1
                
                # Count R2 setback rules specifically
                if 'R2' in zones and 'setback' in requirement_type:
                    r2_setback_count += 1
                    print(f"✓ Imported R2 setback: {rule_id}")
                    print(f"  {requirement_subtype} setback: {value_numeric} {units}")
                    print(f"  Authority: {authority} ({former_council})")
                    print(f"  Source: {source_document}")
                    print(f"  Quality: {quality_score} ({confidence})")
                    print()
                
            except sqlite3.Error as e:
                print(f"Error inserting rule {rule_id}: {e}")
    
    # Also create entries in regulatory_provisions for compatibility
    print("Creating regulatory_provisions entries for R2 setback rules...")
    
    cursor.execute('''
        SELECT rule_id, requirement_subtype, value_numeric, units, context,
               source_document, source_clause, authority, quality_score
        FROM verified_compliance_rules 
        WHERE zones LIKE '%R2%' 
        AND requirement_type = 'min_setback'
    ''')
    
    r2_rules = cursor.fetchall()
    provisions_created = 0
    
    for rule in r2_rules:
        rule_id, subtype, value, units, context, doc, clause, authority, quality = rule
        
        # Create a provision text that combines all the metadata
        provision_text = f"R2 Zone {subtype} setback requirement: minimum {value} {units}. {context}. Source: {doc}, {clause}. Authority: {authority}."
        
        try:
            cursor.execute('''
                INSERT INTO regulatory_provisions (
                    document_id, provision_text, zone, domain_classification,
                    confidence_score, authority_level, legal_source, clause_reference
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                rule_id,
                provision_text,
                'R2',
                'RESIDENTIAL_BUILDINGS',
                quality,
                'DCP',
                doc,
                clause
            ))
            provisions_created += 1
            
        except sqlite3.Error as e:
            print(f"Error creating provision for {rule_id}: {e}")
    
    conn.commit()
    
    print(f"IMPORT COMPLETE:")
    print(f"✓ Imported {imported_count} verified compliance rules")
    print(f"✓ Found {r2_setback_count} R2-specific setback rules")
    print(f"✓ Created {provisions_created} regulatory provisions")
    print()
    
    # Verify the import
    cursor.execute("SELECT COUNT(*) FROM verified_compliance_rules WHERE zones LIKE '%R2%'")
    r2_rules_total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE zone = 'R2' AND provision_text LIKE '%setback%'")
    r2_provisions = cursor.fetchone()[0]
    
    print(f"VERIFICATION:")
    print(f"✓ R2 rules in verified_compliance_rules: {r2_rules_total}")
    print(f"✓ R2 setback provisions in regulatory_provisions: {r2_provisions}")
    
    # Show summary of R2 setback values
    cursor.execute('''
        SELECT requirement_subtype, value_numeric, units, authority, former_council
        FROM verified_compliance_rules 
        WHERE zones LIKE '%R2%' 
        AND requirement_type = 'min_setback'
        ORDER BY former_council, requirement_subtype
    ''')
    
    setback_summary = cursor.fetchall()
    print()
    print("R2 SETBACK SUMMARY:")
    for subtype, value, units, auth, council in setback_summary:
        print(f"  {council} Council - {subtype}: {value} {units}")
    
    conn.close()
    return r2_setback_count

if __name__ == "__main__":
    result = import_r2_setback_rules()