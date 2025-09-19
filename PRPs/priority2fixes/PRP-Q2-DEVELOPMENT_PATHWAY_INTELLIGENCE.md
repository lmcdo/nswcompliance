# PRP-Q2: Development Pathway Intelligence

## OBJECTIVE
Implement intelligent DA/CDC/Exempt pathway determination by combining live NSW API zone data with existing SEPP provisions to answer "Do I need a DA?" - the most common planning question.

## SUCCESS CRITERIA
- [ ] Integrate live NSW API zone data with SEPP provisions database
- [ ] Create PathwayIntelligence engine for DA/CDC/Exempt determination
- [ ] Implement SEPP overlay detection using live API data
- [ ] Handle exempt/complying development criteria from 2,186 SEPP provisions
- [ ] Achieve 90%+ pathway accuracy on test scenarios
- [ ] Response time <500ms including API calls

## TECHNICAL SPECIFICATION

### Phase Q2A: Pathway Decision Framework
```python
from services.nsw_planning_api import PropertyIntelligence, get_property_intelligence
from dataclasses import dataclass
from typing import Optional, Dict, List, Any
import sqlite3
from enum import Enum

class DevelopmentPathway(Enum):
    EXEMPT = "exempt"
    COMPLYING = "complying"
    DA_REQUIRED = "development_application"
    PROHIBITED = "prohibited"

@dataclass
class PathwayRule:
    sepp_name: str
    development_type: str
    zone_applicable: List[str]
    pathway: DevelopmentPathway
    criteria: Dict[str, Any]
    confidence: float
    source_provision_id: int

@dataclass
class PathwayAssessment:
    recommended_pathway: DevelopmentPathway
    applicable_sepps: List[str]
    zone_confirmed: str
    development_type: str
    criteria_met: Dict[str, bool]
    warnings: List[str]
    confidence_score: float
    processing_time_ms: int
```

