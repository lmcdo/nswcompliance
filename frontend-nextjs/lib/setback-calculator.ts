/**
 * Setback Calculator
 * Calculates required setbacks based on:
 * - Lot boundaries and area
 * - Road classifications
 * - Reserve boundaries
 * - DCP rules (Ashfield, Marrickville, Leichhardt)
 */

import { SetbackBoundaries, RoadBoundary, ReserveBoundary } from './spatial-boundary-service';

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

export interface SetbackRequirements {
  front: SetbackRule;
  rear: SetbackRule;
  side_primary: SetbackRule;
  side_secondary: SetbackRule;
  additional_notes: string[];
}

export interface SetbackRule {
  value_meters: number;
  min_value?: number;
  max_value?: number;
  reason: string;
  dcp_reference: string;
  boundary_type: 'road' | 'reserve' | 'lot' | 'other';
  compliance_status?: 'compliant' | 'non-compliant' | 'unknown';
}

export type FormerCouncil = 'Ashfield' | 'Marrickville' | 'Leichhardt';

// ============================================================================
// COUNCIL-SPECIFIC SETBACK RULES
// ============================================================================

/**
 * Ashfield DCP 2016 - Chapter F Setback Rules
 * Front setback based on lot area + road classification
 */
function calculateAshfieldSetbacks(
  boundaries: SetbackBoundaries,
  zone: string,
  developmentType: string
): SetbackRequirements {
  const lotArea = boundaries.lot.area_sqm;
  const primaryRoad = boundaries.roads.find(r => r.is_primary_frontage) || boundaries.roads[0];

  // Front setback (to primary road)
  let frontSetback: SetbackRule;

  if (primaryRoad && primaryRoad.classification === 'primary') {
    // Primary road setback varies by lot area
    if (lotArea < 450) {
      frontSetback = {
        value_meters: 4.5,
        reason: `Lot area ${lotArea.toFixed(0)}sqm < 450sqm - Primary road frontage`,
        dcp_reference: 'Ashfield DCP 2016 Chapter F Section 1.2',
        boundary_type: 'road'
      };
    } else if (lotArea < 600) {
      frontSetback = {
        value_meters: 6.5,
        reason: `Lot area ${lotArea.toFixed(0)}sqm (450-600sqm) - Primary road frontage`,
        dcp_reference: 'Ashfield DCP 2016 Chapter F Section 1.2',
        boundary_type: 'road'
      };
    } else {
      frontSetback = {
        value_meters: 10,
        reason: `Lot area ${lotArea.toFixed(0)}sqm > 600sqm - Primary road frontage`,
        dcp_reference: 'Ashfield DCP 2016 Chapter F Section 1.2',
        boundary_type: 'road'
      };
    }
  } else {
    // Local/secondary road setback (default)
    frontSetback = {
      value_meters: 5.5,
      reason: `Local road frontage (${primaryRoad?.name || 'Unknown road'})`,
      dcp_reference: 'Ashfield DCP 2016 Chapter F Section 1.2',
      boundary_type: 'road'
    };
  }

  // Rear setback
  const adjacentReserve = boundaries.reserves.find(r => r.is_adjacent);
  const rearSetback: SetbackRule = adjacentReserve
    ? {
        value_meters: 3,
        reason: `Adjacent to ${adjacentReserve.name} (${adjacentReserve.type})`,
        dcp_reference: 'Ashfield DCP 2016 Chapter F Section 1.3',
        boundary_type: 'reserve'
      }
    : {
        value_meters: 6,
        reason: 'Standard rear setback to rear lot boundary',
        dcp_reference: 'Ashfield DCP 2016 Chapter F Section 1.3',
        boundary_type: 'lot'
      };

  // Side setbacks (simplified - actual rules are more complex)
  const sideSetbackPrimary: SetbackRule = {
    value_meters: 0.9,
    reason: 'Minimum side setback for single storey',
    dcp_reference: 'Ashfield DCP 2016 Chapter F Section 1.4',
    boundary_type: 'lot'
  };

  const sideSetbackSecondary: SetbackRule = {
    value_meters: 0.9,
    reason: 'Minimum side setback for single storey',
    dcp_reference: 'Ashfield DCP 2016 Chapter F Section 1.4',
    boundary_type: 'lot'
  };

  return {
    front: frontSetback,
    rear: rearSetback,
    side_primary: sideSetbackPrimary,
    side_secondary: sideSetbackSecondary,
    additional_notes: [
      'Setbacks may increase for buildings over 2 storeys',
      'Check DCP for specific development type variations',
      adjacentReserve ? `Property adjoins ${adjacentReserve.name} - special provisions may apply` : ''
    ].filter(Boolean)
  };
}

