name: "NSW Development Compliance MVP - Inner West Council Focus"
description: |

## Purpose
Implement a deterministic compliance checking system that validates development proposals against NSW planning regulations using RAG-Anything and AutoSchemaKG to process Inner West Council's operative DCPs from the local docs folder. This system extracts exact numeric constraints without AI interpretation and provides a user-friendly Next.js interface.

## Core Principles
1. **Deterministic Processing**: Only extract explicit numeric constraints from regulations
2. **No AI Interpretation**: Pure math on council-published constraints 
3. **Exact Regulatory Citations**: Every rule includes direct reference to document and clause
4. **Build-time Processing**: All PDFs processed during build, not user requests
5. **Local Document Processing**: All documents available in docs/ folder structure

---

## Goal
Create a working NSW Development Compliance MVP that processes Inner West Council's operative DCPs (Ashfield 2016, Leichhardt 2013, Marrickville 2011) from the docs folder to extract setback rules and provides a Next.js frontend for compliance checking.

## Why
- **Regulatory Transparency**: Developers need clear understanding of setback requirements across the 3 former council areas
- **Time Efficiency**: Instant compliance feedback rather than lengthy council consultations  
- **Accuracy**: Eliminate manual interpretation errors with deterministic processing
- **Self-Contained**: All regulatory documents available locally, no external API dependencies

## What
A complete system with:
- Python processing pipeline using RAG-Anything + AutoSchemaKG for comprehensive PDF extraction
- Structured JSON output with exact clause references from local documents
- Next.js frontend with Google Maps address autocomplete and mandatory input validation
- API routes serving pre-processed regulatory data with spatial council area determination
- Support for complex DCP chapter structure across different document formats

### Success Criteria
- [ ] Successfully installs and configures RAG-Anything and AutoSchemaKG libraries
- [ ] Correctly extracts setback rules from all 3 operative DCPs using local PDF files
- [ ] Processes multi-chapter DCP structure (Ashfield: Chapters A-H, Leichhardt: Parts A-G)
- [ ] All extracted rules include exact clause references to local documents
- [ ] Frontend validates all required fields before enabling compliance checking
- [ ] System correctly maps properties to former council areas based on spatial data
- [ ] Compliance results show exact gaps and specific mitigation paths
- [ ] No external API calls for document processing - everything local

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- url: https://github.com/HKUDS/RAG-Anything
  why: Core PDF processing library - study installation and usage patterns
  
- url: https://github.com/HKUST-KnowComp/AutoSchemaKG  
  why: Structured knowledge extraction - understand schema creation and extraction workflow
  
- file: examples/regulatory-engine/setback_processor.py
  why: Working implementation pattern - adapt for real DCP structure and library APIs
  
- file: examples/regulatory-engine/schema.json
  why: AutoSchemaKG schema structure - expand for actual Inner West DCPs
  
- file: examples/regulatory-engine/output.json
  why: Expected JSON output format - maintain consistency
  
- file: .claude/app/api/compliance/setbacks/route.ts
  why: Next.js API route pattern - already functional, needs real data integration
  
- file: .claude/app/property/page.tsx
  why: Frontend component - already debugged and working with Google Maps
  
- file: .claude/compliance readme.md
  why: Critical implementation requirements, UI specifications, compliance logic
  
- file: lib/address-parser.ts
  why: Address parsing utility - already created and working
  
- file: lib/property-data.ts  
  why: Property data service - already created and working
  
- file: lib/regulatory-engine/google-maps.ts
  why: Google Maps integration - already debugged and working
```

### Current Codebase Structure
```bash
compliance-engine/
├── .claude/
│   ├── app/
│   │   ├── api/compliance/setbacks/route.ts    # API endpoint (functional, needs real data)
│   │   └── property/page.tsx                   # Frontend component (debugged and working)
│   └── compliance readme.md                    # Implementation requirements
├── lib/
│   ├── address-parser.ts                       # Address parsing utility (created)
│   ├── property-data.ts                        # Property data service (created)
│   └── regulatory-engine/google-maps.ts        # Google Maps integration (working)
├── docs/                                       # LOCAL DOCUMENTS - NO EXTERNAL CALLS NEEDED
│   ├── lep/
│   │   └── Inner West Local Environmental Plan 2022 - NSW Legislation.pdf
│   ├── dcps/INNERWEST/
│   │   ├── [Ashfield DCP 2016 - Chapters A-H with various amendments]
│   │   ├── leichhardt/
│   │   │   └── [Leichhardt DCP 2013 - Parts 1-18 with sections]
│   │   └── Marrickville/
│   │       └── [Marrickville DCP 2011 - Contents Nov 22.pdf]
│   └── sepps/                                  # SEPPs directory (available for future)
├── examples/
│   └── regulatory-engine/
│       ├── setback_processor.py                # Implementation template
│       ├── schema.json                         # Schema template  
│       └── output.json                         # Expected output format
├── venv_linux/                                 # Python virtual environment (mostly empty)
├── public/regulatory-data/                     # Output directory for processed JSON
└── PRPs/templates/prp_base.md                  # This PRP template
```

### Known Gotchas & Library Requirements
```python
# CRITICAL: RAG-Anything installation from GitHub
# pip install git+https://github.com/HKUDS/RAG-Anything.git
# May have dependency conflicts - install in clean environment first

