# PRP-Q1: BASIX and Special Provisions Integration

## Executive Summary
Integrate BASIX (Building Sustainability Index) provisions and other special planning provisions from the NSW Planning API into the compliance engine's authoritative hierarchy system.

## Current State Analysis

### What Works
- NSW Planning API successfully extracts BASIX climate zones and water use data
- Special provisions layer captured in API responses
- Basic SEPP identification logic exists

### Critical Gaps
1. BASIX data not passed to compliance checking API
2. No BASIX-specific compliance rules or targets
3. Special provisions not displayed in UI
4. No integration with tier hierarchy system

## Technical Implementation Plan

### Phase 1: Data Flow Enhancement (2 hours)

#### 1.1 Extend API Request Structure
```typescript
// frontend-nextjs/app/api/authoritative/compliance-check/route.ts
interface EnhancedComplianceRequest {
  zone_code: string;
  property_id?: number;
  development_type?: string;
  basix_provisions?: {
    climate_zone?: string;      // e.g., "Zone 17"
    water_zone?: string;        // Water use classification
    applicable_sepps?: string[]; // Identified SEPPs
  };
  special_provisions?: Array<{
    type: string;
    category: string;
    value: string;
    legislation_url?: string;
  }>;
}
```

#### 1.2 Update Property Search Component
```typescript
// frontend-nextjs/components/property/PropertySearch.tsx
// Add BASIX data to compliance check payload
const compliancePayload = {
  zone_code: zoneCode,
  property_id: propertyId,
  development_type: developmentType,
  basix_provisions: {
    climate_zone: constraints.basixClimate,
    water_zone: constraints.basixWater,
    applicable_sepps: constraints.applicableSepps
  },
  special_provisions: extractedProvisions
};
```

### Phase 2: Backend Processing Enhancement (3 hours)

#### 2.1 Create BASIX Provisions Table
```sql
-- PostgreSQL schema
CREATE TABLE basix_provisions (
    id SERIAL PRIMARY KEY,
    climate_zone VARCHAR(50) NOT NULL,
    development_type VARCHAR(100) NOT NULL,

    -- Energy targets
    energy_reduction_target DECIMAL(5,2),  -- Percentage
    thermal_comfort_rating DECIMAL(3,1),   -- Star rating

    -- Water targets
    water_reduction_target DECIMAL(5,2),   -- Percentage
    water_fixture_rating INTEGER,          -- WELS rating

    -- Compliance thresholds
    min_insulation_r_value DECIMAL(3,1),
    max_glazing_percentage DECIMAL(5,2),

    -- Metadata
    effective_date DATE,
    source_document VARCHAR(255),
    tier_level INTEGER DEFAULT 1,  -- BASIX is Tier 1 (fully authoritative)

    UNIQUE(climate_zone, development_type)
);

-- Populate with NSW BASIX requirements
INSERT INTO basix_provisions (climate_zone, development_type, energy_reduction_target, water_reduction_target) VALUES
('Zone 17', 'dwelling_house', 40.0, 40.0),
('Zone 17', 'residential_flat_building', 35.0, 40.0),
('Zone 17', 'dual_occupancy', 40.0, 40.0),
('Zone 18', 'dwelling_house', 45.0, 40.0),
('Zone 18', 'residential_flat_building', 40.0, 40.0);
```

#### 2.2 Extend Enhanced Compliance API
```python
# services/enhanced_compliance_api.py
class BASIXComplianceChecker:
    def __init__(self, db_connection):
        self.db = db_connection

    def get_basix_requirements(self, climate_zone: str, development_type: str) -> Dict:
        """Get BASIX requirements for zone and development type"""
        query = """
            SELECT
                energy_reduction_target,
                thermal_comfort_rating,
                water_reduction_target,
                water_fixture_rating,
                min_insulation_r_value,
                max_glazing_percentage
            FROM basix_provisions
            WHERE climate_zone = %s
            AND development_type = %s
        """

        result = self.db.execute(query, (climate_zone, development_type))
        if result:
            return {
                'tier_level': 1,  # BASIX is always Tier 1
                'document_type': 'BASIX',
                'provisions': self._format_basix_provisions(result)
            }
        return None

    def _format_basix_provisions(self, data: Dict) -> List[Dict]:
        """Format BASIX requirements as tier 1 provisions"""
        provisions = []

        if data.get('energy_reduction_target'):
            provisions.append({
                'provision_type': 'energy_efficiency',
                'measurement_context': 'energy_reduction',
                'numeric_value': data['energy_reduction_target'],
                'unit': 'percent',
                'provision_text': f"Achieve {data['energy_reduction_target']}% reduction in energy consumption",
                'clause_reference': 'BASIX Energy Target',
                'authority_level': 100,
                'confidence_level': 1.0
            })

        if data.get('water_reduction_target'):
            provisions.append({
                'provision_type': 'water_efficiency',
                'measurement_context': 'water_reduction',
                'numeric_value': data['water_reduction_target'],
                'unit': 'percent',
                'provision_text': f"Achieve {data['water_reduction_target']}% reduction in water consumption",
                'clause_reference': 'BASIX Water Target',
                'authority_level': 100,
                'confidence_level': 1.0
            })

        return provisions
```

