# PRP-Q4: Legal Disclaimers & API Currency Monitoring

## OBJECTIVE
Implement comprehensive legal disclaimer framework with live NSW API currency monitoring, removing "authoritative" language and positioning system as "regulation reference tool" with real-time API health tracking.

## SUCCESS CRITERIA
- [ ] Remove all "authoritative" language from APIs and frontend
- [ ] Implement comprehensive legal disclaimer framework
- [ ] Add NSW API currency monitoring and health checks
- [ ] Create data freshness warnings with API timestamps
- [ ] Implement liability limitation with clear positioning
- [ ] Add professional consultation requirement notices
- [ ] Monitor API availability and data staleness

## TECHNICAL SPECIFICATION

### Phase Q4A: API Health Monitoring Framework
```python
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import asyncio
import aiohttp
import time
from enum import Enum
from datetime import datetime, timedelta

class APIHealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"

@dataclass
class APIHealthCheck:
    service_name: str
    endpoint_url: str
    status: APIHealthStatus
    response_time_ms: int
    last_successful_call: Optional[datetime]
    error_message: Optional[str]
    data_freshness_hours: Optional[int]

@dataclass
class LegalDisclaimer:
    disclaimer_type: str  # 'general', 'api_currency', 'professional_advice', 'liability'
    content: str
    severity: str  # 'info', 'warning', 'critical'
    required_display: bool
    applies_to_api_data: bool
    last_updated: datetime

@dataclass
class SystemHealthReport:
    overall_status: APIHealthStatus
    nsw_planning_api: APIHealthCheck
    valuation_api: APIHealthCheck
    database_status: str
    data_currency_warning: Optional[str]
    recommended_disclaimers: List[LegalDisclaimer]
    system_confidence: float  # 0.0 to 1.0
    last_health_check: datetime
```