# CRITICAL: AutoSchemaKG installation from GitHub  
# pip install git+https://github.com/HKUST-KnowComp/AutoSchemaKG.git
# May require specific versions of transformers, torch, etc.

# CRITICAL: Inner West DCPs have completely different structures
# Ashfield 2016: Chapters A-H (Chapter F likely has setbacks)
# Leichhardt 2013: Parts A-G with numbered sections (Part C likely has setbacks)
# Marrickville 2011: Single consolidated document

# CRITICAL: Document file paths are exact and case-sensitive
# Use exact filenames from docs directory listings
# Handle spaces and special characters in filenames properly

# CRITICAL: Virtual environment is nearly empty - need to install everything
# Current packages: pip (22.3), setuptools (65.5.0) - that's it
# Need to install all dependencies from scratch
```

## Implementation Blueprint

### Data Models and Structure

Create robust data models for the document processing pipeline:
```python
from pydantic import BaseModel
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
    distance: Optional[float] = None
    height_limit: Optional[float] = None
    min_distance: Optional[float] = None
    source: str  # Full document and clause reference
    source_file: str  # Local filename for reference
    applicable_zones: Optional[List[str]] = None
    conditions: Optional[str] = None

class SetbackRules(BaseModel):
    rear: Optional[SetbackRule] = None
    side: Optional[SetbackRule] = None
    front: Optional[SetbackRule] = None

class ProcessedCouncilArea(BaseModel):
    name: FormerCouncilArea
    dcp_version: str  # "Ashfield DCP 2016", etc.
    processed_files: List[str]  # Track which files were processed
    setbacks: SetbackRules
    extraction_confidence: float  # 0-1 confidence score

class InnerWestSetbacks(BaseModel):
    lga: str = "INNER WEST COUNCIL"
    areas: Dict[str, ProcessedCouncilArea]  # Use string keys for JSON compatibility
    processing_metadata: Dict[str, Union[str, int, float]]
```

### List of Tasks (In Implementation Order)

```yaml
Task 1: Install and Configure Required Libraries
UPDATE pip and install core dependencies:
  - UPGRADE pip: ./venv_linux/Scripts/python.exe -m pip install --upgrade pip
  - INSTALL RAG-Anything: pip install git+https://github.com/HKUDS/RAG-Anything.git
  - INSTALL AutoSchemaKG: pip install git+https://github.com/HKUST-KnowComp/AutoSchemaKG.git
  - INSTALL supporting libraries: pip install pydantic pymupdf regex python-dotenv
  - CREATE requirements.txt with all installed packages
  - TEST imports to verify successful installation

Task 2: Create Python Processing Structure
CREATE src/processing/__init__.py:
  - STANDARD Python package initialization
  - IMPORT main processing classes

CREATE src/processing/rag_processor.py:
  - MIRROR pattern from: examples/regulatory-engine/setback_processor.py
  - IMPLEMENT RAG-Anything PDF text extraction for local files
  - HANDLE different PDF formats (Ashfield chapters vs Leichhardt parts)
  - PRESERVE clause context during text chunking

CREATE src/processing/schema_extractor.py:
  - IMPLEMENT AutoSchemaKG integration
  - CREATE schema definitions for each DCP format
  - EXTRACT structured setback rules with document references

Task 3: Build Document Discovery and Processing Logic
CREATE src/utils/document_finder.py:
  - SCAN docs/dcps/INNERWEST/ directory structure
  - IDENTIFY relevant files for each former council area
  - HANDLE filename variations and case sensitivity
  - RETURN organized file lists by council area

CREATE src/processing/spatial_mapper.py:
  - MIRROR function from: examples/regulatory-engine/setback_processor.py (lines 67-90)
  - IMPLEMENT determineFormerCouncilArea with spatial boundaries
  - INTEGRATE with processed DCP data

