# PRP-Q1: Live Compliance Calculator Engine

## OBJECTIVE
Build real-time compliance calculation engine that uses live NSW Planning API data (FSR, height, area) for instant compliance assessments with superior accuracy compared to text extraction approaches.

## SUCCESS CRITERIA
- [ ] Integrate with existing NSW Planning API (services/nsw_planning_api.py)
- [ ] Create LiveComplianceEngine class using PropertyIntelligence data
- [ ] Implement FSR compliance checks using live API FSR limits
- [ ] Implement height compliance checks using live API height limits
- [ ] Implement site coverage calculations using live land area data
- [ ] Response time <100ms per calculation
- [ ] 95%+ accuracy using live data vs static text extraction

## TECHNICAL SPECIFICATION

### Phase Q1A: Live Data Integration Framework
```python
from services.nsw_planning_api import PropertyIntelligence, get_property_intelligence
from dataclasses import dataclass
from typing import Optional, Dict, Any
import asyncio
import time

@dataclass
class ComplianceResult:
    compliant: bool
    actual_value: float
    limit_value: float
    margin: Optional[float]
    units: str
    confidence: float
    data_source: str  # 'nsw_api' or 'fallback'
    calculation_time_ms: int

@dataclass
class ComplianceAssessment:
    fsr_compliance: Optional[ComplianceResult]
    height_compliance: Optional[ComplianceResult]
    site_coverage_compliance: Optional[ComplianceResult]
    overall_compliant: bool
    warnings: List[str]
    total_calculation_time_ms: int
```

### Phase Q1B: Live Compliance Engine
```python
class LiveComplianceEngine:
    """Real-time compliance calculator using NSW Planning API data"""

    def __init__(self):
        self.api_available = True

    async def calculate_compliance(self,
                                 address: str,
                                 proposed_development: Dict[str, Any],
                                 google_coords: Optional[Dict[str, float]] = None) -> ComplianceAssessment:
        """Calculate compliance using live NSW API data"""
        start_time = time.time()

        # Get live property intelligence
        try:
            intelligence = await get_property_intelligence(address, google_coords)
        except Exception as e:
            return self._fallback_compliance_assessment(str(e))

        # Extract proposed development parameters
        proposed_gfa = proposed_development.get('gross_floor_area', 0)
        proposed_height = proposed_development.get('height', 0)
        proposed_building_area = proposed_development.get('building_area', 0)

        results = []

        # FSR Compliance Check (using live API data)
        if intelligence.fsr_limit and proposed_gfa > 0:
            fsr_result = self._check_fsr_compliance(
                intelligence,
                proposed_gfa
            )
            results.append(fsr_result)

        # Height Compliance Check (using live API data)
        if intelligence.height_limit and proposed_height > 0:
            height_result = self._check_height_compliance(
                intelligence,
                proposed_height
            )
            results.append(height_result)

        # Site Coverage Check (using live area data)
        if intelligence.land_area and proposed_building_area > 0:
            coverage_result = self._check_site_coverage_compliance(
                intelligence,
                proposed_building_area
            )
            results.append(coverage_result)

        total_time = int((time.time() - start_time) * 1000)

        return ComplianceAssessment(
            fsr_compliance=next((r for r in results if 'fsr' in r.data_source.lower()), None),
            height_compliance=next((r for r in results if 'height' in r.data_source.lower()), None),
            site_coverage_compliance=next((r for r in results if 'coverage' in r.data_source.lower()), None),
            overall_compliant=all(r.compliant for r in results),
            warnings=self._generate_warnings(intelligence, results),
            total_calculation_time_ms=total_time
        )

    def _check_fsr_compliance(self,
                             intelligence: PropertyIntelligence,
                             proposed_gfa: float) -> ComplianceResult:
        """Check FSR compliance using live API FSR limit"""
        start_time = time.time()

        # Parse live FSR limit (e.g., "0.6:1" -> 0.6)
        fsr_limit_str = intelligence.fsr_limit.value if intelligence.fsr_limit else None
        if not fsr_limit_str:
            raise ValueError("No FSR limit available from NSW API")

        # Handle ratio format like "0.6:1"
        if ':1' in fsr_limit_str:
            fsr_limit = float(fsr_limit_str.replace(':1', ''))
        else:
            fsr_limit = float(fsr_limit_str)

        # Get land area from live API data
        land_area = self._parse_land_area(intelligence.land_area)
        if not land_area:
            raise ValueError("No land area available from NSW API")

        # Calculate actual FSR
        actual_fsr = proposed_gfa / land_area

        calculation_time = int((time.time() - start_time) * 1000)

        return ComplianceResult(
            compliant=actual_fsr <= fsr_limit,
            actual_value=round(actual_fsr, 2),
            limit_value=fsr_limit,
            margin=round(fsr_limit - actual_fsr, 2),
            units='ratio',
            confidence=0.98,  # High confidence - live API data
            data_source='nsw_api_fsr_limit',
            calculation_time_ms=calculation_time
        )

    def _check_height_compliance(self,
                               intelligence: PropertyIntelligence,
                               proposed_height: float) -> ComplianceResult:
        """Check height compliance using live API height limit"""
        start_time = time.time()

        # Parse live height limit (e.g., "9.5 m" -> 9.5)
        height_limit_str = intelligence.height_limit.value if intelligence.height_limit else None
        if not height_limit_str:
            raise ValueError("No height limit available from NSW API")

        # Extract numeric value
        import re
        height_match = re.search(r'(\d+\.?\d*)', height_limit_str)
        if not height_match:
            raise ValueError(f"Cannot parse height limit: {height_limit_str}")

        height_limit = float(height_match.group(1))
        units = intelligence.height_limit.units or 'm'

        calculation_time = int((time.time() - start_time) * 1000)

        return ComplianceResult(
            compliant=proposed_height <= height_limit,
            actual_value=proposed_height,
            limit_value=height_limit,
            margin=round(height_limit - proposed_height, 1),
            units=units,
            confidence=0.98,  # High confidence - live API data
            data_source='nsw_api_height_limit',
            calculation_time_ms=calculation_time
        )

    def _parse_land_area(self, land_area_str: Optional[str]) -> Optional[float]:
        """Parse land area from NSW API valuation data"""
        if not land_area_str:
            return None

        # Handle various formats: "300", "300.5", "300 sqm"
        import re
        area_match = re.search(r'(\d+\.?\d*)', str(land_area_str))
        return float(area_match.group(1)) if area_match else None
```

