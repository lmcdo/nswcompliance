#!/usr/bin/env python3
"""Property Intelligence Service

Transforms NSW Planning API data into structured property intelligence
for the Regulatory Radar UI left column display.
"""

from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from enum import Enum
try:
    from .nsw_planning_api import PropertyIntelligence, PlanningControl, get_property_intelligence
except ImportError:
    from nsw_planning_api import PropertyIntelligence, PlanningControl, get_property_intelligence

class ComplianceStatus(Enum):
    COMPLIANT = "OK"
    NON_COMPLIANT = "FAIL"  
    UNKNOWN = "?"

@dataclass
class QuickMetric:
    """Individual property metric for dashboard"""
    name: str
    value: str
    status: ComplianceStatus
    details: Optional[str] = None

@dataclass
class PropertyDashboard:
    """Structured property intelligence for UI display"""
    # Basic Info
    address: str
    prop_id: Optional[int] = None
    nsw_portal_link: Optional[str] = None
    
    # Planning Controls
    zone: Optional[str] = None
    zone_description: Optional[str] = None
    height_limit: Optional[str] = None
    height_units: Optional[str] = None
    height_clause: Optional[str] = None
    lot_size_req: Optional[str] = None
    fsr_limit: Optional[str] = None
    
    # Property Details
    land_area: Optional[str] = None
    land_value: Optional[str] = None
    
    # Overlays & Constraints
    heritage_status: Optional[str] = None
    heritage_items: List[str] = None
    other_overlays: List[str] = None
    applicable_lep: Optional[str] = None
    lga_name: Optional[str] = None
    
    # Quick Metrics
    quick_metrics: List[QuickMetric] = None
    
    # Status
    data_quality: str = "Unknown"
    api_success: bool = False
    
    def __post_init__(self):
        if self.heritage_items is None:
            self.heritage_items = []
        if self.other_overlays is None:
            self.other_overlays = []
        if self.quick_metrics is None:
            self.quick_metrics = []
        
        # Generate NSW Portal link
        if self.prop_id:
            self.nsw_portal_link = f"https://www.planningportal.nsw.gov.au/property-details/{self.prop_id}"

