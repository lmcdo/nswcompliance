
#!/usr/bin/env python3
"""
SEPP Classification and Legal Hierarchy Migration
Populates legal_instruments table and links provisions properly
"""

import psycopg2
import re
from datetime import datetime

def classify_and_link_legal_instruments():
    """Classify documents as SEPP/LEP/DCP and create proper hierarchy"""

    pg_config = {
        'host': 'localhost',
        'database': 'nsw_planning_corrected',
        'user': 'postgres',
        'password': 'postgres',
        'port': '5432'
    }

    with psycopg2.connect(**pg_config) as conn:
        cursor = conn.cursor()

        print("=== CLASSIFYING LEGAL INSTRUMENTS ===")

        # Get all unique documents
        cursor.execute('''
            SELECT DISTINCT document_id, COUNT(*) as provision_count
            FROM regulatory_provisions
            WHERE document_id IS NOT NULL
            GROUP BY document_id
            ORDER BY provision_count DESC
        ''')

        documents = cursor.fetchall()

        for doc_id, count in documents:
            print(f"Processing: {doc_id} ({count} provisions)")

            # Classify document type
            instrument_type = classify_document_type(doc_id)
            legal_precedence = get_legal_precedence(instrument_type)

            # Extract instrument code
            instrument_code = generate_instrument_code(doc_id, instrument_type)

            # Insert into legal_instruments
            cursor.execute('''
                INSERT INTO legal_instruments
                (instrument_code, instrument_type, legal_precedence, title, status)
                VALUES (%s, %s, %s, %s, 'current')
                ON CONFLICT (instrument_code) DO NOTHING
                RETURNING id
            ''', (instrument_code, instrument_type, legal_precedence, doc_id))

            result = cursor.fetchone()
            if result:
                instrument_id = result[0]
            else:
                # Get existing ID
                cursor.execute('SELECT id FROM legal_instruments WHERE instrument_code = %s', (instrument_code,))
                instrument_id = cursor.fetchone()[0]

            # Update regulatory_provisions to link to instrument
            cursor.execute('''
                ALTER TABLE regulatory_provisions
                ADD COLUMN IF NOT EXISTS instrument_id INTEGER REFERENCES legal_instruments(id)
            ''')

            cursor.execute('''
                UPDATE regulatory_provisions
                SET instrument_id = %s
                WHERE document_id = %s
            ''', (instrument_id, doc_id))

            print(f"  Classified as {instrument_type} (precedence {legal_precedence})")

        # Create zone classifications
        print("\n=== CREATING ZONE CLASSIFICATIONS ===")

        cursor.execute('SELECT DISTINCT zone FROM regulatory_provisions WHERE zone IS NOT NULL')
        zones = cursor.fetchall()

        for (zone,) in zones:
            if zone and zone.strip():
                zone_category = classify_zone(zone)

                cursor.execute('''
                    INSERT INTO zone_classifications (zone_code, zone_name, zone_category)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (zone_code) DO NOTHING
                ''', (zone, f"Zone {zone}", zone_category))

        conn.commit()
        print("\nLegal instrument classification completed!")

def classify_document_type(doc_id):
    """Classify document as SEPP, LEP, or DCP based on ID"""

    doc_lower = doc_id.lower()

    if any(keyword in doc_lower for keyword in ['sepp', 'state environmental planning policy', 'sustainable buildings']):
        return 'SEPP'
    elif any(keyword in doc_lower for keyword in ['lep', 'local environmental plan']):
        return 'LEP'
    elif any(keyword in doc_lower for keyword in ['dcp', 'development control plan']):
        return 'DCP'
    elif any(keyword in doc_lower for keyword in ['rep', 'regional environmental plan']):
        return 'REP'
    else:
        return 'DCP'  # Default to DCP

def get_legal_precedence(instrument_type):
    """Get legal precedence (lower number = higher precedence)"""

    precedence_map = {
        'SEPP': 1,
        'REP': 2,
        'LEP': 3,
        'DCP': 4
    }

    return precedence_map.get(instrument_type, 4)

def generate_instrument_code(doc_id, instrument_type):
    """Generate a clean instrument code"""

    # Clean up document ID
    code = doc_id.replace('___NSW_Legislation', '')
    code = code.replace('_with_IWLEP_2022_amendments', '')

    # Extract year if present
    year_match = re.search(r'(20\d{2})', code)
    year = year_match.group(1) if year_match else 'CURRENT'

    # Generate clean code
    if 'sustainable' in code.lower():
        return f'{instrument_type}_SUSTAINABLE_BUILDINGS_{year}'
    elif 'transport' in code.lower():
        return f'{instrument_type}_TRANSPORT_INFRASTRUCTURE_{year}'
    else:
        # Use first few words
        clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', code)
        clean_name = re.sub(r'_{2,}', '_', clean_name)
        return f'{instrument_type}_{clean_name[:50]}_{year}'.upper()

def classify_zone(zone_code):
    """Classify zone into category"""

    zone_categories = {
        'R1': 'Residential',
        'R2': 'Residential',
        'R3': 'Residential',
        'R4': 'Residential',
        'R5': 'Residential',
        'B1': 'Business',
        'B2': 'Business',
        'B3': 'Business',
        'B4': 'Business',
        'B5': 'Business',
        'B6': 'Business',
        'B7': 'Business',
        'B8': 'Business',
        'IN1': 'Industrial',
        'IN2': 'Industrial',
        'IN3': 'Industrial',
        'SP1': 'Special Purpose',
        'SP2': 'Special Purpose',
        'SP3': 'Special Purpose',
        'RE1': 'Recreation',
        'RE2': 'Recreation',
        'E1': 'Environmental',
        'E2': 'Environmental',
        'E3': 'Environmental',
        'E4': 'Environmental'
    }

    return zone_categories.get(zone_code, 'Other')

if __name__ == "__main__":
    classify_and_link_legal_instruments()
        