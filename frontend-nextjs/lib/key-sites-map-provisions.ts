/**
 * Key Sites Map (KSM) Provision Mappings
 * Maps KSM clause numbers to their page numbers in Inner West LEP 2022
 *
 * Part 4 clauses: General development controls applying to Key Sites
 * Part 6 clauses: Site-specific controls for individual Key Sites
 */

export interface KeySitesProvision {
  clauseNumber: string;
  title: string;
  pageNumber: number;
  part: 4 | 6;
  applicableZones?: string[]; // If specified, only show for these zones
}

export const KEY_SITES_PROVISIONS: KeySitesProvision[] = [
  // Part 4 - General Key Sites controls
  {
    clauseNumber: '4.3C',
    title: 'Landscaped areas for residential accommodation in Zone R1',
    pageNumber: 37,
    part: 4,
    applicableZones: ['R1'] // Only applies to R1 zone
  },
  {
    clauseNumber: '4.4',
    title: 'Floor space ratio',
    pageNumber: 39,
    part: 4
    // No zone restriction - applies to all Key Sites
  },

  // Part 6 - Site-specific Key Sites (verified against LEP PDF, April 2025 version)
  // Clauses 6.1-6.15 are general environmental/planning provisions - NOT site-specific
  // Clauses 6.21-6.23 are zone-based general provisions (E3/E4) - NOT site-specific
  // Clause 6.33 is "Affordable housing" - a general provision, NOT site-specific
  // Only clauses below are actual site-specific Key Sites with street addresses
  {
    clauseNumber: '6.16',
    title: 'Development of land at 141 and 159 Allen Street, Leichhardt',
    pageNumber: 74,
    part: 6
  },
  {
    clauseNumber: '6.17',
    title: 'Development of land at 168 Norton Street, Leichhardt',
    pageNumber: 75,
    part: 6
  },
  {
    clauseNumber: '6.18',
    title: 'Development of land at 101–103 Lilyfield Road, Lilyfield',
    pageNumber: 76,
    part: 6
  },
  {
    clauseNumber: '6.19',
    title: 'Development of land at 17 Marion Street, Leichhardt',
    pageNumber: 76,
    part: 6
  },
  {
    clauseNumber: '6.20',
    title: 'Development on land in Haberfield Heritage Conservation Area',
    pageNumber: 77,
    part: 6
  },
  {
    clauseNumber: '6.24',
    title: 'Development of land at 1–5 Chester Street, Annandale',
    pageNumber: 80,
    part: 6
  },
  {
    clauseNumber: '6.25',
    title: 'Development of land at 469–483 Balmain Road, Lilyfield',
    pageNumber: 81,
    part: 6
  },
  {
    clauseNumber: '6.26',
    title: 'Development at 287–309 Trafalgar Street, Petersham',
    pageNumber: 83,
    part: 6
  },
  {
    clauseNumber: '6.27',
    title: '50–52 Edith Street, 67 and 73–83 Mary Street and 43 Roberts Street, St Peters',
    pageNumber: 83,
    part: 6
  },
  {
    clauseNumber: '6.30',
    title: 'Development of land at 36 Lonsdale Street and 64–70 Brenan Street, Lilyfield',
    pageNumber: 85,
    part: 6
  },
  {
    clauseNumber: '6.31',
    title: 'Development on certain land at Victoria Road, Marrickville',
    pageNumber: 86,
    part: 6
  },
  {
    clauseNumber: '6.32',
    title: 'Special entertainment precinct',
    pageNumber: 87,
    part: 6
  },
  {
    clauseNumber: '6.34',
    title: 'Development of certain land at Alma Avenue and Stanmore Road, Stanmore and Tupper Street, Enmore',
    pageNumber: 88,
    part: 6
  }
];

/**
 * Get provision details for a Key Sites Map clause
 */
export function getKeySitesProvision(clauseNumber: string): KeySitesProvision | undefined {
  return KEY_SITES_PROVISIONS.find(p => p.clauseNumber === clauseNumber);
}

/**
 * Get page number for a Key Sites Map clause
 */
export function getKeySitesPageNumber(clauseNumber: string): number | undefined {
  return getKeySitesProvision(clauseNumber)?.pageNumber;
}

/**
 * Check if a clause is a Key Sites provision
 */
export function isKeySitesClause(clauseNumber: string): boolean {
  return KEY_SITES_PROVISIONS.some(p => p.clauseNumber === clauseNumber);
}
