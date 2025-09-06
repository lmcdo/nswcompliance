## FEATURE: NSW Development Compliance MVP (Inner West Council Focus)

- **Deterministic compliance checking system** that validates development proposals against NSW planning regulations
- **RAG-Anything implementation** that processes Inner West Council's 3 operative DCPs to extract setback rules
- **AutoSchemaKG integration** to structure regulatory knowledge for precise clause retrieval
- **No AI interpretation** - only extracts explicit numeric constraints from regulations
- **Works with existing property data API** (3 API calls for planning data)
- **Google Maps autocomplete address field** for user input
- **Mandatory input fields** for height, FSR, and setbacks
- **Submit button disabled** until all required fields are completed
- **Spatial location determines which DCP applies** (Ashfield/Leichhardt/Marrickville)

## EXAMPLES:

In the `examples/regulatory-engine/` folder:

- `examples/regulatory-engine/setback_processor.py` - RAG-Anything implementation for setback rules
- `examples/regulatory-engine/schema.json` - AutoSchemaKG schema for setback rules
- `examples/regulatory-engine/output.json` - Expected output structure for Inner West Council
- `examples/compliance/api/route.ts` - Next.js API route implementation pattern
- `examples/compliance/property-page.tsx` - Next.js page implementation pattern

## DOCUMENTATION:

- RAG-Anything: https://github.com/HKUDS/RAG-Anything
- AutoSchemaKG: https://github.com/HKUST-KnowComp/AutoSchemaKG
- NSW Planning Portal: https://www.planningportal.nsw.gov.au/
- Inner West Council DCPs: https://www.innerwest.nsw.gov.au/planning-building/planning-documents

## SPECIFIC REQUIREMENTS

### 1. Critical Correction: Inner West Has 3 Operative DCPs
- **Inner West Council has 3 operative DCPs** from former councils (Ashfield, Leichhardt, Marrickville)
- **Spatial data determines which DCP applies** to a property
- **Process all 3 DCPs** during build time, not on user request
- **Do NOT process all possible DCPs** - only Inner West's 3 operative DCPs

### 2. Document Processing Pipeline
- Process Inner West Council documents from `docs/` directory:
  - InnerWest_Ashfield_DCP_2014.pdf
  - InnerWest_Leichhardt_DCP_2014.pdf
  - InnerWest_Marrickville_DCP_2014.pdf
  - SEPP_Sustainable_Buildings_2022.pdf (one of 9 statewide SEPPs)
- Extract setback rules with exact clause references
- Store results in structured JSON format by former council area
- Target completion: 4 hours

### 3. AutoSchemaKG Implementation
- Create schema that captures setback rules by former council area:
  - Ashfield, Leichhardt, Marrickville
  - Source clause references
- Target completion: 2 hours

### 4. Next.js Integration
- Create output format consumable by Next.js API routes
- Include Google Maps autocomplete address field
- Implement mandatory input fields (height, FSR, setbacks)
- Disable submit button until all fields are completed
- Use spatial data to determine which DCP applies
- Target completion: 3 hours

## OTHER CONSIDERATIONS

- Include `.env.example` with RAG-Anything configuration
- Document setup process in README
- **Critical**: All processing must be deterministic with clear audit trail
- **Critical**: Never claim AI is interpreting regulations - only extracting exact clauses
- **Critical**: Must work with existing PlotDetect data structure
- **Critical**: Google Maps autocomplete requires API key management
- **Critical**: Form validation must enforce all required fields
- **Critical**: Only use constraints that map to existing data fields in the app

## SUCCESS CRITERIA

1. When run on Inner West Council documents:
   - Correctly extracts 85%+ of setback rules
   - All extracted setback rules include exact clause references
   - Output JSON is consumable by Next.js frontend
   - Correctly maps properties to former council areas

2. Output JSON includes:
   - Exact setback constraint values
   - Direct link to operative document
   - Former council area applicability
   - Context conditions (if any)

3. The system does NOT:
   - Interpret regulations beyond what's explicitly stated
   - Provide "advice" that requires professional judgment
   - Claim to replace formal development assessment
   - Process PDFs during user requests