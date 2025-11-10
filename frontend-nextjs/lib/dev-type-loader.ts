/**
 * Development Type Mapping Loader
 * Loads UI <-> LEP development type translations from config
 */

import devTypeMappings from '@/config/development-type-mappings.json';

interface DevTypeMappings {
  ui_to_lep: Record<string, string>;
  lep_to_ui: Record<string, string>;
}

let cachedMappings: DevTypeMappings | null = null;

export function getDevTypeMappings(): DevTypeMappings {
  if (!cachedMappings) {
    cachedMappings = devTypeMappings as DevTypeMappings;
  }
  return cachedMappings;
}

export function normalizeDevType(uiType: string): string {
  const mappings = getDevTypeMappings();
  return mappings.ui_to_lep[uiType] || uiType;
}

export function denormalizeDevType(lepType: string): string {
  const mappings = getDevTypeMappings();
  return mappings.lep_to_ui[lepType] || lepType;
}
