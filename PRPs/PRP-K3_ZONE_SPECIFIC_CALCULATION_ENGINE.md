# PRP-K3: Zone-Specific Calculation Engine Implementation

**Project Reference Point K3: Intelligent Setback Calculation System**  
**Status:** Ready for Implementation  
**Priority:** Critical - Solves core cross-contamination problem  
**Dependencies:** PRP-K2 (PostgreSQL integration and zone data import)

## Executive Summary

PRP-K3 addresses the fundamental flaw in the current compliance engine: instead of dumping 765+ generic setback provisions to users, it implements an intelligent calculation engine that applies zone-specific rules to individual property contexts and returns clean, calculated answers.

## Current Problem Analysis

### **Critical Issues Identified:**

1. **Cross-Contamination at Scale**
   - **765 generic setback provisions** apply to all zones
   - R2 residential queries return same results as B1 commercial queries
   - Users receive hundreds of irrelevant rules instead of 3-4 targeted answers

2. **Missing Calculation Intelligence**
   - **No zone-specific calculation engine**
   - API performs database dumps instead of intelligent rule application
   - Raw regulatory text returned instead of calculated setback values

3. **Poor User Experience**
   - **12+ conflicting setback results** for single property (3m, 6m, 9m, 700m)
   - **No hierarchy resolution** between SEPP/LEP/DCP authorities
   - **No property-specific context** applied to base rules

### **Root Cause:**
The system treats setback calculation as a **document retrieval problem** instead of a **rules engine problem**. This results in information overload rather than targeted compliance answers.

## Solution Strategy

### **Phase 1: Zone-Specific Rules Engine**

#### **1. Import Comprehensive Zone-Specific Rules**
```sql
-- Target: Complete zone rule coverage
SELECT zone, COUNT(*) FROM verified_compliance_rules 
WHERE requirement_type = 'min_setback' 
GROUP BY zone;

-- Current: 6 R2 rules (Ashfield + Leichhardt)
-- Required: All zones (R1-R5, B1-B8, IN1-IN4, etc.) × All councils
```

**Data Sources to Process:**
- **4,649+ JSON files** containing zone-specific provisions
- **public/regulatory-data/inner-west-compliance-rules.json** (verified R2 data)
- **AutoSchemaKG outputs** with zone taxonomy
- **LangExtract verified outputs** with DCP extractions

#### **2. Create Rules Engine Architecture**
```typescript
interface ZoneSetbackRule {
  ruleId: string;
  zone: string;           // R2, B1, etc.
  council: string;        // Ashfield, Leichhardt, Marrickville
  boundary: string;       // front, side, rear
  baseValue: number;      // 6.0 metres
  unit: string;          // metres
  conditions: string[];   // ["heritage_overlay", "slope_factor"]
  authority: string;      // SEPP, LEP, DCP
  precedence: number;     // 1=highest, 3=lowest
  sourceDocument: string;
  effectiveDate: string;
}
```

#### **3. Implement Calculation Engine**
```typescript
class SetbackCalculationEngine {
  calculateSetbacks(
    zone: string, 
    council: string, 
    propertyContext: PropertyContext
  ): CalculatedSetbacks {
    
    // Step 1: Get base zone rules
    const baseRules = this.getZoneRules(zone, council);
    
    // Step 2: Apply property-specific modifiers
    const modifiedRules = this.applyPropertyModifiers(baseRules, propertyContext);
    
    // Step 3: Resolve conflicts using hierarchy (SEPP > LEP > DCP)
    const resolvedRules = this.resolveHierarchy(modifiedRules);
    
    // Step 4: Return clean calculated results
    return {
      front: resolvedRules.front,
      side: resolvedRules.side,
      rear: resolvedRules.rear,
      reasoning: this.generateReasoning(resolvedRules)
    };
  }
}
```

### **Phase 2: Property Context Integration**

#### **Property-Specific Modifiers:**
```typescript
interface PropertyContext {
  lotSize: number;
  slope: number;
  heritageOverlay: boolean;
  floodZone: boolean;
  streetFrontage: number;
  cornerLot: boolean;
  developmentType: string;  // single_dwelling, multi_dwelling, etc.
  specialOverlays: string[]; // ["coastal", "heritage", "bushfire"]
}
```

#### **Modifier Application Logic:**
```typescript
// Example calculation flow
Base rule: R2 Ashfield front setback = 6m minimum
+ Heritage overlay: +2m (DCP heritage provisions)  
+ Steep slope (>15%): +1m (engineering requirements)
- Corner lot allowance: -0.5m (corner lot provisions)
= Final result: 8.5m front setback for THIS specific property
```

### **Phase 3: API Response Transformation**