## IMPLEMENTATION STEPS

### Step 1: Create Live Compliance Engine (30 minutes)
```python
def create_live_compliance_engine():
    """Create the live compliance calculation engine"""

    engine_path = 'services/live_compliance_engine.py'

    engine_content = '''
from services.nsw_planning_api import PropertyIntelligence, get_property_intelligence
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import asyncio
import time
import re

@dataclass
class ComplianceResult:
    compliant: bool
    actual_value: float
    limit_value: float
    margin: Optional[float]
    units: str
    confidence: float
    data_source: str
    calculation_time_ms: int

@dataclass
class ComplianceAssessment:
    fsr_compliance: Optional[ComplianceResult] = None
    height_compliance: Optional[ComplianceResult] = None
    site_coverage_compliance: Optional[ComplianceResult] = None
    overall_compliant: bool = True
    warnings: List[str] = None
    total_calculation_time_ms: int = 0

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []

class LiveComplianceEngine:
    """Real-time compliance calculator using NSW Planning API data"""

    async def calculate_compliance(self,
                                 address: str,
                                 proposed_development: Dict[str, Any],
                                 google_coords: Optional[Dict[str, float]] = None) -> ComplianceAssessment:
        """Calculate compliance using live NSW API data"""
        start_time = time.time()

        # Get live property intelligence
        try:
            intelligence = await get_property_intelligence(address, google_coords)
        except Exception as e:
            return ComplianceAssessment(
                overall_compliant=False,
                warnings=[f"NSW API unavailable: {str(e)}"],
                total_calculation_time_ms=int((time.time() - start_time) * 1000)
            )

        assessment = ComplianceAssessment()

        # Extract proposed development parameters
        proposed_gfa = proposed_development.get('gross_floor_area', 0)
        proposed_height = proposed_development.get('height', 0)

        # FSR Compliance Check
        if intelligence.fsr_limit and proposed_gfa > 0:
            try:
                assessment.fsr_compliance = self._check_fsr_compliance(intelligence, proposed_gfa)
            except Exception as e:
                assessment.warnings.append(f"FSR check failed: {str(e)}")

        # Height Compliance Check
        if intelligence.height_limit and proposed_height > 0:
            try:
                assessment.height_compliance = self._check_height_compliance(intelligence, proposed_height)
            except Exception as e:
                assessment.warnings.append(f"Height check failed: {str(e)}")

        # Overall compliance
        compliance_results = [r for r in [assessment.fsr_compliance, assessment.height_compliance] if r]
        assessment.overall_compliant = all(r.compliant for r in compliance_results) if compliance_results else True

        assessment.total_calculation_time_ms = int((time.time() - start_time) * 1000)

        return assessment

    def _check_fsr_compliance(self, intelligence: PropertyIntelligence, proposed_gfa: float) -> ComplianceResult:
        """Check FSR compliance using live API FSR limit"""
        start_time = time.time()

        # Parse live FSR limit
        fsr_limit_str = intelligence.fsr_limit.value if intelligence.fsr_limit else None
        if not fsr_limit_str:
            raise ValueError("No FSR limit available")

        # Handle ratio format like "0.6:1"
        if ':1' in fsr_limit_str:
            fsr_limit = float(fsr_limit_str.replace(':1', ''))
        else:
            fsr_limit = float(re.search(r'(\d+\.?\d*)', fsr_limit_str).group(1))

        # Get land area
        land_area = self._parse_land_area(intelligence.land_area)
        if not land_area:
            raise ValueError("No land area available")

        # Calculate actual FSR
        actual_fsr = proposed_gfa / land_area

        return ComplianceResult(
            compliant=actual_fsr <= fsr_limit,
            actual_value=round(actual_fsr, 2),
            limit_value=fsr_limit,
            margin=round(fsr_limit - actual_fsr, 2),
            units='ratio',
            confidence=0.98,
            data_source='nsw_api_fsr',
            calculation_time_ms=int((time.time() - start_time) * 1000)
        )

    def _check_height_compliance(self, intelligence: PropertyIntelligence, proposed_height: float) -> ComplianceResult:
        """Check height compliance using live API height limit"""
        start_time = time.time()

        # Parse live height limit
        height_limit_str = intelligence.height_limit.value if intelligence.height_limit else None
        if not height_limit_str:
            raise ValueError("No height limit available")

        height_match = re.search(r'(\d+\.?\d*)', height_limit_str)
        if not height_match:
            raise ValueError(f"Cannot parse height: {height_limit_str}")

        height_limit = float(height_match.group(1))

        return ComplianceResult(
            compliant=proposed_height <= height_limit,
            actual_value=proposed_height,
            limit_value=height_limit,
            margin=round(height_limit - proposed_height, 1),
            units='m',
            confidence=0.98,
            data_source='nsw_api_height',
            calculation_time_ms=int((time.time() - start_time) * 1000)
        )

    def _parse_land_area(self, land_area_str: Optional[str]) -> Optional[float]:
        """Parse land area from NSW API data"""
        if not land_area_str:
            return None
        area_match = re.search(r'(\d+\.?\d*)', str(land_area_str))
        return float(area_match.group(1)) if area_match else None
'''

    with open(engine_path, 'w', encoding='utf-8') as f:
        f.write(engine_content)

    return engine_path
```

