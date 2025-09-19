#!/usr/bin/env python3
"""
Live Compliance Calculator Engine - PRP-Q1 Implementation
Real-time compliance calculations using NSW Planning API data

Leverages existing NSW Planning API integration for superior accuracy
compared to text extraction approaches.
"""

from services.nsw_planning_api import PropertyIntelligence, get_property_intelligence
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import asyncio
import time
import re
import logging

logger = logging.getLogger(__name__)

@dataclass
class ComplianceResult:
    """Individual compliance check result"""
    compliant: bool
    actual_value: float
    limit_value: float
    margin: Optional[float]
    units: str
    confidence: float
    data_source: str  # 'nsw_api_fsr', 'nsw_api_height', etc.
    calculation_time_ms: int

@dataclass
class ComplianceAssessment:
    """Complete compliance assessment result"""
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

    def __init__(self):
        """Initialize the live compliance engine"""
        pass

    async def calculate_compliance(self,
                                 address: str,
                                 proposed_development: Dict[str, Any],
                                 google_coords: Optional[Dict[str, float]] = None) -> ComplianceAssessment:
        """Calculate compliance using live NSW API data

        Args:
            address: Property address
            proposed_development: Dict with keys like 'gross_floor_area', 'height', 'building_area'
            google_coords: Optional coordinates for more accurate property lookup

        Returns:
            ComplianceAssessment with individual compliance results
        """
        start_time = time.time()

        try:
            # Get live property intelligence from NSW APIs
            intelligence = await get_property_intelligence(address, google_coords)
        except Exception as e:
            logger.error(f"Failed to get property intelligence for {address}: {e}")
            return ComplianceAssessment(
                overall_compliant=False,
                warnings=[f"NSW API unavailable: {str(e)}"],
                total_calculation_time_ms=int((time.time() - start_time) * 1000)
            )

        assessment = ComplianceAssessment()

        # Extract proposed development parameters
        proposed_gfa = proposed_development.get('gross_floor_area', 0)
        proposed_height = proposed_development.get('height', 0)
        proposed_building_area = proposed_development.get('building_area', 0)

        # FSR Compliance Check (using live API data)
        if intelligence.fsr_limit and proposed_gfa > 0:
            try:
                assessment.fsr_compliance = self._check_fsr_compliance(intelligence, proposed_gfa)
            except Exception as e:
                logger.warning(f"FSR compliance check failed: {e}")
                assessment.warnings.append(f"FSR check failed: {str(e)}")

        # Height Compliance Check (using live API data)
        if intelligence.height_limit and proposed_height > 0:
            try:
                assessment.height_compliance = self._check_height_compliance(intelligence, proposed_height)
            except Exception as e:
                logger.warning(f"Height compliance check failed: {e}")
                assessment.warnings.append(f"Height check failed: {str(e)}")

        # Site Coverage Check (using live area data)
        if intelligence.land_area and proposed_building_area > 0:
            try:
                assessment.site_coverage_compliance = self._check_site_coverage_compliance(
                    intelligence, proposed_building_area
                )
            except Exception as e:
                logger.warning(f"Site coverage check failed: {e}")
                assessment.warnings.append(f"Site coverage check failed: {str(e)}")

        # Calculate overall compliance
        compliance_results = [
            r for r in [assessment.fsr_compliance, assessment.height_compliance, assessment.site_coverage_compliance]
            if r is not None
        ]

        if compliance_results:
            assessment.overall_compliant = all(r.compliant for r in compliance_results)
        else:
            assessment.overall_compliant = False
            assessment.warnings.append("No compliance checks could be performed")

        assessment.total_calculation_time_ms = int((time.time() - start_time) * 1000)

        return assessment

    def _check_fsr_compliance(self, intelligence: PropertyIntelligence, proposed_gfa: float) -> ComplianceResult:
        """Check FSR compliance using live API FSR limit"""
        start_time = time.time()

        # Parse live FSR limit from NSW API (e.g., "0.6:1" -> 0.6)
        fsr_limit_str = intelligence.fsr_limit.value if intelligence.fsr_limit else None
        if not fsr_limit_str:
            raise ValueError("No FSR limit available from NSW API")

        # Handle ratio format like "0.6:1"
        if ':1' in fsr_limit_str:
            fsr_limit = float(fsr_limit_str.replace(':1', ''))
        else:
            # Extract numeric value using regex
            fsr_match = re.search(r'(\d+\.?\d*)', fsr_limit_str)
            if not fsr_match:
                raise ValueError(f"Cannot parse FSR limit: {fsr_limit_str}")
            fsr_limit = float(fsr_match.group(1))

        # Get land area from live API data
        land_area = self._parse_land_area(intelligence.land_area)
        if not land_area or land_area <= 0:
            raise ValueError("No valid land area available from NSW API")

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
            data_source='nsw_api_fsr',
            calculation_time_ms=calculation_time
        )

    def _check_height_compliance(self, intelligence: PropertyIntelligence, proposed_height: float) -> ComplianceResult:
        """Check height compliance using live API height limit"""
        start_time = time.time()

        # Parse live height limit from NSW API (e.g., "9.5 m" -> 9.5)
        height_limit_str = intelligence.height_limit.value if intelligence.height_limit else None
        if not height_limit_str:
            raise ValueError("No height limit available from NSW API")

        # Extract numeric value
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
            data_source='nsw_api_height',
            calculation_time_ms=calculation_time
        )

    def _check_site_coverage_compliance(self, intelligence: PropertyIntelligence,
                                      proposed_building_area: float) -> ComplianceResult:
        """Check site coverage compliance using live land area data"""
        start_time = time.time()

        # Get land area from NSW API valuation data
        land_area = self._parse_land_area(intelligence.land_area)
        if not land_area or land_area <= 0:
            raise ValueError("No valid land area available from NSW API")

        # Get zone from live API data for site coverage limits
        zone = intelligence.zone.value if intelligence.zone else 'R2'  # Default fallback

        # Site coverage limits by zone (typical Inner West LEP)
        coverage_limits = {
            'R1': 0.40,  # 40%
            'R2': 0.50,  # 50%
            'R3': 0.60,  # 60%
            'R4': 0.60,  # 60%
            'B1': 0.80,  # 80%
            'B2': 0.80,  # 80%
            'B3': 0.80,  # 80%
            'B4': 0.60,  # 60%
            'IN1': 0.60, # 60%
            'IN2': 0.60, # 60%
        }

        coverage_limit = coverage_limits.get(zone, 0.50)  # Default 50%
        actual_coverage = proposed_building_area / land_area

        calculation_time = int((time.time() - start_time) * 1000)

        return ComplianceResult(
            compliant=actual_coverage <= coverage_limit,
            actual_value=round(actual_coverage * 100, 1),
            limit_value=round(coverage_limit * 100, 1),
            margin=round((coverage_limit - actual_coverage) * 100, 1),
            units='%',
            confidence=0.85,  # Good confidence from zone + live area data
            data_source='nsw_api_coverage',
            calculation_time_ms=calculation_time
        )

    def _parse_land_area(self, land_area_str: Optional[str]) -> Optional[float]:
        """Parse land area from NSW API valuation data"""
        if not land_area_str:
            return None

        # Handle various formats: "300", "300.5", "300 sqm", etc.
        area_match = re.search(r'(\d+\.?\d*)', str(land_area_str))
        if area_match:
            return float(area_match.group(1))

        return None