### Phase Q4B: API Monitoring Service
```python
class NSWAPIMonitoringService:
    """Monitor NSW Planning API health and data currency"""

    def __init__(self):
        self.planning_api_base = "https://api.apps1.nsw.gov.au/planning"
        self.valuation_api_base = "https://maps.six.nsw.gov.au/arcgis/rest/services"
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            headers={
                'Origin': 'https://www.planningportal.nsw.gov.au',
                'Referer': 'https://www.planningportal.nsw.gov.au/'
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def check_system_health(self) -> SystemHealthReport:
        """Comprehensive system health check"""

        # Check NSW Planning API
        planning_health = await self._check_planning_api_health()

        # Check Valuation API
        valuation_health = await self._check_valuation_api_health()

        # Determine overall status
        if planning_health.status == APIHealthStatus.HEALTHY and valuation_health.status == APIHealthStatus.HEALTHY:
            overall_status = APIHealthStatus.HEALTHY
        elif planning_health.status == APIHealthStatus.UNAVAILABLE and valuation_health.status == APIHealthStatus.UNAVAILABLE:
            overall_status = APIHealthStatus.UNAVAILABLE
        else:
            overall_status = APIHealthStatus.DEGRADED

        # Calculate system confidence
        system_confidence = self._calculate_system_confidence(planning_health, valuation_health)

        # Generate appropriate disclaimers
        disclaimers = self._generate_contextual_disclaimers(overall_status, planning_health, valuation_health)

        # Check data currency
        data_currency_warning = self._assess_data_currency(planning_health, valuation_health)

        return SystemHealthReport(
            overall_status=overall_status,
            nsw_planning_api=planning_health,
            valuation_api=valuation_health,
            database_status="operational",  # Assume local DB is operational
            data_currency_warning=data_currency_warning,
            recommended_disclaimers=disclaimers,
            system_confidence=system_confidence,
            last_health_check=datetime.now()
        )

    async def _check_planning_api_health(self) -> APIHealthCheck:
        """Check NSW Planning API health"""

        start_time = time.time()
        test_url = f"{self.planning_api_base}/viewersf/V1/ePlanningApi/address"
        test_params = {"a": "1 Martin Place Sydney NSW", "noOfRecords": 1}

        try:
            async with self.session.get(test_url, params=test_params) as response:
                response_time = int((time.time() - start_time) * 1000)

                if response.status == 200:
                    data = await response.json()
                    if data and len(data) > 0:
                        return APIHealthCheck(
                            service_name="NSW Planning API",
                            endpoint_url=test_url,
                            status=APIHealthStatus.HEALTHY,
                            response_time_ms=response_time,
                            last_successful_call=datetime.now(),
                            error_message=None,
                            data_freshness_hours=0  # Live data
                        )

                return APIHealthCheck(
                    service_name="NSW Planning API",
                    endpoint_url=test_url,
                    status=APIHealthStatus.DEGRADED,
                    response_time_ms=response_time,
                    last_successful_call=None,
                    error_message=f"HTTP {response.status} - No valid data returned",
                    data_freshness_hours=None
                )

        except Exception as e:
            return APIHealthCheck(
                service_name="NSW Planning API",
                endpoint_url=test_url,
                status=APIHealthStatus.UNAVAILABLE,
                response_time_ms=int((time.time() - start_time) * 1000),
                last_successful_call=None,
                error_message=str(e),
                data_freshness_hours=None
            )

    async def _check_valuation_api_health(self) -> APIHealthCheck:
        """Check NSW Valuation API health"""

        start_time = time.time()
        test_url = f"{self.valuation_api_base}/public/Valuation/MapServer/5/query"
        test_params = {
            "where": "propid=1972074",  # Test property ID from user's example
            "outFields": "propid,address,prop_area,val1_lv",
            "f": "json"
        }

        try:
            async with self.session.get(test_url, params=test_params) as response:
                response_time = int((time.time() - start_time) * 1000)

                if response.status == 200:
                    response_text = await response.text()
                    try:
                        import json
                        data = json.loads(response_text)
                        if data and 'features' in data and data['features']:
                            return APIHealthCheck(
                                service_name="NSW Valuation API",
                                endpoint_url=test_url,
                                status=APIHealthStatus.HEALTHY,
                                response_time_ms=response_time,
                                last_successful_call=datetime.now(),
                                error_message=None,
                                data_freshness_hours=24  # Valuation data updated daily
                            )
                    except json.JSONDecodeError:
                        pass

                return APIHealthCheck(
                    service_name="NSW Valuation API",
                    endpoint_url=test_url,
                    status=APIHealthStatus.DEGRADED,
                    response_time_ms=response_time,
                    last_successful_call=None,
                    error_message=f"HTTP {response.status} - Invalid response format",
                    data_freshness_hours=None
                )

        except Exception as e:
            return APIHealthCheck(
                service_name="NSW Valuation API",
                endpoint_url=test_url,
                status=APIHealthStatus.UNAVAILABLE,
                response_time_ms=int((time.time() - start_time) * 1000),
                last_successful_call=None,
                error_message=str(e),
                data_freshness_hours=None
            )

    def _calculate_system_confidence(self,
                                   planning_health: APIHealthCheck,
                                   valuation_health: APIHealthCheck) -> float:
        """Calculate overall system confidence score"""

        base_confidence = 0.0

        # Planning API contribution (70% weight - primary data source)
        if planning_health.status == APIHealthStatus.HEALTHY:
            base_confidence += 0.7
        elif planning_health.status == APIHealthStatus.DEGRADED:
            base_confidence += 0.35

        # Valuation API contribution (30% weight - supplementary data)
        if valuation_health.status == APIHealthStatus.HEALTHY:
            base_confidence += 0.3
        elif valuation_health.status == APIHealthStatus.DEGRADED:
            base_confidence += 0.15

        return round(base_confidence, 2)

    def _generate_contextual_disclaimers(self,
                                       overall_status: APIHealthStatus,
                                       planning_health: APIHealthCheck,
                                       valuation_health: APIHealthCheck) -> List[LegalDisclaimer]:
        """Generate context-appropriate disclaimers"""

        disclaimers = [
            # Always present - core legal disclaimer
            LegalDisclaimer(
                disclaimer_type="general",
                content="This tool provides regulation reference only. It does not constitute professional planning advice or replace the need for qualified consultation.",
                severity="critical",
                required_display=True,
                applies_to_api_data=True,
                last_updated=datetime.now()
            ),

            # Professional advice requirement
            LegalDisclaimer(
                disclaimer_type="professional_advice",
                content="Professional planning advice from a qualified consultant is required for all development applications.",
                severity="warning",
                required_display=True,
                applies_to_api_data=False,
                last_updated=datetime.now()
            ),

            # Council authority
            LegalDisclaimer(
                disclaimer_type="liability",
                content="Only Council has authority to make binding development determinations. This tool provides guidance only.",
                severity="info",
                required_display=True,
                applies_to_api_data=False,
                last_updated=datetime.now()
            )
        ]

        # API-specific disclaimers based on health status
        if overall_status == APIHealthStatus.DEGRADED:
            disclaimers.append(LegalDisclaimer(
                disclaimer_type="api_currency",
                content="Planning data services are currently experiencing issues. Some information may be outdated or unavailable.",
                severity="warning",
                required_display=True,
                applies_to_api_data=True,
                last_updated=datetime.now()
            ))

        elif overall_status == APIHealthStatus.UNAVAILABLE:
            disclaimers.append(LegalDisclaimer(
                disclaimer_type="api_currency",
                content="Planning data services are currently unavailable. Information shown may be significantly outdated. Professional verification strongly recommended.",
                severity="critical",
                required_display=True,
                applies_to_api_data=True,
                last_updated=datetime.now()
            ))

        # Data freshness warnings
        if planning_health.data_freshness_hours and planning_health.data_freshness_hours > 24:
            disclaimers.append(LegalDisclaimer(
                disclaimer_type="api_currency",
                content=f"Planning data was last updated {planning_health.data_freshness_hours} hours ago. Check for recent amendments.",
                severity="info",
                required_display=True,
                applies_to_api_data=True,
                last_updated=datetime.now()
            ))

        return disclaimers

    def _assess_data_currency(self,
                            planning_health: APIHealthCheck,
                            valuation_health: APIHealthCheck) -> Optional[str]:
        """Assess overall data currency and generate warnings"""

        if planning_health.status == APIHealthStatus.UNAVAILABLE:
            return "CRITICAL: NSW Planning API unavailable - data may be significantly outdated"

        if valuation_health.status == APIHealthStatus.UNAVAILABLE:
            return "WARNING: Property valuation data unavailable - area information may be incomplete"

        if planning_health.status == APIHealthStatus.DEGRADED:
            return "CAUTION: Planning data service degraded - verify information with Council"

        # Check response times for performance warnings
        if planning_health.response_time_ms > 5000:  # 5 seconds
            return "INFO: Planning data service responding slowly - data is current but retrieval may be delayed"

        return None  # No currency issues
```