Task 4: Create Main Processing Pipeline
CREATE scripts/process_inner_west_dcps.py:
  - ORCHESTRATE processing of all 3 DCP sets
  - USE RAG-Anything to extract text from identified PDF files
  - APPLY AutoSchemaKG to structure extracted regulatory text
  - GENERATE public/regulatory-data/inner-west-setbacks.json
  - MATCH output format from: examples/regulatory-engine/output.json
  - INCLUDE processing metadata and confidence scores

Task 5: Integrate with Existing Frontend Components
MODIFY public/regulatory-data/ directory:
  - ENSURE processed JSON file is accessible to Next.js API routes
  - VERIFY file permissions and accessibility

TEST .claude/app/api/compliance/setbacks/route.ts:
  - VERIFY it can read the processed JSON file
  - ENSURE spatial mapping works with real data
  - TEST API responses match expected format

TEST .claude/app/property/page.tsx:
  - VERIFY frontend can consume real processed data
  - ENSURE Google Maps integration still works
  - TEST form validation and compliance checking

Task 6: Create Schema Definitions
CREATE src/schemas/inner_west_setbacks.json:
  - EXTEND examples/regulatory-engine/schema.json
  - DEFINE schema for each DCP format
  - SPECIFY setback rule extraction patterns
  - INCLUDE document source tracking

Task 7: Build Comprehensive Testing
CREATE tests/test_library_installation.py:
  - VERIFY RAG-Anything and AutoSchemaKG import successfully
  - TEST basic functionality of each library
  - ENSURE no import conflicts

CREATE tests/test_document_processing.py:
  - TEST processing of sample documents from each DCP
  - VERIFY text extraction quality
  - TEST schema-based extraction accuracy

CREATE tests/test_api_integration.py:
  - TEST API routes with processed data
  - VERIFY frontend integration
  - TEST spatial mapping with known addresses

Task 8: End-to-End Validation
RUN complete processing pipeline:
  - PROCESS all accessible DCP documents
  - GENERATE complete inner-west-setbacks.json
  - VALIDATE JSON structure and content
  - TEST Next.js frontend with real data
  - VERIFY Google Maps integration
  - ENSURE form validation works correctly
```

### Per Task Pseudocode

```python
# Task 1: Library Installation and Verification
def install_and_verify_libraries():
    """Install required libraries and verify they work"""
    import subprocess
    import sys
    
    # Upgrade pip first
    subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    
    # Install RAG-Anything from GitHub
    subprocess.run([sys.executable, "-m", "pip", "install", 
                   "git+https://github.com/HKUDS/RAG-Anything.git"])
    
    # Install AutoSchemaKG from GitHub
    subprocess.run([sys.executable, "-m", "pip", "install", 
                   "git+https://github.com/HKUST-KnowComp/AutoSchemaKG.git"])
    
    # Test imports
    try:
        import rag_anything
        import autoschemakg
        print("✅ Libraries installed successfully")
        return True
    except ImportError as e:
        print(f"❌ Installation failed: {e}")
        return False

# Task 4: Main Processing Pipeline
def process_all_inner_west_dcps():
    """Main processing function using RAG-Anything and AutoSchemaKG"""
    from src.processing.rag_processor import RAGProcessor
    from src.processing.schema_extractor import SchemaExtractor
    from src.utils.document_finder import DocumentFinder
    
    # Initialize processors
    rag_processor = RAGProcessor()
    schema_extractor = SchemaExtractor("src/schemas/inner_west_setbacks.json")
    doc_finder = DocumentFinder("docs/dcps/INNERWEST/")
    
    results = {}
    
    # Process each former council area
    for area in [FormerCouncilArea.ASHFIELD, FormerCouncilArea.LEICHHARDT, FormerCouncilArea.MARRICKVILLE]:
        print(f"Processing {area.value} DCP documents...")
        
        # Find relevant documents for this area
        dcp_files = doc_finder.get_setback_documents(area)
        
        if not dcp_files:
            print(f"⚠️  No documents found for {area.value}")
            continue
        
        processed_files = []
        extracted_rules = {"rear": None, "side": None, "front": None}
        
        for file_path in dcp_files:
            try:
                # Extract text using RAG-Anything
                text = rag_processor.extract_text_from_pdf(file_path)
                
                # Chunk text for processing
                chunks = rag_processor.chunk_regulatory_text(text)
                
                # Extract structured data using AutoSchemaKG
                rules = schema_extractor.extract_setback_rules(chunks, area, file_path)
                
                # Merge rules (later rules can override earlier ones)
                for rule_type in ["rear", "side", "front"]:
                    if rules.get(rule_type):
                        extracted_rules[rule_type] = rules[rule_type]
                
                processed_files.append(os.path.basename(file_path))
                
            except Exception as e:
                print(f"❌ Failed to process {file_path}: {e}")
                continue
        
        # Create processed area data
        if any(extracted_rules.values()):
            results[area.value] = ProcessedCouncilArea(
                name=area,
                dcp_version=f"{area.value} DCP {doc_finder.get_dcp_year(area)}",
                processed_files=processed_files,
                setbacks=SetbackRules(**extracted_rules),
                extraction_confidence=schema_extractor.calculate_confidence(extracted_rules)
            ).dict()
        
    # Generate final output
    final_output = InnerWestSetbacks(
        areas=results,
        processing_metadata={
            "total_areas_processed": len(results),
            "processing_timestamp": datetime.now().isoformat(),
            "avg_confidence": sum(r["extraction_confidence"] for r in results.values()) / len(results) if results else 0
        }
    ).dict()
    
    # Save to public directory for Next.js consumption
    output_path = "public/regulatory-data/inner-west-setbacks.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(final_output, f, indent=2)
    
    print(f"✅ Processing complete. Output saved to {output_path}")
    return final_output

