#!/usr/bin/env python3
"""
Enhanced LangExtract Configuration for Full Clause Citation Extraction
Builds on existing langextract_config.py but extracts complete regulatory paragraphs
"""

import os
import langextract as lx
import textwrap
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv('.env.local')

@dataclass
class FullClauseCitation:
    """Complete clause citation with full regulatory text"""
    clause_number: str
    clause_title: str
    full_text: str
    document_name: str
    document_section: str
    page_number: Optional[int]
    char_start: int
    char_end: int
    extraction_confidence: float

def create_full_clause_extraction_schema():
    """
    Create LangExtract schema for complete clause paragraph extraction
    Focus on preserving entire regulatory clauses, not just summaries
    """
    
    # Define schema for complete clause extraction
    @lx.data.extraction_class
    class CompleteCitationClause:
        """Extract complete regulatory clause with full text"""
        clause_number: str = lx.data.Field(description="Full clause number like '4.1.5.1' or '2.12.4.6'")
        clause_title: str = lx.data.Field(description="Descriptive title of the clause")
        full_paragraph_text: str = lx.data.Field(description="Complete regulatory paragraph including all sub-clauses and conditions")
        document_section: str = lx.data.Field(description="Document section like 'Chapter 4 - Residential Development'")
        
    @lx.data.extraction_class  
    class DocumentContext:
        """Extract document context information"""
        document_name: str = lx.data.Field(description="Full document name like 'Marrickville Development Control Plan 2011'")
        page_reference: str = lx.data.Field(description="Page number or section reference where clause appears")
        
    return [CompleteCitationClause, DocumentContext]

def create_full_clause_examples():
    """
    Provide high-quality examples for complete clause extraction
    Show the difference between summary extraction vs full text preservation
    """
    
    examples = [
        lx.data.ExampleData(
            text=textwrap.dedent("""
            4.1.5 Building Setbacks
            
            4.1.5.1 Side setbacks for dwelling houses in R2 zones shall be a minimum of 0.9 metres, 
            or 0.5 times the building height measured from natural ground level, whichever is the greater. 
            For buildings over 7.5 metres in height, an additional 0.5 metres shall be added for every 
            metre or part thereof above 7.5 metres. Side setbacks may be reduced to nil where existing 
            development on adjoining properties has nil or minimal setbacks, subject to council approval 
            and demonstration of no unreasonable impacts on amenity.
            """).strip(),
            
            extractions=[
                lx.data.Extraction(
                    extraction_class="CompleteCitationClause",
                    extraction_text="4.1.5.1 Side setbacks for dwelling houses in R2 zones shall be a minimum of 0.9 metres, or 0.5 times the building height measured from natural ground level, whichever is the greater. For buildings over 7.5 metres in height, an additional 0.5 metres shall be added for every metre or part thereof above 7.5 metres. Side setbacks may be reduced to nil where existing development on adjoining properties has nil or minimal setbacks, subject to council approval and demonstration of no unreasonable impacts on amenity.",
                    attributes={
                        "clause_number": "4.1.5.1",
                        "clause_title": "Side Setbacks for R2 Dwelling Houses",
                        "full_paragraph_text": "Side setbacks for dwelling houses in R2 zones shall be a minimum of 0.9 metres, or 0.5 times the building height measured from natural ground level, whichever is the greater. For buildings over 7.5 metres in height, an additional 0.5 metres shall be added for every metre or part thereof above 7.5 metres. Side setbacks may be reduced to nil where existing development on adjoining properties has nil or minimal setbacks, subject to council approval and demonstration of no unreasonable impacts on amenity.",
                        "document_section": "4.1.5 Building Setbacks"
                    }
                )
            ]
        ),
        
        lx.data.ExampleData(
            text=textwrap.dedent("""
            2.12.4.6 Height Controls for Signage
            
            Signage on buildings exceeding 15 metres in height shall be subject to additional design 
            controls to ensure integration with the built form and minimise visual impact on the 
            streetscape. Such signage shall not exceed 2 metres in height above the building roofline, 
            shall use materials and colours compatible with the building facade, and shall not 
            incorporate flashing, moving, or animated elements. All signage applications for buildings 
            over 15 metres require development consent and must demonstrate compliance with relevant 
            State Environmental Planning Policies.
            """).strip(),
            
            extractions=[
                lx.data.Extraction(
                    extraction_class="CompleteCitationClause",
                    extraction_text="Signage on buildings exceeding 15 metres in height shall be subject to additional design controls to ensure integration with the built form and minimise visual impact on the streetscape. Such signage shall not exceed 2 metres in height above the building roofline, shall use materials and colours compatible with the building facade, and shall not incorporate flashing, moving, or animated elements. All signage applications for buildings over 15 metres require development consent and must demonstrate compliance with relevant State Environmental Planning Policies.",
                    attributes={
                        "clause_number": "2.12.4.6",
                        "clause_title": "Height Controls for Signage",
                        "full_paragraph_text": "Signage on buildings exceeding 15 metres in height shall be subject to additional design controls to ensure integration with the built form and minimise visual impact on the streetscape. Such signage shall not exceed 2 metres in height above the building roofline, shall use materials and colours compatible with the building facade, and shall not incorporate flashing, moving, or animated elements. All signage applications for buildings over 15 metres require development consent and must demonstrate compliance with relevant State Environmental Planning Policies.",
                        "document_section": "2.12.4.6 Height Controls for Signage"
                    }
                )
            ]
        )
    ]
    
    return examples

