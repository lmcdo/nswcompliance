#!/usr/bin/env python3
"""
Create LightRAG Demo Data
Creates sample processed data in the expected format for testing integration
"""

import os
import json
from pathlib import Path
from datetime import datetime

def create_demo_unified_data():
    """Create demo unified extraction data"""
    
    # Create directories
    unified_dir = Path("public/regulatory-data/unified")
    unified_dir.mkdir(parents=True, exist_ok=True)
    
    cache_dir = Path("public/regulatory-data/cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Demo extracted rules from Ashfield
    demo_rules = [
        {
            "rule_id": "ASHFIELD_SIDE_SETBACK_001",
            "rule_text": "Side setbacks shall be 0.9m minimum for dwelling houses in R2 zones.",
            "rule_type": "side_setback",
            "measurements": [
                {
                    "measurement_type": "side_setback",
                    "value": 0.9,
                    "unit": "metres",
                    "context": "minimum requirement",
                    "confidence": 0.90
                }
            ],
            "rule_classification": {
                "tier": 1,
                "enforcement_level": "MANDATORY",
                "linguistic_confidence": 0.92,
                "prescriptive_indicators": ["shall be", "minimum"],
                "compliance_message_type": "MUST_COMPLY"
            },
            "source_grounding": {
                "extraction_text": "Side setbacks shall be 0.9m minimum for dwelling houses in R2 zones.",
                "source_location": "Chapter F Part 1 Section 4.3.2",
                "source_page": 45,
                "confidence": 0.93,
                "highlighted_spans": [[0, 71]]
            },
            "overall_confidence": 0.93,
            "rule_complexity": "SIMPLE"
        },
        {
            "rule_id": "ASHFIELD_REAR_SETBACK_001", 
            "rule_text": "Rear setbacks must be 6m minimum OR 0.5 times building height, whichever is greater.",
            "rule_type": "rear_setback",
            "measurements": [
                {
                    "measurement_type": "rear_setback_conditional",
                    "value": "6m minimum OR 0.5 times building height",
                    "unit": "metres",
                    "context": "conditional minimum with height calculation",
                    "confidence": 0.88
                }
            ],
            "rule_classification": {
                "tier": 1,
                "enforcement_level": "MANDATORY",
                "linguistic_confidence": 0.90,
                "prescriptive_indicators": ["must be", "minimum"],
                "compliance_message_type": "MUST_COMPLY"
            },
            "source_grounding": {
                "extraction_text": "Rear setbacks must be 6m minimum OR 0.5 times building height, whichever is greater.",
                "source_location": "Chapter F Part 1 Section 4.3.1",
                "source_page": 43,
                "confidence": 0.88,
                "highlighted_spans": [[0, 85]]
            },
            "overall_confidence": 0.88,
            "rule_complexity": "CONDITIONAL"
        },
        {
            "rule_id": "ASHFIELD_FRONT_SETBACK_001",
            "rule_text": "Front setbacks shall align with the existing streetscape pattern.",
            "rule_type": "front_setback",
            "measurements": [
                {
                    "measurement_type": "front_setback_pattern",
                    "value": "streetscape_alignment",
                    "unit": "pattern",
                    "context": "existing streetscape alignment",
                    "confidence": 0.85
                }
            ],
            "rule_classification": {
                "tier": 2,
                "enforcement_level": "RECOMMENDED",
                "linguistic_confidence": 0.85,
                "prescriptive_indicators": ["shall align"],
                "compliance_message_type": "SHOULD_ALIGN"
            },
            "source_grounding": {
                "extraction_text": "Front setbacks shall align with the existing streetscape pattern.",
                "source_location": "Chapter F Part 1 Section 4.2.1",
                "source_page": 41,
                "confidence": 0.85,
                "highlighted_spans": [[0, 66]]
            },
            "overall_confidence": 0.85,
            "rule_complexity": "PATTERN_BASED"
        }
    ]
    
    # Create Leichhardt demo rules (similar but different values)
    leichhardt_rules = [
        {
            "rule_id": "LEICHHARDT_SIDE_SETBACK_001",
            "rule_text": "Side setbacks shall be 1m minimum for dwelling houses in R2 zones.",
            "rule_type": "side_setback",
            "measurements": [
                {
                    "measurement_type": "side_setback",
                    "value": 1.0,
                    "unit": "metres",
                    "context": "minimum requirement",
                    "confidence": 0.90
                }
            ],
            "rule_classification": {
                "tier": 1,
                "enforcement_level": "MANDATORY",
                "linguistic_confidence": 0.92,
                "prescriptive_indicators": ["shall be", "minimum"],
                "compliance_message_type": "MUST_COMPLY"
            },
            "source_grounding": {
                "extraction_text": "Side setbacks shall be 1m minimum for dwelling houses in R2 zones.",
                "source_location": "Chapter F Part 1 Section 4.3.2",
                "source_page": 45,
                "confidence": 0.93,
                "highlighted_spans": [[0, 70]]
            },
            "overall_confidence": 0.93,
            "rule_complexity": "SIMPLE"
        },
        {
            "rule_id": "LEICHHARDT_REAR_SETBACK_001", 
            "rule_text": "Rear setbacks must be 8m minimum for dwelling houses in R2 zones.",
            "rule_type": "rear_setback",
            "measurements": [
                {
                    "measurement_type": "rear_setback",
                    "value": 8.0,
                    "unit": "metres",
                    "context": "minimum requirement",
                    "confidence": 0.88
                }
            ],
            "rule_classification": {
                "tier": 1,
                "enforcement_level": "MANDATORY",
                "linguistic_confidence": 0.90,
                "prescriptive_indicators": ["must be", "minimum"],
                "compliance_message_type": "MUST_COMPLY"
            },
            "source_grounding": {
                "extraction_text": "Rear setbacks must be 8m minimum for dwelling houses in R2 zones.",
                "source_location": "Chapter F Part 1 Section 4.3.1",
                "source_page": 43,
                "confidence": 0.88,
                "highlighted_spans": [[0, 65]]
            },
            "overall_confidence": 0.88,
            "rule_complexity": "SIMPLE"
        },
        {
            "rule_id": "LEICHHARDT_FRONT_SETBACK_001",
            "rule_text": "Front setbacks shall be 5m minimum or align with existing streetscape pattern.",
            "rule_type": "front_setback",
            "measurements": [
                {
                    "measurement_type": "front_setback",
                    "value": 5.0,
                    "unit": "metres",
                    "context": "minimum or streetscape alignment",
                    "confidence": 0.85
                }
            ],
            "rule_classification": {
                "tier": 1,
                "enforcement_level": "MANDATORY",
                "linguistic_confidence": 0.85,
                "prescriptive_indicators": ["shall be", "minimum"],
                "compliance_message_type": "MUST_COMPLY"
            },
            "source_grounding": {
                "extraction_text": "Front setbacks shall be 5m minimum or align with existing streetscape pattern.",
                "source_location": "Chapter F Part 1 Section 4.2.1",
                "source_page": 41,
                "confidence": 0.85,
                "highlighted_spans": [[0, 78]]
            },
            "overall_confidence": 0.85,
            "rule_complexity": "CONDITIONAL"
        }
    ]

    # Create unified data structure
    unified_data = {
        "Ashfield": {
            "area": "Ashfield",
            "document_path": "docs/dcps/INNERWEST/Chapter E2 Haberfield Neighbourhood.pdf",
            "source_groundings": [rule["source_grounding"] for rule in demo_rules],
            "knowledge_triples": [
                ["side_setback", "has_minimum_distance", "0.9m"],
                ["rear_setback", "calculated_as", "max(6m, 0.5*height)"],
                ["front_setback", "aligns_with", "streetscape_pattern"],
                ["dwelling_house", "applies_in", "R2_zone"],
                ["setback", "is_type_of", "building_control"]
            ],
            "concept_hierarchy": {
                "setbacks": ["side_setback", "rear_setback", "front_setback"],
                "zones": ["R2", "residential_low_density"],
                "development_types": ["dwelling_house", "secondary_dwelling"]
            },
            "multimodal_context": {
                "tables": [
                    {
                        "content": "Setback requirements table with minimum distances",
                        "type": "regulatory_table"
                    }
                ],
                "visual_elements": {
                    "description": "Setback diagram showing minimum distances from boundaries",
                    "type": "diagram_or_map"
                },
                "setback_visuals": "Diagram showing 0.9m side setback measurement",
                "zoning_maps": "R2 zone boundaries and applicable areas"
            },
            "graph_relationships": [
                {
                    "type": "spatial_relationship",
                    "content": "Setback measurements relative to property boundaries"
                }
            ],
            "enhanced_rules": demo_rules,
            "processing_metadata": {
                "timestamp": datetime.now().isoformat(),
                "processors_used": ["LightRAG", "LangExtract", "AutoSchemaKG"],
                "documents_processed": 4,
                "extraction_method": "unified_triple_semantic"
            }
        },
        "Leichhardt": {
            "area": "Leichhardt",
            "document_path": "docs/dcps/INNERWEST/Chapter F1 Leichhardt Local Area.pdf",
            "source_groundings": [rule["source_grounding"] for rule in leichhardt_rules],
            "knowledge_triples": [
                ["side_setback", "has_minimum_distance", "1.0m"],
                ["rear_setback", "has_minimum_distance", "8.0m"],
                ["front_setback", "has_minimum_distance", "5.0m"],
                ["dwelling_house", "applies_in", "R2_zone"],
                ["setback", "is_type_of", "building_control"]
            ],
            "concept_hierarchy": {
                "setbacks": ["side_setback", "rear_setback", "front_setback"],
                "zones": ["R2", "residential_low_density"],
                "development_types": ["dwelling_house", "secondary_dwelling"]
            },
            "multimodal_context": {
                "tables": [
                    {
                        "content": "Setback requirements table for Leichhardt area",
                        "type": "regulatory_table"
                    }
                ],
                "visual_elements": {
                    "description": "Setback diagram showing minimum distances for Leichhardt",
                    "type": "diagram_or_map"
                },
                "setback_visuals": "Diagram showing 1m side, 8m rear, 5m front setbacks",
                "zoning_maps": "R2 zone boundaries in Leichhardt local area"
            },
            "graph_relationships": [
                {
                    "type": "spatial_relationship",
                    "content": "Setback measurements relative to property boundaries for Leichhardt"
                }
            ],
            "enhanced_rules": leichhardt_rules,
            "processing_metadata": {
                "timestamp": datetime.now().isoformat(),
                "processors_used": ["LightRAG", "LangExtract", "AutoSchemaKG"],
                "documents_processed": 3,
                "extraction_method": "unified_triple_semantic"
            }
        }
    }
    
    # Save unified extraction
    unified_file = unified_dir / "unified_extraction.json"
    with open(unified_file, 'w') as f:
        json.dump(unified_data, f, indent=2, default=str)
    
    # Save Ashfield-specific file
    ashfield_file = unified_dir / "ashfield_unified.json"
    with open(ashfield_file, 'w') as f:
        json.dump(unified_data["Ashfield"], f, indent=2, default=str)
    
    # Save Leichhardt-specific file
    leichhardt_file = unified_dir / "leichhardt_unified.json"
    with open(leichhardt_file, 'w') as f:
        json.dump(unified_data["Leichhardt"], f, indent=2, default=str)
    
    print(f"Created unified extraction: {unified_file}")
    print(f"Created Ashfield data: {ashfield_file}")
    print(f"Created Leichhardt data: {leichhardt_file}")
    
    # Create cache files
    create_cache_files(unified_data, cache_dir)
    
    return unified_data

def create_cache_files(unified_data, cache_dir):
    """Create optimized cache files"""
    
    # Rule index
    rule_index = {}
    area_index = {}
    
    for area_name, area_data in unified_data.items():
        # Build rule index
        for rule in area_data.get("enhanced_rules", []):
            rule_index[rule["rule_id"]] = {
                **rule,
                "area": area_name,
                "quick_access": {
                    "text": rule["rule_text"],
                    "type": rule["rule_type"],
                    "tier": rule["rule_classification"]["tier"],
                    "measurements": rule["measurements"]
                }
            }
        
        # Build area index
        area_index[area_name] = {
            "rules": area_data.get("enhanced_rules", []),
            "documents": area_data.get("document_path", ""),
            "setbacks": extract_setback_summary(area_data),
            "statistics": {
                "total_rules": len(area_data.get("enhanced_rules", [])),
                "mandatory_rules": len([r for r in area_data.get("enhanced_rules", []) if r["rule_classification"]["tier"] == 1]),
                "source_groundings": len(area_data.get("source_groundings", [])),
                "knowledge_triples": len(area_data.get("knowledge_triples", []))
            }
        }
    
    # Query index with pre-computed answers
    query_index = {
        "can_build_duplex": {
            "question": "Can I build a duplex on this property?",
            "answers": {
                "Ashfield": [
                    {
                        "rule": "Dual occupancy is permissible in R2 zones subject to setback requirements",
                        "source": "Chapter F Part 1 Section 2.1",
                        "tier": 1
                    }
                ]
            }
        },
        "minimum_setbacks": {
            "question": "What are the minimum setback requirements?",
            "answers": {
                "Ashfield": {
                    "side": {"value": 0.9, "unit": "metres", "source": "Chapter F Part 1 Section 4.3.2"},
                    "rear": {"value": 6.0, "unit": "metres", "source": "Chapter F Part 1 Section 4.3.1"},
                    "front": {"value": "streetscape_alignment", "unit": "pattern", "source": "Chapter F Part 1 Section 4.2.1"}
                }
            }
        }
    }
    
    # Save cache files
    cache_files = {
        "rule_index": rule_index,
        "area_index": area_index,
        "query_index": query_index,
        "master_index": {
            "created_at": datetime.now().isoformat(),
            "version": "1.0.0-demo",
            "indices": ["rule_index", "area_index", "query_index"],
            "statistics": {
                "total_rules": len(rule_index),
                "total_areas": len(area_index),
                "total_queries": len(query_index)
            }
        }
    }
    
    for name, data in cache_files.items():
        cache_file = cache_dir / f"{name}.json"
        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"Created cache: {cache_file}")

def extract_setback_summary(area_data):
    """Extract setback summary from area data"""
    summary = {"front": None, "side": None, "rear": None}
    
    for rule in area_data.get("enhanced_rules", []):
        if rule["rule_type"] == "front_setback":
            summary["front"] = "streetscape_alignment"
        elif rule["rule_type"] == "side_setback" and rule["measurements"]:
            summary["side"] = rule["measurements"][0]["value"]
        elif rule["rule_type"] == "rear_setback":
            summary["rear"] = "6m minimum OR 0.5 times height"
    
    return summary

if __name__ == "__main__":
    print("Creating LightRAG Demo Data...")
    print("=" * 50)
    
    unified_data = create_demo_unified_data()
    
    print("\nDemo data created successfully!")
    print(f"Areas: {list(unified_data.keys())}")
    print(f"Total rules: {sum(len(area.get('enhanced_rules', [])) for area in unified_data.values())}")
    print("\nYou can now test the integration with:")
    print("  - npm run dev")
    print("  - Visit http://localhost:3001/property/enhanced")
    print("  - Test with address: 3 Wilkinson Ln, Telopea NSW 2117")