### Phase Q2B: SEPP Pathway Engine
```python
class PathwayIntelligenceEngine:
    """Intelligent development pathway determination using live API + SEPP data"""

    def __init__(self):
        self.load_sepp_pathway_rules()

    def load_sepp_pathway_rules(self):
        """Load pathway rules from existing SEPP provisions"""
        conn = sqlite3.connect('nsw_planning.db')
        cursor = conn.cursor()

        # Extract exempt development rules from SEPP provisions
        cursor.execute("""
        SELECT id, document_id, provision_text, zone
        FROM regulatory_provisions
        WHERE LOWER(document_id) LIKE '%exempt%'
        AND LOWER(provision_text) LIKE '%exempt%'
        """)

        exempt_provisions = cursor.fetchall()
        self.exempt_rules = self._parse_pathway_rules(exempt_provisions, DevelopmentPathway.EXEMPT)

        # Extract complying development rules
        cursor.execute("""
        SELECT id, document_id, provision_text, zone
        FROM regulatory_provisions
        WHERE LOWER(document_id) LIKE '%complying%'
        AND LOWER(provision_text) LIKE '%complying%'
        """)

        complying_provisions = cursor.fetchall()
        self.complying_rules = self._parse_pathway_rules(complying_provisions, DevelopmentPathway.COMPLYING)

        conn.close()

    async def determine_pathway(self,
                              address: str,
                              development_type: str,
                              development_details: Dict[str, Any],
                              google_coords: Optional[Dict[str, float]] = None) -> PathwayAssessment:
        """Determine development pathway using live API zone + SEPP rules"""

        start_time = time.time()

        # Get live property intelligence including current zoning
        try:
            intelligence = await get_property_intelligence(address, google_coords)
        except Exception as e:
            return PathwayAssessment(
                recommended_pathway=DevelopmentPathway.DA_REQUIRED,
                applicable_sepps=[],
                zone_confirmed="UNKNOWN",
                development_type=development_type,
                criteria_met={},
                warnings=[f"Cannot determine zone from NSW API: {str(e)}"],
                confidence_score=0.1,
                processing_time_ms=int((time.time() - start_time) * 1000)
            )

        # Extract confirmed zone from live API
        live_zone = intelligence.zone.value if intelligence.zone else None
        if not live_zone:
            return PathwayAssessment(
                recommended_pathway=DevelopmentPathway.DA_REQUIRED,
                applicable_sepps=[],
                zone_confirmed="UNKNOWN",
                development_type=development_type,
                criteria_met={},
                warnings=["No zone information available from NSW API"],
                confidence_score=0.1,
                processing_time_ms=int((time.time() - start_time) * 1000)
            )

        # Check exempt development pathway
        exempt_pathway = self._check_exempt_pathway(
            live_zone, development_type, development_details, intelligence
        )

        if exempt_pathway.recommended_pathway == DevelopmentPathway.EXEMPT:
            exempt_pathway.processing_time_ms = int((time.time() - start_time) * 1000)
            return exempt_pathway

        # Check complying development pathway
        complying_pathway = self._check_complying_pathway(
            live_zone, development_type, development_details, intelligence
        )

        if complying_pathway.recommended_pathway == DevelopmentPathway.COMPLYING:
            complying_pathway.processing_time_ms = int((time.time() - start_time) * 1000)
            return complying_pathway

        # Default to DA required
        return PathwayAssessment(
            recommended_pathway=DevelopmentPathway.DA_REQUIRED,
            applicable_sepps=["SEPP (Planning Systems) 2021"],
            zone_confirmed=live_zone,
            development_type=development_type,
            criteria_met={"requires_da": True},
            warnings=["Development does not meet exempt or complying criteria"],
            confidence_score=0.8,
            processing_time_ms=int((time.time() - start_time) * 1000)
        )

    def _check_exempt_pathway(self,
                            zone: str,
                            development_type: str,
                            details: Dict[str, Any],
                            intelligence: PropertyIntelligence) -> PathwayAssessment:
        """Check if development qualifies for exempt pathway"""

        applicable_rules = [
            rule for rule in self.exempt_rules
            if zone in rule.zone_applicable or 'ALL' in rule.zone_applicable
        ]

        # Common exempt development types with criteria
        if development_type == 'dwelling_house':
            # Single dwelling house exempt criteria
            height = details.get('height', 0)
            if height <= 8.5:  # Standard height limit for exempt
                return PathwayAssessment(
                    recommended_pathway=DevelopmentPathway.EXEMPT,
                    applicable_sepps=["SEPP (Exempt and Complying Development Codes) 2008"],
                    zone_confirmed=zone,
                    development_type=development_type,
                    criteria_met={"height_compliant": True},
                    warnings=[],
                    confidence_score=0.9,
                    processing_time_ms=0
                )

        elif development_type == 'alterations_additions':
            # Alterations and additions criteria
            floor_area = details.get('additional_floor_area', 0)
            if floor_area <= 50:  # 50sqm limit for exempt alterations
                return PathwayAssessment(
                    recommended_pathway=DevelopmentPathway.EXEMPT,
                    applicable_sepps=["SEPP (Exempt and Complying Development Codes) 2008"],
                    zone_confirmed=zone,
                    development_type=development_type,
                    criteria_met={"area_compliant": True},
                    warnings=[],
                    confidence_score=0.85,
                    processing_time_ms=0
                )

        # Default - not exempt
        return PathwayAssessment(
            recommended_pathway=DevelopmentPathway.DA_REQUIRED,
            applicable_sepps=[],
            zone_confirmed=zone,
            development_type=development_type,
            criteria_met={"exempt_criteria_met": False},
            warnings=["Does not meet exempt development criteria"],
            confidence_score=0.7,
            processing_time_ms=0
        )

    def _check_complying_pathway(self,
                               zone: str,
                               development_type: str,
                               details: Dict[str, Any],
                               intelligence: PropertyIntelligence) -> PathwayAssessment:
        """Check if development qualifies for complying pathway"""

        if development_type == 'dwelling_house' and zone in ['R2', 'R3', 'R4']:
            # Dwelling house CDC criteria
            height = details.get('height', 0)
            fsr_proposed = details.get('fsr', 0)

            # Get live FSR limit from API
            api_fsr_limit = 0.6  # Default fallback
            if intelligence.fsr_limit:
                try:
                    api_fsr_limit = float(intelligence.fsr_limit.value.replace(':1', ''))
                except:
                    api_fsr_limit = 0.6

            criteria_met = {
                "height_compliant": height <= 9.0,  # CDC height limit
                "fsr_compliant": fsr_proposed <= api_fsr_limit,
                "zone_permissible": zone in ['R2', 'R3', 'R4']
            }

            if all(criteria_met.values()):
                return PathwayAssessment(
                    recommended_pathway=DevelopmentPathway.COMPLYING,
                    applicable_sepps=["SEPP (Exempt and Complying Development Codes) 2008"],
                    zone_confirmed=zone,
                    development_type=development_type,
                    criteria_met=criteria_met,
                    warnings=[],
                    confidence_score=0.9,
                    processing_time_ms=0
                )

        elif development_type == 'secondary_dwelling':
            # Secondary dwelling CDC via SEPP (Housing) 2021
            max_area = details.get('floor_area', 0)

            if max_area <= 60 and zone in ['R2', 'R3', 'R4', 'R5']:
                return PathwayAssessment(
                    recommended_pathway=DevelopmentPathway.COMPLYING,
                    applicable_sepps=["SEPP (Housing) 2021"],
                    zone_confirmed=zone,
                    development_type=development_type,
                    criteria_met={
                        "area_compliant": True,
                        "zone_permissible": True,
                        "housing_sepp_applicable": True
                    },
                    warnings=[],
                    confidence_score=0.85,
                    processing_time_ms=0
                )

        # Default - requires DA
        return PathwayAssessment(
            recommended_pathway=DevelopmentPathway.DA_REQUIRED,
            applicable_sepps=[],
            zone_confirmed=zone,
            development_type=development_type,
            criteria_met={"complying_criteria_met": False},
            warnings=["Does not meet complying development criteria"],
            confidence_score=0.7,
            processing_time_ms=0
        )
```