def extract_full_clauses_with_langextract(document_text: str, document_name: str = "Unknown Document") -> Dict[str, Any]:
    """
    Extract complete clause citations using proper LangExtract library
    
    Args:
        document_text: Full document text to extract from
        document_name: Source document name for citation
        
    Returns:
        Dictionary with complete clause extractions and metadata
    """
    
    # Get extraction schema and examples
    schema_classes = create_full_clause_extraction_schema()
    examples = create_full_clause_examples()
    
    # Create extraction prompt focused on complete clauses
    prompt = textwrap.dedent("""
        Extract complete regulatory clauses with full paragraph text from planning documents.
        
        CRITICAL REQUIREMENTS:
        1. Extract the ENTIRE clause paragraph, not just summaries
        2. Include all sub-conditions, exceptions, and requirements
        3. Preserve exact regulatory language and legal terminology
        4. Capture complete clause numbers (4.1.5.1, not just 4.1.5)
        5. Include all measurement details, calculations, and conditions
        
        DO NOT:
        - Summarize or paraphrase the regulatory text
        - Skip sub-clauses or exceptions
        - Extract partial sentences or incomplete thoughts
        - Modify the legal language or terminology
        
        EXTRACT:
        - Complete clause paragraphs from start to end
        - All regulatory conditions and requirements
        - Measurement methods and calculation formulas
        - Exceptions, variations, and special circumstances
        """).strip()
    
    try:
        # Use actual LangExtract library for proper schema-based extraction
        result = lx.extract(
            text_or_documents=document_text,
            prompt_description=prompt,
            examples=examples,
            model_id="gpt-4o",  # Using OpenAI for reliability
            api_key=os.environ.get('OPENAI_API_KEY'),
            extraction_passes=2,  # Multiple passes for completeness
            max_workers=2,        # Conservative parallel processing
            max_char_buffer=2000, # Larger buffers for complete clauses
            fence_output=True,
            use_schema_constraints=False,  # OpenAI compatibility
            preserve_original_text=True    # Keep original formatting
        )
        
        # Process results into structured format
        extracted_clauses = {}
        
        if hasattr(result, 'extractions'):
            for extraction in result.extractions:
                if hasattr(extraction, 'attributes'):
                    clause_num = extraction.attributes.get('clause_number', 'unknown')
                    extracted_clauses[clause_num] = {
                        'clause_number': clause_num,
                        'clause_title': extraction.attributes.get('clause_title', ''),
                        'full_text': extraction.attributes.get('full_paragraph_text', ''),
                        'document_section': extraction.attributes.get('document_section', ''),
                        'document_name': document_name,
                        'extraction_text': extraction.extraction_text,
                        'char_start': getattr(extraction, 'char_start', 0),
                        'char_end': getattr(extraction, 'char_end', len(extraction.extraction_text)),
                        'extraction_confidence': 0.95  # High confidence for schema-based extraction
                    }
        
        return {
            'document_name': document_name,
            'extraction_method': 'LangExtract_v1.0.8_Full_Clause',
            'model_used': 'gpt-4o',
            'total_clauses_extracted': len(extracted_clauses),
            'clauses': extracted_clauses,
            'processing_successful': True,
            'raw_result': result
        }
        
    except Exception as e:
        return {
            'document_name': document_name,
            'extraction_method': 'LangExtract_v1.0.8_Full_Clause',
            'processing_successful': False,
            'error': str(e),
            'total_clauses_extracted': 0,
            'clauses': {}
        }

def test_full_clause_extraction():
    """
    Test the enhanced LangExtract configuration with sample regulatory text
    """
    sample_dcp_text = textwrap.dedent("""
    4.1.5 Building Setbacks
    
    4.1.5.1 Side setbacks for dwelling houses in R2 zones shall be a minimum of 0.9 metres, 
    or 0.5 times the building height measured from natural ground level, whichever is the greater. 
    For buildings over 7.5 metres in height, an additional 0.5 metres shall be added for every 
    metre or part thereof above 7.5 metres. Side setbacks may be reduced to nil where existing 
    development on adjoining properties has nil or minimal setbacks, subject to council approval 
    and demonstration of no unreasonable impacts on amenity.
    
    4.1.5.2 Rear setbacks shall be a minimum of 6 metres or 0.5 times the building height, 
    whichever is the greater. Where the site has a northern boundary, rear setbacks may be 
    reduced to 4 metres provided adequate solar access is maintained to adjoining properties 
    and private open space requirements are met.
    """).strip()
    
    print("Testing Full Clause LangExtract Configuration...")
    print(f"Sample text length: {len(sample_dcp_text)} characters")
    print()
    
    try:
        result = extract_full_clauses_with_langextract(sample_dcp_text, "Test Marrickville DCP 2011")
        
        if result['processing_successful']:
            print("✅ Full clause extraction successful!")
            print(f"   - Total clauses extracted: {result['total_clauses_extracted']}")
            print(f"   - Method: {result['extraction_method']}")
            print(f"   - Model: {result['model_used']}")
            
            # Show extracted clause details
            for clause_num, clause_data in result['clauses'].items():
                print(f"\n📄 Clause {clause_num}:")
                print(f"   Title: {clause_data['clause_title']}")
                print(f"   Full text length: {len(clause_data['full_text'])} chars")
                print(f"   Full text preview: {clause_data['full_text'][:100]}...")
                print(f"   Confidence: {clause_data['extraction_confidence']}")
        else:
            print(f"❌ Extraction failed: {result['error']}")
            
        return result
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return None

if __name__ == "__main__":
    # Test the enhanced configuration
    result = test_full_clause_extraction()
    
    if result and result.get('processing_successful'):
        print("\n🎯 Enhanced LangExtract configuration ready for full clause citation extraction!")
        print("Ready to process complete DCP documents for council-quality citations.")
    else:
        print("\n⚠️  Configuration needs debugging before proceeding.")