#!/usr/bin/env python3

import psycopg2
from psycopg2.extras import RealDictCursor

def check_wat_sepp_data():
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='nsw_planning',
            user='postgres',
            password='postgres',
            port='5432'
        )

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            print('=== 1. REGULATORY PROVISIONS WITH WAT REFERENCES ===')
            cur.execute("""
                SELECT document_id, provision_type, ref_number, provision_text, section_header
                FROM regulatory_provisions
                WHERE provision_text ILIKE '%WAT%'
                AND provision_text ILIKE '%water%'
                LIMIT 5
            """)

            wat_provisions = cur.fetchall()
            for i, row in enumerate(wat_provisions):
                print(f'\n--- WAT Provision {i+1} ---')
                print(f'Document: {row["document_id"]}')
                print(f'Type: {row["provision_type"]}')
                print(f'Ref: {row["ref_number"]}')
                print(f'Section: {row["section_header"]}')
                print(f'Text: {row["provision_text"][:300]}...')

            print('\n=== 2. KNOWLEDGE GRAPH ENTITIES STRUCTURE ===')
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'kg_entities'
                ORDER BY ordinal_position
            """)

            entity_cols = cur.fetchall()
            print('KG Entities columns:')
            for col in entity_cols:
                print(f'  - {col["column_name"]}')

            print('\n=== KG ENTITIES FOR WAT/WATER ===')
            cur.execute("""
                SELECT *
                FROM kg_entities
                WHERE entity_name ILIKE '%water%'
                OR entity_name ILIKE '%WAT%'
                LIMIT 5
            """)

            kg_entities = cur.fetchall()
            for entity in kg_entities:
                print(f'Entity: {dict(entity)}')
                print()

            print('\n=== 3. WATER USE MAP SPECIFIC PROVISIONS ===')
            cur.execute("""
                SELECT provision_text, ref_number, document_id
                FROM regulatory_provisions
                WHERE provision_text ILIKE '%Water Use Map%'
                AND provision_text ILIKE '%percentage%'
                LIMIT 3
            """)

            water_map_provisions = cur.fetchall()
            for prov in water_map_provisions:
                print(f'Ref: {prov["ref_number"]}')
                print(f'Document: {prov["document_id"]}')
                print(f'Text: {prov["provision_text"][:400]}...')
                print()

            print('\n=== 4. SCHEDULE 3 WATER STANDARDS ===')
            cur.execute("""
                SELECT provision_text, ref_number
                FROM regulatory_provisions
                WHERE provision_text ILIKE '%Schedule 3%'
                AND provision_text ILIKE '%water%'
                LIMIT 2
            """)

            schedule3_provisions = cur.fetchall()
            for prov in schedule3_provisions:
                print(f'Ref: {prov["ref_number"]}')
                print(f'Text: {prov["provision_text"][:400]}...')
                print()

            print('\n=== 4. QUANTITATIVE STANDARDS FOR WATER ===')
            cur.execute("""
                SELECT standard_type, value, unit, context, source_provision
                FROM quantitative_standards
                WHERE standard_type ILIKE '%water%'
                OR context ILIKE '%water%'
                OR source_provision ILIKE '%water%'
                LIMIT 5
            """)

            quant_standards = cur.fetchall()
            for std in quant_standards:
                print(f'Standard: {std["standard_type"]} = {std["value"]} {std["unit"]}')
                print(f'Context: {std["context"]}')
                print(f'Source: {std["source_provision"]}')
                print()

            print('\n=== 5. VISUAL ELEMENTS (OCR PARSED) FOR WATER/WAT ===')
            cur.execute("""
                SELECT element_type, extracted_text, confidence_score, page_number, document_id
                FROM visual_elements_real
                WHERE extracted_text ILIKE '%water%'
                OR extracted_text ILIKE '%WAT%'
                ORDER BY confidence_score DESC
                LIMIT 5
            """)

            visual_elements = cur.fetchall()
            for element in visual_elements:
                print(f'OCR Element ({element["element_type"]}): Page {element["page_number"]}')
                print(f'  Document: {element["document_id"]}')
                print(f'  Text: {element["extracted_text"][:200]}...')
                print(f'  Confidence: {element["confidence_score"]}')
                print()

            print('\n=== 6. DEVELOPMENT CONTROLS FOR WATER ===')
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'development_controls'
                ORDER BY ordinal_position
            """)

            dev_control_cols = cur.fetchall()
            print('Development Controls table columns:')
            for col in dev_control_cols:
                print(f'  - {col["column_name"]}')

            # Check if we can query development controls for water-related content
            try:
                cur.execute("""
                    SELECT control_type, requirement, applicability
                    FROM development_controls
                    WHERE requirement ILIKE '%water%'
                    LIMIT 3
                """)

                dev_controls = cur.fetchall()
                if dev_controls:
                    print('\nWater-related development controls:')
                    for control in dev_controls:
                        print(f'Control: {control["control_type"]}')
                        print(f'Requirement: {control["requirement"][:150]}...')
                        print(f'Applicability: {control["applicability"]}')
                        print()
            except Exception as e:
                print(f'Could not query development_controls: {e}')

            print('\n=== 7. SUMMARY OF AVAILABLE WAT/WATER DATA ===')
            data_sources = [
                ('regulatory_provisions', 'Direct SEPP text with WAT references'),
                ('kg_entities', 'Extracted water-related entities'),
                ('kg_relationships', 'Water relationships between entities'),
                ('quantitative_standards', 'Numerical water requirements'),
                ('visual_elements_real', 'OCR-parsed tables/diagrams'),
                ('development_controls', 'Structured control requirements')
            ]

            for table, description in data_sources:
                cur.execute(f"""
                    SELECT COUNT(*) as count
                    FROM {table}
                    WHERE CAST(ANY(ARRAY[
                        COALESCE(CAST({table} AS TEXT), ''),
                        COALESCE(CAST({table} AS TEXT), '')
                    ]) AS TEXT) ILIKE '%water%'
                """)

                try:
                    # Simplified count for each table
                    cur.execute(f"SELECT COUNT(*) as total FROM {table}")
                    total = cur.fetchone()['total']
                    print(f'{table}: {total} total rows - {description}')
                except Exception as e:
                    print(f'{table}: Error counting - {description}')

    except Exception as e:
        print(f'Database error: {e}')
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    check_wat_sepp_data()