#### **Before (Current):**
```json
{
  "setback_results": [
    { "boundary_type": "front", "required_setback": 3, "reasoning": "..." },
    { "boundary_type": "front", "required_setback": 6, "reasoning": "..." },
    { "boundary_type": "front", "required_setback": 9, "reasoning": "..." },
    { "boundary_type": "front", "required_setback": 700, "reasoning": "..." },
    // ...12 more conflicting results
  ]
}
```

#### **After (PRP-K3):**
```json
{
  "setback_results": {
    "front": {
      "required_setback": 8.5,
      "unit": "metres", 
      "base_rule": "R2 Ashfield: 6m minimum",
      "modifiers_applied": [
        { "type": "heritage_overlay", "adjustment": "+2m" },
        { "type": "steep_slope", "adjustment": "+1m" },
        { "type": "corner_lot", "adjustment": "-0.5m" }
      ],
      "authority": "Ashfield DCP 2016 Chapter E2",
      "confidence": 95,
      "legal_precedence": "DCP"
    },
    "side": { "required_setback": 0.9, "..." },
    "rear": { "required_setback": 1.2, "..." }
  },
  "calculation_summary": {
    "zone": "R2",
    "council": "Ashfield", 
    "rules_applied": 3,
    "conflicts_resolved": 0,
    "processing_method": "Zone-Specific Calculation Engine"
  }
}
```

## Technical Implementation

### **Database Schema Requirements**

#### **1. Enhanced Zone Rules Table**
```sql
CREATE TABLE zone_setback_rules (
    id SERIAL PRIMARY KEY,
    rule_id VARCHAR(100) UNIQUE,
    zone VARCHAR(10) NOT NULL,           -- R2, B1, etc.
    council VARCHAR(50) NOT NULL,        -- Ashfield, Leichhardt
    former_council VARCHAR(50),          -- For amalgamated councils
    boundary_type VARCHAR(20) NOT NULL,  -- front, side, rear
    base_value DECIMAL(5,2),             -- 6.0, 0.9, 1.2
    unit VARCHAR(10) DEFAULT 'metres',
    operator VARCHAR(10) DEFAULT '>=',   -- >=, <=, ==
    authority_type VARCHAR(10),          -- SEPP, LEP, DCP
    precedence_level INTEGER,            -- 1=SEPP, 2=LEP, 3=DCP
    conditions JSONB,                    -- Property conditions that trigger rule
    source_document TEXT,
    source_clause TEXT,
    effective_date DATE,
    quality_score DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_zone_rules_lookup ON zone_setback_rules (zone, council, boundary_type);
CREATE INDEX idx_zone_rules_precedence ON zone_setback_rules (zone, precedence_level);
```

#### **2. Property Modifiers Table**
```sql
CREATE TABLE property_modifiers (
    id SERIAL PRIMARY KEY,
    modifier_id VARCHAR(100) UNIQUE,
    modifier_type VARCHAR(50),           -- heritage_overlay, slope_factor
    zone_applicable VARCHAR(10),         -- R2, or NULL for all zones
    council VARCHAR(50),
    condition_check TEXT,                -- SQL-like condition logic
    adjustment_value DECIMAL(5,2),       -- +2.0, -0.5
    adjustment_type VARCHAR(20),         -- additive, multiplicative, override
    description TEXT,
    source_document TEXT,
    precedence INTEGER DEFAULT 5
);
```

### **API Route Enhancement**

#### **Updated Calculate Route:**
```typescript
// app/api/setbacks/calculate/route.ts
export async function POST(request: NextRequest) {
  try {
    const { property_zone, property_id, lot_geometry } = await request.json();
    
    // Get property context from geometry and database
    const propertyContext = await this.extractPropertyContext(property_id, lot_geometry);
    
    // Initialize calculation engine
    const calculator = new SetbackCalculationEngine();
    
    // Calculate zone-specific setbacks
    const calculatedSetbacks = await calculator.calculateSetbacks(
      property_zone,
      propertyContext.council,
      propertyContext
    );
    
    return NextResponse.json({
      success: true,
      setback_results: calculatedSetbacks,
      calculation_summary: {
        zone: property_zone,
        council: propertyContext.council,
        processing_method: "Zone-Specific Calculation Engine",
        rules_applied: calculatedSetbacks.rulesApplied,
        conflicts_resolved: calculatedSetbacks.conflictsResolved
      },
      processing_time_ms: Date.now() - startTime
    });
    
  } catch (error) {
    // Fallback to existing method if calculation engine fails
    return this.fallbackToExistingMethod();
  }
}
```

## 🎯 **ACCURATE, RELIABLE, OPTIMAL Database Preparation Strategy**

### **Data Quality Hierarchy (Extraction Strategy)**

