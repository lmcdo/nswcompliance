# PRP-Q3: Advanced Compliance Rules Engine

## OBJECTIVE
Implement complex multi-factor compliance assessment engine that combines live NSW API data with regulatory provisions for comprehensive site coverage, parking, landscaping, and setback compliance checks.

## SUCCESS CRITERIA
- [ ] Create AdvancedComplianceEngine using live API data + provisions
- [ ] Implement site coverage calculations using live land area
- [ ] Implement parking requirements using development type + live zone data
- [ ] Implement landscaping requirements with zone-specific rules
- [ ] Combine multiple compliance factors into overall assessment
- [ ] Response time <200ms for multi-factor assessment
- [ ] 90%+ accuracy on complex compliance scenarios

## TECHNICAL SPECIFICATION

### Phase Q3A: Multi-Factor Compliance Framework
```python
from services.nsw_planning_api import PropertyIntelligence, get_property_intelligence
from services.live_compliance_engine import ComplianceResult
from dataclasses import dataclass
from typing import Optional, Dict, List, Any
import sqlite3
import time

@dataclass
class AdvancedComplianceResult:
    site_coverage: Optional[ComplianceResult]
    parking_compliance: Optional[ComplianceResult]
    landscaping_compliance: Optional[ComplianceResult]
    setback_compliance: Optional[ComplianceResult]
    overall_compliant: bool
    compliance_score: float  # 0.0 to 1.0
    critical_failures: List[str]
    warnings: List[str]
    recommendations: List[str]
    total_processing_time_ms: int

@dataclass
class DevelopmentProposal:
    development_type: str
    gross_floor_area: float
    building_area: float  # footprint
    height: float
    storeys: int
    dwelling_count: int
    proposed_parking_spaces: int
    landscaped_area: float
    setbacks: Dict[str, float]  # {'front': 6.0, 'side': 1.5, 'rear': 6.0}
```

