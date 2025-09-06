"""
Data models for NSW Development Compliance processing pipeline
Following the structure from examples/regulatory-engine/output.json
"""

from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, List, Union
from enum import Enum
import json

class FormerCouncilArea(str, Enum):
    ASHFIELD = "Ashfield"
    LEICHHARDT = "Leichhardt"  
    MARRICKVILLE = "Marrickville"

class DocumentSource(BaseModel):
    filename: str
    chapter_section: str  # "Chapter F", "Part C Section 2", etc.
    full_path: str

class SetbackRule(BaseModel):
    """Individual setback rule with source tracking"""
    distance: Optional[float] = None
    height_limit: Optional[float] = None
    min_distance: Optional[float] = None
    source: str  # Full document and clause reference
    source_file: str  # Local filename for reference
    applicable_zones: Optional[List[str]] = None
    conditions: Optional[str] = None

class SetbackRules(BaseModel):
    """Complete setback rules for rear, side, and front"""
    rear: Optional[SetbackRule] = None
    side: Optional[SetbackRule] = None
    front: Optional[SetbackRule] = None

class ProcessedCouncilArea(BaseModel):
    """Processed data for a single former council area"""
    name: FormerCouncilArea
    dcp_version: str  # "Ashfield DCP 2016", etc.
    processed_files: List[str]  # Track which files were processed
    setbacks: SetbackRules
    extraction_confidence: float  # 0-1 confidence score

class InnerWestSetbacks(BaseModel):
    """Final output structure matching examples/regulatory-engine/output.json"""
    lga: str = "INNER WEST COUNCIL"
    areas: Dict[str, ProcessedCouncilArea]  # Use string keys for JSON compatibility
    processing_metadata: Dict[str, Union[str, int, float]]

    def to_api_format(self) -> Dict:
        """Convert to the format expected by the API route"""
        api_format = {
            "lga": self.lga,
            "areas": {}
        }
        
        for area_name, area_data in self.areas.items():
            # Convert to the simpler format expected by existing API
            api_format["areas"][area_name] = {
                "setbacks": {
                    "rear": None,
                    "side": None, 
                    "front": None
                }
            }
            
            # Map setback rules to API format
            if area_data.setbacks.rear:
                api_format["areas"][area_name]["setbacks"]["rear"] = {
                    "distance": area_data.setbacks.rear.distance,
                    "height_limit": area_data.setbacks.rear.height_limit,
                    "source": area_data.setbacks.rear.source,
                    "source_link": f"file:///{area_data.setbacks.rear.source_file}"  # Local file reference
                }
                
            if area_data.setbacks.side:
                api_format["areas"][area_name]["setbacks"]["side"] = {
                    "height_limit": area_data.setbacks.side.height_limit,
                    "source": area_data.setbacks.side.source,
                    "source_link": f"file:///{area_data.setbacks.side.source_file}"
                }
                
            if area_data.setbacks.front:
                api_format["areas"][area_name]["setbacks"]["front"] = {
                    "min_distance": area_data.setbacks.front.min_distance,
                    "source": area_data.setbacks.front.source,
                    "source_link": f"file:///{area_data.setbacks.front.source_file}"
                }
        
        return api_format