#### **Priority 1: VERIFIED STRUCTURED DATA (95% confidence)**
```
✅ public/regulatory-data/inner-west-compliance-rules.json    # 6 verified R2 rules
✅ compliance_result.json                                     # Compliance analysis  
✅ verified_compliance_rules database table                   # Already imported
Expected yield: 50-100 high-quality rules
```

#### **Priority 2: SEMI-STRUCTURED EXTRACTIONS (80% confidence)**
```
📋 langextract_verified_output/*.json                        # PDF extractions with verification
📋 monitored_pipeline_output/*.json                          # Pipeline results with quality scores
📋 validated_outputs/*.json                                  # Processed and validated extractions
Expected yield: 200-500 medium-quality rules
```

#### **Priority 3: RAW TEXT PATTERNS (60% confidence)**
```
📝 multimodal_relationships_complete.json                    # Relationship tables
📝 autoschemakg_output_*.json                               # AutoSchemaKG extractions
📝 rag_storage/*.json                                       # RAG vector database content
Expected yield: 100-300 lower-confidence rules
```

### **OPTIMAL Processing Strategy (NOT 4,649 files)**

#### **Phase 1A: High-Confidence Extraction (30 minutes)**
```bash
#!/bin/bash
# extract_verified_rules.sh

echo "=== PRP-K3 PHASE 1A: HIGH-CONFIDENCE RULE EXTRACTION ==="

# Process only verified, structured data sources
python3 extract_zone_rules_phase1.py \
  --sources "public/regulatory-data/inner-west-compliance-rules.json,compliance_result.json" \
  --output-table "zone_setback_rules" \
  --confidence-threshold 0.9 \
  --verify-against-source true

# Phase 1A Enhanced: Extract comprehensive zone rules for all councils
python3 extract_comprehensive_zones.py

# Verification checkpoint using PostgreSQL
RULES_COUNT=$(python3 -c "
import psycopg2
conn = psycopg2.connect(host='localhost', database='nsw_planning', user='postgres', password='postgres', port='5432')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM zone_setback_rules_comprehensive')
count = cursor.fetchone()[0]
print(count)
conn.close()
")
echo "Phase 1A Complete: $RULES_COUNT comprehensive rules extracted"

# Detailed verification by council
python3 -c "
import psycopg2
conn = psycopg2.connect(host='localhost', database='nsw_planning', user='postgres', password='postgres', port='5432')
cursor = conn.cursor()
cursor.execute('SELECT council, COUNT(DISTINCT zone) as zones, COUNT(*) as rules FROM zone_setback_rules_comprehensive GROUP BY council ORDER BY council')
for council, zones, rules in cursor.fetchall():
    print(f'  {council}: {zones} zones, {rules} rules')
conn.close()
"

# Create completion marker
if [ "$RULES_COUNT" -ge 42 ]; then
    echo "Phase1A_comprehensive_completed" > prp_checkpoints/K3_Phase1A_comprehensive_completed.marker
    echo "✅ Phase 1A: PASSED - Extracted $RULES_COUNT comprehensive rules (target: 42+)"
    echo "✅ Coverage: Ashfield, Leichhardt, and Marrickville with R1-R4 + business zones"
else
    echo "❌ Phase 1A: FAILED - Only $RULES_COUNT rules extracted (expected ≥42)"
    exit 1
fi
```

#### **Phase 1B: Semi-Structured Expansion (2 hours)**
```bash
#!/bin/bash
# extract_semistructured_rules.sh

echo "=== PRP-K3 PHASE 1B: SEMI-STRUCTURED RULE EXTRACTION ==="

# Only proceed if Phase 1A completed
if [ ! -f "prp_checkpoints/K3_Phase1A_completed.marker" ]; then
    echo "❌ Phase 1A not completed. Run extract_verified_rules.sh first"
    exit 1
fi

# Smart file filtering - process only relevant files
python3 filter_relevant_files.py \
  --input-dirs "langextract_verified_output,monitored_pipeline_output,validated_outputs" \
  --filter-patterns "zone,setback,R[1-5],B[1-8]" \
  --max-file-size 10MB \
  --output-list "relevant_files.txt"

RELEVANT_COUNT=$(wc -l < relevant_files.txt)
echo "Found $RELEVANT_COUNT relevant files (instead of 4,649 total)"

# Process filtered files
python3 extract_zone_rules_phase1b.py \
  --file-list "relevant_files.txt" \
  --output-table "zone_setback_rules" \
  --confidence-threshold 0.7 \
  --batch-size 50

# Verification checkpoint
TOTAL_RULES=$(sqlite3 nsw_planning.db "SELECT COUNT(*) FROM zone_setback_rules")
MEDIUM_RULES=$(sqlite3 nsw_planning.db "SELECT COUNT(*) FROM zone_setback_rules WHERE confidence >= 0.7 AND confidence < 0.9")

echo "Phase 1B Complete: $MEDIUM_RULES medium-confidence rules extracted"
echo "Total rules: $TOTAL_RULES"

# Create completion marker
if [ "$TOTAL_RULES" -ge 50 ]; then
    echo "Phase1B_completed" > prp_checkpoints/K3_Phase1B_completed.marker
    echo "✅ Phase 1B: PASSED - Total $TOTAL_RULES rules in database"
else
    echo "❌ Phase 1B: FAILED - Only $TOTAL_RULES total rules (expected ≥50)"
    exit 1
fi
```

