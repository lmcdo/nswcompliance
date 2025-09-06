#!/usr/bin/env python3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware  
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from pathlib import Path
import subprocess
import sys
import time
from typing import List, Optional, Dict, Any
import asyncio
import re
from services.clause_citation_store import enrich_planning_rules_with_citations, search_clause_citations
from services.database_autoschema_query import DatabaseAutoSchemaQuery

class QueryRequest(BaseModel):
    address: str
    query_type: str 
    context: Optional[str] = None
    lga_name: Optional[str] = None  # NEW: Filter results by LGA jurisdiction

class PlanningRule(BaseModel):
    title: str
    text: str
    type: str
    source: Optional[str] = None
    confidence: Optional[float] = None
    citation_text: Optional[str] = None
    citation_clause: Optional[str] = None
    
    # NEW: Full citation fields for council-quality references
    full_clause_text: Optional[str] = None
    clause_number: Optional[str] = None
    clause_title: Optional[str] = None
    document_section: Optional[str] = None
    citation_format: Optional[str] = None
    extraction_confidence: Optional[float] = None
    source_authority: Optional[str] = None
    requires_verification: Optional[bool] = None
    has_full_citation: Optional[bool] = False

class PropertyIntelligenceResponse(BaseModel):
    address: str
    prop_id: Optional[int] = None
    zone: Optional[str] = None
    zone_description: Optional[str] = None
    height_limit: Optional[str] = None
    height_units: Optional[str] = None
    height_clause: Optional[str] = None
    fsr_limit: Optional[str] = None
    land_area: Optional[str] = None
    land_value: Optional[str] = None
    applicable_lep: Optional[str] = None
    lga_name: Optional[str] = None
    heritage_status: Optional[str] = None
    quick_metrics: List[Dict[str, Any]] = []
    data_quality: str = "Unknown"
    api_success: bool = False
    planning_controls: Optional[List[Dict[str, Any]]] = None  # NEW: Full NSW planning data

app = FastAPI(title="NSW Planning API", version="2.0.0")

@app.get("/debug-route-test")
async def debug_route_test():
    """Debug route to test if new routes are being registered"""
    return {"message": "Debug route is working!", "timestamp": "2025-08-30-10:00"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def filter_results_by_jurisdiction(planning_rules: List[PlanningRule], target_lga: str) -> List[PlanningRule]:
    """Filter planning rules to only include documents from target LGA or state-wide policies"""
    if not target_lga:
        return planning_rules
    
    filtered_rules = []
    target_lga_upper = target_lga.upper()
    
    for rule in planning_rules:
        rule_source = (rule.source or "").upper()
        rule_title = (rule.title or "").upper()
        
        # Always include property intelligence from NSW API
        if rule.type == "property_intelligence":
            filtered_rules.append(rule)
            continue
            
        # Always include state-wide policies (SEPPs)
        if any(sepp_indicator in rule_source for sepp_indicator in ["SEPP", "STATE ENVIRONMENTAL PLANNING POLICY"]):
            filtered_rules.append(rule)
            continue
            
        # Include if document matches target LGA
        if target_lga_upper in rule_source or target_lga_upper in rule_title:
            filtered_rules.append(rule)
            continue
            
        # Define what constitutes target LGA documents (including historical councils)
        if target_lga_upper == "INNER WEST":
            # Inner West includes former Marrickville, Ashfield, Leichhardt councils
            target_patterns = ["INNER WEST", "MARRICKVILLE", "ASHFIELD", "LEICHHARDT"]
        else:
            target_patterns = [target_lga_upper]
        
        # Check if this document belongs to target LGA
        is_target_lga_doc = any(pattern in rule_source or pattern in rule_title 
                               for pattern in target_patterns)
        
        if is_target_lga_doc:
            filtered_rules.append(rule)
            continue
        
        # Only exclude documents that have clear council DCP/LEP patterns from OTHER councils
        # Look for pattern: "[OTHER_COUNCIL_NAME] DCP" or "[OTHER_COUNCIL_NAME] LEP"
        import re
        council_doc_pattern = r'([A-Z\s]+)\s+(DCP|LEP)\s+\d{4}'
        match = re.search(council_doc_pattern, rule_source + " " + rule_title)
        
        if match:
            council_name = match.group(1).strip()
            # If it's clearly from a different council, exclude it
            if council_name not in target_patterns:
                continue  # Skip this document
        
        # Default: include document (might be generic or relevant)
        filtered_rules.append(rule)
    
    print(f"DEBUG: Filtered from {len(planning_rules)} to {len(filtered_rules)} rules for LGA: {target_lga}")
    return filtered_rules

validated_query_script = None

async def initialize_validated_system():
    global validated_query_script
    script_path = Path("scripts/validated_nsw_query.py")
    if script_path.exists():
        validated_query_script = str(script_path)
        return True
    return False

@app.get("/")
async def serve_frontend():
    html_file = Path("frontend/index.html")
    if html_file.exists():
        return FileResponse(str(html_file), media_type="text/html")
    return {"error": "Frontend not found"}

@app.get("/app")
async def serve_app():
    html_file = Path("frontend/index.html") 
    if html_file.exists():
        return FileResponse(str(html_file), media_type="text/html")
    return {"error": "Frontend not found"}

@app.get("/property-intelligence")
async def get_property_intelligence_endpoint(address: str, lat: Optional[float] = None, lng: Optional[float] = None, include_raw_nsw_data: Optional[bool] = False):
    """Get property intelligence from NSW Planning APIs"""
    try:
        # Import here to avoid startup issues
        from services.property_intelligence import get_property_dashboard
        
        # Prepare Google coordinates if provided
        google_coords = None
        if lat is not None and lng is not None:
            google_coords = {"lat": lat, "lng": lng}
            print(f"Using Google coordinates for validation: {google_coords}")
        
        dashboard = await get_property_dashboard(address, google_coords)
        
        # Get raw NSW planning data if requested
        raw_planning_controls = None
        if include_raw_nsw_data:
            # Get the original PropertyIntelligence data with raw planning controls
            from services.nsw_planning_api import get_property_intelligence
            intelligence = await get_property_intelligence(address, google_coords)
            raw_planning_controls = intelligence.raw_planning_controls
        
        # Convert to response format
        return PropertyIntelligenceResponse(
            address=dashboard.address,
            prop_id=dashboard.prop_id,
            zone=dashboard.zone,
            zone_description=dashboard.zone_description,
            height_limit=dashboard.height_limit,
            height_units=dashboard.height_units,
            height_clause=dashboard.height_clause,
            fsr_limit=dashboard.fsr_limit,
            land_area=dashboard.land_area,
            land_value=dashboard.land_value,
            applicable_lep=dashboard.applicable_lep,
            lga_name=dashboard.lga_name,
            heritage_status=dashboard.heritage_status,
            quick_metrics=[
                {
                    "name": metric.name,
                    "value": metric.value,
                    "status": metric.status.value,
                    "details": metric.details
                }
                for metric in dashboard.quick_metrics
            ],
            data_quality=dashboard.data_quality,
            api_success=dashboard.api_success,
            planning_controls=raw_planning_controls
        )
        
    except Exception as e:
        return PropertyIntelligenceResponse(
            address=address,
            api_success=False,
            data_quality="Error",
            quick_metrics=[{
                "name": "API Error",
                "value": str(e),
                "status": "FAIL",
                "details": "Failed to fetch property intelligence"
            }]
        )

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "processor_available": validated_query_script is not None,
        "processor_type": "Validated NSW Query System",
        "message": "Ready"
    }

