# PRP-B6: Setback Calculation Engine with Regulatory Citations

## Status: PENDING
**Created:** 2025-08-30  
**Previous:** PRP-B5 Development Application Assistant  
**Next:** PRP-B7 Interactive Building Envelope Calculator

## Objective
Implement property-specific setback calculations that show exact distances, measurement methods, governing regulations, and visual guidance - transforming generic "setback requirements" into actionable "your building can be X metres from the boundary."

## Problem Statement
Current system shows generic setback text without calculations:
- ❌ "Side setbacks shall be in accordance with DCP requirements" (useless)
- ❌ "Refer to Section 2.3 for setback provisions" (forces user to read documents)  
- ✅ "Side setback: 1.9m (0.9m base + 1.0m height bonus for 9.5m building) - DCP 2.3.1" (actionable)

## Solution: Property-Specific Setback Calculator

### Phase 1: Setback Calculation Engine
**File:** `services/setback_calculator.py`
```python
from typing import Dict, List, Optional
from dataclasses import dataclass
import math

@dataclass
class SetbackRequirement:
    """Individual setback requirement with full regulatory context"""
    setback_type: str  # "front", "side", "rear", "street", "lane"
    calculated_distance: float  # Actual distance in metres for this property
    base_requirement: float  # Base setback before height adjustments
    height_adjustment: float  # Additional setback due to building height
    measurement_from: str  # "boundary_line", "building_line", "kerb"
    measurement_to: str  # "external_wall", "eaves", "balcony"
    
    # Regulatory Citations
    source_document: str  # "Marrickville DCP 2011"
    source_clause: str  # "Section 2.3.1 - Side Setbacks"  
    source_page: Optional[int]  # Page number for reference
    regulation_text: str  # Exact regulatory text
    
    # Calculation Details
    calculation_formula: str  # "0.9 + (height - 7.5) * 0.5"
    calculation_explanation: str  # Human-readable calculation steps
    zone_specific: bool  # Whether this varies by zone
    
    # Property Context
    applicable_zones: List[str]  # ["R2", "R3"] 
    heritage_variations: Optional[str]  # Special heritage requirements
    corner_lot_variations: Optional[str]  # Special corner lot rules
    
    # Validation
    confidence: float  # 0.0-1.0 calculation confidence
    validation_notes: List[str]  # Warnings, assumptions, etc.

@dataclass  
class PropertySetbacks:
    """Complete setback analysis for specific property"""
    address: str
    lot_dimensions: Dict[str, float]  # {"width": 12.5, "depth": 35.0}
    zone: str
    height_limit: float
    
    # Calculated Setbacks
    front_setback: SetbackRequirement
    side_setbacks: List[SetbackRequirement]  # Left and right sides
    rear_setback: SetbackRequirement
    street_setbacks: List[SetbackRequirement]  # If corner lot
    
    # Building Envelope Results
    buildable_envelope: Dict[str, float]  # Calculated buildable dimensions
    total_setback_area: float  # Total area lost to setbacks
    buildable_footprint: float  # Maximum building footprint
    
    # Regulatory Summary
    governing_documents: List[str]  # All documents used in calculations
    key_regulatory_citations: List[str]  # Most important clauses
    calculation_timestamp: str
    
class SetbackCalculationEngine:
    """Calculate property-specific setbacks using 4-stack intelligence"""
    
    def __init__(self):
        self.standard_setbacks = self._load_standard_setback_rules()
        self.height_adjustment_rules = self._load_height_adjustment_rules()
    
    async def calculate_property_setbacks(self, property_context: PropertyContext) -> PropertySetbacks:
        """Calculate all setbacks for specific property with full regulatory citations"""
        
        # Step 1: Get base setback requirements from LightRAG
        base_requirements = await self._get_lightrag_setback_requirements(property_context)
        
        # Step 2: Get connected requirements from AutoSchemaKG  
        height_relationships = await self._get_height_setback_relationships(property_context)
        
        # Step 3: Apply property-specific calculations
        calculated_setbacks = self._apply_setback_calculations(
            base_requirements, height_relationships, property_context
        )
        
        # Step 4: Validate against known rules and NSW API data
        validated_setbacks = self._validate_setback_calculations(calculated_setbacks, property_context)
        
        # Step 5: Generate building envelope
        building_envelope = self._calculate_building_envelope(validated_setbacks, property_context)
        
        return PropertySetbacks(
            address=property_context.address,
            lot_dimensions=self._estimate_lot_dimensions(property_context),
            zone=property_context.zone,
            height_limit=float(property_context.height_limit.replace("m", "")),
            front_setback=validated_setbacks["front"],
            side_setbacks=validated_setbacks["sides"],
            rear_setback=validated_setbacks["rear"],
            buildable_envelope=building_envelope,
            governing_documents=self._extract_governing_documents(base_requirements),
            key_regulatory_citations=self._extract_key_citations(base_requirements)
        )
    
    async def _get_lightrag_setback_requirements(self, property_context: PropertyContext) -> Dict:
        """Query LightRAG for property-specific setback requirements"""
        from scripts.validated_nsw_query import query_validated_processor
        
        # Property-specific setback queries
        queries = [
            f"side setbacks {property_context.zone} {property_context.lga_name}",
            f"front setbacks {property_context.zone} {property_context.lga_name}",
            f"rear setbacks {property_context.zone} {property_context.lga_name}",
            f"height setback relationship {property_context.zone}"
        ]
        
        lightrag_results = {}
        for query in queries:
            result = query_validated_processor(query)
            if result and "ERROR" not in result:
                setback_type = query.split()[0]  # "side", "front", "rear", "height"
                lightrag_results[setback_type] = {
                    "query": query,
                    "response": result,
                    "source_documents": self._extract_source_documents(result),
                    "regulatory_citations": self._extract_citations(result)
                }
        
        return lightrag_results
    
    def _apply_setback_calculations(self, base_requirements: Dict, 
                                  height_relationships: List, 
                                  property_context: PropertyContext) -> Dict[str, SetbackRequirement]:
        """Apply mathematical calculations to base requirements"""
        
        building_height = float(property_context.height_limit.replace("m", ""))
        calculated_setbacks = {}
        
        # Front Setback Calculation
        if "front" in base_requirements:
            front_base = self._extract_numeric_value(base_requirements["front"]["response"], "front")
            calculated_setbacks["front"] = SetbackRequirement(
                setback_type="front",
                calculated_distance=front_base,  # Usually fixed
                base_requirement=front_base,
                height_adjustment=0.0,  # Front setbacks rarely vary by height
                measurement_from="street_boundary",
                measurement_to="building_facade",
                source_document=self._extract_source_doc(base_requirements["front"]),
                source_clause=self._extract_source_clause(base_requirements["front"]),
                regulation_text=self._extract_regulation_text(base_requirements["front"]),
                calculation_formula=f"{front_base}m (fixed)",
                calculation_explanation=f"Front setback is fixed at {front_base}m for {property_context.zone} zones",
                zone_specific=True,
                applicable_zones=[property_context.zone],
                confidence=0.95
            )
        
        # Side Setback Calculation (Height-Dependent)
        if "side" in base_requirements:
            side_base = self._extract_numeric_value(base_requirements["side"]["response"], "side")
            height_threshold = 7.5  # metres - common threshold for increased setbacks
            height_multiplier = 0.5  # Additional setback per metre above threshold
            
            height_adjustment = max(0, (building_height - height_threshold) * height_multiplier)
            total_side_setback = side_base + height_adjustment
            
            calculated_setbacks["sides"] = [SetbackRequirement(
                setback_type="side",
                calculated_distance=total_side_setback,
                base_requirement=side_base,
                height_adjustment=height_adjustment,
                measurement_from="side_boundary_line",
                measurement_to="external_building_wall",
                source_document=self._extract_source_doc(base_requirements["side"]),
                source_clause=self._extract_source_clause(base_requirements["side"]),
                regulation_text=self._extract_regulation_text(base_requirements["side"]),
                calculation_formula=f"{side_base} + max(0, ({building_height} - {height_threshold}) × {height_multiplier})",
                calculation_explanation=f"Side setback: {side_base}m base + {height_adjustment:.1f}m height adjustment = {total_side_setback:.1f}m total",
                zone_specific=True,
                applicable_zones=[property_context.zone],
                confidence=0.89,
                validation_notes=["Height adjustment applied for buildings over 7.5m"] if height_adjustment > 0 else []
            )]
        
        # Rear Setback Calculation
        if "rear" in base_requirements:
            rear_base = self._extract_numeric_value(base_requirements["rear"]["response"], "rear")
            # Rear setbacks often have alternative calculations (e.g., "6m OR 0.5 × building height")
            height_based_rear = building_height * 0.5
            calculated_rear = max(rear_base, height_based_rear)
            
            calculated_setbacks["rear"] = SetbackRequirement(
                setback_type="rear",
                calculated_distance=calculated_rear,
                base_requirement=rear_base,
                height_adjustment=max(0, height_based_rear - rear_base),
                measurement_from="rear_boundary_line",
                measurement_to="building_rear_wall",
                source_document=self._extract_source_doc(base_requirements["rear"]),
                source_clause=self._extract_source_clause(base_requirements["rear"]),
                regulation_text=self._extract_regulation_text(base_requirements["rear"]),
                calculation_formula=f"max({rear_base}m, {building_height}m × 0.5)",
                calculation_explanation=f"Rear setback: maximum of {rear_base}m base OR {height_based_rear:.1f}m (half building height) = {calculated_rear:.1f}m",
                zone_specific=True,
                applicable_zones=[property_context.zone],
                confidence=0.91
            )
        
        return calculated_setbacks
    
    def _calculate_building_envelope(self, setbacks: Dict, property_context: PropertyContext) -> Dict[str, float]:
        """Calculate buildable area from setbacks"""
        # Estimate lot dimensions (would be better to get from cadastral data)
        estimated_lot_width = 15.0  # metres - typical R2 lot
        estimated_lot_depth = 30.0  # metres - typical R2 lot
        
        # Calculate buildable dimensions
        buildable_width = estimated_lot_width - (setbacks["sides"][0].calculated_distance * 2)
        buildable_depth = estimated_lot_depth - setbacks["front"].calculated_distance - setbacks["rear"].calculated_distance
        buildable_footprint = buildable_width * buildable_depth
        
        return {
            "lot_width": estimated_lot_width,
            "lot_depth": estimated_lot_depth,
            "buildable_width": buildable_width,
            "buildable_depth": buildable_depth,
            "max_footprint": buildable_footprint,
            "setback_area_lost": (estimated_lot_width * estimated_lot_depth) - buildable_footprint
        }
```

