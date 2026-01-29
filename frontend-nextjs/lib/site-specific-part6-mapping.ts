/**
 * Mapping of site-specific Part 6 LEP provisions
 * Legal compliance: Uses Lot/DP numbers (most accurate) and street addresses
 */

export interface SiteSpecificProvision {
  clauseNumber: string;
  title: string;
  pageNumber: number;
  // Lot/DP identifiers - most reliable for matching
  lotDp?: string[];
  // Street address - for user-friendly matching
  streetAddresses?: string[];
}

export const SITE_SPECIFIC_PART6: SiteSpecificProvision[] = [
  // Clauses 6.1-6.15 are general environmental/planning provisions — NOT site-specific
  // Clauses 6.21-6.23 are zone-based general provisions (E3/E4) — NOT site-specific
  // Clause 6.33 is "Affordable housing" — a general provision, NOT site-specific
  // Clauses 6.28-6.29 do not exist in this LEP version (numbering skips 6.27 to 6.30)
  {
    clauseNumber: '6.16',
    title: 'Development of land at 141 and 159 Allen Street, Leichhardt',
    pageNumber: 74,
    lotDp: ['Lot 1, DP 632522'],
    streetAddresses: ['141 Allen Street, Leichhardt', '159 Allen Street, Leichhardt']
  },
  {
    clauseNumber: '6.17',
    title: 'Development of land at 168 Norton Street, Leichhardt',
    pageNumber: 75,
    lotDp: ['Lot 1, DP 963000', 'Lot 5, DP 1112635'],
    streetAddresses: ['168 Norton Street, Leichhardt']
  },
  {
    clauseNumber: '6.18',
    title: 'Development of land at 101–103 Lilyfield Road, Lilyfield',
    pageNumber: 76,
    lotDp: ['Lot 1, DP 432612'],
    streetAddresses: ['101 Lilyfield Road, Lilyfield', '103 Lilyfield Road, Lilyfield']
  },
  {
    clauseNumber: '6.19',
    title: 'Development of land at 17 Marion Street, Leichhardt',
    pageNumber: 76,
    lotDp: ['Lot 21, Section 1, DP 328', 'Lot 22, Section 1, DP 328', 'Lot 24, Section 1, DP 328', 'Lot 25, Section 1, DP 328', 'Lot A, DP 377714', 'Lot B, DP 377714'],
    streetAddresses: ['17 Marion Street, Leichhardt']
  },
  {
    clauseNumber: '6.20',
    title: 'Development on land in Haberfield Heritage Conservation Area',
    pageNumber: 77,
    // Applies to all C54 heritage items, not specific lot/DP
    streetAddresses: [] // Matched by heritage item C54
  },
  {
    clauseNumber: '6.24',
    title: 'Development of land at 1–5 Chester Street, Annandale',
    pageNumber: 80,
    lotDp: ['Lot 11, DP 499846'],
    streetAddresses: ['1 Chester Street, Annandale', '3 Chester Street, Annandale', '5 Chester Street, Annandale']
  },
  {
    clauseNumber: '6.25',
    title: 'Development of land at 469–483 Balmain Road, Lilyfield',
    pageNumber: 81,
    lotDp: ['Lot 2, DP 1015843'],
    streetAddresses: ['469 Balmain Road, Lilyfield', '471 Balmain Road, Lilyfield', '473 Balmain Road, Lilyfield', '475 Balmain Road, Lilyfield', '477 Balmain Road, Lilyfield', '479 Balmain Road, Lilyfield', '481 Balmain Road, Lilyfield', '483 Balmain Road, Lilyfield']
  },
  {
    clauseNumber: '6.26',
    title: 'Development at 287–309 Trafalgar Street, Petersham',
    pageNumber: 83,
    lotDp: ['Lot 1, DP 1208130', 'Lot 10, DP 1004198', 'Lot 100, DP 1283113'],
    streetAddresses: ['287 Trafalgar Street, Petersham', '289 Trafalgar Street, Petersham', '291 Trafalgar Street, Petersham', '293 Trafalgar Street, Petersham', '295 Trafalgar Street, Petersham', '297 Trafalgar Street, Petersham', '299 Trafalgar Street, Petersham', '301 Trafalgar Street, Petersham', '303 Trafalgar Street, Petersham', '305 Trafalgar Street, Petersham', '307 Trafalgar Street, Petersham', '309 Trafalgar Street, Petersham']
  },
  {
    clauseNumber: '6.27',
    title: '50–52 Edith Street, 67 and 73–83 Mary Street and 43 Roberts Street, St Peters',
    pageNumber: 83,
    streetAddresses: ['50 Edith Street, St Peters', '52 Edith Street, St Peters', '67 Mary Street, St Peters', '73 Mary Street, St Peters', '43 Roberts Street, St Peters']
  },
  {
    clauseNumber: '6.30',
    title: 'Development of land at 36 Lonsdale Street and 64–70 Brenan Street, Lilyfield',
    pageNumber: 85,
    lotDp: ['Lot 2, DP 1257743', 'Lot 3, DP 1257743', 'Lot 4, DP 1257743', 'Lot 1, DP 529451', 'Lot 2, DP 529451', 'Lot 22, DP 977323', 'Lot 1, DP 1057904'],
    streetAddresses: ['36 Lonsdale Street, Lilyfield', '64 Brenan Street, Lilyfield', '66 Brenan Street, Lilyfield', '68 Brenan Street, Lilyfield', '70 Brenan Street, Lilyfield']
  },
  {
    clauseNumber: '6.31',
    title: 'Development on certain land at Victoria Road, Marrickville',
    pageNumber: 86,
    // Uses "Area 13" on Key Sites Map - no specific lot/DP in provision text
    streetAddresses: [] // Requires Key Sites Map matching
  },
  {
    clauseNumber: '6.32',
    title: 'Special Entertainment Precinct Map',
    pageNumber: 87,
    streetAddresses: [] // Matched by SEP map type from Planning Portal
  },
  {
    clauseNumber: '6.34',
    title: 'Development of certain land at Alma Avenue and Stanmore Road, Stanmore and Tupper Street, Enmore',
    pageNumber: 88,
    lotDp: ['Lot 14, Section 4, DP 932', 'Lot 4, DP 540366', 'Lot 1, DP 540366', 'Lot 3, DP 236603', 'Lot 2, DP 540366', 'Lot 7, DP 236603'],
    streetAddresses: [] // Multiple streets, use lot/DP matching
  }
];

