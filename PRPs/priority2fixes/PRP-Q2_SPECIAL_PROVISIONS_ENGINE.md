# PRP-Q2: Special Provisions Processing Engine

## Executive Summary
Implement a comprehensive processing engine for special provisions from the NSW Planning API, including SEPPs, climate overlays, hazard zones, and other regulatory overlays that affect development compliance.

## Problem Statement
The NSW Planning API returns extensive special provisions data that is currently:
- Captured but not processed
- Not integrated with the tier hierarchy
- Not available for compliance checking
- Missing from user-facing displays

## Technical Architecture

### Data Structure Analysis

#### Current Special Provisions Categories
```json
{
  "Special Provisions": [
    {
      "Type": "Climate Zones",
      "Map Type": "CLM",
      "Class": "Zone 17"
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
    },
    {
      "Type": "Bushfire Prone Land",
      "Category": "Vegetation Category 1",
      "Buffer": "100m"
    },
    {
      "Type": "Acid Sulfate Soils",
      "Class": "Class 2",
      "Action": "Works below 2m AHD"
    }
  ]
}
```

### Implementation Components

## Component 1: Special Provisions Database Schema

```sql
-- Core provisions registry
CREATE TABLE special_provisions_registry (
    id SERIAL PRIMARY KEY,
    provision_type VARCHAR(100) NOT NULL,
    provision_category VARCHAR(100),
    provision_subtype VARCHAR(100),

    -- Hierarchy placement
    default_tier_level INTEGER NOT NULL CHECK (tier_level BETWEEN 1 AND 5),
    authority_level INTEGER NOT NULL CHECK (authority_level BETWEEN 0 AND 100),

    -- Processing rules
    requires_specialist BOOLEAN DEFAULT FALSE,
    has_numeric_thresholds BOOLEAN DEFAULT FALSE,
    affects_development_types TEXT[], -- Array of affected development types

    -- Metadata
    legislation_reference VARCHAR(255),
    last_updated DATE,
    active BOOLEAN DEFAULT TRUE,

    UNIQUE(provision_type, provision_category, provision_subtype)
);

-- Numeric thresholds for provisions
CREATE TABLE provision_thresholds (
    id SERIAL PRIMARY KEY,
    provision_id INTEGER REFERENCES special_provisions_registry(id),

    threshold_type VARCHAR(100), -- 'minimum', 'maximum', 'exact'
    measurement_context VARCHAR(100),
    numeric_value DECIMAL(10,2),
    unit VARCHAR(50),

    applies_to_zones TEXT[], -- Specific zones or NULL for all
    applies_to_dev_types TEXT[], -- Specific dev types or NULL for all

    UNIQUE(provision_id, threshold_type, measurement_context)
);

-- Provision implications and actions
CREATE TABLE provision_implications (
    id SERIAL PRIMARY KEY,
    provision_id INTEGER REFERENCES special_provisions_registry(id),

    implication_type VARCHAR(50), -- 'requirement', 'prohibition', 'assessment'
    implication_text TEXT,
    action_required TEXT,

    tier_level INTEGER,
    confidence_level DECIMAL(3,2)
);

-- Populate with known provisions
INSERT INTO special_provisions_registry
(provision_type, provision_category, default_tier_level, authority_level, requires_specialist)
VALUES
('Climate Zones', 'BASIX', 1, 100, FALSE),
('Flood Planning', 'Natural Hazards', 1, 95, TRUE),
('Bushfire Prone Land', 'Natural Hazards', 1, 95, TRUE),
('Acid Sulfate Soils', 'Environmental', 2, 85, TRUE),
('Heritage', 'Conservation', 2, 90, TRUE),
('Coastal Management', 'Environmental', 1, 95, TRUE),
('Riparian Land', 'Environmental', 2, 85, FALSE),
('Biodiversity', 'Environmental', 2, 85, TRUE);

-- Flood planning thresholds
INSERT INTO provision_thresholds
(provision_id, threshold_type, measurement_context, numeric_value, unit)
VALUES
((SELECT id FROM special_provisions_registry WHERE provision_type = 'Flood Planning'),
 'minimum', 'floor_level_above_flood', 0.5, 'm'),
((SELECT id FROM special_provisions_registry WHERE provision_type = 'Flood Planning'),
 'minimum', 'freeboard', 0.5, 'm');
```

## Component 2: Provisions Processing Engine

