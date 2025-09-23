# PRP-K5: SEPP/LEP Hierarchy Engine Activation

**Status**: READY FOR IMPLEMENTATION 
**Priority**: HIGH - Completes Legal Hierarchy 
**Dependencies**: PRP-K4 (Database Migration Complete) 
**Date**: 2025-09-07

## Executive Summary

PRP-K4 successfully imported all SEPP/LEP hierarchy data, but the rules engine remains inactive. This PRP activates the complete SEPP > LEP > DCP legal hierarchy by restoring the processor files and upgrading zone rule authority levels.

## Current State Analysis

### **What PRP-K4 Delivered:**
- **91 SEPP/LEP overrides** imported to PostgreSQL
- **sepp_lep_overrides table** fully operational
- **Hierarchy data relationships** available for processing

### **Critical Gap Identified:**
- **Rules engine deactivated** (`sepp-lep-processor.ts.bak`)
- **All zone rules are DCP level** (0 SEPP rules, 0 LEP rules)
- **Hierarchy logic not integrated** into API calculation flow

## Active Files Requiring Updates

### **Database Tables (PostgreSQL):**
1. **`sepp_lep_overrides`** Active (91 records)
 - Contains SEPP provision → LEP clause relationships
 - Override types: modifies (67), exempts_from (13), replaces (6), adds_to (5)

2. **`zone_setback_rules`** Needs Authority Upgrade
 - Current: 48 rules, all authority_type = "DCP" 
 - Required: Upgrade matching rules to SEPP/LEP authority levels

### **Frontend Components Requiring Activation:**
1. **`frontend-nextjs/lib/compliance/sepp-lep-processor.ts`** Currently .bak
 - Complete hierarchical rules engine
 - Authority resolution logic (SEPP > LEP > DCP)
 - Conflict resolution methods
 - Legal audit trail generation

2. **`frontend-nextjs/lib/database/client.ts`** Active
 - getHierarchicalSetbackControls() function ready
 - SEPP/LEP precedence query logic implemented

3. **`frontend-nextjs/app/api/setbacks/calculate/route.ts`** Needs Integration
 - Current: Uses basic zone rules only
 - Required: Integrate hierarchical processor

## Implementation Tasks

### **Task 1: Restore Hierarchy Processor**
```bash
cd frontend-nextjs/lib/compliance/
mv sepp-lep-processor.ts.bak sepp-lep-processor.ts
```

### **Task 2: Upgrade Zone Rule Authority Levels**
```sql
-- Upgrade rules that match SEPP provisions
UPDATE zone_setback_rules 
SET authority_type = 'SEPP', precedence_level = 1
WHERE rule_id IN (
 SELECT DISTINCT sepp_provision_id::text 
 FROM sepp_lep_overrides
 WHERE override_type IN ('replaces', 'modifies')
);

-- Upgrade rules that match LEP clauses 
UPDATE zone_setback_rules 
SET authority_type = 'LEP', precedence_level = 2
WHERE rule_id IN (
 SELECT DISTINCT lep_clause_reference 
 FROM sepp_lep_overrides 
 WHERE override_type = 'modifies'
);
```

### **Task 3: Integrate Processor into API**
Update `app/api/setbacks/calculate/route.ts` to use hierarchical engine:
```typescript
import { SEPPLEPProcessor } from '@/lib/compliance/sepp-lep-processor';

// In calculation logic:
const hierarchyProcessor = new SEPPLEPProcessor();
const hierarchicalResult = await hierarchyProcessor.processHierarchicalCompliance(
 nswApiLayers,
 property_zone,
 'setback'
);
```

## Success Criteria

### **Functional Requirements:**
1. **SEPP rules take precedence** over LEP and DCP rules
2. **LEP rules take precedence** over DCP rules
3. **Legal audit trail** generated for all hierarchy decisions
4. **API responses include** controlling authority identification

### **Data Quality Requirements:**
1. **Authority distribution**: Mix of SEPP (highest), LEP (medium), DCP (baseline)
2. **Precedence enforcement**: Higher authority always wins conflicts
3. **Source traceability**: All rules linked to legal documents

## Verification Tests

### **Test 1: Authority Precedence**
```bash
# Query should return SEPP rule if available, then LEP, then DCP
curl -X POST http://localhost:3007/api/setbacks/calculate \
 -d '{"property_zone": "R2", "property_id": 1962876}' \
 | grep "authority"
```

### **Test 2: Legal Audit Trail**
Response should include:
```json
{
 "controlling_authority": "SEPP|LEP|DCP",
 "legal_justification": "Authority explanation...", 
 "audit_trail": ["Step 1: ...", "Step 2: ..."]
}
```

## Risk Mitigation

### **Backward Compatibility:**
- **Graceful fallback** to existing DCP-only rules if hierarchy fails
- **Existing API contracts** maintained during integration

### **Performance:**
- **Hierarchy queries optimized** with proper indexes
- **Calculation time target**: <500ms maintained

## Timeline

### **Week 1: Core Activation**
- Restore sepp-lep-processor.ts
- Upgrade zone rule authority levels 
- Basic hierarchy integration testing

### **Week 2: API Integration**
- Update calculation route to use hierarchy
- Implement legal audit trail
- Performance optimization

### **Week 3: Verification**
- End-to-end testing with real addresses
- Legal authority validation
- Production deployment preparation

## Completion Markers

**Success Indicators:**
1. **sepp-lep-processor.ts** active (not .bak)
2. **Zone rules have mixed authorities** (SEPP > 0, LEP > 0, DCP remaining)
3. **API responses show hierarchy** with legal justification
4. **All tests pass** with proper precedence enforcement

---

**This PRP completes the legal hierarchy implementation, transforming the system from DCP-only guidance to full NSW planning law compliance with SEPP > LEP > DCP precedence.**