# Task 2: RAG Processor Implementation
class RAGProcessor:
    def __init__(self):
        # Initialize RAG-Anything with appropriate settings
        from rag_anything import RAG
        self.rag = RAG(chunk_size=500, chunk_overlap=50)
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF using RAG-Anything"""
        # CRITICAL: Handle local file paths correctly
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        # Use RAG-Anything's PDF extraction
        text = self.rag.extract_text(pdf_path)
        
        if not text or len(text.strip()) < 100:
            raise ValueError(f"Insufficient text extracted from {pdf_path}")
        
        return text
    
    def chunk_regulatory_text(self, text: str) -> List[str]:
        """Chunk text while preserving regulatory structure"""
        # PATTERN: Preserve clause references and section boundaries
        chunks = self.rag.chunk_text(text)
        
        # Filter out chunks that are too short or don't contain regulatory content
        filtered_chunks = []
        for chunk in chunks:
            if len(chunk.strip()) > 50 and any(keyword in chunk.lower() for keyword in 
                ["setback", "metres", "height", "distance", "boundary"]):
                filtered_chunks.append(chunk)
        
        return filtered_chunks
```

### Integration Points
```yaml
LIBRARY_INSTALLATION:
  - command: "pip install git+https://github.com/HKUDS/RAG-Anything.git"
  - command: "pip install git+https://github.com/HKUST-KnowComp/AutoSchemaKG.git"
  - verification: "python -c 'import rag_anything, autoschemakg; print(\"OK\")'"
  
DOCUMENT_PATHS:
  - base: "docs/dcps/INNERWEST/"
  - pattern: "Use exact filenames from directory listings"
  - output: "public/regulatory-data/inner-west-setbacks.json"
  
API_INTEGRATION:
  - existing: ".claude/app/api/compliance/setbacks/route.ts reads processed JSON"
  - frontend: ".claude/app/property/page.tsx consumes API data"
  - spatial: "Address mapping to former council areas"
```

## Validation Loop

### Level 1: Library Installation and Setup
```bash
# Navigate to project directory and activate virtual environment
cd "compliance-engine"
./venv_linux/Scripts/python.exe -m pip install --upgrade pip

# Install required libraries
./venv_linux/Scripts/pip.exe install git+https://github.com/HKUDS/RAG-Anything.git
./venv_linux/Scripts/pip.exe install git+https://github.com/HKUST-KnowComp/AutoSchemaKG.git
./venv_linux/Scripts/pip.exe install pydantic pymupdf regex python-dotenv

# Verify installation
./venv_linux/Scripts/python.exe -c "import rag_anything, autoschemakg, pydantic; print('✅ All libraries installed successfully')"

# Expected: "✅ All libraries installed successfully"
```

### Level 2: Document Discovery and Basic Processing
```bash
# Test document discovery
./venv_linux/Scripts/python.exe -c "
import os
ashfield_docs = [f for f in os.listdir('docs/dcps/INNERWEST/') if 'Ashfield' in f and f.endswith('.pdf')]
leichhardt_docs = [f for f in os.listdir('docs/dcps/INNERWEST/leichhardt/') if f.endswith('.pdf')]
marrickville_docs = [f for f in os.listdir('docs/dcps/INNERWEST/Marrickville/') if f.endswith('.pdf')]
print(f'Found: {len(ashfield_docs)} Ashfield, {len(leichhardt_docs)} Leichhardt, {len(marrickville_docs)} Marrickville docs')
"

# Test basic RAG-Anything functionality with one document
./venv_linux/Scripts/python.exe -c "
from rag_anything import RAG
import os
rag = RAG()
# Test with first available document
test_file = 'docs/dcps/INNERWEST/leichhardt/Leichhardt DCP 2013 - 1 - Cover - Amdt 18 - March 23.pdf'
if os.path.exists(test_file):
    text = rag.extract_text(test_file)
    print(f'✅ Successfully extracted {len(text)} characters from test document')
else:
    print('❌ Test document not found')
"

# Expected: Successful text extraction with character count
```

### Level 3: Full Processing Pipeline
```bash
# Run the complete processing pipeline
./venv_linux/Scripts/python.exe scripts/process_inner_west_dcps.py

# Verify output file creation and structure
./venv_linux/Scripts/python.exe -c "
import json
import os
if os.path.exists('public/regulatory-data/inner-west-setbacks.json'):
    with open('public/regulatory-data/inner-west-setbacks.json', 'r') as f:
        data = json.load(f)
    print(f'✅ Generated setbacks file with {len(data[\"areas\"])} areas')
    for area, details in data['areas'].items():
        print(f'  {area}: {len(details[\"processed_files\"])} files processed')
else:
    print('❌ Output file not created')
"

# Expected: Successfully generated JSON file with processed areas
```

### Level 4: API and Frontend Integration
```bash
# Test API endpoint with processed data (requires Next.js to be running)
# Start Next.js dev server
npm run dev &

# Wait for server to start, then test
sleep 5
curl "http://localhost:3000/api/compliance/setbacks?address=123%20Liverpool%20Rd%20Ashfield%20NSW%202131"

# Expected: JSON response with Ashfield setback rules and metadata
```

### Level 5: End-to-End System Validation
```bash
# Full system test
# 1. Frontend loads without errors
# 2. Google Maps autocomplete works
# 3. Form validation active (submit button disabled until all fields filled)
# 4. Compliance checking returns results with real DCP data

# Manual testing checklist:
# - Navigate to http://localhost:3000
# - Enter address in each former council area
# - Fill in proposal values
# - Verify compliance results show exact source files and clause references
```

## Final Validation Checklist
- [ ] RAG-Anything and AutoSchemaKG installed successfully: `python -c "import rag_anything, autoschemakg"`
- [ ] All DCP documents discovered: Check counts for each former council area
- [ ] Text extraction working: Verify character counts from sample documents
- [ ] Processing pipeline completes: `ls public/regulatory-data/inner-west-setbacks.json`
- [ ] Generated JSON is valid: `python -c "import json; json.load(open('public/regulatory-data/inner-west-setbacks.json'))"`
- [ ] API integration works: Test API endpoints with curl
- [ ] Frontend integration works: Manual testing of address entry and compliance checking
- [ ] Setback rules include source file references: Verify metadata in results
- [ ] Spatial mapping works: Test addresses from different former council areas
- [ ] Form validation prevents incomplete submissions: Try submitting partial forms

---

## Anti-Patterns to Avoid
- ❌ Don't install libraries with conflicting dependencies - use clean virtual environment
- ❌ Don't process documents that don't exist - verify file paths first
- ❌ Don't ignore extraction errors - handle PDF format issues gracefully
- ❌ Don't hardcode document filenames - use dynamic discovery
- ❌ Don't skip confidence scoring - low confidence extractions need review
- ❌ Don't claim 100% accuracy - include appropriate disclaimers
- ❌ Don't make external API calls - everything should work with local documents

## Confidence Score: 9/10

**Strengths:**
- Libraries will be installed from official GitHub repositories
- All documents available locally in docs folder - no external dependencies
- Existing frontend components already debugged and functional
- Clear document structure understanding from actual file listings
- Robust error handling and validation pipeline
- Real file paths and structure already mapped

**Potential Challenges:**
- RAG-Anything and AutoSchemaKG may have dependency conflicts during installation
- PDF format variations across different DCPs may require format-specific handling
- Schema creation for AutoSchemaKG may need iteration to get optimal extraction

**Mitigation Strategy:**
- Install libraries one at a time and test after each installation
- Start with simple text extraction before moving to structured extraction
- Test with one document from each DCP type before full processing
- Include comprehensive error handling and logging for debugging issues