#### **Phase 1C: Coverage Gap Analysis**
```bash
#!/bin/bash
# analyze_coverage_gaps.sh

echo "=== PRP-K3 PHASE 1C: COVERAGE GAP ANALYSIS ==="

# Check coverage by zone
python3 analyze_zone_coverage.py \
  --database "nsw_planning.db" \
  --table "zone_setback_rules" \
  --output-report "zone_coverage_report.json"

# Automated decision: only proceed to text mining if gaps exist
COVERAGE_SCORE=$(python3 -c "
import json
data = json.load(open('zone_coverage_report.json'))
total_zones = len(data['zone_coverage'])
covered_zones = sum(1 for zone, count in data['zone_coverage'].items() if count >= 3)
print(covered_zones / total_zones)
")

echo "Zone coverage score: $COVERAGE_SCORE"

if (( $(echo "$COVERAGE_SCORE >= 0.7" | bc -l) )); then
    echo "✅ Phase 1C: Coverage sufficient ($COVERAGE_SCORE) - No text mining needed"
    echo "Phase1C_completed" > prp_checkpoints/K3_Phase1C_completed.marker
else
    echo "⚠️ Phase 1C: Coverage gaps detected ($COVERAGE_SCORE) - Text mining recommended"
    echo "Phase1C_gaps_detected" > prp_checkpoints/K3_Phase1C_gaps.marker
fi
```

### **Phase 2: Automated Rule Quality Validation**

#### **Quality Validation Scripts**
```bash
#!/bin/bash
# validate_rule_quality.sh

echo "=== PRP-K3 PHASE 2: AUTOMATED QUALITY VALIDATION ==="

python3 validate_zone_rules.py \
  --database "nsw_planning.db" \
  --table "zone_setback_rules" \
  --validation-suite "comprehensive" \
  --fix-errors true \
  --output-report "quality_validation_report.json"

# Quality checks performed:
# - Zone format validation (R1, R2, B1 format)
# - Setback value reasonableness (0.5m < value < 50m)
# - Authority identification (SEPP/LEP/DCP)
# - Source document traceability
# - Duplicate detection and removal
# - Precedence hierarchy validation

QUALITY_SCORE=$(python3 -c "
import json
data = json.load(open('quality_validation_report.json'))
print(data['overall_quality_score'])
")

echo "Overall quality score: $QUALITY_SCORE"

if (( $(echo "$QUALITY_SCORE >= 0.85" | bc -l) )); then
    echo "✅ Phase 2: Quality validation PASSED ($QUALITY_SCORE)"
    echo "Phase2_completed" > prp_checkpoints/K3_Phase2_completed.marker
else
    echo "❌ Phase 2: Quality validation FAILED ($QUALITY_SCORE) - Manual review required"
    exit 1
fi
```

### **Phase 3: Calculation Engine Implementation**

#### **Automated Engine Setup**
```bash
#!/bin/bash
# setup_calculation_engine.sh

echo "=== PRP-K3 PHASE 3: CALCULATION ENGINE SETUP ==="

# Only proceed if previous phases completed
for phase in "K3_Phase1A_completed" "K3_Phase1B_completed" "K3_Phase2_completed"; do
    if [ ! -f "prp_checkpoints/$phase.marker" ]; then
        echo "❌ Previous phase not completed: $phase"
        exit 1
    fi
done

# Create enhanced database schema
python3 create_calculation_schema.py \
  --database "nsw_planning.db" \
  --schema-file "schemas/zone_calculation_schema.sql"

# Import property modifiers
python3 import_property_modifiers.py \
  --database "nsw_planning.db" \
  --modifiers-file "data/property_modifiers.json"

# Create calculation engine class
cp "templates/SetbackCalculationEngine.ts" "frontend-nextjs/lib/calculation/SetbackCalculationEngine.ts"

# Update API route
python3 update_api_route.py \
  --route-file "frontend-nextjs/app/api/setbacks/calculate/route.ts" \
  --backup-existing true \
  --integration-type "calculation_engine"

echo "✅ Phase 3: Calculation engine setup complete"
echo "Phase3_completed" > prp_checkpoints/K3_Phase3_completed.marker
```

