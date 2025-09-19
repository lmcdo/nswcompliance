#!/usr/bin/env python3
"""
BASIX Compliance Checker
Handles BASIX provisions and requirements integration (PRP-Q1)
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv
import os

load_dotenv()

class BASIXComplianceChecker:
    """Check BASIX compliance requirements based on climate zone and development type"""

    def __init__(self, db_connection=None):
        """Initialize with database connection"""
        if db_connection:
            self.db = db_connection
        else:
            self.db = self._create_connection()

    def _create_connection(self):
        """Create database connection"""
        try:
            return psycopg2.connect(
                host=os.getenv('PGHOST', 'localhost'),
                port=os.getenv('PGPORT', 5432),
                database=os.getenv('PGDATABASE', 'nsw_planning'),
                user=os.getenv('PGUSER', 'postgres'),
                password=os.getenv('PGPASSWORD', '')
            )
        except Exception as e:
            import sys
            print(f"Warning: Could not connect to database: {e}", file=sys.stderr)
            return None

    def get_basix_requirements(self, climate_zone: str, development_type: str = None) -> Dict:
        """Get BASIX requirements for zone and development type"""

        if not self.db:
            return self._get_fallback_basix_requirements(climate_zone, development_type)

        try:
            cursor = self.db.cursor(cursor_factory=RealDictCursor)

            # Build query with optional development type filter
            if development_type:
                query = """
                    SELECT
                        climate_zone,
                        development_type,
                        energy_reduction_target,
                        thermal_comfort_rating,
                        water_reduction_target,
                        water_fixture_rating,
                        min_insulation_r_value,
                        max_glazing_percentage,
                        tier_level,
                        source_document
                    FROM basix_provisions
                    WHERE climate_zone = %s
                    AND development_type = %s
                """
                cursor.execute(query, (climate_zone, development_type))
            else:
                # Get all development types for this climate zone
                query = """
                    SELECT
                        climate_zone,
                        development_type,
                        energy_reduction_target,
                        thermal_comfort_rating,
                        water_reduction_target,
                        water_fixture_rating,
                        min_insulation_r_value,
                        max_glazing_percentage,
                        tier_level,
                        source_document
                    FROM basix_provisions
                    WHERE climate_zone = %s
                    ORDER BY development_type
                """
                cursor.execute(query, (climate_zone,))

            results = cursor.fetchall()

            if results:
                return {
                    'climate_zone': climate_zone,
                    'development_type': development_type,
                    'basix_provisions': [self._format_basix_provision(row) for row in results],
                    'tier_level': 1,  # BASIX is always Tier 1
                    'document_type': 'BASIX',
                    'has_requirements': True
                }
            else:
                # No specific requirements found - return fallback
                return self._get_fallback_basix_requirements(climate_zone, development_type)

        except Exception as e:
            import sys
            print(f"Warning: Database query failed: {e}", file=sys.stderr)
            return self._get_fallback_basix_requirements(climate_zone, development_type)

    def _format_basix_provision(self, data: Dict) -> Dict:
        """Format BASIX requirement as provision"""

        provisions = []

        # Energy efficiency provision
        if data.get('energy_reduction_target'):
            provisions.append({
                'id': f"basix_energy_{data['development_type']}",
                'provision_type': 'energy_efficiency',
                'measurement_context': 'energy_reduction',
                'numeric_value': float(data['energy_reduction_target']),
                'unit': 'percent',
                'provision_text': f"Achieve {data['energy_reduction_target']}% reduction in energy consumption compared to baseline",
                'clause_reference': 'BASIX Energy Target',
                'document_type': 'BASIX',
                'document_name': 'Building Sustainability Index',
                'tier_level': 1,
                'authority_level': 100,
                'confidence_level': 1.0,
                'extraction_confidence': 1.0
            })

        # Water efficiency provision
        if data.get('water_reduction_target'):
            provisions.append({
                'id': f"basix_water_{data['development_type']}",
                'provision_type': 'water_efficiency',
                'measurement_context': 'water_reduction',
                'numeric_value': float(data['water_reduction_target']),
                'unit': 'percent',
                'provision_text': f"Achieve {data['water_reduction_target']}% reduction in water consumption compared to baseline",
                'clause_reference': 'BASIX Water Target',
                'document_type': 'BASIX',
                'document_name': 'Building Sustainability Index',
                'tier_level': 1,
                'authority_level': 100,
                'confidence_level': 1.0,
                'extraction_confidence': 1.0
            })

        # Thermal comfort provision
        if data.get('thermal_comfort_rating'):
            provisions.append({
                'id': f"basix_thermal_{data['development_type']}",
                'provision_type': 'thermal_comfort',
                'measurement_context': 'thermal_comfort_rating',
                'numeric_value': float(data['thermal_comfort_rating']),
                'unit': 'stars',
                'provision_text': f"Achieve minimum {data['thermal_comfort_rating']} star thermal comfort rating",
                'clause_reference': 'BASIX Thermal Comfort',
                'document_type': 'BASIX',
                'document_name': 'Building Sustainability Index',
                'tier_level': 1,
                'authority_level': 100,
                'confidence_level': 1.0,
                'extraction_confidence': 1.0
            })

        return {
            'development_type': data['development_type'],
            'climate_zone': data['climate_zone'],
            'provisions': provisions,
            'source_document': data.get('source_document', 'BASIX SEPP 2004')
        }

    def _get_fallback_basix_requirements(self, climate_zone: str, development_type: str = None) -> Dict:
        """Fallback BASIX requirements when database unavailable"""

        # Extract zone number from climate zone string
        zone_num = self._extract_zone_number(climate_zone)

        # Default targets based on climate zone
        if zone_num >= 20:
            energy_target = 50.0
            thermal_rating = 6.0
        elif zone_num >= 18:
            energy_target = 45.0
            thermal_rating = 5.5
        else:
            energy_target = 40.0
            thermal_rating = 5.0

        # Water target is consistent across NSW
        water_target = 40.0

        # Adjust for development type
        if development_type and 'residential_flat' in development_type:
            energy_target -= 5.0  # RFBs have slightly lower targets
            thermal_rating -= 0.5

        fallback_provision = {
            'development_type': development_type or 'dwelling_house',
            'climate_zone': climate_zone,
            'provisions': [
                {
                    'id': f"basix_energy_fallback",
                    'provision_type': 'energy_efficiency',
                    'measurement_context': 'energy_reduction',
                    'numeric_value': energy_target,
                    'unit': 'percent',
                    'provision_text': f"Achieve {energy_target}% reduction in energy consumption (estimated for {climate_zone})",
                    'clause_reference': 'BASIX Energy Target',
                    'document_type': 'BASIX',
                    'document_name': 'Building Sustainability Index',
                    'tier_level': 1,
                    'authority_level': 95,  # Slightly lower for fallback
                    'confidence_level': 0.85,  # Lower confidence for estimated values
                    'extraction_confidence': 0.85
                },
                {
                    'id': f"basix_water_fallback",
                    'provision_type': 'water_efficiency',
                    'measurement_context': 'water_reduction',
                    'numeric_value': water_target,
                    'unit': 'percent',
                    'provision_text': f"Achieve {water_target}% reduction in water consumption",
                    'clause_reference': 'BASIX Water Target',
                    'document_type': 'BASIX',
                    'document_name': 'Building Sustainability Index',
                    'tier_level': 1,
                    'authority_level': 95,
                    'confidence_level': 0.90,  # Water targets more consistent
                    'extraction_confidence': 0.90
                }
            ],
            'source_document': 'BASIX SEPP 2004 (fallback estimates)'
        }

        return {
            'climate_zone': climate_zone,
            'development_type': development_type,
            'basix_provisions': [fallback_provision],
            'tier_level': 1,
            'document_type': 'BASIX',
            'has_requirements': True,
            'fallback': True
        }

    def _extract_zone_number(self, climate_zone: str) -> int:
        """Extract numeric zone from climate zone string"""
        import re
        match = re.search(r'(\d+)', climate_zone)
        return int(match.group(1)) if match else 17  # Default to zone 17

    def process_basix_from_api(self, basix_data: Dict) -> Dict:
        """Process BASIX data from NSW Planning API"""

        climate_zone = basix_data.get('climate_zone')
        water_zone = basix_data.get('water_zone')

        if not climate_zone:
            return {
                'basix_provisions': [],
                'has_requirements': False,
                'message': 'No BASIX climate zone provided'
            }

        # Get requirements for this climate zone
        requirements = self.get_basix_requirements(climate_zone)

        # Add water zone information if available
        if water_zone:
            requirements['water_zone'] = water_zone

        # Add API source metadata
        requirements['api_source'] = {
            'climate_zone_from_api': climate_zone,
            'water_zone_from_api': water_zone,
            'extraction_method': 'NSW Planning Portal Special Provisions'
        }

        return requirements

    def integrate_with_compliance_response(self, compliance_data: Dict, basix_data: Dict) -> Dict:
        """Integrate BASIX provisions into compliance response"""

        if not basix_data.get('has_requirements'):
            return compliance_data

        basix_requirements = self.process_basix_from_api(basix_data)

        # Add BASIX provisions to Tier 1 (highest authority)
        if 'tier_1_provisions' not in compliance_data:
            compliance_data['tier_1_provisions'] = []

        # Add each BASIX provision to tier 1
        for basix_provision in basix_requirements.get('basix_provisions', []):
            for provision in basix_provision.get('provisions', []):
                compliance_data['tier_1_provisions'].append(provision)

        # Update metadata
        if 'processing_metadata' not in compliance_data:
            compliance_data['processing_metadata'] = {}

        compliance_data['processing_metadata']['basix_integrated'] = True
        compliance_data['processing_metadata']['basix_climate_zone'] = basix_requirements.get('climate_zone')
        compliance_data['processing_metadata']['basix_provisions_added'] = sum(
            len(bp.get('provisions', [])) for bp in basix_requirements.get('basix_provisions', [])
        )

        # Add BASIX summary to response
        compliance_data['basix_summary'] = {
            'climate_zone': basix_requirements.get('climate_zone'),
            'water_zone': basix_requirements.get('water_zone'),
            'has_requirements': True,
            'provision_count': compliance_data['processing_metadata']['basix_provisions_added'],
            'source': 'NSW Planning Portal + BASIX Database'
        }

        return compliance_data

    def close_connection(self):
        """Close database connection"""
        if self.db:
            self.db.close()