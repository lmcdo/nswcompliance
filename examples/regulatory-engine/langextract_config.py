"""
LangExtract configuration for regulatory setback extraction
Provides precise source grounding for compliance authority citations
"""
import os
import langextract as lx
import textwrap
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

def create_setback_extraction_config() -> Dict[str, Any]:
 """
 Create LangExtract configuration for setback rule extraction
 Returns prompts, examples, and model settings
 """
 
 # Define the extraction prompt for regulatory setback rules
 prompt = textwrap.dedent("""\
 Extract setback rules from planning documents in order of appearance.
 Use exact text for extractions. Do not paraphrase or overlap entities.
 Focus on specific measurements, conditions, and applicability.
 Include regulatory context and calculation methods.
 """)
 
 # Provide high-quality examples to guide the model
 examples = [
 lx.data.ExampleData(
 text="Side setbacks shall be 0.9m minimum OR 0.5 times building height, whichever is greater",
 extractions=[
 lx.data.Extraction(
 extraction_class="setback_rule",
 extraction_text="Side setbacks shall be 0.9m minimum OR 0.5 times building height, whichever is greater",
 attributes={
 "setback_type": "side",
 "measurement_type": "conditional", 
 "minimum_distance": "0.9m",
 "alternative_calculation": "0.5 times building height",
 "selection_rule": "whichever is greater"
 }
 ),
 lx.data.Extraction(
 extraction_class="measurement",
 extraction_text="0.9m minimum",
 attributes={
 "value": 0.9,
 "unit": "metres", 
 "constraint": "minimum"
 }
 ),
 lx.data.Extraction(
 extraction_class="calculation",
 extraction_text="0.5 times building height",
 attributes={
 "formula": "0.5 * building_height",
 "multiplier": 0.5,
 "variable": "building_height"
 }
 )
 ]
 ),
 lx.data.ExampleData(
 text="For driveway access, a 3m wide side setback is required",
 extractions=[
 lx.data.Extraction(
 extraction_class="setback_rule",
 extraction_text="For driveway access, a 3m wide side setback is required",
 attributes={
 "setback_type": "side",
 "measurement_type": "fixed",
 "distance": "3m",
 "width_specification": "wide",
 "condition": "driveway access",
 "requirement_type": "required"
 }
 ),
 lx.data.Extraction(
 extraction_class="condition",
 extraction_text="driveway access",
 attributes={
 "condition_type": "use_purpose",
 "value": "driveway access"
 }
 )
 ]
 ),
 lx.data.ExampleData(
 text="Buildings must not exceed a height of 8m within 3m of the rear boundary",
 extractions=[
 lx.data.Extraction(
 extraction_class="setback_rule", 
 extraction_text="Buildings must not exceed a height of 8m within 3m of the rear boundary",
 attributes={
 "setback_type": "rear",
 "measurement_type": "conditional",
 "distance": "3m",
 "height_limit": "8m",
 "boundary_type": "rear",
 "constraint": "height restriction"
 }
 ),
 lx.data.Extraction(
 extraction_class="height_restriction",
 extraction_text="must not exceed a height of 8m",
 attributes={
 "constraint_type": "maximum",
 "value": 8,
 "unit": "metres",
 "applies_within": "3m of rear boundary"
 }
 )
 ]
 )
 ]
 
 return {
 "prompt": prompt,
 "examples": examples,
 "model_config": {
 "model_id": "gemini-2.5-flash", # Recommended for regulatory text
 "api_key": os.environ.get('OPENAI_API_KEY'), # Will use OpenAI for now
 "extraction_passes": 2, # Multiple passes for higher recall
 "max_workers": 4, # Parallel processing
 "max_char_buffer": 800 # Smaller contexts for regulatory precision
 }
 }

def extract_setback_rules_with_citations(dcp_text: str, area: str = "Unknown") -> Dict[str, Any]:
 """
 Extract setback rules using LangExtract with precise source grounding
 
 Args:
 dcp_text: The regulatory text to extract from
 area: The council area (for reference)
 
 Returns:
 Dictionary with extracted rules and source citations
 """
 config = create_setback_extraction_config()
 
 # Use OpenAI for now (will switch to Gemini when API key is available)
 result = lx.extract(
 text_or_documents=dcp_text,
 prompt_description=config["prompt"], 
 examples=config["examples"],
 model_id="gpt-4o", # Using OpenAI since we have the key
 api_key=config["model_config"]["api_key"],
 extraction_passes=config["model_config"]["extraction_passes"],
 max_workers=config["model_config"]["max_workers"],
 max_char_buffer=config["model_config"]["max_char_buffer"],
 fence_output=True, # Required for OpenAI
 use_schema_constraints=False # OpenAI doesn't support schema constraints
 )
 
 return {
 "area": area,
 "extraction_method": "LangExtract_v1.0.8",
 "model_used": "gpt-4o", 
 "source_grounded": True,
 "result": result,
 "total_extractions": len(result.extractions) if hasattr(result, 'extractions') else 0
 }

def test_langextract_setup():
 """
 Test LangExtract configuration with sample regulatory text
 """
 sample_text = """
 Side setbacks shall be 0.9m minimum OR 0.5 times building height, whichever is greater. 
 For driveway access, a 3m wide side setback is required. Nil side setbacks are not permitted.
 Buildings must not exceed a height of 8m within 3m of the rear boundary.
 """
 
 print("Testing LangExtract Setup...")
 print(f"Sample text: {sample_text.strip()}")
 
 try:
 result = extract_setback_rules_with_citations(sample_text, "Test_Area")
 print("Extraction successful!")
 print(f" - Method: {result['extraction_method']}")
 print(f" - Model: {result['model_used']}")
 print(f" - Total extractions: {result['total_extractions']}")
 print(f" - Source grounded: {result['source_grounded']}")
 
 return True
 
 except Exception as e:
 print(f"Extraction failed: {e}")
 return False

if __name__ == "__main__":
 # Test the configuration
 success = test_langextract_setup()
 if success:
 print("\nLangExtract configuration ready for regulatory extraction!")
 else:
 print("\nLangExtract configuration needs debugging")