### Phase Q3B: Advanced Compliance Engine
```python
class AdvancedComplianceEngine:
    """Complex multi-factor compliance assessment using live API + provisions"""

    def __init__(self):
        self.load_compliance_standards()

    def load_compliance_standards(self):
        """Load compliance standards from regulatory provisions"""
        conn = sqlite3.connect('nsw_planning.db')
        cursor = conn.cursor()

        # Load parking rates by zone and development type
        cursor.execute("""
        SELECT zone, development_type, provision_text
        FROM regulatory_provisions
        WHERE LOWER(provision_text) LIKE '%parking%'
        AND provision_text REGEXP '[0-9]+'
        """)

        parking_provisions = cursor.fetchall()
        self.parking_standards = self._parse_parking_standards(parking_provisions)

        # Load landscaping requirements
        cursor.execute("""
        SELECT zone, provision_text
        FROM regulatory_provisions
        WHERE LOWER(provision_text) LIKE '%landscap%'
        AND (LOWER(provision_text) LIKE '%percent%' OR provision_text REGEXP '[0-9]+%')
        """)

        landscaping_provisions = cursor.fetchall()
        self.landscaping_standards = self._parse_landscaping_standards(landscaping_provisions)

        conn.close()

    async def assess_advanced_compliance(self,
                                        address: str,
                                        proposal: DevelopmentProposal,
                                        google_coords: Optional[Dict[str, float]] = None) -> AdvancedComplianceResult:
        """Comprehensive compliance assessment"""

        start_time = time.time()

        # Get live property intelligence
        try:
            intelligence = await get_property_intelligence(address, google_coords)
        except Exception as e:
            return self._create_error_result(str(e), start_time)

        if not intelligence.zone:
            return self._create_error_result("No zone data from NSW API", start_time)

        live_zone = intelligence.zone.value
        land_area = self._parse_land_area(intelligence.land_area)

        if not land_area:
            return self._create_error_result("No land area data available", start_time)

        # Perform individual compliance checks
        compliance_results = []

        # Site Coverage Check
        if proposal.building_area > 0:
            site_coverage_result = self._check_site_coverage(
                live_zone, land_area, proposal.building_area
            )
            compliance_results.append(site_coverage_result)

        # Parking Compliance Check
        parking_result = self._check_parking_compliance(
            live_zone, proposal.development_type, proposal.dwelling_count,
            proposal.gross_floor_area, proposal.proposed_parking_spaces
        )
        compliance_results.append(parking_result)

        # Landscaping Compliance Check
        if proposal.landscaped_area >= 0:  # 0 is valid for urban areas
            landscaping_result = self._check_landscaping_compliance(
                live_zone, land_area, proposal.landscaped_area
            )
            compliance_results.append(landscaping_result)

        # Setback Compliance Check (using existing setback calculator)
        setback_result = await self._check_setback_compliance(
            intelligence, proposal.development_type, proposal.setbacks
        )
        if setback_result:
            compliance_results.append(setback_result)

        # Calculate overall compliance
        compliant_results = [r for r in compliance_results if r and r.compliant]
        total_results = [r for r in compliance_results if r]

        overall_compliant = len(compliant_results) == len(total_results) if total_results else False
        compliance_score = len(compliant_results) / len(total_results) if total_results else 0.0

        # Generate insights
        critical_failures = [
            f"{r.data_source}: {r.actual_value} {r.units} exceeds limit of {r.limit_value} {r.units}"
            for r in total_results if r and not r.compliant and r.margin and r.margin < -20  # Significant breach
        ]

        warnings = [
            f"{r.data_source}: Close to limit ({r.actual_value} vs {r.limit_value} {r.units})"
            for r in total_results if r and r.compliant and r.margin and 0 <= r.margin <= 10  # Close to limit
        ]

        recommendations = self._generate_recommendations(total_results, proposal, live_zone)

        total_time = int((time.time() - start_time) * 1000)

        return AdvancedComplianceResult(
            site_coverage=next((r for r in total_results if r and 'coverage' in r.data_source), None),
            parking_compliance=next((r for r in total_results if r and 'parking' in r.data_source), None),
            landscaping_compliance=next((r for r in total_results if r and 'landscap' in r.data_source), None),
            setback_compliance=next((r for r in total_results if r and 'setback' in r.data_source), None),
            overall_compliant=overall_compliant,
            compliance_score=compliance_score,
            critical_failures=critical_failures,
            warnings=warnings,
            recommendations=recommendations,
            total_processing_time_ms=total_time
        )

    def _check_site_coverage(self, zone: str, land_area: float, building_area: float) -> ComplianceResult:
        """Check site coverage compliance"""
        start_time = time.time()

        # Site coverage limits by zone (Inner West LEP typical)
        coverage_limits = {
            'R1': 0.40,  # 40%
            'R2': 0.50,  # 50%
            'R3': 0.60,  # 60%
            'R4': 0.60,  # 60%
            'B1': 0.80,  # 80%
            'B2': 0.80,  # 80%
        }

        coverage_limit = coverage_limits.get(zone, 0.50)  # Default 50%
        actual_coverage = building_area / land_area

        return ComplianceResult(
            compliant=actual_coverage <= coverage_limit,
            actual_value=round(actual_coverage * 100, 1),
            limit_value=round(coverage_limit * 100, 1),
            margin=round((coverage_limit - actual_coverage) * 100, 1),
            units='%',
            confidence=0.85,  # Good confidence from zone standards
            data_source='site_coverage_assessment',
            calculation_time_ms=int((time.time() - start_time) * 1000)
        )

    def _check_parking_compliance(self,
                                 zone: str,
                                 development_type: str,
                                 dwelling_count: int,
                                 gfa: float,
                                 proposed_spaces: int) -> ComplianceResult:
        """Check parking compliance using zone-specific rates"""
        start_time = time.time()

        # Parking requirements by development type (Inner West DCP typical)
        parking_rates = {
            'dwelling_house': {'rate': 2, 'unit': 'per_dwelling'},
            'residential_flat_building': {'rate': 1, 'unit': 'per_dwelling'},
            'boarding_house': {'rate': 0.5, 'unit': 'per_bed'},
            'retail_premises': {'rate': 4, 'unit': 'per_100sqm'},
            'office_premises': {'rate': 2.5, 'unit': 'per_100sqm'},
        }

        if development_type not in parking_rates:
            return ComplianceResult(
                compliant=True,
                actual_value=proposed_spaces,
                limit_value=0,
                margin=0,
                units='spaces',
                confidence=0.3,  # Low confidence - unknown type
                data_source='parking_assessment_unknown_type',
                calculation_time_ms=int((time.time() - start_time) * 1000)
            )

        rate_info = parking_rates[development_type]

        if rate_info['unit'] == 'per_dwelling':
            required_spaces = dwelling_count * rate_info['rate']
        elif rate_info['unit'] == 'per_100sqm':
            required_spaces = (gfa / 100) * rate_info['rate']
        else:
            required_spaces = proposed_spaces  # Fallback

        required_spaces = max(1, int(required_spaces))  # Minimum 1 space

        return ComplianceResult(
            compliant=proposed_spaces >= required_spaces,
            actual_value=proposed_spaces,
            limit_value=required_spaces,
            margin=proposed_spaces - required_spaces,
            units='spaces',
            confidence=0.9,  # High confidence from DCP standards
            data_source='parking_assessment',
            calculation_time_ms=int((time.time() - start_time) * 1000)
        )

    def _check_landscaping_compliance(self,
                                    zone: str,
                                    land_area: float,
                                    landscaped_area: float) -> ComplianceResult:
        """Check landscaping compliance"""
        start_time = time.time()

        # Landscaping requirements by zone (Inner West DCP typical)
        landscaping_requirements = {
            'R1': 0.40,  # 40% landscaped area
            'R2': 0.30,  # 30% landscaped area
            'R3': 0.25,  # 25% landscaped area
            'R4': 0.20,  # 20% landscaped area
            'B1': 0.10,  # 10% landscaped area
            'B2': 0.10,  # 10% landscaped area
        }

        required_ratio = landscaping_requirements.get(zone, 0.20)  # Default 20%
        required_area = land_area * required_ratio
        actual_ratio = landscaped_area / land_area

        return ComplianceResult(
            compliant=landscaped_area >= required_area,
            actual_value=round(actual_ratio * 100, 1),
            limit_value=round(required_ratio * 100, 1),
            margin=round((actual_ratio - required_ratio) * 100, 1),
            units='%',
            confidence=0.85,
            data_source='landscaping_assessment',
            calculation_time_ms=int((time.time() - start_time) * 1000)
        )

    async def _check_setback_compliance(self,
                                      intelligence: PropertyIntelligence,
                                      development_type: str,
                                      proposed_setbacks: Dict[str, float]) -> Optional[ComplianceResult]:
        """Check setback compliance using existing calculator"""

        # This would integrate with existing setback calculator
        # For now, simplified implementation
        start_time = time.time()

        # Basic setback requirements by zone
        zone = intelligence.zone.value if intelligence.zone else 'R2'

        setback_requirements = {
            'R1': {'front': 6.0, 'side': 1.5, 'rear': 6.0},
            'R2': {'front': 6.0, 'side': 1.2, 'rear': 6.0},
            'R3': {'front': 3.0, 'side': 1.2, 'rear': 3.0},
            'R4': {'front': 3.0, 'side': 1.2, 'rear': 3.0},
        }

        if zone not in setback_requirements:
            return None

        required_setbacks = setback_requirements[zone]

        # Check if all setbacks meet requirements
        non_compliant = []
        for position, required in required_setbacks.items():
            proposed = proposed_setbacks.get(position, 0)
            if proposed < required:
                non_compliant.append(f"{position}: {proposed}m < {required}m")

        is_compliant = len(non_compliant) == 0

        return ComplianceResult(
            compliant=is_compliant,
            actual_value=min(proposed_setbacks.values()) if proposed_setbacks else 0,
            limit_value=min(required_setbacks.values()),
            margin=None,  # Complex calculation for setbacks
            units='m',
            confidence=0.8,
            data_source='setback_assessment',
            calculation_time_ms=int((time.time() - start_time) * 1000)
        )

    def _generate_recommendations(self,
                                 results: List[ComplianceResult],
                                 proposal: DevelopmentProposal,
                                 zone: str) -> List[str]:
        """Generate improvement recommendations"""

        recommendations = []

        for result in results:
            if not result or result.compliant:
                continue

            if 'coverage' in result.data_source:
                excess_area = (result.actual_value - result.limit_value) / 100 * proposal.building_area
                recommendations.append(f"Reduce building footprint by {excess_area:.0f}sqm to meet site coverage")

            elif 'parking' in result.data_source:
                shortfall = result.limit_value - result.actual_value
                recommendations.append(f"Add {shortfall} parking space(s) to meet requirements")

            elif 'landscap' in result.data_source:
                shortfall = (result.limit_value - result.actual_value) / 100
                recommendations.append(f"Increase landscaped area by {shortfall:.1f}% of site")

        return recommendations
```

