# PRP-B5: Development Application Assistant

## Status: PENDING
**Created:** 2025-08-30 
**Previous:** PRP-B4 Smart Relevance Engine 
**Next:** PRP-B6 Professional Services Integration

## Objective
Generate property-specific Development Application checklists and requirements based on NSW API data and DCP provisions, helping users understand exactly what they need to submit for their specific development.

## Problem Statement
Users know what they want to build but don't know what documentation is required:
- Generic "submit architectural plans" (too vague)
- User guesses what forms and reports are needed
- "Your R2 lot requires: Site Survey, Heritage Assessment, Parking Plan, Tree Report" (specific to property)

## Solution: Development Application Assistant

### Phase 1: DA Requirements Engine
**File:** `services/da_requirements_engine.py`
```python
class DARequirementsEngine:
 def __init__(self):
 self.requirement_rules = self._load_da_requirement_rules()
 
 def generate_da_requirements(self, 
 property_data: PropertyIntelligence,
 development_type: str,
 relevant_provisions: List[PlanningRule]) -> DARequirements:
 """Generate comprehensive DA requirements for specific property and development"""
 
 base_requirements = self._get_base_requirements(development_type)
 property_specific = self._get_property_specific_requirements(property_data)
 provision_triggered = self._get_provision_triggered_requirements(relevant_provisions)
 
 all_requirements = base_requirements + property_specific + provision_triggered
 
 return DARequirements(
 mandatory_documents=self._categorize_by_type(all_requirements, "mandatory"),
 conditional_documents=self._categorize_by_type(all_requirements, "conditional"),
 forms_required=self._get_required_forms(development_type, property_data),
 fees_estimate=self._calculate_fees(development_type, property_data),
 processing_time=self._estimate_processing_time(development_type, property_data),
 submission_pathway=self._determine_submission_pathway(development_type, property_data)
 )
 
 def _get_property_specific_requirements(self, property_data: PropertyIntelligence) -> List[DARequirement]:
 """Generate requirements based on property characteristics"""
 requirements = []
 
 # Heritage requirements
 if property_data.heritage_status and "heritage" in property_data.heritage_status.lower():
 requirements.append(DARequirement(
 document="Heritage Impact Assessment",
 reason=f"Property has heritage status: {property_data.heritage_status}",
 mandatory=True,
 estimated_cost="$2,500 - $5,000",
 professional_required="Heritage Consultant",
 typical_timeframe="3-4 weeks"
 ))
 
 # Large lot requirements
 if property_data.lot_area and property_data.lot_area > 1000:
 requirements.append(DARequirement(
 document="Detailed Site Survey",
 reason="Large lot (>1000m²) requires comprehensive survey",
 mandatory=True,
 estimated_cost="$1,500 - $2,500",
 professional_required="Licensed Surveyor",
 typical_timeframe="1-2 weeks"
 ))
 
 # Flood-prone area requirements 
 if self._is_flood_prone(property_data):
 requirements.append(DARequirement(
 document="Flood Risk Assessment", 
 reason="Property in flood-affected area",
 mandatory=True,
 estimated_cost="$3,000 - $6,000",
 professional_required="Hydraulic Engineer",
 typical_timeframe="2-3 weeks"
 ))
 
 # Zone-specific requirements
 if property_data.zone == "R2":
 requirements.append(DARequirement(
 document="Parking and Access Plan",
 reason="R2 zone requires detailed parking provision",
 mandatory=True,
 estimated_cost="Included in architectural plans",
 professional_required="Architect/Designer",
 typical_timeframe="1 week"
 ))
 
 return requirements
 
 def _get_provision_triggered_requirements(self, provisions: List[PlanningRule]) -> List[DARequirement]:
 """Generate requirements triggered by specific DCP provisions"""
 requirements = []
 
 for provision in provisions:
 if provision.type == "heritage" and "assessment" in provision.text.lower():
 requirements.append(DARequirement(
 document="Heritage Design Response",
 reason=f"Required by {provision.source} - {provision.citation_clause}",
 mandatory=True,
 dcp_reference=provision.citation_clause
 ))
 
 elif provision.type == "environmental_protection" and "tree" in provision.text.lower():
 requirements.append(DARequirement(
 document="Arborist Report and Tree Protection Plan", 
 reason=f"Required by {provision.source} for tree protection",
 mandatory=True,
 estimated_cost="$800 - $1,500",
 professional_required="Qualified Arborist"
 ))
 
 elif provision.type == "stormwater" or "stormwater" in provision.text.lower():
 requirements.append(DARequirement(
 document="Stormwater Management Plan",
 reason=f"Required by {provision.source} for drainage compliance",
 mandatory=True,
 estimated_cost="$1,200 - $2,000", 
 professional_required="Civil Engineer"
 ))
 
 return requirements
```

