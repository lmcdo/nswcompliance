# PRP-B2: Connected Requirements Tree Visualization

## Status: PENDING
**Created:** 2025-08-30 
**Previous:** PRP-B1 Property Intelligence Engine 
**Next:** PRP-B3 Rule-to-Action Transformer

## Objective
Transform flat DCP provisions into an interactive connected requirements tree that shows how planning rules relate to each other for specific properties.

## Problem Statement
Current system shows isolated rules without connections:
- "Height limit 9.5m" + "Setback 1.5m" + "Solar access 3hr" (disconnected)
- "Height 9.5m → affects setbacks → affects neighbor solar access" (connected)

## Solution: Connected Requirements Tree

### Phase 1: Relationship Mapping Engine
**File:** `services/requirements_mapper.py`
```python
class RequirementsMapper:
 def __init__(self, property_data: PropertyIntelligence, dcp_provisions: List[PlanningRule]):
 self.property_data = property_data
 self.provisions = dcp_provisions
 
 def build_connection_tree(self) -> RequirementsTree:
 """Build hierarchical tree of connected planning requirements"""
 
 # Primary nodes (from NSW API)
 primary_nodes = {
 "HEIGHT_LIMIT": self._create_height_node(),
 "ZONE_REQUIREMENTS": self._create_zone_node(), 
 "HERITAGE_STATUS": self._create_heritage_node()
 }
 
 # Connect related provisions to primary nodes
 for node_key, node in primary_nodes.items():
 node.connected_provisions = self._find_connected_provisions(node_key)
 
 return RequirementsTree(primary_nodes)
 
 def _find_connected_provisions(self, primary_requirement: str) -> List[ConnectedProvision]:
 """Find DCP provisions that connect to primary requirements"""
 connections = []
 
 connection_patterns = {
 "HEIGHT_LIMIT": ["setback", "solar_access", "building_envelope", "heritage"],
 "ZONE_REQUIREMENTS": ["parking", "landscaping", "permitted_uses", "density"],
 "HERITAGE_STATUS": ["materials", "design", "additions", "tree_protection"]
 }
 
 target_types = connection_patterns.get(primary_requirement, [])
 
 for provision in self.provisions:
 if any(pattern in provision.type for pattern in target_types):
 connection = ConnectedProvision(
 title=provision.title,
 requirement=self._extract_actionable_requirement(provision),
 source=provision.source,
 connection_reason=self._explain_connection(primary_requirement, provision.type)
 )
 connections.append(connection)
 
 return connections[:5] # Limit to most relevant connections
```

### Phase 2: Interactive Tree Component
**File:** Frontend enhancement in `index.html`
```javascript
class ConnectedRequirementsTree {
 constructor(treeData) {
 this.treeData = treeData;
 this.expandedNodes = new Set();
 }
 
 render() {
 const container = document.getElementById('requirements-tree');
 container.innerHTML = this.renderTree();
 this.attachEventListeners();
 }
 
 renderTree() {
 return `
 <div class="requirements-tree">
 <h4> YOUR REGULATORY REQUIREMENTS</h4>
 ${Object.entries(this.treeData.primary_nodes).map(([key, node]) => 
 this.renderPrimaryNode(key, node)
 ).join('')}
 </div>
 `;
 }
 
 renderPrimaryNode(key, node) {
 const isExpanded = this.expandedNodes.has(key);
 const icon = node.icon || '';
 const connectionCount = node.connected_provisions?.length || 0;
 
 return `
 <div class="primary-node ${isExpanded ? 'expanded' : ''}">
 <div class="node-header" data-node="${key}">
 <span class="expand-icon">${isExpanded ? '▼' : '▶'}</span>
 <span class="node-title">${icon} ${node.title}</span>
 <span class="connection-count">${connectionCount} connected</span>
 </div>
 
 ${isExpanded ? `
 <div class="connected-provisions">
 ${node.connected_provisions.map(provision => `
 <div class="connected-provision">
 <div class="connection-line">├──</div>
 <div class="provision-content">
 <div class="provision-type">${this.getProvisionIcon(provision.type)} ${provision.type}</div>
 <div class="provision-requirement">${provision.requirement}</div>
 <div class="provision-source">(${provision.source})</div>
 <div class="connection-reason">${provision.connection_reason}</div>
 </div>
 </div>
 `).join('')}
 </div>
 ` : ''}
 </div>
 `;
 }
 
 getProvisionIcon(type) {
 const icons = {
 'setback': '',
 'solar_access': '', 
 'parking': '',
 'landscaping': '',
 'heritage': '',
 'height_limit': '',
 'materials': ''
 };
 return icons[type] || '';
 }
 
 attachEventListeners() {
 document.querySelectorAll('.node-header').forEach(header => {
 header.addEventListener('click', (e) => {
 const nodeKey = e.currentTarget.dataset.node;
 this.toggleNode(nodeKey);
 });
 });
 }
 
 toggleNode(nodeKey) {
 if (this.expandedNodes.has(nodeKey)) {
 this.expandedNodes.delete(nodeKey);
 } else {
 this.expandedNodes.add(nodeKey);
 }
 this.render();
 }
}
```

