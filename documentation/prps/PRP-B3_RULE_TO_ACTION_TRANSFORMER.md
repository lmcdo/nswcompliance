# PRP-B3: Rule-to-Action Transformer

## Status: PENDING
**Created:** 2025-08-30 
**Previous:** PRP-B2 Connected Requirements Tree 
**Next:** PRP-B4 Development Roadmap Generator

## Objective
Transform legal DCP text into actionable, step-by-step guidance that tells property owners exactly what to do to comply with planning rules.

## Problem Statement
Current system shows legal text that users can't action:
- "Building height shall not exceed that shown on Height of Buildings Map as amended"
- "Measure your building from natural ground level. Maximum allowed: 9.5m. Check existing height with measuring tape."

## Solution: Rule-to-Action Transformer

### Phase 1: Action Extraction Engine
**File:** `services/action_transformer.py`
```python
class RuleToActionTransformer:
 def __init__(self):
 self.action_patterns = self._load_action_patterns()
 
 def transform_provision_to_actions(self, provision: PlanningRule, property_data: PropertyIntelligence) -> List[ActionStep]:
 """Convert DCP provision into actionable steps"""
 
 actions = []
 rule_type = provision.type
 
 if rule_type == "height_limit":
 actions = self._transform_height_rule(provision, property_data)
 elif rule_type == "setback":
 actions = self._transform_setback_rule(provision, property_data)
 elif rule_type == "parking":
 actions = self._transform_parking_rule(provision, property_data)
 elif rule_type == "heritage":
 actions = self._transform_heritage_rule(provision, property_data)
 else:
 actions = self._transform_generic_rule(provision, property_data)
 
 return actions
 
 def _transform_height_rule(self, provision: PlanningRule, property_data: PropertyIntelligence) -> List[ActionStep]:
 """Transform height provisions into measurable actions"""
 return [
 ActionStep(
 step_number=1,
 action="Measure existing building height",
 method="Use measuring tape from natural ground level to highest point",
 property_specific=f"Your limit: {property_data.height_limit}",
 tool_needed="Measuring tape",
 estimated_time="10 minutes",
 icon=""
 ),
 ActionStep(
 step_number=2, 
 action="Calculate available height for extension",
 method=f"Subtract existing height from {property_data.height_limit} maximum",
 property_specific=self._calculate_available_height(property_data),
 tool_needed="Calculator",
 estimated_time="5 minutes",
 icon=""
 ),
 ActionStep(
 step_number=3,
 action="Check height measurement point",
 method="Measure from natural ground, not retaining walls or fill",
 property_specific="Important for sloping sites like yours",
 tool_needed="Spirit level",
 estimated_time="15 minutes", 
 icon=""
 )
 ]
 
 def _transform_setback_rule(self, provision: PlanningRule, property_data: PropertyIntelligence) -> List[ActionStep]:
 """Transform setback provisions into measurement actions"""
 return [
 ActionStep(
 step_number=1,
 action="Identify all property boundaries", 
 method="Check survey plan or measure with certified surveyor",
 property_specific=f"Focus on {property_data.zone} zone requirements",
 tool_needed="Survey plan",
 estimated_time="30 minutes",
 icon=""
 ),
 ActionStep(
 step_number=2,
 action="Measure required setback distances",
 method="Front: 6m, Sides: 1.5m, Rear: 8m (typical R2)",
 property_specific=self._get_specific_setbacks(property_data),
 tool_needed="Measuring tape (50m)",
 estimated_time="45 minutes",
 icon=""
 ),
 ActionStep(
 step_number=3,
 action="Mark building envelope on site",
 method="Use spray paint or stakes to mark buildable area",
 property_specific="This shows your maximum building footprint",
 tool_needed="Spray paint, stakes",
 estimated_time="30 minutes",
 icon=""
 )
 ]
```