### Step 2: Create API Endpoint (25 minutes)
```python
def create_live_compliance_api():
    """Create API endpoint for live compliance calculations"""

    api_path = 'frontend-nextjs/app/api/compliance/live-check/route.ts'

    # Ensure directory exists
    os.makedirs(os.path.dirname(api_path), exist_ok=True)

    api_content = '''
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  const startTime = Date.now();

  try {
    const body = await request.json();
    const { address, proposed_development, coordinates } = body;

    if (!address || !proposed_development) {
      return NextResponse.json({
        success: false,
        error: 'Address and proposed development details required'
      }, { status: 400 });
    }

    // Call Python live compliance engine
    const pythonScript = `
import asyncio
import sys
import json
sys.path.append('${process.cwd()}')
from services.live_compliance_engine import LiveComplianceEngine

async def main():
    engine = LiveComplianceEngine()

    address = "${address}"
    proposed_dev = ${JSON.stringify(proposed_development)}
    coords = ${coordinates ? JSON.stringify(coordinates) : 'None'}

    result = await engine.calculate_compliance(address, proposed_dev, coords)

    # Convert to dict for JSON serialization
    return {
        'fsr_compliance': {
            'compliant': result.fsr_compliance.compliant if result.fsr_compliance else None,
            'actual_value': result.fsr_compliance.actual_value if result.fsr_compliance else None,
            'limit_value': result.fsr_compliance.limit_value if result.fsr_compliance else None,
            'margin': result.fsr_compliance.margin if result.fsr_compliance else None,
            'units': result.fsr_compliance.units if result.fsr_compliance else None,
            'data_source': result.fsr_compliance.data_source if result.fsr_compliance else None,
        } if result.fsr_compliance else None,
        'height_compliance': {
            'compliant': result.height_compliance.compliant if result.height_compliance else None,
            'actual_value': result.height_compliance.actual_value if result.height_compliance else None,
            'limit_value': result.height_compliance.limit_value if result.height_compliance else None,
            'margin': result.height_compliance.margin if result.height_compliance else None,
            'units': result.height_compliance.units if result.height_compliance else None,
            'data_source': result.height_compliance.data_source if result.height_compliance else None,
        } if result.height_compliance else None,
        'overall_compliant': result.overall_compliant,
        'warnings': result.warnings,
        'calculation_time_ms': result.total_calculation_time_ms
    }

