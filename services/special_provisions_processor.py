from db_config import get_connection
from services.sepp_quantitative_extractor import SEPPQuantitativeExtractor
from typing import Dict, List, Optional, Tuple
import json
import re

class SpecialProvisionsProcessor:
    """Comprehensive processor for NSW Planning API special provisions"""

    def __init__(self):
        self.db = get_connection()
        self.sepp_extractor = SEPPQuantitativeExtractor()
        self._load_provision_registry()

    def _load_provision_registry(self):
        """Load provision processing rules from database"""
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT
                provision_type,
                provision_category,
                default_tier_level,
                authority_level,
                requires_specialist,
                has_numeric_thresholds
            FROM special_provisions_registry
            WHERE active = TRUE
        """)

        self.registry = {}
        for row in cursor.fetchall():
            key = (row[0], row[1]) if row[1] else row[0]
            self.registry[key] = {
                'tier_level': row[2],
                'authority_level': row[3],
                'requires_specialist': row[4],
                'has_numeric_thresholds': row[5]
            }

    def process_special_provisions(self, raw_provisions: List[Dict],
                                 zone_code: str, development_type: str = None) -> Dict:
        """Process raw NSW API special provisions into tiered compliance structure"""

        results = {
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
                'provision_types': set(),
                'requires_specialist': False,
                'quantitative_extractions': 0
            }
        }

        for provision in raw_provisions:
            processed = self._process_single_provision(provision, zone_code, development_type)

            if processed:
                # Add to appropriate tier
                tier_key = f'tier_{processed["tier_level"]}_provisions'
                if tier_key in results:
                    results[tier_key].append(processed)

                # Track metadata
                results['metadata']['total_processed'] += 1
                results['metadata']['provision_types'].add(processed['provision_type'])

                if processed.get('requires_specialist'):
                    results['metadata']['requires_specialist'] = True

                if processed.get('numeric_value') is not None:
                    results['metadata']['quantitative_extractions'] += 1

                # Special handling
                if processed['provision_type'] == 'Climate Zones':
                    results['basix_requirements'] = self._process_basix_requirements(
                        provision, development_type
                    )
                elif processed['provision_type'] in ['Flood Planning', 'Bushfire Prone Land']:
                    results['hazard_assessments'].append(
                        self._create_hazard_assessment(processed)
                    )
                elif processed['provision_type'] in ['Heritage', 'Biodiversity', 'Acid Sulfate Soils']:
                    results['environmental_constraints'].append(
                        self._create_environmental_constraint(processed)
                    )
                elif processed['provision_type'] == 'State Environmental Planning Policy':
                    results['sepp_extractions'].append(processed)

        # Convert set to list for JSON serialization
        results['metadata']['provision_types'] = list(results['metadata']['provision_types'])

        return results

    def _process_single_provision(self, provision: Dict, zone_code: str,
                                development_type: str = None) -> Optional[Dict]:
        """Process a single provision into structured format"""

        provision_type = provision.get('Type', '')
        category = provision.get('Category', '')

        # Look up in registry
        registry_key = (provision_type, category) if category else provision_type
        config = self.registry.get(registry_key) or self.registry.get(provision_type)

        if not config:
            # Unknown provision type - assign to tier 3 with moderate authority
            config = {
                'tier_level': 3,
                'authority_level': 70,
                'requires_specialist': False,
                'has_numeric_thresholds': False
            }

        # Process based on type
        if provision_type == 'Climate Zones':
            return self._process_climate_zone(provision, config)
        elif provision_type == 'State Environmental Planning Policy':
            return self._process_sepp(provision, config)
        elif provision_type == 'Flood Planning':
            return self._process_flood_planning(provision, config, zone_code)
        elif provision_type == 'Bushfire Prone Land':
            return self._process_bushfire(provision, config)
        elif provision_type == 'Heritage':
            return self._process_heritage(provision, config)
        elif provision_type == 'Acid Sulfate Soils':
            return self._process_acid_sulfate(provision, config)
        else:
            return self._process_generic_provision(provision, config)

    def _process_climate_zone(self, provision: Dict, config: Dict) -> Dict:
        """Process BASIX climate zone provision"""
        climate_zone = provision.get('Class', '')

        return {
            'provision_type': 'Climate Zones',
            'tier_level': 1,
            'authority_level': 100,
            'document_type': 'BASIX',
            'document_name': 'Building Sustainability Index',
            'clause_reference': f'Climate {climate_zone}',
            'provision_text': f'Property is in BASIX Climate {climate_zone}',
            'measurement_context': 'climate_zone',
            'climate_zone': climate_zone,
            'requires_specialist': False,
            'confidence_level': 1.0,
            'implications': [
                'BASIX certificate required for new residential development',
                'Energy and water targets apply based on climate zone'
            ]
        }

    def _process_sepp(self, provision: Dict, config: Dict) -> Dict:
        """Process State Environmental Planning Policy"""
        epi_name = provision.get('EPI Name', '')
        clause = provision.get('Legislative Clause', '')

        # Extract SEPP type
        sepp_type = self._identify_sepp_type(epi_name)

        # Try to extract quantitative values
        quantitative_data = None
        if sepp_type and clause:
            quantitative_data = self.sepp_extractor.extract_from_sepp_clause(sepp_type, clause)

        provision_text = f"SEPP applies: {epi_name}"
        if clause:
            provision_text += f" (Clause {clause})"

        result = {
            'provision_type': 'State Environmental Planning Policy',
            'tier_level': 1,
            'authority_level': 95,
            'document_type': 'SEPP',
            'document_name': epi_name,
            'clause_reference': clause or 'General',
            'provision_text': provision_text,
            'sepp_type': sepp_type,
            'requires_specialist': False,
            'confidence_level': 0.9
        }

        # Add quantitative data if extracted
        if quantitative_data:
            result.update({
                'measurement_context': quantitative_data['measurement_context'],
                'numeric_value': quantitative_data['numeric_value'],
                'unit': quantitative_data['unit'],
                'confidence_level': quantitative_data['confidence']
            })

        return result

    def _process_flood_planning(self, provision: Dict, config: Dict, zone_code: str) -> Dict:
        """Process flood planning provision"""
        category = provision.get('Category', '')
        level = provision.get('Level', '')

        return {
            'provision_type': 'Flood Planning',
            'tier_level': 1,
            'authority_level': 95,
            'document_type': 'Flood Planning',
            'document_name': 'Flood Planning Controls',
            'clause_reference': f'Flood Planning - {level}',
            'provision_text': f'Property is in {category} - {level}',
            'measurement_context': 'flood_planning_level',
            'flood_category': category,
            'flood_level': level,
            'requires_specialist': True,
            'confidence_level': 0.95,
            'implications': [
                'Flood Impact Assessment required',
                'Minimum floor levels apply',
                'Emergency evacuation plan required'
            ],
            'actions_required': [
                'Engage flood consultant',
                'Prepare Flood Impact Assessment',
                'Design floor levels above flood level'
            ]
        }

    def _process_bushfire(self, provision: Dict, config: Dict) -> Dict:
        """Process bushfire prone land provision"""
        category = provision.get('Category', '')
        buffer = provision.get('Buffer', '')

        bal_rating = self._estimate_bal_rating(category, buffer)

        return {
            'provision_type': 'Bushfire Prone Land',
            'tier_level': 1,
            'authority_level': 95,
            'document_type': 'Bushfire Planning',
            'document_name': 'Planning for Bush Fire Protection',
            'clause_reference': f'Bushfire - {category}',
            'provision_text': f'Property is bushfire prone - {category}',
            'measurement_context': 'bushfire_attack_level',
            'bushfire_category': category,
            'estimated_bal': bal_rating,
            'numeric_value': bal_rating,
            'unit': 'BAL',
            'requires_specialist': True,
            'confidence_level': 0.9,
            'implications': [
                'Bushfire Assessment Report required',
                f'Construction to BAL-{bal_rating} standard',
                'Asset Protection Zone required'
            ]
        }

    def _process_heritage(self, provision: Dict, config: Dict) -> Dict:
        """Process heritage provision"""
        heritage_type = provision.get('Heritage Type', '')
        item_name = provision.get('Item Name', '')

        return {
            'provision_type': 'Heritage',
            'tier_level': 2,
            'authority_level': 90,
            'document_type': 'Heritage',
            'document_name': 'Heritage Conservation',
            'clause_reference': 'Heritage Item',
            'provision_text': f'{heritage_type}: {item_name}',
            'heritage_type': heritage_type,
            'heritage_item': item_name,
            'requires_specialist': True,
            'confidence_level': 0.95,
            'implications': [
                'Heritage Impact Statement required',
                'Heritage architect consultation recommended'
            ]
        }

    def _process_acid_sulfate(self, provision: Dict, config: Dict) -> Dict:
        """Process acid sulfate soils provision"""
        soil_class = provision.get('Class', '')
        action = provision.get('Action', '')

        return {
            'provision_type': 'Acid Sulfate Soils',
            'tier_level': 2,
            'authority_level': 85,
            'document_type': 'Environmental',
            'document_name': 'Acid Sulfate Soils Management',
            'clause_reference': f'ASS {soil_class}',
            'provision_text': f'Property has {soil_class} acid sulfate soils - {action}',
            'soil_class': soil_class,
            'required_action': action,
            'requires_specialist': True,
            'confidence_level': 0.9
        }

    def _process_generic_provision(self, provision: Dict, config: Dict) -> Dict:
        """Process unknown/generic provision"""
        provision_type = provision.get('Type', 'Unknown')
        category = provision.get('Category', '')

        return {
            'provision_type': provision_type,
            'tier_level': config['tier_level'],
            'authority_level': config['authority_level'],
            'document_type': 'Special Provision',
            'document_name': f'{provision_type} ({category})' if category else provision_type,
            'clause_reference': 'General',
            'provision_text': f'{provision_type} provision applies',
            'requires_specialist': config['requires_specialist'],
            'confidence_level': 0.7
        }

    def _process_basix_requirements(self, provision: Dict, development_type: str) -> Optional[Dict]:
        """Get BASIX requirements for climate zone"""
        climate_zone = provision.get('Class', '')

        if not climate_zone or not development_type:
            return None

        # Import BASIX checker from PRP-Q1
        try:
            from services.basix_compliance_checker import BASIXComplianceChecker
            checker = BASIXComplianceChecker()
            return checker.process_basix_for_compliance(climate_zone, development_type)
        except ImportError:
            return None

    def _identify_sepp_type(self, epi_name: str) -> Optional[str]:
        """Identify SEPP type from EPI name"""
        epi_lower = epi_name.lower()

        if 'housing' in epi_lower and '2021' in epi_lower:
            return 'SEPP_HOUSING_2021'
        elif 'exempt' in epi_lower and 'complying' in epi_lower:
            return 'SEPP_EXEMPT_2008'
        elif 'planning systems' in epi_lower:
            return 'SEPP_PLANNING_SYSTEMS_2021'
        elif 'resilience' in epi_lower or 'hazards' in epi_lower:
            return 'SEPP_RESILIENCE_HAZARDS_2021'

        return None

    def _estimate_bal_rating(self, category: str, buffer: str) -> float:
        """Estimate BAL rating from bushfire category"""
        if 'category 1' in category.lower():
            return 29 if '100m' in buffer else 40
        elif 'category 2' in category.lower():
            return 19 if '100m' in buffer else 29
        return 12.5

    def _create_hazard_assessment(self, provision: Dict) -> Dict:
        """Create hazard assessment summary"""
        return {
            'hazard_type': provision['provision_type'],
            'risk_level': 'high' if provision['tier_level'] == 1 else 'moderate',
            'specialist_required': provision['requires_specialist'],
            'key_requirements': provision.get('implications', []),
            'actions': provision.get('actions_required', [])
        }

    def _create_environmental_constraint(self, provision: Dict) -> Dict:
        """Create environmental constraint summary"""
        return {
            'constraint_type': provision['provision_type'],
            'impact_level': 'significant' if provision['requires_specialist'] else 'moderate',
            'assessment_required': provision['requires_specialist'],
            'provision_details': provision.get('provision_text', '')
        }

# Test the processor
if __name__ == "__main__":
    processor = SpecialProvisionsProcessor()

    # Test with sample NSW API special provisions data
    test_provisions = [
        {
            "Type": "Climate Zones",
            "Class": "Zone 17",
            "Map Type": "CLM"
        },
        {
            "Type": "State Environmental Planning Policy",
            "EPI Name": "SEPP (Housing) 2021",
            "Legislative Clause": "3.31"
        },
        {
            "Type": "Flood Planning",
            "Category": "Flood Planning Area",
            "Level": "1:100 Year"
        }
    ]

    result = processor.process_special_provisions(test_provisions, 'R2', 'dwelling_house')

    print("Processing Results:")
    print(f"Total processed: {result['metadata']['total_processed']}")
    print(f"Tier 1 provisions: {len(result['tier_1_provisions'])}")
    print(f"Quantitative extractions: {result['metadata']['quantitative_extractions']}")
    print(f"Specialist required: {result['metadata']['requires_specialist']}")
