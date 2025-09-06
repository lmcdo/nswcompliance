# PRP-D: Property-Centric 4-Stack Integration Architecture

## Status: DESIGN FOR IMPLEMENTATION
**Created:** 2025-08-30  
**Purpose:** Create integrated, efficient, coherent, prioritized data for selected properties

## Executive Summary

The current system has 4 RAG stacks working in isolation. The integration must be **property-specific** - providing targeted, prioritized, coherent regulatory intelligence for the exact property being analyzed.

## Current vs Required Architecture

### Current (Inefficient):
```
Property Address → Generic Text Search → All Documents → Random Results
```

### Required (Property-Centric):
```
Property Address → Property Intelligence → 4-Stack Synthesis → Prioritized Results
    ↓                      ↓                    ↓                    ↓
NSW API Data     →   Filtered Documents  →  Coherent Synthesis → Property-Specific
(Zone, Height,       (Relevant LEP/DCP    (Connected Rules)     (Actionable Data)
 Heritage, LGA)       Only)
```

## Property-Centric Integration Flow

### Stage 1: Property Intelligence Context
```python
class PropertyContext:
    """Extract all property-specific context first"""
    def __init__(self, address: str):
        self.address = address
        self.nsw_data = self.get_nsw_api_data()  # Zone, height, heritage
        self.applicable_docs = self.filter_applicable_documents()
        self.priority_controls = self.identify_priority_controls()
    
    @property
    def search_context(self):
        return {
            "zone": self.nsw_data.zone,
            "lga": self.nsw_data.lga_name, 
            "height_limit": self.nsw_data.building_height_limit,
            "heritage": self.nsw_data.heritage_status,
            "applicable_lep": self.nsw_data.applicable_lep,
            "priority_queries": ["height", "setbacks", "fsr", "heritage"]
        }
```

### Stage 2: Intelligent Document Filtering
```python
class PropertyDocumentFilter:
    """Only query documents applicable to this specific property"""
    
    def filter_by_jurisdiction(self, property_context):
        """Filter: Only Inner West LEP 2022 + Marrickville DCP for Marrickville properties"""
        if "Inner West" in property_context.lga:
            if "Marrickville" in property_context.address:
                return ["Inner West LEP 2022", "Marrickville DCP 2011"]
            elif "Ashfield" in property_context.address:
                return ["Inner West LEP 2022", "Ashfield DCP 2016"]
        
        return self.get_applicable_documents(property_context.lga)
    
    def filter_by_zone(self, documents, zone):
        """Filter: Only provisions applicable to R2/B4/IN1 etc."""
        zone_specific_docs = []
        for doc in documents:
            if self.applies_to_zone(doc, zone):
                zone_specific_docs.append(doc)
        return zone_specific_docs
```

### Stage 3: 4-Stack Synthesis (Property-Focused)
```python
class PropertyFocused4StackIntegration:
    """Each stack contributes property-specific intelligence"""
    
    async def synthesize_for_property(self, property_context):
        results = {}
        
        # Stack 1: LightRAG - Fast property-specific retrieval
        lightrag_results = await self.query_lightrag_filtered(
            query=f"development controls {property_context.zone} {property_context.lga}",
            document_filter=property_context.applicable_docs
        )
        
        # Stack 2: AutoSchemaKG - Connected requirements for this property  
        connected_requirements = await self.get_connected_requirements(
            base_controls=["height", "setbacks", "fsr"],
            property_zone=property_context.zone,
            knowledge_graph=self.autoschema_data
        )
        
        # Stack 3: RAG-Anything - Extract property-relevant diagrams/tables
        visual_content = await self.extract_property_visuals(
            documents=property_context.applicable_docs,
            property_type=property_context.zone,
            controls=["height_diagrams", "setback_calculations"]
        )
        
        # Stack 4: LangExtract - Structure numeric limits for this property
        structured_limits = await self.extract_numeric_limits(
            provisions=lightrag_results,
            property_zone=property_context.zone,
            schema={
                "height_limit": {"value": float, "units": str, "measurement_from": str},
                "setbacks": {"front": float, "rear": float, "side": float},
                "fsr": {"maximum": float, "zone_specific": bool}
            }
        )
        
        return self.synthesize_coherent_response(
            lightrag_results, connected_requirements, visual_content, structured_limits
        )
```

### Stage 4: Intelligent Prioritization
```python
class PropertySpecificPrioritization:
    """Return only the most relevant, actionable information"""
    
    def prioritize_for_development(self, synthesis_results, property_context):
        priorities = {
            "CRITICAL": [],    # Must comply (height limits, heritage)
            "IMPORTANT": [],   # Significant impact (setbacks, FSR)
            "RELEVANT": [],    # Nice to know (parking, landscaping)
            "INFORMATIONAL": [] # Background context
        }
        
        # Priority 1: Hard limits from NSW API
        if property_context.height_limit:
            priorities["CRITICAL"].append({
                "control": "height_limit",
                "value": property_context.height_limit,
                "source": "NSW Planning Portal",
                "actionable": f"Maximum building height: {property_context.height_limit}m"
            })
        
        # Priority 2: Zone-specific controls from synthesis
        for control in synthesis_results.structured_limits:
            if control.zone_specific and control.applies_to(property_context.zone):
                priorities["IMPORTANT"].append({
                    "control": control.type,
                    "value": control.numeric_value,
                    "calculation_method": control.measurement_method,
                    "exceptions": control.exceptions
                })
        
        # Priority 3: Connected requirements (AutoSchemaKG)
        for connection in synthesis_results.connected_requirements:
            if connection.affects_development_potential:
                priorities["RELEVANT"].append(connection)
        
        return self.format_actionable_response(priorities)
```

