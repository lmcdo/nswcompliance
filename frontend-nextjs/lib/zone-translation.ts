/**
 * PART 2: Zone Translation Mapping
 *
 * NSW Employment Zones Reform (April 26, 2023) replaced Business/Industrial zones
 * with new Employment zones. This mapping allows queries using new zone codes
 * to find provisions tagged with legacy codes.
 *
 * Background:
 * - Documents extracted before 2023 use B1, B2, IN1, etc.
 * - NSW Planning Portal API returns E1, E2, E4, etc. (current codes)
 * - Database preserves original zone codes as written in documents
 * - Query-time translation bridges the gap
 */

/**
 * Zone translation mapping: Current zone → [Current + Legacy equivalents]
 */
export const ZONE_TRANSLATION_MAP: Record<string, string[]> = {
  // E1 Local Centre (replaces B1 Neighbourhood Centre + B2 Local Centre)
  'E1': ['E1', 'B1', 'B2'],

  // E2 Commercial Centre (replaces B3 Commercial Core + B4 Mixed Use + B8 Metropolitan)
  'E2': ['E2', 'B3', 'B4', 'B8'],

  // E3 Productivity Support (replaces B5 Business Development + B6 Enterprise Corridor + B7 Business Park)
  'E3': ['E3', 'B5', 'B6', 'B7'],

  // E4 General Industrial (replaces IN1 General Industrial + IN4 Working Waterfront)
  'E4': ['E4', 'IN1', 'IN4'],

  // E5 Heavy Industrial (replaces IN2 Light Industrial + IN3 Heavy Industrial)
  'E5': ['E5', 'IN2', 'IN3'],

  // Current zones without legacy equivalents (already in new standard)
  'MU1': ['MU1'],  // Mixed Use
  'R1': ['R1'],    // General Residential
  'R2': ['R2'],    // Low Density Residential
  'R3': ['R3'],    // Medium Density Residential
  'R4': ['R4'],    // High Density Residential
  'R5': ['R5'],    // Large Lot Residential
  'RE1': ['RE1'],  // Public Recreation
  'RE2': ['RE2'],  // Private Recreation
  'C1': ['C1'],    // National Parks and Nature Reserves
  'C2': ['C2'],    // Environmental Conservation
  'C3': ['C3'],    // Environmental Management
  'C4': ['C4'],    // Environmental Living
  'W1': ['W1'],    // Natural Waterways
  'W2': ['W2'],    // Recreational Waterways
  'W3': ['W3'],    // Working Waterways
  'W4': ['W4'],    // Working Waterfront
  'SP1': ['SP1'],  // Special Activities
  'SP2': ['SP2'],  // Infrastructure
  'SP3': ['SP3'],  // Tourist
  'SP4': ['SP4'],  // Enterprise
  'SP5': ['SP5'],  // Metropolitan Centre
};

/**
 * Legacy zone codes (pre-April 2023)
 * These should only appear in database, never in API requests
 */
export const LEGACY_ZONES = [
  'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8',  // Business zones
  'IN1', 'IN2', 'IN3', 'IN4'                       // Industrial zones
];

/**
 * Get zone aliases for a given zone code
 * Returns array including both current and legacy equivalents
 *
 * @param zone - The zone code from API request (should be current code like E1)
 * @returns Array of zone codes to search ([current, ...legacy])
 *
 * @example
 * getZoneAliases('E1') // Returns ['E1', 'B1', 'B2']
 * getZoneAliases('R2') // Returns ['R2'] (no legacy equivalent)
 * getZoneAliases('B1') // Returns ['E1', 'B1', 'B2'] (translates legacy to current)
 */
export function getZoneAliases(zone: string): string[] {
  // If zone is already in translation map, return its aliases
  if (zone in ZONE_TRANSLATION_MAP) {
    return ZONE_TRANSLATION_MAP[zone];
  }

  // If zone is a legacy code, find its current equivalent
  if (LEGACY_ZONES.includes(zone)) {
    // Find which current zone this legacy zone maps to
    for (const [currentZone, aliases] of Object.entries(ZONE_TRANSLATION_MAP)) {
      if (aliases.includes(zone)) {
        return aliases; // Return full alias list including current zone
      }
    }
  }

  // Unknown zone - return as-is (will search only that zone)
  return [zone];
}

/**
 * Build SQL IN clause for zone search
 *
 * @param zone - The zone code to search for
 * @param parameterIndex - Starting index for SQL parameters (e.g., $1, $2, $3)
 * @returns Object with SQL fragment and parameter values
 *
 * @example
 * buildZoneInClause('E1', 1)
 * // Returns: { sql: 'zone IN ($1, $2, $3)', params: ['E1', 'B1', 'B2'] }
 */
export function buildZoneInClause(zone: string, parameterIndex: number = 1): {
  sql: string;
  params: string[];
} {
  const aliases = getZoneAliases(zone);
  const placeholders = aliases.map((_, i) => `$${parameterIndex + i}`).join(', ');

  return {
    sql: `zone IN (${placeholders})`,
    params: aliases
  };
}

/**
 * Check if a zone code is legacy (pre-April 2023)
 *
 * @param zone - Zone code to check
 * @returns true if zone is a legacy code
 */
export function isLegacyZone(zone: string): boolean {
  return LEGACY_ZONES.includes(zone);
}

/**
 * Get current zone equivalent for a legacy zone
 *
 * @param legacyZone - Legacy zone code (e.g., 'B1')
 * @returns Current zone code (e.g., 'E1') or null if not found
 *
 * @example
 * getCurrentZone('B1') // Returns 'E1'
 * getCurrentZone('IN1') // Returns 'E4'
 */
export function getCurrentZone(legacyZone: string): string | null {
  for (const [currentZone, aliases] of Object.entries(ZONE_TRANSLATION_MAP)) {
    if (aliases.includes(legacyZone) && currentZone !== legacyZone) {
      return currentZone;
    }
  }
  return null;
}
