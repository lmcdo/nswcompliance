#!/usr/bin/env python3
"""
Parking Rates Fetcher
Fetches actual parking rates from regulatory_provisions database
NO HARDCODED ASSUMPTIONS - All rates from actual regulations
"""

import json
import sys
from typing import Dict, Optional, List
from db_safety_wrapper import get_safe_connection

class ParkingRatesFetcher:
    """Fetches actual parking rates from regulatory provisions"""

    def __init__(self):
        """Initialize parking rates fetcher"""
        self.conn = None

    def get_parking_rate(self, zone: str, development_type: str, lga: str = None) -> Dict:
        """
        Fetch parking rate from regulatory_provisions table

        Args:
            zone: Zone code (e.g., R2, R3, B1)
            development_type: Type of development
            lga: Local Government Area (optional for council-specific rates)

        Returns:
            Dictionary with parking rate and source
        """
        try:
            self.conn = get_safe_connection()
            cursor = self.conn.cursor()

            # Search for parking provisions in regulatory_provisions table
            query = """
                SELECT
                    document_type,
                    document_name,
                    clause_reference,
                    provision_text,
                    numeric_value,
                    units,
                    confidence_score
                FROM regulatory_provisions
                WHERE
                    zone_code = %s
                    AND provision_type IN ('parking', 'car_parking', 'vehicle_parking')
                    AND (
                        LOWER(provision_text) LIKE %s
                        OR LOWER(provision_text) LIKE '%parking%'
                    )
                ORDER BY
                    CASE document_type
                        WHEN 'LEP' THEN 1
                        WHEN 'DCP' THEN 2
                        ELSE 3
                    END,
                    confidence_score DESC
                LIMIT 10
            """

            # Search pattern for development type
            dev_type_pattern = f'%{development_type.replace("_", " ")}%'

            cursor.execute(query, (zone, dev_type_pattern))
            results = cursor.fetchall()

            if results:
                # Try to extract numeric parking rate
                for row in results:
                    doc_type, doc_name, clause_ref, provision_text, numeric_val, units, confidence = row

                    # Look for numeric value with appropriate units
                    if numeric_val and units and 'space' in str(units).lower():
                        return {
                            'rate': float(numeric_val),
                            'units': units,
                            'source': f"{doc_name} - {clause_ref}",
                            'document_type': doc_type,
                            'provision_text': provision_text[:200] if provision_text else '',
                            'confidence': float(confidence) if confidence else 0.7,
                            'found': True
                        }

                # If no direct numeric value, parse from text
                for row in results:
                    doc_type, doc_name, clause_ref, provision_text, _, _, confidence = row

                    if provision_text:
                        # Look for patterns like "1.5 spaces per dwelling"
                        import re
                        patterns = [
                            r'(\d+(?:\.\d+)?)\s*(?:car\s*)?(?:parking\s*)?space[s]?\s*per\s*(?:dwelling|unit)',
                            r'(\d+(?:\.\d+)?)\s*space[s]?\s*per\s*(?:dwelling|unit)',
                            r'(\d+(?:\.\d+)?)\s*(?:parking|car)\s*(?:space[s]?)?/(?:dwelling|unit)'
                        ]

                        for pattern in patterns:
                            match = re.search(pattern, provision_text.lower())
                            if match:
                                rate = float(match.group(1))
                                return {
                                    'rate': rate,
                                    'units': 'spaces per dwelling',
                                    'source': f"{doc_name} - {clause_ref}",
                                    'document_type': doc_type,
                                    'provision_text': provision_text[:200],
                                    'confidence': float(confidence) * 0.9 if confidence else 0.6,
                                    'found': True,
                                    'parsed_from_text': True
                                }

                # Return first result even if no rate extracted
                row = results[0]
                return {
                    'rate': None,
                    'source': f"{row[1]} - {row[2]}",
                    'document_type': row[0],
                    'provision_text': row[3][:200] if row[3] else '',
                    'confidence': float(row[6]) if row[6] else 0.5,
                    'found': True,
                    'requires_manual_interpretation': True,
                    'message': 'Parking provision found but rate requires manual interpretation'
                }

            # Try broader search without development type
            cursor.execute("""
                SELECT
                    document_type,
                    document_name,
                    clause_reference,
                    provision_text
                FROM regulatory_provisions
                WHERE
                    zone_code = %s
                    AND provision_type IN ('parking', 'car_parking')
                LIMIT 5
            """, (zone,))

            fallback_results = cursor.fetchall()

            if fallback_results:
                return {
                    'rate': None,
                    'source': f"Multiple provisions found for zone {zone}",
                    'document_type': 'Various',
                    'provisions_count': len(fallback_results),
                    'found': True,
                    'requires_manual_selection': True,
                    'message': f'Found {len(fallback_results)} parking provisions for zone {zone}. Manual review required.',
                    'available_provisions': [
                        {
                            'document': row[1],
                            'clause': row[2],
                            'excerpt': row[3][:100] if row[3] else ''
                        } for row in fallback_results
                    ]
                }

            # No results found
            return {
                'rate': None,
                'found': False,
                'message': f'No parking provisions found for zone {zone} and development type {development_type}',
                'recommendation': 'Check council DCP manually or contact planning department'
            }

        except Exception as e:
            return {
                'rate': None,
                'found': False,
                'error': str(e),
                'message': 'Database query failed. Please check council DCP manually.'
            }
        finally:
            if cursor:
                cursor.close()
            if self.conn:
                self.conn.close()

    def get_council_parking_table(self, lga: str) -> List[Dict]:
        """
        Get complete parking rates table for a council

        Args:
            lga: Local Government Area name

        Returns:
            List of parking rate entries
        """
        try:
            self.conn = get_safe_connection()
            cursor = self.conn.cursor()

            query = """
                SELECT DISTINCT
                    zone_code,
                    development_type,
                    numeric_value,
                    units,
                    document_name,
                    clause_reference
                FROM regulatory_provisions
                WHERE
                    document_name LIKE %s
                    AND provision_type IN ('parking', 'car_parking')
                    AND numeric_value IS NOT NULL
                ORDER BY zone_code, development_type
            """

            cursor.execute(query, (f'%{lga}%',))
            results = cursor.fetchall()

            parking_table = []
            for row in results:
                parking_table.append({
                    'zone': row[0],
                    'development_type': row[1],
                    'rate': float(row[2]) if row[2] else None,
                    'units': row[3],
                    'source': f"{row[4]} - {row[5]}"
                })

            return parking_table

        except Exception as e:
            return []
        finally:
            if cursor:
                cursor.close()
            if self.conn:
                self.conn.close()