result = asyncio.run(main())
print(json.dumps(result))
`;

    const { spawn } = require('child_process');
    const python = spawn('python', ['-c', pythonScript]);

    let result = '';
    python.stdout.on('data', (data) => {
      result += data.toString();
    });

    const complianceResult = await new Promise((resolve, reject) => {
      python.on('close', (code) => {
        if (code !== 0) {
          reject(new Error('Python calculation failed'));
        } else {
          try {
            resolve(JSON.parse(result.trim()));
          } catch (e) {
            reject(new Error('Invalid JSON response'));
          }
        }
      });
    });

    const response = {
      success: true,
      compliance: complianceResult,
      processing_time_ms: Date.now() - startTime
    };

    return NextResponse.json(response);

  } catch (error) {
    return NextResponse.json({
      success: false,
      error: error.message,
      processing_time_ms: Date.now() - startTime
    }, { status: 500 });
  }
}
'''

    with open(api_path, 'w', encoding='utf-8') as f:
        f.write(api_content)

    return api_path
```

### Step 3: Create Verification Tests (35 minutes)
```python
def create_verification_tests():
    """Create comprehensive verification tests"""

    test_cases = [
        {
            'description': 'Live FSR compliance check - R2 zone',
            'address': '45 Liverpool Street, Ashfield NSW 2131',
            'proposed_development': {
                'gross_floor_area': 180,  # sqm
                'height': 8.0  # metres
            },
            'expected_performance': '<100ms',
            'expected_accuracy': '>95%'
        },
        {
            'description': 'Live height compliance - mixed use',
            'address': '15 Norton Street, Leichhardt NSW 2040',
            'proposed_development': {
                'gross_floor_area': 250,
                'height': 12.0
            },
            'expected_performance': '<100ms',
            'expected_accuracy': '>95%'
        }
    ]

    async def run_verification():
        engine = LiveComplianceEngine()
        results = []

        for test in test_cases:
            start_time = time.time()

            try:
                result = await engine.calculate_compliance(
                    test['address'],
                    test['proposed_development']
                )

                performance_ms = result.total_calculation_time_ms
                performance_ok = performance_ms < 100

                results.append({
                    'test': test['description'],
                    'performance_ms': performance_ms,
                    'performance_ok': performance_ok,
                    'api_data_used': any([
                        result.fsr_compliance and 'nsw_api' in result.fsr_compliance.data_source,
                        result.height_compliance and 'nsw_api' in result.height_compliance.data_source
                    ]),
                    'overall_compliant': result.overall_compliant,
                    'warnings': result.warnings,
                    'passed': performance_ok and len(result.warnings) == 0
                })

            except Exception as e:
                results.append({
                    'test': test['description'],
                    'error': str(e),
                    'passed': False
                })

        return results

    return asyncio.run(run_verification())
```

## VERIFICATION CHECKLIST

### Live API Integration
- [ ] LiveComplianceEngine uses PropertyIntelligence data
- [ ] FSR calculations use live NSW API FSR limits
- [ ] Height calculations use live NSW API height limits
- [ ] Land area sourced from NSW valuation service
- [ ] All calculations <100ms response time

### Accuracy Verification
- [ ] FSR compliance accuracy >95% vs manual calculation
- [ ] Height compliance accuracy >95% vs manual calculation
- [ ] API data confidence scores >90%
- [ ] Graceful degradation when API unavailable

### Performance Benchmarks
- [ ] Individual compliance checks <50ms
- [ ] Total assessment <100ms
- [ ] Memory usage <50MB per calculation
- [ ] Concurrent request handling

## DELIVERABLES

1. **live_compliance_engine.py** - Core calculation engine using NSW API data
2. **live-check API endpoint** - REST API for compliance calculations
3. **verification_tests.py** - Comprehensive test suite
4. **performance_benchmarks.json** - Response time measurements
5. **api_integration_report.md** - NSW API integration documentation

## ESTIMATED TIME
**2 hours total**
- Engine creation: 30 minutes
- API endpoint: 25 minutes
- Verification tests: 35 minutes
- Performance optimization: 20 minutes
- Documentation: 10 minutes

## COMPLETION CRITERIA
✅ Live compliance calculations using NSW API data
✅ Response times <100ms per calculation
✅ 95%+ accuracy using live data vs text extraction
✅ Graceful API fallback handling
✅ Comprehensive verification test suite