## IMPLEMENTATION STEPS

### Step 1: Create Pathway Intelligence Engine (40 minutes)
```python
def create_pathway_intelligence_engine():
    """Create the pathway determination engine"""

    engine_content = '''
from services.nsw_planning_api import PropertyIntelligence, get_property_intelligence
from dataclasses import dataclass
from typing import Optional, Dict, List, Any
import sqlite3
import time
from enum import Enum

class DevelopmentPathway(Enum):
    EXEMPT = "exempt"
    COMPLYING = "complying"
    DA_REQUIRED = "development_application"
    PROHIBITED = "prohibited"

@dataclass
class PathwayAssessment:
    recommended_pathway: DevelopmentPathway
    applicable_sepps: List[str]
    zone_confirmed: str
    development_type: str
    criteria_met: Dict[str, bool]
    warnings: List[str]
    confidence_score: float
    processing_time_ms: int

class PathwayIntelligenceEngine:
    """Development pathway determination using live API + SEPP data"""

    async def determine_pathway(self,
                              address: str,
                              development_type: str,
                              development_details: Dict[str, Any],
                              google_coords: Optional[Dict[str, float]] = None) -> PathwayAssessment:
        """Main pathway determination method"""

        start_time = time.time()

        # Get live zone data from NSW API
        try:
            intelligence = await get_property_intelligence(address, google_coords)
            live_zone = intelligence.zone.value if intelligence.zone else None
        except Exception as e:
            return self._create_fallback_assessment(development_type, str(e), start_time)

        if not live_zone:
            return self._create_fallback_assessment(development_type, "No zone data available", start_time)

        # Check pathways in order of preference
        for pathway_check in [self._check_exempt, self._check_complying]:
            assessment = pathway_check(live_zone, development_type, development_details, intelligence)
            if assessment.recommended_pathway != DevelopmentPathway.DA_REQUIRED:
                assessment.processing_time_ms = int((time.time() - start_time) * 1000)
                return assessment

        # Default to DA required
        return PathwayAssessment(
            recommended_pathway=DevelopmentPathway.DA_REQUIRED,
            applicable_sepps=["Standard DA process"],
            zone_confirmed=live_zone,
            development_type=development_type,
            criteria_met={"requires_da": True},
            warnings=["Development requires Development Application"],
            confidence_score=0.8,
            processing_time_ms=int((time.time() - start_time) * 1000)
        )

    def _check_exempt(self, zone, dev_type, details, intelligence):
        """Check exempt development pathway"""

        if dev_type == 'dwelling_house':
            height = details.get('height', 0)
            if height <= 8.5:
                return PathwayAssessment(
                    recommended_pathway=DevelopmentPathway.EXEMPT,
                    applicable_sepps=["SEPP (Exempt and Complying Development Codes) 2008"],
                    zone_confirmed=zone,
                    development_type=dev_type,
                    criteria_met={"height_exempt": True},
                    warnings=[],
                    confidence_score=0.9,
                    processing_time_ms=0
                )

        return self._create_not_applicable(zone, dev_type)

    def _check_complying(self, zone, dev_type, details, intelligence):
        """Check complying development pathway"""

        if dev_type == 'dwelling_house' and zone in ['R2', 'R3', 'R4']:
            height = details.get('height', 0)

            # Use live FSR limit from API
            api_fsr_limit = 0.6
            if intelligence.fsr_limit:
                try:
                    fsr_str = intelligence.fsr_limit.value
                    api_fsr_limit = float(fsr_str.replace(':1', '')) if ':1' in fsr_str else float(fsr_str)
                except:
                    pass

            proposed_fsr = details.get('fsr', 0)

            if height <= 9.0 and proposed_fsr <= api_fsr_limit:
                return PathwayAssessment(
                    recommended_pathway=DevelopmentPathway.COMPLYING,
                    applicable_sepps=["SEPP (Exempt and Complying Development Codes) 2008"],
                    zone_confirmed=zone,
                    development_type=dev_type,
                    criteria_met={
                        "height_complying": True,
                        "fsr_complying": True,
                        "zone_appropriate": True
                    },
                    warnings=[],
                    confidence_score=0.9,
                    processing_time_ms=0
                )

        return self._create_not_applicable(zone, dev_type)

    def _create_fallback_assessment(self, dev_type, error_msg, start_time):
        return PathwayAssessment(
            recommended_pathway=DevelopmentPathway.DA_REQUIRED,
            applicable_sepps=[],
            zone_confirmed="UNKNOWN",
            development_type=dev_type,
            criteria_met={},
            warnings=[f"API error: {error_msg}"],
            confidence_score=0.1,
            processing_time_ms=int((time.time() - start_time) * 1000)
        )

    def _create_not_applicable(self, zone, dev_type):
        return PathwayAssessment(
            recommended_pathway=DevelopmentPathway.DA_REQUIRED,
            applicable_sepps=[],
            zone_confirmed=zone,
            development_type=dev_type,
            criteria_met={"pathway_not_applicable": True},
            warnings=[],
            confidence_score=0.7,
            processing_time_ms=0
        )
'''

    with open('services/pathway_intelligence_engine.py', 'w', encoding='utf-8') as f:
        f.write(engine_content)

    return 'services/pathway_intelligence_engine.py'
```

