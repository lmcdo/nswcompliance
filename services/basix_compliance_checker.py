from db_config import get_connection
from typing import Dict, List, Optional
import json

class BASIXComplianceChecker:
    """BASIX compliance checking service for NSW planning"""

    def __init__(self):
        pass  # Connection created per request

    def get_basix_requirements(self, climate_zone: str, development_type: str) -> Optional[Dict]:
        """Get BASIX requirements for zone and development type"""
        conn = get_connection()
        cursor = conn.cursor()

        query = """
            SELECT
                energy_reduction_target,
                thermal_comfort_rating,
                water_reduction_target,
                water_fixture_rating,
                min_insulation_r_value,
                max_glazing_percentage,
                source_document
            FROM basix_provisions
            WHERE climate_zone = %s
            AND development_type = %s
        """

        cursor.execute(query, (climate_zone, development_type))
        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                'tier_level': 1,  # BASIX is always Tier 1
                'document_type': 'BASIX',
                'document_name': 'Building Sustainability Index',
                'provisions': self._format_basix_provisions(result, climate_zone)
            }
        return None

    def _format_basix_provisions(self, data: tuple, climate_zone: str) -> List[Dict]:
        """Format BASIX requirements as tier 1 provisions"""
        provisions = []

        energy_target, thermal_rating, water_target, water_rating, insulation, glazing, source = data

        if energy_target:
            provisions.append({
                'provision_type': 'energy_efficiency',
                'measurement_context': 'energy_reduction',
                'numeric_value': float(energy_target),
                'unit': 'percent',
                'provision_text': f"Achieve {energy_target}% reduction in energy consumption compared to reference building",
                'clause_reference': f'BASIX Energy Target - {climate_zone}',
                'authority_level': 100,
                'confidence_level': 1.0
            })

        if water_target:
            provisions.append({
                'provision_type': 'water_efficiency',
                'measurement_context': 'water_reduction',
                'numeric_value': float(water_target),
                'unit': 'percent',
                'provision_text': f"Achieve {water_target}% reduction in water consumption compared to reference building",
                'clause_reference': f'BASIX Water Target - {climate_zone}',
                'authority_level': 100,
                'confidence_level': 1.0
            })

        if thermal_rating:
            provisions.append({
                'provision_type': 'thermal_comfort',
                'measurement_context': 'star_rating',
                'numeric_value': float(thermal_rating),
                'unit': 'stars',
                'provision_text': f"Achieve minimum {thermal_rating} star thermal comfort rating",
                'clause_reference': f'BASIX Thermal Comfort - {climate_zone}',
                'authority_level': 100,
                'confidence_level': 1.0
            })

        if insulation:
            provisions.append({
                'provision_type': 'insulation',
                'measurement_context': 'r_value',
                'numeric_value': float(insulation),
                'unit': 'm2K/W',
                'provision_text': f"Minimum insulation R-value of {insulation}",
                'clause_reference': f'BASIX Insulation - {climate_zone}',
                'authority_level': 100,
                'confidence_level': 1.0
            })

        return provisions

    def process_basix_for_compliance(self, climate_zone: str, development_type: str) -> Dict:
        """Process BASIX requirements for compliance checking"""
        basix_reqs = self.get_basix_requirements(climate_zone, development_type)

        if not basix_reqs:
            return {
                'basix_applicable': False,
                'message': f'No BASIX requirements found for {climate_zone} / {development_type}'
            }

        return {
            'basix_applicable': True,
            'climate_zone': climate_zone,
            'development_type': development_type,
            'tier_1_provisions': basix_reqs['provisions'],
            'document_type': 'BASIX',
            'authority_level': 100,
            'specialist_required': False,
            'certificate_required': True,
            'assessment_notes': [
                'BASIX certificate must be obtained before development approval',
                'Design must demonstrate compliance with energy and water targets',
                'Final construction must match BASIX certificate commitments'
            ]
        }

# Test the service
if __name__ == "__main__":
    checker = BASIXComplianceChecker()

    # Test various climate zones and development types
    test_cases = [
        ('Zone 17', 'dwelling_house'),
        ('Zone 18', 'residential_flat_building'),
        ('Zone 19', 'dual_occupancy')
    ]

    for climate_zone, dev_type in test_cases:
        result = checker.process_basix_for_compliance(climate_zone, dev_type)
        print(f"BASIX check for {climate_zone} / {dev_type}:")
        print(f"  Applicable: {result['basix_applicable']}")
        if result['basix_applicable']:
            print(f"  Provisions: {len(result['tier_1_provisions'])}")
            for provision in result['tier_1_provisions']:
                print(f"    - {provision['provision_text']}")
        print()