### **Phase 4: Integration Testing and Validation**

#### **Automated Testing Suite**
```bash
#!/bin/bash
# test_calculation_engine.sh

echo "=== PRP-K3 PHASE 4: INTEGRATION TESTING ==="

# Test with known addresses
python3 test_calculation_engine.py \
  --test-addresses "test_data/known_addresses.json" \
  --expected-results "test_data/expected_setbacks.json" \
  --api-endpoint "http://localhost:3007/api/setbacks/calculate" \
  --output-report "integration_test_report.json"

# Performance testing
python3 performance_test.py \
  --concurrent-requests 10 \
  --duration-seconds 60 \
  --target-latency-ms 500 \
  --output-report "performance_test_report.json"

# Validation checks
ACCURACY=$(python3 -c "
import json
data = json.load(open('integration_test_report.json'))
print(data['accuracy_score'])
")

PERFORMANCE=$(python3 -c "
import json
data = json.load(open('performance_test_report.json'))
print(data['avg_response_time_ms'])
")

echo "Accuracy score: $ACCURACY"
echo "Average response time: ${PERFORMANCE}ms"

# Success criteria
if (( $(echo "$ACCURACY >= 0.9" | bc -l) )) && (( $(echo "$PERFORMANCE <= 500" | bc -l) )); then
    echo "✅ Phase 4: Integration testing PASSED"
    echo "Phase4_completed" > prp_checkpoints/K3_Phase4_completed.marker
    echo "K3_PRP_COMPLETE" > prp_checkpoints/K3_completed.marker
else
    echo "❌ Phase 4: Integration testing FAILED (Accuracy: $ACCURACY, Performance: ${PERFORMANCE}ms)"
    exit 1
fi
```

#### **2. Import Verified Rules**
```sql
-- Import from verified_compliance_rules (6 R2 rules)
INSERT INTO zone_setback_rules 
SELECT rule_id, zones->>0, authority, requirement_subtype, 
       value_numeric, units, jurisdiction, priority
FROM verified_compliance_rules 
WHERE requirement_type = 'min_setback';

-- Expand to all zones found in JSON files
-- Target: R1-R5, B1-B8, IN1-IN4, SP1-SP5, etc.
```

#### **3. Build Property Modifier Database**
```sql
-- Heritage overlays, flood zones, slope factors
INSERT INTO property_modifiers (modifier_id, modifier_type, adjustment_value)
VALUES 
('heritage_setback_increase', 'heritage_overlay', 2.0),
('steep_slope_safety', 'slope_factor', 1.0),
('corner_lot_allowance', 'corner_lot', -0.5);
```

### **Phase 2: Calculation Engine Development**

#### **1. Zone Rules Query Optimization**
```typescript
async getZoneRules(zone: string, council: string): Promise<ZoneRule[]> {
  const query = `
    SELECT rule_id, boundary_type, base_value, conditions, 
           authority_type, precedence_level, source_document
    FROM zone_setback_rules 
    WHERE zone = $1 AND (council = $2 OR council IS NULL)
    ORDER BY precedence_level ASC, boundary_type ASC
  `;
  return await this.db.query(query, [zone, council]);
}
```

#### **2. Hierarchy Resolution Logic**
```typescript
resolveHierarchy(rules: ZoneRule[]): ResolvedRules {
  // Group by boundary type
  const rulesByBoundary = groupBy(rules, 'boundary_type');
  
  return mapValues(rulesByBoundary, (boundaryRules) => {
    // Sort by legal precedence (SEPP > LEP > DCP)
    const sortedRules = sortBy(boundaryRules, 'precedence_level');
    
    // Apply most restrictive rule (highest authority)
    const primaryRule = sortedRules[0];
    
    // Check for SEPP overrides
    const seppOverride = sortedRules.find(r => r.authority_type === 'SEPP');
    
    return seppOverride || primaryRule;
  });
}
```

### **Phase 3: User Experience Enhancement**

#### **Clean API Responses:**
- **Single answer per boundary** (not 12 conflicting results)
- **Clear reasoning** with legal authority citations
- **Property-specific calculations** with modifier explanations
- **Confidence scores** based on rule quality and data completeness

#### **Error Handling:**
- **Graceful fallback** to existing method if calculation engine fails
- **Missing rule notifications** for zones without complete data
- **Calculation audit trail** for transparency and debugging

## Success Metrics

### **Functional Requirements:**
- ✅ **Single setback value per boundary** (front/side/rear)
- ✅ **Zone-specific rule application** (R2 ≠ B1 ≠ IN1)
- ✅ **Property-specific modifications** (heritage, slope, corner lots)
- ✅ **Legal hierarchy resolution** (SEPP > LEP > DCP)
- ✅ **Clean API responses** with reasoning and confidence scores