### Phase Q4C: Legal Disclaimer Integration
```python
class LegalDisclaimerManager:
    """Manage legal disclaimers across all API responses"""

    def __init__(self, monitoring_service: NSWAPIMonitoringService):
        self.monitoring_service = monitoring_service

    async def enhance_response_with_disclaimers(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add appropriate legal disclaimers to any API response"""

        # Get current system health
        health_report = await self.monitoring_service.check_system_health()

        # Add legal framework to response
        response_data['legal_framework'] = {
            'disclaimers': [
                {
                    'type': disclaimer.disclaimer_type,
                    'message': disclaimer.content,
                    'severity': disclaimer.severity,
                    'required': disclaimer.required_display,
                    'api_related': disclaimer.applies_to_api_data
                }
                for disclaimer in health_report.recommended_disclaimers
            ],
            'system_status': {
                'overall_health': health_report.overall_status.value,
                'system_confidence': health_report.system_confidence,
                'data_currency_warning': health_report.data_currency_warning,
                'last_health_check': health_report.last_health_check.isoformat()
            },
            'api_status': {
                'nsw_planning_api': {
                    'status': health_report.nsw_planning_api.status.value,
                    'response_time_ms': health_report.nsw_planning_api.response_time_ms,
                    'last_successful': health_report.nsw_planning_api.last_successful_call.isoformat() if health_report.nsw_planning_api.last_successful_call else None
                },
                'valuation_api': {
                    'status': health_report.valuation_api.status.value,
                    'response_time_ms': health_report.valuation_api.response_time_ms,
                    'data_freshness_hours': health_report.valuation_api.data_freshness_hours
                }
            },
            'professional_verification_required': True,
            'council_authority_acknowledgment': "Only Inner West Council has authority to make binding development determinations"
        }

        return response_data

    def remove_authoritative_language(self, text: str) -> str:
        """Remove authoritative language from text"""

        replacements = {
            'authoritative': 'reference',
            'definitive': 'indicative',
            'conclusive': 'preliminary',
            'binding': 'guidance-based',
            'determines': 'suggests',
            'confirms': 'indicates',
            'establishes': 'references',
            'official': 'reference',
            'certified': 'estimated'
        }

        result = text
        for old, new in replacements.items():
            result = result.replace(old, new)
            result = result.replace(old.capitalize(), new.capitalize())
            result = result.replace(old.upper(), new.upper())

        return result
```