### Phase 2: Action Prioritization Engine
**File:** `services/action_prioritizer.py`
```python
class ActionPrioritizer:
 def prioritize_actions_by_development_intent(self, actions: List[ActionStep], development_type: str) -> List[PriorizedAction]:
 """Prioritize actions based on what user wants to build"""
 
 priorities = {
 "single_dwelling": ["site_analysis", "setbacks", "height", "parking"],
 "extension": ["heritage_check", "height", "setbacks", "solar_access"], 
 "swimming_pool": ["setbacks", "utilities", "access", "drainage"],
 "secondary_dwelling": ["setbacks", "parking", "utilities", "separate_access"]
 }
 
 priority_order = priorities.get(development_type, ["site_analysis", "setbacks", "height"])
 
 prioritized = []
 for priority_type in priority_order:
 matching_actions = [a for a in actions if priority_type in a.category.lower()]
 prioritized.extend(matching_actions)
 
 return prioritized
 
 def group_actions_by_phase(self, actions: List[ActionStep]) -> Dict[str, List[ActionStep]]:
 """Group actions into logical phases"""
 phases = {
 "SITE ANALYSIS": [],
 "DESIGN COMPLIANCE": [], 
 "DEVELOPMENT APPLICATION": [],
 "CONSTRUCTION PREPARATION": []
 }
 
 phase_mapping = {
 "measure": "SITE ANALYSIS",
 "check": "SITE ANALYSIS", 
 "calculate": "DESIGN COMPLIANCE",
 "design": "DESIGN COMPLIANCE",
 "submit": "DEVELOPMENT APPLICATION",
 "apply": "DEVELOPMENT APPLICATION",
 "prepare": "CONSTRUCTION PREPARATION"
 }
 
 for action in actions:
 phase = self._determine_action_phase(action, phase_mapping)
 phases[phase].append(action)
 
 return phases
```

### Phase 3: Interactive Action Interface
**File:** Frontend enhancement in `index.html`
```javascript
class ActionableGuidance {
 constructor(actions, propertyData) {
 this.actions = actions;
 this.propertyData = propertyData;
 this.completedActions = new Set();
 }
 
 render() {
 const container = document.getElementById('actionable-guidance');
 container.innerHTML = this.renderActionPhases();
 this.attachActionListeners();
 }
 
 renderActionPhases() {
 return `
 <div class="actionable-guidance">
 <h4> YOUR DEVELOPMENT ROADMAP</h4>
 ${Object.entries(this.actions.phases).map(([phase, actions]) => 
 this.renderPhase(phase, actions)
 ).join('')}
 </div>
 `;
 }
 
 renderPhase(phaseName, actions) {
 const completedCount = actions.filter(a => this.completedActions.has(a.id)).length;
 const progressPercent = (completedCount / actions.length) * 100;
 
 return `
 <div class="action-phase">
 <div class="phase-header">
 <h5>${this.getPhaseIcon(phaseName)} ${phaseName}</h5>
 <div class="phase-progress">
 <div class="progress-bar">
 <div class="progress-fill" style="width: ${progressPercent}%"></div>
 </div>
 <span class="progress-text">${completedCount}/${actions.length} complete</span>
 </div>
 </div>
 
 <div class="action-steps">
 ${actions.map((action, index) => this.renderActionStep(action, index)).join('')}
 </div>
 </div>
 `;
 }
 
 renderActionStep(action, index) {
 const isCompleted = this.completedActions.has(action.id);
 const isNext = !isCompleted && index === this.getNextActionIndex();
 
 return `
 <div class="action-step ${isCompleted ? 'completed' : ''} ${isNext ? 'next' : ''}">
 <div class="step-header">
 <input type="checkbox" ${isCompleted ? 'checked' : ''} 
 data-action-id="${action.id}" class="step-checkbox">
 <span class="step-icon">${action.icon}</span>
 <span class="step-title">${action.action}</span>
 <span class="step-time">${action.estimated_time}</span>
 </div>
 
 <div class="step-details">
 <div class="step-method">
 <strong>How:</strong> ${action.method}
 </div>
 <div class="step-property-specific">
 <strong>For your property:</strong> ${action.property_specific}
 </div>
 <div class="step-tools">
 <strong>Tools needed:</strong> ${action.tool_needed}
 </div>
 ${action.external_links ? `
 <div class="step-links">
 ${action.external_links.map(link => 
 `<a href="${link.url}" target="_blank">${link.title}</a>`
 ).join(' | ')}
 </div>
 ` : ''}
 </div>
 </div>
 `;
 }
 
 attachActionListeners() {
 document.querySelectorAll('.step-checkbox').forEach(checkbox => {
 checkbox.addEventListener('change', (e) => {
 const actionId = e.target.dataset.actionId;
 if (e.target.checked) {
 this.completedActions.add(actionId);
 } else {
 this.completedActions.delete(actionId);
 }
 this.render(); // Re-render to update progress
 });
 });
 }
 
 getNextActionIndex() {
 // Find first uncompleted action
 return this.actions.findIndex(action => !this.completedActions.has(action.id));
 }
}
```

