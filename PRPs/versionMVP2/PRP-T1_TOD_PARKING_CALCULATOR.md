# PRP-T1: TOD Parking Reduction Calculator Implementation

## Overview
Implement Transit-Oriented Development (TOD) parking reduction calculator with NSW planning compliance framework integration.

## Technical Requirements

### T1.1 Core Calculator Component
- **File**: `frontend-nextjs/components/tod/TODParkingCalculator.tsx`
- **Functionality**: Calculate parking reductions based on transport proximity and development type
- **Input Parameters**:
  - Development type (dwelling_house, dual_occupancy, multi_dwelling_housing, residential_flat_building)
  - Unit count (auto-calculated from GFA or user input)
  - Transport proximity data (from property API)
  - Zone code context

### T1.2 Parking Reduction Logic
- **Base Rates**: Standard NSW parking requirements by development type
- **Reduction Factors**:
  - Within 400m of train station: 30% reduction
  - Within 800m of train station: 20% reduction
  - High frequency bus (every 15min): 15% reduction
  - Medium frequency bus (every 30min): 10% reduction
  - Combined transport access: Additional 10% reduction (max 50% total)

### T1.3 Data Integration
- **Transport Data Source**: NSW Planning Portal property layers
- **Integration Point**: `enhanced_compliance_api.py` transport proximity detection
- **Fallback**: Manual transport proximity input if API data unavailable

### T1.4 UI Components
- **Calculator Display**: Real-time parking requirement calculation
- **Reduction Breakdown**: Visual breakdown of reduction factors applied
- **Compliance Status**: Pass/fail indicator for TOD parking requirements
- **Export Functionality**: PDF report generation for planning applications

## Verification Criteria

### V1.1 Calculator Accuracy
- Calculate correct base parking rates for all development types
- Apply reduction factors accurately based on transport proximity
- Handle edge cases (zero reductions, maximum reductions)

### V1.2 Data Integration
- Successfully fetch transport proximity from property API
- Handle API failures gracefully with manual input fallback
- Cache transport data for performance

### V1.3 UI Responsiveness
- Calculator updates in real-time as inputs change
- Clear visual feedback for all reduction factors
- Accessible design meeting WCAG 2.1 AA standards

## Implementation Steps

1. Create TODParkingCalculator component with base parking rate lookup
2. Implement transport proximity detection in backend
3. Add reduction calculation logic with validation
4. Integrate with existing AuthoritativeComplianceDisplay
5. Add export functionality for planning reports
6. Create comprehensive test suite

## Dependencies
- React TypeScript components
- NSW Planning Portal API integration
- Existing compliance framework
- PDF generation library (react-pdf or jsPDF)

## Success Metrics
- Accurate parking calculations for 100% of test cases
- Sub-500ms response time for calculator updates
- Successfully processes all NSW development types
- Generates compliant planning reports

## Timeline
- Setup and base component: 1 day
- Transport integration: 1 day
- Calculator logic and testing: 2 days
- UI polish and export: 1 day
- Total: 5 days