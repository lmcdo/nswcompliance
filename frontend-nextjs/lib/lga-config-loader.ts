/**
 * LGA Configuration Loader
 *
 * Loads LGA mappings from external JSON config file instead of hardcoded values.
 * This allows for easy scaling to new LGAs without code changes.
 */

import lgaMappingsConfig from '@/config/lga-mappings.json';

export interface FormerCouncil {
  name: string;
  postcodes: string[];
  suburbs: string[];
  notes?: string;
}

export interface SpecialCase {
  description: string;
  rule: string;
  postcodes_affected: string[];
  resolution: string;
}

export interface LGAConfig {
  lga_name: string;
  formed_date: string;
  former_councils: FormerCouncil[];
  special_cases: SpecialCase[];
  dcp_priority_order: string[];
}

export interface LGAMappings {
  [key: string]: LGAConfig;
}

/**
 * Get all LGA configurations
 */
export function getLGAMappings(): LGAMappings {
  return lgaMappingsConfig as unknown as LGAMappings;
}

/**
 * Get configuration for a specific LGA
 */
export function getLGAConfig(lgaKey: string): LGAConfig | null {
  const mappings = getLGAMappings();
  return mappings[lgaKey] || null;
}

/**
 * Build postcode-to-council mapping from config
 */
export function buildPostcodeMapping(lgaKey: string): Record<string, string> {
  const config = getLGAConfig(lgaKey);
  if (!config) return {};

  const mapping: Record<string, string> = {};

  for (const council of config.former_councils) {
    for (const postcode of council.postcodes) {
      mapping[postcode] = council.name;
    }
  }

  return mapping;
}

/**
 * Build suburb-to-council mapping from config
 */
export function buildSuburbMapping(lgaKey: string): Record<string, string> {
  const config = getLGAConfig(lgaKey);
  if (!config) return {};

  const mapping: Record<string, string> = {};

  for (const council of config.former_councils) {
    for (const suburb of council.suburbs) {
      mapping[suburb.toLowerCase()] = council.name;
    }
  }

  return mapping;
}

/**
 * Get special case rules for an LGA
 */
export function getSpecialCases(lgaKey: string): SpecialCase[] {
  const config = getLGAConfig(lgaKey);
  return config?.special_cases || [];
}

/**
 * Get all former council names for an LGA
 */
export function getFormerCouncils(lgaKey: string): string[] {
  const config = getLGAConfig(lgaKey);
  return config?.former_councils.map(c => c.name) || [];
}

/**
 * Check if a postcode has special case handling
 */
export function hasSpecialCase(lgaKey: string, postcode: string): SpecialCase | null {
  const specialCases = getSpecialCases(lgaKey);
  return specialCases.find(sc => sc.postcodes_affected.includes(postcode)) || null;
}