# Convenience function for direct use
async def calculate_property_compliance(address: str,
                                      proposed_development: Dict[str, Any],
                                      google_coords: Optional[Dict[str, float]] = None) -> ComplianceAssessment:
    """Convenience function for direct compliance calculation

    Args:
        address: Property address
        proposed_development: Development proposal with 'gross_floor_area', 'height', 'building_area'
        google_coords: Optional coordinates for better property matching

    Returns:
        ComplianceAssessment with results
    """
    engine = LiveComplianceEngine()
    return await engine.calculate_compliance(address, proposed_development, google_coords)

# Test function
async def test_live_compliance_engine():
    """Test the live compliance engine with sample data"""

    test_scenarios = [
        {
            'address': '45 Liverpool Street, Ashfield NSW 2131',
            'proposal': {
                'gross_floor_area': 180,  # sqm
                'height': 8.5,  # metres
                'building_area': 120  # sqm
            }
        },
        {
            'address': '15 Norton Street, Leichhardt NSW 2040',
            'proposal': {
                'gross_floor_area': 250,  # sqm
                'height': 12.0,  # metres
                'building_area': 150  # sqm
            }
        }
    ]

    engine = LiveComplianceEngine()

    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n=== Test Scenario {i}: {scenario['address']} ===")

        try:
            start_time = time.time()
            result = await engine.calculate_compliance(
                scenario['address'],
                scenario['proposal']
            )
            total_time = int((time.time() - start_time) * 1000)

            print(f"Overall Compliant: {result.overall_compliant}")
            print(f"Total Time: {total_time}ms")

            if result.fsr_compliance:
                fsr = result.fsr_compliance
                print(f"FSR: {fsr.actual_value} vs {fsr.limit_value} limit ({'✅' if fsr.compliant else '❌'})")
                print(f"  Source: {fsr.data_source}, Time: {fsr.calculation_time_ms}ms")

            if result.height_compliance:
                height = result.height_compliance
                print(f"Height: {height.actual_value}{height.units} vs {height.limit_value}{height.units} limit ({'✅' if height.compliant else '❌'})")
                print(f"  Source: {height.data_source}, Time: {height.calculation_time_ms}ms")

            if result.site_coverage_compliance:
                coverage = result.site_coverage_compliance
                print(f"Site Coverage: {coverage.actual_value}{coverage.units} vs {coverage.limit_value}{coverage.units} limit ({'✅' if coverage.compliant else '❌'})")
                print(f"  Source: {coverage.data_source}, Time: {coverage.calculation_time_ms}ms")

            if result.warnings:
                print(f"Warnings: {', '.join(result.warnings)}")

        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    # Run test
    asyncio.run(test_live_compliance_engine())