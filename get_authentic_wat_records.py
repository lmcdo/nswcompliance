#!/usr/bin/env python3
"""
Get Authentic WAT (Water Use Map) SEPP Records from PostgreSQL
Shows real SEPP provisions with complete text
"""

import psycopg2
import json
from psycopg2.extras import RealDictCursor

def get_authentic_wat_records():
    """Get real WAT SEPP records from PostgreSQL database"""

    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host='localhost',
            database='nsw_planning',
            user='postgres',
            password='postgres',
            port='5432'
        )

        cursor = conn.cursor(cursor_factory=RealDictCursor)

        print('SEARCHING FOR AUTHENTIC WAT (Water Use Map) SEPP RECORDS...')
        print('=' * 70)

        # Search for WAT provisions - looking for real SEPP water use map provisions
        cursor.execute("""
            SELECT
                id,
                ref_number,
                provision_text,
                document_id,
                provision_type,
                zone,
                page_number,
                development_type,
                created_at
            FROM regulatory_provisions
            WHERE (
                provision_text ILIKE '%water use map%'
                OR provision_text ILIKE '%water standard%'
                OR provision_text ILIKE '%BASIX%'
                OR provision_text ILIKE '%water efficiency%'
                OR document_id ILIKE '%sustainable%'
                OR document_id ILIKE '%water%'
            )
            AND document_id ILIKE '%SEPP%'
            ORDER BY id
            LIMIT 5
        """)

        wat_provisions = cursor.fetchall()

        if not wat_provisions:
            print("No WAT records found. Searching broader...")
            # Broader search
            cursor.execute("""
                SELECT * FROM regulatory_provisions
                WHERE provision_text ILIKE '%water%'
                LIMIT 3
            """)
            wat_provisions = cursor.fetchall()

        for i, record in enumerate(wat_provisions, 1):
            print(f'\nAUTHENTIC WAT RECORD {i}:')
            print(f'ID: {record["id"]}')
            print(f'Reference: {record["ref_number"]}')
            print(f'Document: {record["document_id"]}')
            print(f'Type: {record["provision_type"]}')
            print(f'Zone: {record["zone"]}')
            print(f'Page: {record["page_number"]}')
            if record.get("development_type"):
                print(f'Dev Type: {record["development_type"]}')

            print(f'\nCOMPLETE PROVISION TEXT:')
            print(f'{record["provision_text"]}')
            print('=' * 70)

        # Also search development controls for water-related controls
        print('\nSEARCHING DEVELOPMENT CONTROLS FOR WATER/WAT CONTROLS...')
        cursor.execute("""
            SELECT
                dc.id,
                dc.control_type,
                dc.control_subtype,
                dc.value_numeric,
                dc.value_text,
                dc.unit,
                dc.zone_applicable,
                dc.confidence_score,
                rp.provision_text,
                rp.document_id,
                rp.ref_number
            FROM development_controls dc
            JOIN regulatory_provisions rp ON dc.provision_id = rp.id
            WHERE (
                rp.provision_text ILIKE '%water%'
                OR rp.provision_text ILIKE '%BASIX%'
                OR dc.control_type ILIKE '%water%'
            )
            AND rp.document_id ILIKE '%SEPP%'
            ORDER BY dc.confidence_score DESC
            LIMIT 3
        """)

        controls = cursor.fetchall()

        for i, control in enumerate(controls, 1):
            print(f'\nWATER CONTROL {i}:')
            print(f'Control Type: {control["control_type"]}')
            print(f'Subtype: {control["control_subtype"]}')
            print(f'Value: {control["value_numeric"]} {control["unit"] or ""}')
            print(f'Text Value: {control["value_text"]}')
            print(f'Zone: {control["zone_applicable"]}')
            print(f'Confidence: {control["confidence_score"]}')
            print(f'Document: {control["document_id"]}')
            print(f'Reference: {control["ref_number"]}')
            print(f'Source Text: {control["provision_text"][:300]}...')
            print('-' * 50)

        # Search in sepp_lep_overrides table for WAT overrides
        print('\nSEARCHING SEPP/LEP OVERRIDES FOR WAT...')
        cursor.execute("""
            SELECT
                slo.id,
                slo.sepp_provision_id,
                slo.lep_clause_reference,
                slo.override_type,
                slo.confidence_score,
                slo.extracted_text,
                rp.provision_text as sepp_text,
                rp.document_id
            FROM sepp_lep_overrides slo
            JOIN regulatory_provisions rp ON slo.sepp_provision_id = rp.id
            WHERE (
                slo.extracted_text ILIKE '%water%'
                OR rp.provision_text ILIKE '%water%'
                OR rp.provision_text ILIKE '%BASIX%'
            )
            LIMIT 2
        """)

        overrides = cursor.fetchall()

        for i, override in enumerate(overrides, 1):
            print(f'\nSEPP OVERRIDE {i}:')
            print(f'Override ID: {override["id"]}')
            print(f'SEPP Provision ID: {override["sepp_provision_id"]}')
            print(f'LEP Clause: {override["lep_clause_reference"]}')
            print(f'Override Type: {override["override_type"]}')
            print(f'Confidence: {override["confidence_score"]}')
            print(f'Document: {override["document_id"]}')
            print(f'Extracted Text: {override["extracted_text"]}')
            print(f'Full SEPP Text: {override["sepp_text"][:300]}...')
            print('-' * 50)

        conn.close()

        print('\nAUTHENTIC WAT RECORD EXTRACTION COMPLETE')

    except Exception as e:
        print(f'Error: {e}')
        return False

    return True

if __name__ == "__main__":
    get_authentic_wat_records()