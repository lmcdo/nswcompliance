"""
Import missing C11 Multi Dwelling Housing provisions into the database.
These provisions specify 6m front, 4m side, 4m rear setbacks for multi dwelling housing.
"""

import sqlite3
import json
from datetime import datetime

def import_c11_provisions():
    """Import the missing C11 Multi Dwelling Housing setback provisions"""
    
    conn = sqlite3.connect('nsw_planning.db')
    cursor = conn.cursor()
    
    # The actual C11 provisions from Marrickville DCP 2011 section 4.2.4.3
    # These are the Multi Dwelling Housing setback requirements
    c11_provisions = [
        {
            'ref_number': 'C11 i',
            'section_header': '4.2.4.3 Building setbacks',
            'provision_text': '''Multi dwelling housing
Minimum front setback:
a. Must be 6 metres from the front boundary;
b. On corner lots the secondary building line may, at the discretion of Council, be reduced to 4.5 metres; and
c. For buildings above two storeys, each application shall be considered on merit.
NB Council may consider a variation to the above setback requirements where it is considered that a reduced setback will result in an improved streetscape and visual relationship with adjoining development.''',
            'document_id': 'Marrickville_DCP_2011___4_2_Multi_Dwelling_Housing_and_RFBs___with_IWLEP_2022_amendments',
            'zone': 'R2',
            'domain_classification': 'RESIDENTIAL_BUILDINGS',
            'development_type': 'multi_dwelling_housing',
            'page_number': 9
        },
        {
            'ref_number': 'C11 ii',
            'section_header': '4.2.4.3 Building setbacks',
            'provision_text': '''Multi dwelling housing
Minimum side setback:
a. Must be 4 metres where there is no driveway along the side boundary; and
b. Must be 7 metres where a driveway is proposed along that side boundary.
NB Council may agree to a minor variation to the above setbacks in order to create visual interest, provided that a corresponding section of the wall has its setback increased by an amount which is equal to the reduction in setback elsewhere.''',
            'document_id': 'Marrickville_DCP_2011___4_2_Multi_Dwelling_Housing_and_RFBs___with_IWLEP_2022_amendments',
            'zone': 'R2',
            'domain_classification': 'RESIDENTIAL_BUILDINGS',
            'development_type': 'multi_dwelling_housing',
            'page_number': 9
        },
        {
            'ref_number': 'C11 iii',
            'section_header': '4.2.4.3 Building setbacks',
            'provision_text': '''Multi dwelling housing
Minimum rear setback:
a. Must be 4 metres where there is no driveway along the rear boundary; and
b. Must be 7 metres where a driveway is proposed along that rear boundary.''',
            'document_id': 'Marrickville_DCP_2011___4_2_Multi_Dwelling_Housing_and_RFBs___with_IWLEP_2022_amendments',
            'zone': 'R2',
            'domain_classification': 'RESIDENTIAL_BUILDINGS',
            'development_type': 'multi_dwelling_housing',
            'page_number': 9
        },
        {
            'ref_number': 'C11 iv',
            'section_header': '4.2.4.3 Building setbacks',
            'provision_text': '''Multi dwelling housing
Setback along common driveway:
a. Minimum distance between rows of buildings along a common driveway must be 9 metres in the case of single storey development and 11 metres in the case of two storey development.''',
            'document_id': 'Marrickville_DCP_2011___4_2_Multi_Dwelling_Housing_and_RFBs___with_IWLEP_2022_amendments',
            'zone': 'R2',
            'domain_classification': 'RESIDENTIAL_BUILDINGS',
            'development_type': 'multi_dwelling_housing',
            'page_number': 9
        }
    ]
    
    # Check if C11 provisions already exist
    existing = cursor.execute('''
        SELECT COUNT(*) FROM regulatory_provisions 
        WHERE ref_number LIKE 'C11%' 
        AND document_id LIKE '%4_2_Multi_Dwelling%'
    ''').fetchone()[0]
    
    if existing > 0:
        print(f"Found {existing} existing C11 provisions in section 4.2, skipping import")
        return
    
    # Insert the missing provisions
    inserted = 0
    for provision in c11_provisions:
        try:
            cursor.execute('''
                INSERT INTO regulatory_provisions (
                    ref_number, section_header, provision_text, document_id,
                    zone, domain_classification, development_type, page_number,
                    prp_k1_enhanced, classification_confidence, cross_contamination_checked,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 0.95, 1, ?)
            ''', (
                provision['ref_number'],
                provision['section_header'],
                provision['provision_text'],
                provision['document_id'],
                provision['zone'],
                provision['domain_classification'],
                provision['development_type'],
                provision['page_number'],
                datetime.now().isoformat()
            ))
            inserted += 1
            print(f"✓ Inserted {provision['ref_number']}: Multi dwelling housing setback")
        except sqlite3.IntegrityError as e:
            print(f"× Skipped {provision['ref_number']}: Already exists or constraint violation")
    
    # Also need to add quantitative standards for these provisions
    if inserted > 0:
        # Get the IDs of the newly inserted provisions
        c11_provisions_db = cursor.execute('''
            SELECT id, ref_number, provision_text 
            FROM regulatory_provisions 
            WHERE ref_number LIKE 'C11%' 
            AND document_id LIKE '%4_2_Multi_Dwelling%'
        ''').fetchall()
        
        # Extract numeric values and create quantitative standards
        for provision_id, ref_num, text in c11_provisions_db:
            numeric_value = None
            context = None
            
            if 'C11 i' in ref_num and '6 metres' in text:
                numeric_value = 6.0
                context = 'setback_front'
            elif 'C11 ii' in ref_num and '4 metres' in text:
                numeric_value = 4.0
                context = 'setback_side'
            elif 'C11 iii' in ref_num and '4 metres' in text:
                numeric_value = 4.0
                context = 'setback_rear'
            
            if numeric_value and context:
                try:
                    cursor.execute('''
                        INSERT INTO quantitative_standards (
                            provision_id, numeric_value, unit, context, confidence_score
                        ) VALUES (?, ?, 'm', ?, 0.95)
                    ''', (provision_id, numeric_value, context))
                    print(f"  → Added quantitative standard: {numeric_value}m for {context}")
                except sqlite3.IntegrityError:
                    pass
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Successfully imported {inserted} C11 Multi Dwelling Housing provisions")
    print("These provisions specify:")
    print("  - Front setback: 6 metres")
    print("  - Side setback: 4 metres (no driveway) / 7 metres (with driveway)")
    print("  - Rear setback: 4 metres (no driveway) / 7 metres (with driveway)")

if __name__ == "__main__":
    import_c11_provisions()