### Step 2: Create API Endpoint (30 minutes)
```python
def create_pathway_api_endpoint():
    """Create REST API for pathway determination"""

    api_content = '''
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  const startTime = Date.now();

  try {
    const body = await request.json();
    const { address, development_type, development_details, coordinates } = body;

    if (!address || !development_type) {
      return NextResponse.json({
        success: false,
        error: 'Address and development type required'
      }, { status: 400 });
    }

    // Call Python pathway intelligence engine
    const pythonScript = `
import asyncio
import sys
import json
sys.path.append('${process.cwd()}')
from services.pathway_intelligence_engine import PathwayIntelligenceEngine

async def main():
    engine = PathwayIntelligenceEngine()

    result = await engine.determine_pathway(
        "${address}",
        "${development_type}",
        ${JSON.stringify(development_details || {})},
        ${coordinates ? JSON.stringify(coordinates) : 'None'}
    )

    return {
        'recommended_pathway': result.recommended_pathway.value,
        'applicable_sepps': result.applicable_sepps,
        'zone_confirmed': result.zone_confirmed,
        'development_type': result.development_type,
        'criteria_met': result.criteria_met,
        'warnings': result.warnings,
        'confidence_score': result.confidence_score,
        'processing_time_ms': result.processing_time_ms
    }

result = asyncio.run(main())
print(json.dumps(result))
`;

    const { spawn } = require('child_process');
    const python = spawn('python', ['-c', pythonScript]);

    let result = '';
    let error = '';

    python.stdout.on('data', (data) => {
      result += data.toString();
    });

    python.stderr.on('data', (data) => {
      error += data.toString();
    });

    const pathwayResult = await new Promise((resolve, reject) => {
      python.on('close', (code) => {
        if (code !== 0) {
          reject(new Error(`Python error: ${error}`));
        } else {
          try {
            resolve(JSON.parse(result.trim()));
          } catch (e) {
            reject(new Error(`Invalid JSON: ${result}`));
          }
        }
      });
    });

    return NextResponse.json({
      success: true,
      pathway_assessment: pathwayResult,
      processing_time_ms: Date.now() - startTime
    });

  } catch (error) {
    return NextResponse.json({
      success: false,
      error: error.message,
      processing_time_ms: Date.now() - startTime
    }, { status: 500 });
  }
}
'''

    api_path = 'frontend-nextjs/app/api/pathway/determine/route.ts'
    os.makedirs(os.path.dirname(api_path), exist_ok=True)

    with open(api_path, 'w', encoding='utf-8') as f:
        f.write(api_content)

    return api_path
```

