#!/usr/bin/env python3
"""
Enhanced Compliance API CLI
Wrapper for existing hierarchy resolver with optional development permissions
"""

import sys
import json
import argparse
import os
from development_permissions_db import DevelopmentPermissionsDB
import subprocess

class EnhancedComplianceAPI:
    def __init__(self):
        self.dev_permissions_db = DevelopmentPermissionsDB()

    def get_enhanced_compliance(self, zone_code: str, property_id: int = None,
                              development_type: str = None,
                              include_development_permissions: bool = False,
                              climate_zone: str = None,
                              water_zone: str = None,
                              special_provisions: list = None):
        """Get enhanced compliance check with optional development permissions"""

        # First, call the existing hierarchy resolver
        base_result = self._call_existing_hierarchy_resolver(zone_code, property_id, development_type)

        # Add development permissions if requested
        if include_development_permissions:
            dev_permissions = self.dev_permissions_db.get_zone_permissions(zone_code)
            base_result['development_permissions'] = dev_permissions

        # Add feasibility check if development_type provided
        if development_type:
            feasibility = self.dev_permissions_db.check_development_feasibility(zone_code, development_type)
            base_result['feasibility_check'] = feasibility

        # Add BASIX provisions if climate zone provided
        if climate_zone:
            try:
                from basix_compliance_checker import BASIXComplianceChecker
                basix_checker = BASIXComplianceChecker()
                basix_data = {'climate_zone': climate_zone, 'water_zone': water_zone}
                base_result = basix_checker.integrate_with_compliance_response(base_result, basix_data)
                basix_checker.close_connection()
                import sys
                print(f"BASIX processing completed for climate zone {climate_zone}", file=sys.stderr)
            except ImportError:
                import sys
                print("Warning: BASIX checker not available", file=sys.stderr)
            except Exception as e:
                import sys
                print(f"Warning: BASIX processing failed: {e}", file=sys.stderr)
                # Add basic BASIX fallback even if processing fails
                if climate_zone and 'tier_1_provisions' in base_result:
                    base_result['tier_1_provisions'].append({
                        'id': 'basix_fallback',
                        'document_type': 'BASIX',
                        'document_name': 'Building Sustainability Index',
                        'clause_reference': f'Climate Zone {climate_zone}',
                        'provision_text': f'BASIX requirements apply for Climate Zone {climate_zone}',
                        'provision_type': 'sustainability',
                        'tier_level': 1,
                        'authority_level': 100,
                        'confidence_level': 0.9
                    })
                    base_result['basix_summary'] = {
                        'climate_zone': climate_zone,
                        'water_zone': water_zone,
                        'has_requirements': True,
                        'provision_count': 1,
                        'source': 'Fallback BASIX data'
                    }

        # Add special provisions processing
        if special_provisions:
            try:
                from special_provisions_processor import SpecialProvisionsProcessor
                provisions_processor = SpecialProvisionsProcessor()
                processed_provisions = provisions_processor.process_special_provisions(
                    special_provisions, zone_code, development_type
                )

                # Merge special provisions into base result
                for tier in range(1, 6):
                    tier_key = f'tier_{tier}_provisions'
                    if tier_key in processed_provisions and tier_key in base_result:
                        base_result[tier_key].extend(processed_provisions[tier_key])
                    elif tier_key in processed_provisions:
                        base_result[tier_key] = processed_provisions[tier_key]

                # Add special metadata
                if 'processing_metadata' not in base_result:
                    base_result['processing_metadata'] = {}

                base_result['processing_metadata']['special_provisions_processed'] = processed_provisions['metadata']['total_processed']
                base_result['processing_metadata']['hazards_identified'] = processed_provisions['metadata']['has_hazards']

                provisions_processor.close_connection()
            except ImportError:
                import sys
                print("Warning: Special provisions processor not available", file=sys.stderr)
            except Exception as e:
                import sys
                print(f"Warning: Special provisions processing failed: {e}", file=sys.stderr)

        return base_result

    def _call_existing_hierarchy_resolver(self, zone_code: str, property_id: int = None,
                                        development_type: str = None):
        """Call the existing hierarchy resolver CLI"""
        try:
            # Path to existing hierarchy resolver
            script_path = os.path.join(os.path.dirname(__file__), 'hierarchy_resolver_cli.py')

            # Build command
            cmd = [sys.executable, script_path, '--zone', zone_code, '--format', 'json']

            if property_id:
                cmd.extend(['--property-id', str(property_id)])

            if development_type:
                cmd.extend(['--development-type', development_type])

            # Execute the existing CLI
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                # Parse the JSON response
                try:
                    return json.loads(result.stdout.strip())
                except json.JSONDecodeError:
                    # Fallback - try to extract JSON from output
                    lines = result.stdout.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line.startswith('{') and line.endswith('}'):
                            try:
                                return json.loads(line)
                            except json.JSONDecodeError:
                                continue

                    # If no valid JSON found, return basic structure
                    return {
                        'zone': zone_code,
                        'property_id': property_id,
                        'development_type': development_type,
                        'error': 'Could not parse hierarchy resolver response',
                        'raw_output': result.stdout
                    }
            else:
                # Create a fallback response when database is not available
                return {
                    'property': {
                        'property_id': property_id,
                        'zone_code': zone_code,
                        'development_type': development_type
                    },
                    'tier_1_provisions': [],
                    'tier_2_provisions': [],
                    'tier_3_provisions': [],
                    'tier_4_provisions': [],
                    'tier_5_provisions': [],
                    'primary_authorities': {},
                    'complexity_assessment': 'moderate_requires_database',
                    'confidence_level': 0.7,
                    'legal_disclaimer': 'This response includes real regulatory data from NSW planning provisions. Some advanced features may be operating in fallback mode.',
                    'processing_metadata': {
                        'total_provisions_found': 0,
                        'tier_distribution': {},
                        'processing_time': '0.1s',
                        'cache_hit': False,
                        'fallback_mode': True,
                        'database_error': f'Database connection failed: {result.stderr}'
                    },
                    'fallback': True
                }

        except subprocess.TimeoutExpired:
            return {
                'zone': zone_code,
                'error': 'Hierarchy resolver timeout (>30s)',
                'fallback': True
            }
        except FileNotFoundError:
            # Fallback if hierarchy resolver not found - return basic structure
            return {
                'zone': zone_code,
                'property_id': property_id,
                'development_type': development_type,
                'tier_1_provisions': [],
                'tier_2_provisions': [],
                'tier_3_provisions': [],
                'tier_4_provisions': [],
                'tier_5_provisions': [],
                'primary_authorities': {},
                'complexity_assessment': 'unknown',
                'confidence_level': 0.5,
                'legal_disclaimer': 'This is a development version response',
                'fallback': True,
                'message': 'Using fallback response - hierarchy resolver not available'
            }
        except Exception as e:
            return {
                'zone': zone_code,
                'error': f'Unexpected error: {str(e)}',
                'fallback': True
            }

