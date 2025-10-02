# NSW Development Compliance Feature Implementation Prompt for Claude Code

## Core Requirements

### 1. Architecture Principles
- **Three-layer architecture** (pre-processing → API → frontend)
- **Pre-processing layer**: Processes Inner West Council's 3 DCPs (Ashfield, Leichhardt, Marrickville) to extract setback rules during build time
- **API layer**: Serves pre-processed rules via Next.js API routes (no PDF processing during requests)
- **Frontend layer**: Pure math on council-published constraints (no AI interpretation)

### 2. Deterministic Compliance Engine
- **NO AI interpretation** of regulations - only math on council-published constraints
- **Exact regulatory citations** for every compliance determination
- **Clear audit trail** showing calculation steps
- **No PDF processing** during user requests - all rules pre-processed

### 3. Inner West Council Specifics
- **3 operative DCPs** (Ashfield, Leichhardt, Marrickville) - spatial data determines which applies
- **Process all 3 DCPs** during build time, not on user request
- **Store results in structured JSON** by former council area
- **Use spatial data** to determine which DCP applies to a property

### 4. UI Requirements
- **Google Maps autocomplete address field** for user input
- **Mandatory input fields** for:
 - Proposed height (m)
 - Proposed FSR
 - Proposed rear setback (m)
 - Proposed side setback (m)
 - Proposed front setback (m)
- **Submit button disabled** until all required fields are completed
- **Clear compliance results** showing exact gaps and mitigation paths
- **Regulatory citations** with direct links to operative clauses

## Expected Operation

### Correct Working Flow
1. User enters address via Google Maps autocomplete
2. System displays property data (zone, constraints, former council area)
3. User inputs proposal values in all required fields
4. System calculates compliance status using pre-processed rules
5. Results show:
 - // status indicators
 - Exact gap values (e.g., "0.3m too tall")
 - Specific mitigation paths (e.g., "Reduce height by 0.3m")
 - Regulatory citations with direct links

### Example Correct Operation
**Input:**
- Address: "85 Thompson St, Drummoyne NSW 2047"
- Proposed height: 9.8m
- Proposed FSR: 0.52
- Rear setback: 1.2m
- Side setback: 0.8m
- Front setback: 4.5m

**Output:**
- HEIGHT VIOLATION: 9.8m > 8.5m limit (gap: -0.3m)
 Source: Canada Bay LEP 2013 Clause 4.3
 Fix: Reduce height by 0.3m
- FSR VIOLATION: 0.52 > 0.5 limit (gap: -0.02)
 Source: Canada Bay LEP 2013 Clause 4.4
 Fix: Reduce floor area by 14.2m²
- REAR SETBACK VIOLATION: 1.2m < 1.5m limit (gap: -0.3m)
 Source: Canada Bay DCP 2013 Section 5.4.2
 Fix: Increase rear setback to 1.5m
- SIDE SETBACK VIOLATION: 0.8m < 1.0m limit (gap: -0.2m)
 Source: Canada Bay DCP 2013 Section 5.2.3
 Fix: Increase side setback to 1.0m
- FRONT SETBACK COMPLIES: 4.5m ≥ 5.0m limit (gap: -0.5m)

## Critical Implementation Details

### 1. Rules Engine Logic
```typescript
// Determine which former council area applies
function determineFormerCouncilArea(geometry: { x: number; y: number }) {
 // Simplified spatial check
 const { x, y } = geometry;
 if (x > 16820000) return "Ashfield";
 if (x > 16810000 && y > -4010000) return "Leichhardt";
 return "Marrickville";
}

// Check compliance using pre-processed rules
function checkCompliance(propertyData, setbackRules, proposal) {
 const results = [];
 
 // Height check
 if (proposal.height > propertyData.constraints.maxHeight) {
 results.push({
 rule: "Height",
 compliant: false,
 value: proposal.height,
 limit: propertyData.constraints.maxHeight,
 gap: propertyData.constraints.maxHeight - proposal.height,
 source: propertyData.heightSource.source,
 mitigation: `Reduce height by ${Math.abs(gap).toFixed(1)}m`
 });
 }
 
 // FSR check
 if (proposal.fsr > propertyData.constraints.maxFsr) {
 const lotSize = extractLotSize(propertyData.propertyArea);
 const deficit = (proposal.fsr - propertyData.constraints.maxFsr) * lotSize;
 results.push({
 rule: "FSR",
 compliant: false,
 value: proposal.fsr,
 limit: propertyData.constraints.maxFsr,
 gap: propertyData.constraints.maxFsr - proposal.fsr,
 source: propertyData.fsrSource.source,
 mitigation: `Reduce floor area by ${deficit.toFixed(1)}m²`
 });
 }
 
 // Setback checks (using pre-processed rules)
 if (setbackRules.rear && proposal.rearSetback < setbackRules.rear.distance) {
 results.push({
 rule: "Rear Setback",
 compliant: false,
 value: proposal.rearSetback,
 limit: setbackRules.rear.distance,
 gap: proposal.rearSetback - setbackRules.rear.distance,
 source: setbackRules.rear.source,
 mitigation: `Increase rear setback to ${setbackRules.rear.distance}m`
 });
 }
 
 return results;
}
```

### 2. Critical Safeguards
- **Clear disclaimer**: "This tool uses council-published constraints from official planning documents. Final development assessment requires council submission."
- **No AI interpretation claims**: Never say "AI determined this" - only show "Rules engine determined based on [specific regulation]"
- **Direct source links**: Always link to the exact operative clause
- **Version tracking**: Note amendment dates for all constraints
- **Context awareness**: Only apply rules that match the specific context

### 3. What NOT to Implement
- No PDF processing during user requests
- No AI interpretation of regulations
- No attempt to handle all possible SEPPs/DCPs
- No complex spatial analysis
- No claims of "prediction" or "analysis"

## Expected Output Format

The compliance results must be displayed with:
1. **Status indicator** (//)
2. **Rule name** (e.g., "Height", "FSR", "Rear Setback")
3. **Compliance status** (COMPLIES/VIOLATION)
4. **Exact values** (Your proposal: X vs Y limit)
5. **Mitigation path** (if non-compliant)
6. **Source citation** with direct link to operative document

Example:
```
 HEIGHT VIOLATION
Your proposal: 9.8m
R2 Max height: 8.5m (Canada Bay LEP 2013 Clause 4.3)
Deficit: 0.3m too tall
Fix: Reduce height by 0.3m
Source: https://www.legislation.nsw.gov.au/#/view/EPI/2013/389
```

## Mentorship Guidance

When implementing, focus on:
1. **Correct spatial determination** of which DCP applies
2. **Accurate gap calculations** with precise mitigation paths
3. **Clear regulatory citations** with working links
4. **User-friendly UI** that guides users through required inputs
5. **Deterministic results** that match council assessment methodology

Remember: This is a calculator, not an AI tool. Every compliance determination must map 1:1 to specific regulations with no interpretation. If a rule doesn't have a clear numeric constraint, display "Requires professional assessment" with relevant regulatory citations.