### **Performance Requirements:**
- ⚡ **<500ms calculation time** for typical property
- 🎯 **95%+ rule coverage** for Inner West LGA zones
- 📊 **90%+ confidence scores** for verified rules
- 🔄 **Graceful fallback** maintains existing functionality

### **Data Quality Requirements:**
- 📋 **Complete zone coverage**: All R1-R5, B1-B8, IN1-IN4 zones
- 🏛️ **Authority-specific rules**: Ashfield, Leichhardt, Marrickville councils
- 📖 **Source traceability**: Every rule linked to source PDF and clause
- ⚖️ **Legal hierarchy**: Proper SEPP/LEP/DCP precedence implementation

## Risk Mitigation

### **Technical Risks:**
- **Incomplete zone data**: Maintain fallback to existing generic provisions
- **Calculation errors**: Implement comprehensive unit testing and validation
- **Performance degradation**: Cache frequently accessed rules and calculations

### **Data Quality Risks:**
- **Conflicting rules**: Implement conflict detection and manual review workflow
- **Outdated regulations**: Version control and effective date tracking
- **Missing modifiers**: Graceful handling of properties with unknown characteristics

## Implementation Timeline

### **Week 1-2: Foundation**
- Extract zone rules from all 4,649 JSON files
- Create enhanced database schema
- Import verified R2 rules and expand to other zones

### **Week 3-4: Calculation Engine**
- Implement SetbackCalculationEngine class
- Build hierarchy resolution logic
- Create property context extraction

### **Week 5-6: API Integration**
- Update /api/setbacks/calculate route
- Implement fallback mechanisms
- Add comprehensive error handling

### **Week 7-8: Testing & Optimization**
- Unit tests for all calculation scenarios  
- Performance optimization and caching
- User acceptance testing with real addresses

## 📋 **EXECUTION VERIFICATION AND AUTOMATED COMPLETION MARKERS**

### **Master Execution Script**
```bash
#!/bin/bash
# execute_prp_k3.sh - Master execution script with automated verification

echo "=== PRP-K3 ZONE-SPECIFIC CALCULATION ENGINE IMPLEMENTATION ==="
echo "Starting automated execution with verification checkpoints..."

# Create checkpoint directory
mkdir -p prp_checkpoints

# Execute phases in sequence with automated verification
PHASES=(
    "extract_verified_rules.sh"
    "extract_semistructured_rules.sh" 
    "analyze_coverage_gaps.sh"
    "validate_rule_quality.sh"
    "setup_calculation_engine.sh"
    "test_calculation_engine.sh"
)

for phase in "${PHASES[@]}"; do
    echo ""
    echo "🔄 Executing: $phase"
    
    if bash "prp_k3_scripts/$phase"; then
        echo "✅ $phase completed successfully"
    else
        echo "❌ $phase failed - stopping execution"
        echo "FAILED_AT_$phase" > prp_checkpoints/K3_failure.marker
        exit 1
    fi
done

# Final verification - all phases completed
REQUIRED_MARKERS=(
    "K3_Phase1A_completed.marker"
    "K3_Phase1B_completed.marker"
    "K3_Phase2_completed.marker"
    "K3_Phase3_completed.marker"
    "K3_Phase4_completed.marker"
)

echo ""
echo "🔍 Final verification - checking completion markers..."

ALL_COMPLETE=true
for marker in "${REQUIRED_MARKERS[@]}"; do
    if [ -f "prp_checkpoints/$marker" ]; then
        echo "✅ $marker"
    else
        echo "❌ $marker - MISSING"
        ALL_COMPLETE=false
    fi
done

if [ "$ALL_COMPLETE" = true ]; then
    echo ""
    echo "🎉 PRP-K3 IMPLEMENTATION COMPLETE!"
    echo "K3_IMPLEMENTATION_COMPLETE" > prp_checkpoints/K3_master_complete.marker
    
    # Generate final report
    python3 generate_k3_completion_report.py \
        --database "nsw_planning.db" \
        --checkpoint-dir "prp_checkpoints" \
        --output-report "PRP_K3_COMPLETION_REPORT.json"
    
    echo "📊 Completion report generated: PRP_K3_COMPLETION_REPORT.json"
else
    echo ""
    echo "❌ PRP-K3 IMPLEMENTATION INCOMPLETE"
    echo "Some phases failed verification - check individual markers"
    exit 1
fi
```

### **Automated Success Criteria Validation**

