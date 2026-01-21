/**
 * LGA Configuration Loader
 *
 * Loads and caches LGA-specific configuration for DCP document handling.
 * Supports multi-LGA expansion via JSON config files.
 */

import type { LGAConfig } from './types';
import innerWestConfig from './inner-west.json';
import lgaMappings from '../../config/lga-mappings.json';

// Re-export council config functions for convenience
export {
  COUNCIL_CONFIGS,
  detectCouncil,
  getCouncilConfig,
  getConfiguredCouncils,
  isCouncilConfigured,
  getCouncilConfigByLGA,
  getSetbackFallback,
} from '../council-config';

// In-memory cache of loaded configs
const configCache = new Map<string, LGAConfig>();

// Type for LGA mapping entries
interface LGAMapping {
  lga_name: string;
  status?: string;
  formed_date?: string;
  former_councils?: Array<{
    name: string;
    config_id?: string;
    postcodes?: string[];
    suburbs?: string[];
    notes?: string;
  }>;
  postcodes?: string[];
  suburbs?: string[];
  special_cases?: Array<{
    description: string;
    rule?: string;
    postcodes_affected: string[];
    resolution: string;
  }>;
  dcp_priority_order?: string[];
}

// Map of LGA names to config files
// Dynamically built from lga-mappings.json
const LGA_CONFIGS: Record<string, LGAConfig> = {
  // Inner West and its former councils all use the same base config
  'inner west': innerWestConfig as LGAConfig,
  'inner-west': innerWestConfig as LGAConfig,
  'marrickville': innerWestConfig as LGAConfig,
  'ashfield': innerWestConfig as LGAConfig,
  'leichhardt': innerWestConfig as LGAConfig,
};

/**
 * Get all configured LGAs from the mappings file
 */
export function getConfiguredLGAs(): string[] {
  const lgas: string[] = [];
  for (const [key, mapping] of Object.entries(lgaMappings)) {
    if (key.startsWith('_')) continue; // Skip meta fields
    const lgaMapping = mapping as LGAMapping;
    if (lgaMapping.status === 'active') {
      lgas.push(lgaMapping.lga_name);
    }
  }
  return lgas;
}

/**
 * Get all planned LGAs (not yet active)
 */
export function getPlannedLGAs(): string[] {
  const lgas: string[] = [];
  for (const [key, mapping] of Object.entries(lgaMappings)) {
    if (key.startsWith('_')) continue;
    const lgaMapping = mapping as LGAMapping;
    if (lgaMapping.status === 'planned') {
      lgas.push(lgaMapping.lga_name);
    }
  }
  return lgas;
}

/**
 * Check if an LGA is active (has provisions loaded)
 */
export function isLGAActive(lgaName: string): boolean {
  const normalized = lgaName.toLowerCase().trim().replace(/ /g, '_');
  const mapping = (lgaMappings as Record<string, LGAMapping>)[normalized];
  return mapping?.status === 'active';
}

/**
 * Get LGA config by name
 * Case-insensitive, handles variations
 */
export function getLGAConfig(lgaName: string): LGAConfig | null {
  if (!lgaName) return null;

  const normalized = lgaName.toLowerCase().trim();

  // Check cache first
  if (configCache.has(normalized)) {
    return configCache.get(normalized)!;
  }

  // Look up config
  const config = LGA_CONFIGS[normalized];

  if (config) {
    // Cache it
    configCache.set(normalized, config);
    return config;
  }

  // Try fuzzy match
  for (const [key, cfg] of Object.entries(LGA_CONFIGS)) {
    if (normalized.includes(key) || key.includes(normalized)) {
      configCache.set(normalized, cfg);
      return cfg;
    }
  }

  return null;
}

/**
 * Get config from document ID
 * Extracts LGA from document name
 */
export function getConfigFromDocumentId(documentId: string): LGAConfig | null {
  const lower = documentId.toLowerCase();

  // Check Inner West councils
  if (lower.includes('marrickville') || lower.includes('ashfield') || lower.includes('leichhardt')) {
    return getLGAConfig('inner west');
  }

  // Check other configured LGAs
  for (const [key, mapping] of Object.entries(lgaMappings)) {
    if (key.startsWith('_')) continue;
    const lgaMapping = mapping as LGAMapping;

    // Check if document ID contains LGA name or former council name
    if (lower.includes(key.replace(/_/g, ' '))) {
      return getLGAConfig(key);
    }

    // Check former councils
    if (lgaMapping.former_councils) {
      for (const council of lgaMapping.former_councils) {
        if (lower.includes(council.name.toLowerCase())) {
          return getLGAConfig(key);
        }
      }
    }
  }

  return null;
}

/**
 * Check if LGA is configured
 */
export function isLGAConfigured(lgaName: string): boolean {
  return getLGAConfig(lgaName) !== null;
}

/**
 * Get LGA mapping data (postcodes, suburbs, former councils)
 */
export function getLGAMapping(lgaName: string): LGAMapping | null {
  const normalized = lgaName.toLowerCase().trim().replace(/ /g, '_');
  const mapping = (lgaMappings as Record<string, LGAMapping>)[normalized];
  return mapping || null;
}

/**
 * Find LGA from postcode
 */
export function getLGAFromPostcode(postcode: string): string | null {
  for (const [key, mapping] of Object.entries(lgaMappings)) {
    if (key.startsWith('_')) continue;
    const lgaMapping = mapping as LGAMapping;

    // Check direct postcodes
    if (lgaMapping.postcodes?.includes(postcode)) {
      return lgaMapping.lga_name;
    }

    // Check former councils
    if (lgaMapping.former_councils) {
      for (const council of lgaMapping.former_councils) {
        if (council.postcodes?.includes(postcode)) {
          return lgaMapping.lga_name;
        }
      }
    }
  }
  return null;
}

/**
 * Find former council from postcode (for merged LGAs like Inner West)
 */
export function getFormerCouncilFromPostcode(postcode: string): string | null {
  for (const [, mapping] of Object.entries(lgaMappings)) {
    const lgaMapping = mapping as LGAMapping;
    if (!lgaMapping.former_councils) continue;

    for (const council of lgaMapping.former_councils) {
      if (council.postcodes?.includes(postcode)) {
        return council.name;
      }
    }
  }
  return null;
}

/**
 * Find former council from suburb (for merged LGAs like Inner West)
 */
export function getFormerCouncilFromSuburb(suburb: string): string | null {
  const normalizedSuburb = suburb.toLowerCase().trim();

  for (const [, mapping] of Object.entries(lgaMappings)) {
    const lgaMapping = mapping as LGAMapping;
    if (!lgaMapping.former_councils) continue;

    for (const council of lgaMapping.former_councils) {
      if (council.suburbs?.some(s => s.toLowerCase() === normalizedSuburb)) {
        return council.name;
      }
    }
  }
  return null;
}

/**
 * Get the config_id for a council (used to load JSON configs)
 */
export function getCouncilConfigId(councilName: string): string | null {
  const normalized = councilName.toLowerCase().trim();

  for (const [, mapping] of Object.entries(lgaMappings)) {
    const lgaMapping = mapping as LGAMapping;
    if (!lgaMapping.former_councils) continue;

    for (const council of lgaMapping.former_councils) {
      if (council.name.toLowerCase() === normalized) {
        return council.config_id || council.name.toLowerCase();
      }
    }
  }
  return null;
}

// Export types
export type { LGAConfig, LGAConventions, LGAStructure, LGAQuirks } from './types';
