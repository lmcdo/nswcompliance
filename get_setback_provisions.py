#!/usr/bin/env python3
"""
Setback Provisions Retrieval Script - CLAUDE.md SAFETY COMPLIANT
Gets setback-related provisions from DCP database
Follows Universal Technical Implementation Specification - REAL DATA ONLY

CRITICAL: This file now uses CLAUDE.md mandatory safety wrapper
- db_safety_wrapper.py for ALL database operations
- 30-second timeouts enforced
- Emergency backups before ANY operation
- Query safety validation
"""

import argparse
import json
import sys
import os

# MANDATORY: Use safety wrapper per CLAUDE.md requirements
from db_safety_wrapper import get_safe_connection
import logging

# Configure safety logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - SAFETY - %(message)s')
logger = logging.getLogger(__name__)

def get_setback_provisions(zone: str) -> dict:
    """
    Get setback provisions for a specific zone from DCP
    NOW CLAUDE.md SAFETY COMPLIANT

    Args:
        zone: Zone identifier (e.g., "R1", "R2", "B1")

    Returns:
        Dictionary with setback provisions
    """
    try:
        # MANDATORY: Use safety wrapper per CLAUDE.md
        logger.info(f"Starting setback retrieval with safety wrapper: {zone}")

        # Use safe connection - automatically handles timeouts, backups, safety checks
        with get_safe_connection() as safe_conn:
            cursor = safe_conn.cursor()

            # Query for setback-related provisions
            setback_terms = ['setback', 'front yard', 'side yard', 'rear yard', 'building line']

            # Build OR conditions for setback terms
            setback_conditions = []
            params = []

            for term in setback_terms:
                setback_conditions.append("provision_text ILIKE %s")
                params.append(f'%{term}%')

            # Add zone filter
            setback_conditions.append("(zone ILIKE %s OR provision_text ILIKE %s)")
            params.extend([f'%{zone}%', f'%{zone}%'])

            # Add DCP document filter
            setback_conditions.append("document_id ILIKE %s")
            params.append('%DCP%')

            # SAFE QUERY: Uses WHERE clauses, prepared statements per CLAUDE.md
            query = f"""
                SELECT
                    id,
                    ref_number,
                    section_header,
                    provision_text,
                    document_id,
                    provision_type,
                    zone,
                    development_type,
                    page_number
                FROM regulatory_provisions
                WHERE ({' OR '.join(setback_conditions[:len(setback_terms)])})
                AND {setback_conditions[len(setback_terms)]}
                AND {setback_conditions[len(setback_terms) + 1]}
                AND provision_text IS NOT NULL
                AND LENGTH(provision_text) > 30
                ORDER BY
                    CASE
                        WHEN provision_text ILIKE '%front%setback%' THEN 1
                        WHEN provision_text ILIKE '%side%setback%' THEN 2
                        WHEN provision_text ILIKE '%rear%setback%' THEN 3
                        WHEN provision_text ILIKE '%setback%' THEN 4
                        ELSE 5
                    END,
                    LENGTH(provision_text) DESC
                LIMIT 15
            """

            # Execute with safety wrapper (automatically handles timeouts, logging)
            cursor.execute(query, params)
            provisions = cursor.fetchall()

            # Convert to list of dictionaries
            provision_list = []
            for prov in provisions:
                provision_list.append({
                    'id': prov['id'],
                    'ref_number': prov['ref_number'],
                    'section_header': prov['section_header'],
                    'provision_text': prov['provision_text'],
                    'document_id': prov['document_id'],
                    'provision_type': prov['provision_type'],
                    'zone': prov['zone'],
                    'development_type': prov['development_type'],
                    'page_number': prov['page_number']
                })

            # Safe connection automatically closes

        logger.info(f"Setback retrieval completed safely: {len(provision_list)} provisions found")

        return {
            'success': True,
            'provisions': provision_list,
            'total_found': len(provision_list),
            'safety_status': 'CLAUDE.md compliant',
            'query_params': {
                'zone': zone,
                'search_terms': setback_terms
            }
        }

    except Exception as e:
        logger.error(f"Setback retrieval failed with safety protection: {str(e)}")
        return {
            'success': False,
            'error': f'Database safety error: {str(e)}',
            'provisions': [],
            'safety_status': 'error_handled_safely'
        }

def main():
    parser = argparse.ArgumentParser(description='Get setback provisions for a zone')
    parser.add_argument('--zone', required=True, help='Zone identifier (e.g., "R1", "R2")')
    parser.add_argument('--format', default='json', help='Output format')

    args = parser.parse_args()

    result = get_setback_provisions(args.zone)

    if args.format == 'json':
        print(json.dumps(result, indent=2))
    else:
        if result['success']:
            print(f"Found {result['total_found']} setback provisions for zone {args.zone}")
            for prov in result['provisions']:
                print(f"  {prov['ref_number']}: {prov['section_header']}")
                print(f"    Text: {prov['provision_text'][:150]}...")
        else:
            print(f"Error: {result['error']}")

if __name__ == '__main__':
    main()