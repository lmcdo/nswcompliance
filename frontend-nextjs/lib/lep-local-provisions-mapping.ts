/**
 * Map Type codes from Planning Portal "Local Provisions" layer → LEP clause numbers.
 *
 * Architecture: EPI-name-specific mappings take priority; global (Inner West) codes
 * are the fallback for backward compatibility.
 *
 * Planning Portal returns:
 *   - Abbreviated codes (SEP, KSM…) for Inner West
 *   - Full map names ("Additional Local Provisions Map"…) for Parramatta and others
 *
 * Audit status per LEP — last updated 2026-03-05:
 *   Inner West LEP 2022        ✅ SEP confirmed; KSM/LAM/HER/ASS/FBL/APU inferred from PDF
 *   Parramatta LEP 2023        ⚠️  Full map names. 7.1/7.9/7.21 from legislation; IUA/LTI unknown
 *   Waverley LEP 2012          ⚠️  Standard Part 6 (6.1–6.14), no complex map provisions expected
 *   Woollahra LEP 2014         ⚠️  Standard Part 6 (6.1–6.7), no complex map provisions expected
 *   Ku-ring-gai LEP 2015       ⚠️  Standard Part 6 (6.1–6.13), no complex map provisions expected
 *   City of Sydney LEP 2012    ❌  Not yet mapped — needs dedicated research
 *
 * TODO: Verify all codes against live Planning Portal API responses for each LGA.
 */

export interface LocalProvisionMapType {
  code: string;
  name: string;
  clauseNumbers: string[];
  description: string;
}

// ---------------------------------------------------------------------------
// Global fallback — Inner West LEP 2022 abbreviated codes
// (used when no EPI-specific entry matches)
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// EPI-specific mappings — keyed on exact EPI Name string from Planning Portal
// Takes priority over the global fallback above.
// ---------------------------------------------------------------------------

const EPI_CLAUSE_MAPPINGS: Record<string, Record<string, string[]>> = {

  // Parramatta Local Environmental Plan 2023 (epi-2023-0117)
  // legislation.nsw.gov.au/view/html/inforce/current/epi-2023-0117
  // Planning Portal returns FULL MAP NAMES (not abbreviated codes) for this LGA.
  // Source: AustLII consolidated text + NSW Legislation TOC (verified 2026-03-05)
  'Parramatta Local Environmental Plan 2023': {
    // Part 7 — Additional Local Provisions (Parramatta City Centre)
    'Additional Local Provisions Map': ['7.1'],  // cl 7.1 — land to which Part 7 applies
    'ALM':                             ['7.1'],  // abbreviated code if returned
    'Floodplain Risk Management Map':  ['7.9'],  // cl 7.9 — floodplain risk management (City Centre)
    'FRM':                             ['7.9'],
    'Special Provisions Area Map':     ['7.21'], // cl 7.21 — Division 5 (other than Area A)
    'SPA':                             ['7.21'],
    // TODO: verify clause numbers for these from live API + legislation text
    'Intensive Urban Development Area Map': [],  // UNKNOWN — needs verification
    'IUA':                                  [],
    'Land Use and Transport Integration Map': [], // UNKNOWN — needs verification
    'LTI':                                    [],
    // Part 6 standard clauses (same numbers as standard instrument)
    'Acid Sulfate Soils Map': ['6.1'],
    'ASS':                    ['6.1'],
  },

  // Waverley Local Environmental Plan 2012 (epi-2012-0540)
  // Part 6 clauses 6.1–6.14 — all standard instrument, no complex map provisions
  // Source: AustLII consolidated text (verified 2026-03-05)
  // TODO: confirm mapType codes returned by Planning Portal for Waverley properties
  'Waverley Local Environmental Plan 2012': {
    'ASS': ['6.1'],
    'Acid Sulfate Soils Map': ['6.1'],
  },

  // Woollahra Local Environmental Plan 2014 (epi-2014-?)
  // Part 6 clauses 6.1–6.7 — standard instrument, no map-based complex provisions
  // Source: AustLII consolidated text (verified 2026-03-05)
  'Woollahra Local Environmental Plan 2014': {
    'ASS': ['6.1'],
    'Acid Sulfate Soils Map': ['6.1'],
    'FLD': ['6.3'],  // Flood planning
    'Flood Planning Map': ['6.3'],
  },

  // Ku-ring-gai Local Environmental Plan 2015 (epi-2015-?)
  // Part 6 clauses 6.1–6.13 — standard instrument
  // Source: AustLII consolidated text (verified 2026-03-05)
  'Ku-ring-gai Local Environmental Plan 2015': {
    'ASS': ['6.1'],
    'Acid Sulfate Soils Map': ['6.1'],
    'Riparian Land and Waterways Map': ['6.4'],
    'Stormwater Management Map': ['6.5'],
  },

  // City of Sydney Local Environmental Plan 2012 (epi-2012-0628)
  // TODO: research Part 6 clause structure — complex, deferred
  'Sydney Local Environmental Plan 2012': {},
};

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Get clause numbers for a mapType code/name, with optional EPI name for LGA-specific lookup.
 * EPI-specific entries take priority over the global Inner West fallback.
 */
export function getClauseNumbersForMapType(mapType: string, epiName?: string): string[] {
  if (epiName) {
    const epiMap = EPI_CLAUSE_MAPPINGS[epiName];
    if (epiMap) {
      const clauses = epiMap[mapType];
      if (clauses !== undefined) return clauses;
    }
  }
  // Fall back to global Inner West codes
  return LOCAL_PROVISION_MAP_TYPES[mapType]?.clauseNumbers ?? [];
}

export function getProvisionInfoForMapType(mapType: string): LocalProvisionMapType | null {
  return LOCAL_PROVISION_MAP_TYPES[mapType] || null;
}

export function isKnownMapType(mapType: string): boolean {
  return mapType in LOCAL_PROVISION_MAP_TYPES;
}