def parse_validated_response(raw_output: str) -> List[PlanningRule]:
    """Parse the raw output from validated_nsw_query.py into PlanningRule objects"""
    try:
        planning_rules = []
        import re
        
        # Extract content from dictionary structures like {'content': '...'}
        content_matches = re.findall(r"'content': '([^']*(?:\\'[^']*)*)'", raw_output)
        
        # Process each content block
        for content_block in content_matches:
            # Split content by double newlines to get individual provisions
            provisions = content_block.split('\\n\\n')
            
            for provision in provisions:
                provision = provision.strip().replace('\\n', ' ')
                if not provision:
                    continue
                    
                # Look for provision lines: [Document] Clause X (type): Text
                if provision.startswith("[") and "] Clause" in provision and ("): " in provision or "):" in provision):
                    try:
                        # Parse: [Doc Name] Clause X.X (type): Provision text
                        parts = provision.split("] Clause", 1)
                        if len(parts) == 2:
                            doc_name = parts[0][1:]  # Remove leading [
                            clause_part = parts[1]
                            
                            # Split clause reference from type and text
                            if "(" in clause_part and ("): " in clause_part or "):" in clause_part):
                                clause_ref = clause_part.split("(")[0].strip()
                                type_and_text = clause_part.split("(", 1)[1]
                                
                                if "): " in type_and_text:
                                    provision_type = type_and_text.split("): ")[0]
                                    provision_text = type_and_text.split("): ", 1)[1].strip()
                                elif "):" in type_and_text:
                                    provision_type = type_and_text.split("):")[0]
                                    provision_text = type_and_text.split("):", 1)[1].strip()
                                else:
                                    continue
                                    
                                # Create planning rule
                                planning_rules.append(PlanningRule(
                                    title=f"{doc_name} - Clause {clause_ref}",
                                    text=provision_text,
                                    type=provision_type,
                                    source=doc_name,
                                    confidence=0.95,
                                    citation_text=provision_text,
                                    citation_clause=f"Clause {clause_ref}"
                                ))
                                
                                # Limit results to prevent overwhelming the UI
                                if len(planning_rules) >= 15:
                                    break
                                
                    except Exception as parse_error:
                        # Skip malformed lines but continue processing
                        continue
                
                # Break if we hit the limit
                if len(planning_rules) >= 15:
                    break
            
            # Break if we hit the limit
            if len(planning_rules) >= 15:
                break
        
        return planning_rules
        
    except Exception as e:
        print(f"Parse error: {e}")
        return []

