/**
 * Version Metadata Utilities
 * Converts Planning API dates and database dates to consistent version metadata format
 */

import type { ProvisionVersionMetadata } from '@/types/provision-search';

/**
 * Converts Planning API layer result dates to version metadata
 * Used for SEPP/LEP provisions from NSW Planning Portal
 *
 * CRITICAL: Planning API data is LIVE and CURRENT (queried today from NSW Government)
 * Therefore last_verified_date = TODAY, staleness_level = 'current'
 */
export function extractVersionFromPlanningAPI(layerResult: {
  'Commenced Date'?: string;
  'Published Date'?: string;
  'Currency Date'?: string;
  'Amendment'?: string;
  'EPI Name'?: string;
}): ProvisionVersionMetadata | undefined {
  // Extract year from EPI Name (e.g., "Inner West Local Environmental Plan 2022" → 2022)
  const yearMatch = layerResult['EPI Name']?.match(/(\d{4})/);
  const regulationYear = yearMatch ? parseInt(yearMatch[1]) : null;

  if (!regulationYear) {
    return undefined; // Can't determine regulation year
  }

  // Parse Currency Date (when NSW last updated the regulation) for display
  const currencyDate = layerResult['Currency Date'];
  const parsedCurrencyDate = currencyDate ? parseCurrencyDate(currencyDate) : null;

  // CRITICAL FIX: Planning API data is retrieved TODAY from live NSW Government API
  // So last_verified_date = TODAY (not the Currency Date!)
  const today = new Date();

  return {
    regulation_year: regulationYear,
    amendment_reference: layerResult['Amendment'] || null,
    amendment_date: parsedCurrencyDate?.toISOString() || null, // When NSW amended it (for reference)
    version_status: 'current' as 'current' | 'unverified' | 'superseded',
    last_verified_date: today.toISOString(), // TODAY - we just retrieved from live API
    days_since_verified: 0, // Just verified today from Planning Portal
    staleness_level: 'current' // Always current for live API data
  };
}

/**
 * Parse NSW Planning Portal date format (DD-MM-YYYY)
 */
function parseCurrencyDate(dateString: string): Date | null {
  const match = dateString.match(/(\d{1,2})-(\d{1,2})-(\d{4})/);
  if (!match) {
    return null;
  }

  const [, day, month, year] = match;
  return new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
}

/**
 * Extracts year from regulation/document name
 * Examples:
 * - "Inner West Local Environmental Plan 2022" → 2022
 * - "Marrickville DCP 2011" → 2011
 * - "SEPP (Sustainable Buildings) 2022" → 2022
 */
export function extractYearFromName(name: string): number | null {
  const yearMatch = name.match(/(\d{4})/);
  return yearMatch ? parseInt(yearMatch[1]) : null;
}

/**
 * Create mock version metadata for provisions without database tracking
 * Used as fallback when no version data available
 */
export function createMockVersionMetadata(documentName: string): ProvisionVersionMetadata | undefined {
  const year = extractYearFromName(documentName);
  if (!year) {
    return undefined;
  }

  // Assume last verified was today (conservative approach)
  return {
    regulation_year: year,
    amendment_reference: null,
    amendment_date: null,
    version_status: 'unverified',
    last_verified_date: new Date().toISOString(),
    days_since_verified: 0,
    staleness_level: 'current'
  };
}