### Phase 2: DA Checklist Generator
**File:** `services/da_checklist_generator.py`
```python
class DAChecklistGenerator:
 def generate_submission_checklist(self, 
 da_requirements: DARequirements,
 property_data: PropertyIntelligence) -> SubmissionChecklist:
 """Generate step-by-step DA submission checklist"""
 
 checklist_phases = {
 "PREPARATION": self._generate_preparation_checklist(da_requirements),
 "PROFESSIONAL_ENGAGEMENT": self._generate_professional_checklist(da_requirements),
 "DOCUMENT_COMPILATION": self._generate_document_checklist(da_requirements),
 "SUBMISSION": self._generate_submission_checklist(da_requirements, property_data)
 }
 
 return SubmissionChecklist(
 phases=checklist_phases,
 total_estimated_cost=self._calculate_total_cost(da_requirements),
 total_timeframe=self._calculate_total_timeframe(da_requirements),
 critical_path_items=self._identify_critical_path(da_requirements)
 )
 
 def _generate_preparation_checklist(self, da_requirements: DARequirements) -> List[ChecklistItem]:
 """Generate preparation phase checklist"""
 return [
 ChecklistItem(
 task="Confirm development scope and budget",
 description="Clearly define what you want to build before engaging professionals",
 estimated_time="1-2 days",
 priority="HIGH",
 dependencies=[]
 ),
 ChecklistItem(
 task="Obtain accurate site survey",
 description="Essential foundation for all other documentation",
 estimated_time="1-2 weeks",
 estimated_cost="$1,500 - $2,500",
 priority="HIGH",
 professional_required="Licensed Surveyor"
 ),
 ChecklistItem(
 task="Collect existing property documents",
 description="Previous DA approvals, building certificates, survey plans",
 estimated_time="3-5 days",
 priority="MEDIUM"
 )
 ]
 
 def _generate_professional_checklist(self, da_requirements: DARequirements) -> List[ChecklistItem]:
 """Generate professional engagement checklist"""
 professional_requirements = {}
 
 for req in da_requirements.mandatory_documents + da_requirements.conditional_documents:
 if req.professional_required:
 if req.professional_required not in professional_requirements:
 professional_requirements[req.professional_required] = []
 professional_requirements[req.professional_required].append(req.document)
 
 checklist_items = []
 for professional, documents in professional_requirements.items():
 checklist_items.append(ChecklistItem(
 task=f"Engage {professional}",
 description=f"Required for: {', '.join(documents)}",
 estimated_time="1-3 days (to find and engage)",
 priority="HIGH",
 action_required="Get quotes from 2-3 professionals"
 ))
 
 return checklist_items
```

