# PRP-T3: TOD Compliance Assessment Framework

## Overview
Implement comprehensive Transit-Oriented Development compliance assessment framework integrating parking, density, and design requirements.

## Technical Requirements

### T3.1 TOD Compliance Engine
- **File**: `services/tod_compliance_checker.py`
- **Functionality**: Comprehensive TOD compliance assessment
- **Assessment Categories**:
  - Parking reduction compliance
  - Density bonus eligibility
  - Building height variations
  - Design excellence requirements
  - Public domain contributions

### T3.2 Compliance Rules Engine
- **File**: `services/tod_rules_engine.py`
- **Rule Sources**:
  - SEPP (Housing) 2021 TOD provisions
  - Local council TOD policies
  - Design and Place SEPP requirements
  - Transport for NSW design guidelines

### T3.3 Development Type Autocomplete
- **File**: `frontend-nextjs/components/tod/TODDevelopmentTypeSelector.tsx`
- **Features**:
  - Intelligent TOD-specific development type suggestions
  - Context-aware filtering based on zone and transport proximity
  - Visual indicators for TOD eligibility
  - Density and height range previews

### T3.4 Compliance Dashboard
- **File**: `frontend-nextjs/components/tod/TODComplianceDashboard.tsx`
- **Features**:
  - Real-time compliance status for all TOD criteria
  - Interactive compliance checklist
  - Automated report generation
  - Exception pathway identification

## Verification Criteria

### V3.1 Rule Engine Accuracy
- Correctly interpret SEPP (Housing) 2021 TOD provisions
- Accurate density bonus calculations
- Proper height variation assessments
- Valid design excellence pathway identification

### V3.2 Development Type Intelligence
- Suggest appropriate TOD development types
- Filter based on zone compatibility
- Accurate eligibility determination
- Clear visual feedback for selections

### V3.3 Compliance Assessment
- Complete assessment in under 2 seconds
- Identify all applicable TOD pathways
- Generate compliant planning reports
- Handle complex multi-criteria scenarios

## Implementation Steps

1. Create tod_compliance_checker.py with base rule definitions
2. Implement SEPP (Housing) 2021 TOD rule parsing
3. Build TODDevelopmentTypeSelector with smart filtering
4. Create TODComplianceDashboard with real-time updates
5. Integrate with existing compliance framework
6. Add comprehensive test suite with edge cases

## TOD Development Types

### Standard TOD Categories
```typescript
interface TODDevelopmentType {
  id: string;
  name: string;
  minTransportAccess: TransportLevel;
  maxDensityBonus: number;
  heightVariations: HeightRange[];
  parkingReductions: ParkingReduction[];
  designRequirements: DesignRequirement[];
}
```

### Transport Access Levels
- **Premium**: Heavy rail within 400m + high frequency bus
- **High**: Heavy rail within 800m OR light rail within 400m
- **Medium**: High frequency bus within 400m
- **Standard**: Medium frequency bus within 800m

## Compliance Assessment Matrix

### Parking Reductions
| Transport Level | Base Reduction | Additional Criteria | Max Reduction |
|----------------|----------------|-------------------|---------------|
| Premium        | 30%           | + Design Excellence | 50%          |
| High           | 20%           | + Public Domain     | 40%          |
| Medium         | 15%           | + Affordable Housing | 35%          |
| Standard       | 10%           | + Green Building    | 25%          |

### Density Bonuses
| Development Type | Base FSR | TOD Bonus | Design Bonus | Max FSR |
|-----------------|----------|-----------|--------------|---------|
| Multi Dwelling  | 0.75:1   | +50%      | +25%         | 1.4:1   |
| Residential Flat| 1.0:1    | +40%      | +20%         | 1.7:1   |
| Mixed Use       | 1.5:1    | +30%      | +15%         | 2.0:1   |

## Database Integration

```sql
-- TOD compliance results storage
CREATE TABLE tod_compliance_assessments (
    id SERIAL PRIMARY KEY,
    property_id INTEGER,
    development_type VARCHAR(100),
    transport_access_level VARCHAR(20),
    parking_reduction_percent DECIMAL(5,2),
    density_bonus_percent DECIMAL(5,2),
    height_variation_meters DECIMAL(6,2),
    compliance_status VARCHAR(20),
    assessment_date TIMESTAMP DEFAULT NOW(),
    assessment_data JSONB
);
```

## Success Metrics
- 100% accuracy for SEPP (Housing) 2021 interpretations
- Sub-2 second compliance assessment times
- Successful integration with existing compliance framework
- Generate planning-ready compliance reports

## Timeline
- Core compliance engine: 3 days
- Rule engine implementation: 2 days
- Development type selector: 2 days
- Compliance dashboard: 3 days
- Integration and testing: 2 days
- Total: 12 days