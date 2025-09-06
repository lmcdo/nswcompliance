#!/usr/bin/env python3
"""
CRITICAL: Split regulatory_refs into proper normalized tables
This is the main factorization that should have been done originally
"""

import sqlite3
from datetime import datetime
import os

def factorize_regulatory_refs():
    print("FACTORIZING regulatory_refs INTO NORMALIZED TABLES")
    print("=" * 60)
    
    conn = sqlite3.connect('nsw_planning.db')
    cursor = conn.cursor()
    
    # Get original count
    cursor.execute("SELECT COUNT(*) FROM regulatory_refs")
    original_count = cursor.fetchone()[0]
    print(f"Original regulatory_refs count: {original_count:,}")
    
    factorization_stats = {}
    
    # STEP 1: Move FORMAL PROVISIONS to regulatory_provisions_clean
    print("\n1. Creating regulatory_provisions_clean...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS regulatory_provisions_clean AS
        SELECT 
            id, document_id, ref_type as provision_type, ref_number, 
            ref_context as provision_text, page_number, section_header, 
            text_level, 'formal_provision' as category
        FROM regulatory_refs 
        WHERE ref_type LIKE 'formal_%' 
           OR ref_type LIKE 'provision_%'
           OR ref_type = 'clause|section'
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM regulatory_provisions_clean")
    provisions_count = cursor.fetchone()[0]
    factorization_stats['regulatory_provisions_clean'] = provisions_count
    print(f"   Moved {provisions_count:,} formal provisions")
    
    # STEP 2: Move CONTEXTUAL GUIDANCE to contextual_guidance_real  
    print("\n2. Creating contextual_guidance_real...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contextual_guidance_real AS
        SELECT 
            id, document_id, ref_type as guidance_type, ref_number as guidance_title,
            ref_context as guidance_text, page_number, section_header, 
            text_level, 'contextual_guidance' as category
        FROM regulatory_refs
        WHERE ref_type LIKE 'context_%'
           OR ref_type LIKE 'informal_%'
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM contextual_guidance_real")
    guidance_count = cursor.fetchone()[0]
    factorization_stats['contextual_guidance_real'] = guidance_count
    print(f"   Moved {guidance_count:,} contextual guidance entries")
    
    # STEP 3: Move RELATIONSHIPS to kg_relationships_from_refs
    print("\n3. Creating kg_relationships_from_refs...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kg_relationships_from_refs AS
        SELECT 
            id, document_id, ref_type as relationship_type, 
            ref_context as relationship_context, page_number, section_header,
            ref_number as relationship_summary, 'regulatory_ref_relationship' as category
        FROM regulatory_refs
        WHERE ref_type LIKE 'relationship_%'
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM kg_relationships_from_refs")
    ref_relationships_count = cursor.fetchone()[0]
    factorization_stats['kg_relationships_from_refs'] = ref_relationships_count
    print(f"   Moved {ref_relationships_count:,} reference relationships")
    
    # STEP 4: Move VISUAL ELEMENTS to visual_elements_real
    print("\n4. Creating visual_elements_real...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS visual_elements_real AS
        SELECT 
            id, document_id, ref_type as visual_type,
            ref_context as visual_description, page_number, section_header,
            ref_number as visual_caption, 'visual_element' as category
        FROM regulatory_refs
        WHERE ref_type LIKE 'autoschema_%'
           OR ref_type = 'visual_reference'
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM visual_elements_real")
    visual_count = cursor.fetchone()[0]
    factorization_stats['visual_elements_real'] = visual_count
    print(f"   Moved {visual_count:,} visual elements")
    
    # STEP 5: Create development_controls_enhanced from provision data
    print("\n5. Enhancing development_controls...")
    cursor.execute('''
        INSERT OR IGNORE INTO development_controls 
        (provision_id, control_type, control_subtype, value_text, unit, 
         zone_applicable, conditions, confidence_score, extraction_method)
        SELECT 
            rpc.id, 
            CASE 
                WHEN rpc.provision_text LIKE '%height%' THEN 'height'
                WHEN rpc.provision_text LIKE '%setback%' THEN 'setback' 
                WHEN rpc.provision_text LIKE '%FSR%' OR rpc.provision_text LIKE '%floor space%' THEN 'fsr'
                WHEN rpc.provision_text LIKE '%parking%' THEN 'parking'
                ELSE 'general'
            END as control_type,
            'extracted' as control_subtype,
            rpc.provision_text as value_text,
            CASE 
                WHEN rpc.provision_text LIKE '%metre%' OR rpc.provision_text LIKE '%meter%' THEN 'm'
                WHEN rpc.provision_text LIKE '%storey%' OR rpc.provision_text LIKE '%story%' THEN 'storeys'
                ELSE 'text'
            END as unit,
            'general' as zone_applicable,
            'extracted from provisions' as conditions,
            0.8 as confidence_score,
            'factorization_script' as extraction_method
        FROM regulatory_provisions_clean rpc
        WHERE rpc.provision_type LIKE 'provision_%'
        AND (rpc.provision_text LIKE '%height%' 
             OR rpc.provision_text LIKE '%setback%'
             OR rpc.provision_text LIKE '%FSR%'
             OR rpc.provision_text LIKE '%parking%')
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM development_controls")
    enhanced_controls = cursor.fetchone()[0]
    factorization_stats['development_controls_enhanced'] = enhanced_controls
    print(f"   Enhanced development_controls to {enhanced_controls:,} entries")
    
    # STEP 6: Create regulatory_refs_core (remaining core references only)
    print("\n6. Creating regulatory_refs_core...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS regulatory_refs_core AS
        SELECT * FROM regulatory_refs
        WHERE ref_type NOT LIKE 'formal_%'
          AND ref_type NOT LIKE 'provision_%'
          AND ref_type NOT LIKE 'context_%'
          AND ref_type NOT LIKE 'informal_%'
          AND ref_type NOT LIKE 'relationship_%'
          AND ref_type NOT LIKE 'autoschema_%'
          AND ref_type != 'visual_reference'
          AND ref_type != 'clause|section'
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM regulatory_refs_core")
    core_count = cursor.fetchone()[0]
    factorization_stats['regulatory_refs_core'] = core_count
    print(f"   Remaining core references: {core_count:,}")
    
    # STEP 7: Verification
    total_factorized = sum(factorization_stats.values())
    print(f"\nFACTORIZATION VERIFICATION:")
    print(f"   Original regulatory_refs: {original_count:,}")
    print(f"   Total factorized: {total_factorized:,}")
    print(f"   Data preservation: {total_factorized/original_count*100:.1f}%")
    
    if total_factorized >= original_count * 0.95:  # Allow 5% margin
        print("   SUCCESS: FACTORIZATION DATA PRESERVATION: ACCEPTABLE")
    else:
        print("   ERROR: FACTORIZATION DATA LOSS: CRITICAL ERROR")
        return False
    
    conn.commit()
    
    # Create completion marker
    os.makedirs('migration_markers', exist_ok=True)
    with open('migration_markers/factorization_completed.marker', 'w') as f:
        f.write(f"Database factorization completed: {datetime.now().isoformat()}\n")
        f.write(f"Original regulatory_refs: {original_count}\n")
        f.write(f"Total factorized: {total_factorized}\n")
        for table, count in factorization_stats.items():
            f.write(f"{table}: {count}\n")
        f.write("Status: SUCCESS\n")
    
    conn.close()
    return True

if __name__ == "__main__":
    success = factorize_regulatory_refs()
    
    if success:
        print("SUCCESS: DATABASE FACTORIZATION SUCCESSFUL")
        exit(0)
    else:
        print("ERROR: DATABASE FACTORIZATION FAILED")
        exit(1)