```python
# services/provisions_processing_engine.py
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import psycopg2
import json
import re

class ProvisionType(Enum):
    CLIMATE = "Climate Zones"
    SEPP = "State Environmental Planning Policy"
    FLOOD = "Flood Planning"
    BUSHFIRE = "Bushfire Prone Land"
    ACID_SULFATE = "Acid Sulfate Soils"
    HERITAGE = "Heritage"
    COASTAL = "Coastal Management"
    RIPARIAN = "Riparian Land"
    BIODIVERSITY = "Biodiversity"

@dataclass
class ProcessedProvision:
    provision_type: str
    tier_level: int
    authority_level: int
    document_type: str
    document_name: str
    clause_reference: str
    provision_text: str
    numeric_value: Optional[float] = None
    unit: Optional[str] = None
    measurement_context: Optional[str] = None
    requires_specialist: bool = False
    confidence_level: float = 0.95
    implications: List[str] = None
    actions_required: List[str] = None

class SpecialProvisionsEngine:
    """Comprehensive engine for processing special provisions"""

    def __init__(self, db_connection):
        self.db = db_connection
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

    def process_provisions(self,
                          raw_provisions: List[Dict],
                          zone_code: str,
                          development_type: Optional[str] = None) -> Dict:
        """
        Process raw special provisions into tiered compliance structure
        """

        results = {
            'tier_1_provisions': [],
            'tier_2_provisions': [],
            'tier_3_provisions': [],
            'tier_4_provisions': [],
            'tier_5_provisions': [],
            'hazard_assessments': [],
            'environmental_constraints': [],
            'metadata': {
                'total_processed': 0,
                'provision_types': set(),
                'requires_specialist': False
            }
        }

        for provision in raw_provisions:
            processed = self._process_single_provision(provision, zone_code, development_type)

            if processed:
                # Add to appropriate tier
                tier_key = f'tier_{processed.tier_level}_provisions'
                results[tier_key].append(processed.__dict__)

                # Track metadata
                results['metadata']['total_processed'] += 1
                results['metadata']['provision_types'].add(processed.provision_type)

                if processed.requires_specialist:
                    results['metadata']['requires_specialist'] = True

                # Special handling for hazards and environmental
                if processed.provision_type in ['Flood Planning', 'Bushfire Prone Land']:
                    results['hazard_assessments'].append(self._create_hazard_assessment(processed))

                if processed.provision_type in ['Acid Sulfate Soils', 'Biodiversity', 'Riparian Land']:
                    results['environmental_constraints'].append(self._create_environmental_constraint(processed))

        # Convert set to list for JSON serialization
        results['metadata']['provision_types'] = list(results['metadata']['provision_types'])

        return results

    def _process_single_provision(self,
                                 provision: Dict,
                                 zone_code: str,
                                 development_type: Optional[str]) -> Optional[ProcessedProvision]:
        """Process a single provision into structured format"""

        provision_type = provision.get('Type', '')
        category = provision.get('Category', '')

        # Look up in registry
        registry_key = (provision_type, category) if category else provision_type
        if registry_key not in self.registry and provision_type not in self.registry:
            return None

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

        return None

    def _process_climate_zone(self, provision: Dict, config: Dict) -> ProcessedProvision:
        """Process BASIX climate zone"""
        zone = provision.get('Class', '')

        return ProcessedProvision(
            provision_type='Climate Zones',
            tier_level=1,  # BASIX is always Tier 1
            authority_level=100,
            document_type='BASIX',
            document_name='Building Sustainability Index',
            clause_reference=f'Climate {zone}',
            provision_text=f'Property is in BASIX Climate {zone}',
            measurement_context='climate_zone',
            numeric_value=int(zone.replace('Zone ', '')) if 'Zone' in zone else None,
            unit='zone_number',
            implications=[
                'BASIX certificate required for new residential development',
                'Energy and water targets apply based on climate zone'
            ]
        )

    def _process_sepp(self, provision: Dict, config: Dict) -> ProcessedProvision:
        """Process State Environmental Planning Policy"""
        epi_name = provision.get('EPI Name', '')
        clause = provision.get('Legislative Clause', '')

        # Extract SEPP details
        sepp_match = re.search(r'SEPP \(([^)]+)\) (\d{4})', epi_name)
        if sepp_match:
            sepp_type = sepp_match.group(1)
            sepp_year = sepp_match.group(2)

            # Look up specific provisions
            numeric_value, unit, context = self._get_sepp_numeric_provisions(sepp_type, clause)

            return ProcessedProvision(
                provision_type='SEPP',
                tier_level=1 if numeric_value else 2,
                authority_level=95,
                document_type='SEPP',
                document_name=f'SEPP ({sepp_type}) {sepp_year}',
                clause_reference=clause,
                provision_text=self._get_sepp_provision_text(sepp_type, clause),
                numeric_value=numeric_value,
                unit=unit,
                measurement_context=context,
                implications=self._get_sepp_implications(sepp_type, clause)
            )

        return None

    def _process_flood(self, provision: Dict, config: Dict, zone_code: str) -> ProcessedProvision:
        """Process flood planning provisions"""
        category = provision.get('Category', '')
        level = provision.get('Level', '')

        # Get flood planning requirements
        requirements = self._get_flood_requirements(zone_code, category, level)

        return ProcessedProvision(
            provision_type='Flood Planning',
            tier_level=1,  # Flood is Tier 1 due to specific requirements
            authority_level=95,
            document_type='Flood Planning',
            document_name='Flood Planning Controls',
            clause_reference=f'Flood Planning - {level}',
            provision_text=f'Property is in {category} - {level}',
            numeric_value=requirements.get('min_floor_level'),
            unit='m',
            measurement_context='floor_level_above_flood',
            requires_specialist=True,
            implications=[
                'Flood Impact Assessment required',
                'Minimum floor levels apply',
                'Emergency evacuation plan required'
            ],
            actions_required=[
                'Engage flood consultant',
                'Prepare Flood Impact Assessment',
                f'Design floor levels {requirements.get("min_floor_level", 0.5)}m above flood level'
            ]
        )

    def _process_bushfire(self, provision: Dict, config: Dict) -> ProcessedProvision:
        """Process bushfire prone land provisions"""
        category = provision.get('Category', '')
        buffer = provision.get('Buffer', '')

        bal_rating = self._get_bal_rating(category, buffer)

        return ProcessedProvision(
            provision_type='Bushfire Prone Land',
            tier_level=1,
            authority_level=95,
            document_type='Bushfire Planning',
            document_name='Planning for Bush Fire Protection',
            clause_reference=f'Bushfire - {category}',
            provision_text=f'Property is bushfire prone - {category}',
            measurement_context='bushfire_attack_level',
            numeric_value=bal_rating,
            unit='BAL',
            requires_specialist=True,
            implications=[
                'Bushfire Assessment Report required',
                f'Construction to BAL-{bal_rating} standard',
                'Asset Protection Zone required'
            ],
            actions_required=[
                'Engage bushfire consultant',
                'Prepare Bushfire Assessment Report',
                'Design to AS3959 standards'
            ]
        )

    def _process_acid_sulfate(self, provision: Dict, config: Dict) -> ProcessedProvision:
        """Process acid sulfate soils provisions"""
        soil_class = provision.get('Class', '')
        action = provision.get('Action', '')

        return ProcessedProvision(
            provision_type='Acid Sulfate Soils',
            tier_level=2,
            authority_level=85,
            document_type='Environmental',
            document_name='Acid Sulfate Soils Management',
            clause_reference=f'ASS {soil_class}',
            provision_text=f'Property has {soil_class} acid sulfate soils - {action}',
            requires_specialist=True,
            implications=[
                'Acid Sulfate Soils Management Plan may be required',
                f'Applies to {action}'
            ],
            actions_required=[
                'Check excavation depth requirements',
                'Prepare ASS Management Plan if excavating'
            ]
        )

    def _process_heritage(self, provision: Dict, config: Dict) -> ProcessedProvision:
        """Process heritage provisions"""
        heritage_type = provision.get('Heritage Type', '')
        item_name = provision.get('Item Name', '')

        return ProcessedProvision(
            provision_type='Heritage',
            tier_level=2,
            authority_level=90,
            document_type='Heritage',
            document_name='Heritage Conservation',
            clause_reference='Heritage Item',
            provision_text=f'{heritage_type}: {item_name}',
            requires_specialist=True,
            implications=[
                'Heritage Impact Statement required',
                'Heritage architect consultation recommended'
            ]
        )

    def _get_sepp_numeric_provisions(self, sepp_type: str, clause: str) -> Tuple[Optional[float], Optional[str], Optional[str]]:
        """Get numeric provisions for specific SEPP clauses"""

        # SEPP (Housing) 2021 provisions
        if sepp_type == 'Housing' and clause == '3.31':
            return 450, 'sqm', 'minimum_lot_size'
        elif sepp_type == 'Housing' and clause == '3.32':
            return 600, 'sqm', 'minimum_lot_size'

        # Add more SEPP provisions as needed
        return None, None, None

    def _get_sepp_provision_text(self, sepp_type: str, clause: str) -> str:
        """Get provision text for SEPP clause"""
        texts = {
            ('Housing', '3.31'): 'Low-rise housing diversity code - minimum lot size 450sqm',
            ('Housing', '3.32'): 'Manor houses - minimum lot size 600sqm'
        }
        return texts.get((sepp_type, clause), f'SEPP ({sepp_type}) Clause {clause} applies')

    def _get_sepp_implications(self, sepp_type: str, clause: str) -> List[str]:
        """Get implications for SEPP provisions"""
        if sepp_type == 'Housing':
            return [
                'Additional housing types may be permitted',
                'Complying development pathway available'
            ]
        return ['SEPP provisions override LEP where inconsistent']

    def _get_flood_requirements(self, zone_code: str, category: str, level: str) -> Dict:
        """Get flood planning requirements"""
        # Default requirements - should be loaded from database
        if '1:100' in level or 'PMF' in level:
            return {
                'min_floor_level': 0.5,
                'freeboard': 0.5,
                'flood_compatible_materials': True
            }
        return {'min_floor_level': 0.3, 'freeboard': 0.3}

    def _get_bal_rating(self, category: str, buffer: str) -> int:
        """Calculate BAL rating from bushfire category"""
        if 'Category 1' in category:
            return 29 if '100m' in buffer else 40
        elif 'Category 2' in category:
            return 19 if '100m' in buffer else 29
        return 12.5

    def _create_hazard_assessment(self, provision: ProcessedProvision) -> Dict:
        """Create hazard assessment summary"""
        return {
            'hazard_type': provision.provision_type,
            'risk_level': 'high' if provision.tier_level == 1 else 'moderate',
            'specialist_required': provision.requires_specialist,
            'key_requirements': provision.implications,
            'actions': provision.actions_required
        }

    def _create_environmental_constraint(self, provision: ProcessedProvision) -> Dict:
        """Create environmental constraint summary"""
        return {
            'constraint_type': provision.provision_type,
            'impact_level': 'significant' if provision.requires_specialist else 'moderate',
            'assessment_required': provision.requires_specialist,
            'management_measures': provision.actions_required
        }
```