/**
 * Marrickville DCP 2011 Setback Rules
 * Front setback based on street character and development type
 */
function calculateMarrickvilleSetbacks(
  boundaries: SetbackBoundaries,
  zone: string,
  developmentType: string
): SetbackRequirements {
  const lotArea = boundaries.lot.area_sqm;
  const primaryRoad = boundaries.roads.find(r => r.is_primary_frontage) || boundaries.roads[0];

  // Front setback (varies by development type)
  let frontSetback: SetbackRule;

  if (developmentType === 'dual_occupancy') {
    frontSetback = {
      value_meters: 5.5,
      min_value: 4,
      max_value: 6,
      reason: 'Dual occupancy front setback range',
      dcp_reference: 'Marrickville DCP 2011 Part 4.1',
      boundary_type: 'road'
    };
  } else if (developmentType === 'multi_dwelling') {
    frontSetback = {
      value_meters: 6,
      reason: 'Multi-dwelling housing front setback',
      dcp_reference: 'Marrickville DCP 2011 Part 4.2',
      boundary_type: 'road'
    };
  } else {
    frontSetback = {
      value_meters: 5.5,
      reason: `Standard front setback for ${developmentType.replace(/_/g, ' ')}`,
      dcp_reference: 'Marrickville DCP 2011 Part 4',
      boundary_type: 'road'
    };
  }

  // Rear setback
  const adjacentReserve = boundaries.reserves.find(r => r.is_adjacent);
  const rearSetback: SetbackRule = adjacentReserve
    ? {
        value_meters: 3,
        reason: `Adjacent to ${adjacentReserve.name} (${adjacentReserve.type})`,
        dcp_reference: 'Marrickville DCP 2011 Part 2.3',
        boundary_type: 'reserve'
      }
    : {
        value_meters: 6,
        reason: 'Minimum rear setback',
        dcp_reference: 'Marrickville DCP 2011 Part 2.3',
        boundary_type: 'lot'
      };

  // Side setbacks
  const sideSetbackPrimary: SetbackRule = {
    value_meters: 0.9,
    reason: 'Minimum side setback (single storey)',
    dcp_reference: 'Marrickville DCP 2011 Part 2.3',
    boundary_type: 'lot'
  };

  const sideSetbackSecondary: SetbackRule = {
    value_meters: 0.9,
    reason: 'Minimum side setback (single storey)',
    dcp_reference: 'Marrickville DCP 2011 Part 2.3',
    boundary_type: 'lot'
  };

  return {
    front: frontSetback,
    rear: rearSetback,
    side_primary: sideSetbackPrimary,
    side_secondary: sideSetbackSecondary,
    additional_notes: [
      'Front setback should match prevailing street character',
      'Increased setbacks required for multi-storey development',
      adjacentReserve ? `Property adjoins ${adjacentReserve.name}` : ''
    ].filter(Boolean)
  };
}

/**
 * Leichhardt DCP 2013 Setback Rules
 * Universal provisions (no zone/devtype filtering)
 */
function calculateLeichhardtSetbacks(
  boundaries: SetbackBoundaries,
  zone: string,
  developmentType: string
): SetbackRequirements {
  const lotArea = boundaries.lot.area_sqm;
  const primaryRoad = boundaries.roads.find(r => r.is_primary_frontage) || boundaries.roads[0];

  // Front setback
  const frontSetback: SetbackRule = {
    value_meters: 5.5,
    reason: 'Standard front setback to street boundary',
    dcp_reference: 'Leichhardt DCP 2013 Part C Section 1',
    boundary_type: 'road'
  };

  // Rear setback
  const adjacentReserve = boundaries.reserves.find(r => r.is_adjacent);
  const rearSetback: SetbackRule = adjacentReserve
    ? {
        value_meters: 3,
        reason: `Adjacent to ${adjacentReserve.name} (${adjacentReserve.type})`,
        dcp_reference: 'Leichhardt DCP 2013 Part C',
        boundary_type: 'reserve'
      }
    : {
        value_meters: 6,
        reason: 'Minimum rear setback',
        dcp_reference: 'Leichhardt DCP 2013 Part C',
        boundary_type: 'lot'
      };

  // Side setbacks
  const sideSetbackPrimary: SetbackRule = {
    value_meters: 0.9,
    reason: 'Minimum side setback',
    dcp_reference: 'Leichhardt DCP 2013 Part C',
    boundary_type: 'lot'
  };

  const sideSetbackSecondary: SetbackRule = {
    value_meters: 0.9,
    reason: 'Minimum side setback',
    dcp_reference: 'Leichhardt DCP 2013 Part C',
    boundary_type: 'lot'
  };

  return {
    front: frontSetback,
    rear: rearSetback,
    side_primary: sideSetbackPrimary,
    side_secondary: sideSetbackSecondary,
    additional_notes: [
      'Setbacks should respect neighbourhood character',
      adjacentReserve ? `Property adjoins ${adjacentReserve.name}` : ''
    ].filter(Boolean)
  };
}

