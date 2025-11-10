/**
 * Filtering Keywords Loader
 * Loads keyword lists for provision filtering
 */

import filteringKeywords from '@/config/filtering-keywords.json';

interface FilteringKeywords {
  commercial: string[];
  residential: string[];
  environmental: string[];
}

let cachedKeywords: FilteringKeywords | null = null;

export function getFilteringKeywords(): FilteringKeywords {
  if (!cachedKeywords) {
    cachedKeywords = filteringKeywords as FilteringKeywords;
  }
  return cachedKeywords;
}

export function getCommercialKeywords(): string[] {
  return getFilteringKeywords().commercial;
}

export function getResidentialKeywords(): string[] {
  return getFilteringKeywords().residential;
}

export function getEnvironmentalKeywords(): string[] {
  return getFilteringKeywords().environmental;
}