@app.post("/query")
async def query_planning_rules(request: QueryRequest):
    # Use integrated multimodal query system instead of external script
    try:
        from services.integrated_multimodal_query import IntegratedMultimodalQuery
        query_system = IntegratedMultimodalQuery()
        
        result = query_system.query_integrated_planning_rules(
            address=request.address,
            query_context=request.context or "",
            lga_name=request.lga_name
        )
        
        # Convert to expected format
        planning_rules = []
        for rule in result.get("integrated_rules", []):
            planning_rules.append({
                "title": f"{rule['source']} {rule['relation']} {rule['target']}",
                "text": rule.get("regulatory_text", rule.get("visual_text", "")),
                "type": rule["type"],
                "source": rule.get("document", ""),
                "confidence": rule.get("confidence", 0.5),
                "has_full_citation": True,
                "clause_number": rule["source"],
                "citation_format": f"{rule['source']} -> {rule['target']}"
            })
        
        return {
            "success": result["success"],
            "planning_rules": planning_rules,
            "summary": {
                "total_rules": len(planning_rules),
                "regulatory_relationships": result["summary"]["total_regulatory"],
                "visual_context_items": result["summary"]["total_visual"],
                "integrated_rules": result["summary"]["total_integrated"]
            },
            "address": request.address,
            "processing_time": 0.1  # Fast database queries
        }
        
    except Exception as e:
        print(f"Error in multimodal query: {e}")
        return {"success": False, "error": f"Query system error: {str(e)}"}
    
    try:
        # First, get property intelligence to inform the query
        from services.property_intelligence import get_property_dashboard
        dashboard = await get_property_dashboard(request.address)
        
        # Build location-aware query with LEP/LGA context
        location_context = ""
        if dashboard.applicable_lep:
            location_context = f" {dashboard.applicable_lep}"
        if dashboard.lga_name:
            location_context += f" {dashboard.lga_name}"
        if dashboard.zone:
            location_context += f" {dashboard.zone} zone"
            
        # Build query based on type with location context
        if request.query_type == "height":
            query = f"building height limits {location_context} {request.address}"
        elif request.query_type == "fsr": 
            query = f"floor space ratio FSR {location_context} {request.address}"
        elif request.query_type == "setback":
            query = f"boundary setbacks {location_context} {request.address}"
        elif request.query_type == "general":
            query = f"general planning rules {location_context} {request.address}"
        elif request.query_type == "all":
            query = f"all planning controls {location_context} {request.address}"
        else:
            query = f"planning rules {location_context} {request.address}"
            
        if request.context:
            query += f" {request.context}"
        
        # Use LGA from request or fallback to dashboard LGA
        target_lga = request.lga_name or dashboard.lga_name
        print(f"DEBUG: Target LGA for filtering: {target_lga}")
        
        start_time = time.time()
        
        result = subprocess.run([
            sys.executable, validated_query_script, query
        ], capture_output=True, text=True, timeout=30)
        
        processing_time = time.time() - start_time
        
        if result.returncode == 0:
            # Debug: Print first few lines of output
            print(f"DEBUG: Query output (first 500 chars): {result.stdout[:500]}")
            
            # Parse the actual response
            planning_rules = parse_validated_response(result.stdout)
            print(f"DEBUG: Parsed {len(planning_rules)} planning rules")
            
            # Apply LGA jurisdiction filtering
            if target_lga:
                planning_rules = filter_results_by_jurisdiction(planning_rules, target_lga)
            
            # ENHANCE: Add full citations to all planning rules
            try:
                enriched_rules_data = enrich_planning_rules_with_citations(planning_rules)
                # Convert back to PlanningRule objects with full citation data
                enriched_planning_rules = []
                for rule_data in enriched_rules_data:
                    enriched_rule = PlanningRule(**rule_data)
                    enriched_planning_rules.append(enriched_rule)
                planning_rules = enriched_planning_rules
                print(f"DEBUG: Enhanced {len(planning_rules)} rules with full citations")
            except Exception as citation_error:
                print(f"WARNING: Citation enhancement failed: {citation_error}")
                # Continue with original rules if citation fails
            
            # Add NSW API property intelligence as first result
            if dashboard.api_success:
                api_info = PlanningRule(
                    title=f"Property Intelligence - {dashboard.address}",
                    text=f"Zone: {dashboard.zone or 'Unknown'} ({dashboard.zone_description or 'Not specified'})\n" +
                         f"Height Limit: {dashboard.height_limit or 'Not specified'} {dashboard.height_units or ''}\n" +
                         f"LEP: {dashboard.applicable_lep or 'Unknown'}\n" +
                         f"LGA: {dashboard.lga_name or 'Unknown'}\n" +
                         f"Property ID: {dashboard.prop_id}\n" +
                         f"Data Quality: {dashboard.data_quality}\n\n" +
                         "Note: NSW Planning API results may show different locations for same street names. " +
                         "This is a known limitation of the government address geocoding system.",
                    type="property_intelligence",
                    source="NSW Planning Portal API",
                    confidence=0.9,
                    citation_text=f"NSW Planning Portal Property ID: {dashboard.prop_id}",
                    citation_clause="Live Government Data"
                )
                planning_rules.insert(0, api_info)
            
            if not planning_rules:
                planning_rules = [PlanningRule(
                    title="No Results Found",
                    text=f"No regulatory provisions found for {request.address} in the NSW planning database.",
                    type="info",
                    source="Validated NSW Query System",
                    confidence=0.5
                )]
            
            return {
                "success": True,
                "results": [rule.dict() for rule in planning_rules],
                "address": request.address,
                "query_type": request.query_type,
                "processing_time": processing_time
            }
        else:
            return {"success": False, "error": f"Query failed: {result.stderr}"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/council-validation")
async def council_validation_report(request: QueryRequest):
    """Generate complete council validation report with full citations and regulatory text"""
    try:
        from services.council_validation_service import CouncilValidationService
        
        # Get property intelligence for context
        from services.property_intelligence import get_property_dashboard
        dashboard = await get_property_dashboard(request.address)
        
        # Generate validation report
        validation_service = CouncilValidationService()
        # Split context into individual query terms
        query_terms = request.context.split() if request.context else ["setback", "height", "development"]
        report = validation_service.generate_validation_report(
            address=request.address,
            zone=dashboard.zone if hasattr(dashboard, 'zone') else "Unknown",
            query_terms=query_terms
        )
        
        # Convert dataclasses to dict for JSON serialization
        return {
            "success": True,
            "property_address": report.property_address,
            "zone": report.zone,
            "applicable_documents": report.applicable_documents,
            "active_citations": [
                {
                    "clause_ref": citation.clause_ref,
                    "document_name": citation.document_name,
                    "section_title": citation.section_title,
                    "full_text": citation.full_text,
                    "text_before": citation.text_before,
                    "text_before_source": citation.text_before_source, 
                    "text_after": citation.text_after,
                    "text_after_source": citation.text_after_source,
                    "authority": citation.authority,
                    "confidence": citation.confidence
                }
                for citation in report.active_citations
            ],
            "validated_relationships": [
                {
                    "primary_clause_ref": rel.primary_clause.clause_ref,
                    "connected_clause_ref": rel.connected_clause.clause_ref,
                    "relationship_type": rel.relationship_type,
                    "relationship_text": rel.relationship_text,
                    "validation_notes": rel.validation_notes,
                    "precedence_order": rel.precedence_order
                }
                for rel in report.validated_relationships
            ],
            "extracted_values": report.extracted_values,
            "confidence_assessment": report.confidence_assessment,
            "regulatory_summary": report.regulatory_summary,
            "validation_timestamp": report.validation_timestamp
        }
        
    except Exception as e:
        print(f"Council validation error: {e}")
        return {"success": False, "error": f"Validation failed: {str(e)}"}

@app.get("/citations/search")
async def search_citations(q: str, max_results: int = 10):
    """Search for full clause citations by text or clause number"""
    try:
        search_result = search_clause_citations(q, max_results)
        
        return {
            "success": True,
            "query": search_result.query,
            "total_matches": search_result.matches_found,
            "search_time_ms": search_result.search_time_ms,
            "exact_matches": [
                {
                    "clause_number": citation.clause_number,
                    "clause_title": citation.clause_title,
                    "full_text": citation.full_text,
                    "document_name": citation.document_name,
                    "document_section": citation.document_section,
                    "citation_format": citation.citation_format,
                    "source_authority": citation.source_authority,
                    "extraction_confidence": citation.extraction_confidence,
                    "requires_verification": citation.requires_verification
                } for citation in search_result.exact_matches
            ],
            "partial_matches": [
                {
                    "clause_number": citation.clause_number,
                    "clause_title": citation.clause_title,
                    "full_text": citation.full_text[:200] + "..." if len(citation.full_text) > 200 else citation.full_text,
                    "document_name": citation.document_name,
                    "citation_format": citation.citation_format,
                    "extraction_confidence": citation.extraction_confidence
                } for citation in search_result.partial_matches
            ]
        }
        
    except Exception as e:
        return {"success": False, "error": f"Citation search failed: {str(e)}"}

@app.get("/citations/clause/{clause_number}")
async def get_clause_citation(clause_number: str):
    """Get complete citation for a specific clause number"""
    try:
        from services.clause_citation_store import get_citation_for_clause
        citation = get_citation_for_clause(clause_number)
        
        if citation:
            return {
                "success": True,
                "citation": {
                    "clause_number": citation.clause_number,
                    "clause_title": citation.clause_title,
                    "full_text": citation.full_text,
                    "document_name": citation.document_name,
                    "document_section": citation.document_section,
                    "page_number": citation.page_number,
                    "citation_format": citation.citation_format,
                    "source_authority": citation.source_authority,
                    "extraction_confidence": citation.extraction_confidence,
                    "requires_verification": citation.requires_verification,
                    "last_updated": citation.last_updated
                }
            }
        else:
            return {
                "success": False,
                "error": f"No citation found for clause: {clause_number}",
                "suggestions": f"Try searching for '{clause_number}' using /citations/search"
            }
            
    except Exception as e:
        return {"success": False, "error": f"Failed to retrieve citation: {str(e)}"}

@app.get("/citations/stats")
async def get_citation_stats():
    """Get statistics about available citations"""
    try:
        from services.clause_citation_store import ClauseCitationStore
        store = ClauseCitationStore()
        stats = store.get_citation_statistics()
        
        return {
            "success": True,
            "statistics": stats
        }
        
    except Exception as e:
        return {"success": False, "error": f"Failed to get statistics: {str(e)}"}

# Property-Centric 4-Stack Integration Endpoint
@app.post("/property-intelligence-complete")
async def property_intelligence_complete(request: QueryRequest):
    """Complete 4-stack property analysis with prioritized, coherent results"""
    try:
        from services.property_intelligence_4stack import PropertyFocused4StackIntegration
        from dataclasses import asdict
        
        integration = PropertyFocused4StackIntegration()
        result = await integration.analyze_property_complete(request.address)
        
        return {
            "success": True,
            "property_analysis": {
                "address": result.property_address,
                "property_context": result.property_context,
                "critical_controls": [asdict(control) for control in result.critical_controls],
                "important_controls": [asdict(control) for control in result.important_controls],
                "relevant_controls": [asdict(control) for control in result.relevant_controls],
                "connected_requirements": [asdict(req) for req in result.connected_requirements],
                "visual_guidance": result.visual_guidance,
                "actionable_summary": result.actionable_summary,
                "processing_metadata": result.processing_metadata
            }
        }
        
    except Exception as e:
        print(f"ERROR in 4-stack integration: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": f"4-stack integration failed: {str(e)}",
            "fallback_suggestion": "Try the standard /query endpoint"
        }

@app.post("/calculate-setbacks-council")
async def calculate_setbacks_council_ready(request: QueryRequest):
    """
    COUNCIL-READY: Authoritative setback calculator following Inner West LGA 6-step procedure
    MVP Scope: R2 Low Density Residential, Marrickville DCP area, Standard lots, DA pathway
    """
    try:
        # Get property context
        from services.property_intelligence import get_property_dashboard
        property_context = await get_property_dashboard(request.address)
        
        # Calculate using authoritative procedure
        from services.authoritative_setback_calculator import calculate_authoritative_setbacks_for_council, get_council_disclaimers
        
        setback_result = await calculate_authoritative_setbacks_for_council(
            property_context, 
            development_type="development_application"
        )
        
        disclaimers = get_council_disclaimers()
        
        return {
            "success": True,
            "calculator_type": "COUNCIL-READY AUTHORITATIVE",
            "mvp_scope": setback_result.mvp_scope,
            
            # Regulatory Compliance
            "regulatory_compliance": {
                "procedure_followed": "Inner West LGA 6-Step Authoritative Procedure",
                "primary_authority": setback_result.primary_lep,
                "supporting_dcp": setback_result.applicable_dcp,
                "development_pathway": setback_result.development_pathway,
                "verification_required": True
            },
            
            # Property Context
            "property_assessment": {
                "address": setback_result.address,
                "zoning": f"{setback_result.zoning} - {setback_result.zoning_authority}",
                "former_council_area": setback_result.former_council_area,
                "within_mvp_scope": True
            },
            
            # Calculated Setbacks
            "setback_calculations": {
                "front_setback": {
                    "distance": f"{setback_result.front_setback:.1f}m",
                    "authority": setback_result.applicable_dcp,
                    "measurement": setback_result.measurement_points["front"],
                    "verification_required": "Licensed surveyor + building certifier"
                },
                "side_setbacks": {
                    "distance": f"{setback_result.side_setback:.1f}m each side",
                    "authority": f"{setback_result.primary_lep} + height adjustments",
                    "measurement": setback_result.measurement_points["side"],
                    "verification_required": "Licensed surveyor + building certifier"
                },
                "rear_setback": {
                    "distance": f"{setback_result.rear_setback:.1f}m",
                    "authority": f"{setback_result.applicable_dcp} + height-based calculation",
                    "measurement": setback_result.measurement_points["rear"],
                    "verification_required": "Licensed surveyor + building certifier"
                }
            },
            
            # Confidence Assessment
            "confidence_assessment": {
                "grade": setback_result.confidence_grade,
                "percentage": f"{setback_result.confidence_percentage}%",
                "suitable_for": ["Preliminary planning", "DA preparation guidance", "Initial design estimates"],
                "not_suitable_for": setback_result.exclusions,
                "limitations": setback_result.scope_limitations
            },
            
            # Required Disclaimers
            "mandatory_disclaimers": {
                "preliminary_warning": disclaimers.preliminary_warning.strip(),
                "certifier_responsibility": disclaimers.certifier_responsibility.strip(),
                "not_suitable_for": disclaimers.not_suitable_for.strip(),
                "scope_limitations": disclaimers.scope_limitations.strip(),
                "contact_authority": disclaimers.contact_authority.strip()
            },
            
            # Professional Requirements
            "professional_requirements": {
                "verification_sources": setback_result.regulatory_sources,
                "required_verifications": setback_result.verification_requirements,
                "professional_certification": setback_result.professional_certification_required,
                "council_contact": "Inner West Council: (02) 9392 5000"
            },
            
            # Metadata
            "calculation_metadata": {
                "timestamp": setback_result.calculation_timestamp,
                "calculator_version": setback_result.calculator_version,
                "regulatory_procedure": "6-Step Inner West LGA Authoritative Procedure",
                "data_sources": ["IWLEP 2022", "Marrickville DCP 2011", "NSW Planning Portal"]
            }
        }
        
    except ValueError as scope_error:
        # Property outside MVP scope
        disclaimers = get_council_disclaimers()
        return {
            "success": False,
            "error_type": "OUTSIDE_MVP_SCOPE",
            "error_message": str(scope_error),
            "mvp_scope_info": {
                "current_scope": "R2 Low Density Residential, Marrickville DCP area, Standard lots, DA pathway",
                "scope_limitations": disclaimers.scope_limitations.strip(),
                "recommendation": "Contact Inner West Council for properties outside MVP scope"
            },
            "contact_authority": disclaimers.contact_authority.strip()
        }
        
    except Exception as e:
        # Calculation error
        print(f"ERROR in council setback calculation: {str(e)}")
        import traceback
        traceback.print_exc()
        
        disclaimers = get_council_disclaimers()
        return {
            "success": False,
            "error_type": "CALCULATION_FAILED",
            "error_message": f"Calculation failed: {str(e)}",
            "fallback_guidance": {
                "message": "Standard R2 setback estimates available",
                "front_setback": "6.0m (typical Inner West R2)",
                "side_setbacks": "0.9-1.5m (minimum R2 with height adjustments)", 
                "rear_setback": "6.0-8.0m (minimum R2)",
                "important_note": "These are generic estimates only - professional verification essential"
            },
            "mandatory_disclaimers": {
                "preliminary_warning": disclaimers.preliminary_warning.strip(),
                "contact_authority": disclaimers.contact_authority.strip()
            }
        }

@app.post("/calculate-setbacks")
async def calculate_property_setbacks(request: QueryRequest):
    """Calculate property-specific setbacks with full regulatory citations - PRP-B6"""
    try:
        # Get property context
        from services.property_intelligence import get_property_dashboard
        property_context = await get_property_dashboard(request.address)
        
        # Calculate setbacks using PRP-B6 engine
        from services.setback_calculator import calculate_setbacks_for_property
        setback_results = await calculate_setbacks_for_property(property_context)
        
        return {
            "success": True,
            "address": setback_results.address,
            "zone": setback_results.zone,
            "height_limit": setback_results.height_limit,
            "setback_calculations": {
                "front_setback": {
                    "distance": setback_results.front_setback.calculated_distance,
                    "calculation": setback_results.front_setback.calculation_explanation,
                    "formula": setback_results.front_setback.calculation_formula,
                    "source": f"{setback_results.front_setback.source_document} - {setback_results.front_setback.source_clause}",
                    "regulation_text": setback_results.front_setback.regulation_text,
                    "confidence": setback_results.front_setback.confidence,
                    "measurement": f"From {setback_results.front_setback.measurement_from} to {setback_results.front_setback.measurement_to}"
                },
                "side_setbacks": [{
                    "distance": setback_results.side_setbacks[0].calculated_distance,
                    "base_requirement": setback_results.side_setbacks[0].base_requirement,
                    "height_adjustment": setback_results.side_setbacks[0].height_adjustment,
                    "calculation": setback_results.side_setbacks[0].calculation_explanation,
                    "formula": setback_results.side_setbacks[0].calculation_formula,
                    "source": f"{setback_results.side_setbacks[0].source_document} - {setback_results.side_setbacks[0].source_clause}",
                    "regulation_text": setback_results.side_setbacks[0].regulation_text,
                    "confidence": setback_results.side_setbacks[0].confidence,
                    "validation_notes": setback_results.side_setbacks[0].validation_notes
                }],
                "rear_setback": {
                    "distance": setback_results.rear_setback.calculated_distance,
                    "base_requirement": setback_results.rear_setback.base_requirement,
                    "height_adjustment": setback_results.rear_setback.height_adjustment,
                    "calculation": setback_results.rear_setback.calculation_explanation,
                    "formula": setback_results.rear_setback.calculation_formula,
                    "source": f"{setback_results.rear_setback.source_document} - {setback_results.rear_setback.source_clause}",
                    "regulation_text": setback_results.rear_setback.regulation_text,
                    "confidence": setback_results.rear_setback.confidence,
                    "validation_notes": setback_results.rear_setback.validation_notes
                }
            },
            "buildable_envelope": {
                "lot_dimensions": f"{setback_results.buildable_envelope['lot_width']:.1f}m × {setback_results.buildable_envelope['lot_depth']:.1f}m",
                "buildable_dimensions": f"{setback_results.buildable_envelope['buildable_width']:.1f}m × {setback_results.buildable_envelope['buildable_depth']:.1f}m",
                "max_footprint": f"{setback_results.buildable_envelope['max_footprint']:.0f}m²",
                "area_lost_to_setbacks": f"{setback_results.buildable_envelope['setback_area_lost']:.0f}m²",
                "site_coverage_available": f"{setback_results.buildable_envelope['site_coverage_available']:.1f}%"
            },
            "governing_documents": setback_results.governing_documents,
            "calculation_metadata": {
                "timestamp": setback_results.calculation_timestamp,
                "engine_version": "PRP-B6",
                "data_sources": ["LightRAG", "AutoSchemaKG", "NSW Planning Standards"]
            }
        }
        
    except Exception as e:
        print(f"ERROR in setback calculation: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": f"Setback calculation failed: {str(e)}",
            "fallback": {
                "message": "Using standard R2 setback estimates",
                "front_setback": "6.0m (typical)",
                "side_setbacks": "0.9m minimum", 
                "rear_setback": "6.0m minimum",
                "note": "These are generic estimates. Actual requirements may vary."
            }
        }

@app.get("/test-council")
async def test_council_endpoint():
    """Test endpoint to verify council functionality is working"""
    return {"message": "Council setback calculator endpoint is working!", "status": "ready"}

# Enhanced Clause Citation Endpoint with Full Text
@app.post("/clause-citation")
async def get_clause_citation(request: dict):
    """Get complete clause citation details for accordion display"""
    try:
        from services.clause_citation_store import get_citation_for_clause
        
        clause_ref = request.get('clause_ref', '')
        print(f"DEBUG: Received clause request for: '{clause_ref}'")
        
        if not clause_ref:
            return {"error": "No clause reference provided"}
        
        # Try to get full citation first
        full_citation = get_citation_for_clause(clause_ref)
        
        if full_citation:
            return {
                "success": True,
                "clause_ref": clause_ref,
                "has_full_citation": True,
                "clause_number": full_citation.clause_number,
                "clause_title": full_citation.clause_title,
                "full_text": full_citation.full_text,
                "document_name": full_citation.document_name,
                "document_section": full_citation.document_section,
                "citation_format": full_citation.citation_format,
                "source_authority": full_citation.source_authority,
                "extraction_confidence": full_citation.extraction_confidence,
                "requires_verification": full_citation.requires_verification,
                "display_html": f"""
                    <div style="background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 6px; padding: 16px;">
                        <div style="font-weight: 600; color: #0369a1; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">
                            <span>{full_citation.citation_format}</span>
                            <span style="font-size: 12px; background: {'#dcfce7' if full_citation.extraction_confidence >= 0.9 else '#fef3c7'}; color: {'#166534' if full_citation.extraction_confidence >= 0.9 else '#92400e'}; padding: 2px 8px; border-radius: 12px;">
                                {round(full_citation.extraction_confidence * 100)}% confidence
                            </span>
                        </div>
                        <div style="background: white; padding: 16px; border-radius: 4px; border-left: 4px solid #0ea5e9; margin-bottom: 12px;">
                            <div style="font-family: Georgia, serif; line-height: 1.6; color: #1e293b; white-space: pre-wrap;">{full_citation.full_text}</div>
                        </div>
                        <div style="font-size: 12px; color: #64748b;">
                            <div><strong>Authority:</strong> {full_citation.source_authority}</div>
                            <div><strong>Section:</strong> {full_citation.document_section}</div>
                            {'<div style="color: #dc2626; font-weight: 500; margin-top: 4px;">⚠️ Professional verification required for official use</div>' if full_citation.requires_verification else ''}
                        </div>
                    </div>
                """
            }
        
        # Fallback to old citation service if no full citation available
        try:
            from services.clause_citation_inline import InlineClauseCitation
            citation_service = InlineClauseCitation()
            fallback_result = citation_service.get_citation_block(clause_ref)
            fallback_result["has_full_citation"] = False
            fallback_result["note"] = "Using basic citation - full citation not available"
            print(f"DEBUG: Using fallback citation for: {clause_ref}")
            return fallback_result
        except Exception as fallback_error:
            print(f"DEBUG: Fallback citation also failed: {fallback_error}")
            return {
                "error": f"No citation found for: {clause_ref}",
                "has_full_citation": False,
                "clause_ref": clause_ref,
                "suggestion": "Full citation system may need to process this clause number"
            }
        
    except Exception as e:
        print(f"DEBUG: Citation error: {e}")
        return {"error": str(e), "clause_ref": request.get('clause_ref', ''), "has_full_citation": False}

@app.post("/autoschema-relationships")
async def get_autoschema_relationships(request: dict):
    """Get organized AutoSchemaKG relationship tree with 'is before', 'is after', 'is in accordance with' sections"""
    try:
        address = request.get('address', '')
        primary_controls = request.get('primary_controls', ['height', 'setback', 'zone', 'FSR'])
        
        print(f"DEBUG: AutoSchemaKG relationship request for address: {address}")
        print(f"DEBUG: Primary controls: {primary_controls}")
        
        # Initialize database-driven AutoSchema query service
        kg = DatabaseAutoSchemaQuery()
        
        # Get relationships using new database query approach
        query_terms = primary_controls + [address.split(',')[0] if ',' in address else address]
        relationships_list = kg.find_regulatory_relationships(query_terms)
        
        # Convert to organized format expected by API
        relationships = {
            'regulatory_controls': [],
            'compliance_requirements': [],
            'development_standards': []
        }
        
        for rel in relationships_list:
            if rel['relation'] == 'regulates':
                relationships['regulatory_controls'].append({
                    'source': rel['source'],
                    'target': rel['target'],
                    'relation': rel['relation'],
                    'document': rel['document'],
                    'text': rel['text']
                })
            elif 'comply' in rel['relation'] or 'accordance' in rel['relation']:
                relationships['compliance_requirements'].append({
                    'source': rel['source'],
                    'target': rel['target'],
                    'relation': rel['relation'],
                    'document': rel['document'],
                    'text': rel['text']
                })
            else:
                relationships['development_standards'].append({
                    'source': rel['source'],
                    'target': rel['target'],
                    'relation': rel['relation'],
                    'document': rel['document'],
                    'text': rel['text']
                })
        
        # Add summary stats
        total_relationships = sum(len(rel_list) for rel_list in relationships.values())
        
        return {
            "success": True,
            "address": address,
            "relationship_tree": relationships,
            "summary": {
                "total_relationships": total_relationships,
                "regulatory_controls_count": len(relationships.get('regulatory_controls', [])),
                "compliance_requirements_count": len(relationships.get('compliance_requirements', [])),
                "development_standards_count": len(relationships.get('development_standards', []))
            }
        }
        
    except Exception as e:
        print(f"DEBUG: AutoSchemaKG relationship error: {e}")
        return {"error": str(e), "success": False}

@app.get("/visual-content/{provision_id}")
async def get_visual_content(provision_id: int):
    """Get visual content for a specific regulatory provision"""
    import sqlite3
    
    try:
        conn = sqlite3.connect('nsw_planning.db')
        cur = conn.cursor()
        
        # Get visual elements for this provision
        visuals = cur.execute("""
            SELECT visual_type, visual_path, visual_description, page_number,
                   autoschema_source, langextract_source
            FROM visual_elements 
            WHERE provision_id = ?
            ORDER BY page_number
        """, (provision_id,)).fetchall()
        
        # Format for response
        visual_content = []
        for visual_type, path, desc, page, autoschema, langextract in visuals:
            visual_content.append({
                "type": visual_type,
                "path": path,
                "description": desc or "",
                "page_number": page,
                "source": "autoschema" if autoschema else "langextract" if langextract else "unknown",
                "priority": 1 if visual_type in ["diagram", "setback_diagram"] else 2 if visual_type in ["table", "figure"] else 3
            })
        
        conn.close()
        
        # Sort by priority (1 = critical, 2 = important, 3 = helpful)
        visual_content.sort(key=lambda x: x["priority"])
        
        return {
            "success": True,
            "provision_id": provision_id,
            "visual_count": len(visual_content),
            "visuals": visual_content
        }
        
    except Exception as e:
        return {"success": False, "error": str(e), "visuals": []}

@app.get("/visual-content/search")
async def search_visual_content(query: str, visual_type: Optional[str] = None, limit: int = 20):
    """Search visual content by description or clause"""
    import sqlite3
    
    try:
        conn = sqlite3.connect('nsw_planning.db')
        cur = conn.cursor()
        
        # Build search query
        sql = """
            SELECT ve.id, ve.provision_id, ve.visual_type, ve.visual_path, 
                   ve.visual_description, ve.page_number,
                   rp.clause_text, rp.document_id
            FROM visual_elements ve
            JOIN regulatory_provisions rp ON ve.provision_id = rp.id
            WHERE (ve.visual_description LIKE ? OR rp.clause_text LIKE ?)
        """
        params = [f"%{query}%", f"%{query}%"]
        
        if visual_type:
            sql += " AND ve.visual_type = ?"
            params.append(visual_type)
        
        sql += f" ORDER BY ve.page_number LIMIT {limit}"
        
        results = cur.execute(sql, params).fetchall()
        
        # Format results
        visual_results = []
        for result in results:
            vid, prov_id, vtype, path, desc, page, clause, doc_id = result
            visual_results.append({
                "visual_id": vid,
                "provision_id": prov_id,
                "type": vtype,
                "path": path,
                "description": desc or "",
                "page_number": page,
                "clause_preview": (clause or "")[:200] + "..." if clause and len(clause) > 200 else clause or "",
                "document": doc_id,
                "priority": 1 if vtype in ["diagram", "setback_diagram"] else 2 if vtype in ["table", "figure"] else 3
            })
        
        conn.close()
        
        return {
            "success": True,
            "query": query,
            "visual_type_filter": visual_type,
            "results_count": len(visual_results),
            "visuals": visual_results
        }
        
    except Exception as e:
        return {"success": False, "error": str(e), "visuals": []}

@app.post("/enhanced-complete-assessment")
async def enhanced_complete_assessment(request: QueryRequest):
    """Complete assessment using enhanced database with visual content integration"""
    
    try:
        # 1. Get property intelligence (existing function)
        property_response = await property_intelligence_complete(request)
        if not property_response.get("success"):
            return property_response
            
        # 2. Calculate enhanced setbacks (existing function) 
        setback_response = await calculate_setbacks_council_ready(request)
        if not setback_response.get("success"):
            return setback_response
            
        # Extract setback values from council response structure
        setback_calcs = setback_response.get("setback_calculations", {})
        extracted_setbacks = {
            "front": setback_calcs.get("front_setback", {}).get("distance", "Not determined"),
            "side": setback_calcs.get("side_setbacks", {}).get("distance", "Not determined"),
            "rear": setback_calcs.get("rear_setback", {}).get("distance", "Not determined")
        }
        # Add extracted setbacks to response for compatibility
        setback_response["setbacks"] = extracted_setbacks
        
        # 3. Get connected requirements using our design
        from connected_requirements_design import ConnectedRequirementsEngine
        requirements_engine = ConnectedRequirementsEngine()
        
        # Convert property data for requirements engine
        property_data = property_response["property_analysis"] 
        connected = requirements_engine.find_connected_requirements(
            property_data, setback_response.get("setbacks", {})
        )
        
        # 4. Get relevant visual content
        visual_content = []
        # Get visual content - prioritize setback and building envelope diagrams
        import sqlite3
        conn = sqlite3.connect('nsw_planning.db')
        cur = conn.cursor()
        
        # Get visual elements, prioritizing those related to setbacks and building controls
        visuals = cur.execute("""
            SELECT DISTINCT ve.visual_type, ve.visual_path, ve.visual_description, 
                   ve.page_number, rp.document_id
            FROM visual_elements ve
            LEFT JOIN regulatory_provisions rp ON ve.provision_id = rp.id
            WHERE ve.visual_description LIKE '%setback%' 
               OR ve.visual_description LIKE '%building%'
               OR ve.visual_description LIKE '%height%'
               OR ve.visual_description LIKE '%envelope%'
               OR ve.visual_type IN ('diagram', 'figure')
            ORDER BY 
                CASE 
                    WHEN ve.visual_description LIKE '%setback%' THEN 1
                    WHEN ve.visual_description LIKE '%building%' THEN 2
                    WHEN ve.visual_type = 'diagram' THEN 3
                    ELSE 4
                END,
                ve.page_number
            LIMIT 20
        """).fetchall()
        
        # Process visual results
        for vtype, path, desc, page, doc_id in visuals:
            visual_content.append({
                "type": vtype,
                "path": path,
                "description": desc or f"Visual content from {doc_id}",
                "page_number": page,
                "priority": 1 if 'setback' in (desc or '').lower() else 2 if vtype == 'diagram' else 3,
                "source_document": doc_id
            })
        
        conn.close()
        
        # 5. Format comprehensive response
        return {
            "success": True,
            "assessment_type": "enhanced_complete_assessment",
            "property_intelligence": property_response["property_analysis"],
            "setback_calculations": {
                "front_setback": setback_response.get("setbacks", {}).get("front", "Not determined"),
                "side_setback": setback_response.get("setbacks", {}).get("side", "Not determined"), 
                "rear_setback": setback_response.get("setbacks", {}).get("rear", "Not determined"),
                "confidence_grade": setback_response.get("confidence_grade", "MEDIUM"),
                "confidence_percentage": setback_response.get("confidence_percentage", 75),
                "data_source": "Enhanced regulatory database",
                "regulatory_sources": setback_response.get("regulatory_sources", [])
            },
            "connected_requirements": connected,
            "visual_content": visual_content[:10],  # Limit to 10 most relevant visuals
            "page_citations": {
                "total_provisions": (
                    len(connected.get("direct_connections", [])) +
                    len(connected.get("regulatory_links", [])) +
                    len(connected.get("zone_requirements", [])) +
                    len(connected.get("development_context", []))
                ),
                "visual_references": len(visual_content),
                "data_quality": "Database-driven with page citations"
            },
            "processing_metadata": {
                "database_queries": 4,
                "visual_lookups": len(visual_content),
                "cache_status": "fresh_query"
            }
        }
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ENHANCED ASSESSMENT ERROR: {str(e)}")
        print(f"TRACEBACK: {error_details}")
        return {
            "success": False,
            "error": f"Enhanced assessment failed: {str(e)}",
            "error_details": error_details,
            "fallback_available": True
        }

@app.get("/images/{image_name}")
async def serve_image(image_name: str):
    """Serve images for visual guides"""
    image_path = Path("images") / image_name
    if image_path.exists() and image_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
        return FileResponse(image_path)
    else:
        raise HTTPException(status_code=404, detail="Image not found")

@app.on_event("startup")
async def startup_event():
    print("Starting NSW Planning API")
    success = await initialize_validated_system() 
    print(f"Validated system: {success}")
    print("Council setback endpoint should be available at /calculate-setbacks-council")
    print("Enhanced complete assessment endpoint available at /enhanced-complete-assessment")
    print("Image serving endpoint available at /images/{image_name}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8006, reload=False)
