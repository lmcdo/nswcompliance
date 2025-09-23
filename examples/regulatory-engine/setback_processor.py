import os
import re
import json
from rag_anything import RAG
from autoschemakg import AutoSchemaKG

def extract_setback_rules(area: str, dcp_text: str) -> dict:
 """
 Extracts setback rules from DCP text using RAG-Anything and AutoSchemaKG
 Handles the fact that Inner West Council has 3 operative DCPs
 """
 # Process DCP text to find setback rules
 rag = RAG(chunk_size=500, chunk_overlap=50)
 chunks = rag.chunk_text(dcp_text)
 
 setback_rules = {
 "rear": None,
 "side": None,
 "front": None
 }
 
 # Pattern to find rear setback rules
 rear_pattern = r'within\s*(\d+\.?\d*)\s*m.*?must\s*not\s*exceed\s*(\d+\.?\d*)\s*m'
 
 for chunk in chunks:
 # Extract rear setback rules
 rear_match = re.search(rear_pattern, chunk, re.IGNORECASE)
 if rear_match:
 distance = float(rear_match.group(1))
 height_limit = float(rear_match.group(2))
 setback_rules["rear"] = {
 "distance": distance,
 "height_limit": height_limit,
 "source": f"{area} DCP 2014 Section X.X.X",
 "source_link": f"https://www.innerwest.nsw.gov.au/planning-building/planning-documents/dcp-2014#section-x.x.x"
 }
 break
 
 # Pattern for side setbacks
 side_pattern = r'side\s*setback.*?must\s*not\s*exceed\s*(\d+\.?\d*)\s*m'
 for chunk in chunks:
 side_match = re.search(side_pattern, chunk, re.IGNORECASE)
 if side_match:
 height_limit = float(side_match.group(1))
 setback_rules["side"] = {
 "height_limit": height_limit,
 "source": f"{area} LEP 2014 Clause X.X",
 "source_link": f"https://www.legislation.nsw.gov.au/#/view/EPI/2014/389"
 }
 break
 
 # Pattern for front setbacks
 front_pattern = r'front\s*setback.*?(\d+\.?\d*)\s*m'
 for chunk in chunks:
 front_match = re.search(front_pattern, chunk, re.IGNORECASE)
 if front_match:
 min_distance = float(front_match.group(1))
 setback_rules["front"] = {
 "min_distance": min_distance,
 "source": f"{area} LEP 2014 Clause X.X",
 "source_link": f"https://www.legislation.nsw.gov.au/#/view/EPI/2014/389"
 }
 break
 
 return setback_rules

def determine_former_council_area(geometry: dict) -> str:
 """
 Determines which former council area a property is in
 Uses spatial data to map to Ashfield, Leichhardt, or Marrickville
 """
 # In reality, this would use actual spatial calculations
 # This is a simplified example for MVP
 x = geometry.get("x", 0)
 y = geometry.get("y", 0)
 
 # These would be actual spatial boundaries
 ASHFIELD_BOUNDS = {"min_x": 16820000, "max_x": 16830000, "min_y": -4010000, "max_y": -4009000}
 LEICHHARDT_BOUNDS = {"min_x": 16810000, "max_x": 16820000, "min_y": -4010000, "max_y": -4009000}
 MARRICKVILLE_BOUNDS = {"min_x": 16810000, "max_x": 16820000, "min_y": -4011000, "max_y": -4010000}
 
 if (ASHFIELD_BOUNDS["min_x"] <= x <= ASHFIELD_BOUNDS["max_x"] and 
 ASHFIELD_BOUNDS["min_y"] <= y <= ASHFIELD_BOUNDS["max_y"]):
 return "Ashfield"
 
 if (LEICHHARDT_BOUNDS["min_x"] <= x <= LEICHHARDT_BOUNDS["max_x"] and 
 LEICHHARDT_BOUNDS["min_y"] <= y <= LEICHHARDT_BOUNDS["max_y"]):
 return "Leichhardt"
 
 return "Marrickville"

def process_inner_west_setbacks():
 """Processes setback rules for all 3 Inner West DCPs"""
 areas = ["Ashfield", "Leichhardt", "Marrickville"]
 results = {}
 
 for area in areas:
 # Load DCP PDF for the area
 dcp_pdf = f'docs/dcps/InnerWest_{area}_DCP_2014.pdf'
 
 # Extract text from PDF
 rag = RAG()
 dcp_text = rag.extract_text(dcp_pdf)
 
 # Extract setback rules
 results[area] = extract_setback_rules(area, dcp_text)
 
 # Save results
 output_path = 'public/regulatory-data/inner-west_setbacks.json'
 with open(output_path, 'w') as f:
 json.dump({
 "lga": "INNER WEST COUNCIL",
 "areas": results
 }, f, indent=2)
 
 print(f"Setback rules processed for Inner West Council. Output saved to {output_path}")

if __name__ == "__main__":
 # Process Inner West Council's 3 DCPs
 process_inner_west_setbacks()