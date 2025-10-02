#!/usr/bin/env python3

import psycopg2
from psycopg2.extras import RealDictCursor
import re

def create_dynamic_sepp_extractor():
    """
    Create a dynamic SEPP data extractor that works with ANY map type from NSW Planning API
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
            print('=== DYNAMIC SEPP EXTRACTOR FOR ANY MAP TYPE ===')

            def get_sepp_data_for_map_type(map_type):
                """
                Generic function to extract SEPP data for ANY map type from Planning API
                Examples: WAT, CLM, BAL, TEW, FSR, HEIGHT, HERITAGE, etc.
                """
                result = {
                    'map_type': map_type,
                    'provisions': [],
                    'entities': [],
                    'visual_elements': []
                }

                # 1. Get regulatory provisions for this map type
                print(f'\n--- Extracting data for Map Type: {map_type} ---')

                cur.execute("""
                    SELECT document_id, provision_type, ref_number, provision_text, section_header
                    FROM regulatory_provisions
                    WHERE provision_text ILIKE %s
                    OR provision_text ILIKE %s
                    OR section_header ILIKE %s
                    ORDER BY
                        CASE WHEN provision_text ILIKE %s THEN 1 ELSE 2 END,
                        ref_number
                    LIMIT 10
                """, (
                    f'%{map_type}%',
                    f'%{map_type.lower()} map%',
                    f'%{map_type}%',
                    f'%{map_type} map%'
                ))

                provisions = cur.fetchall()
                result['provisions'] = [dict(p) for p in provisions]

                # 2. Get knowledge graph entities
                cur.execute("""
                    SELECT entity_type, entity_name, entity_description, document_id
                    FROM kg_entities
                    WHERE entity_name ILIKE %s
                    OR entity_description ILIKE %s
                    LIMIT 5
                """, (f'%{map_type}%', f'%{map_type}%'))

                entities = cur.fetchall()
                result['entities'] = [dict(e) for e in entities]

                # 3. Get visual elements (check column names first)
                try:
                    cur.execute("""
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_name = 'visual_elements_real'
                        LIMIT 5
                    """)
                    visual_cols = [row['column_name'] for row in cur.fetchall()]

                    if visual_cols:
                        # Use available columns
                        cur.execute(f"""
                            SELECT *
                            FROM visual_elements_real
                            WHERE extracted_text ILIKE %s
                            LIMIT 3
                        """, (f'%{map_type}%',))

                        visual_elements = cur.fetchall()
                        result['visual_elements'] = [dict(v) for v in visual_elements]

                except Exception as e:
                    print(f'Visual elements query failed: {e}')

                return result

            # Test with known map types from NSW Planning API
            test_map_types = [
                'WAT',    # Water Use Map
                'CLM',    # Climate Zones for BASIX Buildings
                'BAL',    # Climate Zones for BASIX Alterations
                'TEW',    # Thermal Energy from Waste
                'FSR',    # Floor Space Ratio
                'HEIGHT', # Height of Buildings
                'HERITAGE', # Heritage Map
                'ZONE'    # Land Zoning
            ]

            all_results = {}

            for map_type in test_map_types:
                data = get_sepp_data_for_map_type(map_type)
                all_results[map_type] = data

                print(f'{map_type}: {len(data["provisions"])} provisions, {len(data["entities"])} entities, {len(data["visual_elements"])} visual elements')

                # Show best match if available
                if data['provisions']:
                    best_match = data['provisions'][0]
                    print(f'  Best: {best_match["ref_number"]} - {best_match["provision_text"][:100]}...')

            print('\n=== CREATING FRONTEND API STRUCTURE ===')

            # Create the API structure that can handle any map type
            api_example = {
                "endpoint": "/api/sepp-data",
                "method": "GET",
                "parameters": {
                    "mapType": "Any 3-letter code from NSW Planning API (WAT, CLM, BAL, etc.)"
                },
                "response_structure": {
                    "mapType": "WAT",
                    "provisions": [
                        {
                            "ref_number": "Section 3(2)",
                            "provision_type": "formal_Water Use Standard",
                            "provision_text": "Full text of requirement...",
                            "document_id": "State_Environmental_Planning_Policy_(Sustainable_Buildings)_2022"
                        }
                    ],
                    "entities": [
                        {
                            "entity_name": "Water Use Map",
                            "entity_type": "Map Reference",
                            "entity_description": "Map showing water use percentages..."
                        }
                    ],
                    "visual_elements": [
                        {
                            "extracted_text": "OCR text from planning documents",
                            "page_number": 15,
                            "document_id": "SEPP_Sustainable_Buildings_2022"
                        }
                    ]
                }
            }

            print('\n=== IMPLEMENTATION SUMMARY ===')
            print(f"""
            ✓ Dynamic extractor created for ANY map type
            ✓ Tested with {len(test_map_types)} common map types
            ✓ Found {sum(len(r['provisions']) for r in all_results.values())} total provisions
            ✓ Found {sum(len(r['entities']) for r in all_results.values())} total entities
            ✓ Ready for frontend integration

            Usage:
            1. PropertyCard extracts map types from NSW Planning API
            2. For each map type, call: get_sepp_data_for_map_type(map_type)
            3. Display provisions, entities, and visual elements
            4. Works with ANY map type - no hardcoding required
            """)

            return all_results

    except Exception as e:
        print(f'Database error: {e}')
        return None
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    results = create_dynamic_sepp_extractor()
    if results:
        print(f'\nSUCCESS: Dynamic SEPP extractor ready for {len(results)} map types')
    else:
        print('FAILED: Could not create dynamic extractor')