### Phase 3: Cost and Timeline Calculator
**File:** `services/da_cost_calculator.py`
```python
class DACostCalculator:
 def __init__(self):
 self.cost_database = self._load_cost_database()
 self.council_fees = self._load_council_fees()
 
 def calculate_comprehensive_costs(self, 
 da_requirements: DARequirements,
 property_data: PropertyIntelligence,
 development_value: Optional[float] = None) -> CostBreakdown:
 """Calculate all costs associated with DA submission"""
 
 # Professional fees
 professional_costs = self._calculate_professional_costs(da_requirements)
 
 # Council fees
 council_costs = self._calculate_council_fees(
 da_requirements.submission_pathway,
 property_data,
 development_value
 )
 
 # Document preparation costs
 document_costs = self._calculate_document_costs(da_requirements)
 
 # Contingency and miscellaneous
 subtotal = sum([professional_costs.total, council_costs.total, document_costs.total])
 contingency = subtotal * 0.15 # 15% contingency
 
 return CostBreakdown(
 professional_fees=professional_costs,
 council_fees=council_costs,
 document_preparation=document_costs,
 contingency=contingency,
 total_estimated=subtotal + contingency,
 cost_range=self._provide_cost_range(subtotal + contingency)
 )
 
 def _calculate_council_fees(self, submission_pathway: str, 
 property_data: PropertyIntelligence,
 development_value: Optional[float]) -> CouncilFees:
 """Calculate council-specific DA fees"""
 
 # Base DA fee (varies by council)
 council_base_fees = {
 "INNER WEST": {
 "single_dwelling": 1520,
 "extension": 760,
 "swimming_pool": 380,
 "secondary_dwelling": 1140
 }
 }
 
 base_fee = council_base_fees.get(property_data.lga_name, {}).get(submission_pathway, 1000)
 
 # Additional fees based on development value
 additional_fees = 0
 if development_value and development_value > 100000:
 additional_fees = (development_value - 100000) * 0.0065 # 0.65% of value over $100k
 
 return CouncilFees(
 base_fee=base_fee,
 value_based_fee=additional_fees,
 other_fees=self._calculate_other_council_fees(property_data),
 total=base_fee + additional_fees
 )
```

## API Integration

### DA Requirements Endpoint
```python
@app.post("/da-requirements")
async def get_da_requirements(request: DARequirementsRequest):
 # Get property intelligence and relevant provisions
 property_data = await get_property_dashboard(request.address)
 
 # Get relevant planning provisions for this development
 query_request = QueryRequest(
 address=request.address,
 query_type="general",
 lga_name=property_data.lga_name
 )
 provisions_response = await query_with_smart_relevance(query_request)
 
 # Generate DA requirements
 requirements_engine = DARequirementsEngine()
 da_requirements = requirements_engine.generate_da_requirements(
 property_data,
 request.development_type,
 provisions_response.filtered_results.provisions
 )
 
 # Generate submission checklist
 checklist_generator = DAChecklistGenerator()
 checklist = checklist_generator.generate_submission_checklist(da_requirements, property_data)
 
 # Calculate costs
 cost_calculator = DACostCalculator()
 cost_breakdown = cost_calculator.calculate_comprehensive_costs(
 da_requirements,
 property_data,
 request.estimated_development_value
 )
 
 return DARequirementsResponse(
 property_context=property_data,
 development_type=request.development_type,
 requirements=da_requirements,
 submission_checklist=checklist,
 cost_breakdown=cost_breakdown,
 next_steps=generate_next_steps(da_requirements, property_data)
 )

class DARequirementsRequest(BaseModel):
 address: str
 development_type: str # "single_dwelling", "extension", "swimming_pool"
 estimated_development_value: Optional[float] = None
 timeline_preference: Optional[str] = "standard" # "urgent", "standard", "flexible"
```

## Frontend Integration