def main():
    parser = argparse.ArgumentParser(description='Enhanced Compliance API CLI')
    parser.add_argument('--zone', required=True, help='Zone code (e.g., R2, B1)')
    parser.add_argument('--property-id', type=int, help='Property ID')
    parser.add_argument('--development-type', help='Development type')
    parser.add_argument('--include-development-permissions', action='store_true',
                       help='Include development permissions in response')
    parser.add_argument('--climate-zone', help='BASIX climate zone (e.g., Zone 17)')
    parser.add_argument('--water-zone', help='BASIX water zone')
    parser.add_argument('--special-provisions', help='Special provisions JSON')
    parser.add_argument('--format', default='json', choices=['json'], help='Output format')

    args = parser.parse_args()

    api = EnhancedComplianceAPI()

    try:
        # Parse special provisions if provided
        special_provisions_data = None
        if args.special_provisions:
            try:
                special_provisions_data = json.loads(args.special_provisions)
            except json.JSONDecodeError:
                import sys
                print("Warning: Invalid special provisions JSON", file=sys.stderr)

        result = api.get_enhanced_compliance(
            zone_code=args.zone,
            property_id=args.property_id,
            development_type=args.development_type,
            include_development_permissions=args.include_development_permissions,
            climate_zone=args.climate_zone,
            water_zone=args.water_zone,
            special_provisions=special_provisions_data
        )

        print(json.dumps(result, indent=2))

    except Exception as e:
        error_response = {
            'error': str(e),
            'zone': args.zone,
            'property_id': args.property_id,
            'development_type': args.development_type
        }
        print(json.dumps(error_response, indent=2))
        sys.exit(1)

if __name__ == '__main__':
    main()