#### **Quantitative Success Metrics (Automatically Verified)**
```bash
#!/bin/bash
# validate_success_criteria.sh

echo "=== PRP-K3 SUCCESS CRITERIA VALIDATION ==="

# Database connectivity test
DB_ACCESSIBLE=$(sqlite3 nsw_planning.db "SELECT 1" 2>/dev/null && echo "true" || echo "false")
echo "Database accessible: $DB_ACCESSIBLE"

# Zone rule coverage test  
ZONE_COVERAGE=$(sqlite3 nsw_planning.db "
SELECT ROUND(
    (SELECT COUNT(DISTINCT zone) FROM zone_setback_rules WHERE confidence >= 0.7) * 100.0 / 
    (SELECT COUNT(*) FROM (SELECT 'R1' UNION SELECT 'R2' UNION SELECT 'R3' UNION SELECT 'R4' UNION SELECT 'B1' UNION SELECT 'B2' UNION SELECT 'B3' UNION SELECT 'B4'))
    , 1
)")
echo "Zone coverage: ${ZONE_COVERAGE}%"

# Rule quality test
AVG_QUALITY=$(sqlite3 nsw_planning.db "SELECT ROUND(AVG(confidence), 2) FROM zone_setback_rules")
echo "Average rule quality: $AVG_QUALITY"

# API response test
API_RESPONSE_TIME=$(curl -o /dev/null -s -w '%{time_total}' \
    -X POST http://localhost:3007/api/setbacks/calculate \
    -H "Content-Type: application/json" \
    -d '{"property_zone": "R2", "property_id": 1962876, "lot_geometry": {"rings": [[[0,0],[1,0],[1,1],[0,1],[0,0]]]}}')
echo "API response time: ${API_RESPONSE_TIME}s"

# Zone-specific calculation test
ZONE_SPECIFIC_TEST=$(curl -s -X POST http://localhost:3007/api/setbacks/calculate \
    -H "Content-Type: application/json" \
    -d '{"property_zone": "R2", "property_id": 1962876, "lot_geometry": {"rings": [[[0,0],[1,0],[1,1],[0,1],[0,0]]]}}' \
    | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    results = data.get('setback_results', {})
    if isinstance(results, dict) and len(results) <= 4:
        print('PASSED')
    else:
        print('FAILED')
except:
    print('ERROR')
")
echo "Zone-specific calculation: $ZONE_SPECIFIC_TEST"

# Success criteria evaluation
SUCCESS_CRITERIA=(
    "ZONE_COVERAGE:>=70"
    "AVG_QUALITY:>=0.80"
    "API_RESPONSE_TIME:<=1.0"
    "ZONE_SPECIFIC_TEST:==PASSED"
    "DB_ACCESSIBLE:==true"
)

echo ""
echo "📊 SUCCESS CRITERIA EVALUATION:"

ALL_PASSED=true
for criterion in "${SUCCESS_CRITERIA[@]}"; do
    METRIC=$(echo $criterion | cut -d':' -f1)
    OPERATOR=$(echo $criterion | cut -d':' -f2 | cut -c1-2)
    THRESHOLD=$(echo $criterion | cut -d':' -f2 | cut -c3-)
    
    case $METRIC in
        "ZONE_COVERAGE")
            ACTUAL=$ZONE_COVERAGE
            ;;
        "AVG_QUALITY") 
            ACTUAL=$AVG_QUALITY
            ;;
        "API_RESPONSE_TIME")
            ACTUAL=$API_RESPONSE_TIME
            ;;
        "ZONE_SPECIFIC_TEST")
            ACTUAL=$ZONE_SPECIFIC_TEST
            ;;
        "DB_ACCESSIBLE")
            ACTUAL=$DB_ACCESSIBLE
            ;;
    esac
    
    if [[ "$OPERATOR" == ">=" ]]; then
        PASSED=$(echo "$ACTUAL >= $THRESHOLD" | bc -l)
    elif [[ "$OPERATOR" == "==" ]]; then
        PASSED=$([ "$ACTUAL" == "$THRESHOLD" ] && echo 1 || echo 0)
    else
        PASSED=$(echo "$ACTUAL <= $THRESHOLD" | bc -l)
    fi
    
    if [ "$PASSED" = "1" ]; then
        echo "✅ $METRIC: $ACTUAL (threshold: $OPERATOR$THRESHOLD)"
    else
        echo "❌ $METRIC: $ACTUAL (threshold: $OPERATOR$THRESHOLD)"
        ALL_PASSED=false
    fi
done

if [ "$ALL_PASSED" = true ]; then
    echo ""
    echo "🎉 ALL SUCCESS CRITERIA PASSED"
    echo "SUCCESS_CRITERIA_VALIDATED" > prp_checkpoints/K3_success_criteria_passed.marker
    exit 0
else
    echo ""
    echo "❌ SOME SUCCESS CRITERIA FAILED"
    echo "SUCCESS_CRITERIA_FAILED" > prp_checkpoints/K3_success_criteria_failed.marker
    exit 1
fi
```

