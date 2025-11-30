/**
 * Inner West Council Former Council Area Mapping V2
 *
 * REFACTORED: Uses external JSON config instead of hardcoded mappings
 *
 * Determines which former council (Ashfield, Leichhardt, Marrickville)
 * a property belongs to based on postcode and suburb name
 */

import {
  buildPostcodeMapping,
  buildSuburbMapping,
  hasSpecialCase
} from './lga-config-loader';

// Cache mappings to avoid rebuilding on every call
let postcodeMapping: Record<string, string> | null = null;
let suburbMapping: Record<string, string> | null = null;

/**
 * Initialize mappings from config (lazy load)
 */
function initializeMappings() {
  if (!postcodeMapping) {
    postcodeMapping = buildPostcodeMapping('inner_west');
  }
  if (!suburbMapping) {
    suburbMapping = buildSuburbMapping('inner_west');
  }
}

/**
 * Determines former Inner West council area from address string
 *
 * @param address - Full address string (e.g., "30 ILLAWARRA ROAD MARRICKVILLE 2204")
 * @param lga - LGA name (must be "INNER WEST" or include "inner west")
 * @returns Former council area name or null if not in Inner West
 *
 * @example
 * // Returns "Marrickville"
 * determineFormerCouncilArea("180 Addison Road Marrickville 2204", "INNER WEST")
 *
 * @example
 * // Returns "Leichhardt"
 * determineFormerCouncilArea("123 Parramatta Road Leichhardt 2040", "INNER WEST")
 *
 * @example
 * // Returns null (not Inner West)
 * determineFormerCouncilArea("1 George Street Sydney 2000", "Sydney")
 */
export function determineFormerCouncilArea(address: string, lga: string): string | null {
  // Only works for Inner West LGA
  if (!lga?.toLowerCase().includes('inner west')) {
    return null;
  }

  // Initialize mappings from config
  initializeMappings();

  const addressLower = address.toLowerCase();

  // First try suburb name matching (more accurate for split postcodes)
  if (suburbMapping) {
    for (const [suburb, councilArea] of Object.entries(suburbMapping)) {
      if (addressLower.includes(suburb)) {
        console.log(`[Inner West Mapping] Suburb match: ${suburb} → ${councilArea}`);
        return councilArea;
      }
    }
  }

  // Then try postcode matching as fallback
  const postcodeMatch = addressLower.match(/\b(\d{4})\b/);
  if (postcodeMatch) {
    const postcode = postcodeMatch[1];

    // Check for special case handling
    const specialCase = hasSpecialCase('inner_west', postcode);
    if (specialCase) {
      console.log(`[Inner West Mapping] Special case detected for postcode ${postcode}: ${specialCase.description}`);
    }

    if (postcodeMapping && postcodeMapping[postcode]) {
      console.log(`[Inner West Mapping] Postcode match: ${postcode} → ${postcodeMapping[postcode]}`);
      return postcodeMapping[postcode];
    }
  }

  // Unable to determine - return null
  console.log(`[Inner West Mapping] Unable to determine former council for: ${address}`);
  return null;
}

/**
 * Get all former council names for Inner West
 */
export function getInnerWestFormerCouncils(): string[] {
  return ['Ashfield', 'Leichhardt', 'Marrickville'];
}

/**
 * Check if a postcode belongs to Inner West
 */
export function isInnerWestPostcode(postcode: string): boolean {
  initializeMappings();
  return postcodeMapping ? postcode in postcodeMapping : false;
}

/**
 * Get council area for a specific postcode
 */
export function getCouncilForPostcode(postcode: string): string | null {
  initializeMappings();
  return postcodeMapping ? postcodeMapping[postcode] || null : null;
}

/**
 * Get council area for a specific suburb
 */
export function getCouncilForSuburb(suburb: string): string | null {
  initializeMappings();
  return suburbMapping ? suburbMapping[suburb.toLowerCase()] || null : null;
}