## Component 3: Integration Layer

```python
# services/provisions_integration.py
from typing import Dict, List, Optional
import json

class ProvisionsIntegrationService:
    """Integrate special provisions with compliance checking"""

    def __init__(self, provisions_engine, hierarchy_resolver):
        self.provisions_engine = provisions_engine
        self.hierarchy = hierarchy_resolver

    def integrate_provisions(self,
                            planning_api_data: Dict,
                            zone_code: str,
                            development_type: Optional[str] = None) -> Dict:
        """
        Integrate special provisions with hierarchical compliance data
        """

        # Extract special provisions from Planning API response
        special_provisions = self._extract_special_provisions(planning_api_data)

        # Process provisions through engine
        processed = self.provisions_engine.process_provisions(
            special_provisions,
            zone_code,
            development_type
        )

        # Merge with existing hierarchy data
        return self._merge_with_hierarchy(processed)

    def _extract_special_provisions(self, api_data: Dict) -> List[Dict]:
        """Extract special provisions from Planning API response"""
        provisions = []

        for layer in api_data.get('layers', []):
            if layer.get('layerName') == 'Special Provisions':
                provisions.extend(layer.get('results', []))

        return provisions

    def _merge_with_hierarchy(self, processed_provisions: Dict) -> Dict:
        """Merge processed provisions with hierarchy resolver output"""

        # Provisions are already tiered, just need to merge
        return {
            'special_provisions': processed_provisions,
            'integration_metadata': {
                'hazards_identified': len(processed_provisions.get('hazard_assessments', [])) > 0,
                'environmental_constraints': len(processed_provisions.get('environmental_constraints', [])) > 0,
                'specialist_required': processed_provisions['metadata'].get('requires_specialist', False)
            }
        }
```