## IMPLEMENTATION STEPS

### Step 1: Create Advanced Compliance Engine (45 minutes)
### Step 2: Create Multi-Factor API Endpoint (35 minutes)
### Step 3: Create Comprehensive Verification Tests (25 minutes)
### Step 4: Integration with Existing Systems (15 minutes)

## VERIFICATION CHECKLIST

### Multi-Factor Assessment
- [ ] Site coverage calculations using live land area data
- [ ] Parking compliance using zone-specific requirements
- [ ] Landscaping compliance with zone-based percentages
- [ ] Setback compliance integration with existing calculator
- [ ] Overall compliance scoring methodology

### Performance Requirements
- [ ] Multi-factor assessment <200ms response time
- [ ] Individual compliance checks <50ms each
- [ ] Handles multiple development scenarios
- [ ] Graceful degradation when API data unavailable

### Accuracy Verification
- [ ] 90%+ accuracy on complex compliance scenarios
- [ ] Cross-validation with manual assessments
- [ ] Confidence scoring reflects data quality
- [ ] Recommendations are actionable and specific

## DELIVERABLES

1. **advanced_compliance_engine.py** - Multi-factor compliance assessment
2. **advanced-compliance API endpoint** - REST API for complex assessments
3. **compliance_verification_suite.py** - Comprehensive test cases
4. **multi_factor_accuracy_report.json** - Accuracy measurement results
5. **compliance_recommendations_engine.py** - Improvement suggestions

## ESTIMATED TIME
**2 hours total**
- Engine development: 45 minutes
- API endpoint: 35 minutes
- Verification tests: 25 minutes
- Integration: 15 minutes

## COMPLETION CRITERIA
✅ Multi-factor compliance assessment (coverage, parking, landscaping, setbacks)
✅ <200ms response time for complex assessments
✅ 90%+ accuracy on multi-variable compliance scenarios
✅ Integration with live NSW API data and existing systems
✅ Actionable improvement recommendations