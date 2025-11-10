/**
 * LGA Configuration Loader
 *
 * Loads and caches LGA-specific configuration for DCP document handling
 */

import type { LGAConfig } from './types';
import innerWestConfig from './inner-west.json';

// In-memory cache of loaded configs
const configCache = new Map<string, LGAConfig>();

// Map of LGA names to config files
const LGA_CONFIGS: Record<string, LGAConfig> = {
  'inner west': innerWestConfig as LGAConfig,
  'inner-west': innerWestConfig as LGAConfig,
  'marrickville': innerWestConfig as LGAConfig,
  'ashfield': innerWestConfig as LGAConfig,
  'leichhardt': innerWestConfig as LGAConfig,
};

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

  if (lower.includes('marrickville') || lower.includes('ashfield') || lower.includes('leichhardt')) {
    return getLGAConfig('inner west');
  }

  // Add more LGAs as they're configured
  return null;
}

/**
 * Check if LGA is configured
 */
export function isLGAConfigured(lgaName: string): boolean {
  return getLGAConfig(lgaName) !== null;
}

/**
 * Get all configured LGAs
 */
export function getConfiguredLGAs(): string[] {
  return Object.keys(LGA_CONFIGS).filter((key, index, arr) => {
    // Return unique LGA names (not aliases)
    const config = LGA_CONFIGS[key];
    return arr.findIndex(k => LGA_CONFIGS[k] === config) === index;
  }).map(key => LGA_CONFIGS[key].lga);
}

// Export types
export type { LGAConfig, LGAConventions, LGAStructure, LGAQuirks } from './types';
