from services.special_provisions_processor import SpecialProvisionsProcessor
from typing import Dict, List, Optional
import json

class SpecialProvisionsIntegrationService:
    """Integrate special provisions processing with compliance checking"""

    def __init__(self):
        self.processor = SpecialProvisionsProcessor()

    def integrate_with_compliance_check(self,
                                      planning_api_data: Dict,
                                      zone_code: str,
                                      development_type: str = None,
                                      property_id: int = None) -> Dict:
        """
        Integrate special provisions processing with compliance checking
        """

        # Extract special provisions from NSW Planning API data
        special_provisions = self._extract_special_provisions_from_api(planning_api_data)

        if not special_provisions:
            return self._create_empty_response()

        # Process provisions through the engine
        processed = self.processor.process_special_provisions(
            special_provisions, zone_code, development_type
        )

        # Enhance with compliance context
        enhanced_result = self._enhance_with_compliance_context(
            processed, zone_code, development_type, property_id
        )

        return enhanced_result

    def _extract_special_provisions_from_api(self, planning_api_data: Dict) -> List[Dict]:
        """Extract special provisions from NSW Planning API response"""
        provisions = []

        # Handle different API response formats
        if 'layers' in planning_api_data:
            # Layer-based format
            for layer in planning_api_data['layers']:
                if layer.get('layerName') == 'Special Provisions':
                    provisions.extend(layer.get('results', []))

        elif 'special_provisions' in planning_api_data:
            # Direct format
            provisions = planning_api_data['special_provisions']

        elif isinstance(planning_api_data, list):
            # Direct list format
            provisions = planning_api_data

        return provisions

    def _enhance_with_compliance_context(self, processed: Dict, zone_code: str,
                                       development_type: str, property_id: int) -> Dict:
        """Enhance processed provisions with compliance context"""

        enhanced = {
            'special_provisions_processing': processed,
            'compliance_summary': {
                'zone_code': zone_code,
                'development_type': development_type,
                'property_id': property_id,
                'total_provisions': processed['metadata']['total_processed'],
                'tier_breakdown': self._calculate_tier_breakdown(processed),
                'specialist_assessment_required': processed['metadata']['requires_specialist'],
                'quantitative_requirements': processed['metadata']['quantitative_extractions'],
                'key_compliance_points': self._extract_key_compliance_points(processed)
            },
            'integration_metadata': {
                'processing_timestamp': processed['metadata'].get('timestamp'),
                'basix_applicable': processed['basix_requirements'] is not None,
                'hazards_identified': len(processed['hazard_assessments']) > 0,
                'environmental_constraints': len(processed['environmental_constraints']) > 0,
                'sepp_provisions_found': len(processed['sepp_extractions']) > 0
            }
        }

        return enhanced

    def _calculate_tier_breakdown(self, processed: Dict) -> Dict:
        """Calculate breakdown of provisions by tier"""
        return {
            'tier_1': len(processed.get('tier_1_provisions', [])),
            'tier_2': len(processed.get('tier_2_provisions', [])),
            'tier_3': len(processed.get('tier_3_provisions', [])),
            'tier_4': len(processed.get('tier_4_provisions', [])),
            'tier_5': len(processed.get('tier_5_provisions', []))
        }

    def _extract_key_compliance_points(self, processed: Dict) -> List[str]:
        """Extract key compliance points for summary"""
        points = []

        # Add BASIX requirements
        if processed['basix_requirements']:
            points.append("BASIX certificate required for residential development")

        # Add hazard assessments
        for hazard in processed['hazard_assessments']:
            if hazard['specialist_required']:
                points.append(f"{hazard['hazard_type']} specialist assessment required")

        # Add environmental constraints
        for constraint in processed['environmental_constraints']:
            if constraint['assessment_required']:
                points.append(f"{constraint['constraint_type']} assessment may be required")

        # Add SEPP requirements
        for sepp in processed['sepp_extractions']:
            if sepp.get('numeric_value'):
                points.append(f"SEPP requirement: {sepp['measurement_context']} = {sepp['numeric_value']} {sepp['unit']}")

        return points

    def _create_empty_response(self) -> Dict:
        """Create empty response when no special provisions found"""
        return {
            'special_provisions_processing': {
                'tier_1_provisions': [],
                'tier_2_provisions': [],
                'tier_3_provisions': [],
                'tier_4_provisions': [],
                'tier_5_provisions': [],
                'basix_requirements': None,
                'hazard_assessments': [],
                'environmental_constraints': [],
                'sepp_extractions': [],
                'metadata': {
                    'total_processed': 0,
                    'provision_types': [],
                    'requires_specialist': False,
                    'quantitative_extractions': 0
                }
            },
            'compliance_summary': {
                'total_provisions': 0,
                'specialist_assessment_required': False,
                'key_compliance_points': []
            },
            'integration_metadata': {
                'basix_applicable': False,
                'hazards_identified': False,
                'environmental_constraints': False,
                'sepp_provisions_found': False
            }
        }

# Test the integration service
if __name__ == "__main__":
    service = SpecialProvisionsIntegrationService()

    # Test with sample planning API data
    test_api_data = {
        'layers': [
            {
                'layerName': 'Special Provisions',
                'results': [
                    {
                        "Type": "Climate Zones",
                        "Class": "Zone 17",
                        "Map Type": "CLM"
                    },
                    {
                        "Type": "State Environmental Planning Policy",
                        "EPI Name": "SEPP (Housing) 2021",
                        "Legislative Clause": "3.31"
                    }
                ]
            }
        ]
    }

    result = service.integrate_with_compliance_check(
        test_api_data, 'R2', 'dwelling_house', 12345
    )

    print("Integration Results:")
    print(f"Total provisions: {result['compliance_summary']['total_provisions']}")
    print(f"BASIX applicable: {result['integration_metadata']['basix_applicable']}")
    print(f"Specialist required: {result['compliance_summary']['specialist_assessment_required']}")

    if result['compliance_summary']['key_compliance_points']:
        print("Key compliance points:")
        for point in result['compliance_summary']['key_compliance_points']:
            print(f"  - {point}")