### Phase 3: Smart Connection Logic
**File:** `services/connection_analyzer.py`
```python
class ConnectionAnalyzer:
 def analyze_requirement_connections(self, property_data, provisions):
 """Analyze how requirements connect for this specific property"""
 
 connections = []
 
 # Height → Setback connections
 if property_data.height_limit and any(p.type == "setback" for p in provisions):
 connections.append(Connection(
 from_requirement="height_limit",
 to_requirement="setback", 
 relationship="affects",
 explanation="Taller buildings need larger setbacks for privacy and solar access",
 property_specific=f"Your {property_data.height_limit} height allows {self._calculate_setback_requirement()} setbacks"
 ))
 
 # Zone → Parking connections 
 if property_data.zone and any(p.type == "parking" for p in provisions):
 connections.append(Connection(
 from_requirement="zone",
 to_requirement="parking",
 relationship="determines",
 explanation=f"{property_data.zone} zone requires specific parking rates",
 property_specific=self._get_zone_specific_parking(property_data.zone)
 ))
 
 return connections
 
 def _explain_property_impact(self, connection, property_data):
 """Explain how this connection affects the user's specific property"""
 
 explanations = {
 ("height_limit", "setback"): f"Your {property_data.height_limit} building can be closer to boundaries if single story, further if two story",
 ("zone", "parking"): f"R2 zone on your lot size requires {self._calculate_parking_spaces()} covered parking spaces",
 ("heritage", "materials"): "Pre-1940 property requires heritage-appropriate materials and colors"
 }
 
 key = (connection.from_requirement, connection.to_requirement)
 return explanations.get(key, "These requirements interact for your property type")
```

## Frontend Integration

### Enhanced Query Response Processing
```javascript
async function displayConnectedRequirements(queryResponse) {
 // Build requirements tree from query response
 const treeBuilder = new RequirementsTreeBuilder(queryResponse);
 const treeData = treeBuilder.buildTree();
 
 // Render interactive tree
 const tree = new ConnectedRequirementsTree(treeData);
 tree.render();
 
 // Add property-specific insights
 displayPropertySpecificInsights(treeData, window.currentPropertyIntelligence);
}

function displayPropertySpecificInsights(treeData, propertyData) {
 const insights = document.getElementById('property-insights');
 insights.innerHTML = `
 <div class="insights-section">
 <h4> HOW THIS AFFECTS YOUR PROPERTY</h4>
 ${generatePropertySpecificInsights(treeData, propertyData)}
 </div>
 `;
}
```

## API Enhancements

### Connected Requirements Endpoint
```python
@app.post("/connected-requirements")
async def get_connected_requirements(request: QueryRequest):
 # Get base query results
 query_response = await query_planning_rules(request)
 
 # Get property intelligence
 property_data = await get_property_dashboard(request.address)
 
 # Build connection tree
 mapper = RequirementsMapper(property_data, query_response['results'])
 tree = mapper.build_connection_tree()
 
 # Analyze connections
 analyzer = ConnectionAnalyzer()
 connections = analyzer.analyze_requirement_connections(property_data, query_response['results'])
 
 return ConnectedRequirementsResponse(
 tree=tree,
 connections=connections,
 property_context=property_data,
 total_requirements=len(query_response['results'])
 )
```

## Success Criteria
1. Display requirements as connected tree, not flat list
2. Show property-specific relationship explanations 
3. Interactive expand/collapse for requirement categories
4. Visual connection indicators (lines, icons, grouping)
5. Explain WHY requirements are connected for this property

## Test Cases
**Primary Test:** 34 Pile St, Dulwich Hill NSW 2203, height query
- Expected Tree Structure:
 ```
 HEIGHT LIMIT (9.5m) ▼
 ├── Setbacks → 1.5m sides (closer for single story)
 ├── Solar Access → 3hr minimum to neighbors 
 ├── Heritage → Must respect original roofline
 └── Tree Protection → Check existing tree heights
 ```

**Interaction Test:** Click HEIGHT LIMIT node → expands to show connected provisions with property-specific explanations

## Dependencies 
- Property intelligence from PRP-B1
- Parsed DCP provisions from existing query system
- Enhanced data models for tree structures
- Frontend JavaScript for interactive components

## Implementation Timeline
**Week 1:** Requirements mapping engine
**Week 2:** Interactive tree component 
**Week 3:** Connection analysis logic
**Week 4:** Property-specific insights integration

## Notes
This transforms the user experience from reading disconnected rules to understanding how regulations work together for their specific property.