### Phase 2: Regulatory Citation Engine
**File:** `services/regulatory_citations.py`
```python
class RegulatoryCitationEngine:
    """Extract and format regulatory citations from LightRAG responses"""
    
    def extract_citations_from_lightrag(self, lightrag_response: str) -> List[Dict]:
        """Extract structured citations from LightRAG text response"""
        citations = []
        
        # Parse document references
        document_patterns = [
            r"Document \d+: ([^-\n]+)",  # "Document 1: Inner West LEP 2022"
            r"Source: ([^-\n]+)",        # "Source: Marrickville DCP 2011"
            r"Reference: ([^-\n]+)"      # "Reference: Ashfield DCP 2016"
        ]
        
        for pattern in document_patterns:
            import re
            matches = re.findall(pattern, lightrag_response)
            for match in matches:
                doc_name = match.strip()
                
                # Extract clause/section references
                clause_patterns = [
                    rf"{re.escape(doc_name)}[^\n]*?([Cc]lause [\d\.]+[^\n]*)",
                    rf"{re.escape(doc_name)}[^\n]*?([Ss]ection [\d\.]+[^\n]*)",
                    rf"{re.escape(doc_name)}[^\n]*?(Part \d+[^\n]*)"
                ]
                
                clause_ref = None
                for clause_pattern in clause_patterns:
                    clause_matches = re.findall(clause_pattern, lightrag_response)
                    if clause_matches:
                        clause_ref = clause_matches[0].strip()
                        break
                
                # Extract the actual regulatory text
                regulation_text = self._extract_regulation_text(lightrag_response, doc_name)
                
                citations.append({
                    "document": doc_name,
                    "clause": clause_ref,
                    "text": regulation_text,
                    "confidence": 0.9 if clause_ref else 0.7
                })
        
        return citations
    
    def format_citation_for_display(self, citation: Dict) -> str:
        """Format citation for user-friendly display"""
        if citation["clause"]:
            return f"{citation['document']} - {citation['clause']}"
        else:
            return f"{citation['document']}"
    
    def create_regulation_tooltip(self, citation: Dict) -> str:
        """Create tooltip text showing full regulatory requirement"""
        tooltip = f"📋 {citation['document']}\n"
        if citation["clause"]:
            tooltip += f"📍 {citation['clause']}\n\n"
        tooltip += f"📖 {citation['text'][:200]}..."
        return tooltip
```