# CLI interface for testing
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Fetch Parking Rates from Regulations')
    parser.add_argument('--zone', required=True, help='Zone code (e.g., R2)')
    parser.add_argument('--development-type', required=True, help='Development type')
    parser.add_argument('--lga', help='Local Government Area')
    parser.add_argument('--format', default='json', choices=['json', 'text'], help='Output format')

    args = parser.parse_args()

    fetcher = ParkingRatesFetcher()
    result = fetcher.get_parking_rate(
        zone=args.zone,
        development_type=args.development_type,
        lga=args.lga
    )

    if args.format == 'json':
        print(json.dumps(result, indent=2))
    else:
        print(f"Parking Rate Search Results")
        print(f"Zone: {args.zone}")
        print(f"Development Type: {args.development_type}")
        print("-" * 40)

        if result['found']:
            if result.get('rate'):
                print(f"Rate: {result['rate']} {result.get('units', 'spaces per unit')}")
                print(f"Source: {result['source']}")
                print(f"Confidence: {result.get('confidence', 0):.1%}")
            else:
                print(f"Status: {result.get('message', 'Rate requires manual interpretation')}")
                print(f"Source: {result.get('source', 'Unknown')}")
                if result.get('provision_text'):
                    print(f"Text: {result['provision_text']}")
        else:
            print(f"Status: No parking provisions found")
            print(f"Recommendation: {result.get('recommendation', 'Check council DCP manually')}")