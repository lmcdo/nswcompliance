"""
Spatial mapping functions for determining former council areas
Based on the example from examples/regulatory-engine/setback_processor.py
"""

from typing import Dict
from ..models import FormerCouncilArea

def determine_former_council_area(geometry: Dict[str, float]) -> str:
    """
    Determines which former council area a property is in
    Uses spatial data to map to Ashfield, Leichhardt, or Marrickville
    
    Args:
        geometry: Dictionary with x, y coordinates
        
    Returns:
        Former council area name as string
    """
    # Extract coordinates
    x = geometry.get("x", 0)
    y = geometry.get("y", 0)
    
    # These are approximate spatial boundaries for Inner West Council
    # In production, this would use actual GIS shapefiles from NSW Planning Portal
    ASHFIELD_BOUNDS = {
        "min_x": 16820000, 
        "max_x": 16830000, 
        "min_y": -4010000, 
        "max_y": -4009000
    }
    
    LEICHHARDT_BOUNDS = {
        "min_x": 16810000, 
        "max_x": 16820000, 
        "min_y": -4010000, 
        "max_y": -4009000
    }
    
    MARRICKVILLE_BOUNDS = {
        "min_x": 16810000, 
        "max_x": 16820000, 
        "min_y": -4011000, 
        "max_y": -4010000
    }
    
    # Check Ashfield bounds
    if (ASHFIELD_BOUNDS["min_x"] <= x <= ASHFIELD_BOUNDS["max_x"] and 
        ASHFIELD_BOUNDS["min_y"] <= y <= ASHFIELD_BOUNDS["max_y"]):
        return FormerCouncilArea.ASHFIELD.value
    
    # Check Leichhardt bounds  
    if (LEICHHARDT_BOUNDS["min_x"] <= x <= LEICHHARDT_BOUNDS["max_x"] and 
        LEICHHARDT_BOUNDS["min_y"] <= y <= LEICHHARDT_BOUNDS["max_y"]):
        return FormerCouncilArea.LEICHHARDT.value
    
    # Default to Marrickville
    return FormerCouncilArea.MARRICKVILLE.value


def get_council_area_enum(area_string: str) -> FormerCouncilArea:
    """
    Convert area string to enum
    
    Args:
        area_string: Area name as string
        
    Returns:
        FormerCouncilArea enum value
    """
    area_map = {
        "Ashfield": FormerCouncilArea.ASHFIELD,
        "Leichhardt": FormerCouncilArea.LEICHHARDT, 
        "Marrickville": FormerCouncilArea.MARRICKVILLE
    }
    
    return area_map.get(area_string, FormerCouncilArea.MARRICKVILLE)