### Phase 3: Frontend Integration
**File:** Frontend enhancement in `index.html`
```javascript
class SetbackCalculationDisplay {
    constructor(setbackData) {
        this.setbacks = setbackData;
    }
    
    render() {
        const container = document.getElementById('setback-calculations');
        container.innerHTML = this.renderSetbackCalculations();
        this.attachCitationTooltips();
    }
    
    renderSetbackCalculations() {
        return `
            <div class="setback-calculations">
                <h4>📐 CALCULATED SETBACKS FOR YOUR PROPERTY</h4>
                <div class="calculation-summary">
                    <div class="envelope-summary">
                        <strong>Buildable Area:</strong> ${this.setbacks.buildable_envelope.buildable_width.toFixed(1)}m × ${this.setbacks.buildable_envelope.buildable_depth.toFixed(1)}m 
                        = ${this.setbacks.buildable_envelope.max_footprint.toFixed(0)}m² footprint
                    </div>
                </div>
                
                ${this.renderIndividualSetbacks()}
                ${this.renderBuildingEnvelope()}
                ${this.renderRegulatoryCitations()}
            </div>
        `;
    }
    
    renderIndividualSetbacks() {
        return `
            <div class="individual-setbacks">
                <h5>Setback Requirements</h5>
                
                <div class="setback-grid">
                    <div class="setback-item front">
                        <div class="setback-header">
                            <span class="direction-icon">🏠</span>
                            <span class="direction">Front Setback</span>
                            <span class="distance">${this.setbacks.front_setback.calculated_distance}m</span>
                        </div>
                        <div class="calculation-detail">
                            ${this.setbacks.front_setback.calculation_explanation}
                        </div>
                        <div class="regulatory-reference">
                            <span class="citation-link" data-citation="front">
                                📋 ${this.setbacks.front_setback.source_document} - ${this.setbacks.front_setback.source_clause}
                            </span>
                        </div>
                    </div>
                    
                    <div class="setback-item sides">
                        <div class="setback-header">
                            <span class="direction-icon">↔️</span>
                            <span class="direction">Side Setbacks</span>
                            <span class="distance">${this.setbacks.side_setbacks[0].calculated_distance.toFixed(1)}m each side</span>
                        </div>
                        <div class="calculation-detail">
                            ${this.setbacks.side_setbacks[0].calculation_explanation}
                        </div>
                        <div class="formula-display">
                            <code>${this.setbacks.side_setbacks[0].calculation_formula}</code>
                        </div>
                        <div class="regulatory-reference">
                            <span class="citation-link" data-citation="sides">
                                📋 ${this.setbacks.side_setbacks[0].source_document} - ${this.setbacks.side_setbacks[0].source_clause}
                            </span>
                        </div>
                    </div>
                    
                    <div class="setback-item rear">
                        <div class="setback-header">
                            <span class="direction-icon">🏡</span>
                            <span class="direction">Rear Setback</span>
                            <span class="distance">${this.setbacks.rear_setback.calculated_distance.toFixed(1)}m</span>
                        </div>
                        <div class="calculation-detail">
                            ${this.setbacks.rear_setback.calculation_explanation}
                        </div>
                        <div class="regulatory-reference">
                            <span class="citation-link" data-citation="rear">
                                📋 ${this.setbacks.rear_setback.source_document} - ${this.setbacks.rear_setback.source_clause}
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    renderBuildingEnvelope() {
        const envelope = this.setbacks.buildable_envelope;
        
        return `
            <div class="building-envelope-visualization">
                <h5>📦 Building Envelope</h5>
                
                <div class="envelope-diagram">
                    <div class="lot-outline">
                        <div class="lot-dimensions">
                            <span class="width-label">${envelope.lot_width}m wide</span>
                            <span class="depth-label">${envelope.lot_depth}m deep</span>
                        </div>
                        
                        <div class="buildable-area" style="
                            width: ${(envelope.buildable_width / envelope.lot_width) * 100}%;
                            height: ${(envelope.buildable_depth / envelope.lot_depth) * 100}%;
                            margin: ${(this.setbacks.front_setback.calculated_distance / envelope.lot_depth) * 100}% 
                                   ${(this.setbacks.side_setbacks[0].calculated_distance / envelope.lot_width) * 100}%;
                        ">
                            <div class="buildable-label">
                                Buildable Area<br>
                                ${envelope.buildable_width.toFixed(1)}m × ${envelope.buildable_depth.toFixed(1)}m
                            </div>
                        </div>
                        
                        <div class="setback-labels">
                            <div class="front-label">Front: ${this.setbacks.front_setback.calculated_distance}m</div>
                            <div class="side-label left">Side: ${this.setbacks.side_setbacks[0].calculated_distance.toFixed(1)}m</div>
                            <div class="side-label right">Side: ${this.setbacks.side_setbacks[0].calculated_distance.toFixed(1)}m</div>
                            <div class="rear-label">Rear: ${this.setbacks.rear_setback.calculated_distance.toFixed(1)}m</div>
                        </div>
                    </div>
                </div>
                
                <div class="envelope-summary-stats">
                    <div class="stat">
                        <strong>Maximum Footprint:</strong> ${envelope.max_footprint.toFixed(0)}m²
                    </div>
                    <div class="stat">
                        <strong>Area Lost to Setbacks:</strong> ${envelope.setback_area_lost.toFixed(0)}m² 
                        (${((envelope.setback_area_lost / (envelope.lot_width * envelope.lot_depth)) * 100).toFixed(0)}%)
                    </div>
                </div>
            </div>
        `;
    }
    
    renderRegulatoryCitations() {
        return `
            <div class="regulatory-citations">
                <h5>📚 Governing Regulations</h5>
                <div class="citations-list">
                    ${this.setbacks.governing_documents.map(doc => `
                        <div class="citation-item">
                            <div class="document-name">${doc}</div>
                        </div>
                    `).join('')}
                </div>
                
                <div class="citation-note">
                    <small>💡 Click any regulation reference above to see the full text and measurement requirements.</small>
                </div>
            </div>
        `;
    }
    
    attachCitationTooltips() {
        document.querySelectorAll('.citation-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const citationType = e.target.dataset.citation;
                this.showRegulationModal(citationType);
            });
        });
    }
    
    showRegulationModal(setbackType) {
        const setback = setbackType === 'sides' ? this.setbacks.side_setbacks[0] : this.setbacks[setbackType + '_setback'];
        
        const modal = document.createElement('div');
        modal.className = 'regulation-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>${setback.setback_type.toUpperCase()} SETBACK REGULATION</h3>
                    <button class="close-modal">×</button>
                </div>
                
                <div class="modal-body">
                    <div class="citation-full">
                        <strong>📋 Source:</strong> ${setback.source_document}<br>
                        <strong>📍 Clause:</strong> ${setback.source_clause}
                    </div>
                    
                    <div class="regulation-text">
                        <h4>📖 Regulation Text:</h4>
                        <blockquote>${setback.regulation_text}</blockquote>
                    </div>
                    
                    <div class="calculation-breakdown">
                        <h4>🧮 Calculation for Your Property:</h4>
                        <div class="calculation-step">
                            <strong>Formula:</strong> <code>${setback.calculation_formula}</code>
                        </div>
                        <div class="calculation-step">
                            <strong>Result:</strong> ${setback.calculation_explanation}
                        </div>
                        <div class="calculation-step">
                            <strong>Measurement:</strong> From ${setback.measurement_from} to ${setback.measurement_to}
                        </div>
                    </div>
                    
                    ${setback.validation_notes.length > 0 ? `
                        <div class="validation-notes">
                            <h4>⚠️ Important Notes:</h4>
                            <ul>
                                ${setback.validation_notes.map(note => `<li>${note}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                </div>
                
                <div class="modal-footer">
                    <button class="btn-primary">Got It</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Close modal handlers
        modal.querySelector('.close-modal').onclick = () => document.body.removeChild(modal);
        modal.querySelector('.btn-primary').onclick = () => document.body.removeChild(modal);
        modal.onclick = (e) => {
            if (e.target === modal) document.body.removeChild(modal);
        };
    }
}
```

## API Integration

### Setback Calculation Endpoint
```python
@app.post("/calculate-setbacks")
async def calculate_property_setbacks(request: QueryRequest):
    """Calculate property-specific setbacks with full regulatory citations"""
    try:
        # Get property context
        from services.property_intelligence import get_property_dashboard
        property_context = await get_property_dashboard(request.address)
        
        # Calculate setbacks
        from services.setback_calculator import SetbackCalculationEngine
        calculator = SetbackCalculationEngine()
        setback_results = await calculator.calculate_property_setbacks(property_context)
        
        return {
            "success": True,
            "setback_calculations": {
                "address": setback_results.address,
                "zone": setback_results.zone,
                "height_limit": setback_results.height_limit,
                "front_setback": {
                    "distance": setback_results.front_setback.calculated_distance,
                    "calculation": setback_results.front_setback.calculation_explanation,
                    "source": f"{setback_results.front_setback.source_document} - {setback_results.front_setback.source_clause}",
                    "regulation_text": setback_results.front_setback.regulation_text
                },
                "side_setbacks": [{
                    "distance": setback_results.side_setbacks[0].calculated_distance,
                    "base_requirement": setback_results.side_setbacks[0].base_requirement,
                    "height_adjustment": setback_results.side_setbacks[0].height_adjustment,
                    "calculation": setback_results.side_setbacks[0].calculation_explanation,
                    "formula": setback_results.side_setbacks[0].calculation_formula,
                    "source": f"{setback_results.side_setbacks[0].source_document} - {setback_results.side_setbacks[0].source_clause}",
                    "regulation_text": setback_results.side_setbacks[0].regulation_text
                }],
                "rear_setback": {
                    "distance": setback_results.rear_setback.calculated_distance,
                    "calculation": setback_results.rear_setback.calculation_explanation,
                    "source": f"{setback_results.rear_setback.source_document} - {setback_results.rear_setback.source_clause}",
                    "regulation_text": setback_results.rear_setback.regulation_text
                },
                "buildable_envelope": setback_results.buildable_envelope,
                "governing_documents": setback_results.governing_documents,
                "calculation_confidence": "HIGH"
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Setback calculation failed: {str(e)}",
            "fallback": "Using standard R2 setback estimates"
        }
```

## Success Criteria
1. ✅ Calculate exact setback distances using property height and zone
2. ✅ Show calculation formulas and steps (not just final numbers)
3. ✅ Display full regulatory citations with document and clause references
4. ✅ Provide visual building envelope showing buildable area
5. ✅ Include clickable regulation tooltips with full text
6. ✅ Show measurement methods (from boundary to wall, etc.)

## Test Cases
**Primary Test:** 34 Pile St, Dulwich Hill NSW 2203 (R2, 9.5m height)
- Expected Side Setback: 0.9m + (9.5m - 7.5m) × 0.5 = 1.9m
- Expected Citation: "Marrickville DCP 2011 - Section 2.3.1 Side Setbacks"
- Expected Regulation Text: "Side setbacks shall be 0.9m minimum, increased by..."
- Expected Building Envelope: Visual diagram showing 15m × 30m lot with buildable area

**Heritage Test:** Heritage property with additional constraints
- Expected: Heritage-specific setback increases and additional citations

## Dependencies
- LightRAG integration (✅ working) for setback provision extraction
- AutoSchemaKG integration (✅ working) for height-setback relationships  
- Property intelligence service (✅ working) for property context
- Frontend modal system for regulation display

## Implementation Timeline
**Week 1:** Setback calculation engine with LightRAG integration
**Week 2:** Regulatory citation extraction and formatting
**Week 3:** Frontend visual envelope and calculation display  
**Week 4:** Regulation modal system and full testing

## Notes
This PRP transforms setbacks from "read the DCP" to "your building can be 1.9m from the side boundary because..." - providing the exact calculation, reasoning, and regulatory authority for every measurement.