## Verification Metrics

### Completeness Metrics
- 100% of special provisions types mapped
- 100% of SEPP clauses with numeric values captured
- 100% of hazard categories processed
- 95%+ of provisions assigned to correct tier

### Accuracy Metrics
- Tier assignments match authority level
- Numeric values preserved with units
- Legislative references maintained
- Specialist requirements correctly flagged

### Performance Metrics
- <100ms processing time for typical property
- <50ms database lookup time
- Zero data loss in processing
- Graceful handling of unknown provisions

## Risk Management

### Technical Risks
1. **Unknown provision types**: Log and assign to Tier 3 by default
2. **Missing numeric values**: Use qualitative assessment
3. **API changes**: Version-aware processing with fallbacks
4. **Performance degradation**: Implement caching layer

### Business Risks
1. **Incorrect tier assignment**: Regular audits and updates
2. **Missing specialist flags**: Conservative approach - flag when uncertain
3. **Outdated provisions**: Quarterly registry updates
4. **Legal implications**: Clear disclaimers on all outputs

## Implementation Checklist

- [ ] Create database schema
- [ ] Populate provision registry
- [ ] Implement processing engine
- [ ] Create integration service
- [ ] Add API endpoints
- [ ] Update frontend components
- [ ] Write verification tests
- [ ] Document provision types
- [ ] Create monitoring dashboard
- [ ] Deploy to staging