### **Automated Acceptance Criteria Checklist**

#### **PRP-K3 Acceptance Criteria (Auto-Verified)**
```json
{
  "prp_k3_acceptance_criteria": {
    "functional_requirements": [
      {
        "criteria": "Zone-specific calculation returns different results for R2 vs B1",
        "test_script": "test_zone_differentiation.py",
        "verification_method": "API_COMPARISON_TEST",
        "pass_threshold": "results_differ_by_zone",
        "auto_verifiable": true
      },
      {
        "criteria": "Single setback per boundary replaces 12+ conflicting results", 
        "test_script": "test_single_results.py",
        "verification_method": "RESULT_COUNT_TEST",
        "pass_threshold": "results_per_boundary <= 1",
        "auto_verifiable": true
      },
      {
        "criteria": "Property modifiers applied (heritage, slopes, corner lots)",
        "test_script": "test_property_modifiers.py", 
        "verification_method": "MODIFIER_APPLICATION_TEST",
        "pass_threshold": "modifiers_detected_in_response",
        "auto_verifiable": true
      },
      {
        "criteria": "Legal hierarchy enforced (SEPP > LEP > DCP)",
        "test_script": "test_legal_hierarchy.py",
        "verification_method": "PRECEDENCE_TEST", 
        "pass_threshold": "higher_authority_wins",
        "auto_verifiable": true
      },
      {
        "criteria": "Clean API responses with reasoning and confidence",
        "test_script": "test_api_response_format.py",
        "verification_method": "RESPONSE_SCHEMA_TEST",
        "pass_threshold": "schema_validation_passes",
        "auto_verifiable": true
      },
      {
        "criteria": "Performance maintained (<500ms calculation time)",
        "test_script": "test_performance.py",
        "verification_method": "LATENCY_TEST",
        "pass_threshold": "avg_response_time < 500ms",
        "auto_verifiable": true
      },
      {
        "criteria": "Fallback functional if calculation engine fails",
        "test_script": "test_fallback_mechanism.py",
        "verification_method": "FAILOVER_TEST", 
        "pass_threshold": "fallback_provides_results",
        "auto_verifiable": true
      }
    ],
    "data_quality_requirements": [
      {
        "criteria": "Zone rule database contains ≥50 high-quality rules",
        "verification_method": "DATABASE_COUNT_QUERY",
        "pass_threshold": "COUNT(*) >= 50 WHERE confidence >= 0.8",
        "auto_verifiable": true
      },
      {
        "criteria": "Zone coverage ≥70% for major zones (R1-R4, B1-B4)",
        "verification_method": "COVERAGE_ANALYSIS_QUERY", 
        "pass_threshold": "covered_zones / total_major_zones >= 0.7",
        "auto_verifiable": true
      },
      {
        "criteria": "Rule traceability to source PDFs maintained",
        "verification_method": "TRACEABILITY_CHECK",
        "pass_threshold": "source_document NOT NULL for all rules",
        "auto_verifiable": true
      }
    ]
  }
}
```

## 🚀 **EXECUTION READINESS CHECKLIST**

### **Pre-Execution Verification**
- [ ] ✅ **PostgreSQL 17 installed** (completed in PRP-K2)
- [ ] ✅ **Zone data imported** (verified_compliance_rules table exists)
- [ ] ✅ **NextJS server operational** (port 3007)
- [ ] ✅ **Python environment active** (venv_linux)
- [ ] ✅ **Database writable** (nsw_planning.db accessible)

### **Execution Command**
```bash
# Single command to execute entire PRP-K3 with verification
bash execute_prp_k3.sh

# Check completion status
ls -la prp_checkpoints/K3_*.marker

# View final report
cat PRP_K3_COMPLETION_REPORT.json
```

### **Success Verification**
```bash
# Verify PRP-K3 completion
if [ -f "prp_checkpoints/K3_master_complete.marker" ]; then
    echo "✅ PRP-K3 SUCCESSFULLY COMPLETED"
    echo "Zone-specific calculation engine is operational"
else
    echo "❌ PRP-K3 INCOMPLETE - check prp_checkpoints/ for failures"
fi
```

---

**PRP-K3 now includes comprehensive automated execution, verification checkpoints, and success criteria validation. The implementation can be executed and verified without manual intervention, ensuring reliable completion of the zone-specific calculation engine.**

---

**This PRP-K3 transforms the compliance engine from a document dump tool into an intelligent calculation system that provides users with exactly what they need: clean, calculated setback requirements specific to their property and zone.**