// ============================================================================
// MAIN CALCULATOR FUNCTION
// ============================================================================

/**
 * Calculate all required setbacks for a property
 *
 * @param boundaries Spatial boundary data (lot, roads, reserves)
 * @param zone LEP zone (R1, R2, B1, etc)
 * @param developmentType Type of development (dual_occupancy, single_dwelling, etc)
 * @param formerCouncil Which former council area (Ashfield, Marrickville, Leichhardt)
 * @returns Complete setback requirements with explanations
 */
export function calculateSetbacks(
  boundaries: SetbackBoundaries,
  zone: string,
  developmentType: string,
  formerCouncil: FormerCouncil
): SetbackRequirements {
  console.log(`[Setback Calculator] Calculating for ${formerCouncil} - Zone: ${zone}, Dev Type: ${developmentType}`);
  console.log(`[Setback Calculator] Lot area: ${boundaries.lot.area_sqm}sqm, Roads: ${boundaries.roads.length}, Reserves: ${boundaries.reserves.length}`);

  switch (formerCouncil) {
    case 'Ashfield':
      return calculateAshfieldSetbacks(boundaries, zone, developmentType);
    case 'Marrickville':
      return calculateMarrickvilleSetbacks(boundaries, zone, developmentType);
    case 'Leichhardt':
      return calculateLeichhardtSetbacks(boundaries, zone, developmentType);
    default:
      throw new Error(`Unknown former council: ${formerCouncil}`);
  }
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Format setback requirements for display in UI
 */
export function formatSetbacksForDisplay(setbacks: SetbackRequirements): string {
  const lines = [
    `Front: ${setbacks.front.value_meters}m (${setbacks.front.reason})`,
    `Rear: ${setbacks.rear.value_meters}m (${setbacks.rear.reason})`,
    `Side (primary): ${setbacks.side_primary.value_meters}m (${setbacks.side_primary.reason})`,
    `Side (secondary): ${setbacks.side_secondary.value_meters}m (${setbacks.side_secondary.reason})`
  ];

  if (setbacks.additional_notes.length > 0) {
    lines.push('');
    lines.push('Additional Notes:');
    setbacks.additional_notes.forEach(note => lines.push(`- ${note}`));
  }

  return lines.join('\n');
}

/**
 * Check if proposed setbacks meet requirements
 */
export function checkSetbackCompliance(
  required: SetbackRequirements,
  proposed: { front: number; rear: number; side_primary: number; side_secondary: number }
): { compliant: boolean; violations: string[] } {
  const violations: string[] = [];

  if (proposed.front < required.front.value_meters) {
    violations.push(`Front setback: ${proposed.front}m provided, ${required.front.value_meters}m required`);
  }

  if (proposed.rear < required.rear.value_meters) {
    violations.push(`Rear setback: ${proposed.rear}m provided, ${required.rear.value_meters}m required`);
  }

  if (proposed.side_primary < required.side_primary.value_meters) {
    violations.push(`Side (primary) setback: ${proposed.side_primary}m provided, ${required.side_primary.value_meters}m required`);
  }

  if (proposed.side_secondary < required.side_secondary.value_meters) {
    violations.push(`Side (secondary) setback: ${proposed.side_secondary}m provided, ${required.side_secondary.value_meters}m required`);
  }

  return {
    compliant: violations.length === 0,
    violations
  };
}
