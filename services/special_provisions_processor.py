#!/usr/bin/env python3
"""
Special Provisions Processor
Handles special provisions from NSW Planning API (PRP-Q2)
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv
import os
import re
import json

load_dotenv()

class SpecialProvisionsProcessor:
    """Process special provisions from NSW Planning API into tiered compliance structure"""

    def __init__(self, db_connection=None):
        """Initialize with database connection"""
        if db_connection:
            self.db = db_connection
        else:
            self.db = self._create_connection()

        self._load_provision_registry()

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

    def _load_provision_registry(self):
        """Load provision processing rules from database"""
        self.registry = {}

        if not self.db:
            self._load_fallback_registry()
            return

        try:
            cursor = self.db.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT
                    provision_type,
                    provision_category,
                    default_tier_level,
                    authority_level,
                    requires_specialist,
                    has_numeric_thresholds,
                    legislation_reference
                FROM special_provisions_registry
                WHERE active = TRUE
            """)

            for row in cursor.fetchall():
                key = (row['provision_type'], row['provision_category']) if row['provision_category'] else row['provision_type']
                self.registry[key] = {
                    'tier_level': row['default_tier_level'],
                    'authority_level': row['authority_level'],
                    'requires_specialist': row['requires_specialist'],
                    'has_numeric_thresholds': row['has_numeric_thresholds'],
                    'legislation_reference': row['legislation_reference']
                }

        except Exception as e:
            import sys
            print(f"Warning: Could not load registry from database: {e}", file=sys.stderr)
            self._load_fallback_registry()

    def _load_fallback_registry(self):
        """Load fallback provision registry when database unavailable"""
        self.registry = {
            # Tier 1 - Fully Authoritative
            'Climate Zones': {'tier_level': 1, 'authority_level': 100, 'requires_specialist': False, 'has_numeric_thresholds': True},
            'Flood Planning': {'tier_level': 1, 'authority_level': 95, 'requires_specialist': True, 'has_numeric_thresholds': True},
            'Bushfire Prone Land': {'tier_level': 1, 'authority_level': 95, 'requires_specialist': True, 'has_numeric_thresholds': True},
            'State Environmental Planning Policy': {'tier_level': 1, 'authority_level': 95, 'requires_specialist': False, 'has_numeric_thresholds': True},

            # Tier 2 - High Authority
            'Acid Sulfate Soils': {'tier_level': 2, 'authority_level': 85, 'requires_specialist': True, 'has_numeric_thresholds': False},
            'Heritage': {'tier_level': 2, 'authority_level': 90, 'requires_specialist': True, 'has_numeric_thresholds': False},
            'Coastal Management': {'tier_level': 2, 'authority_level': 90, 'requires_specialist': True, 'has_numeric_thresholds': True},

            # Tier 3 - Moderate Authority
            'Biodiversity': {'tier_level': 3, 'authority_level': 75, 'requires_specialist': True, 'has_numeric_thresholds': False},
            'Contaminated Land': {'tier_level': 3, 'authority_level': 80, 'requires_specialist': True, 'has_numeric_thresholds': False}
        }

    def process_special_provisions(self, raw_provisions: List[Dict], zone_code: str, development_type: Optional[str] = None) -> Dict:
        """Process raw special provisions into tiered compliance structure"""

        results = {
            'tier_1_provisions': [],
            'tier_2_provisions': [],
            'tier_3_provisions': [],
            'tier_4_provisions': [],
            'tier_5_provisions': [],
            'hazard_assessments': [],
            'environmental_constraints': [],
            'sepp_provisions': [],
            'metadata': {
                'total_processed': 0,
                'provision_types': set(),
                'requires_specialist': False,
                'has_hazards': False,
                'has_environmental': False
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

                # Special handling for hazards and environmental
                if processed['provision_type'] in ['Flood Planning', 'Bushfire Prone Land']:
                    results['hazard_assessments'].append(self._create_hazard_assessment(processed))
                    results['metadata']['has_hazards'] = True

                if processed['provision_type'] in ['Acid Sulfate Soils', 'Biodiversity', 'Heritage']:
                    results['environmental_constraints'].append(self._create_environmental_constraint(processed))
                    results['metadata']['has_environmental'] = True

                if processed['provision_type'] == 'State Environmental Planning Policy':
                    results['sepp_provisions'].append(processed)

        # Convert set to list for JSON serialization
        results['metadata']['provision_types'] = list(results['metadata']['provision_types'])

        return results

    def _process_single_provision(self, provision: Dict, zone_code: str, development_type: Optional[str]) -> Optional[Dict]:
        """Process a single provision into structured format"""

        provision_type = provision.get('Type', '')
        category = provision.get('Category', '')

        # Look up in registry
        registry_key = (provision_type, category) if category else provision_type
        if registry_key not in self.registry and provision_type not in self.registry:
            # Unknown provision type - assign to Tier 3 by default
            config = {'tier_level': 3, 'authority_level': 70, 'requires_specialist': True, 'has_numeric_thresholds': False}
        else:
            config = self.registry.get(registry_key) or self.registry.get(provision_type)

        # Process based on type
        if provision_type == 'Climate Zones':
            return self._process_climate_zone(provision, config)
        elif provision_type == 'State Environmental Planning Policy':
            return self._process_sepp(provision, config)
        elif provision_type == 'Flood Planning':
            return self._process_flood(provision, config, zone_code)
        elif provision_type == 'Bushfire Prone Land':
            return self._process_bushfire(provision, config)
        elif provision_type == 'Acid Sulfate Soils':
            return self._process_acid_sulfate(provision, config)
        elif provision_type == 'Heritage':
            return self._process_heritage(provision, config)
        elif provision_type == 'Coastal Management':
            return self._process_coastal(provision, config)
        else:
            return self._process_generic(provision, config, provision_type)

    def _process_climate_zone(self, provision: Dict, config: Dict) -> Dict:
        """Process BASIX climate zone"""
        zone = provision.get('Class', '')

        return {
            'id': f"climate_zone_{zone.replace(' ', '_').lower()}",
            'provision_type': 'Climate Zones',
            'tier_level': 1,  # BASIX is always Tier 1
            'authority_level': 100,
            'document_type': 'BASIX',
            'document_name': 'Building Sustainability Index',
            'clause_reference': f'Climate {zone}',
            'provision_text': f'Property is in BASIX Climate {zone} - sustainability targets apply',
            'measurement_context': 'climate_zone',
            'numeric_value': self._extract_zone_number(zone),
            'unit': 'zone_number',
            'requires_specialist': False,
            'confidence_level': 1.0,
            'extraction_confidence': 1.0,
            'implications': [
                'BASIX certificate required for new residential development',
                'Energy and water targets apply based on climate zone'
            ],
            'actions_required': [
                'Engage accredited BASIX assessor',
                'Submit BASIX certificate with development application'
            ]
        }

    def _process_sepp(self, provision: Dict, config: Dict) -> Dict:
        """Process State Environmental Planning Policy"""
        epi_name = provision.get('EPI Name', '')
        clause = provision.get('Legislative Clause', '')
        legislation_url = provision.get('legislationUrl', '')

        # Extract SEPP details
        sepp_match = re.search(r'SEPP \(([^)]+)\) (\d{4})', epi_name)
        if sepp_match:
            sepp_type = sepp_match.group(1)
            sepp_year = sepp_match.group(2)
        else:
            sepp_type = 'Unknown'
            sepp_year = '2021'

        # Look up specific provisions
        numeric_value, unit, context = self._get_sepp_numeric_provisions(sepp_type, clause)

        return {
            'id': f"sepp_{sepp_type.lower().replace(' ', '_')}_{clause}",
            'provision_type': 'State Environmental Planning Policy',
            'tier_level': 1 if numeric_value else 2,
            'authority_level': config['authority_level'],
            'document_type': 'SEPP',
            'document_name': f'SEPP ({sepp_type}) {sepp_year}',
            'clause_reference': clause,
            'provision_text': self._get_sepp_provision_text(sepp_type, clause),
            'numeric_value': numeric_value,
            'unit': unit,
            'measurement_context': context,
            'requires_specialist': False,
            'confidence_level': 0.95,
            'extraction_confidence': 0.95,
            'legislation_url': legislation_url,
            'implications': self._get_sepp_implications(sepp_type, clause),
            'actions_required': self._get_sepp_actions(sepp_type, clause)
        }

    def _process_flood(self, provision: Dict, config: Dict, zone_code: str) -> Dict:
        """Process flood planning provisions"""
        category = provision.get('Category', '')
        level = provision.get('Level', '')

        # Get flood planning requirements
        requirements = self._get_flood_requirements(zone_code, category, level)

        return {
            'id': f"flood_{category.lower().replace(' ', '_')}",
            'provision_type': 'Flood Planning',
            'tier_level': 1,  # Flood is Tier 1 due to specific requirements
            'authority_level': config['authority_level'],
            'document_type': 'Flood Planning',
            'document_name': 'Flood Planning Controls',
            'clause_reference': f'Flood Planning - {level}',
            'provision_text': f'Property is in {category} - {level}',
            'numeric_value': requirements.get('min_floor_level'),
            'unit': 'm',
            'measurement_context': 'floor_level_above_flood',
            'requires_specialist': True,
            'confidence_level': 0.95,
            'extraction_confidence': 0.95,
            'implications': [
                'Flood Impact Assessment required',
                'Minimum floor levels apply',
                'Emergency evacuation plan required'
            ],
            'actions_required': [
                'Engage qualified flood engineer',
                'Prepare Flood Impact Assessment',
                f'Design floor levels {requirements.get("min_floor_level", 0.5)}m above flood level'
            ]
        }

    def _process_bushfire(self, provision: Dict, config: Dict) -> Dict:
        """Process bushfire prone land provisions"""
        category = provision.get('Category', '')
        buffer = provision.get('Buffer', '')

        bal_rating = self._get_bal_rating(category, buffer)

        return {
            'id': f"bushfire_{category.lower().replace(' ', '_')}",
            'provision_type': 'Bushfire Prone Land',
            'tier_level': 1,
            'authority_level': config['authority_level'],
            'document_type': 'Bushfire Planning',
            'document_name': 'Planning for Bush Fire Protection',
            'clause_reference': f'Bushfire - {category}',
            'provision_text': f'Property is bushfire prone - {category}',
            'measurement_context': 'bushfire_attack_level',
            'numeric_value': bal_rating,
            'unit': 'BAL',
            'requires_specialist': True,
            'confidence_level': 0.95,
            'extraction_confidence': 0.95,
            'implications': [
                'Bushfire Assessment Report required',
                f'Construction to BAL-{bal_rating} standard',
                'Asset Protection Zone required'
            ],
            'actions_required': [
                'Engage qualified bushfire consultant',
                'Prepare Bushfire Assessment Report',
                'Design to AS3959 standards'
            ]
        }

    def _process_acid_sulfate(self, provision: Dict, config: Dict) -> Dict:
        """Process acid sulfate soils provisions"""
        soil_class = provision.get('Class', '')
        action = provision.get('Action', '')

        return {
            'id': f"ass_{soil_class.lower().replace(' ', '_')}",
            'provision_type': 'Acid Sulfate Soils',
            'tier_level': config['tier_level'],
            'authority_level': config['authority_level'],
            'document_type': 'Environmental',
            'document_name': 'Acid Sulfate Soils Management',
            'clause_reference': f'ASS {soil_class}',
            'provision_text': f'Property has {soil_class} acid sulfate soils - {action}',
            'requires_specialist': True,
            'confidence_level': 0.85,
            'extraction_confidence': 0.85,
            'implications': [
                'Acid Sulfate Soils Management Plan may be required',
                f'Applies to {action}'
            ],
            'actions_required': [
                'Check excavation depth requirements',
                'Prepare ASS Management Plan if excavating below trigger depth'
            ]
        }

    def _process_heritage(self, provision: Dict, config: Dict) -> Dict:
        """Process heritage provisions"""
        heritage_type = provision.get('Heritage Type', '')
        item_name = provision.get('Item Name', '')

        return {
            'id': f"heritage_{item_name.lower().replace(' ', '_')}" if item_name else "heritage_item",
            'provision_type': 'Heritage',
            'tier_level': config['tier_level'],
            'authority_level': config['authority_level'],
            'document_type': 'Heritage',
            'document_name': 'Heritage Conservation',
            'clause_reference': 'Heritage Item',
            'provision_text': f'{heritage_type}: {item_name}' if item_name else f'{heritage_type} heritage item',
            'requires_specialist': True,
            'confidence_level': 0.90,
            'extraction_confidence': 0.90,
            'implications': [
                'Heritage Impact Statement required',
                'Heritage architect consultation recommended'
            ],
            'actions_required': [
                'Engage heritage consultant',
                'Prepare Heritage Impact Statement'
            ]
        }

    def _process_coastal(self, provision: Dict, config: Dict) -> Dict:
        """Process coastal management provisions"""
        category = provision.get('Category', '')
        level = provision.get('Level', '')

        return {
            'id': f"coastal_{category.lower().replace(' ', '_')}",
            'provision_type': 'Coastal Management',
            'tier_level': config['tier_level'],
            'authority_level': config['authority_level'],
            'document_type': 'Coastal Management',
            'document_name': 'Coastal Management Act 2016',
            'clause_reference': f'Coastal {category}',
            'provision_text': f'Property is in {category} - coastal management provisions apply',
            'requires_specialist': True,
            'confidence_level': 0.90,
            'extraction_confidence': 0.90,
            'implications': [
                'Coastal Impact Assessment may be required',
                'Sea level rise considerations apply'
            ],
            'actions_required': [
                'Check coastal development requirements',
                'Consider climate change impacts'
            ]
        }

    def _process_generic(self, provision: Dict, config: Dict, provision_type: str) -> Dict:
        """Process unknown/generic provision types"""
        category = provision.get('Category', '')
        value = provision.get('Value', provision.get('Class', ''))

        return {
            'id': f"generic_{provision_type.lower().replace(' ', '_')}",
            'provision_type': provision_type,
            'tier_level': config['tier_level'],
            'authority_level': config['authority_level'],
            'document_type': 'Special Provision',
            'document_name': f'{provision_type} Controls',
            'clause_reference': category or provision_type,
            'provision_text': f'{provision_type}: {value}' if value else f'{provision_type} applies to property',
            'requires_specialist': config['requires_specialist'],
            'confidence_level': 0.75,  # Lower confidence for unknown types
            'extraction_confidence': 0.80,
            'implications': [
                f'{provision_type} requirements may apply',
                'Check specific provisions for development type'
            ],
            'actions_required': [
                f'Review {provision_type} requirements',
                'Consult planning specialist if uncertain'
            ]
        }

    def _get_sepp_numeric_provisions(self, sepp_type: str, clause: str) -> Tuple[Optional[float], Optional[str], Optional[str]]:
        """Get numeric provisions for specific SEPP clauses"""

        # SEPP (Housing) 2021 provisions
        if sepp_type == 'Housing':
            if clause == '3.31':
                return 450, 'sqm', 'minimum_lot_size'
            elif clause == '3.32':
                return 600, 'sqm', 'minimum_lot_size'
            elif clause == '3.33':
                return 300, 'sqm', 'minimum_lot_size'

        # SEPP (Exempt and Complying Development Codes) 2008
        elif sepp_type == 'Exempt and Complying Development Codes':
            if 'height' in clause.lower():
                return 3, 'm', 'maximum_height'
            elif 'setback' in clause.lower():
                return 1.5, 'm', 'minimum_setback'

        return None, None, None

    def _get_sepp_provision_text(self, sepp_type: str, clause: str) -> str:
        """Get provision text for SEPP clause"""
        texts = {
            ('Housing', '3.31'): 'Low-rise housing diversity code - minimum lot size 450sqm',
            ('Housing', '3.32'): 'Manor houses - minimum lot size 600sqm',
            ('Housing', '3.33'): 'Townhouses - minimum lot size 300sqm'
        }
        return texts.get((sepp_type, clause), f'SEPP ({sepp_type}) Clause {clause} applies')

    def _get_sepp_implications(self, sepp_type: str, clause: str) -> List[str]:
        """Get implications for SEPP provisions"""
        if sepp_type == 'Housing':
            return [
                'Additional housing types may be permitted',
                'Complying development pathway may be available',
                'Design Guide provisions apply'
            ]
        elif sepp_type == 'Exempt and Complying Development Codes':
            return [
                'Exempt or complying development may be available',
                'Simplified approval process possible'
            ]
        return ['SEPP provisions override LEP where inconsistent']

    def _get_sepp_actions(self, sepp_type: str, clause: str) -> List[str]:
        """Get required actions for SEPP provisions"""
        if sepp_type == 'Housing':
            return [
                'Check Design Guide compliance',
                'Consider complying development pathway',
                'Verify lot size and dwelling type requirements'
            ]
        return ['Review SEPP requirements for development type']

    def _get_flood_requirements(self, zone_code: str, category: str, level: str) -> Dict:
        """Get flood planning requirements"""
        if '1:100' in level or 'PMF' in level:
            return {
                'min_floor_level': 0.5,
                'freeboard': 0.5,
                'flood_compatible_materials': True
            }
        return {'min_floor_level': 0.3, 'freeboard': 0.3}

    def _get_bal_rating(self, category: str, buffer: str) -> float:
        """Calculate BAL rating from bushfire category"""
        if 'Category 1' in category:
            return 29 if '100m' in buffer else 40
        elif 'Category 2' in category:
            return 19 if '100m' in buffer else 29
        elif 'Category 3' in category:
            return 12.5
        return 12.5

    def _extract_zone_number(self, zone: str) -> int:
        """Extract zone number from zone string"""
        match = re.search(r'(\d+)', zone)
        return int(match.group(1)) if match else 0

    def _create_hazard_assessment(self, provision: Dict) -> Dict:
        """Create hazard assessment summary"""
        return {
            'hazard_type': provision['provision_type'],
            'risk_level': 'high' if provision['tier_level'] == 1 else 'moderate',
            'specialist_required': provision.get('requires_specialist', False),
            'key_requirements': provision.get('implications', []),
            'actions': provision.get('actions_required', []),
            'measurement_context': provision.get('measurement_context'),
            'numeric_threshold': provision.get('numeric_value'),
            'unit': provision.get('unit')
        }

    def _create_environmental_constraint(self, provision: Dict) -> Dict:
        """Create environmental constraint summary"""
        return {
            'constraint_type': provision['provision_type'],
            'impact_level': 'significant' if provision.get('requires_specialist') else 'moderate',
            'assessment_required': provision.get('requires_specialist', False),
            'management_measures': provision.get('actions_required', []),
            'confidence_level': provision.get('confidence_level', 0.75)
        }

    def close_connection(self):
        """Close database connection"""
        if self.db:
            self.db.close()