### Step 3: Create Verification Tests (30 minutes)
```python
def create_pathway_verification_tests():
    """Create verification tests for pathway determination"""

    test_cases = [
        {
            'description': 'Exempt dwelling house - low height',
            'address': '45 Liverpool Street, Ashfield NSW 2131',
            'development_type': 'dwelling_house',
            'development_details': {'height': 7.5},
            'expected_pathway': 'exempt',
            'expected_confidence': '>0.8'
        },
        {
            'description': 'Complying dwelling house - R2 zone',
            'address': '15 Norton Street, Leichhardt NSW 2040',
            'development_type': 'dwelling_house',
            'development_details': {'height': 8.5, 'fsr': 0.5},
            'expected_pathway': 'complying',
            'expected_confidence': '>0.8'
        },
        {
            'description': 'DA required - exceeds limits',
            'address': '25 King Street, Newtown NSW 2042',
            'development_type': 'dwelling_house',
            'development_details': {'height': 12.0, 'fsr': 1.2},
            'expected_pathway': 'development_application',
            'expected_confidence': '>0.7'
        }
    ]

    return test_cases
```

### Step 4: Update Automated Verification (20 minutes)
```python
def update_automated_verification_q2():
    """Update automated verification for PRP-Q2"""

    verification_code = '''
# PRP-Q2 Verification: Development Pathway Intelligence
import asyncio
from services.pathway_intelligence_engine import PathwayIntelligenceEngine

async def verify_prp_q2():
    """Verify PRP-Q2 pathway determination"""

    engine = PathwayIntelligenceEngine()
    results = []

    test_cases = [
        {
            'address': '45 Liverpool Street, Ashfield NSW 2131',
            'development_type': 'dwelling_house',
            'details': {'height': 7.5},
            'expected': 'exempt'
        },
        {
            'address': '15 Norton Street, Leichhardt NSW 2040',
            'development_type': 'dwelling_house',
            'details': {'height': 8.5, 'fsr': 0.5},
            'expected': 'complying'
        }
    ]

    for test in test_cases:
        try:
            result = await engine.determine_pathway(
                test['address'],
                test['development_type'],
                test['details']
            )

            passed = (
                result.recommended_pathway.value == test['expected'] and
                result.processing_time_ms < 500 and
                result.confidence_score >= 0.7
            )

            results.append({
                'test': f"{test['development_type']} at {test['address']}",
                'expected_pathway': test['expected'],
                'actual_pathway': result.recommended_pathway.value,
                'processing_time_ms': result.processing_time_ms,
                'confidence': result.confidence_score,
                'zone_confirmed': result.zone_confirmed,
                'passed': passed
            })

        except Exception as e:
            results.append({
                'test': f"{test['development_type']} at {test['address']}",
                'error': str(e),
                'passed': False
            })

    return results

if __name__ == '__main__':
    results = asyncio.run(verify_prp_q2())
    for result in results:
        status = "[PASS]" if result.get('passed') else "[FAIL]"
        print(f"{status} {result['test']}")
        if 'actual_pathway' in result:
            print(f"  Pathway: {result['actual_pathway']} (expected {result.get('expected_pathway', 'N/A')})")
            print(f"  Time: {result['processing_time_ms']}ms, Confidence: {result['confidence']}")
'''

    return verification_code
```

## VERIFICATION CHECKLIST

### Live API Integration
- [ ] Uses live NSW API zone data for pathway determination
- [ ] Integrates with existing SEPP provisions database
- [ ] Handles API failures gracefully with fallback logic
- [ ] Response times <500ms including API calls

### Pathway Accuracy
- [ ] Exempt development determination >90% accuracy
- [ ] Complying development determination >90% accuracy
- [ ] DA required determination >90% accuracy
- [ ] Confidence scores reflect data quality appropriately

### SEPP Integration
- [ ] Leverages 2,186 SEPP (Exempt and Complying) provisions
- [ ] Applies SEPP (Housing) 2021 secondary dwelling rules
- [ ] Handles zone-specific development permissions correctly
- [ ] Cross-references live zone data with SEPP applicability

## DELIVERABLES

1. **pathway_intelligence_engine.py** - Core pathway determination engine
2. **determine API endpoint** - REST API for pathway queries
3. **pathway_verification_tests.py** - Comprehensive test suite
4. **sepp_integration_report.json** - SEPP rules mapping documentation
5. **pathway_accuracy_metrics.json** - Accuracy measurement results

## ESTIMATED TIME
**2 hours total**
- Engine creation: 40 minutes
- API endpoint: 30 minutes
- Verification tests: 30 minutes
- SEPP integration: 20 minutes

## COMPLETION CRITERIA
✅ DA/CDC/Exempt pathway determination using live API zone data
✅ 90%+ pathway accuracy on test scenarios
✅ <500ms response time including NSW API calls
✅ Integration with existing 2,186 SEPP provisions
✅ Graceful API failure handling with confidence scoring