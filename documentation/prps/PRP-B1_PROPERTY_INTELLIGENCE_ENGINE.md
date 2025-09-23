# PRP-B1: Property Intelligence Calculation Engine

## Status: PENDING
**Created:** 2025-08-30 
**Previous:** PRP-A9 LGA Filtering (COMPLETED) 
**Next:** PRP-B2 Connected Requirements Tree

## Objective
Transform raw NSW API data and DCP provisions into actionable property-specific intelligence that tells users what they can actually build on their specific lot.

## Problem Statement
Current system shows generic rule text instead of property-specific guidance:
- "Floor space ratio 0.6:1" (meaningless to users)
- "You can build 400m² on your 667m² lot" (actionable)

## Solution: Property Intelligence Engine

### Phase 1: Development Potential Calculator
**File:** `services/property_calculator.py`
```python
class DevelopmentPotential:
 def __init__(self, property_data: PropertyIntelligence, lot_area: float):
 self.property_data = property_data
 self.lot_area = lot_area
 
 def calculate_buildable_area(self) -> Dict[str, Any]:
 """Calculate actual buildable floor area from FSR"""
 fsr = float(self.property_data.floor_space_ratio or "0.6")
 buildable_sqm = self.lot_area * fsr
 
 return {
 "max_floor_area": buildable_sqm,
 "stories_possible": self._estimate_stories(),
 "development_type": self._get_permitted_uses(),
 "opportunities": self._identify_opportunities()
 }
 
 def _estimate_stories(self) -> int:
 """Estimate story count from height limit"""
 height_m = float(self.property_data.height_limit or "8.5")
 # Typical: 3m ground floor + 2.7m upper floors
 if height_m <= 4: return 1
 elif height_m <= 7: return 2 
 elif height_m <= 10: return 3
 else: return int(height_m / 3)
```

### Phase 2: Development Assessment Engine
**File:** `services/development_assessor.py`
```python
class DevelopmentAssessor:
 def assess_development_feasibility(self, property_data, development_type: str):
 """Assess what user can actually do with their property"""
 
 assessments = {
 "single_dwelling": self._assess_house(),
 "secondary_dwelling": self._assess_granny_flat(),
 "addition": self._assess_extension(),
 "swimming_pool": self._assess_pool(),
 "subdivision": self._assess_subdivision()
 }
 
 return {
 "feasible_developments": [k for k, v in assessments.items() if v["feasible"]],
 "constrained_developments": [k for k, v in assessments.items() if v["constrained"]],
 "impossible_developments": [k for k, v in assessments.items() if not v["feasible"]]
 }
```

### Phase 3: Smart Insights Generator
**File:** `services/smart_insights.py`
```python
class SmartInsights:
 def generate_property_insights(self, property_data: PropertyIntelligence) -> List[Insight]:
 """Generate property-specific insights and opportunities"""
 insights = []
 
 # Lot size opportunities
 if property_data.lot_area > 600:
 insights.append(Insight(
 type="opportunity",
 title="Large Lot Advantage",
 description="Your 667m² lot exceeds minimum 450m² - allows flexibility for extensions and pools",
 icon=""
 ))
 
 # Height opportunities
 height_remaining = self._calculate_height_opportunity()
 if height_remaining > 2:
 insights.append(Insight(
 type="opportunity", 
 title="Second Story Potential",
 description=f"You have {height_remaining}m height remaining - ideal for upper floor addition",
 icon=""
 ))
 
 return insights
```

## API Integration

### Enhanced Property Intelligence Endpoint
```python
@app.get("/property-intelligence-enhanced")
async def get_enhanced_property_intelligence(address: str):
 # Get base NSW API data
 base_data = await get_property_dashboard(address)
 
 # Calculate development potential
 calculator = DevelopmentPotential(base_data, lot_area=667) # From cadastral data
 potential = calculator.calculate_buildable_area()
 
 # Assess development feasibility
 assessor = DevelopmentAssessor()
 assessments = assessor.assess_development_feasibility(base_data, "residential")
 
 # Generate smart insights
 insights_engine = SmartInsights()
 insights = insights_engine.generate_property_insights(base_data)
 
 return EnhancedPropertyIntelligence(
 base_data=base_data,
 development_potential=potential,
 feasibility_assessment=assessments,
 smart_insights=insights
 )
```

## Frontend Integration

### Property Intelligence Dashboard Component
```javascript
async function displayPropertyIntelligence(propertyData) {
 const dashboard = document.getElementById('property-dashboard');
 
 dashboard.innerHTML = `
 <div class="property-header">
 <h3> ${propertyData.address}</h3>
 <div class="property-ids">Property ID: ${propertyData.prop_id} | LGA: ${propertyData.lga_name}</div>
 </div>
 
 <div class="development-potential">
 <h4> DEVELOPMENT POTENTIAL</h4>
 <div class="metrics">
 <div class="metric success">
 <span class="label">Max Height:</span>
 <span class="value">${propertyData.height_limit} (${propertyData.development_potential.stories_possible} stories)</span>
 </div>
 <div class="metric success">
 <span class="label">Buildable Area:</span>
 <span class="value">${propertyData.development_potential.max_floor_area}m² floor space</span>
 </div>
 </div>
 </div>
 
 <div class="development-options">
 <h4> WHAT YOU CAN DO</h4>
 ${propertyData.feasibility_assessment.feasible_developments.map(dev => 
 `<div class="option feasible"> ${formatDevelopmentType(dev)}</div>`
 ).join('')}
 </div>
 
 <div class="smart-insights">
 <h4> SMART INSIGHTS</h4>
 ${propertyData.smart_insights.map(insight => 
 `<div class="insight ${insight.type}">
 ${insight.icon} <strong>${insight.title}</strong>
 <p>${insight.description}</p>
 </div>`
 ).join('')}
 </div>
 `;
}
```

## Success Criteria
1. Calculate actual buildable area from FSR + lot size
2. Identify development opportunities (second story, granny flat, pool)
3. Generate property-specific insights based on lot characteristics
4. Transform generic rules into actionable guidance
5. Display "what you can do" instead of "what the rules say"

## Test Cases
**Primary Test:** 34 Pile St, Dulwich Hill NSW 2203
- Input: 667m² lot, R2 zone, 9.5m height, 0.6:1 FSR
- Expected Output: "400m² buildable, 2-story potential, single dwelling + granny flat feasible"

**Validation:** Users should understand their development options without reading DCP text

## Dependencies
- NSW Planning API property data ( working)
- LGA filtering system ( completed in PRP-A9)
- Enhanced property intelligence data structure
- Lot size/cadastral data integration

## Implementation Timeline
**Week 1:** Property calculator engine
**Week 2:** Development assessor logic 
**Week 3:** Smart insights generator
**Week 4:** Frontend integration and testing

## Notes
This PRP transforms the app from "document search" to "property advisor" - the key differentiator for user value.