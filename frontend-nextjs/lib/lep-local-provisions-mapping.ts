/**
 * Map Type codes from Planning Portal "Local Provisions" layer
 * to Inner West LEP 2022 Part 6 clause numbers
 * 
 * Based on analysis of Inner West LEP 2022 Part 6 (pages 60-88)
 * 
 * NOTE: Only "SEP" is confirmed from actual Planning Portal API responses.
 * Other codes are inferred from LEP PDF analysis and will be updated
 * as we encounter them in real API responses.
 */

export interface LocalProvisionMapType {
  code: string;
  name: string;
  clauseNumbers: string[];
  description: string;
}

/**
 * Known Map Type mappings for Inner West LEP 2022 Part 6
 */
export const LOCAL_PROVISION_MAP_TYPES: Record<string, LocalProvisionMapType> = {
  // CONFIRMED from API
  'SEP': {
    code: 'SEP',
    name: 'Special Entertainment Precinct Map',
    clauseNumbers: ['6.32'],
    description: 'Extended trading hours, live music, and sound insulation requirements for entertainment precincts'
  },
  
  // INFERRED from PDF (to be confirmed)
  'LAM': {
    code: 'LAM',
    name: 'Land Application Map',
    clauseNumbers: ['6.33'],
    description: 'Affordable housing requirements for Stage 1 Bays West Precinct'
  },
  
  'KSM': {
    code: 'KSM',
    name: 'Key Sites Map',
    clauseNumbers: [
      '6.14', '6.15', '6.16', '6.17', '6.18', '6.19',
      '6.21', '6.22', '6.23', '6.24', '6.25', '6.27',
      '6.30', '6.31', '6.34'
    ],
    description: 'Site-specific development controls for identified key sites'
  },
  
  'HER': {
    code: 'HER',
    name: 'Heritage Map',
    clauseNumbers: ['6.20'],
    description: 'Development controls for Haberfield Heritage Conservation Area'
  },
  
  'ASS': {
    code: 'ASS',
    name: 'Acid Sulfate Soils Map',
    clauseNumbers: ['6.1'],
    description: 'Controls to prevent disturbance of acid sulfate soils'
  },
  
  'FBL': {
    code: 'FBL',
    name: 'Foreshore Building Line Map',
    clauseNumbers: ['6.5', '6.6'],
    description: 'Development limitations on foreshore areas'
  },
  
  'APU': {
    code: 'APU',
    name: 'Additional Permitted Use Map',
    clauseNumbers: ['6.26'],
    description: 'Additional permitted uses for specific sites'
  }
};

/**
 * Get clause numbers for a Map Type code
 */
export function getClauseNumbersForMapType(mapType: string): string[] {
  const mapping = LOCAL_PROVISION_MAP_TYPES[mapType];
  return mapping ? mapping.clauseNumbers : [];
}

/**
 * Get provision info for a Map Type code
 */
export function getProvisionInfoForMapType(mapType: string): LocalProvisionMapType | null {
  return LOCAL_PROVISION_MAP_TYPES[mapType] || null;
}

/**
 * Check if a Map Type code is known
 */
export function isKnownMapType(mapType: string): boolean {
  return mapType in LOCAL_PROVISION_MAP_TYPES;
}
