#!/usr/bin/env python3

import psycopg2
from psycopg2.extras import RealDictCursor
import json

def get_sepp_data_for_any_map_type():
    """
    Dynamically extract SEPP data for ANY map type that appears in the NSW Planning API
    """
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='nsw_planning',
            user='postgres',
            password='postgres',
            port='5432'
        )

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            print('=== DYNAMIC SEPP MAP TYPE EXTRACTION ===')

            # Extract all possible map types from SEPP provisions text using PostgreSQL regex
            print('Searching for map type patterns in SEPP provisions...')

            # Alternative: Extract common 3-letter codes that appear in planning context
            print('\n=== 1. FINDING ALL MAP TYPE PATTERNS ===')
            cur.execute("""
                SELECT provision_text
                FROM regulatory_provisions
                WHERE provision_text ILIKE '%map%'
                AND (provision_text ILIKE '%WAT%'
                OR provision_text ILIKE '%CLM%'
                OR provision_text ILIKE '%BAL%'
                OR provision_text ILIKE '%TEW%'
                OR provision_text ILIKE '%FSR%'
                OR provision_text ILIKE '%height%')
                LIMIT 10
            """)

            map_patterns = cur.fetchall()

            # Extract potential map codes from text
            potential_map_types = set()
            for row in map_patterns:
                text = row['provision_text'].upper()
                # Look for 3-letter codes that might be map types
                import re
                codes = re.findall(r'\b[A-Z]{3}\b', text)
                for code in codes:
                    if code in ['WAT', 'CLM', 'BAL', 'TEW', 'FSR', 'HSG', 'HER', 'ENV']:
                        potential_map_types.add(code)

            print(f'Potential map types found: {sorted(potential_map_types)}')

            print('\n=== 2. BUILDING GENERIC SEPP DATA EXTRACTOR ===')

            def get_sepp_data_for_map_type(map_type):
                """Generic function to get SEPP data for any map type"""

                # Search for provisions related to this map type
                cur.execute("""
                    SELECT document_id, provision_type, ref_number, provision_text, section_header
                    FROM regulatory_provisions
                    WHERE provision_text ILIKE %s
                    OR provision_text ILIKE %s
                    OR ref_number ILIKE %s
                    LIMIT 5
                """, (f'%{map_type}%', f'%{map_type.lower()}%', f'%{map_type}%'))

                provisions = cur.fetchall()

                # Search for entities related to this map type
                cur.execute("""
                    SELECT entity_type, entity_name, entity_description
                    FROM kg_entities
                    WHERE entity_name ILIKE %s
                    OR entity_description ILIKE %s
                    LIMIT 3
                """, (f'%{map_type}%', f'%{map_type}%'))

                entities = cur.fetchall()

                # Search visual elements (OCR parsed content)
                cur.execute("""
                    SELECT element_type, extracted_text, confidence_score, page_number, document_id
                    FROM visual_elements_real
                    WHERE extracted_text ILIKE %s
                    LIMIT 3
                """, (f'%{map_type}%',))

                visual_elements = cur.fetchall()

                return {
                    'map_type': map_type,
                    'provisions': [dict(p) for p in provisions],
                    'entities': [dict(e) for e in entities],
                    'visual_elements': [dict(v) for v in visual_elements]
                }

            # Test the function with known map types
            test_map_types = ['WAT', 'CLM', 'BAL', 'TEW', 'FSR', 'HEIGHT']

            results = {}
            for map_type in test_map_types:
                print(f'\n--- Processing {map_type} ---')
                data = get_sepp_data_for_map_type(map_type)
                results[map_type] = data

                print(f'{map_type}: {len(data["provisions"])} provisions, {len(data["entities"])} entities, {len(data["visual_elements"])} visual elements')

                # Show sample provision if available
                if data['provisions']:
                    sample = data['provisions'][0]
                    print(f'  Sample: {sample["ref_number"]} - {sample["provision_text"][:100]}...')

            print('\n=== 3. CREATING API ENDPOINT STRUCTURE ===')
            print("""
            Recommended API structure for frontend:

            GET /api/sepp-data?mapType=WAT
            Returns: {
                "mapType": "WAT",
                "description": "Water Use Map",
                "provisions": [...],
                "entities": [...],
                "visualElements": [...],
                "applicableStandards": [...]
            }

            This would work for ANY map type: WAT, CLM, BAL, TEW, etc.
            """)

            print('\n=== 4. SUMMARY FOR FRONTEND INTEGRATION ===')
            print(f"""
            Database contains SEPP data for:
            - regulatory_provisions: {sum(len(r['provisions']) for r in results.values())} relevant provisions
            - kg_entities: {sum(len(r['entities']) for r in results.values())} entities
            - visual_elements_real: {sum(len(r['visual_elements']) for r in results.values())} OCR elements

            This can be dynamically queried for ANY map type from the NSW Planning API.
            """)

            return results

    except Exception as e:
        print(f'Database error: {e}')
        return None
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    results = get_sepp_data_for_any_map_type()
    if results:
        print(f'\nSuccessfully extracted SEPP data for {len(results)} map types')
    else:
        print('Failed to extract SEPP data')