### DA Assistant Interface
```javascript
class DAAssistant {
 constructor() {
 this.requirements = null;
 this.completedItems = new Set();
 }
 
 async generateDAGuidance(address, developmentType, developmentValue) {
 const response = await fetch('/da-requirements', {
 method: 'POST',
 headers: {'Content-Type': 'application/json'},
 body: JSON.stringify({
 address: address,
 development_type: developmentType,
 estimated_development_value: developmentValue
 })
 });
 
 this.requirements = await response.json();
 this.renderDAGuidance();
 }
 
 renderDAGuidance() {
 const container = document.getElementById('da-assistant');
 
 container.innerHTML = `
 <div class="da-assistant">
 <h3> DEVELOPMENT APPLICATION GUIDE</h3>
 <div class="da-summary">
 <div class="cost-summary">
 <strong>Total Estimated Cost:</strong> $${this.requirements.cost_breakdown.total_estimated.toLocaleString()}
 <span class="cost-range">(${this.requirements.cost_breakdown.cost_range})</span>
 </div>
 <div class="timeline-summary">
 <strong>Expected Timeline:</strong> ${this.requirements.submission_checklist.total_timeframe}
 </div>
 <div class="pathway-summary">
 <strong>Submission Type:</strong> ${this.requirements.requirements.submission_pathway}
 </div>
 </div>
 
 ${this.renderRequiredDocuments()}
 ${this.renderSubmissionChecklist()}
 ${this.renderCostBreakdown()}
 ${this.renderNextSteps()}
 </div>
 `;
 }
 
 renderRequiredDocuments() {
 const mandatory = this.requirements.requirements.mandatory_documents;
 const conditional = this.requirements.requirements.conditional_documents;
 
 return `
 <div class="required-documents">
 <h4> REQUIRED DOCUMENTS</h4>
 
 <div class="mandatory-docs">
 <h5> Mandatory Documents</h5>
 ${mandatory.map(doc => `
 <div class="document-requirement mandatory">
 <div class="doc-header">
 <span class="doc-name">${doc.document}</span>
 <span class="doc-cost">${doc.estimated_cost || 'Variable'}</span>
 </div>
 <div class="doc-reason">${doc.reason}</div>
 <div class="doc-professional">
 Professional needed: ${doc.professional_required || 'None'}
 </div>
 <div class="doc-timeframe">Timeline: ${doc.typical_timeframe || 'Variable'}</div>
 </div>
 `).join('')}
 </div>
 
 ${conditional.length > 0 ? `
 <div class="conditional-docs">
 <h5> May Be Required</h5>
 ${conditional.map(doc => `
 <div class="document-requirement conditional">
 <div class="doc-name">${doc.document}</div>
 <div class="doc-reason">${doc.reason}</div>
 </div>
 `).join('')}
 </div>
 ` : ''}
 </div>
 `;
 }
}
```

## Success Criteria
1. Generate property-specific DA requirements, not generic lists
2. Provide accurate cost estimates for all required documentation 
3. Create step-by-step submission checklist with timelines
4. Identify required professionals (heritage consultant, surveyor, etc.)
5. Calculate council fees based on development value and LGA
6. Show critical path items that could delay submission

## Test Cases
**Primary Test:** Single dwelling house - 34 Pile St, Dulwich Hill (R2, Inner West)
- Expected Requirements: Site Survey, Architectural Plans, Parking Plan, BASIX Certificate
- Expected Cost: $8,000 - $15,000 (professional fees + council fees)
- Expected Timeline: 6-10 weeks preparation + 4-8 weeks council processing

**Heritage Test:** Pre-1940 property in heritage area
- Additional Requirements: Heritage Impact Assessment, Heritage Design Response
- Additional Cost: +$4,000 - $8,000
- Additional Timeline: +3-4 weeks

## Dependencies
- Property intelligence from PRP-B1
- Smart relevance engine from PRP-B4
- Council fees database (updated annually)
- Professional services cost database

## Implementation Timeline
**Week 1:** DA requirements engine
**Week 2:** Checklist generator and cost calculator 
**Week 3:** Frontend DA assistant interface
**Week 4:** Integration testing and cost database updates

## Notes
This PRP transforms the app from "what are the rules" to "what do I need to submit" - directly helping users navigate the DA process for their specific property and development.