## IMPLEMENTATION STEPS

### Step 1: Create API Monitoring Service (35 minutes)
### Step 2: Update All API Endpoints with Disclaimer Integration (40 minutes)
### Step 3: Create Legal Disclaimer Frontend Components (30 minutes)
### Step 4: Remove Authoritative Language Across System (15 minutes)

## VERIFICATION CHECKLIST

### Legal Positioning
- [ ] All "authoritative" language removed from APIs and frontend
- [ ] System positioned as "regulation reference tool" not compliance authority
- [ ] Clear professional consultation requirements displayed
- [ ] Council authority acknowledgment present in all responses

### API Health Monitoring
- [ ] NSW Planning API health monitoring implemented
- [ ] Valuation API health monitoring implemented
- [ ] System confidence scoring based on API availability
- [ ] Data currency warnings when APIs degraded/unavailable

### Disclaimer Framework
- [ ] Context-appropriate disclaimers based on API health
- [ ] Required disclaimer display on all user interfaces
- [ ] API response integration with legal framework
- [ ] Professional advice requirement notices

### System Integration
- [ ] All API endpoints include disclaimer framework
- [ ] Frontend components display disclaimers appropriately
- [ ] Health monitoring runs continuously in background
- [ ] Performance impact <50ms per request

## DELIVERABLES

1. **nsw_api_monitoring_service.py** - Comprehensive API health monitoring
2. **legal_disclaimer_manager.py** - Disclaimer framework and integration
3. **disclaimer_frontend_components.tsx** - React components for disclaimers
4. **language_update_script.py** - Remove authoritative language
5. **api_health_dashboard.tsx** - System health monitoring UI
6. **legal_compliance_verification.py** - Verification test suite

## ESTIMATED TIME
**2 hours total**
- API monitoring service: 35 minutes
- Disclaimer integration: 40 minutes
- Frontend components: 30 minutes
- Language updates: 15 minutes

## COMPLETION CRITERIA
✅ All "authoritative" language removed from system
✅ Comprehensive legal disclaimer framework with API monitoring
✅ Real-time NSW API health tracking and currency warnings
✅ Professional advice requirements clearly communicated
✅ System positioned as "regulation reference tool" only
✅ <50ms performance impact from legal framework