/**
 * Find site-specific Part 6 clauses for a property
 * @param address - Full street address (e.g., "168 Norton Street, Leichhardt NSW 2040")
 * @param lotDp - Lot/DP from property cadastre (e.g., "Lot 1, DP 963000")
 * @returns Array of matching clause numbers
 */
export function getSiteSpecificClauses(address?: string, lotDp?: string): string[] {
  const matches: string[] = [];
  
  if (!address && !lotDp) return matches;
  
  // Normalize address for matching
  const normalizedAddress = address?.toLowerCase().replace(/\s+/g, ' ').trim();
  const normalizedLotDp = lotDp?.toLowerCase().replace(/\s+/g, ' ').trim();
  
  for (const provision of SITE_SPECIFIC_PART6) {
    // Priority 1: Match by Lot/DP (most reliable)
    if (normalizedLotDp && provision.lotDp) {
      for (const lot of provision.lotDp) {
        if (normalizedLotDp === lot.toLowerCase().replace(/\s+/g, ' ').trim()) {
          matches.push(provision.clauseNumber);
          break;
        }
      }
    }
    
    // Priority 2: Match by street address
    if (normalizedAddress && provision.streetAddresses) {
      for (const streetAddr of provision.streetAddresses) {
        const normalizedStreet = streetAddr.toLowerCase().replace(/\s+/g, ' ').trim();
        // Fuzzy match - check if provision address is contained in user address
        if (normalizedAddress.includes(normalizedStreet.replace(/, nsw.*$/, ''))) {
          if (!matches.includes(provision.clauseNumber)) {
            matches.push(provision.clauseNumber);
          }
          break;
        }
      }
    }
  }
  
  return matches;
}

/**
 * Get provision details for a clause number
 */
export function getSiteSpecificProvisionDetails(clauseNumber: string): SiteSpecificProvision | undefined {
  return SITE_SPECIFIC_PART6.find(p => p.clauseNumber === clauseNumber);
}