class PropertyIntelligenceService:
    """Service to convert NSW API data to UI-ready property dashboard"""
    
    @staticmethod
    async def get_property_dashboard(address: str, google_coords: Optional[Dict[str, float]] = None) -> PropertyDashboard:
        """Get complete property dashboard for address"""
        
        # Get raw data from NSW APIs with optional Google coordinates for validation
        intelligence = await get_property_intelligence(address, google_coords)
        
        # Transform to UI-ready format
        dashboard = PropertyDashboard(
            address=address,
            prop_id=intelligence.prop_id,
            api_success=intelligence.prop_id is not None
        )
        
        # Process zone information
        if intelligence.zone:
            dashboard.zone = intelligence.zone.value
            dashboard.zone_description = PropertyIntelligenceService._get_zone_description(intelligence.zone.value)
            dashboard.applicable_lep = intelligence.zone.epi_name
            dashboard.lga_name = intelligence.zone.lga_name
        
        # Process height limits  
        if intelligence.height_limit:
            dashboard.height_limit = intelligence.height_limit.value
            dashboard.height_units = intelligence.height_limit.units or "m"
            dashboard.height_clause = intelligence.height_limit.legislative_clause
        
        # Process lot size requirements
        if intelligence.lot_size_req:
            dashboard.lot_size_req = f"{intelligence.lot_size_req.value} {intelligence.lot_size_req.units or 'm²'}"
        
        # Process FSR limits
        if intelligence.fsr_limit:
            dashboard.fsr_limit = intelligence.fsr_limit.value
            
        # Process land area and value
        dashboard.land_area = intelligence.land_area
        dashboard.land_value = intelligence.land_value
        
        # Process heritage items
        if intelligence.heritage_items:
            dashboard.heritage_status = f"{len(intelligence.heritage_items)} heritage item(s)"
            dashboard.heritage_items = [
                f"{item.layer_name}: {item.value}" for item in intelligence.heritage_items
            ]
        
        # Process other overlays
        dashboard.other_overlays = [
            f"{control.layer_name}: {control.value}" 
            for control in intelligence.other_controls
        ]
        
        # Generate quick metrics
        dashboard.quick_metrics = PropertyIntelligenceService._generate_quick_metrics(intelligence)
        
        # Assess data quality
        dashboard.data_quality = PropertyIntelligenceService._assess_data_quality(intelligence)
        
        return dashboard
    
    @staticmethod
    def _get_zone_description(zone_code: str) -> str:
        """Get human-readable description for zone code"""
        zone_descriptions = {
            "R1": "General Residential",
            "R2": "Low Density Residential", 
            "R3": "Medium Density Residential",
            "R4": "High Density Residential",
            "R5": "Large Lot Residential",
            "B1": "Neighbourhood Centre",
            "B2": "Local Centre", 
            "B3": "Commercial Core",
            "B4": "Mixed Use",
            "B5": "Business Development",
            "B6": "Enterprise Corridor",
            "B7": "Business Park",
            "B8": "Metropolitan Centre",
            "IN1": "General Industrial",
            "IN2": "Light Industrial",
            "IN3": "Heavy Industrial",
            "IN4": "Working Waterfront",
            "SP1": "Special Activities",
            "SP2": "Infrastructure",
            "SP3": "Tourist",
            "C1": "National Parks and Nature Reserves",
            "C2": "Environmental Conservation",
            "C3": "Environmental Management", 
            "C4": "Environmental Living",
            "E1": "National Parks and Nature Reserves",
            "E2": "Environmental Conservation",
            "E3": "Environmental Management",
            "E4": "Environmental Living",
            "RE1": "Public Recreation",
            "RE2": "Private Recreation"
        }
        return zone_descriptions.get(zone_code, f"Zone {zone_code}")
    
    @staticmethod
    def _generate_quick_metrics(intelligence: PropertyIntelligence) -> List[QuickMetric]:
        """Generate quick assessment metrics"""
        metrics = []
        
        # API Data Quality Metric
        if intelligence.prop_id:
            metrics.append(QuickMetric(
                name="NSW Portal Data",
                value="Available",
                status=ComplianceStatus.COMPLIANT,
                details=f"Property ID: {intelligence.prop_id}"
            ))
        else:
            metrics.append(QuickMetric(
                name="NSW Portal Data", 
                value="Not Found",
                status=ComplianceStatus.NON_COMPLIANT,
                details="Address not found in NSW Planning Portal"
            ))
        
        # Zone Information
        if intelligence.zone:
            metrics.append(QuickMetric(
                name="Planning Zone",
                value=f"Identified ({intelligence.zone.value})",
                status=ComplianceStatus.COMPLIANT,
                details=intelligence.zone.epi_name
            ))
        
        # Height Limits
        if intelligence.height_limit:
            metrics.append(QuickMetric(
                name="Height Controls",
                value=f"{intelligence.height_limit.value} {intelligence.height_limit.units or 'm'}",
                status=ComplianceStatus.COMPLIANT,
                details=intelligence.height_limit.legislative_clause
            ))
        
        # Heritage Status
        if intelligence.heritage_items:
            metrics.append(QuickMetric(
                name="Heritage Status", 
                value=f"{len(intelligence.heritage_items)} item(s)",
                status=ComplianceStatus.COMPLIANT,
                details="Heritage constraints apply"
            ))
        else:
            metrics.append(QuickMetric(
                name="Heritage Status",
                value="No heritage constraints",
                status=ComplianceStatus.COMPLIANT
            ))
        
        # Development Potential Assessment
        dev_potential = "Medium"
        dev_status = ComplianceStatus.UNKNOWN
        
        if intelligence.zone and intelligence.zone.value in ["R1", "R2", "R3"]:
            dev_potential = "Residential Development"
            dev_status = ComplianceStatus.COMPLIANT
        elif intelligence.zone and intelligence.zone.value.startswith("B"):
            dev_potential = "Commercial Development" 
            dev_status = ComplianceStatus.COMPLIANT
        elif intelligence.heritage_items:
            dev_potential = "Heritage Constrained"
            dev_status = ComplianceStatus.NON_COMPLIANT
        
        metrics.append(QuickMetric(
            name="Development Potential",
            value=dev_potential,
            status=dev_status,
            details="Based on zone and overlays"
        ))
        
        return metrics
    
    @staticmethod
    def _assess_data_quality(intelligence: PropertyIntelligence) -> str:
        """Assess quality and completeness of property data"""
        score = 0
        max_score = 5
        
        if intelligence.prop_id:
            score += 1
        if intelligence.zone:
            score += 1  
        if intelligence.height_limit:
            score += 1
        if intelligence.lot_size_req or intelligence.fsr_limit:
            score += 1
        if intelligence.heritage_items or len(intelligence.other_controls) > 0:
            score += 1
        
        if score >= 4:
            return "High"
        elif score >= 2:
            return "Medium"
        else:
            return "Low"

# Convenience function
async def get_property_dashboard(address: str, google_coords: Optional[Dict[str, float]] = None) -> PropertyDashboard:
    """Get property dashboard for address with optional Google coordinates"""
    return await PropertyIntelligenceService.get_property_dashboard(address, google_coords)

# Test function
async def test_property_intelligence():
    """Test property intelligence service"""
    test_address = "45 Liverpool Street, Ashfield NSW 2131"
    print(f"Testing Property Intelligence: {test_address}")
    
    dashboard = await get_property_dashboard(test_address)
    
    print(f"\nProperty Dashboard:")
    print(f"  Address: {dashboard.address}")
    print(f"  PropID: {dashboard.prop_id}")
    print(f"  Zone: {dashboard.zone} ({dashboard.zone_description})")
    print(f"  Height: {dashboard.height_limit} {dashboard.height_units} ({dashboard.height_clause})")
    print(f"  LEP: {dashboard.applicable_lep}")
    print(f"  LGA: {dashboard.lga_name}")
    
    print(f"\nQuick Metrics:")
    for metric in dashboard.quick_metrics:
        print(f"  {metric.status.value} {metric.name}: {metric.value}")
        if metric.details:
            print(f"    - {metric.details}")
    
    print(f"\nData Quality: {dashboard.data_quality}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_property_intelligence())