## API Integration

### Action Transformation Endpoint
```python
@app.post("/actionable-guidance")
async def get_actionable_guidance(request: ActionGuidanceRequest):
 # Get query results and property data
 query_response = await query_planning_rules(request.query_request)
 property_data = await get_property_dashboard(request.query_request.address)
 
 # Transform provisions to actions
 transformer = RuleToActionTransformer()
 all_actions = []
 
 for provision in query_response['results']:
 actions = transformer.transform_provision_to_actions(provision, property_data)
 all_actions.extend(actions)
 
 # Prioritize and group actions
 prioritizer = ActionPrioritizer()
 prioritized_actions = prioritizer.prioritize_actions_by_development_intent(
 all_actions, 
 request.development_type
 )
 grouped_actions = prioritizer.group_actions_by_phase(prioritized_actions)
 
 return ActionableGuidanceResponse(
 phases=grouped_actions,
 total_actions=len(all_actions),
 estimated_total_time=sum(action.estimated_time_minutes for action in all_actions),
 development_type=request.development_type,
 property_context=property_data
 )

class ActionGuidanceRequest(BaseModel):
 query_request: QueryRequest
 development_type: str # "single_dwelling", "extension", "swimming_pool", etc.
 user_skill_level: Optional[str] = "beginner" # Affects action complexity
```

## Success Criteria
1. Convert legal text into step-by-step actions
2. Provide specific measurements and tools needed
3. Group actions into logical phases (site analysis → design → application)
4. Show property-specific guidance, not generic instructions
5. Enable progress tracking with checkboxes
6. Estimate time required for each action

## Test Cases
**Primary Test:** Height limit provision for 34 Pile St, Dulwich Hill
- Input: "Building height shall not exceed 9.5 metres" 
- Expected Output:
 ```
 STEP 1: Measure existing building height (10 min)
 How: Use measuring tape from natural ground to highest point
 For your property: Your limit is 9.5m, measure from street level
 Tools needed: 50m measuring tape
 
 STEP 2: Calculate available height (5 min)
 How: Subtract existing height from 9.5m maximum
 For your property: Single story = ~6m remaining for extension
 Tools needed: Calculator
 ```

**Integration Test:** User checks off completed actions → progress bar updates → next action highlighted

## Dependencies
- Property intelligence from PRP-B1
- Connected requirements from PRP-B2 
- Enhanced provision parsing with rule types
- Frontend progress tracking components

## Implementation Timeline 
**Week 1:** Action transformation engine
**Week 2:** Action prioritization and grouping
**Week 3:** Interactive frontend components
**Week 4:** Progress tracking and external integrations

## Notes
This PRP transforms the app from "information provider" to "action guide" - directly helping users accomplish their development goals step-by-step.