### Phase 3: Special Provisions Processing (2 hours)

#### 3.1 Create Special Provisions Processor
```python
# services/special_provisions_processor.py
from typing import List, Dict, Optional
import re

class SpecialProvisionsProcessor:
    """Process special provisions from NSW Planning API"""

    # Known SEPP mappings
    SEPP_MAPPINGS = {
        'SEPP_HOUSING_2021': {
            'tier_level': 1,
            'provisions': [
                {
                    'clause': '3.31',
                    'title': 'Low-rise housing diversity',
                    'measurement_context': 'minimum_lot_size',
                    'numeric_value': 450,
                    'unit': 'sqm'
                },
                {
                    'clause': '3.32',
                    'title': 'Manor houses',
                    'measurement_context': 'minimum_lot_size',
                    'numeric_value': 600,
                    'unit': 'sqm'
                }
            ]
        },
        'SEPP_EXEMPT_2008': {
            'tier_level': 1,
            'provisions': [
                {
                    'clause': '2.1',
                    'title': 'General development requirements',
                    'measurement_context': 'maximum_height',
                    'numeric_value': 3,
                    'unit': 'm'
                }
            ]
        }
    }

    def process_special_provisions(self, provisions: List[Dict]) -> Dict:
        """Process special provisions into tiered structure"""

        processed = {
            'tier_1_provisions': [],
            'tier_2_provisions': [],
            'tier_3_provisions': [],
            'metadata': {
                'total_processed': 0,
                'sepps_identified': []
            }
        }

        for provision in provisions:
            # Identify SEPP type
            sepp_type = self._identify_sepp(provision)

            if sepp_type and sepp_type in self.SEPP_MAPPINGS:
                # Add known SEPP provisions
                sepp_data = self.SEPP_MAPPINGS[sepp_type]
                for sepp_provision in sepp_data['provisions']:
                    processed[f'tier_{sepp_data["tier_level"]}_provisions'].append({
                        'document_type': 'SEPP',
                        'document_name': sepp_type,
                        'clause_reference': sepp_provision['clause'],
                        'provision_text': sepp_provision['title'],
                        'measurement_context': sepp_provision.get('measurement_context'),
                        'numeric_value': sepp_provision.get('numeric_value'),
                        'unit': sepp_provision.get('unit'),
                        'tier_level': sepp_data['tier_level'],
                        'authority_level': 95,
                        'confidence_level': 0.95
                    })
                processed['metadata']['sepps_identified'].append(sepp_type)

            processed['metadata']['total_processed'] += 1

        return processed

    def _identify_sepp(self, provision: Dict) -> Optional[str]:
        """Identify SEPP type from provision data"""
        text = ' '.join(str(v) for v in provision.values()).lower()

        if 'housing' in text and ('2021' in text or 'sepp' in text):
            return 'SEPP_HOUSING_2021'
        elif 'exempt' in text and 'complying' in text:
            return 'SEPP_EXEMPT_2008'
        elif 'planning systems' in text:
            return 'SEPP_PLANNING_SYSTEMS_2021'
        elif 'resilience' in text or 'hazards' in text:
            return 'SEPP_RESILIENCE_HAZARDS_2021'

        return None
```

### Phase 4: UI Integration (2 hours)

