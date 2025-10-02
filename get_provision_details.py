#!/usr/bin/env python3
"""
Provision Details Retrieval Script - CLAUDE.md SAFETY COMPLIANT
Gets detailed provision content from PostgreSQL database
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

def get_provision_details(clause_reference: str, document_type: str) -> dict:
    """
    Get detailed provision content for a specific clause
    NOW CLAUDE.md SAFETY COMPLIANT

    Args:
        clause_reference: The clause reference (e.g., "Clause 4.3", "4.4")
        document_type: Document type filter ("LEP", "DCP", "SEPP")

    Returns:
        Dictionary with provisions list
    """
    try:
        # MANDATORY: Use safety wrapper per CLAUDE.md
        logger.info(f"Starting provision retrieval with safety wrapper: {clause_reference}")

        # Use safe connection - automatically handles timeouts, backups, safety checks
        with get_safe_connection() as safe_conn:
            cursor = safe_conn.cursor()

            # Determine document type patterns
            if document_type == 'LEP':
                doc_pattern = '%Local_Environmental_Plan%'
            elif document_type == 'DCP':
                doc_pattern = '%DCP%'
            elif document_type == 'SEPP':
                doc_pattern = '%Environmental_Planning_Policy%'
            else:
                doc_pattern = '%'  # All documents

            # SAFE QUERY: Uses WHERE clauses, prepared statements per CLAUDE.md
            query = """
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
                WHERE (
                    ref_number ILIKE %s
                    OR ref_number ILIKE %s
                    OR provision_text ILIKE %s
                )
                AND document_id ILIKE %s
                AND provision_text IS NOT NULL
                AND LENGTH(provision_text) > 50
                ORDER BY
                    CASE
                        WHEN ref_number ILIKE %s THEN 1
                        WHEN ref_number ILIKE %s THEN 2
                        ELSE 3
                    END,
                    LENGTH(provision_text) DESC
                LIMIT 10
            """

            params = (
                f'%{clause_reference}%',
                f'%{clause_reference.replace("Clause ", "")}%',
                f'%{clause_reference}%',
                doc_pattern,
                f'{clause_reference}',
                f'{clause_reference.replace("Clause ", "")}'
            )

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

        logger.info(f"Provision retrieval completed safely: {len(provision_list)} provisions found")

        return {
            'success': True,
            'provisions': provision_list,
            'total_found': len(provision_list),
            'safety_status': 'CLAUDE.md compliant',
            'query_params': {
                'clause_reference': clause_reference,
                'document_type': document_type
            }
        }

    except Exception as e:
        logger.error(f"Provision retrieval failed with safety protection: {str(e)}")
        return {
            'success': False,
            'error': f'Database safety error: {str(e)}',
            'provisions': [],
            'safety_status': 'error_handled_safely'
        }

def main():
    parser = argparse.ArgumentParser(description='Get provision details from database')
    parser.add_argument('--clause', required=True, help='Clause reference (e.g., "Clause 4.3")')
    parser.add_argument('--document-type', required=True, choices=['LEP', 'DCP', 'SEPP'], help='Document type')
    parser.add_argument('--format', default='json', help='Output format')

    args = parser.parse_args()

    result = get_provision_details(args.clause, args.document_type)

    if args.format == 'json':
        print(json.dumps(result, indent=2))
    else:
        if result['success']:
            print(f"Found {result['total_found']} provisions for {args.clause}")
            for prov in result['provisions']:
                print(f"  {prov['ref_number']}: {prov['section_header']}")
                print(f"    Text: {prov['provision_text'][:200]}...")
        else:
            print(f"Error: {result['error']}")

if __name__ == '__main__':
    main()