## Implementation Architecture

### New API Endpoint
```python
@app.post("/property-intelligence-complete")
async def complete_property_analysis(request: PropertyAnalysisRequest):
    """Complete 4-stack property analysis"""
    
    # Stage 1: Property Context
    property_context = PropertyContext(request.address)
    
    # Stage 2: Document Filtering  
    doc_filter = PropertyDocumentFilter()
    applicable_docs = doc_filter.filter_by_jurisdiction_and_zone(property_context)
    
    # Stage 3: 4-Stack Synthesis
    integration = PropertyFocused4StackIntegration()
    synthesis = await integration.synthesize_for_property(property_context)
    
    # Stage 4: Intelligent Prioritization
    prioritizer = PropertySpecificPrioritization()
    prioritized_results = prioritizer.prioritize_for_development(synthesis, property_context)
    
    return PropertyIntelligenceResponse(
        property_address=request.address,
        property_context=property_context.to_dict(),
        regulatory_intelligence=prioritized_results,
        processing_metadata={
            "stacks_used": ["lightrag", "autoschemakg", "raganything", "langextract"],
            "documents_analyzed": len(applicable_docs),
            "confidence_score": synthesis.overall_confidence,
            "processing_time_ms": synthesis.processing_time
        }
    )
```

### Expected Output Format
```json
{
    "property_address": "34 Pile Street, Dulwich Hill NSW 2203",
    "property_context": {
        "zone": "R2 Low Density Residential",
        "lga": "Inner West Council", 
        "applicable_lep": "Inner West LEP 2022",
        "applicable_dcp": "Marrickville DCP 2011",
        "heritage_status": "None"
    },
    "regulatory_intelligence": {
        "critical_controls": [
            {
                "type": "height_limit",
                "value": "9.5m maximum",
                "source": "Inner West LEP 2022 Clause 4.3",
                "measurement": "from natural ground level",
                "exceptions": ["solar panels up to 1m additional"],
                "development_impact": "Allows 2 stories typically"
            }
        ],
        "important_controls": [
            {
                "type": "setbacks",
                "front": "6m minimum",
                "side": "0.9m minimum", 
                "rear": "6m minimum OR 0.5x building height",
                "source": "Marrickville DCP 2011 Section 2.1",
                "connected_to": ["solar_access", "privacy"]
            }
        ],
        "connected_requirements": [
            {
                "primary_control": "building_height",
                "affects": ["setbacks", "solar_access", "building_envelope"],
                "relationship": "Taller buildings require larger setbacks",
                "calculation": "Side setback = 0.9m + (height - 7.5m) * 0.5"
            }
        ],
        "visual_guidance": {
            "diagrams": ["building_envelope_diagram.png"],
            "calculation_tables": ["setback_calculation_matrix.csv"]
        }
    },
    "actionable_summary": {
        "development_potential": "2-story dwelling possible within 9.5m height limit",
        "key_constraints": ["6m setbacks may limit footprint on narrow lots"],
        "next_steps": ["Check heritage overlay", "Consider SEPP exemptions"],
        "confidence": "HIGH (0.92)"
    }
}
```

## Integration Benefits

### Current System Issues:
- ❌ Generic search returns irrelevant documents
- ❌ No property-specific filtering
- ❌ No data synthesis or prioritization  
- ❌ User must interpret raw regulatory text

### Property-Centric Benefits:
- ✅ **Property-Specific**: Only relevant LEP/DCP provisions
- ✅ **Efficient**: Pre-filtered by zone, LGA, heritage status
- ✅ **Coherent**: Connected requirements identified (height → setbacks)
- ✅ **Prioritized**: Critical controls first, informational last
- ✅ **Actionable**: "You can build X" not "The regulation says Y"

## Implementation Timeline

### Week 1: Property Context Layer
- Build `PropertyContext` class
- Integrate with existing NSW API
- Create document filtering logic

### Week 2: 4-Stack Synthesis Engine  
- Connect existing LightRAG to property-specific queries
- Load AutoSchemaKG data for connected requirements
- Integrate RAG-Anything for visual content
- Apply LangExtract for structured limits

### Week 3: Prioritization & Response Engine
- Build prioritization logic 
- Create actionable response formatting
- Integrate with existing frontend

### Week 4: Testing & Optimization
- Test with various property types
- Optimize performance
- Deploy integrated system

## Success Metrics

### Performance:
- Query response time: < 3 seconds
- Document filtering efficiency: 80%+ irrelevant docs excluded
- Confidence score: > 0.85 for property-specific results

### User Experience:
- Actionable insights: "You can build X" format
- Connected guidance: Show how rules relate
- Visual aids: Include diagrams/calculations when available
- Prioritized information: Critical controls prominently displayed

This creates a true **property intelligence system** rather than a generic document search.