#### 4.1 Create BASIX Display Component
```tsx
// frontend-nextjs/components/compliance/BASIXProvisions.tsx
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Droplets, Zap, Thermometer, Info } from 'lucide-react';

interface BASIXProvision {
  provision_type: string;
  numeric_value: number;
  unit: string;
  provision_text: string;
  clause_reference: string;
}

interface BASIXProvisionsProps {
  climateZone?: string;
  waterZone?: string;
  provisions: BASIXProvision[];
}

export default function BASIXProvisions({
  climateZone,
  waterZone,
  provisions
}: BASIXProvisionsProps) {

  const getProvisionIcon = (type: string) => {
    switch(type) {
      case 'energy_efficiency':
        return <Zap className="w-4 h-4 text-yellow-500" />;
      case 'water_efficiency':
        return <Droplets className="w-4 h-4 text-blue-500" />;
      case 'thermal_comfort':
        return <Thermometer className="w-4 h-4 text-orange-500" />;
      default:
        return <Info className="w-4 h-4 text-gray-500" />;
    }
  };

  if (!provisions || provisions.length === 0) {
    return null;
  }

  return (
    <Card className="border-green-200 bg-green-50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Badge className="bg-green-500 text-white">BASIX</Badge>
          Building Sustainability Requirements
        </CardTitle>
        {climateZone && (
          <div className="text-sm text-gray-600">
            Climate Zone: <strong>{climateZone}</strong>
            {waterZone && <> | Water Zone: <strong>{waterZone}</strong></>}
          </div>
        )}
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {provisions.map((provision, idx) => (
            <div key={idx} className="flex items-start gap-3 p-3 bg-white rounded-lg border border-green-100">
              {getProvisionIcon(provision.provision_type)}
              <div className="flex-1">
                <div className="font-medium text-sm">
                  {provision.clause_reference}
                </div>
                <div className="text-gray-700">
                  {provision.provision_text}
                </div>
                {provision.numeric_value && (
                  <div className="mt-1 text-2xl font-bold text-green-600">
                    {provision.numeric_value}{provision.unit === 'percent' ? '%' : provision.unit}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
          <div className="text-sm text-blue-900">
            <strong>Note:</strong> BASIX certificates are mandatory for all new residential developments.
            These targets must be achieved and verified through the BASIX assessment process.
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

#### 4.2 Update Authoritative Compliance Display
```tsx
// Add to AuthoritativeComplianceDisplay.tsx
import BASIXProvisions from './BASIXProvisions';

// In the render method, add after tier displays:
{data.basix_provisions && (
  <BASIXProvisions
    climateZone={data.basix_climate_zone}
    waterZone={data.basix_water_zone}
    provisions={data.basix_provisions}
  />
)}

{data.special_provisions && data.special_provisions.length > 0 && (
  <Card className="mt-4">
    <CardHeader>
      <CardTitle>Special Planning Provisions</CardTitle>
    </CardHeader>
    <CardContent>
      <div className="space-y-2">
        {data.special_provisions.map((provision, idx) => (
          <div key={idx} className="p-2 bg-gray-50 rounded">
            <Badge variant="outline">{provision.document_type}</Badge>
            <span className="ml-2">{provision.provision_text}</span>
          </div>
        ))}
      </div>
    </CardContent>
  </Card>
)}
```

## Verification Requirements

### V1: Data Flow Verification
- BASIX data extracted from Planning API ✓
- BASIX data passed to compliance API ✓
- BASIX provisions returned in response ✓
- BASIX provisions displayed in UI ✓

### V2: Compliance Rules Verification
- BASIX targets correctly mapped to climate zones ✓
- Development type specific requirements applied ✓
- Tier 1 authority level assigned ✓
- Numeric values and units preserved ✓

### V3: Special Provisions Verification
- SEPPs correctly identified ✓
- SEPP provisions extracted with numeric values ✓
- Provisions correctly tiered ✓
- Legislative references preserved ✓

## Success Metrics
- 100% of BASIX climate zones mapped to requirements
- 100% of BASIX provisions displayed as Tier 1
- 90%+ of applicable SEPPs identified and processed
- <500ms additional processing time

## Risk Mitigation
- Fallback to generic BASIX requirements if zone not found
- Cache BASIX requirements for performance
- Log all unmapped special provisions for analysis
- Maintain backward compatibility with existing API

## Implementation Timeline
- Phase 1: 2 hours - Data flow enhancement
- Phase 2: 3 hours - Backend processing
- Phase 3: 2 hours - Special provisions
- Phase 4: 2 hours - UI integration
- Testing: 1 hour
- **Total: 10 hours**